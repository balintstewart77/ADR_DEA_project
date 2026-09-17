"""Synthetic-only tests; no restricted input is opened.

Run from the repository root: python -m unittest analysis.pairwise_alpha_exploratory.test_run
"""

import hashlib
import random
import unittest

from analysis.validation.alpha import krippendorff_alpha
from analysis.validation.metrics import masi_distance, nominal_distance
from analysis.validation.replacement import DimensionPanel, replacement_panel_analysis
from analysis.scratch_coder_stage_a.config import DIMENSIONS

from . import compute, run

LABELS = ("d1", "d2", "d3", "d4")


def synthetic_sets(n, seed):
    rng = random.Random(seed)
    make = lambda: frozenset(rng.sample(LABELS, rng.randint(1, 2)))
    return tuple((make(), make(), make(), make()) for _ in range(n))


def synthetic_tags(n, seed):
    rng = random.Random(seed)
    return tuple(tuple(int(rng.random() < 0.3) for _ in range(4)) for _ in range(n))


class PairwiseStatistics(unittest.TestCase):
    def test_pairwise_values_are_direct_shared_estimator_calls(self):
        records = synthetic_sets(30, 1)
        stats = compute.statistics(records, compute.memoised(masi_distance))
        for x, y in compute.HUMAN_PAIRS + compute.MODEL_PAIRS:
            i, j = compute.RATER_INDEX[x], compute.RATER_INDEX[y]
            direct = krippendorff_alpha(((r[i], r[j]) for r in records), masi_distance)
            self.assertEqual(stats[f"alpha_{x}{y}"].value, direct.alpha)

    def test_derived_arithmetic(self):
        s = compute.statistics(synthetic_tags(40, 2), nominal_distance)
        v = {k: item.value for k, item in s.items()}
        self.assertEqual(v["diff_AC_minus_AB"], v["alpha_AC"] - v["alpha_AB"])
        self.assertEqual(v["diff_AB_minus_BC"], v["alpha_AB"] - v["alpha_BC"])
        self.assertEqual(v["H_B"], (v["alpha_AB"] + v["alpha_BC"]) / 2)
        self.assertEqual(v["M_B"], (v["alpha_LA"] + v["alpha_LC"]) / 2)
        self.assertEqual(v["D_C"], (v["alpha_LA"] + v["alpha_LB"]) / 2 - (v["alpha_AC"] + v["alpha_BC"]) / 2)

    def test_undefined_propagates(self):
        records = tuple((0, 0, rng_c, rng_l) for rng_c, rng_l in [(0, 1), (1, 0), (0, 0), (1, 1)])
        s = compute.statistics(records, nominal_distance)
        self.assertFalse(s["alpha_AB"].valid)
        self.assertEqual(s["alpha_AB"].reason, "expected_disagreement_zero")
        for name in ("diff_AC_minus_AB", "diff_AB_minus_BC", "H_A", "H_B", "D_A", "D_B"):
            self.assertFalse(s[name].valid, name)
        self.assertTrue(s["H_C"].valid)
        self.assertTrue(s["M_A"].valid)

    def test_three_rater_wiring_matches_replacement_panel(self):
        for records, distance in ((synthetic_sets(25, 3), masi_distance), (synthetic_tags(25, 4), nominal_distance)):
            panels = [DimensionPanel(str(k), *r) for k, r in enumerate(records)]
            canonical = replacement_panel_analysis(panels, distance)
            memo = compute.memoised(distance)
            self.assertEqual(compute.panel_alpha(records, "ABC", memo).alpha, canonical.alpha_abc.alpha)
            self.assertEqual(compute.panel_alpha(records, "LBC", memo).alpha, canonical.alpha_lbc.alpha)
            self.assertEqual(compute.panel_alpha(records, "ALC", memo).alpha, canonical.alpha_alc.alpha)
            self.assertEqual(compute.panel_alpha(records, "ABL", memo).alpha, canonical.alpha_abl.alpha)

    def test_ordering(self):
        self.assertEqual(compute.ordering({"A": 0.2, "B": -0.1, "C": 0.05}), "B < C < A")
        self.assertEqual(compute.ordering({"A": 0.0, "B": 0.1, "C": 0.0}), "A = C < B")
        self.assertIsNone(compute.ordering({"A": None, "B": 0.1, "C": 0.0}))

    def test_bootstrap_counts_and_reproducibility(self):
        records = synthetic_tags(20, 5)
        first = compute.bootstrap_job(records, "COVID-19 & Pandemic", 30, 99, 0.9)
        second = compute.bootstrap_job(records, "COVID-19 & Pandemic", 30, 99, 0.9)
        self.assertEqual(first, second)
        for name in compute.STATISTIC_NAMES:
            self.assertEqual(first[name]["valid"] + first[name]["invalid"], 30)

    def test_crlf_reconstruction(self):
        lf = b'a,b\n1,"x\ny"\n2,z\n'
        crlf = b'a,b\r\n1,"x\ny"\r\n2,z\r\n'
        self.assertEqual(run.crlf_row_terminator_sha256(lf), (hashlib.sha256(crlf).hexdigest(), len(crlf)))


class SyntheticTables(unittest.TestCase):
    def test_tables_checks_and_markdown(self):
        attempts = 20
        built = {}
        for population, _ in run.POPULATIONS:
            for k, dimension in enumerate(DIMENSIONS):
                recs = synthetic_sets(15, k) if dimension in ("Research Domains", "Analytical Purposes") else synthetic_tags(15, k)
                built[(population, dimension)] = dict(ids=tuple(map(str, range(15))), records=recs)
        results = run.compute_all(built, attempts=attempts, workers=2)
        ledger = []
        run.output_checks(ledger, results, attempts=attempts)
        context = {key: dict(n_records=15, tag_majority_positive_n=None if key[1] in ("Research Domains", "Analytical Purposes") else 3,
                             empty_label_sets=0) for key in built}
        deltas = {(p, d, f"delta_{x}"): v for (p, d) in built for x, v in zip("ABC", (0.1, -0.2, 0.0))}
        tables = run.build_tables(results, context, deltas, attempts=attempts, threshold=18)
        self.assertEqual(len(tables), 32)
        self.assertEqual([t["table_id"] for t in tables][:2], ["PWA1T001", "PWA1T002"])
        self.assertTrue(all(t["note"] == run.DIAGNOSTIC for t in tables if t["population"] == "hard_case"))
        self.assertTrue(all(t["note"] == "" for t in tables if t["population"] == "baseline"))
        a4 = [t for t in tables if t["analysis"] == 4]
        self.assertTrue(all(t["ordering"]["delta"] == "B < C < A" for t in a4))
        metadata = dict(run_started_utc="synthetic", check_w=[])
        text = run.render_markdown(tables, metadata)
        self.assertIn("PWA1T032", text)
        self.assertIn("Confidence level: 95%", text)

    def test_output_check_detects_bad_arithmetic(self):
        records = synthetic_tags(15, 7)
        key = ("baseline", "COVID-19 & Pandemic")
        points = compute.statistics(records, nominal_distance)
        points["D_A"] = compute.StatisticValue(123.0, True, None)
        boots = {key: compute.bootstrap_job(records, key[1], 10, 1, 0.9)}
        with self.assertRaises(RuntimeError):
            run.output_checks([], dict(points={key: points}, boots=boots), attempts=10)


if __name__ == "__main__":
    unittest.main()
