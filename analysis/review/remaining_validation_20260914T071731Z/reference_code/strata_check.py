"""Independent recomputation of the post hoc hard-case-stratum outputs.

Audited run: analysis/outputs_validation_scratch_hard_case_strata_20260825 (2026-08-25T16:18Z).
Definitions: saved strata, Stage A and Stage B methods; protocol v1.1 §5.3, §8.3 and §8.9.
MASI distance = 1 - Jaccard x overlap weight (1 equal, 2/3 subset, 1/3 partial overlap, 0 disjoint).
Krippendorff alpha point estimates use the literal ordered-pair definition in exact rationals;
bootstrap replicates use an exact integer-scaled coincidence form. No production module is imported.
"""
from __future__ import annotations

import json
import random
import re
from fractions import Fraction

import numpy as np
import pandas as pd

import common as C

FAM_M, FAM_P, FAM_B, FAM_R, FAM_S, FAM_I = (
    "strata_membership", "strata_point", "strata_bootstrap", "strata_reconciliation",
    "strata_summary_display", "strata_interpretation")
STRATA = ("domain_only", "purpose_only", "both")
MODEL_PAIRS = (("L-A", 3, 0), ("L-B", 3, 1), ("L-C", 3, 2))
HUMAN_PAIRS = (("A-B", 0, 1), ("A-C", 0, 2), ("B-C", 1, 2))
JACCARD_SCALE = 27720  # lcm(1..12): every Jaccard value on <=12 labels is an integer multiple of 1/27720
MASI_SCALE = 83160     # 3 * lcm(1..12)
REPLACEMENT_COLUMNS = {
    "human_alpha": "alpha_ABC", "replace_a_alpha": "alpha_LBC", "replace_b_alpha": "alpha_ALC",
    "replace_c_alpha": "alpha_ABL", "delta_a": "delta_A", "delta_b": "delta_B", "delta_c": "delta_C",
    "delta_min": "delta_min",
}
PANELS = {"alpha_ABC": (0, 1, 2), "alpha_LBC": (3, 1, 2), "alpha_ALC": (0, 3, 2), "alpha_ABL": (0, 1, 3)}
_MASI_CACHE: dict = {}


def jaccard(a: frozenset, b: frozenset) -> Fraction:
    union = a | b
    return Fraction(1) if not union else Fraction(len(a & b), len(union))


def masi(a: frozenset, b: frozenset) -> Fraction:
    key = (a, b)
    if key not in _MASI_CACHE:
        union, inter = a | b, a & b
        if not union:
            value = Fraction(0)
        else:
            if a == b:
                weight = Fraction(1)
            elif not inter:
                weight = Fraction(0)
            elif a < b or b < a:
                weight = Fraction(2, 3)
            else:
                weight = Fraction(1, 3)
            value = 1 - Fraction(len(inter), len(union)) * weight
        _MASI_CACHE[key] = value
    return _MASI_CACHE[key]


def alpha_pairwise(units) -> Fraction | None:
    """Krippendorff alpha from its ordered-pair definition (complete units, exact arithmetic)."""
    pooled = [value for unit in units for value in unit]
    n = len(pooled)
    observed = Fraction(0)
    for unit in units:
        m = len(unit)
        observed += sum((masi(unit[i], unit[j]) for i in range(m) for j in range(m) if i != j), Fraction(0)) / (m - 1)
    observed /= n
    expected = sum((masi(pooled[i], pooled[j]) for i in range(n) for j in range(n) if i != j), Fraction(0)) / (n * (n - 1))
    return None if expected == 0 else 1 - observed / expected


class IntegerAlpha:
    """Exact rational alpha for resampled three-rater units via integer-scaled MASI coincidences."""

    def __init__(self, values):
        self.categories = sorted(set(values), key=lambda s: tuple(sorted(s)))
        self.index = {value: i for i, value in enumerate(self.categories)}
        size = len(self.categories)
        self.distance = np.zeros((size, size), dtype=np.int64)
        for i, a in enumerate(self.categories):
            for j, b in enumerate(self.categories):
                scaled = masi(a, b) * MASI_SCALE
                if scaled.denominator != 1:
                    raise AssertionError("MASI scale does not clear denominators")
                self.distance[i, j] = scaled.numerator

    def alpha(self, idx: np.ndarray) -> Fraction | None:
        n = idx.size
        d = self.distance
        within = int(d[idx[:, 0], idx[:, 1]].sum() + d[idx[:, 0], idx[:, 2]].sum() + d[idx[:, 1], idx[:, 2]].sum())
        counts = np.bincount(idx.ravel(), minlength=len(self.categories)).astype(np.int64)
        expected = int(counts @ d @ counts)
        # observed = (2*within/(m-1))/n with m=3; expected = sum n_c n_k d_ck / (n(n-1)); common scale cancels.
        return None if expected == 0 else 1 - Fraction(within * (n - 1), expected)


