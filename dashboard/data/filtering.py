"""Data filtering, thematic merging, display shaping, and CSV export."""

import numpy as np
import pandas as pd

from dashboard.config import (
    _PROJECT_ID_KEY_COL,
    _MERGE_PROJECT_ID_KEY_COL,
    _MERGE_TITLE_KEY_COL,
    _DERIVED_CLASSIFICATION_COLUMNS,
    _ENRICHED_DERIVED_COLUMNS,
    _ENRICHED_REGISTER_DISPLAY_COLUMNS,
    _BROWSE_DISPLAY_COLUMNS,
    DERIVED_EMPTY_VALUE,
    SUBSTANTIVE_DOMAIN_COUNT_COL,
    CROSS_CUTTING_TAGS_COL,
    RATIONALE_COL,
)
from dashboard.data.registry import (
    df_all,
    df_datasets,
    df_institutions,
    _format_tre_provider,
)
from dashboard.data.thematic import df_thematic_projects
from dashboard.data.deterministic import (
    DETERMINISTIC_FACET_COLUMNS,
    RECORD_LINKAGE_COL,
    RECORD_LINKAGE_DISPLAY_LABELS,
    display_deterministic_set,
)
from dashboard.data.keys import _project_id_key, _title_key


def _filter_by_project_ids(df: pd.DataFrame, project_ids) -> pd.DataFrame:
    matching_keys = {
        key for key in (_project_id_key(value) for value in project_ids)
        if key
    }
    project_key = (
        df[_PROJECT_ID_KEY_COL]
        if _PROJECT_ID_KEY_COL in df.columns
        else df["Project ID"].apply(_project_id_key)
    )
    return df[project_key.isin(matching_keys)]


def _apply_register_filters(df: pd.DataFrame, search, dataset, provider, institution, tre) -> pd.DataFrame:
    """Apply the common register-side filters used by Project Explorer and Enriched Register."""
    base = df.copy()

    if dataset and dataset != "ALL":
        if isinstance(dataset, str) and dataset.startswith("collection::"):
            selected_collection = dataset.split("::", 1)[1]
            if "collections" in base.columns:
                base = base[
                    base["collections"].apply(
                        lambda collections: selected_collection in collections
                        if isinstance(collections, list)
                        else False
                    )
                ]
            else:
                matching_pids = set(
                    df_all.loc[
                        df_all["collections"].apply(lambda x: selected_collection in x),
                        "Project ID",
                    ]
                )
                base = _filter_by_project_ids(base, matching_pids)
        else:
            matching_pids = set(
                df_datasets.loc[df_datasets["dataset"] == dataset, "Project ID"]
            )
            base = _filter_by_project_ids(base, matching_pids)

    if provider and provider != "ALL":
        matching_pids = set(
            df_datasets.loc[df_datasets["provider"] == provider, "Project ID"]
        )
        base = _filter_by_project_ids(base, matching_pids)

    if institution and institution != "ALL":
        matching_pids = set(
            df_institutions.loc[df_institutions["institution"] == institution, "Project ID"]
        )
        base = _filter_by_project_ids(base, matching_pids)

    if tre and tre != "ALL" and "Secure Research Service" in base.columns:
        base = base[
            base["Secure Research Service"].astype("string").str.strip() == str(tre).strip()
        ]

    if search:
        project_id = (
            base["Project ID"]
            if "Project ID" in base.columns
            else pd.Series("", index=base.index)
        )
        title = base["Title"] if "Title" in base.columns else pd.Series("", index=base.index)
        researchers = (
            base["Researchers"]
            if "Researchers" in base.columns
            else pd.Series("", index=base.index)
        )
        mask = (
            project_id.astype(str).str.contains(search, case=False, na=False, regex=False)
            | title.astype(str).str.contains(search, case=False, na=False, regex=False)
            | researchers.astype(str).str.contains(search, case=False, na=False, regex=False)
        )
        base = base[mask]

    return base


