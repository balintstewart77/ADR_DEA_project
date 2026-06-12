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
    df_product_by_year: pd.DataFrame,
    products: list[str],
    short_by_product: dict[str, str],
    span_by_product: dict[str, str],
    metric: str = "count",
    height: int = 460,
    partial_year_info=None,
) -> go.Figure:
    """Per-product adoption curves: projects per year for each linked product.

    Cross-domain products draw solid, within-domain dashed, so the two kinds
    stay distinguishable however many products are selected.
    """
    fig = go.Figure()
    metric_col = "pct_of_projects" if metric == "pct" else "count"
    for i, product in enumerate(products):
        sub = df_product_by_year[df_product_by_year["product"] == product].sort_values("Year")
        if sub.empty:
            continue
        span = span_by_product.get(product, "Within-domain")
        short = short_by_product.get(product, product)
        fig.add_trace(go.Scatter(
            x=sub["Year"], y=sub[metric_col],
            mode="lines+markers",
            name=f"{short} ({span.lower()})",
            line=dict(
                color=_PRODUCT_PALETTE[i % len(_PRODUCT_PALETTE)],
                width=2.5,
                dash="solid" if span == "Cross-domain" else "dash",
            ),
            marker=dict(size=6),
            hovertemplate=(
                f"<b>{product}</b><br>{span} product<br>%{{x}}<br>"
                + ("%{y:.1f}% of year's projects" if metric == "pct" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))
    fig.update_layout(
        title="Linked-Product Adoption Curves",
        xaxis_title="Year",
        yaxis_title="% of year's projects" if metric == "pct" else "Projects",
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=240, t=96),
    )
    fig.add_annotation(
        text="Solid = cross-domain product; dashed = within-domain product.",
        xref="paper", yref="paper",
        x=0, y=1.07, showarrow=False,
        xanchor="left", yanchor="bottom",
        font=dict(size=10, color="#7f8c8d"),
    )
    _annotate_partial_year(
        fig, years=df_product_by_year["Year"].unique(), partial_year_info=partial_year_info,
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