def draws(n: int) -> list[np.ndarray]:
    """Record-level resamples: Python random.Random(seed), randrange(n) n times per replicate."""
    rng = random.Random(C.SEED)
    return [np.array([rng.randrange(n) for _ in range(n)], dtype=np.int64) for _ in range(C.ATTEMPTS)]


def block(records, ids, dim):
    """Sorted Record ID order (resampling index convention, corroborated by replicate reproduction)."""
    return [(records[r]["coders"]["C01"][dim], records[r]["coders"]["C02"][dim],
             records[r]["coders"]["C03"][dim], records[r]["model"][dim]) for r in sorted(ids)]


def _row(frame: pd.DataFrame, **key) -> dict:
    mask = np.ones(len(frame), dtype=bool)
    for column, value in key.items():
        mask &= frame[column].to_numpy() == value
    matches = frame[mask]
    if len(matches) != 1:
        raise ValueError(f"{key} matched {len(matches)} rows")
    return matches.iloc[0].to_dict()


def membership(L: C.Ledger, P: dict, meta: dict) -> dict[str, frozenset]:
    hard, base, cross, records, diag = P["hard"], P["base"], P["cross"], P["records"], P["diag"]
    a_h, a_b, a_x, a_r, a_m = (C.rel(C.HARD), C.rel(C.BASE), C.rel(C.CROSS), C.rel(C.RAW), C.rel(C.MODEL))
    a_meta = C.rel(C.STRATA / "run_metadata.json")
    for artifact_id, path in (("POST-028", C.RAW), ("POST-009", C.BASE), ("POST-011", C.HARD), ("POST-019", C.CROSS), ("RED-036", C.DICTIONARY)):
        L.exact(FAM_M, C.rel(path), f"manifest {artifact_id}", "input SHA-256 equals preregistration manifest identity",
                C.manifest_row(artifact_id)["sha256"], C.sha256(path))
    recorded_model = next(x for x in meta["verified_authorities"] if x["manifest_id"] == "MOD-006")
    L.exact(FAM_M, a_m, "manifest MOD-006", "model output SHA-256 equals the LF-normalised identity recorded at the strata run",
            recorded_model["observed_sha256"], C.sha256(C.MODEL),
            note="Manifest raw identity 6f4ff530...; manifest notes document the LF representation 9827fc9f...")

    L.exact(FAM_M, a_h, "all rows", "POST-011 row count", 75, len(hard))
    L.exact(FAM_M, a_h, "record_id", "unique Record IDs", 75, int(hard["record_id"].nunique()))
    L.exact(FAM_M, a_h, "official_project_id", "repeated official Project IDs inside the hard-case sample", 0,
            int(hard["official_project_id"].duplicated().sum()),
            note="Unit of analysis is Record ID; with no repeat, no Project-ID collapse question arises")
    counts = hard["hard_case_stratum"].value_counts().to_dict()
    for stratum in STRATA:
        L.exact(FAM_M, a_meta, f"stratum_counts.{stratum}", "saved stratum size equals POST-011 count",
                meta["stratum_counts"][stratum], int(counts.get(stratum, 0)))
    L.exact(FAM_M, a_h, "hard_case_stratum", "values outside domain_only/purpose_only/both", 0,
            int((~hard["hard_case_stratum"].isin(STRATA)).sum()))
    L.exact(FAM_M, a_h, "record_id x hard_case_stratum", "records assigned to more than one stratum (mutual exclusivity)", 0,
            int(hard.groupby("record_id")["hard_case_stratum"].nunique().gt(1).sum()))
    L.exact(FAM_M, a_h, "sample_family/sample_status/validation_included", "rows not hard_case/active/yes", 0,
            int(((hard["sample_family"] != "hard_case") | (hard["sample_status"] != "active") | (hard["validation_included"] != "yes")).sum()))
    L.exact(FAM_M, a_b, "record_id vs POST-011", "baseline/hard-case Record ID overlap", 0,
            len(set(base["record_id"]) & set(hard["record_id"])))
    L.exact(FAM_M, a_b, "official_project_id vs POST-011", "baseline/hard-case official Project ID overlap", 0,
            len(set(base["official_project_id"]) & set(hard["official_project_id"])))

    hx = cross[cross["sample_family"] == "hard_case"]
    L.exact(FAM_M, a_x, "sample_family=hard_case", "hard-case assignment rows", 225, len(hx))
    coder_sets = hx.groupby("source_record_id")["reviewer_id"].apply(lambda s: tuple(sorted(s)))
    L.exact(FAM_M, a_x, "reviewer_id per hard-case record", "records with exactly one C01, C02 and C03 assignment", 75,
            int((coder_sets == C.CODERS).sum()))
    L.exact(FAM_M, a_x, "source_record_id", "hard-case crosswalk Record ID set equals POST-011", True,
            set(hx["source_record_id"]) == set(hard["record_id"]))
    L.exact(FAM_M, a_x, "hard_case_stratum within record", "records whose three assignments carry different strata", 0,
            int(hx.groupby("source_record_id")["hard_case_stratum"].nunique().ne(1).sum()))
    stratum_of = dict(zip(hard["record_id"], hard["hard_case_stratum"]))
    L.exact(FAM_M, a_x, "hard_case_stratum vs POST-011", "hard-case assignment rows whose stratum differs from POST-011", 0,
            int(sum(stratum_of.get(r) != s for r, s in zip(hx["source_record_id"], hx["hard_case_stratum"]))))
    bx = cross[cross["sample_family"] == "baseline"]
    L.exact(FAM_M, a_x, "sample_family=baseline", "baseline crosswalk Record ID set equals POST-009", True,
            set(bx["source_record_id"]) == set(base["record_id"]))
    labelled = base[base["hard_case_stratum"] != ""]
    lc = labelled["hard_case_stratum"].value_counts().to_dict()
    L.add(FAM_M, a_b, "hard_case_stratum on baseline rows",
          "baseline records carrying a disagreement-frame stratum label (must not enter the 25-record strata)",
          "not described in strata methods", f"{len(labelled)} (domain_only {lc.get('domain_only', 0)}; purpose_only {lc.get('purpose_only', 0)}; both {lc.get('both', 0)})",
          "descriptive; strata restricted by sample_family", "VERIFIED", "N-STRATA-LABEL-SCOPE")
    forced = hard[hard["forced_into_active_hard"] == "True"]
    fc = forced["hard_case_stratum"].value_counts().to_dict()
    L.add(FAM_M, a_h, "forced_into_active_hard", "accompanying-tag records forced into the active strata (protocol §5.3 ¶57)",
          "not disclosed in strata methods, summary or report Section 11",
          f"{len(forced)} (domain_only {fc.get('domain_only', 0)}; purpose_only {fc.get('purpose_only', 0)}; both {fc.get('both', 0)})",
          "count toward the 25-record quota; non-random within stratum", "VERIFIED", "M-STRATA-FORCED")
    L.exact(FAM_M, a_h, "accompanying_tag_disagreement vs forced_into_active_hard", "rows where the two flags differ", 0,
            int((hard["accompanying_tag_disagreement"] != hard["forced_into_active_hard"]).sum()))

    L.add(FAM_M, a_h, "official draw 2026-07-24", "re-execution of the stratified draw (SEED_DRAW 20260713) from the 380-record frame",
          "", "", "draw reproduced from frame, exclusions and seed", "NOT_CHECKED",
          note="Not attempted: re-execution would materialise embargoed reserve identities; membership taken from hash-verified POST-011 and cross-checked against POST-019")
    for key, expected, check in (
        ("formal_rows", 675, "validation_included=1 response rows"),
        ("formal_assignment_duplicates", 0, "duplicate formal assignment IDs"),
        ("join_both", 675, "export-to-POST-019 one-to-one matches"),
        ("join_export_only", 0, "formal export rows without a crosswalk assignment"),
        ("join_crosswalk_only", 0, "crosswalk assignments without a formal export row"),
        ("reviewer_mismatch", 0, "reviewer pseudonym disagreements between export and crosswalk"),
        ("record_mismatch", 0, "source Record ID disagreements between export and crosswalk"),
        ("incomplete_formal", 0, "formal responses with scratch_coder_complete != 2"),
        ("response_duplicates", 0, "duplicate (record, coder) responses"),
        ("invalid_checkbox_responses", 0, "responses with non-0/1 domain/purpose checkbox values"),
        ("empty_coder_sets", 0, "empty coder domain or purpose sets"),
        ("nonformal_rows_on_formal_records", 0, "validation_included=0 rows attached to formal records"),
        ("model_duplicate_record_ids", 0, "duplicate Record IDs in production model output"),
        ("model_join_unique", 225, "formal records joined one-to-one to production model"),
        ("model_unknown_labels", 0, "model domain/purpose labels outside frozen REDCap label sets"),
    ):
        L.exact(FAM_M, a_m if key.startswith("model") else a_r, key, check, expected, diag[key])
    L.add(FAM_M, a_r, "sample_set / hard_stratum (formal rows)", "export hidden sample/stratum fields as a third membership source",
          "", f"non-blank sample_set {diag['export_sample_set_nonblank_formal']}; non-blank hard_stratum {diag['export_hard_stratum_nonblank_formal']} of 675",
          "fields must be populated to be usable", "NOT_CHECKED",
          note="Both fields are blank for every formal row; membership rests on POST-011 and POST-019, which agree")
    for key in ("model_empty_sets", "coder_unclear_with_other_label", "model_unclear_with_other_label"):
        L.add(FAM_M, a_m if key.startswith("model") else a_r, key, f"descriptive count: {key.replace('_', ' ')} (all 225 formal records)",
              "", diag[key], "descriptive; Unclear retained as an ordinary label per saved methods", "VERIFIED")

    strata = {s: frozenset(hard.loc[hard["hard_case_stratum"] == s, "record_id"]) for s in STRATA}
    for stratum, ids in strata.items():
        available = sum(set(records[r]["coders"]) == set(C.CODERS) and all(records[r]["coders"][c]["complete"] for c in C.CODERS)
                        and records[r]["model"] is not None for r in ids)
        L.exact(FAM_M, a_r, f"stratum={stratum}", "records with three complete coder responses and a model output (complete cases, both dimensions)",
                25, available)
    L.exact(FAM_M, a_h, "union of strata", "union equals POST-011 and strata are pairwise disjoint", "75|0",
            f"{len(frozenset().union(*strata.values()))}|{sum(len(a & b) for i, a in enumerate(strata.values()) for b in list(strata.values())[i + 1:])}")
    return strata


