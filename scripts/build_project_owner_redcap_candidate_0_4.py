#!/usr/bin/env python3
"""Build owner-redcap-candidate-0.4 deterministically and entirely offline.

Candidate 0.4 is a versioned transformation of candidate 0.3.  It preserves
the predecessor and all taxonomy/proposal inputs, aligns owner-level consent
with Participant Information and Consent v3, and removes the obsolete
per-review quotation-permission field.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Iterable

import yaml

try:
    import scripts.build_project_owner_redcap_candidate_0_3 as base
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    import build_project_owner_redcap_candidate_0_3 as base


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "preregistration/package/06_redcap"
LIVE_QA = PACKAGE / "live_qa"
VERSION = "owner-redcap-candidate-0.4"
STATUS = "development_candidate_unfrozen_pre_recruitment_live_migration_and_qa_pending"
PARTICIPANT_INFO_VERSION = "project-owner-information-v3"
CONSENT_FORM_VERSION = "owner-consent-v3"

DICTIONARY = PACKAGE / "project_owner_redcap_data_dictionary_candidate_0.4.csv"
SPEC = PACKAGE / "project_owner_redcap_candidate_0.4_spec.md"
LIVE_CONFIG = PACKAGE / "project_owner_redcap_candidate_0.4_live_configuration.md"
IMPORT_FIXTURE = LIVE_QA / "project_owner_synthetic_import_candidate_0.4.csv"
FIELD_SPEC = PACKAGE / "project_owner_redcap_field_specification_candidate_0.4.csv"
BRANCH_SPEC = PACKAGE / "project_owner_redcap_branching_specification_candidate_0.4.yaml"
EXPORT_SPEC = PACKAGE / "project_owner_redcap_expected_export_candidate_0.4.csv"
FORMATTING_AUDIT = PACKAGE / "project_owner_redcap_formatting_audit_candidate_0.4.csv"
PARTICIPANT_SOURCE = (
    PACKAGE
    / "participant_materials/Project_Owner_Participant_Information_and_Consent_v3.docx"
)
QUESTIONNAIRE_SOURCE = (
    PACKAGE
    / "participant_materials/Project_Owner_Review_Questionnaire_v3.docx"
)

CONSENT_ITEMS = (
    (
        "consent_read_info",
        "I have read and understood the participant information above.",
    ),
    (
        "consent_understand_invitation",
        "I understand why I have been invited and what taking part involves.",
    ),
    (
        "consent_voluntary",
        "I understand that participation is voluntary and that I may review all, some or none of the projects offered.",
    ),
    (
        "consent_no_nonpublic",
        "I understand that I should not disclose confidential, sensitive or otherwise non-public information.",
    ),
    (
        "consent_confidentiality_limits",
        "I understand that my information will be handled confidentially and that direct identifiers will not appear in research outputs, but complete anonymity cannot be guaranteed because the participant group is small and responses concern publicly identifiable projects.",
    ),
    (
        "consent_withdrawal_deadline",
        "I understand that I may withdraw a submitted review by emailing the study team by Friday 2 October 2026, and that after this date responses can no longer be removed.",
    ),
    (
        "consent_quote_process",
        "I understand that if the study wishes to quote my comments, I will be sent the exact proposed wording in advance and it will only be used if I agree.",
    ),
    (
        "consent_retention_reanalysis",
        "I agree that my pseudonymised research data may be retained for 10 years and used by the research team for verification and further analyses directly related to this validation study and the improvement of the classification framework and dashboard.",
    ),
    (
        "consent_complaints",
        "I am aware of who I should contact if I wish to lodge a complaint.",
    ),
    (
        "consent_acknowledgement",
        "I understand that choosing to be acknowledged by name is optional, is separate to my decision to take part, and would make my participation in this study permanently and publicly identifiable.",
    ),
)
CONSENT_NAMES = tuple(name for name, _ in CONSENT_ITEMS)
ALL_CONFIRMED_EXPRESSION = (
    "if("
    + " and ".join(f"[{name}] = '1'" for name in CONSENT_NAMES)
    + ", 1, 0)"
)
QUEUE_CONDITION = (
    "[owner_consent_complete] = '2' and [owner_consent] = '1' and "
    "[intended_recipient] = '1' and [consent_items_complete] = '1'"
)
FINAL_CONSENT_LABEL = (
    "I consent to participate in the study. I understand that my name, professional email "
    "address, consent record, survey responses and optional free-text comments will be used "
    "for the purposes explained to me, that UCL is the data controller, that I can contact "
    "UCL’s Data Protection Officer at data-protection@ucl.ac.uk, and that according to data "
    "protection legislation ‘public task’ will be the lawful basis for processing."
)
ACKNOWLEDGEMENT_LABEL = (
    "We would like to acknowledge the researchers who contributed to this study. Would you "
    "like to be acknowledged by name in resulting publications? Choosing to be acknowledged "
    "makes your involvement in this study permanently and publicly identifiable. Your answer "
    "does not affect your participation. If you decline acknowledgement, the study team will not "
    "name or acknowledge you in resulting outputs."
)
ACKNOWLEDGEMENT_CHOICES = (
    "1, Yes, I would like to be acknowledged by name | "
    "0, No, I would prefer not to be named | "
    "2, I would prefer to decide later. Please contact me about this"
)
QUESTIONNAIRE_FIELD_LABELS = {
    **{
        f"po_d{slot:02d}_vis_explain": (
            "Please briefly explain why the basis for this Research Domain is only partly "
            "visible, not visible, or unclear in the public project title and listed datasets."
        )
        for slot in range(1, 5)
    },
    **{
        f"po_p{slot:02d}_vis_explain": (
            "Please briefly explain why the basis for this Analytical Purpose is only partly "
            "visible, not visible, or unclear in the public project title and listed datasets."
        )
        for slot in range(1, 3)
    },
    "po_t01_vis": (
        "Is the basis for the proposed status of the Demographic disparities / equity tag "
        "visible in the public project title and datasets listed above?"
    ),
    "po_t01_vis_explain": (
        "Please briefly explain why the basis for this proposed tag status is only partly "
        "visible, not visible, or unclear in the public project title and listed datasets."
    ),
    "po_t02_correct_explain": (
        "Please briefly explain why the proposed status for the COVID-19 & Pandemic tag does "
        "not fit the actual project."
    ),
    "po_t02_vis": (
        "Is the basis for the proposed status of the COVID-19 & Pandemic tag visible in the "
        "public project title and datasets listed above?"
    ),
    "po_t02_vis_explain": (
        "Please briefly explain why the basis for this proposed tag status is only partly "
        "visible, not visible, or unclear in the public project title and listed datasets."
    ),
    "po_miss_domains": "Which Research Domain label or labels are missing?",
    "po_miss_domain_basis": (
        "Please briefly explain why the selected Research Domain label or labels should be included."
    ),
    "po_miss_purposes": "Which Analytical Purpose label or labels are missing?",
    "po_miss_purpose_basis": (
        "Please briefly explain why the selected Analytical Purpose label or labels should be "
        "included."
    ),
    "po_miss_tag_basis": (
        "Please briefly explain why the selected tag or tags should have been assigned or applied "
        "differently."
    ),
    "po_suff_explain": "What important information is missing or unclear in the public register entry?",
    "po_nonpublic": (
        "Did any of your answers rely on relevant project knowledge that is not visible in the "
        "public register entry?"
    ),
    "po_nonpublic_note": (
        "Please briefly describe the type of additional context that informed your answer."
    ),
    "po_other_comment": (
        "Do you have any other comments about the proposed classifications, the public register "
        "entry, or the taxonomy?"
    ),
}
APPENDIX_B_CONSENT_WORDING = (
    "Affirmative intended-recipient confirmation, all ten consent confirmations and affirmative "
    "final consent must be recorded once at owner level, with the Owner Consent instrument "
    "complete. The resulting valid owner-level consent record is joined to each repeating project "
    "review."
)

# Candidate 0.3 is a historical predecessor.  Generation stops if any of its
# implementation or generated artefacts has changed.
C03_HASHES = {
    "scripts/build_project_owner_redcap_candidate_0_3.py": "b98bfabaa68a6ea5b1f0f7be0f694d9995996ebe389f7dda49866fcf7e6a22b4",
    "scripts/validate_project_owner_redcap_candidate_0_3.py": "d4f8750ddcfb42d53d38aafd4a39c76f408eeeb0215f236c68db31730fc213df",
    "tests/test_project_owner_redcap_candidate_0_3.py": "11ede010a255aa9890479d62a2d2cdde30ed9371af10c12ced623e2de27927f6",
    "preregistration/package/06_redcap/project_owner_redcap_data_dictionary_candidate_0.3.csv": "97219123588878b7a086a406d08a24e66966b7b4e38e740117335a429d2e011b",
    "preregistration/package/06_redcap/project_owner_redcap_field_specification_candidate_0.3.csv": "88154a52b62241e69ffd73e736744fab0728742e37350d123fe363ba4a3f11af",
    "preregistration/package/06_redcap/project_owner_redcap_branching_specification_candidate_0.3.yaml": "8fc9997cdd86a0871b998070e84215cad30218d8f408bd12a6b0d32eaab2b44e",
    "preregistration/package/06_redcap/project_owner_redcap_expected_export_candidate_0.3.csv": "f95c9f85b41122eec40d035ae074f63148f8524c723a57c5b17ffaf2a18bc1d2",
    "preregistration/package/06_redcap/project_owner_redcap_formatting_audit_candidate_0.3.csv": "6667a1e48f876f73fd455f524e934753c8f80029aca3735900c61d8760df6fcb",
    "preregistration/package/06_redcap/project_owner_redcap_candidate_0.3_spec.md": "ecafc2765930879a61a3f883c22e0b3c7a7afca5269af849472a361a3c09db8b",
    "preregistration/package/06_redcap/project_owner_redcap_candidate_0.3_live_configuration.md": "48df58eff2cb470c807ed8ddc1742fae6b835b2201a12c75ca66b4a94d80b891",
    "preregistration/package/06_redcap/live_qa/project_owner_synthetic_import_candidate_0.3.csv": "0aa47bf0089c76bcb10a2dcf9d208005a18e976eb28cef908566501db4ba3444",
}
PARTICIPANT_SOURCE_SHA256 = "3ceb089b06e707fb815f6fa3dab6cc261617e254aadeffe386ed6e131848af4a"
PARTICIPANT_SOURCE_SIZE = 35369
QUESTIONNAIRE_SOURCE_SHA256 = "05f36763b3557ac4a1d65fbd529abdd50190246c7314ae22d3b0eba0fde6c524"
QUESTIONNAIRE_SOURCE_SIZE = 19825


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def check_sources() -> None:
    for relative, expected in C03_HASHES.items():
        actual = sha256(ROOT / relative)
        if actual != expected:
            raise RuntimeError(
                f"candidate-0.3 predecessor changed: {relative}: {actual}"
            )
    participant_sources = (
        ("participant-information v3", PARTICIPANT_SOURCE, PARTICIPANT_SOURCE_SHA256, PARTICIPANT_SOURCE_SIZE),
        ("review-questionnaire v3", QUESTIONNAIRE_SOURCE, QUESTIONNAIRE_SOURCE_SHA256, QUESTIONNAIRE_SOURCE_SIZE),
    )
    for label, path, expected_hash, expected_size in participant_sources:
        if not path.is_file():
            raise RuntimeError(f"missing canonical {label} source: {path}")
        actual_hash = sha256(path)
        actual_size = path.stat().st_size
        if actual_hash != expected_hash or actual_size != expected_size:
            raise RuntimeError(
                f"canonical {label} source changed: sha256={actual_hash}, size={actual_size}; "
                f"expected sha256={expected_hash}, size={expected_size}"
            )
    base.check_frozen_sources()


def configure_base_outputs() -> None:
    """Point reusable candidate-0.3 generators only at versioned 0.4 outputs."""

    base.VERSION = VERSION
    base.STATUS = STATUS
    base.PARTICIPANT_INFO_VERSION = PARTICIPANT_INFO_VERSION
    base.CONSENT_FORM_VERSION = CONSENT_FORM_VERSION
    base.DICTIONARY = DICTIONARY
    base.SPEC = SPEC
    base.LIVE_CONFIG = LIVE_CONFIG
    base.IMPORT_FIXTURE = IMPORT_FIXTURE
    base.FIELD_SPEC = FIELD_SPEC
    base.BRANCH_SPEC = BRANCH_SPEC
    base.EXPORT_SPEC = EXPORT_SPEC
    base.FORMATTING_AUDIT = FORMATTING_AUDIT


def build_dictionary() -> tuple[list[dict[str, str]], dict[str, object]]:
    rows, _ = base.build_dictionary()
    by_name = {row["Variable / Field Name"]: row for row in rows}

    by_name["participant_info_link"]["Field Label"] = (
        "<strong>Participant Information Sheet v3</strong><br>Read the full approved "
        "Participant Information Sheet displayed here before answering the consent questions. "
        "The controlled live configuration must attach or render "
        "Project_Owner_Participant_Information_and_Consent_v3.docx/PDF; this repository "
        "dictionary does not embed a production attachment."
    )
    by_name["owner_consent"]["Field Label"] = FINAL_CONSENT_LABEL
    by_name["owner_consent"]["Field Note"] = (
        "An affirmative response is valid only when consent_items_complete = 1. A No response "
        "remains available without confirming every statement and invokes the configured Stop Action."
    )
    by_name["ack_pref"]["Field Label"] = ACKNOWLEDGEMENT_LABEL
    by_name["ack_pref"]["Choices, Calculations, OR Slider Labels"] = (
        ACKNOWLEDGEMENT_CHOICES
    )
    by_name["ack_pref"]["Branching Logic (Show field only if...)"] = (
        "[intended_recipient] = '1' and [consent_items_complete] = '1' and "
        "[owner_consent] = '1'"
    )
    by_name["po_other_comment"]["Section Header"] = "Final comments"

    for name, label in QUESTIONNAIRE_FIELD_LABELS.items():
        by_name[name]["Field Label"] = label
    by_name["po_tax_issue"]["Choices, Calculations, OR Slider Labels"] = (
        "1, Missing or inadequately represented category | "
        "2, Ambiguous or overlapping category boundaries | 5, Other taxonomy problem"
    )

    quote_index = next(
        index
        for index, row in enumerate(rows)
        if row["Variable / Field Name"] == "po_quote_permission"
    )
    rows.pop(quote_index)

    intended_index = next(
        index
        for index, row in enumerate(rows)
        if row["Variable / Field Name"] == "wrong_recipient_stop"
    )
    consent_rows = [
        base.field(
            name,
            "owner_consent",
            "radio",
            wording,
            choices="1, Confirmed | 0, Not confirmed",
            branch="[intended_recipient] = '1'",
        )
        for name, wording in CONSENT_ITEMS
    ]
    consent_rows.append(
        base.field(
            "consent_items_complete",
            "owner_consent",
            "calc",
            "All ten owner-consent confirmations complete",
            choices=ALL_CONFIRMED_EXPRESSION,
            branch="[intended_recipient] = '1'",
            annotation=base.HIDDEN_ADMIN,
        )
    )
    rows[intended_index + 1 : intended_index + 1] = consent_rows

    counts = {form: sum(row["Form Name"] == form for row in rows) for form in base.FORMS}
    meta = {
        "field_counts": counts,
        "total_fields": len(rows),
        "production_cardinalities": base.production_cardinalities(),
        "taxonomy_menu_counts": base.MENU_COUNTS,
    }
    return rows, meta


def patch_generated_specs(rows: list[dict[str, str]]) -> None:
    with FIELD_SPEC.open(encoding="utf-8", newline="") as handle:
        field_rows = list(csv.DictReader(handle))
        field_headers = list(field_rows[0])
    for row in field_rows:
        name = row["variable"]
        if name in CONSENT_NAMES:
            row["participant_response"] = "yes"
            row["construct"] = "ethics_consent_confirmation"
            row["analytical_completion"] = "owner_consent_validity"
            row["requiredness_rationale"] = (
                "Separately auditable confirmation; valid affirmative consent requires stored code 1."
            )
            row["notes"] = "Ethics-resubmission v3 statement; blank by default and never pre-populated."
        elif name == "consent_items_complete":
            row["construct"] = "deterministic_all_consent_items_confirmed"
            row["analytical_completion"] = "owner_consent_validity"
            row["notes"] = ALL_CONFIRMED_EXPRESSION
    write_csv(FIELD_SPEC, field_headers, field_rows)

    branch = yaml.safe_load(BRANCH_SPEC.read_text(encoding="utf-8"))
    branch["version"] = VERSION
    branch["status"] = STATUS
    branch["field_counts"] = {
        form: sum(row["Form Name"] == form for row in rows) for form in base.FORMS
    }
    branch["survey_queue"]["project_review"]["condition"] = QUEUE_CONDITION
    branch["owner_consent_v3"] = {
        "participant_document": (
            "participant_materials/Project_Owner_Participant_Information_and_Consent_v3.docx"
        ),
        "participant_document_sha256": PARTICIPANT_SOURCE_SHA256,
        "participant_document_size_bytes": PARTICIPANT_SOURCE_SIZE,
        "intended_recipient_gate": "[intended_recipient] = '1'",
        "confirmation_fields": list(CONSENT_NAMES),
        "confirmation_choices": {1: "Confirmed", 0: "Not confirmed"},
        "all_confirmed_field": "consent_items_complete",
        "all_confirmed_calculation": ALL_CONFIRMED_EXPRESSION,
        "final_decision_field": "owner_consent",
        "valid_affirmative_condition": (
            "[intended_recipient] = '1' and [consent_items_complete] = '1' and "
            "[owner_consent] = '1' and [owner_consent_complete] = '2'"
        ),
        "active_decline_preserved": (
            "owner_consent remains visible when intended_recipient = 1 and stores 0 without "
            "requiring every confirmation to be affirmative"
        ),
        "acknowledgement_condition": (
            "[intended_recipient] = '1' and [consent_items_complete] = '1' and "
            "[owner_consent] = '1'"
        ),
        "raw_owner_consent_1_without_all_items": (
            "not valid consent; grants no queue access and must fail live QA if the production "
            "survey presents it as accepted affirmative participation"
        ),
    }
    branch["project_review_v3"] = {
        "participant_document": (
            "participant_materials/Project_Owner_Review_Questionnaire_v3.docx"
        ),
        "participant_document_sha256": QUESTIONNAIRE_SOURCE_SHA256,
        "participant_document_size_bytes": QUESTIONNAIRE_SOURCE_SIZE,
        "dictionary_alignment": (
            "Participant-facing question labels, response choices, inline checkbox "
            "microdefinitions, requiredness and branching are validated against candidate 0.4."
        ),
        "quotation_permission": "absent; agreement is requested by email only at point of use",
    }
    branch["stop_actions_manual_after_import"]["owner_consent"] = "No"
    branch["stop_actions_manual_after_import"]["invalid_affirmative"] = (
        "No unverified action tag is encoded. Live QA must establish that an attempted Yes with "
        "any item blank or Not confirmed is not treated as valid consent and reveals no Project Review."
    )
    completion = branch["analytical_completion"]
    completion["owner_join"] = [
        "intended_recipient = 1",
        "consent_items_complete = 1",
        "owner_consent = 1",
        "owner_consent_complete = 2",
    ]
    completion["excluded_optional_fields"] = [
        value
        for value in completion["excluded_optional_fields"]
        if value != "po_quote_permission"
    ]
    completion["quotation_policy"] = (
        "No REDCap quotation-permission response. Exact proposed wording and context are sent "
        "by email at point of use and used only after written agreement."
    )
    BRANCH_SPEC.write_text(
        yaml.safe_dump(branch, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    with EXPORT_SPEC.open(encoding="utf-8", newline="") as handle:
        export_rows = list(csv.DictReader(handle))
        export_headers = list(export_rows[0])
    for row in export_rows:
        if row["variable"] in CONSENT_NAMES:
            row["notes"] = (
                "Owner-row ethics confirmation; 1=Confirmed, 0=Not confirmed; blank on "
                "Project Review repeat rows."
            )
        elif row["variable"] == "consent_items_complete":
            row["analysis_role"] = "consent_validity"
            row["notes"] = (
                "Deterministic 1 only when all ten confirmation fields equal 1; blank on "
                "Project Review repeat rows."
            )
    write_csv(EXPORT_SPEC, export_headers, export_rows)


def build_documentation(meta: dict[str, object]) -> None:
    counts = meta["field_counts"]
    items = "\n".join(f"- `{name}` — {wording}" for name, wording in CONSENT_ITEMS)
    SPEC.write_text(
        f"""# Project Owner REDCap candidate 0.4 specification

