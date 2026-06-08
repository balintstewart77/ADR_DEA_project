"""Thematic analysis data loading and filter option building."""

import os
from collections import Counter
from itertools import combinations

import pandas as pd

from dashboard.config import (
    CLASSIFICATION_DIR,
    SUBSTANTIVE_DOMAIN_COUNT_COL,
    CROSS_CUTTING_TAGS_COL,
    TAG_LABELS,
    PURPOSE_LABELS,
    _PROJECT_ID_KEY_COL,
)
from dashboard.data.deterministic import RECORD_LINKAGE_COL, load_register_properties
from dashboard.data.keys import _project_id_key


_DETERMINISTIC_ENRICHED_COLUMNS = [
    RECORD_LINKAGE_COL,
]


def _filter_label_with_count(label: str, count: int) -> str:
    return f"{label}  ({count} {'project' if count == 1 else 'projects'})"


def _split_semicolon_values(value) -> list[str]:
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def _count_substantive_domains(value):
    domains = _split_semicolon_values(value)
    return len(domains) if domains else pd.NA


def _merge_deterministic_facets(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    base = df.copy()
    for col in columns:
        if col in base.columns:
            base = base.drop(columns=col)

    if "Record ID" not in base.columns:
        for col in columns:
            base[col] = ""
        return base

    properties = load_register_properties(columns=columns)
    if properties.empty:
        for col in columns:
            base[col] = ""
        return base

    merged = base.merge(properties, on="Record ID", how="left")
    for col in columns:
        if col not in merged.columns:
            merged[col] = ""
        merged[col] = merged[col].fillna("").astype(str)
    return merged


def _domain_count_label(value: int) -> str:
    return f"{value} {'domain' if value == 1 else 'domains'}"


def _has_any_tag(value) -> bool:
    return any(tag in _split_semicolon_values(value) for tag in TAG_LABELS)


def _tag_series(df: pd.DataFrame) -> pd.Series:
    """Cross-cutting-tag column as strings, tolerant of the column being absent."""
    if CROSS_CUTTING_TAGS_COL in df.columns:
        return df[CROSS_CUTTING_TAGS_COL]
    return pd.Series("", index=df.index, dtype=object)


def _domain_crosstab(df: pd.DataFrame, other_col: str, other_multi: bool, col_order) -> pd.DataFrame:
    """Substantive-domain x classification-value counts over ALL domains.

    Layer A is non-hierarchical, so a project is counted once per assigned domain
    (column totals can exceed the project count). Returns a frame whose first
    column is ``domain`` with the remaining columns holding counts — the shape
    ``make_cross_heatmap`` expects. Rows are ordered by total descending; columns
    follow taxonomy order where known.
    """
    if "substantive_domains" not in df.columns or other_col not in df.columns:
        return pd.DataFrame(columns=["domain"])
    work = df[["substantive_domains", other_col]].copy()
    work["domain"] = work["substantive_domains"].apply(_split_semicolon_values)
    work = work.explode("domain")
    if other_multi:
        work[other_col] = work[other_col].apply(_split_semicolon_values)
        work = work.explode(other_col)
    work = work[
        work["domain"].notna()
        & (work["domain"].astype(str).str.strip() != "")
        & work[other_col].notna()
        & (work[other_col].astype(str).str.strip() != "")
    ].reset_index(drop=True)  # explode leaves duplicate index labels; crosstab rejects them
    if work.empty:
        return pd.DataFrame(columns=["domain"])
    ct = pd.crosstab(work["domain"], work[other_col])
    ordered = [c for c in col_order if c in ct.columns] + [c for c in ct.columns if c not in col_order]
    ct = ct[ordered]
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False, kind="stable").index]
    return ct.reset_index()


