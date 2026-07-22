from __future__ import annotations

import csv
import hashlib
import io
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_project_owner_redcap_candidate_0_2 as builder  # noqa: E402
import validate_project_owner_redcap_candidate_0_2 as validator  # noqa: E402


def rows() -> list[dict[str, str]]:
    return validator.load_dictionary()


def by_name() -> dict[str, dict[str, str]]:
    return {row["Variable / Field Name"]: row for row in rows()}


def fixture() -> dict:
    return yaml.safe_load(builder.RESPONSE_FIXTURE.read_text(encoding="utf-8"))


def contacts() -> dict[str, dict]:
    return {row["owner_id"]: row for row in fixture()["contacts"]}


def assignments() -> dict[str, dict]:
    return {row["owner_record_id"]: row for row in fixture()["assignments"]}


def test_version_status_and_exact_four_instrument_structure() -> None:
    assert builder.VERSION == "owner-redcap-candidate-0.2"
    assert builder.CONSENT_INFO_VERSION == "project-owner-information-v1"
    assert builder.QUESTIONNAIRE_VERSION == "project-owner-review-questionnaire-v1"
    assert builder.FORMS == (
        "owner_contact_admin", "project_owner_consent",
        "owner_assignment_admin", "project_owner_review",
    )
    assert Counter(row["Form Name"] for row in rows()) == Counter(builder.FORM_COUNTS)
    assert builder.FORM_COUNTS == {
        "owner_contact_admin": 31,
        "project_owner_consent": 12,
        "owner_assignment_admin": 39,
        "project_owner_review": 85,
    }
    assert len(rows()) == 167


def test_dictionary_is_deterministic_and_round_trips_parser() -> None:
    built, _ = builder.build_dictionary()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=builder.HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(built)
    assert output.getvalue().encode() == builder.DICTIONARY.read_bytes()
    assert validator.load_dictionary() == built


def test_consent_and_review_record_guards() -> None:
    for row in rows():
        form = row["Form Name"]
        branch = row["Branching Logic (Show field only if...)"]
        if form == "project_owner_consent":
            assert builder.CONTACT in branch
            assert builder.ASSIGNMENT not in branch
        if form == "project_owner_review":
            assert builder.ASSIGNMENT in branch
            assert builder.CONTACT not in branch
            assert "po_ack" not in branch


def test_consent_is_affirmative_required_versioned_and_once_per_owner() -> None:
    by = by_name()
    assert validator.parse_choices(by["pc_decision"]["Choices, Calculations, OR Slider Labels"]) == {
        "1": "Yes, I agree to take part",
        "0": "No, I do not wish to take part",
    }
    assert by["pc_decision"]["Required Field?"] == "y"
    assert by["pc_info_version"]["Required Field?"] == "y"
    assert by["pc_info_version"]["Field Annotation"] == "@READONLY"
    assert all(row["Form Name"] == "project_owner_consent" for name, row in by.items() if name.startswith("pc_"))
    owner_ids = [row["owner_id"] for row in fixture()["contacts"]]
    assert len(owner_ids) == len(set(owner_ids))


def test_consent_content_covers_required_information() -> None:
    text = " ".join(
        row["Field Label"] for row in rows() if row["Form Name"] == "project_owner_consent"
    ).lower()
    for phrase in (
        "dashboard", "large language model", "approached because", "invited to review",
        "estimated total burden", "all, some or none", "voluntary",
        "declining has no consequences", "confidential", "used for",
        "contact details", "withdrawal", "{{study_email}}", "separate project reviews",
        "change substantially",
    ):
        assert phrase in text


def test_no_direct_identifiers_in_participant_facing_instruments() -> None:
    identifiers = [row["Variable / Field Name"] for row in rows() if row["Identifier?"] == "y"]
    assert set(identifiers) == validator.DIRECT_IDENTIFIERS
    assert all(by_name()[name]["Form Name"] == "owner_contact_admin" for name in identifiers)
    assert not any(
        row["Identifier?"] for row in rows()
        if row["Form Name"] in {"project_owner_consent", "project_owner_review"}
    )


