import os
import sys
import unittest

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dataset_normalisation import (  # noqa: E402
    dataset_family_for,
    describe_dataset_normalisation,
    iter_dataset_entries,
    parse_datasets,
    normalise_dataset_name,
    normalise_provider_name,
)


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
            "Births registrations": "Birth Registrations in England and Wales",
            "2022 Census": "Census 2022",
            "Absences and English School Census": "English School Census Absences",
            "Northern Ireland School Census": "Northern Ireland School Census",
            "Business Structure Database": "Business Structure Database (BSD)",
            "Business Structure Database (BSD)": "Business Structure Database (BSD)",
            "ASHE": "Annual Survey of Hours and Earnings (ASHE)",
            "Annual Survey of Hours": "Annual Survey of Hours and Earnings (ASHE)",
            "Annual Business Survey": "Annual Business Survey (ABS)",
            "Annual Population Survey": "Annual Population Survey (APS)",
            'Annual Population Survey " APS Persons': "Annual Population Survey Persons",
            "Business Enterprise Research and Development": "Business Enterprise Research and Development (BERD)",
            "Business Insights and Conditions Survey": "Business Insights and Conditions Survey (BICS)",
            "Business Register and Employment Survey": "Business Register and Employment Survey (BRES)",
            "Crime Survey for England and Wales": "Crime Survey for England and Wales (CSEW)",
            "COVID-19 Infection Survey": "COVID-19 Infection Survey (CIS)",
            "COVID-19 Schools Infection Survey linked to Test and Trace": "COVID-19 Infection Survey linked to NHS Test and Trace",
            "Inter-Departmental Business Register": "Inter-Departmental Business Register (IDBR)",
            "Labour Force Survey": "Labour Force Survey (LFS)",
            "Living Costs and Food Survey": "Living Costs and Food Survey (LCF)",
            "Longitudinal Education Outcomes": "Longitudinal Education Outcomes (LEO)",
            "Longitudinal Education": "Longitudinal Education Outcomes (LEO)",
            "Longitudinal Small Business Survey": "Longitudinal Small Business Survey (LSBS)",
            "Management and Expectations Survey": "Management and Expectations Survey (MES)",
            "New Earnings Survey": "New Earnings Survey (NES)",
            "ONS Longitudinal Study": "ONS Longitudinal Study (LS)",
            "Longitudinal Study": "ONS Longitudinal Study (LS)",
            "Longitudinal Study of England and Wales": "ONS Longitudinal Study (LS)",
            "Longitudinal Study 1971": "ONS Longitudinal Study 1971",
            "Opinions and Lifestyle Survey": "Opinions and Lifestyle Survey (OPN)",
            "UK Innovation Survey": "UK Innovation Survey (UKIS)",
            "Universities and Colleges Admissions Service": "Universities and Colleges Admissions Service (UCAS)",
            "Wealth and Assets Survey": "Wealth and Assets Survey (WAS)",
            "Workplace Employment Relations Study": "Workplace Employment Relations Study (WERS)",
            "GRading and Admissions Data England": "GRading and Admissions Data England (GRADE)",
            "Interdepartmental Business Register": "Inter-Departmental Business Register (IDBR)",
            "Registered Deaths": "Death Registrations",
            'Community Innovation Survey " United Kingdom Innovation Survey': "Community Innovation Survey",
            "Growing Up in England Wave 1": "Growing Up in England Wave 1 (GUIE)",
            "Growing Up in England Wave 2": "Growing Up in England Wave 2 (GUIE)",
            "Growing Up in England Wave 2 - Children in Need": "Growing Up in England Wave 2 (GUIE)",
            "ASHE Longitudinal": "Annual Survey of Hours and Earnings Longitudinal",
            "ASHE Longitudinal Data England": "Annual Survey of Hours and Earnings Longitudinal",
            "ASHE Longitudinal Data England and Wales": "Annual Survey of Hours and Earnings Longitudinal",
            "ASHE Longitudinal Data Great Britain England": "Annual Survey of Hours and Earnings Longitudinal",
            "Annual Survey of Hours and Earnings Longitudinal": "Annual Survey of Hours and Earnings Longitudinal",
            "Annual Survey of Hours and Earnings linked to 2011 Census": "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings Census 2011 Linked": "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings linked to 2011 Census England and Wales": "Annual Survey of Hours and Earnings linked to Census 2011 England and Wales",
            "Annual Survey for Hours and Earnings / Census 2011 Linked Datase": "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment": "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment",
            "2011 Census linked to Benefits and Income": "Census 2011 linked to Benefits and Income",
            "Linked NI Census-ASHE": "Northern Ireland Census linked to ASHE",
            "Nursing and Midwifery Council Register - UK linked to Census 2021": "Nursing and Midwifery Council Register linked to Census 2021",
            "Census 2011 and 2021 England and Wales": "Census 2011 and Census 2021 England and Wales",
            "Census 2011 100% Household and Individual - England an": "Census 2011 Household and Individual England and Wales",
            "Integrated Census Microdata University of Leicester: Digital library of historical directories datasets World Bank open data: Urban Population Database": "Integrated Census Microdata",
            "Census data 1981": "Census 1981",
            "Census microdata 9% sample": "Census Microdata 9% Sample",
            "Education and Child Health Insights from Linked": "Education and Child Health Insights from Linked Data (ECHILD)",
            "Education and Child Health Insights from Linked Data": "Education and Child Health Insights from Linked Data (ECHILD)",
            "Education and Child Health Insights from Linked Data Research Data": "Education and Child Health Insights from Linked Data (ECHILD)",
            "Education and Child Health Insights from Linked Data Research Database": "Education and Child Health Insights from Linked Data (ECHILD)",
            "Agricultural Research Collection": "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "Administrative Data | Agricultural Research Collection": "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "Administrative Data | Agriculture Research Collection": "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "AD|ARC Phase 2 - Census 21 unlinked": "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "MoJ Data First Cross-Justice System Linking Dataset England And Wales": "MoJ Data First Cross-Justice System Linking Dataset",
            "MoJ Data First Cross-Justice System Linking": "MoJ Data First Cross-Justice System Linking Dataset",
            "Capital Stock": "Capital Stock Dataset",
            "Linked Trade-in-Goods/IDBR dataset": "Linked Trade-in-Goods/IDBR",
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

    def test_provider_is_carried_across_wrapped_lines(self):
        raw = (
            "Office for National Statistics: Annual Population Survey Person, Annual Population Survey Household,\n"
            "Occupational differences in mortality from COVID-19,\n"
            "Annual Survey of Hours and Earnings, Labour Force Survey Household"
        )
        entries = [(provider, part) for _, provider, part in iter_dataset_entries(raw)]
        self.assertEqual(
            entries,
            [
                ("Office for National Statistics", "Annual Population Survey Person"),
                ("Office for National Statistics", "Annual Population Survey Household"),
                ("Office for National Statistics", "Occupational differences in mortality from COVID-19"),
                ("Office for National Statistics", "Annual Survey of Hours and Earnings"),
                ("Office for National Statistics", "Labour Force Survey Household"),
            ],
        )

    def test_semicolon_compound_is_split(self):
        raw = (
            "MoJ Data First: "
            "Crown Court Defendant Case Level Dataset; "
            "Magistrates' Court Defendant Case Level"
        )
        parts = [part for _, _, part in iter_dataset_entries(raw)]
        self.assertEqual(
            parts,
            [
                "Crown Court Defendant Case Level Dataset",
                "Magistrates' Court Defendant Case Level",
            ],
        )

    def test_junk_fragments_are_suppressed(self):
        raw = (
            "Office for National Statistics: Office for National, England and Wales, Great Britain, "
            "Household, Trace, Death, Labour Force, Business Structure, Business Register, Research and, Development, "
            "Economy Survey, Employment Survey, Food Survey, occurrences, and Earnings, structure for, "
            "Producer Price Index (PPI, Annual Population Survey &amp, Ofqual/DfE/, University of Oxford, "
            "Patents, Children Looked After, Waves 1-18, Waves 1-5, Data given for all available years unless otherwise stated, Designs and Trade Marks, Prisons, and Harmonised BHPS, and Probation, "
            "Waves 1-10 and Harmonised BHPS: Waves 1-18, Waves 1-13, Waves 1-14, Waves 1-27, Waves 1-9, all future releases, impacts on Great Britain, pension funds and trusts, udinal Busin ess Database, "
            "Household Sample, Infection Survey, Prisons and Probation, Prisons and Probation - England and Wales, Living Costs and Food, Consumer Prices, Offending, Offending data, Department for Environment, Rounds 5-7, Wales: Household Sample, Pay As You Earn Real Time Information in the, Pay As You Earn Real Time Information in the UK, Business Structure Database in the, Business Structure Database in the UK"
        )
        parts = [part for _, _, part in iter_dataset_entries(raw)]
        self.assertEqual(parts, [])

    def test_ambiguous_cases_remain_distinct(self):
        cases = {
            "Infant Mortality linkage of 2011 Census": "Infant Mortality linkage of 2011 Census",
            "Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO); Magistrates Court (MACO); Crown Court (CRCO); Prisoner Custodial Journey Dataset (PRIS); MOJDF cross justice linking (Cross-Justice System Linking dataset) and MAGS CROWN JOURNEY": "Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO); Magistrates Court (MACO); Crown Court (CRCO); Prisoner Custodial Journey Dataset (PRIS); MOJDF cross justice linking (Cross-Justice System Linking dataset) and MAGS CROWN JOURNEY",
            "Annual Survey for Hours and Earnings / Census linked": "Annual Survey of Hours and Earnings linked to Census 2011",
            "2022 Census": "Census 2022",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalise_dataset_name(raw), expected)

    def test_normalisation_metadata(self):
        alias_meta = describe_dataset_normalisation("ASHE")
        self.assertEqual(alias_meta["canonical_dataset_name"], "Annual Survey of Hours and Earnings (ASHE)")
        self.assertEqual(alias_meta["match_type"], "alias")
        self.assertEqual(alias_meta["needs_review"], 0)

        renamed_meta = describe_dataset_normalisation("2022 Census")
        self.assertEqual(renamed_meta["canonical_dataset_name"], "Census 2022")
        self.assertEqual(renamed_meta["needs_review"], 0)

        compound_census = "Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO); Magistrates Court (MACO); Crown Court (CRCO); Prisoner Custodial Journey Dataset (PRIS); MOJDF cross justice linking (Cross-Justice System Linking dataset) and MAGS CROWN JOURNEY"
        compound_meta = describe_dataset_normalisation(compound_census)
        self.assertEqual(compound_meta["match_type"], "compound_or_multi_dataset")
        self.assertEqual(compound_meta["needs_review"], 1)
        self.assertIn("Census 2011 (CENW); Census 2021 (CENS)", compound_meta["canonical_dataset_name"])

        compound_df = "MoJ Data First Crown court defendant case level dataset; MoJ Data First magistrates court defendant case level dataset"
        compound_df_meta = describe_dataset_normalisation(compound_df)
        self.assertEqual(compound_df_meta["match_type"], "compound_or_multi_dataset")
        self.assertEqual(compound_df_meta["needs_review"], 1)

        escaped_compounds = [
            "Quarterly Labour Force Survey Economic and Social Research Council: Integrated Census Microdata",
            "Business Structure Database - UK DBT: Longitudinal Small Business Survey",
            "E-Commerce and Digital Economy Survey - UK Department For Education: Employer Skills Survey and Investment in Training",
            "Bespoke Equalities Data Asset: Companies House - Census 2011",
        ]
        for raw in escaped_compounds:
            meta = describe_dataset_normalisation(raw)
            self.assertEqual(meta["match_type"], "compound_or_multi_dataset")
            self.assertEqual(meta["needs_review"], 1)

    def test_dataset_family_mapping(self):
        self.assertEqual(dataset_family_for("Census 2021"), "Census")
        self.assertEqual(dataset_family_for("Census 2021 Household Secure Microdata Sample England and Wales"), "Census")
        self.assertEqual(dataset_family_for("English School Census Absences"), "School Census")
        self.assertEqual(dataset_family_for("Annual Business Survey (ABS)"), "ABS")
        self.assertEqual(dataset_family_for("Annual Business Survey - UK 2008 - 2021"), "ABS")
        self.assertEqual(dataset_family_for("Annual Business Survey 1973 onwards)"), "ABS")
        self.assertEqual(dataset_family_for("Annual Business Survey 2005-2022"), "ABS")
        self.assertEqual(dataset_family_for("Annual Business Survey Household"), "ABS")
        self.assertEqual(dataset_family_for("Annual Business Survey in Great Britain"), "ABS")
        self.assertEqual(dataset_family_for("Annual Population Survey (APS)"), "APS")
        self.assertEqual(dataset_family_for("Annual Population Survey Household"), "APS")
        self.assertEqual(dataset_family_for("Annual Population Survey Longitudinal"), "APS")
        self.assertEqual(dataset_family_for("Annual Population Survey Person"), "APS")
        self.assertEqual(dataset_family_for("Annual Population Survey: Well-Being"), "APS")
        self.assertEqual(dataset_family_for("Annual Population Survey 2004-2022"), "APS")
        self.assertEqual(dataset_family_for("COVID-19 Infection Survey linked to NHS Test and Trace"), "COVID-19")
        self.assertEqual(dataset_family_for("COVID-19 Infection Survey linked to Combined Vaccination"), "COVID-19")
        self.assertEqual(dataset_family_for("COVID-19 Infection Survey linked to VOA and EPC"), "COVID-19")
        self.assertEqual(dataset_family_for("COVID-19 Infection Survey (CIS)"), "COVID-19")

    def test_provider_normalisation(self):
        cases = {
            "DfE": "Department for Education",
            "Department For Education": "Department for Education",
            "DfT": "Department for Transport",
            "MOJ": "Ministry of Justice",
            "Office For National Statistics": "Office for National Statistics",
            "Office for national Statistics": "Office for National Statistics",
            "Office of National Statistics": "Office for National Statistics",
            "Offcie for National Statistics": "Office for National Statistics",
            "Department for Business, Energy & Industrial Strategy": "Department for Business, Energy and Industrial Strategy",
            "Institute for Social and Economic Research": "Institute for Economic and Social Research",
            "University and Colleges Admission Service": "Universities and Colleges Admissions Service (UCAS)",
            "UCAS": "Universities and Colleges Admissions Service (UCAS)",
            "NISRA": "Northern Ireland Statistics and Research Agency (NISRA)",
            "Northern Ireland Statistics and Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
            "Northern Ireland Statitiscs and Research Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
            "Northern Ireland Statistics and Reserach Agency": "Northern Ireland Statistics and Research Agency (NISRA)",
            "SAIL Databank Databank": "SAIL Databank",
            "NHSD": "NHS Digital",
            "NMC": "Nursing and Midwifery Council",
            "Intellectual Property Office - UK DBT": "Intellectual Property Office",
            "HMRC": "HM Revenue and Customs",
            "UKHSA": "UK Health Security Agency",
            "Ofqual": "Office of Qualifications and Examinations Regulation (Ofqual)",
            "": "Unknown / Unspecified",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalise_provider_name(raw), expected)

    def test_secure_research_service_fallback_provider(self):
        parsed = parse_datasets(
            pd.DataFrame(
                [
                    {
                        "Project ID": "2022/156",
                        "Year": 2022,
                        "quarter_date": pd.Timestamp("2022-10-01"),
                        "Datasets Used": "Northern Ireland Annual Business Inquiry , Broad Economy Sales and Exports Statistics",
                        "Secure Research Service": "Northern Ireland Statistics and Research Agency",
                    }
                ]
            )
        )
        self.assertEqual(
            parsed["provider"].tolist(),
            [
                "Northern Ireland Statistics and Research Agency (NISRA)",
                "Northern Ireland Statistics and Research Agency (NISRA)",
            ],
        )
        self.assertEqual(dataset_family_for("COVID-19 Weekly Opinions Survey"), "COVID-19")
        self.assertEqual(dataset_family_for("Census 2011 England and Wales Household Structure for COVID-19 Models"), "COVID-19")
        self.assertEqual(dataset_family_for("Labour Force Survey"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Labour Force Survey Person"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Labour Force Survey Household"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Labour Force Survey Longitudinal"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Labour Force Survey Five-Quarter Longitudinal"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Labour Force Survey Two-Quarter Longitudinal"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Quarterly Labour Force Survey"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Quarterly Labour Force Survey Household"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Longitudinal Labour Force Survey"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Labour Force Survey Indexed"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("2020 Wave 1 Labour Force Survey"), "Labour Force Survey")
        self.assertEqual(dataset_family_for("Linked Census and Death Occurrences"), "Census")
        self.assertEqual(dataset_family_for("Growing Up in England Wave 1 (GUIE)"), "GUIE")
        self.assertEqual(dataset_family_for("Growing Up in England Wave 2 (GUIE)"), "GUIE")
        self.assertEqual(dataset_family_for("Growing Up in England Wave 2 - Exclusions"), "GUIE")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment"), "ASHE")
        self.assertEqual(dataset_family_for("Administrative Data | Agricultural Research Collection (AD|ARC)"), "AD|ARC")
        self.assertEqual(dataset_family_for("Bespoke Admin Data - Agricultural Research Collection Phase 1"), "AD|ARC")
        self.assertEqual(dataset_family_for("Bespoke Admin Data: Agricultural Research Collection"), "AD|ARC")
        self.assertEqual(dataset_family_for("RETIRED MoJ Data First Magistrates Court Defendant"), "Data First")
        self.assertEqual(dataset_family_for("Annual Survey for Hours and Earnings / Census linked"), "ASHE")
        self.assertEqual(dataset_family_for("Annual Survey for Hours and Earnings Longitudinal"), "ASHE")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings (1997-2024)"), "ASHE")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings 1997-2023"), "ASHE")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings 1997-2024"), "ASHE")
        self.assertEqual(dataset_family_for("Death Registrations in England and Wales"), "Death Registrations")
        self.assertEqual(dataset_family_for("Death registrations in England and Wales indexed"), "Death Registrations")
        self.assertEqual(dataset_family_for("ONS Death Registrations"), "Death Registrations")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings linked to Census 2011"), "ASHE-linked")
        self.assertEqual(dataset_family_for("Annual Survey of Hours and Earnings (ASHE)"), "ASHE")
        self.assertIsNone(dataset_family_for("Census 2011 (CENW); Census 2021 (CENS) Ministry of Justice; Family Court (FACO)"))
        self.assertEqual(dataset_family_for("MoJ Data First Crown Court Defendant Case Level Dataset; Moj Data First Magistrates' Court Defendant Case Level Dataset"), "Data First")


if __name__ == "__main__":
    unittest.main()
