"""classify_batch makes one request per call and checks stop_reason before validating.

A refused, truncated or malformed reply must never trigger a second paid request.
"""
import importlib
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from analysis import llm_theme_analysis_v3 as classifier  # noqa: E402

PROJECT_ID = "2026/001"
PROJECTS = [{"id": PROJECT_ID, "prompt_id": PROJECT_ID, "prompt_title": "T", "prompt_datasets": "D"}]


def _entry(rationale="Employment outcomes.", domain=None):
    return {
        "project_id": PROJECT_ID,
        "substantive_domains": [domain or classifier.DOMAINS[0]],
        "analytical_purpose": [classifier.PURPOSES[0]],
        "cross_cutting_tags": [],
        "rationale": rationale,
    }


def _reply(text, stop_reason="end_turn"):
    # Thinking-on models put a thinking block before the answer.
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=None,
    )


class ClassifyBatchTest(unittest.TestCase):
    def setUp(self):
        # The schema comes from the SDK, which the test environment lacks.
        patcher = patch.object(classifier, "_batch_output_format", return_value={"type": "json_schema"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = MagicMock()

    def _run(self, reply):
        self.client.messages.create.return_value = reply
        try:
            return classifier.classify_batch(self.client, PROJECTS)
        finally:
            self.client.messages.create.assert_called_once()

    def test_api_errors_propagate_after_one_request(self):
        self.client.messages.create.side_effect = ConnectionError("network down")
        with self.assertRaises(ConnectionError):
            classifier.classify_batch(self.client, PROJECTS)
        self.client.messages.create.assert_called_once()

    def test_valid_reply_after_a_thinking_block(self):
        result = self._run(_reply(json.dumps({"classifications": [_entry()]})))
        self.assertEqual(result[PROJECT_ID]["rationale"], "Employment outcomes.")

    def test_refusal_is_rejected_without_another_request(self):
        with self.assertRaisesRegex(classifier.BatchClassificationError, "stop_reason=refusal"):
            self._run(_reply("I can't help with that.", stop_reason="refusal"))

    def test_truncated_reply_is_rejected_without_another_request(self):
        complete = json.dumps({"classifications": [_entry()]})
        with self.assertRaisesRegex(classifier.BatchClassificationError, "stop_reason=max_tokens"):
            self._run(_reply(complete[: len(complete) // 2], stop_reason="max_tokens"))

    def test_near_miss_labels_are_normalised_in_the_same_reply(self):
        lowercased = _entry(domain=classifier.DOMAINS[0].lower())
        result = self._run(_reply(json.dumps({"classifications": [lowercased]})))
        self.assertEqual(result[PROJECT_ID]["substantive_domains"], [classifier.DOMAINS[0]])

    def test_unrecognised_labels_fall_back_to_unclear_as_before(self):
        # The existing normaliser drops labels it cannot match.
        result = self._run(_reply(json.dumps({"classifications": [_entry(domain="Not A Domain")]})))
        self.assertEqual(result[PROJECT_ID]["substantive_domains"], [classifier.UNCLEAR_DOMAIN_LABEL])

    def test_malformed_reply_fails_after_one_request(self):
        with self.assertRaises(classifier.BatchClassificationError):
            self._run(_reply("not json at all"))

    def test_duplicate_entries_keep_the_first(self):
        result = self._run(_reply(json.dumps({"classifications": [_entry("first"), _entry("second")]})))
        self.assertEqual(result[PROJECT_ID]["rationale"], "first")


def _sdk_client(replies, bodies):
    """A real Anthropic client whose HTTP transport returns canned replies."""
    anthropic = pytest.importorskip("anthropic")
    # 0.x is built on httpx, 1.x onwards on httpx2: use the SDK's own transport.
    httpx = importlib.import_module(anthropic.DefaultHttpxClient.__mro__[1].__module__.split(".")[0])

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=replies.pop(0))

    return anthropic.Anthropic(
        api_key="test", max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=httpx.MockTransport(handler)),
    )


def _message(text, stop_reason):
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": classifier.MODEL,
        "content": [{"type": "text", "text": text}], "stop_reason": stop_reason,
        "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def test_request_matches_what_messages_parse_sends():
    bodies = []
    valid = json.dumps({"classifications": [_entry()]})
    client = _sdk_client([_message(valid, "end_turn"), _message(valid, "end_turn")], bodies)
    classifier.classify_batch(client, PROJECTS)
    client.messages.parse(
        model=classifier.MODEL, max_tokens=classifier.MAX_TOKENS,
        messages=classifier._build_prompt_messages(PROJECTS),
        output_format=classifier.BatchLayerResult, output_config=classifier._output_config(),
    )
    assert bodies[0] == bodies[1]


@pytest.mark.parametrize("stop_reason, text", [
    ("refusal", "I can't help with that."),
    ("max_tokens", '{"classifications": [{"project_id": "2026/001", "substantive_dom'),
])
def test_real_sdk_stopped_early_reply_costs_one_request(stop_reason, text):
    bodies = []
    client = _sdk_client([_message(text, stop_reason)], bodies)
    with pytest.raises(classifier.BatchClassificationError, match=f"stop_reason={stop_reason}"):
        classifier.classify_batch(client, PROJECTS)
    assert len(bodies) == 1


if __name__ == "__main__":
    unittest.main()
