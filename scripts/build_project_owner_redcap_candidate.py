#!/usr/bin/env python3
"""Build owner-redcap-candidate-0.1 deterministically and entirely offline."""

from __future__ import annotations

import csv
import hashlib
import html
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "preregistration/package/06_redcap"
FIXTURES = ROOT / "tests/fixtures"
LIVE_QA = PACKAGE / "live_qa"
VERSION = "owner-redcap-candidate-0.1"
SCRATCH_DICTIONARY = PACKAGE / "redcap_data_dictionary_candidate.csv"
SCRATCH_SHA256 = "1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc"
DICTIONARY = PACKAGE / "project_owner_redcap_data_dictionary_candidate_0.1.csv"
FIELD_SPEC = PACKAGE / "project_owner_redcap_field_specification_candidate_0.1.csv"
BRANCH_SPEC = PACKAGE / "project_owner_redcap_branching_specification_candidate_0.1.yaml"
EXPORT_SPEC = PACKAGE / "project_owner_redcap_expected_export_candidate_0.1.csv"
IMPORT_FIXTURE = LIVE_QA / "project_owner_synthetic_import_candidate_0.1.csv"
RESPONSE_FIXTURE = FIXTURES / "project_owner_candidate_0_1_synthetic_submissions.yaml"

HEADERS = [
    "Variable / Field Name", "Form Name", "Section Header", "Field Type",
    "Field Label", "Choices, Calculations, OR Slider Labels", "Field Note",
    "Text Validation Type OR Show Slider Number", "Text Validation Min",
    "Text Validation Max", "Identifier?",
    "Branching Logic (Show field only if...)", "Required Field?",
    "Custom Alignment", "Question Number (surveys only)", "Matrix Group Name",
    "Matrix Ranking?", "Field Annotation",
]
FORMS = ("owner_contact_admin", "owner_assignment_admin", "project_owner_review")
FORM_COUNTS = {"owner_contact_admin": 27, "owner_assignment_admin": 39, "project_owner_review": 86}
CONTACT = "[record_type] = '1'"
ASSIGNMENT = "[record_type] = '2'"
REVIEW = f"({ASSIGNMENT}) and [po_ack] = '1'"
HIDDEN = "@HIDDEN-SURVEY"
HIDDEN_READONLY = "@HIDDEN-SURVEY @READONLY"
WITHDRAWAL_WORDING = (
    "You may request withdrawal of your submitted responses until {{WITHDRAWAL_DATE}} "
    "by contacting {{STUDY_EMAIL}} and quoting the survey reference. After that date, "
    "de-identified responses may already have been incorporated into the analysis and "
    "may no longer be removable."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def taxonomy() -> tuple[list[dict], list[dict], list[dict]]:
    payload = yaml.safe_load((ROOT / "taxonomy_data_dictionary.yaml").read_text(encoding="utf-8"))
    categories = [item for item in payload["categories"] if item.get("include_in_prompt")]
    groups = (
        [item for item in categories if item["layer"] == "Layer A -- domain"],
        [item for item in categories if item["layer"] == "Layer C -- purpose"],
        [item for item in categories if item["layer"] == "Cross-cutting tag"],
    )
    assert tuple(map(len, groups)) == (12, 8, 2)
    return groups


def choices(labels: list[str]) -> str:
    return " | ".join(f"{index}, {label}" for index, label in enumerate(labels, 1))


def field(
    name: str,
    form: str,
    field_type: str,
    label: str,
    *,
    section: str = "",
    choice_text: str = "",
    note: str = "",
    validation: str = "",
    branch: str = "",
    required: bool = False,
    identifier: bool = False,
    annotation: str = "",
) -> dict[str, str]:
    row = {header: "" for header in HEADERS}
    row.update({
        "Variable / Field Name": name,
        "Form Name": form,
        "Section Header": section,
        "Field Type": field_type,
        "Field Label": label,
        "Choices, Calculations, OR Slider Labels": choice_text,
        "Field Note": note,
        "Text Validation Type OR Show Slider Number": validation,
        "Identifier?": "y" if identifier else "",
        "Branching Logic (Show field only if...)": branch,
        "Required Field?": "y" if required else "",
        "Field Annotation": annotation,
    })
    return row


def write_csv(path: Path, headers: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_dictionary() -> tuple[list[dict[str, str]], dict[str, object]]:
    domains, purposes, tags = taxonomy()
    domain_labels = [item["label"] for item in domains]
    purpose_labels = [item["label"] for item in purposes]
    tag_labels = [item["label"] for item in tags]
    rows: list[dict[str, str]] = []

    # Common routing fields are held on the first administrative instrument.
    rows += [
        field("owner_record_id", "owner_contact_admin", "text", "Neutral REDCap record key", section="Record routing", required=True, annotation=HIDDEN_READONLY),
        field("record_type", "owner_contact_admin", "radio", "Record type", choice_text="1, Contact | 2, Assignment", required=True, annotation=HIDDEN_READONLY),
        field("owner_id", "owner_contact_admin", "text", "Pseudonymous owner identifier", required=True, annotation=HIDDEN_READONLY),
        field("oc_name", "owner_contact_admin", "text", "Researcher name", section="Restricted researcher contact", branch=CONTACT, required=True, identifier=True, annotation=HIDDEN),
        field("oc_email", "owner_contact_admin", "text", "Researcher email address", validation="email", branch=CONTACT, identifier=True, annotation=HIDDEN),
        field("oc_affiliation", "owner_contact_admin", "text", "Organisation or affiliation", branch=CONTACT, identifier=True, annotation=HIDDEN),
        field("oc_contact_source", "owner_contact_admin", "dropdown", "Source of contact details", choice_text="1, Public register entry | 2, Institutional profile | 3, Public directory | 4, Existing approved contact record | 5, Other public source", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_contactability", "owner_contact_admin", "radio", "Contactability status", choice_text="0, Unresolved | 1, Contactable | 2, Uncontactable | 3, Identity ambiguous | 4, Contact must not proceed", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_contact_issue_note", "owner_contact_admin", "notes", "Reason contact cannot proceed or identity is ambiguous", note="Operational detail only; do not record substantive project information.", branch=f"({CONTACT}) and ([oc_contactability] = '2' or [oc_contactability] = '3' or [oc_contactability] = '4')", required=True, identifier=True, annotation=HIDDEN),
        field("oc_eligible_projects", "owner_contact_admin", "text", "Number of eligible projects", validation="integer", branch=CONTACT, required=True, annotation=HIDDEN_READONLY),
        field("oc_projects_offered", "owner_contact_admin", "text", "Number of projects offered for review", validation="integer", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_minutes_per_project", "owner_contact_admin", "text", "Estimated minutes per project", validation="integer", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_est_total_minutes", "owner_contact_admin", "text", "Estimated total burden in minutes", validation="integer", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_eoi_invite_date", "owner_contact_admin", "text", "Expression-of-interest invitation date", validation="date_ymd", branch=CONTACT, annotation=HIDDEN),
        field("oc_eoi_status", "owner_contact_admin", "radio", "Expression-of-interest status", choice_text="0, Not approached | 1, Awaiting response | 2, Interested | 3, Not interested | 4, No response | 5, Withdrawn", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_eoi_response_date", "owner_contact_admin", "text", "Expression-of-interest response date", validation="date_ymd", branch=f"({CONTACT}) and ([oc_eoi_status] = '2' or [oc_eoi_status] = '3' or [oc_eoi_status] = '5')", required=True, annotation=HIDDEN),
        field("oc_projects_accepted", "owner_contact_admin", "text", "Number of projects accepted, where stated", validation="integer", branch=f"({CONTACT}) and [oc_eoi_status] = '2'", annotation=HIDDEN),
        field("oc_followup_date", "owner_contact_admin", "text", "Expression-of-interest follow-up or reminder date", validation="date_ymd", branch=CONTACT, annotation=HIDDEN),
        field("oc_contact_suppression", "owner_contact_admin", "radio", "Opt-out, do-not-contact or researcher-level withdrawal status", choice_text="0, None | 1, Declined and no further approach | 2, Do not contact | 3, Researcher-level withdrawal", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_recruit_route", "owner_contact_admin", "radio", "Recruitment route", choice_text="1, Deterministic sequence | 2, Supplementary", section="Recruitment provenance", branch=CONTACT, required=True, annotation=HIDDEN_READONLY),
        field("oc_sequence_pos", "owner_contact_admin", "text", "Deterministic sequence position", validation="integer", branch=f"({CONTACT}) and [oc_recruit_route] = '1'", required=True, annotation=HIDDEN_READONLY),
        field("oc_supp_reason", "owner_contact_admin", "notes", "Reason for supplementary invitation", note="Record before contact; do not use model, coder, disagreement, reserve or adjudication information.", branch=f"({CONTACT}) and [oc_recruit_route] = '2'", required=True, annotation=HIDDEN_READONLY),
        field("oc_ack_permission", "owner_contact_admin", "radio", "Permission to acknowledge researcher by name", section="Optional named acknowledgement", choice_text="0, Not asked | 1, Permission granted | 2, Permission declined | 3, Permission withdrawn", branch=CONTACT, required=True, annotation=HIDDEN),
        field("oc_ack_name", "owner_contact_admin", "text", "Preferred acknowledgement name", branch=f"({CONTACT}) and [oc_ack_permission] = '1'", required=True, identifier=True, annotation=HIDDEN),
        field("oc_ack_affiliation", "owner_contact_admin", "text", "Preferred acknowledgement affiliation", branch=f"({CONTACT}) and [oc_ack_permission] = '1'", required=True, identifier=True, annotation=HIDDEN),
        field("oc_ack_permission_date", "owner_contact_admin", "text", "Date explicit acknowledgement permission was recorded", validation="date_ymd", branch=f"({CONTACT}) and ([oc_ack_permission] = '1' or [oc_ack_permission] = '2' or [oc_ack_permission] = '3')", required=True, annotation=HIDDEN),
        field("oc_ack_permission_source", "owner_contact_admin", "text", "Source of explicit acknowledgement permission", note="For example: affirmative email after participation agreement. Do not paste message content.", branch=f"({CONTACT}) and ([oc_ack_permission] = '1' or [oc_ack_permission] = '2' or [oc_ack_permission] = '3')", required=True, identifier=True, annotation=HIDDEN),
    ]

    assignment = [
        field("owner_assignment_id", "owner_assignment_admin", "text", "Neutral owner-project assignment identifier", section="Owner-project assignment", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("source_record_id", "owner_assignment_admin", "text", "Stable DEA Record ID", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("official_project_id", "owner_assignment_admin", "text", "Official Project ID", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("project_title", "owner_assignment_admin", "notes", "Frozen public-register project title", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("datasets_used", "owner_assignment_admin", "notes", "Frozen public-register datasets-used entry", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("public_register_url", "owner_assignment_admin", "text", "Public register URL", validation="url", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("production_ver", "owner_assignment_admin", "text", "Production-model output and proposed-label version", section="Proposal provenance", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("taxonomy_ver", "owner_assignment_admin", "text", "Taxonomy and definition version", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("proposal_output_sha256", "owner_assignment_admin", "text", "Proposal-output SHA-256", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("owner_recruit_route", "owner_assignment_admin", "radio", "Recruitment route", choice_text="1, Deterministic sequence | 2, Supplementary", section="Invitation administration", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
        field("owner_sequence_pos", "owner_assignment_admin", "text", "Deterministic sequence position", validation="integer", branch=f"({ASSIGNMENT}) and [owner_recruit_route] = '1'", required=True, annotation=HIDDEN_READONLY),
        field("owner_invite_batch", "owner_assignment_admin", "radio", "Invitation batch", choice_text="1, Initial 10 | 2, Day 14 | 3, Day 21 | 4, Day 28 | 5, Supplementary", branch=ASSIGNMENT, required=True, annotation=HIDDEN),
        field("owner_link_release", "owner_assignment_admin", "radio", "Assignment-link release gate", choice_text="0, Blocked pending affirmative interest | 1, Approved not sent | 2, Released", note="A value above 0 requires affirmative expression of interest on the linked contact record.", branch=ASSIGNMENT, required=True, annotation=HIDDEN),
        field("owner_invite_date", "owner_assignment_admin", "text", "Project-link invitation date", validation="date_ymd", branch=f"({ASSIGNMENT}) and [owner_link_release] = '2'", required=True, annotation=HIDDEN),
        field("owner_reminder_date", "owner_assignment_admin", "text", "Project-link reminder date", validation="date_ymd", branch=ASSIGNMENT, annotation=HIDDEN),
        field("owner_withdrawal_status", "owner_assignment_admin", "radio", "Assignment response withdrawal or exclusion status", choice_text="0, None | 1, Withdrawal requested | 2, Withdrawn or excluded before analysis", branch=ASSIGNMENT, required=True, annotation=HIDDEN),
        field("instrument_ver", "owner_assignment_admin", "text", "Standalone owner instrument version", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY),
    ]
    for index, item in enumerate(domains, 1):
        assignment.append(field(f"prop_d{index:02d}", "owner_assignment_admin", "yesno", f"Proposed domain flag: {item['label']}", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY))
    for index, item in enumerate(purposes, 1):
        assignment.append(field(f"prop_p{index:02d}", "owner_assignment_admin", "yesno", f"Proposed purpose flag: {item['label']}", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY))
    for index, item in enumerate(tags, 1):
        assignment.append(field(f"prop_t{index:02d}", "owner_assignment_admin", "radio", f"Proposed status: {item['label']}", choice_text="0, Not applied | 1, Applied", branch=ASSIGNMENT, required=True, annotation=HIDDEN_READONLY))
    rows += assignment

    intro = (
        "This review supports validation of a portfolio view derived from the public DEA register dashboard "
        "({{DASHBOARD_URL}}). The classifications were produced using a large language model. Your project "
        "knowledge provides project-informed validation evidence that blind public-register coding cannot supply; "
        "it is not treated as a definitive gold standard. This review is expected to take about "
        "{{ESTIMATED_MINUTES_PER_PROJECT}} minutes. Participation is voluntary."
    )
    privacy = (
        "Please do not provide confidential, sensitive, restricted or personally identifying information. "
        "Responses will be used for methodological validation, adjudication triggers and possible taxonomy "
        f"improvement. {WITHDRAWAL_WORDING}"
    )
    review = [
        field("po_intro", "project_owner_review", "descriptive", intro, section="Project Owner Review", branch=ASSIGNMENT),
        field("po_privacy", "project_owner_review", "descriptive", privacy, branch=ASSIGNMENT),
        field("po_ack", "project_owner_review", "radio", "Do you agree to participate in this project review?", choice_text="1, Yes, continue to the review | 0, No, I do not wish to participate", note="Selecting No ends the review without displaying classification questions.", branch=ASSIGNMENT, required=True),
        field("po_assignment", "project_owner_review", "descriptive", "Survey reference: <strong>[owner_assignment_id]</strong>", branch=REVIEW),
        field("po_project_title", "project_owner_review", "descriptive", "<strong>Project title</strong><br>[project_title]<br><a href=\"[public_register_url]\" target=\"_blank\">Open the public register entry</a>", branch=REVIEW),
        field("po_datasets", "project_owner_review", "descriptive", "<strong>Datasets used</strong><br>[datasets_used]", branch=REVIEW),
    ]

    note_triggers: list[str] = []
    mapping: list[dict[str, str]] = []
    for prefix, layer, items in (("d", "domain", domains), ("p", "purpose", purposes)):
        for index, item in enumerate(items, 1):
            stem = f"{prefix}{index:02d}"
            flag = f"prop_{stem}"
            visible = f"({REVIEW}) and [{flag}] = '1'"
            fit = f"po_{stem}_fit"
            vis = f"po_{stem}_vis"
            review += [
                field(f"po_{stem}_label", "project_owner_review", "descriptive", f"<strong>{html.escape(item['label'])}</strong><br>{html.escape(str(item['definition']))}", section=f"Proposed {layer} labels" if index == 1 else "", branch=visible),
                field(fit, "project_owner_review", "radio", f"Does {item['label']} describe the actual project?", choice_text="1, Fits | 2, Does not fit | 3, Unsure", branch=visible, required=True),
                field(vis, "project_owner_review", "radio", f"Is the basis for {item['label']} visible in the public register entry?", choice_text="1, Clearly visible | 2, Partly visible | 3, Not visible | 4, Unsure", branch=visible, required=True),
            ]
            note_triggers += [f"[{fit}] = '2'", f"[{fit}] = '3'", f"[{vis}] = '2'", f"[{vis}] = '3'", f"[{vis}] = '4'"]
            mapping.append({"variable": stem, "layer": layer, "flag": flag, "verdict": fit, "visibility": vis, "label": item["label"]})

    for index, item in enumerate(tags, 1):
        stem = f"t{index:02d}"
        correct = f"po_{stem}_correct"
        determinable = f"po_{stem}_det"
        review += [
            field(f"po_{stem}_label", "project_owner_review", "descriptive", f"<strong>{html.escape(item['label'])}</strong><br>{html.escape(str(item['definition']))}<br><strong>Proposed status:</strong> [prop_{stem}:label]", section="Binary tag status review" if index == 1 else "", branch=REVIEW),
            field(correct, "project_owner_review", "radio", "Is the proposed status correct for the actual project?", choice_text="1, Yes | 0, No | 2, Unsure", branch=REVIEW, required=True),
            field(determinable, "project_owner_review", "radio", "Could the correct status reasonably be determined from the public register entry?", choice_text="1, Yes | 2, Partly | 0, No | 3, Unsure", branch=REVIEW, required=True),
        ]
        note_triggers += [f"[{correct}] = '0'", f"[{correct}] = '2'", f"[{determinable}] = '2'", f"[{determinable}] = '0'", f"[{determinable}] = '3'"]
        mapping.append({"variable": stem, "layer": "tag", "flag": f"prop_{stem}", "verdict": correct, "visibility": determinable, "label": item["label"]})

    review += [
        field("po_miss_domain", "project_owner_review", "radio", "Is any Research Domain missing?", section="Missing classifications and overall assessment", choice_text="0, No | 1, Yes", branch=REVIEW, required=True),
        field("po_miss_domains", "project_owner_review", "checkbox", "Which Research Domain label(s) are missing?", choice_text=choices(domain_labels[:-1]), branch=f"({REVIEW}) and [po_miss_domain] = '1'", required=True),
        field("po_miss_purpose", "project_owner_review", "radio", "Is any Analytical Purpose missing?", choice_text="0, No | 1, Yes", branch=REVIEW, required=True),
        field("po_miss_purposes", "project_owner_review", "checkbox", "Which Analytical Purpose label(s) are missing?", choice_text=choices(purpose_labels[:-1]), branch=f"({REVIEW}) and [po_miss_purpose] = '1'", required=True),
        field("po_miss_tag", "project_owner_review", "radio", "Is a binary tag missing or incorrectly absent?", choice_text="0, No | 1, Yes", branch=REVIEW, required=True),
        field("po_miss_tags", "project_owner_review", "checkbox", "Which binary tag status should be Applied?", choice_text=choices(tag_labels), branch=f"({REVIEW}) and [po_miss_tag] = '1'", required=True),
        field("po_sufficiency", "project_owner_review", "radio", "Is the public register entry sufficient to assess the proposed classifications?", choice_text="1, Sufficient | 2, Partial | 3, Insufficient", branch=REVIEW, required=True),
        field("po_taxonomy_fit", "project_owner_review", "radio", "How well can the taxonomy represent the actual project?", choice_text="1, Fit | 2, Partial Fit | 3, No Fit", note="Assess the taxonomy, not merely the amount of public-register information.", branch=REVIEW, required=True),
        field("po_tax_issue", "project_owner_review", "checkbox", "Taxonomy problem type", choice_text="1, Missing or inadequately represented category | 2, Ambiguous or overlapping category boundaries | 5, Other taxonomy problem", branch=f"({REVIEW}) and ([po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3')", required=True),
    ]
    overall_triggers = note_triggers + [
        "[po_miss_domain] = '1'", "[po_miss_purpose] = '1'", "[po_miss_tag] = '1'",
        "[po_sufficiency] = '2'", "[po_sufficiency] = '3'",
        "[po_taxonomy_fit] = '2'", "[po_taxonomy_fit] = '3'",
    ]
    review += [
        field("po_note", "project_owner_review", "notes", "Please explain each disagreement, uncertainty, missing classification, limited public-entry judgement or taxonomy problem, naming the affected label(s).", note="Do not disclose confidential or sensitive content. Identify the issue or source, not restricted substantive information.", branch=f"({REVIEW}) and ({' or '.join(overall_triggers)})", required=True),
        field("po_nonpublic", "project_owner_review", "radio", "Did any answer draw on project knowledge not available in the public register entry?", choice_text="0, No | 1, Yes", branch=REVIEW, required=True),
        field("po_nonpublic_note", "project_owner_review", "notes", "Briefly identify the source or type of that additional project knowledge.", note="Do not disclose the substantive non-public information.", branch=f"({REVIEW}) and [po_nonpublic] = '1'", required=True),
        field("po_quote_permission", "project_owner_review", "radio", "May the study use a short anonymised quotation from your comments in research outputs, provided that it does not identify you, your project or disclose non-public information?", choice_text="1, Yes | 0, No | 2, Please contact me before using a quotation", note="Optional. This choice does not affect participation or analytical completeness.", branch=REVIEW),
        field("po_other_comment", "project_owner_review", "notes", "Optional additional comment", note="Do not include confidential, restricted or personally identifying information.", branch=REVIEW),
    ]
    rows += review

    actual = {form: sum(row["Form Name"] == form for row in rows) for form in FORMS}
    assert actual == FORM_COUNTS, actual
    assert len(rows) == 152
    assert len({row["Variable / Field Name"] for row in rows}) == 152
    return rows, {"domains": domains, "purposes": purposes, "tags": tags, "mapping": mapping}


def build_specs(rows: list[dict[str, str]], meta: dict[str, object]) -> None:
    old_names: set[str] = set()
    with SCRATCH_DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
        old_names = {row["Variable / Field Name"] for row in csv.DictReader(handle)}
    renamed = {
        "owner_record_id": "assignment_id", "record_type": "record_kind",
        "owner_id": "owner_resp_id", "owner_assignment_id": "owner_project_id",
        "po_t01_correct": "po_t01_fit", "po_t01_det": "po_t01_vis",
        "po_t02_correct": "po_t02_fit", "po_t02_det": "po_t02_vis",
    }
    spec_rows: list[dict[str, object]] = []
    for row in rows:
        name = row["Variable / Field Name"]
        form = row["Form Name"]
        if name in renamed:
            source = f"renamed:{renamed[name]}"
        elif name in old_names:
            source = "retained_name_modified_for_standalone"
        else:
            source = "new"
        respondent = "yes" if form == "project_owner_review" else "no"
        analytical = "no" if form == "owner_contact_admin" and name not in {"owner_record_id", "record_type", "owner_id"} else "no" if row["Field Type"] == "descriptive" else "yes"
        restricted = "direct_identifier" if row["Identifier?"] == "y" else "restricted_qualitative" if name in {"po_note", "po_nonpublic_note", "po_other_comment"} else "standard"
        spec_rows.append({
            "variable": name, "form": form, "field_type": row["Field Type"],
            "choices": row["Choices, Calculations, OR Slider Labels"],
            "validation": row["Text Validation Type OR Show Slider Number"],
            "branching": row["Branching Logic (Show field only if...)"],
            "required": row["Required Field?"], "identifier": row["Identifier?"],
            "respondent_visible": respondent, "ordinary_analytical_export": analytical,
            "restriction": restricted, "candidate_source": source,
        })
    write_csv(
        FIELD_SPEC,
        ["variable", "form", "field_type", "choices", "validation", "branching", "required", "identifier", "respondent_visible", "ordinary_analytical_export", "restriction", "candidate_source"],
        spec_rows,
    )

    export_rows = [
        {
            "variable": row["Variable / Field Name"],
            "source_form": row["Form Name"],
            "include_in_ordinary_analytical_export": "no" if row["Form Name"] == "owner_contact_admin" and row["Variable / Field Name"] not in {"owner_record_id", "record_type", "owner_id"} else "no" if row["Field Type"] == "descriptive" else "yes",
            "restricted_or_public": "restricted" if row["Identifier?"] == "y" or row["Variable / Field Name"] in {"po_note", "po_nonpublic_note", "po_other_comment"} else "internal_analysis",
            "notes": "Contact crosswalk only" if row["Form Name"] == "owner_contact_admin" else "Stable assignment/response column",
        }
        for row in rows
    ]
    export_rows += [
        {"variable": f"{form}_complete", "source_form": form, "include_in_ordinary_analytical_export": "yes" if form != "owner_contact_admin" else "no", "restricted_or_public": "internal_analysis", "notes": "REDCap-generated form status"}
        for form in FORMS
    ]
    export_rows += [
        {"variable": "project_owner_review_timestamp", "source_form": "project_owner_review", "include_in_ordinary_analytical_export": "yes", "restricted_or_public": "internal_analysis", "notes": "REDCap survey/audit completion timestamp; not manually entered"},
        {"variable": "owner_analytical_complete", "source_form": "derived", "include_in_ordinary_analytical_export": "yes", "restricted_or_public": "internal_analysis", "notes": "Deterministic derivation: affirmative participation; every populated domain/purpose verdict; both tag correctness responses; public-entry sufficiency"},
    ]
    write_csv(EXPORT_SPEC, ["variable", "source_form", "include_in_ordinary_analytical_export", "restricted_or_public", "notes"], export_rows)

    branch_spec = {
        "version": VERSION,
        "status": "development_candidate_unfrozen_live_qa_pending",
        "classic_non_longitudinal": True,
        "forms": list(FORMS),
        "field_counts": FORM_COUNTS,
        "record_type": {1: "Contact", 2: "Assignment"},
        "guards": {"contact": CONTACT, "assignment": ASSIGNMENT, "review": REVIEW},
        "only_survey_instrument": "project_owner_review",
        "contact_instrument_is_survey": False,
        "record_specific_links_only": True,
        "link_release_requires_affirmative_interest": True,
        "direct_identifier_fields": [row["Variable / Field Name"] for row in rows if row["Identifier?"] == "y"],
        "label_mapping": meta["mapping"],
        "domain_slots": 12,
        "purpose_slots": 8,
        "purpose_maximum": 2,
        "binary_tags_always_reviewed": True,
        "tag_correctness_codes": {1: "Yes", 0: "No", 2: "Unsure"},
        "tag_determinability_codes": {1: "Yes", 2: "Partly", 0: "No", 3: "Unsure"},
        "owner_taxonomy_fit_codes": {1: "Fit", 2: "Partial Fit", 3: "No Fit"},
        "quotation_permission_optional": True,
        "named_acknowledgement_contact_level_only": True,
        "withdrawal_wording": WITHDRAWAL_WORDING,
        "configuration_placeholders": ["{{DASHBOARD_URL}}", "{{ESTIMATED_MINUTES_PER_PROJECT}}", "{{WITHDRAWAL_DATE}}", "{{STUDY_EMAIL}}"],
        "analytical_completion": {
            "participation": "po_ack == 1",
            "domains": "every prop_dNN == 1 has po_dNN_fit in 1,2,3",
            "purposes": "every prop_pNN == 1 has po_pNN_fit in 1,2,3",
            "tags": "po_t01_correct and po_t02_correct in 1,0,2",
            "sufficiency": "po_sufficiency in 1,2,3",
            "not_required": ["po_quote_permission", "po_other_comment"],
        },
        "prohibited_architecture": ["repeating instruments", "longitudinal events", "respondent accounts", "respondent DAGs", "shared public survey link"],
        "live_project": {"pid": 9149, "title": "DEA Validation Study – Project Owner Review", "status": "Development", "connection_performed": False},
    }
    BRANCH_SPEC.write_text(yaml.safe_dump(branch_spec, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _blank(names: list[str]) -> dict[str, object]:
    return {name: "" for name in names}


def build_fixtures(rows: list[dict[str, str]]) -> None:
    names = [row["Variable / Field Name"] for row in rows]
    contacts = [
        dict(owner_record_id="A1B2C3D4", record_type=1, owner_id="SYN-OWNER-01", oc_name="Avery Example", oc_email="avery.example@example.invalid", oc_affiliation="Example Research Institute", oc_contact_source=2, oc_contactability=1, oc_eligible_projects=3, oc_projects_offered=3, oc_minutes_per_project=10, oc_est_total_minutes=30, oc_eoi_invite_date="2026-07-01", oc_eoi_status=2, oc_eoi_response_date="2026-07-02", oc_projects_accepted=2, oc_contact_suppression=0, oc_recruit_route=1, oc_sequence_pos=1, oc_ack_permission=1, oc_ack_name="Avery Example", oc_ack_affiliation="Example Research Institute", oc_ack_permission_date="2026-07-03", oc_ack_permission_source="Synthetic affirmative email record"),
        dict(owner_record_id="B2C3D4E5", record_type=1, owner_id="SYN-OWNER-02", oc_name="Blair Example", oc_email="blair.example@example.invalid", oc_affiliation="Fictional Policy Centre", oc_contact_source=3, oc_contactability=1, oc_eligible_projects=1, oc_projects_offered=1, oc_minutes_per_project=10, oc_est_total_minutes=10, oc_eoi_invite_date="2026-07-01", oc_eoi_status=2, oc_eoi_response_date="2026-07-04", oc_projects_accepted=1, oc_contact_suppression=0, oc_recruit_route=2, oc_supp_reason="Synthetic supplementary coverage rationale fixed before contact.", oc_ack_permission=2, oc_ack_permission_date="2026-07-04", oc_ack_permission_source="Synthetic email record"),
        dict(owner_record_id="C3D4E5F6", record_type=1, owner_id="SYN-OWNER-03", oc_name="Casey Example", oc_email="casey.example@example.invalid", oc_affiliation="Example University", oc_contact_source=2, oc_contactability=1, oc_eligible_projects=2, oc_projects_offered=2, oc_minutes_per_project=10, oc_est_total_minutes=20, oc_eoi_invite_date="2026-07-01", oc_eoi_status=3, oc_eoi_response_date="2026-07-02", oc_contact_suppression=1, oc_recruit_route=1, oc_sequence_pos=2, oc_ack_permission=0),
        dict(owner_record_id="D4E5F6G7", record_type=1, owner_id="SYN-OWNER-04", oc_name="Devon Example", oc_email="devon.example@example.invalid", oc_affiliation="Fictional Institute", oc_contact_source=4, oc_contactability=4, oc_contact_issue_note="Synthetic do-not-contact instruction.", oc_eligible_projects=1, oc_projects_offered=0, oc_minutes_per_project=10, oc_est_total_minutes=0, oc_eoi_status=0, oc_contact_suppression=2, oc_recruit_route=1, oc_sequence_pos=3, oc_ack_permission=0),
        dict(owner_record_id="E5F6G7H8", record_type=1, owner_id="SYN-OWNER-05", oc_name="Emery Example", oc_affiliation="Unknown fictional affiliation", oc_contact_source=5, oc_contactability=3, oc_contact_issue_note="Synthetic ambiguous identity; no contact attempted.", oc_eligible_projects=1, oc_projects_offered=0, oc_minutes_per_project=10, oc_est_total_minutes=0, oc_eoi_status=0, oc_contact_suppression=0, oc_recruit_route=2, oc_supp_reason="Synthetic unresolved supplementary candidate retained for QA only.", oc_ack_permission=0),
        dict(owner_record_id="F6G7H8J9", record_type=1, owner_id="SYN-OWNER-06", oc_name="Finley Example", oc_email="finley.example@example.invalid", oc_affiliation="Example Data Lab", oc_contact_source=1, oc_contactability=1, oc_eligible_projects=1, oc_projects_offered=1, oc_minutes_per_project=10, oc_est_total_minutes=10, oc_eoi_invite_date="2026-07-01", oc_eoi_status=2, oc_eoi_response_date="2026-07-02", oc_projects_accepted=1, oc_followup_date="2026-07-11", oc_contact_suppression=3, oc_recruit_route=1, oc_sequence_pos=4, oc_ack_permission=3, oc_ack_permission_date="2026-07-12", oc_ack_permission_source="Synthetic withdrawal email record"),
    ]

    def proposal(domain_codes: list[int], purpose_codes: list[int], tag_values: tuple[int, int]) -> dict[str, int]:
        payload = {f"prop_d{i:02d}": int(i in domain_codes) for i in range(1, 13)}
        payload.update({f"prop_p{i:02d}": int(i in purpose_codes) for i in range(1, 9)})
        payload.update({"prop_t01": tag_values[0], "prop_t02": tag_values[1]})
        return payload

    assignments = [
        dict(owner_record_id="G7H8J9K2", record_type=2, owner_id="SYN-OWNER-01", owner_assignment_id="SYN-ASG-001", source_record_id="SYNTHETIC-RECORD-001", official_project_id="SYNTHETIC-PROJECT-001", project_title="Synthetic employment pathways study", datasets_used="Synthetic workforce dataset", public_register_url="https://example.invalid/register/001", production_ver="synthetic-production-1", taxonomy_ver="dict-1.0-rc2", proposal_output_sha256="a"*64, owner_recruit_route=1, owner_sequence_pos=1, owner_invite_batch=1, owner_link_release=2, owner_invite_date="2026-07-05", owner_withdrawal_status=0, instrument_ver=VERSION, **proposal([1], [1], (1, 0))),
        dict(owner_record_id="H8J9K2L3", record_type=2, owner_id="SYN-OWNER-01", owner_assignment_id="SYN-ASG-002", source_record_id="SYNTHETIC-RECORD-002", official_project_id="SYNTHETIC-PROJECT-002", project_title="Synthetic education and health linkage study", datasets_used="Synthetic education dataset; Synthetic health dataset", public_register_url="https://example.invalid/register/002", production_ver="synthetic-production-1", taxonomy_ver="dict-1.0-rc2", proposal_output_sha256="b"*64, owner_recruit_route=1, owner_sequence_pos=1, owner_invite_batch=1, owner_link_release=2, owner_invite_date="2026-07-05", owner_reminder_date="2026-07-15", owner_withdrawal_status=0, instrument_ver=VERSION, **proposal([2, 3], [1, 2], (0, 1))),
        dict(owner_record_id="J9K2L3M4", record_type=2, owner_id="SYN-OWNER-02", owner_assignment_id="SYN-ASG-003", source_record_id="SYNTHETIC-RECORD-003", official_project_id="SYNTHETIC-PROJECT-003", project_title="Synthetic justice systems study", datasets_used="Synthetic courts dataset", public_register_url="https://example.invalid/register/003", production_ver="synthetic-production-1", taxonomy_ver="dict-1.0-rc2", proposal_output_sha256="c"*64, owner_recruit_route=2, owner_invite_batch=5, owner_link_release=2, owner_invite_date="2026-07-06", owner_withdrawal_status=0, instrument_ver=VERSION, **proposal([4], [4], (1, 1))),
        dict(owner_record_id="K2L3M4N5", record_type=2, owner_id="SYN-OWNER-06", owner_assignment_id="SYN-ASG-004", source_record_id="SYNTHETIC-RECORD-004", official_project_id="SYNTHETIC-PROJECT-004", project_title="Synthetic environmental methods study", datasets_used="Synthetic environmental dataset", public_register_url="https://example.invalid/register/004", production_ver="synthetic-production-1", taxonomy_ver="dict-1.0-rc2", proposal_output_sha256="d"*64, owner_recruit_route=1, owner_sequence_pos=4, owner_invite_batch=1, owner_link_release=2, owner_invite_date="2026-07-05", owner_withdrawal_status=2, instrument_ver=VERSION, **proposal([9], [7], (0, 0))),
    ]

    import_rows: list[dict[str, object]] = []
    for payload in contacts + assignments:
        row = _blank(names)
        row.update(payload)
        import_rows.append(row)
    write_csv(IMPORT_FIXTURE, names, import_rows)

    responses = [
        {"case_id": "complete_fit_quote_yes", "owner_record_id": "G7H8J9K2", "expected_valid": True, "expected_analytical_complete": True, "data": {"po_ack": 1, "po_d01_fit": 1, "po_d01_vis": 1, "po_p01_fit": 1, "po_p01_vis": 1, "po_t01_correct": 1, "po_t01_det": 1, "po_t02_correct": 1, "po_t02_det": 1, "po_miss_domain": 0, "po_miss_purpose": 0, "po_miss_tag": 0, "po_sufficiency": 1, "po_taxonomy_fit": 1, "po_nonpublic": 0, "po_quote_permission": 1}},
        {"case_id": "complete_disagreement_nonpublic_quote_no", "owner_record_id": "H8J9K2L3", "expected_valid": True, "expected_analytical_complete": True, "data": {"po_ack": 1, "po_d02_fit": 2, "po_d02_vis": 2, "po_d03_fit": 3, "po_d03_vis": 3, "po_p01_fit": 1, "po_p01_vis": 1, "po_p02_fit": 2, "po_p02_vis": 4, "po_t01_correct": 0, "po_t01_det": 2, "po_t02_correct": 2, "po_t02_det": 0, "po_miss_domain": 1, "po_miss_domains": [4], "po_miss_purpose": 0, "po_miss_tag": 1, "po_miss_tags": [1], "po_sufficiency": 2, "po_taxonomy_fit": 2, "po_tax_issue": [1], "po_note": "Synthetic explanation identifying affected labels without non-public content.", "po_nonpublic": 1, "po_nonpublic_note": "Synthetic prior project involvement.", "po_quote_permission": 0}},
        {"case_id": "complete_insufficient_taxonomy_no_fit_contact_quote", "owner_record_id": "J9K2L3M4", "expected_valid": True, "expected_analytical_complete": True, "data": {"po_ack": 1, "po_d04_fit": 1, "po_d04_vis": 4, "po_p04_fit": 3, "po_p04_vis": 3, "po_t01_correct": 1, "po_t01_det": 3, "po_t02_correct": 0, "po_t02_det": 1, "po_miss_domain": 0, "po_miss_purpose": 1, "po_miss_purposes": [5], "po_miss_tag": 0, "po_sufficiency": 3, "po_taxonomy_fit": 3, "po_tax_issue": [2, 5], "po_note": "Synthetic explanation of register and taxonomy limitations.", "po_nonpublic": 0, "po_quote_permission": 2}},
        {"case_id": "incomplete_partial_response", "owner_record_id": "K2L3M4N5", "expected_valid": True, "expected_analytical_complete": False, "data": {"po_ack": 1, "po_d09_fit": 1}},
        {"case_id": "declined_before_questions", "owner_record_id": "K2L3M4N5", "expected_valid": True, "expected_analytical_complete": False, "data": {"po_ack": 0}},
    ]
    fixture = {
        "fixture_status": "synthetic_only",
        "candidate_version": VERSION,
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
    if sha256(SCRATCH_DICTIONARY) != SCRATCH_SHA256:
        raise RuntimeError("Frozen scratch candidate-0.7 dictionary hash changed")
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
