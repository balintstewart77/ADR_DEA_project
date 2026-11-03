# ADR DEA Project

This repository contains a public-facing dashboard and supporting analysis for exploring research projects accredited under the Digital Economy Act 2017 (DEA) research powers.

The project turns the UK Statistics Authority public register of accredited researchers and research projects into a more legible tool for exploration. It is designed to help users search individual projects, inspect portfolio-level patterns, and understand how public data is being used for accredited research over time.

## What The Dashboard Does

The dashboard supports two main use cases:

- `Project Explorer`: search and filter the public register by title, researcher, dataset, provider, institution, and flagship collection.
- `Portfolio Analysis`: explore overall trends, dataset demand, ADR England flagship dataset uptake, institutional participation, and thematic analysis.

The `Overview` page acts as a landing page, while the `About` page documents the data source, processing logic, and classification methodology.

## What Data This Covers

The DEA research powers allow accredited researchers to access de-identified data held by public authorities for public-good research in accredited secure environments.

This repository is built around the UK Statistics Authority public register of DEA-accredited projects. 

## Repository Structure

- [`dashboard/app.py`](dashboard/app.py): main Dash application.
- [`dashboard/dataset_normalisation.py`](dashboard/dataset_normalisation.py): dataset parsing and normalisation helpers shared by the dashboard and analysis scripts.
- [`data`](data): source extracts and processed CSV/XLSX files used by the app.
- [`analysis`](analysis): notebooks and scripts for quality checks, thematic classification, comparison work, and derived outputs.
- [`scrape`](scrape): scraper scripts used to refresh the source register data.
- [`docs`](docs): published analysis artefacts and supporting documentation.

## Dashboard Features

- Overview landing page with summary statistics and entry points into search and analysis.
- Searchable project explorer over the full register.
- Analysis views for yearly and quarterly trends.
- Dataset demand analysis based on parsed dataset entries.
- ADR England flagship collection analysis.
- Institution-level analysis derived from researcher affiliation strings.
- Experimental thematic analysis based on LLM-assisted project classification.

## Data Processing Approach

The dashboard loads the latest available CSV from [`data`](data) and applies a small amount of cleaning before rendering:

- rows with missing accreditation dates are removed
- non-DEA / non-relevant rows are filtered out
- exact duplicates are removed
- same `Project ID` + same title duplicates are collapsed
- reviewed duplicate-`Project ID` rulings collapse duplicate/update rows, retain
  clear identifier collisions as separate entries, and assign stable `Record ID`
  values
- dates are parsed and year/quarter fields are derived
- dataset and institution fields are normalised into analysis-friendly tables

The `About` tab in the app documents the currently implemented counting and duplicate-handling logic in more detail.

## Thematic Analysis

The thematic analysis layer is experimental.

It uses a separate script in [`analysis/llm_theme_analysis_v3.py`](analysis/llm_theme_analysis_v3.py) to classify projects using project titles and datasets used. The dashboard reads generated outputs from the analysis directory when they are present; if those files are missing, the thematic analysis tab falls back to an informational message.

## Setup

Create a virtual environment and install the dashboard runtime:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python dashboard/app.py
```

Then open `http://127.0.0.1:8050`.

You can also launch the app from the repo root with:

```bash
python -m dashboard.app
```

The development server listens only on this computer (`127.0.0.1`). To accept
connections from other machines, set `HOST=0.0.0.0` (and `PORT` if needed).
A production host can instead serve `dashboard.app:server` with gunicorn,
which ignores both settings.

## Optional Dependency Sets

Install extra dependency groups only when needed:

```bash
pip install -r requirements-analysis.txt
pip install -r requirements-dev.txt
pip install -r requirements-llm.txt
pip install -r requirements-ml.txt
pip install -r requirements-scrape.txt
```

Use cases:

- `requirements-analysis.txt`: local analysis scripts beyond the dashboard runtime.
- `requirements-dev.txt`: notebooks and interactive development tooling.
- `requirements-llm.txt`: Anthropic/Pydantic-based classification scripts.
- `requirements-ml.txt`: heavier ML and embedding dependencies.
- `requirements-scrape.txt`: scraper dependencies for refreshing source data.

### Pinned runtime and test dependencies

`requirements.lock` contains shared, exact transitive constraints for the
dashboard, scraper, test suite and browser tests. The dashboard and scraper
requirements include it automatically; test and browser requirements inherit
those constraints. Install only the group you need:

```bash
python -m pip install -r requirements-test.txt
python -m pip install -r requirements-browser.txt
python -m pip check
```

The browser group adds Playwright; Chromium is installed separately with
`python -m playwright install chromium`. CI targets Python 3.12; the local
Windows environment also uses Python 3.13. The test group includes the
`anthropic` SDK, so the lock also pins the SDK that `requirements-llm.txt`
installs for classification runs; each run records it in `run_metadata.json`.
Notebook, optional analysis and archived ML dependencies outside these groups
are not fully locked.

To regenerate the constraints while retaining the selected versions, use the
recorded resolver and include platform markers:

