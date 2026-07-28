from __future__ import annotations

import csv
from collections import Counter

import yaml

from scripts import build_project_owner_redcap_candidate_0_4 as builder
from scripts import validate_project_owner_redcap_candidate_0_4 as validator


def dictionary_rows():
    return validator.load_dictionary()


def dictionary_by_name():
    return {row["Variable / Field Name"]: row for row in dictionary_rows()}


def affirmative_owner():
    owner = {name: "1" for name in builder.CONSENT_NAMES}
    owner.update(
        {
            "owner_id": "OWNER_TEST_001",
            "intended_recipient": "1",
            "consent_items_complete": "1",
            "owner_consent": "1",
            "owner_consent_complete": "2",
        }
    )
    return owner


def test_candidate_0_4_full_offline_check_passes():
    assert validator.check()["status"] == "passed"


def test_exact_two_instruments_and_counts():
    rows = dictionary_rows()
    assert tuple(dict.fromkeys(row["Form Name"] for row in rows)) == (
        "owner_consent",
        "project_review",
    )
    assert Counter(row["Form Name"] for row in rows) == Counter(
        {"owner_consent": 22, "project_review": 96}
    )
    assert len(rows) == 118


def test_ten_unique_owner_level_consent_items_match_ethics_document():
    by = dictionary_by_name()
    assert len(builder.CONSENT_NAMES) == len(set(builder.CONSENT_NAMES)) == 10
    document = set(validator.participant_doc_paragraphs())
    for name, wording in builder.CONSENT_ITEMS:
        assert by[name]["Form Name"] == "owner_consent"
        assert validator.normalise_text(by[name]["Field Label"]) == validator.normalise_text(
            wording
        )
        assert validator.normalise_text(wording) in document
        assert by[name]["Branching Logic (Show field only if...)"] == (
            "[intended_recipient] = '1'"
        )
    assert not set(builder.CONSENT_NAMES) & {
        row["Variable / Field Name"]
        for row in dictionary_rows()
        if row["Form Name"] == "project_review"
    }


def test_all_confirmed_logic_requires_every_item_and_clearing_revokes_validity():
    owner = affirmative_owner()
    assert validator.consent_items_complete(owner)
    assert validator.valid_owner_consent(owner)
    for name in builder.CONSENT_NAMES:
        omitted = dict(owner)
        omitted[name] = ""
        assert not validator.consent_items_complete(omitted)
        assert not validator.valid_owner_consent(omitted)
        cleared = dict(owner)
        cleared[name] = "0"
        assert not validator.valid_owner_consent(cleared)


def test_all_confirmed_calc_and_queue_conditions_are_exact():
    by = dictionary_by_name()
    assert by["consent_items_complete"]["Field Type"] == "calc"
    assert (
        by["consent_items_complete"]["Choices, Calculations, OR Slider Labels"]
        == builder.ALL_CONFIRMED_EXPRESSION
    )
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    assert branch["survey_queue"]["project_review"]["condition"] == (
        builder.QUEUE_CONDITION
    )
    assert "ack_pref" not in builder.QUEUE_CONDITION


def test_active_decline_and_wrong_recipient_paths_remain_available():
    by = dictionary_by_name()
    assert by["owner_consent"]["Branching Logic (Show field only if...)"] == (
        "[intended_recipient] = '1'"
    )
    assert validator.parse_choices(
        by["owner_consent"]["Choices, Calculations, OR Slider Labels"]
    ) == {
        "1": "Yes, I agree to take part",
        "0": "No, I do not wish to take part",
    }
    assert not validator.valid_owner_consent(
        {"intended_recipient": "1", "owner_consent": "0"}
    )
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    assert branch["stop_actions_manual_after_import"]["owner_consent"] == "No"
    assert branch["stop_actions_manual_after_import"]["intended_recipient"] == "No"


def test_acknowledgement_is_optional_and_only_after_valid_affirmative_path():
    row = dictionary_by_name()["ack_pref"]
    assert row["Required Field?"] == ""
    assert row["Branching Logic (Show field only if...)"] == (
        "[intended_recipient] = '1' and [consent_items_complete] = '1' and "
        "[owner_consent] = '1'"
    )
    assert validator.parse_choices(row["Choices, Calculations, OR Slider Labels"]) == {
        "1": "Yes, I would like to be acknowledged by name",
        "0": "No, I would prefer not to be named",
        "2": "I would prefer to decide later. Please contact me about this",
    }
    label = row["Field Label"]
    assert label == builder.ACKNOWLEDGEMENT_LABEL
    assert "participation will not be disclosed" not in label.lower()


