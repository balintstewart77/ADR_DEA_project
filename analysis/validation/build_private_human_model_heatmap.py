"""Build the restricted second-stage human/model pilot comparison.

The builder is deliberately separate from the source-masked pilot runner.  It
reads frozen local model outputs, validates their provenance and taxonomy, and
writes all data-bearing products below ``preregistration_restricted``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from .build_private_pilot_heatmap import (
    DOMAIN_ABBREVIATIONS,
    PURPOSE_ABBREVIATIONS,
)
from .metrics import exact_set_equality, jaccard_similarity
from .schema import DOMAIN_LABELS, PURPOSE_LABELS, UNCLEAR
from .scratch_agreement import complete_set_pattern


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_READY = Path(
    "preregistration/package/05_training_and_pilot/pilot_analysis/"
    "pilot_analysis_ready.csv"
)
DEFAULT_AGREEMENT = Path(
    "preregistration/package/05_training_and_pilot/pilot_analysis/"
    "pilot_record_agreement.csv"
)
DEFAULT_PILOT_RAW = Path(
    "preregistration/package/05_training_and_pilot/"
    "pilot_raw_DATA_2026-07-20_2153.csv"
)
DEFAULT_FABLE = Path(
    "analysis/outputs_classified_20260702_fable5/layer_classifications.csv"
)
DEFAULT_FABLE_METADATA = Path(
    "analysis/outputs_classified_20260702_fable5/run_metadata.json"
)
DEFAULT_GPT55 = Path(
    "analysis/releases/gpt55_crossmodel_20260707/gpt55_classifications.csv"
)
DEFAULT_GPT55_METADATA = Path("analysis/outputs/gpt55_run_metadata.json")
DEFAULT_OUTPUT_DIR = Path("preregistration_restricted/pilot_private_review")

CODERS = ("C01", "C02", "C03")
MODELS = ("Fable", "GPT-5.5")
SOURCES = (*CODERS, *MODELS)
DIMENSIONS = ("Research Domains", "Analytical Purposes")
READY_FIELDS = {
    "Research Domains": "research_domains",
    "Analytical Purposes": "analytical_purposes",
}
MODEL_FIELDS = {
    "Research Domains": "substantive_domains",
    "Analytical Purposes": "analytical_purpose",
}
ALLOWED_LABELS = {
    "Research Domains": DOMAIN_LABELS,
    "Analytical Purposes": PURPOSE_LABELS,
}
LABEL_ORDERS = {
    "Research Domains": tuple(DOMAIN_ABBREVIATIONS),
    "Analytical Purposes": tuple(PURPOSE_ABBREVIATIONS),
}
ABBREVIATIONS = {
    "Research Domains": DOMAIN_ABBREVIATIONS,
    "Analytical Purposes": PURPOSE_ABBREVIATIONS,
}
COLORS = {
    "green": "#5AAE61",
    "red": "#D6604D",
    "amber": "#F6C85F",
    "grey": "#BDBDBD",
}

JOIN_COLUMNS = (
    "record_id",
    "dimension",
    "source",
    "canonical_labels",
    "display_labels",
    "source_type",
    "human_complete_set_pattern",
    "human_majority_set",
    "exact_match_to_human_majority",
    "matching_human_coder_ids",
    "mean_jaccard_to_three_coders",
    "jaccard_to_human_majority_set",
)
SUMMARY_COLUMNS = (
    "comparison_type",
    "model",
    "dimension",
    "record_count",
    "exact_matches_to_C01",
    "exact_matches_to_C02",
    "exact_matches_to_C03",
    "mean_jaccard_to_C01",
    "mean_jaccard_to_C02",
    "mean_jaccard_to_C03",
    "human_majority_available_count",
    "exact_matches_to_human_majority",
    "exact_match_rate_to_human_majority",
    "mean_jaccard_to_human_majority",
    "all_humans_distinct_count",
    "fable_gpt_exact_complete_set_agreement_count",
    "fable_gpt_mean_jaccard",
)
DISAGREEMENT_COLUMNS = (
    "record_id",
    "dimension",
    "human_pattern",
    "C01_labels",
    "C02_labels",
    "C03_labels",
    "Fable_labels",
    "GPT55_labels",
    "Fable_exact_human_match",
    "GPT55_exact_human_match",
    "Fable_mean_human_jaccard",
    "GPT55_mean_human_jaccard",
    "model_sets_identical",
    "notes",
)


class HumanModelHeatmapError(RuntimeError):
    """Raised when provenance, joins, taxonomy, or output scope is invalid."""


@dataclass(frozen=True)
class SourceProvenance:
    source: str
    path: Path
    sha256: str
    model_identifier: str
    run_identifier: str
    prompt_version: str
    taxonomy_version: str
    rows: int
    record_id_field: str = "Record ID"
    domain_field: str = "substantive_domains"
    purpose_field: str = "analytical_purpose"
    decoding: str = "semicolon-delimited canonical labels decoded to sets"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _float(value: float) -> str:
    return f"{value:.6f}"


def validate_private_output_path(output_dir: Path) -> None:
    if "preregistration_restricted" not in {
        part.lower() for part in output_dir.resolve().parts
    }:
        raise HumanModelHeatmapError(
            "Human-model pilot outputs must be under preregistration_restricted"
        )


def parse_label_set(
    value: str,
    *,
    delimiter: str,
    allowed: frozenset[str],
    field: str,
) -> frozenset[str]:
    labels = frozenset(part.strip() for part in str(value).split(delimiter) if part.strip())
    if not labels:
        raise HumanModelHeatmapError(f"Missing classification in {field}")
    unknown = labels - allowed
    if unknown:
        raise HumanModelHeatmapError(f"Unknown taxonomy label in {field}: {sorted(unknown)!r}")
    if UNCLEAR in labels and len(labels) > 1:
        raise HumanModelHeatmapError(
            f"Unclear from Register Entry is combined with substantive labels in {field}"
        )
    return labels


def canonical_text(dimension: str, labels: frozenset[str]) -> str:
    order = {label: index for index, label in enumerate(LABEL_ORDERS[dimension])}
    return " | ".join(sorted(labels, key=lambda label: order[label]))


def display_text(dimension: str, labels: frozenset[str]) -> str:
    order = {label: index for index, label in enumerate(LABEL_ORDERS[dimension])}
    abbreviations = ABBREVIATIONS[dimension]
    return "|".join(
        abbreviations[label] for label in sorted(labels, key=lambda label: order[label])
    )


def verify_pilot_taxonomy_pointer(
    pilot_raw_path: Path,
    expected_record_ids: set[str],
) -> tuple[str, str]:
    rows = _read_csv(pilot_raw_path)
    required = {"source_record_id", "production_ver"}
    if rows and not required <= set(rows[0]):
        raise HumanModelHeatmapError("Pilot raw export lacks production-version fields")
    observed_ids = {row["source_record_id"].strip() for row in rows}
    if observed_ids != expected_record_ids:
        raise HumanModelHeatmapError("Pilot production-pointer records do not match analysis")
    pointers = {row["production_ver"].strip() for row in rows}
    if len(pointers) != 1:
        raise HumanModelHeatmapError(f"Ambiguous pilot production pointers: {sorted(pointers)!r}")
    pointer = next(iter(pointers))
    marker = "-fable5-"
    if marker not in pointer:
        raise HumanModelHeatmapError(f"Cannot decode pilot taxonomy from {pointer!r}")
    return pointer, pointer.split(marker, 1)[1]


def verify_model_metadata(
    metadata_path: Path,
    *,
    source: str,
    expected_taxonomy: str,
    row_count: int,
) -> dict[str, object]:
    with metadata_path.open(encoding="utf-8") as handle:
        metadata = json.load(handle)
    expected = {
        "Fable": ("claude-fable-5", "validation_release_fable5_full_register"),
        "GPT-5.5": ("gpt-5.5", "cross_model_hard_case_disagreement_stratum_not_release"),
    }
    expected_model, expected_run = expected[source]
    if metadata.get("model") != expected_model:
        raise HumanModelHeatmapError(
            f"Unexpected {source} model identifier: {metadata.get('model')!r}"
        )
    if metadata.get("run_type") != expected_run:
        raise HumanModelHeatmapError(
            f"Ambiguous {source} run type: {metadata.get('run_type')!r}"
        )
    if metadata.get("taxonomy_version") != expected_taxonomy:
        raise HumanModelHeatmapError(
            f"{source} taxonomy-version mismatch: "
            f"{metadata.get('taxonomy_version')!r} != {expected_taxonomy!r}"
        )
    if metadata.get("prompt_version") != expected_taxonomy:
        raise HumanModelHeatmapError(
            f"{source} prompt-version mismatch: {metadata.get('prompt_version')!r}"
        )
    if int(metadata.get("n_projects", -1)) != row_count:
        raise HumanModelHeatmapError(
            f"{source} metadata row count does not match classification file"
        )
    return metadata


def load_model_rows(
    path: Path,
    *,
    source: str,
    expected_record_ids: set[str],
) -> tuple[dict[tuple[str, str], frozenset[str]], int]:
    rows = _read_csv(path)
    required = {"Record ID", "substantive_domains", "analytical_purpose"}
    if source == "GPT-5.5":
        required |= {"gpt_status", "validation_error"}
    if rows and not required <= set(rows[0]):
        raise HumanModelHeatmapError(
            f"{source} input missing columns: {sorted(required - set(rows[0]))!r}"
        )
    ids = [row["Record ID"] for row in rows]
    if any(not record_id or record_id != record_id.strip() for record_id in ids):
        raise HumanModelHeatmapError(f"{source} has blank or unnormalised Record IDs")
    duplicates = sorted(record_id for record_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise HumanModelHeatmapError(f"Duplicate {source} model rows: {duplicates[:10]!r}")
    selected = {row["Record ID"]: row for row in rows if row["Record ID"] in expected_record_ids}
    missing = sorted(expected_record_ids - set(selected))
    if missing:
        raise HumanModelHeatmapError(f"Missing {source} model rows: {missing!r}")
    if len(selected) != len(expected_record_ids):
        raise HumanModelHeatmapError(f"Unexpected {source} pilot join cardinality")
    output: dict[tuple[str, str], frozenset[str]] = {}
    for record_id, row in selected.items():
        if source == "GPT-5.5" and (
            row["gpt_status"] != "ok" or row["validation_error"].strip()
        ):
            raise HumanModelHeatmapError(
                f"Invalid GPT-5.5 stored output for {record_id}"
            )
        for dimension in DIMENSIONS:
            output[(record_id, dimension)] = parse_label_set(
                row[MODEL_FIELDS[dimension]],
                delimiter=";",
                allowed=ALLOWED_LABELS[dimension],
                field=f"{source}/{record_id}/{dimension}",
            )
    return output, len(rows)


def load_human_rows(
    ready_rows: Sequence[Mapping[str, str]],
    agreement_rows: Sequence[Mapping[str, str]],
) -> tuple[
    list[str],
    dict[tuple[str, str, str], frozenset[str]],
    dict[tuple[str, str], str],
]:
    if len(ready_rows) != 30:
        raise HumanModelHeatmapError(f"Expected 30 human rows; found {len(ready_rows)}")
    human: dict[tuple[str, str, str], frozenset[str]] = {}
    for row in ready_rows:
        record_id, coder = row["record_id"], row["coder_id"]
        if coder not in CODERS:
            raise HumanModelHeatmapError(f"Unexpected coder: {coder!r}")
        for dimension in DIMENSIONS:
            key = (record_id, dimension, coder)
            if key in human:
                raise HumanModelHeatmapError(f"Duplicate human classification: {key!r}")
            human[key] = parse_label_set(
                row[READY_FIELDS[dimension]],
                delimiter="|",
                allowed=ALLOWED_LABELS[dimension],
                field=f"{coder}/{record_id}/{dimension}",
            )
    record_ids = sorted({key[0] for key in human})
    if len(record_ids) != 10:
        raise HumanModelHeatmapError(f"Expected 10 pilot records; found {len(record_ids)}")
    expected = {
        (record_id, dimension, coder)
        for record_id in record_ids
        for dimension in DIMENSIONS
        for coder in CODERS
    }
    if set(human) != expected:
        raise HumanModelHeatmapError("Human pilot matrix is not complete 10 x 2 x 3")

    patterns: dict[tuple[str, str], str] = {}
    for row in agreement_rows:
        record_id = row["record_id"]
        dimension = row["classification_dimension"]
        if record_id not in record_ids or dimension not in DIMENSIONS:
            continue
        key = (record_id, dimension)
        if key in patterns:
            raise HumanModelHeatmapError(f"Duplicate human agreement row: {key!r}")
        values = [human[(record_id, dimension, coder)] for coder in CODERS]
        derived = complete_set_pattern(values)
        if row["complete_set_pattern"] != derived:
            raise HumanModelHeatmapError(f"Human pattern mismatch for {key!r}")
        for coder, value in zip(CODERS, values):
            stored = parse_label_set(
                row[f"{coder}_set"],
                delimiter="|",
                allowed=ALLOWED_LABELS[dimension],
                field=f"agreement/{coder}/{record_id}/{dimension}",
            )
            if stored != value:
                raise HumanModelHeatmapError(f"Human set mismatch for {key!r}/{coder}")
        patterns[key] = derived
    expected_patterns = {
        (record_id, dimension) for record_id in record_ids for dimension in DIMENSIONS
    }
    if set(patterns) != expected_patterns:
        raise HumanModelHeatmapError("Human agreement table is incomplete")
    return record_ids, human, patterns


def human_majority_set(
    coder_sets: Mapping[str, frozenset[str]],
) -> frozenset[str] | None:
    counts = Counter(coder_sets.values())
    value, count = counts.most_common(1)[0]
    return value if count >= 2 else None


def matching_coders(
    labels: frozenset[str], coder_sets: Mapping[str, frozenset[str]]
) -> str:
    matches = [coder for coder in CODERS if exact_set_equality(labels, coder_sets[coder])]
    return "|".join(matches) if matches else "none"


def build_joined_rows(
    record_ids: Sequence[str],
    human: Mapping[tuple[str, str, str], frozenset[str]],
    patterns: Mapping[tuple[str, str], str],
    model_sets: Mapping[str, Mapping[tuple[str, str], frozenset[str]]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record_id in record_ids:
        for dimension in DIMENSIONS:
            coder_sets = {
                coder: human[(record_id, dimension, coder)] for coder in CODERS
            }
            majority = human_majority_set(coder_sets)
            for source in SOURCES:
                labels = (
                    coder_sets[source]
                    if source in CODERS
                    else model_sets[source][(record_id, dimension)]
                )
                jaccards = [
                    float(jaccard_similarity(labels, coder_sets[coder])) for coder in CODERS
                ]
                rows.append({
                    "record_id": record_id,
                    "dimension": dimension,
                    "source": source,
                    "canonical_labels": canonical_text(dimension, labels),
                    "display_labels": display_text(dimension, labels),
                    "source_type": "human" if source in CODERS else "model",
                    "human_complete_set_pattern": patterns[(record_id, dimension)],
                    "human_majority_set": (
                        canonical_text(dimension, majority) if majority is not None else ""
                    ),
                    "exact_match_to_human_majority": (
                        "" if majority is None else int(exact_set_equality(labels, majority))
                    ),
                    "matching_human_coder_ids": matching_coders(labels, coder_sets),
                    "mean_jaccard_to_three_coders": _float(mean(jaccards)),
                    "jaccard_to_human_majority_set": (
                        "" if majority is None else _float(float(jaccard_similarity(labels, majority)))
                    ),
                })
    if len(rows) != 100:
        raise HumanModelHeatmapError(f"Expected 100 joined rows; found {len(rows)}")
    return rows


def _joined_lookup(
    rows: Sequence[Mapping[str, object]],
) -> dict[tuple[str, str, str], Mapping[str, object]]:
    lookup: dict[tuple[str, str, str], Mapping[str, object]] = {}
    for row in rows:
        key = (str(row["record_id"]), str(row["dimension"]), str(row["source"]))
        if key in lookup:
            raise HumanModelHeatmapError(f"Duplicate joined row: {key!r}")
        lookup[key] = row
    return lookup


def build_heatmap_cells(
    joined_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    lookup = _joined_lookup(joined_rows)
    record_ids = sorted({key[0] for key in lookup})
    cells: list[dict[str, str]] = []
    for record_id in record_ids:
        for dimension in DIMENSIONS:
            human_rows = {coder: lookup[(record_id, dimension, coder)] for coder in CODERS}
            pattern = str(human_rows["C01"]["human_complete_set_pattern"])
            majority_text = str(human_rows["C01"]["human_majority_set"])
            for source in SOURCES:
                row = lookup[(record_id, dimension, source)]
                annotation = ""
                if source in CODERS:
                    if pattern == "unanimous":
                        color, state = "green", "human_all_agree"
                    elif pattern == "two_vs_one":
                        match_count = sum(
                            row["canonical_labels"] == human_rows[coder]["canonical_labels"]
                            for coder in CODERS
                        )
                        color, state = (
                            ("green", "human_agreeing_pair")
                            if match_count == 2
                            else ("red", "human_lone_dissenter")
                        )
                    elif pattern == "all_sets_distinct":
                        color, state = "amber", "human_all_distinct"
                    else:
                        raise HumanModelHeatmapError(f"Unknown human pattern: {pattern!r}")
                elif pattern == "all_sets_distinct":
                    color, state = "amber", "model_no_human_complete_set_majority"
                    matches = str(row["matching_human_coder_ids"])
                    annotation = f"={matches}" if matches != "none" else "unique"
                else:
                    exact = str(row["canonical_labels"]) == majority_text
                    color, state = (
                        ("green", "model_matches_human_majority")
                        if exact
                        else ("red", "model_differs_from_human_majority")
                    )
                cells.append({
                    "record_id": record_id,
                    "dimension": dimension,
                    "source": source,
                    "display": str(row["display_labels"]),
                    "annotation": annotation,
                    "cell_color": color,
                    "agreement_state": state,
                })
    if len(record_ids) != 10 or len(cells) != 100:
        raise HumanModelHeatmapError(
            f"Heatmap must be 10 rows x 10 columns; got {len(record_ids)} rows/"
            f"{len(cells)} cells"
        )
    if any(cell["cell_color"] not in {"green", "red", "amber", "grey"} for cell in cells):
        raise HumanModelHeatmapError("Every heatmap cell must have one valid colour")
    return cells


def build_comparison_summary(
    joined_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    lookup = _joined_lookup(joined_rows)
    record_ids = sorted({key[0] for key in lookup})
    output: list[dict[str, object]] = []
    for model in MODELS:
        for dimension in DIMENSIONS:
            model_rows = [lookup[(record_id, dimension, model)] for record_id in record_ids]
            available = [row for row in model_rows if row["human_majority_set"]]
            row: dict[str, object] = {
                column: "" for column in SUMMARY_COLUMNS
            }
            row.update({
                "comparison_type": "model_to_humans",
                "model": model,
                "dimension": dimension,
                "record_count": len(model_rows),
                "human_majority_available_count": len(available),
                "exact_matches_to_human_majority": sum(
                    int(item["exact_match_to_human_majority"]) for item in available
                ),
                "exact_match_rate_to_human_majority": _float(
                    mean(int(item["exact_match_to_human_majority"]) for item in available)
                ),
                "mean_jaccard_to_human_majority": _float(
                    mean(float(item["jaccard_to_human_majority_set"]) for item in available)
                ),
                "all_humans_distinct_count": sum(
                    item["human_complete_set_pattern"] == "all_sets_distinct"
                    for item in model_rows
                ),
            })
            for coder in CODERS:
                coder_rows = [lookup[(record_id, dimension, coder)] for record_id in record_ids]
                row[f"exact_matches_to_{coder}"] = sum(
                    model_item["canonical_labels"] == coder_item["canonical_labels"]
                    for model_item, coder_item in zip(model_rows, coder_rows)
                )
                row[f"mean_jaccard_to_{coder}"] = _float(mean(
                    float(jaccard_similarity(
                        parse_label_set(
                            str(model_item["canonical_labels"]), delimiter="|",
                            allowed=ALLOWED_LABELS[dimension], field="summary/model",
                        ),
                        parse_label_set(
                            str(coder_item["canonical_labels"]), delimiter="|",
                            allowed=ALLOWED_LABELS[dimension], field="summary/human",
                        ),
                    ))
                    for model_item, coder_item in zip(model_rows, coder_rows)
                ))
            output.append(row)
    for dimension in DIMENSIONS:
        pairs = [
            (lookup[(record_id, dimension, "Fable")], lookup[(record_id, dimension, "GPT-5.5")])
            for record_id in record_ids
        ]
        row = {column: "" for column in SUMMARY_COLUMNS}
        row.update({
            "comparison_type": "model_to_model",
            "model": "Fable_vs_GPT-5.5",
            "dimension": dimension,
            "record_count": len(pairs),
            "fable_gpt_exact_complete_set_agreement_count": sum(
                left["canonical_labels"] == right["canonical_labels"] for left, right in pairs
            ),
            "fable_gpt_mean_jaccard": _float(mean(
                float(jaccard_similarity(
                    parse_label_set(
                        str(left["canonical_labels"]), delimiter="|",
                        allowed=ALLOWED_LABELS[dimension], field="summary/Fable",
                    ),
                    parse_label_set(
                        str(right["canonical_labels"]), delimiter="|",
                        allowed=ALLOWED_LABELS[dimension], field="summary/GPT-5.5",
                    ),
                ))
                for left, right in pairs
            )),
        })
        output.append(row)
    return output


def build_disagreement_rows(
    joined_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    lookup = _joined_lookup(joined_rows)
    record_ids = sorted({key[0] for key in lookup})
    output: list[dict[str, object]] = []
    for record_id in record_ids:
        for dimension in DIMENSIONS:
            pattern = str(lookup[(record_id, dimension, "C01")]["human_complete_set_pattern"])
            if pattern == "unanimous":
                continue
            fable = lookup[(record_id, dimension, "Fable")]
            gpt = lookup[(record_id, dimension, "GPT-5.5")]
            fable_match = str(fable["matching_human_coder_ids"])
            gpt_match = str(gpt["matching_human_coder_ids"])
            identical = fable["canonical_labels"] == gpt["canonical_labels"]
            notes = (
                f"Fable exact human match: {fable_match}; "
                f"GPT-5.5 exact human match: {gpt_match}; "
                f"model sets identical: {'yes' if identical else 'no'}."
            )
            output.append({
                "record_id": record_id,
                "dimension": dimension,
                "human_pattern": pattern,
                "C01_labels": lookup[(record_id, dimension, "C01")]["canonical_labels"],
                "C02_labels": lookup[(record_id, dimension, "C02")]["canonical_labels"],
                "C03_labels": lookup[(record_id, dimension, "C03")]["canonical_labels"],
                "Fable_labels": fable["canonical_labels"],
                "GPT55_labels": gpt["canonical_labels"],
                "Fable_exact_human_match": fable_match,
                "GPT55_exact_human_match": gpt_match,
                "Fable_mean_human_jaccard": fable["mean_jaccard_to_three_coders"],
                "GPT55_mean_human_jaccard": gpt["mean_jaccard_to_three_coders"],
                "model_sets_identical": int(identical),
                "notes": notes,
            })
    return output


def render_heatmap(cells: Sequence[Mapping[str, str]], output_path: Path) -> None:
    record_ids = sorted({cell["record_id"] for cell in cells})
    columns = [(dimension, source) for dimension in DIMENSIONS for source in SOURCES]
    lookup = {
        (cell["record_id"], cell["dimension"], cell["source"]): cell for cell in cells
    }
    color_value = {"green": 0, "red": 1, "amber": 2, "grey": 3}
    matrix = [
        [color_value[lookup[(record_id, dimension, source)]["cell_color"]]
         for dimension, source in columns]
        for record_id in record_ids
    ]
    cmap = ListedColormap([COLORS[name] for name in ("green", "red", "amber", "grey")])
    fig, ax = plt.subplots(figsize=(22, 9.5), constrained_layout=True)
    ax.imshow(matrix, cmap=cmap, vmin=-0.5, vmax=3.5, aspect="auto")
    labels = [
        f"{'Domains' if dimension == 'Research Domains' else 'Purposes'}\n{source}"
        for dimension, source in columns
    ]
    ax.set_xticks(range(10), labels=labels)
    ax.set_yticks(range(10), labels=record_ids)
    ax.tick_params(axis="x", labelsize=10)
    ax.tick_params(axis="y", labelsize=10)
    for index, (_, source) in enumerate(columns):
        if source in MODELS:
            ax.get_xticklabels()[index].set_bbox(
                {"facecolor": "#EEEEEE", "edgecolor": "#777777", "pad": 3.0}
            )
            ax.get_xticklabels()[index].set_fontweight("bold")
    ax.set_xlabel("Classification dimension and source", fontweight="bold")
    ax.set_ylabel("Pilot Record ID", fontweight="bold")
    ax.set_title(
        "Restricted pilot diagnostic: independent human and stored model classifications",
        fontsize=15,
        fontweight="bold",
        pad=18,
    )
    ax.set_xticks([value - 0.5 for value in range(1, 10)], minor=True)
    ax.set_yticks([value - 0.5 for value in range(1, 10)], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.axvline(4.5, color="#222222", linewidth=3.0)
    for boundary in (2.5, 7.5):
        ax.axvline(boundary, color="#555555", linewidth=1.6, linestyle="--")
    for row_index, record_id in enumerate(record_ids):
        for column_index, (dimension, source) in enumerate(columns):
            cell = lookup[(record_id, dimension, source)]
            text = cell["display"]
            if cell["annotation"]:
                text += f"\n{cell['annotation']}"
            ax.text(
                column_index,
                row_index,
                text,
                ha="center",
                va="center",
                fontsize=7.4,
                fontweight="semibold",
                color="#111111",
            )
    ax.legend(
        handles=[
            Patch(facecolor=COLORS["green"], label="Exact agreement with human pattern"),
            Patch(facecolor=COLORS["red"], label="Difference from human complete-set majority"),
            Patch(facecolor=COLORS["amber"], label="All human sets distinct / no majority"),
            Patch(facecolor=COLORS["grey"], label="Missing verified value"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=4,
        frameon=False,
        fontsize=9.5,
    )
    fig.text(
        0.5,
        0.01,
        "Restricted exploratory comparison — colour indicates agreement structure, not correctness or accuracy.",
        ha="center",
        fontsize=10,
        color="#444444",
    )
    fig.savefig(output_path, dpi=210, facecolor="white", metadata={"Software": "matplotlib"})
    plt.close(fig)


def legend_text(
    provenance: Sequence[SourceProvenance],
    *,
    pilot_pointer: str,
) -> str:
    source_lines = []
    for item in provenance:
        source_lines.append(
            f"- **{item.source}:** `{item.path.as_posix()}`; SHA-256 "
            f"`{item.sha256}`; model `{item.model_identifier}`; run "
            f"`{item.run_identifier}`; prompt/taxonomy `{item.prompt_version}` / "
            f"`{item.taxonomy_version}`; {item.rows} rows; Record ID field "
            f"`{item.record_id_field}`; Domain/Purpose fields `{item.domain_field}` / "
            f"`{item.purpose_field}`; {item.decoding}."
        )
    return f"""# Restricted human-model pilot heatmap legend

