"""Preserve a block's blind Stage 1 answers and verify its reveal before import.

Run between affirming a block's Stage 1 and importing its reveal file
(build spec, preservation and reveal; ADJ-071).  From a raw REDCap export it:

1. refuses unless every record in the block is affirmed, with the difference
   summary confirmed, and no reveal field yet carries a value;
2. checks that what REDCap holds as displayed (package ID, options, candidate
   maps, counts, public entry) is exactly what the generator imported;
3. writes an append-only snapshot of the block's Stage 1 and admin fields and
   logs its SHA-256, refusing to overwrite an earlier one;
4. checks the block's reveal file against the receipt hash and against the
   source mapping recomputed from the original classifications for the
   preserved package, so a wrong or edited reveal file cannot be imported.

Only then does it say the reveal may be imported.  Printed output names the
block, counts and hashes: never an answer, a classification or a source.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from build_formal_import import OUT, SEED_PRESENTATION
from build_route1_component import formal_cases, input_hashes
from prototype_lib import field_rows, generated_evidence, package_case, reveal_columns, reveal_fields

PRESERVED = OUT / "preservation"
LOG_COLUMNS = ("block", "preserved_at_utc", "records", "snapshot_sha256", "export_sha256", "reveal_file_sha256")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def norm(value):
    """REDCap may return a stored newline as CRLF and trim trailing space."""
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def stage1_columns(export_columns):
    """Export columns belonging to the admin and Stage 1 forms, checkbox codes included."""
    fields = {r[0] for r in field_rows() if r[1] in ("adj_admin", "adj_stage1") and r[3] != "descriptive"}
    return sorted(c for c in export_columns
                  if c.split("___")[0] in fields or c in ("adj_admin_complete", "adj_stage1_complete"))


def check_block(export_rows, packages, reveal_rows, expected_reveal):
    """Problems preventing preservation or reveal; an empty list means go.

    export_rows: assignment ID -> raw export row.  packages: assignment ID ->
    package rebuilt from the original classifications.  reveal_rows: the
    block's reveal file rows.  expected_reveal: assignment ID -> reveal fields
    recomputed for that package.
    """
    out = []
    for aid, package in packages.items():
        row = export_rows.get(aid)
        if row is None:
            out.append(f"{aid}: absent from the export"); continue
        if row.get("adj_stage1_affirmed") != "1": out.append(f"{aid}: Stage 1 not affirmed")
        if row.get("adj_diff_check") != "1": out.append(f"{aid}: difference summary not confirmed correct")
        if "adj_reveal_state" not in row:
            out.append(f"{aid}: export lacks the Stage 2 form, so the pre-reveal state cannot be shown")
        elif any(norm(row.get(c)) for c in ["adj_reveal_state"] + reveal_columns()):
            out.append(f"{aid}: a reveal field already holds a value")
        if norm(row.get("adj_stage1_package_id")) != package["package_id"]:
            out.append(f"{aid}: package ID differs from the package rebuilt from the original classifications")
        for field, value in generated_evidence(package).items():
            if norm(row.get(field)) != norm(str(value)):
                out.append(f"{aid}: displayed field {field} differs from what was generated")
    by_id = {r["adj_assignment_id"]: r for r in reveal_rows}
    if set(by_id) != set(packages):
        out.append("reveal file does not cover exactly this block")
    for aid, expected in expected_reveal.items():
        got = by_id.get(aid, {})
        if got.get("adj_reveal_state") != "1" or any(norm(got.get(c)) != norm(v) for c, v in expected.items()):
            out.append(f"{aid}: reveal file does not match the sources recomputed for the preserved package")
    return out


def snapshot(export_rows, columns):
    """Canonical bytes of the block's Stage 1: sorted records, sorted fields."""
    body = {aid: {c: row.get(c, "") for c in columns} for aid, row in sorted(export_rows.items())}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, required=True, help="raw CSV export of all instruments, inside the restricted folder")
    parser.add_argument("--block", type=int, required=True)
    args = parser.parse_args(argv)
    if not args.export.resolve().is_relative_to(OUT.resolve()):
        parser.error("the export must be saved inside preregistration_restricted/adjudication_formal")

    receipt = json.loads((OUT / "formal_import_receipt.json").read_text(encoding="utf-8"))
    crosswalk_path = OUT / "adjudication_formal_crosswalk.csv"
    if sha256_bytes(crosswalk_path.read_bytes()) != receipt["crosswalk_sha256"]:
        raise SystemExit("the crosswalk does not match the receipt")
    name = f"adjudication_reveal_formal_block_{args.block:02d}.csv"
    reveal_path = OUT / "reveal" / name
    reveal_bytes = reveal_path.read_bytes()
    if sha256_bytes(reveal_bytes) != receipt["reveal_files"].get(name):
        raise SystemExit(f"{name} does not match the receipt")
    snap_path = PRESERVED / f"block_{args.block:02d}_stage1_snapshot.json"
    if snap_path.exists():
        raise SystemExit(f"block {args.block} is already preserved; snapshots are never overwritten")

    members = [r for r in csv.DictReader(crosswalk_path.open(encoding="utf-8")) if r["block"] == str(args.block)]
    if not members:
        raise SystemExit(f"no block {args.block}")
    input_hashes()
    cases = {c["record_id"]: c for c in formal_cases()}
    packages, expected = {}, {}
    for m in members:
        case = {**cases[m["source_record_id"]], "assignment_id": m["adj_assignment_id"]}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["package_id"] != m["adj_stage1_package_id"]:
            raise SystemExit(f"{m['adj_assignment_id']}: rebuilt package differs from the crosswalk")
        packages[m["adj_assignment_id"]] = package
        expected[m["adj_assignment_id"]] = reveal_fields(case, package)

    export_bytes = args.export.read_bytes()
    reader = csv.DictReader(export_bytes.decode("utf-8-sig").splitlines(keepends=True))
    export_rows = {r["adj_assignment_id"]: r for r in reader if r.get("adj_assignment_id") in packages}
    reveal_rows = list(csv.DictReader(reveal_bytes.decode("utf-8").splitlines(keepends=True)))
    problems = check_block(export_rows, packages, reveal_rows, expected)
    if problems:
        raise SystemExit("Not preserved; do not import the reveal.\n" + "\n".join(problems))

    body = snapshot(export_rows, stage1_columns(reader.fieldnames))
    PRESERVED.mkdir(parents=True, exist_ok=True)
    snap_path.write_bytes(body)
    entry = {"block": args.block, "preserved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "records": len(export_rows), "snapshot_sha256": sha256_bytes(body),
             "export_sha256": sha256_bytes(export_bytes), "reveal_file_sha256": sha256_bytes(reveal_bytes)}
    log = PRESERVED / "preservation_log.csv"
    new = not log.exists()
    with log.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        if new: w.writeheader()
        w.writerow(entry)
    print(f"Block {args.block:02d}: {len(export_rows)} records affirmed and preserved, "
          f"snapshot {entry['snapshot_sha256'][:12]}; reveal verified against the original classifications.\n"
          f"Import reveal/{name} now.")


if __name__ == "__main__":
    main()
