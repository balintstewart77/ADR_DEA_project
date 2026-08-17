import unittest

from analysis.register_manifest import CURRENT_POINTER, load_manifest, snapshot_record
from dashboard.data.registry import (
    _ALL_DATASET_OPTIONS,
    _ALL_PROVIDER_OPTIONS,
    _ALL_TRE_OPTIONS,
    df_all,
    df_flagship_projects,
    source_file,
)


class DashboardRegistryOptionTest(unittest.TestCase):
    def test_dataset_filter_options_do_not_include_collection_shortcuts(self):
        values = [option["value"] for option in _ALL_DATASET_OPTIONS]

        self.assertFalse(
            [value for value in values if str(value).startswith("collection::")]
        )
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(
            values.count("Education and Child Health Insights from Linked Data (ECHILD)"),
            1,
        )
        self.assertNotIn("collection::ECHILD", values)

    def test_data_first_collection_uses_deterministic_reference(self):
        counts = (
            df_flagship_projects
            .groupby("collection")["Project Row ID"]
            .nunique()
            .to_dict()
        )

        self.assertEqual(counts.get("Data First"), 31)

    def test_provider_filter_expands_selected_department_acronyms(self):
        values = [option["value"] for option in _ALL_PROVIDER_OPTIONS]

        expected_values = {
            "Department for Business and Trade (DBT)",
            "Department for Levelling Up, Housing and Communities (DLUHC)",
            "Department for Transport (DfT)",
            "Department for Work and Pensions (DWP)",
        }
        self.assertTrue(expected_values.issubset(set(values)))
        for acronym in ("DBT", "DLUHC", "DfT", "DWP"):
            self.assertNotIn(acronym, values)

    def test_processing_environment_options_are_canonicalised(self):
        # This test intentionally describes the mutable operational register.
        # Derive its category/count contract from the current cleaned snapshot
        # that produced the dashboard data, so legitimate category additions
        # are represented automatically.
        expected_counts = (
            df_all.assign(
                _processing_environment=(
                    df_all["Secure Research Service"].astype("string").str.strip()
                )
            )
            .dropna(subset=["_processing_environment"])
            .query("_processing_environment != ''")
            ["_processing_environment"]
            .value_counts()
            .to_dict()
        )
        values = [option["value"] for option in _ALL_TRE_OPTIONS]
        labels_by_value = {option["value"]: option["label"] for option in _ALL_TRE_OPTIONS}

        current_snapshot = snapshot_record(load_manifest(), CURRENT_POINTER)
        self.assertEqual(source_file, current_snapshot["canonical_csv_path"])
        self.assertEqual(set(values) - {"ALL"}, set(expected_counts))
        for value, count in expected_counts.items():
            with self.subTest(processing_environment=value):
                self.assertIn(f"({count} projects)", labels_by_value[value])

        raw_aliases = {
            "Office for National Statistics Secure Research Service",
            "ONS SRS",
            "SRS",
            "Northern Ireland Statistics and Research Agency",
            "NISRA",
            "SAIL",
            "UK Data Service",
            "UKDS",
            "Integrated Data Service",
        }
        self.assertFalse(raw_aliases & set(values))

        counts = df_all["Secure Research Service"].value_counts().to_dict()
        for value, count in expected_counts.items():
            with self.subTest(live_count=value):
                self.assertEqual(counts.get(value), count)


if __name__ == "__main__":
    unittest.main()
