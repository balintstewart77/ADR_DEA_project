#!/usr/bin/env python3
"""Build owner-redcap-candidate-0.3 deterministically and entirely offline."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import html
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "preregistration/package/06_redcap"
LIVE_QA = PACKAGE / "live_qa"
VERSION = "owner-redcap-candidate-0.3"
CANDIDATE_SOURCE_COMMIT = "69cf6665b845428fa2abd855c0445ae20589579f"
STATUS = "development_candidate_unfrozen_controlled_import_and_live_qa_pending"
PARTICIPANT_INFO_VERSION = "project-owner-information-pending-approval-candidate-0.3"
CONSENT_FORM_VERSION = "owner-consent-candidate-0.3"
TAXONOMY_DISPLAY_VERSION = "project-owner-taxonomy-display-v1"
TAXONOMY_REFERENCE_VERSION = "project-owner-taxonomy-reference-v1"
TAXONOMY_REFERENCE_DATE = "23 July 2026"
TAXONOMY_REVIEW_STATUS = "approved_by_author"
TAXONOMY_REVIEWER = "Balint Stewart"
TAXONOMY_REVIEW_DATE = "2026-07-23"
REFERENCE_PREFERRED_WORD_MIN = 15
REFERENCE_PREFERRED_WORD_MAX = 60
SOURCE_POPULATION_VERSION = "20260601-cleaned-1308"
PRODUCTION_VERSION = "dea-validation-production-20260702-fable5-dict-1.0-rc2"

TAXONOMY = ROOT / "taxonomy_data_dictionary.yaml"
FROZEN_OUTPUT = ROOT / "analysis/outputs_classified_20260702_fable5/layer_classifications.csv"
RELEASE_MANIFEST = PACKAGE.parent / "02_taxonomy_prompt_and_model/production_release_manifest.yaml"
V02_DICTIONARY = PACKAGE / "project_owner_redcap_data_dictionary_candidate_0.2.csv"

DICTIONARY = PACKAGE / "project_owner_redcap_data_dictionary_candidate_0.3.csv"
SPEC = PACKAGE / "project_owner_redcap_candidate_0.3_spec.md"
LIVE_CONFIG = PACKAGE / "project_owner_redcap_candidate_0.3_live_configuration.md"
IMPORT_FIXTURE = LIVE_QA / "project_owner_synthetic_import_candidate_0.3.csv"
TAXONOMY_DISPLAY = PACKAGE / "project_owner_taxonomy_display_v1.yaml"
TAXONOMY_REFERENCE = PACKAGE / "project_owner_taxonomy_reference_v1.md"
TAXONOMY_HUMAN_REVIEW = PACKAGE / "project_owner_taxonomy_human_review_v1.csv"
FIELD_SPEC = PACKAGE / "project_owner_redcap_field_specification_candidate_0.3.csv"
BRANCH_SPEC = PACKAGE / "project_owner_redcap_branching_specification_candidate_0.3.yaml"
EXPORT_SPEC = PACKAGE / "project_owner_redcap_expected_export_candidate_0.3.csv"
FORMATTING_AUDIT = PACKAGE / "project_owner_redcap_formatting_audit_candidate_0.3.csv"

HEADERS = [
    "Variable / Field Name",
    "Form Name",
    "Section Header",
    "Field Type",
    "Field Label",
    "Choices, Calculations, OR Slider Labels",
    "Field Note",
    "Text Validation Type OR Show Slider Number",
    "Text Validation Min",
    "Text Validation Max",
    "Identifier?",
    "Branching Logic (Show field only if...)",
    "Required Field?",
    "Custom Alignment",
    "Question Number (surveys only)",
    "Matrix Group Name",
    "Matrix Ranking?",
    "Field Annotation",
]
FORMS = ("owner_consent", "project_review")
HIDDEN_ADMIN = "@HIDDEN-SURVEY @READONLY"
READONLY_SURVEY = "@READONLY-SURVEY"
DOMAIN_SLOTS = 4
PURPOSE_SLOTS = 2
TAG_SLOTS = 2
TAG_SUMMARY_LABELS = (
    "Demographic disparities / equity",
    "COVID-19 & Pandemic",
)
MENU_COUNTS = {"domain": 11, "purpose": 7, "tag": 2}
PROPOSED_DISPLAY_COUNTS = {"domain": 12, "purpose": 8, "tag": 2}
LAYER_NAMES = {
    "domain": "Layer A -- domain",
    "purpose": "Layer C -- purpose",
    "tag": "Cross-cutting tag",
}
FROZEN_COLUMNS = {
    "domain": "substantive_domains",
    "purpose": "analytical_purpose",
    "tag": "cross_cutting_tags",
}
SLOT_CAPACITY = {"domain": DOMAIN_SLOTS, "purpose": PURPOSE_SLOTS, "tag": TAG_SLOTS}
UNCLEAR_LABEL = "Unclear from Register Entry"
PROPOSED_ONLY_DEFINITIONS = {
    ("domain", UNCLEAR_LABEL): (
        "Use only where the project title and dataset field together do not provide enough "
        "evidence to assign any substantive domain."
    ),
    ("purpose", UNCLEAR_LABEL): (
        "Use where the project title and datasets do not provide enough information to infer "
        "the analytical purpose."
    ),
}
AMBIGUITY_NOTES = {
    ("domain", "Data Infrastructure & Methodology"): (
        "Confirm that the wording distinguishes projects about data or methods from projects "
        "that merely use complex, linked or administrative data."
    ),
    ("purpose", "Outcome Tracking"): (
        "Review the boundary with Policy Evaluation / Impact Analysis, especially where an "
        "exposure is a named policy, programme or intervention."
    ),
    ("purpose", "Policy Evaluation / Impact Analysis"): (
        "Review the boundary with Outcome Tracking, retaining evaluation for a specific named "
        "policy, programme, regulation, intervention, scheme or institutional change."
    ),
    ("tag", "Demographic disparities / equity tag"): (
        "Confirm the boundary between projects centred on demographic or equality-group "
        "comparisons and projects that merely include demographic covariates or subgroup reporting."
    ),
}
UNCHANGED_MICRODEFINITIONS = {
    ("domain", "Labour Market & Employment"): "Work, employment, earnings, job quality, workforce dynamics, skills demand and labour-market transitions.",
    ("domain", "Education & Skills"): "Education, learning, training, skills formation and transitions through education systems and into work.",
    ("domain", "Crime & Justice"): "Crime, victimisation, public safety, policing, courts, sentencing, prisons, probation and justice outcomes.",
    ("domain", "Business & Productivity"): "Firms, business activity, innovation, productivity, entrepreneurship, trade, investment and business performance.",
    ("domain", "Poverty, Wealth & Living Standards"): "Material resources, poverty, wealth, debt, benefits, deprivation, cost of living and household income.",
    ("domain", "Housing & Planning"): "Housing, homelessness, tenure, residential conditions and mobility, neighbourhood change and planning systems.",
    ("domain", "Migration & Demographics"): "Population structure and change, migration, fertility, ageing and mortality as a demographic outcome.",
    ("domain", "Environment & Agriculture"): "Environment, climate, energy, agriculture, land use, pollution, decarbonisation and environmental impacts.",
    ("domain", "Public Finance & Taxation"): "Taxation, government revenue, public spending, fiscal transfers, tax reliefs and fiscal policy.",
    ("domain", "Data Infrastructure & Methodology"): "Data or methodology as the primary research object, rather than tools used for another question.",
    ("purpose", "Life-Course / Trajectory Analysis"): "Following people, households, firms or cases over time to understand trajectories, transitions or cumulative outcomes.",
    ("purpose", "Service Interaction / Systems Analysis"): "How people, cases or organisations access, use, move through or are processed by public services.",
    ("purpose", "Risk Prediction / Early Identification"): "Predicting risk or identifying at-risk people, groups or places for screening or early targeting.",
    ("purpose", "Methodological / Infrastructure Research"): "Developing, testing, validating or improving research methods, measures, linkage approaches, infrastructure or data assets.",
}
REVISED_MICRODEFINITIONS = {
    ("domain", "Health & Social Care"): "Health, illness, mental health, wellbeing, mortality as a health outcome, healthcare services and social care.",
    ("domain", UNCLEAR_LABEL): "The public title and datasets do not provide enough evidence to assign a substantive Research Domain.",
    ("purpose", "Descriptive Monitoring"): "Measuring and describing levels, distributions, patterns or trends across places, populations or time, without primarily testing an exposure–outcome relationship.",
    ("purpose", "Outcome Tracking"): "Linking a naturally occurring exposure, condition or event to a later outcome, where the exposure is not a deliberate policy or programme.",
    ("purpose", "Policy Evaluation / Impact Analysis"): "Assessing the implementation, effects or consequences of a specific named policy, programme, regulation or intervention.",
    ("purpose", UNCLEAR_LABEL): "The public title and datasets do not provide enough information to infer the Analytical Purpose.",
    ("tag", "Demographic disparities / equity tag"): "Comparisons across demographic or equality-relevant groups are central; socioeconomic inequality alone or routine subgroup breakdowns do not qualify.",
    ("tag", "COVID-19 & Pandemic"): "COVID-19 or pandemic conditions are a central research focus or lens, not merely the period covered by the data.",
}
MICRODEFINITIONS = UNCHANGED_MICRODEFINITIONS | REVISED_MICRODEFINITIONS
REFERENCE_BOUNDARY_CLAUSES = {
    ("domain", "Data Infrastructure & Methodology"): (
        "This applies where data infrastructure, linkage, measurement or methodology is itself "
        "the primary research object, not merely a tool used to answer another substantive question."
    ),
    ("tag", "Demographic disparities / equity tag"): (
        "Routine subgroup breakdowns do not qualify, and socioeconomic or deprivation-based "
        "inequality alone is insufficient unless comparison across demographic or "
        "equality-relevant groups is central."
    ),
    ("tag", "COVID-19 & Pandemic"): (
        "Research does not qualify merely because its data cover the pandemic period or because "
        "COVID-19 is mentioned incidentally."
    ),
    ("purpose", "Outcome Tracking"): (
        "This does not apply where the exposure is a deliberate named policy, programme, reform "
        "or intervention; that is Policy Evaluation / Impact Analysis."
    ),
}
REFERENCE_BOUNDARY_SOURCE_FIELDS = {
    ("domain", "Data Infrastructure & Methodology"): (
        "inclusion_rules",
        "exclusion_rules",
    ),
    ("purpose", "Outcome Tracking"): (
        "inclusion_rules",
        "exclusion_rules",
    ),
    ("tag", "Demographic disparities / equity tag"): (
        "inclusion_rules",
        "exclusion_rules",
    ),
    ("tag", "COVID-19 & Pandemic"): ("exclusion_rules",),
}
HIGH_RISK_BOUNDARY_NOTES = {
    ("domain", "Health & Social Care"): "Yes — explicitly includes mental health and retains mortality where health is the research object.",
    ("domain", "Migration & Demographics"): "Yes — retains mortality specifically as a demographic outcome.",
    ("domain", "Data Infrastructure & Methodology"): "Yes — makes data or methodology the primary research object, not merely a tool.",
    ("domain", UNCLEAR_LABEL): "Yes — states that no substantive Research Domain can be assigned from the public entry.",
    ("purpose", "Descriptive Monitoring"): "Yes — covers levels, distributions, patterns and trends without primarily testing an exposure–outcome relationship.",
    ("purpose", "Outcome Tracking"): "Yes — links a naturally occurring exposure to a later outcome and excludes deliberate policy or programme exposure.",
    ("purpose", "Policy Evaluation / Impact Analysis"): "Yes — retains assessment of implementation, effects or consequences of a specific named intervention.",
    ("purpose", UNCLEAR_LABEL): "Yes — states that the Analytical Purpose cannot be inferred from the public entry.",
    ("tag", "Demographic disparities / equity tag"): "Yes — requires central demographic or equality-relevant comparison and excludes socioeconomic inequality alone and routine subgroup breakdowns.",
    ("tag", "COVID-19 & Pandemic"): "Yes — requires pandemic relevance to be a central focus or lens, not merely the period covered by the data.",
}
HIGH_RISK_COMPRESSION_NOTES = {
    ("domain", "Health & Social Care"): "Human review focus: preserve the health-object boundary for mortality.",
    ("domain", "Migration & Demographics"): "Human review focus: preserve the demographic-outcome boundary for mortality.",
    ("domain", "Data Infrastructure & Methodology"): "Human review focus: preserve the primary-object versus merely-used-tools boundary.",
    ("domain", UNCLEAR_LABEL): "Human review focus: preserve Domain-specific insufficiency and avoid conflating it with Purpose.",
    ("purpose", "Descriptive Monitoring"): "Human review focus: preserve description across place, population or time and exclude primary exposure–outcome testing.",
    ("purpose", "Outcome Tracking"): "Human review focus: preserve naturally occurring exposure and exclude deliberate policy or programme exposure.",
    ("purpose", "Policy Evaluation / Impact Analysis"): "Human review focus: retain a specific policy, programme, regulation or intervention.",
    ("purpose", UNCLEAR_LABEL): "Human review focus: preserve Purpose-specific insufficiency and avoid conflating it with Domain.",
    ("tag", "Demographic disparities / equity tag"): "Human review focus: preserve central analytical focus rather than routine subgroup reporting.",
    ("tag", "COVID-19 & Pandemic"): "Human review focus: preserve central condition or lens rather than incidental mention.",
}
TAXONOMY_SHA256 = "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
FROZEN_OUTPUT_SHA256 = "6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299"

# Candidate 0.2 is a controlled historical candidate. These hashes are checked
# before generation and again by the candidate-0.3 validator/tests.
V02_HASHES = {
    "scripts/build_project_owner_redcap_candidate_0_2.py": "71ba2557a76454e608148f776c7241ef77ea7f08dd6892f4e78b6bff11c374fc",
    "scripts/validate_project_owner_redcap_candidate_0_2.py": "bac416e76762ba2d644b8cfbe22b1b8f87c0a5db081360ed8e5a0d423cdf0c4f",
    "tests/test_project_owner_redcap_candidate_0_2.py": "85c0761401eb48c2fd94e4c024ab86844fc02fc96feeee857bbc065bb80619e9",
    "tests/fixtures/project_owner_candidate_0_2_synthetic_submissions.yaml": "7afe706a04d8f9ad40a167a303e507f67276543d545bcd4e663ad17a4c339733",
    "preregistration/package/06_redcap/project_owner_redcap_data_dictionary_candidate_0.2.csv": "8225aec9afaae533151fa66e484b7361d8292777e9398b5a722fdc58b1fd52ec",
    "preregistration/package/06_redcap/project_owner_redcap_field_specification_candidate_0.2.csv": "97d73d402dd18f9b5312b997cb278fe90c3326d9a83a0838a2d6f0f265d7d014",
    "preregistration/package/06_redcap/project_owner_redcap_branching_specification_candidate_0.2.yaml": "6880407b8e47d06510724f170f0aa8822406c0f62011e1afac55738ff9e7740d",
    "preregistration/package/06_redcap/project_owner_redcap_expected_export_candidate_0.2.csv": "18b9fbe9ef0bbac565495b7699b8d855d04b884d500ef2d38009535326093420",
    "preregistration/package/06_redcap/live_qa/project_owner_synthetic_import_candidate_0.2.csv": "1a0c61835fca6866196905f274908dc2f333be699d25066dbf4e19cb1e7d5346",
    "preregistration/package/06_redcap/project_owner_redcap_candidate_0.2_README.md": "d0a3e29666e28cfa6990de6a48a91f060a4d0f04135243e60a6413f9e3616544",
    "preregistration/package/06_redcap/project_owner_live_qa_plan_candidate_0.2.md": "f8479149ec96d434be3832e030927bf9cf736532bbb2f9906610c7267ad4b7ad",
    "preregistration/package/06_redcap/project_owner_recruitment_materials_candidate_0.2.md": "50a891369e375088162c2d42a766b29db11386be79b250d7b071d667b8d9c3ef",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def field(
    name: str,
    form: str,
    field_type: str,
    label: str,
    *,
    section: str = "",
    choices: str = "",
    note: str = "",
    validation: str = "",
    branch: str = "",
    required: bool = False,
    annotation: str = "",
) -> dict[str, str]:
    row = {header: "" for header in HEADERS}
    row.update(
        {
            "Variable / Field Name": name,
            "Form Name": form,
            "Section Header": section,
            "Field Type": field_type,
            "Field Label": label,
            "Choices, Calculations, OR Slider Labels": choices,
            "Field Note": note,
            "Text Validation Type OR Show Slider Number": validation,
            "Branching Logic (Show field only if...)": branch,
            "Required Field?": "y" if required else "",
            "Field Annotation": annotation,
        }
    )
    return row


def _normalise(value: object) -> str:
    return " ".join(str(value or "").split())


def taxonomy_payload() -> dict[str, object]:
    return yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))


def taxonomy_groups() -> tuple[dict[str, list[dict[str, object]]], list[dict[str, object]]]:
    """Return substantive owner menus and proposed-only public-evidence fallbacks.

    The source dictionary uses ``relabelled v3.4`` and ``new v3.4`` for two
    current categories. Therefore current/effective-active selection is
    include_in_prompt=true, an active output layer, and a non-removed status.
    The exact source status is retained in the display source.
    """

    payload = taxonomy_payload()
    categories = payload["categories"]
    selected = [
        item
        for item in categories
        if item.get("include_in_prompt") is True
        and item.get("layer") in set(LAYER_NAMES.values())
        and not str(item.get("status", "")).lower().startswith("removed")
    ]
    selected_keys = [(item["layer"], item["label"]) for item in selected]
    if len(selected_keys) != len(set(selected_keys)):
        raise RuntimeError("duplicate active taxonomy (layer, label) key")
    fallbacks = [
        item
        for item in selected
        if item["label"] == UNCLEAR_LABEL
        and item["layer"] in {LAYER_NAMES["domain"], LAYER_NAMES["purpose"]}
    ]
    menu = [item for item in selected if item not in fallbacks]
    groups = {
        key: [item for item in menu if item["layer"] == layer]
        for key, layer in LAYER_NAMES.items()
    }
    counts = {key: len(items) for key, items in groups.items()}
    if counts != MENU_COUNTS:
        raise RuntimeError(f"owner taxonomy menu counts differ: {counts}")
    if len(fallbacks) != 2:
        raise RuntimeError("expected domain and purpose Unclear fallbacks")
    return groups, fallbacks


def display_key(item: dict[str, object]) -> tuple[str, str]:
    """Return the authoritative owner display identity for an entry."""

    return str(item["owner_layer"]), str(item["canonical_label"])


def all_display_entries(source: dict[str, object]) -> list[dict[str, object]]:
    return list(source["labels"]) + list(source["proposed_only_fallbacks"])


def taxonomy_display_index(
    source: dict[str, object] | None = None,
) -> dict[tuple[str, str], dict[str, object]]:
    """Index owner-facing definitions by (owner layer, canonical label)."""

    payload = source if source is not None else display_source()
    index: dict[tuple[str, str], dict[str, object]] = {}
    for item in all_display_entries(payload):
        key = display_key(item)
        if key in index:
            raise RuntimeError(f"duplicate taxonomy display key: {key}")
        index[key] = item
    return index


def imported_boundary_sources(
    key: tuple[str, str], taxonomy_item: dict[str, object]
) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for field_name in REFERENCE_BOUNDARY_SOURCE_FIELDS.get(key, ()):
        source_text = _normalise(taxonomy_item.get(field_name))
        if not source_text:
            raise RuntimeError(f"imported boundary source is empty: {key}:{field_name}")
        source_path = (
            f'{TAXONOMY.name}::categories[layer={json.dumps(str(taxonomy_item["layer"]))},'
            f'label={json.dumps(str(taxonomy_item["label"]))}].{field_name}'
        )
        sources.append(
            {
                "source_field": field_name,
                "source_path": source_path,
                "source_text": source_text,
            }
        )
    return sources


def production_cardinalities() -> dict[str, dict[str, object]]:
    with FROZEN_OUTPUT.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1308:
        raise RuntimeError(f"frozen production row count differs: {len(rows)}")
    result: dict[str, dict[str, object]] = {}
    for layer, column in FROZEN_COLUMNS.items():
        counts = [
            len([value for value in row[column].split(";") if value.strip()])
            for row in rows
        ]
        maximum = max(counts)
        if SLOT_CAPACITY[layer] < maximum:
            raise RuntimeError(
                f"{layer} display capacity {SLOT_CAPACITY[layer]} is below frozen maximum {maximum}"
            )
        result[layer] = {
            "column": column,
            "maximum": maximum,
            "rows_at_maximum": sum(value == maximum for value in counts),
            "distribution": dict(sorted(Counter(counts).items())),
        }
    return result


def display_source() -> dict[str, object]:
    payload = taxonomy_payload()
    groups, fallbacks = taxonomy_groups()
    entries: list[dict[str, object]] = []
    for layer, items in groups.items():
        for index, item in enumerate(items, 1):
            definition = _normalise(item["definition"])
            key = (layer, item["label"])
            reference_definition = owner_reference_definition(key, definition)
            boundary_sources = imported_boundary_sources(key, item)
            boundary_clause_imported = bool(boundary_sources)
            reference_provenance = (
                "frozen_definition_plus_imported_exclusion_boundary_clause"
                if boundary_clause_imported
                else "frozen_definition_verbatim_after_whitespace_normalisation"
            )
            entries.append(
                {
                    "code": index,
                    "canonical_label": item["label"],
                    "owner_layer": layer,
                    "source_layer": item["layer"],
                    "source_status": item["status"],
                    "effective_status": "active_current_prompt_category",
                    "include_in_prompt": True,
                    "include_in_owner_missing_menu": True,
                    "owner_microdefinition": MICRODEFINITIONS[key],
                    "owner_reference_definition": reference_definition,
                    "source_dictionary_version": payload["metadata"]["dictionary_version"],
                    "source_definition": definition,
                    "traceability": (
                        "Reference definition combines the frozen definition with an imported "
                        "exclusion/boundary clause approved in the 2026-07-23 addendum; inline "
                        "microdefinition is unchanged."
                        if boundary_clause_imported
                        else "Reference definition is verbatim after whitespace normalisation from "
                        "the frozen dictionary and Project Owner Review Questionnaire v1; inline "
                        "microdefinition was approved by the author on 2026-07-23."
                    ),
                    "wording_origin": reference_provenance,
                    "reference_definition_provenance": reference_provenance,
                    "imported_boundary_source_field": [
                        source["source_field"] for source in boundary_sources
                    ],
                    "imported_boundary_source_path": [
                        source["source_path"] for source in boundary_sources
                    ],
                    "imported_boundary_source_text": [
                        source["source_text"] for source in boundary_sources
                    ],
                    "imported_boundary_note": (
                        "Participant-reference wording imports an authoritative inclusion or "
                        "exclusion boundary; it is not a verbatim source definition."
                        if boundary_clause_imported
                        else ""
                    ),
                    "reused_or_condensed": (
                        "approved_microdefinition_with_frozen_definition_plus_imported_boundary_clause"
                        if boundary_clause_imported
                        else "approved_microdefinition_with_verbatim_source_reference"
                    ),
                    "microdefinition_material_simplification": True,
                    "reference_definition_material_simplification": False,
                    "reference_definition_boundary_clause_imported": boundary_clause_imported,
                    "review_status": TAXONOMY_REVIEW_STATUS,
                    "reviewer": TAXONOMY_REVIEWER,
                    "review_date": TAXONOMY_REVIEW_DATE,
                }
            )
    fallback_entries = []
    for item in fallbacks:
        layer = next(key for key, value in LAYER_NAMES.items() if value == item["layer"])
        key = (layer, item["label"])
        definition = _normalise(item["definition"])
        expected_definition = PROPOSED_ONLY_DEFINITIONS[key]
        if definition != expected_definition:
            raise RuntimeError(f"proposed-only definition drift: {key}")
        fallback_entries.append(
            {
                "canonical_label": item["label"],
                "owner_layer": layer,
                "source_layer": item["layer"],
                "source_status": item["status"],
                "effective_status": "active_current_prompt_proposed_only_fallback",
                "include_in_prompt": True,
                "include_in_owner_missing_menu": False,
                "include_as_proposed_label": True,
                "owner_microdefinition": MICRODEFINITIONS[key],
                "owner_reference_definition": expected_definition,
                "source_dictionary_version": payload["metadata"]["dictionary_version"],
                "source_definition": definition,
                "traceability": "Reference definition is the verbatim frozen public-evidence fallback; inline microdefinition was approved by the author on 2026-07-23 and is supported only for pre-populated production proposals.",
                "wording_origin": "frozen_definition_verbatim_after_whitespace_normalisation",
                "reference_definition_provenance": "frozen_definition_verbatim_after_whitespace_normalisation",
                "imported_boundary_source_field": [],
                "imported_boundary_source_path": [],
                "imported_boundary_source_text": [],
                "imported_boundary_note": "",
                "reused_or_condensed": "approved_microdefinition_with_verbatim_source_reference",
                "microdefinition_material_simplification": True,
                "reference_definition_material_simplification": False,
                "reference_definition_boundary_clause_imported": False,
                "review_status": TAXONOMY_REVIEW_STATUS,
                "reviewer": TAXONOMY_REVIEWER,
                "review_date": TAXONOMY_REVIEW_DATE,
            }
        )
    source = {
        "display_version": TAXONOMY_DISPLAY_VERSION,
        "status": "author_approved_display_unfrozen_live_qa_pending",
        "approval": {
            "review_status": TAXONOMY_REVIEW_STATUS,
            "reviewer": TAXONOMY_REVIEWER,
            "review_date": TAXONOMY_REVIEW_DATE,
            "scope": "owner microdefinitions and participant-reference definitions only; frozen taxonomy remains authoritative",
        },
        "source": {
            "path": str(TAXONOMY.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(TAXONOMY),
            "dictionary_version": payload["metadata"]["dictionary_version"],
            "ontology_version": payload["metadata"]["documents_ontology_version"],
        },
        "selection": {
            "include_in_prompt": True,
            "layers": list(LAYER_NAMES.values()),
            "effective_active_rule": "include_in_prompt is true; layer is current; source status does not begin 'removed'",
            "source_status_note": "Poverty, Wealth & Living Standards is 'relabelled v3.4'; Demographic disparities / equity tag is 'new v3.4'. Exact source statuses are retained.",
            "missing_menu_exclusion": "Unclear from Register Entry is a public-evidence fallback, not an owner-addable substantive label.",
            "menu_counts": MENU_COUNTS,
            "proposed_display_counts": PROPOSED_DISPLAY_COUNTS,
            "unique_key": ["owner_layer", "canonical_label"],
            "removed_linkage_unclear_excluded": True,
        },
        "labels": entries,
        "proposed_only_fallbacks": fallback_entries,
    }
    if set(taxonomy_display_index(source)) != {
        (layer, item["canonical_label"])
        for layer in LAYER_NAMES
        for item in entries + fallback_entries
        if item["owner_layer"] == layer
    }:
        raise RuntimeError("taxonomy display index differs from generated entries")
    return source


def menu_choices(entries: list[dict[str, object]]) -> str:
    return " | ".join(
        f"{item['code']}, {item['canonical_label']} — {item['owner_microdefinition']}"
        for item in entries
    )


def checkbox_trigger(name: str, entries: list[dict[str, object]]) -> str:
    return " or ".join(f"[{name}({item['code']})] = '1'" for item in entries)


def stable_unique_summary(values: Iterable[object]) -> str:
    """Return non-empty labels once each, preserving first-slot order."""

    seen: set[str] = set()
    labels: list[str] = []
    for value in values:
        label = str(value or "").strip()
        if label and label not in seen:
            labels.append(label)
            seen.add(label)
    return "; ".join(labels)


def proposed_label_summary(row: Mapping[str, object], prefix: str, capacity: int) -> str:
    return stable_unique_summary(
        row.get(f"prop_{prefix}{index:02d}_label", "")
        for index in range(1, capacity + 1)
    )


def proposed_tag_summary(row: Mapping[str, object]) -> str:
    values: list[str] = []
    for index, label in enumerate(TAG_SUMMARY_LABELS, 1):
        status = str(row.get(f"prop_t{index:02d}_status", "")).strip()
        display_status = {"1": "Applied", "0": "Not applied"}.get(status, "")
        values.append(f"{label} — {display_status}" if display_status else "")
    return "; ".join(value for value in values if value)


def populate_proposed_summaries(row: dict[str, object]) -> None:
    """Populate deterministic display-support summaries from proposal fields."""

    row["prop_domain_summary"] = proposed_label_summary(row, "d", DOMAIN_SLOTS)
    row["prop_purpose_summary"] = proposed_label_summary(row, "p", PURPOSE_SLOTS)
    row["prop_tag_summary"] = proposed_tag_summary(row)


def build_dictionary() -> tuple[list[dict[str, str]], dict[str, object]]:
    source = display_source()
    groups = {
        layer: [item for item in source["labels"] if item["owner_layer"] == layer]
        for layer in LAYER_NAMES
    }
    maxima = production_cardinalities()
    rows: list[dict[str, str]] = [
        field(
            "owner_id",
            "owner_consent",
            "text",
            "Pseudonymous owner identifier",
            section="Owner Consent",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "owner_intro",
            "owner_consent",
            "descriptive",
            "<strong>DEA Validation Study – Project Owner Review</strong><br><br>"
            "This personalised link was sent because you are named as a researcher on one or more projects "
            "in the UK Statistics Authority public register. Researchers directly involved in a project may "
            "have relevant context that is not visible in the public register entry.<br><br>"
            "Participation is voluntary. After confirming that you are the intended recipient and agreeing "
            "to take part, your personalised list of projects will be displayed. You may review one, some, "
            "all or none of the listed projects, in any order.<br><br>"
            "Please do not forward this personalised link and do not enter confidential, sensitive or "
            "otherwise non-public information. Each project review normally takes approximately 3–5 minutes. "
            "To pause an unfinished review, select <strong>Save & Return Later</strong> before leaving. "
            "You can then return using the same personalised link.",
        ),
        field(
            "participant_info_link",
            "owner_consent",
            "descriptive",
            "<strong>Participant Information PDF — synthetic-QA placeholder (not for production)</strong><br>"
            "[Attach or link the final approved, versioned Participant Information PDF here after approval.]",
        ),
        field(
            "participant_info_ver",
            "owner_consent",
            "text",
            "Participant-information version token",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "consent_form_ver",
            "owner_consent",
            "text",
            "Owner-consent form version",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "owner_instr_ver",
            "owner_consent",
            "text",
            "Project Owner REDCap candidate version",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "intended_recipient",
            "owner_consent",
            "radio",
            "I confirm that I am the researcher to whom this personalised link was sent.",
            choices="1, Yes | 0, No",
            required=True,
        ),
        field(
            "wrong_recipient_stop",
            "owner_consent",
            "descriptive",
            "This personalised link is intended only for the researcher to whom it was sent. "
            "Please do not complete or forward it. No project reviews will be displayed.",
            branch="[intended_recipient] = '0'",
        ),
        field(
            "owner_consent",
            "owner_consent",
            "radio",
            "I confirm that I have read and understood the Participant Information Sheet provided with this "
            "survey, have had the opportunity to ask questions, and agree to take part in the Project Owner Review.",
            choices="1, Yes, I agree to take part | 0, No, I do not wish to take part",
            branch="[intended_recipient] = '1'",
            required=True,
            note="A No response stops the survey and prevents Project Review from appearing in the Survey Queue.",
        ),
        field(
            "consent_decline_stop",
            "owner_consent",
            "descriptive",
            "Thank you for considering the study. You have chosen not to take part, and no project reviews "
            "will be displayed. This will have no adverse consequences.",
            branch="[owner_consent] = '0'",
        ),
        field(
            "ack_pref",
            "owner_consent",
            "radio",
            "Would you like to be acknowledged by name as a contributor to the project-owner validation exercise "
            "in resulting research outputs?<br><br>This is optional and separate from your decision to take part. "
            "If you select Yes, the research team will contact you separately to confirm how your name and "
            "affiliation should appear.",
            choices="1, Yes | 0, No | 2, Decide later",
            branch="[intended_recipient] = '1' and [owner_consent] = '1'",
        ),
    ]

    rows += [
        field(
            "assignment_id",
            "project_review",
            "text",
            "Review reference",
            section="Project Review",
            required=True,
            annotation=READONLY_SURVEY,
        ),
        field(
            "source_record_id",
            "project_review",
            "text",
            "Stable DEA source Record ID",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "official_project_id",
            "project_review",
            "text",
            "Official Project ID",
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "project_title",
            "project_review",
            "notes",
            "Public-register project title",
            required=True,
            annotation=READONLY_SURVEY,
        ),
        field(
            "datasets_used",
            "project_review",
            "notes",
            "Datasets listed in the public register",
            required=True,
            annotation=READONLY_SURVEY,
        ),
        field(
            "public_register_url",
            "project_review",
            "text",
            "Public register URL",
            annotation=READONLY_SURVEY,
        ),
        field(
            "source_pop_ver",
            "project_review",
            "text",
            "Frozen source-population version",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "production_ver",
            "project_review",
            "text",
            "Frozen production-classification release",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "taxonomy_ver",
            "project_review",
            "text",
            "Frozen taxonomy/dictionary version",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "proposal_output_sha256",
            "project_review",
            "text",
            "Proposal-output SHA-256 provenance",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "review_instr_ver",
            "project_review",
            "text",
            "Project Review instrument version",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "taxonomy_display_ver",
            "project_review",
            "text",
            "Owner-facing taxonomy display version",
            required=True,
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "prop_domain_summary",
            "project_review",
            "notes",
            "Deterministic proposed Research Domain summary",
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "prop_purpose_summary",
            "project_review",
            "notes",
            "Deterministic proposed Analytical Purpose summary",
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "prop_tag_summary",
            "project_review",
            "notes",
            "Deterministic proposed cross-cutting tag-status summary",
            annotation=HIDDEN_ADMIN,
        ),
        field(
            "po_classification_overview",
            "project_review",
            "descriptive",
            "<strong>Classification overview</strong><br>"
            "The proposed classifications are summarised below for context. Please judge each item "
            "independently in the sections that follow.<br><br>"
            "<strong>Research Domains</strong><br>[prop_domain_summary]<br><br>"
            "<strong>Analytical Purposes</strong><br>[prop_purpose_summary]<br><br>"
            "<strong>Cross-cutting tags</strong><br>[prop_tag_summary]",
        ),
        field(
            "po_intro",
            "project_review",
            "descriptive",
            "This review shows a short definition beside each proposed classification. "
            "You do not need to learn the full classification framework before answering. "
            "A concise reference to all classifications is also available. "
            "You may complete all, some or none of your listed project reviews, in any order. "
            "To pause an unfinished review, select <strong>Save & Return Later</strong> before leaving. "
            "You can then return using the same personalised link.<br><br>"
            "<strong>Research Domains</strong><br>"
            "Research Domains describe the main subjects of the project. A project may have several "
            "Research Domains where each is substantively part of the research. Judge each proposed "
            "Domain independently; the Domains are not ranked.<br><br>"
            "<strong>Analytical Purposes</strong><br>"
            "Analytical Purposes describe what the project is trying to do analytically. More than one "
            "may apply, but the framework assigns no more than two to a project. Judge each proposed "
            "Purpose independently against the project's main analytical aims.<br><br>"
            "<strong>Cross-cutting tags</strong><br>"
            "The framework has two cross-cutting tags. Either, both or neither may apply. They indicate "
            "whether demographic or equality-group disparities, or COVID-19 and pandemic conditions, "
            "are a central focus or analytical lens rather than merely being mentioned.",
        ),
        field(
            "po_privacy",
            "project_review",
            "descriptive",
            "<strong>Important</strong><br>"
            "Do not enter confidential, sensitive, restricted, personally identifying or otherwise "
            "non-public information. Describe any relevant context only at a general level.",
        ),
        field(
            "po_taxonomy_ref",
            "project_review",
            "descriptive",
            "<strong>Optional classification reference — synthetic-QA placeholder (not for production)</strong><br>"
            "[Attach or link the final formatted owner-facing taxonomy reference PDF here after "
            "participant-document alignment.]",
        ),
    ]

    slot_plan = (("d", "domain", DOMAIN_SLOTS), ("p", "purpose", PURPOSE_SLOTS))
    for prefix, layer, capacity in slot_plan:
        section = {
            "domain": "Proposed Research Domains",
            "purpose": "Proposed Analytical Purposes",
            "tag": "Proposed cross-cutting tags",
        }[layer]
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            prop_label = f"prop_{stem}_label"
            prop_def = f"prop_{stem}_def"
            visible = f"[{prop_label}] <> ''"
            fit = f"po_{stem}_fit"
            visibility = f"po_{stem}_vis"
            visibility_question = (
                "Is the basis for this classification visible in the public project title and datasets listed above?"
            )
            rows += [
                field(
                    prop_label,
                    "project_review",
                    "text",
                    f"Pre-populated proposed {layer} label {index}",
                    section=section if index == 1 else "",
                    annotation=HIDDEN_ADMIN,
                ),
                field(
                    prop_def,
                    "project_review",
                    "notes",
                    f"Pre-populated owner-facing definition for proposed {layer} label {index}",
                    annotation=HIDDEN_ADMIN,
                ),
                field(
                    f"po_{stem}_display",
                    "project_review",
                    "descriptive",
                    f"<strong>[{prop_label}]</strong><br>[{prop_def}]",
                    branch=visible,
                ),
                field(
                    fit,
                    "project_review",
                    "radio",
                    f"Does [{prop_label}] describe the actual project?",
                    choices="1, Fits | 2, Does not fit | 3, Unsure",
                    branch=visible,
                    required=True,
                ),
                field(
                    f"po_{stem}_correct_explain",
                    "project_review",
                    "notes",
                    "Please briefly explain why this proposed "
                    f"{'Research Domain' if layer == 'domain' else 'Analytical Purpose'} does not fit "
                    "the actual project.",
                    branch=f"[{fit}] = '2'",
                    required=True,
                ),
                field(
                    visibility,
                    "project_review",
                    "radio",
                    visibility_question,
                    choices="2, Clearly visible | 1, Partly visible | 0, Not visible | 3, Unsure",
                    branch=visible,
                    required=True,
                ),
                field(
                    f"po_{stem}_vis_explain",
                    "project_review",
                    "notes",
                    "Optional: Please briefly explain what about this "
                    f"{'Research Domain' if layer == 'domain' else 'Analytical Purpose'} is only partly "
                    "visible, not visible or unclear in the public project title and listed datasets.",
                    branch=(
                        f"[{visibility}] = '1' or [{visibility}] = '0' or [{visibility}] = '3'"
                    ),
                ),
            ]

    for index in range(1, TAG_SLOTS + 1):
        stem = f"t{index:02d}"
        prop_label = f"prop_{stem}_label"
        prop_def = f"prop_{stem}_def"
        proposed_status = f"prop_{stem}_status"
        correctness = f"po_{stem}_correct"
        visibility = f"po_{stem}_vis"
        rows += [
            field(
                prop_label,
                "project_review",
                "text",
                f"Pre-populated canonical tag label {index}",
                section="Cross-cutting tag status review" if index == 1 else "",
                required=True,
                annotation=HIDDEN_ADMIN,
            ),
            field(
                prop_def,
                "project_review",
                "notes",
                f"Pre-populated owner-facing definition for canonical tag {index}",
                required=True,
                annotation=HIDDEN_ADMIN,
            ),
            field(
                f"po_{stem}_display",
                "project_review",
                "descriptive",
                f"<strong>[{prop_label}]</strong><br>[{prop_def}]",
            ),
            field(
                proposed_status,
                "project_review",
                "radio",
                f"Proposed status for [{prop_label}]",
                choices="1, Applied | 0, Not applied",
                required=True,
                annotation=READONLY_SURVEY,
            ),
            field(
                correctness,
                "project_review",
                "radio",
                f"Is the proposed status for [{prop_label}] correct for the actual project?",
                choices="1, Yes | 0, No | 2, Unsure",
                required=True,
            ),
            field(
                f"po_{stem}_correct_explain",
                "project_review",
                "notes",
                "Please briefly explain why the proposed status for the "
                f"{'Demographic disparities / equity tag' if index == 1 else 'COVID-19 & Pandemic tag'} "
                "does not fit the actual project.",
                branch=f"[{correctness}] = '0'",
                required=True,
            ),
            field(
                visibility,
                "project_review",
                "radio",
                "Is the basis for this tag status visible in the public project title and datasets "
                "listed above?",
                choices="2, Clearly visible | 1, Partly visible | 0, Not visible | 3, Unsure",
                required=True,
            ),
            field(
                f"po_{stem}_vis_explain",
                "project_review",
                "notes",
                "Optional: Please briefly explain what about this tag status is only partly visible, "
                "not visible or unclear in the public project title and listed datasets.",
                branch=(
                    f"[{visibility}] = '1' or [{visibility}] = '0' or [{visibility}] = '3'"
                ),
            ),
        ]

    missing_config = (
        (
            "domain",
            "po_miss_domain",
            "Should any additional Research Domain have been assigned?",
            "po_miss_domains",
            "Which additional Research Domain label or labels should have been assigned?",
            "po_miss_domain_basis",
        ),
        (
            "purpose",
            "po_miss_purpose",
            "Should any additional Analytical Purpose have been assigned?",
            "po_miss_purposes",
            "Which additional Analytical Purpose label or labels should have been assigned?",
            "po_miss_purpose_basis",
        ),
        (
            "tag",
            "po_miss_tag",
            "Should either cross-cutting tag have been assigned or applied differently?",
            "po_miss_tags",
            "Which cross-cutting tag or tags should have been assigned or applied differently?",
            "po_miss_tag_basis",
        ),
    )
    for index, (layer, gateway, gateway_label, menu, menu_label, basis) in enumerate(missing_config):
        entries = groups[layer]
        dimension_rows = [
            field(
                gateway,
                "project_review",
                "radio",
                gateway_label,
                section="Potential missing classifications" if index == 0 else "",
                choices="1, Yes | 0, No | 2, Unsure",
                required=True,
            ),
        ]
        if layer == "purpose":
            dimension_rows.append(
                field(
                    "po_miss_purpose_guidance",
                    "project_review",
                    "descriptive",
                    "The framework assigns a maximum of two Analytical Purposes to each project. "
                    "Select only the most important missing purpose or purposes, taking account of "
                    "any proposed purposes that you judged to fit. The resulting classification "
                    "should contain no more than two purposes in total.",
                    branch="[po_miss_purpose] = '1'",
                )
            )
        dimension_rows.extend(
            [
            field(
                menu,
                "project_review",
                "checkbox",
                menu_label,
                choices=menu_choices(entries),
                branch=f"[{gateway}] = '1'",
                required=True,
                annotation="@MAXCHECKED=2" if layer == "purpose" else "",
            ),
            field(
                basis,
                "project_review",
                "notes",
                "Optional: Please briefly explain why the selected label or labels should be included.",
                branch=checkbox_trigger(menu, entries),
            ),
            ]
        )
        rows += dimension_rows

    rows += [
        field(
            "po_sufficiency",
            "project_review",
            "radio",
            "Overall, does the public register entry provide enough information for someone external to classify the project correctly?",
            section="Overall assessment",
            choices="1, Sufficient | 2, Partial | 3, Insufficient",
            required=True,
        ),
        field(
            "po_suff_explain",
            "project_review",
            "notes",
            "Optional: Please briefly explain what information is missing or unclear in the public entry.",
            branch="[po_sufficiency] = '2' or [po_sufficiency] = '3'",
        ),
        field(
            "po_taxonomy_fit",
            "project_review",
            "radio",
            "Thinking about the actual project, how well do the available classification categories cover it?",
            choices="1, Fit | 2, Partial Fit | 3, No Fit",
            required=True,
        ),
        field(
            "po_tax_issue",
            "project_review",
            "checkbox",
            "What type of taxonomy problem applies?",
            choices=(
                "1, No suitable category exists in the framework | "
                "2, Ambiguous or overlapping category boundaries | "
                "5, Other taxonomy problem"
            ),
            note=(
                "This question concerns the available classification framework itself. If an "
                "existing category fits but was omitted from the proposed classification, report "
                "it in the missing-classification section instead."
            ),
            branch="[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'",
            required=True,
        ),
        field(
            "po_tax_explain",
            "project_review",
            "notes",
            "Optional: Please briefly explain the taxonomy-fit problem. If you selected "
            "'Other taxonomy problem', describe it here.",
            branch="[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'",
        ),
        field(
            "po_nonpublic",
            "project_review",
            "radio",
            "Did any of your answers rely on relevant knowledge about the project that is not visible in the "
            "public register entry?",
            choices="0, No | 1, Yes | 2, Unsure",
            required=True,
        ),
        field(
            "po_nonpublic_note",
            "project_review",
            "notes",
            "Optional: At a general level, please describe the relevant project knowledge that was not "
            "visible in the public project title and listed datasets.",
            branch="[po_nonpublic] = '1' or [po_nonpublic] = '2'",
        ),
        field(
            "po_other_comment",
            "project_review",
            "notes",
            "Optional final comments about the proposed classifications, public register entry, or taxonomy",
            section="Final comments and quotation permission",
        ),
        field(
            "po_quote_permission",
            "project_review",
            "radio",
            "May the study use a short anonymised quotation from your free-text comments in research outputs, "
            "provided that it does not identify you or your project and does not disclose non-public information?",
            choices="1, Yes | 0, No | 2, Please contact me before using a quotation",
            note="This response-specific permission is optional and does not affect whether the review is analytically complete.",
        ),
        field(
            "po_final_warning",
            "project_review",
            "descriptive",
            "<strong>Important</strong><br>Do not include confidential, sensitive, restricted, personally "
            "identifying or otherwise non-public information in comments.<br><br>"
            "You may request withdrawal of this submitted review before the deadline stated in the "
            "Participant Information Sheet by contacting the study team and quoting the Review reference "
            "shown above.",
        ),
    ]

    counts = Counter(row["Form Name"] for row in rows)
    meta = {
        "field_counts": dict(counts),
        "total_fields": len(rows),
        "production_cardinalities": maxima,
        "taxonomy_menu_counts": MENU_COUNTS,
    }
    return rows, meta


def microdefinition_word_count(value: str) -> int:
    return len(value.split())


def reference_definition_word_count(value: str) -> int:
    return len(value.split())


def owner_reference_definition(key: tuple[str, str], source_definition: str) -> str:
    clause = REFERENCE_BOUNDARY_CLAUSES.get(key)
    return f"{source_definition} {clause}" if clause else source_definition


def taxonomy_human_review_rows(
    source: dict[str, object],
) -> list[dict[str, object]]:
    display_entries = all_display_entries(source)
    display_keys = {display_key(item) for item in display_entries}
    if display_keys != set(MICRODEFINITIONS):
        missing = sorted(display_keys - set(MICRODEFINITIONS))
        extra = sorted(set(MICRODEFINITIONS) - display_keys)
        raise RuntimeError(f"microdefinition key mismatch: missing={missing}; extra={extra}")
    review_rows: list[dict[str, object]] = []
    for item in display_entries:
        key = display_key(item)
        microdefinition = MICRODEFINITIONS[key]
        if key in HIGH_RISK_BOUNDARY_NOTES:
            boundary_note = HIGH_RISK_BOUNDARY_NOTES[key]
        elif key[0] == "domain":
            boundary_note = "Yes — central research object retained."
        elif key[0] == "purpose":
            boundary_note = "Yes — central analytical purpose retained."
        else:
            boundary_note = "Yes — central cross-cutting lens retained."
        compression_note = HIGH_RISK_COMPRESSION_NOTES.get(
            key,
            "Examples and extended enumerations removed; central meaning retained.",
        )
        review_rows.append(
            {
                "layer": item["owner_layer"],
                "canonical_label": item["canonical_label"],
                "current_short_definition": item["source_definition"],
                "candidate_reference_definition": item["owner_reference_definition"],
                "reference_definition_word_count": reference_definition_word_count(
                    item["owner_reference_definition"]
                ),
                "reference_definition_character_count": len(
                    item["owner_reference_definition"]
                ),
                "candidate_microdefinition": microdefinition,
                "microdefinition_word_count": microdefinition_word_count(microdefinition),
                "microdefinition_character_count": len(microdefinition),
                "source_taxonomy_definition": item["source_definition"],
                "source_dictionary_version": item["source_dictionary_version"],
                "wording_origin": item["wording_origin"],
                "reference_definition_provenance": item[
                    "reference_definition_provenance"
                ],
                "imported_boundary_source_field": json.dumps(
                    item["imported_boundary_source_field"], ensure_ascii=False
                ),
                "imported_boundary_source_path": json.dumps(
                    item["imported_boundary_source_path"], ensure_ascii=False
                ),
                "imported_boundary_source_text": json.dumps(
                    item["imported_boundary_source_text"], ensure_ascii=False
                ),
                "imported_boundary_note": item["imported_boundary_note"],
                "reused_or_condensed": item["reused_or_condensed"],
                "material_simplification_note": (
                    "Approved inline microdefinition is unchanged; participant-reference definition "
                    "combines the frozen definition with an imported exclusion/boundary clause."
                    if key in REFERENCE_BOUNDARY_CLAUSES
                    else "Approved inline microdefinition is a display condensation; frozen source "
                    "and participant-reference definition remain unchanged."
                ),
                "essential_boundary_preserved": boundary_note,
                "compression_note": compression_note,
                "possible_ambiguity": AMBIGUITY_NOTES.get(key, ""),
                "review_status": TAXONOMY_REVIEW_STATUS,
                "reviewer": TAXONOMY_REVIEWER,
                "review_date": TAXONOMY_REVIEW_DATE,
                "reviewer_note": "",
            }
        )
    return review_rows


def build_taxonomy_human_review(source: dict[str, object] | None = None) -> None:
    display = source if source is not None else yaml.safe_load(
        TAXONOMY_DISPLAY.read_text(encoding="utf-8")
    )
    write_csv(
        TAXONOMY_HUMAN_REVIEW,
        [
            "layer",
            "canonical_label",
            "current_short_definition",
            "candidate_reference_definition",
            "reference_definition_word_count",
            "reference_definition_character_count",
            "candidate_microdefinition",
            "microdefinition_word_count",
            "microdefinition_character_count",
            "source_taxonomy_definition",
            "source_dictionary_version",
            "wording_origin",
            "reference_definition_provenance",
            "imported_boundary_source_field",
            "imported_boundary_source_path",
            "imported_boundary_source_text",
            "imported_boundary_note",
            "reused_or_condensed",
            "material_simplification_note",
            "essential_boundary_preserved",
            "compression_note",
            "possible_ambiguity",
            "review_status",
            "reviewer",
            "review_date",
            "reviewer_note",
        ],
        taxonomy_human_review_rows(display),
    )


def build_taxonomy_outputs() -> None:
    source = display_source()
    TAXONOMY_DISPLAY.write_text(
        yaml.safe_dump(source, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    sections = []
    names = {
        "domain": "Research Domains",
        "purpose": "Analytical Purposes",
        "tag": "Cross-cutting tags",
    }
    for layer in ("domain", "purpose", "tag"):
        lines = [f"## {names[layer]}", ""]
        for item in source["labels"]:
            if item["owner_layer"] == layer:
                lines.append(
                    f"- **{item['canonical_label']}** — {item['owner_reference_definition']}"
                )
        sections.append("\n".join(lines))
    fallback_lines = [
        "## About ‘Unclear from Register Entry’",
        "",
        "This label may appear where the classification judged that the public project title "
        "and listed datasets did not provide enough information to assign a substantive "
        "Research Domain or infer an Analytical Purpose. Your view on whether that judgement "
        "was reasonable is itself useful evidence for the validation study.",
        "",
        "The framework’s own definitions are:",
        "",
    ]
    for item in source["proposed_only_fallbacks"]:
        layer_name = "Research Domain" if item["owner_layer"] == "domain" else "Analytical Purpose"
        fallback_lines.append(
            f"- **{layer_name} — {item['canonical_label']}** — {item['owner_reference_definition']}"
        )
    sections.append("\n".join(fallback_lines))
    TAXONOMY_REFERENCE.write_text(
        "# Project Owner classification reference\n\n"
        f"Document version: {TAXONOMY_REFERENCE_VERSION}  \n"
        f"Date: {TAXONOMY_REFERENCE_DATE}\n\n"
        "## How to use this guide\n\n"
        "Use this guide when deciding whether each proposed classification fits the actual "
        "project and how clearly its basis is visible in the public project title and listed "
        "datasets. The short definitions summarise how the framework uses each category.\n\n"
        "A project may be assigned more than one Research Domain where each is substantively "
        "part of the research; the Domains are not ranked.\n\n"
        "The framework assigns no more than two Analytical Purposes to a project. "
        "The purposes should describe its main analytical aims. More than one Analytical "
        "Purpose may apply.\n\n"
        + "\n\n".join(sections)
        + "\n\n## Important distinctions\n\n"
        "- **Health and demographic mortality:** Health & Social Care covers mortality where health is the research object; Migration & Demographics covers mortality as a demographic outcome.\n"
        "- **Description, outcomes and evaluation:** Descriptive Monitoring measures or describes levels, distributions, patterns or trends without primarily testing an exposure–outcome relationship. Outcome Tracking links a naturally occurring exposure, condition or event to a later outcome and excludes deliberate policy or programme exposure. Policy Evaluation / Impact Analysis assesses a specific named policy, programme, regulation or intervention.\n",
        encoding="utf-8",
    )
    build_taxonomy_human_review(source)


def build_specs(rows: list[dict[str, str]], meta: dict[str, object]) -> None:
    response_prefixes = ("intended_recipient", "owner_consent", "ack_pref", "po_")
    prepop = {
        "owner_id",
        "participant_info_ver",
        "consent_form_ver",
        "owner_instr_ver",
        "assignment_id",
        "source_record_id",
        "official_project_id",
        "project_title",
        "datasets_used",
        "public_register_url",
        "source_pop_ver",
        "production_ver",
        "taxonomy_ver",
        "proposal_output_sha256",
        "review_instr_ver",
        "taxonomy_display_ver",
    } | {
        row["Variable / Field Name"]
        for row in rows
        if row["Variable / Field Name"].startswith("prop_")
    }
    field_rows = []
    for row in rows:
        name = row["Variable / Field Name"]
        if re.fullmatch(r"po_[dpt]\d{2}_vis", name):
            notes = (
                "Required proposed-label public-evidence response: 2 Clearly visible; "
                "1 Partly visible; 0 Not visible; 3 Unsure."
            )
        elif re.fullmatch(r"po_[dpt]\d{2}_correct_explain", name):
            notes = (
                "Required only when the block correctness/verdict is the explicit negative value; "
                "records actual-project classification disagreement. Unsure shows no explanation field."
            )
        elif re.fullmatch(r"po_[dpt]\d{2}_vis_explain", name):
            notes = (
                "Optional enrichment shown when final visibility is Partly visible/Not visible/Unsure; "
                "blank means not provided, not absence of an evidence limitation. Retained hidden values "
                "are ignored when final visibility is Clearly visible."
            )
        elif re.fullmatch(r"prop_t\d{2}_status", name):
            notes = "Pre-populated Applied/Not applied status; always participant-visible and survey-read-only."
        elif name in {"prop_domain_summary", "prop_purpose_summary", "prop_tag_summary"}:
            notes = (
                "Pre-populated deterministic display-support summary; survey-hidden, not participant-editable, "
                "not an analytical outcome and excluded from analytical completion."
            )
        elif row["Field Type"] == "descriptive":
            notes = "Generated display/wording field"
        else:
            notes = "REDCap field"
        construct = ""
        analytical_completion = "not_applicable"
        requiredness_rationale = ""
        analysis_applicability = "always_if_row_and_field_are_applicable"
        if row["Field Type"] == "notes" and name.startswith("po_"):
            if re.fullmatch(r"po_[dpt]\d{2}_correct_explain", name):
                construct = "actual_project_disagreement_explanation"
                analytical_completion = "required_when_displayed_for_explicit_disagreement"
                requiredness_rationale = "Explicit disagreement needs adjudicable context; Unsure does not display this field."
            elif re.fullmatch(r"po_[dpt]\d{2}_vis_explain", name):
                construct = "public_entry_visibility_enrichment"
                analytical_completion = "excluded_optional_enrichment"
                requiredness_rationale = "The required four-level visibility rating captures the primary evidence judgement."
            elif name in {"po_miss_domain_basis", "po_miss_purpose_basis", "po_miss_tag_basis"}:
                construct = "missing_classification_enrichment"
                analytical_completion = "excluded_optional_enrichment"
                requiredness_rationale = "The required gateway and checkbox selection capture the omission."
            elif name == "po_suff_explain":
                construct = "public_entry_sufficiency_enrichment"
                analytical_completion = "excluded_optional_enrichment"
                requiredness_rationale = "The required sufficiency rating captures the primary judgement."
            elif name == "po_nonpublic_note":
                construct = "project_knowledge_enrichment"
                analytical_completion = "excluded_optional_enrichment"
                requiredness_rationale = "The required project-knowledge gateway captures reliance on non-public context."
            elif name == "po_tax_explain":
                construct = "taxonomy_fit_enrichment"
                analytical_completion = "excluded_optional_enrichment"
                requiredness_rationale = "Taxonomy fit and required issue type capture the structured taxonomy diagnosis."
            elif name == "po_other_comment":
                construct = "final_comment"
                analytical_completion = "excluded_optional_enrichment"
                requiredness_rationale = "Optional final comment."
        if re.fullmatch(r"po_[dp]\d{2}_correct_explain", name):
            analysis_applicability = "only_if_final_fit_is_2_does_not_fit"
        elif re.fullmatch(r"po_t\d{2}_correct_explain", name):
            analysis_applicability = "only_if_final_correctness_is_0_no"
        elif re.fullmatch(r"po_[dpt]\d{2}_vis_explain", name):
            analysis_applicability = "only_if_final_visibility_is_1_0_or_3"
        elif name in {"po_miss_domains", "po_miss_purposes", "po_miss_tags"}:
            analysis_applicability = "only_if_final_missing_gateway_is_1_yes"
        elif name in {"po_miss_domain_basis", "po_miss_purpose_basis", "po_miss_tag_basis"}:
            analysis_applicability = "only_if_final_missing_gateway_is_yes_and_a_label_is_selected"
        elif name == "po_suff_explain":
            analysis_applicability = "only_if_final_sufficiency_is_2_partial_or_3_insufficient"
        elif name in {"po_tax_issue", "po_tax_explain"}:
            analysis_applicability = "only_if_final_taxonomy_fit_is_2_partial_or_3_no_fit"
        elif name == "po_nonpublic_note":
            analysis_applicability = "only_if_final_project_knowledge_is_1_yes_or_2_unsure"
        field_rows.append(
            {
                "variable": name,
                "form": row["Form Name"],
                "field_type": row["Field Type"],
                "scope": "owner_row" if row["Form Name"] == "owner_consent" else "project_review_repeat_row",
                "prepopulated": "yes" if name in prepop else "no",
                "participant_response": "yes"
                if name in {"intended_recipient", "owner_consent", "ack_pref"}
                or (name.startswith("po_") and row["Field Type"] != "descriptive")
                else "no",
                "branching": row["Branching Logic (Show field only if...)"],
                "required": row["Required Field?"],
                "annotation": row["Field Annotation"],
                "construct": construct,
                "analytical_completion": analytical_completion,
                "requiredness_rationale": requiredness_rationale,
                "analysis_applicability": analysis_applicability,
                "notes": notes,
            }
        )
    write_csv(
        FIELD_SPEC,
        [
            "variable",
            "form",
            "field_type",
            "scope",
            "prepopulated",
            "participant_response",
            "branching",
            "required",
            "annotation",
            "construct",
            "analytical_completion",
            "requiredness_rationale",
            "analysis_applicability",
            "notes",
        ],
        field_rows,
    )

    branch = {
        "version": VERSION,
        "status": STATUS,
        "project": {
            "pid": 9149,
            "title": "DEA Validation Study – Project Owner Review",
            "connection_performed": False,
            "classic_non_longitudinal": True,
            "record_id": "owner_id",
        },
        "forms": list(FORMS),
        "field_counts": meta["field_counts"],
        "repeating_instruments": ["project_review"],
        "repeat_custom_label": "[assignment_id] — [project_title]",
        "repeat_survey_button_enabled": False,
        "survey_queue": {
            "visible": True,
            "introduction_html": (
                "<strong>Project Owner Review</strong><br>"
                "Please begin by completing <strong>Participant Information and Consent</strong> below. "
                "If you agree to take part, your available project reviews will then appear in this list. "
                "You may complete all, some or none, in any order. To pause an unfinished review, use "
                "<strong>Save & Return Later</strong> before leaving. You can return using the same "
                "personalised link. Please do not forward this link."
            ),
            "owner_consent": {
                "active": True,
                "condition": "[owner_id] <> ''",
                "auto_start": True,
            },
            "project_review": {
                "active": True,
                "condition": (
                    "[owner_consent_complete] = '2' and "
                    "[owner_consent] = '1' and [intended_recipient] = '1'"
                ),
                "auto_start": False,
            },
        },
        "project_review_survey_settings_required": {
            "repository_documented_not_live_verified": True,
            "save_and_return_later_enabled": True,
            "return_without_separate_return_code_enabled": True,
            "completed_response_modification_enabled": False,
            "automatically_continue_to_next_survey_enabled": False,
            "redirect_url": "",
            "participant_repeat_the_survey_enabled": False,
            "security_note": (
                "Possession of the personalised link permits access to an unfinished review; participants "
                "must not forward it, and direct contact identifiers are absent from the REDCap response project."
            ),
        },
        "stop_actions_manual_after_import": {
            "intended_recipient": "No",
            "owner_consent": "No",
            "offline_equivalent": "Downstream consent content is branched on affirmative answers; queue logic suppresses Project Review.",
            "minimum_external_disposition": "No automatic deletion, retention, reminder-suppression or contact-table action is encoded or claimed; follow the separately approved recruitment-administration process.",
        },
        "production_cardinalities": meta["production_cardinalities"],
        "slot_capacity": SLOT_CAPACITY,
        "classification_overview": {
            "display_field": "po_classification_overview",
            "summary_fields": [
                "prop_domain_summary",
                "prop_purpose_summary",
                "prop_tag_summary",
            ],
            "display_support_only": True,
            "participant_editable": False,
            "analytical_completion_requirement": False,
            "domain_and_purpose_order": "first populated proposal-slot order with blanks omitted and duplicates removed",
            "tag_order": list(TAG_SUMMARY_LABELS),
        },
        "taxonomy_menu_counts": MENU_COUNTS,
        "proposed_slot_visibility": {
            "domain_and_purpose_question": (
                "Is the basis for this classification visible in the public project title and datasets "
                "listed above?"
            ),
            "tag_question": (
                "Is the basis for this tag status visible in the public project title and datasets "
                "listed above?"
            ),
            "choices": {
                "2": "Clearly visible",
                "1": "Partly visible",
                "0": "Not visible",
                "3": "Unsure",
            },
            "explanation_required_when": {
                "domain_or_purpose_verdict": ["2: Does not fit"],
                "tag_correctness": ["0: No"],
            },
            "optional_visibility_explanation_shown_when": [
                "1: Partly visible", "0: Not visible", "3: Unsure"
            ],
            "unsure_correctness_explanation_displayed": False,
        },
        "tag_reviews": {
            "always_review_both": True,
            "canonical_order": [item["canonical_label"] for item in display_source()["labels"] if item["owner_layer"] == "tag"],
            "fields": {
                "t01": {
                    "proposed_status": "prop_t01_status",
                    "correctness": "po_t01_correct",
                    "correctness_explanation": "po_t01_correct_explain",
                    "visibility": "po_t01_vis",
                    "visibility_explanation": "po_t01_vis_explain",
                },
                "t02": {
                    "proposed_status": "prop_t02_status",
                    "correctness": "po_t02_correct",
                    "correctness_explanation": "po_t02_correct_explain",
                    "visibility": "po_t02_vis",
                    "visibility_explanation": "po_t02_vis_explain",
                },
            },
            "missing_tag_summary_role": "Summary cross-check after the two primary per-tag proposed-status assessments; retained for later protocol and participant-document alignment.",
        },
        "missing_label_branching": {
            "gateways_required": True,
            "checkbox_menus_show_only_for_yes": True,
            "checkbox_menus_required_when_shown": True,
            "at_least_one_checkbox_requires_live_qa": True,
            "unsure_does_not_show_menu": True,
            "purpose_guidance_field": "po_miss_purpose_guidance",
            "purpose_max_checked_annotation": "@MAXCHECKED=2",
            "purpose_cardinality_analysis": (
                "Derive retained fitted proposed purposes plus selected missing purposes; flag an implied "
                "corrected count above two as a cardinality/taxonomy issue, not a directly comparable "
                "corrected classification."
            ),
        },
        "analytical_completion": {
            "owner_join": ["intended_recipient = 1", "owner_consent = 1"],
            "domains_and_purposes": "verdict and visibility for every populated slot, plus correctness explanation only for Does not fit",
            "tags": "correctness and visibility for both tags, plus correctness explanation only for No",
            "missing_labels": "all three gateways and every triggered checkbox menu; prose bases are optional",
            "overall": "public-entry sufficiency, project-knowledge gateway and taxonomy fit, plus taxonomy issue for Partial Fit/No Fit",
            "excluded_optional_fields": [
                "ack_pref", "po_d01_vis_explain", "po_d02_vis_explain",
                "po_d03_vis_explain", "po_d04_vis_explain", "po_p01_vis_explain",
                "po_p02_vis_explain", "po_t01_vis_explain", "po_t02_vis_explain",
                "po_miss_domain_basis", "po_miss_purpose_basis", "po_miss_tag_basis",
                "po_suff_explain", "po_nonpublic_note", "po_tax_explain",
                "po_other_comment", "po_quote_permission"
            ],
            "excluded_display_support_fields": [
                "prop_domain_summary", "prop_purpose_summary", "prop_tag_summary", "po_classification_overview"
            ],
            "submitted_is_separate": "project_review_complete = 2 is submission status, not the analytical-completion definition",
            "final_branching_state_rule": (
                "Derive completion and analysis variables from final parent responses. Preserve raw exported "
                "values, but ignore any retained value whose field is hidden under the final branching state."
            ),
            "optional_text_missingness": (
                "Blank optional prose means not provided; it does not mean no issue, no missing information, "
                "no taxonomy problem or no reliance on project knowledge. Structured responses are primary outcomes."
            ),
            "qualitative_reporting": (
                "Report the number of comments contributing to each qualitative theme or quotation; do not "
                "interpret optional-comment themes as prevalence estimates."
            ),
        },
        "participant_reference": {
            "field": "assignment_id",
            "display_label": "Review reference",
            "survey_read_only": True,
            "owner_id_survey_hidden": True,
            "repeat_instance_not_sole_reference": True,
        },
        "live_qa_assertions": [
            "one owner-specific Survey Queue link reopens the queue and preserves progress",
            "pre-created repeated Project Review instances appear separately with the custom label",
            "participants cannot create blank repeat instances",
            "each repeated instance exports as a separate long-format row",
            "untouched pre-created instances remain present as incomplete repeated rows",
            "completion returns to the visible Survey Queue",
        ],
    }
    BRANCH_SPEC.write_text(
        yaml.safe_dump(branch, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    export_rows = [
        {
            "variable": "owner_id",
            "row_type": "owner_and_review",
            "source": "record_id",
            "analysis_role": "join_key",
            "notes": "Pseudonymous owner identifier; join owner consent onto repeating reviews.",
        },
        {
            "variable": "redcap_repeat_instrument",
            "row_type": "system",
            "source": "redcap_generated",
            "analysis_role": "row_split",
            "notes": "Blank on owner row; project_review on review rows.",
        },
        {
            "variable": "redcap_repeat_instance",
            "row_type": "system",
            "source": "redcap_generated",
            "analysis_role": "assignment_instance",
            "notes": "Blank on owner row; 1...N on pre-created review rows.",
        },
    ]
    for row in rows:
        name = row["Variable / Field Name"]
        if name == "owner_id" or row["Field Type"] == "descriptive":
            continue
        if re.fullmatch(r"po_[dpt]\d{2}_vis", name):
            export_notes = (
                "Codes: 2=Clearly visible; 1=Partly visible; 0=Not visible; 3=Unsure. "
                "Blank on the owner row."
            )
        elif re.fullmatch(r"po_[dpt]\d{2}_correct_explain", name):
            export_notes = (
                "Actual-project classification disagreement explanation; analyse only when the final fit is Does not fit or "
                "final tag correctness is No. Preserve but ignore a retained hidden value after the parent changes."
            )
        elif re.fullmatch(r"po_[dpt]\d{2}_vis_explain", name):
            export_notes = (
                "Optional label-level public-register evidence explanation; analyse only when final visibility is Partly "
                "visible, Not visible or Unsure. Blank means not provided; ignore a retained value after Clearly visible."
            )
        elif re.fullmatch(r"prop_t\d{2}_status", name):
            export_notes = (
                "Pre-populated 1=Applied or 0=Not applied for one of the two tags reviewed on every assignment; "
                "blank on the owner row."
            )
        elif name in {"prop_domain_summary", "prop_purpose_summary", "prop_tag_summary"}:
            export_notes = (
                "Deterministic display-support derivative of the existing proposed labels/statuses; "
                "not a participant response, analytical outcome or analytical-completion requirement."
            )
        elif name == "po_miss_purposes":
            export_notes = (
                "Missing-purpose checkboxes; @MAXCHECKED=2 limits this menu. Analyse selections only when the "
                "final gateway is Yes; ignore retained hidden selections after No/Unsure. Add applicable selections "
                "to proposed purposes judged Fits and flag an implied corrected count above two as a cardinality/taxonomy issue."
            )
        elif name in {"po_miss_domains", "po_miss_tags"}:
            export_notes = (
                "Structured missing-classification selections; analyse only when the final gateway is Yes and "
                "ignore retained hidden selections after No/Unsure."
            )
        elif name in {"po_miss_domain_basis", "po_miss_purpose_basis", "po_miss_tag_basis"}:
            export_notes = (
                "Optional missing-classification context; analyse only when the final gateway is Yes and at least "
                "one applicable label is selected. Blank means not provided and does not negate the structured report."
            )
        elif name == "po_suff_explain":
            export_notes = (
                "Optional project-level sufficiency context; analyse only for final Partial/Insufficient. Blank means "
                "not provided, not no missing information; ignore retained hidden text after Sufficient."
            )
        elif name == "po_tax_issue":
            export_notes = (
                "Structured project-level taxonomy issue; analyse only for final Partial Fit/No Fit and ignore "
                "retained hidden selections after Fit."
            )
        elif name == "po_tax_explain":
            export_notes = (
                "Optional project-level taxonomy context; analyse only for final Partial Fit/No Fit. Blank means "
                "not provided, not no taxonomy problem; ignore retained hidden text after Fit."
            )
        elif name == "po_nonpublic_note":
            export_notes = (
                "Optional project-level knowledge context; analyse only for final Yes/Unsure gateway. Blank means "
                "not provided, not no reliance on project knowledge; ignore retained hidden text after No."
            )
        elif name == "po_other_comment":
            export_notes = (
                "Optional enrichment. Blank means not provided. Report comment counts with qualitative themes or "
                "quotations and do not treat themes as prevalence estimates."
            )
        else:
            export_notes = "Blank on the other row type in REDCap long export."
        export_rows.append(
            {
                "variable": name,
                "row_type": "owner"
                if row["Form Name"] == "owner_consent"
                else "project_review",
                "source": row["Form Name"],
                "analysis_role": "owner_consent"
                if row["Form Name"] == "owner_consent"
                else (
                    "display_support"
                    if name in {"prop_domain_summary", "prop_purpose_summary", "prop_tag_summary"}
                    else ("assignment_or_proposal" if name in prepop else "owner_response")
                ),
                "notes": export_notes,
            }
        )
    export_rows += [
        {
            "variable": "owner_consent_timestamp",
            "row_type": "owner",
            "source": "redcap_survey_timestamp",
            "analysis_role": "consent_provenance",
            "notes": "Native Owner Consent survey completion timestamp.",
        },
        {
            "variable": "owner_consent_complete",
            "row_type": "owner",
            "source": "redcap_form_status",
            "analysis_role": "consent_completion",
            "notes": "REDCap-generated form completion status.",
        },
        {
            "variable": "project_review_timestamp",
            "row_type": "project_review",
            "source": "redcap_survey_timestamp",
            "analysis_role": "review_provenance",
            "notes": "Native repeating Project Review survey completion timestamp.",
        },
        {
            "variable": "project_review_complete",
            "row_type": "project_review",
            "source": "redcap_form_status",
            "analysis_role": "review_completion",
            "notes": "REDCap submission status: 2=Submitted. Derive offered/untouched/partial/analytically complete separately; do not treat 2 alone as analytical completeness.",
        },
    ]
    write_csv(
        EXPORT_SPEC,
        ["variable", "row_type", "source", "analysis_role", "notes"],
        export_rows,
    )


def build_formatting_audit(rows: list[dict[str, str]]) -> None:
    """Record the semantic-HTML audit for every participant-visible descriptive field."""

    purposes = {
        "owner_intro": "Study introduction and voluntary-participation overview",
        "participant_info_link": "Non-production placeholder for the approved Participant Information PDF",
        "wrong_recipient_stop": "Wrong-recipient termination message",
        "consent_decline_stop": "Consent-decline termination message",
        "po_intro": "Project Review overview and classification-dimension guidance",
        "po_classification_overview": "Read-only summary of every proposed Domain, Purpose and both tag statuses",
        "po_privacy": "Confidentiality and non-public-information warning",
        "po_taxonomy_ref": "Non-production placeholder for the optional classification reference",
        "po_miss_purpose_guidance": "Maximum-two Analytical Purposes selection guidance",
        "po_final_warning": "Final confidentiality and non-public-information reminder",
    }
    corrected = {
        "participant_info_link", "po_classification_overview", "po_intro", "po_privacy",
        "po_taxonomy_ref", "po_final_warning"
    }
    audit_rows: list[dict[str, str]] = []
    for row in rows:
        if row["Field Type"] != "descriptive":
            continue
        name = row["Variable / Field Name"]
        label = row["Field Label"]
        headings = re.findall(r"<strong>(.*?)</strong>", label, flags=re.IGNORECASE | re.DOTALL)
        without_headings = re.sub(
            r"<strong>.*?</strong>", "", label, flags=re.IGNORECASE | re.DOTALL
        )
        body = html.unescape(re.sub(r"<[^>]+>", " ", without_headings))
        body = " ".join(body.split())
        tags = sorted({tag.lower() for tag in re.findall(r"</?([a-zA-Z0-9]+)", label)})
        if name.startswith("po_d") and name.endswith("_display"):
            purpose = "Proposed Research Domain label and inline microdefinition"
        elif name.startswith("po_p") and name.endswith("_display"):
            purpose = "Proposed Analytical Purpose label and inline microdefinition"
        elif name.startswith("po_t") and name.endswith("_display"):
            purpose = "Cross-cutting tag label and inline microdefinition"
        else:
            purpose = purposes[name]
        remaining = "Confirm semantic HTML renders as recorded after dictionary import."
        if name == "participant_info_link":
            remaining = "Attach/link the final approved Participant Information PDF and verify rendering before production."
        elif name == "po_taxonomy_ref":
            remaining = "Attach/link the final formatted classification reference and verify rendering before production."
        elif name.endswith("_display"):
            remaining = "Verify piped canonical label is bold and piped microdefinition remains normal weight in live QA."
        audit_rows.append(
            {
                "variable_name": name,
                "instrument": row["Form Name"],
                "participant_visible_purpose": purpose,
                "contains_heading": "yes" if headings else "no",
                "heading_text": " | ".join(" ".join(html.unescape(item).split()) for item in headings),
                "body_text": body,
                "html_tags_used": " | ".join(tags),
                "whole_block_bold_present_before_correction": "no",
                "final_formatting_status": (
                    "corrected_semantic_html" if name in corrected else "audited_no_change"
                ),
                "remaining_live_qa_requirement": remaining,
            }
        )
    write_csv(
        FORMATTING_AUDIT,
        [
            "variable_name",
            "instrument",
            "participant_visible_purpose",
            "contains_heading",
            "heading_text",
            "body_text",
            "html_tags_used",
            "whole_block_bold_present_before_correction",
            "final_formatting_status",
            "remaining_live_qa_requirement",
        ],
        audit_rows,
    )


def _traceability_table() -> str:
    return """| Candidate 0.2 field(s) | Candidate 0.3 disposition |
