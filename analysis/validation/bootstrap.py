"""Project-level bootstrap primitives with no top-up of invalid replicates."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import ceil, floor, isfinite
from random import Random
from typing import Callable, Generic, Mapping, Sequence, TypeVar


T = TypeVar("T")
SEED_BOOTSTRAP = 20260714
DEFAULT_ATTEMPTS = 2000


@dataclass(frozen=True)
class StatisticValue:
    value: float | None
    valid: bool
    reason: str | None = None


@dataclass(frozen=True)
class BootstrapStatistic:
    attempted: int
    valid: int
    invalid: int
    lower: float | None
    upper: float | None
    interval_reported: bool
    invalid_reasons: tuple[tuple[str, int], ...]
    valid_values: tuple[float, ...]


@dataclass(frozen=True)
class BootstrapResult:
    attempted_replicates: int
    seed: int
    statistics: Mapping[str, BootstrapStatistic]
    semantics: str = "attempted replicates, with no replacement or top-up of undefined replicates"


def percentile(values: Sequence[float], probability: float) -> float:
    """Type-7 linear percentile: rank=(n-1)*p.

    Protocol v0.14 Section 8.9 fixes Hyndman-Fan Type 7 interpolation. This is
    equivalent to NumPy/Pandas ``linear`` quantile interpolation.
    """

    if not values:
        raise ValueError("Cannot calculate a percentile of no values")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must lie in [0, 1]")
    ordered = sorted(float(value) for value in values)
    rank = (len(ordered) - 1) * probability
    low, high = floor(rank), ceil(rank)
    if low == high:
        return ordered[low]
    fraction = rank - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def _coerce(value: StatisticValue | float | int | None) -> StatisticValue:
    if isinstance(value, StatisticValue):
        return value
    if value is None:
        return StatisticValue(None, False, "undefined")
    number = float(value)
    if not isfinite(number):
        return StatisticValue(None, False, "non_finite")
    return StatisticValue(number, True, None)


def bootstrap_joint(
    records: Sequence[T],
    evaluator: Callable[[tuple[T, ...]], Mapping[str, StatisticValue | float | int | None]],
    *,
    statistic_names: Sequence[str],
    attempted_replicates: int = DEFAULT_ATTEMPTS,
    seed: int = SEED_BOOTSTRAP,
    minimum_valid_fraction: float = 0.90,
) -> BootstrapResult:
    """Evaluate every linked statistic on the same sampled block per replicate."""

    if not records:
        raise ValueError("Bootstrap requires at least one project block")
    if attempted_replicates <= 0:
        raise ValueError("attempted_replicates must be positive")
    if not 0.0 <= minimum_valid_fraction <= 1.0:
        raise ValueError("minimum_valid_fraction must lie in [0, 1]")
    names = tuple(statistic_names)
    if not names or len(set(names)) != len(names):
        raise ValueError("statistic_names must be unique and non-empty")
    values: dict[str, list[float]] = {name: [] for name in names}
    reasons: dict[str, Counter[str]] = {name: Counter() for name in names}
    generator = Random(seed)
    n = len(records)
    for _ in range(attempted_replicates):
        sample = tuple(records[generator.randrange(n)] for _ in range(n))
        evaluated = evaluator(sample)
        for name in names:
            item = _coerce(evaluated.get(name, StatisticValue(None, False, "statistic_missing")))
            if item.valid and item.value is not None and isfinite(item.value):
                values[name].append(float(item.value))
            else:
                reasons[name][item.reason or "undefined"] += 1

    required_valid = ceil(minimum_valid_fraction * attempted_replicates)
    summaries: dict[str, BootstrapStatistic] = {}
    for name in names:
        valid_values = tuple(values[name])
        valid = len(valid_values)
        report = valid >= required_valid
        summaries[name] = BootstrapStatistic(
            attempted=attempted_replicates,
            valid=valid,
            invalid=attempted_replicates - valid,
            lower=percentile(valid_values, 0.025) if report else None,
            upper=percentile(valid_values, 0.975) if report else None,
            interval_reported=report,
            invalid_reasons=tuple(sorted(reasons[name].items())),
            valid_values=valid_values,
        )
    return BootstrapResult(attempted_replicates, seed, summaries)
