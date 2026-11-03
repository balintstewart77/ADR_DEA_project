"""Focused tests for the pass-4 display helpers."""
from __future__ import annotations

import unittest

from analysis.visualisations.render_scratch_coder_pass4 import marker_offsets, whole_percent_text


class MarkerOffsetTests(unittest.TestCase):
    def test_isolated_counts_stay_on_the_row(self):
        offsets = marker_offsets({"C01": 47, "C02": 38, "C03": 32, "Fable 5": 45})
        self.assertEqual(set(offsets.values()), {0.0})

    def test_identical_counts_are_separated_symmetrically(self):
        offsets = marker_offsets({"C01": 3, "C02": 0, "C03": 0, "Fable 5": 4})
        self.assertNotEqual(offsets["C02"], offsets["C03"])
        self.assertEqual(offsets["C02"] + offsets["C03"], 0.0)
        self.assertNotEqual(offsets["C01"], offsets["Fable 5"])

    def test_adjacent_counts_chain_into_one_cluster(self):
        offsets = marker_offsets({"C01": 4, "C02": 4, "C03": 3, "Fable 5": 4})
        self.assertEqual(sorted(offsets.values()), [-1.5, -0.5, 0.5, 1.5])


class PercentTextTests(unittest.TestCase):
    def test_near_complete_agreement_is_not_shown_as_100(self):
        self.assertEqual(whole_percent_text(1304, 1308), ">99%")
        self.assertEqual(whole_percent_text(201, 201), "100%")

    def test_ordinary_values_round_half_up(self):
        self.assertEqual(whole_percent_text(1263, 1308), "97%")
        self.assertEqual(whole_percent_text(171, 201), "85%")


if __name__ == "__main__":
    unittest.main()
