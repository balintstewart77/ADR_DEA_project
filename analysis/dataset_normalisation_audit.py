"""
Generate QA artifacts for dataset-name normalisation without changing the
dashboard-facing parsed dataset schema.

Outputs:
    analysis/outputs_v3/quality/dataset_normalisation_audit.csv
    analysis/outputs_v3/quality/dataset_normalisation_review_queue.csv
"""

import os
import sys

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
QUALITY_DIR = os.path.join(PROJECT_ROOT, "analysis", "outputs_v3", "quality")
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dataset_normalisation import dataset_family_for, describe_dataset_normalisation, iter_dataset_entries  # noqa: E402


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


def apply_duplicate_policy(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.drop_duplicates().reset_index(drop=True)
    if "Project ID" in out.columns and "Title" in out.columns:
        out["_title_key"] = out["Title"].fillna("").astype(str).str.strip()
        special_mask = out.apply(
            lambda row: (str(row["Project ID"]), row["_title_key"]) in SPECIAL_DROP_PROJECT_TITLE_PAIRS,
            axis=1,
        )
        out = out.loc[~special_mask].copy()
        out = out.drop_duplicates(subset=["Project ID", "_title_key"], keep="first").reset_index(drop=True)
        out = out.drop(columns="_title_key")
    return out


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
    return apply_duplicate_policy(df)


def build_audit_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, proj in df.iterrows():
        raw = proj.get("Datasets Used", "")
        if not isinstance(raw, str) or not raw.strip():
            continue
        for _, _, part in iter_dataset_entries(raw):
            meta = describe_dataset_normalisation(part)
            rows.append({
                "Project ID": proj["Project ID"],
                "Title": proj["Title"],
                **meta,
                "dataset_family": dataset_family_for(str(meta["canonical_dataset_name"])),
            })

    detail = pd.DataFrame(rows)
    if detail.empty:
        return pd.DataFrame(columns=[
            "raw_dataset",
            "canonical_dataset_name",
            "dataset_family",
            "match_type",
            "needs_review",
            "count",
            "example_project_id",
        ])

    grouped = (
        detail.groupby(
            ["raw_dataset", "canonical_dataset_name", "match_type", "needs_review"],
            as_index=False,
        )
        .agg(
            dataset_family=("dataset_family", "first"),
            count=("Project ID", "size"),
            example_project_id=("Project ID", "first"),
        )
        .sort_values(["count", "raw_dataset"], ascending=[False, True])
        .reset_index(drop=True)
    )
    grouped = grouped[
        [
            "raw_dataset",
            "canonical_dataset_name",
            "dataset_family",
            "match_type",
            "needs_review",
            "count",
            "example_project_id",
        ]
    ]
    return grouped


def main():
    os.makedirs(QUALITY_DIR, exist_ok=True)

    df_raw = load_raw()
    df = process_data(df_raw)
    audit = build_audit_table(df)

    audit_path = os.path.join(QUALITY_DIR, "dataset_normalisation_audit.csv")
    review_path = os.path.join(QUALITY_DIR, "dataset_normalisation_review_queue.csv")

    audit.to_csv(audit_path, index=False, encoding="utf-8-sig")
    review = (
        audit[audit["needs_review"] == 1]
        .sort_values(["count", "raw_dataset"], ascending=[False, True])
        .reset_index(drop=True)
    )
    review.to_csv(review_path, index=False, encoding="utf-8-sig")

    print(f"Audit rows: {len(audit)}")
    print(f"Review queue rows: {len(review)}")
    print(f"Saved audit to {audit_path}")
    print(f"Saved review queue to {review_path}")


if __name__ == "__main__":
    main()