|---|---|
| `owner_record_id` | Replaced by `owner_id` as the REDCap record ID because one record now represents one owner. |
| `record_type` | Removed; row type is represented by REDCap repeating metadata. |
| `owner_id` | Retained and moved to the first field/record ID on non-repeating `owner_consent`. |
| `oc_name`, `oc_email`, `oc_affiliation`, `oc_contact_source`, `oc_contactability`, `oc_contact_issue_note` | Removed from the research project; held only in the separate restricted recruitment/contact layer keyed by `owner_id`. |
| `oc_eligible_projects`, `oc_projects_offered`, `oc_minutes_per_project`, `oc_est_total_minutes`, `oc_eoi_invite_date`, `oc_eoi_status`, `oc_eoi_response_date`, `oc_projects_accepted`, `oc_followup_date`, `oc_contact_suppression`, `oc_recruit_route`, `oc_sequence_pos`, `oc_supp_reason`, `oc_reconsent_required`, `oc_consent_withdrawal`, `oc_consent_withdraw_date`, `oc_link_eligible` | Removed from PID 9149 and moved to the restricted recruitment/contact workflow. Queue access now uses owner-row consent fields and manual restricted disposition. |
| `oc_ack_permission` | Moved and renamed to owner-level `ack_pref`; choices become Yes / No / Decide later. |
| `oc_ack_name`, `oc_ack_affiliation`, `oc_ack_permission_date`, `oc_ack_permission_source` | Removed from PID 9149. Exact presentation and its operational record remain in the separate restricted contact process. |
| `pc_intro`, `pc_reason`, `pc_burden`, `pc_scope`, `pc_voluntary`, `pc_data`, `pc_withdrawal`, `pc_contact`, `pc_reference` | Consolidated into `owner_intro`, the participant-information placeholder, and consent stop messages. |
| `pc_info_version` | Renamed `participant_info_ver`; hidden candidate token must be replaced by the approved document version before production. |
| `pc_decision` | Replaced by the two-stage `intended_recipient` and `owner_consent` gateway. |
| `pc_decline_end` | Replaced by `wrong_recipient_stop` and `consent_decline_stop`; live Stop Actions remain manual configuration. |
| `owner_assignment_id` | Renamed `assignment_id` and moved onto each repeating `project_review` instance. |
| `source_record_id`, `official_project_id`, `project_title`, `datasets_used`, `public_register_url`, `production_ver`, `taxonomy_ver`, `proposal_output_sha256` | Retained per assignment on repeating `project_review`; administrative provenance is survey-hidden, while public register text is survey-read-only. |
| `owner_recruit_route`, `owner_sequence_pos`, `owner_invite_batch`, `owner_link_release`, `owner_invite_date`, `owner_reminder_date`, `owner_withdrawal_status` | Removed from PID 9149 and moved to restricted recruitment/response administration. |
| `instrument_ver` | Split into `owner_instr_ver` and `review_instr_ver`; `consent_form_ver` and `taxonomy_display_ver` add document/display provenance. |
| `prop_d01`–`prop_d12`, `po_d01_label`–`po_d12_vis` | Replaced by four pre-populated domain value/definition slots (`prop_d01_*`–`prop_d04_*`) and paired display/verdict/visibility fields with separate conditional correctness and visibility explanations. The capacity equals the frozen maximum. |
| `prop_p01`–`prop_p08`, `po_p01_label`–`po_p08_vis` | Replaced by two pre-populated purpose slots (`prop_p01_*`–`prop_p02_*`) with the same paired response structure. |
| `prop_t01`, `prop_t02`, `po_t01_label`–`po_t02_det` | Retained in substance as two always-present tag blocks: canonical label/definition, pre-populated Applied/Not applied status, required correctness, four-level visibility and separate conditional correctness and visibility explanations. |
| `po_intro`, `po_privacy`, `po_assignment`, `po_project_title`, `po_datasets` | Retained in substance; consolidated/renamed as `po_intro`, `po_privacy`, taxonomy-reference placeholder and read-only assignment fields. |
| `po_miss_domain`, `po_miss_purpose`, `po_miss_tag` | Retained as required gateways and expanded to Yes / No / Unsure. |
| `po_miss_domains`, `po_miss_purposes`, `po_miss_tags` | Retained with definitions added to every option and with `Unclear from Register Entry` excluded. |
| `po_note` | Split into separate conditional correctness and visibility explanation fields per proposed slot, one basis per missing-label dimension, `po_suff_explain`, and `po_tax_explain`. The redundant `po_tax_other` textbox was removed before import. |
| `po_sufficiency`, `po_taxonomy_fit`, `po_tax_issue` | Retained with the requested codes and explicit conditional explanations. |
| `po_nonpublic`, `po_nonpublic_note` | Retained; `po_nonpublic` adds Unsure and the note remains optional to reduce disclosure pressure. |
| `po_quote_permission`, `po_other_comment` | Retained at repeating review-instance level; quotation permission remains response-specific. |
| REDCap completion/timestamp fields | Generated per non-repeating consent row and per repeating review row; they are specified in the export schema, not dictionary rows. |"""


def build_documentation(meta: dict[str, object]) -> None:
    maxima = meta["production_cardinalities"]
    counts = meta["field_counts"]
    SPEC.write_text(
        f"""# Project Owner REDCap candidate 0.3 specification

