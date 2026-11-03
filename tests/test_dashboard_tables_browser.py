"""Browser checks for the dashboard's AG Grid tables.

These drive the real dashboard in Chromium: sorting, paging, the pinned
Project ID column, the rationale toggle, the record modal and its keyboard
access. They need Playwright and its Chromium build, and are skipped where
those are not installed (``--require-browser`` makes that a failure).
"""

import importlib
import re
import threading

import pytest
from werkzeug.serving import make_server

pytestmark = pytest.mark.browser

GRID = "#enriched-register-table"
ROWS = f"{GRID} .ag-center-cols-container .ag-row"

# Largest gap between a pinned Project ID row and the rest of its row.
ROW_DRIFT = f"""() => {{
    const grid = document.querySelector('{GRID}');
    const pinned = [...grid.querySelectorAll('.ag-pinned-left-cols-container .ag-row')];
    return Math.max(...pinned.map((row) => {{
        const index = row.getAttribute('row-index');
        const other = grid.querySelector(`.ag-center-cols-container .ag-row[row-index="${{index}}"]`);
        const a = row.getBoundingClientRect();
        const b = other.getBoundingClientRect();
        return Math.abs(a.top - b.top) + Math.abs(a.height - b.height);
    }}));
}}"""

OPEN_COUNT = f"() => document.querySelectorAll('{GRID} details.rationale-details[open]').length"

SORTED_IDS = f"""(state) => {{
    const api = dash_ag_grid.getApi('{GRID[1:]}');
    api.applyColumnState({{state, defaultState: {{sort: null}}}});
    const ids = [];
    api.forEachNodeAfterFilterAndSort((node) => ids.push(node.data.id));
    return ids;
}}"""


