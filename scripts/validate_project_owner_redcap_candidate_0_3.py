#!/usr/bin/env python3
"""Validate owner-redcap-candidate-0.3 entirely offline."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping

import yaml

import build_project_owner_redcap_candidate_0_3 as builder


ROOT = Path(__file__).resolve().parents[1]
VALID_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
BRANCH_REFERENCE = re.compile(r"\[([a-z][a-z0-9_]*)(?:\(([^)]+)\))?\]")
REAL_RECORD_ID = re.compile(r"\b20\d{2}/\d{3,}\b")
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
FORBIDDEN_VARIABLE = re.compile(
    r"(^|_)(name|email|affiliation|organisation|organization|contact|researcher)($|_)"
)
ALLOWED_TYPES = {
    "text",
    "notes",
    "descriptive",
    "radio",
    "dropdown",
    "checkbox",
    "yesno",
    "truefalse",
    "calc",
    "file",
    "slider",
}
ALLOWED_VALIDATION_TYPES = {
    "date_dmy",
    "date_mdy",
    "date_ymd",
    "datetime_dmy",
    "datetime_mdy",
    "datetime_ymd",
    "datetime_seconds_dmy",
    "datetime_seconds_mdy",
    "datetime_seconds_ymd",
    "email",
    "integer",
    "alpha_only",
    "number",
    "number_1dp",
    "number_2dp",
    "number_3dp",
    "number_4dp",
    "orcid",
    "phone",
    "time_hh_mm_ss",
    "time",
    "zipcode",
}
OWNER_RESPONSE_FIELDS = {"intended_recipient", "owner_consent", "ack_pref"}


class OwnerCandidate03Error(RuntimeError):
    pass


def parse_choices(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    if not value:
        return result
    for item in value.split(" | "):
        code, label = item.split(",", 1)
        result[code.strip()] = label.strip()
    return result


def load_dictionary(path: Path = builder.DICTIONARY) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != builder.HEADERS:
            raise OwnerCandidate03Error(
                "dictionary columns differ from the ordered standard REDCap 18-column schema"
            )
        return list(reader)


def load_fixture(path: Path = builder.IMPORT_FIXTURE) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _normalise(value: object) -> str:
    return " ".join(str(value or "").split())


def _dictionary_by_name(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["Variable / Field Name"]: row for row in rows}


def _response_fields(rows: Iterable[dict[str, str]]) -> set[str]:
    return OWNER_RESPONSE_FIELDS | {
        row["Variable / Field Name"]
        for row in rows
        if row["Form Name"] == "project_review"
        and row["Variable / Field Name"].startswith("po_")
        and row["Field Type"] != "descriptive"
    }


def frozen_proposed_keys() -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    with builder.FROZEN_OUTPUT.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for owner_layer, column in builder.FROZEN_COLUMNS.items():
                for label in row[column].split(";"):
                    if label.strip():
                        keys.add((owner_layer, label.strip()))
    return keys


def validate_display_source() -> dict[str, object]:
    source = yaml.safe_load(builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8"))
    taxonomy = builder.taxonomy_payload()
    taxonomy_groups: defaultdict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for item in taxonomy["categories"]:
        taxonomy_groups[(item["layer"], item["label"])].append(item)
    errors: list[str] = []
    if source.get("display_version") != builder.TAXONOMY_DISPLAY_VERSION:
        errors.append("taxonomy display version differs")
    if source.get("status") != "author_approved_display_unfrozen_live_qa_pending":
        errors.append("taxonomy display approval/live-QA status differs")
    approval = source.get("approval", {})
    if approval.get("review_status") != builder.TAXONOMY_REVIEW_STATUS:
        errors.append("taxonomy display approval status differs")
    if approval.get("reviewer") != builder.TAXONOMY_REVIEWER:
        errors.append("taxonomy display reviewer differs")
    if approval.get("review_date") != builder.TAXONOMY_REVIEW_DATE:
        errors.append("taxonomy display review date differs")
    if source.get("source", {}).get("sha256") != builder.sha256(builder.TAXONOMY):
        errors.append("taxonomy display source hash differs")
    if source.get("source", {}).get("dictionary_version") != taxonomy["metadata"]["dictionary_version"]:
        errors.append("taxonomy display dictionary version differs")
    menu_groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    display_entries = builder.all_display_entries(source)
    display_keys = [builder.display_key(item) for item in display_entries]
    if len(display_keys) != len(set(display_keys)):
        errors.append("duplicate owner taxonomy (layer, canonical_label) key")
    for item in display_entries:
        owner_key = builder.display_key(item)
        source_key = (item.get("source_layer"), item.get("canonical_label"))
        originals = taxonomy_groups.get(source_key, [])
        if len(originals) != 1:
            errors.append(f"display label does not map to exactly one taxonomy entry: {source_key}")
            continue
        original = originals[0]
        if original is None:
            errors.append(f"display label is absent from taxonomy: {key}")
            continue
        if original.get("include_in_prompt") is not True:
            errors.append(f"display label is not prompt-included: {source_key}")
        if str(original.get("status", "")).lower().startswith("removed"):
            errors.append(f"display label is removed: {source_key}")
        if item.get("source_status") != original.get("status"):
            errors.append(f"source status drift: {source_key}")
        if _normalise(item.get("source_definition")) != _normalise(original.get("definition")):
            errors.append(f"source definition drift: {source_key}")
        source_definition = _normalise(original.get("definition"))
        expected_reference = builder.owner_reference_definition(owner_key, source_definition)
        boundary_clause_imported = owner_key in builder.REFERENCE_BOUNDARY_CLAUSES
        expected_boundary_sources = builder.imported_boundary_sources(owner_key, original)
        if _normalise(item.get("owner_reference_definition")) != _normalise(
            expected_reference
        ):
            errors.append(f"owner reference definition differs from approved source: {source_key}")
        if item.get("owner_microdefinition") != builder.MICRODEFINITIONS.get(owner_key):
            errors.append(f"owner microdefinition differs from approved wording: {owner_key}")
        if not _normalise(item.get("owner_microdefinition")):
            errors.append(f"approved owner microdefinition is empty: {owner_key}")
        if not _normalise(item.get("owner_reference_definition")):
            errors.append(f"approved owner reference definition is empty: {owner_key}")
        if item.get("review_status") != builder.TAXONOMY_REVIEW_STATUS:
            errors.append(f"display definition is not author-approved: {owner_key}")
        if item.get("reviewer") != builder.TAXONOMY_REVIEWER:
            errors.append(f"display reviewer differs: {owner_key}")
        if item.get("review_date") != builder.TAXONOMY_REVIEW_DATE:
            errors.append(f"display review date differs: {owner_key}")
        if item.get("microdefinition_material_simplification") is not True:
            errors.append(f"display microdefinition simplification flag differs: {owner_key}")
        if item.get("reference_definition_material_simplification") is not False:
            errors.append(f"display reference simplification flag differs: {owner_key}")
        if item.get("reference_definition_boundary_clause_imported") is not boundary_clause_imported:
            errors.append(f"display reference boundary-clause flag differs: {owner_key}")
        expected_origin = (
            "frozen_definition_plus_imported_exclusion_boundary_clause"
            if boundary_clause_imported
            else "frozen_definition_verbatim_after_whitespace_normalisation"
        )
        if item.get("wording_origin") != expected_origin:
            errors.append(f"display reference wording origin differs: {owner_key}")
        if item.get("reference_definition_provenance") != expected_origin:
            errors.append(f"display reference-definition provenance differs: {owner_key}")
        expected_source_fields = [source["source_field"] for source in expected_boundary_sources]
        expected_source_paths = [source["source_path"] for source in expected_boundary_sources]
        expected_source_texts = [source["source_text"] for source in expected_boundary_sources]
        if item.get("imported_boundary_source_field") != expected_source_fields:
            errors.append(f"display imported-boundary source fields differ: {owner_key}")
        if item.get("imported_boundary_source_path") != expected_source_paths:
            errors.append(f"display imported-boundary source paths differ: {owner_key}")
        if item.get("imported_boundary_source_text") != expected_source_texts:
            errors.append(f"display imported-boundary source text differs: {owner_key}")
        if boundary_clause_imported and not _normalise(item.get("imported_boundary_note")):
            errors.append(f"display imported-boundary note is empty: {owner_key}")
        if not boundary_clause_imported:
            if _normalise(item.get("owner_reference_definition")) != source_definition:
                errors.append(f"verbatim reference differs materially from cited source: {owner_key}")
            if _normalise(item.get("imported_boundary_note")):
                errors.append(f"verbatim reference has an imported-boundary note: {owner_key}")
        expected_reuse = (
            "approved_microdefinition_with_frozen_definition_plus_imported_boundary_clause"
            if boundary_clause_imported
            else "approved_microdefinition_with_verbatim_source_reference"
        )
        if item.get("reused_or_condensed") != expected_reuse:
            errors.append(f"display definition provenance differs: {source_key}")
        if item in source.get("labels", []):
            menu_groups[owner_key[0]].append(item)
            if item.get("include_in_owner_missing_menu") is not True:
                errors.append(f"menu label is not marked for owner menus: {owner_key}")
        else:
            if item.get("include_in_owner_missing_menu") is not False:
                errors.append(f"proposed-only label is enabled for owner menus: {owner_key}")
            if item.get("include_as_proposed_label") is not True:
                errors.append(f"proposed-only label is not active for model proposals: {owner_key}")
            if item.get("owner_reference_definition") != builder.PROPOSED_ONLY_DEFINITIONS.get(
                owner_key
            ):
                errors.append(f"proposed-only reference definition differs: {owner_key}")
    counts = {key: len(menu_groups[key]) for key in builder.MENU_COUNTS}
    if counts != builder.MENU_COUNTS:
        errors.append(f"taxonomy display menu counts differ: {counts}")
    if any(
        item.get("canonical_label") == "Unclear from Register Entry"
        for item in source.get("labels", [])
    ):
        errors.append("Unclear from Register Entry appears in owner menu labels")
    fallbacks = source.get("proposed_only_fallbacks", [])
    if len(fallbacks) != 2:
        errors.append("proposed-only fallback count differs")
    if {
        (item.get("owner_layer"), item.get("canonical_label")) for item in fallbacks
    } != {
        ("domain", "Unclear from Register Entry"),
        ("purpose", "Unclear from Register Entry"),
    }:
        errors.append("proposed-only fallback identity differs")
    if any(item.get("include_in_owner_missing_menu") is not False for item in fallbacks):
        errors.append("a public-evidence fallback is enabled for owner missing menus")
    proposed_counts = Counter(key[0] for key in display_keys)
    if dict(proposed_counts) != builder.PROPOSED_DISPLAY_COUNTS:
        errors.append(f"proposed display counts differ: {dict(proposed_counts)}")
    linkage_key = ("Layer B -- linkage", builder.UNCLEAR_LABEL)
    linkage_entries = taxonomy_groups.get(linkage_key, [])
    if len(linkage_entries) != 1:
        errors.append("legacy linkage Unclear source entry count differs")
    else:
        linkage = linkage_entries[0]
        if linkage.get("include_in_prompt") is not False or not str(
            linkage.get("status", "")
        ).lower().startswith("removed"):
            errors.append("legacy linkage Unclear is not authoritatively excluded")
    if any(item.get("source_layer") == "Layer B -- linkage" for item in display_entries):
        errors.append("legacy linkage Unclear entered owner-facing outputs")
    proposed_keys = frozen_proposed_keys()
    missing_proposed = proposed_keys - set(display_keys)
    if missing_proposed:
        errors.append(f"frozen proposed labels lack unique display definitions: {sorted(missing_proposed)}")
    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {
        "version": source["display_version"],
        "counts": counts,
        "fallbacks": len(fallbacks),
        "proposed_display_counts": dict(proposed_counts),
        "distinct_frozen_proposed_mappings": len(proposed_keys),
        "status": source["status"],
        "approved_by_author": len(display_entries),
        "reviewer": approval.get("reviewer"),
        "review_date": approval.get("review_date"),
    }


def validate_taxonomy_human_review() -> dict[str, object]:
    expected_headers = [
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
    ]
    with builder.TAXONOMY_HUMAN_REVIEW.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames
        rows = list(reader)
    errors: list[str] = []
    if headers != expected_headers:
        errors.append("taxonomy human-review columns differ")
    if len(rows) != 22:
        errors.append(f"taxonomy human-review row count differs: {len(rows)}")
    display = yaml.safe_load(builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8"))
    expected = {
        (item["owner_layer"], item["canonical_label"]): item
        for item in builder.all_display_entries(display)
    }
    key_counts = Counter((row["layer"], row["canonical_label"]) for row in rows)
    duplicate_keys = sorted(key for key, count in key_counts.items() if count > 1)
    actual = {(row["layer"], row["canonical_label"]): row for row in rows}
    if set(actual) != set(expected):
        errors.append("taxonomy human-review labels differ from display source")
    allowed = {"pending_human_approval", "approved_by_author", "revision_required"}
    for key, row in actual.items():
        item = expected.get(key)
        if item is None:
            continue
        if row["review_status"] not in allowed:
            errors.append(f"invalid taxonomy review status: {key}")
        if row["review_status"] != builder.TAXONOMY_REVIEW_STATUS:
            errors.append(f"taxonomy wording is not author-approved: {key}")
        if row["reviewer"] != builder.TAXONOMY_REVIEWER:
            errors.append(f"taxonomy reviewer differs: {key}")
        if row["review_date"] != builder.TAXONOMY_REVIEW_DATE:
            errors.append(f"taxonomy review date differs: {key}")
        if _normalise(row["current_short_definition"]) != _normalise(
            item["source_definition"]
        ):
            errors.append(f"human-review current wording drifts from display source: {key}")
        reference_definition = row["candidate_reference_definition"]
        if _normalise(reference_definition) != _normalise(
            item["owner_reference_definition"]
        ):
            errors.append(f"human-review reference wording drifts from display source: {key}")
        if not reference_definition.strip():
            errors.append(f"approved human-review reference definition is empty: {key}")
        reference_words = builder.reference_definition_word_count(reference_definition)
        reference_characters = len(reference_definition)
        if row["reference_definition_word_count"] != str(reference_words):
            errors.append(f"reference definition word count differs: {key}")
        if row["reference_definition_character_count"] != str(reference_characters):
            errors.append(f"reference definition character count differs: {key}")
        microdefinition = row["candidate_microdefinition"]
        expected_microdefinition = builder.MICRODEFINITIONS.get(key)
        if microdefinition != expected_microdefinition:
            errors.append(f"human-review microdefinition proposal differs from generator: {key}")
        computed_words = builder.microdefinition_word_count(microdefinition)
        computed_characters = len(microdefinition)
        if row["microdefinition_word_count"] != str(computed_words):
            errors.append(f"microdefinition word count differs: {key}")
        if row["microdefinition_character_count"] != str(computed_characters):
            errors.append(f"microdefinition character count differs: {key}")
        expected_ambiguity = builder.AMBIGUITY_NOTES.get(key, "")
        if row["possible_ambiguity"] != expected_ambiguity:
            errors.append(f"taxonomy ambiguity review field differs: {key}")
        if _normalise(row["source_taxonomy_definition"]) != _normalise(item["source_definition"]):
            errors.append(f"human-review source wording drifts from taxonomy: {key}")
        expected_reuse = (
            "approved_microdefinition_with_frozen_definition_plus_imported_boundary_clause"
            if key in builder.REFERENCE_BOUNDARY_CLAUSES
            else "approved_microdefinition_with_verbatim_source_reference"
        )
        if row["reused_or_condensed"] != expected_reuse:
            errors.append(f"human-review wording provenance differs: {key}")
        if row["reference_definition_provenance"] != item["reference_definition_provenance"]:
            errors.append(f"human-review reference provenance differs: {key}")
        for column in (
            "imported_boundary_source_field",
            "imported_boundary_source_path",
            "imported_boundary_source_text",
        ):
            try:
                actual_value = json.loads(row[column])
            except json.JSONDecodeError:
                errors.append(f"human-review {column} is not valid JSON: {key}")
                continue
            if actual_value != item[column]:
                errors.append(f"human-review {column} differs: {key}")
        if row["imported_boundary_note"] != item["imported_boundary_note"]:
            errors.append(f"human-review imported-boundary note differs: {key}")
    counts = Counter(row["review_status"] for row in rows)
    empty_microdefinitions = sorted(
        (row["layer"], row["canonical_label"])
        for row in rows
        if not row["candidate_microdefinition"].strip()
    )
    word_counts = [int(row["microdefinition_word_count"]) for row in rows]
    character_counts = [int(row["microdefinition_character_count"]) for row in rows]
    reference_word_counts = [int(row["reference_definition_word_count"]) for row in rows]
    reference_character_counts = [
        int(row["reference_definition_character_count"]) for row in rows
    ]
    below_preferred_word_target = sorted(
        (row["layer"], row["canonical_label"])
        for row in rows
        if int(row["microdefinition_word_count"]) < 10
    )
    above_preferred_word_target = sorted(
        (row["layer"], row["canonical_label"])
        for row in rows
        if int(row["microdefinition_word_count"]) > 18
    )
    exceeds_soft_limits = [
        {
            "layer": row["layer"],
            "canonical_label": row["canonical_label"],
            "word_count": int(row["microdefinition_word_count"]),
            "character_count": int(row["microdefinition_character_count"]),
        }
        for row in rows
        if int(row["microdefinition_word_count"]) > 22
        or int(row["microdefinition_character_count"]) > 150
    ]
    reference_outside_preferred_range = [
        {
            "layer": row["layer"],
            "canonical_label": row["canonical_label"],
            "word_count": int(row["reference_definition_word_count"]),
            "character_count": int(row["reference_definition_character_count"]),
        }
        for row in rows
        if int(row["reference_definition_word_count"])
        < builder.REFERENCE_PREFERRED_WORD_MIN
        or int(row["reference_definition_word_count"])
        > builder.REFERENCE_PREFERRED_WORD_MAX
    ]
    unclear_rows = [
        row for row in rows if row["canonical_label"] == builder.UNCLEAR_LABEL
    ]
    unclear_microdefinitions_identical = (
        len(unclear_rows) == 2
        and unclear_rows[0]["candidate_microdefinition"]
        == unclear_rows[1]["candidate_microdefinition"]
    )
    missing_boundary_notes = sorted(
        key
        for key in builder.HIGH_RISK_BOUNDARY_NOTES
        if not actual.get(key, {}).get("essential_boundary_preserved", "").strip()
    )
    compression_risk_entries = sorted(
        (row["layer"], row["canonical_label"])
        for row in rows
        if row["compression_note"].startswith("Human review focus:")
    )
    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {
        "rows": len(rows),
        "pending_human_approval": counts["pending_human_approval"],
        "approved_by_author": counts["approved_by_author"],
        "revision_required": counts["revision_required"],
        "editorial_checks": {
            "word_count_range": [min(word_counts), max(word_counts)],
            "character_count_range": [min(character_counts), max(character_counts)],
            "reference_word_count_range": [
                min(reference_word_counts),
                max(reference_word_counts),
            ],
            "reference_character_count_range": [
                min(reference_character_counts),
                max(reference_character_counts),
            ],
            "reference_preferred_word_range": [
                builder.REFERENCE_PREFERRED_WORD_MIN,
                builder.REFERENCE_PREFERRED_WORD_MAX,
            ],
            "reference_outside_preferred_range": reference_outside_preferred_range,
            "below_preferred_word_target": below_preferred_word_target,
            "above_preferred_word_target": above_preferred_word_target,
            "exceeds_soft_limits": exceeds_soft_limits,
            "empty_microdefinitions": empty_microdefinitions,
            "duplicate_keys": duplicate_keys,
            "unclear_microdefinitions_identical": unclear_microdefinitions_identical,
            "missing_high_risk_boundary_notes": missing_boundary_notes,
            "compression_risk_entries": compression_risk_entries,
        },
    }


def validate_dictionary(path: Path = builder.DICTIONARY) -> dict[str, object]:
    rows = load_dictionary(path)
    by = _dictionary_by_name(rows)
    errors: list[str] = []
    names = [row["Variable / Field Name"] for row in rows]
    forms = tuple(dict.fromkeys(row["Form Name"] for row in rows))
    form_counts = Counter(row["Form Name"] for row in rows)
    if forms != builder.FORMS:
        errors.append(f"forms differ: {forms}")
    if names[0] != "owner_id" or rows[0]["Form Name"] != "owner_consent":
        errors.append("owner_id is not the first record-ID field")
    if len(names) != len(set(names)):
        errors.append("variable names are not unique")
    for name in names:
        if not VALID_NAME.fullmatch(name):
            errors.append(f"invalid REDCap variable name: {name}")
        if len(name) > 26:
            errors.append(f"REDCap variable name exceeds 26 characters: {name}")
        if FORBIDDEN_VARIABLE.search(name):
            errors.append(f"direct identifier/contact variable is prohibited: {name}")
    if any(row["Identifier?"] for row in rows):
        errors.append("dictionary marks one or more direct identifier fields")
    if any(row["Field Type"] not in ALLOWED_TYPES for row in rows):
        errors.append("dictionary contains an unsupported field type")
    validation_column = "Text Validation Type OR Show Slider Number"
    validation_types = [row[validation_column] for row in rows if row[validation_column]]
    if any(value != value.lower() for value in validation_types):
        errors.append("dictionary validation types must be lower-case")
    unsupported_validation_types = sorted(
        set(validation_types) - ALLOWED_VALIDATION_TYPES
    )
    if unsupported_validation_types:
        errors.append(
            "dictionary contains validation types unsupported by the target REDCap instance: "
            f"{unsupported_validation_types}"
        )
    if by.get("public_register_url", {}).get(validation_column):
        errors.append("public_register_url validation type must remain blank")

    expected_counts = {"owner_consent": 11, "project_review": 86}
    if dict(form_counts) != expected_counts:
        errors.append(f"field counts differ: {dict(form_counts)}")
    if len(rows) != 97:
        errors.append(f"total field count differs: {len(rows)}")
    domain_guidance = (
        "A project may have several Research Domains. Each proposed Domain should be judged "
        "independently; the Domains are not ranked."
    )
    if domain_guidance not in by.get("po_intro", {}).get("Field Label", ""):
        errors.append("Project Review introduction omits multi-label, unranked Domain guidance")

    required_consent = {
        "owner_id",
        "participant_info_ver",
        "consent_form_ver",
        "owner_instr_ver",
        "intended_recipient",
        "owner_consent",
    }
    if not required_consent <= set(by):
        errors.append(f"required owner fields missing: {sorted(required_consent - set(by))}")
    if parse_choices(by["intended_recipient"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Yes",
        "0": "No",
    }:
        errors.append("intended_recipient is not required Yes/No")
    if by["intended_recipient"]["Field Note"]:
        errors.append("intended_recipient field note must remain blank")
    participant_visible_text = "\n".join(
        f"{row['Field Label']}\n{row['Field Note']}"
        for row in rows
        if builder.HIDDEN_ADMIN not in row["Field Annotation"]
    ).lower()
    if "restricted recruitment/contact system" in participant_visible_text:
        errors.append("participant-facing dictionary text exposes restricted contact administration")
    if "dispositioned" in participant_visible_text:
        errors.append("participant-facing dictionary text exposes internal disposition language")
    if parse_choices(by["owner_consent"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Yes, I agree to take part",
        "0": "No, I do not wish to take part",
    }:
        errors.append("owner_consent is not required Yes/No")
    if parse_choices(by["ack_pref"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Yes",
        "0": "No",
        "2": "Decide later",
    }:
        errors.append("ack_pref choices differ")
    for name in ("intended_recipient", "owner_consent"):
        if by[name]["Required Field?"] != "y":
            errors.append(f"required owner field is not required: {name}")
        if by[name]["Form Name"] != "owner_consent":
            errors.append(f"owner-level field appears outside owner_consent: {name}")
    if by["ack_pref"]["Required Field?"]:
        errors.append("ack_pref must remain optional")
    if by["ack_pref"]["Form Name"] != "owner_consent":
        errors.append("ack_pref appears outside owner_consent")
    expected_owner_branches = {
        "owner_consent": "[intended_recipient] = '1'",
        "wrong_recipient_stop": "[intended_recipient] = '0'",
        "consent_decline_stop": "[owner_consent] = '0'",
        "ack_pref": "[intended_recipient] = '1' and [owner_consent] = '1'",
    }
    for name, expected_branch in expected_owner_branches.items():
        if by[name]["Branching Logic (Show field only if...)"] != expected_branch:
            errors.append(f"owner consent branching differs: {name}")
    owner_order = {name: names.index(name) for name in (
        "owner_intro", "participant_info_link", "intended_recipient", "owner_consent"
    )}
    if not (
        owner_order["owner_intro"] < owner_order["intended_recipient"]
        and owner_order["participant_info_link"] < owner_order["intended_recipient"]
        and owner_order["participant_info_link"] < owner_order["owner_consent"]
    ):
        errors.append("participant information is not before recipient confirmation and consent")
    expected_consent_label = (
        "I confirm that I have read and understood the Participant Information Sheet provided with this "
        "survey, have had the opportunity to ask questions, and agree to take part in the Project Owner Review."
    )
    if by["owner_consent"]["Field Label"] != expected_consent_label:
        errors.append("owner_consent participant wording differs")
    intro = by["owner_intro"]["Field Label"]
    for phrase in (
        "named as a researcher on one or more projects in the UK Statistics Authority public register",
        "one, some, all or none",
        "Your progress is saved",
        "same personalised link",
    ):
        if phrase not in intro:
            errors.append(f"owner_intro omits participant-facing content: {phrase}")
    for prohibited in (
        "owner status is the provenance",
        "review stream",
        "after expressing interest",
        "separate project links",
        "links will be released",
    ):
        if prohibited.lower() in intro.lower():
            errors.append(f"owner_intro retains prohibited technical/link wording: {prohibited}")
    if by["owner_id"]["Field Annotation"] != builder.HIDDEN_ADMIN:
        errors.append("owner_id does not use the supported survey-hidden action tag")
    for name in ("participant_info_ver", "consent_form_ver", "owner_instr_ver"):
        if by[name]["Field Annotation"] != builder.HIDDEN_ADMIN:
            errors.append(f"owner administrative field is not survey-hidden/read-only: {name}")
    if builder.PARTICIPANT_INFO_VERSION == "project-owner-information-v1":
        errors.append("participant-information version reused the previous final token")
    ack_label = by["ack_pref"]["Field Label"]
    for phrase in (
        "optional and separate from your decision to take part",
        "contact you separately",
        "name and affiliation should appear",
    ):
        if phrase not in ack_label:
            errors.append(f"acknowledgement wording omits: {phrase}")
    if any(
        "ack" in name for name, row in by.items() if row["Form Name"] == "project_review"
    ):
        errors.append("Project Review contains a repeated acknowledgement field")

    prepop_visible = {
        "assignment_id",
        "project_title",
        "datasets_used",
        "public_register_url",
        "prop_t01_status",
        "prop_t02_status",
    }
    for name in prepop_visible:
        if by[name]["Field Annotation"] != builder.READONLY_SURVEY:
            errors.append(f"participant-visible pre-populated field is not survey-read-only: {name}")
    hidden_admin = {
        "source_record_id",
        "official_project_id",
        "source_pop_ver",
        "production_ver",
        "taxonomy_ver",
        "proposal_output_sha256",
        "review_instr_ver",
        "taxonomy_display_ver",
    }
    hidden_admin |= {
        name for name in names
        if name.startswith("prop_") and not re.fullmatch(r"prop_t\d{2}_status", name)
    }
    for name in hidden_admin:
        if by[name]["Field Annotation"] != builder.HIDDEN_ADMIN:
            errors.append(f"administrative/pre-populated field is not survey-hidden/read-only: {name}")

    maxima = builder.production_cardinalities()
    for layer, capacity in builder.SLOT_CAPACITY.items():
        if capacity < maxima[layer]["maximum"]:
            errors.append(f"{layer} slot capacity is below the frozen maximum")
    for prefix, layer, capacity in (
        ("d", "domain", builder.DOMAIN_SLOTS),
        ("p", "purpose", builder.PURPOSE_SLOTS),
    ):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            label = f"prop_{stem}_label"
            definition = f"prop_{stem}_def"
            display = f"po_{stem}_display"
            fit = f"po_{stem}_fit"
            visibility = f"po_{stem}_vis"
            basis = f"po_{stem}_basis"
            required = {label, definition, display, fit, visibility, basis}
            if not required <= set(by):
                errors.append(f"incomplete {layer} slot: {stem}")
                continue
            visible = f"[{label}] <> ''"
            for name in (display, fit, visibility):
                if by[name]["Branching Logic (Show field only if...)"] != visible:
                    errors.append(f"empty proposed slot is not completely hidden: {name}")
            if parse_choices(by[fit]["Choices, Calculations, OR Slider Labels"]) != {
                "1": "Fits",
                "2": "Does not fit",
                "3": "Unsure",
            }:
                errors.append(f"verdict choices differ: {fit}")
            if parse_choices(by[visibility]["Choices, Calculations, OR Slider Labels"]) != {
                "2": "Clearly visible",
                "1": "Partly visible",
                "0": "Not visible",
                "3": "Unsure",
            }:
                errors.append(f"visibility choices differ: {visibility}")
            expected_visibility_question = (
                "Is the basis for this classification visible in the public project title and "
                "datasets listed above?"
            )
            if by[visibility]["Field Label"] != expected_visibility_question:
                errors.append(f"visibility wording differs: {visibility}")
            basis_branch = by[basis]["Branching Logic (Show field only if...)"]
            expected_basis_branch = (
                f"[{fit}] = '2' or [{fit}] = '3' or "
                f"[{visibility}] = '1' or [{visibility}] = '0' or [{visibility}] = '3'"
            )
            if basis_branch != expected_basis_branch:
                errors.append(f"conditional slot basis differs: {basis}")
            if by[basis]["Required Field?"] != "y":
                errors.append(f"conditional slot basis is not required: {basis}")

    tag_entries = [
        item for item in builder.display_source()["labels"] if item["owner_layer"] == "tag"
    ]
    for index, item in enumerate(tag_entries, 1):
        stem = f"t{index:02d}"
        label = f"prop_{stem}_label"
        definition = f"prop_{stem}_def"
        status = f"prop_{stem}_status"
        display_name = f"po_{stem}_display"
        correctness = f"po_{stem}_correct"
        visibility = f"po_{stem}_vis"
        basis = f"po_{stem}_basis"
        needed = {label, definition, status, display_name, correctness, visibility, basis}
        if not needed <= set(by):
            errors.append(f"incomplete always-reviewed tag block: {stem}")
            continue
        if any(by[name]["Branching Logic (Show field only if...)"] for name in (
            display_name, status, correctness, visibility
        )):
            errors.append(f"tag block is conditionally hidden: {stem}")
        if parse_choices(by[status]["Choices, Calculations, OR Slider Labels"]) != {
            "1": "Applied", "0": "Not applied"
        }:
            errors.append(f"tag proposed-status choices differ: {status}")
        if by[status]["Field Annotation"] != builder.READONLY_SURVEY:
            errors.append(f"tag proposed status is not survey-read-only: {status}")
        if parse_choices(by[correctness]["Choices, Calculations, OR Slider Labels"]) != {
            "1": "Yes", "0": "No", "2": "Unsure"
        }:
            errors.append(f"tag correctness choices differ: {correctness}")
        if by[correctness]["Required Field?"] != "y":
            errors.append(f"tag correctness is not required: {correctness}")
        if parse_choices(by[visibility]["Choices, Calculations, OR Slider Labels"]) != {
            "2": "Clearly visible", "1": "Partly visible", "0": "Not visible", "3": "Unsure"
        }:
            errors.append(f"tag visibility choices differ: {visibility}")
        if by[visibility]["Field Label"] != (
            "Could the correct status for this tag reasonably be determined from the public project "
            "title and datasets listed above?"
        ):
            errors.append(f"tag visibility wording differs: {visibility}")
        expected_basis = (
            f"[{correctness}] = '0' or [{correctness}] = '2' or "
            f"[{visibility}] = '1' or [{visibility}] = '0' or [{visibility}] = '3'"
        )
        if by[basis]["Branching Logic (Show field only if...)"] != expected_basis:
            errors.append(f"tag conditional basis differs: {basis}")
        if by[basis]["Required Field?"] != "y":
            errors.append(f"tag basis is not required: {basis}")

    display = yaml.safe_load(builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8"))
    expected_by_layer = {
        layer: {
            str(item["code"]): (
                str(item["canonical_label"]),
                _normalise(item["owner_microdefinition"]),
            )
            for item in display["labels"]
            if item["owner_layer"] == layer
        }
        for layer in builder.MENU_COUNTS
    }
    menu_fields = {
        "domain": "po_miss_domains",
        "purpose": "po_miss_purposes",
        "tag": "po_miss_tags",
    }
    for layer, name in menu_fields.items():
        actual = parse_choices(by[name]["Choices, Calculations, OR Slider Labels"])
        if len(actual) != builder.MENU_COUNTS[layer]:
            errors.append(f"{layer} missing-menu count differs: {len(actual)}")
        decoded: dict[str, tuple[str, str]] = {}
        for code, value in actual.items():
            if " — " not in value:
                errors.append(f"missing-menu option lacks definition: {name}({code})")
                continue
            label, definition = value.split(" — ", 1)
            decoded[code] = (label, _normalise(definition))
        if decoded != expected_by_layer[layer]:
            errors.append(f"{layer} missing-menu labels/definitions drift from display source")
        if "Unclear from Register Entry" in by[name]["Choices, Calculations, OR Slider Labels"]:
            errors.append(f"Unclear from Register Entry appears in {name}")
    gateway_config = {
        "domain": (
            "po_miss_domain",
            "Should any additional Research Domain have been assigned?",
            "po_miss_domain_basis",
        ),
        "purpose": (
            "po_miss_purpose",
            "Should any additional Analytical Purpose have been assigned?",
            "po_miss_purpose_basis",
        ),
        "tag": (
            "po_miss_tag",
            "Should either cross-cutting tag have been assigned or applied differently?",
            "po_miss_tag_basis",
        ),
    }
    for layer, (gateway, question, basis) in gateway_config.items():
        menu = menu_fields[layer]
        if by[gateway]["Field Label"] != question:
            errors.append(f"missing-label gateway wording differs: {gateway}")
        if parse_choices(by[gateway]["Choices, Calculations, OR Slider Labels"]) != {
            "1": "Yes", "0": "No", "2": "Unsure"
        }:
            errors.append(f"missing-label gateway choices differ: {gateway}")
        if by[gateway]["Required Field?"] != "y":
            errors.append(f"missing-label gateway is not required: {gateway}")
        if by[menu]["Branching Logic (Show field only if...)"] != f"[{gateway}] = '1'":
            errors.append(f"missing-label menu does not branch only on Yes: {menu}")
        if by[menu]["Required Field?"] != "y":
            errors.append(f"missing-label menu is not required when shown: {menu}")
        if layer == "purpose" and by[menu]["Field Annotation"] != "@MAXCHECKED=2":
            errors.append("missing-purpose menu lacks @MAXCHECKED=2")
        entries = [
            item for item in display["labels"] if item["owner_layer"] == layer
        ]
        if by[basis]["Branching Logic (Show field only if...)"] != builder.checkbox_trigger(menu, entries):
            errors.append(f"missing-label basis branching differs: {basis}")
        if by[basis]["Required Field?"] != "y":
            errors.append(f"missing-label basis is not required: {basis}")
    purpose_guidance = by.get("po_miss_purpose_guidance")
    expected_purpose_guidance = (
        "The framework assigns a maximum of two Analytical Purposes to each project. "
        "Select only the most important missing purpose or purposes, taking account of any "
        "proposed purposes that you judged to fit. The resulting classification should "
        "contain no more than two purposes in total."
    )
    if purpose_guidance is None:
        errors.append("missing-purpose participant guidance is absent")
    else:
        if purpose_guidance["Field Type"] != "descriptive":
            errors.append("missing-purpose guidance is not descriptive")
        if purpose_guidance["Field Label"] != expected_purpose_guidance:
            errors.append("missing-purpose guidance wording differs")
        if purpose_guidance["Branching Logic (Show field only if...)"] != "[po_miss_purpose] = '1'":
            errors.append("missing-purpose guidance branching differs")

    # Every reference in branching logic must resolve. Checkbox references must
    # point to a checkbox option code that exists.
    for row in rows:
        branch = row["Branching Logic (Show field only if...)"]
        if branch.count("(") != branch.count(")"):
            errors.append(f"unbalanced branching logic: {row['Variable / Field Name']}")
        for reference, code in BRANCH_REFERENCE.findall(branch):
            target = by.get(reference)
            if target is None:
                errors.append(
                    f"unresolved branch reference {reference}: {row['Variable / Field Name']}"
                )
                continue
            if code:
                if target["Field Type"] != "checkbox":
                    errors.append(f"checkbox syntax references non-checkbox field: {reference}")
                elif code not in parse_choices(
                    target["Choices, Calculations, OR Slider Labels"]
                ):
                    errors.append(f"invalid checkbox code {reference}({code})")

    required_overall = {
        "po_sufficiency",
        "po_suff_explain",
        "po_taxonomy_fit",
        "po_tax_issue",
        "po_tax_explain",
        "po_tax_other",
        "po_other_comment",
        "po_quote_permission",
        "po_nonpublic",
        "po_nonpublic_note",
    }
    if not required_overall <= set(by):
        errors.append("one or more overall assessment fields are missing")
    if parse_choices(by["po_sufficiency"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Sufficient",
        "2": "Partial",
        "3": "Insufficient",
    }:
        errors.append("public-entry sufficiency choices differ")
    if parse_choices(by["po_taxonomy_fit"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Fit",
        "2": "Partial Fit",
        "3": "No Fit",
    }:
        errors.append("taxonomy-fit choices differ")
    if by["po_taxonomy_fit"]["Field Label"] != (
        "Thinking about the actual project, how well do the available classification categories cover it?"
    ):
        errors.append("taxonomy-fit wording differs")
    if any(term in by["po_taxonomy_fit"]["Choices, Calculations, OR Slider Labels"] for term in (
        "Cannot assess", "Unclear from Register Entry", "Not enough information"
    )):
        errors.append("taxonomy fit contains a prohibited evidence-sufficiency option")
    if parse_choices(by["po_tax_issue"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Missing or inadequately represented category",
        "2": "Ambiguous or overlapping category boundaries",
        "5": "Other taxonomy problem",
    }:
        errors.append("taxonomy issue choices differ")
    fit_branch = "[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'"
    for name in ("po_tax_issue", "po_tax_explain"):
        if by[name]["Branching Logic (Show field only if...)"] != fit_branch:
            errors.append(f"taxonomy problem branching differs: {name}")
        if by[name]["Required Field?"] != "y":
            errors.append(f"taxonomy problem field is not required: {name}")
    if by["po_tax_other"]["Branching Logic (Show field only if...)"] != "[po_tax_issue(5)] = '1'":
        errors.append("other taxonomy explanation branching differs")
    if by["po_tax_other"]["Required Field?"] != "y":
        errors.append("other taxonomy explanation is not required")
    if by["po_suff_explain"]["Branching Logic (Show field only if...)"] != (
        "[po_sufficiency] = '2' or [po_sufficiency] = '3'"
    ) or by["po_suff_explain"]["Required Field?"] != "y":
        errors.append("public-entry sufficiency explanation logic differs")
    if parse_choices(by["po_nonpublic"]["Choices, Calculations, OR Slider Labels"]) != {
        "0": "No", "1": "Yes", "2": "Unsure"
    }:
        errors.append("project-knowledge choices differ")
    if by["po_nonpublic"]["Required Field?"] != "y":
        errors.append("project-knowledge gateway is not required")
    if by["po_nonpublic_note"]["Branching Logic (Show field only if...)"] != (
        "[po_nonpublic] = '1' or [po_nonpublic] = '2'"
    ):
        errors.append("project-knowledge note branching differs")
    if by["po_nonpublic_note"]["Required Field?"]:
        errors.append("project-knowledge note must remain optional")
    if not all(term in by["po_nonpublic_note"]["Field Label"].lower() for term in (
        "confidential", "non-public"
    )):
        errors.append("project-knowledge note lacks disclosure warning")
    for optional in ("po_other_comment", "po_quote_permission"):
        if by[optional]["Required Field?"]:
            errors.append(f"optional review field became required: {optional}")
    if parse_choices(by["po_tax_issue"]["Choices, Calculations, OR Slider Labels"]) != {
        "1": "Missing or inadequately represented category",
        "2": "Ambiguous or overlapping category boundaries",
        "5": "Other taxonomy problem",
    }:
        errors.append("taxonomy issue choices differ")
    if by["po_tax_other"]["Branching Logic (Show field only if...)"] != "[po_tax_issue(5)] = '1'":
        errors.append("Other taxonomy problem explanation logic differs")
    if "confidential" not in by["po_final_warning"]["Field Label"].lower():
        errors.append("final comments lack a confidentiality warning")
    if by["po_quote_permission"]["Form Name"] != "project_review":
        errors.append("quotation permission is not review-instance-specific")

    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {
        "version": builder.VERSION,
        "fields": len(rows),
        "forms": dict(form_counts),
        "production_maxima": {
            layer: value["maximum"] for layer, value in maxima.items()
        },
        "slot_capacity": builder.SLOT_CAPACITY,
    }


FIXTURE_STRUCTURAL_FIELDS = {
    "redcap_repeat_instrument",
    "redcap_repeat_instance",
    "owner_consent_complete",
    "project_review_complete",
}


def fixture_column_error(
    column: str, dictionary_by_name: Mapping[str, Mapping[str, str]]
) -> str | None:
    if column in FIXTURE_STRUCTURAL_FIELDS:
        return None
    dictionary_field = dictionary_by_name.get(column)
    if dictionary_field is not None:
        if dictionary_field["Field Type"] == "descriptive":
            return f"descriptive field is not importable: {column}"
        if dictionary_field["Field Type"] == "checkbox":
            return f"checkbox base variable is not importable: {column}"
        return None
    expanded_checkbox = re.fullmatch(r"([a-z][a-z0-9_]*)___(.+)", column)
    if expanded_checkbox:
        base_name, option_code = expanded_checkbox.groups()
        base_field = dictionary_by_name.get(base_name)
        if base_field is None or base_field["Field Type"] != "checkbox":
            return f"expanded checkbox column has no checkbox base field: {column}"
        if option_code not in parse_choices(
            base_field["Choices, Calculations, OR Slider Labels"]
        ):
            return f"expanded checkbox column has an invalid option code: {column}"
        return None
    return f"fixture column is not an importable REDCap field: {column}"


def validate_fixture(path: Path = builder.IMPORT_FIXTURE) -> dict[str, object]:
    dictionary = load_dictionary()
    by = _dictionary_by_name(dictionary)
    response_fields = _response_fields(dictionary)
    rows = load_fixture(path)
    errors: list[str] = []
    expected_header = [
        "owner_id",
        "redcap_repeat_instrument",
        "redcap_repeat_instance",
        *[
            row["Variable / Field Name"]
            for row in dictionary
            if row["Variable / Field Name"] != "owner_id"
            and row["Field Type"] not in {"descriptive", "checkbox"}
        ],
        "owner_consent_complete",
        "project_review_complete",
    ]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    if header != expected_header:
        errors.append("synthetic import header differs from long-format contract")
    if len(header) != len(set(header)):
        errors.append("synthetic import header contains duplicate columns")
    for column in header:
        column_error = fixture_column_error(column, by)
        if column_error:
            errors.append(column_error)
    descriptive_names = {
        row["Variable / Field Name"]
        for row in dictionary
        if row["Field Type"] == "descriptive"
    }
    checkbox_names = {
        row["Variable / Field Name"]
        for row in dictionary
        if row["Field Type"] == "checkbox"
    }
    if descriptive_names & set(header):
        errors.append("synthetic import header contains descriptive fields")
    if checkbox_names & set(header):
        errors.append("synthetic import header contains checkbox base variables")
    raw = path.read_text(encoding="utf-8")
    if EMAIL.search(raw):
        errors.append("synthetic fixture contains an email address")
    if REAL_RECORD_ID.search(raw):
        errors.append("synthetic fixture contains a real-format DEA Record ID")
    for forbidden in ("Researcher name", "participant name", "contact email"):
        if forbidden.lower() in raw.lower():
            errors.append(f"synthetic fixture contains forbidden personal-data wording: {forbidden}")

    owner_rows = [row for row in rows if not row["redcap_repeat_instrument"]]
    repeat_rows = [
        row for row in rows if row["redcap_repeat_instrument"] == "project_review"
    ]
    if len(owner_rows) != 3 or len(repeat_rows) != 19 or len(rows) != 22:
        errors.append(
            f"synthetic fixture counts differ: owners={len(owner_rows)}, "
            f"assignments={len(repeat_rows)}, rows={len(rows)}"
        )
    if any(
        row["redcap_repeat_instrument"] not in {"", "project_review"} for row in rows
    ):
        errors.append("fixture contains an unexpected repeat instrument")
    by_owner: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_owner[row["owner_id"]].append(row)
    expected = {"OWNER_TEST_001": 1, "OWNER_TEST_002": 3, "OWNER_TEST_003": 15}
    if set(by_owner) != set(expected):
        errors.append("synthetic owner IDs differ")
    for owner_id, assignment_count in expected.items():
        items = by_owner.get(owner_id, [])
        owners = [row for row in items if not row["redcap_repeat_instrument"]]
        reviews = [row for row in items if row["redcap_repeat_instrument"]]
        if len(owners) != 1:
            errors.append(f"{owner_id} does not have exactly one owner row")
        if len(reviews) != assignment_count:
            errors.append(f"{owner_id} assignment count differs")
        instances = [int(row["redcap_repeat_instance"]) for row in reviews]
        if instances != list(range(1, assignment_count + 1)):
            errors.append(f"{owner_id} repeat instances are not 1...N")
    if len({row["assignment_id"] for row in repeat_rows}) != len(repeat_rows):
        errors.append("synthetic assignment IDs are not unique")
    if any(not re.fullmatch(r"ASSIGN_TEST_\d{3}", row["assignment_id"]) for row in repeat_rows):
        errors.append("synthetic assignment IDs are not neutral participant-safe references")
    for row in owner_rows:
        if row["redcap_repeat_instance"]:
            errors.append("owner row has a repeat instance")
        if row["participant_info_ver"] != builder.PARTICIPANT_INFO_VERSION:
            errors.append("owner row participant-information candidate token differs")
        if row["owner_consent_complete"] != "0":
            errors.append("owner row is not initially incomplete")
    for row in repeat_rows:
        if row["project_review_complete"] != "0":
            errors.append("pre-created review row is not initially incomplete")
        for name in (
            "assignment_id",
            "source_record_id",
            "project_title",
            "datasets_used",
            "source_pop_ver",
            "production_ver",
            "taxonomy_ver",
            "proposal_output_sha256",
            "review_instr_ver",
            "taxonomy_display_ver",
        ):
            if not row[name]:
                errors.append(f"pre-created repeat row lacks {name}: {row['assignment_id']}")
    for row in rows:
        for name in response_fields:
            if row.get(name):
                errors.append(
                    f"participant response field is pre-filled: {row['owner_id']}:{name}"
                )
    # All populated proposed labels must have their matching traced definition.
    display = yaml.safe_load(builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8"))
    definition_by_key = {
        builder.display_key(item): _normalise(item["owner_microdefinition"])
        for item in builder.all_display_entries(display)
    }
    canonical_tags = [
        item for item in display["labels"] if item["owner_layer"] == "tag"
    ]
    for row in repeat_rows:
        for prefix, owner_layer, capacity in (
            ("d", "domain", builder.DOMAIN_SLOTS),
            ("p", "purpose", builder.PURPOSE_SLOTS),
            ("t", "tag", builder.TAG_SLOTS),
        ):
            for index in range(1, capacity + 1):
                label = row[f"prop_{prefix}{index:02d}_label"]
                definition = row[f"prop_{prefix}{index:02d}_def"]
                if bool(label) != bool(definition):
                    errors.append(f"label/definition population differs: {row['assignment_id']}")
                key = (owner_layer, label)
                if label and _normalise(definition) != definition_by_key.get(key):
                    errors.append(f"fixture definition drift: {row['assignment_id']}:{key}")
        for index, item in enumerate(canonical_tags, 1):
            stem = f"t{index:02d}"
            if row[f"prop_{stem}_label"] != item["canonical_label"]:
                errors.append(f"fixture does not populate canonical tag {stem}: {row['assignment_id']}")
            if _normalise(row[f"prop_{stem}_def"]) != _normalise(
                item["owner_microdefinition"]
            ):
                errors.append(f"fixture tag definition drift: {row['assignment_id']}:{stem}")
            if row[f"prop_{stem}_status"] not in {"0", "1"}:
                errors.append(f"fixture tag status is not Applied/Not applied: {row['assignment_id']}:{stem}")
    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {
        "owners": len(owner_rows),
        "assignments": len(repeat_rows),
        "rows": len(rows),
        "columns": len(header),
        "assignments_by_owner": expected,
    }


def _checkbox_selected(row: Mapping[str, object], name: str, count: int) -> list[str]:
    selected: list[str] = []
    for code in range(1, count + 1):
        code_text = str(code)
        if any(
            str(row.get(key, "")) == "1"
            for key in (f"{name}___{code_text}", f"{name}({code_text})")
        ):
            selected.append(code_text)
    return selected


def analytical_completion_missing(
    review: Mapping[str, object], owner: Mapping[str, object]
) -> list[str]:
    """Return every unmet analytical-completion requirement."""

    missing: list[str] = []
    if str(owner.get("intended_recipient", "")) != "1":
        missing.append("joined_intended_recipient")
    if str(owner.get("owner_consent", "")) != "1":
        missing.append("joined_owner_consent")
    for prefix, capacity in (("d", builder.DOMAIN_SLOTS), ("p", builder.PURPOSE_SLOTS)):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            if not str(review.get(f"prop_{stem}_label", "")).strip():
                continue
            fit = str(review.get(f"po_{stem}_fit", ""))
            visibility = str(review.get(f"po_{stem}_vis", ""))
            if fit not in {"1", "2", "3"}:
                missing.append(f"po_{stem}_fit")
            if visibility not in {"2", "1", "0", "3"}:
                missing.append(f"po_{stem}_vis")
            if (fit in {"2", "3"} or visibility in {"1", "0", "3"}) and not str(
                review.get(f"po_{stem}_basis", "")
            ).strip():
                missing.append(f"po_{stem}_basis")
    for index in range(1, builder.TAG_SLOTS + 1):
        stem = f"t{index:02d}"
        correctness = str(review.get(f"po_{stem}_correct", ""))
        visibility = str(review.get(f"po_{stem}_vis", ""))
        if correctness not in {"1", "0", "2"}:
            missing.append(f"po_{stem}_correct")
        if visibility not in {"2", "1", "0", "3"}:
            missing.append(f"po_{stem}_vis")
        if (correctness in {"0", "2"} or visibility in {"1", "0", "3"}) and not str(
            review.get(f"po_{stem}_basis", "")
        ).strip():
            missing.append(f"po_{stem}_basis")
    missing_config = (
        ("po_miss_domain", "po_miss_domains", "po_miss_domain_basis", 11),
        ("po_miss_purpose", "po_miss_purposes", "po_miss_purpose_basis", 7),
        ("po_miss_tag", "po_miss_tags", "po_miss_tag_basis", 2),
    )
    for gateway, menu, basis, count in missing_config:
        gateway_value = str(review.get(gateway, ""))
        if gateway_value not in {"1", "0", "2"}:
            missing.append(gateway)
        selected = _checkbox_selected(review, menu, count)
        if gateway_value == "1" and not selected:
            missing.append(menu)
        if selected and not str(review.get(basis, "")).strip():
            missing.append(basis)
    sufficiency = str(review.get("po_sufficiency", ""))
    if sufficiency not in {"1", "2", "3"}:
        missing.append("po_sufficiency")
    if sufficiency in {"2", "3"} and not str(review.get("po_suff_explain", "")).strip():
        missing.append("po_suff_explain")
    if str(review.get("po_nonpublic", "")) not in {"0", "1", "2"}:
        missing.append("po_nonpublic")
    taxonomy_fit = str(review.get("po_taxonomy_fit", ""))
    if taxonomy_fit not in {"1", "2", "3"}:
        missing.append("po_taxonomy_fit")
    issue_codes = _checkbox_selected(review, "po_tax_issue", 5)
    approved_issues = [code for code in issue_codes if code in {"1", "2", "5"}]
    if taxonomy_fit in {"2", "3"}:
        if not approved_issues:
            missing.append("po_tax_issue")
        if not str(review.get("po_tax_explain", "")).strip():
            missing.append("po_tax_explain")
    if "5" in approved_issues and not str(review.get("po_tax_other", "")).strip():
        missing.append("po_tax_other")
    return missing


def prepare_long_export(
    rows: Iterable[Mapping[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Split and join a REDCap long export without filtering consent on repeat rows."""

    materialised = [dict(row) for row in rows]
    owner_rows = [
        row for row in materialised if not str(row.get("redcap_repeat_instrument", ""))
    ]
    review_rows = [
        row
        for row in materialised
        if row.get("redcap_repeat_instrument") == "project_review"
    ]
    owners = {str(row.get("owner_id")): row for row in owner_rows}
    response_fields = _response_fields(load_dictionary()) - OWNER_RESPONSE_FIELDS
    joined: list[dict[str, object]] = []
    for review in review_rows:
        owner = owners.get(str(review.get("owner_id")), {})
        item = dict(review)
        item["joined_intended_recipient"] = owner.get("intended_recipient", "")
        item["joined_owner_consent"] = owner.get("owner_consent", "")
        item["joined_owner_consent_complete"] = owner.get(
            "owner_consent_complete", ""
        )
        has_response = any(str(review.get(name, "")).strip() for name in response_fields)
        review_status = str(review.get("project_review_complete", ""))
        completion_missing = analytical_completion_missing(review, owner)
        item["offered"] = True
        item["untouched"] = not has_response
        item["partial"] = has_response and bool(completion_missing)
        item["analytically_complete"] = not completion_missing
        item["submitted"] = review_status == "2"
        item["analytical_completion_missing"] = completion_missing
        item["assignment_response_state"] = (
            "untouched"
            if not has_response
            else ("analytically_complete" if not completion_missing else "partial")
        )
        item["substantive_analysis_eligible"] = item["analytically_complete"]
        joined.append(item)
    return owner_rows, joined