Version: {VERSION}  
Status: unfrozen development candidate; controlled manual import and live QA pending.  
Live-development target: UCL REDCap PID 9149, “DEA Validation Study – Project Owner Review”. No repository process connected to REDCap.

## Architecture

Candidate 0.3 is a substantial pre-recruitment architecture change:

- one pseudonymous REDCap record per owner, keyed by `owner_id`, in a Classic/non-longitudinal project;
- non-repeating survey `owner_consent`;
- repeating survey `project_review`;
- one pre-created repeat instance for every owner–project assignment;
- one participant-specific Survey Queue link per owner;
- owner-level consent and acknowledgement preference collected once;
- each review independently completable and exported as one long-format row.

The dictionary contains exactly two instruments and {meta['total_fields']} fields:

- `owner_consent`: {counts['owner_consent']} fields;
- `project_review`: {counts['project_review']} fields.

Candidate 0.2 remains unchanged and unfrozen. Candidate 0.3 is not frozen and does not authorise recruitment.

## Frozen production capacity check

The authoritative frozen file is `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` ({sha256(FROZEN_OUTPUT)}; 1,308 rows). Semicolon-delimited non-empty values were counted independently in the three output columns.

| Dimension | Frozen column | Observed maximum | Candidate slots | Rows at maximum |
|---|---|---:|---:|---:|
| Research Domains | `substantive_domains` | {maxima['domain']['maximum']} | {DOMAIN_SLOTS} | {maxima['domain']['rows_at_maximum']} |
| Analytical Purposes | `analytical_purpose` | {maxima['purpose']['maximum']} | {PURPOSE_SLOTS} | {maxima['purpose']['rows_at_maximum']} |
| Cross-cutting tags | `cross_cutting_tags` | {maxima['tag']['maximum']} | {TAG_SLOTS} | {maxima['tag']['rows_at_maximum']} |

