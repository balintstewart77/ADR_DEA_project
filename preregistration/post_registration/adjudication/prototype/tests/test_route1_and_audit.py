"""Synthetic checks only; this module does not open formal or restricted data."""
import csv
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_formal_import import (BLOCK_SIZE, SEED_PRIMARY_QUEUE, SEED_PRESENTATION,
                                 assignment_id, block_of, primary_queue)
from build_route1_component import component_values
from draw_secondary_audit import SEED_ADJUDICATION_AUDIT, SEED_SECONDARY_QUEUE, draw, main, read_manifest
from preserve_block import check_block, snapshot, stage1_columns
from prototype_lib import (DOMAINS, PURPOSES, generated_evidence, load_json, package_case,
                           reveal_columns, reveal_fields)


class Route1AndAuditTests(unittest.TestCase):
    def test_route1_uses_model_difference_not_displayed_split_for_stratum(self):
        def classification(kind, domain, purpose):
            return {"source_type": kind, "domains": [domain], "purposes": [purpose],
                    "covid": "Not applied", "equity": "Not applied"}
        case = {"record_id": "SYN_ROUTE1", "assignment_id": "SYN_ROUTE1",
                "classifications": [classification("fable", DOMAINS[0], PURPOSES[0]),
                                    classification("scratch", DOMAINS[1], PURPOSES[0]),
                                    classification("scratch", DOMAINS[2], PURPOSES[0]),
                                    classification("scratch", DOMAINS[3], PURPOSES[1])]}
        row = component_values(case, package_case(case))
        self.assertEqual(row["route1_eligible"], 1)
        self.assertEqual(row["route1_components"], "dom")
        self.assertEqual(row["no_majority_components"], "dom")
        self.assertEqual(row["displayed_differing_components"], "dom;purp")
        self.assertEqual(row["stratum"], 3)
        case["classifications"][0]["purposes"] = []
        blocked = component_values(case, package_case(case))
        self.assertEqual((blocked["qa_flagged"], blocked["route1_eligible"]), (1, 0))

    def test_primary_queue_is_seeded_and_blocks_are_consecutive_ids(self):
        ids = [f"SYN_{i:03d}" for i in range(12)]
        order = primary_queue(ids)
        self.assertEqual(order, primary_queue(list(reversed(ids))))  # input order cannot matter
        self.assertEqual(sorted(order), sorted(ids))
        self.assertNotEqual(order, sorted(ids))
        self.assertNotEqual(order, primary_queue(ids, seed=SEED_PRIMARY_QUEUE + 1))
        self.assertEqual([assignment_id(p) for p in (1, 186)], ["ADJ_0001", "ADJ_0186"])
        self.assertEqual(BLOCK_SIZE, 5)
        self.assertEqual([block_of(p) for p in (1, 5, 6, 185, 186)], [1, 1, 2, 37, 38])
        # Four distinct seeds: presentation, primary queue, audit draw, secondary queue.
        self.assertEqual(len({SEED_PRESENTATION, SEED_PRIMARY_QUEUE, SEED_ADJUDICATION_AUDIT, SEED_SECONDARY_QUEUE}), 4)

    def test_block_is_preserved_only_when_affirmed_unrevealed_and_verified(self):
        case = {**load_json("cases.json")[0], "assignment_id": "ADJ_0001"}
        package = package_case(case)
        expected = reveal_fields(case, package)
        # A raw export: generated fields with CRLF newlines, as REDCap may return them.
        row = {"adj_assignment_id": "ADJ_0001", "adj_stage1_package_id": package["package_id"],
               "adj_stage1_affirmed": "1", "adj_diff_check": "1", "adj_reveal_state": "",
               "adj_dom_best___1": "1", "adj_dom_best___2": "0",
               **{c: "" for c in reveal_columns()},
               **{k: str(v).replace("\n", "\r\n") for k, v in generated_evidence(package).items()}}
        reveal = [{"adj_assignment_id": "ADJ_0001", "adj_reveal_state": "1", **expected}]
        packages, wanted = {"ADJ_0001": package}, {"ADJ_0001": expected}
        self.assertEqual(check_block({"ADJ_0001": row}, packages, reveal, wanted), [])

        def fails(changed_row=None, changed_reveal=None):
            return check_block({"ADJ_0001": {**row, **(changed_row or {})}}, packages,
                               [{**reveal[0], **(changed_reveal or {})}], wanted)
        self.assertTrue(fails({"adj_stage1_affirmed": ""}))
        self.assertTrue(fails({"adj_diff_check": "2"}))
        self.assertTrue(fails({"adj_reveal_state": "1"}))
        self.assertTrue(fails({reveal_columns()[0]: "production model"}))
        self.assertTrue(fails({"adj_dom_opt_a": "An option nobody generated"}))
        self.assertTrue(fails({"adj_stage1_package_id": "PKG_other"}))
        slot = next(c for c, v in expected.items() if v)
        self.assertTrue(fails(changed_reveal={slot: "coder C99"}))
        self.assertTrue(check_block({}, packages, reveal, wanted))  # record absent from export
        no_stage2 = {k: v for k, v in row.items() if k != "adj_reveal_state"}
        self.assertTrue(check_block({"ADJ_0001": no_stage2}, packages, reveal, wanted))

        # The snapshot keeps Stage 1 and admin fields, checkbox codes included, and no reveal field.
        columns = stage1_columns(list(row))
        self.assertIn("adj_dom_best___1", columns)
        self.assertIn("adj_stage1_affirmed", columns)
        self.assertFalse(set(columns) & set(reveal_columns() + ["adj_reveal_state"]))
        self.assertEqual(snapshot({"ADJ_0001": row}, columns), snapshot({"ADJ_0001": dict(reversed(list(row.items())))}, columns))

    def test_audit_is_deterministic_and_overlap_keeps_full_random_draw(self):
        rows = [{"source_record_id": f"SYN_{i:02d}", "completed_primary": "1",
                 "apparent_production_model_rule_problem": "0", "unresolved_finding": "0",
                 "release_implications": ""} for i in range(10)]
        universe, random_ids, mandatory_ids, result = draw(rows)
        self.assertEqual(len(universe), 10)
        self.assertEqual(len(random_ids), 2)
        self.assertFalse(mandatory_ids)
        overlap = next(iter(random_ids))
        extra = next(r["source_record_id"] for r in rows if r["source_record_id"] not in random_ids)
        for row in rows:
            if row["source_record_id"] == overlap:
                row["unresolved_finding"] = "1"
            if row["source_record_id"] == extra:
                row["release_implications"] = "taxonomy revision"
        first = draw(rows)
        second = draw(rows)
        self.assertEqual(first, second)
        self.assertEqual(first[1], random_ids)
        self.assertEqual(first[2], {overlap, extra})
        self.assertEqual(len(first[3]), 3)
        self.assertEqual(sum(r["random_draw"] for r in first[3]), 2)
        self.assertEqual(sum(r["mandatory_review"] for r in first[3]), 2)
        rows[0]["completed_primary"] = "0"
        self.assertEqual(len(draw(rows)[0]), 9)

    def test_audit_refuses_absent_or_empty_manifest(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic_manifest.csv"
            with self.assertRaises(ValueError):
                read_manifest(path)
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(("source_record_id", "completed_primary",
                                        "apparent_production_model_rule_problem",
                                        "unresolved_finding", "release_implications"))
            with self.assertRaises(ValueError):
                read_manifest(path)
            with path.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(("SYN_VALID", "1", "0", "0", "2"))
            self.assertEqual(read_manifest(path)[0]["source_record_id"], "SYN_VALID")

    def test_audit_mandatory_flags_and_zero_completed_primary(self):
        rows = [{"source_record_id": f"SYN_{i}", "completed_primary": "1",
                 "apparent_production_model_rule_problem": "0", "unresolved_finding": "0",
                 "release_implications": ""} for i in range(6)]
        rows[0]["apparent_production_model_rule_problem"] = "1"
        rows[1]["release_implications"] = "2"
        rows[2]["release_implications"] = "3"
        rows[3]["release_implications"] = "5"
        rows[4]["unresolved_finding"] = "1"
        self.assertEqual(draw(rows)[2], {f"SYN_{i}" for i in range(5)})
        for row in rows:
            row["completed_primary"] = "0"
        universe, random_ids, mandatory_ids, result = draw(rows)
        self.assertEqual((universe, random_ids, mandatory_ids, result), ([], set(), set(), []))


if __name__ == "__main__":
    unittest.main()
