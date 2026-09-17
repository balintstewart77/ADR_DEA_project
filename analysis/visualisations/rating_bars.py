"""Shared stacked rating-bar panels (Figure 2 and Supplementary Figure S2).

Drawing only: callers pass per-actor segments already read from the figure data.
Each segment is a dict with "category", "width" (percentage of records, Decimal or
float), "label" (displayed percentage) and "count" (records).
"""

from __future__ import annotations

from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import Rectangle
from matplotlib.ticker import FixedLocator, FuncFormatter

ACTORS = ("C01", "C02", "C03", "Majority of coders")
YPOS = (3.25, 2.35, 1.45, 0.35)          # gap before "Majority of coders"
YLIM = (-0.08, 3.58)
BAR_HEIGHT = 0.57
X_MAX = 130                              # 0-100% bars plus room for outside labels
X_TICKS = (0, 20, 40, 60, 80, 100)
SQ = 7                                   # outside-label square, points
LABEL_PT = 8.0
TITLE_PT = 9.0
INSIDE_PAD_PT = 2.0                      # clear space each side of an inside label
DARK_FACES = {"#246B45", "#5A4A86", "#5F5F5F", "#888888", "#A63D57"}


def key_square(face: str, hatched: bool = False) -> DrawingArea:
    """Return a fixed-size outside-label square in point coordinates."""
    da = DrawingArea(SQ, SQ, 0, 0)
    square = Rectangle((0, 0), SQ, SQ, facecolor=face, edgecolor="#555555", linewidth=0.6)
    da.add_artist(square)
    if hatched:
        for x0 in (-SQ * 0.35, SQ * 0.35):
            line = Line2D([x0, x0 + SQ], [0, SQ], color="white", linewidth=1.0,
                          solid_capstyle="butt", clip_on=True)
            line.set_clip_path(square)
            da.add_artist(line)
    return da


def key_handles(palette: dict[str, str], hatched) -> list[Rectangle]:
    return [Rectangle((0, 0), 1, 1, facecolor=face, edgecolor="#777", hatch="///" if category in hatched else None, label=category)
            for category, face in palette.items()]


def _style_bar_axis(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#E7E7E7", linewidth=0.55, zorder=0)
    ax.tick_params(length=3)


def _fits_inside(ax, text, width) -> bool:
    fig = ax.get_figure()
    segment_pt = float(width) / X_MAX * ax.get_position().width * fig.get_figwidth() * 72
    text_pt = text.get_window_extent(renderer=fig.canvas.get_renderer()).width * 72 / fig.dpi
    return text_pt + 2 * INSIDE_PAD_PT <= segment_pt


def draw_bars(ax, data: dict[str, list[dict]], palette: dict[str, str], hatched, show_xlabels: bool = False) -> dict:
    fig = ax.get_figure()
    # final limits first, so point offsets for outside labels convert at the scale they are drawn at
    ax.set_xlim(0, X_MAX); ax.set_ylim(*YLIM)
    inside, outside, segments, present = [], [], [], []
    nonzero = 0
    for actor, y in zip(ACTORS, YPOS):
        left = 0 * data[actor][0]["width"] if data[actor] else 0
        small = []
        for segment in data[actor]:
            category, width, count = segment["category"], segment["width"], segment["count"]
            present.append(category)
            is_hatched = category in hatched
            ax.barh(y, float(width), left=float(left), height=BAR_HEIGHT, color=palette[category], edgecolor="white",
                    linewidth=0.65, hatch="///" if is_hatched else None, zorder=2)
            segments.append({"actor": actor, "category": category, "left": float(left), "width": float(width), "y": y,
                             "label": segment["label"], "count": count})
            if count > 0:
                nonzero += 1
                text_kw = dict(ha="center", va="center", fontsize=LABEL_PT, zorder=4)
                if is_hatched:
                    text_kw.update(color="#222", bbox=dict(facecolor="white", edgecolor="none", pad=1))
                else:
                    text_kw["color"] = "white" if palette[category] in DARK_FACES else "#222"
                text = ax.text(float(left + width / 2), y, segment["label"], **text_kw)
                if _fits_inside(ax, text, width):
                    inside.append({"text": text, **segments[-1]})
                else:
                    text.remove()
                    small.append((segment["label"], palette[category], is_hatched, segments[-1]))
            left += width
        if small:
            fig.canvas.draw()
            inv = ax.transData.inverted()
            pt2dx = lambda pts: (inv.transform((pts * fig.dpi / 72, 0)) - inv.transform((0, 0)))[0]
            x_text_end = None
            for si, (label, face, is_hatched, record) in enumerate(small):
                x_data, offset_pts = (100.0, 3.0) if si == 0 else (x_text_end, 6.0)
                square = AnnotationBbox(key_square(face, is_hatched), (x_data, y), xybox=(offset_pts, 0),
                                        boxcoords="offset points", frameon=False, box_alignment=(0, 0.5),
                                        annotation_clip=False)
                square.set_zorder(5)
                ax.add_artist(square)
                x_text = x_data + pt2dx(offset_pts + SQ + 3.0)
                text = ax.text(x_text, y, label, ha="left", va="center", fontsize=LABEL_PT)
                fig.canvas.draw()
                bb = text.get_window_extent(renderer=fig.canvas.get_renderer())
                x_text_end = x_text + (inv.transform((bb.width, 0)) - inv.transform((0, 0)))[0]
                outside.append({"square": square, "text": text, "hatched": is_hatched, **record})
    ax.set_yticks(YPOS, ACTORS)
    ax.spines["bottom"].set_bounds(0, 100)
    ax.xaxis.set_major_locator(FixedLocator(list(X_TICKS)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x)}%" if x <= 100 else ""))
    if show_xlabels:
        ax.set_xlabel("Percentage of records")
    else:
        ax.tick_params(axis="x", labelbottom=False)
    _style_bar_axis(ax)
    return {"inside": inside, "outside": outside, "segments": segments, "nonzero_segments": nonzero,
            "labels_rendered": len(inside) + len(outside), "encodings_present": sorted(set(present))}


def draw_rating_panel(ax_title, ax_key, ax_bars, data: dict[str, list[dict]], palette: dict[str, str], hatched, title: str,
                      show_key: bool = True, show_xlabels: bool = False) -> dict:
    """Title row, one-row key, stacked bars with inside and outside percentage labels."""
    ax_title.set_xticks([]); ax_title.set_yticks([]); ax_title.axis("off")
    ax_title.text(0, 0.5, title, transform=ax_title.transAxes, ha="left", va="center", fontweight="bold", fontsize=TITLE_PT)
    result = draw_bars(ax_bars, data, palette, hatched, show_xlabels)
    if show_key and ax_key is not None:
        ax_key.set_xticks([]); ax_key.set_yticks([]); ax_key.axis("off")
        ax_key.legend(handles=key_handles(palette, hatched), loc="center left", bbox_to_anchor=(0, 0.5),
                      ncol=len(palette), frameon=False, handlelength=1.2, columnspacing=1.2)
    return result
