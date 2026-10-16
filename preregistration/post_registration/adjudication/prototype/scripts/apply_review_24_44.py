"""Apply the blind 24/44 review decisions to the harmonisation file (ADJ-091, ADJ-101).

Reads the completed review CSV and its key, checks that every row carries 24
or 44 and that nothing but the decision and comment columns was edited, then
appends one row per reviewed finding to
``preservation/mechanism_harmonisation.csv``.  For a finding that already has a
harmonisation row (24 typed and harmonised, ADJ-092), the new row supersedes it:
the latest row for an assignment and finding is the one the analysis uses.
REDCap is never edited.

Prints counts only: the review outcome, and the 24 and 44 totals over the whole
primary pass before and after the recode.  Refuses to run twice.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter

from build_formal_import import OUT
from build_review_24_44 import EXPORT, EXPORT_SHA256, SLOTS

REVIEW = OUT / "review_24_44"
SHEET, KEY, XLSX = REVIEW / "review_sheet_24_44_v2.csv", REVIEW / "review_sheet_24_44_key_v2.csv", REVIEW / "review_sheet_24_44_v2.xlsx"
HARMONISATION = OUT / "preservation" / "mechanism_harmonisation.csv"
APPLIED_ON = "2026-10-16"
VOCABULARY = {"24": "mechvocab-0.1", "44": "mechvocab-0.5"}
TAG = "ADJ-091 blind review"


def totals(export_rows, harmonised):
    """Findings coded 24 and 44 over the pass: the latest harmonisation row wins, otherwise the picked code."""
    out = Counter()
    for aid, row in export_rows.items():
        for k in SLOTS:
            code = harmonised.get((aid, k), row.get(f"adj_f{k}_mech", ""))
            if code in ("24", "44"):
                out[code] += 1
    return out


def read_harmonisation():
    latest = {}
    for h in csv.DictReader(HARMONISATION.open(encoding="utf-8")):
        latest[(h["assignment_id"], int(h["finding"]))] = h["harmonised_code"]
    return latest


def main():
    if TAG in HARMONISATION.read_text(encoding="utf-8"):
        raise SystemExit("the review decisions are already applied")
    data = EXPORT.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPORT_SHA256:
        raise SystemExit("the final export does not match its recorded hash")
    export_rows = {r["adj_assignment_id"]: r for r in csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True))}
    decisions = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    key = {r["review_id"]: r for r in csv.DictReader(KEY.open(encoding="utf-8"))}
    if {d["review_id"] for d in decisions} != set(key) or len(decisions) != len(key):
        raise SystemExit("the review rows do not match the key")
    bad = [d["review_id"] for d in decisions if d["decision"].strip() not in ("24", "44")]
    if bad:
        raise SystemExit("rows without a 24 or 44 decision: " + ", ".join(bad))

    # Nothing but the decision and comment may have been edited.
    from openpyxl import load_workbook
    ws = load_workbook(XLSX).active
    hdr = [c.value for c in ws[3]]
    flat = lambda v: " // ".join(p.strip() for p in str(v or "").split("\n") if p.strip())
    built = {r[0].value: [flat(c.value) for c in r] for r in ws.iter_rows(min_row=4)}
    cols = {"title": "title", "datasets": "datasets", "labels_concerned": "labels concerned (finding)",
            "linked_stage1_conflicts": "linked Stage 1 conflicts (blind)", "basis_note": "basis note", "optional_note": "optional note"}
    edited = [d["review_id"] for d in decisions if any(d[c] != built[d["review_id"]][hdr.index(h)] for c, h in cols.items())]
    if edited:
        raise SystemExit("content other than the decision was edited in: " + ", ".join(edited))

    before = totals(export_rows, read_harmonisation())
    fields = next(csv.reader(HARMONISATION.open(encoding="utf-8")))
    with HARMONISATION.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        for d in sorted(decisions, key=lambda d: (key[d["review_id"]]["assignment_id"], int(key[d["review_id"]]["finding"]))):
            k = key[d["review_id"]]
            code = d["decision"].strip()
            note = f"{TAG} {d['review_id']}: " + ("24 kept" if code == "24" else "recoded 24 to 44")
            if k["recorded_as"] == "harmonised":
                note += "; supersedes the ADJ-092 row for this finding"
            if d["comment"].strip():
                note += "; reviewer comment on file in the review sheet"
            w.writerow({"assignment_id": k["assignment_id"], "finding": k["finding"], "typed_name": "",
                        "harmonised_code": code, "vocabulary": VOCABULARY[code], "harmonised_on": APPLIED_ON, "note": note})
    after = totals(export_rows, read_harmonisation())
    outcome = Counter(d["decision"].strip() for d in decisions)
    print(f"reviewed {len(decisions)}: {outcome['24']} kept as 24, {outcome['44']} recoded to 44")
    print(f"whole primary pass, before: 24 = {before['24']}, 44 = {before['44']}; after: 24 = {after['24']}, 44 = {after['44']}")
    print("sheet SHA-256", hashlib.sha256(SHEET.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
