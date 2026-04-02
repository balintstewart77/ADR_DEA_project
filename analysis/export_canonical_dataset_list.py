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


CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

SPECIAL_DROP_PROJECT_TITLE_PAIRS = {
    ("2023/113", "The Influence of Early Life Health and Nutritional Environment on Later Life Health and Morbidity"),
}


def load_raw():
    for fname in CANDIDATE_FILES:
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(f"[data] Loaded {len(df)} rows from {fname}")
            return df
    raise FileNotFoundError("No DEA projects CSV found in data/")


def process_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    col_map = {
        "Project Number": "Project ID",
        "Project Name": "Title",
        "Accredited Researchers": "Researchers",
        "Legal Gateway": "Legal Basis",
        "Protected Data Accessed": "Datasets Used",
        "Processing Environment": "Secure Research Service",
    }
    df = df.rename(columns=col_map)
    df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    df = df.dropna(subset=["Accreditation Date"])
    if "Legal Basis" in df.columns:
        df = df[df["Legal Basis"].astype(str).str.contains("Digital Economy Act", na=False, case=False)]

    df = df.drop_duplicates().reset_index(drop=True)
    df["_title_key"] = df["Title"].fillna("").astype(str).str.strip()
    special_mask = df.apply(
        lambda row: (str(row["Project ID"]), row["_title_key"]) in SPECIAL_DROP_PROJECT_TITLE_PAIRS,
        axis=1,
    )
    df = df.loc[~special_mask].copy()
    df = df.drop_duplicates(subset=["Project ID", "_title_key"], keep="first").reset_index(drop=True)
    df = df.drop(columns="_title_key")

    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["quarter_date"] = df["Quarter"].dt.to_timestamp()
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
