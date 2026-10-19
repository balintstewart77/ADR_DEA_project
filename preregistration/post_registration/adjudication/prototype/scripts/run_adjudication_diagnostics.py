"""Adjudication diagnostics over the completed primary pass (protocol 8.7, 9.1, 9.3).

Interim results: primary only, unaudited, routes 1 and 2 (ADJ-076, ADJ-099).
Builds one long table of findings, then the 8.7 tables from it:

* population: eligible and completed records by route and sample;
* families: records with at least one finding of each family, percentages over
  completed adjudicated records (multiple codes per record, so they may sum to
  more than 100%), and codes per record; overall and by sample;
* source-specific findings by source; mechanisms by family, general
  mechanisms split by label, and recurrence (two or more distinct records);
* release implications, and the mandatory second-review set;
* Stage 1 outcomes from the preserved snapshots: evidence, best supported,
  multiple defensible, insufficient support, rule conflicts and their rule
  groups (ADJ-079), boundaries, masking, single-set label support.

Inputs folded in: the latest harmonised mechanism per finding (ADJ-091 to
ADJ-093), the label supplement for typed general mechanisms (ADJ-111),
reflections (retracted findings and conflicts are reported and not counted,
ADJ-085), and the owner-evidence addendum (ADJ-112, counted and flagged).
Writes only to ``preregistration_restricted/adjudication_formal/analysis/``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from build_formal_import import OUT
from preserve_block import _choices, field_rows
from prototype_lib import DOMAINS, GENERAL_MECHANISM_CODES, PURPOSES, ROOT
from rule_groups import record_groups

EXPORT = OUT / "exports" / "AdjudicationPRODUCTI_DATA_2026-10-19_0942.csv"
SAMPLING = OUT.parent / "sampling" / "official_draw_20260724"
DEST = OUT / "analysis"
FAMILIES = {1: "Model rule-application problem", 2: "Coder rule-application problem", 3: "Evidence problem", 4: "Taxonomy problem",
            5: "Project-knowledge gap", 6: "Legitimate boundary case", 7: "Data or instrument problem", 8: "Unresolved"}
MANDATORY_RELEASE = {"2", "3", "5"}
COMP = {1: "dom", 2: "purp", 3: "covid", 4: "equity"}


def load():
    data = EXPORT.read_bytes()
    rows = {r["adj_assignment_id"]: r for r in csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True))}
    cw = {}
    for path, route in ((OUT / "adjudication_formal_crosswalk.csv", "1"), (OUT / "route2" / "adjudication_route2_crosswalk.csv", "2")):
        for r in csv.DictReader(path.open(encoding="utf-8")):
            cw[r["adj_assignment_id"]] = {"source": r["source_record_id"], "route": route, "block": int(r["block"]),
                                          "stratum": r.get("stratum", ""), "form": r.get("form", "")}
    sample = {}
    for name, label in (("baseline_active.csv", "baseline"), ("hard_active.csv", "hard-case")):
        for r in csv.DictReader((SAMPLING / name).open(encoding="utf-8-sig")):
            sample[r["record_id"].strip()] = label
    for aid, c in cw.items():
        c["sample"] = sample.get(c["source"], "owner-only")
    latest = {}
    for h in csv.DictReader((OUT / "preservation" / "mechanism_harmonisation.csv").open(encoding="utf-8")):
        latest[(h["assignment_id"], int(h["finding"]))] = h["harmonised_code"]
    supplement = {(s["assignment_id"], int(s["finding"])): [x.strip() for x in s["labels"].split(";") if x.strip()]
                  for s in csv.DictReader((OUT / "preservation" / "finding_label_supplement.csv").open(encoding="utf-8"))}
    retracted_findings, retracted_conflicts = set(), set()
    for ref in csv.DictReader((OUT / "preservation" / "reflections.csv").open(encoding="utf-8")):
        for m in re.finditer(r"Stage 2 finding (\d)", ref["stage1_answer"]):
            retracted_findings.add((ref["assignment_id"], int(m.group(1))))
        for m in re.finditer(r"rule conflict (\d)", ref["stage1_answer"]):
            retracted_conflicts.add((ref["assignment_id"], int(m.group(1))))
    addendum = [a for a in csv.DictReader((OUT / "route2" / "overlap_addendum" / "overlap_addendum_decisions.csv").open(encoding="utf-8"))
                if a["decision"] == "additional finding"]
    return data, rows, cw, latest, supplement, retracted_findings, retracted_conflicts, addendum


def conflict_records(resp):
    """(n, code, scope components, labels) for each conflict recorded in a preserved Stage 1 response."""
    out = []
    for n in range(1, 7):
        ask = "adj_rule_conflict" if n == 1 else {2: "adj_conflict_second", 3: "adj_conflict_third", 4: "adj_conflict_fourth",
                                                 5: "adj_conflict_fifth", 6: "adj_conflict_sixth"}[n]
        if resp.get(ask) != 1:
            continue
        m = "" if n == 1 else str(n)
        scope = [COMP[c] for c in resp.get("adj_rule_conflict_scope" if n == 1 else f"adj_conflict{n}_scope", [])]
        labels = {c: resp.get(f"adj_{c}_conflict{m}_labels", []) for c in ("dom", "purp")}
        out.append((n, resp.get(f"adj_conflict_rule{m}_cited"), scope, labels))
    return out


def inherited_labels(snap, row, k):
    """Labels a finding inherits from the Stage 1 conflicts it cites: ticked labels, else the cited rule's own label."""
    if not snap:
        return []
    labels = []
    for n, code, scope, lab in conflict_records(snap["response"]):
        if row.get(f"adj_f{k}_conflicts___{n}") != "1":
            continue
        ticked = lab.get("dom", []) + lab.get("purp", [])
        if ticked:
            labels += ticked
            continue
        for g in record_groups([(code, scope, lab)]):
            name = g.split(": ", 1)[-1]
            if name in DOMAINS or name in PURPOSES:
                labels.append(name)
    return list(dict.fromkeys(labels))


