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
import html
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
IMPORT_READY_DICTIONARY = (
    PACKAGE
    / "project_owner_redcap_data_dictionary_candidate_0.4_defect_repaired_import_2026-08-18.csv"
)
SPEC = PACKAGE / "project_owner_redcap_candidate_0.4_spec.md"
LIVE_CONFIG = PACKAGE / "project_owner_redcap_candidate_0.4_live_configuration.md"
IMPORT_FIXTURE = LIVE_QA / "project_owner_synthetic_import_candidate_0.4.csv"
FIELD_SPEC = PACKAGE / "project_owner_redcap_field_specification_candidate_0.4.csv"
BRANCH_SPEC = PACKAGE / "project_owner_redcap_branching_specification_candidate_0.4.yaml"
EXPORT_SPEC = PACKAGE / "project_owner_redcap_expected_export_candidate_0.4.csv"
FORMATTING_AUDIT = PACKAGE / "project_owner_redcap_formatting_audit_candidate_0.4.csv"
MISSING_DOMAIN_REVIEW = (
    PACKAGE / "project_owner_missing_domain_microdefinitions_candidate_0.4_review.md"
)
DOMAIN_CONCORDANCE = (
    PACKAGE / "project_owner_domain_wording_concordance_candidate_0.4.md"
)
TAG_AND_QUOTATION_AUDIT = (
    PACKAGE / "project_owner_cross_cutting_tag_and_quotation_audit_candidate_0.4.md"
)
PARTICIPANT_SOURCE = (
    PACKAGE
    / "participant_materials/Project_Owner_Participant_Information_and_Consent_v3.docx"
)
QUESTIONNAIRE_SOURCE = (
    PACKAGE
    / "participant_materials/Project_Owner_Review_Questionnaire_v3.docx"
)
RC3_TAXONOMY_SOURCE = ROOT / "taxonomy_data_dictionary_1.0-rc3.yaml"

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
OPERATIONAL_TAGS = (
    "Demographic disparities / equity tag",
    "COVID-19 & Pandemic",
)
OPERATIONAL_INCLUSION_RULE = (
    "include_in_prompt is true; layer is Cross-cutting tag; source status does not begin "
    "'removed'"
)
TAG_DEFINITIONS = {
    "Demographic disparities / equity tag": (
        "A cross-cutting tag for projects whose research question centres on comparing outcomes, "
        "experiences, risks, access, or trajectories across demographic or equality-relevant "
        "groups. Routine subgroup breakdowns do not qualify, and socioeconomic or "
        "deprivation-based inequality alone is insufficient unless comparison across demographic "
        "or equality-relevant groups is central."
    ),
    "COVID-19 & Pandemic": (
        "A cross-cutting tag for projects where COVID-19, the COVID-19 pandemic, pandemic "
        "conditions, infection surveillance, vaccination, lockdowns, social distancing, "
        "pandemic-related public support, or pandemic consequences are a central condition or "
        "lens for the research question. Research does not qualify merely because its data cover "
        "the pandemic period or because COVID-19 is mentioned incidentally."
    ),
}
TAG_FIELD_MAPPING = {
    "prop_t01_status": OPERATIONAL_TAGS[0],
    "prop_t02_status": OPERATIONAL_TAGS[1],
}
QUOTATION_POLICY = (
    "Quotation permission is not collected in REDCap. If the study team wishes to use a "
    "participant’s words, the participant will be contacted by email with the exact proposed "
    "quotation and the context in which it would appear. The quotation will be used only "
    "following written agreement."
)
SUBSTANTIVE_FOCUS_PHRASE = (
    "only when it is a substantive focus of the project’s research question or analytical aims"
)
SUBSTANTIVE_FOCUS_PARAGRAPH = (
    "A Research Domain or Analytical Purpose should be treated as applying "
    f"{SUBSTANTIVE_FOCUS_PHRASE}—not merely because related terms, datasets, variables, "
    "methods or outcomes are mentioned or used."
)
MISSING_DOMAIN_REMINDER_PHRASE = "a substantive subject of the project"
MISSING_DOMAIN_REMINDER = (
    "Select a missing Research Domain only if it represents "
    f"{MISSING_DOMAIN_REMINDER_PHRASE}, not merely a dataset, variable, population "
    "characteristic or contextual factor used in the research."
)
MISSING_PURPOSE_REMINDER_PHRASE = "a substantive analytical aim of the project"
MISSING_PURPOSE_REMINDER = (
    "Select a missing Analytical Purpose only if it represents "
    f"{MISSING_PURPOSE_REMINDER_PHRASE}, not merely a method, analytical step or secondary "
    "feature of the work."
)
MISSING_DOMAIN_REMINDER_HTML = MISSING_DOMAIN_REMINDER.replace(
    MISSING_DOMAIN_REMINDER_PHRASE,
    f"<strong>{MISSING_DOMAIN_REMINDER_PHRASE}</strong>",
)
MISSING_PURPOSE_REMINDER_HTML = MISSING_PURPOSE_REMINDER.replace(
    MISSING_PURPOSE_REMINDER_PHRASE,
    f"<strong>{MISSING_PURPOSE_REMINDER_PHRASE}</strong>",
)
CLASSIFICATION_INTRO_PARAGRAPHS = (
    "How the classifications work",
    "Research Domains describe what the project is about. Several may apply, and they are not ranked.",
    "Analytical Purposes describe what the project is trying to do analytically. One or two may apply.",
    SUBSTANTIVE_FOCUS_PARAGRAPH,
    (
        "Cross-cutting tags show whether Demographic disparities / equity or COVID-19 & Pandemic "
        "is a central feature of the research question. Either, both or neither may apply."
    ),
    (
        "Each proposed classification is shown with a definition. Please judge each one "
        "independently against the actual project and then assess whether its basis is visible "
        "in the public register entry."
    ),
)
CLASSIFICATION_INTRO_LABEL = (
    "<strong>How the classifications work</strong><br><br>"
    + "<br><br>".join(CLASSIFICATION_INTRO_PARAGRAPHS[1:3])
    + "<br><br>A Research Domain or Analytical Purpose should be treated as applying "
    + f"<strong>{SUBSTANTIVE_FOCUS_PHRASE}</strong>—not merely because related terms, "
    + "datasets, variables, methods or outcomes are mentioned or used.<br><br>"
    + "<br><br>".join(CLASSIFICATION_INTRO_PARAGRAPHS[4:])
)