def _domain_cooccurrence(df: pd.DataFrame) -> pd.DataFrame:
    """Square domain x domain matrix of how often each pair co-occurs in a project.

    The diagonal holds each domain's project total; off-diagonal cells hold the
    number of projects carrying both domains. Domains are ordered by total
    (descending). The "Unclear" fallback is excluded — it cannot co-occur with a
    real domain by construction.
    """
    if "substantive_domains" not in df.columns:
        return pd.DataFrame()
    project_domains = []
    for value in df["substantive_domains"]:
        domains = sorted(
            d for d in set(_split_semicolon_values(value))
            if not d.lower().startswith("unclear")
        )
        if domains:
            project_domains.append(domains)

    totals: Counter = Counter()
    pairs: Counter = Counter()
    for domains in project_domains:
        for domain in domains:
            totals[domain] += 1
        for a, b in combinations(domains, 2):
            pairs[(a, b)] += 1
            pairs[(b, a)] += 1
    if not totals:
        return pd.DataFrame()

    order = [domain for domain, _ in totals.most_common()]
    matrix = pd.DataFrame(0, index=order, columns=order, dtype=int)
    for domain in order:
        matrix.loc[domain, domain] = totals[domain]
    for (a, b), count in pairs.items():
        matrix.loc[a, b] = count
    return matrix


