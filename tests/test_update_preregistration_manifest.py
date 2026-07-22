from __future__ import annotations

import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.update_preregistration_manifest import (
    COMPUTED_COLUMNS,
    ManifestError,
    refresh_manifest,
    sha256_file,
)


FIELDNAMES = [
    "artifact_id",
    "artefact_group",
    "filename",
    "current_path",
    "proposed_package_path",
    "description",
    "version",
    "current_state",
    "status_at_registration",
    "pre_existing_or_prospective",
    "access_class",
    "registration_inclusion",
    "sha256",
    "created_or_modified_at",
    "source_commit",
    "authoritative_status",
    "supersedes_or_superseded_by",
    "notes",
    "size_bytes",
]
TEST_COMMIT = "a" * 40


class ManifestUpdaterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.manifest = self.root / "manifest.csv"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def row(self, **overrides: str) -> dict[str, str]:
        row = {field: "" for field in FIELDNAMES}
        row.update(
            {
                "artifact_id": "ART-001",
                "artefact_group": "test",
                "filename": "example.txt",
                "current_path": "example.txt",
                "description": "Manually curated description",
                "version": "manual-v1",
                "current_state": "existing",
                "status_at_registration": "frozen",
                "pre_existing_or_prospective": "pre_existing",
                "access_class": "public",
                "registration_inclusion": "include",
                "authoritative_status": "supporting",
                "notes": "Manual note",
            }
        )
        row.update(overrides)
        return row

    def write_manifest(self, rows: list[dict[str, str]]) -> None:
        with self.manifest.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

    def read_rows(self) -> list[dict[str, str]]:
        with self.manifest.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_hashing_an_existing_file(self) -> None:
        path = self.root / "example.txt"
        path.write_bytes(b"exact bytes\n")
        expected = hashlib.sha256(b"exact bytes\n").hexdigest()
        self.assertEqual(sha256_file(path), expected)

        self.write_manifest([self.row()])
        result = refresh_manifest(
            self.manifest, self.root, source_commit=TEST_COMMIT
        )
        self.assertEqual(result.updated, 1)
        self.assertEqual(self.read_rows()[0]["sha256"], expected)
        self.assertEqual(self.read_rows()[0]["size_bytes"], "12")
        self.assertNotIn(b"\r\n", self.manifest.read_bytes())

    def test_missing_row_is_left_unchanged(self) -> None:
        row = self.row(
            current_path="missing.txt",
            current_state="missing",
            sha256="manual-placeholder",
            created_or_modified_at="manual-time",
            source_commit="manual-commit",
            size_bytes="manual-size",
        )
        self.write_manifest([row])
        result = refresh_manifest(
            self.manifest, self.root, source_commit=TEST_COMMIT
        )
        self.assertEqual(result.updated, 0)
        after = self.read_rows()[0]
        for column in COMPUTED_COLUMNS:
            self.assertEqual(after[column], row[column])

    def test_manual_columns_are_preserved(self) -> None:
        (self.root / "example.txt").write_text("content", encoding="utf-8")
        before = self.row()
        self.write_manifest([before])
        refresh_manifest(self.manifest, self.root, source_commit=TEST_COMMIT)
        after = self.read_rows()[0]
        for column in FIELDNAMES:
            if column not in COMPUTED_COLUMNS:
                self.assertEqual(after[column], before[column])

    def test_restricted_paths_are_excluded_without_opt_in(self) -> None:
        restricted_dir = self.root / "preregistration_restricted"
        restricted_dir.mkdir()
        (restricted_dir / "secret.txt").write_text("restricted", encoding="utf-8")
        self.write_manifest(
            [
                self.row(
                    current_path="preregistration_restricted/secret.txt",
                    access_class="restricted",
                )
            ]
        )
        result = refresh_manifest(
            self.manifest, self.root, source_commit=TEST_COMMIT
        )
        self.assertEqual(result.checked, 0)
        self.assertEqual(result.updated, 0)
        self.assertEqual(self.read_rows()[0]["sha256"], "")
        self.assertTrue(any("restricted path skipped" in item for item in result.skipped))

    def test_check_detects_changed_file_without_writing(self) -> None:
        path = self.root / "example.txt"
        path.write_text("before", encoding="utf-8")
        self.write_manifest([self.row()])
        refresh_manifest(self.manifest, self.root, source_commit=TEST_COMMIT)
        recorded = self.read_rows()[0]

        path.write_text("after", encoding="utf-8")
        result = refresh_manifest(
            self.manifest,
            self.root,
            check=True,
            source_commit=TEST_COMMIT,
        )
        self.assertTrue(any("stale sha256" in issue for issue in result.issues))
        self.assertEqual(self.read_rows()[0], recorded)

    def test_extra_cells_are_rejected_as_a_shifted_row(self) -> None:
        self.manifest.write_text(
            ",".join(FIELDNAMES) + "\n" + ",".join(["ART-001", *([""] * len(FIELDNAMES))]) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "beyond the declared columns"):
            refresh_manifest(self.manifest, self.root, source_commit=TEST_COMMIT)


if __name__ == "__main__":
    unittest.main()
