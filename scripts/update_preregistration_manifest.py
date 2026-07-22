#!/usr/bin/env python3
"""Refresh or check computed provenance in the preregistration manifest.

Only ``sha256``, ``created_or_modified_at``, ``source_commit``, and
``size_bytes`` are changed. Descriptions, classifications, proposed paths, and
notes are preserved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("preregistration/preregistration_artifact_manifest.csv")
COMPUTED_COLUMNS = ("sha256", "created_or_modified_at", "source_commit", "size_bytes")
REQUIRED_COLUMNS = (
    "artifact_id",
    "current_path",
    "current_state",
    "access_class",
    *COMPUTED_COLUMNS,
)
SKIP_STATES = {"missing", "placeholder", "not_yet_generated"}
RESTRICTED_ACCESS = {"restricted", "temporarily_embargoed"}
PERSONAL_DATA_ACCESS = "contains_personal_data"
RESTRICTED_DIRECTORY = "preregistration_restricted"


class ManifestError(RuntimeError):
    """Raised for invalid manifest or repository configuration."""


@dataclass
class RefreshResult:
    checked: int = 0
    updated: int = 0
    skipped: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest without loading the full file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def modified_at_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(
        timespec="seconds"
    )


def current_git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ManifestError(f"Cannot determine Git commit for {repo_root}: {exc}") from exc
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ManifestError(f"Git returned an invalid commit hash: {commit!r}")
    return commit


def _load_manifest(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ManifestError(f"Manifest has no header: {path}")
            fieldnames = list(reader.fieldnames)
            missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
            if missing_columns:
                raise ManifestError(
                    f"Manifest lacks required columns: {', '.join(missing_columns)}"
                )
            rows = list(reader)
    except UnicodeDecodeError as exc:
        raise ManifestError(f"Manifest is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise ManifestError(f"Cannot read manifest {path}: {exc}") from exc

    shifted_rows = [index for index, row in enumerate(rows, start=2) if None in row]
    if shifted_rows:
        raise ManifestError(
            "Manifest rows contain values beyond the declared columns: "
            + ", ".join(str(index) for index in shifted_rows)
        )

    identifiers = [row.get("artifact_id", "").strip() for row in rows]
    if any(not identifier for identifier in identifiers):
        raise ManifestError("Every manifest row must have a non-empty artifact_id")
    duplicates = sorted(identifier for identifier in set(identifiers) if identifiers.count(identifier) > 1)
    if duplicates:
        raise ManifestError(f"Duplicate artifact_id values: {', '.join(duplicates)}")
    return fieldnames, rows


def _write_manifest(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
        raise ManifestError(f"Cannot write manifest {path}: {exc}") from exc


def _resolve_current_path(repo_root: Path, current_path: str) -> Path:
    candidate = (repo_root / current_path).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ManifestError(f"current_path escapes repository root: {current_path}") from exc
    return candidate


def _path_is_restricted(current_path: str) -> bool:
    return RESTRICTED_DIRECTORY in Path(current_path).parts


def refresh_manifest(
    manifest_path: Path,
    repo_root: Path,
    *,
    check: bool = False,
    include_restricted: bool = False,
    source_commit: str | None = None,
) -> RefreshResult:
    """Check or refresh computed fields and return a non-content diagnostic."""
    repo_root = repo_root.resolve()
    manifest_path = manifest_path.resolve()
    fieldnames, rows = _load_manifest(manifest_path)
    commit = source_commit or current_git_commit(repo_root)
    result = RefreshResult()

    for row in rows:
        artifact_id = row["artifact_id"].strip()
        state = row.get("current_state", "").strip()
        current_path = row.get("current_path", "").strip()
        access_class = row.get("access_class", "").strip()

        if state in SKIP_STATES or not current_path:
            result.skipped.append(f"{artifact_id}: no existing path to hash")
            continue
        if access_class == PERSONAL_DATA_ACCESS:
            result.skipped.append(f"{artifact_id}: personal-data content is never hashed")
            continue
        restricted = access_class in RESTRICTED_ACCESS or _path_is_restricted(current_path)
        if restricted and not include_restricted:
            result.skipped.append(f"{artifact_id}: restricted path skipped")
            continue

        try:
            path = _resolve_current_path(repo_root, current_path)
        except ManifestError as exc:
            result.issues.append(f"{artifact_id}: {exc}")
            continue
        if not path.is_file():
            result.issues.append(f"{artifact_id}: existing path is not a file: {current_path}")
            continue

        digest = sha256_file(path)
        modified = modified_at_utc(path)
        result.checked += 1
        expected = {
            "sha256": digest,
            "created_or_modified_at": modified,
            "source_commit": commit,
            "size_bytes": str(path.stat().st_size),
        }
        stale = [column for column, value in expected.items() if row.get(column, "") != value]
        if check:
            if stale:
                result.issues.append(
                    f"{artifact_id}: stale {', '.join(stale)} for {current_path}"
                )
            continue

        if stale:
            for column, value in expected.items():
                row[column] = value
            result.updated += 1

    if not check and result.updated:
        _write_manifest(manifest_path, fieldnames, rows)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh SHA-256, file size, modification time, and Git commit metadata "
            "for existing non-sensitive preregistration artefacts."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest path, relative to --repo-root by default",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="Repository root used to resolve current_path values",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale computed metadata without modifying the manifest",
    )
    parser.add_argument(
        "--include-restricted",
        action="store_true",
        help=(
            "Opt in to hashing restricted or embargoed paths. Personal-data rows "
            "are still skipped. Do not use for the public manifest without approval."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    try:
        result = refresh_manifest(
            manifest_path,
            repo_root,
            check=args.check,
            include_restricted=args.include_restricted,
        )
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    mode = "checked" if args.check else "refreshed"
    print(
        f"Manifest {mode}: {result.checked} existing non-sensitive files checked; "
        f"{result.updated} rows updated; {len(result.skipped)} rows skipped."
    )
    for issue in result.issues:
        print(f"issue: {issue}", file=sys.stderr)
    return 1 if result.issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
