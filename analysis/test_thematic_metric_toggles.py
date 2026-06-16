import json
import unittest

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
    OTHER_LINKED_DATASETS_LABEL,
    SERVED_DOMAIN_PAIRS,
    adoption_curve_table,
)


def _metric_col(metric: str) -> str:
    return "pct_of_projects" if metric == "pct" else "count"


class ThematicMetricToggleRegressionTest(unittest.TestCase):
    """Defend against the second recurrence of the G9 metric-toggle coupling bug."""

    def _assert_serialises(self, figure):
        payload = figure.to_plotly_json()
        json.dumps(payload, cls=PlotlyJSONEncoder)
        self.assertIn("data", payload)
        self.assertIn("layout", payload)

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
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
            (
                "thematic-cross-domain-purpose",
                lambda metric: make_cross_heatmap(
                    thematic_data.df_cross_domain_purpose,
                    "domain",
                    "Substantive Domain x Analytical Purpose",
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
                    partial_year_info=PARTIAL_YEAR_INFO,
                ),
            ),
        ]
        for figure_id, builder in cases:
            for metric in ("pct", "count"):
                with self.subTest(figure=figure_id, metric=metric):
                    self._assert_serialises(builder(metric))

    def test_uptake_adoption_toggle_renders_both_metrics_and_granularities(self):
        for granularity in ("year", "quarter"):
            for metric in ("pct", "count"):
                for break_out_other in (False, True):
                    with self.subTest(
                        metric=metric,
                        granularity=granularity,
                        break_out_other=break_out_other,
                    ):
                        frame = adoption_curve_table(
                            granularity,
                            show_flagships=True,
                            break_out_other=break_out_other,
                        )
                        self._assert_serialises(
                            make_adoption_curves(
                                frame,
                                metric=metric,
                                granularity=granularity,
                                partial_year_info=PARTIAL_YEAR_INFO,
                            )
                        )

    def test_uptake_adoption_default_groups_flagships_and_aggregates_other(self):
        expected_flagship_products = {
            "Longitudinal Education Outcomes (LEO)",
            "Education and Child Health Insights from Linked Data (ECHILD)",
            "MoJ Data First",
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

        default = adoption_curve_table("year", show_flagships=True, break_out_other=False)
        default_lines = set(default["line_id"].dropna().unique())
        self.assertEqual(default_lines, expected_flagship_products | {OTHER_LINKED_DATASETS_LABEL})
        self.assertTrue(non_england_flagships.isdisjoint(default_lines))
        self.assertEqual(
            set(default.loc[
                default["line_id"] == OTHER_LINKED_DATASETS_LABEL,
                "line_group",
            ].unique()),
            {OTHER_LINKED_DATASETS_LABEL},
        )

        breakout = adoption_curve_table("year", show_flagships=True, break_out_other=True)
        breakout_lines = set(breakout["line_id"].dropna().unique())
        self.assertTrue(expected_flagship_products.issubset(breakout_lines))
        self.assertTrue(non_england_flagships.issubset(breakout_lines))
        self.assertNotIn(OTHER_LINKED_DATASETS_LABEL, breakout_lines)
        for product in non_england_flagships:
            with self.subTest(other_product=product):
                groups = set(breakout.loc[breakout["line_id"] == product, "line_group"].unique())
                self.assertEqual(groups, {OTHER_LINKED_DATASETS_LABEL})

    def test_metric_callbacks_are_one_output_and_do_not_share_toggle_state(self):
        from dashboard.app import app

        expected = {
            "thematic-domain-trend.figure": {"thematic-domain-trend-metric.value"},
            "thematic-purpose-trend.figure": {"thematic-purpose-trend-metric.value"},
            "thematic-cross-domain-purpose.figure": {"thematic-cross-domain-purpose-metric.value"},
            "thematic-domain-cooccurrence.figure": {"thematic-domain-cooccurrence-metric.value"},
            "thematic-tag-trend.figure": {"thematic-tag-trend-metric.value"},
            "thematic-covid-tag-domain.figure": {"thematic-covid-tag-domain-metric.value"},
            "thematic-demographic-tag-domain.figure": {"thematic-demographic-tag-domain-metric.value"},
            "deterministic-record-linkage-trend.figure": {"deterministic-record-linkage-trend-metric.value"},
            "deterministic-domain-linkage-breakdown.figure": {"deterministic-domain-linkage-metric.value"},
            "deterministic-collection-method-trend.figure": {"deterministic-collection-method-trend-metric.value"},
            "deterministic-temporal-structure-trend.figure": {"deterministic-temporal-structure-trend-metric.value"},
            "deterministic-unit-trend.figure": {"deterministic-unit-trend-metric.value"},
            "thematic-latent-demand.figure": {"thematic-latent-demand-metric.value"},
            "uptake-adoption-curves.figure": {
                "uptake-adoption-metric.value",
                "uptake-adoption-granularity.value",
                "uptake-adoption-display-options.value",
            },
        }
        callback_by_output = {}
        for meta in app.callback_map.values():
            output = meta["output"]
            if isinstance(output, list):
                continue
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
