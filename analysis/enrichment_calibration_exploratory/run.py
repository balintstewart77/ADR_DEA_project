"""Enrichment calibration exploratory: does cross-model disagreement enrich for human disagreement?

Reads the shared Stage A data and the frozen sampling artefact to assign
dimension-matched cross-model disagreement exposure, then compares human
agreement outcomes between exposed and unexposed baseline records.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.agreement import (
    alpha_encoded,
    encode_panels,
)
from analysis.scratch_coder_stage_a.config import CODERS
from analysis.scratch_coder_stage_a.load import (
    resolve_manifest_row,
    verify_authorities,
)
from analysis.scratch_coder_stage_a.panels import (
    build_stage_a_data,
    dimension_panels,
    distance_for_dimension,
)
from analysis.validation.bootstrap import (
    BootstrapResult,
    StatisticValue,
    bootstrap_joint,
    percentile,
)

SEED = 20260918
REPLICATES = 2000
MIN_VALID = 1800
DIMENSIONS = ("Research Domains", "Analytical Purposes")
UNCLEAR = "Unclear from Register Entry"

OUTPUT_DIR = Path(__file__).resolve().parent
RESTRICTED_DIR = ROOT / "preregistration_restricted" / "enrichment_calibration_exploratory"

EXPORTED_ALPHA_ABC = {
    "Research Domains": 0.5263372741925532,
    "Analytical Purposes": 0.2921101465494055,
}

EXPECTED_STATE_COUNTS = {
    "Research Domains": {"S1": 50, "S2": 82, "S3": 13, "S4": 5},
    "Analytical Purposes": {"S1": 27, "S2": 73, "S3": 26, "S4": 24},
}


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


def load_baseline_strata(data) -> dict[str, str]:
    """Load baseline records' cross-model disagreement strata from frozen sampling artefact."""
    baseline_csv = ROOT / "preregistration_restricted" / "sampling" / "official_draw_20260724" / "baseline_active.csv"
    if not baseline_csv.exists():
        raise FileNotFoundError(f"Baseline sample not found: {baseline_csv}")
    strata: dict[str, str] = {}
    with baseline_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["record_id"]
            stratum = row["hard_case_stratum"].strip()
            strata[rid] = stratum if stratum else "none"
    if set(strata.keys()) != data.baseline_ids:
        raise ValueError("Baseline sample IDs do not match Stage A data")
    return strata


def verify_strata_against_comparison(strata: dict[str, str]) -> None:
    """Cross-check strata against crossmodel_comparison.csv."""
    comparison_csv = ROOT / "analysis" / "outputs" / "crossmodel_comparison.csv"
    comp = pd.read_csv(comparison_csv)
    for rid, stratum in strata.items():
        row = comp[comp["Record ID"] == rid]
        if row.empty:
            raise ValueError(f"Record {rid} not in comparison CSV")
        d_match = row.iloc[0]["domains_exact_match"]
        p_match = row.iloc[0]["purposes_exact_match"]
        if isinstance(d_match, str):
            d_match = d_match == "True"
        if isinstance(p_match, str):
            p_match = p_match == "True"
        expected = (
            "both" if not d_match and not p_match
            else "domain_only" if not d_match
            else "purpose_only" if not p_match
            else "none"
        )
        if stratum != expected:
            raise ValueError(f"Stratum mismatch for {rid}: sampling={stratum}, comparison={expected}")


def exposure_ids(strata: dict[str, str], dimension: str) -> tuple[frozenset[str], frozenset[str]]:
    """Return (exposed_ids, unexposed_ids) for the given dimension."""
    if dimension == "Research Domains":
        exposed = frozenset(rid for rid, s in strata.items() if s in ("domain_only", "both"))
        unexposed = frozenset(rid for rid, s in strata.items() if s not in ("domain_only", "both"))
    elif dimension == "Analytical Purposes":
        exposed = frozenset(rid for rid, s in strata.items() if s in ("purpose_only", "both"))
        unexposed = frozenset(rid for rid, s in strata.items() if s not in ("purpose_only", "both"))
    else:
        raise ValueError(f"Unsupported dimension: {dimension}")
    assert len(exposed) + len(unexposed) == len(strata)
    return exposed, unexposed


