"""Linked data uptake section shared by portfolio analysis tabs."""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

from dashboard.charts.template import CHART_CONFIG
from dashboard.charts.uptake import make_exposure_rate_bar
from dashboard.components.chart_tips import chart_wrapper
from dashboard.components.table_styles import BROWSE_TABLE_STYLES
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


def build_adoption_summary_table(summary: pd.DataFrame) -> dash_table.DataTable:
    """Static per-product adoption summary (deterministic)."""
    display = summary.copy()
    columns = [
        {"name": "Linked product", "id": "product"},
        {"name": "Flagship grouping", "id": "flagship_group"},
        {"name": "Linkage span", "id": "linkage_span"},
        {"name": "First accredited use", "id": "first_use"},
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
            "can be added as a group or chosen individually. Lines begin at each dataset's "
            "first accredited use in the DEA register. The Collections toggle switches between reference-defined "
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
            "Exposure begins at the first accredited use of each linked dataset observed in "
            "the DEA register. Exposure-years therefore measure observed DEA-gateway uptake "
            "from first use onwards; they do not claim to identify when the dataset first "
            "became technically available through any route. For grouped collections, exposure "
            "begins at the earliest first accredited use among the collection members included "
            "in that line. Rates over short exposures are initial-adoption rates, not sustained demand.",
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
                    className="dea-table mb-2",
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
