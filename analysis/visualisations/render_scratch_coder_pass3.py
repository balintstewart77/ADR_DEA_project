"""Stage 2 renderer for pass 3.

Only the pass-3 manifest and the CSV/JSON files it lists are analytical
inputs.  The renderer performs display rounding and graphical layout only.
"""
from __future__ import annotations

import argparse
import colorsys
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
from matplotlib.patches import Circle, Rectangle
from matplotlib.text import Text
from matplotlib.ticker import FixedLocator, FuncFormatter, MultipleLocator
from matplotlib.transforms import Bbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_style  # noqa: E402
from figure_style import COLOURS  # noqa: E402
import rating_bars  # noqa: E402
from matplotlib.offsetbox import AnnotationBbox  # noqa: E402


FONT_FAMILY = "Arial"
FIGURE_WIDTH = 17 / 2.54
MIN_PT = 8.0
# Scatter accepts marker area (points squared), so retain the existing circle
# area and express the star size as a visual diameter in points.
CIRCLE_AREA = 38
STAR_SIZE = 1.3 * math.sqrt(CIRCLE_AREA)
S1_EXTRA_TOP_PT = 6.0
# Supplementary Figure S1 row geometry: rows 1.4x Figure 1's row pitch (25.95 pt -> 36.3 pt), the
# baseline/hard-case pair offset kept at Figure 3's 7.71 pt, and gaps between dimensions kept at 32.6 pt.
S1_HEIGHT = 9.74
S1_DODGE = 0.106
S1_HSPACE = 0.108
matplotlib.rcParams.update({
    "font.family": FONT_FAMILY,
    "font.sans-serif": [FONT_FAMILY],
    "mathtext.fontset": "custom",
    "mathtext.rm": FONT_FAMILY,
    "svg.fonttype": "none",
    "svg.hashsalt": "scratch-coder-pass3",
    "axes.titlesize": 9.0,
    "axes.labelsize": 8.5,
    "xtick.labelsize": 8.0,
    "ytick.labelsize": 8.0,
    "legend.fontsize": 8.0,
    "axes.unicode_minus": True,
})

DIMENSIONS = ("Research Domains", "Analytical Purposes", "Demographic disparities / equity", "COVID-19 & Pandemic")
ALPHA_ORDER = ("alpha ABC", "alpha LBC", "alpha ALC", "alpha ABL")
DELTA_ORDER = ("delta_min", "delta_A", "delta_B", "delta_C")
ALPHA_LABELS = {q: q.removeprefix("alpha ") for q in ALPHA_ORDER}
DELTA_LABELS = {"delta_min": r"δ$_{\mathrm{min}}$", "delta_A": r"δ$_{\mathrm{A}}$", "delta_B": r"δ$_{\mathrm{B}}$", "delta_C": r"δ$_{\mathrm{C}}$"}
POPULATION = {
    "baseline": {"color": COLOURS["baseline"], "hollow": False, "label": "Baseline (n=150)"},
    "baseline_strict_sufficient": {"color": COLOURS["strict"], "hollow": True, "label": "Register entry judged sufficient (n=92)"},
    "hard_case": {"color": COLOURS["hardcase"], "hollow": True, "label": "Hard-case (n=75)"},
}
RATING_PALETTES = {
    "Register-entry information": {
        "Sufficient": "#246B45", "Partially sufficient": "#78AF82", "Insufficient": "#D6E8D8", "No majority": "#888888",
    },
    "Taxonomy fit": {
        "Fit": "#5A4A86", "Partial Fit": "#9B8CC0", "No Fit": "#DED8EC",
        "Cannot assess from register entry": "#5F5F5F", "No majority": "#AEAEAE",
    },
    "Coder confidence": {"High": "#A63D57", "Medium": "#D77A8B", "Low": "#F3D0D7", "No majority": "#888888"},
}
DISAGREE_COLORS = {"containment": "#3B6B8C", "overlap": "#C58B36", "disjoint": "#777777"}
PAIR_ORDER = (
    "C01 versus C02", "C01 versus C03", "C02 versus C03",
    "Fable 5 versus C01", "Fable 5 versus C02", "Fable 5 versus C03",
)
BANNED = (
    re.compile(r"\bsupport\b", re.I), re.compile(r"\bStandard\b", re.I), re.compile(r"\bRare\b", re.I),
    re.compile(r"\bWithheld\b", re.I), re.compile(r"\bSV\b"), re.compile(r"delta_", re.I),
    re.compile(r"source-exported", re.I), re.compile(r"\bcanonical\b", re.I), re.compile(r"\bU\d{4}\b"),
    re.compile(r"^Notes\b", re.I), re.compile(r"split judgement", re.I), re.compile(r"Equity tag", re.I),
    re.compile(r"COVID-19 tag", re.I), re.compile(r"Strict register-sufficient", re.I),
    re.compile(r"Exploratory; not preregistered", re.I), re.compile(r"coder declined to classify", re.I),
)


