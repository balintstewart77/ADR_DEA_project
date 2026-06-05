"""
Build side-by-side comparison artefacts for two v4 rc1 classifier runs.

By default this reproduces the Instruction 4 Opus 4.8 vs Opus 4.6 comparison.
The same script can also compare arbitrary run directories, for example the
Opus 4.8 run 1 vs run 2 intra-model replicate.
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


ANALYSIS_DIR = Path(__file__).resolve().parent
DEFAULT_RUN_A_DIR = ANALYSIS_DIR / "outputs_v4_8_rc1"
DEFAULT_RUN_B_DIR = ANALYSIS_DIR / "outputs_v4_6_rc1"
DEFAULT_OUTPUT_DIR = ANALYSIS_DIR / "outputs_comparison_v4_rc1"
DEFAULT_RUN_A_LABEL = "4.8"
DEFAULT_RUN_B_LABEL = "4.6"

META_COLUMNS = ["Record ID", "Project ID", "Title", "Datasets Used", "Year"]
LABEL_FIELDS = [
    "substantive_domains",
    "analytical_purpose",
    "cross_cutting_tags",
]
MULTI_LABEL_FIELDS = {"substantive_domains", "analytical_purpose", "cross_cutting_tags"}
RATIONALE_COLUMN = "rationale"
RATIONALE_PLACEHOLDER = "(rationale not provided)"

FIELD_LABELS = {
    "substantive_domains": "Layer A",
    "analytical_purpose": "Layer C",
    "cross_cutting_tags": "Tag",
}


@dataclass(frozen=True)
class RunSpec:
    key: str
    label: str
    suffix: str
    output_dir: Path


def _suffix_from_label(label: str) -> str:
    suffix = re.sub(r"[^0-9A-Za-z]+", "_", label.strip().lower()).strip("_")
    if not suffix:
        raise ValueError("Run labels must contain at least one alphanumeric character")
    return suffix


def _display_label(label: str) -> str:
    stripped = label.strip()
    if stripped.lower().startswith("opus "):
        return stripped
    return f"Opus {stripped}"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"Record ID": str, "Project ID": str})
    if "Record ID" not in df.columns:
        raise ValueError(f"{path} is missing Record ID")
    duplicate_ids = df["Record ID"][df["Record ID"].duplicated()].dropna().unique()
    if len(duplicate_ids):
        sample = ", ".join(map(str, duplicate_ids[:10]))
        raise ValueError(f"{path} has duplicate Record ID values, including: {sample}")
    return df


def _clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _split_labels(value: object) -> list[str]:
    text = _clean_cell(value)
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


def _label_set(value: object, field: str) -> frozenset[str]:
    if field in MULTI_LABEL_FIELDS:
        return frozenset(_split_labels(value))
    text = _clean_cell(value)
    return frozenset([text]) if text else frozenset()


def _canonical_label_string(value: object, field: str) -> str:
    labels = sorted(_label_set(value, field))
    return "; ".join(labels) if labels else "(none)"


def _prepare_model_frame(df: pd.DataFrame, suffix: str) -> pd.DataFrame:
    out = df.copy()
    for col in META_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    for field in LABEL_FIELDS:
        if field not in out.columns:
            out[field] = ""
    if RATIONALE_COLUMN not in out.columns:
        out[RATIONALE_COLUMN] = RATIONALE_PLACEHOLDER

    keep = META_COLUMNS + LABEL_FIELDS + [RATIONALE_COLUMN]
    rename = {
        col: f"{col}_{suffix}"
        for col in keep
        if col != "Record ID"
    }
    return out[keep].rename(columns=rename)


def _coalesce_columns(df: pd.DataFrame, output_col: str, left_col: str, right_col: str) -> None:
    left = df[left_col] if left_col in df else pd.Series([""] * len(df), index=df.index)
    right = df[right_col] if right_col in df else pd.Series([""] * len(df), index=df.index)
    left_clean = left.map(_clean_cell)
    right_clean = right.map(_clean_cell)
    df[output_col] = left_clean.where(left_clean != "", right_clean)


def build_comparison(df_a: pd.DataFrame, df_b: pd.DataFrame, run_a: RunSpec, run_b: RunSpec) -> pd.DataFrame:
    left = _prepare_model_frame(df_a, run_a.suffix)
    right = _prepare_model_frame(df_b, run_b.suffix)
    merged = left.merge(right, on="Record ID", how="outer", indicator=True)

    for meta in ["Project ID", "Title", "Datasets Used", "Year"]:
        _coalesce_columns(merged, meta, f"{meta}_{run_a.suffix}", f"{meta}_{run_b.suffix}")

    for field in LABEL_FIELDS:
        for run in (run_a, run_b):
            col = f"{field}_{run.suffix}"
            if col not in merged:
                merged[col] = ""
            merged[col] = merged[col].fillna("").map(_clean_cell)
        merged[f"{field}_agree"] = merged.apply(
            lambda row, f=field: (
                _label_set(row[f"{f}_{run_a.suffix}"], f)
                == _label_set(row[f"{f}_{run_b.suffix}"], f)
            ),
            axis=1,
        )

    for run in (run_a, run_b):
        col = f"{RATIONALE_COLUMN}_{run.suffix}"
        if col not in merged:
            merged[col] = RATIONALE_PLACEHOLDER
        merged[col] = merged[col].fillna(RATIONALE_PLACEHOLDER).map(_clean_cell)
        merged.loc[merged[col] == "", col] = RATIONALE_PLACEHOLDER

    def disagreement_summary(row: pd.Series) -> str:
        parts = [
            f"{FIELD_LABELS[field]} disagreed"
            for field in LABEL_FIELDS
            if not bool(row[f"{field}_agree"])
        ]
        return "; ".join(parts)

    merged["disagreement_summary"] = merged.apply(disagreement_summary, axis=1)

    output_cols = [
        "Record ID",
        "Project ID",
        "Title",
        "Datasets Used",
        "Year",
        f"substantive_domains_{run_a.suffix}",
        f"substantive_domains_{run_b.suffix}",
        "substantive_domains_agree",
        f"analytical_purpose_{run_a.suffix}",
        f"analytical_purpose_{run_b.suffix}",
        "analytical_purpose_agree",
        f"cross_cutting_tags_{run_a.suffix}",
        f"cross_cutting_tags_{run_b.suffix}",
        "cross_cutting_tags_agree",
        f"rationale_{run_a.suffix}",
        f"rationale_{run_b.suffix}",
        "disagreement_summary",
    ]
    merged = merged.sort_values("Record ID").reset_index(drop=True)
    return merged[output_cols]


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "None":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_run_log(log_path: Path) -> dict:
    telemetry = {
        "log_path": str(log_path),
        "log_exists": log_path.exists(),
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "input_tokens_observed": False,
        "output_tokens_observed": False,
        "retry_lines": [],
        "error_lines": [],
        "targeted_cache_fill_lines": [],
        "traceback": False,
        "output_saved": False,
    }
    if not log_path.exists():
        return telemetry

    field_re = re.compile(r"([A-Za-z_]*tokens)=([0-9]+|None)")
    with log_path.open(encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if "[prompt-cache]" in line:
                fields = dict(field_re.findall(line))
                creation = _parse_int(fields.get("cache_creation_input_tokens"))
                read = _parse_int(fields.get("cache_read_input_tokens"))
                if creation is not None:
                    telemetry["cache_creation_input_tokens"] += creation
                if read is not None:
                    telemetry["cache_read_input_tokens"] += read
                input_tokens = _parse_int(fields.get("input_tokens"))
                output_tokens = _parse_int(fields.get("output_tokens"))
                if input_tokens is not None:
                    telemetry["input_tokens"] += input_tokens
                    telemetry["input_tokens_observed"] = True
                if output_tokens is not None:
                    telemetry["output_tokens"] += output_tokens
                    telemetry["output_tokens_observed"] = True
            if "[retry]" in line:
                telemetry["retry_lines"].append(line)
            if "[error]" in line or "ERROR" in line:
                telemetry["error_lines"].append(line)
            if "[targeted-cache-fill]" in line:
                telemetry["targeted_cache_fill_lines"].append(line)
            if "Traceback (most recent call last)" in line:
                telemetry["traceback"] = True
            if "[output] Files saved" in line:
                telemetry["output_saved"] = True

    return telemetry


def cache_hit_rate(telemetry: dict) -> float | None:
    creation = telemetry["cache_creation_input_tokens"]
    read = telemetry["cache_read_input_tokens"]
    denom = creation + read
    if denom == 0:
        return None
    return read / denom


def cost_estimate(telemetry: dict) -> tuple[float, str]:
    input_tokens = telemetry["input_tokens"] if telemetry["input_tokens_observed"] else (
        telemetry["cache_creation_input_tokens"] + telemetry["cache_read_input_tokens"]
    )
    output_tokens = telemetry["output_tokens"] if telemetry["output_tokens_observed"] else 0
    cost = (input_tokens / 1_000_000) * 5 + (output_tokens / 1_000_000) * 25
    note = ""
    if not telemetry["output_tokens_observed"]:
        note = "output tokens not present in run.log telemetry"
    return cost, note


def _pct(numerator: int | float, denominator: int | float) -> str:
    if denominator == 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.1f}%"


def _fmt_rate(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value * 100:.1f}%"


def _md(value: object) -> str:
    text = _clean_cell(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _agreement_rates(comparison: pd.DataFrame) -> dict[str, float]:
    return {
        field: float(comparison[f"{field}_agree"].mean())
        for field in LABEL_FIELDS
    }


def _substitution_counts(
    comparison: pd.DataFrame,
    field: str,
    run_a: RunSpec,
    run_b: RunSpec,
) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    disagree = comparison[~comparison[f"{field}_agree"]]
    for _, row in disagree.iterrows():
        label_a = _canonical_label_string(row[f"{field}_{run_a.suffix}"], field)
        label_b = _canonical_label_string(row[f"{field}_{run_b.suffix}"], field)
        counts[(label_a, label_b)] += 1
    return counts


def _examples_for_mask(comparison: pd.DataFrame, mask: pd.Series, limit: int = 8) -> str:
    titles = comparison.loc[mask, "Title"].dropna().astype(str).head(limit).tolist()
    return "; ".join(titles)


def _tag_specific_rows(comparison: pd.DataFrame, run_a: RunSpec, run_b: RunSpec) -> list[dict[str, object]]:
    tag_values: set[str] = set()
    col_a = f"cross_cutting_tags_{run_a.suffix}"
    col_b = f"cross_cutting_tags_{run_b.suffix}"
    for col in (col_a, col_b):
        for value in comparison[col]:
            tag_values.update(_split_labels(value))

    rows = []
    for tag in sorted(tag_values):
        in_a = comparison[col_a].apply(lambda v, t=tag: t in _split_labels(v))
        in_b = comparison[col_b].apply(lambda v, t=tag: t in _split_labels(v))
        only_a = in_a & ~in_b
        only_b = in_b & ~in_a
        if int(only_a.sum()) or int(only_b.sum()):
            rows.append({
                "tag": tag,
                "only_a_count": int(only_a.sum()),
                "only_a_examples": _examples_for_mask(comparison, only_a),
                "only_b_count": int(only_b.sum()),
                "only_b_examples": _examples_for_mask(comparison, only_b),
            })
    return rows


def _markdown_table(headers: list[str], rows: Iterable[Iterable[object]]) -> list[str]:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(_md(cell) for cell in row) + " |")
    return out


def write_summary(
    path: Path,
    comparison: pd.DataFrame,
    counts: dict[str, int],
    telemetry: dict[str, dict],
    id_sets_match: bool,
    run_a: RunSpec,
    run_b: RunSpec,
) -> None:
    total_rows = len(comparison)
    all_agree = comparison[[f"{field}_agree" for field in LABEL_FIELDS]].all(axis=1)
    overall_count = int(all_agree.sum())
    rates = _agreement_rates(comparison)
    run_a_display = _display_label(run_a.label)
    run_b_display = _display_label(run_b.label)

    lines = [
        f"# {run_a_display} vs {run_b_display} rc1 Comparison Summary",
        "",
        "This report compares two full-register v4 rc1 classification runs side by side. It reports label agreement and disagreement patterns only; it does not rank the runs.",
        "",
        "## Run Counts",
        "",
        * _markdown_table(
            ["Run", "Projects classified"],
            [
                [run_a_display, counts[run_a.key]],
                [run_b_display, counts[run_b.key]],
            ],
        ),
        "",
        f"Project ID sets match: {'yes' if id_sets_match else 'no'}",
        "",
        "## Agreement Rates",
        "",
        f"Overall agreement: {_pct(overall_count, total_rows)} ({overall_count:,} of {total_rows:,} projects agreed on all compared label fields).",
        "",
        * _markdown_table(
            ["Field", "Agreement rate", "Agreed projects", "Compared projects"],
            [
                [
                    field,
                    _fmt_rate(rate),
                    int(comparison[f"{field}_agree"].sum()),
                    total_rows,
                ]
                for field, rate in rates.items()
            ],
        ),
        "",
        "## Disagreement Patterns by Category",
        "",
    ]

    for field in LABEL_FIELDS:
        lines.extend([f"### {field}", ""])
        counts_for_field = _substitution_counts(comparison, field, run_a, run_b)
        rows = [
            [from_label, to_label, count]
            for (from_label, to_label), count in counts_for_field.most_common()
            if count >= 3
        ]
        if rows:
            lines.extend(_markdown_table([f"{run_a.label} label set", f"{run_b.label} label set", "Projects"], rows))
        else:
            lines.append("No substitutions with at least 3 projects.")
        lines.append("")

    tag_rows = _tag_specific_rows(comparison, run_a, run_b)
    lines.extend(["## Tag-Specific Differences", ""])
    if tag_rows:
        lines.extend(_markdown_table(
            [
                "Tag",
                f"{run_a.label} only count",
                f"{run_a.label} only example titles",
                f"{run_b.label} only count",
                f"{run_b.label} only example titles",
            ],
            [
                [
                    row["tag"],
                    row["only_a_count"],
                    row["only_a_examples"],
                    row["only_b_count"],
                    row["only_b_examples"],
                ]
                for row in tag_rows
            ],
        ))
    else:
        lines.append("No tag-specific differences.")
    lines.append("")

    lines.extend(["## Cache Telemetry and Cost", ""])
    telemetry_rows = []
    cost_notes = []
    for run in (run_a, run_b):
        tel = telemetry[run.key]
        hit = cache_hit_rate(tel)
        cost, note = cost_estimate(tel)
        telemetry_rows.append([
            _display_label(run.label),
            tel["cache_read_input_tokens"],
            tel["cache_creation_input_tokens"],
            _fmt_rate(hit),
            f"${cost:,.2f}",
        ])
        if note:
            cost_notes.append(f"{_display_label(run.label)}: {note}.")

    lines.extend(_markdown_table(
        ["Run", "Cache read tokens", "Cache creation tokens", "Approx cache hit rate", "Approx cost"],
        telemetry_rows,
    ))
    if cost_notes:
        lines.extend(["", "Cost note: " + " ".join(cost_notes)])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_status(csv_path: Path, telemetry: dict, count: int | None) -> str:
    if not csv_path.exists():
        return "incomplete: layer_classifications.csv missing"
    if telemetry["traceback"]:
        return "completed with traceback in log"
    if telemetry["output_saved"]:
        return "complete"
    if count:
        return "classification CSV present; completion marker not found in log"
    return "incomplete"


def write_build_report(
    path: Path,
    run_dirs: dict[str, Path],
    counts: dict[str, int | None],
    telemetry: dict[str, dict],
    id_sets_match: bool | None,
    anomalies: list[str],
    blocking: list[str],
    run_a: RunSpec,
    run_b: RunSpec,
) -> None:
    lines = [
        "# v4 rc1 Comparison Build Report",
        "",
        "## Run Completion",
        "",
    ]

    rows = []
    for run in (run_a, run_b):
        csv_path = run_dirs[run.key] / "layer_classifications.csv"
        tel = telemetry[run.key]
        rows.append([
            _display_label(run.label),
            _run_status(csv_path, tel, counts.get(run.key)),
            counts.get(run.key) if counts.get(run.key) is not None else "n/a",
            len(tel["retry_lines"]),
            len(tel["error_lines"]),
        ])
    lines.extend(_markdown_table(["Run", "Status", "Projects", "Retry lines", "Error lines"], rows))
    lines.append("")

    lines.extend(["## Cache Hit Rates", ""])
    lines.extend(_markdown_table(
        ["Run", "Cache read tokens", "Cache creation tokens", "Approx hit rate"],
        [
            [
                _display_label(run.label),
                telemetry[run.key]["cache_read_input_tokens"],
                telemetry[run.key]["cache_creation_input_tokens"],
                _fmt_rate(cache_hit_rate(telemetry[run.key])),
            ]
            for run in (run_a, run_b)
        ],
    ))
    lines.append("")

    if id_sets_match is not None:
        lines.append(f"Project counts and ID sets match: {'yes' if id_sets_match else 'no'}")
        lines.append("")

    lines.extend(["## Failed or Retried Batches", ""])
    any_retry = False
    for run in (run_a, run_b):
        tel = telemetry[run.key]
        if tel["retry_lines"] or tel["error_lines"]:
            any_retry = True
            lines.extend([f"### {_display_label(run.label)}", ""])
            for line in tel["retry_lines"][:20]:
                lines.append(f"- Retry: `{_md(line)}`")
            for line in tel["error_lines"][:20]:
                lines.append(f"- Error: `{_md(line)}`")
            if len(tel["retry_lines"]) > 20 or len(tel["error_lines"]) > 20:
                lines.append("- Additional retry/error lines omitted from report; see run.log.")
            lines.append("")
    if not any_retry:
        lines.append("No retry or batch error lines found in run.log.")
        lines.append("")

    lines.extend(["## Targeted Cache Fill", ""])
    any_targeted_fill = False
    for run in (run_a, run_b):
        targeted = telemetry[run.key]["targeted_cache_fill_lines"]
        if targeted:
            any_targeted_fill = True
            lines.extend([f"### {_display_label(run.label)}", ""])
            for line in targeted[:30]:
                lines.append(f"- `{_md(line)}`")
            if len(targeted) > 30:
                lines.append("- Additional targeted cache-fill lines omitted from report; see run.log.")
            lines.append("")
    if not any_targeted_fill:
        lines.append("No targeted cache-fill lines found in run.log.")
        lines.append("")

    lines.extend(["## Anomalies", ""])
    if anomalies:
        lines.extend(f"- {item}" for item in anomalies)
    else:
        lines.append("No anomalies detected by the build script.")
    lines.append("")

    if blocking:
        lines.extend(["## Blocking Conditions", ""])
        lines.extend(f"- {item}" for item in blocking)
        lines.append("")
        lines.append("Comparison CSVs and summary were not produced because at least one run looked unreliable.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def detect_anomalies(
    comparison: pd.DataFrame | None,
    counts: dict[str, int | None],
    telemetry: dict[str, dict],
    id_sets_match: bool | None,
    run_a: RunSpec,
    run_b: RunSpec,
) -> tuple[list[str], list[str]]:
    anomalies: list[str] = []
    blocking: list[str] = []

    for run in (run_a, run_b):
        label = _display_label(run.label)
        count = counts.get(run.key)
        tel = telemetry[run.key]
        if count is None:
            blocking.append(f"{label}: classification CSV could not be read.")
            continue
        if count < 1_000:
            blocking.append(f"{label}: project count is {count:,}, well below the expected full register size.")
        hit = cache_hit_rate(tel)
        if hit is None:
            anomalies.append(f"{label}: cache telemetry was not found in run.log.")
        elif hit < 0.5:
            blocking.append(f"{label}: cache hit rate is {_fmt_rate(hit)}, below the 50% reliability threshold.")
        elif hit < 0.8:
            anomalies.append(f"{label}: cache hit rate is {_fmt_rate(hit)}, below the expected 80% pattern.")
        if tel["traceback"]:
            anomalies.append(f"{label}: traceback text appears in run.log.")
        if not tel["output_saved"]:
            anomalies.append(f"{label}: run.log does not contain the final output-saved marker.")

    if id_sets_match is False:
        anomalies.append("The two runs do not have identical Record ID sets.")

    if comparison is not None:
        for run in (run_a, run_b):
            label = _display_label(run.label)
            col = f"{RATIONALE_COLUMN}_{run.suffix}"
            missing = int((comparison[col] == RATIONALE_PLACEHOLDER).sum())
            if missing:
                text = f"{label}: {missing:,} rationale placeholder value(s) found."
                if missing >= 25:
                    blocking.append(text)
                else:
                    anomalies.append(text)

    return anomalies, blocking


def main() -> None:
    parser = argparse.ArgumentParser(description="Build v4 rc1 comparison outputs for two classifier runs")
    parser.add_argument("--run-a-dir", type=Path, default=DEFAULT_RUN_A_DIR)
    parser.add_argument("--run-b-dir", type=Path, default=DEFAULT_RUN_B_DIR)
    parser.add_argument("--run-a-label", default=DEFAULT_RUN_A_LABEL)
    parser.add_argument("--run-b-label", default=DEFAULT_RUN_B_LABEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    run_a = RunSpec("a", args.run_a_label, _suffix_from_label(args.run_a_label), args.run_a_dir)
    run_b = RunSpec("b", args.run_b_label, _suffix_from_label(args.run_b_label), args.run_b_dir)
    if run_a.suffix == run_b.suffix:
        raise SystemExit(f"Run labels produce the same column suffix: {run_a.suffix}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_dirs = {run_a.key: run_a.output_dir, run_b.key: run_b.output_dir}
    telemetry = {
        run.key: parse_run_log(run.output_dir / "run.log")
        for run in (run_a, run_b)
    }

    counts: dict[str, int | None] = {run_a.key: None, run_b.key: None}
    comparison: pd.DataFrame | None = None
    id_sets_match: bool | None = None

    try:
        df_a = _read_csv(run_a.output_dir / "layer_classifications.csv")
        df_b = _read_csv(run_b.output_dir / "layer_classifications.csv")
        counts = {run_a.key: len(df_a), run_b.key: len(df_b)}
        id_sets_match = set(df_a["Record ID"]) == set(df_b["Record ID"]) and counts[run_a.key] == counts[run_b.key]
        comparison = build_comparison(df_a, df_b, run_a, run_b)
    except Exception as exc:
        anomalies = [f"Comparison build failed before CSV generation: {exc}"]
        blocking = [str(exc)]
        write_build_report(
            args.output_dir / "comparison_build_report.md",
            run_dirs,
            counts,
            telemetry,
            id_sets_match,
            anomalies,
            blocking,
            run_a,
            run_b,
        )
        raise SystemExit(1) from exc

    anomalies, blocking = detect_anomalies(comparison, counts, telemetry, id_sets_match, run_a, run_b)
    write_build_report(
        args.output_dir / "comparison_build_report.md",
        run_dirs,
        counts,
        telemetry,
        id_sets_match,
        anomalies,
        blocking,
        run_a,
        run_b,
    )

    if blocking:
        raise SystemExit("Blocking run-quality issue detected; see comparison_build_report.md")

    full_path = args.output_dir / "comparison_full.csv"
    disagreements_path = args.output_dir / "comparison_disagreements.csv"
    summary_path = args.output_dir / "comparison_summary.md"

    comparison.to_csv(full_path, index=False, encoding="utf-8-sig")
    disagreements = comparison[comparison["disagreement_summary"] != ""].copy()
    disagreements.to_csv(disagreements_path, index=False, encoding="utf-8-sig")
    write_summary(summary_path, comparison, counts, telemetry, bool(id_sets_match), run_a, run_b)

    print(f"Saved {len(comparison):,} comparison rows to {full_path}")
    print(f"Saved {len(disagreements):,} disagreement rows to {disagreements_path}")
    print(f"Saved summary to {summary_path}")
    print(f"Saved build report to {args.output_dir / 'comparison_build_report.md'}")


if __name__ == "__main__":
    main()