Generation fails if any observed maximum exceeds capacity.

## Taxonomy display source

`project_owner_taxonomy_display_v1.yaml` is the single owner-facing display source. It is parsed from `taxonomy_data_dictionary.yaml`, includes exactly 11 substantive domains, seven purposes and two tags in missing-label menus, plus the active proposed-only Domain and Purpose `Unclear from Register Entry` fallbacks. Every entry carries three separate values: the immutable `source_definition`, the author-approved compact `owner_microdefinition`, and the author-approved participant-reference `owner_reference_definition`. All 22 rows record `review_status: approved_by_author`, reviewer `{TAXONOMY_REVIEWER}` and review date `{TAXONOMY_REVIEW_DATE}`. Eighteen reference definitions remain verbatim frozen definitions after whitespace normalisation. Data Infrastructure & Methodology, Outcome Tracking and both cross-cutting tags combine the frozen definition with an imported inclusion/exclusion boundary clause. Their `reference_definition_provenance`, `imported_boundary_source_field`, `imported_boundary_source_path`, `imported_boundary_source_text` and `imported_boundary_note` values record the exact authoritative source and make clear that the combined reference wording is not verbatim. The microdefinitions are unchanged display-only condensations and do not alter taxonomy rules.

The unique display key is `(owner_layer, canonical_label)`, so the Domain and Purpose `Unclear from Register Entry` entries remain distinct and map to their different frozen definitions. Candidate 0.3 selects entries only when the authoritative `include_in_prompt=true`, the source layer is current and the source status is not removed. The legacy Layer B linkage `Unclear from Register Entry` has `include_in_prompt=false`, status `removed rc2`, and a non-owner layer; generation and validation therefore exclude it from every owner-facing output. Both active Unclear entries remain available only when pre-populated as model proposals and are absent from the 11/7/2 owner missing-label menus.

