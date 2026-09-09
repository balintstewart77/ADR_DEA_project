"""Linked data uptake callbacks (deterministic layer)."""

from dash import Input, Output, ctx

from dashboard.charts.uptake import make_adoption_curves, make_exposure_rate_bar
from dashboard.charts.template import annotate_empty
from dashboard.layout.analysis.uptake import build_adoption_summary_table
from dashboard.data.registry import PARTIAL_YEAR_INFO, df_all
from dashboard.data.year_filter import selected_record_ids, year_range
from dashboard.data.uptake import (
    FLAGSHIP_PRODUCTS,
    OTHER_PRODUCTS,
    adoption_curve_table,
    product_summary_table,
)


_YEAR_RANGE = year_range(df_all)


def register(app):
    def _group_values_for_products(products):
        selected = set(products or [])
        values = []
        if set(FLAGSHIP_PRODUCTS).issubset(selected):
            values.append("flagship")
        if set(OTHER_PRODUCTS).issubset(selected):
            values.append("other")
        return values

    def _products_for_groups(groups):
        selected = []
        group_values = set(groups or [])
        if "flagship" in group_values:
            selected.extend(FLAGSHIP_PRODUCTS)
        if "other" in group_values:
            selected.extend(OTHER_PRODUCTS)
        return selected

    @app.callback(
        Output("uptake-adoption-group-toggles", "value"),
        Output("uptake-adoption-products", "value"),
        Input("uptake-adoption-group-toggles", "value"),
        Input("uptake-adoption-products", "value"),
    )
    def sync_adoption_product_selection(group_values, product_values):
        triggered = ctx.triggered_id
        if triggered == "uptake-adoption-group-toggles":
            products = _products_for_groups(group_values)
            return list(group_values or []), products
        products = list(dict.fromkeys(product_values or []))
        return _group_values_for_products(products), products

    @app.callback(
        Output("uptake-adoption-curves", "figure"),
        Output("uptake-exposure-rate-bar", "figure"),
        Output("uptake-adoption-summary-table", "children"),
        Input("uptake-adoption-metric", "value"),
        Input("uptake-adoption-granularity", "value"),
        Input("uptake-adoption-products", "value"),
        Input("datasets-collection-display-mode", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_adoption_curves(
        metric, granularity, selected_products, collection_view, year_selection,
    ):
        selected_granularity = granularity or "year"
        selected = selected_products or []
        record_ids = selected_record_ids(df_all, year_selection, _YEAR_RANGE)
        source = adoption_curve_table(
            selected_granularity,
            selected_products=selected,
            collection_view=collection_view,
            eligible_record_ids=record_ids,
        )
        summary = product_summary_table(
            collection_view=collection_view,
            selected_products=selected,
            eligible_record_ids=record_ids,
        )
        curves = make_adoption_curves(
            source,
            metric=metric or "count",
            granularity=selected_granularity,
            partial_year_info=PARTIAL_YEAR_INFO,
            collection_view=collection_view or "grouped",
        )
        exposure = make_exposure_rate_bar(summary)
        return (
            annotate_empty(curves, source.empty),
            annotate_empty(exposure, not bool(summary["total_projects"].sum()) if len(summary) else True),
            build_adoption_summary_table(summary),
        )
