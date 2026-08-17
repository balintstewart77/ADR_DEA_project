import io
import json
import os
import tempfile
import sys
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scrape"))

from fetch_register import (  # noqa: E402
    find_xlsx_urls,
    parse_upload_directory_date,
    parse_url_date,
    run_fetch,
    select_register_url,
    validate_register_dataframe,
    xlsx_to_dataframe,
)

# The link shapes actually observed on the UKSA page (June 2026).
PROJECTS_JUNE = (
    "https://uksa.statisticsauthority.gov.uk/wp-content/uploads/2026/06/"
    "01-06-2026-UKSA-Accredited-Research-Projects-Report-1.xlsx"
)
PROJECTS_NOV = (
    "https://uksa.statisticsauthority.gov.uk/wp-content/uploads/2025/11/"
    "06-11-2025-UKSA-Accredited-Research-Projects-Report-1.xlsx"
)
RESEARCHERS_JUNE = (
    "https://uksa.statisticsauthority.gov.uk/wp-content/uploads/2026/06/"
    "01-06-2026-UKSA-Accredited-Researchers-Report.xlsx"
)
REPUBLISHED_JUNE_RAW_SHA256 = (
    "33c8ba2abd2085a28b2e5ca5ba2913398c6edb96f59f31331e5c125c96661014"
)
REPUBLISHED_JUNE_CSV_SHA256 = (
    "918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd"
)
REPUBLISHED_JUNE_URL = PROJECTS_JUNE.replace("/2026/06/", "/2026/08/")


class UrlDiscoveryTest(unittest.TestCase):
    def test_find_xlsx_urls_dedupes_and_preserves_order(self):
        html = (
            f'<a href="{PROJECTS_NOV}">old</a>'
            f'<a href="{PROJECTS_JUNE}">new</a>'
            f'<a href="{PROJECTS_JUNE}">new again</a>'
        )
        self.assertEqual(find_xlsx_urls(html), [PROJECTS_NOV, PROJECTS_JUNE])

    def test_parse_filename_dmy_date(self):
        self.assertEqual(parse_url_date(PROJECTS_JUNE), date(2026, 6, 1))
        self.assertEqual(parse_url_date(PROJECTS_NOV), date(2025, 11, 6))

    def test_parse_month_name_date(self):
        url = "https://example.org/uploads/Accredited-projects-March-2026.xlsx"
        self.assertEqual(parse_url_date(url), date(2026, 3, 1))

    def test_parse_uploads_path_fallback(self):
        url = "https://example.org/wp-content/uploads/2026/03/projects-list.xlsx"
        self.assertEqual(parse_url_date(url), date(2026, 3, 1))

    def test_parse_no_date(self):
        self.assertIsNone(parse_url_date("https://example.org/projects.xlsx"))

    def test_upload_directory_date_is_independent_of_nominal_filename_date(self):
        republished = PROJECTS_JUNE.replace("/2026/06/", "/2026/08/")
        self.assertEqual(parse_url_date(republished), date(2026, 6, 1))
        self.assertEqual(parse_upload_directory_date(republished), "2026-08")

    def test_selects_latest_projects_report_not_researchers_report(self):
        # The researchers report sorts after the projects report
        # lexicographically; date-aware keyword selection must pick the
        # June projects file.
        urls = [PROJECTS_NOV, PROJECTS_JUNE, RESEARCHERS_JUNE]
        url, source_date = select_register_url(urls)
        self.assertEqual(url, PROJECTS_JUNE)
        self.assertEqual(source_date, date(2026, 6, 1))

    def test_no_projects_candidates_raises(self):
        with self.assertRaises(RuntimeError):
            select_register_url([RESEARCHERS_JUNE])
        with self.assertRaises(RuntimeError):
            select_register_url([])

    def test_ambiguous_undated_candidates_raise(self):
        urls = [
            "https://example.org/projects-a.xlsx",
            "https://example.org/projects-b.xlsx",
        ]
        with self.assertRaises(RuntimeError):
            select_register_url(urls)

    def test_single_undated_candidate_is_accepted(self):
        url, source_date = select_register_url(["https://example.org/projects.xlsx"])
        self.assertEqual(url, "https://example.org/projects.xlsx")
        self.assertIsNone(source_date)


