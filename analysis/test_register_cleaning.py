import tempfile
import unittest

from analysis.register_cleaning import clean_register_dataframe, load_raw_register


class RegisterCleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        raw, _source_file = load_raw_register()
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
        self.assertEqual(len(self.df), 1272)

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


if __name__ == "__main__":
    unittest.main()