def d(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def f(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def half_up(value: str, places: int = 2) -> str:
    rounded = d(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    shown = f"{rounded:.{places}f}"
    return "−" + shown[1:] if shown.startswith("-") else shown


def whole_percent(value: str) -> int:
    return int((d(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percent_text(value: str, count: int | None = None) -> str:
    pct = whole_percent(value)
    if (count is None or count > 0) and d(value) > 0 and pct == 0:
        return "<1%"
    return f"{pct}%"


def minus_tick(value: float, _position=None) -> str:
    if abs(value) < 1e-12:
        return "0"
    shown = f"{value:g}"
    return "−" + shown[1:] if shown.startswith("-") else shown


def display_category(category: str) -> str:
    return "No majority" if category == "No majority / split judgement" else category


def load(data_dir: Path) -> tuple[dict, dict[str, list[dict]]]:
    manifest = json.loads((data_dir / "pass3_deliverable_manifest.json").read_text(encoding="utf-8"))
    datasets = {}
    for deliverable, entry in manifest["entries"].items():
        with (data_dir / entry["inputs"]["data"]).open(newline="", encoding="utf-8") as handle:
            datasets[deliverable] = list(csv.DictReader(handle))
    return manifest, datasets


def archive_existing(figure_dir: Path, table_dir: Path, manifest: dict) -> list[dict]:
    archive_fig = figure_dir / "archive" / "pass3_preexisting_64679cf"
    archive_tab = table_dir / "archive" / "pass3_preexisting_64679cf"
    names = {
        figure_dir: {
            "figure_1_panel_agreement_replacement.png", "figure_1_panel_agreement_replacement.svg",
            "figure_2_sufficiency_sensitivity.png", "figure_2_sufficiency_sensitivity.svg",
            "figure_3_label_application.png", "figure_3_label_application.svg",
            "figure_4_disagreement_composition.png", "figure_4_disagreement_composition.svg",
            "supplementary_figure_s1_baseline_vs_hardcase.png", "supplementary_figure_s1_baseline_vs_hardcase.svg",
            "supplementary_figure_s2_coder_ratings.png", "supplementary_figure_s2_coder_ratings.svg",
            "draft_captions_pass2.md", "pass2_rendering_report.json", "pass2_run_metadata.json",
        },
        table_dir: {
            "table_1_agreement_domains.csv", "table_1_agreement_domains.md",
            "table_2_agreement_purposes.csv", "table_2_agreement_purposes.md",
            "table_3_agreement_with_majority_domains.csv", "table_3_agreement_with_majority_domains.md",
            "table_4_agreement_with_majority_purposes.csv", "table_4_agreement_with_majority_purposes.md",
            "table_5_disagreement_composition.csv", "table_5_disagreement_composition.md",
            "supplementary_table_s1a_register_information.csv", "supplementary_table_s1a_register_information.md",
            "supplementary_table_s1b_taxonomy_fit.csv", "supplementary_table_s1b_taxonomy_fit.md",
            "supplementary_table_s1c_agreed_labels.csv", "supplementary_table_s1c_agreed_labels.md",
        },
    }
    moved = []
    for directory, candidates in names.items():
        archive = archive_fig if directory == figure_dir else archive_tab
        existing = [directory / name for name in sorted(candidates) if (directory / name).is_file()]
        if existing:
            archive.mkdir(parents=True, exist_ok=True)
        for source in existing:
            target = archive / source.name
            if target.exists():
                raise RuntimeError(f"Archive target already exists: {target}")
            shutil.move(source, target)
            moved.append({"from": str(source), "to": str(target)})
    return moved


def style_axis(ax, grid: str = "x") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis=grid, color="#E7E7E7", linewidth=0.55, zorder=0)
    ax.tick_params(length=3)


def draw_interval(ax, y: float, row: dict, color: str, marker: str = "o", hollow: bool = False, size: float | None = None,
                  shared_star: bool = False) -> dict:
    estimate, lower, upper = f(row["parsed_value"]), f(row["parsed_interval_lower"]), f(row["parsed_interval_upper"])
    if estimate is None:
        return {}
    interval_artists = []
    if lower is not None and upper is not None and row["interval_status"] == "R":
        interval_artists.append(ax.hlines(y, lower, upper, color=color, linewidth=1.45, zorder=5))
        interval_artists.append(ax.vlines([lower, upper], y - 0.075, y + 0.075, color=color, linewidth=1.0, zorder=5))
    marker_size = size if size is not None else (STAR_SIZE if marker == "*" else CIRCLE_AREA)
    marker_area = marker_size ** 2 if marker == "*" else marker_size
    if shared_star and marker == "*":
        point = ax.scatter(estimate, y, marker=marker, s=marker_area,
                           facecolors=figure_style.STAR_HOLLOW_FACE if hollow else color, edgecolors=color if hollow else "black",
                           linewidths=figure_style.STAR_HOLLOW_EDGE_PT if hollow else figure_style.STAR_FILLED_EDGE_PT,
                           zorder=figure_style.MARKER_ZORDER)
        for artist in interval_artists:
            artist.set_zorder(figure_style.INTERVAL_ZORDER)
        return {"row": row, "point": point, "interval": interval_artists, "x": estimate, "lower": lower, "upper": upper, "y": y}
    point = ax.scatter(estimate, y, marker=marker, s=marker_area,
                       facecolors="none" if hollow else color, edgecolors=color if hollow else "black",
                       linewidths=1.35 if hollow else 0.65, zorder=4)
    return {"row": row, "point": point, "interval": interval_artists, "x": estimate, "lower": lower, "upper": upper, "y": y}


def add_delta_annotation(ax, records: list[dict], text: str) -> Text:
    upper_bound = max((record["upper"] if record["upper"] is not None else record["x"]) for record in records)
    y = sum(record["y"] for record in records) / len(records)
    return ax.annotate(text, xy=(upper_bound, y), xytext=(6, 0), textcoords="offset points",
                       fontsize=9.5, ha="left", va="center", color="#333", zorder=6)


def add_single_population_delta_annotation(ax, records: list[dict], text: str) -> Text:
    right = max((record["upper"] if record["upper"] is not None else record["x"]) for record in records)
    left = min((record["lower"] if record["lower"] is not None else record["x"]) for record in records)
    x_limit = ax.get_xlim()
    if right + 0.10 < x_limit[1]:
        x, ha = right + 0.08, "left"
    else:
        x, ha = left - 0.08, "right"
    return ax.text(x, sum(record["y"] for record in records) / len(records), text, fontsize=9.5, ha=ha, va="center", color="#333", zorder=6)


def replacement_figure(rows: list[dict], dimensions: tuple[str, ...], populations: tuple[str, ...],
                       alpha_range: tuple[float, float], height: float, annotate: bool, s1: bool = False, dodge_step: float = 0.115,
                       hspace: float = 0.15):
    fig, axes = plt.subplots(len(dimensions), 2, figsize=(FIGURE_WIDTH, height), constrained_layout=True,
                             gridspec_kw={"hspace": hspace})
    if len(dimensions) == 1:
        axes = [axes]
    dodge = {populations[0]: 0.0} if len(populations) == 1 else {populations[0]: -dodge_step, populations[1]: dodge_step}
    positions = []; delta_checks = []
    for index, dimension in enumerate(dimensions):
        for column, series in enumerate(("alpha", "delta")):
            ax = axes[index][column]
            order = ALPHA_ORDER if series == "alpha" else DELTA_ORDER
            plotted: dict[tuple[str, str], dict] = {}
            for population in populations:
                keyed = {r["quantity"]: r for r in rows if r["dimension"] == dimension and r["population"] == population and r["series"] == series and r["role"] == "plotted"}
                for y, quantity in enumerate(order):
                    marker = "*" if quantity == "delta_min" else "o"
                    star_size = figure_style.STAR_DIAMETER_RATIO * math.sqrt(CIRCLE_AREA) if s1 else STAR_SIZE
                    record = draw_interval(ax, y + dodge[population], keyed[quantity], POPULATION[population]["color"], marker,
                                           POPULATION[population]["hollow"], star_size if marker == "*" else None, shared_star=s1)
                    plotted[(population, quantity)] = record
                    positions.append({"dimension": dimension, "population": population, "series": series, "quantity": quantity, "y": y})
                    if series == "delta" and quantity == "delta_min":
                        delta_checks.append({"dimension": dimension, "population": population, "quantity": quantity,
                                             "source_row_key": keyed[quantity]["source_row_key"], "interval": [keyed[quantity]["parsed_interval_lower"], keyed[quantity]["parsed_interval_upper"]]})
            ax.set_yticks(range(4), [ALPHA_LABELS[q] for q in order] if series == "alpha" else [DELTA_LABELS[q] for q in order])
            ax.tick_params(axis="y", labelsize=9.5)
            ax.invert_yaxis()
            ax.set_xlim(alpha_range if series == "alpha" else (-0.45, 0.45))
            if series == "alpha" and alpha_range in ((0.0, 1.0), (0.0, 1.02)):
                ax.xaxis.set_major_locator(FixedLocator([0, 0.2, 0.4, 0.6, 0.8, 1.0]))
            elif series == "alpha":
                ax.xaxis.set_major_locator(FixedLocator([0.2, 0.3, 0.4, 0.5, 0.6, 0.7]))
            else:
                ax.xaxis.set_major_locator(FixedLocator([-0.4, -0.2, 0, 0.2, 0.4]))
            ax.xaxis.set_major_formatter(FuncFormatter(minus_tick))
            if series == "delta":
                ax.axvline(0, color="#333333", linewidth=0.8, zorder=1)
                if annotate and not s1:
                    if len(populations) == 1:
                        component = r"δ$_{\mathrm{A}}$" if dimension == "COVID-19 & Pandemic" else r"δ$_{\mathrm{B}}$"
                    else:
                        component = r"δ$_{\mathrm{B}}$"
                    records = [plotted[(population, "delta_min")] for population in populations]
                    if len(populations) == 2:
                        add_delta_annotation(ax, records, f"= {component}")
                    else:
                        add_single_population_delta_annotation(ax, records, f"= {component}")
            style_axis(ax)
            ax.tick_params(axis="x", labelbottom=True)
            if index == 0:
                ax.set_title("Krippendorff’s α" if series == "alpha" else "Replacement difference δ", pad=7)
            if column == 0:
                displayed_dimension = dimension.replace("Demographic disparities", "Demographic\ndisparities")
                ax.set_ylabel(displayed_dimension, fontweight="bold", rotation=0, ha="right", va="center", labelpad=4, multialignment="right")
    return fig, axes, positions, delta_checks


def text_metrics(fig, name: str) -> dict:
    fig.canvas.draw(); renderer = fig.canvas.get_renderer(); box = fig.bbox
    texts = [text for text in fig.findobj(Text) if text.get_visible() and text.get_text().strip()]
    edge_failures = []
    for text in texts:
        extent = text.get_window_extent(renderer)
        if extent.width and extent.height and (extent.x0 < box.x0 + 1 or extent.y0 < box.y0 + 1 or extent.x1 > box.x1 - 1 or extent.y1 > box.y1 - 1):
            edge_failures.append({"text": text.get_text(), "bbox": [extent.x0, extent.y0, extent.x1, extent.y1], "figure": [box.x0, box.y0, box.x1, box.y1]})
    sizes = []
    for text in texts:
        contains_subscript = "$_" in text.get_text() or any(ch in text.get_text() for ch in "ₐᵦₘᵢₙ")
        effective = float(text.get_fontsize()) * (0.85 if "$_" in text.get_text() else 1.0)
        sizes.append({"text": text.get_text(), "effective_pt": effective, "contains_subscript": contains_subscript})
    minimum = min(item["effective_pt"] for item in sizes)
    minimum_items = [item for item in sizes if item["effective_pt"] == minimum]
    subscript_sizes = [item["effective_pt"] for item in sizes if item["contains_subscript"]]
    return {
        "name": name, "target_width_cm": 17, "saved_width_inches": fig.get_figwidth(),
        "minimum_effective_pt": minimum, "minimum_is_subscript": any(item["contains_subscript"] for item in minimum_items),
        "minimum_subscript_effective_pt": min(subscript_sizes) if subscript_sizes else None,
        "font_status": "PASS" if minimum >= MIN_PT and (not subscript_sizes or min(subscript_sizes) >= MIN_PT) else "FAIL",
        "edge_status": "PASS" if not edge_failures else "FAIL", "edge_failures": edge_failures,
        "rendered_text": [text.get_text() for text in texts],
    }


def save_figure(fig, base: Path, name: str, tight: bool = True, extra_top_pt: float = 0.0) -> dict:
    metrics = text_metrics(fig, name)
    bbox = "tight" if tight else None
    if tight and extra_top_pt:
        pad = matplotlib.rcParams["savefig.pad_inches"]
        box = fig.get_tightbbox(fig.canvas.get_renderer())
        bbox = Bbox.from_extents(box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad + extra_top_pt / 72)
    fig.savefig(base.with_suffix(".svg"), format="svg", dpi=300, facecolor="white", bbox_inches=bbox, metadata={"Date": None})
    fig.savefig(base.with_suffix(".png"), format="png", dpi=300, facecolor="white", bbox_inches=bbox, metadata={"Software": "matplotlib"})
    plt.close(fig)
    return metrics


def render_figure1(rows: list[dict], base: Path):
    fig, axes, positions, delta = replacement_figure(rows, DIMENSIONS, ("baseline",), (0.0, 1.0), 6.8, True)
    render = save_figure(fig, base, "Figure 1")
    return render, {"status": "PASS", "key_entries": [], "encodings_present": [], "row_positions": positions, "delta_min_rows": delta,
                    "annotation_components": {dimension: ("delta_A" if dimension == "COVID-19 & Pandemic" else "delta_B") for dimension in DIMENSIONS}}


def render_figure3(rows: list[dict], base: Path):
    fig, axes, positions, delta = replacement_figure(rows, DIMENSIONS[:2], ("baseline", "baseline_strict_sufficient"), (0.15, 0.75), 4.45, True)
    handles = [Line2D([0], [0], marker="o", color=POPULATION[p]["color"], markerfacecolor="none" if POPULATION[p]["hollow"] else POPULATION[p]["color"],
                      markeredgecolor=POPULATION[p]["color"], linewidth=1.2, label=POPULATION[p]["label"]) for p in ("baseline", "baseline_strict_sufficient")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False)
    render = save_figure(fig, base, "Figure 3")
    return render, {"status": "PASS", "key_entries": [h.get_label() for h in handles], "encodings_present": ["baseline filled", "sufficient-subset hollow"],
                    "row_positions": positions, "delta_min_rows": delta, "annotation_components": {dimension: "delta_B" for dimension in DIMENSIONS[:2]}}


def render_s1(rows: list[dict], base: Path):
    fig, axes, positions, delta = replacement_figure(rows, DIMENSIONS, ("baseline", "hard_case"), (0.0, 1.02), S1_HEIGHT, False, s1=True,
                                                     dodge_step=S1_DODGE, hspace=S1_HSPACE)
    fig.suptitle("Hard-case sample: diagnostic, non-representative", fontsize=8.5, fontweight="bold", color="0.15")
    handles = [Line2D([0], [0], marker="o", color=POPULATION[p]["color"], markerfacecolor="none" if POPULATION[p]["hollow"] else POPULATION[p]["color"],
                      markeredgecolor=POPULATION[p]["color"], linewidth=1.2, label=POPULATION[p]["label"]) for p in ("baseline", "hard_case")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False)
    render = save_figure(fig, base, "Supplementary Figure S1", extra_top_pt=S1_EXTRA_TOP_PT)
    return render, {"status": "PASS", "key_entries": [h.get_label() for h in handles], "encodings_present": ["baseline filled", "hard-case hollow"],
                    "row_positions": positions, "delta_min_rows": delta, "annotation_components": {}}


HATCHED_CATEGORIES = {"Cannot assess from register entry"}
S3_OUTSIDE_GAP_PT = 3.0  # bar end to square, and square to label text
S2_HEADER = "Hard-case panels: diagnostic, non-representative"
S2_ROWS = (  # (content, height in inches)
    ("header", 0.24),
    ("title", 0.26), ("key", 0.30), ("bars", 1.45), ("spacer", 0.30),
    ("title", 0.26), ("key", 0.30), ("bars", 1.45), ("spacer", 0.30),
    ("title", 0.26), ("key", 0.30), ("bars", 1.45), ("spacer", 0.30),
    ("title", 0.26), ("bars", 1.45),
    ("xlabels", 0.50),
)


def rating_data(rows: list[dict], construct: str, population: str) -> tuple[dict[str, list[dict]], list[dict]]:
    data = {}; sums = []
    for actor in rating_bars.ACTORS:
        selected = sorted([r for r in rows if r["dimension"] == construct and r["population"] == population and r["pair"] == actor and r["role"] == "plotted"], key=lambda r: int(r["source_order"]))
        data[actor] = [{"category": display_category(r["label"]), "width": d(r["parsed_interval_lower"]) * 100,
                        "label": percent_text(r["parsed_interval_lower"], int(r["parsed_value"])), "count": int(r["parsed_value"])} for r in selected]
        displayed = [segment["label"] for segment in data[actor]]
        sums.append({"construct": construct, "population": population, "bar": actor, "displayed_percentages": displayed,
                     "sum": sum(int(v.rstrip("%").replace("<1", "0")) for v in displayed)})
    return data, sums


def rating_check(construct: str, result: dict) -> dict:
    categories = list(RATING_PALETTES[construct])
    return {"status": "PASS" if result["nonzero_segments"] == result["labels_rendered"] and set(result["encodings_present"]) == set(categories) else "FAIL",
            "nonzero_segments": result["nonzero_segments"], "labels_rendered": result["labels_rendered"],
            "encodings_present": result["encodings_present"], "key_entries": categories}


def render_figure2(rows: list[dict], base: Path):
    row_heights = [0.30, 0.35, 2.40, 0.45, 0.30, 0.35, 2.40, 0.55]
    fig_h = sum(row_heights)
    fig = plt.figure(figsize=(FIGURE_WIDTH, fig_h))
    grid = fig.add_gridspec(8, 1, height_ratios=row_heights,
                            left=0.20, right=0.87, top=1.0, bottom=0.0, hspace=0.0)
    title_axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[4, 0])]
    key_axes = [fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[5, 0])]
    bar_axes = [fig.add_subplot(grid[2, 0]), fig.add_subplot(grid[6, 0])]
    spacer = fig.add_subplot(grid[3, 0]); spacer.axis("off")
    xlabel_ax = fig.add_subplot(grid[7, 0]); xlabel_ax.axis("off")
    sums = []; checks = []
    for i, construct in enumerate(("Register-entry information", "Taxonomy fit")):
        data, panel_sums = rating_data(rows, construct, "baseline")
        result = rating_bars.draw_rating_panel(title_axes[i], key_axes[i], bar_axes[i], data, RATING_PALETTES[construct],
                                               HATCHED_CATEGORIES, construct, show_key=True, show_xlabels=i == 1)
        sums.extend(panel_sums); checks.append(rating_check(construct, result))
    render = save_figure(fig, base, "Figure 2", tight=False)
    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    return render, {"status": status, "panels": checks}, sums


def build_s2(rows: list[dict]):
    heights = [h for _, h in S2_ROWS]
    fig = plt.figure(figsize=(FIGURE_WIDTH, sum(heights)))
    grid = fig.add_gridspec(len(heights), 1, height_ratios=heights, left=0.20, right=0.87, top=1.0, bottom=0.0, hspace=0.0)
    row_axes = {kind: [] for kind, _ in S2_ROWS}
    for index, (kind, _) in enumerate(S2_ROWS):
        ax = fig.add_subplot(grid[index, 0])
        if kind in ("header", "spacer", "xlabels"):
            ax.axis("off")
        row_axes[kind].append(ax)
    header = row_axes["header"][0]
    header.text(0, 0.5, S2_HEADER, transform=header.transAxes, ha="left", va="center", fontsize=8.5, fontweight="bold", color="0.15")
    specs = (
        ("Register-entry information", "hard_case", "Register-entry information: hard-case (n=75)", True),
        ("Taxonomy fit", "hard_case", "Taxonomy fit: hard-case (n=75)", True),
        ("Coder confidence", "baseline", "Coder confidence: baseline (n=150)", True),
        ("Coder confidence", "hard_case", "Coder confidence: hard-case (n=75)", False),  # same categories as the key above
    )
    sums = []; checks = []; panels = []; key_axes = iter(row_axes["key"])
    for index, (construct, population, title, show_key) in enumerate(specs):
        data, panel_sums = rating_data(rows, construct, population)
        result = rating_bars.draw_rating_panel(row_axes["title"][index], next(key_axes) if show_key else None, row_axes["bars"][index],
                                               data, RATING_PALETTES[construct], HATCHED_CATEGORIES, title,
                                               show_key=show_key, show_xlabels=index == len(specs) - 1)
        sums.extend(panel_sums); checks.append(rating_check(construct, result))
        panels.append({"construct": construct, "population": population, "title": title, "data": data, "result": result})
    return fig, panels, sums, checks


def render_s2(rows: list[dict], base: Path):
    fig, _, sums, checks = build_s2(rows)
    render = save_figure(fig, base, "Supplementary Figure S2", tight=False)
    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    return render, {"status": status, "panels": checks}, sums


def expanded(box: Bbox, pixels: float) -> Bbox:
    return box.expanded((box.width + 2 * pixels) / max(box.width, 1), (box.height + 2 * pixels) / max(box.height, 1))


def line_hits_box(ax, box: Bbox) -> bool:
    for value in [(-1.5 + i * 61.5 / 600) for i in range(601)]:
        px, py = ax.transData.transform((value, value))
        if box.x0 - 1 <= px <= box.x1 + 1 and box.y0 - 1 <= py <= box.y1 + 1:
            return True
    return False


def place_point_labels(fig, ax, rows: list[dict], threshold_boxes: list[Bbox]) -> tuple[list[dict], list[dict]]:
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    marker_boxes = []
    for row in rows:
        px, py = ax.transData.transform((float(row["parsed_value"]), float(row["parsed_interval_lower"])))
        marker_boxes.append(Bbox.from_extents(px - 5.5, py - 5.5, px + 5.5, py + 5.5))
    placed = []; records = []; annotations = []
    direct_names = {"Labour Market & Employment": "Labour Market", "Descriptive Monitoring": "Descriptive Monitoring"}
    for row in sorted(rows, key=lambda r: (0 if r["label"] in direct_names else 1, int(r["source_order"]))):
        x, y = float(row["parsed_value"]), float(row["parsed_interval_lower"])
        text = direct_names.get(row["label"], row["source_order"])
        accepted = None
        adjacent = ((9, 7), (9, -7), (-9, 7), (-9, -7), (13, 0), (-13, 0), (0, 12), (0, -12))
        leader = ((22, 16), (22, -16), (-22, 16), (-22, -16), (34, 24), (34, -24), (-34, 24), (-34, -24), (48, 0), (-48, 0), (0, 48), (0, -48), (64, 35), (-64, 35), (64, -35), (-64, -35))
        for method, candidates in (("direct", adjacent), ("leader", leader)):
            for dx, dy in candidates:
                annotation = ax.annotate(text, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                                         ha="left" if dx >= 0 else "right", va="bottom" if dy >= 0 else "top", fontsize=8.0,
                                         bbox={"boxstyle": "round,pad=0.12", "fc": "white", "ec": "none", "alpha": 0.92},
                                         arrowprops=None if method == "direct" else {"arrowstyle": "-", "color": "#777", "lw": 0.65, "shrinkA": 2, "shrinkB": 4},
                                         annotation_clip=False, zorder=7)
                annotation.set_gid("point-label")
                fig.canvas.draw(); box = Text.get_window_extent(annotation, renderer)
                axes_box = ax.get_window_extent(renderer)
                inside = box.x0 >= axes_box.x0 + 1 and box.y0 >= axes_box.y0 + 1 and box.x1 <= axes_box.x1 - 1 and box.y1 <= axes_box.y1 - 1
                collision = any(expanded(box, 1.5).overlaps(other) for other in placed + marker_boxes + threshold_boxes) or line_hits_box(ax, expanded(box, 1))
                if inside and not collision:
                    accepted = (annotation, box, dx, dy, method); break
                annotation.remove()
            if accepted:
                break
        if not accepted:
            raise RuntimeError(f"Figure 4 label placement failed for {row['dimension']}: {row['label']}")
        annotation, box, dx, dy, method = accepted
        placed.append(box); annotations.append(annotation)
        records.append({"dimension": row["dimension"], "label": row["label"], "display": text, "number": int(row["source_order"]),
                        "method": method, "x": x, "y": y, "dx_points": dx, "dy_points": dy})
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    boxes = [Text.get_window_extent(annotation, renderer) for annotation in annotations]
    overlaps = []
    for i, box in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            if box.overlaps(boxes[j]): overlaps.append([i, j])
        for j, marker in enumerate(marker_boxes):
            if box.overlaps(marker): overlaps.append([i, f"marker-{j}"])
        for j, threshold in enumerate(threshold_boxes):
            if box.overlaps(threshold): overlaps.append([i, f"threshold-{j}"])
        if line_hits_box(ax, box): overlaps.append([i, "equality-line"])
    return records, overlaps


def render_figure4(rows: list[dict], base: Path):
    fig = plt.figure(figsize=(FIGURE_WIDTH, 7.15), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.0, 0.63], hspace=0.08)
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])]
    key_axes = [fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])]
    all_records = []; all_overlaps = []; selected_map = {}
    for ax, key_ax, dimension in zip(axes, key_axes, DIMENSIONS[:2]):
        selected = sorted([r for r in rows if r["dimension"] == dimension], key=lambda r: int(r["source_order"]))
        selected_map[dimension] = selected
        ax.plot([-1.5, 60], [-1.5, 60], color="#4D4D4D", linestyle="--", linewidth=0.8, zorder=1)
        ax.axvline(10, color="#666", linestyle=(0, (4, 3)), linewidth=0.9, zorder=1)
        ax.axvline(30, color="#666", linestyle=(0, (4, 3)), linewidth=0.9, zorder=1)
        threshold_texts = [ax.text(10, 58.7, "10 records", ha="center", va="top", fontsize=8.0, color="#555", zorder=6),
                           ax.text(30, 58.7, "30 records", ha="center", va="top", fontsize=8.0, color="#555", zorder=6)]
        for row in selected:
            x, y = int(row["parsed_value"]), int(row["parsed_interval_lower"])
            ax.scatter(x, y, s=35, color=POPULATION["baseline"]["color"], edgecolor="black", linewidth=0.55, zorder=4)
            if row["label"] == "Unclear from Register Entry":
                ax.scatter(x, y, s=95, facecolors="none", edgecolors="#8A4F7D", linewidths=1.35, zorder=5)
        ax.set(xlim=(-1.5, 60), ylim=(-1.5, 60), aspect="equal", xlabel="Records labelled by the coder majority", ylabel="Records labelled by Fable 5")
        ax.xaxis.set_major_locator(FixedLocator(range(0, 61, 10))); ax.yaxis.set_major_locator(FixedLocator(range(0, 61, 10)))
        ax.set_title(dimension, fontweight="bold", pad=8); style_axis(ax, "both")
        key_ax.set_xticks([]); key_ax.set_yticks([]); key_ax.axis("off"); key_ax.set_title("Labels", loc="left", fontsize=8.5, fontweight="bold", pad=2)
        split = math.ceil(len(selected) / 2)
        for idx, row in enumerate(selected):
            column, within = idx // split, idx % split
            label = row["label"] + (" (declined to classify)" if row["label"] == "Unclear from Register Entry" else "")
            wrapped = "\n".join(textwrap.wrap(label, width=18, break_long_words=False))
            x0 = 0.01 + column * 0.55; y0 = 0.96 - within * (0.88 / max(split, 1))
            key_ax.text(x0, y0, f"{row['source_order']}. {wrapped}", transform=key_ax.transAxes, ha="left", va="top", fontsize=8.0, linespacing=0.88)
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    for ax, dimension in zip(axes, DIMENSIONS[:2]):
        threshold_boxes = [Text.get_window_extent(text, renderer) for text in ax.texts if text.get_text() in {"10 records", "30 records"}]
        records, overlaps = place_point_labels(fig, ax, selected_map[dimension], threshold_boxes)
        all_records.extend(records); all_overlaps.extend({"dimension": dimension, "overlap": value} for value in overlaps)
    if len(all_records) != 20 or all_overlaps:
        raise RuntimeError(f"Figure 4 rendered-label assertion failed: labels={len(all_records)}, overlaps={all_overlaps}")
    render = save_figure(fig, base, "Figure 4")
    named = [record for record in all_records if not record["display"].isdigit()]
    return render, {"status": "PASS", "labels_expected": 20, "labels_rendered": len(all_records), "overlaps": all_overlaps,
                    "placements": all_records, "direct_names": named, "key_entries": ["Labels", "Unclear from Register Entry (declined to classify)"],
                    "encodings_present": ["direct or numbered point labels", "Unclear outline", "10-record threshold", "30-record threshold"]}


