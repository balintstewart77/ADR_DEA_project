"""Build the restricted route-1 component; this is not the eligibility manifest.

Inputs are read-only. Routes 2 and 3 remain outstanding. Printed output contains
aggregates only; the record-level component and receipt stay git-ignored.
"""
from __future__ import annotations

import collections
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from build_pilot_timing import (EXCLUSIONS, EXCLUSIONS_SHA256, EXPORT, MODEL,
                                MODEL_SHA256, sha256, split)
from prototype_lib import (DOMAINS, PURPOSES, comparative_components,
                           model_differing_components, no_majority_components,
                           package_case, package_stratum)

REPO = Path(__file__).resolve().parents[5]
OUT = REPO / "preregistration_restricted/adjudication_route1_component.csv"
INSTRUMENT = "redcap-candidate-0.7"
# Pinned from the first route-1 build, 2026-09-24, so every later build reads
# the same coder snapshot the 186 was counted on.
EXPORT_SHA256 = "29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d"
# The component depends on the three inputs, not on the REDCap dictionary, so
# it records no dictionary hash: one would be read as the version it was built
# against when nothing in it was.
COLUMNS = ("source_record_id", "route1_eligible", "route1_components",
           "no_majority_components", "stratum", "displayed_differing_components",
           "qa_flagged", "model_output_sha256",
           "coder_export_sha256", "exclusion_list_sha256", "generator_commit")


def component_values(case, package):
    """Record-level route-1 fields, with QA-blocked records never eligible."""
    if package["qa_flags"]:
        differing, empty, displayed, stratum = [], [], [], ""
    else:
        differing = model_differing_components(case)
        empty = no_majority_components(case)
        displayed = comparative_components(package)
        stratum = package_stratum(case, package) if differing else ""
    return {"source_record_id": case["record_id"], "route1_eligible": int(bool(differing)),
            "route1_components": ";".join(differing),
            "no_majority_components": ";".join(empty), "stratum": stratum,
            "displayed_differing_components": ";".join(displayed),
            "qa_flagged": int(bool(package["qa_flags"]))}


def input_hashes():
    """Hash-check the three inputs; refuse to read anything that has moved."""
    hashes = {"exclusion_list_sha256": sha256(EXCLUSIONS),
              "model_output_sha256": sha256(MODEL),
              "coder_export_sha256": sha256(EXPORT)}
    for name, expected in (("exclusion_list_sha256", EXCLUSIONS_SHA256),
                           ("model_output_sha256", MODEL_SHA256),
                           ("coder_export_sha256", EXPORT_SHA256)):
        if hashes[name] != expected:
            raise SystemExit(f"{name} does not match the pinned SHA-256")
    return hashes


def formal_cases():
    """Every non-excluded formal record as a case: frozen model output plus three coders.

    Shared by the route-1 component and the formal record import, so the two
    cannot disagree about which classifications a record carries.
    """
    excluded = {r["record_id"].strip() for r in csv.DictReader(EXCLUSIONS.open(encoding="utf-8-sig"))}
    coders = collections.defaultdict(list)
    for r in csv.DictReader(EXPORT.open(encoding="utf-8-sig")):
        rid = r["source_record_id"].strip()
        if r["record_kind"] == "1" and rid not in excluded:
            if r["scratch_coder_complete"] != "2" or r["instrument_ver"] != INSTRUMENT:
                raise SystemExit("a non-excluded formal coder row is incomplete or has the wrong instrument version")
            coders[rid].append(r)

    model = {}
    for r in csv.DictReader(MODEL.open(encoding="utf-8-sig")):
        rid = r["Record ID"].strip()
        if rid in coders:
            if rid in model:
                raise SystemExit("duplicate frozen model output for a formal record")
            tags = split(r["cross_cutting_tags"])
            model[rid] = {"domains": sorted(split(r["substantive_domains"])),
                          "purposes": sorted(split(r["analytical_purpose"])),
                          "covid": "Applied" if "COVID-19 & Pandemic" in tags else "Not applied",
                          "equity": "Applied" if "Demographic disparities / equity tag" in tags else "Not applied"}

    cases = []
    for rid in sorted(coders):
        rows = coders[rid]
        if len(rows) != 3 or len({r["reviewer_id"].strip() for r in rows}) != 3 or rid not in model:
            raise SystemExit("a formal record lacks exactly three coder rows or a model output")
        titles = {r["project_title"].strip() for r in rows}
        datasets = {r["datasets_used"].strip() for r in rows}
        if len(titles) != 1 or len(datasets) != 1:
            raise SystemExit("coders were not shown one identical public entry for a formal record")
        classifications = [{"source_type": "fable", **model[rid]}]
        for r in rows:
            classifications.append({"source_type": "scratch", "source_id": r["reviewer_id"].strip(),
                                    "domains": [DOMAINS[i - 1] for i in range(1, 13) if r.get(f"sc_domains___{i}") == "1"],
                                    "purposes": [PURPOSES[i - 1] for i in range(1, 9) if r.get(f"sc_purposes___{i}") == "1"],
                                    "covid": "Applied" if r.get("sc_covid") == "1" else "Not applied",
                                    "equity": "Applied" if r.get("sc_equity") == "1" else "Not applied"})
        cases.append({"record_id": rid, "title": titles.pop(), "datasets": datasets.pop(),
                      "classifications": classifications})
    return cases


def git_commit():
    """Short commit, marked dirty when the generator has uncommitted changes."""
    return subprocess.check_output(["git", "describe", "--always", "--dirty", "--exclude=*"], cwd=REPO, text=True).strip()


def main():
    hashes = input_hashes()
    cases = formal_cases()
    commit = git_commit()
    output = []
    strata = collections.Counter()
    qa_count = 0
    eligible_count = 0
    for case in cases:
        package = package_case({**case, "assignment_id": "ROUTE1_COMPONENT"})
        values = component_values(case, package)
        qa_count += values["qa_flagged"]
        if values["qa_flagged"]:
            continue
        eligible_count += values["route1_eligible"]
        if values["route1_eligible"]:
            strata[values["stratum"]] += 1
        output.append({**values, **hashes, "generator_commit": commit})

    # These are independently logged route-1 aggregates, not a manifest N.
    if eligible_count != 186 or [strata[i] for i in (1, 2, 3)] != [143, 21, 22]:
        raise SystemExit("route-1 count or corrected strata differ from recorded aggregates; no output written")
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "artifact": "route-1 component only; not the eligibility manifest",
               "routes_2_and_3": "outstanding", "formal_records_seen": len(cases),
               "component_rows": len(output),
               "route1_eligible": eligible_count, "qa_flagged": qa_count,
               "stratum_counts": {str(i): strata[i] for i in (1, 2, 3)},
               **hashes, "generator_commit": commit}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        f.write("# Route-1 component only; not the eligibility manifest; routes 2 and 3 outstanding.\n")
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(output)
    OUT.with_suffix(".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k not in hashes}, indent=2))


if __name__ == "__main__":
    main()
