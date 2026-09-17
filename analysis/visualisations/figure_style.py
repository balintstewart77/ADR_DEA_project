"""Shared matplotlib style for paper figures (Arial throughout)."""

from __future__ import annotations

import matplotlib

FONT_FAMILY = "Arial"

# Population colours shared by Figures 1 and 3 and Supplementary Figure S1.
COLOURS = {"baseline": "#28658C", "strict": "#D98524", "hardcase": "#4d4d4d"}

# δ_min star markers: visual diameter relative to the circle diameter, edge widths in points,
# and a z-order for interval lines above the markers.
STAR_DIAMETER_RATIO = 1.25
STAR_FILLED_EDGE_PT = 0.6
STAR_HOLLOW_EDGE_PT = 1.0
STAR_HOLLOW_FACE = "white"
MARKER_ZORDER = 4
INTERVAL_ZORDER = 5


def apply() -> None:
    matplotlib.rcParams.update({
        "font.family": FONT_FAMILY,
        "font.sans-serif": [FONT_FAMILY],
        "mathtext.fontset": "custom",
        "mathtext.rm": FONT_FAMILY,
        "mathtext.it": f"{FONT_FAMILY}:italic",
        "mathtext.bf": f"{FONT_FAMILY}:bold",
        "mathtext.sf": FONT_FAMILY,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.unicode_minus": True,
    })
