import csv
from pathlib import Path


PACKAGE = Path("preregistration/package/09_logs_and_templates")
EXPECTED = {
    "protocol_deviation_log.csv",
    "instrument_change_log.csv",
    "coding_clarification_log.csv",
    "jo_review_decision_log.csv",
}


def test_required_log_files_and_post_pilot_governance_entry():
    assert {path.name for path in PACKAGE.glob("*.csv")} == EXPECTED
    for path in PACKAGE.glob("*.csv"):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        expected_rows = 4 if path.name == "instrument_change_log.csv" else 3 if path.name == "coding_clarification_log.csv" else 1
        assert len(rows) == expected_rows
        assert rows[0]
    with (PACKAGE / "coding_clarification_log.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        entries = list(csv.DictReader(handle))
    assert len(entries) == 2
    by_id = {row["clarification_id"]: row for row in entries}
    assert set(by_id) == {"CAL-PILOT-001", "CAL-STATUS-002"}
    entry = by_id["CAL-PILOT-001"]
    assert entry["phase"] == "pre-formal pilot calibration"
    assert entry["circulation_status"] == "circulated"
    assert entry["circulated_at"] == "2026-07-21"
    assert entry["simultaneous_circulation"] == "yes"
    assert entry["feedback_received_from_all_coders"] == "yes"
    assert entry["no_further_substantive_concerns"] == "yes"
    assert entry["no_pilot_recoding_requested"] == "yes"
    assert entry["no_coder_specific_performance_circulated"] == "yes"
    assert entry["no_model_output_shown"] == "yes"
    status = by_id["CAL-STATUS-002"]
    assert status["date_raised"] == "2026-07-22"
    assert "candidate 0.7" in status["general_clarification"].lower()
    assert "150-field formal instrument" in status["general_clarification"]
    assert "no formal assignments are populated" in status["general_clarification"].lower()
    assert "formal sampling and assignment import remain prohibited" in status["status"]

    with (PACKAGE / "instrument_change_log.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        instrument_entries = list(csv.DictReader(handle))
    assert len(instrument_entries) == 3
    historical, instrument, freeze = instrument_entries
    assert historical["change_id"] == "REDCAP-006"
    assert historical["instrument_version"] == "redcap-candidate-0.6"
    assert "all three responded" in historical["evidence_or_reason"]
    assert instrument["change_id"] == "REDCAP-007"
    assert instrument["instrument_version"] == "redcap-candidate-0.7"
    assert instrument["classification_rule_change"] == "no"
    assert "Exposure can vary by project" in instrument["evidence_or_reason"]
    assert "Candidate-0.3 pilot responses" in instrument["pilot_or_formal_data_effect"]
    assert "remain unchanged" in instrument["pilot_or_formal_data_effect"]
    assert "live-runtime-QA" in instrument["status"]
    assert freeze["change_id"] == "REDCAP-008"
    assert freeze["instrument_version"] == "redcap-candidate-0.7"
    assert freeze["classification_rule_change"] == "no"
    assert "residual mismatches were zero" in freeze["evidence_or_reason"]
    assert "no formal sample" in freeze["pilot_or_formal_data_effect"]
    assert "Frozen; live-QA complete" in freeze["status"]


def test_dated_pilot_feedback_log_records_feedback_closure_without_approval():
    text = Path(
        "preregistration/package/05_training_and_pilot/pilot_feedback_log_20260717.md"
    ).read_text(encoding="utf-8")
    assert "Status: coder feedback closed and resolved" in text
    assert "close of play on Wednesday 22 July 2026" in text
    assert "All three coders responded" in text
    assert "not treated as formal approval or endorsement" in text
    assert "Coder feedback resolved; formal-instrument freeze and live REDCap QA pending." in text
    assert "prepared_for_circulation" not in text