Status: **private/restricted second-stage unmasked analysis**. The initial
source-masked human-only analysis remains the primary pilot agreement analysis.
Do not copy these outputs into the shared pilot-analysis package.

Rows are the ten pilot Record IDs. Columns are C01, C02, C03, Fable and GPT-5.5
within Research Domains and Analytical Purposes. The bold grey-backed column
headers mark model sources; the cell colours retain one semantic scale.

## Colour rules

- **Human cells:** green means all humans agree or the coder belongs to the
  matching pair; red identifies the lone different complete set; amber means all
  three complete sets differ.
- **Model cells with a human complete-set majority:** green means exact set
  agreement with the human majority and red means a different complete set.
- **Model cells without a human complete-set majority:** amber preserves the
  human split. `=C01`, `=C02` or `=C03` records an exact coder-set match; `unique`
  means the model set exactly matches none of the three.
- **Grey:** a verified value is unavailable. The builder fails before output for
  missing, duplicate, invalid or taxonomy-incompatible stored model rows.

Green means exact agreement, not correctness. Red means difference from a human
complete-set majority, not model error. Amber does not create a majority. Model
agreement cannot independently validate a coder's interpretation and neither
model is treated as a reference standard.

The ten pilot records are not a probability sample. These exploratory summaries
support no coder-accuracy estimate, model-performance estimate, release decision,
or register-wide inference.

