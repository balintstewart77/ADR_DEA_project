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
DEFAULT_VERSION = "v0.11"
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
GIT_OBJECT = re.compile(r"[0-9a-f]{40,64}")
REQUIRED_PENDING_GATES = (
    "Complete the excluded pilot and pilot debrief",
    "Close the dated pilot-feedback log",
    "Complete Jo's final substantive review",
    "Resolve and propagate all resulting changes",
    "Complete final cross-document and repository consistency checks",
    "Create and freeze the final preregistration protocol",
    "Submit and verify the official preregistration",
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
    for field, expected in {
        "protocol_status": "review_candidate", "supersedes": "v0.10", "superseded_by": "",
    }.items():
        if (row.get(field) or "").strip() != expected:
            issues.append(f"{field} must be {expected!r} for {version}")

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
    try:
        committed_oid = str(_git(repo_root, "rev-parse", f"{source_commit}:{relative}")).strip()
        committed_bytes = bytes(_git(repo_root, "cat-file", "blob", committed_oid, binary=True))
        source_details = str(
            _git(repo_root, "show", "-s", "--format=%cI%n%s", source_commit)
        ).splitlines()
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
    if gates != REQUIRED_PENDING_GATES:
        issues.append("pending_gates does not match the required ordered v0.11 gates")
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