def build_record_data(data, dimension: str, strata: dict[str, str]):
    """Build per-record data for all baseline records in a given dimension."""
    field = {"Research Domains": "domains", "Analytical Purposes": "purposes"}[dimension]
    record_ids = data.baseline_ids
    rows = data.responses[data.responses["record_id"].isin(record_ids)]
    grouped = {rid: group for rid, group in rows.groupby("record_id")}

    exp_ids, unexp_ids = exposure_ids(strata, dimension)

    records = []
    for rid in sorted(record_ids):
        group = grouped[rid]
        by_coder = {r["coder"]: r for r in group.to_dict("records")}
        coder_sets = [by_coder[c][field] for c in CODERS]
        model_set = data.model[rid][dimension]
        maj = majority_set(coder_sets)
        state = classify_state(coder_sets, maj)

        hh_jaccards = [
            jaccard(coder_sets[0], coder_sets[1]),
            jaccard(coder_sets[0], coder_sets[2]),
            jaccard(coder_sets[1], coder_sets[2]),
        ]
        mc_jaccards = [
            jaccard(model_set, coder_sets[0]),
            jaccard(model_set, coder_sets[1]),
            jaccard(model_set, coder_sets[2]),
        ]

        records.append({
            "record_id": rid,
            "coder_sets": coder_sets,
            "model_set": model_set,
            "majority_set": maj,
            "state": state,
            "exposed": rid in exp_ids,
            "mean_hh_jaccard": sum(hh_jaccards) / 3,
            "mean_mc_jaccard": sum(mc_jaccards) / 3,
            "is_s3": state == "S3",
            "is_s4": state == "S4",
        })
    return records


def build_encoded_data(data, dimension: str):
    """Build encoded panels and record-id-to-index mapping for alpha computation."""
    panels = dimension_panels(data, data.baseline_ids, dimension)
    distance_fn = distance_for_dimension(dimension)
    encoded = encode_panels(panels, distance_fn)
    complete_panels = [p for p in panels if None not in (p.coder_a, p.coder_b, p.coder_c, p.model)]
    rid_to_idx = {p.record_id: i for i, p in enumerate(complete_panels)}
    return encoded, rid_to_idx


def check_alpha_reconciliation(encoded, dimension: str) -> None:
    """Verify full-baseline alpha matches exported value exactly."""
    alpha_abc = alpha_encoded(encoded.ratings[:, [0, 1, 2]], encoded.distance)
    expected = EXPORTED_ALPHA_ABC[dimension]
    if alpha_abc is None:
        raise ValueError(f"Alpha ABC undefined for {dimension}")
    if not np.isclose(alpha_abc, expected, rtol=0, atol=1e-12):
        raise ValueError(
            f"Alpha ABC reconciliation failed for {dimension}: "
            f"computed={alpha_abc!r}, expected={expected!r}, diff={abs(alpha_abc - expected)}"
        )


def check_state_counts(records: list[dict], dimension: str) -> None:
    """Verify consensus-state counts match the completed consensus-state run."""
    counts = Counter(r["state"] for r in records)
    expected = EXPECTED_STATE_COUNTS[dimension]
    for state in ("S1", "S2", "S3", "S4"):
        if counts.get(state, 0) != expected[state]:
            raise ValueError(
                f"State count mismatch for {dimension}/{state}: "
                f"computed={counts.get(state, 0)}, expected={expected[state]}"
            )