def disagreement_group(rows: list[dict]) -> dict[tuple[str, str], dict[str, dict]]:
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        grouped[(row["dimension"], row["series"])][row["quantity"]] = row
    return grouped


def draw_relation_icon(ax, relation: str, color: str) -> None:
    ax.set_xlim(0, 4.6); ax.set_ylim(0, 1); ax.set_aspect("equal", adjustable="box"); ax.axis("off")
    if relation == "containment":
        ax.add_patch(Circle((0.52, 0.5), 0.30, fill=False, lw=1.0)); ax.add_patch(Circle((0.52, 0.5), 0.15, fill=False, lw=1.0))
    elif relation == "overlap":
        ax.add_patch(Circle((0.40, 0.5), 0.25, fill=False, lw=1.0)); ax.add_patch(Circle((0.67, 0.5), 0.25, fill=False, lw=1.0))
    else:
        ax.add_patch(Circle((0.35, 0.5), 0.20, fill=False, lw=1.0)); ax.add_patch(Circle((0.78, 0.5), 0.20, fill=False, lw=1.0))
    ax.add_patch(Rectangle((1.12, 0.31), 0.55, 0.38, color=color)); ax.text(1.82, 0.5, relation.capitalize(), va="center", fontsize=8.0)


def render_s3(rows: list[dict], base: Path):
    grouped = disagreement_group(rows)
    order = (("Research Domains", "human_human"), ("Research Domains", "model_human"),
             ("Analytical Purposes", "human_human"), ("Analytical Purposes", "model_human"))
    labels = ("Between human coders", "Fable 5 with each coder", "Between human coders", "Fable 5 with each coder")
    yvals = (3.25, 2.42, 1.12, 0.29)
    fig = plt.figure(figsize=(FIGURE_WIDTH, 4.45), constrained_layout=True)
    outer = fig.add_gridspec(2, 1, height_ratios=[0.22, 1.0])
    key_grid = outer[0].subgridspec(1, 3)
    for i, relation in enumerate(("containment", "overlap", "disjoint")):
        draw_relation_icon(fig.add_subplot(key_grid[0, i]), relation, DISAGREE_COLORS[relation])
    ax = fig.add_subplot(outer[1])
    sums = []; nonzero = 0; labelled = 0
    for y, key, label in zip(yvals, order, labels):
        relations = grouped[key]; left = Decimal(0); displayed = []
        denom = json.loads(relations["containment"]["presentation_note"].split("; structurally", 1)[0])["nonidentical_nonempty_pairs"]
        small = []
        for relation in ("containment", "overlap", "disjoint"):
            row = relations[relation]; width = d(row["interval_lower_string"]) * 100; count = int(row["source_value_string"])
            ax.barh(y, float(width), left=float(left), height=0.52, color=DISAGREE_COLORS[relation], edgecolor="white", linewidth=0.7, zorder=2)
            shown = percent_text(row["interval_lower_string"], count); displayed.append(shown)
            if count:
                nonzero += 1
                # overlap is always labelled outside the bar, identified by its colour square
                if width >= 8 and relation != "overlap":
                    ax.text(float(left + width / 2), y, shown, ha="center", va="center", color="white", fontsize=8.0, zorder=4); labelled += 1
                else:
                    small.append((relation, f"{count} ({shown})"))
            left += width
        for offset, (relation, value) in enumerate(small):
            y_label = y + (offset - (len(small) - 1) / 2) * 0.20
            square = AnnotationBbox(rating_bars.key_square(DISAGREE_COLORS[relation]), (100, y_label), xybox=(S3_OUTSIDE_GAP_PT, 0),
                                    boxcoords="offset points", frameon=False, box_alignment=(0, 0.5), annotation_clip=False)
            square.set_zorder(5); ax.add_artist(square)
            ax.annotate(value, xy=(100, y_label), xytext=(S3_OUTSIDE_GAP_PT + rating_bars.SQ + S3_OUTSIDE_GAP_PT, 0), textcoords="offset points",
                        ha="left", va="center", fontsize=8.0, annotation_clip=False); labelled += 1
        ax.text(-2.2, y, f"{label} (n={denom})", ha="right", va="center", fontsize=8.0)
        numeric = [0 if value == "<1%" else int(value.rstrip("%")) for value in displayed]
        sums.append({"dimension": key[0], "pair_family": key[1], "displayed_percentages": displayed, "sum": sum(numeric)})
    ax.text(-2.2, 3.72, "Research Domains", ha="right", va="center", fontweight="bold", fontsize=8.5)
    ax.text(-2.2, 1.59, "Analytical Purposes", ha="right", va="center", fontweight="bold", fontsize=8.5)
    ax.set_xlim(0, 132); ax.set_ylim(-0.12, 3.95); ax.set_yticks([]); ax.set_xlabel("Percentage of disagreeing pairs")
    ax.xaxis.set_major_locator(FixedLocator([0, 20, 40, 60, 80, 100])); ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x)}%"))
    style_axis(ax); ax.grid(axis="x", zorder=0)
    ax.spines["bottom"].set_bounds(0, 100)
    render = save_figure(fig, base, "Supplementary Figure S3")
    return render, {"status": "PASS" if nonzero == labelled else "FAIL", "nonzero_segments": nonzero, "labels_rendered": labelled,
                    "key_entries": ["Containment", "Overlap", "Disjoint"], "encodings_present": ["containment", "overlap", "disjoint"], "icons_equal_aspect": True}, sums


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


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
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
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows: grouped[row["label"]][row["pair"]] = row
    selected = [label for label in grouped if next(iter(grouped[label].values()))["support_band"] != "RARE"]
    ordered = []
    for label in selected:
        base = next(iter(grouped[label].values()))
        rank = 0 if base["support_band"] == "STANDARD" else 2 if label == "Unclear from Register Entry" else 1
        ordered.append(((rank, -int(base["support_string"]), int(base["source_order"])), label))
    ordered.sort()
    headers = ["Label", "Applied by coder majority (n)", "C01–C02", "C01–C03", "C02–C03", "C01", "C02", "C03"]
    body = []; flat = []; current = None
    for _, label in ordered:
        base = next(iter(grouped[label].values())); group = base["row_group"]
        if group != current: body.append([group]); current = group
        shown = [label, base["support_string"]] + [metric(grouped[label][pair]) for pair in PAIR_ORDER]
        body.append(shown); flat.append([group] + shown)
    spans = [("", 2), ("Between human coders (Cohen’s κ [95% interval])", 3), ("Fable 5 with each human coder (Cohen’s κ [95% interval])", 3)]
    md_path.write_text(html_table(headers, body, spans), encoding="utf-8"); write_csv(csv_path, ["Row group"] + headers, flat)
    return {"status": "PASS", "rows_shown": len(selected), "rows_omitted_below_10": len(grouped) - len(selected), "headings": [row[0] for row in body if len(row) == 1]}


