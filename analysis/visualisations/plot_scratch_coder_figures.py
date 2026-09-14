"""Plot scratch-coder paper figures using only extracted figure-data files.

The script has no path or import dependency on canonical analytical results.
It can be copied with the ``scratch_coder_figure_*.csv/json`` files and rerun
for presentation-only revisions.
"""
from __future__ import annotations

import argparse
import csv
import json
import textwrap
from collections import defaultdict
from pathlib import Path


def load_figure(data_dir: Path, figure_id: str):
    with (data_dir / f"scratch_coder_{figure_id}.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    metadata = json.loads((data_dir / f"scratch_coder_{figure_id}_metadata.json").read_text())
    return rows, metadata


def f(value: str):
    return float(value) if value not in ("", None) else None


def number(value: str):
    return int(float(value)) if value not in ("", None) else None


def theme():
    # The figures are rendered non-interactively, including in the isolated
    # rerun environment; avoid the macOS GUI backend in headless sessions.
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    return plt.rc_context({
        "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
        "font.size": 8.5, "axes.titlesize": 10, "axes.labelsize": 9, "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.7, "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })


def style_axis(ax):
    ax.grid(axis="x", color="#D8DDE3", linewidth=.55, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, color="#65717C")


def caption(fig, text: str, *, y=0.035, width=155):
    fig.text(.5, y, textwrap.fill(text, width), ha="center", va="bottom", fontsize=7.1, color="#38434D")


def save(fig, out_dir: Path, figure_id: str):
    import matplotlib.pyplot as plt
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"scratch_coder_{figure_id}.svg")
    fig.savefig(out_dir / f"scratch_coder_{figure_id}.png", dpi=320)
    plt.close(fig)


DIM_ORDER = ["Research Domains", "Analytical Purposes", "COVID-19 tag", "Demographic disparities / equity tag"]
PANEL_ORDER = ["alpha ABC", "alpha LBC", "alpha ALC", "alpha ABL"]
DELTA_ORDER = ["delta_A", "delta_B", "delta_C", "delta_min"]
PANEL_LABELS = {"alpha ABC": "ABC", "alpha LBC": "LBC", "alpha ALC": "ALC", "alpha ABL": "ABL"}
DELTA_LABELS = {"delta_A": "δ_A", "delta_B": "δ_B", "delta_C": "δ_C", "delta_min": "δ_min"}


def interval(ax, x, row, color="#1F4E79", *, marker="o", filled=True, zorder=3):
    value = f(row["plot_value"])
    if value is None or row["estimate_status"] not in {"R", "reported"}:
        return
    lo, hi = f(row["interval_lower"]), f(row["interval_upper"])
    if row["interval_status"] == "R" and lo is not None and hi is not None:
        ax.errorbar(value, x, xerr=[[value - lo], [hi - value]], fmt="none", color=color, lw=1.0, capsize=2, zorder=zorder)
    ax.plot(value, x, marker=marker, markersize=5.0, color=color,
            markerfacecolor=color if filled else "white", markeredgewidth=1.0, zorder=zorder + .1)