def make_evaluator(encoded, rid_to_idx: dict[str, int]):
    """Create a bootstrap evaluator that computes all statistics from resampled records."""
    ratings = encoded.ratings
    distance = encoded.distance

    def evaluator(sample: tuple[dict, ...]) -> dict[str, StatisticValue | float | None]:
        exposed = [r for r in sample if r["exposed"]]
        unexposed = [r for r in sample if not r["exposed"]]

        def alpha_for_group(group):
            idxs = [rid_to_idx[r["record_id"]] for r in group if r["record_id"] in rid_to_idx]
            if len(idxs) < 2:
                return None
            mat = ratings[np.array(idxs)][:, [0, 1, 2]]
            return alpha_encoded(mat, distance)

        alpha_exp = alpha_for_group(exposed)
        alpha_unexp = alpha_for_group(unexposed)
        alpha_full = alpha_for_group(list(sample))

        if alpha_exp is not None and alpha_unexp is not None:
            delta = alpha_exp - alpha_unexp
        else:
            delta = None

        def mean_stat(group, key):
            if not group:
                return None
            return sum(r[key] for r in group) / len(group)

        def rate_stat(group, key):
            if not group:
                return None
            return sum(1 for r in group if r[key]) / len(group)

        def state_prop(group, state):
            if not group:
                return None
            return sum(1 for r in group if r["state"] == state) / len(group)

        result: dict[str, StatisticValue | float | None] = {
            "alpha_full": alpha_full,
            "alpha_exposed": alpha_exp,
            "alpha_unexposed": alpha_unexp,
            "delta_enrichment": delta,
            "mean_hh_jaccard_exposed": mean_stat(exposed, "mean_hh_jaccard"),
            "mean_hh_jaccard_unexposed": mean_stat(unexposed, "mean_hh_jaccard"),
            "unclear_only_rate_exposed": rate_stat(exposed, "is_s3"),
            "unclear_only_rate_unexposed": rate_stat(unexposed, "is_s3"),
            "no_agreed_label_rate_exposed": rate_stat(exposed, "is_s4"),
            "no_agreed_label_rate_unexposed": rate_stat(unexposed, "is_s4"),
            "s1_prop_exposed": state_prop(exposed, "S1"),
            "s2_prop_exposed": state_prop(exposed, "S2"),
            "s3_prop_exposed": state_prop(exposed, "S3"),
            "s4_prop_exposed": state_prop(exposed, "S4"),
            "s1_prop_unexposed": state_prop(unexposed, "S1"),
            "s2_prop_unexposed": state_prop(unexposed, "S2"),
            "s3_prop_unexposed": state_prop(unexposed, "S3"),
            "s4_prop_unexposed": state_prop(unexposed, "S4"),
            "mean_mc_jaccard_exposed": mean_stat(exposed, "mean_mc_jaccard"),
            "mean_mc_jaccard_unexposed": mean_stat(unexposed, "mean_mc_jaccard"),
        }
        return result

    return evaluator


STATISTIC_NAMES = (
    "alpha_full",
    "alpha_exposed",
    "alpha_unexposed",
    "delta_enrichment",
    "mean_hh_jaccard_exposed",
    "mean_hh_jaccard_unexposed",
    "unclear_only_rate_exposed",
    "unclear_only_rate_unexposed",
    "no_agreed_label_rate_exposed",
    "no_agreed_label_rate_unexposed",
    "s1_prop_exposed",
    "s2_prop_exposed",
    "s3_prop_exposed",
    "s4_prop_exposed",
    "s1_prop_unexposed",
    "s2_prop_unexposed",
    "s3_prop_unexposed",
    "s4_prop_unexposed",
    "mean_mc_jaccard_exposed",
    "mean_mc_jaccard_unexposed",
)


