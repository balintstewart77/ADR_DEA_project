"""
Build per-layer agreement figures from an existing v4 comparison CSV.

The figures match each layer's label structure:
- Layer A: per-domain contested-ness table for multi-label assignments.
- Layer B: linkage-mode confusion matrix for single-label assignments.
- Layer C: purpose substitution matrix for single-purpose projects, with
  multi-purpose projects reconciled and reported separately.
"""

from __future__ import annotations

import argparse
import re
import textwrap
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle


ANALYSIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = ANALYSIS_DIR.parent
TAXONOMY_PATH = REPO_ROOT / "taxonomy_data_dictionary.yaml"

LAYER_A_DOMAIN = "Layer A -- domain"
LAYER_B_LINKAGE = "Layer B -- linkage"
LAYER_C_PURPOSE = "Layer C -- purpose"

FIELD_LAYERS = {
    "substantive_domains": LAYER_A_DOMAIN,
    "linkage_mode": LAYER_B_LINKAGE,
    "analytical_purpose": LAYER_C_PURPOSE,
}
EXPECTED_LABEL_COUNTS = {
    "substantive_domains": 13,
    "linkage_mode": 4,
    "analytical_purpose": 8,
}

NEUTRAL = "#EFEDE6"
GREEN = "#1D9E75"
RED = "#E24B4A"
DIAGONAL_BORDER = "#126C51"


@dataclass(frozen=True)
class FieldSummary:
    agreement_rate: float
    agreed_projects: int
    compared_projects: int


@dataclass(frozen=True)
class ParsedComparison:
    frame: pd.DataFrame
    run_columns: dict[str, tuple[str, str]]
    label_sets: dict[str, tuple[list[frozenset[str]], list[frozenset[str]]]]
    summary: dict[str, FieldSummary]


@dataclass(frozen=True)
class DomainStats:
    label: str
    both: int
    run_1_only: int
    run_2_only: int
    neither: int

    @property
    def disagreement(self) -> int:
        return self.run_1_only + self.run_2_only

    @property
    def union(self) -> int:
        return self.both + self.disagreement

    @property
    def contested_rate(self) -> float | None:
        if not self.union:
            return None
        return 100 * self.disagreement / self.union


@dataclass(frozen=True)
class MatrixStats:
    total: int
    diagonal: int
    agreement_rate: float
    disagreements: int
    largest_pair: str
    largest_pair_count: int


@dataclass(frozen=True)
class PurposeSplit:
    single_purpose_projects: int
    multi_purpose_projects: int
    multi_purpose_agreed: int
    multi_purpose_disagreed: int
    combined_agreed: int
    combined_rate: float


def _flatten_dictionary_text(value: object) -> str:
    """Match the classifier's treatment of YAML-folded whitespace."""
    return " ".join(str(value or "").split()).strip()


def _in_prompt_category(category: dict, layer: str) -> bool:
    """Use the same active in-prompt filter as llm_theme_analysis_v3.py."""
    status = _flatten_dictionary_text(category.get("status")).lower()
    return (
        category.get("layer") == layer
        and category.get("include_in_prompt") is True
        and not status.startswith("removed")
    )


def load_dictionary_labels() -> dict[str, list[str]]:
    with TAXONOMY_PATH.open(encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)
    if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get("categories"), list):
        raise ValueError(f"{TAXONOMY_PATH} is missing a categories list")

    labels_by_field = {}
    for field, layer in FIELD_LAYERS.items():
        labels = [
            category["label"]
            for category in taxonomy["categories"]
            if isinstance(category, dict) and _in_prompt_category(category, layer)
        ]
        if any(not isinstance(label, str) or not label.strip() for label in labels):
            raise ValueError(f"{TAXONOMY_PATH} has invalid active labels for {layer}")
        expected_count = EXPECTED_LABEL_COUNTS[field]
        if len(labels) != expected_count:
            raise ValueError(
                f"{TAXONOMY_PATH} resolved {len(labels)} labels for {layer}; "
                f"expected {expected_count}"
            )
        if len(labels) != len(set(labels)):
            raise ValueError(f"{TAXONOMY_PATH} has duplicate active labels for {layer}")
        labels_by_field[field] = labels
    return labels_by_field


