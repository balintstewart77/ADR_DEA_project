from __future__ import annotations

import itertools

import pytest

from .generate import classify_relation, relation_row, semicolon_set_with_audit


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (frozenset(), frozenset(), "both_empty"),
        (frozenset(), frozenset({"a"}), "exactly_one_empty"),
        (frozenset({"a"}), frozenset({"a"}), "identical"),
        (frozenset({"a"}), frozenset({"a", "b"}), "containment"),
        (frozenset({"a", "b"}), frozenset({"b", "c"}), "overlap"),
        (frozenset({"a"}), frozenset({"b"}), "disjoint"),
    ],
)
def test_all_six_relations_and_symmetry(left, right, expected):
    assert classify_relation(left, right) == expected
    assert classify_relation(right, left) == expected


def test_missing_is_rejected_not_empty():
    with pytest.raises(ValueError, match="Missing observations"):
        classify_relation(None, frozenset())


def test_two_tag_universe_has_no_overlap_without_containment():
    tags = ("equity", "covid")
    sets = [frozenset(choice) for size in range(3) for choice in itertools.combinations(tags, size)]
    assert all(classify_relation(left, right) != "overlap" for left in sets for right in sets)


def test_semicolon_codec_preserves_labels_and_audits_duplicate_tokens():
    decoded, duplicate = semicolon_set_with_audit(
        "Alpha, internal punctuation; Beta / Gamma", record_id="REC00001", field="example"
    )
    assert decoded == frozenset({"Alpha, internal punctuation", "Beta / Gamma"})
    assert duplicate is None
    decoded, duplicate = semicolon_set_with_audit("Alpha; Alpha", record_id="REC00001", field="example")
    assert decoded == frozenset({"Alpha"})
    assert duplicate == {"record_key": "REC00001", "field": "example"}


def test_empty_model_field_is_explicit_empty_set():
    decoded, duplicate = semicolon_set_with_audit("", record_id="REC00001", field="example")
    assert decoded == frozenset()
    assert duplicate is None


def test_proportion_statuses_with_positive_denominators():
    counts = {
        "both_empty": 2,
        "exactly_one_empty": 1,
        "identical": 3,
        "containment": 2,
        "overlap": 1,
        "disjoint": 1,
    }
    containment = relation_row(
        population="baseline", dimension="Research Domains", family="human_human",
        relation="containment", eligible_records=10, counts=counts,
    )
    both_empty = relation_row(
        population="baseline", dimension="Research Domains", family="human_human",
        relation="both_empty", eligible_records=10, counts=counts,
    )
    assert containment["proportion_of_nonidentical_nonempty_pairs"] == "0.5"
    assert containment["proportion_of_all_nonidentical_pairs"] == "0.40000000000000002"
    assert both_empty["nonempty_proportion_status"] == "not_applicable"
    assert both_empty["all_proportion_status"] == "not_applicable"


def test_zero_denominator_statuses_never_emit_numeric_proportions():
    counts = {relation: 0 for relation in ("both_empty", "exactly_one_empty", "identical", "containment", "overlap", "disjoint")}
    row = relation_row(
        population="baseline", dimension="Research Domains", family="human_human",
        relation="containment", eligible_records=0, counts=counts,
    )
    assert row["proportion_of_nonidentical_nonempty_pairs"] == ""
    assert row["nonempty_proportion_status"] == "zero_denominator"
    assert row["proportion_of_all_nonidentical_pairs"] == ""
    assert row["all_proportion_status"] == "zero_denominator"
