"""Derive deterministic rc2 register properties from the reference YAML."""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import yaml

try:
    from analysis.register_cleaning import CANDIDATE_FILES, DATA_DIR, load_clean_register
    from analysis.run_manifest import git_state, write_manifest
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROJECT_ROOT))
    from analysis.register_cleaning import CANDIDATE_FILES, DATA_DIR, load_clean_register  # type: ignore
    from analysis.run_manifest import git_state, write_manifest  # type: ignore

from dashboard.dataset_normalisation import dataset_family_for, normalise_dataset_name, parse_datasets
from dashboard.institution_normalisation import parse_institutions


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
REFERENCE_PATH = ANALYSIS_DIR / "register_reference.yaml"
DEFAULT_OUTPUT_DIR = ANALYSIS_DIR / "outputs_deterministic_rc2"
DEFAULT_REPORT_PATH = ANALYSIS_DIR / "outputs" / "instruction_rc2_reference_report.md"

COLLECTION_TYPES = ("survey", "cohort", "administrative")
UNITS = ("individual", "household", "business", "area")
SECTORS = ("academic", "government", "third-sector", "commercial", "unclassified")
DOMAIN_ORDER = (
    "Education & Skills",
    "Health & Social Care",
    "Labour Market & Employment",
    "Business & Productivity",
    "Income, Poverty & Inequality",
    "Housing & Planning",
    "Crime & Justice",
    "Migration & Demographics",
    "Environment & Agriculture",
    "Public Finance & Taxation",
    "Transport & Mobility",
    "COVID-19 & Pandemic",
    "Data Infrastructure & Methodology",
    "Other / Cross-sector",
    "Unclear from Register Entry",
)
LINKAGE_SPANS = (
    "No record linkage",
    "Within-domain record linkage",
    "Cross-domain record linkage",
)
LINKED_PRODUCT_STATUSES = ("standing", "discontinued")
RC1_PATH_PREFIXES = (
    "analysis/outputs_v3/",
    "analysis/outputs_v4_",
    "analysis/outputs_comparison_",
)


@dataclass(frozen=True)
class ReferenceIndexes:
    reference: dict
    dataset_by_key: dict[str, dict]
    organisation_by_key: dict[str, dict]
    linked_product_by_key: dict[str, list[dict]]
    linked_product_order: dict[str, int]


