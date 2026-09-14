"""Independent audit of the dated baseline Wilson supplement (2026-09-07T14:24:27Z).

Wilson bounds are the two roots of (k/n - p)^2 = z^2 p(1-p)/n, solved in 80-digit Decimal
arithmetic with z = Phi^{-1}(0.975) obtained by bisection on an erf series (pi by Gauss-Legendre).
Counts are reconstructed from the frozen export through POST-009/POST-019, independently of
the Stage A summaries. No production interval or aggregation function is imported.
"""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path

import common as C

getcontext().prec = 80
FAM_S, FAM_N, FAM_C, FAM_R, FAM_L, FAM_U = ("wilson_scope", "wilson_numeric", "wilson_counts", "wilson_reuse",
                                            "wilson_lineage", "wilson_unit_dependence")
SUFFICIENCY = {1: "Sufficient", 2: "Partially sufficient", 3: "Insufficient"}  # REDCap code 2 is labelled "Partial"
FIT = {1: "Fit", 2: "Partial Fit", 3: "No Fit", 4: "Cannot assess from register entry"}
SPLIT = "No majority / split judgement"
WILSON_COMMIT = "dcf763bdec92a5f65d61cff4eeffaae6ded675fd"
_PI = None


def dec_pi() -> Decimal:
    global _PI
    if _PI is None:
        a, b, t, p = Decimal(1), Decimal(1) / Decimal(2).sqrt(), Decimal(1) / 4, Decimal(1)
        for _ in range(12):
            a_next = (a + b) / 2
            b = (a * b).sqrt()
            t -= p * (a - a_next) ** 2
            a, p = a_next, p * 2
        _PI = (a + b) ** 2 / (4 * t)
    return _PI


def dec_erf(x: Decimal) -> Decimal:
    total, term, k = Decimal(0), x, 0
    threshold = Decimal(10) ** -(getcontext().prec - 5)
    while True:
        addend = term / (2 * k + 1)
        total += addend
        if abs(addend) < threshold:
            break
        k += 1
        term = -term * x * x / k
    return 2 / dec_pi().sqrt() * total


def z975() -> Decimal:
    low, high = Decimal("1.9"), Decimal("2.0")
    root2 = Decimal(2).sqrt()
    for _ in range(220):
        mid = (low + high) / 2
        if (1 + dec_erf(mid / root2)) / 2 < Decimal("0.975"):
            low = mid
        else:
            high = mid
    return (low + high) / 2


def wilson(k: int, n: int, z: Decimal) -> tuple[Decimal, Decimal]:
    k_, n_, z2 = Decimal(k), Decimal(n), z * z
    centre_numerator = 2 * k_ + z2
    root = z * (z2 + 4 * k_ * (n_ - k_) / n_).sqrt()
    denominator = 2 * (n_ + z2)
    return (centre_numerator - root) / denominator, (centre_numerator + root) / denominator


def score_residual(k: int, n: int, p: Decimal, z: Decimal) -> Decimal:
    phat = Decimal(k) / Decimal(n)
    return abs(abs(phat - p) - z * (p * (1 - p) / Decimal(n)).sqrt())