DOMAIN_ORDER = (
    "Labour Market & Employment",
    "Education & Skills",
    "Health & Social Care",
    "Crime & Justice",
    "Business & Productivity",
    "Poverty, Wealth & Living Standards",
    "Housing & Planning",
    "Migration & Demographics",
    "Environment & Agriculture",
    "Public Finance & Taxation",
    "Data Infrastructure & Methodology",
)
_APPROVED_MISSING_DOMAIN_MICRODEFINITIONS = {
    "Labour Market & Employment": (
        "Labour Market & Employment — Work, employment, earnings, job quality, workforce "
        "dynamics, skills demand or labour-market transitions; not employment or earnings used "
        "only to measure the consequences of education, health or another substantive exposure "
        "unless labour-market outcomes are themselves a central focus."
    ),
    "Education & Skills": (
        "Education & Skills — Educational participation, attainment, qualifications, admissions, "
        "skills acquisition, training, apprenticeships or educational progression, including "
        "where later employment or earnings outcomes are used to study the effects of education "
        "or training; not education level used only as a subgroup, covariate or worker characteristic."
    ),
    "Health & Social Care": (
        "Health & Social Care — Health, illness, mental health, wellbeing, clinical outcomes, "
        "healthcare access or use, mortality as a health outcome, and social care; not mortality "
        "studied only as a demographic or population outcome."
    ),
    "Crime & Justice": (
        "Crime & Justice — Offending, victimisation, public safety, policing, courts, sentencing, "
        "prisons, probation, family justice, civil justice or justice-system outcomes; not general "
        "harm, risk, vulnerability or public-service use without crime, legal proceedings or "
        "justice-system involvement."
    ),
    "Business & Productivity": (
        "Business & Productivity — Firms, business behaviour, innovation, productivity, "
        "entrepreneurship, trade, investment or firm performance; not firm-level data used only "
        "as a setting or source for another substantive question."
    ),
    "Poverty, Wealth & Living Standards": (
        "Poverty, Wealth & Living Standards — Household income and resources, poverty, wealth, "
        "savings, debt, benefits, food insecurity, cost of living or material deprivation; not pay "
        "gaps, employment, deprivation indices, area-level disadvantage or demographic inequality "
        "unless household resources or living standards are central."
    ),
    "Housing & Planning": (
        "Housing & Planning — Housing, homelessness, tenure, housing markets, residential "
        "conditions or mobility, neighbourhood change and planning; domestic energy or "
        "environmental exposure belongs here only where a housing, dwelling or residential "
        "mechanism is central, not merely because home, place or geography is mentioned."
    ),
    "Migration & Demographics": (
        "Migration & Demographics — Population structure or change, migration, fertility, ageing "
        "or mortality as a demographic outcome; not every study that includes demographic "
        "characteristics or subgroup comparisons."
    ),
    "Environment & Agriculture": (
        "Environment & Agriculture — The natural environment, climate, energy, agriculture, land "
        "use, pollution, decarbonisation or environmental impacts; not “environment” used only to "
        "mean a social, economic, family or institutional context."
    ),
    "Public Finance & Taxation": (
        "Public Finance & Taxation — Taxation, tax compliance, tax credits, business rates, public "
        "revenue or expenditure, fiscal transfers, tax reliefs or fiscal policy; not private "
        "income, debt, wealth, investment or household finances without a public-finance mechanism."
    ),
    "Data Infrastructure & Methodology": (
        "Data Infrastructure & Methodology — Research primarily about data, linkage, measurement, "
        "classifications, methods or statistical infrastructure; not merely a substantive project "
        "that uses linked data or advanced methods."
    ),
}
_DOMAIN_BOUNDARY_SUMMARIES = {
    "Labour Market & Employment": "Labour-market outcomes as a central object versus downstream or contextual employment/earnings measures.",
    "Education & Skills": "Education or training as the research object versus education level as a subgroup, covariate or worker characteristic.",
    "Health & Social Care": "Mortality as a health outcome versus mortality as a demographic population outcome.",
    "Crime & Justice": "Crime, legal proceedings or justice-system involvement versus general harm, risk, vulnerability or public-service use.",
    "Business & Productivity": "Firms as the substantive research object versus firms used only as a setting or data source.",
    "Poverty, Wealth & Living Standards": "Household resources and living standards versus labour, area-deprivation or demographic-inequality measures alone.",
    "Housing & Planning": "A housing, dwelling or residential mechanism versus home, place or geography as incidental context.",
    "Migration & Demographics": "Population structure or change versus demographic variables or subgroup comparisons alone.",
    "Environment & Agriculture": "Natural-environment mechanisms versus non-environmental uses of the word environment.",
    "Public Finance & Taxation": "Public revenue, expenditure or fiscal mechanisms versus private or household finances.",
    "Data Infrastructure & Methodology": "Data or methods as the primary research object versus tools used for another substantive question.",
}
_DOMAIN_APPROVAL_CHANGE_SUMMARIES = {
    "Labour Market & Employment": "Replaced the draft background-context boundary with the approved education/health consequence boundary.",
    "Education & Skills": "Added the approved education-to-employment outcome clause and retained the covariate boundary.",
    "Health & Social Care": "Changed ‘used’ to the approved ‘studied’ mortality boundary wording.",
    "Crime & Justice": "Added family justice and civil justice to the positive scope.",
    "Business & Productivity": "Compressed the draft adjacent-domain list to the approved setting-or-source boundary.",
    "Poverty, Wealth & Living Standards": "Expanded the approved positive scope and replaced the draft boundary with the approved detailed exclusions.",
    "Housing & Planning": "Replaced the draft general place boundary with the approved domestic-energy/environmental-exposure mechanism boundary.",
    "Migration & Demographics": "Used the approved phrase ‘mortality as a demographic outcome’.",
    "Environment & Agriculture": "Retained the approved boundary, with typographic quotation marks.",
    "Public Finance & Taxation": "Added tax compliance, tax credits, business rates and tax reliefs to the approved positive scope.",
    "Data Infrastructure & Methodology": "Retained the approved draft wording unchanged.",
}
DOMAIN_TAXONOMY_SOURCE_FIELDS = (
    "definition",
    "inclusion_rules",
    "exclusion_rules",
    "counterexamples",
)
RC3_LAYER_BY_OWNER_LAYER = {
    "domain": "Layer A -- domain",
    "purpose": "Layer C -- purpose",
    "tag": "Cross-cutting tag",
}


def _load_rc3_short_definitions() -> dict[tuple[str, str], str]:
    """Load the 22 in-prompt display definitions from the rc3 authority."""

    payload = yaml.safe_load(RC3_TAXONOMY_SOURCE.read_text(encoding="utf-8"))
    if payload.get("metadata", {}).get("dictionary_version") != "1.0-rc3":
        raise RuntimeError("owner display taxonomy is not dictionary version 1.0-rc3")
    rows = [
        item for item in payload.get("categories", []) if item.get("include_in_prompt") is True
    ]
    definitions: dict[tuple[str, str], str] = {}
    for item in rows:
        identity = (str(item.get("layer", "")), str(item.get("label", "")))
        definition = str(item.get("short_definition", "")).strip()
        if not all(identity) or not definition or identity in definitions:
            raise RuntimeError(f"invalid or duplicate rc3 display definition: {identity!r}")
        definitions[identity] = definition
    expected_counts = {
        "Layer A -- domain": 12,
        "Layer C -- purpose": 8,
        "Cross-cutting tag": 2,
    }
    actual_counts = {
        layer: sum(identity[0] == layer for identity in definitions)
        for layer in expected_counts
    }
    if actual_counts != expected_counts or len(definitions) != 22:
        raise RuntimeError(f"rc3 in-prompt display-definition coverage differs: {actual_counts}")
    return definitions


RC3_SHORT_DEFINITIONS = _load_rc3_short_definitions()


def rc3_short_definition(owner_layer: str, label: str) -> str:
    return RC3_SHORT_DEFINITIONS[(RC3_LAYER_BY_OWNER_LAYER[owner_layer], label)]


def _build_owner_domain_display() -> dict[str, dict[str, object]]:
    """Join approved owner wording to exact frozen-derived proposed definitions."""

    display_entries = {
        str(item["canonical_label"]): item
        for item in base.display_source()["labels"]
        if item["owner_layer"] == "domain"
    }
    taxonomy_entries = {
        str(item["label"]): item
        for item in base.taxonomy_payload()["categories"]
        if item.get("layer") == base.LAYER_NAMES["domain"]
        and item.get("include_in_prompt") is True
        and not str(item.get("status", "")).lower().startswith("removed")
        and item.get("label") != base.UNCLEAR_LABEL
    }
    if tuple(display_entries) != DOMAIN_ORDER or tuple(taxonomy_entries) != DOMAIN_ORDER:
        raise RuntimeError("eligible frozen Research Domain order or labels differ")
    if tuple(_APPROVED_MISSING_DOMAIN_MICRODEFINITIONS) != DOMAIN_ORDER:
        raise RuntimeError("approved missing-Domain mapping order or labels differ")

    result: dict[str, dict[str, object]] = {}
    for label in DOMAIN_ORDER:
        source = taxonomy_entries[label]
        rc3_definition = rc3_short_definition("domain", label)
        if str(display_entries[label]["owner_microdefinition"]) != rc3_definition:
            raise RuntimeError(f"candidate-0.3 and rc3 owner display wording differ: {label}")
        missing_fields = [
            name for name in DOMAIN_TAXONOMY_SOURCE_FIELDS if not source.get(name)
        ]
        if missing_fields:
            raise RuntimeError(f"frozen Domain source fields empty for {label}: {missing_fields}")
        result[label] = {
            "canonical_label": label,
            "full_definition": rc3_definition,
            "missing_choice_microdefinition": _APPROVED_MISSING_DOMAIN_MICRODEFINITIONS[label],
            "taxonomy_source_fields": DOMAIN_TAXONOMY_SOURCE_FIELDS,
            "boundary_summary": _DOMAIN_BOUNDARY_SUMMARIES[label],
            "approval_change_summary": _DOMAIN_APPROVAL_CHANGE_SUMMARIES[label],
            "author_approval": "Approved, 2026-07-28",
        }
    return result


