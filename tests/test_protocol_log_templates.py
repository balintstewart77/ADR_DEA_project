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
        expected_rows = 2 if path.name in {
            "coding_clarification_log.csv", "instrument_change_log.csv"
        } else 1
        assert len(rows) == expected_rows
        assert rows[0]
    with (PACKAGE / "coding_clarification_log.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        entries = list(csv.DictReader(handle))
    assert len(entries) == 1
    entry = entries[0]
    assert entry["phase"] == "pre-formal pilot calibration"
    assert entry["circulation_status"] == "circulated"
    assert entry["circulated_at"] == "2026-07-21"
    assert entry["simultaneous_circulation"] == "yes"
    assert entry["feedback_received_from_all_coders"] == "yes"
    assert entry["no_further_substantive_concerns"] == "yes"
    assert entry["no_pilot_recoding_requested"] == "yes"
    assert entry["no_coder_specific_performance_circulated"] == "yes"
    assert entry["no_model_output_shown"] == "yes"

    with (PACKAGE / "instrument_change_log.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        instrument_entries = list(csv.DictReader(handle))
    assert len(instrument_entries) == 1
    instrument = instrument_entries[0]
    assert instrument["change_id"] == "REDCAP-006"
    assert instrument["instrument_version"] == "redcap-candidate-0.6"
    assert instrument["classification_rule_change"] == "no"
    assert "all three responded" in instrument["evidence_or_reason"]
    assert "Candidate-0.3 pilot responses remain unchanged" in (
        instrument["pilot_or_formal_data_effect"]
    )
    assert "live REDCap runtime QA" in instrument["status"]


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
