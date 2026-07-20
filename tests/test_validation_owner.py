from analysis.validation.owner import (
    OwnerReview, complete_owner_review, owner_response_denominators,
    record_label_response_patterns, sequence_evidence_status,
)


def review(record, respondent, route="sequence_based", verdict="Fits", sufficiency="Sufficient"):
    return OwnerReview(
        record, respondent, route, {"Synthetic label": verdict}, sufficiency,
        missing_label_report=False, taxonomy_fit="Fit",
    )


def test_completion_requires_all_proposed_verdicts_and_sufficiency():
    assert complete_owner_review(review("SYN-001", "SYN-R1"))
    incomplete = OwnerReview(
        "SYN-001", "SYN-R1", "sequence_based", {"A": "Fits", "B": None}, "Sufficient"
    )
    assert not complete_owner_review(incomplete)


def test_owner_denominators_keep_response_and_unique_record_units_distinct():
    reviews = (
        review("SYN-001", "SYN-R1"),
        review("SYN-001", "SYN-R2", verdict="Does not fit"),
        review("SYN-002", "SYN-R3", route="supplementary_purposive"),
    )
    denominators = owner_response_denominators(reviews)
    assert denominators["completed_owner_label_verdicts"] == 3
    assert denominators["complete_owner_record_responses"] == 3
    assert denominators["combined_unique_reviewed_records"] == 2
    assert record_label_response_patterns(reviews)["mixed_responses"] == 1


def test_supplementary_reviews_do_not_count_toward_sequence_thresholds():
    sequence = tuple(review(f"SYN-{i:03}", f"SYN-R{i:03}") for i in range(25))
    supplementary = tuple(
        review(f"SYN-X{i:03}", f"SYN-XR{i:03}", route="supplementary_purposive")
        for i in range(30)
    )
    assert sequence_evidence_status(sequence + supplementary) == "minimum_viable"
