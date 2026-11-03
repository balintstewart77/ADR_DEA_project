"""Stage 2 renderer for pass 4.

Only the pass-4 manifest and the CSV/JSON files it lists are analytical inputs.
Carried-forward figures are drawn with the pass-3 functions unchanged; this
module adds layout for the new deliverables and performs display rounding only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402  (sets the shared rcParams)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator  # noqa: E402

from figure_style import COLOURS  # noqa: E402


ARCHIVE_NAME = "pass4_preexisting_7e77c47"
DIMENSIONS = p3.DIMENSIONS
TAGS = DIMENSIONS[2:]
UNCLEAR = "Unclear from Register Entry"
UNCLEAR_NAME = "Unclear from Register Entry (declined to classify)"
CODERS = ("C01", "C02", "C03")
RATERS = (*CODERS, "Fable 5")
FIGURE1_LABELS = {
    "baseline": "Random baseline, n=150 (primary analysis)",
    "baseline_strict_sufficient": "Register-sufficient subset, n=92 (preregistered sensitivity analysis)",
}
# Figure 3 encodings: coders are small hollow shapes in one neutral colour; Fable 5 is the only
# filled, coloured and larger marker.
CODER_MARKERS = {"C01": "o", "C02": "s", "C03": "^"}
CODER_COLOUR = "#3D3D3D"
CODER_AREA = 20
CODER_EDGE_PT = 0.95
FABLE_MARKER = "D"
FABLE_AREA = 46
FABLE_COLOUR = COLOURS["baseline"]
RANGE_COLOUR = "#9A9A9A"
RANGE_PT = 1.2
ROW_PITCH_PT = 18.0
OFFSET_PT = 4.0          # vertical step between markers sharing or nearly sharing a count
UNCLEAR_GAP = 0.8
COUNT_LIMITS = (-1.5, 70.5)
S4_MARKERS = {"exact_set_proportion": ("o", True), "mean_jaccard": ("s", False)}
S4_COLOUR = "#3D3D3D"
PRE_EXISTING_FIGURES = {
    "figure_1_panel_agreement_replacement", "figure_2_coder_ratings_baseline", "figure_3_sufficiency_sensitivity",
    "figure_4_label_application", "supplementary_figure_s1_baseline_vs_hardcase",
    "supplementary_figure_s2_hardcase_ratings_confidence", "supplementary_figure_s3_disagreement_composition",
}
HYPHEN_BEFORE_DIGIT = re.compile(r"(?<!COVID)(?<!GPT)-(?=\d)")


def load(data_dir: Path) -> tuple[dict, dict[str, list[dict]]]:
    manifest = json.loads((data_dir / "pass4_deliverable_manifest.json").read_text(encoding="utf-8"))
    datasets = {}
    for deliverable, entry in manifest["entries"].items():
        with (data_dir / entry["inputs"]["data"]).open(newline="", encoding="utf-8") as handle:
            datasets[deliverable] = list(csv.DictReader(handle))
    return manifest, datasets


def archive_existing(figure_dir: Path) -> list[dict]:
    archive = figure_dir / "archive" / ARCHIVE_NAME
    names = [f"{slug}{suffix}" for slug in sorted(PRE_EXISTING_FIGURES) for suffix in (".png", ".svg")]
    names += ["draft_captions_pass2.md", "pass3_rendering_report.json", "pass3_run_metadata.json"]
    moved = []
    for name in names:
        source, target = figure_dir / name, archive / name
        if not source.is_file() or target.is_file():
            continue  # already archived by an earlier pass-4 run; the active file is a pass-4 output
        archive.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)
        moved.append({"from": name, "to": str(target.relative_to(figure_dir.parent.parent)).replace("\\", "/")})
    return moved


def thousands(value: int | str) -> str:
    return f"{int(value):,}"


def whole_percent_text(numerator: int, denominator: int) -> str:
    """H.10 whole percentages; values in [99.5%, 100%) display as >99% so they never read as complete agreement."""
    value = Decimal(numerator) / Decimal(denominator)
    if numerator != denominator and p3.whole_percent(str(value)) == 100:
        return ">99%"
    return p3.percent_text(str(value), numerator)


# ---------------------------------------------------------------- replacement figures
def replacement_handles(populations: tuple[str, ...], labels: dict[str, str]) -> list[Line2D]:
    return [Line2D([0], [0], marker="o", color=p3.POPULATION[p]["color"],
                   markerfacecolor="none" if p3.POPULATION[p]["hollow"] else p3.POPULATION[p]["color"],
                   markeredgecolor=p3.POPULATION[p]["color"], linewidth=1.2, label=labels[p]) for p in populations]


def matching_components(rows: list[dict], dimensions: tuple[str, ...]) -> dict[str, str]:
    """Read the component whose point estimate equals δ_min from figure data (one per dimension)."""
    result = {}
    for dimension in dimensions:
        notes = {r["presentation_note"].rsplit(": ", 1)[-1] for r in rows
                 if r["dimension"] == dimension and r["quantity"] == "delta_min" and r["series"] == "delta"}
        if len(notes) != 1:
            raise RuntimeError(f"δ_min matches different components across populations for {dimension}: {notes}")
        result[dimension] = notes.pop()
    return result


def render_figure1(rows: list[dict], base: Path):
    populations = ("baseline", "baseline_strict_sufficient")
    components = matching_components(rows, DIMENSIONS[:2])
    if set(components.values()) != {"delta_B"}:
        raise RuntimeError(f"Figure 1 annotation assumes δ_B; data give {components}")
    fig, axes, positions, delta = p3.replacement_figure(rows, DIMENSIONS[:2], populations, (0.15, 0.75), 4.55, True)
    handles = replacement_handles(populations, FIGURE1_LABELS)
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False, columnspacing=1.6, handletextpad=0.5)
    render = save_figure(fig, base, "Figure 1")
    return render, {"status": "PASS", "key_entries": [h.get_label() for h in handles],
                    "encodings_present": ["baseline filled (primary)", "register-sufficient subset hollow (sensitivity)"],
                    "row_positions": positions, "delta_min_rows": delta, "annotation_components": components}


def render_s3(rows: list[dict], base: Path):
    components = matching_components(rows, TAGS)
    if components != {"Demographic disparities / equity": "delta_B", "COVID-19 & Pandemic": "delta_A"}:
        raise RuntimeError(f"Supplementary Figure S3 annotation mapping differs from pass-3 rendering: {components}")
    fig, axes, positions, delta = p3.replacement_figure(rows, TAGS, ("baseline",), (0.0, 1.0), 3.75, True)
    counts = {}
    for index, dimension in enumerate(TAGS):
        selected = {r["support_string"] for r in rows if r["dimension"] == dimension}
        denominators = {r["sample_size"] for r in rows if r["dimension"] == dimension}
        if len(selected) != 1 or len(denominators) != 1:
            raise RuntimeError(f"Inconsistent tag count or denominator for {dimension}")
        count, denominator = selected.pop(), denominators.pop()
        counts[dimension] = {"coder_majority_positive": int(count), "records": int(denominator)}
        ax = axes[index][0]
        ax.annotate(f"Coder majority positive:\n{count} of {denominator} records", xy=(1, 0), xycoords=ax.yaxis.label,
                    xytext=(0, -4), textcoords="offset points", ha="right", va="top", fontsize=8.0, color="#333333",
                    multialignment="right")
    render = save_figure(fig, base, "Supplementary Figure S3")
    return render, {"status": "PASS", "key_entries": [], "encodings_present": ["baseline filled"], "row_positions": positions,
                    "delta_min_rows": delta, "annotation_components": components, "displayed_counts": counts}


def text_overlaps(fig) -> list[list[str]]:
    """Pairs of visible, non-empty text objects whose rendered boxes overlap."""
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    boxes = [(t.get_text(), t.get_window_extent(renderer)) for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text().strip()]
    return [[a, b] for i, (a, box_a) in enumerate(boxes) for b, box_b in boxes[i + 1:] if box_a.overlaps(box_b)]


def save_figure(fig, base: Path, name: str, **kwargs) -> dict:
    """Pass-3 save (H.1 and H.2 metrics), plus the text-overlap check for figures laid out in pass 4."""
    overlaps = text_overlaps(fig)
    render = p3.save_figure(fig, base, name, **kwargs)
    render["text_overlaps"] = overlaps
    return render


def row_alignment(keys: dict) -> dict:
    expected = {"alpha ABC": 0, "alpha LBC": 1, "alpha ALC": 2, "alpha ABL": 3, "delta_min": 0, "delta_A": 1, "delta_B": 2, "delta_C": 3}
    failures = [{"deliverable": deliverable, **row} for deliverable in ("Figure 1", "Supplementary Figure S1", "Supplementary Figure S3")
                for row in keys[deliverable]["row_positions"] if row["y"] != expected[row["quantity"]]]
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, "mapping": expected}


def delta_annotation_check(datasets: dict, keys: dict) -> dict:
    checks = []
    for deliverable in ("Figure 1", "Supplementary Figure S3"):
        rows = datasets[deliverable]
        for dimension, component in keys[deliverable]["annotation_components"].items():
            for population in sorted({r["population"] for r in rows if r["dimension"] == dimension}):
                keyed = {r["quantity"]: r for r in rows if r["dimension"] == dimension and r["population"] == population and r["series"] == "delta"}
                drawn = next(item for item in keys[deliverable]["delta_min_rows"] if item["dimension"] == dimension and item["population"] == population)["interval"]
                own = [keyed["delta_min"]["parsed_interval_lower"], keyed["delta_min"]["parsed_interval_upper"]]
                equal = p3.d(keyed["delta_min"]["parsed_value"]) == p3.d(keyed[component]["parsed_value"])
                checks.append({"deliverable": deliverable, "dimension": dimension, "population": population, "component": component,
                               "delta_min": keyed["delta_min"]["parsed_value"], "component_value": keyed[component]["parsed_value"],
                               "delta_min_interval_drawn": drawn, "status": "PASS" if equal and drawn == own else "FAIL"})
    failures = [c for c in checks if c["status"] != "PASS"]
    return {"status": "PASS" if not failures else "FAIL", "checks": checks, "failures": failures}


# ---------------------------------------------------------------- Figure 3
def label_table(rows: list[dict]) -> dict[str, list[dict]]:
    """One record per label: counts by rater, coder range and established order."""
    grouped: dict[tuple[str, str], dict] = {}
    for row in rows:
        record = grouped.setdefault((row["dimension"], row["label"]), {"dimension": row["dimension"], "label": row["label"],
                                                                       "order": int(row["source_order"]), "records": int(row["sample_size"])})
        if row["quantity"] == "label_application_count":
            record[row["pair"]] = int(row["parsed_value"])
        else:
            record[row["quantity"]] = int(row["parsed_value"])
    result = {}
    for dimension in DIMENSIONS[:2]:
        selected = [r for r in grouped.values() if r["dimension"] == dimension]
        substantive = sorted([r for r in selected if r["label"] != UNCLEAR], key=lambda r: r["order"])
        result[dimension] = substantive + [r for r in selected if r["label"] == UNCLEAR]
    return result


def marker_offsets(counts: dict[str, int], adjacent: int = 1) -> dict[str, float]:
    """Vertical offsets (multiples of the step) for markers whose counts are identical or adjacent.

    Raters are chained into clusters while consecutive sorted counts differ by at most
    ``adjacent``; members of a cluster are spread symmetrically in rater order.  Counts are
    never changed, and raters outside any cluster stay on the row's centre line.
    """
    ordered = sorted(counts, key=lambda rater: (counts[rater], RATERS.index(rater)))
    clusters: list[list[str]] = []
    for rater in ordered:
        if clusters and counts[rater] - counts[clusters[-1][-1]] <= adjacent:
            clusters[-1].append(rater)
        else:
            clusters.append([rater])
    offsets = {}
    for cluster in clusters:
        members = sorted(cluster, key=RATERS.index)
        for index, rater in enumerate(members):
            offsets[rater] = 0.0 if len(members) == 1 else index - (len(members) - 1) / 2
    return offsets


FIG3_TOP_IN, FIG3_GAP_IN, FIG3_BOTTOM_IN = 0.32, 0.42, 0.95  # panel title, gap between panels, x-axis and key
ROW_MARGIN = 0.62  # rows of space above the first and below the last label


def render_figure3(rows: list[dict], base: Path):
    data = label_table(rows)
    # Each panel spans its rows, the Unclear gap and the margins, so the row pitch is equal in both panels.
    spans = {dimension: len(records) - 1 + UNCLEAR_GAP + 2 * ROW_MARGIN for dimension, records in data.items()}
    rows_in = sum(spans.values()) * ROW_PITCH_PT / 72
    height = FIG3_TOP_IN + FIG3_GAP_IN + FIG3_BOTTOM_IN + rows_in
    fig = plt.figure(figsize=(p3.FIGURE_WIDTH, height))
    grid = fig.add_gridspec(2, 1, height_ratios=[spans[d] for d in DIMENSIONS[:2]], hspace=FIG3_GAP_IN / (rows_in / 2),
                            left=0.38, right=0.975, top=1 - FIG3_TOP_IN / height, bottom=FIG3_BOTTOM_IN / height)
    axes, panels, drawn = [], {}, []
    step = OFFSET_PT / ROW_PITCH_PT
    for index, dimension in enumerate(DIMENSIONS[:2]):
        ax = fig.add_subplot(grid[index, 0], sharex=axes[0] if axes else None)
        axes.append(ax)
        records = data[dimension]
        ypos = {}
        for k, record in enumerate(records):
            ypos[record["label"]] = k + UNCLEAR_GAP if record["label"] == UNCLEAR else k
        for record in records:
            y = ypos[record["label"]]
            counts = {rater: record[rater] for rater in RATERS}
            low, high = min(counts[c] for c in CODERS), max(counts[c] for c in CODERS)
            if (low, high) != (record["coder_min"], record["coder_max"]):
                raise RuntimeError(f"Coder range in figure data disagrees with coder counts: {record['label']}")
            ax.plot([low, high], [y, y], color=RANGE_COLOUR, linewidth=RANGE_PT, solid_capstyle="butt", zorder=2)
            offsets = marker_offsets(counts)
            fable_y = y + offsets["Fable 5"] * step
            ax.scatter(counts["Fable 5"], fable_y, s=FABLE_AREA, marker=FABLE_MARKER, facecolor=FABLE_COLOUR, edgecolor="black",
                       linewidth=0.6, zorder=3, clip_on=False)
            drawn.append({"dimension": dimension, "label": record["label"], "rater": "Fable 5", "x": counts["Fable 5"], "y": fable_y,
                          "area": FABLE_AREA})
            for coder in CODERS:
                coder_y = y + offsets[coder] * step
                ax.scatter(counts[coder], coder_y, s=CODER_AREA, marker=CODER_MARKERS[coder], facecolor="white", edgecolor=CODER_COLOUR,
                           linewidth=CODER_EDGE_PT, zorder=4, clip_on=False)
                drawn.append({"dimension": dimension, "label": record["label"], "rater": coder, "x": counts[coder], "y": coder_y,
                              "area": CODER_AREA})
        ax.set_yticks([ypos[r["label"]] for r in records])
        ax.set_yticklabels([UNCLEAR_NAME if r["label"] == UNCLEAR else r["label"] for r in records])
        ax.set_ylim(ypos[UNCLEAR] + ROW_MARGIN, -ROW_MARGIN)
        ax.set_xlim(*COUNT_LIMITS)
        ax.xaxis.set_major_locator(FixedLocator(range(0, 71, 10)))
        ax.tick_params(labelsize=8.0, length=3)
        ax.tick_params(axis="y", length=0, pad=6)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#E7E7E7", linewidth=0.55, zorder=0)
        ax.axvline(0, color="#9E9E9E", linewidth=0.8, zorder=1)
        if index == 0:
            ax.spines["bottom"].set_visible(False)
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
        else:
            ax.set_xlabel("Records labelled (of 150 random-baseline records)", fontsize=8.5)
        panels[dimension] = {"ax": ax, "records": records, "ypos": ypos}
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    widest = max(t.get_window_extent(renderer).width for ax in axes for t in ax.get_yticklabels())
    dpi = fig.dpi
    grid.update(left=(widest + 6 * dpi / 72 + 10 * dpi / 72) / (p3.FIGURE_WIDTH * dpi))
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    for dimension, ax in zip(DIMENSIONS[:2], axes):
        ax.set_title(dimension, loc="left", fontweight="bold", fontsize=9.0, pad=5,
                     x=-(widest + 6 * dpi / 72) / ax.get_window_extent(renderer).width)
    handles = [Line2D([], [], marker=CODER_MARKERS[c], linestyle="none", markersize=math.sqrt(CODER_AREA), markerfacecolor="white",
                      markeredgecolor=CODER_COLOUR, markeredgewidth=CODER_EDGE_PT, label=c) for c in CODERS]
    handles.append(Line2D([], [], marker=FABLE_MARKER, linestyle="none", markersize=math.sqrt(FABLE_AREA), markerfacecolor=FABLE_COLOUR,
                          markeredgecolor="black", markeredgewidth=0.6, label="Fable 5"))
    handles.append(Line2D([], [], color=RANGE_COLOUR, linewidth=RANGE_PT, label="Range across the three coders"))
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.012), ncol=5, frameon=False, fontsize=8.0,
               handletextpad=0.4, columnspacing=1.4)
    checks = verify_figure3(fig, panels, drawn)
    render = save_figure(fig, base, "Figure 3", tight=False)
    return render, checks


def verify_figure3(fig, panels: dict, drawn: list[dict]) -> dict:
    """Read marks back from the artists and check positions, ranges, labels and marker visibility."""
    fig.canvas.draw()
    failures, rows_checked = [], 0
    for dimension, panel in panels.items():
        ax = panel["ax"]
        ticks = [t.get_text() for t in ax.get_yticklabels()]
        expected = [UNCLEAR_NAME if r["label"] == UNCLEAR else r["label"] for r in panel["records"]]
        if ticks != expected:
            failures.append({"dimension": dimension, "issue": "tick labels", "ticks": ticks})
        offsets = sorted((tuple(map(float, c.get_offsets()[0])), c.get_sizes()[0]) for c in ax.collections)
        for item in (i for i in drawn if i["dimension"] == dimension):
            if not any(abs(x - item["x"]) < 1e-9 and abs(y - item["y"]) < 1e-9 and size == item["area"] for (x, y), size in offsets):
                failures.append({"dimension": dimension, "issue": "marker not found at its count", **item})
        lines = [line for line in ax.get_lines() if line.get_color() == RANGE_COLOUR]
        for record in panel["records"]:
            rows_checked += 1
            y = panel["ypos"][record["label"]]
            line = [ln for ln in lines if abs(float(ln.get_ydata()[0]) - y) < 1e-9]
            if len(line) != 1 or sorted(map(float, line[0].get_xdata())) != [record["coder_min"], record["coder_max"]]:
                failures.append({"dimension": dimension, "issue": "range line", "label": record["label"]})
        # visibility: no marker's centre lies inside another marker's footprint in the same row
        transform = ax.transData
        same_panel = [i for i in drawn if i["dimension"] == dimension]
        for a_index, a in enumerate(same_panel):
            for b in same_panel[a_index + 1:]:
                if a["label"] != b["label"]:
                    continue
                ax_, ay_ = transform.transform((a["x"], a["y"])); bx_, by_ = transform.transform((b["x"], b["y"]))
                radius = max(math.sqrt(a["area"]), math.sqrt(b["area"])) / 2 * fig.dpi / 72
                if math.hypot(ax_ - bx_, ay_ - by_) < radius:
                    failures.append({"dimension": dimension, "issue": "marker hidden", "label": a["label"], "raters": [a["rater"], b["rater"]]})
        if any(type(artist).__name__ in {"ErrorbarContainer", "PolyCollection"} for artist in ax.containers + ax.collections):
            failures.append({"dimension": dimension, "issue": "interval-style artist present"})
    offset_rows = sorted({(i["dimension"], i["label"]) for i in drawn if abs(i["y"] - panels[i["dimension"]]["ypos"][i["label"]]) > 1e-9})
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, "rows_checked": rows_checked,
            "markers_checked": len(drawn), "rows_with_vertical_offsets": [list(r) for r in offset_rows],
            "fable_area_pt2": FABLE_AREA, "coder_area_pt2": CODER_AREA, "range_encoding": "observed min–max of three coders; no interval artists",
            "key_entries": ["C01", "C02", "C03", "Fable 5", "Range across the three coders"], "encodings_present": ["coder shapes", "Fable 5 diamond", "coder range line"]}


# ---------------------------------------------------------------- Supplementary Figure S4
S4_PANELS = (
    ("repeatability", "A. Same-model repeatability: two independent Fable 5 runs",
     "Fixed sample of 201 records ({adjudicated} purposively selected, {random} random); same model, prompt, taxonomy and inputs"),
    ("cross_model", "B. Cross-model agreement: Fable 5 versus GPT-5.5",
     "Frozen register of 1,308 records; GPT-5.5 given the production prompt without model-specific adaptation"),
)
S4_ROWS = (
    ("Research Domains", "exact_set_proportion", "Research Domains: exact-set agreement"),
    ("Research Domains", "mean_jaccard", "Research Domains: mean Jaccard"),
    ("Analytical Purposes", "exact_set_proportion", "Analytical Purposes: exact-set agreement"),
    ("Analytical Purposes", "mean_jaccard", "Analytical Purposes: mean Jaccard"),
)


def s4_values(rows: list[dict]) -> dict:
    values: dict = defaultdict(dict)
    for row in rows:
        values[(row["series"], row["dimension"])][row["quantity"]] = row
    return values


def render_s4(rows: list[dict], base: Path):
    values = s4_values(rows)
    strata = {key.split(":", 1)[1]: int(row["parsed_value"]) for key, row in values[("repeatability", "Sample composition")].items()}
    fig = plt.figure(figsize=(p3.FIGURE_WIDTH, 4.55))
    grid = fig.add_gridspec(2, 1, hspace=0.95, left=0.34, right=0.80, top=0.87, bottom=0.17)
    labels_drawn, checks, axes, headings = [], [], [], []
    for index, (series, title, subtitle) in enumerate(S4_PANELS):
        ax = fig.add_subplot(grid[index, 0]); axes.append(ax)
        for y, (dimension, quantity, row_label) in enumerate(S4_ROWS):
            row = values[(series, dimension)][quantity]
            value = float(row["parsed_value"])
            marker, filled = S4_MARKERS[quantity]
            ax.plot([0, value], [y, y], color="#D9D9D9", linewidth=1.0, zorder=1, solid_capstyle="butt")
            ax.scatter(value, y, s=30, marker=marker, facecolor=S4_COLOUR if filled else "white", edgecolor=S4_COLOUR, linewidth=1.0, zorder=3)
            shown = p3.half_up(row["source_value_string"], 2)
            if quantity == "exact_set_proportion":
                numerator, denominator = row["derivation_operands"].split("/")
                text = f"{shown} ({thousands(numerator)}/{thousands(denominator)})"
            else:
                text = f"{shown} (n={thousands(row['sample_size'])})"
            ax.annotate(text, xy=(1.0, y), xycoords=("axes fraction", "data"), xytext=(8, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=8.0, annotation_clip=False)
            labels_drawn.append({"panel": series, "row": row_label, "text": text, "value": value})
            checks.append(abs(Decimal(shown) - Decimal(row["source_value_string"])) <= Decimal("0.005"))
        ax.set_yticks(range(len(S4_ROWS)), [r[2] for r in S4_ROWS])
        ax.set_ylim(len(S4_ROWS) - 0.4, -0.6)
        ax.set_xlim(0, 1.0)
        ax.xaxis.set_major_locator(FixedLocator([0, 0.2, 0.4, 0.6, 0.8, 1.0]))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(p3.minus_tick))
        p3.style_axis(ax)
        ax.tick_params(axis="y", length=0, labelsize=8.0)
        ax.set_xlabel("Agreement (0–1)", fontsize=8.5)
        headings.append(ax.annotate(title, xy=(0, 1), xycoords="axes fraction", xytext=(0, 26), textcoords="offset points",
                                    ha="left", va="bottom", fontsize=9.0, fontweight="bold"))
        headings.append(ax.annotate(subtitle.format(**strata), xy=(0, 1), xycoords="axes fraction", xytext=(0, 14), textcoords="offset points",
                                    ha="left", va="bottom", fontsize=8.0, color="#333333"))
    # Left margin from the widest row label; headings align with the left edge of the row labels.
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    widest = max(t.get_window_extent(renderer).width for ax in axes for t in ax.get_yticklabels())
    left = (widest + 4 * fig.dpi / 72 + 8 * fig.dpi / 72) / (p3.FIGURE_WIDTH * fig.dpi)
    grid.update(left=left, right=0.79)  # direct labels sit to the right of the 0–1 axis
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    shift = -(widest + 4 * fig.dpi / 72) / axes[0].get_window_extent(renderer).width
    for heading in headings:
        heading.xy = (shift, 1)
    handles = [Line2D([], [], marker="o", linestyle="none", markersize=math.sqrt(30), markerfacecolor=S4_COLOUR, markeredgecolor=S4_COLOUR,
                      label="Exact-set agreement (records with identical label sets)"),
               Line2D([], [], marker="s", linestyle="none", markersize=math.sqrt(30), markerfacecolor="white", markeredgecolor=S4_COLOUR,
                      label="Mean Jaccard")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False, fontsize=8.0, handletextpad=0.4)
    render = save_figure(fig, base, "Supplementary Figure S4")
    status = "PASS" if all(checks) and len(labels_drawn) == 8 else "FAIL"
    return render, {"status": status, "direct_labels": labels_drawn, "intervals_drawn": 0, "panels": [p[0] for p in S4_PANELS],
                    "sample_composition": strata, "key_entries": [h.get_label() for h in handles],
                    "encodings_present": ["exact-set filled circle", "mean Jaccard hollow square"]}


# ---------------------------------------------------------------- tables
def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle); writer.writerow(headers); writer.writerows(row for row in rows if len(row) == len(headers))


PLACEMENT_TEXT = {"above_all_coders": "More than every coder", "below_all_coders": "Fewer than every coder", "within_coder_range": "Within coder range"}


def render_source_table(rows: list[dict], csv_path: Path, md_path: Path) -> dict:
    data = label_table(rows)
    lineage = {(r["dimension"], r["label"], r["pair"]): r for r in rows if r["quantity"] == "label_application_count"}
    headers = ["Dimension", "Label", "C01", "C02", "C03", "Fable 5", "Coder minimum", "Coder maximum", "Fable 5 relative to coders",
               "Population", "Records (denominator)", "Coder-count source", "Fable 5 count source"]
    body, flat = [], []
    for dimension in DIMENSIONS[:2]:
        body.append([dimension])
        for record in data[dimension]:
            fable = record["Fable 5"]
            placement = "above_all_coders" if fable > record["coder_max"] else "below_all_coders" if fable < record["coder_min"] else "within_coder_range"
            fable_row = lineage[(dimension, record["label"], "Fable 5")]
            coder_row = lineage[(dimension, record["label"], "C01")]
            shown = [dimension, record["label"]] + [str(record[r]) for r in RATERS] + [str(record["coder_min"]), str(record["coder_max"]),
                     PLACEMENT_TEXT[placement], "Random baseline", str(record["records"]),
                     f"{coder_row['source_table_id']} (exploratory descriptive)", f"{fable_row['source_table_id']} model-positive count"]
            body.append(shown[1:]); flat.append(shown)
    md_path.write_text(p3.html_table(headers[1:], body), encoding="utf-8")
    write_csv(csv_path, headers, flat)
    return {"status": "PASS", "rows": len(flat)}


def render_s13(rows: list[dict], csv_path: Path, md_path: Path) -> dict:
    values: dict = defaultdict(dict)
    for row in rows:
        values[(row["dimension"], row["pair"])][row["quantity"]] = row
    headers = ["Rater", "Records (N)", "Mean substantive labels per record", "Records assigned Unclear, n (%)",
               "Records substantively classified (n)", "Mean substantive labels among classified records"]
    body, flat = [], []
    for dimension in DIMENSIONS[:2]:
        body.append([dimension])
        for rater in RATERS:
            v = values[(dimension, rater)]
            n = int(v["mean_substantive_labels_per_record"]["sample_size"])
            unclear = int(v["unclear_records"]["parsed_value"])
            shown = [rater, str(n), p3.half_up(v["mean_substantive_labels_per_record"]["source_value_string"], 2),
                     f"{unclear} ({p3.percent_text(v['unclear_proportion']['source_value_string'], unclear)})",
                     v["substantively_classified_records"]["parsed_value"],
                     p3.half_up(v["mean_substantive_labels_among_classified"]["source_value_string"], 2)]
            if int(shown[4]) + unclear != n:
                raise RuntimeError(f"Supplementary Table S13 classified + Unclear differs from N: {dimension} {rater}")
            body.append(shown); flat.append([dimension] + shown)
    md_path.write_text(p3.html_table(headers, body), encoding="utf-8"); write_csv(csv_path, ["Dimension"] + headers, flat)
    return {"status": "PASS", "rows": len(flat)}


def render_s14(rows: list[dict], csv_path: Path, md_path: Path) -> dict:
    values = s4_values(rows)
    n = {series: int(next(iter(values[(series, "Research Domains")].values()))["sample_size"]) for series in ("repeatability", "cross_model")}

    def agreement(series: str, dimension: str, quantity: str = "agreement_count") -> str:
        row = values[(series, dimension)].get(quantity)
        if row is None:
            return "Not exported"
        count = int(row["parsed_value"])
        return f"{thousands(count)}/{thousands(n[series])} ({whole_percent_text(count, n[series])})"

    def jaccard(series: str, dimension: str) -> str:
        return p3.half_up(values[(series, dimension)]["mean_jaccard"]["source_value_string"], 2)

    frame_rows = values[("cross_model", "Disagreement frame")]
    frame = {key.split(":", 1)[1]: int(row["parsed_value"]) for key, row in frame_rows.items() if key.startswith("pre_exclusion:")}
    post = {key.split(":", 1)[1]: int(row["parsed_value"]) for key, row in frame_rows.items() if key.startswith("post_exclusion:")}
    excluded = int(values[("cross_model", "Disagreement frame")]["exclusions_applied"]["parsed_value"])
    strata = {key.split(":", 1)[1]: int(row["parsed_value"]) for key, row in values[("repeatability", "Sample composition")].items()}
    headers = ["Measure", f"A. Same-model repeatability: two Fable 5 runs ({n['repeatability']} records)",
               f"B. Cross-model: Fable 5 versus GPT-5.5 ({thousands(n['cross_model'])} records)"]
    body = [
        ["Records compared"],
        ["Population", f"Fixed sample: {strata['adjudicated']} purposively selected and {strata['random']} random records", "Frozen register, all records"],
        ["Research Domains"],
        ["Exact-set agreement, n/N (%)", agreement("repeatability", "Research Domains", "exact_set_count"), agreement("cross_model", "Research Domains", "exact_set_count")],
        ["Mean Jaccard", jaccard("repeatability", "Research Domains"), jaccard("cross_model", "Research Domains")],
        ["Analytical Purposes"],
        ["Exact-set agreement, n/N (%)", agreement("repeatability", "Analytical Purposes", "exact_set_count"), agreement("cross_model", "Analytical Purposes", "exact_set_count")],
        ["Mean Jaccard", jaccard("repeatability", "Analytical Purposes"), jaccard("cross_model", "Analytical Purposes")],
        ["Binary tags and all components"],
        ["COVID-19 & Pandemic agreement, n/N (%)", agreement("repeatability", "COVID-19 & Pandemic"), agreement("cross_model", "COVID-19 & Pandemic")],
        ["Demographic disparities / equity agreement, n/N (%)", agreement("repeatability", "Demographic disparities / equity"), agreement("cross_model", "Demographic disparities / equity")],
        ["Both tags agree, n/N (%)", agreement("repeatability", "Both tags"), agreement("cross_model", "Both tags")],
        ["All four components agree, n/N (%)", agreement("repeatability", "All four components"), "Not exported"],
        ["Invalid or failed classifications", values[("repeatability", "All components")]["invalid_or_failed_classifications"]["parsed_value"],
         values[("cross_model", "All components")]["invalid_or_failed_classifications"]["parsed_value"]],
        ["Cross-model disagreement frame (Research Domains or Analytical Purposes)"],
        ["Before exclusions: records (Research Domains only; Analytical Purposes only; both)", "–",
         f"{frame['total_disagreement']} ({frame['domain_only']}; {frame['purpose_only']}; {frame['both']})"],
        ["Before exclusions: with an accompanying tag disagreement", "–", str(frame["tag_disagreement_alongside_domain_or_purpose"])],
        ["Before exclusions: differing on a tag only (outside the frame)", "–", str(frame["tag_only_outside_domain_purpose_frame"])],
        ["Training and pilot records excluded from the register", "–", str(excluded)],
        ["After exclusions: records (Research Domains only; Analytical Purposes only; both)", "–",
         f"{post['total_disagreement']} ({post['domain_only']}; {post['purpose_only']}; {post['both']})"],
        ["After exclusions: with an accompanying tag disagreement", "–", str(post["tag_disagreement_alongside_domain_or_purpose"])],
        ["After exclusions: differing on a tag only (outside the frame)", "–", str(post["tag_only_outside_domain_purpose_frame"])],
    ]
    if frame["domain_only"] + frame["purpose_only"] + frame["both"] != frame["total_disagreement"] or \
            post["domain_only"] + post["purpose_only"] + post["both"] != post["total_disagreement"]:
        raise RuntimeError("Supplementary Table S14 frame components do not sum")
    flat, section = [], ""
    for row in body:
        if len(row) == 1:
            section = row[0]
        else:
            flat.append([section] + row)
    md_path.write_text(p3.html_table(headers, body), encoding="utf-8"); write_csv(csv_path, ["Section"] + headers, flat)
    return {"status": "PASS", "rows": len(flat)}


# ---------------------------------------------------------------- captions and checks
def write_captions(manifest: dict, path: Path) -> None:
    lines = ["# Draft captions — pass 4", "",
             "Figure and table numbering follows the pass-4 decision log, which supersedes pass-3 H.7 for figures. "
             "Tables 1–4 and Supplementary Tables S1a–S1c are carried forward unchanged from pass 3.", ""]
    for deliverable in manifest["order"]:
        entry = manifest["entries"][deliverable]; punctuation = "." if "Figure" in deliverable and "table" not in deliverable else ":"
        lines.extend([f"## {deliverable}", "", f"**{deliverable}{punctuation} {entry['title']}.**", "", "Legend content checklist:", ""])
        lines.extend(f"- {bullet}" for bullet in entry["caption_bullets"]); lines.append("")
    for deliverable, entry in manifest["carried_forward_tables"]["entries"].items():
        lines.extend([f"## {deliverable}", "", f"**{deliverable}: {entry['title']}.** (carried forward from pass 3; unchanged)", "",
                      "Legend content checklist:", ""])
        lines.extend(f"- {bullet}" for bullet in entry["caption_bullets"]); lines.append("")
    lines.extend(["## Not in the active publication set", ""])
    for deliverable, entry in manifest["withheld"].items():
        lines.append(f"- {deliverable}: {entry['reason']}")
    lines.extend(["", "## Unnumbered placeholders", ""])
    lines.extend(f"- {item}: numbered only once generated." for item in manifest["unnumbered_placeholders"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def file_checks(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    banned, minus = [], []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        banned.extend(p3.banned_check_text(text.splitlines(), str(path)))
        minus.extend({"path": str(path), "position": m.start()} for m in HYPHEN_BEFORE_DIGIT.finditer(text))
    return banned, minus


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
    if set(manifest["entries"]) != set(datasets) or len(datasets) != 10:
        raise RuntimeError("Pass-4 manifest/dataset mismatch")
    archived = archive_existing(figure_dir) if args.archive_existing else []

    rendering, keys, sums = {}, {}, []
    # Carried-forward pass-3 renderers are called unchanged; the text-overlap check covers the figures laid out in pass 4.
    renderers = (("Figure 1", render_figure1), ("Figure 2", p3.render_figure2), ("Figure 3", render_figure3),
                 ("Supplementary Figure S1", p3.render_s1), ("Supplementary Figure S2", p3.render_s2),
                 ("Supplementary Figure S3", render_s3), ("Supplementary Figure S4", render_s4))
    for deliverable, function in renderers:
        result = function(datasets[deliverable], figure_dir / manifest["entries"][deliverable]["slug"])
        rendering[deliverable], keys[deliverable] = result[0], result[1]
        if len(result) == 3:
            sums.extend({"deliverable": deliverable, **row} for row in result[2])

    table_reports, table_paths = {}, []
    for deliverable, function in (("Figure 3 source table", render_source_table), ("Supplementary Table S13", render_s13),
                                  ("Supplementary Table S14", render_s14)):
        slug = manifest["entries"][deliverable]["slug"]
        csv_path, md_path = table_dir / f"{slug}.csv", table_dir / f"{slug}.md"
        table_reports[deliverable] = function(datasets[deliverable], csv_path, md_path); table_paths += [csv_path, md_path]

    captions_path = figure_dir / "draft_captions_pass4.md"; write_captions(manifest, captions_path)
    figure_banned = [f for deliverable, record in rendering.items() for f in p3.banned_check_text(record["rendered_text"], deliverable)]
    table_banned, table_minus = file_checks(table_paths)
    caption_banned, _ = file_checks([captions_path])
    figure_minus = [{"deliverable": deliverable, "text": text} for deliverable, record in rendering.items()
                    for text in record["rendered_text"] if HYPHEN_BEFORE_DIGIT.search(text)]
    if figure_banned + table_banned + caption_banned:
        raise RuntimeError(f"Banned reader-facing text found: {figure_banned + table_banned + caption_banned}")
    if table_minus or figure_minus:
        raise RuntimeError(f"Hyphen-minus assertion failed: tables={table_minus}; figures={figure_minus}")
    if any(record.get("status") != "PASS" for record in keys.values()):
        raise RuntimeError(f"Key, label or marker assertion failed: { {k: v for k, v in keys.items() if v.get('status') != 'PASS'} }")
    if any(record["font_status"] != "PASS" for record in rendering.values()):
        raise RuntimeError(f"H.1 font-size assertion failed: { {k: v['minimum_effective_pt'] for k, v in rendering.items()} }")
    if any(record.get("text_overlaps") for record in rendering.values()):
        raise RuntimeError(f"Overlapping text: { {k: v['text_overlaps'] for k, v in rendering.items() if v.get('text_overlaps')} }")
    if any(record["edge_status"] != "PASS" for record in rendering.values()):
        raise RuntimeError(f"H.2 edge assertion failed: { {k: v['edge_failures'] for k, v in rendering.items() if v['edge_failures']} }")
    alignment, delta_check = row_alignment(keys), delta_annotation_check(datasets, keys)
    if alignment["status"] != "PASS":
        raise RuntimeError(f"H.5 row alignment failed: {alignment}")
    if delta_check["status"] != "PASS":
        raise RuntimeError(f"δ_min annotation assertion failed: {delta_check}")
    active = sorted(path.name for path in figure_dir.iterdir() if path.is_file())
    stale = [name for name in active if any(name.startswith(slug) for slug in PRE_EXISTING_FIGURES - {
        "figure_2_coder_ratings_baseline", "supplementary_figure_s1_baseline_vs_hardcase", "supplementary_figure_s2_hardcase_ratings_confidence"})]
    if stale:
        raise RuntimeError(f"Superseded figure files remain active: {stale}")
    for number in ("1", "2", "3"):
        expected = {f"{manifest['entries'][f'Figure {number}']['slug']}{suffix}" for suffix in (".png", ".svg")}
        present = {name for name in active if name.startswith(f"figure_{number}_")}
        if present != expected:
            raise RuntimeError(f"Active Figure {number} filenames differ: {sorted(present)}")
    if any(name.startswith("figure_4") for name in active):
        raise RuntimeError("An active figure_4 file remains")

    report = {
        "renderer": Path(__file__).name, "input_boundary": "pass-4 manifest plus its listed CSV and JSON files only",
        "matplotlib_version": matplotlib.__version__, "python_version": sys.version, "font_family": p3.FONT_FAMILY,
        "font_resolved": font_manager.findfont(p3.FONT_FAMILY), "archived_preexisting_outputs": archived,
        "font_sizes": {k: {f: v[f] for f in ("target_width_cm", "saved_width_inches", "minimum_effective_pt", "minimum_is_subscript",
                                             "minimum_subscript_effective_pt", "font_status")} for k, v in rendering.items()},
        "edges": {k: {"status": v["edge_status"], "failures": v["edge_failures"]} for k, v in rendering.items()},
        "row_alignment": alignment, "delta_min_annotation": delta_check, "keys": keys, "table_rendering": table_reports,
        "percentages": {"displayed_sums": sums}, "banned_text": {"status": "PASS"}, "minus_sign": {"status": "PASS"},
        "caption_policy": {"titles_or_caption_prose_embedded": False, "draft_captions": captions_path.name},
        "isolation_test": {"status": "PENDING RUNNER"}, "manual_visual_inspection": {"status": "PENDING"},
    }
    (figure_dir / "pass4_rendering_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    run_metadata = {"manifest_generated_utc": manifest["generated_utc"], "rendered_utc": datetime.now(timezone.utc).isoformat(),
                    "provenance": manifest["provenance"], "font_family": p3.FONT_FAMILY,
                    "software": {"python": sys.version, "matplotlib": matplotlib.__version__, "font": font_manager.findfont(p3.FONT_FAMILY)}}
    (figure_dir / "pass4_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
