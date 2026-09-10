"""Dataset Demand sub-tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.charts.template import CHART_CONFIG
from dashboard.components.chart_tips import chart_wrapper
from dashboard.data.registry import _ALL_PROVIDER_OPTIONS
from dashboard.layout.analysis.uptake import build_linked_data_uptake_section


def build_datasets_tab():
    return dbc.Tab(label="Dataset Demand", tab_id="tab-datasets", children=[
        html.P(
            "Explore which datasets are used most, how demand changes over time, and which dataset source organisations are most represented.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col([
                html.Label("Show top N datasets", className="filter-label"),
                html.Div([
                    dcc.Dropdown(
                        id="datasets-topn-preset",
                        options=[
                            {"label": "5", "value": 5},
                            {"label": "10", "value": 10},
                            {"label": "25", "value": 25},
                            {"label": "50", "value": 50},
                            {"label": "Custom", "value": -1},
                        ],
                        value=10,
                        clearable=False,
                        searchable=False,
                        style={"width": "110px", "display": "inline-block", "verticalAlign": "middle"},
                    ),
                    dbc.Input(
                        id="datasets-topn-custom", type="number",
                        min=1, max=500, step=1, placeholder="N",
                        style={"width": "80px", "display": "none", "verticalAlign": "middle", "marginLeft": "8px"},
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
            ], md=3),
            dbc.Col([
                html.Label("Dataset source organisation", className="filter-label"),
                dcc.Dropdown(
                    id="datasets-provider-filter",
                    options=_ALL_PROVIDER_OPTIONS,
                    value="ALL",
                    clearable=False,
                ),
            ], md=4),
            dbc.Col([
                html.Label("Metric", className="filter-label"),
                dcc.Dropdown(
                    id="datasets-topn-metric",
                    options=[
                        {"label": "Total projects", "value": "count"},
                        {"label": "Selected projects per exposure-year", "value": "rate"},
                    ],
                    value="count",
                    clearable=False,
                    searchable=False,
                ),
            ], md=3),
        ], className="mb-3 g-2"),
        dbc.Row([
            dbc.Col(
                chart_wrapper(
                    dcc.Graph(id="datasets-topn-chart", config=CHART_CONFIG),
                    "datasets-topn-chart",
                ),
                width=12,
            ),
        ]),
        html.P(
            "The rate divides selected-period distinct projects by exposure within the selected "
            "calendar window. Exposure is the intersection of that window with the dataset's "
            "historical availability: a curated reference date where present, otherwise its first "
            "full-register appearance. Completed years run to the following 1 January; the partial "
            "final year stops at the full-register cutoff. Rates over short exposures are "
            "initial-adoption rates, not sustained demand.",
            className="section-desc text-muted small",
        ),
        dbc.Row([
            dbc.Col(
                chart_wrapper(
                    dcc.Graph(id="datasets-trend-chart", config=CHART_CONFIG),
                    "datasets-trend-chart",
                ),
                md=7,
            ),
            dbc.Col(
                chart_wrapper(
                    dcc.Graph(id="datasets-provider-chart", config=CHART_CONFIG),
                    "datasets-provider-chart",
                ),
                md=5,
            ),
        ]),
        build_linked_data_uptake_section(),
    ])