def compute_point_estimates(records: list[dict], encoded, rid_to_idx: dict[str, int]) -> dict[str, float | None]:
    """Compute point estimates from the full (non-resampled) data."""
    exposed = [r for r in records if r["exposed"]]
    unexposed = [r for r in records if not r["exposed"]]
    ratings = encoded.ratings
    distance = encoded.distance

    def alpha_for_group(group):
        idxs = [rid_to_idx[r["record_id"]] for r in group if r["record_id"] in rid_to_idx]
        if len(idxs) < 2:
            return None
        mat = ratings[np.array(idxs)][:, [0, 1, 2]]
        return alpha_encoded(mat, distance)

    alpha_full = alpha_for_group(records)
    alpha_exp = alpha_for_group(exposed)
    alpha_unexp = alpha_for_group(unexposed)

    delta = (alpha_exp - alpha_unexp) if (alpha_exp is not None and alpha_unexp is not None) else None

    def mean_stat(group, key):
        if not group:
            return None
        return sum(r[key] for r in group) / len(group)

    def rate_stat(group, key):
        if not group:
            return None
        return sum(1 for r in group if r[key]) / len(group)

    def state_prop(group, state):
        if not group:
            return None
        return sum(1 for r in group if r["state"] == state) / len(group)

    return {
        "alpha_full": alpha_full,
        "alpha_exposed": alpha_exp,
        "alpha_unexposed": alpha_unexp,
        "delta_enrichment": delta,
        "mean_hh_jaccard_exposed": mean_stat(exposed, "mean_hh_jaccard"),
        "mean_hh_jaccard_unexposed": mean_stat(unexposed, "mean_hh_jaccard"),
        "unclear_only_rate_exposed": rate_stat(exposed, "is_s3"),
        "unclear_only_rate_unexposed": rate_stat(unexposed, "is_s3"),
        "no_agreed_label_rate_exposed": rate_stat(exposed, "is_s4"),
        "no_agreed_label_rate_unexposed": rate_stat(unexposed, "is_s4"),
        "s1_prop_exposed": state_prop(exposed, "S1"),
        "s2_prop_exposed": state_prop(exposed, "S2"),
        "s3_prop_exposed": state_prop(exposed, "S3"),
        "s4_prop_exposed": state_prop(exposed, "S4"),
        "s1_prop_unexposed": state_prop(unexposed, "S1"),
        "s2_prop_unexposed": state_prop(unexposed, "S2"),
        "s3_prop_unexposed": state_prop(unexposed, "S3"),
        "s4_prop_unexposed": state_prop(unexposed, "S4"),
        "mean_mc_jaccard_exposed": mean_stat(exposed, "mean_mc_jaccard"),
        "mean_mc_jaccard_unexposed": mean_stat(unexposed, "mean_mc_jaccard"),
    }


