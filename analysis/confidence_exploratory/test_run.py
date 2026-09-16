"""Synthetic-only integration checks for table and denominator edge cases."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd

from . import run


class SyntheticTables(unittest.TestCase):
    def test_complete_categories_and_zero_confidence_row(self):
        rows = []
        ratings = {"baseline": ((1, 2, 3), (1, 1, 1), (2, 2, 2)),
                   "hard_case": ((1, 1, 1), (2, 2, 2), (1, 2, 2))}
        for population, units in ratings.items():
            for index, unit in enumerate(units):
                for coder, confidence in zip(run.CODERS, unit):
                    rows.append(dict(population=population, record_id=str(index), coder=coder,
                                     confidence=confidence, sufficiency=index + 1))
        data = SimpleNamespace(responses=pd.DataFrame(rows), baseline_ids=frozenset(map(str, range(3))),
                               hard_case_ids=frozenset(map(str, range(3))))
        summary = {
            "baseline": dict(records=3, confidence_counts=(4, 4, 1), sufficiency_counts={"all": (3, 3, 3)}),
            "hard_case": dict(records=3, confidence_counts=(4, 5, 0), sufficiency_counts={"all": (3, 3, 3)}),
        }
        with patch.object(run, "ATTEMPTS", 20), patch.object(run, "THRESHOLD", 18):
            tables = run.compute(data)
            run.output_checks(tables, summary)
        self.assertEqual(len(tables), 10)
        majority = tables[1]["rows"]
        self.assertEqual([r["count"] for r in majority], [1, 1, 0, 1])
        zero_row = [r for r in tables[9]["rows"] if r["category"] == "Low"]
        self.assertEqual(len(zero_row), 3)
        for row in zero_row:
            self.assertEqual((row["count"], row["denominator"], row["proportion"], row["estimate_status"]), (0, 0, None, "undefined"))
        for row in tables[5]["rows"] + tables[6]["rows"]:
            self.assertEqual(row["interval_status"], "not_applied_diagnostic_sample")
        for table in tables:
            for row in table["rows"]:
                if table["population"] == "hard_case":
                    self.assertEqual(row["analysis_note"], run.DIAGNOSTIC)


if __name__ == "__main__":
    unittest.main()
