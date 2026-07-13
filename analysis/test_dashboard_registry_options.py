import unittest

from dashboard.data.registry import (
    _ALL_DATASET_OPTIONS,
    _ALL_PROVIDER_OPTIONS,
    _ALL_TRE_OPTIONS,
    df_all,
    df_flagship_projects,
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
        expected_counts = {
            "ONS Secure Research Service (SRS)": 1011,
            "Northern Ireland Statistics and Research Agency (NISRA)": 22,
            "SAIL Databank": 77,
            "UK Data Service (UKDS)": 184,
            "Integrated Data Service (IDS)": 13,
        }
        values = [option["value"] for option in _ALL_TRE_OPTIONS]
        labels_by_value = {option["value"]: option["label"] for option in _ALL_TRE_OPTIONS}

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
