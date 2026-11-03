"""classify_batch falls back to a raw request only when the output, not the API, failed."""
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import ValidationError

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analysis import llm_theme_analysis_v3 as classifier  # noqa: E402

PROJECT_ID = "2026/001"
PROJECTS = [{"id": PROJECT_ID, "prompt_id": PROJECT_ID, "prompt_title": "T", "prompt_datasets": "D"}]


def _entry(rationale="Employment outcomes."):
    return {
        "project_id": PROJECT_ID,
        "substantive_domains": [classifier.DOMAINS[0]],
        "analytical_purpose": [classifier.PURPOSES[0]],
        "cross_cutting_tags": [],
        "rationale": rationale,
    }


def _schema_error() -> ValidationError:
    try:
        classifier.BatchLayerResult.model_validate_json('{"classifications": [{"project_id": 1}]}')
    except ValidationError as exc:
        return exc
    raise AssertionError("expected a validation error")


def _raw_response(text, stop_reason="end_turn"):
    # Thinking-on models put a thinking block before the answer.
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=None,
    )


class ClassifyBatchFallbackTest(unittest.TestCase):
    def test_api_errors_propagate_without_a_second_paid_request(self):
        client = MagicMock()
        client.messages.parse.side_effect = ConnectionError("network down")
        with self.assertRaises(ConnectionError):
            classifier.classify_batch(client, PROJECTS)
        client.messages.create.assert_not_called()

    def test_schema_failure_falls_back_and_reads_the_text_after_thinking(self):
        client = MagicMock()
        client.messages.parse.side_effect = _schema_error()
        client.messages.create.return_value = _raw_response(json.dumps({"classifications": [_entry()]}))
        result = classifier.classify_batch(client, PROJECTS)
        self.assertEqual(result[PROJECT_ID]["rationale"], "Employment outcomes.")
        self.assertEqual(classifier.LAST_CLASSIFY_API_PATH, "messages.create fallback")

    def test_refused_structured_request_is_not_repeated_raw(self):
        client = MagicMock()
        client.messages.parse.return_value = SimpleNamespace(
            parsed_output=None, stop_reason="refusal", usage=None,
        )
        with self.assertRaises(classifier.BatchClassificationError):
            classifier.classify_batch(client, PROJECTS)
        client.messages.create.assert_not_called()

    def test_truncated_fallback_output_is_rejected_not_salvaged(self):
        client = MagicMock()
        client.messages.parse.side_effect = _schema_error()
        client.messages.create.return_value = _raw_response(
            json.dumps({"classifications": [_entry()]}), stop_reason="max_tokens",
        )
        with self.assertRaises(classifier.BatchClassificationError):
            classifier.classify_batch(client, PROJECTS)

    def test_duplicate_entries_keep_the_first(self):
        parsed = classifier.BatchLayerResult(classifications=[_entry("first"), _entry("second")])
        client = MagicMock()
        client.messages.parse.return_value = SimpleNamespace(
            parsed_output=parsed, stop_reason="end_turn", usage=None,
        )
        result = classifier.classify_batch(client, PROJECTS)
        self.assertEqual(result[PROJECT_ID]["rationale"], "first")
        client.messages.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
