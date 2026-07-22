import copy

import pytest

from analysis.validation.instrument_sensitivity import (
    InstrumentSensitivityError,
    analyse_instrument_validity_sensitivity,
    validate_formal_candidate_0_7_rows,
)
from analysis.validation.schema import CoderRating, ModelRating, ProjectRatings


CODERS = ("C01", "C02", "C03")


def raw_row(assignment, record, reviewer, **updates):
    row = {
        "assignment_id": assignment,
        "source_record_id": record,
        "reviewer_id": reviewer,
        "instrument_ver": "redcap-candidate-0.7",
        "record_kind": "1",
        "review_stream": "1",
        "validation_included": "1",
        "sample_status": "1",
        "assignment_batch": "formal_validation",
        "sample_set": "1",
        "scratch_coder_complete": "2",
        "sc_exposure": "0",
        "sc_domains": [1],
        "sc_purposes": [1],
        "sc_covid": "0",
        "sc_equity": "0",
        "sc_sufficiency": "1",
        "sc_taxonomy_fit": "1",
        "sc_tax_issue": [],
        "sc_confidence": "1",
        "sc_note": "",
        "sc_exposure_note": "",
        "sc_blind_decl": "",
    }
    row.update(updates)
    return row


def rating(reviewer, domain):
    return CoderRating(
        reviewer, frozenset({domain}), frozenset({"Descriptive Monitoring"}),
        0, 0, "Sufficient", "Fit",
    )


def project(index, *, discordant=False):
    record = f"SYN-{index:03d}"
    domains = ["Health & Social Care"] * 3
    if discordant:
        domains[2] = "Crime & Justice"
    return ProjectRatings(
        record, "random_baseline",
        rating("C01", domains[0]), rating("C02", domains[1]), rating("C03", domains[2]),
        ModelRating(frozenset({"Health & Social Care"}), frozenset({"Descriptive Monitoring"}), 0, 0),
        "redcap-candidate-0.7", True,
    )


def rows_for(projects):
    rows = []
    serial = 1
    for item in projects:
        for reviewer in CODERS:
            rows.append(raw_row(f"A{serial:07d}", item.record_id, reviewer))
            serial += 1
    return rows


def test_actual_frozen_validator_filters_nonformal_streams_without_mutation():
    formal = raw_row("A0000001", "SYN-001", "C01", sc_exposure="1")
    declaration = raw_row("A0000002", "SYN-001", "C01", record_kind="2")
    owner = raw_row("A0000003", "SYN-001", "O01", review_stream="2")
    qa = raw_row(
        "A0000004", "SYN-001", "C01", record_kind="3",
        validation_included="0", sample_status="3",
    )
    historical = raw_row(
        "A0000005", "SYN-001", "C01",
        instrument_ver="redcap-candidate-0.3", record_kind="",
    )
    rows = [formal, declaration, owner, qa, historical]
    before = copy.deepcopy(rows)
    batch = validate_formal_candidate_0_7_rows(rows)
    assert rows == before
    assert batch.excluded_row_count == 4
    assert len(batch.results) == 1
    assert batch.results[0].issues == (
        "additional knowledge requires a source explanation",
    )


def test_whole_project_exclusion_recomputes_metrics_and_reports_differences():
    projects = tuple(project(i, discordant=(i in {11, 12})) for i in range(1, 13))
    rows = rows_for(projects)
    rows[-1]["sc_exposure"] = "1"
    results = validate_formal_candidate_0_7_rows(rows).results
    primary_before = copy.deepcopy(projects)
    report = analyse_instrument_validity_sensitivity(projects, results)
    assert projects == primary_before
    assert report.population.affected_response_count == 1
    assert report.population.affected_project_ids == ("SYN-012",)
    assert report.population.retained_project_count == 11
    alpha = next(
        item for item in report.replacement_estimates
        if item.dimension == "domains" and item.metric == "alpha_ABC"
    )
    assert alpha.primary_estimate != alpha.sensitivity_estimate
    assert alpha.difference == pytest.approx(
        alpha.sensitivity_estimate-alpha.primary_estimate
    )
    f1 = next(
        item for item in report.per_label_estimates
        if item.dimension == "domains"
        and item.label == "Health & Social Care"
        and item.metric == "f1"
    )
    assert f1.primary_estimate is not None
    assert f1.sensitivity_estimate is not None
    assert f1.difference == pytest.approx(
        (f1.sensitivity_estimate-f1.primary_estimate)*100
    )
    assert {
        item.panel for item in report.per_label_estimates
        if item.dimension == "domains"
        and item.label == "Health & Social Care"
        and item.metric == "cohen_kappa"
    } == {
        "C01_C02", "C01_C03", "C02_C03",
        "model_C01", "model_C02", "model_C03",
    }


def test_zero_affected_case_is_explicit_and_identical():
    projects = tuple(project(i, discordant=(i == 12)) for i in range(1, 13))
    report = analyse_instrument_validity_sensitivity(
        projects, validate_formal_candidate_0_7_rows(rows_for(projects)).results
    )
    assert report.population.affected_response_count == 0
    assert report.population.affected_project_count == 0
    assert report.population.retained_project_ids == report.population.primary_project_ids
    assert report.zero_affected_results_identical is True
    assert all(
        item.difference == 0
        for item in report.replacement_estimates
        if item.difference is not None
    )


def test_missing_duplicate_and_wrong_coder_panels_are_rejected():
    projects = (project(1),)
    rows = rows_for(projects)
    with pytest.raises(InstrumentSensitivityError, match="exactly three"):
        analyse_instrument_validity_sensitivity(
            projects, validate_formal_candidate_0_7_rows(rows[:-1]).results
        )
    duplicate_assignment = rows + [dict(rows[-1])]
    with pytest.raises(InstrumentSensitivityError, match="Duplicate assignment"):
        analyse_instrument_validity_sensitivity(
            projects,
            validate_formal_candidate_0_7_rows(duplicate_assignment).results,
        )
    duplicate = rows + [dict(rows[-1], assignment_id="A9999999")]
    with pytest.raises(InstrumentSensitivityError, match="exactly three"):
        analyse_instrument_validity_sensitivity(
            projects, validate_formal_candidate_0_7_rows(duplicate).results
        )
    wrong = [dict(row) for row in rows]
    wrong[-1]["reviewer_id"] = "C99"
    with pytest.raises(InstrumentSensitivityError, match="do not match"):
        analyse_instrument_validity_sensitivity(
            projects, validate_formal_candidate_0_7_rows(wrong).results
        )
