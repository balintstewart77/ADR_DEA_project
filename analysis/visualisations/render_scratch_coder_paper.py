"""Stage 2: render the manifest-listed scratch-coder paper deliverables.

The renderer accepts only extracted figure-data plus ordinary plotting libraries.
It has no canonical-results paths and never hashes or opens analytical sources.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, MultipleLocator
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


FONT = "DejaVu Sans"
PAIRS = (
    "C01 versus C02", "C01 versus C03", "C02 versus C03",
    "Fable 5 versus C01", "Fable 5 versus C02", "Fable 5 versus C03",
)
PAIR_DISPLAY = {pair: pair.replace(" versus ", "–") for pair in PAIRS}
FIGURE_SIZES = {
    "Figure 1": (17.0, 15.0), "Figure 2": (15.0, 9.5),
    "Figure 3": (18.0, 10.5), "Figure 4": (17.0, 15.0),
}
POP_STYLE = {
    "baseline": {"color": "#1f4e79", "marker": "o", "label": "Baseline"},
    "baseline_strict_sufficient": {"color": "#9a4f00", "marker": "s", "label": "Strict register-sufficient"},
    "hard_case": {"color": "#7a1f2b", "marker": "^", "label": "DIAGNOSTIC — non-representative"},
}
BAND_STYLE = {
    "STANDARD": {"marker": "o", "face": "#4c78a8", "label": "Standard (≥30)"},
    "LOW SUPPORT": {"marker": "s", "face": "#f2cf5b", "label": "Low support (10–29)"},
    "RARE": {"marker": "^", "face": "white", "label": "Rare (<10)"},
}


def load_manifest(data_dir: Path) -> dict:
    return json.loads((data_dir / "scratch_coder_deliverable_manifest.json").read_text())


def load_rows(data_dir: Path, entry: dict) -> list[dict]:
    path = data_dir / Path(entry["inputs"][0]).name
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def f(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rounded_outward(value: float, step: float, direction: str) -> float:
    return (math.floor(value / step) if direction == "down" else math.ceil(value / step)) * step


def calculate_limits(datasets: dict[str, list[dict]]) -> dict:
    delta_values = []
    alpha_14 = []
    alpha_2 = []
    for deliverable in ("Figure 1", "Figure 2", "Figure 4"):
        for row in datasets[deliverable]:
            if row["role"] != "plotted" or row["estimate_status"] != "R":
                continue
            target = delta_values if row["series"] == "delta" else alpha_2 if deliverable == "Figure 2" else alpha_14
            for field in ("parsed_value", "parsed_interval_lower", "parsed_interval_upper"):
                value = f(row[field])
                if value is not None:
                    target.append(value)
    delta_limit = max(0.2, rounded_outward(max(abs(v) for v in delta_values) + 0.02, 0.05, "up"))
    alpha_14_limits = (
        min(0.2, rounded_outward(min(alpha_14) - 0.02, 0.05, "down")),
        max(1.0, rounded_outward(max(alpha_14) + 0.02, 0.05, "up")),
    )
    alpha_2_limits = (
        rounded_outward(min(alpha_2) - 0.02, 0.05, "down"),
        rounded_outward(max(alpha_2) + 0.02, 0.05, "up"),
    )
    return {"delta": (-delta_limit, delta_limit), "alpha_figures_1_4": alpha_14_limits, "alpha_figure_2": alpha_2_limits}


def style_axes(ax):
    ax.grid(axis="x", color="#d9d9d9", linewidth=0.7, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)


def draw_value(ax, y: float, row: dict, *, color: str, marker: str, label: str | None = None):
    estimate = f(row["parsed_value"])
    if row["estimate_status"] != "R" or estimate is None:
        return
    lower, upper = f(row["parsed_interval_lower"]), f(row["parsed_interval_upper"])
    if row["interval_status"] == "R" and lower is not None and upper is not None:
        ax.hlines(y, lower, upper, color=color, linewidth=1.5, zorder=2)
        ax.vlines([lower, upper], y - 0.08, y + 0.08, color=color, linewidth=1.2, zorder=2)
        if lower == upper:
            ax.scatter([lower], [y], marker="D", s=75, facecolors="none", edgecolors="black", linewidths=1.4, zorder=5)
    ax.scatter([estimate], [y], marker=marker, s=58, facecolors=color if marker != "*" else "white",
               edgecolors="black", linewidths=0.8, zorder=4, label=label)
    if row["exported_caution"] == "True":
        ax.annotate("!", (estimate, y), xytext=(6, 6), textcoords="offset points", fontsize=8, fontweight="bold")


def add_caption(fig, deliverable: str, caption: str, *, y: float = 0.012):
    wrapped = textwrap.fill(f"{deliverable}. {caption}", width=185)
    fig.text(0.04, y, wrapped, ha="left", va="bottom", fontsize=8.5)


def render_figure1(rows: list[dict], out: Path, caption: str, limits: dict):
    dimensions = ["Research Domains", "Analytical Purposes", "COVID-19 & Pandemic", "Demographic disparities / equity"]
    fig, axes = plt.subplots(4, 2, figsize=FIGURE_SIZES["Figure 1"], constrained_layout=False)
    plt.subplots_adjust(left=0.13, right=0.79, top=0.94, bottom=0.20, wspace=0.28, hspace=0.62)
    for i, dimension in enumerate(dimensions):
        subset = [r for r in rows if r["dimension"] == dimension and r["role"] == "plotted"]
        for j, series in enumerate(("alpha", "delta")):
            ax = axes[i, j]
            selected = [r for r in subset if r["series"] == series]
            order = (["alpha ABC", "alpha LBC", "alpha ALC", "alpha ABL"] if series == "alpha" else ["delta_A", "delta_B", "delta_C", "delta_min"])
            keyed = {r["quantity"]: r for r in selected}
            for y, quantity in enumerate(order):
                row = keyed[quantity]
                marker = "*" if quantity == "delta_min" else "o"
                draw_value(ax, y, row, color="#2d5f8b" if series == "alpha" else "#7a3e00", marker=marker)
                if quantity == "delta_min":
                    match = row["presentation_note"].split("matching observed component(s): ")[-1]
                    ax.text(limits["delta"][1] * 0.97, y, f"matches {match}", ha="right", va="center", fontsize=7.5)
            ax.set_yticks(range(len(order)), [q.replace("alpha ", "α ").replace("delta", "δ") for q in order])
            ax.invert_yaxis()
            ax.set_xlim(limits["alpha_figures_1_4"] if series == "alpha" else limits["delta"])
            ax.xaxis.set_major_locator(MultipleLocator(0.2 if series == "alpha" else 0.1))
            if series == "delta":
                ax.axvline(0, color="black", linewidth=0.9, zorder=1)
            style_axes(ax)
            ax.set_title(("Krippendorff’s α" if series == "alpha" else "Replacement difference δ") + (f"\n{dimension}" if j == 0 else ""), loc="left", fontsize=11, fontweight="bold")
    key_ax = fig.add_axes([0.81, 0.36, 0.17, 0.39])
    key_ax.axis("off")
    key_ax.set_title("Panel and status key", loc="left", fontsize=10, fontweight="bold")
    key_text = (
        "ABC  C01/C02/C03\nLBC  Fable 5/C02/C03\nALC  C01/Fable 5/C03\nABL  C01/C02/Fable 5\n\n"
        "● estimate\n—| interval endpoints\n◇ coincident reported endpoints\n★ δ_min\n! exported caution\n\n"
        "δ_A = LBC − ABC\nδ_B = ALC − ABC\nδ_C = ABL − ABC"
    )
    key_ax.text(0, 0.95, key_text, va="top", fontsize=9.3, linespacing=1.45)
    add_caption(fig, "Figure 1", caption)
    save_figure(fig, out)


def render_overlay(rows: list[dict], out: Path, caption: str, limits: dict, deliverable: str):
    dimensions = ["Research Domains", "Analytical Purposes"] if deliverable == "Figure 2" else ["Research Domains", "Analytical Purposes", "COVID-19 & Pandemic", "Demographic disparities / equity"]
    populations = ["baseline", "baseline_strict_sufficient"] if deliverable == "Figure 2" else ["baseline", "hard_case"]
    fig, axes = plt.subplots(len(dimensions), 2, figsize=FIGURE_SIZES[deliverable], squeeze=False)
    bottom = 0.23 if deliverable == "Figure 2" else 0.20
    plt.subplots_adjust(left=0.13, right=0.79, top=0.93, bottom=bottom, wspace=0.30, hspace=0.62)
    dodge = {populations[0]: -0.10, populations[1]: 0.10}
    for i, dimension in enumerate(dimensions):
        for j, series in enumerate(("alpha", "delta")):
            ax = axes[i, j]
            order = ["alpha ABC", "alpha LBC", "alpha ALC", "alpha ABL"] if series == "alpha" else (["delta_min"] if deliverable == "Figure 2" else ["delta_A", "delta_B", "delta_C", "delta_min"])
            for population in populations:
                keyed = {r["quantity"]: r for r in rows if r["role"] == "plotted" and r["dimension"] == dimension and r["population"] == population and r["series"] == series}
                for y, quantity in enumerate(order):
                    style = POP_STYLE[population]
                    draw_value(ax, y + dodge[population], keyed[quantity], color=style["color"], marker=style["marker"])
                    if quantity == "delta_min":
                        estimate = f(keyed[quantity]["parsed_value"])
                        if estimate is not None:
                            ax.scatter(estimate, y + dodge[population], marker="*", s=24,
                                       facecolor="white", edgecolor="black", linewidth=0.6, zorder=5)
            ax.set_yticks(range(len(order)), [q.replace("alpha ", "α ").replace("delta", "δ") for q in order])
            ax.invert_yaxis()
            ax.set_xlim(limits["alpha_figure_2"] if deliverable == "Figure 2" and series == "alpha" else limits["alpha_figures_1_4"] if series == "alpha" else limits["delta"])
            ax.xaxis.set_major_locator(MultipleLocator(0.1 if series == "alpha" and deliverable == "Figure 2" else 0.2 if series == "alpha" else 0.1))
            if series == "delta":
                ax.axvline(0, color="black", linewidth=0.9, zorder=1)
            style_axes(ax)
            title = "Krippendorff’s α" if series == "alpha" else ("Minimum replacement difference δ_min" if deliverable == "Figure 2" else "Replacement difference δ")
            ax.set_title(title + (f"\n{dimension}" if j == 0 else ""), loc="left", fontsize=11, fontweight="bold")
    key_ax = fig.add_axes([0.81, 0.40 if deliverable == "Figure 2" else 0.42, 0.17, 0.28])
    key_ax.axis("off")
    key_ax.set_title("Population and status key", loc="left", fontsize=10, fontweight="bold")
    handles = [Line2D([0], [0], marker=POP_STYLE[p]["marker"], color="none", markerfacecolor=POP_STYLE[p]["color"], markeredgecolor="black", label=POP_STYLE[p]["label"], markersize=7) for p in populations]
    handles += [Line2D([0], [0], marker="D", color="none", markerfacecolor="none", markeredgecolor="black", label="Coincident reported bounds", markersize=7), Line2D([0], [0], marker="$!$", color="black", label="Exported caution", markersize=8)]
    key_ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=9, handletextpad=0.8)
    add_caption(fig, deliverable, caption)
    save_figure(fig, out)


def render_figure3(rows: list[dict], out: Path, caption: str):
    fig = plt.figure(figsize=FIGURE_SIZES["Figure 3"])
    grid = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.92], left=0.07, right=0.98, top=0.90, bottom=0.22, wspace=0.28)
    dimensions = ["Research Domains", "Analytical Purposes"]
    for idx, dimension in enumerate(dimensions):
        ax = fig.add_subplot(grid[0, idx])
        selected = sorted([r for r in rows if r["dimension"] == dimension], key=lambda r: int(r["source_order"]))
        maximum = max(max(int(r["parsed_value"]), int(r["parsed_interval_lower"])) for r in selected)
        limit = int(math.ceil((maximum + 3) / 10) * 10)
        ax.plot([0, limit], [0, limit], color="#555555", linestyle="--", linewidth=1)
        coord_labels: dict[tuple[int, int], list[str]] = defaultdict(list)
        for row in selected:
            x, y = int(row["parsed_value"]), int(row["parsed_interval_lower"])
            coord_labels[(x, y)].append(row["source_order"])
            style = BAND_STYLE[row["support_band"]]
            ax.scatter(x, y, marker=style["marker"], s=70, facecolor=style["face"], edgecolor="black", linewidth=0.9, zorder=3)
            if row["label"] == "Unclear from Register Entry":
                ax.scatter(x, y, marker="o", s=150, facecolors="none", edgecolors="#8b1a1a", linewidths=2.0, zorder=4)
        for (x, y), numbers in sorted(coord_labels.items()):
            ax.annotate(",".join(numbers), (x, y), xytext=(5, 5), textcoords="offset points", fontsize=8, zorder=5)
        ax.text(0.98, 0.84, "Model labels more often", transform=ax.transAxes, ha="right", fontsize=9, color="#444")
        ax.text(0.98, 0.10, "Model labels less often", transform=ax.transAxes, ha="right", fontsize=9, color="#444")
        ax.set(xlim=(-1, limit), ylim=(-1, limit), aspect="equal", xlabel="Records labelled by the human majority", ylabel="Records labelled by the model")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=7)); ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
        ax.set_title(dimension, loc="left", fontsize=12, fontweight="bold")
        style_axes(ax); ax.grid(axis="both", color="#e2e2e2", linewidth=0.6)
        inset = inset_axes(ax, width="39%", height="39%", loc="lower right", borderpad=1.1)
        zoom = [r for r in selected if int(r["parsed_value"]) <= 12 and int(r["parsed_interval_lower"]) <= 15]
        inset.plot([0, 15], [0, 15], color="#777", linestyle="--", linewidth=0.7)
        inset_coords: dict[tuple[int, int], list[str]] = defaultdict(list)
        for row in zoom:
            x, y = int(row["parsed_value"]), int(row["parsed_interval_lower"])
            inset_coords[(x, y)].append(row["source_order"])
            style = BAND_STYLE[row["support_band"]]
            inset.scatter(x, y, marker=style["marker"], s=38, facecolor=style["face"], edgecolor="black", linewidth=0.7)
        for (x, y), numbers in inset_coords.items():
            inset.annotate(",".join(numbers), (x, y), xytext=(3, 3), textcoords="offset points", fontsize=6.5)
        inset.set(xlim=(-0.5, 12.5), ylim=(-0.5, 15.5), title="Near-origin detail")
        inset.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4)); inset.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=4)); inset.tick_params(labelsize=6); inset.title.set_size(7)
    key_ax = fig.add_subplot(grid[0, 2]); key_ax.axis("off"); key_ax.set_title("Numbered label key", loc="left", fontsize=11, fontweight="bold")
    y = 0.97
    for dimension in dimensions:
        key_ax.text(0, y, dimension, fontweight="bold", fontsize=9.5, va="top"); y -= 0.045
        for row in sorted([r for r in rows if r["dimension"] == dimension], key=lambda r: int(r["source_order"])):
            label = textwrap.shorten(row["label"], width=48, placeholder="…")
            key_ax.text(0.01, y, f"{row['source_order']}. {label}", fontsize=8.1, va="top"); y -= 0.038
        y -= 0.025
    handles = [Line2D([0], [0], marker=s["marker"], color="none", markerfacecolor=s["face"], markeredgecolor="black", label=s["label"], markersize=7) for s in BAND_STYLE.values()]
    handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor="none", markeredgecolor="#8b1a1a", markeredgewidth=2, label="Unclear from Register Entry", markersize=9))
    key_ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=8.5)
    add_caption(fig, "Figure 3", caption)
    save_figure(fig, out)


def save_figure(fig, base: Path):
    fig.savefig(base.with_suffix(".svg"), format="svg", dpi=300, facecolor="white")
    fig.savefig(base.with_suffix(".png"), format="png", dpi=300, facecolor="white")
    plt.close(fig)


def display_value(row: dict) -> str:
    est, status, int_status = row["source_value_string"], row["estimate_status"], row["interval_status"]
    if status == "W": return "Withheld"
    if status == "D": return "Undefined"
    if status == "U": return "Unresolved"
    if status == "N": return "Not applicable"
    if status != "R" or est == "": return "Unavailable"
    try: shown = f"{float(est):.3f}"
    except ValueError: shown = est
    if int_status == "R" and row["interval_lower_string"] != "" and row["interval_upper_string"] != "":
        lo, hi = float(row["interval_lower_string"]), float(row["interval_upper_string"])
        suffix = " ◇" if lo == hi else ""
        confidence = " 95%" if row["confidence_level"] == "95%" else ""
        return f"{shown} [{lo:.3f}, {hi:.3f}]{confidence}{suffix}"
    if int_status in {"SV", "SD"}: return f"{shown} {int_status}"
    if int_status == "A": return f"{shown} A"
    return shown


def write_csv(path: Path, rows: list[dict]):
    fields = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    esc = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    return "\n".join(["| " + " | ".join(map(esc, headers)) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + ["| " + " | ".join(map(esc, row)) + " |" for row in rows])


def render_kappa(rows: list[dict], csv_path: Path, md_path: Path, caption: str):
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows: grouped[row["label"]][row["pair"]] = row
    labels = sorted(grouped, key=lambda label: (-int(next(iter(grouped[label].values()))["support_string"]), int(next(iter(grouped[label].values()))["source_order"])))
    wide = []
    for label in labels:
        base = next(iter(grouped[label].values()))
        item = {"label": label, "baseline_human_majority_support_n": base["support_string"], "support_band": base["support_band"]}
        for pair in PAIRS:
            row = grouped[label][pair]; prefix = PAIR_DISPLAY[pair]
            for target, source in (("estimate_string", "source_value_string"), ("estimate", "parsed_value"), ("lower_string", "interval_lower_string"), ("lower", "parsed_interval_lower"), ("upper_string", "interval_upper_string"), ("upper", "parsed_interval_upper"), ("estimate_status", "estimate_status"), ("interval_status", "interval_status"), ("method", "interval_method"), ("confidence", "confidence_level")):
                item[f"{prefix}_{target}"] = row[source]
        wide.append(item)
    write_csv(csv_path, wide)
    headers = ["Label", "Support n", "Band"] + [PAIR_DISPLAY[p] for p in PAIRS]
    md_rows = [[label, next(iter(grouped[label].values()))["support_string"], next(iter(grouped[label].values()))["support_band"]] + [display_value(grouped[label][p]) for p in PAIRS] for label in labels]
    notes = (
        "Human–human pairs are the first three columns; Fable 5–human pairs are the last three. Each reported interval is a 95% percentile-bootstrap interval. "
        "Withheld cells follow S5T009/S5T010. Pair columns share records and coders and are not independent comparisons. "
        "Support is the baseline human-majority-positive count: Standard ≥30, Low support 10–29, Rare <10. ◇ marks coincident reported bounds and does not imply absent sampling uncertainty. Full-width/landscape typesetting is recommended."
    )
    md_path.write_text(f"# {caption}\n\n{markdown_table(headers, md_rows)}\n\n**Notes.** {notes}\n")


def render_performance(rows: list[dict], csv_path: Path, md_path: Path, caption: str, dimension: str):
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows: grouped[row["label"]][row["quantity"]] = row
    labels = sorted(grouped, key=lambda label: (-int(next(iter(grouped[label].values()))["support_string"]), int(next(iter(grouped[label].values()))["source_order"])))
    wide = []
    for label in labels:
        base = grouped[label]["tp"]
        item = {"label": label, "baseline_human_majority_support_n": base["support_string"], "support_band": base["support_band"], "exported_caution": base["exported_caution"],
                "eligible_for_per_label_performance": base["eligible_for_per_label_performance"], "eligible_for_macro_average": base["eligible_for_macro_average"], "performance_metrics_reportable": base["performance_metrics_reportable"]}
        for quantity in ("tp", "fp", "fn", "tn", "precision", "recall", "f1"):
            row = grouped[label][quantity]
            for target, source in (("estimate_string", "source_value_string"), ("estimate", "parsed_value"), ("lower_string", "interval_lower_string"), ("lower", "parsed_interval_lower"), ("upper_string", "interval_upper_string"), ("upper", "parsed_interval_upper"), ("estimate_status", "estimate_status"), ("interval_status", "interval_status"), ("method", "interval_method"), ("confidence", "confidence_level"), ("status_string", "original_status_string")):
                item[f"{quantity}_{target}"] = row[source]
        wide.append(item)
    write_csv(csv_path, wide)
    headers = ["Label", "Support n", "TP", "FP", "FN", "TN", "Precision", "Recall", "F1", "Band"]
    md_rows = [[label, grouped[label]["tp"]["support_string"]]
               + [grouped[label][q]["source_value_string"] for q in ("tp", "fp", "fn", "tn")]
               + [display_value(grouped[label][q]) for q in ("precision", "recall", "f1")]
               + [grouped[label]["tp"]["support_band"]] for label in labels]
    unclear = grouped["Unclear from Register Entry"]
    unclear_note = f"In {dimension}, Unclear has model-positive n=1, TP=1, FP=0 and FN={unclear['fn']['source_value_string']}; precision 1.0 therefore reflects one model-positive record, not broad agreement. Its precision and F1 intervals are marked SV because only {re.search(r'valid/invalid/requested draws ([^;]+)', unclear['precision']['original_status_string']).group(1)} replicates were valid/invalid/requested, below the recorded 1,800-valid threshold."
    notes = (
        "Reference is the labelwise human majority, not an adjudicated record-level truth set. Each label is evaluated separately; this is not exact-set accuracy against an adjudicated label combination. "
        "TP: model and reference positive; FP: model positive/reference negative; FN: model negative/reference positive; TN: both negative. Precision denominator is model-positive records; recall denominator is human-majority-positive records. "
        "Standard ≥30, Low support 10–29, Rare <10 baseline human-majority-positive records; all exported cautions and the three eligibility/reportability flags remain in the CSV. Macro eligibility does not govern this table. "
        "Withheld is distinct from undefined/unavailable; SV means interval suppressed by the valid-replicate rule while the estimate is retained. " + unclear_note + " Unclear is a non-substantive classification option; FP/FN describe disagreement about applying it, not a proven right/wrong classification. Full-width/landscape typesetting is recommended."
    )
    md_path.write_text(f"# {caption}\n\n{markdown_table(headers, md_rows)}\n\n**Notes.** {notes}\n")


def render_table5(rows: list[dict], csv_path: Path, md_path: Path, caption: str):
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in rows: grouped[(row["dimension"], row["series"])][row["quantity"]] = row
    wide = []
    for (dimension, family), rel in grouped.items():
        meta = json.loads(rel["both_empty"]["presentation_note"].split("; structurally", 1)[0])
        item = {"dimension": dimension, "pair_family": family, **meta}
        for relation in ("containment", "overlap", "disjoint", "both_empty", "exactly_one_empty"):
            row = rel[relation]
            item[f"{relation}_count_string"] = row["source_value_string"]
            item[f"{relation}_count"] = row["parsed_value"]
            item[f"{relation}_proportion_string"] = row["interval_lower_string"]
            item[f"{relation}_proportion"] = row["parsed_interval_lower"]
            item[f"{relation}_proportion_status"] = row["interval_status"]
        item["overlap_structural_zero_note"] = "structurally impossible under this two-label relation definition" if dimension == "Joint cross-cutting tag set" else ""
        wide.append(item)
    write_csv(csv_path, wide)
    headers = ["Dimension", "Pair family", "Eligible pair denominator", "Containment n (proportion)", "Overlap n (proportion)", "Disjoint n (proportion)", "Both empty n", "Exactly one empty n", "Any empty-set-involved n"]
    def cp(row):
        return f"{row['source_value_string']} ({float(row['interval_lower_string']):.3f})" if row["interval_status"] == "reported" else f"{row['source_value_string']} (Unavailable: {row['interval_status']})"
    md_rows = []
    for (dimension, family), rel in grouped.items():
        meta = json.loads(rel["both_empty"]["presentation_note"].split("; structurally", 1)[0])
        overlap = cp(rel["overlap"])
        if dimension == "Joint cross-cutting tag set" and rel["overlap"]["interval_status"] == "reported": overlap += "*"
        md_rows.append([dimension, family.replace("_", "–"), meta["nonidentical_nonempty_pairs"], cp(rel["containment"]), overlap, cp(rel["disjoint"]), rel["both_empty"]["source_value_string"], rel["exactly_one_empty"]["source_value_string"], meta["empty_set_involved_pairs"]])
    notes = (
        "Proportion header/conditioning: Among non-identical pairs with both label sets non-empty. Denominators are pair units, not records. "
        "Each record can contribute C01–C02, C01–C03 and C02–C03 to human–human, or Fable 5–C01, Fable 5–C02 and Fable 5–C03 to model–human, but eligibility still depends on the pair’s sets. Pairs within a record share observations and are not independent samples. "
        "The source defines empty_set_involved_pairs as both_empty + exactly_one_empty, including identical both-empty pairs; those components are shown separately. Exactly-one-empty pairs are disagreements. Both-empty joint-tag pairs show shared tag absence only for that pair, not general agreement. "
        "* Joint-tag overlap is a reported numeric zero and structurally impossible under this two-label relation definition. Not-applicable/zero-denominator proportions remain unavailable and are never converted to zero or renormalised. No intervals or missing proportions were created."
    )
    md_path.write_text(f"# {caption}\n\n{markdown_table(headers, md_rows)}\n\n**Notes.** {notes}\n")


def render_s1(rows: list[dict], csv_path: Path, md_path: Path, caption: str):
    # The final machine-readable table remains long so Part A intervals and Part B
    # categorical cells retain independent source strings and statuses.
    write_csv(csv_path, rows)
    part_a = [r for r in rows if r["series"] == "Part A"]
    a_group: dict[tuple[str, str, str], dict[str, dict]] = defaultdict(dict)
    for row in part_a: a_group[(row["dimension"], row["population"], row["label"])][row["quantity"]] = row
    a_rows = []
    for key, values in a_group.items():
        construct, population, category = key
        a_rows.append([construct, "Baseline" if population == "baseline" else "Hard-case — DIAGNOSTIC", category,
                       values["count"]["source_value_string"], values["proportion"]["sample_size"], display_value(values["proportion"])])
    part_b = [r for r in rows if r["series"] == "Part B"]
    size = [r for r in part_b if r["quantity"] == "majority_set_size"]
    size_group: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in size: size_group[(row["population"], row["dimension"])][row["label"]] = row
    b1 = []
    for (population, dimension), values in size_group.items():
        b1.append(["Baseline" if population == "baseline" else "Hard-case — DIAGNOSTIC", dimension, values["size_0"]["denominator_string"]] + [values[k]["source_value_string"] for k in ("size_0", "size_1", "size_2", "size_3", "size_4_plus")])
    composition = [r for r in part_b if r["quantity"] == "unclear_composition"]
    comp_group: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in composition: comp_group[(row["population"], row["dimension"])][row["label"]] = row
    b2 = []
    keys = ("unclear_absent__substantive_absent", "unclear_absent__substantive_present", "unclear_present__substantive_absent", "unclear_present__substantive_present")
    for (population, dimension), values in comp_group.items():
        b2.append(["Baseline" if population == "baseline" else "Hard-case — DIAGNOSTIC", dimension, values[keys[0]]["denominator_string"]] + [values[k]["source_value_string"] for k in keys])
    card = [r for r in part_b if r["quantity"] == "majority_set_exceeds_single_coder_constraint"]
    b3 = [["Baseline" if r["population"] == "baseline" else "Hard-case — DIAGNOSTIC", r["dimension"], "At most two purposes" if r["dimension"] == "Analytical Purposes" else "No documented constraint", (r["source_value_string"] + "/" + r["denominator_string"]) if r["estimate_status"] == "R" else r["unavailable_reason"]] for r in card]
    content = [f"# {caption}", "", "## Part A — Sufficiency and taxonomy-fit record-majority categories", "", markdown_table(["Response", "Population", "Source category", "Count", "Denominator (records)", "Exported proportion [interval/status]"], a_rows), "", "Baseline intervals shown are the source-supplied 95% Wilson intervals. Hard-case proportions retain interval-unavailable/non-application status; no interval is extrapolated. ‘No majority / split judgement’ retains the source name and is not pooled with Part B.", "", "## Part B — Majority-label coverage", "", "### Majority-set size", "", markdown_table(["Population", "Dimension", "Denominator (records)", "0", "1", "2", "3", "4+"], b1), "", "### Majority Unclear × substantive-label presence", "", markdown_table(["Population", "Dimension", "Denominator (records)", "Unclear absent / substantive absent", "Unclear absent / substantive present", "Unclear present / substantive absent", "Unclear present / substantive present"], b2), "", "### Documented single-coder constraint", "", markdown_table(["Population", "Dimension", "Constraint", "Derived-majority exceedance"], b3), "", "Part B reports operational labelwise-majority outcomes only. No-majority and Unclear-only counts remain separate; no combined statistic is introduced. No human-majority set contained both Unclear and a substantive label in the observed baseline or hard-case populations for either dimension. Analytical Purposes has the documented two-label single-coder limit and zero exported derived-majority exceedances; Research Domains is not assessed because no constraint is documented."]
    md_path.write_text("\n".join(content) + "\n")


def archive_legacy(figure_dir: Path, archive_dir: Path):
    candidates = [figure_dir / f"scratch_coder_figure_{number}.{suffix}" for number in range(1, 7) for suffix in ("svg", "png")]
    existing = [path for path in candidates if path.exists()]
    if not existing: return []
    if archive_dir.exists(): raise RuntimeError(f"Fresh archive directory already exists: {archive_dir}")
    archive_dir.mkdir(parents=True)
    moved = []
    for path in existing:
        target = archive_dir / path.name
        shutil.move(path, target)
        moved.append({"from": str(path), "to": str(target)})
    return moved


def validate_visibility(datasets: dict[str, list[dict]], limits: dict) -> dict:
    results = {}
    for deliverable in ("Figure 1", "Figure 2", "Figure 4"):
        misses = []
        for row in datasets[deliverable]:
            if row["role"] != "plotted" or row["estimate_status"] != "R": continue
            lim = limits["alpha_figure_2"] if deliverable == "Figure 2" and row["series"] == "alpha" else limits["alpha_figures_1_4"] if row["series"] == "alpha" else limits["delta"]
            for field in ("parsed_value", "parsed_interval_lower", "parsed_interval_upper"):
                value = f(row[field])
                if value is not None and not (lim[0] < value < lim[1]): misses.append(f"{row['source_table_id']}:{row['quantity']}:{field}={value}")
        results[deliverable] = {"all_values_strictly_inside_axes": not misses, "misses": misses}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--figure-dir", type=Path, required=True)
    parser.add_argument("--table-dir", type=Path, required=True)
    parser.add_argument("--archive-dir", type=Path)
    args = parser.parse_args()
    data_dir, figure_dir, table_dir = map(Path.resolve, (args.data_dir, args.figure_dir, args.table_dir))
    figure_dir.mkdir(parents=True, exist_ok=True); table_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(data_dir)
    datasets = {deliverable: load_rows(data_dir, entry) for deliverable, entry in manifest["current"].items()}
    # Enforce manifest routing: no glob discovers deliverables.
    expected = {"Figure 1", "Figure 2", "Figure 3", "Figure 4", "Table 1", "Table 2", "Table 3", "Table 4", "Table 5", "Supplementary Table S1"}
    if set(datasets) != expected: raise RuntimeError(f"Manifest deliverable mismatch: {set(datasets) ^ expected}")
    moved = archive_legacy(figure_dir, args.archive_dir.resolve()) if args.archive_dir else []
    if args.archive_dir and not moved:
        archive_dir = args.archive_dir.resolve()
        moved = [{"from": "already archived", "to": str(path)} for path in sorted(archive_dir.glob("scratch_coder_figure_[1-6].*"))]
    limits = calculate_limits(datasets)
    for deliverable in ("Figure 1", "Figure 2", "Figure 3", "Figure 4"):
        entry = manifest["current"][deliverable]; base = figure_dir / entry["stem"]
        if deliverable == "Figure 1": render_figure1(datasets[deliverable], base, entry["caption"], limits)
        elif deliverable == "Figure 3": render_figure3(datasets[deliverable], base, entry["caption"])
        else: render_overlay(datasets[deliverable], base, entry["caption"], limits, deliverable)
    for deliverable in ("Table 1", "Table 2", "Table 3", "Table 4", "Table 5", "Supplementary Table S1"):
        entry = manifest["current"][deliverable]; csv_path = table_dir / f"{entry['stem']}.csv"; md_path = table_dir / f"{entry['stem']}.md"
        if deliverable in {"Table 1", "Table 2"}: render_kappa(datasets[deliverable], csv_path, md_path, entry["caption"])
        elif deliverable in {"Table 3", "Table 4"}: render_performance(datasets[deliverable], csv_path, md_path, entry["caption"], datasets[deliverable][0]["dimension"])
        elif deliverable == "Table 5": render_table5(datasets[deliverable], csv_path, md_path, entry["caption"])
        else: render_s1(datasets[deliverable], csv_path, md_path, entry["caption"])
    captions = [f"# Scratch-coder figure captions\n"] + [f"## {d}\n\n{manifest['current'][d]['caption']}\n" for d in ("Figure 1", "Figure 2", "Figure 3", "Figure 4")]
    (figure_dir / "scratch_coder_figure_captions.md").write_text("\n".join(captions))
    report = {
        "renderer": "analysis/visualisations/render_scratch_coder_paper.py",
        "input_boundary": "manifest plus listed extracted CSV/JSON only",
        "manifest": str(data_dir / "scratch_coder_deliverable_manifest.json"),
        "font": FONT, "matplotlib_font_resolved": font_manager.findfont(FONT),
        "figure_dimensions_inches": {key: list(value) for key, value in FIGURE_SIZES.items()},
        "axis_limits": limits, "visibility_validation": validate_visibility(datasets, limits),
        "figure_2_layout": "population overlay with dodged positions succeeded",
        "figure_4_layout": "population overlay with dodged positions succeeded",
        "archived_legacy_outputs": moved,
        "markdown_review_scope": "Markdown source rendered structurally; no journal-specific typesetter was available, so publication-layout typesetting remains unverified.",
    }
    resolved_manifest = json.loads(json.dumps(manifest))
    for number in range(1, 7):
        old_id, old_number = f"old Figure {number}", f"scratch_coder_figure_{number}"
        resolved_manifest["withdrawn"][old_id]["archived_outputs"] = [
            item["to"] for item in moved if Path(item["to"]).stem == old_number
        ]
    resolved_path = figure_dir / "scratch_coder_deliverable_manifest_resolved.json"
    resolved_manifest["resolved_manifest_path"] = str(resolved_path)
    resolved_path.write_text(json.dumps(resolved_manifest, indent=2, ensure_ascii=False) + "\n")
    report["resolved_manifest"] = str(resolved_path)
    (figure_dir / "scratch_coder_rendering_report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