The same YAML generates inline definitions, menu option text, `project_owner_taxonomy_reference_v1.md` and the 22-row `project_owner_taxonomy_human_review_v1.csv`. Inline REDCap definitions and missing-label choice displays use `owner_microdefinition`; the reference Markdown uses `owner_reference_definition`. The Markdown is clean participant content with its own document version/date and no repository filenames, build/review status or audit footer; technical provenance remains in the YAML, human-review table, specification and manifest. Proposed instances pre-populate canonical label and microdefinition fields through the layer-qualified display index (including its proposed-only fallback section when needed); REDCap descriptive rows pipe those values inline. No `revision_required` or unapproved row may propagate.

## Consent and disposition

`owner_id` is the first field and REDCap record ID. It is pseudonymous and hidden from surveys with `@HIDDEN-SURVEY`. PID 9149 contains no participant name, email, affiliation, organisation or recruitment/contact field. Those data and all invitation/withdrawal administration stay in a separately restricted layer keyed by `owner_id`.

`participant_info_ver` uses the explicit candidate token `{PARTICIPANT_INFO_VERSION}`. It must be replaced with the approved participant-document version before production. The descriptive field is only a clearly marked attachment/link placeholder.

`intended_recipient` and `owner_consent` are required Yes/No gateways. Participant information precedes them. `owner_consent` appears only for the intended recipient; the two concise stop messages branch on their respective No values. The Project Review queue condition requires completed Owner Consent plus both affirmative values. REDCap Survey Stop Actions for each No response must be configured manually after import and verified live. No automatic deletion, retention-period, recruitment-system or reminder-suppression behaviour is claimed by the dictionary.

