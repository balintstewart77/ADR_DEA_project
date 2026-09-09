"""Portfolio Analysis tab — assembles sub-tabs."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.data.registry import df_all
from dashboard.data.year_filter import year_slider_kwargs

from .trends import build_trends_tab
from .datasets import build_datasets_tab
from .institutions import build_institutions_tab
from .thematic import build_thematic_tab


def build_analysis_tab():
    return dbc.Tab(label="Portfolio Analysis", tab_id="tab-analysis", children=[
        html.Div([
            html.H5(
                "Portfolio Analysis",
                className="page-title",
            ),
            html.P(
                "Explore portfolio-level patterns through trends, dataset demand, cross-domain linked dataset uptake, institutions, and thematic analysis.",
                className="section-desc",
            ),
            dbc.Row([
                dbc.Col([
                    html.Label("Accreditation year", className="filter-label"),
                    dcc.RangeSlider(
                        id="portfolio-accreditation-year-filter",
                        **year_slider_kwargs(df_all),
                    ),
                ], md=8),
                dbc.Col([
                    html.Label("\u00a0", className="filter-label"),
                    html.Button(
                        "All years",
                        id="portfolio-year-reset",
                        className="btn btn-outline-primary btn-sm w-100",
                    ),
                ], md=2),
                dbc.Col([
                    html.Div(
                        id="portfolio-filter-summary",
                        className="text-muted small",
                        style={"paddingTop": "1.7rem"},
                    ),
                ], md=2),
            ], className="mb-2 g-2"),
            html.P(
                "All years includes records without a usable accreditation date; "
                "a restricted range excludes them. Year options always come from the "
                "full authoritative register.",
                className="section-desc text-muted small",
            ),
            html.Div("Choose an analysis view", className="analysis-tabs-label"),
            dbc.Tabs(
                [build_trends_tab(), build_datasets_tab(), build_institutions_tab(), build_thematic_tab()],
                id="analysis-tabs",
                active_tab="tab-overall-trends",
                className="analysis-tabs analysis-shell",
            ),
        ], className="analysis-panel"),
    ])
