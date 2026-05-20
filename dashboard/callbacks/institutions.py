"""Institutions callbacks."""

from dash import Input, Output

from dashboard.charts.institutions import make_institution_bar, make_institution_trend
from dashboard.data.registry import df_institutions, PARTIAL_YEAR_INFO


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
        Output("institutions-bar-chart", "figure"),
        Output("institutions-trend-chart", "figure"),
        Input("institutions-topn-preset", "value"),
        Input("institutions-topn-custom", "value"),
    )
    def update_institutions_tab(preset, custom):
        top_n = int(custom) if preset == -1 and custom else (preset if preset != -1 else 10)
        top_n = max(1, int(top_n))
        return (
            make_institution_bar(df_institutions, top_n=top_n),
            make_institution_trend(df_institutions, top_n=8, partial_year_info=PARTIAL_YEAR_INFO),
        )
