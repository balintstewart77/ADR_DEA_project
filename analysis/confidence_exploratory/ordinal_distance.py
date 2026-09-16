"""Local ordinal distance; all alpha and bootstrap calculations remain shared."""
from collections import Counter
from fractions import Fraction

from analysis.validation.alpha import krippendorff_alpha
from analysis.validation.bootstrap import StatisticValue


def ordinal_distance(units, categories=(1, 2, 3)):
    """Return squared disagreements from this call's pairable-value counts.

    alpha.py:38-42 excludes units with fewer than two non-None ratings.
    alpha.py:50,58 consumes float(distance(...)) without another square.
    Fraction constructs exact distances; float conversion matches that contract.
    Precomputing this small table avoids repeating exact arithmetic per pair.
    """
    counts = Counter()
    for unit in units:
        pairable = tuple(v for v in unit if v is not None)
        if len(pairable) >= 2:
            counts.update(pairable)
    if set(counts) - set(categories):
        raise ValueError("Unexpected ordinal category")
    matrix = {}
    for i, left in enumerate(categories):
        for j, right in enumerate(categories):
            low, high = sorted((i, j))
            span = sum(counts[v] for v in categories[low:high + 1])
            squared = Fraction(0) if i == j else (Fraction(span) - Fraction(counts[left] + counts[right], 2)) ** 2
            matrix[left, right] = float(squared)
    return lambda left, right: matrix[left, right]


def estimate(units, distance_factory=ordinal_distance):
    """Build this call's metric, then delegate unchanged to shared alpha."""
    units = tuple(tuple(unit) for unit in units)
    return krippendorff_alpha(units, distance_factory(units))


def bootstrap_evaluator(units, distance_factory=ordinal_distance):
    result = estimate(units, distance_factory)
    return {"alpha": StatisticValue(result.alpha, result.valid, result.undefined_reason)}
