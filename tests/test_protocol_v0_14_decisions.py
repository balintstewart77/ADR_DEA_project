import csv
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import yaml


PROTOCOL = Path(
    "preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.14.docx"
)
SPECIFICATION = Path(
    "preregistration/package/04_exclusions_and_sampling/sampling_specification.yaml"
)
MANIFEST = Path("preregistration/preregistration_artifact_manifest.csv")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def protocol_text() -> str:
    with zipfile.ZipFile(PROTOCOL) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.iter(W + "t"))
        for paragraph in root.iter(W + "p")
    )


def manifest_rows() -> dict[str, dict[str, str]]:
    with MANIFEST.open(encoding="utf-8-sig", newline="") as handle:
        return {row["artifact_id"]: row for row in csv.DictReader(handle)}


def test_v0_14_is_the_lean_unfrozen_review_candidate():
    text = protocol_text()
    assert "Review candidate v0.14 | prepared 22 July 2026" in text
    assert "not frozen, registered, or authorised for formal sampling" in text
    assert "1,308 retained register record-units representing 1,304 unique official Project IDs" in text
    assert "yielding 675 coder–project classifications in total" in text
    assert "The declaration and per-assignment exposure disclosure are specified in Section 7.1" in text
    assert "candidate 0.7 passed administrator and restricted-user live QA and was frozen" in text
    assert "No formal validation assignments have been populated" in text


def test_v0_14_preserves_type_7_and_matched_panel_sensitivity():
    text = protocol_text()
    assert "Hyndman–Fan Type 7 interpolation" in text
    assert "equivalent to NumPy/Pandas linear quantile interpolation" in text
    assert "failing any structural-validity rule encoded in the frozen candidate-0.7 offline validator" in text
    assert "will not be silently repaired or reinterpreted" in text
    assert "remain flagged in the primary analysis" in text
    assert "exclude every project containing at least one affected response" in text
    assert "headline replacement-panel alpha and applicable per-label estimates" in text
    assert "does not apply to the project-owner stream" in text


def test_v0_14_adjudication_and_sampling_rules_remain_explicit():
    text = protocol_text()
    assert "project completing primary adjudication" in text
    assert "If N = 0 the random audit size is zero; otherwise it is ceil(0.20 × N)" in text
    assert "sampled without replacement using SEED_ADJUDICATION_AUDIT = 20260715" in text
    assert "Overlap is allowed but does not reduce the required random draw" in text
    assert "Active and reserve identities will be generated only after registration and authorisation" in text
    assert "unused reserve identities remain embargoed while eligible for a clean retest" in text


def test_sampling_design_is_rebound_without_execution_or_design_change():
    specification = yaml.safe_load(SPECIFICATION.read_text(encoding="utf-8"))
    assert specification["protocol_basis"] == {
        "version": "v0.14",
        "path": "preregistration/package/00_protocol/Validation_Protocol_PreReg_v0.14.docx",
        "status": "review_candidate",
        "current_implementation_basis": True,
        "frozen": False,
        "registered": False,
        "official_sample_draw_authorised": False,
    }
    assert specification["prospective_boundary"]["official_draw_executed"] is False
    assert specification["prospective_boundary"]["official_sample_exists"] is False
    assert specification["randomisation"]["master_seed"] == 20260713
    assert specification["baseline"]["active_n"] == 150
    assert specification["baseline"]["reserve_n"] == 100
    assert {
        key: specification["hard_active"][key]
        for key in ("total_n", "domain_only_n", "purpose_only_n", "both_n")
    } == {
        "total_n": 75, "domain_only_n": 25,
        "purpose_only_n": 25, "both_n": 25,
    }
    assert specification["hard_reserve"]["target_n"] == 50
    assert specification["hard_reserve"]["initial_allocation"]["seat_counts"] == [17, 17, 16]


def test_sam_003_manifest_row_is_column_aligned():
    row = manifest_rows()["SAM-003"]
    assert row["current_path"] == (
        "preregistration/package/04_exclusions_and_sampling/official_sampling_runbook.md"
    )
    assert row["proposed_package_path"] == row["current_path"]
    assert row["description"] == "Controlled one-page runbook for the future Gate 2 official draw"
    assert row["version"] == "runbook-1.0-rc1"
    assert row["current_state"] == "existing"
    assert row["status_at_registration"] == "draft_template"
    assert row["pre_existing_or_prospective"] == "prospective"
    assert row["access_class"] == "public"
    assert row["registration_inclusion"] == "include"
    assert row["authoritative_status"] == "supporting_current_candidate"
    assert row["supersedes_or_superseded_by"] == "SAM-001"


def test_manifest_has_one_current_v0_14_protocol_and_v0_13_history():
    rows = manifest_rows()
    current = rows["PRO-008"]
    assert current["version"] == "v0.14"
    assert current["protocol_status"] == "review_candidate"
    assert current["current_implementation_basis"] == "true"
    assert current["frozen"] == current["registered"] == "false"
    assert current["official_sample_draw_authorised"] == "false"
    assert rows["PRO-006"]["version"] == "v0.13"
    assert rows["PRO-006"]["superseded_by"] == "v0.14"
    assert rows["PRO-006"]["current_implementation_basis"] == "false"
    assert rows["PRO-007"]["supersedes_or_superseded_by"] == ""
