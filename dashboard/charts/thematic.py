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


def make_linkage_complexity(
    df_cross_mode_domain: pd.DataFrame,
    colour_map: dict,
    height: int = 460,
) -> go.Figure:
    """Sorted 100%-stacked horizontal bars of each domain's linkage-mode profile.

    A proportional ("relative complexity") view: each bar is the share of that
    domain's projects by linkage mode, so domains compare regardless of size.
    Ordered by cross-domain share. Counts are assignment-weighted (a project is
    counted once per domain it touches).
    """
    if df_cross_mode_domain.empty or "domain" not in df_cross_mode_domain.columns:
        return _apply_common(go.Figure(), height=height)
    counts = df_cross_mode_domain.set_index("domain")
    modes = [m for m in LINKAGE_LABELS if m in counts.columns]
    counts = counts[modes]
    row_totals = counts.sum(axis=1)
    pct = counts.div(row_totals, axis=0).mul(100).fillna(0)
    cross = "Cross-Domain Linkage"
    order = (pct[cross] if cross in pct.columns else row_totals).sort_values().index.tolist()

    fig = go.Figure()
    for mode in modes:
        fig.add_trace(go.Bar(
            y=order,
            x=pct.loc[order, mode],
            name=mode,
            orientation="h",
            marker_color=colour_map.get(mode, "#999"),
            customdata=counts.loc[order, mode],
            hovertemplate=(
                "<b>%{y}</b><br>" + mode + ": %{x:.0f}% (%{customdata} projects)<extra></extra>"
            ),
        ))
    fig.update_layout(
        barmode="stack",
        title="Linkage Profile by Domain",
        xaxis=dict(title="% of the domain's projects", range=[0, 100]),
        yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        margin=dict(l=220),
    )
    return _apply_common(fig, height=height)


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


def make_domain_cooccurrence(
    cooc: pd.DataFrame,
    metric: str = "count",
    colorscale: list | str = "Greens",
    height: int | None = None,
) -> go.Figure:
    """Domain x domain co-occurrence heatmap.

    ``cooc`` is a square matrix whose diagonal holds each domain's total and whose
    off-diagonal cells hold the number of projects carrying both domains. The
    diagonal is masked. ``metric`` ("count" | "pct") switches the off-diagonal
    cells between the (symmetric) co-occurrence count and the row-wise share
    P(column | row) = co-occurrences ÷ the row domain's total. The hover shows both.
    """
    if cooc.empty:
        return _apply_common(go.Figure(), height=height or 620)
    domains = list(cooc.index)
    if height is None:
        # tall enough that every domain row labels without Plotly thinning them
        height = 240 + 44 * len(domains)
    counts = cooc.to_numpy(dtype=float)
    totals = np.diag(counts).copy()
    pct = np.divide(counts * 100, totals[:, None], out=np.zeros_like(counts), where=totals[:, None] != 0)

    mask = np.eye(len(domains), dtype=bool)
    disp_counts = counts.copy(); disp_counts[mask] = np.nan
    disp_pct = pct.copy(); disp_pct[mask] = np.nan

    show_pct = metric == "pct"
    z = disp_pct if show_pct else disp_counts
    customdata = np.dstack([disp_counts, disp_pct])
    z_hi = np.nanmax(z) if np.isfinite(z).any() else 0

    annotations = []
    for i, yd in enumerate(domains):
        for j, xd in enumerate(domains):
            val = z[i][j]
            if i == j or not np.isfinite(val) or val == 0:
                continue
            text = f"{disp_pct[i][j]:.0f}%" if show_pct else str(int(disp_counts[i][j]))
            annotations.append(dict(
                x=xd, y=yd, text=text, showarrow=False,
                font=dict(size=10, color="white" if val > z_hi * 0.55 else "#2c3e50"),
            ))

    fig = go.Figure(go.Heatmap(
        z=z, x=domains, y=domains, customdata=customdata,
        colorscale=colorscale, showscale=True, hoverongaps=False,
        colorbar=dict(title="% of row domain" if show_pct else "Projects"),
        hovertemplate=(
            "<b>%{y}</b> + <b>%{x}</b><br>"
            "%{customdata[0]:.0f} projects carry both<br>"
            "%{customdata[1]:.0f}% of %{y}"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Domain Co-occurrence",
        annotations=annotations,
        xaxis=dict(side="bottom", tickangle=-35, automargin=True, tickmode="linear", tick0=0, dtick=1),
        yaxis=dict(autorange="reversed", tickmode="linear", tick0=0, dtick=1),
        margin=dict(l=240, b=180),
    )
    return _apply_common(fig, height=height)
