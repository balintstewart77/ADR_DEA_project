"""Fetch the latest DEA accredited-projects register from the UKSA page.

Replaces the dated scraper scripts. Differences that matter:

- Discovers the projects-report xlsx with plain requests; Selenium is only an
  optional fallback (--selenium) if the page ever stops rendering statically.
- Picks the latest file by parsing dates out of candidate URLs (filename
  DD-MM-YYYY or DD_MM_YYYY, month names, or WordPress upload paths with an
  optional numeric site ID) and filters to
  project-report files. The page also hosts an "Accredited Researchers" report
  whose name sorts after the projects report, so naive lexicographic
  selection downloads the wrong dataset.
- Validates the converted table against the expected register schema and the
  previous version's row count before anything is written.
- Append-only for meaningful provenance: a new date, URL or content identity
  is retained. Exact retries are successful no-ops, while known content at a
  new URL records an observation without duplicating a snapshot.
- Stores both raw XLSX and canonical CSV hashes plus independent nominal-file
  and upload-directory dates.

Usage:
    python scrape/fetch_register.py             # fetch, validate, register
    python scrape/fetch_register.py --dry-run   # report what would happen
    python scrape/fetch_register.py --url <xlsx url>   # skip discovery
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
from datetime import date, datetime

import pandas as pd
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from analysis.register_cleaning import COLUMN_MAP  # noqa: E402
from analysis.register_manifest import (  # noqa: E402
    CURRENT_POINTER,
    DATA_DIR,
    load_manifest,
    matching_fetch_observation,
    record_fetch_observation,
    snapshot_record,
)

PAGE_URL = (
    "https://uksa.statisticsauthority.gov.uk/digitaleconomyact-research-statistics/"
    "better-useofdata-for-research-information-for-researchers/"
    "list-of-accredited-researchers-and-research-projects-under-the-research-strand-of-the-digital-economy-act/"
)
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
REQUEST_TIMEOUT = 60

# Canonical schema after COLUMN_MAP renaming; the cleaning pipeline and
# dashboard rely on these columns existing.
EXPECTED_COLUMNS = [
    "Project ID",
    "Title",
    "Researchers",
    "Legal Basis",
    "Datasets Used",
    "Secure Research Service",
    "Accreditation Date",
]
MAX_UNPARSEABLE_DATE_SHARE = 0.05

XLSX_HREF_RE = re.compile(r'href=["\']([^"\']+\.xlsx)["\']', re.IGNORECASE)
_FILENAME_DMY_RE = re.compile(r"(\d{1,2})[-_](\d{1,2})[-_](\d{4})")
_UPLOADS_PATH_RE = re.compile(r"/uploads/(?:sites/\d+/)?(\d{4})/(\d{2})/")
_MONTHS = {
    name: i + 1
    for i, name in enumerate(
        ["january", "february", "march", "april", "may", "june",
         "july", "august", "september", "october", "november", "december"]
    )
}
_MONTH_NAME_RE = re.compile(
    r"(" + "|".join(_MONTHS) + r")[-_ ]?(\d{4})", re.IGNORECASE
)


def find_xlsx_urls(html: str) -> list[str]:
    seen: list[str] = []
    for url in XLSX_HREF_RE.findall(html):
        if url not in seen:
            seen.append(url)
    return seen


def parse_url_date(url: str) -> date | None:
    """Best-effort date for a register file URL.

    Tries, in order: DD-MM-YYYY or DD_MM_YYYY in the filename, a month name +
    year in the filename, and a WordPress /uploads/YYYY/MM/ or
    /uploads/sites/<numeric-site-id>/YYYY/MM/ path (day pinned to 1).
    """
    filename = url.rsplit("/", 1)[-1]
    match = _FILENAME_DMY_RE.search(filename)
    if match:
        day, month, year = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            pass
    match = _MONTH_NAME_RE.search(filename)
    if match:
        return date(int(match.group(2)), _MONTHS[match.group(1).lower()], 1)
    match = _UPLOADS_PATH_RE.search(url)
    if match:
        return date(int(match.group(1)), int(match.group(2)), 1)
    return None


def parse_upload_directory_date(url: str) -> str | None:
    """Return YYYY-MM from a standard or numeric-site WordPress upload path."""
    match = _UPLOADS_PATH_RE.search(url)
    return f"{match.group(1)}-{match.group(2)}" if match else None


def select_register_url(urls: list[str]) -> tuple[str, date | None]:
    """Choose the latest projects-report xlsx from the page's links."""
    candidates = [
        url for url in urls
        if "project" in url.rsplit("/", 1)[-1].lower()
    ]
    if not candidates:
        raise RuntimeError(
            "No projects-report xlsx link found on the page. "
            f"All xlsx links seen: {urls or '(none)'}"
        )
    dated = [(parse_url_date(url), url) for url in candidates]
    undated = [url for parsed, url in dated if parsed is None]
    if undated and len(candidates) > 1:
        raise RuntimeError(
            "Cannot order candidate files by date; pass --url explicitly. "
            f"Undated candidates: {undated}"
        )
    best_date, best_url = max(dated, key=lambda pair: pair[0] or date.min)
    return best_url, best_date


