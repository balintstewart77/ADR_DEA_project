"""Replacement-panel point estimates and joint record bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable, Hashable, Sequence

import numpy as np

from analysis.validation.bootstrap import percentile
from analysis.validation.replacement import (
    DimensionPanel,
    REPLACEMENT_STATISTIC_NAMES,
    replacement_panel_analysis,
)

from .config import (
    BOOTSTRAP_REPLICATES,
    DIMENSIONS,
    MINIMUM_VALID_REPLICATES,
    POPULATION_ORDER,
    SEED_BOOTSTRAP,
)
from .panels import StageAData, dimension_panels, distance_for_dimension, population_ids


@dataclass(frozen=True)
class EncodedPanels:
    ratings: np.ndarray
    distance: np.ndarray


def encode_panels(
    panels: Sequence[DimensionPanel[Hashable]],
    distance: Callable[[Hashable, Hashable], float],
) -> EncodedPanels:
    complete = [p for p in panels if None not in (p.coder_a, p.coder_b, p.coder_c, p.model)]
    values: list[Hashable] = []
    for panel in complete:
        values.extend((panel.coder_a, panel.coder_b, panel.coder_c, panel.model))  # type: ignore[arg-type]
    categories = tuple(dict.fromkeys(values))
    index = {value: idx for idx, value in enumerate(categories)}
    ratings = np.array([
        [index[p.coder_a], index[p.coder_b], index[p.coder_c], index[p.model]]
        for p in complete
    ], dtype=np.int32)
    distances = np.array([
        [float(distance(left, right)) for right in categories]
        for left in categories
    ], dtype=float)
    return EncodedPanels(ratings, distances)


def alpha_encoded(ratings: np.ndarray, distance: np.ndarray) -> float | None:
    """Coincidence-form alpha for a complete N x 3 encoded rating matrix."""

    if ratings.ndim != 2 or ratings.shape[1] != 3 or len(ratings) == 0:
        return None
    observed_sum = (
        distance[ratings[:, 0], ratings[:, 1]].sum()
        + distance[ratings[:, 0], ratings[:, 2]].sum()
        + distance[ratings[:, 1], ratings[:, 2]].sum()
    )
    n_ratings = ratings.size
    observed = float(observed_sum) / n_ratings
    counts = np.bincount(ratings.ravel(), minlength=distance.shape[0]).astype(float)
    expected = float(counts @ distance @ counts) / (n_ratings * (n_ratings - 1))
    if not np.isfinite(observed) or not np.isfinite(expected) or abs(expected) <= 1e-15:
        return None
    return 1.0 - observed / expected


def encoded_replacement_statistics(encoded: EncodedPanels, indices: np.ndarray | None = None) -> dict[str, float | None]:
    ratings = encoded.ratings if indices is None else encoded.ratings[indices]
    panels = {
        "alpha_ABC": ratings[:, [0, 1, 2]],
        "alpha_LBC": ratings[:, [3, 1, 2]],
        "alpha_ALC": ratings[:, [0, 3, 2]],
        "alpha_ABL": ratings[:, [0, 1, 3]],
    }
    values = {name: alpha_encoded(matrix, encoded.distance) for name, matrix in panels.items()}
    human = values["alpha_ABC"]
    for delta, alpha in (("delta_A", "alpha_LBC"), ("delta_B", "alpha_ALC"), ("delta_C", "alpha_ABL")):
        values[delta] = None if human is None or values[alpha] is None else values[alpha] - human
    delta_values = [values[name] for name in ("delta_A", "delta_B", "delta_C")]
    values["delta_min"] = None if any(value is None for value in delta_values) else min(delta_values)  # type: ignore[arg-type]
    return values


def bootstrap_replacement(
    encoded: EncodedPanels,
    *,
    attempts: int = BOOTSTRAP_REPLICATES,
    seed: int = SEED_BOOTSTRAP,
) -> list[dict[str, float | int | None]]:
    """Jointly resample complete record rows, retaining duplicate draws."""

    generator = Random(seed)
    n = len(encoded.ratings)
    rows: list[dict[str, float | int | None]] = []
    for replicate in range(1, attempts + 1):
        indices = np.fromiter((generator.randrange(n) for _ in range(n)), dtype=np.int32, count=n)
        values = encoded_replacement_statistics(encoded, indices)
        rows.append({"replicate": replicate, "sample_n": n, **values})
    return rows


def _canonical_values(panels, distance) -> tuple[int, dict[str, float | None]]:
    result = replacement_panel_analysis(panels, distance)
    values = {
        "alpha_ABC": result.alpha_abc.alpha,
        "alpha_LBC": result.alpha_lbc.alpha,
        "alpha_ALC": result.alpha_alc.alpha,
        "alpha_ABL": result.alpha_abl.alpha,
        "delta_A": result.delta_a,
        "delta_B": result.delta_b,
        "delta_C": result.delta_c,
        "delta_min": result.delta_min,
    }
    return len(result.common_record_ids), values


def _interval(rows: list[dict[str, object]], statistic: str, attempts: int) -> dict[str, object]:
    valid = [float(row[statistic]) for row in rows if row[statistic] is not None]
    report = len(valid) >= min(MINIMUM_VALID_REPLICATES, int(0.9 * attempts))
    return {
        "valid": len(valid),
        "invalid": attempts - len(valid),
        "lower": percentile(valid, 0.025) if report else None,
        "upper": percentile(valid, 0.975) if report else None,
        "reported": report,
    }


def run_replacement_analyses(
    data: StageAData,
    subset_ids: dict[str, frozenset[str]],
    *,
    attempts: int = BOOTSTRAP_REPLICATES,
) -> dict[str, list[dict[str, object]]]:
    panel_results: list[dict[str, object]] = []
    delta_results: list[dict[str, object]] = []
    replicate_results: list[dict[str, object]] = []
    trigger_results: list[dict[str, object]] = []
    for population in POPULATION_ORDER:
        ids = population_ids(data, population, subset_ids)
        for dimension in DIMENSIONS:
            panels = dimension_panels(data, ids, dimension)
            distance = distance_for_dimension(dimension)
            n, points = _canonical_values(panels, distance)
            encoded = encode_panels(panels, distance)
            if n != len(encoded.ratings):
                raise AssertionError("Canonical and encoded complete-case Ns differ")
            encoded_points = encoded_replacement_statistics(encoded)
            for statistic in REPLACEMENT_STATISTIC_NAMES:
                left, right = points[statistic], encoded_points[statistic]
                if left is None or right is None:
                    if left is not right:
                        raise AssertionError("Canonical and encoded undefined states differ")
                elif not np.isclose(left, right, rtol=0, atol=1e-12):
                    raise AssertionError("Encoded alpha differs from canonical implementation")
            boot = bootstrap_replacement(encoded, attempts=attempts)
            analysis_note = (
                "DIAGNOSTIC — disagreement-enriched hard-case sample; not a register-wide performance estimate."
                if population == "hard_case" else ""
            )
            for row in boot:
                replicate_results.append({"population": population, "dimension": dimension, **row, "analysis_note": analysis_note})
            summaries = {name: _interval(boot, name, attempts) for name in REPLACEMENT_STATISTIC_NAMES}
            distance_name = "MASI" if dimension in {"Research Domains", "Analytical Purposes"} else "nominal"
            for panel_name, statistic in (
                ("ABC", "alpha_ABC"), ("LBC", "alpha_LBC"),
                ("ALC", "alpha_ALC"), ("ABL", "alpha_ABL"),
            ):
                summary = summaries[statistic]
                panel_results.append({
                    "population": population, "dimension": dimension, "distance": distance_name,
                    "n_records": n, "panel": panel_name, "point_estimate": points[statistic],
                    "bootstrap_valid_n": summary["valid"], "bootstrap_invalid_n": summary["invalid"],
                    "ci_lower": summary["lower"], "ci_upper": summary["upper"],
                    "ci_reported": summary["reported"],
                    "analysis_note": analysis_note,
                })
            for statistic in ("delta_A", "delta_B", "delta_C", "delta_min"):
                summary = summaries[statistic]
                delta_results.append({
                    "population": population, "dimension": dimension, "n_records": n,
                    "delta": statistic, "point_estimate": points[statistic],
                    "bootstrap_valid_n": summary["valid"], "bootstrap_invalid_n": summary["invalid"],
                    "ci_lower": summary["lower"], "ci_upper": summary["upper"],
                    "ci_reported": summary["reported"],
                    "analysis_note": analysis_note,
                })
            if population == "baseline":
                delta_min = summaries["delta_min"]
                component_values = [points[name] for name in ("delta_A", "delta_B", "delta_C")]
                trigger_results.append({
                    "population": population, "dimension": dimension,
                    "all_three_replacement_deltas_below_zero": (
                        "YES" if all(value is not None and value < 0 for value in component_values) else "NO"
                    ),
                    "delta_min_ci_entirely_below_zero": (
                        "CI NOT ESTIMABLE" if not delta_min["reported"]
                        else "YES" if float(delta_min["upper"]) < 0 else "NO"
                    ),
                })
    return {
        "panels": panel_results,
        "deltas": delta_results,
        "replicates": replicate_results,
        "triggers": trigger_results,
    }