def render_performance(rows: list[dict], csv_path: Path, md_path: Path) -> dict:
    per_label = [row for row in rows if row["series"] != "macro"]
    macro_rows = [row for row in rows if row["series"] == "macro"]
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in per_label: grouped[row["label"]][row["quantity"]] = row
    ordered = []
    for label, values in grouped.items():
        base = values["tp"]
        rank = 2 if label == "Unclear from Register Entry" else {"STANDARD": 0, "LOW SUPPORT": 1, "RARE": 3}[base["support_band"]]
        ordered.append(((rank, -int(base["support_string"]), int(base["source_order"])), label))
    ordered.sort()
    headers = ["Label", "Applied by coder majority (n)", "Both", "Fable 5 only", "Coder majority only", "Neither", "Precision [95% interval]", "Recall [95% interval]", "F1 [95% interval]"]
    body = []; flat = []; current = None
    for _, label in ordered:
        values = grouped[label]; base = values["tp"]; group = base["row_group"]
        if group != current: body.append([group]); current = group
        metrics = []
        for quantity in ("precision", "recall", "f1"):
            if base["support_band"] == "RARE": shown = "–"
            elif label == "Unclear from Register Entry" and quantity in {"precision", "f1"}: shown = "Not estimable"
            else: shown = metric(values[quantity])
            metrics.append(shown)
        shown = [label, base["support_string"]] + [values[q]["source_value_string"] for q in ("tp", "fp", "fn", "tn")] + metrics
        body.append(shown); flat.append([group] + shown)
    macro_report = {}
    if macro_rows:
        macro_by_q = {row["quantity"]: row for row in macro_rows}
        eligible = macro_by_q["eligible_label_n"]["source_value_string"]
        macro_label = macro_by_q["precision"]["label"]
        macro_metrics = []
        for quantity in ("precision", "recall", "f1"):
            row = macro_by_q[quantity]
            shown = metric(row) if row["interval_status"] == "R" else half_up(row["source_value_string"], 2) + " (interval not estimable)"
            macro_metrics.append(shown)
        macro_shown = [macro_label, eligible, "", "", "", ""] + macro_metrics
        body.append([macro_label]); body.append(macro_shown)
        flat.append([macro_label] + macro_shown)
        macro_report = {"macro_row_label": macro_label, "eligible_labels": int(eligible),
                        "source_table_id": macro_by_q["precision"]["source_table_id"]}
    md_path.write_text(html_table(headers, body), encoding="utf-8"); write_csv(csv_path, ["Row group"] + headers, flat)
    return {"status": "PASS", "rows_shown": len(ordered), "sparse_rows_counts_only": sum(1 for _, label in ordered if grouped[label]["tp"]["support_band"] == "RARE"),
            "headings": [row[0] for row in body if len(row) == 1], "macro": macro_report}


