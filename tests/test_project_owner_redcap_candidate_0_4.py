from __future__ import annotations

import csv
import hashlib
import html
import inspect
import re
import zipfile
from collections import Counter
from pathlib import Path

import yaml

from analysis import llm_theme_analysis_v3 as classifier
from dashboard import taxonomy as dashboard_taxonomy
from scripts import build_project_owner_redcap_candidate_0_4 as builder
from scripts import update_project_owner_participant_documents_candidate_0_4 as updater
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
        {"owner_consent": 22, "project_review": 101}
    )
    assert len(rows) == 123


def test_import_ready_dictionary_is_exact_generator_output():
    assert builder.IMPORT_READY_DICTIONARY.read_bytes() == builder.DICTIONARY.read_bytes()


def test_read_only_requiredness_descriptive_weight_and_provenance_are_repaired():
    rows = dictionary_rows()
    by = dictionary_by_name()
    assert all(
        not row["Required Field?"]
        for row in rows
        if "@READONLY-SURVEY" in row["Field Annotation"]
    )
    for row in rows:
        if row["Field Type"] != "descriptive":
            continue
        label = row["Field Label"]
        assert label.count('style="font-weight:400;"') == 1
        assert "<p" not in label.lower()
    assert by["public_register_url"]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"
    assert by["po_register_provenance"]["Field Label"] == builder.normal_weight_descriptive(
        builder.REGISTER_PROVENANCE
    )
    assert builder.APPROVED_PRIVACY_WORDING in validator.plain_redcap_label(
        by["po_privacy"]["Field Label"]
    )


def test_missing_label_order_requiredness_branching_and_limits_are_repaired():
    rows = dictionary_rows()
    by = dictionary_by_name()
    names = [row["Variable / Field Name"] for row in rows]
    expected_groups = {
        "domain": [
            "po_miss_domain_reference", "po_miss_domain_reminder", "po_miss_domains",
            "po_miss_domain_basis", "po_miss_domain",
        ],
        "purpose": [
            "po_miss_purpose_reference", "po_miss_purpose_guidance",
            "po_miss_purpose_reminder", "po_miss_purposes",
            "po_miss_purpose_basis", "po_miss_purpose",
        ],
        "tag": [
            "po_miss_tag_reference", "po_miss_tags", "po_miss_tag_basis", "po_miss_tag",
        ],
    }
    for group in expected_groups.values():
        positions = [names.index(name) for name in group]
        assert positions == list(range(positions[0], positions[0] + len(group)))
    for gate, label in builder.GATE_LABELS.items():
        assert by[gate]["Field Label"] == label
    for layer, reference in builder.REFERENCE_FIELD_BY_LAYER.items():
        assert by[reference]["Section Header"] == builder.REFERENCE_SECTION_BY_LAYER[layer]
    for menu, gate in (
        ("po_miss_domains", "po_miss_domain"),
        ("po_miss_purposes", "po_miss_purpose"),
        ("po_miss_tags", "po_miss_tag"),
    ):
        assert by[menu]["Branching Logic (Show field only if...)"] == ""
        assert by[menu]["Required Field?"] == ""
        assert by[gate]["Required Field?"] == "y"
        assert names.index(gate) > names.index(menu)
    assert by["po_miss_purpose_guidance"]["Branching Logic (Show field only if...)"] == ""
    assert by["po_miss_purposes"]["Field Annotation"] == "@MAXCHECKED=2"
    assert "up to two" in by["po_miss_purposes"]["Field Label"].lower()
    assert "@MAXCHECKED" not in by["po_miss_domains"]["Field Annotation"]
    assert "@MAXCHECKED" not in by["po_miss_tags"]["Field Annotation"]
    for basis in ("po_miss_domain_basis", "po_miss_purpose_basis", "po_miss_tag_basis"):
        assert by[basis]["Required Field?"] == ""
        assert "(1)] = '1'" in by[basis]["Branching Logic (Show field only if...)"]


