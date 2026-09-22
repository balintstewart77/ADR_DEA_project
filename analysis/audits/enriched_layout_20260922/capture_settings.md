# Capture settings — Enriched Register layout audit (2026-09-22)

Used unchanged for the `before/` (Step 2) and `after/` (Step 5) runs.
Implemented in `capture_layout.py` in this directory; content baselines in
`extract_baseline.py`.

## Environment

- Browser: Chromium via Playwright, headless.
- Chromium version: **153.0.8010.12** (Playwright 1.63.0).
- Installed for this task only, into the project venv, with
  `python -m pip install playwright` then `python -m playwright install chromium`.
  No tracked project file (requirements*.txt, config) was modified.
- App: `dashboard.app.app` served in-process by the capture script on
  `127.0.0.1:<ephemeral port>`, `debug=False`, no reloader.

## Viewport

- Widths: 375, 768, 1280, 1440, 1920 px.
- Height: 900 px. Device scale factor 1. Page zoom 100% (Playwright default).

## Table state

- Page size: 20 (the layout default, `page_size=20`).
- Page number: 1 (`page_current=0`, never changed).
- Sort: the table's default sort — `sort_action="custom"` with the DataTable's
  default `sort_by` of `[]`. `_sort_enriched_table_records` returns the records
  unchanged when `sort_by` is empty, so the default order is the order produced
  by `_enriched_register_base` after filtering. No user sort is applied.

## Navigation

Main tab "Portfolio Analysis" → sub-tab "Thematic Analysis (Experimental)" →
accordion item "Enriched Register" (the accordion starts collapsed).

## Filter states

- **F0** — no filters. Every select at its default `"ALL"`; search empty; both
  year sliders at their full default range `[2019, 2026]`.
  Yields `Showing 1,343 accreditation records`.
- **F1** — two selects changed from F0, chosen through the real dropdowns:
  - Dataset: label `Annual Survey of Hours and Earnings (ASHE)  (206 projects)`,
    option value `Annual Survey of Hours and Earnings (ASHE)`.
  - Domain: label `Labour Market & Employment  (454 projects)`,
    option value `Labour Market & Employment`.
  Both options exist; no substitution was needed.
  Yields `Showing 129 accreditation records` — 7 pages at page size 20.

## Settling predicate

Applied before **every** screenshot, in both runs. All of the following must hold
on three consecutive polls 150 ms apart:

1. No in-flight `POST /_dash-update-component` requests (counted from Playwright
   `request` / `requestfinished` / `requestfailed` events).
2. No element matching `._dash-loading, .dash-loading, ._dash-loading-callback`
   is present.
3. `document.fonts.ready` has resolved (`window.__fontsReady === true`).
4. `#enriched-register-table` contains at least two `table.cell-table` elements
   and **each** has exactly `20 + 1` `tr` (20 data rows for page 1 plus the
   header row).

A 400 ms `wait_for_timeout` is applied **after** the predicate passes, as margin
only. It is never the sole readiness criterion.

## Screenshot matrix (per run)

Per width (5) per filter state (2):

- `filters_w<W>_<state>.png` — the whole filter panel, clipped from the top of
  the first filter row to the bottom of the count/Download row, captured with
  `full_page=True` so a panel taller than the viewport is still captured whole.
  10 filter-panel captures per run, as expected.
- `table_w<W>_<state>_hleft_collapsed.png` — table clipped to
  `#enriched-register-table`, horizontal scroller (`.dt-table-container__row-1`)
  at `scrollLeft = 0`.
- `table_w<W>_<state>_hright_collapsed.png` — same, scroller at `scrollWidth`.
  Where the scroller has no horizontal overflow the capture is skipped and
  `"no horizontal scroll at this width"` is recorded in `measurements.json`
  instead.
- F1 only, for D5: `table_w<W>_F1_<hpos>_expanded.png` — as above after
  expanding one multiline cell with an existing inline control.
  The only control that expands content **inline in the table** is the Rationale
  column's `<details>` "Read more" disclosure; "View full value" and
  "View details" open the record modal rather than expanding the row.

`measurements.json` records, for every capture: page/scroller overflow, the two
tables' header heights, per-row top and height deltas between the pinned and the
scrolling table, every body cell's computed `vertical-align`, the header cell
heights, the filter grid's per-column geometry, and the count/Download geometry.

Explorer control captures (`explorer_w<W>.png`, 5 per run) are taken because the
Project Explorer shares the `.dea-table` and `.filter-label` CSS with this tab.
