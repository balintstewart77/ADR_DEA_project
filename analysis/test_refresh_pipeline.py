import json
import hashlib
import difflib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from analysis.refresh_pipeline import (
    build_ingest_revision_comparison,
    build_nominal_release_comparison,
    build_raw_register_diff,
    build_register_diff,
    diff_markdown,
    load_cleaned_snapshot,
    review_required_markdown,
    run_gates,
)
import analysis.refresh_pipeline as refresh_pipeline
from analysis.register_manifest import load_manifest
from analysis.register_cleaning import clean_register_dataframe
from analysis.derive_register_properties import (
    build_indexes,
    derive_properties,
    load_reference,
    parse_register_entities,
)
from scrape.fetch_register import xlsx_to_dataframe
from dashboard.config import _DEFAULT_RELEASE_POINTERS, _load_release_pointers


def _register(rows: list[dict]) -> pd.DataFrame:
    base = {
        "Record ID": "",
        "Title": "",
        "Datasets Used": "",
        "Researchers": "",
        "Secure Research Service": "",
    }
    return pd.DataFrame([{**base, **row} for row in rows])


class BuildRegisterDiffTest(unittest.TestCase):
    def test_added_removed_and_changed_projects(self):
        old = _register([
            {"Record ID": "2024/001", "Title": "Kept unchanged"},
            {"Record ID": "2024/002", "Title": "Gets retitled"},
            {"Record ID": "2024/003", "Title": "Gets removed"},
        ])
        new = _register([
            {"Record ID": "2024/001", "Title": "Kept unchanged"},
            {"Record ID": "2024/002", "Title": "Was retitled"},
            {"Record ID": "2026/001", "Title": "Brand new"},
        ])

        diff = build_register_diff(old, new)

        self.assertEqual([e["record_id"] for e in diff["added"]], ["2026/001"])
        self.assertEqual([e["record_id"] for e in diff["removed"]], ["2024/003"])
        self.assertEqual(
            [(e["record_id"], e["fields"]) for e in diff["changed"]],
            [("2024/002", ["Title"])],
        )
        self.assertEqual(diff["old_rows"], 3)
        self.assertEqual(diff["new_rows"], 3)

    def test_whitespace_and_case_changes_are_not_content_changes(self):
        old = _register([
            {"Record ID": "2024/001", "Title": "A  Study of\nWages",
             "Datasets Used": "ASHE"},
        ])
        new = _register([
            {"Record ID": "2024/001", "Title": "a study of wages",
             "Datasets Used": "ASHE"},
        ])
        diff = build_register_diff(old, new)
        self.assertEqual(diff["changed"], [])

    def test_changed_reports_each_differing_field(self):
        old = _register([
            {"Record ID": "2024/001", "Title": "Same title",
             "Datasets Used": "ASHE", "Researchers": "A. Smith"},
        ])
        new = _register([
            {"Record ID": "2024/001", "Title": "Same title",
             "Datasets Used": "ASHE; LEO", "Researchers": "B. Jones"},
        ])
        diff = build_register_diff(old, new)
        self.assertEqual(len(diff["changed"]), 1)
        self.assertEqual(diff["changed"][0]["fields"], ["Datasets Used", "Researchers"])

    def test_diff_markdown_lists_each_section(self):
        old = _register([{"Record ID": "2024/003", "Title": "Gets removed"}])
        new = _register([{"Record ID": "2026/001", "Title": "Brand new"}])
        text = diff_markdown(build_register_diff(old, new), "20260101", "20260201")
        self.assertIn("# Register diff: 20260101 -> 20260201", text)
        self.assertIn("- `2026/001` Brand new", text)
        self.assertIn("- `2024/003` Gets removed", text)


