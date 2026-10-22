"""Calibration comparison report for the secondary adjudicator's training (ADJ-104, Session 3).

Reads the preserved blind Stage 1 snapshot (``preserve_group.py --set
training-blind``) and the final export, taken after both reviewers' Stage 2.
Option letters are shuffled for each reviewer, so every answer is decoded into
the classifications that reviewer's own record displayed: the comparison is by
classification, never by letter.

* Shared cases (the calibration): the secondary's and the primary's answers
  side by side, with an agreement flag per item.
* The secondary's practice-only cases: his answers, beside the primary's
  earlier pilot adjudication of the same record where the export holds one;
  the single-set cases' instructor readings are in the worked-examples handout.

Stage 1 comes from the snapshot, Stage 2 from the export; any Stage 1 answer
that changed after preservation is flagged.  Writes
``analysis/calibration_comparison_report.md`` in the training folder (restricted)
and prints counts only.  Training answers are excluded from every formal analysis.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_review_24_44 import conflict_fields
from preserve_block import _choices, flat, stage1_columns
from preserve_group import TRAINING
from prototype_lib import DOMAINS, PURPOSES, field_rows, rule_catalogue

COMPS = {"dom": "Research Domains", "purp": "Analytical Purposes", "covid": "COVID-19 tag", "equity": "Equity tag"}
ORDINAL = {2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth"}
SLOT_SPECIAL = {"6": "Cannot determine", "0": "None", "9": "Cannot judge"}
CH = {r[0]: dict(_choices(r[5])) for r in field_rows() if r[5].strip()}
RULES = {r["code"]: r["rule_id"] for r in rule_catalogue()}


def ticked(row, field):
    return [k.rsplit("___", 1)[1] for k, v in row.items() if k.startswith(field + "___") and v == "1"]


def label(field, code):
    return CH.get(field, {}).get(str(code), str(code))


def slots(row, comp, field):
    """Ticked option codes as the classifications this record displayed under them."""
    shown = {str(n): flat(row.get(f"adj_{comp}_opt_{L}", "")) for n, L in enumerate("abcd", 1)}
    return frozenset(SLOT_SPECIAL.get(c) or shown.get(c) or f"?{c}" for c in ticked(row, field))


def rule(row, cited, other):
    code = row.get(cited, "")
    if not code:
        return ""
    name = label(cited, code)
    return f"{RULES.get(code, '')} {name}".strip() if not row.get(other) else f"{name}: {flat(row[other])}"


def conflicts(row):
    out = []
    for n in range(1, 7):
        if row.get("adj_rule_conflict" if n == 1 else f"adj_conflict_{ORDINAL[n]}") != "1":
            continue
        m, f = "" if n == 1 else str(n), conflict_fields(n)
        options = frozenset((COMPS[c], o) for c in COMPS for o in slots(row, c, f"adj_{c}_conflict{m}_slots"))
        labels = [label(f[c], x) for c in ("dom", "purp") for x in ticked(row, f[c])]
        out.append({"rule": rule(row, f["rule"], f["other"]), "options": options, "labels": labels, "note": flat(row.get(f["note"], ""))})
    return out


def stage1(row):
    s = {"components": {}, "conflicts": conflicts(row), "labels": {}, "tags": {},
         "boundary": sorted(label("adj_boundary", c) for c in ticked(row, "adj_boundary") if c != "0"),
         "unresolved": row.get("adj_stage1_unresolved") == "1", "note": flat(row.get("adj_stage1_note", ""))}
    for c in COMPS:
        if row.get(f"adj_{c}_comparative") == "1":
            s["components"][c] = {"evidence": label(f"adj_{c}_evidence", row.get(f"adj_{c}_evidence", "")),
                                  "best": slots(row, c, f"adj_{c}_best"), "defensible": slots(row, c, f"adj_{c}_defensible")}
    for c, vocab in (("dom", DOMAINS), ("purp", PURPOSES)):
        for n, lab in enumerate(vocab, 1):
            pre = f"adj_{c}_l{n:02d}_"
            if row.get(pre + "applicable") == "1":
                s["labels"][f"{COMPS[c]}: {lab}"] = (label(pre + "support", row.get(pre + "support", "")),
                                                    label(pre + "rule_conflict", row.get(pre + "rule_conflict", "")))
    for t in ("covid", "equity"):
        if row.get(f"adj_{t}_status_support"):
            s["tags"][COMPS[t]] = (label(f"adj_{t}_status_support", row[f"adj_{t}_status_support"]),
                                   label(f"adj_{t}_rule_conflict", row.get(f"adj_{t}_rule_conflict", "")))
    return s


def stage2(row):
    findings = []
    for k in range(1, 7):
        fam = row.get(f"adj_f{k}_family", "")
        if not fam:
            continue
        p = f"adj_f{k}_"
        mech = (label(p + "mech", row[p + "mech"]) if row.get(p + "mech") else
                label(p + "mech_data", row[p + "mech_data"]) if row.get(p + "mech_data") else flat(row.get(p + "mech_new", "")))
        findings.append({"family": label(p + "family", fam), "mechanism": mech,
                         "labels": [label(p + f"{c}_labels", x) for c in ("dom", "purp") for x in ticked(row, p + f"{c}_labels")],
                         "coders": [label(p + "coders", x) for x in ticked(row, p + "coders")],
                         "basis": label(p + "basis", row.get(p + "basis", "")) if row.get(p + "basis") else "",
                         "release": label(p + "release", row.get(p + "release", "")) if row.get(p + "release") else "",
                         "note": flat(row.get(p + "note", ""))})
    return {"closure": label("adj_stage2_closure", row.get("adj_stage2_closure", "")), "findings": findings}


def show(value):
    if isinstance(value, frozenset):
        return "; ".join(sorted(value)) or "-"
    return value or "-"


def mark(a, b):
    return "same" if a == b else "**differs**"


def side_by_side(a, b, names):
    """Markdown rows for two reviewers' Stage 1 and Stage 2, with agreement flags; b may be None."""
    rows = []
    def add(item, x, y):
        rows.append(f"| {item} | {show(x)} | {show(y) if b else ''} | {mark(x, y) if b else ''} |")
    s1a, s1b = a["s1"], (b or {}).get("s1", {"components": {}, "conflicts": [], "labels": {}, "tags": {}, "boundary": [], "unresolved": False})
    for c in COMPS:
        if c in s1a["components"] or c in s1b["components"]:
            ca, cb = s1a["components"].get(c, {}), s1b["components"].get(c, {})
            for key in ("evidence", "best", "defensible"):
                add(f"{COMPS[c]}: {key}", ca.get(key, ""), cb.get(key, ""))
    for name in sorted(set(s1a["labels"]) | set(s1b["labels"])):
        add(f"{name} (support; rule conflict)", " ; ".join(s1a["labels"].get(name, ())), " ; ".join(s1b["labels"].get(name, ())))
    for name in sorted(set(s1a["tags"]) | set(s1b["tags"])):
        add(f"{name} status (support; rule conflict)", " ; ".join(s1a["tags"].get(name, ())), " ; ".join(s1b["tags"].get(name, ())))
    key = lambda s: frozenset((c["rule"], c["options"]) for c in s["conflicts"])
    fmt = lambda s: frozenset(f"{c['rule']} against {'; '.join(f'{k}: {o}' for k, o in sorted(c['options'])) or 'labels ' + ', '.join(c['labels'])}"
                              for c in s["conflicts"])
    rows.append(f"| Rule conflicts | {show(fmt(s1a))} | {show(fmt(s1b)) if b else ''} | {mark(key(s1a), key(s1b)) if b else ''} |")
    add("Boundary", ", ".join(s1a["boundary"]), ", ".join(s1b["boundary"]))
    add("Unresolved at Stage 1", "yes" if s1a["unresolved"] else "no", "yes" if s1b["unresolved"] else "no")
    fa, fb = a["s2"]["findings"], (b or {}).get("s2", {"findings": []})["findings"]
    add("Stage 2 closure", a["s2"]["closure"], (b or {}).get("s2", {}).get("closure", ""))
    add("Families", frozenset(f["family"] for f in fa), frozenset(f["family"] for f in fb))
    add("Mechanisms", frozenset(f["mechanism"] for f in fa if f["mechanism"]), frozenset(f["mechanism"] for f in fb if f["mechanism"]))
    add("Release", frozenset(f"{f['family']}: {f['release']}" for f in fa if f["release"]),
        frozenset(f"{f['family']}: {f['release']}" for f in fb if f["release"]))
    head = [f"| Item | {names[0]} | {names[1] if b else ''} | Agreement |", "|---|---|---|---|"]
    return head + rows


