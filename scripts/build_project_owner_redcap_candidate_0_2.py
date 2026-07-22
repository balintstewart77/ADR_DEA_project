#!/usr/bin/env python3
"""Build owner-redcap-candidate-0.2 deterministically and entirely offline."""

from __future__ import annotations

import csv
import hashlib
from copy import deepcopy
from pathlib import Path

import yaml

import build_project_owner_redcap_candidate as v01


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "preregistration/package/06_redcap"
FIXTURES = ROOT / "tests/fixtures"
LIVE_QA = PACKAGE / "live_qa"
VERSION = "owner-redcap-candidate-0.2"
CONSENT_INFO_VERSION = "project-owner-information-v1"
OLD_CONSENT_INFO_VERSION = "owner-information-0.2"
QUESTIONNAIRE_VERSION = "project-owner-review-questionnaire-v1"
V01_DICTIONARY = PACKAGE / "project_owner_redcap_data_dictionary_candidate_0.1.csv"
V01_SHA256 = "e3b59478ff9e37a52964790340dc1a65daccb5381293a42883ed7eaf398c3114"
SCRATCH_DICTIONARY = PACKAGE / "redcap_data_dictionary_candidate.csv"
SCRATCH_SHA256 = v01.SCRATCH_SHA256
DICTIONARY = PACKAGE / "project_owner_redcap_data_dictionary_candidate_0.2.csv"
FIELD_SPEC = PACKAGE / "project_owner_redcap_field_specification_candidate_0.2.csv"
BRANCH_SPEC = PACKAGE / "project_owner_redcap_branching_specification_candidate_0.2.yaml"
EXPORT_SPEC = PACKAGE / "project_owner_redcap_expected_export_candidate_0.2.csv"
IMPORT_FIXTURE = LIVE_QA / "project_owner_synthetic_import_candidate_0.2.csv"
RESPONSE_FIXTURE = FIXTURES / "project_owner_candidate_0_2_synthetic_submissions.yaml"

HEADERS = v01.HEADERS
FORMS = (
    "owner_contact_admin",
    "project_owner_consent",
    "owner_assignment_admin",
    "project_owner_review",
)
FORM_COUNTS = {
    "owner_contact_admin": 31,
    "project_owner_consent": 12,
    "owner_assignment_admin": 39,
    "project_owner_review": 85,
}
CONTACT = v01.CONTACT
ASSIGNMENT = v01.ASSIGNMENT
HIDDEN = v01.HIDDEN
HIDDEN_READONLY = v01.HIDDEN_READONLY
WITHDRAWAL_WORDING = v01.WITHDRAWAL_WORDING


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _field(*args: object, **kwargs: object) -> dict[str, str]:
    return v01.field(*args, **kwargs)


