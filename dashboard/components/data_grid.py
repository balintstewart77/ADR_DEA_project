"""Shared AG Grid set-up for the dashboard tables.

The look (dark header, striped rows) is in assets/styles.css under .dea-grid.
The sort comparator and the HTML cell renderer are in
assets/dash_ag_grid_functions.js.
"""

import dash_ag_grid as dag
from dash import Patch

DEFAULT_PAGE_SIZE = 20

_DEFAULT_COL_DEF = {
    "sortable": True,
    "resizable": True,
    "suppressMovable": True,
    "suppressHeaderMenuButton": True,
    "wrapText": True,
    "autoHeight": True,
    "wrapHeaderText": True,
    "autoHeaderHeight": True,
    # Show and sort values as sent. Without this the grid guesses a type from
    # the first row, for example parsing ISO date strings as dates.
    "cellDataType": False,
    # Missing values sort last in both directions, as they did in Dash DataTable.
    "comparator": {"function": "nullsLast"},
}

_GRID_OPTIONS = {
    "pagination": True,
    "paginationPageSize": DEFAULT_PAGE_SIZE,
    # Each table's own "Per page" dropdown sets the size.
    "paginationPageSizeSelector": False,
    # Grow to fit the page instead of scrolling inside a fixed height.
    "domLayout": "autoHeight",
    # Render every column, so auto-height rows get their final height at once.
    "suppressColumnVirtualisation": True,
    "enableCellTextSelection": True,
    "ensureDomOrder": True,
    "tooltipShowDelay": 0,
}


def data_grid(column_defs, row_data=(), class_name="", **kwargs) -> dag.AgGrid:
    """A paged, sortable grid of server-built rows."""
    return dag.AgGrid(
        columnDefs=column_defs,
        rowData=list(row_data),
        defaultColDef=_DEFAULT_COL_DEF,
        dashGridOptions=_GRID_OPTIONS,
        className=f"dea-grid {class_name}".strip(),
        **kwargs,
    )


def page_size_patch(page_size) -> Patch:
    """Change a grid's page size and leave its other options alone."""
    patch = Patch()
    patch["paginationPageSize"] = page_size or DEFAULT_PAGE_SIZE
    return patch
