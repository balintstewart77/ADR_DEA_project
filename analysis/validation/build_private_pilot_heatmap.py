"""Build the restricted coder-expanded pilot agreement heatmap.

This module reads only existing source-masked pilot-analysis tables and writes
coder-specific outputs exclusively below ``preregistration_restricted``.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = Path("preregistration/package/05_training_and_pilot/pilot_analysis")
DEFAULT_OUTPUT_DIR = Path("preregistration_restricted/pilot_private_review")
CODERS = ("C01", "C02", "C03")
COLORS = {"green": "#5AAE61", "red": "#D6604D", "amber": "#F6C85F"}
DIMENSIONS = (
    ("Domains", "Research Domains", "complete_set", "research_domains"),
    ("Purposes", "Analytical Purposes", "complete_set", "analytical_purposes"),
    ("Sufficiency", "Register sufficiency", "categorical", "register_sufficiency"),
    ("TaxonomyFit", "Taxonomy fit", "categorical", "taxonomy_fit"),
    ("Confidence", "Confidence", "categorical", "confidence"),
)
LONG_COLUMNS = (
    "record_id", "dimension", "coder_id", "coder_value_display",
    "agreement_state", "cell_color", "comparison_rule", "all_agree_flag",
    "two_vs_one_flag", "split_flag",
)
DOMAIN_ABBREVIATIONS = {
    "Labour Market & Employment": "Lab",
    "Education & Skills": "Edu",
    "Health & Social Care": "Health",
    "Crime & Justice": "Crime",
    "Business & Productivity": "Business",
    "Poverty, Wealth & Living Standards": "Poverty",
    "Housing & Planning": "Housing",
    "Migration & Demographics": "Migration",
    "Environment & Agriculture": "Env",
    "Public Finance & Taxation": "PublicFin",
    "Data Infrastructure & Methodology": "Data",
    "Unclear from Register Entry": "Unclear",
}
PURPOSE_ABBREVIATIONS = {
    "Descriptive Monitoring": "Desc",
    "Outcome Tracking": "Outcome",
    "Life-Course / Trajectory Analysis": "Traj",
    "Service Interaction / Systems Analysis": "Systems",
    "Policy Evaluation / Impact Analysis": "Eval",
    "Risk Prediction / Early Identification": "Risk",
    "Methodological / Infrastructure Research": "Methods",
    "Unclear from Register Entry": "Unclear",
}
CATEGORICAL_ABBREVIATIONS = {
    "Sufficient": "S",
    "Partially sufficient": "P",
    "Insufficient": "I",
    "Fit": "Fit",
    "Partial Fit": "Part",
    "No Fit": "No",
    "Cannot assess from register entry": "CA",
    "High": "H",
    "Medium": "M",
    "Low": "L",
}


class PrivateHeatmapError(RuntimeError):
    """Raised when inputs or output paths violate the restricted heatmap contract."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def validate_private_output_path(output_dir: Path) -> None:
    if "preregistration_restricted" not in {part.lower() for part in output_dir.resolve().parts}:
        raise PrivateHeatmapError("Coder-expanded outputs must be under preregistration_restricted")


def _ready_by_record(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, Mapping[str, str]]]:
    grouped: dict[str, dict[str, Mapping[str, str]]] = defaultdict(dict)
    for row in rows:
        record_id, coder_id = row["record_id"], row["coder_id"]
        if coder_id not in CODERS:
            raise PrivateHeatmapError(f"Unexpected coder ID: {coder_id}")
        if coder_id in grouped[record_id]:
            raise PrivateHeatmapError(f"Duplicate coder-record response: {record_id}/{coder_id}")
        grouped[record_id][coder_id] = row
    for record_id, coder_rows in grouped.items():
        if set(coder_rows) != set(CODERS):
            raise PrivateHeatmapError(f"Incomplete coder matrix for {record_id}")
    return dict(grouped)