def set_metrics(L, P, strata, model_csv, human_csv, boot_set, out):
    records = P["records"]
    art_m = C.rel(C.STRATA / "hard_case_stratum_exact_set_jaccard.csv")
    art_h = C.rel(C.STRATA / "hard_case_stratum_human_pair_agreement.csv")
    art_bs = C.rel(C.STRATA / "bootstrap_hard_case_stratum_exact_set_jaccard.csv")
    resamples = draws(25)
    grouped = {key: frame.sort_values("replicate") for key, frame in boot_set.groupby(["stratum", "dimension", "pair"])}
    for stratum in STRATA:
        for dim in C.DIMENSIONS:
            rows = block(records, strata[stratum], dim)
            n = len(rows)
            for label, pairs, frame, artifact, bootstrap in (("model", MODEL_PAIRS, model_csv, art_m, True),
                                                           ("human", HUMAN_PAIRS, human_csv, art_h, False)):
                means = []
                for pair, i, j in pairs:
                    exact = np.array([int(r[i] == r[j]) for r in rows], dtype=np.int64)
                    jac = [jaccard(r[i], r[j]) for r in rows]
                    jac_scaled = np.array([int(x * JACCARD_SCALE) for x in jac], dtype=np.int64)
                    if any(Fraction(int(v), JACCARD_SCALE) != x for v, x in zip(jac_scaled, jac)):
                        raise AssertionError("Jaccard scale does not clear denominators")
                    proportion = Fraction(int(exact.sum()), n)
                    mean_j = sum(jac, Fraction(0)) / n
                    means.append((proportion, mean_j))
                    saved = _row(frame, stratum=stratum, dimension=dim, pair=pair)
                    ident = f"stratum={stratum}; dimension={dim}; pair={pair}"
                    out.setdefault("set", {})[(stratum, dim, pair)] = {"exact": float(proportion), "jaccard": float(mean_j)}
                    L.exact(FAM_P, artifact, ident, "n_records", saved["n_records"], str(n))
                    L.exact(FAM_P, artifact, ident, "exact_match_n", saved["exact_match_n"], str(int(exact.sum())))
                    L.num(FAM_P, artifact, ident, "exact_match_proportion", saved["exact_match_proportion"], float(proportion), C.TOL_FLOAT)
                    L.num(FAM_P, artifact, ident, "mean_jaccard", saved["mean_jaccard"], float(mean_j), C.TOL_FLOAT)
                    floats = [float(x) for x in jac]
                    for column, p in (("median_jaccard", 0.5), ("q1_jaccard", 0.25), ("q3_jaccard", 0.75)):
                        L.num(FAM_P, artifact, ident, f"{column} (Type 7 over 25 record Jaccard values)", saved[column], C.type7(floats, p), C.TOL_FLOAT)
                    if not bootstrap:
                        continue
                    mine_e = [float(Fraction(int(exact[d].sum()), n)) for d in resamples]
                    mine_j = [float(Fraction(int(jac_scaled[d].sum()), n * JACCARD_SCALE)) for d in resamples]
                    saved_group = grouped[(stratum, dim, pair)]
                    L.exact(FAM_B, art_bs, ident, "replicate numbering 1..2000 complete", True,
                            saved_group["replicate"].tolist() == list(range(1, C.ATTEMPTS + 1)))
                    for column, mine, ci in (("exact_match_proportion", mine_e, "exact_match"), ("mean_jaccard", mine_j, "mean_jaccard")):
                        saved_values = saved_group[column].to_numpy(dtype=float)
                        diffs = np.abs(saved_values - np.array(mine))
                        L.add(FAM_B, art_bs, ident, f"{column}: all 2000 saved replicate values reproduced from regenerated record resamples",
                              "2000 saved values", f"{int((diffs <= C.TOL_FLOAT).sum())} of 2000 within tolerance",
                              f"every replicate absolute difference <= {C.TOL_FLOAT:g}",
                              "VERIFIED" if bool((diffs <= C.TOL_FLOAT).all()) else "DISCREPANT", difference=repr(float(diffs.max())))
                        L.exact(FAM_B, artifact, ident, f"{ci}_bootstrap_valid_n (finite saved replicates)", saved[f"{ci}_bootstrap_valid_n"],
                                str(int(np.isfinite(saved_values).sum())))
                        for bound, p in (("lower", 0.025), ("upper", 0.975)):
                            L.num(FAM_B, artifact, ident, f"{ci}_ci_{bound} = Type 7 p={p} of saved replicates", saved[f"{ci}_ci_{bound}"],
                                  C.type7(saved_values, p), C.TOL_FLOAT)
                            L.num(FAM_B, artifact, ident, f"{ci}_ci_{bound} = Type 7 p={p} of independently regenerated replicates",
                                  saved[f"{ci}_ci_{bound}"], C.type7(mine, p), C.TOL_FLOAT)
                            out.setdefault("ci", {})[(stratum, dim, pair, ci, bound)] = C.type7(mine, p)
                mean_exact = sum((m[0] for m in means), Fraction(0)) / 3
                mean_jac = sum((m[1] for m in means), Fraction(0)) / 3
                out.setdefault("pair_mean", {})[(label, stratum, dim)] = (float(mean_exact), float(mean_jac))
                for pair, _, _ in pairs:
                    saved = _row(frame, stratum=stratum, dimension=dim, pair=pair)
                    ident = f"stratum={stratum}; dimension={dim}; pair={pair}"
                    finding = "U0068" if label == "human" else ""
                    what = "human pairs A-B/A-C/B-C" if label == "human" else "model-coder pairs L-A/L-B/L-C"
                    L.num(FAM_P, artifact, ident, f"mean_model_coder_exact_set = mean exact-set proportion over {what}",
                          saved["mean_model_coder_exact_set"], float(mean_exact), C.TOL_FLOAT, finding)
                    L.num(FAM_P, artifact, ident, f"mean_model_coder_jaccard = mean Jaccard over {what}",
                          saved["mean_model_coder_jaccard"], float(mean_jac), C.TOL_FLOAT, finding)


