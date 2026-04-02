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
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]
    df = apply_duplicate_policy(df)
    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["quarter_date"] = df["Quarter"].dt.to_timestamp()
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
