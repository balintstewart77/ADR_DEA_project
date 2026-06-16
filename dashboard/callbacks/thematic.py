"""Thematic Analysis callbacks."""

from dash import dcc, Input, Output, State

from dashboard.data.thematic import (
    THEMATIC_DATA_AVAILABLE,
    df_thematic_a, df_thematic_c,
    df_thematic_a_totals, df_thematic_c_totals,
    df_cross_domain_purpose,
    df_thematic_tag_by_year,
    df_thematic_covid_tag_by_domain,
    df_thematic_demographic_tag_by_domain,
    df_domain_cooccurrence,
    df_latent_demand_cooccurrence,
    df_record_linkage_totals,
    df_collection_method_totals,
    df_temporal_structure_totals,
    df_unit_totals,
    df_researcher_sector_totals,
    df_record_linkage_by_year,
    df_collection_method_by_year,
    df_temporal_structure_by_year,
    df_unit_by_year,
    df_domain_record_linkage,
    df_researcher_sector_cooccurrence,
    RESEARCHER_SECTOR_EXCLUDED_COUNT,
)
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.filtering import _get_enriched_register_display_df, _csv_date_stamp
from dashboard.charts.template import CHART_HEIGHT
from dashboard.charts.thematic import (
    make_thematic_trend, make_thematic_totals_bar, make_tag_domain_bar,
    make_cross_heatmap,
    make_domain_cooccurrence, make_latent_demand_cooccurrence,
    make_compact_distribution_bar,
    make_record_linkage_trend, make_domain_record_linkage_breakdown,
    make_researcher_sector_cooccurrence,
)
from dashboard.config import DOMAIN_COLOURS, PURPOSE_COLOURS, TAG_COLOURS
from dashboard.data.uptake import SERVED_DOMAIN_PAIRS


