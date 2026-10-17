"""Build route 2 of the adjudication population from the closing owner export (ADJ-106).

Route 2 (protocol 9.1): owner-reviewed records with any Does not fit or Unsure
verdict, a missing-label report, or an owner-indicated public-entry or taxonomy
problem, screened by ``owner_trigger`` on complete reviews from consenting
owners (the agreed policy; ADJ-098 found that route 3 adds nothing).  Records
already in route 1 are not re-imported; they get an owner-evidence addendum
instead (``build_overlap_addendum.py``).

New records follow ADJ_0186 in their own seeded queue (ADJ-070), in blocks of
five numbered on from block 38.  Records in the scratch-coder sample keep their
coder and model classifications; records outside it show the model's set
alone (the single-set form, 9.2).  Owner evidence is never part of Stage 1:
one sheet per owner review is written for use at Stage 2 only, after the
block's Stage 1 is preserved and its reveal imported.

Writes only to ``preregistration_restricted/adjudication_formal/route2/``.
Prints counts only.  Refuses to overwrite.  Withdrawals received by
26 October 2026 are applied by rebuilding from a fresh export (DEV-006).
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from build_formal_import import GROUP, ID_PREFIX, OUT, SEED_PRESENTATION
from build_pilot_timing import MODEL, MODEL_SHA256, split
from build_route1_component import formal_cases, git_commit
from prototype_lib import (IMPORTED_DEFAULTS, IMPORT_FORBIDDEN, comparative_components, field_rows, generated_evidence,
                           model_differing_components, owner_trigger, package_case, reveal_fields, write_reveal_import)

REPO = Path(__file__).resolve().parents[5]
ROUTE2 = OUT / "route2"
OWNER_EXPORT = REPO / "preregistration_restricted/owner_responses/exports/DEAValidationStudyPr_DATA_2026-10-13_0737.csv"
OWNER_EXPORT_SHA256 = "792afed9d6e6b6c0d45be03aa690526a534d43f15bc18cb6b7b6e930617ad169"
REGISTER = REPO / "preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv"
REGISTER_SHA256 = "a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1"
OWNER_DICTIONARY = REPO / "preregistration/package/06_redcap/DEAValidationStudyProjectOwner_DataDictionary_frozen_2026-08-24.csv"
SEED_ROUTE2_QUEUE = 20261018   # route-2 work order; fixed before the queue was built
FIRST_POSITION = 187
FIRST_BLOCK = 39
BLOCK_SIZE = 5
FREE_TEXT = {"adj_case_title", "adj_case_datasets", "adj_source_record_id"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, expected):
    data = path.read_bytes()
    if sha(data) != expected:
        raise SystemExit(f"{path.name} does not match its pinned SHA-256")
    return data


def owner_rows():
    data = pinned(OWNER_EXPORT, OWNER_EXPORT_SHA256)
    return list(csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True)))


def screen():
    """Qualifying complete reviews from consenting owners: record -> [(review row, reasons)]."""
    rows = owner_rows()
    main = {r["owner_id"]: r for r in rows if not r["redcap_repeat_instrument"]}
    consented = {o for o, r in main.items() if r["owner_consent_complete"] == "2" and r["owner_consent"] == "1"}
    out = collections.defaultdict(list)
    for r in rows:
        if r["redcap_repeat_instrument"] != "project_review" or r["project_review_complete"] != "2" or r["owner_id"] not in consented:
            continue
        s = owner_trigger({k: v for k, v in r.items() if k.startswith("po_")})
        if s["qualifies"]:
            out[r["source_record_id"].strip()].append((r, s["reasons"]))
    return out


def model_case(rid, register, model):
    reg = register[rid]
    tags = split(model[rid]["cross_cutting_tags"])
    return {"record_id": rid, "title": reg["Title"].strip(), "datasets": reg["Datasets Used"].strip(),
            "classifications": [{"source_type": "fable", "domains": sorted(split(model[rid]["substantive_domains"])),
                                 "purposes": sorted(split(model[rid]["analytical_purpose"])),
                                 "covid": "Applied" if "COVID-19 & Pandemic" in tags else "Not applied",
                                 "equity": "Applied" if "Demographic disparities / equity tag" in tags else "Not applied"}]}


def route2_cases():
    """(new route-2 cases by record ID, overlap record IDs, screening result)."""
    screened = screen()
    formal = {c["record_id"]: c for c in formal_cases()}
    route1 = {rid for rid, c in formal.items() if model_differing_components(c)}
    pinned(MODEL, MODEL_SHA256)
    register = {r["Record ID"].strip(): r for r in csv.DictReader(pinned(REGISTER, REGISTER_SHA256).decode("utf-8-sig").splitlines(keepends=True))}
    model = {r["Record ID"].strip(): r for r in csv.DictReader(MODEL.open(encoding="utf-8-sig"))}
    new = {}
    for rid in screened:
        if rid in route1:
            continue
        new[rid] = formal[rid] if rid in formal else model_case(rid, register, model)
    return new, sorted(set(screened) & route1), screened


def block_of(position):
    return FIRST_BLOCK + (position - FIRST_POSITION) // BLOCK_SIZE


# ---- owner-evidence sheets -------------------------------------------------

def owner_choices():
    d = list(csv.reader(OWNER_DICTIONARY.open(encoding="utf-8-sig")))
    return {r[0]: dict((c.split(",", 1)[0].strip(), c.split(",", 1)[1].strip()) for c in r[5].split("|") if "," in c)
            for r in d[1:] if r[5].strip()}


def sheet(aid, review, reasons, choices):
    v = lambda f: " ".join((review.get(f) or "").split()).replace("|", "/")
    lab = lambda f: choices.get(f, {}).get(v(f), v(f)) if v(f) else "(no answer)"
    lines = [f"# Owner evidence: {aid}, {review['owner_id']}", "",
             "For Stage 2 only. Open after this record's Stage 1 is preserved and its reveal imported. "
             "One sheet per owner review; no owner majority is formed.", "",
             "Owner evidence describes the actual project, not what the public entry supports. A verdict that rests on "
             "non-public knowledge may point to a project-knowledge gap (family 5) rather than a source error.", "",
             "## Proposed labels", "", "| Component | Proposed label | Describes the actual project? | Basis visible in the entry? | Explanation |",
             "|---|---|---|---|---|"]
    for comp, slots, name in (("d", 4, "Research Domain"), ("p", 2, "Analytical Purpose")):
        for n in range(1, slots + 1):
            label = v(f"prop_{comp}{n:02d}_label")
            if not label:
                continue
            expl = "; ".join(x for x in (v(f"po_{comp}{n:02d}_correct_explain"), v(f"po_{comp}{n:02d}_vis_explain")) if x)
            lines.append(f"| {name} | {label} | {lab(f'po_{comp}{n:02d}_fit')} | {lab(f'po_{comp}{n:02d}_vis')} | {expl} |")
    lines += ["", "## Tag statuses", "", "| Tag | Proposed status | Status correct? | Basis visible? | Explanation |", "|---|---|---|---|---|"]
    for n in (1, 2):
        label = v(f"prop_t{n:02d}_label")
        if label:
            expl = "; ".join(x for x in (v(f"po_t{n:02d}_correct_explain"), v(f"po_t{n:02d}_vis_explain")) if x)
            lines.append(f"| {label} | {lab(f'prop_t{n:02d}_status')} | {lab(f'po_t{n:02d}_correct')} | {lab(f'po_t{n:02d}_vis')} | {expl} |")
    lines += ["", "## Missing labels", ""]
    for field, basis, name in (("po_miss_domains", "po_miss_domain_basis", "Research Domains"),
                               ("po_miss_purposes", "po_miss_purpose_basis", "Analytical Purposes"),
                               ("po_miss_tags", "po_miss_tag_basis", "Tags")):
        picked = [lbl for code, lbl in choices.get(field, {}).items() if v(f"{field}___{code}") == "1"]
        lines.append(f"* {name}: {'; '.join(picked) or 'none selected'}" + (f". Basis: \"{v(basis)}\"" if v(basis) else ""))
    issues = [lbl for code, lbl in choices.get("po_tax_issue", {}).items() if v(f"po_tax_issue___{code}") == "1"]
    lines += ["", "## Overall", "",
              f"* **Public-entry sufficiency:** {lab('po_sufficiency')}" + (f". \"{v('po_suff_explain')}\"" if v("po_suff_explain") else ""),
              f"* **Taxonomy fit:** {lab('po_taxonomy_fit')}" + (f". Issue: {'; '.join(issues)}" if issues else "") + (f". \"{v('po_tax_explain')}\"" if v("po_tax_explain") else ""),
              f"* **Relied on non-public project knowledge:** {lab('po_nonpublic')}" + (f". \"{v('po_nonpublic_note')}\"" if v("po_nonpublic_note") else ""),
              f"* **Other comments:** " + (f"\"{v('po_other_comment')}\"" if v("po_other_comment") else "none"),
              "", "## Why this record is in route 2", "", "Qualifying answers: " + ", ".join(r.replace("_", " ") for r in reasons) + "."]
    return "\n".join(lines) + "\n"


def main():
    if ROUTE2.exists() and any(ROUTE2.iterdir()):
        raise SystemExit("route 2 is already built; rebuild deliberately from a fresh export after withdrawals")
    new, overlap, screened = route2_cases()
    names = [r[0] for r in field_rows()]
    order = sorted(new)
    random.Random(SEED_ROUTE2_QUEUE).shuffle(order)
    rows_out, crosswalk, by_block = [], [], collections.defaultdict(list)
    for i, rid in enumerate(order):
        position = FIRST_POSITION + i
        case = {**new[rid], "assignment_id": f"{ID_PREFIX}{position:04d}"}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["qa_flags"]:
            raise SystemExit("a route-2 record carries QA flags; nothing written")
        row = {"adj_assignment_id": package["assignment_id"], "redcap_data_access_group": GROUP, "adj_source_record_id": rid,
               "adj_reviewer_role": 1, "adj_stage1_package_id": package["package_id"], **generated_evidence(package), **IMPORTED_DEFAULTS}
        for k, val in row.items():
            if k not in FREE_TEXT and any(t in str(val).lower() for t in IMPORT_FORBIDDEN):
                raise SystemExit(f"a masked route-2 row leaks a source token in {k}; nothing written")
        rows_out.append(row)
        by_block[block_of(position)].append((case, package))
        crosswalk.append({"adj_assignment_id": package["assignment_id"], "source_record_id": rid, "queue_position": position,
                          "block": block_of(position), "adj_stage1_package_id": package["package_id"], "route": "2",
                          "in_coder_sample": int(len(case["classifications"]) > 1),
                          "form": "+".join(comparative_components(package)) or "single set",
                          "owner_ids": ";".join(r["owner_id"] for r, _ in screened[rid]),
                          "qualifying_reasons": ";".join(sorted({x for _, rs in screened[rid] for x in rs}))})
    unknown = [k for k in rows_out[0] if k != "redcap_data_access_group" and k not in names]
    if unknown:
        raise SystemExit("columns absent from the dictionary: " + ", ".join(unknown))

    (ROUTE2 / "reveal").mkdir(parents=True, exist_ok=True)
    (ROUTE2 / "owner_evidence").mkdir(exist_ok=True)
    columns = ["adj_assignment_id", "redcap_data_access_group"] + [n for n in names if n != "adj_assignment_id" and any(n in r for r in rows_out)]
    with (ROUTE2 / "adjudication_record_import_route2_primary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, restval="")
        w.writeheader()
        w.writerows(rows_out)
    for block, members in sorted(by_block.items()):
        write_reveal_import(ROUTE2 / "reveal" / f"adjudication_reveal_formal_block_{block:02d}.csv", members)
    with (ROUTE2 / "adjudication_route2_crosswalk.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(crosswalk[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(crosswalk)

    choices = owner_choices()
    route1_ids = {r["source_record_id"]: r["adj_assignment_id"] for r in csv.DictReader((OUT / "adjudication_formal_crosswalk.csv").open(encoding="utf-8"))}
    aid_of = {c["source_record_id"]: c["adj_assignment_id"] for c in crosswalk} | {rid: route1_ids[rid] for rid in overlap}
    sheets = 0
    for rid, reviews in screened.items():
        for review, reasons in reviews:
            (ROUTE2 / "owner_evidence" / f"{aid_of[rid]}_{review['owner_id']}.md").write_text(sheet(aid_of[rid], review, reasons, choices), encoding="utf-8")
            sheets += 1

    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "decision": "ADJ-106",
               "records": len(rows_out), "first_id": rows_out[0]["adj_assignment_id"], "last_id": rows_out[-1]["adj_assignment_id"],
               "blocks": sorted(by_block), "qualifying_records": len(screened), "overlap_with_route1": len(overlap),
               "in_coder_sample": sum(c["in_coder_sample"] for c in crosswalk), "owner_sheets": sheets,
               "seeds": {"route2_queue": SEED_ROUTE2_QUEUE, "presentation": SEED_PRESENTATION},
               "inputs": {"owner_export_sha256": OWNER_EXPORT_SHA256, "register_sha256": REGISTER_SHA256, "model_output_sha256": MODEL_SHA256},
               "record_import_sha256": sha((ROUTE2 / "adjudication_record_import_route2_primary.csv").read_bytes()),
               "crosswalk_sha256": sha((ROUTE2 / "adjudication_route2_crosswalk.csv").read_bytes()),
               "reveal_files": {p.name: sha(p.read_bytes()) for p in sorted((ROUTE2 / "reveal").glob("*.csv"))},
               "generator_commit": git_commit()}
    (ROUTE2 / "route2_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("inputs", "reveal_files") and not k.endswith("sha256")}, indent=2))


def load_route2_block(block):
    """Route-2 counterpart of preserve_block.load_block: reveal file, packages, expected reveal, sources."""
    receipt = json.loads((ROUTE2 / "route2_receipt.json").read_text(encoding="utf-8"))
    crosswalk_path = ROUTE2 / "adjudication_route2_crosswalk.csv"
    if sha(crosswalk_path.read_bytes()) != receipt["crosswalk_sha256"]:
        raise SystemExit("the route-2 crosswalk does not match its receipt")
    name = f"adjudication_reveal_formal_block_{block:02d}.csv"
    reveal_bytes = (ROUTE2 / "reveal" / name).read_bytes()
    if sha(reveal_bytes) != receipt["reveal_files"].get(name):
        raise SystemExit(f"{name} does not match the route-2 receipt")
    members = [r for r in csv.DictReader(crosswalk_path.open(encoding="utf-8")) if r["block"] == str(block)]
    if not members:
        raise SystemExit(f"no route-2 block {block}")
    new, _, _ = route2_cases()
    packages, expected, sources = {}, {}, {}
    for m in members:
        aid = m["adj_assignment_id"]
        case = {**new[m["source_record_id"]], "assignment_id": aid}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["package_id"] != m["adj_stage1_package_id"]:
            raise SystemExit(f"{aid}: rebuilt package differs from the route-2 crosswalk")
        packages[aid], expected[aid], sources[aid] = package, reveal_fields(case, package), m["source_record_id"]
    return name, reveal_bytes, packages, expected, sources


if __name__ == "__main__":
    main()
