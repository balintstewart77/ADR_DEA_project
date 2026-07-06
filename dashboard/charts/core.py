"""Core chart functions: quarterly, yearly, SRS."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.charts.template import _apply_common, _annotate_partial_year
from dashboard.config import PRIMARY_BAR, SECONDARY_BAR


def make_quarterly_chart(df: pd.DataFrame) -> go.Figure:
    counts = (
        df.groupby("quarter_date")["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig = px.bar(
        counts, x="quarter_date", y="Projects",
        title="New DEA-Accredited Projects by Quarter",
        labels={"quarter_date": "Quarter", "Projects": "New projects"},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig.update_layout(xaxis_tickformat="%b %Y", bargap=0.15)
    fig.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y} projects<extra></extra>",
    )
    return _apply_common(fig)


def make_yearly_chart(df: pd.DataFrame, partial_year_info=None) -> go.Figure:
    yearly = df.groupby("Year")["Project ID"].count().reset_index()
    yearly.columns = ["Year", "Projects"]
    # Use a lighter colour for the partial final year
    colours = [
        SECONDARY_BAR if (not partial_year_info or yr != partial_year_info.year) else "#f4a582"
        for yr in yearly["Year"]
    ]
    fig = go.Figure(go.Bar(
        x=yearly["Year"], y=yearly["Projects"],
        marker_color=colours,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>%{y} projects<extra></extra>",
    ))
    fig.update_layout(
        title="New DEA Projects by Year",
        xaxis_title="Year", yaxis_title="Projects",
        bargap=0.25, xaxis_dtick=1,
    )
    _annotate_partial_year(fig, years=yearly["Year"], partial_year_info=partial_year_info)
    return _apply_common(fig)


def make_srs_chart(df: pd.DataFrame) -> go.Figure:
    srs = (
        df["Secure Research Service"]
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .reset_index()
    )
    srs.columns = ["SRS", "Count"]

    fig = px.pie(
        srs, names="SRS", values="Count",
        title="Projects by Trusted Research Environment Provider",
        color_discrete_sequence=["#2a9d8f", "#264653", "#e9c46a", "#e76f51", "#f4a261",
                                 "#606c38", "#457b9d", "#bc6c25", "#8d99ae"],
    )
    fig.update_traces(
        textposition="inside",
        texttemplate="%{label}<br>%{percent:.0%}",
        insidetextorientation="horizontal",
        hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent:.0%})<extra></extra>",
        textfont_size=12,
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=8, r=8, t=56, b=8),
    )
    return _apply_common(fig)
