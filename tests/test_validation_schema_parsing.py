from copy import deepcopy
from itertools import product
from pathlib import Path

import pytest
import yaml

from analysis.validation.diagnostics import (
    human_supported,
    macro_average_eligible,
    majority_diagnostic_rating,
    majority_supported_labels,
    support_band,
    taxonomy_issue_denominator,
)
from analysis.validation.redcap import (
    ExportParseError,
    decode_scratch_row,
    load_wide_export,
    parse_scratch_export_rows,
)
from analysis.validation.schema import (
    CoderRating,
    ModelRating,
    ProjectRatings,
    UNCLEAR,
    complete_case_projects,
    validate_project,
)
from analysis.validation.sufficiency import (
    broad_register_usable,
    majority_insufficient,
    strict_register_sufficient,
)


FIXTURE = Path("tests/fixtures/validation_synthetic_export.csv")
EXPECTED = Path("tests/fixtures/validation_expected_cases.yaml")
SLOTS = {"SYN-CODER-A": "A", "SYN-CODER-B": "B", "SYN-CODER-C": "C"}


def model_map():
    data = yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))["export_models"]
    return {
        record_id: ModelRating(
            frozenset(values["domains"]),
            frozenset(values["purposes"]),
            values["equity_tag"],
            values["covid_tag"],
        )
        for record_id, values in data.items()
    }


def parsed():
    return parse_scratch_export_rows(
        load_wide_export(FIXTURE), model_by_record=model_map(), coder_slot_by_reviewer=SLOTS
    )


def valid_coder(reviewer="SYN-CODER-A", **changes):
    values = dict(
        reviewer_id=reviewer,
        domains=frozenset({"Labour Market & Employment"}),
        purposes=frozenset({"Descriptive Monitoring"}),
        equity_tag=0,
        covid_tag=0,
        register_sufficiency="Sufficient",
        taxonomy_fit="Fit",
        taxonomy_issues=frozenset(),
        complete=True,
    )
    values.update(changes)
    return CoderRating(**values)


def valid_project(**changes):
    values = dict(
        record_id="SYN-900",
        sample_set="random_baseline",
        coder_a=valid_coder("SYN-CODER-A"),
        coder_b=valid_coder("SYN-CODER-B"),
        coder_c=valid_coder("SYN-CODER-C"),
        model=ModelRating(
            frozenset({"Labour Market & Employment"}),
            frozenset({"Descriptive Monitoring"}),
            0,
            0,
        ),
        instrument_version="redcap-candidate-0.6",
    )
    values.update(changes)
    return ProjectRatings(**values)


def test_synthetic_export_parses_without_id_inference():
    result = parsed()
    assert result.decoded_assignment_count == 11
    assert result.excluded_assignment_count == 0
    assert [project.record_id for project in result.projects] == ["SYN-001", "SYN-002", "SYN-003", "SYN-004"]
    assert validate_project(result.projects[0]).status == "valid_response"
    assert "all" in validate_project(result.projects[-1]).fatal_dimensions  # missing coder C


def test_candidate_0_4_fixture_exercises_all_fit_values():
    projects = parsed().projects
    fits = {
        coder.taxonomy_fit
        for project in projects
        for coder in project.coders
        if coder is not None
    }
    assert fits == {"Fit", "Partial Fit", "No Fit", "Cannot assess from register entry"}
    assert any(
        coder is not None and coder.explanatory_note == "Synthetic partial-fit note."
        for project in projects
        for coder in project.coders
    )


def test_candidate_0_3_old_issue_code_decodes_but_pilot_is_excluded():
    row = deepcopy(load_wide_export(FIXTURE)[0])
    row.update(
        assignment_id="SYN-HIST-001",
        source_record_id="SYN-099",
        sample_set="4",
        validation_included="0",
        instrument_ver="redcap-candidate-0.3",
        sc_taxonomy_fit="2",
        sc_tax_issue___1="0",
        sc_tax_issue___3="1",
    )
    decoded = decode_scratch_row(row)
    assert decoded.rating.taxonomy_issues == frozenset({"Too broad"})
    result = parse_scratch_export_rows([row], model_by_record={}, coder_slot_by_reviewer=SLOTS)
    assert not result.projects
    assert result.excluded_assignment_count == 1


