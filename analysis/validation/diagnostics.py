"""Labelwise majority and taxonomy-diagnostic denominator primitives."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


def human_supported(coder_sets: Iterable[frozenset[str]], label: str) -> bool:
    ratings = tuple(coder_sets)
    if len(ratings) != 3:
        raise ValueError("Human support requires exactly three scratch coders")
    return sum(label in labels for labels in ratings) >= 2


def majority_supported_labels(coder_sets: Iterable[frozenset[str]]) -> frozenset[str]:
    ratings = tuple(coder_sets)
    if len(ratings) != 3:
        raise ValueError("Labelwise aggregation requires exactly three scratch coders")
    counts = Counter(label for labels in ratings for label in labels)
    return frozenset(label for label, count in counts.items() if count >= 2)


def taxonomy_defect_eligible(taxonomy_fit: str) -> bool:
    """Cannot assess is evidence-limited and never enters defect denominators."""

    if taxonomy_fit not in {"Fit", "Partial Fit", "No Fit", "Cannot assess from register entry"}:
        raise ValueError(f"Unknown current-candidate taxonomy-fit value: {taxonomy_fit!r}")
    return taxonomy_fit in {"Partial Fit", "No Fit"}


def taxonomy_issue_denominator(taxonomy_fits: Iterable[str]) -> int:
    return sum(taxonomy_defect_eligible(value) for value in taxonomy_fits)


def support_band(positive_records: int) -> str:
    """Return the Section 8.6 random-baseline reporting band."""

    if not isinstance(positive_records, int) or positive_records < 0:
        raise ValueError("positive_records must be a non-negative integer")
    if positive_records < 10:
        return "fewer_than_10_descriptive_only"
    if positive_records < 30:
        return "10_to_29_low_support_caution"
    return "30_or_more_standard_reporting"


def macro_average_eligible(positive_records: int) -> bool:
    """Domains and purposes enter macro-averages at 10 baseline positives."""

    support_band(positive_records)
    return positive_records >= 10


def majority_diagnostic_rating(values: Iterable[str]) -> str:
    """Return an exact two-of-three category or the prespecified split label."""

    ratings = tuple(values)
    if len(ratings) != 3 or any(not value for value in ratings):
        raise ValueError("Diagnostic majority requires three non-empty ratings")
    counts = Counter(ratings)
    winner, count = counts.most_common(1)[0]
    return winner if count >= 2 else "No majority / split judgement"
