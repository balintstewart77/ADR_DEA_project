"""Regression tests defending human-adjudicated reference decisions.

Every test here encodes a decision Balint adjudicated on the evidence (facet
audits, the linked-products review, the unclassified-dataset rulings, the
organisation sector sweep). These decisions are ground truth: code and other
tests conform to THEM, never the reverse.

If a test in this module fails, a deliberate decision has been undone — do NOT
"fix" the reference data to satisfy other tests or expectations. Investigate
which change reverted the adjudication and restore it (or get the adjudication
explicitly revisited by a human). This module exists because a stale test once
caused the 0.4.4 ASHE Longitudinal removal to be helpfully reverted.
"""

import unittest

from analysis.derive_register_properties import (
    REFERENCE_PATH,
    build_indexes,
    linkage_span_for_domains,
    load_reference,
    lookup_dataset_record,
    lookup_organisation_record,
    match_linked_products,
    project_linkage_span,
)


class AdjudicatedDecisionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference(REFERENCE_PATH)
        cls.indexes = build_indexes(cls.reference)
        cls.linked_products = {
            entry["canonical"]: entry
            for entry in cls.reference.get("linked_products", [])
        }
        cls.datasets = {
            entry["canonical"]: entry for entry in cls.reference.get("datasets", [])
        }

    def facets(self, canonical: str) -> tuple:
        record = self.datasets.get(canonical)
        self.assertIsNotNone(record, f"no dataset facet record for {canonical!r}")
        return (
            record["collection_method"],
            record["temporal_structure"],
            record["unit_of_observation"],
        )

    # 1. ASHE Longitudinal removal (human-adjudicated, linked-products review,
    # reference 0.4.4; re-applied at 0.4.7 — do not revert to satisfy other
    # tests; if this fails, a deliberate decision has been undone).
    def test_ashe_longitudinal_is_not_a_linked_product(self):
        # It is a longitudinally-weighted SINGLE dataset (its sole component is
        # itself), not a record linkage.
        self.assertNotIn(
            "Annual Survey of Hours and Earnings Longitudinal", self.linked_products
        )

    def test_ashe_longitudinal_keeps_its_dataset_facet_record(self):
        # The 0.4.4 removal was from linked_products only; the dataset facet
        # record stays (survey by employer-return design, longitudinal
        # construction applied, individual unit).
        self.assertEqual(
            self.facets("Annual Survey of Hours and Earnings Longitudinal"),
            ("survey", "longitudinal", "individual"),
        )

    # 2. The genuine ASHE linkages stay (same 0.4.4 review: these have real
    # second components, unlike the self-referential ASHE Longitudinal).
    def test_genuine_ashe_linkages_remain_linked_products(self):
        census = self.linked_products.get(
            "Annual Survey of Hours and Earnings linked to Census 2011"
        )
        self.assertIsNotNone(census)
        self.assertGreaterEqual(len(set(census["component_domains"])), 2)
        self.assertEqual(
            linkage_span_for_domains(census["component_domains"]),
            "Cross-domain record linkage",
        )
        self.assertIn(
            "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment",
            self.linked_products,
        )

    def test_ashe_longitudinal_mention_derives_no_record_linkage(self):
        # Adjudicated consequence of 1.: a register mention of ASHE Longitudinal
        # matches no linked product and must derive "No record linkage".
        domains: set = set()
        for product in match_linked_products(
            "Annual Survey of Hours and Earnings Longitudinal", self.indexes
        ):
            domains.update(product["component_domains"])
        self.assertEqual(linkage_span_for_domains(domains), "No record linkage")

    # 3. BSD temporal (facet audit, 0.4.2-0.4.3 era; human-adjudicated): base
    # BSD is released as annual point-in-time snapshots -> cross-sectional.
    def test_bsd_is_cross_sectional(self):
        record = self.datasets["Business Structure Database (BSD)"]
        self.assertEqual(record["temporal_structure"], "cross-sectional")
        self.assertTrue(record.get("temporal_source"), "adjudication source missing")

    # 4. CPI collection method (facet audit; human-adjudicated): price
    # quotes are collected by survey; the index is an aggregate output.
    def test_cpi_is_survey(self):
        record = self.datasets["Consumer Prices Index"]
        self.assertEqual(record["collection_method"], "survey")
        self.assertTrue(record.get("collection_method_source"), "adjudication source missing")

    # 5. ONS LS collection method (facet audit; human-adjudicated): Census-cored
    # linked-record dataset classified by primary content -> survey; the worked
    # edge case generalising this ruling must stay in the collection rule.
    def test_ons_ls_is_survey_with_worked_edge_case(self):
        record = self.datasets["ONS Longitudinal Study (LS)"]
        self.assertEqual(record["collection_method"], "survey")
        self.assertTrue(record.get("collection_method_source"), "adjudication source missing")
        edge_cases = self.reference["dataset_collection_method_rule"]["worked_edge_cases"]
        matches = [
            case for case in edge_cases
            if "ONS Longitudinal Study" in str(case) and "survey" in str(case)
        ]
        self.assertTrue(matches, "Census-based linked-record edge case missing")

    # 6. AD|ARC temporal (facet audit; human-adjudicated): single-period
    # collection -> cross-sectional.
    def test_adarc_is_cross_sectional(self):
        record = self.datasets["AD|ARC"]
        self.assertEqual(record["temporal_structure"], "cross-sectional")
        self.assertTrue(record.get("temporal_source"), "adjudication source missing")

    # 7. Facet-audit items #12/#13 (human-adjudicated): Census-cored linked
    # mortality products classify by primary content -> survey.
    def test_census_cored_linked_products_are_survey(self):
        for canonical in (
            "Linked Census, HES and Mortality Data",
            "Linked Census and Death Occurrences",
        ):
            with self.subTest(dataset=canonical):
                self.assertEqual(self.datasets[canonical]["collection_method"], "survey")

    # 8. EES 2011 NI temporal (facet audit; human-adjudicated, NISRA-sourced):
    # one-off 2011 linkage -> cross-sectional.
    def test_ees_2011_ni_is_cross_sectional(self):
        record = self.datasets["Earnings and Employees Study (EES) 2011 - Northern Ireland"]
        self.assertEqual(record["temporal_structure"], "cross-sectional")
        self.assertIn("nisra.gov.uk", str(record.get("temporal_source", "")))

    # 9. CIS unit (facet audit; PARKED pending discussion with Jo): individual
    # under the sampling-frame definition. The parked state is itself defended:
    # changing the unit without resolving/removing the flag must fail here.
    def test_cis_unit_is_individual_with_pending_flag(self):
        record = self.datasets["COVID-19"]
        self.assertEqual(record["unit_of_observation"], "individual")
        self.assertIn("pending discussion with Jo", str(record.get("notes", "")))

    # 10. Parked schema question on the collection-method rule (deliberately
    # unresolved; human-adjudicated to park, not drop).
    def test_collection_method_parked_schema_question_intact(self):
        question = self.reference["dataset_collection_method_rule"].get(
            "parked_schema_question"
        )
        self.assertTrue(question)
        self.assertIn("multi-valued", str(question))

    # 11. Unclassified-dataset rulings (0.4.5; human-adjudicated): aliases
    # resolve to existing canonicals rather than spawning new records.
    def test_unclassified_ruling_aliases_resolve(self):
        cases = {
            "Expenditure and Food Survey": "Living Costs and Food Survey (LCF)",
            "Innovation Panel": "Understanding Society",
            "Telephone-Operated Crime Survey for England and Wales":
                "Crime Survey for England and Wales (CSEW)",
        }
        for alias, canonical in cases.items():
            with self.subTest(alias=alias):
                record = lookup_dataset_record(alias, self.indexes)
                self.assertIsNotNone(record, f"{alias!r} resolves to nothing")
                self.assertEqual(record["canonical"], canonical)

    # 12. Unclassified-dataset rulings (0.4.5; human-adjudicated): fresh facet
    # records created with these values.
    def test_unclassified_ruling_fresh_records(self):
        cases = {
            "Children of the 2020s Longitudinal Study":
                ("survey", "longitudinal", "individual"),
            "International Passenger Survey":
                ("survey", "cross-sectional", "individual"),
            "The Second Longitudinal Study of Young People in England":
                ("survey", "longitudinal", "individual"),
            "Childcare and Early Years Survey of Parents":
                ("survey", "cross-sectional", "individual"),
        }
        for canonical, expected in cases.items():
            with self.subTest(dataset=canonical):
                self.assertEqual(self.facets(canonical), expected)

    # 13. Organisation sector sweep (human-adjudicated): SAIL Databank is
    # Swansea-hosted infrastructure -> academic, with the Swansea spelling an
    # alias of the same entity; international bodies -> government.
    def test_sail_databank_is_academic_with_alias(self):
        primary = lookup_organisation_record("SAIL Databank", self.indexes)
        aliased = lookup_organisation_record(
            "SAIL Databank, Swansea University", self.indexes
        )
        self.assertIsNotNone(primary)
        self.assertIsNotNone(aliased)
        self.assertEqual(primary["canonical"], aliased["canonical"])
        self.assertEqual(primary["sectors"], ["academic"])

    def test_international_bodies_are_government(self):
        for canonical in (
            "International Monetary Fund (IMF)",
            "OECD",
            "World Bank open data",
            "Federal Reserve Bank of Philadelphia",
            "Federal Reserve Board of Governors",
        ):
            with self.subTest(organisation=canonical):
                record = lookup_organisation_record(canonical, self.indexes)
                self.assertIsNotNone(record, f"{canonical!r} not found")
                self.assertEqual(record["sectors"], ["government"])

    # 15. June 2026 organisation rulings (human-adjudicated, reference 0.4.9):
    # Oxford Brookes academic (distinct from University of Oxford), Anna Freud
    # Centre third-sector (registered charity), Turkish education ministry
    # folded into government like IMF/OECD.
    def test_june_2026_organisation_rulings(self):
        cases = {
            "Oxford Brookes University": ["academic"],
            "Anna Freud Centre": ["third-sector"],
            "Ministry of National Education, Republic of Türkiye": ["government"],
        }
        for canonical, sectors in cases.items():
            with self.subTest(organisation=canonical):
                record = lookup_organisation_record(canonical, self.indexes)
                self.assertIsNotNone(record, f"{canonical!r} not found")
                self.assertEqual(record["sectors"], sectors)
        brookes = lookup_organisation_record("Oxford Brookes University", self.indexes)
        oxford = lookup_organisation_record("University of Oxford", self.indexes)
        self.assertNotEqual(brookes["canonical"], oxford["canonical"])
        # Dataset alias from the same ruling: the acronym-suffixed register
        # form inherits the existing Annual Business Inquiry facets.
        niabi = lookup_dataset_record(
            "Northern Ireland Annual Business Inquiry (NIABI)", self.indexes
        )
        self.assertIsNotNone(niabi)
        self.assertEqual(niabi["canonical"], "Annual Business Inquiry")
        self.assertEqual(
            (niabi["collection_method"], niabi["temporal_structure"],
             niabi["unit_of_observation"]),
            ("survey", "cross-sectional", "business"),
        )

    # 16. Known-unclassifiable residuals (human-adjudicated): person names and
    # unresolvable strings are honestly unclassified, never classified as
    # organisations; the list only suppresses them from the review queue.
    def test_known_unclassifiable_residuals(self):
        known = set(self.reference.get("known_unclassifiable_organisations") or [])
        self.assertLessEqual(
            {"Independent Researcher", "OREC", "Calver Pang"}, known
        )
        for name in known:
            with self.subTest(residual=name):
                self.assertIsNone(
                    lookup_organisation_record(name, self.indexes),
                    f"{name!r} must stay unclassified, not become an organisation",
                )

    # 14. Cross-domain redefinition (human-adjudicated; implemented at
    # reference 0.4.8): a project's span is the maximum of its individually
    # matched products' spans, never the union of domains across the project's
    # portfolio. Two single-domain products from different domains -> within-
    # domain; one multi-domain product -> cross-domain.
    def test_cross_domain_span_is_per_product(self):
        single_domain_spans = [
            linkage_span_for_domains(["Crime & Justice"]),
            linkage_span_for_domains(["Labour Market & Employment"]),
        ]
        self.assertEqual(
            project_linkage_span(single_domain_spans),
            "Within-domain record linkage",
        )
        multi_domain_span = linkage_span_for_domains(
            ["Education & Skills", "Health & Social Care"]
        )
        self.assertEqual(
            project_linkage_span([multi_domain_span]),
            "Cross-domain record linkage",
        )
        self.assertEqual(project_linkage_span([]), "No record linkage")

    # 9. Availability "available-by" rule (human-adjudicated, June 2026
    # availability-dates apply; review table:
    # analysis/outputs/linked_product_availability_review.csv). Availability is
    # the EARLIEST evidence-consistent date and first accredited use is a hard
    # upper bound on it: documented dates that postdate first register use
    # record something else (cataloguing/announcement) and were bounded to
    # first use instead. Any future availability_date later than observed
    # first use violates the adjudicated rule and must fail here.
    def test_availability_dates_never_postdate_first_register_use(self):
        from dashboard.data.uptake import (
            DF_PRODUCT_PROJECTS,
            LINKED_PRODUCTS,
            _availability_to_timestamp,
        )

        # Basis taxonomy refined at 0.5.1 (human-adjudicated, Balint/ex-ADR UK,
        # ECHILD correction): "documented" split into documented_accessible
        # (source evidences actual SRS/DEA access) and announced (source
        # evidences existence only; availability bounded by first use).
        valid_bases = {
            "documented_accessible",
            "announced",
            "bounded_by_first_use",
            "pre_register_window",
        }
        first_seen = DF_PRODUCT_PROJECTS.groupby("product")["quarter_date"].min()
        for product in LINKED_PRODUCTS:
            canonical = product["canonical"]
            with self.subTest(product=canonical):
                date = product["curated_date"]
                self.assertIsNotNone(
                    date, f"{canonical!r} has no parseable availability_date"
                )
                self.assertIn(
                    product["availability_basis"],
                    valid_bases,
                    f"{canonical!r} has invalid availability_basis",
                )
                seen = first_seen.get(canonical)
                if seen is None:
                    continue  # product never used in the register: no bound to check
                self.assertLessEqual(
                    date,
                    seen,
                    f"{canonical!r} availability_date {date.date()} postdates "
                    f"first register use {seen.date()} - violates the "
                    "adjudicated available-by rule",
                )
        # The rule's worked example: the WED announcement (2022-Q3) postdates
        # first register use of ASHE-Census 2011 (2020 Q2), so the recorded
        # availability is the first-use bound, not the announcement.
        by_canonical = {p["canonical"]: p for p in LINKED_PRODUCTS}
        ashe_census = by_canonical["Annual Survey of Hours and Earnings linked to Census 2011"]
        self.assertEqual(ashe_census["availability_basis"], "bounded_by_first_use")
        self.assertEqual(
            ashe_census["curated_date"], _availability_to_timestamp("2020-Q2")
        )
        # ECHILD correction (0.5.1, human domain knowledge): the 2021 IJE
        # publication is an ANNOUNCEMENT, not evidence of DEA/SRS access — a
        # governance dispute delayed DEA-route availability, so it is bounded
        # at first register use (2024 Q3) with the announcement kept apart.
        # Its 2021->2024 gap is a delivery/governance lag, never adoption lag.
        echild = by_canonical[
            "Education and Child Health Insights from Linked Data (ECHILD)"
        ]
        self.assertEqual(echild["availability_basis"], "announced")
        self.assertEqual(echild["curated_date"], _availability_to_timestamp("2024-Q3"))
        self.assertEqual(echild["announced_date"], _availability_to_timestamp("2021"))


if __name__ == "__main__":
    unittest.main()
