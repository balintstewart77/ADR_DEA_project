"""Pairwise Krippendorff alpha quantities (Analyses 1-4) on four-rater records.

A record is a tuple ``(A, B, C, L)`` of label values for one project. Every
alpha is a call into the shared estimator ``analysis.validation.alpha`` with
the canonical distance; nothing here reimplements alpha, a metric or the
bootstrap. The distance is memoised per process: the memo returns the exact
object the shared metric returns, so every float conversion is unchanged.
"""

from __future__ import annotations

from functools import lru_cache
from math import isfinite
from typing import Callable, Hashable, Mapping, Sequence

from analysis.validation.alpha import AlphaResult, krippendorff_alpha
from analysis.validation.bootstrap import StatisticValue, bootstrap_joint
from analysis.validation.metrics import masi_distance, nominal_distance

RATER_INDEX = {"A": 0, "B": 1, "C": 2, "L": 3}
HUMAN_PAIRS = (("A", "B"), ("A", "C"), ("B", "C"))
MODEL_PAIRS = (("L", "A"), ("L", "B"), ("L", "C"))
PAIR_NAMES = tuple(f"alpha_{x}{y}" for x, y in HUMAN_PAIRS + MODEL_PAIRS)
DIFFERENCES = (
    ("diff_AC_minus_AB", "alpha_AC", "alpha_AB"),
    ("diff_AC_minus_BC", "alpha_AC", "alpha_BC"),
    ("diff_AB_minus_BC", "alpha_AB", "alpha_BC"),
)
# X -> ((human pair terms of H_X), (model pair terms of M_X)), fixed order.
REPLACEMENT_TERMS = {
    "A": (("alpha_AB", "alpha_AC"), ("alpha_LB", "alpha_LC")),
    "B": (("alpha_AB", "alpha_BC"), ("alpha_LA", "alpha_LC")),
    "C": (("alpha_AC", "alpha_BC"), ("alpha_LA", "alpha_LB")),
}
DIFFERENCE_NAMES = tuple(name for name, _, _ in DIFFERENCES)
REPLACEMENT_NAMES = tuple(f"{kind}_{x}" for x in "ABC" for kind in ("H", "M", "D"))
STATISTIC_NAMES = PAIR_NAMES + DIFFERENCE_NAMES + REPLACEMENT_NAMES

Record = tuple[Hashable, Hashable, Hashable, Hashable]


def canonical_distance(dimension: str) -> Callable[[Hashable, Hashable], float]:
    """Mirror of the canonical choice; asserted equal to panels.distance_for_dimension in run.py."""

    return masi_distance if dimension in {"Research Domains", "Analytical Purposes"} else nominal_distance


def memoised(distance: Callable[[Hashable, Hashable], float]) -> Callable[[Hashable, Hashable], float]:
    return lru_cache(maxsize=None)(distance)


def panel_alpha(records: Sequence[Record], raters: Sequence[str], distance) -> AlphaResult:
    """One call into the shared estimator with units made of the named raters."""

    index = [RATER_INDEX[r] for r in raters]
    return krippendorff_alpha((tuple(record[i] for i in index) for record in records), distance)


def _undefined(reason: str | None) -> StatisticValue:
    return StatisticValue(None, False, reason or "undefined")


def derive(pairwise: Mapping[str, StatisticValue]) -> dict[str, StatisticValue]:
    """Analyses 3 and 4 from the six pairwise values; undefined inputs propagate."""

    out: dict[str, StatisticValue] = dict(pairwise)

    def combine(names: Sequence[str], fn) -> StatisticValue:
        items = [out[n] for n in names]
        bad = [f"{n}:{out[n].reason}" for n in names if not out[n].valid]
        if bad:
            return _undefined("input_undefined(" + ";".join(bad) + ")")
        return StatisticValue(fn(*[i.value for i in items]), True, None)

    for name, left, right in DIFFERENCES:
        out[name] = combine((left, right), lambda a, b: a - b)
    for x, (human, model) in REPLACEMENT_TERMS.items():
        out[f"H_{x}"] = combine(human, lambda a, b: (a + b) / 2)
        out[f"M_{x}"] = combine(model, lambda a, b: (a + b) / 2)
        out[f"D_{x}"] = combine((f"M_{x}", f"H_{x}"), lambda m, h: m - h)
    return out


def statistics(records: Sequence[Record], distance) -> dict[str, StatisticValue]:
    pairwise: dict[str, StatisticValue] = {}
    for x, y in HUMAN_PAIRS + MODEL_PAIRS:
        result = panel_alpha(records, (x, y), distance)
        pairwise[f"alpha_{x}{y}"] = StatisticValue(result.alpha, result.valid, result.undefined_reason)
    return derive(pairwise)


def ordering(values: Mapping[str, float | None]) -> str | None:
    """Ascending order of component letters; exact float ties shown with '='."""

    if any(v is None or not isfinite(v) for v in values.values()):
        return None
    ranked = sorted(values.items(), key=lambda kv: (kv[1], kv[0]))  # ties: alphabetical letters
    text = ranked[0][0]
    for (_, prev), (letter, value) in zip(ranked, ranked[1:]):
        text += (" = " if value == prev else " < ") + letter
    return text


def bootstrap_job(
    records: Sequence[Record], dimension: str, attempts: int, seed: int, minimum_valid_fraction: float
) -> dict[str, dict[str, object]]:
    """Joint record-level bootstrap of all Analyses 1-4 quantities (one process)."""

    distance = memoised(canonical_distance(dimension))
    result = bootstrap_joint(
        tuple(records),
        lambda sample: statistics(sample, distance),
        statistic_names=STATISTIC_NAMES,
        attempted_replicates=attempts,
        seed=seed,
        minimum_valid_fraction=minimum_valid_fraction,
    )
    return {
        name: dict(
            attempted=s.attempted, valid=s.valid, invalid=s.invalid, lower=s.lower, upper=s.upper,
            interval_reported=s.interval_reported, invalid_reasons=list(s.invalid_reasons),
        )
        for name, s in result.statistics.items()
    } | {"_seed": {"seed": result.seed, "attempted": result.attempted_replicates, "semantics": result.semantics}}
