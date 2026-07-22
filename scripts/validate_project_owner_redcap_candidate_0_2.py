#!/usr/bin/env python3
"""Validate owner-redcap-candidate-0.2 entirely offline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping

import yaml

import build_project_owner_redcap_candidate as build01
import build_project_owner_redcap_candidate_0_2 as builder
import validate_project_owner_redcap_candidate as validate01


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TYPES = validate01.ALLOWED_TYPES
DIRECT_IDENTIFIERS = validate01.DIRECT_IDENTIFIERS
PROHIBITED_OWNER_TERMS = validate01.PROHIBITED_OWNER_TERMS
NEUTRAL_RECORD = validate01.NEUTRAL_RECORD
REAL_RECORD_ID = validate01.REAL_RECORD_ID
HEX64 = validate01.HEX64


class OwnerCandidate02Error(RuntimeError):
    pass


def parse_choices(value: str) -> dict[str, str]:
    return validate01.parse_choices(value)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dictionary(path: Path = builder.DICTIONARY) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != builder.HEADERS:
            raise OwnerCandidate02Error("dictionary columns differ from the ordered REDCap 18-column schema")
        return list(reader)


def _balanced_branch(value: str) -> bool:
    return value.count("(") == value.count(")")


def validate_dictionary(path: Path = builder.DICTIONARY) -> dict[str, object]:
    rows = load_dictionary(path)
    errors: list[str] = []
    names = [row["Variable / Field Name"] for row in rows]
    forms = Counter(row["Form Name"] for row in rows)
    by = {row["Variable / Field Name"]: row for row in rows}
    if len(names) != len(set(names)):
        errors.append("field names are not unique")
    if tuple(dict.fromkeys(row["Form Name"] for row in rows)) != builder.FORMS:
        errors.append("form order differs from the four-instrument contract")
    if dict(forms) != builder.FORM_COUNTS:
        errors.append(f"form counts differ: {dict(forms)}")
    if len(rows) != 167:
        errors.append(f"total field count differs: {len(rows)}")
    for row in rows:
        name = row["Variable / Field Name"]
        form = row["Form Name"]
        branch = row["Branching Logic (Show field only if...)"]
        if row["Field Type"] not in ALLOWED_TYPES:
            errors.append(f"unsupported field type: {name}")
        if not _balanced_branch(branch):
            errors.append(f"unbalanced branch: {name}")
        if form == "owner_contact_admin" and name not in {"owner_record_id", "record_type", "owner_id"}:
            if builder.CONTACT not in branch:
                errors.append(f"contact field lacks contact guard: {name}")
        if form == "project_owner_consent" and builder.CONTACT not in branch:
            errors.append(f"consent field lacks contact guard: {name}")
        if form in {"owner_assignment_admin", "project_owner_review"} and builder.ASSIGNMENT not in branch:
            errors.append(f"assignment/review field lacks assignment guard: {name}")
        if form != "owner_contact_admin" and row["Identifier?"]:
            errors.append(f"identifier outside restricted contact admin: {name}")
        if form in {"owner_assignment_admin", "project_owner_review"}:
            # Review wording may legitimately ask an owner to explain a
            # disagreement.  The prohibited leakage is administrative
            # metadata, so review variables are checked by name while
            # assignment-administration fields are also checked by wording.
            lowered = (
                " ".join((name, row["Field Label"], row["Field Note"])).lower()
                if form == "owner_assignment_admin"
                else name.lower()
            )
            if any(term in lowered for term in PROHIBITED_OWNER_TERMS):
                errors.append(f"prohibited scratch/sampling metadata leaked: {name}")
    if parse_choices(by["record_type"]["Choices, Calculations, OR Slider Labels"]) != {"1": "Contact", "2": "Assignment"}:
        errors.append("record_type choices differ")
    if "po_ack" in by:
        errors.append("candidate 0.2 retains the per-assignment participation acknowledgement")
    decision = by.get("pc_decision")
    if not decision:
        errors.append("one-time consent decision field is missing")
    else:
        if parse_choices(decision["Choices, Calculations, OR Slider Labels"]) != {
            "1": "Yes, I agree to take part", "0": "No, I do not wish to take part"
        }:
            errors.append("consent choices differ")
        required = (
            "I have read and understood the information provided, have had the opportunity "
            "to ask questions, and agree to take part"
        )
        if required not in decision["Field Label"] or decision["Required Field?"] != "y":
            errors.append("consent decision wording or required status differs")
    if by.get("pc_info_version", {}).get("Field Annotation") != "@READONLY":
        errors.append("participant-information version is not visible read-only metadata")
    calc = by.get("oc_link_eligible", {}).get("Choices, Calculations, OR Slider Labels", "")
    for required in (
        "[oc_eoi_status] = '2'", "[pc_decision] = '1'",
        f"[pc_info_version] = '{builder.CONSENT_INFO_VERSION}'",
        "[oc_reconsent_required] = '0'", "[oc_consent_withdrawal] = '0'",
        "[oc_contact_suppression] = '0'",
    ):
        if required not in calc:
            errors.append(f"link-eligibility calculation omits: {required}")
    intro = by.get("po_intro", {}).get("Field Label", "")
    if "previously agreed" not in intro.lower() or "remains voluntary" not in intro.lower():
        errors.append("review survey lacks the brief voluntary-participation reminder")
    if any(
        row["Form Name"] == "project_owner_review"
        and row["Field Type"] in {"radio", "yesno", "checkbox"}
        and "consent" in (row["Field Label"] + row["Field Note"]).lower()
        for row in rows
    ):
        errors.append("review survey contains a repeated consent question")
    if parse_choices(by["po_taxonomy_fit"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Fit", "2": "Partial Fit", "3": "No Fit"
    }:
        errors.append("owner taxonomy-fit choices differ")

    # Candidate 0.1 substantive review rows must differ only in the authorised
    # branch removal and the two reminder/privacy descriptions.
    with builder.V01_DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
        old = {row["Variable / Field Name"]: row for row in csv.DictReader(handle)}
    allowed_modified = {
        name for name, row in old.items() if row["Form Name"] == "project_owner_review"
    } | {"owner_link_release"}
    allowed_modified.discard("po_ack")
    for name in set(old) & set(by):
        if old[name] != by[name] and name not in allowed_modified:
            errors.append(f"unrelated candidate-0.1 field changed: {name}")
    if set(old) - set(by) != {"po_ack"}:
        errors.append(f"removed fields differ from consent design: {sorted(set(old) - set(by))}")
    added = set(by) - set(old)
    expected_added = {
        "oc_reconsent_required", "oc_consent_withdrawal", "oc_consent_withdraw_date",
        "oc_link_eligible", "pc_intro", "pc_reason", "pc_burden", "pc_scope",
        "pc_voluntary", "pc_data", "pc_withdrawal", "pc_contact", "pc_reference",
        "pc_info_version", "pc_decision", "pc_decline_end",
    }
    if added != expected_added:
        errors.append(f"added fields differ from consent design: {sorted(added ^ expected_added)}")
    if errors:
        raise OwnerCandidate02Error("\n".join(errors))
    return {"fields": len(rows), "forms": dict(forms), "version": builder.VERSION}


def _integer(value: object) -> int | None:
    return validate01._integer(value)


def current_consent(contact: Mapping[str, object] | None) -> bool:
    if contact is None:
        return False
    return (
        _integer(contact.get("oc_eoi_status")) == 2
        and _integer(contact.get("pc_decision")) == 1
        and contact.get("pc_info_version") == builder.CONSENT_INFO_VERSION
        and _integer(contact.get("oc_reconsent_required")) == 0
        and _integer(contact.get("oc_consent_withdrawal")) == 0
        and _integer(contact.get("oc_contact_suppression")) == 0
    )


def validate_contact(data: Mapping[str, object]) -> list[str]:
    errors = validate01.validate_contact(data)
    if _integer(data.get("oc_reconsent_required")) not in (0, 1):
        errors.append("re-consent-required status is invalid")
    withdrawal = _integer(data.get("oc_consent_withdrawal"))
    if withdrawal not in (0, 1, 2, 3):
        errors.append("consent-withdrawal status is invalid")
    if withdrawal in (1, 2, 3) and not data.get("oc_consent_withdraw_date"):
        errors.append("consent-withdrawal status requires a date")
    decision = _integer(data.get("pc_decision"))
    if decision is not None and decision not in (0, 1):
        errors.append("consent decision is invalid")
    if decision is not None and not data.get("pc_info_version"):
        errors.append("consent decision lacks participant-information version")
    if decision == 1 and data.get("oc_eoi_status") != 2:
        errors.append("consent recorded without affirmative expression of interest")
    return errors


def validate_assignment(
    data: Mapping[str, object],
    contacts: Mapping[str, Mapping[str, object]],
) -> list[str]:
    # Reuse the candidate-0.1 proposal, identifier and routing validator through
    # a narrow adapter; only version and the release gate differ.
    adapted = dict(data)
    adapted["instrument_ver"] = build01.VERSION
    adapted["owner_link_release"] = 0
    errors = validate01.validate_assignment(adapted, contacts)
    release = _integer(data.get("owner_link_release"))
    if release not in (0, 1, 2):
        errors.append("invalid assignment-link release code")
    contact = contacts.get(str(data.get("owner_id", "")))
    if release in (1, 2) and not current_consent(contact):
        errors.append("assignment link eligible or released without current affirmative consent")
    if release == 2 and not data.get("owner_invite_date"):
        errors.append("released assignment link requires an invitation date")
    if data.get("instrument_ver") != builder.VERSION:
        errors.append("assignment instrument version differs")
    return errors


def validate_response(
    response: Mapping[str, object],
    assignment: Mapping[str, object],
    *,
    strict: bool,
) -> list[str]:
    if "po_ack" in response:
        return ["review response contains removed repeated-consent field: po_ack"]
    adapted = dict(response)
    adapted["po_ack"] = 1
    return validate01.validate_response(adapted, assignment, strict=strict)


def analytically_complete(
    response: Mapping[str, object],
    assignment: Mapping[str, object],
    contacts: Mapping[str, Mapping[str, object]],
) -> bool:
    if not current_consent(contacts.get(str(assignment.get("owner_id", "")))):
        return False
    adapted = dict(response)
    adapted["po_ack"] = 1
    return validate01.analytically_complete(adapted, assignment)


def validate_fixtures(path: Path = builder.RESPONSE_FIXTURE) -> dict[str, int]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = path.read_text(encoding="utf-8") + builder.IMPORT_FIXTURE.read_text(encoding="utf-8")
    errors: list[str] = []
    if REAL_RECORD_ID.search(raw):
        errors.append("synthetic fixture contains a real-format DEA Record ID")
    if re.search(r"@(?!example\.invalid)", raw):
        errors.append("synthetic fixture contains a non-.invalid email")
    contacts: dict[str, Mapping[str, object]] = {}
    for row in payload["contacts"]:
        owner_id = str(row["owner_id"])
        if owner_id in contacts:
            errors.append("more than one consent/contact record for owner_id")
        contacts[owner_id] = row
        errors += [f"contact {owner_id}: {item}" for item in validate_contact(row)]
    assignments = {str(row["owner_record_id"]): row for row in payload["assignments"]}
    seen_assignment_ids: set[str] = set()
    owner_assignments: defaultdict[str, int] = defaultdict(int)
    for row in payload["assignments"]:
        errors += [
            f"assignment {row['owner_record_id']}: {item}"
            for item in validate_assignment(row, contacts)
        ]
        assignment_id = str(row["owner_assignment_id"])
        if assignment_id in seen_assignment_ids:
            errors.append("duplicate owner_assignment_id")
        seen_assignment_ids.add(assignment_id)
        owner_assignments[str(row["owner_id"])] += 1
    if max(owner_assignments.values(), default=0) < 2:
        errors.append("no consented owner links to several assignments")
    for row in payload["assignments"]:
        consent = current_consent(contacts.get(str(row["owner_id"])))
        release = _integer(row.get("owner_link_release"))
        if not consent and release != 0:
            errors.append("non-current consent fixture has an unblocked assignment")
    for case in payload["responses"]:
        assignment = assignments.get(str(case["owner_record_id"]))
        if assignment is None:
            errors.append(f"response has no assignment: {case['case_id']}")
            continue
        actual_errors = validate_response(
            case["data"], assignment, strict=bool(case["strict_validation"])
        )
        if (not actual_errors) != bool(case["expected_valid"]):
            errors.append(f"{case['case_id']} validity differs: {actual_errors}")
        actual_complete = analytically_complete(case["data"], assignment, contacts)
        if actual_complete != bool(case["expected_analytical_complete"]):
            errors.append(f"{case['case_id']} analytical completion differs")
    if errors:
        raise OwnerCandidate02Error("\n".join(errors))
    return {
        "contacts": len(contacts),
        "assignments": len(assignments),
        "responses": len(payload["responses"]),
    }


def check() -> dict[str, object]:
    if sha256_file(builder.V01_DICTIONARY) != builder.V01_SHA256:
        raise OwnerCandidate02Error("candidate-0.1 dictionary hash changed")
    if sha256_file(builder.SCRATCH_DICTIONARY) != builder.SCRATCH_SHA256:
        raise OwnerCandidate02Error("frozen scratch candidate-0.7 dictionary hash changed")
    return {
        "version": builder.VERSION,
        "dictionary": validate_dictionary(),
        "fixtures": validate_fixtures(),
        "status": "passed_offline_unfrozen",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    print(yaml.safe_dump(check(), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