def findings_table(rows, cw, latest, supplement, retracted, addendum, ch, mech_names, snaps):
    out = []
    for aid, r in sorted(rows.items()):
        if aid not in cw:
            continue
        for k in range(1, 7):
            fam = r.get(f"adj_f{k}_family", "")
            if not fam:
                continue
            code = latest.get((aid, k), r.get(f"adj_f{k}_mech", "") or r.get(f"adj_f{k}_mech_data", ""))
            labels = [l for comp in ("dom", "purp") for c, l in ch.get(f"adj_f1_{comp}_labels", {}).items() if r.get(f"adj_f{k}_{comp}_labels___{c}") == "1"]
            labels = labels or supplement.get((aid, k), []) or inherited_labels(snaps.get(aid), r, k)
            out.append({"adj_assignment_id": aid, "source_record_id": cw[aid]["source"], "route": cw[aid]["route"], "sample": cw[aid]["sample"],
                        "finding": str(k), "family_code": int(fam), "family": FAMILIES[int(fam)],
                        "coders": ";".join(f"C0{x}" for x in "123" if r.get(f"adj_f{k}_coders___{x}") == "1"),
                        "basis": ch["adj_f1_basis"].get(r.get(f"adj_f{k}_basis", ""), ""),
                        "mechanism_code": code, "mechanism": mech_names.get(code, ""), "general": int(code in {str(c) for c in GENERAL_MECHANISM_CODES}),
                        "labels": "; ".join(labels), "release_code": r.get(f"adj_f{k}_release", ""),
                        "release": ch["adj_f1_release"].get(r.get(f"adj_f{k}_release", ""), ""),
                        "retracted": int((aid, k) in retracted), "addendum": 0})
    for n, a in enumerate(addendum, 1):
        aid = a["adj_assignment_id"]
        fam = int(a["family"].split()[0])
        code = a["mechanism_code"]
        out.append({"adj_assignment_id": aid, "source_record_id": cw[aid]["source"], "route": cw[aid]["route"], "sample": cw[aid]["sample"],
                    "finding": f"A{n}", "family_code": fam, "family": FAMILIES[fam], "coders": a["coders"], "basis": "",
                    "mechanism_code": code, "mechanism": mech_names.get(code, ""), "general": int(code in {str(c) for c in GENERAL_MECHANISM_CODES}),
                    "labels": a["labels"], "release_code": {"None": "0"}.get(a["release"], ""), "release": a["release"], "retracted": 0, "addendum": 1})
    return out


