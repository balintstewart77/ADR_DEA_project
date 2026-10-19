"""Project-owner review analysis (protocol 8.6, RQ6), provisional until withdrawals close.

Reads the closing owner export (hash-pinned), the frozen owner dictionary and
the restricted recruitment tables; writes tables only to
``preregistration_restricted/owner_responses/analysis/``.  Prints no result:
the results are held until the primary adjudicator has completed route-2
Stage 1, because small owner counts could point to individual records.

Analytical completeness (5.4): affirmative consent joined by owner_id, the
review submitted, and every required field shown under the final branching
state answered (dictionary-driven; REDCap deletes hidden child values, AMD-001).
Structured outcomes use analytically complete reviews; counts are not
population estimates, so no intervals are given.  Re-run after any withdrawal
(DEV-006).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from analysis.validation.owner import OwnerReview, record_label_response_patterns, sequence_evidence_status

REPO = Path(__file__).resolve().parents[2]
EXPORT = REPO / "preregistration_restricted/owner_responses/exports/DEAValidationStudyPr_DATA_2026-10-13_0737.csv"
EXPORT_SHA256 = "792afed9d6e6b6c0d45be03aa690526a534d43f15bc18cb6b7b6e930617ad169"
DICTIONARY = REPO / "preregistration/package/06_redcap/DEAValidationStudyProjectOwner_DataDictionary_frozen_2026-08-24.csv"
DISPATCH = REPO / "preregistration_restricted/owner_candidate_frame_8a/owner_dispatch_table.csv"
FOLLOWUP = REPO / "preregistration_restricted/owner_candidate_frame_8a/PO_followup_log.csv"
OUT = REPO / "preregistration_restricted/owner_responses/analysis"
LABEL_SLOTS = [("Research Domain", f"d{n:02d}") for n in range(1, 5)] + [("Analytical Purpose", f"p{n:02d}") for n in range(1, 3)]
TAG_SLOTS = ["t01", "t02"]
EXPLANATIONS = {"label not-fit explanation": r"po_[dp]0\d_correct_explain", "label visibility explanation": r"po_[dp]0\d_vis_explain",
                "tag explanation": r"po_t0\d_(correct|vis)_explain", "missing-label basis": r"po_miss_\w+_basis",
                "sufficiency explanation": r"po_suff_explain", "taxonomy explanation": r"po_tax_explain",
                "non-public knowledge note": r"po_nonpublic_note", "other comment": r"po_other_comment"}


def dictionary():
    d = list(csv.reader(DICTIONARY.open(encoding="utf-8-sig")))
    h = d[0]
    bi = next(i for i, c in enumerate(h) if "Branching" in c)
    ri = next(i for i, c in enumerate(h) if "Required" in c)
    rows = {r[0]: {"form": r[1], "type": r[3], "choices": dict((c.split(",", 1)[0].strip(), c.split(",", 1)[1].strip())
                                                                for c in r[5].split("|") if "," in c) if r[5].strip() else {},
                   "branching": r[bi].strip(), "required": r[ri].strip().lower() == "y"} for r in d[1:]}
    return rows


def to_py(logic):
    s = re.sub(r"\[([a-z0-9_]+)\((\w+)\)\]", r"v('\1___\2')", logic)
    s = re.sub(r"\[([a-z0-9_]+)\]", r"v('\1')", s)
    s = s.replace("<>", "!=")
    s = re.sub(r"(?<![!<>=])=(?!=)", "==", s)
    return re.sub(r"(==|!=)\s*(-?\d+)\b", r"\1 '\2'", s)


def answered(row, field, kind):
    if kind == "checkbox":
        return any(v == "1" for k, v in row.items() if k.startswith(field + "___"))
    return (row.get(field) or "").strip() != ""


def main():
    data = EXPORT.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPORT_SHA256:
        raise SystemExit("the owner export does not match its pinned SHA-256")
    rows = list(csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True)))
    dd = dictionary()
    required = {f: compile(to_py(m["branching"]) if m["branching"] else "True", f, "eval")
                for f, m in dd.items() if m["required"] and m["form"] == "project_review"}
    main_rows = {r["owner_id"]: r for r in rows if not r["redcap_repeat_instrument"]}
    consented = {o for o, r in main_rows.items() if r.get("owner_consent_complete") == "2" and r.get("owner_consent") == "1"}
    reviews = [r for r in rows if r["redcap_repeat_instrument"] == "project_review"]
    po_cols = [c for c in rows[0] if c.startswith("po_")]

    # Assignment states and analytical completeness
    states, complete, check = Counter(), [], []
    for r in reviews:
        touched = any((r.get(c) or "").strip() not in ("", "0") for c in po_cols)
        submitted = r["project_review_complete"] == "2"
        v = lambda name, r=r: r.get(name, "")
        missing = [f for f, code in required.items() if eval(code, {"v": v}) and not answered(r, f, dd[f]["type"])]
        analytic = submitted and r["owner_id"] in consented and not missing
        state = "analytically complete" if analytic else ("submitted, not analytically complete" if submitted else ("partial" if touched else "untouched"))
        states[state] += 1
        check.append({"owner_id": r["owner_id"], "assignment_id": r["assignment_id"], "source_record_id": r["source_record_id"],
                      "state": state, "consent_joined": int(r["owner_id"] in consented), "missing_required": ";".join(missing)})
        if analytic:
            complete.append(r)

    lab = lambda f, val: dd.get(f, {}).get("choices", {}).get(val, val)
    # Verdicts, visibility, record-label patterns
    verdicts, by_label, visibility, owner_reviews = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), []
    for r in complete:
        per_review = {}
        for layer, slot in LABEL_SLOTS:
            label = (r.get(f"prop_{slot}_label") or "").strip()
            if not label:
                continue
            verdict = lab(f"po_{slot}_fit", r.get(f"po_{slot}_fit", ""))
            verdicts[layer][verdict] += 1
            by_label[f"{layer}: {label}"][verdict] += 1
            visibility[layer][lab(f"po_{slot}_vis", r.get(f"po_{slot}_vis", ""))] += 1
            per_review[f"{layer}: {label}"] = verdict
        owner_reviews.append(OwnerReview(record_id=r["source_record_id"], respondent_id=r["owner_id"], recruitment_route="sequence_based",
                                         proposed_label_verdicts=per_review, public_entry_sufficiency=lab("po_sufficiency", r.get("po_sufficiency", "")) or None,
                                         missing_label_report=None, taxonomy_fit=lab("po_taxonomy_fit", r.get("po_taxonomy_fit", "")) or None))
    tags = defaultdict(Counter)
    for r in complete:
        for slot in TAG_SLOTS:
            tag = (r.get(f"prop_{slot}_label") or "").strip()
            status = lab(f"prop_{slot}_status", r.get(f"prop_{slot}_status", ""))
            tags[f"{tag} (proposed {status.lower()})"][lab(f"po_{slot}_correct", r.get(f"po_{slot}_correct", ""))] += 1
            visibility[f"Tag: {tag}"][lab(f"po_{slot}_vis", r.get(f"po_{slot}_vis", ""))] += 1

    # Missing labels
    missing_any, missing_names, records_with_missing = Counter(), Counter(), set()
    for r in complete:
        any_here = False
        for field, layer in (("po_miss_domains", "Research Domains"), ("po_miss_purposes", "Analytical Purposes"), ("po_miss_tags", "Tags")):
            picked = [name for code, name in dd[field]["choices"].items() if r.get(f"{field}___{code}") == "1"]
            if picked:
                missing_any[layer] += 1
                any_here = True
                for name in picked:
                    missing_names[f"{layer}: {name}"] += 1
        if any_here:
            records_with_missing.add(r["source_record_id"])
    overall = {name: Counter(lab(f, r.get(f, "")) for r in complete) for name, f in
               (("Public-entry sufficiency", "po_sufficiency"), ("Taxonomy fit", "po_taxonomy_fit"), ("Relied on non-public knowledge", "po_nonpublic"))}
    tax_issues = Counter(name for r in complete for code, name in dd["po_tax_issue"]["choices"].items() if r.get(f"po_tax_issue___{code}") == "1")
    comments = Counter()
    for r in complete:
        for name, pattern in EXPLANATIONS.items():
            comments[name] += sum(1 for c in r if re.fullmatch(pattern, c) and (r.get(c) or "").strip())

    # Recruitment flow
    dispatch = [d for d in csv.DictReader(DISPATCH.open(encoding="utf-8")) if d["owner_id"]]
    followup = list(csv.DictReader(FOLLOWUP.open(encoding="utf-8-sig")))
    withdrawn = {f["owner_id"] for f in followup if "WITHDRAWN" in (f.get("consent status", "") + f.get("action", "")).upper()}
    responding = {r["owner_id"] for r in complete}
    flow = {"owners invited": len(dispatch), "invitation waves": dict(Counter(d["recruitment_wave"] for d in dispatch)),
            "owners consented": len(consented), "owners recorded as withdrawn before submitting": len(withdrawn),
            "owners with at least one analytically complete review": len(responding),
            "reviews offered": len(reviews), "review states": dict(states),
            "unique records with an analytically complete review": len({r["source_record_id"] for r in complete}),
            "composition: institutions of responding owners": dict(Counter(d["institution"].strip() for d in dispatch if d["owner_id"] in responding))}
    results = {"status": "PROVISIONAL until the 26 October 2026 withdrawal deadline (DEV-006)",
               "recruitment_flow": flow,
               "evidence_status": sequence_evidence_status(tuple(owner_reviews)),
               "label_verdicts_by_layer": {k: dict(v) for k, v in verdicts.items()},
               "label_verdicts_by_label": {k: dict(v) for k, v in sorted(by_label.items())},
               "record_label_patterns": dict(record_label_response_patterns(tuple(owner_reviews))),
               "tag_status_correctness": {k: dict(v) for k, v in tags.items()},
               "visibility": {k: dict(v) for k, v in visibility.items()},
               "missing_labels": {"reviews naming a missing label, by layer": dict(missing_any),
                                  "reviews naming any missing label": sum(1 for r in complete if r["source_record_id"] in records_with_missing),
                                  "records with any missing label": len(records_with_missing),
                                  "labels named missing": dict(missing_names)},
               "overall_judgements": {k: dict(v) for k, v in overall.items()}, "taxonomy_issue_types": dict(tax_issues),
               "comments_provided": dict(comments)}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "owner_results_provisional.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    with (OUT / "owner_completeness_check.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(check[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(check)
    md = ["# Project-owner review results (PROVISIONAL)", "",
          "Protocol 8.6 / RQ6. Provisional until the 26 October 2026 withdrawal deadline (DEV-006); re-run after any withdrawal. "
          "Counts and proportions only; recruitment was purposive and responses cluster by researcher, so no intervals are given and "
          "nothing is broken down by owner in any public output.", ""]

    def table(title, counter_map, cols=None):
        md.append(f"## {title}\n")
        keys = cols or sorted({k for c in counter_map.values() for k in c})
        md.append("| | " + " | ".join(keys) + " | Total |")
        md.append("|---|" + "---|" * (len(keys) + 1))
        for name, c in counter_map.items():
            total = sum(c.values())
            md.append(f"| {name} | " + " | ".join(f"{c.get(k, 0)} ({100 * c.get(k, 0) / total:.0f}%)" if total else "0" for k in keys) + f" | {total} |")
        md.append("")

    md += ["## Recruitment flow", ""] + [f"* {k}: {v}" for k, v in flow.items()] + ["", f"Evidence status: **{results['evidence_status']}**", ""]
    table("Proposed-label verdicts, by layer", verdicts, ["Fits", "Does not fit", "Unsure"])
    table("Proposed-label verdicts, by label", dict(sorted(by_label.items())), ["Fits", "Does not fit", "Unsure"])
    md += [f"Record-label patterns: {results['record_label_patterns']}", ""]
    table("Tag status correctness", tags)
    table("Basis visible in the public entry", visibility)
    md += ["## Missing labels", ""] + [f"* {k}: {v}" for k, v in results["missing_labels"].items()] + [""]
    for k, v in overall.items():
        table(k, {k: v})
    md += ["## Taxonomy issue types", ""] + [f"* {k}: {v}" for k, v in tax_issues.items()] + ["",
           "## Comments provided (for thematic reading; counts are not prevalence)", ""] + [f"* {k}: {v}" for k, v in comments.items()]
    (OUT / "owner_results_provisional.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    receipt = {"run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "export_sha256": EXPORT_SHA256,
               "outputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("owner_*"))}}
    (OUT / "owner_analysis_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("owner analysis written to", OUT.relative_to(REPO), "(results held; not printed)")


if __name__ == "__main__":
    main()