OWNER_DOMAIN_DISPLAY = _build_owner_domain_display()


def owner_domain_redcap_choices() -> str:
    return " | ".join(
        f"{index}, {entry['canonical_label']}"
        for index, entry in enumerate(OWNER_DOMAIN_DISPLAY.values(), 1)
    )


def owner_domain_questionnaire_choices() -> str:
    return " / ".join(
        str(entry["missing_choice_microdefinition"])
        for entry in OWNER_DOMAIN_DISPLAY.values()
    )


def missing_menu_labels(owner_layer: str) -> tuple[str, ...]:
    groups, _ = base.taxonomy_groups()
    return tuple(str(item["label"]) for item in groups[owner_layer])


def label_only_redcap_choices(owner_layer: str) -> str:
    return " | ".join(
        f"{index}, {label}"
        for index, label in enumerate(missing_menu_labels(owner_layer), 1)
    )


def missing_questionnaire_choices(owner_layer: str) -> str:
    if owner_layer == "domain":
        return owner_domain_questionnaire_choices()
    return " / ".join(
        f"{label} — {rc3_short_definition(owner_layer, label)}"
        for label in missing_menu_labels(owner_layer)
    )


def _domain_boundary_definition(label: str) -> str:
    exact = _APPROVED_MISSING_DOMAIN_MICRODEFINITIONS[label]
    prefix = f"{label} — "
    if not exact.startswith(prefix):
        raise RuntimeError(f"approved Q6b wording has no exact label prefix: {label}")
    return exact.removeprefix(prefix)


