from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

from scripts import build_project_owner_redcap_candidate as builder
from scripts import validate_project_owner_redcap_candidate as validator


ROOT = Path(__file__).resolve().parents[1]


def rows() -> list[dict[str, str]]:
    return validator.load_dictionary()


def by_name() -> dict[str, dict[str, str]]:
    return {row["Variable / Field Name"]: row for row in rows()}


def fixture() -> dict:
    return yaml.safe_load(builder.RESPONSE_FIXTURE.read_text(encoding="utf-8"))


def test_candidate_version_status_and_exact_structure() -> None:
    result = validator.validate_dictionary()
    assert result["version"] == "owner-redcap-candidate-0.1"
    assert result["fields"] == 152
    assert result["forms"] == builder.FORM_COUNTS == {
        "owner_contact_admin": 27,
        "owner_assignment_admin": 39,
        "project_owner_review": 86,
    }
    assert tuple(dict.fromkeys(row["Form Name"] for row in rows())) == builder.FORMS


def test_dictionary_is_deterministic_and_round_trips_existing_parser() -> None:
    built, _ = builder.build_dictionary()
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=builder.HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(built)
    assert buffer.getvalue().encode("utf-8") == builder.DICTIONARY.read_bytes()
    assert len(validator.load_dictionary()) == 152


def test_unique_names_valid_types_and_balanced_branches() -> None:
    candidate = rows()
    names = [row["Variable / Field Name"] for row in candidate]
    assert len(names) == len(set(names))
    assert all(row["Field Type"] in validator.ALLOWED_TYPES for row in candidate)
    assert all(validator._balanced_branch(row["Branching Logic (Show field only if...)"]) for row in candidate)


def test_neutral_record_key_and_stable_record_type() -> None:
    by = by_name()
    assert rows()[0]["Variable / Field Name"] == "owner_record_id"
    assert validator.parse_choices(by["record_type"]["Choices, Calculations, OR Slider Labels"]) == {"1": "Contact", "2": "Assignment"}
    assert "Record ID" not in by["owner_record_id"]["Field Label"]


def test_record_type_and_acknowledgement_guards() -> None:
    for row in rows():
        name, form = row["Variable / Field Name"], row["Form Name"]
        branch = row["Branching Logic (Show field only if...)"]
        if form == "owner_contact_admin" and name not in {"owner_record_id", "record_type", "owner_id"}:
            assert builder.CONTACT in branch
        elif form == "owner_assignment_admin":
            assert builder.ASSIGNMENT in branch
        elif form == "project_owner_review":
            assert builder.ASSIGNMENT in branch
            if name not in {"po_intro", "po_privacy", "po_ack"}:
                assert "[po_ack] = '1'" in branch


def test_direct_identifiers_exist_only_in_contact_admin() -> None:
    identifiers = {row["Variable / Field Name"] for row in rows() if row["Identifier?"] == "y"}
    assert identifiers == validator.DIRECT_IDENTIFIERS
    assert all(by_name()[name]["Form Name"] == "owner_contact_admin" for name in identifiers)
    assert by_name()["oc_email"]["Text Validation Type OR Show Slider Number"] == "email"


def test_no_prohibited_scientific_or_sampling_metadata_fields() -> None:
    for row in rows():
        if row["Form Name"] in {"owner_assignment_admin", "project_owner_review"}:
            name = row["Variable / Field Name"].lower()
            assert not any(term in name for term in validator.PROHIBITED_OWNER_TERMS)


def test_fixed_slots_are_paired_and_unused_slots_are_hidden() -> None:
    by = by_name()
    for prefix, maximum in (("d", 12), ("p", 8)):
        for index in range(1, maximum + 1):
            stem = f"{prefix}{index:02d}"
            flag = f"prop_{stem}"
            for suffix in ("label", "fit", "vis"):
                row = by[f"po_{stem}_{suffix}"]
                assert f"[{flag}] = '1'" in row["Branching Logic (Show field only if...)"]
            assert by[f"po_{stem}_fit"]["Required Field?"] == "y"
            assert by[f"po_{stem}_vis"]["Required Field?"] == "y"


def test_binary_tags_support_applied_and_not_applied_without_fit_wording() -> None:
    by = by_name()
    for stem in ("t01", "t02"):
        assert validator.parse_choices(by[f"prop_{stem}"]["Choices, Calculations, OR Slider Labels"]) == {"0": "Not applied", "1": "Applied"}
        assert f"[prop_{stem}:label]" in by[f"po_{stem}_label"]["Field Label"]
        assert validator.parse_choices(by[f"po_{stem}_correct"]["Choices, Calculations, OR Slider Labels"]) == {"1": "Yes", "0": "No", "2": "Unsure"}
        assert validator.parse_choices(by[f"po_{stem}_det"]["Choices, Calculations, OR Slider Labels"]) == {"1": "Yes", "2": "Partly", "0": "No", "3": "Unsure"}
        assert "fit" not in by[f"po_{stem}_correct"]["Field Label"].lower()
        assert f"[po_{stem}_correct] = '0'" in by["po_note"]["Branching Logic (Show field only if...)"]
        assert f"[po_{stem}_correct] = '2'" in by["po_note"]["Branching Logic (Show field only if...)"]