def test_branching_and_action_tag_references_resolve():
    rows = dictionary_rows()
    names = {row["Variable / Field Name"] for row in rows}
    for row in rows:
        for column in (
            "Branching Logic (Show field only if...)",
            "Field Annotation",
        ):
            references = set(re.findall(r"\[([A-Za-z][A-Za-z0-9_]*)", row[column]))
            assert references <= names, (row["Variable / Field Name"], column, references - names)


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
    for path in (builder.PARTICIPANT_SOURCE, builder.QUESTIONNAIRE_SOURCE):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None


def test_classification_orientation_matches_questionnaire_and_precedes_overview():
    by = dictionary_by_name()
    rows = dictionary_rows()
    names = [row["Variable / Field Name"] for row in rows]
    assert names.count("po_intro") == 1
    assert by["po_intro"]["Form Name"] == "project_review"
    assert validator.plain_redcap_label(by["po_intro"]["Field Label"]) == (
        validator.normalise_text(" ".join(builder.CLASSIFICATION_INTRO_PARAGRAPHS))
    )
    paragraphs = validator.questionnaire_doc_paragraphs()
    intro = [validator.normalise_text(item) for item in builder.CLASSIFICATION_INTRO_PARAGRAPHS]
    start = paragraphs.index(intro[0])
    overview = next(
        index
        for index, paragraph in enumerate(paragraphs)
        if paragraph.startswith("Read-only classification overview:")
    )
    assert paragraphs[start : start + len(intro)] == intro
    assert start + len(intro) == overview
    assert names.index("datasets_used") < names.index("po_intro") < names.index(
        "po_classification_overview"
    )
    assert "save & return later" not in by["po_intro"]["Field Label"].lower()
    assert builder.CLASSIFICATION_INTRO_PARAGRAPHS.count(
        builder.SUBSTANTIVE_FOCUS_PARAGRAPH
    ) == 1
    assert by["po_intro"]["Field Label"].count(
        f"<strong>{builder.SUBSTANTIVE_FOCUS_PHRASE}</strong>"
    ) == 1
    assert validator.validate_exact_docx_bold_phrase(
        builder.QUESTIONNAIRE_SOURCE,
        builder.SUBSTANTIVE_FOCUS_PARAGRAPH,
        builder.SUBSTANTIVE_FOCUS_PHRASE,
        "substantive-focus rule",
    ) == []


def test_missing_domain_and_purpose_reminders_are_exact_bold_and_immediate():
    by = dictionary_by_name()
    rows = dictionary_rows()
    names = [row["Variable / Field Name"] for row in rows]
    paragraphs = validator.questionnaire_doc_paragraphs()
    specs = (
        ("po_miss_domain_reminder", "po_miss_domains", "Q6b.", builder.MISSING_DOMAIN_REMINDER, builder.MISSING_DOMAIN_REMINDER_PHRASE, builder.MISSING_DOMAIN_REMINDER_HTML),
        ("po_miss_purpose_reminder", "po_miss_purposes", "Q7b.", builder.MISSING_PURPOSE_REMINDER, builder.MISSING_PURPOSE_REMINDER_PHRASE, builder.MISSING_PURPOSE_REMINDER_HTML),
    )
    for reminder, target, question, plain, phrase, markup in specs:
        assert names.index(reminder) + 1 == names.index(target)
        assert by[reminder]["Field Type"] == "descriptive"
        assert by[reminder]["Field Label"] == builder.normal_weight_descriptive(markup)
        assert validator.plain_redcap_label(by[reminder]["Field Label"]) == validator.normalise_text(plain)
        assert markup.count(f"<strong>{phrase}</strong>") == 1
        assert by[reminder]["Branching Logic (Show field only if...)"] == ""
        assert by[reminder]["Required Field?"] == ""
        question_index = validator._question_index(paragraphs, question)
        assert paragraphs[question_index - 1] == validator.normalise_text(plain)
        assert validator.validate_exact_docx_bold_phrase(
            builder.QUESTIONNAIRE_SOURCE, plain, phrase, reminder
        ) == []


