"""GHA1: exploratory comparison of GPT-5.5, Fable 5 and three coders (post hoc; not preregistered).

Specification: SPEC_gpt55_human_agreement_2026-11-17.md (dated plan, written before any new quantity was calculated).
Reuses the Stage A loaders, validator, MASI distance and coincidence-form alpha. Reads only the active baseline and
hard-case records. No model API calls; nothing frozen is modified.

Results are written only to a gitignored folder under preregistration_restricted/; the repository holds code only.

Run from the repository root:  python -m analysis.exploratory_gpt55_human_agreement.run
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from random import Random

import numpy as np

from analysis.scratch_coder_stage_a.agreement import alpha_encoded, bootstrap_replacement, encode_panels, encoded_replacement_statistics
from analysis.scratch_coder_stage_a.config import BOOTSTRAP_REPLICATES, CODERS, MINIMUM_VALID_REPLICATES, ROOT, SEED_BOOTSTRAP
from analysis.scratch_coder_stage_a.load import read_manifest_csv, resolve_manifest_row, semicolon_set, sha256_file, verify_authorities
from analysis.scratch_coder_stage_a.panels import _taxonomy_labels, build_stage_a_data, dimension_panels
from analysis.scratch_coder_stage_a.sufficiency import SPLIT, SUFFICIENCY_LABELS, majority_category
from analysis.scratch_coder_stage_a.taxonomy import FIT_LABELS
from analysis.validation.metrics import jaccard_similarity, masi_distance

HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_gpt55_human_agreement_2026-11-17.md"
STAGE_A = ROOT / "analysis/outputs_validation_scratch_20260824"
STRATA_DIR = ROOT / "analysis/outputs_validation_scratch_hard_case_strata_20260825"
DIMS = ("Research Domains", "Analytical Purposes")
FIELD = {"Research Domains": "domains", "Analytical Purposes": "purposes"}
GPT_FIELD = {"Research Domains": "substantive_domains", "Analytical Purposes": "analytical_purpose"}
SOURCES = ("C01", "C02", "C03", "Fable 5", "GPT-5.5")
F, G = 3, 4  # column indices of the two models
STRATA = ("domain_only", "purpose_only", "both")
DIVERGENT_STRATA = {"Research Domains": {"domain_only", "both"}, "Analytical Purposes": {"purpose_only", "both"}}
UNCLEAR = "Unclear from Register Entry"
CHECKPOINTS = {  # from the instruction; rounded to six decimals there
    ("baseline", "Research Domains"): (0.526337, 0.583385, 0.527982, 0.573524),
    ("baseline", "Analytical Purposes"): (0.292110, 0.275617, 0.249442, 0.357540),
    ("hard_case", "Research Domains"): (0.462288, 0.438664, 0.442947, 0.434898),
    ("hard_case", "Analytical Purposes"): (0.291742, 0.182599, 0.177920, 0.255618),
}
PATTERNS = (
    "P1 coders unanimous, matching Fable 5",
    "P2 coders unanimous, matching GPT-5.5",
    "P3 coders unanimous on a third set",
    "P4 not unanimous; exact match to each model",
    "P5 not unanimous; exact match to Fable 5 only",
    "P6 not unanimous; exact match to GPT-5.5 only",
    "P7 not unanimous; no exact match to either model",
)
AGREE_PATTERNS = (
    "A1 coders unanimous, matching the shared model set",
    "A2 coders unanimous on another set",
    "A3 not unanimous; at least one coder matches the shared set",
    "A4 not unanimous; no coder matches the shared set",
)


# ---------------------------------------------------------------- helpers
def manifest_hash_ok(path: Path, expected: str) -> tuple[bool, str]:
    raw = path.read_bytes()
    for blob in (raw, raw.replace(b"\r\n", b"\n")):
        digest = hashlib.sha256(blob).hexdigest()
        if digest == expected:
            return True, digest
    return False, hashlib.sha256(raw).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def show(labels) -> str:
    return "MISSING" if labels is None else "; ".join(sorted(labels)) if labels else "(empty)"


def interval(values: list[float | None], attempts: int) -> dict:
    valid = np.array([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    out = {"valid": int(len(valid)), "invalid": int(attempts - len(valid))}
    if len(valid) >= int(np.ceil(0.9 * attempts)):
        out.update(lower=float(np.quantile(valid, 0.025, method="linear")), upper=float(np.quantile(valid, 0.975, method="linear")),
                   reported=True)
    else:
        out.update(lower=None, upper=None, reported=False)
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"No rows for {path.name}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------- statistics
def statistics(ratings: np.ndarray, distance: np.ndarray, idx: np.ndarray | None = None) -> dict[str, float | None]:
    r = ratings if idx is None else ratings[idx]
    out: dict[str, float | None] = {"alpha_ABC": alpha_encoded(r[:, [0, 1, 2]], distance)}
    for tag, col in (("F", F), ("G", G)):
        deltas = []
        for position, coder in enumerate(CODERS):
            cols = [0, 1, 2]
            cols[position] = col
            alpha = alpha_encoded(r[:, cols], distance)
            out[f"{tag}_alpha_replacing_{coder}"] = alpha
            delta = None if alpha is None or out["alpha_ABC"] is None else alpha - out["alpha_ABC"]
            out[f"{tag}_delta_replacing_{coder}"] = delta
            deltas.append(delta)
        out[f"{tag}_delta_min"] = None if any(d is None for d in deltas) else min(deltas)
    for coder in CODERS:
        g, f = out[f"G_alpha_replacing_{coder}"], out[f"F_alpha_replacing_{coder}"]
        out[f"contrast_G_minus_F_replacing_{coder}"] = None if g is None or f is None else g - f
    return out


def pair_rows(records: list[tuple], population: str, stratum: str, dimension: str) -> list[dict]:
    rows = []
    for i, j in combinations(range(5), 2):
        n = len(records)
        exact = sum(1 for rec in records if rec[i] == rec[j])
        jac = [float(jaccard_similarity(rec[i], rec[j])) for rec in records]
        family = ("coder–coder" if j < 3 else "Fable 5–coder" if j == F and i < 3 else
                  "GPT-5.5–coder" if j == G and i < 3 else "Fable 5–GPT-5.5")
        rows.append({"population": population, "stratum": stratum, "dimension": dimension, "source_a": SOURCES[i],
                     "source_b": SOURCES[j], "family": family, "records": n, "exact_set_n": exact,
                     "exact_set_proportion": exact / n if n else None, "mean_jaccard": float(np.mean(jac)) if n else None})
    return rows


def pattern_for(humans: tuple, fable, gpt) -> str:
    if humans[0] == humans[1] == humans[2]:
        return PATTERNS[0] if humans[0] == fable else PATTERNS[1] if humans[0] == gpt else PATTERNS[2]
    mf, mg = any(h == fable for h in humans), any(h == gpt for h in humans)
    return PATTERNS[3] if mf and mg else PATTERNS[4] if mf else PATTERNS[5] if mg else PATTERNS[6]


def agree_pattern_for(humans: tuple, shared) -> str:
    if humans[0] == humans[1] == humans[2]:
        return AGREE_PATTERNS[0] if humans[0] == shared else AGREE_PATTERNS[1]
    return AGREE_PATTERNS[2] if any(h == shared for h in humans) else AGREE_PATTERNS[3]


# ---------------------------------------------------------------- main
def main() -> None:
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    # All results stay out of the repository (investigator instruction, 17 November 2026): one gitignored folder,
    # with the record-level file in a restricted subfolder.
    out_dir = ROOT / f"preregistration_restricted/exploratory_gpt55_human_agreement_{stamp}"
    restricted_dir = out_dir / "record_level"
    restricted_dir.mkdir(parents=True)
    audit: list[dict] = []
    discrepancies: list[dict] = []

    def check(name: str, passed: bool, observed="", expected="", hard: bool = True) -> None:
        audit.append({"check": name, "observed": str(observed), "expected": str(expected), "status": "passed" if passed else "FAILED"})
        if not passed and hard:
            raise SystemExit(f"Check failed: {name} (observed {observed}, expected {expected})")

    # ---- inputs and identities
    authorities = verify_authorities()
    check("Stage A authority hashes (POST-028, POST-019, POST-009, POST-011, MOD-001, MOD-006 and others)", True, len(authorities))
    release = (ROOT / resolve_manifest_row("MOD-011")["current_path"]).read_text(encoding="utf-8")
    check("production model identity in MOD-011 release manifest", "model_identifier: claude-fable-5" in release, "claude-fable-5", "claude-fable-5")
    gpt_row = resolve_manifest_row("EVD-005")
    gpt_path = ROOT / gpt_row["current_path"]
    ok, digest = manifest_hash_ok(gpt_path, gpt_row["sha256"])
    check("EVD-005 GPT-5.5 output hash", ok, digest, gpt_row["sha256"])
    gpt_meta_row = resolve_manifest_row("EVD-027")
    gpt_meta = json.loads((ROOT / gpt_meta_row["current_path"]).read_text(encoding="utf-8"))
    data = build_stage_a_data()
    check("baseline active records", len(data.baseline_ids) == 150, len(data.baseline_ids), 150)
    check("hard-case active records", len(data.hard_case_ids) == 75, len(data.hard_case_ids), 75)
    hard = read_manifest_csv("POST-011")
    stratum_of = dict(zip(hard["record_id"], hard["hard_case_stratum"]))
    check("hard-case strata 25/25/25", Counter(stratum_of.values()) == Counter({s: 25 for s in STRATA}), dict(Counter(stratum_of.values())), "25 each")
    check("hard-case records forced in for an accompanying tag disagreement (count only)", True,
          int(hard["forced_into_active_hard"].isin(["True", "1"]).sum()), "", hard=False)
    active = sorted(data.formal_ids)

    gpt_all = list(csv.DictReader(gpt_path.open(encoding="utf-8-sig", newline="")))
    gpt_ids = [r["Record ID"] for r in gpt_all]
    check("EVD-005 Record IDs unique", len(gpt_ids) == len(set(gpt_ids)), len(gpt_ids) - len(set(gpt_ids)), 0)
    gpt_by_id = {r["Record ID"]: r for r in gpt_all if r["Record ID"] in data.formal_ids}  # active records only
    check("every active record joins one-to-one to EVD-005", set(gpt_by_id) == set(active), len(gpt_by_id), 225)
    prod = read_manifest_csv("MOD-006")
    prod = prod[prod["Record ID"].isin(data.formal_ids)].set_index("Record ID")
    mismatched = [rid for rid in active if (prod.at[rid, "Title"], prod.at[rid, "Datasets Used"]) !=
                  (gpt_by_id[rid]["Title"], gpt_by_id[rid]["Datasets Used"])]
    check("title and datasets identical in MOD-006 and EVD-005 for every active record", not mismatched, len(mismatched), 0)

    allowed = _taxonomy_labels()
    allowed_layer = {"Research Domains": allowed["domains"], "Analytical Purposes": allowed["purposes"]}

    def cardinality_ok(dimension: str, labels: frozenset) -> bool:
        if not labels:
            return False
        if UNCLEAR in labels:
            return len(labels) == 1
        return dimension == "Research Domains" or len(labels) <= 2

    gpt_sets: dict[str, dict[str, frozenset | None]] = {}
    gpt_invalid = Counter()
    fable_cardinality_flags = Counter()
    for rid in active:
        row = gpt_by_id[rid]
        gpt_sets[rid] = {}
        for dim in DIMS:
            labels = semicolon_set(row[GPT_FIELD[dim]])
            valid = row["gpt_status"] == "ok" and not row["validation_error"] and labels <= allowed_layer[dim] and cardinality_ok(dim, labels)
            gpt_sets[rid][dim] = labels if valid else None
            if not valid:
                gpt_invalid[dim] += 1
            if not cardinality_ok(dim, data.model[rid][dim]):
                fable_cardinality_flags[dim] += 1
    for dim in DIMS:
        check(f"GPT-5.5 valid classifications, {dim}", True, 225 - gpt_invalid[dim], 225, hard=False)
        check(f"Fable 5 outputs outside the cardinality rule, {dim} (kept, as in Stage A)", True, fable_cardinality_flags[dim], 0, hard=False)

    # ---- five-source records
    responses = data.responses.set_index(["record_id", "coder"])

    def coder_set(rid: str, coder: str, dim: str):
        row = responses.loc[(rid, coder)]
        return row[FIELD[dim]] if row["complete"] else None

    five = {rid: {dim: (coder_set(rid, "C01", dim), coder_set(rid, "C02", dim), coder_set(rid, "C03", dim),
                        data.model[rid][dim], gpt_sets[rid][dim]) for dim in DIMS} for rid in active}
    population_ids = {"baseline": sorted(data.baseline_ids), "hard_case": sorted(data.hard_case_ids)}

    # ---- reproduction of Stage A
    repro: list[dict] = []
    stage_a_points = {(r["population"], r["dimension"], r["panel"]): r for r in csv.DictReader((STAGE_A / "replacement_panel_results.csv").open(encoding="utf-8"))}
    stage_a_complete: dict[tuple, int] = {}
    for population, ids in population_ids.items():
        for dim in DIMS:
            panels = dimension_panels(data, frozenset(ids), dim)
            encoded = encode_panels(panels, masi_distance)
            stage_a_complete[(population, dim)] = len(encoded.ratings)
            point = encoded_replacement_statistics(encoded)
            for name, reference in zip(("alpha_ABC", "alpha_LBC", "alpha_ALC", "alpha_ABL"), CHECKPOINTS[(population, dim)]):
                diff = point[name] - reference
                repro.append({"population": population, "dimension": dim, "statistic": name, "kind": "point vs instruction checkpoint",
                              "reproduced": point[name], "reference": reference, "difference": diff, "status": "passed" if abs(diff) < 1e-6 else "FAILED"})
                check(f"reproduce {population} {dim} {name}", abs(diff) < 1e-6, round(point[name], 6), reference)
            if population == "baseline":  # Stage A's own bootstrap stream; compare intervals too
                boot = bootstrap_replacement(encoded)
                for name, panel in (("alpha_ABC", "ABC"), ("alpha_LBC", "LBC"), ("alpha_ALC", "ALC"), ("alpha_ABL", "ABL")):
                    ref = stage_a_points[(population, dim, panel)]
                    iv = interval([row[name] for row in boot], BOOTSTRAP_REPLICATES)
                    for bound, key in (("lower", "ci_lower"), ("upper", "ci_upper")):
                        diff = iv[bound] - float(ref[key])
                        repro.append({"population": population, "dimension": dim, "statistic": f"{name} interval {bound}",
                                      "kind": "Stage A bootstrap stream", "reproduced": iv[bound], "reference": float(ref[key]),
                                      "difference": diff, "status": "passed" if abs(diff) < 1e-9 else "FAILED"})
                        check(f"reproduce baseline {dim} {name} interval {bound}", abs(diff) < 1e-9, iv[bound], ref[key])

    # ---- audit of the historical hard-case stratum fields
    hist = list(csv.DictReader((STRATA_DIR / "hard_case_stratum_exact_set_jaccard.csv").open(encoding="utf-8")))
    human_hist = list(csv.DictReader((STRATA_DIR / "hard_case_stratum_human_pair_agreement.csv").open(encoding="utf-8")))
    for row in hist:
        stratum, dim = row["stratum"], row["dimension"]
        if dim not in DIMS:
            continue
        ids = [rid for rid in population_ids["hard_case"] if stratum_of[rid] == stratum]
        complete = [five[rid][dim] for rid in ids if None not in five[rid][dim][:4]]
        coder_index = {"A": 0, "B": 1, "C": 2}[row["pair"].split("-")[1]]
        exact = np.mean([rec[F] == rec[coder_index] for rec in complete])
        jac = np.mean([float(jaccard_similarity(rec[F], rec[coder_index])) for rec in complete])
        model_coder_exact = np.mean([np.mean([rec[F] == rec[c] for rec in complete]) for c in range(3)])
        model_coder_jac = np.mean([np.mean([float(jaccard_similarity(rec[F], rec[c])) for rec in complete]) for c in range(3)])
        human_exact = np.mean([np.mean([rec[a] == rec[b] for rec in complete]) for a, b in ((0, 1), (0, 2), (1, 2))])
        human_jac = np.mean([np.mean([float(jaccard_similarity(rec[a], rec[b])) for rec in complete]) for a, b in ((0, 1), (0, 2), (1, 2))])
        for field, historical, recomputed, alternative in (
                ("exact_match_proportion", float(row["exact_match_proportion"]), exact, None),
                ("mean_jaccard", float(row["mean_jaccard"]), jac, None),
                ("mean_model_coder_exact_set", float(row["mean_model_coder_exact_set"]), model_coder_exact, human_exact),
                ("mean_model_coder_jaccard", float(row["mean_model_coder_jaccard"]), model_coder_jac, human_jac)):
            matches = abs(historical - recomputed) < 1e-9
            equals_human = alternative is not None and abs(historical - alternative) < 1e-9
            if not matches or equals_human:
                discrepancies.append({"file": str((STRATA_DIR / "hard_case_stratum_exact_set_jaccard.csv").relative_to(ROOT)).replace("\\", "/"),
                                      "row": f"{stratum} {dim} {row['pair']}", "field": field, "historical": historical,
                                      "recomputed_model_coder": recomputed, "mean_human_human": alternative,
                                      "finding": "equals the mean human-human value" if equals_human else "differs from the raw recomputation"})
    model_file_issues = len(discrepancies)
    human_file = str((STRATA_DIR / "hard_case_stratum_human_pair_agreement.csv").relative_to(ROOT)).replace("\\", "/")
    for row in human_hist:
        stratum, dim = row["stratum"], row["dimension"]
        if dim not in DIMS:
            continue
        ids = [rid for rid in population_ids["hard_case"] if stratum_of[rid] == stratum]
        complete = [five[rid][dim] for rid in ids if None not in five[rid][dim][:4]]
        human = (np.mean([np.mean([rec[a] == rec[b] for rec in complete]) for a, b in ((0, 1), (0, 2), (1, 2))]),
                 np.mean([np.mean([float(jaccard_similarity(rec[a], rec[b])) for rec in complete]) for a, b in ((0, 1), (0, 2), (1, 2))]))
        model = (np.mean([np.mean([rec[F] == rec[c] for rec in complete]) for c in range(3)]),
                 np.mean([np.mean([float(jaccard_similarity(rec[F], rec[c])) for rec in complete]) for c in range(3)]))
        for k, field in enumerate(("mean_model_coder_exact_set", "mean_model_coder_jaccard")):
            historical = float(row[field])
            if abs(historical - human[k]) < 1e-9 and abs(historical - model[k]) >= 1e-9:
                discrepancies.append({"file": human_file, "row": f"{stratum} {dim} {row['pair']}", "field": field, "historical": historical,
                                      "recomputed_model_coder": model[k], "mean_human_human": human[k],
                                      "finding": "field named model-coder holds the mean human-human value (label error; values correct "
                                                 "for human-human); not used as an input; file not changed"})
            elif abs(historical - model[k]) >= 1e-9:
                discrepancies.append({"file": human_file, "row": f"{stratum} {dim} {row['pair']}", "field": field, "historical": historical,
                                      "recomputed_model_coder": model[k], "mean_human_human": human[k],
                                      "finding": "differs from both recomputations"})
    if model_file_issues == 0:
        discrepancies.append({"file": "analysis/outputs_validation_scratch_hard_case_strata_20260825/hard_case_stratum_exact_set_jaccard.csv",
                              "row": "all Research Domains and Analytical Purposes rows", "field": "exact_match_proportion; mean_jaccard; "
                              "mean_model_coder_exact_set; mean_model_coder_jaccard", "historical": "", "recomputed_model_coder": "",
                              "mean_human_human": "", "finding": "no discrepancy: every field equals its raw recomputation, and the two "
                              "mean_model_coder fields equal the mean of the three Fable 5–coder values, not the human-human mean"})
    summary_md = (STRATA_DIR / "hard_case_stratum_summary.md").read_text(encoding="utf-8")

    # ---- complete-case matrices, points and bootstraps
    pairwise, replacement, stratum_points, label_rows = [], [], [], []
    populations_used: dict[tuple, int] = {}
    divergence_rows = []
    for population, ids in population_ids.items():
        for dim in DIMS:
            complete_ids = [rid for rid in ids if None not in five[rid][dim]]
            populations_used[(population, dim)] = len(complete_ids)
            excluded = len(ids) - len(complete_ids)
            check(f"{population} {dim}: five-source complete cases", True, f"{len(complete_ids)} of {len(ids)}", "", hard=False)
            same_as_stage_a = len(complete_ids) == stage_a_complete[(population, dim)] and excluded == 0
            records = [five[rid][dim] for rid in complete_ids]
            pairwise += pair_rows(records, population, "all", dim)
            if population == "hard_case":
                for stratum in STRATA:
                    pairwise += pair_rows([five[rid][dim] for rid in complete_ids if stratum_of[rid] == stratum], population, stratum, dim)
            # encoding
            categories = tuple(dict.fromkeys(v for rec in records for v in rec))
            index = {v: k for k, v in enumerate(categories)}
            ratings = np.array([[index[v] for v in rec] for rec in records], dtype=np.int32)
            distance = np.array([[float(masi_distance(a, b)) for b in categories] for a in categories])
            point = statistics(ratings, distance)
            # zero-contrast check: GPT column replaced by the Fable column
            twin = ratings.copy()
            twin[:, G] = twin[:, F]
            zero = statistics(twin, distance)
            check(f"{population} {dim}: identical model outputs give zero contrasts",
                  all(abs(zero[f"contrast_G_minus_F_replacing_{c}"]) < 1e-12 for c in CODERS), "0", "0")
            # bootstrap
            generator = Random(SEED_BOOTSTRAP)
            boots = []
            if population == "baseline":
                n = len(records)
                for _ in range(BOOTSTRAP_REPLICATES):
                    idx = np.fromiter((generator.randrange(n) for _ in range(n)), dtype=np.int32, count=n)
                    boots.append(statistics(ratings, distance, idx))
                scheme = "record bootstrap over the baseline (Stage A stream)" if same_as_stage_a else "record bootstrap over the baseline complete cases"
            else:
                positions = {s: [k for k, rid in enumerate(complete_ids) if stratum_of[rid] == s] for s in STRATA}
                for _ in range(BOOTSTRAP_REPLICATES):
                    idx = np.array([pos[generator.randrange(len(pos))] for s in STRATA for pos in [positions[s]] for _ in range(len(pos))], dtype=np.int32)
                    boots.append(statistics(ratings, distance, idx))
                scheme = "exploratory conditional bootstrap within each hard-case stratum at its observed size"
            for name, value in point.items():
                iv = interval([b[name] for b in boots], BOOTSTRAP_REPLICATES)
                model = "GPT-5.5" if name.startswith("G_") else "Fable 5" if name.startswith("F_") else "both" if name.startswith("contrast") else "none"
                replaced = next((c for c in CODERS if name.endswith(c)), "")
                replacement.append({"population": population, "dimension": dim, "statistic": name, "model": model, "replaced_coder": replaced,
                                    "records": len(records), "point_estimate": value, "interval_lower_95": iv["lower"],
                                    "interval_upper_95": iv["upper"], "interval_reported": iv["reported"], "draws_valid": iv["valid"],
                                    "draws_invalid": iv["invalid"], "resampling": scheme,
                                    "same_population_as_stage_a": same_as_stage_a})
            if population == "hard_case":
                for stratum in STRATA:
                    mask = np.array([stratum_of[rid] == stratum for rid in complete_ids])
                    sub = ratings[mask]
                    sub_categories = sorted(set(sub.ravel()))
                    spoint = statistics(sub, distance)
                    for name, value in spoint.items():
                        stratum_points.append({"population": population, "stratum": stratum, "dimension": dim, "statistic": name,
                                               "records": int(mask.sum()), "point_estimate": value,
                                               "categories_used": len(sub_categories), "note": "point estimate only; n = 25; prevalence-sensitive"})
            # label frequencies and set sizes
            for k, source in enumerate(SOURCES):
                sets = [rec[k] for rec in records]
                counts = Counter(label for s in sets for label in s)
                label_rows.append({"population": population, "dimension": dim, "source": source, "label": "(mean set size)",
                                   "records_with_label": "", "value": float(np.mean([len(s) for s in sets]))})
                for label in sorted(allowed_layer[dim]):
                    label_rows.append({"population": population, "dimension": dim, "source": source, "label": label,
                                       "records_with_label": counts.get(label, 0), "value": counts.get(label, 0) / len(sets)})
            # divergence against recorded strata
            div = [rid for rid in ids if five[rid][dim][F] is not None and five[rid][dim][G] is not None and five[rid][dim][F] != five[rid][dim][G]]
            row = {"population": population, "dimension": dim, "records": len(ids), "models_differ": len(div)}
            if population == "hard_case":
                expected = {rid for rid in ids if stratum_of[rid] in DIVERGENT_STRATA[dim]}
                row["expected_from_strata"] = len(expected)
                row["mismatched_records"] = len(expected.symmetric_difference(div))
                if expected.symmetric_difference(div):
                    discrepancies.append({"file": "POST-011 hard_case_stratum against MOD-006/EVD-005", "row": dim, "field": "model divergence",
                                          "historical": len(expected), "recomputed_model_coder": len(div), "mean_human_human": "",
                                          "finding": f"{len(expected.symmetric_difference(div))} records differ between the recorded strata and the frozen outputs; strata kept"})
            divergence_rows.append(row)

    # ---- symmetry and label-order invariance (pairwise)
    sample = population_ids["baseline"][:40]
    for dim in DIMS:
        recs = [five[rid][dim] for rid in sample if None not in five[rid][dim]]
        # symmetry: Jaccard and exact equality are unchanged when the two sources swap, record by record
        sym = all(jaccard_similarity(r[i], r[j]) == jaccard_similarity(r[j], r[i]) and (r[i] == r[j]) == (r[j] == r[i])
                  for r in recs for i, j in combinations(range(5), 2))
        # label order: rebuilding every set from its labels in reverse order changes no pairwise result
        rebuilt = [tuple(frozenset(list(reversed(sorted(s)))) for s in rec) for rec in recs]
        order = pair_rows(recs, "check", "all", dim) == pair_rows(rebuilt, "check", "all", dim)
        check(f"pairwise symmetry and label-order invariance, {dim}", sym and order, "", "")

    # ---- record-level diagnostics and patterns
    suff_major, fit_major = {}, {}
    for rid in active:
        s_values = tuple(responses.loc[(rid, c)]["sufficiency"] for c in CODERS)
        f_values = tuple(responses.loc[(rid, c)]["taxonomy_fit"] for c in CODERS)
        suff_major[rid] = majority_category(tuple(int(v) for v in s_values), SUFFICIENCY_LABELS) if all(v in SUFFICIENCY_LABELS for v in s_values) else "Missing"
        fit_major[rid] = majority_category(tuple(int(v) for v in f_values), FIT_LABELS) if all(v in FIT_LABELS for v in f_values) else "Missing"
    record_rows, pattern_rows = [], []
    for population, ids in population_ids.items():
        for dim in DIMS:
            for rid in ids:
                rec = five[rid][dim]
                stratum = "baseline" if population == "baseline" else stratum_of[rid]
                complete = None not in rec
                models_valid = rec[F] is not None and rec[G] is not None
                differ = models_valid and rec[F] != rec[G]
                unanimous = complete and rec[0] == rec[1] == rec[2]
                pattern = pattern_for(rec[:3], rec[F], rec[G]) if complete and differ else ""
                agree = agree_pattern_for(rec[:3], rec[F]) if complete and models_valid and not differ else ""
                row = {"population": population, "stratum": stratum, "record_id": rid, "dimension": dim,
                       **{f"labels_{s.replace(' ', '_').replace('.', '').replace('-', '')}": show(rec[k]) for k, s in enumerate(SOURCES)},
                       "models_differ": differ if models_valid else "", "dimension_in_selection_stratum":
                           (stratum in DIVERGENT_STRATA[dim]) if population == "hard_case" else "",
                       "coders_unanimous": unanimous if complete else "", "pattern_models_differ": pattern, "pattern_models_agree": agree,
                       "sufficiency_majority": suff_major[rid], "taxonomy_fit_majority": fit_major[rid]}
                for c, coder in enumerate(CODERS):
                    for k, model in ((F, "fable5"), (G, "gpt55")):
                        if rec[c] is None or rec[k] is None:
                            row[f"{coder}_{model}_exact"] = row[f"{coder}_{model}_jaccard"] = ""
                        else:
                            row[f"{coder}_{model}_exact"] = rec[c] == rec[k]
                            row[f"{coder}_{model}_jaccard"] = float(jaccard_similarity(rec[c], rec[k]))
                record_rows.append(row)
    # exactly one pattern per eligible divergent record-dimension
    eligible = [r for r in record_rows if r["models_differ"] is True and r["coders_unanimous"] != ""]
    check("every divergent record-dimension with complete ratings has exactly one pattern",
          all(r["pattern_models_differ"] in PATTERNS for r in eligible) and all(not r["pattern_models_agree"] for r in eligible),
          len(eligible), len(eligible))
    for population in population_ids:
        for dim in DIMS:
            groups = ["all"] + (list(STRATA) if population == "hard_case" else [])
            for group in groups:
                rows = [r for r in record_rows if r["population"] == population and r["dimension"] == dim and (group == "all" or r["stratum"] == group)]
                differ = [r for r in rows if r["pattern_models_differ"]]
                agree = [r for r in rows if r["pattern_models_agree"]]
                for name in PATTERNS:
                    pattern_rows.append({"population": population, "stratum": group, "dimension": dim, "case": "models differ", "pattern": name,
                                         "records": sum(r["pattern_models_differ"] == name for r in differ), "denominator": len(differ)})
                for name in AGREE_PATTERNS:
                    pattern_rows.append({"population": population, "stratum": group, "dimension": dim, "case": "models agree", "pattern": name,
                                         "records": sum(r["pattern_models_agree"] == name for r in agree), "denominator": len(agree)})
    crosstab = []
    for population in population_ids:
        for dim in DIMS:
            rows = [r for r in record_rows if r["population"] == population and r["dimension"] == dim and r["pattern_models_differ"]]
            for rating, values in (("sufficiency_majority", list(SUFFICIENCY_LABELS.values()) + [SPLIT, "Missing"]),
                                   ("taxonomy_fit_majority", list(FIT_LABELS.values()) + [SPLIT, "Missing"])):
                for name in PATTERNS:
                    in_pattern = [r for r in rows if r["pattern_models_differ"] == name]
                    for value in values:
                        crosstab.append({"population": population, "dimension": dim, "rating": rating, "pattern": name, "rating_value": value,
                                         "records": sum(r[rating] == value for r in in_pattern), "pattern_total": len(in_pattern)})

    # ---- write outputs
    tables = {
        "GHA1T001_input_join_audit.csv": audit,
        "GHA1T002_reproduction.csv": repro,
        "GHA1T003_pairwise_agreement.csv": pairwise,
        "GHA1T004_replacement_and_contrasts.csv": replacement,
        "GHA1T005_hard_case_stratum_points.csv": stratum_points,
        "GHA1T006_label_frequency_and_set_size.csv": label_rows,
        "GHA1T007_record_patterns.csv": pattern_rows,
        "GHA1T008_patterns_by_sufficiency_and_fit.csv": crosstab,
        "GHA1T009_model_divergence_check.csv": divergence_rows,
        "discrepancy_log.csv": discrepancies,
    }
    for name, rows in tables.items():
        write_csv(out_dir / name, rows)
    write_csv(restricted_dir / "GHA1_record_level_diagnostics.csv", record_rows)

    from analysis.exploratory_gpt55_human_agreement import figures, report
    figure_files = figures.draw_all(out_dir, pairwise, replacement)
    report_path = report.write(out_dir, tables, populations_used, stage_a_complete, gpt_invalid, divergence_rows, summary_md)

    metadata = {
        "analysis": "GHA1 exploratory comparison of GPT-5.5, Fable 5 and three coders",
        "status": "post hoc and exploratory; not preregistered; production-model results inspected beforehand",
        "run_started_utc": started.isoformat(), "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python -m analysis.exploratory_gpt55_human_agreement.run",
        "git_head": git("rev-parse", "HEAD"), "git_status_porcelain": git("status", "--porcelain").splitlines(),
        "specification": {"path": str(SPEC.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(SPEC), "created": "2026-11-17",
                          "committed_before_run": False},
        "code": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256_file(p) for p in sorted(HERE.glob("*.py"))},
        "authorities": [{"role": a.role, "manifest_id": a.manifest_id, "path": a.path, "sha256": a.observed_sha256} for a in authorities],
        "gpt55": {"manifest_id": "EVD-005", "path": gpt_row["current_path"], "sha256": digest,
                  "run_metadata_manifest_id": "EVD-027", "model_reported": {k: gpt_meta.get(k) for k in ("model", "model_id", "prompt_version", "taxonomy_version") if k in gpt_meta}},
        "production_model": {"manifest_id": "MOD-006", "release_manifest": "MOD-011", "model_identifier": "claude-fable-5"},
        "bootstrap": {"draws": BOOTSTRAP_REPLICATES, "seed": SEED_BOOTSTRAP, "minimum_valid": MINIMUM_VALID_REPLICATES,
                      "percentiles": [2.5, 97.5], "interpolation": "Hyndman-Fan Type 7 (numpy linear)",
                      "baseline": "Python Random(seed).randrange over complete records in Record-ID order (Stage A stream)",
                      "hard_case": "one Random(seed) stream; within-stratum draws of 25 in the order domain_only, purpose_only, both"},
        "populations": {f"{p} {d}": n for (p, d), n in populations_used.items()},
        "outputs": {name: sha256_file(out_dir / name) for name in (*tables, report_path.name, *figure_files)},
        "restricted_outputs": {str((restricted_dir / "GHA1_record_level_diagnostics.csv").relative_to(ROOT)).replace("\\", "/"):
                               sha256_file(restricted_dir / "GHA1_record_level_diagnostics.csv")},
        "not_accessed": ["reserve samples", "records outside the active samples beyond the one-to-one join", "adjudication material",
                         "project-owner responses", "any model API"],
        "software": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__},
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"GHA1 written to {out_dir.relative_to(ROOT)}; record-level diagnostics to {restricted_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
