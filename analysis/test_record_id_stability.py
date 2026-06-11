import tempfile
import unittest

import pandas as pd

from analysis.register_cleaning import assign_record_ids
from analysis.llm_theme_analysis_v3 import (
    CACHE_SCHEMA_VERSION,
    _classification_fingerprint,
    _sanitise_prompt_text,
    _summarise_datasets,
    load_cache,
)
from analysis.rebuild_llm_cache import build_cache_entries, write_cache


def _register_rows():
    return [
        {
            "Project ID": "2026/001",
            "Title": "Zebra crossings and road safety",
            "Accreditation Date": pd.Timestamp("2026-02-01"),
            "Datasets Used": "DfT: Road Safety Data",
            "Researchers": "A Researcher, University of Somewhere",
        },
        {
            "Project ID": "2026/001",
            "Title": "Apple orchards and rural employment",
            "Accreditation Date": pd.Timestamp("2026-01-01"),
            "Datasets Used": "DEFRA: June Survey of Agriculture",
            "Researchers": "B Researcher, University of Elsewhere",
        },
        {
            "Project ID": "2026/002",
            "Title": "A project with a unique ID",
            "Accreditation Date": pd.Timestamp("2026-03-01"),
            "Datasets Used": "ONS: Labour Force Survey",
            "Researchers": "C Researcher",
        },
    ]


class StableRecordIdTest(unittest.TestCase):
    def test_suffixes_do_not_depend_on_row_order(self):
        rows = _register_rows()
        forward = assign_record_ids(pd.DataFrame(rows))
        reversed_df = assign_record_ids(pd.DataFrame(list(reversed(rows))))

        forward_map = dict(zip(forward["Title"], forward["Record ID"]))
        reversed_map = dict(zip(reversed_df["Title"], reversed_df["Record ID"]))
        self.assertEqual(forward_map, reversed_map)

    def test_suffix_order_is_content_derived(self):
        out = assign_record_ids(pd.DataFrame(_register_rows()))
        by_title = dict(zip(out["Title"], out["Record ID"]))
        # The earlier-dated record takes /a regardless of file position.
        self.assertEqual(by_title["Apple orchards and rural employment"], "2026/001/a")
        self.assertEqual(by_title["Zebra crossings and road safety"], "2026/001/b")
        self.assertEqual(by_title["A project with a unique ID"], "2026/002")

    def test_unique_ids_get_no_suffix(self):
        out = assign_record_ids(pd.DataFrame(_register_rows()))
        unsuffixed = out[out["Project ID"] == "2026/002"]
        self.assertEqual(list(unsuffixed["Record ID"]), ["2026/002"])


class ClassificationFingerprintTest(unittest.TestCase):
    def test_fingerprint_changes_with_content(self):
        base = _classification_fingerprint("Title A", "Datasets A")
        self.assertEqual(base, _classification_fingerprint("Title A", "Datasets A"))
        self.assertNotEqual(base, _classification_fingerprint("Title B", "Datasets A"))
        self.assertNotEqual(base, _classification_fingerprint("Title A", "Datasets B"))


class RebuildCacheTest(unittest.TestCase):
    def _classifications_frame(self):
        return pd.DataFrame([
            {
                "Project ID": "2026/001",
                "Record ID": "2026/001/a",
                "Title": "Apple orchards and rural employment",
                "Datasets Used": "DEFRA: June Survey of Agriculture",
                "substantive_domains": "Environment & Agriculture; Labour Market & Employment",
                "analytical_purpose": "Descriptive Monitoring",
                "cross_cutting_tags": "",
                "rationale": "Farm employment patterns.",
            },
            {
                "Project ID": "2026/002",
                "Record ID": "2026/002",
                "Title": "A project with a unique ID",
                "Datasets Used": "ONS: Labour Force Survey",
                "substantive_domains": "Labour Market & Employment",
                "analytical_purpose": "Policy Evaluation / Impact Analysis",
                "cross_cutting_tags": "COVID-19 & Pandemic",
                "rationale": "",
            },
        ])

    def test_entries_roundtrip_through_load_cache(self):
        entries = build_cache_entries(self._classifications_frame())
        self.assertEqual(
            entries["2026/001/a"]["substantive_domains"],
            ["Environment & Agriculture", "Labour Market & Employment"],
        )
        self.assertEqual(entries["2026/002"]["cross_cutting_tags"], ["COVID-19 & Pandemic"])
        self.assertEqual(entries["2026/001/a"]["cross_cutting_tags"], [])

        # Fingerprints must match what classify_all computes for the same content.
        expected = _classification_fingerprint(
            _sanitise_prompt_text("A project with a unique ID"),
            _summarise_datasets("ONS: Labour Force Survey"),
        )
        self.assertEqual(entries["2026/002"]["fingerprint"], expected)

        with tempfile.TemporaryDirectory() as tmp:
            path = f"{tmp}/llm_layer_cache.json"
            from analysis.llm_theme_analysis_v3 import MODEL, PROMPT_VERSION
            write_cache(entries, path, model=MODEL, prompt_version=PROMPT_VERSION)
            loaded = load_cache(path)
        self.assertEqual(set(loaded), {"2026/001/a", "2026/002"})
        self.assertEqual(loaded["2026/002"]["fingerprint"], expected)

    def test_duplicate_record_ids_rejected(self):
        frame = self._classifications_frame()
        frame.loc[1, "Record ID"] = "2026/001/a"
        with self.assertRaises(ValueError):
            build_cache_entries(frame)

    def test_schema_version_is_current(self):
        # The rebuild tool writes the version load_cache expects; if the schema
        # bumps again this test forces the tool to be revisited.
        self.assertEqual(CACHE_SCHEMA_VERSION, 6)


if __name__ == "__main__":
    unittest.main()
