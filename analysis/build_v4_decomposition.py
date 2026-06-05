"""
Compare intra-Opus-4.8 instability against Opus 4.8 vs Opus 4.6 disagreement.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import pandas as pd


ANALYSIS_DIR = Path(__file__).resolve().parent
DEFAULT_INTRA_DIR = ANALYSIS_DIR / "outputs_comparison_v4_8_intra_rc1"
DEFAULT_INTER_DIR = ANALYSIS_DIR / "outputs_comparison_v4_rc1"
DEFAULT_OUTPUT_DIR = ANALYSIS_DIR / "outputs_comparison_decomposition_rc1"

FIELD_COLUMNS = {
    "Domains": "substantive_domains_agree",
    "Purpose": "analytical_purpose_agree",
    "Tags": "cross_cutting_tags_agree",
}
FIELD_ORDER = ["Domains", "Purpose", "Tags"]


def _read_comparison(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"Record ID": str, "Project ID": str})
    missing = ["Record ID", "Title", *FIELD_COLUMNS.values()]
    absent = [col for col in missing if col not in df.columns]
    if absent:
        raise ValueError(f"{path} is missing columns: {', '.join(absent)}")
    return df


def _bool_series(df: pd.DataFrame, col: str) -> pd.Series:
    series = df[col]
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes"])


def _field_agree(df: pd.DataFrame, field: str) -> pd.Series:
    return _bool_series(df, FIELD_COLUMNS[field])


def _overall_agree(df: pd.DataFrame) -> pd.Series:
    agreed = pd.Series(True, index=df.index)
    for field in FIELD_ORDER:
        agreed = agreed & _field_agree(df, field)
    return agreed


def _rates(df: pd.DataFrame) -> dict[str, float]:
    rates = {"Overall agreement": float(_overall_agree(df).mean())}
    for field in FIELD_ORDER:
        rates[field] = float(_field_agree(df, field).mean())
    return rates


def _fmt_pct(value: float, digits: int = 1) -> str:
    return f"{value * 100:.{digits}f}%"


def _fmt_pp(value: float, digits: int = 1) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.{digits}f} pp"


def _md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _markdown_table(headers: list[str], rows: Iterable[Iterable[object]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_md(cell) for cell in row) + " |")
    return lines


def _disagreed_overall(df: pd.DataFrame) -> pd.Series:
    return ~_overall_agree(df)


def _examples(titles: pd.Series, limit: int = 5) -> str:
    values = [str(title) for title in titles.dropna().head(limit).tolist()]
    return "; ".join(values) if values else "None in this bucket."


def build_pattern_overlap(intra: pd.DataFrame, inter: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int]]:
    intra_flags = pd.DataFrame({
        "Record ID": intra["Record ID"],
        "unstable_intra_4_8": _disagreed_overall(intra),
    })
    inter_flags = pd.DataFrame({
        "Record ID": inter["Record ID"],
        "disagreed_inter_model": _disagreed_overall(inter),
    })
    overlap = intra_flags.merge(inter_flags, on="Record ID", how="outer").fillna(False)
    overlap["unstable_intra_4_8"] = overlap["unstable_intra_4_8"].astype(bool)
    overlap["disagreed_inter_model"] = overlap["disagreed_inter_model"].astype(bool)

    both = int((overlap["unstable_intra_4_8"] & overlap["disagreed_inter_model"]).sum())
    union = int((overlap["unstable_intra_4_8"] | overlap["disagreed_inter_model"]).sum())
    stats = {
        "intra_disagreement_count": int(overlap["unstable_intra_4_8"].sum()),
        "inter_disagreement_count": int(overlap["disagreed_inter_model"].sum()),
        "overlap_count": both,
        "union_count": union,
        "jaccard_index": both / union if union else 0.0,
    }
    return overlap.sort_values("Record ID").reset_index(drop=True), stats


def build_per_layer_rates(intra: pd.DataFrame, inter: pd.DataFrame) -> pd.DataFrame:
    intra_rates = _rates(intra)
    inter_rates = _rates(inter)
    rows = []
    rows.append({
        "comparison": "Intra-4.8 (run 1 vs run 2)",
        **{key: round(value * 100, 4) for key, value in intra_rates.items()},
    })
    rows.append({
        "comparison": "Inter-model (4.8 vs 4.6)",
        **{key: round(value * 100, 4) for key, value in inter_rates.items()},
    })
    rows.append({
        "comparison": "Excess inter-model disagreement, percentage points",
        **{key: round(((1 - inter_rates[key]) - (1 - intra_rates[key])) * 100, 4) for key in intra_rates},
    })
    return pd.DataFrame(rows)


def write_summary(
    path: Path,
    intra: pd.DataFrame,
    inter: pd.DataFrame,
    rates_df: pd.DataFrame,
    overlap_stats: dict[str, float | int],
) -> None:
    intra_rates = _rates(intra)
    inter_rates = _rates(inter)
    diff_disagreement = {
        key: (1 - inter_rates[key]) - (1 - intra_rates[key])
        for key in intra_rates
    }

    headline_rows = [
        [
            "Intra-4.8 (run 1 vs run 2)",
            _fmt_pct(intra_rates["Overall agreement"]),
            _fmt_pct(intra_rates["Domains"]),
            _fmt_pct(intra_rates["Purpose"]),
            _fmt_pct(intra_rates["Tags"]),
        ],
        [
            "Inter-model (4.8 vs 4.6)",
            _fmt_pct(inter_rates["Overall agreement"]),
            _fmt_pct(inter_rates["Domains"]),
            _fmt_pct(inter_rates["Purpose"]),
            _fmt_pct(inter_rates["Tags"]),
        ],
        [
            "Difference (inter - intra disagreement)",
            _fmt_pp(diff_disagreement["Overall agreement"]),
            _fmt_pp(diff_disagreement["Domains"]),
            _fmt_pp(diff_disagreement["Purpose"]),
            _fmt_pp(diff_disagreement["Tags"]),
        ],
    ]

    lines = [
        "# v4 rc1 Intra-vs-Inter Comparison Decomposition",
        "",
        "This report compares two disagreement baselines for the same full DEA register and the same rc1 dictionary. The intra-4.8 comparison measures Opus 4.8 run against itself on identical inputs. The inter-model comparison measures Opus 4.8 against Opus 4.6 on the same inputs.",
        "",
        "## 1. Headline Decomposition",
        "",
        * _markdown_table(
            ["Comparison", "Overall agreement", "Domains", "Purpose", "Tags"],
            headline_rows,
        ),
        "",
        "The difference row reports excess inter-model disagreement in percentage points, calculated as inter-model disagreement minus intra-4.8 disagreement.",
        "",
        "## 2. Interpretation Framing",
        "",
        "Intra-4.8 disagreement reflects stochastic variation in the model's output on identical inputs. Inter-model disagreement reflects stochastic variation plus differences in how Opus 4.8 and Opus 4.6 read the prompt and apply the dictionary. The difference between inter-model and intra-model disagreement is an approximate lower bound on the model-attributable portion. It is approximate because the two sources are not strictly additive; both involve sampling.",
        "",
        "## 3. Per-Field Rates",
        "",
        * _markdown_table(
            ["Comparison", "Overall agreement", "Domains", "Purpose", "Tags"],
            [
                [
                    row["comparison"],
                    f"{row['Overall agreement']:.4f}",
                    f"{row['Domains']:.4f}",
                    f"{row['Purpose']:.4f}",
                    f"{row['Tags']:.4f}",
                ]
                for _, row in rates_df.iterrows()
            ],
        ),
        "",
        "The numeric rates table is also saved as `per_layer_rates.csv`.",
        "",
        "## 4. Pattern Overlap",
        "",
        * _markdown_table(
            ["Measure", "Value"],
            [
                ["Projects unstable intra-4.8", overlap_stats["intra_disagreement_count"]],
                ["Projects disagreed inter-model", overlap_stats["inter_disagreement_count"]],
                ["Overlap count", overlap_stats["overlap_count"]],
                ["Union count", overlap_stats["union_count"]],
                ["Jaccard index", f"{overlap_stats['jaccard_index']:.4f}"],
            ],
        ),
        "",
        "The project-level overlap table is saved as `pattern_overlap.csv`.",
        "",
        "## 5. Per-Field Examples",
        "",
    ]

    inter_by_id = inter.set_index("Record ID")
    intra_by_id = intra.set_index("Record ID")
    common_ids = inter_by_id.index.intersection(intra_by_id.index)
    titles = inter_by_id.loc[common_ids, "Title"]

    for field in FIELD_ORDER:
        inter_disagreed = ~_field_agree(inter_by_id.loc[common_ids].reset_index(), field).set_axis(common_ids)
        intra_disagreed = ~_field_agree(intra_by_id.loc[common_ids].reset_index(), field).set_axis(common_ids)

        inter_only = inter_disagreed & ~intra_disagreed
        intra_only = intra_disagreed & ~inter_disagreed
        both = inter_disagreed & intra_disagreed

        lines.extend([f"### {field}", ""])
        lines.extend(_markdown_table(
            ["Bucket", "Example titles"],
            [
                ["Disagreed inter-model but agreed intra-4.8", _examples(titles[inter_only])],
                ["Disagreed intra-4.8 but agreed inter-model", _examples(titles[intra_only])],
                ["Disagreed in both", _examples(titles[both])],
            ],
        ))
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build intra-vs-inter v4 rc1 decomposition report")
    parser.add_argument("--intra-dir", type=Path, default=DEFAULT_INTRA_DIR)
    parser.add_argument("--inter-dir", type=Path, default=DEFAULT_INTER_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    intra = _read_comparison(args.intra_dir / "comparison_full.csv")
    inter = _read_comparison(args.inter_dir / "comparison_full.csv")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rates_df = build_per_layer_rates(intra, inter)
    rates_path = args.output_dir / "per_layer_rates.csv"
    rates_df.to_csv(rates_path, index=False, encoding="utf-8-sig")

    overlap, overlap_stats = build_pattern_overlap(intra, inter)
    overlap_path = args.output_dir / "pattern_overlap.csv"
    overlap.to_csv(overlap_path, index=False, encoding="utf-8-sig")

    summary_path = args.output_dir / "decomposition_summary.md"
    write_summary(summary_path, intra, inter, rates_df, overlap_stats)

    print(f"Saved rates to {rates_path}")
    print(f"Saved pattern overlap to {overlap_path}")
    print(f"Saved summary to {summary_path}")


if __name__ == "__main__":
    main()