def load_thematic_data(thematic_dir):
    """Returns (data_dict, available_flag)."""
    try:
        df_thematic_a = pd.read_csv(os.path.join(thematic_dir, "layer_a_by_year.csv"), encoding="utf-8-sig")
        df_thematic_c = pd.read_csv(os.path.join(thematic_dir, "layer_c_by_year.csv"), encoding="utf-8-sig")
        df_thematic_a_totals = pd.read_csv(os.path.join(thematic_dir, "layer_a_totals.csv"), encoding="utf-8-sig")
        df_thematic_c_totals = pd.read_csv(os.path.join(thematic_dir, "layer_c_totals.csv"), encoding="utf-8-sig")
        with open(os.path.join(thematic_dir, "layer_summary.txt"), "r", encoding="utf-8") as _f:
            thematic_narrative = _f.read()
        df_thematic_projects = pd.read_csv(
            os.path.join(thematic_dir, "layer_classifications.csv"), encoding="utf-8-sig",
        )
        df_thematic_projects = _merge_deterministic_facets(
            df_thematic_projects,
            _DETERMINISTIC_ENRICHED_COLUMNS,
        )
        df_thematic_projects[SUBSTANTIVE_DOMAIN_COUNT_COL] = (
            df_thematic_projects["substantive_domains"]
            .apply(_count_substantive_domains)
            .astype("Int64")
        )
        thematic_project_count = len(df_thematic_projects)

        # Cross-layer heatmaps, derived over ALL substantive domains (multi-label:
        # a project is counted once per assigned domain), replacing the legacy
        # top-6 "primary domain" cross-tabs.
        df_cross_domain_purpose = _domain_crosstab(
            df_thematic_projects, "analytical_purpose", True, PURPOSE_LABELS
        )

        # How often pairs of substantive domains co-occur in the same project.
        df_domain_cooccurrence = _domain_cooccurrence(df_thematic_projects)

        # Apply project-id keying on df_thematic_projects
        if "Project ID" in df_thematic_projects.columns:
            df_thematic_projects[_PROJECT_ID_KEY_COL] = df_thematic_projects["Project ID"].apply(_project_id_key)

        # Build filter options for the thematic browse table
        _domain_project_counts = {}
        for domains in df_thematic_projects["substantive_domains"].dropna():
            for domain in set(_split_semicolon_values(domains)):
                _domain_project_counts[domain] = _domain_project_counts.get(domain, 0) + 1
        _all_domains = sorted({
            domain
            for domains in df_thematic_projects["substantive_domains"].dropna()
            for domain in _split_semicolon_values(domains)
        })
        _thematic_domain_options = (
            [{"label": "All domains", "value": "ALL"}]
            + [
                {"label": _filter_label_with_count(d, _domain_project_counts.get(d, 0)), "value": d}
                for d in _all_domains
            ]
        )
        _domain_count_project_counts = (
            df_thematic_projects[SUBSTANTIVE_DOMAIN_COUNT_COL]
            .dropna()
            .value_counts()
            .sort_index()
        )
        _thematic_domain_count_options = (
            [{"label": "All domain counts", "value": "ALL"}]
            + [
                {
                    "label": _filter_label_with_count(
                        _domain_count_label(int(domain_count)),
                        int(count),
                    ),
                    "value": int(domain_count),
                }
                for domain_count, count in _domain_count_project_counts.items()
            ]
        )
        _purpose_project_counts = {}
        for purposes in df_thematic_projects["analytical_purpose"].dropna():
            for purpose in set(_split_semicolon_values(purposes)):
                _purpose_project_counts[purpose] = _purpose_project_counts.get(purpose, 0) + 1
        _all_purposes = sorted({
            purpose
            for purposes in df_thematic_projects["analytical_purpose"].dropna()
            for purpose in _split_semicolon_values(purposes)
        })
        _thematic_purpose_options = (
            [{"label": "All purposes", "value": "ALL"}]
            + [
                {"label": _filter_label_with_count(p, _purpose_project_counts.get(p, 0)), "value": p}
                for p in _all_purposes
            ]
        )

        # Cross-cutting tag (e.g. demographic-disparities / equity) — empty for
        # most projects, so it is surfaced as its own filter and charts rather
        # than as a layer.
        _tag_series_values = _tag_series(df_thematic_projects)
        _tag_project_counts = {}
        for tags in _tag_series_values.dropna():
            for tag in set(_split_semicolon_values(tags)):
                _tag_project_counts[tag] = _tag_project_counts.get(tag, 0) + 1
        _all_tags = [t for t in TAG_LABELS if t in _tag_project_counts] or sorted(_tag_project_counts)
        _thematic_tag_options = (
            [{"label": "All projects", "value": "ALL"}]
            + [
                {"label": _filter_label_with_count(t, _tag_project_counts.get(t, 0)), "value": t}
                for t in _all_tags
            ]
        )

        _tagged_mask = _tag_series_values.apply(_has_any_tag)
        thematic_tagged_count = int(_tagged_mask.sum())

        # Tag prevalence by year (one line per tag; explicit zeros so dips show).
        if "Year" in df_thematic_projects.columns:
            _years = sorted(int(y) for y in df_thematic_projects["Year"].dropna().unique())
            _total_by_year = df_thematic_projects.groupby("Year").size()
            _tag_year_rows = []
            for tag in TAG_LABELS:
                _tag_mask = _tag_series_values.apply(
                    lambda v, t=tag: t in _split_semicolon_values(v)
                )
                _cnt_by_year = df_thematic_projects[_tag_mask].groupby("Year").size()
                for y in _years:
                    total = int(_total_by_year.get(y, 0))
                    count = int(_cnt_by_year.get(y, 0))
                    _tag_year_rows.append({
                        "Year": y,
                        "tag": tag,
                        "count": count,
                        "total": total,
                        "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
                    })
            df_thematic_tag_by_year = pd.DataFrame(_tag_year_rows)
        else:
            df_thematic_tag_by_year = pd.DataFrame()

        # Which domains the tagged projects fall in (where the equity lens applies).
        _tag_domain_counts = {}
        for domains in df_thematic_projects.loc[_tagged_mask, "substantive_domains"].dropna():
            for domain in _split_semicolon_values(domains):
                _tag_domain_counts[domain] = _tag_domain_counts.get(domain, 0) + 1
        df_thematic_tag_by_domain = pd.DataFrame(
            sorted(_tag_domain_counts.items(), key=lambda kv: kv[1], reverse=True),
            columns=["domain", "count"],
        )

        return {
            "df_thematic_a": df_thematic_a,
            "df_thematic_c": df_thematic_c,
            "df_thematic_a_totals": df_thematic_a_totals,
            "df_thematic_c_totals": df_thematic_c_totals,
            "df_cross_domain_purpose": df_cross_domain_purpose,
            "df_thematic_projects": df_thematic_projects,
            "df_thematic_tag_by_year": df_thematic_tag_by_year,
            "df_thematic_tag_by_domain": df_thematic_tag_by_domain,
            "df_domain_cooccurrence": df_domain_cooccurrence,
            "THEMATIC_NARRATIVE": thematic_narrative,
            "THEMATIC_PROJECT_COUNT": thematic_project_count,
            "THEMATIC_TAGGED_COUNT": thematic_tagged_count,
            "_THEMATIC_DOMAIN_OPTIONS": _thematic_domain_options,
            "_THEMATIC_DOMAIN_COUNT_OPTIONS": _thematic_domain_count_options,
            "_THEMATIC_PURPOSE_OPTIONS": _thematic_purpose_options,
            "_THEMATIC_TAG_OPTIONS": _thematic_tag_options,
        }, True
    except (FileNotFoundError, KeyError):
        return {
            "df_thematic_a": pd.DataFrame(),
            "df_thematic_c": pd.DataFrame(),
            "df_thematic_a_totals": pd.DataFrame(),
            "df_thematic_c_totals": pd.DataFrame(),
            "df_cross_domain_purpose": pd.DataFrame(),
            "df_thematic_projects": pd.DataFrame(),
            "df_thematic_tag_by_year": pd.DataFrame(),
            "df_thematic_tag_by_domain": pd.DataFrame(),
            "df_domain_cooccurrence": pd.DataFrame(),
            "THEMATIC_NARRATIVE": "",
            "THEMATIC_PROJECT_COUNT": 0,
            "THEMATIC_TAGGED_COUNT": 0,
            "_THEMATIC_DOMAIN_OPTIONS": [],
            "_THEMATIC_DOMAIN_COUNT_OPTIONS": [],
            "_THEMATIC_PURPOSE_OPTIONS": [],
            "_THEMATIC_TAG_OPTIONS": [],
        }, False


