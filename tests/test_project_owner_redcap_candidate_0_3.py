from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_project_owner_redcap_candidate_0_3 as builder  # noqa: E402
import validate_project_owner_redcap_candidate_0_3 as validator  # noqa: E402


def rows() -> list[dict[str, str]]:
    return validator.load_dictionary()


def by_name() -> dict[str, dict[str, str]]:
    return {row["Variable / Field Name"]: row for row in rows()}


def display() -> dict:
    return yaml.safe_load(builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8"))


def complete_owner_review() -> tuple[dict[str, str], dict[str, str]]:
    fixture = [dict(row) for row in validator.load_fixture()]
    owner = next(
        row for row in fixture
        if row["owner_id"] == "OWNER_TEST_001" and not row["redcap_repeat_instrument"]
    )
    review = next(
        row for row in fixture
        if row["owner_id"] == "OWNER_TEST_001" and row["redcap_repeat_instrument"]
    )
    owner.update({"intended_recipient": "1", "owner_consent": "1", "owner_consent_complete": "2"})
    review.update(
        {
            "po_miss_domain": "0",
            "po_miss_purpose": "0",
            "po_miss_tag": "0",
            "po_sufficiency": "1",
            "po_nonpublic": "0",
            "po_taxonomy_fit": "1",
            "project_review_complete": "2",
        }
    )
    for prefix, capacity in (("d", 4), ("p", 2)):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            if review[f"prop_{stem}_label"]:
                review[f"po_{stem}_fit"] = "1"
                review[f"po_{stem}_vis"] = "2"
    for index in range(1, 3):
        stem = f"t{index:02d}"
        review[f"po_{stem}_correct"] = "1"
        review[f"po_{stem}_vis"] = "2"
    return owner, review


def test_standard_redcap_columns_parseability_and_deterministic_dictionary() -> None:
    built, _ = builder.build_dictionary()
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=builder.HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(built)
    assert buffer.getvalue().encode("utf-8") == builder.DICTIONARY.read_bytes()
    assert validator.load_dictionary() == built
    assert len(builder.HEADERS) == 18


def test_unique_valid_redcap_variable_names_and_length_limit() -> None:
    names = [row["Variable / Field Name"] for row in rows()]
    assert len(names) == len(set(names))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in names)
    assert max(map(len, names)) <= 26


def test_exact_two_form_architecture_and_owner_id_record_field() -> None:
    candidate = rows()
    assert builder.VERSION == "owner-redcap-candidate-0.3"
    assert tuple(dict.fromkeys(row["Form Name"] for row in candidate)) == (
        "owner_consent",
        "project_review",
    )
    assert Counter(row["Form Name"] for row in candidate) == {
        "owner_consent": 11,
        "project_review": 86,
    }
    assert candidate[0]["Variable / Field Name"] == "owner_id"
    assert candidate[0]["Form Name"] == "owner_consent"
    assert candidate[0]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"


def test_no_direct_identifier_or_recruitment_contact_fields() -> None:
    names = {row["Variable / Field Name"] for row in rows()}
    assert not any(row["Identifier?"] for row in rows())
    assert not any(validator.FORBIDDEN_VARIABLE.search(name) for name in names)
    for prohibited in (
        "oc_name",
        "oc_email",
        "oc_affiliation",
        "oc_contact_source",
        "owner_invite_date",
        "owner_reminder_date",
    ):
        assert prohibited not in names


def test_consent_wording_branching_and_optional_acknowledgement_once() -> None:
    by = by_name()
    assert validator.parse_choices(
        by["intended_recipient"]["Choices, Calculations, OR Slider Labels"]
    ) == {"1": "Yes", "0": "No"}
    assert validator.parse_choices(
        by["owner_consent"]["Choices, Calculations, OR Slider Labels"]
    ) == {
        "1": "Yes, I agree to take part",
        "0": "No, I do not wish to take part",
    }
    assert validator.parse_choices(
        by["ack_pref"]["Choices, Calculations, OR Slider Labels"]
    ) == {"1": "Yes", "0": "No", "2": "Decide later"}
    assert all(by[name]["Required Field?"] == "y" for name in (
        "intended_recipient", "owner_consent"
    ))
    assert by["ack_pref"]["Required Field?"] == ""
    assert by["ack_pref"]["Form Name"] == "owner_consent"
    assert "optional and separate from your decision to take part" in by["ack_pref"]["Field Label"]
    assert by["owner_consent"]["Branching Logic (Show field only if...)"] == "[intended_recipient] = '1'"
    assert by["wrong_recipient_stop"]["Branching Logic (Show field only if...)"] == "[intended_recipient] = '0'"
    assert by["consent_decline_stop"]["Branching Logic (Show field only if...)"] == "[owner_consent] = '0'"
    assert by["ack_pref"]["Branching Logic (Show field only if...)"] == (
        "[intended_recipient] = '1' and [owner_consent] = '1'"
    )
    assert not any(
        "ack" in row["Variable / Field Name"]
        for row in rows()
        if row["Form Name"] == "project_review"
    )


def test_candidate_document_token_and_manual_stop_configuration() -> None:
    by = by_name()
    assert builder.PARTICIPANT_INFO_VERSION != "project-owner-information-v1"
    assert "placeholder" in by["participant_info_link"]["Field Label"].lower()
    assert "permanent URL" in by["participant_info_link"]["Field Label"]
    config = builder.LIVE_CONFIG.read_text(encoding="utf-8")
    assert "Survey Stop Action for `intended_recipient = No`" in config
    assert "Survey Stop Action for `owner_consent = No`" in config
    assert "Do not infer or claim automatic deletion" in config