def replacement(L, P, strata, rep_csv, boot_rep, out):
    records = P["records"]
    art = C.rel(C.STRATA / "hard_case_stratum_replacement.csv")
    art_b = C.rel(C.STRATA / "bootstrap_hard_case_stratum_replacement.csv")
    resamples = draws(25)
    grouped = {key: frame.sort_values("replicate") for key, frame in boot_rep.groupby(["stratum", "dimension"])}
    for stratum in STRATA:
        for dim in C.DIMENSIONS:
            rows = block(records, strata[stratum], dim)
            ident = f"stratum={stratum}; dimension={dim}"
            saved = _row(rep_csv, stratum=stratum, dimension=dim)
            exact = {name: alpha_pairwise([tuple(r[k] for k in cols) for r in rows]) for name, cols in PANELS.items()}
            values = dict(exact)
            values["delta_A"] = exact["alpha_LBC"] - exact["alpha_ABC"]
            values["delta_B"] = exact["alpha_ALC"] - exact["alpha_ABC"]
            values["delta_C"] = exact["alpha_ABL"] - exact["alpha_ABC"]
            values["delta_min"] = min(values["delta_A"], values["delta_B"], values["delta_C"])
            out.setdefault("replacement", {})[(stratum, dim)] = {k: float(v) for k, v in values.items()}
            L.exact(FAM_P, art, ident, "n_records (complete cases)", saved["n_records"], str(len(rows)))
            for column, name in REPLACEMENT_COLUMNS.items():
                L.num(FAM_P, art, ident, f"{column} ({name}; MASI; exact-rational ordered-pair alpha)", saved[column], float(values[name]), C.TOL_FLOAT)
            engine = IntegerAlpha([v for r in rows for v in r])
            idx = np.array([[engine.index[v] for v in r] for r in rows], dtype=np.int64)
            identity = {name: engine.alpha(idx[:, list(cols)]) for name, cols in PANELS.items()}
            L.exact(FAM_P, art, ident, "two independent exact formulations (ordered-pair vs coincidence) agree for all four panels",
                    True, all(identity[k] == exact[k] for k in PANELS), criterion="exact rational equality")
            mine = {name: [] for name in REPLACEMENT_COLUMNS.values()}
            undefined = 0
            for d in resamples:
                sub = idx[d]
                alphas = {name: engine.alpha(sub[:, list(cols)]) for name, cols in PANELS.items()}
                if any(v is None for v in alphas.values()):
                    undefined += 1
                    for name in mine:
                        mine[name].append(float("nan"))
                    continue
                deltas = [alphas["alpha_LBC"] - alphas["alpha_ABC"], alphas["alpha_ALC"] - alphas["alpha_ABC"], alphas["alpha_ABL"] - alphas["alpha_ABC"]]
                for name, value in (*alphas.items(), ("delta_A", deltas[0]), ("delta_B", deltas[1]), ("delta_C", deltas[2]), ("delta_min", min(deltas))):
                    mine[name].append(float(value))
            group = grouped[(stratum, dim)]
            L.exact(FAM_B, art_b, ident, "replicate numbering 1..2000 and sample_n=25 throughout", "True|True",
                    f"{group['replicate'].tolist() == list(range(1, C.ATTEMPTS + 1))}|{bool((group['sample_n'] == 25).all())}")
            for name, series in mine.items():
                saved_values = group[name].to_numpy(dtype=float)
                diffs = np.abs(saved_values - np.array(series))
                ok = bool(np.all(diffs <= C.TOL_FLOAT))
                L.add(FAM_B, art_b, ident, f"{name}: all 2000 saved replicate values reproduced (joint A/B/C/L record resampling)",
                      "2000 saved values", f"{int((diffs <= C.TOL_FLOAT).sum())} of 2000 within tolerance",
                      f"every replicate absolute difference <= {C.TOL_FLOAT:g}", "VERIFIED" if ok else "DISCREPANT",
                      difference=repr(float(np.nanmax(diffs))))
            saved_delta = group["delta_min"].to_numpy(dtype=float)
            L.exact(FAM_B, art, ident, "bootstrap_valid_n / bootstrap_invalid_n", f"{saved['bootstrap_valid_n']}|{saved['bootstrap_invalid_n']}",
                    f"{C.ATTEMPTS - undefined}|{undefined}")
            for bound, p in (("lower", 0.025), ("upper", 0.975)):
                L.num(FAM_B, art, ident, f"delta_min_ci_{bound} = Type 7 p={p} of saved replicates", saved[f"delta_min_ci_{bound}"],
                      C.type7(saved_delta, p), C.TOL_FLOAT, "U0005")
                L.num(FAM_B, art, ident, f"delta_min_ci_{bound} = Type 7 p={p} of independently regenerated replicates",
                      saved[f"delta_min_ci_{bound}"], C.type7(mine["delta_min"], p), C.TOL_FLOAT, "U0005")
                out.setdefault("ci", {})[(stratum, dim, "delta_min", bound)] = C.type7(mine["delta_min"], p)


