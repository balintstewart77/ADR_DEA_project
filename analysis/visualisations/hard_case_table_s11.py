"""Supplementary Table S11: the hard-case sample by selection stratum (post hoc diagnostic). Pass-4 log P4.54.

Reads, each checked against its committed version in git (allowing for line endings):

* ``analysis/outputs_validation_scratch_hard_case_strata_20260825/hard_case_stratum_replacement.csv`` — coder-panel
  alpha, Fable 5 replacement alphas and differences by 25-record stratum (post hoc diagnostic, 25 August 2026);
* ``analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv`` and ``replacement_delta_results.csv``
  — the same quantities for all 75 hard cases (Stage A; S3T007, S3T008).

Rows: for each dimension, all 75 hard cases, then the three strata. Display rounding only: three decimals, Unicode
minus. Interval for delta_min only: 95% percentile bootstrap from 2,000 record resamples, Stage A conventions. Writes ``analysis/tables/supplementary_table_s11_hard_case_strata.{md,csv}``
and a copy in ``DEA_paper/tables/`` (both gitignored).

Run from the repository root:  python -m analysis.visualisations.hard_case_table_s11
"""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402

STRATA_FILE = "analysis/outputs_validation_scratch_hard_case_strata_20260825/hard_case_stratum_replacement.csv"
PANEL_FILE = "analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv"
DELTA_FILE = "analysis/outputs_validation_scratch_20260824/replacement_delta_results.csv"
SLUG = "supplementary_table_s11_hard_case_strata"
OUT, PAPER = REPO / "analysis/tables", REPO / "DEA_paper/tables"
DIMENSIONS = ("Research Domains", "Analytical Purposes")
STRATA = (("domain_only", "Models disagreed on domains only"), ("purpose_only", "Models disagreed on purposes only"),
          ("both", "Models disagreed on both"))


def committed_rows(rel: str) -> list[dict]:
    lf = (REPO / rel).read_bytes().replace(b"\r\n", b"\n")
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, check=True).stdout.replace(b"\r\n", b"\n")
    if lf != blob:
        raise SystemExit(f"{rel} differs from its committed version")
    return list(csv.DictReader(lf.decode("utf-8").splitlines()))


def num(value: float, signed: bool = False) -> str:
    text = f"{value:+.3f}" if signed else f"{value:.3f}"
    return text.replace("-", "−")


def build() -> tuple[str, list[list[str]]]:
    strata = {(r["stratum"], r["dimension"]): r for r in committed_rows(STRATA_FILE)}
    panels = {(r["dimension"], r["panel"]): r for r in committed_rows(PANEL_FILE) if r["population"] == "hard_case"}
    deltas = {(r["dimension"], r["delta"]): r for r in committed_rows(DELTA_FILE) if r["population"] == "hard_case"}
    head = ["Dimension", "Records", "Coder panel α", "α, Fable 5 replacing C01", "α, replacing C02", "α, replacing C03",
            "δ_A", "δ_B", "δ_C", "δ_min (interval)"]
    body, flat = [], []
    for dim in DIMENSIONS:
        # all 75 hard cases (Stage A)
        alphas = [float(panels[(dim, k)]["point_estimate"]) for k in ("ABC", "LBC", "ALC", "ABL")]
        ds = [float(deltas[(dim, k)]["point_estimate"]) for k in ("delta_A", "delta_B", "delta_C")]
        dmin = deltas[(dim, "delta_min")]
        if int(panels[(dim, "ABC")]["n_records"]) != 75 or abs(min(ds) - float(dmin["point_estimate"])) > 1e-12:
            raise SystemExit(f"{dim}: Stage A hard-case rows do not reconcile")
        rows = [("All hard cases", 75, alphas, ds, (float(dmin["point_estimate"]), float(dmin["ci_lower"]), float(dmin["ci_upper"])))]
        n_strata = 0
        for key, label in STRATA:
            r = strata[(key, dim)]
            a = [float(r[k]) for k in ("human_alpha", "replace_a_alpha", "replace_b_alpha", "replace_c_alpha")]
            d = [float(r[k]) for k in ("delta_a", "delta_b", "delta_c")]
            if any(abs((a[i + 1] - a[0]) - d[i]) > 1e-12 for i in range(3)) or abs(min(d) - float(r["delta_min"])) > 1e-12:
                raise SystemExit(f"{key} {dim}: replacement differences do not reconcile with the alphas")
            if int(r["bootstrap_valid_n"]) < 1800:
                raise SystemExit(f"{key} {dim}: too few valid bootstrap draws")
            n_strata += int(r["n_records"])
            rows.append((label, int(r["n_records"]), a, d, (float(r["delta_min"]), float(r["delta_min_ci_lower"]), float(r["delta_min_ci_upper"]))))
        if n_strata != 75:
            raise SystemExit(f"{dim}: strata do not sum to 75 records")
        body.append([dim])
        for label, n, a, d, (point, low, high) in rows:
            row = [label, str(n), *(num(x) for x in a), *(num(x, True) for x in d),
                   f"{num(point, True)} ({num(low, True)} to {num(high, True)})"]
            body.append(row)
            flat.append([dim] + row)
    return p3.html_table(head, body), [head] + flat


def main() -> None:
    html, flat = build()
    OUT.mkdir(parents=True, exist_ok=True)
    md_path, csv_path = OUT / f"{SLUG}.md", OUT / f"{SLUG}.csv"
    md_path.write_text(html, encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerows(flat)
    texts = [p.read_text(encoding="utf-8") for p in (md_path, csv_path)]
    banned = [b for text, p in zip(texts, (md_path, csv_path)) for b in p3.banned_check_text(text.splitlines(), p.name)]
    ascii_minus = [m.start() for text in texts for m in re.finditer(r"(?<![A-Za-z0-9])-(?=\d)", text)]
    if banned or ascii_minus:
        raise SystemExit(f"S11 wording or minus-sign check failed: {banned or ascii_minus[:5]}")
    PAPER.mkdir(parents=True, exist_ok=True)
    for path in (md_path, csv_path):
        shutil.copy2(path, PAPER / path.name)
    print(f"Supplementary Table S11 written to {OUT.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)}; checks passed")


if __name__ == "__main__":
    main()