def _merge_thematic_classifications(register_df: pd.DataFrame) -> pd.DataFrame:
    base = register_df.copy()
    derived_cols = [
        col for col in _ENRICHED_DERIVED_COLUMNS
        if col in df_thematic_projects.columns
    ]
    for col in _ENRICHED_DERIVED_COLUMNS:
        if col in base.columns:
            base = base.drop(columns=col)

    if not derived_cols:
        for col in _ENRICHED_DERIVED_COLUMNS:
            base[col] = np.nan
        return base

    left = base.copy()
    right = df_thematic_projects[derived_cols].copy()
    left[_MERGE_PROJECT_ID_KEY_COL] = left["Project ID"].apply(_project_id_key)
    right[_MERGE_PROJECT_ID_KEY_COL] = df_thematic_projects["Project ID"].apply(_project_id_key)
    merge_keys = [_MERGE_PROJECT_ID_KEY_COL]
    if "Title" in base.columns and "Title" in df_thematic_projects.columns:
        left[_MERGE_TITLE_KEY_COL] = left["Title"].apply(_title_key)
        right[_MERGE_TITLE_KEY_COL] = df_thematic_projects["Title"].apply(_title_key)
        merge_keys = [_MERGE_PROJECT_ID_KEY_COL, _MERGE_TITLE_KEY_COL]

    right = (
        right[merge_keys + derived_cols]
        .drop_duplicates(subset=merge_keys, keep="first")
    )
    merged = left.merge(right, on=merge_keys, how="left")
    merged = merged.drop(columns=merge_keys)
    for col in _ENRICHED_DERIVED_COLUMNS:
        if col not in merged.columns:
            merged[col] = np.nan
    return merged


def _ensure_enriched_register_columns(source_df: pd.DataFrame) -> pd.DataFrame:
    base = source_df.copy()
    register_cols = [
        "Title",
        "Researchers",
        "Datasets Used",
        "Secure Research Service",
        "Accreditation Date",
    ]
    missing_register_cols = [
        col for col in register_cols
        if col not in base.columns
    ]
    if missing_register_cols:
        left = base.copy()
        right = df_all[missing_register_cols].copy()
        left[_MERGE_PROJECT_ID_KEY_COL] = left["Project ID"].apply(_project_id_key)
        right[_MERGE_PROJECT_ID_KEY_COL] = df_all["Project ID"].apply(_project_id_key)
        merge_keys = [_MERGE_PROJECT_ID_KEY_COL]
        if "Title" in base.columns and "Title" in df_all.columns:
            left[_MERGE_TITLE_KEY_COL] = left["Title"].apply(_title_key)
            right[_MERGE_TITLE_KEY_COL] = df_all["Title"].apply(_title_key)
            merge_keys = [_MERGE_PROJECT_ID_KEY_COL, _MERGE_TITLE_KEY_COL]
            missing_register_cols = [
                col for col in missing_register_cols
                if col != "Title"
            ]
            right = df_all[missing_register_cols].copy()
            right[_MERGE_PROJECT_ID_KEY_COL] = df_all["Project ID"].apply(_project_id_key)
            right[_MERGE_TITLE_KEY_COL] = df_all["Title"].apply(_title_key)
        right = (
            right[merge_keys + missing_register_cols]
            .drop_duplicates(subset=merge_keys, keep="first")
        )
        base = left.merge(right, on=merge_keys, how="left").drop(columns=merge_keys)

    if any(col not in base.columns for col in _ENRICHED_DERIVED_COLUMNS):
        base = _merge_thematic_classifications(base)

    for col in _ENRICHED_REGISTER_DISPLAY_COLUMNS:
        if col not in base.columns:
            base[col] = np.nan
    return base


def _contains_semicolon_value(series: pd.Series, value: str) -> pd.Series:
    return series.notna() & series.fillna("").astype(str).apply(
        lambda values: value in [part.strip() for part in values.split(";")]
    )


def _classified_mask(df: pd.DataFrame) -> pd.Series:
    return df[_DERIVED_CLASSIFICATION_COLUMNS].notna().all(axis=1)


def _compute_classified_register_count() -> int:
    if not len(df_thematic_projects):
        return 0
    classified = _merge_thematic_classifications(df_all)
    return int(_classified_mask(classified).sum())


_CLASSIFIED_REGISTER_COUNT = _compute_classified_register_count()


def _format_display_dates(series: pd.Series) -> pd.Series:
    return (
        pd.to_datetime(series, errors="coerce")
        .dt.strftime("%d %b %Y")
        .fillna("")
    )


