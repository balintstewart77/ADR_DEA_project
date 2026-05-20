"""Data loading and processing functions."""

import os

import pandas as pd

from dashboard.config import (
    DATA_DIR,
    CANDIDATE_FILES,
    SPECIAL_DROP_PROJECT_TITLE_PAIRS,
    FLAGSHIP_COLLECTIONS,
)

try:
    from dashboard.dataset_normalisation import iter_dataset_entries, parse_datasets
except ModuleNotFoundError:
    from dataset_normalisation import iter_dataset_entries, parse_datasets


def load_raw(data_dir=DATA_DIR):
    for fname in CANDIDATE_FILES:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(f"[data] Loaded {len(df)} rows from {fname}")
            return df, fname
    raise FileNotFoundError("No DEA projects CSV found in data/")


def apply_duplicate_policy(df: pd.DataFrame, stats: dict | None = None) -> pd.DataFrame:
    """Remove exact duplicates and same-ID/same-title duplicates, keep conflicting titles."""
    out = df.copy()

    n_before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    exact_removed = n_before - len(out)

    special_removed = 0
    same_title_removed = 0
    if "Project ID" in out.columns and "Title" in out.columns:
        out["_title_key"] = out["Title"].fillna("").astype(str).str.strip()
        special_mask = out.apply(
            lambda row: (str(row["Project ID"]), row["_title_key"]) in SPECIAL_DROP_PROJECT_TITLE_PAIRS,
            axis=1,
        )
        n_before = len(out)
        out = out.loc[~special_mask].copy()
        special_removed = n_before - len(out)

        n_before = len(out)
        out = out.drop_duplicates(subset=["Project ID", "_title_key"], keep="first").reset_index(drop=True)
        same_title_removed = n_before - len(out)
        out = out.drop(columns="_title_key")

    if stats is not None:
        stats["dropped_exact_duplicates"] = exact_removed
        stats["dropped_special_duplicate_rows"] = special_removed
        stats["dropped_same_id_same_title"] = same_title_removed

    return out


def classify_collection(datasets_str: str) -> list[str]:
    """Return list of matching collection names for a datasets string."""
    if not isinstance(datasets_str, str):
        return []
    s = " ".join(datasets_str.lower().split())
    matches = []
    for col, keywords in FLAGSHIP_COLLECTIONS.items():
        if any(kw in s for kw in keywords):
            matches.append(col)
    return matches


def count_collection_usages(datasets_str: str) -> list[str]:
    """Return one collection entry per individual dataset match.

    If a project uses Crown Court + Magistrates Court + Prisoner Dataset,
    this returns ["Data First", "Data First", "Data First"] — counting each
    dataset access request separately, consistent with the notebook methodology.
    """
    if not isinstance(datasets_str, str):
        return []
    # Split into individual dataset entries (same logic as parse_datasets)
    entries = [
        " ".join(part.lower().split())
        for _, _, part in iter_dataset_entries(datasets_str)
        if part
    ]

    usages = []
    for entry in entries:
        for col, keywords in FLAGSHIP_COLLECTIONS.items():
            if any(kw in entry for kw in keywords):
                usages.append(col)
                break  # each entry maps to at most one collection
    return usages


def process_data(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Returns:
        df_all      -- full cleaned dataset (one row per retained project record)
        df_flagship -- exploded dataset (one row per dataset request x collection)
        stats       -- dict of row counts at each processing step
    """
    stats = {}
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
    stats["raw_loaded"] = len(df)

    df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    n_before = len(df)
    df = df.dropna(subset=["Accreditation Date"])
    stats["dropped_no_date"] = n_before - len(df)

    if "Legal Basis" in df.columns:
        n_before = len(df)
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]
        stats["dropped_non_dea"] = n_before - len(df)
    else:
        stats["dropped_non_dea"] = 0

    df = apply_duplicate_policy(df, stats)
    stats["after_filters"] = len(df)

    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")
    df["quarter_date"] = df["Quarter"].dt.to_timestamp()
    df["Project Row ID"] = [f"proj-{i:04d}" for i in range(len(df))]

    df["collections"] = df["Datasets Used"].apply(classify_collection)
    df["is_flagship"] = df["collections"].apply(lambda x: len(x) > 0)

    # Explode by individual dataset usage (not just unique collection per project).
    # A project using 3 Data First datasets produces 3 rows, counting each access request.
    df["collection_usages"] = df["Datasets Used"].apply(count_collection_usages)
    flagship_rows = []
    for _, row in df[df["is_flagship"]].iterrows():
        for coll in row["collection_usages"]:
            flagship_rows.append({**row.to_dict(), "collection": coll})
    df_flagship = pd.DataFrame(flagship_rows)

    return df, df_flagship, stats
