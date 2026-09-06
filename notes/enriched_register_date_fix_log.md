# Enriched Register accreditation dates - 2026-09-06

## Pre-edit diagnosis and scope

Read `notes/explorer_date_fix_log.md`, `dashboard/layout/explorer.py`,
`dashboard/callbacks/explorer.py`, and `analysis/test_dashboard_date_provenance.py`
before editing. No AGENTS.md was found. No Git commands were used.

Exact permitted production paths, discovered before editing:
`dashboard/layout/analysis/thematic.py` and `dashboard/callbacks/thematic.py`.
Only the Enriched Register path was changed in these multi-view modules.
The other authored files are the new `analysis/test_enriched_register_dates.py`
and this new, append-only log.

Pre-edit production copies were preserved with PowerShell `Copy-Item` outside
the repository at
`C:\Users\balin\AppData\Local\Temp\enriched_register_date_fix_17aac1934046492c929ce07cae539eb4`,
as `layout_thematic.py` and `callbacks_thematic.py`. Neither the new test nor
this log existed; their diff baselines are empty strings. Existing contents of
the production modules were preserved except for the scoped changes.

The table is constructed by `_analyses_accordion()`, called from
`build_thematic_tab()`. Its ID is `enriched-register-table`. The date column is
exactly `{"name": f"{REGISTER_SOURCE_ICON} Accreditation Date", "id": "Accreditation Date"}`,
rendering as `\u25a3 Accreditation Date`; it has no type or format declaration.
Data is exclusively callback-produced, with no static layout data.
`register()` owns the single `update_enriched_register()` table-data callback
and `download_enriched_csv()` download callback. No competing writer was added.

Table-boundary samples before editing were `25 Oct 2019`, `25 Oct 2019`, and
`12 Oct 2019`, all Python strings. The loaded thematic source has ISO strings;
after the existing clean-register overlay, the backing dataframe has
`datetime64[ns]` timestamps, including `2019-10-25 00:00:00` and
`2019-10-12 00:00:00`. The shared display getter converts them to `%d %b %Y`
before the callback receives them. Thus the defect is dashboard representation
and lexical sorting, not an upstream date error.

The full classified Enriched Register population, before interactive filters,
contains 1,343 records: 1,343 valid dates, 0 missing, 0 present-but-unparseable.
The source, overlaid backing data, and table boundary agree. Valid dates run
from 2019-03-12 to 2026-08-12, giving global year bounds 2019-2026.
Four rows repeat a Project ID; these are retained without deduplication.
The old count was `Showing 1,343 of 1,343 classified projects`.

Settings are `sort_action="native"`, `filter_action="none"`, `page_size=20`;
`sort_mode` and `page_action` are omitted (single sorting and native paging).
There is no backend paging or page slicing. Existing controls are all
server-side: search, dataset, source organisation/provider, institution,
processing environment, domain, domain count, analytical purpose, cross-cutting
tag, record linkage, collection method, temporal structure, unit of observation,
and researcher sector. The page-size control selects 10/20/50/100 rows.
The download already receives all 14 search/filter values as State, triggered
by `enriched-download-btn.n_clicks`, and writes `enriched-download-csv.data`.
Neither callback depends on current table records, client-side sort, or page.

## Implementation decisions

Preserved native sorting, filtering, and paging settings. The table callback
explicitly parses the observed `%d %b %Y` strings and serializes only
Accreditation Date as zero-padded `YYYY-MM-DD`, matching Explorer's solution.
The callback's display getter does not expose the backing timestamps; using
its observed format avoids a second overlay/filter implementation or shared
module changes. Other columns retain their presentation. Defensive missing
and unparseable dates become `""` in the table.

The layout derives bounds from the existing display getter with every filter
reset, using the exact Enriched Register population rather than Explorer's
data or the raw unclassified population. It does not load another data source.
The two-handle `enriched-accreditation-year-filter` is labelled
`Accreditation year`, defaults to the full range, has integer steps and marks,
and disallows crossing handles. The callback also sorts reversed bounds.

One local callback helper applies inclusive year filtering to both table and
download. Full-range detection uses the global slider min/max as State.
Cleared, non-convertible, and invalid-length values reset to all existing-filter
matches, consistently with Explorer. Full range/reset includes unusable dates;
narrower ranges exclude them even when another filter leaves only the selected
years. The conditional help text is absent for the current zero-unusable-date
population and appears if unusable dates are present. At full range, included
blanks are passed to native sorting; their browser placement in either direction
has not been tested. Canonical valid-date lexical ordering is tested in both
directions, including examples whose old display values misorder.

Every update starts from the existing underlying getter and returns the complete
matching record set. Widening/resetting can restore rows. Counts say
`Showing N accreditation record(s)` and describe all matches, not just one page.
The CSV shares year semantics and keeps every existing filter, column order,
date presentation, and `dea-enriched-register-YYYY-MM-DD.csv` filename convention.
Unrelated copy left unchanged includes the download tooltip's
`Downloads all projects matching the current filters.` and the thematic summary
card's `Projects Classified`.

## Automated verification

