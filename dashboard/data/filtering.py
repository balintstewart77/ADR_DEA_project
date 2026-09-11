"""Data filtering, thematic merging, display shaping, and CSV export."""

import re
from collections.abc import Callable, Mapping

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
    _ALL_DATASET_OPTIONS,
    _ALL_PROVIDER_OPTIONS,
    _ALL_INSTITUTION_OPTIONS,
    _ALL_TRE_OPTIONS,
)
from dashboard.data.thematic import (
    df_thematic_projects,
    _THEMATIC_DOMAIN_OPTIONS,
    _THEMATIC_DOMAIN_COUNT_OPTIONS,
    _THEMATIC_PURPOSE_OPTIONS,
    _THEMATIC_TAG_OPTIONS,
    _DETERMINISTIC_RECORD_LINKAGE_OPTIONS,
    _DETERMINISTIC_COLLECTION_METHOD_OPTIONS,
    _DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS,
    _DETERMINISTIC_UNIT_OPTIONS,
    _DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS,
    _split_semicolon_values,
)
from dashboard.data.deterministic import (
    DETERMINISTIC_FACET_COLUMNS,
    RECORD_LINKAGE_COL,
    RECORD_LINKAGE_DISPLAY_LABELS,
    display_deterministic_set,
)
from dashboard.data.keys import _project_id_key, _title_key
from dashboard.data.year_filter import YearRange, filter_records_by_year


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


def _filter_by_record_ids(df: pd.DataFrame, record_ids) -> pd.DataFrame:
    if "Record ID" not in df.columns:
        return _filter_by_project_ids(df, record_ids)
    wanted = {str(value).strip() for value in record_ids if str(value).strip()}
    return df[df["Record ID"].astype(str).str.strip().isin(wanted)]


def _apply_dataset_filter(base: pd.DataFrame, dataset) -> pd.DataFrame:
    if not dataset or dataset == "ALL":
        return base
    if isinstance(dataset, str) and dataset.startswith("collection::"):
        selected_collection = dataset.split("::", 1)[1]
        if "collections" in base.columns:
            return base[
                base["collections"].apply(
                    lambda collections: selected_collection in collections
                    if isinstance(collections, list)
                    else False
                )
            ]
        matching_ids = set(
            df_all.loc[
                df_all["collections"].apply(lambda x: selected_collection in x),
                "Record ID" if "Record ID" in df_all.columns else "Project ID",
            ]
        )
        return _filter_by_record_ids(base, matching_ids)

    id_col = "Record ID" if "Record ID" in df_datasets.columns else "Project ID"
    matching_ids = set(df_datasets.loc[df_datasets["dataset"] == dataset, id_col])
    return _filter_by_record_ids(base, matching_ids)


def _apply_provider_filter(base: pd.DataFrame, provider) -> pd.DataFrame:
    if not provider or provider == "ALL":
        return base
    id_col = "Record ID" if "Record ID" in df_datasets.columns else "Project ID"
    matching_ids = set(df_datasets.loc[df_datasets["provider"] == provider, id_col])
    return _filter_by_record_ids(base, matching_ids)


def _apply_institution_filter(base: pd.DataFrame, institution) -> pd.DataFrame:
    if not institution or institution == "ALL":
        return base
    id_col = "Record ID" if "Record ID" in df_institutions.columns else "Project ID"
    matching_ids = set(
        df_institutions.loc[df_institutions["institution"] == institution, id_col]
    )
    return _filter_by_record_ids(base, matching_ids)


def _apply_tre_filter(base: pd.DataFrame, tre) -> pd.DataFrame:
    if not tre or tre == "ALL" or "Secure Research Service" not in base.columns:
        return base
    return base[
        base["Secure Research Service"].astype("string").str.strip() == str(tre).strip()
    ]


_REGISTER_FACET_PREDICATES: dict[str, Callable[[pd.DataFrame, object], pd.DataFrame]] = {
    "dataset": _apply_dataset_filter,
    "provider": _apply_provider_filter,
    "institution": _apply_institution_filter,
    "tre": _apply_tre_filter,
}