def reconcile(L, P, strata, model_csv, out):
    records = P["records"]
    pooled_ids = frozenset().union(*strata.values())
    art_b = C.rel(C.STAGE_B / "exact_set_jaccard_summary.csv")
    stage_b = C.read_str_csv(C.STAGE_B / "exact_set_jaccard_summary.csv")
    for dim in C.DIMENSIONS:
        rows = block(records, pooled_ids, dim)
        for pair, i, j in MODEL_PAIRS:
            saved = _row(stage_b, population="hard_case", dimension=dim, pair=pair)
            ident = f"population=hard_case; dimension={dim}; pair={pair}"
            strata_rows = [_row(model_csv, stratum=s, dimension=dim, pair=pair) for s in STRATA]
            L.exact(FAM_R, art_b, ident, "pooled n_records equals sum of stratum n_records (disjoint strata)", saved["n_records"],
                    str(sum(int(r["n_records"]) for r in strata_rows)))
            L.exact(FAM_R, art_b, ident, "pooled exact_match_n equals sum of saved stratum exact_match_n (additive count)", saved["exact_match_n"],
                    str(sum(int(r["exact_match_n"]) for r in strata_rows)))
            L.num(FAM_R, art_b, ident, "pooled mean_jaccard equals n-weighted mean of saved stratum means (equal n=25; additive totals)",
                  saved["mean_jaccard"], sum(float(r["mean_jaccard"]) * int(r["n_records"]) for r in strata_rows) / 75, C.TOL_FLOAT)
            jac = [float(jaccard(r[i], r[j])) for r in rows]
            L.exact(FAM_R, art_b, ident, "pooled exact_match_n recomputed on the 75-record union", saved["exact_match_n"],
                    str(sum(r[i] == r[j] for r in rows)))
            for column, p in (("median_jaccard", 0.5), ("q1_jaccard", 0.25), ("q3_jaccard", 0.75)):
                L.num(FAM_R, art_b, ident, f"pooled {column} recomputed on union (not derivable from stratum quartiles)", saved[column],
                      C.type7(jac, p), C.TOL_FLOAT)
    stage_a_panels = C.read_str_csv(C.STAGE_A / "replacement_panel_results.csv")
    stage_a_delta = C.read_str_csv(C.STAGE_A / "replacement_delta_results.csv")
    art_a = C.rel(C.STAGE_A / "replacement_panel_results.csv")
    for dim in C.DIMENSIONS:
        rows = block(records, pooled_ids, dim)
        exact = {name: alpha_pairwise([tuple(r[k] for k in cols) for r in rows]) for name, cols in PANELS.items()}
        for name, panel in (("alpha_ABC", "ABC"), ("alpha_LBC", "LBC"), ("alpha_ALC", "ALC"), ("alpha_ABL", "ABL")):
            saved = _row(stage_a_panels, population="hard_case", dimension=dim, panel=panel)
            L.num(FAM_R, art_a, f"population=hard_case; dimension={dim}; panel={panel}",
                  "pooled alpha recomputed on the 75-record union (never averaged from strata)", saved["point_estimate"], float(exact[name]), C.TOL_FLOAT)
        delta_min = min(exact["alpha_LBC"], exact["alpha_ALC"], exact["alpha_ABL"]) - exact["alpha_ABC"]
        saved = _row(stage_a_delta, population="hard_case", dimension=dim, delta="delta_min")
        L.num(FAM_R, C.rel(C.STAGE_A / "replacement_delta_results.csv"), f"population=hard_case; dimension={dim}; delta=delta_min",
              "pooled delta_min recomputed on union", saved["point_estimate"], float(delta_min), C.TOL_FLOAT)
        mean_of_strata = sum(out["replacement"][(s, dim)]["alpha_ABC"] for s in STRATA) / 3
        L.add(FAM_R, art_a, f"population=hard_case; dimension={dim}; panel=ABC",
              "non-additivity guard: unweighted mean of stratum alpha_ABC differs from pooled alpha_ABC", saved_value := float(exact["alpha_ABC"]),
              mean_of_strata, "not expected to be equal; strata alphas must not be averaged", "VERIFIED",
              note=f"difference {abs(saved_value - mean_of_strata):.4f}")