def test_missing_choices_are_labels_only_and_reference_wording_is_preserved():
    by = dictionary_by_name()
    assert tuple(validator.parse_choices(by["po_miss_domains"]["Choices, Calculations, OR Slider Labels"]).values()) == builder.DOMAIN_ORDER
    assert tuple(validator.parse_choices(by["po_miss_purposes"]["Choices, Calculations, OR Slider Labels"]).values()) == builder.missing_menu_labels("purpose")
    assert tuple(validator.parse_choices(by["po_miss_tags"]["Choices, Calculations, OR Slider Labels"]).values()) == builder.missing_menu_labels("tag")
    assert builder.TAG_DEFINITIONS == {
        "Demographic disparities / equity tag": (
            "A cross-cutting tag for projects whose research question centres on comparing outcomes, experiences, risks, access, or trajectories across demographic or equality-relevant groups. Routine subgroup breakdowns do not qualify, and socioeconomic or deprivation-based inequality alone is insufficient unless comparison across demographic or equality-relevant groups is central."
        ),
        "COVID-19 & Pandemic": (
            "A cross-cutting tag for projects where COVID-19, the COVID-19 pandemic, pandemic conditions, infection surveillance, vaccination, lockdowns, social distancing, pandemic-related public support, or pandemic consequences are a central condition or lens for the research question. Research does not qualify merely because its data cover the pandemic period or because COVID-19 is mentioned incidentally."
        ),
    }


def test_three_wording_roles_are_kept_separate_and_complete():
    by = dictionary_by_name()
    for prefix, layer, count in (("d", "domain", 4), ("p", "purpose", 2), ("t", "tag", 2)):
        for index in range(1, count + 1):
            stem = f"{prefix}{index:02d}"
            assert by[f"po_{stem}_display"]["Field Label"] == (
                f"<div><strong>[prop_{stem}_label]</strong><br>"
                f'<span style="font-weight:400;">What this {layer} covers: '
                f"[prop_{stem}_def]</span></div>"
            )
    for layer in ("domain", "purpose", "tag"):
        reference = by[builder.REFERENCE_FIELD_BY_LAYER[layer]]["Field Label"]
        assert reference == builder.missing_reference_html(layer)
        assert builder.base.UNCLEAR_LABEL not in html.unescape(reference)
        for label in builder.missing_menu_labels(layer):
            definition = (
                builder._domain_boundary_definition(label)
                if layer == "domain"
                else builder.rc3_short_definition(layer, label)
            )
            rendered = (
                f"<strong>{html.escape(label, quote=False)}</strong> — "
                f"{html.escape(definition, quote=False)}"
            )
            assert reference.count(rendered) == 1
            if layer == "domain":
                rc3_rendered = (
                    f"<strong>{html.escape(label, quote=False)}</strong> — "
                    f"{html.escape(builder.rc3_short_definition(layer, label), quote=False)}"
                )
                assert rc3_rendered not in reference

    fixture, _ = validator.read_csv(builder.IMPORT_FIXTURE)
    for row in fixture:
        if row["redcap_repeat_instrument"] != "project_review":
            continue
        for prefix, layer, count in (("d", "domain", 4), ("p", "purpose", 2), ("t", "tag", 2)):
            for index in range(1, count + 1):
                label = row[f"prop_{prefix}{index:02d}_label"]
                if label:
                    assert row[f"prop_{prefix}{index:02d}_def"] == builder.rc3_short_definition(
                        layer, label
                    )


def test_no_participant_facing_text_promises_a_missing_reference():
    participant_text = "\n".join(
        row["Field Label"] for row in dictionary_rows() if row["Field Label"]
    ).lower()
    for obsolete in (
        "a concise reference to all classifications is also available",
        "one-page guide attached",
        "taxonomy reference pdf",
        "optional classification reference",
    ):
        assert obsolete not in participant_text


