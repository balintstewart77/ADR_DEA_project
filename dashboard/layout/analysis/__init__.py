"""Portfolio Analysis tab — assembles sub-tabs."""

from dash import html
import dash_bootstrap_components as dbc

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
            html.P([
                html.Strong("Chart interactions: "),
                "click legend labels to hide or show a series; double-click a legend label to isolate it; "
                "drag to zoom; double-click the plot area to reset.",
            ], className="chart-interaction-hint"),
            html.Div("Choose an analysis view", className="analysis-tabs-label"),
            dbc.Tabs(
                [build_trends_tab(), build_datasets_tab(), build_institutions_tab(), build_thematic_tab()],
                id="analysis-tabs",
                active_tab="tab-overall-trends",
                className="analysis-tabs analysis-shell",
            ),
        ], className="analysis-panel"),
    ])