def fmt(value: float | None, decimals: int = 4) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def fmt_ci(boot: BootstrapResult, name: str, decimals: int = 4) -> str:
    stat = boot.statistics[name]
    if not stat.interval_reported:
        return "not estimable"
    return f"[{stat.lower:.{decimals}f}, {stat.upper:.{decimals}f}]"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def write_results_md(
    all_results: dict[str, dict],
    strata: dict[str, str],
    output_path: Path,
) -> None:
    """Write the full results markdown file."""
    lines: list[str] = []
    lines.append("# Enrichment calibration exploratory results")
    lines.append("")
    lines.append(f"Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append("")
    lines.append("Population: baseline only (n = 150).")
    lines.append("")
    lines.append("Exposure: dimension-matched cross-model disagreement (Fable 5 vs GPT-5.5).")
    lines.append("")

    stratum_counts = Counter(strata.values())
    total_disagree = stratum_counts["domain_only"] + stratum_counts["purpose_only"] + stratum_counts["both"]

    lines.append("## ECT001 — Baseline frame membership")
    lines.append("")
    lines.append("| Stratum | n |")
    lines.append("|---|---|")
    lines.append(f"| domain_only | {stratum_counts['domain_only']} |")
    lines.append(f"| purpose_only | {stratum_counts['purpose_only']} |")
    lines.append(f"| both | {stratum_counts['both']} |")
    lines.append(f"| none | {stratum_counts['none']} |")
    lines.append(f"| **Total disagreement** | **{total_disagree}** |")
    lines.append(f"| **Total** | **{len(strata)}** |")
    lines.append("")

    table_num = 2
    for dimension in DIMENSIONS:
        dim_short = "domains" if dimension == "Research Domains" else "purposes"
        res = all_results[dimension]
        points = res["points"]
        boot = res["bootstrap"]
        n_exp = res["n_exposed"]
        n_unexp = res["n_unexposed"]
        state_counts_exp = res["state_counts_exposed"]
        state_counts_unexp = res["state_counts_unexposed"]

        lines.append(f"## ECT{table_num:03d} — Alpha comparison — {dimension}")
        lines.append("")
        lines.append(f"Dimension-matched exposure: {dim_short} disagreement (n exposed = {n_exp}, n unexposed = {n_unexp}).")
        lines.append("")
        lines.append("| Group | n | α ABC (MASI) | 95% CI |")
        lines.append("|---|---|---|---|")
        lines.append(f"| Full baseline | 150 | {fmt(points['alpha_full'])} | {fmt_ci(boot, 'alpha_full')} |")
        lines.append(f"| Exposed | {n_exp} | {fmt(points['alpha_exposed'])} | {fmt_ci(boot, 'alpha_exposed')} |")
        lines.append(f"| Unexposed | {n_unexp} | {fmt(points['alpha_unexposed'])} | {fmt_ci(boot, 'alpha_unexposed')} |")
        lines.append(f"| **Δα (exposed − unexposed)** | — | **{fmt(points['delta_enrichment'])}** | **{fmt_ci(boot, 'delta_enrichment')}** |")
        lines.append("")
        table_num += 1

        lines.append(f"## ECT{table_num:03d} — Human-human pairwise Jaccard — {dimension}")
        lines.append("")
        lines.append("Mean of per-record mean pairwise Jaccard: J(A,B), J(A,C), J(B,C).")
        lines.append("")
        lines.append("| Group | n | Mean | 95% CI |")
        lines.append("|---|---|---|---|")
        lines.append(f"| Exposed | {n_exp} | {fmt(points['mean_hh_jaccard_exposed'])} | {fmt_ci(boot, 'mean_hh_jaccard_exposed')} |")
        lines.append(f"| Unexposed | {n_unexp} | {fmt(points['mean_hh_jaccard_unexposed'])} | {fmt_ci(boot, 'mean_hh_jaccard_unexposed')} |")
        lines.append("")
        table_num += 1

        lines.append(f"## ECT{table_num:03d} — Human difficulty indicators — {dimension}")
        lines.append("")
        lines.append("| Indicator | Group | n | Count | Rate | 95% CI |")
        lines.append("|---|---|---|---|---|---|")
        s3_exp = state_counts_exp.get("S3", 0)
        s3_unexp = state_counts_unexp.get("S3", 0)
        s4_exp = state_counts_exp.get("S4", 0)
        s4_unexp = state_counts_unexp.get("S4", 0)
        lines.append(f"| Unclear-only (S3) | Exposed | {n_exp} | {s3_exp} | {fmt(points['unclear_only_rate_exposed'])} | {fmt_ci(boot, 'unclear_only_rate_exposed')} |")
        lines.append(f"| Unclear-only (S3) | Unexposed | {n_unexp} | {s3_unexp} | {fmt(points['unclear_only_rate_unexposed'])} | {fmt_ci(boot, 'unclear_only_rate_unexposed')} |")
        lines.append(f"| No agreed label (S4) | Exposed | {n_exp} | {s4_exp} | {fmt(points['no_agreed_label_rate_exposed'])} | {fmt_ci(boot, 'no_agreed_label_rate_exposed')} |")
        lines.append(f"| No agreed label (S4) | Unexposed | {n_unexp} | {s4_unexp} | {fmt(points['no_agreed_label_rate_unexposed'])} | {fmt_ci(boot, 'no_agreed_label_rate_unexposed')} |")
        lines.append("")
        table_num += 1

        lines.append(f"## ECT{table_num:03d} — Consensus-state distribution — {dimension}")
        lines.append("")
        lines.append("| State | Exposed n | Exposed prop | Exposed 95% CI | Unexposed n | Unexposed prop | Unexposed 95% CI |")
        lines.append("|---|---|---|---|---|---|---|")
        for state in ("S1", "S2", "S3", "S4"):
            n_e = state_counts_exp.get(state, 0)
            n_u = state_counts_unexp.get(state, 0)
            prop_e_key = f"{state.lower()}_prop_exposed"
            prop_u_key = f"{state.lower()}_prop_unexposed"
            lines.append(
                f"| {state} | {n_e} | {fmt(points[prop_e_key])} | {fmt_ci(boot, prop_e_key)} "
                f"| {n_u} | {fmt(points[prop_u_key])} | {fmt_ci(boot, prop_u_key)} |"
            )
        lines.append(f"| **Total** | **{n_exp}** | — | — | **{n_unexp}** | — | — |")
        lines.append("")
        table_num += 1

        lines.append(f"## ECT{table_num:03d} — Model-coder Jaccard (secondary) — {dimension}")
        lines.append("")
        lines.append("Mean of per-record mean model-coder Jaccard: J(M,A), J(M,B), J(M,C). Secondary outcome.")
        lines.append("")
        lines.append("| Group | n | Mean | 95% CI |")
        lines.append("|---|---|---|---|")
        lines.append(f"| Exposed | {n_exp} | {fmt(points['mean_mc_jaccard_exposed'])} | {fmt_ci(boot, 'mean_mc_jaccard_exposed')} |")
        lines.append(f"| Unexposed | {n_unexp} | {fmt(points['mean_mc_jaccard_unexposed'])} | {fmt_ci(boot, 'mean_mc_jaccard_unexposed')} |")
        lines.append("")
        table_num += 1

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_csvs(
    all_results: dict[str, dict],
    strata: dict[str, str],
    output_dir: Path,
) -> list[Path]:
    """Write one CSV per table. Returns paths written."""
    paths: list[Path] = []

    stratum_counts = Counter(strata.values())
    path = output_dir / "ect001_frame_membership.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stratum", "n"])
        for s in ("domain_only", "purpose_only", "both", "none"):
            w.writerow([s, stratum_counts[s]])
    paths.append(path)

    for dimension in DIMENSIONS:
        dim_tag = "domains" if dimension == "Research Domains" else "purposes"
        res = all_results[dimension]
        points = res["points"]
        boot = res["bootstrap"]
        n_exp = res["n_exposed"]
        n_unexp = res["n_unexposed"]
        state_counts_exp = res["state_counts_exposed"]
        state_counts_unexp = res["state_counts_unexposed"]

        path = output_dir / f"alpha_comparison_{dim_tag}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dimension", "group", "n", "alpha_abc", "ci_lower", "ci_upper"])
            for label, key, n in [
                ("full", "alpha_full", 150),
                ("exposed", "alpha_exposed", n_exp),
                ("unexposed", "alpha_unexposed", n_unexp),
                ("delta_enrichment", "delta_enrichment", ""),
            ]:
                stat = boot.statistics[key]
                w.writerow([
                    dimension, label, n,
                    points[key],
                    stat.lower if stat.interval_reported else "",
                    stat.upper if stat.interval_reported else "",
                ])
        paths.append(path)

        path = output_dir / f"human_jaccard_{dim_tag}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dimension", "group", "n", "mean_pairwise_jaccard", "ci_lower", "ci_upper"])
            for label, key, n in [
                ("exposed", "mean_hh_jaccard_exposed", n_exp),
                ("unexposed", "mean_hh_jaccard_unexposed", n_unexp),
            ]:
                stat = boot.statistics[key]
                w.writerow([
                    dimension, label, n,
                    points[key],
                    stat.lower if stat.interval_reported else "",
                    stat.upper if stat.interval_reported else "",
                ])
        paths.append(path)

        path = output_dir / f"difficulty_indicators_{dim_tag}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dimension", "indicator", "group", "n", "count", "rate", "ci_lower", "ci_upper"])
            for indicator, rate_key, count_fn in [
                ("unclear_only_S3", "unclear_only_rate", lambda g: sum(1 for r in g if r["is_s3"])),
                ("no_agreed_label_S4", "no_agreed_label_rate", lambda g: sum(1 for r in g if r["is_s4"])),
            ]:
                exposed_recs = [r for r in res["records"] if r["exposed"]]
                unexposed_recs = [r for r in res["records"] if not r["exposed"]]
                for label, recs, n, suffix in [
                    ("exposed", exposed_recs, n_exp, "_exposed"),
                    ("unexposed", unexposed_recs, n_unexp, "_unexposed"),
                ]:
                    key = rate_key + suffix
                    stat = boot.statistics[key]
                    w.writerow([
                        dimension, indicator, label, n,
                        count_fn(recs),
                        points[key],
                        stat.lower if stat.interval_reported else "",
                        stat.upper if stat.interval_reported else "",
                    ])
        paths.append(path)

        path = output_dir / f"consensus_state_distribution_{dim_tag}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dimension", "state", "group", "n", "count", "proportion", "ci_lower", "ci_upper"])
            for state in ("S1", "S2", "S3", "S4"):
                for label, counts, n_grp, suffix in [
                    ("exposed", state_counts_exp, n_exp, "_exposed"),
                    ("unexposed", state_counts_unexp, n_unexp, "_unexposed"),
                ]:
                    key = f"{state.lower()}_prop{suffix}"
                    stat = boot.statistics[key]
                    w.writerow([
                        dimension, state, label, n_grp,
                        counts.get(state, 0),
                        points[key],
                        stat.lower if stat.interval_reported else "",
                        stat.upper if stat.interval_reported else "",
                    ])
        paths.append(path)

        path = output_dir / f"model_coder_jaccard_{dim_tag}.csv"
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dimension", "group", "n", "mean_model_coder_jaccard", "ci_lower", "ci_upper"])
            for label, key, n in [
                ("exposed", "mean_mc_jaccard_exposed", n_exp),
                ("unexposed", "mean_mc_jaccard_unexposed", n_unexp),
            ]:
                stat = boot.statistics[key]
                w.writerow([
                    dimension, label, n,
                    points[key],
                    stat.lower if stat.interval_reported else "",
                    stat.upper if stat.interval_reported else "",
                ])
        paths.append(path)

    return paths


