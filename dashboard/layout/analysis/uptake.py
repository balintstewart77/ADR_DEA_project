"""Linked data uptake section shared by portfolio analysis tabs."""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

from dashboard.charts.template import CHART_CONFIG
from dashboard.charts.uptake import make_exposure_rate_bar
from dashboard.components.table_styles import BROWSE_TABLE_STYLES
from dashboard.data.uptake import (
    FLAGSHIP_PRODUCTS,
    OTHER_PRODUCTS,
    PRODUCT_SELECTION_OPTIONS,
    PRODUCT_SUMMARY,
)

UPTAKE_CURVES_HEIGHT = 460
UPTAKE_EXPOSURE_BAR_HEIGHT = 520


def _uptake_graph(graph_id: str, height: int) -> html.Div:
    return html.Div(
        dcc.Graph(
            id=graph_id,
            config=CHART_CONFIG,
            responsive=True,
            style={"height": f"{height}px"},
        ),
        className="chart-wrapper",
        style={"minHeight": f"{height + 8}px"},
    )


_AVAILABILITY_BASIS_DISPLAY = {
    "documented_accessible": "documented accessible",
    "bounded_by_first_use": "bounded by first use",
    "pre_register_window": "pre-register window",
    "proxy": "first register appearance",
}


def _adoption_summary_table() -> dash_table.DataTable:
    """Static per-product adoption summary (deterministic)."""
    display = PRODUCT_SUMMARY.copy()
    display["availability_display"] = display.apply(
        lambda row: (
            f"{row['availability']} (bounded; announced {row['announced']})"
            if row["basis"] == "announced"
            else f"{row['availability']} "
                 f"({_AVAILABILITY_BASIS_DISPLAY.get(row['basis'], row['basis'])})"
        ),
        axis=1,
    )
    display["lag_display"] = display.apply(
        lambda row: (
            "n/a (bounded)" if row["basis"] in ("announced", "bounded_by_first_use")
            else "-" if pd.isna(row["lag_years"])
            else f"{row['lag_years']:.1f}"
        ),
        axis=1,
    )
    display["delivery_display"] = display["delivery_lag_years"].map(
        lambda value: "-" if pd.isna(value) else f"{value:.1f}"
    )
    columns = [
        {"name": "Linked product", "id": "product"},
        {"name": "Flagship grouping", "id": "flagship_group"},
        {"name": "Linkage span", "id": "linkage_span"},
        {"name": "Availability", "id": "availability_display"},
        {"name": "First accredited use", "id": "first_use"},
        {"name": "Adoption lag (years)", "id": "lag_display"},
        {"name": "Announcement -> first DEA-route use (years)", "id": "delivery_display"},
        {"name": "Exposure (years)", "id": "exposure_years", "type": "numeric"},
        {"name": "Total projects", "id": "total_projects", "type": "numeric"},
        {"name": "Projects / exposure-year", "id": "projects_per_exposure_year", "type": "numeric"},
    ]
    table_cols = [column["id"] for column in columns]
    table_data = display[table_cols].astype(object).where(pd.notna(display[table_cols]), None)
    return dash_table.DataTable(
        data=table_data.to_dict("records"),
        columns=columns,
        sort_action="native",
        page_size=20,
        **BROWSE_TABLE_STYLES,
    )


def build_linked_data_uptake_item() -> dbc.AccordionItem:
    flagship_count = len(FLAGSHIP_PRODUCTS)
    other_count = len(OTHER_PRODUCTS)
    return dbc.AccordionItem(
        [
            html.P(
                "Derived deterministically from the register and the named linked-product "
                "catalogue in analysis/register_reference.yaml - exact, reproducible, auditable. "
                "The register observes DEA-gateway use only: assets accessible via other legal "
                "gateways have demand invisible to this instrument, so all uptake findings here "
                "are DEA-route uptake.",
                className="section-desc",
            ),
            html.P(
                "ADR England flagship datasets are selected by default. Other linked datasets "
                "can be added as a group or chosen individually. Lines begin at each dataset's "
                "availability. DEA-gateway use only.",
                className="section-desc text-muted",
            ),
            dbc.Row([
                dbc.Col([
                    html.Label("Metric", className="filter-label"),
                    dcc.Dropdown(
                        id="uptake-adoption-metric",
                        options=[
                            {"label": "Project count", "value": "count"},
                            {"label": "% of period's projects", "value": "pct"},
                        ],
                        value="count",
                        clearable=False,
                        searchable=False,
                    ),
                ], md=3),
                dbc.Col([
                    html.Label("Granularity", className="filter-label"),
                    dcc.Dropdown(
                        id="uptake-adoption-granularity",
                        options=[
                            {"label": "Year", "value": "year"},
                            {"label": "Quarter", "value": "quarter"},
                        ],
                        value="year",
                        clearable=False,
                        searchable=False,
                    ),
                ], md=3),
                dbc.Col([
                    html.Label("Dataset groups", className="filter-label"),
                    dcc.Checklist(
                        id="uptake-adoption-group-toggles",
                        options=[
                            {
                                "label": f"Show ADR England flagship datasets ({flagship_count})",
                                "value": "flagship",
                            },
                            {
                                "label": f"Show Other linked datasets ({other_count})",
                                "value": "other",
                            },
                        ],
                        value=["flagship"],
                        inline=False,
                        inputStyle={"marginRight": "0.35rem"},
                        labelStyle={"display": "block", "fontSize": "0.88rem", "lineHeight": "1.55"},
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Datasets shown", className="filter-label"),
                    dcc.Dropdown(
                        id="uptake-adoption-products",
                        options=PRODUCT_SELECTION_OPTIONS,
                        value=FLAGSHIP_PRODUCTS,
                        multi=True,
                        clearable=True,
                        searchable=True,
                        placeholder="Choose linked datasets",
                    ),
                ], md=12),
            ], className="mb-2 g-2"),
            _uptake_graph("uptake-adoption-curves", height=UPTAKE_CURVES_HEIGHT),
            html.H6("Adoption summary", className="mt-3"),
            html.P(
                "Availability follows the available-by rule: a date is recorded as accessible "
                "only where the source evidences actual SRS/DEA access; announcement-only "
                "sources bound availability by first register use instead, with the "
                "announcement kept separately. Adoption lag (availability -> first DEA use) and "
                "delivery/governance lag (announcement -> first DEA-route use) are different "
                "quantities and shown in separate columns - bounded and announced rows show "
                "adoption lag as \"n/a (bounded)\" rather than a false zero. Rates over short "
                "exposures are initial-adoption rates, not sustained demand.",
                className="section-desc",
            ),
            html.Div(
                [
                    dcc.Graph(
                        id="uptake-exposure-rate-bar",
                        figure=make_exposure_rate_bar(PRODUCT_SUMMARY),
                        config=CHART_CONFIG,
                        responsive=True,
                        style={"height": f"{UPTAKE_EXPOSURE_BAR_HEIGHT}px"},
                    ),
                    html.Div(_adoption_summary_table(), className="dea-table mb-2"),
                ],
                className="g-3",
            ),
        ],
        title="Linked data uptake",
    )


def build_linked_data_uptake_section() -> dbc.Accordion:
    return dbc.Accordion(
        [build_linked_data_uptake_item()],
        start_collapsed=False,
        always_open=True,
        className="mt-4",
    )
