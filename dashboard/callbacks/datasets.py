"""Dataset Demand callbacks."""

from textwrap import wrap

import pandas as pd
import plotly.express as px
from dash import Input, Output

from dashboard.config import PRIMARY_BAR
from dashboard.charts.template import _apply_common, _annotate_partial_year
from dashboard.data.collection_view import (
    COLLECTION_VIEW_GROUPED,
    COLLECTION_VIEW_INDIVIDUAL,
    display_entity_counts,
    display_entity_exposure,
    normalise_collection_view,
    with_collection_display,
)
from dashboard.data.registry import df_datasets, PARTIAL_YEAR_INFO
from dashboard.data.uptake import DATASET_EXPOSURE


def _wrap_axis_label(value, width=36):
    text = " ".join(str(value or "").split())
    if len(text) <= width:
        return text
    return "<br>".join(
        wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    )


def build_dataset_demand_figures(preset, custom, provider, topn_metric, collection_view):
    top_n = int(custom) if preset == -1 and custom else (preset if preset != -1 else 10)
    top_n = max(1, int(top_n))
    selected_view = normalise_collection_view(collection_view)
    grouped = selected_view == COLLECTION_VIEW_GROUPED
    entity_noun = "Collections / datasets" if grouped else "Datasets"
    entity_label = "Collection / dataset" if grouped else "Dataset"
    sub = df_datasets.copy()

    if provider and provider != "ALL":
        sub = sub[sub["provider"] == provider]

    display_sub = with_collection_display(sub, selected_view)

    # -- Top N datasets / collections bar chart --
    dataset_counts = display_entity_counts(display_sub)
    if (topn_metric or "count") == "rate":
        # Demand normalised by exposure WITHIN the register window (years
        # from max(availability, window start) to the latest register date,
        # current year fractional) -- never by raw dataset age.
        exposure = display_entity_exposure(display_sub, DATASET_EXPOSURE).reindex(
            dataset_counts["display_dataset"]
        )
        dataset_counts["exposure_years"] = exposure["exposure_years"].to_numpy()
        dataset_counts["availability_basis"] = exposure["availability_basis"].to_numpy()
        dataset_counts["Rate"] = (
            dataset_counts["Projects"] / dataset_counts["exposure_years"].replace(0, pd.NA)
        ).astype(float).round(2)
        dataset_counts = (
            dataset_counts.dropna(subset=["Rate"])
            .sort_values("Rate", ascending=True, kind="stable")
            .tail(top_n)
        )
        fig_top = px.bar(
            dataset_counts,
            x="Rate",
            y="display_dataset",
            orientation="h",
            title=f"Top {top_n} {entity_noun} by Demand Rate (per year available)",
            labels={
                "display_dataset": "",
                "Rate": "Retained entries per year available",
            },
            color_discrete_sequence=[PRIMARY_BAR],
            custom_data=["Projects", "exposure_years", "availability_basis", "display_kind"],
        )
        fig_top.update_traces(
            marker_line_width=0,
            hovertemplate=(
                "<b>%{y}</b><br>%{customdata[3]}<br>"
                "%{x:.2f} retained entries per year available<br>"
                "%{customdata[0]} retained entries over %{customdata[1]:.1f} exposure years<br>"
                "availability basis: %{customdata[2]}<extra></extra>"
            ),
        )
    else:
        dataset_counts = (
            dataset_counts.sort_values("Projects", ascending=True).tail(top_n)
        )
        fig_top = px.bar(
            dataset_counts,
            x="Projects",
            y="display_dataset",
            orientation="h",
            title=f"Top {top_n} Most-Requested {entity_noun}",
            labels={"display_dataset": "", "Projects": "Retained entries"},
            color_discrete_sequence=[PRIMARY_BAR],
            custom_data=["display_kind"],
        )
        fig_top.update_traces(
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>%{customdata[0]}<br>%{x} retained entries<extra></extra>",
        )
    fig_top.update_layout(
        showlegend=False,
        margin=dict(l=320),
        yaxis_tickfont_size=11,
    )
    _apply_common(fig_top, height=max(400, top_n * 22))

    # -- Trend: top N datasets / collections over time --
    trend_n = min(top_n, 15)  # cap legend at 15 for readability
    top_trend = (
        display_entity_counts(display_sub)
        .nlargest(trend_n, "Projects")["display_dataset"]
        .tolist()
    )
    trend_data = (
        display_sub[display_sub["display_dataset"].isin(top_trend)]
        .drop_duplicates(subset=[
            "Record ID" if "Record ID" in display_sub.columns else "Project ID",
            "Year",
            "display_dataset",
        ])
        .groupby(["Year", "display_dataset"])["Record ID" if "Record ID" in display_sub.columns else "Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Record ID" if "Record ID" in display_sub.columns else "Project ID": "Projects"})
    )
    fig_trend = px.line(
        trend_data,
        x="Year",
        y="Projects",
        color="display_dataset",
        title=f"Top {trend_n} {entity_noun} - Usage by Year",
        labels={"display_dataset": entity_label},
        markers=True,
    )
    fig_trend.update_layout(
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=9),
        ),
        margin=dict(r=200),
    )
    fig_trend.update_traces(line_width=2.5, marker_size=6)
    _annotate_partial_year(
        fig_trend,
        years=trend_data["Year"].unique() if "Year" in trend_data else [],
        partial_year_info=PARTIAL_YEAR_INFO,
    )
    _apply_common(fig_trend)

    # -- Provider breakdown bar --
    prov_counts = (
        sub[sub["provider"] != ""]
        .groupby("provider")["Record ID" if "Record ID" in sub.columns else "Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Record ID" if "Record ID" in sub.columns else "Project ID": "Projects"})
        .sort_values("Projects", ascending=False)
    )
    provider_top_n = 15
    if len(prov_counts) > provider_top_n:
        top = prov_counts.head(provider_top_n).copy()
        small = prov_counts.iloc[provider_top_n:]
        prov_counts = pd.concat(
            [
                top,
                pd.DataFrame([{"provider": "Other", "Projects": int(small["Projects"].sum())}]),
            ],
            ignore_index=True,
        )
    prov_plot = prov_counts.sort_values("Projects", ascending=True, kind="stable")
    prov_plot["provider_label"] = prov_plot["provider"].apply(_wrap_axis_label)
    fig_prov = px.bar(
        prov_plot,
        x="Projects",
        y="provider_label",
        orientation="h",
        title="Projects by Dataset source organisation",
        labels={"provider_label": "", "Projects": "Retained entries"},
        color_discrete_sequence=[PRIMARY_BAR],
        custom_data=["provider"],
    )
    fig_prov.update_traces(
        marker_line_width=0,
        text=prov_plot["Projects"],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="<b>%{customdata[0]}</b><br>%{x} retained entries<extra></extra>",
    )
    fig_prov.update_layout(
        showlegend=False,
        margin=dict(l=300, r=64, t=64, b=48),
        yaxis=dict(automargin=True, tickfont=dict(size=10)),
    )
    _apply_common(fig_prov, height=max(420, len(prov_plot) * 26))

    return fig_top, fig_trend, fig_prov


def register(app):
    @app.callback(
        Output("datasets-topn-custom", "style"),
        Input("datasets-topn-preset", "value"),
    )
    def toggle_datasets_custom(preset):
        base = {"width": "80px", "verticalAlign": "middle", "marginLeft": "8px"}
        if preset == -1:
            return {**base, "display": "inline-block"}
        return {**base, "display": "none"}

    @app.callback(
        Output("datasets-topn-chart", "figure"),
        Output("datasets-trend-chart", "figure"),
        Output("datasets-provider-chart", "figure"),
        Input("datasets-topn-preset", "value"),
        Input("datasets-topn-custom", "value"),
        Input("datasets-provider-filter", "value"),
        Input("datasets-topn-metric", "value"),
    )
    def update_datasets_tab(preset, custom, provider, topn_metric):
        # Top-of-section demand always shows individual datasets; the collections
        # toggle scopes only the Linked Data Uptake views.
        return build_dataset_demand_figures(
            preset,
            custom,
            provider,
            topn_metric,
            COLLECTION_VIEW_INDIVIDUAL,
        )
