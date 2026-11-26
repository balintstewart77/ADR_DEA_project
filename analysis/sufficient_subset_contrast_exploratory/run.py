"""Post hoc exploratory run: strict register-sufficient subset against the full random baseline.

Specification: SPEC_sufficient_subset_contrast_2026-11-13.md (written after the initial,
since-deleted results were seen, and before this code). Not preregistered. Random baseline
only; aggregate outputs only; 95% percentile bootstrap intervals; no tests or p-values.

Run from the repository root (Windows: set PYTHONUTF8=1):
    venv/Scripts/python.exe analysis/sufficient_subset_contrast_exploratory/run.py
"""

from __future__ import annotations

import csv
import datetime
import functools
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.agreement import encode_panels, encoded_replacement_statistics  # noqa: E402
from analysis.scratch_coder_stage_a.config import CODERS  # noqa: E402
from analysis.scratch_coder_stage_a.load import sha256_file, verify_authorities  # noqa: E402
from analysis.scratch_coder_stage_a.panels import _taxonomy_labels, build_stage_a_data, dimension_panels  # noqa: E402
from analysis.scratch_coder_stage_a.sufficiency import SUFFICIENCY_LABELS, SPLIT, _record_codes, derive_sufficiency_subsets, majority_category  # noqa: E402
from analysis.validation.metrics import jaccard_similarity, masi_distance  # noqa: E402
from analysis.validation.replacement import REPLACEMENT_STATISTIC_NAMES, DimensionPanel, replacement_panel_analysis  # noqa: E402

HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_sufficient_subset_contrast_2026-11-13.md"
# Hash of the specification as written before the code, recorded by the first run (before the post-run addendum).
SPEC_SHA256_BEFORE_ADDENDUM = "b40b5c35a581670dd21150a9a62bf5cccc0bc7ace843b62f019a25b0e6befa50"
RESULTS_MD = ROOT / "analysis/scratch_coder_results/results.md"
LAC1T001 = ROOT / "analysis/label_application_cardinality_exploratory/LAC1T001.csv"
REUSED_MODULES = (
    "analysis/scratch_coder_stage_a/load.py", "analysis/scratch_coder_stage_a/panels.py",
    "analysis/scratch_coder_stage_a/sufficiency.py", "analysis/scratch_coder_stage_a/agreement.py",
    "analysis/validation/metrics.py", "analysis/validation/replacement.py", "analysis/validation/alpha.py",
)
PREFIX = "SSC1T"
STATUS = "post hoc exploratory, not preregistered; initial results seen before the specification"

SEED = 20261113
DRAWS = 10_000
N_BASELINE = 150
MIN_VALID_SHARE = 0.90
QUANTILES = (0.025, 0.975)
EXPLICIT_SEQUENCE_CHECK_DRAWS = 5

UNCLEAR = "Unclear from Register Entry"
UNCLEAR_ONLY = frozenset({UNCLEAR})
FABLE = "Fable 5"
RATERS = (*CODERS, FABLE)  # indices 0..3: A = C01, B = C02, C = C03, L = Fable 5
DIMENSIONS = ("Research Domains", "Analytical Purposes")
TAXONOMY_KEY = {"Research Domains": "domains", "Analytical Purposes": "purposes"}
POPULATIONS = ("full", "sufficient", "complement")
POPULATION_LABEL = {
    "full": "Full baseline (n = 150)",
    "sufficient": "Strict register-sufficient subset (n = 92)",
    "complement": "Complement of the sufficient subset (n = 58)",
}
CANONICAL_TABLES = {
    ("full", "Research Domains"): "S3T001", ("full", "Analytical Purposes"): "S3T002",
    ("sufficient", "Research Domains"): "S3T011", ("sufficient", "Analytical Purposes"): "S3T012",
}
PANELS = {"ABC": (0, 1, 2), "LBC": (3, 1, 2), "ALC": (0, 3, 2), "ABL": (0, 1, 3)}
ALPHA_OF = {"ABC": "alpha_ABC", "LBC": "alpha_LBC", "ALC": "alpha_ALC", "ABL": "alpha_ABL"}
DELTA_PANEL = {"delta_A": "LBC", "delta_B": "ALC", "delta_C": "ABL"}
HUMAN_PAIRS = ((0, 1), (0, 2), (1, 2))
MODEL_PAIRS = ((3, 0), (3, 1), (3, 2))
FAMILIES = {"human-human": HUMAN_PAIRS, "model-human": MODEL_PAIRS}
CATEGORIES = ("both_unclear_only", "first_unclear_only", "second_unclear_only", "identical_substantive", "different_substantive")

# Reconciliation targets from the deleted 13 November 2026 run: compared and reported, never enforced.
TARGET_BOOTSTRAP = {
    "Research Domains": {
        "alpha_ABC": (0.0400, -0.0093, 0.0871), "alpha_LBC": (0.0713, 0.0194, 0.1260),
        "alpha_ALC": (0.0801, 0.0321, 0.1288), "alpha_ABL": (0.0661, 0.0178, 0.1133),
        "delta_A": (0.0313, -0.0054, 0.0704), "delta_B": (0.0401, 0.0087, 0.0735),
        "delta_C": (0.0261, -0.0125, 0.0652), "delta_min": (0.0401, 0.0067, 0.0701),
    },
    "Analytical Purposes": {
        "alpha_ABC": (-0.0036, -0.0553, 0.0467), "alpha_LBC": (0.0543, 0.0047, 0.1036),
        "alpha_ALC": (0.0527, 0.0057, 0.1005), "alpha_ABL": (0.0389, -0.0163, 0.0935),
        "delta_A": (0.0579, 0.0177, 0.1023), "delta_B": (0.0563, 0.0173, 0.0980),
        "delta_C": (0.0425, -0.0093, 0.0945), "delta_min": (0.0563, 0.0159, 0.0950),
    },
}
TARGET_HUMAN_ALPHA = {"Research Domains": (0.526337, 0.566337), "Analytical Purposes": (0.292110, 0.288509)}
# (exactly one Unclear: sufficient, complement), (different substantive among both-substantive: sufficient, complement)
TARGET_DIAGNOSTIC = {
    ("Research Domains", "human-human"): ((30, 276), (52, 174), (96, 245), (42, 104)),
    ("Research Domains", "model-human"): ((16, 276), (41, 174), (83, 260), (59, 130)),
    ("Analytical Purposes", "human-human"): ((44, 276), (80, 174), (124, 232), (24, 50)),
    ("Analytical Purposes", "model-human"): ((22, 276), (81, 174), (125, 254), (42, 90)),
}
TARGET_BOTH_UNCLEAR_PURPOSES_HH = {"sufficient": (0, 276), "complement": (44, 174)}
TARGET_LABELS = (
    ("Analytical Purposes", FABLE, "Descriptive Monitoring", (25, 92), (27, 58)),
    ("Analytical Purposes", "C03", "Policy Evaluation / Impact Analysis", (32, 92), (5, 58)),
)
TARGET_ALL_FOUR_SUBSTANTIVE = {"Research Domains": (77, 29), "Analytical Purposes": (70, 9)}
TARGET_AUDIT_DELTA_MIN = {"Research Domains": (0.0031, 0.0355, 0.0014, 0.0401), "Analytical Purposes": (0.0430, 0.0161, -0.0029, 0.0563)}


# --------------------------------------------------------------------------- pure helpers


@functools.lru_cache(maxsize=None)
def masi(left: frozenset, right: frozenset) -> Fraction:
    """Memoised wrapper around the canonical MASI distance (same Fraction values)."""
    return masi_distance(left, right)


def is_unclear_only(labels: frozenset) -> bool:
    return labels == UNCLEAR_ONLY


