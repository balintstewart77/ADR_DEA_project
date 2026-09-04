# Explorer accreditation-date sort and year filter — 2026-09-04

## Diagnosis before editing

The Project Explorer table is constructed by
`dashboard.layout.explorer.build_explorer_tab()`.  Its Accreditation Date
column was exactly `{"name": "Accreditation Date", "id": "Accreditation
Date"}`: it had no `type`, `format`, or column-level display transformation.
At the table boundary, the only transformation was in the existing
`dashboard.data.filtering._get_browse_display_df()`, which called
`_format_display_dates()` and converted the raw pandas timestamps to strings
with `%d %b %Y`.  Representative table values were `25 Oct 2019`, `12 Oct
2019`, and `19 Nov 2019`; all were strings.  The raw Explorer dataframe
retained `datetime64[ns]` timestamps, for example `2019-10-25 00:00:00`.

`browse-table` used `sort_action="native"`, `filter_action="none"`, and
`page_size=20`; `sort_mode` and `page_action` were omitted, so Dash's
documented defaults applied (`single` and `native`, respectively).  There is
no backend paging.  The table data was callback-produced, not static:
`dashboard.callbacks.explorer.register()` registers the sole callback that
writes `browse-table.data`, `tooltip_data`, `page_size`, and `browse-count`.
Before this change it took the dataset, provider, institution, processing
environment, search, and page-size controls as inputs, and used
`_get_browse_display_df()` to make complete records.  The download callback
reads the same server-side Explorer controls but does not read or write the
table data, sorting, filtering, or paging properties.  No callback reads or
writes `sort_by`, `sort_action`, `filter_action`, `page_action`, or
`page_current`.

The dropdown/search controls are existing server-side filters.  DataTable
column filtering is disabled (`filter_action="none"`), and Dash retains
native sorting and native paging over the complete callback result.  The
working hypothesis was confirmed: chronological timestamps were correct
upstream, but native sorting received human-formatted strings and therefore
sorted them lexically.

At the Explorer dataframe boundary there were 1,343 valid parseable dates,
0 missing dates, and 0 present-but-unparseable dates.  Valid dates ranged
from 2019-03-12 through 2026-08-12, giving derived year bounds 2019–2026.
The directly associated count previously said `Showing … projects`, despite
the table being an accreditation-event register; it now says accreditation
records.

## Date-sort branch and behaviour

Branch A was selected.  Native sorting is already appropriate, there is no
backend paging constraint, and the defect was solely the local display-string
representation.  The existing callback now serializes valid dates as
zero-padded `YYYY-MM-DD` strings, which native lexical sorting orders
chronologically in both directions.  No date column `format` was added.

The defensive blank representation is the Explorer's established empty string
(`""`).  The current register contains no missing or unparseable dates, so
there were no actual blank values whose native ascending or descending
position could be observed.  The focused fixture verifies that blank and
malformed inputs are converted to that representation without raising.  This
repository has no browser-test infrastructure, so no client-side Dash blank
placement assertion was added.  If a later register contains unusable dates,
they are included when the whole slider range is selected and excluded for a
narrower range; when included their position is determined by Dash's native
sort.  No help text was added because there are currently no such records.

## Year control

The new `dcc.RangeSlider` is labelled `Accreditation year`, has two handles,
integer marks from the loaded dataframe's 2019–2026 bounds, and disallows
crossing handles.  Its default is the full derived range.  The callback treats
`None`, an empty value, or any non-two-value input as that full range and
safely sorts reversed bounds.  Bounds are inclusive.  Its global slider
minimum and maximum are callback state so a global narrow range still excludes
unusable dates even if another server-side filter happens to leave only dates
inside that range.  The callback returns the complete year-bounded record set;
it never slices by page, so native paging remains over all matching records.

## Other sortable-column observations (not changed)

Project ID remains `{"name": "Project ID", "id": "Project ID"}`, with no
declared type or format.  At the table boundary all 1,343 values are strings,
all are eight characters, and all match `YYYY/NNN`; representative values are
`2019/003`, `2019/004`, and `2019/005`.  The numeric portion is consistently
three-digit zero-padded both within and across years; no format exception or
mixed representation was observed.

The other visible sortable columns have no declared type or format.  Title and
Processing environment are strings.  Researchers and Datasets Used contain a
mixture of strings and `None`; representative string values include `Carolin
Ioramashvili, London School of Economics` and `Office for National Statistics:
Annual Respondents Database`.  No changes were made to those columns.  The
existing download tooltip says `Downloads all projects matching the current
filters.`; because that could be read as one row per unique project, it is
reported here for a separate wording decision and was intentionally left out
of this narrowly scoped change.

## Verification

* Data/table-boundary diagnostic (`python -c` with `PYTHONDONTWRITEBYTECODE=1`):
  confirmed 1,343 valid, 0 missing, and 0 unparseable dates; raw timestamps;
  formatted-string table values; 2019–2026 range; and uniformly padded Project
  IDs.
* DataTable/default-property diagnostic (`python -c` with
  `PYTHONDONTWRITEBYTECODE=1`): confirmed native sorting, disabled column
  filtering, explicit page size 20, and Dash's documented default native
  paging/single sort mode.
