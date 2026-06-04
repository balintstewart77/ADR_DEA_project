import os
import sys
import unittest

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from institution_normalisation import (  # noqa: E402
    describe_institution_normalisation,
    institution_sector_for,
    parse_institutions,
    parse_institutions_with_metadata,
)


class InstitutionNormalisationTest(unittest.TestCase):
    def parse(self, researchers: str) -> list[str]:
        df = pd.DataFrame([
            {"Project ID": "P1", "Year": 2024, "Researchers": researchers},
        ])
        parsed = parse_institutions(df)
        return parsed["institution"].tolist()

    def test_agri_food_variants_are_canonicalised(self):
        institutions = self.parse(
            "Paul Caskie, Agri-Food Biosciences Institute\n"
            "Erica Chisholm, Agri-Food & Biosciences Institute\n"
            "Paul Wilson, University of Nottingham\n"
            "Paul Caskie, Agri-Food Bioscience Institute, Sian Morrison-Rees"
        )
        self.assertEqual(
            institutions,
            [
                "Agri-Food and Biosciences Institute",
                "University of Nottingham",
            ],
        )

    def test_multi_comma_institutions_are_preserved(self):
        institutions = self.parse(
            "Arnaud Chevalier, Royal Holloway, University of London\n"
            "Neil Scott, University of London - Royal Holloway"
        )
        self.assertEqual(institutions, ["Royal Holloway, University of London"])

    def test_department_names_with_commas_are_preserved(self):
        institutions = self.parse(
            "Peter Goodridge, Department for Business, Energy and Industrial Strategy\n"
            "Oliver Wright, Department for Business, Inovation and Skills - Enterprise Directorate"
        )
        self.assertEqual(
            institutions,
            [
                "Department for Business, Energy and Industrial Strategy",
                "Department for Business, Innovation and Skills",
            ],
        )

    def test_split_name_tokens_do_not_pollute_institutions(self):
        institutions = self.parse(
            "Marco Manacorda, Queen Mary University of London\n"
            "Andrea, Giglio, Queen Mary University of London\n"
            "Josh Dixon, Administrative Data Research, Wales\n"
            "Ian Farr, SAIL Databank Databank, Swansea University"
        )
        self.assertEqual(
            institutions,
            [
                "Queen Mary University of London",
                "Administrative Data Research Wales",
                "SAIL Databank, Swansea University",
            ],
        )

    def test_school_aliases_roll_up_to_parent_institution(self):
        institutions = self.parse(
            "Suzanna Nesom, Cardiff Business School\n"
            "Melanie Jones, Cardiff University\n"
            "Serra-Sastre Victoria, City, University of London\n"
            "Helene Turon, City University"
        )
        self.assertEqual(
            institutions,
            [
                "Cardiff University",
                "City, University of London",
            ],
        )

    def test_spacing_separated_researchers_are_split(self):
        institutions = self.parse(
            "David Bateman, Alma Economics                                "
            "Suzie Harrison, Alma Economics                                       "
            "Lawrence Newland, Alma Economics"
        )
        self.assertEqual(institutions, ["Alma Economics"])

    def test_company_suffix_breaks_glued_researcher_name(self):
        institutions = self.parse(
            "Alexander Katz, Frontier Economics Ltd "
            "Margheritaserena Ferrara, Frontier Economics Ltd"
        )
        self.assertEqual(institutions, ["Frontier Economics Ltd"])

    def test_wrapped_researcher_names_do_not_pollute_institutions(self):
        institutions = self.parse(
            "Gemma Catney, Queen's University Belfast\n"
            "David \n"
            "Manley, University of Bristol\n"
            "Gemma \n"
            "Catney,\n"
            "Queen's University \n"
            "Belfast\n"
            "Momoko \n"
            "Nishikido,\n"
            "Queen's University \n"
            "Belfast\n"
            "Stephen \n"
            "Jivraj, University College \n"
            "London"
        )
        self.assertEqual(
            institutions,
            [
                "Queen's University Belfast",
                "University of Bristol",
                "University College London",
            ],
        )

    def test_wrapped_middle_names_do_not_pollute_institutions(self):
        institutions = self.parse(
            "Anne Berrington, University of Southampton\n"
            "Vincent \n"
            "Jerald \n"
            "Ramos, University of \n"
            "Southampt\n"
            "on"
        )
        self.assertEqual(institutions, ["University of Southampton"])

    def test_institution_only_lines_do_not_absorb_next_researcher(self):
        institutions = self.parse(
            "Christian Stow,\n"
            "IPSOS MORI\n"
            "Jan Franke,\n"
            "IPSOS MORI\n"
            "Scott Carter,\n"
            "IPSOS MORI"
        )
        self.assertEqual(institutions, ["Ipsos"])

    def test_continuation_lines_are_joined_into_institution_names(self):
        institutions = self.parse(
            "Manpreet Khera,\nDepartment for\nInternational Trade\n"
            "Robert Cruikshanks, Education\nPolicy Institute\n"
            "Claire Crawford, UCL Institute of Education"
        )
        self.assertEqual(
            institutions,
            [
                "Department for International Trade",
                "Education Policy Institute",
                "UCL Institute of Education",
            ],
        )

    def test_missing_comma_before_institution_is_recovered(self):
        institutions = self.parse(
            "Elaine Drayton, Institute for Fiscal Studies\n"
            "Christine Farquharson Institute for\nFiscal Studies,\n"
            "Tom Waters, Institute for Fiscal Studies"
        )
        self.assertEqual(institutions, ["Institute for Fiscal Studies"])

    def test_obvious_alias_variants_are_rolled_up(self):
        institutions = self.parse(
            "Jake Finney, PWC LLP\n"
            "Siobhan Prendiville, PricewaterhouseCoopers LLP\n"
            "Scott Carter, Ipsos MORI\n"
            "Jake Finney, IPSOS UK\n"
            "Jo Blanden, Institute of Education\n"
            "Neil Scott, City University London\n"
            "Analyst One, Cambridge university"
        )
        self.assertEqual(
            institutions,
            [
                "PwC LLP",
                "Ipsos",
                "UCL Institute of Education",
                "City, University of London",
                "University of Cambridge",
            ],
        )

    def test_known_compound_labels_are_split(self):
        institutions = self.parse(
            "Analyst One, Health Foundation/ Academy of Medical Sciences\n"
            "Analyst Two, London School of Economics; and University College London"
        )
        self.assertEqual(
            institutions,
            [
                "Health Foundation",
                "Academy of Medical Sciences",
                "London School of Economics and Political Science (LSE)",
                "University College London",
            ],
        )

    def test_requested_institution_aliases_are_canonicalised(self):
        institutions = self.parse(
            "Jane Smith, ADS Group Limited\n"
            "John Doe, Belmana Ltd\n"
            "Jane Smith, CEBR\n"
            "John Doe, Centre for Economic and Business Research Ltd (CBER)\n"
            "Jane Smith, CEDAR\n"
            "John Doe, Department of Health\n"
            "Jane Smith, Department of Health - NI\n"
            "John Doe, ECIBT\n"
            "Jane Smith, EHRC\n"
            "John Doe, Equality and Human Rights Commission\n"
            "Jane Smith, ESRI\n"
            "John Doe, Greater London Authority\n"
            "Jane Smith, Health Data Research UK\n"
            "John Doe, HM Revenue and Customs\n"
            "Jane Smith, Henley Business School\n"
            "John Doe, INSEAD\n"
            "Jane Smith, Institute for Social and Economic Research\n"
            "John Doe, Institute for Social and Economic Research, University of Essex\n"
            "Jane Smith, Learning and Work\n"
            "John Doe, London Metropolitan, University\n"
            "Jane Smith, London School of Economics\n"
            "John Doe, M&G\n"
            "Jane Smith, NFER\n"
            "John Doe, National Foundation for Education Research"
        )
        self.assertEqual(
            institutions,
            [
                "ADS (Aerospace, Defence, Security, Space) Group Limited",
                "Belmana",
                "Centre for Economic and Business Research (CEBR)",
                "Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR)",
                "Department of Health and Social Care (DHSC)",
                "Department of Health (Northern Ireland)",
                "Engineering Construction Industry Training Board (ECITB)",
                "Equality and Human Rights Commission (EHRC)",
                "Economic and Social Research Institute (ESRI)",
                "Greater London Authority (GLA)",
                "Health Data Research UK (HDR UK)",
                "HM Revenue and Customs (HMRC)",
                "Henley Business School (University of Reading)",
                "Institut Européen d'Administration des Affaires (INSEAD)",
                "Institute for Social and Economic Research (University of Essex)",
                "Learning and Work Institute",
                "London Metropolitan University",
                "London School of Economics and Political Science (LSE)",
                "Municipal & General (M&G)",
                "National Foundation for Education Research (NFER)",
            ],
        )

    def test_person_and_placeholder_fragments_are_dropped(self):
        institutions = self.parse(
            "Jane Smith, Cristina Sechel\n"
            "John Doe, Independent Research"
        )
        self.assertEqual(institutions, [])

    def test_real_johannes_kepler_affiliations_are_preserved(self):
        institutions = self.parse(
            "Daniel Schaefer,\n"
            "Johannes Kepler University\n"
            "John Doe, Johannes Kepler, University"
        )
        self.assertEqual(institutions, ["Johannes Kepler University Linz"])

    def test_empty_canonical_aliases_do_not_prefix_delete_universities(self):
        for institution in [
            "University of Derby",
            "University College London",
            "University of Suffolk",
        ]:
            with self.subTest(institution=institution):
                description = describe_institution_normalisation(institution)
                self.assertNotEqual(description["institution"], "")
                self.assertEqual(description["institution"], institution)

        self.assertEqual(
            describe_institution_normalisation("University")["institution"],
            "",
        )

    def test_embedded_researcher_names_after_known_institutions_are_removed(self):
        institutions = self.parse(
            "John Doe, EHRC Angela Kubi, EHRC, EHRC Arturo Lonighi, EHRC Sian Hughes\n"
            "Jane Smith, NFER Gemma Schwendel, NFER\n"
            "Jane Smith, King's College London Dimitris Vallis, King's College London\n"
            "John Doe, London School of Hygiene and Tropical Medicine Rochelle Schneider dos"
        )
        self.assertEqual(
            institutions,
            [
                "Equality and Human Rights Commission (EHRC)",
                "National Foundation for Education Research (NFER)",
                "King's College London",
                "London School of Hygiene and Tropical Medicine",
            ],
        )

    def test_typo_aliases_are_canonicalised(self):
        institutions = self.parse(
            "Jane Smith, Equality and Human Rights Comission\n"
            "John Doe, Institue for Employment Studies\n"
            "Jane Smith, Sentencing Acadamey\n"
            "John Doe, Teeside University\n"
            "Jane Smith, London School of Economics and Polictical Science"
        )
        self.assertEqual(
            institutions,
            [
                "Equality and Human Rights Commission (EHRC)",
                "Institute for Employment Studies",
                "Sentencing Academy",
                "Teesside University",
                "London School of Economics and Political Science (LSE)",
            ],
        )

    def test_university_display_names_are_standardised(self):
        institutions = self.parse(
            "Jane Smith, University of Aston\n"
            "John Doe, Oxford University\n"
            "Jane Smith, Bath University\n"
            "John Doe, University of Swansea\n"
            "Jane Smith, Durham University\n"
            "John Doe, University of Loughborough"
        )
        self.assertEqual(
            institutions,
            [
                "Aston University",
                "University of Oxford",
                "University of Bath",
                "Swansea University",
                "Durham University",
                "Loughborough University",
            ],
        )

    def test_subunit_rollups_to_parent_institutions(self):
        institutions = self.parse(
            "Jane Smith, Bayes Business School\n"
            "John Doe, UCL Institute of Health Informatics\n"
            "Jane Smith, University of Cambridge - Department of Land Economy\n"
            "John Doe, Centre for Economic Performance, London School of Economics\n"
            "Jane Smith, Warwick Economics and Development"
        )
        self.assertEqual(
            institutions,
            [
                "City, University of London",
                "University College London",
                "University of Cambridge",
                "London School of Economics and Political Science (LSE)",
                "University of Warwick",
            ],
        )

    def test_explicit_person_name_contamination_aliases(self):
        institutions = self.parse(
            "Jane Smith, King's College London Dimitris Vallis, King's College London Julia Ellingwood, King's College London\n"
            "John Doe, University of Leeds Jose Pina-Sánchez, University of Leeds"
        )
        self.assertEqual(
            institutions,
            [
                "King's College London",
                "University of Leeds",
            ],
        )

    def test_ambiguous_campus_names_are_not_specialised(self):
        institutions = self.parse(
            "Jane Smith, University of Texas\n"
            "John Doe, University of California"
        )
        self.assertEqual(
            institutions,
            [
                "University of Texas",
                "University of California",
            ],
        )

    def test_additional_compound_strings_split_to_expected_institutions(self):
        institutions = self.parse(
            "Jane Smith, Imperial College Business School/London School of Economics\n"
            "John Doe, Health Foundation / Academy of Medical Sciences\n"
            "Jane Smith, University of Warwick / London School of Economics"
        )
        self.assertEqual(
            institutions,
            [
                "Imperial College London",
                "London School of Economics and Political Science (LSE)",
                "Health Foundation",
                "Academy of Medical Sciences",
                "University of Warwick",
            ],
        )

    def test_sector_and_metadata_helpers_preserve_existing_parse_output(self):
        df = pd.DataFrame([
            {
                "Project ID": "P1",
                "Year": 2024,
                "Researchers": "Jane Smith, AQA Education\nJohn Doe, University of Texas",
            },
        ])
        parsed = parse_institutions(df)
        self.assertEqual(parsed.columns.tolist(), ["Project ID", "Year", "institution"])

        metadata = parse_institutions_with_metadata(df)
        self.assertEqual(
            metadata[["institution", "institution_sector", "match_status"]].values.tolist(),
            [
                ["AQA Education", "commercial", "alias"],
                ["University of Texas", "academic", "alias"],
            ],
        )
        self.assertEqual(institution_sector_for("AQA Education"), "commercial")
        self.assertEqual(institution_sector_for("Unknown Organisation"), "unclassified")
        self.assertEqual(
            describe_institution_normalisation("Cristina Sechel"),
            {
                "raw_institution": "Cristina Sechel",
                "institution": "",
                "institution_sector": "unclassified",
                "match_status": "empty",
                "needs_review": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