```bash
python -m pip install uv==0.13.6
python -m uv pip compile requirements-browser.txt --universal --python-version 3.12 --no-header --no-annotate --output-file requirements.lock
```

For a deliberate upgrade, first edit or remove the affected constraints in
`requirements.lock`, then run the same command and review the resulting diff.
The requirements files reference the lock, so `--upgrade` alone does not remove
its version constraints. Verify Linux resolution with:

```bash
python -m uv pip compile requirements-browser.txt --python-version 3.12 --python-platform x86_64-unknown-linux-gnu
```

After changing versions, install the affected groups, run `python -m pip check`
and the relevant tests before committing the lock.

### Running the CI checks locally

```bash
python -m ruff check dashboard analysis scrape scripts tests conftest.py
python -m pytest analysis tests -q -ra -m "not browser" --require-history
python -m pytest tests/test_enriched_register_alignment_browser.py -q --require-browser
```

Historical provenance tests require a full Git checkout. Tests that need
untracked private inputs report explicit skips when those inputs are absent;
use `--require-private` to make missing inputs fail instead. Browser CI requires
Playwright and Chromium and fails if either is unavailable. The dashboard's
external stylesheet also requires network access for the browser checks.

Tests redirect cleaning reports and generator outputs to temporary directories.
CI checks that tracked files remain unchanged after testing. Ruff currently
checks syntax and undefined names, with one documented exception for the
byte-pinned historical candidate-0.3 validator.

The portfolio baseline includes the provider and facet changes from the
previously committed parser correction (`acc05ba`, `02d61fa`), including two
additional longitudinal and three additional household classifications.

## Refreshing The Data

One command runs the whole flow — fetch, compare against both the preceding
ingested content snapshot and preceding nominal release,
deterministic facet derivation, and validation gates — and writes reports
(register diff, curation queue, refresh summary) to
`analysis/outputs_refresh/<version>/`:

```bash
python -m analysis.refresh_pipeline
```

It records every new stable observation identity and exits cleanly when that
date/URL/raw-hash/canonical-hash identity is already present. New content is
archived immutably by hash even when UKSA reuses a nominal source date. Add
`--classify` (with `ANTHROPIC_API_KEY` set) to also run incremental LLM
classification for new/changed projects and repoint the dashboard at the new
run via `data/release_pointers.json`. Use `--skip-fetch --force` to re-run
the downstream steps on the current data.

A scheduled GitHub Actions workflow
(`.github/workflows/register-refresh.yml`) runs the same pipeline weekly and
opens a pull request when a new register version is published; classification
is left as a local follow-up after the curation queue has been reviewed.

The individual steps remain available:

1. Fetch the latest register (downloads, validates the schema, archives new
   XLSX and canonical CSV bytes under `data/register_snapshots/<hash>/`, and
   appends the observation to `data/register_provenance_manifest.json`):

   ```bash
   python scrape/fetch_register.py
   ```

   The manifest separates fetch observations, immutable content snapshots and
   cleaned analytical states. Its `current_latest_revision` pointer may move;
   `frozen_validation_snapshot` is independently protected. Observation
   identity is the nominal source date, source URL, raw XLSX hash and canonical
   CSV hash. The manifest records distinct source observations and revisions,
   not polling history. An exact repeat is a clean no-op whether it is an
   immediate retry or a later scheduled check, so unchanged polling creates no
   timestamp-only branch, commit or PR. Workflow execution logs retain that
   operational polling history outside the canonical source-provenance DAG. A
   new URL for known content is retained as provenance without duplicating its
   snapshot. Use `--dry-run` to preview without writing.

2. Regenerate the deterministic facets and review any newly unmatched
   datasets/organisations it reports:

   ```bash
   python -m analysis.derive_register_properties
   ```

3. Classify new/changed projects (incremental — cached classifications are
   reused; `analysis/rebuild_llm_cache.py` can rebuild the cache from a
   previous `layer_classifications.csv` if it is missing):

   ```bash
   python analysis/llm_theme_analysis_v3.py
   ```

4. Start the dashboard and confirm the updated data date and views render as expected.

## Limitations

- The public register is the governing source, so any inconsistencies in project titles, researcher strings, or dataset descriptions flow through into the dashboard.
- Dataset and institution parsing depend on semi-structured free text and therefore involve heuristics.
- Flagship collection membership is derived from the curated linked-product reference ([`analysis/register_reference.yaml`](analysis/register_reference.yaml)).
- Thematic analysis is experimental and should be treated as indicative rather than definitive.

## Main Entry Points

- Run the dashboard: [`dashboard/app.py`](dashboard/app.py)
- Refresh the data end to end: `python -m analysis.refresh_pipeline` ([`analysis/refresh_pipeline.py`](analysis/refresh_pipeline.py))
- Fetch the source data only: [`scrape/fetch_register.py`](scrape/fetch_register.py)
- Regenerate thematic outputs: [`analysis/llm_theme_analysis_v3.py`](analysis/llm_theme_analysis_v3.py)
