"""Overall Trends sub-tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.charts.core import make_yearly_chart, make_quarterly_chart, make_srs_chart
from dashboard.charts.template import CHART_CONFIG
from dashboard.components.chart_tips import chart_wrapper
from dashboard.data.registry import df_all, PARTIAL_YEAR_INFO


def build_trends_tab():
    yearly_fig = make_yearly_chart(df_all, partial_year_info=PARTIAL_YEAR_INFO)
    quarterly_fig = make_quarterly_chart(df_all)
    srs_fig = make_srs_chart(df_all)

    return dbc.Tab(label="Overall Trends", tab_id="tab-overall-trends", children=[
        html.P(
            "Track portfolio growth over time using yearly and quarterly views, alongside the spread of accredited researchers per project.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col(
                chart_wrapper(
                    dcc.Graph(
                        id="overall-yearly-chart",
                        figure=yearly_fig,
                        config=CHART_CONFIG,
                    ),
                    "overall-yearly-chart",
                ),
                width=12,
            ),
        ]),
        dbc.Row([
            dbc.Col(
                chart_wrapper(
                    dcc.Graph(
                        id="overall-quarterly-chart",
                        figure=quarterly_fig,
                        config=CHART_CONFIG,
                    ),
                    "overall-quarterly-chart",
                ),
                md=6,
            ),
            dbc.Col(
                chart_wrapper(
                    dcc.Graph(
                        id="overall-srs-chart",
                        figure=srs_fig,
                        config=CHART_CONFIG,
                    ),
                    "overall-srs-chart",
                ),
                md=6,
            ),
        ]),
    ])