def test_unknown_instrument_version_and_0_3_fit_4_fail_clearly():
    row = deepcopy(load_wide_export(FIXTURE)[0])
    row["instrument_ver"] = "redcap-candidate-9.9"
    with pytest.raises(ExportParseError, match="Unknown instrument version"):
        decode_scratch_row(row)
    row["instrument_ver"] = "redcap-candidate-0.3"
    row["sc_taxonomy_fit"] = "4"
    with pytest.raises(ExportParseError, match="Unknown sc_taxonomy_fit code"):
        decode_scratch_row(row)


def test_candidate_0_6_uses_the_existing_post_pilot_response_mapping():
    row = deepcopy(load_wide_export(FIXTURE)[0])
    row["instrument_ver"] = "redcap-candidate-0.6"
    row["sc_taxonomy_fit"] = "4"
    decoded = decode_scratch_row(row)
    assert decoded.rating.taxonomy_fit == "Cannot assess from register entry"
    assert not decoded.rating.taxonomy_issues


def test_duplicate_reviewer_project_and_inconsistent_assignment_ids_fail():
    rows = load_wide_export(FIXTURE)
    duplicate = deepcopy(rows[0])
    duplicate["assignment_id"] = "SYN-DUPLICATE"
    with pytest.raises(ExportParseError, match="Duplicate reviewer-project"):
        parse_scratch_export_rows(rows + [duplicate], model_by_record=model_map(), coder_slot_by_reviewer=SLOTS)
    inconsistent = deepcopy(rows[0])
    inconsistent["source_record_id"] = "SYN-999"
    with pytest.raises(ExportParseError, match="inconsistent Record IDs"):
        parse_scratch_export_rows([rows[0], inconsistent], model_by_record=model_map(), coder_slot_by_reviewer=SLOTS)


def test_parser_requires_explicit_reviewer_mapping():
    with pytest.raises(ExportParseError, match="no explicit coder-slot mapping"):
        parse_scratch_export_rows(
            load_wide_export(FIXTURE), model_by_record=model_map(), coder_slot_by_reviewer={}
        )


@pytest.mark.parametrize(
    ("coder_change", "fatal_dimension"),
    [
        ({"domains": frozenset()}, "domains"),
        ({"domains": frozenset({"Unknown domain"})}, "domains"),
        ({"purposes": frozenset()}, "purposes"),
        ({"equity_tag": 2}, "equity_tag"),
        ({"register_sufficiency": "Unknown"}, "register_sufficiency"),
        ({"taxonomy_fit": "Unknown"}, "taxonomy_fit"),
    ],
)
def test_fatal_or_uninterpretable_dimensions(coder_change, fatal_dimension):
    report = validate_project(valid_project(coder_a=valid_coder(**coder_change)))
    assert fatal_dimension in report.fatal_dimensions
    assert report.status == "fatal_or_uninterpretable_dimension"


def test_unclear_coexistence_and_readable_impossible_combinations_are_retained():
    unclear = valid_project(
        coder_a=valid_coder(domains=frozenset({UNCLEAR, "Education & Skills"}))
    )
    report = validate_project(unclear)
    assert report.retained_instrument_inconsistent
    assert "domains" not in report.fatal_dimensions
    cannot = valid_project(
        coder_a=valid_coder(
            taxonomy_fit="Cannot assess from register entry",
            register_sufficiency="Sufficient",
        )
    )
    assert validate_project(cannot).retained_instrument_inconsistent
    missing_issue = valid_project(coder_a=valid_coder(taxonomy_fit="Partial Fit"))
    assert validate_project(missing_issue).retained_instrument_inconsistent


def test_duplicate_reviewer_project_assignment_detected_in_canonical_model():
    project = valid_project(coder_b=valid_coder("SYN-CODER-A"))
    assert "all" in validate_project(project).fatal_dimensions


