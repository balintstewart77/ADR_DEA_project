"""Whole-round preservation and the calibration comparison (ADJ-104), on synthetic fixtures only."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from compare_training import build, stage1  # noqa: E402
from preserve_block import _choices, check_block, required_columns, stage1_columns  # noqa: E402
from prototype_lib import (comparative_components, default_valid_submission, field_rows, generated_evidence,  # noqa: E402
                           load_json, package_case, reveal_fields)

CHOICES = {r[0]: r[5] for r in field_rows()}
CHECKBOXES = {c.split("___")[0] for c in stage1_columns() if "___" in c}


def export_row(case, package, group, role, answers):
    """A raw export row of every instrument, as REDCap writes it, for a comparative package."""
    row = {c: ("0" if "___" in c else "") for c in required_columns()}
    row.update({"adj_assignment_id": package["assignment_id"], "adj_source_record_id": case["record_id"],
                "adj_reviewer_role": role, "adj_stage1_package_id": package["package_id"],
                "redcap_data_access_group": group, "adj_stage1_complete": "2",
                **{k: str(v) for k, v in generated_evidence(package).items()}})
    for key, value in answers.items():
        if key in ("assignment_id", "package_id"):
            continue
        if key in CHECKBOXES:
            codes = {label: code for code, label in _choices(CHOICES[key])}
            for v in value:
                row[f"{key}___{codes.get(v, v)}"] = "1"
        else:
            row[key] = str(value)
    return row


class SecondaryTrainingTests(unittest.TestCase):
    def setUp(self):
        self.case = load_json("cases.json")[0]
        self.packages = {aid: package_case({**self.case, "assignment_id": aid}) for aid in ("TRN_S01", "TRN_P01")}
        self.comp = comparative_components(self.packages["TRN_S01"])[0]

    def test_each_record_is_checked_against_its_own_group_and_role(self):
        package = self.packages["TRN_S01"]
        case = {**self.case, "assignment_id": "TRN_S01"}
        row = export_row(self.case, package, "secondary", "2", default_valid_submission(package))
        reveal = [{"adj_assignment_id": "TRN_S01", "adj_reveal_state": "1", **reveal_fields(case, package)}]
        args = (sorted(row), {"TRN_S01": row}, {"TRN_S01": self.case["record_id"]}, {"TRN_S01": package},
                reveal, {"TRN_S01": reveal_fields(case, package)})
        self.assertEqual(check_block(*args, assignments={"TRN_S01": ("secondary", "2")}), [])
        self.assertTrue(check_block(*args))  # without assignments, a secondary record is refused
        self.assertTrue(check_block(*args, assignments={"TRN_S01": ("primary", "2")}))
        self.assertTrue(check_block(*args, assignments={"TRN_S01": ("secondary", "1")}))

    def test_answers_are_compared_by_classification_not_letter(self):
        rows = {}
        for aid, group, role in (("TRN_S01", "secondary", "2"), ("TRN_P01", "primary", "1")):
            package = self.packages[aid]
            rows[aid] = export_row(self.case, package, group, role, default_valid_submission(package))
        shown = {aid: {n: generated_evidence(p)[f"adj_{self.comp}_opt_{L}"] for n, L in enumerate("abcd", 1)
                       if generated_evidence(p).get(f"adj_{self.comp}_opt_{L}")} for aid, p in self.packages.items()}
        target = shown["TRN_S01"][1]  # the classification the secondary saw as Option A
        p_code = next(n for n, text in shown["TRN_P01"].items() if text == target)
        for aid, code in (("TRN_S01", 1), ("TRN_P01", p_code)):
            for n in range(1, 5):
                rows[aid][f"adj_{self.comp}_best___{n}"] = "1" if n == code else "0"
        s, p = stage1(rows["TRN_S01"]), stage1(rows["TRN_P01"])
        self.assertEqual(s["components"][self.comp]["best"], p["components"][self.comp]["best"])
        if p_code != 1:  # the same letter on the other record is a different classification
            rows["TRN_P01"][f"adj_{self.comp}_best___{p_code}"] = "0"
            rows["TRN_P01"][f"adj_{self.comp}_best___1"] = "1"
            self.assertNotEqual(s["components"][self.comp]["best"], stage1(rows["TRN_P01"])["components"][self.comp]["best"])

    def test_report_pairs_shared_cases_and_flags_changes_after_preservation(self):
        rows = {aid: export_row(self.case, p, g, r, default_valid_submission(p))
                for (aid, p), (g, r) in zip(self.packages.items(), (("secondary", "2"), ("primary", "1")))}
        snapshot = {aid: {"stage1_columns": {c: row.get(c, "") for c in stage1_columns()}} for aid, row in rows.items()}
        crosswalk = [{"adj_assignment_id": "TRN_S01", "group": "secondary", "source_record_id": self.case["record_id"], "set_role": "shared calibration"},
                     {"adj_assignment_id": "TRN_P01", "group": "primary", "source_record_id": self.case["record_id"], "set_role": "shared calibration"}]
        final = {aid: {**row, "adj_stage2_closure": "1", "adj_f1_family": "6"} for aid, row in rows.items()}
        report, counts = build(snapshot, final, crosswalk)
        self.assertEqual(counts, {"shared": 1, "practice": 0, "changed_after_preservation": 0})
        self.assertIn("Shared 1 (TRN_S01 / TRN_P01)", report)
        final["TRN_S01"]["adj_stage1_note"] = "Changed after the reveal"
        self.assertEqual(build(snapshot, final, crosswalk)[1]["changed_after_preservation"], 1)


if __name__ == "__main__":
    unittest.main()