def test_owner_taxonomy_fit_has_no_cannot_assess() -> None:
    choices = validator.parse_choices(by_name()["po_taxonomy_fit"]["Choices, Calculations, OR Slider Labels"])
    assert choices == {"1": "Fit", "2": "Partial Fit", "3": "No Fit"}
    assert "Cannot assess" not in str(choices)


def test_participation_quote_and_named_acknowledgement_are_separate() -> None:
    by = by_name()
    assert by["po_ack"]["Form Name"] == "project_owner_review"
    assert by["po_quote_permission"]["Form Name"] == "project_owner_review"
    assert by["po_quote_permission"]["Required Field?"] == ""
    for name in ("oc_ack_permission", "oc_ack_name", "oc_ack_affiliation", "oc_ack_permission_date", "oc_ack_permission_source"):
        assert by[name]["Form Name"] == "owner_contact_admin"
    assert not any("ack_permission" in row["Variable / Field Name"] for row in rows() if row["Form Name"] == "project_owner_review")


def test_approved_withdrawal_and_configuration_placeholders() -> None:
    by = by_name()
    assert builder.WITHDRAWAL_WORDING in by["po_privacy"]["Field Label"]
    assert "{{DASHBOARD_URL}}" in by["po_intro"]["Field Label"]
    assert "{{ESTIMATED_MINUTES_PER_PROJECT}}" in by["po_intro"]["Field Label"]
    assert "{{WITHDRAWAL_DATE}}" in by["po_privacy"]["Field Label"]
    assert "{{STUDY_EMAIL}}" in by["po_privacy"]["Field Label"]


def test_expression_of_interest_is_an_explicit_link_release_gate() -> None:
    payload = fixture()
    contacts = {row["owner_id"]: row for row in payload["contacts"]}
    assignment = dict(payload["assignments"][0])
    assert not validator.validate_assignment(assignment, contacts)
    contacts[assignment["owner_id"]] = dict(contacts[assignment["owner_id"]], oc_eoi_status=1)
    assert "assignment link released without affirmative interest" in validator.validate_assignment(assignment, contacts)


def test_contact_to_assignment_link_is_one_to_many() -> None:
    payload = fixture()
    assignments = [row for row in payload["assignments"] if row["owner_id"] == "SYN-OWNER-01"]
    assert len(assignments) == 2
    assert len({row["owner_assignment_id"] for row in assignments}) == 2
    assert len({row["source_record_id"] for row in assignments}) == 2


def test_synthetic_fixtures_are_fictional_and_validate() -> None:
    result = validator.validate_fixtures()
    assert result == {"contacts": 6, "assignments": 4, "responses": 5}
    raw = builder.RESPONSE_FIXTURE.read_text(encoding="utf-8") + builder.IMPORT_FIXTURE.read_text(encoding="utf-8")
    assert not validator.REAL_RECORD_ID.search(raw)
    assert "@example.invalid" in raw
    assert not re.search(r"@(?!example\.invalid)", raw)
    assert "Synthetic" in raw


def test_fixture_coverage_includes_required_routes_states_and_cardinality() -> None:
    payload = fixture()
    assert {row["oc_recruit_route"] for row in payload["contacts"]} == {1, 2}
    assert {row["oc_eoi_status"] for row in payload["contacts"]} >= {0, 2, 3}
    assert {row["oc_contactability"] for row in payload["contacts"]} >= {1, 3, 4}
    assert {row["oc_contact_suppression"] for row in payload["contacts"]} >= {0, 1, 2, 3}
    assert any(sum(row[f"prop_d{i:02d}"] for i in range(1, 13)) > 1 for row in payload["assignments"])
    assert any(sum(row[f"prop_p{i:02d}"] for i in range(1, 9)) == 2 for row in payload["assignments"])
    assert {row["prop_t01"] for row in payload["assignments"]} == {0, 1}
    assert {row["prop_t02"] for row in payload["assignments"]} == {0, 1}
    quotes = {case["data"].get("po_quote_permission") for case in payload["responses"]}
    assert quotes >= {0, 1, 2, None}


def test_analytical_completion_is_deterministic_and_quote_independent() -> None:
    payload = fixture()
    assignments = {row["owner_record_id"]: row for row in payload["assignments"]}
    case = next(row for row in payload["responses"] if row["case_id"] == "complete_fit_quote_yes")
    response = dict(case["data"])
    assignment = assignments[case["owner_record_id"]]
    assert validator.analytically_complete(response, assignment)
    response.pop("po_quote_permission")
    assert validator.analytically_complete(response, assignment)
    response.pop("po_sufficiency")
    assert not validator.analytically_complete(response, assignment)


def test_decline_hides_substantive_response_and_is_incomplete() -> None:
    assignment = fixture()["assignments"][0]
    assert not validator.validate_response({"po_ack": 0}, assignment, strict=False)
    assert not validator.analytically_complete({"po_ack": 0}, assignment)
    assert validator.validate_response({"po_ack": 0, "po_sufficiency": 1}, assignment, strict=False)