def pair_category(first: frozenset, second: frozenset) -> str:
    u1, u2 = is_unclear_only(first), is_unclear_only(second)
    if u1 and u2:
        return "both_unclear_only"
    if u1:
        return "first_unclear_only"
    if u2:
        return "second_unclear_only"
    return "identical_substantive" if first == second else "different_substantive"


def pair_summary(records: list[tuple], pairs: tuple[tuple[int, int], ...]) -> dict:
    """Pooled pair comparison counts and exact sums over the given rater pairs."""
    counts = Counter({c: 0 for c in CATEGORIES})
    jac_all = masi_all = jac_sub = masi_sub = Fraction(0)
    for sets in records:
        for i, j in pairs:
            a, b = sets[i], sets[j]
            category = pair_category(a, b)
            counts[category] += 1
            jac, dist = jaccard_similarity(a, b), masi(a, b)
            jac_all += jac
            masi_all += dist
            if category in ("identical_substantive", "different_substantive"):
                jac_sub += jac
                masi_sub += dist
    n = len(records) * len(pairs)
    n_sub = counts["identical_substantive"] + counts["different_substantive"]
    return {
        "comparisons": n, **{c: counts[c] for c in CATEGORIES},
        "exactly_one_unclear_only": counts["first_unclear_only"] + counts["second_unclear_only"],
        "exact_matches": counts["both_unclear_only"] + counts["identical_substantive"],
        "jaccard_sum": jac_all, "masi_sum": masi_all,
        "both_substantive": n_sub, "jaccard_sum_substantive": jac_sub, "masi_sum_substantive": masi_sub,
    }


def panel_disagreement(records: list[tuple], panel: tuple[int, int, int]) -> dict[str, Fraction]:
    """Do = mean over records of mean MASI over the three within-record pairs, split into U and S parts."""
    a, b, c = panel
    pairs = ((a, b), (a, c), (b, c))
    do_u = do_s = Fraction(0)
    for sets in records:
        for i, j in pairs:
            category = pair_category(sets[i], sets[j])
            if category in ("first_unclear_only", "second_unclear_only"):
                assert masi(sets[i], sets[j]) == 1
                do_u += 1
            elif category == "different_substantive":
                do_s += masi(sets[i], sets[j])
    denominator = 3 * len(records)
    return {"Do": (do_u + do_s) / denominator, "DoU": do_u / denominator, "DoS": do_s / denominator,
            "DoU_sum": do_u, "DoS_sum": do_s}


def decompose(full: dict, strict: dict) -> dict[str, float]:
    """Order-dependent identity: alpha_strict - alpha_full = U term + S term + De term."""
    u_term = (full["DoU"] - strict["DoU"]) / full["De"]
    s_term = (full["DoS"] - strict["DoS"]) / full["De"]
    de_term = strict["Do"] * (1 / full["De"] - 1 / strict["De"])
    return {"U_term": u_term, "S_term": s_term, "De_term": de_term, "total": u_term + s_term + de_term}


def percentile_interval(values: np.ndarray, attempted: int) -> dict:
    valid = values[np.isfinite(values)]
    reported = len(valid) >= MIN_VALID_SHARE * attempted
    lower, upper = (np.quantile(valid, QUANTILES, method="linear") if reported else (None, None))
    return {"attempted": attempted, "valid": int(len(valid)), "undefined": int(attempted - len(valid)),
            "interval_reported": bool(reported),
            "lower": None if lower is None else float(lower), "upper": None if upper is None else float(upper)}


def stats_vector(encoded, indices: np.ndarray) -> np.ndarray:
    values = encoded_replacement_statistics(encoded, indices)
    return np.array([np.nan if values[name] is None else values[name] for name in REPLACEMENT_STATISTIC_NAMES], dtype=float)