def plot_replacement_grid(rows, metadata, out_dir, figure_id):
    """Figures 1 and 2: separate alpha and delta axes, one row per dimension/population."""
    import matplotlib.pyplot as plt
    shown = [r for r in rows if r["role"] == "plotted"]
    groups = []
    if figure_id == "figure_2":
        for pop in ["baseline", "baseline_strict_sufficient"]:
            for dim in ["Research Domains", "Analytical Purposes"]:
                groups.append((pop, dim))
    else:
        groups = [("baseline", dim) for dim in DIM_ORDER]
    fig, axes = plt.subplots(len(groups), 2, figsize=(7.35, 1.45 * len(groups) + 1.55), squeeze=False)
    alpha_vals = [f(r["plot_value"]) for r in shown if r["series"] == "alpha" and f(r["plot_value"]) is not None]
    delta_vals = [f(r["plot_value"]) for r in shown if r["series"] == "delta" and f(r["plot_value"]) is not None]
    for row_index, (population, dimension) in enumerate(groups):
        subset = [r for r in shown if r["population"] == population and r["dimension"] == dimension]
        label = dimension + (" — baseline (n=150)" if population == "baseline" else " — strict sufficient (n=92)")
        for col, (series, order, labels) in enumerate([( "alpha", PANEL_ORDER, PANEL_LABELS), ("delta", DELTA_ORDER, DELTA_LABELS)]):
            ax = axes[row_index, col]
            selected = {r["quantity"]: r for r in subset if r["series"] == series}
            for y, quantity in enumerate(order):
                interval(ax, y, selected.get(quantity, {}), color="#1F4E79" if quantity != "delta_min" else "#9C3D2E", marker="D" if quantity == "delta_min" else "o", filled=quantity != "delta_min") if quantity in selected else None
            ax.set_yticks(range(len(order)), [labels[q] for q in order])
            ax.set_ylim(len(order) - .45, -.55)
            style_axis(ax)
            if series == "delta":
                ax.axvline(0, color="#48545E", lw=.8, ls="--", zorder=1)
                ax.set_xlabel("Replacement difference, δ" if row_index == len(groups)-1 else "")
            else:
                ax.set_xlabel("Krippendorff’s α" if row_index == len(groups)-1 else "")
            ax.set_title(label if col == 0 else "", loc="left", fontweight="semibold")
    for col, values in enumerate([alpha_vals, delta_vals]):
        lo, hi = min(values), max(values)
        padding = max(.05, (hi - lo) * .16)
        for ax in axes[:, col]: ax.set_xlim(lo-padding, hi+padding)
    fig.text(.5, .992, "Interval bars: source-exported percentile-bootstrap intervals; confidence level unresolved", ha="center", va="top", fontsize=7.2, color="#38434D")
    caption(fig, metadata["caption"], width=110)
    fig.subplots_adjust(left=.16, right=.98, top=.93, bottom=.23, hspace=.65, wspace=.35)
    save(fig, out_dir, figure_id)


def plot_figure_3(rows, metadata, out_dir):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    plotted = [r for r in rows if r["role"] == "plotted" and r["human_majority_positive_n"] and r["model_positive_n"]]
    dimensions = ["Research Domains", "Analytical Purposes"]
    styles = {"STANDARD": ("s", "#1F4E79", True), "LOW SUPPORT": ("o", "#9C3D2E", False), "RARE": ("^", "#3C6E71", False)}
    fig, axes = plt.subplots(1, 2, figsize=(7.35, 4.35))
    for ax, dimension in zip(axes, dimensions):
        subset = [r for r in plotted if r["dimension"] == dimension]
        maximum = max(max(number(r["human_majority_positive_n"]), number(r["model_positive_n"])) for r in subset)
        limit = max(5, maximum + max(2, round(maximum*.08)))
        for row in subset:
            marker, color, filled = styles.get(row["support_band"], ("o", "#333333", False))
            ax.plot(number(row["human_majority_positive_n"]), number(row["model_positive_n"]), marker=marker, markersize=6, color=color, markerfacecolor=color if filled else "white", markeredgewidth=1.1, zorder=3)
        # Annotation ranking is the only permitted count difference calculation.
        ranked = sorted(subset, key=lambda r: abs(number(r["model_positive_n"]) - number(r["human_majority_positive_n"])), reverse=True)
        threshold = abs(number(ranked[min(2, len(ranked)-1)]["model_positive_n"]) - number(ranked[min(2, len(ranked)-1)]["human_majority_positive_n"]))
        annotate = [r for r in ranked if abs(number(r["model_positive_n"]) - number(r["human_majority_positive_n"])) >= threshold]
        annotate += [r for r in subset if r["label"] == "Unclear from Register Entry" and r not in annotate]
        for index, row in enumerate(annotate):
            label = row["label"].replace(" / ", "/").replace("Unclear from Register Entry", "Unclear")
            x = number(row["human_majority_positive_n"])
            ax.annotate(label, (x, number(row["model_positive_n"])), xytext=(-4 if x > limit*.55 else 4, 4 + (index % 3)*7), textcoords="offset points", ha="right" if x > limit*.55 else "left", fontsize=6.3, color="#202A33")
        ax.plot([0, limit], [0, limit], color="#65717C", ls="--", lw=.8, zorder=1)
        ax.set(xlim=(0, limit), ylim=(0, limit), aspect="equal", title=dimension)
        ax.set_xlabel("Human-majority-positive record count")
        ax.set_ylabel("Model-positive record count")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6)); ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        ax.grid(color="#D8DDE3", linewidth=.55, zorder=0); ax.set_axisbelow(True)
    handles = [axes[0].plot([], [], marker=s[0], color=s[1], markerfacecolor=s[1] if s[2] else "white", ls="")[0] for s in styles.values()]
    fig.legend(handles, list(styles), loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(.5, .145), fontsize=7.4)
    caption(fig, metadata["caption"], width=110)
    fig.subplots_adjust(left=.1, right=.985, top=.9, bottom=.28, wspace=.28)
    save(fig, out_dir, "figure_3")


