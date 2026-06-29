"""Module-level data loading and computed metadata / filter option lists."""

import pandas as pd

from dashboard.config import (
    FLAGSHIP_COLLECTIONS,
    _PROJECT_ID_KEY_COL,
    PartialYearInfo,
)
from dashboard.data.loader import load_raw, process_data
from dashboard.data.keys import _project_id_key

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
    else list(FLAGSHIP_COLLECTIONS.keys())
)
_max_date = df_all["Accreditation Date"].max() if len(df_all) else None
DATA_DATE = _max_date.strftime("%d %B %Y") if _max_date is not None else "unknown"

# Detect whether the latest year is incomplete (data doesn't cover the full year)
_partial_year = int(_max_date.year) if (_max_date is not None and _max_date.month < 12) else None
PARTIAL_YEAR_INFO = PartialYearInfo(
    year=_partial_year,
    label=f"{_partial_year}*" if _partial_year else None,
    note=f"* {_partial_year} data covers Jan–{_max_date.strftime('%b')} only" if _partial_year else "",
)

TOTAL_PROJECTS = len(df_all)
TOTAL_DATASET_REQUESTS = len(df_datasets)
TOTAL_FLAGSHIP = df_flagship_projects["Project Row ID"].nunique() if len(df_flagship_projects) else 0
TOTAL_FLAGSHIP_REQUESTS = len(df_flagship_requests) if len(df_flagship_requests) else 0
YEAR_RANGE = f"{int(df_all['Year'].min())}–{int(df_all['Year'].max())}" if len(df_all) else ""

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

_dataset_project_counts = (
    df_datasets.drop_duplicates(subset=["Project ID", "dataset"])
    .groupby("dataset")["Project ID"].nunique()
)
_ALL_DATASET_OPTIONS = (
    [{"label": "All datasets", "value": "ALL"}]
    + [
        {"label": f"{d}  ({n} {'project' if n == 1 else 'projects'})", "value": d}
        for d in sorted(df_datasets["dataset"].unique()) if d
        for n in [_dataset_project_counts.get(d, 0)]
    ]
)
_provider_project_counts = (
    df_datasets.drop_duplicates(subset=["Project ID", "provider"])
    .groupby("provider")["Project ID"].nunique()
)
_ALL_PROVIDER_OPTIONS = (
    [{"label": "All dataset source organisations", "value": "ALL"}]
    + [
        {"label": f"{p}  ({n} {'project' if n == 1 else 'projects'})", "value": p}
        for p in sorted(df_datasets["provider"].unique()) if p
        for n in [_provider_project_counts.get(p, 0)]
    ]
)
_institution_project_counts = (
    df_institutions.drop_duplicates(subset=["Project ID", "institution"])
    .groupby("institution")["Project ID"].nunique()
)
_ALL_INSTITUTION_OPTIONS = (
    [{"label": "All institutions", "value": "ALL"}]
    + [
        {"label": f"{i}  ({n} {'project' if n == 1 else 'projects'})", "value": i}
        for i in sorted(df_institutions["institution"].unique()) if i
        for n in [_institution_project_counts.get(i, 0)]
    ]
)


def _format_tre_provider(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


_tre_values = sorted({
    str(value).strip()
    for value in df_all["Secure Research Service"].dropna()
    if str(value).strip()
})
_tre_project_counts = (
    df_all.assign(_tre_value=df_all["Secure Research Service"].astype("string").str.strip())
    .dropna(subset=["_tre_value"])
    .query("_tre_value != ''")
    .groupby("_tre_value")["Project Row ID"].count()
)
_ALL_TRE_OPTIONS = (
    [{"label": "All processing environments", "value": "ALL"}]
    + [
        {
            "label": (
                f"{_format_tre_provider(value)}  "
                f"({_tre_project_counts.get(value, 0)} "
                f"{'project' if _tre_project_counts.get(value, 0) == 1 else 'projects'})"
            ),
            "value": value,
        }
        for value in _tre_values
    ]
)
