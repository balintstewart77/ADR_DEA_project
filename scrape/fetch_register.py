"""Fetch the latest DEA accredited-projects register from the UKSA page.

Replaces the dated scraper scripts. Differences that matter:

- Discovers the projects-report xlsx with plain requests; Selenium is only an
  optional fallback (--selenium) if the page ever stops rendering statically.
- Picks the latest file by parsing dates out of candidate URLs (filename
  DD-MM-YYYY, month names, or the /uploads/YYYY/MM/ path) and filters to
  project-report files. The page also hosts an "Accredited Researchers" report
  whose name sorts after the projects report, so naive lexicographic
  selection downloads the wrong dataset.
- Validates the converted table against the expected register schema and the
  previous version's row count before anything is written.
- Idempotent: if the converted CSV matches the manifest's current version
  (sha256), nothing is written and the script exits 0 reporting "no change".
- On success writes dated xlsx+csv into data/ and registers the version in
  data/register_manifest.json (the single source of truth the dashboard and
  analysis pipeline load from).

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
    DATA_DIR,
    add_version,
    load_manifest,
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
_FILENAME_DMY_RE = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})")
_UPLOADS_PATH_RE = re.compile(r"/uploads/(\d{4})/(\d{2})/")
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

    Tries, in order: DD-MM-YYYY in the filename, a month name + year in the
    filename, and the wordpress /uploads/YYYY/MM/ path (day pinned to 1).
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
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


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

    if args.url:
        xlsx_url, source_date = args.url, parse_url_date(args.url)
    else:
        print(f"Discovering register link on {args.page_url}")
        html = fetch_page_html(args.page_url, use_selenium=args.selenium)
        urls = find_xlsx_urls(html)
        xlsx_url, source_date = select_register_url(urls)
    print(f"Register file: {xlsx_url}")
    print(f"Source date:   {source_date or 'unknown'}")

    xlsx_bytes = download_bytes(xlsx_url)
    print(f"Downloaded {len(xlsx_bytes):,} bytes")
    df = xlsx_to_dataframe(xlsx_bytes)
    print(f"Parsed {len(df):,} rows, columns: {list(df.columns)}")

    manifest = load_manifest(args.data_dir)
    current_record = None
    if manifest is not None:
        current_record = next(
            (r for r in manifest["versions"] if r["version"] == manifest["current"]),
            None,
        )

    min_rows = None
    if current_record is not None and not args.allow_shrink:
        min_rows = current_record.get("row_count")
    problems = validate_register_dataframe(df, min_rows=min_rows)
    if problems:
        for problem in problems:
            print(f"[invalid] {problem}")
        print("Nothing written.")
        return 2

    csv_bytes = _csv_bytes(df)
    csv_sha = hashlib.sha256(csv_bytes).hexdigest()
    if current_record is not None and csv_sha == current_record.get("sha256_csv"):
        print(
            f"No change: register matches current version "
            f"{current_record['version']} (sha256 {csv_sha[:12]}...)"
        )
        return 0

    version = args.version or (source_date or date.today()).strftime("%Y%m%d")
    xlsx_name = f"dea_accredited_projects_{version}.xlsx"
    csv_name = f"dea_accredited_projects_{version}.csv"

    if args.dry_run:
        print(f"[dry run] would write {xlsx_name} and {csv_name} "
              f"({len(df):,} rows) and register version {version}"
              + ("" if args.no_set_current else " as current"))
        return 0

    os.makedirs(args.data_dir, exist_ok=True)
    with open(os.path.join(args.data_dir, xlsx_name), "wb") as f:
        f.write(xlsx_bytes)
    with open(os.path.join(args.data_dir, csv_name), "wb") as f:
        f.write(csv_bytes)
    print(f"Saved {xlsx_name} and {csv_name}")

    record = add_version(
        csv_name,
        data_dir=args.data_dir,
        xlsx_path=xlsx_name,
        source_url=xlsx_url,
        version=version,
        retrieved_at=datetime.now().date().isoformat(),
        notes=f"Fetched by scrape/fetch_register.py; source date {source_date or 'unknown'}",
        set_current=not args.no_set_current,
    )
    print(
        f"Registered version {record['version']} ({record['row_count']:,} rows)"
        + ("" if args.no_set_current else "; manifest 'current' updated")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
