"""Primary versus secondary adjudicator agreement on the formal second review (protocol 9.1; AMD-002, AMD-003).

Run once the secondary adjudicator has finished Stage 2 of every batch reviewed, from a raw export of all
instruments taken then (unassigned, so it holds the ``secondary`` group), saved inside the secondary folder:

    python compare_formal_secondary.py --export <export inside adjudication_formal/secondary/>

Inputs and how they are read:

* **Secondary.** Stage 1 comes from each preserved batch snapshot (``preserve_group.py --set
  formal-secondary-*``); a batch without a snapshot is not compared. Stage 2 comes from the export. Any Stage 1
  answer changed after preservation is flagged, and the preserved answer is used.
* **Primary.** Stage 1 comes from the preserved block snapshots. Stage 2 is the findings table as
  ``run_adjudication_diagnostics.py`` builds it from the 2026-10-19 export: harmonised mechanisms, the label
  supplement, retractions excluded, and owner-evidence addendum findings included and flagged. Release
  implications are shown as recorded and as harmonised under ADJ-121.
* **Pairing.** Records are paired through the secondary key and the primary crosswalks, by source record.
  Option letters differ between the two, so every Stage 1 answer is compared by classification, never by letter.

Populations (AMD-003):

* **core, random:** the primary estimate, 20 records reviewed blind;
* **core, mandatory:** AMD-002 items 1 to 4, reported record by record;
* **extensions:** post-reveal, reported separately;
* **all random records:** core and extensions pooled, a sensitivity analysis.

Agreement is reported as counts, percentages and Wilson 95% intervals. Cohen's kappa is given for the presence
of a model finding. Differences are listed record by record for discussion, without forced consensus.
Recurring-mechanism confirmation follows AMD-002: a mechanism is confirmed when the secondary records the same
mechanism (code, and label for a general mechanism) on the record that covers it.

Writes only to ``preregistration_restricted/adjudication_formal/secondary/analysis/``. Prints counts only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from build_formal_secondary import SECONDARY
from compare_training import stage1
from preserve_block import _choices, flat, stage1_columns
from prototype_lib import GENERAL_MECHANISM_CODES, ROOT, field_rows
import run_adjudication_diagnostics as diag

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
from analysis.validation.intervals import wilson_interval  # noqa: E402

DRAW_RECEIPT = REPO / "preregistration_restricted/adjudication_secondary_audit_draw.receipt.json"
SETS = {"core": "formal-secondary-core", "extension_1": "formal-secondary-ext1", "extension_2": "formal-secondary-ext2"}
FAMILY_NAMES = list(diag.FAMILIES.values())
MODEL = diag.FAMILIES[1]
COMPS = ("dom", "purp", "covid", "equity")


# ---------------------------------------------------------------- loading
def primary_side():
    """(Stage 1 snapshots by ADJ id, live findings by ADJ id, source -> ADJ id, harmonised release by (aid, finding))."""
    _, rows, cw, latest, supplement, retracted_f, _, addendum = diag.load()
    ch = {r[0]: dict(_choices(r[5])) for r in field_rows() if r[5].strip()}
    mech_names = {r["code"]: r["name"] for r in csv.DictReader((ROOT / "instruments" / "mechanism_vocabulary.csv").open(encoding="utf-8"))}
    snaps = {}
    for p in sorted((diag.OUT / "preservation").glob("block_*_stage1_snapshot.json")):
        snaps.update(json.loads(p.read_text(encoding="utf-8")))
    findings = diag.findings_table(rows, cw, latest, supplement, retracted_f, addendum, ch, mech_names, snaps)
    live = [f for f in findings if not f["retracted"]]
    harmonised = diag.harmonised_releases(live)
    by_aid = defaultdict(list)
    for f in live:
        by_aid[f["adj_assignment_id"]].append({**f, "release_harmonised": harmonised.get((f["adj_assignment_id"], str(f["finding"])), f["release"])})
    closure = {a: rows[a].get("adj_stage2_closure", "") for a in cw}
    return snaps, by_aid, {c["source"]: a for a, c in cw.items()}, closure, ch, mech_names


def secondary_side(export_rows, key, ch, mech_names):
    """(preserved Stage 1 by SEC id, findings by SEC id, batches with a snapshot, Stage 1 changed after preservation)."""
    snaps, batches = {}, []
    for batch, name in SETS.items():
        path = SECONDARY / "preservation" / f"{name}_stage1_snapshot.json"
        if path.exists():
            snaps.update(json.loads(path.read_text(encoding="utf-8")))
            batches.append(batch)
    cw = {k["adj_assignment_id"]: {"source": k["source_record_id"], "route": "", "sample": k["batch"], "block": 0}
          for k in key if k["adj_assignment_id"] in snaps}
    latest = {}
    harmonisation = SECONDARY / "preservation" / "mechanism_harmonisation.csv"
    if harmonisation.exists():  # typed secondary mechanisms mapped onto the vocabulary, as ADJ-091 to ADJ-093 did for the primary
        for h in csv.DictReader(harmonisation.open(encoding="utf-8")):
            latest[(h["assignment_id"], int(h["finding"]))] = h["harmonised_code"]
    rows = {a: r for a, r in export_rows.items() if a in cw}
    findings = diag.findings_table(rows, cw, latest, {}, set(), [], ch, mech_names, snaps)
    by_aid = defaultdict(list)
    for f in findings:
        by_aid[f["adj_assignment_id"]].append({**f, "release_harmonised": f["release"]})
    cols = stage1_columns()
    changed = sorted(a for a in snaps if a in export_rows and any(
        flat(export_rows[a].get(c, "")) != flat(snaps[a]["stage1_columns"].get(c, "")) for c in cols if c in export_rows[a]))
    closure = {a: rows.get(a, {}).get("adj_stage2_closure", "") for a in cw}
    return snaps, by_aid, batches, changed, closure


# ---------------------------------------------------------------- comparison
def mechanism_keys(findings):
    """AMD-002 keys for model findings: the code, or 'code | label' per label for a general mechanism."""
    keys = set()
    for f in findings:
        if f["family"] != MODEL:
            continue
        code = str(f["mechanism_code"]).strip() or "(none)"
        if not code.isdigit():
            keys.add(f"typed: {code}")
        elif int(code) in GENERAL_MECHANISM_CODES:
            keys |= {f"{code} | {lab.strip()}" for lab in f["labels"].split(";") if lab.strip()} or {f"{code} | (labels not recorded)"}
        else:
            keys.add(code)
    return keys


def pair_record(sec_aid, prim_aid, sec_snap, prim_snap, sec_f, prim_f, sec_closure, prim_closure):
    s1s, s1p = stage1(sec_snap["stage1_columns"]), stage1(prim_snap["stage1_columns"])
    comps = sorted(set(s1s["components"]) & set(s1p["components"]))
    comp_agree = {c: {k: s1s["components"][c][k] == s1p["components"][c][k] for k in ("evidence", "best", "defensible")} for c in comps}
    fam_s, fam_p = {f["family"] for f in sec_f}, {f["family"] for f in prim_f}
    mech_s, mech_p = mechanism_keys(sec_f), mechanism_keys(prim_f)
    rel = lambda fs, k: sorted({f"{f['family']}: {f[k]}" for f in fs if f[k]})
    masking = sec_snap["response"].get("adj_masking_failure")
    return {"secondary_id": sec_aid, "primary_id": prim_aid,
            "s1_components": comps, "s1_component_agreement": comp_agree,
            "s1_conflict_any": (bool(s1s["conflicts"]), bool(s1p["conflicts"])),
            "closure": (sec_closure, prim_closure),
            "families": (sorted(fam_s), sorted(fam_p)),
            "model_finding": (MODEL in fam_s, MODEL in fam_p),
            "mechanisms": (sorted(mech_s), sorted(mech_p)),
            "release": (rel(sec_f, "release"), rel(prim_f, "release"), rel(prim_f, "release_harmonised")),
            "primary_addendum_findings": sum(int(f["addendum"]) for f in prim_f),
            "masking_failure": {1: "yes", 0: "no", 2: "unsure"}.get(masking, "missing")}


def rate(flags):
    n, k = len(flags), sum(flags)
    if not n:
        return {"n": 0, "agree": 0, "percent": None, "wilson_95": None}
    ci = wilson_interval(k, n)
    return {"n": n, "agree": k, "percent": round(100 * k / n, 1), "wilson_95": [round(100 * ci.lower, 1), round(100 * ci.upper, 1)]}


def kappa(pairs):
    """Cohen's kappa for two raters' binary judgements."""
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def summarise(records):
    comp_flags = defaultdict(list)
    for r in records:
        for c, flags in r["s1_component_agreement"].items():
            for k, v in flags.items():
                comp_flags[k].append(v)
    out = {"records": len(records),
           "stage1_by_component": {k: rate(v) for k, v in comp_flags.items()},
           "stage1_any_rule_conflict": rate([a == b for a, b in (r["s1_conflict_any"] for r in records)]),
           "closure": rate([a == b for a, b in (r["closure"] for r in records)]),
           "family_set_exact": rate([a == b for a, b in (r["families"] for r in records)]),
           "model_finding_presence": {**rate([a == b for a, b in (r["model_finding"] for r in records)]),
                                      "kappa": kappa([r["model_finding"] for r in records]),
                                      "both": sum(a and b for a, b in (r["model_finding"] for r in records)),
                                      "secondary_only": sum(a and not b for a, b in (r["model_finding"] for r in records)),
                                      "primary_only": sum(b and not a for a, b in (r["model_finding"] for r in records))},
           "model_mechanisms_exact_where_both_found": rate([set(r["mechanisms"][0]) == set(r["mechanisms"][1])
                                                            for r in records if all(r["model_finding"])]),
           "family_presence": {fam: rate([(fam in r["families"][0]) == (fam in r["families"][1]) for r in records]) for fam in FAMILY_NAMES},
           "release_as_recorded_exact": rate([r["release"][0] == r["release"][1] for r in records]),
           "release_harmonised_exact": rate([r["release"][0] == r["release"][2] for r in records]),
           "masking_failure": dict(Counter(r["masking_failure"] for r in records))}
    return out


def compare(export_rows, key, draw_receipt, primary, secondary):
    snaps_p, findings_p, prim_of, closure_p, *_ = primary
    snaps_s, findings_s, batches, changed, closure_s = secondary
    meta = {k["adj_assignment_id"]: k for k in key}
    records = []
    for aid in sorted(snaps_s):
        k = meta[aid]
        prim = prim_of.get(k["source_record_id"])
        if prim is None or prim not in snaps_p:
            raise SystemExit(f"{aid}: no preserved primary record for its source record")
        r = pair_record(aid, prim, snaps_s[aid], snaps_p[prim], findings_s.get(aid, []), findings_p.get(prim, []),
                        closure_s.get(aid, ""), closure_p.get(prim, ""))
        r.update({"source_record_id": k["source_record_id"], "batch": k["batch"],
                  "random_draw": k["random_draw"] == "1", "mandatory_review": k["mandatory_review"] == "1"})
        records.append(r)
    populations = {
        "core_random (primary estimate; blind)": [r for r in records if r["batch"] == "core" and r["random_draw"]],
        "core_mandatory": [r for r in records if r["batch"] == "core" and r["mandatory_review"]],
        "core_all": [r for r in records if r["batch"] == "core"],
        "extension_1 (post-reveal)": [r for r in records if r["batch"] == "extension_1"],
        "extension_2 (post-reveal)": [r for r in records if r["batch"] == "extension_2"],
        "all_random (sensitivity; pooled)": [r for r in records if r["random_draw"]],
    }
    summary = {name: summarise(rs) for name, rs in populations.items() if rs}
    by_source = {r["source_record_id"]: r for r in records}
    confirmation = []
    for c in draw_receipt["mechanism_coverage"]:
        r = by_source.get(c["covered_by"])
        if r is None:
            status = "not reviewed"
        elif c["mechanism"] in r["mechanisms"][0]:
            status = "confirmed"
        elif any(m.startswith("typed: ") for m in r["mechanisms"][0]):
            status = "unconfirmed pending harmonisation of a typed mechanism"
        else:
            status = "unconfirmed"
        confirmation.append({"mechanism": c["mechanism"], "records_carrying": c["records"], "reviewed_on": c["covered_by"],
                             "secondary_id": r["secondary_id"] if r else "", "status": status})
    return records, summary, confirmation, batches, changed


# ---------------------------------------------------------------- report
def fmt(rate_):
    if not rate_ or not rate_["n"]:
        return "n = 0"
    lo, hi = rate_["wilson_95"]
    return f"{rate_['agree']}/{rate_['n']} ({rate_['percent']}%; 95% interval {lo} to {hi})"


def report(records, summary, confirmation, batches, changed, mandatory_reasons):
    lines = ["# Formal second review: primary versus secondary agreement", "",
             "Restricted. Do not share before the secondary review is finished (ADJ-073). Compared by classification, not option "
             "letter. Differences are for discussion; no consensus is forced.", "",
             f"Batches compared: {', '.join(batches)}."]
    if changed:
        lines += ["", f"**Stage 1 changed after preservation on {len(changed)} record(s): {', '.join(changed)}.** The preserved answers are used."]
    for name, s in summary.items():
        mf = s["model_finding_presence"]
        lines += ["", f"## {name}: {s['records']} records", "",
                  f"* Model finding present (both / secondary only / primary only: {mf['both']} / {mf['secondary_only']} / {mf['primary_only']}): "
                  f"agreement {fmt(mf)}; kappa {mf['kappa']}",
                  f"* Same model mechanisms, where both found a model finding: {fmt(s['model_mechanisms_exact_where_both_found'])}",
                  f"* Same set of families: {fmt(s['family_set_exact'])}",
                  f"* Same closure (findings or no assignable issue): {fmt(s['closure'])}",
                  f"* Stage 1, per component: evidence {fmt(s['stage1_by_component'].get('evidence'))}; best supported "
                  f"{fmt(s['stage1_by_component'].get('best'))}; defensible set {fmt(s['stage1_by_component'].get('defensible'))}",
                  f"* Stage 1, any rule conflict recorded: {fmt(s['stage1_any_rule_conflict'])}",
                  f"* Release, against primary as recorded: {fmt(s['release_as_recorded_exact'])}; against primary harmonised (ADJ-121): "
                  f"{fmt(s['release_harmonised_exact'])}",
                  f"* Secondary masking question: {s['masking_failure']}", "",
                  "| Family | Agreement on presence |", "|---|---|"]
        lines += [f"| {fam} | {fmt(v)} |" for fam, v in s["family_presence"].items()]
    lines += ["", "## Recurring model mechanisms (AMD-002 item 4)", "",
              "| Mechanism | Records carrying it | Reviewed on | Status |", "|---|---|---|---|"]
    lines += [f"| {c['mechanism']} | {c['records_carrying']} | {c['secondary_id'] or '-'} | {c['status']} |" for c in confirmation]
    lines += ["", "## Mandatory items 1 to 3", "", "| Secondary | Primary | Reason | Secondary model finding | Secondary release |",
              "|---|---|---|---|---|"]
    for r in records:
        if r["source_record_id"] in mandatory_reasons:
            lines.append(f"| {r['secondary_id']} | {r['primary_id']} | {mandatory_reasons[r['source_record_id']]} | "
                         f"{'yes' if r['model_finding'][0] else 'no'} | {'; '.join(r['release'][0]) or '-'} |")
    lines += ["", "## Record by record", "",
              "| Secondary | Primary | Batch | Selection | Families (secondary / primary) | Model mechanisms (secondary / primary) | "
              "Release (secondary / primary / primary harmonised) | Stage 1 components agreeing (best supported) |",
              "|---|---|---|---|---|---|---|---|"]
    for r in records:
        sel = "random" if r["random_draw"] else "mandatory"
        best = sum(v["best"] for v in r["s1_component_agreement"].values())
        flag = "" if r["families"][0] == r["families"][1] else " **differs**"
        conv = " (ADJ-121 convention)" if r["release"][1] != r["release"][2] else ""
        lines.append(f"| {r['secondary_id']} | {r['primary_id']} | {r['batch']} | {sel} | {'; '.join(r['families'][0]) or 'none'} / "
                     f"{'; '.join(r['families'][1]) or 'none'}{flag} | {'; '.join(r['mechanisms'][0]) or '-'} / {'; '.join(r['mechanisms'][1]) or '-'} | "
                     f"{'; '.join(r['release'][0]) or '-'} / {'; '.join(r['release'][1]) or '-'} / {'; '.join(r['release'][2]) or '-'}{conv} | "
                     f"{best}/{len(r['s1_components'])} |")
    return "\n".join(lines) + "\n"


def mandatory_reason_map():
    manifest = {m["source_record_id"]: m for m in csv.DictReader(
        (diag.DEST / "secondary_audit_manifest.csv").open(encoding="utf-8-sig"))}
    names = {"2": "prompt revision", "3": "taxonomy revision", "5": "non-release"}
    out = {}
    for rid, m in manifest.items():
        reasons = [f"evidence for {names[c.strip()]}" for c in m["release_implications"].split(";") if c.strip() in names]
        if m["unresolved_finding"] == "1":
            reasons.append("unresolved finding")
        if m["retracted_model_finding"] == "1":
            reasons.append("model finding retracted")
        if reasons:
            out[rid] = "; ".join(reasons)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", type=Path, required=True, help="raw export of all instruments after the secondary's Stage 2")
    args = parser.parse_args(argv)
    if not args.export.resolve().is_relative_to(SECONDARY.resolve()):
        parser.error(f"the export must be saved inside {SECONDARY}")
    data = args.export.read_bytes()
    export_rows = {r["adj_assignment_id"]: r for r in csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True))}
    key = list(csv.DictReader((SECONDARY / "secondary_crosswalk_KEY.csv").open(encoding="utf-8")))
    draw_receipt = json.loads(DRAW_RECEIPT.read_text(encoding="utf-8"))
    primary = primary_side()
    _, _, _, _, ch, mech_names = primary
    secondary = secondary_side(export_rows, key, ch, mech_names)
    if not secondary[0]:
        raise SystemExit("no preserved secondary batch; preserve each batch's Stage 1 before comparing")
    records, summary, confirmation, batches, changed = compare(export_rows, key, draw_receipt, primary, secondary)
    out = SECONDARY / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    (out / "secondary_agreement_report.md").write_text(
        report(records, summary, confirmation, batches, changed, mandatory_reason_map()), encoding="utf-8")
    (out / "secondary_agreement_summary.json").write_text(json.dumps(
        {"export_sha256": hashlib.sha256(data).hexdigest(), "batches": batches, "stage1_changed_after_preservation": changed,
         "summary": summary, "mechanism_confirmation": confirmation}, indent=2) + "\n", encoding="utf-8")
    with (out / "secondary_agreement_records.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["secondary_id", "primary_id", "source_record_id", "batch", "random_draw", "mandatory_review", "families_secondary",
                    "families_primary", "mechanisms_secondary", "mechanisms_primary", "release_secondary", "release_primary",
                    "release_primary_harmonised", "masking_failure"])
        for r in records:
            w.writerow([r["secondary_id"], r["primary_id"], r["source_record_id"], r["batch"], int(r["random_draw"]), int(r["mandatory_review"]),
                        "; ".join(r["families"][0]), "; ".join(r["families"][1]), "; ".join(r["mechanisms"][0]), "; ".join(r["mechanisms"][1]),
                        "; ".join(r["release"][0]), "; ".join(r["release"][1]), "; ".join(r["release"][2]), r["masking_failure"]])
    core = summary.get("core_random (primary estimate; blind)", {})
    print(json.dumps({"batches": batches, "records_compared": len(records), "core_random_records": core.get("records", 0),
                      "mechanisms_confirmed": sum(c["status"] == "confirmed" for c in confirmation),
                      "stage1_changed_after_preservation": len(changed)}, indent=2))


if __name__ == "__main__":
    main()
