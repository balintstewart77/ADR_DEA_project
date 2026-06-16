"""Linked data uptake callbacks (deterministic layer)."""

from dash import Input, Output

from dashboard.charts.uptake import make_adoption_curves
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.uptake import (
    adoption_curve_table,
)


def register(app):
    @app.callback(
        Output("uptake-adoption-curves", "figure"),
        Input("uptake-adoption-metric", "value"),
        Input("uptake-adoption-granularity", "value"),
        Input("uptake-adoption-display-options", "value"),
    )
    def update_adoption_curves(metric, granularity, display_options):
        selected_granularity = granularity or "year"
        options = set(display_options or [])
        source = adoption_curve_table(
            selected_granularity,
            show_flagships="show_flagships" in options,
            break_out_other="breakout_other" in options,
        )
        return make_adoption_curves(
            source,
            metric=metric or "count",
            granularity=selected_granularity,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