def test_strict_response_requires_conditional_explanation_but_not_quote() -> None:
    payload = fixture()
    assignments = {row["owner_record_id"]: row for row in payload["assignments"]}
    case = next(row for row in payload["responses"] if row["case_id"] == "complete_disagreement_nonpublic_quote_no")
    response = dict(case["data"])
    assignment = assignments[case["owner_record_id"]]
    assert not validator.validate_response(response, assignment, strict=True)
    response.pop("po_note")
    assert "conditional explanation missing" in validator.validate_response(response, assignment, strict=True)
    response = dict(case["data"])
    response.pop("po_quote_permission")
    assert not validator.validate_response(response, assignment, strict=True)


def test_unused_proposal_slot_response_is_rejected() -> None:
    assignment = fixture()["assignments"][0]
    errors = validator.validate_response({"po_ack": 1, "po_d02_fit": 1}, assignment, strict=False)
    assert "hidden unused slot answered: d02" in errors


def test_contact_burden_and_acknowledgement_rules() -> None:
    contact = dict(fixture()["contacts"][0])
    assert not validator.validate_contact(contact)
    contact["oc_est_total_minutes"] = 999
    assert "offered/eligible counts or total burden are incoherent" in validator.validate_contact(contact)
    contact = dict(fixture()["contacts"][0])
    contact.pop("oc_ack_name")
    assert "acknowledgement permission field missing: oc_ack_name" in validator.validate_contact(contact)


def test_assignment_contains_no_contact_identifier_values() -> None:
    payload = fixture()
    contacts = {row["owner_id"]: row for row in payload["contacts"]}
    assignment = dict(payload["assignments"][0], oc_email="leak@example.invalid")
    assert "direct identifier leaked into assignment: oc_email" in validator.validate_assignment(assignment, contacts)


def test_field_provenance_counts_reconcile_to_152() -> None:
    with builder.FIELD_SPEC.open(encoding="utf-8", newline="") as handle:
        source_counts = Counter(row["candidate_source"].split(":", 1)[0] for row in csv.DictReader(handle))
    assert source_counts == Counter({"retained_name_modified_for_standalone": 109, "new": 35, "renamed": 8})


def test_branch_and_export_specs_are_synchronised() -> None:
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    assert branch["version"] == builder.VERSION
    assert branch["field_counts"] == builder.FORM_COUNTS
    assert branch["only_survey_instrument"] == "project_owner_review"
    assert branch["contact_instrument_is_survey"] is False
    assert branch["link_release_requires_affirmative_interest"] is True
    with builder.EXPORT_SPEC.open(encoding="utf-8", newline="") as handle:
        export = list(csv.DictReader(handle))
    contact = [row for row in export if row["source_form"] == "owner_contact_admin" and row["variable"].startswith("oc_")]
    assert contact and all(row["include_in_ordinary_analytical_export"] == "no" for row in contact)
    assert any(row["variable"] == "owner_analytical_complete" for row in export)


def test_recruitment_materials_begin_with_context_and_initial_email_has_no_survey_link() -> None:
    text = (builder.PACKAGE / "project_owner_recruitment_materials_candidate_0.1.md").read_text(encoding="utf-8")
    initial = text.split("## 1. Initial expression-of-interest email", 1)[1].split("## 2.", 1)[0]
    for required in ("{{DASHBOARD_URL}}", "large language model", "particularly valuable", "multiple projects", "{{ELIGIBLE_PROJECT_COUNT}}", "{{MINUTES_PER_PROJECT}}", "{{ESTIMATED_TOTAL_MINUTES}}", "all or only some", "acknowledged by name"):
        assert required in initial
    assert "No survey or" in initial
    assert "{{PROJECT_LINK_LIST}}" not in initial


def test_qa_plan_keeps_candidate_unfrozen_and_pid_offline() -> None:
    text = (builder.PACKAGE / "project_owner_live_qa_plan_candidate_0.1.md").read_text(encoding="utf-8")
    normalised = " ".join(text.split())
    assert "PID 9149" in normalised
    assert "No connection" in normalised
    assert "remains unfrozen" in normalised
    assert "synthetic" in normalised.lower()


def test_frozen_scratch_candidate_remains_byte_identical() -> None:
    assert hashlib.sha256(builder.SCRATCH_DICTIONARY.read_bytes()).hexdigest() == builder.SCRATCH_SHA256
    frozen = builder.PACKAGE / "redcap_data_dictionary_frozen_0.7_2026-07-22.csv"
    assert builder.SCRATCH_DICTIONARY.read_bytes() == frozen.read_bytes()


def test_canonical_dictionary_hash_and_status_are_documented() -> None:
    assert validator.sha256_file(builder.DICTIONARY) == "e3b59478ff9e37a52964790340dc1a65daccb5381293a42883ed7eaf398c3114"
    readme = (builder.PACKAGE / "project_owner_redcap_candidate_0.1_README.md").read_text(encoding="utf-8")
    assert "development review candidate; unfrozen; not imported" in readme
    assert validator.sha256_file(builder.DICTIONARY) in readme


def test_complete_offline_check() -> None:
    assert validator.check()["status"] == "passed_offline_unfrozen"
