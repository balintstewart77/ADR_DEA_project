"""Targeted checks for GHA1's pure functions (no data files needed)."""
from itertools import product

import numpy as np

from analysis.exploratory_gpt55_human_agreement.run import (AGREE_PATTERNS, PATTERNS, agree_pattern_for, pair_rows, pattern_for,
                                                            statistics)
from analysis.validation.metrics import masi_distance

A, B, C, D = (frozenset({x}) for x in "abcd")
AB = frozenset({"a", "b"})


def test_patterns_are_exclusive_and_exhaustive():
    options = (A, B, C, AB)
    for humans in product(options, repeat=3):
        for fable, gpt in product(options, repeat=2):
            if fable == gpt:
                continue
            assert pattern_for(humans, fable, gpt) in PATTERNS
    assert pattern_for((A, A, A), A, B) == PATTERNS[0]
    assert pattern_for((B, B, B), A, B) == PATTERNS[1]
    assert pattern_for((C, C, C), A, B) == PATTERNS[2]
    assert pattern_for((A, B, C), A, B) == PATTERNS[3]
    assert pattern_for((A, C, C), A, B) == PATTERNS[4]
    assert pattern_for((B, C, C), A, B) == PATTERNS[5]
    assert pattern_for((C, D, C), A, B) == PATTERNS[6]


def test_agreement_cases():
    assert agree_pattern_for((A, A, A), A) == AGREE_PATTERNS[0]
    assert agree_pattern_for((B, B, B), A) == AGREE_PATTERNS[1]
    assert agree_pattern_for((A, B, B), A) == AGREE_PATTERNS[2]
    assert agree_pattern_for((B, C, B), A) == AGREE_PATTERNS[3]


def _encode(records):
    categories = tuple(dict.fromkeys(v for rec in records for v in rec))
    index = {v: k for k, v in enumerate(categories)}
    ratings = np.array([[index[v] for v in rec] for rec in records], dtype=np.int32)
    distance = np.array([[float(masi_distance(a, b)) for b in categories] for a in categories])
    return ratings, distance


def test_identical_models_give_zero_contrasts_and_equal_deltas():
    rng = np.random.default_rng(1)
    options = (A, B, C, AB)
    records = [tuple(options[i] for i in rng.integers(0, 4, size=4)) for _ in range(40)]
    records = [rec + (rec[3],) for rec in records]  # GPT column copies the Fable column
    ratings, distance = _encode(records)
    out = statistics(ratings, distance)
    for coder in ("C01", "C02", "C03"):
        assert abs(out[f"contrast_G_minus_F_replacing_{coder}"]) < 1e-12
        assert out[f"F_delta_replacing_{coder}"] == out[f"G_delta_replacing_{coder}"]


def test_pairwise_symmetric_counts():
    records = [(A, A, B, AB, A), (AB, A, A, AB, AB)]
    rows = {(r["source_a"], r["source_b"]): r for r in pair_rows(records, "t", "all", "Research Domains")}
    assert len(rows) == 10
    assert rows[("C01", "C02")]["exact_set_n"] == 1
    assert rows[("Fable 5", "GPT-5.5")]["exact_set_n"] == 1
    assert abs(rows[("C01", "Fable 5")]["mean_jaccard"] - 0.75) < 1e-12