def notes(r, who):
    out = []
    if r["s1"]["note"]:
        out.append(f"* {who}, Stage 1 note: {r['s1']['note']}")
    for c in r["s1"]["conflicts"]:
        if c["note"]:
            out.append(f"* {who}, conflict ({c['rule']}): {c['note']}")
    for f in r["s2"]["findings"]:
        detail = ", ".join(x for x in (f["basis"], "labels " + ", ".join(f["labels"]) if f["labels"] else "",
                                         "coders " + ", ".join(f["coders"]) if f["coders"] else "") if x)
        out.append(f"* {who}, {f['family']}{' (' + detail + ')' if detail else ''}: {f['note'] or '-'}")
    return out


def build(snapshot, export_rows, crosswalk):
    """The report's markdown and counts.  snapshot: aid -> preserved entry; export_rows: aid -> raw row."""
    stage1_cols = stage1_columns()
    records, changed = {}, []
    for aid, entry in snapshot.items():
        final = export_rows.get(aid, {})
        if any(flat(final.get(c, "")) != flat(entry["stage1_columns"].get(c, "")) for c in stage1_cols if c in final):
            changed.append(aid)
        records[aid] = {"s1": stage1(entry["stage1_columns"]), "s2": stage2(final),
                        "title": flat(entry["stage1_columns"].get("adj_case_title", "")),
                        "datasets": flat(entry["stage1_columns"].get("adj_case_datasets", ""))}
    by_source = {}
    for m in crosswalk:
        if m["adj_assignment_id"] in records:
            by_source.setdefault(m["source_record_id"], {})[m["group"]] = m
    shared = sorted(s for s, g in by_source.items() if {"secondary", "primary"} <= set(g))
    practice = sorted((s, g["secondary"]) for s, g in by_source.items() if set(g) == {"secondary"})

    lines = ["# Secondary adjudicator training: calibration comparison (Session 3)", "",
             "Restricted. Training answers only, excluded from every formal analysis (ADJ-104). "
             "Answers are compared by classification, not option letter.", ""]
    if changed:
        lines += [f"**Stage 1 changed after preservation on {len(changed)} record(s): {', '.join(sorted(changed))}.** "
                  "The comparison uses the preserved answers.", ""]
    summary = ["| Case | Evidence | Best supported | Defensible | Rule conflicts | Families |", "|---|---|---|---|---|---|"]
    body = []
    for n, src in enumerate(shared, 1):
        sa, pa = by_source[src]["secondary"]["adj_assignment_id"], by_source[src]["primary"]["adj_assignment_id"]
        a, b = records[sa], records[pa]
        comps = sorted(set(a["s1"]["components"]) | set(b["s1"]["components"]))
        agree = lambda key: f"{sum(a['s1']['components'].get(c, {}).get(key) == b['s1']['components'].get(c, {}).get(key) for c in comps)}/{len(comps)}"
        ck = lambda s: frozenset((c["rule"], c["options"]) for c in s["conflicts"])
        fams = lambda r: frozenset(f["family"] for f in r["s2"]["findings"])
        summary.append(f"| Shared {n} ({sa} / {pa}) | {agree('evidence')} | {agree('best')} | {agree('defensible')} | "
                       f"{mark(ck(a['s1']), ck(b['s1']))} | {mark(fams(a), fams(b))} |")
        body += [f"## Shared {n}: {sa} (secondary) and {pa} (primary)", "", f"**Title:** {a['title']}  ", f"**Datasets:** {a['datasets']}", ""]
        body += side_by_side(a, b, ("Secondary", "Primary")) + [""] + notes(a, "Secondary") + notes(b, "Primary") + [""]
    for src, m in practice:
        aid = m["adj_assignment_id"]
        a = records[aid]
        reference = next(({"s1": stage1(r), "s2": stage2(r)} for x, r in sorted(export_rows.items())
                          if x.startswith("PILOT_ADJ_") and not x.endswith("_SEC") and flat(r.get("adj_source_record_id", "")) == src), None)
        body += [f"## Practice: {aid} ({m['set_role'].split(': ')[-1]})", "", f"**Title:** {a['title']}  ", f"**Datasets:** {a['datasets']}", ""]
        body += side_by_side(a, reference, ("Secondary", "Primary's pilot adjudication")) + [""] + notes(a, "Secondary")
        if reference is None:
            body.append("* Reference reading: the instructor reading in the worked-examples handout (single set) or the pilot debrief.")
        body.append("")
    lines += ["## Summary of the shared cases", ""] + summary + [""] + body
    return "\n".join(lines) + "\n", {"shared": len(shared), "practice": len(practice), "changed_after_preservation": len(changed)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, required=True, help="raw export of all instruments taken after both reviewers' Stage 2")
    args = parser.parse_args(argv)
    if not args.export.resolve().is_relative_to(TRAINING.resolve()):
        parser.error(f"the export must be saved inside {TRAINING}")
    snapshot = json.loads((TRAINING / "preservation" / "training-blind_stage1_snapshot.json").read_text(encoding="utf-8"))
    export_rows = {r["adj_assignment_id"]: r for r in csv.DictReader(args.export.open(encoding="utf-8-sig"))}
    crosswalk = list(csv.DictReader((TRAINING / "training_crosswalk_KEY.csv").open(encoding="utf-8")))
    report, counts = build(snapshot, export_rows, crosswalk)
    out = TRAINING / "analysis" / "calibration_comparison_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"written {out.relative_to(TRAINING)}:", json.dumps(counts))


if __name__ == "__main__":
    main()