def test_expression_of_interest_is_not_consent() -> None:
    interested_pending = dict(contacts()["SYN-OWNER-03"])
    assert interested_pending["oc_eoi_status"] == 2
    assert not validator.current_consent(interested_pending)
    interested_pending["pc_decision"] = 1
    interested_pending["pc_info_version"] = builder.CONSENT_INFO_VERSION
    assert validator.current_consent(interested_pending)


def test_release_gate_requires_interest_and_current_consent() -> None:
    by = by_name()
    calc = by["oc_link_eligible"]["Choices, Calculations, OR Slider Labels"]
    assert "[oc_eoi_status] = '2'" in calc
    assert "[pc_decision] = '1'" in calc
    assert builder.CONSENT_INFO_VERSION in calc
    assert "[oc_reconsent_required] = '0'" in calc
    assert "[oc_consent_withdrawal] = '0'" in calc
    assert "[oc_contact_suppression] = '0'" in calc
    assert validator.current_consent(contacts()["SYN-OWNER-01"])
    assert validator.current_consent(contacts()["SYN-OWNER-07"])


def test_missing_declined_withdrawn_and_stale_consent_block_release() -> None:
    data = contacts()
    for owner in ("SYN-OWNER-02", "SYN-OWNER-03", "SYN-OWNER-04", "SYN-OWNER-05", "SYN-OWNER-06"):
        assert not validator.current_consent(data[owner])
    for assignment in assignments().values():
        if assignment["owner_id"] in {"SYN-OWNER-02", "SYN-OWNER-03", "SYN-OWNER-04", "SYN-OWNER-05"}:
            assert assignment["owner_link_release"] == 0


def test_old_information_0_2_token_is_stale_and_requires_reconsent() -> None:
    stale = contacts()["SYN-OWNER-04"]
    assert stale["pc_info_version"] == builder.OLD_CONSENT_INFO_VERSION
    assert stale["oc_reconsent_required"] == 1
    assert not validator.current_consent(stale)
    current = dict(stale, pc_info_version=builder.CONSENT_INFO_VERSION, oc_reconsent_required=0)
    assert validator.current_consent(current)


def test_official_release_validator_cannot_accept_stale_consent() -> None:
    item = dict(assignments()["M4N5P6Q7"])
    item["owner_link_release"] = 1
    assert "assignment link eligible or released without current affirmative consent" in validator.validate_assignment(item, contacts())


def test_one_consent_supports_several_assignment_records() -> None:
    linked = [row for row in assignments().values() if row["owner_id"] == "SYN-OWNER-01"]
    assert len(linked) == 2
    assert all(row["owner_link_release"] == 2 for row in linked)
    assert validator.current_consent(contacts()["SYN-OWNER-01"])


def test_review_has_reminder_but_no_repeated_consent_checkbox() -> None:
    by = by_name()
    assert "po_ack" not in by
    intro = by["po_intro"]["Field Label"].lower()
    assert "previously agreed" in intro
    assert "remains voluntary" in intro
    assert "skip this review or stop" in intro
    assert not any(
        "consent" in row["Field Label"].lower()
        and row["Field Type"] in {"radio", "yesno", "checkbox"}
        for row in rows() if row["Form Name"] == "project_owner_review"
    )


def test_substantive_review_questions_preserve_candidate_0_1_codes() -> None:
    with builder.V01_DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
        old = {row["Variable / Field Name"]: row for row in csv.DictReader(handle)}
    new = by_name()
    exempt = {"po_intro", "po_privacy", "po_ack"}
    for name, before in old.items():
        if before["Form Name"] != "project_owner_review" or name in exempt:
            continue
        after = new[name]
        for column in (
            "Field Type", "Field Label", "Choices, Calculations, OR Slider Labels",
            "Field Note", "Text Validation Type OR Show Slider Number",
            "Required Field?", "Identifier?",
        ):
            assert after[column] == before[column], (name, column)


def test_quote_response_level_and_acknowledgement_researcher_level() -> None:
    by = by_name()
    assert by["po_quote_permission"]["Form Name"] == "project_owner_review"
    for name in ("oc_ack_permission", "oc_ack_name", "oc_ack_affiliation", "oc_ack_permission_date", "oc_ack_permission_source"):
        assert by[name]["Form Name"] == "owner_contact_admin"
    assert not any("ack_permission" in row["Variable / Field Name"] for row in rows() if row["Form Name"] == "project_owner_review")