def validate_long_model() -> dict[str, int]:
    fixture = load_fixture()
    owner_rows, joined = prepare_long_export(fixture)
    errors: list[str] = []
    if len(owner_rows) != 3 or len(joined) != 19:
        errors.append("fixture split does not preserve owner/repeat rows")
    if any(row["assignment_response_state"] != "untouched" for row in joined):
        errors.append("untouched pre-created assignments are not retained as incomplete")
    if any(row["substantive_analysis_eligible"] for row in joined):
        errors.append("blank synthetic participant responses are analysis-eligible")

    synthetic = [dict(row) for row in fixture]
    owner = next(row for row in synthetic if row["owner_id"] == "OWNER_TEST_001" and not row["redcap_repeat_instrument"])
    review = next(row for row in synthetic if row["owner_id"] == "OWNER_TEST_001" and row["redcap_repeat_instrument"])
    owner.update(
        {
            "intended_recipient": "1",
            "owner_consent": "1",
            "owner_consent_complete": "2",
        }
    )
    review["project_review_complete"] = "2"
    review["po_sufficiency"] = "1"
    review["po_nonpublic"] = "0"
    review["po_taxonomy_fit"] = "1"
    review["po_miss_domain"] = "0"
    review["po_miss_purpose"] = "0"
    review["po_miss_tag"] = "0"
    for prefix, capacity in (
        ("d", builder.DOMAIN_SLOTS),
        ("p", builder.PURPOSE_SLOTS),
    ):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            if review.get(f"prop_{stem}_label"):
                review[f"po_{stem}_fit"] = "1"
                review[f"po_{stem}_vis"] = "2"
    for index in range(1, builder.TAG_SLOTS + 1):
        stem = f"t{index:02d}"
        review[f"po_{stem}_correct"] = "1"
        review[f"po_{stem}_vis"] = "2"
    _, joined_synthetic = prepare_long_export(synthetic)
    test_review = next(
        row for row in joined_synthetic if row["owner_id"] == "OWNER_TEST_001"
    )
    if test_review["joined_owner_consent"] != "1":
        errors.append("owner consent was not joined onto the repeated review")
    if not test_review["substantive_analysis_eligible"]:
        errors.append("joined consent/completion rule rejects a complete synthetic review")
    if not test_review["submitted"]:
        errors.append("submitted state was not derived from project_review_complete")
    if test_review["analytical_completion_missing"]:
        errors.append("complete synthetic review has unmet analytical requirements")
    if review.get("owner_consent"):
        errors.append("test incorrectly populated owner_consent on the repeated row")
    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {"owner_rows": len(owner_rows), "review_rows": len(joined)}