def plot_figure_4(rows, metadata, out_dir):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    plotted = [r for r in rows if r["role"] == "plotted" and r["performance_metrics_reportable"] == "True"]
    excluded = [r for r in rows if r["role"] == "caption"]
    fig, axes = plt.subplots(1, 2, figsize=(7.35, 5.25))
    for ax, dimension in zip(axes, ["Research Domains", "Analytical Purposes"]):
        subset = [r for r in plotted if r["dimension"] == dimension]
        labels = [r["label"] for r in subset]
        y = list(range(len(labels)))
        fp = [number(r["fp"]) for r in subset]; fn = [number(r["fn"]) for r in subset]
        ax.barh([v-.18 for v in y], fp, .34, color="#1F4E79", label="FP", zorder=3)
        ax.barh([v+.18 for v in y], fn, .34, color="#B65445", hatch="//", label="FN", zorder=3)
        ax.set_yticks(y, [textwrap.fill(v, 25) for v in labels]); ax.invert_yaxis(); ax.set_title(dimension)
        ax.set_xlabel("FP/FN record count")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6)); style_axis(ax)
    excl_text = "; ".join(f"{r['dimension']}: {r['label']} (FP={r['fp_string'] or 'unavailable'}, FN={r['fn_string'] or 'unavailable'})" for r in excluded)
    axes[0].text(.98, .98, "FP: solid blue\nFN: hatched red", transform=axes[0].transAxes, ha="right", va="top", fontsize=7.1, color="#38434D", bbox={"facecolor":"white", "edgecolor":"#BFC7CE", "pad":2.5})
    caption(fig, metadata["caption"] + " Excluded labels: " + excl_text + ".", width=112)
    fig.subplots_adjust(left=.2, right=.985, top=.9, bottom=.32, wspace=.55)
    save(fig, out_dir, "figure_4")


def plot_figure_5(rows, metadata, out_dir):
    import matplotlib.pyplot as plt
    dimensions = []
    for r in rows:
        if r["dimension"] not in dimensions: dimensions.append(r["dimension"])
    relations = ["containment", "overlap", "disjoint"]
    fig, axes = plt.subplots(1, len(dimensions), figsize=(8.7, 4.2), sharey=True)
    for ax, dimension in zip(axes, dimensions):
        subset = [r for r in rows if r["dimension"] == dimension and r["role"] == "plotted"]
        families = ["human_human", "model_human"]
        width=.34
        handles=[]
        denoms=[]
        for i, family in enumerate(families):
            family_rows={r["relation"]:r for r in subset if r["pair_family"] == family}
            values=[f(family_rows[r]["plot_value"]) if r in family_rows else None for r in relations]
            denoms.append(f"{'human–human' if family=='human_human' else 'model–human'} n={family_rows[relations[0]]['eligible_pairs']} pairs; empty-set involved={family_rows[relations[0]]['empty_set_pairs']}" if relations[0] in family_rows else "")
            bar=ax.bar([x+(i-.5)*width for x in range(3)], [v if v is not None else 0 for v in values], width, color="#1F4E79" if i == 0 else "#B65445", hatch="" if i == 0 else "//", label="Human–human" if i == 0 else "Model–human", zorder=3)
            handles.append(bar)
            for x, value in enumerate(values):
                if value is None: ax.text(x+(i-.5)*width, .02, "NA", ha="center", fontsize=7)
        ax.set_xticks(range(3), [x.capitalize() for x in relations]); ax.set_ylim(0,1.04); ax.set_title(textwrap.fill(dimension, 18)); ax.set_xlabel("\n".join(denoms), fontsize=6.5)
        ax.grid(axis="y", color="#D8DDE3", linewidth=.55, zorder=0); ax.set_axisbelow(True)
    axes[0].set_ylabel("Proportion of non-identical, non-empty pairs")
    axes[0].legend([h[0] for h in handles], ["Human–human", "Model–human"], loc="upper left", frameon=True, fontsize=6.8)
    caption(fig, metadata["caption"] + " Source rows marked not_applicable are visibly unavailable (NA), never shown as 0.", width=130)
    fig.subplots_adjust(left=.085,right=.99,top=.88,bottom=.31,wspace=.22)
    save(fig, out_dir, "figure_5")


