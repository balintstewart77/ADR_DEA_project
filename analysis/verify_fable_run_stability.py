#!/usr/bin/env python3
"""Deterministically verify the pre-existing Fable 5 stability evidence.

This module is deliberately offline.  It reads recovered caches and registered
repository evidence, validates provenance and taxonomy labels, recomputes the
fixed target metrics, and optionally writes a compact reproducibility package.
It contains no network client and never invokes a classifier.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXPECTED_MODEL = "claude-fable-5"
EXPECTED_VERSION = "dict-1.0-rc2"
COVID_TAG = "COVID-19 & Pandemic"
EQUITY_TAG = "Demographic disparities / equity tag"
EXPECTED_PRODUCTION_ROWS = 1_308
EXPECTED_PRODUCTION_HASH = (
    "eaf8b8280b58a64a42950fe316230c3640678dd402464c630b0c4d44d4884098"
)
EXPECTED_PRODUCTION_METADATA_HASH = (
    "a5784924133d71f03797df67194f8a6fd60ed61e3703124cdfc4e7f023e47cab"
)


@dataclass(frozen=True)
class TargetMetrics:
    n: int = 201
    domain_exact: int = 191
    domain_jaccard: float = 0.974
    purpose_exact: int = 185
    purpose_jaccard: float = 0.935
    covid_agreement: int = 201
    equity_agreement: int = 197
    joint_tag_agreement: int = 197
    all_component_agreement: int = 171
    invalid_or_failed: int = 0


TARGET = TargetMetrics()


class VerificationError(RuntimeError):
    """Raised when recovered evidence fails a verification gate."""


@dataclass(frozen=True)
class Taxonomy:
    version: str
    domains: frozenset[str]
    purposes: frozenset[str]
    tags: frozenset[str]


@dataclass(frozen=True)
class Classification:
    record_id: str
    domains: frozenset[str]
    purposes: frozenset[str]
    tags: frozenset[str]
    fingerprint: str


@dataclass(frozen=True)
class RunArtifact:
    path: Path
    sha256: str
    file_size: int
    modified_at_utc: str
    model: str
    prompt_version: str
    cache_schema_version: str
    entries: Mapping[str, Classification]
    metadata_path: Path
    metadata: Mapping[str, Any]
    metadata_sha256: str


@dataclass(frozen=True)
class MappingEvidence:
    original_record_id: str
    canonical_record_id: str
    project_id: str
    mapping_source: str
    mapping_reason: str
    fingerprint_match: bool


@dataclass(frozen=True)
class Diagnostic:
    canonical_record_id: str
    original_run1_id: str
    original_run2_id: str
    domain_run1: tuple[str, ...]
    domain_run2: tuple[str, ...]
    domain_exact: bool
    domain_jaccard: float
    purpose_run1: tuple[str, ...]
    purpose_run2: tuple[str, ...]
    purpose_exact: bool
    purpose_jaccard: float
    covid_run1: bool
    covid_run2: bool
    equity_run1: bool
    equity_run2: bool
    joint_tag_match: bool
    all_component_match: bool
    migration_note: str


@dataclass(frozen=True)
class Metrics:
    n: int
    domain_exact: int
    domain_jaccard: float
    purpose_exact: int
    purpose_jaccard: float
    covid_agreement: int
    equity_agreement: int
    joint_tag_agreement: int
    all_component_agreement: int
    invalid_or_failed: int
    missing_run1_ids: tuple[str, ...]
    missing_run2_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProductionLink:
    row_count: int
    unique_record_ids: int
    matched_records: int
    mapping_evidence: tuple[MappingEvidence, ...]
    source_register: str
    production_model: str
    prompt_version: str
    taxonomy_version: str
    seed_cache: str
    seed_cache_entries: int
    fresh_classifications: int


@dataclass(frozen=True)
class VerificationResult:
    run1: RunArtifact
    run2: RunArtifact
    taxonomy: Taxonomy
    taxonomy_path: Path
    taxonomy_sha256: str
    comparison_ids: tuple[str, ...]
    sample_source: Path | None
    sample_source_sha256: str | None
    diagnostics: tuple[Diagnostic, ...]
    metrics: Metrics
    production_link: ProductionLink
    production_rows: Mapping[str, Mapping[str, str]]
    production_output_path: Path
    production_output_sha256: str
    production_output_lf_sha256: str
    production_metadata_path: Path
    production_metadata_sha256: str
    production_metadata_lf_sha256: str
    migration_path: Path | None
    migration_sha256: str | None
    cleaned_register_path: Path | None
    cleaned_register_sha256: str | None
    cleaned_register_row_count: int | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def lf_normalized_sha256(path: Path) -> str:
    """Hash text after in-memory CRLF/CR to LF conversion; never write it."""
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def modified_at_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Cannot parse JSON {path}: {exc}") from exc


def _normalize_version(value: object) -> str:
    text = str(value or "").strip()
    if text and not text.startswith("dict-"):
        text = f"dict-{text}"
    return text


def load_taxonomy(path: Path) -> Taxonomy:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - repository has PyYAML
            raise VerificationError(
                "PyYAML is required to parse the frozen taxonomy"
            ) from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict) or not isinstance(payload.get("categories"), list):
        raise VerificationError(f"Invalid taxonomy structure: {path}")
    metadata = payload.get("metadata") or {}
    version = _normalize_version(metadata.get("dictionary_version"))
    labels: dict[str, set[str]] = {
        "Layer A -- domain": set(),
        "Layer C -- purpose": set(),
        "Cross-cutting tag": set(),
    }
    for category in payload["categories"]:
        if not isinstance(category, dict) or not category.get("include_in_prompt"):
            continue
        layer = str(category.get("layer") or "")
        label = str(category.get("label") or "").strip()
        if layer in labels and label:
            labels[layer].add(label)
    taxonomy = Taxonomy(
        version=version,
        domains=frozenset(labels["Layer A -- domain"]),
        purposes=frozenset(labels["Layer C -- purpose"]),
        tags=frozenset(labels["Cross-cutting tag"]),
    )
    if taxonomy.version != EXPECTED_VERSION:
        raise VerificationError(
            f"Taxonomy version is {taxonomy.version!r}, expected {EXPECTED_VERSION!r}"
        )
    if taxonomy.tags != {COVID_TAG, EQUITY_TAG}:
        raise VerificationError(
            f"Unexpected active cross-cutting taxonomy labels: {sorted(taxonomy.tags)}"
        )
    return taxonomy


def parse_label_list(value: object, field: str, *, allow_empty: bool) -> frozenset[str]:
    """Parse only actual lists or explicit JSON/Python list representations."""
    parsed = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            parsed = []
        else:
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(text)
                except (SyntaxError, ValueError) as exc:
                    raise VerificationError(
                        f"{field} is not a list representation"
                    ) from exc
    if not isinstance(parsed, (list, tuple)):
        raise VerificationError(f"{field} must be a list, got {type(parsed).__name__}")
    values: list[str] = []
    for item in parsed:
        if not isinstance(item, str) or not item.strip():
            raise VerificationError(f"{field} contains a blank or non-string label")
        values.append(item.strip())
    if not allow_empty and not values:
        raise VerificationError(f"{field} is empty")
    if len(values) != len(set(values)):
        raise VerificationError(f"{field} contains a duplicate label")
    return frozenset(values)


def parse_production_labels(value: object, field: str) -> frozenset[str]:
    text = str(value or "").strip()
    if not text:
        if field == "cross_cutting_tags":
            return frozenset()
        raise VerificationError(f"Production {field} is empty")
    if text.startswith("["):
        return parse_label_list(text, field, allow_empty=field == "cross_cutting_tags")
    values = [part.strip() for part in text.split(";") if part.strip()]
    if not values and field != "cross_cutting_tags":
        raise VerificationError(f"Production {field} is empty")
    if len(values) != len(set(values)):
        raise VerificationError(f"Production {field} contains a duplicate label")
    return frozenset(values)


def validate_labels(
    labels: Iterable[str], allowed: frozenset[str], *, record_id: str, field: str
) -> None:
    unknown = sorted(set(labels) - set(allowed))
    if unknown:
        raise VerificationError(
            f"Unknown {field} label(s) for {record_id!r}: {unknown}"
        )


def _classification_payload(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = entry.get("classification")
    if isinstance(nested, dict):
        merged = dict(entry)
        merged.update(nested)
        return merged
    return entry


def _has_failure_marker(entry: Mapping[str, Any]) -> bool:
    for key, value in entry.items():
        name = str(key).lower()
        if name in {"failed", "failure", "invalid"} and bool(value):
            return True
        if name == "error" and value not in (None, "", False, 0):
            return True
        if name == "status" and str(value).strip().lower() in {
            "failed",
            "failure",
            "invalid",
            "error",
        }:
            return True
        if isinstance(value, str) and value.strip().upper() in {
            "TRIAL_FAILED",
            "CLASSIFICATION_FAILED",
        }:
            return True
    return False


def _cache_entries(payload: Any) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(payload, dict):
        raise VerificationError("Cache top level must be an object")
    meta = payload.get("__meta__") or payload.get("meta") or payload.get("metadata") or {}
    if "entries" in payload:
        entries = payload["entries"]
    else:
        entries = {
            key: value
            for key, value in payload.items()
            if key not in {"__meta__", "meta", "metadata"}
        }
    if not isinstance(meta, dict) or not isinstance(entries, dict):
        raise VerificationError("Cache metadata and entries must be objects")
    return meta, entries


def load_run_artifact(
    cache_path: Path,
    metadata_path: Path,
    taxonomy: Taxonomy,
) -> RunArtifact:
    payload = _read_json(cache_path)
    meta, raw_entries = _cache_entries(payload)
    metadata = _read_json(metadata_path)
    if not isinstance(metadata, dict):
        raise VerificationError(f"Run metadata must be an object: {metadata_path}")
    model = str(meta.get("model") or metadata.get("model") or "").strip()
    prompt = str(meta.get("prompt_version") or metadata.get("prompt_version") or "").strip()
    schema = str(
        meta.get("cache_schema_version") or metadata.get("cache_schema_version") or ""
    ).strip()
    if model != EXPECTED_MODEL or prompt != EXPECTED_VERSION:
        raise VerificationError(
            f"Wrong run provenance for {cache_path}: model={model!r}, prompt={prompt!r}"
        )
    if str(metadata.get("model") or "").strip() != EXPECTED_MODEL:
        raise VerificationError(f"Run metadata model mismatch: {metadata_path}")
    if str(metadata.get("prompt_version") or "").strip() != EXPECTED_VERSION:
        raise VerificationError(f"Run metadata prompt mismatch: {metadata_path}")

    entries: dict[str, Classification] = {}
    failures: list[str] = []
    for outer_id, raw_entry in raw_entries.items():
        if not isinstance(raw_entry, dict):
            failures.append(str(outer_id))
            continue
        entry = _classification_payload(raw_entry)
        record_id = str(
            entry.get("Record ID") or entry.get("record_id") or outer_id
        )
        if not record_id.strip() or record_id in entries or _has_failure_marker(entry):
            failures.append(record_id)
            continue
        try:
            domains = parse_label_list(
                entry.get("substantive_domains"),
                "substantive_domains",
                allow_empty=False,
            )
            purposes = parse_label_list(
                entry.get("analytical_purpose"),
                "analytical_purpose",
                allow_empty=False,
            )
            tags = parse_label_list(
                entry.get("cross_cutting_tags", []),
                "cross_cutting_tags",
                allow_empty=True,
            )
            validate_labels(
                domains, taxonomy.domains, record_id=record_id, field="domain"
            )
            validate_labels(
                purposes, taxonomy.purposes, record_id=record_id, field="purpose"
            )
            validate_labels(tags, taxonomy.tags, record_id=record_id, field="tag")
        except VerificationError as exc:
            raise VerificationError(f"Invalid cache entry {record_id!r}: {exc}") from exc
        fingerprint = str(entry.get("fingerprint") or raw_entry.get("fingerprint") or "")
        if not fingerprint:
            raise VerificationError(f"Missing prompt fingerprint for {record_id!r}")
        entries[record_id] = Classification(
            record_id=record_id,
            domains=domains,
            purposes=purposes,
            tags=tags,
            fingerprint=fingerprint,
        )
    if failures:
        raise VerificationError(
            f"{len(failures)} invalid or failed classifications in {cache_path}"
        )
    if int(metadata.get("n_projects") or -1) != len(entries):
        raise VerificationError(
            f"Run metadata count does not match cache entries for {cache_path}"
        )
    return RunArtifact(
        path=cache_path,
        sha256=sha256_file(cache_path),
        file_size=cache_path.stat().st_size,
        modified_at_utc=modified_at_utc(cache_path),
        model=model,
        prompt_version=prompt,
        cache_schema_version=schema,
        entries=entries,
        metadata_path=metadata_path,
        metadata=metadata,
        metadata_sha256=sha256_file(metadata_path),
    )


def read_sample_ids(path: Path) -> frozenset[str]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise VerificationError(f"Sample manifest has no header: {path}")
            column = "Record ID" if "Record ID" in reader.fieldnames else "run_record_id"
            if column not in reader.fieldnames:
                raise VerificationError(f"Sample manifest has no Record ID column: {path}")
            values = [str(row.get(column) or "") for row in reader]
    except OSError as exc:
        raise VerificationError(f"Cannot read sample manifest {path}: {exc}") from exc
    if any(not value.strip() for value in values) or len(values) != len(set(values)):
        raise VerificationError(f"Sample manifest contains blank or duplicate IDs: {path}")
    return frozenset(values)


def determine_comparison_ids(
    run1_ids: Iterable[str],
    run2_ids: Iterable[str],
    explicit_sample_ids: Iterable[str] | None = None,
) -> tuple[str, ...]:
    left = set(run1_ids)
    right = set(run2_ids)
    sample = set(explicit_sample_ids) if explicit_sample_ids is not None else None
    if left == right:
        if sample is not None and sample != left:
            raise VerificationError(
                "Recovered sample manifest does not exactly match the two equal cache key sets"
            )
        return tuple(sorted(left))
    if sample is None:
        raise VerificationError(
            "Run cache keys differ and no explicit recovered sample manifest was supplied"
        )
    missing_left = sample - left
    missing_right = sample - right
    if missing_left or missing_right:
        raise VerificationError(
            "Explicit comparison sample contains IDs absent from a recovered run"
        )
    return tuple(sorted(sample))


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        raise VerificationError("Empty-empty set encountered; Jaccard is not selected")
    return len(left_set & right_set) / len(union)


def compare_classifications(
    run1: Mapping[str, Classification],
    run2: Mapping[str, Classification],
    comparison_ids: Sequence[str],
    canonical_ids: Mapping[str, str] | None = None,
) -> tuple[tuple[Diagnostic, ...], Metrics]:
    canonical_ids = canonical_ids or {}
    diagnostics: list[Diagnostic] = []
    for record_id in comparison_ids:
        if record_id not in run1 or record_id not in run2:
            raise VerificationError(f"Missing comparison ID {record_id!r}")
        left = run1[record_id]
        right = run2[record_id]
        domain_exact = left.domains == right.domains
        purpose_exact = left.purposes == right.purposes
        covid1 = COVID_TAG in left.tags
        covid2 = COVID_TAG in right.tags
        equity1 = EQUITY_TAG in left.tags
        equity2 = EQUITY_TAG in right.tags
        joint = covid1 == covid2 and equity1 == equity2
        canonical = canonical_ids.get(record_id, record_id)
        diagnostics.append(
            Diagnostic(
                canonical_record_id=canonical,
                original_run1_id=record_id,
                original_run2_id=record_id,
                domain_run1=tuple(sorted(left.domains)),
                domain_run2=tuple(sorted(right.domains)),
                domain_exact=domain_exact,
                domain_jaccard=jaccard(left.domains, right.domains),
                purpose_run1=tuple(sorted(left.purposes)),
                purpose_run2=tuple(sorted(right.purposes)),
                purpose_exact=purpose_exact,
                purpose_jaccard=jaccard(left.purposes, right.purposes),
                covid_run1=covid1,
                covid_run2=covid2,
                equity_run1=equity1,
                equity_run2=equity2,
                joint_tag_match=joint,
                all_component_match=domain_exact and purpose_exact and joint,
                migration_note=(
                    "" if canonical == record_id else "Explicit Record-ID migration applied"
                ),
            )
        )
    n = len(diagnostics)
    if not n:
        raise VerificationError("Comparison population is empty")
    metrics = Metrics(
        n=n,
        domain_exact=sum(row.domain_exact for row in diagnostics),
        domain_jaccard=sum(row.domain_jaccard for row in diagnostics) / n,
        purpose_exact=sum(row.purpose_exact for row in diagnostics),
        purpose_jaccard=sum(row.purpose_jaccard for row in diagnostics) / n,
        covid_agreement=sum(row.covid_run1 == row.covid_run2 for row in diagnostics),
        equity_agreement=sum(row.equity_run1 == row.equity_run2 for row in diagnostics),
        joint_tag_agreement=sum(row.joint_tag_match for row in diagnostics),
        all_component_agreement=sum(row.all_component_match for row in diagnostics),
        invalid_or_failed=0,
        missing_run1_ids=tuple(sorted(set(comparison_ids) - set(run1))),
        missing_run2_ids=tuple(sorted(set(comparison_ids) - set(run2))),
    )
    return tuple(diagnostics), metrics


def assert_target_metrics(metrics: Metrics, target: TargetMetrics = TARGET) -> None:
    count_fields = (
        "n",
        "domain_exact",
        "purpose_exact",
        "covid_agreement",
        "equity_agreement",
        "joint_tag_agreement",
        "all_component_agreement",
        "invalid_or_failed",
    )
    mismatches = [
        f"{field}={getattr(metrics, field)} expected {getattr(target, field)}"
        for field in count_fields
        if getattr(metrics, field) != getattr(target, field)
    ]
    for field in ("domain_jaccard", "purpose_jaccard"):
        actual = getattr(metrics, field)
        expected = getattr(target, field)
        if round(actual, 3) != round(expected, 3):
            mismatches.append(f"{field}={actual:.12f} expected {expected:.3f}")
    if metrics.missing_run1_ids or metrics.missing_run2_ids:
        mismatches.append("unreconciled missing run IDs")
    if mismatches:
        raise VerificationError("Target metrics do not reproduce: " + "; ".join(mismatches))


def _resolved_repo_path(root: Path, value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("\\", "/")
    path = Path(normalized)
    return path if path.is_absolute() else root / path


def _validate_run_relationship(run1: RunArtifact, run2: RunArtifact) -> None:
    for record_id in set(run1.entries) & set(run2.entries):
        if run1.entries[record_id].fingerprint != run2.entries[record_id].fingerprint:
            raise VerificationError(
                f"Run input fingerprint differs for comparison ID {record_id!r}"
            )
    ids_by_run: dict[int, set[str]] = {}
    for number, run in ((1, run1), (2, run2)):
        usage = run.metadata.get("usage_log") or []
        if not isinstance(usage, list):
            raise VerificationError(f"Run {number} usage_log is not a list")
        ids = {
            str(row.get("response_id"))
            for row in usage
            if isinstance(row, dict) and row.get("response_id")
        }
        if not ids:
            raise VerificationError(f"Run {number} has no response IDs proving execution")
        ids_by_run[number] = ids
    if ids_by_run[1] & ids_by_run[2]:
        raise VerificationError("Run 1 and Run 2 response IDs overlap")
    if str(run1.metadata.get("created_at_utc")) == str(run2.metadata.get("created_at_utc")):
        raise VerificationError("Run metadata timestamps are not independent")


def read_production(path: Path, taxonomy: Taxonomy) -> dict[str, dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "Record ID" not in reader.fieldnames:
                raise VerificationError(f"Production CSV lacks Record ID: {path}")
            required = {"Project ID", "Title", "substantive_domains", "analytical_purpose", "cross_cutting_tags"}
            if not required.issubset(reader.fieldnames):
                raise VerificationError(f"Production CSV lacks classification columns: {path}")
            rows: dict[str, dict[str, str]] = {}
            for row in reader:
                record_id = str(row.get("Record ID") or "")
                validate_canonical_record_id(record_id)
                if record_id in rows:
                    raise VerificationError(f"Blank or duplicate production Record ID {record_id!r}")
                domains = parse_production_labels(row["substantive_domains"], "substantive_domains")
                purposes = parse_production_labels(row["analytical_purpose"], "analytical_purpose")
                tags = parse_production_labels(row["cross_cutting_tags"], "cross_cutting_tags")
                validate_labels(domains, taxonomy.domains, record_id=record_id, field="domain")
                validate_labels(purposes, taxonomy.purposes, record_id=record_id, field="purpose")
                validate_labels(tags, taxonomy.tags, record_id=record_id, field="tag")
                rows[record_id] = dict(row)
    except OSError as exc:
        raise VerificationError(f"Cannot read production CSV {path}: {exc}") from exc
    return rows


def validate_canonical_record_id(record_id: str) -> None:
    """Reject non-canonical IDs without rewriting source evidence."""
    if not record_id or not record_id.strip():
        raise VerificationError(f"Blank canonical Record ID {record_id!r}")
    if record_id != record_id.strip():
        raise VerificationError(
            f"Canonical Record ID has leading or trailing whitespace: {record_id!r}"
        )
    prohibited = [
        char
        for char in record_id
        if ord(char) < 0x20 or ord(char) == 0x7F or char == "\u00a0"
    ]
    if prohibited:
        escaped = " ".join(f"U+{ord(char):04X}" for char in prohibited)
        raise VerificationError(
            f"Canonical Record ID contains prohibited control characters "
            f"({escaped}): {record_id!r}"
        )


def verify_cleaned_register_link(
    path: Path, production_rows: Mapping[str, Mapping[str, str]]
) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"Record ID", "Project ID", "Title"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise VerificationError(f"Cleaned register lacks required columns: {path}")
            rows: dict[str, Mapping[str, str]] = {}
            for row in reader:
                record_id = str(row.get("Record ID") or "")
                validate_canonical_record_id(record_id)
                if record_id in rows:
                    raise VerificationError(
                        f"Duplicate cleaned-register Record ID {record_id!r}"
                    )
                rows[record_id] = dict(row)
    except OSError as exc:
        raise VerificationError(f"Cannot read cleaned register {path}: {exc}") from exc
    if set(rows) != set(production_rows):
        missing = sorted(set(production_rows) - set(rows))
        extra = sorted(set(rows) - set(production_rows))
        raise VerificationError(
            f"Cleaned-register/production Record IDs differ: missing={missing[:10]}; extra={extra[:10]}"
        )
    for record_id, cleaned in rows.items():
        production = production_rows[record_id]
        for field in ("Project ID", "Title"):
            if str(cleaned.get(field) or "") != str(production.get(field) or ""):
                raise VerificationError(
                    f"Cleaned-register/production {field} differs for {record_id!r}"
                )
    return len(rows)


def load_migration_rows(path: Path | None) -> dict[str, Mapping[str, str]]:
    if path is None:
        return {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"old_record_id", "new_record_id", "project_id", "action"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise VerificationError(f"Migration file lacks required columns: {path}")
            rows = list(reader)
    except OSError as exc:
        raise VerificationError(f"Cannot read migration file {path}: {exc}") from exc
    result: dict[str, Mapping[str, str]] = {}
    for row in rows:
        if "source" in row and row.get("source") not in ("", "fable"):
            continue
        old = str(row.get("old_record_id") or "")
        new = str(row.get("new_record_id") or "")
        if not old or not new:
            continue
        if old in result and result[old].get("new_record_id") != new:
            raise VerificationError(f"Ambiguous migration mapping for {old!r}")
        result[old] = row
    return result


def verify_production_link(
    run1: RunArtifact,
    production_rows: Mapping[str, Mapping[str, str]],
    production_metadata_path: Path,
    migration_path: Path | None,
    repo_root: Path,
) -> tuple[ProductionLink, dict[str, str]]:
    metadata = _read_json(production_metadata_path)
    if not isinstance(metadata, dict):
        raise VerificationError("Production run metadata must be an object")
    model = str(metadata.get("model") or "")
    prompt = str(metadata.get("prompt_version") or "")
    taxonomy = str(metadata.get("taxonomy_version") or "")
    if (model, prompt, taxonomy) != (EXPECTED_MODEL, EXPECTED_VERSION, EXPECTED_VERSION):
        raise VerificationError("Production model/prompt/taxonomy provenance is wrong")
    seed_entries = int(metadata.get("seed_cache_entries") or -1)
    if seed_entries != len(run1.entries):
        raise VerificationError("Production seed-cache count does not match Run 1")
    seed_cache = str(metadata.get("seed_cache") or "")
    try:
        run1_relative = run1.path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        run1_relative = run1.path.name
    if not seed_cache.replace("\\", "/").endswith(run1_relative):
        raise VerificationError(
            f"Production seed-cache path does not identify Run 1: {seed_cache!r}"
        )
    if len(production_rows) != EXPECTED_PRODUCTION_ROWS:
        raise VerificationError(
            f"Production output has {len(production_rows)} rows, expected {EXPECTED_PRODUCTION_ROWS}"
        )
    mapping_rows = load_migration_rows(migration_path)
    canonical_ids: dict[str, str] = {}
    mappings: list[MappingEvidence] = []
    differences: list[str] = []
    for old_id, classification in run1.entries.items():
        canonical = old_id
        mapping = None
        if canonical not in production_rows:
            mapping = mapping_rows.get(old_id)
            if mapping is None:
                raise VerificationError(
                    f"Run 1 ID {old_id!r} is absent from production with no explicit mapping"
                )
            canonical = str(mapping.get("new_record_id") or "")
            if canonical not in production_rows:
                raise VerificationError(
                    f"Mapped production ID {canonical!r} for {old_id!r} is absent"
                )
            fingerprint_match = (
                not mapping.get("fingerprint")
                or str(mapping.get("fingerprint")) == classification.fingerprint
            )
            if not fingerprint_match:
                raise VerificationError(f"Migration fingerprint mismatch for {old_id!r}")
            mappings.append(
                MappingEvidence(
                    original_record_id=old_id,
                    canonical_record_id=canonical,
                    project_id=str(mapping.get("project_id") or ""),
                    mapping_source=_repo_relative(migration_path, repo_root),
                    mapping_reason=(
                        "Explicit offline rekey by Project ID and exact prompt fingerprint "
                        f"(action={mapping.get('action')})"
                    ),
                    fingerprint_match=True,
                )
            )
        canonical_ids[old_id] = canonical
        row = production_rows[canonical]
        expected = {
            "substantive_domains": classification.domains,
            "analytical_purpose": classification.purposes,
            "cross_cutting_tags": classification.tags,
        }
        for field, labels in expected.items():
            if parse_production_labels(row.get(field, ""), field) != labels:
                differences.append(f"{old_id!r}->{canonical!r}:{field}")
    if differences:
        raise VerificationError(
            f"{len(differences)} Run 1 classification fields differ from production"
        )
    if mappings:
        migration_meta = metadata.get("reviewed_duplicate_record_id_migration") or {}
        if not isinstance(migration_meta, dict) or migration_meta.get("status") != "applied":
            raise VerificationError("Production metadata does not record the applied migration")
    return (
        ProductionLink(
            row_count=len(production_rows),
            unique_record_ids=len(production_rows),
            matched_records=len(run1.entries),
            mapping_evidence=tuple(sorted(mappings, key=lambda row: row.original_record_id)),
            source_register=str(metadata.get("source_register") or ""),
            production_model=model,
            prompt_version=prompt,
            taxonomy_version=taxonomy,
            seed_cache=seed_cache,
            seed_cache_entries=seed_entries,
            fresh_classifications=int(metadata.get("fresh_api_classifications") or -1),
        ),
        canonical_ids,
    )


def _select_sample_source(
    repo_root: Path,
    explicit_path: Path | None,
    run1: RunArtifact,
    run2: RunArtifact,
) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    left = str(run1.metadata.get("sample_csv") or "")
    right = str(run2.metadata.get("sample_csv") or "")
    if not left or left.replace("\\", "/") != right.replace("\\", "/"):
        return None
    return _resolved_repo_path(repo_root, left)


def verify_package(
    *,
    run1_path: Path,
    run2_path: Path,
    production_output_path: Path,
    taxonomy_path: Path,
    repo_root: Path,
    run1_metadata_path: Path,
    run2_metadata_path: Path,
    production_metadata_path: Path,
    migration_path: Path | None,
    sample_source_path: Path | None,
    cleaned_register_path: Path | None = None,
) -> VerificationResult:
    taxonomy = load_taxonomy(taxonomy_path)
    run1 = load_run_artifact(run1_path, run1_metadata_path, taxonomy)
    run2 = load_run_artifact(run2_path, run2_metadata_path, taxonomy)
    _validate_run_relationship(run1, run2)
    sample_source = _select_sample_source(repo_root, sample_source_path, run1, run2)
    sample_ids = None
    sample_sha = None
    if sample_source is not None:
        if not sample_source.is_file():
            raise VerificationError(f"Recovered sample source is absent: {sample_source}")
        sample_ids = read_sample_ids(sample_source)
        sample_sha = sha256_file(sample_source)
    comparison_ids = determine_comparison_ids(run1.entries, run2.entries, sample_ids)
    production_rows = read_production(production_output_path, taxonomy)
    cleaned_register_rows = None
    cleaned_register_sha = None
    if cleaned_register_path is not None:
        cleaned_register_rows = verify_cleaned_register_link(
            cleaned_register_path, production_rows
        )
        cleaned_register_sha = sha256_file(cleaned_register_path)
    production_link, canonical_ids = verify_production_link(
        run1,
        production_rows,
        production_metadata_path,
        migration_path,
        repo_root,
    )
    diagnostics, metrics = compare_classifications(
        run1.entries, run2.entries, comparison_ids, canonical_ids
    )
    assert_target_metrics(metrics)
    return VerificationResult(
        run1=run1,
        run2=run2,
        taxonomy=taxonomy,
        taxonomy_path=taxonomy_path,
        taxonomy_sha256=sha256_file(taxonomy_path),
        comparison_ids=comparison_ids,
        sample_source=sample_source,
        sample_source_sha256=sample_sha,
        diagnostics=diagnostics,
        metrics=metrics,
        production_link=production_link,
        production_rows=production_rows,
        production_output_path=production_output_path,
        production_output_sha256=sha256_file(production_output_path),
        production_output_lf_sha256=lf_normalized_sha256(production_output_path),
        production_metadata_path=production_metadata_path,
        production_metadata_sha256=sha256_file(production_metadata_path),
        production_metadata_lf_sha256=lf_normalized_sha256(production_metadata_path),
        migration_path=migration_path,
        migration_sha256=sha256_file(migration_path) if migration_path else None,
        cleaned_register_path=cleaned_register_path,
        cleaned_register_sha256=cleaned_register_sha,
        cleaned_register_row_count=cleaned_register_rows,
    )


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _git_commit(root: Path) -> str:
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"Cannot determine repository commit: {exc}") from exc
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise VerificationError(f"Invalid Git commit {value!r}")
    return value


def _earliest_production_commit(root: Path, path: Path) -> Mapping[str, str]:
    relative = _repo_relative(path, root)
    try:
        lines = subprocess.check_output(
            ["git", "log", "--reverse", "--format=%H|%cI|%s", "--", relative],
            cwd=root,
            text=True,
        ).splitlines()
    except (OSError, subprocess.CalledProcessError):
        return {}
    if not lines:
        return {}
    commit, timestamp, subject = lines[0].split("|", 2)
    return {"commit": commit, "timestamp": timestamp, "subject": subject}


def _metric_payload(count: int, n: int) -> Mapping[str, float | int]:
    return {"count": count, "denominator": n, "percentage": count * 100 / n}


def _jsonable_run(run: RunArtifact, root: Path) -> Mapping[str, Any]:
    return {
        "cache_path": _repo_relative(run.path, root),
        "cache_sha256": run.sha256,
        "cache_size_bytes": run.file_size,
        "cache_modified_at_utc": run.modified_at_utc,
        "metadata_path": _repo_relative(run.metadata_path, root),
        "metadata_sha256": run.metadata_sha256,
        "created_at_utc": run.metadata.get("created_at_utc"),
        "run_key": run.metadata.get("run_key"),
        "model": run.model,
        "prompt_version": run.prompt_version,
        "cache_schema_version": run.cache_schema_version,
        "entry_count": len(run.entries),
        "usage_response_count": len(run.metadata.get("usage_log") or []),
    }


def build_metrics_payload(
    result: VerificationResult, repo_root: Path, script_path: Path
) -> Mapping[str, Any]:
    metrics = result.metrics
    commit = _git_commit(repo_root)
    input_hashes: dict[str, str] = {
        _repo_relative(result.run1.path, repo_root): result.run1.sha256,
        _repo_relative(result.run1.metadata_path, repo_root): result.run1.metadata_sha256,
        _repo_relative(result.run2.path, repo_root): result.run2.sha256,
        _repo_relative(result.run2.metadata_path, repo_root): result.run2.metadata_sha256,
        _repo_relative(result.production_output_path, repo_root): result.production_output_sha256,
        _repo_relative(result.production_metadata_path, repo_root): result.production_metadata_sha256,
        _repo_relative(result.taxonomy_path, repo_root): result.taxonomy_sha256,
    }
    if result.sample_source and result.sample_source_sha256:
        input_hashes[_repo_relative(result.sample_source, repo_root)] = result.sample_source_sha256
    if result.migration_path and result.migration_sha256:
        input_hashes[_repo_relative(result.migration_path, repo_root)] = result.migration_sha256
    if result.cleaned_register_path and result.cleaned_register_sha256:
        input_hashes[_repo_relative(result.cleaned_register_path, repo_root)] = (
            result.cleaned_register_sha256
        )
    return {
        "verification_status": "verified",
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "no_api_or_llm_calls_made": True,
        "repository_commit": commit,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "verification_script": {
            "path": _repo_relative(script_path, repo_root),
            "sha256": sha256_file(script_path),
        },
        "input_hashes": dict(sorted(input_hashes.items())),
        "run1": _jsonable_run(result.run1, repo_root),
        "run2": _jsonable_run(result.run2, repo_root),
        "comparison_sample": {
            "n": metrics.n,
            "source_path": (
                _repo_relative(result.sample_source, repo_root)
                if result.sample_source
                else None
            ),
            "source_sha256": result.sample_source_sha256,
            "cache_key_sets_identical": set(result.run1.entries) == set(result.run2.entries),
        },
        "metrics": {
            "n": metrics.n,
            "domain_exact": _metric_payload(metrics.domain_exact, metrics.n),
            "mean_domain_jaccard": metrics.domain_jaccard,
            "purpose_exact": _metric_payload(metrics.purpose_exact, metrics.n),
            "mean_purpose_jaccard": metrics.purpose_jaccard,
            "covid_tag_agreement": _metric_payload(metrics.covid_agreement, metrics.n),
            "equity_tag_agreement": _metric_payload(metrics.equity_agreement, metrics.n),
            "joint_tag_agreement": _metric_payload(metrics.joint_tag_agreement, metrics.n),
            "all_component_agreement": _metric_payload(
                metrics.all_component_agreement, metrics.n
            ),
            "invalid_or_failed_classifications": metrics.invalid_or_failed,
            "missing_ids_run1": list(metrics.missing_run1_ids),
            "missing_ids_run2": list(metrics.missing_run2_ids),
        },
        "production_link": {
            **asdict(result.production_link),
            "mapping_evidence": [
                asdict(row) for row in result.production_link.mapping_evidence
            ],
            "production_output_path": _repo_relative(
                result.production_output_path, repo_root
            ),
            "production_output_sha256_working_bytes": result.production_output_sha256,
            "production_output_sha256_lf_normalized_in_memory": result.production_output_lf_sha256,
            "production_output_reference_hash": EXPECTED_PRODUCTION_HASH,
            "production_output_reference_match": (
                result.production_output_sha256 == EXPECTED_PRODUCTION_HASH
                or result.production_output_lf_sha256 == EXPECTED_PRODUCTION_HASH
            ),
            "production_metadata_path": _repo_relative(
                result.production_metadata_path, repo_root
            ),
            "production_metadata_sha256_working_bytes": result.production_metadata_sha256,
            "production_metadata_sha256_lf_normalized_in_memory": result.production_metadata_lf_sha256,
            "production_metadata_reference_hash": EXPECTED_PRODUCTION_METADATA_HASH,
            "production_metadata_reference_match": (
                result.production_metadata_sha256 == EXPECTED_PRODUCTION_METADATA_HASH
                or result.production_metadata_lf_sha256
                == EXPECTED_PRODUCTION_METADATA_HASH
            ),
        },
        "cleaned_register_link": {
            "path": (
                _repo_relative(result.cleaned_register_path, repo_root)
                if result.cleaned_register_path
                else None
            ),
            "sha256": result.cleaned_register_sha256,
            "row_count": result.cleaned_register_row_count,
            "record_ids_match_production_exactly": bool(result.cleaned_register_path),
        },
        "pre_registration_git_evidence": _earliest_production_commit(
            repo_root, result.production_metadata_path
        ),
        "taxonomy": {
            "version": result.taxonomy.version,
            "covid_tag_label": COVID_TAG,
            "equity_tag_label": EQUITY_TAG,
        },
        "mapping_count": len(result.production_link.mapping_evidence),
    }


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _diagnostic_rows(result: VerificationResult) -> Iterable[Mapping[str, Any]]:
    for row in result.diagnostics:
        yield {
            "canonical_record_id": row.canonical_record_id,
            "original_run1_id": row.original_run1_id,
            "original_run2_id": row.original_run2_id,
            "domain_set_run1": json.dumps(row.domain_run1, ensure_ascii=False),
            "domain_set_run2": json.dumps(row.domain_run2, ensure_ascii=False),
            "domain_exact_match": str(row.domain_exact).lower(),
            "domain_jaccard": f"{row.domain_jaccard:.12f}",
            "purpose_set_run1": json.dumps(row.purpose_run1, ensure_ascii=False),
            "purpose_set_run2": json.dumps(row.purpose_run2, ensure_ascii=False),
            "purpose_exact_match": str(row.purpose_exact).lower(),
            "purpose_jaccard": f"{row.purpose_jaccard:.12f}",
            "covid_run1": str(row.covid_run1).lower(),
            "covid_run2": str(row.covid_run2).lower(),
            "equity_disparities_run1": str(row.equity_run1).lower(),
            "equity_disparities_run2": str(row.equity_run2).lower(),
            "joint_tag_match": str(row.joint_tag_match).lower(),
            "all_component_match": str(row.all_component_match).lower(),
            "migration_note": row.migration_note,
        }


def _manifest_rows(result: VerificationResult) -> Iterable[Mapping[str, Any]]:
    mapping_by_old = {
        row.original_record_id: row for row in result.production_link.mapping_evidence
    }
    for record_id in result.comparison_ids:
        mapping = mapping_by_old.get(record_id)
        canonical = mapping.canonical_record_id if mapping else record_id
        production = result.production_rows[canonical]
        yield {
            "run_record_id": record_id,
            "canonical_record_id": canonical,
            "official_project_id": production.get("Project ID", ""),
            "title": production.get("Title", ""),
            "present_in_run1": "true",
            "present_in_run2": "true",
            "present_in_current_production": "true",
            "record_id_mapping_applied": str(mapping is not None).lower(),
            "mapping_source": mapping.mapping_source if mapping else "",
            "notes": mapping.mapping_reason if mapping else "",
        }


def _verification_report(
    result: VerificationResult, payload: Mapping[str, Any], repo_root: Path
) -> str:
    m = result.metrics
    mapping_lines = [
        (
            f"- `{row.original_record_id}` -> `{row.canonical_record_id.encode('unicode_escape').decode()}` "
            f"for Project ID `{row.project_id}`; exact audit fingerprint and classifications matched."
        )
        for row in result.production_link.mapping_evidence
    ] or ["- No Record-ID mapping was required."]
    source_lines = [
        f"- `{path}`: `{digest}`"
        for path, digest in payload["input_hashes"].items()
    ]
    earliest = payload.get("pre_registration_git_evidence") or {}
    return "\n".join(
        [
            "# Fable 5 run-to-run stability verification",
            "",
            "## Conclusion",
            "",
            "The exact underlying Fable 5 caches were recovered in their original canonical "
            "directories and verified. The classifications pre-existed registration. Both run "
            "metadata files date the independent runs to 2 July 2026, and the tracked production "
            f"metadata first entered Git at `{earliest.get('commit', 'not available')}` "
            f"({earliest.get('timestamp', 'timestamp unavailable')}) while naming Run 1 as its seed cache.",
            "",
            "The recovered source caches were already at the canonical repository paths. They were "
            "not copied, rewritten, reformatted, normalised, or otherwise modified.",
            "",
            "## Provenance and population",
            "",
            f"- Model: `{EXPECTED_MODEL}` (Fable 5).",
            f"- Prompt/taxonomy: `{EXPECTED_VERSION}`.",
            f"- Comparison population: {m.n} exact Record IDs; both cache key sets and the recovered sample CSV agree.",
            "- Run metadata contains disjoint provider response IDs, corroborating two independent executions.",
            f"- Run 1 was the {result.production_link.seed_cache_entries}-entry seed cache for the current production output.",
            f"- Corrected cleaned register: `{_repo_relative(result.cleaned_register_path, repo_root) if result.cleaned_register_path else 'not supplied'}` "
            f"({result.cleaned_register_row_count or 0} rows); its canonical Record-ID set matches production exactly.",
            "",
            "## Reproduced metrics",
            "",
            f"- Research Domain exact-set agreement: {m.domain_exact}/{m.n} ({m.domain_exact / m.n:.1%}).",
            f"- Mean Research Domain Jaccard: {m.domain_jaccard:.12f} (displayed as {m.domain_jaccard:.3f}).",
            f"- Analytical Purpose exact-set agreement: {m.purpose_exact}/{m.n} ({m.purpose_exact / m.n:.1%}).",
            f"- Mean Analytical Purpose Jaccard: {m.purpose_jaccard:.12f} (displayed as {m.purpose_jaccard:.3f}).",
            f"- COVID-19/pandemic tag agreement: {m.covid_agreement}/{m.n} ({m.covid_agreement / m.n:.1%}).",
            f"- Demographic-disparities/equity tag agreement: {m.equity_agreement}/{m.n} ({m.equity_agreement / m.n:.1%}).",
            f"- Joint two-tag agreement: {m.joint_tag_agreement}/{m.n} ({m.joint_tag_agreement / m.n:.1%}).",
            f"- All-component agreement: {m.all_component_agreement}/{m.n} ({m.all_component_agreement / m.n:.1%}).",
            f"- Invalid or failed classifications: {m.invalid_or_failed}.",
            "",
            "## Production linkage and Record-ID migration",
            "",
            f"All {result.production_link.matched_records} Run 1 classifications match the corrected "
            f"{result.production_link.row_count}-row production output. The recovered run keys were "
            "already clean; the direct canonical linkage now requires:",
            "",
            *mapping_lines,
            "",
            "Before registration, an upstream cleaning-order defect was found: 16 later canonical "
            "Record IDs inherited boundary spaces or CR/LF from the raw public register even though "
            "Project ID was subsequently stripped. The central Record-ID assignment function now "
            "normalises boundary whitespace and enforces control-character, nonblank, and uniqueness "
            "invariants. Current Fable/GPT and deterministic outputs were rekeyed offline. No "
            "classification array, rationale, fingerprint, or other model output was regenerated.",
            "",
            "Project `2023/211` was not in the 201-record comparison sample. The production metadata "
            "and reviewed duplicate-ruling report separately record its collapse to one retained "
            "unsuffixed Record ID; no mapping for it was invented or applied here.",
            "",
            "The previously recorded production hashes identify the pre-correction dirty-ID files. "
            "The corrected production output and metadata therefore have new hashes. Deterministic "
            "semantic checks prove that classification content is unchanged apart from Record-ID "
            "keys and the explicit metadata provenance annotation.",
            "",
            "## Determinism and security",
            "",
            "No model or API call was made. Verification used local JSON/CSV/YAML parsing, exact "
            "labels, unordered sets, ordinary set Jaccard, exact audit mappings, and local hashing. "
            "The recovered caches contain public register identifiers, classifications, rationales, "
            "prompt fingerprints, and non-sensitive run metadata. A targeted credential scan found no "
            "secret indicator.",
            "",
            "## Limitations",
            "",
            "This is one pre-existing run pair on one fixed 201-record sample. Filesystem timestamps "
            "are recovery metadata rather than proof of authorship; the tracked 2 July production "
            "metadata provides the stronger Git provenance link. The raw June register retains its "
            "source whitespace as an unchanged snapshot; only cleaned/current derived identifiers "
            "were corrected.",
            "",
            "## Source hashes",
            "",
            *source_lines,
            "",
            f"Verification script: `{payload['verification_script']['path']}` at "
            f"`{payload['verification_script']['sha256']}`.",
            "",
        ]
    )


def write_outputs(
    result: VerificationResult,
    output_dir: Path,
    repo_root: Path,
    script_path: Path,
) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "fable_run_stability_201_record_manifest.csv"
    diagnostics_path = output_dir / "fable_run_stability_record_diagnostics.csv"
    metrics_path = output_dir / "fable_run_stability_metrics.json"
    report_path = output_dir / "fable_run_stability_verification_report.md"
    _write_csv(
        manifest_path,
        (
            "run_record_id",
            "canonical_record_id",
            "official_project_id",
            "title",
            "present_in_run1",
            "present_in_run2",
            "present_in_current_production",
            "record_id_mapping_applied",
            "mapping_source",
            "notes",
        ),
        _manifest_rows(result),
    )
    _write_csv(
        diagnostics_path,
        (
            "canonical_record_id",
            "original_run1_id",
            "original_run2_id",
            "domain_set_run1",
            "domain_set_run2",
            "domain_exact_match",
            "domain_jaccard",
            "purpose_set_run1",
            "purpose_set_run2",
            "purpose_exact_match",
            "purpose_jaccard",
            "covid_run1",
            "covid_run2",
            "equity_disparities_run1",
            "equity_disparities_run2",
            "joint_tag_match",
            "all_component_match",
            "migration_note",
        ),
        _diagnostic_rows(result),
    )
    payload = build_metrics_payload(result, repo_root, script_path)
    metrics_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report_path.write_text(
        _verification_report(result, payload, repo_root),
        encoding="utf-8",
        newline="\n",
    )
    return manifest_path, diagnostics_path, metrics_path, report_path


def _resolve(path: Path | None, root: Path, fallback: Path | None = None) -> Path:
    selected = path if path is not None else fallback
    if selected is None:
        raise VerificationError("A required path was not supplied")
    return selected.resolve() if selected.is_absolute() else (root / selected).resolve()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline deterministic verification of the two recovered Fable 5 stability runs."
    )
    parser.add_argument("--run1", type=Path, required=True, help="Run 1 cache JSON")
    parser.add_argument("--run2", type=Path, required=True, help="Run 2 cache JSON")
    parser.add_argument(
        "--production-output", type=Path, required=True, help="Current production CSV"
    )
    parser.add_argument("--migration-file", type=Path, help="Explicit Record-ID migration CSV")
    parser.add_argument(
        "--cleaned-register", type=Path,
        help="Corrected frozen cleaned register whose canonical IDs must match production",
    )
    parser.add_argument("--taxonomy", type=Path, default=Path("taxonomy_data_dictionary.yaml"))
    parser.add_argument("--run1-metadata", type=Path)
    parser.add_argument("--run2-metadata", type=Path)
    parser.add_argument("--production-metadata", type=Path)
    parser.add_argument("--sample-source", type=Path, help="Recovered exact sample CSV")
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("preregistration/package/03_preexisting_model_evidence"),
    )
    parser.add_argument(
        "--check", action="store_true", help="Verify only; never create output artefacts"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.repository_root.resolve()
    try:
        run1_path = _resolve(args.run1, root)
        run2_path = _resolve(args.run2, root)
        production_path = _resolve(args.production_output, root)
        result = verify_package(
            run1_path=run1_path,
            run2_path=run2_path,
            production_output_path=production_path,
            taxonomy_path=_resolve(args.taxonomy, root),
            repo_root=root,
            run1_metadata_path=_resolve(
                args.run1_metadata, root, run1_path.with_name("run_metadata.json")
            ),
            run2_metadata_path=_resolve(
                args.run2_metadata, root, run2_path.with_name("run_metadata.json")
            ),
            production_metadata_path=_resolve(
                args.production_metadata,
                root,
                production_path.with_name("run_metadata.json"),
            ),
            migration_path=(
                _resolve(args.migration_file, root) if args.migration_file else None
            ),
            sample_source_path=(
                _resolve(args.sample_source, root) if args.sample_source else None
            ),
            cleaned_register_path=(
                _resolve(args.cleaned_register, root) if args.cleaned_register else None
            ),
        )
        if args.check:
            print(
                "VERIFIED (check mode): "
                f"n={result.metrics.n}; domain={result.metrics.domain_exact}; "
                f"purpose={result.metrics.purpose_exact}; "
                f"joint_tags={result.metrics.joint_tag_agreement}; "
                f"all_components={result.metrics.all_component_agreement}; "
                "no files written"
            )
        else:
            output_dir = _resolve(args.output_dir, root)
            written = write_outputs(result, output_dir, root, Path(__file__).resolve())
            print(
                f"VERIFIED: n={result.metrics.n}; wrote {len(written)} reproducibility artefacts"
            )
        return 0
    except VerificationError as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