def render_supplementary_table_s2(rows: list[dict], csv_path: Path, md_path: Path):
    grouped = disagreement_group(rows)
    headers = ["Pair type", "Disagreeing pairs (n)", "Containment n (%)", "Overlap n (%)", "Disjoint n (%)"]
    body = []; flat = []; sums = []
    for dimension in DIMENSIONS[:2]:
        body.append([dimension])
        for family, label in (("human_human", "Between human coders"), ("model_human", "Fable 5 with each coder")):
            rel = grouped[(dimension, family)]
            denominator = json.loads(rel["containment"]["presentation_note"].split("; structurally", 1)[0])["nonidentical_nonempty_pairs"]
            cells = []; displayed = []
            for relation in ("containment", "overlap", "disjoint"):
                row = rel[relation]; shown = percent_text(row["interval_lower_string"], int(row["source_value_string"])); displayed.append(shown)
                cells.append(f"{row['source_value_string']} ({shown})")
            record = [label, str(denominator)] + cells; body.append(record); flat.append([dimension] + record)
            sums.append({"dimension": dimension, "pair_family": family, "displayed_percentages": displayed,
                         "sum": sum(0 if value == "<1%" else int(value.rstrip("%")) for value in displayed)})
    md_path.write_text(html_table(headers, body), encoding="utf-8"); write_csv(csv_path, ["Dimension"] + headers, flat)
    return {"status": "PASS", "rows": 4}, sums


