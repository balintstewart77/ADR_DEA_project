"""Build the secondary adjudicator's formal review for PID 9227 from the AMD-003 draw (ADJ-119).

Three batches, each with its own record import and reveal file:

* **core:** 20 random and 17 mandatory records, already interleaved and masked
  by the draw. This is the only import loaded at the start. Every Stage 1 is
  completed and preserved (``preserve_group.py --set formal-secondary-core``)
  before its reveal is imported.
* **extension_1** and **extension_2:** reserve random records, in seeded order.
  These are imported only if the secondary adjudicator has time, after the
  core's reveal, each preserved before its own reveal (AMD-003).

The records sit in the ``secondary`` group with reviewer role 2. Assignment IDs
are SEC_0001 upwards in work order: core first, then extension 1, then
extension 2. Options are ordered by package seed and assignment ID, so the
secondary's option order is independent of the primary's. Packages are rebuilt
from the same original classifications the primary saw: scratch-coder sets for
route-1 records, and the model set alone for route-2 single-set records.

Owner evidence is never part of Stage 1 (adjudication methods 9.2). For each
selected record with a qualifying owner review, one sheet per review is written
to ``owner_evidence/``. Sheets are handed over only for Stage 2, after the
batch's Stage 1 is preserved and its reveal imported. The primary's answers,
findings and notes are not part of any file here.

Writes only to ``preregistration_restricted/adjudication_formal/secondary/``.
Prints counts only. Refuses to overwrite.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from build_formal_import import OUT, SEED_PRESENTATION
from build_route1_component import formal_cases, git_commit
from build_route2_import import owner_choices, route2_cases, sheet
from prototype_lib import (IMPORTED_DEFAULTS, IMPORT_FORBIDDEN, comparative_components, field_rows, generated_evidence,
                           package_case, reveal_fields, write_reveal_import)

REPO = Path(__file__).resolve().parents[5]
DRAW = REPO / "preregistration_restricted/adjudication_secondary_audit_draw.csv"
DRAW_SHA256 = "975056d4e63046e30e8991dbefaebd34fb46e478cc343aeb93b64e77877f11d4"  # ADJ-119
SECONDARY = OUT / "secondary"
GROUP = "secondary"
ROLE = 2
ID_PREFIX = "SEC_"
BATCHES = ("core", "extension_1", "extension_2")
FREE_TEXT = {"adj_case_title", "adj_case_datasets", "adj_source_record_id"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def draw_rows():
    data = DRAW.read_bytes()
    if sha(data) != DRAW_SHA256:
        raise SystemExit("the secondary audit draw does not match the file recorded in ADJ-119")
    rows = list(csv.DictReader(data.decode("utf-8").splitlines(keepends=True)))
    ordered = []
    for batch in BATCHES:
        ordered += sorted((r for r in rows if r["batch"] == batch), key=lambda r: int(r["queue_position"]))
    if len(ordered) != len(rows):
        raise SystemExit("the draw holds a batch this builder does not know")
    return ordered


def all_cases():
    """Original classification sets for every adjudicated record: route 1 from the formal export, route 2 as built."""
    formal = {c["record_id"]: c for c in formal_cases()}
    route2_new, _, screened = route2_cases()
    return {**formal, **route2_new}, screened


def secondary_packages():
    """(assignment ID, draw row, case, package) for every selected record, in work order."""
    cases, screened = all_cases()
    out = []
    for position, row in enumerate(draw_rows(), 1):
        rid = row["source_record_id"]
        if rid not in cases:
            raise SystemExit(f"{rid} has no original classifications; nothing written")
        aid = f"{ID_PREFIX}{position:04d}"
        case = {**cases[rid], "assignment_id": aid}
        out.append((aid, row, case, package_case(case, seed=SEED_PRESENTATION)))
    return out, screened


def main():
    if SECONDARY.exists() and any(SECONDARY.iterdir()):
        raise SystemExit("the secondary review is already built; it is never rebuilt over itself")
    built, screened = secondary_packages()
    names = [r[0] for r in field_rows()]
    by_batch = {b: [] for b in BATCHES}
    crosswalk = []
    for aid, draw_row, case, package in built:
        if package["qa_flags"]:
            raise SystemExit(f"{aid} carries QA flags; nothing written")
        row = {"adj_assignment_id": aid, "redcap_data_access_group": GROUP, "adj_source_record_id": case["record_id"],
               "adj_reviewer_role": ROLE, "adj_stage1_package_id": package["package_id"],
               **generated_evidence(package), **IMPORTED_DEFAULTS}
        for key, value in row.items():
            if key not in FREE_TEXT and any(token in str(value).lower() for token in IMPORT_FORBIDDEN):
                raise SystemExit(f"a masked row leaks a source token in {key}; nothing written")
        by_batch[draw_row["batch"]].append((row, case, package))
        crosswalk.append({"adj_assignment_id": aid, "source_record_id": case["record_id"], "batch": draw_row["batch"],
                          "random_draw": draw_row["random_draw"], "random_position": draw_row["random_position"],
                          "mandatory_review": draw_row["mandatory_review"], "adj_stage1_package_id": package["package_id"],
                          "form": "+".join(comparative_components(package)) or "single set",
                          "in_coder_sample": int(len(case["classifications"]) > 1),
                          "owner_reviewed": int(case["record_id"] in screened)})
    unknown = sorted({k for rows in by_batch.values() for r, _, _ in rows for k in r} - set(names) - {"redcap_data_access_group"})
    if unknown:
        raise SystemExit("columns absent from the dictionary: " + ", ".join(unknown))

    (SECONDARY / "reveal").mkdir(parents=True, exist_ok=True)
    (SECONDARY / "owner_evidence").mkdir(exist_ok=True)
    present = {k for rows in by_batch.values() for r, _, _ in rows for k in r}
    columns = ["adj_assignment_id", "redcap_data_access_group"] + [n for n in names if n != "adj_assignment_id" and n in present]
    files = {}
    for batch, members in by_batch.items():
        if not members:
            continue
        imp = SECONDARY / f"secondary_record_import_{batch}.csv"
        with imp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=columns, restval="")
            w.writeheader()
            w.writerows(r for r, _, _ in members)
        rev = SECONDARY / "reveal" / f"secondary_reveal_{batch}.csv"
        write_reveal_import(rev, [(case, package) for _, case, package in members])
        files[imp.name] = sha(imp.read_bytes())
        files[f"reveal/{rev.name}"] = sha(rev.read_bytes())
    key = SECONDARY / "secondary_crosswalk_KEY.csv"
    with key.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(crosswalk[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(crosswalk)
    files[key.name] = sha(key.read_bytes())

    choices, sheets = owner_choices(), 0
    for aid, _, case, _ in built:
        for review, reasons in screened.get(case["record_id"], []):
            path = SECONDARY / "owner_evidence" / f"{aid}_{review['owner_id']}.md"
            path.write_text(sheet(aid, review, reasons, choices), encoding="utf-8")
            files[f"owner_evidence/{path.name}"] = sha(path.read_bytes())
            sheets += 1

    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "decisions": ["AMD-003", "ADJ-118", "ADJ-119"], "draw_sha256": DRAW_SHA256,
               "group": GROUP, "reviewer_role": ROLE, "presentation_seed": SEED_PRESENTATION,
               "batches": {b: {"records": len(m), "first_id": m[0][0]["adj_assignment_id"] if m else None,
                               "last_id": m[-1][0]["adj_assignment_id"] if m else None} for b, m in by_batch.items()},
               "owner_evidence_sheets": sheets, "files": files, "generator_commit": git_commit()}
    (SECONDARY / "secondary_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batches": receipt["batches"], "owner_evidence_sheets": sheets}, indent=2))


def load_batch(batch):
    """For preserve_group.py: the batch's verified reveal file and the rebuilt packages, expected reveals and sources."""
    if batch not in BATCHES:
        raise SystemExit(f"unknown batch {batch}")
    receipt = json.loads((SECONDARY / "secondary_receipt.json").read_text(encoding="utf-8"))
    files = receipt["files"]

    def verified(name):
        data = (SECONDARY / name).read_bytes()
        if sha(data) != files.get(name):
            raise SystemExit(f"{name} does not match the secondary receipt")
        return data

    imports = verified(f"secondary_record_import_{batch}.csv")
    reveal_name = f"reveal/secondary_reveal_{batch}.csv"
    reveal_bytes = verified(reveal_name)
    verified("secondary_crosswalk_KEY.csv")
    imported = {r["adj_assignment_id"]: r for r in csv.DictReader(imports.decode("utf-8-sig").splitlines(keepends=True))}
    built, _ = secondary_packages()
    packages, expected, sources, assignments = {}, {}, {}, {}
    for aid, _, case, package in built:
        if aid not in imported:
            continue
        if package["package_id"] != imported[aid]["adj_stage1_package_id"]:
            raise SystemExit(f"{aid}: rebuilt package differs from the import")
        packages[aid], expected[aid], sources[aid] = package, reveal_fields(case, package), case["record_id"]
        assignments[aid] = (imported[aid]["redcap_data_access_group"], imported[aid]["adj_reviewer_role"])
    if set(packages) != set(imported):
        raise SystemExit(f"the {batch} import and the draw do not cover the same records")
    return SECONDARY, reveal_name, reveal_bytes, packages, expected, sources, assignments


if __name__ == "__main__":
    main()
