"""Supplementary Table S12: project-owner verdicts (protocol 8.6), plus the counts §3.9 cites.

Re-runs ``run_owner_analysis`` into a temporary folder and requires its JSON to equal
the analysis record (``owner_results_provisional.json``), so the record is shown to
hold for the final export.  The table is then built from that record alone; display
rounding only.  Two further descriptive counts for §3.9 are written alongside: the
size of the label sets owners were shown, and the overlap of owner-reviewed records
with the coder samples (with the §3.3 consensus states for baseline records).  These
are aggregate; no record identifier, owner or institution is written.

Outputs (gitignored): ``preregistration_restricted/owner_responses/analysis/table_s12/``,
with the table copied to ``DEA_paper/tables/``.  Owner-derived material: keep it away
from the secondary adjudicator until their Stage 1 is complete (adjudication methods 9.2).

Run from the repository root:  python -m analysis.visualisations.owner_table_s12
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402
import render_scratch_coder_pass4 as p4  # noqa: E402

from analysis.enrichment_calibration_exploratory.run import classify_state, majority_set  # noqa: E402
from analysis.scratch_coder_stage_a.config import CODERS  # noqa: E402
from analysis.scratch_coder_stage_a.panels import build_stage_a_data  # noqa: E402
from analysis.validation import run_owner_analysis as roa  # noqa: E402

SLUG = "supplementary_table_s12_owner_verdicts"
ANALYSIS = REPO / "preregistration_restricted/owner_responses/analysis"
RECORD = ANALYSIS / "owner_results_provisional.json"
COMPLETENESS = ANALYSIS / "owner_completeness_check.csv"
OUT = ANALYSIS / "table_s12"
PAPER_TABLES = REPO / "DEA_paper/tables"
TAGS = {"Demographic disparities / equity tag": "Demographic disparities / equity", "COVID-19 & Pandemic": "COVID-19 & Pandemic"}
LAYERS = {"Research Domain": "Research Domains", "Analytical Purpose": "Analytical Purposes"}
LABEL_SLOTS = {"Research Domains": ("d", 4, "domains", "po_miss_domains"), "Analytical Purposes": ("p", 2, "purposes", "po_miss_purposes")}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pct(k: int, n: int) -> str:
    return f"{k} ({p4.whole_percent_text(k, n)})" if n else "0"


def tag_name(key: str) -> str:
    for raw, shown in TAGS.items():
        if key.startswith(raw):
            return shown
    raise KeyError(key)


def reproduce_record() -> dict:
    """Re-run the owner analysis from the final inputs; it must equal the record."""
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    tmp = OUT / "_rerun"
    shutil.rmtree(tmp, ignore_errors=True)
    original = roa.OUT
    try:
        roa.OUT = tmp
        with contextlib.redirect_stdout(io.StringIO()):
            roa.main()
        rerun = json.loads((tmp / "owner_results_provisional.json").read_text(encoding="utf-8"))
        same_check = (tmp / "owner_completeness_check.csv").read_bytes() == COMPLETENESS.read_bytes()
    finally:
        roa.OUT = original
        shutil.rmtree(tmp, ignore_errors=True)
    if rerun != record or not same_check:
        raise RuntimeError("the owner analysis no longer reproduces its record from the final export")
    return record


def descriptive_counts() -> dict:
    """Proposed-set sizes and coder-sample overlap, aggregate only."""
    dd = roa.dictionary()
    done = {c["assignment_id"] for c in csv.DictReader(COMPLETENESS.open(encoding="utf-8")) if c["state"] == "analytically complete"}
    rows = [r for r in csv.DictReader(roa.EXPORT.read_bytes().decode("utf-8-sig").splitlines(keepends=True))
            if r["redcap_repeat_instrument"] == "project_review" and r["assignment_id"] in done]
    data = build_stage_a_data()
    sizes = {layer: Counter() for layer in LABEL_SLOTS}
    overlap = {"baseline": 0, "hard-case": 0}
    states: dict[str, Counter] = {layer: Counter() for layer in LABEL_SLOTS}
    cases = []
    for r in rows:
        rid = r["source_record_id"]
        sample = "baseline" if rid in data.baseline_ids else "hard-case" if rid in data.hard_case_ids else None
        for layer, (s, k, field, miss) in LABEL_SLOTS.items():
            proposed = {(r.get(f"prop_{s}0{i}_label") or "").strip() for i in range(1, k + 1)} - {""}
            sizes[layer][len(proposed)] += 1
            if sample and set(data.model[rid][layer]) != proposed:
                raise RuntimeError("labels shown to an owner differ from Fable 5's production labels")
            if sample != "baseline":
                continue
            by = {x["coder"]: x for x in data.responses[data.responses["record_id"] == rid].to_dict("records")}
            sets = [by[c][field] for c in CODERS]
            state = classify_state(sets, majority_set(sets))
            states[layer][state] += 1
            if state in ("S3", "S4"):
                verdicts = [dd[f"po_{s}0{i}_fit"]["choices"].get(r.get(f"po_{s}0{i}_fit", ""), "") for i in range(1, k + 1)
                            if (r.get(f"prop_{s}0{i}_label") or "").strip()]
                named = [n for c, n in dd[miss]["choices"].items() if r.get(f"{miss}___{c}") == "1" and n not in proposed]
                cases.append({"dimension": layer, "state": state, "model_labels_proposed": len(proposed),
                              "verdicts": dict(Counter(verdicts)), "further_labels_named_missing": len(named)})
        if sample:
            overlap[sample] += 1
    return {"proposed_set_sizes": {k: dict(sorted(v.items())) for k, v in sizes.items()},
            "reviewed_records": len(rows), "overlap_with_coder_samples": overlap,
            "baseline_consensus_states": {k: dict(sorted(v.items())) for k, v in states.items()},
            "state_key": "S1 unanimous substantive; S2 substantive majority with dissent; S3 Unclear majority; S4 no agreed label (§3.3)",
            "unclear_or_no_agreed_label_cases": cases}


def build(record: dict) -> tuple[list[tuple[str, list[str], list[list[str]]]], list[list[str]]]:
    panels, flat = [], []

    # S12a: proposed-label verdicts
    headers = ["Label", "Fits, n (%)", "Does not fit, n (%)", "Unsure, n (%)", "Completed verdicts"]
    body = []
    for raw, layer in LAYERS.items():
        body.append([layer])
        items = sorted(((k.split(": ", 1)[1], v) for k, v in record["label_verdicts_by_label"].items() if k.startswith(raw + ":")),
                       key=lambda kv: (-sum(kv[1].values()), kv[0]))
        for name, counts in items + [(f"All {layer}", record["label_verdicts_by_layer"][raw])]:
            n = sum(counts.values())
            row = [name] + [pct(counts.get(v, 0), n) for v in ("Fits", "Does not fit", "Unsure")] + [str(n)]
            body.append(row); flat.append(["S12a", layer] + row)
    if sum(sum(c.values()) for c in record["label_verdicts_by_layer"].values()) != sum(sum(c.values()) for c in record["label_verdicts_by_label"].values()):
        raise RuntimeError("S12a label rows do not sum to the layer totals")
    panels.append(("Supplementary Table S12a. Owner verdicts on the labels Fable 5 proposed", headers, body))

    # S12b: tag status
    headers = ["Tag and proposed status", "Answers", "As answered: Yes", "As answered: No", "As answered: Unsure",
               "DEV-007 sensitivity: Yes", "DEV-007 sensitivity: No", "DEV-007 sensitivity: Unsure"]
    body = []
    for key in sorted(record["tag_status_correctness"], key=lambda k: (list(TAGS).index(next(t for t in TAGS if k.startswith(t))), "not applied" not in k)):
        a, s = record["tag_status_correctness"][key], record["tag_status_correctness_sensitivity_DEV007"][key]
        n = sum(a.values())
        if sum(s.values()) != n:
            raise RuntimeError("S12b sensitivity total differs")
        status = "proposed not applied" if "not applied" in key else "proposed applied"
        row = [f"{tag_name(key)}, {status}", str(n)] + [pct(a.get(v, 0), n) for v in ("Yes", "No", "Unsure")] + [pct(s.get(v, 0), n) for v in ("Yes", "No", "Unsure")]
        body.append(row); flat.append(["S12b", tag_name(key)] + row)
    moved = sum(record["tag_status_correctness"][k].get("No", 0) - record["tag_status_correctness_sensitivity_DEV007"][k].get("No", 0) for k in record["tag_status_correctness"])
    if moved != record["tag_answers_read_as_misread_DEV007"]:
        raise RuntimeError("S12b sensitivity changes differ from the DEV-007 count")
    panels.append(("Supplementary Table S12b. Owner answers on whether each proposed tag status is correct", headers, body))

    # S12c: basis visible
    options = ("Clearly visible", "Partly visible", "Not visible", "Unsure")
    headers = ["Proposed label or tag", "Judgements"] + [f"{o}, n (%)" for o in options]
    body = []
    for key, counts in record["visibility"].items():
        name = LAYERS.get(key) or tag_name(key.removeprefix("Tag: "))
        n = sum(counts.values())
        row = [name, str(n)] + [pct(counts.get(o, 0), n) for o in options]
        body.append(row); flat.append(["S12c", name] + row)
    panels.append(("Supplementary Table S12c. Whether the basis for each proposed label or tag is visible in the public entry", headers, body))

    # S12d: missing labels
    m = record["missing_labels"]
    reviews = sum(record["overall_judgements"]["Public-entry sufficiency"].values())
    headers = ["Layer or label", "Named missing (DEV-007)", "Selected as missing, including labels already proposed"]
    body = [["Records with at least one label named"]]
    raw_any = record.get("_raw_any_records")
    for layer in ("Research Domains", "Analytical Purposes", "Tags"):
        row = [layer if layer != "Tags" else "Tags", pct(m["reviews naming a missing label, by layer"].get(layer, 0), reviews),
               pct(m["raw: reviews selecting any label, by layer"].get(layer, 0), reviews)]
        body.append(row); flat.append(["S12d", "records"] + row)
    row = ["Any layer", pct(m["records with any missing label"], reviews), pct(raw_any, reviews)]
    body.append(row); flat.append(["S12d", "records"] + row)
    body.append(["Times each label was named"])
    names = sorted(set(m["raw: labels selected"]) | set(m["labels named missing"]),
                   key=lambda k: (["Research Domains", "Analytical Purposes", "Tags"].index(k.split(": ")[0]), -m["labels named missing"].get(k, 0), k))
    for key in names:
        layer, label = key.split(": ", 1)
        label = TAGS.get(label, label)
        row = [f"{layer}: {label}", str(m["labels named missing"].get(key, 0)), str(m["raw: labels selected"].get(key, 0))]
        body.append(row); flat.append(["S12d", "labels"] + row)
    if sum(m["raw: labels selected"].values()) - sum(m["labels named missing"].values()) != m["already-proposed selections excluded"]:
        raise RuntimeError("S12d raw and DEV-007 label counts do not reconcile")
    panels.append(("Supplementary Table S12d. Labels owners named as missing", headers, body))

    # S12e: overall judgements
    headers = ["Question and answer", "Reviews, n (%)"]
    body = []
    orders = {"Public-entry sufficiency": ("Sufficient", "Partial", "Insufficient"), "Taxonomy fit": ("Fit", "Partial Fit", "No Fit"),
              "Relied on non-public knowledge": ("No", "Yes", "Unsure")}
    for question, order in orders.items():
        counts = record["overall_judgements"][question]
        if sum(counts.values()) != reviews:
            raise RuntimeError(f"S12e {question} total differs")
        body.append([question])
        for answer in order:
            row = [answer, pct(counts.get(answer, 0), reviews)]
            body.append(row); flat.append(["S12e", question] + row)
    body.append(["Taxonomy issue type, more than one allowed"])
    for issue, count in sorted(record["taxonomy_issue_types"].items(), key=lambda kv: -kv[1]):
        row = [issue, str(count)]
        body.append(row); flat.append(["S12e", "Taxonomy issue type"] + row)
    panels.append(("Supplementary Table S12e. Owners' overall judgements", headers, body))
    return panels, flat


def main() -> None:
    record = reproduce_record()
    OUT.mkdir(parents=True, exist_ok=True)
    counts = descriptive_counts()
    # Raw any-layer missing-label records are not in the record; recompute from the export the same way.
    dd = roa.dictionary()
    done = {c["assignment_id"] for c in csv.DictReader(COMPLETENESS.open(encoding="utf-8")) if c["state"] == "analytically complete"}
    rows = [r for r in csv.DictReader(roa.EXPORT.read_bytes().decode("utf-8-sig").splitlines(keepends=True))
            if r["redcap_repeat_instrument"] == "project_review" and r["assignment_id"] in done]
    record["_raw_any_records"] = sum(any(r.get(f"{f}___{c}") == "1" for f in ("po_miss_domains", "po_miss_purposes", "po_miss_tags")
                                         for c in dd[f]["choices"]) for r in rows)
    counts["raw_records_with_any_missing_selection"] = record["_raw_any_records"]
    panels, flat = build(record)

    md_path, csv_path = OUT / f"{SLUG}.md", OUT / f"{SLUG}.csv"
    md = []
    for title, headers, body in panels:
        md += [f"**{title}**", "", p3.html_table(headers, body).rstrip("\n"), ""]
    md_path.write_text("\n".join(md), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["panel", "group", "row", "values..."])
        w.writerows(flat)
    counts_path = OUT / "owner_section_counts.json"
    counts_path.write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    banned, _ = p4.file_checks([md_path, csv_path])
    # H.9 minus signs; identifiers such as DEV-007 are exempt, as COVID-19 and GPT-5.5 are in pass 4.
    minus = [{"path": str(p), "position": x.start()} for p in (md_path, csv_path)
             for x in re.finditer(r"(?<!COVID)(?<!GPT)(?<!DEV)-(?=\d)", p.read_text(encoding="utf-8"))]
    if banned or minus:
        raise RuntimeError(f"S12 wording or minus-sign check failed: {banned + minus}")
    manifest = {"deliverable": "Supplementary Table S12", "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_record": {str(RECORD.relative_to(REPO)).replace("\\", "/"): sha256(RECORD)},
                "record_reproduced_from_final_export": True, "export_sha256": roa.EXPORT_SHA256,
                "outputs": {p.name: sha256(p) for p in (md_path, csv_path, counts_path)},
                "status": "protocol 8.6 owner results; tag sensitivity and missing-label rule under DEV-007 (a deviation, not preregistered); "
                          "proposed-set sizes and coder-sample overlap are descriptive"}
    (OUT / f"{SLUG}_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    PAPER_TABLES.mkdir(parents=True, exist_ok=True)
    for path in (md_path, csv_path):
        shutil.copy2(path, PAPER_TABLES / path.name)
    print(f"Supplementary Table S12 written to {OUT.relative_to(REPO)} and copied to {PAPER_TABLES.relative_to(REPO)}; checks passed")


if __name__ == "__main__":
    main()