Commands ran in PowerShell from the repository root using the established
`venv\Scripts\python.exe`. No dependencies were installed. Python bytecode and
pytest cache writes were disabled. The temporary runtime config override below
redirects application-import cleaning audits without editing production config.

Focused command:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -c "import tempfile; import dashboard.config as config; config.CLEANING_OUTPUT_DIR = tempfile.mkdtemp(prefix='enriched_date_checks_'); import pytest; raise SystemExit(pytest.main(['-p', 'no:cacheprovider', 'analysis/test_enriched_register_dates.py', 'analysis/test_dashboard_date_provenance.py', '-q']))"
```

Result: 23 passed, 6 Dash DataTable deprecation warnings, 3.82 seconds.
This includes all 8 existing Explorer/provenance tests unchanged. New tests
cover ISO chronology, blank/malformed/null coercion, inclusive bounds,
reversed/cleared/invalid-length resets, global-bound recognition after another
filter, forwarding all existing filters, real search/year composition, restored
rows, duplicate IDs, complete native pages (25 matches with page size 10),
zero/singular/plural counts, CSV contents and filename, conditional help,
layout properties, and callback dependency registration. Callback tests exercise
Python functions; they do not establish browser interaction behaviour.

Documented suite (`.github/workflows/register-refresh.yml` specifies `analysis`),
with the same runtime audit redirection:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -c "import tempfile; import dashboard.config as config; config.CLEANING_OUTPUT_DIR = tempfile.mkdtemp(prefix='enriched_date_checks_'); import pytest; raise SystemExit(pytest.main(['-p', 'no:cacheprovider', 'analysis', '-q']))"
```

Result: 244 passed, 658 subtests passed, 11 warnings, 19.94 seconds.
Warnings: 10 Dash DataTable deprecations and the existing pandas date-inference
warning from `analysis/test_fetch_register.py`. No failing tests were fixed.

Application, live callback, and HTTP smoke command:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import tempfile
import dashboard.config as config
config.CLEANING_OUTPUT_DIR = tempfile.mkdtemp(prefix='enriched_date_smoke_')
import dashboard.app as application
from dashboard.layout.analysis.thematic import build_thematic_tab
from analysis.test_dashboard_date_provenance import _find_component
layout = build_thematic_tab()
slider = _find_component(layout, 'enriched-accreditation-year-filter')
app = application.app
keys = [k for k in app.callback_map if 'enriched-register-table.data' in k]
callback = app.callback_map[keys[0]]['callback'].__wrapped__
full, _, count = callback(None, *(['ALL'] * 13), 10, slider.value, slider.min, slider.max)
narrow, _, _ = callback(None, *(['ALL'] * 13), 10, [2025, 2025], slider.min, slider.max)
print('import=ok; layout=ok; callbacks=', len(app.callback_map), '; table_writers=', len(keys), '; download_registered=', 'enriched-download-csv.data' in app.callback_map)
print('bounds=', slider.value, '; full=', len(full), '; 2025=', len(narrow), '; count=', count)
assert len(keys) == 1 and all(r['Accreditation Date'].startswith('2025-') for r in narrow)
assert all(len(r['Accreditation Date']) == 10 for r in full)
client = app.server.test_client()
for route in ['/', '/_dash-layout', '/_dash-dependencies']:
    response = client.get(route)
    assert response.status_code == 200
    print(route, response.status_code)
