"""
Export the canonical dataset list used for QA/reference.

Output:
    analysis/outputs_v3/quality/canonical_dataset_list.csv
"""

import os
import sys

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
QUALITY_DIR = os.path.join(PROJECT_ROOT, "analysis", "outputs_v3", "quality")
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dataset_normalisation import dataset_family_for, parse_datasets  # noqa: E402
from register_cleaning import clean_register_dataframe, load_raw_register  # noqa: E402


def load_raw():
    df, _source_file = load_raw_register(DATA_DIR)
    return df


def process_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    df, _stats = clean_register_dataframe(
        df_raw,
        include_quarter_date=True,
    )
    return df


def build_canonical_dataset_list(df: pd.DataFrame) -> pd.DataFrame:
    datasets = parse_datasets(df)
    datasets = datasets.drop_duplicates(subset=["Project ID", "dataset"])
    summary = (
        datasets.groupby("dataset")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "projects"})
    )
    summary["dataset_family"] = summary["dataset"].apply(dataset_family_for)
    summary = summary[["dataset", "dataset_family", "projects"]]
    summary = summary.sort_values(["projects", "dataset"], ascending=[False, True]).reset_index(drop=True)
    return summary


def main():
    os.makedirs(QUALITY_DIR, exist_ok=True)
    df_raw = load_raw()
    df = process_data(df_raw)
    summary = build_canonical_dataset_list(df)
    out_path = os.path.join(QUALITY_DIR, "canonical_dataset_list.csv")
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(summary)} rows to {out_path}")


if __name__ == "__main__":
    main()
