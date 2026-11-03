"""Linked data uptake section shared by portfolio analysis tabs."""

from dash import dcc, html
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd

from dashboard.charts.template import CHART_CONFIG
from dashboard.charts.uptake import make_exposure_rate_bar
from dashboard.components.chart_tips import chart_wrapper
from dashboard.components.data_grid import data_grid
from dashboard.data.uptake import (
    FLAGSHIP_PRODUCTS,
    OTHER_PRODUCTS,
    PRODUCT_SELECTION_OPTIONS,
    product_summary_table,
)

UPTAKE_CURVES_HEIGHT = 460
UPTAKE_EXPOSURE_BAR_HEIGHT = 520


def _uptake_graph(graph_id: str, height: int) -> html.Div:
    return chart_wrapper(
        dcc.Graph(
            id=graph_id,
            config=CHART_CONFIG,
            responsive=True,
            style={"height": f"{height}px"},
        ),
        graph_id,
        style={"minHeight": f"{height + 8}px"},
    )


_ADOPTION_SUMMARY_COLUMNS = [
    {"headerName": "Linked product", "field": "product", "flex": 2, "minWidth": 200},
    {"headerName": "Flagship grouping", "field": "flagship_group", "flex": 2, "minWidth": 170},
    {"headerName": "Linkage span", "field": "linkage_span", "flex": 1, "minWidth": 120},
    {"headerName": "Historical first accredited use", "field": "first_use", "flex": 1, "minWidth": 140},
    {"headerName": "Selected-window exposure (years)", "field": "exposure_years", "flex": 1, "minWidth": 140},
    {"headerName": "Selected projects", "field": "total_projects", "flex": 1, "minWidth": 120},
    {"headerName": "Selected projects / exposure-year", "field": "projects_per_exposure_year", "flex": 1, "minWidth": 150},
]


def build_adoption_summary_table(summary: pd.DataFrame) -> dag.AgGrid:
    """Static per-product adoption summary (deterministic)."""
    fields = [column["field"] for column in _ADOPTION_SUMMARY_COLUMNS]
    rows = summary[fields].astype(object).where(pd.notna(summary[fields]), None)
    return data_grid(_ADOPTION_SUMMARY_COLUMNS, rows.to_dict("records"))


def _linked_data_uptake_content() -> list:
    flagship_count = len(FLAGSHIP_PRODUCTS)
    other_count = len(OTHER_PRODUCTS)
    initial_summary = product_summary_table(
        collection_view="grouped",
        selected_products=FLAGSHIP_PRODUCTS,
    )
    return [
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
            "can be added as a group or chosen individually. Lines cover the selected observation "
            "window from each dataset's historical first accredited-use period. The Collections toggle switches between reference-defined "
            "collection lines and individual linked-product lines. DEA-gateway use only.",
            className="section-desc text-muted",
        ),
        dbc.Row([
            dbc.Col([
                html.Label("Metric", className="filter-label"),
                dcc.Dropdown(
                    id="uptake-adoption-metric",
                    options=[
                        {"label": "Project count", "value": "count"},
                        {"label": "Access requests", "value": "requests"},
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
                html.Label("Collections", className="filter-label"),
                dcc.RadioItems(
                    id="datasets-collection-display-mode",
                    options=[
                        {"label": "Grouped", "value": "grouped"},
                        {"label": "Individual", "value": "individual"},
                    ],
                    value="grouped",
                    inline=True,
                    inputStyle={"marginRight": "0.3rem"},
                    labelStyle={"marginRight": "0.7rem", "fontSize": "0.86rem"},
                    className="collection-display-toggle",
                ),
            ], md=2),
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
                html.Label("Linked products included", className="filter-label"),
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
            "Historical first use comes from the full matched-product register history. Exposure is "
            "its intersection with the selected calendar window; completed years run to the following "
            "1 January and the partial final year stops at the full-register cutoff. Counts and rates "
            "use only selected records. Grouped collections use the earliest historical first use "
            "among their included members. These are DEA-route uptake measures; short exposures show "
            "initial adoption, not sustained demand.",
            className="section-desc",
        ),
        html.Div(
            [
                chart_wrapper(
                    dcc.Graph(
                        id="uptake-exposure-rate-bar",
                        figure=make_exposure_rate_bar(initial_summary),
                        config=CHART_CONFIG,
                        responsive=True,
                        style={"height": f"{UPTAKE_EXPOSURE_BAR_HEIGHT}px"},
                    ),
                    "uptake-exposure-rate-bar",
                    style={"minHeight": f"{UPTAKE_EXPOSURE_BAR_HEIGHT + 8}px"},
                ),
                html.Div(
                    build_adoption_summary_table(initial_summary),
                    id="uptake-adoption-summary-table",
                    className="mb-2",
                ),
            ],
            className="g-3",
        ),
    ]


def build_linked_data_uptake_section() -> html.Section:
    return html.Section(
        [
            html.H4("Linked Data Uptake", className="linked-data-uptake-heading"),
            *_linked_data_uptake_content(),
        ],
        className="linked-data-uptake-section",
    )
