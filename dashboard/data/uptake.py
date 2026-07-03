"""Linked-product uptake and availability-exposure data (deterministic layer).

Everything here is derived deterministically from the register and the named
linked-product catalogue in analysis/register_reference.yaml:

- exposure windows for availability-normalised demand (years a dataset has
  been requestable WITHIN the register window, never raw dataset age);
- per-product adoption counts from the matched_products facet;
- the set of domain pairs served by an existing cross-domain linked product.

Availability dates come in two tiers. The EMPIRICAL default for every dataset
and product is its first appearance in the register (first mention quarter) —
an honest proxy, labelled as such. CURATED dates from the reference
(``availability_date``, falling back to the legacy ``available_from``)
override the proxy where present.
"""

from collections import Counter
from itertools import combinations

import pandas as pd

from analysis.derive_register_properties import (
    build_indexes,
    load_reference,
    match_linked_products,
)
from dashboard.data.deterministic import load_register_properties
from dashboard.data.collection_view import (
    COLLECTION_VIEW_GROUPED,
    COLLECTION_VIEW_INDIVIDUAL,
    normalise_collection_view,
)
from dashboard.data.registry import df_all, df_datasets

REGISTER_WINDOW_START = pd.Timestamp("2019-01-01")
LATEST_REGISTER_DATE = df_all["Accreditation Date"].max()

# Short display labels for annotation/legend use; canonical names stay the key.
PRODUCT_SHORT_LABELS = {
    "Longitudinal Education Outcomes (LEO)": "LEO",
    "Education and Child Health Insights from Linked Data (ECHILD)": "ECHILD",
    "Linked Census, HES and Mortality Data": "Census-HES-Mortality",
    "GRading and Admissions Data England (GRADE)": "GRADE",
    "MoJ Data First": "Data First",
    "Administrative Data | Agricultural Research Collection (AD|ARC)": "AD|ARC",
    "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment": "ASHE-PAYE/SA",
    "Annual Survey of Hours and Earnings linked to Census 2011": "ASHE-Census 2011",
    "Earnings and Employees Study (EES) 2011 - Northern Ireland": "EES (NI)",
    "Growing Up in England (GUIE)": "GUIE",
    "ONS Longitudinal Study": "ONS LS",
    "Linked Trade-in-Goods/IDBR": "Trade-in-Goods/IDBR",
    "2011 Census linked to Benefits and Income - England and Wales": "Census-Benefits/Income",
    "Nursing and Midwifery Council Register - UK Linked to Census 2021": "NMC-Census 2021",
    "EOL": "EOL",
    "COVID-19 Infection Survey linked to NHS Test and Trace - England": "CIS-Test & Trace",
    "COVID-19 Infection Survey linked to Combined Vaccination - UK": "CIS-Vaccination",
    "COVID-19 Infection Survey linked to Mortality - England and Wales ONS": "CIS-Mortality",
    "Covid-19 Schools Infection Survey linked with Test and Trace": "Schools IS-Test & Trace",
    "Covid-19 Infection Survey linked with VOA and EPC data": "CIS-VOA/EPC",
}

ADR_ENGLAND_FLAGSHIP_COLLECTION = "ADR England"
OTHER_LINKED_DATASETS_LABEL = "Other linked datasets"


def product_short_label(canonical: str) -> str:
    return PRODUCT_SHORT_LABELS.get(canonical, canonical)


