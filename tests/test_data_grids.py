"""The dashboard's tables are AG Grids served with the app."""

from pathlib import Path

import pytest

from dashboard.components.data_grid import DEFAULT_PAGE_SIZE, page_size_patch

ROOT = Path(__file__).resolve().parents[1]


def test_no_dashboard_module_uses_the_deprecated_datatable():
    sources = {path: path.read_text(encoding="utf-8") for path in (ROOT / "dashboard").rglob("*.py")}
    assert sources
    assert not [str(path) for path, text in sources.items() if "dash_table" in text]


def test_grid_scripts_are_served_by_the_app_not_a_cdn():
    from dashboard.app import app

    page = app.server.test_client().get("/").get_data(as_text=True)
    # Dash fingerprints the file name with the package version.
    assert '"/_dash-component-suites/dash_ag_grid/dash_ag_grid.v' in page
    assert "unpkg.com" not in page and "cdn.jsdelivr.net" not in page


@pytest.mark.parametrize("dropdown, grid", [
    ("browse-page-size", "browse-table"),
    ("enriched-page-size", "enriched-register-table"),
])
def test_page_size_dropdown_changes_only_the_grid_page_size(dropdown, grid):
    from dashboard.app import app

    spec = next(
        spec for spec in app.callback_map.values()
        if spec["inputs"] == [{"id": dropdown, "property": "value"}]
    )
    assert str(spec["output"]) == f"{grid}.dashGridOptions"
    patch = spec["callback"].__wrapped__(50).to_plotly_json()
    assert patch["operations"] == [{
        "operation": "Assign", "location": ["paginationPageSize"], "params": {"value": 50},
    }]


def test_empty_page_size_falls_back_to_the_default():
    operation = page_size_patch(None).to_plotly_json()["operations"][0]
    assert operation["params"]["value"] == DEFAULT_PAGE_SIZE == 20
