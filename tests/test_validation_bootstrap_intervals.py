from dataclasses import dataclass

import pytest

from analysis.validation.bootstrap import StatisticValue, bootstrap_joint, percentile
from analysis.validation.intervals import wilson_interval
from analysis.validation.metrics import nominal_distance
from analysis.validation.replacement import (
    REPLACEMENT_STATISTIC_NAMES,
    DimensionPanel,
    replacement_statistic_values,
)


def test_wilson_zero_all_and_half_successes():
    zero = wilson_interval(0, 10)
    all_success = wilson_interval(10, 10)
    half = wilson_interval(5, 10)
    assert zero.lower == 0
    assert zero.upper == pytest.approx(0.2775327998628892)
    assert all_success.lower == pytest.approx(1 - zero.upper)
    assert all_success.upper == 1
    assert half.lower == pytest.approx(0.236593090512564)
    assert half.upper == pytest.approx(0.7634069094874361)
    assert half.interval_type == "Wilson score"


def test_wilson_small_n_and_n_one():
    interval = wilson_interval(0, 1)
    assert interval.lower == 0
    assert interval.upper == pytest.approx(0.7934506856227626)
    assert wilson_interval(1, 1).lower == pytest.approx(1 - interval.upper)


@pytest.mark.parametrize(("successes", "n"), [(-1, 10), (11, 10), (0, 0), (0, -1)])
def test_wilson_rejects_invalid_counts(successes, n):
    with pytest.raises(ValueError):
        wilson_interval(successes, n)


def test_percentile_uses_explicit_type_7_linear_interpolation():
    assert percentile((0.0, 10.0), 0.025) == pytest.approx(0.25)
    assert percentile((0.0, 10.0), 0.975) == pytest.approx(9.75)
    assert percentile((1.0, 2.0, 3.0), 0.5) == 2.0


def test_bootstrap_is_reproducible_for_same_toy_seed():
    records = (1, 2, 3, 4)
    evaluator = lambda sample: {"mean": sum(sample) / len(sample)}
    first = bootstrap_joint(records, evaluator, statistic_names=("mean",), attempted_replicates=20, seed=17)
    second = bootstrap_joint(records, evaluator, statistic_names=("mean",), attempted_replicates=20, seed=17)
    assert first == second
    assert first.statistics["mean"].attempted == 20
    assert first.statistics["mean"].valid == 20


@dataclass(frozen=True)
class Block:
    record_id: str
    ratings: tuple[int, int, int, int]


def test_sampling_with_replacement_keeps_complete_blocks_together():
    blocks = (
        Block("SYN-201", (0, 0, 0, 0)),
        Block("SYN-202", (1, 1, 1, 1)),
        Block("SYN-203", (0, 1, 0, 1)),
    )

    def evaluator(sample):
        assert all(isinstance(block, Block) and len(block.ratings) == 4 for block in sample)
        duplicate = len({block.record_id for block in sample}) < len(sample)
        return {"duplicate_present": float(duplicate)}

    result = bootstrap_joint(
        blocks, evaluator, statistic_names=("duplicate_present",), attempted_replicates=30, seed=3
    )
    assert 1.0 in result.statistics["duplicate_present"].valid_values
    assert result.semantics == "attempted replicates, with no replacement or top-up of undefined replicates"


def test_no_top_up_and_statistic_specific_validity_counts():
    calls = 0

    def evaluator(sample):
        nonlocal calls
        calls += 1
        return {
            "always": 1.0,
            "sometimes": StatisticValue(1.0, True) if sum(sample) % 2 else StatisticValue(None, False, "even_sum"),
            "never": StatisticValue(None, False, "designed_undefined"),
        }

    result = bootstrap_joint(
        (1, 2, 3),
        evaluator,
        statistic_names=("always", "sometimes", "never"),
        attempted_replicates=17,
        seed=5,
    )
    assert calls == 17
    assert result.statistics["always"].valid == 17
    assert result.statistics["never"].valid == 0
    assert result.statistics["never"].invalid == 17
    assert result.statistics["never"].invalid_reasons == (("designed_undefined", 17),)
    assert result.statistics["sometimes"].valid + result.statistics["sometimes"].invalid == 17


def test_ninety_percent_threshold_is_inclusive_and_suppresses_below_threshold():
    calls = 0

    def evaluator(sample):
        nonlocal calls
        calls += 1
        return {
            "nine": 1.0 if calls <= 9 else StatisticValue(None, False, "last_invalid"),
            "eight": 1.0 if calls <= 8 else StatisticValue(None, False, "late_invalid"),
        }

    result = bootstrap_joint(
        (1,), evaluator, statistic_names=("nine", "eight"), attempted_replicates=10, seed=1
    )
    assert result.statistics["nine"].valid == 9
    assert result.statistics["nine"].interval_reported
    assert result.statistics["eight"].valid == 8
    assert not result.statistics["eight"].interval_reported
    assert result.statistics["eight"].lower is None
    assert result.statistics["eight"].upper is None


def test_replacement_quantities_are_recalculated_jointly_per_replicate():
    panels = (
        DimensionPanel("SYN-210", 0, 0, 0, 0),
        DimensionPanel("SYN-211", 1, 1, 1, 0),
        DimensionPanel("SYN-212", 0, 1, 0, 1),
    )
    calls = 0

    def evaluator(sample):
        nonlocal calls
        calls += 1
        return replacement_statistic_values(sample, nominal_distance)

    first = bootstrap_joint(
        panels,
        evaluator,
        statistic_names=REPLACEMENT_STATISTIC_NAMES,
        attempted_replicates=40,
        seed=29,
    )
    assert calls == 40
    for name in REPLACEMENT_STATISTIC_NAMES:
        statistic = first.statistics[name]
        assert statistic.attempted == 40
        assert statistic.valid + statistic.invalid == 40
    calls = 0
    second = bootstrap_joint(
        panels,
        evaluator,
        statistic_names=REPLACEMENT_STATISTIC_NAMES,
        attempted_replicates=40,
        seed=29,
    )
    assert first == second
    assert calls == 40
