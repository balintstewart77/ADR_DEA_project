"""Targeted mutation checks for concrete collation risks; no output files."""
import copy
import unittest
from unittest.mock import patch

from .preflight import Fatal, Sources, TAGS
from .report import Report, esc, unresolved_explanation_rollup


class CollationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = Sources({})
        cls.sources.load()

    def fresh(self):
        return copy.deepcopy(self.sources)

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
        r = Report(s)
        t = r.new_table(2, "Synthetic policy test", "baseline", TAGS[0])
        source = s.lookup("tag_diagnostics", population="baseline", tag=TAGS[0])
        item = r.add(t, "tag_diagnostics", source, "cohen_kappa")
        self.assertEqual(item["displayed_estimate"], source["cohen_kappa"])
        self.assertEqual(item["estimate_status"], "reported")
        self.assertIn("RARE", item["support_display"])

    def test_withholding_cannot_leak_into_second_table(self):
        s = self.fresh()
        r = Report(s)
        source = next(x for x in s.tables["per_label_contingencies"] if x["support_band"] == "RARE")
        for _ in range(2):
            t = r.new_table(5, "Synthetic withholding test", "baseline", source["dimension"])
            item = r.add(t, "per_label_contingencies", source, "kappa", force_withheld=True)
            self.assertEqual([item[k] for k in ("displayed_estimate", "displayed_lower", "displayed_upper")], ["", "", ""])
            self.assertEqual(item["estimate_status"], "withheld_support_rule")
        self.assertFalse(any(x["field"] == "kappa.interval" for x in s.unresolved))

    def test_zero_false_and_missing_remain_distinct(self):
        s = self.fresh()
        r = Report(s)
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
        r = Report(s)
        r.build()
        document = r.render()
        self.assertEqual(len(s.unresolved), 69)
        self.assertEqual(len({item["id"] for item in s.unresolved}), 69)
        self.assertIn("Every hard-case record belongs to one of three 25-record strata", document)
        self.assertIn("supplementary 95% Wilson-score intervals calculated on 7 September 2026", document)
        self.assertIn("Dated audit evidence annotations — 2026-09-14", document)
        self.assertIn("U0005 remains open pending review of the historical documentation", document)
        followup = r.meta["reporting_followup"]
        self.assertEqual(followup["ledger"], {"checks": 3496, "verified": 3488, "discrepant": 3, "blocked": 3, "not_checked": 2})
        self.assertEqual(followup["original_unresolved_entries_retained"], 69)


if __name__ == "__main__":
    unittest.main()