def missing_reference_html(owner_layer: str) -> str:
    singular = {"domain": "domain", "purpose": "purpose", "tag": "tag"}[owner_layer]
    lines: list[str] = []
    for label in missing_menu_labels(owner_layer):
        definition = (
            _domain_boundary_definition(label)
            if owner_layer == "domain"
            else rc3_short_definition(owner_layer, label)
        )
        lines.append(
            f"<strong>{html.escape(label, quote=False)}</strong> — "
            f"{html.escape(definition, quote=False)}"
        )
    return (
        f"<details><summary>What each {singular} covers</summary>"
        '<div style="font-weight:400;">'
        + "<br>".join(lines)
        + "</div></details>"
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
REFERENCE_FIELD_BY_LAYER = {
    "domain": "po_miss_domain_reference",
    "purpose": "po_miss_purpose_reference",
    "tag": "po_miss_tag_reference",
}
REFERENCE_SECTION_BY_LAYER = {
    "domain": "Missing Research Domains",
    "purpose": "Missing Analytical Purposes",
    "tag": "Missing cross-cutting tags",
}
REGISTER_PROVENANCE = (
    "These details are reproduced from the UK Statistics Authority register of accredited "
    "research projects, June 2026 edition."
)
APPROVED_PRIVACY_WORDING = (
    "Please do not include confidential, sensitive or otherwise non-public information in your "
    "answers. Where wider project context affects your answer, describe it only at a general "
    "level you are comfortable sharing."
)
FINAL_COMMENT_CAUTION = (
    "Comments may be quoted in published outputs, so please avoid including restricted or "
    "personally identifying detail in anything you would not want reproduced."
)
FINAL_WITHDRAWAL_REMINDER = (
    "You may request withdrawal of this submitted review before the deadline stated in the "
    "Participant Information Sheet by contacting the study team and quoting the Review "
    "reference shown above."
)
GATE_LABELS = {
    "po_miss_domain": "Did you identify any missing domains?",
    "po_miss_purpose": "Did you identify any missing purposes?",
    "po_miss_tag": "Did you identify any missing tags?",
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
    # 2026-08-18: LF identity after correcting only the candidate-0.3 internal
    # CRLF-derived guard constants. Its preceding LF identity was
    # 499c0490ee808aaab646147f86c75a8b43e75b3ce03f1ce5c0ba6c5f2a6992d2.
    "scripts/build_project_owner_redcap_candidate_0_3.py": "6cec3e12a8db9e4a789e4b7926240f37a6c10e3985cad50fe5ccdff569da014f",
    # 2026-08-18: LF identity under .gitattributes; previous CRLF SHA-256 was
    # d4f8750ddcfb42d53d38aafd4a39c76f408eeeb0215f236c68db31730fc213df.
    "scripts/validate_project_owner_redcap_candidate_0_3.py": "a8a188aee462b40c1a5abd76401b00776776c4b012fea3222674e895ed2cce84",
    # 2026-08-18: LF identity. The previous 527eb3a9... value matched no version
    # of this file or any other blob at d51e5512 and is presumed to have come
    # from an intermediate authoring state that was never committed.
    "tests/test_project_owner_redcap_candidate_0_3.py": "26ef209cc931ccff5144cc7e2ba386f21144d12261b66f940668c605a53e6c5d",
    "preregistration/package/06_redcap/project_owner_redcap_data_dictionary_candidate_0.3.csv": "97219123588878b7a086a406d08a24e66966b7b4e38e740117335a429d2e011b",
    "preregistration/package/06_redcap/project_owner_redcap_field_specification_candidate_0.3.csv": "88154a52b62241e69ffd73e736744fab0728742e37350d123fe363ba4a3f11af",
    # 2026-08-18: LF identity under .gitattributes; previous CRLF SHA-256 was
    # 8fc9997cdd86a0871b998070e84215cad30218d8f408bd12a6b0d32eaab2b44e.
    "preregistration/package/06_redcap/project_owner_redcap_branching_specification_candidate_0.3.yaml": "fddc467a2f5518524c5759906016a42c6046c07e97afa35e6965f868330e0c9c",
    "preregistration/package/06_redcap/project_owner_redcap_expected_export_candidate_0.3.csv": "f95c9f85b41122eec40d035ae074f63148f8524c723a57c5b17ffaf2a18bc1d2",
    "preregistration/package/06_redcap/project_owner_redcap_formatting_audit_candidate_0.3.csv": "6667a1e48f876f73fd455f524e934753c8f80029aca3735900c61d8760df6fcb",
    # 2026-08-18: LF identity under .gitattributes; previous CRLF SHA-256 was
    # ecafc2765930879a61a3f883c22e0b3c7a7afca5269af849472a361a3c09db8b.
    "preregistration/package/06_redcap/project_owner_redcap_candidate_0.3_spec.md": "df54995df491427f51b0097c966b24675c816b954298c63260d75920e669bd09",
    # 2026-08-18: LF identity under .gitattributes; previous CRLF SHA-256 was
    # 48df58eff2cb470c807ed8ddc1742fae6b835b2201a12c75ca66b4a94d80b891.
    "preregistration/package/06_redcap/project_owner_redcap_candidate_0.3_live_configuration.md": "13be4db8727cf80e5f4b25736bde5974ecb97fe7ea7ad8e29a9c4bc2bc603431",
    "preregistration/package/06_redcap/live_qa/project_owner_synthetic_import_candidate_0.3.csv": "0aa47bf0089c76bcb10a2dcf9d208005a18e976eb28cef908566501db4ba3444",
}
PARTICIPANT_SOURCE_SHA256 = "3ceb089b06e707fb815f6fa3dab6cc261617e254aadeffe386ed6e131848af4a"
PARTICIPANT_SOURCE_SIZE = 35369
QUESTIONNAIRE_SOURCE_SHA256 = "cea613180ea2bb379f0996076d100c16fe09065098b743224e96f0d98cfa1b64"
QUESTIONNAIRE_SOURCE_SIZE = 21038


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def operational_tag_audit() -> list[dict[str, object]]:
    """Return operational tag rows using the shared production inclusion rule."""

    rows = [
        item
        for item in base.taxonomy_payload()["categories"]
        if item.get("layer") == base.LAYER_NAMES["tag"]
        and item.get("include_in_prompt") is True
        and not str(item.get("status", "")).lower().startswith("removed")
    ]
    labels = tuple(str(item.get("label", "")) for item in rows)
    if labels != OPERATIONAL_TAGS:
        raise RuntimeError(
            f"operational cross-cutting-tag invariant differs: {labels!r}"
        )
    active_only = tuple(
        str(item.get("label", ""))
        for item in rows
        if str(item.get("status", "")).lower() == "active"
    )
    if active_only == OPERATIONAL_TAGS:
        raise RuntimeError(
            "lifecycle status unexpectedly duplicates the operational inclusion rule"
        )
    return rows


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
    display_source = base.display_source()
    display_rows = [
        *display_source["labels"],
        *display_source["proposed_only_fallbacks"],
    ]
    display_definitions = {
        (RC3_LAYER_BY_OWNER_LAYER[str(item["owner_layer"])], str(item["canonical_label"])):
        str(item["owner_microdefinition"])
        for item in display_rows
    }
    if display_definitions != RC3_SHORT_DEFINITIONS:
        raise RuntimeError(
            "candidate-0.3 display wording and rc3 short_definition differ; "
            "candidate-0.4 proposed-label wording cannot be generated safely"
        )
    if tuple(missing_menu_labels("purpose")) != tuple(
        label
        for layer, label in RC3_SHORT_DEFINITIONS
        if layer == RC3_LAYER_BY_OWNER_LAYER["purpose"] and label != base.UNCLEAR_LABEL
    ):
        raise RuntimeError("Q7b/rc3 purpose order or coverage differs")
    if tuple(missing_menu_labels("tag")) != tuple(
        label
        for layer, label in RC3_SHORT_DEFINITIONS
        if layer == RC3_LAYER_BY_OWNER_LAYER["tag"]
    ):
        raise RuntimeError("Q8b/rc3 tag order or coverage differs")
    base.check_frozen_sources()
    operational_tag_audit()


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


def normal_weight_descriptive(label: str) -> str:
    """Apply one normal-weight body wrapper while preserving an initial lead-in."""

    if 'style="font-weight:400;"' in label:
        if label.count('style="font-weight:400;"') != 1:
            raise RuntimeError("descriptive label contains nested normal-weight wrappers")
        return label
    if label.startswith("<strong>") and "<br>" in label:
        split_at = label.index("<br>") + len("<br>")
        return (
            label[:split_at]
            + '<div style="font-weight:400;">'
            + label[split_at:]
            + "</div>"
        )
    return f'<div style="font-weight:400;">{label}</div>'


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
    by_name["po_intro"]["Field Label"] = CLASSIFICATION_INTRO_LABEL

    for name, label in QUESTIONNAIRE_FIELD_LABELS.items():
        by_name[name]["Field Label"] = label
    by_name["po_miss_domains"][
        "Choices, Calculations, OR Slider Labels"
    ] = owner_domain_redcap_choices()
    by_name["po_miss_purposes"][
        "Choices, Calculations, OR Slider Labels"
    ] = label_only_redcap_choices("purpose")
    by_name["po_miss_tags"][
        "Choices, Calculations, OR Slider Labels"
    ] = label_only_redcap_choices("tag")
    by_name["po_miss_purposes"]["Field Label"] = (
        "Which Analytical Purpose label or labels are missing? Select up to two."
    )
    by_name["po_tax_issue"]["Choices, Calculations, OR Slider Labels"] = (
        "1, Missing or inadequately represented category | "
        "2, Ambiguous or overlapping category boundaries | 5, Other taxonomy problem"
    )

    for removed_name in ("po_quote_permission", "po_taxonomy_ref"):
        removed_index = next(
            index
            for index, row in enumerate(rows)
            if row["Variable / Field Name"] == removed_name
        )
        rows.pop(removed_index)

    provenance_index = next(
        index
        for index, row in enumerate(rows)
        if row["Variable / Field Name"] == "public_register_url"
    )
    rows.insert(
        provenance_index,
        base.field(
            "po_register_provenance",
            "project_review",
            "descriptive",
            REGISTER_PROVENANCE,
        ),
    )
    by_name["public_register_url"]["Field Annotation"] = "@HIDDEN-SURVEY @READONLY"

    for row in rows:
        if "@READONLY-SURVEY" in row["Field Annotation"]:
            row["Required Field?"] = ""

    by_name["po_privacy"]["Field Label"] = (
        f"<strong>Important</strong><br>{APPROVED_PRIVACY_WORDING}"
    )
    by_name["po_final_warning"]["Field Label"] = (
        f"<strong>Important</strong><br>{FINAL_COMMENT_CAUTION}<br><br>"
        f"{FINAL_WITHDRAWAL_REMINDER}"
    )

    proposal_displays = {
        **{f"po_d{index:02d}_display": "domain" for index in range(1, 5)},
        **{f"po_p{index:02d}_display": "purpose" for index in range(1, 3)},
        **{f"po_t{index:02d}_display": "tag" for index in range(1, 3)},
    }
    for name, layer in proposal_displays.items():
        stem = name.removeprefix("po_").removesuffix("_display")
        by_name[name]["Field Label"] = (
            f"<div><strong>[prop_{stem}_label]</strong><br>"
            f'<span style="font-weight:400;">What this {layer} covers: '
            f"[prop_{stem}_def]</span></div>"
        )

    intro_index = next(
        index for index, row in enumerate(rows) if row["Variable / Field Name"] == "po_intro"
    )
    intro_row = rows.pop(intro_index)
    overview_index = next(
        index
        for index, row in enumerate(rows)
        if row["Variable / Field Name"] == "po_classification_overview"
    )
    rows.insert(overview_index, intro_row)

    missing_names = {
        "po_miss_domain",
        "po_miss_domains",
        "po_miss_domain_basis",
        "po_miss_purpose",
        "po_miss_purpose_guidance",
        "po_miss_purposes",
        "po_miss_purpose_basis",
        "po_miss_tag",
        "po_miss_tags",
        "po_miss_tag_basis",
    }
    missing_index = next(
        index
        for index, row in enumerate(rows)
        if row["Variable / Field Name"] == "po_miss_domain"
    )
    missing_rows = {
        row["Variable / Field Name"]: row
        for row in rows
        if row["Variable / Field Name"] in missing_names
    }
    rows[:] = [
        row for row in rows if row["Variable / Field Name"] not in missing_names
    ]
    for gate, label in GATE_LABELS.items():
        missing_rows[gate]["Field Label"] = label
        missing_rows[gate]["Section Header"] = ""
    for menu in ("po_miss_domains", "po_miss_purposes", "po_miss_tags"):
        missing_rows[menu]["Branching Logic (Show field only if...)"] = ""
        missing_rows[menu]["Required Field?"] = ""
    missing_rows["po_miss_purpose_guidance"][
        "Branching Logic (Show field only if...)"
    ] = ""

    reference_rows = {
        layer: base.field(
            REFERENCE_FIELD_BY_LAYER[layer],
            "project_review",
            "descriptive",
            missing_reference_html(layer),
            section=REFERENCE_SECTION_BY_LAYER[layer],
        )
        for layer in ("domain", "purpose", "tag")
    }
    domain_reminder = base.field(
        "po_miss_domain_reminder",
        "project_review",
        "descriptive",
        MISSING_DOMAIN_REMINDER_HTML,
    )
    purpose_reminder = base.field(
        "po_miss_purpose_reminder",
        "project_review",
        "descriptive",
        MISSING_PURPOSE_REMINDER_HTML,
    )
    reordered_missing = [
        reference_rows["domain"],
        domain_reminder,
        missing_rows["po_miss_domains"],
        missing_rows["po_miss_domain_basis"],
        missing_rows["po_miss_domain"],
        reference_rows["purpose"],
        missing_rows["po_miss_purpose_guidance"],
        purpose_reminder,
        missing_rows["po_miss_purposes"],
        missing_rows["po_miss_purpose_basis"],
        missing_rows["po_miss_purpose"],
        reference_rows["tag"],
        missing_rows["po_miss_tags"],
        missing_rows["po_miss_tag_basis"],
        missing_rows["po_miss_tag"],
    ]
    rows[missing_index:missing_index] = reordered_missing

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

    for row in rows:
        if row["Field Type"] == "descriptive":
            row["Field Label"] = normal_weight_descriptive(row["Field Label"])

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
        elif name in {"prop_t01_def", "prop_t02_def"}:
            slot = "prop_t01_status" if name == "prop_t01_def" else "prop_t02_status"
            row["construct"] = "participant_facing_rc3_tag_short_definition"
            row["notes"] = rc3_short_definition("tag", TAG_FIELD_MAPPING[slot])
        elif name in {"po_t01_display", "po_t02_display"}:
            slot = "prop_t01_status" if name == "po_t01_display" else "prop_t02_status"
            row["construct"] = "tag_definition_immediately_before_proposed_status"
            row["notes"] = (
                f"Pipes the canonical label and exact full definition for "
                f"{TAG_FIELD_MAPPING[slot]}."
            )
        elif name == "po_intro":
            row["construct"] = "participant_facing_classification_orientation"
            row["notes"] = (
                "Exact canonical Questionnaire Section 2 orientation with the governing "
                "substantive-focus phrase strongly emphasised; displayed after project "
                "information and before po_classification_overview."
            )
        elif name in {"po_miss_domain_reminder", "po_miss_purpose_reminder"}:
            row["construct"] = "participant_facing_substantive_focus_reminder"
            row["notes"] = (
                "Display-only threshold clarification immediately before its missing-label "
                "checkbox; the governing phrase uses supported strong HTML markup."
            )
        elif name in set(REFERENCE_FIELD_BY_LAYER.values()):
            row["construct"] = "participant_facing_complete_missing_label_reference"
            row["notes"] = (
                "Display-only complete nominable-category reference immediately before its "
                "unconditional missing-label checkbox."
            )
        elif name == "po_register_provenance":
            row["construct"] = "participant_facing_static_register_provenance"
            row["notes"] = REGISTER_PROVENANCE
        elif name == "po_miss_domains":
            row["construct"] = "author_approved_missing_domain_identification"
            row["notes"] = (
                "Label-only options; approved Q6b boundary wording is displayed in "
                "po_miss_domain_reference."
            )
        elif name in {"po_miss_purposes", "po_miss_tags"}:
            row["construct"] = "missing_classification_identification"
            row["notes"] = (
                "Label-only options; approved Q7b/Q8b wording is displayed in the adjacent "
                "reference block."
            )
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
        "classification_orientation_field": "po_intro",
        "classification_orientation_paragraphs": list(CLASSIFICATION_INTRO_PARAGRAPHS),
        "classification_orientation_order": (
            "project information -> po_intro -> po_classification_overview -> detailed judgements"
        ),
        "substantive_focus_rule": {
            "plain_text": SUBSTANTIVE_FOCUS_PARAGRAPH,
            "bold_phrase": SUBSTANTIVE_FOCUS_PHRASE,
            "redcap_markup": f"<strong>{SUBSTANTIVE_FOCUS_PHRASE}</strong>",
            "position": "inside po_intro before po_classification_overview",
        },
        "missing_classification_reminders": {
            "po_miss_domain_reminder": {
                "plain_text": MISSING_DOMAIN_REMINDER,
                "bold_phrase": MISSING_DOMAIN_REMINDER_PHRASE,
                "branching": "",
                "position": "after po_miss_domain_reference and before po_miss_domains",
            },
            "po_miss_purpose_reminder": {
                "plain_text": MISSING_PURPOSE_REMINDER,
                "bold_phrase": MISSING_PURPOSE_REMINDER_PHRASE,
                "branching": "",
                "position": "after po_miss_purpose_guidance and before po_miss_purposes",
            },
        },
        "taxonomy_reference": (
            "no standalone field or attachment; complete nominable-category reference blocks "
            "appear at the point of each missing-label decision"
        ),
        "missing_label_reference_fields": REFERENCE_FIELD_BY_LAYER,
        "missing_domain_microdefinitions": (
            "author-approved owner-instrument display aids generated from OWNER_DOMAIN_DISPLAY; "
            "live semantic and display QA pending"
        ),
        "missing_domain_labels": list(DOMAIN_ORDER),
        "missing_domain_choices": owner_domain_redcap_choices(),
        "missing_domain_concordance": (
            "project_owner_domain_wording_concordance_candidate_0.4.md"
        ),
    }
    tag_rows = operational_tag_audit()
    branch["tag_reviews"].update(
        {
            "operational_inclusion_rule": OPERATIONAL_INCLUSION_RULE,
            "operational_set": list(OPERATIONAL_TAGS),
            "lifecycle_statuses": {
                str(item["label"]): str(item.get("status", "")) for item in tag_rows
            },
            "lifecycle_status_is_not_operational_inclusion": True,
            "definitions": TAG_DEFINITIONS,
            "proposed_display_short_definitions": {
                label: rc3_short_definition("tag", label) for label in OPERATIONAL_TAGS
            },
            "rc3_short_definition_immediately_before_status": True,
            "independent_required_judgements": True,
        }
    )
    for index, label in enumerate(OPERATIONAL_TAGS, 1):
        key = f"t{index:02d}"
        branch["tag_reviews"]["fields"][key].update(
            {
                "label": label,
                "definition": TAG_DEFINITIONS[label],
                "definition_field": f"prop_t{index:02d}_def",
                "display_field": f"po_t{index:02d}_display",
            }
        )
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
        QUOTATION_POLICY
    )
    completion["missing_labels"] = (
        "all three required post-list identification radios; checkbox selections are optional "
        "raw responses and contradictory radio/checkbox states require a separately approved "
        "analysis rule"
    )
    branch["missing_label_branching"] = {
        "gateways_required": True,
        "gateway_position": "after each checkbox and optional basis field",
        "checkbox_menus_unconditional": True,
        "checkbox_menus_required": False,
        "purpose_guidance_field": "po_miss_purpose_guidance",
        "purpose_max_checked_annotation": "@MAXCHECKED=2",
        "contradictory_state_rule": (
            "pending: checkbox selections with a final No or Unsure radio response must be "
            "flagged and handled under an approved analysis rule"
        ),
    }
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
        elif row["variable"] in {"prop_t01_def", "prop_t02_def"}:
            slot = (
                "prop_t01_status"
                if row["variable"] == "prop_t01_def"
                else "prop_t02_status"
            )
            row["notes"] = (
                f"Exact rc3 proposed-label short definition for {TAG_FIELD_MAPPING[slot]}; "
                "populated on every Project Review repeat row."
            )
        elif row["variable"] in {"po_miss_domains", "po_miss_purposes", "po_miss_tags"}:
            row["notes"] = (
                "Optional raw checkbox selections displayed unconditionally. Preserve alongside "
                "the required post-list radio; contradictory states require an approved analysis rule."
            )
    write_csv(EXPORT_SPEC, export_headers, export_rows)