def test_observed_production_cardinality_and_under_capacity_failure() -> None:
    maxima = builder.production_cardinalities()
    assert {layer: value["maximum"] for layer, value in maxima.items()} == {
        "domain": 4,
        "purpose": 2,
        "tag": 2,
    }
    assert builder.SLOT_CAPACITY == {"domain": 4, "purpose": 2, "tag": 2}
    original = builder.SLOT_CAPACITY["domain"]
    try:
        builder.SLOT_CAPACITY["domain"] = 3
        with pytest.raises(RuntimeError, match="below frozen maximum"):
            builder.production_cardinalities()
    finally:
        builder.SLOT_CAPACITY["domain"] = original


def test_every_domain_and_purpose_slot_has_hidden_empty_logic_and_response_triplet() -> None:
    by = by_name()
    for prefix, capacity in (
        ("d", 4),
        ("p", 2),
    ):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            label = f"prop_{stem}_label"
            definition = f"prop_{stem}_def"
            visible = f"[{label}] <> ''"
            assert by[label]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"
            assert by[definition]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"
            for suffix in ("display", "fit", "vis"):
                assert by[f"po_{stem}_{suffix}"][
                    "Branching Logic (Show field only if...)"
                ] == visible
            assert validator.parse_choices(
                by[f"po_{stem}_fit"]["Choices, Calculations, OR Slider Labels"]
            ) == {"1": "Fits", "2": "Does not fit", "3": "Unsure"}
            assert validator.parse_choices(
                by[f"po_{stem}_vis"]["Choices, Calculations, OR Slider Labels"]
            ) == {
                "2": "Clearly visible",
                "1": "Partly visible",
                "0": "Not visible",
                "3": "Unsure",
            }
            expected_question = (
                "Is the basis for this classification visible in the public project title "
                "and datasets listed above?"
            )
            assert by[f"po_{stem}_vis"]["Field Label"] == expected_question
            basis = by[f"po_{stem}_basis"]
            assert basis["Required Field?"] == "y"
            for trigger in (
                "fit] = '2'",
                "fit] = '3'",
                "vis] = '1'",
                "vis] = '0'",
                "vis] = '3'",
            ):
                assert trigger in basis["Branching Logic (Show field only if...)"]
            assert "vis] = '2'" not in basis["Branching Logic (Show field only if...)"]


def test_both_tag_statuses_are_always_reviewed_with_common_definitions() -> None:
    by = by_name()
    source_tags = [item for item in display()["labels"] if item["owner_layer"] == "tag"]
    assert [item["canonical_label"] for item in source_tags] == [
        "Demographic disparities / equity tag",
        "COVID-19 & Pandemic",
    ]
    for index, item in enumerate(source_tags, 1):
        stem = f"t{index:02d}"
        assert by[f"prop_{stem}_label"]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"
        assert by[f"prop_{stem}_def"]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"
        assert validator.parse_choices(
            by[f"prop_{stem}_status"]["Choices, Calculations, OR Slider Labels"]
        ) == {"1": "Applied", "0": "Not applied"}
        assert by[f"prop_{stem}_status"]["Field Annotation"] == "@READONLY-SURVEY"
        assert validator.parse_choices(
            by[f"po_{stem}_correct"]["Choices, Calculations, OR Slider Labels"]
        ) == {"1": "Yes", "0": "No", "2": "Unsure"}
        assert validator.parse_choices(
            by[f"po_{stem}_vis"]["Choices, Calculations, OR Slider Labels"]
        ) == {
            "2": "Clearly visible",
            "1": "Partly visible",
            "0": "Not visible",
            "3": "Unsure",
        }
        for name in (f"po_{stem}_display", f"prop_{stem}_status", f"po_{stem}_correct", f"po_{stem}_vis"):
            assert by[name]["Branching Logic (Show field only if...)"] == ""
        basis = by[f"po_{stem}_basis"]
        assert basis["Branching Logic (Show field only if...)"] == (
            f"[po_{stem}_correct] = '0' or [po_{stem}_correct] = '2' or "
            f"[po_{stem}_vis] = '1' or [po_{stem}_vis] = '0' or [po_{stem}_vis] = '3'"
        )
        assert f"[prop_{stem}_def]" in by[f"po_{stem}_display"]["Field Label"]


def test_missing_gateways_menus_and_definition_counts() -> None:
    by = by_name()
    mapping = {
        "domain": ("po_miss_domain", "po_miss_domains", 11),
        "purpose": ("po_miss_purpose", "po_miss_purposes", 7),
        "tag": ("po_miss_tag", "po_miss_tags", 2),
    }
    for layer, (gateway, menu, count) in mapping.items():
        assert validator.parse_choices(
            by[gateway]["Choices, Calculations, OR Slider Labels"]
        ) == {"1": "Yes", "0": "No", "2": "Unsure"}
        choices = validator.parse_choices(
            by[menu]["Choices, Calculations, OR Slider Labels"]
        )
        assert len(choices) == count
        assert all(" — " in value for value in choices.values())
        assert all("Unclear from Register Entry" not in value for value in choices.values())
        assert by[menu]["Branching Logic (Show field only if...)"] == f"[{gateway}] = '1'"
        assert by[menu]["Required Field?"] == "y"
        basis = by[{
            "domain": "po_miss_domain_basis",
            "purpose": "po_miss_purpose_basis",
            "tag": "po_miss_tag_basis",
        }[layer]]
        assert basis["Required Field?"] == "y"
        assert f"[{menu}(1)] = '1'" in basis[
            "Branching Logic (Show field only if...)"
        ]
    assert by["po_miss_purposes"]["Field Annotation"] == "@MAXCHECKED=2"
    guidance = by["po_miss_purpose_guidance"]
    assert guidance["Field Type"] == "descriptive"
    assert guidance["Branching Logic (Show field only if...)"] == "[po_miss_purpose] = '1'"
    assert guidance["Field Label"] == (
        "The framework assigns a maximum of two Analytical Purposes to each project. "
        "Select only the most important missing purpose or purposes, taking account of any "
        "proposed purposes that you judged to fit. The resulting classification should "
        "contain no more than two purposes in total."
    )