def test_analytical_completion_uses_contact_consent_not_quote() -> None:
    payload = fixture()
    cases = {case["case_id"]: case for case in payload["responses"]}
    current = cases["complete_first_review_quote_yes"]
    assignment = assignments()[current["owner_record_id"]]
    assert validator.analytically_complete(current["data"], assignment, contacts())
    changed = dict(current["data"])
    changed.pop("po_quote_permission")
    assert validator.analytically_complete(changed, assignment, contacts())
    declined = cases["structurally_complete_but_consent_declined"]
    assert not validator.analytically_complete(
        declined["data"], assignments()[declined["owner_record_id"]], contacts()
    )


def test_review_response_with_removed_po_ack_is_rejected() -> None:
    item = assignments()["H8J9K2L3"]
    assert validator.validate_response({"po_ack": 1}, item, strict=False) == [
        "review response contains removed repeated-consent field: po_ack"
    ]


def test_synthetic_fixture_coverage_and_validity() -> None:
    result = validator.validate_fixtures()
    assert result == {"contacts": 7, "assignments": 7, "responses": 4}
    raw = builder.RESPONSE_FIXTURE.read_text(encoding="utf-8")
    assert "contains_real_researchers: false" in raw
    assert "contains_real_emails: false" in raw
    assert "contains_real_record_ids: false" in raw
    assert "example.invalid" in raw


def test_field_difference_is_exactly_consent_redesign() -> None:
    spec = list(csv.DictReader(builder.FIELD_SPEC.open(encoding="utf-8", newline="")))
    counts = Counter(row["candidate_source"] for row in spec)
    assert counts == {
        "retained_unchanged_from_candidate_0.1": 65,
        "modified_for_one_time_consent": 86,
        "new_for_one_time_consent": 16,
    }
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    assert branch["difference_from_candidate_0.1"]["removed_fields"] == ["po_ack"]
    assert branch["difference_from_candidate_0.1"]["renamed_fields"] == {}


def test_export_spec_has_native_consent_timestamp_and_derived_flags() -> None:
    export = {row["variable"]: row for row in csv.DictReader(builder.EXPORT_SPEC.open(encoding="utf-8", newline=""))}
    assert export["project_owner_consent_timestamp"]["source_form"] == "project_owner_consent"
    assert export["owner_current_consent"]["source_form"] == "derived_contact_consent_join"
    assert "current contact-level consent" in export["owner_analytical_complete"]["notes"]
    assert builder.QUESTIONNAIRE_VERSION in export["project_owner_review_questionnaire_version"]["notes"]


def _visible_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    return " ".join(re.sub(r"<[^>]+>", " ", xml).split())


