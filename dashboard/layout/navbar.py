"""Navbar component."""

from dash import html
import dash_bootstrap_components as dbc

from dashboard.config import FEEDBACK_EMAIL_URL, SOURCE_URL
from dashboard.data.registry import DATA_DATE, source_file


def build_navbar():
    return html.Nav(
        dbc.Container([
            html.Div([
                html.Span("DEA Accredited Projects", className="navbar-brand"),
                html.Span(" Dashboard", className="navbar-brand", style={"fontWeight": "400"}),
                html.Span("Beta", className="navbar-badge"),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div([
                html.A(
                    "Provide feedback",
                    href=FEEDBACK_EMAIL_URL,
                    target="_blank",
                    rel="noopener noreferrer",
                    className="nav-feedback-link",
                ),
                html.A(
                    "View source / report issue",
                    href=SOURCE_URL,
                    target="_blank",
                    rel="noopener noreferrer",
                    className="nav-feedback-link",
                ),
                html.Button(
                    "\U0001F50D Search Projects",
                    id="nav-search-btn",
                    className="nav-search-btn btn btn-sm me-3",
                ),
                html.Span(
                    f"Data to {DATA_DATE}  •  {source_file}",
                    className="nav-meta",
                ),
            ], className="d-flex align-items-center ms-auto"),
        ], fluid=True, className="d-flex align-items-center"),
        className="dea-navbar navbar",
    )
