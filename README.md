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

- [`dashboard/app.py`](/C:/Users/balin/Desktop/ADR_DEA_project/dashboard/app.py): main Dash application.
- [`dashboard/dataset_normalisation.py`](/C:/Users/balin/Desktop/ADR_DEA_project/dashboard/dataset_normalisation.py): dataset parsing and normalisation helpers shared by the dashboard and analysis scripts.
- [`data`](/C:/Users/balin/Desktop/ADR_DEA_project/data): source extracts and processed CSV/XLSX files used by the app.
- [`analysis`](/C:/Users/balin/Desktop/ADR_DEA_project/analysis): notebooks and scripts for quality checks, thematic classification, comparison work, and derived outputs.
- [`scrape`](/C:/Users/balin/Desktop/ADR_DEA_project/scrape): scraper scripts used to refresh the source register data.
- [`docs`](/C:/Users/balin/Desktop/ADR_DEA_project/docs): published analysis artefacts and supporting documentation.

## Dashboard Features

- Overview landing page with summary statistics and entry points into search and analysis.
- Searchable project explorer over the full register.
- Analysis views for yearly and quarterly trends.
- Dataset demand analysis based on parsed dataset entries.
- ADR England flagship collection analysis.
- Institution-level analysis derived from researcher affiliation strings.
- Experimental thematic analysis based on LLM-assisted project classification.

## Data Processing Approach

The dashboard loads the latest available CSV from [`data`](/C:/Users/balin/Desktop/ADR_DEA_project/data) and applies a small amount of cleaning before rendering:

- rows with missing accreditation dates are removed
- non-DEA / non-relevant rows are filtered out
- exact duplicates are removed
- same `Project ID` + same title duplicates are collapsed
- a small number of special duplicate cases are handled explicitly
- dates are parsed and year/quarter fields are derived
- dataset and institution fields are normalised into analysis-friendly tables

The `About` tab in the app documents the currently implemented counting and duplicate-handling logic in more detail.

## Thematic Analysis

The thematic analysis layer is experimental.

It uses a separate script in [`analysis/llm_theme_analysis_v3.py`](/C:/Users/balin/Desktop/ADR_DEA_project/analysis/llm_theme_analysis_v3.py) to classify projects using project titles and datasets used. The dashboard reads generated outputs from the analysis directory when they are present; if those files are missing, the thematic analysis tab falls back to an informational message.

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

## Refreshing The Data

Typical workflow:

1. Refresh the source register using a script in [`scrape`](/C:/Users/balin/Desktop/ADR_DEA_project/scrape).
2. Save the updated extract into [`data`](/C:/Users/balin/Desktop/ADR_DEA_project/data).
3. Run any analysis scripts needed to regenerate derived outputs.
4. Start the dashboard and confirm the updated data date and views render as expected.

## Limitations

- The public register is the governing source, so any inconsistencies in project titles, researcher strings, or dataset descriptions flow through into the dashboard.
- Dataset and institution parsing depend on semi-structured free text and therefore involve heuristics.
- Flagship classification is based on keyword matching against dataset text.
- Thematic analysis is experimental and should be treated as indicative rather than definitive.

## Main Entry Points

- Run the dashboard: [`dashboard/app.py`](/C:/Users/balin/Desktop/ADR_DEA_project/dashboard/app.py)
- Refresh the source data: [`scrape/scraper_20260325.py`](/C:/Users/balin/Desktop/ADR_DEA_project/scrape/scraper_20260325.py)
- Regenerate thematic outputs: [`analysis/llm_theme_analysis_v3.py`](/C:/Users/balin/Desktop/ADR_DEA_project/analysis/llm_theme_analysis_v3.py)
