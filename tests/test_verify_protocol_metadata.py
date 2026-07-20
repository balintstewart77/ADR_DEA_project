from scripts.verify_protocol_metadata import (
    DEFAULT_MANIFEST, REPOSITORY_ROOT, validate_protocol_status, verify_protocol_entry,
)


def candidate_row() -> dict[str, str]:
    return {
        "protocol_status": "review_candidate", "current_implementation_basis": "true",
        "frozen": "false", "registered": "false",
        "official_sample_draw_authorised": "false", "registration_identifier": "",
        "registration_timestamp": "",
    }


def test_canonical_v0_11_metadata_and_committed_bytes_verify_offline():
    assert verify_protocol_entry(REPOSITORY_ROOT / DEFAULT_MANIFEST, REPOSITORY_ROOT) == []


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