def reconstruct(P: dict) -> tuple[dict, dict]:
    """Baseline counts keyed like the Stage A summary rows, from raw responses only."""
    base_ids = sorted(set(P["base"]["record_id"]))
    records = P["records"]
    counts: dict = {}
    extra: dict = {}
    for coder in C.CODERS:
        suff = [records[r]["coders"][coder]["sufficiency"] for r in base_ids]
        fit = [records[r]["coders"][coder]["fit"] for r in base_ids]
        for code, label in SUFFICIENCY.items():
            counts[("sufficiency_response_distribution", ("coder", coder), ("category", label))] = (sum(v == code for v in suff), sum(v in SUFFICIENCY for v in suff))
        for code, label in FIT.items():
            counts[("taxonomy_fit_response_distribution", ("coder", coder), ("category", label))] = (sum(v == code for v in fit), sum(v in FIT for v in fit))
        extra[f"responses_{coder}"] = (len(suff), len({r for r in base_ids if coder in records[r]["coders"]}))

    def majority(codes, labels):
        if not all(c in labels for c in codes):
            return None
        for code, label in labels.items():
            if sum(c == code for c in codes) >= 2:
                return label
        return SPLIT

    suff_major, fit_major, strict, broad = [], [], [], []
    for r in base_ids:
        s_codes = [records[r]["coders"][c]["sufficiency"] for c in C.CODERS]
        f_codes = [records[r]["coders"][c]["fit"] for c in C.CODERS]
        suff_major.append(majority(s_codes, SUFFICIENCY))
        fit_major.append(majority(f_codes, FIT))
        strict.append(sum(c == 1 for c in s_codes) >= 2)
        broad.append(sum(c in (1, 2) for c in s_codes) >= 2)
    valid_s = sum(v is not None for v in suff_major)
    valid_f = sum(v is not None for v in fit_major)
    for label in (*SUFFICIENCY.values(), SPLIT):
        counts[("sufficiency_record_distribution", ("category", label))] = (suff_major.count(label), valid_s)
    for label in (*FIT.values(), SPLIT):
        counts[("taxonomy_fit_record_distribution", ("category", label))] = (fit_major.count(label), valid_f)
    counts[("sufficiency_subset_summary", ("subset", "strict_register_sufficient"))] = (sum(strict), valid_s)
    counts[("sufficiency_subset_summary", ("subset", "broad_register_usable"))] = (sum(broad), valid_s)
    extra["majority_sufficient_vs_strict_mismatch"] = sum((m == "Sufficient") != s for m, s in zip(suff_major, strict))
    for dim in C.DIMENSIONS:
        uses = [sum(C.UNCLEAR in records[r]["coders"][c][dim] for c in C.CODERS) for r in base_ids]
        for measure, predicate in (("records_with_1_of_3", lambda u: u == 1), ("records_with_2_of_3", lambda u: u == 2),
                                   ("records_with_3_of_3", lambda u: u == 3), ("records_with_majority_use", lambda u: u >= 2)):
            counts[("unclear_register_summary", ("dimension", dim), ("measure", measure))] = (sum(predicate(u) for u in uses), len(uses))
    extra["baseline_records"] = len(base_ids)
    return counts, extra


def recon_key(source_path: str, key: dict):
    stem = Path(source_path).stem
    fields = {"sufficiency_response_distribution": ("coder", "category"), "taxonomy_fit_response_distribution": ("coder", "category"),
              "sufficiency_record_distribution": ("category",), "taxonomy_fit_record_distribution": ("category",),
              "sufficiency_subset_summary": ("subset",), "unclear_register_summary": ("dimension", "measure")}[stem]
    return (stem, *((f, key[f]) for f in fields))


def source_row(source_path: str, key: dict) -> tuple[int, dict]:
    frame = C.read_str_csv(C.ROOT / source_path)
    mask = None
    for column, value in key.items():
        m = frame[column] == value
        mask = m if mask is None else mask & m
    matches = frame[mask]
    return len(matches), (matches.iloc[0].to_dict() if len(matches) else {})


