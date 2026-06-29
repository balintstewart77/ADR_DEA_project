import copy
from pathlib import Path
import tempfile
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from analysis.derive_register_properties import (
    REFERENCE_PATH,
    build_indexes,
    derive_properties,
    linkage_span_for_domains,
    load_reference,
    lookup_dataset_record,
    lookup_organisation_record,
    match_linked_products,
    parse_register_entities,
    project_linkage_span,
    _organisation_match_keys,
)
from analysis.register_cleaning import DATA_DIR, load_clean_register


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_REGISTER_PROPERTIES = PROJECT_ROOT / "analysis" / "outputs_deterministic_rc2" / "register_properties.csv"
EXPECTED_2023_066_PRODUCTS = (
    "COVID-19 Infection Survey linked to NHS Test and Trace - England; "
    "COVID-19 Infection Survey linked to Combined Vaccination - UK; "
    "Covid-19 Schools Infection Survey linked with Test and Trace"
)
EXPECTED_2023_228_PRODUCTS = (
    "COVID-19 Infection Survey linked to NHS Test and Trace - England; "
    "COVID-19 Infection Survey linked to Combined Vaccination - UK; "
    "COVID-19 Infection Survey linked to Mortality - England and Wales ONS; "
    "Covid-19 Infection Survey linked with VOA and EPC data"
)


def _derive_current_register_properties() -> pd.DataFrame:
    reference = load_reference(REFERENCE_PATH)
    indexes = build_indexes(reference)
    with tempfile.TemporaryDirectory() as output_dir:
        df, _, _ = load_clean_register(
            DATA_DIR,
            output_dir=output_dir,
            include_quarter_date=True,
            verbose=False,
        )
    datasets, institutions = parse_register_entities(df)
    return derive_properties(df, datasets, institutions, indexes)