## Verified local sources

- Pilot production pointer: `{pilot_pointer}`.
{chr(10).join(source_lines)}
"""


def build_outputs(
    *,
    ready_path: Path,
    agreement_path: Path,
    pilot_raw_path: Path,
    fable_path: Path,
    fable_metadata_path: Path,
    gpt55_path: Path,
    gpt55_metadata_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    validate_private_output_path(output_dir)
    record_ids, human, patterns = load_human_rows(
        _read_csv(ready_path), _read_csv(agreement_path)
    )
    pilot_pointer, pilot_taxonomy = verify_pilot_taxonomy_pointer(
        pilot_raw_path, set(record_ids)
    )
    fable_sets, fable_count = load_model_rows(
        fable_path, source="Fable", expected_record_ids=set(record_ids)
    )
    gpt_sets, gpt_count = load_model_rows(
        gpt55_path, source="GPT-5.5", expected_record_ids=set(record_ids)
    )
    fable_meta = verify_model_metadata(
        fable_metadata_path,
        source="Fable",
        expected_taxonomy=pilot_taxonomy,
        row_count=fable_count,
    )
    gpt_meta = verify_model_metadata(
        gpt55_metadata_path,
        source="GPT-5.5",
        expected_taxonomy=pilot_taxonomy,
        row_count=gpt_count,
    )
    provenance = (
        SourceProvenance(
            "Fable", fable_path.relative_to(REPOSITORY_ROOT), _sha256(fable_path),
            str(fable_meta["model"]), str(fable_meta["run_type"]),
            str(fable_meta["prompt_version"]), str(fable_meta["taxonomy_version"]),
            fable_count,
        ),
        SourceProvenance(
            "GPT-5.5", gpt55_path.relative_to(REPOSITORY_ROOT), _sha256(gpt55_path),
            str(gpt_meta["model"]), str(gpt_meta["run_type"]),
            str(gpt_meta["prompt_version"]), str(gpt_meta["taxonomy_version"]),
            gpt_count,
        ),
    )
    joined = build_joined_rows(
        record_ids, human, patterns, {"Fable": fable_sets, "GPT-5.5": gpt_sets}
    )
    cells = build_heatmap_cells(joined)
    summary = build_comparison_summary(joined)
    disagreements = build_disagreement_rows(joined)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "pilot_human_model_classifications.csv", JOIN_COLUMNS, joined)
    _write_csv(
        output_dir / "pilot_human_model_comparison_summary.csv",
        SUMMARY_COLUMNS,
        summary,
    )
    _write_csv(
        output_dir / "pilot_model_alignment_with_human_disagreements.csv",
        DISAGREEMENT_COLUMNS,
        disagreements,
    )
    render_heatmap(cells, output_dir / "pilot_human_model_expanded_heatmap.png")
    (output_dir / "pilot_human_model_heatmap_legend.md").write_text(
        legend_text(provenance, pilot_pointer=pilot_pointer), encoding="utf-8"
    )
    return {
        "record_ids": record_ids,
        "joined_rows": len(joined),
        "heatmap_cells": len(cells),
        "summary_rows": len(summary),
        "disagreement_rows": len(disagreements),
        "provenance": provenance,
    }


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready", type=Path, default=DEFAULT_READY)
    parser.add_argument("--agreement", type=Path, default=DEFAULT_AGREEMENT)
    parser.add_argument("--pilot-raw", type=Path, default=DEFAULT_PILOT_RAW)
    parser.add_argument("--fable", type=Path, default=DEFAULT_FABLE)
    parser.add_argument("--fable-metadata", type=Path, default=DEFAULT_FABLE_METADATA)
    parser.add_argument("--gpt55", type=Path, default=DEFAULT_GPT55)
    parser.add_argument("--gpt55-metadata", type=Path, default=DEFAULT_GPT55_METADATA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = build_outputs(
            ready_path=_resolve(args.ready),
            agreement_path=_resolve(args.agreement),
            pilot_raw_path=_resolve(args.pilot_raw),
            fable_path=_resolve(args.fable),
            fable_metadata_path=_resolve(args.fable_metadata),
            gpt55_path=_resolve(args.gpt55),
            gpt55_metadata_path=_resolve(args.gpt55_metadata),
            output_dir=_resolve(args.output_dir),
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError, HumanModelHeatmapError) as exc:
        print(f"private human-model heatmap error: {exc}")
        return 2
    print(
        "Restricted human-model pilot outputs written: "
        f"{len(result['record_ids'])} records, {result['heatmap_cells']} heatmap cells"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
