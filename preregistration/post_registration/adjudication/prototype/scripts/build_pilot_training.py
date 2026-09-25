"""Build a joint-training package from the four pilot records that are not eligible.

The ten pilot records are permanently excluded from every validation analysis
(protocol §5.1).  Six are route-1-like eligible, because the model differs
from the coders' two-of-three reference somewhere; those are reserved for the
second adjudicator's blind calibration run (ADJ-058) and are never written
here.  The other four have the model agreeing with that reference, while the
coders still split among themselves, so they render as ordinary comparative
records: easy, real cases for the study lead and second adjudicator to work
through together before the blind run.

Output goes only to the git-ignored restricted folder: a record import in its
own `training` Data Access Group, so these records can never be confused with
the calibration records, and a reveal file for the same four.  Printed output
is aggregate only.
"""
from __future__ import annotations

import collections
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from build_pilot_timing import (EXCLUSIONS, EXCLUSIONS_SHA256, EXPORT, FREE_TEXT, MODEL, MODEL_SHA256,
                                PILOT_INSTRUMENT, sha256, split)
from prototype_lib import (DOMAINS, IMPORTED_DEFAULTS, IMPORT_FORBIDDEN, PURPOSES, comparative_components,
                           field_rows, generated_evidence, model_differing_components, package_case,
                           write_reveal_import)

REPO = Path(__file__).resolve().parents[5]
OUT = REPO / "preregistration_restricted/adjudication_pilot_training"
GROUP = "training"
ID_PREFIX = "PILOT_TRN_"


def pilot_cases():
    """All ten pilot records as cases: frozen model output plus three coders."""
    for path, expected in ((EXCLUSIONS, EXCLUSIONS_SHA256), (MODEL, MODEL_SHA256)):
        if sha256(path) != expected:
            raise SystemExit(f"{path.name} does not match its pinned SHA-256")
    pilot = sorted(r["record_id"].strip() for r in csv.DictReader(EXCLUSIONS.open(encoding="utf-8-sig"))
                   if r["exclusion_group"] == "pilot")
    if len(pilot) != 10:
        raise SystemExit(f"expected 10 pilot records, found {len(pilot)}")
    model = {}
    for r in csv.DictReader(MODEL.open(encoding="utf-8-sig")):
        rid = r["Record ID"].strip()
        if rid in pilot:
            tags = split(r["cross_cutting_tags"])
            model[rid] = {"domains": sorted(split(r["substantive_domains"])), "purposes": sorted(split(r["analytical_purpose"])),
                          "covid": "Applied" if "COVID-19 & Pandemic" in tags else "Not applied",
                          "equity": "Applied" if "Demographic disparities / equity tag" in tags else "Not applied"}
    coders = collections.defaultdict(list)
    for r in csv.DictReader(EXPORT.open(encoding="utf-8-sig")):
        rid = r["source_record_id"].strip()
        if rid in pilot and r["record_kind"] != "1":
            if r["instrument_ver"] != PILOT_INSTRUMENT or r["scratch_coder_complete"] != "2":
                raise SystemExit("a pilot row is not a complete candidate-0.3 classification")
            coders[rid].append(r)
    cases = []
    for rid in pilot:
        rows = coders[rid]
        if len(rows) != 3 or rid not in model:
            raise SystemExit("a pilot record lacks three coder rows or a model output")
        titles = {r["project_title"].strip() for r in rows}
        datasets = {r["datasets_used"].strip() for r in rows}
        if len(titles) != 1 or len(datasets) != 1:
            raise SystemExit("coders were not shown one identical public entry for a pilot record")
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


def main():
    cases = pilot_cases()
    eligible = [c for c in cases if model_differing_components(c)]
    training = [c for c in cases if not model_differing_components(c)]
    if (len(eligible), len(training)) != (6, 4):
        raise SystemExit("expected 6 eligible and 4 non-eligible pilot records; nothing written")

    names = [r[0] for r in field_rows()]
    rows_out, pairs = [], []
    for n, case in enumerate(training, 1):
        case = {**case, "assignment_id": f"{ID_PREFIX}{n:03d}"}
        package = package_case(case)
        if package["qa_flags"] or not comparative_components(package):
            raise SystemExit("a training record is QA-flagged or has no displayed difference; nothing written")
        row = {"adj_assignment_id": package["assignment_id"], "redcap_data_access_group": GROUP,
               "adj_source_record_id": case["record_id"], "adj_reviewer_role": 1,
               "adj_stage1_package_id": package["package_id"], **generated_evidence(package), **IMPORTED_DEFAULTS}
        for key, value in row.items():
            if key in FREE_TEXT: continue
            for token in IMPORT_FORBIDDEN:
                if token in str(value).lower():
                    raise SystemExit(f"a masked training row leaks {token!r} in {key}")
        rows_out.append(row)
        pairs.append((case, package))
    unknown = [k for k in rows_out[0] if k != "redcap_data_access_group" and k not in names]
    if unknown:
        raise SystemExit("columns absent from the dictionary: " + ", ".join(unknown))

    OUT.mkdir(parents=True, exist_ok=True)
    columns = ["adj_assignment_id", "redcap_data_access_group"] + [n for n in names if n in rows_out[0] and n != "adj_assignment_id"]
    with (OUT / "adjudication_record_import_pilot_training.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns); w.writeheader(); w.writerows(rows_out)
    write_reveal_import(OUT / "adjudication_reveal_import_pilot_training.csv", pairs)
    patterns = collections.Counter("+".join(comparative_components(p)) for _, p in pairs)
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "purpose": "joint training on the four non-eligible pilot records; the six eligible stay reserved for blind calibration",
               "records": len(rows_out), "group": GROUP, "first_id": rows_out[0]["adj_assignment_id"],
               "last_id": rows_out[-1]["adj_assignment_id"], "displayed_differing_components": dict(patterns),
               "inputs": {"exclusion_list_sha256": EXCLUSIONS_SHA256, "model_output_sha256": MODEL_SHA256,
                          "coder_export_sha256": sha256(EXPORT)}}
    (OUT / "pilot_training_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if k != "inputs"}, indent=2))


if __name__ == "__main__":
    main()