def test_participant_documents_are_version_1_and_manifestable_without_exact_case() -> None:
    materials = builder.PACKAGE / "participant_materials"
    information = materials / "Project_Owner_Participant_Information_and_consent_v1.docx"
    questionnaire = materials / "Project_Owner_Review_questionnaire_v1.docx"
    assert information.exists() and questionnaire.exists()
    assert "v1" in information.name.lower() and "v1" in questionnaire.name.lower()
    info_text = _visible_docx_text(information).lower()
    questionnaire_text = _visible_docx_text(questionnaire).lower()
    assert "project owner participant information and consent" in info_text
    assert "version 1" in info_text
    assert "project owner review questionnaire" in questionnaire_text
    assert re.search(r"\b(?:version\s*)?v?1\b", questionnaire_text)
    assert "candidate 0.2" not in info_text
    assert "candidate 0.2" not in questionnaire_text
    manifest = {
        row["artifact_id"]: row
        for row in csv.DictReader(
            (ROOT / "preregistration/preregistration_artifact_manifest.csv").open(
                encoding="utf-8", newline=""
            )
        )
    }
    for artifact_id, path, version in (
        ("RED-066", information, builder.CONSENT_INFO_VERSION),
        ("RED-067", questionnaire, builder.QUESTIONNAIRE_VERSION),
    ):
        row = manifest[artifact_id]
        assert row["version"] == version
        assert row["current_state"] == "working_candidate"
        assert row["authoritative_status"] == "current_ethics_review_material"
        assert row["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert int(row["size_bytes"]) == path.stat().st_size


def test_protocol_v0_15_is_byte_identical() -> None:
    protocol = ROOT / "preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.15.docx"
    assert hashlib.sha256(protocol.read_bytes()).hexdigest() == "5eff044b4f8d488e84a5b49720d35318add4f29ef53136cb6ce9c2b197409ee7"


def test_recruitment_materials_have_three_distinct_stages() -> None:
    text = " ".join((builder.PACKAGE / "project_owner_recruitment_materials_candidate_0.2.md").read_text(encoding="utf-8").split())
    assert "Stage 1 — expression-of-interest" in text
    assert "It is not informed consent" in text
    assert "Stage 2 — post-interest" in text
    assert "{{CONSENT_SURVEY_LINK}}" in text
    assert "Stage 3 — post-consent" in text
    assert "{{PROJECT_LINK_LIST}}" in text
    first = text.split("## 1.", 1)[1].split("## 2.", 1)[0]
    assert "{{CONSENT_SURVEY_LINK}}" not in first
    assert "{{PROJECT_LINK_LIST}}" not in first


def test_live_qa_plan_keeps_candidate_unfrozen_and_pid_offline() -> None:
    text = " ".join((builder.PACKAGE / "project_owner_live_qa_plan_candidate_0.2.md").read_text(encoding="utf-8").lower().split())
    for phrase in (
        "pid 9149", "no connection", "not frozen", "one consent supports several",
        "missing, declined, withdrawn or re-consent-required", "desktop/mobile",
        "no repeated consent checkbox", "all synthetic records",
    ):
        assert phrase in text


def test_candidate_0_1_controlled_artefacts_are_byte_identical() -> None:
    expected = {
        "preregistration/package/06_redcap/project_owner_redcap_data_dictionary_candidate_0.1.csv": "e3b59478ff9e37a52964790340dc1a65daccb5381293a42883ed7eaf398c3114",
        "preregistration/package/06_redcap/project_owner_redcap_field_specification_candidate_0.1.csv": "2a063a1a3fc68c97507cf99b96b8ae65c801b24fa669fc505e08b3919045a41a",
        "preregistration/package/06_redcap/project_owner_redcap_branching_specification_candidate_0.1.yaml": "0341cce6577e631237de7a39875defc182a3a2bc45587ffd53c6843fde7b32cc",
        "preregistration/package/06_redcap/project_owner_redcap_expected_export_candidate_0.1.csv": "07a1e3e160977afc16f627e878e52d31f5bb8e1bb527839dbd3f63f484953138",
        "preregistration/package/06_redcap/live_qa/project_owner_synthetic_import_candidate_0.1.csv": "bbf7dfbea83362c395bcc4525bf7d3d6d0d559938ba8bd32044444f76537856b",
        "preregistration/package/06_redcap/project_owner_recruitment_materials_candidate_0.1.md": "d1ee845665beaf390cf1a9885b6012ef479f8e135bd80d349ddf21ad1b735f2b",
        "preregistration/package/06_redcap/project_owner_live_qa_plan_candidate_0.1.md": "863fa752d0c2f5a8c9634a849a5ab327fbd8bcb8998ce42d5def316d1b5db093",
        "preregistration/package/06_redcap/project_owner_redcap_candidate_0.1_README.md": "a0862452898ca0136b7f4cc850403b704c55bc2b15b0a4eb7a421f909c36ae1c",
        "tests/fixtures/project_owner_candidate_0_1_synthetic_submissions.yaml": "9eeb8915dabce74a2f894f361fdb7106e5763d4e0debc54385f550bd6a8e584e",
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_frozen_scratch_candidate_remains_byte_identical() -> None:
    source = ROOT / "preregistration/package/06_redcap/redcap_data_dictionary_candidate.csv"
    frozen = ROOT / "preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv"
    assert source.read_bytes() == frozen.read_bytes()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == builder.SCRATCH_SHA256


def test_complete_offline_check() -> None:
    result = validator.check()
    assert result["status"] == "passed_offline_unfrozen"
    assert result["dictionary"]["fields"] == 167
