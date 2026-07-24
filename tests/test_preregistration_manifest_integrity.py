from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "preregistration/preregistration_artifact_manifest.csv"
FUTURE_STATES = {"not_yet_generated", "placeholder"}
HISTORICAL_STATE = "historical_git_only"
RESTRICTED_ACCESS = {"restricted", "temporarily_embargoed", "contains_personal_data"}
RELATIONSHIP_SPLIT = re.compile(r"\s*[;|]\s*")


def rows() -> list[dict[str, str]]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        parsed = list(reader)
    assert all(None not in row for row in parsed)
    return parsed


def test_manifest_structure_statuses_and_relationships() -> None:
    manifest_rows = rows()
    identifiers = [row["artifact_id"] for row in manifest_rows]
    assert all(re.fullmatch(r"[A-Z]+-\d{3}", artifact_id) for artifact_id in identifiers)
    assert len(manifest_rows) == len(identifiers) == len(set(identifiers))
    redcap = {
        row["artifact_id"]: row
        for row in manifest_rows
        if row["artifact_id"].startswith("RED-0")
    }
    redcap_sequence = sorted(int(artifact_id.split("-")[1]) for artifact_id in redcap)
    assert redcap_sequence == list(range(redcap_sequence[0], redcap_sequence[-1] + 1))
    assert f"RED-{redcap_sequence[-1]:03d}" == "RED-085"
    assert redcap["RED-054"]["version"] == "owner-redcap-candidate-0.2"
    assert redcap["RED-054"]["current_state"] == "historical_candidate"
    assert redcap["RED-054"]["authoritative_status"] == "superseded_unfrozen_candidate"
    assert redcap["RED-068"]["version"] == "owner-redcap-candidate-0.3"
    assert redcap["RED-068"]["current_state"] == "working_candidate"
    assert redcap["RED-068"]["authoritative_status"] == "current_candidate"
    assert redcap["RED-080"]["version"] == "owner-redcap-candidate-0.3"
    assert redcap["RED-080"]["authoritative_status"] == "supporting_current_candidate"
    formatting_audit = redcap["RED-082"]
    assert formatting_audit["version"] == "owner-redcap-candidate-0.3"
    assert formatting_audit["authoritative_status"] == "supporting_current_candidate"
    assert "18 participant-visible descriptive fields" in formatting_audit["notes"]
    information_v2 = redcap["RED-083"]
    questionnaire_v2 = redcap["RED-084"]
    questionnaire_v3 = redcap["RED-085"]
    assert information_v2["version"] == "project-owner-information-v2"
    assert questionnaire_v2["version"] == "project-owner-review-questionnaire-v2"
    assert information_v2["authoritative_status"] == "current_ethics_review_material"
    assert questionnaire_v2["authoritative_status"] == "superseded_ethics_review_material"
    assert questionnaire_v3["version"] == "project-owner-review-questionnaire-v3"
    assert questionnaire_v3["authoritative_status"] == "current_ethics_review_material"
    assert redcap["RED-066"]["authoritative_status"] == "superseded_ethics_review_material"
    assert redcap["RED-067"]["authoritative_status"] == "superseded_ethics_review_material"
    invitation = redcap["RED-081"]
    assert invitation["version"] == ""
    assert invitation["current_state"] == "working_candidate"
    assert invitation["status_at_registration"] == "draft_template"
    assert invitation["pre_existing_or_prospective"] == "prospective"
    assert invitation["access_class"] == "public"
    assert invitation["registration_inclusion"] == "include"
    assert invitation["authoritative_status"] == "supporting_current_candidate"
    assert invitation["frozen"] == "false"
    assert invitation["registered"] == "false"
    assert "not approved for participant use" in invitation["notes"].lower()
    assert "retained byte-for-byte" in invitation["notes"]
    identifier_set = set(identifiers)
    assert not any(row["current_state"] in {"missing", "needs_verification"} for row in manifest_rows)
    assert not any(row["registration_inclusion"] == "undecided" for row in manifest_rows)

    for row in manifest_rows:
        for token in filter(None, RELATIONSHIP_SPLIT.split(row["supersedes_or_superseded_by"])):
            assert token in identifier_set, (row["artifact_id"], token)

    current_protocols = [
        row for row in manifest_rows
        if row["current_implementation_basis"] == "true"
    ]
    assert [row["artifact_id"] for row in current_protocols] == ["PRO-017"]
    current_protocol = current_protocols[0]
    assert current_protocol["version"] == "v1.0"
    assert current_protocol["protocol_status"] == "frozen"
    assert current_protocol["frozen"] == "true"
    assert current_protocol["registered"] == "false"
    assert current_protocol["official_sample_draw_authorised"] == "false"
    documentation_protocols = [
        row for row in manifest_rows
        if row["protocol_status"] == "documentation_review_candidate"
    ]
    assert documentation_protocols == []