def plot_figure_6(rows, metadata, out_dir):
    import matplotlib.pyplot as plt
    plotted=[r for r in rows if r["role"] == "plotted"]
    fig, axes=plt.subplots(4,4,figsize=(10.2,7.7), squeeze=False)
    for row_index, dimension in enumerate(DIM_ORDER):
        for col, (population, series, order, labels) in enumerate([
            ("baseline","alpha",PANEL_ORDER,PANEL_LABELS), ("baseline","delta",DELTA_ORDER,DELTA_LABELS),
            ("hard_case","alpha",PANEL_ORDER,PANEL_LABELS), ("hard_case","delta",DELTA_ORDER,DELTA_LABELS),
        ]):
            ax=axes[row_index,col]
            subset={r["quantity"]:r for r in plotted if r["population"]==population and r["dimension"]==dimension and r["series"]==series}
            vals=[f(r["plot_value"]) for r in subset.values() if f(r["plot_value"]) is not None]
            for y, quantity in enumerate(order):
                if quantity in subset: interval(ax,y,subset[quantity],color="#1F4E79" if quantity!="delta_min" else "#9C3D2E",marker="D" if quantity=="delta_min" else "o",filled=quantity!="delta_min")
            ax.set_yticks(range(4),[labels[x] for x in order]); ax.set_ylim(3.45,-.55); style_axis(ax)
            if series=="delta": ax.axvline(0,color="#48545E",lw=.8,ls="--",zorder=1)
            if population == "hard_case":
                ax.set_facecolor("#FCFAF7")
                ax.set_title("DIAGNOSTIC — non-representative", loc="left", fontweight="semibold", fontsize=5.0, color="#7B3F00")
            else:
                ax.set_title(dimension if col == 0 else "", loc="left", fontweight="semibold", fontsize=8.1)
        # matching limits for corresponding baseline/hard-case quantity panels.
        for left,right in [(0,2),(1,3)]:
            values=[]
            for col in [left,right]:
                values += [f(r["plot_value"]) for r in plotted if r["dimension"]==dimension and r["series"]==("alpha" if left==0 else "delta") and f(r["plot_value"]) is not None]
            pad=max(.04,(max(values)-min(values))*.15)
            axes[row_index,left].set_xlim(min(values)-pad,max(values)+pad); axes[row_index,right].set_xlim(min(values)-pad,max(values)+pad)
    fig.text(.5,.992,"Interval bars: source-exported percentile-bootstrap intervals; confidence level unresolved",ha="center",va="top",fontsize=7.2,color="#38434D")
    for x, label in [(.20, "Baseline α"), (.42, "Baseline δ"), (.64, "Hard-case α"), (.86, "Hard-case δ")]:
        fig.text(x, .972, label, ha="center", va="top", fontsize=8.2, fontweight="semibold")
    caption(fig,metadata["caption"],width=180)
    fig.subplots_adjust(left=.12,right=.99,top=.91,bottom=.16,hspace=.8,wspace=.45)
    save(fig,out_dir,"figure_6")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args()
    with theme():
        for figure_id in ["figure_1","figure_2"]:
            rows,meta=load_figure(args.data_dir,figure_id); plot_replacement_grid(rows,meta,args.output_dir,figure_id)
        rows,meta=load_figure(args.data_dir,"figure_3"); plot_figure_3(rows,meta,args.output_dir)
        rows,meta=load_figure(args.data_dir,"figure_4"); plot_figure_4(rows,meta,args.output_dir)
        rows,meta=load_figure(args.data_dir,"figure_5"); plot_figure_5(rows,meta,args.output_dir)
        rows,meta=load_figure(args.data_dir,"figure_6"); plot_figure_6(rows,meta,args.output_dir)


if __name__ == "__main__":
    main()