FLOAT = r"(-?\d+\.\d{3})"


def summary_display(L, out):
    text = (C.STRATA / "hard_case_stratum_summary.md").read_text(encoding="utf-8")
    art = C.rel(C.STRATA / "hard_case_stratum_summary.md")
    sections = {m.group(1): m.group(2) for m in re.finditer(r"^## (.+?)\n(.*?)(?=^## |\Z)", text, re.S | re.M)}
    fmt = lambda x: f"{x:.3f}"
    parsed = 0
    for heading, label in (("Pair-averaged model–coder comparison", "model"), ("Human–human context", "human")):
        for m in re.finditer(rf"^\| (domain_only|purpose_only|both) \| {FLOAT} \| {FLOAT} \| {FLOAT} \| {FLOAT} \|$", sections[heading], re.M):
            s = m.group(1)
            d, p = out["pair_mean"][(label, s, "Research Domains")], out["pair_mean"][(label, s, "Analytical Purposes")]
            parsed += 1
            L.exact(FAM_S, art, f"{heading}; stratum={s}", "displayed Domain exact/Jaccard, Purpose exact/Jaccard (3 dp)",
                    "|".join(m.group(k) for k in range(2, 6)), "|".join(fmt(x) for x in (d[0], d[1], p[0], p[1])))
    block_text = sections["Pair-averaged model–coder comparison"]
    means = {s: (*out["pair_mean"][("model", s, "Research Domains")], *out["pair_mean"][("model", s, "Analytical Purposes")]) for s in STRATA}
    for m in re.finditer(rf"^- (domain_only|purpose_only|both): exact-set {FLOAT}; Jaccard {FLOAT}\.$", block_text, re.M):
        v = means[m.group(1)]
        parsed += 1
        L.exact(FAM_S, art, f"Domain-minus-Purpose contrast; stratum={m.group(1)}", "displayed contrast (3 dp)",
                f"{m.group(2)}|{m.group(3)}", f"{fmt(v[0] - v[2])}|{fmt(v[1] - v[3])}")
    for m in re.finditer(rf"^- (Domain|Purpose) (\w+) minus (\w+): exact-set {FLOAT}; Jaccard {FLOAT}\.$", block_text, re.M):
        e, j = (0, 1) if m.group(1) == "Domain" else (2, 3)
        a, b = means[m.group(2)], means[m.group(3)]
        parsed += 1
        L.exact(FAM_S, art, f"across-stratum contrast; {m.group(1)} {m.group(2)} minus {m.group(3)}", "displayed contrast (3 dp)",
                f"{m.group(4)}|{m.group(5)}", f"{fmt(a[e] - b[e])}|{fmt(a[j] - b[j])}")
    for m in re.finditer(rf"^\| (\w+) \| (Research Domains|Analytical Purposes) \| (L-[ABC]) \| {FLOAT} \[{FLOAT}, {FLOAT}\] \| {FLOAT} \[{FLOAT}, {FLOAT}\] \|$",
                         sections["Full model–coder results"], re.M):
        s, dim, pair = m.group(1), m.group(2), m.group(3)
        v, ci = out["set"][(s, dim, pair)], out["ci"]
        parsed += 1
        L.exact(FAM_S, art, f"Full model–coder results; stratum={s}; dimension={dim}; pair={pair}", "displayed estimate [CI] pairs (3 dp)",
                "|".join(m.group(k) for k in range(4, 10)),
                "|".join(fmt(x) for x in (v["exact"], ci[(s, dim, pair, "exact_match", "lower")], ci[(s, dim, pair, "exact_match", "upper")],
                                          v["jaccard"], ci[(s, dim, pair, "mean_jaccard", "lower")], ci[(s, dim, pair, "mean_jaccard", "upper")])))
    for m in re.finditer(rf"^\| (\w+) \| (Research Domains|Analytical Purposes) \| {FLOAT} \| {FLOAT} \| {FLOAT} \| {FLOAT} \| {FLOAT} \[{FLOAT}, {FLOAT}\] \|$",
                         sections["Replacement-panel diagnostic"], re.M):
        s, dim = m.group(1), m.group(2)
        r = out["replacement"][(s, dim)]
        parsed += 1
        L.exact(FAM_S, art, f"Replacement-panel diagnostic; stratum={s}; dimension={dim}", "displayed alphas and delta_min [CI] (3 dp)",
                "|".join(m.group(k) for k in range(3, 10)),
                "|".join(fmt(x) for x in (r["alpha_ABC"], r["alpha_LBC"], r["alpha_ALC"], r["alpha_ABL"], r["delta_min"],
                                          out["ci"][(s, dim, "delta_min", "lower")], out["ci"][(s, dim, "delta_min", "upper")])))
    L.exact(FAM_S, art, "all tables and bullet lines", "numeric display lines parsed (3+3 table rows, 3+6 contrasts, 18 + 6 result rows)", 39, parsed)
    for phrase in ("Post hoc diagnostic analysis", "deliberately non-representative", "no hypothesis tests", "The results are descriptive only",
                   "not true errors or a gold standard", "No classifier release decision, population-performance inference, per-label analysis, or adjudication"):
        L.exact(FAM_I, art, f"phrase: {phrase}", "diagnostic framing statement present", True, phrase in text)
    return text


