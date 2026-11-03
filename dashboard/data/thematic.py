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
from dashboard.taxonomy import DOMAIN_LABELS
from dashboard.data.deterministic import (
    DETERMINISTIC_FACET_COLUMNS,
    MATCHED_PRODUCTS_COL,
    RECORD_LINKAGE_COMPONENT_DOMAINS_COL,
    RECORD_LINKAGE_DISPLAY_LABELS,
    display_deterministic_value,
    load_register_properties,
)
from dashboard.data.keys import _project_id_key
from dashboard.data.uptake import LINKED_PRODUCTS, product_short_label
from dashboard.data.year_filter import (
    YearRange,
    is_all_years,
    parse_accreditation_dates,
    year_selection_mask,
)


RESEARCHER_SECTOR_HEATMAP_ORDER = ["academic", "government", "third-sector", "commercial"]
DOMAIN_BREADTH_ORDER = ["1 domain", "2 domains", "3+ domains"]
DOMAIN_BREADTH_COVERAGE_COLUMNS = [
    "period_label",
    "dated_selected_records",
    "included_records",
    "unmatched_classification",
    "missing_classification",
    "invalid_classification",
    "zero_substantive_domains",
    "excluded_records",
]


def _filter_label_with_count(label: str, count: int) -> str:
    return f"{label}  ({count} {'project' if count == 1 else 'projects'})"


def _split_semicolon_values(value) -> list[str]:
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def _display_record_linkage(value: str) -> str:
    cleaned = str(value).strip()
    return RECORD_LINKAGE_DISPLAY_LABELS.get(cleaned, cleaned)


def _single_value_options(
    df: pd.DataFrame,
    column: str,
    all_label: str,
    preferred_order: list[str] | None = None,
) -> list[dict]:
    if column not in df.columns:
        return [{"label": all_label, "value": "ALL"}]
    values = df[column].fillna("").astype(str).str.strip()
    counts = Counter(v for v in values if v)
    display_counts = Counter()
    for value, count in counts.items():
        display_counts[_display_record_linkage(value) if column == "record_linkage" else value] += count
    if preferred_order:
        ordered = [v for v in preferred_order if v in display_counts]
        ordered.extend(sorted(v for v in display_counts if v not in ordered))
    else:
        ordered = sorted(display_counts)
    return (
        [{"label": all_label, "value": "ALL"}]
        + [
            {
                "label": _filter_label_with_count(value, display_counts[value]),
                "value": value,
            }
            for value in ordered
        ]
    )


def _semicolon_value_options(df: pd.DataFrame, column: str, all_label: str) -> list[dict]:
    if column not in df.columns:
        return [{"label": all_label, "value": "ALL"}]
    counts: Counter = Counter()
    for values in df[column].dropna():
        counts.update(set(_split_semicolon_values(values)))
    return (
        [{"label": all_label, "value": "ALL"}]
        + [
            {
                "label": _filter_label_with_count(
                    display_deterministic_value(value),
                    counts[value],
                ),
                "value": value,
            }
            for value in sorted(counts)
        ]
    )


def _single_value_totals(
    df: pd.DataFrame,
    source_col: str,
    output_col: str,
    preferred_order: list[str] | None = None,
) -> pd.DataFrame:
    if source_col not in df.columns:
        return pd.DataFrame(columns=[output_col, "count"])
    counts: Counter = Counter()
    for value in df[source_col].fillna("").astype(str).str.strip():
        if value:
            counts[_display_record_linkage(value) if source_col == "record_linkage" else value] += 1
    if preferred_order:
        ordered = [value for value in preferred_order if value in counts]
        ordered.extend(sorted(value for value in counts if value not in ordered))
    else:
        ordered = sorted(counts)
    return pd.DataFrame(
        [{output_col: value, "count": int(counts[value])} for value in ordered],
        columns=[output_col, "count"],
    )


def _semicolon_value_totals(df: pd.DataFrame, source_col: str, output_col: str) -> pd.DataFrame:
    if source_col not in df.columns:
        return pd.DataFrame(columns=[output_col, "count"])
    counts: Counter = Counter()
    for values in df[source_col].dropna():
        counts.update(set(_split_semicolon_values(values)))
    return pd.DataFrame(
        [
            {
                output_col: display_deterministic_value(value),
                "count": int(counts[value]),
            }
            for value in sorted(counts)
        ],
        columns=[output_col, "count"],
    )


