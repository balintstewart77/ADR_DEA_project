"""Thematic Analysis callbacks."""

from dash import dcc, Input, Output, State

from dashboard.data.thematic import (
    THEMATIC_DATA_AVAILABLE,
    df_thematic_a, df_thematic_b, df_thematic_c,
    df_thematic_a_totals, df_thematic_b_totals, df_thematic_c_totals,
    df_cross_mode_domain, df_cross_domain_purpose,
)
from dashboard.data.registry import PARTIAL_YEAR_INFO
from dashboard.data.filtering import _get_enriched_register_display_df, _csv_date_stamp
from dashboard.charts.template import CHART_HEIGHT
from dashboard.charts.thematic import (
    make_thematic_trend, make_linkage_area, make_thematic_totals_bar, make_cross_heatmap,
)
from dashboard.config import DOMAIN_COLOURS, LINKAGE_COLOURS, PURPOSE_COLOURS


def register(app):
    if not THEMATIC_DATA_AVAILABLE:
        return

    @app.callback(
        Output("thematic-domain-trend", "figure"),
        Output("thematic-linkage-trend", "figure"),
        Output("thematic-purpose-trend", "figure"),
        Output("thematic-domain-totals", "figure"),
        Output("thematic-linkage-totals", "figure"),
        Output("thematic-purpose-totals", "figure"),
        Output("thematic-cross-mode-domain", "figure"),
        Output("thematic-cross-domain-purpose", "figure"),
        Input("thematic-metric-toggle", "value"),
    )
    def update_thematic_tab(metric_mode):
        metric_col = "pct_of_projects" if metric_mode == "pct" else "count"

        domain_trend = make_thematic_trend(
            df_thematic_a, "domain", DOMAIN_COLOURS, metric_col,
            "Substantive Domains Over Time",
            partial_year_info=PARTIAL_YEAR_INFO,
        )
        linkage_trend = make_linkage_area(
            df_thematic_b, LINKAGE_COLOURS, metric_col,
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
        linkage_totals = make_thematic_totals_bar(
            df_thematic_b_totals, "linkage_mode", LINKAGE_COLOURS,
            "Projects by Linkage Mode", height=280,
        )
        purpose_totals = make_thematic_totals_bar(
            df_thematic_c_totals, "purpose", PURPOSE_COLOURS,
            "Projects by Purpose", height=380,
        )

        cross_mode = make_cross_heatmap(
            df_cross_mode_domain, "primary_domain",
            "Primary Domain × Linkage Mode",
            colorscale="Tealgrn",
        )
        cross_purpose = make_cross_heatmap(
            df_cross_domain_purpose, "primary_domain",
            "Primary Domain × Analytical Purpose",
            colorscale=[[0, "#fef0ec"], [0.5, "#f4a582"], [1, "#d73027"]],
        )

        return (
            domain_trend, linkage_trend, purpose_trend,
            domain_totals, linkage_totals, purpose_totals,
            cross_mode, cross_purpose,
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
        Input("enriched-linkage-filter", "value"),
        Input("enriched-purpose-filter", "value"),
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
        linkage_filter,
        purpose_filter,
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
            linkage_filter,
            purpose_filter,
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
        State("enriched-linkage-filter", "value"),
        State("enriched-purpose-filter", "value"),
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
        linkage_filter,
        purpose_filter,
    ):
        display, _ = _get_enriched_register_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            domain_filter,
            domain_count_filter,
            linkage_filter,
            purpose_filter,
        )
        filename = f"dea-enriched-register-{_csv_date_stamp()}.csv"
        return dcc.send_data_frame(display.to_csv, filename, index=False)
