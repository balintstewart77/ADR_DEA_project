"""Append-only, hash-addressed register provenance manifest.

Single source of truth for which source extract of the UKSA register the
pipeline and dashboard load. Schema 2 separates fetch observations, immutable
content snapshots, analytical states, and mutable-live versus frozen-release
pointers in ``data/register_provenance_manifest.json``. The frozen legacy
``data/register_manifest.json`` remains byte-identical, and the compatibility
``current``/``versions`` view remains available.

Adding a new register version is a manifest update, not a code change:

    python -m analysis.register_manifest add data/dea_accredited_projects_YYYYMMDD.csv \
        --xlsx data/dea_accredited_projects_YYYYMMDD.xlsx \
        --source-url <download url>

    python -m analysis.register_manifest show
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MANIFEST_FILENAME = "register_provenance_manifest.json"
LEGACY_MANIFEST_FILENAME = "register_manifest.json"
MANIFEST_SCHEMA_VERSION = 2
CURRENT_POINTER = "current_latest_revision"
FROZEN_VALIDATION_POINTER = "frozen_validation_snapshot"
FROZEN_SOURCE_XLSX_SHA256 = "4f3851544846059c15b4df4dadc63b33079ca47a07e4eae41e98d5ddb3e452a3"
FROZEN_SOURCE_CSV_SHA256 = "abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d"
FROZEN_CLEANED_PATH = (
    "preregistration/package/01_source_and_cleaning/"
    "dea_accredited_projects_20260601_cleaned_1308.csv"
)
FROZEN_CLEANED_SHA256 = "a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1"
OBSERVATION_IDENTITY_FIELDS = (
    "nominal_source_date",
    "source_url",
    "raw_xlsx_sha256",
    "canonical_csv_sha256",
)

_VERSIONED_FILENAME_RE = re.compile(r"dea_accredited_projects_(\d{8})\.csv$")


def manifest_path(data_dir: str = DATA_DIR) -> str:
    return os.path.join(data_dir, MANIFEST_FILENAME)


def load_manifest(data_dir: str = DATA_DIR) -> dict | None:
    """Return the parsed manifest, or None when no manifest exists yet."""
    path = manifest_path(data_dir)
    if not os.path.exists(path):
        legacy_path = os.path.join(data_dir, LEGACY_MANIFEST_FILENAME)
        if not os.path.exists(legacy_path):
            return None
        path = legacy_path
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if "versions" not in manifest or "current" not in manifest:
        raise ValueError(f"Register manifest at {path} is missing 'versions' or 'current'")
    if manifest.get("schema_version", 1) >= 2:
        _validate_v2_manifest(manifest, path)
    return manifest


def _validate_v2_manifest(manifest: dict, path: str) -> None:
    for key in ("pointers", "content_snapshots", "fetch_observations", "analytical_states"):
        if key not in manifest:
            raise ValueError(f"Register manifest at {path} is missing '{key}'")
    pointers = manifest["pointers"]
    for pointer in (CURRENT_POINTER, FROZEN_VALIDATION_POINTER):
        if pointer not in pointers:
            raise ValueError(f"Register manifest at {path} is missing pointer '{pointer}'")
    snapshot_ids = [snapshot["snapshot_id"] for snapshot in manifest["content_snapshots"]]
    if len(snapshot_ids) != len(set(snapshot_ids)):
        raise ValueError(f"Register manifest at {path} contains duplicate snapshot IDs")
    known = set(snapshot_ids)
    for pointer, record in pointers.items():
        if record["snapshot_id"] not in known:
            raise ValueError(f"Pointer '{pointer}' references unknown snapshot {record['snapshot_id']}")
        snapshot = snapshot_record(manifest, record["snapshot_id"])
        if record.get("canonical_csv_sha256") != snapshot["canonical_csv_sha256"]:
            raise ValueError(f"Pointer '{pointer}' canonical CSV hash does not match its snapshot")
        if record.get("raw_xlsx_sha256") != snapshot.get("raw_xlsx_sha256"):
            raise ValueError(f"Pointer '{pointer}' raw XLSX hash does not match its snapshot")
    for observation in manifest["fetch_observations"]:
        if observation["snapshot_id"] not in known:
            raise ValueError(f"Observation references unknown snapshot {observation['snapshot_id']}")
        snapshot = snapshot_record(manifest, observation["snapshot_id"])
        if observation["raw_xlsx_sha256"] != snapshot["raw_xlsx_sha256"]:
            raise ValueError("Observation raw hash does not match its snapshot")
        if observation["canonical_csv_sha256"] != snapshot["canonical_csv_sha256"]:
            raise ValueError("Observation canonical hash does not match its snapshot")
    for state in manifest["analytical_states"]:
        if not set(state.get("source_snapshot_ids", [])) <= known:
            raise ValueError("Analytical state references an unknown source snapshot")
    frozen = pointers[FROZEN_VALIDATION_POINTER]
    if frozen.get("raw_xlsx_sha256") != FROZEN_SOURCE_XLSX_SHA256:
        raise ValueError(
            "Frozen validation source pointer changed: expected raw XLSX "
            f"{FROZEN_SOURCE_XLSX_SHA256}, got {frozen.get('raw_xlsx_sha256')}"
        )
    if frozen.get("canonical_csv_sha256") != FROZEN_SOURCE_CSV_SHA256:
        raise ValueError(
            "Frozen validation source pointer changed: expected canonical CSV "
            f"{FROZEN_SOURCE_CSV_SHA256}, got {frozen.get('canonical_csv_sha256')}"
        )
    if frozen.get("cleaned_population_sha256") != FROZEN_CLEANED_SHA256:
        raise ValueError("Frozen validation cleaned-population binding changed")
    if frozen.get("cleaned_population_path") != FROZEN_CLEANED_PATH:
        raise ValueError("Frozen validation cleaned-population path changed")


def write_manifest(manifest: dict, data_dir: str = DATA_DIR) -> str:
    path = manifest_path(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    if manifest.get("schema_version", 1) >= 2:
        _validate_v2_manifest(manifest, path)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(temp_path, path)
    return path


def _version_record(manifest: dict, version: str) -> dict:
    if version == "current":
        if manifest.get("schema_version", 1) >= 2:
            snapshot = snapshot_record(manifest, CURRENT_POINTER)
            version = snapshot["nominal_source_date"].replace("-", "")
        else:
            version = manifest["current"]
    for record in manifest["versions"]:
        if record["version"] == version:
            return record
    available = ", ".join(r["version"] for r in manifest["versions"])
    raise FileNotFoundError(
        f"Register version '{version}' not found in manifest (available: {available})"
    )


def snapshot_record(manifest: dict, snapshot_ref: str) -> dict:
    """Resolve a snapshot ID, either content hash, or named pointer."""
    pointer = manifest.get("pointers", {}).get(snapshot_ref)
    if pointer:
        snapshot_ref = pointer["snapshot_id"]
    for snapshot in manifest.get("content_snapshots", []):
        references = {
            snapshot["snapshot_id"],
            snapshot.get("raw_xlsx_sha256"),
            snapshot.get("canonical_csv_sha256"),
        }
        if snapshot_ref in references:
            return snapshot
    raise FileNotFoundError(f"Register snapshot '{snapshot_ref}' not found in manifest")


def resolve_snapshot_csv(
    data_dir: str = DATA_DIR,
    snapshot_ref: str = CURRENT_POINTER,
) -> tuple[str, dict]:
    manifest = load_manifest(data_dir)
    if manifest is None:
        raise FileNotFoundError(f"No {MANIFEST_FILENAME} found in {data_dir}")
    if manifest.get("schema_version", 1) < 2:
        raise FileNotFoundError("Hash-addressed snapshots require manifest schema 2")
    snapshot = snapshot_record(manifest, snapshot_ref)
    path = os.path.join(data_dir, *snapshot["canonical_csv_path"].split("/"))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Snapshot {snapshot['snapshot_id']} points at missing file {path}")
    return path, snapshot


def resolve_register_csv(
    data_dir: str = DATA_DIR,
    version: str = "current",
) -> tuple[str, dict]:
    """Return (csv path, version record) for a manifest version.

    Raises FileNotFoundError when the manifest is missing, the version is
    unknown, or the referenced file does not exist on disk.
    """
    manifest = load_manifest(data_dir)
    if manifest is None:
        raise FileNotFoundError(f"No {MANIFEST_FILENAME} found in {data_dir}")
    if manifest.get("schema_version", 1) >= 2:
        if version in {"current", CURRENT_POINTER, FROZEN_VALIDATION_POINTER}:
            pointer = CURRENT_POINTER if version == "current" else version
            path, snapshot = resolve_snapshot_csv(data_dir, pointer)
            version = snapshot["nominal_source_date"].replace("-", "")
            record = dict(_version_record(manifest, version))
            record.update(_compatibility_fields(snapshot))
            return path, record
        record = _version_record(manifest, version)
        if record.get("latest_snapshot_id"):
            path, snapshot = resolve_snapshot_csv(data_dir, record["latest_snapshot_id"])
            resolved = dict(record)
            resolved.update(_compatibility_fields(snapshot))
            return path, resolved
    else:
        record = _version_record(manifest, version)
    path = os.path.join(data_dir, *record["csv"].replace("\\", "/").split("/"))
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Manifest version '{record['version']}' points at missing file {path}"
        )
    return path, record


def _compatibility_fields(snapshot: dict) -> dict:
    return {
        "csv": snapshot["canonical_csv_path"],
        "xlsx": snapshot.get("raw_xlsx_path"),
        "source_url": snapshot.get("source_url"),
        "retrieved_at": snapshot.get("first_seen_at"),
        "sha256_csv": snapshot["canonical_csv_sha256"],
        "sha256_xlsx": snapshot.get("raw_xlsx_sha256"),
        "row_count": snapshot["raw_row_count"],
        "snapshot_id": snapshot["snapshot_id"],
    }


def previous_ingested_snapshot(manifest: dict, snapshot_ref: str) -> dict | None:
    """Return the preceding distinct snapshot in append-only observation order."""
    target = snapshot_record(manifest, snapshot_ref)["snapshot_id"]
    distinct: list[str] = []
    for observation in manifest.get("fetch_observations", []):
        snapshot_id = observation["snapshot_id"]
        if snapshot_id not in distinct:
            distinct.append(snapshot_id)
    if target not in distinct:
        return None
    index = distinct.index(target)
    return snapshot_record(manifest, distinct[index - 1]) if index else None


def latest_snapshot_for_nominal_date(manifest: dict, nominal_source_date: str) -> dict:
    candidates = [
        snapshot for snapshot in manifest.get("content_snapshots", [])
        if snapshot.get("nominal_source_date") == nominal_source_date
    ]
    if not candidates:
        raise FileNotFoundError(f"No snapshot for nominal source date {nominal_source_date}")
    order = {
        observation["snapshot_id"]: index
        for index, observation in enumerate(manifest.get("fetch_observations", []))
    }
    return max(candidates, key=lambda snapshot: order.get(snapshot["snapshot_id"], -1))


def previous_nominal_release_snapshot(manifest: dict, snapshot_ref: str) -> dict | None:
    target = snapshot_record(manifest, snapshot_ref)
    earlier = sorted({
        snapshot["nominal_source_date"]
        for snapshot in manifest.get("content_snapshots", [])
        if snapshot.get("nominal_source_date")
        and snapshot["nominal_source_date"] < target["nominal_source_date"]
    })
    return latest_snapshot_for_nominal_date(manifest, earlier[-1]) if earlier else None


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_row_count(path: str) -> int:
    # pandas handles quoted embedded newlines, which a raw line count would not.
    return len(pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_upstream_filename(source_url: str) -> str:
    name = os.path.basename(urlparse(source_url).path) or "register.xlsx"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def matching_fetch_observation(manifest: dict, identity: dict) -> dict | None:
    """Return an observation with the same stable provenance identity, if any."""
    missing = [field for field in OBSERVATION_IDENTITY_FIELDS if field not in identity]
    if missing:
        raise ValueError(f"Observation identity is missing fields: {missing}")
    return next(
        (
            item for item in manifest.get("fetch_observations", [])
            if all(item.get(field) == identity[field] for field in OBSERVATION_IDENTITY_FIELDS)
        ),
        None,
    )


def _write_immutable(path: str, data: bytes) -> None:
    if os.path.exists(path):
        if _sha256(path) != _sha256_bytes(data):
            raise FileExistsError(f"Refusing to overwrite existing snapshot bytes at {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "xb") as f:
        f.write(data)


def record_fetch_observation(
    *,
    data_dir: str,
    source_url: str,
    nominal_source_date: str,
    upload_directory_date: str | None,
    xlsx_bytes: bytes,
    canonical_csv_bytes: bytes,
    raw_row_count: int,
    converter: dict,
    observed_at: str | None = None,
    set_current: bool = True,
) -> dict:
    """Record meaningful provenance and archive new content without overwriting.

    Observation identity is the structured tuple of nominal source date, URL,
    raw XLSX hash and canonical CSV hash. An exact repeat is a byte-stable
    successful no-op; its retrieval timestamp is deliberately ignored.
    """
    manifest = load_manifest(data_dir)
    if manifest is None or manifest.get("schema_version", 1) < 2:
        raise ValueError("Fetch observations require an existing schema-2 manifest")
    raw_sha = _sha256_bytes(xlsx_bytes)
    csv_sha = _sha256_bytes(canonical_csv_bytes)
    observed_at = observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    previous = snapshot_record(manifest, CURRENT_POINTER)
    identity = {
        "nominal_source_date": nominal_source_date,
        "source_url": source_url,
        "raw_xlsx_sha256": raw_sha,
        "canonical_csv_sha256": csv_sha,
    }
    existing_observation = matching_fetch_observation(manifest, identity)
    if existing_observation is not None:
        snapshot = snapshot_record(manifest, existing_observation["snapshot_id"])
        return {
            "snapshot": snapshot,
            "observation": existing_observation,
            "created_snapshot": False,
            "created_observation": False,
            "outcome": "unchanged_noop",
            "previous_snapshot_id": previous["snapshot_id"],
        }

    snapshot = next(
        (
            item for item in manifest["content_snapshots"]
            if item.get("raw_xlsx_sha256") == raw_sha
            and item.get("canonical_csv_sha256") == csv_sha
        ),
        None,
    )
    raw_hash_collision = any(
        item.get("raw_xlsx_sha256") == raw_sha
        for item in manifest["content_snapshots"]
    )
    snapshot_id = (
        f"sha256:{raw_sha}:csv-sha256:{csv_sha}"
        if raw_hash_collision and snapshot is None
        else f"sha256:{raw_sha}"
    )
    created_snapshot = snapshot is None
    upstream_filename = _safe_upstream_filename(source_url)
    if created_snapshot:
        archive_key = f"{raw_sha}-{csv_sha}" if raw_hash_collision else raw_sha
        archive_dir = f"register_snapshots/{archive_key}"
        xlsx_rel = f"{archive_dir}/{upstream_filename}"
        csv_rel = f"{archive_dir}/canonical.csv"
        _write_immutable(os.path.join(data_dir, *xlsx_rel.split("/")), xlsx_bytes)
        _write_immutable(os.path.join(data_dir, *csv_rel.split("/")), canonical_csv_bytes)
        snapshot = {
            "snapshot_id": snapshot_id,
            "raw_xlsx_path": xlsx_rel,
            "canonical_csv_path": csv_rel,
            "raw_xlsx_sha256": raw_sha,
            "canonical_csv_sha256": csv_sha,
            "raw_row_count": raw_row_count,
            "first_seen_at": observed_at,
            "nominal_source_date": nominal_source_date,
            "source_url": source_url,
            "upstream_filename": upstream_filename,
            "converter": converter,
        }
        manifest["content_snapshots"].append(snapshot)
    else:
        if snapshot["raw_row_count"] != raw_row_count:
            raise ValueError("Identical snapshot hash produced a different row count")

    observation = {
        "observation_id": f"obs-{len(manifest['fetch_observations']) + 1:04d}",
        "observed_at": observed_at,
        "source_url": source_url,
        "upstream_filename": upstream_filename,
        "nominal_source_date": nominal_source_date,
        "upload_directory_date": upload_directory_date,
        "raw_xlsx_sha256": raw_sha,
        "canonical_csv_sha256": csv_sha,
        "snapshot_id": snapshot_id,
        "converter": converter,
    }
    manifest["fetch_observations"].append(observation)
    nominal_version = nominal_source_date.replace("-", "")
    version = next((item for item in manifest["versions"] if item["version"] == nominal_version), None)
    if version is None:
        version = {"version": nominal_version}
        manifest["versions"].append(version)
    version.update({"latest_snapshot_id": snapshot_id, **_compatibility_fields(snapshot)})
    manifest["versions"].sort(key=lambda item: item["version"])
    if set_current:
        manifest["current"] = nominal_version
        manifest["pointers"][CURRENT_POINTER] = {
            "snapshot_id": snapshot_id,
            "raw_xlsx_sha256": raw_sha,
            "canonical_csv_sha256": csv_sha,
        }
    write_manifest(manifest, data_dir)
    return {
        "snapshot": snapshot,
        "observation": observation,
        "created_snapshot": created_snapshot,
        "created_observation": True,
        "outcome": "new_snapshot" if created_snapshot else "new_provenance_observation",
        "previous_snapshot_id": previous["snapshot_id"],
    }


def add_version(
    csv_path: str,
    *,
    data_dir: str = DATA_DIR,
    xlsx_path: str | None = None,
    source_url: str | None = None,
    version: str | None = None,
    retrieved_at: str | None = None,
    notes: str | None = None,
    set_current: bool = True,
) -> dict:
    """Register a CSV (and optional XLSX) in the manifest and return its record.

    Files must already live inside ``data_dir``; the manifest stores bare file
    names. Re-adding an existing version replaces its record.
    """
    csv_name = os.path.basename(csv_path)
    full_csv = os.path.join(data_dir, csv_name)
    if not os.path.exists(full_csv):
        raise FileNotFoundError(f"CSV not found in data dir: {full_csv}")

    if version is None:
        match = _VERSIONED_FILENAME_RE.search(csv_name)
        if not match:
            raise ValueError(
                f"Cannot derive a version from '{csv_name}'; pass version= explicitly"
            )
        version = match.group(1)

    xlsx_name = None
    if xlsx_path:
        xlsx_name = os.path.basename(xlsx_path)
        if not os.path.exists(os.path.join(data_dir, xlsx_name)):
            raise FileNotFoundError(f"XLSX not found in data dir: {xlsx_name}")

    record = {
        "version": version,
        "csv": csv_name,
        "xlsx": xlsx_name,
        "source_url": source_url,
        "retrieved_at": retrieved_at or date.today().isoformat(),
        "sha256_csv": _sha256(full_csv),
        "row_count": _csv_row_count(full_csv),
    }
    if notes:
        record["notes"] = notes

    manifest = load_manifest(data_dir)
    if manifest is not None and manifest.get("schema_version", 1) >= 2:
        raise ValueError(
            "add_version cannot mutate a schema-2 append-only manifest; "
            "use record_fetch_observation"
        )
    if manifest is None:
        manifest = {
            # Compatibility bootstrap only. Automated fetch refuses schema 1
            # and uses record_fetch_observation with immutable schema-2 state.
            "schema_version": 1,
            "current": version,
            "versions": [],
        }
    manifest["versions"] = [
        r for r in manifest["versions"] if r["version"] != version
    ] + [record]
    manifest["versions"].sort(key=lambda r: r["version"])
    if set_current:
        manifest["current"] = version
    write_manifest(manifest, data_dir)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the register data-version manifest")
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="Print the manifest")
    show.add_argument("--data-dir", default=DATA_DIR)

    add = sub.add_parser("add", help="Add or update a register version")
    add.add_argument("csv", help="CSV file inside the data directory")
    add.add_argument("--data-dir", default=DATA_DIR)
    add.add_argument("--xlsx", default=None, help="Matching XLSX file, if any")
    add.add_argument("--source-url", default=None)
    add.add_argument("--version", default=None, help="Override the filename-derived version")
    add.add_argument("--retrieved-at", default=None, help="ISO date the file was retrieved")
    add.add_argument("--notes", default=None)
    add.add_argument(
        "--no-set-current",
        action="store_true",
        help="Register the version without making it the current one",
    )

    args = parser.parse_args()
    if args.command == "show":
        manifest = load_manifest(args.data_dir)
        if manifest is None:
            print(f"No {MANIFEST_FILENAME} in {args.data_dir}")
            return
        print(json.dumps(manifest, indent=2))
        return

    record = add_version(
        args.csv,
        data_dir=args.data_dir,
        xlsx_path=args.xlsx,
        source_url=args.source_url,
        version=args.version,
        retrieved_at=args.retrieved_at,
        notes=args.notes,
        set_current=not args.no_set_current,
    )
    print(f"Registered version {record['version']} ({record['row_count']:,} rows)")
    if not args.no_set_current:
        print(f"Manifest 'current' now points at {record['version']}")


if __name__ == "__main__":
    main()