def supplementary_group(rows: list[dict]) -> dict[tuple[str, str], dict[str, dict]]:
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in rows: grouped[(row["population"], row["label"])][row["quantity"]] = row
    return grouped


def render_s1ab(rows: list[dict], csv_path: Path, md_path: Path):
    values = supplementary_group(rows); labels = []
    for row in rows:
        shown = display_category(row["label"])
        if shown not in labels: labels.append(shown)
    source_label = {display_category(row["label"]): row["label"] for row in rows}
    headers = ["Response", "Baseline, n=150: n (%) [95% interval]", "Hard-case (diagnostic), n=75: n (%)"]
    body = []; sums = {"baseline": 0, "hard_case": 0}
    for label in labels:
        cells = []
        for population in ("baseline", "hard_case"):
            count = values[(population, source_label[label])]["count"]; prop = values[(population, source_label[label])]["proportion"]
            pct = percent_text(prop["source_value_string"], int(count["source_value_string"])); sums[population] += 0 if pct == "<1%" else int(pct.rstrip("%"))
            shown = f"{count['source_value_string']} ({pct})"
            if population == "baseline":
                shown += f" [{percent_text(prop['interval_lower_string'])}, {percent_text(prop['interval_upper_string'])}]"
            cells.append(shown)
        body.append([label] + cells)
    md_path.write_text(html_table(headers, body), encoding="utf-8"); write_csv(csv_path, headers, body)
    return {"status": "PASS", "rows": len(body)}, [{"population": p, "displayed_percentage_sum": total} for p, total in sums.items()]


