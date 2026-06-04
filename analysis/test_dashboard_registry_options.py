import unittest

from dashboard.data.registry import _ALL_DATASET_OPTIONS, _ALL_PROVIDER_OPTIONS


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


if __name__ == "__main__":
    unittest.main()
