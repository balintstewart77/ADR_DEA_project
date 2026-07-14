from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from analysis import migrate_record_id_whitespace as migration


def mapping(old: str = "2020/001 ", new: str = "2020/001") -> migration.RecordIdMapping:
    return migration.RecordIdMapping(
        old_record_id=old,
        new_record_id=new,
        official_project_id=new,
        title="Synthetic public title",
        fingerprint="fixture",
        reference_csv_row=2,
        removed_characters="space",
    )


class RecordIdWhitespaceMigrationUnitTest(unittest.TestCase):
    def test_clean_one_to_one_csv_migration(self) -> None:
        rows = [{"Record ID": "2020/001 ", "classification": "unchanged"}]
        migrated, changes = migration.migrate_csv_rows(
            rows, {"2020/001 ": "2020/001"}, exact_fields=["Record ID"]
        )
        self.assertEqual(changes, 1)
        self.assertEqual(migrated[0]["Record ID"], "2020/001")
        self.assertEqual(migrated[0]["classification"], "unchanged")

    def test_json_mapping_key_and_embedded_id_migration(self) -> None:
        classification = {
            "status": "ok",
            "substantive_domains": ["Domain A"],
            "rationale": "unchanged rationale",
            "record_id": "2020/001 ",
            "project_id": "2020/001 ",
            "Record ID": "2020/001 ",
        }
        payload = {"__meta__": {"model": "fixture"}, "entries": {"2020/001 ": classification}}
        migrated, changes = migration.migrate_json_cache(
            payload, {"2020/001 ": "2020/001"}
        )
        self.assertGreaterEqual(changes, 1)
        self.assertEqual(list(migrated["entries"]), ["2020/001"])
        entry = migrated["entries"]["2020/001"]
        self.assertEqual(entry["record_id"], "2020/001")
        self.assertEqual(entry["project_id"], "2020/001")
        self.assertEqual(entry["Record ID"], "2020/001")
        self.assertEqual(entry["substantive_domains"], ["Domain A"])
        self.assertEqual(entry["rationale"], "unchanged rationale")

    def test_json_collision_detection(self) -> None:
        payload = {"entries": {"2020/001 ": {"value": 1}, "2020/001": {"value": 2}}}
        with self.assertRaisesRegex(migration.MigrationError, "target key already exists"):
            migration.migrate_json_cache(payload, {"2020/001 ": "2020/001"})

    def test_classification_content_is_unchanged(self) -> None:
        entry = {
            "status": "ok",
            "substantive_domains": ["Domain A", "Domain B"],
            "analytical_purpose": ["Purpose A"],
            "cross_cutting_tags": ["Tag A"],
            "rationale": "Exact model output.",
            "fingerprint": "abc123",
        }
        payload = {"entries": {"2020/001 ": entry}}
        migrated, _changes = migration.migrate_json_cache(
            payload, {"2020/001 ": "2020/001"}
        )
        self.assertEqual(migrated["entries"]["2020/001"], entry)

    def test_already_clean_file_is_a_noop(self) -> None:
        payload = {"entries": {"2020/001": {"rationale": "unchanged"}}}
        migrated, changes = migration.migrate_json_cache(
            payload, {"2020/001 ": "2020/001"}
        )
        self.assertEqual(migrated, payload)
        self.assertEqual(changes, 0)

    def test_unmapped_dirty_key_fails(self) -> None:
        with self.assertRaisesRegex(migration.MigrationError, "Unmapped dirty"):
            migration.migrate_exact_id("2020/999 ", {"2020/001 ": "2020/001"})

    def test_normalisation_collision_in_mapping_fails(self) -> None:
        corrected = [{
            "Project ID": "2020/001", "Record ID": "2020/001",
            "Title": "First", "Datasets Used": "Data A",
        }]
        reference = [
            {"Project ID": "2020/001", "Record ID": "2020/001 ", "Title": "First", "Datasets Used": "Data A"},
            {"Project ID": "2020/002", "Record ID": "2020/001", "Title": "Second", "Datasets Used": "Data B"},
        ]
        with self.assertRaisesRegex(migration.MigrationError, "target already exists"):
            migration.derive_mapping(corrected, reference)