class VerifiedRepublicationComparisonTest(unittest.TestCase):
    ORIGINAL = "abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d"
    REVISED = "918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd"

    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.ingest = build_ingest_revision_comparison(cls.manifest)
        cls.nominal = build_nominal_release_comparison(cls.manifest)

    def test_previous_ingest_uses_preceding_hash_not_nominal_date(self):
        self.assertEqual(self.ingest["baseline"]["canonical_csv_sha256"], self.ORIGINAL)
        self.assertEqual(self.ingest["target"]["canonical_csv_sha256"], self.REVISED)
        self.assertEqual(
            self.ingest["baseline"]["nominal_source_date"],
            self.ingest["target"]["nominal_source_date"],
        )

    def test_raw_revision_is_zero_zero_one_researchers(self):
        diff = self.ingest["raw_diff"]
        self.assertEqual((len(diff["added"]), len(diff["removed"]), len(diff["changed"])), (0, 0, 1))
        self.assertEqual(diff["changed"], [{"project_id": "2023/126", "fields": ["Researchers"]}])

    def test_cleaned_revision_has_no_analytical_change(self):
        diff = self.ingest["cleaned_diff"]
        self.assertEqual((len(diff["added"]), len(diff["removed"]), len(diff["changed"])), (0, 0, 0))
        self.assertEqual(self.ingest["analytical_impact"], "none")

    def test_nominal_release_comparison_remains_separate_march_to_june(self):
        self.assertEqual(self.nominal["baseline"]["nominal_source_date"], "2026-03-25")
        self.assertEqual(self.nominal["target"]["nominal_source_date"], "2026-06-01")
        self.assertNotEqual(
            self.nominal["baseline"]["snapshot_id"], self.ingest["baseline"]["snapshot_id"]
        )
        diff = self.nominal["cleaned_diff"]
        self.assertEqual((len(diff["added"]), len(diff["removed"]), len(diff["changed"])), (38, 1, 1))

    def test_original_and_revised_cleaned_outputs_are_identical_and_exclude_target(self):
        original = load_cleaned_snapshot(self.ORIGINAL)
        revised = load_cleaned_snapshot(self.REVISED)
        pd.testing.assert_frame_equal(original, revised, check_exact=True)
        self.assertEqual(len(original), 1308)
        self.assertNotIn("2023/126", set(original["Project ID"].astype(str)))

    def test_workbook_reclean_and_deterministic_serializations_are_byte_identical(self):
        snapshots = {
            item["canonical_csv_sha256"]: item
            for item in self.manifest["content_snapshots"]
        }
        root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        cleaned = []
        with tempfile.TemporaryDirectory() as tmp:
            for label, csv_hash in (("original", self.ORIGINAL), ("revised", self.REVISED)):
                snapshot = snapshots[csv_hash]
                xlsx_path = os.path.join(
                    root, "data", *snapshot["raw_xlsx_path"].split("/")
                )
                raw = xlsx_to_dataframe(open(xlsx_path, "rb").read())
                frame, _stats = clean_register_dataframe(
                    raw,
                    output_dir=os.path.join(tmp, label),
                    include_quarter_date=True,
                    verbose=False,
                )
                cleaned.append(frame)
        clean_bytes = [
            frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
            for frame in cleaned
        ]
        self.assertEqual(clean_bytes[0], clean_bytes[1])
        self.assertEqual(
            hashlib.sha256(clean_bytes[0]).hexdigest(),
            "6b8d3c5f12e1bbe957fecbada4885c450f4c3ab41d1bd1ec2fa67170494abc5f",
        )

        indexes = build_indexes(load_reference())
        properties = []
        for frame in cleaned:
            datasets, institutions = parse_register_entities(frame)
            properties.append(derive_properties(frame, datasets, institutions, indexes))
        property_bytes = [
            frame.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")
            for frame in properties
        ]
        self.assertEqual(property_bytes[0], property_bytes[1])
        self.assertEqual(
            hashlib.sha256(property_bytes[0]).hexdigest(),
            "318bc4409a7d41c9c96b6d364e0e78b9c340165c1a0244f6243faf801565a43f",
        )

    def test_csv_physical_diff_is_one_deleted_two_added_without_encoding_churn(self):
        root = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
        original = subprocess.check_output(
            ["git", "show", "HEAD:data/dea_accredited_projects_20260601.csv"],
            cwd=root,
        )
        revised_path = os.path.join(
            root, "data", "register_snapshots",
            "33c8ba2abd2085a28b2e5ca5ba2913398c6edb96f59f31331e5c125c96661014",
            "canonical.csv",
        )
        revised = open(revised_path, "rb").read().replace(b"\r\n", b"\n")
        self.assertTrue(original.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(revised.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", original)
        self.assertNotIn(b"\r\n", revised)
        changes = list(difflib.ndiff(
            original.decode("utf-8-sig").splitlines(),
            revised.decode("utf-8-sig").splitlines(),
        ))
        self.assertEqual(sum(line.startswith("- ") for line in changes), 1)
        self.assertEqual(sum(line.startswith("+ ") for line in changes), 2)


class ReviewRequiredMarkdownTest(unittest.TestCase):
    def test_lists_unmatched_names_by_mention_count(self):
        coverage = {
            "dataset_mentions_matched": 10,
            "dataset_mentions_total": 12,
            "organisation_mentions_matched": 5,
            "organisation_mentions_total": 6,
            "dataset_unmatched_counts": {"Mystery Dataset": 2},
            "organisation_unmatched_counts": {"Anna Freud Centre": 1},
        }
        text = review_required_markdown(coverage)
        self.assertIn("- Dataset mentions matched: 10/12", text)
        self.assertIn("- Mystery Dataset (2 mentions)", text)
        self.assertIn("- Anna Freud Centre (1 mention)", text)

    def test_known_unclassifiable_residuals_are_excluded_from_action_list(self):
        coverage = {
            "dataset_mentions_matched": 12,
            "dataset_mentions_total": 12,
            "organisation_mentions_matched": 4,
            "organisation_mentions_total": 6,
            "dataset_unmatched_counts": {},
            "organisation_unmatched_counts": {
                "Calver Pang": 1,
                "Genuinely New Org": 1,
            },
        }
        text = review_required_markdown(coverage, {"Calver Pang", "OREC"})
        self.assertIn("- Known residuals (adjudicated unclassifiable, no action): 1", text)
        self.assertIn("- Genuinely New Org (1 mention)", text)
        self.assertNotIn("- Calver Pang", text)

    def test_empty_queues_render_none(self):
        coverage = {
            "dataset_mentions_matched": 12,
            "dataset_mentions_total": 12,
            "organisation_mentions_matched": 6,
            "organisation_mentions_total": 6,
            "dataset_unmatched_counts": {},
            "organisation_unmatched_counts": {},
        }
        text = review_required_markdown(coverage)
        self.assertEqual(text.count("- (none)"), 2)


class RunGatesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def _write_ids_csv(self, name: str, record_ids: list[str]) -> str:
        path = os.path.join(self.tmp, name)
        pd.DataFrame({"Record ID": record_ids}).to_csv(
            path, index=False, encoding="utf-8-sig"
        )
        return path

    def test_passes_when_record_id_sets_match(self):
        register = _register([
            {"Record ID": "2024/001"}, {"Record ID": "2024/002"},
        ])
        properties = self._write_ids_csv("props.csv", ["2024/002", "2024/001"])
        classifications = self._write_ids_csv("class.csv", ["2024/001", "2024/002"])
        self.assertEqual(run_gates(register, properties, classifications), [])

    def test_flags_properties_mismatch(self):
        register = _register([
            {"Record ID": "2024/001"}, {"Record ID": "2024/002"},
        ])
        properties = self._write_ids_csv("props.csv", ["2024/001", "2024/999"])
        problems = run_gates(register, properties)
        self.assertEqual(len(problems), 1)
        self.assertIn("register_properties", problems[0])
        self.assertIn("2024/002", problems[0])
        self.assertIn("2024/999", problems[0])

    def test_flags_missing_classifications(self):
        register = _register([
            {"Record ID": "2024/001"}, {"Record ID": "2024/002"},
        ])
        properties = self._write_ids_csv("props.csv", ["2024/001", "2024/002"])
        classifications = self._write_ids_csv("class.csv", ["2024/001"])
        problems = run_gates(register, properties, classifications)
        self.assertEqual(len(problems), 1)
        self.assertIn("layer_classifications is missing 1", problems[0])

    def test_classifications_not_checked_when_omitted(self):
        register = _register([{"Record ID": "2024/001"}])
        properties = self._write_ids_csv("props.csv", ["2024/001"])
        self.assertEqual(run_gates(register, properties), [])


class ReleasePointersTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = self._tmp.name

    def _write_pointers(self, payload) -> str:
        path = os.path.join(self.tmp, "release_pointers.json")
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f)
        return path

    def test_valid_file_overrides_defaults(self):
        path = self._write_pointers({
            "classification_dir": "analysis/outputs_classified_20260601",
        })
        pointers = _load_release_pointers(path)
        self.assertEqual(
            pointers["classification_dir"], "analysis/outputs_classified_20260601"
        )
        self.assertEqual(
            pointers["register_properties_csv"],
            _DEFAULT_RELEASE_POINTERS["register_properties_csv"],
        )

    def test_missing_file_falls_back_to_defaults(self):
        missing = os.path.join(self.tmp, "does_not_exist.json")
        self.assertEqual(_load_release_pointers(missing), _DEFAULT_RELEASE_POINTERS)

    def test_invalid_json_falls_back_to_defaults(self):
        path = self._write_pointers("{not json")
        self.assertEqual(_load_release_pointers(path), _DEFAULT_RELEASE_POINTERS)

    def test_blank_or_non_string_values_are_ignored(self):
        path = self._write_pointers({
            "classification_dir": "   ",
            "register_properties_csv": 42,
        })
        self.assertEqual(_load_release_pointers(path), _DEFAULT_RELEASE_POINTERS)

    def test_committed_pointer_targets_exist(self):
        project_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        committed = os.path.join(project_root, "data", "release_pointers.json")
        pointers = _load_release_pointers(committed)
        classification_dir = os.path.join(
            project_root, *pointers["classification_dir"].split("/")
        )
        properties_csv = os.path.join(
            project_root, *pointers["register_properties_csv"].split("/")
        )
        self.assertTrue(os.path.isdir(classification_dir), classification_dir)
        self.assertTrue(
            os.path.isfile(
                os.path.join(classification_dir, "layer_classifications.csv")
            )
        )
        self.assertTrue(os.path.isfile(properties_csv), properties_csv)

    def test_committed_classification_release_matches_classifier_defaults(self):
        from analysis.llm_theme_analysis_v3 import MODEL, PROMPT_VERSION

        project_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        committed = os.path.join(project_root, "data", "release_pointers.json")
        pointers = _load_release_pointers(committed)
        classification_dir = os.path.join(
            project_root, *pointers["classification_dir"].split("/")
        )
        metadata_path = os.path.join(classification_dir, "run_metadata.json")
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.assertEqual(metadata["model"], MODEL)
        self.assertEqual(metadata["prompt_version"], PROMPT_VERSION)
        self.assertEqual(metadata["taxonomy_version"], PROMPT_VERSION)


class UnchangedRefreshControlFlowTest(unittest.TestCase):
    def test_unchanged_noop_exits_before_reports_even_when_forced(self):
        manifest = load_manifest()
        snapshot = manifest["pointers"]["current_latest_revision"]["snapshot_id"]
        result = {
            "status": "no-change",
            "outcome": "unchanged_noop",
            "snapshot_id": snapshot,
        }
        with tempfile.TemporaryDirectory() as tmp, patch(
            "fetch_register.run_fetch", return_value=result
        ), patch.object(
            refresh_pipeline, "REFRESH_DIR", Path(tmp) / "reports"
        ), patch.object(
            refresh_pipeline, "build_ingest_revision_comparison"
        ) as ingest, patch.object(
            refresh_pipeline, "build_nominal_release_comparison"
        ) as nominal, patch.object(
            refresh_pipeline, "_emit_workflow_outcome"
        ) as emit, patch(
            "sys.argv", ["refresh_pipeline", "--force"]
        ):
            self.assertEqual(refresh_pipeline.main(), 0)
            ingest.assert_not_called()
            nominal.assert_not_called()
            emit.assert_called_once_with("unchanged_noop")
            self.assertFalse((Path(tmp) / "reports").exists())

    def test_workflow_skips_version_branch_commit_and_pr_step_for_noop(self):
        workflow = Path(".github/workflows/register-refresh.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("id: refresh", workflow)
        guard = "if: steps.refresh.outputs.outcome != 'unchanged_noop'"
        self.assertEqual(workflow.count(guard), 2)
        self.assertIn("uses: peter-evans/create-pull-request@v6", workflow)


if __name__ == "__main__":
    unittest.main()