def _clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _field_run_columns(columns: list[str], field: str) -> tuple[str, str]:
    agree_column = f"{field}_agree"
    matches = [
        column
        for column in columns
        if column.startswith(f"{field}_") and column != agree_column
    ]
    if len(matches) != 2:
        raise ValueError(f"Expected exactly two run-label columns for {field}, found {matches}")
    return matches[0], matches[1]


def _parse_labels(
    value: object,
    *,
    allowed_labels: set[str],
    field: str,
    record_id: str,
    single_label: bool,
) -> frozenset[str]:
    text = _clean_cell(value)
    labels = [part.strip() for part in text.split(";") if part.strip()]
    if not labels:
        raise ValueError(f"{record_id}: {field} has no assigned label")
    if single_label and len(labels) != 1:
        raise ValueError(f"{record_id}: {field} expected one label, found {labels}")
    unknown = sorted(set(labels) - allowed_labels)
    if unknown:
        raise ValueError(f"{record_id}: {field} contains unknown or retired labels: {unknown}")
    return frozenset(labels)


def _as_bool(value: object, *, column: str, record_id: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = _clean_cell(value).lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"{record_id}: {column} is not a boolean: {value!r}")


SUMMARY_ROW_RE = re.compile(
    r"^\|\s*(substantive_domains|linkage_mode|analytical_purpose|cross_cutting_tags)"
    r"\s*\|\s*([0-9.]+)%\s*\|\s*([0-9,]+)\s*\|\s*([0-9,]+)\s*\|$"
)


def read_summary(summary_path: Path) -> dict[str, FieldSummary]:
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    summaries = {}
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        match = SUMMARY_ROW_RE.match(line)
        if not match:
            continue
        field, rate, agreed, compared = match.groups()
        summaries[field] = FieldSummary(
            agreement_rate=float(rate),
            agreed_projects=int(agreed.replace(",", "")),
            compared_projects=int(compared.replace(",", "")),
        )
    missing = set(FIELD_LAYERS) - set(summaries)
    if missing:
        raise ValueError(f"{summary_path} is missing summary rows for: {sorted(missing)}")
    return summaries


