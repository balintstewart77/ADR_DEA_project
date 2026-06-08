"""Thematic analysis chart functions."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.charts.template import CHART_HEIGHT, _apply_common, _annotate_partial_year


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


def make_compact_distribution_bar(
    df_totals: pd.DataFrame,
    category_col: str,
    title: str,
    multi_count: bool = False,
    height: int = 280,
) -> go.Figure:
    """Compact horizontal distribution bar for deterministic facet totals."""
    fig = go.Figure()
    if not df_totals.empty and category_col in df_totals.columns and "count" in df_totals.columns:
        df_sorted = df_totals.sort_values("count", ascending=True, kind="stable")
        palette = ["#4c78a8", "#f58518", "#54a24b", "#b279a2", "#72b7b2", "#e45756"]
        colours = [palette[i % len(palette)] for i in range(len(df_sorted))]
        fig.add_trace(go.Bar(
            y=df_sorted[category_col],
            x=df_sorted["count"],
            orientation="h",
            marker_color=colours,
            marker_line_width=0,
            text=df_sorted["count"],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x} projects<extra></extra>",
        ))
    fig.update_layout(
        title=title,
        xaxis_title="Projects",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=130, r=28, t=72, b=54),
    )
    if multi_count:
        fig.add_annotation(
            text="Multi-count: a project can appear under more than one value.",
            xref="paper",
            yref="paper",
            x=0,
            y=-0.18,
            showarrow=False,
            xanchor="left",
            font=dict(size=10, color="#7f8c8d"),
        )
    return _apply_common(fig, height=height)


def make_record_linkage_trend(
    df_by_year: pd.DataFrame,
    metric: str = "pct",
    height: int = 360,
    partial_year_info=None,
) -> go.Figure:
    """Stacked area trend for record-linkage span by year."""
    fig = go.Figure()
    if df_by_year.empty:
        return _apply_common(fig, height=height)

    metric_col = "pct_of_projects" if metric == "pct" else "count"
    linkage_order = ["No record linkage", "Within-domain", "Cross-domain"]
    colours = {
        "No record linkage": "#8d99ae",
        "Within-domain": "#2a9d8f",
        "Cross-domain": "#e76f51",
    }
    for linkage in linkage_order:
        sub = df_by_year[df_by_year["record_linkage"] == linkage].sort_values("Year")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["Year"],
            y=sub[metric_col],
            name=linkage,
            mode="lines",
            stackgroup="one",
            line=dict(color=colours.get(linkage, "#999999"), width=1.5),
            fillcolor=colours.get(linkage, "#999999"),
            hovertemplate=(
                f"<b>{linkage}</b><br>%{{x}}<br>"
                + ("%{y:.1f}% of projects" if metric == "pct" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))

    fig.update_layout(
        title="Record Linkage Over Time",
        xaxis_title="Year",
        yaxis_title="% of projects" if metric == "pct" else "Projects",
        xaxis_dtick=1,
        yaxis=dict(range=[0, 100] if metric == "pct" else None),
        margin=dict(r=160),
    )
    _annotate_partial_year(fig, years=df_by_year["Year"].unique(), partial_year_info=partial_year_info)
    return _apply_common(fig, height=height)


def make_domain_record_linkage_breakdown(
    df_cross: pd.DataFrame,
    metric: str = "pct",
    height: int = 560,
) -> go.Figure:
    """Stacked horizontal domain x record-linkage breakdown."""
    fig = go.Figure()
    linkage_order = ["No record linkage", "Within-domain", "Cross-domain"]
    if df_cross.empty or "domain" not in df_cross.columns:
        return _apply_common(fig, height=height)

    value_cols = [col for col in linkage_order if col in df_cross.columns]
    if not value_cols:
        return _apply_common(fig, height=height)

    work = df_cross.copy()
    work["_total"] = work[value_cols].sum(axis=1)
    work = work.sort_values("_total", ascending=True, kind="stable")
    counts = work[value_cols].astype(float)
    pct = counts.div(work["_total"].replace(0, np.nan), axis=0).fillna(0) * 100
    colours = {
        "No record linkage": "#8d99ae",
        "Within-domain": "#2a9d8f",
        "Cross-domain": "#e76f51",
    }
    for linkage in value_cols:
        x = pct[linkage] if metric == "pct" else counts[linkage]
        customdata = np.stack([counts[linkage], pct[linkage]], axis=-1)
        fig.add_trace(go.Bar(
            y=work["domain"],
            x=x,
            name=linkage,
            orientation="h",
            marker_color=colours.get(linkage, "#999999"),
            customdata=customdata,
            hovertemplate=(
                f"<b>%{{y}}</b><br>{linkage}<br>"
                "%{customdata[0]:.0f} projects<br>"
                "%{customdata[1]:.1f}% of domain"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        title="Domain by Record Linkage",
        xaxis_title="% of domain projects" if metric == "pct" else "Projects",
        yaxis_title="",
        barmode="stack",
        xaxis=dict(range=[0, 100] if metric == "pct" else None),
        margin=dict(l=230, r=80, t=80, b=48),
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
