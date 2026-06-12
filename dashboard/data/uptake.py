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
    _matched = df_all[["Record ID", "Year", "quarter_date"]].copy()
    _matched["matched_products"] = (
        _matched["Record ID"].fillna("").astype(str).str.strip().map(_product_lookup).fillna("")
    )
    _matched = _matched[_matched["matched_products"] != ""]
    _matched["product"] = _matched["matched_products"].str.split(";")
    _matched = _matched.explode("product")
    _matched["product"] = _matched["product"].str.strip()
    _matched = _matched[_matched["product"] != ""]
    DF_PRODUCT_PROJECTS = _matched[["product", "Year", "quarter_date"]].reset_index(drop=True)
else:
    DF_PRODUCT_PROJECTS = pd.DataFrame(columns=["product", "Year", "quarter_date"])

PRODUCT_TOTALS = Counter(DF_PRODUCT_PROJECTS["product"])

_register_years = sorted(int(y) for y in df_all["Year"].dropna().unique())
_total_by_year = df_all.groupby("Year").size()


def _product_by_year() -> pd.DataFrame:
    """Projects per year per product, explicit zeros so dips show."""
    rows = []
    counts = DF_PRODUCT_PROJECTS.groupby(["product", "Year"]).size()
    for product, _ in PRODUCT_TOTALS.most_common():
        for year in _register_years:
            total = int(_total_by_year.get(year, 0))
            count = int(counts.get((product, year), 0))
            rows.append({
                "product": product,
                "Year": year,
                "count": count,
                "total": total,
                "pct_of_projects": round(count / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(rows, columns=["product", "Year", "count", "total", "pct_of_projects"])


DF_PRODUCT_BY_YEAR = _product_by_year()

# Honest annotation/table wording per availability basis: a documented-
# accessible date is a real access date ("available"); announced and bounded
# dates are only upper bounds from observed register use ("available by").
_ANNOTATION_BASIS_LABELS = {
    "documented_accessible": "available",
    "announced": "available by",
    "bounded_by_first_use": "available by",
    "pre_register_window": "available",
}


def product_summary_table() -> pd.DataFrame:
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
    first_seen = DF_PRODUCT_PROJECTS.groupby("product")["quarter_date"].min()
    rows = []
    for product in LINKED_PRODUCTS:
        canonical = product["canonical"]
        curated = product["curated_date"]
        basis = product["availability_basis"] if curated is not None else "proxy"
        seen = first_seen.get(canonical, pd.NaT)
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
    return pd.DataFrame(rows).sort_values(
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
