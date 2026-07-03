"""Reusable chart container with compact interaction tips."""

from dash import html
import dash_bootstrap_components as dbc


CHART_TIPS = [
    "Hover over lines, bars, and cells for exact values and notes.",
    "Clicking a line or bar does not filter the dashboard.",
    "Click legend labels to hide or show a series; double-click a legend label to isolate it.",
    "Drag across the plot area to zoom; double-click the plot area to reset.",
]


def chart_wrapper(graph, graph_id: str, style: dict | None = None) -> html.Div:
    """Wrap a Dash graph with a click-to-open tips control."""
    button_id = f"{graph_id}-chart-tips"
    return html.Div(
        [
            html.Button(
                [
                    html.Span("?", className="chart-tips-icon", **{"aria-hidden": "true"}),
                    html.Span("Chart tips", className="chart-tips-label"),
                ],
                id=button_id,
                className="chart-tips-button",
                type="button",
            ),
            dbc.Popover(
                [
                    dbc.PopoverHeader("Chart tips"),
                    dbc.PopoverBody(html.Ul([html.Li(tip) for tip in CHART_TIPS], className="chart-tips-list")),
                ],
                target=button_id,
                trigger="click",
                placement="left",
                autohide=True,
            ),
            graph,
        ],
        className="chart-wrapper",
        style=style,
    )
