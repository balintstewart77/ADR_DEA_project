"""Collection chart functions: line, yearly line, totals, cumulative."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.charts.template import CHART_HEIGHT, _apply_common, _annotate_partial_year, _metric_labels
from dashboard.config import COLLECTION_COLOURS


def make_collection_line_chart(df_flag: pd.DataFrame, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    counts = (
        df_flag.groupby(["quarter_date", "collection"])
        .size()
        .reset_index()
        .rename(columns={0: "Value"})
    )
    fig = px.line(
        counts, x="quarter_date", y="Value", color="collection",
        title=f"Cross-Domain Linked {metric_label} by Quarter",
        labels={"quarter_date": "Quarter", "Value": metric_label, "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
        markers=True,
    )
    fig.update_layout(xaxis_tickformat="%b %Y")
    fig.update_traces(
        line_width=2.5,
        marker_size=6,
        hovertemplate=f"<b>%{{fullData.name}}</b><br>%{{x|%b %Y}}<br>%{{y}} {title_noun}<extra></extra>",
    )
    return _apply_common(fig, height=CHART_HEIGHT + 20)


def make_collection_yearly_line_chart(df_flag: pd.DataFrame, metric_mode: str, partial_year_info=None) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    counts = (
        df_flag.groupby(["Year", "collection"])
        .size()
        .reset_index()
        .rename(columns={0: "Value"})
    )
    fig = px.line(
        counts, x="Year", y="Value", color="collection",
        title=f"Cross-Domain Linked {metric_label} by Year",
        labels={"Year": "Year", "Value": metric_label, "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
        markers=True,
    )
    fig.update_layout(xaxis_dtick=1)
    fig.update_traces(
        line_width=2.5,
        marker_size=6,
        hovertemplate=f"<b>%{{fullData.name}}</b><br>%{{x}}<br>%{{y}} {title_noun}<extra></extra>",
    )
    _annotate_partial_year(fig, years=counts["Year"].unique(), partial_year_info=partial_year_info)
    return _apply_common(fig, height=CHART_HEIGHT + 20)


def make_collection_totals_chart(df_flag: pd.DataFrame, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    totals = (
        df_flag.groupby("collection")
        .size()
        .reset_index()
        .rename(columns={0: "Value"})
        .sort_values("Value", ascending=True)
    )
    fig = px.bar(
        totals, x="Value", y="collection", orientation="h",
        title=f"Total Cross-Domain Linked {metric_label} per Collection",
        labels={"collection": "", "Value": metric_label},
        color="collection",
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(showlegend=False, yaxis_tickfont_size=12, margin=dict(l=220))
    fig.update_traces(
        marker_line_width=0,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x}} {title_noun}<extra></extra>",
    )
    return _apply_common(fig)


def make_cumulative_chart(df_flag: pd.DataFrame, selected_collections: list, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    sub = df_flag if not selected_collections else df_flag[df_flag["collection"].isin(selected_collections)]
    counts = (
        sub.groupby(["quarter_date", "collection"])
        .size()
        .reset_index()
        .rename(columns={0: "New"})
    )
    counts = counts.sort_values("quarter_date")
    counts["Cumulative"] = counts.groupby("collection")["New"].cumsum()
    fig = px.area(
        counts, x="quarter_date", y="Cumulative", color="collection",
        title=f"Cumulative Cross-Domain Linked {metric_label}",
        labels={"quarter_date": "Quarter", "Cumulative": f"Cumulative {title_noun}", "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(
        xaxis_tickformat="%b %Y",
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=160),
    )
    fig.update_traces(
        line_width=2,
        hovertemplate=f"<b>%{{fullData.name}}</b><br>%{{x|%b %Y}}<br>%{{y}} cumulative {title_noun}<extra></extra>",
    )
    return _apply_common(fig)