* Initial focused run:
  `$env:PYTHONDONTWRITEBYTECODE = "1"; python -m pytest -p no:cacheprovider analysis/test_dashboard_date_provenance.py -q`
  produced 1 failed and 5 passed.  The failure exposed test-fixture reuse and
  led to correcting the full-range check to use global slider bounds rather
  than only the dates left by another filter.
* Focused rerun:
  `$env:PYTHONDONTWRITEBYTECODE = "1"; python -m pytest -p no:cacheprovider analysis/test_dashboard_date_provenance.py -q`
  passed: 6 passed, 4 Dash DataTable deprecation warnings.  These tests cover
  ISO date values, lexical ascending/descending chronology, blank/malformed
  coercion, inclusive lower/upper year bounds, reset/full range, record count,
  complete data despite a page size of 10, and unchanged native table settings.
* Application smoke check:
  `$env:PYTHONDONTWRITEBYTECODE = "1"; python -c "import dashboard.app ..."`
  passed: application import and Explorer layout construction succeeded, 26
  callbacks registered, and the Browse table callback was present with no
  duplicate-output or circular-dependency error.
* Live callback check (`python -c` with `PYTHONDONTWRITEBYTECODE=1`): the full
  range returned 1,343 records; all 1,343 dates were canonical ISO strings;
  the 2025-only range returned 272 records and every returned value had year
  2025.
* Existing documented suite:
  `$env:PYTHONDONTWRITEBYTECODE = "1"; python -m pytest -p no:cacheprovider analysis -q`
  passed: 227 passed, 658 subtests passed, no failures or errors.  It emitted
  eight Dash DataTable deprecation warnings and one existing pandas
  date-inference warning from `analysis/test_fetch_register.py`.

Filtering and paging semantics were preserved: the pre-existing controls
remain server-side, DataTable filtering remains disabled, and native sorting
and native paging remain client-side over the complete callback result.  No
verification check remains unrun apart from client-side blank placement, which
is not observable in the current zero-blank register and has no existing
browser-test harness.

Temporary pre-edit copies of each permitted changed file (and an empty baseline
for this new log) were kept in `C:\tmp\explorer_date_fix_20260904`.  A
cross-platform `difflib.unified_diff` command compared those copies with the
four current files.  A final
`python -c` whitespace/newline check passed (`whitespace=ok;
final_newlines=ok`).  No Git command was run.  All Python commands used
`PYTHONDONTWRITEBYTECODE=1`, and pytest cache creation was disabled.

## Correction pass — download range and strengthened verification

The download callback now takes the accreditation-year range and its global
minimum/maximum as state and calls the same
`_filter_accreditation_year_range()` helper as the table callback.  It retains
the existing search, dataset, provider, institution, and processing-environment
filter arguments, CSV date presentation, filename, and download-tooltip
wording.  A full/cleared range leaves all existing-filter matches in the CSV;
a narrower inclusive range retains only parseable dates within its bounds and
excludes unusable dates.  This is the same global-bound rule used by the table,
not a replacement for the existing server-side filters.

The focused tests were expanded and rerun with the exact command:

`$env:PYTHONDONTWRITEBYTECODE = "1"; python -m pytest -p no:cacheprovider analysis/test_dashboard_date_provenance.py -q`

Result: 8 passed, 4 Dash DataTable deprecation warnings.  The test-backed
assertions now cover: ISO values and lexical chronological ordering; blank and
malformed coercion; inclusive/full/cleared year ranges; plural counts for 2,
5, and 25 records and the singular count for 1 record; an existing server-side
Explorer filter being passed through before the year condition; all 25 matching
records being returned despite a page size of 10; and the CSV callback receiving
only the two selected 2023 rows.  The complete-data/native-page assertion is
therefore directly tested rather than only inferred from the callback code.

The exact smoke-test command, replacing the earlier abbreviated `python -c`
description, was:

`$env:PYTHONDONTWRITEBYTECODE = "1"; python -c "import dashboard.app as application; from dashboard.layout.explorer import build_explorer_tab; layout = build_explorer_tab(); print('import=ok'); print('layout=ok'); print('callbacks=' + str(len(application.app.callback_map))); print('browse_table_callback=' + str(any('browse-table.data' in key for key in application.app.callback_map))); print('browse_download_callback=' + str(any('browse-download-csv.data' in key for key in application.app.callback_map)))"`

Result: `import=ok`, `layout=ok`, `callbacks=26`,
`browse_table_callback=True`, and `browse_download_callback=True`.

The full suite was rerun with:

`$env:PYTHONDONTWRITEBYTECODE = "1"; python -m pytest -p no:cacheprovider analysis -q`

Result: 229 passed, 658 subtests passed, 9 warnings, no failures or errors.
The warnings remain eight Dash DataTable deprecations and the existing pandas
date-inference warning in `analysis/test_fetch_register.py`.

Qualification of earlier verification wording: there are still no current blank
accreditation dates, and no browser test harness exists, so the position of a
blank under Dash client-side ascending or descending sorting has not been
tested.  The implementation's defensive empty-string handling and reversed
bound normalization are source-inspection observations; the focused tests do
not make a separate reversed-bound assertion.  The page-completeness, count,
filter-intersection, and download-range claims above are test-backed.