def build_dictionary() -> tuple[list[dict[str, str]], dict[str, object]]:
    """Transform candidate 0.1 only where the one-time-consent design requires."""
    old_rows, meta = v01.build_dictionary()
    contact = [deepcopy(row) for row in old_rows if row["Form Name"] == "owner_contact_admin"]
    assignment = [deepcopy(row) for row in old_rows if row["Form Name"] == "owner_assignment_admin"]
    review = [deepcopy(row) for row in old_rows if row["Form Name"] == "project_owner_review"]

    consent_admin = [
        _field(
            "oc_reconsent_required", "owner_contact_admin", "radio",
            "Re-consent required before further project-review links",
            choice_text="0, No | 1, Yes", section="Consent administration",
            branch=CONTACT, required=True, annotation=HIDDEN,
        ),
        _field(
            "oc_consent_withdrawal", "owner_contact_admin", "radio",
            "Consent-withdrawal status",
            choice_text=(
                "0, No withdrawal | 1, Withdrawal requested; assessment pending | "
                "2, Consent withdrawn before analysis lock | "
                "3, Request received after responses could no longer be removed"
            ),
            branch=CONTACT, required=True, annotation=HIDDEN,
        ),
        _field(
            "oc_consent_withdraw_date", "owner_contact_admin", "text",
            "Date consent-withdrawal request was received", validation="date_ymd",
            branch=(
                f"({CONTACT}) and ([oc_consent_withdrawal] = '1' or "
                "[oc_consent_withdrawal] = '2' or [oc_consent_withdrawal] = '3')"
            ),
            required=True, annotation=HIDDEN,
        ),
        _field(
            "oc_link_eligible", "owner_contact_admin", "calc",
            "Current eligibility to release project-review links",
            choice_text=(
                f"if([oc_eoi_status] = '2' and [pc_decision] = '1' and "
                f"[pc_info_version] = '{CONSENT_INFO_VERSION}' and "
                "[oc_reconsent_required] = '0' and [oc_consent_withdrawal] = '0' "
                "and [oc_contact_suppression] = '0', 1, 0)"
            ),
            note=(
                "Deterministic gate: affirmative interest plus affirmative current consent, "
                "with no re-consent, withdrawal or contact-suppression block."
            ),
            branch=CONTACT, annotation=HIDDEN_READONLY,
        ),
    ]
    insertion = next(i for i, row in enumerate(contact) if row["Variable / Field Name"] == "oc_ack_permission")
    contact[insertion:insertion] = consent_admin

    consent = [
        _field(
            "pc_intro", "project_owner_consent", "descriptive",
            "<strong>DEA Validation Study – Project Owner Review</strong><br>"
            "This study validates a portfolio view derived from the public DEA register dashboard "
            "({{DASHBOARD_URL}}). The proposed classifications were produced using a large language "
            "model and are being checked using project-informed validation evidence.",
            section="Project Owner Consent", branch=CONTACT,
        ),
        _field(
            "pc_reason", "project_owner_consent", "descriptive",
            "You were approached because you are named as a researcher on eligible DEA register "
            "projects. You may be invited to review <strong>[oc_projects_offered]</strong> project(s).",
            branch=CONTACT,
        ),
        _field(
            "pc_burden", "project_owner_consent", "descriptive",
            "Each review is expected to take about <strong>[oc_minutes_per_project]</strong> minutes; "
            "the estimated total burden if all offered reviews are completed is "
            "<strong>[oc_est_total_minutes]</strong> minutes.",
            branch=CONTACT,
        ),
        _field(
            "pc_scope", "project_owner_consent", "descriptive",
            "This one consent covers the separate project reviews described in the participant "
            "information. You may review all, some or none of the projects. Every later review "
            "remains optional. Consent will be sought again if the research activities or intended "
            "use of responses change substantially.",
            branch=CONTACT,
        ),
        _field(
            "pc_voluntary", "project_owner_consent", "descriptive",
            "Participation is voluntary. Declining has no consequences. You may skip any project "
            "review or stop at any time.",
            branch=CONTACT,
        ),
        _field(
            "pc_data", "project_owner_consent", "descriptive",
            "Please do not provide confidential, sensitive or restricted information. Responses "
            "will be used for methodological validation, adjudication triggers and possible taxonomy "
            "improvement. Restricted contact details are held separately from project-review responses "
            "and ordinary analytical exports. Raw comments or named responses will not be published "
            "without the relevant separate permission.",
            branch=CONTACT,
        ),
        _field(
            "pc_withdrawal", "project_owner_consent", "descriptive",
            WITHDRAWAL_WORDING, branch=CONTACT,
        ),
        _field(
            "pc_contact", "project_owner_consent", "descriptive",
            "Questions may be sent to {{STUDY_EMAIL}} before deciding or at any later point.",
            branch=CONTACT,
        ),
        _field(
            "pc_reference", "project_owner_consent", "descriptive",
            "Consent survey reference: <strong>[owner_record_id]</strong>", branch=CONTACT,
        ),
        _field(
            "pc_info_version", "project_owner_consent", "text",
            "Participant-information version", branch=CONTACT, required=True,
            annotation="@READONLY",
        ),
        _field(
            "pc_decision", "project_owner_consent", "radio",
            "I have read and understood the information provided, have had the opportunity to ask "
            "questions, and agree to take part in the project-owner validation exercise described above.",
            choice_text="1, Yes, I agree to take part | 0, No, I do not wish to take part",
            note="A No response ends this consent survey and keeps every project-review link blocked.",
            branch=CONTACT, required=True,
        ),
        _field(
            "pc_decline_end", "project_owner_consent", "descriptive",
            "Thank you for considering the study. No project-review links will be released.",
            branch=f"({CONTACT}) and [pc_decision] = '0'",
        ),
    ]

    for row in assignment:
        if row["Variable / Field Name"] == "owner_link_release":
            row["Choices, Calculations, OR Slider Labels"] = (
                "0, Blocked | 1, Eligible after interest and current consent; not sent | 2, Released"
            )
            row["Field Note"] = (
                "A value above 0 requires affirmative interest and current affirmative consent on "
                "the linked contact record. Missing, declined, withdrawn or stale consent blocks release."
            )

    review = [row for row in review if row["Variable / Field Name"] != "po_ack"]
    for row in review:
        row["Branching Logic (Show field only if...)"] = row[
            "Branching Logic (Show field only if...)"
        ].replace(v01.REVIEW, ASSIGNMENT)
        if row["Variable / Field Name"] == "po_intro":
            row["Field Label"] = (
                "This project review forms part of the DEA register portfolio-view validation. "
                "You previously agreed to participate in this validation exercise. Completing this "
                "particular project review remains voluntary. You may skip this review or stop at any "
                "time. It is expected to take about {{ESTIMATED_MINUTES_PER_PROJECT}} minutes."
            )
        elif row["Variable / Field Name"] == "po_privacy":
            row["Field Label"] = (
                "Please do not provide confidential, sensitive, restricted or personally identifying "
                f"information. {WITHDRAWAL_WORDING} Questions may be sent to {{STUDY_EMAIL}}."
            )

    rows = contact + consent + assignment + review
    counts = {form: sum(row["Form Name"] == form for row in rows) for form in FORMS}
    if counts != FORM_COUNTS or len(rows) != sum(FORM_COUNTS.values()):
        raise RuntimeError(f"candidate-0.2 field-count drift: {counts}")
    names = [row["Variable / Field Name"] for row in rows]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate candidate-0.2 variable name")
    return rows, meta


