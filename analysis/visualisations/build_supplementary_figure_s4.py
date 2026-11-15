"""Supplementary Figure S4: exploratory pairwise Krippendorff's α.

Exploratory and not preregistered (requested 2026-11-15). Presentation only:
every plotted number is read from the result tables of the 2026-09-17
pairwise-α run (``analysis/pairwise_alpha_exploratory/ADDENDUM_pairwise_alpha.md``);
nothing is recomputed from record-level data.

Content: pairwise Krippendorff's α (the three coder pairs, then Fable 5 with each
coder; Analyses 1-2 of that run) and the per-coder replacement comparison D
(Analysis 4) for Research Domains and Analytical Purposes, baseline sample
only: S4 explains Figure 1, which is baseline only, and the hard-case
diagnostic has its own figure (S1). The caption reports that the D and δ
orders also match in the hard-case sample and points to its tables. The tag
dimensions are left out (11-12 coder-majority-positive baseline records).
Letters follow Figure 1:
A = C01, B = C02, C = C03, L = Fable 5. D_X is descriptive, not a decomposition
of δ_X.

Hard stops before anything is written: (1) every value is the verbatim CSV
string and its 4-decimal display is in results_pairwise_alpha.md; (2) every
quantity is defined with a reported interval and at least 1,800 valid
resamples; (3) n is 150; (4) D recomputed from the plotted α equals the
exported D within 1e-12; (5) the D order equals the δ order in every panel
shown, and the all-cell count is recomputed for the caption; (6) the pass-3
text checks (8 pt minimum, nothing clipped, banned wording, minus signs), and
every plotted value and bound inside the axis range.

Inputs (read only):
  analysis/pairwise_alpha_exploratory/PWA1T*.csv and results_pairwise_alpha.md
  analysis/outputs_validation_scratch_20260824/replacement_delta_results.csv
    (δ point estimates, for the ordering check only)

Outputs (local, ignored by git like the other paper exports):
  <data-dir>/supplementary_figure_s4_pairwise_alpha.csv and _metadata.json
  <figure-dir>/supplementary_figure_s4_pairwise_alpha.svg and .png
  <figure-dir>/supplementary_figure_s4_rendering_report.json
  the Supplementary Figure S4 section of <figure-dir>/draft_captions_pass2.md

The pass-3 renderer rewrites draft_captions_pass2.md from its own manifest, so
run this stage after it:

    python analysis/visualisations/build_supplementary_figure_s4.py
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as pass3  # noqa: E402
from extract_scratch_coder_pass3 import FIELDNAMES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "analysis/pairwise_alpha_exploratory"
DELTA_EXPORT = ROOT / "analysis/outputs_validation_scratch_20260824/replacement_delta_results.csv"
DELIVERABLE = "Supplementary Figure S4"
SLUG = "supplementary_figure_s4_pairwise_alpha"
TITLE = (
    "Agreement between pairs of human coders and between Fable 5 and each coder, and the per-coder replacement "
    "comparison (exploratory)"
)

POPULATIONS = ("baseline",)
DIMENSIONS = ("Research Domains", "Analytical Purposes")
N_RECORDS = {"baseline": 150}
# (population, dimension) -> (Analysis 1, Analysis 2, Analysis 4) table ids.
TABLES = {
    ("baseline", "Research Domains"): ("PWA1T001", "PWA1T002", "PWA1T004"),
    ("baseline", "Analytical Purposes"): ("PWA1T005", "PWA1T006", "PWA1T008"),
}
# Hard-case tables for the same two dimensions: cited in the caption, not drawn.
HARD_CASE_TABLES = ("PWA1T017", "PWA1T018", "PWA1T020", "PWA1T021", "PWA1T022", "PWA1T024")
# Every cell of the run, for the 7-of-8 ordering count in the caption.
ALL_ANALYSIS_4 = {
    ("baseline", "Research Domains"): "PWA1T004", ("baseline", "Analytical Purposes"): "PWA1T008",
    ("baseline", "Demographic disparities / equity"): "PWA1T012", ("baseline", "COVID-19 & Pandemic"): "PWA1T016",
    ("hard_case", "Research Domains"): "PWA1T020", ("hard_case", "Analytical Purposes"): "PWA1T024",
    ("hard_case", "Demographic disparities / equity"): "PWA1T028", ("hard_case", "COVID-19 & Pandemic"): "PWA1T032",
}
PAIR_ORDER = ("alpha_AB", "alpha_AC", "alpha_BC", "alpha_LA", "alpha_LB", "alpha_LC")
D_ORDER = ("D_A", "D_B", "D_C")
PAIR_NAMES = {
    "alpha_AB": "C01 versus C02", "alpha_AC": "C01 versus C03", "alpha_BC": "C02 versus C03",
    "alpha_LA": "Fable 5 versus C01", "alpha_LB": "Fable 5 versus C02", "alpha_LC": "Fable 5 versus C03",
}
D_REPLACES = {"D_A": "C01", "D_B": "C02", "D_C": "C03"}
TICKS = {q: q.removeprefix("alpha_") for q in PAIR_ORDER}
D_TICKS = {"D_A": r"D$_{\mathrm{A}}$", "D_B": r"D$_{\mathrm{B}}$", "D_C": r"D$_{\mathrm{C}}$"}
D_CAPTION = {"D_A": "Dₐ", "D_B": "Dᵦ", "D_C": "D꜀"}
ALPHA_RANGE = (0.0, 0.8)
D_RANGE = (-0.45, 0.45)
FIGURE_HEIGHT = 5.0


class CheckFailed(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

def figure_row(source: dict, table_id: str, series: str, order: int) -> dict:
    quantity = source["quantity"]
    defined = source["estimate_status"] == "defined"
    reported = source["interval_status"] == "reported"
    pair = PAIR_NAMES.get(quantity) or f"Fable 5 replacing {D_REPLACES[quantity]}"
    row = {name: "" for name in FIELDNAMES}
    row.update({
        "deliverable_id": DELIVERABLE,
        "role": "plotted",
        "population": source["population"],
        "dimension": source["dimension"],
        "source_order": str(order),
        "series": series,
        "quantity": quantity,
        "pair": pair,
        "source_file": f"analysis/pairwise_alpha_exploratory/{table_id}.csv",
        "source_table_id": table_id,
        "source_section": source["analysis"],
        "source_row_key": f"{source['population']}; {source['dimension']}; {quantity}",
        "source_column_locator": "estimate; ci_lower; ci_upper; estimate_status; interval_status; bootstrap_valid/invalid/requested",
        "source_value_string": source["estimate"],
        "parsed_value": source["estimate"],
        "interval_lower_string": source["ci_lower"],
        "parsed_interval_lower": source["ci_lower"],
        "interval_upper_string": source["ci_upper"],
        "parsed_interval_upper": source["ci_upper"],
        "estimate_status": "R" if defined else "U",
        "interval_status": "R" if reported else "U",
        "original_status_string": (
            f"{source['estimate_status']}/{source['interval_status']}; {source['interval_method']}; "
            f"confidence {source['confidence_level']}; valid/invalid/requested draws "
            f"{source['bootstrap_valid']}/{source['bootstrap_invalid']}/{source['bootstrap_requested']}"
        ),
        "interval_method": "bootstrap_percentile",
        "confidence_level": "95%",
        "denominator_string": f"{source['n_records']} records",
        "sample_size": source["n_records"],
        "denominator_unit": "records",
        "presentation_note": "exploratory, not preregistered (ADDENDUM_pairwise_alpha.md)",
        "row_group": "coder pairs" if quantity in PAIR_ORDER[:3] else ("Fable 5 with each coder" if quantity in PAIR_ORDER else "replacement comparison"),
    })
    return row


def extract(source_dir: Path = SOURCE_DIR) -> list[dict]:
    rows: list[dict] = []
    for population in POPULATIONS:
        for dimension in DIMENSIONS:
            pair_tables = TABLES[(population, dimension)]
            sources = {}
            for table_id in pair_tables:
                for source in read_rows(source_dir / f"{table_id}.csv"):
                    if source["population"] != population or source["dimension"] != dimension:
                        raise CheckFailed(f"{table_id} holds {source['population']} / {source['dimension']}")
                    sources[source["quantity"]] = (table_id, source)
            for order, quantity in enumerate(PAIR_ORDER):
                table_id, source = sources[quantity]
                rows.append(figure_row(source, table_id, "pairwise_alpha", order))
            for order, quantity in enumerate(D_ORDER):
                table_id, source = sources[quantity]
                rows.append(figure_row(source, table_id, "replacement_comparison", order))
    return rows


# --------------------------------------------------------------------------
# Checks (hard stops 1-5; 6 runs after rendering)
# --------------------------------------------------------------------------

def four_dp(value: str) -> str:
    return f"{Decimal(value):.4f}"


def ascending_order(values: dict[str, float]) -> str:
    """'B < C < A' style order, with '=' for exact ties (as in the run)."""
    ordered = sorted(values.items(), key=lambda item: item[1])
    text = ordered[0][0]
    for (_, previous), (letter, value) in zip(ordered, ordered[1:]):
        text += (" = " if value == previous else " < ") + letter
    return text


def delta_orders(delta_csv: Path = DELTA_EXPORT) -> dict[tuple[str, str], str]:
    orders = {}
    grouped: dict[tuple[str, str], dict[str, float]] = {}
    for row in read_rows(delta_csv):
        if row["delta"] not in ("delta_A", "delta_B", "delta_C"):
            continue  # the export also carries δ_min, which is not a component
        grouped.setdefault((row["population"], row["dimension"]), {})[row["delta"].removeprefix("delta_")] = float(row["point_estimate"])
    for key, values in grouped.items():
        orders[key] = ascending_order(values)
    return orders


def d_orders(source_dir: Path = SOURCE_DIR) -> dict[tuple[str, str], str]:
    orders = {}
    for key, table_id in ALL_ANALYSIS_4.items():
        values = {r["quantity"].removeprefix("D_"): float(r["estimate"]) for r in read_rows(source_dir / f"{table_id}.csv") if r["quantity"].startswith("D_")}
        orders[key] = ascending_order(values)
    return orders


def run_checks(rows: list[dict], source_dir: Path = SOURCE_DIR, delta_csv: Path = DELTA_EXPORT) -> dict:
    report_text = (source_dir / "results_pairwise_alpha.md").read_text(encoding="utf-8")
    failures: list[str] = []

    # 1. Verbatim values, and their 4-dp display in the run's report.
    traced = 0
    for row in rows:
        source = next(r for r in read_rows(ROOT / row["source_file"]) if r["quantity"] == row["quantity"])
        for field, column in (("parsed_value", "estimate"), ("parsed_interval_lower", "ci_lower"), ("parsed_interval_upper", "ci_upper")):
            if row[field] != source[column]:
                failures.append(f"check 1: {row['source_row_key']} {field} {row[field]!r} != {source[column]!r}")
        section = report_text.split(f"## {row['source_table_id']} ", 1)[-1].split("\n## ", 1)[0]
        line = next((ln for ln in section.splitlines() if ln.startswith(f"| {source['definition']} |")), "")
        expected = [four_dp(source[c]) for c in ("estimate", "ci_lower", "ci_upper")]
        if not line or any(f"| {value} |" not in line for value in expected):
            failures.append(f"check 1: {row['source_row_key']} 4-dp display not found in results_pairwise_alpha.md")
        traced += 1

    # 2. Defined, interval reported, at least 1,800 valid resamples.
    for row in rows:
        valid = int(row["original_status_string"].split("draws ")[1].split("/")[0])
        if row["estimate_status"] != "R" or row["interval_status"] != "R" or valid < 1800:
            failures.append(f"check 2: {row['source_row_key']} not defined/reported with >=1800 valid draws")

    # 3. Record counts.
    for row in rows:
        if int(row["sample_size"]) != N_RECORDS[row["population"]]:
            failures.append(f"check 3: {row['source_row_key']} n={row['sample_size']}")

    # 4. D recomputed from the plotted pairwise α point estimates.
    recomputed = []
    for population in POPULATIONS:
        for dimension in DIMENSIONS:
            alpha = {r["quantity"].removeprefix("alpha_"): float(r["parsed_value"]) for r in rows
                     if r["population"] == population and r["dimension"] == dimension and r["series"] == "pairwise_alpha"}
            exported = {r["quantity"]: float(r["parsed_value"]) for r in rows
                        if r["population"] == population and r["dimension"] == dimension and r["series"] == "replacement_comparison"}

            def pair(x: str, y: str) -> float:
                return alpha["".join(sorted((x, y)))] if "L" not in (x, y) else alpha["L" + (y if x == "L" else x)]

            for x in "ABC":
                others = [c for c in "ABC" if c != x]
                h = (pair(x, others[0]) + pair(x, others[1])) / 2
                m = (pair("L", others[0]) + pair("L", others[1])) / 2
                value = m - h
                recomputed.append({"population": population, "dimension": dimension, "quantity": f"D_{x}", "recomputed": value, "exported": exported[f"D_{x}"]})
                if abs(value - exported[f"D_{x}"]) > 1e-12:
                    failures.append(f"check 4: {population} {dimension} D_{x} {value} != {exported[f'D_{x}']}")

    # 5. D ordering versus δ ordering.
    d_order, delta_order = d_orders(source_dir), delta_orders(delta_csv)
    cells = [{"population": p, "dimension": dim, "D_order": d_order[(p, dim)], "delta_order": delta_order[(p, dim)],
              "agree": d_order[(p, dim)] == delta_order[(p, dim)], "shown": p in POPULATIONS and dim in DIMENSIONS}
             for (p, dim) in ALL_ANALYSIS_4]
    for cell in cells:
        if cell["shown"] and not cell["agree"]:
            failures.append(f"check 5: shown cell {cell['population']} {cell['dimension']} D {cell['D_order']} vs δ {cell['delta_order']}")
    # Cross-check against the run's own ordering lines.
    run_lines = re.findall(r"Orderings agree: (yes|no)\.", report_text)
    if len(run_lines) != 8 or sum(line == "yes" for line in run_lines) != sum(cell["agree"] for cell in cells):
        failures.append(f"check 5: run reports {run_lines}, recomputed {[c['agree'] for c in cells]}")

    if failures:
        raise CheckFailed("; ".join(failures))
    return {
        "check_1_values_traced": {"status": "PASS", "rows": traced},
        "check_2_defined_and_reported": {"status": "PASS", "rows": len(rows)},
        "check_3_record_counts": {"status": "PASS", "n": N_RECORDS},
        "check_4_D_recomputed": {"status": "PASS", "tolerance": 1e-12, "values": recomputed},
        "check_5_orderings": {"status": "PASS", "cells": cells,
                              "agree_all_cells": sum(c["agree"] for c in cells), "cells_total": len(cells),
                              "exceptions": [c for c in cells if not c["agree"]]},
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render(rows: list[dict], base: Path, font_family: str) -> tuple[dict, dict]:
    matplotlib.rcParams.update({"font.family": font_family, "font.sans-serif": [font_family], "mathtext.rm": font_family})
    fig, axes = plt.subplots(len(DIMENSIONS), 2, figsize=(pass3.FIGURE_WIDTH, FIGURE_HEIGHT), constrained_layout=True,
                             gridspec_kw={"hspace": 0.08, "width_ratios": (1.35, 1.0)})
    positions = []
    outside = []
    for index, dimension in enumerate(DIMENSIONS):
        for column, (series, order) in enumerate((("pairwise_alpha", PAIR_ORDER), ("replacement_comparison", D_ORDER))):
            ax = axes[index][column]
            for population in POPULATIONS:
                keyed = {r["quantity"]: r for r in rows if r["dimension"] == dimension and r["population"] == population and r["series"] == series}
                style = pass3.POPULATION[population]
                limits = ALPHA_RANGE if series == "pairwise_alpha" else D_RANGE
                for y, quantity in enumerate(order):
                    row = keyed[quantity]
                    pass3.draw_interval(ax, y, row, style["color"], "o", style["hollow"])
                    positions.append({"dimension": dimension, "population": population, "series": series, "quantity": quantity, "y": y})
                    for field in ("parsed_value", "parsed_interval_lower", "parsed_interval_upper"):
                        if not limits[0] <= float(row[field]) <= limits[1]:
                            outside.append({"row": row["source_row_key"], "field": field, "value": row[field], "axis": limits})
            labels = [TICKS[q] for q in order] if series == "pairwise_alpha" else [D_TICKS[q] for q in order]
            ax.set_yticks(range(len(order)), labels)
            ax.tick_params(axis="y", labelsize=9.5)
            ax.set_ylim(len(order) - 0.5, -0.5)
            if series == "pairwise_alpha":
                ax.axhline(2.5, color="#B8B8B8", linewidth=0.7, linestyle=(0, (2.5, 2)), zorder=1)
                ax.set_xlim(ALPHA_RANGE)
                ax.xaxis.set_major_locator(FixedLocator([0, 0.2, 0.4, 0.6, 0.8]))
            else:
                ax.axvline(0, color="#333333", linewidth=0.8, zorder=1)
                ax.set_xlim(D_RANGE)
                ax.xaxis.set_major_locator(FixedLocator([-0.4, -0.2, 0, 0.2, 0.4]))
            ax.xaxis.set_major_formatter(FuncFormatter(pass3.minus_tick))
            pass3.style_axis(ax)
            if index == 0:
                ax.set_title("Pairwise Krippendorff’s α" if series == "pairwise_alpha" else "Replacement comparison D", pad=7)
            if column == 0:
                ax.set_ylabel(dimension.replace(" ", "\n", 1), fontweight="bold", rotation=0, ha="right", va="center",
                              labelpad=4, multialignment="right")
    if outside:
        plt.close(fig)
        raise CheckFailed(f"check 6: values outside the axis range: {outside}")
    metrics = pass3.save_figure(fig, base, DELIVERABLE)
    expected = {q: i for i, q in enumerate(PAIR_ORDER)} | {q: i for i, q in enumerate(D_ORDER)}
    misaligned = [p for p in positions if p["y"] != expected[p["quantity"]]]
    keys = {"status": "PASS" if not misaligned else "FAIL", "key_entries": [], "encodings_present": ["baseline filled"],
            "row_positions": positions, "misaligned": misaligned, "values_inside_axes": True}
    return metrics, keys


def text_checks(metrics: dict, captions: list[str]) -> dict:
    banned = pass3.banned_check_text(metrics["rendered_text"], DELIVERABLE) + pass3.banned_check_text(captions, f"{DELIVERABLE} caption")
    minus = [text for text in metrics["rendered_text"] if re.search(r"(?<!COVID)-(?=\d)", text)]
    failures = []
    if metrics["font_status"] != "PASS":
        failures.append(f"font: minimum {metrics['minimum_effective_pt']} pt")
    if metrics["edge_status"] != "PASS":
        failures.append(f"edges: {metrics['edge_failures']}")
    if banned:
        failures.append(f"banned text: {banned}")
    if minus:
        failures.append(f"hyphen-minus: {minus}")
    if failures:
        raise CheckFailed("check 6: " + "; ".join(failures))
    return {"status": "PASS", "minimum_effective_pt": metrics["minimum_effective_pt"], "edges": "PASS",
            "banned_text": "PASS", "minus_sign": "PASS"}


# --------------------------------------------------------------------------
# Caption
# --------------------------------------------------------------------------

def _values(rows: list[dict], population: str, dimension: str, quantities: tuple[str, ...]) -> list[dict]:
    return [r for r in rows if r["population"] == population and r["dimension"] == dimension and r["quantity"] in quantities]


def _span(rows: list[dict]) -> tuple[dict, dict]:
    ordered = sorted(rows, key=lambda r: Decimal(r["parsed_value"]))
    return ordered[0], ordered[-1]


def caption_bullets(rows: list[dict], checks: dict) -> list[str]:
    bullets = [
        "The figure is exploratory and not preregistered. The addendum documents this status [PWA1T001 onwards].",
        "Baseline n=150 records, as in Figure 1 [PWA1T001/PWA1T005 n_records cells].",
        "A, B and C are C01, C02 and C03 and L is Fable 5, as in Figure 1. AB, AC and BC are the coder–coder pairs and "
        "LA, LB and LC are Fable 5 with each coder; each point is a two-rater Krippendorff’s α with MASI distance "
        "[PWA1T001/PWA1T002/PWA1T005/PWA1T006 quantity cells].",
    ]
    for population, label in (("baseline", "Baseline"),):
        parts = []
        for dimension in DIMENSIONS:
            coder_lo, coder_hi = _span(_values(rows, population, dimension, PAIR_ORDER[:3]))
            model_lo, model_hi = _span(_values(rows, population, dimension, PAIR_ORDER[3:]))
            parts.append(
                f"{dimension}: coder–coder α {coder_lo['parsed_value']} to {coder_hi['parsed_value']}, Fable 5–coder α "
                f"{model_lo['parsed_value']} to {model_hi['parsed_value']} (display "
                f"{pass3.half_up(coder_lo['parsed_value'])}–{pass3.half_up(coder_hi['parsed_value'])} and "
                f"{pass3.half_up(model_lo['parsed_value'])}–{pass3.half_up(model_hi['parsed_value'])})"
            )
        tables = "/".join(t for (p, _), ids in TABLES.items() if p == population for t in ids[:2])
        bullets.append(f"{label} point estimates, {'; '.join(parts)} [{tables} estimate cells].")
    bullets.append(
        "Dₓ is the mean α of Fable 5 with the two coders other than X minus the mean α of coder X with those two coders, "
        "for X = A, B, C. It is a descriptive comparison and not a decomposition of δₓ, because panel α is not the mean of "
        "pairwise αs [PWA1T004/PWA1T008 cells]."
    )
    cells = checks["check_5_orderings"]["cells"]

    def where(cell: dict) -> str:
        return f"{'baseline' if cell['population'] == 'baseline' else 'hard-case'} {cell['dimension']}"

    shown = [c for c in cells if c["population"] == "baseline" and c["dimension"] in DIMENSIONS]
    hard = [c for c in cells if c["population"] == "hard_case" and c["dimension"] in DIMENSIONS]
    exceptions = checks["check_5_orderings"]["exceptions"]
    exception_text = (
        "; the exception is " + ", ".join(f"{where(c)} (D {c['D_order']}, δ {c['delta_order']})" for c in exceptions)
        if exceptions else ""
    )
    hard_text = (
        "The orders also match in the hard-case sample for both dimensions ("
        + "; ".join(f"{c['dimension']} {c['D_order']}" for c in hard) + ")"
        if all(c["agree"] for c in hard) else
        "In the hard-case sample the orders are " + "; ".join(
            f"{c['dimension']} D {c['D_order']}, δ {c['delta_order']}" for c in hard)
    )
    bullets.append(
        f"In both panels the ascending order of Dₐ, Dᵦ and D꜀ matches the order of the δ point estimates in Figure 1 ("
        + "; ".join(f"{c['dimension']} {c['D_order']}" for c in shown) + "). "
        f"{hard_text}. Across all {checks['check_5_orderings']['cells_total']} population and dimension cells of the run the "
        f"orders match in {checks['check_5_orderings']['agree_all_cells']}{exception_text} "
        "[results_pairwise_alpha.md ordering lines; replacement δ point-estimate cells]."
    )
    draws = sorted({r["original_status_string"].split("draws ")[1] for r in rows})
    bullets.append(
        "Intervals are 95% percentile-bootstrap intervals from one joint record-level bootstrap per population and "
        f"dimension (2,000 resamples, seed 20260917; valid/invalid/requested draws {', '.join(draws)} for every plotted "
        "quantity). Quantities in a panel share records and are not independent, and intervals are not compared by "
        "overlap [PWA1 interval and replicate cells]."
    )
    bullets.append(
        "The hard-case sample is not shown; its pairwise α and D values for these dimensions are in "
        f"{HARD_CASE_TABLES[0]}–{HARD_CASE_TABLES[-1]}, and Supplementary Figure S1 gives its panel α and δ. The two tag "
        "dimensions are not shown either; their values are in PWA1T009–PWA1T016 and PWA1T025–PWA1T032."
    )
    return bullets


def update_captions(path: Path, bullets: list[str]) -> None:
    section = "\n".join([
        f"## {DELIVERABLE}", "", f"**{DELIVERABLE}. {TITLE}.**", "", "Legend content checklist:", "",
        *[f"- {bullet}" for bullet in bullets], "", "",
    ])
    text = path.read_text(encoding="utf-8") if path.exists() else "# Draft captions — pass 3\n\n"
    text = re.sub(rf"## {re.escape(DELIVERABLE)}\n.*?(?=\n## |\Z)", "", text, flags=re.S).rstrip("\n") + "\n\n"
    marker = "## Supplementary Table S1a"
    if marker in text:
        text = text.replace(marker, section + marker, 1)
    else:
        text += section
    path.write_text(re.sub(r"\n{3,}", "\n\n", text), encoding="utf-8")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def write_data(rows: list[dict], data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{SLUG}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--delta-export", type=Path, default=DELTA_EXPORT)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "analysis/figure_data")
    parser.add_argument("--figure-dir", type=Path, default=ROOT / "analysis/figures")
    parser.add_argument("--font", default=pass3.FONT_FAMILY,
                        help="font family (default Arial, as the pass-3 figures; Liberation Sans has the same metrics)")
    args = parser.parse_args(argv)

    rows = extract(args.source_dir)
    checks = run_checks(rows, args.source_dir, args.delta_export)
    data_path = write_data(rows, args.data_dir)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    metrics, keys = render(rows, args.figure_dir / SLUG, args.font)
    bullets = caption_bullets(rows, checks)
    checks["check_6_text"] = text_checks(metrics, bullets)
    if keys["status"] != "PASS":
        raise CheckFailed(f"row alignment: {keys['misaligned']}")
    captions_path = args.figure_dir / "draft_captions_pass2.md"
    update_captions(captions_path, bullets)

    inputs = sorted({ROOT / r["source_file"] for r in rows} | {args.source_dir / "results_pairwise_alpha.md", args.delta_export})
    metadata = {
        "deliverable_id": DELIVERABLE, "title": TITLE, "slug": SLUG,
        "status": "exploratory, not preregistered",
        "addendum": "analysis/pairwise_alpha_exploratory/ADDENDUM_pairwise_alpha.md",
        "inputs": {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): sha256(p) for p in inputs},
        "rows": len(rows), "caption_bullets": bullets, "checks": checks,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_commit": git("rev-parse", "HEAD"), "code_dirty": bool(git("status", "--porcelain", "--", "analysis/visualisations")),
    }
    (args.data_dir / f"{SLUG}_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {
        "deliverable_id": DELIVERABLE, "renderer": Path(__file__).name,
        "font_family_requested": args.font, "font_resolved": font_manager.findfont(args.font),
        "matplotlib_version": matplotlib.__version__, "python_version": sys.version,
        "font_size": {k: metrics[k] for k in ("target_width_cm", "saved_width_inches", "minimum_effective_pt", "font_status")},
        "edges": {"status": metrics["edge_status"], "failures": metrics["edge_failures"]},
        "keys": keys, "text_checks": checks["check_6_text"], "rendered_text": metrics["rendered_text"],
        "outputs": [str((args.figure_dir / f"{SLUG}{suffix}")) for suffix in (".svg", ".png")] + [str(data_path), str(captions_path)],
    }
    (args.figure_dir / "supplementary_figure_s4_rendering_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[S4] {len(rows)} rows; checks 1-6 PASS; wrote {args.figure_dir / SLUG}.svg/.png, "
          f"{data_path.name} and the S4 caption section")


if __name__ == "__main__":
    main()