def test_paths_ownership_and_tracked_preregistration_coverage() -> None:
    manifest_rows = rows()
    owners: dict[str, list[dict[str, str]]] = defaultdict(list)
    covered: set[str] = set()
    for row in manifest_rows:
        current_path = row["current_path"]
        proposed_path = row["proposed_package_path"]
        if current_path:
            owners[current_path].append(row)
            covered.add(current_path)
        if proposed_path:
            covered.add(proposed_path)
        if row["current_state"] in FUTURE_STATES:
            assert not current_path
            assert not (ROOT / proposed_path).exists()
        elif row["current_state"] == HISTORICAL_STATE:
            assert not current_path
            assert not proposed_path
            assert row["registration_inclusion"] == "exclude"
            assert len(row["sha256"]) == 64
            assert row["size_bytes"].isdigit()
            assert row["source_commit"]
        elif current_path:
            assert (ROOT / current_path).is_file(), (row["artifact_id"], current_path)

    duplicates = {path: group for path, group in owners.items() if len(group) > 1}
    assert set(duplicates) == {"analysis/register_cleaning.py"}
    duplicate_rows = duplicates["analysis/register_cleaning.py"]
    physical = [row for row in duplicate_rows if row["authoritative_status"] != "conceptual_alias"]
    aliases = [row for row in duplicate_rows if row["authoritative_status"] == "conceptual_alias"]
    assert [row["artifact_id"] for row in physical] == ["SRC-004"]
    assert [row["artifact_id"] for row in aliases] == ["SRC-007"]
    assert aliases[0]["registration_inclusion"] == "exclude"
    assert aliases[0]["proposed_package_path"] == ""

    tracked = subprocess.run(
        ["git", "ls-files", "preregistration"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    excluded_structure = {
        "preregistration/preregistration_artifact_manifest.csv",
        *[path for path in tracked if path.endswith("/.gitkeep")],
        *[
            f"preregistration/package/00_protocol/{row['filename']}"
            for row in manifest_rows if row["current_state"] == HISTORICAL_STATE
        ],
    }
    assert not [path for path in tracked if path not in covered | excluded_structure]


def test_computed_metadata_and_restricted_pilot_treatment() -> None:
    manifest_rows = rows()
    for row in manifest_rows:
        current_path = row["current_path"]
        if not current_path or row["current_state"] in FUTURE_STATES | {HISTORICAL_STATE}:
            continue
        if row["access_class"] in RESTRICTED_ACCESS:
            assert row["registration_inclusion"] != "include"
            assert row["sha256"] == ""
            assert row["size_bytes"] == ""
            continue
        path = ROOT / current_path
        assert row["size_bytes"] == str(path.stat().st_size), row["artifact_id"]
        assert len(row["sha256"]) == 64, row["artifact_id"]

    pilot_rows = [row for row in manifest_rows if "TRN-018" <= row["artifact_id"] <= "TRN-031"]
    pilot_sequence = sorted(int(row["artifact_id"].split("-")[1]) for row in pilot_rows)
    assert pilot_sequence[0] == 18
    assert pilot_sequence[-1] == 31
    assert pilot_sequence == list(range(pilot_sequence[0], pilot_sequence[-1] + 1))
    assert all(row["access_class"] == "restricted" for row in pilot_rows)
    assert all(row["registration_inclusion"] == "exclude" for row in pilot_rows)

    protocol = next(row for row in manifest_rows if row["artifact_id"] == "PRO-013")
    protocol_path = ROOT / protocol["current_path"]
    assert protocol_path.is_file()
    assert protocol["size_bytes"] == str(protocol_path.stat().st_size)
    assert protocol["sha256"] == hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    predecessor = next(row for row in manifest_rows if row["artifact_id"] == "PRO-016")
    assert predecessor["version"] == "v0.18"
    assert predecessor["current_state"] == "superseded"
    assert predecessor["current_implementation_basis"] == "false"
    assert predecessor["superseded_by"] == "v1.0"
    assert predecessor["sha256"] == "d12dca15723c702028e5f73634b8b147abb584a22362aea6d5586d26ee3d3a19"
    assert predecessor["size_bytes"] == "3228034"
    assert hashlib.sha256((ROOT / predecessor["current_path"]).read_bytes()).hexdigest() == predecessor["sha256"]
    current = next(row for row in manifest_rows if row["artifact_id"] == "PRO-017")
    assert current["version"] == "v1.0"
    assert current["supersedes"] == "v0.18"
    assert current["sha256"] == "6d385f40443e96b0b8cc774610b5d0ff6947ae43dff42576aa1a84c90dc8906e"
    assert current["size_bytes"] == "413327"

    historical = [row for row in manifest_rows if row["current_state"] == HISTORICAL_STATE]
    assert {row["version"] for row in historical} == {
        "0.9", "0.10", "v0.11", "v0.12", "v0.13", "v0.14"
    }
    assert all(row["current_path"] == "" for row in historical)
    assert all(row["sha256"] and row["size_bytes"] and row["source_commit"] for row in historical)
    for row in historical:
        historical_path = f"preregistration/package/00_protocol/{row['filename']}"
        content = subprocess.run(
            ["git", "show", f"{row['source_commit']}:{historical_path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert hashlib.sha256(content).hexdigest() == row["sha256"]
        assert len(content) == int(row["size_bytes"])


def test_no_package_detritus_or_generated_scientific_outputs() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "preregistration"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    prohibited = [
        path for path in tracked
        if Path(path).name == ".Rhistory"
        or Path(path).name.startswith("~$")
        or "__pycache__" in Path(path).parts
        or path.endswith((".pyc", ".tmp"))
    ]
    assert not prohibited
    for row in rows():
        if row["current_state"] == "not_yet_generated":
            assert not (ROOT / row["proposed_package_path"]).exists()
    assert not (ROOT / "preregistration/package/00_protocol/Validation_Protocol_PreReg_final.pdf").exists()