def pct(n, d):
    return f"{n} ({100 * n / d:.1f}%)" if d else "0"


def main():
    data, rows, cw, latest, supplement, retracted_f, retracted_c, addendum = load()
    ch = {r[0]: dict(_choices(r[5])) for r in field_rows() if r[5].strip()}
    mech_names = {r["code"]: r["name"] for r in csv.DictReader((ROOT / "instruments" / "mechanism_vocabulary.csv").open(encoding="utf-8"))}
    snaps = {}
    for p in sorted((OUT / "preservation").glob("block_*_stage1_snapshot.json")):
        snaps.update(json.loads(p.read_text(encoding="utf-8")))
    findings = findings_table(rows, cw, latest, supplement, retracted_f, addendum, ch, mech_names, snaps)
    live = [f for f in findings if not f["retracted"]]
    aids = sorted(cw)
    closure = {a: rows[a].get("adj_stage2_closure", "") for a in aids}
    completed = [a for a in aids if closure[a] in ("1", "2")]
    N = len(completed)

    # Population
    population = {"eligible": len(aids), "completed": N, "by_route": dict(Counter(cw[a]["route"] for a in aids)),
                  "by_sample": dict(Counter(cw[a]["sample"] for a in aids)),
                  "completed_with_findings": sum(closure[a] == "1" for a in completed),
                  "completed_with_no_assignable_issue": sum(closure[a] == "2" for a in completed),
                  "administrative_closure_or_incomplete": len(aids) - N}

    # Families
    fam_records = {fc: {f["adj_assignment_id"] for f in live if f["family_code"] == fc} for fc in FAMILIES}
    families = {FAMILIES[fc]: {"records": len(s), "percent_of_completed": round(100 * len(s) / N, 1)} for fc, s in fam_records.items()}
    per_record = Counter(len({f["family_code"] for f in live if f["adj_assignment_id"] == a}) for a in completed)
    by_sample = {}
    for smp in sorted({cw[a]["sample"] for a in completed}):
        recs = [a for a in completed if cw[a]["sample"] == smp]
        by_sample[smp] = {"completed": len(recs), **{FAMILIES[fc]: sum(a in fam_records[fc] for a in recs) for fc in FAMILIES}}

    # Source-specific findings
    source = {"Model (family 1)": len(fam_records[1])}
    for c in ("C01", "C02", "C03"):
        source[f"Coder {c} (family 2)"] = len({f["adj_assignment_id"] for f in live if f["family_code"] == 2 and c in f["coders"].split(";")})

    # Mechanisms, general ones split by label; recurrence = 2+ distinct records
    mech = defaultdict(set)
    for f in live:
        if not f["mechanism_code"]:
            continue
        key = f"{f['mechanism_code']} {f['mechanism']}"
        if f["general"]:
            for lab in [x.strip() for x in f["labels"].split(";") if x.strip()] or ["(labels not recorded)"]:
                mech[(f["family"], f"{key} | {lab}")].add(f["adj_assignment_id"])
        else:
            mech[(f["family"], key)].add(f["adj_assignment_id"])
    mechanisms = sorted(({"family": fam, "mechanism": m, "records": len(s), "recurring": len(s) >= 2} for (fam, m), s in mech.items()),
                        key=lambda x: (x["family"], -x["records"], x["mechanism"]))

    # Release and the mandatory second-review set
    release = dict(Counter(f["release"] or "(not asked)" for f in live))
    mandatory = defaultdict(set)
    for f in live:
        if f["family_code"] == 1:
            mandatory[f["adj_assignment_id"]].add("model rule-application finding")
        if f["family_code"] == 8:
            mandatory[f["adj_assignment_id"]].add("unresolved")
        if f["release_code"] in MANDATORY_RELEASE:
            mandatory[f["adj_assignment_id"]].add(f"release: {f['release']}")
    mandatory["ADJ_0167"].add("retracted model finding (ADJ-112)")

    # Stage 1 outcomes from the preserved snapshots
    evidence, best, multi, insuff = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    conflicts_per_record, masking, boundary, groups, single_support = Counter(), Counter(), Counter(), Counter(), defaultdict(Counter)
    ev_lab = ch.get("adj_dom_evidence", {})
    for aid in completed:
        s = snaps[aid]
        resp, der = s["response"], s["derived"]
        for comp in ("dom", "purp", "covid", "equity"):
            if f"adj_{comp}_evidence" in resp:
                evidence[comp][ev_lab.get(str(resp[f"adj_{comp}_evidence"]), resp[f"adj_{comp}_evidence"])] += 1
            if f"adj_{comp}_best_outcome" in der:
                best[comp][{1: "unique best", 2: "tie (subset)", 3: "all equally", 4: "cannot determine", 9: "not asked"}[der[f"adj_{comp}_best_outcome"]]] += 1
                multi[comp][der[f"adj_{comp}_multiple_defensible"]] += 1
                insuff[comp][{0: "no", 1: "yes", 9: "cannot judge"}[der[f"adj_{comp}_insufficient_support"]]] += 1
        recorded = [(code, scope, lab) for n, code, scope, lab in conflict_records(resp) if (aid, n) not in retracted_c]
        conflicts_per_record[len(recorded)] += 1
        for g in record_groups(recorded):
            groups[g] += 1
        masking[{1: "yes", 0: "no", 2: "unsure"}.get(resp.get("adj_masking_failure"), "missing")] += 1
        for b in resp.get("adj_boundary", []):
            boundary[ch.get("adj_boundary", {}).get(str(b), b)] += 1
        for comp, labs in resp.get("label_assessments", {}).items():
            for _, a in labs.items():
                single_support[comp][{1: "supported", 2: "not supported", 3: "cannot determine"}.get(a.get("support"), "?")] += 1
        for comp, a in resp.get("tag_assessments", {}).items():
            single_support[comp][{1: "supported", 2: "not supported", 3: "cannot determine"}.get(a.get("support"), "?")] += 1

    results = {"status": "INTERIM: primary only, unaudited, routes 1 and 2 (ADJ-076, ADJ-099); retracted findings and conflicts not counted (ADJ-085); owner-evidence addendum findings counted and flagged (ADJ-112)",
               "export_sha256": hashlib.sha256(data).hexdigest(), "population": population,
               "families": families, "families_per_record": dict(sorted(per_record.items())), "families_by_sample": by_sample,
               "source_specific_records": source, "findings": {"total": len(findings), "retracted": len(findings) - len(live),
                                                               "addendum": sum(f["addendum"] for f in live)},
               "mechanisms": mechanisms, "release_implications": release,
               "mandatory_second_review_records": len(mandatory),
               "stage1": {"evidence": {k: dict(v) for k, v in evidence.items()}, "best_supported": {k: dict(v) for k, v in best.items()},
                          "multiple_defensible": {k: dict(v) for k, v in multi.items()}, "insufficient_support": {k: dict(v) for k, v in insuff.items()},
                          "rule_conflicts_per_record": dict(sorted(conflicts_per_record.items())),
                          "retracted_conflicts": len(retracted_c), "rule_groups_record_pairs": dict(groups.most_common()),
                          "boundary": dict(boundary), "masking_failure": dict(masking),
                          "single_set_support": {k: dict(v) for k, v in single_support.items()}}}
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "adjudication_diagnostics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with (DEST / "findings_long.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(findings[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(findings)
    with (DEST / "mandatory_second_review.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["adj_assignment_id", "source_record_id", "reasons"])
        for aid in sorted(mandatory):
            w.writerow([aid, cw[aid]["source"], "; ".join(sorted(mandatory[aid]))])
    print("written:", ", ".join(p.name for p in sorted(DEST.glob("*"))))


if __name__ == "__main__":
    main()