def test_display_labels_and_definitions_trace_exactly_to_taxonomy() -> None:
    source = display()
    taxonomy = builder.taxonomy_payload()
    index = {
        (item["layer"], item["label"]): item for item in taxonomy["categories"]
    }
    assert Counter(item["owner_layer"] for item in source["labels"]) == {
        "domain": 11,
        "purpose": 7,
        "tag": 2,
    }
    for item in builder.all_display_entries(source):
        original = index[(item["source_layer"], item["canonical_label"])]
        key = builder.display_key(item)
        assert item["source_status"] == original["status"]
        source_definition = validator._normalise(original["definition"])
        assert validator._normalise(item["owner_reference_definition"]) == validator._normalise(
            builder.owner_reference_definition(key, source_definition)
        )
        assert validator._normalise(item["source_definition"]) == validator._normalise(
            original["definition"]
        )
        assert item["owner_microdefinition"] == builder.MICRODEFINITIONS[key]
        assert item["source_dictionary_version"] == "1.0-rc2"
        assert item["review_status"] == "approved_by_author"
        assert item["reviewer"] == "Balint Stewart"
        assert item["review_date"] == "2026-07-23"
        assert item["microdefinition_material_simplification"] is True
        assert item["reference_definition_material_simplification"] is False
        assert item["reference_definition_boundary_clause_imported"] is (
            key in builder.REFERENCE_BOUNDARY_CLAUSES
        )
        expected_sources = builder.imported_boundary_sources(key, original)
        expected_origin = (
            "frozen_definition_plus_imported_exclusion_boundary_clause"
            if expected_sources
            else "frozen_definition_verbatim_after_whitespace_normalisation"
        )
        assert item["reference_definition_provenance"] == expected_origin
        assert item["imported_boundary_source_field"] == [
            source["source_field"] for source in expected_sources
        ]
        assert item["imported_boundary_source_path"] == [
            source["source_path"] for source in expected_sources
        ]
        assert item["imported_boundary_source_text"] == [
            source["source_text"] for source in expected_sources
        ]
        if not expected_sources:
            assert validator._normalise(item["owner_reference_definition"]) == source_definition
    assert {
        item["source_status"] for item in source["labels"]
    } >= {"relabelled v3.4", "new v3.4"}


def test_fallbacks_are_proposed_only_and_reference_is_generated_from_source() -> None:
    source = display()
    assert {
        (item["owner_layer"], item["canonical_label"])
        for item in source["proposed_only_fallbacks"]
    } == {
        ("domain", "Unclear from Register Entry"),
        ("purpose", "Unclear from Register Entry"),
    }
    assert all(
        item["include_in_owner_missing_menu"] is False
        for item in source["proposed_only_fallbacks"]
    )
    fallback_index = {
        builder.display_key(item): item for item in source["proposed_only_fallbacks"]
    }
    assert {
        key: item["owner_reference_definition"] for key, item in fallback_index.items()
    } == builder.PROPOSED_ONLY_DEFINITIONS
    assert fallback_index[("domain", builder.UNCLEAR_LABEL)]["owner_microdefinition"] != (
        fallback_index[("purpose", builder.UNCLEAR_LABEL)]["owner_microdefinition"]
    )
    assert all(item["include_in_prompt"] is True for item in fallback_index.values())
    assert all(item["include_as_proposed_label"] is True for item in fallback_index.values())
    assert all(item["review_status"] == "approved_by_author" for item in fallback_index.values())
    reference = builder.TAXONOMY_REFERENCE.read_text(encoding="utf-8")
    for item in source["labels"]:
        assert f"**{item['canonical_label']}**" in reference
        assert item["owner_reference_definition"] in reference
    for item in source["proposed_only_fallbacks"]:
        assert item["canonical_label"] in reference
        assert item["owner_reference_definition"] in reference
    assert f"Document version: {builder.TAXONOMY_REFERENCE_VERSION}" in reference
    assert f"Date: {builder.TAXONOMY_REFERENCE_DATE}" in reference


def test_layer_qualified_proposed_label_definitions_are_unique_and_complete() -> None:
    source = display()
    entries = builder.all_display_entries(source)
    index = builder.taxonomy_display_index(source)
    assert len(index) == len(entries) == 22
    assert Counter(key[0] for key in index) == {"domain": 12, "purpose": 8, "tag": 2}
    assert index[("domain", builder.UNCLEAR_LABEL)]["owner_reference_definition"] == (
        "Use only where the project title and dataset field together do not provide enough "
        "evidence to assign any substantive domain."
    )
    assert index[("purpose", builder.UNCLEAR_LABEL)]["owner_reference_definition"] == (
        "Use where the project title and datasets do not provide enough information to infer "
        "the analytical purpose."
    )
    assert validator.frozen_proposed_keys() <= set(index)
    assert not any(item["source_layer"] == "Layer B -- linkage" for item in entries)
    taxonomy = builder.taxonomy_payload()["categories"]
    linkage = [
        item for item in taxonomy
        if item["layer"] == "Layer B -- linkage" and item["label"] == builder.UNCLEAR_LABEL
    ]
    assert len(linkage) == 1
    assert linkage[0]["include_in_prompt"] is False
    assert linkage[0]["status"].startswith("removed")

    duplicate = yaml.safe_load(yaml.safe_dump(source, sort_keys=False))
    duplicate["proposed_only_fallbacks"].append(
        dict(duplicate["proposed_only_fallbacks"][0])
    )
    with pytest.raises(RuntimeError, match="duplicate taxonomy display key"):
        builder.taxonomy_display_index(duplicate)


