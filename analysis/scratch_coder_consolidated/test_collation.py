"""Targeted mutation checks for concrete collation risks; no output files."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .audit_applicability import content_sha256, validate as validate_audit_applicability
from .generate import historical_housekeeping
from .preflight import Fatal, ROOT, Sources, TAGS
from .report import Report, esc, unresolved_explanation_rollup
from .supplement import WilsonSupplement


class CollationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Sources({})
        cls.sources.load()

    def fresh(self):
        return copy.deepcopy(self.sources)

    def supplemented_report(self, sources):
        return Report(sources, supplement=WilsonSupplement(ROOT / "analysis/outputs_validation_wilson_baseline_20260907T142427225531Z", sources))

    def test_duplicate_key_is_fatal(self):
        s = Sources({})
        original = s.text

        def text_with_duplicate(path):
            result = original(path)
            if path.endswith("replacement_panel_results.csv"):
                result += result.splitlines()[1] + "\n"
            return result

        with patch.object(s, "text", side_effect=text_with_duplicate):
            with self.assertRaisesRegex(Fatal, "duplicate row key"):
                s.load()

    def test_missing_baseline_tag_row_is_fatal(self):
        s = self.fresh()
        del s.index["tag_diagnostics"][("baseline", TAGS[0])]
        with self.assertRaisesRegex(Fatal, "Coverage failure"):
            s.coverage()

    def test_tag_rare_band_does_not_blank_diagnostics(self):
        # Synthetic in-memory policy mutation; never saved as analytical output.
        s = self.fresh()
        support = s.lookup("label_support", dimension="Cross-cutting tag", label=TAGS[0])
        support["support_band"] = "RARE"
        support["low_support_caution_required"] = "True"
        r = self.supplemented_report(s)
        t = r.new_table(2, "Synthetic policy test", "baseline", TAGS[0])
        source = s.lookup("tag_diagnostics", population="baseline", tag=TAGS[0])
        item = r.add(t, "tag_diagnostics", source, "cohen_kappa")
        self.assertEqual(item["displayed_estimate"], source["cohen_kappa"])
        self.assertEqual(item["estimate_status"], "reported")
        self.assertIn("RARE", item["support_display"])

    def test_withholding_cannot_leak_into_second_table(self):
        s = self.fresh()
        r = self.supplemented_report(s)
        source = next(x for x in s.tables["per_label_contingencies"] if x["support_band"] == "RARE")
        for _ in range(2):
            t = r.new_table(5, "Synthetic withholding test", "baseline", source["dimension"])
            item = r.add(t, "per_label_contingencies", source, "kappa", force_withheld=True)
            self.assertEqual([item[k] for k in ("displayed_estimate", "displayed_lower", "displayed_upper")], ["", "", ""])
            self.assertEqual(item["estimate_status"], "withheld_support_rule")
        self.assertFalse(any(x["field"] == "kappa.interval" for x in s.unresolved))

    def test_zero_false_and_missing_remain_distinct(self):
        s = self.fresh()
        r = self.supplemented_report(s)
        source = next(x for x in s.tables["qa_summary"] if x["count"] == "0")
        t = r.new_table(1, "Missingness test", source["population"], source["dimension"])
        self.assertEqual(r.add(t, "qa_summary", source, "count")["displayed_estimate"], "0")
        flag = dict(s.tables["replacement_trigger_summary"][0])
        col = "all_three_replacement_deltas_below_zero"
        for raw in ("NO", "False", ""):
            flag[col] = raw
            item = r.add(t, "replacement_trigger_summary", flag, col)
            self.assertEqual(item["displayed_estimate"], raw)
            self.assertEqual(item["estimate_status"], "unresolved" if raw == "" else "reported")

    def test_support_join_conflict_is_fatal(self):
        s = self.fresh()
        s.tables["per_label_pairwise_kappa"][0]["support_band"] = "RARE"
        with self.assertRaisesRegex(Fatal, "Support join conflict"):
            s.support_joins()

    def test_markdown_pipe_escape(self):
        self.assertEqual(esc("dimension | label\nnext"), "dimension \\| label next")

    def test_unresolved_rollup_uses_exact_explanations_and_all_identifiers(self):
        fixture = [
            {"id": "U1", "cannot_establish": "Repeated explanation."},
            {"id": "U2", "cannot_establish": "Singleton explanation."},
            {"id": "U3", "cannot_establish": "Repeated explanation."},
        ]
        rows = unresolved_explanation_rollup(fixture)
        self.assertEqual(rows, [
            {"cannot_establish": "Repeated explanation.", "count": 2, "member_ids": ["U1", "U3"]},
            {"cannot_establish": "Singleton explanation.", "count": 1, "member_ids": ["U2"]},
        ])
        self.assertEqual(sum(row["count"] for row in rows), len(fixture))

    def test_unresolved_rollup_rejects_duplicate_identifiers(self):
        fixture = [
            {"id": "U1", "cannot_establish": "First."},
            {"id": "U1", "cannot_establish": "Second."},
        ]
        with self.assertRaisesRegex(Fatal, "Duplicate canonical unresolved identifier"):
            unresolved_explanation_rollup(fixture)

    def test_reporting_followup_preserves_unresolved_inventory_and_renders_clarifications(self):
        s = self.fresh()
        s.meta.update(generation_timestamp_utc="test", generator={"git_head": "test", "git_status_before": ""})
        r = self.supplemented_report(s)
        r.build()
        document = r.render()
        self.assertEqual(len(s.unresolved), 69)
        self.assertEqual(len({item["id"] for item in s.unresolved}), 69)
        self.assertIn("Every hard-case record belongs to one of three 25-record strata", document)
        self.assertIn("Section 8 contains 12 of the report-wide 37 newly calculated supplementary Wilson-score intervals", document)
        self.assertIn("Section 9 contains 17 of the report-wide 37 newly calculated supplementary Wilson-score intervals", document)
        self.assertIn("Section 10 contains eight of the report-wide 37 newly calculated supplementary Wilson-score intervals", document)
        self.assertIn("Dated audit evidence annotations — 2026-09-14", document)
        self.assertIn("U0005 remains open pending review of the historical documentation", document)
        followup = r.meta["reporting_followup"]
        self.assertEqual(followup["ledger"], {"checks": 3496, "verified": 3488, "discrepant": 3, "blocked": 3, "not_checked": 2})
        self.assertEqual(followup["original_unresolved_entries_retained"], 69)
        self.assertTrue(followup["applicability"]["analytical_content"]["current_matches_fixed_baseline"])

    def test_audit_applicability_fails_closed_for_each_audit_relevant_mutation(self):
        s = self.fresh()
        r = self.supplemented_report(s)
        r.build()
        baseline = copy.deepcopy(r.meta)
        self.assertEqual(content_sha256(baseline), "9da6e0dc6bcc7f8487a43aa89bb941d240064f61bdfb55ed1a3ebcd4689724ce")
        self.assertTrue(validate_audit_applicability(baseline)["analytical_content"]["current_matches_fixed_baseline"])
        mutations = [
            ("result", lambda m: m["result_items"][0].__setitem__("displayed_estimate", "changed")),
            ("denominator", lambda m: m["result_items"][0].__setitem__("denominator_display", "changed")),
            ("population", lambda m: m["result_items"][0].__setitem__("population", "changed")),
            ("source", lambda m: m["source_files"][next(iter(m["source_files"]))].__setitem__("sha256", "0" * 64)),
            ("reuse", lambda m: m["supplement"].__setitem__("equivalent_result_reuse", "changed")),
            ("unresolved", lambda m: m["unresolved_items"][0].__setitem__("known", "changed")),
        ]
        for name, mutate in mutations:
            changed = copy.deepcopy(baseline)
            mutate(changed)
            with self.subTest(name=name), self.assertRaisesRegex(Fatal, "Audit applicability"):
                validate_audit_applicability(changed)
        volatile = copy.deepcopy(baseline)
        volatile["generation_timestamp_utc"] = "changed"
        volatile["generator"] = {"changed": True}
        self.assertTrue(validate_audit_applicability(volatile)["analytical_content"]["current_matches_fixed_baseline"])
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(Fatal, "evidence is missing"):
                validate_audit_applicability(baseline, root=temporary)

    def test_historical_housekeeping_is_separate_from_current_generation(self):
        historic = historical_housekeeping()
        self.assertEqual(historic["canonical"]["report_sha256"], "5a7e4a3e3d140869511afb6c1b5dc97dff07f3705791c1380175ac90896e24a6")
        self.assertNotIn("last_regeneration", historic)
        self.assertEqual(historic["retrieved_from"]["commit"], "5559da39533bf061149f0dd335719f52c18d3dfc")
        self.assertIn("historical housekeeping operation only", historic["interpretation_scope"])


if __name__ == "__main__":
    unittest.main()
