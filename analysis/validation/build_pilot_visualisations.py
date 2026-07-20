"""Build neutral pilot agreement visuals and restricted coder summaries.

The shared outputs contain only record-level agreement patterns. Coder-specific
divergence is written exclusively below the caller-supplied restricted path.
No raw notes, model labels, instructor readings, or debrief materials are used.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHARED_DIR = Path("preregistration/package/05_training_and_pilot/pilot_analysis")
DEFAULT_PRIVATE_DIR = Path("preregistration_restricted/pilot_private_review")
CODERS = ("C01", "C02", "C03")
PAIRS = (("C01", "C02"), ("C01", "C03"), ("C02", "C03"))
DIMENSIONS = (
    ("Research Domains", "Domains", "set"),
    ("Analytical Purposes", "Purposes", "set"),
    ("Tag: Demographic disparities / equality", "Equity tag", "binary_tag"),
    ("Tag: COVID-19 / pandemic", "COVID tag", "binary_tag"),
    ("Register sufficiency", "Sufficiency", "categorical"),
    ("Taxonomy fit", "Taxonomy fit", "categorical"),
    ("Confidence", "Confidence", "categorical"),
)
HEATMAP_COLORS = {
    "all_agree": "#5AAE61",
    "two_vs_one": "#F6C85F",
    "split": "#D6604D",
}
READY_FIELDS = {
    "Tag: Demographic disparities / equality": "equity_tag",
    "Tag: COVID-19 / pandemic": "covid_tag",
    "Register sufficiency": "register_sufficiency",
    "Taxonomy fit": "taxonomy_fit",
    "Confidence": "confidence",
}
SHARED_COLUMNS = (
    "record_id", "dimension", "dimension_type", "agreement_pattern",
    "all_agree_flag", "two_vs_one_flag", "split_flag", "pairwise_exact_count",
    "mean_pairwise_jaccard", "majority_category", "notes_for_interpretation",
)
PRIVATE_COLUMNS = (
    "coder_id", "domain_lone_dissenter_count", "purpose_lone_dissenter_count",
    "sufficiency_lone_dissenter_count", "taxonomy_fit_lone_dissenter_count",
    "confidence_lone_dissenter_count", "domain_mean_jaccard_to_others",
    "purpose_mean_jaccard_to_others", "domain_exact_agreement_rate_to_others",
    "purpose_exact_agreement_rate_to_others", "low_confidence_count", "note_count",
    "cannot_assess_count", "unclear_from_register_count",
)


class PilotVisualisationError(RuntimeError):
    """Raised when inputs or output separation violate the visualisation contract."""


@dataclass(frozen=True)
class ThreeValuePattern:
    agreement_pattern: str
    all_agree: bool
    two_vs_one: bool
    split: bool
    pairwise_exact_count: int
    majority_category: str


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _label_set(value: str) -> frozenset[str]:
    return frozenset(part.strip() for part in value.split(" | ") if part.strip())


def _float(value: float) -> str:
    return f"{value:.6f}"


def classify_three_values(values: Mapping[str, str]) -> ThreeValuePattern:
    """Apply the exact categorical majority/split rule to three coder values."""

    if set(values) != set(CODERS) or any(values[coder] == "" for coder in CODERS):
        raise PilotVisualisationError("Exactly three non-empty canonical coder values are required")
    counts = Counter(values.values())
    most_common = counts.most_common()
    if most_common[0][1] == 3:
        return ThreeValuePattern("all_agree", True, False, False, 3, most_common[0][0])
    if most_common[0][1] == 2:
        return ThreeValuePattern("two_vs_one", False, True, False, 1, most_common[0][0])
    return ThreeValuePattern(
        "split", False, False, True, 0, "No majority / split judgement"
    )


def classify_binary_tag(values: Mapping[str, str]) -> ThreeValuePattern:
    if any(value not in {"0", "1"} for value in values.values()):
        raise PilotVisualisationError("Binary tag values must be 0 or 1")
    base = classify_three_values(values)
    if base.all_agree:
        pattern = "all_agree_positive" if base.majority_category == "1" else "all_agree_negative"
        category = "Positive" if base.majority_category == "1" else "Negative"
        return ThreeValuePattern(pattern, True, False, False, 3, category)
    return ThreeValuePattern(
        "two_vs_one", False, True, False, 1,
        "Positive" if base.majority_category == "1" else "Negative",
    )


def _ready_by_record(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, Mapping[str, str]]]:
    grouped: dict[str, dict[str, Mapping[str, str]]] = defaultdict(dict)
    for row in rows:
        record_id, coder_id = row["record_id"], row["coder_id"]
        if coder_id not in CODERS:
            raise PilotVisualisationError(f"Unexpected coder ID: {coder_id}")
        if coder_id in grouped[record_id]:
            raise PilotVisualisationError(f"Duplicate coder-record response: {record_id}/{coder_id}")
        grouped[record_id][coder_id] = row
    for record_id, coders in grouped.items():
        if set(coders) != set(CODERS):
            raise PilotVisualisationError(f"Incomplete coder matrix for {record_id}")
    return dict(grouped)


def build_record_dimension_summary(
    record_agreement_rows: Sequence[Mapping[str, str]],
    ready_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    ready = _ready_by_record(ready_rows)
    record_ids = sorted(ready)
    set_rows = {
        (row["record_id"], row["classification_dimension"]): row
        for row in record_agreement_rows
    }
    output: list[dict[str, object]] = []
    for record_id in record_ids:
        for dimension, _, dimension_type in DIMENSIONS:
            if dimension_type == "set":
                try:
                    source = set_rows[(record_id, dimension)]
                except KeyError as exc:
                    raise PilotVisualisationError(
                        f"Missing set-agreement row for {record_id}/{dimension}"
                    ) from exc
                pattern = source["complete_set_pattern"]
                if pattern not in {"unanimous", "two_vs_one", "all_sets_distinct"}:
                    raise PilotVisualisationError(f"Unknown set pattern: {pattern}")
                pair_exact = sum(int(source[field]) for field in (
                    "C01_C02_exact", "C01_C03_exact", "C02_C03_exact"
                ))
                mean_jaccard = mean(float(source[field]) for field in (
                    "C01_C02_jaccard", "C01_C03_jaccard", "C02_C03_jaccard"
                ))
                all_agree = pattern == "unanimous"
                two_vs_one = pattern == "two_vs_one"
                split = pattern == "all_sets_distinct"
                notes = {
                    "unanimous": "All three complete label sets are identical",
                    "two_vs_one": "Two complete label sets match and one differs",
                    "all_sets_distinct": "All three complete label sets differ pairwise",
                }[pattern]
                majority = ""
            else:
                field = READY_FIELDS[dimension]
                values = {coder: ready[record_id][coder][field] for coder in CODERS}
                classified = (
                    classify_binary_tag(values) if dimension_type == "binary_tag"
                    else classify_three_values(values)
                )
                pattern = classified.agreement_pattern
                pair_exact = classified.pairwise_exact_count
                mean_jaccard = None
                all_agree, two_vs_one, split = (
                    classified.all_agree, classified.two_vs_one, classified.split
                )
                majority = classified.majority_category
                notes = (
                    "All three coders selected the positive tag" if pattern == "all_agree_positive"
                    else "All three coders selected the negative tag" if pattern == "all_agree_negative"
                    else "All three categorical responses are identical" if pattern == "all_agree"
                    else "Two categorical responses match and one differs" if pattern == "two_vs_one"
                    else "All three categorical responses differ; no majority"
                )
            output.append({
                "record_id": record_id,
                "dimension": dimension,
                "dimension_type": dimension_type,
                "agreement_pattern": pattern,
                "all_agree_flag": int(all_agree),
                "two_vs_one_flag": int(two_vs_one),
                "split_flag": int(split),
                "pairwise_exact_count": pair_exact,
                "mean_pairwise_jaccard": "" if mean_jaccard is None else _float(mean_jaccard),
                "majority_category": majority,
                "notes_for_interpretation": notes,
            })
    return output


def validate_summary_matrix(rows: Sequence[Mapping[str, object]]) -> tuple[list[str], list[str]]:
    record_ids = sorted({str(row["record_id"]) for row in rows})
    dimensions = [item[0] for item in DIMENSIONS]
    if len(record_ids) != 10:
        raise PilotVisualisationError(f"Heatmap requires exactly 10 records; found {len(record_ids)}")
    if len(rows) != 70:
        raise PilotVisualisationError(f"Heatmap requires exactly 70 classified cells; found {len(rows)}")
    counts = Counter((str(row["record_id"]), str(row["dimension"])) for row in rows)
    missing = [
        (record_id, dimension) for record_id in record_ids for dimension in dimensions
        if counts[(record_id, dimension)] != 1
    ]
    if missing:
        raise PilotVisualisationError(f"Missing or duplicate heatmap cells: {missing}")
    if any(
        sum(int(row[field]) for field in ("all_agree_flag", "two_vs_one_flag", "split_flag")) != 1
        for row in rows
    ):
        raise PilotVisualisationError("Every heatmap cell must have exactly one agreement state")
    return record_ids, dimensions


def render_heatmap(rows: Sequence[Mapping[str, object]], output_path: Path) -> None:
    record_ids, dimensions = validate_summary_matrix(rows)
    lookup = {(str(row["record_id"]), str(row["dimension"])): row for row in rows}
    matrix: list[list[int]] = []
    annotations: list[list[str]] = []
    for record_id in record_ids:
        values: list[int] = []
        labels: list[str] = []
        for dimension in dimensions:
            row = lookup[(record_id, dimension)]
            if int(row["all_agree_flag"]):
                values.append(0)
                pattern = str(row["agreement_pattern"])
                labels.append("All +" if pattern == "all_agree_positive" else "All −" if pattern == "all_agree_negative" else "All agree")
            elif int(row["two_vs_one_flag"]):
                values.append(1)
                labels.append("2–1")
            else:
                values.append(2)
                labels.append("Split")
        matrix.append(values)
        annotations.append(labels)

    cmap = ListedColormap([
        HEATMAP_COLORS["all_agree"],
        HEATMAP_COLORS["two_vs_one"],
        HEATMAP_COLORS["split"],
    ])
    fig, ax = plt.subplots(figsize=(15.5, 9.0), constrained_layout=True)
    ax.imshow(matrix, cmap=cmap, vmin=-0.5, vmax=2.5, aspect="auto")
    ax.set_xticks(range(len(DIMENSIONS)), labels=[item[1] for item in DIMENSIONS])
    ax.set_yticks(range(len(record_ids)), labels=record_ids)
    ax.tick_params(axis="x", labelrotation=25, labelsize=10)
    ax.tick_params(axis="y", labelsize=10)
    ax.set_xlabel("Classification and diagnostic dimensions", fontweight="bold")
    ax.set_ylabel("Pilot Record ID", fontweight="bold")
    ax.set_title(
        "Three-coder pilot agreement patterns by record and dimension",
        fontsize=16, fontweight="bold", pad=18,
    )
    ax.set_xticks([value - 0.5 for value in range(1, len(DIMENSIONS))], minor=True)
    ax.set_yticks([value - 0.5 for value in range(1, len(record_ids))], minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)
    for row_index, labels in enumerate(annotations):
        for column_index, label in enumerate(labels):
            ax.text(
                column_index, row_index, label,
                ha="center", va="center", fontsize=9, fontweight="semibold",
                color="#1A1A1A",
            )
    ax.legend(
        handles=[
            Patch(facecolor=HEATMAP_COLORS["all_agree"], label="All three agree"),
            Patch(facecolor=HEATMAP_COLORS["two_vs_one"], label="Two agree, one differs"),
            Patch(facecolor=HEATMAP_COLORS["split"], label="All differ / no majority"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3,
        frameon=False, fontsize=10,
    )
    fig.text(
        0.5, 0.01,
        "Descriptive instrument pilot: highlights difficult records and dimensions; not a coder-performance ranking.",
        ha="center", fontsize=10, color="#444444",
    )
    fig.savefig(output_path, dpi=220, facecolor="white", metadata={"Software": "matplotlib"})
    plt.close(fig)


def _lone_dissenter(values: Mapping[str, object]) -> str | None:
    grouped: defaultdict[object, list[str]] = defaultdict(list)
    for coder, value in values.items():
        grouped[value].append(coder)
    sizes = sorted(len(coders) for coders in grouped.values())
    if sizes != [1, 2]:
        return None
    return next(coders[0] for coders in grouped.values() if len(coders) == 1)


def build_private_coder_summary(
    record_agreement_rows: Sequence[Mapping[str, str]],
    ready_rows: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    ready = _ready_by_record(ready_rows)
    set_rows = {
        (row["record_id"], row["classification_dimension"]): row
        for row in record_agreement_rows
    }
    lone_counts: dict[str, Counter[str]] = {coder: Counter() for coder in CODERS}
    jaccards: dict[str, defaultdict[str, list[float]]] = {
        coder: defaultdict(list) for coder in CODERS
    }
    exacts: dict[str, defaultdict[str, list[int]]] = {
        coder: defaultdict(list) for coder in CODERS
    }
    pair_alignment: dict[tuple[str, str], list[float]] = {pair: [] for pair in PAIRS}

    for (record_id, dimension), row in sorted(set_rows.items()):
        key = "domain" if dimension == "Research Domains" else "purpose"
        values = {coder: row[f"{coder}_set"] for coder in CODERS}
        dissenter = _lone_dissenter(values)
        if dissenter:
            lone_counts[dissenter][key] += 1
        for left, right in PAIRS:
            pair_key = f"{left}_{right}"
            jaccard = float(row[f"{pair_key}_jaccard"])
            exact = int(row[f"{pair_key}_exact"])
            pair_alignment[(left, right)].append(jaccard)
            for coder in (left, right):
                jaccards[coder][key].append(jaccard)
                exacts[coder][key].append(exact)

    categorical_fields = {
        "sufficiency": "register_sufficiency",
        "taxonomy_fit": "taxonomy_fit",
        "confidence": "confidence",
    }
    disagreement_records_by_coder: dict[str, set[str]] = {coder: set() for coder in CODERS}
    for record_id, records in ready.items():
        for key, field in categorical_fields.items():
            dissenter = _lone_dissenter({coder: records[coder][field] for coder in CODERS})
            if dissenter:
                lone_counts[dissenter][key] += 1
                disagreement_records_by_coder[dissenter].add(record_id)
        for dimension, key in (("Research Domains", "domain"), ("Analytical Purposes", "purpose")):
            row = set_rows[(record_id, dimension)]
            dissenter = _lone_dissenter({coder: row[f"{coder}_set"] for coder in CODERS})
            if dissenter:
                disagreement_records_by_coder[dissenter].add(record_id)

    output: list[dict[str, object]] = []
    low_confidence_on_divergent = 0
    total_low_confidence = 0
    for coder in CODERS:
        coder_rows = [row for row in ready_rows if row["coder_id"] == coder]
        low = [row for row in coder_rows if row["confidence"] == "Low"]
        total_low_confidence += len(low)
        low_confidence_on_divergent += sum(
            row["record_id"] in disagreement_records_by_coder[coder] for row in low
        )
        output.append({
            "coder_id": coder,
            "domain_lone_dissenter_count": lone_counts[coder]["domain"],
            "purpose_lone_dissenter_count": lone_counts[coder]["purpose"],
            "sufficiency_lone_dissenter_count": lone_counts[coder]["sufficiency"],
            "taxonomy_fit_lone_dissenter_count": lone_counts[coder]["taxonomy_fit"],
            "confidence_lone_dissenter_count": lone_counts[coder]["confidence"],
            "domain_mean_jaccard_to_others": _float(mean(jaccards[coder]["domain"])),
            "purpose_mean_jaccard_to_others": _float(mean(jaccards[coder]["purpose"])),
            "domain_exact_agreement_rate_to_others": _float(mean(exacts[coder]["domain"])),
            "purpose_exact_agreement_rate_to_others": _float(mean(exacts[coder]["purpose"])),
            "low_confidence_count": len(low),
            "note_count": sum(row["note_present"] == "1" for row in coder_rows),
            "cannot_assess_count": sum(
                row["taxonomy_fit"] == "Cannot assess from register entry" for row in coder_rows
            ),
            "unclear_from_register_count": sum(
                "Unclear from Register Entry" in (
                    _label_set(row["research_domains"]) | _label_set(row["analytical_purposes"])
                )
                for row in coder_rows
            ),
        })
    context = {
        "pair_alignment": {
            f"{left}-{right}": mean(pair_alignment[(left, right)]) for left, right in PAIRS
        },
        "lone_counts": lone_counts,
        "total_low_confidence": total_low_confidence,
        "low_confidence_on_divergent": low_confidence_on_divergent,
    }
    return output, context


def render_private_profile(
    rows: Sequence[Mapping[str, object]], context: Mapping[str, object]
) -> str:
    pair_alignment = context["pair_alignment"]
    assert isinstance(pair_alignment, dict)
    most_aligned_pair = max(pair_alignment, key=pair_alignment.get)
    lines = [
        "# Private coder-divergence profile",
        "",
        "Status: restricted internal review only. Do not place this file in the shared",
        "pilot-analysis package or use it as a group-facing coder ranking.",
        "",
        "## Descriptive patterns",
        "",
        f"- Across Domains and Purposes combined, {most_aligned_pair} had the highest mean "
        f"pairwise Jaccard ({pair_alignment[most_aligned_pair]:.3f}).",
    ]
    for row in rows:
        lone_total = sum(int(row[field]) for field in (
            "domain_lone_dissenter_count", "purpose_lone_dissenter_count",
            "sufficiency_lone_dissenter_count", "taxonomy_fit_lone_dissenter_count",
            "confidence_lone_dissenter_count",
        ))
        lines.append(
            f"- {row['coder_id']}: {lone_total} lone-dissenter instances across the two set "
            "dimensions and three categorical diagnostics; "
            f"Domains={row['domain_lone_dissenter_count']}, "
            f"Purposes={row['purpose_lone_dissenter_count']}, "
            f"Sufficiency={row['sufficiency_lone_dissenter_count']}, "
            f"Taxonomy fit={row['taxonomy_fit_lone_dissenter_count']}, "
            f"Confidence={row['confidence_lone_dissenter_count']}."
        )
    lines.extend([
        "",
        "Set-level divergence can be compared through the mean Jaccard and exact-agreement",
        "columns in the accompanying CSV. Counts describe this 10-record instrument pilot",
        "only and are not estimates of coder quality or accuracy.",
        "",
        f"Low confidence was recorded {context['total_low_confidence']} times; "
        f"{context['low_confidence_on_divergent']} of those responses were on records where "
        "that coder was the lone dissenter in at least one set or categorical dimension.",
        "This co-occurrence is descriptive and does not establish an association.",
        "",
        "`unclear_from_register_count` counts coder-record responses where either Domains or",
        "Purposes contains `Unclear from Register Entry`; a response is counted once even if",
        "both dimensions contain it.",
    ])
    return "\n".join(lines) + "\n"


def legend_text() -> str:
    return """# Pilot agreement heatmap legend

