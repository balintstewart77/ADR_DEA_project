"""Project Explorer tab."""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from dashboard.data.registry import (
    _ALL_DATASET_OPTIONS, _ALL_PROVIDER_OPTIONS, _ALL_INSTITUTION_OPTIONS, _ALL_TRE_OPTIONS,
)
from dashboard.components.table_styles import BROWSE_TABLE_STYLES


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
                    placeholder="Search by title or researcher…",
                    type="text",
                ),
            ],
                md=6,
            ),
            dbc.Col([
                html.Label("Dataset", className="filter-label"),
                dcc.Dropdown(
                    id="browse-dataset-filter",
                    options=_ALL_DATASET_OPTIONS,
                    value="ALL",
                    clearable=False,
                    searchable=True,
                    placeholder="All datasets",
                ),
            ], md=3),
            dbc.Col([
                html.Label("Source organisation", className="filter-label"),
                dcc.Dropdown(
                    id="browse-provider-filter",
                    options=_ALL_PROVIDER_OPTIONS,
                    value="ALL",
                    clearable=False,
                    searchable=True,
                    placeholder="All source organisations",
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
                    value="ALL",
                    clearable=False,
                    searchable=True,
                    placeholder="All institutions",
                ),
            ], md=3),
            dbc.Col([
                html.Label("TRE provider", className="filter-label"),
                dcc.Dropdown(
                    id="browse-tre-filter",
                    options=_ALL_TRE_OPTIONS,
                    value="ALL",
                    clearable=False,
                    searchable=True,
                    placeholder="All TRE providers",
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
                html.Div(id="browse-count", className="text-muted small",
                         style={"paddingTop": "1.8rem"}),
            ], md=2),
            dbc.Col([
                html.Label(" ", className="filter-label"),
                html.Button(
                    "Download CSV",
                    id="browse-download-btn",
                    className="btn btn-outline-primary btn-sm w-100",
                ),
                dbc.Tooltip(
                    "Downloads all projects matching the current filters.",
                    target="browse-download-btn",
                    placement="top",
                ),
            ], md=2),
        ], className="mb-3 g-2"),
        html.Div(
            dash_table.DataTable(
                id="browse-table",
                columns=[
                    {"name": "Project ID", "id": "Project ID"},
                    {"name": "Title", "id": "Title"},
                    {"name": "Researchers", "id": "Researchers"},
                    {"name": "Datasets Used", "id": "Datasets Used"},
                    {"name": "Accreditation Date", "id": "Accreditation Date"},
                ],
                page_size=20,
                sort_action="native",
                filter_action="none",
                tooltip_data=[],
                tooltip_delay=0,
                tooltip_duration=None,
                **BROWSE_TABLE_STYLES,
            ),
            className="dea-table",
        ),
    ])
