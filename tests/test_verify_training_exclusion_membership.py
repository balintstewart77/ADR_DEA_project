from __future__ import annotations

import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import verify_training_exclusion_membership as membership

KEYED = {"A1": "2019/004", "A2": "2020/021", "A3": "2024/019", "P2": "2022/073", "P4": "2025/039", "P5": "2022/042", "P6": "2021/065", "P7": "2025/251", "T1": "2021/113", "T3": "2021/007", "I1": "2020/003"}
DISCUSSION = {"I2": "2022/090"}
PILOTS = {"1": "2019/015", "2": "2021/038", "3": "2021/063", "4": "2021/103", "5": "2022/130", "6": "2024/248", "7": "2021/056", "8": "2022/034", "9": "2025/181", "10": "2025/027"}
CORRECT_BLINDING = (
    "assignment_id Visible: neutral opaque code identifying this assignment, e.g. A7K3M9Q2. "
    "project_title Visible, read-only: public register project title. "
    "datasets_used Visible, read-only: public register datasets-used entry. "
    "reviewer_id / coder_id Hidden: administrative reviewer linkage. "
    "record_id Hidden: stable source-record linkage. "
    "official_project_id Hidden: official register identifier. "
    "sample and stratum fields Hidden: sampling administration."
)


def make_docx(path: Path, cards: dict[str, str], discussion: dict[str, str], pilots: dict[str, str], summary: bool) -> None:
    parts = ['<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Worked examples</w:t></w:r></w:p>']
    parts += [f'<w:p><w:r><w:t>Example {card} Record ID: {record_id}</w:t></w:r></w:p>' for card, record_id in cards.items()]
    parts += [f'<w:p><w:r><w:t>Example {card} discussion card Record ID: {record_id}</w:t></w:r></w:p>' for card, record_id in discussion.items()]
    parts += ['<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Hidden pilot set</w:t></w:r></w:p>']
    parts += [f'<w:p><w:r><w:t>Pilot {number}: {record_id}</w:t></w:r></w:p>' for number, record_id in pilots.items()]
    if summary:
        ids = ", ".join([*cards.values(), *discussion.values(), *pilots.values()])
        parts += ['<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Exclusion set</w:t></w:r></w:p>', f'<w:p><w:r><w:t>IDs: {ids}</w:t></w:r></w:p>']
    parts += [f'<w:p><w:r><w:t>{CORRECT_BLINDING}</w:t></w:r></w:p>']
    xml = '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(parts) + '<w:sectPr/></w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def write_csv(path: Path, *, replacement: tuple[str, str] | None = None, role: tuple[str, str] | None = None, duplicate: bool = False, whitespace: bool = False) -> None:
    rows = ([{"record_id": item, "exclusion_group": "training", "use_in_materials": "Worked example"} for item in KEYED.values()] + [{"record_id": "2022/090", "exclusion_group": "training", "use_in_materials": "No-key discussion card"}] + [{"record_id": item, "exclusion_group": "pilot", "use_in_materials": "Pilot"} for item in PILOTS.values()])
    if replacement:
        for row in rows:
            if row["record_id"] == replacement[0]:
                row["record_id"] = replacement[1]
                break
    if role:
        for row in rows:
            if row["record_id"] == role[0]:
                row["exclusion_group"], row["use_in_materials"] = role[1], "Pilot"
                break
    if duplicate:
        rows[-1]["record_id"] = rows[-2]["record_id"]
    if whitespace:
        rows[0]["record_id"] += " "
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_id", "exclusion_group", "use_in_materials"])
        writer.writeheader(); writer.writerows(rows)


class MembershipTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(); root = Path(self.temp.name)
        self.trainer, self.coder, self.pilot, self.csv = root/"trainer.docx", root/"coder.docx", root/"pilot.docx", root/"exclusions.csv"
        make_docx(self.trainer, KEYED, DISCUSSION, PILOTS, True)
        make_docx(self.coder, KEYED, DISCUSSION, PILOTS, False)
        make_docx(self.pilot, {"A1": "2019/004"}, DISCUSSION, PILOTS, False)
        write_csv(self.csv)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def check(self) -> dict[str, object]:
        return membership.verify_membership(self.trainer, self.coder, self.pilot, self.csv)

    def test_equal_sets_pass(self) -> None:
        self.assertEqual(self.check()["counts"]["total_unique"], 22)

    def test_substituted_id_with_correct_count_fails(self) -> None:
        write_csv(self.csv, replacement=("2025/039", "2024/259"))
        with self.assertRaisesRegex(membership.MembershipError, "extra"):
            self.check()

    def test_trainer_coder_card_mismatch_fails(self) -> None:
        changed = dict(KEYED); changed["P4"] = "2024/259"
        make_docx(self.trainer, changed, DISCUSSION, PILOTS, True)
        with self.assertRaisesRegex(membership.MembershipError, "keyed-card mismatch"):
            self.check()

    def test_missing_taught_id_and_extra_stale_id_fail(self) -> None:
        write_csv(self.csv, replacement=("2025/251", "2021/090"))
        with self.assertRaisesRegex(membership.MembershipError, "missing"):
            self.check()

    def test_role_mismatch_fails(self) -> None:
        write_csv(self.csv, role=("2025/039", "pilot"))
        with self.assertRaisesRegex(membership.MembershipError, "Role mismatch"):
            self.check()

    def test_duplicate_fails(self) -> None:
        write_csv(self.csv, duplicate=True)
        with self.assertRaisesRegex(membership.MembershipError, "Duplicate"):
            self.check()

    def test_whitespace_fails(self) -> None:
        write_csv(self.csv, whitespace=True)
        with self.assertRaisesRegex(membership.MembershipError, "boundary-whitespace"):
            self.check()


class CoderBlindingTests(unittest.TestCase):
    def test_corrected_materials_pass(self) -> None:
        membership.verify_coder_blinding_text(CORRECT_BLINDING)

    def test_prohibited_encoded_assignment_example_fails(self) -> None:
        with self.assertRaisesRegex(membership.MembershipError, "prohibited encoded assignment"):
            membership.verify_coder_blinding_text(CORRECT_BLINDING + " baseline_C02_2024_123")

    def test_visible_record_id_language_fails(self) -> None:
        text = CORRECT_BLINDING.replace("record_id Hidden: stable source-record linkage", "record_id Visible: DEA project ID")
        with self.assertRaisesRegex(membership.MembershipError, "source Record ID described as visible"):
            membership.verify_coder_blinding_text(text)

    def test_visible_coder_id_language_fails(self) -> None:
        text = CORRECT_BLINDING.replace("reviewer_id / coder_id Hidden: administrative reviewer linkage", "coder_id Visible: your anonymised coder ID reviewer_id / coder_id Hidden")
        with self.assertRaisesRegex(membership.MembershipError, "coder/reviewer ID described as visible"):
            membership.verify_coder_blinding_text(text)

    def test_neutral_assignment_language_passes(self) -> None:
        membership.verify_coder_blinding_text(CORRECT_BLINDING.replace("A7K3M9Q2", "Q4N8Z2L7"))


if __name__ == "__main__":
    unittest.main()