def patch_formatting_audit() -> None:
    with FORMATTING_AUDIT.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        headers = list(rows[0])
    for row in rows:
        if row["variable_name"] == "po_intro":
            row["participant_visible_purpose"] = (
                "Concise classification orientation matching canonical Questionnaire Section 2"
            )
            row["heading_text"] = CLASSIFICATION_INTRO_PARAGRAPHS[0]
            row["body_text"] = " ".join(CLASSIFICATION_INTRO_PARAGRAPHS[1:])
            row["remaining_live_qa_requirement"] = (
                "Verify exact wording before the read-only classification overview and confirm "
                "that only the governing phrase is visibly bold on desktop and mobile, with no "
                "literal or malformed HTML."
            )
        if row["variable_name"] in {
            "po_miss_domain_reminder",
            "po_miss_purpose_reminder",
        }:
            domain = row["variable_name"] == "po_miss_domain_reminder"
            row["participant_visible_purpose"] = (
                "Missing-Domain substantive-subject threshold reminder"
                if domain
                else "Missing-Purpose substantive-analytical-aim threshold reminder"
            )
            row["heading_text"] = ""
            row["body_text"] = MISSING_DOMAIN_REMINDER if domain else MISSING_PURPOSE_REMINDER
            row["html_tags_used"] = "div | strong"
            row["final_formatting_status"] = (
                "Only the governing phrase is wrapped in supported strong HTML markup"
            )
            row["remaining_live_qa_requirement"] = (
                "Verify immediate placement before the checkbox, exact plain wording and clearly "
                "bold governing phrase on desktop/mobile without literal HTML or unusable wrapping."
            )
        if row["variable_name"] in {"po_t01_display", "po_t02_display"}:
            slot = (
                "prop_t01_status"
                if row["variable_name"] == "po_t01_display"
                else "prop_t02_status"
            )
            row["participant_visible_purpose"] = (
                f"Canonical label and exact rc3 short definition for "
                f"{TAG_FIELD_MAPPING[slot]}"
            )
            row["remaining_live_qa_requirement"] = (
                "Verify the piped canonical label and exact rc3 short definition render immediately "
                "before the proposed Applied / Not applied status and tag questions."
            )
    if any(row["variable_name"] == "po_taxonomy_ref" for row in rows):
        raise RuntimeError("formatting audit retained po_taxonomy_ref")
    for name, plain, phrase, purpose in (
        (
            "po_miss_domain_reminder",
            MISSING_DOMAIN_REMINDER,
            MISSING_DOMAIN_REMINDER_PHRASE,
            "Missing-Domain substantive-subject threshold reminder",
        ),
        (
            "po_miss_purpose_reminder",
            MISSING_PURPOSE_REMINDER,
            MISSING_PURPOSE_REMINDER_PHRASE,
            "Missing-Purpose substantive-analytical-aim threshold reminder",
        ),
    ):
        rows.append(
            {
                "variable_name": name,
                "instrument": "project_review",
                "participant_visible_purpose": purpose,
                "contains_heading": "no",
                "heading_text": "",
                "body_text": plain,
                "html_tags_used": "div | strong",
                "whole_block_bold_present_before_correction": "no",
                "final_formatting_status": (
                    "Only the governing phrase is wrapped in supported strong HTML markup"
                ),
                "remaining_live_qa_requirement": (
                    "Verify immediate placement before the checkbox, exact plain wording and "
                    "clearly bold governing phrase on desktop/mobile without literal HTML or "
                    "unusable wrapping."
                ),
            }
        )
    for layer in ("domain", "purpose", "tag"):
        rows.append(
            {
                "variable_name": REFERENCE_FIELD_BY_LAYER[layer],
                "instrument": "project_review",
                "participant_visible_purpose": (
                    f"Complete collapsible missing-{layer} definition reference"
                ),
                "contains_heading": "yes",
                "heading_text": f"What each {layer} covers",
                "body_text": " | ".join(
                    (
                        _APPROVED_MISSING_DOMAIN_MICRODEFINITIONS[label]
                        if layer == "domain"
                        else f"{label} — {rc3_short_definition(layer, label)}"
                    )
                    for label in missing_menu_labels(layer)
                ),
                "html_tags_used": "br | details | div | strong | summary",
                "whole_block_bold_present_before_correction": "no",
                "final_formatting_status": "normal-weight definitions with bold category labels",
                "remaining_live_qa_requirement": (
                    "Verify <details> expansion, every category and boundary, desktop/mobile "
                    "wrapping and PDF/export behaviour; use an always-open div if unsupported."
                ),
            }
        )
    rows.append(
        {
            "variable_name": "po_register_provenance",
            "instrument": "project_review",
            "participant_visible_purpose": "Static public-register provenance",
            "contains_heading": "no",
            "heading_text": "",
            "body_text": REGISTER_PROVENANCE,
            "html_tags_used": "div",
            "whole_block_bold_present_before_correction": "no",
            "final_formatting_status": "normal-weight descriptive text",
            "remaining_live_qa_requirement": "Verify placement after public project details.",
        }
    )
    rows.append(
        {
            "variable_name": "po_miss_domains",
            "instrument": "project_review",
            "participant_visible_purpose": (
                "Author-approved missing-Research-Domain checkbox wording"
            ),
            "contains_heading": "no",
            "heading_text": "",
            "body_text": owner_domain_redcap_choices(),
            "html_tags_used": "",
            "whole_block_bold_present_before_correction": "no",
            "final_formatting_status": (
                "Exact questionnaire/dictionary wording; semantic concordance author-approved"
            ),
            "remaining_live_qa_requirement": (
                "Verify all 11 full choices, order, wrapping, desktop/mobile usability, "
                "required multi-select behaviour and semantic concordance with full definitions."
            ),
        }
    )
    write_csv(FORMATTING_AUDIT, headers, rows)


