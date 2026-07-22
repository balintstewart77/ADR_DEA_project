import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import verify_redcap_candidate_0_7_freeze as freeze


class Candidate07FreezeVerifierTests(unittest.TestCase):
    def copy_live(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "live.csv"
        path.write_bytes(freeze.LIVE.read_bytes())
        return temporary, path

    def mutate(self, path: Path, variable: str, column: str, transform) -> None:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        row = next(item for item in rows if item["Variable / Field Name"] == variable)
        row[column] = transform(row[column])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def test_authoritative_files_have_exact_narrow_equivalence(self):
        result = freeze.verify_round_trip()
        self.assertEqual(result["raw_mismatch_count"], 65)
        self.assertEqual(result["accepted_counts"], freeze.EXPECTED_TRANSFORMATIONS)
        self.assertEqual(result["residual_mismatch_count"], 0)
        self.assertEqual(result["source_forms"], freeze.EXPECTED_FORMS)
        self.assertEqual(result["live_forms"], freeze.EXPECTED_FORMS)
        self.assertTrue(freeze.verify_archive_state()["passed"])

    def test_two_leading_spaces_are_not_accepted(self):
        temporary, path = self.copy_live()
        self.addCleanup(temporary.cleanup)
        self.mutate(path, "record_kind", "Field Annotation", lambda value: " " + value)
        result = freeze.verify_round_trip(live=path)
        self.assertGreater(result["residual_mismatch_count"], 0)

    def test_owner_wording_change_is_not_hidden_by_entity_decoding(self):
        temporary, path = self.copy_live()
        self.addCleanup(temporary.cleanup)
        self.mutate(path, "po_d01_label", "Field Label", lambda value: value + " Changed")
        result = freeze.verify_round_trip(live=path)
        self.assertGreater(result["residual_mismatch_count"], 0)

    def test_changed_markup_structure_is_not_accepted(self):
        temporary, path = self.copy_live()
        self.addCleanup(temporary.cleanup)
        self.mutate(path, "po_d01_label", "Field Label", lambda value: value.replace("<strong>", "<em>", 1))
        result = freeze.verify_round_trip(live=path)
        self.assertGreater(result["residual_mismatch_count"], 0)

    def test_second_section_header_omission_is_not_accepted(self):
        temporary, path = self.copy_live()
        self.addCleanup(temporary.cleanup)
        self.mutate(path, "cd_intro", "Section Header", lambda value: "")
        result = freeze.verify_round_trip(live=path)
        self.assertGreater(result["residual_mismatch_count"], 0)

    def test_report_records_both_comparison_levels_and_limits(self):
        result = freeze.verify_round_trip()
        report = freeze.render_report(result, freeze.verify_archive_state())
        self.assertIn("Raw mismatching cells: **65**", report)
        self.assertIn("Residual mismatches: **0**", report)
        self.assertIn("does not claim byte identity", report)
        self.assertIn("Single leading annotation space", report)
        self.assertIn("One-pass HTML character-entity decoding", report)

    def test_freeze_manifest_rows_are_hash_synchronised(self):
        manifest_path = freeze.ROOT / "preregistration/preregistration_artifact_manifest.csv"
        with manifest_path.open(encoding="utf-8", newline="") as handle:
            manifest = {row["artifact_id"]: row for row in csv.DictReader(handle)}
        required = {"RED-001", "RED-026", "RED-027", "RED-030", "RED-031", "RED-032", "RED-033", "RED-034", "RED-035", "RED-036", "RED-037"}
        self.assertTrue(required.issubset(manifest))
        for artifact_id in required:
            row = manifest[artifact_id]
            artifact = freeze.ROOT / row["current_path"]
            self.assertTrue(artifact.is_file(), artifact_id)
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), row["sha256"], artifact_id)
        self.assertEqual(manifest["RED-001"]["frozen"], "true")
        self.assertEqual(manifest["RED-036"]["frozen"], "true")
        self.assertEqual(manifest["RED-036"]["registered"], "false")
        self.assertEqual(manifest["RED-036"]["sha256"], freeze.SOURCE_SHA256)
        self.assertEqual(manifest["RED-026"]["sha256"], freeze.LIVE_SHA256)
        self.assertIn("zero residual mismatches", manifest["RED-033"]["notes"])


if __name__ == "__main__":
    unittest.main()