def register(app):
    if not THEMATIC_DATA_AVAILABLE:
        return

    @app.callback(
        Output("thematic-domain-totals", "figure"),
        Output("thematic-purpose-totals", "figure"),
        Output("deterministic-researcher-sector-cooccurrence", "figure"),
        Output("deterministic-record-linkage-distribution", "figure"),
        Output("deterministic-collection-method-distribution", "figure"),
        Output("deterministic-temporal-structure-distribution", "figure"),
        Output("deterministic-unit-distribution", "figure"),
        Output("deterministic-researcher-sector-distribution", "figure"),
        Input("main-tabs", "active_tab"),
    )
    def update_static_thematic_figures(_active_tab):
        domain_totals = make_thematic_totals_bar(
            df_thematic_a_totals, "domain", DOMAIN_COLOURS,
            "Projects by Domain", height=440,
        )
        purpose_totals = make_thematic_totals_bar(
            df_thematic_c_totals, "purpose", PURPOSE_COLOURS,
            "Projects by Purpose", height=380,
        )

        researcher_sector_cooccurrence = make_researcher_sector_cooccurrence(
            df_researcher_sector_cooccurrence,
            excluded_count=RESEARCHER_SECTOR_EXCLUDED_COUNT,
        )
        record_linkage_distribution = make_compact_distribution_bar(
            df_record_linkage_totals,
            "record_linkage",
            "Record Linkage",
            height=280,
        )
        collection_method_distribution = make_compact_distribution_bar(
            df_collection_method_totals,
            "collection_method",
            "Collection method",
            multi_count=True,
            height=280,
        )
        temporal_structure_distribution = make_compact_distribution_bar(
            df_temporal_structure_totals,
            "temporal_structure",
            "Temporal structure",
            multi_count=True,
            height=280,
        )
        unit_distribution = make_compact_distribution_bar(
            df_unit_totals,
            "unit_of_observation",
            "Unit of observation",
            multi_count=True,
            height=280,
        )
        researcher_sector_distribution = make_compact_distribution_bar(
            df_researcher_sector_totals,
            "researcher_sector",
            "Researcher sector",
            multi_count=True,
            height=280,
        )

        return (
            domain_totals, purpose_totals,
            researcher_sector_cooccurrence,
            record_linkage_distribution,
            collection_method_distribution,
            temporal_structure_distribution,
            unit_distribution,
            researcher_sector_distribution,
        )

    def metric_col(metric_mode):
        return "pct_of_projects" if (metric_mode or "pct") == "pct" else "count"

    # Tag-by-domain bars have independent per-figure metric controls
    # (count vs % of the domain's classified projects).
    @app.callback(
        Output("thematic-covid-tag-domain", "figure"),
        Input("thematic-covid-tag-domain-metric", "value"),
    )
    def update_covid_tag_domain(metric):
        return make_tag_domain_bar(
            df_thematic_covid_tag_by_domain, DOMAIN_COLOURS,
            "COVID-19 & Pandemic by domain",
            metric=metric or "count",
        )

    @app.callback(
        Output("thematic-demographic-tag-domain", "figure"),
        Input("thematic-demographic-tag-domain-metric", "value"),
    )
    def update_demographic_tag_domain(metric):
        return make_tag_domain_bar(
            df_thematic_demographic_tag_by_domain, DOMAIN_COLOURS,
            "Demographic disparities by domain",
            metric=metric or "count",
        )

    @app.callback(
        Output("thematic-domain-trend", "figure"),
        Input("thematic-domain-trend-metric", "value"),
    )
    def update_domain_trend(metric):
        return make_thematic_trend(
            df_thematic_a, "domain", DOMAIN_COLOURS, metric_col(metric),
            "Substantive Domains Over Time",
            partial_year_info=PARTIAL_YEAR_INFO,
        )

    @app.callback(
        Output("thematic-purpose-trend", "figure"),
        Input("thematic-purpose-trend-metric", "value"),
    )
    def update_purpose_trend(metric):
        return make_thematic_trend(
            df_thematic_c, "purpose", PURPOSE_COLOURS, metric_col(metric),
            "Analytical Purpose Over Time",
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )

    @app.callback(
        Output("thematic-cross-domain-purpose", "figure"),
        Input("thematic-cross-domain-purpose-metric", "value"),
    )
    def update_cross_domain_purpose(metric):
        return make_cross_heatmap(
            df_cross_domain_purpose, "domain",
            "Substantive Domain × Analytical Purpose",
            colorscale=[[0, "#fef0ec"], [0.5, "#f4a582"], [1, "#d73027"]],
            height=560,
            metric=metric or "pct",
        )

    @app.callback(
        Output("thematic-tag-trend", "figure"),
        Input("thematic-tag-trend-metric", "value"),
    )
    def update_tag_trend(metric):
        return make_thematic_trend(
            df_thematic_tag_by_year, "tag", TAG_COLOURS, metric_col(metric),
            "Cross-Cutting Tags Over Time",
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )

    @app.callback(
        Output("thematic-domain-cooccurrence", "figure"),
        Input("thematic-domain-cooccurrence-metric", "value"),
    )
    def update_domain_cooccurrence(metric):
        return make_domain_cooccurrence(
            df_domain_cooccurrence,
            metric=metric or "pct",
        )

    @app.callback(
        Output("thematic-latent-demand", "figure"),
        Input("thematic-latent-demand-metric", "value"),
    )
    def update_latent_demand(metric):
        return make_latent_demand_cooccurrence(
            df_latent_demand_cooccurrence,
            SERVED_DOMAIN_PAIRS,
            metric=metric or "pct",
        )

    @app.callback(
        Output("deterministic-record-linkage-trend", "figure"),
        Input("deterministic-record-linkage-trend-metric", "value"),
    )
    def update_record_linkage_trend(metric):
        return make_record_linkage_trend(
            df_record_linkage_by_year,
            metric=metric or "pct",
            partial_year_info=PARTIAL_YEAR_INFO,
        )

    _MULTI_COUNT_NOTE = "Multi-count: a project carrying both values counts in both lines."

    def _facet_trend_figure(df_by_year, category_col, colours, metric, title):
        fig = make_thematic_trend(
            df_by_year, category_col, colours, metric_col(metric), title,
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        fig.add_annotation(
            text=_MULTI_COUNT_NOTE,
            xref="paper", yref="paper",
            x=0, y=1.07, showarrow=False,
            xanchor="left", yanchor="bottom",
            font=dict(size=10, color="#7f8c8d"),
        )
        return fig

    @app.callback(
        Output("deterministic-collection-method-trend", "figure"),
        Input("deterministic-collection-method-trend-metric", "value"),
    )
    def update_collection_method_trend(metric):
        return _facet_trend_figure(
            df_collection_method_by_year,
            "collection_method",
            {"Survey": "#e76f51", "Administrative": "#2a9d8f"},
            metric,
            "Collection Method Over Time",
        )

    @app.callback(
        Output("deterministic-temporal-structure-trend", "figure"),
        Input("deterministic-temporal-structure-trend-metric", "value"),
    )
    def update_temporal_structure_trend(metric):
        return _facet_trend_figure(
            df_temporal_structure_by_year,
            "temporal_structure",
            {"Cross-sectional": "#f4a261", "Longitudinal": "#6a3d9a"},
            metric,
            "Temporal Structure Over Time",
        )

    @app.callback(
        Output("deterministic-unit-trend", "figure"),
        Input("deterministic-unit-trend-metric", "value"),
    )
    def update_unit_trend(metric):
        return _facet_trend_figure(
            df_unit_by_year,
            "unit_of_observation",
            {
                "Individual": "#2a9d8f",
                "Household": "#e9c46a",
                "Business": "#264653",
                "Area": "#e76f51",
            },
            metric,
            "Unit of Observation Over Time",
        )

    @app.callback(
        Output("deterministic-domain-linkage-breakdown", "figure"),
        Input("deterministic-domain-linkage-metric", "value"),
    )
    def update_domain_linkage_breakdown(metric):
        return make_domain_record_linkage_breakdown(
            df_domain_record_linkage,
            metric=metric or "pct",
        )

    @app.callback(
        Output("enriched-register-table", "data"),
        Output("enriched-register-table", "page_size"),
        Output("enriched-browse-count", "children"),
        Input("enriched-search", "value"),
        Input("enriched-dataset-filter", "value"),
        Input("enriched-provider-filter", "value"),
        Input("enriched-institution-filter", "value"),
        Input("enriched-tre-filter", "value"),
        Input("enriched-domain-filter", "value"),
        Input("enriched-domain-count-filter", "value"),
        Input("enriched-purpose-filter", "value"),
        Input("enriched-tag-filter", "value"),
        Input("enriched-record-linkage-filter", "value"),
        Input("enriched-collection-method-filter", "value"),
        Input("enriched-temporal-structure-filter", "value"),
        Input("enriched-unit-filter", "value"),
        Input("enriched-researcher-sector-filter", "value"),
        Input("enriched-page-size", "value"),
    )
    def update_enriched_register(
        search,
        dataset_filter,
        provider_filter,
        institution_filter,
        tre_filter,
        domain_filter,
        domain_count_filter,
        purpose_filter,
        tag_filter,
        record_linkage_filter,
        collection_method_filter,
        temporal_structure_filter,
        unit_filter,
        researcher_sector_filter,
        page_size,
    ):
        display, count_text = _get_enriched_register_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            domain_filter,
            domain_count_filter,
            purpose_filter,
            tag_filter,
            record_linkage_filter,
            collection_method_filter,
            temporal_structure_filter,
            unit_filter,
            researcher_sector_filter,
        )

        return (
            display.to_dict("records"),
            page_size or 20,
            count_text,
        )

    @app.callback(
        Output("enriched-download-csv", "data"),
        Input("enriched-download-btn", "n_clicks"),
        State("enriched-search", "value"),
        State("enriched-dataset-filter", "value"),
        State("enriched-provider-filter", "value"),
        State("enriched-institution-filter", "value"),
        State("enriched-tre-filter", "value"),
        State("enriched-domain-filter", "value"),
        State("enriched-domain-count-filter", "value"),
        State("enriched-purpose-filter", "value"),
        State("enriched-tag-filter", "value"),
        State("enriched-record-linkage-filter", "value"),
        State("enriched-collection-method-filter", "value"),
        State("enriched-temporal-structure-filter", "value"),
        State("enriched-unit-filter", "value"),
        State("enriched-researcher-sector-filter", "value"),
        prevent_initial_call=True,
    )
    def download_enriched_csv(
        n_clicks,
        search,
        dataset_filter,
        provider_filter,
        institution_filter,
        tre_filter,
        domain_filter,
        domain_count_filter,
        purpose_filter,
        tag_filter,
        record_linkage_filter,
        collection_method_filter,
        temporal_structure_filter,
        unit_filter,
        researcher_sector_filter,
    ):
        display, _ = _get_enriched_register_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            domain_filter,
            domain_count_filter,
            purpose_filter,
            tag_filter,
            record_linkage_filter,
            collection_method_filter,
            temporal_structure_filter,
            unit_filter,
            researcher_sector_filter,
        )
        filename = f"dea-enriched-register-{_csv_date_stamp()}.csv"
        return dcc.send_data_frame(display.to_csv, filename, index=False)