def paired_bootstrap(encoded, strict_mask: np.ndarray, draws: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For each draw: statistics on all drawn rows and on the drawn rows that are in the strict subset."""
    full = np.empty((len(draws), len(REPLACEMENT_STATISTIC_NAMES)))
    strict = np.empty_like(full)
    sizes = np.empty(len(draws), dtype=int)
    for k, indices in enumerate(draws):
        strict_indices = indices[strict_mask[indices]]  # keeps duplicates; size varies
        sizes[k] = len(strict_indices)
        full[k] = stats_vector(encoded, indices)
        strict[k] = stats_vector(encoded, strict_indices)
    return full, strict, sizes


def results_md_point(table_id: str, statistic: str) -> float:
    lines = RESULTS_MD.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"### {table_id} "))
    row_key = statistic.replace("alpha_", "alpha ") if statistic.startswith("alpha_") else statistic
    for line in lines[start + 1:]:
        if line.startswith("### ") or line.startswith("## "):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == row_key and cells[1] == "`point_estimate`":
            return float(cells[2])
    raise KeyError(f"{table_id}: {statistic}")


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def signed(value: float | None, places: int = 4) -> str:
    return "" if value is None else f"{value:+.{places}f}".replace("-", "−")


def pct(k: int, n: int) -> str:
    return f"{k}/{n} ({share(k, n)})" if n else f"{k}/0"


def share(k: int, n: int) -> str:
    """Whole-number percentage, half up; a non-zero share below 0.5% is shown as <1%."""
    value = int(100 * k / n + 0.5)
    return "<1%" if value == 0 and k else f"{value}%"


def as_float(value) -> float:
    return float(value) if isinstance(value, Fraction) else value


# --------------------------------------------------------------------------- run


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    checks: list[dict] = []
    targets: list[dict] = []

    def check(name: str, passed: bool, observed=None, expected=None) -> None:
        checks.append({"check": name, "status": "passed" if passed else "FAILED", "observed": observed, "expected": expected})
        if not passed:
            raise SystemExit(f"Check failed: {name}: observed {observed!r}, expected {expected!r}")

    def target(item: str, observed: str, expected: str) -> None:
        targets.append({"table_id": f"{PREFIX}011", "item": item, "observed": observed, "target": expected,
                        "match": observed == expected})

    # ---- data
    authorities = verify_authorities()
    for authority in authorities:
        check(f"authority hash {authority.manifest_id}", authority.matched, authority.observed_sha256, authority.expected_sha256)
    data = build_stage_a_data()
    baseline = sorted(data.baseline_ids)
    check("150 baseline records", len(baseline) == N_BASELINE, len(baseline), N_BASELINE)
    base_responses = data.responses[data.responses["population"] == "baseline"]
    check("450 baseline coder responses, all complete and structurally valid",
          len(base_responses) == 450 and bool(base_responses["complete"].all()) and bool(base_responses["structural_valid"].all()),
          [len(base_responses), int(base_responses["complete"].sum()), int(base_responses["structural_valid"].sum())], [450, 450, 450])

    strict_ids = derive_sufficiency_subsets(data)["strict"]
    complement_ids = data.baseline_ids - strict_ids
    check("strict subset 92 records within baseline", len(strict_ids) == 92 and strict_ids <= data.baseline_ids, len(strict_ids), 92)
    check("complement 58 records", len(complement_ids) == 58, len(complement_ids), 58)
    codes = _record_codes(data, "baseline")
    complement_majority = Counter(majority_category(codes[r], SUFFICIENCY_LABELS) for r in complement_ids)
    check("complement majorities 55 Partially sufficient / 2 Insufficient / 1 no majority (S8T003)",
          complement_majority == Counter({"Partially sufficient": 55, "Insufficient": 2, SPLIT: 1}), dict(complement_majority))
    check("strict subset equals coder majority Sufficient",
          strict_ids == frozenset(r for r in baseline if majority_category(codes[r], SUFFICIENCY_LABELS) == "Sufficient"))
    exposure = data.exposure_ids & data.baseline_ids
    check("one exposure-flagged baseline record, kept", len(exposure) == 1, len(exposure), 1)
    exposure_population = "sufficient" if exposure <= strict_ids else "complement"

    membership = {"full": data.baseline_ids, "sufficient": strict_ids, "complement": complement_ids}
    taxonomy = _taxonomy_labels()
    panels_by_dim: dict[str, tuple[DimensionPanel, ...]] = {}
    records: dict[str, dict[str, list[tuple]]] = {}
    for dimension in DIMENSIONS:
        panels = dimension_panels(data, data.baseline_ids, dimension)
        ids = [p.record_id for p in panels]
        check(f"{dimension}: panels sorted by Record ID, one per baseline record", ids == baseline, len(ids), N_BASELINE)
        for p in panels:
            sets = (p.coder_a, p.coder_b, p.coder_c, p.model)
            if any(s is None or not s for s in sets):
                check(f"{dimension}: complete non-empty sets for all four raters", False, p.record_id)
            if any(UNCLEAR in s and len(s) > 1 for s in sets):
                check(f"{dimension}: Unclear exclusive within every set", False)
            if any(s - taxonomy[TAXONOMY_KEY[dimension]] for s in sets):
                check(f"{dimension}: labels within frozen taxonomy", False)
        check(f"{dimension}: complete, non-empty, exclusive-Unclear sets for all four raters", True)
        panels_by_dim[dimension] = panels
        records[dimension] = {pop: [(p.coder_a, p.coder_b, p.coder_c, p.model) for p in panels if p.record_id in membership[pop]]
                              for pop in POPULATIONS}
        check(f"{dimension}: population sizes 150/92/58", [len(records[dimension][p]) for p in POPULATIONS] == [150, 92, 58])

    # ---- 1. point estimates (canonical estimator) and reconciliation
    point: dict[tuple[str, str], dict] = {}
    alpha_results: dict[tuple[str, str], object] = {}
    t1: list[dict] = []
    reconciled = 0
    for dimension in DIMENSIONS:
        for pop in POPULATIONS:
            pop_panels = [p for p in panels_by_dim[dimension] if p.record_id in membership[pop]]
            result = replacement_panel_analysis(pop_panels, masi)
            check(f"{dimension}/{pop}: all panels defined", result.valid and len(result.common_record_ids) == len(pop_panels))
            values = {"alpha_ABC": result.alpha_abc.alpha, "alpha_LBC": result.alpha_lbc.alpha, "alpha_ALC": result.alpha_alc.alpha,
                      "alpha_ABL": result.alpha_abl.alpha, "delta_A": result.delta_a, "delta_B": result.delta_b,
                      "delta_C": result.delta_c, "delta_min": result.delta_min}
            point[(pop, dimension)] = values
            alpha_results[(pop, dimension)] = {"ABC": result.alpha_abc, "LBC": result.alpha_lbc, "ALC": result.alpha_alc, "ABL": result.alpha_abl}
            for statistic in REPLACEMENT_STATISTIC_NAMES:
                row = {"table_id": f"{PREFIX}001", "dimension": dimension, "population": pop, "records": len(pop_panels),
                       "statistic": statistic, "point_estimate": repr(values[statistic])}
                table_id = CANONICAL_TABLES.get((pop, dimension))
                if table_id:
                    canonical = results_md_point(table_id, statistic)
                    diff = abs(values[statistic] - canonical)
                    check(f"{dimension}/{pop}/{statistic} equals {table_id} within 1e-12", diff <= 1e-12, values[statistic], canonical)
                    reconciled += 1
                    row.update({"canonical_table": table_id, "canonical_value": repr(canonical), "absolute_difference": repr(diff)})
                else:
                    row.update({"canonical_table": "", "canonical_value": "", "absolute_difference": ""})
                row["status"] = STATUS if pop != "complement" else STATUS + "; complement estimate descriptive only"
                t1.append(row)
    check("32 point estimates reconciled with S3T001/S3T002/S3T011/S3T012", reconciled == 32, reconciled, 32)
    for dimension in DIMENSIONS:
        full_h, strict_h = TARGET_HUMAN_ALPHA[dimension]
        target(f"{dimension}: human-only alpha full", f"{point[('full', dimension)]['alpha_ABC']:.6f}", f"{full_h:.6f}")
        target(f"{dimension}: human-only alpha strict", f"{point[('sufficient', dimension)]['alpha_ABC']:.6f}", f"{strict_h:.6f}")

    # LAC1T001 reconciliation (full-baseline label counts).
    lac = pd.read_csv(LAC1T001, dtype=str, keep_default_na=False)
    lac_checked = 0
    for row in lac.to_dict("records"):
        sets = records[row["dimension"]]["full"]
        for idx, column in enumerate(("C01_count", "C02_count", "C03_count", "fable5_count")):
            observed = sum(row["label"] in s[idx] for s in sets)
            check(f"LAC1T001 {row['dimension']}/{row['label']}/{column}", observed == int(row[column]), observed, int(row[column]))
            lac_checked += 1
    check("LAC1T001 rows covered (20 labels x 4 raters)", lac_checked == 80, lac_checked, 80)

    # ---- 2. paired bootstrap
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, N_BASELINE, size=(DRAWS, N_BASELINE), dtype=np.int32)
    draws_sha256 = hashlib.sha256(np.ascontiguousarray(draws).tobytes()).hexdigest()
    strict_mask = np.array([rid in strict_ids for rid in baseline], dtype=bool)
    check("strict mask has 92 true positions", int(strict_mask.sum()) == 92)
    t2: list[dict] = []
    t3: list[dict] = []
    boot_summary: dict = {}
    for dimension in DIMENSIONS:
        panels = panels_by_dim[dimension]
        encoded = encode_panels(panels, masi_distance)
        check(f"{dimension}: encoded rows equal 150 sorted records", len(encoded.ratings) == N_BASELINE)
        for pop, indices in (("full", np.arange(N_BASELINE)), ("sufficient", np.flatnonzero(strict_mask))):
            vector = stats_vector(encoded, indices)
            canonical = np.array([point[(pop, dimension)][s] for s in REPLACEMENT_STATISTIC_NAMES])
            check(f"{dimension}/{pop}: encoded alpha equals canonical within 1e-12",
                  bool(np.all(np.abs(vector - canonical) <= 1e-12)), float(np.max(np.abs(vector - canonical))))
        full_values, strict_values, sizes = paired_bootstrap(encoded, strict_mask, draws)
        # Explicit duplicated-sequence check with the canonical estimator on the first draws.
        for k in range(EXPLICIT_SEQUENCE_CHECK_DRAWS):
            full_seq = [panels[i] for i in draws[k]]
            strict_seq = [panels[i] for i in draws[k] if strict_mask[i]]
            check(f"{dimension}: draw {k + 1} strict sequence keeps duplicates",
                  len(strict_seq) == int(strict_mask[draws[k]].sum()) and len(strict_seq) >= len({p.record_id for p in strict_seq}))
            for label, sequence, values in (("full", full_seq, full_values[k]), ("sufficient", strict_seq, strict_values[k])):
                result = replacement_panel_analysis(sequence, masi)
                direct = np.array([result.alpha_abc.alpha, result.alpha_lbc.alpha, result.alpha_alc.alpha, result.alpha_abl.alpha,
                                   result.delta_a, result.delta_b, result.delta_c, result.delta_min], dtype=float)
                check(f"{dimension}: draw {k + 1} {label} encoded equals canonical on explicit duplicated sequence",
                      bool(np.all(np.abs(direct - values) <= 1e-12)), float(np.max(np.abs(direct - values))))
        check(f"{dimension}: draws contain duplicate records", bool(all(len(set(d.tolist())) < N_BASELINE for d in draws[:100])))
        # delta_min recomputed within each resample
        for values in (full_values, strict_values):
            finite = np.all(np.isfinite(values[:, 4:7]), axis=1)
            check(f"{dimension}: delta_min is the per-draw minimum of the three deltas",
                  bool(np.array_equal(values[finite, 7], np.min(values[finite, 4:7], axis=1))))
        contrasts = strict_values - full_values
        boot_summary[dimension] = {}
        for s_idx, statistic in enumerate(REPLACEMENT_STATISTIC_NAMES):
            interval = percentile_interval(contrasts[:, s_idx], DRAWS)
            observed = point[("sufficient", dimension)][statistic] - point[("full", dimension)][statistic]
            excludes = None if not interval["interval_reported"] else (interval["lower"] > 0 or interval["upper"] < 0)
            role = "primary" if statistic == "alpha_ABC" else "secondary"
            t2.append({"table_id": f"{PREFIX}002", "dimension": dimension, "contrast": f"{statistic}: strict minus full", "role": role,
                       "full_point": repr(point[("full", dimension)][statistic]), "strict_point": repr(point[("sufficient", dimension)][statistic]),
                       "contrast_point": repr(observed), "interval_lower_95": repr(interval["lower"]), "interval_upper_95": repr(interval["upper"]),
                       "interval_method": "95% percentile, numpy linear (Type 7) quantiles", "draws_attempted": interval["attempted"],
                       "draws_valid": interval["valid"], "draws_undefined": interval["undefined"],
                       "interval_reported": interval["interval_reported"], "interval_excludes_zero": excludes,
                       "full_draws_valid": int(np.isfinite(full_values[:, s_idx]).sum()),
                       "strict_draws_valid": int(np.isfinite(strict_values[:, s_idx]).sum()),
                       "seed": SEED, "status": STATUS})
            boot_summary[dimension][statistic] = {"point": observed, **interval, "excludes_zero": excludes}
            expected = TARGET_BOOTSTRAP[dimension][statistic]
            target(f"{dimension}: {statistic} contrast [95% interval]",
                   f"{observed:+.4f} [{interval['lower']:+.4f}, {interval['upper']:+.4f}]" if interval["interval_reported"] else f"{observed:+.4f} [not reported]",
                   f"{expected[0]:+.4f} [{expected[1]:+.4f}, {expected[2]:+.4f}]")
        all_valid = int(np.all(np.isfinite(contrasts), axis=1).sum())
        target(f"{dimension}: draws valid for every contrast", f"{all_valid}/{DRAWS}", f"{DRAWS}/{DRAWS}")
        boot_summary[dimension]["_draws_valid_for_all_contrasts"] = all_valid
        q = np.quantile(sizes, (0.025, 0.5, 0.975), method="linear")
        t3.append({"table_id": f"{PREFIX}003", "dimension": dimension, "draws": DRAWS, "observed_strict_records": 92,
                   "resample_strict_size_min": int(sizes.min()), "resample_strict_size_q025": float(q[0]),
                   "resample_strict_size_median": float(q[1]), "resample_strict_size_q975": float(q[2]),
                   "resample_strict_size_max": int(sizes.max()), "resample_strict_size_mean": float(sizes.mean()),
                   "draws_with_empty_strict_subset": int((sizes == 0).sum()),
                   "draws_with_duplicate_records": int(sum(len(set(d.tolist())) < N_BASELINE for d in draws)),
                   "note": "same index matrix for both dimensions; strict size is identical across dimensions"})
    check("strict resample sizes identical across dimensions",
          all(t3[0][k] == t3[1][k] for k in t3[0] if k.startswith("resample_")))

    # ---- 3. disagreement diagnostic
    t4: list[dict] = []
    t5: list[dict] = []
    family_summary: dict = {}
    for dimension in DIMENSIONS:
        for pop in POPULATIONS:
            recs = records[dimension][pop]
            for family, pairs in FAMILIES.items():
                for pair in pairs:
                    s = pair_summary(recs, (pair,))
                    t4.append(diagnostic_row(f"{PREFIX}004", dimension, pop, family, f"{RATERS[pair[0]]}–{RATERS[pair[1]]}", s, family == "model-human"))
                s = pair_summary(recs, pairs)
                family_summary[(dimension, pop, family)] = s
                t5.append(diagnostic_row(f"{PREFIX}005", dimension, pop, family, "pooled (3N comparisons; not independent)", s, family == "model-human"))
        for family in FAMILIES:
            full, suff, comp = (family_summary[(dimension, p, family)] for p in POPULATIONS)
            for key in ("comparisons", *CATEGORIES, "jaccard_sum", "masi_sum", "masi_sum_substantive"):
                check(f"{dimension}/{family}: {key} adds across sufficient and complement", full[key] == suff[key] + comp[key], str(full[key]), str(suff[key] + comp[key]))
            e1, e2, d1, d2 = TARGET_DIAGNOSTIC[(dimension, family)]
            target(f"{dimension}, {family}: exactly one Unclear-only, sufficient", f"{suff['exactly_one_unclear_only']}/{suff['comparisons']}", f"{e1[0]}/{e1[1]}")
            target(f"{dimension}, {family}: exactly one Unclear-only, complement", f"{comp['exactly_one_unclear_only']}/{comp['comparisons']}", f"{e2[0]}/{e2[1]}")
            target(f"{dimension}, {family}: different substantive among both-substantive, sufficient", f"{suff['different_substantive']}/{suff['both_substantive']}", f"{d1[0]}/{d1[1]}")
            target(f"{dimension}, {family}: different substantive among both-substantive, complement", f"{comp['different_substantive']}/{comp['both_substantive']}", f"{d2[0]}/{d2[1]}")
    for pop, (k, n) in TARGET_BOTH_UNCLEAR_PURPOSES_HH.items():
        s = family_summary[("Analytical Purposes", pop, "human-human")]
        target(f"Analytical Purposes, human-human: both Unclear-only, {pop}", f"{s['both_unclear_only']}/{s['comparisons']}", f"{k}/{n}")

    # Per-rater Unclear frequency, cardinality and label counts.
    t6: list[dict] = []
    t7: list[dict] = []
    for dimension in DIMENSIONS:
        labels = sorted(taxonomy[TAXONOMY_KEY[dimension]])
        for pop in POPULATIONS:
            recs = records[dimension][pop]
            n = len(recs)
            for idx, rater in enumerate(RATERS):
                unclear = sum(is_unclear_only(s[idx]) for s in recs)
                sizes = [len(s[idx] - UNCLEAR_ONLY) for s in recs]
                classified = sum(size >= 1 for size in sizes)
                check(f"{dimension}/{pop}/{rater}: Unclear-only plus classified equals N", unclear + classified == n)
                t6.append({"table_id": f"{PREFIX}006", "dimension": dimension, "population": pop, "rater": rater, "records": n,
                           "unclear_only_records": unclear, "unclear_only_proportion": repr(unclear / n),
                           "substantively_classified_records": classified, "substantive_label_applications": sum(sizes),
                           "mean_substantive_labels_per_record": repr(sum(sizes) / n),
                           "mean_substantive_labels_among_classified": repr(sum(sizes) / classified) if classified else "",
                           "status": STATUS})
                for label in labels:
                    count = sum(label in s[idx] for s in recs)
                    t7.append({"table_id": f"{PREFIX}007", "dimension": dimension, "population": pop, "rater": rater, "label": label,
                               "label_type": "unclear" if label == UNCLEAR else "substantive", "count": count, "records": n,
                               "proportion": repr(count / n)})
    for dimension in DIMENSIONS:
        for idx, rater in enumerate(RATERS):
            for label in sorted(taxonomy[TAXONOMY_KEY[dimension]]):
                c = {p: next(r["count"] for r in t7 if r["dimension"] == dimension and r["population"] == p and r["rater"] == rater and r["label"] == label) for p in POPULATIONS}
                if c["full"] != c["sufficient"] + c["complement"]:
                    check(f"{dimension}/{rater}/{label}: label counts add", False, c)
    check("per-label counts add across sufficient and complement", True)
    for dimension, rater, label, (k1, n1), (k2, n2) in TARGET_LABELS:
        got = {p: next(r for r in t7 if r["dimension"] == dimension and r["population"] == p and r["rater"] == rater and r["label"] == label) for p in ("sufficient", "complement")}
        target(f"{dimension}: {rater} {label}, sufficient", f"{got['sufficient']['count']}/{got['sufficient']['records']}", f"{k1}/{n1}")
        target(f"{dimension}: {rater} {label}, complement", f"{got['complement']['count']}/{got['complement']['records']}", f"{k2}/{n2}")

    # Secondary: records on which all four raters classify substantively.
    t8: list[dict] = []
    for dimension in DIMENSIONS:
        counts = {}
        for pop in POPULATIONS:
            recs = [s for s in records[dimension][pop] if not any(is_unclear_only(x) for x in s)]
            counts[pop] = len(recs)
            for family, pairs in FAMILIES.items():
                s = pair_summary(recs, pairs)
                row = diagnostic_row(f"{PREFIX}008", dimension, pop, family, "pooled (3N comparisons; not independent)", s, False)
                row["records_all_four_substantive"] = len(recs)
                row["records_in_population"] = len(records[dimension][pop])
                row["note"] = "record composition differs between populations; not a controlled comparison"
                t8.append(row)
        check(f"{dimension}: all-four-substantive counts add", counts["full"] == counts["sufficient"] + counts["complement"])
        exp = TARGET_ALL_FOUR_SUBSTANTIVE[dimension]
        target(f"{dimension}: records with all four substantive (sufficient, complement)", f"{counts['sufficient']}, {counts['complement']}", f"{exp[0]}, {exp[1]}")

    # Post-run caveat table: each coder's Unclear-only use by that coder's own sufficiency rating (aggregate counts).
    t12: list[dict] = []
    for dimension in DIMENSIONS:
        field = TAXONOMY_KEY[dimension]
        for coder in CODERS:
            rows = base_responses[base_responses["coder"] == coder]
            unclear = rows[field].apply(is_unclear_only)
            own_sufficient = rows["sufficiency"] == 1
            check(f"{dimension}/{coder}: 150 sufficiency ratings, all valid", len(rows) == 150 and bool(rows["sufficiency"].isin(SUFFICIENCY_LABELS).all()))
            expected_unclear = next(r["unclear_only_records"] for r in t6 if r["dimension"] == dimension and r["population"] == "full" and r["rater"] == coder)
            check(f"{dimension}/{coder}: own-rating Unclear-only counts add to SSC1T006", int(unclear.sum()) == expected_unclear, int(unclear.sum()), expected_unclear)
            t12.append({"table_id": f"{PREFIX}012", "dimension": dimension, "coder": coder,
                        "own_sufficient_records": int(own_sufficient.sum()), "unclear_only_when_own_sufficient": int(unclear[own_sufficient].sum()),
                        "own_not_sufficient_records": int((~own_sufficient).sum()), "unclear_only_when_own_not_sufficient": int(unclear[~own_sufficient].sum()),
                        "note": "post-run caveat table: the subset is defined by the same coders' ratings, so it is not independent of their abstention",
                        "status": STATUS})

    # ---- 4. Do / De audit and identity
    t9: list[dict] = []
    audit: dict[tuple[str, str, str], dict] = {}
    for dimension in DIMENSIONS:
        for pop in POPULATIONS:
            recs = records[dimension][pop]
            for name, panel in PANELS.items():
                split = panel_disagreement(recs, panel)
                result = alpha_results[(pop, dimension)][name]
                check(f"{dimension}/{pop}/{name}: Do equals estimator observed disagreement", abs(float(split["Do"]) - result.observed_disagreement) <= 1e-12,
                      float(split["Do"]), result.observed_disagreement)
                check(f"{dimension}/{pop}/{name}: Do = DoU + DoS", split["Do"] == split["DoU"] + split["DoS"])
                pair_means = []
                for i, j in ((panel[0], panel[1]), (panel[0], panel[2]), (panel[1], panel[2])):
                    pair_means.append(pair_summary(recs, ((i, j),))["masi_sum"] / len(recs))
                check(f"{dimension}/{pop}/{name}: Do equals mean of the three pair mean MASI distances", split["Do"] == sum(pair_means) / 3)
                if name == "ABC":
                    fam = family_summary[(dimension, pop, "human-human")]
                    check(f"{dimension}/{pop}: pooled human-human mean MASI equals Do_ABC", fam["masi_sum"] / fam["comparisons"] == split["Do"])
                entry = {"Do": float(split["Do"]), "DoU": float(split["DoU"]), "DoS": float(split["DoS"]), "De": result.expected_disagreement,
                         "DoU_sum": split["DoU_sum"], "DoS_sum": split["DoS_sum"], "alpha": result.alpha}
                audit[(dimension, pop, name)] = entry
                t9.append({"table_id": f"{PREFIX}009", "dimension": dimension, "population": pop, "panel": name, "records": len(recs),
                           "Do": repr(entry["Do"]), "DoU_unclear_vs_substantive": repr(entry["DoU"]), "DoS_different_substantive": repr(entry["DoS"]),
                           "De": repr(entry["De"]), "alpha": repr(entry["alpha"]), "alpha_check_1_minus_Do_over_De": repr(1 - entry["Do"] / entry["De"]),
                           "DoU_pair_sum": int(entry["DoU_sum"]), "DoS_pair_sum": str(entry["DoS_sum"]), "pair_comparisons": 3 * len(recs)})
            if pop == "complement":
                for name in PANELS:
                    f, s, c = (audit[(dimension, p, name)] for p in POPULATIONS)
                    check(f"{dimension}/{name}: record-weighted DoU and DoS sums add", f["DoU_sum"] == s["DoU_sum"] + c["DoU_sum"] and f["DoS_sum"] == s["DoS_sum"] + c["DoS_sum"])
                    check(f"{dimension}/{name}: 150 Do_full = 92 Do_strict + 58 Do_complement",
                          abs(150 * f["Do"] - (92 * s["Do"] + 58 * c["Do"])) <= 1e-10, 150 * f["Do"], 92 * s["Do"] + 58 * c["Do"])
    t10: list[dict] = []
    for dimension in DIMENSIONS:
        terms = {name: decompose(audit[(dimension, "full", name)], audit[(dimension, "sufficient", name)]) for name in PANELS}
        for name in PANELS:
            observed = point[("sufficient", dimension)][ALPHA_OF[name]] - point[("full", dimension)][ALPHA_OF[name]]
            check(f"{dimension}/{ALPHA_OF[name]}: identity sums to the observed contrast", abs(terms[name]["total"] - observed) <= 1e-12, terms[name]["total"], observed)
            t10.append(audit_row(dimension, ALPHA_OF[name], terms[name], observed))
        delta_rows = {}
        for delta, panel in DELTA_PANEL.items():
            d = {k: terms[panel][k] - terms["ABC"][k] for k in terms["ABC"]}
            observed = point[("sufficient", dimension)][delta] - point[("full", dimension)][delta]
            check(f"{dimension}/{delta}: identity sums to the observed contrast", abs(d["total"] - observed) <= 1e-12, d["total"], observed)
            delta_rows[delta] = d
            t10.append(audit_row(dimension, delta, d, observed))
        argmin = {pop: min(DELTA_PANEL, key=lambda k: point[(pop, dimension)][k]) for pop in ("full", "sufficient")}
        observed = point[("sufficient", dimension)]["delta_min"] - point[("full", dimension)]["delta_min"]
        # The identity applies to delta_min only when the same delta is the minimum in both populations.
        check(f"{dimension}: delta_min is the same delta in both populations (identity defined)", argmin["full"] == argmin["sufficient"], argmin)
        dm = delta_rows[argmin["full"]]
        note = f"delta_min = {argmin['full']} in both populations"
        t10.append(audit_row(dimension, "delta_min", dm, observed, note))
        exp = TARGET_AUDIT_DELTA_MIN[dimension]
        target(f"{dimension}: delta_min audit (U, S, De, total)",
               ", ".join(f"{dm[k]:+.4f}" for k in ("U_term", "S_term", "De_term", "total")), ", ".join(f"{v:+.4f}" for v in exp))

    # ---- outputs
    tables = {f"{PREFIX}001.csv": t1, f"{PREFIX}002.csv": t2, f"{PREFIX}003.csv": t3, f"{PREFIX}004.csv": t4, f"{PREFIX}005.csv": t5,
              f"{PREFIX}006.csv": t6, f"{PREFIX}007.csv": t7, f"{PREFIX}008.csv": t8, f"{PREFIX}009.csv": t9, f"{PREFIX}010.csv": t10,
              f"{PREFIX}011.csv": targets, f"{PREFIX}012.csv": t12}
    for name, rows in tables.items():
        write_csv(HERE / name, rows)
    lines = render_results(point, boot_summary, t3, family_summary, t6, t7, t8, audit, t10, targets, exposure_population, t12)
    results_path = HERE / "results_sufficient_subset_contrast.md"
    results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--", str(HERE.relative_to(ROOT))], cwd=ROOT, text=True).strip())
    metadata = {
        "analysis": "strict register-sufficient subset against the full random baseline",
        "status": STATUS,
        "analysis_status": "complete; exploratory, descriptive; not for confirmatory use",
        "specification": {"path": rel(SPEC), "sha256": sha256_file(SPEC), "created": "2026-11-13", "committed_before_run": False,
                          "sha256_before_post_run_addendum": SPEC_SHA256_BEFORE_ADDENDUM,
                          "note": "Investigator instructed no commit; specification hash recorded instead. Written after the initial (deleted) results "
                                  "were seen. A dated post-run addendum (interpretation caveats only; no method change) was appended after the first run; "
                                  "the hash of the specification as it stood before the addendum is kept above."},
        "code": {rel(Path(__file__)): sha256_file(Path(__file__)), **{m: sha256_file(ROOT / m) for m in REUSED_MODULES}},
        "sources": {
            "authorities": [{"manifest_id": a.manifest_id, "role": a.role, "path": a.path, "sha256": a.observed_sha256} for a in authorities],
            "canonical_results_md": {"path": rel(RESULTS_MD), "sha256": sha256_file(RESULTS_MD), "tables": sorted(set(CANONICAL_TABLES.values()))},
            "label_counts": {"path": rel(LAC1T001), "sha256": sha256_file(LAC1T001)},
            "taxonomy": {"path": "taxonomy_data_dictionary.yaml", "sha256": sha256_file(ROOT / "taxonomy_data_dictionary.yaml")},
        },
        "software": {"python": sys.version, "numpy": np.__version__, "pandas": pd.__version__, "platform": platform.platform()},
        "bootstrap": {"seed": SEED, "generator": "numpy.random.default_rng", "call": "rng.integers(0, 150, size=(10000, 150), dtype=np.int32)",
                      "index_matrix_sha256": draws_sha256, "draws_attempted": DRAWS,
                      "draws_valid": {d: {s: boot_summary[d][s]["valid"] for s in REPLACEMENT_STATISTIC_NAMES} for d in DIMENSIONS},
                      "draws_valid_for_all_contrasts": {d: boot_summary[d]["_draws_valid_for_all_contrasts"] for d in DIMENSIONS},
                      "minimum_valid_share_for_interval": MIN_VALID_SHARE, "interval": "95% percentile; numpy quantile method='linear' (Type 7)",
                      "record_order": "sorted by Record ID", "shared_across": "both dimensions and both populations",
                      "explicit_sequence_check_draws": EXPLICIT_SEQUENCE_CHECK_DRAWS},
        "populations": {"full": 150, "sufficient": 92, "complement": 58, "exposure_flagged_record_kept_in": exposure_population},
        "run_started_utc": started.isoformat(), "run_completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository_head": head, "run_directory_uncommitted": dirty,
        "checks_passed": len(checks), "checks": checks,
        "target_comparison": {"items": len(targets), "matched": sum(t["match"] for t in targets),
                              "mismatched": [t["item"] for t in targets if not t["match"]]},
        "outputs": {name: sha256_file(HERE / name) for name in (*tables, results_path.name)},
        "restricted_outputs": [], "not_accessed": ["adjudication findings", "project-owner responses", "DEA_paper manuscript"],
    }
    (HERE / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"{len(checks)} checks passed; targets matched {metadata['target_comparison']['matched']}/{len(targets)}")
    for t in targets:
        if not t["match"]:
            print(f"  TARGET DIFFERS: {t['item']}: observed {t['observed']} vs target {t['target']}")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def diagnostic_row(table_id: str, dimension: str, pop: str, family: str, pair: str, s: dict, directional: bool) -> dict:
    n, n_sub = s["comparisons"], s["both_substantive"]
    return {
        "table_id": table_id, "dimension": dimension, "population": pop, "family": family, "pair": pair, "comparisons": n,
        "both_unclear_only": s["both_unclear_only"], "exactly_one_unclear_only": s["exactly_one_unclear_only"],
        "model_unclear_only_coder_substantive": s["first_unclear_only"] if directional else "",
        "coder_unclear_only_model_substantive": s["second_unclear_only"] if directional else "",
        "identical_substantive": s["identical_substantive"], "different_substantive": s["different_substantive"],
        "exact_match_rate": repr(s["exact_matches"] / n) if n else "", "mean_jaccard": repr(float(s["jaccard_sum"] / n)) if n else "",
        "mean_masi_distance": repr(float(s["masi_sum"] / n)) if n else "",
        "both_substantive_comparisons": n_sub,
        "exact_match_rate_both_substantive": repr(s["identical_substantive"] / n_sub) if n_sub else "",
        "mean_jaccard_both_substantive": repr(float(s["jaccard_sum_substantive"] / n_sub)) if n_sub else "",
        "mean_masi_distance_both_substantive": repr(float(s["masi_sum_substantive"] / n_sub)) if n_sub else "",
    }


def audit_row(dimension: str, quantity: str, terms: dict, observed: float, note: str = "") -> dict:
    return {"table_id": f"{PREFIX}010", "dimension": dimension, "contrast": f"{quantity}: strict minus full",
            "U_term_unclear_vs_substantive": repr(terms["U_term"]), "S_term_different_substantive": repr(terms["S_term"]),
            "De_term_expected_disagreement": repr(terms["De_term"]), "identity_total": repr(terms["total"]),
            "observed_contrast": repr(observed), "note": note or ("replacement panel terms minus ABC terms" if quantity.startswith("delta") else ""),
            "caveat": "order-dependent arithmetic audit; not causal attribution"}


def caveats(point, boot, audit, t10, t12) -> list[str]:
    """Interpretation caveats added after the first run (no method change)."""
    D, P = DIMENSIONS
    term = {(r["dimension"], r["contrast"].split(":")[0]): r for r in t10}
    dm = {d: term[(d, "delta_min")] for d in DIMENSIONS}
    share_u = {d: float(dm[d]["U_term_unclear_vs_substantive"]) / float(dm[d]["identity_total"]) for d in DIMENSIONS}
    share_s = {d: float(dm[d]["S_term_different_substantive"]) / float(dm[d]["identity_total"]) for d in DIMENSIONS}
    own = "; ".join(
        f"{r['dimension']}, {r['coder']}: {r['unclear_only_when_own_sufficient']}/{r['own_sufficient_records']} against "
        f"{r['unclear_only_when_own_not_sufficient']}/{r['own_not_sufficient_records']}" for r in t12)
    same_min = all(point[(p, d)]["delta_min"] == point[(p, d)]["delta_B"] for p in ("full", "sufficient") for d in DIMENSIONS)
    excluding = sum(bool(boot[d][s]["excludes_zero"]) for d in DIMENSIONS for s in REPLACEMENT_STATISTIC_NAMES)
    return [
        "## Caveats for interpretation (added after the first run)", "",
        "These caveats were added after the first run, on review, before any commit. They change no method or number.", "",
        "1. **The subset is not independent of the coders' abstention.** Sufficiency is rated by the same coders whose agreement is measured, "
        "and each coder's Unclear-only sets fall almost entirely on entries that coder did not rate Sufficient (SSC1T012; Unclear-only when "
        f"own rating Sufficient against when not: {own}). Fable 5 almost never abstains, so restricting to coder-rated Sufficient entries removes "
        "coder abstentions largely by construction, and that favours the panels that include Fable 5. "
        f"For Analytical Purposes the abstention (U) term is {share(round(share_u[P] * 1000), 1000)} of the delta_min contrast "
        f"({signed(float(dm[P]['U_term_unclear_vs_substantive']))} of {signed(float(dm[P]['identity_total']))}), so that contrast mostly reflects "
        "this selection, not better substantive classification on clear entries. For Research Domains the substantive (S) term is "
        f"{share(round(share_s[D] * 1000), 1000)} ({signed(float(dm[D]['S_term_different_substantive']))} of {signed(float(dm[D]['identity_total']))}), "
        "so the domains contrast rests mainly on substantive agreement.",
        "2. **The contrast compares a subset with the population that contains it.** The subset is 92 of the 150 records (61%), so strict minus "
        "full is diluted towards zero and is not a comparison of sufficient against not-sufficient entries. The complement estimates show the "
        f"larger gap (human-only alpha: domains {point[('sufficient', D)]['alpha_ABC']:.2f} sufficient, {point[('complement', D)]['alpha_ABC']:.2f} complement; "
        f"purposes {point[('sufficient', P)]['alpha_ABC']:.2f} and {point[('complement', P)]['alpha_ABC']:.2f}).",
        "3. **delta_B and delta_min are not separate findings.** "
        + ("delta_min equals delta_B at the point estimate in both populations and both dimensions, so both intervals excluding zero is one "
           "finding, not two. " if same_min else "")
        + f"Sixteen intervals are reported without adjustment ({excluding} exclude zero); reading only those that exclude zero overstates the evidence.",
        "4. **Delta contrasts are differences of differences.** Each delta contrast is in substance a subset-by-panel interaction. They are "
        "reported as descriptive contrasts; no interaction is claimed, and an interval excluding zero is not evidence of one.",
        "5. **The coders are held fixed.** Only records were resampled, so the intervals describe uncertainty over records for these three "
        "coders (C01, C02, C03) and this model output, not over other coders or other runs.", "",
    ]


def render_results(point, boot, t3, fam, t6, t7, t8, audit, t10, targets, exposure_population, t12) -> list[str]:
    L = ["# Strict register-sufficient subset against the full random baseline (post hoc, exploratory)", "",
         "**Post hoc and exploratory; not preregistered.** The specification (`SPEC_sufficient_subset_contrast_2026-11-13.md`) was written "
         "on 13 November 2026 after initial results from a since-deleted run had been seen. No hypothesis tests or p-values. "
         "Bootstrap intervals here are 95% percentile intervals (10,000 paired record resamples, seed 20261113). "
         "Distance: MASI. A = C01, B = C02, C = C03, L = Fable 5.", "",
         "Populations: full random baseline (150 records); strict register-sufficient subset (92 records on which at least two coders rated "
         "the entry Sufficient); its complement (58 records). The exposure-flagged record is kept "
         f"(it lies in the {'sufficient subset' if exposure_population == 'sufficient' else 'complement'}). All four raters have complete, valid sets in both dimensions on all 150 records.", ""]
    L += caveats(point, boot, audit, t10, t12)

    L += [f"## {PREFIX}001–002 — Point estimates and strict-minus-full contrasts", "",
          "| Quantity | Domains: full | strict | contrast [95% interval] | Purposes: full | strict | contrast [95% interval] |",
          "|---|---|---|---|---|---|---|"]
    for s in REPLACEMENT_STATISTIC_NAMES:
        cells = []
        for d in DIMENSIONS:
            b = boot[d][s]
            interval = f"[{signed(b['lower'])}, {signed(b['upper'])}]" if b["interval_reported"] else "[not reported]"
            cells += [f"{point[('full', d)][s]:.4f}".replace("-", "−"), f"{point[('sufficient', d)][s]:.4f}".replace("-", "−"), f"{signed(b['point'])} {interval}"]
        L.append(f"| {s}{' (primary)' if s == 'alpha_ABC' else ''} | " + " | ".join(cells) + " |")
    L += ["", "Valid draws: " + "; ".join(f"{d}: {boot[d]['_draws_valid_for_all_contrasts']:,}/{DRAWS:,} valid for every contrast" for d in DIMENSIONS) + ". "
          "Full and strict point estimates equal S3T001, S3T002, S3T011 and S3T012 within 1e-12.", ""]
    L += ["Complement point estimates (descriptive; no intervals): " + "; ".join(
        f"{d}: alpha_ABC {point[('complement', d)]['alpha_ABC']:.4f}, delta_min {signed(point[('complement', d)]['delta_min'])}".replace("-", "−")
        for d in DIMENSIONS) + ".", ""]
    r = t3[0]
    L += [f"## {PREFIX}003 — Strict resample size", "",
          f"Across {DRAWS:,} draws the strict resample held {r['resample_strict_size_min']}–{r['resample_strict_size_max']} occurrences "
          f"(median {r['resample_strict_size_median']:.0f}; central 95% {r['resample_strict_size_q025']:.0f}–{r['resample_strict_size_q975']:.0f}); "
          f"no draw had an empty subset; every draw contained duplicate records.", ""]

    L += [f"## {PREFIX}005 — Disagreement diagnostic, pooled by pair family", "",
          "Pooled over three pairs (3N comparisons per family; not 3N independent observations).", ""]
    for d in DIMENSIONS:
        L += [f"### {d}", "", "| Family | Population | Both Unclear-only | Exactly one Unclear-only | Different substantive (of both substantive) | Exact match | Mean Jaccard | Mean MASI distance | Mean MASI, both substantive |",
              "|---|---|---|---|---|---|---|---|---|"]
        for family in FAMILIES:
            for p in POPULATIONS:
                s = fam[(d, p, family)]
                n, ns = s["comparisons"], s["both_substantive"]
                L.append(f"| {family} | {p} | {pct(s['both_unclear_only'], n)} | {pct(s['exactly_one_unclear_only'], n)} | "
                         f"{pct(s['different_substantive'], ns)} | {pct(s['exact_matches'], n)} | {float(s['jaccard_sum'] / n):.3f} | "
                         f"{float(s['masi_sum'] / n):.3f} | {float(s['masi_sum_substantive'] / ns):.3f} |")
        L.append("")
    L += ["Direction of model–human abstention mismatches (Fable 5 Unclear-only with the coder substantive / the coder Unclear-only with Fable 5 substantive): " +
          "; ".join(f"{d}, {p}: {fam[(d, p, 'model-human')]['first_unclear_only']} / {fam[(d, p, 'model-human')]['second_unclear_only']}"
                    for d in DIMENSIONS for p in ("sufficient", "complement")) + ". Per-pair rows are in `SSC1T004.csv`.", ""]

    L += [f"## {PREFIX}006 — Unclear-only frequency and substantive cardinality, by rater", "",
          "| Dimension | Rater | Unclear-only: sufficient | complement | Mean substantive labels among classified: sufficient | complement |", "|---|---|---|---|---|---|"]
    get6 = {(r["dimension"], r["population"], r["rater"]): r for r in t6}
    for d in DIMENSIONS:
        for rater in RATERS:
            a, b = get6[(d, "sufficient", rater)], get6[(d, "complement", rater)]
            L.append(f"| {d} | {rater} | {pct(a['unclear_only_records'], a['records'])} | {pct(b['unclear_only_records'], b['records'])} | "
                     f"{float(a['mean_substantive_labels_among_classified'] or 'nan'):.2f} | "
                     f"{float(b['mean_substantive_labels_among_classified'] or 'nan'):.2f} |")
    L += ["", f"## {PREFIX}007 — Label counts by rater (sufficient / complement)", "", "Counts out of 92 / 58 records; zero-count labels included.", ""]
    get7 = {(r["dimension"], r["population"], r["rater"], r["label"]): r["count"] for r in t7}
    for d in DIMENSIONS:
        L += [f"### {d}", "", "| Label | " + " | ".join(RATERS) + " |", "|---|" + "---|" * len(RATERS)]
        for label in sorted({k[3] for k in get7 if k[0] == d}):
            L.append(f"| {label} | " + " | ".join(f"{get7[(d, 'sufficient', r, label)]} / {get7[(d, 'complement', r, label)]}" for r in RATERS) + " |")
        L.append("")

    L += [f"## {PREFIX}008 — Secondary check: records where all four raters classify substantively", "",
          "Not a controlled comparison: the records that remain differ in composition between populations.", "",
          "| Dimension | Population | Records | Family | Different substantive sets | Mean MASI distance |", "|---|---|---|---|---|---|"]
    for row in t8:
        if row["population"] == "full":
            continue
        L.append(f"| {row['dimension']} | {row['population']} | {row['records_all_four_substantive']}/{row['records_in_population']} | {row['family']} | "
                 f"{pct(row['different_substantive'], row['comparisons'])} | {float(row['mean_masi_distance']):.3f} |")

    L += ["", f"## {PREFIX}009 — Observed (Do) and expected (De) disagreement", "",
          "Do = mean MASI distance over the three within-record pairs; DoU = abstention mismatches (one set Unclear-only, the other substantive); "
          "DoS = different substantive sets.", "",
          "| Dimension | Panel | Population | Do | DoU | DoS | De | alpha |", "|---|---|---|---|---|---|---|---|"]
    for d in DIMENSIONS:
        for name in PANELS:
            for p in POPULATIONS:
                a = audit[(d, p, name)]
                L.append(f"| {d} | {name} | {p} | {a['Do']:.4f} | {a['DoU']:.4f} | {a['DoS']:.4f} | {a['De']:.4f} | {a['alpha']:.4f} |")
    L += ["", f"## {PREFIX}010 — Arithmetic audit of each contrast", "",
          "alpha_strict − alpha_full = (DoU_full − DoU_strict)/De_full + (DoS_full − DoS_strict)/De_full + Do_strict(1/De_full − 1/De_strict). "
          "Delta rows are the replacement panel's terms minus ABC's. Order-dependent arithmetic, not causal attribution.", "",
          "| Dimension | Contrast | U term | S term | De term | Total |", "|---|---|---|---|---|---|"]
    for row in t10:
        L.append(f"| {row['dimension']} | {row['contrast'].split(':')[0]} | {signed(float(row['U_term_unclear_vs_substantive']))} | "
                 f"{signed(float(row['S_term_different_substantive']))} | {signed(float(row['De_term_expected_disagreement']))} | {signed(float(row['identity_total']))} |")

    matched = sum(t["match"] for t in targets)
    L += ["", f"## {PREFIX}011 — Comparison with the deleted 13 November run", "",
          f"{matched} of {len(targets)} target items reproduce exactly (bootstrap at four decimal places, alpha at six, counts exactly)."]
    misses = [t for t in targets if not t["match"]]
    if misses:
        L += ["", "| Item | This run | Deleted run |", "|---|---|---|"] + [f"| {t['item']} | {t['observed']} | {t['target']} |" for t in misses]
    L.append("")
    L += [f"## {PREFIX}012 — Coder abstention by the coder's own sufficiency rating (caveat 1)", "",
          "| Dimension | Coder | Unclear-only when own rating Sufficient | Unclear-only when own rating not Sufficient |", "|---|---|---|---|"]
    L += [f"| {r['dimension']} | {r['coder']} | {pct(r['unclear_only_when_own_sufficient'], r['own_sufficient_records'])} | "
          f"{pct(r['unclear_only_when_own_not_sufficient'], r['own_not_sufficient_records'])} |" for r in t12]
    L.append("")
    L += suggested_text(point, boot, fam, audit)
    return L


def suggested_text(point, boot, fam, audit) -> list[str]:
    """Suggested compact tables (not applied to the manuscript)."""
    D, P = DIMENSIONS
    b = lambda d, s, places=3: (f"{signed(boot[d][s]['point'], places)} [{signed(boot[d][s]['lower'], places)}, {signed(boot[d][s]['upper'], places)}]")
    f = lambda d, p, fm: fam[(d, p, fm)]
    L = ["## Suggested manuscript tables (not applied)", "",
         "### Compact bootstrap table", "",
         "Strict register-sufficient subset (n = 92) minus full random baseline (n = 150); paired record bootstrap, 10,000 resamples; 95% percentile intervals. "
         "Post hoc. delta_min equals delta_B at the point estimate. The subset is defined by the coders' own sufficiency ratings, which track their "
         "own abstention, and the coders are held fixed; see the caveats above.", "",
         "| Quantity | Research Domains | Analytical Purposes |", "|---|---|---|"]
    names = {"alpha_ABC": "Human-only alpha (C01, C02, C03)", "delta_A": "delta_A (Fable 5 replaces C01)",
             "delta_B": "delta_B (Fable 5 replaces C02)", "delta_C": "delta_C (Fable 5 replaces C03)", "delta_min": "delta_min"}
    for s, label in names.items():
        L.append(f"| {label} | {b(D, s)} | {b(P, s)} |")
    L += ["", "### Small diagnostic table", "",
          "Pair comparisons pooled over three pairs per family (3N; not independent). Sufficient subset (92 records) / complement (58 records).", "",
          "| Dimension | Pairs | One rater Unclear-only, other substantive | Different substantive sets, of comparisons where both classify |", "|---|---|---|---|"]
    for d in DIMENSIONS:
        for fm in FAMILIES:
            s, c = f(d, "sufficient", fm), f(d, "complement", fm)
            L.append(f"| {d} | {fm} | {share(s['exactly_one_unclear_only'], s['comparisons'])} / {share(c['exactly_one_unclear_only'], c['comparisons'])} | "
                     f"{s['different_substantive']}/{s['both_substantive']} ({share(s['different_substantive'], s['both_substantive'])}) / "
                     f"{c['different_substantive']}/{c['both_substantive']} ({share(c['different_substantive'], c['both_substantive'])}) |")
    L.append("")
    return L


if __name__ == "__main__":
    main()