def write_metadata(
    all_results: dict[str, dict],
    strata: dict[str, str],
    checks: dict[str, Any],
    authority_checks: tuple,
    output_path: Path,
) -> None:
    """Write run_metadata.json."""
    stratum_counts = Counter(strata.values())

    dimension_summaries = {}
    for dimension in DIMENSIONS:
        res = all_results[dimension]
        boot = res["bootstrap"]
        dim_key = "domains" if dimension == "Research Domains" else "purposes"

        boot_summary = {}
        for name in STATISTIC_NAMES:
            stat = boot.statistics[name]
            boot_summary[name] = {
                "valid": stat.valid,
                "invalid": stat.invalid,
                "interval_reported": stat.interval_reported,
                "lower": stat.lower,
                "upper": stat.upper,
            }

        dimension_summaries[dim_key] = {
            "n_exposed": res["n_exposed"],
            "n_unexposed": res["n_unexposed"],
            "point_estimates": {k: v for k, v in res["points"].items()},
            "bootstrap": boot_summary,
            "state_counts_exposed": dict(res["state_counts_exposed"]),
            "state_counts_unexposed": dict(res["state_counts_unexposed"]),
        }

    metadata = {
        "analysis": "enrichment_calibration_exploratory",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "population": "baseline",
        "n_records": 150,
        "frame_membership": {
            "domain_only": stratum_counts["domain_only"],
            "purpose_only": stratum_counts["purpose_only"],
            "both": stratum_counts["both"],
            "none": stratum_counts["none"],
        },
        "bootstrap": {
            "seed": SEED,
            "attempted_replicates": REPLICATES,
            "minimum_valid": MIN_VALID,
            "method": "record-level resampling with replacement, not stratified by exposure",
        },
        "dimensions": dimension_summaries,
        "checks": checks,
        "data_sources": {
            "raw_export_sha256": "29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d",
            "baseline_sample_sha256": "0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11",
            "model_output_sha256_lf_normalised": "6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299",
            "taxonomy_sha256": "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de",
        },
        "authority_checks": [
            {"artifact_id": c.manifest_id, "path": str(c.path), "expected_sha256": c.expected_sha256, "matched": c.matched}
            for c in authority_checks
        ],
        "platform": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "system": platform.system(),
        },
    }

    output_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")