def _workbook_bytes(rows, *, preamble=True, sheet_name="Accredited Projects"):
    frame_rows = []
    if preamble:
        frame_rows.append(["List of accredited research projects", None, None, None, None, None, None])
        frame_rows.append([None, None, None, None, None, None, None])
    frame_rows.append([
        "Project Number", "Project Name", "Accredited Researchers",
        "Legal Gateway", "Protected Data Accessed", "Processing Environment",
        "Accreditation Date",
    ])
    frame_rows.extend(rows)
    buffer = io.BytesIO()
    pd.DataFrame(frame_rows).to_excel(
        buffer, index=False, header=False, sheet_name=sheet_name
    )
    return buffer.getvalue()


def _sample_rows(n=3):
    return [
        [
            f"2026/{i:03d}", f"Project {i}", f"Researcher {i}, University {i}",
            "Digital Economy Act 2017", "ONS: Labour Force Survey",
            "ONS Secure Research Service", f"2026-01-{i + 1:02d}",
        ]
        for i in range(n)
    ]


def _copy_republished_june_manifest(source_data: str, target_data: str) -> str:
    """Create the manifest state in which the 1,450-row fixture was current."""
    source_path = os.path.join(source_data, "register_provenance_manifest.json")
    with open(source_path, encoding="utf-8") as handle:
        manifest = json.load(handle)

    matches = [
        snapshot
        for snapshot in manifest["content_snapshots"]
        if snapshot.get("raw_xlsx_sha256") == REPUBLISHED_JUNE_RAW_SHA256
        and snapshot.get("canonical_csv_sha256") == REPUBLISHED_JUNE_CSV_SHA256
    ]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one republished June fixture snapshot")
    snapshot = matches[0]
    frozen_snapshot_id = manifest["pointers"]["frozen_validation_snapshot"]["snapshot_id"]
    retained_snapshot_ids = {frozen_snapshot_id, snapshot["snapshot_id"]}
    manifest["content_snapshots"] = [
        item
        for item in manifest["content_snapshots"]
        if item["snapshot_id"] in retained_snapshot_ids
    ]
    manifest["fetch_observations"] = [
        item
        for item in manifest["fetch_observations"]
        if item["snapshot_id"] in retained_snapshot_ids
    ]
    manifest["analytical_states"] = [
        state
        for state in manifest["analytical_states"]
        if set(state.get("source_snapshot_ids", [])) <= retained_snapshot_ids
    ]
    manifest["current"] = "20260601"
    manifest["pointers"]["current_latest_revision"] = {
        "snapshot_id": snapshot["snapshot_id"],
        "raw_xlsx_sha256": REPUBLISHED_JUNE_RAW_SHA256,
        "canonical_csv_sha256": REPUBLISHED_JUNE_CSV_SHA256,
    }
    version = next(
        item for item in manifest["versions"] if item["version"] == "20260601"
    )
    manifest["versions"] = [version]
    version.update({
        "latest_snapshot_id": snapshot["snapshot_id"],
        "csv": snapshot["canonical_csv_path"],
        "xlsx": snapshot["raw_xlsx_path"],
        "source_url": snapshot["source_url"],
        "retrieved_at": snapshot["first_seen_at"][:10],
        "sha256_csv": REPUBLISHED_JUNE_CSV_SHA256,
        "sha256_xlsx": REPUBLISHED_JUNE_RAW_SHA256,
        "row_count": snapshot["raw_row_count"],
    })

    target_path = os.path.join(target_data, "register_provenance_manifest.json")
    with open(target_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    return target_path


class XlsxConversionTest(unittest.TestCase):
    def test_header_detection_skips_preamble_and_renames_columns(self):
        df = xlsx_to_dataframe(_workbook_bytes(_sample_rows()))
        self.assertEqual(len(df), 3)
        for col in [
            "Project ID", "Title", "Researchers", "Legal Basis",
            "Datasets Used", "Secure Research Service", "Accreditation Date",
        ]:
            self.assertIn(col, df.columns)
        self.assertEqual(df.iloc[0]["Project ID"], "2026/000")

    def test_no_preamble_also_works(self):
        df = xlsx_to_dataframe(_workbook_bytes(_sample_rows(), preamble=False))
        self.assertEqual(len(df), 3)
        self.assertIn("Project ID", df.columns)


class ValidationTest(unittest.TestCase):
    def _valid_df(self, n=5):
        return xlsx_to_dataframe(_workbook_bytes(_sample_rows(n)))

    def test_valid_register_passes(self):
        self.assertEqual(validate_register_dataframe(self._valid_df(), min_rows=3), [])

    def test_missing_column_fails(self):
        df = self._valid_df().drop(columns=["Datasets Used"])
        problems = validate_register_dataframe(df, min_rows=None)
        self.assertEqual(len(problems), 1)
        self.assertIn("Datasets Used", problems[0])

    def test_shrinking_register_fails(self):
        problems = validate_register_dataframe(self._valid_df(3), min_rows=10)
        self.assertTrue(any("shrank" in p for p in problems))

    def test_unparseable_dates_fail(self):
        df = self._valid_df(5)
        df["Accreditation Date"] = "not a date"
        problems = validate_register_dataframe(df, min_rows=None)
        self.assertTrue(any("Accreditation Date" in p for p in problems))


class LocalDryRunTest(unittest.TestCase):
    def test_republished_fixture_dry_run_has_no_network_or_writes(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_data = os.path.join(root, "data")
        revised_xlsx = os.path.join(
            source_data,
            "register_snapshots",
            REPUBLISHED_JUNE_RAW_SHA256,
            "01-06-2026-UKSA-Accredited-Research-Projects-Report-1.xlsx",
        )
        with tempfile.TemporaryDirectory() as data_dir:
            manifest_path = _copy_republished_june_manifest(source_data, data_dir)
            before = open(manifest_path, "rb").read()
            with patch("fetch_register.download_bytes", return_value=open(revised_xlsx, "rb").read()):
                result = run_fetch(
                    url=REPUBLISHED_JUNE_URL,
                    data_dir=data_dir,
                    dry_run=True,
                )
            self.assertEqual(result["status"], "dry-run")
            self.assertEqual(result["outcome"], "unchanged_noop")
            self.assertEqual(result["raw_xlsx_sha256"], REPUBLISHED_JUNE_RAW_SHA256)
            self.assertEqual(open(manifest_path, "rb").read(), before)

    def test_two_identical_local_fetches_are_manifest_byte_stable_noops(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_data = os.path.join(root, "data")
        revised_xlsx = os.path.join(
            source_data,
            "register_snapshots",
            REPUBLISHED_JUNE_RAW_SHA256,
            "01-06-2026-UKSA-Accredited-Research-Projects-Report-1.xlsx",
        )
        xlsx_bytes = open(revised_xlsx, "rb").read()
        with tempfile.TemporaryDirectory() as data_dir:
            manifest_path = _copy_republished_june_manifest(source_data, data_dir)
            before = open(manifest_path, "rb").read()
            with patch("fetch_register.download_bytes", return_value=xlsx_bytes):
                first = run_fetch(
                    url=REPUBLISHED_JUNE_URL,
                    data_dir=data_dir,
                )
                after_first = open(manifest_path, "rb").read()
                second = run_fetch(
                    url=REPUBLISHED_JUNE_URL,
                    data_dir=data_dir,
                )
            self.assertEqual(first["outcome"], "unchanged_noop")
            self.assertEqual(second["outcome"], "unchanged_noop")
            self.assertFalse(first["created_observation"])
            self.assertFalse(second["created_observation"])
            self.assertEqual(before, after_first)
            self.assertEqual(after_first, open(manifest_path, "rb").read())
            self.assertEqual(os.listdir(data_dir), ["register_provenance_manifest.json"])


if __name__ == "__main__":
    unittest.main()