def test_exact_eight_author_approved_microdefinition_revisions() -> None:
    assert builder.REVISED_MICRODEFINITIONS == {
        ("domain", "Health & Social Care"): "Health, illness, mental health, wellbeing, mortality as a health outcome, healthcare services and social care.",
        ("domain", builder.UNCLEAR_LABEL): "The public title and datasets do not provide enough evidence to assign a substantive Research Domain.",
        ("purpose", "Descriptive Monitoring"): "Measuring and describing levels, distributions, patterns or trends across places, populations or time, without primarily testing an exposure–outcome relationship.",
        ("purpose", "Outcome Tracking"): "Linking a naturally occurring exposure, condition or event to a later outcome, where the exposure is not a deliberate policy or programme.",
        ("purpose", "Policy Evaluation / Impact Analysis"): "Assessing the implementation, effects or consequences of a specific named policy, programme, regulation or intervention.",
        ("purpose", builder.UNCLEAR_LABEL): "The public title and datasets do not provide enough information to infer the Analytical Purpose.",
        ("tag", "Demographic disparities / equity tag"): "Comparisons across demographic or equality-relevant groups are central; socioeconomic inequality alone or routine subgroup breakdowns do not qualify.",
        ("tag", "COVID-19 & Pandemic"): "COVID-19 or pandemic conditions are a central research focus or lens, not merely the period covered by the data.",
    }


