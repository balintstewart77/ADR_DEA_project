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
from register_cleaning import clean_register_dataframe, load_raw_register  # noqa: E402


def load_raw():
    df, _source_file = load_raw_register(DATA_DIR)
    return df


def process_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    df, _stats = clean_register_dataframe(df_raw)
    return df


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
