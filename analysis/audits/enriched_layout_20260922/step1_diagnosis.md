# Step 1 — diagnosis (revised after Step 2 runtime inspection)

Starting commit: `e0ecbdbe4d93f320c2576362253a5fef215c8c4f`
(branch `adjudication/build-docs-and-prototype`).

## Components and stylesheets that control the tab

| Concern | Location |
|---|---|
| Filter panel rows/columns | `dashboard/layout/analysis/thematic.py:548-733` (the "Enriched Register" `dbc.AccordionItem`) |
| Filter label styling | `dashboard/assets/styles.css:345-352` (`.filter-label`) — **shared** |
| Table component + column widths | `dashboard/layout/analysis/thematic.py:743-800` (`dash_table.DataTable`, `style_cell_conditional`) |
| Table style dicts | `dashboard/components/table_styles.py:31-70` (`ENRICHED_TABLE_STYLES`) — enriched only |
| Table CSS (generic) | `dashboard/assets/styles.css:192-205` (`.dea-table … th/td`) — **shared** |
| Table CSS (scoped) | `dashboard/assets/styles.css:206-219` (`.enriched-register-table-container …`) — enriched only |
| Preview / rationale CSS | `dashboard/assets/styles.css:220-332` — enriched only |
| Rationale disclosure behaviour | `dashboard/assets/rationale_overflow.js` — enriched only |

### Sharing with Project Explorer

- `.dea-table` (styles.css:192-205) is used by the Enriched Register
  (`thematic.py:799`), the Project Explorer (`layout/explorer.py:139`) and the
  Uptake tab (`layout/analysis/uptake.py:184`). **Shared.**
- `.filter-label` (styles.css:345-352) is used by the Explorer, Datasets,
  Institutions and Thematic filter panels. **Shared.**
- `.enriched-register-table-container` and every `.enriched-*` / `.rationale-*`
  rule are used by the Enriched Register only. **Not shared.**
- `ENRICHED_TABLE_STYLES` is used only by `enriched-register-table`; the Explorer
  uses the separate `BROWSE_TABLE_STYLES`. **Not shared.**

All Step 3 edits were confined to enriched-only selectors and to the enriched
`AccordionItem`; no shared rule was modified. Explorer screenshots were still
captured in both runs as a control.

## How pinning is implemented (D5 prerequisite) — established at runtime

`fixed_columns={"headers": True, "data": 1}` (`thematic.py:776`). Dash's
DataTable renders the table **twice** inside `.dt-table-container__row-1`:

- `.cell-1-0.dash-fixed-column > table.cell-table` — the pinned copy;
- `.cell-1-1.dash-fixed-content > table.cell-table` — the scrolling copy.

Both copies contain all 17 cells per row and are laid out at the same origin
(both `x = 55.59`, `width = 3344` at 1440 px). Each copy hides the cells it does
not own with `visibility: hidden`; `.cell-1-0` has `clientWidth = 0` so only the
first column of the pinned copy is visible. The two tables compute their row
heights **independently**.

Runtime evidence (1440 px, F0):

- pinned copy, header cell 0: `innerHTML` present, height **69.5 px**;
- scrolling copy, header cell 0: `visibility: hidden` **and `innerHTML: ""`**,
  height **53.5 px**;
- body cells: both copies keep full `innerHTML` in every column, so collapsed
  body row heights match exactly (68 / 67 / 67 …).

## Defect-by-defect

| Defect | Cause | How established |
|---|---|---|
| **D1** "Per page" alone on a row | The second filter group's Bootstrap columns sum to **13**: `md=3+2+2+2+3+1` (`thematic.py:606,617,628,638,648,658`). A `dbc.Row` wraps past 12, so `Per page` (`md=1`) is pushed onto a new line. | **Established statically**, confirmed at runtime (`filterRowLineBreaks` row 2 has two distinct column tops at 768/1280/1440/1920). |
| **D2** filter grid overflows the right edge, controls cut off | **No cause — the defect was not reproduced.** At 768/1280/1440/1920 `document.scrollWidth == clientWidth` and no filter column's right edge exceeds the accordion body or the viewport. At 375 the page does overflow by 8 px (`scrollWidth 383`), but the overflowing element is `nav.dea-navbar > .container-fluid`, which overflows identically on the Overview, Explorer and Analysis tabs before the Enriched Register is ever opened. | **Rejected at runtime** (see `before/measurements.json`, `filters_w*_*.png`). |
| **D3** count floats mid-row, Download detached | `thematic.py:721-736`: the count `html.Div` carries `style={"paddingTop": "0.35rem", "textAlign": "center"}` inside a `dbc.Col(md=9)`, and the button sits in a separate `dbc.Col(md=3)` with `w-100`. The count is therefore centred in the first three quarters of the row, not aligned to the grid or the table. | **Established statically**, confirmed at runtime (`count.textAlign == "center"`, count spans 56→1050 with its text centred, button 1058→1384 at 1440 px). |
| **D4** inconsistent select widths / column boundaries | The three filter rows use unrelated `md` splits: `5+3+2+2`, `3+2+2+2+3+1`, `2+3+2+2+3`. Runtime column left edges at 1440 px: row B `52/609/943/1166`, row C `52/386/609/831/1054`, row D `52/274/609/831/1054`. | **Established statically**, confirmed at runtime. |
| **D5** pinned column out of step | Two independent tables (above). The pinned copy's header row is **69.5 px** because `▣ PROJECT ID` wraps to three lines inside the 90 px column; the scrolling copy's header row is **53.5 px** because its copy of that header cell is emptied, so its height is set by its own tallest header (two lines). Every body row in the pinned copy is therefore offset by exactly **16 px** (`maxAbsRowTopDelta = 16` at all five widths, both states). When a Rationale cell is expanded the divergence grows to **95.4 px** of row-top offset and **111.4 px** of row-height difference, because the `<details>` element exists in both copies and only the visible one receives `[open]`. | **Established at runtime.** The hypothesis in the instruction (separate rendering desynchronises the copies) is confirmed as the mechanism; the specific trigger is the emptied duplicate header cell, not the scoped CSS added in bc2e3ed/682d829. |
| **D6** mixed vertical alignment | `style_cell_conditional` (`thematic.py:762-775`) sets `"verticalAlign": "top"` on 13 columns but omits it on **Project ID**, **Accreditation Date**, **record_linkage** and **substantive_domain_count**, which therefore fall back to the browser default `middle`. | **Established statically**, confirmed at runtime (computed `vertical-align` is `middle` for exactly those four columns at all five widths). |
| **D7** header labels wrap unevenly | Partly. Within the **scrolling** header row every cell measures 53.5 px, because table row layout equalises cell heights — so header height is *not* inconsistent there, even though individual labels wrap to one or two lines. The inconsistency is between the pinned header row (69.5 px, three lines) and the scrolling header row (53.5 px). Same cause as D5. | **Established at runtime**; the "inconsistent header height" part is confirmed only across the pinned/scrolling split, and rejected within the scrolling header. |

## Additional defect found

**D8 (new).** A filter label that wraps to two lines pushes its own control down,
so controls in the same row no longer share a baseline. Visible at 1440 px where
`DATASET SOURCE ORGANISATION` wraps and its select sits ~17 px lower than
`SEARCH`, `DATASET` and `DOMAIN COUNT`. Cause: `.filter-label` has no reserved
height, so each column's control starts wherever its label ends. Established
statically and from `before/filters_w1440_F0.png`.
