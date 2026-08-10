import json
import hashlib
import os
import tempfile
import unittest

from analysis.register_cleaning import load_raw_register
from analysis.register_manifest import (
    CURRENT_POINTER,
    FROZEN_CLEANED_PATH,
    FROZEN_CLEANED_SHA256,
    FROZEN_SOURCE_CSV_SHA256,
    FROZEN_SOURCE_XLSX_SHA256,
    MANIFEST_FILENAME,
    add_version,
    load_manifest,
    record_fetch_observation,
    resolve_register_csv,
    write_manifest,
)


def _write_csv(data_dir: str, name: str, rows: int = 3) -> str:
    path = os.path.join(data_dir, name)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("Project Number,Project Name,Accreditation Date\n")
        for i in range(rows):
            f.write(f"2026/{i:03d},Project {i},2026-01-0{i + 1}\n")
    return path


def _write_schema2_manifest(data_dir: str) -> tuple[bytes, bytes]:
    xlsx_bytes = b"original immutable workbook bytes"
    # The manifest validator deliberately fixes the real frozen identity. The
    # synthetic bytes exercise later snapshots; direct byte assertions for the
    # three real frozen files live in the canonical-release integrity tests.
    raw_sha = FROZEN_SOURCE_XLSX_SHA256
    csv_bytes = (
        b"\xef\xbb\xbfProject ID,Title,Researchers,Legal Basis,Datasets Used,"
        b"Secure Research Service,Accreditation Date\n"
        b"2026/001,Original,A Researcher,Digital Economy Act 2017,Data,SRS,2026-01-01\n"
    )
    open(os.path.join(data_dir, "original.xlsx"), "wb").write(xlsx_bytes)
    open(os.path.join(data_dir, "original.csv"), "wb").write(csv_bytes)
    snapshot_id = f"sha256:{raw_sha}"
    manifest = {
        "schema_version": 2,
        "current": "20260601",
        "pointers": {
            CURRENT_POINTER: {
                "snapshot_id": snapshot_id,
                "raw_xlsx_sha256": raw_sha,
                "canonical_csv_sha256": FROZEN_SOURCE_CSV_SHA256,
            },
            "frozen_validation_snapshot": {
                "snapshot_id": snapshot_id,
                "raw_xlsx_sha256": raw_sha,
                "canonical_csv_sha256": FROZEN_SOURCE_CSV_SHA256,
                "cleaned_population_path": FROZEN_CLEANED_PATH,
                "cleaned_population_sha256": FROZEN_CLEANED_SHA256,
            },
        },
        "versions": [{
            "version": "20260601", "latest_snapshot_id": snapshot_id,
            "csv": "original.csv", "xlsx": "original.xlsx",
            "sha256_csv": FROZEN_SOURCE_CSV_SHA256, "row_count": 1,
        }],
        "content_snapshots": [{
            "snapshot_id": snapshot_id,
            "raw_xlsx_path": "original.xlsx",
            "canonical_csv_path": "original.csv",
            "raw_xlsx_sha256": raw_sha,
            "canonical_csv_sha256": FROZEN_SOURCE_CSV_SHA256,
            "raw_row_count": 1,
            "first_seen_at": "2026-06-11",
            "nominal_source_date": "2026-06-01",
            "source_url": "https://example.test/uploads/2026/06/register.xlsx",
            "upstream_filename": "register.xlsx",
            "converter": {"identity": "test"},
        }],
        "fetch_observations": [{
            "observation_id": "obs-0001", "observed_at": "2026-06-11",
            "source_url": "https://example.test/uploads/2026/06/register.xlsx",
            "upstream_filename": "register.xlsx", "nominal_source_date": "2026-06-01",
            "upload_directory_date": "2026-06", "raw_xlsx_sha256": raw_sha,
            "canonical_csv_sha256": FROZEN_SOURCE_CSV_SHA256,
            "snapshot_id": snapshot_id,
        }],
        "analytical_states": [],
    }
    write_manifest(manifest, data_dir)
    return xlsx_bytes, csv_bytes


class RegisterManifestTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_add_version_creates_manifest_and_sets_current(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260611.csv", rows=4)
        record = add_version(
            "dea_accredited_projects_20260611.csv",
            data_dir=self.data_dir,
        )
        self.assertEqual(record["version"], "20260611")
        self.assertEqual(record["row_count"], 4)
        self.assertEqual(len(record["sha256_csv"]), 64)

        manifest = load_manifest(self.data_dir)
        self.assertEqual(manifest["current"], "20260611")
        self.assertEqual(len(manifest["versions"]), 1)

    def test_add_version_without_set_current_keeps_pointer(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260325.csv")
        _write_csv(self.data_dir, "dea_accredited_projects_20260611.csv")
        add_version("dea_accredited_projects_20260325.csv", data_dir=self.data_dir)
        add_version(
            "dea_accredited_projects_20260611.csv",
            data_dir=self.data_dir,
            set_current=False,
        )
        manifest = load_manifest(self.data_dir)
        self.assertEqual(manifest["current"], "20260325")
        self.assertEqual(len(manifest["versions"]), 2)

    def test_add_version_requires_explicit_version_for_unversioned_name(self):
        _write_csv(self.data_dir, "dea_accredited_projects.csv")
        with self.assertRaises(ValueError):
            add_version("dea_accredited_projects.csv", data_dir=self.data_dir)
        record = add_version(
            "dea_accredited_projects.csv",
            data_dir=self.data_dir,
            version="legacy",
        )
        self.assertEqual(record["version"], "legacy")

    def test_resolve_current_and_explicit_versions(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260325.csv")
        _write_csv(self.data_dir, "dea_accredited_projects_20260611.csv")
        add_version("dea_accredited_projects_20260325.csv", data_dir=self.data_dir)
        add_version("dea_accredited_projects_20260611.csv", data_dir=self.data_dir)

        path, record = resolve_register_csv(self.data_dir)
        self.assertTrue(path.endswith("dea_accredited_projects_20260611.csv"))
        self.assertEqual(record["version"], "20260611")

        path, record = resolve_register_csv(self.data_dir, version="20260325")
        self.assertTrue(path.endswith("dea_accredited_projects_20260325.csv"))

    def test_resolve_unknown_version_or_missing_manifest_raises(self):
        with self.assertRaises(FileNotFoundError):
            resolve_register_csv(self.data_dir)
        _write_csv(self.data_dir, "dea_accredited_projects_20260325.csv")
        add_version("dea_accredited_projects_20260325.csv", data_dir=self.data_dir)
        with self.assertRaises(FileNotFoundError):
            resolve_register_csv(self.data_dir, version="20990101")

    def test_resolve_missing_file_raises(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260325.csv")
        add_version("dea_accredited_projects_20260325.csv", data_dir=self.data_dir)
        os.remove(os.path.join(self.data_dir, "dea_accredited_projects_20260325.csv"))
        with self.assertRaises(FileNotFoundError):
            resolve_register_csv(self.data_dir)


class LoadRawRegisterResolutionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_manifest_current_version_wins(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260325.csv", rows=2)
        _write_csv(self.data_dir, "dea_accredited_projects_20260611.csv", rows=5)
        add_version("dea_accredited_projects_20260325.csv", data_dir=self.data_dir)
        add_version("dea_accredited_projects_20260611.csv", data_dir=self.data_dir)

        df, source = load_raw_register(self.data_dir)
        self.assertEqual(source, "dea_accredited_projects_20260611.csv")
        self.assertEqual(len(df), 5)

    def test_explicit_manifest_version(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260325.csv", rows=2)
        _write_csv(self.data_dir, "dea_accredited_projects_20260611.csv", rows=5)
        add_version("dea_accredited_projects_20260325.csv", data_dir=self.data_dir)
        add_version("dea_accredited_projects_20260611.csv", data_dir=self.data_dir)

        df, source = load_raw_register(self.data_dir, version="20260325")
        self.assertEqual(source, "dea_accredited_projects_20260325.csv")
        self.assertEqual(len(df), 2)

    def test_explicit_version_does_not_fall_back(self):
        _write_csv(self.data_dir, "dea_accredited_projects.csv", rows=2)
        with self.assertRaises(FileNotFoundError):
            load_raw_register(self.data_dir, version="20260325")

    def test_no_manifest_falls_back_to_candidate_files(self):
        _write_csv(self.data_dir, "dea_accredited_projects.csv", rows=2)
        self.assertFalse(os.path.exists(os.path.join(self.data_dir, MANIFEST_FILENAME)))
        df, source = load_raw_register(self.data_dir)
        self.assertEqual(source, "dea_accredited_projects.csv")
        self.assertEqual(len(df), 2)

    def test_explicit_candidate_files_bypass_manifest(self):
        _write_csv(self.data_dir, "dea_accredited_projects_20260611.csv", rows=5)
        _write_csv(self.data_dir, "other.csv", rows=1)
        add_version("dea_accredited_projects_20260611.csv", data_dir=self.data_dir)
        df, source = load_raw_register(self.data_dir, ["other.csv"])
        self.assertEqual(source, "other.csv")
        self.assertEqual(len(df), 1)

    def test_manifest_is_valid_json_in_repo(self):
        repo_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        manifest_path = os.path.join(repo_data_dir, MANIFEST_FILENAME)
        self.assertTrue(os.path.exists(manifest_path), "repo data/ manifest should exist")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        versions = {record["version"] for record in manifest["versions"]}
        self.assertIn(manifest["current"], versions)


class HashAddressedManifestTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        self.original_xlsx, self.original_csv = _write_schema2_manifest(self.data_dir)

    def record(
        self,
        xlsx_bytes: bytes,
        csv_bytes: bytes,
        url: str,
        observed_at: str,
        nominal_source_date: str = "2026-06-01",
    ):
        return record_fetch_observation(
            data_dir=self.data_dir,
            source_url=url,
            nominal_source_date=nominal_source_date,
            upload_directory_date=url.split("/uploads/")[1][:7].replace("/", "-"),
            xlsx_bytes=xlsx_bytes,
            canonical_csv_bytes=csv_bytes,
            raw_row_count=1,
            converter={"identity": "test", "canonical_line_terminator": "LF"},
            observed_at=observed_at,
        )

    def test_same_nominal_date_different_hash_creates_distinct_revision(self):
        result = self.record(
            b"revised workbook bytes",
            self.original_csv.replace(b"Original", b"Revised!"),
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        manifest = load_manifest(self.data_dir)
        self.assertTrue(result["created_snapshot"])
        self.assertEqual(result["outcome"], "new_snapshot")
        self.assertEqual(len(manifest["content_snapshots"]), 2)
        self.assertEqual(len(manifest["fetch_observations"]), 2)
        self.assertEqual(
            manifest["pointers"][CURRENT_POINTER]["snapshot_id"],
            result["snapshot"]["snapshot_id"],
        )
        self.assertEqual(
            manifest["pointers"]["frozen_validation_snapshot"]["canonical_csv_sha256"],
            FROZEN_SOURCE_CSV_SHA256,
        )

    def test_both_urls_and_upload_directory_movement_are_retained(self):
        self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        observations = load_manifest(self.data_dir)["fetch_observations"]
        self.assertEqual(
            [item["upload_directory_date"] for item in observations],
            ["2026-06", "2026-08"],
        )
        self.assertEqual(len({item["source_url"] for item in observations}), 2)

    def test_existing_snapshot_bytes_are_never_overwritten(self):
        result = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        path = os.path.join(
            self.data_dir, *result["snapshot"]["raw_xlsx_path"].split("/")
        )
        before = open(path, "rb").read()
        self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/09/register.xlsx",
            "2026-09-01T09:00:00+00:00",
        )
        self.assertEqual(open(path, "rb").read(), before)

    def test_exact_repeat_is_byte_stable_noop_and_immediate_retry_is_idempotent(self):
        first = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        manifest_path = os.path.join(self.data_dir, MANIFEST_FILENAME)
        snapshot_path = os.path.join(
            self.data_dir, *first["snapshot"]["raw_xlsx_path"].split("/")
        )
        manifest_before = open(manifest_path, "rb").read()
        snapshot_before = open(snapshot_path, "rb").read()
        second = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:01+00:00",
        )
        manifest = load_manifest(self.data_dir)
        self.assertTrue(first["created_snapshot"])
        self.assertFalse(second["created_snapshot"])
        self.assertFalse(second["created_observation"])
        self.assertEqual(second["outcome"], "unchanged_noop")
        self.assertEqual(len(manifest["content_snapshots"]), 2)
        self.assertEqual(len(manifest["fetch_observations"]), 2)
        self.assertEqual(open(manifest_path, "rb").read(), manifest_before)
        self.assertEqual(open(snapshot_path, "rb").read(), snapshot_before)

    def test_same_content_at_new_url_adds_observation_not_snapshot(self):
        first = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        second = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://mirror.example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T10:00:00+00:00",
        )
        manifest = load_manifest(self.data_dir)
        self.assertTrue(first["created_snapshot"])
        self.assertFalse(second["created_snapshot"])
        self.assertTrue(second["created_observation"])
        self.assertEqual(second["outcome"], "new_provenance_observation")
        self.assertEqual(len(manifest["content_snapshots"]), 2)
        self.assertEqual(len(manifest["fetch_observations"]), 3)

    def test_same_raw_with_new_canonical_hash_is_distinct_snapshot(self):
        first = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        second = self.record(
            b"revised workbook bytes", self.original_csv.replace(b"Original", b"Revised!"),
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T10:00:00+00:00",
        )
        manifest = load_manifest(self.data_dir)
        self.assertTrue(first["created_snapshot"])
        self.assertTrue(second["created_snapshot"])
        self.assertEqual(second["outcome"], "new_snapshot")
        self.assertNotEqual(first["snapshot"]["snapshot_id"], second["snapshot"]["snapshot_id"])
        self.assertEqual(len(manifest["content_snapshots"]), 3)

    def test_new_nominal_source_date_is_retained(self):
        first = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-10T09:00:00+00:00",
        )
        second = self.record(
            b"revised workbook bytes", self.original_csv,
            "https://example.test/uploads/2026/08/register.xlsx",
            "2026-08-11T09:00:00+00:00",
            nominal_source_date="2026-07-01",
        )
        manifest = load_manifest(self.data_dir)
        self.assertTrue(first["created_snapshot"])
        self.assertFalse(second["created_snapshot"])
        self.assertTrue(second["created_observation"])
        self.assertEqual(second["outcome"], "new_provenance_observation")
        self.assertEqual(manifest["fetch_observations"][-1]["nominal_source_date"], "2026-07-01")


class CommittedManifestIntegrityTest(unittest.TestCase):
    def test_snapshot_paths_hashes_and_analytical_links_are_consistent(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(root, "data")
        manifest = load_manifest(data_dir)
        snapshots = {item["snapshot_id"]: item for item in manifest["content_snapshots"]}
        for snapshot in snapshots.values():
            xlsx_path = os.path.join(data_dir, *snapshot["raw_xlsx_path"].split("/"))
            csv_path = os.path.join(data_dir, *snapshot["canonical_csv_path"].split("/"))
            self.assertEqual(
                hashlib.sha256(open(xlsx_path, "rb").read()).hexdigest(),
                snapshot["raw_xlsx_sha256"],
            )
            csv_bytes = open(csv_path, "rb").read().replace(b"\r\n", b"\n")
            self.assertEqual(
                hashlib.sha256(csv_bytes).hexdigest(),
                snapshot["canonical_csv_sha256"],
            )
        for observation in manifest["fetch_observations"]:
            self.assertIn(observation["snapshot_id"], snapshots)
        for state in manifest["analytical_states"]:
            self.assertTrue(set(state["source_snapshot_ids"]) <= set(snapshots))
        self.assertEqual(
            manifest["pointers"]["frozen_validation_snapshot"]["canonical_csv_sha256"],
            FROZEN_SOURCE_CSV_SHA256,
        )
        self.assertEqual(
            manifest["pointers"]["frozen_validation_snapshot"]["raw_xlsx_sha256"],
            FROZEN_SOURCE_XLSX_SHA256,
        )


if __name__ == "__main__":
    unittest.main()
