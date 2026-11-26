"""Post hoc exploratory run: taxonomy fit, descriptive and triangulation (random baseline only).

Specification: SPEC_taxonomy_fit_2026-11-26.md. Not preregistered. Descriptive only; 95% Wilson CIs.
Writes aggregate tables, a restricted coding sheet and its key to preregistration_restricted/taxonomy_fit_exploratory/.
Coder notes are written to the coding sheet but never printed.

Run from the repository root (Windows: set PYTHONUTF8=1):
    python analysis/taxonomy_fit_exploratory/run.py
Re-run after the study lead has coded the sheet to fill the notes column of TFX4T001.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import random
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.config import RAW_EXPORT  # noqa: E402
from analysis.scratch_coder_stage_a.load import verify_authorities  # noqa: E402
from analysis.scratch_coder_stage_a.panels import build_stage_a_data  # noqa: E402
from analysis.scratch_coder_stage_a.sufficiency import SUFFICIENCY_LABELS, majority_category  # noqa: E402
from analysis.validation import run_owner_analysis as owner  # noqa: E402
from analysis.validation.intervals import wilson_interval  # noqa: E402

HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_taxonomy_fit_2026-11-26.md"
OUT = ROOT / "preregistration_restricted" / "taxonomy_fit_exploratory"
FINDINGS = ROOT / "preregistration_restricted" / "adjudication_formal" / "analysis" / "findings_long.csv"
SHEET = OUT / "TFX3_coding_sheet.csv"
KEY = OUT / "TFX3_coding_key.csv"
STATUS = "post hoc exploratory, not preregistered; fit counts seen before the specification"
SEED = 20261126
CODERS = ("C01", "C02", "C03")
FIT = {1: "Fit", 2: "Partial Fit", 3: "No Fit", 4: "Cannot assess from register entry"}
FLAGGED = (2, 3)
UNCLEAR = "Unclear from Register Entry"
SPLIT = "No majority / split judgement"

THEMES = {
    "T01": "No category for transport, travel or mobility",
    "T02": "No home for wellbeing",
    "T03": "No home for third-sector or civil-society research",
    "T04": "Overlap among Business, Labour Market and Poverty",
    "T05": "Descriptive Monitoring as default or its boundaries",
    "T06": "Policy Evaluation / Impact Analysis boundary",
    "T07": "Scope of the Demographic disparities / equity tag",
    "T08": "Whether a dataset alone can set a label",
    "T09": "Other missing or poorly represented domain",
    "T10": "Other missing purpose",
    "T11": "Thin evidence rather than a taxonomy problem",
    "T12": "Ambiguity of Migration & Demographics or Environment & Agriculture",
    "MISSING": "Missing category, any (T01, T02, T03, T09, T10)",
}
MISSING_CODES = ("T01", "T02", "T03", "T09", "T10")
FEEDBACK = {"T01": ("C01", "C02"), "T02": ("C01", "C02"), "T04": ("C01", "C02"), "T05": ("C02", "C03"),
            "T06": ("C01", "C03"), "T09": ("C01",), "T10": ("C01",), "T11": ("C02", "C03"), "T12": ("C03",),
            "MISSING": ("C01", "C02")}
MECHANISMS = {"T02": (38,), "T04": (3, 9, 41), "T05": (11, 36, 42), "T06": (12, 16, 43), "T07": (28, 29),
              "T08": (24,), "T12": (7,), "MISSING": (34,)}
FAMILIES = {"T11": ("3",), "MISSING": ("4",)}
TR_NOTES = {"T01": "TR-004", "T03": "TR-005", "T06": "TR-002", "T07": "TR-001", "T08": "TR-003"}
LABEL_SETS = {"T04": ("Business & Productivity", "Labour Market & Employment", "Poverty, Wealth & Living Standards"),
              "T05": ("Descriptive Monitoring", "Outcome Tracking", "Life-Course / Trajectory Analysis"),
              "T06": ("Policy Evaluation / Impact Analysis", "Outcome Tracking"),
              "T12": ("Migration & Demographics", "Environment & Agriculture")}
OWNER_THEMES_FILE = OUT / "TFX4_owner_theme_map.csv"  # owner_assignment_id,codes ; filled by the study lead


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k: int, n: int) -> tuple[float | str, float | str]:
    if n == 0:
        return "", ""
    i = wilson_interval(k, n)
    return i.lower, i.upper


def write(name: str, rows: list[dict], title: str) -> None:
    fields = list(rows[0])
    with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    def fmt(v):
        return f"{v:.3f}" if isinstance(v, float) else str(v)
    md = [f"## {name}", "", f"{title} Status: {STATUS}. Random baseline only.", "",
          "| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    md += ["| " + " | ".join(fmt(r[f]) for f in fields) + " |" for r in rows]
    (OUT / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    if not all(a.matched for a in verify_authorities()):
        raise SystemExit("authority hash mismatch")
    OUT.mkdir(parents=True, exist_ok=True)
    data = build_stage_a_data()
    b = data.responses[data.responses["population"] == "baseline"].copy()
    if len(b) != 450 or set(b["coder"]) != set(CODERS):
        raise SystemExit("baseline is not 450 coder responses")
    checks: list[str] = []

    # Part 1 ---------------------------------------------------------------
    t1 = []
    for who in (*CODERS, "All coders"):
        sel = b if who == "All coders" else b[b["coder"] == who]
        n = len(sel)
        for code, lab in FIT.items():
            k = int((sel["taxonomy_fit"] == code).sum())
            lo, hi = wilson(k, n)
            t1.append({"coder": who, "fit": lab, "count": k, "responses": n, "share": k / n, "ci_lower": lo, "ci_upper": hi})
    allc = {r["fit"]: r["count"] for r in t1 if r["coder"] == "All coders"}
    if (allc["Partial Fit"], allc["No Fit"], allc["Cannot assess from register entry"]) != (84, 4, 34):
        raise SystemExit(f"TFX1T001 does not reconcile with S9T001: {allc}")
    checks.append("TFX1T001 all-coder Partial Fit, No Fit, Cannot assess = 84, 4, 34 (S9T001)")
    write("TFX1T001", t1, "Taxonomy fit by coder, responses; 95% Wilson CIs.")

    fit_maj, suf_maj = {}, {}
    for rid, g in b.groupby("record_id"):
        g = g.set_index("coder")
        fit_maj[rid] = majority_category(tuple(int(g.loc[c, "taxonomy_fit"]) for c in CODERS), FIT)
        suf_maj[rid] = majority_category(tuple(int(g.loc[c, "sufficiency"]) for c in CODERS), SUFFICIENCY_LABELS)
    fm = Counter(fit_maj.values())
    expect = {"Fit": 119, "Partial Fit": 12, "No Fit": 0, "Cannot assess from register entry": 6, SPLIT: 13}
    if {k: fm.get(k, 0) for k in expect} != expect:
        raise SystemExit(f"TFX1T002 does not reconcile with S9T003: {fm}")
    checks.append("TFX1T002 record majorities = 119, 12, 0, 6, 13 (S9T003)")
    t2 = []
    for lab in (*FIT.values(), SPLIT):
        k = fm.get(lab, 0); lo, hi = wilson(k, 150)
        t2.append({"fit_majority": lab, "records": k, "share": k / 150, "ci_lower": lo, "ci_upper": hi})
    write("TFX1T002", t2, "Taxonomy fit by record majority (two identical ratings); 95% Wilson CIs.")

    cross = Counter((fit_maj[r], suf_maj[r]) for r in fit_maj)
    suf_cols = (*SUFFICIENCY_LABELS.values(), SPLIT)
    t3 = [{"fit_majority": f, **{s: cross.get((f, s), 0) for s in suf_cols}, "total": sum(cross.get((f, s), 0) for s in suf_cols)}
          for f in (*FIT.values(), SPLIT)]
    write("TFX1T003", t3, "Records by taxonomy-fit majority (rows) and sufficiency majority (columns).")

    flagged = b[b["taxonomy_fit"].isin(FLAGGED)]
    issue_codes = {1: "Missing or inadequately represented category", 2: "Ambiguous or overlapping category boundaries",
                   5: "Other taxonomy problem"}
    if not {i for s in flagged["taxonomy_issues"] for i in s} <= set(issue_codes):
        raise SystemExit("unexpected taxonomy issue code")
    t4 = []
    for who in (*CODERS, "All coders"):
        sel = flagged if who == "All coders" else flagged[flagged["coder"] == who]
        row = {"coder": who, "flagged_responses": len(sel)}
        for code, name in issue_codes.items():
            row[name] = int(sum(code in s for s in sel["taxonomy_issues"]))
        t4.append(row)
    tot = t4[-1]
    got = (tot["flagged_responses"], *(tot[n] for n in issue_codes.values()))
    if got != (88, 28, 76, 11):
        raise SystemExit(f"TFX1T004 does not reconcile with S9T005: {got}")
    checks.append("TFX1T004 issue ticks = 28, 76, 11 of 88 flagged responses (S9T005)")
    write("TFX1T004", t4, "Taxonomy issue types ticked on Partial Fit and No Fit responses, by coder (several per response allowed).")

    # Owners
    raw = owner.EXPORT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != owner.EXPORT_SHA256:
        raise SystemExit("owner export hash mismatch")
    rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines(keepends=True)))
    dd = owner.dictionary()
    required = {f: compile(owner.to_py(m["branching"]) if m["branching"] else "True", f, "eval")
                for f, m in dd.items() if m["required"] and m["form"] == "project_review"}
    mains = {r["owner_id"]: r for r in rows if not r["redcap_repeat_instrument"]}
    consented = {o for o, r in mains.items() if r.get("owner_consent_complete") == "2" and r.get("owner_consent") == "1"}
    complete = []
    for r in rows:
        if r["redcap_repeat_instrument"] != "project_review" or r["project_review_complete"] != "2" or r["owner_id"] not in consented:
            continue
        v = lambda name, r=r: r.get(name, "")  # noqa: E731
        if not any(eval(code, {"v": v}) and not owner.answered(r, f, dd[f]["type"]) for f, code in required.items()):
            complete.append(r)
    if len(complete) != 30:
        raise SystemExit(f"expected 30 analytically complete owner reviews, got {len(complete)}")
    checks.append("owners: 30 analytically complete reviews (as in the owner analysis)")
    of = Counter(r["po_taxonomy_fit"] for r in complete)
    issue_owner = {"Missing or inadequately represented category": "po_tax_issue___1",
                   "Ambiguous or overlapping category boundaries": "po_tax_issue___2", "Other taxonomy problem": "po_tax_issue___5"}
    t5 = [{"item": f"fit: {FIT[int(c)]}", "reviews": of.get(c, 0), "of": 30} for c in ("1", "2", "3")]
    t5 += [{"item": f"issue: {k}", "reviews": sum(r.get(f) == "1" for r in complete), "of": sum(r["po_taxonomy_fit"] in ("2", "3") for r in complete)}
           for k, f in issue_owner.items()]
    t5.append({"item": "explanation given", "reviews": sum(bool(r.get("po_tax_explain", "").strip()) for r in complete),
               "of": sum(r["po_taxonomy_fit"] in ("2", "3") for r in complete)})
    write("TFX1T005", t5, "Project owners' taxonomy fit and issue types, 30 analytically complete reviews.")
    owner_ids = {r["assignment_id"] for r in complete if r.get("po_tax_explain", "").strip()}

    # Part 2 ---------------------------------------------------------------
    rated = b[b["taxonomy_fit"].isin((1, 2, 3))]
    def labels(r):
        return [("domain", x) for x in r["domains"] if x != UNCLEAR] + [("purpose", x) for x in r["purposes"] if x != UNCLEAR]
    t21 = []
    per = {}
    for who, sel in (("All coders", rated), ("Excluding C03", rated[rated["coder"] != "C03"])):
        c_all, c_flag = Counter(), Counter()
        for _, r in sel.iterrows():
            for lab in labels(r):
                c_all[lab] += 1
                c_flag[lab] += int(r["taxonomy_fit"] in FLAGGED)
        per[who] = (c_all, c_flag)
    overall = {who: (int(sel["taxonomy_fit"].isin(FLAGGED).sum()), len(sel)) for who, sel in
               (("All coders", rated), ("Excluding C03", rated[rated["coder"] != "C03"]))}
    for lab in sorted(per["All coders"][0]):
        row = {"dimension": lab[0], "label": lab[1]}
        for who in ("All coders", "Excluding C03"):
            n, k = per[who][0][lab], per[who][1][lab]
            row[f"{who}: responses"] = n; row[f"{who}: flagged"] = k; row[f"{who}: share"] = (k / n) if n else ""
        row["fewer than 10 responses"] = "yes" if row["All coders: responses"] < 10 else ""
        t21.append(row)
    t21.append({"dimension": "all", "label": "any response rated Fit, Partial Fit or No Fit",
                **{k: v for who in ("All coders", "Excluding C03") for k, v in
                   ((f"{who}: responses", overall[who][1]), (f"{who}: flagged", overall[who][0]), (f"{who}: share", overall[who][0] / overall[who][1]))},
                "fewer than 10 responses": ""})
    write("TFX2T001", t21, "Flagged share (Partial Fit or No Fit) of responses assigning each label; Cannot assess excluded.")

    pair_all, pair_flag = Counter(), Counter()
    for _, r in rated.iterrows():
        for dim in ("domain", "purpose"):
            labs = sorted(x for d, x in labels(r) if d == dim)
            for p in combinations(labs, 2):
                pair_all[(dim, p)] += 1
                pair_flag[(dim, p)] += int(r["taxonomy_fit"] in FLAGGED)
    t22 = [{"dimension": d, "label_1": p[0], "label_2": p[1], "responses": n, "flagged": pair_flag[(d, p)], "share": pair_flag[(d, p)] / n}
           for (d, p), n in sorted(pair_all.items(), key=lambda kv: -kv[1]) if n >= 5]
    write("TFX2T002", t22, "Label pairs assigned together in one response (same dimension, at least 5 responses): flagged share.")

    # Part 3: coding sheet (notes never printed) ----------------------------
    exp = pd.read_csv(RAW_EXPORT, dtype=str, keep_default_na=False, encoding="utf-8-sig").set_index("assignment_id")
    fl = flagged.sort_values(["record_id", "coder"]).to_dict("records")
    random.Random(SEED).shuffle(fl)
    sheet, key = [], []
    for i, r in enumerate(fl, 1):
        e = exp.loc[r["assignment_id"]]
        if e["source_record_id"] != r["record_id"]:
            raise SystemExit("export join mismatch")
        sid = f"N{i:03d}"
        sheet.append({"note_id": sid, "project_title": e["project_title"], "datasets_used": e["datasets_used"],
                      "domains": "; ".join(sorted(r["domains"])), "purposes": "; ".join(sorted(r["purposes"])),
                      "taxonomy_fit": FIT[int(r["taxonomy_fit"])], "issues": "; ".join(issue_codes[i] for i in sorted(r["taxonomy_issues"])),
                      "note": e["sc_note"], "codes": "", "t99_label": "", "coding_comment": ""})
        key.append({"note_id": sid, "coder": r["coder"], "record_id": r["record_id"], "assignment_id": r["assignment_id"]})
    if len(sheet) != 88 or any(not s["note"].strip() for s in sheet):
        raise SystemExit("expected 88 flagged baseline responses, each with a note")
    checks.append("TFX3: 88 flagged baseline responses, all with a note")
    if not SHEET.exists():
        with SHEET.open("w", newline="", encoding="utf-8-sig") as h:
            w = csv.DictWriter(h, fieldnames=list(sheet[0]), lineterminator="\n"); w.writeheader(); w.writerows(sheet)
        with KEY.open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(key[0]), lineterminator="\n"); w.writeheader(); w.writerows(key)
        sheet_state = "written"
    else:
        sheet_state = "existing sheet kept (not overwritten)"
    if not OWNER_THEMES_FILE.exists():
        with OWNER_THEMES_FILE.open("w", newline="", encoding="utf-8-sig") as h:
            w = csv.writer(h, lineterminator="\n"); w.writerow(["owner_assignment_id", "codes"])
            for a in sorted(owner_ids):
                w.writerow([a, ""])

    # Part 4: triangulation ------------------------------------------------
    coded = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    keymap = {k["note_id"]: k["coder"] for k in csv.DictReader(KEY.open(encoding="utf-8"))}
    notes_done = all(c["codes"].strip() for c in coded)
    note_codes = {c["note_id"]: {x.strip() for x in c["codes"].replace(",", ";").split(";") if x.strip()} for c in coded}
    owner_map = {r["owner_assignment_id"]: {x.strip() for x in r["codes"].replace(",", ";").split(";") if x.strip()}
                 for r in csv.DictReader(OWNER_THEMES_FILE.open(encoding="utf-8-sig"))}
    owners_done = all(owner_map.values()) if owner_map else True

    finds = [r for r in csv.DictReader(FINDINGS.open(encoding="utf-8")) if r["sample"] == "baseline" and r["retracted"] == "0"]
    t4r = []
    for code, theme in THEMES.items():
        members = MISSING_CODES if code == "MISSING" else (code,)
        n_notes = sum(bool(note_codes[i] & set(members)) for i in note_codes)
        n_coders = len({keymap[i] for i in note_codes if note_codes[i] & set(members)})
        mech = MECHANISMS.get(code, ()); fam = FAMILIES.get(code, ())
        hit = [r for r in finds if (r["mechanism_code"].isdigit() and int(r["mechanism_code"]) in mech) or r["family_code"] in fam]
        by_family = Counter(r["family"] for r in hit)
        n_owner = sum(bool(v & set(members)) for v in owner_map.values())
        support = ""
        if code in LABEL_SETS:
            ca, cf = per["All coders"]
            n = sum(ca[(d, l)] for (d, l) in ca if l in LABEL_SETS[code]); k = sum(cf[(d, l)] for (d, l) in cf if l in LABEL_SETS[code])
            support = f"{k} of {n} label assignments flagged"
        coders_src = bool(FEEDBACK.get(code)) or (notes_done and n_notes > 0)
        adj_src = bool(hit) or code in TR_NOTES
        own_src = owners_done and n_owner > 0
        t4r.append({"code": code, "theme": theme,
                    "coder notes (notes; coders)": f"{n_notes}; {n_coders}" if notes_done else "pending",
                    "post-coding feedback (coders)": ", ".join(FEEDBACK.get(code, ())) or "none",
                    "adjudication findings by family": "; ".join(f"{f} {c}" for f, c in sorted(by_family.items())) or "none",
                    "TR note": TR_NOTES.get(code, ""),
                    "owner reviews": n_owner if owners_done else "pending",
                    "Part 2 support": support,
                    "source types": sum((coders_src, adj_src, own_src)),
                    "convergent (2+ source types)": "yes" if sum((coders_src, adj_src, own_src)) >= 2 else "no",
                    "complete": "yes" if notes_done and owners_done else "no: notes or owner mapping pending"})
    write("TFX4T001", t4r, "Triangulation of taxonomy themes across source types (coders, adjudication, owners).")

    meta = {"run_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "status": STATUS,
            "spec": SPEC.name, "spec_sha256": sha256(SPEC), "script_sha256": sha256(Path(__file__)), "seed": SEED,
            "checks": checks, "coding_sheet": sheet_state, "notes_coded": notes_done, "owner_mapping_done": owners_done,
            "findings_sha256": sha256(FINDINGS), "export_sha256": sha256(RAW_EXPORT),
            "outputs": {p.name: sha256(p) for p in sorted(OUT.glob("TFX[124]T*.*"))}}
    (OUT / "run_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"done; {len(checks)} checks passed; coding sheet {sheet_state}; notes coded: {notes_done}; owner mapping: {owners_done}")


if __name__ == "__main__":
    main()
