"""Post hoc exploratory run: type of pairwise set disagreement by dimension, random baseline.

Specification: SPEC_disagreement_type_2026-11-20.md (written after an ad hoc count was seen). Not preregistered.
Aggregate outputs only, written outside tracked files; 95% percentile bootstrap intervals; no tests or p-values.

Run from the repository root (Windows: set PYTHONUTF8=1):
    python analysis/disagreement_type_exploratory/run.py
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.load import verify_authorities  # noqa: E402
from analysis.scratch_coder_stage_a.panels import build_stage_a_data, dimension_panels  # noqa: E402
from analysis.scratch_coder_stage_a.sufficiency import derive_sufficiency_subsets  # noqa: E402
from analysis.validation.bootstrap import percentile  # noqa: E402

HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_disagreement_type_2026-11-20.md"
OUT = ROOT / "preregistration_restricted" / "disagreement_type_exploratory"
TABLE_DIRS = (ROOT / "analysis" / "tables", ROOT / "DEA_paper" / "tables")
TABLE_SLUG = "supplementary_table_s2_disagreement_type"
SSC1T005 = ROOT / "analysis" / "sufficient_subset_contrast_exploratory" / "SSC1T005.csv"
STATUS = "post hoc exploratory, not preregistered; an ad hoc count was seen before the specification"

SEED = 20261120
DRAWS = 2000
QUANTILES = (0.025, 0.975)
UNCLEAR = "Unclear from Register Entry"
DIMENSIONS = ("Research Domains", "Analytical Purposes")
POPULATIONS = ("full", "sufficient", "complement")
POPULATION_LABEL = {"full": "Random baseline (n = 150)", "sufficient": "Sufficient entries (n = 92)",
                    "complement": "Other entries (n = 58)"}
FAMILIES = ("coder pairs", "Fable 5–coder pairs")
SSC1_FAMILY = {"coder pairs": "human-human", "Fable 5–coder pairs": "model-human"}
CATEGORIES = ("same", "unclear", "contains", "partial", "disjoint")
CATEGORY_LABEL = {"same": "Same set", "unclear": "Unclear against a label", "contains": "One set contains the other",
                  "partial": "Partial overlap", "disjoint": "No label shared"}
SUBSTANTIVE = ("contains", "partial", "disjoint")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def category(a: frozenset[str], b: frozenset[str]) -> str:
    if a == b:
        return "same"
    if UNCLEAR in a or UNCLEAR in b:
        return "unclear"
    if a < b or b < a:
        return "contains"
    return "partial" if a & b else "disjoint"


def record_counts(data, ids: frozenset[str]) -> dict:
    """Per dimension and family: record ids (sorted) and an array (records x categories) of pair counts,
    plus a count of one-against-one disjoint pairs."""
    out = {}
    for dim in DIMENSIONS:
        panels = dimension_panels(data, ids, dim)
        if len(panels) != len(ids):
            raise SystemExit(f"{dim}: {len(panels)} panels for {len(ids)} records")
        rows = {f: [] for f in FAMILIES}
        singles = Counter()
        rids = []
        for p in panels:
            coders = [p.coder_a, p.coder_b, p.coder_c]
            if any(c is None for c in coders) or p.model is None:
                raise SystemExit(f"{dim}: incomplete rater set")
            coders = [frozenset(c) for c in coders]
            model = frozenset(p.model)
            pairs = {"coder pairs": list(combinations(coders, 2)), "Fable 5–coder pairs": [(model, c) for c in coders]}
            for f, ps in pairs.items():
                c = Counter(category(a, b) for a, b in ps)
                rows[f].append([c[k] for k in CATEGORIES])
                singles[f] += sum(1 for a, b in ps if category(a, b) == "disjoint" and len(a) == len(b) == 1)
            rids.append(p.record_id)
        out[dim] = {"record_ids": rids, "counts": {f: np.array(rows[f], dtype=np.int64) for f in FAMILIES},
                    "one_against_one_disjoint": dict(singles)}
    return out


def shares(totals: np.ndarray) -> dict[str, float | None]:
    """totals: (..., 5) summed counts. Returns shares of all pairs and of substantive disagreements."""
    n = totals.sum(axis=-1)
    sub = totals[..., 2:].sum(axis=-1)
    res = {}
    for i, k in enumerate(CATEGORIES):
        res[f"{k}_of_pairs"] = (totals[..., i], n)
    for i, k in enumerate(SUBSTANTIVE, start=2):
        res[f"{k}_of_substantive"] = (totals[..., i], sub)
    return res


def main() -> None:
    if not all(a.matched for a in verify_authorities()):
        raise SystemExit("authority hash mismatch")
    data = build_stage_a_data()
    full = frozenset(data.baseline_ids)
    if len(full) != 150:
        raise SystemExit("baseline is not 150 records")
    strict = frozenset(derive_sufficiency_subsets(data)["strict"])
    if len(strict) != 92:
        raise SystemExit("strict subset is not 92 records")
    pops = {"full": full, "sufficient": strict, "complement": full - strict}

    base = record_counts(data, full)
    index = {dim: {rid: i for i, rid in enumerate(base[dim]["record_ids"])} for dim in DIMENSIONS}
    rng = np.random.default_rng(SEED)
    draws = {pop: rng.integers(0, len(ids), size=(DRAWS, len(ids))) for pop, ids in pops.items()}

    ssc1 = {(r["dimension"], r["population"], r["family"]): r for r in csv.DictReader(SSC1T005.open(encoding="utf-8"))}
    rows, checks = [], []
    for dim in DIMENSIONS:
        for pop, ids in pops.items():
            sel = np.array(sorted(index[dim][rid] for rid in ids))
            singles = record_counts(data, ids)[dim]["one_against_one_disjoint"] if pop != "full" else base[dim]["one_against_one_disjoint"]
            for fam in FAMILIES:
                mat = base[dim]["counts"][fam][sel]
                tot = mat.sum(axis=0)
                ref = ssc1[(dim, pop, SSC1_FAMILY[fam])]
                expect = {"pairs": int(ref["comparisons"]),
                          "same": int(ref["both_unclear_only"]) + int(ref["identical_substantive"]),
                          "unclear": int(ref["exactly_one_unclear_only"]), "substantive": int(ref["different_substantive"])}
                got = {"pairs": int(tot.sum()), "same": int(tot[0]), "unclear": int(tot[1]), "substantive": int(tot[2:].sum())}
                if got != expect:
                    raise SystemExit(f"SSC1T005 reconciliation failed: {dim} {pop} {fam}: {got} != {expect}")
                checks.append(f"{dim} | {pop} | {fam}: matches SSC1T005")
                boot = mat[draws[pop]].sum(axis=1)  # (DRAWS, 5)
                point, rep = shares(tot), shares(boot)
                for stat, (num, den) in point.items():
                    rnum, rden = rep[stat]
                    ok = rden > 0
                    vals = (rnum[ok] / rden[ok]).tolist()
                    rows.append({
                        "table_id": "DTY1T001", "dimension": dim, "population": pop, "family": fam, "statistic": stat,
                        "numerator": int(num), "denominator": int(den),
                        "estimate": (num / den) if den else "",
                        "ci_lower": percentile(vals, QUANTILES[0]) if vals else "",
                        "ci_upper": percentile(vals, QUANTILES[1]) if vals else "",
                        "defined_resamples": int(ok.sum()),
                        "one_against_one_disjoint_pairs": singles[fam] if stat.startswith("disjoint") else "",
                    })

    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (OUT / "DTY1T001.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    md = ["## DTY1T001", "", f"Type of pairwise set disagreement, random baseline. Status: {STATUS}. Pairs pooled within "
          "records (three per record; not independent). 95% percentile bootstrap CIs (record resamples).", "",
          "| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    md += ["| " + " | ".join(str(r[f]) for f in fields) + " |" for r in rows]
    (OUT / "DTY1T001.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    write_s20(rows)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    meta = {"run_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "status": STATUS,
            "spec": SPEC.name, "spec_sha256": sha256(SPEC), "script_sha256": sha256(Path(__file__)), "git_head": commit,
            "seed": SEED, "draws": DRAWS, "quantiles": QUANTILES, "quantile_method": "Hyndman-Fan Type 7",
            "ssc1t005_sha256": sha256(SSC1T005), "checks": checks, "python": platform.python_version(),
            "numpy": np.__version__, "outputs": {p.name: sha256(p) for p in sorted(OUT.glob("DTY1T001.*"))}}
    (OUT / "run_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"DTY1T001 written ({len(rows)} rows); {len(checks)} reconciliation checks passed")


def pct(x: float) -> str:
    return f"{round(100 * x):d}%"


def write_s20(rows: list[dict]) -> None:
    get = {(r["dimension"], r["population"], r["family"], r["statistic"]): r for r in rows}
    head = ["Dimension", "Comparison", "Pairs", *(CATEGORY_LABEL[k] for k in CATEGORIES),
            "Of substantive disagreements: one set contains the other", "Of substantive disagreements: no label shared"]
    body = []
    layout = [("full", "coder pairs"), ("full", "Fable 5–coder pairs"), ("sufficient", "coder pairs"), ("complement", "coder pairs")]
    for dim in DIMENSIONS:
        for pop, fam in layout:
            g = lambda s: get[(dim, pop, fam, s)]  # noqa: E731
            cells = [pct(g(f"{k}_of_pairs")["estimate"]) for k in CATEGORIES]
            for k in ("contains", "disjoint"):
                r = g(f"{k}_of_substantive")
                cells.append(f"{pct(r['estimate'])} ({pct(r['ci_lower'])} to {pct(r['ci_upper'])}; n = {r['denominator']})")
            label = f"{fam[0].upper()}{fam[1:]}, {POPULATION_LABEL[pop][0].lower()}{POPULATION_LABEL[pop][1:]}"
            body.append([dim, label, str(g("same_of_pairs")["denominator"]), *cells])
    caption = ("**Supplementary Table S2.** Type of difference between two raters' sets, random baseline (post hoc, "
               "exploratory). Each record contributes three pairs per comparison, which are not independent. "
               "Substantive disagreements are pairs in which both raters gave substantive labels and the sets differ. "
               "Sufficient entries are those at least two coders rated Sufficient. 95% CIs are percentile "
               "bootstrap estimates from 2,000 record resamples; n is the number of substantive disagreements.")
    for d in TABLE_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        lines = [caption, "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(r) + " |" for r in body]
        (d / f"{TABLE_SLUG}.md").write_text("\n".join(lines).replace("-0%", "0%") + "\n", encoding="utf-8")
        with (d / f"{TABLE_SLUG}.csv").open("w", newline="", encoding="utf-8") as h:
            csv.writer(h, lineterminator="\n").writerows([head, *body])


if __name__ == "__main__":
    main()
