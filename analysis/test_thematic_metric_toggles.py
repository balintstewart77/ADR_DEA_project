import json
import unittest

import pandas as pd
from dash import dcc
from plotly.utils import PlotlyJSONEncoder

from dashboard.charts.thematic import (
    make_cross_heatmap,
    make_domain_cooccurrence,
    make_domain_record_linkage_breakdown,
    make_latent_demand_cooccurrence,
    make_record_linkage_trend,
    make_tag_domain_bar,
    make_thematic_trend,
)
from dashboard.charts.uptake import make_adoption_curves
from dashboard.config import DOMAIN_COLOURS, PURPOSE_COLOURS, TAG_COLOURS
from dashboard.data import thematic as thematic_data
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.uptake import (
    ALL_PRODUCT_SELECTION,
    FLAGSHIP_PRODUCTS,
    OTHER_LINKED_DATASETS_LABEL,
    OTHER_PRODUCTS,
    SERVED_DOMAIN_PAIRS,
    adoption_curve_table,
)


def _metric_col(metric: str) -> str:
    return "pct_of_projects" if metric == "pct" else "count"


EXPECTED_TOGGLE_GRAPH_HEIGHTS = {
    "thematic-domain-trend": 480,
    "thematic-purpose-trend": 400,
    "thematic-cross-domain-purpose": 560,
    "thematic-domain-cooccurrence": 724,
    "thematic-tag-trend": 400,
    "thematic-covid-tag-domain": 440,
    "thematic-demographic-tag-domain": 440,
    "deterministic-record-linkage-trend": 360,
    "deterministic-domain-linkage-breakdown": 560,
    "deterministic-collection-method-trend": 400,
    "deterministic-temporal-structure-trend": 400,
    "deterministic-unit-trend": 400,
    "thematic-latent-demand": 724,
    "uptake-adoption-curves": 460,
    "uptake-exposure-rate-bar": 520,
}


def _walk_components(component):
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for child in children:
            if child is not None:
                yield from _walk_components(child)
    else:
        yield from _walk_components(children)


