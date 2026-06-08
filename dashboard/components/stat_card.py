"""Stat card factory component."""

from dash import html
import dash_bootstrap_components as dbc


def stat_card(value, label, accent, icon=None):
    body_children = []
    if icon:
        body_children.append(
            html.Div([
                html.Span(icon, className="stat-icon", **{"aria-hidden": "true"}),
                html.Div(str(value), className="stat-number"),
            ], className="stat-value-row")
        )
    else:
        body_children.append(html.Div(str(value), className="stat-number"))
    body_children.append(html.P(label, className="stat-label"))

    return dbc.Col(
        dbc.Card(
            dbc.CardBody(body_children),
            className="stat-card",
            style={"--accent-color": accent},
        ),
        className="col-auto",
    )
