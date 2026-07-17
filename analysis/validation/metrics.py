"""Auditable set and nominal distance primitives from protocol Section 8."""

from __future__ import annotations

from fractions import Fraction
from typing import AbstractSet, Hashable


def exact_set_equality(left: AbstractSet[Hashable], right: AbstractSet[Hashable]) -> bool:
    return set(left) == set(right)


def jaccard_similarity(
    left: AbstractSet[Hashable], right: AbstractSet[Hashable]
) -> Fraction:
    """Return exact Jaccard similarity; two empty sets are defined as identical."""

    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    if not union:
        return Fraction(1, 1)
    return Fraction(len(left_set & right_set), len(union))


def masi_overlap_weight(
    left: AbstractSet[Hashable], right: AbstractSet[Hashable]
) -> Fraction:
    """Return the preregistered 1, 2/3, 1/3, or 0 overlap weight."""

    left_set, right_set = set(left), set(right)
    if left_set == right_set:
        return Fraction(1, 1)
    intersection = left_set & right_set
    if not intersection:
        return Fraction(0, 1)
    if left_set < right_set or right_set < left_set:
        return Fraction(2, 3)
    return Fraction(1, 3)


def masi_similarity(
    left: AbstractSet[Hashable], right: AbstractSet[Hashable]
) -> Fraction:
    return jaccard_similarity(left, right) * masi_overlap_weight(left, right)


def masi_distance(
    left: AbstractSet[Hashable], right: AbstractSet[Hashable]
) -> Fraction:
    return Fraction(1, 1) - masi_similarity(left, right)


def nominal_distance(left: Hashable, right: Hashable) -> int:
    return 0 if left == right else 1
