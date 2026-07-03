"""Linked-data uptake chart functions (deterministic layer)."""

import plotly.graph_objects as go
import pandas as pd

from dashboard.charts.template import _apply_common, _annotate_partial_year

# Fixed palette keyed by adoption rank so colours are stable for a given run.
_PRODUCT_PALETTE = [
    "#1f77b4", "#e76f51", "#2a9d8f", "#9467bd", "#f4a261", "#264653",
    "#d62728", "#8c564b", "#0099c6", "#bcbd22", "#e377c2", "#7f7f7f",
    "#109618", "#dc3912", "#3366cc", "#ff9900", "#6a3d9a", "#54a24b",
    "#b279a2", "#72b7b2",
]


def make_adoption_curves(
    df_adoption: pd.DataFrame,
    metric: str = "count",
    granularity: str = "year",
    height: int = 460,
    partial_year_info=None,
    collection_view: str = "individual",
) -> go.Figure:
    """Per-product adoption curves for each linked product.

    Cross-domain products draw solid, within-domain dashed, so the two kinds
    stay distinguishable however many products are selected. The data frame is
    already clipped so each product starts at its availability period.
    """
    fig = go.Figure()
    if df_adoption.empty:
        return _apply_common(fig, height=height)
    metric_col = "pct_of_projects" if metric == "pct" else "count"
    x_col = "period_label" if "period_label" in df_adoption.columns else "Year"
    period_label = "Quarter" if granularity == "quarter" else "Year"
    share_label = "% of quarter's projects" if granularity == "quarter" else "% of year's projects"
    category_order = []
    if x_col == "period_label" and "period_date" in df_adoption.columns:
        category_order = (
            df_adoption[["period_label", "period_date"]]
            .drop_duplicates()
            .sort_values("period_date", kind="stable")["period_label"]
            .astype(str)
            .tolist()
        )
    line_ids = list(dict.fromkeys(df_adoption["line_id"].dropna().astype(str)))
    for i, line_id in enumerate(line_ids):
        sort_cols = [
            col for col in ["period_date", "Year", "period_label"]
            if col in df_adoption.columns
        ]
        sub = df_adoption[df_adoption["line_id"].astype(str) == line_id].sort_values(sort_cols)
        if sub.empty:
            continue
        span = str(sub["line_linkage_span"].iloc[0])
        label = str(sub["line_label"].iloc[0])
        group = str(sub["line_group"].iloc[0])
        name = label if group == "ADR England flagship" else f"{label} (other)"
        dash = "solid" if span == "Cross-domain" else "dash" if span == "Within-domain" else "dot"
        fig.add_trace(go.Scatter(
            x=sub[x_col], y=sub[metric_col],
            mode="lines+markers",
            name=name,
            line=dict(
                color=_PRODUCT_PALETTE[i % len(_PRODUCT_PALETTE)],
                width=2.5,
                dash=dash,
            ),
            marker=dict(size=6),
            customdata=sub[["line_group", "line_linkage_span"]].to_numpy(),
            hovertemplate=(
                f"<b>{name}</b><br>"
                "%{customdata[0]}<br>"
                "%{customdata[1]} linked product span<br>"
                "%{x}<br>"
                + (f"%{{y:.1f}}{share_label}" if metric == "pct" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))
    fig.update_layout(
        title="Linked-Product Adoption Curves",
        xaxis_title=period_label,
        yaxis_title=share_label if metric == "pct" else "Projects",
        xaxis=dict(
            dtick=1 if granularity == "year" else None,
            tickangle=-35 if granularity == "quarter" else 0,
            type="category" if x_col == "period_label" else None,
            categoryorder="array" if category_order else None,
            categoryarray=category_order if category_order else None,
        ),
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=240, t=96),
    )
    if collection_view == "grouped":
        note = (
            "Reference-defined collections are de-duplicated to one project per collection. "
            "Lines begin at the earliest selected member availability. DEA-gateway use only."
        )
    else:
        note = (
            "Selected linked datasets shown individually. Lines begin at each dataset's "
            "availability. DEA-gateway use only. Solid = cross-domain; dashed = within-domain."
        )
    fig.add_annotation(
        text=note,
        xref="paper", yref="paper",
        x=0, y=1.07, showarrow=False,
        xanchor="left", yanchor="bottom",
        font=dict(size=10, color="#7f8c8d"),
    )
    if granularity == "year" and "Year" in df_adoption.columns:
        _annotate_partial_year(
            fig, years=df_adoption["Year"].unique(), partial_year_info=partial_year_info,
        )
    return _apply_common(fig, height=height)


def make_exposure_rate_bar(
    product_summary: pd.DataFrame,
    height: int = 520,
) -> go.Figure:
    """Projects per exposure-year by linked product, with exposure shown."""
    fig = go.Figure()
    if product_summary.empty:
        return _apply_common(fig, height=height)
    work = product_summary.copy()
    work = work[work["projects_per_exposure_year"].notna()].copy()
    if work.empty:
        return _apply_common(fig, height=height)
    work = work.sort_values("projects_per_exposure_year", ascending=True, kind="stable")
    colours = work["is_adr_england_flagship"].map({
        True: "#2a9d8f",
        False: "#8d99ae",
    }).tolist()
    fig.add_trace(go.Bar(
        y=work["short"],
        x=work["projects_per_exposure_year"],
        orientation="h",
        marker_color=colours,
        text=work["projects_per_exposure_year"].map(lambda value: f"{value:.1f}"),
        textposition="outside",
        cliponaxis=False,
        customdata=work[["product", "flagship_group", "total_projects", "exposure_years"]].to_numpy(),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "%{customdata[1]}<br>"
            "%{x:.1f} projects per exposure-year<br>"
            "%{customdata[2]} total projects<br>"
            "%{customdata[3]:.1f} exposure years"
            "<extra></extra>"
        ),
    ))
    fig.update_layout(
        title="Projects per Exposure-Year",
        xaxis_title="Projects per exposure-year",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=150, r=60, t=92, b=56),
    )
    fig.add_annotation(
        text=(
            "Teal = ADR England flagship; grey = Other linked datasets. "
            "Exposure-years are counted from availability within the register window; "
            "short exposures are initial-adoption rates."
        ),
        xref="paper", yref="paper",
        x=0, y=1.08, showarrow=False,
        xanchor="left", yanchor="bottom",
        font=dict(size=10, color="#7f8c8d"),
    )
    return _apply_common(fig, height=height)


