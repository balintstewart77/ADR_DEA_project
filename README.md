# ADR DEA Project

## Setup

Create a virtual environment and install the dashboard runtime:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python dashboard/app.py
```

The dashboard can also be launched as a module from the repo root:

```bash
python -m dashboard.app
```

## Optional Installs

Install extra dependency sets only when needed:

```bash
pip install -r requirements-analysis.txt
pip install -r requirements-dev.txt
pip install -r requirements-llm.txt
pip install -r requirements-ml.txt
pip install -r requirements-scrape.txt
```

Use cases:

- `requirements-analysis.txt`: local analysis scripts beyond the dashboard runtime
- `requirements-dev.txt`: notebooks and interactive development tooling
- `requirements-llm.txt`: Anthropic/Pydantic-based classification scripts
- `requirements-ml.txt`: heavyweight ML and embedding dependencies
- `requirements-scrape.txt`: scraper dependencies for refreshing the source data
