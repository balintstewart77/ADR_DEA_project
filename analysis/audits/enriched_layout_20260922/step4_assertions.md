# Step 4 — assertions

## A1 (readable) — PASS
`comparison_output.txt`, section "A1". For F0 and F1: the "Showing N" text, the
page size, the first 20 Record IDs in table order, and all 13 facets' complete
option lists (label including count, and value) are identical before and after.

## A2 (complete) — PASS, run in full
`comparison_output.txt`, section "A2". For F0 (1,343 records) and F1 (129
records): the complete ordered Record ID sequence and every one of the 17
displayed column values for every matching record — all pages, not just page 1 —
are identical before and after.

Captured by calling the production callback itself: `extract_baseline.py` looks
up `dashboard.app.app.callback_map[<enriched key>]["callback"]` and unwraps
Dash's dispatch wrapper via `__wrapped__`, giving `update_enriched_register`.
Filtering, sorting, pagination and cell rendering are therefore the application's
own; nothing is reimplemented. No part of the chain had to be approximated, so
A2 is fully available.

## A3 (change scope) — PASS with one explained entry
See the final response for `git diff --stat` and `git status --short`.

Deltas from the Step 0 status:

- `dashboard/layout/analysis/thematic.py` — **(intended source edit)**
- `dashboard/assets/styles.css` — **(intended source edit)**
- `analysis/audits/` (untracked) — **(expected task artefact)**
- `analysis/outputs_validation_scratch_20260824/headline_summary.md` —
  **(unexpected)**, explained: `git diff --numstat` reports zero changed lines;
  the file is byte-identical apart from CRLF-vs-LF line endings. It is rewritten
  by `tests/test_scratch_coder_stage_a_reporting.py` whenever the suite runs, so
  it appeared as a side effect of the Step 0 and Step 4 test runs the
  instruction requires. Left untouched rather than reverted: it is a data output
  under the standing rule, and any later test run recreates it.

No Python edit touches callbacks, data, filtering, sorting, pagination or cell
content. The only Python file edited is `dashboard/layout/analysis/thematic.py`;
every changed line is listed in the final response.

## A4 (protected files) — PASS
No change to `analysis/register_reference.yaml`, any taxonomy file, any release
pointer, or any data or classification file. `dashboard/dataset_normalisation.py`
is untouched. The geography/coverage change is **not** present in the working
tree.

## A5 (tests) — PASS (no new failures)
Same command and environment both times: `python -m pytest tests -q` in the
project venv (Python 3.13.2).

- Step 0: 21 failed, 621 passed, 10 subtests passed.
- Step 4: 21 failed, 621 passed, 10 subtests passed.
- The two `FAILED` lists are **identical** (diffed line by line): 21
  pre-existing failures, 0 newly introduced. None was repaired.

Full output: `step0_tests.txt`, `step4_tests.txt`.

## A6 (column set) — PASS
`comparison_output.txt`, section "A6": the same 17 columns in the same order,
read from the built layout component in both runs.