Version: `{VERSION}`  
Status: unfrozen development candidate; pre-recruitment; controlled PID 9149 migration and live QA pending.  
Ethics trace: UCL Project ID 5004; Participant Information and Consent v3 dated 28 July 2026.

## Architecture and field counts

Candidate 0.4 preserves candidate 0.3 as its unchanged historical predecessor. It retains one pseudonymous owner record, non-repeating `owner_consent`, repeating `project_review`, pre-created review instances and one participant-specific Survey Queue link. It contains exactly two instruments and {meta['total_fields']} dictionary fields:

- `owner_consent`: {counts['owner_consent']} fields;
- `project_review`: {counts['project_review']} fields.

The Project Owner instrument remains unfrozen and non-authoritative. This candidate does not authorise recruitment or live migration. Both canonical participant DOCX files are pinned by SHA-256 and byte size; generation stops if either changes without an authorised metadata refresh.

## Ethics-to-REDCap consent traceability

The participant-visible sequence is: full Participant Information Sheet v3; `intended_recipient`; ten separately stored confirmations; final `owner_consent`; and optional `ack_pref` only after valid affirmative consent. The controlled live project must display or attach the full approved v3 information sheet before these fields.

Participant-document alignment is complete for candidate 0.4: the canonical consent DOCX contains the ten statements, final consent decision and acknowledgement wording represented here; the canonical Questionnaire v3 reproduces the participant-facing Project Review labels, response choices and inline checkbox microdefinitions. Its Appendix B records the complete owner-level consent-validity join. Q13 and participant-facing per-project quotation permission are absent. Controlled migration and live QA remain mandatory before recruitment.

