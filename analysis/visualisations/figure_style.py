"""Shared matplotlib style for paper figures (Arial throughout)."""

from __future__ import annotations

import matplotlib

FONT_FAMILY = "Arial"


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
