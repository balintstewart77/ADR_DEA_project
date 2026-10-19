"""Draw the secondary audit only from an explicit completed-primary manifest.

Implements protocol 9.1 as amended by AMD-002. The input manifest must have
source_record_id, completed_primary (0/1), unresolved_finding (0/1),
release_implications (semicolon-separated values), retracted_model_finding (0/1:
a model rule-application finding retracted by a recorded reflection) and
model_mechanisms (semicolon-separated mechanisms of the record's live family 1
findings: the code, or "code | label" for a general mechanism, one key per
label). Rows marked completed_primary 0 do not enter N.

Order (AMD-002): the random audit is drawn first; then revision or non-release
proposals, unresolved findings and retracted model findings are added; then each
recurring mechanism (two or more records) not already covered gets one of its
records, drawn with SEED_MECHANISM_DRAW, mechanisms taken in ascending order of
record count, then code, then label. Outputs, including identifiers and
selection flags, are administrative files in the git-ignored restricted
directory, never REDCap imports.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
SEED_ADJUDICATION_AUDIT = 20260715
SEED_SECONDARY_QUEUE = 20260924  # separate implementation seed; not preregistered
SEED_MECHANISM_DRAW = 20261019  # fixed in AMD-002
GENERATOR_VERSION = "secondary-audit-2.0 (AMD-002)"
REQUIRED = ("source_record_id", "completed_primary", "unresolved_finding",
            "retracted_model_finding", "release_implications", "model_mechanisms")
FLAGS = ("completed_primary", "unresolved_finding", "retracted_model_finding")
MECHANISM_KEY = re.compile(r"^(\d+)(?: \| (?!\(labels not recorded\))(\S.*))?$")
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
        for field in FLAGS:
            if row[field] not in {"0", "1"}:
                raise ValueError(f"manifest {field} must be 0 or 1")
        if not all(MECHANISM_KEY.match(m) for m in mechanisms(row)):
            raise ValueError("manifest model_mechanisms must be codes, or 'code | label' with a label recorded")
        release = {s.strip().lower() for s in row["release_implications"].split(";") if s.strip()}
        if release - MANDATORY_RELEASE - RELEASE_ALIASES.keys() - NONMANDATORY_RELEASE:
            raise ValueError("manifest contains an unknown release implication")
    return rows


def mechanisms(row):
    return {m.strip() for m in row["model_mechanisms"].split(";") if m.strip()}


def mechanism_order(key, count):
    code, label = MECHANISM_KEY.match(key).groups()
    return count, int(code), label or ""


def draw(rows, audit_seed=SEED_ADJUDICATION_AUDIT, queue_seed=SEED_SECONDARY_QUEUE,
         mechanism_seed=SEED_MECHANISM_DRAW):
    """Return stable universe, random IDs, mandatory IDs, interleaved rows, and mechanism coverage."""
    universe = sorted((r for r in rows if r["completed_primary"] == "1"),
                      key=lambda r: r["source_record_id"])
    ordered_ids = [r["source_record_id"] for r in universe]
    random_count = math.ceil(0.20 * len(universe))
    random_ids = set(random.Random(audit_seed).sample(ordered_ids, random_count))
    mandatory_ids = set()
    for row in universe:
        release = {RELEASE_ALIASES.get(s.strip().lower(), s.strip().lower())
                   for s in row["release_implications"].split(";") if s.strip()}
        if row["unresolved_finding"] == "1" or row["retracted_model_finding"] == "1" or release & MANDATORY_RELEASE:
            mandatory_ids.add(row["source_record_id"])
    carriers = {}
    for row in universe:
        for key in mechanisms(row):
            carriers.setdefault(key, []).append(row["source_record_id"])
    recurring = sorted((k for k, ids in carriers.items() if len(ids) >= 2),
                       key=lambda k: mechanism_order(k, len(carriers[k])))
    mechanism_rng = random.Random(mechanism_seed)
    coverage = []
    for key in recurring:
        ids = sorted(carriers[key])
        covered = [rid for rid in ids if rid in random_ids or rid in mandatory_ids]
        chosen = covered[0] if covered else mechanism_rng.choice(ids)
        if not covered:
            mandatory_ids.add(chosen)
        coverage.append({"mechanism": key, "records": len(ids), "covered_by": chosen, "drawn": not covered})
    combined = sorted(random_ids | mandatory_ids)
    random.Random(queue_seed).shuffle(combined)
    result = [{"source_record_id": rid, "random_draw": int(rid in random_ids),
               "mandatory_review": int(rid in mandatory_ids), "queue_position": n}
              for n, rid in enumerate(combined, 1)]
    return ordered_ids, random_ids, mandatory_ids, result, coverage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True,
                        help="existing restricted manifest with completed-primary status and mandatory-review flags")
    args = parser.parse_args(argv)
    if not args.manifest.resolve().is_relative_to(OUT.resolve()):
        parser.error("input manifest must be inside preregistration_restricted")
    rows = read_manifest(args.manifest)
    universe, random_ids, mandatory_ids, selected, coverage = draw(rows)
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, text=True).strip()
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "input_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
               "stable_input_order": universe, "selected_universe": sorted(random_ids | mandatory_ids),
               "selection_algorithm": ("stable source_record_id sort; Python random.Random.sample without replacement; "
                                       "then AMD-002 items 1 to 3; then, for each recurring mechanism in ascending order of "
                                       "record count, code and label, the first already-selected carrier, else "
                                       "random.Random(mechanism_seed).choice over its sorted carriers"),
               "queue_algorithm": "sort selected IDs, then independent Python random.Random.shuffle",
               "library": "Python standard-library random (Mersenne Twister)",
               "library_version": platform.python_version(), "generator_version": GENERATOR_VERSION,
               "generator_commit": commit, "audit_seed": SEED_ADJUDICATION_AUDIT,
               "queue_seed": SEED_SECONDARY_QUEUE, "mechanism_seed": SEED_MECHANISM_DRAW,
               "mechanism_coverage": coverage, "N_completed_primary": len(universe),
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
                      "mandatory_count": len(mandatory_ids), "recurring_mechanisms": len(coverage),
                      "mechanism_draws": sum(c["drawn"] for c in coverage), "combined_count": len(selected)}, indent=2))


if __name__ == "__main__":
    main()
