"""Transparent multi-rater Krippendorff alpha with supplied distance.

For each unit with m ratings, ordered pair disagreements are divided by m-1.
Their sum is divided by the total number of eligible ratings to obtain observed
disagreement.  Expected disagreement is the mean distance across all ordered
pairs drawn without replacement from the pooled rating marginals.  This is the
standard coincidence-matrix convention and permits unequal m after missing
ratings are removed. Repeated bootstrap units remain separate sequence entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable, Hashable, Iterable, Sequence, TypeVar


T = TypeVar("T", bound=Hashable)


@dataclass(frozen=True)
class AlphaResult:
    alpha: float | None
    observed_disagreement: float | None
    expected_disagreement: float | None
    number_of_units: int
    number_of_ratings: int
    valid: bool
    undefined_reason: str | None = None


def krippendorff_alpha(
    units: Iterable[Sequence[T | None]], distance: Callable[[T, T], float]
) -> AlphaResult:
    eligible_units: list[tuple[T, ...]] = []
    pooled: list[T] = []
    for unit in units:
        ratings = tuple(value for value in unit if value is not None)
        if len(ratings) >= 2:
            eligible_units.append(ratings)
            pooled.extend(ratings)
    n_ratings = len(pooled)
    if not eligible_units or n_ratings < 2:
        return AlphaResult(None, None, None, len(eligible_units), n_ratings, False, "fewer_than_two_eligible_ratings")

    observed_sum = 0.0
    for ratings in eligible_units:
        m = len(ratings)
        observed_sum += sum(
            float(distance(left, right))
            for i, left in enumerate(ratings)
            for j, right in enumerate(ratings)
            if i != j
        ) / (m - 1)
    observed = observed_sum / n_ratings

    expected_sum = sum(
        float(distance(left, right))
        for i, left in enumerate(pooled)
        for j, right in enumerate(pooled)
        if i != j
    )
    expected = expected_sum / (n_ratings * (n_ratings - 1))
    if not isfinite(observed) or not isfinite(expected):
        return AlphaResult(None, observed, expected, len(eligible_units), n_ratings, False, "non_finite_disagreement")
    if abs(expected) <= 1e-15:
        return AlphaResult(None, observed, expected, len(eligible_units), n_ratings, False, "expected_disagreement_zero")
    alpha = 1.0 - observed / expected
    return AlphaResult(alpha, observed, expected, len(eligible_units), n_ratings, True, None)