The participant-visible `intended_recipient` field note is intentionally blank. Administrative disposition instructions remain outside participant-facing dictionary text; this does not alter the No-response Stop Action, wrong-recipient termination message, consent branching or Survey Queue condition.

`ack_pref` is optional, appears once after affirmative intended-recipient confirmation and consent, and offers Yes / No / Decide later. It does not affect consent, Survey Queue access or analytical completion. PID 9149 does not collect a preferred acknowledgement name or affiliation.

## Repeating project review

Every repeat contains neutral assignment/source identifiers, frozen register text, production/taxonomy provenance and fixed proposed-label slots. `assignment_id` is a stable, survey-read-only participant-facing Review reference; it contains no participant name, email or direct identifier in the fixture or design contract. `owner_id` and internal source/provenance fields remain survey-hidden. Empty domain/purpose proposal slots are completely hidden through `[prop_*_label] <> ''`.

After the visible Review reference and public project information, three survey-hidden stored fields provide deterministic summaries of all proposed Domains, all proposed Purposes and both tag statuses. `po_classification_overview` pipes those values as a compact participant-visible overview before the framework guidance and detailed judgement blocks. Domain and Purpose summaries follow first populated proposal-slot order, omit blanks and remove duplicates without ranking; the tag summary always shows Demographic disparities / equity followed by COVID-19 & Pandemic with explicit Applied/Not applied statuses. These four fields are display support only: they are not participant-editable, analytical outcomes or analytical-completion requirements.