{items}

Every confirmation is a separate owner-level radio field with stored codes `1, Confirmed | 0, Not confirmed`, starts blank, is never pre-populated, and branches only on `[intended_recipient] = '1'`. None appears in `project_review` or counts as a Project Review analytical outcome.

`consent_items_complete` is a survey-hidden calculated field with this exact expression:

```text
{ALL_CONFIRMED_EXPRESSION}
```

Valid affirmative consent is the composite condition:

```text
[intended_recipient] = '1' and [consent_items_complete] = '1' and [owner_consent] = '1' and [owner_consent_complete] = '2'
```

`owner_consent` retains the ethics-approved final decision wording and `1, Yes, I agree to take part | 0, No, I do not wish to take part`. It is shown whenever the intended-recipient response is Yes, so a participant can actively decline even when one or more confirmations are blank or Not confirmed. The existing No Stop Action ends the consent survey, hides acknowledgement and reveals no reviews. An attempted raw Yes with `consent_items_complete != 1` is not valid consent, grants no Survey Queue access and must be tested explicitly during controlled live QA. No unverified action tag or runtime claim is encoded.

The Project Review Survey Queue condition is exactly:

```text
{QUEUE_CONDITION}
```

Clearing a confirmation recalculates `consent_items_complete` to 0 and therefore invalidates queue eligibility.