def _key(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def _as_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _ordered(values: Iterable[str], order: Iterable[str]) -> list[str]:
    wanted = set(values)
    ordered = [value for value in order if value in wanted]
    ordered.extend(sorted(wanted - set(ordered)))
    return ordered


def _join(values: Iterable[str], order: Iterable[str] | None = None) -> str:
    values = list(values)
    if order is not None:
        values = _ordered(values, order)
    else:
        values = sorted(set(values))
    return "; ".join(values)


def _dataset_match_keys(name: str) -> list[str]:
    """Return exact then reviewed-family lookup keys for a canonical dataset."""
    canonical = normalise_dataset_name(name)
    keys = [_key(canonical)]
    family = dataset_family_for(canonical)
    if family:
        keys.append(_key(family))
    return [item for i, item in enumerate(keys) if item and item not in keys[:i]]


def _reference_dataset_keys(value: str) -> set[str]:
    keys = {_key(value)}
    normalised = normalise_dataset_name(value)
    keys.add(_key(normalised))
    return {item for item in keys if item}


def _reference_literal_keys(value: str) -> set[str]:
    keys = {_key(value)}
    normalised = normalise_dataset_name(value)
    keys.add(_key(normalised))
    return {item for item in keys if item}


def load_reference(path: str | Path = REFERENCE_PATH) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        reference = yaml.safe_load(f)
    if not isinstance(reference, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return reference


def _add_unique(mapping: dict[str, dict], key: str, record: dict, section: str) -> None:
    if key in mapping and mapping[key] is not record:
        existing = mapping[key].get("canonical", "<unknown>")
        incoming = record.get("canonical", "<unknown>")
        raise ValueError(f"Duplicate {section} reference key {key!r}: {existing!r} and {incoming!r}")
    mapping[key] = record


def build_indexes(reference: dict) -> ReferenceIndexes:
    validate_reference(reference)
    dataset_by_key: dict[str, dict] = {}
    for record in reference.get("datasets", []):
        values = [record["canonical"], *_as_list(record.get("aliases"))]
        for value in values:
            for key in _reference_dataset_keys(str(value)):
                _add_unique(dataset_by_key, key, record, "dataset")

    organisation_by_key: dict[str, dict] = {}
    for record in reference.get("organisations", []):
        values = [record["canonical"], *_as_list(record.get("aliases"))]
        for value in values:
            _add_unique(organisation_by_key, _key(value), record, "organisation")

    linked_product_by_key: dict[str, list[dict]] = defaultdict(list)
    linked_product_order: dict[str, int] = {}
    for i, record in enumerate(reference.get("linked_products", [])):
        linked_product_order[record["canonical"]] = i
        values = [record["canonical"], *_as_list(record.get("aliases"))]
        keys: set[str] = set()
        for value in values:
            keys.update(_reference_literal_keys(str(value)))
        for key in keys:
            if not key:
                continue
            if record not in linked_product_by_key[key]:
                linked_product_by_key[key].append(record)

    return ReferenceIndexes(
        reference=reference,
        dataset_by_key=dataset_by_key,
        organisation_by_key=organisation_by_key,
        linked_product_by_key=dict(linked_product_by_key),
        linked_product_order=linked_product_order,
    )


def validate_reference(reference: dict) -> None:
    if not reference.get("reference_version"):
        raise ValueError("reference_version is required")
    if not reference.get("meta_principle"):
        raise ValueError("meta_principle is required")

    seen_datasets: set[str] = set()
    for record in reference.get("datasets", []):
        canonical = record.get("canonical")
        if not canonical:
            raise ValueError("Every dataset record needs canonical")
        if canonical in seen_datasets:
            raise ValueError(f"Duplicate dataset record {canonical!r}")
        seen_datasets.add(canonical)
        if record.get("collection_type") not in COLLECTION_TYPES:
            raise ValueError(f"{canonical!r} has invalid collection_type {record.get('collection_type')!r}")
        if record.get("unit_of_observation") not in UNITS:
            raise ValueError(f"{canonical!r} has invalid unit_of_observation {record.get('unit_of_observation')!r}")

    seen_orgs: set[str] = set()
    for record in reference.get("organisations", []):
        canonical = record.get("canonical")
        if not canonical:
            raise ValueError("Every organisation record needs canonical")
        if canonical in seen_orgs:
            raise ValueError(f"Duplicate organisation record {canonical!r}")
        seen_orgs.add(canonical)
        sectors = _as_list(record.get("sectors"))
        if not sectors:
            raise ValueError(f"{canonical!r} has no sectors")
        invalid = sorted(set(sectors) - set(SECTORS))
        if invalid:
            raise ValueError(f"{canonical!r} has invalid sectors {invalid!r}")

    seen_products: set[str] = set()
    for record in reference.get("linked_products", []):
        canonical = record.get("canonical")
        if not canonical:
            raise ValueError("Every linked product record needs canonical")
        if canonical in seen_products:
            raise ValueError(f"Duplicate linked product record {canonical!r}")
        seen_products.add(canonical)
        status = record.get("status")
        if status not in LINKED_PRODUCT_STATUSES:
            raise ValueError(f"{canonical!r} has invalid linked-product status {status!r}")
        if "available_from" not in record:
            raise ValueError(f"{canonical!r} is missing available_from")
        if "discontinued_date" not in record:
            raise ValueError(f"{canonical!r} is missing discontinued_date")
        if status == "standing" and record.get("discontinued_date") is not None:
            raise ValueError(f"{canonical!r} is standing but has discontinued_date")
        domains = _as_list(record.get("component_domains"))
        if not domains:
            raise ValueError(f"{canonical!r} has no component_domains")
        invalid = sorted(set(domains) - set(DOMAIN_ORDER))
        if invalid:
            raise ValueError(f"{canonical!r} has invalid component domains {invalid!r}")


def lookup_dataset_record(canonical_dataset: str, indexes: ReferenceIndexes) -> dict | None:
    for key in _dataset_match_keys(canonical_dataset):
        record = indexes.dataset_by_key.get(key)
        if record is not None:
            return record
    return None


def lookup_organisation_record(institution: str, indexes: ReferenceIndexes) -> dict | None:
    return indexes.organisation_by_key.get(_key(institution))


def match_linked_products(canonical_dataset: str, indexes: ReferenceIndexes) -> list[dict]:
    matches: list[dict] = []
    for key in _dataset_match_keys(canonical_dataset):
        for record in indexes.linked_product_by_key.get(key, []):
            if record not in matches:
                matches.append(record)
    return sorted(matches, key=lambda record: indexes.linked_product_order[record["canonical"]])


def linkage_span_for_domains(component_domains: Iterable[str]) -> str:
    domains = set(component_domains)
    if not domains:
        return "No record linkage"
    if len(domains) == 1:
        return "Within-domain record linkage"
    return "Cross-domain record linkage"


def _register_with_record_ids_for_parsers(df: pd.DataFrame) -> pd.DataFrame:
    parser_df = df.copy()
    parser_df["Project ID"] = parser_df["Record ID"]
    return parser_df


def parse_register_entities(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    parser_df = _register_with_record_ids_for_parsers(df)
    datasets = parse_datasets(parser_df).rename(columns={"Project ID": "Record ID"})
    institutions = parse_institutions(parser_df).rename(columns={"Project ID": "Record ID"})
    return datasets, institutions


def derive_properties(
    df: pd.DataFrame,
    datasets: pd.DataFrame,
    institutions: pd.DataFrame,
    indexes: ReferenceIndexes,
) -> pd.DataFrame:
    datasets_by_record = datasets.groupby("Record ID", sort=False)["dataset"].apply(list).to_dict() if len(datasets) else {}
    institutions_by_record = (
        institutions.groupby("Record ID", sort=False)["institution"].apply(list).to_dict()
        if len(institutions)
        else {}
    )

    rows = []
    for _, project in df.iterrows():
        record_id = str(project["Record ID"])
        project_datasets = datasets_by_record.get(record_id, [])
        project_institutions = institutions_by_record.get(record_id, [])

        matched_product_names: list[str] = []
        component_domains: set[str] = set()
        for dataset in project_datasets:
            for product in match_linked_products(dataset, indexes):
                product_name = product["canonical"]
                if product_name not in matched_product_names:
                    matched_product_names.append(product_name)
                component_domains.update(_as_list(product.get("component_domains")))

        collection_types: set[str] = set()
        units: set[str] = set()
        for dataset in project_datasets:
            record = lookup_dataset_record(dataset, indexes)
            if record is None:
                continue
            collection_types.add(record["collection_type"])
            units.add(record["unit_of_observation"])

        sectors: set[str] = set()
        for institution in project_institutions:
            record = lookup_organisation_record(institution, indexes)
            if record is None:
                sectors.add("unclassified")
            else:
                sectors.update(_as_list(record.get("sectors")))
        if not sectors and not project_institutions:
            sectors.add("unclassified")

        rows.append({
            "Record ID": record_id,
            "record_linkage": linkage_span_for_domains(component_domains),
            "matched_products": _join(
                matched_product_names,
                [record["canonical"] for record in indexes.reference.get("linked_products", [])],
            ),
            "record_linkage_component_domains": _join(component_domains, DOMAIN_ORDER),
            "dataset_collection_types": _join(collection_types, COLLECTION_TYPES),
            "dataset_units": _join(units, UNITS),
            "researcher_sectors": _join(sectors, SECTORS),
        })

    return pd.DataFrame(rows)


def coverage_summary(
    datasets: pd.DataFrame,
    institutions: pd.DataFrame,
    indexes: ReferenceIndexes,
) -> dict:
    dataset_counts = Counter(datasets["dataset"].astype(str)) if len(datasets) else Counter()
    dataset_matched_counts = Counter()
    dataset_unmatched_counts = Counter()
    for dataset, count in dataset_counts.items():
        if lookup_dataset_record(dataset, indexes):
            dataset_matched_counts[dataset] = count
        else:
            dataset_unmatched_counts[dataset] = count

    org_counts = Counter(institutions["institution"].astype(str)) if len(institutions) else Counter()
    org_matched_counts = Counter()
    org_unmatched_counts = Counter()
    for institution, count in org_counts.items():
        if lookup_organisation_record(institution, indexes):
            org_matched_counts[institution] = count
        else:
            org_unmatched_counts[institution] = count

    return {
        "dataset_mentions_total": sum(dataset_counts.values()),
        "dataset_mentions_matched": sum(dataset_matched_counts.values()),
        "dataset_unique_total": len(dataset_counts),
        "dataset_unique_matched": len(dataset_matched_counts),
        "dataset_unmatched_counts": dataset_unmatched_counts,
        "organisation_mentions_total": sum(org_counts.values()),
        "organisation_mentions_matched": sum(org_matched_counts.values()),
        "organisation_unique_total": len(org_counts),
        "organisation_unique_matched": len(org_matched_counts),
        "organisation_unmatched_counts": org_unmatched_counts,
    }


def organisation_review_table(institutions: pd.DataFrame, indexes: ReferenceIndexes) -> pd.DataFrame:
    """Return every parsed organisation name with reference-match status."""
    columns = [
        "organisation",
        "mentions",
        "project_count",
        "matched_reference",
        "reference_canonical",
        "sectors",
        "example_record_ids",
        "suggested_canonical",
        "review_note",
    ]
    if not len(institutions):
        return pd.DataFrame(columns=columns)

    rows = []
    grouped = institutions.groupby("institution", sort=True)
    for organisation, group in grouped:
        record = lookup_organisation_record(str(organisation), indexes)
        sectors = _join(_as_list(record.get("sectors")) if record else [], SECTORS)
        example_ids = [
            str(record_id)
            for record_id in group["Record ID"].dropna().astype(str).drop_duplicates().head(10).tolist()
        ]
        rows.append({
            "organisation": str(organisation),
            "mentions": int(len(group)),
            "project_count": int(group["Record ID"].nunique()),
            "matched_reference": bool(record),
            "reference_canonical": record.get("canonical", "") if record else "",
            "sectors": sectors,
            "example_record_ids": "; ".join(example_ids),
            "suggested_canonical": "",
            "review_note": "",
        })

    review = pd.DataFrame(rows, columns=columns)
    return review.sort_values(
        by=["matched_reference", "organisation"],
        ascending=[True, True],
        kind="stable",
    ).reset_index(drop=True)


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def _series_markdown(series: pd.Series, *, name: str, limit: int | None = None) -> str:
    if limit is not None:
        series = series.head(limit)
    lines = [f"| {name} | Count |", "|---|---:|"]
    for index, value in series.items():
        label = _md(str(index) if str(index) else "(blank)")
        lines.append(f"| {label} | {int(value)} |")
    return "\n".join(lines)


def _md(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _counter_markdown(counter: Counter, *, name: str, limit: int = 20) -> str:
    lines = [f"| {name} | Mentions |", "|---|---:|"]
    for label, count in counter.most_common(limit):
        lines.append(f"| {_md(label)} | {count} |")
    if len(lines) == 2:
        lines.append("| None | 0 |")
    return "\n".join(lines)


def _edge_dataset_checks(indexes: ReferenceIndexes) -> list[dict[str, str]]:
    cases = [
        ("Census", "survey", "individual"),
        ("Understanding Society", "cohort", "household"),
        ("Annual Survey of Hours and Earnings (ASHE)", "survey", "individual"),
        ("Longitudinal Education Outcomes (LEO)", "administrative", "individual"),
        ("Education and Child Health Insights from Linked Data (ECHILD)", "administrative", "individual"),
        ("Linked Census, HES and Mortality Data", "administrative", "individual"),
        ("Death Registrations", "administrative", "individual"),
        ("Birth Registrations in England and Wales", "administrative", "individual"),
        ("Decision Maker Panel", "cohort", "business"),
        ("Longitudinal Small Business Survey (LSBS)", "cohort", "business"),
    ]
    rows = []
    for name, expected_collection, expected_unit in cases:
        record = lookup_dataset_record(name, indexes)
        rows.append({
            "Dataset": name,
            "Collection": record.get("collection_type", "UNMATCHED") if record else "UNMATCHED",
            "Unit": record.get("unit_of_observation", "UNMATCHED") if record else "UNMATCHED",
            "Expected": f"{expected_collection} / {expected_unit}",
            "Pass": str(bool(record and record.get("collection_type") == expected_collection and record.get("unit_of_observation") == expected_unit)),
        })
    return rows


def _edge_sector_checks(indexes: ReferenceIndexes) -> list[dict[str, str]]:
    cases = [
        ("Nesta", "third-sector"),
        ("Institute for Fiscal Studies", "third-sector"),
        ("Bank of England", "government"),
        ("Office for National Statistics", "government"),
        ("Frontier Economics Ltd", "commercial"),
        ("University College London", "academic"),
        ("Tech City UK", "government"),
        ("Office of the Victims' Commissioner for England and Wales", "government"),
        ("Chartered Institute of Personnel and Development", "third-sector"),
        ("Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR)", "unclassified"),
        ("Equality and Human Rights Commission (EHRC)", "government"),
    ]
    rows = []
    for name, expected in cases:
        record = lookup_organisation_record(name, indexes)
        sectors = _as_list(record.get("sectors")) if record else ["UNMATCHED"]
        rows.append({
            "Organisation": name,
            "Sectors": "; ".join(sectors),
            "Expected": expected,
            "Pass": str(expected in sectors),
        })
    return rows


def _edge_linkage_checks(indexes: ReferenceIndexes) -> list[dict[str, str]]:
    cases = [
        ("Longitudinal Education Outcomes (LEO)", "Cross-domain record linkage"),
        ("Education and Child Health Insights from Linked Data (ECHILD)", "Cross-domain record linkage"),
        ("Linked Census, HES and Mortality Data", "Cross-domain record linkage"),
        ("GRading and Admissions Data England (GRADE)", "Within-domain record linkage"),
        ("MoJ Data First Crown Court Defendant Case Level", "Within-domain record linkage"),
        ("Administrative Data | Agricultural Research Collection (AD|ARC)", "Cross-domain record linkage"),
        ("Growing Up in England Wave 1 (GUIE)", "Cross-domain record linkage"),
        ("Annual Survey of Hours and Earnings Longitudinal", "Within-domain record linkage"),
        ("Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment", "Within-domain record linkage"),
        ("Annual Survey of Hours and Earnings linked to Census 2011", "Cross-domain record linkage"),
        ("Annual Business Survey (ABS)", "No record linkage"),
    ]
    rows = []
    for dataset, expected in cases:
        domains: set[str] = set()
        products = match_linked_products(dataset, indexes)
        for product in products:
            domains.update(_as_list(product.get("component_domains")))
        span = linkage_span_for_domains(domains)
        rows.append({
            "Dataset": dataset,
            "Products": "; ".join(product["canonical"] for product in products),
            "Span": span,
            "Expected": expected,
            "Pass": str(span == expected),
        })
    return rows


def _rows_markdown(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    columns = list(rows[0].keys())
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_md(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)


def _reference_review_notes_markdown(reference: dict) -> str:
    rows = []
    for item in reference.get("dataset_lookup_review_notes", []):
        if not isinstance(item, dict):
            continue
        rows.append({
            "Raw entry": item.get("raw", ""),
            "Action": item.get("action", ""),
            "Rationale": " ".join(str(item.get("rationale", "")).split()),
        })
    return _rows_markdown(rows)


def _spot_check_rows(df: pd.DataFrame, properties: pd.DataFrame, *, n: int = 15) -> list[dict[str, str]]:
    merged = df[["Record ID", "Title", "Datasets Used"]].merge(properties, on="Record ID", how="left")
    linked = merged[merged["matched_products"].astype(str).str.len() > 0].head(n)
    if len(linked) < n:
        linked = pd.concat([linked, merged[~merged["Record ID"].isin(linked["Record ID"])].head(n - len(linked))])
    rows = []
    for _, row in linked.iterrows():
        rows.append({
            "Record ID": str(row["Record ID"]),
            "Title": " ".join(str(row["Title"]).split())[:100],
            "Record linkage": str(row["record_linkage"]),
            "Products": str(row["matched_products"])[:120],
            "Dataset types": str(row["dataset_collection_types"]),
            "Units": str(row["dataset_units"]),
            "Sectors": str(row["researcher_sectors"]),
        })
    return rows


def _rc1_status_note() -> str:
    status = git_state().get("status_porcelain", "")
    touched = []
    for line in str(status).splitlines():
        path = line[3:] if len(line) > 3 else line
        if path.startswith(RC1_PATH_PREFIXES):
            touched.append(line)
    if not touched:
        return "No git status entries under rc1 output prefixes were present after this run."
    return "Potential rc1 path status entries:\n\n" + "\n".join(f"- `{line}`" for line in touched)


def write_report(
    report_path: Path,
    *,
    reference: dict,
    df: pd.DataFrame,
    datasets: pd.DataFrame,
    institutions: pd.DataFrame,
    properties: pd.DataFrame,
    coverage: dict,
    output_csv: Path,
    output_manifest: Path,
    quality_manifest: Path,
    report_manifest: Path,
    indexes: ReferenceIndexes,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    collection_distribution = properties["dataset_collection_types"].replace("", "(none matched)").value_counts()
    unit_distribution = properties["dataset_units"].replace("", "(none matched)").value_counts()
    sector_distribution = properties["researcher_sectors"].replace("", "(none)").value_counts()
    span_distribution = properties["record_linkage"].value_counts().reindex(LINKAGE_SPANS, fill_value=0)

    dataset_total = int(coverage["dataset_mentions_total"])
    dataset_matched = int(coverage["dataset_mentions_matched"])
    org_total = int(coverage["organisation_mentions_total"])
    org_matched = int(coverage["organisation_mentions_matched"])

    lines = [
        "# rc2 deterministic reference report",
        "",
        "## Scope",
        "",
        (
            f"Reference version `{reference['reference_version']}` was applied to "
            f"{len(df):,} cleaned DEA register records. Output CSV: `{output_csv.relative_to(PROJECT_ROOT)}`."
        ),
        "",
        "This run is deterministic and uses no LLM calls.",
        "",
        "## Canonical keys",
        "",
        (
            "Datasets are parsed with `dashboard.dataset_normalisation.parse_datasets`, "
            "which applies `normalise_dataset_name` to each parsed dataset entry. "
            "Lookup first uses that exact canonical dataset string, then falls back "
            "to `dataset_family_for` where the normaliser defines a reviewed family key."
        ),
        "",
        (
            "Researcher organisations are parsed with "
            "`dashboard.institution_normalisation.parse_institutions` and matched on "
            "the parser's canonical `institution` string."
        ),
        "",
        "## Record linkage",
        "",
        reference["linked_products_rule"]["rule"],
        "",
        reference["linked_products_rule"]["lens_vs_object_rule"],
        "",
        _series_markdown(span_distribution, name="Record linkage span"),
        "",
        "### Linkage edge checks",
        "",
        _rows_markdown(_edge_linkage_checks(indexes)),
        "",
        "## Dataset collection type",
        "",
        reference["dataset_collection_type_rule"]["rule"],
        "",
        reference["dataset_collection_type_rule"]["acknowledged_simplification"],
        "",
        _series_markdown(collection_distribution, name="Project collection-type set"),
        "",
        "## Dataset unit of observation",
        "",
        reference["dataset_unit_rule"]["rule"],
        "",
        reference["dataset_unit_rule"]["cross_facet_consistency_note"],
        "",
        _series_markdown(unit_distribution, name="Project unit set"),
        "",
        "### Dataset edge checks",
        "",
        _rows_markdown(_edge_dataset_checks(indexes)),
        "",
        "## Researcher sector",
        "",
        reference["researcher_sector_rule"]["rule"],
        "",
        _series_markdown(sector_distribution, name="Project researcher-sector set"),
        "",
        "### Sector edge checks",
        "",
        _rows_markdown(_edge_sector_checks(indexes)),
        "",
        "## Coverage and unmatched tail",
        "",
        (
            f"Dataset reference coverage: {dataset_matched:,}/{dataset_total:,} "
            f"project-dataset mentions ({_pct(dataset_matched, dataset_total)}), "
            f"{coverage['dataset_unique_matched']:,}/{coverage['dataset_unique_total']:,} "
            "unique canonical datasets."
        ),
        "",
        (
            f"Organisation reference coverage: {org_matched:,}/{org_total:,} "
            f"project-organisation mentions ({_pct(org_matched, org_total)}), "
            f"{coverage['organisation_unique_matched']:,}/{coverage['organisation_unique_total']:,} "
            "unique canonical organisations."
        ),
        "",
        "Largest unmatched datasets:",
        "",
        _counter_markdown(coverage["dataset_unmatched_counts"], name="Dataset", limit=25),
        "",
        "Largest unmatched organisations:",
        "",
        _counter_markdown(coverage["organisation_unmatched_counts"], name="Organisation", limit=25),
        "",
        "### Deliberate non-mappings and manual-review dataset names",
        "",
        _reference_review_notes_markdown(reference),
        "",
        "## Spot-check sample",
        "",
        _rows_markdown(_spot_check_rows(df, properties, n=15)),
        "",
        "## Judgement calls",
        "",
        (
            "- `AD|ARC` is labelled administrative/business for dataset facets. "
            "The product links individual and farm-level data, but the farm or "
            "agricultural holding is treated as the closest available structural unit."
        ),
        (
            "- `Data First` is labelled administrative/individual for dataset facets. "
            "The extracts include case and journey structures, but the deterministic "
            "single-label unit is person-defendant/offender oriented."
        ),
        (
            "- `Consumer Prices Index` is labelled administrative/area because the "
            "allowed unit vocabulary has no product or price-observation unit."
        ),
        "",
        "## Manifests and rc1",
        "",
        f"Deterministic output manifest: `{output_manifest.relative_to(PROJECT_ROOT)}`.",
        "",
        f"Quality output manifest: `{quality_manifest.relative_to(PROJECT_ROOT)}`.",
        "",
        f"Report output manifest: `{report_manifest.relative_to(PROJECT_ROOT)}`.",
        "",
        _rc1_status_note(),
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")


def run(
    *,
    reference_path: Path = REFERENCE_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> tuple[pd.DataFrame, dict]:
    reference = load_reference(reference_path)
    indexes = build_indexes(reference)

    df, cleaning_stats, source_file = load_clean_register(
        DATA_DIR,
        candidate_files=CANDIDATE_FILES,
        output_dir=str(output_dir),
        include_quarter_date=True,
        verbose=False,
    )
    datasets, institutions = parse_register_entities(df)
    properties = derive_properties(df, datasets, institutions, indexes)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "register_properties.csv"
    properties.to_csv(output_csv, index=False, encoding="utf-8-sig")

    quality_dir = output_dir / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    organisation_review_csv = quality_dir / "organisation_names_for_review.csv"
    organisation_review_table(institutions, indexes).to_csv(
        organisation_review_csv,
        index=False,
        encoding="utf-8-sig",
    )

    coverage = coverage_summary(datasets, institutions, indexes)
    manifest_extra = {
        "source_file": source_file,
        "cleaning_stats": cleaning_stats,
        "row_count": len(properties),
        "output_files": [str(output_csv.relative_to(PROJECT_ROOT))],
    }
    output_manifest = write_manifest(
        output_dir,
        run_type="deterministic_properties",
        model=None,
        reference_table_version=reference["reference_version"],
        extra=manifest_extra,
    )
    quality_manifest = write_manifest(
        quality_dir,
        run_type="deterministic_properties_quality",
        model=None,
        reference_table_version=reference["reference_version"],
        extra={
            "source_file": source_file,
            "output_files": [
                str((quality_dir / "duplicate_review_flagged.csv").relative_to(PROJECT_ROOT)),
                str(organisation_review_csv.relative_to(PROJECT_ROOT)),
            ],
        },
    )

    report_manifest = write_manifest(
        report_path.parent,
        run_type="deterministic_properties_report",
        model=None,
        reference_table_version=reference["reference_version"],
        extra={
            "source_file": source_file,
            "report_file": str(report_path.relative_to(PROJECT_ROOT)),
            "deterministic_output_dir": str(output_dir.relative_to(PROJECT_ROOT)),
        },
    )
    write_report(
        report_path,
        reference=reference,
        df=df,
        datasets=datasets,
        institutions=institutions,
        properties=properties,
        coverage=coverage,
        output_csv=output_csv,
        output_manifest=output_manifest,
        quality_manifest=quality_manifest,
        report_manifest=report_manifest,
        indexes=indexes,
    )
    return properties, coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=REFERENCE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    properties, coverage = run(
        reference_path=args.reference,
        output_dir=args.output_dir,
        report_path=args.report,
    )
    print(f"Wrote {len(properties):,} project rows to {args.output_dir / 'register_properties.csv'}")
    print(
        "Dataset coverage: "
        f"{coverage['dataset_mentions_matched']:,}/{coverage['dataset_mentions_total']:,} "
        f"({_pct(coverage['dataset_mentions_matched'], coverage['dataset_mentions_total'])})"
    )
    print(
        "Organisation coverage: "
        f"{coverage['organisation_mentions_matched']:,}/{coverage['organisation_mentions_total']:,} "
        f"({_pct(coverage['organisation_mentions_matched'], coverage['organisation_mentions_total'])})"
    )


if __name__ == "__main__":
    main()