The Project Review introduction gives separate concise guidance for Research Domains, Analytical Purposes and cross-cutting tags. It explains that Domains may be multiple and unranked, Purposes may be multiple but are capped at two, and either, both or neither tag may apply. It also instructs participants to select Save & Return Later before leaving an unfinished review and to return through the same personalised link; it does not claim automatic saving. The privacy warning and synthetic-QA taxonomy-reference placeholder remain separate descriptive fields immediately after the introduction, in that order. The former long withdrawal paragraph remains absent from the repeat opening. A single short reminder is placed in `po_final_warning` after quotation permission and immediately before submission; it points to the Participant Information Sheet and the visible Review reference without repeating the all-reviews procedure.

Each populated domain/purpose slot has an inline label/definition and a Fits / Does not fit / Unsure verdict. Domain and purpose slots ask, “Is the basis for this classification visible in the public project title and datasets listed above?”

Both canonical cross-cutting tags are reviewed on every assignment, including when their pre-populated status is Not applied. Each block shows its common-source definition, a survey-read-only Applied/Not applied proposed status, required Yes/No/Unsure correctness, the visibility question “Is the basis for this tag status visible in the public project title and datasets listed above?”, a required correctness explanation shown only for No, and an optional visibility explanation shown for non-clear visibility. Neither block branches on proposed status.

Every visibility field uses `2, Clearly visible | 1, Partly visible | 0, Not visible | 3, Unsure`. Across all eight proposed-classification blocks, the correctness explanation is shown and required only for explicit disagreement (Does not fit/No); Unsure shows no correctness explanation. The visibility explanation is optional enrichment shown for Partly visible, Not visible or Unsure. The two field families remain analytically distinct: actual-project classification disagreement versus public-register evidence limitation or uncertainty. Public visibility is a label-level judgement; taxonomy fit and the project-knowledge gateway are overall project-level diagnostics and do not independently explain every label decision.

All three missing-label gateways are required Yes/No/Unsure items. The complete 11/7/2 definition-bearing checkbox menus appear only after Yes and are required when displayed; Unsure does not force a label selection. One optional basis field per dimension is shown when at least one checkbox is selected; the required gateway and at least one selected label determine completion. The missing-purpose construct displays the maximum-two guidance immediately before its checkbox and applies `@MAXCHECKED=2`. REDCap checkbox requiredness, at-least-one behaviour and the maximum-two action tag must be confirmed in live QA. The missing-tag gateway is retained as an explicit summary cross-check; the two per-tag correctness judgements are the primary status assessments. This deliberate redundancy requires later protocol and participant-document alignment but is not a contradictory coding rule.

Overall review fields retain required public-entry sufficiency, taxonomy fit and conditional issue type, with optional explanatory enrichment, optional final comments and response-specific quotation permission. `po_tax_explain` is optional for Partial Fit or No Fit and covers any elaboration on the “Other taxonomy problem” issue choice; no duplicate `po_tax_other` field remains. Existing `po_nonpublic`/`po_nonpublic_note` fields remain the required project-knowledge gateway and optional conditional context note. Blank optional prose means “not provided”; it is not interpreted as no issue, no missing information, no taxonomy problem or no reliance on project knowledge. Structured responses are the primary analytical outcomes. The repeated sentence “Do not provide confidential or non-public information.” is removed from the 20 conditional per-question explanations; the instrument-level warnings in `po_privacy` and `po_final_warning` remain unchanged. Named acknowledgement is not repeated.

`po_suff_explain` is isolated from proposed-classification branching: it is shown as optional enrichment only when `po_sufficiency` is Partial (`2`) or Insufficient (`3`). No Domain, Purpose or tag fit, correctness or visibility response controls it. Before REDCAP-016, each negative/unsure proposed-classification response revealed its own combined `po_d01_basis`–`po_t02_basis` field; after this revision only explicit disagreement reveals the matching required `*_correct_explain` field. The public-entry sufficiency explanation was not part of that split.

## Long-format export and analysis preparation

An owner row has blank `redcap_repeat_instrument`/`redcap_repeat_instance` and holds `intended_recipient`, `owner_consent`, `ack_pref`, `owner_consent_timestamp` and `owner_consent_complete`.

A review row has `redcap_repeat_instrument = project_review`, numbered `redcap_repeat_instance`, assignment/project/proposal values, owner responses, `project_review_timestamp` and `project_review_complete`. Pre-created untouched instances must remain exported as incomplete review rows.

Assignment-response states are defined independently:

- **Offered:** a pre-created repeat exists.
- **Untouched:** the repeat exists with no participant response.
- **Partial:** at least one response exists but the analytical-completion rule fails.
- **Analytically complete:** joined intended-recipient and consent are affirmative; every populated domain/purpose has verdict and visibility, with a correctness explanation for Does not fit; both tags have correctness and visibility, with a correctness explanation for No; all three missing-label gateways are answered and every Yes has at least one valid selection; sufficiency, project-knowledge gateway and taxonomy fit are answered; and Partial Fit/No Fit has at least one taxonomy issue type. Optional explanatory text is not required. Completion follows the final applicable branching state; retained values in fields hidden by a changed parent response neither satisfy nor prevent completion.
- **Submitted:** `project_review_complete = 2`.

A submitted review should normally be analytically complete because requiredness and branching operate in REDCap, but analysis derives and verifies analytical completeness rather than relying on form status alone. Optional visibility explanations, missing-label bases, `po_suff_explain`, `po_nonpublic_note`, `po_tax_explain`, `ack_pref`, final comments and quotation permission do not determine it. Neither the three stored classification summaries nor the descriptive overview determines analytical completion. REDCap raw exports retain any stale hidden values, but the derived analysis view masks them whenever the final parent response makes the field inapplicable.

Analysis preparation must:

1. split owner rows where `redcap_repeat_instrument` is blank from review rows where it equals `project_review`;
2. join owner consent to reviews by `owner_id`;
3. create a final-applicability analysis view that masks retained values in fields hidden under the final parent responses while preserving the raw export unchanged;
4. derive offered, untouched, partial, analytically complete and submitted indicators from that final applicable state;
5. retain offered, untouched and partial rows for recruitment and response-rate reporting;
6. restrict substantive complete-review summaries to analytically complete rows after the owner join.

For Analytical Purposes, derive the implied corrected-purpose count as the number of populated proposed purposes judged `Fits` plus the number of applicable selected missing-purpose labels where the final gateway is Yes. If that count exceeds two, flag the response as a purpose-cardinality/taxonomy issue rather than treating it as a directly comparable corrected classification. A response containing an `Unsure` proposed-purpose verdict is not a definitive corrected-purpose set even when analytically complete.

The instrument supplies label-level fit/correctness and public-visibility evidence, project-level sufficiency/project-knowledge/taxonomy-fit diagnostics, structured missing-label reports and optional explanatory evidence. These signals support subsequent adjudication; they do not automatically establish a definitive error source. For missing classifications, attribution to public versus non-public evidence may remain unresolved when optional context is blank. Owner disagreement is evidence for adjudication, not itself a gold-standard classification error. Report the number of comments contributing to each qualitative theme or quotation and do not interpret optional-comment themes as prevalence estimates.

Do **not** filter repeated rows directly with `owner_consent = 1`: non-repeating values are blank on repeated rows.

## Withdrawal reference

`assignment_id` is displayed as Review reference near the project information, remains stable independently of repeat-instance ordering, and is repeated in the manually configured completion text. Specific-review withdrawal instructions use this reference. A participant withdrawing all submitted reviews may contact the study team from the professional email address used for the invitation and state that request without knowing or quoting `owner_id`. The production withdrawal deadline remains a Participant Information Sheet configuration item and is not invented here.

## Candidate 0.2 → 0.3 architecture change

| Component | Candidate 0.2 | Candidate 0.3 |
|---|---|---|
| Record unit | Owner–project assignment (plus contact records) | One pseudonymous owner |
| Assignment representation | One separate record | One pre-created repeating Project Review instance |
| Participant link | One link per assignment | One participant-specific Survey Queue link per owner |
| Consent | Linked contact workflow | One non-repeating consent gateway |
| Acknowledgement | Restricted contact-admin location | `ack_pref` once at owner level; presentation handled separately |
| Project reviews | Separate records | Independent long-format repeat rows |
| Direct identifiers | Present in restricted admin instrument inside the project | Absent from PID 9149; contact layer separated |
| Taxonomy delivery | Inline full definitions/full admin flags | Inline definitions, conditional complete menus, optional reference |
| Export | Wide assignment/contact records | Owner row plus long-format repeating rows |

This substantial instrument architecture change is made before recruitment and before final participant-document, protocol and ethics alignment.

## Field-level traceability

{_traceability_table()}

## Files and status

The dictionary, field/branch/export specifications, participant-formatting audit, display/reference/review sources and synthetic fixture are deterministic repository artefacts. The {meta['fixture_columns']}-column synthetic Data Import Tool fixture contains only stored non-checkbox dictionary fields and valid REDCap structural/completion fields; descriptive fields and unexpanded checkbox base variables are deliberately absent, and no participant checkbox or explanation responses are pre-populated. Project-level Survey Queue, repeating-instrument, Stop Action, checkbox requiredness, survey completion, Save & Return Later, HTML rendering and attachment settings cannot be guaranteed by the CSV and are mandatory live-QA assertions. Candidate 0.3 is technically ready for controlled synthetic import and its taxonomy wording is approved for participant use. It remains unfrozen and is not ready for recruitment until live QA and coordinated participant-document, invitation, protocol, ethics and governance alignment are complete.
""",
        encoding="utf-8",
    )

    LIVE_CONFIG.write_text(
        f"""# Project Owner REDCap candidate 0.3 — PID 9149 live configuration

Version: {VERSION}  
Candidate source commit: `{CANDIDATE_SOURCE_COMMIT}`
Status: manual controlled-import checklist; unfrozen; live QA pending.  
Target: UCL REDCap PID 9149, “DEA Validation Study – Project Owner Review”.

The REDCap CSV cannot encode project mode, repeating-instrument settings, Survey Queue behaviour, Survey Stop Actions, survey completion routing, uploaded files or participant-specific invitations. Treat every item below as a required admin action or live-QA assertion.

## Controlled setup

1. Verify PID 9149 is blank, in Development, and contains no real records.
2. Import `project_owner_redcap_data_dictionary_candidate_0.3.csv`.
3. Confirm Classic/non-longitudinal mode and `owner_id` as the first/record-ID field. Do not enable auto-numbering.
4. Confirm exactly two instruments in this order: Owner Consent (`owner_consent`) and Project Review (`project_review`).
5. Enable both instruments as surveys.
6. Configure Project Review as the **only** repeating instrument.
7. Set its repeating-instance custom label exactly to `[assignment_id] — [project_title]`.
8. Keep **Repeat the Survey disabled**. Participants must not be able to create blank instances; administrators pre-create every assignment instance.
9. Keep the Survey Queue visible and configure:
   - Owner Consent active;
   - condition `[owner_id] <> ''`;
   - Auto Start enabled;
   - Project Review active;
   - condition `[owner_consent_complete] = '2' and [owner_consent] = '1' and [intended_recipient] = '1'`;
   - Project Review Auto Start disabled.
10. Configure a Survey Stop Action for `intended_recipient = No`. Expected behaviour: show the wrong-recipient stop text, end the survey, show no consent/acknowledgement questions and no Project Review queue entries. Do not infer or claim automatic deletion, retention or reminder-suppression behaviour.
11. Configure a Survey Stop Action for `owner_consent = No`. Expected behaviour: show the decline text, end the survey, collect no `ack_pref` and show no Project Review queue entries. Do not infer or claim automatic deletion, retention or reminder-suppression behaviour.
12. Add this concise queue-top text:

   > <strong>Project Owner Review</strong><br>Please begin by completing <strong>Participant Information and Consent</strong> below. If you agree to take part, your available project reviews will then appear in this list. You may complete all, some or none, in any order. To pause an unfinished review, use <strong>Save & Return Later</strong> before leaving. You can return using the same personalised link. Please do not forward this link.

