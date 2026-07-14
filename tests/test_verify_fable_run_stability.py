from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from analysis import verify_fable_run_stability as verify


def classification(
    record_id: str,
    *,
    domains: tuple[str, ...] = ("Domain A",),
    purposes: tuple[str, ...] = ("Purpose A",),
    tags: tuple[str, ...] = (),
) -> verify.Classification:
    return verify.Classification(
        record_id=record_id,
        domains=frozenset(domains),
        purposes=frozenset(purposes),
        tags=frozenset(tags),
        fingerprint="same-fixed-input",
    )


class VerifyFableRunStabilityUnitTest(unittest.TestCase):
    def test_unordered_multilabel_equality(self) -> None:
        left = classification("r1", domains=("Domain A", "Domain B"))
        right = classification("r1", domains=("Domain B", "Domain A"))
        diagnostics, metrics = verify.compare_classifications(
            {"r1": left}, {"r1": right}, ["r1"]
        )
        self.assertTrue(diagnostics[0].domain_exact)
        self.assertEqual(metrics.domain_exact, 1)
        self.assertEqual(metrics.domain_jaccard, 1.0)

    def test_jaccard(self) -> None:
        self.assertEqual(verify.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)
        with self.assertRaises(verify.VerificationError):
            verify.jaccard(set(), set())

    def test_binary_tags_are_compared_independently(self) -> None:
        left = classification("r1", tags=(verify.COVID_TAG,))
        right = classification("r1", tags=(verify.EQUITY_TAG,))
        diagnostics, metrics = verify.compare_classifications(
            {"r1": left}, {"r1": right}, ["r1"]
        )
        row = diagnostics[0]
        self.assertNotEqual(row.covid_run1, row.covid_run2)
        self.assertNotEqual(row.equity_run1, row.equity_run2)
        self.assertFalse(row.joint_tag_match)
        self.assertEqual(metrics.covid_agreement, 0)
        self.assertEqual(metrics.equity_agreement, 0)

    def test_unknown_label_causes_failure(self) -> None:
        with self.assertRaisesRegex(verify.VerificationError, "Unknown domain"):
            verify.validate_labels(
                {"Invented label"},
                frozenset({"Domain A"}),
                record_id="r1",
                field="domain",
            )

    def test_missing_ids_cause_failure(self) -> None:
        with self.assertRaisesRegex(verify.VerificationError, "keys differ"):
            verify.determine_comparison_ids({"r1"}, {"r2"})
        with self.assertRaisesRegex(verify.VerificationError, "absent"):
            verify.determine_comparison_ids({"r1"}, {"r2"}, {"r3"})

    def test_target_value_comparison(self) -> None:
        metrics = verify.Metrics(
            n=201,
            domain_exact=191,
            domain_jaccard=0.9742951907131012,
            purpose_exact=185,
            purpose_jaccard=0.9353233830845771,
            covid_agreement=201,
            equity_agreement=197,
            joint_tag_agreement=197,
            all_component_agreement=171,
            invalid_or_failed=0,
            missing_run1_ids=(),
            missing_run2_ids=(),
        )
        verify.assert_target_metrics(metrics)
        with self.assertRaisesRegex(verify.VerificationError, "domain_exact"):
            verify.assert_target_metrics(replace(metrics, domain_exact=190))

    def test_whitespace_or_control_in_canonical_id_causes_failure(self) -> None:
        for record_id in ("r1 ", " r1", "r\t1", "r\n1", "r\r1", "r\x001", "r\u00a01"):
            with self.subTest(record_id=repr(record_id)):
                with self.assertRaisesRegex(verify.VerificationError, "canonical|Canonical"):
                    verify.validate_canonical_record_id(record_id)


class VerifyFableRunStabilityCheckModeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.run1 = self.root / "run1"
        self.run2 = self.root / "run2"
        self.production = self.root / "production"
        self.run1.mkdir()
        self.run2.mkdir()
        self.production.mkdir()
        self._write_taxonomy()
        self._write_run(self.run1, "run1-response")
        self._write_run(self.run2, "run2-response")
        self._write_sample()
        self._write_production()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_taxonomy(self) -> None:
        payload = {
            "metadata": {"dictionary_version": "1.0-rc2"},
            "categories": [
                {"label": "Domain A", "layer": "Layer A -- domain", "include_in_prompt": True},
                {"label": "Purpose A", "layer": "Layer C -- purpose", "include_in_prompt": True},
                {"label": verify.COVID_TAG, "layer": "Cross-cutting tag", "include_in_prompt": True},
                {"label": verify.EQUITY_TAG, "layer": "Cross-cutting tag", "include_in_prompt": True},
            ],
        }
        (self.root / "taxonomy.json").write_text(json.dumps(payload), encoding="utf-8")

    def _write_run(self, directory: Path, response_id: str) -> None:
        cache = {
            "__meta__": {
                "model": verify.EXPECTED_MODEL,
                "prompt_version": verify.EXPECTED_VERSION,
                "cache_schema_version": 6,
            },
            "entries": {
                "r1": {
                    "substantive_domains": ["Domain A"],
                    "analytical_purpose": ["Purpose A"],
                    "cross_cutting_tags": [],
                    "fingerprint": "same-fixed-input",
                }
            },
        }
        (directory / "llm_layer_cache.json").write_text(json.dumps(cache), encoding="utf-8")
        metadata = {
            "model": verify.EXPECTED_MODEL,
            "prompt_version": verify.EXPECTED_VERSION,
            "cache_schema_version": 6,
            "n_projects": 1,
            "sample_csv": "sample.csv",
            "created_at_utc": response_id,
            "usage_log": [{"response_id": response_id}],
        }
        (directory / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    def _write_sample(self) -> None:
        with (self.root / "sample.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Record ID"])
            writer.writeheader()
            writer.writerow({"Record ID": "r1"})

    def _write_production(self) -> None:
        path = self.production / "layer_classifications.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "Project ID",
                    "Title",
                    "Record ID",
                    "substantive_domains",
                    "analytical_purpose",
                    "cross_cutting_tags",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "Project ID": "p1",
                    "Title": "Public title",
                    "Record ID": "r1",
                    "substantive_domains": "Domain A",
                    "analytical_purpose": "Purpose A",
                    "cross_cutting_tags": "",
                }
            )
        metadata = {
            "model": verify.EXPECTED_MODEL,
            "prompt_version": verify.EXPECTED_VERSION,
            "taxonomy_version": verify.EXPECTED_VERSION,
            "seed_cache": "run1/llm_layer_cache.json",
            "seed_cache_entries": 1,
            "fresh_api_classifications": 0,
            "source_register": "synthetic public fixture",
        }
        (self.production / "run_metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

    def test_check_mode_writes_no_output(self) -> None:
        output = self.root / "must-not-exist"
        argv = [
            "--repository-root",
            str(self.root),
            "--taxonomy",
            "taxonomy.json",
            "--run1",
            "run1/llm_layer_cache.json",
            "--run2",
            "run2/llm_layer_cache.json",
            "--production-output",
            "production/layer_classifications.csv",
            "--output-dir",
            str(output),
            "--check",
        ]
        stdout = io.StringIO()
        with (
            patch.object(verify, "EXPECTED_PRODUCTION_ROWS", 1),
            patch.object(verify, "assert_target_metrics"),
            redirect_stdout(stdout),
        ):
            self.assertEqual(verify.main(argv), 0)
        self.assertFalse(output.exists())
        self.assertIn("no files written", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
