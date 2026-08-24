"""File loading, integrity verification, and manifest resolution."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import AUTHORITY_IDS, MANIFEST, RAW_EXPORT, ROOT


@dataclass(frozen=True)
class AuthorityCheck:
    role: str
    manifest_id: str
    path: str
    expected_sha256: str
    observed_sha256: str
    size_bytes: int
    matched: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_rows(path: Path = MANIFEST) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_manifest_row(artifact_id: str) -> dict[str, str]:
    matches = [row for row in manifest_rows() if row["artifact_id"] == artifact_id]
    if len(matches) != 1:
        raise ValueError(f"Manifest ID {artifact_id} resolved {len(matches)} times")
    return matches[0]


def _manifest_hash(path: Path, expected: str) -> tuple[str, int, bool]:
    raw = path.read_bytes()
    raw_hash = hashlib.sha256(raw).hexdigest()
    if raw_hash == expected:
        return raw_hash, len(raw), True
    lf = raw.replace(b"\r\n", b"\n")
    lf_hash = hashlib.sha256(lf).hexdigest()
    return lf_hash, len(lf), lf_hash == expected


def verify_authorities() -> tuple[AuthorityCheck, ...]:
    checks: list[AuthorityCheck] = []
    for role, manifest_id in AUTHORITY_IDS.items():
        row = resolve_manifest_row(manifest_id)
        path = ROOT / row["current_path"]
        if not path.is_file():
            raise FileNotFoundError(f"Missing authority {manifest_id}: {row['current_path']}")
        observed, represented_size, matched = _manifest_hash(path, row["sha256"])
        check = AuthorityCheck(
            role=role,
            manifest_id=manifest_id,
            path=row["current_path"],
            expected_sha256=row["sha256"],
            observed_sha256=observed,
            size_bytes=path.stat().st_size,
            matched=matched,
        )
        if not matched:
            raise ValueError(f"Authority hash mismatch: {manifest_id}")
        if row["size_bytes"] and int(row["size_bytes"]) != represented_size:
            raise ValueError(f"Authority size mismatch: {manifest_id}")
        checks.append(check)
    expected_model = "6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299"
    model = next(item for item in checks if item.role == "production_model")
    if model.expected_sha256 != expected_model:
        raise ValueError("Protected Fable 5 identity differs from the protocol instruction")
    expected_protocol = "fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77"
    protocol = next(item for item in checks if item.role == "protocol")
    if protocol.expected_sha256 != expected_protocol:
        raise ValueError("Protocol identity differs from PRO-018")
    return tuple(checks)


def load_frozen_export(path: Path = RAW_EXPORT) -> pd.DataFrame:
    """Load the hash-pinned raw export without altering it."""

    row = resolve_manifest_row("POST-028")
    if path.resolve() != (ROOT / row["current_path"]).resolve():
        raise ValueError("Raw export path differs from POST-028")
    if sha256_file(path) != row["sha256"]:
        raise ValueError("Frozen raw export hash mismatch")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def read_manifest_csv(artifact_id: str) -> pd.DataFrame:
    row = resolve_manifest_row(artifact_id)
    return pd.read_csv(ROOT / row["current_path"], dtype=str, keep_default_na=False, encoding="utf-8-sig")


def semicolon_set(value: str) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(part.strip() for part in value.split(";") if part.strip())


def assert_unique(values: Iterable[str], *, context: str) -> None:
    sequence = tuple(values)
    if len(sequence) != len(set(sequence)):
        raise ValueError(f"Duplicate values in {context}")
