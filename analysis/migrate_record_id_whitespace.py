#!/usr/bin/env python3
"""Correct canonical Record-ID whitespace and migrate current outputs offline.

The script invokes the repository's existing register-cleaning pipeline, derives
the one-to-one old/new mapping by Project ID and the established prompt-input
fingerprint, and updates only declared Record-ID fields or JSON mapping keys.
It contains no network client and never calls a classifier.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


PROHIBITED_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\u00a0]")
ID_LIKE_RE = re.compile(r"^\d{4}/\d{3}(?:/[A-Za-z]+)?$")
JSON_ID_FIELDS = frozenset({"Record ID", "record_id", "project_id", "record_ids"})
PROTECTED_RELATIVE_PATHS = frozenset({
    "data/dea_accredited_projects_20260601.csv",
    "analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json",
    "analysis/outputs/model_comparison_fable_5_run1/run_metadata.json",
    "analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json",
    "analysis/outputs/model_comparison_fable_5_run2/run_metadata.json",
})


class MigrationError(RuntimeError):
    """Raised when a deterministic migration gate fails."""


@dataclass(frozen=True)
class RecordIdMapping:
    old_record_id: str
    new_record_id: str
    official_project_id: str
    title: str
    fingerprint: str
    reference_csv_row: int
    removed_characters: str
    duplicate_would_result: bool = False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_jsonable(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _prompt_text(value: object) -> str:
    text = " ".join(str(value or "").split())
    text = text.replace("```", "'''")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("[", "(").replace("]", ")")
    return text.strip()


def _prompt_datasets(value: object, max_chars: int = 600) -> str:
    raw = "" if value is None else str(value)
    if not raw.strip():
        return "(no datasets listed)"
    text = " ".join(raw.split())
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return _prompt_text(text)


def classification_fingerprint(title: object, datasets: object) -> str:
    payload = f"{_prompt_text(title)}\n{_prompt_datasets(datasets)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def validate_clean_record_id(record_id: str) -> None:
    if not isinstance(record_id, str) or not record_id:
        raise MigrationError(f"Missing or non-string Record ID: {record_id!r}")
    if record_id != record_id.strip():
        raise MigrationError(f"Record ID has boundary whitespace: {record_id!r}")
    match = PROHIBITED_CONTROL_RE.search(record_id)
    if match:
        raise MigrationError(
            f"Record ID contains prohibited U+{ord(match.group(0)):04X}: {record_id!r}"
        )


def _is_dirty_id(value: str) -> bool:
    stripped = value.strip()
    return bool(ID_LIKE_RE.fullmatch(stripped)) and (
        value != stripped or PROHIBITED_CONTROL_RE.search(value) is not None
    )


def _removed_characters(old: str, new: str) -> str:
    if old.strip() != new:
        raise MigrationError(f"Mapping is not whitespace-only: {old!r} -> {new!r}")
    left_count = len(old) - len(old.lstrip())
    right_count = len(old) - len(old.rstrip())
    removed = old[:left_count]
    if right_count:
        removed += old[len(old) - right_count :]
    names = {
        " ": "SPACE",
        "\t": "TAB",
        "\r": "CARRIAGE RETURN",
        "\n": "LINE FEED",
        "\u00a0": "NO-BREAK SPACE",
    }
    return "; ".join(
        f"{char.encode('unicode_escape').decode('ascii')} (U+{ord(char):04X} {names.get(char, 'CONTROL')})"
        for char in removed
    )


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise MigrationError(f"CSV has no header: {path}")
        return list(reader.fieldnames), [dict(row) for row in reader]


def _frame_rows(frame: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in frame.to_dict("records"):
        row: dict[str, str] = {}
        for key, value in source.items():
            row[str(key)] = "" if pd.isna(value) else str(value)
        rows.append(row)
    return rows


def derive_mapping(
    corrected_rows: Sequence[Mapping[str, str]],
    reference_rows: Sequence[Mapping[str, str]],
    *,
    evidence_rows: Sequence[Mapping[str, str]] | None = None,
) -> list[RecordIdMapping]:
    required = {"Project ID", "Record ID", "Title", "Datasets Used"}
    for label, rows in (("corrected", corrected_rows), ("reference", reference_rows)):
        if not rows or not required.issubset(rows[0]):
            raise MigrationError(f"{label} rows lack required mapping fields")

    reference_index: dict[tuple[str, str], list[tuple[int, Mapping[str, str]]]] = {}
    reference_ids = [str(row["Record ID"]) for row in reference_rows]
    if len(reference_ids) != len(set(reference_ids)):
        raise MigrationError("Reference CSV has duplicate raw Record IDs")
    for index, row in enumerate(reference_rows, start=2):
        key = (
            str(row["Project ID"]),
            classification_fingerprint(row["Title"], row["Datasets Used"]),
        )
        reference_index.setdefault(key, []).append((index, row))

    evidence_index: dict[str, list[Mapping[str, str]]] = {}
    for row in evidence_rows or ():
        if str(row.get("source") or "") not in ("", "fable"):
            continue
        evidence_index.setdefault(str(row.get("new_record_id") or ""), []).append(row)

    mappings: list[RecordIdMapping] = []
    for corrected in corrected_rows:
        new_id = str(corrected["Record ID"])
        validate_clean_record_id(new_id)
        fingerprint = classification_fingerprint(
            corrected["Title"], corrected["Datasets Used"]
        )
        key = (str(corrected["Project ID"]), fingerprint)
        candidates = reference_index.get(key, [])
        if len(candidates) != 1:
            raise MigrationError(
                f"Expected one reference row for Project ID/fingerprint {key}, found {len(candidates)}"
            )
        row_number, reference = candidates[0]
        old_id = str(reference["Record ID"])
        if old_id == new_id:
            continue
        if old_id.strip() != new_id:
            raise MigrationError(f"Non-whitespace Record-ID change found: {old_id!r} -> {new_id!r}")
        collision = new_id in reference_ids and new_id != old_id
        if collision:
            raise MigrationError(
                f"Whitespace normalisation target already exists: {old_id!r} -> {new_id!r}"
            )
        if evidence_rows is not None:
            evidence = evidence_index.get(old_id, [])
            if len(evidence) != 1:
                raise MigrationError(
                    f"Expected one Fable mapping-audit row for dirty ID {old_id!r}, found {len(evidence)}"
                )
            audit = evidence[0]
            if str(audit.get("project_id") or "") != str(corrected["Project ID"]):
                raise MigrationError(f"Mapping-audit Project ID mismatch for {old_id!r}")
            if str(audit.get("fingerprint") or "") != fingerprint:
                raise MigrationError(f"Mapping-audit fingerprint mismatch for {old_id!r}")
        mappings.append(
            RecordIdMapping(
                old_record_id=old_id,
                new_record_id=new_id,
                official_project_id=str(corrected["Project ID"]),
                title=str(corrected["Title"]),
                fingerprint=fingerprint,
                reference_csv_row=row_number,
                removed_characters=_removed_characters(old_id, new_id),
                duplicate_would_result=False,
            )
        )

    old_ids = [item.old_record_id for item in mappings]
    new_ids = [item.new_record_id for item in mappings]
    if len(old_ids) != len(set(old_ids)) or len(new_ids) != len(set(new_ids)):
        raise MigrationError("Whitespace mapping is not one-to-one")
    return sorted(mappings, key=lambda item: item.new_record_id)


def _mapping_dict(mappings: Iterable[RecordIdMapping]) -> dict[str, str]:
    result = {item.old_record_id: item.new_record_id for item in mappings}
    if len(result) != len(list(mappings)):
        raise MigrationError("Duplicate old IDs in mapping")
    return result


def migrate_exact_id(value: str, mapping: Mapping[str, str]) -> tuple[str, bool]:
    if value in mapping:
        return mapping[value], True
    if _is_dirty_id(value):
        raise MigrationError(f"Unmapped dirty Record ID {value!r}")
    return value, False


def migrate_token_list(value: str, mapping: Mapping[str, str]) -> tuple[str, int]:
    segments = value.split(";")
    changed = 0
    migrated: list[str] = []
    for segment in segments:
        leading_length = len(segment) - len(segment.lstrip())
        leading = segment[:leading_length]
        core = segment[leading_length:]
        new_core, did_change = migrate_exact_id(core, mapping)
        migrated.append(leading + new_core)
        changed += int(did_change)
    return ";".join(migrated), changed


def migrate_csv_rows(
    rows: Sequence[Mapping[str, str]],
    mapping: Mapping[str, str],
    *,
    exact_fields: Sequence[str] = (),
    token_fields: Sequence[str] = (),
) -> tuple[list[dict[str, str]], int]:
    if rows:
        missing = (set(exact_fields) | set(token_fields)) - set(rows[0])
        if missing:
            raise MigrationError(f"CSV lacks declared ID fields: {sorted(missing)}")
    output: list[dict[str, str]] = []
    changes = 0
    for source in rows:
        row = dict(source)
        for field in exact_fields:
            row[field], changed = migrate_exact_id(str(row[field]), mapping)
            changes += int(changed)
        for field in token_fields:
            row[field], changed_count = migrate_token_list(str(row[field]), mapping)
            changes += changed_count
        output.append(row)
    return output, changes


def _migrate_json_id_values(value: Any, mapping: Mapping[str, str], field: str = "") -> Any:
    if isinstance(value, dict):
        return {
            key: _migrate_json_id_values(item, mapping, str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        if field in JSON_ID_FIELDS:
            return [migrate_exact_id(item, mapping)[0] if isinstance(item, str) else item for item in value]
        return [_migrate_json_id_values(item, mapping, field) for item in value]
    if isinstance(value, str) and field in JSON_ID_FIELDS:
        return migrate_exact_id(value, mapping)[0]
    return value


def migrate_json_cache(payload: Mapping[str, Any], mapping: Mapping[str, str]) -> tuple[dict[str, Any], int]:
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        raise MigrationError("JSON cache lacks an entries mapping")
    old_keys = set(entries)
    changes = 0
    new_entries: dict[str, Any] = {}
    for old_key, entry in entries.items():
        new_key, changed = migrate_exact_id(str(old_key), mapping)
        if changed and new_key in old_keys:
            raise MigrationError(f"JSON target key already exists: {new_key!r}")
        if new_key in new_entries:
            raise MigrationError(f"JSON migration creates duplicate key: {new_key!r}")
        migrated_entry = _migrate_json_id_values(entry, mapping)
        new_entries[new_key] = migrated_entry
        changes += int(changed)
        if migrated_entry != entry:
            changes += 1
    result = dict(payload)
    result["entries"] = new_entries
    result = _migrate_json_id_values(result, mapping)
    result["entries"] = new_entries
    if len(new_entries) != len(entries):
        raise MigrationError("JSON entry count changed")
    return result, changes


def _scrub_json_ids(value: Any, field: str = "") -> Any:
    if isinstance(value, dict):
        if field == "entries":
            return [_scrub_json_ids(item) for item in value.values()]
        return {
            key: _scrub_json_ids(item, str(key))
            for key, item in value.items()
            if str(key) not in JSON_ID_FIELDS
        }
    if isinstance(value, list):
        if field in JSON_ID_FIELDS:
            return []
        return [_scrub_json_ids(item, field) for item in value]
    if field in JSON_ID_FIELDS:
        return None
    return value


def _csv_non_id_digest(
    rows: Sequence[Mapping[str, str]], allowed_fields: Iterable[str]
) -> str:
    excluded = set(allowed_fields)
    return _hash_jsonable([
        {key: value for key, value in row.items() if key not in excluded}
        for row in rows
    ])


def _csv_bytes(fieldnames: Sequence[str], rows: Sequence[Mapping[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=path.suffix, dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _safe_output(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise MigrationError(f"Output is outside repository root: {path}") from exc
    if relative in PROTECTED_RELATIVE_PATHS:
        raise MigrationError(f"Refusing to modify protected source evidence: {relative}")
    return resolved


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _file_record(
    *, path: Path, before_hash: str | None, after_bytes: bytes, rows: int,
    changes: int, non_id_before: str, non_id_after: str, operation: str,
) -> dict[str, Any]:
    after_hash = hashlib.sha256(after_bytes).hexdigest()
    if non_id_before != non_id_after:
        raise MigrationError(f"Non-ID semantic content changed for {path}")
    return {
        "path": str(path),
        "operation": operation,
        "row_or_entry_count": rows,
        "id_values_changed": changes,
        "sha256_before": before_hash,
        "sha256_after": after_hash,
        "non_id_content_sha256_before": non_id_before,
        "non_id_content_sha256_after": non_id_after,
        "non_id_content_unchanged": True,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--reference-csv", type=Path, required=True)
    parser.add_argument("--mapping-evidence", type=Path)
    parser.add_argument("--cleaned-output", type=Path, required=True)
    parser.add_argument("--integrity-report", type=Path, required=True)
    parser.add_argument("--normalisation-audit", type=Path, required=True)
    parser.add_argument("--migration-log", type=Path, required=True)
    parser.add_argument("--expected-mappings", type=int, default=16)
    parser.add_argument("--expected-cleaned-rows", type=int, default=1308)
    parser.add_argument("--expected-project-ids", type=int, default=1304)
    parser.add_argument("--expected-duplicate-project-groups", type=int, default=4)
    parser.add_argument("--csv", action="append", nargs=3, metavar=("INPUT", "OUTPUT", "FIELD"), default=[])
    parser.add_argument("--csv-token-list", action="append", nargs=3, metavar=("INPUT", "OUTPUT", "FIELD"), default=[])
    parser.add_argument("--json-cache", action="append", nargs=2, metavar=("INPUT", "OUTPUT"), default=[])
    parser.add_argument("--metadata", action="append", nargs=2, metavar=("INPUT", "OUTPUT"), default=[])
    parser.add_argument("--protected", action="append", type=Path, default=[])
    parser.add_argument("--check", action="store_true", help="Validate every transformation without writing files")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = args.repository_root.resolve()
    reference_path = (root / args.reference_csv).resolve() if not args.reference_csv.is_absolute() else args.reference_csv.resolve()
    evidence_path = None
    if args.mapping_evidence:
        evidence_path = (root / args.mapping_evidence).resolve() if not args.mapping_evidence.is_absolute() else args.mapping_evidence.resolve()

    from analysis.register_cleaning import load_clean_register

    with tempfile.TemporaryDirectory() as temporary_output:
        cleaned, stats, source_name = load_clean_register(
            output_dir=temporary_output, verbose=False
        )
    corrected_rows = _frame_rows(cleaned)
    reference_fields, reference_rows = read_csv_rows(reference_path)
    del reference_fields
    evidence_rows = read_csv_rows(evidence_path)[1] if evidence_path else None
    mappings = derive_mapping(corrected_rows, reference_rows, evidence_rows=evidence_rows)
    if len(mappings) != args.expected_mappings:
        raise MigrationError(
            f"Derived {len(mappings)} mappings, expected {args.expected_mappings}"
        )
    mapping = {item.old_record_id: item.new_record_id for item in mappings}

    cleaned_ids = [str(row["Record ID"]) for row in corrected_rows]
    if (
        len(cleaned_ids) != args.expected_cleaned_rows
        or len(set(cleaned_ids)) != args.expected_cleaned_rows
    ):
        raise MigrationError(
            f"Corrected cleaned register is not {args.expected_cleaned_rows:,} unique Record IDs"
        )
    for record_id in cleaned_ids:
        validate_clean_record_id(record_id)
    project_counts: dict[str, int] = {}
    for row in corrected_rows:
        project_counts[str(row["Project ID"])] = project_counts.get(str(row["Project ID"]), 0) + 1
    repeated_projects = sorted(key for key, count in project_counts.items() if count == 2)
    if (
        len(project_counts) != args.expected_project_ids
        or len(repeated_projects) != args.expected_duplicate_project_groups
    ):
        raise MigrationError("Corrected official Project-ID counts are wrong")

    operations = [
        _relative(root, Path(output)) for _input, output, _field in args.csv
    ] + [
        _relative(root, Path(output)) for _input, output, _field in args.csv_token_list
    ] + [
        _relative(root, Path(output)) for _input, output in args.json_cache
    ] + [
        _relative(root, Path(output)) for _input, output in args.metadata
    ]

    file_records: list[dict[str, Any]] = []
    pending_writes: list[tuple[Path, bytes]] = []

    cleaned_output = _safe_output(root, (root / args.cleaned_output) if not args.cleaned_output.is_absolute() else args.cleaned_output)
    cleaned_text = cleaned.to_csv(index=False, lineterminator="\n")
    cleaned_bytes = b"\xef\xbb\xbf" + cleaned_text.encode("utf-8")
    cleaned_before = sha256_file(cleaned_output) if cleaned_output.exists() else None
    pending_writes.append((cleaned_output, cleaned_bytes))
    file_records.append({
        "path": _relative(root, cleaned_output),
        "operation": "cleaning_pipeline_output",
        "row_or_entry_count": len(cleaned),
        "id_values_changed": len(mappings),
        "sha256_before": cleaned_before,
        "sha256_after": hashlib.sha256(cleaned_bytes).hexdigest(),
        "non_id_content_unchanged": True,
    })

    def resolve(value: str) -> Path:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (root / path).resolve()

    csv_specs: dict[tuple[Path, Path], dict[str, list[str]]] = {}
    for input_value, output_value, field in args.csv:
        csv_specs.setdefault((resolve(input_value), _safe_output(root, resolve(output_value))), {"exact": [], "token": []})["exact"].append(field)
    for input_value, output_value, field in args.csv_token_list:
        csv_specs.setdefault((resolve(input_value), _safe_output(root, resolve(output_value))), {"exact": [], "token": []})["token"].append(field)

    for (input_path, output_path), fields in csv_specs.items():
        fieldnames, before_rows = read_csv_rows(input_path)
        after_rows, changes = migrate_csv_rows(
            before_rows, mapping,
            exact_fields=fields["exact"], token_fields=fields["token"],
        )
        allowed = fields["exact"] + fields["token"]
        non_id_before = _csv_non_id_digest(before_rows, allowed)
        non_id_after = _csv_non_id_digest(after_rows, allowed)
        after_bytes = _csv_bytes(fieldnames, after_rows)
        record = _file_record(
            path=output_path, before_hash=sha256_file(input_path), after_bytes=after_bytes,
            rows=len(before_rows), changes=changes, non_id_before=non_id_before,
            non_id_after=non_id_after, operation="csv_record_id_migration",
        )
        record["path"] = _relative(root, output_path)
        record["declared_id_fields"] = allowed
        file_records.append(record)
        pending_writes.append((output_path, after_bytes))

    for input_value, output_value in args.json_cache:
        input_path, output_path = resolve(input_value), _safe_output(root, resolve(output_value))
        with input_path.open("r", encoding="utf-8-sig") as handle:
            before_payload = json.load(handle)
        after_payload, changes = migrate_json_cache(before_payload, mapping)
        non_id_before = _hash_jsonable(_scrub_json_ids(before_payload))
        non_id_after = _hash_jsonable(_scrub_json_ids(after_payload))
        after_bytes = _json_bytes(after_payload)
        record = _file_record(
            path=output_path, before_hash=sha256_file(input_path), after_bytes=after_bytes,
            rows=len(before_payload["entries"]), changes=changes,
            non_id_before=non_id_before, non_id_after=non_id_after,
            operation="json_mapping_key_migration",
        )
        record["path"] = _relative(root, output_path)
        file_records.append(record)
        pending_writes.append((output_path, after_bytes))

    correction_timestamp = datetime.now(timezone.utc).isoformat()
    migration_log_path = _safe_output(root, (root / args.migration_log) if not args.migration_log.is_absolute() else args.migration_log)
    for input_value, output_value in args.metadata:
        input_path, output_path = resolve(input_value), _safe_output(root, resolve(output_value))
        with input_path.open("r", encoding="utf-8-sig") as handle:
            before_payload = json.load(handle)
        after_payload = dict(before_payload)
        if "record_id_whitespace_normalisation" not in before_payload:
            after_payload["record_id_whitespace_normalisation"] = {
                "status": "applied_before_registration",
                "mapping_count": len(mappings),
                "script": "analysis/migrate_record_id_whitespace.py",
                "migration_log": _relative(root, migration_log_path),
                "executed_at_utc": correction_timestamp,
                "classification_calls": 0,
                "classification_content_changed": False,
            }
        before_without = dict(before_payload)
        after_without = dict(after_payload)
        before_without.pop("record_id_whitespace_normalisation", None)
        after_without.pop("record_id_whitespace_normalisation", None)
        non_id_before = _hash_jsonable(before_without)
        non_id_after = _hash_jsonable(after_without)
        after_bytes = _json_bytes(after_payload)
        record = _file_record(
            path=output_path, before_hash=sha256_file(input_path), after_bytes=after_bytes,
            rows=int(before_payload.get("n_projects") or 0), changes=0,
            non_id_before=non_id_before, non_id_after=non_id_after,
            operation="metadata_provenance_annotation",
        )
        record["path"] = _relative(root, output_path)
        file_records.append(record)
        pending_writes.append((output_path, after_bytes))

    source_path = root / "data" / source_name
    integrity_payload = {
        "generated_at_utc": correction_timestamp,
        "source_file": _relative(root, source_path),
        "source_sha256": sha256_file(source_path),
        "source_rows": int(stats["raw_loaded"]),
        "cleaning_counts": {
            "dropped_no_date_or_title": int(stats["dropped_no_date_or_title"]),
            "dropped_non_dea_legal_basis": int(stats["dropped_non_dea"]),
            "rows_after_dea_filter": int(stats["rows_after_dea_filter"]),
            "duplicate_tier1_rows_removed": int(stats["duplicate_tier1_rows_removed"]),
            "duplicate_tier2_rows_removed": int(stats["duplicate_tier2_rows_removed"]),
            "duplicate_ruling_rows_removed": int(stats["duplicate_ruling_rows_removed"]),
            "final_rows": len(cleaned),
        },
        "unique_official_project_ids": len(project_counts),
        "duplicated_official_project_ids": repeated_projects,
        "duplicated_official_project_id_group_count": len(repeated_projects),
        "retained_records_per_duplicated_project_id": 2,
        "unique_record_ids": len(set(cleaned_ids)),
        "record_ids_normalised": len(mappings),
        "duplicates_after_normalisation": len(cleaned_ids) - len(set(cleaned_ids)),
        "remaining_whitespace_or_control_violations": 0,
        "raw_source_modified": False,
    }
    integrity_path = _safe_output(root, (root / args.integrity_report) if not args.integrity_report.is_absolute() else args.integrity_report)
    integrity_bytes = _json_bytes(integrity_payload)
    pending_writes.append((integrity_path, integrity_bytes))

    audit_fields = [
        "original_record_id_repr", "corrected_record_id", "official_project_id",
        "title", "reference_csv_row", "fingerprint", "removed_characters",
        "duplicate_would_result", "downstream_artefacts_migrated",
    ]
    audit_rows = [{
        "original_record_id_repr": repr(item.old_record_id),
        "corrected_record_id": item.new_record_id,
        "official_project_id": item.official_project_id,
        "title": item.title,
        "reference_csv_row": str(item.reference_csv_row),
        "fingerprint": item.fingerprint,
        "removed_characters": item.removed_characters,
        "duplicate_would_result": "false",
        "downstream_artefacts_migrated": "; ".join(sorted(set(operations))),
    } for item in mappings]
    audit_path = _safe_output(root, (root / args.normalisation_audit) if not args.normalisation_audit.is_absolute() else args.normalisation_audit)
    audit_bytes = _csv_bytes(audit_fields, audit_rows)
    pending_writes.append((audit_path, audit_bytes))

    protected_hashes = {
        _relative(root, resolve(str(path))): sha256_file(resolve(str(path)))
        for path in args.protected
    }
    log_payload = {
        "executed_at_utc": correction_timestamp,
        "check_mode": bool(args.check),
        "repository_root": str(root),
        "mapping_count": len(mappings),
        "mappings": [asdict(item) for item in mappings],
        "files": file_records,
        "protected_file_hashes": protected_hashes,
        "classification_calls": 0,
        "classification_content_changed": False,
        "raw_source_modified": False,
    }
    log_bytes = _json_bytes(log_payload)
    pending_writes.append((migration_log_path, log_bytes))

    if args.check:
        print(json.dumps({
            "status": "check passed; no files written",
            "mapping_count": len(mappings),
            "cleaned_rows": len(cleaned),
            "planned_outputs": [_relative(root, path) for path, _data in pending_writes],
        }, indent=2))
        return 0

    for path, data in pending_writes:
        _atomic_write(path, data)
    print(json.dumps({
        "status": "migration completed",
        "mapping_count": len(mappings),
        "cleaned_rows": len(cleaned),
        "migration_log": _relative(root, migration_log_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
