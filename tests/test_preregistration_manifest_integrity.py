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
    assert len(manifest_rows) == 244
    redcap = {
        row["artifact_id"]: row
        for row in manifest_rows
        if row["artifact_id"].startswith("RED-0")
    }
    assert set(f"RED-{number:03d}" for number in range(54, 82)) <= set(redcap)
    assert redcap["RED-054"]["version"] == "owner-redcap-candidate-0.2"
    assert redcap["RED-054"]["current_state"] == "historical_candidate"
    assert redcap["RED-054"]["authoritative_status"] == "superseded_unfrozen_candidate"
    assert redcap["RED-068"]["version"] == "owner-redcap-candidate-0.3"
    assert redcap["RED-068"]["current_state"] == "working_candidate"
    assert redcap["RED-068"]["authoritative_status"] == "current_candidate"
    assert redcap["RED-080"]["version"] == "owner-redcap-candidate-0.3"
    assert redcap["RED-080"]["authoritative_status"] == "supporting_current_candidate"
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
    assert "not approved for participant use" in invitation["notes"]
    assert "not yet aligned" in invitation["notes"]
    identifiers = [row["artifact_id"] for row in manifest_rows]
    assert len(identifiers) == len(set(identifiers))
    identifier_set = set(identifiers)
    assert not any(row["current_state"] in {"missing", "needs_verification"} for row in manifest_rows)
    assert not any(row["registration_inclusion"] == "undecided" for row in manifest_rows)

    for row in manifest_rows:
        for token in filter(None, RELATIONSHIP_SPLIT.split(row["supersedes_or_superseded_by"])):
            assert token in identifier_set, (row["artifact_id"], token)

    current_protocols = [
        row for row in manifest_rows if row["protocol_status"] == "review_candidate"
    ]
    assert [row["artifact_id"] for row in current_protocols] == ["PRO-012"]
    protocol = current_protocols[0]
    assert protocol["version"] == "v0.15"
    assert protocol["frozen"] == "false"
    assert protocol["registered"] == "false"
    assert protocol["official_sample_draw_authorised"] == "false"


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
    assert len(pilot_rows) == 14
    assert all(row["access_class"] == "restricted" for row in pilot_rows)
    assert all(row["registration_inclusion"] == "exclude" for row in pilot_rows)

    protocol = next(row for row in manifest_rows if row["artifact_id"] == "PRO-012")
    protocol_path = ROOT / protocol["current_path"]
    assert protocol_path.is_file()
    assert protocol["size_bytes"] == str(protocol_path.stat().st_size) == "3223383"
    assert protocol["sha256"] == "5eff044b4f8d488e84a5b49720d35318add4f29ef53136cb6ce9c2b197409ee7"

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