def classify_coder_cells(
    values: Mapping[str, str], overall_pattern: str
) -> dict[str, tuple[str, str]]:
    """Return ``agreement_state, color`` for each coder under the supplied pattern."""

    if set(values) != set(CODERS) or any(not values[coder] for coder in CODERS):
        raise PrivateHeatmapError("Exactly three non-empty canonical coder values are required")
    if overall_pattern in {"unanimous", "all_agree"}:
        if len(set(values.values())) != 1:
            raise PrivateHeatmapError("All-agree pattern conflicts with coder values")
        return {coder: ("majority_match", "green") for coder in CODERS}
    if overall_pattern == "two_vs_one":
        counts = Counter(values.values())
        if sorted(counts.values()) != [1, 2]:
            raise PrivateHeatmapError("Two-versus-one pattern conflicts with coder values")
        majority_value = next(value for value, count in counts.items() if count == 2)
        return {
            coder: (
                ("majority_match", "green")
                if values[coder] == majority_value
                else ("lone_dissenter", "red")
            )
            for coder in CODERS
        }
    if overall_pattern in {"all_sets_distinct", "split"}:
        if len(set(values.values())) != 3:
            raise PrivateHeatmapError("Split pattern conflicts with coder values")
        return {coder: ("split_all_different", "amber") for coder in CODERS}
    raise PrivateHeatmapError(f"Unknown overall agreement pattern: {overall_pattern}")


def _set_display(value: str, abbreviations: Mapping[str, str]) -> str:
    labels = [part.strip() for part in value.split(" | ") if part.strip()]
    try:
        return "|".join(abbreviations[label] for label in labels)
    except KeyError as exc:
        raise PrivateHeatmapError(f"No display abbreviation for {exc.args[0]!r}") from exc


def display_value(dimension: str, value: str) -> str:
    if dimension == "Domains":
        return _set_display(value, DOMAIN_ABBREVIATIONS)
    if dimension == "Purposes":
        return _set_display(value, PURPOSE_ABBREVIATIONS)
    try:
        return CATEGORICAL_ABBREVIATIONS[value]
    except KeyError as exc:
        raise PrivateHeatmapError(f"No categorical display abbreviation for {value!r}") from exc


def build_expanded_rows(
    record_agreement_rows: Sequence[Mapping[str, str]],
    ready_rows: Sequence[Mapping[str, str]],
    dimension_summary_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, object]]:
    ready = _ready_by_record(ready_rows)
    set_rows = {
        (row["record_id"], row["classification_dimension"]): row
        for row in record_agreement_rows
    }
    summary = {
        (row["record_id"], row["dimension"]): row
        for row in dimension_summary_rows
    }
    output: list[dict[str, object]] = []
    for record_id in sorted(ready):
        for short_dimension, summary_dimension, rule, ready_field in DIMENSIONS:
            try:
                summary_row = summary[(record_id, summary_dimension)]
            except KeyError as exc:
                raise PrivateHeatmapError(
                    f"Missing dimension summary for {record_id}/{summary_dimension}"
                ) from exc
            pattern = summary_row["agreement_pattern"]
            if rule == "complete_set":
                try:
                    source = set_rows[(record_id, summary_dimension)]
                except KeyError as exc:
                    raise PrivateHeatmapError(
                        f"Missing complete-set row for {record_id}/{summary_dimension}"
                    ) from exc
                if source["complete_set_pattern"] != pattern:
                    raise PrivateHeatmapError(
                        f"Set pattern mismatch for {record_id}/{summary_dimension}"
                    )
                values = {coder: source[f"{coder}_set"] for coder in CODERS}
            else:
                values = {coder: ready[record_id][coder][ready_field] for coder in CODERS}
            states = classify_coder_cells(values, pattern)
            all_agree = pattern in {"unanimous", "all_agree"}
            two_vs_one = pattern == "two_vs_one"
            split = pattern in {"all_sets_distinct", "split"}
            for coder in CODERS:
                state, color = states[coder]
                output.append({
                    "record_id": record_id,
                    "dimension": short_dimension,
                    "coder_id": coder,
                    "coder_value_display": display_value(short_dimension, values[coder]),
                    "agreement_state": state,
                    "cell_color": color,
                    "comparison_rule": rule,
                    "all_agree_flag": int(all_agree),
                    "two_vs_one_flag": int(two_vs_one),
                    "split_flag": int(split),
                })
    return output


