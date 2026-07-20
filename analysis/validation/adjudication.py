"""Source-masked adjudication and recurring-trigger primitives for v0.11."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, Sequence

ADJUDICATION_ISSUE_FAMILIES = (
    "Apparent model rule-application problem",
    "Apparent scratch-coder rule-application problem",
    "Evidence problem",
    "Taxonomy problem",
    "Project-knowledge gap",
    "Legitimate boundary case",
    "Data or instrument problem",
    "Unresolved",
)


@dataclass(frozen=True)
class AdjudicationCase:
    record_id: str
    sample_set: str
    production_labels: Mapping[str, frozenset[str]]
    majority_human_labels: Mapping[str, frozenset[str]] | None = None
    owner_problem_reported: bool = False
    data_or_instrument_problem: bool = False


@dataclass(frozen=True)
class MaskedLabelSet:
    display_id: str
    labels: frozenset[str]


@dataclass(frozen=True)
class MechanismReport:
    record_id: str
    reviewer_stream: str
    source_revealed_confirmation: bool = False


def adjudication_reasons(case: AdjudicationCase) -> frozenset[str]:
    reasons: set[str] = set()
    if case.majority_human_labels is not None and any(
        case.production_labels.get(dimension, frozenset()) != labels
        for dimension, labels in case.majority_human_labels.items()
    ):
        reasons.add("production_majority_disagreement")
    if case.owner_problem_reported:
        reasons.add("owner_reported_problem")
    if case.data_or_instrument_problem:
        reasons.add("data_or_instrument_flag")
    return frozenset(reasons)


def build_source_masked_stage1(
    source_label_sets: Mapping[str, frozenset[str]], *, seed: int
) -> tuple[MaskedLabelSet, ...]:
    """Deduplicate and randomise label sets without returning source identities."""

    unique = sorted(set(source_label_sets.values()), key=lambda value: tuple(sorted(value)))
    random.Random(seed).shuffle(unique)
    return tuple(
        MaskedLabelSet(f"set_{position}", labels)
        for position, labels in enumerate(unique, 1)
    )


def recurring_mechanism(
    reports: Sequence[MechanismReport], *, headline_material_single_case: bool = False
) -> bool:
    """Apply the two-record or independent-pre-reveal-stream recurrence rule."""

    if headline_material_single_case and reports:
        return True
    if len({report.record_id for report in reports}) >= 2:
        return True
    independent_streams = {
        report.reviewer_stream
        for report in reports
        if not report.source_revealed_confirmation
    }
    return len(independent_streams) >= 2
