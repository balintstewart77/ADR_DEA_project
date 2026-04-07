"""
Build a manual-review CSV for comparing Opus and Sonnet classifications.

Usage examples:
    python analysis/build_model_comparison.py
    python analysis/build_model_comparison.py --sonnet-csv analysis/outputs_v3/sonnet_layer_classifications.csv
    python analysis/build_model_comparison.py --sample-csv analysis/outputs_v3/quality/human_review_sample.csv
"""

from __future__ import annotations

import argparse
import os

import pandas as pd


ANALYSIS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(ANALYSIS_DIR, "outputs_v3")
QUALITY_DIR = os.path.join(OUTPUT_DIR, "quality")

DEFAULT_OPUS_CSV = os.path.join(OUTPUT_DIR, "layer_classifications.csv")
DEFAULT_SAMPLE_CSV = os.path.join(QUALITY_DIR, "human_review_sample.csv")
DEFAULT_OUTPUT_CSV = os.path.join(QUALITY_DIR, "model_comparison_review.csv")


KEY_COLUMNS = [
    "Project ID",
    "Record ID",
    "Title",
    "Datasets Used",
]

LABEL_COLUMNS = [
    "substantive_domains",
    "linkage_mode",
    "analytical_purpose",
]


def _load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return pd.read_csv(path, encoding="utf-8-sig")


def _rename_model_columns(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    extra = ["primary_domain"] if "primary_domain" in df.columns else []
    cols = LABEL_COLUMNS + extra
    rename_map = {col: f"{prefix}_{col}" for col in cols}
    return df[KEY_COLUMNS + cols].rename(columns=rename_map)


def build_comparison(
    opus_csv: str,
    sonnet_csv: str | None,
    sample_csv: str | None,
) -> pd.DataFrame:
    opus = _rename_model_columns(_load_csv(opus_csv), "opus")

    if sample_csv and os.path.exists(sample_csv):
        sample = _load_csv(sample_csv)
        base = sample[KEY_COLUMNS].drop_duplicates()
        if "is_flagged" in sample.columns:
            base = base.merge(
                sample[["Record ID", "is_flagged"]].drop_duplicates(),
                on="Record ID",
                how="left",
            )
        else:
            base["is_flagged"] = False
    else:
        base = opus[KEY_COLUMNS].drop_duplicates().copy()
        base["is_flagged"] = False

    comparison = base.merge(opus, on=KEY_COLUMNS, how="left")

    if sonnet_csv and os.path.exists(sonnet_csv):
        sonnet = _rename_model_columns(_load_csv(sonnet_csv), "sonnet")
        comparison = comparison.merge(sonnet, on=KEY_COLUMNS, how="left")
    else:
        for col in LABEL_COLUMNS:
            comparison[f"sonnet_{col}"] = ""

    comparison["domain_match"] = (
        comparison["opus_substantive_domains"].fillna("").astype(str).str.strip()
        == comparison["sonnet_substantive_domains"].fillna("").astype(str).str.strip()
    )
    comparison["linkage_match"] = (
        comparison["opus_linkage_mode"].fillna("").astype(str).str.strip()
        == comparison["sonnet_linkage_mode"].fillna("").astype(str).str.strip()
    )
    comparison["purpose_match"] = (
        comparison["opus_analytical_purpose"].fillna("").astype(str).str.strip()
        == comparison["sonnet_analytical_purpose"].fillna("").astype(str).str.strip()
    )
    comparison["all_layers_match"] = (
        comparison["domain_match"] & comparison["linkage_match"] & comparison["purpose_match"]
    )

    comparison["review_status"] = ""
    comparison["preferred_model"] = ""
    comparison["final_domain"] = ""
    comparison["final_linkage"] = ""
    comparison["final_purpose"] = ""
    comparison["review_notes"] = ""

    sort_cols = ["all_layers_match", "is_flagged", "Record ID"]
    ascending = [True, False, True]
    comparison = comparison.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Opus/Sonnet comparison review CSV")
    parser.add_argument("--opus-csv", default=DEFAULT_OPUS_CSV, help="Path to Opus classifications CSV")
    parser.add_argument("--sonnet-csv", default=None, help="Path to Sonnet classifications CSV")
    parser.add_argument(
        "--sample-csv",
        default=DEFAULT_SAMPLE_CSV,
        help="Optional review sample CSV to restrict rows and carry forward flags",
    )
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV, help="Output CSV path")
    args = parser.parse_args()

    comparison = build_comparison(args.opus_csv, args.sonnet_csv, args.sample_csv)
    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    comparison.to_csv(args.output_csv, index=False, encoding="utf-8-sig")
    print(f"Saved {len(comparison):,} rows to {args.output_csv}")


if __name__ == "__main__":
    main()