def expanded_column_names() -> list[str]:
    return [f"{dimension}_{coder}" for dimension, _, _, _ in DIMENSIONS for coder in CODERS]


def validate_expanded_matrix(rows: Sequence[Mapping[str, object]]) -> tuple[list[str], list[str]]:
    record_ids = sorted({str(row["record_id"]) for row in rows})
    columns = expanded_column_names()
    if len(record_ids) != 10:
        raise PrivateHeatmapError(f"Expected exactly 10 Record IDs; found {len(record_ids)}")
    if len(columns) != 15:
        raise PrivateHeatmapError(f"Expected exactly 15 expanded columns; found {len(columns)}")
    if len(rows) != 150:
        raise PrivateHeatmapError(f"Expected exactly 150 classified cells; found {len(rows)}")
    counts = Counter(
        (str(row["record_id"]), f"{row['dimension']}_{row['coder_id']}") for row in rows
    )
    missing = [
        (record_id, column) for record_id in record_ids for column in columns
        if counts[(record_id, column)] != 1
    ]
    if missing:
        raise PrivateHeatmapError(f"Missing or duplicate expanded cells: {missing}")
    if any(str(row["cell_color"]) not in COLORS for row in rows):
        raise PrivateHeatmapError("Every cell must be assigned green, red, or amber")
    if any(
        sum(int(row[field]) for field in ("all_agree_flag", "two_vs_one_flag", "split_flag")) != 1
        for row in rows
    ):
        raise PrivateHeatmapError("Every cell must have exactly one overall agreement flag")
    if any(str(row["dimension"]).lower().startswith("tag") for row in rows):
        raise PrivateHeatmapError("Tag columns are intentionally excluded")
    return record_ids, columns


def build_wide_rows(rows: Sequence[Mapping[str, object]]) -> tuple[list[str], list[dict[str, object]]]:
    record_ids, columns = validate_expanded_matrix(rows)
    lookup = {
        (str(row["record_id"]), f"{row['dimension']}_{row['coder_id']}"): row
        for row in rows
    }
    headers = ["record_id"]
    for column in columns:
        headers.extend((f"{column}_state", f"{column}_value"))
    wide: list[dict[str, object]] = []
    for record_id in record_ids:
        output: dict[str, object] = {"record_id": record_id}
        for column in columns:
            row = lookup[(record_id, column)]
            output[f"{column}_state"] = row["agreement_state"]
            output[f"{column}_value"] = row["coder_value_display"]
        wide.append(output)
    return headers, wide