def test_other_fourteen_author_approved_microdefinitions_remain_unchanged() -> None:
    assert builder.UNCHANGED_MICRODEFINITIONS == {
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
    assert len(builder.MICRODEFINITIONS) == 22


def test_approved_paired_category_and_boundary_wording_is_coherent() -> None:
    micro = builder.MICRODEFINITIONS
    descriptive = micro[("purpose", "Descriptive Monitoring")]
    outcome = micro[("purpose", "Outcome Tracking")]
    policy = micro[("purpose", "Policy Evaluation / Impact Analysis")]
    assert "levels, distributions, patterns or trends" in descriptive
    assert "exposure–outcome relationship" in descriptive
    assert "naturally occurring exposure" in outcome
    assert "not a deliberate policy or programme" in outcome
    assert "specific named policy, programme, regulation or intervention" in policy
    assert "without necessarily estimating an intervention effect" not in outcome
    assert "mental health" in micro[("domain", "Health & Social Care")]
    assert "mortality as a health outcome" in micro[("domain", "Health & Social Care")]
    assert "mortality as a demographic outcome" in micro[("domain", "Migration & Demographics")]
    assert "socioeconomic inequality alone" in micro[("tag", "Demographic disparities / equity tag")]
    assert "not merely the period covered by the data" in micro[("tag", "COVID-19 & Pandemic")]


def test_branching_references_and_checkbox_codes_resolve() -> None:
    by = by_name()
    for row in rows():
        branch = row["Branching Logic (Show field only if...)"]
        assert branch.count("(") == branch.count(")")
        for reference, code in validator.BRANCH_REFERENCE.findall(branch):
            assert reference in by
            if code:
                assert by[reference]["Field Type"] == "checkbox"
                assert code in validator.parse_choices(
                    by[reference]["Choices, Calculations, OR Slider Labels"]
                )


def test_prepopulated_action_tags_are_survey_specific() -> None:
    by = by_name()
    for name in (
        "assignment_id", "project_title", "datasets_used", "public_register_url",
        "prop_t01_status", "prop_t02_status"
    ):
        assert by[name]["Field Annotation"] == "@READONLY-SURVEY"
    hidden = {
        "owner_id",
        "participant_info_ver",
        "consent_form_ver",
        "owner_instr_ver",
        "source_record_id",
        "official_project_id",
        "source_pop_ver",
        "production_ver",
        "taxonomy_ver",
        "proposal_output_sha256",
        "review_instr_ver",
        "taxonomy_display_ver",
    } | {
        name for name in by
        if name.startswith("prop_") and not name.endswith("_status")
    }
    assert all(by[name]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY" for name in hidden)


def test_redcap_instance_validation_types_and_public_url_structure() -> None:
    dictionary_rows = rows()
    validation_column = "Text Validation Type OR Show Slider Number"
    validation_types = {
        row[validation_column] for row in dictionary_rows if row[validation_column]
    }
    assert "url" not in validation_types
    assert validation_types <= validator.ALLOWED_VALIDATION_TYPES
    assert all(value == value.lower() for value in validation_types)

    public_url = by_name()["public_register_url"]
    assert public_url[validation_column] == ""
    assert public_url["Field Type"] == "text"
    assert public_url["Field Label"] == "Public register URL"
    assert public_url["Field Note"] == ""
    assert public_url["Choices, Calculations, OR Slider Labels"] == ""
    assert public_url["Branching Logic (Show field only if...)"] == ""
    assert public_url["Required Field?"] == ""
    assert public_url["Field Annotation"] == "@READONLY-SURVEY"
    assert all(
        row["public_register_url"].startswith("https://example.invalid/synthetic/")
        for row in validator.load_fixture()
        if row["redcap_repeat_instrument"] == "project_review"
    )


def test_overall_assessment_fields_and_conditional_explanations() -> None:
    by = by_name()
    assert validator.parse_choices(
        by["po_sufficiency"]["Choices, Calculations, OR Slider Labels"]
    ) == {"1": "Sufficient", "2": "Partial", "3": "Insufficient"}
    assert by["po_suff_explain"]["Required Field?"] == "y"
    assert validator.parse_choices(
        by["po_taxonomy_fit"]["Choices, Calculations, OR Slider Labels"]
    ) == {"1": "Fit", "2": "Partial Fit", "3": "No Fit"}
    assert validator.parse_choices(
        by["po_tax_issue"]["Choices, Calculations, OR Slider Labels"]
    ) == {
        "1": "Missing or inadequately represented category",
        "2": "Ambiguous or overlapping category boundaries",
        "5": "Other taxonomy problem",
    }
    assert by["po_tax_explain"]["Required Field?"] == "y"
    assert by["po_tax_other"]["Required Field?"] == "y"
    assert by["po_tax_other"]["Branching Logic (Show field only if...)"] == (
        "[po_tax_issue(5)] = '1'"
    )
    assert "confidential" in by["po_final_warning"]["Field Label"].lower()
    assert by["po_quote_permission"]["Form Name"] == "project_review"
    assert by["po_quote_permission"]["Required Field?"] == ""
    assert validator.parse_choices(
        by["po_nonpublic"]["Choices, Calculations, OR Slider Labels"]
    ) == {"0": "No", "1": "Yes", "2": "Unsure"}
    assert by["po_nonpublic"]["Required Field?"] == "y"
    assert by["po_nonpublic_note"]["Branching Logic (Show field only if...)"] == (
        "[po_nonpublic] = '1' or [po_nonpublic] = '2'"
    )
    assert by["po_nonpublic_note"]["Required Field?"] == ""
    assert "non-public information" in by["po_nonpublic_note"]["Field Label"]


def test_synthetic_long_fixture_owner_assignment_counts_and_instances() -> None:
    result = validator.validate_fixture()
    assert result == {
        "owners": 3,
        "assignments": 19,
        "rows": 22,
        "assignments_by_owner": {
            "OWNER_TEST_001": 1,
            "OWNER_TEST_002": 3,
            "OWNER_TEST_003": 15,
        },
    }


def test_synthetic_fixture_has_no_prefilled_responses_or_personal_data() -> None:
    fixture = validator.load_fixture()
    response_fields = validator._response_fields(rows())
    assert all(not row.get(name) for row in fixture for name in response_fields)
    raw = builder.IMPORT_FIXTURE.read_text(encoding="utf-8")
    assert not validator.EMAIL.search(raw)
    assert not validator.REAL_RECORD_ID.search(raw)
    assert "OWNER_TEST_001" in raw
    assert "SYN_RECORD_001" in raw
    assert "Researcher name" not in raw
    tag_labels = [item["canonical_label"] for item in display()["labels"] if item["owner_layer"] == "tag"]
    repeats = [row for row in fixture if row["redcap_repeat_instrument"] == "project_review"]
    for row in repeats:
        assert [row["prop_t01_label"], row["prop_t02_label"]] == tag_labels
        assert row["prop_t01_status"] in {"0", "1"}
        assert row["prop_t02_status"] in {"0", "1"}


def test_long_export_split_join_and_response_states() -> None:
    fixture = validator.load_fixture()
    owners, reviews = validator.prepare_long_export(fixture)
    assert len(owners) == 3
    assert len(reviews) == 19
    assert {row["assignment_response_state"] for row in reviews} == {
        "untouched"
    }
    assert not any(row["substantive_analysis_eligible"] for row in reviews)
    assert validator.validate_long_model() == {"owner_rows": 3, "review_rows": 19}


def test_analytical_completion_is_explicit_and_independent_of_optional_fields() -> None:
    owner, review = complete_owner_review()
    assert validator.analytical_completion_missing(review, owner) == []
    review["ack_pref"] = ""
    review["po_quote_permission"] = ""
    review["po_other_comment"] = ""
    review["po_nonpublic_note"] = ""
    assert validator.analytical_completion_missing(review, owner) == []
    review["project_review_complete"] = "0"
    joined = validator.prepare_long_export([owner, review])[1][0]
    assert joined["analytically_complete"] is True
    assert joined["submitted"] is False
    assert joined["assignment_response_state"] == "analytically_complete"


def test_analytical_completion_requires_both_tags_and_every_triggered_field() -> None:
    owner, review = complete_owner_review()
    review["po_t02_correct"] = ""
    assert "po_t02_correct" in validator.analytical_completion_missing(review, owner)
    review["po_t02_correct"] = "0"
    assert "po_t02_basis" in validator.analytical_completion_missing(review, owner)
    review["po_t02_basis"] = "General non-confidential explanation."
    review["po_d01_vis"] = "1"
    assert "po_d01_basis" in validator.analytical_completion_missing(review, owner)
    review["po_d01_basis"] = "General register limitation."
    review["po_miss_domain"] = "1"
    assert "po_miss_domains" in validator.analytical_completion_missing(review, owner)
    review["po_miss_domains___1"] = "1"
    assert "po_miss_domain_basis" in validator.analytical_completion_missing(review, owner)
    review["po_miss_domain_basis"] = "General missing-label basis."
    assert validator.analytical_completion_missing(review, owner) == []


def test_submitted_does_not_override_incomplete_required_responses() -> None:
    owner, review = complete_owner_review()
    review["po_taxonomy_fit"] = "2"
    joined = validator.prepare_long_export([owner, review])[1][0]
    assert joined["submitted"] is True
    assert joined["analytically_complete"] is False
    assert joined["assignment_response_state"] == "partial"
    assert {"po_tax_issue", "po_tax_explain"} <= set(joined["analytical_completion_missing"])


def test_expected_export_explicitly_requires_owner_join() -> None:
    export = list(
        csv.DictReader(builder.EXPORT_SPEC.open(encoding="utf-8", newline=""))
    )
    by = {row["variable"]: row for row in export}
    assert by["owner_id"]["analysis_role"] == "join_key"
    assert by["redcap_repeat_instrument"]["analysis_role"] == "row_split"
    assert by["owner_consent"]["row_type"] == "owner"
    assert by["project_review_complete"]["row_type"] == "project_review"
    assert (
        "do not treat 2 alone as analytical completeness"
        in by["project_review_complete"]["notes"]
    )
    spec = builder.SPEC.read_text(encoding="utf-8")
    assert "Do **not** filter repeated rows directly with `owner_consent = 1`" in spec
    assert "join owner consent to reviews by `owner_id`" in spec
    assert "cardinality/taxonomy issue" in by["po_miss_purposes"]["notes"]
    assert "number of populated proposed purposes judged `Fits`" in spec


def test_visibility_scale_is_documented_across_generated_specifications() -> None:
    field_spec = list(
        csv.DictReader(builder.FIELD_SPEC.open(encoding="utf-8-sig", newline=""))
    )
    field_by = {row["variable"]: row for row in field_spec}
    export = list(
        csv.DictReader(builder.EXPORT_SPEC.open(encoding="utf-8-sig", newline=""))
    )
    export_by = {row["variable"]: row for row in export}
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    assert branch["proposed_slot_visibility"]["choices"] == {
        "2": "Clearly visible",
        "1": "Partly visible",
        "0": "Not visible",
        "3": "Unsure",
    }
    for prefix, capacity in (("d", 4), ("p", 2), ("t", 2)):
        for index in range(1, capacity + 1):
            stem = f"{prefix}{index:02d}"
            assert "2 Clearly visible" in field_by[f"po_{stem}_vis"]["notes"]
            assert "Partly visible/Not visible/Unsure" in field_by[f"po_{stem}_basis"]["notes"]
            assert "2=Clearly visible" in export_by[f"po_{stem}_vis"]["notes"]
            assert "Partly visible/Not visible/Unsure" in export_by[f"po_{stem}_basis"]["notes"]
    assert validator.validate_response_specifications() == {
        "visibility_fields": 8,
        "basis_fields": 8,
    }


def test_live_configuration_records_non_csv_runtime_assertions() -> None:
    config = builder.LIVE_CONFIG.read_text(encoding="utf-8")
    assert builder.CANDIDATE_SOURCE_COMMIT == "69cf6665b845428fa2abd855c0445ae20589579f"
    assert f"Candidate source commit: `{builder.CANDIDATE_SOURCE_COMMIT}`" in config
    for phrase in (
        "Classic/non-longitudinal",
        "only** repeating instrument",
        "[assignment_id] — [project_title]",
        "Repeat the Survey disabled",
        "[owner_id] <> ''",
        "Auto Start enabled",
        "[owner_consent_complete] = '2'",
        "Project Review Auto Start disabled",
        "participant/record-specific Survey Queue URL",
        "Return the participant to the visible Survey Queue",
        "desktop and mobile",
        "19 pre-created Project Review repeat rows",
        "Your response has been recorded under the reference [assignment_id]",
        "Both canonical tag blocks appear on every repeat",
        "at-least-one behaviour as a live-QA assertion",
    ):
        assert phrase in config
    assert "cannot encode" in config


def test_candidate_status_is_unfrozen_pending_controlled_import_and_live_qa() -> None:
    branch = yaml.safe_load(builder.BRANCH_SPEC.read_text(encoding="utf-8"))
    assert branch["status"] == (
        "development_candidate_unfrozen_controlled_import_and_live_qa_pending"
    )
    assert branch["project"]["pid"] == 9149
    assert branch["project"]["connection_performed"] is False
    assert branch["repeating_instruments"] == ["project_review"]
    assert branch["repeat_survey_button_enabled"] is False
    assert "ack_pref" not in branch["survey_queue"]["project_review"]["condition"]
    assert branch["tag_reviews"]["always_review_both"] is True


def test_taxonomy_human_review_table_has_twenty_two_approved_rows() -> None:
    result = validator.validate_taxonomy_human_review()
    assert result["rows"] == 22
    assert result["pending_human_approval"] == 0
    assert result["approved_by_author"] == 22
    assert result["revision_required"] == 0
    with builder.TAXONOMY_HUMAN_REVIEW.open(encoding="utf-8-sig", newline="") as handle:
        review_rows = list(csv.DictReader(handle))
    assert all(row["reviewer"] == "Balint Stewart" for row in review_rows)
    assert all(row["review_date"] == "2026-07-23" for row in review_rows)
    assert all(row["review_status"] == "approved_by_author" for row in review_rows)
    assert Counter(row["layer"] for row in review_rows) == {
        "domain": 12,
        "purpose": 8,
        "tag": 2,
    }
    display_by_key = builder.taxonomy_display_index(display())
    rows_by_key = {
        (row["layer"], row["canonical_label"]): row for row in review_rows
    }
    assert set(rows_by_key) == set(builder.MICRODEFINITIONS)
    for key, row in rows_by_key.items():
        microdefinition = builder.MICRODEFINITIONS[key]
        reference_definition = display_by_key[key]["owner_reference_definition"]
        assert row["current_short_definition"] == display_by_key[key]["source_definition"]
        assert row["candidate_reference_definition"] == reference_definition
        assert row["candidate_microdefinition"] == microdefinition
        assert row["reference_definition_provenance"] == display_by_key[key][
            "reference_definition_provenance"
        ]
        assert json.loads(row["imported_boundary_source_field"]) == display_by_key[key][
            "imported_boundary_source_field"
        ]
        assert json.loads(row["imported_boundary_source_path"]) == display_by_key[key][
            "imported_boundary_source_path"
        ]
        assert json.loads(row["imported_boundary_source_text"]) == display_by_key[key][
            "imported_boundary_source_text"
        ]
        if key in builder.REFERENCE_BOUNDARY_CLAUSES:
            assert row["wording_origin"] == (
                "frozen_definition_plus_imported_exclusion_boundary_clause"
            )
            assert row["material_simplification_note"] == (
                "Approved inline microdefinition is unchanged; participant-reference definition "
                "combines the frozen definition with an imported exclusion/boundary clause."
            )
        else:
            assert row["wording_origin"] == (
                "frozen_definition_verbatim_after_whitespace_normalisation"
            )
            assert row["material_simplification_note"] == (
                "Approved inline microdefinition is a display condensation; frozen source "
                "and participant-reference definition remain unchanged."
            )
        assert int(row["reference_definition_word_count"]) == (
            builder.reference_definition_word_count(reference_definition)
        )
        assert int(row["reference_definition_character_count"]) == len(
            reference_definition
        )
        assert int(row["microdefinition_word_count"]) == builder.microdefinition_word_count(
            microdefinition
        )
        assert int(row["microdefinition_character_count"]) == len(microdefinition)
        assert row["essential_boundary_preserved"]
    ambiguity_by_key = {
        (row["layer"], row["canonical_label"]): row["possible_ambiguity"]
        for row in review_rows
    }
    assert {
        key: note for key, note in ambiguity_by_key.items() if note
    } == builder.AMBIGUITY_NOTES


def test_taxonomy_microdefinition_editorial_checks_are_non_blocking_and_complete() -> None:
    editorial = validator.validate_taxonomy_human_review()["editorial_checks"]
    assert editorial["empty_microdefinitions"] == []
    assert editorial["duplicate_keys"] == []
    assert editorial["unclear_microdefinitions_identical"] is False
    assert editorial["missing_high_risk_boundary_notes"] == []
    assert editorial["reference_outside_preferred_range"] == []
    assert editorial["compression_risk_entries"] == sorted(
        builder.HIGH_RISK_COMPRESSION_NOTES
    )


def test_approved_microdefinitions_propagate_inline_not_reference_definitions() -> None:
    source = display()
    display_by_key = builder.taxonomy_display_index(source)
    dictionary_text = builder.DICTIONARY.read_text(encoding="utf-8")
    fixture = validator.load_fixture()
    for item in source["labels"]:
        if item["include_in_owner_missing_menu"]:
            assert item["owner_microdefinition"] in dictionary_text
    for row in fixture:
        if row["redcap_repeat_instrument"] != "project_review":
            continue
        for prefix, layer, capacity in (
            ("d", "domain", builder.DOMAIN_SLOTS),
            ("p", "purpose", builder.PURPOSE_SLOTS),
            ("t", "tag", builder.TAG_SLOTS),
        ):
            for index in range(1, capacity + 1):
                label = row[f"prop_{prefix}{index:02d}_label"]
                if label:
                    assert row[f"prop_{prefix}{index:02d}_def"] == display_by_key[
                        (layer, label)
                    ]["owner_microdefinition"]


def test_four_reference_definitions_add_boundaries_without_changing_inline_text() -> None:
    source = display()
    display_by_key = builder.taxonomy_display_index(source)
    dictionary_text = builder.DICTIONARY.read_text(encoding="utf-8")
    for key, clause in builder.REFERENCE_BOUNDARY_CLAUSES.items():
        item = display_by_key[key]
        assert item["owner_reference_definition"] == (
            f"{item['source_definition']} {clause}"
        )
        assert item["owner_microdefinition"] == builder.MICRODEFINITIONS[key]
        assert item["reference_definition_boundary_clause_imported"] is True
        assert item["wording_origin"] == (
            "frozen_definition_plus_imported_exclusion_boundary_clause"
        )
        assert item["reference_definition_provenance"] == (
            "frozen_definition_plus_imported_exclusion_boundary_clause"
        )
        original = next(
            candidate
            for candidate in builder.taxonomy_payload()["categories"]
            if candidate["layer"] == item["source_layer"]
            and candidate["label"] == item["canonical_label"]
        )
        expected_sources = builder.imported_boundary_sources(key, original)
        assert expected_sources
        assert item["imported_boundary_source_path"] == [
            source["source_path"] for source in expected_sources
        ]
        assert clause not in dictionary_text


def test_taxonomy_reference_is_clean_participant_content_with_unclear_framing() -> None:
    reference = builder.TAXONOMY_REFERENCE.read_text(encoding="utf-8")
    assert f"Document version: {builder.TAXONOMY_REFERENCE_VERSION}" in reference
    assert f"Date: {builder.TAXONOMY_REFERENCE_DATE}" in reference
    assert "## About ‘Unclear from Register Entry’" in reference
    assert (
        "This label may appear where the classification judged that the public project title "
        "and listed datasets did not provide enough information to assign a substantive "
        "Research Domain or infer an Analytical Purpose. Your view on whether that judgement "
        "was reasonable is itself useful evidence for the validation study."
    ) in reference
    assert "The framework’s own definitions are:" in reference
    assert reference.index("The framework’s own definitions are:") < reference.index(
        "**Research Domain — Unclear from Register Entry**"
    )
    assert (
        "Use this guide when deciding whether each proposed classification fits the actual "
        "project and how clearly its basis is visible in the public project title and listed "
        "datasets. The short definitions summarise how the framework uses each category."
    ) in reference
    for clause in builder.REFERENCE_BOUNDARY_CLAUSES.values():
        assert clause in reference
    for phrase in (
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
    ):
        assert phrase.lower() not in reference.lower()
    display_text = builder.TAXONOMY_DISPLAY.read_text(encoding="utf-8")
    review_text = builder.TAXONOMY_HUMAN_REVIEW.read_text(encoding="utf-8")
    assert "source_definition:" in display_text
    assert "review_status: approved_by_author" in display_text
    assert "frozen_definition_plus_imported_exclusion_boundary_clause" in display_text
    assert "source_taxonomy_definition" in review_text
    assert "frozen_definition_plus_imported_exclusion_boundary_clause" in review_text


def test_domain_and_purpose_cardinality_guidance_is_clear_without_a_new_field() -> None:
    reference = builder.TAXONOMY_REFERENCE.read_text(encoding="utf-8")
    domain_guidance = (
        "A project may be assigned more than one Research Domain where each is substantively "
        "part of the research; the domains are not ranked."
    )
    assert domain_guidance in reference
    assert reference.index(domain_guidance) < reference.index("## Research Domains")
    assert "maximum number of Research Domains" not in reference
    assert "maximum of two Research Domains" not in reference
    assert "no more than two Analytical Purposes" in reference
    assert "More than one Analytical Purpose may apply." in reference
    dictionary_rows = rows()
    assert len(dictionary_rows) == 97
    assert Counter(row["Form Name"] for row in dictionary_rows) == {
        "owner_consent": 11,
        "project_review": 86,
    }
    assert set(row["Variable / Field Name"] for row in dictionary_rows) == set(by_name())
    assert not any(
        row["Variable / Field Name"] == "po_domain_guidance" for row in dictionary_rows
    )
    inline_guidance = (
        "A project may have several Research Domains. Each proposed Domain should be judged "
        "independently; the Domains are not ranked."
    )
    assert inline_guidance in by_name()["po_intro"]["Field Label"]


def test_participant_reference_and_withdrawal_wording_are_neutral() -> None:
    by = by_name()
    assert by["assignment_id"]["Field Label"] == "Review reference"
    assert by["assignment_id"]["Field Annotation"] == "@READONLY-SURVEY"
    assert by["owner_id"]["Field Annotation"] == "@HIDDEN-SURVEY @READONLY"
    assert "Review reference [assignment_id]" in by["po_intro"]["Field Label"]
    config = builder.LIVE_CONFIG.read_text(encoding="utf-8")
    assert "reference [assignment_id]" in config
    assert "without knowing or quoting `owner_id`" in builder.SPEC.read_text(
        encoding="utf-8"
    )


def test_candidate_participant_wording_has_no_old_separate_link_workflow() -> None:
    participant_text = "\n".join(row["Field Label"] for row in rows())
    for phrase in (
        "after expressing interest",
        "separate project links",
        "project-specific review links",
        "links will be released",
        "separately emailed project-review links",
    ):
        assert phrase not in participant_text.lower()


def test_frozen_taxonomy_and_production_output_hashes_are_preserved() -> None:
    assert builder.check_frozen_sources() is None
    assert hashlib.sha256(builder.TAXONOMY.read_bytes()).hexdigest() == builder.TAXONOMY_SHA256
    assert hashlib.sha256(builder.FROZEN_OUTPUT.read_bytes()).hexdigest() == builder.FROZEN_OUTPUT_SHA256


def test_candidate_0_2_controlled_artefacts_remain_byte_identical() -> None:
    assert builder.check_v02_hashes() is None
    for relative, expected in builder.V02_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_protocol_and_participant_documents_remain_byte_identical() -> None:
    expected = {
        "preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.15.docx": "5eff044b4f8d488e84a5b49720d35318add4f29ef53136cb6ce9c2b197409ee7",
        "preregistration/package/06_redcap/participant_materials/Project_Owner_Participant_Information_and_consent_v1.docx": "912e4c05e5b0deae30f3024d9ca0c60eef5d91a2b43169c7df3dc631c79c1df7",
        "preregistration/package/06_redcap/participant_materials/Project_Owner_Review_questionnaire_v1.docx": "a02aabe2d953d568b0abebe23531de86ad694b4d227e7b74b35bf53e65e2e154",
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest


def test_complete_offline_validator_passes() -> None:
    result = validator.check()
    assert result["status"] == "passed_offline_unfrozen_live_qa_required"
    assert result["dictionary"]["fields"] == 97
    assert result["taxonomy_display"]["counts"] == {
        "domain": 11,
        "purpose": 7,
        "tag": 2,
    }
    assert result["taxonomy_display"]["proposed_display_counts"] == {
        "domain": 12,
        "purpose": 8,
        "tag": 2,
    }
    assert result["taxonomy_human_review"]["pending_human_approval"] == 0
    assert result["taxonomy_human_review"]["approved_by_author"] == 22
    assert result["taxonomy_human_review"]["revision_required"] == 0
