import csv
import re
from pathlib import Path


PACKAGE = Path("preregistration/package/09_logs_and_templates")
EXPECTED = {
    "protocol_deviation_log.csv",
    "instrument_change_log.csv",
    "coding_clarification_log.csv",
    "jo_review_decision_log.csv",
}
INSTRUMENT_LOG_REQUIRED_COLUMNS = {
    "change_id",
    "date_identified",
    "instrument_version",
    "field_or_component",
    "change_description",
    "evidence_or_reason",
    "classification_rule_change",
    "protocol_effect",
    "pilot_or_formal_data_effect",
    "approval",
    "implemented_version",
    "implemented_date",
    "status",
}
INSTRUMENT_CHANGE_ID = re.compile(r"^REDCAP-(\d{3})$")
NEWEST_INSTRUMENT_CHANGE_ID = "REDCAP-020"


def test_required_log_files_and_post_pilot_governance_entry():
    assert {path.name for path in PACKAGE.glob("*.csv")} == EXPECTED
    for path in PACKAGE.glob("*.csv"):
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert reader.fieldnames
    with (PACKAGE / "coding_clarification_log.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        entries = list(csv.DictReader(handle))
    by_id = {row["clarification_id"]: row for row in entries}
    assert len(entries) == len(by_id)
    assert all(re.fullmatch(r"CAL-[A-Z]+-\d{3}", entry_id) for entry_id in by_id)
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
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert INSTRUMENT_LOG_REQUIRED_COLUMNS <= set(reader.fieldnames)
        instrument_entries = list(reader)
    instrument_ids = [row["change_id"] for row in instrument_entries]
    assert all(INSTRUMENT_CHANGE_ID.fullmatch(entry_id) for entry_id in instrument_ids)
    assert len(instrument_entries) == len(instrument_ids) == len(set(instrument_ids))
    sequence = [int(INSTRUMENT_CHANGE_ID.fullmatch(entry_id).group(1)) for entry_id in instrument_ids]
    assert sequence == list(range(sequence[0], sequence[-1] + 1))
    assert instrument_ids[-1] == NEWEST_INSTRUMENT_CHANGE_ID
    assert all(
        row[column].strip()
        for row in instrument_entries
        for column in INSTRUMENT_LOG_REQUIRED_COLUMNS
    )
    instrument_by_id = {row["change_id"]: row for row in instrument_entries}
    historical = instrument_by_id["REDCAP-006"]
    instrument = instrument_by_id["REDCAP-007"]
    freeze = instrument_by_id["REDCAP-008"]
    owner = instrument_by_id["REDCAP-009"]
    owner_preimport = instrument_by_id["REDCAP-010"]
    taxonomy_correction = instrument_by_id["REDCAP-011"]
    taxonomy_approval = instrument_by_id["REDCAP-012"]
    import_correction = instrument_by_id["REDCAP-013"]
    fixture_correction = instrument_by_id["REDCAP-014"]
    participant_note_correction = instrument_by_id["REDCAP-015"]
    current_live_qa_correction = instrument_by_id["REDCAP-016"]
    documentation_alignment = instrument_by_id["REDCAP-017"]
    overview_live_qa_correction = instrument_by_id["REDCAP-018"]
    wording_only_correction = instrument_by_id["REDCAP-019"]
    burden_reduction = instrument_by_id[NEWEST_INSTRUMENT_CHANGE_ID]
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
    assert fixture_correction["change_id"] == "REDCAP-014"
    assert fixture_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert fixture_correction["field_or_component"] == "synthetic Data Import Tool fixture columns"
    assert fixture_correction["classification_rule_change"] == "no"
    assert "descriptive fields" in fixture_correction["change_description"]
    assert "unexpanded checkbox base variables" in fixture_correction["change_description"]
    assert "three owners, 19 pre-created assignments and 22 rows" in fixture_correction["pilot_or_formal_data_effect"]
    assert participant_note_correction["change_id"] == "REDCAP-015"
    assert participant_note_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert participant_note_correction["field_or_component"] == "intended_recipient participant-visible field note"
    assert participant_note_correction["classification_rule_change"] == "no"
    assert "Field Note is now blank" in participant_note_correction["change_description"]
    assert "manual Stop Action" in participant_note_correction["protocol_effect"]
    assert current_live_qa_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert current_live_qa_correction["classification_rule_change"] == "no"
    assert "eight combined proposed-classification basis fields" in current_live_qa_correction["change_description"]
    assert "controlled synthetic dictionary re-import" in current_live_qa_correction["status"]
    assert documentation_alignment["instrument_version"] == "owner-redcap-candidate-0.3"
    assert documentation_alignment["classification_rule_change"] == "no"
    assert "one personalised Survey Queue link" in documentation_alignment["change_description"]
    assert "final 22-record exclusion set" in documentation_alignment["protocol_effect"]
    assert "invitation email are preserved unchanged" in documentation_alignment["pilot_or_formal_data_effect"]
    assert "live QA" in documentation_alignment["status"]
    assert overview_live_qa_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert overview_live_qa_correction["classification_rule_change"] == "no"
    assert "classification overview" in overview_live_qa_correction["change_description"]
    assert "Save & Return Later" in overview_live_qa_correction["change_description"]
    assert "po_suff_explain" in overview_live_qa_correction["change_description"]
    assert "display support only" in overview_live_qa_correction["protocol_effect"]
    assert "19 assignments and 22 rows" in overview_live_qa_correction["pilot_or_formal_data_effect"]
    assert "controlled dictionary/fixture re-import" in overview_live_qa_correction["approval"]
    assert wording_only_correction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert wording_only_correction["classification_rule_change"] == "no"
    assert "20 conditional per-question labels" in wording_only_correction["change_description"]
    assert "Is the basis for this tag status visible" in wording_only_correction["change_description"]
    assert "108 fields" in wording_only_correction["pilot_or_formal_data_effect"]
    assert "DEV-001" in wording_only_correction["protocol_effect"]
    assert burden_reduction["instrument_version"] == "owner-redcap-candidate-0.3"
    assert burden_reduction["classification_rule_change"] == "no"
    assert "explicit disagreement" in burden_reduction["change_description"]
    assert "optional" in burden_reduction["change_description"]
    assert "Questionnaire v3" in burden_reduction["change_description"]
    assert "protocol candidate v0.17" in burden_reduction["change_description"]
    assert "108 fields" in burden_reduction["pilot_or_formal_data_effect"]
    assert burden_reduction["date_identified"] == "2026-07-23"

    with (PACKAGE / "protocol_deviation_log.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        deviation_reader = csv.DictReader(handle)
        assert deviation_reader.fieldnames is not None
        deviation_entries = list(deviation_reader)
    required_deviation_columns = {
        "deviation_id", "date_identified", "study_stage", "protocol_section",
        "description", "reason", "affected_records_or_outputs", "temporary_action",
        "substantive", "amendment_required", "resolution", "resolved_date",
        "reviewer", "status",
    }
    assert required_deviation_columns <= set(deviation_reader.fieldnames)
    assert [row["deviation_id"] for row in deviation_entries] == ["DEV-001"]
    deviation = deviation_entries[0]
    assert all(deviation[column].strip() for column in required_deviation_columns)
    assert deviation["substantive"] == "no"
    assert deviation["amendment_required"] == "no"
    assert deviation["status"] == "applied"
    assert deviation["resolved_date"] == "2026-07-23"
    assert deviation["reviewer"] == "Balint Stewart"
    assert "Validation_Protocol_PreReg_v0.17.docx" in deviation["resolution"]
    assert "before analysis begins" in deviation["resolution"] or "before analysis begins" in deviation["description"]


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
