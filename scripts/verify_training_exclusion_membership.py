#!/usr/bin/env python3
"""Verify exact training/discussion/pilot exclusion membership offline."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NS}
RECORD_ID_RE = re.compile(r"(?<![0-9/])20\d{2}/\d{3}(?:/[a-z])?(?![0-9/])")
RECORD_ID_FULL_RE = re.compile(r"20\d{2}/\d{3}(?:/[a-z])?\Z")
EXAMPLE_RE = re.compile(r"\bExample\s+([APTIS]\d+)\b", re.IGNORECASE)
PILOT_RE = re.compile(r"\bPilot\s+(\d+)\s*:\s*(20\d{2}/\d{3}(?:/[a-z])?)\b")


class MembershipError(ValueError):
    """Raised when document and CSV membership does not agree."""


@dataclass(frozen=True)
class Block:
    location: str
    section: str
    text: str


@dataclass(frozen=True)
class DocumentCards:
    path: Path
    keyed_cards: dict[str, str]
    discussion_cards: dict[str, str]
    pilots: dict[str, str]
    exclusion_summary_ids: set[str]

    @property
    def keyed_ids(self) -> set[str]:
        return set(self.keyed_cards.values())

    @property
    def discussion_ids(self) -> set[str]:
        return set(self.discussion_cards.values())

    @property
    def pilot_ids(self) -> set[str]:
        return set(self.pilots.values())


def _text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(".//w:t", NS)).strip()


def _style(element: ET.Element) -> str:
    style = element.find("./w:pPr/w:pStyle", NS)
    return style.get(f"{{{WORD_NS}}}val", "") if style is not None else ""


def iter_document_blocks(path: Path) -> list[Block]:
    """Return paragraphs and table rows in document-body order."""
    try:
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise MembershipError(f"Cannot parse DOCX {path}: {exc}") from exc
    body = root.find("w:body", NS)
    if body is None:
        raise MembershipError(f"DOCX has no document body: {path}")
    blocks: list[Block] = []
    section = ""
    for index, child in enumerate(body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _text(child)
            if _style(child).lower().startswith("heading") and text:
                section = text
            blocks.append(Block(f"paragraph:{index}", section, text))
        elif tag == "tbl":
            for row_index, row in enumerate(child.findall("./w:tr", NS)):
                cells = [_text(cell) for cell in row.findall("./w:tc", NS)]
                blocks.append(Block(f"table:{index}:row:{row_index}", section, " | ".join(cells)))
    return blocks


def _validate_record_id(record_id: str, source: str) -> None:
    if not record_id or record_id != record_id.strip():
        raise MembershipError(f"Blank or boundary-whitespace Record ID in {source}: {record_id!r}")
    if RECORD_ID_FULL_RE.fullmatch(record_id) is None:
        raise MembershipError(f"Malformed Record ID in {source}: {record_id!r}")
    if any(ord(character) <= 31 or ord(character) == 127 or character == "\u00a0" for character in record_id):
        raise MembershipError(f"Control character in Record ID in {source}: {record_id!r}")


def _single_card_id(block: Block, card: str) -> str:
    ids = RECORD_ID_RE.findall(block.text)
    if len(ids) != 1:
        raise MembershipError(f"{card} at {block.location} must contain exactly one Record ID; found {ids}")
    _validate_record_id(ids[0], f"{card} at {block.location}")
    return ids[0]


def extract_document_cards(path: Path, *, require_cards: bool = True) -> DocumentCards:
    """Extract designated Example/Pilot cards and trainer exclusion-summary IDs."""
    keyed: dict[str, str] = {}
    discussion: dict[str, str] = {}
    pilots: dict[str, str] = {}
    summary_ids: set[str] = set()
    for block in iter_document_blocks(path):
        for match in EXAMPLE_RE.finditer(block.text):
            card = match.group(1).upper()
            record_id = _single_card_id(block, card)
            target = discussion if "discussion card" in block.text.lower() else keyed
            if card in target and target[card] != record_id:
                raise MembershipError(f"Conflicting {card} IDs in {path}: {target[card]} vs {record_id}")
            target[card] = record_id
        if "pilot" in block.section.lower():
            for match in PILOT_RE.finditer(block.text):
                card, record_id = f"Pilot {match.group(1)}", match.group(2)
                _validate_record_id(record_id, f"{card} at {block.location}")
                if card in pilots and pilots[card] != record_id:
                    raise MembershipError(f"Conflicting {card} IDs in {path}: {pilots[card]} vs {record_id}")
                pilots[card] = record_id
        if "exclusion set" in block.section.lower() or "exclusion-summary" in block.section.lower():
            for record_id in RECORD_ID_RE.findall(block.text):
                _validate_record_id(record_id, f"exclusion summary at {block.location}")
                summary_ids.add(record_id)
    if require_cards and (not keyed or not discussion):
        raise MembershipError(f"Missing designated worked-example/discussion cards in {path}")
    return DocumentCards(path, keyed, discussion, pilots, summary_ids)


def read_exclusion_csv(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "record_id" not in rows[0] or "exclusion_group" not in rows[0]:
        raise MembershipError(f"Exclusion CSV lacks record_id/exclusion_group columns: {path}")
    roles: dict[str, str] = {}
    for row_number, row in enumerate(rows, start=2):
        record_id = row.get("record_id", "")
        _validate_record_id(record_id, f"{path}:{row_number}")
        group = row.get("exclusion_group", "").strip().lower()
        materials = row.get("use_in_materials", "").strip().lower()
        role = "pilot" if group == "pilot" else "unkeyed_discussion" if group == "training" and "discussion" in materials else "keyed_worked_example" if group == "training" else ""
        if not role:
            raise MembershipError(f"Unknown exclusion role at {path}:{row_number}: {group!r}")
        if record_id in roles:
            raise MembershipError(f"Duplicate Record ID in exclusion CSV: {record_id}")
        roles[record_id] = role
    return roles


def _differences(name: str, actual: set[str], expected: set[str]) -> list[str]:
    messages = []
    if expected - actual:
        messages.append(f"{name} missing: {sorted(expected - actual)}")
    if actual - expected:
        messages.append(f"{name} extra: {sorted(actual - expected)}")
    return messages


def verify_membership(
    trainer_path: Path, coder_path: Path, pilot_reference_path: Path,
    exclusion_path: Path, cleaned_register_path: Path | None = None,
) -> dict[str, object]:
    trainer, coder, pilot = (
        extract_document_cards(trainer_path),
        extract_document_cards(coder_path),
        extract_document_cards(pilot_reference_path, require_cards=False),
    )
    csv_roles = read_exclusion_csv(exclusion_path)
    errors: list[str] = []
    if trainer.keyed_cards != coder.keyed_cards:
        errors.append(f"trainer/coder keyed-card mismatch: trainer={trainer.keyed_cards}; coder={coder.keyed_cards}")
    if trainer.discussion_cards != coder.discussion_cards:
        errors.append(f"trainer/coder discussion-card mismatch: trainer={trainer.discussion_cards}; coder={coder.discussion_cards}")
    if trainer.pilots != pilot.pilots:
        errors.append(f"trainer/pilot-reference mismatch: trainer={trainer.pilots}; pilot_reference={pilot.pilots}")
    keyed_ids, discussion_ids, pilot_ids = trainer.keyed_ids, trainer.discussion_ids, trainer.pilot_ids
    if (len(keyed_ids), len(discussion_ids), len(pilot_ids)) != (11, 1, 10):
        errors.append(f"Expected 11 keyed + 1 discussion + 10 pilot IDs; found {len(keyed_ids)} + {len(discussion_ids)} + {len(pilot_ids)}")
    if (keyed_ids | discussion_ids) & pilot_ids:
        errors.append(f"Training/discussion and pilot overlap: {sorted((keyed_ids | discussion_ids) & pilot_ids)}")
    expected_roles = {**{item: "keyed_worked_example" for item in keyed_ids}, **{item: "unkeyed_discussion" for item in discussion_ids}, **{item: "pilot" for item in pilot_ids}}
    expected_ids = set(expected_roles)
    errors.extend(_differences("exclusion CSV", set(csv_roles), expected_ids))
    errors.extend(_differences("trainer exclusion summary", trainer.exclusion_summary_ids, expected_ids))
    for record_id in sorted(expected_ids & set(csv_roles)):
        if csv_roles[record_id] != expected_roles[record_id]:
            errors.append(f"Role mismatch for {record_id}: CSV={csv_roles[record_id]}, document={expected_roles[record_id]}")
    if cleaned_register_path is not None:
        with cleaned_register_path.open(encoding="utf-8-sig", newline="") as handle:
            register = list(csv.DictReader(handle))
        valid = {value for row in register for value in (row.get("Record ID", ""), row.get("Project ID", ""))}
        errors.extend(_differences("cleaned register", valid & expected_ids, expected_ids))
    if errors:
        raise MembershipError("\n".join(errors))
    return {
        "status": "passed",
        "counts": {"keyed_worked_examples": len(keyed_ids), "unkeyed_discussion": len(discussion_ids), "pilot": len(pilot_ids), "total_unique": len(expected_ids)},
        "keyed_cards": trainer.keyed_cards, "discussion_cards": trainer.discussion_cards,
        "pilots": trainer.pilots, "exclusion_ids": sorted(expected_ids),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify exact training/pilot exclusion membership offline.")
    parser.add_argument("--trainer-docx", type=Path, required=True)
    parser.add_argument("--coder-docx", type=Path, required=True)
    parser.add_argument("--pilot-reference", type=Path, required=True)
    parser.add_argument("--exclusion-csv", type=Path, required=True)
    parser.add_argument("--cleaned-register", type=Path)
    parser.add_argument("--check", action="store_true", help="Verify only; write no output artefact.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_membership(args.trainer_docx, args.coder_docx, args.pilot_reference, args.exclusion_csv, args.cleaned_register)
    except (MembershipError, OSError, zipfile.BadZipFile) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
