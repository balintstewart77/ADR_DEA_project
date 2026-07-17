from fractions import Fraction

import pytest

from analysis.validation.alpha import krippendorff_alpha
from analysis.validation.metrics import (
    exact_set_equality,
    jaccard_similarity,
    masi_distance,
    masi_similarity,
    nominal_distance,
)
from analysis.validation.replacement import DimensionPanel, replacement_panel_analysis


def test_set_primitives_hand_checked_examples():
    assert exact_set_equality(frozenset({"A", "B"}), frozenset({"B", "A"}))
    assert jaccard_similarity(frozenset({"A", "B"}), frozenset({"A", "B"})) == Fraction(1)
    assert masi_similarity(frozenset({"A", "B"}), frozenset({"A", "B"})) == Fraction(1)
    assert jaccard_similarity(frozenset({"A"}), frozenset({"A", "B"})) == Fraction(1, 2)
    assert masi_similarity(frozenset({"A"}), frozenset({"A", "B"})) == Fraction(1, 3)
    assert jaccard_similarity(frozenset({"A", "B"}), frozenset({"B", "C"})) == Fraction(1, 3)
    assert masi_similarity(frozenset({"A", "B"}), frozenset({"B", "C"})) == Fraction(1, 9)
    assert masi_similarity(frozenset({"A"}), frozenset({"B"})) == 0


@pytest.mark.parametrize(
    ("left", "right", "jaccard", "masi"),
    [
        (frozenset(), frozenset(), Fraction(1), Fraction(1)),
        (frozenset(), frozenset({"A"}), Fraction(0), Fraction(0)),
        (frozenset({"A"}), frozenset(), Fraction(0), Fraction(0)),
        (frozenset({"A"}), frozenset({"A"}), Fraction(1), Fraction(1)),
    ],
)
def test_explicit_empty_and_singleton_behaviour(left, right, jaccard, masi):
    assert jaccard_similarity(left, right) == jaccard
    assert masi_similarity(left, right) == masi
    assert masi_distance(left, right) == 1 - masi
    assert jaccard_similarity(right, left) == jaccard
    assert masi_similarity(right, left) == masi


def test_alpha_perfect_agreement_with_between_unit_variation():
    result = krippendorff_alpha(((0, 0, 0), (1, 1, 1)), nominal_distance)
    assert result.valid
    assert result.alpha == pytest.approx(1.0)
    assert result.observed_disagreement == 0
    assert result.expected_disagreement == pytest.approx(0.6)
    assert result.number_of_units == 2
    assert result.number_of_ratings == 6


def test_constant_panel_is_undefined_not_perfect():
    result = krippendorff_alpha(((0, 0, 0), (0, 0, 0)), nominal_distance)
    assert not result.valid
    assert result.alpha is None
    assert result.undefined_reason == "expected_disagreement_zero"


def test_known_mixed_agreement_panel_alpha_is_three_eighths():
    # Do=1/3; De=8/15; alpha=1-(1/3)/(8/15)=3/8.
    result = krippendorff_alpha(((0, 0, 0), (0, 1, 1)), nominal_distance)
    assert result.valid
    assert result.observed_disagreement == pytest.approx(1 / 3)
    assert result.expected_disagreement == pytest.approx(8 / 15)
    assert result.alpha == pytest.approx(3 / 8)


def test_negative_alpha_panel():
    result = krippendorff_alpha(((0, 0, 1), (1, 1, 0)), nominal_distance)
    assert result.valid
    assert result.alpha == pytest.approx(-1 / 9)


def test_alpha_accepts_label_sets_and_is_coder_order_invariant():
    units = (
        (frozenset({"A"}), frozenset({"A"}), frozenset({"A", "B"})),
        (frozenset({"B"}), frozenset({"B"}), frozenset({"B"})),
    )
    permuted = tuple((c, a, b) for a, b, c in units)
    first = krippendorff_alpha(units, masi_distance)
    second = krippendorff_alpha(permuted, masi_distance)
    assert first.valid and second.valid
    assert first.alpha == pytest.approx(second.alpha)


def test_repeated_bootstrap_units_remain_separate_units():
    units = ((0, 0, 0), (1, 1, 1))
    result = krippendorff_alpha((units[0], units[0], units[1]), nominal_distance)
    assert result.valid
    assert result.number_of_units == 3
    assert result.number_of_ratings == 9
    assert result.alpha == pytest.approx(1.0)


def test_replacement_panel_manual_deltas():
    panels = (
        DimensionPanel("SYN-101", 0, 0, 0, 0),
        DimensionPanel("SYN-102", 1, 1, 1, 0),
    )
    result = replacement_panel_analysis(panels, nominal_distance)
    assert result.alpha_abc.alpha == pytest.approx(1.0)
    assert result.alpha_lbc.alpha == pytest.approx(3 / 8)
    assert result.alpha_alc.alpha == pytest.approx(3 / 8)
    assert result.alpha_abl.alpha == pytest.approx(3 / 8)
    assert result.delta_a == pytest.approx(-5 / 8)
    assert result.delta_b == pytest.approx(-5 / 8)
    assert result.delta_c == pytest.approx(-5 / 8)
    assert result.delta_min == pytest.approx(-5 / 8)


def test_replacement_positions_use_the_model_in_the_correct_slot():
    panels = (
        DimensionPanel("SYN-103", 1, 0, 0, 0),
        DimensionPanel("SYN-104", 0, 1, 1, 1),
    )
    result = replacement_panel_analysis(panels, nominal_distance)
    assert result.alpha_lbc.alpha == pytest.approx(1.0)  # model replaces A
    assert result.alpha_alc.alpha != pytest.approx(1.0)  # model replaces B
    assert result.alpha_abl.alpha != pytest.approx(1.0)  # model replaces C


def test_replacement_uses_one_common_complete_case_set():
    panels = (
        DimensionPanel("SYN-105", 0, 0, 0, 0),
        DimensionPanel("SYN-106", 1, 1, 1, 1),
        DimensionPanel("SYN-107", 0, 0, None, 0),
    )
    result = replacement_panel_analysis(panels, nominal_distance)
    assert result.common_record_ids == ("SYN-105", "SYN-106")
    for alpha in (result.alpha_abc, result.alpha_lbc, result.alpha_alc, result.alpha_abl):
        assert alpha.number_of_units == 2


def test_replacement_delta_min_is_coder_order_invariant():
    panels = (
        DimensionPanel("SYN-108", 1, 0, 0, 0),
        DimensionPanel("SYN-109", 0, 1, 1, 1),
        DimensionPanel("SYN-110", 1, 1, 0, 1),
    )
    permuted = tuple(DimensionPanel(p.record_id, p.coder_c, p.coder_a, p.coder_b, p.model) for p in panels)
    first = replacement_panel_analysis(panels, nominal_distance)
    second = replacement_panel_analysis(permuted, nominal_distance)
    assert first.alpha_abc.alpha == pytest.approx(second.alpha_abc.alpha)
    assert first.delta_min == pytest.approx(second.delta_min)


def test_replacement_propagates_undefined_components():
    result = replacement_panel_analysis(
        (DimensionPanel("SYN-111", 0, 0, 0, 0), DimensionPanel("SYN-112", 0, 0, 0, 0)),
        nominal_distance,
    )
    assert not result.valid
    assert result.delta_min is None
    assert "expected_disagreement_zero" in (result.undefined_reason or "")
