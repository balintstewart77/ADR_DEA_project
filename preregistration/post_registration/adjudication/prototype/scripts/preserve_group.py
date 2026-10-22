"""Preserve a whole round's blind Stage 1 answers in one pass, then verify its reveal file.

For rounds where every Stage 1 is completed before any reveal, and records may
belong to more than one reviewer group: the secondary adjudicator's blind
training round (ADJ-104, Session 2), and later the formal secondary review.
From one raw REDCap export of all instruments it runs the same checks as
``preserve_block.py`` (schema, identity, displayed fields, empty reveal,
Stage 1 validation with affirmation), with each record checked against its own
group and reviewer role.  It refuses unless every record passes, logging the
refusal; it then writes an append-only snapshot and logs its SHA-256, and
checks the reveal file against the receipt and the sources recomputed from the
original classifications.  Only then does it say the reveal may be imported.

Printed output names records and problems, never an answer, a
classification or a source.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from build_formal_import import SEED_PRESENTATION
from preserve_block import LOG_COLUMNS, check_block, log_refusal, sha256_bytes, snapshot
from prototype_lib import package_case, reveal_fields

REPO = Path(__file__).resolve().parents[5]
TRAINING = REPO / "preregistration_restricted/adjudication_secondary_training"


def _verified(folder, receipt_files, name):
    data = (folder / name).read_bytes()
    if sha256_bytes(data) != receipt_files.get(name):
        raise SystemExit(f"{name} does not match the receipt")
    return data


def load_training_blind():
    """The blind training round: the secondary's 12 and the primary's 6 (ADJ-104), rebuilt and hash-checked."""
    from build_secondary_training import pilot_cases, shared_pool, single_set_cases
    receipt = json.loads((TRAINING / "training_receipt.json").read_text(encoding="utf-8"))["files"]
    imports = _verified(TRAINING, receipt, "blind_record_import.csv")
    reveal_bytes = _verified(TRAINING, receipt, "blind_reveal_import.csv")
    key = _verified(TRAINING, receipt, "training_crosswalk_KEY.csv")
    imported = {r["adj_assignment_id"]: r for r in csv.DictReader(imports.decode("utf-8-sig").splitlines(keepends=True))}
    members = [r for r in csv.DictReader(key.decode("utf-8").splitlines(keepends=True)) if r["adj_assignment_id"] in imported]
    if {m["adj_assignment_id"] for m in members} != set(imported):
        raise SystemExit("the crosswalk and the blind import do not cover the same records")
    cases = {**{c["record_id"]: c for c in pilot_cases()}, **shared_pool(), **single_set_cases()}
    packages, expected, sources, assignments = {}, {}, {}, {}
    for m in members:
        aid, row = m["adj_assignment_id"], imported[m["adj_assignment_id"]]
        case = {**cases[m["source_record_id"]], "assignment_id": aid}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["package_id"] != row["adj_stage1_package_id"]:
            raise SystemExit(f"{aid}: rebuilt package differs from the import")
        packages[aid], expected[aid], sources[aid] = package, reveal_fields(case, package), m["source_record_id"]
        assignments[aid] = (row["redcap_data_access_group"], row["adj_reviewer_role"])
    return TRAINING, "blind_reveal_import.csv", reveal_bytes, packages, expected, sources, assignments


SETS = {"training-blind": load_training_blind}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=sorted(SETS), required=True)
    parser.add_argument("--export", type=Path, required=True, help="raw CSV export of all instruments, inside the set's restricted folder")
    args = parser.parse_args(argv)
    folder, name, reveal_bytes, packages, expected, sources, assignments = SETS[args.set]()
    if not args.export.resolve().is_relative_to(folder.resolve()):
        parser.error(f"the export must be saved inside {folder}")
    preserved = folder / "preservation"
    snap_path = preserved / f"{args.set}_stage1_snapshot.json"
    if snap_path.exists():
        raise SystemExit(f"{args.set} is already preserved; snapshots are never overwritten")

    export_bytes = args.export.read_bytes()
    reader = csv.DictReader(export_bytes.decode("utf-8-sig").splitlines(keepends=True))
    export_rows = {r["adj_assignment_id"]: r for r in reader if r.get("adj_assignment_id") in packages}
    reveal_rows = list(csv.DictReader(reveal_bytes.decode("utf-8-sig").splitlines(keepends=True)))
    problems = check_block(reader.fieldnames or [], export_rows, sources, packages, reveal_rows, expected, assignments=assignments)
    if problems:
        log_refusal(preserved / "refusal_log.csv", args.set, args.export.name, export_bytes, problems)
        raise SystemExit("Not preserved; do not import the reveal. Correct these in Stage 1, re-export and rerun:\n" + "\n".join(problems))

    body = snapshot(export_rows, packages)
    preserved.mkdir(parents=True, exist_ok=True)
    snap_path.write_bytes(body)
    entry = {"block": args.set, "preserved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "records": len(export_rows), "snapshot_sha256": sha256_bytes(body),
             "export_sha256": sha256_bytes(export_bytes), "reveal_file_sha256": sha256_bytes(reveal_bytes)}
    log = preserved / "preservation_log.csv"
    new = not log.exists()
    with log.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if new: w.writeheader()
        w.writerow(entry)
    groups = sorted({g for g, _ in assignments.values()})
    print(f"{args.set}: {len(export_rows)} records ({', '.join(groups)}) validated and preserved, "
          f"snapshot {entry['snapshot_sha256'][:12]}; reveal verified against the original classifications.\n"
          f"Import {name} now.")


if __name__ == "__main__":
    main()
