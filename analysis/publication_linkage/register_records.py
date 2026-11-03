"""Register projects as matching records.

Builds one :class:`ProjectRecord` per cleaned register entry (stable
``Record ID``), reusing the repository's existing helpers:

* ``dashboard.data.loader.load_raw`` / ``process_data`` for the cleaned,
  deduplicated register;
* ``analysis.derive_register_properties`` for dataset parsing, the reference
  layer (dataset aliases and linked products) and environment labels;
* ``dashboard.institution_normalisation`` for researcher/institution parsing;
* the derived ``register_properties.csv`` named in ``data/release_pointers.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from analysis.derive_register_properties import (
    REFERENCE_PATH,
    build_indexes,
    load_reference,
    lookup_dataset_record,
    match_linked_products,
    parse_register_entities,
)
from analysis.publication_linkage.config import MATURE_COHORT_YEARS, REPO_ROOT
from analysis.publication_linkage.matching import (
    ENVIRONMENT_CODES,
    DatasetTerm,
    build_dataset_terms,
    official_project_id,
)
from dashboard import institution_normalisation as inst
from dashboard.dataset_normalisation import dataset_family_for


@dataclass(frozen=True)
class Researcher:
    name: str
    institution: str  # canonical institution string ("" when unparsed)


@dataclass
class ProjectRecord:
    record_id: str
    project_id: str  # official published Project ID
    title: str
    accreditation_date: date
    environment: str
    environment_code: str | None
    researchers: list[Researcher]
    datasets: list[str]  # canonical register datasets
    providers: list[str]
    linked_products: list[str]
    record_linkage: str
    component_domains: str
    researcher_sectors: str
    dataset_spellings: dict[str, list[str]] = field(default_factory=dict)
    _terms: list[DatasetTerm] | None = field(default=None, repr=False, compare=False)

    @property
    def dataset_terms(self) -> list[DatasetTerm]:
        if self._terms is None:
            self._terms = build_dataset_terms(self.dataset_spellings)
        return self._terms

    @property
    def researcher_names(self) -> list[str]:
        return [researcher.name for researcher in self.researchers]

    def summary(self) -> dict:
        """Register facts given to adjudicators and written to sheets."""
        return {
            "record_id": self.record_id,
            "project_id": self.project_id,
            "title": self.title,
            "accreditation_date": self.accreditation_date.isoformat(),
            "environment": self.environment,
            "researchers": [asdict(researcher) for researcher in self.researchers],
            "datasets": self.datasets,
            "linked_products": self.linked_products,
        }


def parse_researchers(raw: object) -> list[Researcher]:
    """(name, institution) pairs from a register ``Researchers`` field.

    Mirrors the token walk in ``institution_normalisation._parse_institution_rows``
    (which keeps only institutions) so names and institutions are split by the
    same reviewed rules.
    """
    if not isinstance(raw, str) or not raw.strip():
        return []
    text = inst._clean_text(raw)
    researchers: list[Researcher] = []
    seen: set[str] = set()
    for line in inst._build_logical_lines(text):
        if not line or "," not in line:
            continue
        tokens = [inst._clean_fragment(part) for part in line.split(",")]
        tokens = [token for token in tokens if token]
        i = 0
        while i < len(tokens):
            consumed = inst._starts_name(tokens, i)
            if not consumed:
                i += 1
                continue
            name = " ".join(tokens[i: i + consumed])
            i += consumed
            institution_parts: list[str] = []
            while i < len(tokens):
                next_consumed = inst._starts_name(tokens, i)
                if institution_parts and next_consumed:
                    break
                token = tokens[i]
                if institution_parts and inst._looks_like_name(token) and i == len(tokens) - 1:
                    break
                institution_parts.append(token)
                i += 1
            institution = ""
            if institution_parts:
                institution = str(inst.describe_institution_normalisation(", ".join(institution_parts))["institution"])
            key = " ".join(name.split()).casefold()
            if key not in seen:
                seen.add(key)
                researchers.append(Researcher(" ".join(name.split()), institution))
    return researchers


# Matching-only acronyms and common names that the reference layer does not
# list as aliases. They widen text matching; they do not change the reference.
SUPPLEMENTARY_SPELLINGS: dict[str, tuple[str, ...]] = {
    "Understanding Society": ("UKHLS", "UK Household Longitudinal Study"),
    "Inter-Departmental Business Register": ("IDBR",),
    "Annual Respondents Database": ("ARD",),
    "Business Structure Database (BSD)": ("BSD",),
    "National Pupil Database": ("NPD",),
    "Hospital Episode Statistics": ("HES",),
    "Individualised Learner Record": ("ILR",),
    "ONS Longitudinal Study (LS)": ("ONS LS", "ONS Longitudinal Study"),
    "Labour Force Survey": ("LFS",),
    "Annual Population Survey (APS)": ("Annual Population Survey",),
}

_YEAR_RE = re.compile(r"\b(?:19|20)\d\d\b")


def _year_consistent(spelling: str, dataset: str) -> bool:
    """Drop family aliases that name a different year (Census 2021 is not
    Census 2011, even though the reference keys both to the Census family)."""
    dataset_years = set(_YEAR_RE.findall(dataset))
    spelling_years = set(_YEAR_RE.findall(spelling))
    return not dataset_years or not spelling_years or bool(dataset_years & spelling_years)


def _spellings_for_dataset(dataset: str, indexes) -> tuple[list[str], list[str]]:
    """All spellings that name a dataset, plus the linked products it matches."""
    spellings = [dataset]
    family = dataset_family_for(dataset)
    if family:
        spellings.append(family)
    record = lookup_dataset_record(dataset, indexes)
    if record:
        spellings.append(str(record.get("canonical") or ""))
        spellings.extend(str(alias) for alias in record.get("aliases", []) or [])
    products = []
    for product in match_linked_products(dataset, indexes):
        products.append(str(product["canonical"]))
        spellings.append(str(product["canonical"]))
        spellings.extend(str(alias) for alias in product.get("aliases", []) or [])
    for key in [dataset, family, record and record.get("canonical")]:
        if key:
            spellings.extend(SUPPLEMENTARY_SPELLINGS.get(str(key), ()))
    spellings = [s for s in dict.fromkeys(spellings) if s and _year_consistent(s, dataset)]
    if family and family.casefold() == "census" and _YEAR_RE.search(dataset):
        spellings = [s for s in spellings if s.casefold() != "census"]
    return spellings, products


def load_register(version: str = "current") -> tuple[pd.DataFrame, dict]:
    """Cleaned register merged with derived properties, plus snapshot metadata."""
    from analysis.register_manifest import resolve_register_csv
    from dashboard.config import DATA_DIR
    from dashboard.data.loader import load_raw, process_data

    _, manifest_record = resolve_register_csv(DATA_DIR, version)
    df_raw, source_file = load_raw()
    df, _, stats = process_data(df_raw)
    pointers = json.loads((REPO_ROOT / "data" / "release_pointers.json").read_text(encoding="utf-8"))
    properties_path = REPO_ROOT / pointers["register_properties_csv"]
    properties = pd.read_csv(properties_path, encoding="utf-8-sig", dtype=str).fillna("")
    merged = df.merge(properties, on="Record ID", how="left", validate="one_to_one")
    missing = merged["record_linkage"].isna().sum()
    if missing:
        raise ValueError(f"{missing} register records have no derived properties in {properties_path}")
    snapshot_version = str(manifest_record["version"])
    meta = {
        "register_version": snapshot_version,
        "snapshot_date": date(int(snapshot_version[:4]), int(snapshot_version[4:6]), int(snapshot_version[6:8])).isoformat(),
        "register_source_file": source_file,
        "register_sha256_csv": manifest_record.get("sha256_csv"),
        "register_properties_csv": pointers["register_properties_csv"],
        "records": int(len(merged)),
        "cleaning_final_rows": int(stats.get("final_rows", len(merged))),
    }
    return merged, meta


def build_project_records(df: pd.DataFrame) -> list[ProjectRecord]:
    indexes = build_indexes(load_reference(REFERENCE_PATH))
    datasets, _ = parse_register_entities(df)
    by_record_datasets = datasets.groupby("Record ID", sort=False)["dataset"].apply(list).to_dict() if len(datasets) else {}
    by_record_providers = datasets.groupby("Record ID", sort=False)["provider"].apply(list).to_dict() if len(datasets) else {}
    records: list[ProjectRecord] = []
    for row in df.to_dict("records"):
        record_id = str(row["Record ID"])
        records.append(_record_from_row(row, record_id, by_record_datasets, by_record_providers, indexes))
    return records


def _record_from_row(row: dict, record_id: str, by_record_datasets, by_record_providers, indexes) -> ProjectRecord:
    def get(name: str, default: str = "") -> object:
        value = row.get(name, default)
        return default if value is None or (isinstance(value, float) and pd.isna(value)) else value

    project_datasets = list(dict.fromkeys(by_record_datasets.get(record_id, [])))
    spellings: dict[str, list[str]] = {}
    products: list[str] = []
    for dataset in project_datasets:
        dataset_spellings, dataset_products = _spellings_for_dataset(dataset, indexes)
        spellings[dataset] = dataset_spellings
        products.extend(dataset_products)
    environment = str(get("Secure Research Service") or "").strip()
    accreditation = pd.Timestamp(get("Accreditation Date")).date()
    return ProjectRecord(
        record_id=record_id,
        project_id=official_project_id(str(get("Project ID"))),
        title=str(get("Title") or "").strip(),
        accreditation_date=accreditation,
        environment=environment,
        environment_code=ENVIRONMENT_CODES.get(environment),
        researchers=parse_researchers(get("Researchers")),
        datasets=project_datasets,
        providers=list(dict.fromkeys(str(p) for p in by_record_providers.get(record_id, []) if str(p).strip())),
        linked_products=list(dict.fromkeys(products)),
        record_linkage=str(get("record_linkage") or ""),
        component_domains=str(get("record_linkage_component_domains") or ""),
        researcher_sectors=str(get("researcher_sectors") or ""),
        dataset_spellings=spellings,
    )


def mature_cutoff(snapshot_date: date, years: int = MATURE_COHORT_YEARS) -> date:
    """Last accreditation date in the mature cohort (snapshot minus N years)."""
    try:
        return snapshot_date.replace(year=snapshot_date.year - years)
    except ValueError:  # 29 February
        return snapshot_date.replace(year=snapshot_date.year - years, day=28)


def sector_group(sectors: str) -> str:
    """Coarse researcher-sector stratum for sampling and breakdowns."""
    values = {value.strip() for value in str(sectors or "").split(";") if value.strip()}
    if not values or values == {"unclassified"}:
        return "unclassified"
    if "government" in values:
        return "government"
    if values == {"academic"}:
        return "academic"
    if "third-sector" in values:
        return "third-sector"
    if "commercial" in values:
        return "commercial"
    return "other"


def records_frame(records: list[ProjectRecord]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Record ID": record.record_id,
            "Project ID": record.project_id,
            "Title": record.title,
            "accreditation_date": record.accreditation_date.isoformat(),
            "accreditation_year": record.accreditation_date.year,
            "environment": record.environment,
            "n_researchers": len(record.researchers),
            "n_datasets": len(record.datasets),
            "providers": "; ".join(record.providers),
            "datasets": "; ".join(record.datasets),
            "linked_products": "; ".join(record.linked_products),
            "record_linkage": record.record_linkage,
            "researcher_sectors": record.researcher_sectors,
            "sector_group": sector_group(record.researcher_sectors),
            "institutions": "; ".join(dict.fromkeys(r.institution for r in record.researchers if r.institution)),
        }
        for record in records
    ])


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
