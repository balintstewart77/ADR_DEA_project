"""Project-owner completion, route, and denominator primitives for v0.11."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping

ROUTES = frozenset({"sequence_based", "supplementary_purposive", "post_revision"})
VERDICTS = frozenset({"Fits", "Does not fit", "Unsure"})


@dataclass(frozen=True)
class OwnerReview:
    record_id: str
    respondent_id: str
    recruitment_route: str
    proposed_label_verdicts: Mapping[str, str | None]
    public_entry_sufficiency: str | None
    missing_label_report: bool | None = None
    taxonomy_fit: str | None = None


def complete_owner_review(review: OwnerReview) -> bool:
    """Protocol completion requires every proposed-label verdict and sufficiency."""

    if review.recruitment_route not in ROUTES:
        raise ValueError(f"Unknown owner recruitment route: {review.recruitment_route}")
    verdicts = tuple(review.proposed_label_verdicts.values())
    return bool(verdicts) and all(value in VERDICTS for value in verdicts) and bool(
        review.public_entry_sufficiency
    )


def owner_response_denominators(reviews: tuple[OwnerReview, ...]) -> dict[str, int]:
    """Return the distinct v0.11 owner-label and owner-record denominators."""

    completed_verdicts = sum(
        value in VERDICTS
        for review in reviews
        for value in review.proposed_label_verdicts.values()
    )
    complete_responses = tuple(review for review in reviews if complete_owner_review(review))
    return {
        "completed_owner_label_verdicts": completed_verdicts,
        "complete_owner_record_responses": len(complete_responses),
        "nonmissing_missing_label_responses": sum(
            review.missing_label_report is not None for review in reviews
        ),
        "nonmissing_sufficiency_responses_among_complete": sum(
            review.public_entry_sufficiency is not None for review in complete_responses
        ),
        "nonmissing_taxonomy_fit_responses_among_complete": sum(
            review.taxonomy_fit is not None for review in complete_responses
        ),
        "combined_unique_reviewed_records": len({
            review.record_id for review in complete_responses
        }),
    }


def record_label_response_patterns(
    reviews: tuple[OwnerReview, ...]
) -> Counter[str]:
    """Classify unique record-label results without constructing owner majorities."""

    grouped: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for review in reviews:
        for label, verdict in review.proposed_label_verdicts.items():
            if verdict in VERDICTS:
                grouped[(review.record_id, label)].append(verdict)
    patterns: Counter[str] = Counter()
    for verdicts in grouped.values():
        if len(verdicts) == 1:
            patterns["one_completed_response"] += 1
        elif len(set(verdicts)) == 1:
            patterns["multiple_concordant_responses"] += 1
        else:
            patterns["mixed_responses"] += 1
    return patterns


def sequence_evidence_status(reviews: tuple[OwnerReview, ...]) -> str:
    """Apply the 50-record target and 25-record minimum to sequence reviews only."""

    records = {
        review.record_id for review in reviews
        if review.recruitment_route == "sequence_based" and complete_owner_review(review)
    }
    if len(records) >= 50:
        return "target_met"
    if len(records) >= 25:
        return "minimum_viable"
    return "limited_exploratory_below_minimum"
