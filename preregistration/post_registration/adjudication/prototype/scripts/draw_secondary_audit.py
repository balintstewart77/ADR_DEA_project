"""Draw the secondary audit only from an explicit completed-primary manifest.

The input manifest must have source_record_id, completed_primary (0/1),
apparent_production_model_rule_problem (0/1), unresolved_finding (0/1), and
release_implications (semicolon-separated values). Rows marked completed_primary
0 do not enter N. Outputs, including identifiers and selection flags, are
administrative files in the git-ignored restricted directory, never REDCap imports.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
SEED_ADJUDICATION_AUDIT = 20260715
SEED_SECONDARY_QUEUE = 20260924  # separate implementation seed; not preregistered
GENERATOR_VERSION = "secondary-audit-1.0"
REQUIRED = ("source_record_id", "completed_primary",
            "apparent_production_model_rule_problem", "unresolved_finding",
            "release_implications")
MANDATORY_RELEASE = {"prompt revision", "taxonomy revision", "non-release"}
RELEASE_ALIASES = {"2": "prompt revision", "3": "taxonomy revision", "5": "non-release",
                   "evidence for prompt revision": "prompt revision",
                   "evidence for taxonomy revision": "taxonomy revision",
                   "evidence for non-release": "non-release"}
NONMANDATORY_RELEASE = {"0", "1", "4", "6", "9", "none", "caveat", "caveat only",
                        "data or instrument repair", "data/instrument repair",
                        "escalate: may alter a headline dashboard output", "pending"}
OUT = REPO / "preregistration_restricted"


def read_manifest(path: Path):
    if not path.is_file():
        raise ValueError("an input manifest file is required")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or any(field not in reader.fieldnames for field in REQUIRED):
            raise ValueError("manifest lacks required completed-primary or mandatory-review columns")
        rows = list(reader)
    if not rows:
        raise ValueError("input manifest has no records")
    seen = set()
    for row in rows:
        if None in row or any(row[field] is None for field in REQUIRED):
            raise ValueError("manifest contains a malformed row")
        rid = row["source_record_id"].strip()
        if not rid or rid in seen:
            raise ValueError("manifest has a blank or duplicate source Record ID")
        seen.add(rid)
        row["source_record_id"] = rid
        for field in REQUIRED[1:4]:
            if row[field] not in {"0", "1"}:
                raise ValueError(f"manifest {field} must be 0 or 1")
        release = {s.strip().lower() for s in row["release_implications"].split(";") if s.strip()}
        if release - MANDATORY_RELEASE - RELEASE_ALIASES.keys() - NONMANDATORY_RELEASE:
            raise ValueError("manifest contains an unknown release implication")
    return rows


def draw(rows, audit_seed=SEED_ADJUDICATION_AUDIT, queue_seed=SEED_SECONDARY_QUEUE):
    """Return stable universe, random IDs, mandatory IDs, and interleaved rows."""
    universe = sorted((r for r in rows if r["completed_primary"] == "1"),
                      key=lambda r: r["source_record_id"])
    ordered_ids = [r["source_record_id"] for r in universe]
    random_count = math.ceil(0.20 * len(universe))
    random_ids = set(random.Random(audit_seed).sample(ordered_ids, random_count))
    mandatory_ids = set()
    for row in universe:
        release = {RELEASE_ALIASES.get(s.strip().lower(), s.strip().lower())
                   for s in row["release_implications"].split(";") if s.strip()}
        if (row["apparent_production_model_rule_problem"] == "1"
                or row["unresolved_finding"] == "1" or release & MANDATORY_RELEASE):
            mandatory_ids.add(row["source_record_id"])
    combined = sorted(random_ids | mandatory_ids)
    random.Random(queue_seed).shuffle(combined)
    result = [{"source_record_id": rid, "random_draw": int(rid in random_ids),
               "mandatory_review": int(rid in mandatory_ids), "queue_position": n}
              for n, rid in enumerate(combined, 1)]
    return ordered_ids, random_ids, mandatory_ids, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="existing restricted manifest with completed-primary status and mandatory-review flags")
    args = parser.parse_args(argv)
    if not args.manifest.resolve().is_relative_to(OUT.resolve()):
        parser.error("input manifest must be inside preregistration_restricted")
    rows = read_manifest(args.manifest)
    universe, random_ids, mandatory_ids, selected = draw(rows)
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "input_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
               "stable_input_order": universe, "selected_universe": sorted(random_ids | mandatory_ids),
               "selection_algorithm": "stable source_record_id sort; Python random.Random.sample without replacement; mandatory union after full random draw",
               "queue_algorithm": "sort selected IDs, then independent Python random.Random.shuffle",
               "library": "Python standard-library random (Mersenne Twister)",
               "library_version": platform.python_version(), "generator_version": GENERATOR_VERSION,
               "generator_commit": commit, "audit_seed": SEED_ADJUDICATION_AUDIT,
               "queue_seed": SEED_SECONDARY_QUEUE, "N_completed_primary": len(universe),
               "random_count": len(random_ids), "mandatory_count": len(mandatory_ids),
               "combined_count": len(selected), "result_order": [r["source_record_id"] for r in selected]}
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "adjudication_secondary_audit_draw.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=("source_record_id", "random_draw", "mandatory_review", "queue_position"))
        writer.writeheader()
        writer.writerows(selected)
    (OUT / "adjudication_secondary_audit_draw.receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"N_completed_primary": len(universe), "random_count": len(random_ids),
                      "mandatory_count": len(mandatory_ids), "combined_count": len(selected)}, indent=2))


if __name__ == "__main__":
    main()
