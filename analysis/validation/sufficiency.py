"""Pre-adjudication register-sufficiency subset rules from Section 8.3."""

from __future__ import annotations

from collections.abc import Iterable


ALLOWED = frozenset({"Sufficient", "Partially sufficient", "Insufficient"})


def _ratings(values: Iterable[str]) -> tuple[str, str, str]:
    ratings = tuple(values)
    if len(ratings) != 3 or any(value not in ALLOWED for value in ratings):
        raise ValueError(f"Expected exactly three valid pre-adjudication ratings: {ratings!r}")
    return ratings  # type: ignore[return-value]


def broad_register_usable(values: Iterable[str]) -> bool:
    ratings = _ratings(values)
    return sum(value in {"Sufficient", "Partially sufficient"} for value in ratings) >= 2


def strict_register_sufficient(values: Iterable[str]) -> bool:
    ratings = _ratings(values)
    return sum(value == "Sufficient" for value in ratings) >= 2


def majority_insufficient(values: Iterable[str]) -> bool:
    ratings = _ratings(values)
    return sum(value == "Insufficient" for value in ratings) >= 2