class RecordIdWhitespaceMigrationCheckModeTest(unittest.TestCase):
    def test_check_mode_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data" / "source.csv").write_bytes(b"fixture source\n")
            reference = root / "reference.csv"
            with reference.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["Project ID", "Record ID", "Title", "Datasets Used"],
                )
                writer.writeheader()
                writer.writerow({
                    "Project ID": "2020/001",
                    "Record ID": "2020/001 ",
                    "Title": "Synthetic public title",
                    "Datasets Used": "Public data",
                })
            cleaned = pd.DataFrame([{
                "Project ID": "2020/001",
                "Record ID": "2020/001",
                "Title": "Synthetic public title",
                "Datasets Used": "Public data",
            }])
            stats = {
                "raw_loaded": 1,
                "dropped_no_date_or_title": 0,
                "dropped_non_dea": 0,
                "rows_after_dea_filter": 1,
                "duplicate_tier1_rows_removed": 0,
                "duplicate_tier2_rows_removed": 0,
                "duplicate_ruling_rows_removed": 0,
            }
            outputs = [
                root / "package" / "cleaned.csv",
                root / "package" / "integrity.json",
                root / "package" / "audit.csv",
                root / "package" / "migration.json",
            ]
            argv = [
                "--repository-root", str(root),
                "--reference-csv", str(reference),
                "--cleaned-output", str(outputs[0]),
                "--integrity-report", str(outputs[1]),
                "--normalisation-audit", str(outputs[2]),
                "--migration-log", str(outputs[3]),
                "--expected-mappings", "1",
                "--expected-cleaned-rows", "1",
                "--expected-project-ids", "1",
                "--expected-duplicate-project-groups", "0",
                "--check",
            ]
            with patch(
                "analysis.register_cleaning.load_clean_register",
                return_value=(cleaned, stats, "source.csv"),
            ):
                self.assertEqual(migration.main(argv), 0)
            self.assertTrue(all(not path.exists() for path in outputs))

    def test_clean_metadata_is_a_check_mode_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data" / "source.csv").write_bytes(b"fixture source\n")
            reference = root / "reference.csv"
            reference.write_text(
                "Project ID,Record ID,Title,Datasets Used\n"
                "2020/001,2020/001,Synthetic public title,Public data\n",
                encoding="utf-8",
            )
            metadata = root / "metadata.json"
            metadata.write_text(
                '{"n_projects": 1, "record_id_whitespace_normalisation": {"status": "applied_before_registration"}}',
                encoding="utf-8",
            )
            before = metadata.read_bytes()
            cleaned = pd.DataFrame([{
                "Project ID": "2020/001",
                "Record ID": "2020/001",
                "Title": "Synthetic public title",
                "Datasets Used": "Public data",
            }])
            stats = {
                "raw_loaded": 1, "dropped_no_date_or_title": 0,
                "dropped_non_dea": 0, "rows_after_dea_filter": 1,
                "duplicate_tier1_rows_removed": 0,
                "duplicate_tier2_rows_removed": 0,
                "duplicate_ruling_rows_removed": 0,
            }
            argv = [
                "--repository-root", str(root),
                "--reference-csv", str(reference),
                "--cleaned-output", str(root / "cleaned.csv"),
                "--integrity-report", str(root / "integrity.json"),
                "--normalisation-audit", str(root / "audit.csv"),
                "--migration-log", str(root / "migration.json"),
                "--metadata", str(metadata), str(metadata),
                "--expected-mappings", "0", "--expected-cleaned-rows", "1",
                "--expected-project-ids", "1",
                "--expected-duplicate-project-groups", "0", "--check",
            ]
            with patch(
                "analysis.register_cleaning.load_clean_register",
                return_value=(cleaned, stats, "source.csv"),
            ):
                self.assertEqual(migration.main(argv), 0)
            self.assertEqual(metadata.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
