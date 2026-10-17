"""Build the owner-evidence addendum pack for route-1 records also in route 2 (ADJ-106).

These records were adjudicated before owner responses existed, so their Stage 2
never saw owner evidence.  For each, the pack shows the entry and the revealed
options, the primary's preserved Stage 1 answers and recorded Stage 2
findings, and links the owner-evidence sheet.  The primary then records, in the
decisions template, either no change or each additional finding.  Nothing in
REDCap or in a preserved snapshot is edited.

Writes only to ``preregistration_restricted/adjudication_formal/route2/overlap_addendum/``.
Prints counts only.  Refuses to overwrite.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from build_formal_import import OUT, ROOT
from build_review_24_44 import EXPORT, EXPORT_SHA256, conflict_fields
from build_route2_import import ROUTE2, route2_cases
from preserve_block import _choices, field_rows, flat

DEST = ROUTE2 / "overlap_addendum"
COMPONENTS = (("dom", "Research Domains"), ("purp", "Analytical Purposes"), ("covid", "COVID-19 tag"), ("equity", "Equity tag"))


def choices():
    return {r[0]: dict(_choices(r[5])) for r in field_rows() if r[5].strip()}


def main():
    if DEST.exists() and any(DEST.iterdir()):
        raise SystemExit("the addendum pack already exists")
    data = EXPORT.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPORT_SHA256:
        raise SystemExit("the final export does not match its recorded hash")
    export = {r["adj_assignment_id"]: r for r in csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True))}
    imported = {r["adj_assignment_id"]: r for r in csv.DictReader((OUT / "adjudication_record_import_formal_primary.csv").open(encoding="utf-8"))}
    crosswalk = {r["source_record_id"]: r for r in csv.DictReader((OUT / "adjudication_formal_crosswalk.csv").open(encoding="utf-8"))}
    harmonised = {}
    for h in csv.DictReader((OUT / "preservation" / "mechanism_harmonisation.csv").open(encoding="utf-8")):
        harmonised[(h["assignment_id"], h["finding"])] = h["harmonised_code"]
    mech_names = {r["code"]: r["name"] for r in csv.DictReader((ROOT / "instruments" / "mechanism_vocabulary.csv").open(encoding="utf-8"))}
    ch = choices()
    _, overlap, _ = route2_cases()
    DEST.mkdir(parents=True, exist_ok=True)
    template = []
    for rid in overlap:
        cw = crosswalk[rid]
        aid, block = cw["adj_assignment_id"], int(cw["block"])
        imp, row = imported[aid], export[aid]
        reveal = {r["adj_assignment_id"]: r for r in csv.DictReader((OUT / "reveal" / f"adjudication_reveal_formal_block_{block:02d}.csv").open(encoding="utf-8"))}[aid]
        snap = json.loads((OUT / "preservation" / f"block_{block:02d}_stage1_snapshot.json").read_text(encoding="utf-8"))[aid]
        resp, cols = snap["response"], snap["stage1_columns"]
        letters = lambda codes: ", ".join("Cannot determine" if str(c) == "6" else ("None" if str(c) == "0" else chr(64 + int(c))) for c in codes) or "-"
        out = [f"# Owner-evidence addendum: {aid}", "",
               f"Block {block}. Owner sheet(s): " + ", ".join(f"`../owner_evidence/{p.name}`" for p in sorted((ROUTE2 / "owner_evidence").glob(f"{aid}_*.md"))), "",
               f"**Title:** {flat(imp['adj_case_title'])}", "", f"**Datasets:** {flat(imp['adj_case_datasets'])}", "",
               "## Options as shown, with the revealed sources", ""]
        for c, name in COMPONENTS:
            opts = [(L, imp.get(f"adj_{c}_opt_{L}", "")) for L in "abcd" if imp.get(f"adj_{c}_opt_{L}", "")]
            differs = imp.get(f"adj_{c}_comparative") == "1"
            out.append(f"**{name}**{' (differs)' if differs else ''}")
            for L, o in opts:
                out.append(f"* {L.upper()}: {flat(o)} (from {flat(reveal.get(f'adj_reveal_{c}_{L}_src', ''))})")
            if differs:
                ev = ch.get(f"adj_{c}_evidence", {}).get(str(resp.get(f"adj_{c}_evidence", "")), "-")
                out.append(f"* Your Stage 1: information {ev.lower()}; best supported {letters(resp.get(f'adj_{c}_best', []))}; "
                           f"defensible {letters(resp.get(f'adj_{c}_defensible', []))}")
            out.append("")
        out += ["## Your Stage 1 rule conflicts and boundary", ""]
        if str(resp.get("adj_rule_conflict", "")) == "1":
            rules = ch.get("adj_conflict_rule_cited", {})
            for n in range(1, 7):
                f = conflict_fields(n)
                if cols.get(f["rule"]):
                    out.append(f"* Conflict {n}: {rules.get(cols[f['rule']], cols[f['rule']])}. {flat(cols.get(f['note'], ''))}")
        else:
            out.append("* No rule conflict recorded.")
        bnd = [ch.get("adj_boundary", {}).get(k.rsplit("___", 1)[1], "") for k, v in cols.items() if k.startswith("adj_boundary___") and v == "1"]
        out.append(f"* Boundary: {'; '.join(bnd) or '-'}")
        if flat(cols.get("adj_stage1_note", "")):
            out.append(f"* Stage 1 note: {flat(cols['adj_stage1_note'])}")
        out += ["", "## Your Stage 2 findings", ""]
        for k in range(1, 7):
            fam = row.get(f"adj_f{k}_family", "")
            if not fam:
                continue
            code = harmonised.get((aid, str(k)), row.get(f"adj_f{k}_mech", ""))
            coders = [f"C0{x}" for x in "123" if row.get(f"adj_f{k}_coders___{x}") == "1"]
            labels = [lbl for comp in ("dom", "purp") for c, lbl in ch.get(f"adj_f1_{comp}_labels", {}).items() if row.get(f"adj_f{k}_{comp}_labels___{c}") == "1"]
            out.append(f"* **Finding {k}:** {ch['adj_f1_family'].get(fam, fam)}" + (f"; coders {', '.join(coders)}" if coders else "")
                       + (f"; mechanism {code} {mech_names.get(code, '')}" if code else "") + (f"; labels {', '.join(labels)}" if labels else "")
                       + f"; release {ch.get('adj_f1_release', {}).get(row.get(f'adj_f{k}_release', ''), '-')}.")
            for field in ("note", "comment"):
                if flat(row.get(f"adj_f{k}_{field}", "")):
                    out.append(f"  * {field}: {flat(row[f'adj_f{k}_{field}'])}")
        out += ["", "## Your decision", "",
                "Read the owner sheet, then record in `overlap_addendum_decisions.csv` either **no change**, or each "
                "**additional finding** (family, coders if any, mechanism, labels, release, note). Your Stage 1 and the "
                "findings above stand as recorded; the addendum adds to them."]
        (DEST / f"{aid}_addendum_pack.md").write_text("\n".join(out) + "\n", encoding="utf-8")
        template.append({"adj_assignment_id": aid, "source_record_id": rid, "decision": "", "family": "", "coders": "",
                         "mechanism_code": "", "labels": "", "release": "", "note": ""})
    with (DEST / "overlap_addendum_decisions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(template[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(template)
    print(f"{len(template)} addendum packs written; decisions template has one row per record (add rows for further findings)")


if __name__ == "__main__":
    main()
