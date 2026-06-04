import unittest

from dashboard.data.registry import _ALL_DATASET_OPTIONS


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


if __name__ == "__main__":
    unittest.main()
