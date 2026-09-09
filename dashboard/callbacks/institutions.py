"""Institutions callbacks."""

from dash import Input, Output

from dashboard.charts.institutions import make_institution_bar, make_institution_trend
from dashboard.charts.template import annotate_empty
from dashboard.data.registry import df_all, df_institutions, PARTIAL_YEAR_INFO
from dashboard.data.year_filter import filter_related_by_record_ids, selected_record_ids, year_range


_YEAR_RANGE = year_range(df_all)


def register(app):
    @app.callback(
        Output("institutions-topn-custom", "style"),
        Input("institutions-topn-preset", "value"),
    )
    def toggle_institutions_custom(preset):
        base = {"width": "80px", "verticalAlign": "middle", "marginLeft": "8px"}
        if preset == -1:
            return {**base, "display": "inline-block"}
        return {**base, "display": "none"}

    @app.callback(
        Output("institutions-trend-topn-custom", "style"),
        Input("institutions-trend-topn-preset", "value"),
    )
    def toggle_institutions_trend_custom(preset):
        base = {"width": "80px", "verticalAlign": "middle", "marginLeft": "8px"}
        if preset == -1:
            return {**base, "display": "inline-block"}
        return {**base, "display": "none"}

    @app.callback(
        Output("institutions-bar-chart", "figure"),
        Output("institutions-trend-chart", "figure"),
        Input("institutions-topn-preset", "value"),
        Input("institutions-topn-custom", "value"),
        Input("institutions-trend-topn-preset", "value"),
        Input("institutions-trend-topn-custom", "value"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_institutions_tab(preset, custom, trend_preset, trend_custom, year_selection):
        top_n = int(custom) if preset == -1 and custom else (preset if preset != -1 else 10)
        top_n = max(1, int(top_n))
        trend_top_n = (
            int(trend_custom)
            if trend_preset == -1 and trend_custom
            else (trend_preset if trend_preset != -1 else 8)
        )
        trend_top_n = max(1, int(trend_top_n))
        record_ids = selected_record_ids(df_all, year_selection, _YEAR_RANGE)
        selected = filter_related_by_record_ids(df_institutions, record_ids)
        figures = (
            make_institution_bar(selected, top_n=top_n),
            make_institution_trend(
                selected,
                top_n=trend_top_n,
                partial_year_info=PARTIAL_YEAR_INFO,
            ),
        )
        return tuple(annotate_empty(fig, selected.empty) for fig in figures)
