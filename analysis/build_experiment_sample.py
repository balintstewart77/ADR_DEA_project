"""
Build a deterministic sample for manual Opus vs Sonnet comparison.

The sample is boundary-aware without relying on prior LLM classifications:
- include short/opaque titles
- include records with long dataset strings
- fill the rest with a reproducible random sample

Usage:
    python analysis/build_experiment_sample.py
"""

from __future__ import annotations

import os

import pandas as pd

from llm_theme_analysis_v3 import load_data


ANALYSIS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(ANALYSIS_DIR, "outputs_v3", "quality")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "experiment_sample_150.csv")

SAMPLE_SIZE = 150
SEED = 42


def build_sample(df: pd.DataFrame, n: int = SAMPLE_SIZE, seed: int = SEED) -> pd.DataFrame:
    rng = pd.Series(range(len(df))).sample(frac=1, random_state=seed)
    shuffled = df.iloc[rng].copy()

    title_len = shuffled["Title"].fillna("").astype(str).str.len()
    dataset_len = shuffled["Datasets Used"].fillna("").astype(str).str.len()

    chosen_ids: list[str] = []

    def add_rows(mask: pd.Series, limit: int) -> None:
        nonlocal chosen_ids
        subset = shuffled.loc[mask & ~shuffled["Record ID"].astype(str).isin(chosen_ids)]
        chosen_ids.extend(subset.head(limit)["Record ID"].astype(str).tolist())

    add_rows(title_len < 30, 25)
    add_rows(dataset_len >= 500, 25)

    remaining = shuffled.loc[~shuffled["Record ID"].astype(str).isin(chosen_ids)]
    chosen_ids.extend(remaining.head(max(0, n - len(chosen_ids)))["Record ID"].astype(str).tolist())

    sample = df[df["Record ID"].astype(str).isin(chosen_ids)].copy()
    sample["_order"] = pd.Categorical(sample["Record ID"].astype(str), categories=chosen_ids, ordered=True)
    sample = sample.sort_values("_order").drop(columns="_order")

    out = sample[["Project ID", "Record ID", "Title", "Datasets Used", "Accreditation Date", "Year"]].copy()
    out["sample_reason"] = ""
    short_ids = set(df.loc[df["Title"].fillna("").astype(str).str.len() < 30, "Record ID"].astype(str))
    long_ids = set(df.loc[df["Datasets Used"].fillna("").astype(str).str.len() >= 500, "Record ID"].astype(str))
    out.loc[out["Record ID"].astype(str).isin(short_ids), "sample_reason"] += "short_title;"
    out.loc[out["Record ID"].astype(str).isin(long_ids), "sample_reason"] += "long_datasets;"
    out["sample_reason"] = out["sample_reason"].str.strip(";").replace("", "random_fill")
    return out.reset_index(drop=True)


def main() -> None:
    df = load_data()
    sample = build_sample(df)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sample.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Saved {len(sample):,} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