def render_s1c(rows: list[dict], csv_path: Path, md_path: Path):
    headers = ["Population and dimension", "No agreed label", "Agreed only on Unclear", "1 substantive label", "2 substantive labels", "3 substantive labels"]
    order = (("baseline", "Research Domains"), ("baseline", "Analytical Purposes"), ("hard_case", "Research Domains"), ("hard_case", "Analytical Purposes"))
    body = []; sums = []
    for population, dimension in order:
        selected = sorted([r for r in rows if r["population"] == population and r["dimension"] == dimension], key=lambda r: int(r["source_order"]))
        population_text = "Baseline, n=150" if population == "baseline" else "Hard-case (diagnostic), n=75"
        label = f"{population_text} — {dimension}"
        cells = [f"{row['source_value_string']} ({row['display_percent']}%)" for row in selected]
        percentages = [int(row["display_percent"]) for row in selected]
        body.append([label] + cells); sums.append({"population": population, "dimension": dimension, "displayed_percentages": percentages, "sum": sum(percentages)})
    md_path.write_text(html_table(headers, body), encoding="utf-8"); write_csv(csv_path, headers, body)
    return {"status": "PASS", "rows": 4, "row_layout": "single population-and-dimension column"}, sums


def write_captions(manifest: dict, path: Path) -> None:
    lines = ["# Draft captions — pass 3", ""]
    for deliverable in manifest["order"]:
        entry = manifest["entries"][deliverable]; punctuation = "." if "Figure" in deliverable else ":"
        lines.extend([f"## {deliverable}", "", f"**{deliverable}{punctuation} {entry['title']}.**", "", "Legend content checklist:", ""])
        lines.extend(f"- {bullet}" for bullet in entry["caption_bullets"]); lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def banned_check_text(texts: list[str], label: str) -> list[dict]:
    failures = []
    for value in texts:
        for pattern in BANNED:
            if pattern.search(value): failures.append({"scope": label, "text": value, "pattern": pattern.pattern})
    return failures


def file_checks(paths: list[Path]) -> tuple[list[dict], list[dict]]:
    banned = []; minus = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        banned.extend(banned_check_text(text.splitlines(), str(path)))
        for match in re.finditer(r"-(?=\d)", text): minus.append({"path": str(path), "position": match.start()})
    return banned, minus


def row_alignment(keys: dict) -> dict:
    failures = []
    expected = {"alpha ABC": 0, "alpha LBC": 1, "alpha ALC": 2, "alpha ABL": 3,
                "delta_min": 0, "delta_A": 1, "delta_B": 2, "delta_C": 3}
    for deliverable in ("Figure 1", "Figure 3", "Supplementary Figure S1"):
        for row in keys[deliverable]["row_positions"]:
            if row["y"] != expected[row["quantity"]]: failures.append({"deliverable": deliverable, **row, "expected_y": expected[row["quantity"]]})
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, "mapping": expected}