## Acknowledgement and quotation policy

`ack_pref` remains optional, owner-level, and excluded from consent validity and analytical completion. It appears only after intended-recipient Yes, all ten confirmations and final consent Yes. Its participant-facing wording and the full Yes / No / Decide later response labels match the canonical consent document exactly. It states that declining means the study team will not name or acknowledge the participant in resulting outputs; it does not make an absolute non-disclosure claim.

Candidate 0.4 removes `po_quote_permission` from the generator, dictionary, Project Review count, branching specification, field and export specifications, fixture and analytical-completion documentation. It is not replaced. The current point-of-use policy is: if a comment is proposed for quotation, the participant is emailed the exact proposed wording and context, and it is used only after written agreement.

`po_final_warning` now follows `po_other_comment` immediately before submission and has no quotation-permission dependency.

## Fixture and long-format analysis

The synthetic fixture remains three owners, 19 pre-created Project Review instances and 22 long-format rows. Owner consent responses, all ten confirmations, `consent_items_complete`, final consent and acknowledgement are blank on import. Owner consent values occur only on the non-repeating owner row; Project Review repeat rows keep them blank. No synthetic participant is imported as consented.

Analysis must join the non-repeating owner row to reviews by `owner_id` and require intended-recipient Yes, all-confirmed 1, final consent Yes and Owner Consent complete. Review-row values alone must never establish consent.