'@ | python -
```

Result: import/layout succeeded; 26 callbacks; exactly one Enriched table writer;
download registered; bounds [2019, 2026]; full=1,343; 2025=272; count
`Showing 1,343 accreditation records`; all three HTTP routes returned 200.
No browser tool/harness was available. Browser sorting, blank placement,
slider gestures, widening, paging, and download interaction were not run.

## Scope exception from existing diagnostic/test side effects

The initial two pre-edit diagnostic imports invoked existing loader writes to
`analysis/outputs_v3/quality/duplicate_review_flagged.csv` and
`analysis/outputs_v3/quality/duplicate_rulings_audit.csv` before that side effect
was discovered. Subsequent application imports were redirected to temporary
storage. The full suite nevertheless rewrote `duplicate_review_flagged.csv`
through the existing direct `apply_duplicate_policy(filtered, verbose=False)`
call in `analysis/test_register_cleaning.py`, bypassing the dashboard config.
These were unintended out-of-scope audit writes. No pre-run copies of those
two audit files exist for this task, so their prior contents cannot be verified,
restored confidently, or included in an honest before/after diff. No attempted
restoration or pipeline change was made. This prevents claiming that every
read-only artifact was unchanged or that a diff covers those incidental writes.

The first diagnostic also hit a Windows cp1252 UnicodeEncodeError printing the
column icon, after successfully printing date counts and samples; the column
and callback inspection was rerun successfully with JSON-escaped output.
Neither issue required a production change beyond the permitted files.

## Preservation and handoff

No Explorer or other read-only source module was edited; no underlying register
CSV, ingestion code, classification code, reference, taxonomy, or preregistration
artifact was edited. The audit-output exception above qualifies filesystem
preservation. Exact before/after SHA256 checks used:

```powershell
Get-FileHash dashboard/layout/explorer.py,dashboard/callbacks/explorer.py,notes/explorer_date_fix_log.md,analysis/test_dashboard_date_provenance.py,dashboard/data/filtering.py -Algorithm SHA256 | Format-List Path,Hash
```

All five hashes matched. Explorer layout: `D6653815C485D7A1D2118AA70CBFA0D6C79A3A7B3014B5CA10BA33490C380A7A`;
Explorer callbacks: `BE66C8D7E503BDA2DCFD6715297FBB91666D42983FD8A7D2AF82604165487CC9`;
Explorer log: `E0A51118D36802734EE705945B3CF2601EEF562E74E09B86FE6FE20A098731CE`;
existing date tests: `9420DBA28452090D2C1BD2AC7F6FE5589F5111DBB60F7097E00020C613DA5F8A`;
shared filtering: `B391C861CE1E716AC0007143AE7981D920DC5469F1B84452DAA0C01402AC158A`.

The complete, unabridged diff for the four authored files is generated outside
the repository from the saved pre-edit copies and empty new-file comparisons
using Python `difflib.unified_diff`. No Git operation, commit, push, dependency
change, or unrelated source cleanup was performed. Work stops for review.

Final source-preservation and whitespace check (passed):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import ast
from pathlib import Path
backup = Path(r'C:\Users\balin\AppData\Local\Temp\enriched_register_date_fix_17aac1934046492c929ce07cae539eb4')
for relative, original in [('dashboard/layout/analysis/thematic.py', 'layout_thematic.py'), ('dashboard/callbacks/thematic.py', 'callbacks_thematic.py')]:
    before = ast.parse((backup / original).read_text(encoding='utf-8'))
    after = ast.parse(Path(relative).read_text(encoding='utf-8'))
    old_functions = {node.name: node for node in before.body if isinstance(node, ast.FunctionDef)}
    new_functions = {node.name: node for node in after.body if isinstance(node, ast.FunctionDef)}
    for name, node in old_functions.items():
        if name == '_analyses_accordion':
            continue
        if name == 'register':
            old_nodes = [n for n in node.body if not isinstance(n, ast.FunctionDef) or n.name not in ('update_enriched_register', 'download_enriched_csv')]
            new_nodes = [n for n in new_functions[name].body if not isinstance(n, ast.FunctionDef) or n.name not in ('update_enriched_register', 'download_enriched_csv')]
            assert [ast.dump(n) for n in old_nodes] == [ast.dump(n) for n in new_nodes]
        else:
            assert ast.dump(node) == ast.dump(new_functions[name]), name
    print(relative, 'unrelated functions/callbacks unchanged')
for relative in ['dashboard/layout/analysis/thematic.py', 'dashboard/callbacks/thematic.py', 'analysis/test_enriched_register_dates.py', 'notes/enriched_register_date_fix_log.md']:
    content = Path(relative).read_text(encoding='utf-8')
    assert content.endswith('\n')
    assert all(line == line.rstrip() for line in content.splitlines()), relative
print('whitespace=ok; final_newlines=ok')
'@ | python -
```

Result: unrelated functions and non-Enriched callbacks unchanged in both
modules; whitespace and final newlines passed. The accordion's change was
inspected in the unified diff and is confined to Enriched year bounds/control.

Exact diff-generation command (empty strings are used for new-file baselines):

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
@'
import difflib
from pathlib import Path
backup = Path(r'C:\Users\balin\AppData\Local\Temp\enriched_register_date_fix_17aac1934046492c929ce07cae539eb4')
files = [('dashboard/layout/analysis/thematic.py', 'layout_thematic.py'), ('dashboard/callbacks/thematic.py', 'callbacks_thematic.py'), ('analysis/test_enriched_register_dates.py', None), ('notes/enriched_register_date_fix_log.md', None)]
parts = []
for relative, original in files:
    before = (backup / original).read_text(encoding='utf-8') if original else ''
    after = Path(relative).read_text(encoding='utf-8')
    assert after.endswith('\n') and all(line == line.rstrip() for line in after.splitlines())
    parts.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile='a/' + relative, tofile='b/' + relative))
result = ''.join(parts)
destination = backup / 'enriched_register_date_fix.diff'
destination.write_text(result, encoding='utf-8', newline='\n')
assert result.count('--- a/') == len(files)
assert destination.read_text(encoding='utf-8') == result
print(destination)
print('diff=ok; files=', len(files), '; lines=', len(result.splitlines()))
'@ | python -
```

The initial diff artifact was generated, but its header-count assertion failed:
the log quotes the assertion itself, adding an extra `--- a/` substring. This
was a verification-script issue, not an implementation failure. The command
was rerun with that assertion replaced by the exact line below, counting only
actual diff header lines:

```python
assert sum(line.startswith('--- a/') for line in result.splitlines()) == len(files)
```

Corrected generation passed for all four authored files. The diff was regenerated
with this final log entry included and its saved contents verified against the
complete in-memory unified diff. The two incidental audit writes remain outside
the recoverable comparison, as disclosed above.
