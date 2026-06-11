"""Register data-version manifest.

Single source of truth for which source extract of the UKSA register the
pipeline and dashboard load. The manifest lives at
``data/register_manifest.json`` and records every retained register version
(file names, provenance, sha256, row count) plus a ``current`` pointer.

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
from datetime import date

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MANIFEST_FILENAME = "register_manifest.json"
MANIFEST_SCHEMA_VERSION = 1

_VERSIONED_FILENAME_RE = re.compile(r"dea_accredited_projects_(\d{8})\.csv$")


def manifest_path(data_dir: str = DATA_DIR) -> str:
    return os.path.join(data_dir, MANIFEST_FILENAME)


def load_manifest(data_dir: str = DATA_DIR) -> dict | None:
    """Return the parsed manifest, or None when no manifest exists yet."""
    path = manifest_path(data_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    if "versions" not in manifest or "current" not in manifest:
        raise ValueError(f"Register manifest at {path} is missing 'versions' or 'current'")
    return manifest


def write_manifest(manifest: dict, data_dir: str = DATA_DIR) -> str:
    path = manifest_path(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
        f.write("\n")
    return path


def _version_record(manifest: dict, version: str) -> dict:
    if version == "current":
        version = manifest["current"]
    for record in manifest["versions"]:
        if record["version"] == version:
            return record
    available = ", ".join(r["version"] for r in manifest["versions"])
    raise FileNotFoundError(
        f"Register version '{version}' not found in manifest (available: {available})"
    )


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
    record = _version_record(manifest, version)
    path = os.path.join(data_dir, record["csv"])
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Manifest version '{record['version']}' points at missing file {path}"
        )
    return path, record


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_row_count(path: str) -> int:
    # pandas handles quoted embedded newlines, which a raw line count would not.
    return len(pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False))


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
    if manifest is None:
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
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