def patch_fixture_proposed_definitions() -> None:
    with IMPORT_FIXTURE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        headers = list(rows[0])
    for row in rows:
        repeating = row["redcap_repeat_instrument"] == "project_review"
        for index, label in enumerate(OPERATIONAL_TAGS, 1):
            label_field = f"prop_t{index:02d}_label"
            definition_field = f"prop_t{index:02d}_def"
            status_field = f"prop_t{index:02d}_status"
            if repeating:
                if row[label_field] != label or row[status_field] not in {"0", "1"}:
                    raise RuntimeError(
                        f"synthetic fixture tag mapping differs for {label_field}"
                    )
                row[definition_field] = rc3_short_definition("tag", label)
            elif any(row[field] for field in (label_field, definition_field, status_field)):
                raise RuntimeError("owner fixture row unexpectedly contains project tag values")
    write_csv(IMPORT_FIXTURE, headers, rows)


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_domain_wording_audits() -> None:
    """Write the approved review decision and human concordance record."""

    source_fields = ", ".join(DOMAIN_TAXONOMY_SOURCE_FIELDS)
    review_rows = "\n".join(
        "| "
        + " | ".join(
            _markdown_cell(value)
            for value in (
                label,
                entry["missing_choice_microdefinition"],
                len(str(entry["missing_choice_microdefinition"]).split()),
                source_fields,
                entry["boundary_summary"],
                entry["approval_change_summary"],
                entry["author_approval"],
                "Implemented in candidate 0.4",
                "project_owner_domain_wording_concordance_candidate_0.4.md",
            )
        )
        + " |"
        for label, entry in OWNER_DOMAIN_DISPLAY.items()
    )
    MISSING_DOMAIN_REVIEW.write_text(
        f"""# Candidate 0.4 missing-domain microdefinitions — approved implementation

Status: **approved instrument wording; implemented in candidate 0.4; live semantic and display QA pending**. Author approval was recorded on 2026-07-28. Candidate 0.4 remains unfrozen, pre-recruitment and non-authoritative; PID 9149 migration and recruitment remain blocked until controlled migration and successful live QA.

These Project Owner instrument display aids apply to the complete 11-category reference block shown immediately before the label-only Research Domain checkbox choices. The generator mapping OWNER_DOMAIN_DISPLAY is their single operational source. The frozen taxonomy remains authoritative for labels, definitions, inclusion rules, exclusion rules, examples, counterexamples and boundaries; it was not changed.

| Canonical Domain | Final approved Q6b wording | Word count | Frozen source fields | Boundary addressed | Change from initial draft | Author approval | Implementation | Concordance record |
|---|---|---:|---|---|---|---|---|---|
{review_rows}

## Author-review decision

The project author approved the exact 11 lines above on 2026-07-28. The table records every substantive change from the earlier draft. The approved lines remain in Q6b of the canonical questionnaire and are generated into the REDCap reference block, field specification and formatting audit. The checkbox itself contains labels only. Unclear from Register Entry remains excluded.

## Semantic-concordance status

The companion project_owner_domain_wording_concordance_candidate_0.4.md records the author-approved comparison of each full proposed-label definition with its compressed missing-label wording. Automated checks establish label-set, source, order and exact-text alignment; they do not claim to establish complete natural-language semantic equivalence. Human semantic and display confirmation remains mandatory during controlled PID 9149 live QA.

No taxonomy rule, category, field, production prompt, production classification or dashboard schema was changed. No owner-facing microdefinition field was added to the frozen taxonomy, and no freeze cycle was initiated.
""",
        encoding="utf-8",
    )

    concordance_rows = "\n".join(
        "| "
        + " | ".join(
            _markdown_cell(value)
            for value in (
                label,
                entry["full_definition"],
                entry["missing_choice_microdefinition"],
                source_fields,
                "Yes — author-reviewed; both identify the same substantive research object.",
                "Yes — author-reviewed.",
                entry["boundary_summary"],
                entry["author_approval"],
                "Pending — controlled PID 9149 live QA not executed.",
            )
        )
        + " |"
        for label, entry in OWNER_DOMAIN_DISPLAY.items()
    )
    DOMAIN_CONCORDANCE.write_text(
        f"""# Candidate 0.4 Research Domain wording concordance

Status: **author-approved repository concordance; live-QA result pending**. This is an auditable human review record for Project Owner candidate 0.4, not a taxonomy amendment. Automated exact-text and structural checks supplement but cannot replace human semantic review.

| Canonical Domain | Full proposed-label definition | Approved Q6b wording | Frozen source fields | Inclusion direction aligned | Boundary direction aligned | Main boundary compressed | Author approval | Live-QA result |
|---|---|---|---|---|---|---|---|---|
{concordance_rows}

The full definition and compressed Q6b wording must continue to identify the same substantive research object and apply compatible inclusion and exclusion boundaries. Migration approval fails if live QA judges either wording to direct participants toward assigning a Domain in circumstances excluded by the other wording.

The canonical labels and full definitions remain derived from the frozen taxonomy/display pipeline. The Q6b aids are stored only in the candidate-0.4 generator mapping; taxonomy_data_dictionary.yaml and the frozen production prompt were not changed. Unclear from Register Entry is not an eligible missing-Domain choice.
""",
        encoding="utf-8",
    )


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