@pytest.fixture(scope="module")
def dashboard_url():
    from dashboard.app import app

    server = make_server("127.0.0.1", 0, app.server, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


@pytest.fixture(scope="module")
def browser(pytestconfig):
    try:
        sync_api = importlib.import_module("playwright.sync_api")
    except ImportError:
        if pytestconfig.getoption("--require-browser"):
            pytest.fail("Browser CI requires Playwright")
        pytest.skip("Playwright is not installed")
    with sync_api.sync_playwright() as playwright:
        try:
            chromium = playwright.chromium.launch()
        except sync_api.Error as exc:
            if pytestconfig.getoption("--require-browser"):
                pytest.fail(f"Browser CI requires Chromium: {exc}")
            pytest.skip(f"Playwright Chromium unavailable: {exc}")
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    yield page
    page.close()


def _open_enriched_register(page, url):
    page.goto(url)
    page.get_by_role("tab", name="Portfolio Analysis").click()
    page.get_by_role("tab", name="Thematic Analysis (Experimental)").click()
    page.get_by_role("button", name="Enriched Register").click()
    page.wait_for_function(f"document.querySelectorAll('{ROWS}').length === 20")
    page.wait_for_function("!!window.__enrichedRationaleOverflowManager")


def _modal(page):
    return page.locator("#enriched-record-detail-modal")


def _focused_cell(page):
    return page.evaluate("""() => {
        const cell = document.activeElement.closest('.ag-cell');
        return cell && [cell.closest('.ag-row').getAttribute('row-id'), cell.getAttribute('col-id')];
    }""")


@pytest.mark.parametrize("width", [375, 1280, 1920])
def test_pinned_rows_stay_aligned_when_rationales_expand(browser, dashboard_url, width):
    page = browser.new_page(viewport={"width": width, "height": 900})
    try:
        _open_enriched_register(page, dashboard_url)
        assert page.evaluate(ROW_DRIFT) < 0.5

        toggles = page.locator(f"{GRID} details.rationale-details[data-overflow='true'] > summary")
        assert toggles.count() >= 2
        first_row = page.locator(ROWS).first
        collapsed_height = first_row.bounding_box()["height"]

        toggles.nth(0).click()
        toggles.nth(1).click()
        page.wait_for_function(f"({OPEN_COUNT})() === 2", timeout=5000)
        page.wait_for_function(f"({ROW_DRIFT})() < 0.5", timeout=5000)
        assert first_row.bounding_box()["height"] > collapsed_height

        toggles.nth(0).click()
        toggles.nth(1).click()
        page.wait_for_function(f"({OPEN_COUNT})() === 0", timeout=5000)
        page.wait_for_function(f"({ROW_DRIFT})() < 0.5", timeout=5000)
    finally:
        page.close()


# The display columns show identical HTML; the grid must sort on the source values.
SORT_ROWS = [
    {"id": "r3", "Title": "Beta", "Accreditation Date": "2023-12-01", "substantive_domain_count": 10, "rationale": "Same"},
    {"id": "r1", "Title": "Alpha", "Accreditation Date": "2023-02-15", "substantive_domain_count": 2, "rationale": "Same"},
    {"id": "r2", "Title": "Gamma", "Accreditation Date": "2024-01-01", "substantive_domain_count": None, "rationale": None},
    {"id": "r4", "Title": "Delta", "Accreditation Date": "2023-03-20", "substantive_domain_count": 2, "rationale": "Alpha"},
]
for _row in SORT_ROWS:
    _row.update({"Title_display": "Same preview", "rationale_display": "Same preview"})


SORT_CASES = [
    ([("rationale_display", "asc")], ["r4", "r3", "r1", "r2"]),
    ([("rationale_display", "desc")], ["r3", "r1", "r4", "r2"]),
    ([("Title_display", "asc")], ["r1", "r3", "r4", "r2"]),
    ([("substantive_domain_count", "asc")], ["r1", "r4", "r3", "r2"]),
    ([("substantive_domain_count", "desc")], ["r3", "r1", "r4", "r2"]),
    ([("Accreditation Date", "asc")], ["r1", "r4", "r3", "r2"]),
    ([("rationale_display", "asc"), ("Title_display", "asc")], ["r4", "r1", "r3", "r2"]),
]


def test_sorting_uses_source_values_keeps_ties_and_puts_missing_last(page, dashboard_url):
    _open_enriched_register(page, dashboard_url)
    page.evaluate(f"(rows) => dash_ag_grid.getApi('{GRID[1:]}').setGridOption('rowData', rows)", SORT_ROWS)
    for state, expected in SORT_CASES:
        column_state = [
            {"colId": column, "sort": direction, "sortIndex": index}
            for index, (column, direction) in enumerate(state)
        ]
        assert page.evaluate(SORTED_IDS, column_state) == expected, state


def test_blank_text_is_a_value_and_header_clicks_sort(page, dashboard_url):
    _open_enriched_register(page, dashboard_url)
    rows = [
        {"id": "blank", "Accreditation Date": ""},
        {"id": "missing", "Accreditation Date": None},
        {"id": "dated", "Accreditation Date": "2023-01-01"},
    ]
    page.evaluate(f"(rows) => dash_ag_grid.getApi('{GRID[1:]}').setGridOption('rowData', rows)", rows)
    header = page.locator(f"{GRID} .ag-header-cell[col-id='Accreditation Date']")
    order = f"""() => {{
        const ids = [];
        dash_ag_grid.getApi('{GRID[1:]}').forEachNodeAfterFilterAndSort((n) => ids.push(n.data.id));
        return ids.join();
    }}"""
    header.click()
    page.wait_for_function(f"({order})() === 'blank,dated,missing'")
    header.click()
    page.wait_for_function(f"({order})() === 'dated,blank,missing'")


def test_record_modal_opens_by_record_id_and_keyboard_returns_focus(page, dashboard_url):
    _open_enriched_register(page, dashboard_url)
    row = page.locator(ROWS).first
    record_id = row.get_attribute("row-id")

    row.locator(".enriched-detail-trigger").first.click()
    _modal(page).wait_for(state="visible")
    assert record_id in page.inner_text("#enriched-record-detail-body")

    page.keyboard.press("Escape")
    _modal(page).wait_for(state="hidden")
    page.wait_for_function("!!document.activeElement.closest('.ag-cell')")
    assert _focused_cell(page) == [record_id, "details_action"]

    # Focus is on the grid cell, not its button: Enter presses the button.
    page.keyboard.press("Enter")
    _modal(page).wait_for(state="visible")
    page.click("#enriched-record-detail-close")
    _modal(page).wait_for(state="hidden")
    page.wait_for_function("!!document.activeElement.closest('.ag-cell')")
    assert _focused_cell(page) == [record_id, "details_action"]

    rationale = row.locator(".ag-cell[col-id='rationale_display']")
    rationale.focus()
    page.keyboard.press("Enter")
    page.wait_for_function(f"({OPEN_COUNT})() === 1", timeout=5000)
    assert not _modal(page).is_visible()


def test_record_modal_closes_when_its_row_leaves_the_page(page, dashboard_url):
    _open_enriched_register(page, dashboard_url)
    page.locator(ROWS).first.locator(".enriched-detail-trigger").first.click()
    _modal(page).wait_for(state="visible")
    page.evaluate(f"() => dash_ag_grid.getApi('{GRID[1:]}').paginationGoToNextPage()")
    _modal(page).wait_for(state="hidden", timeout=5000)


def test_explorer_page_size_clear_filters_and_register_text_tooltips(page, dashboard_url):
    page.goto(dashboard_url)
    page.get_by_role("tab", name="Project Explorer").click()
    rows = "#browse-table .ag-center-cols-container .ag-row"
    summary = page.locator("#browse-table .ag-paging-row-summary-panel")
    page.wait_for_function(f"document.querySelectorAll('{rows}').length === 20")

    # A tooltip shows the register text as written, line breaks included.
    register_text = page.evaluate("""() => {
        const api = dash_ag_grid.getApi('browse-table');
        return api.getDisplayedRowAtIndex(0).data['Researchers_tooltip'];
    }""")
    page.locator("#browse-table .ag-center-cols-container [col-id='Researchers']").first.hover()
    tooltip = page.locator(".ag-tooltip")
    tooltip.wait_for(state="visible")

    def lines(text):
        return [re.sub(r"\s+", " ", line).strip() for line in text.strip().splitlines()]

    assert len(lines(register_text)) > 1
    assert lines(tooltip.inner_text()) == lines(register_text)

    page.click("#browse-page-size")
    page.get_by_role("option", name="50", exact=True).click()
    page.wait_for_function(f"document.querySelectorAll('{rows}').length === 50")
    page.click("#browse-table .ag-paging-button[aria-label='Next Page']")
    assert summary.inner_text().startswith("51 to 100")
    page.click("#browse-clear-filters-btn")
    page.wait_for_function(
        "document.querySelector('#browse-table .ag-paging-row-summary-panel').innerText.startsWith('1 to 50')"
    )


def test_grids_render_from_local_assets_without_errors(page, dashboard_url):
    errors, external = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: message.type == "error" and errors.append(message.text))
    page.on("request", lambda request: (
        request.url.startswith(("http://", "https://"))
        and not request.url.startswith(dashboard_url)
        and external.append(request.url)
    ))

    page.goto(dashboard_url)
    page.get_by_role("tab", name="Project Explorer").click()
    page.wait_for_selector("#browse-table .ag-center-cols-container .ag-row")
    page.get_by_role("tab", name="Portfolio Analysis").click()
    page.get_by_role("tab", name="Dataset Demand").click()
    page.wait_for_selector("#uptake-adoption-summary-table .ag-center-cols-container .ag-row")
    page.get_by_role("tab", name="Thematic Analysis (Experimental)").click()
    page.get_by_role("button", name="Enriched Register").click()
    page.wait_for_selector(f"{ROWS}")

    assert errors == []
    assert external == []
