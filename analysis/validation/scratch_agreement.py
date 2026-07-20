"""Reusable three-coder agreement orchestration for scratch classifications.

This module assembles the small, tested metric primitives in this package.  It
contains no file paths, model ratings, sampling behavior, or release logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from statistics import mean, median
from typing import Iterable, Mapping

from .alpha import AlphaResult, krippendorff_alpha
from .diagnostics import majority_diagnostic_rating, majority_supported_labels
from .metrics import exact_set_equality, jaccard_similarity, masi_distance, nominal_distance


DEFAULT_CODERS = ("C01", "C02", "C03")
DEFAULT_PAIRS = (("C01", "C02"), ("C01", "C03"), ("C02", "C03"))
SET_PATTERNS = frozenset({"unanimous", "two_vs_one", "all_sets_distinct"})
DIFFERENCE_PATTERNS = frozenset({
    "matches_majority_supported_set",
    "extra_only",
    "missing_only",
    "mixed_extra_and_missing",
    "no_labelwise_majority_reference",
})


@dataclass(frozen=True)
class ScratchSetRating:
    record_id: str
    coder_id: str
    labels: frozenset[str]


@dataclass(frozen=True)
class ScratchSetRecord:
    record_id: str
    coder_sets: Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class PairwiseSetResult:
    left_coder: str
    right_coder: str
    exact: bool
    jaccard: Fraction


@dataclass(frozen=True)
class MajorityDifference:
    extra_labels: frozenset[str]
    missing_labels: frozenset[str]
    classification: str


@dataclass(frozen=True)
class SetRecordAgreement:
    record_id: str
    pattern: str
    pairwise: tuple[PairwiseSetResult, ...]
    majority_supported: frozenset[str]
    majority_differences: Mapping[str, MajorityDifference]


@dataclass(frozen=True)
class PairwiseSummary:
    left_coder: str
    right_coder: str
    denominator: int
    exact_count: int
    exact_proportion: float
    mean_jaccard: float
    median_jaccard: float
    minimum_jaccard: float
    maximum_jaccard: float


class ScratchAgreementError(ValueError):
    """Raised when a supposedly complete scratch-coder matrix is not complete."""


def complete_case_three_coder_matrix(
    ratings: Iterable[ScratchSetRating],
    *,
    expected_coders: tuple[str, str, str] = DEFAULT_CODERS,
) -> tuple[ScratchSetRecord, ...]:
    """Build one record per complete three-coder unit and reject ambiguity."""

    if len(set(expected_coders)) != 3:
        raise ScratchAgreementError("Exactly three distinct expected coders are required")
    grouped: dict[str, dict[str, frozenset[str]]] = {}
    for rating in ratings:
        if not rating.record_id or not rating.coder_id:
            raise ScratchAgreementError("Record and coder IDs must be non-empty")
        if rating.coder_id not in expected_coders:
            raise ScratchAgreementError(f"Unexpected coder: {rating.coder_id}")
        coder_sets = grouped.setdefault(rating.record_id, {})
        if rating.coder_id in coder_sets:
            raise ScratchAgreementError(
                f"Duplicate coder-record rating: {rating.coder_id}/{rating.record_id}"
            )
        coder_sets[rating.coder_id] = frozenset(rating.labels)

    records: list[ScratchSetRecord] = []
    expected = set(expected_coders)
    for record_id in sorted(grouped):
        observed = set(grouped[record_id])
        if observed != expected:
            missing = sorted(expected - observed)
            extra = sorted(observed - expected)
            raise ScratchAgreementError(
                f"Incomplete coder matrix for {record_id}; missing={missing}, extra={extra}"
            )
        records.append(ScratchSetRecord(record_id, dict(grouped[record_id])))
    return tuple(records)


def complete_set_pattern(coder_sets: Iterable[frozenset[str]]) -> str:
    """Classify equality of three complete sets without implying label majorities."""

    values = tuple(frozenset(value) for value in coder_sets)
    if len(values) != 3:
        raise ScratchAgreementError("Set-pattern classification requires three sets")
    ab = exact_set_equality(values[0], values[1])
    ac = exact_set_equality(values[0], values[2])
    bc = exact_set_equality(values[1], values[2])
    if ab and ac:
        return "unanimous"
    if ab or ac or bc:
        return "two_vs_one"
    return "all_sets_distinct"


def pairwise_set_results(
    coder_sets: Mapping[str, frozenset[str]],
    *,
    coder_pairs: tuple[tuple[str, str], ...] = DEFAULT_PAIRS,
) -> tuple[PairwiseSetResult, ...]:
    results: list[PairwiseSetResult] = []
    for left, right in coder_pairs:
        try:
            left_set, right_set = coder_sets[left], coder_sets[right]
        except KeyError as exc:
            raise ScratchAgreementError(f"Missing coder set for pair {left}-{right}") from exc
        results.append(PairwiseSetResult(
            left,
            right,
            exact_set_equality(left_set, right_set),
            jaccard_similarity(left_set, right_set),
        ))
    return tuple(results)


def majority_relative_difference(
    coder_set: frozenset[str], majority_set: frozenset[str]
) -> MajorityDifference:
    extra = frozenset(coder_set - majority_set)
    missing = frozenset(majority_set - coder_set)
    if not majority_set:
        classification = "no_labelwise_majority_reference"
    elif not extra and not missing:
        classification = "matches_majority_supported_set"
    elif extra and not missing:
        classification = "extra_only"
    elif missing and not extra:
        classification = "missing_only"
    else:
        classification = "mixed_extra_and_missing"
    return MajorityDifference(extra, missing, classification)


def analyse_set_record(
    record: ScratchSetRecord,
    *,
    expected_coders: tuple[str, str, str] = DEFAULT_CODERS,
) -> SetRecordAgreement:
    values = tuple(record.coder_sets[coder] for coder in expected_coders)
    majority = majority_supported_labels(values)
    return SetRecordAgreement(
        record_id=record.record_id,
        pattern=complete_set_pattern(values),
        pairwise=pairwise_set_results(record.coder_sets),
        majority_supported=majority,
        majority_differences={
            coder: majority_relative_difference(record.coder_sets[coder], majority)
            for coder in expected_coders
        },
    )


def summarise_pairwise(
    records: Iterable[ScratchSetRecord],
    *,
    coder_pairs: tuple[tuple[str, str], ...] = DEFAULT_PAIRS,
) -> tuple[PairwiseSummary, ...]:
    values = tuple(records)
    if not values:
        raise ScratchAgreementError("Pairwise summaries require at least one record")
    summaries: list[PairwiseSummary] = []
    for left, right in coder_pairs:
        per_record = tuple(
            PairwiseSetResult(
                left,
                right,
                exact_set_equality(record.coder_sets[left], record.coder_sets[right]),
                jaccard_similarity(record.coder_sets[left], record.coder_sets[right]),
            )
            for record in values
        )
        jaccards = tuple(float(item.jaccard) for item in per_record)
        exact_count = sum(item.exact for item in per_record)
        summaries.append(PairwiseSummary(
            left_coder=left,
            right_coder=right,
            denominator=len(per_record),
            exact_count=exact_count,
            exact_proportion=exact_count / len(per_record),
            mean_jaccard=mean(jaccards),
            median_jaccard=median(jaccards),
            minimum_jaccard=min(jaccards),
            maximum_jaccard=max(jaccards),
        ))
    return tuple(summaries)


def three_rater_masi_alpha(
    records: Iterable[ScratchSetRecord],
    *,
    expected_coders: tuple[str, str, str] = DEFAULT_CODERS,
) -> AlphaResult:
    return krippendorff_alpha(
        (
            tuple(record.coder_sets[coder] for coder in expected_coders)
            for record in records
        ),
        masi_distance,
    )


def three_rater_nominal_alpha(
    records: Iterable[Mapping[str, int | str | None]],
    *,
    expected_coders: tuple[str, str, str] = DEFAULT_CODERS,
) -> AlphaResult:
    return krippendorff_alpha(
        (tuple(record.get(coder) for coder in expected_coders) for record in records),
        nominal_distance,
    )


def categorical_majority(values: Iterable[str]) -> str:
    """Reuse the exact two-of-three categorical majority/split rule."""

    return majority_diagnostic_rating(values)