def test_common_complete_case_retains_flagged_but_excludes_fatal_dimension():
    retained = valid_project(
        record_id="SYN-901",
        coder_a=valid_coder(domains=frozenset({UNCLEAR, "Education & Skills"})),
    )
    fatal = valid_project(record_id="SYN-902", coder_a=valid_coder(domains=frozenset()))
    assert complete_case_projects((retained, fatal), "domains") == (retained,)


def test_all_register_sufficiency_combinations_match_count_rules():
    values = ("Sufficient", "Partially sufficient", "Insufficient")
    for ratings in product(values, repeat=3):
        assert broad_register_usable(ratings) == (sum(v != "Insufficient" for v in ratings) >= 2)
        assert strict_register_sufficient(ratings) == (ratings.count("Sufficient") >= 2)
        assert majority_insufficient(ratings) == (ratings.count("Insufficient") >= 2)
    majority_insufficient_case = ("Insufficient", "Insufficient", "Sufficient")
    assert majority_insufficient(majority_insufficient_case)
    # This primitive is diagnostic only; it does not remove the record from the primary population.


def test_labelwise_majority_is_independent_and_can_exceed_two_purposes():
    coders = (
        frozenset({"P1", "P2"}),
        frozenset({"P2", "P3"}),
        frozenset({"P1", "P3"}),
    )
    assert human_supported(coders, "P1")
    assert human_supported(coders, "P2")
    assert human_supported(coders, "P3")
    assert not human_supported(coders, "P4")
    assert majority_supported_labels(coders) == frozenset({"P1", "P2", "P3"})


def test_individual_more_than_two_purposes_is_retained_inconsistent():
    project = valid_project(
        coder_a=valid_coder(
            purposes=frozenset(
                {
                    "Descriptive Monitoring",
                    "Outcome Tracking",
                    "Policy Evaluation / Impact Analysis",
                }
            )
        )
    )
    report = validate_project(project)
    assert report.retained_instrument_inconsistent
    assert "purpose_maximum_exceeded" in {issue.code for issue in report.issues}


def test_other_taxonomy_problem_requires_parsed_explanatory_note():
    without_note = valid_project(
        coder_a=valid_coder(
            taxonomy_fit="Partial Fit",
            taxonomy_issues=frozenset({"Other taxonomy problem"}),
        )
    )
    report = validate_project(without_note)
    assert "other_taxonomy_problem_without_note" in {
        issue.code for issue in report.issues
    }

    with_note = valid_project(
        coder_a=valid_coder(
            taxonomy_fit="Partial Fit",
            taxonomy_issues=frozenset({"Other taxonomy problem"}),
            explanatory_note="A synthetic explanation.",
        )
    )
    assert validate_project(with_note).valid


def test_cannot_assess_is_excluded_from_taxonomy_defect_denominator():
    assert taxonomy_issue_denominator(
        ("Fit", "Partial Fit", "No Fit", "Cannot assess from register entry")
    ) == 2


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "fewer_than_10_descriptive_only"),
        (9, "fewer_than_10_descriptive_only"),
        (10, "10_to_29_low_support_caution"),
        (29, "10_to_29_low_support_caution"),
        (30, "30_or_more_standard_reporting"),
    ],
)
def test_support_bands_use_random_baseline_count_boundaries(count, expected):
    assert support_band(count) == expected


def test_macro_average_eligibility_starts_at_ten_baseline_positives():
    assert not macro_average_eligible(9)
    assert macro_average_eligible(10)


def test_diagnostic_majority_preserves_three_way_split():
    assert majority_diagnostic_rating(("Fit", "Fit", "No Fit")) == "Fit"
    assert majority_diagnostic_rating(
        ("Fit", "Partial Fit", "No Fit")
    ) == "No majority / split judgement"


def test_fixture_contains_no_real_ids_and_future_owner_cluster_is_synthetic():
    rows = load_wide_export(FIXTURE)
    assert all(row["source_record_id"].startswith("SYN-") for row in rows)
    assert all("/" not in row["source_record_id"] for row in rows)
    data = yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))
    owner = next(case for case in data["cases"] if case["case_id"] == "future_owner_multiple_responses")
    assert owner["owner_project_id"] == "SYN-OWNER-001"
    assert len(owner["responses"]) == 2
    assert owner["implementation_status"].startswith("schema fixture only")
