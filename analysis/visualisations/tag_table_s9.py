"""Supplementary Table S9: the two binary tags in the random baseline.

(a) Fable 5 against the labelwise coder majority (at least two of three coders), from the Stage B tag diagnostics
    (``analysis/outputs_validation_scratch_stage_b_20260825/tag_diagnostics.csv``; S2T015, S2T016): the four cells,
    raw, positive and negative agreement, Cohen's kappa and Gwet's AC1, each with its 95% percentile bootstrap CI
    (2,000 record resamples, seed 20260714).
(b) Records by the number of coders who applied each tag, and how many of them Fable 5 tagged. Computed here from the
    Stage A panels. Post hoc: a descriptive count first made ad hoc on 25 November 2026 and scripted on 26 November.

Writes ``analysis/tables/supplementary_table_s9_tag_diagnostics.{md,csv}`` and a copy in ``DEA_paper/tables/``
(both gitignored). Run from the repository root:  python -m analysis.visualisations.tag_table_s9
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from analysis.scratch_coder_stage_a.panels import build_stage_a_data, dimension_panels  # noqa: E402

DIAG = REPO / "analysis/outputs_validation_scratch_stage_b_20260825/tag_diagnostics.csv"
SLUG = "supplementary_table_s9_tag_diagnostics"
OUT, PAPER = REPO / "analysis/tables", REPO / "DEA_paper/tables"
TAGS = ("COVID-19 & Pandemic", "Demographic disparities / equity")
EXPECTED = {"COVID-19 & Pandemic": (12, 1, 0, 137), "Demographic disparities / equity": (6, 13, 5, 126)}  # S2T016, S2T015
METRICS = (("raw_agreement", "Raw agreement"), ("positive_agreement", "Positive agreement"),
           ("negative_agreement", "Negative agreement"), ("cohen_kappa", "Cohen's κ"), ("gwet_ac1", "Gwet's AC1"))


def num(x: float) -> str:
    return f"{x:.2f}".replace("-", "−")


def main() -> None:
    rows = {r["tag"]: r for r in csv.DictReader(DIAG.open(encoding="utf-8")) if r["population"] == "baseline"}
    for tag, cells in EXPECTED.items():
        got = tuple(int(rows[tag][k]) for k in ("tp", "fp", "fn", "tn"))
        if got != cells:
            raise SystemExit(f"{tag}: cells {got} differ from S2T015/S2T016 {cells}")
        for m, _ in METRICS:
            if int(rows[tag][f"{m}_bootstrap_valid_n"]) != 2000:
                raise SystemExit(f"{tag} {m}: expected 2,000 valid resamples")

    data = build_stage_a_data()
    ids = frozenset(data.baseline_ids)
    votes = {}
    for tag in TAGS:
        c = Counter()
        for p in dimension_panels(data, ids, tag):
            k = sum(int(x) for x in (p.coder_a, p.coder_b, p.coder_c))
            c[(k, int(p.model))] += 1
        votes[tag] = c
        maj = sum(n for (k, _), n in c.items() if k >= 2)
        both = sum(n for (k, m), n in c.items() if k >= 2 and m)
        if (maj, both) != (EXPECTED[tag][0] + EXPECTED[tag][2], EXPECTED[tag][0]):
            raise SystemExit(f"{tag}: vote counts do not reconcile with the tag diagnostics")

    head_a = ["Tag", "Majority-positive", "Fable 5-positive", "Both", "Fable 5 only", "Majority only", "Neither",
              *(label for _, label in METRICS)]
    body_a = []
    for tag in TAGS:
        r = rows[tag]
        tp, fp, fn, tn = (int(r[k]) for k in ("tp", "fp", "fn", "tn"))
        body_a.append([tag, str(tp + fn), str(tp + fp), str(tp), str(fp), str(fn), str(tn),
                       *(f"{num(float(r[m]))} ({num(float(r[m + '_ci_lower']))} to {num(float(r[m + '_ci_upper']))})" for m, _ in METRICS)])
    head_b = ["Tag", "Coders applying the tag", "Records", "Tagged by Fable 5"]
    body_b = []
    for tag in TAGS:
        for k in (3, 2, 1, 0):
            n = votes[tag][(k, 0)] + votes[tag][(k, 1)]
            body_b.append([tag, str(k), str(n), str(votes[tag][(k, 1)])])

    caption = ("**Supplementary Table S9. The binary tags in the random baseline (n = 150).** (a) Fable 5 against the coder "
               "majority (the tag applied by at least two of three coders). Raw agreement, negative agreement and AC1 credit "
               "agreed absence and are high because few records carry either tag; positive agreement and κ are the more "
               "informative measures. 95% CIs are percentile bootstrap estimates from 2,000 record resamples. (b) Records "
               "by the number of coders who applied each tag, and how many of them Fable 5 tagged (post hoc descriptive count).")
    md = [caption, "", "**(a) Agreement with the coder majority**", "", "| " + " | ".join(head_a) + " |", "|" + "---|" * len(head_a)]
    md += ["| " + " | ".join(r) + " |" for r in body_a]
    md += ["", "**(b) Coder votes**", "", "| " + " | ".join(head_b) + " |", "|" + "---|" * len(head_b)]
    md += ["| " + " | ".join(r) + " |" for r in body_b]
    OUT.mkdir(parents=True, exist_ok=True); PAPER.mkdir(parents=True, exist_ok=True)
    (OUT / f"{SLUG}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with (OUT / f"{SLUG}.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h, lineterminator="\n")
        w.writerows([["panel", *head_a], *(["a", *r] for r in body_a)])
        w.writerows([["panel", *head_b], *(["b", *r] for r in body_b)])
    for suffix in (".md", ".csv"):
        shutil.copy2(OUT / f"{SLUG}{suffix}", PAPER / f"{SLUG}{suffix}")
    print(f"Supplementary Table S9 written to {OUT.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)}; checks passed")


if __name__ == "__main__":
    main()
