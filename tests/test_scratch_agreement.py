from fractions import Fraction

import pytest

from analysis.validation.scratch_agreement import (
    ScratchAgreementError,
    ScratchSetRating,
    ScratchSetRecord,
    analyse_set_record,
    categorical_majority,
    complete_case_three_coder_matrix,
    complete_set_pattern,
    majority_relative_difference,
    pairwise_set_results,
    three_rater_masi_alpha,
    three_rater_nominal_alpha,
)


def record(a, b, c):
    return ScratchSetRecord(
        "SYN-001", {"C01": frozenset(a), "C02": frozenset(b), "C03": frozenset(c)}
    )


def test_complete_matrix_rejects_missing_and_duplicate_coder_record_ratings():
    ratings = (
        ScratchSetRating("SYN-001", "C01", frozenset({"A"})),
        ScratchSetRating("SYN-001", "C02", frozenset({"A"})),
    )
    with pytest.raises(ScratchAgreementError, match="Incomplete coder matrix"):
        complete_case_three_coder_matrix(ratings)
    with pytest.raises(ScratchAgreementError, match="Duplicate coder-record"):
        complete_case_three_coder_matrix((ratings[0], ratings[0]))


@pytest.mark.parametrize(
    ("sets", "expected"),
    [
        (({"A"}, {"A"}, {"A"}), "unanimous"),
        (({"A"}, {"A"}, {"B"}), "two_vs_one"),
        (({"A"}, {"B"}, {"C"}), "all_sets_distinct"),
    ],
)
def test_complete_set_patterns(sets, expected):
    assert complete_set_pattern(tuple(frozenset(value) for value in sets)) == expected


def test_all_distinct_sets_can_have_nonempty_labelwise_majority():
    result = analyse_set_record(record({"A", "B"}, {"A", "C"}, {"B", "C"}))
    assert result.pattern == "all_sets_distinct"
    assert result.majority_supported == {"A", "B", "C"}


def test_all_distinct_sets_can_have_no_labelwise_majority():
    result = analyse_set_record(record({"A"}, {"B"}, {"C"}))
    assert result.pattern == "all_sets_distinct"
    assert result.majority_supported == frozenset()
    assert all(
        item.classification == "no_labelwise_majority_reference"
        for item in result.majority_differences.values()
    )


@pytest.mark.parametrize(
    ("coder", "majority", "expected"),
    [
        ({"A", "B"}, {"A", "B"}, "matches_majority_supported_set"),
        ({"A", "B", "C"}, {"A", "B"}, "extra_only"),
        ({"A"}, {"A", "B"}, "missing_only"),
        ({"A", "C"}, {"A", "B"}, "mixed_extra_and_missing"),
        ({"A"}, set(), "no_labelwise_majority_reference"),
    ],
)
def test_majority_relative_difference_patterns(coder, majority, expected):
    result = majority_relative_difference(frozenset(coder), frozenset(majority))
    assert result.classification == expected


def test_pairwise_exact_and_jaccard_are_wired_to_existing_primitives():
    results = pairwise_set_results(record({"A"}, {"A", "B"}, {"B"}).coder_sets)
    by_pair = {(item.left_coder, item.right_coder): item for item in results}
    assert not by_pair[("C01", "C02")].exact
    assert by_pair[("C01", "C02")].jaccard == Fraction(1, 2)
    assert by_pair[("C01", "C03")].jaccard == 0


def test_purpose_majority_can_exceed_two_labels_without_mutating_responses():
    result = analyse_set_record(record({"P1", "P2"}, {"P1", "P3"}, {"P2", "P3"}))
    assert len(result.majority_supported) == 3


def test_three_rater_masi_alpha_wiring():
    records = (
        record({"A"}, {"A"}, {"A"}),
        ScratchSetRecord(
            "SYN-002",
            {"C01": frozenset({"B"}), "C02": frozenset({"B"}), "C03": frozenset({"B"})},
        ),
    )
    result = three_rater_masi_alpha(records)
    assert result.valid
    assert result.alpha == pytest.approx(1.0)


def test_nominal_alpha_remains_undefined_without_variation():
    result = three_rater_nominal_alpha((
        {"C01": 0, "C02": 0, "C03": 0},
        {"C01": 0, "C02": 0, "C03": 0},
    ))
    assert not result.valid
    assert result.undefined_reason == "expected_disagreement_zero"


def test_categorical_three_way_split_is_not_resolved_by_order():
    assert categorical_majority(("Sufficient", "Partially sufficient", "Insufficient")) == (
        "No majority / split judgement"
    )