def render_heatmap(rows: Sequence[Mapping[str, object]], output_path: Path) -> None:
    record_ids, columns = validate_expanded_matrix(rows)
    lookup = {
        (str(row["record_id"]), f"{row['dimension']}_{row['coder_id']}"): row
        for row in rows
    }
    color_value = {"green": 0, "red": 1, "amber": 2}
    matrix = [
        [color_value[str(lookup[(record_id, column)]["cell_color"])] for column in columns]
        for record_id in record_ids
    ]
    labels = [
        [str(lookup[(record_id, column)]["coder_value_display"]) for column in columns]
        for record_id in record_ids
    ]
    cmap = ListedColormap([COLORS["green"], COLORS["red"], COLORS["amber"]])
    fig, ax = plt.subplots(figsize=(23.5, 9.5), constrained_layout=True)
    ax.imshow(matrix, cmap=cmap, vmin=-0.5, vmax=2.5, aspect="auto")
    ax.set_xticks(range(len(columns)), labels=[column.replace("_", "\n") for column in columns])
    ax.set_yticks(range(len(record_ids)), labels=record_ids)
    ax.tick_params(axis="x", labelsize=9)
    ax.tick_params(axis="y", labelsize=10)
    ax.set_xlabel("Dimension and coder", fontweight="bold")
    ax.set_ylabel("Pilot Record ID", fontweight="bold")
    ax.set_title(
        "Restricted pilot diagnostic heatmap: coder-level agreement structure by record and dimension",
        fontsize=15, fontweight="bold", pad=18,
    )
    ax.set_xticks([value - 0.5 for value in range(1, len(columns))], minor=True)
    ax.set_yticks([value - 0.5 for value in range(1, len(record_ids))], minor=True)
    ax.grid(which="minor", color="white", linewidth=1.4)
    ax.tick_params(which="minor", bottom=False, left=False)
    for boundary in (2.5, 5.5, 8.5, 11.5):
        ax.axvline(boundary, color="#333333", linewidth=2.1)
    for row_index, row_labels in enumerate(labels):
        for column_index, label in enumerate(row_labels):
            ax.text(
                column_index, row_index, label,
                ha="center", va="center", fontsize=7.5, fontweight="semibold",
                color="#111111",
            )
    ax.legend(
        handles=[
            Patch(facecolor=COLORS["green"], label="Agrees with majority / agreeing pair"),
            Patch(facecolor=COLORS["red"], label="Lone dissenter"),
            Patch(facecolor=COLORS["amber"], label="All three differ / split"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3,
        frameon=False, fontsize=10,
    )
    fig.text(
        0.5, 0.01,
        "Restricted internal diagnostic only — descriptive pilot structure, not a formal coder-performance score.",
        ha="center", fontsize=10, color="#444444",
    )
    fig.savefig(output_path, dpi=210, facecolor="white", metadata={"Software": "matplotlib"})
    plt.close(fig)


def legend_text() -> str:
    return """# Restricted coder-expanded pilot heatmap legend

Status: **private/restricted internal diagnostic**. Do not copy this visual or
its coder-specific tables into the shared pilot-analysis package.

Rows are the 10 pilot Record IDs. Columns are C01, C02 and C03 within each of
five dimensions: Research Domains, Analytical Purposes, register sufficiency,
taxonomy fit, and confidence. The two unanimously agreed binary tags are omitted
to avoid clutter.

## Cell colours

- **Green — majority match.** The coder agrees with both other coders, or belongs
  to the matching pair in a two-versus-one pattern.
- **Red — lone dissenter.** The other two coders selected an identical complete
  set or categorical response and this coder differed.
- **Amber — all three differ.** Every complete set or categorical response is
  different, so there is no agreeing pair and no majority.

Domains and Purposes use **complete-set agreement**: the cell colour does not use
the richer labelwise two-of-three aggregation. Sufficiency, taxonomy fit and
confidence use exact categorical equality and the existing majority/split state.

Cell text is a deterministic abbreviation of the coder's actual value. This
visual describes agreement structure in a 10-record instrument pilot. It is not
a formal accuracy measure, coder score, ranking, or adjudication decision.
"""


def build_outputs(input_dir: Path, output_dir: Path) -> None:
    validate_private_output_path(output_dir)
    record_rows = _read_csv(input_dir / "pilot_record_agreement.csv")
    ready_rows = _read_csv(input_dir / "pilot_analysis_ready.csv")
    dimension_rows = _read_csv(input_dir / "pilot_record_dimension_summary.csv")
    rows = build_expanded_rows(record_rows, ready_rows, dimension_rows)
    validate_expanded_matrix(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "pilot_coder_expanded_heatmap.csv", LONG_COLUMNS, rows)
    headers, wide_rows = build_wide_rows(rows)
    _write_csv(output_dir / "pilot_coder_expanded_heatmap_wide.csv", headers, wide_rows)
    render_heatmap(rows, output_dir / "pilot_coder_expanded_heatmap.png")
    (output_dir / "pilot_coder_expanded_heatmap_legend.md").write_text(
        legend_text(), encoding="utf-8"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    input_dir = args.input_dir if args.input_dir.is_absolute() else REPOSITORY_ROOT / args.input_dir
    output_dir = args.output_dir if args.output_dir.is_absolute() else REPOSITORY_ROOT / args.output_dir
    try:
        build_outputs(input_dir, output_dir)
    except (OSError, ValueError, PrivateHeatmapError) as exc:
        print(f"private pilot heatmap error: {exc}")
        return 2
    print(f"Restricted coder-expanded heatmap written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
