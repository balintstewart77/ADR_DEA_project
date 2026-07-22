#!/usr/bin/env python3
"""Offline validator for owner-redcap-candidate-0.1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import build_project_owner_redcap_candidate as builder  # noqa: E402


ALLOWED_TYPES = {"text", "notes", "radio", "dropdown", "checkbox", "yesno", "descriptive", "calc", "slider", "file", "signature", "truefalse"}
NEUTRAL_RECORD = re.compile(r"^[A-Z0-9]{8}$")
REAL_RECORD_ID = re.compile(r"\b20\d{2}/\d{3}\b")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DIRECT_IDENTIFIERS = {"oc_name", "oc_email", "oc_affiliation", "oc_contact_issue_note", "oc_ack_name", "oc_ack_affiliation", "oc_ack_permission_source"}
PROHIBITED_OWNER_TERMS = {"sample_set", "hard_stratum", "reserve", "scratch", "adjudication", "disagreement"}


class OwnerCandidateError(RuntimeError):
    pass


def parse_choices(value: str) -> dict[str, str]:
    if not value:
        return {}
    result: dict[str, str] = {}
    for part in value.split(" | "):
        code, label = part.split(", ", 1)
        if code in result:
            raise OwnerCandidateError(f"duplicate choice code {code}")
        result[code] = label
    return result


def load_dictionary(path: Path = builder.DICTIONARY) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != builder.HEADERS:
            raise OwnerCandidateError("dictionary does not have the ordered 18-column REDCap header")
        rows = list(reader)
    return rows


def _balanced_branch(value: str) -> bool:
    return value.count("[") == value.count("]") and value.count("(") == value.count(")")


def validate_dictionary(path: Path = builder.DICTIONARY) -> dict[str, object]:
    rows = load_dictionary(path)
    errors: list[str] = []
    names = [row["Variable / Field Name"] for row in rows]
    counts = Counter(row["Form Name"] for row in rows)
    if len(rows) != 152:
        errors.append(f"expected 152 fields, found {len(rows)}")
    if dict(counts) != builder.FORM_COUNTS:
        errors.append(f"form counts differ: {dict(counts)}")
    if tuple(dict.fromkeys(row["Form Name"] for row in rows)) != builder.FORMS:
        errors.append("form order differs")
    if len(names) != len(set(names)):
        errors.append("field names are not unique")
    if not rows or names[0] != "owner_record_id":
        errors.append("neutral owner_record_id is not the REDCap record key")
    for row in rows:
        name = row["Variable / Field Name"]
        form = row["Form Name"]
        branch = row["Branching Logic (Show field only if...)"]
        if row["Field Type"] not in ALLOWED_TYPES:
            errors.append(f"invalid field type: {name}")
        try:
            parse_choices(row["Choices, Calculations, OR Slider Labels"])
        except (ValueError, OwnerCandidateError) as exc:
            errors.append(f"invalid choices for {name}: {exc}")
        if branch and not _balanced_branch(branch):
            errors.append(f"unbalanced branching syntax: {name}")
        if form == "owner_contact_admin" and name not in {"owner_record_id", "record_type", "owner_id"} and builder.CONTACT not in branch:
            errors.append(f"contact field lacks contact guard: {name}")
        if form == "owner_assignment_admin" and builder.ASSIGNMENT not in branch:
            errors.append(f"assignment field lacks assignment guard: {name}")
        if form == "project_owner_review":
            if builder.ASSIGNMENT not in branch:
                errors.append(f"review field lacks assignment guard: {name}")
            if name not in {"po_intro", "po_privacy", "po_ack"} and "[po_ack] = '1'" not in branch:
                errors.append(f"substantive review field lacks acknowledgement guard: {name}")
        if form != "owner_contact_admin" and row["Identifier?"]:
            errors.append(f"direct identifier outside contact admin: {name}")
        if form in {"owner_assignment_admin", "project_owner_review"}:
            for term in PROHIBITED_OWNER_TERMS:
                if term in name.lower() or (form == "owner_assignment_admin" and term in row["Field Label"].lower()):
                    errors.append(f"prohibited metadata field {term} in {name}")
    actual_identifiers = {row["Variable / Field Name"] for row in rows if row["Identifier?"] == "y"}
    if actual_identifiers != DIRECT_IDENTIFIERS:
        errors.append(f"direct identifier set differs: {sorted(actual_identifiers)}")

    by = {row["Variable / Field Name"]: row for row in rows}
    if parse_choices(by["record_type"]["Choices, Calculations, OR Slider Labels"]) != {"1": "Contact", "2": "Assignment"}:
        errors.append("record_type choices differ")
    if parse_choices(by["po_quote_permission"]["Choices, Calculations, OR Slider Labels"]) != {"1": "Yes", "0": "No", "2": "Please contact me before using a quotation"}:
        errors.append("quotation permission choices differ")
    if by["po_quote_permission"]["Required Field?"]:
        errors.append("quotation permission must remain optional")
    if parse_choices(by["po_taxonomy_fit"]["Choices, Calculations, OR Slider Labels"]) != {"1": "Fit", "2": "Partial Fit", "3": "No Fit"}:
        errors.append("owner taxonomy-fit choices differ")
    for stem in ("t01", "t02"):
        correct = by[f"po_{stem}_correct"]
        determinable = by[f"po_{stem}_det"]
        if parse_choices(correct["Choices, Calculations, OR Slider Labels"]) != {"1": "Yes", "0": "No", "2": "Unsure"}:
            errors.append(f"{stem} correctness choices differ")
        if parse_choices(determinable["Choices, Calculations, OR Slider Labels"]) != {"1": "Yes", "2": "Partly", "0": "No", "3": "Unsure"}:
            errors.append(f"{stem} determinability choices differ")
        if "fit" in correct["Field Label"].lower() or "does not fit" in correct["Choices, Calculations, OR Slider Labels"].lower():
            errors.append(f"negative tag uses fit wording: {stem}")
        if f"[prop_{stem}:label]" not in by[f"po_{stem}_label"]["Field Label"]:
            errors.append(f"{stem} proposal status is not piped")
    for prefix, maximum in (("d", 12), ("p", 8)):
        for index in range(1, maximum + 1):
            stem = f"{prefix}{index:02d}"
            flag = f"prop_{stem}"
            for suffix in ("label", "fit", "vis"):
                if f"[{flag}] = '1'" not in by[f"po_{stem}_{suffix}"]["Branching Logic (Show field only if...)"]:
                    errors.append(f"unused-slot guard missing: po_{stem}_{suffix}")
    if builder.WITHDRAWAL_WORDING not in by["po_privacy"]["Field Label"]:
        errors.append("approved withdrawal wording differs")
    if "{{DASHBOARD_URL}}" not in by["po_intro"]["Field Label"] or "{{STUDY_EMAIL}}" not in by["po_privacy"]["Field Label"]:
        errors.append("required configuration placeholders are absent")
    if sha256_file(builder.SCRATCH_DICTIONARY) != builder.SCRATCH_SHA256:
        errors.append("frozen scratch candidate-0.7 dictionary changed")
    if errors:
        raise OwnerCandidateError("\n".join(errors))
    return {"fields": len(rows), "forms": dict(counts), "version": builder.VERSION}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_contact(data: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    if data.get("record_type") != 1:
        errors.append("contact record_type must equal 1")
    if not NEUTRAL_RECORD.fullmatch(str(data.get("owner_record_id", ""))):
        errors.append("contact record key is not neutral opaque")
    for name in ("owner_id", "oc_name", "oc_contact_source", "oc_contactability", "oc_eligible_projects", "oc_projects_offered", "oc_minutes_per_project", "oc_est_total_minutes", "oc_eoi_status", "oc_contact_suppression", "oc_recruit_route", "oc_ack_permission"):
        if data.get(name) in (None, ""):
            errors.append(f"contact field missing: {name}")
    if data.get("oc_contactability") == 1 and not str(data.get("oc_email", "")).endswith(".invalid"):
        errors.append("synthetic contactable fixture requires a .invalid email")
    if data.get("oc_contactability") in (2, 3, 4) and not data.get("oc_contact_issue_note"):
        errors.append("contact issue requires a note")
    eligible = _integer(data.get("oc_eligible_projects"))
    offered = _integer(data.get("oc_projects_offered"))
    minutes = _integer(data.get("oc_minutes_per_project"))
    total = _integer(data.get("oc_est_total_minutes"))
    if None in (eligible, offered, minutes, total) or min(eligible or 0, offered or 0, minutes or 0, total or 0) < 0:
        errors.append("contact burden/count fields must be non-negative integers")
    elif offered > eligible or total != offered * minutes:
        errors.append("offered/eligible counts or total burden are incoherent")
    if data.get("oc_eoi_status") in (2, 3, 5) and not data.get("oc_eoi_response_date"):
        errors.append("expression-of-interest response requires a date")
    accepted = _integer(data.get("oc_projects_accepted"))
    if accepted is not None and (accepted < 0 or offered is None or accepted > offered):
        errors.append("accepted project count is incoherent")
    if data.get("oc_recruit_route") == 1 and not data.get("oc_sequence_pos"):
        errors.append("sequence route requires a sequence position")
    if data.get("oc_recruit_route") == 2 and not data.get("oc_supp_reason"):
        errors.append("supplementary route requires a pre-contact reason")
    if data.get("oc_ack_permission") == 1:
        for name in ("oc_ack_name", "oc_ack_affiliation", "oc_ack_permission_date", "oc_ack_permission_source"):
            if not data.get(name):
                errors.append(f"acknowledgement permission field missing: {name}")
    if data.get("oc_ack_permission") in (2, 3) and not data.get("oc_ack_permission_date"):
        errors.append("acknowledgement decision requires a date")
    return errors


def validate_assignment(data: Mapping[str, object], contacts: Mapping[str, Mapping[str, object]]) -> list[str]:
    errors: list[str] = []
    if data.get("record_type") != 2:
        errors.append("assignment record_type must equal 2")
    if not NEUTRAL_RECORD.fullmatch(str(data.get("owner_record_id", ""))):
        errors.append("assignment record key is not neutral opaque")
    required = ("owner_id", "owner_assignment_id", "source_record_id", "official_project_id", "project_title", "datasets_used", "public_register_url", "production_ver", "taxonomy_ver", "proposal_output_sha256", "owner_recruit_route", "owner_invite_batch", "owner_link_release", "owner_withdrawal_status", "instrument_ver")
    for name in required:
        if data.get(name) in (None, ""):
            errors.append(f"assignment field missing: {name}")
    if data.get("instrument_ver") != builder.VERSION:
        errors.append("assignment instrument version differs")
    if not HEX64.fullmatch(str(data.get("proposal_output_sha256", ""))):
        errors.append("proposal output hash is invalid")
    owner_id = str(data.get("owner_id", ""))
    contact = contacts.get(owner_id)
    if contact is None:
        errors.append("assignment has no contact parent")
    release = _integer(data.get("owner_link_release"))
    if release not in (0, 1, 2):
        errors.append("invalid assignment-link release code")
    elif release > 0 and (contact is None or contact.get("oc_eoi_status") != 2):
        errors.append("assignment link released without affirmative interest")
    if release == 2 and not data.get("owner_invite_date"):
        errors.append("released assignment link requires an invitation date")
    if data.get("owner_recruit_route") == 1 and not data.get("owner_sequence_pos"):
        errors.append("sequence assignment requires sequence position")
    domains = [i for i in range(1, 13) if _integer(data.get(f"prop_d{i:02d}")) == 1]
    purposes = [i for i in range(1, 9) if _integer(data.get(f"prop_p{i:02d}")) == 1]
    for prefix, maximum in (("d", 12), ("p", 8), ("t", 2)):
        for index in range(1, maximum + 1):
            if _integer(data.get(f"prop_{prefix}{index:02d}")) not in (0, 1):
                errors.append(f"invalid proposal flag: prop_{prefix}{index:02d}")
    if not domains or (12 in domains and len(domains) != 1):
        errors.append("proposed domains are empty or violate Unclear exclusivity")
    if not 1 <= len(purposes) <= 2 or (8 in purposes and len(purposes) != 1):
        errors.append("proposed purposes violate cardinality or Unclear exclusivity")
    for name in DIRECT_IDENTIFIERS:
        if data.get(name) not in (None, ""):
            errors.append(f"direct identifier leaked into assignment: {name}")
    return errors


def analytically_complete(response: Mapping[str, object], assignment: Mapping[str, object]) -> bool:
    if response.get("po_ack") != 1:
        return False
    for prefix, maximum in (("d", 12), ("p", 8)):
        for index in range(1, maximum + 1):
            if _integer(assignment.get(f"prop_{prefix}{index:02d}")) == 1 and _integer(response.get(f"po_{prefix}{index:02d}_fit")) not in (1, 2, 3):
                return False
    if _integer(response.get("po_t01_correct")) not in (0, 1, 2) or _integer(response.get("po_t02_correct")) not in (0, 1, 2):
        return False
    return _integer(response.get("po_sufficiency")) in (1, 2, 3)


def validate_response(response: Mapping[str, object], assignment: Mapping[str, object], *, strict: bool) -> list[str]:
    errors: list[str] = []
    ack = _integer(response.get("po_ack"))
    if ack not in (0, 1):
        errors.append("participation acknowledgement is invalid")
        return errors
    if ack == 0:
        if any(value not in (None, "", []) for name, value in response.items() if name != "po_ack"):
            errors.append("declined response contains substantive answers")
        return errors
    triggered_note = False
    for prefix, maximum in (("d", 12), ("p", 8)):
        for index in range(1, maximum + 1):
            proposed = _integer(assignment.get(f"prop_{prefix}{index:02d}")) == 1
            fit_name = f"po_{prefix}{index:02d}_fit"
            vis_name = f"po_{prefix}{index:02d}_vis"
            fit = _integer(response.get(fit_name))
            vis = _integer(response.get(vis_name))
            if not proposed and (response.get(fit_name) not in (None, "") or response.get(vis_name) not in (None, "")):
                errors.append(f"hidden unused slot answered: {prefix}{index:02d}")
            if proposed and fit is not None and fit not in (1, 2, 3):
                errors.append(f"invalid proposed-label verdict: {fit_name}")
            if proposed and vis is not None and vis not in (1, 2, 3, 4):
                errors.append(f"invalid visibility judgement: {vis_name}")
            if strict and proposed and fit not in (1, 2, 3):
                errors.append(f"required proposed-label verdict missing: {fit_name}")
            if strict and proposed and vis not in (1, 2, 3, 4):
                errors.append(f"required visibility judgement missing: {vis_name}")
            triggered_note |= fit in (2, 3) or vis in (2, 3, 4)
    for stem in ("t01", "t02"):
        correct = _integer(response.get(f"po_{stem}_correct"))
        determinable = _integer(response.get(f"po_{stem}_det"))
        if correct is not None and correct not in (0, 1, 2):
            errors.append(f"invalid tag correctness: {stem}")
        if determinable is not None and determinable not in (0, 1, 2, 3):
            errors.append(f"invalid tag determinability: {stem}")
        if strict and correct not in (0, 1, 2):
            errors.append(f"tag correctness missing: {stem}")
        if strict and determinable not in (0, 1, 2, 3):
            errors.append(f"tag determinability missing: {stem}")
        triggered_note |= correct in (0, 2) or determinable in (0, 2, 3)
    for flag, target in (("po_miss_domain", "po_miss_domains"), ("po_miss_purpose", "po_miss_purposes"), ("po_miss_tag", "po_miss_tags")):
        value = _integer(response.get(flag))
        if strict and value not in (0, 1):
            errors.append(f"missing-label indicator absent: {flag}")
        if value == 1:
            triggered_note = True
            if strict and not response.get(target):
                errors.append(f"missing-label selection absent: {target}")
        if value == 0 and response.get(target):
            errors.append(f"hidden missing-label selection populated: {target}")
    sufficiency = _integer(response.get("po_sufficiency"))
    taxonomy_fit = _integer(response.get("po_taxonomy_fit"))
    if strict and sufficiency not in (1, 2, 3):
        errors.append("public-entry sufficiency missing")
    if strict and taxonomy_fit not in (1, 2, 3):
        errors.append("taxonomy fit missing")
    issue = response.get("po_tax_issue") or []
    if taxonomy_fit in (2, 3):
        triggered_note = True
        if strict and not issue:
            errors.append("taxonomy issue type missing")
    elif issue:
        errors.append("taxonomy issue populated while hidden")
    triggered_note |= sufficiency in (2, 3)
    if strict and triggered_note and not response.get("po_note"):
        errors.append("conditional explanation missing")
    nonpublic = _integer(response.get("po_nonpublic"))
    if strict and nonpublic not in (0, 1):
        errors.append("non-public-knowledge response missing")
    if strict and nonpublic == 1 and not response.get("po_nonpublic_note"):
        errors.append("non-public-knowledge source note missing")
    quote = _integer(response.get("po_quote_permission"))
    if quote is not None and quote not in (0, 1, 2):
        errors.append("quotation permission is invalid")
    return errors


def validate_fixtures(path: Path = builder.RESPONSE_FIXTURE) -> dict[str, int]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = path.read_text(encoding="utf-8") + builder.IMPORT_FIXTURE.read_text(encoding="utf-8")
    errors: list[str] = []
    if REAL_RECORD_ID.search(raw):
        errors.append("synthetic fixture contains a real-format DEA Record ID")
    if re.search(r"@(?!example\.invalid)", raw):
        errors.append("synthetic fixture contains a non-.invalid email")
    contacts = {row["owner_id"]: row for row in payload["contacts"]}
    for row in payload["contacts"]:
        errors += [f"contact {row['owner_id']}: {item}" for item in validate_contact(row)]
    assignments = {row["owner_record_id"]: row for row in payload["assignments"]}
    seen_assignment_ids: set[str] = set()
    for row in payload["assignments"]:
        errors += [f"assignment {row['owner_record_id']}: {item}" for item in validate_assignment(row, contacts)]
        if row["owner_assignment_id"] in seen_assignment_ids:
            errors.append("duplicate owner_assignment_id")
        seen_assignment_ids.add(row["owner_assignment_id"])
    owner_assignments: defaultdict[str, int] = defaultdict(int)
    for row in payload["assignments"]:
        owner_assignments[row["owner_id"]] += 1
    if max(owner_assignments.values(), default=0) < 2:
        errors.append("no synthetic owner links to several assignments")
    for case in payload["responses"]:
        assignment = assignments.get(case["owner_record_id"])
        if assignment is None:
            errors.append(f"response has no assignment: {case['case_id']}")
            continue
        strict = bool(case["expected_analytical_complete"])
        actual_errors = validate_response(case["data"], assignment, strict=strict)
        actual_valid = not actual_errors
        if actual_valid != bool(case["expected_valid"]):
            errors.append(f"{case['case_id']} validity differs: {actual_errors}")
        if analytically_complete(case["data"], assignment) != bool(case["expected_analytical_complete"]):
            errors.append(f"{case['case_id']} analytical completion differs")
    if errors:
        raise OwnerCandidateError("\n".join(errors))
    return {"contacts": len(contacts), "assignments": len(assignments), "responses": len(payload["responses"])}


def check() -> dict[str, object]:
    dictionary = validate_dictionary()
    fixtures = validate_fixtures()
    return {"version": builder.VERSION, "dictionary": dictionary, "fixtures": fixtures, "status": "passed_offline_unfrozen"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    print(yaml.safe_dump(check(), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
