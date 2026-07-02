import json
import os
import tempfile
import unittest

import pandas as pd

from analysis.refresh_pipeline import (
    build_register_diff,
    diff_markdown,
    review_required_markdown,
    run_gates,
)
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


if __name__ == "__main__":
    unittest.main()
