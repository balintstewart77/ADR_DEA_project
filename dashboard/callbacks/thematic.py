"""Thematic Analysis callbacks."""

from dash import dcc, Input, Output, State

from dashboard.data.thematic import (
    THEMATIC_DATA_AVAILABLE,
    df_thematic_a, df_thematic_c,
    df_thematic_a_totals, df_thematic_c_totals,
    df_cross_domain_purpose,
    df_thematic_tag_by_year, df_thematic_tag_by_domain,
    df_domain_cooccurrence,
)
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.filtering import _get_enriched_register_display_df, _csv_date_stamp
from dashboard.charts.template import CHART_HEIGHT
from dashboard.charts.thematic import (
    make_thematic_trend, make_thematic_totals_bar, make_cross_heatmap,
    make_domain_cooccurrence,
)
from dashboard.config import DOMAIN_COLOURS, PURPOSE_COLOURS, TAG_COLOURS


def register(app):
    if not THEMATIC_DATA_AVAILABLE:
        return

    @app.callback(
        Output("thematic-domain-trend", "figure"),
        Output("thematic-purpose-trend", "figure"),
        Output("thematic-domain-totals", "figure"),
        Output("thematic-purpose-totals", "figure"),
        Output("thematic-cross-domain-purpose", "figure"),
        Output("thematic-tag-trend", "figure"),
        Output("thematic-tag-domain", "figure"),
        Output("thematic-domain-cooccurrence", "figure"),
        Input("thematic-metric-toggle", "value"),
    )
    def update_thematic_tab(metric_mode):
        metric_col = "pct_of_projects" if metric_mode == "pct" else "count"

        domain_trend = make_thematic_trend(
            df_thematic_a, "domain", DOMAIN_COLOURS, metric_col,
            "Substantive Domains Over Time",
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        purpose_trend = make_thematic_trend(
            df_thematic_c, "purpose", PURPOSE_COLOURS, metric_col,
            "Analytical Purpose Over Time",
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )

        domain_totals = make_thematic_totals_bar(
            df_thematic_a_totals, "domain", DOMAIN_COLOURS,
            "Projects by Domain", height=440,
        )
        purpose_totals = make_thematic_totals_bar(
            df_thematic_c_totals, "purpose", PURPOSE_COLOURS,
            "Projects by Purpose", height=380,
        )

        cross_purpose = make_cross_heatmap(
            df_cross_domain_purpose, "domain",
            "Substantive Domain × Analytical Purpose",
            colorscale=[[0, "#fef0ec"], [0.5, "#f4a582"], [1, "#d73027"]],
            height=560,
            metric=metric_mode,
        )

        tag_trend = make_thematic_trend(
            df_thematic_tag_by_year, "tag", TAG_COLOURS, metric_col,
            "Cross-Cutting Tags Over Time",
            height=CHART_HEIGHT,
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        tag_domain = make_thematic_totals_bar(
            df_thematic_tag_by_domain, "domain", DOMAIN_COLOURS,
            "Tagged Projects by Domain", height=440,
        )

        domain_cooccurrence = make_domain_cooccurrence(df_domain_cooccurrence, metric=metric_mode)

        return (
            domain_trend, purpose_trend,
            domain_totals, purpose_totals,
            cross_purpose,
            tag_trend, tag_domain,
            domain_cooccurrence,
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
