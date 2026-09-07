"""Focused checks for the authorised Wilson supplement only."""
from __future__ import annotations

import unittest

from .wilson_supplement import (
    DEFAULT_MANIFEST,
    SELECTED_IDS,
    TOLERANCE,
    calculation,
    create_rows,
    load_manifest,
    reused_payload,
    validate_selected,
)


class WilsonSupplementChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope, _ = load_manifest(DEFAULT_MANIFEST)

    def test_authorised_selection_is_exact_and_source_grounded(self):
        selected, hashes = validate_selected(self.scope)
        self.assertEqual([item["candidate_id"] for item in selected], list(SELECTED_IDS))
        self.assertEqual(len(selected), 37)
        self.assertTrue(all(item["population"] == "baseline" for item in selected))
        self.assertTrue(all(item["source_denominator"] == "150" for item in selected))
        self.assertEqual({item["observational_unit_class"] for item in selected},
                         {"individual_coder_binary", "record_binary"})
        self.assertTrue(hashes)

    def test_zero_all_and_interior_formula_checks(self):
        for successes in (0, 1, 75, 149, 150):
            result = calculation(successes, 150)
            point = successes / 150
            self.assertLessEqual(result["lower"] - TOLERANCE, point)
            self.assertLessEqual(point, result["upper"] + TOLERANCE)
            self.assertGreaterEqual(result["lower"], 0.0)
            self.assertLessEqual(result["upper"], 1.0)

    def test_wilson_midpoint_is_not_required_to_equal_observed_proportion(self):
        result = calculation(92, 150)
        midpoint = (result["lower"] + result["upper"]) / 2
        self.assertGreater(abs(midpoint - 92 / 150), 1e-6)

    def test_exactly_37_rows_are_created_without_replacing_point_strings(self):
        selected, _ = validate_selected(self.scope)
        rows, _ = create_rows(selected, "2026-09-07T00:00:00+00:00", "implementation-hash-fixture")
        self.assertEqual(len(rows), 37)
        by_id = {row["candidate_id"]: row for row in rows}
        source = {item["candidate_id"]: item for item in selected}
        for identifier in SELECTED_IDS:
            self.assertEqual(by_id[identifier]["original_proportion"], source[identifier]["source_proportion"])
            self.assertEqual(by_id[identifier]["original_numerator"], source[identifier]["source_numerator"])
            self.assertEqual(by_id[identifier]["original_denominator"], source[identifier]["source_denominator"])

    def test_equivalent_reuse_has_two_origins_and_three_entries(self):
        _, hashes = validate_selected(self.scope)
        reused = reused_payload(self.scope, hashes)
        self.assertEqual(reused["originating_interval_count"], 2)
        self.assertEqual(reused["report_entry_count"], 3)
        entries = {item["candidate_id"]: item for item in reused["report_entries"]}
        self.assertEqual(entries["WSA0074"]["origin"], "WSA0083")
        self.assertEqual(entries["WSA0074"]["exact_cells_equal"], ["count", "denominator", "proportion"])


if __name__ == "__main__":
    unittest.main()
