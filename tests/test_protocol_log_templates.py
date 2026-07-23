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
        expected_rows = 9 if path.name == "instrument_change_log.csv" else 3 if path.name == "coding_clarification_log.csv" else 1
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
    assert len(instrument_entries) == 8
    (
        historical,
        instrument,
        freeze,
        owner,
        owner_preimport,
        taxonomy_correction,
        taxonomy_approval,
        import_correction,
    ) = instrument_entries
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
    assert owner["change_id"] == "REDCAP-009"
    assert owner["instrument_version"] == "owner-redcap-candidate-0.3"
    assert owner["classification_rule_change"] == "no"
    assert "4 domains, 2 purposes and 2 tags" in owner["evidence_or_reason"]
    assert owner["pilot_or_formal_data_effect"].startswith("No real participant data")
    assert "REDCap connection was created" in owner["pilot_or_formal_data_effect"]
    assert "unfrozen" in owner["status"]
    assert owner_preimport["change_id"] == "REDCAP-010"
    assert owner_preimport["instrument_version"] == "owner-redcap-candidate-0.3"
    assert owner_preimport["classification_rule_change"] == "no"
    assert "four-level visibility scale" in owner_preimport["change_description"]
    assert "No protocol or participant-facing Word document was edited" in owner_preimport["protocol_effect"]
    assert "20 taxonomy definitions remain pending human approval" in owner_preimport["status"]
    assert taxonomy_correction["change_id"] == "REDCAP-011"
    assert taxonomy_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert taxonomy_correction["classification_rule_change"] == "no"
    assert "Layer-qualified mapping" in taxonomy_correction["evidence_or_reason"]
    assert "@MAXCHECKED=2" in taxonomy_correction["change_description"]
    assert "all 22 taxonomy definitions remain pending human approval" in taxonomy_correction["status"]
    assert taxonomy_approval["change_id"] == "REDCAP-012"
    assert taxonomy_approval["instrument_version"] == "owner-redcap-candidate-0.3"
    assert taxonomy_approval["classification_rule_change"] == "no"
    assert "Balint Stewart's approval of all 22" in taxonomy_approval["change_description"]
    assert "eight exact microdefinition revisions" in taxonomy_approval["change_description"]
    assert "No protocol or participant-facing Word document was edited" in taxonomy_approval["protocol_effect"]
    assert "taxonomy wording approved for participant use" in taxonomy_approval["status"]
    assert import_correction["change_id"] == "REDCAP-013"
    assert import_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert import_correction["field_or_component"] == "public_register_url Text Validation Type"
    assert import_correction["classification_rule_change"] == "no"
    assert "unsupported url validation type" in import_correction["change_description"]
    assert "No protocol, taxonomy, participant-facing document" in import_correction["protocol_effect"]
    assert "pre-import correction" in import_correction["protocol_effect"]


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