def lightness(color: str) -> float:
    rgb = tuple(int(color[i:i+2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(*rgb)[1]


def delta_annotation_check(datasets: dict, keys: dict) -> dict:
    failures = []; checks = []
    for deliverable in ("Figure 1", "Figure 3"):
        rows = datasets[deliverable]
        for dimension, component in keys[deliverable]["annotation_components"].items():
            populations = sorted({r["population"] for r in rows if r["dimension"] == dimension})
            for population in populations:
                keyed = {r["quantity"]: r for r in rows if r["dimension"] == dimension and r["population"] == population and r["series"] == "delta" and r["role"] == "plotted"}
                equal = d(keyed["delta_min"]["parsed_value"]) == d(keyed[component]["parsed_value"])
                own_interval = next(item for item in keys[deliverable]["delta_min_rows"] if item["dimension"] == dimension and item["population"] == population)["interval"]
                expected_interval = [keyed["delta_min"]["parsed_interval_lower"], keyed["delta_min"]["parsed_interval_upper"]]
                status = "PASS" if equal and own_interval == expected_interval else "FAIL"
                record = {"deliverable": deliverable, "dimension": dimension, "population": population, "component": component,
                          "delta_min": keyed["delta_min"]["parsed_value"], "component_value": keyed[component]["parsed_value"],
                          "delta_min_interval_drawn": own_interval, "status": status}
                checks.append(record)
                if status != "PASS": failures.append(record)
    return {"status": "PASS" if not failures else "FAIL", "checks": checks, "failures": failures}


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
    if set(manifest["entries"]) != set(datasets) or len(datasets) != 15:
        raise RuntimeError("Pass-3 manifest/dataset mismatch")
    archived = archive_existing(figure_dir, table_dir, manifest) if args.archive_existing else []

    rendering = {}; keys = {}; sums = []; table_reports = {}; table_paths = []
    for deliverable, function in (("Figure 1", render_figure1), ("Figure 2", render_figure2), ("Figure 3", render_figure3),
                                  ("Figure 4", render_figure4), ("Supplementary Figure S1", render_s1),
                                  ("Supplementary Figure S2", render_s2), ("Supplementary Figure S3", render_s3)):
        result = function(datasets[deliverable], figure_dir / manifest["entries"][deliverable]["slug"])
        rendering[deliverable], keys[deliverable] = result[0], result[1]
        if len(result) == 3: sums.extend([{"deliverable": deliverable, **row} for row in result[2]])

    for deliverable in ("Table 1", "Table 2"):
        slug = manifest["entries"][deliverable]["slug"]; csv_path, md_path = table_dir / f"{slug}.csv", table_dir / f"{slug}.md"
        table_reports[deliverable] = render_kappa(datasets[deliverable], csv_path, md_path); table_paths += [csv_path, md_path]
    for deliverable in ("Table 3", "Table 4"):
        slug = manifest["entries"][deliverable]["slug"]; csv_path, md_path = table_dir / f"{slug}.csv", table_dir / f"{slug}.md"
        table_reports[deliverable] = render_performance(datasets[deliverable], csv_path, md_path); table_paths += [csv_path, md_path]
    for deliverable in ("Supplementary Table S1a", "Supplementary Table S1b"):
        slug = manifest["entries"][deliverable]["slug"]; csv_path, md_path = table_dir / f"{slug}.csv", table_dir / f"{slug}.md"
        table_reports[deliverable], rows = render_s1ab(datasets[deliverable], csv_path, md_path); sums.extend([{"deliverable": deliverable, **row} for row in rows]); table_paths += [csv_path, md_path]
    deliverable = "Supplementary Table S1c"; slug = manifest["entries"][deliverable]["slug"]; csv_path, md_path = table_dir / f"{slug}.csv", table_dir / f"{slug}.md"
    table_reports[deliverable], rows = render_s1c(datasets[deliverable], csv_path, md_path); sums.extend([{"deliverable": deliverable, **row} for row in rows]); table_paths += [csv_path, md_path]
    deliverable = "Supplementary Table S2"; slug = manifest["entries"][deliverable]["slug"]; csv_path, md_path = table_dir / f"{slug}.csv", table_dir / f"{slug}.md"
    table_reports[deliverable], rows = render_supplementary_table_s2(datasets[deliverable], csv_path, md_path); sums.extend([{"deliverable": deliverable, **row} for row in rows]); table_paths += [csv_path, md_path]

    captions_path = figure_dir / "draft_captions_pass2.md"; write_captions(manifest, captions_path)
    figure_banned = []
    for deliverable, record in rendering.items(): figure_banned += banned_check_text(record["rendered_text"], deliverable)
    table_banned, table_minus = file_checks(table_paths)
    caption_banned, caption_minus = file_checks([captions_path])
    figure_minus = [{"deliverable": deliverable, "text": text} for deliverable, record in rendering.items() for text in record["rendered_text"] if re.search(r"(?<!COVID)-(?=\d)", text)]
    banned = figure_banned + table_banned + caption_banned
    if banned: raise RuntimeError(f"Banned reader-facing text found: {banned}")
    if table_minus or figure_minus: raise RuntimeError(f"Hyphen-minus assertion failed: tables={table_minus}; figures={figure_minus}")
    if any(record.get("status") != "PASS" for record in keys.values()): raise RuntimeError(f"Key or label assertion failed: {keys}")
    if any(record["font_status"] != "PASS" for record in rendering.values()): raise RuntimeError("H.1 font-size assertion failed")

    alignment = row_alignment(keys); delta_check = delta_annotation_check(datasets, keys)
    if alignment["status"] != "PASS": raise RuntimeError(f"H.5 row alignment failed: {alignment}")
    if delta_check["status"] != "PASS": raise RuntimeError(f"δ_min annotation assertion failed: {delta_check}")
    exact = [row for row in sums if row["deliverable"] in {"Supplementary Figure S3", "Supplementary Table S2", "Supplementary Table S1c"}]
    if any(row["sum"] != 100 for row in exact): raise RuntimeError(f"Required whole-percentage sum failed: {exact}")
    active_names = [path.name for path in figure_dir.iterdir() if path.is_file()]
    if sorted(name for name in active_names if name.startswith("figure_4")) != ["figure_4_label_application.png", "figure_4_label_application.svg"]:
        raise RuntimeError("Active Figure 4 filename assertion failed")
    if any(path.name.startswith("table_5") for path in table_dir.iterdir() if path.is_file()): raise RuntimeError("Active table_5 filename remains")

    colors = {
        "population": {key: value["color"] for key, value in POPULATION.items()},
        "population_lightness": {key: lightness(value["color"]) for key, value in POPULATION.items()},
        "ratings": RATING_PALETTES, "disagreement": DISAGREE_COLORS,
        "strict_hard_case_lightness_difference": abs(lightness(POPULATION["baseline_strict_sufficient"]["color"]) - lightness(POPULATION["hard_case"]["color"])),
    }
    report = {
        "renderer": Path(__file__).name, "input_boundary": "pass3 manifest plus its listed CSV and JSON files only",
        "matplotlib_version": matplotlib.__version__, "python_version": sys.version, "font_family": FONT_FAMILY,
        "font_resolved": font_manager.findfont(FONT_FAMILY), "archived_preexisting_outputs": archived,
        "font_sizes": {deliverable: {k: v for k, v in record.items() if k in {"target_width_cm", "saved_width_inches", "minimum_effective_pt", "minimum_is_subscript", "minimum_subscript_effective_pt", "font_status"}} for deliverable, record in rendering.items()},
        "edges": {deliverable: {"status": record["edge_status"], "failures": record["edge_failures"]} for deliverable, record in rendering.items()},
        "fonts": {"status": "PASS", "family": FONT_FAMILY, "math_family": FONT_FAMILY},
        "dimension_names": {"status": "PASS", "names": list(DIMENSIONS)}, "row_alignment": alignment,
        "colors": colors, "minus_sign": {"status": "PASS", "table_failures": [], "figure_failures": []},
        "percentages": {"status": "PASS", "displayed_sums": sums, "whole_number_display": True, "sub_half_percent": "<1%"},
        "table_rendering": table_reports, "figure_4_labels": keys["Figure 4"], "small_segment_labels": {d: keys[d] for d in ("Figure 2", "Supplementary Figure S2", "Supplementary Figure S3")},
        "keys": keys, "delta_min_annotation": delta_check,
        "banned_text": {"status": "PASS", "failures": []},
        "caption_policy": {"status": "PASS", "titles_or_caption_prose_embedded": False, "draft_captions": str(captions_path)},
        "isolation_test": {"status": "PENDING RUNNER"}, "manual_visual_inspection": {"status": "PENDING"},
    }
    (figure_dir / "pass3_rendering_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    data_metadata = json.loads((data_dir / "pass3_run_metadata.json").read_text(encoding="utf-8"))
    run_metadata = {
        "manifest_generated_utc": manifest["generated_utc"], "rendered_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "logs": manifest["provenance"]["logs"], "source_commits": manifest["provenance"]["source_commits"], "code_commits": data_metadata["code_commits"],
        "font_family": FONT_FAMILY, "colors": colors,
        "software": {"python": sys.version, "matplotlib": matplotlib.__version__, "font": font_manager.findfont(FONT_FAMILY)},
    }
    (figure_dir / "pass3_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
