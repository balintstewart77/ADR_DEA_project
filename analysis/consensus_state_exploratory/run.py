"""Consensus-state exploratory analysis: model agreement by human consensus state.

Reads the shared Stage A data (panels, model, population authorities) without
modification and computes all outcomes specified in the instruction.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from random import Random
from typing import Any

import numpy
import pandas

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.config import CODERS
from analysis.scratch_coder_stage_a.load import (
    resolve_manifest_row,
    verify_authorities,
)
from analysis.scratch_coder_stage_a.panels import build_stage_a_data, dimension_panels
from analysis.validation.bootstrap import (
    BootstrapResult,
    StatisticValue,
    bootstrap_joint,
    percentile,
)

SEED = 20260918
REPLICATES = 2000
MIN_VALID = 1800
POPULATIONS = ("baseline", "hard_case")
DIMENSIONS = ("Research Domains", "Analytical Purposes")
UNCLEAR = "Unclear from Register Entry"

OUTPUT_DIR = Path(__file__).resolve().parent
RESTRICTED_DIR = ROOT / "preregistration_restricted" / "consensus_state_exploratory"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def majority_set(labels_by_coder: list[frozenset[str]]) -> frozenset[str]:
    counts: Counter[str] = Counter()
    for s in labels_by_coder:
        for label in s:
            counts[label] += 1
    return frozenset(label for label, n in counts.items() if n >= 2)


def classify_state(
    coder_sets: list[frozenset[str]], maj: frozenset[str]
) -> str:
    if not maj:
        return "S4"
    substantive = maj - {UNCLEAR}
    if not substantive and UNCLEAR in maj:
        return "S3"
    if all(s == coder_sets[0] for s in coder_sets[1:]) and substantive:
        return "S1"
    return "S2"


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def set_relationship(model: frozenset[str], ref: frozenset[str]) -> str:
    if model == ref:
        return "exact"
    if not (model & ref):
        return "disjoint"
    if model > ref:
        return "strict_superset"
    if model < ref:
        return "strict_subset"
    return "partial_overlap"


def build_record_data(data, population: str, dimension: str):
    if population == "baseline":
        record_ids = data.baseline_ids
    else:
        record_ids = data.hard_case_ids

    field = {"Research Domains": "domains", "Analytical Purposes": "purposes"}[dimension]
    rows = data.responses[data.responses["record_id"].isin(record_ids)]
    grouped = {rid: group for rid, group in rows.groupby("record_id")}

    records = []
    for rid in sorted(record_ids):
        group = grouped[rid]
        by_coder = {r["coder"]: r for r in group.to_dict("records")}
        coder_sets = [by_coder[c][field] for c in CODERS]
        model_set = data.model[rid][dimension]
        if isinstance(model_set, (int, float)):
            raise ValueError(f"Model set is not a frozenset for {dimension}")
        maj = majority_set(coder_sets)
        state = classify_state(coder_sets, maj)
        records.append({
            "record_id": rid,
            "coder_sets": coder_sets,
            "model_set": model_set,
            "majority_set": maj,
            "state": state,
        })
    return records


def check_3a_3b(data, population: str, dimension: str, record_ids: frozenset[str]):
    field = {"Research Domains": "domains", "Analytical Purposes": "purposes"}[dimension]
    rows = data.responses[data.responses["record_id"].isin(record_ids)]

    for _, row in rows.iterrows():
        label_set = row[field]
        if label_set is None or len(label_set) == 0:
            raise ValueError(f"Empty coder set: {population}/{dimension}/{row['coder']}")
        if UNCLEAR in label_set and len(label_set) > 1:
            raise ValueError(
                f"Unclear co-occurs with substantive: {population}/{dimension}/{row['coder']}"
            )

    for rid in sorted(record_ids):
        model_set = data.model[rid][dimension]
        if not isinstance(model_set, frozenset) or len(model_set) == 0:
            raise ValueError(f"Empty model set: {population}/{dimension}/{rid}")
        if UNCLEAR in model_set and len(model_set) > 1:
            raise ValueError(
                f"Model Unclear co-occurs with substantive: {population}/{dimension}/{rid}"
            )


def check_3c(data, record_ids: frozenset[str]):
    for rid in sorted(record_ids):
        model_set = data.model[rid]["Analytical Purposes"]
        if len(model_set) > 2:
            raise ValueError(f"Model purpose set > 2: {rid}")


def compute_s1_s2_outcomes(records_in_state: list[dict], dimension: str):
    n = len(records_in_state)
    if n == 0:
        return {"n": 0}

    exact_count = sum(1 for r in records_in_state if r["model_set"] == r["majority_set"])
    jaccards = [jaccard(r["model_set"], r["majority_set"]) for r in records_in_state]
    mean_jaccard = sum(jaccards) / n

    rel_counts = Counter(
        set_relationship(r["model_set"], r["majority_set"]) for r in records_in_state
    )
    model_cards = [len(r["model_set"]) for r in records_in_state]
    maj_cards = [len(r["majority_set"]) for r in records_in_state]

    result = {
        "n": n,
        "exact_match_count": exact_count,
        "exact_match_proportion": exact_count / n,
        "mean_jaccard": mean_jaccard,
        "rel_exact": rel_counts.get("exact", 0),
        "rel_strict_superset": rel_counts.get("strict_superset", 0),
        "rel_strict_subset": rel_counts.get("strict_subset", 0),
        "rel_partial_overlap": rel_counts.get("partial_overlap", 0),
        "rel_disjoint": rel_counts.get("disjoint", 0),
        "mean_model_cardinality": sum(model_cards) / n,
        "mean_majority_cardinality": sum(maj_cards) / n,
    }

    rel_sum = sum(
        result[k]
        for k in [
            "rel_exact", "rel_strict_superset", "rel_strict_subset",
            "rel_partial_overlap", "rel_disjoint",
        ]
    )
    assert rel_sum == n, f"Set relationship counts sum to {rel_sum}, expected {n}"

    if dimension == "Analytical Purposes":
        gt2 = sum(1 for r in records_in_state if len(r["majority_set"]) > 2)
        result["majority_gt2_count"] = gt2
        result["majority_gt2_proportion"] = gt2 / n if n > 0 else None

    return result


def compute_s3_outcomes(records_in_state: list[dict]):
    n = len(records_in_state)
    if n == 0:
        return {"n": 0}

    unclear_count = sum(1 for r in records_in_state if UNCLEAR in r["model_set"])
    substantive_count = sum(
        1 for r in records_in_state
        if any(label != UNCLEAR for label in r["model_set"])
    )
    subst_records = [
        r for r in records_in_state
        if any(label != UNCLEAR for label in r["model_set"])
    ]
    mean_subst_labels = (
        sum(
            sum(1 for label in r["model_set"] if label != UNCLEAR)
            for r in subst_records
        )
        / len(subst_records)
        if subst_records
        else None
    )

    return {
        "n": n,
        "model_unclear_count": unclear_count,
        "model_unclear_proportion": unclear_count / n,
        "model_substantive_count": substantive_count,
        "model_substantive_proportion": substantive_count / n,
        "mean_substantive_labels_among_substantive": mean_subst_labels,
        "mean_substantive_labels_denominator": len(subst_records),
    }


def compute_s4_outcomes(records_in_state: list[dict]):
    n = len(records_in_state)
    if n == 0:
        return {"n": 0}

    card_dist = Counter(len(r["model_set"]) for r in records_in_state)
    card_0 = card_dist.get(0, 0)
    card_1 = card_dist.get(1, 0)
    card_2 = card_dist.get(2, 0)
    card_3plus = sum(v for k, v in card_dist.items() if k >= 3)

    unclear_count = sum(1 for r in records_in_state if UNCLEAR in r["model_set"])

    return {
        "n": n,
        "card_0": card_0,
        "card_0_proportion": card_0 / n,
        "card_1": card_1,
        "card_1_proportion": card_1 / n,
        "card_2": card_2,
        "card_2_proportion": card_2 / n,
        "card_3plus": card_3plus,
        "card_3plus_proportion": card_3plus / n,
        "model_unclear_count": unclear_count,
        "model_unclear_proportion": unclear_count / n,
        "jaccard_exact_match_status": "undefined — human-majority reference set is empty",
    }


def compute_label_support(records_in_state: list[dict], data):
    results = []
    for r in records_in_state:
        for label in r["model_set"]:
            coder_count = sum(1 for cs in r["coder_sets"] if label in cs)
            results.append({"label": label, "coder_support": coder_count})
    dist = Counter(item["coder_support"] for item in results)
    total = len(results)
    return {
        "total_assignments": total,
        "support_0": dist.get(0, 0),
        "support_1": dist.get(1, 0),
        "support_2": dist.get(2, 0),
        "support_3": dist.get(3, 0),
        "support_0_proportion": dist.get(0, 0) / total if total else None,
        "support_1_proportion": dist.get(1, 0) / total if total else None,
        "support_2_proportion": dist.get(2, 0) / total if total else None,
        "support_3_proportion": dist.get(3, 0) / total if total else None,
    }


def bootstrap_evaluator_s1s2(sample, dimension: str):
    n = len(sample)
    if n == 0:
        return {}
    exact_count = sum(1 for r in sample if r["model_set"] == r["majority_set"])
    jaccards = [jaccard(r["model_set"], r["majority_set"]) for r in sample]

    rel_counts = Counter(
        set_relationship(r["model_set"], r["majority_set"]) for r in sample
    )
    model_cards = [len(r["model_set"]) for r in sample]
    maj_cards = [len(r["majority_set"]) for r in sample]

    result = {
        "exact_match_proportion": StatisticValue(exact_count / n, True),
        "mean_jaccard": StatisticValue(sum(jaccards) / n, True),
        "rel_exact_proportion": StatisticValue(rel_counts.get("exact", 0) / n, True),
        "rel_strict_superset_proportion": StatisticValue(rel_counts.get("strict_superset", 0) / n, True),
        "rel_strict_subset_proportion": StatisticValue(rel_counts.get("strict_subset", 0) / n, True),
        "rel_partial_overlap_proportion": StatisticValue(rel_counts.get("partial_overlap", 0) / n, True),
        "rel_disjoint_proportion": StatisticValue(rel_counts.get("disjoint", 0) / n, True),
        "mean_model_cardinality": StatisticValue(sum(model_cards) / n, True),
        "mean_majority_cardinality": StatisticValue(sum(maj_cards) / n, True),
    }

    if dimension == "Analytical Purposes":
        gt2 = sum(1 for r in sample if len(r["majority_set"]) > 2)
        result["majority_gt2_proportion"] = StatisticValue(gt2 / n, True)

    label_support_items = []
    for r in sample:
        for label in r["model_set"]:
            coder_count = sum(1 for cs in r["coder_sets"] if label in cs)
            label_support_items.append(coder_count)
    total_assignments = len(label_support_items)
    if total_assignments > 0:
        dist = Counter(label_support_items)
        for k in range(4):
            result[f"support_{k}_proportion"] = StatisticValue(
                dist.get(k, 0) / total_assignments, True
            )
    else:
        for k in range(4):
            result[f"support_{k}_proportion"] = StatisticValue(None, False, "no_assignments")

    return result


def bootstrap_evaluator_s3(sample):
    n = len(sample)
    if n == 0:
        return {}
    unclear_count = sum(1 for r in sample if UNCLEAR in r["model_set"])
    subst_count = sum(
        1 for r in sample if any(label != UNCLEAR for label in r["model_set"])
    )
    subst_records = [
        r for r in sample if any(label != UNCLEAR for label in r["model_set"])
    ]
    result = {
        "model_unclear_proportion": StatisticValue(unclear_count / n, True),
        "model_substantive_proportion": StatisticValue(subst_count / n, True),
    }
    if subst_records:
        mean_n = sum(
            sum(1 for label in r["model_set"] if label != UNCLEAR)
            for r in subst_records
        ) / len(subst_records)
        result["mean_substantive_labels"] = StatisticValue(mean_n, True)
    else:
        result["mean_substantive_labels"] = StatisticValue(None, False, "no_substantive_records")

    label_support_items = []
    for r in sample:
        for label in r["model_set"]:
            coder_count = sum(1 for cs in r["coder_sets"] if label in cs)
            label_support_items.append(coder_count)
    total = len(label_support_items)
    if total > 0:
        dist = Counter(label_support_items)
        for k in range(4):
            result[f"support_{k}_proportion"] = StatisticValue(dist.get(k, 0) / total, True)
    else:
        for k in range(4):
            result[f"support_{k}_proportion"] = StatisticValue(None, False, "no_assignments")

    return result


def bootstrap_evaluator_s4(sample):
    n = len(sample)
    if n == 0:
        return {}
    card_dist = Counter(len(r["model_set"]) for r in sample)
    unclear_count = sum(1 for r in sample if UNCLEAR in r["model_set"])
    result = {
        "card_0_proportion": StatisticValue(card_dist.get(0, 0) / n, True),
        "card_1_proportion": StatisticValue(card_dist.get(1, 0) / n, True),
        "card_2_proportion": StatisticValue(card_dist.get(2, 0) / n, True),
        "card_3plus_proportion": StatisticValue(
            sum(v for k, v in card_dist.items() if k >= 3) / n, True
        ),
        "model_unclear_proportion": StatisticValue(unclear_count / n, True),
    }

    label_support_items = []
    for r in sample:
        for label in r["model_set"]:
            coder_count = sum(1 for cs in r["coder_sets"] if label in cs)
            label_support_items.append(coder_count)
    total = len(label_support_items)
    if total > 0:
        dist = Counter(label_support_items)
        for k in range(4):
            result[f"support_{k}_proportion"] = StatisticValue(dist.get(k, 0) / total, True)
    else:
        for k in range(4):
            result[f"support_{k}_proportion"] = StatisticValue(None, False, "no_assignments")

    return result


def interval_row(
    stat_name: str,
    bs: BootstrapResult,
    observed_value: float | None,
    observed_n: int,
    population: str,
) -> dict:
    s = bs.statistics[stat_name]
    analysis_note = (
        "DIAGNOSTIC -- descriptive resampling intervals for a selected diagnostic sample, not population-generalising intervals"
        if population == "hard_case"
        else ""
    )
    interval_status = "R" if s.interval_reported else "SV"
    return {
        "estimate": observed_value,
        "state_n": observed_n,
        "lower": s.lower,
        "upper": s.upper,
        "valid_replicates": s.valid,
        "invalid_replicates": s.invalid,
        "requested_replicates": s.attempted,
        "interval_status": interval_status,
        "analysis_note": analysis_note,
    }


def run_bootstrap_s1s2(records_in_state, dimension, population):
    stat_names = [
        "exact_match_proportion", "mean_jaccard",
        "rel_exact_proportion", "rel_strict_superset_proportion",
        "rel_strict_subset_proportion", "rel_partial_overlap_proportion",
        "rel_disjoint_proportion",
        "mean_model_cardinality", "mean_majority_cardinality",
        "support_0_proportion", "support_1_proportion",
        "support_2_proportion", "support_3_proportion",
    ]
    if dimension == "Analytical Purposes":
        stat_names.append("majority_gt2_proportion")
    return bootstrap_joint(
        records_in_state,
        lambda sample: bootstrap_evaluator_s1s2(sample, dimension),
        statistic_names=stat_names,
        attempted_replicates=REPLICATES,
        seed=SEED,
        minimum_valid_fraction=MIN_VALID / REPLICATES,
    )


def run_bootstrap_s3(records_in_state, population):
    stat_names = [
        "model_unclear_proportion", "model_substantive_proportion",
        "mean_substantive_labels",
        "support_0_proportion", "support_1_proportion",
        "support_2_proportion", "support_3_proportion",
    ]
    return bootstrap_joint(
        records_in_state,
        bootstrap_evaluator_s3,
        statistic_names=stat_names,
        attempted_replicates=REPLICATES,
        seed=SEED,
        minimum_valid_fraction=MIN_VALID / REPLICATES,
    )


def run_bootstrap_s4(records_in_state, population):
    stat_names = [
        "card_0_proportion", "card_1_proportion",
        "card_2_proportion", "card_3plus_proportion",
        "model_unclear_proportion",
        "support_0_proportion", "support_1_proportion",
        "support_2_proportion", "support_3_proportion",
    ]
    return bootstrap_joint(
        records_in_state,
        bootstrap_evaluator_s4,
        statistic_names=stat_names,
        attempted_replicates=REPLICATES,
        seed=SEED,
        minimum_valid_fraction=MIN_VALID / REPLICATES,
    )


def format_interval(row: dict) -> str:
    if row["interval_status"] == "SV":
        return "(interval not estimable)"
    if row["lower"] is not None and row["upper"] is not None:
        return f"[{row['lower']:.4f}, {row['upper']:.4f}]"
    return "(interval not estimable)"


def write_csv(path: Path, headers: list[str], rows: list[list]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def main():
    run_start = datetime.datetime.now(datetime.timezone.utc)
    checks = []

    print("Verifying authorities...")
    authority_checks = verify_authorities()
    for ac in authority_checks:
        checks.append({
            "check": f"hash {ac.manifest_id}",
            "status": "passed" if ac.matched else "FAILED",
            "actual": ac.observed_sha256,
            "expected": ac.expected_sha256,
        })
        if not ac.matched:
            raise ValueError(f"Authority hash mismatch: {ac.manifest_id}")

    print("Building Stage A data...")
    data = build_stage_a_data()

    for pop in POPULATIONS:
        ids = data.baseline_ids if pop == "baseline" else data.hard_case_ids
        expected_n = 150 if pop == "baseline" else 75

        checks.append({
            "check": f"{pop} record count",
            "status": "passed" if len(ids) == expected_n else "FAILED",
            "actual": len(ids),
            "expected": expected_n,
        })

        for dim in DIMENSIONS:
            print(f"Checking 3a/3b: {pop}/{dim}...")
            check_3a_3b(data, pop, dim, ids)
            checks.append({
                "check": f"{pop}/{dim} 3a/3b non-empty sets, Unclear exclusive",
                "status": "passed",
            })

        if pop == "baseline" or pop == "hard_case":
            check_3c(data, ids)
            checks.append({
                "check": f"{pop} 3c model purpose set <= 2",
                "status": "passed",
            })

    majority_coverage = pandas.read_csv(
        ROOT / "analysis" / "outputs_majority_coverage_20260914T170315Z" / "majority_coverage.csv",
        dtype=str,
        keep_default_na=False,
    )

    all_results = {}
    table_counter = 0
    all_csv_data = {}

    for pop in POPULATIONS:
        ids = data.baseline_ids if pop == "baseline" else data.hard_case_ids
        expected_n = 150 if pop == "baseline" else 75

        for dim in DIMENSIONS:
            print(f"\nProcessing {pop}/{dim}...")
            records = build_record_data(data, pop, dim)
            assert len(records) == expected_n

            state_groups = defaultdict(list)
            for r in records:
                state_groups[r["state"]].append(r)

            state_counts = {s: len(state_groups[s]) for s in ["S1", "S2", "S3", "S4"]}
            total = sum(state_counts.values())
            assert total == expected_n, f"States sum to {total}, expected {expected_n}"
            checks.append({
                "check": f"{pop}/{dim} S1+S2+S3+S4 = {expected_n}",
                "status": "passed",
                "actual": total,
                "expected": expected_n,
            })

            unclear_only_expected = int(
                majority_coverage.loc[
                    (majority_coverage["population"] == pop)
                    & (majority_coverage["dimension"] == dim)
                    & (majority_coverage["quantity"] == "unclear_composition")
                    & (majority_coverage["category"] == "unclear_present__substantive_absent"),
                    "count",
                ].iloc[0]
            )
            no_majority_expected = int(
                majority_coverage.loc[
                    (majority_coverage["population"] == pop)
                    & (majority_coverage["dimension"] == dim)
                    & (majority_coverage["quantity"] == "no_majority_label")
                    & (majority_coverage["category"] == "size_0"),
                    "count",
                ].iloc[0]
            )

            checks.append({
                "check": f"{pop}/{dim} S3 = Unclear-only majority count",
                "status": "passed" if state_counts["S3"] == unclear_only_expected else "FAILED",
                "actual": state_counts["S3"],
                "expected": unclear_only_expected,
            })
            checks.append({
                "check": f"{pop}/{dim} S4 = no-majority count",
                "status": "passed" if state_counts["S4"] == no_majority_expected else "FAILED",
                "actual": state_counts["S4"],
                "expected": no_majority_expected,
            })

            if state_counts["S3"] != unclear_only_expected or state_counts["S4"] != no_majority_expected:
                raise ValueError(
                    f"Reconciliation failed: {pop}/{dim} "
                    f"S3={state_counts['S3']} expected {unclear_only_expected}, "
                    f"S4={state_counts['S4']} expected {no_majority_expected}"
                )

            if dim == "Analytical Purposes":
                maj_gt2 = sum(
                    1
                    for r in records
                    if len(r["majority_set"]) > 2
                )
                checks.append({
                    "check": f"{pop}/{dim} majority purpose sets > 2",
                    "status": "passed" if maj_gt2 == 0 else "FAILED",
                    "actual": maj_gt2,
                    "expected": 0,
                })
                if maj_gt2 != 0:
                    raise ValueError(
                        f"STOP: {pop}/{dim} has {maj_gt2} majority purpose sets with cardinality > 2"
                    )

            maj_size_dist = Counter(len(r["majority_set"]) for r in records)
            for size_key in range(5):
                csv_key = f"size_{size_key}" if size_key < 4 else "size_4_plus"
                row_match = majority_coverage.loc[
                    (majority_coverage["population"] == pop)
                    & (majority_coverage["dimension"] == dim)
                    & (majority_coverage["quantity"] == "majority_set_size")
                    & (majority_coverage["category"] == csv_key),
                ]
                if not row_match.empty:
                    expected_count = int(row_match["count"].iloc[0])
                    if size_key < 4:
                        actual_count = maj_size_dist.get(size_key, 0)
                    else:
                        actual_count = sum(v for k, v in maj_size_dist.items() if k >= 4)
                    checks.append({
                        "check": f"{pop}/{dim} majority set size {csv_key}",
                        "status": "passed" if actual_count == expected_count else "FAILED",
                        "actual": actual_count,
                        "expected": expected_count,
                    })

            pop_label = pop
            analysis_note_prefix = (
                "DIAGNOSTIC -- non-representative"
                if pop == "hard_case"
                else ""
            )

            key = (pop, dim)
            result_block = {
                "population": pop,
                "dimension": dim,
                "state_counts": state_counts,
                "analysis_note": analysis_note_prefix,
            }

            for state_name in ["S1", "S2"]:
                recs = state_groups[state_name]
                n_state = len(recs)
                if n_state == 0:
                    result_block[state_name] = {"n": 0}
                    continue

                outcomes = compute_s1_s2_outcomes(recs, dim)
                support = compute_label_support(recs, data)
                bs = run_bootstrap_s1s2(recs, dim, pop)

                block = {**outcomes, **support, "bootstrap": {}}
                for stat_name in bs.statistics:
                    obs_val = None
                    if stat_name == "exact_match_proportion":
                        obs_val = outcomes["exact_match_proportion"]
                    elif stat_name == "mean_jaccard":
                        obs_val = outcomes["mean_jaccard"]
                    elif stat_name.startswith("rel_"):
                        rel_key = stat_name.replace("_proportion", "")
                        obs_val = outcomes.get(rel_key, 0) / n_state if n_state else None
                    elif stat_name == "mean_model_cardinality":
                        obs_val = outcomes["mean_model_cardinality"]
                    elif stat_name == "mean_majority_cardinality":
                        obs_val = outcomes["mean_majority_cardinality"]
                    elif stat_name == "majority_gt2_proportion":
                        obs_val = outcomes.get("majority_gt2_proportion")
                    elif stat_name.startswith("support_"):
                        k = int(stat_name.split("_")[1])
                        obs_val = support.get(f"support_{k}_proportion")

                    block["bootstrap"][stat_name] = interval_row(
                        stat_name, bs, obs_val, n_state, pop
                    )

                result_block[state_name] = block

            recs_s3 = state_groups["S3"]
            if recs_s3:
                outcomes_s3 = compute_s3_outcomes(recs_s3)
                support_s3 = compute_label_support(recs_s3, data)
                bs_s3 = run_bootstrap_s3(recs_s3, pop)
                block_s3 = {**outcomes_s3, **support_s3, "bootstrap": {}}
                for stat_name in bs_s3.statistics:
                    obs_val = None
                    if stat_name == "model_unclear_proportion":
                        obs_val = outcomes_s3["model_unclear_proportion"]
                    elif stat_name == "model_substantive_proportion":
                        obs_val = outcomes_s3["model_substantive_proportion"]
                    elif stat_name == "mean_substantive_labels":
                        obs_val = outcomes_s3["mean_substantive_labels_among_substantive"]
                    elif stat_name.startswith("support_"):
                        k = int(stat_name.split("_")[1])
                        obs_val = support_s3.get(f"support_{k}_proportion")
                    block_s3["bootstrap"][stat_name] = interval_row(
                        stat_name, bs_s3, obs_val, len(recs_s3), pop
                    )
                result_block["S3"] = block_s3
            else:
                result_block["S3"] = {"n": 0}

            recs_s4 = state_groups["S4"]
            if recs_s4:
                outcomes_s4 = compute_s4_outcomes(recs_s4)
                support_s4 = compute_label_support(recs_s4, data)
                bs_s4 = run_bootstrap_s4(recs_s4, pop)
                block_s4 = {**outcomes_s4, **support_s4, "bootstrap": {}}
                for stat_name in bs_s4.statistics:
                    obs_val = None
                    if stat_name.startswith("card_"):
                        obs_val = outcomes_s4.get(f"{stat_name}")
                    elif stat_name == "model_unclear_proportion":
                        obs_val = outcomes_s4["model_unclear_proportion"]
                    elif stat_name.startswith("support_"):
                        k = int(stat_name.split("_")[1])
                        obs_val = support_s4.get(f"support_{k}_proportion")
                    block_s4["bootstrap"][stat_name] = interval_row(
                        stat_name, bs_s4, obs_val, len(recs_s4), pop
                    )
                result_block["S4"] = block_s4
            else:
                result_block["S4"] = {"n": 0}

            all_results[key] = result_block

    for check in checks:
        if check["status"] == "FAILED":
            raise ValueError(f"Check failed: {check}")

    print("\nAll checks passed. Writing outputs...")

    write_results_md(all_results, checks)
    write_csvs(all_results)
    write_metadata(all_results, checks, run_start)

    print("Done.")


def write_results_md(all_results, checks):
    lines = ["# Results — consensus-state exploratory analysis\n"]
    lines.append("This file reports model agreement with the labelwise human majority,")
    lines.append("conditioned on human consensus state. Consensus states are defined from")
    lines.append("human ratings only; the model plays no role in assigning a record to a state.")
    lines.append("The labelwise majority set is not treated as truth.\n")
    lines.append("Populations are reported separately and never pooled.")
    lines.append("Hard-case results are labelled DIAGNOSTIC -- non-representative.\n")

    table_id = 0

    for pop in POPULATIONS:
        for dim in DIMENSIONS:
            key = (pop, dim)
            rb = all_results[key]
            sc = rb["state_counts"]
            note = rb["analysis_note"]
            pop_label = "Random baseline" if pop == "baseline" else "Hard-case sample"
            note_suffix = f" -- {note}" if note else ""

            table_id += 1
            tid = f"CST1T{table_id:03d}"
            lines.append(f"## {tid} -- State counts -- {pop_label} ({pop}){note_suffix} -- {dim}\n")
            lines.append("| State | Definition | Count | Proportion |")
            lines.append("| --- | --- | --- | --- |")
            n = sum(sc.values())
            for state, defn in [
                ("S1", "Unanimous substantive"),
                ("S2", "Majority with dissent"),
                ("S3", "Majority Unclear only"),
                ("S4", "No agreed label"),
            ]:
                c = sc[state]
                p = c / n if n else 0
                lines.append(f"| {state} | {defn} | {c} | {p:.4f} |")
            lines.append(f"| Total | | {n} | 1.0000 |")
            lines.append(f"\nInterval status for all counts: N/A (raw observed counts).\n")

            for state_name in ["S1", "S2"]:
                block = rb[state_name]
                state_n = block.get("n", 0)
                if state_n == 0:
                    table_id += 1
                    tid = f"CST1T{table_id:03d}"
                    lines.append(f"## {tid} -- {state_name} outcomes -- {pop_label} ({pop}){note_suffix} -- {dim}\n")
                    lines.append(f"State n = 0. No outcomes to report.\n")
                    continue

                table_id += 1
                tid = f"CST1T{table_id:03d}"
                lines.append(f"## {tid} -- {state_name} outcomes -- {pop_label} ({pop}){note_suffix} -- {dim}\n")
                lines.append(f"State n = {state_n}.\n")

                lines.append("### Set-level agreement\n")
                lines.append("| Quantity | Estimate | 95% interval | State n | Valid / invalid / requested replicates | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- |")

                bs = block["bootstrap"]
                for qty, stat_key in [
                    ("Exact match proportion", "exact_match_proportion"),
                    ("Mean Jaccard similarity", "mean_jaccard"),
                ]:
                    row = bs[stat_key]
                    iv = format_interval(row)
                    lines.append(
                        f"| {qty} | {row['estimate']:.4f} | {iv} | {row['state_n']} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )

                lines.append("\n### Set relationship (five categories)\n")
                lines.append("| Category | Count | Proportion | 95% interval | State n | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                for cat, rel_key in [
                    ("Exact", "rel_exact"),
                    ("Strict superset", "rel_strict_superset"),
                    ("Strict subset", "rel_strict_subset"),
                    ("Partial overlap", "rel_partial_overlap"),
                    ("Disjoint", "rel_disjoint"),
                ]:
                    count_val = block[rel_key]
                    prop_val = count_val / state_n
                    row = bs[f"{rel_key}_proportion"]
                    iv = format_interval(row)
                    lines.append(
                        f"| {cat} | {count_val} | {prop_val:.4f} | {iv} | {row['state_n']} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )

                lines.append("\n### Cardinality\n")
                lines.append("| Quantity | Estimate | 95% interval | State n | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- |")
                for qty, stat_key in [
                    ("Mean model-set cardinality", "mean_model_cardinality"),
                    ("Mean majority-set cardinality", "mean_majority_cardinality"),
                ]:
                    row = bs[stat_key]
                    iv = format_interval(row)
                    lines.append(
                        f"| {qty} | {row['estimate']:.4f} | {iv} | {row['state_n']} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )

                if dim == "Analytical Purposes" and "majority_gt2_count" in block:
                    gt2_count = block["majority_gt2_count"]
                    lines.append(
                        f"\nMajority purpose sets with cardinality > 2: {gt2_count} of {state_n} records."
                    )
                    if gt2_count > 0:
                        lines.append("WARNING: non-zero count.")
                    lines.append("")

                lines.append("\n### Model-label support by coder agreement\n")
                lines.append("| Coder support | Count | Proportion | 95% interval | Assignments | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                total_assign = block["total_assignments"]
                for k in range(4):
                    c = block[f"support_{k}"]
                    p = block[f"support_{k}_proportion"]
                    row = bs[f"support_{k}_proportion"]
                    iv = format_interval(row)
                    p_str = f"{p:.4f}" if p is not None else "N/A"
                    lines.append(
                        f"| {k} of 3 coders | {c} | {p_str} | {iv} | {total_assign} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )
                lines.append("")

            block_s3 = rb["S3"]
            state_n_s3 = block_s3.get("n", 0)
            table_id += 1
            tid = f"CST1T{table_id:03d}"
            lines.append(f"## {tid} -- S3 outcomes -- {pop_label} ({pop}){note_suffix} -- {dim}\n")
            if state_n_s3 == 0:
                lines.append(f"State n = 0. No outcomes to report.\n")
            else:
                lines.append(f"State n = {state_n_s3}.\n")
                bs_s3 = block_s3["bootstrap"]
                lines.append("| Quantity | Count | Proportion | 95% interval | State n | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                for qty, count_key, prop_key, stat_key in [
                    ("Model applied Unclear", "model_unclear_count", "model_unclear_proportion", "model_unclear_proportion"),
                    ("Model applied substantive label(s)", "model_substantive_count", "model_substantive_proportion", "model_substantive_proportion"),
                ]:
                    c = block_s3[count_key]
                    p = block_s3[prop_key]
                    row = bs_s3[stat_key]
                    iv = format_interval(row)
                    lines.append(
                        f"| {qty} | {c} | {p:.4f} | {iv} | {row['state_n']} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )
                mean_subst = block_s3["mean_substantive_labels_among_substantive"]
                mean_denom = block_s3["mean_substantive_labels_denominator"]
                if mean_subst is not None:
                    row_mean = bs_s3["mean_substantive_labels"]
                    iv_mean = format_interval(row_mean)
                    lines.append(
                        f"\nAmong the {mean_denom} records where the model applied at least one substantive label, "
                        f"the mean number of substantive labels applied: {mean_subst:.4f} {iv_mean} "
                        f"(valid/invalid/requested: {row_mean['valid_replicates']}/{row_mean['invalid_replicates']}/{row_mean['requested_replicates']}; "
                        f"interval status: {row_mean['interval_status']}).\n"
                    )
                else:
                    lines.append(f"\nNo records in this state had the model apply a substantive label.\n")

                lines.append("### Model-label support by coder agreement\n")
                lines.append("| Coder support | Count | Proportion | 95% interval | Assignments | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                total_assign = block_s3["total_assignments"]
                for k in range(4):
                    c = block_s3[f"support_{k}"]
                    p = block_s3[f"support_{k}_proportion"]
                    row = bs_s3[f"support_{k}_proportion"]
                    iv = format_interval(row)
                    p_str = f"{p:.4f}" if p is not None else "N/A"
                    lines.append(
                        f"| {k} of 3 coders | {c} | {p_str} | {iv} | {total_assign} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )
                lines.append("")

            block_s4 = rb["S4"]
            state_n_s4 = block_s4.get("n", 0)
            table_id += 1
            tid = f"CST1T{table_id:03d}"
            lines.append(f"## {tid} -- S4 outcomes -- {pop_label} ({pop}){note_suffix} -- {dim}\n")
            if state_n_s4 == 0:
                lines.append(f"State n = 0. No outcomes to report.\n")
            else:
                lines.append(f"State n = {state_n_s4}.\n")
                lines.append(f"Jaccard and exact match: {block_s4['jaccard_exact_match_status']}.\n")
                bs_s4 = block_s4["bootstrap"]
                lines.append("### Model-set cardinality distribution\n")
                lines.append("| Cardinality | Count | Proportion | 95% interval | State n | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                for card_label, count_key, prop_key, stat_key in [
                    ("0", "card_0", "card_0_proportion", "card_0_proportion"),
                    ("1", "card_1", "card_1_proportion", "card_1_proportion"),
                    ("2", "card_2", "card_2_proportion", "card_2_proportion"),
                    ("3+", "card_3plus", "card_3plus_proportion", "card_3plus_proportion"),
                ]:
                    c = block_s4[count_key]
                    p = block_s4[prop_key]
                    row = bs_s4[stat_key]
                    iv = format_interval(row)
                    lines.append(
                        f"| {card_label} | {c} | {p:.4f} | {iv} | {row['state_n']} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )

                lines.append(f"\nModel applied Unclear from Register Entry: {block_s4['model_unclear_count']} of {state_n_s4} "
                             f"({block_s4['model_unclear_proportion']:.4f}).")
                row_unc = bs_s4["model_unclear_proportion"]
                iv_unc = format_interval(row_unc)
                lines.append(
                    f"95% interval: {iv_unc} (valid/invalid/requested: "
                    f"{row_unc['valid_replicates']}/{row_unc['invalid_replicates']}/{row_unc['requested_replicates']}; "
                    f"interval status: {row_unc['interval_status']}).\n"
                )

                card_0_val = block_s4["card_0"]
                card_3plus_val = block_s4["card_3plus"]
                lines.append(f"Cardinality 0 bin: {card_0_val} (asserted {'zero' if card_0_val == 0 else 'non-zero'}).")
                lines.append(f"Cardinality 3+ bin: {card_3plus_val} (asserted {'zero' if card_3plus_val == 0 else 'non-zero'}).\n")

                lines.append("### Model-label support by coder agreement\n")
                lines.append("| Coder support | Count | Proportion | 95% interval | Assignments | Valid / invalid / requested | Interval status |")
                lines.append("| --- | --- | --- | --- | --- | --- | --- |")
                total_assign = block_s4["total_assignments"]
                for k in range(4):
                    c = block_s4[f"support_{k}"]
                    p = block_s4[f"support_{k}_proportion"]
                    row = bs_s4[f"support_{k}_proportion"]
                    iv = format_interval(row)
                    p_str = f"{p:.4f}" if p is not None else "N/A"
                    lines.append(
                        f"| {k} of 3 coders | {c} | {p_str} | {iv} | {total_assign} | "
                        f"{row['valid_replicates']} / {row['invalid_replicates']} / {row['requested_replicates']} | "
                        f"{row['interval_status']} |"
                    )
                lines.append("")

    path = OUTPUT_DIR / "results_consensus_state.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def write_csvs(all_results):
    table_id = 0
    for pop in POPULATIONS:
        for dim in DIMENSIONS:
            key = (pop, dim)
            rb = all_results[key]
            sc = rb["state_counts"]
            n = sum(sc.values())

            table_id += 1
            tid = f"CST1T{table_id:03d}"
            headers = ["state", "definition", "count", "proportion"]
            rows = []
            for state, defn in [
                ("S1", "Unanimous substantive"),
                ("S2", "Majority with dissent"),
                ("S3", "Majority Unclear only"),
                ("S4", "No agreed label"),
            ]:
                rows.append([state, defn, sc[state], f"{sc[state]/n:.4f}"])
            rows.append(["Total", "", n, "1.0000"])
            write_csv(OUTPUT_DIR / f"{tid}.csv", headers, rows)

            for state_name in ["S1", "S2"]:
                block = rb[state_name]
                state_n = block.get("n", 0)
                table_id += 1
                tid = f"CST1T{table_id:03d}"
                if state_n == 0:
                    write_csv(
                        OUTPUT_DIR / f"{tid}.csv",
                        ["quantity", "value", "note"],
                        [["state_n", 0, "No outcomes"]],
                    )
                    continue

                csv_rows = []
                bs = block["bootstrap"]
                for qty, stat_key in [
                    ("exact_match_proportion", "exact_match_proportion"),
                    ("mean_jaccard", "mean_jaccard"),
                ]:
                    row = bs[stat_key]
                    csv_rows.append([
                        qty, state_n, f"{row['estimate']:.6f}",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                for cat, rel_key in [
                    ("exact", "rel_exact"),
                    ("strict_superset", "rel_strict_superset"),
                    ("strict_subset", "rel_strict_subset"),
                    ("partial_overlap", "rel_partial_overlap"),
                    ("disjoint", "rel_disjoint"),
                ]:
                    count_val = block[rel_key]
                    row = bs[f"{rel_key}_proportion"]
                    csv_rows.append([
                        f"set_rel_{cat}", state_n,
                        f"{count_val}; {count_val/state_n:.6f}",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                for qty, stat_key in [
                    ("mean_model_cardinality", "mean_model_cardinality"),
                    ("mean_majority_cardinality", "mean_majority_cardinality"),
                ]:
                    row = bs[stat_key]
                    csv_rows.append([
                        qty, state_n, f"{row['estimate']:.6f}",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                if dim == "Analytical Purposes" and "majority_gt2_proportion" in bs:
                    row = bs["majority_gt2_proportion"]
                    csv_rows.append([
                        "majority_gt2_proportion", state_n,
                        f"{block.get('majority_gt2_count', 0)}; {row['estimate']:.6f}" if row["estimate"] is not None else "0; 0.000000",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                total_assign = block["total_assignments"]
                for k in range(4):
                    row = bs[f"support_{k}_proportion"]
                    csv_rows.append([
                        f"support_{k}_of_3", state_n,
                        f"{block[f'support_{k}']}; {block[f'support_{k}_proportion']:.6f}" if block[f"support_{k}_proportion"] is not None else f"{block[f'support_{k}']}; N/A",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])

                write_csv(
                    OUTPUT_DIR / f"{tid}.csv",
                    ["quantity", "state_n", "estimate", "lower", "upper",
                     "valid_replicates", "invalid_replicates", "requested_replicates",
                     "interval_status"],
                    csv_rows,
                )

            block_s3 = rb["S3"]
            state_n_s3 = block_s3.get("n", 0)
            table_id += 1
            tid = f"CST1T{table_id:03d}"
            if state_n_s3 == 0:
                write_csv(
                    OUTPUT_DIR / f"{tid}.csv",
                    ["quantity", "value", "note"],
                    [["state_n", 0, "No outcomes"]],
                )
            else:
                csv_rows = []
                bs_s3 = block_s3["bootstrap"]
                for qty, stat_key in [
                    ("model_unclear_proportion", "model_unclear_proportion"),
                    ("model_substantive_proportion", "model_substantive_proportion"),
                ]:
                    row = bs_s3[stat_key]
                    csv_rows.append([
                        qty, state_n_s3,
                        f"{block_s3[qty.replace('_proportion', '_count')]}; {block_s3[qty]:.6f}",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                mean_subst = block_s3.get("mean_substantive_labels_among_substantive")
                if mean_subst is not None:
                    row_mean = bs_s3["mean_substantive_labels"]
                    csv_rows.append([
                        "mean_substantive_labels", block_s3["mean_substantive_labels_denominator"],
                        f"{mean_subst:.6f}",
                        f"{row_mean['lower']:.6f}" if row_mean["lower"] is not None else "",
                        f"{row_mean['upper']:.6f}" if row_mean["upper"] is not None else "",
                        row_mean["valid_replicates"], row_mean["invalid_replicates"],
                        row_mean["requested_replicates"], row_mean["interval_status"],
                    ])
                total_assign = block_s3["total_assignments"]
                for k in range(4):
                    row = bs_s3[f"support_{k}_proportion"]
                    csv_rows.append([
                        f"support_{k}_of_3", state_n_s3,
                        f"{block_s3[f'support_{k}']}; {block_s3[f'support_{k}_proportion']:.6f}" if block_s3[f"support_{k}_proportion"] is not None else f"{block_s3[f'support_{k}']}; N/A",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                write_csv(
                    OUTPUT_DIR / f"{tid}.csv",
                    ["quantity", "state_n", "estimate", "lower", "upper",
                     "valid_replicates", "invalid_replicates", "requested_replicates",
                     "interval_status"],
                    csv_rows,
                )

            block_s4 = rb["S4"]
            state_n_s4 = block_s4.get("n", 0)
            table_id += 1
            tid = f"CST1T{table_id:03d}"
            if state_n_s4 == 0:
                write_csv(
                    OUTPUT_DIR / f"{tid}.csv",
                    ["quantity", "value", "note"],
                    [["state_n", 0, "No outcomes"]],
                )
            else:
                csv_rows = []
                bs_s4 = block_s4["bootstrap"]
                for card_label, count_key, prop_key, stat_key in [
                    ("card_0", "card_0", "card_0_proportion", "card_0_proportion"),
                    ("card_1", "card_1", "card_1_proportion", "card_1_proportion"),
                    ("card_2", "card_2", "card_2_proportion", "card_2_proportion"),
                    ("card_3plus", "card_3plus", "card_3plus_proportion", "card_3plus_proportion"),
                ]:
                    c = block_s4[count_key]
                    p = block_s4[prop_key]
                    row = bs_s4[stat_key]
                    csv_rows.append([
                        card_label, state_n_s4, f"{c}; {p:.6f}",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                row_unc = bs_s4["model_unclear_proportion"]
                csv_rows.append([
                    "model_unclear", state_n_s4,
                    f"{block_s4['model_unclear_count']}; {block_s4['model_unclear_proportion']:.6f}",
                    f"{row_unc['lower']:.6f}" if row_unc["lower"] is not None else "",
                    f"{row_unc['upper']:.6f}" if row_unc["upper"] is not None else "",
                    row_unc["valid_replicates"], row_unc["invalid_replicates"],
                    row_unc["requested_replicates"], row_unc["interval_status"],
                ])
                total_assign = block_s4["total_assignments"]
                for k in range(4):
                    row = bs_s4[f"support_{k}_proportion"]
                    csv_rows.append([
                        f"support_{k}_of_3", state_n_s4,
                        f"{block_s4[f'support_{k}']}; {block_s4[f'support_{k}_proportion']:.6f}" if block_s4[f"support_{k}_proportion"] is not None else f"{block_s4[f'support_{k}']}; N/A",
                        f"{row['lower']:.6f}" if row["lower"] is not None else "",
                        f"{row['upper']:.6f}" if row["upper"] is not None else "",
                        row["valid_replicates"], row["invalid_replicates"],
                        row["requested_replicates"], row["interval_status"],
                    ])
                write_csv(
                    OUTPUT_DIR / f"{tid}.csv",
                    ["quantity", "state_n", "estimate", "lower", "upper",
                     "valid_replicates", "invalid_replicates", "requested_replicates",
                     "interval_status"],
                    csv_rows,
                )


def write_metadata(all_results, checks, run_start):
    run_end = datetime.datetime.now(datetime.timezone.utc)

    data_sources = []
    for artifact_id in ["POST-028", "POST-009", "POST-011", "POST-019", "MOD-006", "MOD-001", "RED-036", "RED-017", "RED-013"]:
        row = resolve_manifest_row(artifact_id)
        path = ROOT / row["current_path"]
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        match_method = "raw_bytes"
        if raw_hash != row["sha256"]:
            lf_hash = hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            if lf_hash == row["sha256"]:
                match_method = "csv_row_terminator_crlf_reconstruction"
                raw_hash = lf_hash
        data_sources.append({
            "manifest_id": artifact_id,
            "path": row["current_path"],
            "manifest_sha256": row["sha256"],
            "on_disk_raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "on_disk_bytes": path.stat().st_size,
            "match_method": match_method,
        })

    state_summaries = {}
    for pop in POPULATIONS:
        for dim in DIMENSIONS:
            key = (pop, dim)
            rb = all_results[key]
            state_summaries[f"{pop}/{dim}"] = rb["state_counts"]

    meta = {
        "specification_and_instruction_date": "specified, and instruction issued, on or before 18 September 2026 (investigator-attested)",
        "addendum_creation_date": "2026-09-18",
        "run_started_utc": run_start.isoformat(),
        "run_completed_utc": run_end.isoformat(),
        "status": "exploratory, not preregistered",
        "addendum_commit": "8bab6a5",
        "state_definitions": {
            "S1": "Unanimous: all three coders gave identical label sets, and that set is substantive",
            "S2": "Majority with dissent: majority set is substantive and non-empty, but coders' sets are not identical",
            "S3": "Majority Unclear: majority set consists of Unclear from Register Entry only",
            "S4": "No agreed label: no label reached two of three coders; majority set is empty",
        },
        "state_counts": state_summaries,
        "bootstrap": {
            "seed": SEED,
            "requested_replicates": REPLICATES,
            "minimum_valid_replicates": MIN_VALID,
            "minimum_valid_fraction": MIN_VALID / REPLICATES,
            "confidence_level": 0.95,
            "percentile": "Hyndman-Fan Type 7",
            "resampling_unit": "record (coder sets and model set kept together)",
        },
        "populations": {
            "baseline": 150,
            "hard_case": 75,
            "pooled": False,
            "hard_case_label": "DIAGNOSTIC -- non-representative",
        },
        "dimensions": list(DIMENSIONS),
        "data_sources": data_sources,
        "reconciliation_authority": "analysis/outputs_majority_coverage_20260914T170315Z/majority_coverage.csv",
        "checks": checks,
        "software": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                "numpy": numpy.__version__,
                "pandas": pandas.__version__,
            },
        },
    }

    path = OUTPUT_DIR / "run_metadata.json"
    path.write_text(json.dumps(meta, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
