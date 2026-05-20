"""Project Explorer callbacks."""

from dash import dcc, Input, Output, State

from dashboard.config import _BROWSE_DISPLAY_COLUMNS
from dashboard.data.filtering import _get_browse_display_df, _csv_date_stamp


def register(app):
    @app.callback(
        Output("browse-table", "data"),
        Output("browse-table", "tooltip_data"),
        Output("browse-table", "page_size"),
        Output("browse-count", "children"),
        Input("browse-dataset-filter", "value"),
        Input("browse-provider-filter", "value"),
        Input("browse-institution-filter", "value"),
        Input("browse-tre-filter", "value"),
        Input("browse-search", "value"),
        Input("browse-page-size", "value"),
    )
    def update_browse_table(dataset_filter, provider_filter, institution_filter, tre_filter, search, page_size):
        display = _get_browse_display_df(
            search,
            dataset_filter,
            provider_filter,
            institution_filter,
            tre_filter,
        )
        table_data = display.to_dict("records")

        tooltip_data = [
            {
                col: {"value": str(row.get(col, "")), "type": "markdown"}
                for col in _BROWSE_DISPLAY_COLUMNS
            }
            for row in table_data
        ]

        count_text = f"Showing {len(table_data):,} project{'s' if len(table_data) != 1 else ''}"
        return table_data, tooltip_data, page_size or 20, count_text

    @app.callback(
        Output("browse-download-csv", "data"),
        Input("browse-download-btn", "n_clicks"),
        State("browse-search", "value"),
        State("browse-dataset-filter", "value"),
        State("browse-provider-filter", "value"),
        State("browse-institution-filter", "value"),
        State("browse-tre-filter", "value"),
        prevent_initial_call=True,
    )
    def download_browse_csv(n_clicks, search, dataset, provider, institution, tre):
        display = _get_browse_display_df(search, dataset, provider, institution, tre)
        filename = f"dea-projects-{_csv_date_stamp()}.csv"
        return dcc.send_data_frame(display.to_csv, filename, index=False)
