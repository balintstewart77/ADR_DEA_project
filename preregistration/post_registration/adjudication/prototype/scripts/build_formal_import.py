"""Build the primary adjudicator's formal record import for the route-1 records.

Route 1 only: records added later by owner screening and coding or cleaning
flags (routes 2 and 3) are appended after these, in their own queue, and do
not renumber anything here (ADJ-070).

Inputs are the three hash-pinned files the route-1 component was built from,
plus that component, which the eligible set here must reproduce exactly.
Output goes only to the git-ignored restricted folder:

* the masked Stage 1 record import, one row per record, primary group only;
* one reveal file per block of five, in queue order, each imported only after
  that block's Stage 1 is affirmed (ADJ-060, ADJ-062);
* a crosswalk and stratum file that travel beside the import, never inside it;
* a receipt with every seed, hash and count needed to regenerate the lot.

Assignment IDs follow the queue, so the work order is simply ADJ_0001 upwards
and a block is five consecutive IDs.  Printed output is aggregate only.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from build_route1_component import OUT as COMPONENT, formal_cases, git_commit, input_hashes
from prototype_lib import (IMPORTED_DEFAULTS, IMPORT_FORBIDDEN, ROOT, field_rows, generated_evidence,
                           model_differing_components, no_majority_components, package_case,
                           package_stratum, write_reveal_import)

REPO = Path(__file__).resolve().parents[5]
OUT = REPO / "preregistration_restricted/adjudication_formal"
DICTIONARY = ROOT / "instruments" / "adjudication_stage1_candidate.csv"
# The ADJ-082 amendment: ADJ-078 with mechanism vocabulary mechvocab-0.2, which
# changes only the six mechanism dropdowns' choices.  ADJ-078 was 66d9f3a4...;  The import is refused against any other
# dictionary, so a later change to the instrument has to be made here on
# purpose.  The first 186-record import was built against the ADJ-069 version,
# 52b63541...adc15305, as its receipt records.
DICTIONARY_SHA256 = "5e9476fd0e5f869542d6a0185b3d91280125e2913326e16668142a250ada9d37"
# Its data-quality rules, pinned alongside: the two files are one instrument.
RULES = ROOT / "instruments" / "adjudication_data_quality_rules.csv"
RULES_SHA256 = "4c4f9f9f41d0d41d219b581017724982c120da1aefcca6d65fd47bf62802ede1"
# Implementation seeds, not preregistered (build spec, "Presentation/queue
# seeds"); fixed here before any formal package existed (ADJ-070).
SEED_PRESENTATION = 20260921   # option order within a package; the generator default the pilot used
SEED_PRIMARY_QUEUE = 20260925  # work order; distinct from the audit and secondary-queue seeds
BLOCK_SIZE = 5
ID_PREFIX = "ADJ_"
GROUP = "primary"
FREE_TEXT = {"adj_case_title", "adj_case_datasets", "adj_source_record_id"}


def primary_queue(record_ids, seed=SEED_PRIMARY_QUEUE):
    """Stable sort, then one seeded shuffle: the order the primary works in."""
    order = sorted(record_ids)
    random.Random(seed).shuffle(order)
    return order


def assignment_id(position):
    return f"{ID_PREFIX}{position:04d}"


def block_of(position):
    return (position - 1) // BLOCK_SIZE + 1


def component_eligible():
    """Eligible IDs from the route-1 component, and the file's hash."""
    raw = COMPONENT.read_bytes()
    rows = csv.DictReader(line for line in raw.decode("utf-8").splitlines() if not line.startswith("#"))
    return {r["source_record_id"] for r in rows if r["route1_eligible"] == "1"}, hashlib.sha256(raw).hexdigest()