def test_nonproduction_taxonomy_reference_is_replaced_by_point_of_need_blocks():
    names = {row["Variable / Field Name"] for row in dictionary_rows()}
    assert "po_taxonomy_ref" not in names
    forbidden = (
        "po_taxonomy_ref",
        "synthetic-QA placeholder",
        "Attach or link the final formatted owner-facing taxonomy reference",
        "taxonomy reference PDF",
    )
    for path in (
        builder.DICTIONARY,
        builder.FIELD_SPEC,
        builder.BRANCH_SPEC,
        builder.EXPORT_SPEC,
        builder.IMPORT_FIXTURE,
        builder.FORMATTING_AUDIT,
    ):
        text = path.read_text(encoding="utf-8-sig")
        assert not any(phrase in text for phrase in forbidden)
    documentation = builder.SPEC.read_text(encoding="utf-8") + builder.LIVE_CONFIG.read_text(
        encoding="utf-8"
    )
    assert "three complete collapsible reference blocks" in documentation
    assert "point-of-need reference blocks" in documentation


def test_approved_missing_domain_mapping_is_exact_complete_and_single_source():
    display = builder.OWNER_DOMAIN_DISPLAY
    assert tuple(display) == builder.DOMAIN_ORDER
    assert len(display) == 11
    assert tuple(item["label"] for item in builder.base.taxonomy_groups()[0]["domain"]) == (
        builder.DOMAIN_ORDER
    )
    assert builder.base.UNCLEAR_LABEL not in display
    approved_digest = hashlib.sha256(
        "\n".join(
            str(item["missing_choice_microdefinition"])
            for item in display.values()
        ).encode("utf-8")
    ).hexdigest()
    assert approved_digest == "8d79baa97b4a1ac17bd9b19767cb37197c2b9d77d3d60f32ed766be9111bb329"
    for label, item in display.items():
        assert item["canonical_label"] == label
        assert item["missing_choice_microdefinition"].startswith(f"{label} — ")
        assert tuple(item["taxonomy_source_fields"]) == builder.DOMAIN_TAXONOMY_SOURCE_FIELDS
        assert item["boundary_summary"]
        assert item["author_approval"] == "Approved, 2026-07-28"

    updater_source = Path(
        "scripts/update_project_owner_participant_documents_candidate_0_4.py"
    ).read_text(encoding="utf-8")
    assert "candidate.owner_domain_questionnaire_choices()" in updater_source
    assert "DOMAIN_CHOICES = (" not in updater_source


def test_q6b_questionnaire_dictionary_specs_and_audits_are_exactly_aligned():
    display = builder.OWNER_DOMAIN_DISPLAY
    expected = {
        str(index): str(item["missing_choice_microdefinition"])
        for index, item in enumerate(display.values(), 1)
    }
    row = dictionary_by_name()["po_miss_domains"]
    assert row["Field Type"] == "checkbox"
    assert row["Branching Logic (Show field only if...)"] == ""
    assert row["Required Field?"] == ""
    assert tuple(validator.parse_choices(row["Choices, Calculations, OR Slider Labels"]).values()) == builder.DOMAIN_ORDER
    documented = validator._question_following(
        validator.questionnaire_doc_paragraphs(), "Q6b.", "Response options:"
    ).removeprefix("Response options:").strip()
    assert documented == validator.normalise_text(" / ".join(expected.values()))

    field_rows, _ = validator.read_csv(builder.FIELD_SPEC)
    field = next(item for item in field_rows if item["variable"] == "po_miss_domains")
    assert "po_miss_domain_reference" in field["notes"]
    formatting, _ = validator.read_csv(builder.FORMATTING_AUDIT)
    audit = [item for item in formatting if item["variable_name"] == "po_miss_domains"]
    assert len(audit) == 1
    assert audit[0]["body_text"] == builder.owner_domain_redcap_choices()


def test_full_domain_definitions_remain_frozen_derived_and_distinct_from_q6b_aids():
    source = {
        item["canonical_label"]: item["owner_microdefinition"]
        for item in builder.base.display_source()["labels"]
        if item["owner_layer"] == "domain"
    }
    fixture, _ = validator.read_csv(builder.IMPORT_FIXTURE)
    reviews = [item for item in fixture if item["redcap_repeat_instrument"] == "project_review"]
    seen = set()
    for label, item in builder.OWNER_DOMAIN_DISPLAY.items():
        assert item["full_definition"] == source[label]
        assert item["full_definition"] != item["missing_choice_microdefinition"]
    for row in reviews:
        for index in range(1, builder.base.DOMAIN_SLOTS + 1):
            label = row[f"prop_d{index:02d}_label"]
            if label:
                seen.add(label)
                assert row[f"prop_d{index:02d}_def"] == source[label]
    assert seen == set(builder.DOMAIN_ORDER)


