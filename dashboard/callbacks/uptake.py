"""Linked data uptake callbacks (deterministic layer)."""

from dash import Input, Output

from dashboard.charts.thematic import make_record_linkage_trend
from dashboard.charts.uptake import add_availability_annotations, make_adoption_curves
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.thematic import df_record_linkage_by_year
from dashboard.data.uptake import (
    DF_PRODUCT_BY_YEAR,
    PRODUCT_SUMMARY,
    availability_annotations,
    top_products,
)

_SHORT_BY_PRODUCT = dict(zip(PRODUCT_SUMMARY["product"], PRODUCT_SUMMARY["short"]))
_SPAN_BY_PRODUCT = dict(zip(PRODUCT_SUMMARY["product"], PRODUCT_SUMMARY["linkage_span"]))


def register(app):
    @app.callback(
        Output("uptake-adoption-curves", "figure"),
        Input("uptake-adoption-topn", "value"),
        Input("uptake-adoption-metric", "value"),
    )
    def update_adoption_curves(top_n, metric):
        return make_adoption_curves(
            DF_PRODUCT_BY_YEAR,
            top_products(int(top_n or 6)),
            _SHORT_BY_PRODUCT,
            _SPAN_BY_PRODUCT,
            metric=metric or "count",
            partial_year_info=PARTIAL_YEAR_INFO,
        )

    @app.callback(
        Output("uptake-linkage-availability-trend", "figure"),
        Input("uptake-linkage-trend-metric", "value"),
    )
    def update_linkage_availability_trend(metric):
        # Reuse the record-linkage trend (same data and logic as the
        # "Record linkage & data structure" figure), then overlay
        # availability markers for the top products.
        fig = make_record_linkage_trend(
            df_record_linkage_by_year,
            metric=metric or "pct",
            height=440,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        years = df_record_linkage_by_year["Year"]
        min_year = float(years.min()) if len(years) else None
        return add_availability_annotations(
            fig,
            availability_annotations(n=6),
            min_x=min_year,
        )
