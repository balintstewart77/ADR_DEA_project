"""Build the second adjudicator's training material for the training project (PID 9221).

Plan (ADJ-104): a joint walkthrough, a blind calibration, a discussion, then
the formal secondary review in PID 9227.  Nothing here touches a record that
is, or could become, part of the formal adjudication population.

* **Joint walkthrough** (``training`` group): four pilot records chosen for
  coverage (2019/015 basics; 2022/130 two components; 2021/038 model differs
  with four options; 2024/248 model differs on Domain) and two synthetic
  fixtures for the paths no excluded record has (SYN_ADJ_002 no coder
  majority with an equity tag; SYN_ADJ_003 single set).
* **Blind calibration**, each reviewer completing every Stage 1 before any
  reveal.  Shared by both: six formal records that are never adjudicated
  (model equals the coder majority on every component, a coder split is
  displayed, not owner-reviewed), drawn with a fixed seed.  Secondary only:
  the four remaining model-differs pilot records and two single-set records
  drawn from the keyed worked training examples.  The secondary's twelve sit in
  the ``secondary`` group, the primary's six in ``primary``, each package
  ordered independently; queue order is shuffled with the same fixed seed.

Writes only to ``preregistration_restricted/adjudication_secondary_training/``:
record imports, reveal files, a crosswalk (the key; not for the secondary) and
a receipt.  Prints counts only.  Refuses to overwrite.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from build_formal_import import SEED_PRESENTATION
from build_pilot_timing import EXCLUSIONS, MODEL, split
from build_pilot_training import pilot_cases
from build_route1_component import formal_cases
from prototype_lib import (IMPORTED_DEFAULTS, IMPORT_FORBIDDEN, comparative_components, field_rows, generated_evidence,
                           load_json, model_differing_components, package_case, write_reveal_import)

REPO = Path(__file__).resolve().parents[5]
OUT = REPO / "preregistration_restricted/adjudication_secondary_training"
OWNER_EXPORT = REPO / "preregistration_restricted/owner_responses/exports/DEAValidationStudyPr_DATA_2026-10-13_0737.csv"
MANIFEST = REPO / "preregistration/package/05_training_and_pilot/training_material_record_manifest.csv"
SEED_SECONDARY_TRAINING = 20261017   # draws and queue order for this material; fixed before it was built
JOINT_PILOT = ["2019/015", "2022/130", "2021/038", "2024/248"]
JOINT_SYNTHETIC = ["SYN_ADJ_002", "SYN_ADJ_003"]
BLIND_PILOT = ["2021/056", "2021/063", "2021/103", "2022/034"]
N_SHARED, N_SINGLE = 6, 2
FREE_TEXT = {"adj_case_title", "adj_case_datasets", "adj_source_record_id"}


def model_set(row):
    tags = split(row["cross_cutting_tags"])
    return {"source_type": "fable", "domains": sorted(split(row["substantive_domains"])),
            "purposes": sorted(split(row["analytical_purpose"])),
            "covid": "Applied" if "COVID-19 & Pandemic" in tags else "Not applied",
            "equity": "Applied" if "Demographic disparities / equity tag" in tags else "Not applied"}


def single_set_cases():
    """Keyed worked training examples as model-only cases (no coder ever classified them independently)."""
    keyed = sorted({r["record_id"].strip() for r in csv.DictReader(MANIFEST.open(encoding="utf-8-sig"))
                    if r["material_role"] == "worked_example" and r["keyed_status"] == "keyed"})
    entry = {r["record_id"].strip(): r for r in csv.DictReader(EXCLUSIONS.open(encoding="utf-8-sig")) if r["exclusion_group"] == "training"}
    model = {r["Record ID"].strip(): model_set(r) for r in csv.DictReader(MODEL.open(encoding="utf-8-sig"))}
    keyed = [k for k in keyed if k in entry and k in model]
    return {k: {"record_id": k, "title": entry[k]["title"].strip(), "datasets": entry[k]["datasets_used"].strip(),
                "classifications": [model[k]]} for k in keyed}


def shared_pool():
    """Formal records outside every adjudication route, with a displayed coder split."""
    owner_reviewed = {r["source_record_id"].strip() for r in csv.DictReader(OWNER_EXPORT.open(encoding="utf-8-sig"))
                      if r["redcap_repeat_instrument"] == "project_review"}
    pool = {}
    for c in formal_cases():
        if model_differing_components(c) or c["record_id"] in owner_reviewed:
            continue
        if comparative_components(package_case({**c, "assignment_id": "POOL"}, seed=SEED_PRESENTATION)):
            pool[c["record_id"]] = c
    return pool


def build_rows(entries, group, role, prefix, start=1):
    """entries: [(case, set_role)] in queue order -> import rows, reveal pairs, crosswalk rows."""
    rows, pairs, key = [], [], []
    for n, (case, set_role) in enumerate(entries, start):
        case = {**case, "assignment_id": f"{prefix}{n:02d}"}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["qa_flags"]:
            raise SystemExit(f"{case['assignment_id']} carries a QA flag; nothing written")
        row = {"adj_assignment_id": package["assignment_id"], "redcap_data_access_group": group,
               "adj_source_record_id": case["record_id"], "adj_reviewer_role": role,
               "adj_stage1_package_id": package["package_id"], **generated_evidence(package), **IMPORTED_DEFAULTS}
        for k, v in row.items():
            if k in FREE_TEXT:
                continue
            for token in IMPORT_FORBIDDEN:
                if token in str(v).lower():
                    raise SystemExit(f"{case['assignment_id']} leaks {token!r} in {k}; nothing written")
        rows.append(row)
        pairs.append((case, package))
        key.append({"adj_assignment_id": package["assignment_id"], "group": group, "source_record_id": case["record_id"],
                    "set_role": set_role, "form": "+".join(comparative_components(package)) or "single set"})
    return rows, pairs, key


def write_import(path, rows, names):
    columns = ["adj_assignment_id", "redcap_data_access_group"] + [n for n in names if n != "adj_assignment_id" and any(n in r for r in rows)]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, restval="")
        w.writeheader()
        w.writerows(rows)


def main():
    if OUT.exists() and any(OUT.iterdir()):
        raise SystemExit("the training material already exists; it is built once")
    pilot = {c["record_id"]: c for c in pilot_cases()}
    synthetic = {c["record_id"]: c for c in load_json("cases.json")}
    singles = single_set_cases()
    pool = shared_pool()
    if len(pool) < N_SHARED or len(singles) < N_SINGLE:
        raise SystemExit("not enough eligible cases; nothing written")
    rng = lambda tag: random.Random(f"{SEED_SECONDARY_TRAINING}:{tag}")
    shared = rng("shared").sample(sorted(pool), N_SHARED)
    single = rng("single").sample(sorted(singles), N_SINGLE)

    joint = [(pilot[r], "joint: pilot") for r in JOINT_PILOT] + [(synthetic[r], "joint: synthetic") for r in JOINT_SYNTHETIC]
    secondary = ([(pool[r], "shared calibration") for r in shared] + [(pilot[r], "secondary practice: pilot") for r in BLIND_PILOT]
                 + [(singles[r], "secondary practice: single set") for r in single])
    primary = [(pool[r], "shared calibration") for r in shared]
    rng("order-secondary").shuffle(secondary)
    rng("order-primary").shuffle(primary)

    names = [r[0] for r in field_rows()]
    j_rows, j_pairs, j_key = build_rows(joint, "training", 1, "TRN_J")
    s_rows, s_pairs, s_key = build_rows(secondary, "secondary", 2, "TRN_S")
    p_rows, p_pairs, p_key = build_rows(primary, "primary", 1, "TRN_P")
    unknown = sorted({k for r in j_rows + s_rows + p_rows for k in r if k != "redcap_data_access_group" and k not in names})
    if unknown:
        raise SystemExit("columns absent from the dictionary: " + ", ".join(unknown))

    OUT.mkdir(parents=True, exist_ok=True)
    write_import(OUT / "joint_record_import.csv", j_rows, names)
    write_reveal_import(OUT / "joint_reveal_import.csv", j_pairs)
    write_import(OUT / "blind_record_import.csv", s_rows + p_rows, names)
    write_reveal_import(OUT / "blind_reveal_import.csv", s_pairs + p_pairs)
    with (OUT / "training_crosswalk_KEY.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(j_key[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(j_key + s_key + p_key)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "decision": "ADJ-104",
               "seed": SEED_SECONDARY_TRAINING, "presentation_seed": SEED_PRESENTATION,
               "joint": len(j_rows), "secondary_blind": len(s_rows), "primary_blind": len(p_rows),
               "shared_pool_size": len(pool), "single_set_pool_size": len(singles),
               "forms": {"joint": [k["form"] for k in j_key], "secondary": sorted(k["form"] for k in s_key)},
               "files": {p.name: digest(p) for p in sorted(OUT.glob("*.csv"))}}
    (OUT / "training_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"joint {len(j_rows)} (training group); blind: secondary {len(s_rows)}, primary {len(p_rows)}; "
          f"shared drawn from {len(pool)} eligible; single-set drawn from {len(singles)} keyed examples")
    print("joint forms:", [k["form"] for k in j_key])
    print("secondary forms:", sorted(k["form"] for k in s_key))


JOINT_ADDENDUM = {"TRN_J05": "SYN_TRN_005", "TRN_J06": "SYN_TRN_006", "TRN_J07": "SYN_TRN_007"}  # ADJ-115; fixtures/training_cases.json


def joint_addendum():
    """ADJ-115: replace joint cases J05 and J06 and add J07, leaving every other training file unchanged.

    The new J05 and J06 have the old ones' shapes, so importing them overwrites the
    records already in PID 9221 (J06's old per-label fields are switched off).
    """
    out = {p: OUT / p for p in ("joint_addendum_record_import.csv", "joint_addendum_reveal_import.csv")}
    if any(p.exists() for p in out.values()):
        raise SystemExit("the joint addendum already exists; it is built once")
    fixtures = {c["record_id"]: c for c in load_json("training_cases.json")}
    rows, pairs = [], []
    for aid, rid in JOINT_ADDENDUM.items():
        (row,), (pair,), _ = build_rows([(fixtures[rid], "joint: synthetic")], "training", 1, "TRN_J", start=int(aid[-2:]))
        assert row["adj_assignment_id"] == aid
        rows.append(row)
        pairs.append(pair)
    names = [r[0] for r in field_rows()]
    unknown = sorted({k for r in rows for k in r if k != "redcap_data_access_group" and k not in names})
    if unknown:
        raise SystemExit("columns absent from the dictionary: " + ", ".join(unknown))
    write_import(out["joint_addendum_record_import.csv"], rows, names)
    write_reveal_import(out["joint_addendum_reveal_import.csv"], pairs)
    receipt_path = OUT / "training_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["joint_addendum"] = {"decision": "ADJ-115", "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "records": JOINT_ADDENDUM,
                                 "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.values()}}
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("joint addendum:", ", ".join(JOINT_ADDENDUM), "(training group)")


if __name__ == "__main__":
    import sys
    joint_addendum() if "--joint-addendum" in sys.argv[1:] else main()