def _row_signature(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[header] for header in HEADERS)


def build_specs(rows: list[dict[str, str]], meta: dict[str, object]) -> None:
    with V01_DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
        old_rows = list(csv.DictReader(handle))
    old_by = {row["Variable / Field Name"]: row for row in old_rows}
    new_names = {row["Variable / Field Name"] for row in rows}
    spec_rows: list[dict[str, object]] = []
    for row in rows:
        name = row["Variable / Field Name"]
        form = row["Form Name"]
        if name not in old_by:
            source = "new_for_one_time_consent"
        elif _row_signature(row) == _row_signature(old_by[name]):
            source = "retained_unchanged_from_candidate_0.1"
        else:
            source = "modified_for_one_time_consent"
        respondent = "yes" if form in {"project_owner_consent", "project_owner_review"} else "no"
        if form == "owner_contact_admin":
            analytical = "yes" if name in {"owner_record_id", "record_type", "owner_id"} else "no"
        else:
            analytical = "no" if row["Field Type"] == "descriptive" else "yes"
        restricted = (
            "direct_identifier" if row["Identifier?"] == "y" else
            "restricted_qualitative" if name in {"po_note", "po_nonpublic_note", "po_other_comment"} else
            "consent_metadata" if form == "project_owner_consent" else "standard"
        )
        spec_rows.append({
            "variable": name,
            "form": form,
            "field_type": row["Field Type"],
            "choices": row["Choices, Calculations, OR Slider Labels"],
            "validation": row["Text Validation Type OR Show Slider Number"],
            "branching": row["Branching Logic (Show field only if...)"] ,
            "required": row["Required Field?"],
            "identifier": row["Identifier?"],
            "respondent_visible": respondent,
            "ordinary_analytical_export": analytical,
            "restriction": restricted,
            "candidate_source": source,
        })
    write_csv(
        FIELD_SPEC,
        ["variable", "form", "field_type", "choices", "validation", "branching", "required", "identifier", "respondent_visible", "ordinary_analytical_export", "restriction", "candidate_source"],
        spec_rows,
    )

    export_rows = []
    for row in rows:
        name = row["Variable / Field Name"]
        form = row["Form Name"]
        if form == "owner_contact_admin":
            include = "yes" if name in {"owner_record_id", "record_type", "owner_id"} else "no"
        else:
            include = "no" if row["Field Type"] == "descriptive" else "yes"
        export_rows.append({
            "variable": name,
            "source_form": form,
            "include_in_ordinary_analytical_export": include,
            "restricted_or_public": (
                "restricted" if row["Identifier?"] == "y" or name in {"po_note", "po_nonpublic_note", "po_other_comment"}
                else "internal_analysis"
            ),
            "notes": (
                "Restricted contact/consent administration" if form == "owner_contact_admin" else
                "One-time contact-record consent metadata" if form == "project_owner_consent" else
                "Stable assignment/response column"
            ),
        })
    export_rows += [
        {
            "variable": f"{form}_complete", "source_form": form,
            "include_in_ordinary_analytical_export": "yes" if form in {"project_owner_consent", "owner_assignment_admin", "project_owner_review"} else "no",
            "restricted_or_public": "internal_analysis",
            "notes": "REDCap-generated form status",
        }
        for form in FORMS
    ]
    export_rows += [
        {
            "variable": "project_owner_consent_timestamp",
            "source_form": "project_owner_consent",
            "include_in_ordinary_analytical_export": "yes",
            "restricted_or_public": "internal_analysis",
            "notes": "REDCap-native consent survey completion timestamp; operational consent date/time",
        },
        {
            "variable": "project_owner_review_questionnaire_version",
            "source_form": "configuration",
            "include_in_ordinary_analytical_export": "yes",
            "restricted_or_public": "internal_analysis",
            "notes": f"Readable participant-facing review tool: {QUESTIONNAIRE_VERSION}",
        },
        {
            "variable": "owner_current_consent",
            "source_form": "derived_contact_consent_join",
            "include_in_ordinary_analytical_export": "yes",
            "restricted_or_public": "internal_analysis",
            "notes": (
                "Deterministic: interested; pc_decision=1; current pc_info_version; no re-consent, "
                "consent-withdrawal or contact-suppression block"
            ),
        },
        {
            "variable": "project_owner_review_timestamp",
            "source_form": "project_owner_review",
            "include_in_ordinary_analytical_export": "yes",
            "restricted_or_public": "internal_analysis",
            "notes": "REDCap-native review survey completion timestamp",
        },
        {
            "variable": "owner_analytical_complete",
            "source_form": "derived",
            "include_in_ordinary_analytical_export": "yes",
            "restricted_or_public": "internal_analysis",
            "notes": (
                "Deterministic: current contact-level consent; every populated domain/purpose verdict; "
                "both tag-correctness responses; public-entry sufficiency. Quote/comments excluded."
            ),
        },
    ]
    write_csv(
        EXPORT_SPEC,
        ["variable", "source_form", "include_in_ordinary_analytical_export", "restricted_or_public", "notes"],
        export_rows,
    )

    removed = sorted(set(old_by) - new_names)
    source_counts: dict[str, int] = {}
    for row in spec_rows:
        source_counts[str(row["candidate_source"])] = source_counts.get(str(row["candidate_source"]), 0) + 1
    branch_spec = {
        "version": VERSION,
        "status": "development_candidate_unfrozen_live_qa_pending",
        "classic_non_longitudinal": True,
        "forms": list(FORMS),
        "field_counts": FORM_COUNTS,
        "record_type": {1: "Contact", 2: "Assignment"},
        "guards": {"contact": CONTACT, "consent": CONTACT, "assignment": ASSIGNMENT, "review": ASSIGNMENT},
        "survey_instruments": ["project_owner_consent", "project_owner_review"],
        "admin_only_instruments": ["owner_contact_admin", "owner_assignment_admin"],
        "consent_once_per_owner_id": True,
        "consent_information_version": CONSENT_INFO_VERSION,
        "review_questionnaire_version": QUESTIONNAIRE_VERSION,
        "consent_timestamp": "project_owner_consent_timestamp",
        "reconsent_trigger": "oc_reconsent_required == 1 after substantial activity or intended-use change",
        "link_release_requires": [
            "oc_eoi_status == 2", "pc_decision == 1",
            f"pc_info_version == {CONSENT_INFO_VERSION}",
            "oc_reconsent_required == 0", "oc_consent_withdrawal == 0",
            "oc_contact_suppression == 0",
        ],
        "record_specific_links_only": True,
        "label_mapping": meta["mapping"],
        "domain_slots": 12,
        "purpose_slots": 8,
        "purpose_maximum": 2,
        "binary_tags_always_reviewed": True,
        "quotation_permission_response_level": True,
        "named_acknowledgement_contact_level_only": True,
        "withdrawal_wording": WITHDRAWAL_WORDING,
        "configuration_placeholders": [
            "{{DASHBOARD_URL}}", "{{ESTIMATED_MINUTES_PER_PROJECT}}",
            "{{WITHDRAWAL_DATE}}", "{{STUDY_EMAIL}}",
        ],
        "analytical_completion": {
            "consent": "linked contact has current affirmative consent",
            "domains": "every prop_dNN == 1 has po_dNN_fit in 1,2,3",
            "purposes": "every prop_pNN == 1 has po_pNN_fit in 1,2,3",
            "tags": "po_t01_correct and po_t02_correct in 1,0,2",
            "sufficiency": "po_sufficiency in 1,2,3",
            "not_required": ["po_quote_permission", "po_other_comment"],
        },
        "difference_from_candidate_0.1": {
            "field_source_counts": source_counts,
            "removed_fields": removed,
            "renamed_fields": {},
            "reason": "one-time researcher-level informed consent replaces per-assignment participation acknowledgement",
        },
        "live_project": {
            "pid": 9149,
            "title": "DEA Validation Study – Project Owner Review",
            "status": "Development",
            "connection_performed": False,
        },
    }
    BRANCH_SPEC.write_text(yaml.safe_dump(branch_spec, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _proposal(domain_codes: list[int], purpose_codes: list[int], tag_values: tuple[int, int]) -> dict[str, int]:
    payload = {f"prop_d{i:02d}": int(i in domain_codes) for i in range(1, 13)}
    payload.update({f"prop_p{i:02d}": int(i in purpose_codes) for i in range(1, 9)})
    payload.update({"prop_t01": tag_values[0], "prop_t02": tag_values[1]})
    return payload


def _contact(key: str, owner: str, name: str, email: str, **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "owner_record_id": key, "record_type": 1, "owner_id": owner,
        "oc_name": name, "oc_email": email, "oc_affiliation": "Fictional Research Institute",
        "oc_contact_source": 2, "oc_contactability": 1,
        "oc_eligible_projects": 2, "oc_projects_offered": 2,
        "oc_minutes_per_project": 10, "oc_est_total_minutes": 20,
        "oc_eoi_invite_date": "2026-07-01", "oc_eoi_status": 2,
        "oc_eoi_response_date": "2026-07-02", "oc_projects_accepted": 2,
        "oc_contact_suppression": 0, "oc_recruit_route": 1, "oc_sequence_pos": 1,
        "oc_reconsent_required": 0, "oc_consent_withdrawal": 0,
        "oc_ack_permission": 0,
    }
    row.update(values)
    return row


def _assignment(key: str, owner: str, number: int, release: int, domains: list[int], purposes: list[int], tags: tuple[int, int], **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "owner_record_id": key, "record_type": 2, "owner_id": owner,
        "owner_assignment_id": f"SYN-ASG-{number:03d}",
        "source_record_id": f"SYNTHETIC-RECORD-{number:03d}",
        "official_project_id": f"SYNTHETIC-PROJECT-{number:03d}",
        "project_title": f"Synthetic project review {number}",
        "datasets_used": f"Synthetic dataset {number}",
        "public_register_url": f"https://example.invalid/register/{number:03d}",
        "production_ver": "synthetic-production-1", "taxonomy_ver": "dict-1.0-rc2",
        "proposal_output_sha256": format(number, "064x"),
        "owner_recruit_route": 1, "owner_sequence_pos": number,
        "owner_invite_batch": 1, "owner_link_release": release,
        "owner_withdrawal_status": 0, "instrument_ver": VERSION,
        **_proposal(domains, purposes, tags),
    }
    if release == 2:
        row["owner_invite_date"] = "2026-07-05"
    row.update(values)
    return row


def build_fixtures(rows: list[dict[str, str]]) -> None:
    names = [row["Variable / Field Name"] for row in rows]
    contacts = [
        _contact("A1B2C3D4", "SYN-OWNER-01", "Avery Example", "avery@example.invalid", pc_info_version=CONSENT_INFO_VERSION, pc_decision=1, oc_ack_permission=1, oc_ack_name="Avery Example", oc_ack_affiliation="Fictional Research Institute", oc_ack_permission_date="2026-07-04", oc_ack_permission_source="Synthetic post-participation email"),
        _contact("B2C3D4E5", "SYN-OWNER-02", "Blair Example", "blair@example.invalid", pc_info_version=CONSENT_INFO_VERSION, pc_decision=0),
        _contact("C3D4E5F6", "SYN-OWNER-03", "Casey Example", "casey@example.invalid"),
        _contact("D4E5F6G7", "SYN-OWNER-04", "Devon Example", "devon@example.invalid", pc_info_version=OLD_CONSENT_INFO_VERSION, pc_decision=1, oc_reconsent_required=1),
        _contact("E5F6G7H8", "SYN-OWNER-05", "Emery Example", "emery@example.invalid", pc_info_version=CONSENT_INFO_VERSION, pc_decision=1, oc_consent_withdrawal=2, oc_consent_withdraw_date="2026-07-12"),
        _contact("F6G7H8J9", "SYN-OWNER-06", "Finley Example", "finley@example.invalid", oc_eoi_status=3, oc_eoi_response_date="2026-07-02", oc_projects_accepted="", oc_contact_suppression=1),
        _contact("G7H8J9K2", "SYN-OWNER-07", "Gray Example", "gray@example.invalid", pc_info_version=CONSENT_INFO_VERSION, pc_decision=1, oc_eligible_projects=1, oc_projects_offered=1, oc_projects_accepted=1, oc_est_total_minutes=10, oc_recruit_route=2, oc_sequence_pos="", oc_supp_reason="Synthetic supplementary coverage rationale fixed before contact."),
    ]
    assignments = [
        _assignment("H8J9K2L3", "SYN-OWNER-01", 1, 2, [1], [1], (1, 0)),
        _assignment("J9K2L3M4", "SYN-OWNER-01", 2, 2, [2, 3], [1, 2], (0, 1)),
        _assignment("K2L3M4N5", "SYN-OWNER-02", 3, 0, [4], [4], (1, 1)),
        _assignment("L3M4N5P6", "SYN-OWNER-03", 4, 0, [5], [5], (0, 0)),
        _assignment("M4N5P6Q7", "SYN-OWNER-04", 5, 0, [6], [6], (1, 0)),
        _assignment("N5P6Q7R8", "SYN-OWNER-05", 6, 0, [7], [7], (0, 1)),
        _assignment("P6Q7R8S9", "SYN-OWNER-07", 7, 1, [9], [1], (1, 1), owner_recruit_route=2, owner_sequence_pos="", owner_invite_batch=5),
    ]
    import_rows: list[dict[str, object]] = []
    for payload in contacts + assignments:
        row = {name: "" for name in names}
        row.update(payload)
        import_rows.append(row)
    write_csv(IMPORT_FIXTURE, names, import_rows)

    responses = [
        {"case_id": "complete_first_review_quote_yes", "owner_record_id": "H8J9K2L3", "expected_valid": True, "expected_analytical_complete": True, "data": {"po_d01_fit": 1, "po_d01_vis": 1, "po_p01_fit": 1, "po_p01_vis": 1, "po_t01_correct": 1, "po_t01_det": 1, "po_t02_correct": 1, "po_t02_det": 1, "po_miss_domain": 0, "po_miss_purpose": 0, "po_miss_tag": 0, "po_sufficiency": 1, "po_taxonomy_fit": 1, "po_nonpublic": 0, "po_quote_permission": 1}},
        {"case_id": "complete_later_review_same_consent_quote_no", "owner_record_id": "J9K2L3M4", "expected_valid": True, "expected_analytical_complete": True, "data": {"po_d02_fit": 2, "po_d02_vis": 2, "po_d03_fit": 3, "po_d03_vis": 3, "po_p01_fit": 1, "po_p01_vis": 1, "po_p02_fit": 2, "po_p02_vis": 4, "po_t01_correct": 0, "po_t01_det": 2, "po_t02_correct": 2, "po_t02_det": 0, "po_miss_domain": 1, "po_miss_domains": [4], "po_miss_purpose": 0, "po_miss_tag": 1, "po_miss_tags": [1], "po_sufficiency": 2, "po_taxonomy_fit": 2, "po_tax_issue": [1], "po_note": "Synthetic explanation of the affected labels.", "po_nonpublic": 1, "po_nonpublic_note": "Synthetic prior project involvement.", "po_quote_permission": 0}},
        {"case_id": "structurally_complete_but_consent_declined", "owner_record_id": "K2L3M4N5", "expected_valid": True, "expected_analytical_complete": False, "data": {"po_d04_fit": 1, "po_d04_vis": 1, "po_p04_fit": 1, "po_p04_vis": 1, "po_t01_correct": 1, "po_t01_det": 1, "po_t02_correct": 1, "po_t02_det": 1, "po_miss_domain": 0, "po_miss_purpose": 0, "po_miss_tag": 0, "po_sufficiency": 1, "po_taxonomy_fit": 1, "po_nonpublic": 0, "po_quote_permission": 2}},
        {"case_id": "incomplete_current_consent", "owner_record_id": "H8J9K2L3", "expected_valid": True, "expected_analytical_complete": False, "data": {"po_d01_fit": 1}},
    ]
    for case in responses:
        case["strict_validation"] = case["case_id"] != "incomplete_current_consent"
    fixture = {
        "fixture_status": "synthetic_only",
        "candidate_version": VERSION,
        "consent_information_version": CONSENT_INFO_VERSION,
        "review_questionnaire_version": QUESTIONNAIRE_VERSION,
        "contains_real_researchers": False,
        "contains_real_emails": False,
        "contains_real_record_ids": False,
        "contacts": contacts,
        "assignments": assignments,
        "responses": responses,
    }
    RESPONSE_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    RESPONSE_FIXTURE.write_text(yaml.safe_dump(fixture, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    if sha256(V01_DICTIONARY) != V01_SHA256:
        raise RuntimeError("owner-redcap-candidate-0.1 dictionary hash changed")
    if sha256(SCRATCH_DICTIONARY) != SCRATCH_SHA256:
        raise RuntimeError("frozen scratch candidate-0.7 dictionary hash changed")
    rows, meta = build_dictionary()
    write_csv(DICTIONARY, HEADERS, rows)
    build_specs(rows, meta)
    build_fixtures(rows)
    print(yaml.safe_dump({
        "version": VERSION,
        "dictionary": str(DICTIONARY.relative_to(ROOT)),
        "dictionary_sha256": sha256(DICTIONARY),
        "dictionary_size": DICTIONARY.stat().st_size,
        "fields": len(rows),
        "forms": FORM_COUNTS,
        "status": "development_candidate_unfrozen_live_qa_pending",
    }, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
