# Step 6 — Follow-up after review

Supersedes two points in `step5_resolution.md`.

## D5 expanded — resolved

`dashboard/assets/rationale_overflow.js` now mirrors each Rationale `<details>`
toggle into the counterpart cell of the other `fixed_columns` copy
(`mirrorToggle`, called from `handleToggle`). Pinning is unchanged; the option
chosen from the S3 list is "mirror the toggle in `rationale_overflow.js`".

Measured in headless Chromium at 375, 1280 and 1920 px, default filters, page 1:
max row-top delta 0 px collapsed, with one and with two rationales expanded, and
after collapsing again. Both copies report the same number of open disclosures.

Covered by `tests/test_enriched_register_alignment_browser.py` (skipped when
Playwright is not installed). With the previous `rationale_overflow.js` it fails
at 1280 and 1920 px; at 375 px it passes either way.

## Header height — 4.5rem → 80px

`style_header` sets the header font in px, so the minimum height is now px too.
The tallest header (Project ID, three lines in 90 px) needs about 70 px; 80 px
leaves about 10 px of headroom instead of 2 px. No header is clipped at any
tested width.

## Also

- Removed the unused `enriched-filter-actions` class from the count/Download row.
- Screenshots, JSON measurements and the full pytest logs from steps 0–5 are
  not committed.
- The step 0/4 test counts (21 failed) were taken on
  `adjudication/build-docs-and-prototype`. On `main`, with and without these
  changes, 24 fail and 7 error, the same set both ways.
