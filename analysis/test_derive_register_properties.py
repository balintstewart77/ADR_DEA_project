import copy
import unittest

from analysis.derive_register_properties import (
    REFERENCE_PATH,
    build_indexes,
    linkage_span_for_domains,
    load_reference,
    lookup_dataset_record,
    lookup_organisation_record,
    match_linked_products,
    _organisation_match_keys,
)


class DeterministicRegisterPropertiesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference(REFERENCE_PATH)
        cls.indexes = build_indexes(cls.reference)

    def span_for_dataset(self, dataset: str) -> str:
        domains = set()
        for product in match_linked_products(dataset, self.indexes):
            domains.update(product["component_domains"])
        return linkage_span_for_domains(domains)

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
            "Annual Survey of Hours and Earnings Longitudinal": "Within-domain record linkage",
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
        self.assertEqual(self.reference["reference_version"], "0.4.1")
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
            "ONS Longitudinal Study (LS)": ("administrative", "longitudinal", "individual"),
            "Annual Survey of Hours and Earnings (ASHE)": ("survey", "cross-sectional", "individual"),
            "Annual Survey of Hours and Earnings Longitudinal": ("survey", "longitudinal", "individual"),
            "Longitudinal Education Outcomes (LEO)": ("administrative", "longitudinal", "individual"),
            "Education and Child Health Insights from Linked Data (ECHILD)": ("administrative", "longitudinal", "individual"),
            "Linked Census, HES and Mortality Data": ("administrative", "longitudinal", "individual"),
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
            "Consumer Prices Index": ("administrative", "cross-sectional", "area"),
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
