"""Reconstruct refused attempts and block timings from the saved exports.

Answers two findings of the 2026-09-30 audit (ADJ-095): refusals before
refusal logging existed left no record, and manual timing stopped after block
4.  Both are rebuilt from contemporaneous files only, the saved exports and
the preservation log, and nothing is inferred beyond what they show.

* **Refusals.**  For each block, every saved export taken before the one it
  was preserved from, in which all the block's records have Stage 1 affirmed,
  was a preservation attempt.  ``check_block`` is re-run on each; those it
  refuses are appended to ``preservation/refusal_log.csv`` as backfilled.
  Exports without the block affirmed (for example the previous block's Stage 2
  export) are not attempts and are skipped.
* **Timings.**  Times come from the export file names, which REDCap stamps to
  the minute in local time.  Per block: the first attempt, the preserved
  export, and the first later export in which every record has the reveal
  imported and Stage 2 affirmed.  Stage 1 is measured from the end of the
  previous piece of work (the latest Stage 2 completion before the first
  attempt, same day only), so it includes any pause between blocks; intervals
  over two hours are flagged.  Written to ``block_intervals_derived.csv``.

Both outputs are restricted.  Printed output is block numbers, times and
counts, never an answer.  Refuses to run twice.
"""
from __future__ import annotations

import csv
import hashlib
import re
import statistics
from datetime import datetime
from pathlib import Path

from build_formal_import import OUT
from preserve_block import PRESERVED, REFUSALS, check_block, load_block, log_refusal

EXPORTS = OUT / "exports"
INTERVALS = OUT / "block_intervals_derived.csv"
STAMP = re.compile(r"_DATA_(\d{4}-\d{2}-\d{2})_(\d{4})")
BACKFILLED = "backfilled 2026-09-30: check_block re-run on the saved export"
LONG = 120


def exports():
    """(time, name, bytes, header, rows by assignment ID), oldest first; byte-identical copies kept once."""
    out, seen = [], set()
    for p in sorted(EXPORTS.glob("AdjudicationPRODUCTI_DATA_*.csv")):
        m = STAMP.search(p.name)
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if not m or digest in seen:
            continue
        seen.add(digest)
        reader = csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True))
        rows = {r["adj_assignment_id"]: r for r in reader}
        out.append((datetime.strptime(" ".join(m.groups()), "%Y-%m-%d %H%M"), p.name, data, reader.fieldnames or [], rows, digest))
    return sorted(out, key=lambda e: (e[0], e[1]))


def main():
    if INTERVALS.exists() or (REFUSALS.exists() and BACKFILLED in REFUSALS.read_text(encoding="utf-8")):
        raise SystemExit("already reconstructed; outputs are not overwritten")
    ledger = list(csv.DictReader((PRESERVED / "preservation_log.csv").open(encoding="utf-8")))
    saved = exports()
    by_hash = {e[5]: e for e in saved}
    blocks, refused = {}, []
    for entry in ledger:
        block = int(entry["block"])
        name, reveal_bytes, packages, expected, sources = load_block(block)
        members = sorted(packages)
        preserved = by_hash.get(entry["export_sha256"])
        if preserved is None:
            raise SystemExit(f"block {block}: the preserved export is not among the saved exports")
        reveal_rows = list(csv.DictReader(reveal_bytes.decode("utf-8").splitlines(keepends=True)))
        attempts, unused = [], 0
        for t, fname, data, header, rows, digest in saved:
            if t > preserved[0] or digest == preserved[5]:
                continue
            if not all(rows.get(a, {}).get("adj_stage1_affirmed") == "1" for a in members):
                continue
            problems = check_block(header, {a: rows[a] for a in members}, sources, packages, reveal_rows, expected)
            if problems:
                attempts.append(t)
                refused.append((block, t, fname, data, problems))
            else:
                unused += 1
        stage2 = next((e[0] for e in saved if e[0] > preserved[0] and all(
            e[4].get(a, {}).get("adj_reveal_state") == "1" and e[4].get(a, {}).get("adj_stage2_affirmed") == "1" for a in members)), None)
        blocks[block] = {"first_attempt": min(attempts + [preserved[0]]), "preserved": preserved[0], "stage2": stage2,
                         "refused": len(attempts), "unused_passing": unused, "records": len(members)}

    for block, t, fname, data, problems in sorted(refused, key=lambda r: (r[0], r[1])):
        log_refusal(REFUSALS, block, fname, data, problems, recorded=BACKFILLED)

    rows = []
    ends = sorted(b["stage2"] for b in blocks.values() if b["stage2"])
    minutes = lambda a, b: round((b - a).total_seconds() / 60) if a and b else ""
    for block, b in sorted(blocks.items()):
        before = [e for e in ends if e < b["first_attempt"] and e.date() == b["first_attempt"].date()]
        start = before[-1] if before else None
        s1, fix, s2 = minutes(start, b["first_attempt"]), minutes(b["first_attempt"], b["preserved"]), minutes(b["preserved"], b["stage2"])
        long = [n for n, v in (("stage1", s1), ("correction", fix), ("stage2", s2)) if v != "" and v > LONG]
        rows.append({"block": block, "records": b["records"],
                     "previous_work_ended": start.strftime("%Y-%m-%d %H:%M") if start else "",
                     "first_stage1_export": b["first_attempt"].strftime("%Y-%m-%d %H:%M"),
                     "preserved_export": b["preserved"].strftime("%Y-%m-%d %H:%M"),
                     "stage2_complete_export": b["stage2"].strftime("%Y-%m-%d %H:%M") if b["stage2"] else "",
                     "stage1_minutes": s1, "correction_minutes": fix, "stage2_minutes": s2,
                     "refused_attempts": b["refused"], "affirmed_passing_exports_not_used": b["unused_passing"],
                     "flag": ("over two hours, may include a break: " + ", ".join(long)) if long else
                             ("" if start else "no same-day start point; Stage 1 not timed")})
    # Blocks worked through together share one interval; say so, so it is not counted twice.
    together = {}
    for r in rows:
        together.setdefault((r["first_stage1_export"], r["stage2_complete_export"]), []).append(str(r["block"]))
    for r in rows:
        others = [b for b in together[(r["first_stage1_export"], r["stage2_complete_export"])] if b != str(r["block"])]
        if others:
            note = f"done together with block {', '.join(others)}; the intervals cover both"
            r["flag"] = f"{r['flag']}; {note}" if r["flag"] else note
    with INTERVALS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"{len(saved)} distinct exports; {len(blocks)} blocks; {len(refused)} refused attempt(s) backfilled "
          f"in blocks {sorted({r[0] for r in refused})}")
    clean = lambda k: [r[k] for r in rows if r[k] != "" and not r["flag"].startswith("over")]
    for k in ("stage1_minutes", "stage2_minutes"):
        vals = clean(k)
        print(f"{k}: {len(vals)} blocks timed without a flag, median {statistics.median(vals)} min")
    print(f"flagged or untimed: {sum(bool(r['flag']) for r in rows)} block(s)")


if __name__ == "__main__":
    main()