def add_availability_annotations(
    fig: go.Figure,
    annotations: list[dict],
    min_x: float | None = None,
) -> go.Figure:
    """Overlay product-availability vertical lines on a by-year trend figure.

    Each annotation dict carries ``year_fraction``, ``short`` and ``basis``
    ("available" for a curated date, "first register appearance" for the
    empirical proxy) — the label keeps that distinction visible. Dates before
    ``min_x`` are pinned to the left edge and labelled as pre-window rather
    than stretching the axis back decades.
    """
    seen_x: dict[float, int] = {}
    for spec in annotations:
        x = spec["year_fraction"]
        label = f"{spec['short']} ({spec['basis']})"
        if min_x is not None and x < min_x:
            label = f"{spec['short']} (available pre-{int(min_x)})"
            x = min_x
        collisions = seen_x.get(x, 0)
        seen_x[x] = collisions + 1
        fig.add_shape(
            type="line",
            x0=x, x1=x, y0=0, y1=1,
            yref="paper",
            line=dict(color="#5c677d", width=1, dash="dot"),
        )
        fig.add_annotation(
            x=x, y=1, yref="paper",
            text=label,
            showarrow=False,
            textangle=-90,
            xanchor="left", yanchor="top",
            xshift=11 * collisions,  # nudge labels apart when dates coincide
            font=dict(size=9, color="#5c677d"),
        )
    return fig