def run(L: C.Ledger, P: dict) -> dict:
    rows = C.read_str_csv(C.WILSON / "wilson_intervals.csv")
    meta = json.loads((C.WILSON / "run_metadata.json").read_text())
    reused = json.loads((C.WILSON / "reused_intervals.json").read_text())
    methods = (C.WILSON / "methods_wilson_baseline.md").read_text()
    manifest = json.loads((C.FOLLOWUP / "wilson_scope_manifest.json").read_text())
    canon = json.loads((C.CANON / "run_metadata.json").read_text())
    by_id = {row["candidate_id"]: row for row in manifest["rows"]}
    art = C.rel(C.WILSON / "wilson_intervals.csv")
    art_meta = C.rel(C.WILSON / "run_metadata.json")
    art_methods = C.rel(C.WILSON / "methods_wilson_baseline.md")
    art_manifest = C.rel(C.FOLLOWUP / "wilson_scope_manifest.json")
    ids = rows["candidate_id"].tolist()
    selected = set(ids)

    # ---- scope -------------------------------------------------------------------------------------------
    L.exact(FAM_S, art, "candidate_id", "interval rows / unique candidate IDs", "37|37", f"{len(ids)}|{len(selected)}")
    methods_ids = re.search(r"Included IDs are `([^`]+)`", methods).group(1).split(", ")
    L.exact(FAM_S, art_methods, "Included IDs", "methods ID list equals CSV IDs", sorted(methods_ids), sorted(ids))
    L.exact(FAM_S, art_meta, "selection_list", "metadata selection list equals CSV IDs", sorted(meta["selection_list"]), sorted(ids))
    L.exact(FAM_S, C.rel(C.CANON / "run_metadata.json"), "supplement.new_interval_candidate_ids", "canonical supplement IDs equal CSV IDs",
            sorted(canon["supplement"]["new_interval_candidate_ids"]), sorted(ids))
    L.add(FAM_S, art_methods, "approval instruction", "archived approval text defining the 37-row selection",
          "methods cite 'the explicit selected scope in the user instruction'", "no repository record located",
          "approval text resolvable in repository", "BLOCKED", "N-WILSON-APPROVAL-RECORD",
          note="Consistency of the list across methods, metadata, CSV, canonical metadata and manifest decisions is verified instead")
    rows_manifest = manifest["rows"]
    candidates = [r for r in rows_manifest if r["scope_decision"] == "candidate_for_later_authorised_wilson"]
    L.exact(FAM_S, art_manifest, "totals.decisions", "manifest decision totals recomputed from rows", manifest["totals"]["decisions"],
            dict(Counter(r["scope_decision"] for r in rows_manifest)))
    L.exact(FAM_S, art_manifest, "selected vs candidates", "selected IDs that are not manifest candidates", 0, len(selected - {r["candidate_id"] for r in candidates}))
    unselected = [r for r in candidates if r["candidate_id"] not in selected]
    excluded = meta["scope_decision"]["excluded"]
    L.exact(FAM_S, art_meta, "scope_decision.excluded.qa_candidates", "unselected candidates (all qa_record_status family)",
            f"{excluded['qa_candidates']}|True", f"{len(unselected)}|{all(r['metric_family'] == 'qa_record_status' for r in unselected)}")
    pooled = [r for r in rows_manifest if r["scope_decision"] == "methodological_decision_required"]
    L.exact(FAM_S, art_meta, "scope_decision.excluded.pooled_response_rows", "pooled within-project rows excluded", excluded["pooled_response_rows"], len(pooled))
    L.exact(FAM_U, art_manifest, "methodological_decision_required rows", "pooled rows: all baseline, pooled flag true, none given a supplement interval",
            f"{len(pooled)}|{len(pooled)}|0",
            f"{sum(r['population'] == 'baseline' for r in pooled)}|{sum(bool(r['pooled_repeated_within_project']) for r in pooled)}|{len({r['candidate_id'] for r in pooled} & selected)}")
    structural = [r for r in rows_manifest if r["scope_decision"] == "no_inferential_interval_proposed"]
    nonbaseline = [r for r in rows_manifest if r["scope_decision"] == "excluded_nonbaseline"]
    L.exact(FAM_S, art_meta, "scope_decision.excluded.structural_ratios|nonbaseline_rows", "structural and nonbaseline exclusions; none selected",
            f"{excluded['structural_ratios']}|{excluded['nonbaseline_rows']}|0",
            f"{len(structural)}|{len(nonbaseline)}|{len({r['candidate_id'] for r in structural + nonbaseline} & selected)}")
    family = Counter((Path(by_id[i]["source_path"]).stem, by_id[i]["metric_family"], by_id[i]["row_key"].get("dimension", "")) for i in ids)
    L.exact(FAM_S, art_methods, "family counts", "methods: 9 named-coder sufficiency, 3 record sufficiency, 12 named-coder fit, 5 record fit, 4+4 Unclear",
            "9|3|12|5|4|4",
            "|".join(str(family[k]) for k in (("sufficiency_response_distribution", "named_coder_distribution", ""),
                                               ("sufficiency_record_distribution", "record_majority_or_subset", ""),
                                               ("taxonomy_fit_response_distribution", "named_coder_distribution", ""),
                                               ("taxonomy_fit_record_distribution", "record_majority_or_subset", ""),
                                               ("unclear_register_summary", "unclear_record_frequency", "Research Domains"),
                                               ("unclear_register_summary", "unclear_record_frequency", "Analytical Purposes"))))
    L.exact(FAM_S, art_meta, "reused_report_entries", "retained/reused entries", ["WSA0074", "WSA0082", "WSA0083"], sorted(meta["reused_report_entries"]))
    for cid in ("WSA0074", "WSA0082", "WSA0083"):
        L.exact(FAM_S, art_manifest, cid, "manifest decision for retained/reused entry", "already_exported", by_id[cid]["scope_decision"])

    # ---- unit and dependence ------------------------------------------------------------------------------
    counts, extra = reconstruct(P)
    L.exact(FAM_U, C.rel(C.BASE), "baseline records", "baseline records reconstructed", 150, extra["baseline_records"])
    for coder in C.CODERS:
        L.exact(FAM_U, C.rel(C.RAW), f"coder={coder}", "named-coder rows: one rating per baseline project (ratings|distinct projects)", "150|150",
                "|".join(str(x) for x in extra[f"responses_{coder}"]))
    L.add(FAM_U, art_manifest, "record_binary / individual_coder_binary", "observational unit of included rows is one indicator per sampled project",
          "manifest unit classes", "verified from raw joins: 150 projects, one indicator per project (record rows) or per project for one fixed coder",
          "no pooled repeated ratings in included rows", "VERIFIED", "M-WILSON-INFERENCE",
          note="Independence across projects follows from simple random sampling of records (protocol ¶52); interval refers to the fixed coder or panel, not coders in general")

    # ---- numerical ---------------------------------------------------------------------------------------
    z = z975()
    L.num(FAM_N, "analysis/validation/intervals.py", "Z_975", "repository z (recorded) vs 80-digit inverse normal at 0.975", meta["implementation"]["z"], z, C.TOL_Z)
    L.num(FAM_N, "(python statistics.NormalDist)", "inv_cdf(0.975)", "stdlib inverse normal vs 80-digit bisection", statistics.NormalDist().inv_cdf(0.975), z, C.TOL_Z)
    impl_sha = C.sha256(C.ROOT / "analysis/validation/intervals.py")
    max_diff = Decimal(0)
    for row in rows.to_dict("records"):
        cid = row["candidate_id"]
        item = by_id[cid]
        key = json.loads(row["source_key_json"])
        ident = f"{cid}; {Path(row['source_path']).name}; " + "; ".join(f"{k}={v}" for k, v in sorted(key.items()))
        found, src = source_row(row["source_path"], key)
        L.exact(FAM_L, row["source_path"], ident, "source key resolves to exactly one source row", 1, found)
        L.exact(FAM_L, row["source_path"], ident, "source SHA-256: supplement field | manifest | current file", "|".join([row["source_sha256"]] * 3),
                "|".join([row["source_sha256"], item["source_sha256"], C.sha256(C.ROOT / row["source_path"])]))
        L.exact(FAM_S, art_manifest, ident, "manifest decision / population / unit class / pooled flag",
                "candidate_for_later_authorised_wilson|baseline|" + row["observational_unit"] + "|False",
                f"{item['scope_decision']}|{item['population']}|{item['observational_unit_class']}|{item['pooled_repeated_within_project']}")
        L.exact(FAM_S, art, ident, "population/unit in supplement row are approved values", True,
                row["population"] == "baseline" and row["observational_unit"] in ("record_binary", "individual_coder_binary"))
        L.exact(FAM_C, art, ident, "count|denominator|proportion strings: supplement vs source CSV",
                f"{src['count']}|{src['denominator']}|{src['proportion']}",
                f"{row['original_numerator']}|{row['original_denominator']}|{row['original_proportion']}")
        L.exact(FAM_C, art_manifest, ident, "count|denominator|proportion strings: manifest vs source CSV",
                f"{src['count']}|{src['denominator']}|{src['proportion']}",
                f"{item['source_numerator']}|{item['source_denominator']}|{item['source_proportion']}")
        try:
            k, n = int(row["original_numerator"]), int(row["original_denominator"])
            valid = str(k) == row["original_numerator"] and str(n) == row["original_denominator"] and 0 <= k <= n and n > 0
        except ValueError:
            k = n = None
            valid = False
        L.exact(FAM_C, art, ident, "integer counts with 0 <= k <= n and n > 0 (zero denominator absent)", True, valid)
        if not valid:
            continue
        L.exact(FAM_C, art, ident, "exported proportion string equals repr(k/n): point estimate from exact counts", row["original_proportion"], repr(k / n))
        L.exact(FAM_C, art, ident, "validation_k_over_n | point_validation_absolute_difference", f"{repr(k / n)}|0.0",
                f"{row['validation_k_over_n']}|{row['point_validation_absolute_difference']}")
        rk, rn = counts[recon_key(row["source_path"], key)]
        L.exact(FAM_C, C.rel(C.RAW), ident, "numerator|denominator reconstructed from frozen raw export via POST-009/POST-019", f"{k}|{n}", f"{rk}|{rn}")
        lower, upper = wilson(k, n, z)
        for column, exact_value in (("ci_lower", lower), ("ci_upper", upper), ("raw_formula_lower", lower), ("raw_formula_upper", upper)):
            L.num(FAM_N, art, ident, f"{column} vs independent Wilson root (two-sided 95%, no continuity correction)", row[column], exact_value, C.TOL_WILSON)
            max_diff = max(max_diff, abs(Decimal(row[column]) - exact_value))
        lo_s, hi_s = float(row["ci_lower"]), float(row["ci_upper"])
        L.exact(FAM_N, art, ident, "0 <= lower <= k/n <= upper <= 1", True, 0.0 <= lo_s <= k / n <= hi_s <= 1.0)
        residual = max(score_residual(k, n, lower, z) if k > 0 else Decimal(0), score_residual(k, n, upper, z) if k < n else Decimal(0))
        L.add(FAM_N, art, ident, "independent bounds satisfy the Wilson score equation", "", f"{residual:.3e}", "residual < 1e-60",
              "VERIFIED" if residual < Decimal("1e-60") else "DISCREPANT")
        corrections = json.loads(row["boundary_correction"])
        if k == 0:
            L.exact(FAM_N, art, ident, "zero-success: exact lower root is 0 and stored ci_lower is '0.0'", "True|0.0", f"{lower == 0}|{row['ci_lower']}")
            L.exact(FAM_N, art, ident, "zero-success correction record (endpoint|raw|corrected)", "lower|1.734723475976807e-18|0.0",
                    "|".join(str(corrections[0][f]) for f in ("endpoint", "raw", "corrected")) if len(corrections) == 1 else repr(corrections))
            L.exact(FAM_N, art, ident, "raw residue equals 2**-59 (floating-point cancellation, not a mathematical bound)",
                    float(row["raw_formula_lower"]), 2.0 ** -59)
        else:
            L.exact(FAM_N, art, ident, "no boundary correction; stored bounds equal raw-formula strings", "[]|True",
                    f"{row['boundary_correction']}|{row['ci_lower'] == row['raw_formula_lower'] and row['ci_upper'] == row['raw_formula_upper']}")
        L.exact(FAM_N, art, ident, "method|confidence|alpha|two_sided|continuity_correction", "Wilson score|0.95|0.05|True|False",
                "|".join(row[f] for f in ("method", "confidence_level", "alpha", "two_sided", "continuity_correction")))
        L.exact(FAM_L, art, ident, "implementation SHA-256 and calculation timestamp", f"{impl_sha}|{meta['calculation_timestamp_utc']}",
                f"{row['implementation_sha256']}|{row['calculation_timestamp_utc']}")
    L.exact(FAM_N, art_meta, "boundary_corrections", "metadata lists exactly the two zero-success lower corrections",
            ["WSA0100:lower", "WSA0120:lower"], sorted(f"{c['candidate_id']}:{c['endpoint']}" for c in meta["boundary_corrections"]))
    L.exact(FAM_N, art, "all rows", "rows with k=0 | rows with k=n",
            "2|0", f"{sum(r['original_numerator'] == '0' for r in rows.to_dict('records'))}|{sum(r['original_numerator'] == r['original_denominator'] for r in rows.to_dict('records'))}")

    # ---- retained and reused intervals -------------------------------------------------------------------
    subset_path = "analysis/outputs_validation_scratch_20260824/sufficiency_subset_summary.csv"
    for cid, subset in (("WSA0082", "broad_register_usable"), ("WSA0083", "strict_register_sufficient")):
        _, src = source_row(subset_path, {"population": "baseline", "subset": subset})
        origin = reused["originating_intervals"][cid]
        existing = by_id[cid]["existing_interval"]
        ident = f"{cid}; sufficiency_subset_summary.csv; population=baseline; subset={subset}"
        L.exact(FAM_R, subset_path, ident, "retained bounds/method: source CSV == reused_intervals.json == manifest",
                f"{src['ci_lower']}|{src['ci_upper']}|{src['ci_method']}" * 1,
                f"{origin['lower']}|{origin['upper']}|{origin['method']}")
        L.exact(FAM_R, art_manifest, ident, "manifest existing_interval equals source", f"{src['ci_lower']}|{src['ci_upper']}|{src['ci_method']}",
                f"{existing['lower']}|{existing['upper']}|{existing['method']}")
        L.exact(FAM_R, subset_path, ident, "count|denominator|proportion: source vs reused_intervals.json",
                f"{src['count']}|{src['denominator']}|{src['proportion']}", f"{origin['numerator']}|{origin['denominator']}|{origin['proportion']}")
        rk, rn = counts[("sufficiency_subset_summary", ("subset", subset))]
        L.exact(FAM_R, C.rel(C.RAW), ident, "subset count|denominator reconstructed from raw export", f"{src['count']}|{src['denominator']}", f"{rk}|{rn}")
        lower, upper = wilson(int(src["count"]), int(src["denominator"]), z)
        L.num(FAM_R, subset_path, ident, "original ci_lower vs independent Wilson root", src["ci_lower"], lower, C.TOL_WILSON)
        L.num(FAM_R, subset_path, ident, "original ci_upper vs independent Wilson root", src["ci_upper"], upper, C.TOL_WILSON)
    L.exact(FAM_R, subset_path, "source CSV identity", "pre-existing Stage A subset file unchanged (canonical source record vs current)",
            canon["source_files"][subset_path]["sha256"], C.sha256(C.ROOT / subset_path))
    entry = next(e for e in reused["report_entries"] if e["candidate_id"] == "WSA0074")
    _, target = source_row("analysis/outputs_validation_scratch_20260824/sufficiency_record_distribution.csv", {"population": "baseline", "category": "Sufficient"})
    _, strict = source_row(subset_path, {"population": "baseline", "subset": "strict_register_sufficient"})
    ident = "WSA0074 <- WSA0083; sufficiency_record_distribution.csv category=Sufficient"
    L.exact(FAM_R, C.rel(C.WILSON / "reused_intervals.json"), ident, "target count|denominator|proportion equal source and origin strings",
            f"{target['count']}|{target['denominator']}|{target['proportion']}|{strict['count']}|{strict['denominator']}|{strict['proportion']}",
            f"{entry['target']['numerator']}|{entry['target']['denominator']}|{entry['target']['proportion']}|{entry['target']['numerator']}|{entry['target']['denominator']}|{entry['target']['proportion']}")
    L.exact(FAM_R, C.rel(C.WILSON / "reused_intervals.json"), ident, "reused bounds equal the original strict-sufficiency bounds",
            f"{strict['ci_lower']}|{strict['ci_upper']}", f"{entry['lower']}|{entry['upper']}")
    L.exact(FAM_R, C.rel(C.RAW), ident, "per-record estimand equivalence: majority 'Sufficient' vs >=2 Sufficient ratings (mismatching baseline records)", 0,
            extra["majority_sufficient_vs_strict_mismatch"],
            note="Same 150-record denominator (all three ratings valid); with three ratings a category reaching >=2 is necessarily the unique majority")
    lower, upper = wilson(92, 150, z)
    L.num(FAM_R, C.rel(C.WILSON / "reused_intervals.json"), ident, "reused lower vs independent Wilson root for 92/150", entry["lower"], lower, C.TOL_WILSON)
    L.num(FAM_R, C.rel(C.WILSON / "reused_intervals.json"), ident, "reused upper vs independent Wilson root for 92/150", entry["upper"], upper, C.TOL_WILSON)

    # ---- lineage and reproducibility ---------------------------------------------------------------------
    for name in ("wilson_intervals.csv", "reused_intervals.json", "methods_wilson_baseline.md"):
        L.exact(FAM_L, art_meta, f"files.{name}", "recorded output SHA-256|bytes equal current file",
                f"{meta['files'][name]['sha256']}|{meta['files'][name]['bytes']}", f"{C.sha256(C.WILSON / name)}|{(C.WILSON / name).stat().st_size}")
    L.exact(FAM_L, C.rel(C.CANON / "run_metadata.json"), "supplement.files.run_metadata.json", "canonical record of supplement metadata equals current",
            canon["supplement"]["files"]["run_metadata.json"]["sha256"], C.sha256(C.WILSON / "run_metadata.json"))
    for path, record in meta["source_files"].items():
        L.exact(FAM_L, art_meta, f"source_files.{path}", "recorded before|after|current SHA-256 identical",
                "|".join([record["sha256_before"]] * 3), f"{record['sha256_before']}|{record['sha256_after']}|{C.sha256(C.ROOT / path)}")
    deleted = {d["historical_directory"] + "/run_metadata.json": d["files"]["run_metadata.json"]["sha256"] for d in canon["housekeeping"]["deletion_inventory"]}
    for path, record in meta["inputs"].items():
        current = C.ROOT / path
        if current.exists():
            L.exact(FAM_L, art_meta, f"inputs.{path}", "recorded input SHA-256 equals current file", record["sha256_before"], C.sha256(current))
        else:
            L.add(FAM_L, art_meta, f"inputs.{path}", "recorded input still available for historical re-run", record["sha256_before"], "file absent",
                  "input present", "BLOCKED", "N-WILSON-HIST-REPRO",
                  note="Deleted by housekeeping; canonical deletion inventory SHA-256 " + ("matches" if deleted.get(path) == record["sha256_before"] else "does NOT match"))
    for path, record in meta["task_code"].items():
        historical = C.sha256_bytes(C.git("show", f"{WILSON_COMMIT}:{path}", binary=True))
        L.exact(FAM_L, path, f"task_code at {WILSON_COMMIT[:7]}", "recorded generator code SHA-256 equals the committed blob at the recorded HEAD",
                record["sha256"], historical)
        L.add(FAM_L, path, "task_code at HEAD", "current generator code identical to the historical run code", record["sha256"], C.sha256(C.ROOT / path),
              "identity (historical reproducibility with current code)", "VERIFIED" if record["sha256"] == C.sha256(C.ROOT / path) else "DISCREPANT",
              "N-WILSON-HIST-REPRO", note="Changed in commit 5559da3 (2026-09-08); historical version recoverable from git")
    impl_hist = C.sha256_bytes(C.git("show", f"{WILSON_COMMIT}:analysis/validation/intervals.py", binary=True))
    L.exact(FAM_L, "analysis/validation/intervals.py", "implementation", "recorded|historical-commit|current implementation SHA-256",
            "|".join([meta["implementation"]["sha256"]] * 3), f"{meta['implementation']['sha256']}|{impl_hist}|{impl_sha}")
    current_code = (C.ROOT / "analysis/scratch_coder_consolidation_followup/wilson_supplement.py").read_text()
    L.add(FAM_L, art_meta, "invocation", "recorded invocation is runnable with current generator code",
          " ".join(meta["invocation"][2:]), "current code requires --task-b-metadata" if "required=True" in current_code and "--task-b-metadata" in current_code else "no new required argument",
          "recorded invocation accepted by current code", "BLOCKED" if "--task-b-metadata" not in " ".join(meta["invocation"]) and "--task-b-metadata" in current_code else "VERIFIED",
          "N-WILSON-HIST-REPRO", note="Numerical results verified independently; this limits historical re-execution only")
    stage_a_meta = json.loads((C.STAGE_A / "run_metadata.json").read_text())
    dirty = stage_a_meta["analysis_code_commit_or_worktree_state"]["changed_paths_at_run"]
    L.exact(FAM_L, C.rel(C.STAGE_A / "run_metadata.json"), "changed_paths_at_run", "Wilson implementation file clean at Stage A run (original intervals)",
            False, any("analysis/validation/intervals.py" in p for p in dirty))
    L.exact(FAM_L, "analysis/validation/intervals.py", "git diff ac18315..dcf763b", "implementation unchanged between Stage A run HEAD and supplement HEAD", "",
            C.git("diff", "--stat", "ac183152ba192b2bc74e0e41e16ce4d699cc321c", WILSON_COMMIT, "--", "analysis/validation/intervals.py").strip())
    return {"z975": str(z)[:40], "max_abs_bound_difference": f"{max_diff:.3e}", "reconstructed_counts": len(counts)}