## Scope exclusions and change record

Reason: align live consent implementation with ethics-resubmission v3 wording. Nature: ten owner-level consent confirmations added; final affirmative consent retained; active decline preserved; obsolete per-project quotation permission removed; acknowledgement language corrected. No taxonomy, classification, assignment, sampling, project metadata or participant data changed.
""",
        encoding="utf-8",
    )

    LIVE_CONFIG.write_text(
        f"""# Project Owner candidate 0.4 authorised-administrator migration and live-QA checklist

Status: instructions only. Do not execute without separate authorisation. Candidate 0.4 is unfrozen, pre-recruitment and non-authoritative. Recruitment remains blocked until every item passes.

## Before migration

Document baseline: verify the canonical consent and questionnaire DOCX files match the SHA-256 and byte-size metadata embedded in the generator and branching specification. Confirm the consent wording, questionnaire labels/options and Appendix B against the generated dictionary before any live action. The former untracked `- Copy` questionnaire is not required.

1. Confirm PID 9149 is the Development project and contains no real participant, contact, consent or response records.
2. Confirm only disposable synthetic candidate-0.3 data exist.
3. Archive/export the candidate-0.3 live dictionary, synthetic data export, Survey Queue/repeating settings and QA evidence without credentials or live links.
4. Delete only the verified disposable synthetic records through the authorised REDCap administrator workflow.

