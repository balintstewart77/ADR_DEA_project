"""Paths, constants and politeness settings for publication linkage."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "data" / "publication_linkage_cache"
OUTPUT_ROOT = REPO_ROOT / "analysis" / "outputs_publication_linkage"

# Descriptive client identity, with no personal contact details.
USER_AGENT = (
    "ADR-DEA-publication-linkage/0.1 "
    "(public-output linkage for the UKSA DEA research register; "
    "+https://github.com/balintstewart77/ADR_DEA_project)"
)

# Publication window: 6 months before accreditation to the register snapshot.
WINDOW_MONTHS_BEFORE = 6
# "Mature cohort": accredited at least this many years before the snapshot.
MATURE_COHORT_YEARS = 2

# OpenAlex free tier: $1 of usage per key per UTC day. Stop well before it.
OPENALEX_DAILY_BUDGET_USD = 1.0
OPENALEX_STOP_AT_USD = 0.90
# Published list prices (USD per call), used only when a response does not
# report its own cost. Single-entity lookups are free.
OPENALEX_PRICE_USD = {"singleton": 0.0, "list": 0.0001, "search": 0.001}

# Minimum seconds between live calls, per source (politeness, not just limits).
MIN_INTERVAL_SECONDS = {
    "openalex": 0.15,  # documented 30 requests/second with a free key
    "core": 2.6,  # registered personal tier: 25 tokens/minute, 1,000/day
    "europepmc": 0.25,
    "gtr": 0.5,
    "govuk": 0.25,
    "semanticscholar": 1.1,  # shared unauthenticated pool: 1 request/second
}
REQUEST_TIMEOUT_SECONDS = 90
MAX_RETRIES = 4  # backoff 2, 4, 8, 16 seconds


def openalex_api_key() -> str | None:
    return os.environ.get("OPENALEX_API_KEY") or None


def core_api_key() -> str | None:
    """CORE key from the environment; absent means the proxy attaches it."""
    return os.environ.get("CORE_API_KEY") or None


SECRET_ENV_VARS = ("OPENALEX_API_KEY", "CORE_API_KEY")


def redact(text: str) -> str:
    """Remove any configured secret value from text bound for logs or files."""
    for name in SECRET_ENV_VARS:
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "<redacted>")
    return text