def _facet_values_by_year(df: pd.DataFrame, source_col: str, output_col: str) -> pd.DataFrame:
    """Yearly counts/shares for a semicolon multi-value deterministic facet.

    Multi-count: a project carrying both values (e.g. survey AND administrative
    data) counts under both, so shares can sum past 100%. The denominator is
    each year's classified-project total. Explicit zeros so dips show.
    """
    columns = ["Year", output_col, "count", "total", "pct_of_projects"]
    if "Year" not in df.columns or source_col not in df.columns:
        return pd.DataFrame(columns=columns)

    work = df[["Year", source_col]].copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work = work[work["Year"].notna()]
    if work.empty:
        return pd.DataFrame(columns=columns)
    work["Year"] = work["Year"].astype(int)
    work["_values"] = work[source_col].apply(
        lambda v: sorted({
            display_deterministic_value(part)
            for part in _split_semicolon_values(v)
        })
    )

    years = sorted(work["Year"].unique())
    totals = work.groupby("Year").size()
    values = sorted({value for parts in work["_values"] for value in parts})
    exploded = work.explode("_values").dropna(subset=["_values"])
    grouped = exploded.groupby(["Year", "_values"]).size()
    rows = []
    for value in values:
        for year in years:
            total = int(totals.get(year, 0))
            count = int(grouped.get((year, value), 0))
            rows.append({
                "Year": year,
                output_col: value,
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(rows, columns=columns)


def _record_linkage_by_year(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["Year", "record_linkage", "count", "total", "pct_of_projects"]
    if "Year" not in df.columns or "record_linkage" not in df.columns:
        return pd.DataFrame(columns=columns)

    work = df[["Year", "record_linkage"]].copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["record_linkage"] = work["record_linkage"].fillna("").astype(str).str.strip().apply(_display_record_linkage)
    work = work[work["Year"].notna() & (work["record_linkage"] != "")]
    if work.empty:
        return pd.DataFrame(columns=columns)

    work["Year"] = work["Year"].astype(int)
    years = sorted(work["Year"].unique())
    linkage_order = [
        value
        for value in ["No record linkage", "Within-domain", "Cross-domain"]
        if value in set(work["record_linkage"])
    ]
    rows = []
    grouped = work.groupby(["Year", "record_linkage"]).size()
    totals = work.groupby("Year").size()
    for year in years:
        total = int(totals.get(year, 0))
        for linkage in linkage_order:
            count = int(grouped.get((year, linkage), 0))
            rows.append({
                "Year": year,
                "record_linkage": linkage,
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(rows, columns=columns)


def _record_linkage_by_quarter(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Year", "Quarter", "period_date", "period_label",
        "record_linkage", "count", "total", "pct_of_projects",
    ]
    required = {"Year", "Quarter", "record_linkage"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=columns)

    work = df[["Year", "Quarter", "record_linkage"]].copy()
    work["Year"] = pd.to_numeric(work["Year"], errors="coerce")
    work["Quarter"] = work["Quarter"].fillna("").astype(str).str.strip()
    work["record_linkage"] = (
        work["record_linkage"].fillna("").astype(str).str.strip().apply(_display_record_linkage)
    )
    work = work[
        work["Year"].notna()
        & (work["Quarter"] != "")
        & (work["record_linkage"] != "")
    ].copy()
    if work.empty:
        return pd.DataFrame(columns=columns)

    periods = pd.PeriodIndex(work["Quarter"], freq="Q")
    work["Year"] = work["Year"].astype(int)
    work["period_date"] = periods.start_time
    work["period_label"] = [f"{period.year} Q{period.quarter}" for period in periods]
    period_order = (
        work[["Quarter", "period_date", "period_label", "Year"]]
        .drop_duplicates()
        .sort_values("period_date", kind="stable")
    )
    linkage_order = [
        value
        for value in ["No record linkage", "Within-domain", "Cross-domain"]
        if value in set(work["record_linkage"])
    ]
    grouped = work.groupby(["Quarter", "record_linkage"]).size()
    totals = work.groupby("Quarter").size()
    rows = []
    for _, period in period_order.iterrows():
        quarter = period["Quarter"]
        total = int(totals.get(quarter, 0))
        for linkage in linkage_order:
            count = int(grouped.get((quarter, linkage), 0))
            rows.append({
                "Year": int(period["Year"]),
                "Quarter": quarter,
                "period_date": period["period_date"],
                "period_label": period["period_label"],
                "record_linkage": linkage,
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(rows, columns=columns)


def _domain_record_linkage_crosstab(df: pd.DataFrame) -> pd.DataFrame:
    linkage_order = ["No record linkage", "Within-domain", "Cross-domain"]
    columns = ["domain", *linkage_order]
    if "substantive_domains" not in df.columns or "record_linkage" not in df.columns:
        return pd.DataFrame(columns=columns)

    work = df[["substantive_domains", "record_linkage"]].copy()
    work["domain"] = work["substantive_domains"].apply(_split_semicolon_values)
    work["record_linkage"] = (
        work["record_linkage"].fillna("").astype(str).str.strip().apply(_display_record_linkage)
    )
    work = work.explode("domain")
    work = work[
        work["domain"].notna()
        & (work["domain"].astype(str).str.strip() != "")
        & (work["record_linkage"] != "")
    ].reset_index(drop=True)
    if work.empty:
        return pd.DataFrame(columns=columns)

    ct = pd.crosstab(work["domain"], work["record_linkage"])
    for linkage in linkage_order:
        if linkage not in ct.columns:
            ct[linkage] = 0
    ct = ct[linkage_order]
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False, kind="stable").index]
    return ct.reset_index().rename(columns={"index": "domain"})


def _researcher_sector_cooccurrence(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    order = RESEARCHER_SECTOR_HEATMAP_ORDER
    matrix = pd.DataFrame(0, index=order, columns=order, dtype=int)
    if "researcher_sectors" not in df.columns:
        return matrix, 0

    excluded_count = 0
    real_sectors = set(order)
    for value in df["researcher_sectors"].dropna():
        sectors = {
            sector
            for sector in _split_semicolon_values(value)
            if sector in real_sectors
        }
        if not sectors:
            excluded_count += 1
            continue
        if len(sectors) == 1:
            sector = next(iter(sectors))
            matrix.loc[sector, sector] += 1
        for first, second in combinations(sorted(sectors), 2):
            matrix.loc[first, second] += 1
            matrix.loc[second, first] += 1
    return matrix, excluded_count


def _count_substantive_domains(value):
    """Count distinct recognised substantive domains, matching breadth eligibility.

    The ``substantive_domains`` source field can contain the taxonomy fallback
    or an invalid token. The Enriched Register's count must not describe either
    as a substantive domain, and an invalid set must not be partially counted.
    """
    substantive_labels = {
        label for label in DOMAIN_LABELS if not label.lower().startswith("unclear")
    }
    unclear_labels = set(DOMAIN_LABELS) - substantive_labels
    _, _, count = _domain_breadth_classification(
        value, substantive_labels, unclear_labels,
    )
    return pd.NA if count is None else count


def _is_missing_value(value) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _validated_record_keys(df: pd.DataFrame, source_name: str) -> pd.Series:
    """Return stripped Record ID keys, rejecting an ambiguous join source."""
    if "Record ID" not in df.columns:
        raise ValueError(f"{source_name} is missing Record ID")
    keys = df["Record ID"].astype("string").str.strip()
    if keys.isna().any() or keys.eq("").any():
        raise ValueError(f"{source_name} contains blank Record ID values")
    if keys.duplicated().any():
        raise ValueError(f"{source_name} contains duplicate Record ID values")
    return keys.astype(str)


def _domain_breadth_classification(value, substantive_labels, unclear_labels):
    """Classify one raw domain set without accepting unknown tokens partially."""
    if _is_missing_value(value):
        return "missing_classification", None, None
    tokens = set(_split_semicolon_values(value))
    if not tokens:
        return "zero_substantive_domains", None, 0
    unknown = tokens - substantive_labels - unclear_labels
    if unknown:
        return "invalid_classification", None, None
    breadth = len(tokens & substantive_labels)
    if breadth == 0:
        return "zero_substantive_domains", None, 0
    bucket = "1 domain" if breadth == 1 else "2 domains" if breadth == 2 else "3+ domains"
    return "included", bucket, breadth


def _zero_substantive_domain_kind(value) -> str:
    """Distinguish empty sets from non-empty Unclear-only classifications."""
    return (
        "explicit_empty_substantive_domains"
        if not _split_semicolon_values(value)
        else "unclear_only_substantive_domains"
    )


def _domain_breadth_calendar_periods(
    dates: pd.Series,
    selection,
    bounds: YearRange,
    granularity: str,
) -> pd.DataFrame:
    """Build complete selected calendar periods, clipped to register coverage."""
    valid_dates = dates.dropna()
    columns = ["period_key", "Year", "period_date", "period_label"]
    if valid_dates.empty:
        return pd.DataFrame(columns=columns)

    if is_all_years(selection, bounds):
        start = pd.Timestamp(int(valid_dates.min().year), 1, 1)
        end = pd.Timestamp(valid_dates.max())
    else:
        try:
            lower, upper = sorted(int(year) for year in selection)
        except (TypeError, ValueError):
            return pd.DataFrame(columns=columns)
        start = max(pd.Timestamp(int(valid_dates.min().year), 1, 1), pd.Timestamp(lower, 1, 1))
        end = min(pd.Timestamp(valid_dates.max()), pd.Timestamp(upper, 12, 31))
    if start > end:
        return pd.DataFrame(columns=columns)

    if granularity == "quarter":
        periods = pd.period_range(start=start, end=end, freq="Q")
        return pd.DataFrame({
            "period_key": periods.astype(str),
            "Year": [period.year for period in periods],
            "period_date": periods.start_time,
            "period_label": [f"{period.year} Q{period.quarter}" for period in periods],
        })

    years = list(range(start.year, end.year + 1))
    return pd.DataFrame({
        "period_key": [str(year) for year in years],
        "Year": years,
        "period_date": [pd.Timestamp(year, 1, 1) for year in years],
        "period_label": [str(year) for year in years],
    })


def _domain_breadth_period_tables(
    records: pd.DataFrame,
    periods: pd.DataFrame,
    granularity: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    trend_columns = [
        "Year", "Quarter", "period_date", "period_label", "domain_breadth",
        "count", "eligible_denominator", "pct_of_eligible",
    ]
    if periods.empty:
        return (
            pd.DataFrame(columns=trend_columns),
            pd.DataFrame(columns=DOMAIN_BREADTH_COVERAGE_COLUMNS),
        )

    if granularity == "quarter":
        period_values = records["_date"].dt.to_period("Q").astype(str)
    else:
        period_values = records["_date"].dt.year.astype(str)
    dated = records.assign(_period_key=period_values)
    reason_counts = dated.groupby(["_period_key", "_reason"]).size()
    bucket_counts = dated.loc[dated["_reason"].eq("included")].groupby(
        ["_period_key", "_bucket"]
    ).size()

    trend_rows = []
    coverage_rows = []
    for _, period in periods.iterrows():
        key = period["period_key"]
        included = int(reason_counts.get((key, "included"), 0))
        reasons = {
            reason: int(reason_counts.get((key, reason), 0))
            for reason in [
                "unmatched_classification",
                "missing_classification",
                "invalid_classification",
                "zero_substantive_domains",
            ]
        }
        coverage_rows.append({
            "period_label": period["period_label"],
            "dated_selected_records": included + sum(reasons.values()),
            "included_records": included,
            **reasons,
            "excluded_records": sum(reasons.values()),
        })
        for bucket in DOMAIN_BREADTH_ORDER:
            count = int(bucket_counts.get((key, bucket), 0))
            trend_rows.append({
                "Year": int(period["Year"]),
                "Quarter": key if granularity == "quarter" else None,
                "period_date": period["period_date"],
                "period_label": period["period_label"],
                "domain_breadth": bucket,
                "count": count,
                "eligible_denominator": included,
                "pct_of_eligible": round(count / included * 100, 1) if included else None,
            })
    return (
        pd.DataFrame(trend_rows, columns=trend_columns),
        pd.DataFrame(coverage_rows, columns=DOMAIN_BREADTH_COVERAGE_COLUMNS),
    )


def domain_breadth_aggregates(
    register_df: pd.DataFrame,
    classification_df: pd.DataFrame,
    selection,
    bounds: YearRange,
) -> dict:
    """Aggregate taxonomy-validated substantive-domain breadth by record period.

    The authoritative register supplies selection and dates. Frozen production
    classifications join one-to-one on Record ID. Invalid token sets are kept
    wholly outside the denominator so a recognised token cannot mask an
    unrecognised companion token.
    """
    register = register_df.copy()
    classifications = classification_df.copy()
    register["_record_key"] = _validated_record_keys(register, "Register")
    classifications["_record_key"] = _validated_record_keys(
        classifications, "Classifications",
    )
    dates = parse_accreditation_dates(register)
    selected_mask = year_selection_mask(register, selection, bounds)
    selected = register.loc[selected_mask].copy()
    selected["_date"] = dates.loc[selected_mask]

    all_undated = int(dates.isna().sum())
    undated_selected = int(selected["_date"].isna().sum())
    undated_omitted = 0 if is_all_years(selection, bounds) else all_undated - undated_selected
    dated = selected.loc[selected["_date"].notna()].copy()

    domain_column = (
        classifications[["_record_key", "substantive_domains"]].copy()
        if "substantive_domains" in classifications.columns
        else classifications[["_record_key"]].assign(substantive_domains=pd.NA)
    )
    merged = dated.merge(
        domain_column,
        on="_record_key",
        how="left",
        validate="one_to_one",
        indicator="_classification_join",
    )

    substantive_labels = {
        label for label in DOMAIN_LABELS if not label.lower().startswith("unclear")
    }
    unclear_labels = set(DOMAIN_LABELS) - substantive_labels
    classifications_result = []
    for _, row in merged.iterrows():
        if row["_classification_join"] != "both":
            classification = ("unmatched_classification", None, None)
        else:
            classification = _domain_breadth_classification(
                row["substantive_domains"], substantive_labels, unclear_labels,
            )
        classifications_result.append((
            *classification,
            _zero_substantive_domain_kind(row["substantive_domains"])
            if classification[0] == "zero_substantive_domains" else None,
        ))
    result = pd.DataFrame(
        classifications_result,
        index=merged.index,
        columns=[
            "_reason", "_bucket", "_derived_domain_count",
            "_zero_substantive_domain_kind",
        ],
    )
    merged = pd.concat([merged, result], axis=1)

    year_periods = _domain_breadth_calendar_periods(dates, selection, bounds, "year")
    quarter_periods = _domain_breadth_calendar_periods(dates, selection, bounds, "quarter")
    by_year, coverage_by_year = _domain_breadth_period_tables(merged, year_periods, "year")
    by_quarter, coverage_by_quarter = _domain_breadth_period_tables(
        merged, quarter_periods, "quarter",
    )
    return {
        "df_domain_breadth_by_year": by_year,
        "df_domain_breadth_by_quarter": by_quarter,
        "df_domain_breadth_coverage_by_year": coverage_by_year,
        "df_domain_breadth_coverage_by_quarter": coverage_by_quarter,
        "domain_breadth_selection_coverage": {
            "selected_records": int(len(selected)),
            "dated_selected_records": int(len(dated)),
            "undated_selected_records": undated_selected,
            "undated_omitted_records": int(undated_omitted),
            "included_records": int(merged["_reason"].eq("included").sum()),
            "unmatched_classification": int(merged["_reason"].eq("unmatched_classification").sum()),
            "missing_classification": int(merged["_reason"].eq("missing_classification").sum()),
            "invalid_classification": int(merged["_reason"].eq("invalid_classification").sum()),
            "zero_substantive_domains": int(merged["_reason"].eq("zero_substantive_domains").sum()),
            "unclear_only_substantive_domains": int(
                merged["_zero_substantive_domain_kind"].eq(
                    "unclear_only_substantive_domains",
                ).sum(),
            ),
            "explicit_empty_substantive_domains": int(
                merged["_zero_substantive_domain_kind"].eq(
                    "explicit_empty_substantive_domains",
                ).sum(),
            ),
        },
    }


_LINKAGE_PAIR_COLUMNS = ["domain_a", "domain_b", "count", "within_domain", "products"]
_LINKAGE_PRODUCTS_SHOWN = 3


def _product_cells() -> dict[str, set[tuple[str, str]]]:
    """Domain-pair cells each linked product spans, from the reference."""
    cells: dict[str, set[tuple[str, str]]] = {}
    for product in LINKED_PRODUCTS:
        domains = sorted(set(product["component_domains"]))
        if not domains:
            continue
        cells[product["canonical"]] = (
            {(domains[0], domains[0])} if len(domains) == 1
            else set(combinations(domains, 2))
        )
    return cells


def _products_label(product_counts: Counter, cell_projects: int) -> str:
    """Which products put projects in this cell, biggest first."""
    if not product_counts:
        return ""
    shown = product_counts.most_common(_LINKAGE_PRODUCTS_SHOWN)
    parts = [f"{product_short_label(name)} {count}" for name, count in shown]
    remaining = len(product_counts) - len(shown)
    if remaining:
        parts.append(f"+{remaining} more")
    label = "; ".join(parts)
    # A project can match several products in one cell, so the per-product
    # counts can sum past the cell's project count.
    if sum(product_counts.values()) > cell_projects:
        label += " (projects overlap)"
    return label


def _record_linkage_domain_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Domain pairs spanned by each project's record linkage, per product.

    Deterministic, and attributed the way the linkage rule defines span: a
    cell counts projects that matched a linked product spanning that pair.
    The recorded component-domain column is a union across a project's
    products, so using it would draw pairs no single product spans - which the
    rule explicitly does not treat as cross-domain linkage - and would hide the
    diagonal cells of that project's single-domain products.
    """
    if df.empty or "Record ID" not in df.columns:
        return pd.DataFrame(columns=_LINKAGE_PAIR_COLUMNS)

    properties = load_register_properties(columns=[MATCHED_PRODUCTS_COL])
    if properties.empty:
        return pd.DataFrame(columns=_LINKAGE_PAIR_COLUMNS)

    product_cells = _product_cells()
    merged = df[["Record ID"]].merge(properties, on="Record ID", how="left")
    cell_projects: dict[tuple[str, str], set[str]] = {}
    cell_products: dict[tuple[str, str], Counter] = {}
    for record_id, value in zip(merged["Record ID"], merged[MATCHED_PRODUCTS_COL].fillna("")):
        products = [part.strip() for part in str(value).split(";") if part.strip()]
        for product in products:
            for cell in product_cells.get(product, ()):  # unknown products contribute nothing
                cell_projects.setdefault(cell, set()).add(str(record_id))
                cell_products.setdefault(cell, Counter())[product] += 1

    rows = [
        {
            "domain_a": a,
            "domain_b": b,
            "count": len(projects),
            "within_domain": a == b,
            "products": _products_label(cell_products[(a, b)], len(projects)),
        }
        for (a, b), projects in cell_projects.items()
    ]
    rows.sort(key=lambda row: (-row["count"], row["domain_a"], row["domain_b"]))
    return pd.DataFrame(rows, columns=_LINKAGE_PAIR_COLUMNS)


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


def _tag_domain_totals(
    df: pd.DataFrame,
    tag_series_values: pd.Series,
    tag: str,
) -> pd.DataFrame:
    """Tagged projects per domain, with each domain's project count as the
    normalising denominator (% = tagged projects in domain / projects in domain)."""
    tag_mask = tag_series_values.apply(lambda value: tag in _split_semicolon_values(value))
    tag_domain_counts: Counter = Counter()
    for domains in df.loc[tag_mask, "substantive_domains"].dropna():
        tag_domain_counts.update(set(_split_semicolon_values(domains)))
    domain_totals: Counter = Counter()
    for domains in df["substantive_domains"].dropna():
        domain_totals.update(set(_split_semicolon_values(domains)))
    return pd.DataFrame(
        [
            {
                "domain": domain,
                "count": count,
                "domain_total": domain_totals.get(domain, 0),
                "pct_of_domain": (
                    round(count / domain_totals[domain] * 100, 1)
                    if domain_totals.get(domain) else 0.0
                ),
            }
            for domain, count in sorted(
                tag_domain_counts.items(), key=lambda kv: kv[1], reverse=True
            )
        ],
        columns=["domain", "count", "domain_total", "pct_of_domain"],
    )


def _domain_crosstab(df: pd.DataFrame, other_col: str, other_multi: bool, col_order) -> pd.DataFrame:
    """Substantive-domain x classification-value counts over ALL domains.

    Substantive domain is non-hierarchical, so a project is counted once per
    assigned domain (column totals can exceed the project count). Returns a
    frame whose first
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

    The diagonal holds projects whose domain set is exactly that domain.
    Off-diagonal cells hold the number of projects carrying both domains.
    Domains are ordered by total (descending). The "Unclear" fallback is
    excluded because it cannot co-occur with a real domain by construction.
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
    solo_totals: Counter = Counter()
    pairs: Counter = Counter()
    for domains in project_domains:
        for domain in domains:
            totals[domain] += 1
        if len(domains) == 1:
            solo_totals[domains[0]] += 1
        for a, b in combinations(domains, 2):
            pairs[(a, b)] += 1
            pairs[(b, a)] += 1
    if not totals:
        return pd.DataFrame()

    order = [domain for domain, _ in totals.most_common()]
    matrix = pd.DataFrame(0, index=order, columns=order, dtype=int)
    for domain in order:
        matrix.loc[domain, domain] = solo_totals[domain]
    for (a, b), count in pairs.items():
        matrix.loc[a, b] = count
    matrix.attrs["domain_totals"] = dict(totals)
    return matrix


def _classification_trends(
    df: pd.DataFrame,
    source_col: str,
    category_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rebuild the frozen release's multi-label trend and totals tables."""
    by_year_columns = ["Year", category_col, "count", "total", "pct_of_projects"]
    total_columns = [category_col, "count"]
    if df.empty or source_col not in df.columns or "Year" not in df.columns:
        return pd.DataFrame(columns=by_year_columns), pd.DataFrame(columns=total_columns)
    key = "Record ID" if "Record ID" in df.columns else "Project ID"
    base = df[[key, "Year", source_col]].copy()
    base[category_col] = base[source_col].apply(_split_semicolon_values)
    exploded = base.explode(category_col)
    exploded = exploded[
        exploded[category_col].notna()
        & exploded[category_col].astype(str).str.strip().ne("")
    ]
    totals_by_year = base.groupby("Year")[key].count().rename("total")
    by_year = (
        exploded.groupby(["Year", category_col])[key].count()
        .reset_index().rename(columns={key: "count"})
        .merge(totals_by_year, on="Year")
    )
    by_year["pct_of_projects"] = (
        by_year["count"] / by_year["total"] * 100
    ).round(1)
    totals = (
        exploded.groupby(category_col)[key].count()
        .reset_index().rename(columns={key: "count"})
        .sort_values("count", ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    return by_year[by_year_columns], totals[total_columns]


def build_thematic_aggregates(df: pd.DataFrame) -> dict:
    """Aggregate one already record-filtered classified-project population."""
    work = df.copy()
    by_year_a, totals_a = _classification_trends(
        work, "substantive_domains", "domain",
    )
    by_year_c, totals_c = _classification_trends(
        work, "analytical_purpose", "purpose",
    )
    tag_values = _tag_series(work)
    tagged_count = int(tag_values.apply(_has_any_tag).sum()) if len(work) else 0
    years = sorted(int(y) for y in work.get("Year", pd.Series(dtype=float)).dropna().unique())
    totals_by_year = work.groupby("Year").size() if "Year" in work.columns else pd.Series(dtype=int)
    tag_rows = []
    for tag in TAG_LABELS:
        tag_mask = tag_values.apply(lambda value, selected=tag: selected in _split_semicolon_values(value))
        counts = work.loc[tag_mask].groupby("Year").size() if "Year" in work.columns else pd.Series(dtype=int)
        for year in years:
            total = int(totals_by_year.get(year, 0))
            count = int(counts.get(year, 0))
            tag_rows.append({
                "Year": year,
                "tag": tag,
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    no_linkage = (
        work["record_linkage"].fillna("").astype(str).str.strip().eq("No record linkage")
        if "record_linkage" in work.columns else pd.Series(False, index=work.index)
    )
    sector_matrix, sector_excluded = _researcher_sector_cooccurrence(work)
    return {
        "df_thematic_a": by_year_a,
        "df_thematic_c": by_year_c,
        "df_thematic_a_totals": totals_a,
        "df_thematic_c_totals": totals_c,
        "df_cross_domain_purpose": _domain_crosstab(
            work, "analytical_purpose", True, PURPOSE_LABELS,
        ),
        "df_thematic_tag_by_year": pd.DataFrame(
            tag_rows,
            columns=["Year", "tag", "count", "total", "pct_of_projects"],
        ),
        "df_thematic_covid_tag_by_domain": _tag_domain_totals(
            work, tag_values, "COVID-19 & Pandemic",
        ),
        "df_thematic_demographic_tag_by_domain": _tag_domain_totals(
            work, tag_values, "Demographic disparities / equity tag",
        ),
        "df_domain_cooccurrence": _domain_cooccurrence(work),
        "df_latent_demand_cooccurrence": _domain_cooccurrence(work.loc[no_linkage]),
        "LATENT_NO_LINKAGE_COUNT": int(no_linkage.sum()),
        "df_record_linkage_totals": _single_value_totals(
            work, "record_linkage", "record_linkage",
            ["No record linkage", "Cross-domain", "Within-domain"],
        ),
        "df_collection_method_totals": _semicolon_value_totals(
            work, "dataset_collection_methods", "collection_method",
        ),
        "df_temporal_structure_totals": _semicolon_value_totals(
            work, "dataset_temporal_structures", "temporal_structure",
        ),
        "df_unit_totals": _semicolon_value_totals(
            work, "dataset_units", "unit_of_observation",
        ),
        "df_researcher_sector_totals": _semicolon_value_totals(
            work, "researcher_sectors", "researcher_sector",
        ),
        "df_record_linkage_by_year": _record_linkage_by_year(work),
        "df_record_linkage_by_quarter": _record_linkage_by_quarter(work),
        "df_record_linkage_domain_pairs": _record_linkage_domain_pairs(work),
        "df_collection_method_by_year": _facet_values_by_year(
            work, "dataset_collection_methods", "collection_method",
        ),
        "df_temporal_structure_by_year": _facet_values_by_year(
            work, "dataset_temporal_structures", "temporal_structure",
        ),
        "df_unit_by_year": _facet_values_by_year(
            work, "dataset_units", "unit_of_observation",
        ),
        "df_domain_record_linkage": _domain_record_linkage_crosstab(work),
        "df_researcher_sector_cooccurrence": sector_matrix,
        "RESEARCHER_SECTOR_EXCLUDED_COUNT": sector_excluded,
        "THEMATIC_PROJECT_COUNT": int(len(work)),
        "THEMATIC_TAGGED_COUNT": tagged_count,
    }


def _thematic_filter_options(projects: pd.DataFrame) -> dict:
    """Fixed Enriched Register filter universes, labelled with project counts."""
    domain_counts = projects[SUBSTANTIVE_DOMAIN_COUNT_COL].dropna().value_counts().sort_index()
    tag_counts: Counter = Counter()
    for tags in _tag_series(projects).dropna():
        tag_counts.update(set(_split_semicolon_values(tags)))
    tags = [tag for tag in TAG_LABELS if tag in tag_counts] or sorted(tag_counts)
    return {
        "_THEMATIC_DOMAIN_OPTIONS": _semicolon_value_options(
            projects, "substantive_domains", "All domains",
        ),
        "_THEMATIC_DOMAIN_COUNT_OPTIONS": [{"label": "All domain counts", "value": "ALL"}] + [
            {
                "label": _filter_label_with_count(_domain_count_label(int(value)), int(count)),
                "value": int(value),
            }
            for value, count in domain_counts.items()
        ],
        "_THEMATIC_PURPOSE_OPTIONS": _semicolon_value_options(
            projects, "analytical_purpose", "All purposes",
        ),
        "_THEMATIC_TAG_OPTIONS": [{"label": "All projects", "value": "ALL"}] + [
            {"label": _filter_label_with_count(tag, tag_counts[tag]), "value": tag}
            for tag in tags
        ],
        "_DETERMINISTIC_RECORD_LINKAGE_OPTIONS": _single_value_options(
            projects, "record_linkage", "All record linkage",
            ["No record linkage", "Cross-domain", "Within-domain"],
        ),
        "_DETERMINISTIC_COLLECTION_METHOD_OPTIONS": _semicolon_value_options(
            projects, "dataset_collection_methods", "All collection methods",
        ),
        "_DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS": _semicolon_value_options(
            projects, "dataset_temporal_structures", "All temporal structures",
        ),
        "_DETERMINISTIC_UNIT_OPTIONS": _semicolon_value_options(
            projects, "dataset_units", "All units",
        ),
        "_DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS": _semicolon_value_options(
            projects, "researcher_sectors", "All researcher sectors",
        ),
    }


# The frozen release's own trend and totals tables, published with the run.
_RELEASE_TABLE_FILES = {
    "df_thematic_a": "layer_a_by_year.csv",
    "df_thematic_c": "layer_c_by_year.csv",
    "df_thematic_a_totals": "layer_a_totals.csv",
    "df_thematic_c_totals": "layer_c_totals.csv",
}


def load_thematic_data(thematic_dir):
    """Returns (data_dict, available_flag).

    Only a missing release file marks the thematic layer unavailable; any
    other error is a bug and propagates rather than silently hiding the tab.
    """
    try:
        release_tables = {
            key: pd.read_csv(os.path.join(thematic_dir, filename), encoding="utf-8-sig")
            for key, filename in _RELEASE_TABLE_FILES.items()
        }
        with open(os.path.join(thematic_dir, "layer_summary.txt"), "r", encoding="utf-8") as f:
            narrative = f.read()
        projects = pd.read_csv(
            os.path.join(thematic_dir, "layer_classifications.csv"), encoding="utf-8-sig",
        )
    except FileNotFoundError:
        # Unavailable: the same structure with no rows, so nothing downstream
        # needs a separate empty-data path.
        empty = pd.DataFrame(columns=[
            "Record ID", "Project ID", "Year", "Quarter", "substantive_domains",
            "analytical_purpose", CROSS_CUTTING_TAGS_COL, *DETERMINISTIC_FACET_COLUMNS,
            SUBSTANTIVE_DOMAIN_COUNT_COL,
        ])
        return {
            **build_thematic_aggregates(empty),
            **{key: pd.DataFrame() for key in _RELEASE_TABLE_FILES},
            **_thematic_filter_options(empty),
            "df_thematic_projects": empty,
            "THEMATIC_NARRATIVE": "",
        }, False

    projects = _merge_deterministic_facets(projects, DETERMINISTIC_FACET_COLUMNS)
    projects[SUBSTANTIVE_DOMAIN_COUNT_COL] = (
        projects["substantive_domains"].apply(_count_substantive_domains).astype("Int64")
    )
    if "Project ID" in projects.columns:
        projects[_PROJECT_ID_KEY_COL] = projects["Project ID"].apply(_project_id_key)

    return {
        **build_thematic_aggregates(projects),
        **release_tables,
        **_thematic_filter_options(projects),
        "df_thematic_projects": projects,
        "THEMATIC_NARRATIVE": narrative,
    }, True


_thematic_data, THEMATIC_DATA_AVAILABLE = load_thematic_data(CLASSIFICATION_DIR)

# Module-level names used by the filters, the layout and the chart tests.
df_thematic_projects = _thematic_data["df_thematic_projects"]
df_thematic_a = _thematic_data["df_thematic_a"]
df_thematic_c = _thematic_data["df_thematic_c"]
df_cross_domain_purpose = _thematic_data["df_cross_domain_purpose"]
df_thematic_tag_by_year = _thematic_data["df_thematic_tag_by_year"]
df_thematic_covid_tag_by_domain = _thematic_data["df_thematic_covid_tag_by_domain"]
df_thematic_demographic_tag_by_domain = _thematic_data["df_thematic_demographic_tag_by_domain"]
df_domain_cooccurrence = _thematic_data["df_domain_cooccurrence"]
df_latent_demand_cooccurrence = _thematic_data["df_latent_demand_cooccurrence"]
df_record_linkage_by_year = _thematic_data["df_record_linkage_by_year"]
df_record_linkage_by_quarter = _thematic_data["df_record_linkage_by_quarter"]
df_collection_method_by_year = _thematic_data["df_collection_method_by_year"]
df_temporal_structure_by_year = _thematic_data["df_temporal_structure_by_year"]
df_unit_by_year = _thematic_data["df_unit_by_year"]
df_domain_record_linkage = _thematic_data["df_domain_record_linkage"]
LATENT_NO_LINKAGE_COUNT = _thematic_data["LATENT_NO_LINKAGE_COUNT"]
THEMATIC_PROJECT_COUNT = _thematic_data["THEMATIC_PROJECT_COUNT"]
THEMATIC_TAGGED_COUNT = _thematic_data["THEMATIC_TAGGED_COUNT"]
_THEMATIC_DOMAIN_OPTIONS = _thematic_data["_THEMATIC_DOMAIN_OPTIONS"]
_THEMATIC_DOMAIN_COUNT_OPTIONS = _thematic_data["_THEMATIC_DOMAIN_COUNT_OPTIONS"]
_THEMATIC_PURPOSE_OPTIONS = _thematic_data["_THEMATIC_PURPOSE_OPTIONS"]
_THEMATIC_TAG_OPTIONS = _thematic_data["_THEMATIC_TAG_OPTIONS"]
_DETERMINISTIC_RECORD_LINKAGE_OPTIONS = _thematic_data["_DETERMINISTIC_RECORD_LINKAGE_OPTIONS"]
_DETERMINISTIC_COLLECTION_METHOD_OPTIONS = _thematic_data["_DETERMINISTIC_COLLECTION_METHOD_OPTIONS"]
_DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS = _thematic_data["_DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS"]
_DETERMINISTIC_UNIT_OPTIONS = _thematic_data["_DETERMINISTIC_UNIT_OPTIONS"]
_DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS = _thematic_data["_DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS"]
