"""Focused extraction/rendering tests for the revised scratch-coder paper set."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from analysis.visualisations.extract_scratch_coder_paper import ROOT, status_parts
from analysis.visualisations.render_scratch_coder_paper import display_value


class StatusPresentationTests(unittest.TestCase):
    def row(self, estimate="0.5", estimate_status="R", interval_status="R", lower="0.4", upper="0.6", confidence="95%"):
        return {"source_value_string": estimate, "estimate_status": estimate_status,
                "interval_status": interval_status, "interval_lower_string": lower,
                "interval_upper_string": upper, "confidence_level": confidence}

    def test_status_parser_keeps_estimate_and_interval_separate(self):
        self.assertEqual(status_parts("R/SV; valid/invalid/requested draws 1/9/10"), ("R", "SV", "", ""))
        self.assertEqual(status_parts("W/W"), ("W", "W", "", ""))
        self.assertEqual(status_parts("D/A"), ("D", "A", "", ""))

    def test_synthetic_presentation_states(self):
        self.assertIn("◇", display_value(self.row(lower="0.5", upper="0.5")))
        self.assertEqual(display_value(self.row(interval_status="SV", lower="", upper="")), "0.500 SV")
        self.assertEqual(display_value(self.row(interval_status="A", lower="", upper="")), "0.500 A")
        self.assertEqual(display_value(self.row(estimate="", estimate_status="W", interval_status="W", lower="", upper="")), "Withheld")
        self.assertEqual(display_value(self.row(estimate="", estimate_status="D", interval_status="A", lower="", upper="")), "Undefined")
        self.assertEqual(display_value(self.row(estimate="0", interval_status="N", lower="", upper="")), "0.000")


class IsolatedWorkflowTests(unittest.TestCase):
    def test_stage1_and_stage2_complete_from_copied_extractions(self):
        with tempfile.TemporaryDirectory(prefix="scratch_coder_paper_test_") as temp:
            root = Path(temp)
            data = root / "data"
            figures = root / "figures"
            tables = root / "tables"
            subprocess.run([sys.executable, "-B", str(ROOT / "analysis/visualisations/extract_scratch_coder_paper.py"), "--data-dir", str(data)], cwd=ROOT, check=True)
            manifest = json.loads((data / "scratch_coder_deliverable_manifest.json").read_text())
            self.assertEqual(len(manifest["current"]), 10)
            subprocess.run([sys.executable, "-B", str(ROOT / "analysis/visualisations/render_scratch_coder_paper.py"), "--data-dir", str(data), "--figure-dir", str(figures), "--table-dir", str(tables)], cwd=ROOT, check=True)
            self.assertEqual(len(list(figures.glob("scratch_coder_figure_[1-4]_*.svg"))), 4)
            self.assertEqual(len(list(figures.glob("scratch_coder_figure_[1-4]_*.png"))), 4)
            self.assertEqual(len(list(tables.glob("scratch_coder_*.md"))), 6)
            self.assertEqual(len(list(tables.glob("scratch_coder_*.csv"))), 6)
            report = json.loads((figures / "scratch_coder_rendering_report.json").read_text())
            self.assertTrue(all(v["all_values_strictly_inside_axes"] for v in report["visibility_validation"].values()))
            # Production-shape checks: every label has exactly six kappa cells.
            with (data / "scratch_coder_table_1_pairwise_kappa_domains.csv").open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            counts = {}
            for row in rows: counts[row["label"]] = counts.get(row["label"], 0) + 1
            self.assertEqual(set(counts.values()), {6})


if __name__ == "__main__":
    unittest.main()
