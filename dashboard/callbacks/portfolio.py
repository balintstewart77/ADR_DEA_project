"""Portfolio-wide accreditation-year state and overall-trend callbacks."""

from dash import Input, Output

from dashboard.charts.core import make_quarterly_chart, make_srs_chart, make_yearly_chart
from dashboard.charts.template import annotate_empty
from dashboard.data.registry import PARTIAL_YEAR_INFO, df_all
from dashboard.data.year_filter import (
    date_coverage,
    filter_records_by_year,
    is_all_years,
    selection_label,
    year_range,
)


PORTFOLIO_YEAR_RANGE = year_range(df_all)


def selected_portfolio_records(selection):
    return filter_records_by_year(df_all, selection, PORTFOLIO_YEAR_RANGE)


def portfolio_filter_summary(selection) -> str:
    selected = selected_portfolio_records(selection)
    coverage = date_coverage(df_all)
    count = len(selected)
    label = selection_label(selection, PORTFOLIO_YEAR_RANGE)
    if count == 0:
        lead = "No selected projects"
    else:
        lead = f"{count:,} selected project{'s' if count != 1 else ''}"
    if is_all_years(selection, PORTFOLIO_YEAR_RANGE):
        date_note = (
            f"{coverage['undated_or_invalid_records']:,} undated/invalid included"
        )
    else:
        date_note = (
            f"{coverage['undated_or_invalid_records']:,} undated/invalid omitted"
        )
    return f"{lead} · {label} · {date_note}"


def build_overall_figures(selection):
    selected = selected_portfolio_records(selection)
    is_empty = selected.empty
    return tuple(
        annotate_empty(fig, is_empty)
        for fig in (
            make_yearly_chart(selected, partial_year_info=PARTIAL_YEAR_INFO),
            make_quarterly_chart(selected),
            make_srs_chart(selected),
        )
    )


def register(app):
    @app.callback(
        Output("portfolio-accreditation-year-filter", "value"),
        Input("portfolio-year-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_portfolio_years(_n_clicks):
        return PORTFOLIO_YEAR_RANGE.value

    @app.callback(
        Output("portfolio-filter-summary", "children"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_portfolio_summary(selection):
        return portfolio_filter_summary(selection)

    @app.callback(
        Output("overall-yearly-chart", "figure"),
        Output("overall-quarterly-chart", "figure"),
        Output("overall-srs-chart", "figure"),
        Input("portfolio-accreditation-year-filter", "value"),
    )
    def update_overall_trends(selection):
        return build_overall_figures(selection)
