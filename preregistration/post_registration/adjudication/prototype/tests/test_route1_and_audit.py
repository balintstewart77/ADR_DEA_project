"""Synthetic checks only; this module does not open formal or restricted data."""
import csv
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_formal_import import (BLOCK_SIZE, SEED_PRIMARY_QUEUE, SEED_PRESENTATION,
                                 assignment_id, block_of, primary_queue)
from build_route1_component import component_values
from check_blocks import compare as compare_blocks
from draw_secondary_audit import SEED_ADJUDICATION_AUDIT, SEED_SECONDARY_QUEUE, draw, main, read_manifest
from preserve_block import (_choices, _label_vocabulary, check_block, required_columns, response_from_export,
                            snapshot, stage1_columns)
from prototype_lib import (BEST_CANNOT_DETERMINE, DOMAINS, PURPOSES, RULE_OTHER, comparative_components, default_valid_submission,
                           field_rows, rule_catalogue, validate_submission,
                           derive_stage1, generated_evidence, load_json, package_case,
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

    def test_block_is_preserved_only_when_complete_valid_unrevealed_and_verified(self):
        # Two datasets, so the displayed entry spans two lines as real ones do.
        case = {**load_json("cases.json")[0], "assignment_id": "ADJ_0001",
                "datasets": "Synthetic linked dataset one & Synthetic linked dataset two"}
        package = package_case(case)
        self.assertTrue(comparative_components(package))
        self.assertIn("\n", generated_evidence(package)["adj_case_datasets"])
        expected = reveal_fields(case, package)
        response = default_valid_submission(package)
        checkboxes = {c.split("___")[0] for c in stage1_columns() if "___" in c}
        choices = {r[0]: r[5] for r in field_rows()}

        def export_row(answers):
            # A raw export of every instrument: unticked checkboxes are "0",
            # generated fields come back with CRLF newlines, reveal is blank.
            row = {c: ("0" if "___" in c else "") for c in required_columns()}
            row.update({"adj_assignment_id": "ADJ_0001", "adj_source_record_id": case["record_id"],
                        "adj_reviewer_role": "1", "adj_stage1_package_id": package["package_id"],
                        "redcap_data_access_group": "primary", "adj_stage1_complete": "2",
                        **{k: str(v).replace("\n", "\r\n") for k, v in generated_evidence(package).items()}})
            for key, value in answers.items():
                if key in ("assignment_id", "package_id"): continue
                if key in checkboxes:
                    # REDCap stores a label checkbox as its choice code, never the name.
                    codes = {label: code for code, label in _choices(choices[key])}
                    for v in value: row[f"{key}___{codes.get(v, v)}"] = "1"
                else: row[key] = str(value)
            return row
        row = export_row(response)
        columns = sorted(row)
        reveal = [{"adj_assignment_id": "ADJ_0001", "adj_reveal_state": "1", **expected}]
        sources, packages, wanted = {"ADJ_0001": case["record_id"]}, {"ADJ_0001": package}, {"ADJ_0001": expected}

        def problems(changed=None, dropped=(), changed_reveal=None):
            r = {**row, **(changed or {})}
            return check_block([c for c in columns if c not in dropped], {"ADJ_0001": r}, sources, packages,
                               [{**reveal[0], **(changed_reveal or {})}], wanted)
        self.assertEqual(problems(), [])
        # REDCap's CSV export writes each stored line break as two spaces; that
        # exact substitution is accepted, any other change to the text is not.
        multiline = next(k for k, v in generated_evidence(package).items() if "\n" in str(v))
        as_exported = str(generated_evidence(package)[multiline]).replace("\n", "  ")
        self.assertEqual(problems({multiline: as_exported}), [])
        self.assertTrue(problems({multiline: as_exported.replace("  ", " ", 1)}))
        self.assertTrue(problems({multiline: as_exported + " extra"}))
        # The converted response is the one submitted, so the validator judges the real answers.
        self.assertEqual(response_from_export(row, generated_evidence(package)), response)

        self.assertTrue(problems({"adj_stage1_affirmed": ""}))
        self.assertTrue(problems({"adj_diff_check": "2"}))
        self.assertTrue(problems({"adj_reveal_state": "1"}))
        self.assertTrue(problems({reveal_columns()[0]: "production model"}))
        self.assertTrue(problems({"adj_dom_opt_a": "An option nobody generated"}))
        self.assertTrue(problems({"adj_stage1_package_id": "PKG_other"}))
        slot = next(c for c, v in expected.items() if v)
        self.assertTrue(problems(changed_reveal={slot: "coder C99"}))
        self.assertTrue(check_block(columns, {}, sources, packages, reveal, wanted))  # absent from export
        # Identity: the right source record, the primary role, the primary group.
        self.assertTrue(problems({"adj_source_record_id": "SYN_OTHER"}))
        self.assertTrue(problems({"adj_reviewer_role": "2"}))
        self.assertTrue(problems({"redcap_data_access_group": "secondary"}))
        # Schema: an export missing any answer column, or the Stage 2 form, is refused outright.
        comp = comparative_components(package)[0]
        self.assertTrue(problems(dropped=(f"adj_{comp}_best___1",)))
        self.assertTrue(problems(dropped=("adj_reveal_state",)))
        self.assertTrue(problems(dropped=("redcap_data_access_group",)))
        # Validation: answers REDCap accepted but the rules refuse are caught before the reveal.
        self.assertTrue(problems({f"adj_{comp}_best___{BEST_CANNOT_DETERMINE}": "1"}))  # cannot determine plus an option
        self.assertTrue(problems({f"adj_{comp}_evidence": ""}))
        self.assertTrue(problems({"adj_rule_conflict": "1"}))  # a conflict with no scope, rule or reason

        # A rule naming no label of its own (an assignment principle, or Other)
        # makes the reviewer tick the labels; REDCap stores their codes, the
        # validator reads names.  Both conflicts must survive the round trip.
        principle = next(r["code"] for r in rule_catalogue() if r["scope"] == "principle")
        dom_labels, purp_labels = [DOMAINS[2], DOMAINS[5]], [PURPOSES[3]]
        labelled = {**response, "adj_rule_conflict": 1, "adj_rule_conflict_scope": [1],
                    "adj_dom_conflict_slots": [1], "adj_conflict_rule_cited": principle,
                    "adj_dom_conflict_labels": dom_labels, "adj_rule_conflict_note": "Synthetic",
                    "adj_conflict_second": 1, "adj_conflict2_scope": [2], "adj_purp_conflict2_slots": [1],
                    "adj_conflict_rule2_cited": RULE_OTHER, "adj_conflict_rule2_other": "Synthetic rule",
                    "adj_purp_conflict2_labels": purp_labels, "adj_rule_conflict_note2": "Synthetic",
                    "adj_conflict_third": 0}
        self.assertEqual(validate_submission(labelled, package), [])
        labelled_row = export_row(labelled)
        self.assertEqual(labelled_row["adj_dom_conflict_labels___3"], "1")  # stored as a code
        back = response_from_export(labelled_row, generated_evidence(package))
        self.assertEqual(back, labelled)
        self.assertEqual(check_block(columns, {"ADJ_0001": labelled_row}, sources, packages, reveal, wanted), [])
        # Every Stage 1 label checkbox is decoded, and no other Stage 1 checkbox.
        decoded = {r[0] for r in field_rows() if r[1] == "adj_stage1" and r[3] == "checkbox" and _label_vocabulary(r[5])}
        self.assertEqual(decoded, {f"adj_{c}_conflict{n}_labels".replace("conflict1_", "conflict_")
                                   for c in ("dom", "purp") for n in range(1, 7)}
                         | {"adj_dom_additional_label_ids", "adj_purp_additional_label_ids"})

        # The snapshot carries the full Stage 1 column set, the response and its derivations.
        body = json.loads(snapshot({"ADJ_0001": row}, packages))["ADJ_0001"]
        self.assertEqual(sorted(body["stage1_columns"]), stage1_columns())
        self.assertFalse(set(body["stage1_columns"]) & set(reveal_columns() + ["adj_reveal_state"]))
        self.assertEqual(body["derived"], derive_stage1(response, package))
        self.assertIn(f"adj_{comp}_insufficient_support", body["derived"])
        self.assertEqual(snapshot({"ADJ_0001": row}, packages),
                         snapshot({"ADJ_0001": dict(reversed(list(row.items())))}, packages))

    def test_later_export_is_checked_against_every_snapshot(self):
        columns = ["adj_dom_best___1", "adj_stage1_note"]
        snapshots = {1: {"ADJ_0001": {"stage1_columns": {"adj_dom_best___1": "1", "adj_stage1_note": "a"}},
                         "ADJ_0002": {"stage1_columns": {"adj_dom_best___1": "0", "adj_stage1_note": ""}}}}
        rows = {"ADJ_0001": {"adj_dom_best___1": "1", "adj_stage1_note": "a", "adj_reveal_state": "1", "adj_stage2_affirmed": "1"},
                "ADJ_0002": {"adj_dom_best___1": "1", "adj_stage1_note": "", "adj_reveal_state": "1", "adj_stage2_affirmed": ""}}
        result = {aid: (changed, reveal, stage2) for _, aid, changed, reveal, stage2 in compare_blocks(rows, snapshots, columns)}
        self.assertEqual(result["ADJ_0001"], ([], "1", "1"))
        self.assertEqual(result["ADJ_0002"], (["adj_dom_best___1"], "1", ""))  # edited after preservation
        self.assertEqual(compare_blocks({}, snapshots, columns)[0][2], ["absent from export"])

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