def test_approved_review_and_concordance_records_are_complete_and_live_qa_pending():
    review_rows = validator.missing_domain_review_rows()
    concordance_rows = validator.domain_concordance_rows()
    assert tuple(row["Canonical Domain"] for row in review_rows) == builder.DOMAIN_ORDER
    assert tuple(row["Canonical Domain"] for row in concordance_rows) == builder.DOMAIN_ORDER
    for review, concordance in zip(review_rows, concordance_rows, strict=True):
        label = review["Canonical Domain"]
        item = builder.OWNER_DOMAIN_DISPLAY[label]
        assert review["Final approved Q6b wording"] == item["missing_choice_microdefinition"]
        assert review["Author approval"] == "Approved, 2026-07-28"
        assert review["Implementation"] == "Implemented in candidate 0.4"
        assert concordance["Full proposed-label definition"] == item["full_definition"]
        assert concordance["Approved Q6b wording"] == item["missing_choice_microdefinition"]
        assert concordance["Inclusion direction aligned"].startswith("Yes")
        assert concordance["Boundary direction aligned"].startswith("Yes")
        assert concordance["Live-QA result"].startswith("Pending")
    combined = validator.MISSING_DOMAIN_REVIEW.read_text(encoding="utf-8") + (
        validator.DOMAIN_CONCORDANCE.read_text(encoding="utf-8")
    )
    assert "review_draft_pending_author_approval" not in combined
    assert "| Unclear from Register Entry |" not in combined


def test_live_qa_requires_all_eleven_semantic_and_display_checks():
    text = builder.LIVE_CONFIG.read_text(encoding="utf-8")
    assert "Research Domain wording concordance: For every Research Domain" in text
    assert "Record an individual pass/fail live-QA result for all 11 Domains" in text
    assert "without truncation or ambiguous line wrapping" in text
    assert "multi-select" in text
    assert "Unclear from Register Entry" in text
    assert "Migration approval fails if any Domain points in materially different directions" in text
    assert builder.SUBSTANTIVE_FOCUS_PHRASE in text
    assert builder.MISSING_DOMAIN_REMINDER_PHRASE in text
    assert builder.MISSING_PURPOSE_REMINDER_PHRASE in text
    assert "Fail migration approval if the governing rule is absent" in text
    assert "displayed as literal HTML" in text


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


def test_exact_two_tag_operational_invariant_uses_explicit_inclusion_rule():
    rows = builder.operational_tag_audit()
    assert builder.OPERATIONAL_TAGS == (
        "Demographic disparities / equity tag",
        "COVID-19 & Pandemic",
    )
    assert tuple(row["label"] for row in rows) == builder.OPERATIONAL_TAGS
    assert tuple(classifier.CROSS_CUTTING_TAGS) == builder.OPERATIONAL_TAGS
    assert tuple(dashboard_taxonomy.TAG_LABELS) == builder.OPERATIONAL_TAGS
    assert all(row["include_in_prompt"] is True for row in rows)
    assert [row["status"] for row in rows] == ["new v3.4", "active"]
    assert [row["label"] for row in rows if row["status"] == "active"] == [
        "COVID-19 & Pandemic"
    ]
    for predicate in (classifier._in_prompt_category, dashboard_taxonomy._is_active):
        source = inspect.getsource(predicate)
        assert "include_in_prompt" in source
        assert "startswith(\"removed\")" in source


def test_frozen_taxonomy_and_production_prompt_are_byte_unchanged():
    taxonomy = Path("taxonomy_data_dictionary.yaml")
    prompt = Path(
        "preregistration/package/02_taxonomy_prompt_and_model/"
        "production_prompt_dict-1.0-rc2.txt"
    )
    assert hashlib.sha256(taxonomy.read_bytes()).hexdigest() == (
        "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de"
    )
    assert hashlib.sha256(prompt.read_bytes()).hexdigest() == (
        "8fd34b5e80a748dce114ebe636d9861662c4cd8d3f0ce053ef458b95d9593861"
    )