## Controlled dictionary migration

5. Import `project_owner_redcap_data_dictionary_candidate_0.4.csv` through the controlled REDCap dictionary process and resolve every reported change before applying it.
6. Confirm exactly two instruments: non-repeating Owner Consent (`owner_consent`) and repeating Project Review (`project_review`).
7. Confirm `project_review` is the only repeating instrument, custom label `[assignment_id] — [project_title]`, participant-created repeats disabled and auto-start disabled.
8. Display or attach the full approved `Project_Owner_Participant_Information_and_Consent_v3` information sheet before `intended_recipient`.
9. Confirm all ten confirmation fields are owner-level, blank by default, not import-populated and hidden after intended-recipient No.
10. Confirm `consent_items_complete` uses exactly `{ALL_CONFIRMED_EXPRESSION}` and is hidden/read-only to participants.
11. Configure the Project Review Survey Queue condition exactly as `{QUEUE_CONDITION}`. Do not include `ack_pref`.
12. Re-establish the existing Stop Action for `intended_recipient = No`: end the consent survey and reveal no consent items, acknowledgement or Project Reviews.
13. Re-establish the existing Stop Action for `owner_consent = No`: end the consent survey, collect no acknowledgement and reveal no Project Reviews.
14. Do not add an unverified action tag. Verify in the Online Designer that an attempted affirmative response with any confirmation blank or Not confirmed is not treated as valid participation and cannot reveal Project Reviews. If the target REDCap runtime cannot enforce this beyond the deterministic gate, stop migration approval and document the unresolved limitation before recruitment.