def main() -> None:
    print("Verifying authorities...")
    authority_checks = verify_authorities()
    failed = [c for c in authority_checks if not c.matched]
    if failed:
        for c in failed:
            print(f"  FAILED: {c.artifact_id} — {c.path}")
        raise RuntimeError("Authority verification failed")
    print(f"  All {len(authority_checks)} authorities verified.")

    print("Building Stage A data...")
    data = build_stage_a_data()
    print(f"  {data.raw_rows} rows, {len(data.baseline_ids)} baseline, {len(data.hard_case_ids)} hard-case.")

    print("Loading baseline strata from frozen sampling artefact...")
    strata = load_baseline_strata(data)
    stratum_counts = Counter(strata.values())
    print(f"  domain_only={stratum_counts['domain_only']}, purpose_only={stratum_counts['purpose_only']}, "
          f"both={stratum_counts['both']}, none={stratum_counts['none']}")

    print("Verifying strata against crossmodel_comparison.csv...")
    verify_strata_against_comparison(strata)
    print("  Strata verified.")

    known_frame_total = 386
    known_domain_only = 186
    known_purpose_only = 143
    known_both = 57
    stratum_csv = ROOT / "analysis" / "outputs" / "crossmodel_disagreement_stratum.csv"
    full_stratum = pd.read_csv(stratum_csv)
    full_counts = full_stratum["disagreement_layer"].value_counts()
    assert len(full_stratum) == known_frame_total, f"Frame total: {len(full_stratum)} != {known_frame_total}"
    assert full_counts.get("domains-only", 0) == known_domain_only
    assert full_counts.get("purposes-only", 0) == known_purpose_only
    assert full_counts.get("both", 0) == known_both
    print(f"  Full-frame totals reconciled: {known_frame_total} total ({known_domain_only}/{known_purpose_only}/{known_both}).")

    checks: dict[str, Any] = {
        "strata_verified_against_comparison": True,
        "full_frame_totals_reconciled": True,
    }

    all_results: dict[str, dict] = {}

    for dimension in DIMENSIONS:
        dim_tag = "domains" if dimension == "Research Domains" else "purposes"
        print(f"\n--- {dimension} ---")

        print("  Building record data...")
        records = build_record_data(data, dimension, strata)
        exp_ids, unexp_ids = exposure_ids(strata, dimension)
        n_exp = len(exp_ids)
        n_unexp = len(unexp_ids)
        print(f"  Exposed: {n_exp}, Unexposed: {n_unexp}")

        print("  Building encoded panels...")
        encoded, rid_to_idx = build_encoded_data(data, dimension)
        assert len(encoded.ratings) == 150, f"Expected 150 complete panels, got {len(encoded.ratings)}"

        print("  Check: alpha ABC reconciliation...")
        check_alpha_reconciliation(encoded, dimension)
        checks[f"alpha_abc_reconciliation_{dim_tag}"] = True
        print(f"    PASS — α ABC matches exported value ({EXPORTED_ALPHA_ABC[dimension]})")

        print("  Check: consensus-state counts...")
        check_state_counts(records, dimension)
        checks[f"state_counts_reconciliation_{dim_tag}"] = True
        expected = EXPECTED_STATE_COUNTS[dimension]
        print(f"    PASS — S1={expected['S1']}, S2={expected['S2']}, S3={expected['S3']}, S4={expected['S4']}")

        print("  Computing point estimates...")
        points = compute_point_estimates(records, encoded, rid_to_idx)

        state_counts_exp = Counter(r["state"] for r in records if r["exposed"])
        state_counts_unexp = Counter(r["state"] for r in records if not r["exposed"])

        print(f"  Running bootstrap ({REPLICATES} replicates, seed {SEED})...")
        evaluator = make_evaluator(encoded, rid_to_idx)
        boot = bootstrap_joint(
            records,
            evaluator,
            statistic_names=list(STATISTIC_NAMES),
            attempted_replicates=REPLICATES,
            seed=SEED,
            minimum_valid_fraction=MIN_VALID / REPLICATES,
        )

        for name in STATISTIC_NAMES:
            stat = boot.statistics[name]
            print(f"    {name}: valid={stat.valid}/{REPLICATES}, reported={stat.interval_reported}")

        all_results[dimension] = {
            "points": points,
            "bootstrap": boot,
            "records": records,
            "n_exposed": n_exp,
            "n_unexposed": n_unexp,
            "state_counts_exposed": state_counts_exp,
            "state_counts_unexposed": state_counts_unexp,
        }

    print("\nWriting results...")
    results_path = OUTPUT_DIR / "results_enrichment_calibration.md"
    write_results_md(all_results, strata, results_path)
    print(f"  {results_path.name}")

    csv_paths = write_csvs(all_results, strata, OUTPUT_DIR)
    for p in csv_paths:
        print(f"  {p.name}")

    metadata_path = OUTPUT_DIR / "run_metadata.json"
    write_metadata(all_results, strata, checks, authority_checks, metadata_path)
    print(f"  {metadata_path.name}")

    print("\nAll checks passed. Done.")


if __name__ == "__main__":
    main()