13. Configure the Project Review survey settings as required, without treating repository documentation as proof of the live state:
   - **Save & Return Later: enabled**;
   - **respondents may return without a separate Return Code: enabled**;
   - **modification of completed responses: disabled**;
   - **Automatically continue to next survey: disabled**;
   - **redirect URL: blank**;
   - **participant “Repeat the Survey” option: disabled**.
14. Security implication: possession of the personalised link permits access to an unfinished review. Participants are instructed not to forward it, and direct contact identifiers are not held in the REDCap response project. Verify the live behaviour; do not describe it as confirmed from repository artefacts.
15. Configure the Project Review completion text exactly or equivalently as: “Thank you for reviewing this project. Your response has been recorded under the reference [assignment_id]. Please return to your personalised project list to review another project or to finish.” Return the participant to the visible Survey Queue and do not auto-start another review.
16. Confirm the near-submission `po_final_warning` reminder reads: “You may request withdrawal of this submitted review before the deadline stated in the Participant Information Sheet by contacting the study team and quoting the Review reference shown above.” Do not add the all-reviews procedure to the repeat.
17. Do not use a public survey URL for recruitment. Use only the participant/record-specific Survey Queue URL, which must reopen the same owner queue after Save & Return Later has been selected.
18. After approval, replace `{PARTICIPANT_INFO_VERSION}` with the approved participant-information version in controlled import data and attach/link the final approved PDF at `participant_info_link`.
19. After coordinated participant-document alignment, format and attach/link the final taxonomy-reference PDF at `po_taxonomy_ref`; the repository Markdown is the author-approved wording source.
20. Load only `live_qa/project_owner_synthetic_import_candidate_0.3.csv`. It contains three owner rows and 19 pre-created Project Review repeat rows across {meta['fixture_columns']} importable columns; the three stored classification summaries are populated on every assignment, descriptive fields and unexpanded checkbox base variables are excluded, and participant explanation fields are blank.
21. Confirm `assignment_id` is displayed as the survey-read-only **Review reference**, contains no personal identifier, states its specific-withdrawal purpose near submission, and remains stable when repeat instances are reordered.
22. Confirm the specific-review withdrawal wording uses `[assignment_id]`; confirm the all-reviews wording requires no visible owner identifier. Configure no production deadline outside the approved Participant Information Sheet.
23. Test desktop and mobile, then export and verify row structure before any real recruitment.

## Required live-QA assertions

- OWNER_TEST_001 shows consent once and one labelled project instance.
- OWNER_TEST_002 shows consent once and three separately labelled instances.
- OWNER_TEST_003 remains usable with 15 separately labelled instances.
- The custom labels show `[assignment_id] — [project_title]`.
- Save & Return Later is enabled; an unfinished review is recoverable through the same owner-specific queue link only after the participant selects Save & Return Later before leaving.
- Return without a separate Return Code is enabled; completed-response modification and Automatically continue to next survey are disabled; redirect URL is blank.
- One, some, all or none of the reviews can be completed independently.
- Completing one review returns to the visible queue and does not auto-start another.
- Participants cannot create an extra repeat instance and never see a Repeat the Survey control.
- Intended-recipient No and consent No each stop as specified and suppress Project Review.
- Owner-level `ack_pref` appears once only; no acknowledgement field appears inside Project Review.
- `ack_pref` is optional and has no effect on Survey Queue access, submission or analytical completeness.
- Empty proposed-label slots are absent, and populated definitions plus separately triggered correctness/visibility explanations behave correctly.
- The classification overview follows the Review reference/public project information and precedes detailed judgements; it shows every populated Domain and Purpose once, without ranking, and both tags in fixed order with Applied/Not applied status. The three stored summaries remain survey-hidden and participant-read-only through the overview.
- Both canonical tag blocks appear on every repeat, including Not applied statuses; each has required correctness, preserved four-level visibility, a required explanation only for No and an optional explanation for non-clear visibility, and neither branches on status.
- Both tag visibility questions use “Is the basis for this tag status visible in the public project title and datasets listed above?” with the unchanged four-level response scale.
- Missing menus contain 11 domains, seven purposes and two tags with definitions; no menu contains `Unclear from Register Entry`.
- Missing checkbox menus appear only for Yes, are required when shown, and enforce at least one selection; Unsure does not reveal a required menu. Treat at-least-one behaviour as a live-QA assertion.
- The missing-purpose guidance appears directly before its menu; `@MAXCHECKED=2` limits that menu to two selections. Confirm the action tag live, and verify analysis flags fitted-proposal-plus-missing selections above two as a cardinality/taxonomy issue.
- The missing-tag gateway functions as a summary cross-check after both primary per-tag correctness judgements and is not presented as a replacement assessment.
- The required project-knowledge gateway appears once; its optional note appears for Yes or Unsure and asks only for general-level context.
- In every domain, purpose and tag block, explicit disagreement reveals its required correctness explanation; Unsure reveals no correctness explanation; Partly visible/Not visible/Unsure reveals an optional visibility explanation; Fits/Yes plus Clearly visible reveals neither.
- The repeated sentence “Do not provide confidential or non-public information.” is absent from participant-visible field labels and notes; the central warnings in `po_privacy` and `po_final_warning` remain visible.
- `po_suff_explain` appears only as optional enrichment for Partial or Insufficient `po_sufficiency` and is not controlled by any proposed-classification fit, correctness or visibility response.
- Changing a parent response hides its former child field without necessarily deleting the stored value. Live QA must verify the display transition; analysis preserves the raw value but ignores it under the final inapplicable state.
- Does not fit/No cannot be submitted without the corresponding correctness explanation; Unsure shows no correctness-explanation textbox.
- Non-clear visibility can be submitted with its optional explanation blank.
- Missing-label Yes requires at least one selected label but not prose.
- Partial/Insufficient sufficiency can be submitted with `po_suff_explain` blank.
- Project-knowledge Yes/Unsure can be submitted with `po_nonpublic_note` blank.
- Partial Fit/No Fit requires at least one `po_tax_issue` selection but not `po_tax_explain`.
- Exercise final-state transitions: Does not fit→Unsure, missing-label Yes→No/Unsure, Partial/No Fit→Fit, non-clear→Clearly visible and project-knowledge Yes/Unsure→No. Confirm hidden values do not enter completion or derived analysis variables.
- Confirm blank optional prose is treated as not provided, never as a structured negative response.
- Live REDCap Required Field behaviour and the offline analytical-completion derivation agree; repository metadata is not proof that these runtime checks passed.
- `assignment_id` is visible as Review reference near project information, is included in completion and specific-withdrawal wording, and the REDCap repeat-instance number is not the sole participant reference.
- The short specific-review withdrawal reminder appears in `po_final_warning` after quotation permission and before submission, is absent from `po_intro`, and refers to the Participant Information Sheet and the Review reference.
- An untouched pre-created assignment exports as a row with `redcap_repeat_instrument = project_review`, its numbered instance and incomplete status.
- Each repeat exports separately; owner consent remains on the non-repeating owner row and is blank on repeated rows.
- The analysis test join by `owner_id` supplies consent to repeated reviews; no direct repeated-row consent filter is used.
- Export preparation distinguishes offered, untouched, partial, analytically complete and submitted; a submitted row is not accepted as analytically complete unless every condition in the specification is met.
- PID 9149 contains no participant name, email, affiliation, organisation/contact field, public recruitment URL, real record or real response.

## Required live migration after repository validation

Do not perform these actions from the repository task. In PID 9149 an authorised administrator must:

1. delete the disposable synthetic records;
2. re-import the regenerated candidate-0.3 dictionary;
3. confirm that `project_review` remains the repeating instrument;
4. confirm the custom repeat-instance label `[assignment_id] — [project_title]`;
5. verify Survey Queue conditions and both Stop Actions;
6. enable and verify Save & Return Later;
7. enable return without a separate Return Code;
8. confirm completed-response modification remains disabled;
9. import the regenerated synthetic fixture;
10. rerun the affected desktop/mobile, queue, overview, branching, final-state transition and return-flow live-QA tests;
11. export and verify all 19 offered assignment rows, their stored summaries and the separation of raw retained values from final-applicable analysis values.

## Evidence and exit gate

Archive the post-import live dictionary, configuration screenshots/notes, desktop/mobile results, synthetic export and a source/live comparison without credentials or live links. Candidate 0.3 remains unfrozen until every assertion passes and residual differences are resolved or explicitly approved. It is technically ready for controlled synthetic import and all 22 taxonomy definitions are author-approved. Recruitment remains blocked until live QA and later participant-document, invitation, protocol, ethics and governance alignment are complete.
""",
        encoding="utf-8",
    )


def fixture_import_headers(rows: list[dict[str, str]]) -> list[str]:
    importable_names = [
        row["Variable / Field Name"]
        for row in rows
        if row["Field Type"] not in {"descriptive", "checkbox"}
    ]
    return [
        "owner_id",
        "redcap_repeat_instrument",
        "redcap_repeat_instance",
        *[name for name in importable_names if name != "owner_id"],
        "owner_consent_complete",
        "project_review_complete",
    ]


def build_fixture(rows: list[dict[str, str]]) -> None:
    display = display_source()
    menu = {
        layer: [item for item in display["labels"] if item["owner_layer"] == layer]
        for layer in LAYER_NAMES
    }
    headers = fixture_import_headers(rows)
    output: list[dict[str, object]] = []
    owners = (("OWNER_TEST_001", 1), ("OWNER_TEST_002", 3), ("OWNER_TEST_003", 15))
    project_number = 0
    for owner_id, count in owners:
        owner = {header: "" for header in headers}
        owner.update(
            {
                "owner_id": owner_id,
                "participant_info_ver": PARTICIPANT_INFO_VERSION,
                "consent_form_ver": CONSENT_FORM_VERSION,
                "owner_instr_ver": VERSION,
                "owner_consent_complete": 0,
            }
        )
        output.append(owner)
        for instance in range(1, count + 1):
            project_number += 1
            repeat = {header: "" for header in headers}
            repeat.update(
                {
                    "owner_id": owner_id,
                    "redcap_repeat_instrument": "project_review",
                    "redcap_repeat_instance": instance,
                    "assignment_id": f"ASSIGN_TEST_{project_number:03d}",
                    "source_record_id": f"SYN_RECORD_{project_number:03d}",
                    "official_project_id": f"SYN_PROJECT_{project_number:03d}",
                    "project_title": f"Synthetic project {project_number:03d}: neutral public-register test",
                    "datasets_used": f"Synthetic dataset A{project_number:03d}; Synthetic dataset B{project_number:03d}",
                    "public_register_url": f"https://example.invalid/synthetic/{project_number:03d}",
                    "source_pop_ver": SOURCE_POPULATION_VERSION,
                    "production_ver": PRODUCTION_VERSION,
                    "taxonomy_ver": display["source"]["dictionary_version"],
                    "proposal_output_sha256": format(project_number, "064x"),
                    "review_instr_ver": VERSION,
                    "taxonomy_display_ver": TAXONOMY_DISPLAY_VERSION,
                    "project_review_complete": 0,
                }
            )
            domain_count = 4 if project_number == 1 else 1 + (project_number % 4)
            purpose_count = 2 if project_number % 2 else 1
            tag_count = 2 if project_number in {1, 5, 10, 15} else (1 if project_number % 3 == 0 else 0)
            selections = {
                "domain": [
                    menu["domain"][(project_number + offset - 1) % len(menu["domain"])]
                    for offset in range(domain_count)
                ],
                "purpose": [
                    menu["purpose"][(project_number + offset - 1) % len(menu["purpose"])]
                    for offset in range(purpose_count)
                ],
            }
            for prefix, layer, capacity in (
                ("d", "domain", DOMAIN_SLOTS),
                ("p", "purpose", PURPOSE_SLOTS),
            ):
                for slot in range(1, capacity + 1):
                    if slot <= len(selections[layer]):
                        item = selections[layer][slot - 1]
                        repeat[f"prop_{prefix}{slot:02d}_label"] = item["canonical_label"]
                        repeat[f"prop_{prefix}{slot:02d}_def"] = item["owner_microdefinition"]
            applied_tags = {
                item["canonical_label"] for item in menu["tag"][:tag_count]
            }
            for slot, item in enumerate(menu["tag"], 1):
                repeat[f"prop_t{slot:02d}_label"] = item["canonical_label"]
                repeat[f"prop_t{slot:02d}_def"] = item["owner_microdefinition"]
                repeat[f"prop_t{slot:02d}_status"] = (
                    "1" if item["canonical_label"] in applied_tags else "0"
                )
            populate_proposed_summaries(repeat)
            output.append(repeat)
    write_csv(IMPORT_FIXTURE, headers, output)


def check_v02_hashes() -> None:
    for relative, expected in V02_HASHES.items():
        actual = sha256(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"candidate-0.2 artefact changed: {relative}: {actual}")


def check_frozen_sources() -> None:
    checks = {
        TAXONOMY: TAXONOMY_SHA256,
        FROZEN_OUTPUT: FROZEN_OUTPUT_SHA256,
    }
    for path, expected in checks.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"frozen source changed: {path.relative_to(ROOT)}: {actual}")


def main() -> int:
    check_v02_hashes()
    check_frozen_sources()
    build_taxonomy_outputs()
    rows, meta = build_dictionary()
    meta["fixture_columns"] = len(fixture_import_headers(rows))
    write_csv(DICTIONARY, HEADERS, rows)
    build_specs(rows, meta)
    build_formatting_audit(rows)
    build_documentation(meta)
    build_fixture(rows)
    print(
        yaml.safe_dump(
            {
                "version": VERSION,
                "status": STATUS,
                "dictionary": str(DICTIONARY.relative_to(ROOT)).replace("\\", "/"),
                "dictionary_sha256": sha256(DICTIONARY),
                "fields": meta["total_fields"],
                "forms": meta["field_counts"],
                "production_maxima": {
                    key: value["maximum"]
                    for key, value in meta["production_cardinalities"].items()
                },
                "taxonomy_menu_counts": MENU_COUNTS,
                "taxonomy_proposed_display_counts": PROPOSED_DISPLAY_COUNTS,
                "taxonomy_human_review": {
                    "rows": 22,
                    "pending_human_approval": 0,
                    "approved_by_author": 22,
                    "revision_required": 0,
                    "reviewer": TAXONOMY_REVIEWER,
                    "review_date": TAXONOMY_REVIEW_DATE,
                },
                "synthetic_fixture": {"owners": 3, "assignments": 19, "rows": 22},
            },
            sort_keys=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