def _availability_to_timestamp(value) -> pd.Timestamp | None:
    """Parse a curated availability value (year, 'YYYY-Qn', 'YYYY-MM', date)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit() and len(text) == 4:
        return pd.Timestamp(int(text), 1, 1)
    normalised = text.upper().replace(" ", "-")
    if len(normalised) == 7 and normalised[4] == "-" and normalised[5] == "Q":
        year, quarter = int(normalised[:4]), int(normalised[6])
        if 1 <= quarter <= 4:
            return pd.Timestamp(year, 3 * quarter - 2, 1)
    try:
        return pd.Timestamp(text)
    except ValueError:
        return None


def _quarter_label(ts) -> str:
    if ts is None or pd.isna(ts):
        return ""
    ts = pd.Timestamp(ts)
    return f"{ts.year} Q{(ts.month - 1) // 3 + 1}"


def _exposure_years(availability: pd.Timestamp | None) -> float:
    """Years of exposure WITHIN the register window, fractional current year.

    Anything available before the window start gets the full window — its rate
    is then count/window by construction, which is the intended reading.
    """
    start = REGISTER_WINDOW_START
    if availability is not None and not pd.isna(availability):
        start = max(start, pd.Timestamp(availability))
    days = (LATEST_REGISTER_DATE - start).days
    return max(days, 0) / 365.25


_reference_indexes = build_indexes(load_reference())

LINKED_PRODUCTS = []
for _record in _reference_indexes.reference.get("linked_products", []):
    _domains = sorted(set(_record.get("component_domains") or []))
    _curated_raw = _record.get("availability_date", None)
    if _curated_raw is None:
        _curated_raw = _record.get("available_from", None)
    _announced_raw = _record.get("availability_announced", None)
    LINKED_PRODUCTS.append({
        "canonical": _record["canonical"],
        "short": product_short_label(_record["canonical"]),
        "component_domains": _domains,
        "is_cross_domain": len(_domains) >= 2,
        "curated_raw": _curated_raw,
        "curated_date": _availability_to_timestamp(_curated_raw),
        # available-by rule (adjudicated, refined 0.5.1): documented_accessible
        # (source evidences actual SRS/DEA access) | announced (source
        # evidences existence only — availability bounded by first use, the
        # announcement kept separately) | bounded_by_first_use |
        # pre_register_window; empty when no curated date exists (proxy).
        "availability_basis": str(_record.get("availability_basis") or ""),
        "availability_source": _record.get("availability_source", ""),
        "announced_raw": _announced_raw,
        "announced_date": _availability_to_timestamp(_announced_raw),
        "flagship_collection": str(_record.get("flagship_collection") or ""),
        "collection_label": str(_record.get("collection_label") or "").strip(),
        "flagship_source": str(_record.get("flagship_source") or ""),
        "flagship_note": str(_record.get("flagship_note") or ""),
    })

# Domain pairs covered by an existing linked product: every pair within a
# cross-domain product's component-domain set is "served".
SERVED_DOMAIN_PAIRS = frozenset(
    frozenset(pair)
    for product in LINKED_PRODUCTS
    for pair in combinations(product["component_domains"], 2)
)

# ---------------------------------------------------------------------------
# Dataset-level exposure (availability-normalised demand, item A)
# ---------------------------------------------------------------------------

_dataset_first_seen = df_datasets.groupby("dataset")["quarter_date"].min()


def _dataset_curated_date(dataset: str) -> pd.Timestamp | None:
    matches = match_linked_products(dataset, _reference_indexes)
    dates = [
        date for date in (
            _availability_to_timestamp(
                record.get("availability_date") or record.get("available_from")
            )
            for record in matches
        )
        if date is not None
    ]
    return min(dates) if dates else None


def dataset_exposure_table() -> pd.DataFrame:
    """Per-dataset availability, exposure years and basis (curated vs proxy)."""
    rows = []
    for dataset, first_seen in _dataset_first_seen.items():
        curated = _dataset_curated_date(dataset)
        availability = curated if curated is not None else first_seen
        rows.append({
            "dataset": dataset,
            "availability_date": availability,
            "availability_basis": (
                "curated" if curated is not None else "first register appearance"
            ),
            "first_seen": first_seen,
            "exposure_years": _exposure_years(availability),
        })
    return pd.DataFrame(rows).set_index("dataset")


DATASET_EXPOSURE = dataset_exposure_table()

# ---------------------------------------------------------------------------
# Product-level adoption (Linked data uptake section, item D)
# ---------------------------------------------------------------------------

_properties = load_register_properties(columns=["matched_products"])
if "Record ID" in df_all.columns and not _properties.empty:
    _product_lookup = (
        _properties.set_index("Record ID")["matched_products"]
    )
    _project_key_col = (
        "Project Row ID"
        if "Project Row ID" in df_all.columns
        else "Project ID" if "Project ID" in df_all.columns else "Record ID"
    )
    _matched = df_all[["Record ID", _project_key_col, "Year", "quarter_date"]].copy()
    _matched["project_key"] = _matched[_project_key_col].astype(str)
    _matched["matched_products"] = (
        _matched["Record ID"].fillna("").astype(str).str.strip().map(_product_lookup).fillna("")
    )
    _matched = _matched[_matched["matched_products"] != ""]
    _matched["product"] = _matched["matched_products"].str.split(";")
    _matched = _matched.explode("product")
    _matched["product"] = _matched["product"].str.strip()
    _matched = _matched[_matched["product"] != ""]
    DF_PRODUCT_PROJECTS = _matched[["project_key", "product", "Year", "quarter_date"]].reset_index(drop=True)
else:
    DF_PRODUCT_PROJECTS = pd.DataFrame(columns=["project_key", "product", "Year", "quarter_date"])

PRODUCT_TOTALS = Counter(DF_PRODUCT_PROJECTS["product"])

_register_years = sorted(int(y) for y in df_all["Year"].dropna().unique())
_register_quarters = list(pd.period_range(
    df_all["quarter_date"].min().to_period("Q"),
    df_all["quarter_date"].max().to_period("Q"),
    freq="Q",
))
_total_by_year = df_all.groupby("Year").size()
_total_by_quarter = df_all.groupby("quarter_date").size()
_first_seen_by_product = DF_PRODUCT_PROJECTS.groupby("product")["quarter_date"].min()
_linked_product_by_canonical = {product["canonical"]: product for product in LINKED_PRODUCTS}
PRODUCT_METADATA = pd.DataFrame([
    {
        "product": product["canonical"],
        "short": product["short"],
        "linkage_span": "Cross-domain" if product["is_cross_domain"] else "Within-domain",
        "flagship_collection": product["flagship_collection"],
        "collection_label": product["collection_label"],
        "is_adr_england_flagship": product["flagship_collection"] == ADR_ENGLAND_FLAGSHIP_COLLECTION,
        "flagship_group": (
            "ADR England flagship"
            if product["flagship_collection"] == ADR_ENGLAND_FLAGSHIP_COLLECTION
            else OTHER_LINKED_DATASETS_LABEL
        ),
    }
    for product in LINKED_PRODUCTS
])

FLAGSHIP_PRODUCTS = [
    product["canonical"]
    for product in LINKED_PRODUCTS
    if product["flagship_collection"] == ADR_ENGLAND_FLAGSHIP_COLLECTION
]
OTHER_PRODUCTS = [
    product["canonical"]
    for product in LINKED_PRODUCTS
    if product["flagship_collection"] != ADR_ENGLAND_FLAGSHIP_COLLECTION
]
ALL_PRODUCT_SELECTION = [*FLAGSHIP_PRODUCTS, *OTHER_PRODUCTS]
PRODUCT_SELECTION_OPTIONS = [
    {
        "label": f"{product['short']} — {product['canonical']}",
        "value": product["canonical"],
    }
    for product in LINKED_PRODUCTS
]


def _product_availability_date(product: str) -> pd.Timestamp | None:
    record = _linked_product_by_canonical.get(product)
    curated = record["curated_date"] if record else None
    seen = _first_seen_by_product.get(product, pd.NaT)
    if curated is not None and not pd.isna(curated):
        return pd.Timestamp(curated)
    if not pd.isna(seen):
        return pd.Timestamp(seen)
    return None


def _product_period_start(product: str, granularity: str) -> pd.Timestamp:
    availability = _product_availability_date(product)
    start = REGISTER_WINDOW_START if availability is None else max(REGISTER_WINDOW_START, availability)
    if granularity == "quarter":
        return start.to_period("Q").start_time
    return pd.Timestamp(start.year, 1, 1)


def _product_by_year() -> pd.DataFrame:
    """Projects per year per product, beginning at product availability."""
    rows = []
    counts = DF_PRODUCT_PROJECTS.groupby(["product", "Year"]).size()
    for product, _ in PRODUCT_TOTALS.most_common():
        start_year = _product_period_start(product, "year").year
        for year in _register_years:
            if year < start_year:
                continue
            total = int(_total_by_year.get(year, 0))
            count = int(counts.get((product, year), 0))
            rows.append({
                "product": product,
                "Year": year,
                "period_date": pd.Timestamp(year, 1, 1),
                "period_label": str(year),
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(
        rows,
        columns=[
            "product", "Year", "period_date", "period_label",
            "count", "total", "pct_of_projects",
        ],
    )


DF_PRODUCT_BY_YEAR = _product_by_year()


def _product_by_quarter() -> pd.DataFrame:
    """Projects per quarter per product, beginning at product availability."""
    rows = []
    counts = DF_PRODUCT_PROJECTS.groupby(["product", "quarter_date"]).size()
    for product, _ in PRODUCT_TOTALS.most_common():
        start_quarter = _product_period_start(product, "quarter")
        for quarter in _register_quarters:
            quarter_start = quarter.start_time
            if quarter_start < start_quarter:
                continue
            total = int(_total_by_quarter.get(quarter_start, 0))
            count = int(counts.get((product, quarter_start), 0))
            rows.append({
                "product": product,
                "Year": int(quarter.year),
                "quarter_date": quarter_start,
                "period_date": quarter_start,
                "period_label": f"{quarter.year} Q{quarter.quarter}",
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(
        rows,
        columns=[
            "product", "Year", "quarter_date", "period_date", "period_label",
            "count", "total", "pct_of_projects",
        ],
    )


DF_PRODUCT_BY_QUARTER = _product_by_quarter()


def _with_product_metadata(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.merge(PRODUCT_METADATA, on="product", how="left")
    work["short"] = work["short"].fillna(work["product"])
    work["linkage_span"] = work["linkage_span"].fillna("Unclassified")
    work["flagship_collection"] = work["flagship_collection"].fillna("")
    work["collection_label"] = work["collection_label"].fillna("")
    work["is_adr_england_flagship"] = work["is_adr_england_flagship"].fillna(False).astype(bool)
    work["flagship_group"] = work["flagship_group"].fillna(OTHER_LINKED_DATASETS_LABEL)
    return work


def _line_span(values: pd.Series) -> str:
    spans = set(values.dropna().astype(str))
    if "Cross-domain" in spans:
        return "Cross-domain"
    if "Within-domain" in spans:
        return "Within-domain"
    return next(iter(spans), "Unclassified")


def _line_start_for_products(products: list[str], granularity: str) -> pd.Timestamp:
    starts = [_product_period_start(product, granularity) for product in products]
    starts = [start for start in starts if start is not None and not pd.isna(start)]
    if not starts:
        return REGISTER_WINDOW_START
    return min(starts)


def _empty_adoption_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "line_id", "line_label", "line_group", "line_linkage_span",
        "product", "period_date", "period_label", "Year", "count",
        "total", "pct_of_projects",
    ])


def adoption_curve_table(
    granularity: str = "year",
    *,
    selected_products: list[str] | None = None,
    collection_view: str | None = None,
) -> pd.DataFrame:
    """Per-product adoption-curve rows for selected linked products."""
    selected = list(dict.fromkeys(selected_products or []))
    if not selected:
        return _empty_adoption_frame()
    if DF_PRODUCT_PROJECTS.empty:
        return _empty_adoption_frame()

    work = DF_PRODUCT_PROJECTS[DF_PRODUCT_PROJECTS["product"].isin(selected)].copy()
    if work.empty:
        return _empty_adoption_frame()
    work = _with_product_metadata(work)
    mode = (
        normalise_collection_view(collection_view)
        if collection_view is not None
        else COLLECTION_VIEW_INDIVIDUAL
    )
    grouped = mode == COLLECTION_VIEW_GROUPED
    has_collection = work["collection_label"].astype(str) != ""

    if grouped:
        work["line_id"] = work["product"]
        work.loc[has_collection, "line_id"] = (
            "collection::" + work.loc[has_collection, "collection_label"].astype(str)
        )
        work["line_label"] = work["short"]
        work.loc[has_collection, "line_label"] = work.loc[has_collection, "collection_label"]
        work["line_group"] = work["flagship_group"]
    else:
        work["line_id"] = work["product"]
        work["line_label"] = work["short"]
        work["line_group"] = work["flagship_group"]

    if granularity == "quarter":
        work["period_date"] = pd.to_datetime(work["quarter_date"])
        work["period_label"] = work["period_date"].dt.to_period("Q").map(
            lambda quarter: f"{quarter.year} Q{quarter.quarter}"
        )
        period_values = [
            {
                "period_key": quarter.start_time,
                "period_date": quarter.start_time,
                "period_label": f"{quarter.year} Q{quarter.quarter}",
                "Year": int(quarter.year),
                "total": int(_total_by_quarter.get(quarter.start_time, 0)),
            }
            for quarter in _register_quarters
        ]
        count_keys = ["line_id", "period_date"]
    else:
        work["period_date"] = work["Year"].map(lambda year: pd.Timestamp(int(year), 1, 1))
        work["period_label"] = work["Year"].astype(int).astype(str)
        period_values = [
            {
                "period_key": int(year),
                "period_date": pd.Timestamp(int(year), 1, 1),
                "period_label": str(int(year)),
                "Year": int(year),
                "total": int(_total_by_year.get(year, 0)),
            }
            for year in _register_years
        ]
        count_keys = ["line_id", "Year"]

    counts = (
        work.drop_duplicates(subset=["line_id", *count_keys[1:], "project_key"])
        .groupby(count_keys)["project_key"]
        .nunique()
    )
    line_meta = (
        work.groupby("line_id", sort=False)
        .agg(
            line_label=("line_label", "first"),
            line_group=("line_group", "first"),
            line_linkage_span=("linkage_span", _line_span),
            products=("product", lambda values: list(dict.fromkeys(values))),
            total_projects=("project_key", lambda values: values.nunique()),
        )
        .sort_values("total_projects", ascending=False, kind="stable")
    )

    rows = []
    for line_id, meta in line_meta.iterrows():
        products = list(meta["products"])
        start = _line_start_for_products(products, granularity)
        for period in period_values:
            period_date = period["period_date"]
            if period_date < start:
                continue
            if granularity == "quarter":
                count_key = (line_id, period_date)
            else:
                count_key = (line_id, period["Year"])
            count = int(counts.get(count_key, 0))
            total = int(period["total"])
            rows.append({
                "line_id": line_id,
                "line_label": str(meta["line_label"]),
                "line_group": str(meta["line_group"]),
                "line_linkage_span": str(meta["line_linkage_span"]),
                "product": "; ".join(products),
                "period_date": period_date,
                "period_label": period["period_label"],
                "Year": int(period["Year"]),
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })

    if not rows:
        return _empty_adoption_frame()
    return pd.DataFrame(rows).sort_values(
        ["line_group", "line_label", "period_date"],
        kind="stable",
    ).reset_index(drop=True)

# Honest annotation/table wording per availability basis: a documented-
# accessible date is a real access date ("available"); announced and bounded
# dates are only upper bounds from observed register use ("available by").
_ANNOTATION_BASIS_LABELS = {
    "documented_accessible": "available",
    "announced": "available by",
    "bounded_by_first_use": "available by",
    "pre_register_window": "available",
}


def _group_product_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary.empty:
        return summary

    work = summary.copy()
    has_collection = work["collection_label"].astype(str) != ""
    work["line_id"] = work["product"]
    work.loc[has_collection, "line_id"] = (
        "collection::" + work.loc[has_collection, "collection_label"].astype(str)
    )
    rows = []
    for line_id, group in work.groupby("line_id", sort=False):
        if str(line_id).startswith("collection::"):
            collection = str(group["collection_label"].iloc[0])
            products = group["product"].dropna().astype(str).tolist()
            project_count = int(
                DF_PRODUCT_PROJECTS.loc[
                    DF_PRODUCT_PROJECTS["product"].isin(products),
                    ["project_key"],
                ]["project_key"].nunique()
            )
            availability_values = [
                value for value in group["availability_date"]
                if value is not None and not pd.isna(value)
            ]
            availability = min(availability_values) if availability_values else pd.NaT
            first_values = [
                _first_seen_by_product.get(product, pd.NaT)
                for product in products
            ]
            first_values = [value for value in first_values if not pd.isna(value)]
            first_use = min(first_values) if first_values else pd.NaT
            exposure = _exposure_years(availability) if not pd.isna(availability) else 0.0
            span = _line_span(group["linkage_span"])
            rows.append({
                "product": collection,
                "short": collection,
                "linkage_span": span,
                "flagship_collection": str(group["flagship_collection"].iloc[0]),
                "collection_label": collection,
                "is_adr_england_flagship": bool(group["is_adr_england_flagship"].any()),
                "flagship_group": str(group["flagship_group"].iloc[0]),
                "availability": _quarter_label(availability),
                "basis": "collection",
                "availability_basis": "collection member availability",
                "availability_date": availability,
                "announced": "",
                "first_use": _quarter_label(first_use),
                "lag_years": None,
                "delivery_lag_years": None,
                "exposure_years": round(exposure, 1),
                "total_projects": project_count,
                "projects_per_exposure_year": round(project_count / exposure, 1) if exposure else None,
            })
        else:
            row = group.iloc[0].drop(labels=["line_id"]).to_dict()
            rows.append(row)
    return pd.DataFrame(rows)


def product_summary_table(
    *,
    collection_view: str | None = None,
    selected_products: list[str] | None = None,
) -> pd.DataFrame:
    """Per-product availability, first accredited use, lags and demand rate.

    Two DISTINCT lag quantities, never conflated:

    - adoption lag (availability -> first DEA use): observable only for
      documented_accessible or pre_register_window dates. For announced or
      bounded dates, availability <= first use with an unknown gap — the
      column stays unset (rendered "n/a (bounded)"), never a false zero.
    - delivery/governance lag (announcement -> first DEA-route use): only for
      announced rows, measuring how long after an announcement the asset first
      shows DEA-gateway use. NOT adoption lag — ECHILD's ~3.5y here is a
      governance delay, not slow researcher uptake.
    """
    rows = []
    for product in LINKED_PRODUCTS:
        canonical = product["canonical"]
        curated = product["curated_date"]
        basis = product["availability_basis"] if curated is not None else "proxy"
        seen = _first_seen_by_product.get(canonical, pd.NaT)
        availability = curated if curated is not None else seen
        exposure = _exposure_years(availability) if not pd.isna(availability) else 0.0
        total = int(PRODUCT_TOTALS.get(canonical, 0))
        if (
            basis in ("documented_accessible", "pre_register_window")
            and curated is not None
            and not pd.isna(seen)
        ):
            lag_years = round((seen - curated).days / 365.25, 1)
        else:
            lag_years = None
        announced_date = product["announced_date"]
        if basis == "announced" and announced_date is not None and not pd.isna(seen):
            delivery_lag_years = round((seen - announced_date).days / 365.25, 1)
        else:
            delivery_lag_years = None
        rows.append({
            "product": canonical,
            "short": product["short"],
            "linkage_span": "Cross-domain" if product["is_cross_domain"] else "Within-domain",
            "flagship_collection": product["flagship_collection"],
            "collection_label": product["collection_label"],
            "is_adr_england_flagship": product["flagship_collection"] == ADR_ENGLAND_FLAGSHIP_COLLECTION,
            "flagship_group": (
                "ADR England flagship"
                if product["flagship_collection"] == ADR_ENGLAND_FLAGSHIP_COLLECTION
                else OTHER_LINKED_DATASETS_LABEL
            ),
            "availability": (
                str(product["curated_raw"]) if curated is not None else _quarter_label(seen)
            ),
            "basis": basis,
            "availability_basis": _ANNOTATION_BASIS_LABELS.get(
                basis, "first register appearance"
            ),
            "availability_date": availability,
            "announced": str(product["announced_raw"]) if announced_date is not None else "",
            "first_use": _quarter_label(seen),
            "lag_years": lag_years,
            "delivery_lag_years": delivery_lag_years,
            "exposure_years": round(exposure, 1),
            "total_projects": total,
            "projects_per_exposure_year": round(total / exposure, 1) if exposure else None,
        })
    summary = pd.DataFrame(rows)
    selected = list(dict.fromkeys(selected_products or []))
    if selected:
        summary = summary[summary["product"].isin(selected)].copy()
    summary_mode = (
        normalise_collection_view(collection_view)
        if collection_view is not None
        else COLLECTION_VIEW_INDIVIDUAL
    )
    if summary_mode == COLLECTION_VIEW_GROUPED:
        summary = _group_product_summary(summary)
    return summary.sort_values(
        "total_projects", ascending=False, kind="stable"
    ).reset_index(drop=True)


PRODUCT_SUMMARY = product_summary_table()


def top_products(n: int) -> list[str]:
    return [product for product, _ in PRODUCT_TOTALS.most_common(n)]


def availability_annotations(n: int = 6) -> list[dict]:
    """Annotation specs for the top-n products: curated date when present,
    else the first-register-appearance proxy, labelled accordingly."""
    summary = PRODUCT_SUMMARY.set_index("product")
    annotations = []
    for product in top_products(n):
        if product not in summary.index:
            continue
        row = summary.loc[product]
        date = row["availability_date"]
        if pd.isna(date):
            continue
        date = pd.Timestamp(date)
        annotations.append({
            "product": product,
            "short": str(row["short"]),
            "date": date,
            "year_fraction": date.year + (date.dayofyear - 1) / 365.25,
            "basis": str(row["availability_basis"]),
        })
    return annotations
