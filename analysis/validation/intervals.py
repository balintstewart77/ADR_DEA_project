"""Baseline-proportion uncertainty intervals."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


Z_975 = 1.959963984540054


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float
    confidence_level: float = 0.95
    interval_type: str = "Wilson score"


def wilson_interval(successes: int, n: int, *, z: float = Z_975) -> Interval:
    if not isinstance(successes, int) or not isinstance(n, int):
        raise TypeError("successes and n must be integers")
    if n <= 0:
        raise ValueError("Wilson interval requires n > 0")
    if successes < 0 or successes > n:
        raise ValueError("successes must be between zero and n")
    proportion = successes / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    centre = (proportion + z2 / (2.0 * n)) / denominator
    half_width = z * sqrt(proportion * (1.0 - proportion) / n + z2 / (4.0 * n * n)) / denominator
    lower = 0.0 if successes == 0 else max(0.0, centre - half_width)
    upper = 1.0 if successes == n else min(1.0, centre + half_width)
    return Interval(lower, upper)
