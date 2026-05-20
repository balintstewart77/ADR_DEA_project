"""Overview tab and stat cards."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.components.stat_card import stat_card
from dashboard.charts.core import make_yearly_chart, make_quarterly_chart, make_srs_chart
from dashboard.charts.template import CHART_CONFIG
from dashboard.config import FEEDBACK_EMAIL_URL, SOURCE_URL
from dashboard.data.registry import (
    df_all, PARTIAL_YEAR_INFO,
    TOTAL_PROJECTS, TOTAL_DATASET_REQUESTS, TOTAL_FLAGSHIP, TOTAL_FLAGSHIP_REQUESTS,
    YEAR_RANGE,
)


def build_stat_cards():
    return dbc.Row([
        stat_card(f"{TOTAL_PROJECTS:,}", "Total DEA Projects", "#3366cc"),
        stat_card(f"{TOTAL_DATASET_REQUESTS:,}", "DEA Dataset Requests", "#6633cc"),
        stat_card(f"{TOTAL_FLAGSHIP:,}", "Projects Using Cross-Domain Linked Datasets", "#109618"),
        stat_card(f"{TOTAL_FLAGSHIP_REQUESTS:,}", "Cross-Domain Linked Dataset Requests", "#ff9900"),
        stat_card(YEAR_RANGE, "Year Range", "#0099c6"),
    ], className="mb-4 g-3")


def build_overview_tab():
    yearly_fig = make_yearly_chart(df_all, partial_year_info=PARTIAL_YEAR_INFO)

    return dbc.Tab(label="Overview", tab_id="tab-overview", children=[
        html.Div([
            html.H4("Explore Digital Economy Act 2017 (DEA)-accredited research projects through a searchable public register and portfolio-level analysis."),
            html.P(
                "The DEA research powers allow accredited researchers to access de-identified data held by public authorities for public-good research "
                "in accredited secure environments. Built from the public register of DEA-accredited projects, this dashboard is primarily a public-facing "
                "tool to make those projects easier to see, search, and understand. It is intended to improve legibility around how public data is being "
                "used for accredited research, while also providing a clearer view of patterns "
                "in dataset use, institutional participation, and demand over time."
            ),
            html.Div([
                html.P("This dashboard is a public prototype. Feedback, corrections, and suggestions are welcome."),
                html.Div([
                    html.A(
                        "Provide feedback",
                        href=FEEDBACK_EMAIL_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="btn btn-outline-secondary btn-sm feedback-link",
                    ),
                    html.A(
                        "View source / report issue",
                        href=SOURCE_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="btn btn-outline-secondary btn-sm feedback-link",
                    ),
                ], style={"display": "flex", "gap": "0.6rem", "flexWrap": "wrap"}),
            ], className="prototype-note"),
        ], className="overview-lead"),

        # Mode selection cards
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.H5("\U0001F50D Project Explorer"),
                    html.P(
                        "Search by title, researcher, dataset, provider, institution, or collection."
                    ),
                    html.Button(
                        "Open Project Explorer",
                        id="mode-explorer-btn",
                        className="btn btn-outline-primary btn-sm",
                    ),
                ], className="mode-card"),
                md=6,
            ),
            dbc.Col(
                html.Div([
                    html.H5("\U0001F4CA Portfolio Analysis"),
                    html.P(
                        "Explore trends in project growth, dataset demand, linked dataset uptake, institutions, and themes."
                    ),
                    html.Button(
                        "View analysis",
                        id="mode-analysis-btn",
                        className="btn btn-outline-primary btn-sm",
                    ),
                ], className="mode-card"),
                md=6,
            ),
        ], className="mb-4 g-3"),

        dbc.Row([
            dbc.Col(
                html.Div(
                    dcc.Graph(
                        id="overview-teaser-chart",
                        figure=yearly_fig,
                        config=CHART_CONFIG,
                    ),
                    className="chart-wrapper",
                ),
                width=12,
            ),
        ]),
    ])
