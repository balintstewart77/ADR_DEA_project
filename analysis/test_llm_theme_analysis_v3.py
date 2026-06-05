import unittest

from analysis import llm_theme_analysis_v3 as classifier


class ProjectLayersRc2Test(unittest.TestCase):
    def test_schema_accepts_without_retired_linkage_field(self):
        parsed = classifier.ProjectLayers(
            project_id="2020/001",
            substantive_domains=["Education & Skills"],
            analytical_purpose=["Outcome Tracking"],
            cross_cutting_tags=[],
            rationale="Education outcomes are central; outcome tracking links education to later outcomes; no tag applies.",
        )

        self.assertEqual(parsed.project_id, "2020/001")
        retired_field = "linkage" + "_mode"
        self.assertFalse(hasattr(parsed, retired_field))

    def test_multi_tag_validation_preserves_covid_and_demographic_tags(self):
        tags = ["COVID-19 & Pandemic", "Demographic disparities / equity tag"]

        parsed = classifier.ProjectLayers(
            project_id="2021/018",
            substantive_domains=["Labour Market & Employment"],
            analytical_purpose=["Outcome Tracking"],
            cross_cutting_tags=tags,
            rationale="Labour-market outcomes are central; outcome tracking links pandemic exposure to work outcomes; both tags apply.",
        )

        self.assertEqual(parsed.cross_cutting_tags, tags)

    def test_covid_is_tag_not_domain(self):
        self.assertNotIn("COVID-19 & Pandemic", classifier.DOMAINS)
        self.assertIn("COVID-19 & Pandemic", classifier.CROSS_CUTTING_TAGS)

    def test_prompt_excludes_retired_linkage_and_places_covid_under_tags(self):
        prompt = classifier._build_static_prompt()

        retired_field = "linkage" + "_mode"
        retired_rule_key = "layer" + "_b_assignment_rule"
        self.assertNotIn(f'"{retired_field}"', prompt)
        self.assertNotIn("LAYER B", prompt)
        self.assertNotIn(retired_rule_key, prompt)
        self.assertNotIn("Single-Dataset", prompt)
        self.assertNotIn("Within-Domain Linkage", prompt)
        self.assertNotIn("Cross-Domain Linkage", prompt)

        tag_header_index = prompt.index("CROSS-CUTTING TAGS")
        covid_index = prompt.index("COVID-19 & Pandemic")
        self.assertGreater(covid_index, tag_header_index)


if __name__ == "__main__":
    unittest.main()
