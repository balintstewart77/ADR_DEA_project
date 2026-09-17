"""Alternative layouts for Figure 4 (label application).

Reads only analysis/figure_data/figure_4_label_application.csv and writes
figure_4_label_application_alt_scatter_inset.{png,svg} and
figure_4_label_application.{png,svg} (the dumbbell chart, chosen as Figure 4;
run with --only dumbbell). Layout only; no counts are derived or altered.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import Bbox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figure_style  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "analysis" / "figure_data" / "figure_4_label_application.csv"
OUT = Path(os.environ.get("FIG4_ALT_OUT", ROOT / "analysis" / "figures"))

FIG_WIDTH = 17 / 2.54
MIN_PT = 8.0
DPI = 100
DIMENSIONS = ("Research Domains", "Analytical Purposes")
UNCLEAR = "Unclear from Register Entry"
UNCLEAR_NAME = "Unclear from Register Entry (declined to classify)"
POINT_COLOR = "#28658C"
RING_COLOR = "#8A4F7D"
POINT_S, RING_S = 35, 95          # main panels (as in the current Figure 4)
INSET_POINT_S, INSET_RING_S = 24, 65
AX_MIN, AX_MAX = -1.5, 60
ZOOM = (-1.0, 14.0)               # square zoom region used in both panels
ZOOM_MAX_COUNT = 14               # points with both counts <= 14 belong to the zoom

def load() -> dict[str, list[dict]]:
    with DATA.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    out = {}
    for dim in DIMENSIONS:
        sel = [r for r in rows if r["dimension"] == dim]
        for r in sel:
            r["coder"] = int(r["parsed_value"])           # human-majority-positive count (x)
            r["fable"] = int(r["parsed_interval_lower"])  # model-positive count (y)
            assert str(r["coder"]) == r["source_value_string"] and str(r["fable"]) == r["interval_lower_string"]
        out[dim] = sorted(sel, key=lambda r: int(r["source_order"]))
    return out


# ---------------------------------------------------------------- geometry (display pixels)
def px(v_pt: float) -> float:
    return v_pt * DPI / 72


def seg_samples(p0, p1, step=1.0) -> np.ndarray:
    n = max(2, int(math.dist(p0, p1) / step))
    t = np.linspace(0, 1, n + 1)[:, None]
    return np.asarray(p0) * (1 - t) + np.asarray(p1) * t


def box_hits_samples(box: Bbox, samples: np.ndarray, pad=0.0) -> bool:
    if len(samples) == 0:
        return False
    s = samples
    return bool(np.any((s[:, 0] >= box.x0 - pad) & (s[:, 0] <= box.x1 + pad) & (s[:, 1] >= box.y0 - pad) & (s[:, 1] <= box.y1 + pad)))


def point_box_dist(box: Bbox, p) -> float:
    dx = max(box.x0 - p[0], 0, p[0] - box.x1)
    dy = max(box.y0 - p[1], 0, p[1] - box.y1)
    return math.hypot(dx, dy)


def circle_hits_box(box: Bbox, centre, r) -> bool:
    return point_box_dist(box, centre) < r


def grow(box: Bbox, pad: float) -> Bbox:
    return Bbox.from_extents(box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad)


# ---------------------------------------------------------------- version 1
LABEL_PT = 9.0
LABEL_PT_REDUCED = 8.0
COLLISION_PAD_PT = 2.0
FRAME_GREY, FRAME_LW = "0.6", 0.8
INSET_BOUNDS = (34.0, 5.0, 24.0, 24.0)  # x0, y0, width, height in main-panel data coordinates

MAIN_SHORT = {
    "Labour Market & Employment": "Labour Market",
    "Business & Productivity": "Business",
    "Education & Skills": "Education & Skills",
    "Health & Social Care": "Health & Social Care",
    "Descriptive Monitoring": "Descriptive Monitoring",
    "Outcome Tracking": "Outcome Tracking",
    "Policy Evaluation / Impact Analysis": "Policy Evaluation",
    UNCLEAR: "Unclear from Register Entry",
}


def marker_radius_px(s: float, lw: float) -> float:
    return px(math.sqrt(s) / 2 + lw / 2)


def side_of(row) -> str:
    return "left" if row["fable"] > row["coder"] else "right"


def annotate_by_rule(ax, row, text, fontsize):
    """Above the equality line: label left of the point; below or on it: label right."""
    left = side_of(row) == "left"
    return ax.annotate(text, xy=(row["coder"], row["fable"]), xytext=(-5, 0) if left else (5, 0),
                       textcoords="offset points", ha="right" if left else "left", va="center",
                       fontsize=fontsize, annotation_clip=False, zorder=8)


def rect_edges(box: Bbox) -> np.ndarray:
    c = [(box.x0, box.y0), (box.x1, box.y0), (box.x1, box.y1), (box.x0, box.y1)]
    return np.vstack([seg_samples(a, b) for a, b in zip(c, c[1:] + c[:1])])


def render_scatter(data):
    left_margin, gap, panel = 0.55, 0.62, 2.70
    key_lines = max(sum(r["coder"] <= ZOOM_MAX_COUNT and r["fable"] <= ZOOM_MAX_COUNT for r in data[d]) for d in DIMENSIONS)
    key_block = 0.24 + key_lines * 11.2 / 72
    panel_bottom = 0.74 + key_block + 0.08
    H = panel_bottom + panel + 0.42
    fig = plt.figure(figsize=(FIG_WIDTH, H), dpi=DPI)
    panels = {}
    for i, dim in enumerate(DIMENSIONS):
        rows = data[dim]
        ax = fig.add_axes([(left_margin + i * (panel + gap)) / FIG_WIDTH, panel_bottom / H, panel / FIG_WIDTH, panel / H])
        ax.plot([AX_MIN, AX_MAX], [AX_MIN, AX_MAX], color="#4D4D4D", linestyle="--", linewidth=0.8, zorder=1)
        for r in rows:
            ax.scatter(r["coder"], r["fable"], s=POINT_S, color=POINT_COLOR, edgecolor="black", linewidth=0.55, zorder=4)
            if r["label"] == UNCLEAR:
                ax.scatter(r["coder"], r["fable"], s=RING_S, facecolors="none", edgecolors=RING_COLOR, linewidths=1.35, zorder=5)
        ax.set(xlim=(AX_MIN, AX_MAX), ylim=(AX_MIN, AX_MAX), aspect="equal",
               xlabel="Records labelled by the coder majority", ylabel="Records labelled by Fable 5")
        ax.set_xticks(range(0, 61, 10)); ax.set_yticks(range(0, 61, 10))
        ax.tick_params(labelsize=8.0, length=3)
        ax.xaxis.label.set_size(8.5); ax.yaxis.label.set_size(8.5)
        ax.set_title(dim, fontweight="bold", fontsize=9.0, pad=8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True); ax.grid(color="#E7E7E7", linewidth=0.55, zorder=0)

        # zoom rectangle (no connectors) and inset
        ax.add_patch(Rectangle((ZOOM[0], ZOOM[0]), ZOOM[1] - ZOOM[0], ZOOM[1] - ZOOM[0], fill=False,
                               edgecolor=FRAME_GREY, linewidth=FRAME_LW, zorder=3))
        inset = ax.inset_axes(list(INSET_BOUNDS), transform=ax.transData)
        in_rows = [r for r in rows if r["coder"] <= ZOOM_MAX_COUNT and r["fable"] <= ZOOM_MAX_COUNT]
        inset.plot(ZOOM, ZOOM, color="#4D4D4D", linestyle="--", linewidth=0.8, zorder=1)
        for r in in_rows:
            inset.scatter(r["coder"], r["fable"], s=INSET_POINT_S, color=POINT_COLOR, edgecolor="black", linewidth=0.5, zorder=4, clip_on=False)
            if r["label"] == UNCLEAR:
                inset.scatter(r["coder"], r["fable"], s=INSET_RING_S, facecolors="none", edgecolors=RING_COLOR, linewidths=1.2, zorder=5, clip_on=False)
        inset.set(xlim=ZOOM, ylim=ZOOM, aspect="equal")
        inset.set_xticks([0, 5, 10]); inset.set_yticks([0, 5, 10])
        inset.tick_params(labelsize=8.0, length=2, pad=1.5)
        inset.set_facecolor("white")
        inset.set_zorder(6)
        for s in inset.spines.values():
            s.set_linewidth(FRAME_LW); s.set_color(FRAME_GREY)

        main_rows = sorted([r for r in rows if r not in in_rows], key=lambda r: (-r["coder"], r["label"]))
        main_labels = [{"row": r, "where": "main", "text": MAIN_SHORT[r["label"]], "artist": annotate_by_rule(ax, r, MAIN_SHORT[r["label"]], LABEL_PT)}
                       for r in main_rows]
        ordered = sorted(in_rows, key=lambda r: (-r["coder"], r["label"]))
        numbers = {r["label"]: n for n, r in enumerate(ordered, start=1)}
        inset_labels = [{"row": r, "where": "inset", "text": str(numbers[r["label"]]), "artist": annotate_by_rule(inset, r, str(numbers[r["label"]]), LABEL_PT)}
                        for r in ordered]

        key_x = ax.get_position().x0 - 0.35 / FIG_WIDTH
        key_top = panel_bottom - 0.74
        fig.text(key_x, key_top / H, "Inset", fontsize=8.5, fontweight="bold", ha="left", va="top")
        for k, r in enumerate(ordered):
            y = (key_top - 0.2 - k * 11.2 / 72) / H
            name = UNCLEAR_NAME if r["label"] == UNCLEAR else r["label"]
            fig.text(key_x + 0.10 / FIG_WIDTH, y, str(numbers[r["label"]]), fontsize=8.0, ha="right", va="top")
            fig.text(key_x + 0.17 / FIG_WIDTH, y, name, fontsize=8.0, ha="left", va="top")
        panels[dim] = {"ax": ax, "inset": inset, "rows": rows, "in_rows": in_rows, "labels": main_labels + inset_labels}
    return fig, panels


def label_collisions(fig, panels, dim, label) -> list[str]:
    """What a label's rendered box (padded by 2 pt) touches. Main labels are checked in the main panel, inset
    labels inside their inset."""
    renderer = fig.canvas.get_renderer()
    p = panels[dim]
    ax, inset = p["ax"], p["inset"]
    host = ax if label["where"] == "main" else inset
    text_box = Text.get_window_extent(label["artist"], renderer)
    box = grow(text_box, px(COLLISION_PAD_PT))
    hits = []
    for other in p["labels"]:
        if other is not label and other["where"] == label["where"] and box.overlaps(Text.get_window_extent(other["artist"], renderer)):
            hits.append(f"label '{other['text']}'")
    rows = p["rows"] if label["where"] == "main" else p["in_rows"]
    for r in rows:
        if label["where"] == "main":
            rad = marker_radius_px(RING_S, 1.35) if r["label"] == UNCLEAR else marker_radius_px(POINT_S, 0.55)
        else:
            rad = marker_radius_px(INSET_RING_S, 1.2) if r["label"] == UNCLEAR else marker_radius_px(INSET_POINT_S, 0.5)
        centre = host.transData.transform((r["coder"], r["fable"]))
        if r is label["row"]:
            # the rule fixes the gap to the label's own marker at 5 pt, so only an actual overlap counts here
            if circle_hits_box(text_box, centre, rad):
                hits.append(f"own marker{' ring' if r['label'] == UNCLEAR else ''} (text overlaps it)")
        elif circle_hits_box(box, centre, rad):
            hits.append(f"marker {r['label']} ({r['coder']}, {r['fable']})")
    lim = (AX_MIN, AX_MAX) if label["where"] == "main" else ZOOM
    if box_hits_samples(box, seg_samples(host.transData.transform((lim[0], lim[0])), host.transData.transform((lim[1], lim[1])))):
        hits.append("equality line")
    host_box = host.get_window_extent(renderer)
    if label["where"] == "main":
        zoom = Bbox.from_extents(*ax.transData.transform((ZOOM[0], ZOOM[0])), *ax.transData.transform((ZOOM[1], ZOOM[1])))
        if box_hits_samples(box, rect_edges(zoom)):
            hits.append("zoom rectangle")
        if box.overlaps(inset.get_tightbbox(renderer)):
            hits.append("inset (frame or tick labels)")
    else:
        if box_hits_samples(box, rect_edges(host_box)):
            hits.append("inset frame")
        for tick in inset.get_xticklabels() + inset.get_yticklabels():
            if tick.get_visible() and tick.get_text() and box.overlaps(tick.get_window_extent(renderer)):
                hits.append(f"inset tick label '{tick.get_text()}'")
    if box.x0 < host_box.x0 or box.x1 > host_box.x1 or box.y0 < host_box.y0 or box.y1 > host_box.y1:
        hits.append("panel edge" if label["where"] == "main" else "inset edge")
    return hits


def resolve_scatter(fig, panels):
    """Report collisions; a colliding main-panel label is reduced by 1 pt once and re-checked. Nothing is moved."""
    fig.canvas.draw()
    report = {}
    for dim, p in panels.items():
        entries = []
        for label in p["labels"]:
            hits = label_collisions(fig, panels, dim, label)
            reduced = False
            if hits and label["where"] == "main":
                label["artist"].set_fontsize(LABEL_PT_REDUCED)
                fig.canvas.draw()
                reduced, first_hits = True, hits
                hits = label_collisions(fig, panels, dim, label)
            r = label["row"]
            entries.append({"where": label["where"], "text": label["text"], "label": r["label"], "coder_majority": r["coder"],
                            "fable5": r["fable"], "side": side_of(r), "font_pt": label["artist"].get_fontsize(),
                            "reduced_from_9pt_because": first_hits if reduced else [], "collisions": hits})
        report[dim] = entries
    # re-check everything at the end, since a reduction can change what other labels touch
    fig.canvas.draw()
    for dim, p in panels.items():
        for entry, label in zip(report[dim], p["labels"]):
            entry["collisions"] = label_collisions(fig, panels, dim, label)
    return report


# ---------------------------------------------------------------- version 2
def render_dumbbell(data):
    gap = 0.8
    fig = plt.figure(figsize=(FIG_WIDTH, 5.3), dpi=DPI)
    spans = {d: len(data[d]) - 1 + gap + 1.2 for d in DIMENSIONS}
    grid = fig.add_gridspec(2, 1, height_ratios=[spans[d] for d in DIMENSIONS], hspace=0.2,
                            left=0.34, right=0.97, top=0.95, bottom=0.15)
    axes, panels = [], {}
    for i, dim in enumerate(DIMENSIONS):
        ax = fig.add_subplot(grid[i, 0], sharex=axes[0] if axes else None)
        axes.append(ax)
        rows = data[dim]
        substantive = sorted([r for r in rows if r["label"] != UNCLEAR], key=lambda r: (-r["coder"], r["label"]))
        unclear = [r for r in rows if r["label"] == UNCLEAR]
        order = substantive + unclear
        ypos = {r["label"]: k for k, r in enumerate(substantive)}
        ypos[UNCLEAR] = len(substantive) + gap
        for r in order:
            y = ypos[r["label"]]
            ax.plot([r["coder"], r["fable"]], [y, y], color="#A0A0A0", linewidth=1.0, zorder=2, solid_capstyle="butt")
            ax.scatter(r["coder"], y, s=POINT_S, facecolor="white", edgecolor=POINT_COLOR, linewidth=1.1, zorder=3, clip_on=False)
            # filled Fable 5 marker drawn above the hollow one, so equal counts show only the filled marker
            ax.scatter(r["fable"], y, s=POINT_S, facecolor=POINT_COLOR, edgecolor=POINT_COLOR, linewidth=1.1, zorder=4, clip_on=False)
        ax.set_yticks([ypos[r["label"]] for r in order])
        ax.set_yticklabels([UNCLEAR_NAME if r["label"] == UNCLEAR else r["label"] for r in order])
        ax.set_ylim(ypos[UNCLEAR] + 0.6, -0.6)
        ax.set_xlim(0, 60)
        ax.set_xticks(range(0, 61, 10))
        ax.tick_params(labelsize=8.0, length=3)
        ax.tick_params(axis="y", length=0, pad=6)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#E7E7E7", linewidth=0.55, zorder=0)
        if i == 0:
            ax.spines["bottom"].set_visible(False)
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
        else:
            ax.set_xlabel("Records labelled", fontsize=8.5)
        panels[dim] = {"ax": ax, "order": order, "ypos": ypos}
    # left margin from the widest tick label, plus room for markers at x=0
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    widest = max(t.get_window_extent(renderer).width for ax in axes for t in ax.get_yticklabels())
    grid.update(left=(widest + px(6) + px(12)) / (FIG_WIDTH * DPI))
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    for dim, ax in zip(DIMENSIONS, axes):
        ax.set_title(dim, loc="left", fontweight="bold", fontsize=9.0, pad=5,
                     x=-(widest + px(6)) / ax.get_window_extent(renderer).width)
    handles = [
        Line2D([], [], marker="o", linestyle="none", markersize=math.sqrt(POINT_S), markerfacecolor="white",
               markeredgecolor=POINT_COLOR, markeredgewidth=1.1, label="Coder majority"),
        Line2D([], [], marker="o", linestyle="none", markersize=math.sqrt(POINT_S), markerfacecolor=POINT_COLOR,
               markeredgecolor=POINT_COLOR, markeredgewidth=1.1, label="Fable 5"),
    ]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.01), ncol=2, frameon=False, fontsize=8.0,
               handletextpad=0.4, columnspacing=2.0)
    return fig, panels


def verify_dumbbell(fig, panels):
    fig.canvas.draw()
    out = {}
    for dim, p in panels.items():
        ax = p["ax"]
        ticks = [t.get_text() for t in ax.get_yticklabels()]
        rows = []
        for r, tick, tpos in zip(p["order"], ticks, ax.get_yticks()):
            name = UNCLEAR_NAME if r["label"] == UNCLEAR else r["label"]
            # read marks back from the plotted artists on this row
            coll = [c for c in ax.collections if np.allclose(c.get_offsets()[:, 1], tpos)]
            hollow = [float(c.get_offsets()[0, 0]) for c in coll
                      if len(c.get_facecolor()) and np.allclose(c.get_facecolor()[0], [1, 1, 1, 1])]
            filled = [float(c.get_offsets()[0, 0]) for c in coll
                      if len(c.get_facecolor()) and c.get_facecolor()[0][3] > 0 and not np.allclose(c.get_facecolor()[0], [1, 1, 1, 1])]
            rows.append({"tick_label": tick, "coder_majority": r["coder"], "fable5": r["fable"],
                         "plotted_hollow_x": hollow, "plotted_filled_x": filled,
                         "ok": tick == name and hollow == [r["coder"]] and filled == [r["fable"]]})
        substantive = [r["coder"] for r in p["order"] if r["label"] != UNCLEAR]
        vlines = [l for l in ax.get_lines() if len(set(np.atleast_1d(l.get_xdata()))) == 1 and len(set(np.atleast_1d(l.get_ydata()))) > 1]
        rings = [c for c in ax.collections if len(c.get_facecolor()) == 0 or c.get_facecolor()[0][3] == 0]
        out[dim] = {"rings": len(rings), "marker_collections": len(ax.collections),
                    "bottom_spine_visible": ax.spines["bottom"].get_visible(),
                    "x_tick_marks_visible": any(t.tick1line.get_visible() for t in ax.xaxis.get_major_ticks()),
                    "x_tick_labels_visible": any(t.label1.get_visible() for t in ax.xaxis.get_major_ticks()),
                    "xlabel": ax.get_xlabel(), "gridline_x": [float(l.get_xdata()[0]) for l in ax.get_xgridlines() if l.get_visible()],
                    "rows": rows, "order_descending": substantive == sorted(substantive, reverse=True),
                    "unclear_last": p["order"][-1]["label"] == UNCLEAR, "vertical_data_lines": len(vlines)}
    return out


# ---------------------------------------------------------------- shared checks
def text_checks(fig):
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    fb = fig.bbox
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text().strip()]
    boxes = [(t, t.get_window_extent(renderer)) for t in texts]
    edge = [t.get_text() for t, b in boxes if b.x0 < fb.x0 + 1 or b.y0 < fb.y0 + 1 or b.x1 > fb.x1 - 1 or b.y1 > fb.y1 - 1]
    overlaps = [(a.get_text(), b.get_text()) for (a, ba), (b, bb) in itertools.combinations(boxes, 2)
                if ba.overlaps(bb) and ba.width and bb.width]
    return {"figure_width_cm": round(fig.get_figwidth() * 2.54, 2), "figure_height_cm": round(fig.get_figheight() * 2.54, 2),
            "smallest_font_pt": min(t.get_fontsize() for t in texts), "fonts": sorted({t.get_fontname() for t in texts}),
            "text_crossing_edge": edge, "text_text_overlaps": overlaps}


def save(fig, stem):
    base = OUT / stem
    fig.savefig(base.with_suffix(".png"), dpi=300, facecolor="white")
    fig.savefig(base.with_suffix(".svg"), format="svg", facecolor="white", metadata={"Date": None})


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else "dumbbell"
    figure_style.apply()
    data = load()
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}

    if only in (None, "scatter"):
        fig, panels = render_scatter(data)
        labels = resolve_scatter(fig, panels)
        report["scatter"] = {"text": text_checks(fig), "labels": labels,
                             "lines_in_main_panels": {d: len(p["ax"].get_lines()) for d, p in panels.items()},
                             "lines_in_insets": {d: len(p["inset"].get_lines()) for d, p in panels.items()},
                             "patches_in_main_panels": {d: [type(a).__name__ for a in p["ax"].patches] for d, p in panels.items()}}
        save(fig, "figure_4_label_application_alt_scatter_inset")
        plt.close(fig)

    if only in (None, "dumbbell"):
        fig, dpanels = render_dumbbell(data)
        report["dumbbell"] = {"text": text_checks(fig), "panels": verify_dumbbell(fig, dpanels)}
        save(fig, "figure_4_label_application")
        plt.close(fig)
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()
