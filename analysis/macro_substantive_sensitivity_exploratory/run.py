"""MSS1: macro precision, recall and F1 over substantive labels only (post hoc sensitivity; not preregistered).

Specification: SPEC_macro_substantive_sensitivity_2026-11-17.md (dated, written before any substantive-only value was
calculated). Implements pass-3 decision M.3. Reads only committed Stage B outputs; draws no new resamples, but reuses
Stage B's saved per-label replicate values (seed 20260714, 2,000 record-level resamples) so the substantive-only macro
uses exactly the resamples of the preregistered macro. A reproduction gate must pass before anything is written.

Results are written only to a gitignored folder under preregistration_restricted/; the repository holds code only.

Run from the repository root:  python -m analysis.macro_substantive_sensitivity_exploratory.run
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from analysis.scratch_coder_stage_b.bootstrap import interval
from analysis.scratch_coder_stage_b.config import ATTEMPTS, SEED

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_macro_substantive_sensitivity_2026-11-17.md"
STAGE_B = "analysis/outputs_validation_scratch_stage_b_20260825"
INPUTS = {name: f"{STAGE_B}/{name}" for name in (
    "per_label_model_performance.csv", "bootstrap_per_label_performance.csv",
    "macro_performance.csv", "bootstrap_macro_performance.csv")}
OUT_PARENT = ROOT / "preregistration_restricted"
PAPER_SOURCES = ROOT / "DEA_paper/sources"
DIMS = ("Research Domains", "Analytical Purposes")
METRICS = ("precision", "recall", "f1")
UNCLEAR = "Unclear from Register Entry"
TOL = 1e-12


def committed_text(rel: str) -> tuple[str, str]:
    """Return the working-tree text (LF) after checking it matches HEAD, and its SHA-256."""
    raw = (ROOT / rel).read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True, check=True).stdout.replace(b"\r\n", b"\n")
    if lf != blob:
        raise SystemExit(f"{rel} differs from its committed version")
    return lf.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def rows(text: str) -> list[dict]:
    return list(csv.DictReader(text.splitlines()))


def opt(cell: str) -> float | None:
    return None if cell == "" else float(cell)


def macro(labels: list[str], point: dict, reps: dict) -> dict:
    """Unweighted mean over labels, Stage B rules: a replicate is undefined if any label is undefined in it."""
    out = {"labels": labels}
    for m in METRICS:
        pts = [point[(lab, m)] for lab in labels]
        out[m] = None if any(v is None for v in pts) else float(np.mean(pts))
        series = []
        for r in range(1, ATTEMPTS + 1):
            xs = [reps[(lab, r, m)] for lab in labels]
            series.append(None if any(v is None for v in xs) else float(np.mean(xs)))
        out[m + "_replicates"] = series
        out[m + "_interval"] = interval(series, ATTEMPTS)
    return out


def close(a: float | None, b: float | None) -> bool:
    return (a is None and b is None) or (a is not None and b is not None and abs(a - b) <= TOL)


def main() -> None:
    texts, hashes = {}, {}
    for name, rel in INPUTS.items():
        texts[name], hashes[rel] = committed_text(rel)
    perf = rows(texts["per_label_model_performance.csv"])
    reps_rows = rows(texts["bootstrap_per_label_performance.csv"])
    pre = {r["dimension"]: r for r in rows(texts["macro_performance.csv"])}
    pre_reps = {(r["dimension"], int(r["replicate"])): r for r in rows(texts["bootstrap_macro_performance.csv"])}

    results, gate = {}, []
    for dim in DIMS:
        eligible = pre[dim]["eligible_labels"].split("; ")  # Stage B averaging order
        if len(eligible) != int(pre[dim]["eligible_label_n"]) or UNCLEAR not in eligible:
            raise SystemExit(f"{dim}: eligible membership is not as expected")
        point = {(r["label"], m): opt(r[m]) for r in perf if r["dimension"] == dim for m in METRICS}
        reps = {(r["label"], int(r["replicate"]), m): opt(r[m]) for r in reps_rows if r["dimension"] == dim for m in METRICS}
        missing = [lab for lab in eligible if (lab, 1, "precision") not in reps or (lab, "precision") not in point]
        if missing:
            raise SystemExit(f"{dim}: no per-label values for {missing}")

        # Reproduction gate: the preregistered macro from the same saved replicates.
        full = macro(eligible, point, reps)
        for m in METRICS:
            ok_point = close(full[m], opt(pre[dim][m]))
            ok_reps = all(close(full[m + "_replicates"][r - 1], opt(pre_reps[(dim, r)][m])) for r in range(1, ATTEMPTS + 1))
            iv = full[m + "_interval"]
            ok_iv = (close(iv["lower"], opt(pre[dim][m + "_ci_lower"])) and close(iv["upper"], opt(pre[dim][m + "_ci_upper"]))
                     and iv["valid"] == int(pre[dim][m + "_bootstrap_valid_n"]) and iv["invalid"] == int(pre[dim][m + "_bootstrap_invalid_n"]))
            gate.append({"dimension": dim, "metric": m, "point": ok_point, "replicates": ok_reps, "interval": ok_iv})
        results[dim] = {"preregistered": full, "substantive": macro([lab for lab in eligible if lab != UNCLEAR], point, reps)}

    failed = [g for g in gate if not all((g["point"], g["replicates"], g["interval"]))]
    if failed:
        raise SystemExit(f"Reproduction gate failed; nothing written: {failed}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = OUT_PARENT / f"macro_substantive_sensitivity_{stamp}"
    out.mkdir(parents=True)
    table = [["dimension", "version", "labels_averaged", "labels", "metric", "estimate", "ci_lower", "ci_upper",
              "valid_replicates", "invalid_replicates", "interval_reported"]]
    for dim in DIMS:
        for version in ("preregistered", "substantive"):
            res = results[dim][version]
            for m in METRICS:
                iv = res[m + "_interval"]
                table.append([dim, version, len(res["labels"]), "; ".join(res["labels"]), m, res[m], iv["lower"], iv["upper"],
                              iv["valid"], iv["invalid"], iv["reported"]])
    with (out / "MSS1T001.csv").open("w", newline="", encoding="utf-8") as h:
        csv.writer(h, lineterminator="\n").writerows(table)

    def fmt(x):
        return "" if x is None else f"{x:.4f}"

    lines = [
        "# MSS1: macro averages over substantive labels only — results",
        "",
        "Status: post hoc sensitivity analysis, exploratory, not preregistered; specified on 17 November 2026 after the "
        "preregistered per-label and macro results had been seen (SPEC_macro_substantive_sensitivity_2026-11-17.md; "
        "pass-3 M.3). The preregistered macro averages (S6T001, S6T002) remain primary.",
        "",
        f"Population: random baseline (n = 150). Reference: labelwise coder majority (not a truth set). Resamples: the "
        f"{ATTEMPTS:,} saved Stage B record-level resamples (seed {SEED}); 95% percentile intervals, Hyndman–Fan Type 7, "
        "reported only with at least 1,800 valid replicates.",
        "",
        "Reproduction gate: passed. Recomputing the preregistered macro from the saved per-label replicates reproduced "
        "every replicate value, point estimate, interval bound and valid/invalid count in Stage B's macro outputs "
        f"(tolerance {TOL}).",
        "",
        "## MSS1T001 — Macro precision, recall and F1: preregistered (all eligible labels) and substantive labels only",
        "",
        "| Dimension | Version | Labels averaged | Metric | Estimate | 95% CI lower | 95% CI upper | Valid / invalid replicates |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in table[1:]:
        dim, version, n, _, m, est, lo, hi, v, inv, _rep = row
        name = "Preregistered (Unclear included)" if version == "preregistered" else "Substantive labels only (post hoc)"
        lines.append(f"| {dim} | {name} | {n} | {m} | {fmt(est)} | {fmt(lo)} | {fmt(hi)} | {v} / {inv} |")
    lines += ["", "Substantive labels averaged:"]
    lines += [f"- {dim}: {'; '.join(results[dim]['substantive']['labels'])}." for dim in DIMS]
    lines += ["", "Inputs (each matched its committed version at HEAD):"]
    lines += [f"- `{rel}` (SHA-256 {sha})" for rel, sha in hashes.items()]
    md = out / "results_macro_substantive_sensitivity.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(HERE.relative_to(ROOT))], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.strip()
    meta = {"analysis": "MSS1", "status": "post hoc sensitivity, exploratory, not preregistered",
            "specification": SPEC.name, "specification_sha256": hashlib.sha256(SPEC.read_bytes()).hexdigest(),
            "run_utc": stamp, "git_HEAD": head, "analysis_code_uncommitted": bool(dirty),
            "inputs_sha256": hashes, "bootstrap_seed": SEED, "bootstrap_replicates": ATTEMPTS,
            "reproduction_gate": gate, "python": sys.version, "platform": platform.platform(),
            "numpy": np.__version__}
    (out / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    shutil.copy2(md, PAPER_SOURCES / md.name)
    print(md.read_text(encoding="utf-8"))
    print(f"Written to {out.relative_to(ROOT)}; results copied to {PAPER_SOURCES.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
