"""Figure 4: register-sufficient subset minus full random baseline (post hoc; SSC1). Pass-4 log P4.32; Figure 4 from P4.37.

Reads SSC1T002 from ``analysis/sufficient_subset_contrast_exploratory/`` (branch
``analysis/sufficient-subset-contrast``), checked against the hash in that analysis's run metadata, and draws,
for Research Domains and Analytical Purposes, the strict-minus-full contrast for α_ABC, δ_A, δ_B, δ_C and δ_min
with its 95% percentile interval. Row labels carry the full-baseline and subset point estimates. Display
rounding only; no estimation.

Writes ``analysis/figures/figure_4_sufficient_subset_contrast.{svg,png}``, figure data and metadata in
``analysis/figure_data/``, a Figure 4 section in ``analysis/figures/draft_captions_pass4.md`` (after Figure 3),
and copies of the image files in ``DEA_paper/figures/``. The pass-4 renderer rewrites the captions file, so run
this after it.

Run from the repository root:  python -m analysis.visualisations.ssc1_figure_4
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
import render_scratch_coder_pass3 as p3  # noqa: E402  (sets the shared rcParams)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter  # noqa: E402

from figure_style import COLOURS  # noqa: E402

SSC = REPO / "analysis/sufficient_subset_contrast_exploratory"
SLUG = "figure_4_sufficient_subset_contrast"
FIGURES = REPO / "analysis/figures"
FIGURE_DATA = REPO / "analysis/figure_data"
PAPER = REPO / "DEA_paper/figures"
CAPTIONS = FIGURES / "draft_captions_pass4.md"
DIMENSIONS = ("Research Domains", "Analytical Purposes")
QUANTITIES = ("alpha_ABC", "delta_A", "delta_B", "delta_C", "delta_min")
LABELS = {"alpha_ABC": r"α$_{\mathrm{ABC}}$", **{q: p3.DELTA_LABELS[q] for q in ("delta_A", "delta_B", "delta_C", "delta_min")}}
X_LIMITS = (-0.10, 0.15)
COLOUR = COLOURS["strict"]
TITLE = "Change in reliability when the analysis is restricted to the register-sufficient subset"
CAPTION_BULLETS = [
    "Post hoc and exploratory, not preregistered: the SSC1 contrast was specified on 13 November 2026 after initial "
    "results had been seen [SSC1 specification and run metadata].",
    "Each point is the register-sufficient subset (n=92) minus the full random baseline (n=150); the subset is "
    "nested in the baseline and is the 92 records at least two coders rated Sufficient (Figure 3) [SSC1T002 cells].",
    "Rows: α for the all-human panel (ABC) and the three replacement differences δₐ, δᵦ and δ꜀ with δₘᵢₙ, defined as in "
    "Figure 2. The two numbers beside each row label are the full-baseline and subset point estimates. The replacement "
    "panels’ α (LBC, ALC, ABL) and all 16 contrasts are in Supplementary Table S15a [SSC1T002 point cells].",
    "Intervals are 95% percentile intervals from 10,000 paired record resamples (seed 20261113), as the SSC1 "
    "specification fixes; they imply no confidence level for the Figure 2 intervals [SSC1T002 interval cells].",
    "δₘᵢₙ equals δᵦ in both populations and dimensions, so its point contrast equals δᵦ’s; its interval is estimated "
    "separately, as the least favourable of the three in each resample [SSC1T002 cells].",
    "The subset is defined by the coders’ own ratings, and each coder’s use of Unclear from Register Entry depends on "
    "that coder’s rating (Supplementary Table S15c), so the contrast is not independent of coder behaviour. It does not "
    "show that sufficiency raised agreement.",
    "Statements refer to point estimates and to each interval on its own; intervals are not compared by overlap.",
]


def committed_rows(metadata: dict) -> list[dict]:
    name = "SSC1T002.csv"
    lf = (SSC / name).read_bytes().replace(b"\r\n", b"\n")
    # run.py wrote CRLF CSVs and hashed those bytes; git stores them as LF. Accept either line ending.
    if metadata["outputs"][name] not in {hashlib.sha256(b).hexdigest() for b in (lf, lf.replace(b"\n", b"\r\n"))}:
        raise SystemExit(f"{name} differs from the hash in the SSC1 run metadata")
    return list(csv.DictReader(lf.decode("utf-8").splitlines()))


def two(value: str) -> str:
    return p3.half_up(value, 2)


def select(rows: list[dict]) -> dict[tuple[str, str], dict]:
    keyed = {(r["dimension"], r["contrast"].split(":")[0]): r for r in rows}
    chosen = {(d, q): keyed[(d, q)] for d in DIMENSIONS for q in QUANTITIES}
    for (d, q), r in chosen.items():
        if r["draws_valid"] != r["draws_attempted"] or r["interval_reported"] != "True":
            raise SystemExit(f"{d} {q}: interval not reported for every draw")
        for value in (r["contrast_point"], r["interval_lower_95"], r["interval_upper_95"]):
            if not X_LIMITS[0] < float(value) < X_LIMITS[1]:
                raise SystemExit(f"{d} {q}: {value} falls outside the axis {X_LIMITS}")
    for d in DIMENSIONS:  # δ_min equals δ_B in both populations (caption bullet 5)
        for column in ("full_point", "strict_point"):
            if chosen[(d, "delta_min")][column] != chosen[(d, "delta_B")][column]:
                raise SystemExit(f"{d}: δ_min {column} differs from δ_B")
    return chosen


def draw(chosen: dict) -> tuple[dict, list[dict]]:
    fig, axes = plt.subplots(len(DIMENSIONS), 1, figsize=(p3.FIGURE_WIDTH, 4.1), constrained_layout=True,
                             gridspec_kw={"hspace": 0.12})
    plotted = []
    for ax, dimension in zip(axes, DIMENSIONS):
        labels = []
        for y, quantity in enumerate(QUANTITIES):
            r = chosen[(dimension, quantity)]
            row = {"parsed_value": r["contrast_point"], "parsed_interval_lower": r["interval_lower_95"],
                   "parsed_interval_upper": r["interval_upper_95"], "interval_status": "R"}
            marker = "*" if quantity == "delta_min" else "o"
            record = p3.draw_interval(ax, y, row, COLOUR, marker, False, p3.STAR_SIZE if marker == "*" else None)
            labels.append(f"{LABELS[quantity]}   {two(r['full_point'])} → {two(r['strict_point'])}")
            plotted.append({"dimension": dimension, "quantity": quantity, "y": y, "x": record["x"],
                            "lower": record["lower"], "upper": record["upper"]})
        ax.set_yticks(range(len(QUANTITIES)), labels)
        ax.tick_params(axis="y", labelsize=9.5)
        ax.set_ylim(len(QUANTITIES) - 0.4, -0.6)
        ax.axhline(0.5, color="#BDBDBD", linewidth=0.6, zorder=1)
        ax.axvline(0, color="#333333", linewidth=0.8, zorder=1)
        ax.set_xlim(X_LIMITS)
        ax.xaxis.set_major_locator(FixedLocator([-0.10, -0.05, 0, 0.05, 0.10, 0.15]))
        ax.xaxis.set_major_formatter(FuncFormatter(p3.minus_tick))
        p3.style_axis(ax)
        ax.set_ylabel(dimension, fontweight="bold", rotation=0, ha="right", va="center", labelpad=4)
    # Header over the value column of the row labels (legibility change after the first render, P4.32)
    axes[0].text(-0.012, 1.03, "Full baseline → subset", transform=axes[0].transAxes, ha="right", va="bottom",
                 fontsize=8.5, color="0.25")
    axes[-1].set_xlabel("Change from full baseline (n = 150) to register-sufficient subset (n = 92),\nwith 95% interval")
    return p3.save_figure(fig, FIGURES / SLUG, "Figure 4"), plotted


def update_captions(bullets: list[str]) -> None:
    text = CAPTIONS.read_text(encoding="utf-8")
    section = "\n".join(["## Figure 4", "", f"**Figure 4. {TITLE}.**", "", "Legend content checklist:", "",
                         *(f"- {b}" for b in bullets), "", ""])
    text = re.sub(r"## Figure 4\n.*?(?=\n## )\n", "", text, flags=re.S)
    marker = "## Figure 5\n"
    if text.count(marker) != 1:
        raise SystemExit("draft_captions_pass4.md: expected exactly one Figure 5 section")
    CAPTIONS.write_text(text.replace(marker, section + marker), encoding="utf-8")


def main() -> None:
    metadata = json.loads((SSC / "run_metadata.json").read_text(encoding="utf-8"))
    chosen = select(committed_rows(metadata))
    metrics, plotted = draw(chosen)
    rendered = metrics["rendered_text"]
    banned = p3.banned_check_text(rendered + CAPTION_BULLETS + [TITLE], "Figure 4")
    ascii_minus = [t for t in rendered + CAPTION_BULLETS if re.search(r"(?<![A-Za-z0-9])-(?=\d)", t)]
    if banned or ascii_minus or metrics["font_status"] != "PASS" or metrics["edge_status"] != "PASS":
        raise SystemExit(f"Figure 4 checks failed: banned={banned} minus={ascii_minus} font={metrics['font_status']} "
                         f"edges={metrics['edge_failures']}")
    for p in plotted:  # display check: every row label's values match SSC1T002 to two decimals
        r = chosen[(p["dimension"], p["quantity"])]
        if f"{two(r['full_point'])} → {two(r['strict_point'])}" not in " ".join(rendered):
            raise SystemExit(f"{p['dimension']} {p['quantity']}: row label does not match SSC1T002")

    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    columns = ("dimension", "contrast", "full_point", "strict_point", "contrast_point", "interval_lower_95",
               "interval_upper_95", "interval_method", "draws_attempted", "draws_valid", "seed", "status")
    with (FIGURE_DATA / f"{SLUG}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows([chosen[(d, q)][c] for c in columns] for d in DIMENSIONS for q in QUANTITIES)
    (FIGURE_DATA / f"{SLUG}_metadata.json").write_text(json.dumps({
        "deliverable": "Figure 4", "decision_log": "pass-4 P4.32, P4.34 and P4.37 (16 November 2026)",
        "input": {"path": "analysis/sufficient_subset_contrast_exploratory/SSC1T002.csv",
                  "sha256_in_run_metadata": metadata["outputs"]["SSC1T002.csv"]},
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "matplotlib_version": matplotlib.__version__, "python_version": sys.version,
        "checks": {"font_status": metrics["font_status"], "minimum_effective_pt": metrics["minimum_effective_pt"],
                   "edge_status": metrics["edge_status"], "banned_text": "PASS", "minus_sign": "PASS",
                   "axis_containment": "PASS", "row_labels_match": "PASS", "delta_min_equals_delta_B": "PASS"},
        "plotted": plotted,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    update_captions(CAPTION_BULLETS)
    PAPER.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".svg"):
        shutil.copy2(FIGURES / f"{SLUG}{suffix}", PAPER / f"{SLUG}{suffix}")
    print(f"Figure 4 written to {FIGURES.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)}; "
          f"minimum {metrics['minimum_effective_pt']:.2f} pt; checks passed")


if __name__ == "__main__":
    main()
