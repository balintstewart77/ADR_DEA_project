#!/usr/bin/env python3
"""Verify protocol provenance and status in the canonical artifact manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("preregistration/preregistration_artifact_manifest.csv")
DEFAULT_VERSION = "v1.1"
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
GIT_OBJECT = re.compile(r"[0-9a-f]{40,64}")
REQUIRED_PENDING_GATES = (
    "Record the subsequent formal-sampling authorisation gate",
)


class ProtocolMetadataError(RuntimeError):
    """Raised when protocol metadata cannot be inspected."""


def _git(repo_root: Path, *args: str, binary: bool = False) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo_root, check=True,
            capture_output=True, text=not binary,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProtocolMetadataError(f"Git command failed: git {' '.join(args)}") from exc
    return result.stdout


def _boolean(row: Mapping[str, str], field: str, issues: list[str]) -> bool | None:
    value = (row.get(field) or "").strip().lower()
    if value not in {"true", "false"}:
        issues.append(f"{field} must be exactly true or false")
        return None
    return value == "true"


def validate_protocol_status(row: Mapping[str, str]) -> list[str]:
    """Reject combinations that could authorise premature study activity."""

    issues: list[str] = []
    status = (row.get("protocol_status") or "").strip()
    frozen = _boolean(row, "frozen", issues)
    registered = _boolean(row, "registered", issues)
    draw_authorised = _boolean(row, "official_sample_draw_authorised", issues)
    implementation_basis = _boolean(row, "current_implementation_basis", issues)
    if status == "review_candidate" and frozen is True:
        issues.append("review_candidate cannot be frozen")
    if registered is True:
        if not (row.get("registration_identifier") or "").strip():
            issues.append("registered protocol lacks registration_identifier")
        if not (row.get("registration_timestamp") or "").strip():
            issues.append("registered protocol lacks registration_timestamp")
        if frozen is not True:
            issues.append("registered protocol must be frozen")
    if draw_authorised is True and frozen is not True:
        issues.append("official sample draw cannot be authorised before final freeze")
    if draw_authorised is True and registered is not True:
        issues.append("official sample draw cannot be authorised before registration")
    if status == "review_candidate" and implementation_basis is not True:
        issues.append("current review candidate must be the current implementation basis")
    if status == "documentation_review_candidate" and implementation_basis is not False:
        issues.append("documentation review candidate cannot replace the analysis implementation basis")
    if status == "frozen":
        if frozen is not True:
            issues.append("frozen protocol status requires frozen=true")
        if implementation_basis is not True:
            issues.append("frozen protocol must be the current implementation basis")
    return issues


def _load_protocol_row(manifest_path: Path, version: str) -> dict[str, str]:
    try:
        with manifest_path.open("r", encoding="utf-8", newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if row.get("artefact_group") == "00_protocol" and row.get("version") == version
            ]
    except OSError as exc:
        raise ProtocolMetadataError(f"Cannot read manifest: {manifest_path}") from exc
    if len(rows) != 1:
        raise ProtocolMetadataError(
            f"Expected exactly one 00_protocol row for {version}; found {len(rows)}"
        )
    return rows[0]


def verify_protocol_entry(
    manifest_path: Path, repo_root: Path, *, version: str = DEFAULT_VERSION,
) -> list[str]:
    """Return deterministic verification issues; an empty list means success."""

    repo_root = repo_root.resolve()
    row = _load_protocol_row(manifest_path.resolve(), version)
    issues = validate_protocol_status(row)
    expected_predecessor = {
        "v1.1": "v1.0", "v1.0": "v0.18", "v0.18": "v0.17",
        "v0.17": "v0.16", "v0.16": "v0.15", "v0.15": "v0.14", "v0.14": "v0.13", "v0.13": "v0.12",
        "v0.12": "v0.11", "v0.11": "v0.10",
    }.get(version)
    if expected_predecessor is None:
        raise ProtocolMetadataError(f"No protocol predecessor rule is defined for {version}")
    expected_status = {
        "v1.1": "frozen",
        "v1.0": "superseded_frozen_protocol",
        "v0.18": "superseded_review_candidate",
        "v0.17": "superseded_review_candidate",
    }.get(version, "review_candidate")
    expected_successor = {
        "v1.1": "", "v1.0": "v1.1", "v0.18": "v1.0",
        "v0.17": "v0.18", "v0.16": "v0.17", "v0.15": "v0.16",
        "v0.14": "v0.15", "v0.13": "v0.14", "v0.12": "v0.13",
        "v0.11": "v0.12",
    }[version]
    for field, expected in {
        "protocol_status": expected_status,
        "supersedes": expected_predecessor,
        "superseded_by": expected_successor,
    }.items():
        if (row.get(field) or "").strip() != expected:
            issues.append(f"{field} must be {expected!r} for {version}")
    if version in {"v0.15", "v0.16", "v0.17", "v0.18", "v1.0", "v1.1"}:
        notes = (row.get("notes") or "").strip()
        if "candidate 0.7" not in notes:
            issues.append(f"{version} notes must identify candidate 0.7 as the frozen scratch instrument")
        if "live QA complete" not in notes or "frozen formal instrument" not in notes:
            issues.append(f"{version} notes must record candidate 0.7 live QA and instrument freeze")
        if "candidate 0.6" not in notes or "imported" not in notes or "superseded before final runtime QA" not in notes:
            issues.append(f"{version} notes must record candidate 0.6 as an imported intermediate superseded before final runtime QA")
        if "candidate 0.5" in notes:
            issues.append(f"{version} notes retain a stale current-candidate 0.5 reference")
        if "closed coder feedback" not in notes:
            issues.append(f"{version} notes must record closed coder feedback")
        if "separate project-owner" not in notes or "live QA" not in notes:
            issues.append(f"{version} notes must record the separate project-owner instrument gate")
        if version in {"v0.16", "v0.17"}:
            if "one personalised Survey Queue" not in notes:
                issues.append(f"{version} notes must record the one-link Project Owner alignment")
            if "live QA remains pending" not in notes:
                issues.append(f"{version} notes must not imply Project Owner live QA is complete")
        if version == "v0.17" and "optional enrichment" not in notes:
            issues.append("v0.17 notes must record the reduced mandatory free-text rule")
        if version == "v0.18" and "superseded directly by frozen v1.0" not in notes:
            issues.append("v0.18 notes must record direct supersession by frozen v1.0")
        if version == "v1.0" and "superseded directly by frozen v1.1" not in notes:
            issues.append("v1.0 notes must record direct supersession by frozen v1.1")
        if version == "v1.1":
            if "OSF registration 8sn2j approved" not in notes:
                issues.append("v1.1 notes must record the approved OSF registration")
            if "project_lead_reported" not in notes:
                issues.append("v1.1 notes must record the registration evidence basis")
            if "Typographical rendering correction only" not in notes:
                issues.append("v1.1 notes must identify the typographical-only correction")

    relative = (row.get("current_path") or "").strip()
    posix_path = PurePosixPath(relative)
    if not relative or posix_path.is_absolute() or ".." in posix_path.parts:
        issues.append("current_path must be a canonical repository-relative path")
        return issues
    protocol_path = (repo_root / Path(*posix_path.parts)).resolve()
    try:
        protocol_path.relative_to(repo_root)
    except ValueError:
        issues.append("current_path escapes the repository")
        return issues
    if not protocol_path.is_file():
        issues.append(f"declared protocol path does not exist: {relative}")
        return issues

    content = protocol_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != (row.get("sha256") or "").strip():
        issues.append("working protocol SHA-256 differs from manifest")
    try:
        expected_size = int((row.get("size_bytes") or "").strip())
    except ValueError:
        issues.append("size_bytes must be an integer")
    else:
        if len(content) != expected_size:
            issues.append("working protocol size differs from manifest")

    source_commit = (row.get("protocol_source_commit") or "").strip()
    implementation_commit = (row.get("implementation_last_checked_commit") or "").strip()
    blob_oid = (row.get("git_blob_oid") or "").strip()
    if not FULL_COMMIT.fullmatch(source_commit):
        issues.append("protocol_source_commit must be a full lowercase 40-character commit hash")
        return issues
    if not FULL_COMMIT.fullmatch(implementation_commit):
        issues.append("implementation_last_checked_commit must be a full lowercase 40-character commit hash")
    if not GIT_OBJECT.fullmatch(blob_oid):
        issues.append("git_blob_oid must be a full lowercase Git object ID")
    source_kind = (row.get("protocol_source_kind") or "").strip()
    if source_kind not in {"committed_blob", "working_tree_candidate"}:
        issues.append("protocol_source_kind must be committed_blob or working_tree_candidate")
        return issues
    try:
        current_oid = str(_git(repo_root, "hash-object", relative)).strip()
        source_details = str(
            _git(repo_root, "show", "-s", "--format=%cI%n%s", source_commit)
        ).splitlines()
    except ProtocolMetadataError as exc:
        issues.append(str(exc))
        return issues
    if current_oid != blob_oid:
        issues.append("working protocol Git object ID differs from manifest")
    if source_kind == "committed_blob":
        try:
            committed_oid = str(
                _git(repo_root, "rev-parse", f"{source_commit}:{relative}")
            ).strip()
            committed_bytes = bytes(
                _git(repo_root, "cat-file", "blob", committed_oid, binary=True)
            )
        except ProtocolMetadataError as exc:
            issues.append(str(exc))
            return issues
        if committed_oid != blob_oid:
            issues.append("protocol source commit contains a different Git blob than declared")
        if hashlib.sha256(committed_bytes).hexdigest() != (row.get("sha256") or "").strip():
            issues.append("committed protocol SHA-256 differs from manifest")
        if len(committed_bytes) != len(content):
            issues.append("committed protocol size differs from working protocol")
    if len(source_details) < 2:
        issues.append("could not read protocol source commit date and message")
    else:
        if source_details[0] != (row.get("protocol_source_commit_date") or "").strip():
            issues.append("protocol_source_commit_date differs from Git")
        if source_details[1] != (row.get("protocol_source_commit_message") or "").strip():
            issues.append("protocol_source_commit_message differs from Git")
    try:
        date.fromisoformat((row.get("metadata_generated_on") or "").strip())
    except ValueError:
        issues.append("metadata_generated_on must be an ISO-8601 calendar date")
    gates = tuple(
        value.strip() for value in (row.get("pending_gates") or "").split(" | ") if value.strip()
    )
    if version == "v1.1" and gates != REQUIRED_PENDING_GATES:
        issues.append(f"pending_gates does not match the required ordered {version} gates")
    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = args.manifest if args.manifest.is_absolute() else args.repo_root / args.manifest
    try:
        issues = verify_protocol_entry(manifest, args.repo_root, version=args.version)
    except ProtocolMetadataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if issues:
        for issue in issues:
            print(f"issue: {issue}", file=sys.stderr)
        return 1
    print(f"Protocol metadata verified: {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
