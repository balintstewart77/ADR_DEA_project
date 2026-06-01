"""Thematic analysis chart functions."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.charts.template import CHART_HEIGHT, _apply_common, _annotate_partial_year
from dashboard.config import LINKAGE_LABELS


def make_thematic_trend(
    df_by_year: pd.DataFrame,
    category_col: str,
    colour_map: dict,
    metric_col: str,
    title: str,
    height: int = 480,
    partial_year_info=None,
) -> go.Figure:
    """Multi-line trend chart for a thematic layer (domains or purposes)."""
    fig = go.Figure()
    for cat in df_by_year[category_col].unique():
        sub = df_by_year[df_by_year[category_col] == cat].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=sub["Year"], y=sub[metric_col],
            mode="lines+markers",
            name=cat,
            line=dict(color=colour_map.get(cat, "#999"), width=2.5),
            marker=dict(size=6),
            hovertemplate=(
                f"<b>{cat}</b><br>"
                "%{x}<br>"
                + ("%{y:.1f}%" if metric_col == "pct_of_projects" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))
    yaxis_title = "% of projects" if metric_col == "pct_of_projects" else "Projects"
    fig.update_layout(
        title=title,
        xaxis_title="Year", yaxis_title=yaxis_title,
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=260),
    )
    _annotate_partial_year(fig, years=df_by_year["Year"].unique(), partial_year_info=partial_year_info)
    return _apply_common(fig, height=height)


def make_linkage_area(
    df_by_year: pd.DataFrame,
    colour_map: dict,
    metric_col: str,
    partial_year_info=None,
) -> go.Figure:
    """Stacked area chart for linkage modes (single-label, compositional)."""
    present = [m for m in LINKAGE_LABELS if m in df_by_year["linkage_mode"].values]
    fig = go.Figure()
    for mode in present:
        sub = df_by_year[df_by_year["linkage_mode"] == mode].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=sub["Year"], y=sub[metric_col],
            mode="lines",
            name=mode,
            stackgroup="one",
            line=dict(color=colour_map.get(mode, "#999"), width=0.5),
            fillcolor=colour_map.get(mode, "#999"),
            hovertemplate=(
                f"<b>{mode}</b><br>"
                "%{x}<br>"
                + ("%{y:.1f}%" if metric_col == "pct_of_projects" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))
    yaxis_title = "% of projects" if metric_col == "pct_of_projects" else "Projects"
    fig.update_layout(
        title="Data Linkage Complexity Over Time",
        xaxis_title="Year", yaxis_title=yaxis_title,
        xaxis_dtick=1,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.05,
            xanchor="left", x=0,
        ),
    )
    _annotate_partial_year(fig, years=df_by_year["Year"].unique(), partial_year_info=partial_year_info)
    return _apply_common(fig)


def make_thematic_totals_bar(
    df_totals: pd.DataFrame,
    category_col: str,
    colour_map: dict,
    title: str,
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Horizontal bar chart of total counts for a layer."""
    df_sorted = df_totals.sort_values("count", ascending=True)
    colours = [colour_map.get(cat, "#999") for cat in df_sorted[category_col]]
    fig = go.Figure(go.Bar(
        y=df_sorted[category_col],
        x=df_sorted["count"],
        orientation="h",
        marker_color=colours,
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>%{x} projects<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Projects",
        yaxis_title="",
        margin=dict(l=220),
    )
    return _apply_common(fig, height=height)


def make_cross_heatmap(
    df_cross: pd.DataFrame,
    row_col: str,
    title: str,
    colorscale: list | str = "Tealgrn",
    height: int = 380,
    metric: str = "count",
) -> go.Figure:
    """Annotated cross-tab heatmap.

    ``metric`` ("count" | "pct") sets the in-cell value and the colour basis.
    Percentages are row-wise — each cell as a share of its row (domain) total —
    and the hover always shows both the absolute count and that row percentage.
    """
    row_labels = df_cross[row_col].tolist()
    value_cols = [c for c in df_cross.columns if c != row_col]
    counts = df_cross[value_cols].to_numpy(dtype=float)
    row_totals = counts.sum(axis=1, keepdims=True)
    pct = np.divide(counts * 100, row_totals, out=np.zeros_like(counts), where=row_totals != 0)

    show_pct = metric == "pct"
    z = pct if show_pct else counts
    customdata = np.dstack([counts, pct])  # per cell: [count, row %]
    z_hi = z.max() if z.size else 0

    annotations = []
    for i, label in enumerate(row_labels):
        for j, col in enumerate(value_cols):
            text = f"{pct[i][j]:.0f}%" if show_pct else str(int(counts[i][j]))
            annotations.append(dict(
                x=col, y=label,
                text=text,
                showarrow=False,
                font=dict(
                    size=11,
                    color="white" if z[i][j] > z_hi * 0.55 else "#2c3e50",
                ),
            ))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=value_cols,
        y=row_labels,
        customdata=customdata,
        colorscale=colorscale,
        showscale=True,
        colorbar=dict(title="% of domain" if show_pct else "Projects"),
        hovertemplate=(
            "<b>%{y}</b> × <b>%{x}</b><br>"
            "%{customdata[0]:.0f} projects<br>"
            "%{customdata[1]:.0f}% of %{y}"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=title,
        annotations=annotations,
        xaxis=dict(side="bottom", tickangle=-35, automargin=True),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=220, b=165),
    )
    return _apply_common(fig, height=height)