def _format_record_linkage(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()
    labels = values.map(RECORD_LINKAGE_DISPLAY_LABELS)
    return labels.where(labels.notna(), values).replace("", DERIVED_EMPTY_VALUE)


def _format_deterministic_facet(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()
    return values.apply(display_deterministic_set).replace("", DERIVED_EMPTY_VALUE)


def _get_browse_display_df(search, dataset, provider, institution, tre) -> pd.DataFrame:
    base = _apply_register_filters(
        df_all,
        search,
        dataset,
        provider,
        institution,
        tre,
    )
    display = base.copy()
    display["Secure Research Service"] = display["Secure Research Service"].apply(_format_tre_provider)
    display["Accreditation Date"] = _format_display_dates(display["Accreditation Date"])
    return display[_BROWSE_DISPLAY_COLUMNS]


def _get_enriched_register_display_df(
    search,
    dataset_filter,
    provider_filter,
    institution_filter,
    tre_filter,
    domain_filter,
    domain_count_filter,
    purpose_filter,
    tag_filter,
    record_linkage_filter="ALL",
    collection_method_filter="ALL",
    temporal_structure_filter="ALL",
    unit_filter="ALL",
    researcher_sector_filter="ALL",
) -> tuple[pd.DataFrame, str]:
    base = _ensure_enriched_register_columns(df_thematic_projects)
    base = base[_classified_mask(base)]

    base = _apply_register_filters(
        base,
        search,
        dataset_filter,
        provider_filter,
        institution_filter,
        tre_filter,
    )

    if domain_filter and domain_filter != "ALL":
        base = base[_contains_semicolon_value(base["substantive_domains"], domain_filter)]
    if domain_count_filter and domain_count_filter != "ALL":
        domain_count = int(domain_count_filter)
        base = base[
            pd.to_numeric(base[SUBSTANTIVE_DOMAIN_COUNT_COL], errors="coerce") == domain_count
        ]
    if purpose_filter and purpose_filter != "ALL":
        base = base[_contains_semicolon_value(base["analytical_purpose"], purpose_filter)]
    if tag_filter and tag_filter != "ALL":
        base = base[_contains_semicolon_value(base[CROSS_CUTTING_TAGS_COL], tag_filter)]
    if record_linkage_filter and record_linkage_filter != "ALL":
        base = base[_format_record_linkage(base[RECORD_LINKAGE_COL]) == record_linkage_filter]
    if collection_method_filter and collection_method_filter != "ALL":
        base = base[
            _contains_semicolon_value(
                base["dataset_collection_methods"],
                collection_method_filter,
            )
        ]
    if temporal_structure_filter and temporal_structure_filter != "ALL":
        base = base[
            _contains_semicolon_value(
                base["dataset_temporal_structures"],
                temporal_structure_filter,
            )
        ]
    if unit_filter and unit_filter != "ALL":
        base = base[_contains_semicolon_value(base["dataset_units"], unit_filter)]
    if researcher_sector_filter and researcher_sector_filter != "ALL":
        base = base[
            _contains_semicolon_value(base["researcher_sectors"], researcher_sector_filter)
        ]

    n_displayed = len(base)
    n_classified_total = _CLASSIFIED_REGISTER_COUNT
    count_text = (
        f"Showing {n_displayed:,} of {n_classified_total:,} classified projects"
    )

    display = base.copy()
    for col in _DERIVED_CLASSIFICATION_COLUMNS:
        display[col] = display[col].fillna(DERIVED_EMPTY_VALUE)
    # Tag is blank (not "—") when no equity/demographic lens applies; rationale
    # is always present for a classified row but filled defensively.
    for col in (CROSS_CUTTING_TAGS_COL, RATIONALE_COL):
        if col in display.columns:
            display[col] = display[col].fillna("")
    domain_counts = pd.to_numeric(display[SUBSTANTIVE_DOMAIN_COUNT_COL], errors="coerce").astype("Int64")
    display[SUBSTANTIVE_DOMAIN_COUNT_COL] = (
        domain_counts.astype("object").where(domain_counts.notna(), None)
    )
    display["Secure Research Service"] = display["Secure Research Service"].apply(_format_tre_provider)
    display["Accreditation Date"] = _format_display_dates(display["Accreditation Date"])
    for col in DETERMINISTIC_FACET_COLUMNS:
        if col not in display.columns:
            continue
        if col == RECORD_LINKAGE_COL:
            display[col] = _format_record_linkage(display[col])
        else:
            display[col] = _format_deterministic_facet(display[col])

    return display[_ENRICHED_REGISTER_DISPLAY_COLUMNS], count_text


def _csv_date_stamp() -> str:
    return pd.Timestamp.today().strftime("%Y-%m-%d")
