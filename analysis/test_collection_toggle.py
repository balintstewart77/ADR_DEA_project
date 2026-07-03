import unittest
from unittest.mock import patch

import pandas as pd

from dashboard.callbacks.datasets import build_dataset_demand_figures
from dashboard.data.collection_view import (
    collection_membership_reference_frame,
    display_entity_counts,
    with_collection_display,
)
from dashboard.data.loader import collection_labels_for_dataset
from dashboard.data.registry import df_datasets, df_flagship_projects, df_flagship_requests
from dashboard.data.uptake import adoption_curve_table


class CollectionToggleTest(unittest.TestCase):
    def test_collection_membership_is_derived_from_reference(self):
        membership = collection_membership_reference_frame()
        self.assertFalse(membership.empty)

        expected = {
            (row.member, row.collection)
            for row in membership.itertuples(index=False)
        }
        actual = {
            (row.member, label)
            for row in membership.itertuples(index=False)
            for label in collection_labels_for_dataset(row.member)
        }
        self.assertEqual(actual, expected)
        self.assertIn(("MoJ Data First Crown Court Defendant", "Data First"), actual)
        self.assertIn(
            (
                "Annual Survey of Hours and Earnings linked to Census 2011",
                "Wage and Employment Dynamics",
            ),
            actual,
        )

    def test_live_data_first_collection_count_is_project_deduped(self):
        grouped = with_collection_display(df_datasets, "grouped")
        counts = display_entity_counts(grouped).set_index("display_dataset")["Projects"]
        request_counts = df_flagship_requests.groupby("collection")["Project Row ID"].count()
        project_counts = df_flagship_projects.groupby("collection")["Project Row ID"].nunique()

        self.assertEqual(int(counts["Data First"]), 31)
        self.assertEqual(int(project_counts["Data First"]), 31)
        self.assertEqual(int(request_counts["Data First"]), 94)

    def test_grouped_collection_counts_dedupe_data_first_member_rows(self):
        rows = pd.DataFrame([
            {
                "Project ID": "P1",
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
                "provider": "Ministry of Justice (MoJ)",
                "dataset": "MoJ Data First Crown Court Defendant Case Level",
            },
            {
                "Project ID": "P1",
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
                "provider": "Ministry of Justice (MoJ)",
                "dataset": "MoJ Data First Prisoner Custodial Journey",
            },
            {
                "Project ID": "P2",
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
                "provider": "Ministry of Justice (MoJ)",
                "dataset": "MoJ Data First Probation",
            },
        ])
        counts = display_entity_counts(with_collection_display(rows, "grouped"))
        by_label = counts.set_index("display_dataset")["Projects"].to_dict()
        self.assertEqual(by_label["Data First"], 2)

    def test_grouped_collection_counts_dedupe_wed_member_rows(self):
        rows = pd.DataFrame([
            {
                "Project ID": "P1",
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
                "provider": "Office for National Statistics (ONS)",
                "dataset": "Annual Survey of Hours and Earnings linked to Census 2011",
            },
            {
                "Project ID": "P1",
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
                "provider": "Office for National Statistics (ONS)",
                "dataset": "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment",
            },
            {
                "Project ID": "P2",
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
                "provider": "Office for National Statistics (ONS)",
                "dataset": "Annual Survey of Hours and Earnings linked to Census 2011",
            },
        ])
        counts = display_entity_counts(with_collection_display(rows, "grouped"))
        by_label = counts.set_index("display_dataset")["Projects"].to_dict()
        self.assertEqual(by_label["Wage and Employment Dynamics"], 2)

    def test_dataset_demand_toggle_figures_keep_explicit_heights(self):
        for collection_view in ("grouped", "individual"):
            with self.subTest(collection_view=collection_view):
                top, trend, provider = build_dataset_demand_figures(
                    10,
                    None,
                    "ALL",
                    "count",
                    collection_view,
                )
                self.assertEqual(top.to_plotly_json()["layout"]["height"], 400)
                self.assertEqual(trend.to_plotly_json()["layout"]["height"], 400)
                self.assertGreaterEqual(provider.to_plotly_json()["layout"]["height"], 420)

    def _registered_callback_map(self):
        from dash import Dash

        from dashboard.callbacks import datasets as datasets_cb
        from dashboard.callbacks import uptake as uptake_cb

        app = Dash(__name__)
        datasets_cb.register(app)
        uptake_cb.register(app)
        return app.callback_map

    def test_collection_toggle_input_only_wires_linked_data_uptake(self):
        toggle = "datasets-collection-display-mode"
        uptake_output_ids = {
            "uptake-adoption-curves",
            "uptake-exposure-rate-bar",
            "uptake-adoption-summary-table",
        }
        top_demand_output_ids = {
            "datasets-topn-chart",
            "datasets-trend-chart",
            "datasets-provider-chart",
        }

        keys_with_toggle = [
            key
            for key, spec in self._registered_callback_map().items()
            if any(inp["id"] == toggle for inp in spec["inputs"])
        ]

        self.assertTrue(keys_with_toggle, "toggle must still drive a callback")
        for key in keys_with_toggle:
            self.assertTrue(
                any(out in key for out in uptake_output_ids),
                f"toggle drives non-uptake outputs: {key}",
            )
            self.assertFalse(
                any(out in key for out in top_demand_output_ids),
                f"toggle must not drive top-of-section demand: {key}",
            )

    def test_top_demand_callback_renders_individual_regardless_of_toggle(self):
        callback_map = self._registered_callback_map()
        key = next(k for k in callback_map if "datasets-topn-chart" in k)
        spec = callback_map[key]

        input_ids = {inp["id"] for inp in spec["inputs"]}
        self.assertNotIn("datasets-collection-display-mode", input_ids)

        outputs_list = [
            {"id": "datasets-topn-chart", "property": "figure"},
            {"id": "datasets-trend-chart", "property": "figure"},
            {"id": "datasets-provider-chart", "property": "figure"},
        ]
        with patch(
            "dashboard.callbacks.datasets.build_dataset_demand_figures",
            return_value=("top", "trend", "provider"),
        ) as mocked:
            spec["callback"](10, None, "ALL", "count", outputs_list=outputs_list)

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(mocked.call_args.args[-1], "individual")

    def test_uptake_grouped_wed_curve_dedupes_project_with_two_member_products(self):
        products = [
            "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment",
        ]
        synthetic = pd.DataFrame([
            {
                "project_key": "P1",
                "product": products[0],
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
            },
            {
                "project_key": "P1",
                "product": products[1],
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
            },
            {
                "project_key": "P2",
                "product": products[0],
                "Year": 2024,
                "quarter_date": pd.Timestamp("2024-01-01"),
            },
        ])
        with patch("dashboard.data.uptake.DF_PRODUCT_PROJECTS", synthetic), \
             patch("dashboard.data.uptake._register_years", [2024]), \
             patch("dashboard.data.uptake._total_by_year", pd.Series({2024: 2})):
            curve = adoption_curve_table(
                "year",
                selected_products=products,
                collection_view="grouped",
            )

        wed_2024 = curve[
            (curve["line_label"] == "Wage and Employment Dynamics")
            & (curve["Year"] == 2024)
        ]
        self.assertEqual(int(wed_2024["count"].iloc[0]), 2)


if __name__ == "__main__":
    unittest.main()