def test_both_canonical_participant_documents_are_pinned_and_aligned():
    assert builder.sha256(builder.PARTICIPANT_SOURCE) == builder.PARTICIPANT_SOURCE_SHA256
    assert builder.PARTICIPANT_SOURCE.stat().st_size == builder.PARTICIPANT_SOURCE_SIZE
    assert builder.sha256(builder.QUESTIONNAIRE_SOURCE) == builder.QUESTIONNAIRE_SOURCE_SHA256
    assert builder.QUESTIONNAIRE_SOURCE.stat().st_size == builder.QUESTIONNAIRE_SOURCE_SIZE
    assert validator.validate_participant_documents(dictionary_by_name()) == []


def test_questionnaire_appendix_visibility_and_q11b_wording_are_exact():
    paragraphs = validator.questionnaire_doc_paragraphs()
    assert validator.normalise_text(builder.APPENDIX_B_CONSENT_WORDING) in paragraphs
    for question in ("Q3d.", "Q4d."):
        assert "or unclear" in validator._documented_question_label(paragraphs, question)
    q11_options = validator._question_following(paragraphs, "Q11b.", "Response options:")
    assert q11_options == (
        "Response options: Missing or inadequately represented category / Ambiguous or "
        "overlapping category boundaries / Other taxonomy problem"
    )
    assert validator.parse_choices(
        dictionary_by_name()["po_tax_issue"]["Choices, Calculations, OR Slider Labels"]
    )["1"] == "Missing or inadequately represented category"


def test_obsolete_per_review_quotation_permission_is_removed():
    names = {row["Variable / Field Name"] for row in dictionary_rows()}
    assert "po_quote_permission" not in names
    for path in (
        builder.DICTIONARY,
        builder.FIELD_SPEC,
        builder.BRANCH_SPEC,
        builder.EXPORT_SPEC,
        builder.IMPORT_FIXTURE,
        builder.FORMATTING_AUDIT,
    ):
        assert "po_quote_permission" not in path.read_text(encoding="utf-8-sig")
    documentation = builder.SPEC.read_text(encoding="utf-8")
    assert "exact proposed wording and context" in documentation
    assert "used only after written agreement" in documentation
    questionnaire = "\n".join(validator.questionnaire_doc_paragraphs()).lower()
    assert "q13" not in questionnaire
    assert "quotation permission" not in questionnaire
    assert "may the study use a short anonymised quotation" not in questionnaire


def test_final_warning_immediately_follows_comments_without_quote_dependency():
    rows = dictionary_rows()
    names = [row["Variable / Field Name"] for row in rows]
    assert names[-2:] == ["po_other_comment", "po_final_warning"]
    warning = dictionary_by_name()["po_final_warning"]
    assert "quotation permission" not in warning["Field Label"].lower()
    assert "po_quote_permission" not in warning["Branching Logic (Show field only if...)"]


def test_fixture_preserves_three_owner_nineteen_review_structure_and_blank_consent():
    rows, header = validator.read_csv(builder.IMPORT_FIXTURE)
    assert len(rows) == 22
    owners = [row for row in rows if row["redcap_repeat_instrument"] == ""]
    reviews = [row for row in rows if row["redcap_repeat_instrument"] == "project_review"]
    assert len(owners) == 3
    assert len(reviews) == 19
    consent_fields = [
        *builder.CONSENT_NAMES,
        "consent_items_complete",
        "intended_recipient",
        "owner_consent",
        "ack_pref",
    ]
    assert set(consent_fields) <= set(header)
    assert all(not row[name] for row in rows for name in consent_fields)
    assert all(row["owner_consent_complete"] == "0" for row in owners)
    assert all(row["owner_instr_ver"] == builder.VERSION for row in owners)
    assert all(row["review_instr_ver"] == builder.VERSION for row in reviews)


def test_long_export_joins_composite_valid_consent_from_nonrepeating_owner_row():
    owner = affirmative_owner()
    review = {
        "owner_id": owner["owner_id"],
        "redcap_repeat_instrument": "project_review",
        "redcap_repeat_instance": "1",
    }
    owner_rows, reviews = validator.prepare_long_export([owner, review])
    assert len(owner_rows) == len(reviews) == 1
    joined = reviews[0]
    assert joined["joined_intended_recipient"] == "1"
    assert joined["joined_consent_items_complete"] == "1"
    assert joined["joined_owner_consent"] == "1"
    assert joined["joined_owner_consent_complete"] == "2"
    assert not any(review.get(name) for name in builder.CONSENT_NAMES)
    invalid = dict(owner)
    invalid[builder.CONSENT_NAMES[0]] = ""
    _, invalid_reviews = validator.prepare_long_export([invalid, review])
    assert "joined_consent_items_complete" in invalid_reviews[0][
        "analytical_completion_missing"
    ]


def test_no_direct_identifier_field_is_introduced():
    names = {row["Variable / Field Name"] for row in dictionary_rows()}
    assert not {
        name
        for name in names
        if any(token in name.split("_") for token in ("name", "email", "affiliation"))
    }


def test_project_review_is_predecessor_equivalent_except_documented_removal():
    # validate_dictionary performs the exact row-level predecessor comparison.
    assert validator.validate_dictionary()["forms"]["project_review"] == 96
