"""Thematic analysis chart functions."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.charts.template import CHART_HEIGHT, _apply_common, _annotate_partial_year
from dashboard.data.deterministic import display_deterministic_value


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


def make_tag_domain_bar(
    df_totals: pd.DataFrame,
    colour_map: dict,
    title: str,
    metric: str = "count",
    height: int = 440,
) -> go.Figure:
    """Tagged-projects-by-domain bar with count / %-of-domain metric.

    The percentage denominator is the number of classified projects carrying
    that domain, so large domains stop dominating purely through size. The
    hover always shows both readings.
    """
    fig = go.Figure()
    if df_totals.empty or "domain" not in df_totals.columns:
        return _apply_common(fig, height=height)
    show_pct = metric == "pct"
    value_col = "pct_of_domain" if show_pct else "count"
    df_sorted = df_totals.sort_values(value_col, ascending=True, kind="stable")
    colours = [colour_map.get(domain, "#999") for domain in df_sorted["domain"]]
    customdata = df_sorted[["count", "domain_total", "pct_of_domain"]].to_numpy()
    fig.add_trace(go.Bar(
        y=df_sorted["domain"],
        x=df_sorted[value_col],
        orientation="h",
        marker_color=colours,
        marker_line_width=0,
        customdata=customdata,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "%{customdata[0]} tagged projects of %{customdata[1]} in domain<br>"
            "%{customdata[2]:.1f}% of domain's projects"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title=title,
        xaxis_title="% of domain's projects" if show_pct else "Projects",
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
        margin=dict(l=130, r=28, t=92, b=48),
    )
    if multi_count:
        fig.add_annotation(
            text="Multi-count: a project can appear under more than one value.",
            xref="paper",
            yref="paper",
            x=0,
            y=1.08,
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
        ),
        margin=dict(r=160, t=112, b=56),
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
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=230, r=80, t=112, b=56),
    )
    return _apply_common(fig, height=height)


def make_researcher_sector_cooccurrence(
    matrix: pd.DataFrame,
    excluded_count: int = 0,
    height: int = 500,
) -> go.Figure:
    """Lower-triangle researcher-sector co-occurrence heatmap."""
    fig = go.Figure()
    caption = (
        "Diagonal = projects with researchers from only that sector.<br>"
        "Projects with unmapped (unclassified) organisations are excluded from this figure.<br>"
        f"Excluded projects: {excluded_count:,}."
    )
    if matrix.empty:
        fig.update_layout(
            title="Researcher Sector Co-occurrence",
            margin=dict(l=120, r=80, t=130, b=70),
        )
        fig.add_annotation(
            text=caption,
            xref="paper",
            yref="paper",
            x=0,
            y=1.12,
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(size=11, color="#7f8c8d"),
        )
        return _apply_common(fig, height=height)

    sectors = list(matrix.index)
    display_sectors = [display_deterministic_value(sector) for sector in sectors]
    counts = matrix.loc[sectors, sectors].to_numpy(dtype=float)
    lower_mask = np.tri(len(sectors), dtype=bool)
    z = counts.copy()
    z[~lower_mask] = np.nan
    z_hi = np.nanmax(z) if np.isfinite(z).any() else 0

    annotations = []
    for i, row_sector in enumerate(sectors):
        for j, col_sector in enumerate(sectors):
            if not lower_mask[i][j] or not np.isfinite(z[i][j]):
                continue
            value = int(z[i][j])
            if value == 0:
                continue
            annotations.append(dict(
                x=display_deterministic_value(col_sector),
                y=display_deterministic_value(row_sector),
                text=str(value),
                showarrow=False,
                font=dict(size=12, color="white" if value > z_hi * 0.55 else "#2c3e50"),
            ))

    fig.add_trace(go.Heatmap(
        z=z,
        x=display_sectors,
        y=display_sectors,
        colorscale="Tealgrn",
        showscale=True,
        hoverongaps=False,
        colorbar=dict(title="Projects"),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>%{z:.0f} projects<extra></extra>",
    ))
    fig.update_layout(
        title="Researcher Sector Co-occurrence",
        annotations=annotations,
        xaxis=dict(side="bottom", tickangle=-25, automargin=True),
        yaxis=dict(autorange="reversed", automargin=True),
        margin=dict(l=120, r=80, t=130, b=70),
    )
    fig.add_annotation(
        text=caption,
        xref="paper",
        yref="paper",
        x=0,
        y=1.12,
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font=dict(size=11, color="#7f8c8d"),
    )
    return _apply_common(fig, height=height)


def make_latent_demand_cooccurrence(
    cooc: pd.DataFrame,
    served_pairs: frozenset,
    metric: str = "count",
    height: int | None = None,
) -> go.Figure:
    """Domain co-occurrence over NO-LINKAGE projects, with served-pair overlay.

    MIXED-LAYER figure: domains are LLM-inferred (unvalidated), the no-linkage
    filter is deterministic. ``served_pairs`` is a set of frozenset domain
    pairs covered by an existing linked product's component domains; those
    cells get a coloured outline. The diagonal (single-domain projects) is
    excluded — the object of interest is pairs. ``metric`` mirrors
    ``make_domain_cooccurrence``: counts or row-wise share P(column | row).
    """
    if cooc.empty:
        return _apply_common(go.Figure(), height=height or 620)
    domains = list(cooc.index)
    if height is None:
        height = 240 + 44 * len(domains)
    counts = cooc.to_numpy(dtype=float).copy()
    np.fill_diagonal(counts, np.nan)
    domain_totals = cooc.attrs.get("domain_totals", {})
    totals = np.array([
        float(domain_totals.get(domain, np.nansum(counts[i])))
        for i, domain in enumerate(domains)
    ])
    pct = np.divide(counts * 100, totals[:, None], out=np.full_like(counts, np.nan), where=totals[:, None] != 0)

    show_pct = metric == "pct"
    z = pct if show_pct else counts
    z_hi = np.nanmax(z) if np.isfinite(z).any() else 0

    annotations = []
    hovertext = []
    served_shapes = []
    for i, yd in enumerate(domains):
        hover_row = []
        for j, xd in enumerate(domains):
            if i == j:
                hover_row.append(f"<b>{yd}</b><br>Diagonal excluded - pairs only")
                continue
            served = frozenset((yd, xd)) in served_pairs
            if served:
                served_shapes.append(dict(
                    type="rect",
                    xref="x",
                    yref="y",
                    x0=j - 0.5,
                    x1=j + 0.5,
                    y0=i - 0.5,
                    y1=i + 0.5,
                    line=dict(color="#e76f51", width=2.2),
                    fillcolor="rgba(0,0,0,0)",
                    layer="above",
                ))
            cell_count = counts[i][j]
            cell_pct = pct[i][j]
            served_note = (
                "Served by an existing linked product"
                if served else "Not served by any linked product"
            )
            hover_row.append(
                f"<b>{yd}</b> + <b>{xd}</b><br>"
                f"{cell_count:.0f} no-linkage projects carry both<br>"
                f"{cell_pct:.0f}% of {yd}<br>{served_note}"
            )
            val = z[i][j]
            if not np.isfinite(val) or val == 0:
                continue
            text = f"{cell_pct:.0f}%" if show_pct else str(int(cell_count))
            annotations.append(dict(
                x=j, y=i, text=text, showarrow=False,
                font=dict(size=10, color="white" if val > z_hi * 0.55 else "#2c3e50"),
            ))
        hovertext.append(hover_row)

    fig = go.Figure(go.Heatmap(
        z=z, x=list(range(len(domains))), y=list(range(len(domains))), text=hovertext,
        colorscale="Purples", showscale=True, hoverongaps=False,
        colorbar=dict(title="% of row domain" if show_pct else "Projects"),
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="markers",
        marker=dict(symbol="square-open", size=13, color="#e76f51", line_width=2),
        name="Outlined = domain-pair served by an existing linked product",
        hoverinfo="skip",
        showlegend=True,
    ))
    fig.update_layout(
        title="Latent Cross-Domain Demand (projects without record linkage)",
        annotations=annotations,
        shapes=served_shapes,
        xaxis=dict(
            side="bottom",
            tickangle=-35,
            automargin=True,
            tickmode="array",
            tickvals=list(range(len(domains))),
            ticktext=domains,
        ),
        yaxis=dict(
            autorange="reversed",
            tickmode="array",
            tickvals=list(range(len(domains))),
            ticktext=domains,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.10,
            xanchor="left", x=0,
        ),
        margin=dict(l=240, t=150, b=190),
    )
    fig.add_annotation(
        text="Diagonal (single-domain projects) excluded — the object of interest is domain pairs.",
        xref="paper",
        yref="paper",
        x=0,
        y=1.06,
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font=dict(size=11, color="#7f8c8d"),
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

    ``cooc`` is a square matrix whose diagonal holds projects with only that
    domain and whose off-diagonal cells hold the number of projects carrying both
    domains. ``metric`` ("count" | "pct") switches cells between counts and the
    row-wise share P(column | row), using total row-domain projects supplied in
    ``cooc.attrs["domain_totals"]`` where available. The hover shows both.
    """
    if cooc.empty:
        return _apply_common(go.Figure(), height=height or 620)
    domains = list(cooc.index)
    if height is None:
        # tall enough that every domain row labels without Plotly thinning them
        height = 240 + 44 * len(domains)
    counts = cooc.to_numpy(dtype=float)
    domain_totals = cooc.attrs.get("domain_totals", {})
    totals = np.array([
        float(domain_totals.get(domain, counts[i].sum()))
        for i, domain in enumerate(domains)
    ])
    pct = np.divide(counts * 100, totals[:, None], out=np.zeros_like(counts), where=totals[:, None] != 0)

    show_pct = metric == "pct"
    z = pct if show_pct else counts
    z_hi = np.nanmax(z) if np.isfinite(z).any() else 0

    annotations = []
    hovertext = []
    for i, yd in enumerate(domains):
        hover_row = []
        for j, xd in enumerate(domains):
            val = z[i][j]
            cell_count = counts[i][j]
            cell_pct = pct[i][j]
            if i == j:
                hover_row.append(
                    f"<b>{yd}</b><br>"
                    f"{cell_count:.0f} projects with only this domain<br>"
                    f"{cell_pct:.0f}% of {yd}"
                )
            else:
                hover_row.append(
                    f"<b>{yd}</b> + <b>{xd}</b><br>"
                    f"{cell_count:.0f} projects carry both<br>"
                    f"{cell_pct:.0f}% of {yd}"
                )
            if not np.isfinite(val) or val == 0:
                continue
            text = f"{cell_pct:.0f}%" if show_pct else str(int(cell_count))
            annotations.append(dict(
                x=xd, y=yd, text=text, showarrow=False,
                font=dict(size=10, color="white" if val > z_hi * 0.55 else "#2c3e50"),
            ))
        hovertext.append(hover_row)

    fig = go.Figure(go.Heatmap(
        z=z, x=domains, y=domains, text=hovertext,
        colorscale=colorscale, showscale=True, hoverongaps=False,
        colorbar=dict(title="% of row domain" if show_pct else "Projects"),
        hovertemplate="%{text}<extra></extra>",
    ))
    fig.update_layout(
        title="Domain Co-occurrence",
        annotations=annotations,
        xaxis=dict(side="bottom", tickangle=-35, automargin=True, tickmode="linear", tick0=0, dtick=1),
        yaxis=dict(autorange="reversed", tickmode="linear", tick0=0, dtick=1),
        margin=dict(l=240, t=132, b=190),
    )
    fig.add_annotation(
        text="Diagonal = projects with only that domain.",
        xref="paper",
        yref="paper",
        x=0,
        y=1.10,
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font=dict(size=11, color="#7f8c8d"),
    )
    return _apply_common(fig, height=height)
