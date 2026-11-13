"""Supplementary Table S15: strict Sufficient subset against the full random baseline (post hoc; SSC1).

Reads three aggregate SSC1 tables from ``analysis/sufficient_subset_contrast_exploratory/`` (branch
``analysis/sufficient-subset-contrast``), each checked against the hash recorded in that analysis's run
metadata, and writes:

* S15a: the 16 strict-minus-full contrasts with their 95% percentile intervals (SSC1T002);
* S15b: abstention and substantive disagreement by pair family, subset against the remaining records (SSC1T005);
* S15c: each coder's Unclear rate by that coder's own sufficiency rating (SSC1T012).

Display rounding only: three decimals for α and δ, whole-number percentages (H.10), Unicode minus (H.9).
Writes ``analysis/tables/supplementary_table_s15_sufficient_subset_contrast.{md,csv}`` and a copy in
``DEA_paper/tables/``; both locations are gitignored.

Run from the repository root:  python -m analysis.visualisations.ssc1_table_s15
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402
import render_scratch_coder_pass4 as p4  # noqa: E402

SSC = REPO / "analysis/sufficient_subset_contrast_exploratory"
SLUG = "supplementary_table_s15_sufficient_subset_contrast"
OUT = REPO / "analysis/tables"
PAPER = REPO / "DEA_paper/tables"
DIMENSIONS = ("Research Domains", "Analytical Purposes")
QUANTITIES = {"alpha_ABC": "α_ABC (C01, C02, C03)", "alpha_LBC": "α_LBC (Fable 5 replaces C01)",
              "alpha_ALC": "α_ALC (Fable 5 replaces C02)", "alpha_ABL": "α_ABL (Fable 5 replaces C03)",
              "delta_A": "δ_A = α_LBC − α_ABC", "delta_B": "δ_B = α_ALC − α_ABC", "delta_C": "δ_C = α_ABL − α_ABC",
              "delta_min": "δ_min, least favourable of the three"}
FAMILIES = {"human-human": "Coder–coder", "model-human": "Fable 5–coder"}


def rows(name: str, metadata: dict) -> list[dict]:
    path = SSC / name
    # run.py wrote CRLF CSVs and hashed those bytes; git stores them as LF. Accept either line ending.
    lf = path.read_bytes().replace(b"\r\n", b"\n")
    if metadata["outputs"][name] not in {hashlib.sha256(d).hexdigest() for d in (lf, lf.replace(b"\n", b"\r\n"))}:
        raise SystemExit(f"{name} differs from the hash in the SSC1 run metadata")
    return list(csv.DictReader(path.open(encoding="utf-8")))


def num(value: float, places: int = 3, signed: bool = False) -> str:
    text = f"{value:+.{places}f}" if signed else f"{value:.{places}f}"
    return text.replace("-", "−")


def pct(k: int, n: int) -> str:
    return f"{k} ({p4.whole_percent_text(k, n)})" if n else "0"


def build() -> tuple[str, list[list[str]]]:
    metadata = json.loads((SSC / "run_metadata.json").read_text(encoding="utf-8"))
    t2, t5, t12 = (rows(n, metadata) for n in ("SSC1T002.csv", "SSC1T005.csv", "SSC1T012.csv"))
    flat, md = [], []

    # S15a
    by = {(r["dimension"], r["contrast"].split(":")[0]): r for r in t2}
    if len(by) != 16 or any(r["draws_valid"] != r["draws_attempted"] for r in t2):
        raise SystemExit("S15a: expected 16 contrasts, each with every draw valid")
    head = ["Quantity"] + [f"{d}: {c}" for d in DIMENSIONS for c in ("full baseline", "Sufficient subset", "change (95% interval)")]
    body = []
    for key, label in QUANTITIES.items():
        row = [label]
        for d in DIMENSIONS:
            r = by[(d, key)]
            row += [num(float(r["full_point"])), num(float(r["strict_point"])),
                    f"{num(float(r['contrast_point']), signed=True)} ({num(float(r['interval_lower_95']), signed=True)} to "
                    f"{num(float(r['interval_upper_95']), signed=True)})"]
        body.append(row)
        flat.append(["S15a"] + row)
    md += ["**Supplementary Table S15a. Strict Sufficient subset (n = 92) minus full random baseline (n = 150): "
           "α and replacement differences**", "", p3.html_table(head, body).rstrip("\n"), ""]

    # S15b
    fam = {(r["dimension"], r["population"], r["family"]): r for r in t5}
    head = ["Dimension", "Pair family", "Population", "Comparisons", "Both Unclear, n (%)", "One Unclear, other substantive, n (%)",
            "Different substantive sets, of comparisons where both classified"]
    body = []
    for d in DIMENSIONS:
        body.append([d])
        for f, fname in FAMILIES.items():
            for pop, plabel, records in (("sufficient", "Sufficient subset", 92), ("complement", "Remaining records", 58)):
                r = fam[(d, pop, f)]
                n = int(r["comparisons"])
                if n != 3 * records:
                    raise SystemExit(f"S15b: {d} {f} {pop} has {n} comparisons, expected {3 * records}")
                both = int(r["both_substantive_comparisons"])
                row = [fname, f"{plabel} ({records} records)", str(n), pct(int(r["both_unclear_only"]), n),
                       pct(int(r["exactly_one_unclear_only"]), n), f"{r['different_substantive']}/{both} ({p4.whole_percent_text(int(r['different_substantive']), both)})"]
                body.append(row)
                flat.append(["S15b", d] + row)
    md += ["**Supplementary Table S15b. Abstention and substantive disagreement by pair family**", "",
           p3.html_table(head, body).rstrip("\n"), ""]

    # S15c
    head = ["Dimension", "Coder", "Own rating Sufficient: records", "Unclear, n (%)", "Own rating not Sufficient: records", "Unclear, n (%)"]
    body = []
    for d in DIMENSIONS:
        body.append([d])
        for r in (x for x in t12 if x["dimension"] == d):
            s, ns = int(r["own_sufficient_records"]), int(r["own_not_sufficient_records"])
            if s + ns != 150:
                raise SystemExit(f"S15c: {d} {r['coder']} records do not sum to 150")
            row = [r["coder"], str(s), pct(int(r["unclear_only_when_own_sufficient"]), s), str(ns),
                   pct(int(r["unclear_only_when_own_not_sufficient"]), ns)]
            body.append(row)
            flat.append(["S15c", d] + row)
    md += ["**Supplementary Table S15c. Each coder's use of Unclear by that coder's own sufficiency rating, random baseline**", "",
           p3.html_table(head, body).rstrip("\n"), ""]
    return "\n".join(md), flat


def main() -> None:
    text, flat = build()
    OUT.mkdir(parents=True, exist_ok=True)
    md_path, csv_path = OUT / f"{SLUG}.md", OUT / f"{SLUG}.csv"
    md_path.write_text(text, encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h, lineterminator="\n")
        w.writerow(["panel", "row..."])
        w.writerows(flat)
    banned, _ = p4.file_checks([md_path, csv_path])
    ascii_minus = [m.start() for p in (md_path, csv_path) for m in re.finditer(r"(?<![A-Za-z0-9])-(?=\d)", p.read_text(encoding="utf-8"))]
    if banned or ascii_minus:
        raise SystemExit(f"S15 wording or minus-sign check failed: {banned or ascii_minus[:5]}")
    PAPER.mkdir(parents=True, exist_ok=True)
    for path in (md_path, csv_path):
        shutil.copy2(path, PAPER / path.name)
    print(f"Supplementary Table S15 written to {OUT.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)}; checks passed")


if __name__ == "__main__":
    main()
