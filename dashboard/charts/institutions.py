"""Institution chart functions: bar and trend."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.charts.template import _apply_common, _annotate_partial_year
from dashboard.config import PRIMARY_BAR


def make_institution_bar(df_inst: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Horizontal bar chart of top institutions by project count."""
    project_key = "Record ID" if "Record ID" in df_inst.columns else "Project ID"
    counts = (
        df_inst.groupby("institution")[project_key]
        .nunique()
        .reset_index()
        .rename(columns={project_key: "Projects"})
        .sort_values("Projects", ascending=True)
        .tail(top_n)
    )
    fig = px.bar(
        counts, x="Projects", y="institution", orientation="h",
        title=f"Top {top_n} Institutions by Number of Retained Register Entries",
        labels={"institution": "", "Projects": "Retained entries"},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{x} retained entries<extra></extra>",
    )
    fig.update_layout(
        margin=dict(l=280),
        height=max(400, top_n * 24),
        yaxis_tickfont=dict(size=11),
    )
    return _apply_common(fig, height=max(400, top_n * 24))


def make_institution_trend(df_inst: pd.DataFrame, top_n: int = 8, partial_year_info=None) -> go.Figure:
    """Line chart of projects per year for the top institutions."""
    project_key = "Record ID" if "Record ID" in df_inst.columns else "Project ID"
    top_insts = (
        df_inst.groupby("institution")[project_key]
        .nunique()
        .nlargest(top_n)
        .index.tolist()
    )
    sub = df_inst[df_inst["institution"].isin(top_insts)]
    yearly = (
        sub.groupby(["Year", "institution"])[project_key]
        .nunique()
        .reset_index()
        .rename(columns={project_key: "Projects"})
    )
    fig = px.line(
        yearly, x="Year", y="Projects", color="institution",
        title=f"Retained Entries per Year - Top {top_n} Institutions",
        labels={"institution": "Institution", "Projects": "Retained entries"},
        markers=True,
    )
    fig.update_layout(
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=200),
    )
    fig.update_traces(line_width=2.5)
    _annotate_partial_year(fig, years=yearly["Year"].unique(), partial_year_info=partial_year_info)
    return _apply_common(fig)
