"""Project Explorer tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.data.registry import (
    _ALL_DATASET_OPTIONS, _ALL_PROVIDER_OPTIONS, _ALL_INSTITUTION_OPTIONS, _ALL_TRE_OPTIONS,
    df_all,
)
from dashboard.components.filter_controls import all_option_label
from dashboard.components.data_grid import data_grid
from dashboard.data.year_filter import year_slider_kwargs

# The register separates researchers (and datasets) with line breaks, which the
# pre-line cells show. Each tooltip shows the register text as written.
_BROWSE_COLUMNS = [
    {"headerName": "Project ID", "field": "Project ID", "tooltipField": "Project ID", "width": 115},
    {"headerName": "Title", "field": "Title", "tooltipField": "Title", "flex": 2, "minWidth": 220},
    {
        "headerName": "Researchers", "field": "Researchers", "tooltipField": "Researchers_tooltip",
        "cellClass": "dea-pre-line", "flex": 2, "minWidth": 220,
    },
    {
        "headerName": "Datasets Used", "field": "Datasets Used", "tooltipField": "Datasets Used_tooltip",
        "cellClass": "dea-pre-line", "flex": 3, "minWidth": 260,
    },
    {
        "headerName": "Processing environment", "field": "Secure Research Service",
        "tooltipField": "Secure Research Service", "flex": 1, "minWidth": 150,
    },
    {
        "headerName": "Accreditation Date", "field": "Accreditation Date",
        "tooltipField": "Accreditation Date", "width": 140,
    },
]


def build_explorer_tab():
    return dbc.Tab(label="\U0001F50D Project Explorer", tab_id="tab-browse", children=[
        html.H5(
            "Project Explorer",
            className="page-title",
        ),
        html.P(
            "Search and filter the full DEA-accredited project register.",
            className="section-desc",
        ),
        # Search row
        dbc.Row([
            dbc.Col([
                html.Label("Search", className="filter-label"),
                dbc.Input(
                    id="browse-search",
                    placeholder="Search by project ID, title, or researcher…",
                    type="text",
                    # Wait for a pause in typing: each update re-filters and re-counts the register.
                    debounce=400,
                ),
            ],
                md=6,
            ),
            dbc.Col([
                html.Label("Dataset", className="filter-label"),
                dcc.Dropdown(
                    id="browse-dataset-filter",
                    options=_ALL_DATASET_OPTIONS,
                    value=None,
                    clearable=True,
                    placeholder=all_option_label(_ALL_DATASET_OPTIONS),
                    searchable=True,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Dataset source organisation", className="filter-label"),
                dcc.Dropdown(
                    id="browse-provider-filter",
                    options=_ALL_PROVIDER_OPTIONS,
                    value=None,
                    clearable=True,
                    placeholder=all_option_label(_ALL_PROVIDER_OPTIONS),
                    searchable=True,
                ),
            ], md=3),
        ], className="mb-2 g-2"),
        # Secondary filters
        dbc.Row([
            dbc.Col([
                html.Label("Research Institution", className="filter-label"),
                dcc.Dropdown(
                    id="browse-institution-filter",
                    options=_ALL_INSTITUTION_OPTIONS,
                    value=None,
                    clearable=True,
                    placeholder=all_option_label(_ALL_INSTITUTION_OPTIONS),
                    searchable=True,
                ),
            ], md=3),
            dbc.Col([
                    html.Label("Processing environment", className="filter-label"),
                dcc.Dropdown(
                    id="browse-tre-filter",
                    options=_ALL_TRE_OPTIONS,
                    value=None,
                    clearable=True,
                    placeholder=all_option_label(_ALL_TRE_OPTIONS),
                    searchable=True,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Per page", className="filter-label"),
                dcc.Dropdown(
                    id="browse-page-size",
                    options=[{"label": str(n), "value": n} for n in [10, 20, 50, 100]],
                    value=20,
                    clearable=False,
                    searchable=False,
                ),
            ], md=2),
            dbc.Col([
                html.Label("Accreditation year", className="filter-label"),
                dcc.RangeSlider(
                    id="browse-accreditation-year-filter",
                    **year_slider_kwargs(df_all),
                ),
            ], md=4),
        ], className="mb-2 g-2"),
        dbc.Row([
            dbc.Col([
                html.Div(id="browse-count", className="text-muted small"),
                html.Div([
                    html.Button(
                        "Clear filters",
                        id="browse-clear-filters-btn",
                        className="btn btn-outline-secondary btn-sm",
                    ),
                    html.Button(
                        "Download CSV",
                        id="browse-download-btn",
                        className="btn btn-outline-primary btn-sm",
                    ),
                    dbc.Tooltip(
                        "Downloads all projects matching the current filters.",
                        target="browse-download-btn",
                        placement="top",
                    ),
                ], className="d-flex gap-2"),
            ],
                md=12,
                className=(
                    "d-flex flex-wrap align-items-center "
                    "justify-content-between gap-2"
                ),
            ),
        ], className="mb-3 g-2"),
        data_grid(_BROWSE_COLUMNS, id="browse-table"),
    ])