def validate_documentation() -> dict[str, object]:
    spec = builder.SPEC.read_text(encoding="utf-8")
    config = builder.LIVE_CONFIG.read_text(encoding="utf-8")
    reference = builder.TAXONOMY_REFERENCE.read_text(encoding="utf-8")
    errors: list[str] = []
    required_spec = (
        "one pseudonymous REDCap record per owner",
        "one participant-specific Survey Queue link",
        "Do **not** filter repeated rows directly",
        "owner_microdefinition",
        "owner_reference_definition",
        "approved_by_author",
        "Candidate 0.2 remains unchanged",
        "Field-level traceability",
        "substantial instrument architecture change",
        "2, Clearly visible | 1, Partly visible | 0, Not visible | 3, Unsure",
        "Could the correct status for this tag reasonably be determined",
        "Both canonical cross-cutting tags are reviewed on every assignment",
        "Analytically complete",
        "Submitted",
        "Review reference",
        "project_owner_taxonomy_human_review_v1.csv",
        "technically ready for controlled synthetic import",
        "unique display key is `(owner_layer, canonical_label)`",
        "purpose-cardinality/taxonomy issue",
    )
    for phrase in required_spec:
        if phrase not in spec:
            errors.append(f"specification omits: {phrase}")
    required_config = (
        "PID 9149",
        f"Candidate source commit: `{builder.CANDIDATE_SOURCE_COMMIT}`",
        "Classic/non-longitudinal",
        "[assignment_id] — [project_title]",
        "Repeat the Survey disabled",
        "[owner_id] <> ''",
        "[owner_consent_complete] = '2' and [owner_consent] = '1' and [intended_recipient] = '1'",
        "Project Review Auto Start disabled",
        "participant/record-specific Survey Queue URL",
        "desktop and mobile",
        "untouched pre-created assignment",
        "no real records",
        "Your response has been recorded under the reference [assignment_id]",
        "at-least-one behaviour as a live-QA assertion",
        "Both canonical tag blocks appear on every repeat",
        "all 22 taxonomy definitions are author-approved",
        "@MAXCHECKED=2",
    )
    for phrase in required_config:
        if phrase not in config:
            errors.append(f"live configuration omits: {phrase}")
    required_reference = (
        f"Document version: {builder.TAXONOMY_REFERENCE_VERSION}",
        f"Date: {builder.TAXONOMY_REFERENCE_DATE}",
        "How to use this guide",
        "Use this guide when deciding whether each proposed classification fits the actual project and how clearly its basis is visible in the public project title and listed datasets. The short definitions summarise how the framework uses each category.",
        "A project may be assigned more than one Research Domain where each is substantively part of the research; the domains are not ranked.",
        "The framework assigns no more than two Analytical Purposes to a project",
        "More than one Analytical Purpose may apply.",
        "About ‘Unclear from Register Entry’",
        "This label may appear where the classification judged that the public project title and listed datasets did not provide enough information to assign a substantive Research Domain or infer an Analytical Purpose. Your view on whether that judgement was reasonable is itself useful evidence for the validation study.",
        "The framework’s own definitions are:",
        "mortality where health is the research object",
        "mortality as a demographic outcome",
        "data infrastructure, linkage, measurement or methodology is itself the primary research object, not merely a tool used to answer another substantive question",
        "without primarily testing an exposure–outcome relationship",
        "excludes deliberate policy or programme exposure",
        "specific named policy, programme, regulation or intervention",
        "Routine subgroup breakdowns do not qualify, and socioeconomic or deprivation-based inequality alone is insufficient",
        "Research does not qualify merely because its data cover the pandemic period or because COVID-19 is mentioned incidentally",
    )
    for phrase in required_reference:
        if phrase not in reference:
            errors.append(f"taxonomy reference omits: {phrase}")
    display = yaml.safe_load(builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8"))
    for item in builder.all_display_entries(display):
        if item["owner_reference_definition"] not in reference:
            errors.append(
                f"taxonomy reference does not use approved reference definition: "
                f"{builder.display_key(item)}"
            )
    forbidden_reference_phrases = (
        "project_owner_",
        "taxonomy_data_dictionary",
        ".yaml",
        ".csv",
        ".md",
        "missing-label menu",
        "pending_human_approval",
        "approved_by_author",
        "Status:",
        "generated from",
        "Human approval",
        "all 22 definitions",
    )
    for phrase in forbidden_reference_phrases:
        if phrase.lower() in reference.lower():
            errors.append(f"participant taxonomy reference exposes audit scaffolding: {phrase}")
    if "taxonomy_data_dictionary.yaml" not in spec or "review_status: approved_by_author" not in spec:
        errors.append("technical taxonomy provenance is not retained outside participant content")
    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {"specification": "passed", "live_configuration": "passed", "reference": "passed"}


def validate_response_specifications() -> dict[str, object]:
    errors: list[str] = []
    with builder.FIELD_SPEC.open(encoding="utf-8-sig", newline="") as handle:
        field_rows = {row["variable"]: row for row in csv.DictReader(handle)}
    with builder.EXPORT_SPEC.open(encoding="utf-8-sig", newline="") as handle:
        export_rows = {row["variable"]: row for row in csv.DictReader(handle)}
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    expected_choices = {
        "2": "Clearly visible",
        "1": "Partly visible",
        "0": "Not visible",
        "3": "Unsure",
    }
    visibility_spec = branch.get("proposed_slot_visibility", {})
    if visibility_spec.get("choices") != expected_choices:
        errors.append("branching specification visibility choices differ")
    queue_condition = branch.get("survey_queue", {}).get("project_review", {}).get("condition", "")
    if "ack_pref" in queue_condition:
        errors.append("ack_pref incorrectly affects Survey Queue access")
    if branch.get("tag_reviews", {}).get("always_review_both") is not True:
        errors.append("branching specification does not require both tag reviews")
    if branch.get("missing_label_branching", {}).get("at_least_one_checkbox_requires_live_qa") is not True:
        errors.append("branching specification overclaims checkbox at-least-one enforcement")
    missing_spec = branch.get("missing_label_branching", {})
    if missing_spec.get("purpose_guidance_field") != "po_miss_purpose_guidance":
        errors.append("branching specification omits missing-purpose guidance")
    if missing_spec.get("purpose_max_checked_annotation") != "@MAXCHECKED=2":
        errors.append("branching specification omits missing-purpose maximum")
    if "cardinality/taxonomy issue" not in missing_spec.get("purpose_cardinality_analysis", ""):
        errors.append("branching specification omits corrected-purpose cardinality treatment")
    if field_rows.get("po_miss_purposes", {}).get("annotation") != "@MAXCHECKED=2":
        errors.append("field specification omits missing-purpose @MAXCHECKED=2")
    if "cardinality/taxonomy issue" not in export_rows.get("po_miss_purposes", {}).get("notes", ""):
        errors.append("expected export omits corrected-purpose cardinality treatment")
    if "project_review_complete = 2" not in branch.get("analytical_completion", {}).get(
        "submitted_is_separate", ""
    ):
        errors.append("branching specification conflates submission and analytical completion")
    for prefix, capacity in (
        ("d", builder.DOMAIN_SLOTS),
        ("p", builder.PURPOSE_SLOTS),
        ("t", builder.TAG_SLOTS),
    ):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            visibility = f"po_{stem}_vis"
            basis = f"po_{stem}_basis"
            if "2 Clearly visible" not in field_rows.get(visibility, {}).get("notes", ""):
                errors.append(f"field specification omits visibility coding: {visibility}")
            if "Partly visible/Not visible/Unsure" not in field_rows.get(basis, {}).get("notes", ""):
                errors.append(f"field specification omits basis triggers: {basis}")
            if "2=Clearly visible" not in export_rows.get(visibility, {}).get("notes", ""):
                errors.append(f"expected export omits visibility coding: {visibility}")
            if "Partly visible/Not visible/Unsure" not in export_rows.get(basis, {}).get("notes", ""):
                errors.append(f"expected export omits basis triggers: {basis}")
    if errors:
        raise OwnerCandidate03Error("\n".join(errors))
    return {"visibility_fields": 8, "basis_fields": 8}


def check_v02_unchanged() -> int:
    builder.check_v02_hashes()
    return len(builder.V02_HASHES)


def validate_frozen_sources() -> dict[str, str]:
    builder.check_frozen_sources()
    return {
        "taxonomy_sha256": builder.TAXONOMY_SHA256,
        "production_output_sha256": builder.FROZEN_OUTPUT_SHA256,
    }


def check() -> dict[str, object]:
    return {
        "version": builder.VERSION,
        "dictionary": validate_dictionary(),
        "taxonomy_display": validate_display_source(),
        "taxonomy_human_review": validate_taxonomy_human_review(),
        "fixture": validate_fixture(),
        "long_model": validate_long_model(),
        "documentation": validate_documentation(),
        "response_specifications": validate_response_specifications(),
        "frozen_sources": validate_frozen_sources(),
        "candidate_0_2_hashes_checked": check_v02_unchanged(),
        "status": "passed_offline_unfrozen_live_qa_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    print(yaml.safe_dump(check(), sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