class ThematicMetricToggleRegressionTest(unittest.TestCase):
    """Defend against the second recurrence of the G9 metric-toggle coupling bug."""

    def _assert_serialises(self, figure, expected_height: int | None = None):
        payload = figure.to_plotly_json()
        json.dumps(payload, cls=PlotlyJSONEncoder)
        self.assertIn("data", payload)
        self.assertIn("layout", payload)
        # Collapse-on-re-render regression: callback liveness and figure
        # serialisation are not enough. Re-rendered figures must keep an
        # explicit layout height so Plotly never returns a heightless sliver.
        height = payload["layout"].get("height")
        self.assertIsInstance(height, int)
        self.assertGreater(height, 0)
        if expected_height is not None:
            self.assertEqual(height, expected_height)

    def test_every_thematic_metric_figure_renders_in_both_metric_states(self):
        cases = [
            (
                "thematic-domain-trend",
                lambda metric: make_thematic_trend(
                    thematic_data.df_thematic_a,
                    "domain",
                    DOMAIN_COLOURS,
                    _metric_col(metric),
                    "Substantive Domains Over Time",
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "thematic-purpose-trend",
                lambda metric: make_thematic_trend(
                    thematic_data.df_thematic_c,
                    "purpose",
                    PURPOSE_COLOURS,
                    _metric_col(metric),
                    "Analytical Purpose Over Time",
                    height=400,
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "thematic-cross-domain-purpose",
                lambda metric: make_cross_heatmap(
                    thematic_data.df_cross_domain_purpose,
                    "domain",
                    "Substantive Domain x Analytical Purpose",
                    height=560,
                    metric=metric,
                ),
            ),
            (
                "thematic-tag-trend",
                lambda metric: make_thematic_trend(
                    thematic_data.df_thematic_tag_by_year,
                    "tag",
                    TAG_COLOURS,
                    _metric_col(metric),
                    "Cross-Cutting Tags Over Time",
                    height=400,
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "thematic-domain-cooccurrence",
                lambda metric: make_domain_cooccurrence(
                    thematic_data.df_domain_cooccurrence,
                    metric=metric,
                ),
            ),
            (
                "thematic-latent-demand",
                lambda metric: make_latent_demand_cooccurrence(
                    thematic_data.df_latent_demand_cooccurrence,
                    SERVED_DOMAIN_PAIRS,
                    metric=metric,
                ),
            ),
            (
                "thematic-covid-tag-domain",
                lambda metric: make_tag_domain_bar(
                    thematic_data.df_thematic_covid_tag_by_domain,
                    DOMAIN_COLOURS,
                    "COVID-19 & Pandemic by domain",
                    metric=metric,
                ),
            ),
            (
                "thematic-demographic-tag-domain",
                lambda metric: make_tag_domain_bar(
                    thematic_data.df_thematic_demographic_tag_by_domain,
                    DOMAIN_COLOURS,
                    "Demographic disparities by domain",
                    metric=metric,
                ),
            ),
            (
                "deterministic-record-linkage-trend",
                lambda metric: make_record_linkage_trend(
                    thematic_data.df_record_linkage_by_year,
                    metric=metric,
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "deterministic-domain-linkage-breakdown",
                lambda metric: make_domain_record_linkage_breakdown(
                    thematic_data.df_domain_record_linkage,
                    metric=metric,
                ),
            ),
            (
                "deterministic-collection-method-trend",
                lambda metric: make_thematic_trend(
                    thematic_data.df_collection_method_by_year,
                    "collection_method",
                    {"Survey": "#e76f51", "Administrative": "#2a9d8f"},
                    _metric_col(metric),
                    "Collection Method Over Time",
                    height=400,
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "deterministic-temporal-structure-trend",
                lambda metric: make_thematic_trend(
                    thematic_data.df_temporal_structure_by_year,
                    "temporal_structure",
                    {"Cross-sectional": "#f4a261", "Longitudinal": "#6a3d9a"},
                    _metric_col(metric),
                    "Temporal Structure Over Time",
                    height=400,
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "deterministic-unit-trend",
                lambda metric: make_thematic_trend(
                    thematic_data.df_unit_by_year,
                    "unit_of_observation",
                    {
                        "Individual": "#2a9d8f",
                        "Household": "#e9c46a",
                        "Business": "#264653",
                        "Area": "#e76f51",
                    },
                    _metric_col(metric),
                    "Unit of Observation Over Time",
                    height=400,
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
        ]
        for figure_id, builder in cases:
            for metric in ("pct", "count"):
                with self.subTest(figure=figure_id, metric=metric):
                    self._assert_serialises(
                        builder(metric),
                        EXPECTED_TOGGLE_GRAPH_HEIGHTS[figure_id],
                    )

    def test_uptake_adoption_toggle_renders_both_metrics_and_granularities(self):
        for granularity in ("year", "quarter"):
            for metric in ("pct", "count", "requests"):
                for collection_view in ("grouped", "individual"):
                    for selected_products in (FLAGSHIP_PRODUCTS, OTHER_PRODUCTS, ALL_PRODUCT_SELECTION, []):
                        with self.subTest(
                            metric=metric,
                            granularity=granularity,
                            collection_view=collection_view,
                            selected=len(selected_products),
                        ):
                            frame = adoption_curve_table(
                                granularity,
                                selected_products=selected_products,
                                collection_view=collection_view,
                            )
                            fig = make_adoption_curves(
                                frame,
                                metric=metric,
                                granularity=granularity,
                                partial_year_info=PARTIAL_YEAR_INFO,
                                collection_view=collection_view,
                            )
                            self._assert_serialises(
                                fig,
                                EXPECTED_TOGGLE_GRAPH_HEIGHTS["uptake-adoption-curves"],
                            )
                            payload = fig.to_plotly_json()
                            if frame.empty:
                                self.assertNotIn("categoryarray", payload["layout"].get("xaxis", {}))
                            else:
                                expected_order = (
                                    frame[["period_label", "period_date"]]
                                    .drop_duplicates()
                                    .sort_values("period_date", kind="stable")["period_label"]
                                    .astype(str)
                                    .tolist()
                                )
                                self.assertEqual(
                                    list(payload["layout"]["xaxis"]["categoryarray"]),
                                    expected_order,
                                )

    def test_uptake_adoption_selects_individual_products_without_other_aggregate(self):
        expected_flagship_products = {
            "Longitudinal Education Outcomes (LEO)",
            "Education and Child Health Insights from Linked Data (ECHILD)",
            # Data First per-dataset member products (reference 0.5.7); each is
            # its own line in individual view, collapsed to "Data First" grouped.
            "MoJ Data First Crown Court Defendant",
            "MoJ Data First Magistrates' Court Defendant",
            "MoJ Data First Linked Criminal Courts",
            "MoJ Data First Prisoner Custodial Journey",
            "MoJ Data First Probation",
            "MoJ Data First Family Court",
            "MoJ Data First Cross-Justice System Linking Dataset",
            "Growing Up in England (GUIE)",
            "GRading and Admissions Data England (GRADE)",
            "Administrative Data | Agricultural Research Collection (AD|ARC)",
            "Annual Survey of Hours and Earnings linked to Census 2011",
            "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment",
        }
        non_england_flagships = {
            "Earnings and Employees Study (EES) 2011 - Northern Ireland",
            "EOL",
        }

        default = adoption_curve_table("year", selected_products=FLAGSHIP_PRODUCTS)
        default_lines = set(default["line_id"].dropna().unique())
        self.assertEqual(default_lines, expected_flagship_products)
        self.assertTrue(non_england_flagships.isdisjoint(default_lines))

        all_selected = adoption_curve_table("year", selected_products=ALL_PRODUCT_SELECTION)
        all_lines = set(all_selected["line_id"].dropna().unique())
        self.assertTrue(expected_flagship_products.issubset(all_lines))
        self.assertTrue(non_england_flagships.issubset(all_lines))
        self.assertNotIn(OTHER_LINKED_DATASETS_LABEL, all_lines)
        for product in non_england_flagships:
            with self.subTest(other_product=product):
                groups = set(all_selected.loc[all_selected["line_id"] == product, "line_group"].unique())
                self.assertEqual(groups, {OTHER_LINKED_DATASETS_LABEL})

    def test_record_linkage_quarterly_trend_has_height_and_provisional_flag(self):
        frame = thematic_data.df_record_linkage_by_quarter
        fig = make_record_linkage_trend(
            frame,
            metric="pct",
            granularity="quarter",
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        self._assert_serialises(
            fig,
            EXPECTED_TOGGLE_GRAPH_HEIGHTS["deterministic-record-linkage-trend"],
        )
        payload = fig.to_plotly_json()
        expected_order = (
            frame[["period_label", "period_date"]]
            .drop_duplicates()
            .sort_values("period_date", kind="stable")["period_label"]
            .astype(str)
            .tolist()
        )
        self.assertEqual(list(payload["layout"]["xaxis"]["categoryarray"]), expected_order)
        annotation_text = " ".join(
            str(annotation.get("text", ""))
            for annotation in payload["layout"].get("annotations", [])
        )
        self.assertIn("latest quarter provisional", annotation_text)

    def test_tag_domain_bars_exclude_unclear_display_only(self):
        frame = pd.DataFrame([
            {
                "domain": "Health & Social Care",
                "count": 3,
                "domain_total": 10,
                "pct_of_domain": 30.0,
            },
            {
                "domain": "Unclear from Register Entry",
                "count": 1,
                "domain_total": 2,
                "pct_of_domain": 50.0,
            },
        ])
        fig = make_tag_domain_bar(
            frame,
            DOMAIN_COLOURS,
            "Tagged projects by domain",
            metric="pct",
        )
        payload = fig.to_plotly_json()
        y_values = list(payload["data"][0]["y"])
        self.assertNotIn("Unclear from Register Entry", y_values)
        annotation_text = " ".join(
            str(annotation.get("text", ""))
            for annotation in payload["layout"].get("annotations", [])
        )
        self.assertIn("Excludes 'Unclear from Register Entry' (n=2 projects)", annotation_text)

    def test_toggle_graph_components_have_fixed_render_height(self):
        # Collapse-on-re-render regression: the dcc.Graph container itself must
        # have a fixed height. 200-OK callbacks and valid figures did not catch
        # the visual collapse because the rendered graph div lost its height.
        from dashboard.layout.analysis.datasets import build_datasets_tab
        from dashboard.layout.analysis.thematic import build_thematic_tab

        graphs = {
            component.id: component
            for root in (build_thematic_tab(), build_datasets_tab())
            for component in _walk_components(root)
            if isinstance(component, dcc.Graph) and component.id
        }
        for graph_id, expected_height in EXPECTED_TOGGLE_GRAPH_HEIGHTS.items():
            with self.subTest(graph=graph_id):
                self.assertIn(graph_id, graphs)
                style = graphs[graph_id].style or {}
                self.assertEqual(style.get("height"), f"{expected_height}px")

    def test_deterministic_facets_are_four_separate_accordion_items(self):
        from dashboard.layout.analysis.thematic import build_thematic_tab

        titles = [
            getattr(component, "title", None)
            for component in _walk_components(build_thematic_tab())
            if component.__class__.__name__ == "AccordionItem"
        ]
        for title in [
            "Record linkage",
            "Researcher sector",
            "Unit of observation",
            "Collection method & temporal structure",
        ]:
            with self.subTest(title=title):
                self.assertIn(title, titles)
        self.assertNotIn("Record linkage & data structure", titles)

    def test_metric_callbacks_do_not_share_unrelated_toggle_state(self):
        from dashboard.app import app

        expected = {
            "thematic-domain-trend.figure": {"thematic-domain-trend-metric.value"},
            "thematic-purpose-trend.figure": {"thematic-purpose-trend-metric.value"},
            "thematic-cross-domain-purpose.figure": {"thematic-cross-domain-purpose-metric.value"},
            "thematic-domain-cooccurrence.figure": {"thematic-domain-cooccurrence-metric.value"},
            "thematic-tag-trend.figure": {"thematic-tag-trend-metric.value"},
            "thematic-covid-tag-domain.figure": {"thematic-covid-tag-domain-metric.value"},
            "thematic-demographic-tag-domain.figure": {"thematic-demographic-tag-domain-metric.value"},
            "deterministic-record-linkage-trend.figure": {
                "deterministic-record-linkage-trend-metric.value",
                "deterministic-record-linkage-trend-granularity.value",
            },
            "deterministic-domain-linkage-breakdown.figure": {"deterministic-domain-linkage-metric.value"},
            "deterministic-collection-method-trend.figure": {"deterministic-collection-method-trend-metric.value"},
            "deterministic-temporal-structure-trend.figure": {"deterministic-temporal-structure-trend-metric.value"},
            "deterministic-unit-trend.figure": {"deterministic-unit-trend-metric.value"},
            "thematic-latent-demand.figure": {"thematic-latent-demand-metric.value"},
            "uptake-adoption-curves.figure": {
                "uptake-adoption-metric.value",
                "uptake-adoption-granularity.value",
                "uptake-adoption-products.value",
                "datasets-collection-display-mode.value",
            },
            "uptake-exposure-rate-bar.figure": {
                "uptake-adoption-metric.value",
                "uptake-adoption-granularity.value",
                "uptake-adoption-products.value",
                "datasets-collection-display-mode.value",
            },
        }
        callback_by_output = {}
        for meta in app.callback_map.values():
            output = meta["output"]
            if isinstance(output, list):
                for item in output:
                    callback_by_output[str(item)] = meta
            else:
                callback_by_output[str(output)] = meta

        for output, allowed_inputs in expected.items():
            with self.subTest(output=output):
                self.assertIn(output, callback_by_output)
                meta = callback_by_output[output]
                inputs = {f"{item['id']}.{item['property']}" for item in meta["inputs"]}
                states = {f"{item['id']}.{item['property']}" for item in meta["state"]}
                self.assertEqual(inputs, allowed_inputs)
                self.assertFalse(states)


if __name__ == "__main__":
    unittest.main()
