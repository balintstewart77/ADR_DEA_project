"""Institutions sub-tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.charts.template import CHART_CONFIG


def build_institutions_tab():
    return dbc.Tab(label="Institutions", tab_id="tab-institutions", children=[
        html.P(
            "See which research organisations are most represented through researcher affiliations, and how that changes over time.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col([
                html.Label("Show top N institutions", className="filter-label"),
                html.Div([
                    dcc.Dropdown(
                        id="institutions-topn-preset",
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
                        id="institutions-topn-custom", type="number",
                        min=1, max=500, step=1, placeholder="N",
                        style={"width": "80px", "display": "none", "verticalAlign": "middle", "marginLeft": "8px"},
                    ),
                ], style={"display": "flex", "alignItems": "center"}),
            ], md=3),
        ]),
        dbc.Row([
            dbc.Col(
                html.Div(dcc.Graph(id="institutions-bar-chart", config=CHART_CONFIG), className="chart-wrapper"),
                width=12,
            ),
        ]),
        dbc.Row([
            dbc.Col(
                html.Div(dcc.Graph(id="institutions-trend-chart", config=CHART_CONFIG), className="chart-wrapper"),
                width=12,
            ),
        ]),
    ])