The heatmap shows seven dimensions for each of the 10 pilot Record IDs:
Research Domains, Analytical Purposes, the demographic-disparities/equality tag,
the COVID-19/pandemic tag, register sufficiency, taxonomy fit, and confidence.

## Colours and classification rules

- **Green — all three agree.** For set dimensions, all three complete label sets
  are identical. For binary tags, all three responses are positive or all three
  are negative. For categorical diagnostics, all three selected the same category.
- **Yellow — two agree and one differs.** For set dimensions, exactly two complete
  sets are identical. For tags or categorical diagnostics, two responses match
  and the third differs.
- **Red — split.** For set dimensions, all three complete sets differ pairwise.
  For categorical diagnostics, all three categories differ and there is no
  majority. A three-way binary-tag split is impossible under the stored 0/1 coding.

The labels inside the cells abbreviate these states as `All agree`, `All +`,
`All −`, `2–1`, or `Split`. Set-level `all_sets_distinct` does not imply that no
individual label has two-of-three support.

This is a descriptive instrument-pilot visual intended to highlight difficult
records and dimensions. It is not a coder-performance ranking and does not
identify or evaluate a lone dissenter.
"""


def validate_output_separation(shared_dir: Path, private_dir: Path) -> None:
    shared = shared_dir.resolve()
    private = private_dir.resolve()
    if shared == private or shared in private.parents or private in shared.parents:
        raise PilotVisualisationError("Shared and restricted output directories must be separate")
    if "preregistration_restricted" not in {part.lower() for part in private.parts}:
        raise PilotVisualisationError("Private coder outputs must be under preregistration_restricted")


def build_outputs(shared_dir: Path, private_dir: Path) -> None:
    validate_output_separation(shared_dir, private_dir)
    record_rows = _read_csv(shared_dir / "pilot_record_agreement.csv")
    ready_rows = _read_csv(shared_dir / "pilot_analysis_ready.csv")
    summary_rows = build_record_dimension_summary(record_rows, ready_rows)
    validate_summary_matrix(summary_rows)
    _write_csv(shared_dir / "pilot_record_dimension_summary.csv", SHARED_COLUMNS, summary_rows)
    render_heatmap(summary_rows, shared_dir / "pilot_heatmap_summary.png")
    (shared_dir / "pilot_heatmap_legend.md").write_text(legend_text(), encoding="utf-8")

    private_dir.mkdir(parents=True, exist_ok=True)
    private_rows, context = build_private_coder_summary(record_rows, ready_rows)
    _write_csv(private_dir / "pilot_coder_divergence_summary.csv", PRIVATE_COLUMNS, private_rows)
    (private_dir / "pilot_private_coder_profile.md").write_text(
        render_private_profile(private_rows, context), encoding="utf-8"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", type=Path, default=DEFAULT_SHARED_DIR)
    parser.add_argument("--private-dir", type=Path, default=DEFAULT_PRIVATE_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    shared = args.shared_dir if args.shared_dir.is_absolute() else REPOSITORY_ROOT / args.shared_dir
    private = args.private_dir if args.private_dir.is_absolute() else REPOSITORY_ROOT / args.private_dir
    try:
        build_outputs(shared, private)
    except (OSError, ValueError, PilotVisualisationError) as exc:
        print(f"pilot visualisation error: {exc}")
        return 2
    print(f"Shared pilot visualisations written to {shared}")
    print(f"Restricted coder summaries written to {private}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
