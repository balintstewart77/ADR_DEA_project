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
            "Census 2011": ("survey", "individual"),
            "Understanding Society": ("cohort", "household"),
            "Annual Survey of Hours and Earnings (ASHE)": ("survey", "individual"),
            "Longitudinal Education Outcomes (LEO)": ("administrative", "individual"),
            "Education and Child Health Insights from Linked Data (ECHILD)": ("administrative", "individual"),
            "Linked Census, HES and Mortality Data": ("administrative", "individual"),
            "Earnings and Employees Study": ("survey", "individual"),
            "EOL": ("administrative", "individual"),
            "EOL Dataset (2015-2022)": ("administrative", "individual"),
            "Death Registrations": ("administrative", "individual"),
            "Birth Registrations in England and Wales": ("administrative", "individual"),
            "Decision Maker Panel": ("cohort", "business"),
            "Longitudinal Small Business Survey (LSBS)": ("cohort", "business"),
            "Business Enterprise Research and Development England": ("survey", "business"),
            "Products of the European Community": ("survey", "business"),
            "Annual Gas and Electricity Consumption at Meter Level": ("administrative", "area"),
            "Prices Survey Microdata": ("survey", "business"),
            "Bespoke Management and Expectations Survey": ("survey", "business"),
            "Over 50s Lifestyle Study": ("survey", "individual"),
            "Online Time Use Survey": ("survey", "individual"),
            "British Household Panel Survey": ("cohort", "household"),
            "Working Lives of Teachers and Leaders": ("cohort", "individual"),
            "Annual Outward Foreign Direct Investment Survey": ("survey", "business"),
            "Survey of Innovation and Patent Use": ("survey", "business"),
            "Longitudinal Business Structure Database": ("administrative", "business"),
            "Monthly Inquiry into the Distributive and Services Sector": ("survey", "business"),
            "Monthly Production Inquiry": ("survey", "business"),
            "Effects of Tax and Benefits": ("survey", "household"),
            "UK Gross Value Added": ("administrative", "area"),
            "Statutory Homelessness Flows England": ("administrative", "household"),
        }
        for dataset, (collection, unit) in cases.items():
            with self.subTest(dataset=dataset):
                record = lookup_dataset_record(dataset, self.indexes)
                self.assertIsNotNone(record)
                self.assertEqual(record["collection_type"], collection)
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


if __name__ == "__main__":
    unittest.main()
