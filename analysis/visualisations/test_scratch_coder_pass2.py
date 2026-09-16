"""Synthetic-only checks for pass-2 display logic and the isolation boundary."""
from __future__ import annotations

import unittest
from pathlib import Path

from analysis.visualisations.render_scratch_coder_pass2 import half_up, metric, signed, whole_percent


ROOT = Path(__file__).resolve().parents[2]


class RoundingTests(unittest.TestCase):
    def test_half_up_and_signed_zero(self):
        self.assertEqual(half_up("-0.000000000000000314", 2), "0.00")
        self.assertEqual(half_up("-0.03775091928386179", 2), "-0.04")
        self.assertEqual(signed("0.0005992244570877603", 3), "+0.001")
        self.assertEqual(signed("-0.002141124278556386", 3), "-0.002")

    def test_whole_percentage_uses_full_precision(self):
        self.assertEqual(whole_percent("0.014814814814814815"), 1)
        self.assertEqual(whole_percent("0.0036764705882352941"), 0)

    def test_metric_keeps_interval_and_removes_signed_zero(self):
        row = {"estimate_status": "R", "source_value_string": "0.076",
               "interval_status": "R", "interval_lower_string": "-3e-16", "interval_upper_string": "0.211"}
        self.assertEqual(metric(row), "0.08 [0.00, 0.21]")


class IsolationBoundaryTests(unittest.TestCase):
    def test_renderer_has_no_analytical_source_paths(self):
        source = (ROOT / "analysis/visualisations/render_scratch_coder_pass2.py").read_text(encoding="utf-8")
        for forbidden in ("scratch_coder_results", "confidence_exploratory", "results.md", "outputs_disagreement", "outputs_majority"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
