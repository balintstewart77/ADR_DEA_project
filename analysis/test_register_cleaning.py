import tempfile
import unittest

from analysis.register_cleaning import (
    apply_reviewed_duplicate_rulings,
    clean_register_dataframe,
    load_duplicate_rulings,
    load_raw_register,
    normalise_register_columns,
    filter_dea_projects,
    apply_duplicate_policy,
)


class RegisterCleaningTests(unittest.TestCase):
    # Pinned to the 2026-03-25 register: these are fixture-based regression
    # tests for the duplicate policy, so they must not float with the
    # manifest's current version.
    REGISTER_VERSION = "20260325"

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        raw, _source_file = load_raw_register(version=cls.REGISTER_VERSION)
        cls.df, cls.stats = clean_register_dataframe(raw, output_dir=cls._tmp.name, verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_duplicate_policy_counts(self):
        self.assertEqual(self.stats["raw_loaded"], 1413)
        self.assertEqual(self.stats["rows_after_dea_filter"], 1307)
        self.assertEqual(self.stats["duplicate_tier1_rows_removed"], 23)
        self.assertEqual(self.stats["duplicate_tier2_merge_groups"], 12)
        self.assertEqual(self.stats["duplicate_tier2_input_rows"], 24)
        self.assertEqual(self.stats["duplicate_tier3_rows_flagged"], 0)
        self.assertEqual(self.stats["rows_after_duplicate_policy"], 1272)
        self.assertEqual(self.stats["rows_after_duplicate_rulings"], 1271)
        self.assertEqual(self.stats["duplicate_ruling_groups_applied"], 5)
        self.assertEqual(self.stats["duplicate_ruling_rows_removed"], 1)
        self.assertEqual(len(self.df), 1271)

    def test_2023_113_survives(self):
        rows = self.df[self.df["Project ID"].astype(str).eq("2023/113")]
        self.assertEqual(len(rows), 1)

    def test_2021_178_dataset_fragments_are_merged(self):
        row = self.df[self.df["Project ID"].astype(str).eq("2021/178")].iloc[0]
        datasets = row["Datasets Used"]
        self.assertIn("Annual Population Survey", datasets)
        self.assertIn("Understanding Society", datasets)
        self.assertIn("BHPS", datasets)
        self.assertIn("Workplace Employee Relations Survey", datasets)

    def test_2023_193_clerical_duplicate_collapses(self):
        rows = self.df[self.df["Project ID"].astype(str).eq("2023/193")]
        self.assertEqual(len(rows), 1)

    def test_same_title_different_ids_are_retained(self):
        rows = self.df[self.df["Title"].astype(str).str.strip().eq("Incentives for Innovation")]
        self.assertEqual(set(rows["Project ID"].astype(str)), {"2020/029", "2023/151"})

    def test_same_id_different_titles_get_record_suffixes(self):
        rows = self.df[self.df["Project ID"].astype(str).eq("2020/030")]
        self.assertEqual(set(rows["Record ID"].astype(str)), {"2020/030/a", "2020/030/b"})

    def test_2023_211_duplicate_update_collapses(self):
        rows = self.df[self.df["Project ID"].astype(str).eq("2023/211")]
        self.assertEqual(len(rows), 1)
        row = rows.iloc[0]
        self.assertEqual(row["Record ID"], "2023/211")
        self.assertEqual(row["Title"], "ESCoE: Local Consumption and National Sustainable Well-being")
        self.assertIn("Peter Levell, Institute for Fiscal Studies", row["Researchers"])
        self.assertIn("Martin Weale, King's College London", row["Researchers"])
        self.assertIn("Martin Weale, University of London - Kings College", row["Researchers"])
        self.assertIn("Lars Nesheim, University College London", row["Researchers"])
        self.assertIn("Gautam Vyas, Institute for Fiscal Studies", row["Researchers"])
        self.assertIn("Annual Population Survey", row["Datasets Used"])
        self.assertIn("Living Costs and Food Survey", row["Datasets Used"])
        self.assertIn("Understanding Society", row["Datasets Used"])
        self.assertNotIn("2023/211/a", set(self.df["Record ID"].astype(str)))
        self.assertNotIn("2023/211/b", set(self.df["Record ID"].astype(str)))

    def test_reviewed_collision_mappings_match_ruling_file(self):
        rulings = load_duplicate_rulings()
        for project_id in ("2020/030", "2022/036", "2024/095"):
            rows = self.df[self.df["Project ID"].astype(str).eq(project_id)]
            self.assertEqual(len(rows), 2)
            actual = dict(zip(rows["Title"], rows["Record ID"]))
            expected = {
                entry["title"]: entry["record_id"]
                for entry in rulings[project_id]["entries"]
            }
            self.assertEqual(actual, expected)

    def test_2024_014_related_distinct_entry_mapping(self):
        rulings = load_duplicate_rulings()
        self.assertEqual(
            rulings["2024/014"]["ruling_type"],
            "related_distinct_entries_same_project_id",
        )
        rows = self.df[self.df["Project ID"].astype(str).eq("2024/014")]
        self.assertEqual(len(rows), 2)
        actual = dict(zip(rows["Title"], rows["Record ID"]))
        expected = {
            entry["title"]: entry["record_id"]
            for entry in rulings["2024/014"]["entries"]
        }
        self.assertEqual(actual, expected)

    def test_record_ids_are_unique(self):
        self.assertFalse(self.df["Record ID"].isna().any())
        self.assertFalse(self.df["Record ID"].duplicated().any())

    def test_shuffled_source_preserves_record_ids(self):
        raw, _source_file = load_raw_register(version=self.REGISTER_VERSION)
        shuffled = raw.sample(frac=1, random_state=42).reset_index(drop=True)
        with tempfile.TemporaryDirectory() as tmp:
            shuffled_df, _stats = clean_register_dataframe(shuffled, output_dir=tmp, verbose=False)
        base_map = dict(zip(self.df["Record ID"], self.df["Title"]))
        shuffled_map = dict(zip(shuffled_df["Record ID"], shuffled_df["Title"]))
        self.assertEqual(base_map, shuffled_map)

    def test_reviewed_rulings_cover_all_residual_duplicate_ids(self):
        raw, _source_file = load_raw_register(version=self.REGISTER_VERSION)
        filtered = filter_dea_projects(normalise_register_columns(raw), {})
        exact_result = apply_duplicate_policy(filtered, verbose=False)
        with tempfile.TemporaryDirectory() as tmp:
            result = apply_reviewed_duplicate_rulings(
                exact_result.dataframe,
                audit_file=f"{tmp}/duplicate_rulings_audit.csv",
            )
        residual = sorted(
            result.dataframe.loc[
                result.dataframe["Project ID"].astype(str).duplicated(keep=False),
                "Project ID",
            ].astype(str).unique()
        )
        self.assertEqual(residual, ["2020/030", "2022/036", "2024/014", "2024/095"])


class CurrentRegisterCleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        raw, _source_file = load_raw_register(version="current")
        cls.df, cls.stats = clean_register_dataframe(raw, output_dir=cls._tmp.name, verbose=False)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_current_register_revised_counts(self):
        self.assertEqual(len(self.df), 1308)
        self.assertEqual(self.df["Project ID"].nunique(), 1304)
        self.assertEqual(self.df["Record ID"].nunique(), 1308)
        repeated = self.df["Project ID"].value_counts()
        self.assertEqual(len(repeated[repeated.eq(2)]), 4)
        self.assertTrue((repeated <= 2).all())
        self.assertEqual(self.stats["rows_after_duplicate_policy"], 1309)
        self.assertEqual(self.stats["rows_after_duplicate_rulings"], 1308)

    def test_current_record_ids_are_clean_and_collision_free(self):
        record_ids = self.df["Record ID"].astype("string")
        self.assertFalse(record_ids.isna().any())
        self.assertTrue(record_ids.map(lambda value: isinstance(value, str)).all())
        self.assertTrue(record_ids.eq(record_ids.str.strip()).all())
        self.assertFalse(
            record_ids.str.contains(r"[\x00-\x1f\x7f\u00a0]", regex=True).any()
        )
        self.assertFalse(record_ids.duplicated().any())
        self.assertFalse(record_ids.str.strip().duplicated().any())

    def test_escaped_carriage_return_artifacts_are_removed(self):
        text_values = self.df.select_dtypes(include=["object"]).fillna("").astype(str)
        combined = "\n".join(text_values.stack().tolist())
        self.assertNotIn("_x000D_", combined)
        self.assertNotIn("\r", combined)

        row = self.df[self.df["Project ID"].astype(str).eq("2026/002")].iloc[0]
        researchers = row["Researchers"]
        self.assertIn("Hannah Slevin, University of Manchester", researchers)
        self.assertIn("Katie Harron, University College London", researchers)
        self.assertNotIn("_x000D_", researchers)


if __name__ == "__main__":
    unittest.main()
