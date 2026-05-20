"""
DEA Accredited Projects Dashboard
===================================
Interactive Dash app for exploring access requests under the Digital Economy Act,
focusing on cross-domain linked datasets.

Run with:
    python dashboard/app.py

Then open http://127.0.0.1:8050 in your browser.
"""

import os
import sys

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_PACKAGE_DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from dash import Dash, dcc, html
import dash_bootstrap_components as dbc

from dashboard.data import registry
from dashboard.layout.navbar import build_navbar
from dashboard.layout.overview import build_stat_cards, build_overview_tab
from dashboard.layout.explorer import build_explorer_tab
from dashboard.layout.analysis import build_analysis_tab
from dashboard.layout.about import build_about_tab
from dashboard.callbacks import register_callbacks

app = Dash(
    "dashboard",
    assets_folder=os.path.join(_PACKAGE_DIR, "assets"),
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="DEA Projects Dashboard",
)
server = app.server

app.layout = html.Div([
    build_navbar(),
    dcc.Download(id="browse-download-csv"),
    dcc.Download(id="enriched-download-csv"),
    dbc.Container([
        html.Div(style={"height": "1.25rem"}),
        build_stat_cards(),
        dbc.Tabs(
            [
                build_overview_tab(),
                build_explorer_tab(),
                build_analysis_tab(),
                build_about_tab(),
            ],
            id="main-tabs",
            active_tab="tab-overview",
            className="dea-tabs",
        ),
        html.Footer(
            f"DEA Accredited Projects Dashboard  •  Data sourced from UKSA  •  "
            f"Last updated {registry.DATA_DATE}",
            className="dea-footer",
        ),
    ], fluid=True),
])

register_callbacks(app)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(
        debug=debug_mode,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8050)),
    )
