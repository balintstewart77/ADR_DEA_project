"""Project Explorer callbacks."""

from dash import dcc, Input, Output, State

from dashboard.config import _BROWSE_DISPLAY_COLUMNS
from dashboard.data.filtering import (
    _get_browse_display_df,
    _get_browse_facet_options,
    _csv_date_stamp,
)
from dashboard.data.year_filter import YearRange, filter_records_by_year, parse_accreditation_dates


def _filter_accreditation_year_range(
    display,
    accreditation_year_range,
    accreditation_year_min,
    accreditation_year_max,
):
    bounds = YearRange(int(accreditation_year_min), int(accreditation_year_max))
    filtered = filter_records_by_year(display, accreditation_year_range, bounds)
    return filtered, parse_accreditation_dates(display)


def register(app):
    @app.callback(
        Output("browse-table", "data"),
        Output("browse-table", "tooltip_data"),
        Output("browse-table", "page_size"),
        Output("browse-count", "children"),
        Output("browse-dataset-filter", "options"),
        Output("browse-provider-filter", "options"),
        Output("browse-institution-filter", "options"),
        Output("browse-tre-filter", "options"),
        Input("browse-dataset-filter", "value"),
        Input("browse-provider-filter", "value"),
        Input("browse-institution-filter", "value"),
        Input("browse-tre-filter", "value"),
        Input("browse-search", "value"),
        Input("browse-page-size", "value"),
        Input("browse-accreditation-year-filter", "value"),
        State("browse-accreditation-year-filter", "min"),
        State("browse-accreditation-year-filter", "max"),
    )
    def update_browse_table(
        dataset_filter,
        provider_filter,
        institution_filter,
        tre_filter,
        search,
        page_size,
        accreditation_year_range,
        accreditation_year_min,
        accreditation_year_max,
    ):
        display = _get_browse_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
        )
        display, accreditation_dates = _filter_accreditation_year_range(
            display,
            accreditation_year_range,
            accreditation_year_min,
            accreditation_year_max,
        )

        display["Accreditation Date"] = (
            accreditation_dates.loc[display.index].dt.strftime("%Y-%m-%d").fillna("")
        )
        table_data = display.to_dict("records")

        tooltip_data = [
            {
                col: {"value": str(row.get(col, "")), "type": "markdown"}
                for col in _BROWSE_DISPLAY_COLUMNS
            }
            for row in table_data
        ]

        count_text = (
            f"Showing {len(table_data):,} accreditation "
            f"record{'s' if len(table_data) != 1 else ''}"
        )
        facet_options = _get_browse_facet_options(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
            accreditation_year_range,
            accreditation_year_min,
            accreditation_year_max,
        )
        return (
            table_data,
            tooltip_data,
            page_size or 20,
            count_text,
            facet_options["dataset"],
            facet_options["provider"],
            facet_options["institution"],
            facet_options["tre"],
        )

    @app.callback(
        Output("browse-download-csv", "data"),
        Input("browse-download-btn", "n_clicks"),
        State("browse-search", "value"),
        State("browse-dataset-filter", "value"),
        State("browse-provider-filter", "value"),
        State("browse-institution-filter", "value"),
        State("browse-tre-filter", "value"),
        State("browse-accreditation-year-filter", "value"),
        State("browse-accreditation-year-filter", "min"),
        State("browse-accreditation-year-filter", "max"),
        prevent_initial_call=True,
    )
    def download_browse_csv(
        n_clicks,
        search,
        dataset,
        provider,
        institution,
        tre,
        accreditation_year_range,
        accreditation_year_min,
        accreditation_year_max,
    ):
        display = _get_browse_display_df(search, dataset, provider, institution, tre)
        display, _ = _filter_accreditation_year_range(
            display,
            accreditation_year_range,
            accreditation_year_min,
            accreditation_year_max,
        )
        filename = f"dea-projects-{_csv_date_stamp()}.csv"
        return dcc.send_data_frame(display.to_csv, filename, index=False)
