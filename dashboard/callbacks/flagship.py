"""Cross-domain linked dataset (flagship) callbacks."""

import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output

from dashboard.config import PRIMARY_BAR, SECONDARY_BAR
from dashboard.charts.template import _apply_common, _annotate_partial_year, _metric_labels
from dashboard.charts.collections import (
    make_collection_line_chart, make_collection_yearly_line_chart,
    make_collection_totals_chart, make_cumulative_chart,
)
from dashboard.data.registry import (
    df_flagship_projects, df_flagship_requests, PARTIAL_YEAR_INFO,
)


def register(app):
    @app.callback(
        Output("flagship-pooled-yearly", "figure"),
        Output("flagship-pooled-quarterly", "figure"),
        Output("flagship-line-yearly-chart", "figure"),
        Output("flagship-line-quarterly-chart", "figure"),
        Output("flagship-totals-chart", "figure"),
        Output("flagship-cumulative-chart", "figure"),
        Input("collection-filter", "value"),
        Input("flagship-metric-mode", "value"),
    )
    def update_flagship(selected_collections, metric_mode):
        df_flagship = df_flagship_projects if metric_mode == "projects" else df_flagship_requests
        metric_label, title_noun = _metric_labels(metric_mode)

        if not len(df_flagship):
            empty = go.Figure().update_layout(title="No cross-domain linked data available")
            return empty, empty, empty, empty, empty, empty

        sub = df_flagship
        if selected_collections:
            sub = df_flagship[df_flagship["collection"].isin(selected_collections)]

        # Pooled yearly across all filtered collections
        if metric_mode == "projects":
            pooled_yearly = (
                sub.groupby("Year")["Project Row ID"]
                .nunique()
                .reset_index()
                .rename(columns={"Project Row ID": "Value"})
            )
        else:
            pooled_yearly = (
                sub.groupby("Year")
                .size()
                .reset_index()
                .rename(columns={0: "Value"})
            )
        year_colours = [
            SECONDARY_BAR if yr != PARTIAL_YEAR_INFO.year else "#f4a582"
            for yr in pooled_yearly["Year"]
        ]
        fig_pooled_yearly = go.Figure(go.Bar(
            x=pooled_yearly["Year"], y=pooled_yearly["Value"],
            marker_color=year_colours,
            marker_line_width=0,
            hovertemplate=f"<b>%{{x}}</b><br>%{{y}} {title_noun}<extra></extra>",
        ))
        fig_pooled_yearly.update_layout(
            title=f"All Cross-Domain Linked {metric_label} by Year",
            xaxis_title="Year",
            yaxis_title=metric_label,
            bargap=0.25,
            xaxis_dtick=1,
        )
        _annotate_partial_year(fig_pooled_yearly, years=pooled_yearly["Year"], partial_year_info=PARTIAL_YEAR_INFO)
        _apply_common(fig_pooled_yearly)

        # Pooled quarterly across all filtered collections
        if metric_mode == "projects":
            pooled = (
                sub.groupby("quarter_date")["Project Row ID"]
                .nunique()
                .reset_index()
                .rename(columns={"Project Row ID": "Value"})
            )
        else:
            pooled = (
                sub.groupby("quarter_date")
                .size()
                .reset_index()
                .rename(columns={0: "Value"})
            )
        fig_pooled = px.bar(
            pooled, x="quarter_date", y="Value",
            title=f"All Cross-Domain Linked {metric_label} by Quarter (Pooled)",
            labels={"quarter_date": "Quarter", "Value": metric_label},
            color_discrete_sequence=[PRIMARY_BAR],
        )
        fig_pooled.update_layout(xaxis_tickformat="%b %Y", bargap=0.15)
        fig_pooled.update_traces(
            marker_line_width=0,
            hovertemplate=f"<b>%{{x|%b %Y}}</b><br>%{{y}} {title_noun}<extra></extra>",
        )
        _apply_common(fig_pooled)

        return (
            fig_pooled_yearly,
            fig_pooled,
            make_collection_yearly_line_chart(sub, metric_mode, partial_year_info=PARTIAL_YEAR_INFO),
            make_collection_line_chart(sub, metric_mode),
            make_collection_totals_chart(sub, metric_mode),
            make_cumulative_chart(df_flagship, selected_collections or [], metric_mode),
        )