def _canonicalise_register_properties(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return (
        df.loc[:, columns]
        .fillna("")
        .astype(str)
        .sort_values("Record ID")
        .reset_index(drop=True)
    )


class DeterministicRegisterPropertiesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference(REFERENCE_PATH)
        cls.indexes = build_indexes(cls.reference)
        cls._current_properties = None

    @classmethod
    def current_register_properties(cls) -> pd.DataFrame:
        if cls._current_properties is None:
            cls._current_properties = _derive_current_register_properties()
        return cls._current_properties.copy()

    def span_for_dataset(self, dataset: str) -> str:
        # Per-product aggregation (reference 0.4.8): the span is the maximum of
        # the matched products' own spans, never a union of their domains.
        return project_linkage_span(
            linkage_span_for_domains(product["component_domains"])
            for product in match_linked_products(dataset, self.indexes)
        )

    def test_linked_products_derive_expected_spans(self):
        cases = {
            "Longitudinal Education Outcomes (LEO)": "Cross-domain record linkage",
            "Education and Child Health Insights from Linked Data (ECHILD)": "Cross-domain record linkage",
            "Linked Census, HES and Mortality Data": "Cross-domain record linkage",
            "Earnings and Employees Study": "Cross-domain record linkage",
            "GRading and Admissions Data England (GRADE)": "Within-domain record linkage",
            "MoJ Data First Crown Court Defendant Case Level": "Within-domain record linkage",
            "Administrative Data | Agricultural Research Collection (AD|ARC)": "Cross-domain record linkage",
            "Growing Up in England Wave 1 (GUIE)": "Cross-domain record linkage",
            # ASHE Longitudinal is a longitudinally-weighted single dataset, not
            # a record linkage (human-adjudicated removal, reference 0.4.4; see
            # test_adjudicated_decisions.py). A stale "Within-domain" expectation
            # here once caused the entry to be wrongly restored to the reference.
            "Annual Survey of Hours and Earnings Longitudinal": "No record linkage",
            "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment": "Within-domain record linkage",
            "Annual Survey of Hours and Earnings linked to Census 2011": "Cross-domain record linkage",
            "ONS Longitudinal Study (LS)": "Cross-domain record linkage",
            "Longitudinal Study of England and Wales": "Cross-domain record linkage",
            "Linked Trade-in-Goods/IDBR": "Within-domain record linkage",
            "Linked Trade-in-Goods/Inter-Departmental Business Register": "Within-domain record linkage",
            "2011 Census linked to Benefits and Income - England and Wales": "Cross-domain record linkage",
            "Nursing and Midwifery Council Register - UK Linked to Census 2021": "Cross-domain record linkage",
            "EOL": "Within-domain record linkage",
            "EOL Dataset (2015-2022)": "Within-domain record linkage",
            "Linked Census and death occurrences - England and Wales": "Cross-domain record linkage",
            "COVID-19 Infection Survey linked to NHS Test and Trace - England": "Within-domain record linkage",
            "Covid-19 Infection Survey linked with Combined Vaccination Dataset": "Within-domain record linkage",
            "COVID-19 Infection Survey linked to Mortality - England and Wales ONS": "Within-domain record linkage",
            "Covid-19 Schools Infection Survey linked with Test and Trace": "Within-domain record linkage",
            "Covid-19 Infection Survey linked with VOA and EPC data": "Cross-domain record linkage",
        }
        for dataset, expected in cases.items():
            with self.subTest(dataset=dataset):
                self.assertEqual(self.span_for_dataset(dataset), expected)

    def test_linked_product_lifecycle_fields_are_present(self):
        for product in self.reference["linked_products"]:
            with self.subTest(product=product["canonical"]):
                self.assertIn(product["status"], {"standing", "discontinued"})
                self.assertIn("available_from", product)
                self.assertIn("discontinued_date", product)
                if product["status"] == "standing":
                    self.assertIsNone(product["discontinued_date"])

    def test_dataset_reference_uses_split_collection_schema(self):
        # The split collection schema arrived in 0.4.1; later revisions must
        # keep it, so assert a minimum version rather than pinning one.
        version = tuple(int(part) for part in self.reference["reference_version"].split("."))
        self.assertGreaterEqual(version, (0, 4, 1))
        for dataset in self.reference["datasets"]:
            with self.subTest(dataset=dataset["canonical"]):
                self.assertNotIn("collection_type", dataset)
                self.assertIn(dataset["collection_method"], {"survey", "administrative"})
                self.assertIn(dataset["temporal_structure"], {"cross-sectional", "longitudinal"})

    def test_multi_product_union_and_no_product(self):
        domains = set()
        for dataset in [
            "GRading and Admissions Data England (GRADE)",
            "MoJ Data First Crown Court Defendant Case Level",
        ]:
            for product in match_linked_products(dataset, self.indexes):
                domains.update(product["component_domains"])
        self.assertEqual(linkage_span_for_domains(domains), "Cross-domain record linkage")
        self.assertEqual(self.span_for_dataset("Annual Business Survey (ABS)"), "No record linkage")

    def test_new_linked_product_aliases_do_not_bleed(self):
        self.assertEqual(self.span_for_dataset("COVID-19 Infection Survey (CIS)"), "No record linkage")
        self.assertEqual(self.span_for_dataset("Inter-Departmental Business Register (IDBR)"), "No record linkage")
        self.assertEqual(self.span_for_dataset("International Trade in Services"), "No record linkage")
        self.assertEqual(self.span_for_dataset("Longitudinal Education Outcomes (LEO)"), "Cross-domain record linkage")
        self.assertEqual(self.span_for_dataset("EOL"), "Within-domain record linkage")

    def test_linked_products_have_dataset_property_records(self):
        missing = []
        for product in self.reference.get("linked_products", []):
            values = [product["canonical"], *(product.get("aliases") or [])]
            if not any(lookup_dataset_record(value, self.indexes) for value in values):
                missing.append(product["canonical"])
        self.assertEqual(missing, [])

    def test_covid_linked_product_regression_records(self):
        # Incident guard: parsed COVID alias variants for these records must keep
        # resolving to the adjudicated linked products.
        properties = self.current_register_properties().set_index("Record ID")
        self.assertEqual(properties.at["2023/066", "matched_products"], EXPECTED_2023_066_PRODUCTS)
        self.assertEqual(properties.at["2023/228", "matched_products"], EXPECTED_2023_228_PRODUCTS)
        self.assertIn("business", properties.at["2021/015", "dataset_units"].split("; "))

    def test_committed_register_properties_are_reproducible(self):
        committed = pd.read_csv(
            COMMITTED_REGISTER_PROPERTIES,
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
        )
        current = self.current_register_properties()
        self.assertEqual(set(current.columns), set(committed.columns))

        columns = committed.columns.tolist()
        assert_frame_equal(
            _canonicalise_register_properties(current, columns),
            _canonicalise_register_properties(committed, columns),
            check_dtype=False,
        )

    def test_linked_products_require_dataset_property_records(self):
        reference = copy.deepcopy(self.reference)
        reference["datasets"] = [
            record for record in reference.get("datasets", [])
            if record.get("canonical") != "EOL"
        ]
        with self.assertRaisesRegex(ValueError, "Linked product 'EOL' has no matching dataset record"):
            build_indexes(reference)

    def test_dataset_worked_edge_cases(self):
        cases = {
            "Census 2011": ("survey", "cross-sectional", "individual"),
            "Understanding Society": ("survey", "longitudinal", "household"),
            "Millennium Cohort Study": ("survey", "longitudinal", "individual"),
            # Census-cored linked-record datasets are survey by primary
            # content (reference 0.4.5 collection-method edge-case rule).
            "ONS Longitudinal Study (LS)": ("survey", "longitudinal", "individual"),
            "Annual Survey of Hours and Earnings (ASHE)": ("survey", "cross-sectional", "individual"),
            "Annual Survey of Hours and Earnings Longitudinal": ("survey", "longitudinal", "individual"),
            "Longitudinal Education Outcomes (LEO)": ("administrative", "longitudinal", "individual"),
            "Education and Child Health Insights from Linked Data (ECHILD)": ("administrative", "longitudinal", "individual"),
            "Linked Census, HES and Mortality Data": ("survey", "longitudinal", "individual"),
            "Public Health Research Database": ("administrative", "longitudinal", "individual"),
            "Earnings and Employees Study": ("survey", "cross-sectional", "individual"),
            "EOL": ("administrative", "longitudinal", "individual"),
            "EOL Dataset (2015-2022)": ("administrative", "longitudinal", "individual"),
            "Death Registrations": ("administrative", "cross-sectional", "individual"),
            "Birth Registrations in England and Wales": ("administrative", "cross-sectional", "individual"),
            "Annual Business Survey (ABS)": ("survey", "cross-sectional", "business"),
            "Annual Population Survey (APS)": ("survey", "cross-sectional", "individual"),
            "Labour Force Survey": ("survey", "cross-sectional", "individual"),
            "Labour Force Survey Longitudinal": ("survey", "longitudinal", "individual"),
            "Decision Maker Panel": ("survey", "longitudinal", "business"),
            "Longitudinal Small Business Survey (LSBS)": ("survey", "longitudinal", "business"),
            "Business Enterprise Research and Development England": ("survey", "cross-sectional", "business"),
            "Products of the European Community": ("survey", "cross-sectional", "business"),
            "Annual Gas and Electricity Consumption at Meter Level": ("administrative", "cross-sectional", "area"),
            "Prices Survey Microdata": ("survey", "cross-sectional", "business"),
            "Bespoke Management and Expectations Survey": ("survey", "cross-sectional", "business"),
            "Over 50s Lifestyle Study": ("survey", "cross-sectional", "individual"),
            "Online Time Use Survey": ("survey", "cross-sectional", "individual"),
            "British Household Panel Survey": ("survey", "longitudinal", "household"),
            "Working Lives of Teachers and Leaders": ("survey", "longitudinal", "individual"),
            "Annual Outward Foreign Direct Investment Survey": ("survey", "cross-sectional", "business"),
            "Survey of Innovation and Patent Use": ("survey", "cross-sectional", "business"),
            "Longitudinal Business Structure Database": ("administrative", "longitudinal", "business"),
            "Monthly Inquiry into the Distributive and Services Sector": ("survey", "cross-sectional", "business"),
            "Monthly Production Inquiry": ("survey", "cross-sectional", "business"),
            "Effects of Tax and Benefits": ("survey", "cross-sectional", "household"),
            "UK Gross Value Added": ("administrative", "cross-sectional", "area"),
            # CPI's primary collection is field price collection (survey),
            # per the sourced note in the reference; aligns with PPI.
            "Consumer Prices Index": ("survey", "cross-sectional", "area"),
            "Producer Price Index": ("survey", "cross-sectional", "business"),
            "Capital Stock Dataset": ("administrative", "cross-sectional", "business"),
            "Capital Stock 2014": ("administrative", "cross-sectional", "business"),
            "Statutory Homelessness Flows England": ("administrative", "cross-sectional", "household"),
        }
        for dataset, (method, temporal, unit) in cases.items():
            with self.subTest(dataset=dataset):
                record = lookup_dataset_record(dataset, self.indexes)
                self.assertIsNotNone(record)
                self.assertNotIn("collection_type", record)
                self.assertEqual(record["collection_method"], method)
                self.assertEqual(record["temporal_structure"], temporal)
                self.assertEqual(record["unit_of_observation"], unit)

    def test_dataset_manual_review_and_non_dataset_entries_are_not_mapped(self):
        for dataset in [
            "Research and Development Expenditures and Subsidies",
            "Firm Productivity",
            "Employment Creation and Survival",
            "Racial Disparity Audit",
            "Bespoke National Council for Voluntary Organisations",
            "Foreign Direct Investment Index",
        ]:
            with self.subTest(dataset=dataset):
                self.assertIsNone(lookup_dataset_record(dataset, self.indexes))

    def test_researcher_sector_worked_edge_cases(self):
        cases = {
            "Nesta": "third-sector",
            "Institute for Fiscal Studies": "third-sector",
            "Bank of England": "government",
            "Office for National Statistics": "government",
            "Frontier Economics Ltd": "commercial",
            "University College London": "academic",
            "Economic and Social Research Institute (ESRI)": "third-sector",
            "Johannes Kepler University Linz": "academic",
            "Tech City UK": "government",
            "University of Derby": "academic",
            "Anglia Ruskin University Higher Education Corporation": "academic",
            "Northumbria University": "academic",
            "University of Suffolk": "academic",
            "Alma Economics": "commercial",
            "AQA Education": "third-sector",
            "Chartered Institute of Personnel and Development": "third-sector",
            "Office of the Victims' Commissioner for England and Wales": "government",
            "Happy City Initiative": "third-sector",
            "New Economics Foundation": "third-sector",
            "Oxford Economics": "commercial",
            "St Mungo's": "third-sector",
            "Columbia University": "academic",
            "Hardisty Jones Associates": "commercial",
            "BOP Consulting": "commercial",
        }
        for organisation, sector in cases.items():
            with self.subTest(organisation=organisation):
                record = lookup_organisation_record(organisation, self.indexes)
                self.assertIsNotNone(record)
                self.assertIn(sector, record["sectors"])

    def test_researcher_sector_acronym_suffixes_match_plain_reference_keys(self):
        cases = {
            "University College London (UCL)": "academic",
            "Institute for Fiscal Studies (IFS)": "third-sector",
            "Office for National Statistics (ONS)": "government",
            "King's College London (KCL)": "academic",
            "National Institute for Economic and Social Research (NIESR)": "third-sector",
            "Public Health Wales (PHW)": "government",
            "London School of Hygiene and Tropical Medicine (LSHTM)": "academic",
            "Competition and Markets Authority (CMA)": "government",
            "Northern Ireland Statistics and Research Agency (NISRA)": "government",
            "Massachusetts Institute of Technology (MIT)": "academic",
            "Department for Business, Energy and Industrial Strategy (BEIS)": "government",
            "Low Pay Commission (LPC)": "government",
            "Department for Business and Trade (DBT)": "government",
            "National Centre for Social Research (NatCen)": "third-sector",
            "Intellectual Property Office (IPO)": "government",
            "Department for Levelling Up, Housing and Communities (DLUHC)": "government",
            "Public Health England (PHE)": "government",
            "National Physical Laboratory (NPL)": "government",
            "Chartered Institute of Personnel and Development (CIPD)": "third-sector",
        }
        for organisation, sector in cases.items():
            with self.subTest(organisation=organisation):
                record = lookup_organisation_record(organisation, self.indexes)
                self.assertIsNotNone(record)
                self.assertIn(sector, record["sectors"])

    def test_organisation_acronym_suffix_normalisation_keeps_near_twins_distinct(self):
        guarded_groups = [
            [
                "National Institute for Economic and Social Research (NIESR)",
                "National Institute of Social and Economic Research",
            ],
            [
                "Public Health England (PHE)",
                "Office for Health Improvement and Disparities (OHID)",
                "UK Health Security Agency",
            ],
            [
                "Department for Business, Energy and Industrial Strategy (BEIS)",
                "Department for Business and Trade (DBT)",
            ],
        ]
        for group in guarded_groups:
            normalised = {_organisation_match_keys(value)[-1] for value in group}
            with self.subTest(group=group):
                self.assertEqual(len(normalised), len(group))

    def test_no_distinct_organisation_reference_records_share_match_keys(self):
        key_to_canonical = {}
        collisions = []
        for record in self.reference.get("organisations", []):
            canonical = record["canonical"]
            for value in [canonical, *(record.get("aliases") or [])]:
                for key in _organisation_match_keys(value):
                    existing = key_to_canonical.setdefault(key, canonical)
                    if existing != canonical:
                        collisions.append((key, existing, canonical))
        self.assertEqual(collisions, [])


if __name__ == "__main__":
    unittest.main()
