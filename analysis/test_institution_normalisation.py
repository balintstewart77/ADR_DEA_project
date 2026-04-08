import os
import sys
import unittest

import pandas as pd


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from institution_normalisation import parse_institutions  # noqa: E402


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
                "IPSOS MORI",
                "Ipsos UK",
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
                "London School of Economics",
                "University College London",
            ],
        )


if __name__ == "__main__":
    unittest.main()
