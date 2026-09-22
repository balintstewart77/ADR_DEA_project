"""Screenshot and measure the Enriched Register tab (filter panel + table).

Starts the real Dash app in-process, drives it with headless Chromium via
Playwright, and writes screenshots plus a measurements JSON per width/state.
Presentation evidence only: it never writes to application state beyond the
user-facing filter controls.

Usage:
    python analysis/audits/enriched_layout_20260922/capture_layout.py <out_dir> [--explorer]
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from playwright.sync_api import sync_playwright  # noqa: E402

import dashboard.app as dashboard_app  # noqa: E402

WIDTHS = [375, 768, 1280, 1440, 1920]
VIEWPORT_HEIGHT = 900
DEVICE_SCALE = 1
EXPECTED_ROWS = 20  # page size 20, page 1; both F0 (1,343) and F1 (129) fill a page

F1_DATASET_LABEL = "Annual Survey of Hours and Earnings (ASHE)"
F1_DOMAIN_LABEL = "Labour Market & Employment"

TABLE = "#enriched-register-table"
SCROLLER = f"{TABLE} .dt-table-container__row-1"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server() -> int:
    port = _free_port()
    threading.Thread(
        target=lambda: dashboard_app.app.run(
            debug=False, host="127.0.0.1", port=port, use_reloader=False,
        ),
        daemon=True,
    ).start()
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return port
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("Dash server did not start")


class Inflight:
    """Counts in-flight POSTs to /_dash-update-component for the settling predicate."""

    def __init__(self, page):
        self.n = 0
        page.on("request", self._req)
        page.on("requestfinished", self._done)
        page.on("requestfailed", self._done)

    def _req(self, request):
        if "/_dash-update-component" in request.url:
            self.n += 1

    def _done(self, request):
        if "/_dash-update-component" in request.url:
            self.n -= 1


SETTLE_JS = """(expectedRows) => {
  if (document.querySelector('._dash-loading, .dash-loading, ._dash-loading-callback')) return false;
  if (!window.__fontsReady) return false;
  const t = document.querySelector('#enriched-register-table');
  if (!t) return false;
  const tables = t.querySelectorAll('table.cell-table');
  if (tables.length < 2) return false;
  // Each cell-table holds one header row plus the page's data rows.
  for (const tb of tables) {
    if (tb.querySelectorAll('tr').length !== expectedRows + 1) return false;
  }
  return true;
}"""


def settle(page, inflight, expected_rows=EXPECTED_ROWS, margin_ms=400):
    page.evaluate("document.fonts.ready.then(() => { window.__fontsReady = true; })")
    deadline = time.time() + 60
    stable = 0
    while time.time() < deadline:
        ok = inflight.n == 0 and page.evaluate(SETTLE_JS, expected_rows)
        stable = stable + 1 if ok else 0
        if stable >= 3:
            page.wait_for_timeout(margin_ms)  # additional margin only, never the sole criterion
            return True
        page.wait_for_timeout(150)
    raise RuntimeError("settling predicate never satisfied")


def open_enriched(page):
    page.get_by_role("tab", name="Portfolio Analysis").click()
    page.wait_for_selector("#analysis-tabs", state="visible")
    page.get_by_role("tab", name="Thematic Analysis (Experimental)").click()
    page.get_by_role("button", name="Enriched Register").click()
    page.wait_for_selector(TABLE, state="visible")


def select_dropdown(page, dropdown_id, label_text):
    """Pick an option in a dcc.Dropdown by its visible label, then verify it stuck."""
    root = page.locator(f"#{dropdown_id}")
    root.scroll_into_view_if_needed()
    root.click()
    popup_id = root.get_attribute("aria-controls")
    popup = page.locator(f'[id="{popup_id}"]')
    popup.wait_for(state="visible", timeout=15000)
    search = popup.locator("input.dash-dropdown-search").first
    search.click()
    page.keyboard.type(label_text, delay=6)
    page.wait_for_timeout(400)
    option = popup.locator('[role="option"]').filter(has_text=label_text).first
    option.wait_for(state="visible", timeout=15000)
    option.click()
    page.wait_for_timeout(300)
    shown = root.locator(".dash-dropdown-value").first.inner_text().strip()
    if label_text not in shown:
        raise RuntimeError(f"{dropdown_id}: expected {label_text!r}, got {shown!r}")
    return shown


MEASURE_JS = r"""() => {
  const out = {};
  const doc = document.documentElement;
  out.page = {scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth,
              horizontalOverflow: doc.scrollWidth > doc.clientWidth + 1};
  let body = null;
  document.querySelectorAll('.accordion-body').forEach(b => {
    if (b.querySelector('#enriched-register-table')) body = b;
  });
  if (body) {
    const br = body.getBoundingClientRect();
    out.panel = {left: Math.round(br.left), right: Math.round(br.right), width: Math.round(br.width)};
    out.filterRows = [...body.children].filter(e => e.classList.contains('row')).map((r, i) => {
      const rr = r.getBoundingClientRect();
      return {
        index: i,
        top: Math.round(rr.top), left: Math.round(rr.left), right: Math.round(rr.right),
        cols: [...r.children].map(c => {
          const cr = c.getBoundingClientRect();
          const lab = c.querySelector('.filter-label');
          return {
            cls: c.className,
            label: lab ? lab.innerText.trim() : (c.innerText || '').trim().slice(0, 28),
            left: Math.round(cr.left), right: Math.round(cr.right),
            width: Math.round(cr.width), top: Math.round(cr.top),
            clippedRight: cr.right > out.panel.right + 1,
            offscreen: cr.right > doc.clientWidth + 1,
          };
        }),
      };
    });
    // rows whose children start on more than one visual line
    out.filterRowLineBreaks = out.filterRows.map(r => {
      const tops = [...new Set(r.cols.map(c => c.top))];
      return {index: r.index, distinctTops: tops.length, tops: tops,
              labels: r.cols.map(c => c.label)};
    });
  }
  const count = document.querySelector('#enriched-browse-count');
  const dl = document.querySelector('#enriched-download-btn');
  if (count) {
    const cr = count.getBoundingClientRect();
    out.count = {text: count.innerText.trim(), left: Math.round(cr.left),
                 right: Math.round(cr.right), top: Math.round(cr.top),
                 textAlign: getComputedStyle(count).textAlign};
  }
  if (dl) {
    const dr = dl.getBoundingClientRect();
    out.download = {left: Math.round(dr.left), right: Math.round(dr.right), top: Math.round(dr.top)};
  }

  const t = document.querySelector('#enriched-register-table');
  if (!t) return out;
  const scroller = t.querySelector('.dt-table-container__row-1');
  out.table = {
    scroller: scroller ? {scrollWidth: scroller.scrollWidth, clientWidth: scroller.clientWidth,
                          scrollLeft: Math.round(scroller.scrollLeft),
                          hasHorizontalScroll: scroller.scrollWidth > scroller.clientWidth + 1} : null,
  };
  const fixed = t.querySelector('.dash-fixed-column table.cell-table');
  const content = t.querySelector('.dash-fixed-content table.cell-table');
  const rows = (tb) => [...tb.querySelectorAll('tr')].map(tr => {
    const r = tr.getBoundingClientRect();
    return {top: +r.top.toFixed(2), height: +r.height.toFixed(2)};
  });
  if (fixed && content) {
    const f = rows(fixed), c = rows(content);
    out.table.headerHeights = {fixed: f[0].height, content: c[0].height};
    out.table.rowTopDeltas = f.slice(0, Math.min(f.length, c.length)).map(
      (fr, i) => +(fr.top - c[i].top).toFixed(2));
    out.table.maxAbsRowTopDelta = Math.max(...out.table.rowTopDeltas.map(Math.abs));
    out.table.rowHeightDeltas = f.slice(0, Math.min(f.length, c.length)).map(
      (fr, i) => +(fr.height - c[i].height).toFixed(2));
    out.table.maxAbsRowHeightDelta = Math.max(...out.table.rowHeightDeltas.map(Math.abs));
    // header cell heights across the scrolling table
    out.table.contentHeaderCells = [...content.querySelectorAll('tr')[0].children].map(th => ({
      col: th.getAttribute('data-dash-column'),
      text: (th.innerText || '').replace(/\n/g, '|').trim(),
      height: +th.getBoundingClientRect().height.toFixed(2),
      lines: Math.round(th.getBoundingClientRect().height),
    }));
    out.table.fixedHeaderCell = (() => {
      const th = content && fixed.querySelectorAll('tr')[0].children[0];
      return th ? {text: (th.innerText || '').replace(/\n/g, '|').trim(),
                   height: +th.getBoundingClientRect().height.toFixed(2)} : null;
    })();
    // vertical alignment of every body cell in the first data row
    const vrow = (tb) => [...tb.querySelectorAll('tr')[1].children].map(td => ({
      col: td.getAttribute('data-dash-column'),
      verticalAlign: getComputedStyle(td).verticalAlign,
    })).filter(x => x.col);
    out.table.bodyVerticalAlign = [...vrow(fixed), ...vrow(content)]
      .reduce((acc, x) => { acc[x.col] = x.verticalAlign; return acc; }, {});
    out.table.distinctBodyVerticalAlign =
      [...new Set(Object.values(out.table.bodyVerticalAlign))];
    out.table.columnOrder = [...content.querySelectorAll('tr')[0].children]
      .map(th => th.getAttribute('data-dash-column'));
  }
  return out;
}"""


def table_clip(page):
    box = page.locator(TABLE).bounding_box()
    scroll = page.evaluate("() => ({x: window.scrollX, y: window.scrollY})")
    return {
        "x": box["x"] + scroll["x"], "y": box["y"] + scroll["y"],
        "width": box["width"], "height": box["height"],
    }


def panel_clip(page):
    box = page.evaluate("""() => {
      let body = null;
      document.querySelectorAll('.accordion-body').forEach(b => {
        if (b.querySelector('#enriched-register-table')) body = b;
      });
      const rows = [...body.children].filter(e => e.classList.contains('row'));
      const first = rows[0].getBoundingClientRect();
      const last = rows[rows.length - 1].getBoundingClientRect();
      return {x: 0, y: first.top + window.scrollY - 8,
              width: document.documentElement.clientWidth,
              height: (last.bottom - first.top) + 16};
    }""")
    return box


def scroll_table(page, to):
    page.evaluate(
        """([sel, to]) => {
            const el = document.querySelector(sel);
            el.scrollLeft = to === 'right' ? el.scrollWidth : 0;
        }""",
        [SCROLLER, to],
    )
    page.wait_for_timeout(250)


def expand_first_rationale(page):
    """Expand a multiline cell with the existing inline control (Rationale 'Read more')."""
    summary = page.locator(f"{TABLE} .dash-fixed-content .rationale-details summary").first
    if summary.count() == 0:
        return False
    summary.scroll_into_view_if_needed()
    summary.click()
    page.wait_for_timeout(350)
    return page.locator(f"{TABLE} .dash-fixed-content .rationale-details[open]").count() > 0


def capture(out_dir, with_explorer=False):
    os.makedirs(out_dir, exist_ok=True)
    port = start_server()
    results = {}
    notes = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        print("chromium:", browser.version)
        results["_browser_version"] = browser.version
        for width in WIDTHS:
            for state in ("F0", "F1"):
                key = f"w{width}_{state}"
                page = browser.new_page(
                    viewport={"width": width, "height": VIEWPORT_HEIGHT},
                    device_scale_factor=DEVICE_SCALE,
                )
                inflight = Inflight(page)
                page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
                open_enriched(page)
                settle(page, inflight)
                selections = {}
                if state == "F1":
                    selections["dataset"] = select_dropdown(
                        page, "enriched-dataset-filter", F1_DATASET_LABEL)
                    settle(page, inflight)
                    selections["domain"] = select_dropdown(
                        page, "enriched-domain-filter", F1_DOMAIN_LABEL)
                    settle(page, inflight)

                entry = {"selections": selections, "screenshots": {}}

                # Filter panel: one capture per width per state.
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(150)
                fname = f"filters_w{width}_{state}.png"
                page.screenshot(path=os.path.join(out_dir, fname), clip=panel_clip(page),
                                full_page=True)
                entry["screenshots"]["filters"] = fname

                for pos in ("hleft", "hright"):
                    m = page.evaluate(MEASURE_JS)
                    has_scroll = m["table"]["scroller"]["hasHorizontalScroll"]
                    if pos == "hright" and not has_scroll:
                        entry.setdefault("notes", []).append(
                            f"no horizontal scroll at this width ({width}px, {state})")
                        continue
                    scroll_table(page, "left" if pos == "hleft" else "right")
                    fname = f"table_w{width}_{state}_{pos}_collapsed.png"
                    page.screenshot(path=os.path.join(out_dir, fname), clip=table_clip(page),
                                    full_page=True)
                    entry["screenshots"][f"table_{pos}_collapsed"] = fname
                    entry[f"measure_{pos}_collapsed"] = page.evaluate(MEASURE_JS)

                if state == "F1":
                    expanded = expand_first_rationale(page)
                    entry["expanded_control_used"] = (
                        "Rationale <details> 'Read more' (inline)" if expanded else None)
                    if expanded:
                        for pos in ("hleft", "hright"):
                            m = page.evaluate(MEASURE_JS)
                            if pos == "hright" and not m["table"]["scroller"]["hasHorizontalScroll"]:
                                entry.setdefault("notes", []).append(
                                    f"no horizontal scroll at this width ({width}px, {state}, expanded)")
                                continue
                            scroll_table(page, "left" if pos == "hleft" else "right")
                            fname = f"table_w{width}_{state}_{pos}_expanded.png"
                            page.screenshot(path=os.path.join(out_dir, fname),
                                            clip=table_clip(page), full_page=True)
                            entry["screenshots"][f"table_{pos}_expanded"] = fname
                            entry[f"measure_{pos}_expanded"] = page.evaluate(MEASURE_JS)
                    else:
                        entry.setdefault("notes", []).append(
                            "no inline expansion control found; D5 limited to collapsed rows")

                results[key] = entry
                print(key, "done")
                page.close()

        if with_explorer:
            for width in WIDTHS:
                page = browser.new_page(
                    viewport={"width": width, "height": VIEWPORT_HEIGHT},
                    device_scale_factor=DEVICE_SCALE)
                page.goto(f"http://127.0.0.1:{port}", wait_until="networkidle")
                page.get_by_role("tab", name="Project Explorer").click()
                page.wait_for_selector("#browse-table", state="visible")
                page.wait_for_timeout(1500)
                fname = f"explorer_w{width}.png"
                page.screenshot(path=os.path.join(out_dir, fname), full_page=True)
                results[f"explorer_w{width}"] = {"screenshots": {"explorer": fname}}
                print("explorer", width, "done")
                page.close()

        browser.close()

    path = os.path.join(out_dir, "measurements.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=1, sort_keys=True, ensure_ascii=False)
    print("wrote", path)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    capture(args[0] if args else os.path.join(_HERE, "before"),
            with_explorer="--explorer" in sys.argv)
