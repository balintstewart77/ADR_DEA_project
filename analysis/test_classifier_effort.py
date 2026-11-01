"""The classifier's reasoning effort is pinned, sent, and recorded.

Effort changes what the model produces, so it is an explicit request
parameter and part of the cache identity rather than an API default the run
happens to inherit.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analysis import llm_theme_analysis_v3 as classifier  # noqa: E402
from analysis.rebuild_llm_cache import write_cache  # noqa: E402

VALID_EFFORTS = ["low", "medium", "high", "xhigh", "max"]


class EffortIsPinnedTest(unittest.TestCase):
    def test_default_effort_is_an_explicit_valid_level(self):
        self.assertIn(classifier.EFFORT, VALID_EFFORTS)

    def test_output_config_carries_the_current_effort(self):
        self.assertEqual(classifier._output_config(), {"effort": classifier.EFFORT})


class EffortReachesTheApiTest(unittest.TestCase):
    def setUp(self):
        self.projects = [{
            "prompt_id": "2026/001",
            "prompt_title": "A study of employment outcomes",
            "prompt_datasets": "Labour Force Survey",
        }]

    def _client_returning_parsed(self):
        client = MagicMock()
        parsed = MagicMock()
        parsed.classifications = []
        response = MagicMock(parsed_output=parsed, usage=MagicMock())
        client.messages.parse.return_value = response
        return client

    def test_classification_request_sends_the_effort(self):
        client = self._client_returning_parsed()
        try:
            classifier.classify_batch(client, self.projects)
        except Exception:
            pass  # empty classifications fail validation; the request is what matters
        self.assertTrue(client.messages.parse.called, "no classification request was made")
        kwargs = client.messages.parse.call_args.kwargs
        self.assertEqual(kwargs.get("output_config"), {"effort": classifier.EFFORT})

    def test_no_sampling_parameters_are_sent(self):
        # temperature / top_p / top_k return 400 on current models.
        client = self._client_returning_parsed()
        try:
            classifier.classify_batch(client, self.projects)
        except Exception:
            pass
        kwargs = client.messages.parse.call_args.kwargs
        for forbidden in ("temperature", "top_p", "top_k"):
            self.assertNotIn(forbidden, kwargs)


class EffortIsPartOfCacheIdentityTest(unittest.TestCase):
    def _write_and_load(self, meta_effort, current_effort):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "llm_layer_cache.json")
            meta = {
                "cache_schema_version": classifier.CACHE_SCHEMA_VERSION,
                "prompt_version": classifier.PROMPT_VERSION,
                "model": classifier.MODEL,
            }
            if meta_effort is not None:
                meta["effort"] = meta_effort
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"__meta__": meta, "entries": {"k": {"v": 1}}}, handle)
            original = classifier.EFFORT
            classifier.EFFORT = current_effort
            try:
                return classifier.load_cache(path)
            finally:
                classifier.EFFORT = original

    def test_cache_written_at_a_different_effort_is_discarded(self):
        self.assertEqual(self._write_and_load("low", "high"), {})

    def test_cache_written_at_the_same_effort_is_reused(self):
        self.assertEqual(self._write_and_load("high", "high"), {"k": {"v": 1}})

    def test_cache_predating_the_setting_is_kept(self):
        # Those entries were produced at the API default, which EFFORT names;
        # discarding them would re-classify the whole register for nothing.
        self.assertEqual(self._write_and_load(None, classifier.EFFORT), {"k": {"v": 1}})

    def test_saved_cache_records_the_effort(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "llm_layer_cache.json")
            classifier.save_cache({"k": {"v": 1}}, path)
            with open(path, encoding="utf-8") as handle:
                meta = json.load(handle)["__meta__"]
        self.assertEqual(meta["effort"], classifier.EFFORT)

    def test_seeded_cache_records_the_effort(self):
        # The refresh pipeline seeds a cache before running the classifier; an
        # unrecorded effort there would read as "predates the setting".
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "llm_layer_cache.json")
            write_cache({}, path, model="claude-fable-5",
                        prompt_version=classifier.PROMPT_VERSION, effort="high")
            with open(path, encoding="utf-8") as handle:
                meta = json.load(handle)["__meta__"]
        self.assertEqual(meta["effort"], "high")


class EffortIsSettableFromTheCommandLineTest(unittest.TestCase):
    def test_classifier_rejects_an_unknown_effort(self):
        result = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, "analysis", "llm_theme_analysis_v3.py"),
             "--effort", "maximum"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_refresh_pipeline_exposes_the_same_levels(self):
        result = subprocess.run(
            [sys.executable, "-m", "analysis.refresh_pipeline", "--help"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        self.assertIn("--effort", result.stdout)
        for level in VALID_EFFORTS:
            self.assertIn(level, result.stdout)


if __name__ == "__main__":
    unittest.main()
