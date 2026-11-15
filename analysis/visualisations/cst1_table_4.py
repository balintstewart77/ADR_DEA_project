"""Table 4: Fable 5 against the coder-majority set by human consensus state, random baseline (CST1; exploratory).

Reads CST1T001-T010 from ``analysis/consensus_state_exploratory/`` (addendum ``ADDENDUM_consensus_state.md``,
2026-09-18; exploratory, post-registration). Each input must match its committed version in git, allowing for
line endings, because the run metadata records no output hashes. Display rounding only: whole-number
percentages (H.10), two decimals for mean Jaccard, Unicode minus (H.9).

Rows are the four consensus states, defined from the three coders' sets alone. Where a substantive majority
exists (unanimous; majority with dissent), the table gives exact match and mean Jaccard with 95% percentile
intervals, and, for majority with dissent, how often Fable 5's set was a strict superset or subset of the
majority set. Where it does not (majority Unclear; no agreed label), it gives Fable 5's use of Unclear and how
many of its label assignments any coder also applied.

Numbered under the manuscript's table plan (Table 4 = consensus state). The pass-3 file
``table_4_agreement_with_majority_purposes`` is a different table (manuscript Supplementary Table S4); see
manuscript item 5.

Writes ``analysis/tables/table_4_consensus_state_baseline.{md,csv}`` and a copy in ``DEA_paper/tables/``.
Run from the repository root:  python -m analysis.visualisations.cst1_table_4
"""
from __future__ import annotations

import csv
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402

CST = REPO / "analysis/consensus_state_exploratory"
SLUG = "table_4_consensus_state_baseline"
OUT = REPO / "analysis/tables"
PAPER = REPO / "DEA_paper/tables"
TABLES = {"Research Domains": {"counts": "CST1T001", "S1": "CST1T002", "S2": "CST1T003", "S3": "CST1T004", "S4": "CST1T005"},
          "Analytical Purposes": {"counts": "CST1T006", "S1": "CST1T007", "S2": "CST1T008", "S3": "CST1T009", "S4": "CST1T010"}}
STATES = {"S1": "Unanimous substantive set", "S2": "Substantive majority with dissent",
          "S3": "Majority Unclear", "S4": "No agreed label"}


def committed_rows(table_id: str) -> list[dict]:
    rel = f"analysis/consensus_state_exploratory/{table_id}.csv"
    lf = (REPO / rel).read_bytes().replace(b"\r\n", b"\n")
    blob = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO, capture_output=True, check=True).stdout.replace(b"\r\n", b"\n")
    if lf != blob:
        raise SystemExit(f"{table_id} differs from its committed version")
    return list(csv.DictReader(lf.decode("utf-8").splitlines()))


def counts_of(cell: str) -> tuple[int, float]:
    """'12; 0.923077' -> (12, 0.923077)."""
    n, p = (x.strip() for x in cell.split(";"))
    return int(n), float(p)


def pct(value: float) -> str:
    return f"{round(value * 100 + 1e-9):.0f}"


def interval_pct(row: dict) -> str:
    return f"{pct(float(row['estimate']))}% ({pct(float(row['lower']))} to {pct(float(row['upper']))})"


def interval_dec(row: dict) -> str:
    return f"{float(row['estimate']):.2f} ({float(row['lower']):.2f} to {float(row['upper']):.2f})"


def build() -> tuple[str, list[list[str]], dict]:
    data = {d: {k: committed_rows(t) for k, t in ids.items()} for d, ids in TABLES.items()}
    cells, flat = {}, []
    for d, t in data.items():
        counts = {r["state"]: int(r["count"]) for r in t["counts"]}
        if sum(counts[s] for s in STATES) != 150 or counts.get("Total") != 150:
            raise SystemExit(f"{d}: state counts do not sum to 150")
        q = {s: {r["quantity"]: r for r in t[s]} for s in STATES}
        for s in STATES:
            if any(r["interval_status"] != "R" or int(r["valid_replicates"]) < 1800 for r in q[s].values()):
                raise SystemExit(f"{d} {s}: an interval is not reported or has too few valid replicates")
            if int(next(iter(q[s].values()))["state_n"]) != counts[s] and s in ("S1", "S2"):
                raise SystemExit(f"{d} {s}: state n differs from the state count")
        n2 = counts["S2"]
        sup, sub = counts_of(q["S2"]["set_rel_strict_superset"]["estimate"])[0], counts_of(q["S2"]["set_rel_strict_subset"]["estimate"])[0]
        s3_sub = counts_of(q["S3"]["model_substantive_proportion"]["estimate"])[0]
        s3_labels = {k: counts_of(q["S3"][f"support_{k}_of_3"]["estimate"])[0] for k in range(4)}
        s4_unclear = counts_of(q["S4"]["model_unclear"]["estimate"])[0]
        s4_labels = {k: counts_of(q["S4"][f"support_{k}_of_3"]["estimate"])[0] for k in range(4)}
        cells[d] = {
            "S1": (counts["S1"], f"Exact match {interval_pct(q['S1']['exact_match_proportion'])}; mean Jaccard {interval_dec(q['S1']['mean_jaccard'])}"),
            "S2": (n2, f"Exact match {interval_pct(q['S2']['exact_match_proportion'])}; mean Jaccard {interval_dec(q['S2']['mean_jaccard'])}; "
                       f"strict superset of the majority set {sup} ({pct(sup / n2)}%), strict subset {sub} ({pct(sub / n2)}%)"),
            "S3": (counts["S3"], f"Substantive label on {s3_sub} of {counts['S3']} records; {s3_labels[0]} of {sum(s3_labels.values())} "
                                 f"label assignments applied by no coder"),
            "S4": (counts["S4"], f"Unclear on {s4_unclear} of {counts['S4']} records; {s4_labels[1]} of {sum(s4_labels.values())} "
                                 f"label assignments applied by exactly one coder"),
        }
    head = ["Consensus state (coders only)", "Research Domains: records", "Research Domains: Fable 5",
            "Analytical Purposes: records", "Analytical Purposes: Fable 5"]
    body = []
    for s, label in STATES.items():
        row = [label] + [x for d in TABLES for x in (str(cells[d][s][0]), cells[d][s][1])]
        body.append(row)
        flat.append(row)
    return p3.html_table(head, body), [head] + flat, cells


def main() -> None:
    html, flat, _ = build()
    OUT.mkdir(parents=True, exist_ok=True)
    md_path, csv_path = OUT / f"{SLUG}.md", OUT / f"{SLUG}.csv"
    md_path.write_text(html, encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as h:
        csv.writer(h, lineterminator="\n").writerows(flat)
    banned = [f for p in (md_path, csv_path) for f in p3.banned_check_text(p.read_text(encoding="utf-8").splitlines(), p.name)]
    ascii_minus = [m.start() for p in (md_path, csv_path) for m in re.finditer(r"(?<![A-Za-z0-9])-(?=\d)", p.read_text(encoding="utf-8"))]
    if banned or ascii_minus:
        raise SystemExit(f"Table 4 wording or minus-sign check failed: {banned or ascii_minus[:5]}")
    PAPER.mkdir(parents=True, exist_ok=True)
    for path in (md_path, csv_path):
        shutil.copy2(path, PAPER / path.name)
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    print(f"Table 4 written to {OUT.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)} "
          f"(CST1 inputs match HEAD {head}); checks passed")


if __name__ == "__main__":
    main()