def read_comparison(
    comparison_dir: Path,
    labels_by_field: dict[str, list[str]],
) -> ParsedComparison:
    csv_path = comparison_dir / "comparison_full.csv"
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    frame = pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
        dtype={"Record ID": str, "Project ID": str},
    )
    if "Record ID" not in frame.columns:
        raise ValueError(f"{csv_path} is missing Record ID")
    if frame["Record ID"].isna().any() or frame["Record ID"].duplicated().any():
        raise ValueError(f"{csv_path} must contain unique, non-empty Record ID values")

    summary = read_summary(comparison_dir / "comparison_summary.md")
    run_columns = {}
    parsed_sets = {}
    for field in FIELD_LAYERS:
        run_1_column, run_2_column = _field_run_columns(list(frame.columns), field)
        agree_column = f"{field}_agree"
        if agree_column not in frame.columns:
            raise ValueError(f"{csv_path} is missing {agree_column}")

        allowed_labels = set(labels_by_field[field])
        single_label = field == "linkage_mode"
        run_1_sets = []
        run_2_sets = []
        stored_agreement = []
        for _, row in frame.iterrows():
            record_id = str(row["Record ID"])
            run_1_sets.append(
                _parse_labels(
                    row[run_1_column],
                    allowed_labels=allowed_labels,
                    field=field,
                    record_id=record_id,
                    single_label=single_label,
                )
            )
            run_2_sets.append(
                _parse_labels(
                    row[run_2_column],
                    allowed_labels=allowed_labels,
                    field=field,
                    record_id=record_id,
                    single_label=single_label,
                )
            )
            stored_agreement.append(
                _as_bool(row[agree_column], column=agree_column, record_id=record_id)
            )

        parsed_agreement = [
            run_1 == run_2 for run_1, run_2 in zip(run_1_sets, run_2_sets)
        ]
        if parsed_agreement != stored_agreement:
            mismatch_count = sum(
                parsed != stored
                for parsed, stored in zip(parsed_agreement, stored_agreement)
            )
            raise ValueError(
                f"{field}: parsed label agreement disagrees with {agree_column} "
                f"for {mismatch_count} project(s)"
            )

        field_summary = summary[field]
        parsed_agreed_count = sum(parsed_agreement)
        calculated_rate = round(100 * parsed_agreed_count / len(frame), 1)
        if len(frame) != field_summary.compared_projects:
            raise ValueError(
                f"{field}: CSV has {len(frame)} projects but summary reports "
                f"{field_summary.compared_projects}"
            )
        if (
            parsed_agreed_count != field_summary.agreed_projects
            or calculated_rate != field_summary.agreement_rate
        ):
            raise ValueError(
                f"{field}: parsed agreement is {parsed_agreed_count}/{len(frame)} "
                f"({calculated_rate:.1f}%) but summary reports "
                f"{field_summary.agreed_projects}/{field_summary.compared_projects} "
                f"({field_summary.agreement_rate:.1f}%)"
            )

        run_columns[field] = (run_1_column, run_2_column)
        parsed_sets[field] = (run_1_sets, run_2_sets)

    return ParsedComparison(
        frame=frame,
        run_columns=run_columns,
        label_sets=parsed_sets,
        summary=summary,
    )


def calculate_domain_stats(
    comparison: ParsedComparison,
    labels: list[str],
) -> tuple[list[DomainStats], int]:
    run_1_sets, run_2_sets = comparison.label_sets["substantive_domains"]
    total = len(run_1_sets)
    stats = []
    for label in labels:
        both = run_1_only = run_2_only = neither = 0
        for run_1, run_2 in zip(run_1_sets, run_2_sets):
            in_run_1 = label in run_1
            in_run_2 = label in run_2
            if in_run_1 and in_run_2:
                both += 1
            elif in_run_1:
                run_1_only += 1
            elif in_run_2:
                run_2_only += 1
            else:
                neither += 1
        stat = DomainStats(label, both, run_1_only, run_2_only, neither)
        if stat.both + stat.run_1_only + stat.run_2_only + stat.neither != total:
            raise ValueError(f"substantive_domains: {label} counts do not sum to {total}")
        stats.append(stat)

    zero_contested_projects = sum(
        run_1 == run_2 for run_1, run_2 in zip(run_1_sets, run_2_sets)
    )
    summary = comparison.summary["substantive_domains"]
    rate = round(100 * zero_contested_projects / total, 1)
    if (
        zero_contested_projects != summary.agreed_projects
        or rate != summary.agreement_rate
    ):
        raise ValueError(
            "substantive_domains: zero-contested-domain reconciliation failed: "
            f"{zero_contested_projects}/{total} ({rate:.1f}%) vs summary "
            f"{summary.agreed_projects}/{summary.compared_projects} "
            f"({summary.agreement_rate:.1f}%)"
        )
    return stats, zero_contested_projects


