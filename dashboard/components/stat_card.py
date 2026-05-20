"""Stat card factory component."""

from dash import html
import dash_bootstrap_components as dbc


def stat_card(value, label, accent):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.Div(str(value), className="stat-number"),
                html.P(label, className="stat-label"),
            ]),
            className="stat-card",
            style={"--accent-color": accent},
        ),
        className="col-auto",
    )
