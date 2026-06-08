"""Deterministic register-facet loading for dashboard enrichment."""

import logging

import pandas as pd

from dashboard.config import REGISTER_PROPERTIES_CSV

LOGGER = logging.getLogger(__name__)

REGISTER_PROPERTIES_KEY_COL = "Record ID"
RECORD_LINKAGE_COL = "record_linkage"

DETERMINISTIC_FACET_COLUMNS = [
    RECORD_LINKAGE_COL,
    "dataset_collection_methods",
    "dataset_temporal_structures",
    "dataset_units",
    "researcher_sectors",
]

RECORD_LINKAGE_DISPLAY_LABELS = {
    "No record linkage": "No record linkage",
    "Cross-domain record linkage": "Cross-domain",
    "Within-domain record linkage": "Within-domain",
}


def _empty_register_properties(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=[REGISTER_PROPERTIES_KEY_COL, *columns])


def load_register_properties(
    columns: list[str] | None = None,
    path: str = REGISTER_PROPERTIES_CSV,
) -> pd.DataFrame:
    """Load deterministic register facets, degrading to blanks on failure."""
    requested_columns = columns or DETERMINISTIC_FACET_COLUMNS
    try:
        properties = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        ).fillna("")
    except Exception as exc:
        LOGGER.warning(
            "Could not load deterministic register properties from %s; "
            "deterministic dashboard columns will be blank. %s",
            path,
            exc,
        )
        return _empty_register_properties(requested_columns)

    if REGISTER_PROPERTIES_KEY_COL not in properties.columns:
        LOGGER.warning(
            "Deterministic register properties at %s are missing %s; "
            "deterministic dashboard columns will be blank.",
            path,
            REGISTER_PROPERTIES_KEY_COL,
        )
        return _empty_register_properties(requested_columns)

    for col in requested_columns:
        if col not in properties.columns:
            properties[col] = ""

    properties = properties[[REGISTER_PROPERTIES_KEY_COL, *requested_columns]].copy()
    for col in properties.columns:
        properties[col] = properties[col].astype(str).str.strip()

    duplicate_count = int(properties[REGISTER_PROPERTIES_KEY_COL].duplicated().sum())
    if duplicate_count:
        LOGGER.warning(
            "Deterministic register properties contain %s duplicate %s values; "
            "using the first row for each key.",
            duplicate_count,
            REGISTER_PROPERTIES_KEY_COL,
        )
        properties = properties.drop_duplicates(
            subset=[REGISTER_PROPERTIES_KEY_COL],
            keep="first",
        )

    return properties
