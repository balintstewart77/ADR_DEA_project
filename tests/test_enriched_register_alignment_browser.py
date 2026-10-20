"""Browser check that the pinned Project ID column stays level with the table.

fixed_columns renders the Enriched Register body twice, and each copy sizes its
rows independently. This test drives a real browser and fails if the two copies'
rows drift apart, collapsed or with a rationale expanded. It needs Playwright
and its Chromium build, and is skipped where they are not installed.
"""

import threading

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from werkzeug.serving import make_server


ROW_OFFSET = """() => {
    const table = document.querySelector('#enriched-register-table');
    const pinned = [...table.querySelectorAll('.cell-1-0 tr')];
    const scrolling = [...table.querySelectorAll('.cell-1-1 tr')];
    return Math.max(...pinned.map((row, i) => Math.abs(
        row.getBoundingClientRect().top - scrolling[i].getBoundingClientRect().top
    )));
}"""

OPEN_COUNTS = """() => ['.cell-1-0', '.cell-1-1'].map((copy) => document.querySelectorAll(
    `#enriched-register-table ${copy} details.rationale-details[open]`
).length)"""


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
def browser():
    with sync_api.sync_playwright() as playwright:
        try:
            chromium = playwright.chromium.launch()
        except sync_api.Error as exc:
            pytest.skip(f"Playwright Chromium unavailable: {exc}")
        yield chromium
        chromium.close()


@pytest.mark.parametrize("width", [375, 1280, 1920])
def test_pinned_rows_stay_aligned_when_rationales_expand(browser, dashboard_url, width):
    page = browser.new_page(viewport={"width": width, "height": 900})
    try:
        page.goto(dashboard_url)
        page.get_by_role("tab", name="Portfolio Analysis").click()
        page.get_by_role("tab", name="Thematic Analysis (Experimental)").click()
        page.get_by_role("button", name="Enriched Register").click()
        page.wait_for_function(
            "document.querySelectorAll('#enriched-register-table .cell-1-1 tr').length === 21"
        )
        page.wait_for_function("!!window.__enrichedRationaleOverflowManager")

        assert page.evaluate(ROW_OFFSET) < 0.5

        toggles = page.locator(
            "#enriched-register-table .cell-1-1 "
            "details.rationale-details[data-overflow='true'] > summary"
        )
        assert toggles.count() >= 2

        toggles.nth(0).click()
        toggles.nth(1).click()
        page.wait_for_function(f"({OPEN_COUNTS})().join() === '2,2'", timeout=5000)
        assert page.evaluate(ROW_OFFSET) < 0.5

        toggles.nth(0).click()
        toggles.nth(1).click()
        page.wait_for_function(f"({OPEN_COUNTS})().join() === '0,0'", timeout=5000)
        assert page.evaluate(ROW_OFFSET) < 0.5
    finally:
        page.close()