_thematic_data, THEMATIC_DATA_AVAILABLE = load_thematic_data(CLASSIFICATION_DIR)

# Unpack for convenient module-level access
df_thematic_a = _thematic_data["df_thematic_a"]
df_thematic_c = _thematic_data["df_thematic_c"]
df_thematic_a_totals = _thematic_data["df_thematic_a_totals"]
df_thematic_c_totals = _thematic_data["df_thematic_c_totals"]
df_cross_domain_purpose = _thematic_data["df_cross_domain_purpose"]
df_thematic_projects = _thematic_data["df_thematic_projects"]
df_thematic_tag_by_year = _thematic_data["df_thematic_tag_by_year"]
df_thematic_tag_by_domain = _thematic_data["df_thematic_tag_by_domain"]
df_domain_cooccurrence = _thematic_data["df_domain_cooccurrence"]
THEMATIC_NARRATIVE = _thematic_data["THEMATIC_NARRATIVE"]
THEMATIC_PROJECT_COUNT = _thematic_data["THEMATIC_PROJECT_COUNT"]
THEMATIC_TAGGED_COUNT = _thematic_data["THEMATIC_TAGGED_COUNT"]
_THEMATIC_DOMAIN_OPTIONS = _thematic_data["_THEMATIC_DOMAIN_OPTIONS"]
_THEMATIC_DOMAIN_COUNT_OPTIONS = _thematic_data["_THEMATIC_DOMAIN_COUNT_OPTIONS"]
_THEMATIC_PURPOSE_OPTIONS = _thematic_data["_THEMATIC_PURPOSE_OPTIONS"]
_THEMATIC_TAG_OPTIONS = _thematic_data["_THEMATIC_TAG_OPTIONS"]
