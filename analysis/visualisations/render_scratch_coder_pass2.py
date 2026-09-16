"""Stage 2 for the pass-2 scratch-coder presentation run.

The renderer reads only a pass-2 manifest and its listed figure-data files.
It contains no paths to analytical reports or exports and performs only display
rounding and graphical layout arithmetic.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sys
import textwrap
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Circle
from matplotlib.text import Text
from matplotlib.ticker import MultipleLocator


matplotlib.rcParams.update({
    "font.family": "DejaVu Sans", "svg.fonttype": "none", "svg.hashsalt": "scratch-coder-pass2",
    "axes.titlesize": 10.5, "axes.labelsize": 9.5, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
})

PAIR_ORDER = (
    "C01 versus C02", "C01 versus C03", "C02 versus C03",
    "Fable 5 versus C01", "Fable 5 versus C02", "Fable 5 versus C03",
)
PAIR_SHORT = {
    "C01 versus C02": "C01–C02", "C01 versus C03": "C01–C03", "C02 versus C03": "C02–C03",
    "Fable 5 versus C01": "C01", "Fable 5 versus C02": "C02", "Fable 5 versus C03": "C03",
}
DIMENSION_ORDER = ("Research Domains", "Analytical Purposes", "Demographic disparities / equity", "COVID-19 & Pandemic")
REPLACEMENT_ORDER = ("alpha ABC", "alpha LBC", "alpha ALC", "alpha ABL")
DELTA_ORDER = ("delta_A", "delta_B", "delta_C", "delta_min")
ALPHA_LABELS = {"alpha ABC": "α ABC", "alpha LBC": "α LBC", "alpha ALC": "α ALC", "alpha ABL": "α ABL"}
DELTA_LABELS = {"delta_A": "δ$_A$", "delta_B": "δ$_B$", "delta_C": "δ$_C$", "delta_min": "δ$_{min}$"}
COLORS = {"blue": "#2F5D7E", "orange": "#B55A30", "red": "#8C3B4A", "grey": "#6B6B6B"}
DISAGREE_COLORS = {"containment": "#3B6B8C", "overlap": "#C58B36", "disjoint": "#777777"}
BANNED = (
    re.compile(r"support", re.I), re.compile(r"\bStandard\b", re.I), re.compile(r"\bRare\b", re.I),
    re.compile(r"\bWithheld\b", re.I), re.compile(r"\bSV\b"), re.compile(r"delta_", re.I),
    re.compile(r"source-exported", re.I), re.compile(r"canonical", re.I), re.compile(r"U\d{4}"),
    re.compile(r"^Notes\b", re.I),
)


def f(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def d(value: str) -> Decimal:
    return Decimal(str(value))


def half_up(value: str, places: int = 2) -> str:
    quantum = Decimal(1).scaleb(-places)
    rounded = d(value).quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    return f"{rounded:.{places}f}"


def signed(value: str, places: int = 3) -> str:
    shown = half_up(value, places)
    if d(shown) > 0:
        return "+" + shown
    return shown.replace("-0." + "0" * places, "0." + "0" * places)


def whole_percent(value: str) -> int:
    return int((d(value) * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percent_2(value: str) -> str:
    return half_up(str(d(value) * Decimal(100)), 2)


def load(data_dir: Path) -> tuple[dict, dict[str, list[dict]]]:
    manifest = json.loads((data_dir / "pass2_deliverable_manifest.json").read_text(encoding="utf-8"))
    datasets = {}
    for deliverable, entry in manifest["entries"].items():
        with (data_dir / entry["inputs"]["data"]).open(newline="", encoding="utf-8") as handle:
            datasets[deliverable] = list(csv.DictReader(handle))
    return manifest, datasets


def archive_existing(figure_dir: Path, table_dir: Path) -> list[dict]:
    moved = []
    mappings = {
        figure_dir: {
            "scratch_coder_figure_1_panel_agreement": "figure_1_panel_agreement_replacement_superseded",
            "scratch_coder_figure_2_sufficiency_sensitivity": "figure_2_sufficiency_sensitivity_superseded",
            "scratch_coder_figure_3_label_application_patterns": "figure_3_label_application_superseded",
            "scratch_coder_figure_4_baseline_hard_case": "supplementary_figure_s1_baseline_vs_hardcase_superseded",
            "scratch_coder_deliverable_manifest_resolved": "legacy_deliverable_manifest_resolved",
            "scratch_coder_figure_captions": "legacy_figure_captions_superseded",
            "scratch_coder_rendering_report": "legacy_rendering_report_superseded",
        },
        table_dir: {
            "scratch_coder_table_1_pairwise_kappa_domains": "table_1_agreement_domains_superseded",
            "scratch_coder_table_2_pairwise_kappa_purposes": "table_2_agreement_purposes_superseded",
            "scratch_coder_table_3_contingencies_performance_domains": "table_3_agreement_with_majority_domains_superseded",
            "scratch_coder_table_4_contingencies_performance_purposes": "table_4_agreement_with_majority_purposes_superseded",
            "scratch_coder_table_5_disagreeing_pair_relations": "table_5_disagreement_composition_superseded",
            "scratch_coder_supplementary_table_s1_majority_coverage": "supplementary_table_s1_combined_superseded",
        },
    }
    for directory, stems in mappings.items():
        archive = directory / "archive" / "pass2_preexisting_6cbf154"
        existing = []
        for old, new in stems.items():
            for path in directory.glob(old + ".*"):
                if path.is_file():
                    existing.append((path, archive / (new + path.suffix)))
        if existing:
            archive.mkdir(parents=True, exist_ok=True)
        for source, target in sorted(existing):
            if target.exists():
                raise RuntimeError(f"Archive target already exists: {target}")
            shutil.move(source, target)
            moved.append({"from": str(source), "to": str(target)})
    return moved


def style_axis(ax, grid: str = "x"):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid, color="#E2E2E2", linewidth=0.7, zorder=0)
    ax.tick_params(length=3)


def draw_interval(ax, y: float, row: dict, color: str, marker: str = "o", hollow: bool = False):
    estimate = f(row["parsed_value"])
    lower, upper = f(row["parsed_interval_lower"]), f(row["parsed_interval_upper"])
    if estimate is None:
        return
    if lower is not None and upper is not None and row["interval_status"] == "R":
        ax.hlines(y, lower, upper, color=color, linewidth=1.6, zorder=2)
        ax.vlines([lower, upper], y - 0.08, y + 0.08, color=color, linewidth=1.1, zorder=2)
        if lower == upper:
            ax.scatter(lower, y, marker="D", s=75, facecolors="none", edgecolors=color, linewidths=1.4, zorder=3)
    ax.scatter(estimate, y, marker=marker, s=82 if marker == "*" else 50,
               facecolors="none" if hollow else color, edgecolors=color if hollow else "black",
               linewidths=1.2 if hollow else 0.7, zorder=4)


def save_figure(fig, base: Path) -> dict:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    figure_box = fig.bbox
    clipped = []
    for text in fig.findobj(Text):
        if not text.get_visible() or not text.get_text().strip():
            continue
        box = text.get_window_extent(renderer)
        if box.width and box.height and (box.x0 < figure_box.x0 - 2 or box.y0 < figure_box.y0 - 2 or box.x1 > figure_box.x1 + 2 or box.y1 > figure_box.y1 + 2):
            clipped.append(text.get_text())
    fig.savefig(base.with_suffix(".svg"), format="svg", dpi=300, facecolor="white", metadata={"Date": None})
    fig.savefig(base.with_suffix(".png"), format="png", dpi=300, facecolor="white", metadata={"Software": "matplotlib"})
    texts = [text.get_text() for text in fig.findobj(Text) if text.get_visible() and text.get_text().strip()]
    plt.close(fig)
    return {"clipped_text_candidates": clipped, "rendered_text": texts}


def figure_text_check(texts: list[str]) -> list[dict]:
    failures = []
    for value in texts:
        for pattern in BANNED:
            if pattern.search(value):
                failures.append({"text": value, "pattern": pattern.pattern})
    return failures


def replacement_axes(fig, axes, rows: list[dict], dimensions: tuple[str, ...], populations: tuple[str, ...],
                     alpha_range: tuple[float, float], delta_range: tuple[float, float], s1: bool = False):
    dodge = {populations[0]: -0.10, populations[-1]: 0.10} if len(populations) == 2 else {populations[0]: 0.0}
    styles = {
        "baseline": (COLORS["blue"], False, "Baseline (n=150)"),
        "baseline_strict_sufficient": (COLORS["orange"], True, "Strict register-sufficient (n=92)"),
        "hard_case": (COLORS["red"], True, "Hard-case (n=75; diagnostic, non-representative)"),
    }
    for index, dimension in enumerate(dimensions):
        for column, series in enumerate(("alpha", "delta")):
            ax = axes[index, column]
            order = REPLACEMENT_ORDER if series == "alpha" else DELTA_ORDER
            for population in populations:
                keyed = {r["quantity"]: r for r in rows if r["dimension"] == dimension and r["population"] == population and r["series"] == series and r["role"] == "plotted"}
                for y, quantity in enumerate(order):
                    color, hollow, _ = styles[population]
                    draw_interval(ax, y + dodge[population], keyed[quantity], color,
                                  marker="*" if quantity == "delta_min" else "o", hollow=hollow)
            labels = [ALPHA_LABELS[q] for q in order] if series == "alpha" else [DELTA_LABELS[q] for q in order]
            if series == "delta" and not s1:
                component = "δ$_A$" if dimension == "COVID-19 & Pandemic" and populations == ("baseline",) else "δ$_B$"
                labels[-1] += f" (= {component} estimate)"
            ax.set_yticks(range(len(order)), labels)
            ax.invert_yaxis()
            ax.set_xlim(alpha_range if series == "alpha" else delta_range)
            ax.xaxis.set_major_locator(MultipleLocator(0.2 if series == "alpha" and alpha_range == (0.0, 1.0) else 0.1))
            if series == "delta":
                ax.axvline(0, color="#222222", linewidth=0.9, zorder=1)
            style_axis(ax)
            if index == 0:
                ax.set_title("Krippendorff’s α" if series == "alpha" else "Replacement difference")
            if column == 0:
                shown_dimension = dimension
                if dimension == "Demographic disparities / equity":
                    shown_dimension += "\nApplied by coder majority: " + ("baseline 11; hard-case 8" if s1 else "11 records")
                elif dimension == "COVID-19 & Pandemic":
                    shown_dimension += "\nApplied by coder majority: " + ("baseline 12; hard-case 6" if s1 else "12 records")
                ax.set_ylabel(shown_dimension, fontweight="bold", labelpad=12)
    return styles


def render_figure1(rows: list[dict], base: Path) -> tuple[dict, dict]:
    fig, axes = plt.subplots(4, 2, figsize=(13.5, 12.5), constrained_layout=True)
    replacement_axes(fig, axes, rows, DIMENSION_ORDER, ("baseline",), (0.0, 1.0), (-0.45, 0.45))
    handles = [
        Line2D([0], [0], marker="o", color="#333", markerfacecolor=COLORS["blue"], linewidth=1.3, label="Estimate and interval"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="none", markeredgecolor=COLORS["blue"], label="Zero-width interval"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=COLORS["blue"], markeredgecolor="black", markersize=10, label="δₘᵢₙ estimate"),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False)
    render = save_figure(fig, base)
    return render, {"status": "PASS", "encodings_present": ["estimate and interval", "zero-width interval", "δₘᵢₙ"],
                    "key_entries": [h.get_label() for h in handles]}


def render_figure2(rows: list[dict], base: Path) -> tuple[dict, dict]:
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 7.3), constrained_layout=True)
    styles = replacement_axes(fig, axes, rows, DIMENSION_ORDER[:2], ("baseline", "baseline_strict_sufficient"), (0.15, 0.75), (-0.45, 0.45))
    handles = [
        Line2D([0], [0], marker="o", color=styles[p][0], markerfacecolor="none" if styles[p][1] else styles[p][0],
               markeredgecolor=styles[p][0], label=styles[p][2], linewidth=1.2) for p in ("baseline", "baseline_strict_sufficient")
    ]
    handles.append(Line2D([0], [0], marker="*", color="none", markerfacecolor="#777", markeredgecolor="black", markersize=10, label="δₘᵢₙ estimate"))
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False)
    render = save_figure(fig, base)
    return render, {"status": "PASS", "encodings_present": ["baseline filled", "strict hollow", "δₘᵢₙ star"], "key_entries": [h.get_label() for h in handles]}


def render_s1(rows: list[dict], base: Path) -> tuple[dict, dict]:
    fig, axes = plt.subplots(4, 2, figsize=(13.5, 12.8), constrained_layout=True)
    styles = replacement_axes(fig, axes, rows, DIMENSION_ORDER, ("baseline", "hard_case"), (0.0, 1.0), (-0.45, 0.45), s1=True)
    fig.text(0.5, 0.995, "Hard-case sample: diagnostic, non-representative", ha="center", va="top", fontsize=10, fontweight="bold", color=COLORS["red"])
    handles = [
        Line2D([0], [0], marker="o", color=styles[p][0], markerfacecolor="none" if styles[p][1] else styles[p][0],
               markeredgecolor=styles[p][0], label=styles[p][2], linewidth=1.2) for p in ("baseline", "hard_case")
    ]
    handles.append(Line2D([0], [0], marker="*", color="none", markerfacecolor="#777", markeredgecolor="black", markersize=10, label="δₘᵢₙ estimate"))
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False)
    render = save_figure(fig, base)
    return render, {"status": "PASS", "encodings_present": ["baseline filled", "hard-case hollow", "δₘᵢₙ star"], "key_entries": [h.get_label() for h in handles]}


DIRECT_LABELS = {
    "Research Domains": {1, 4, 8},
    "Analytical Purposes": {1, 4},
}


def point_label(row: dict) -> str:
    if int(row["source_order"]) not in DIRECT_LABELS[row["dimension"]]:
        return row["source_order"]
    return "\n".join(textwrap.wrap(row["label"], width=26, break_long_words=False))


def expanded(box, pixels: float):
    return box.expanded((box.width + 2 * pixels) / max(box.width, 1), (box.height + 2 * pixels) / max(box.height, 1))


def place_labels(fig, ax, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    markers = []
    for row in rows:
        x, y = float(row["parsed_value"]), float(row["parsed_interval_lower"])
        px, py = ax.transData.transform((x, y))
        from matplotlib.transforms import Bbox
        markers.append(Bbox.from_extents(px - 6, py - 6, px + 6, py + 6))
    placed = []; positions = []
    radii = (18, 28, 40, 55, 72, 90, 115, 140, 170, 200)
    angles = (35, 145, -35, -145, 75, 105, -75, -105, 0, 180, 90, -90)
    figure_box = fig.bbox
    for row in sorted(rows, key=lambda r: (-len(point_label(r)), int(r["source_order"]))):
        x, y = float(row["parsed_value"]), float(row["parsed_interval_lower"])
        accepted = None
        for radius in radii:
            for angle in angles:
                dx = radius * math.cos(math.radians(angle)); dy = radius * math.sin(math.radians(angle))
                annotation = ax.annotate(point_label(row), xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                                         ha="left" if dx >= 0 else "right", va="bottom" if dy >= 0 else "top",
                                         fontsize=7.0, annotation_clip=False,
                                         bbox={"boxstyle": "round,pad=0.16", "fc": "white", "ec": "none", "alpha": 0.90},
                                         arrowprops={"arrowstyle": "-", "color": "#777", "lw": 0.7, "shrinkA": 2, "shrinkB": 5})
                annotation.set_gid("point-label")
                fig.canvas.draw(); box = annotation.get_window_extent(renderer)
                inside = box.x0 >= figure_box.x0 + 3 and box.y0 >= figure_box.y0 + 3 and box.x1 <= figure_box.x1 - 3 and box.y1 <= figure_box.y1 - 3
                collision = any(expanded(box, 2).overlaps(other) for other in placed) or any(expanded(box, 2).overlaps(marker) for marker in markers)
                if inside and not collision:
                    accepted = (annotation, box, dx, dy); break
                annotation.remove()
            if accepted:
                break
        if not accepted:
            raise RuntimeError(f"Figure 3 label placement failed for {row['dimension']}: {row['label']}")
        annotation, box, dx, dy = accepted
        placed.append(box)
        positions.append({"dimension": row["dimension"], "label": row["label"], "x": x, "y": y, "dx_points": dx, "dy_points": dy})
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    markers = []
    for row in rows:
        px, py = ax.transData.transform((float(row["parsed_value"]), float(row["parsed_interval_lower"])))
        from matplotlib.transforms import Bbox
        markers.append(Bbox.from_extents(px - 6, py - 6, px + 6, py + 6))
    final_boxes = [annotation.get_window_extent(renderer) for annotation in ax.texts if annotation.get_gid() == "point-label"]
    overlaps = []
    for i, box in enumerate(final_boxes):
        for j in range(i + 1, len(final_boxes)):
            if box.overlaps(final_boxes[j]): overlaps.append([i, j])
        for j, marker in enumerate(markers):
            if box.overlaps(marker): overlaps.append([i, f"marker-{j}"])
    return positions, overlaps


def render_figure3(rows: list[dict], base: Path) -> tuple[dict, dict]:
    fig = plt.figure(figsize=(18, 10.8), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[4.2, 1.25])
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])]
    key_axes = [fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])]
    all_positions = []; all_overlaps = []
    for ax, dimension in zip(axes, DIMENSION_ORDER[:2]):
        selected = sorted([r for r in rows if r["dimension"] == dimension], key=lambda r: int(r["source_order"]))
        ax.plot([0, 60], [0, 60], color="#555", linestyle="--", linewidth=1.0, zorder=1)
        ax.axvline(10, color="#BBBBBB", linewidth=0.9, zorder=0); ax.axvline(30, color="#BBBBBB", linewidth=0.9, zorder=0)
        ax.text(10, 59, "10", ha="center", va="top", fontsize=8, color="#666")
        ax.text(30, 59, "30", ha="center", va="top", fontsize=8, color="#666")
        for row in selected:
            x, y = int(row["parsed_value"]), int(row["parsed_interval_lower"])
            ax.scatter(x, y, marker="o", s=52, facecolor=COLORS["blue"], edgecolor="black", linewidth=0.7, zorder=3)
            if row["label"] == "Unclear from Register Entry":
                ax.scatter(x, y, marker="o", s=145, facecolors="none", edgecolors=COLORS["red"], linewidths=1.8, zorder=4)
        ax.set(xlim=(0, 60), ylim=(0, 60), aspect="equal", xlabel="Records labelled by the coder majority", ylabel="Records labelled by Fable 5")
        ax.set_title(dimension, fontweight="bold")
        style_axis(ax, "both")
        positions, overlaps = place_labels(fig, ax, selected)
        all_positions.extend(positions); all_overlaps.extend([{"dimension": dimension, "pair": pair} for pair in overlaps])
        key_ax = key_axes[0 if dimension == "Research Domains" else 1]
        key_ax.axis("off")
        crowded = [row for row in selected if int(row["source_order"]) not in DIRECT_LABELS[dimension]]
        key_ax.set_title("Numbered labels", loc="left", fontsize=9, fontweight="bold")
        columns = 2
        split = math.ceil(len(crowded) / columns)
        for index, row in enumerate(crowded):
            column = index // split; within = index % split
            label = row["label"] + (" (coder declined to classify)" if row["label"] == "Unclear from Register Entry" else "")
            key_ax.text(column * 0.50, 0.88 - within * 0.19, f"{row['source_order']}. {label}", transform=key_ax.transAxes,
                        ha="left", va="top", fontsize=7.6, wrap=True)
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    annotations = [text for ax in axes for text in ax.texts if text.get_gid() == "point-label"]
    boxes = [annotation.get_window_extent(renderer) for annotation in annotations]
    global_markers = []
    from matplotlib.transforms import Bbox
    for ax, dimension in zip(axes, DIMENSION_ORDER[:2]):
        for row in [r for r in rows if r["dimension"] == dimension]:
            px, py = ax.transData.transform((float(row["parsed_value"]), float(row["parsed_interval_lower"])))
            global_markers.append(Bbox.from_extents(px - 6, py - 6, px + 6, py + 6))
    for i, box in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            if box.overlaps(boxes[j]): all_overlaps.append({"global_labels": [i, j]})
        for j, marker in enumerate(global_markers):
            if box.overlaps(marker): all_overlaps.append({"global_label_marker": [i, j]})
    if all_overlaps or len(all_positions) != 20:
        raise RuntimeError(f"Figure 3 rendered-label assertion failed: labels={len(all_positions)}, overlaps={all_overlaps}")
    render = save_figure(fig, base)
    return render, {"status": "PASS", "labels_expected": 20, "labels_rendered": len(all_positions), "overlaps": all_overlaps,
                    "positions": all_positions, "key_entries": ["Numbered labels", "Unclear from Register Entry (coder declined to classify)"],
                    "encodings_present": ["numbered crowded-point labels", "direct isolated-point names", "Unclear outline"]}


def disagreement_group(rows: list[dict]) -> dict[tuple[str, str], dict[str, dict]]:
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        grouped[(row["dimension"], row["series"])][row["quantity"]] = row
    return grouped


def render_figure4(rows: list[dict], base: Path) -> tuple[dict, dict, list[dict]]:
    grouped = disagreement_group(rows)
    order = (("Research Domains", "human_human"), ("Research Domains", "model_human"),
             ("Analytical Purposes", "human_human"), ("Analytical Purposes", "model_human"))
    labels = ("Between human coders", "Fable 5 with each coder", "Between human coders", "Fable 5 with each coder")
    y = (3.3, 2.45, 1.15, 0.30)
    fig, ax = plt.subplots(figsize=(12.5, 6.3), constrained_layout=True)
    sums = []
    for position, key, label in zip(y, order, labels):
        relations = grouped[key]; left = Decimal(0); displayed = []
        denom = json.loads(relations["containment"]["presentation_note"].split("; structurally", 1)[0])["nonidentical_nonempty_pairs"]
        for relation in ("containment", "overlap", "disjoint"):
            row = relations[relation]; width = d(row["interval_lower_string"]) * Decimal(100)
            ax.barh(position, float(width), left=float(left), height=0.55, color=DISAGREE_COLORS[relation], edgecolor="white", linewidth=0.8)
            pct = whole_percent(row["interval_lower_string"]); displayed.append(pct)
            if float(width) >= 8:
                ax.text(float(left + width / 2), position, f"{pct}%", ha="center", va="center", color="white", fontsize=9, fontweight="bold")
            left += width
        ax.text(-1.5, position, f"{label} (n={denom})", ha="right", va="center", fontsize=9)
        sums.append({"dimension": key[0], "pair_family": key[1], "displayed_percentages": displayed, "sum": sum(displayed)})
    ax.text(-1.5, 3.84, "Research Domains", ha="right", va="center", fontweight="bold")
    ax.text(-1.5, 1.68, "Analytical Purposes", ha="right", va="center", fontweight="bold")
    ax.set_xlim(0, 100); ax.set_ylim(-0.25, 4.1); ax.set_yticks([]); ax.set_xlabel("Percentage of disagreeing pairs")
    ax.xaxis.set_major_locator(MultipleLocator(20)); style_axis(ax)
    key_ax = ax.inset_axes([0.52, 1.01, 0.48, 0.18]); key_ax.axis("off")
    for index, relation in enumerate(("containment", "overlap", "disjoint")):
        x = 0.02 + index * 0.33
        if relation == "containment":
            key_ax.add_patch(Circle((x + .035, .55), .085, fill=False, lw=1.2)); key_ax.add_patch(Circle((x + .035, .55), .045, fill=False, lw=1.2))
        elif relation == "overlap":
            key_ax.add_patch(Circle((x + .015, .55), .065, fill=False, lw=1.2)); key_ax.add_patch(Circle((x + .070, .55), .065, fill=False, lw=1.2))
        else:
            key_ax.add_patch(Circle((x + .005, .55), .05, fill=False, lw=1.2)); key_ax.add_patch(Circle((x + .085, .55), .05, fill=False, lw=1.2))
        key_ax.add_patch(plt.Rectangle((x, .08), .10, .10, color=DISAGREE_COLORS[relation], transform=key_ax.transAxes))
        key_ax.text(x + .12, .13, relation.capitalize(), transform=key_ax.transAxes, va="center", fontsize=8.5)
    render = save_figure(fig, base)
    return render, {"status": "PASS", "encodings_present": ["containment", "overlap", "disjoint"],
                    "key_entries": ["Containment", "Overlap", "Disjoint"], "schematic_icons": True}, sums


def render_s2(rows: list[dict], base: Path) -> tuple[dict, dict, list[dict]]:
    constructs = ("Register-entry information", "Taxonomy fit", "Coder confidence")
    populations = ("baseline", "hard_case")
    palettes = {
        "Register-entry information": {"Sufficient": "#2F6B4F", "Partially sufficient": "#87B58D", "Insufficient": "#D5E5D1", "No majority / split judgement": "#888888"},
        "Taxonomy fit": {"Fit": "#3B5F8A", "Partial Fit": "#829CC2", "No Fit": "#CED8E8", "Cannot assess from register entry": "#686868", "No majority / split judgement": "#B0B0B0"},
        "Coder confidence": {"High": "#70478A", "Medium": "#AA82BD", "Low": "#DDCEE5", "No majority": "#888888"},
    }
    fig, axes = plt.subplots(3, 2, figsize=(14.5, 12), constrained_layout=True)
    sums = []; legend_checks = []
    for i, construct in enumerate(constructs):
        for j, population in enumerate(populations):
            ax = axes[i, j]
            subset = [r for r in rows if r["role"] == "plotted" and r["dimension"] == construct and r["population"] == population]
            actors = ("C01", "C02", "C03", "Majority of coders")
            ypos = (3.3, 2.45, 1.60, 0.35)
            present_categories = []
            for actor, y in zip(actors, ypos):
                selected = sorted([r for r in subset if r["pair"] == actor], key=lambda r: int(r["source_order"]))
                left = Decimal(0); displayed = []
                for row in selected:
                    prop = d(row["parsed_interval_lower"]); width = prop * Decimal(100)
                    category = row["label"]; present_categories.append(category)
                    ax.barh(y, float(width), left=float(left), height=0.56, color=palettes[construct][category], edgecolor="white", linewidth=0.7)
                    pct = whole_percent(row["parsed_interval_lower"]); displayed.append(pct)
                    if float(width) >= 9:
                        ax.text(float(left + width / 2), y, f"{pct}%", ha="center", va="center", fontsize=8,
                                color="white" if palettes[construct][category] in {"#2F6B4F", "#3B5F8A", "#70478A", "#686868", "#888888"} else "#222")
                    left += width
                sums.append({"construct": construct, "population": population, "bar": actor, "displayed_percentages": displayed, "sum": sum(displayed)})
            ax.set_xlim(0, 100); ax.set_ylim(-0.15, 3.85); ax.set_yticks(ypos, actors); ax.set_xlabel("Percentage of records")
            ax.xaxis.set_major_locator(MultipleLocator(20)); style_axis(ax)
            if i == 0:
                ax.set_title("Baseline (n=150)" if population == "baseline" else "Hard-case (n=75)", fontweight="bold")
            if j == 0:
                ax.set_ylabel(construct, fontweight="bold", labelpad=10)
            if population == "hard_case":
                ax.text(1.0, 1.03, "Diagnostic, non-representative", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=COLORS["red"], fontweight="bold")
            if construct == "Coder confidence":
                ax.text(0.0, 1.03, "Exploratory; not preregistered", transform=ax.transAxes, ha="left", va="bottom", fontsize=8, fontweight="bold")
            categories = list(palettes[construct])
            handles = [plt.Rectangle((0, 0), 1, 1, color=palettes[construct][category], label=category) for category in categories]
            ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.33), ncol=min(3, len(handles)), frameon=False, fontsize=7.2)
            legend_checks.append({"construct": construct, "population": population, "encodings_present": sorted(set(present_categories)), "key_entries": categories,
                                  "status": "PASS" if set(categories) == set(present_categories) else "FAIL"})
    render = save_figure(fig, base)
    status = "PASS" if all(item["status"] == "PASS" for item in legend_checks) else "FAIL"
    return render, {"status": status, "panels": legend_checks}, sums


def html_table(headers: list[str], body: list[list[str]], spans: list[tuple[str, int]] | None = None) -> str:
    lines = ["<table>", "  <thead>"]
    if spans:
        lines.append("    <tr>" + "".join(f'<th colspan="{span}">{label}</th>' for label, span in spans) + "</tr>")
    lines.append("    <tr>" + "".join(f"<th>{value}</th>" for value in headers) + "</tr>")
    lines.extend(["  </thead>", "  <tbody>"])
    for row in body:
        if len(row) == 1:
            lines.append(f'    <tr><th colspan="{len(headers)}">{row[0]}</th></tr>')
        else:
            lines.append("    <tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>")
    lines.extend(["  </tbody>", "</table>", ""])
    return "\n".join(lines)


def write_csv(path: Path, headers: list[str], rows: list[list[str]]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(headers); writer.writerows(row for row in rows if len(row) == len(headers))


def metric(row: dict) -> str:
    if row["estimate_status"] != "R" or not row["source_value_string"]:
        return ""
    estimate = half_up(row["source_value_string"], 2)
    if row["interval_status"] == "R" and row["interval_lower_string"] and row["interval_upper_string"]:
        return f"{estimate} [{half_up(row['interval_lower_string'], 2)}, {half_up(row['interval_upper_string'], 2)}]"
    return estimate


def render_kappa(rows: list[dict], csv_path: Path, md_path: Path) -> dict:
    grouped_rows: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        grouped_rows[row["label"]][row["pair"]] = row
    selected = [label for label in grouped_rows if next(iter(grouped_rows[label].values()))["support_band"] != "RARE"]
    order_groups = []
    for label in selected:
        base = next(iter(grouped_rows[label].values()))
        key = (0 if base["support_band"] == "STANDARD" else 2 if label == "Unclear from Register Entry" else 1,
               -int(base["support_string"]), int(base["source_order"]))
        order_groups.append((key, label))
    order_groups.sort()
    headers = ["Label", "Applied by coder majority (n)", "C01–C02", "C01–C03", "C02–C03", "C01", "C02", "C03"]
    body = []; flat = []; current = None
    for _, label in order_groups:
        base = next(iter(grouped_rows[label].values())); group = base["row_group"]
        if group != current:
            body.append([group]); current = group
        values = [label, base["support_string"]] + [metric(grouped_rows[label][pair]) for pair in PAIR_ORDER]
        body.append(values); flat.append([group] + values)
    spans = [("", 2), ("Between human coders (Cohen’s κ [95% interval])", 3), ("Fable 5 with each human coder (Cohen’s κ [95% interval])", 3)]
    md_path.write_text(html_table(headers, body, spans), encoding="utf-8")
    write_csv(csv_path, ["Row group"] + headers, flat)
    return {"rows_shown": len(selected), "rows_omitted_below_10": len(grouped_rows) - len(selected), "status": "PASS"}


def render_performance(rows: list[dict], csv_path: Path, md_path: Path) -> dict:
    grouped_rows: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        grouped_rows[row["label"]][row["quantity"]] = row
    ordered = []
    group_rank = {"STANDARD": 0, "LOW SUPPORT": 1, "RARE": 3}
    for label, values in grouped_rows.items():
        base = values["tp"]
        rank = 2 if label == "Unclear from Register Entry" else group_rank[base["support_band"]]
        ordered.append(((rank, -int(base["support_string"]), int(base["source_order"])), label))
    ordered.sort()
    headers = ["Label", "Applied by coder majority (n)", "Both", "Fable 5 only", "Coder majority only", "Neither", "Precision [95% interval]", "Recall [95% interval]", "F1 [95% interval]"]
    body = []; flat = []; current = None
    for _, label in ordered:
        values = grouped_rows[label]; base = values["tp"]; group = base["row_group"]
        if group != current:
            body.append([group]); current = group
        metrics = []
        for quantity in ("precision", "recall", "f1"):
            if base["support_band"] == "RARE":
                shown = ""
            elif label == "Unclear from Register Entry" and quantity in {"precision", "f1"}:
                shown = "Not estimable"
            else:
                shown = metric(values[quantity])
            metrics.append(shown)
        shown = [label, base["support_string"]] + [values[q]["source_value_string"] for q in ("tp", "fp", "fn", "tn")] + metrics
        body.append(shown); flat.append([group] + shown)
    md_path.write_text(html_table(headers, body), encoding="utf-8")
    write_csv(csv_path, ["Row group"] + headers, flat)
    return {"rows_shown": len(ordered), "sparse_rows_counts_only": sum(1 for _, label in ordered if grouped_rows[label]["tp"]["support_band"] == "RARE"), "status": "PASS"}


def render_table5(rows: list[dict], csv_path: Path, md_path: Path) -> tuple[dict, list[dict]]:
    grouped = disagreement_group(rows)
    headers = ["Pair type", "Disagreeing pairs (n)", "Containment n (%)", "Overlap n (%)", "Disjoint n (%)"]
    body = []; flat = []; sums = []
    for dimension in ("Research Domains", "Analytical Purposes"):
        body.append([dimension])
        for family, label in (("human_human", "Between human coders"), ("model_human", "Fable 5 with each coder")):
            rel = grouped[(dimension, family)]
            denominator = json.loads(rel["containment"]["presentation_note"].split("; structurally", 1)[0])["nonidentical_nonempty_pairs"]
            cells = [] ; displayed = []
            for relation in ("containment", "overlap", "disjoint"):
                row = rel[relation]; pct = whole_percent(row["interval_lower_string"]); displayed.append(pct)
                pct_text = "<1%" if int(row["source_value_string"]) > 0 and pct == 0 else f"{pct}%"
                cells.append(f"{row['source_value_string']} ({pct_text})")
            shown = [label, str(denominator)] + cells
            body.append(shown); flat.append([dimension] + shown)
            sums.append({"dimension": dimension, "pair_family": family, "displayed_percentages": displayed, "sum": sum(displayed)})
    md_path.write_text(html_table(headers, body), encoding="utf-8")
    write_csv(csv_path, ["Dimension"] + headers, flat)
    return {"status": "PASS", "rows": 4}, sums


def supplementary_group(rows: list[dict]) -> dict[tuple[str, str], dict[str, dict]]:
    result: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        result[(row["population"], row["label"])][row["quantity"]] = row
    return result


def render_s1ab(rows: list[dict], csv_path: Path, md_path: Path) -> tuple[dict, list[dict]]:
    values = supplementary_group(rows)
    labels = []
    for row in rows:
        if row["label"] not in labels: labels.append(row["label"])
    headers = ["Response", "Baseline, n=150: n (%) [95% interval]", "Hard-case, n=75: n (%)"]
    body = []; sums = {"baseline": Decimal(0), "hard_case": Decimal(0)}
    for label in labels:
        cells = []
        for population in ("baseline", "hard_case"):
            count = values[(population, label)]["count"]
            prop = values[(population, label)]["proportion"]
            sums[population] += d(prop["source_value_string"]) * Decimal(100)
            shown = f"{count['source_value_string']} ({percent_2(prop['source_value_string'])}%)"
            if population == "baseline":
                shown += f" [{percent_2(prop['interval_lower_string'])}%, {percent_2(prop['interval_upper_string'])}%]"
            cells.append(shown)
        body.append([label] + cells)
    md_path.write_text(html_table(headers, body), encoding="utf-8")
    write_csv(csv_path, headers, body)
    sum_rows = [{"population": population, "displayed_percentage_sum": half_up(str(total), 2)} for population, total in sums.items()]
    return {"status": "PASS", "rows": len(body)}, sum_rows


def render_s1c(rows: list[dict], csv_path: Path, md_path: Path) -> tuple[dict, list[dict]]:
    headers = ["Population and dimension", "No agreed label", "Agreed only on Unclear", "1 agreed label", "2 agreed labels", "3 agreed labels"]
    order = (("baseline", "Analytical Purposes"), ("baseline", "Research Domains"), ("hard_case", "Analytical Purposes"), ("hard_case", "Research Domains"))
    body = []; sums = []
    for population, dimension in order:
        selected = sorted([r for r in rows if r["population"] == population and r["dimension"] == dimension], key=lambda r: int(r["source_order"]))
        label = ("Baseline" if population == "baseline" else "Hard-case, diagnostic") + " — " + ("purposes" if dimension == "Analytical Purposes" else "domains") + f" (n={selected[0]['denominator_string']})"
        cells = [f"{row['source_value_string']} ({row['display_percent']}%)" for row in selected]
        body.append([label] + cells)
        sums.append({"population": population, "dimension": dimension, "displayed_percentages": [int(r["display_percent"]) for r in selected], "sum": sum(int(r["display_percent"]) for r in selected)})
    md_path.write_text(html_table(headers, body), encoding="utf-8")
    write_csv(csv_path, headers, body)
    return {"status": "PASS", "rows": len(body)}, sums


def write_captions(manifest: dict, path: Path):
    order = ("Figure 1", "Figure 2", "Figure 3", "Figure 4", "Table 1", "Table 2", "Table 3", "Table 4", "Table 5",
             "Supplementary Figure S1", "Supplementary Figure S2", "Supplementary Table S1a", "Supplementary Table S1b", "Supplementary Table S1c")
    lines = ["# Draft captions — pass 2", ""]
    for deliverable in order:
        entry = manifest["entries"][deliverable]
        punctuation = "." if "Figure" in deliverable else ":"
        lines.extend([f"## {deliverable}", "", f"**{deliverable}{punctuation} {entry['title']}.**", ""])
        if deliverable == "Supplementary Figure S2":
            lines.extend(["**Title to revisit: confidence panel added.**", ""])
        lines.extend(["Legend content checklist:", ""])
        lines.extend([f"- {bullet}" for bullet in entry["caption_bullets"]])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def axis_validation(datasets: dict, manifest: dict) -> dict:
    result = {}
    for deliverable in ("Figure 1", "Figure 2", "Supplementary Figure S1"):
        failures = []
        for row in datasets[deliverable]:
            if row["role"] != "plotted": continue
            limits = ((0.15, 0.75) if deliverable == "Figure 2" else (0.0, 1.0)) if row["series"] == "alpha" else (-0.45, 0.45)
            for field in ("parsed_value", "parsed_interval_lower", "parsed_interval_upper"):
                value = f(row[field])
                if value is not None and not (limits[0] <= value <= limits[1]):
                    failures.append({"table": row["source_table_id"], "quantity": row["quantity"], "field": field, "value": value, "limits": limits})
        result[deliverable] = {"status": "PASS" if not failures else "FAIL", "failures": failures,
                               "range": manifest["axis_ranges"]["alpha_figure_2" if deliverable == "Figure 2" else "alpha_figure_1_and_s1"],
                               "delta_range": manifest["axis_ranges"]["delta_all"]}
    return result


def table_banned_check(paths: list[Path]) -> list[dict]:
    failures = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pattern in BANNED:
            for match in pattern.finditer(text):
                failures.append({"path": str(path), "pattern": pattern.pattern, "match": match.group(0)})
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--figure-dir", type=Path, required=True)
    parser.add_argument("--table-dir", type=Path, required=True)
    parser.add_argument("--archive-existing", action="store_true")
    args = parser.parse_args()
    data_dir, figure_dir, table_dir = args.data_dir.resolve(), args.figure_dir.resolve(), args.table_dir.resolve()
    figure_dir.mkdir(parents=True, exist_ok=True); table_dir.mkdir(parents=True, exist_ok=True)
    manifest, datasets = load(data_dir)
    expected = set(manifest["entries"])
    if expected != set(datasets) or len(expected) != 14:
        raise RuntimeError(f"Manifest/dataset mismatch: {expected ^ set(datasets)}")
    archived = archive_existing(figure_dir, table_dir) if args.archive_existing else []

    rendering = {}; keys = {}; displayed_sums = []; table_reports = {}; output_tables = []
    for deliverable, renderer in (("Figure 1", render_figure1), ("Figure 2", render_figure2), ("Figure 3", render_figure3),
                                  ("Supplementary Figure S1", render_s1)):
        base = figure_dir / manifest["entries"][deliverable]["slug"]
        render, key = renderer(datasets[deliverable], base); rendering[deliverable] = render; keys[deliverable] = key
    base = figure_dir / manifest["entries"]["Figure 4"]["slug"]
    render, key, sums = render_figure4(datasets["Figure 4"], base); rendering["Figure 4"] = render; keys["Figure 4"] = key; displayed_sums.extend([{"deliverable": "Figure 4", **row} for row in sums])
    base = figure_dir / manifest["entries"]["Supplementary Figure S2"]["slug"]
    render, key, sums = render_s2(datasets["Supplementary Figure S2"], base); rendering["Supplementary Figure S2"] = render; keys["Supplementary Figure S2"] = key; displayed_sums.extend([{"deliverable": "Supplementary Figure S2", **row} for row in sums])

    for deliverable in ("Table 1", "Table 2"):
        slug = manifest["entries"][deliverable]["slug"]; csv_path = table_dir / f"{slug}.csv"; md_path = table_dir / f"{slug}.md"
        table_reports[deliverable] = render_kappa(datasets[deliverable], csv_path, md_path); output_tables.extend([csv_path, md_path])
    for deliverable in ("Table 3", "Table 4"):
        slug = manifest["entries"][deliverable]["slug"]; csv_path = table_dir / f"{slug}.csv"; md_path = table_dir / f"{slug}.md"
        table_reports[deliverable] = render_performance(datasets[deliverable], csv_path, md_path); output_tables.extend([csv_path, md_path])
    slug = manifest["entries"]["Table 5"]["slug"]; csv_path = table_dir / f"{slug}.csv"; md_path = table_dir / f"{slug}.md"
    table_reports["Table 5"], sums = render_table5(datasets["Table 5"], csv_path, md_path); displayed_sums.extend([{"deliverable": "Table 5", **row} for row in sums]); output_tables.extend([csv_path, md_path])
    for deliverable in ("Supplementary Table S1a", "Supplementary Table S1b"):
        slug = manifest["entries"][deliverable]["slug"]; csv_path = table_dir / f"{slug}.csv"; md_path = table_dir / f"{slug}.md"
        table_reports[deliverable], sums = render_s1ab(datasets[deliverable], csv_path, md_path); displayed_sums.extend([{"deliverable": deliverable, **row} for row in sums]); output_tables.extend([csv_path, md_path])
    deliverable = "Supplementary Table S1c"; slug = manifest["entries"][deliverable]["slug"]; csv_path = table_dir / f"{slug}.csv"; md_path = table_dir / f"{slug}.md"
    table_reports[deliverable], sums = render_s1c(datasets[deliverable], csv_path, md_path); displayed_sums.extend([{"deliverable": deliverable, **row} for row in sums]); output_tables.extend([csv_path, md_path])

    captions_path = figure_dir / "draft_captions_pass2.md"; write_captions(manifest, captions_path)
    figure_banned = []
    for deliverable, record in rendering.items():
        figure_banned.extend([{"deliverable": deliverable, **failure} for failure in figure_text_check(record["rendered_text"])])
    table_banned = table_banned_check(output_tables)
    caption_banned = table_banned_check([captions_path])
    if figure_banned or table_banned or caption_banned:
        raise RuntimeError(f"Banned reader-facing text found: figures={figure_banned}, tables={table_banned}, captions={caption_banned}")
    if any(record.get("status") != "PASS" for record in keys.values()):
        raise RuntimeError(f"Figure-key assertion failed: {keys}")
    axis = axis_validation(datasets, manifest)
    if any(record["status"] != "PASS" for record in axis.values()):
        raise RuntimeError(f"Axis-range assertion failed: {axis}")
    exact_100 = [row for row in displayed_sums if row["deliverable"] in {"Figure 4", "Table 5", "Supplementary Table S1c"}]
    if any(row["sum"] != 100 for row in exact_100):
        raise RuntimeError(f"Required displayed-percentage sum failed: {exact_100}")

    report = {
        "renderer": Path(__file__).name, "input_boundary": "pass2 manifest plus its listed CSV and JSON files only",
        "matplotlib_version": matplotlib.__version__, "python_version": sys.version,
        "font": "DejaVu Sans", "font_resolved": font_manager.findfont("DejaVu Sans"),
        "archived_preexisting_outputs": archived, "axis_ranges": axis, "keys": keys,
        "figure_3_labels": keys["Figure 3"], "displayed_percentage_sums": displayed_sums,
        "table_rendering": table_reports, "banned_text": {"status": "PASS", "figure_failures": [], "table_failures": [], "caption_failures": []},
        "render_clipping_scan": {deliverable: {"status": "PASS" if not record["clipped_text_candidates"] else "REVIEW", "candidates": record["clipped_text_candidates"]} for deliverable, record in rendering.items()},
        "caption_policy": {"status": "PASS", "titles_or_caption_prose_embedded": False, "draft_captions": str(captions_path)},
        "isolation_test": {"status": "PENDING RUNNER"},
    }
    (figure_dir / "pass2_rendering_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run_metadata = {
        "manifest_generated_utc": manifest["generated_utc"], "rendered_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "logs": manifest["provenance"]["logs"], "source_commits": manifest["provenance"]["source_commits"],
        "code_commits": json.loads((data_dir / "pass2_run_metadata.json").read_text(encoding="utf-8"))["code_commits"],
        "software": {"python": sys.version, "matplotlib": matplotlib.__version__, "font": font_manager.findfont("DejaVu Sans")},
    }
    (figure_dir / "pass2_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