def main():
    dictionary_hash = hashlib.sha256(DICTIONARY.read_bytes()).hexdigest()
    if dictionary_hash != DICTIONARY_SHA256:
        raise SystemExit("the dictionary on disk is not the ADJ-069 amendment this import is pinned to")
    rules_hash = hashlib.sha256(RULES.read_bytes()).hexdigest()
    if rules_hash != RULES_SHA256:
        raise SystemExit("the data-quality rules on disk are not the ADJ-069 amendment this import is pinned to")
    hashes = input_hashes()
    cases = {c["record_id"]: c for c in formal_cases()}
    eligible = {rid for rid, c in cases.items() if model_differing_components(c)}
    recorded, component_hash = component_eligible()
    if eligible != recorded or len(eligible) != 186:
        raise SystemExit("the eligible set does not reproduce the route-1 component")

    names = [row[0] for row in field_rows()]
    rows_out, crosswalk, pairs = [], [], []
    strata = collections.Counter()
    for position, rid in enumerate(primary_queue(eligible), 1):
        case = {**cases[rid], "assignment_id": assignment_id(position)}
        package = package_case(case, seed=SEED_PRESENTATION)
        if package["qa_flags"]:
            raise SystemExit("a route-1 record carries QA flags; no output written")
        row = {"adj_assignment_id": package["assignment_id"], "redcap_data_access_group": GROUP,
               "adj_source_record_id": rid, "adj_reviewer_role": 1,
               "adj_stage1_package_id": package["package_id"], **generated_evidence(package), **IMPORTED_DEFAULTS}
        for key, value in row.items():
            if key in FREE_TEXT:
                continue
            for token in IMPORT_FORBIDDEN:
                if token in str(value).lower():
                    raise SystemExit(f"a masked row leaks {token!r} in {key}; no output written")
        rows_out.append(row)
        pairs.append((position, case, package))
        stratum = package_stratum(case, package)
        strata[stratum] += 1
        crosswalk.append({"adj_assignment_id": package["assignment_id"], "source_record_id": rid,
                          "queue_position": position, "block": block_of(position),
                          "adj_stage1_package_id": package["package_id"], "stratum": stratum,
                          "route1_components": ";".join(model_differing_components(case)),
                          "no_majority_components": ";".join(no_majority_components(case))})
    unknown = [k for k in rows_out[0] if k != "redcap_data_access_group" and k not in names]
    if unknown:
        raise SystemExit("columns absent from the dictionary: " + ", ".join(unknown))
    if [strata[i] for i in (1, 2, 3)] != [143, 21, 22]:
        raise SystemExit("strata differ from the route-1 component; no output written")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reveal").mkdir(exist_ok=True)
    columns = ["adj_assignment_id", "redcap_data_access_group"] + [n for n in names if n in rows_out[0] and n != "adj_assignment_id"]
    with (OUT / "adjudication_record_import_formal_primary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows_out)
    blocks = collections.defaultdict(list)
    for position, case, package in pairs:
        blocks[block_of(position)].append((case, package))
    for block, members in sorted(blocks.items()):
        write_reveal_import(OUT / "reveal" / f"adjudication_reveal_formal_block_{block:02d}.csv", members)
    with (OUT / "adjudication_formal_crosswalk.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(crosswalk[0]))
        w.writeheader()
        w.writerows(crosswalk)

    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    import_hash = digest(OUT / "adjudication_record_import_formal_primary.csv")
    # Every output is hashed, so preserve_block.py can refuse a reveal file or
    # crosswalk that has been edited or regenerated since this receipt.
    reveal_hashes = {p.name: digest(p) for p in sorted((OUT / "reveal").glob("adjudication_reveal_formal_block_*.csv"))}
    if len(reveal_hashes) != len(blocks):
        raise SystemExit("the reveal folder holds files this build did not write")
    receipt = {"generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "artifact": "primary formal record import, route-1 records only (ADJ-070)",
               "routes_2_and_3": "outstanding; appended later in their own queue",
               "records": len(rows_out), "blocks": len(blocks), "block_size": BLOCK_SIZE,
               "first_id": assignment_id(1), "last_id": assignment_id(len(rows_out)),
               "stratum_counts": {str(i): strata[i] for i in (1, 2, 3)},
               "seeds": {"presentation": SEED_PRESENTATION, "primary_queue": SEED_PRIMARY_QUEUE},
               "queue_algorithm": "sort source Record IDs; Python random.Random(seed).shuffle",
               "dictionary_sha256": dictionary_hash, "data_quality_rules_sha256": rules_hash,
               "route1_component_sha256": component_hash,
               "record_import_sha256": import_hash,
               "crosswalk_sha256": digest(OUT / "adjudication_formal_crosswalk.csv"),
               "reveal_files": reveal_hashes, **hashes, "generator_commit": git_commit()}
    (OUT / "formal_import_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in receipt.items() if not k.endswith("sha256") and k != "reveal_files"}, indent=2))


if __name__ == "__main__":
    main()
