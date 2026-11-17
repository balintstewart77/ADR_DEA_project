"""GHA1 figures: pairwise agreement matrices and the replacement comparison (PNG and SVG)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis/visualisations"))
import render_scratch_coder_pass3 as p3  # noqa: E402  (shared rcParams, minus-sign tick formatter)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

SOURCES = ("C01", "C02", "C03", "Fable 5", "GPT-5.5")
DIMS = ("Research Domains", "Analytical Purposes")
POPS = (("baseline", "Random baseline (n=150)"), ("hard_case", "Hard-case sample (n=75; diagnostic)"))
CODERS = ("C01", "C02", "C03")
FABLE, GPT = "#28658C", "#B5651D"


def save(fig, base: Path) -> list[str]:
    fig.savefig(base.with_suffix(".png"), dpi=300, facecolor="white", bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), facecolor="white", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    return [base.with_suffix(".png").name, base.with_suffix(".svg").name]


def matrices(out_dir: Path, pairwise: list[dict], metric: str, title: str, slug: str) -> list[str]:
    fig, axes = plt.subplots(2, 2, figsize=(p3.FIGURE_WIDTH, 6.4), constrained_layout=True)
    image = None
    for r, (pop, pop_label) in enumerate(POPS):
        for c, dim in enumerate(DIMS):
            ax = axes[r][c]
            m = np.full((5, 5), np.nan)
            for row in pairwise:
                if row["population"] == pop and row["dimension"] == dim and row["stratum"] == "all":
                    i, j = SOURCES.index(row["source_a"]), SOURCES.index(row["source_b"])
                    m[i, j] = m[j, i] = row[metric]
            image = ax.imshow(m, vmin=0, vmax=1, cmap="Blues")
            for i in range(5):
                for j in range(5):
                    if i != j:
                        ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=8,
                                color="white" if m[i, j] > 0.6 else "#222222")
            ax.set_xticks(range(5), SOURCES, rotation=45, ha="right", fontsize=8)
            ax.set_yticks(range(5), SOURCES, fontsize=8)
            ax.set_title(f"{dim}\n{pop_label}", fontsize=8.5)
            for edge in (2.5,):
                ax.axhline(edge, color="#666666", lw=0.8)
                ax.axvline(edge, color="#666666", lw=0.8)
    cbar = fig.colorbar(image, ax=axes, shrink=0.6, location="right")
    cbar.set_label(title, fontsize=8.5)
    return save(fig, out_dir / slug)


def replacement(out_dir: Path, rows: list[dict]) -> list[str]:
    lookup = {(r["population"], r["dimension"], r["statistic"]): r for r in rows}
    fig, axes = plt.subplots(2, 3, figsize=(p3.FIGURE_WIDTH, 5.2), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1.2, 1.2, 1.0]})
    for r, (pop, pop_label) in enumerate(POPS):
        for c, dim in enumerate(DIMS):
            ax = axes[r][c]
            human = lookup[(pop, dim, "alpha_ABC")]
            ax.axvspan(human["interval_lower_95"], human["interval_upper_95"], color="#DDDDDD", zorder=0)
            ax.axvline(human["point_estimate"], color="#333333", lw=0.9, zorder=1)
            for y, coder in enumerate(CODERS):
                for offset, tag, colour, marker in ((-0.15, "F", FABLE, "o"), (0.15, "G", GPT, "s")):
                    row = lookup[(pop, dim, f"{tag}_alpha_replacing_{coder}")]
                    if row["interval_reported"]:
                        ax.hlines(y + offset, row["interval_lower_95"], row["interval_upper_95"], color=colour, lw=1.3)
                    ax.scatter(row["point_estimate"], y + offset, color=colour, marker=marker, s=26, zorder=3, edgecolor="black", lw=0.5)
            ax.set_yticks(range(3), [f"replacing {c}" for c in CODERS], fontsize=8)
            ax.invert_yaxis()
            ax.set_xlim(0.0, 0.8)
            ax.set_title(f"{dim}\n{pop_label}", fontsize=8.5)
            ax.set_xlabel("Krippendorff’s α (MASI)", fontsize=8.5)
            p3.style_axis(ax)
        ax = axes[r][2]
        labels = []
        for y, (dim, coder) in enumerate((d, c) for d in DIMS for c in CODERS):
            row = lookup[(pop, dim, f"contrast_G_minus_F_replacing_{coder}")]
            if row["interval_reported"]:
                ax.hlines(y, row["interval_lower_95"], row["interval_upper_95"], color="#444444", lw=1.3)
            ax.scatter(row["point_estimate"], y, color="#444444", s=22, zorder=3)
            labels.append(f"{'Domains' if dim == DIMS[0] else 'Purposes'}: {coder}")
        ax.axvline(0, color="#333333", lw=0.8)
        ax.set_yticks(range(6), labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(-0.3, 0.3)
        ax.xaxis.set_major_formatter(FuncFormatter(p3.minus_tick))
        ax.set_title(f"GPT-5.5 minus Fable 5 panel α\n{pop_label}", fontsize=8.5)
        ax.set_xlabel("Paired contrast (same retained coders)", fontsize=8.5)
        p3.style_axis(ax)
    handles = [plt.Line2D([], [], color=FABLE, marker="o", lw=1.3, label="Fable 5 replaces the coder"),
               plt.Line2D([], [], color=GPT, marker="s", lw=1.3, label="GPT-5.5 replaces the coder"),
               plt.Line2D([], [], color="#333333", lw=0.9, label="All-human α (grey band: its interval)")]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    return save(fig, out_dir / "GHA1_figure_replacement_comparison")


def draw_all(out_dir: Path, pairwise: list[dict], rows: list[dict]) -> list[str]:
    files = matrices(out_dir, pairwise, "mean_jaccard", "Mean Jaccard similarity", "GHA1_figure_pairwise_mean_jaccard")
    files += matrices(out_dir, pairwise, "exact_set_proportion", "Exact-set agreement (proportion of records)", "GHA1_figure_pairwise_exact_set")
    files += replacement(out_dir, rows)
    return files