def build_domain_table(
    *,
    comparison: ParsedComparison,
    comparison_dir: Path,
    comparison_label: str,
    labels: list[str],
    sort_by_disagreement: bool,
) -> tuple[list[DomainStats], int]:
    stats, zero_contested_projects = calculate_domain_stats(comparison, labels)
    if sort_by_disagreement:
        dictionary_position = {label: index for index, label in enumerate(labels)}
        stats = sorted(
            stats,
            key=lambda stat: (-stat.disagreement, dictionary_position[stat.label]),
        )

    rows = [
        [
            stat.label,
            f"{stat.both:,}",
            f"{stat.run_1_only:,}",
            f"{stat.run_2_only:,}",
            f"{stat.disagreement:,}",
            "n/a" if stat.contested_rate is None else f"{stat.contested_rate:.1f}%",
        ]
        for stat in stats
    ]
    columns = [
        "Domain",
        "Both assign",
        "Run 1 only",
        "Run 2 only",
        "Disagreement",
        "Contested rate",
    ]
    figure, axis = plt.subplots(figsize=(12.4, 6.8))
    axis.axis("off")
    table = axis.table(
        cellText=rows,
        colLabels=columns,
        colWidths=[0.43, 0.105, 0.105, 0.105, 0.125, 0.13],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.48)
    header_colours = ["#D7D4CB", "#D9EEE7", "#DCE8F5", "#F8E3D3", "#F6D8D7", "#F6EACB"]
    body_colours = ["#F8F7F3", "#E6F4EF", "#EAF1F8", "#FBEEE5", "#FBE8E7", "#FBF2DB"]
    for column in range(len(columns)):
        table[(0, column)].set_facecolor(header_colours[column])
        table[(0, column)].set_text_props(weight="bold")
    for row in range(1, len(rows) + 1):
        for column in range(len(columns)):
            table[(row, column)].set_facecolor(body_colours[column])
        table[(row, 0)].set_text_props(ha="left")
    for cell in table.get_celld().values():
        cell.set_edgecolor("#FFFFFF")
        cell.set_linewidth(1)

    sort_note = "sorted by disagreement count" if sort_by_disagreement else "dictionary order"
    figure.suptitle(
        f"Layer A: domain contested-ness - {comparison_label}",
        fontsize=14,
        weight="bold",
        y=0.97,
    )
    figure.text(
        0.035,
        0.035,
        "Contested rate = (Run 1 only + Run 2 only) / projects where either run "
        f"assigned the domain. Rows use {sort_note}.",
        fontsize=8.5,
    )
    figure.savefig(
        comparison_dir / "layer_a_domain_contested_table.png",
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(figure)
    return stats, zero_contested_projects


def _single_label(label_set: frozenset[str]) -> str:
    if len(label_set) != 1:
        raise ValueError(f"Expected one label, found {sorted(label_set)}")
    return next(iter(label_set))


def _blend_with_neutral(colour: str, strength: float) -> tuple[float, float, float]:
    neutral = np.asarray(to_rgb(NEUTRAL))
    target = np.asarray(to_rgb(colour))
    return tuple(neutral * (1 - strength) + target * strength)


def _matrix_stats(matrix: np.ndarray, labels: list[str]) -> MatrixStats:
    total = int(matrix.sum())
    diagonal = int(np.trace(matrix))
    disagreements = total - diagonal
    rate = round(100 * diagonal / total, 1) if total else 0.0
    pair_counts = [
        (
            int(matrix[left, right] + matrix[right, left]),
            labels[left],
            labels[right],
        )
        for left, right in combinations(range(len(labels)), 2)
    ]
    largest_pair_count, largest_left, largest_right = max(pair_counts)
    return MatrixStats(
        total=total,
        diagonal=diagonal,
        agreement_rate=rate,
        disagreements=disagreements,
        largest_pair=f"{largest_left} <-> {largest_right}",
        largest_pair_count=largest_pair_count,
    )


def _render_matrix(
    *,
    matrix: np.ndarray,
    labels: list[str],
    title: str,
    caption: str,
    output_path: Path,
) -> None:
    row_totals = matrix.sum(axis=1)
    row_percentages = np.divide(
        matrix * 100,
        row_totals[:, None],
        out=np.zeros_like(matrix, dtype=float),
        where=row_totals[:, None] != 0,
    )
    non_empty_rows = row_totals > 0
    if not np.allclose(row_percentages[non_empty_rows].sum(axis=1), 100):
        raise ValueError("Matrix row percentages do not sum to 100%")

    size = len(labels)
    diagonal_max = max(int(np.diag(matrix).max()), 1)
    off_diagonal_max = max(
        [
            int(matrix[row, column])
            for row in range(size)
            for column in range(size)
            if row != column
        ],
        default=1,
    )
    figure_size = (8.8, 7.2) if size <= 4 else (12.8, 10.6)
    figure, axis = plt.subplots(figsize=figure_size)
    for row in range(size):
        for column in range(size):
            value = int(matrix[row, column])
            if row == column:
                strength = 0.12 + 0.88 * value / diagonal_max
                colour = _blend_with_neutral(GREEN, strength)
            elif value:
                strength = 0.16 + 0.84 * value / off_diagonal_max
                colour = _blend_with_neutral(RED, strength)
            else:
                colour = to_rgb(NEUTRAL)
            axis.add_patch(
                Rectangle(
                    (column, row),
                    1,
                    1,
                    facecolor=colour,
                    edgecolor="white",
                    linewidth=1.2,
                )
            )
            if row == column:
                axis.add_patch(
                    Rectangle(
                        (column, row),
                        1,
                        1,
                        fill=False,
                        edgecolor=DIAGONAL_BORDER,
                        linewidth=2,
                    )
                )
            axis.text(
                column + 0.5,
                row + 0.43,
                f"{value:,}",
                ha="center",
                va="center",
                fontsize=11 if size <= 4 else 9,
                weight="bold",
            )
            row_percentage = row_percentages[row, column]
            percentage_text = f"{row_percentage:.1f}%" if row_totals[row] else "-"
            axis.text(
                column + 0.5,
                row + 0.68,
                percentage_text,
                ha="center",
                va="center",
                fontsize=8 if size <= 4 else 7,
                color="#363636",
            )

    wrapped_labels = [textwrap.fill(label, width=18) for label in labels]
    axis.set_xlim(0, size)
    axis.set_ylim(size, 0)
    axis.set_aspect("equal")
    axis.set_xticks(np.arange(size) + 0.5)
    axis.set_xticklabels(wrapped_labels, rotation=35, ha="left", fontsize=9)
    axis.xaxis.tick_top()
    axis.xaxis.set_label_position("top")
    axis.set_yticks(np.arange(size) + 0.5)
    axis.set_yticklabels(wrapped_labels, fontsize=9)
    axis.set_xlabel("Run 2 label", labelpad=12, fontsize=10, weight="bold")
    axis.set_ylabel("Run 1 label", labelpad=12, fontsize=10, weight="bold")
    axis.tick_params(axis="both", length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.suptitle(title, fontsize=14, weight="bold", y=0.98)
    figure.text(0.035, 0.045, caption, fontsize=8.5)
    figure.text(
        0.035,
        0.023,
        "Rows are conditional on Run 1 labels by convention; neither run is a "
        "ground-truth reference. Each cell shows count and row percentage.",
        fontsize=8,
    )
    figure.subplots_adjust(left=0.27 if size <= 4 else 0.22, right=0.98, top=0.80, bottom=0.14)
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)


def build_linkage_confusion(
    *,
    comparison: ParsedComparison,
    comparison_dir: Path,
    comparison_label: str,
    labels: list[str],
) -> MatrixStats:
    label_indexes = {label: index for index, label in enumerate(labels)}
    matrix = np.zeros((len(labels), len(labels)), dtype=int)
    run_1_sets, run_2_sets = comparison.label_sets["linkage_mode"]
    for run_1, run_2 in zip(run_1_sets, run_2_sets):
        matrix[
            label_indexes[_single_label(run_1)],
            label_indexes[_single_label(run_2)],
        ] += 1

    stats = _matrix_stats(matrix, labels)
    summary = comparison.summary["linkage_mode"]
    if (
        stats.total != summary.compared_projects
        or stats.diagonal != summary.agreed_projects
        or stats.agreement_rate != summary.agreement_rate
    ):
        raise ValueError(
            "linkage_mode: confusion matrix reconciliation failed: "
            f"{stats.diagonal}/{stats.total} ({stats.agreement_rate:.1f}%) vs summary "
            f"{summary.agreed_projects}/{summary.compared_projects} "
            f"({summary.agreement_rate:.1f}%)"
        )
    caption = (
        f"Overall diagonal agreement: {stats.diagonal:,}/{stats.total:,} "
        f"({stats.agreement_rate:.1f}%). Largest contested boundary: "
        f"{stats.largest_pair} accounts for {stats.largest_pair_count:,} of "
        f"{stats.disagreements:,} disagreements."
    )
    _render_matrix(
        matrix=matrix,
        labels=labels,
        title=f"Layer B: linkage-mode confusion matrix - {comparison_label}",
        caption=caption,
        output_path=comparison_dir / "layer_b_linkage_confusion.png",
    )
    return stats


def build_purpose_confusion(
    *,
    comparison: ParsedComparison,
    comparison_dir: Path,
    comparison_label: str,
    labels: list[str],
) -> tuple[MatrixStats, PurposeSplit]:
    label_indexes = {label: index for index, label in enumerate(labels)}
    matrix = np.zeros((len(labels), len(labels)), dtype=int)
    run_1_sets, run_2_sets = comparison.label_sets["analytical_purpose"]
    multi_purpose_agreed = multi_purpose_disagreed = 0
    for run_1, run_2 in zip(run_1_sets, run_2_sets):
        if len(run_1) == 1 and len(run_2) == 1:
            matrix[
                label_indexes[_single_label(run_1)],
                label_indexes[_single_label(run_2)],
            ] += 1
        elif run_1 == run_2:
            multi_purpose_agreed += 1
        else:
            multi_purpose_disagreed += 1

    matrix_stats = _matrix_stats(matrix, labels)
    multi_purpose_projects = multi_purpose_agreed + multi_purpose_disagreed
    total = len(run_1_sets)
    combined_agreed = matrix_stats.diagonal + multi_purpose_agreed
    combined_rate = round(100 * combined_agreed / total, 1)
    split = PurposeSplit(
        single_purpose_projects=matrix_stats.total,
        multi_purpose_projects=multi_purpose_projects,
        multi_purpose_agreed=multi_purpose_agreed,
        multi_purpose_disagreed=multi_purpose_disagreed,
        combined_agreed=combined_agreed,
        combined_rate=combined_rate,
    )
    summary = comparison.summary["analytical_purpose"]
    if matrix_stats.total + multi_purpose_projects != total:
        raise ValueError(
            "analytical_purpose: single-purpose matrix and multi-purpose tally "
            f"sum to {matrix_stats.total + multi_purpose_projects}, expected {total}"
        )
    if (
        combined_agreed != summary.agreed_projects
        or combined_rate != summary.agreement_rate
    ):
        raise ValueError(
            "analytical_purpose: combined reconciliation failed: "
            f"{combined_agreed}/{total} ({combined_rate:.1f}%) vs summary "
            f"{summary.agreed_projects}/{summary.compared_projects} "
            f"({summary.agreement_rate:.1f}%)"
        )

    caption = (
        f"Single-purpose matrix: {matrix_stats.total:,} projects. Multi-purpose "
        f"projects tallied separately: {multi_purpose_projects:,} "
        f"({multi_purpose_agreed:,} agreed on the full set; "
        f"{multi_purpose_disagreed:,} disagreed). Combined agreement: "
        f"{combined_agreed:,}/{total:,} ({combined_rate:.1f}%)."
    )
    _render_matrix(
        matrix=matrix,
        labels=labels,
        title=f"Layer C: purpose substitution matrix - {comparison_label}",
        caption=caption,
        output_path=comparison_dir / "layer_c_purpose_confusion.png",
    )
    return matrix_stats, split


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build dictionary-driven per-layer agreement figures"
    )
    parser.add_argument(
        "--comparison-dir",
        required=True,
        type=Path,
        help="Comparison directory containing comparison_full.csv and comparison_summary.md",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Human-readable comparison label for figure titles (defaults to directory name)",
    )
    parser.add_argument(
        "--sort-by-disagreement",
        action="store_true",
        help="Sort the Layer A table by descending disagreement instead of dictionary order",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    comparison_dir = args.comparison_dir.resolve()
    comparison_label = args.label or comparison_dir.name
    labels_by_field = load_dictionary_labels()
    comparison = read_comparison(comparison_dir, labels_by_field)

    print(f"[source] {comparison_dir / 'comparison_full.csv'}")
    print("[source] Run labels read directly from comparison_full.csv (semicolon-delimited label sets)")
    for field, columns in comparison.run_columns.items():
        print(f"[schema] {field}: {columns[0]} | {columns[1]}")
    print(
        "[dictionary] "
        f"Layer A={len(labels_by_field['substantive_domains'])}, "
        f"Layer B={len(labels_by_field['linkage_mode'])}, "
        f"Layer C={len(labels_by_field['analytical_purpose'])}"
    )

    domain_stats, zero_contested = build_domain_table(
        comparison=comparison,
        comparison_dir=comparison_dir,
        comparison_label=comparison_label,
        labels=labels_by_field["substantive_domains"],
        sort_by_disagreement=args.sort_by_disagreement,
    )
    domain_summary = comparison.summary["substantive_domains"]
    print(
        f"[check] substantive_domains: zero-contested projects={zero_contested}/"
        f"{domain_summary.compared_projects} ({domain_summary.agreement_rate:.1f}%)"
    )
    for stat in domain_stats:
        contested_rate = "n/a" if stat.contested_rate is None else f"{stat.contested_rate:.1f}%"
        print(
            f"[domain] {stat.label}: both={stat.both}, run_1_only={stat.run_1_only}, "
            f"run_2_only={stat.run_2_only}, disagreement={stat.disagreement}, "
            f"contested_rate={contested_rate}"
        )
    print(f"[output] {comparison_dir / 'layer_a_domain_contested_table.png'}")

    linkage_stats = build_linkage_confusion(
        comparison=comparison,
        comparison_dir=comparison_dir,
        comparison_label=comparison_label,
        labels=labels_by_field["linkage_mode"],
    )
    print(
        f"[check] linkage_mode: diagonal={linkage_stats.diagonal}/"
        f"{linkage_stats.total} ({linkage_stats.agreement_rate:.1f}%)"
    )
    print(
        f"[check] linkage_mode: largest off-diagonal pair="
        f"{linkage_stats.largest_pair} ({linkage_stats.largest_pair_count})"
    )
    print(f"[output] {comparison_dir / 'layer_b_linkage_confusion.png'}")

    purpose_stats, purpose_split = build_purpose_confusion(
        comparison=comparison,
        comparison_dir=comparison_dir,
        comparison_label=comparison_label,
        labels=labels_by_field["analytical_purpose"],
    )
    print(
        f"[check] analytical_purpose: single-purpose matrix={purpose_stats.total}, "
        f"multi-purpose={purpose_split.multi_purpose_projects}, "
        f"combined={purpose_stats.total + purpose_split.multi_purpose_projects}"
    )
    print(
        f"[check] analytical_purpose: combined agreement={purpose_split.combined_agreed}/"
        f"{len(comparison.frame)} ({purpose_split.combined_rate:.1f}%)"
    )
    print(
        f"[check] analytical_purpose: multi-purpose agreed="
        f"{purpose_split.multi_purpose_agreed}, disagreed="
        f"{purpose_split.multi_purpose_disagreed}"
    )
    print(f"[output] {comparison_dir / 'layer_c_purpose_confusion.png'}")


if __name__ == "__main__":
    main()
