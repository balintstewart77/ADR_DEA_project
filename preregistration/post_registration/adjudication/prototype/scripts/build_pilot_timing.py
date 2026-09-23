"""Build a Stage 1 timing package from the ten permanently excluded pilot records (ADJ-041).

The pilot records are excluded from every validation analysis (protocol §5.1),
so timing the instrument on them spends no formal case.  Each has a real title
and datasets-used entry, the frozen production output and three complete coder
classifications, entered under candidate 0.3, whose Domain, Purpose and tag
codes are identical to the frozen 0.7 dictionary.

Inputs are read-only.  Output goes only to the git-ignored restricted folder,
because it contains coder classifications, as the coder export itself does.
Printed output is aggregate only: no record identifier, content or source
mapping, so the adjudicator's view of each case stays masked.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from prototype_lib import (COMPONENTS, DOMAINS, IMPORTED_DEFAULTS, IMPORT_FORBIDDEN, PURPOSES,
                           comparative_components, field_rows, generated_evidence, package_case,
                           write_reveal_import, no_majority_components, package_stratum, assignment_packages)

REPO = Path(__file__).resolve().parents[5]
EXCLUSIONS = REPO / "preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv"
EXCLUSIONS_SHA256 = "cf36e6d34375d0e68bac31df8169207fc0602bc7291a64e995b9cd86141413a6"
MODEL = REPO / "analysis/outputs_classified_20260702_fable5/layer_classifications.csv"
MODEL_SHA256 = "6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299"
EXPORT = REPO / "preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv"
OUT = REPO / "preregistration_restricted/adjudication_pilot_timing"
PILOT_INSTRUMENT = "redcap-candidate-0.3"
# Fields holding real public-register text, which may legitimately contain
# words such as "reveal"; every generated field is still leak-checked.
FREE_TEXT = {"adj_case_title", "adj_case_datasets"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split(value):
    return {x.strip() for x in (value or "").replace(";", "|").split("|") if x.strip()}


def main():
    for path, expected in ((EXCLUSIONS, EXCLUSIONS_SHA256), (MODEL, MODEL_SHA256)):
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"{path.name}: SHA-256 {actual} does not match the recorded {expected}")

    pilot = [r for r in csv.DictReader(EXCLUSIONS.open(encoding="utf-8-sig")) if r["exclusion_group"] == "pilot"]
    pilot_ids = sorted(r["record_id"].strip() for r in pilot)
    if len(pilot_ids) != 10:
        raise SystemExit(f"expected 10 pilot records, found {len(pilot_ids)}")

    model = {}
    for r in csv.DictReader(MODEL.open(encoding="utf-8-sig")):
        rid = r["Record ID"].strip()
        if rid in pilot_ids:
            tags = split(r["cross_cutting_tags"])
            model[rid] = {"domains": sorted(split(r["substantive_domains"])), "purposes": sorted(split(r["analytical_purpose"])),
                          "covid": "Applied" if "COVID-19 & Pandemic" in tags else "Not applied",
                          "equity": "Applied" if "Demographic disparities / equity tag" in tags else "Not applied"}

    coders = collections.defaultdict(list)
    for r in csv.DictReader(EXPORT.open(encoding="utf-8-sig")):
        rid = r["source_record_id"].strip()
        if rid in pilot_ids and r["record_kind"] != "1":
            if r["instrument_ver"] != PILOT_INSTRUMENT or r["scratch_coder_complete"] != "2":
                raise SystemExit("a pilot row is not a complete candidate-0.3 classification")
            coders[rid].append(r)

    cases, excluded_qa, not_eligible, no_majority = [], 0, 0, 0
    patterns = collections.Counter()
    for rid in pilot_ids:
        rows = coders[rid]
        if len(rows) != 3 or rid not in model:
            raise SystemExit("a pilot record lacks three coder rows or a model output")
        titles = {r["project_title"].strip() for r in rows}; datasets = {r["datasets_used"].strip() for r in rows}
        if len(titles) != 1 or len(datasets) != 1:
            raise SystemExit("coders were not shown one identical public entry for a pilot record")
        classifications = [{"source_type": "fable", **model[rid]}]
        for n, r in enumerate(rows):
            classifications.append({"source_type": "scratch", "source_id": r["reviewer_id"].strip(),
                                    "domains": [DOMAINS[i - 1] for i in range(1, 13) if r.get(f"sc_domains___{i}") == "1"],
                                    "purposes": [PURPOSES[i - 1] for i in range(1, 9) if r.get(f"sc_purposes___{i}") == "1"],
                                    "covid": "Applied" if r.get("sc_covid") == "1" else "Not applied",
                                    "equity": "Applied" if r.get("sc_equity") == "1" else "Not applied"})
        # Route-1-like eligibility: the model differs from the labelwise
        # two-of-three human reference on any component (§9.1).
        differs = []
        for key, vocab in (("domains", DOMAINS), ("purposes", PURPOSES)):
            majority = {lab for lab in vocab if sum(lab in c[key] for c in classifications[1:]) >= 2}
            if not majority: no_majority += 1
            if majority != set(model[rid][key]): differs.append(key)
        for key in ("covid", "equity"):
            if (sum(c[key] == "Applied" for c in classifications[1:]) >= 2) != (model[rid][key] == "Applied"): differs.append(key)
        if not differs:
            not_eligible += 1
            continue
        case = {"record_id": rid, "assignment_id": f"PILOT_ADJ_{len(cases) + 1:03d}", "title": titles.pop(),
                "datasets": datasets.pop(), "classifications": classifications}
        package = package_case(case)
        if package["qa_flags"]:
            excluded_qa += 1
            continue
        patterns[tuple(comparative_components(package))] += 1
        cases.append((case, package))

    names = [x[0] for x in field_rows()]
    rows_out = []
    # One record per case-reviewer assignment (ADJ-058): the second adjudicator
    # works the same cases in their own group, from their own independently
    # ordered package, so neither sees the other's answers and option letters
    # do not line up between them.
    assignments = [(case, role, group, package) for case, _ in cases for role, group, package in assignment_packages(case)]
    for case, role, group, package in assignments:
        row = {"adj_assignment_id": package["assignment_id"], "redcap_data_access_group": group,
               "adj_source_record_id": case["record_id"], "adj_reviewer_role": role,
               "adj_stage1_package_id": package["package_id"], **generated_evidence(package), **IMPORTED_DEFAULTS}
        for key, value in row.items():
            if key in FREE_TEXT: continue
            for token in IMPORT_FORBIDDEN:
                if token in str(value).lower():
                    raise SystemExit(f"masked pilot row leaks {token!r} in {key}")
        rows_out.append(row)
    unknown = [k for k in rows_out[0] if k != "redcap_data_access_group" and k not in names]
    if unknown:
        raise SystemExit("columns absent from the candidate dictionary: " + ", ".join(unknown))

    OUT.mkdir(parents=True, exist_ok=True)
    columns = ["adj_assignment_id", "redcap_data_access_group"] + [n for n in names if n in rows_out[0] and n != "adj_assignment_id"]
    with (OUT / "adjudication_record_import_pilot_timing.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows_out)
    # The reveal is a separate file, to import only after Stage 1 is complete
    # for these cases.  It is never printed.
    write_reveal_import(OUT / "adjudication_reveal_import_pilot_timing.csv", [(case, package) for case, _, _, package in assignments])
    # One file per reviewer as well.  The combined file would put a reviewer's
    # source mapping into their records before they have done Stage 1, which is
    # the order the whole blind stage depends on being able to evidence.
    for wanted in ("primary", "secondary"):
        write_reveal_import(OUT / f"adjudication_reveal_import_pilot_timing_{wanted}.csv",
                            [(case, package) for case, _, group, package in assignments if group == wanted])
    # The analytic stratum (ADJ-038) travels beside the import, not inside it:
    # nothing on the form reads it, and a hidden field saying the coders did
    # not converge would be source information in the reviewer's own export.
    strata = collections.Counter()
    with (OUT / "adjudication_stratum_pilot_timing.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["adj_assignment_id", "stratum", "no_majority_components"])
        w.writeheader()
        for case, role, group, package in assignments:
            stratum = package_stratum(case, package)
            if role == 1: strata[stratum] += 1
            w.writerow({"adj_assignment_id": package["assignment_id"], "stratum": stratum,
                        "no_majority_components": ";".join(no_majority_components(case))})
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "purpose": "Stage 1 timing on permanently excluded pilot records (ADJ-041); not adjudication evidence",
               "inputs": {"exclusion_list_sha256": EXCLUSIONS_SHA256, "model_output_sha256": MODEL_SHA256,
                          "coder_export_sha256": sha256(EXPORT), "pilot_instrument": PILOT_INSTRUMENT},
               "pilot_records": len(pilot_ids), "not_eligible": not_eligible, "excluded_for_qa_flags": excluded_qa,
               "timing_cases": len(cases), "assignment_rows": len(rows_out), "components_with_no_majority_label": no_majority,
               "stratum_counts": {"1_standard": strata[1], "2_mixed": strata[2], "3_no_majority_only": strata[3]},
               "differing_component_patterns": {"+".join(k): v for k, v in sorted(patterns.items())}}
    (OUT / "pilot_timing_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "inputs"}, indent=2))


if __name__ == "__main__":
    main()
