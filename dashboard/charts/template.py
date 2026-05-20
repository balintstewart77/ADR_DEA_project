"""Plotly template and shared chart helpers."""

import plotly.graph_objects as go
import plotly.io as pio


# Shared template for all charts -- consistent look with minimal clutter
_template = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            size=13,
            color="#2c3e50",
        ),
        title=dict(
            font=dict(size=15, color="#2c3e50"),
            x=0.01, xanchor="left",
            y=0.97, yanchor="top",
            yref="container",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=56, r=24, t=80, b=48),
        xaxis=dict(
            gridcolor="#ecf0f1",
            linecolor="#bdc3c7",
            linewidth=1,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#ecf0f1",
            linecolor="#bdc3c7",
            linewidth=1,
            showgrid=True,
            zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#ecf0f1",
            borderwidth=1,
            font=dict(size=11),
            orientation="h",
            yanchor="bottom", y=1.08,
            xanchor="left", x=0,
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#bdc3c7",
            font_size=12,
        ),
    )
)
pio.templates["dea"] = _template
pio.templates.default = "dea"

CHART_HEIGHT = 400
CHART_CONFIG = {"displayModeBar": False}


def _apply_common(fig: go.Figure, height: int = CHART_HEIGHT) -> go.Figure:
    """Apply shared styling to any figure."""
    fig.update_layout(height=height)
    return fig


def _annotate_partial_year(fig: go.Figure, years=None, partial_year_info=None) -> go.Figure:
    """Add a footnote and asterisked x-tick for the partial final year."""
    if not partial_year_info or not partial_year_info.year:
        return fig
    if years is not None:
        tickvals = sorted(years)
        ticktext = [f"{yr}*" if yr == partial_year_info.year else str(yr) for yr in tickvals]
        fig.update_xaxes(tickvals=tickvals, ticktext=ticktext)
    fig.add_annotation(
        text=partial_year_info.note,
        xref="paper", yref="paper",
        x=1, y=-0.12, showarrow=False,
        font=dict(size=10, color="#7f8c8d"),
        xanchor="right",
    )
    return fig


def _metric_labels(metric_mode: str) -> tuple[str, str]:
    if metric_mode == "requests":
        return "Dataset access requests", "requests"
    return "Distinct projects", "projects"
