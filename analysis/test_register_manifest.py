import json
import os
import tempfile
import unittest

from analysis.register_cleaning import load_raw_register
from analysis.register_manifest import (
    MANIFEST_FILENAME,
    add_version,
    load_manifest,
    resolve_register_csv,
)


def _write_csv(data_dir: str, name: str, rows: int = 3) -> str:
    path = os.path.join(data_dir, name)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("Project Number,Project Name,Accreditation Date\n")
        for i in range(rows):
            f.write(f"2026/{i:03d},Project {i},2026-01-0{i + 1}\n")
    return path


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


if __name__ == "__main__":
    unittest.main()
