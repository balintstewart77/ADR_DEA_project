"""Dataset Demand sub-tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.charts.template import CHART_CONFIG
from dashboard.data.registry import _ALL_PROVIDER_OPTIONS


def build_datasets_tab():
    return dbc.Tab(label="Dataset Demand", tab_id="tab-datasets", children=[
        html.P(
            "Explore which datasets are used most, how demand changes over time, and which source organisations are most represented.",
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
                html.Label("Source organisation", className="filter-label"),
                dcc.Dropdown(
                    id="datasets-provider-filter",
                    options=_ALL_PROVIDER_OPTIONS,
                    value="ALL",
                    clearable=False,
                ),
            ], md=4),
            dbc.Col([
                html.Label("Exclude cross-domain linked datasets", className="filter-label"),
                dcc.Checklist(
                    id="datasets-exclude-flagship",
                    options=[{"label": " Exclude cross-domain linked", "value": "yes"}],
                    value=[],
                    className="pt-1",
                ),
            ], md=3),
        ], className="mb-3 g-2"),
        dbc.Row([
            dbc.Col(
                html.Div(dcc.Graph(id="datasets-topn-chart", config=CHART_CONFIG), className="chart-wrapper"),
                width=12,
            ),
        ]),
        dbc.Row([
            dbc.Col(
                html.Div(dcc.Graph(id="datasets-trend-chart", config=CHART_CONFIG), className="chart-wrapper"),
                md=7,
            ),
            dbc.Col(
                html.Div(dcc.Graph(id="datasets-provider-chart", config=CHART_CONFIG), className="chart-wrapper"),
                md=5,
            ),
        ]),
        # The previous Cross-Domain Linked Dataset Breakdown used the stale ADR
        # flagship dataset list. Rebuild it from deterministic record-linkage
        # data before surfacing that breakdown again.
    ])
