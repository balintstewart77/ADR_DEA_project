"""Dataset Demand sub-tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.charts.template import CHART_CONFIG
from dashboard.data.registry import COLLECTIONS, _ALL_PROVIDER_OPTIONS


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
        html.Hr(className="my-4"),
        dbc.Accordion([
            dbc.AccordionItem(
                title="Cross-Domain Linked Dataset Breakdown",
                children=[
                    html.P(
                        "Track use of cross-domain linked datasets using either distinct projects or total dataset requests.",
                        className="section-desc",
                    ),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Filter by collection", className="filter-label"),
                            dcc.Dropdown(
                                id="collection-filter",
                                options=[{"label": c, "value": c} for c in COLLECTIONS],
                                multi=True,
                                placeholder="All collections",
                                clearable=True,
                            ),
                        ], md=6),
                        dbc.Col([
                            html.Label("Metric", className="filter-label"),
                            dcc.Dropdown(
                                id="flagship-metric-mode",
                                options=[
                                    {"label": "Distinct projects", "value": "projects"},
                                    {"label": "Dataset access requests", "value": "requests"},
                                ],
                                value="projects",
                                clearable=False,
                            ),
                        ], md=3),
                    ], className="mb-2 g-2"),
                    html.P(
                        "Distinct projects count each retained project once per collection. "
                        "Dataset access requests count every matched dataset request, so one project can contribute multiple requests within the same collection.",
                        className="section-desc",
                    ),
                    dbc.Row([
                        dbc.Col(
                            html.Div(dcc.Graph(id="flagship-pooled-yearly", config=CHART_CONFIG), className="chart-wrapper"),
                            width=12,
                        ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            html.Div(dcc.Graph(id="flagship-pooled-quarterly", config=CHART_CONFIG), className="chart-wrapper"),
                            width=12,
                        ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            html.Div(dcc.Graph(id="flagship-line-yearly-chart", config=CHART_CONFIG), className="chart-wrapper"),
                            width=12,
                        ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            html.Div(dcc.Graph(id="flagship-line-quarterly-chart", config=CHART_CONFIG), className="chart-wrapper"),
                            width=12,
                        ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            html.Div(dcc.Graph(id="flagship-totals-chart", config=CHART_CONFIG), className="chart-wrapper"),
                            width=12,
                        ),
                    ]),
                    dbc.Row([
                        dbc.Col(
                            html.Div(dcc.Graph(id="flagship-cumulative-chart", config=CHART_CONFIG), className="chart-wrapper"),
                            width=12,
                        ),
                    ]),
                ],
            ),
        ], start_collapsed=True, className="mt-3"),
    ])