def interpretation(L, out):
    art = C.rel(C.STRATA / "hard_case_stratum_summary.md")
    m = {s: (*out["pair_mean"][("model", s, "Research Domains")], *out["pair_mean"][("model", s, "Analytical Purposes")]) for s in STRATA}
    h = {s: (*out["pair_mean"][("human", s, "Research Domains")], *out["pair_mean"][("human", s, "Analytical Purposes")]) for s in STRATA}
    L.add(FAM_I, art, "domain_only", "intended-dimension signal: Domain below Purpose in domain_only (exact-set | Jaccard)", "",
          f"{m['domain_only'][0] < m['domain_only'][2]}|{m['domain_only'][1] < m['domain_only'][3]}",
          "descriptive; summary does not assert a direction", "VERIFIED", "N-STRATA-INTERP")
    L.add(FAM_I, art, "purpose_only", "intended-dimension signal: Purpose below Domain in purpose_only (exact-set | Jaccard)", "",
          f"{m['purpose_only'][2] < m['purpose_only'][0]}|{m['purpose_only'][3] < m['purpose_only'][1]}",
          "descriptive", "VERIFIED", "N-STRATA-INTERP")
    lowest_human_domain = min(STRATA, key=lambda s: h[s][0])
    L.add(FAM_I, art, "Human–human context", "stratum with lowest human-human Domain exact-set agreement", "",
          f"{lowest_human_domain} ({h[lowest_human_domain][0]:.3f})", "descriptive; shared human difficulty limits attribution to model error",
          "VERIFIED", "N-STRATA-INTERP")
    below = [k for k, v in out["ci"].items() if k[2] == "delta_min" and k[3] == "upper" and v < 0]
    L.add(FAM_I, art, "Replacement-panel diagnostic", "stratum x dimension delta_min intervals with upper bound < 0", "",
          f"{len(below)} of 6", "descriptive; n=25 percentile bootstrap, no multiplicity control, no triggers applied", "VERIFIED", "M-STRATA-SMALLN")