The Project Owner instrument remains unfrozen and non-authoritative. This candidate does not authorise recruitment or live migration. Both canonical participant DOCX files are pinned by SHA-256 and byte size; generation stops if either changes without an authorised metadata refresh. The missing-Domain wording is author-approved and repository-validated; controlled migration and live semantic/display QA remain mandatory before recruitment.

## Project Review orientation and point-of-need references

After the public project information, `po_intro` presents the six-paragraph Questionnaire Section 2 block beginning “How the classifications work”. The governing substantive-focus phrase is the only phrase strongly emphasised in its threshold paragraph. It is followed immediately by the otherwise unchanged read-only `po_classification_overview`, then the detailed Domain, Purpose and tag judgements. The intro contains no consent, confidentiality, withdrawal or Save & Return Later wording and introduces no training material.

The inherited participant-visible `po_taxonomy_ref` synthetic-QA placeholder remains absent. It is replaced functionally—not as a standalone field or attachment—by three complete collapsible reference blocks immediately before the missing-Domain, missing-Purpose and missing-tag menus. These blocks are the participant delivery route for every nominable category definition at the point of need.

Q6b contains exactly 11 label-only missing-Domain choices. `po_miss_domain_reference` displays every matching author-approved boundary definition generated from `OWNER_DOMAIN_DISPLAY`; `Unclear from Register Entry` is excluded. Q7b and Q8b likewise use label-only choices with complete adjacent reference blocks sourced from their questionnaire/rc3-identical wording. `project_owner_missing_domain_microdefinitions_candidate_0.4_review.md` records the author decision, and `project_owner_domain_wording_concordance_candidate_0.4.md` records the human semantic review. Live semantic, `<details>` and PDF/export display QA remains pending.

The three missing-label menus are displayed unconditionally and are optional. Their required Yes/No/Unsure identification radios follow each menu and optional basis field. Domain and Purpose guidance remains visible before the relevant checkbox. This deliberate departure from the approved questionnaire branching must be notified to the REC. Checkbox selections combined with a final No or Unsure response are possible and require a separately approved analysis rule.

## Operational cross-cutting-tag invariant

The operational set contains exactly two frozen machine values, in this order:

- `Demographic disparities / equity tag` (`prop_t01_status`);
- `COVID-19 & Pandemic` (`prop_t02_status`).

Operational inclusion is determined by `{OPERATIONAL_INCLUSION_RULE}`. Lifecycle/provenance status is not the inclusion criterion: the first tag is `new v3.4`, while the second is `active`, and both are operational because they satisfy the explicit rule. The production classifier, production outputs, dashboard and Project Owner pipeline therefore retain both tags; no one-tag bug exists. Candidate 0.4 changes neither the frozen taxonomy nor the production prompt.

Each Project Review displays the canonical label and exact rc3 proposed-label short definition from `prop_t01_def` or `prop_t02_def` immediately before its Applied / Not applied proposed status. The longer Questionnaire and Appendix A definitions remain documentary reference wording and are not substituted into the proposed-label display. Both independent correctness and visibility blocks remain required for analytical completion.

## Ethics-to-REDCap consent traceability

The participant-visible sequence is: full Participant Information Sheet v3; `intended_recipient`; ten separately stored confirmations; final `owner_consent`; and optional `ack_pref` only after valid affirmative consent. The controlled live project must display or attach the full approved v3 information sheet before these fields.

Participant-document alignment is complete for the implemented candidate-0.4 content: the canonical consent DOCX contains the ten statements, final consent decision and acknowledgement wording represented here; the canonical Questionnaire v3 reproduces the participant-facing Project Review orientation, labels, response choices and author-approved inline checkbox microdefinitions. Its Appendix B records the complete owner-level consent-validity join. Q13, participant-facing per-project quotation permission and taxonomy-reference placeholders are absent. Controlled migration and live QA remain mandatory before recruitment.

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

Candidate 0.4 removes `po_quote_permission` from the generator, dictionary, Project Review count, branching specification, field and export specifications, fixture and analytical-completion documentation. It is not replaced. {QUOTATION_POLICY}

`po_final_warning` now follows `po_other_comment` immediately before submission and has no quotation-permission dependency.

All participant-visible read-only stimulus fields are optional, so an empty prefilled value cannot block submission. `public_register_url` is retained for downstream compatibility but survey-hidden; `po_register_provenance` supplies the static June 2026 register provenance line. `po_privacy` uses both sentences of the approved questionnaire wording. Descriptive-field bodies render at normal weight while intended headings and proposed category labels remain emphasised.

## Fixture and long-format analysis

The synthetic fixture remains three owners, 19 pre-created Project Review instances and 22 long-format rows. Owner consent responses, all ten confirmations, `consent_items_complete`, final consent and acknowledgement are blank on import. Owner consent values occur only on the non-repeating owner row; Project Review repeat rows keep them blank. No synthetic participant is imported as consented.

Analysis must join the non-repeating owner row to reviews by `owner_id` and require intended-recipient Yes, all-confirmed 1, final consent Yes and Owner Consent complete. Review-row values alone must never establish consent.

## Scope exclusions and change record

Reason: repair participant-facing requiredness, density, reference delivery, missing-label task order, privacy, provenance and descriptive formatting defects while preserving category wording authorities. Nature: candidate 0.4 remains unfrozen, pre-recruitment and non-authoritative. The missing-label gate removal intentionally departs from questionnaire Q6a/Q7a/Q8a branching and requires REC notification before migration. No frozen taxonomy, production prompt, candidate 0.3 artefact, assignment, sample or participant record changed.
""",
        encoding="utf-8",
    )

    LIVE_CONFIG.write_text(
        f"""# Project Owner candidate 0.4 authorised-administrator migration and live-QA checklist

Status: instructions only. Do not execute without separate authorisation. Candidate 0.4 is unfrozen, pre-recruitment and non-authoritative. The missing-Domain wording is author-approved and implemented; PID 9149 migration and recruitment remain blocked until controlled migration is authorised and every live-QA item passes.

## Before migration

Document baseline: verify the canonical consent and questionnaire DOCX files match the SHA-256 and byte-size metadata embedded in the generator and branching specification. Confirm the consent wording, questionnaire labels/options and Appendix B against the generated dictionary before any live action. The former untracked `- Copy` questionnaire is not required.

Use the generated dictionary as the migration source. `project_owner_missing_domain_microdefinitions_candidate_0.4_review.md` records the author approval, and `project_owner_domain_wording_concordance_candidate_0.4.md` supplies the 11-row semantic-concordance record whose live-QA result must be completed.

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

