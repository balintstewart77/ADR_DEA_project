"""
Preview dataset-name merges produced by the shared normalisation rules.

Usage:
    python analysis/preview_dataset_merges.py
    # -> writes analysis/outputs_v3/quality/proposed_dataset_merges.csv
"""

import os
import sys
from collections import defaultdict

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dataset_normalisation import iter_dataset_entries, normalise_dataset_name  # noqa: E402
from register_cleaning import clean_register_dataframe, load_raw_register  # noqa: E402


def load_raw():
    df, _source_file = load_raw_register(DATA_DIR)
    return df


def process_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    df, _stats = clean_register_dataframe(df_raw, include_quarter_date=True)
    return df


def main():
    df_raw = load_raw()
    df_all = process_data(df_raw)
    rows = []
    for _, proj in df_all.iterrows():
        raw = proj.get("Datasets Used", "")
        if not isinstance(raw, str) or not raw.strip():
            continue
        for _, _, part in iter_dataset_entries(raw):
            rows.append({
                "Project ID": proj["Project ID"],
                "current_name": part,
                "proposed_canonical": normalise_dataset_name(part),
            })

    df_names = pd.DataFrame(rows)
    current_names = (
        df_names.groupby("current_name")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "projects"})
    )
    current_to_proposed = (
        df_names[["current_name", "proposed_canonical"]]
        .drop_duplicates()
        .merge(current_names, on="current_name", how="left")
    )

    groups = defaultdict(list)
    for _, row in current_to_proposed.iterrows():
        groups[row["proposed_canonical"]].append((row["current_name"], row["projects"]))

    merges = {k: v for k, v in groups.items() if len({name for name, _ in v}) > 1}

    rows = []
    for canonical in sorted(merges, key=lambda k: -sum(p for _, p in merges[k])):
        variants = sorted(merges[canonical], key=lambda x: -x[1])
        total = sum(p for _, p in variants)
        for current_name, projects in variants:
            rows.append({
                "proposed_canonical": canonical,
                "current_name": current_name,
                "projects": projects,
                "total_projects_in_group": total,
                "n_variants": len(variants),
            })

    df_out = pd.DataFrame(rows)

    out_dir = os.path.join(os.path.dirname(__file__), "outputs_v3", "quality")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "proposed_dataset_merges.csv")
    df_out.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Total unique raw dataset names: {len(current_names)}")
    print(f"Merge groups produced by current normalisation: {len(merges)}")
    print(f"\nFull merge list saved to: {out_path}")


if __name__ == "__main__":
    main()