def run(L: C.Ledger, P: dict) -> dict:
    meta = json.loads((C.STRATA / "run_metadata.json").read_text())
    strata = membership(L, P, meta)
    model_csv = C.read_str_csv(C.STRATA / "hard_case_stratum_exact_set_jaccard.csv")
    human_csv = C.read_str_csv(C.STRATA / "hard_case_stratum_human_pair_agreement.csv")
    rep_csv = C.read_str_csv(C.STRATA / "hard_case_stratum_replacement.csv")
    boot_set = pd.read_csv(C.STRATA / "bootstrap_hard_case_stratum_exact_set_jaccard.csv")
    boot_rep = pd.read_csv(C.STRATA / "bootstrap_hard_case_stratum_replacement.csv")
    art_meta = C.rel(C.STRATA / "run_metadata.json")
    for key, expected in (("bootstrap_seed", C.SEED), ("bootstrap_replicates", C.ATTEMPTS)):
        L.exact(FAM_B, art_meta, key, "recorded bootstrap setting used by the independent regeneration", meta[key], expected)
    L.exact(FAM_B, art_meta, "row counts", "saved replicate rows (18 x 2000 set; 6 x 2000 replacement)", "36000|12000", f"{len(boot_set)}|{len(boot_rep)}")
    out: dict = {}
    set_metrics(L, P, strata, model_csv, human_csv, boot_set, out)
    replacement(L, P, strata, rep_csv, boot_rep, out)
    reconcile(L, P, strata, model_csv, out)
    summary_display(L, out)
    interpretation(L, out)
    return {
        "pair_means": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in out["pair_mean"].items()},
        "replacement": {f"{k[0]}|{k[1]}": v for k, v in out["replacement"].items()},
        "delta_min_ci": {f"{k[0]}|{k[1]}|{k[3]}": v for k, v in out["ci"].items() if k[2] == "delta_min"},
    }