23. Verify `po_quote_permission` and any participant-facing replacement quotation-permission question are absent everywhere in Project Review. Quotation remains a later point-of-use email process using the exact proposed wording and context and requiring written agreement.
24. Verify `po_final_warning` follows final comments immediately before submission and does not refer to quotation permission.
25. Verify both permanent tag blocks appear in every Project Review, each with its exact rc3 proposed-label short definition immediately before the Applied / Not applied proposed status.
26. Verify consent values export only on the non-repeating owner row and are blank on every Project Review repeat row.
27. Verify valid consent is joined onto review rows using all four conditions: intended recipient, all-confirmed, final Yes and Owner Consent complete.
28. Verify Save & Return Later, return-to-queue, completed-response modification disabled, no automatic next survey, no redirect and no participant-created repeat.
29. Verify desktop and mobile rendering of the full information sheet, ten statements, final decision, acknowledgement and repeated reviews.
30. Archive post-migration screenshots, dictionary, configuration evidence, synthetic export and source/live comparison in the approved restricted evidence location.
31. Verify `prop_t01_status` maps to `Demographic disparities / equity tag` and `prop_t02_status` maps to `COVID-19 & Pandemic` in every review and export.
32. Verify each tag's correctness and visibility questions operate independently and each visibility explanation retains its existing Partly visible / Not visible / Unsure branch.
33. Omit each tag correctness or visibility judgement in turn and confirm analytical completion remains false.
34. Verify all proposed-label displays use rc3 short definitions and that the separate missing-label reference blocks use Q6b/Q7b/Q8b wording.
35. Verify `po_taxonomy_ref` is absent and the three point-of-need reference blocks are the only complete participant-facing framework reference.
36. Verify the exact six-paragraph `po_intro` block appears after project information and immediately before the unchanged read-only `po_classification_overview`.
37. Verify `po_intro` contains no duplicate Save & Return Later, consent, confidentiality or withdrawal guidance.
38. Verify Q6b displays all 11 label-only choices in `DOMAIN_ORDER`, with no `Unclear from Register Entry` choice, and that `po_miss_domain_reference` contains all 11 exact approved boundary definitions.
39. Verify all three missing-label multi-select checkboxes display unconditionally and remain optional, while each required Yes/No/Unsure radio follows its checkbox and optional basis field.
40. Verify every reference block expands on desktop/mobile without truncation or ambiguous line wrapping and test whether `<details>` survives PDF export. If it does not, replace it with an always-open `<div>` before migration approval.
41. Research Domain wording concordance: For every Research Domain, compare the rc3 definition displayed when the Domain is proposed with the Q6b boundary wording displayed in `po_miss_domain_reference`. Confirm that both identify the same substantive research object and apply compatible inclusion and exclusion boundaries.
42. Record an individual pass/fail live-QA result for all 11 Domains in `project_owner_domain_wording_concordance_candidate_0.4.md` or an associated completed QA record. Migration approval fails if any Domain points in materially different directions.
43. Confirm no separate taxonomy-reference document, link or placeholder appears and no participant-facing text promises one.
44. Verify the substantive-focus rule is visible before participants see or judge proposed classifications; confirm only `{SUBSTANTIVE_FOCUS_PHRASE}` is clearly bold on desktop and mobile.
45. Confirm the bold is not lost, malformed or displayed as literal HTML, and remains visible and readable after line wrapping.
46. Verify `po_miss_domain_reminder` appears after the Domain reference and before Q6b and clearly bolds only `{MISSING_DOMAIN_REMINDER_PHRASE}` on desktop and mobile.
47. Verify the Purpose reference, maximum-two guidance and `po_miss_purpose_reminder` all appear before Q7b, with only `{MISSING_PURPOSE_REMINDER_PHRASE}` strongly emphasised in the reminder.
48. Confirm participants are not instructed to assign a Domain merely because a dataset, variable, population characteristic or contextual factor is present.
49. Confirm participants are not instructed to assign a Purpose merely because a method, analytical step or secondary feature is present.
50. Confirm both reminders and the purpose guidance are unconditional; checkbox codes and order remain unchanged while checkbox requiredness is removed.
51. Compare the plain wording and visual emphasis of all three substantive-focus displays with the canonical questionnaire.
52. Fail migration approval if the governing rule is absent, appears after the classification overview or is not visibly emphasised.

Migration and recruitment are prohibited until controlled migration is authorised, all live tests pass, every Domain has a recorded semantic-concordance pass, residual differences are resolved or approved, and candidate 0.4 receives the required ethics/governance and repository approval.
""",
        encoding="utf-8",
    )

    tag_rows = operational_tag_audit()
    lifecycle = "\n".join(
        f"- `{item['label']}`: `status={item.get('status')}`, `include_in_prompt=true`."
        for item in tag_rows
    )
    TAG_AND_QUOTATION_AUDIT.write_text(
        f"""# Candidate 0.4 cross-cutting-tag and quotation-permission audit

Status: completed offline pre-migration audit; candidate 0.4 remains unfrozen, pre-recruitment and non-authoritative.

## Operational inclusion and data flow

The authoritative taxonomy is `taxonomy_data_dictionary.yaml`. The operational inclusion rule is: **{OPERATIONAL_INCLUSION_RULE}**. It is implemented consistently in:

- `analysis/llm_theme_analysis_v3.py` (`_in_prompt_category`, `CROSS_CUTTING_TAGS`) for production prompt construction and output schema;
- `dashboard/taxonomy.py` (`_is_active`, `TAG_LABELS`) for dashboard values;
- `scripts/build_project_owner_redcap_candidate_0_3.py` (`taxonomy_groups`) inherited by candidate 0.4 for owner display and assignment generation;
- `scripts/build_project_owner_redcap_candidate_0_4.py` (`operational_tag_audit`) for the candidate guard, definitions and fixture;
- candidate field/export/branching specifications, synthetic fixture, validator and regression tests for analysis and QA.

The final operational set is exactly:

1. `Demographic disparities / equity tag` → `prop_t01_status`;
2. `COVID-19 & Pandemic` → `prop_t02_status`.

Lifecycle/provenance metadata deliberately differ:

{lifecycle}

Consequently, `status == active` is not and must not become the sole operational-inclusion test. No one-tag bug existed. Both tags are present in production instructions, outputs, dashboard data, owner records and both permanent REDCap review blocks. Every synthetic Project Review row carries both proposed statuses, and analytical completion requires both independent correctness and visibility judgements.

The frozen taxonomy and production prompt were inspected and deliberately left unchanged. No taxonomy category, label, output value, classification decision, assignment, sample or participant data was modified.

## Participant-facing definitions

The canonical Questionnaire main sections 5.1 and 5.2 and Appendix A retain their full reference definitions. REDCap `prop_t01_def` and `prop_t02_def` instead carry the exact rc3 short definitions for proposed-label display. The missing-tag reference uses the Q8b wording, which is byte-identical to rc3 after entity decoding and whitespace normalisation.

## Quotation-permission audit

`po_quote_permission` and any participant-facing equivalent are absent from the current candidate-0.4 dictionary, field specification, branching specification, expected export, synthetic fixture, analytical-completion rule, formatting audit, live-configuration guide and operational tests. The generator mentions the legacy variable only to remove it from the candidate-0.3 source rows; validators and tests mention it only as negative regression assertions. Historical candidate 0.1–0.3 artefacts, version history and audit logs remain unchanged or explicitly historical.

{QUOTATION_POLICY}

The live-QA checklist requires an authorised administrator to confirm that the migrated PID 9149 Project Review contains no quotation-permission field. Migration and live QA were not executed, and recruitment remains blocked.
""",
        encoding="utf-8",
    )


def main() -> int:
    check_sources()
    configure_base_outputs()
    rows, meta = build_dictionary()
    meta["fixture_columns"] = len(base.fixture_import_headers(rows))
    write_csv(DICTIONARY, base.HEADERS, rows)
    write_csv(IMPORT_READY_DICTIONARY, base.HEADERS, rows)
    base.build_specs(rows, meta)
    patch_generated_specs(rows)
    base.build_formatting_audit(
        [
            row
            for row in rows
            if row["Variable / Field Name"]
            not in {
                "po_miss_domain_reminder",
                "po_miss_purpose_reminder",
                "po_miss_domain_reference",
                "po_miss_purpose_reference",
                "po_miss_tag_reference",
                "po_register_provenance",
            }
        ]
    )
    patch_formatting_audit()
    build_domain_wording_audits()
    build_documentation(meta)
    base.build_fixture(rows)
    patch_fixture_proposed_definitions()
    print(
        yaml.safe_dump(
            {
                "version": VERSION,
                "status": STATUS,
                "dictionary": str(DICTIONARY.relative_to(ROOT)).replace("\\", "/"),
                "dictionary_sha256": sha256(DICTIONARY),
                "import_ready_dictionary": str(
                    IMPORT_READY_DICTIONARY.relative_to(ROOT)
                ).replace("\\", "/"),
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