## Synthetic import and consent-path tests

15. Import `live_qa/project_owner_synthetic_import_candidate_0.4.csv`; verify three owner rows, 19 pre-created reviews and 22 total rows.
16. Verify no owner is imported with any consent confirmation, final consent, acknowledgement or all-confirmed value populated.
17. Test affirmative consent with all ten confirmations: calculated flag 1, final Yes, Owner Consent complete and Project Reviews visible.
18. Repeat the attempted affirmative test ten times, omitting or clearing one different confirmation each time: flag 0 and no Project Review visible.
19. Test active final No without all ten confirmations; verify the consent-decline Stop Action and no acknowledgement/reviews.
20. Test intended-recipient No; verify immediate termination and no downstream fields/reviews.
21. Verify `ack_pref` appears only after intended-recipient Yes, all-confirmed 1 and final consent Yes; verify it remains optional and does not affect queue eligibility or analytical completion.
22. Clear a previously confirmed item before final submission; verify the flag returns to 0 and Project Review eligibility is removed.

## Review, export and evidence tests

23. Verify `po_quote_permission` and any replacement quotation-permission question are absent.
24. Verify `po_final_warning` follows final comments immediately before submission and does not refer to quotation permission.
25. Verify existing Project Review wording and branching are unchanged apart from quotation-field removal and placement text.
26. Verify consent values export only on the non-repeating owner row and are blank on every Project Review repeat row.
27. Verify valid consent is joined onto review rows using all four conditions: intended recipient, all-confirmed, final Yes and Owner Consent complete.
28. Verify Save & Return Later, return-to-queue, completed-response modification disabled, no automatic next survey, no redirect and no participant-created repeat.
29. Verify desktop and mobile rendering of the full information sheet, ten statements, final decision, acknowledgement and repeated reviews.
30. Archive post-migration screenshots, dictionary, configuration evidence, synthetic export and source/live comparison in the approved restricted evidence location.

Recruitment is prohibited until all tests pass, residual differences are resolved or approved, and candidate 0.4 receives the required ethics/governance and repository approval.
""",
        encoding="utf-8",
    )


def main() -> int:
    check_sources()
    configure_base_outputs()
    rows, meta = build_dictionary()
    meta["fixture_columns"] = len(base.fixture_import_headers(rows))
    write_csv(DICTIONARY, base.HEADERS, rows)
    base.build_specs(rows, meta)
    patch_generated_specs(rows)
    base.build_formatting_audit(rows)
    build_documentation(meta)
    base.build_fixture(rows)
    print(
        yaml.safe_dump(
            {
                "version": VERSION,
                "status": STATUS,
                "dictionary": str(DICTIONARY.relative_to(ROOT)).replace("\\", "/"),
                "dictionary_sha256": sha256(DICTIONARY),
                "fields": meta["total_fields"],
                "forms": meta["field_counts"],
                "consent_confirmations": list(CONSENT_NAMES),
                "synthetic_fixture": {"owners": 3, "assignments": 19, "rows": 22},
            },
            sort_keys=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
