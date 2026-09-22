# Step 5 — visual verification and resolution

Same capture settings for both runs (`capture_settings.md`), same script
(`capture_layout.py`), same Chromium 153.0.8010.12.

Filenames below are relative to `before/` and `after/`.

## Filter panel defects (one capture per width per filter state)

The filter panel does not move with the table's horizontal scroll, so scroll
position is **not applicable** to D1–D4 and D8.

| Defect | Width | F0 | F1 | Evidence |
|---|---|---|---|---|
| **D1** Per page alone on a row | 375 | not applicable (all controls stack) | not applicable | `filters_w375_F0.png`, `filters_w375_F1.png` |
| | 768 | **resolved** | **resolved** | `filters_w768_*.png` |
| | 1280 | **resolved** | **resolved** | `filters_w1280_*.png` |
| | 1440 | **resolved** | **resolved** | `filters_w1440_*.png` |
| | 1920 | **resolved** | **resolved** | `filters_w1920_*.png` |
| **D2** grid overflows / controls clipped | all five | **not applicable — rejected in Step 2** | same | `before/filters_w*_*.png`, `before/measurements.json` |
| **D3** count floats mid-row, Download detached | 375 | **resolved** (count and button stack, both left-aligned to the grid) | **resolved** | `filters_w375_*.png` |
| | 768 / 1280 / 1440 / 1920 | **resolved** (count at the grid's left edge, Download at its right edge, one row) | **resolved** | `filters_w{768,1280,1440,1920}_*.png` |
| **D4** inconsistent widths / boundaries | 375 | not applicable (single column) | not applicable | `filters_w375_*.png` |
| | 768 | **resolved** (three equal columns, boundaries 52 / 273 / 495) | **resolved** | `filters_w768_*.png` |
| | 1280 | **resolved** (boundaries 52 / 248 / 444 / 640 / 836 / 1032) | **resolved** | `filters_w1280_*.png` |
| | 1440 | **resolved** (52 / 274 / 497 / 720 / 943 / 1166) | **resolved** | `filters_w1440_*.png` |
| | 1920 | **resolved** (52 / 354 / 657 / 960 / 1263 / 1566) | **resolved** | `filters_w1920_*.png` |
| **D8** wrapped label pushes its control out of line | 375 | not applicable (stacked) | not applicable | `filters_w375_*.png` |
| | 768 / 1280 / 1440 / 1920 | **resolved for the selects**; the Search text input still sits 4 px higher than the dropdowns on its line because it is intrinsically 4 px taller and the column now bottom-aligns its control | same | `filters_w*_*.png`, `after/d8_control_tops.json` |

In every after capture, `measurements.json` reports no filter column whose right
edge exceeds the accordion body or the viewport, at any width or state.

## Table defects

Horizontal scrolling exists at **every** tested width (scroller content 3344 px
against 264–1809 px of viewport), so both `hleft` and `hright` were captured
everywhere; no "no horizontal scroll at this width" case arose.

| Defect | Width | State | hleft | hright | Evidence |
|---|---|---|---|---|---|
| **D5** pinned header taller; rows offset — **collapsed** | 375, 768, 1280, 1440, 1920 | F0 and F1 | **resolved** (header 72 / 72, max row-top delta 0.00 px, was 69.5 / 53.5 and 16 px) | **resolved** (same numbers) | `table_w*_F{0,1}_h{left,right}_collapsed.png` |
| **D5** — **expanded** (Rationale "Read more" open) | 375, 768, 1280, 1440, 1920 | F1 | **not resolved** — max row-top delta 111.39 px (was 95.40 px) | **not resolved** — same | `table_w*_F1_h{left,right}_expanded.png` |
| **D6** mixed vertical alignment | all five | F0 and F1 | **resolved** — computed `vertical-align` is `top` for all 17 columns (was `top` for 13, `middle` for Project ID, Accreditation Date, record_linkage, substantive_domain_count) | **resolved** | `table_w*_*_h*_collapsed.png` |
| **D7** inconsistent header height | all five | F0 and F1 | **resolved across the pinned/scrolling split** — both header rows are 72 px. Within the scrolling header row the heights were already uniform (53.5 px everywhere), so that part of D7 was rejected in Step 2 and is **not applicable**. | **resolved** | `table_w*_*_h*_collapsed.png` |

### D5 expanded: why it is not resolved (hard stop S3)

`fixed_columns` renders the table twice and both copies contain the full row
markup, including a copy of the Rationale column's `<details>` element. Only the
visible copy can receive the user's click, so only it gets `[open]`; the pinned
copy's row keeps its collapsed height and the two tables drift apart for every
row below the expanded one.

Nothing in the permitted scope closes that gap:

- CSS cannot copy one element's `[open]` state onto a sibling table's row.
- Equalising with a fixed row height would clip the expanded rationale.
- The remaining fixes all fall under S3 and are **not chosen here**:

| Option | Trade-off |
|---|---|
| Replace `fixed_columns` with `position: sticky` on the first column | One table, so header and every row align by construction in all states. But it changes the DataTable's pinning mechanism, and `tests/test_enriched_rationale_details.py:459` asserts `fixed_columns == {"headers": True, "data": 1}`, so it would break a currently passing test. |
| Mirror the `toggle` event onto the duplicate `<details>` in `rationale_overflow.js` | Small and targeted, keeps `fixed_columns`. But it is a behaviour change in a clientside callback asset, outside the stated CSS/layout scope, and it makes the pinned copy's disclosure state a thing to keep in sync. |
| Drop the inline Rationale disclosure and route long rationales through the existing record modal only | Removes the divergence entirely, but changes cell content and the truncation/preview rules, which are explicitly out of scope. |
| Clamp row heights | Rejected outright: it would hide expanded content. |

The collapsed-row fix does move this number from 95.40 px to 111.39 px. That is
not new divergence: the expansion always cost ~111 px, and the old 16 px header
offset happened to run the other way and mask 16 px of it. Collapsed rows — the
state the table is in unless a reader opens a rationale — are now exact.

## Project Explorer control

The Explorer shares `.dea-table` and `.filter-label` with this tab. Neither
shared rule was modified; the new CSS is scoped to
`.enriched-register-table-container` and `.enriched-filter-row`. The Explorer
screenshots are **byte-identical** between the two runs at all five widths
(`explorer_w{375,768,1280,1440,1920}.png`, SHA-256 compared).
