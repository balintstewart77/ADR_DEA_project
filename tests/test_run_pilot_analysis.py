from pathlib import Path

import pytest

from analysis.validation.redcap import DecodedScratchAssignment
from analysis.validation.run_pilot_analysis import (
    PilotAnalysisError,
    PilotDecodedAssignment,
    build_assignment_mapping,
    instrument_qc,
    validate_output_row_schema,
    validate_pilot_safety_configuration,
)
from analysis.validation.schema import CoderRating, UNCLEAR


def mapping_rows():
    return [
        {
            "assignment_id": f"SYN{record:02}{coder[-1]}",
            "source_record_id": f"SYN-{record:03}",
            "reviewer_id": coder,
            "review_stream": "1",
            "sample_set": "4",
            "validation_included": "0",
        }
        for record in range(1, 11)
        for coder in ("C01", "C02", "C03")
    ]


def test_complete_ten_by_three_mapping_passes_independent_of_row_order():
    rows = list(reversed(mapping_rows()))
    result = build_assignment_mapping(rows)
    assert not result.fatal
    assert result.observed_assignments == 30
    assert result.unique_records == 10
    assert result.coder_counts == {"C01": 10, "C02": 10, "C03": 10}
    assert not result.missing_combinations


def test_missing_coder_record_assignment_fails():
    result = build_assignment_mapping(mapping_rows()[:-1])
    assert result.fatal
    assert any(item.code == "missing_coder_record_combinations" for item in result.findings)


def test_duplicate_coder_record_assignment_fails():
    rows = mapping_rows()
    rows[-1] = dict(rows[0], assignment_id="SYN-DUPLICATE")
    result = build_assignment_mapping(rows)
    assert result.fatal
    assert any(item.code == "duplicate_coder_record" for item in result.findings)


def test_ambiguous_assignment_mapping_fails():
    rows = mapping_rows()
    rows[1] = dict(rows[1], assignment_id=rows[0]["assignment_id"])
    result = build_assignment_mapping(rows)
    assert result.fatal
    assert any(item.code == "ambiguous_assignment_mapping" for item in result.findings)


def test_mapping_is_never_inferred_from_row_position():
    rows = mapping_rows()
    rows[0] = dict(rows[0], reviewer_id="")
    result = build_assignment_mapping(rows)
    assert result.fatal
    assert result.rows[0]["mapping_status"] == "unmapped"
    assert result.rows[0]["coder_id"] == ""


def pilot_assignment(*, domains=None, purposes=None):
    domains = frozenset({"Education & Skills"}) if domains is None else frozenset(domains)
    purposes = frozenset({"Descriptive Monitoring"}) if purposes is None else frozenset(purposes)
    rating = CoderRating(
        reviewer_id="C01",
        domains=domains,
        purposes=purposes,
        equity_tag=0,
        covid_tag=0,
        register_sufficiency="Sufficient",
        taxonomy_fit="Fit",
        taxonomy_issues=frozenset(),
        complete=True,
        response_valid=True,
    )
    decoded = DecodedScratchAssignment(
        assignment_id="SYNASSIGN",
        reviewer_id="C01",
        record_id="SYN-001",
        sample_set="pilot",
        validation_included=False,
        instrument_version="redcap-candidate-0.3",
        rating=rating,
    )
    raw = {
        "sc_confidence": "1",
        "sc_sufficiency": "1",
        "sc_taxonomy_fit": "1",
        "sc_blind_decl": "1",
        "sc_exposure": "0",
        **{f"sc_tax_issue___{code}": "0" for code in range(1, 7)},
    }
    return PilotDecodedAssignment(decoded, "High", False, False, raw)


def test_unclear_plus_substantive_label_is_rejected_for_query():
    item = pilot_assignment(domains={UNCLEAR, "Education & Skills"})
    findings = instrument_qc(
        (item,), frozen_pilot_ids=frozenset({"SYN-001"}),
        instrument_version="redcap-candidate-0.3",
    )
    assert any(
        finding.code == "unclear_with_substantive_label"
        and finding.severity == "query_required"
        for finding in findings
    )


def test_more_than_two_purposes_is_rejected_for_query():
    item = pilot_assignment(purposes={"Descriptive Monitoring", "Outcome Tracking", "Risk Prediction / Early Identification"})
    findings = instrument_qc(
        (item,), frozen_pilot_ids=frozenset({"SYN-001"}),
        instrument_version="redcap-candidate-0.3",
    )
    assert any(
        finding.code == "purpose_maximum_exceeded"
        and finding.severity == "query_required"
        for finding in findings
    )


def test_output_schema_validation_rejects_missing_columns():
    with pytest.raises(PilotAnalysisError, match="unexpected schema"):
        validate_output_row_schema(("a", "b"), ({"a": 1},))


def test_pilot_runner_cannot_enable_formal_metrics_or_reveal_models():
    with pytest.raises(PilotAnalysisError, match="Formal validation metrics"):
        validate_pilot_safety_configuration(
            formal_validation_metrics=True, model_outputs_initially_hidden=True
        )
    with pytest.raises(PilotAnalysisError, match="keep model outputs hidden"):
        validate_pilot_safety_configuration(
            formal_validation_metrics=False, model_outputs_initially_hidden=False
        )