def test_full_tag_definitions_match_main_questionnaire_appendix_and_redcap():
    paragraphs = validator.questionnaire_doc_paragraphs()
    headings = (
        "5.1 Demographic disparities / equity tag",
        "5.2 COVID-19 & Pandemic",
    )
    for heading, label in zip(headings, builder.OPERATIONAL_TAGS, strict=True):
        definition = validator.normalise_text(builder.TAG_DEFINITIONS[label])
        assert validator._definition_after_heading(paragraphs, heading) == definition
        assert paragraphs.count(definition) == 2
    assert "Routine subgroup breakdowns do not qualify" in builder.TAG_DEFINITIONS[
        builder.OPERATIONAL_TAGS[0]
    ]
    assert "socioeconomic or deprivation-based inequality alone is insufficient" in (
        builder.TAG_DEFINITIONS[builder.OPERATIONAL_TAGS[0]]
    )
    assert "data cover the pandemic period" in builder.TAG_DEFINITIONS[
        builder.OPERATIONAL_TAGS[1]
    ]
    assert "COVID-19 is mentioned incidentally" in builder.TAG_DEFINITIONS[
        builder.OPERATIONAL_TAGS[1]
    ]


def test_both_permanent_tag_blocks_are_populated_independent_and_required():
    by = dictionary_by_name()
    names = [row["Variable / Field Name"] for row in dictionary_rows()]
    fixture, _ = validator.read_csv(builder.IMPORT_FIXTURE)
    reviews = [row for row in fixture if row["redcap_repeat_instrument"] == "project_review"]
    assert len(reviews) == 19
    for index, label in enumerate(builder.OPERATIONAL_TAGS, 1):
        prefix = f"t{index:02d}"
        status = f"prop_{prefix}_status"
        definition = f"prop_{prefix}_def"
        display = f"po_{prefix}_display"
        correct = f"po_{prefix}_correct"
        visibility = f"po_{prefix}_vis"
        assert builder.TAG_FIELD_MAPPING[status] == label
        assert all(row[f"prop_{prefix}_label"] == label for row in reviews)
        assert all(
            row[definition] == builder.rc3_short_definition("tag", label)
            for row in reviews
        )
        assert all(row[status] in {"0", "1"} for row in reviews)
        assert validator.parse_choices(
            by[status]["Choices, Calculations, OR Slider Labels"]
        ) == {"1": "Applied", "0": "Not applied"}
        assert by[status]["Required Field?"] == ""
        assert names.index(display) < names.index(status) < names.index(correct)
        for judgement in (correct, visibility):
            assert by[judgement]["Required Field?"] == "y"
            assert by[judgement]["Branching Logic (Show field only if...)"] == ""
    missing = validator.analytical_completion_missing({}, affirmative_owner())
    assert {"po_t01_correct", "po_t01_vis", "po_t02_correct", "po_t02_vis"} <= set(missing)


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
    assert builder.QUOTATION_POLICY in documentation
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


def test_project_review_preserves_existing_names_and_types_with_four_additions():
    assert validator.validate_dictionary()["forms"]["project_review"] == 101


def test_deterministic_build_includes_approval_and_concordance_records():
    outputs = (
        builder.DICTIONARY,
        builder.SPEC,
        builder.LIVE_CONFIG,
        builder.IMPORT_FIXTURE,
        builder.FIELD_SPEC,
        builder.BRANCH_SPEC,
        builder.EXPORT_SPEC,
        builder.FORMATTING_AUDIT,
        builder.MISSING_DOMAIN_REVIEW,
        builder.DOMAIN_CONCORDANCE,
    )
    before = {path: path.read_bytes() for path in outputs}
    assert builder.main() == 0
    assert {path: path.read_bytes() for path in outputs} == before


def test_participant_document_updater_is_idempotent():
    before = {path: path.read_bytes() for path in (updater.CONSENT, updater.QUESTIONNAIRE)}
    assert updater.main() == 0
    assert {path: path.read_bytes() for path in before} == before
