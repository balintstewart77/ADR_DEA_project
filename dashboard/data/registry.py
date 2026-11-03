"""Module-level data loading and computed metadata / filter option lists."""

import pandas as pd

from dashboard.config import (
    _PROJECT_ID_KEY_COL,
    PartialYearInfo,
)
from dashboard.data.loader import REFERENCE_COLLECTIONS, load_raw, process_data
from dashboard.data.keys import _project_id_key
from dashboard.components.filter_controls import label_with_count

try:
    from dashboard.dataset_normalisation import parse_datasets
except ModuleNotFoundError:
    from dataset_normalisation import parse_datasets

try:
    from dashboard.institution_normalisation import parse_institutions
except ModuleNotFoundError:
    from institution_normalisation import parse_institutions

from dashboard.data.deterministic import RECORD_LINKAGE_COL, load_register_properties

# ---------------------------------------------------------------------------
# Load data once at startup
# ---------------------------------------------------------------------------

df_raw, source_file = load_raw()
df_all, df_flagship_requests, PROCESSING_STATS = process_data(df_raw)
PROCESSING_STATS["final_rows"] = len(df_all)
PROCESSING_STATS["retained_conflicting_duplicate_rows"] = int(
    df_all["Project ID"].duplicated(keep=False).sum()
)
df_flagship_projects = (
    df_flagship_requests
    .drop_duplicates(subset=["Project Row ID", "collection"], keep="first")
    .reset_index(drop=True)
)

# Parse individual dataset usage
df_datasets = parse_datasets(df_all)

# Parse institution affiliations
df_institutions = parse_institutions(df_all)

COLLECTIONS = (
    sorted(df_flagship_projects["collection"].unique())
    if len(df_flagship_projects)
    else REFERENCE_COLLECTIONS
)
_max_date = df_all["Accreditation Date"].max() if len(df_all) else None
DATA_DATE = _max_date.strftime("%d %B %Y") if _max_date is not None else "unknown"
# Public source wording deliberately describes the register, not its internal
# archive path or content hashes. Its accompanying coverage date is DATA_DATE.
DATA_SOURCE_LABEL = "UKSA accredited-project register"

# Detect whether the latest year is incomplete (data doesn't cover the full year)
_partial_year = int(_max_date.year) if (_max_date is not None and _max_date.month < 12) else None
PARTIAL_YEAR_INFO = PartialYearInfo(
    year=_partial_year,
    label=f"{_partial_year}*" if _partial_year else None,
    note=f"* {_partial_year} data covers Jan–{_max_date.strftime('%b')} only" if _partial_year else "",
)

TOTAL_PROJECTS = len(df_all)
TOTAL_RETAINED_REGISTER_ENTRIES = len(df_all)
TOTAL_UNIQUE_OFFICIAL_PROJECT_IDS = df_all["Project ID"].nunique() if len(df_all) else 0
TOTAL_DATASET_REQUESTS = len(df_datasets)
TOTAL_FLAGSHIP = df_flagship_projects["Project Row ID"].nunique() if len(df_flagship_projects) else 0
TOTAL_FLAGSHIP_REQUESTS = len(df_flagship_requests)
YEAR_RANGE = f"{int(df_all['Year'].min())}–{int(df_all['Year'].max())}" if len(df_all) else ""
DATASET_PROJECT_KEY_COL = "Record ID" if "Record ID" in df_datasets.columns else "Project ID"
INSTITUTION_PROJECT_KEY_COL = "Record ID" if "Record ID" in df_institutions.columns else "Project ID"

_register_properties = load_register_properties(columns=[RECORD_LINKAGE_COL])
if "Record ID" in df_all.columns and not _register_properties.empty:
    _linkage_lookup = (
        _register_properties
        .drop_duplicates(subset=["Record ID"], keep="first")
        .set_index("Record ID")[RECORD_LINKAGE_COL]
    )
    _record_linkage_values = (
        df_all["Record ID"]
        .fillna("")
        .astype(str)
        .str.strip()
        .map(_linkage_lookup)
        .fillna("")
    )
else:
    _record_linkage_values = pd.Series("", index=df_all.index, dtype=object)

CROSS_DOMAIN_LINKED_PROJECTS = int(
    (_record_linkage_values == "Cross-domain record linkage").sum()
)
WITHIN_DOMAIN_LINKED_PROJECTS = int(
    (_record_linkage_values == "Within-domain record linkage").sum()
)
RECORD_LINKED_PROJECTS = CROSS_DOMAIN_LINKED_PROJECTS + WITHIN_DOMAIN_LINKED_PROJECTS
RECORD_LINKED_PROJECT_SHARE = (
    RECORD_LINKED_PROJECTS / TOTAL_PROJECTS * 100
    if TOTAL_PROJECTS
    else 0.0
)
RETAINED_CONFLICTING_DUPLICATE_IDS = sorted(
    df_all.loc[df_all["Project ID"].duplicated(keep=False), "Project ID"].unique().tolist()
)
RETAINED_CONFLICTING_DUPLICATE_IDS_TEXT = (
    ", ".join(RETAINED_CONFLICTING_DUPLICATE_IDS) if RETAINED_CONFLICTING_DUPLICATE_IDS else "None"
)

# ---------------------------------------------------------------------------
# Apply project-id keying on df_all
# ---------------------------------------------------------------------------

df_all[_PROJECT_ID_KEY_COL] = df_all["Project ID"].apply(_project_id_key)

# ---------------------------------------------------------------------------
# Filter option lists
# ---------------------------------------------------------------------------

def _related_options(frame: pd.DataFrame, value_col: str, key_col: str, all_label: str) -> list[dict]:
    """Option universe for a related-table facet, counted in distinct records."""
    counts = frame.drop_duplicates(subset=[key_col, value_col]).groupby(value_col)[key_col].nunique()
    return [{"label": all_label, "value": "ALL"}] + [
        {"label": label_with_count(value, int(counts.get(value, 0))), "value": value}
        for value in sorted(frame[value_col].unique()) if value
    ]


_ALL_DATASET_OPTIONS = _related_options(
    df_datasets, "dataset", DATASET_PROJECT_KEY_COL, "All datasets",
)
_ALL_PROVIDER_OPTIONS = _related_options(
    df_datasets, "provider", DATASET_PROJECT_KEY_COL, "All dataset source organisations",
)
_ALL_INSTITUTION_OPTIONS = _related_options(
    df_institutions, "institution", INSTITUTION_PROJECT_KEY_COL, "All institutions",
)


def _format_tre_provider(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


_tre_values = df_all["Secure Research Service"].astype("string").str.strip()
_tre_project_counts = _tre_values[_tre_values.notna() & _tre_values.ne("")].value_counts()
_ALL_TRE_OPTIONS = [{"label": "All processing environments", "value": "ALL"}] + [
    {"label": label_with_count(value, int(_tre_project_counts[value])), "value": value}
    for value in sorted(_tre_project_counts.index)
]
