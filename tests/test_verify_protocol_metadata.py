import csv

from scripts.verify_protocol_metadata import (
    DEFAULT_MANIFEST, REPOSITORY_ROOT, REQUIRED_PENDING_GATES,
    validate_protocol_status, verify_protocol_entry,
)


def candidate_row() -> dict[str, str]:
    return {
        "protocol_status": "review_candidate", "current_implementation_basis": "true",
        "frozen": "false", "registered": "false",
        "official_sample_draw_authorised": "false", "registration_identifier": "",
        "registration_timestamp": "",
    }


def test_canonical_v0_15_working_candidate_metadata_verifies_offline():
    assert verify_protocol_entry(REPOSITORY_ROOT / DEFAULT_MANIFEST, REPOSITORY_ROOT) == []


def test_feedback_closure_is_removed_from_pending_protocol_gates():
    assert not any("feedback" in gate.lower() for gate in REQUIRED_PENDING_GATES)
    assert REQUIRED_PENDING_GATES[0] == (
        "Complete project-owner instrument implementation, live QA and freeze"
    )
    assert "Complete Jo's final substantive review" in REQUIRED_PENDING_GATES


def test_review_candidate_cannot_be_frozen():
    row = candidate_row()
    row["frozen"] = "true"
    assert "review_candidate cannot be frozen" in validate_protocol_status(row)


def test_registration_requires_metadata_and_freeze():
    row = candidate_row()
    row["registered"] = "true"
    issues = validate_protocol_status(row)
    assert "registered protocol lacks registration_identifier" in issues
    assert "registered protocol lacks registration_timestamp" in issues
    assert "registered protocol must be frozen" in issues


def test_official_draw_requires_freeze_and_registration():
    row = candidate_row()
    row["official_sample_draw_authorised"] = "true"
    issues = validate_protocol_status(row)
    assert "official sample draw cannot be authorised before final freeze" in issues
    assert "official sample draw cannot be authorised before registration" in issues


def test_falsely_missing_current_protocol_still_fails(tmp_path):
    manifest = tmp_path / "manifest.csv"
    row = candidate_row() | {
        "artefact_group": "00_protocol",
        "version": "v0.15",
        "supersedes": "v0.14",
        "superseded_by": "",
        "notes": "candidate 0.7 live QA complete frozen formal instrument; candidate 0.6 imported and superseded before final runtime QA; closed coder feedback; separate project-owner live QA gate",
        "current_path": "missing-v0.15.docx",
    }
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    issues = verify_protocol_entry(manifest, tmp_path, version="v0.15")
    assert "declared protocol path does not exist: missing-v0.15.docx" in issues
