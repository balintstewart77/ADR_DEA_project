"""Owner missing-label reports: cross-tabulations and free-text coding sheets (exploratory).

Specification: SPEC_owner_missing_labels_2026-11-13.md (hash recorded in run metadata).

  python -m analysis.owner_missing_label_exploratory.run extract    # Part A tables, Part B sheets
  python -m analysis.owner_missing_label_exploratory.run summarise  # Part B tables from a codes file

Reads restricted inputs; writes only to
preregistration_restricted/owner_responses/analysis/missing_label_exploratory/.
Prints no owner text.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from analysis.validation import run_owner_analysis as roa

HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_owner_missing_labels_2026-11-13.md"
SPEC_SHA256 = "af8777831ff859b936b894e231f82382940205e7166ce7591395a248a0229f2c"
OUT = roa.REPO / "preregistration_restricted/owner_responses/analysis/missing_label_exploratory"
COMPLETENESS = roa.REPO / "preregistration_restricted/owner_responses/analysis/owner_completeness_check.csv"
LAYERS = {"Research Domains": ("po_miss_domains", "po_miss_domain_basis", [f"d0{i}" for i in range(1, 5)]),
          "Analytical Purposes": ("po_miss_purposes", "po_miss_purpose_basis", ["p01", "p02"]),
          "Tags": ("po_miss_tags", "po_miss_tag_basis", [])}
OTHER_TEXT = {"sufficiency explanation": "po_suff_explain", "non-public knowledge note": "po_nonpublic_note",
              "taxonomy explanation": "po_tax_explain", "other comment": "po_other_comment"}
OTHER_PATTERNS = {"label visibility explanation": ("_vis_explain", ("po_d0", "po_p0")),
                  "label not-fit explanation": ("_correct_explain", ("po_d0", "po_p0"))}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> tuple[list[dict], dict]:
    if sha256(SPEC) != SPEC_SHA256:
        raise SystemExit("specification changed since its hash was recorded")
    data = roa.EXPORT.read_bytes()
    if hashlib.sha256(data).hexdigest() != roa.EXPORT_SHA256:
        raise SystemExit("owner export does not match its pinned SHA-256")
    done = {c["assignment_id"] for c in csv.DictReader(COMPLETENESS.open(encoding="utf-8")) if c["state"] == "analytically complete"}
    rows = [r for r in csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True))
            if r["redcap_repeat_instrument"] == "project_review" and r["assignment_id"] in done]
    if len(rows) != 30 or len({r["source_record_id"] for r in rows}) != 30:
        raise SystemExit("expected 30 analytically complete reviews of 30 records")
    return sorted(rows, key=lambda r: r["assignment_id"]), roa.dictionary()


def review_facts(r: dict, dd: dict) -> dict:
    lab = lambda f: dd[f]["choices"].get(r.get(f, ""), r.get(f, ""))
    proposed = {layer: [(r.get(f"prop_{s}_label") or "").strip() for s in slots if (r.get(f"prop_{s}_label") or "").strip()]
                for layer, (_, _, slots) in LAYERS.items()}
    all_proposed = set(proposed["Research Domains"]) | set(proposed["Analytical Purposes"])  # as run_owner_analysis (DEV-007 rule 1)
    facts = {"assignment_id": r["assignment_id"], "record": r["source_record_id"], "owner": r["owner_id"],
             "nonpublic": lab("po_nonpublic"), "sufficiency": lab("po_sufficiency"), "taxonomy_fit": lab("po_taxonomy_fit"),
             "proposed": proposed, "raw": {}, "genuine": {}, "dup": {}, "basis": {}}
    for layer, (field, basis, _) in LAYERS.items():
        picked = [n for c, n in dd[field]["choices"].items() if r.get(f"{field}___{c}") == "1"]
        facts["raw"][layer] = picked
        facts["genuine"][layer] = [n for n in picked if n not in all_proposed]
        facts["dup"][layer] = [n for n in picked if n in all_proposed]
        facts["basis"][layer] = (r.get(basis) or "").strip()
    return facts


def write_table(name: str, header: list[str], body: list[list], note: str) -> None:
    with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h, lineterminator="\n"); w.writerow(header); w.writerows(body)
    md = [f"## {name}", "", note, "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(str(x) for x in row) + " |" for row in body]
    (OUT / f"{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def crosstab(facts: list[dict], column: str, options: tuple[str, ...], name: str, note: str) -> None:
    header = ["Missing-label status", "Rule"] + list(options) + ["Total", "Researchers contributing (restricted; never publish)"]
    body = []
    for rule in ("DEV-007", "raw"):
        key = "genuine" if rule == "DEV-007" else "raw"
        for layer in ("Any layer", *LAYERS):
            has = (lambda f: any(f[key].values())) if layer == "Any layer" else (lambda f, l=layer: bool(f[key][l]))
            for status, test in (("named", has), ("none named", lambda f, h=has: not h(f))):
                cell = [f for f in facts if test(f)]
                counts = Counter(f[column] for f in cell)
                body.append([f"{layer}: {status}", rule] + [counts.get(o, 0) for o in options] + [len(cell), len({f['owner'] for f in cell})])
    unexpected = {f[column] for f in facts} - set(options)
    if unexpected:
        raise RuntimeError(f"{name}: unexpected answers {unexpected}")
    write_table(name, header, body, note)


def extract() -> None:
    rows, dd = load()
    OUT.mkdir(parents=True, exist_ok=True)
    facts = [review_facts(r, dd) for r in rows]
    if sum(any(f["genuine"].values()) for f in facts) != 15 or sum(any(f["raw"].values()) for f in facts) != 16:
        raise RuntimeError("missing-label counts differ from Supplementary Table S12d")

    note = "Unit: analytically complete review (one per record), n = 30. Counts only; no tests or intervals; responses cluster within seven researchers."
    crosstab(facts, "nonpublic", ("No", "Yes", "Unsure"), "OMX1T001", "Missing-label reports against 'relied on non-public knowledge'. " + note)
    crosstab(facts, "sufficiency", ("Sufficient", "Partial", "Insufficient"), "OMX1T002", "Missing-label reports against owner-rated public-entry sufficiency. " + note)
    crosstab(facts, "taxonomy_fit", ("Fit", "Partial Fit", "No Fit"), "OMX1T003", "Missing-label reports against owner-rated taxonomy fit. " + note)

    labels = defaultdict(Counter)
    for f in facts:
        for layer in LAYERS:
            for name in f["genuine"][layer]:
                labels[f"{layer}: {name}"][f["nonpublic"]] += 1
    body = [[k, v.get("No", 0), v.get("Yes", 0), v.get("Unsure", 0), sum(v.values())] for k, v in sorted(labels.items())]
    body.append(["All named missing labels", *(sum(r[i] for r in body) for i in (1, 2, 3, 4))])
    write_table("OMX1T004", ["Missing label (DEV-007)", "No", "Yes", "Unsure", "Total"], body,
                "Each missing label named under DEV-007, by the same review's answer on reliance on non-public knowledge.")

    over_cap = [f for f in facts if len(f["proposed"]["Analytical Purposes"]) + len(f["genuine"]["Analytical Purposes"]) > 2]
    sel = [(f, layer) for f in facts for layer in LAYERS if f["raw"][layer]]
    body = [["Reviews whose missing purposes would exceed two purposes in total", len(over_cap)],
            ["Reviews selecting at least one already-proposed label (DEV-007)", sum(any(f["dup"].values()) for f in facts)],
            ["Already-proposed selections", sum(len(v) for f in facts for v in f["dup"].values())],
            ["Layer selections (raw) with a basis explanation", sum(1 for f, l in sel if f["basis"][l])],
            ["Layer selections (raw) without a basis explanation", sum(1 for f, l in sel if not f["basis"][l])],
            ["Layer selections with only already-proposed labels", sum(1 for f, l in sel if not f["genuine"][l])]]
    write_table("OMX1T005", ["Check", "Count"], body, "Mechanical rule checks on missing-label selections. Unit as stated in each row.")

    # Part B coding sheets: one row per DEV-007 missing label, with its layer's basis text and the public entry shown
    by_id = {r["assignment_id"]: r for r in rows}
    sheet, n = [], 0
    for f in facts:
        r = by_id[f["assignment_id"]]
        for layer in LAYERS:
            for name in f["genuine"][layer]:
                n += 1
                sheet.append({"item": f"OMX-{n:02d}", "record": f["record"], "layer": layer, "missing_label": name,
                              "labels_named_in_layer": "; ".join(f["genuine"][layer]),
                              "already_proposed_also_selected": "; ".join(f["dup"][layer]),
                              "proposed_labels_shown": "; ".join(f["proposed"]["Research Domains"] + f["proposed"]["Analytical Purposes"]),
                              "project_title": r.get("project_title", ""), "datasets_used": r.get("datasets_used", ""),
                              "basis_text": f["basis"][layer], "nonpublic": f["nonpublic"], "nonpublic_note": (r.get("po_nonpublic_note") or "").strip(),
                              "sufficiency": f["sufficiency"], "sufficiency_explanation": (r.get("po_suff_explain") or "").strip(),
                              "B1_rule_reading": "", "B2_basis_source": "", "rationale": ""})
    fields = list(sheet[0])
    with (OUT / "coding_sheet_blank.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(sheet)
    # Candidate codes were drafted once into this file and are now kept in sealed_candidate/; never rewritten here.

    other = []
    for f in facts:
        r = by_id[f["assignment_id"]]
        for label, field in OTHER_TEXT.items():
            if (r.get(field) or "").strip():
                other.append({"record": f["record"], "field": label, "text": r[field].strip()})
        for label, (suffix, prefixes) in OTHER_PATTERNS.items():
            for c in r:
                if c.endswith(suffix) and c.startswith(prefixes) and (r.get(c) or "").strip():
                    slot = c[3:6]
                    other.append({"record": f["record"], "field": f"{label} ({(r.get(f'prop_{slot}_label') or '').strip()})", "text": r[c].strip()})
    with (OUT / "other_free_text.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["record", "field", "text"], lineterminator="\n"); w.writeheader(); w.writerows(other)

    meta = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "spec": SPEC.name, "spec_sha256": SPEC_SHA256,
            "export_sha256": roa.EXPORT_SHA256, "coding_units": len(sheet), "other_free_text_items": len(other),
            "outputs": {p.name: sha256(p) for p in sorted(OUT.glob("OMX1T00[1-5].*"))}}
    (OUT / "run_metadata_extract.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"extract written: {len(sheet)} coding units, {len(other)} other free-text items (text not printed)")


def summarise(codes_file: str = "candidate_codes_claude.csv") -> None:
    path = OUT / codes_file
    codes = list(csv.DictReader(path.open(encoding="utf-8")))
    blank = {c["item"] for c in codes if not c["B1_rule_reading"] or not c["B2_basis_source"]}
    if blank:
        raise SystemExit(f"uncoded items: {sorted(blank)}")
    if {c["B1_rule_reading"] for c in codes} - set("SIUN") or {c["B2_basis_source"] for c in codes} - set("EKBU"):
        raise SystemExit("codes outside the specified sets")
    status = ("candidate codes (Claude Opus 5.5), not yet verified" if "claude" in codes_file else
              "final codes: study lead, after discussion of disagreements with candidate codes (OMX1T010) and the dated codebook clarifications"
              if codes_file == "codes_final.csv" else f"codes from {codes_file}")
    b1, b2 = ("S", "I", "U", "N"), ("E", "K", "B", "U")
    body = []
    for layer in (*LAYERS, "All layers"):
        sub = [c for c in codes if layer == "All layers" or c["layer"] == layer]
        x = Counter((c["B1_rule_reading"], c["B2_basis_source"]) for c in sub)
        for a in b1:
            body.append([layer, a] + [x.get((a, b), 0) for b in b2] + [sum(x.get((a, b), 0) for b in b2)])
        body.append([layer, "Total"] + [sum(x.get((a, b), 0) for a in b1) for b in b2] + [len(sub)])
    write_table("OMX1T006", ["Layer", "B1 rule reading", "B2: E entry", "B2: K knowledge", "B2: B both", "B2: U unclear", "Total"], body,
                f"Missing labels (DEV-007) by rule reading (S substantive, I incidental, U unclear, N no explanation) and basis source. Status: {status}.")
    x = Counter((c["nonpublic"], c["B2_basis_source"]) for c in codes)
    body = [[np] + [x.get((np, b), 0) for b in b2] + [sum(x.get((np, b), 0) for b in b2)] for np in ("No", "Yes", "Unsure")]
    write_table("OMX1T007", ["Review: relied on non-public knowledge", "E entry", "K knowledge", "B both", "U unclear", "Total"], body,
                f"Basis source of each missing label against the review's own answer on non-public knowledge. Status: {status}.")
    meta = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "spec_sha256": SPEC_SHA256, "codes_file": codes_file,
            "codes_sha256": sha256(path), "status": status, "outputs": {p.name: sha256(p) for p in sorted(OUT.glob("OMX1T00[67].*"))}}
    (OUT / "run_metadata_summarise.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("summary tables written:", status)


def posthoc() -> None:
    """Added 13 November 2026 after viewing OMX1T001-T005 and the coding sheet; NOT in the specification."""
    rows, dd = load()
    facts = [review_facts(r, dd) for r in rows]
    named = [f for f in facts if any(f["genuine"].values())]
    body = []
    for label, group in (("Review also re-selected an already-proposed label", [f for f in named if any(f["dup"].values())]),
                         ("Review re-selected no proposed label", [f for f in named if not any(f["dup"].values())])):
        labels = [(f, l, n) for f in group for l in LAYERS for n in f["genuine"][l]]
        body.append([label, len(group), len(labels), sum(1 for f, l, _ in labels if f["basis"][l]), sum(1 for f, l, _ in labels if not f["basis"][l]),
                     sum(f["sufficiency"] == "Partial" for f in group), sum(f["nonpublic"] == "No" for f in group), len({f["owner"] for f in group})])
    write_table("OMX1T008", ["Reviews naming a missing label (DEV-007)", "Reviews", "Missing labels", "With explanation", "Without explanation",
                             "Reviews rating the entry Partial", "Reviews reporting no non-public knowledge", "Researchers (restricted; never publish)"], body,
                "POST HOC: added after viewing OMX1T001-T005 and the coding sheet; not in the specification. Unit as stated in each column.")
    x = Counter((f["nonpublic"], f["sufficiency"]) for f in named)
    body = [[np] + [x.get((np, s), 0) for s in ("Sufficient", "Partial", "Insufficient")] for np in ("No", "Yes", "Unsure")]
    write_table("OMX1T009", ["Relied on non-public knowledge", "Sufficient", "Partial", "Insufficient"], body,
                "POST HOC: reviews naming a missing label (DEV-007, n = 15), non-public knowledge against owner-rated sufficiency; not in the specification.")
    print("post hoc tables written")


SEALED = OUT / "sealed_candidate" / "candidate_codes_claude.csv"
LEAD_SHEET = OUT / "coding_sheet_study_lead.csv"
LEAD_COLUMNS = ["item", "layer", "missing_label", "definition_shown", "labels_named_in_layer", "already_proposed_also_selected",
                "proposed_labels_shown", "project_title", "datasets_used", "basis_text", "B1_rule_reading", "B2_basis_source", "note", "prefilled"]


def definitions(dd: dict) -> dict[str, str]:
    import html, re
    out = {}
    for field in ("po_miss_domain_reference", "po_miss_purpose_reference", "po_miss_tag_reference"):
        text = re.sub(r"<[^>]+>", "", html.unescape(re.sub(r"<br\s*/?>", "\n", dd_raw_label(field))))
        for line in re.split(r"\n+", text):
            if " – " in line or " — " in line or " – " in line:
                name, definition = re.split(r"\s[–—–]\s", line.strip(), maxsplit=1)
                out[name.strip()] = definition.strip()
    return out


def dd_raw_label(field: str) -> str:
    with roa.DICTIONARY.open(encoding="utf-8-sig") as h:
        for row in csv.reader(h):
            if row and row[0] == field:
                return row[4]
    raise KeyError(field)


def pack() -> None:
    """Study-lead coding sheet: judgement rows blank; rows with no explanation pre-filled N/U by rule.
    Columns that carry the review's non-public and sufficiency answers are left out so that B2 is judged from the
    explanation and the public entry alone."""
    if LEAD_SHEET.exists():
        raise SystemExit("study-lead sheet already exists; not overwritten")
    _, dd = load()
    defs = definitions(dd)
    rows = list(csv.DictReader((OUT / "coding_sheet_blank.csv").open(encoding="utf-8")))
    out = []
    for r in rows:
        name = r["missing_label"]
        definition = defs.get(name) or defs.get(name.replace(" tag", "")) or ""
        if not definition:
            raise SystemExit(f"no definition found for {name}")
        mechanical = not r["basis_text"].strip()
        out.append({**{k: r.get(k, "") for k in LEAD_COLUMNS}, "definition_shown": definition,
                    "B1_rule_reading": "N" if mechanical else "", "B2_basis_source": "U" if mechanical else "", "note": "",
                    "prefilled": "yes: no explanation, so N and U by rule" if mechanical else ""})
    with LEAD_SHEET.open("w", newline="", encoding="utf-8-sig") as h:  # BOM so Excel opens it as UTF-8
        w = csv.DictWriter(h, fieldnames=LEAD_COLUMNS, lineterminator="\n"); w.writeheader(); w.writerows(out)
    print(f"study-lead sheet written: {sum(not r['prefilled'] for r in out)} rows to code, {sum(bool(r['prefilled']) for r in out)} pre-filled")


def compare() -> None:
    lead = {r["item"]: r for r in csv.DictReader(LEAD_SHEET.open(encoding="utf-8-sig"))}
    cand = {r["item"]: r for r in csv.DictReader(SEALED.open(encoding="utf-8"))}
    blank = [i for i, r in lead.items() if not r["B1_rule_reading"].strip() or not r["B2_basis_source"].strip()]
    if blank:
        raise SystemExit(f"uncoded items in the study-lead sheet: {blank}")
    judged = [i for i, r in lead.items() if not r["prefilled"]]
    body, rows = [], []
    for code in ("B1_rule_reading", "B2_basis_source"):
        agree = [i for i in judged if lead[i][code].strip().upper() == cand[i][code]]
        x = Counter((cand[i][code], lead[i][code].strip().upper()) for i in judged)
        body.append([code, len(judged), len(agree), "; ".join(f"{a}->{b}: {n}" for (a, b), n in sorted(x.items()) if a != b) or "none"])
        rows += [[i, code, cand[i][code], lead[i][code].strip().upper()] for i in judged if i not in agree]
    write_table("OMX1T010", ["Code", "Items judged (excludes pre-filled no-explanation rows)", "Agreements", "Disagreements (candidate -> study lead)"], body,
                "Study lead (coded after seeing a summary that disclosed most candidate B1 codes; not fully blind) against candidate codes by Claude Opus 5.5. Counts only.")
    with (OUT / "OMX1T010_disagreements.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h, lineterminator="\n"); w.writerow(["item", "code", "candidate", "study_lead"]); w.writerows(rows)
    print("comparison written: OMX1T010 (+ disagreements list)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "extract"
    {"extract": extract, "posthoc": posthoc, "pack": pack, "compare": compare}.get(mode, lambda: summarise(*sys.argv[2:]))()
