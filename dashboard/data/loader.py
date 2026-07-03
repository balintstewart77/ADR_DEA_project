"""Data loading and processing functions."""

import pandas as pd

from dashboard.config import (
    DATA_DIR,
    CLEANING_OUTPUT_DIR,
)
from analysis.register_cleaning import clean_register_dataframe, load_raw_register
from analysis.derive_register_properties import (
    REFERENCE_PATH,
    build_indexes,
    canonical_processing_environment_label,
    load_reference,
    match_linked_products,
)

try:
    from dashboard.dataset_normalisation import (
        iter_dataset_entries,
        normalise_dataset_name,
        parse_datasets,
    )
except ModuleNotFoundError:
    from dataset_normalisation import iter_dataset_entries, normalise_dataset_name, parse_datasets

_REFERENCE_INDEXES = build_indexes(load_reference(REFERENCE_PATH))
_LINKED_PRODUCT_COLLECTION_LABELS = {
    record["canonical"]: str(record.get("collection_label") or "").strip()
    for record in _REFERENCE_INDEXES.reference.get("linked_products", [])
    if str(record.get("collection_label") or "").strip()
}
REFERENCE_COLLECTIONS = list(dict.fromkeys(_LINKED_PRODUCT_COLLECTION_LABELS.values()))


def collection_labels_for_dataset(canonical_dataset: str) -> list[str]:
    """Return reference-defined collection labels for a canonical dataset."""
    labels = [
        _LINKED_PRODUCT_COLLECTION_LABELS[product["canonical"]]
        for product in match_linked_products(canonical_dataset, _REFERENCE_INDEXES)
        if product["canonical"] in _LINKED_PRODUCT_COLLECTION_LABELS
    ]
    return list(dict.fromkeys(labels))


def reference_collection_membership_rows() -> list[dict[str, str]]:
    """Reference-derived collection membership rows, one row per product spelling."""
    rows: list[dict[str, str]] = []
    for record in _REFERENCE_INDEXES.reference.get("linked_products", []):
        collection = str(record.get("collection_label") or "").strip()
        if not collection:
            continue
        canonical = str(record.get("canonical") or "").strip()
        values = [canonical, *[str(value).strip() for value in record.get("aliases", [])]]
        for value in values:
            if value:
                rows.append({
                    "collection": collection,
                    "product": canonical,
                    "member": value,
                })
    return rows


def load_raw(data_dir=DATA_DIR):
    return load_raw_register(data_dir)


def classify_collection(datasets_str: str) -> list[str]:
    """Return referenced collection labels matched through linked products."""
    return list(dict.fromkeys(count_collection_usages(datasets_str)))


def count_collection_usages(datasets_str: str) -> list[str]:
    """Return one collection entry per matched individual dataset request."""
    if not isinstance(datasets_str, str):
        return []

    usages = []
    for _, _, part in iter_dataset_entries(datasets_str):
        if not part:
            continue
        dataset = normalise_dataset_name(part)
        usages.extend(collection_labels_for_dataset(dataset))
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

    df["Secure Research Service"] = df["Secure Research Service"].apply(
        lambda value: canonical_processing_environment_label(value, _REFERENCE_INDEXES)
    )

    df["collection_usages"] = df["Datasets Used"].apply(count_collection_usages)
    df["collections"] = df["collection_usages"].apply(lambda values: list(dict.fromkeys(values)))
    df["is_flagship"] = df["collections"].apply(lambda x: len(x) > 0)

    # Explode by individual dataset usage (not just unique collection per project).
    # A project using 3 Data First datasets produces 3 rows, counting each access request.
    flagship_rows = []
    for _, row in df[df["is_flagship"]].iterrows():
        for coll in row["collection_usages"]:
            flagship_rows.append({**row.to_dict(), "collection": coll})
    df_flagship = pd.DataFrame(flagship_rows, columns=[*df.columns, "collection"])

    return df, df_flagship, stats
