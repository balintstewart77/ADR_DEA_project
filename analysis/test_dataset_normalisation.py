import os
import sys
import unittest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dataset_normalisation import dataset_family_for, describe_dataset_normalisation, iter_dataset_entries, normalise_dataset_name  # noqa: E402


class DatasetNormalisationTest(unittest.TestCase):
    def test_manual_aliases(self):
        cases = {
            "2011 Census": "Census 2011",
            "2011 Census Data": "Census 2011",
            "2011 Census Data Welsh": "Census Wales 2011",
            "2011 Census Data Welsh residents": "Census Wales 2011",
            "Welsh Census 2011": "Census Wales 2011",
            "Census 2011 Welsh Records": "Census Wales 2011",
            "Census 2011 Welsh Residents": "Census Wales 2011",
            "Census 2011 Household": "Census 2011 Household",
            "Census 2011: Household": "Census 2011 Household",
            "Census 2011: Household Sample": "Census 2011 Household Sample",
            "Secure Census 2011 England and Wales: Household Sample": "Census 2011 Household Sample England and Wales",
            "Household Sample Scottish Government: Secure Census 2011 Scotland": "Census 2011 Household Sample Scotland",
            "Census 2011 Individual England and Wales": "Census 2011 Individual England and Wales",
            "Census 2011 Individual Northern Ireland": "Census 2011 Individual Northern Ireland",
            "Census 2011 Individual Scotland": "Census 2011 Individual Scotland",
            "Census 2011 Individual Secure Sample in England and Wales": "Census 2011 Individual Secure Sample England and Wales",
            "Census 2011 England and Wales: Individual Sample": "Census 2011 Individual Sample England and Wales",
            "Secure Census 2011 Origin / Destination": "Census 2011 Origin-Destination",
            "Census 2011 Origin / Destination": "Census 2011 Origin-Destination",
            "Census 2011 Origin-Destination": "Census 2011 Origin-Destination",
            "Census 2011 Origin/Destination: Flow": "Census 2011 Origin-Destination Flow",
            "2011 Census: Aggregate": "Census 2011 Aggregate",
            "2011 Census Ethnicity": "Census 2011 Ethnicity",
            "Census 2011 England": "Census 2011 England",
            "Census 2011 NI": "Census 2011 Northern Ireland",
            "Secure Census 2011 England": "Census 2011 England",
            "Census 2011 E&W Household structure for COVID-19 models": "Census 2011 England and Wales Household Structure for COVID-19 Models",
            "Census 2011 England and Wales Household structure for COVID-19 models": "Census 2011 England and Wales Household Structure for COVID-19 Models",
            "2021 Census": "Census 2021",
            "2021 (Welsh residents)": "Census Wales 2021",
            "2021 Census Data Welsh Residents": "Census Wales 2021",
            "Census 2021 Welsh Records": "Census Wales 2021",
            "Census 2021 England and Wales": "Census 2021 England and Wales",
            "2021 Census Data Welsh Household": "Census Wales 2021 Household",
            "Indexed Census 2021": "Census 2021 Indexed",
            "Census 2021 10% sample": "Census 2021 10% Sample",
            "Census 2021 Comprehensive Microdata (C21CM)": "Census 2021 Comprehensive Microdata",
            "Census 21 Comprehensive Microdata": "Census 2021 Comprehensive Microdata",
            "Census 2021 Household Secure Microdata Sample": "Census 2021 Household Secure Microdata Sample",
            "Census 2021 Household Secure Microdata Sample in England and Wales": "Census 2021 Household Secure Microdata Sample England and Wales",
            "Census 2021 Secure Origin Destination Tables for England and Wales": "Census 2021 Origin-Destination Tables England and Wales",
            "Census Non Response Link Study 2021 England and Wales": "Census 2021 Non-Response Link Study England and Wales",
            "Census Non Response Link Study 2021 England and Wales indexed": "Census 2021 Non-Response Link Study England and Wales Indexed",
            "Northern Ireland Census 2021 Census Microdata": "Northern Ireland Census 2021 Microdata",
            "2001 Census": "Census 2001",
            "2001 Census: Household Sample of Anonymised": "Census 2001 Household",
            "2001 Census: Household Sample of Anonymised Records": "Census 2001 Household",
            "Census 2001 Household for the": "Census 2001 Household",
            "Access Microdata Samples": "Census 2001 Individual",
            "Census 2001 Controlled": "Census 2001 Individual",
            "Absences and English School Census": "English School Census Absences",
            "Northern Ireland School Census": "Northern Ireland School Census",
            "Business Structure Database (BSD)": "Business Structure Database",
            "ASHE": "Annual Survey of Hours and Earnings",
            "Annual Survey of Hours": "Annual Survey of Hours and Earnings",
            "ASHE Longitudinal": "ASHE Longitudinal",
            "ASHE Longitudinal Data England": "ASHE Longitudinal",
            "ASHE Longitudinal Data England and Wales": "ASHE Longitudinal",
            "ASHE Longitudinal Data Great Britain England": "ASHE Longitudinal",
            "Annual Survey of Hours and Earnings Longitudinal": "ASHE Longitudinal",
            "Annual Survey of Hours and Earnings linked to 2011 Census": "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings Census 2011 Linked": "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings linked to 2011 Census England and Wales": "Annual Survey of Hours and Earnings linked to Census 2011 England and Wales",
            "Annual Survey for Hours and Earnings / Census 2011 Linked Datase": "Annual Survey of Hours and Earnings linked to Census 2011",
            "2011 Census linked to Benefits and Income": "Census 2011 linked to Benefits and Income",
            "Linked NI Census-ASHE": "Northern Ireland Census linked to ASHE",
            "Nursing and Midwifery Council Register - UK linked to Census 2021": "Nursing and Midwifery Council Register linked to Census 2021",
            "Census 2011 and 2021 England and Wales": "Census 2011 and Census 2021 England and Wales",
            "Census 2011 100% Household and Individual - England an": "Census 2011 Household and Individual England and Wales",
            "Integrated Census Microdata University of Leicester: Digital library of historical directories datasets World Bank open data: Urban Population Database": "Integrated Census Microdata",
            "Census data 1981": "Census 1981",
            "Census microdata 9% sample": "Census Microdata 9% Sample",
            "Agricultural Research Collection": "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "Administrative Data | Agricultural Research Collection": "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "AD|ARC Phase 2 - Census 21 unlinked": "Administrative Data | Agricultural Research Collection (AD|ARC)",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalise_dataset_name(raw), expected)

    def test_fragment_is_dropped(self):
        raw = (
            "Office for National Statistics, HM Revenue & Customs: "
            ": Census 2021 attributes - England and Wales with Geography, "
            "Indexed Census 2021"
        )
        parts = [part for _, _, part in iter_dataset_entries(raw)]
        self.assertNotIn("Census 2021 attributes - England and Wales with Geography", parts)
        self.assertEqual(parts, ["Indexed Census 2021"])

    def test_ambiguous_cases_remain_distinct(self):
        cases = {
            "Infant Mortality linkage of 2011 Census": "Infant Mortality linkage of 2011 Census",
            "Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO); Magistrates Court (MACO); Crown Court (CRCO); Prisoner Custodial Journey Dataset (PRIS); MOJDF cross justice linking (Cross-Justice System Linking dataset) and MAGS CROWN JOURNEY": "Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO); Magistrates Court (MACO); Crown Court (CRCO); Prisoner Custodial Journey Dataset (PRIS); MOJDF cross justice linking (Cross-Justice System Linking dataset) and MAGS CROWN JOURNEY",
            "Annual Survey for Hours and Earnings / Census linked": "Annual Survey for Hours and Earnings / Census linked",
            "2022 Census": "2022 Census",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalise_dataset_name(raw), expected)

    def test_normalisation_metadata(self):
        alias_meta = describe_dataset_normalisation("ASHE")
        self.assertEqual(alias_meta["canonical_dataset_name"], "Annual Survey of Hours and Earnings")
        self.assertEqual(alias_meta["match_type"], "alias")
        self.assertEqual(alias_meta["needs_review"], 0)

        unresolved_meta = describe_dataset_normalisation("2022 Census")
        self.assertEqual(unresolved_meta["canonical_dataset_name"], "2022 Census")
        self.assertEqual(unresolved_meta["needs_review"], 1)

        compound_census = "Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO); Magistrates Court (MACO); Crown Court (CRCO); Prisoner Custodial Journey Dataset (PRIS); MOJDF cross justice linking (Cross-Justice System Linking dataset) and MAGS CROWN JOURNEY"
        compound_meta = describe_dataset_normalisation(compound_census)
        self.assertEqual(compound_meta["match_type"], "compound_or_multi_dataset")
        self.assertEqual(compound_meta["needs_review"], 1)
        self.assertIn("Census 2011 (CENW); Census 2021 (CENS)", compound_meta["canonical_dataset_name"])

        compound_df = "MoJ Data First Crown court defendant case level dataset; MoJ Data First magistrates court defendant case level dataset"
        compound_df_meta = describe_dataset_normalisation(compound_df)
        self.assertEqual(compound_df_meta["match_type"], "compound_or_multi_dataset")
        self.assertEqual(compound_df_meta["needs_review"], 1)

    def test_dataset_family_mapping(self):
        self.assertEqual(dataset_family_for("Census 2021"), "Census")
        self.assertEqual(dataset_family_for("Census 2021 Household Secure Microdata Sample England and Wales"), "Census")
        self.assertEqual(dataset_family_for("English School Census Absences"), "School Census")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings linked to Census 2011"), "ASHE-linked")
        self.assertEqual(dataset_family_for("ASHE Longitudinal"), "ASHE")
        self.assertIsNone(dataset_family_for("Linked Census and Death Occurrences"))
        self.assertIsNone(dataset_family_for("Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO)"))
        self.assertEqual(dataset_family_for("MoJ Data First Crown Court Defendant Case Level Dataset; Moj Data First Magistrates' Court Defendant Case Level Dataset"), "Data First")


if __name__ == "__main__":
    unittest.main()