def _apply_register_filters(
    df: pd.DataFrame,
    search,
    dataset,
    provider,
    institution,
    tre,
    *,
    include_rationale_search: bool = False,
    excluded_facets=frozenset(),
) -> pd.DataFrame:
    """Apply shared register filters, with enriched-only rationale search opt-in.

    Facet counting passes ``excluded_facets`` to omit an entire current
    selection while retaining these exact table predicates for every other
    restriction.
    """
    base = df.copy()
    selected = {
        "dataset": dataset,
        "provider": provider,
        "institution": institution,
        "tre": tre,
    }
    excluded = set(excluded_facets or ())
    for facet, predicate in _REGISTER_FACET_PREDICATES.items():
        if facet not in excluded:
            base = predicate(base, selected[facet])

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
        if include_rationale_search:
            rationale = (
                base[RATIONALE_COL]
                if RATIONALE_COL in base.columns
                else pd.Series("", index=base.index)
            )
            mask |= rationale.astype("string").str.contains(
                search, case=False, na=False, regex=False,
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


def _merge_register_overlay(
    left: pd.DataFrame,
    right: pd.DataFrame,
    merge_keys: list[str],
    overlay_columns: list[str],
) -> pd.DataFrame:
    rename_map = {col: f"{col}__register" for col in overlay_columns}
    right_overlay = (
        right[merge_keys + overlay_columns]
        .drop_duplicates(subset=merge_keys, keep="first")
        .rename(columns=rename_map)
    )
    merged = left.merge(right_overlay, on=merge_keys, how="left")
    for col, overlay_col in rename_map.items():
        if overlay_col not in merged.columns:
            continue
        if col in merged.columns:
            merged[col] = merged[overlay_col].where(merged[overlay_col].notna(), merged[col])
        else:
            merged[col] = merged[overlay_col]
        merged = merged.drop(columns=overlay_col)
    return merged


def _overlay_clean_register_fields(source_df: pd.DataFrame, register_cols: list[str]) -> pd.DataFrame:
    base = source_df.copy()
    overlay_columns = [col for col in register_cols if col in df_all.columns]
    if not overlay_columns:
        return base

    if "Record ID" in base.columns and "Record ID" in df_all.columns:
        return _merge_register_overlay(
            base,
            df_all[["Record ID", *overlay_columns]].copy(),
            ["Record ID"],
            overlay_columns,
        )

    if "Project ID" not in base.columns or "Project ID" not in df_all.columns:
        return base

    left = base.copy()
    right = df_all[["Project ID", *overlay_columns]].copy()
    left[_MERGE_PROJECT_ID_KEY_COL] = left["Project ID"].apply(_project_id_key)
    right[_MERGE_PROJECT_ID_KEY_COL] = df_all["Project ID"].apply(_project_id_key)
    merge_keys = [_MERGE_PROJECT_ID_KEY_COL]

    if "Title" in base.columns and "Title" in df_all.columns:
        left[_MERGE_TITLE_KEY_COL] = left["Title"].apply(_title_key)
        right[_MERGE_TITLE_KEY_COL] = df_all["Title"].apply(_title_key)
        merge_keys.append(_MERGE_TITLE_KEY_COL)

    merged = _merge_register_overlay(left, right, merge_keys, overlay_columns)
    return merged.drop(columns=merge_keys, errors="ignore")


def _ensure_enriched_register_columns(source_df: pd.DataFrame) -> pd.DataFrame:
    base = source_df.copy()
    register_cols = [
        "Title",
        "Researchers",
        "Datasets Used",
        "Secure Research Service",
        "Accreditation Date",
    ]
    base = _overlay_clean_register_fields(base, register_cols)

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


_BROWSE_FACET_OPTIONS = {
    "dataset": _ALL_DATASET_OPTIONS,
    "provider": _ALL_PROVIDER_OPTIONS,
    "institution": _ALL_INSTITUTION_OPTIONS,
    "tre": _ALL_TRE_OPTIONS,
}
_ENRICHED_FACET_OPTIONS = {
    **_BROWSE_FACET_OPTIONS,
    "domain": _THEMATIC_DOMAIN_OPTIONS,
    "domain_count": _THEMATIC_DOMAIN_COUNT_OPTIONS,
    "purpose": _THEMATIC_PURPOSE_OPTIONS,
    "tag": _THEMATIC_TAG_OPTIONS,
    "record_linkage": _DETERMINISTIC_RECORD_LINKAGE_OPTIONS,
    "collection_method": _DETERMINISTIC_COLLECTION_METHOD_OPTIONS,
    "temporal_structure": _DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS,
    "unit": _DETERMINISTIC_UNIT_OPTIONS,
    "researcher_sector": _DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS,
}
_OPTION_COUNT_SUFFIX = re.compile(r"  \(\d+ projects?\)$")


def _canonical_option_label(option: Mapping) -> str:
    """Recover the static option's label without its legacy count suffix."""
    return _OPTION_COUNT_SUFFIX.sub("", str(option["label"]))


def _distinct_record_id_count(df: pd.DataFrame) -> int:
    if "Record ID" not in df.columns:
        raise KeyError("Facet counts require the unique Record ID")
    record_ids = df["Record ID"].astype("string").str.strip()
    if record_ids.isna().any() or record_ids.eq("").any():
        raise ValueError("Facet counts require non-blank Record ID values")
    return int(record_ids.nunique())


def _format_option_count(label: str, count: int) -> str:
    return f"{label}  ({count} {'project' if count == 1 else 'projects'})"


def _normalised_record_ids(df: pd.DataFrame) -> pd.Series:
    if "Record ID" not in df.columns:
        raise KeyError("Facet counts require the unique Record ID")
    record_ids = df["Record ID"].astype("string").str.strip()
    if record_ids.isna().any() or record_ids.eq("").any():
        raise ValueError("Facet counts require non-blank Record ID values")
    return record_ids


def _grouped_record_counts(record_ids: pd.Series, values: pd.Series) -> dict:
    """Count distinct record IDs by an already predicate-normalised value."""
    grouped = pd.DataFrame({"record_id": record_ids, "facet_value": values})
    grouped = grouped.dropna(subset=["facet_value"])
    grouped = grouped.drop_duplicates(subset=["record_id", "facet_value"])
    return grouped.groupby("facet_value")["record_id"].nunique().to_dict()


def _related_option_counts(
    base: pd.DataFrame,
    related: pd.DataFrame,
    value_column: str,
) -> dict | None:
    """Group relation-backed predicates by option without repeated base scans."""
    if "Record ID" not in base.columns or "Record ID" not in related.columns:
        return None
    base_ids = _normalised_record_ids(base)
    related_ids = related["Record ID"].astype("string").str.strip()
    relation = pd.DataFrame({
        "record_id": related_ids,
        "facet_value": related[value_column],
    })
    relation = relation[relation["record_id"].isin(set(base_ids))]
    return _grouped_record_counts(relation["record_id"], relation["facet_value"])


def _semicolon_option_counts(base: pd.DataFrame, column: str) -> dict:
    """Use the same semicolon parser as the option-matching predicate."""
    values = base[column].apply(_split_semicolon_values)
    expanded = pd.DataFrame({
        "record_id": _normalised_record_ids(base),
        "facet_value": values,
    }).explode("facet_value")
    return _grouped_record_counts(expanded["record_id"], expanded["facet_value"])


def _dataset_option_counts(base: pd.DataFrame, options: list[dict]) -> dict:
    counts = _related_option_counts(base, df_datasets, "dataset")
    if counts is None:
        return {}
    # Collections use a different established predicate. They are not in the
    # current authoritative universe, but retain exact fallback semantics.
    for option in options:
        value = option["value"]
        if isinstance(value, str) and value.startswith("collection::"):
            counts[value] = _distinct_record_id_count(_apply_dataset_filter(base, value))
    return counts


def _provider_option_counts(base: pd.DataFrame, _options: list[dict]) -> dict:
    return _related_option_counts(base, df_datasets, "provider") or {}


def _institution_option_counts(base: pd.DataFrame, _options: list[dict]) -> dict:
    return _related_option_counts(base, df_institutions, "institution") or {}


def _tre_option_counts(base: pd.DataFrame, _options: list[dict]) -> dict:
    return _grouped_record_counts(
        _normalised_record_ids(base),
        base["Secure Research Service"].astype("string").str.strip(),
    )


def _facet_options_with_dynamic_counts(
    base: pd.DataFrame,
    state: Mapping[str, object],
    option_universes: Mapping[str, list[dict]],
    apply_restrictions: Callable[[pd.DataFrame, Mapping[str, object], set[str]], pd.DataFrame],
    facet_predicates: Mapping[str, Callable[[pd.DataFrame, object], pd.DataFrame]],
    facet_count_functions: Mapping[str, Callable[[pd.DataFrame, list[dict]], dict]] | None = None,
) -> dict[str, list[dict]]:
    """Decorate fixed option universes using the tables' actual predicates.

    Each facet starts from the base record population, applies every active
    restriction other than that facet, then applies its existing predicate for
    each option.  The result is always a distinct-Record-ID count, so an
    expanded source table or repeated official Project ID cannot inflate it.
    """
    counted_options = {}
    for facet, options in option_universes.items():
        without_facet = apply_restrictions(base, state, {facet})
        predicate = facet_predicates[facet]
        counter = (facet_count_functions or {}).get(facet)
        grouped_counts = counter(without_facet, options) if counter else None
        decorated = []
        for option in options:
            result = dict(option)
            label = _canonical_option_label(option)
            if option["value"] != "ALL":
                count = (
                    grouped_counts.get(option["value"], 0)
                    if grouped_counts is not None
                    else _distinct_record_id_count(predicate(without_facet, option["value"]))
                )
                result["label"] = _format_option_count(label, count)
            else:
                # ALL is a reset sentinel, not an ordinary stored category.
                result["label"] = label
            decorated.append(result)
        counted_options[facet] = decorated
    return counted_options


def _apply_domain_filter(base: pd.DataFrame, domain) -> pd.DataFrame:
    if not domain or domain == "ALL":
        return base
    return base[_contains_semicolon_value(base["substantive_domains"], domain)]


def _apply_domain_count_filter(base: pd.DataFrame, domain_count) -> pd.DataFrame:
    # ``0`` is a real selectable category, not an absence-of-selection value.
    if domain_count is None or domain_count == "" or domain_count == "ALL":
        return base
    count = int(domain_count)
    return base[pd.to_numeric(base[SUBSTANTIVE_DOMAIN_COUNT_COL], errors="coerce") == count]


def _apply_purpose_filter(base: pd.DataFrame, purpose) -> pd.DataFrame:
    if not purpose or purpose == "ALL":
        return base
    return base[_contains_semicolon_value(base["analytical_purpose"], purpose)]


def _apply_tag_filter(base: pd.DataFrame, tag) -> pd.DataFrame:
    if not tag or tag == "ALL":
        return base
    return base[_contains_semicolon_value(base[CROSS_CUTTING_TAGS_COL], tag)]


def _apply_record_linkage_filter(base: pd.DataFrame, record_linkage) -> pd.DataFrame:
    if not record_linkage or record_linkage == "ALL":
        return base
    return base[_format_record_linkage(base[RECORD_LINKAGE_COL]) == record_linkage]


def _apply_collection_method_filter(base: pd.DataFrame, collection_method) -> pd.DataFrame:
    if not collection_method or collection_method == "ALL":
        return base
    return base[_contains_semicolon_value(base["dataset_collection_methods"], collection_method)]


def _apply_temporal_structure_filter(base: pd.DataFrame, temporal_structure) -> pd.DataFrame:
    if not temporal_structure or temporal_structure == "ALL":
        return base
    return base[_contains_semicolon_value(base["dataset_temporal_structures"], temporal_structure)]


def _apply_unit_filter(base: pd.DataFrame, unit) -> pd.DataFrame:
    if not unit or unit == "ALL":
        return base
    return base[_contains_semicolon_value(base["dataset_units"], unit)]


def _apply_researcher_sector_filter(base: pd.DataFrame, researcher_sector) -> pd.DataFrame:
    if not researcher_sector or researcher_sector == "ALL":
        return base
    return base[_contains_semicolon_value(base["researcher_sectors"], researcher_sector)]


_ENRICHED_DERIVED_FACET_PREDICATES = {
    "domain": _apply_domain_filter,
    "domain_count": _apply_domain_count_filter,
    "purpose": _apply_purpose_filter,
    "tag": _apply_tag_filter,
    "record_linkage": _apply_record_linkage_filter,
    "collection_method": _apply_collection_method_filter,
    "temporal_structure": _apply_temporal_structure_filter,
    "unit": _apply_unit_filter,
    "researcher_sector": _apply_researcher_sector_filter,
}
_ENRICHED_FACET_PREDICATES = {
    **_REGISTER_FACET_PREDICATES,
    **_ENRICHED_DERIVED_FACET_PREDICATES,
}
_BROWSE_FACET_COUNTERS = {
    "dataset": _dataset_option_counts,
    "provider": _provider_option_counts,
    "institution": _institution_option_counts,
    "tre": _tre_option_counts,
}


def _domain_count_option_counts(base: pd.DataFrame, _options: list[dict]) -> dict:
    return _grouped_record_counts(
        _normalised_record_ids(base),
        pd.to_numeric(base[SUBSTANTIVE_DOMAIN_COUNT_COL], errors="coerce"),
    )


def _record_linkage_option_counts(base: pd.DataFrame, _options: list[dict]) -> dict:
    return _grouped_record_counts(
        _normalised_record_ids(base), _format_record_linkage(base[RECORD_LINKAGE_COL]),
    )


_ENRICHED_FACET_COUNTERS = {
    **_BROWSE_FACET_COUNTERS,
    "domain": lambda base, _options: _semicolon_option_counts(base, "substantive_domains"),
    "domain_count": _domain_count_option_counts,
    "purpose": lambda base, _options: _semicolon_option_counts(base, "analytical_purpose"),
    "tag": lambda base, _options: _semicolon_option_counts(base, CROSS_CUTTING_TAGS_COL),
    "record_linkage": _record_linkage_option_counts,
    "collection_method": lambda base, _options: _semicolon_option_counts(
        base, "dataset_collection_methods",
    ),
    "temporal_structure": lambda base, _options: _semicolon_option_counts(
        base, "dataset_temporal_structures",
    ),
    "unit": lambda base, _options: _semicolon_option_counts(base, "dataset_units"),
    "researcher_sector": lambda base, _options: _semicolon_option_counts(
        base, "researcher_sectors",
    ),
}


def _enriched_register_base(eligible_record_ids=None) -> pd.DataFrame:
    base = _ensure_enriched_register_columns(df_thematic_projects)
    base = base[_classified_mask(base)]
    if eligible_record_ids is not None:
        base = _filter_by_record_ids(base, eligible_record_ids)
    return base


def _apply_enriched_register_filters(
    base: pd.DataFrame,
    state: Mapping[str, object],
    excluded_facets=frozenset(),
) -> pd.DataFrame:
    excluded = set(excluded_facets or ())
    filtered = _apply_register_filters(
        base,
        state.get("search"),
        state.get("dataset"),
        state.get("provider"),
        state.get("institution"),
        state.get("tre"),
        include_rationale_search=True,
        excluded_facets=excluded,
    )
    for facet, predicate in _ENRICHED_DERIVED_FACET_PREDICATES.items():
        if facet not in excluded:
            filtered = predicate(filtered, state.get(facet, "ALL"))
    return filtered


def _get_browse_facet_options(
    search,
    dataset,
    provider,
    institution,
    tre,
    accreditation_year_range,
    accreditation_year_min,
    accreditation_year_max,
) -> dict[str, list[dict]]:
    state = {
        "search": search,
        "dataset": dataset,
        "provider": provider,
        "institution": institution,
        "tre": tre,
    }
    bounds = YearRange(int(accreditation_year_min), int(accreditation_year_max))

    def apply_restrictions(base, selected, excluded):
        filtered = _apply_register_filters(
            base,
            selected["search"],
            selected["dataset"],
            selected["provider"],
            selected["institution"],
            selected["tre"],
            excluded_facets=excluded,
        )
        return filter_records_by_year(filtered, accreditation_year_range, bounds)

    return _facet_options_with_dynamic_counts(
        df_all,
        state,
        _BROWSE_FACET_OPTIONS,
        apply_restrictions,
        _REGISTER_FACET_PREDICATES,
        _BROWSE_FACET_COUNTERS,
    )


def _get_enriched_register_facet_options(
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
    eligible_record_ids=None,
    accreditation_year_range=None,
    accreditation_year_min=None,
    accreditation_year_max=None,
) -> dict[str, list[dict]]:
    state = {
        "search": search,
        "dataset": dataset_filter,
        "provider": provider_filter,
        "institution": institution_filter,
        "tre": tre_filter,
        "domain": domain_filter,
        "domain_count": domain_count_filter,
        "purpose": purpose_filter,
        "tag": tag_filter,
        "record_linkage": record_linkage_filter,
        "collection_method": collection_method_filter,
        "temporal_structure": temporal_structure_filter,
        "unit": unit_filter,
        "researcher_sector": researcher_sector_filter,
    }
    bounds = YearRange(int(accreditation_year_min), int(accreditation_year_max))

    def apply_restrictions(base, selected, excluded):
        filtered = _apply_enriched_register_filters(base, selected, excluded)
        return filter_records_by_year(filtered, accreditation_year_range, bounds)

    return _facet_options_with_dynamic_counts(
        _enriched_register_base(eligible_record_ids),
        state,
        _ENRICHED_FACET_OPTIONS,
        apply_restrictions,
        _ENRICHED_FACET_PREDICATES,
        _ENRICHED_FACET_COUNTERS,
    )


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
    eligible_record_ids=None,
    include_record_id=False,
) -> tuple[pd.DataFrame, str]:
    base = _enriched_register_base(eligible_record_ids)
    n_classified_total = len(base)
    state = {
        "search": search,
        "dataset": dataset_filter,
        "provider": provider_filter,
        "institution": institution_filter,
        "tre": tre_filter,
        "domain": domain_filter,
        "domain_count": domain_count_filter,
        "purpose": purpose_filter,
        "tag": tag_filter,
        "record_linkage": record_linkage_filter,
        "collection_method": collection_method_filter,
        "temporal_structure": temporal_structure_filter,
        "unit": unit_filter,
        "researcher_sector": researcher_sector_filter,
    }
    base = _apply_enriched_register_filters(base, state)

    n_displayed = len(base)
    count_text = (
        f"Showing {n_displayed:,} of {n_classified_total:,} classified projects"
    )

    display = base.copy()
    for col in _DERIVED_CLASSIFICATION_COLUMNS:
        display[col] = display[col].fillna(DERIVED_EMPTY_VALUE)
    # Tag is blank (not "—") when no equity/demographic lens applies. Preserve
    # missing rationale values so table sorting retains DataTable's nulls-last policy.
    if CROSS_CUTTING_TAGS_COL in display.columns:
        display[CROSS_CUTTING_TAGS_COL] = display[CROSS_CUTTING_TAGS_COL].fillna("")
    if RATIONALE_COL in display.columns:
        rationale = display[RATIONALE_COL]
        display[RATIONALE_COL] = rationale.astype("object").where(rationale.notna(), None)
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

    columns = list(_ENRICHED_REGISTER_DISPLAY_COLUMNS)
    if include_record_id:
        if "Record ID" not in display.columns:
            raise KeyError("Enriched Register rows require the unique Record ID")
        columns.insert(0, "Record ID")
    return display[columns], count_text


def _csv_date_stamp() -> str:
    return pd.Timestamp.today().strftime("%Y-%m-%d")
