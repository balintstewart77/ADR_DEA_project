from __future__ import annotations

import unittest

import pandas as pd

from analysis.crossmodel_comparison import ComparisonError, build_comparison


def frames(fable_tags: list[str], gpt_tags: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    fable = pd.DataFrame({
        "Project ID": ["2025/001"], "Title": ["Synthetic"], "Record ID": ["2025/001"],
        "substantive_domains": ["Health & Social Care"], "analytical_purpose": ["Descriptive Monitoring"],
        "cross_cutting_tags": ["; ".join(fable_tags)], "rationale": ["r"],
    })
    gpt = pd.DataFrame({
        "Record ID": ["2025/001"], "gpt_status": ["ok"],
        "substantive_domains": ["Health & Social Care"], "analytical_purpose": ["Descriptive Monitoring"],
        "cross_cutting_tags": ["; ".join(gpt_tags)], "rationale": ["r"], "validation_error": [""],
    })
    return fable, gpt


class CrossmodelTagComparisonTests(unittest.TestCase):
    def compare(self, fable_tags: list[str], gpt_tags: list[str]) -> dict[str, object]:
        fable, gpt = frames(fable_tags, gpt_tags)
        comparison, _ = build_comparison(fable, gpt)
        return comparison.iloc[0].to_dict()

    def test_equity_absent_both_matches(self) -> None:
        self.assertTrue(self.compare([], [])["disparities_tag_match"])

    def test_equity_present_both_matches(self) -> None:
        label = "Demographic disparities / equity tag"
        self.assertTrue(self.compare([label], [label])["disparities_tag_match"])

    def test_fable_only_equity_mismatches(self) -> None:
        self.assertFalse(self.compare(["Demographic disparities / equity tag"], [])["disparities_tag_match"])

    def test_gpt_only_equity_mismatches(self) -> None:
        self.assertFalse(self.compare([], ["Demographic disparities / equity tag"])["disparities_tag_match"])

    def test_covid_and_equity_are_independent(self) -> None:
        row = self.compare(["COVID-19 & Pandemic"], ["COVID-19 & Pandemic", "Demographic disparities / equity tag"])
        self.assertTrue(row["covid_tag_match"])
        self.assertFalse(row["disparities_tag_match"])

    def test_equity_agreement_does_not_mask_covid_mismatch(self) -> None:
        row = self.compare(["Demographic disparities / equity tag"], ["COVID-19 & Pandemic", "Demographic disparities / equity tag"])
        self.assertFalse(row["covid_tag_match"])
        self.assertTrue(row["disparities_tag_match"])

    def test_joint_tag_match_is_conjunction_and_compatibility_field_matches(self) -> None:
        row = self.compare(["COVID-19 & Pandemic"], [])
        self.assertEqual(row["tag_set_match"], row["covid_tag_match"] and row["disparities_tag_match"])
        self.assertEqual(row["tag_set_match"], row["any_tag_set_match"])

    def test_historical_inequality_string_fails(self) -> None:
        with self.assertRaisesRegex(ComparisonError, "Unknown Fable tag"):
            self.compare(["Inequality"], [])

    def test_unknown_tag_fails(self) -> None:
        with self.assertRaisesRegex(ComparisonError, "Unknown GPT tag"):
            self.compare([], ["Unknown tag"])

    def test_aggregate_fixture_counts_tag_mismatches(self) -> None:
        fable = pd.concat([frames([], [])[0], frames(["COVID-19 & Pandemic"], [])[0], frames(["Demographic disparities / equity tag"], [])[0]], ignore_index=True)
        gpt = pd.concat([frames([], [])[1], frames([], [])[1], frames([], [])[1]], ignore_index=True)
        fable["Record ID"] = ["2025/001", "2025/002", "2025/003"]
        gpt["Record ID"] = ["2025/001", "2025/002", "2025/003"]
        comparison, _ = build_comparison(fable, gpt)
        self.assertEqual(int((~comparison["covid_tag_match"]).sum()), 1)
        self.assertEqual(int((~comparison["disparities_tag_match"]).sum()), 1)
        self.assertEqual(int((~comparison["tag_set_match"]).sum()), 2)

    def test_dirty_record_id_fails(self) -> None:
        fable, gpt = frames([], [])
        fable.loc[0, "Record ID"] = "2025/001\t"
        with self.assertRaisesRegex(ComparisonError, "non-canonical Record ID"):
            build_comparison(fable, gpt)


if __name__ == "__main__":
    unittest.main()
