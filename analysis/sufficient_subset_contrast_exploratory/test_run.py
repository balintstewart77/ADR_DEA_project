"""Synthetic-only tests; no restricted or coder input is opened.

Run from the repository root: venv/Scripts/python.exe -m pytest analysis/sufficient_subset_contrast_exploratory/test_run.py
"""

import random
import unittest

import numpy as np

from analysis.scratch_coder_stage_a.agreement import encode_panels
from analysis.validation.metrics import masi_distance
from analysis.validation.replacement import DimensionPanel, replacement_panel_analysis

from . import run

U = run.UNCLEAR_ONLY
LABELS = ("d1", "d2", "d3", "d4")


def synthetic(n, seed, p_unclear=0.2):
    rng = random.Random(seed)
    make = lambda: U if rng.random() < p_unclear else frozenset(rng.sample(LABELS, rng.randint(1, 2)))
    return [tuple(make() for _ in range(4)) for _ in range(n)]


def as_panels(records):
    return [DimensionPanel(f"r{i:03d}", *sets) for i, sets in enumerate(records)]


class PairCategories(unittest.TestCase):
    def test_categories_are_exhaustive_and_directional(self):
        a, b = frozenset({"d1"}), frozenset({"d1", "d2"})
        self.assertEqual(run.pair_category(U, U), "both_unclear_only")
        self.assertEqual(run.pair_category(U, a), "first_unclear_only")
        self.assertEqual(run.pair_category(a, U), "second_unclear_only")
        self.assertEqual(run.pair_category(a, a), "identical_substantive")
        self.assertEqual(run.pair_category(a, b), "different_substantive")

    def test_summary_counts_add_and_exact_sums(self):
        records = synthetic(40, 1)
        s = run.pair_summary(records, run.HUMAN_PAIRS)
        self.assertEqual(sum(s[c] for c in run.CATEGORIES), 120)
        self.assertEqual(s["both_substantive"], s["identical_substantive"] + s["different_substantive"])
        direct = sum(masi_distance(r[i], r[j]) for r in records for i, j in run.HUMAN_PAIRS)
        self.assertEqual(s["masi_sum"], direct)


class Disagreement(unittest.TestCase):
    def test_do_split_matches_estimator_and_adds(self):
        records = synthetic(60, 2)
        result = replacement_panel_analysis(as_panels(records), masi_distance)
        for name, alpha in (("ABC", result.alpha_abc), ("LBC", result.alpha_lbc), ("ALC", result.alpha_alc), ("ABL", result.alpha_abl)):
            split = run.panel_disagreement(records, run.PANELS[name])
            self.assertAlmostEqual(float(split["Do"]), alpha.observed_disagreement, places=12)
            self.assertEqual(split["Do"], split["DoU"] + split["DoS"])

    def test_identity_reproduces_contrast(self):
        records = synthetic(80, 3)
        strict = records[:50]
        out = {}
        for label, recs in (("full", records), ("strict", strict)):
            result = replacement_panel_analysis(as_panels(recs), masi_distance)
            split = run.panel_disagreement(recs, run.PANELS["ALC"])
            out[label] = {k: float(v) for k, v in split.items() if k in ("Do", "DoU", "DoS")}
            out[label]["De"] = result.alpha_alc.expected_disagreement
            out[label]["alpha"] = result.alpha_alc.alpha
        terms = run.decompose(out["full"], out["strict"])
        self.assertAlmostEqual(terms["total"], out["strict"]["alpha"] - out["full"]["alpha"], places=12)


class Bootstrap(unittest.TestCase):
    def test_paired_bootstrap_keeps_duplicates_and_matches_explicit_sequences(self):
        records = synthetic(30, 4)
        panels = as_panels(records)
        encoded = encode_panels(panels, masi_distance)
        mask = np.array([i % 3 != 0 for i in range(30)])
        draws = np.random.default_rng(7).integers(0, 30, size=(4, 30), dtype=np.int32)
        full, strict, sizes = run.paired_bootstrap(encoded, mask, draws)
        for k, d in enumerate(draws):
            self.assertEqual(sizes[k], int(mask[d].sum()))
            seq = [panels[i] for i in d if mask[i]]
            res = replacement_panel_analysis(seq, masi_distance)
            np.testing.assert_allclose(strict[k][:4], [res.alpha_abc.alpha, res.alpha_lbc.alpha, res.alpha_alc.alpha, res.alpha_abl.alpha], atol=1e-12, rtol=0)
            res = replacement_panel_analysis([panels[i] for i in d], masi_distance)
            self.assertAlmostEqual(full[k][7], res.delta_min, places=12)

    def test_interval_rule_counts_undefined_and_requires_90_percent(self):
        values = np.concatenate([np.linspace(-1, 1, 89), np.full(11, np.nan)])
        out = run.percentile_interval(values, 100)
        self.assertEqual((out["valid"], out["undefined"], out["interval_reported"]), (89, 11, False))
        self.assertIsNone(out["lower"])
        values = np.concatenate([np.linspace(-1, 1, 90), np.full(10, np.nan)])
        out = run.percentile_interval(values, 100)
        self.assertTrue(out["interval_reported"])
        self.assertAlmostEqual(out["lower"], float(np.quantile(np.linspace(-1, 1, 90), 0.025, method="linear")))

    def test_share_is_whole_number(self):
        self.assertEqual(run.share(1, 276), "<1%")
        self.assertEqual(run.share(0, 276), "0%")
        self.assertEqual(run.share(1, 8), "13%")


if __name__ == "__main__":
    unittest.main()
