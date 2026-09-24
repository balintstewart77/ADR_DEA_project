"""Check every preserved block against a later REDCap export.

For each block with a snapshot, reports per record whether its Stage 1
columns still equal the preserved snapshot, whether the reveal is imported, and
whether Stage 2 is affirmed.  A changed Stage 1 answer after preservation is
the thing to catch: the analysis uses the snapshot, so a later edit must go
through a clerical correction or a reflection instead.

Printed output is assignment IDs, statuses and the names of changed columns,
never an answer, a classification or a source.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_formal_import import OUT
from preserve_block import PRESERVED, stage1_columns


def compare(rows, snapshots, columns):
    """Per record: (block, assignment ID, changed Stage 1 columns, reveal state, Stage 2 affirmed)."""
    out = []
    for block, snap in sorted(snapshots.items()):
        for aid, body in sorted(snap.items()):
            row = rows.get(aid)
            if row is None:
                out.append((block, aid, ["absent from export"], "", "")); continue
            changed = [c for c in columns if row.get(c, "") != body["stage1_columns"][c]]
            out.append((block, aid, changed, row.get("adj_reveal_state", ""), row.get("adj_stage2_affirmed", "")))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.export.resolve().is_relative_to(OUT.resolve()):
        parser.error("the export must be saved inside preregistration_restricted/adjudication_formal")
    rows = {r["adj_assignment_id"]: r for r in csv.DictReader(args.export.open(encoding="utf-8-sig"))}
    snapshots = {int(p.name.split("_")[1]): json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted(PRESERVED.glob("block_*_stage1_snapshot.json"))}
    problems = 0
    for block, aid, changed, reveal, stage2 in compare(rows, snapshots, stage1_columns()):
        state = "Stage 1 unchanged" if not changed else f"STAGE 1 CHANGED since preservation: {', '.join(changed)}"
        done = "complete" if reveal == "1" and stage2 == "1" else f"reveal {reveal or '-'}, Stage 2 affirmed {stage2 or '-'}"
        problems += bool(changed)
        print(f"block {block:02d}  {aid}  {state}  |  {done}")
    print(f"{len(snapshots)} preserved block(s); {problems} record(s) with a changed Stage 1")


if __name__ == "__main__":
    main()
