"""Data loading and processing functions."""

import pandas as pd

from dashboard.config import (
    DATA_DIR,
    CANDIDATE_FILES,
    FLAGSHIP_COLLECTIONS,
    CLEANING_OUTPUT_DIR,
)
from analysis.register_cleaning import clean_register_dataframe, load_raw_register

try:
    from dashboard.dataset_normalisation import iter_dataset_entries, parse_datasets
except ModuleNotFoundError:
    from dataset_normalisation import iter_dataset_entries, parse_datasets


def load_raw(data_dir=DATA_DIR):
    return load_raw_register(data_dir, CANDIDATE_FILES)


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
    df, stats = clean_register_dataframe(
        df_raw,
        output_dir=CLEANING_OUTPUT_DIR,
        include_quarter_date=True,
        include_project_row_id=True,
    )

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