def fetch_page_html(page_url: str, *, use_selenium: bool = False) -> str:
    if use_selenium:
        return _fetch_page_selenium(page_url)
    response = requests.get(
        page_url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.text


def _fetch_page_selenium(page_url: str) -> str:
    import time

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options

    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    try:
        driver.get(page_url)
        time.sleep(5)
        try:
            driver.find_element(By.ID, "ccc-recommended-settings").click()
            time.sleep(2)
        except Exception:
            pass
        return driver.page_source
    finally:
        driver.quit()


def download_bytes(url: str) -> bytes:
    response = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.content


def xlsx_to_dataframe(xlsx_bytes: bytes) -> pd.DataFrame:
    """Convert the register workbook to a canonical-column DataFrame."""
    workbook = pd.ExcelFile(io.BytesIO(xlsx_bytes))
    target_sheet = workbook.sheet_names[0]
    for name in workbook.sheet_names:
        if any(kw in name.lower() for kw in ["project", "accredited", "data", "register"]):
            target_sheet = name
            break

    raw = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=target_sheet, header=None)
    header_row = 0
    for i, row in raw.iterrows():
        str_cells = [
            v for v in row.values
            if pd.notna(v) and isinstance(v, str) and v.strip()
        ]
        if len(str_cells) >= 3:
            header_row = i
            break

    df = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=target_sheet, header=header_row)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [
        col if not str(col).startswith("Unnamed") else f"Column_{i}"
        for i, col in enumerate(df.columns)
    ]
    return df.rename(columns=COLUMN_MAP)


def validate_register_dataframe(
    df: pd.DataFrame,
    *,
    min_rows: int | None,
) -> list[str]:
    """Return a list of problems; empty means the table looks like the register."""
    problems: list[str] = []
    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        problems.append(
            f"missing expected columns: {missing}; found columns: {list(df.columns)}"
        )
        return problems  # further checks would only add noise

    if min_rows is not None and len(df) < min_rows:
        problems.append(
            f"row count shrank: {len(df)} rows vs {min_rows} in the current "
            "manifest version (the register normally only grows; pass "
            "--allow-shrink to accept)"
        )

    dates = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    unparseable = float(dates.isna().mean())
    if unparseable > MAX_UNPARSEABLE_DATE_SHARE:
        problems.append(
            f"{unparseable:.1%} of Accreditation Date values failed to parse "
            f"(threshold {MAX_UNPARSEABLE_DATE_SHARE:.0%})"
        )
    return problems


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue().encode("utf-8-sig")


def converter_metadata() -> dict:
    import openpyxl

    return {
        "identity": "scrape.fetch_register.xlsx_to_dataframe:v1",
        "pandas": pd.__version__,
        "openpyxl": openpyxl.__version__,
        "canonical_csv_encoding": "utf-8-sig",
        "canonical_line_terminator": "LF",
        "index": False,
    }


