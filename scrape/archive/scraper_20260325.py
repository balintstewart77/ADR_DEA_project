"""
Scraper for DEA accredited projects — March 2026.

The UKSA page now provides the register as a downloadable Excel file rather
than a paginated HTML table. This script downloads the latest xlsx, converts
it to CSV, and saves both to the data/ directory with a dated suffix so
existing files are not overwritten.

Data correct as of: 24th March 2026
Source page: https://uksa.statisticsauthority.gov.uk/digitaleconomyact-research-statistics/
             better-useofdata-for-research-information-for-researchers/
             list-of-accredited-researchers-and-research-projects-under-the-research-strand-of-the-digital-economy-act/
"""

import os
import re
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import time

DATE_SUFFIX = "20260325"
DATA_DIR = "data"
XLSX_OUT = os.path.join(DATA_DIR, f"dea_accredited_projects_{DATE_SUFFIX}.xlsx")
CSV_OUT  = os.path.join(DATA_DIR, f"dea_accredited_projects_{DATE_SUFFIX}.csv")

PAGE_URL = (
    "https://uksa.statisticsauthority.gov.uk/digitaleconomyact-research-statistics/"
    "better-useofdata-for-research-information-for-researchers/"
    "list-of-accredited-researchers-and-research-projects-under-the-research-strand-of-the-digital-economy-act/"
)


def find_xlsx_url():
    """Use Selenium to load the page (accepting cookies) and find the xlsx download link."""
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    try:
        print("Loading page to discover xlsx link...")
        driver.get(PAGE_URL)
        time.sleep(5)

        # Accept cookies
        try:
            driver.find_element(By.ID, "ccc-recommended-settings").click()
            time.sleep(2)
        except Exception:
            pass

        time.sleep(3)
        src = driver.page_source

        # Find all .xlsx links
        urls = re.findall(r'href=["\']([^"\']+\.xlsx)["\']', src, re.IGNORECASE)
        if not urls:
            raise RuntimeError("No xlsx links found on page. Page may have changed.")

        # Prefer the most recent one (highest year in path)
        urls_sorted = sorted(set(urls), reverse=True)
        print(f"Found xlsx links: {urls_sorted}")
        return urls_sorted[0]
    finally:
        driver.quit()


def download_xlsx(url, out_path):
    print(f"Downloading: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)
    print(f"Saved xlsx to: {out_path} ({len(r.content):,} bytes)")


def xlsx_to_csv(xlsx_path, csv_path):
    print(f"Converting xlsx to csv...")
    xl = pd.ExcelFile(xlsx_path)
    print(f"  Sheets: {xl.sheet_names}")

    # Pick the most likely data sheet
    target_sheet = xl.sheet_names[0]
    for name in xl.sheet_names:
        if any(kw in name.lower() for kw in ["project", "accredited", "data", "register"]):
            target_sheet = name
            break

    # Read without skipping rows first to detect where column headers are
    df_raw = pd.read_excel(xlsx_path, sheet_name=target_sheet, header=None)
    print(f"  Raw shape: {df_raw.shape}")

    # Find the header row: first row where the majority of cells are non-null strings
    header_row = 0
    for i, row in df_raw.iterrows():
        non_null = [v for v in row.values if pd.notna(v) and str(v).strip() != ""]
        # Header row will have multiple non-null string cells (not datetime/numbers)
        str_cells = [v for v in non_null if isinstance(v, str)]
        if len(str_cells) >= 3:
            header_row = i
            break

    print(f"  Header at row: {header_row}")
    df = pd.read_excel(xlsx_path, sheet_name=target_sheet, header=header_row)

    # Drop fully empty rows and columns
    df = df.dropna(how="all").dropna(axis=1, how="all")
    # Rename any remaining unnamed columns
    df.columns = [
        col if not str(col).startswith("Unnamed") else f"Column_{i}"
        for i, col in enumerate(df.columns)
    ]

    print(f"  Shape after cleaning: {df.shape}")
    print(f"  Columns: {list(df.columns)}")

    # Rename columns to match the original CSV schema for compatibility
    rename_map = {
        "Project Number": "Project ID",
        "Project Name": "Title",
        "Accredited Researchers": "Researchers",
        "Legal Gateway": "Legal Basis",
        "Protected Data Accessed": "Datasets Used",
        "Processing Environment": "Secure Research Service",
    }
    df = df.rename(columns=rename_map)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Saved CSV to: {csv_path}")
    return df


if __name__ == "__main__":
    xlsx_url = find_xlsx_url()
    download_xlsx(xlsx_url, XLSX_OUT)
    df = xlsx_to_csv(XLSX_OUT, CSV_OUT)
    print(f"\nDone. {len(df):,} rows scraped.")
