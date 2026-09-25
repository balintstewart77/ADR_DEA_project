"""Preserve a block's blind Stage 1 answers and verify its reveal before import.

Run between affirming a block's Stage 1 and importing its reveal file
(build spec, preservation and reveal; ADJ-071, ADJ-073).  From a raw REDCap
export of all instruments it refuses unless:

1. the export carries every admin, Stage 1 and reveal column the dictionary
   defines, so no blind answer can be missing from the snapshot;
2. each record is the right one: source Record ID, primary role and primary
   Data Access Group match the import and crosswalk;
3. what REDCap holds as displayed (package ID, options, candidate maps, counts,
   public entry) is exactly what the generator imported;
4. no reveal field yet carries a value;
5. every response passes the Stage 1 validator, affirmation included.  Pre-
   reveal is the last point at which a wrong answer can be corrected blind.

It then writes an append-only snapshot of the block, holding each record's
full Stage 1 columns, the validated response and the derived indicators
(best outcome, multiple defensible, insufficient support), and logs its
SHA-256.  Finally it checks the block's reveal file against the receipt hash
and against the source mapping recomputed from the original classifications
for the preserved package.  Only then does it say the reveal may be imported.

Printed output names records and problems, never an answer, a
classification or a source.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from build_formal_import import GROUP, OUT, SEED_PRESENTATION
from build_route1_component import formal_cases, input_hashes
from prototype_lib import (DOMAINS, PURPOSES, derive_stage1, field_rows, generated_evidence, package_case,
                           reveal_columns, reveal_fields, validate_submission)

PRESERVED = OUT / "preservation"
LOG_COLUMNS = ("block", "preserved_at_utc", "records", "snapshot_sha256", "export_sha256", "reveal_file_sha256")
ADMIN = ("adj_assignment_id", "adj_source_record_id", "adj_reviewer_role", "adj_stage1_package_id")
REVEAL = ["adj_reveal_state"] + reveal_columns()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def norm(value):
    """REDCap may return a stored newline as CRLF and trim trailing space."""
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def flat(value):
    """A displayed field as REDCap's CSV export writes it.

    The export replaces every line break with two spaces, although the stored
    value and the form keep the break (block 1, 2026-09-24).  Only that exact
    substitution is equated; any other change to the text still differs.
    """
    return norm(value).replace("\n", "  ")


def _fields():
    return [r for r in field_rows() if r[1] in ("adj_admin", "adj_stage1") and r[3] != "descriptive"]


def _choices(choices):
    return [tuple(x.strip() for x in c.partition(",")[::2]) for c in choices.split("|") if c.strip()]


def _codes(choices):
    return [code for code, _ in _choices(choices)]


def _label_vocabulary(choices):
    """Code -> label where a checkbox offers the Domain or Purpose vocabulary.

    REDCap stores the code; the validator and the analysis name the label, as
    the prototype's responses always have.  Only these fields are decoded.
    """
    pairs = _choices(choices)
    return dict(pairs) if [label for _, label in pairs] in (list(DOMAINS), list(PURPOSES)) else None


def stage1_columns():
    """Every export column the admin and Stage 1 forms produce, checkbox codes expanded."""
    cols = []
    for r in _fields():
        cols += [f"{r[0]}___{code}" for code in _codes(r[5])] if r[3] == "checkbox" else [r[0]]
    return sorted(cols + ["adj_stage1_complete"])


def required_columns():
    return set(stage1_columns()) | set(REVEAL) | {"redcap_data_access_group"}


def response_from_export(row, generated):
    """The reviewer's answers, in the validator's shape: ints, checked codes, label names, text.

    Generated display fields and admin fields are not answers.  A blank cell
    is no answer; a checkbox with nothing ticked is absent, as in the
    prototype, so a stale hidden value is caught rather than silently kept.
    """
    out = {"assignment_id": row["adj_assignment_id"], "package_id": norm(row["adj_stage1_package_id"])}
    for r in _fields():
        name, kind = r[0], r[3]
        if name in generated or name in ADMIN:
            continue
        if kind == "checkbox":
            codes = [code for code in _codes(r[5]) if row.get(f"{name}___{code}") == "1"]
            labels = _label_vocabulary(r[5])
            ticked = [labels[code] for code in codes] if labels else [int(code) for code in codes]
            if ticked:
                out[name] = ticked
        elif norm(row.get(name)):
            value = norm(row[name])
            out[name] = int(value) if kind in ("radio", "dropdown", "yesno") else value
    return out


def check_block(columns, export_rows, sources, packages, reveal_rows, expected_reveal, post_reveal=False):
    """Problems preventing preservation or reveal; an empty list means go.

    columns: the export's header.  export_rows: assignment ID -> raw row.
    sources: assignment ID -> source Record ID from the crosswalk.  packages:
    assignment ID -> package rebuilt from the original classifications.
    reveal_rows: the block's reveal file.  expected_reveal: assignment ID ->
    reveal fields recomputed for that package.

    post_reveal: the reveal was imported before the block was preserved (a
    logged deviation, ADJ-081).  The reveal fields must then hold exactly the
    sources recomputed for the package, instead of being empty.  Nothing else
    is relaxed: the schema, identity, display and validation checks still run,
    but Stage 1 can no longer be corrected blind, so validation problems are
    returned separately, as (blocking, invalid), to be recorded rather than fixed.
    """
    missing = sorted(required_columns() - set(columns))
    if missing:
        shown = ", ".join(missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
        return [f"export lacks {len(missing)} expected column(s), e.g. {shown}: export all instruments, raw, without de-identification"]
    out, invalid = [], []
    for aid, package in packages.items():
        row = export_rows.get(aid)
        if row is None:
            out.append(f"{aid}: absent from the export"); continue
        if norm(row.get("adj_source_record_id")) != sources[aid]: out.append(f"{aid}: source Record ID differs from the crosswalk")
        if row.get("adj_reviewer_role") != "1": out.append(f"{aid}: not a primary assignment")
        if row.get("redcap_data_access_group") != GROUP: out.append(f"{aid}: not in the {GROUP} Data Access Group")
        if post_reveal:
            held = {c: norm(row.get(c)) for c in reveal_columns()}
            if row.get("adj_reveal_state") != "1" or held != {c: norm(v) for c, v in expected_reveal[aid].items()}:
                out.append(f"{aid}: the reveal REDCap holds does not match the sources recomputed for the package")
        elif any(norm(row.get(c)) for c in REVEAL):
            out.append(f"{aid}: a reveal field already holds a value")
        if norm(row.get("adj_stage1_package_id")) != package["package_id"]:
            out.append(f"{aid}: package ID differs from the package rebuilt from the original classifications")
        generated = generated_evidence(package)
        for field, value in generated.items():
            if flat(row.get(field)) != flat(str(value)):
                out.append(f"{aid}: displayed field {field} differs from what was generated")
        invalid += [f"{aid}: {p}" for p in validate_submission(response_from_export(row, generated), package)]
    by_id = {r["adj_assignment_id"]: r for r in reveal_rows}
    if set(by_id) != set(packages):
        out.append("reveal file does not cover exactly this block")
    for aid, expected in expected_reveal.items():
        got = by_id.get(aid, {})
        if got.get("adj_reveal_state") != "1" or any(norm(got.get(c)) != norm(v) for c, v in expected.items()):
            out.append(f"{aid}: reveal file does not match the sources recomputed for the preserved package")
    return (out, invalid) if post_reveal else out + invalid


def snapshot(export_rows, packages):
    """Canonical bytes: per record, every Stage 1 column, the response and its derivations."""
    columns = stage1_columns()
    body = {}
    for aid, row in sorted(export_rows.items()):
        generated = generated_evidence(packages[aid])
        response = response_from_export(row, generated)
        body[aid] = {"package_id": packages[aid]["package_id"],
                     "stage1_columns": {c: row.get(c, "") for c in columns},
                     "response": response, "derived": derive_stage1(response, packages[aid])}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, required=True, help="raw CSV export of all instruments, inside the restricted folder")
    parser.add_argument("--block", type=int, required=True)
    parser.add_argument("--post-reveal", metavar="REASON",
                        help="the reveal was already imported: preserve Stage 1 as it stands, flag the block, and say why")
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
    packages, expected, sources = {}, {}, {}
    for m in members:
        aid = m["adj_assignment_id"]
        case = {**cases[m["source_record_id"]], "assignment_id": aid}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["package_id"] != m["adj_stage1_package_id"]:
            raise SystemExit(f"{aid}: rebuilt package differs from the crosswalk")
        packages[aid], expected[aid], sources[aid] = package, reveal_fields(case, package), m["source_record_id"]

    export_bytes = args.export.read_bytes()
    reader = csv.DictReader(export_bytes.decode("utf-8-sig").splitlines(keepends=True))
    export_rows = {r["adj_assignment_id"]: r for r in reader if r.get("adj_assignment_id") in packages}
    reveal_rows = list(csv.DictReader(reveal_bytes.decode("utf-8").splitlines(keepends=True)))
    invalid = []
    if args.post_reveal:
        problems, invalid = check_block(reader.fieldnames or [], export_rows, sources, packages, reveal_rows, expected,
                                        post_reveal=True)
        if problems:
            raise SystemExit("Not preserved:\n" + "\n".join(problems))
    else:
        problems = check_block(reader.fieldnames or [], export_rows, sources, packages, reveal_rows, expected)
        if problems:
            raise SystemExit("Not preserved; do not import the reveal. Correct these in Stage 1, re-export and rerun:\n" + "\n".join(problems))

    body = snapshot(export_rows, packages)
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
    if args.post_reveal:
        # Every post-reveal preservation is flagged, with its reason and any
        # Stage 1 answer that failed validation and now stands uncorrected.
        flags = PRESERVED / "post_reveal_blocks.csv"
        first = not flags.exists()
        with flags.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=("block", "preserved_at_utc", "reason", "uncorrected_validation_problems"))
            if first: w.writeheader()
            w.writerow({"block": args.block, "preserved_at_utc": entry["preserved_at_utc"], "reason": args.post_reveal,
                        "uncorrected_validation_problems": "; ".join(invalid)})
        print(f"Block {args.block:02d}: {len(export_rows)} records preserved AFTER the reveal and flagged, "
              f"snapshot {entry['snapshot_sha256'][:12]}; the reveal REDCap holds matches the original classifications.")
        print(("Recorded, not corrected: " + "; ".join(invalid)) if invalid else "All Stage 1 answers pass validation.")
        print("Do not change Stage 1 for this block.")
        return
    print(f"Block {args.block:02d}: {len(export_rows)} records validated and preserved, "
          f"snapshot {entry['snapshot_sha256'][:12]}; reveal verified against the original classifications.\n"
          f"Import reveal/{name} now.")


if __name__ == "__main__":
    main()
