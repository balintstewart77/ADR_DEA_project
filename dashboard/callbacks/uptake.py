"""Linked data uptake callbacks (deterministic layer)."""

from dash import Input, Output, ctx

from dashboard.charts.uptake import make_adoption_curves
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.uptake import (
    FLAGSHIP_PRODUCTS,
    OTHER_PRODUCTS,
    adoption_curve_table,
)


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
        Input("uptake-adoption-metric", "value"),
        Input("uptake-adoption-granularity", "value"),
        Input("uptake-adoption-products", "value"),
    )
    def update_adoption_curves(metric, granularity, selected_products):
        selected_granularity = granularity or "year"
        source = adoption_curve_table(
            selected_granularity,
            selected_products=selected_products or [],
        )
        return make_adoption_curves(
            source,
            metric=metric or "count",
            granularity=selected_granularity,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