def run_fetch(
    *,
    page_url: str = PAGE_URL,
    url: str | None = None,
    data_dir: str = DATA_DIR,
    version: str | None = None,
    allow_shrink: bool = False,
    set_current: bool = True,
    use_selenium: bool = False,
    dry_run: bool = False,
) -> dict:
    """Fetch/validate/register the latest register.

    Returns a result dict with a machine-readable ``outcome`` of
    ``new_snapshot``, ``new_provenance_observation`` or ``unchanged_noop``
    after a successful write-enabled fetch. Used by the CLI below and by
    analysis/refresh_pipeline.py.
    """
    if url:
        xlsx_url, source_date = url, parse_url_date(url)
    else:
        print(f"Discovering register link on {page_url}")
        html = fetch_page_html(page_url, use_selenium=use_selenium)
        urls = find_xlsx_urls(html)
        xlsx_url, source_date = select_register_url(urls)
    print(f"Register file: {xlsx_url}")
    print(f"Source date:   {source_date or 'unknown'}")

    xlsx_bytes = download_bytes(xlsx_url)
    print(f"Downloaded {len(xlsx_bytes):,} bytes")
    df = xlsx_to_dataframe(xlsx_bytes)
    print(f"Parsed {len(df):,} rows, columns: {list(df.columns)}")

    manifest = load_manifest(data_dir)
    if manifest is None or manifest.get("schema_version", 1) < 2:
        raise RuntimeError(
            "Automated fetch requires register manifest schema 2 so observations "
            "and immutable snapshots cannot be lost"
        )
    current_snapshot = snapshot_record(manifest, CURRENT_POINTER)
    previous_version = current_snapshot["nominal_source_date"].replace("-", "")

    result = {
        "source_url": xlsx_url,
        "rows": len(df),
        "previous_version": previous_version,
        "version": None,
        "problems": [],
    }

    min_rows = None
    if not allow_shrink:
        min_rows = current_snapshot.get("raw_row_count")
    problems = validate_register_dataframe(df, min_rows=min_rows)
    if problems:
        for problem in problems:
            print(f"[invalid] {problem}")
        print("Nothing written.")
        return {**result, "status": "invalid", "problems": problems}

    csv_bytes = _csv_bytes(df)
    csv_sha = hashlib.sha256(csv_bytes).hexdigest()
    resolved_version = version or (source_date or date.today()).strftime("%Y%m%d")
    nominal_source_date = (
        source_date or datetime.strptime(resolved_version, "%Y%m%d").date()
    ).isoformat()
    raw_sha = hashlib.sha256(xlsx_bytes).hexdigest()

    if dry_run:
        identity = {
            "nominal_source_date": nominal_source_date,
            "source_url": xlsx_url,
            "raw_xlsx_sha256": raw_sha,
            "canonical_csv_sha256": csv_sha,
        }
        repeated = matching_fetch_observation(manifest, identity) is not None
        known_content = any(
            snapshot.get("raw_xlsx_sha256") == raw_sha
            and snapshot.get("canonical_csv_sha256") == csv_sha
            for snapshot in manifest["content_snapshots"]
        )
        if repeated:
            action = "make no changes because this observation identity is already recorded"
            outcome = "unchanged_noop"
        elif known_content:
            action = "record a provenance observation of known content"
            outcome = "new_provenance_observation"
        else:
            action = "archive a new snapshot"
            outcome = "new_snapshot"
        print(
            f"[dry run] would {action}: raw {raw_sha}, canonical {csv_sha}, "
            f"{len(df):,} rows, nominal date {nominal_source_date}"
        )
        return {
            **result,
            "status": "dry-run",
            "outcome": outcome,
            "version": resolved_version,
            "raw_xlsx_sha256": raw_sha,
            "canonical_csv_sha256": csv_sha,
        }

    recorded = record_fetch_observation(
        data_dir=data_dir,
        source_url=xlsx_url,
        nominal_source_date=nominal_source_date,
        upload_directory_date=parse_upload_directory_date(xlsx_url),
        xlsx_bytes=xlsx_bytes,
        canonical_csv_bytes=csv_bytes,
        raw_row_count=len(df),
        converter=converter_metadata(),
        set_current=set_current,
    )
    snapshot = recorded["snapshot"]
    outcome = recorded["outcome"]
    if outcome == "new_snapshot":
        status = "fetched"
        print(f"Archived immutable snapshot {snapshot['snapshot_id']}")
    elif outcome == "new_provenance_observation":
        status = "provenance-only"
        print(
            "Recorded meaningful provenance for known content "
            f"{snapshot['snapshot_id']}"
        )
    else:
        status = "no-change"
        print(
            "Observed identity is already recorded; no manifest, snapshot, "
            "pointer or report changes are needed."
        )
    return {
        **result,
        "status": status,
        "outcome": outcome,
        "version": resolved_version,
        "snapshot_id": snapshot["snapshot_id"],
        "previous_snapshot_id": recorded["previous_snapshot_id"],
        "created_snapshot": recorded["created_snapshot"],
        "created_observation": recorded["created_observation"],
        "observation_id": recorded["observation"]["observation_id"],
        "raw_xlsx_sha256": raw_sha,
        "canonical_csv_sha256": csv_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch the latest UKSA DEA register")
    parser.add_argument("--page-url", default=PAGE_URL)
    parser.add_argument("--url", default=None, help="Direct xlsx URL (skips discovery)")
    parser.add_argument("--data-dir", default=DATA_DIR)
    parser.add_argument("--version", default=None, help="Override the YYYYMMDD version suffix")
    parser.add_argument("--allow-shrink", action="store_true",
                        help="Accept a register with fewer rows than the current version")
    parser.add_argument("--no-set-current", action="store_true",
                        help="Register the version without pointing 'current' at it")
    parser.add_argument("--selenium", action="store_true",
                        help="Render the page with Selenium instead of plain requests")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and report; write nothing")
    args = parser.parse_args()

    result = run_fetch(
        page_url=args.page_url,
        url=args.url,
        data_dir=args.data_dir,
        version=args.version,
        allow_shrink=args.allow_shrink,
        set_current=not args.no_set_current,
        use_selenium=args.selenium,
        dry_run=args.dry_run,
    )
    return 2 if result["status"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
