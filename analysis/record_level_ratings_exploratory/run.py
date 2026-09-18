"""Record-level ratings exploratory analysis: rating patterns, cross-tabulations, downgrade patterns and heatmaps."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from analysis.scratch_coder_stage_a.config import CODERS, ROOT
from analysis.scratch_coder_stage_a.load import verify_authorities
from analysis.scratch_coder_stage_a.panels import build_stage_a_data, StageAData
from analysis.scratch_coder_stage_a.sufficiency import SUFFICIENCY_LABELS, SPLIT, majority_category
from analysis.scratch_coder_stage_a.taxonomy import FIT_LABELS
from analysis.visualisations import figure_style

OUTPUT_DIR = ROOT / "analysis/record_level_ratings_exploratory"
FIGURE_DIR = OUTPUT_DIR / "figures"
RESTRICTED_DIR = ROOT / "preregistration_restricted/record_level_ratings_exploratory"
CANONICAL_DIR = ROOT / "analysis/outputs_validation_scratch_20260824"

QUESTIONS = {
    "register_entry_information": {
        "field": "sufficiency",
        "labels": SUFFICIENCY_LABELS,
        "ordered_codes": [1, 2, 3],
        "title": "Register-entry information",
    },
    "taxonomy_fit": {
        "field": "taxonomy_fit",
        "labels": FIT_LABELS,
        "ordered_codes": [1, 2, 3],
        "title": "Taxonomy fit",
    },
}

SUFFICIENCY_COLORS = {
    "Sufficient": "#246B45",
    "Partially sufficient": "#78AF82",
    "Insufficient": "#D6E8D8",
    "No majority": "#888888",
}
TAXONOMY_COLORS = {
    "Fit": "#5A4A86",
    "Partial Fit": "#9B8CC0",
    "No Fit": "#DED8EC",
    "Cannot assess from register entry": "#5F5F5F",
    "No majority": "#AEAEAE",
}
BLOCK_COLORS = {"unanimous": "#4a90d9", "two_agree": "#f0ad4e", "all_different": "#d9534f"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty output: {path.name}")
    columns = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def extract_record_ratings(data: StageAData, population: str, field: str, labels: dict[int, str]) -> dict[str, tuple[str, str, str]]:
    pop_map = {"baseline": data.baseline_ids, "hard_case": data.hard_case_ids}
    record_ids = pop_map[population]
    rows = data.responses[data.responses["record_id"].isin(record_ids)]
    output = {}
    for record_id, group in rows.groupby("record_id"):
        by_coder = {r["coder"]: r[field] for r in group.to_dict("records")}
        if set(by_coder) == set(CODERS) and all(by_coder[c] in labels for c in CODERS):
            output[record_id] = tuple(labels[int(by_coder[c])] for c in CODERS)
    return output


def classify_block(pattern: tuple[str, str, str]) -> str:
    unique = len(set(pattern))
    if unique == 1:
        return "unanimous"
    if unique == 2:
        return "two_agree"
    return "all_different"


def analysis_1_patterns(ratings: dict[str, tuple[str, str, str]], labels: dict[int, str], n_expected: int) -> tuple[list[dict], list[dict]]:
    pattern_counter = Counter(ratings.values())
    pattern_rows = []
    for pattern, count in sorted(pattern_counter.items(), key=lambda x: (-x[1], x[0])):
        maj = majority_category(
            tuple(code for code, lab in labels.items() if lab == cat for cat in [pattern[i]] for _ in [None])[0]
            if False else _majority_from_labels(pattern, labels),
            labels,
        )
        pattern_rows.append({
            "C01": pattern[0], "C02": pattern[1], "C03": pattern[2],
            "count": count, "percentage": round(100 * count / n_expected, 2),
            "majority_category": _majority_label(pattern, labels),
            "block": classify_block(pattern),
        })

    block_counter = Counter(classify_block(p) for p in ratings.values())
    block_rows = []
    for block in ["unanimous", "two_agree", "all_different"]:
        c = block_counter.get(block, 0)
        block_rows.append({"block": block, "count": c, "percentage": round(100 * c / n_expected, 2)})
    return pattern_rows, block_rows


def _majority_from_labels(pattern: tuple[str, str, str], labels: dict[int, str]) -> tuple[int, int, int]:
    reverse = {v: k for k, v in labels.items()}
    return tuple(reverse[p] for p in pattern)


def _majority_label(pattern: tuple[str, str, str], labels: dict[int, str]) -> str:
    codes = _majority_from_labels(pattern, labels)
    return majority_category(codes, labels)


def analysis_2_crosstab(
    ratings: dict[str, tuple[str, str, str]],
    labels: dict[int, str],
    ordered_codes: list[int],
) -> tuple[list[dict], list[dict], list[dict]]:
    all_labels = [labels[c] for c in sorted(labels.keys())]
    pairs = [("C01", "C02", 0, 1), ("C01", "C03", 0, 2), ("C02", "C03", 1, 2)]
    crosstab_rows = []
    direction_rows = []
    cannot_rows = []

    for coder_a, coder_b, idx_a, idx_b in pairs:
        counts = Counter()
        for pattern in ratings.values():
            counts[(pattern[idx_a], pattern[idx_b])] += 1
        for lab_a in all_labels:
            for lab_b in all_labels:
                crosstab_rows.append({
                    "coder_row": coder_a, "coder_col": coder_b,
                    "row_category": lab_a, "col_category": lab_b,
                    "count": counts.get((lab_a, lab_b), 0),
                })

        ordered_labels = [labels[c] for c in ordered_codes]
        higher = same = lower = 0
        for pattern in ratings.values():
            ra, rb = pattern[idx_a], pattern[idx_b]
            if ra in ordered_labels and rb in ordered_labels:
                code_a = next(c for c, l in labels.items() if l == ra)
                code_b = next(c for c, l in labels.items() if l == rb)
                if code_a < code_b:
                    higher += 1
                elif code_a == code_b:
                    same += 1
                else:
                    lower += 1
        direction_rows.append({
            "coder_row": coder_a, "coder_col": coder_b,
            "row_higher": higher, "same": same, "row_lower": lower,
            "note": f"Among records where both coders used an ordered category. Higher means {coder_a} rated higher (better) on the scale.",
        })

        cannot_label = labels.get(4)
        if cannot_label:
            both_neither = 0
            only_a = 0
            only_b = 0
            both_ca = 0
            for pattern in ratings.values():
                ra, rb = pattern[idx_a], pattern[idx_b]
                a_ca = ra == cannot_label
                b_ca = rb == cannot_label
                if a_ca and b_ca:
                    both_ca += 1
                elif a_ca:
                    only_a += 1
                elif b_ca:
                    only_b += 1
                else:
                    both_neither += 1
            cannot_rows.append({
                "coder_row": coder_a, "coder_col": coder_b,
                "only_row_coder": only_a, "only_col_coder": only_b,
                "both_cannot_assess": both_ca, "neither": both_neither,
            })

    return crosstab_rows, direction_rows, cannot_rows


def analysis_3_downgrade(
    ratings: dict[str, tuple[str, str, str]],
    labels: dict[int, str],
    ordered_codes: list[int],
) -> list[dict]:
    coder_indices = {"C01": 0, "C02": 1, "C03": 2}
    ordered_labels = {labels[c] for c in ordered_codes}
    rows = []

    for coder_x in CODERS:
        idx_x = coder_indices[coder_x]
        other_indices = [i for i in range(3) if i != idx_x]

        for record_id, pattern in ratings.items():
            other_vals = [pattern[i] for i in other_indices]
            if other_vals[0] != other_vals[1]:
                continue
            shared = other_vals[0]
            if shared not in ordered_labels:
                continue
            x_val = pattern[idx_x]
            if x_val not in ordered_labels:
                continue
            shared_code = next(c for c, l in labels.items() if l == shared)
            x_code = next(c for c, l in labels.items() if l == x_val)
            if x_code < shared_code:
                direction = "higher"
            elif x_code == shared_code:
                direction = "same"
            else:
                direction = "lower"
            rows.append({
                "coder": coder_x, "record_id": record_id,
                "shared_rating": shared, "coder_rating": x_val, "direction": direction,
            })

    summary_rows = []
    for coder_x in CODERS:
        coder_data = [r for r in rows if r["coder"] == coder_x]
        directions = Counter(r["direction"] for r in coder_data)
        total = len(coder_data)
        summary_rows.append({
            "coder": coder_x,
            "total_records_others_agree_ordered": total,
            "same": directions.get("same", 0),
            "higher": directions.get("higher", 0),
            "lower": directions.get("lower", 0),
        })
        by_shared = Counter()
        for r in coder_data:
            by_shared[(r["shared_rating"], r["direction"])] += 1
        ordered_label_list = [labels[c] for c in ordered_codes]
        for shared_label in ordered_label_list:
            for direction in ["same", "higher", "lower"]:
                count = by_shared.get((shared_label, direction), 0)
                summary_rows.append({
                    "coder": coder_x,
                    "total_records_others_agree_ordered": "",
                    "shared_rating": shared_label,
                    "direction": direction,
                    "count": count,
                })

    return summary_rows


def analysis_3_clean(
    ratings: dict[str, tuple[str, str, str]],
    labels: dict[int, str],
    ordered_codes: list[int],
) -> tuple[list[dict], list[dict]]:
    coder_indices = {"C01": 0, "C02": 1, "C03": 2}
    ordered_labels = {labels[c] for c in ordered_codes}
    ordered_label_list = [labels[c] for c in ordered_codes]

    overview_rows = []
    detail_rows = []

    for coder_x in CODERS:
        idx_x = coder_indices[coder_x]
        other_indices = [i for i in range(3) if i != idx_x]

        same = higher = lower = 0
        breakdown = Counter()

        for pattern in ratings.values():
            other_vals = [pattern[i] for i in other_indices]
            if other_vals[0] != other_vals[1]:
                continue
            shared = other_vals[0]
            if shared not in ordered_labels:
                continue
            x_val = pattern[idx_x]
            if x_val not in ordered_labels:
                continue
            shared_code = next(c for c, l in labels.items() if l == shared)
            x_code = next(c for c, l in labels.items() if l == x_val)
            if x_code < shared_code:
                higher += 1
                breakdown[(shared, "higher")] += 1
            elif x_code == shared_code:
                same += 1
                breakdown[(shared, "same")] += 1
            else:
                lower += 1
                breakdown[(shared, "lower")] += 1

        total = same + higher + lower
        overview_rows.append({
            "coder": coder_x,
            "records_others_agree_ordered": total,
            "same": same, "higher": higher, "lower": lower,
            "pct_same": round(100 * same / total, 1) if total else "",
            "pct_higher": round(100 * higher / total, 1) if total else "",
            "pct_lower": round(100 * lower / total, 1) if total else "",
        })

        for shared_label in ordered_label_list:
            for direction in ["same", "higher", "lower"]:
                count = breakdown.get((shared_label, direction), 0)
                detail_rows.append({
                    "coder": coder_x,
                    "shared_rating": shared_label,
                    "direction": direction,
                    "count": count,
                })

    return overview_rows, detail_rows


def _sort_key(record_id: str, pattern: tuple[str, str, str], labels: dict[int, str], ordered_codes: list[int]) -> tuple:
    block = classify_block(pattern)
    block_order = {"unanimous": 0, "two_agree": 1, "all_different": 2}
    codes = _majority_from_labels(pattern, labels)
    maj_label = majority_category(codes, labels)
    label_list = [labels[c] for c in sorted(labels.keys())]
    if maj_label in label_list:
        maj_order = label_list.index(maj_label)
    elif maj_label == SPLIT:
        maj_order = len(label_list)
    else:
        maj_order = len(label_list) + 1
    return (block_order[block], maj_order, pattern, record_id)


def render_heatmap(
    ratings: dict[str, tuple[str, str, str]],
    labels: dict[int, str],
    ordered_codes: list[int],
    colors: dict[str, str],
    population: str,
    question_title: str,
    show_record_ids: bool,
    output_path: Path,
    dpi: int = 300,
) -> list[dict]:
    sorted_records = sorted(
        ratings.items(),
        key=lambda item: _sort_key(item[0], item[1], labels, ordered_codes),
    )
    n = len(sorted_records)
    figure_style.apply()

    col_labels = ["C01", "C02", "C03", "Majority"]
    n_cols = len(col_labels)
    gap_frac = 0.3
    total_width_units = 3 + gap_frac + 1

    cell_h = max(0.08, min(0.15, 12 / n))
    fig_h = max(4, n * cell_h + 2.0)
    fig_w = 5.5 if not show_record_ids else 8.0

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, total_width_units)
    ax.set_ylim(0, n)
    ax.set_aspect("auto")
    ax.invert_yaxis()

    all_labels = [labels[c] for c in sorted(labels.keys())]
    maj_label_fn = lambda pat: majority_category(_majority_from_labels(pat, labels), labels)

    verify_data = []
    block_spans = {}
    prev_block = None
    block_start = 0
    cannot_label = labels.get(4)

    for row_idx, (record_id, pattern) in enumerate(sorted_records):
        block = classify_block(pattern)
        if block != prev_block and prev_block is not None:
            ax.axhline(y=row_idx, color="#333333", linewidth=0.8, zorder=3)
            block_spans[prev_block] = (block_start, row_idx)
            block_start = row_idx
        prev_block = block

        maj = maj_label_fn(pattern)
        values = list(pattern) + [maj]

        for col_idx, val in enumerate(values):
            if col_idx < 3:
                x = col_idx
            else:
                x = 3 + gap_frac

            color = colors.get(val, "#CCCCCC")
            if val == "No majority / split judgement":
                color = colors.get("No majority", "#888888")

            rect = plt.Rectangle((x, row_idx), 1, 1, facecolor=color, edgecolor="white", linewidth=0.3, zorder=2)
            ax.add_patch(rect)

            if cannot_label and val == cannot_label:
                for offset in np.arange(0, 2, 0.25):
                    ax.plot(
                        [x + offset - 0.5, x + offset + 0.5],
                        [row_idx - 0.5 + 1, row_idx + 0.5 + 1],
                        color="white", linewidth=0.3, zorder=2.5,
                        clip_on=True,
                    )

        verify_data.append({
            "record_id": record_id, "row": row_idx, "C01": pattern[0], "C02": pattern[1], "C03": pattern[2],
            "majority": maj, "block": block,
        })

    if prev_block is not None:
        block_spans[prev_block] = (block_start, n)

    block_labels_map = {"unanimous": "Unanimous", "two_agree": "Two agree", "all_different": "All different"}
    strip_x = -0.35
    strip_w = 0.25
    for block, (start, end) in block_spans.items():
        rect = plt.Rectangle(
            (strip_x, start), strip_w, end - start,
            facecolor=BLOCK_COLORS.get(block, "#999999"), edgecolor="none", zorder=2,
        )
        ax.add_patch(rect)
        mid = (start + end) / 2
        ax.text(strip_x - 0.05, mid, block_labels_map.get(block, block),
                ha="right", va="center", fontsize=6, rotation=90)

    for col_idx, label in enumerate(col_labels):
        x = col_idx if col_idx < 3 else 3 + gap_frac
        ax.text(x + 0.5, -0.3, label, ha="center", va="bottom", fontsize=7, fontweight="bold")

    if show_record_ids:
        for row_idx, (record_id, _) in enumerate(sorted_records):
            ax.text(total_width_units + 0.1, row_idx + 0.5, record_id, ha="left", va="center", fontsize=3.5)

    pop_label = f"Baseline (n={n})" if population == "baseline" else f"Hard-case (n={n}) — DIAGNOSTIC — non-representative"
    ax.set_title(f"{question_title}\n{pop_label}", fontsize=9, pad=10)
    ax.set_xlim(strip_x - 1.5, total_width_units + (3 if show_record_ids else 0.3))
    ax.axis("off")

    legend_handles = []
    for label_name in all_labels:
        c = colors.get(label_name, "#CCCCCC")
        legend_handles.append(mpatches.Patch(facecolor=c, edgecolor="grey", label=label_name))
    no_maj_color = colors.get("No majority", "#888888")
    legend_handles.append(mpatches.Patch(facecolor=no_maj_color, edgecolor="grey", label="No majority"))
    ax.legend(handles=legend_handles, loc="lower center", bbox_to_anchor=(0.5, -0.02),
              ncol=min(len(legend_handles), 4), fontsize=6, frameon=False)

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    if str(output_path).endswith(".png"):
        svg_path = output_path.with_suffix(".svg")
        fig.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)

    return verify_data


def reconcile_per_coder(data: StageAData, canonical_dir: Path) -> list[dict]:
    checks = []
    suff_resp = pd.read_csv(canonical_dir / "sufficiency_response_distribution.csv")
    tax_resp = pd.read_csv(canonical_dir / "taxonomy_fit_response_distribution.csv")
    suff_rec = pd.read_csv(canonical_dir / "sufficiency_record_distribution.csv")
    tax_rec = pd.read_csv(canonical_dir / "taxonomy_fit_record_distribution.csv")

    for population in ("baseline", "hard_case"):
        pop_ids = data.baseline_ids if population == "baseline" else data.hard_case_ids
        responses = data.responses[data.responses["record_id"].isin(pop_ids)]

        for coder in CODERS:
            coder_resp = responses[responses["coder"] == coder]
            for code, label in SUFFICIENCY_LABELS.items():
                computed = int((coder_resp["sufficiency"] == code).sum())
                canonical = int(suff_resp.loc[
                    (suff_resp["population"] == population) & (suff_resp["coder"] == coder) & (suff_resp["category"] == label), "count"
                ].iloc[0])
                checks.append({
                    "check": f"sufficiency_per_coder_{population}_{coder}_{label}",
                    "computed": computed, "canonical": canonical,
                    "status": "passed" if computed == canonical else "FAILED",
                })

            for code, label in FIT_LABELS.items():
                computed = int((coder_resp["taxonomy_fit"] == code).sum())
                canonical = int(tax_resp.loc[
                    (tax_resp["population"] == population) & (tax_resp["coder"] == coder) & (tax_resp["category"] == label), "count"
                ].iloc[0])
                checks.append({
                    "check": f"taxonomy_per_coder_{population}_{coder}_{label}",
                    "computed": computed, "canonical": canonical,
                    "status": "passed" if computed == canonical else "FAILED",
                })

        suff_ratings = extract_record_ratings(data, population, "sufficiency", SUFFICIENCY_LABELS)
        majorities_suff = Counter(
            majority_category(_majority_from_labels(p, SUFFICIENCY_LABELS), SUFFICIENCY_LABELS)
            for p in suff_ratings.values()
        )
        for label in [*SUFFICIENCY_LABELS.values(), SPLIT]:
            col_label = label
            computed = majorities_suff.get(label, 0)
            canonical = int(suff_rec.loc[
                (suff_rec["population"] == population) & (suff_rec["category"] == label), "count"
            ].iloc[0])
            checks.append({
                "check": f"sufficiency_majority_{population}_{label}",
                "computed": computed, "canonical": canonical,
                "status": "passed" if computed == canonical else "FAILED",
            })

        tax_ratings = extract_record_ratings(data, population, "taxonomy_fit", FIT_LABELS)
        majorities_tax = Counter(
            majority_category(_majority_from_labels(p, FIT_LABELS), FIT_LABELS)
            for p in tax_ratings.values()
        )
        for label in [*FIT_LABELS.values(), SPLIT]:
            computed = majorities_tax.get(label, 0)
            canonical = int(tax_rec.loc[
                (tax_rec["population"] == population) & (tax_rec["category"] == label), "count"
            ].iloc[0])
            checks.append({
                "check": f"taxonomy_majority_{population}_{label}",
                "computed": computed, "canonical": canonical,
                "status": "passed" if computed == canonical else "FAILED",
            })

    return checks


def verify_heatmap_data(
    verify_data: list[dict],
    ratings: dict[str, tuple[str, str, str]],
    labels: dict[int, str],
    ordered_codes: list[int],
    population: str,
) -> list[dict]:
    checks = []
    n_expected = 150 if population == "baseline" else 75

    rendered_ids = {d["record_id"] for d in verify_data}
    checks.append({
        "check": f"heatmap_{population}_record_count",
        "expected": n_expected, "observed": len(verify_data),
        "status": "passed" if len(verify_data) == n_expected else "FAILED",
    })
    checks.append({
        "check": f"heatmap_{population}_unique_records",
        "expected": n_expected, "observed": len(rendered_ids),
        "status": "passed" if len(rendered_ids) == n_expected else "FAILED",
    })

    for d in verify_data:
        rid = d["record_id"]
        pattern = ratings[rid]
        match = d["C01"] == pattern[0] and d["C02"] == pattern[1] and d["C03"] == pattern[2]
        if not match:
            checks.append({
                "check": f"heatmap_{population}_color_match_{rid}",
                "status": "FAILED", "expected": str(pattern), "observed": str((d["C01"], d["C02"], d["C03"])),
            })

    prev_key = None
    sort_ok = True
    for d in verify_data:
        pattern = ratings[d["record_id"]]
        key = _sort_key(d["record_id"], pattern, labels, ordered_codes)
        if prev_key is not None and key < prev_key:
            sort_ok = False
            break
        prev_key = key
    checks.append({
        "check": f"heatmap_{population}_sort_order",
        "status": "passed" if sort_ok else "FAILED",
    })
    return checks


def verify_no_record_ids_in_paper(figure_dir: Path, all_record_ids: set[str]) -> list[dict]:
    checks = []
    for path in figure_dir.iterdir():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        found = [rid for rid in all_record_ids if rid in text]
        checks.append({
            "check": f"no_record_ids_{path.name}",
            "ids_found": len(found),
            "status": "passed" if not found else "FAILED",
        })
    return checks


def verify_crosstab_margins(
    crosstab_rows: list[dict],
    ratings: dict[str, tuple[str, str, str]],
    labels: dict[int, str],
    population: str,
    question: str,
) -> list[dict]:
    checks = []
    coder_idx = {"C01": 0, "C02": 1, "C03": 2}
    all_labels = [labels[c] for c in sorted(labels.keys())]
    pairs = [("C01", "C02"), ("C01", "C03"), ("C02", "C03")]

    coder_counts = {}
    for coder in CODERS:
        idx = coder_idx[coder]
        coder_counts[coder] = Counter(pattern[idx] for pattern in ratings.values())

    for coder_a, coder_b in pairs:
        pair_rows = [r for r in crosstab_rows if r["coder_row"] == coder_a and r["coder_col"] == coder_b]
        for lab in all_labels:
            row_sum = sum(r["count"] for r in pair_rows if r["row_category"] == lab)
            expected = coder_counts[coder_a].get(lab, 0)
            checks.append({
                "check": f"crosstab_row_margin_{population}_{question}_{coder_a}_{coder_b}_{lab}",
                "row_sum": row_sum, "expected": expected,
                "status": "passed" if row_sum == expected else "FAILED",
            })
            col_sum = sum(r["count"] for r in pair_rows if r["col_category"] == lab)
            expected = coder_counts[coder_b].get(lab, 0)
            checks.append({
                "check": f"crosstab_col_margin_{population}_{question}_{coder_a}_{coder_b}_{lab}",
                "col_sum": col_sum, "expected": expected,
                "status": "passed" if col_sum == expected else "FAILED",
            })
    return checks


def run() -> None:
    timestamp = datetime.now(timezone.utc).isoformat()

    if FIGURE_DIR.exists() and any(FIGURE_DIR.iterdir()):
        raise RuntimeError("Output figures directory is not empty; remove existing outputs before rerunning")

    authorities = verify_authorities()
    data = build_stage_a_data()

    assert data.baseline_ids and len(data.baseline_ids) == 150
    assert data.hard_case_ids and len(data.hard_case_ids) == 75
    all_record_ids = data.baseline_ids | data.hard_case_ids

    reconciliation_checks = reconcile_per_coder(data, CANONICAL_DIR)
    failed = [c for c in reconciliation_checks if c["status"] == "FAILED"]
    if failed:
        print("RECONCILIATION FAILED:")
        for f in failed:
            print(f"  {f}")
        raise RuntimeError(f"Reconciliation failed: {len(failed)} checks")

    all_checks = list(reconciliation_checks)
    all_pattern_rows = []
    all_block_rows = []
    all_crosstab_rows = []
    all_direction_rows = []
    all_cannot_rows = []
    all_downgrade_overview = []
    all_downgrade_detail = []
    all_verify_heatmap = []
    record_level_rows = []

    for population in ("baseline", "hard_case"):
        n_expected = 150 if population == "baseline" else 75
        pop_label = "Baseline" if population == "baseline" else "Hard-case — DIAGNOSTIC — non-representative"

        for q_key, q_info in QUESTIONS.items():
            ratings = extract_record_ratings(data, population, q_info["field"], q_info["labels"])
            assert len(ratings) == n_expected, f"Expected {n_expected} ratings for {population}/{q_key}, got {len(ratings)}"

            pattern_rows, block_rows = analysis_1_patterns(ratings, q_info["labels"], n_expected)
            for r in pattern_rows:
                r["population"] = population
                r["question"] = q_info["title"]
            for r in block_rows:
                r["population"] = population
                r["question"] = q_info["title"]
            all_pattern_rows.extend(pattern_rows)
            all_block_rows.extend(block_rows)

            total_patterns = sum(r["count"] for r in pattern_rows)
            all_checks.append({
                "check": f"pattern_count_sum_{population}_{q_key}",
                "expected": n_expected, "observed": total_patterns,
                "status": "passed" if total_patterns == n_expected else "FAILED",
            })
            total_blocks = sum(r["count"] for r in block_rows)
            all_checks.append({
                "check": f"block_count_sum_{population}_{q_key}",
                "expected": n_expected, "observed": total_blocks,
                "status": "passed" if total_blocks == n_expected else "FAILED",
            })

            crosstab_rows, direction_rows, cannot_rows = analysis_2_crosstab(
                ratings, q_info["labels"], q_info["ordered_codes"],
            )
            for r in crosstab_rows:
                r["population"] = population
                r["question"] = q_info["title"]
            for r in direction_rows:
                r["population"] = population
                r["question"] = q_info["title"]
            for r in cannot_rows:
                r["population"] = population
                r["question"] = q_info["title"]
            all_crosstab_rows.extend(crosstab_rows)
            all_direction_rows.extend(direction_rows)
            all_cannot_rows.extend(cannot_rows)

            margin_checks = verify_crosstab_margins(crosstab_rows, ratings, q_info["labels"], population, q_key)
            all_checks.extend(margin_checks)

            overview, detail = analysis_3_clean(ratings, q_info["labels"], q_info["ordered_codes"])
            for r in overview:
                r["population"] = population
                r["question"] = q_info["title"]
            for r in detail:
                r["population"] = population
                r["question"] = q_info["title"]
            all_downgrade_overview.extend(overview)
            all_downgrade_detail.extend(detail)

            colors = SUFFICIENCY_COLORS if q_key == "register_entry_information" else TAXONOMY_COLORS

            paper_path = FIGURE_DIR / f"heatmap_{q_key}_{population}.png"
            verify_paper = render_heatmap(
                ratings, q_info["labels"], q_info["ordered_codes"], colors,
                population, q_info["title"], False, paper_path,
            )
            paper_checks = verify_heatmap_data(verify_paper, ratings, q_info["labels"], q_info["ordered_codes"], population)
            all_checks.extend(paper_checks)
            all_verify_heatmap.extend(verify_paper)

            internal_path = RESTRICTED_DIR / f"heatmap_{q_key}_{population}_internal.png"
            verify_internal = render_heatmap(
                ratings, q_info["labels"], q_info["ordered_codes"], colors,
                population, q_info["title"], True, internal_path,
            )

            for record_id, pattern in ratings.items():
                codes = _majority_from_labels(pattern, q_info["labels"])
                maj = majority_category(codes, q_info["labels"])
                sorted_records = sorted(
                    ratings.items(),
                    key=lambda item: _sort_key(item[0], item[1], q_info["labels"], q_info["ordered_codes"]),
                )
                sort_pos = next(i for i, (rid, _) in enumerate(sorted_records) if rid == record_id)
                record_level_rows.append({
                    "record_id": record_id, "population": population,
                    "question": q_info["title"],
                    "C01": pattern[0], "C02": pattern[1], "C03": pattern[2],
                    "majority": maj, "block": classify_block(pattern),
                    "sort_position": sort_pos,
                })

    for population in ("baseline", "hard_case"):
        suff_ratings = extract_record_ratings(data, population, "sufficiency", SUFFICIENCY_LABELS)
        tax_ratings = extract_record_ratings(data, population, "taxonomy_fit", FIT_LABELS)

        aligned_path = RESTRICTED_DIR / f"heatmap_aligned_{population}_internal.png"
        n = len(suff_ratings)
        suff_sorted = sorted(
            suff_ratings.items(),
            key=lambda item: _sort_key(item[0], item[1], SUFFICIENCY_LABELS, [1, 2, 3]),
        )
        record_order = [rid for rid, _ in suff_sorted]

        figure_style.apply()
        cell_h = max(0.08, min(0.15, 12 / n))
        fig_h = max(4, n * cell_h + 2.5)
        fig_w = 14
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fig_w, fig_h))

        for ax, ratings_dict, colors, title, labels, ordered_codes in [
            (ax1, suff_ratings, SUFFICIENCY_COLORS, "Register-entry information", SUFFICIENCY_LABELS, [1, 2, 3]),
            (ax2, tax_ratings, TAXONOMY_COLORS, "Taxonomy fit", FIT_LABELS, [1, 2, 3]),
        ]:
            all_labels = [labels[c] for c in sorted(labels.keys())]
            gap_frac = 0.3
            total_w = 3 + gap_frac + 1
            ax.set_xlim(-0.5, total_w + 3.5)
            ax.set_ylim(0, n)
            ax.set_aspect("auto")
            ax.invert_yaxis()

            cannot_label = labels.get(4)

            for row_idx, rid in enumerate(record_order):
                pattern = ratings_dict.get(rid, ("", "", ""))
                codes_tuple = _majority_from_labels(pattern, labels) if all(p for p in pattern) else (0, 0, 0)
                maj = majority_category(codes_tuple, labels) if all(p for p in pattern) else ""
                values = list(pattern) + [maj]

                for col_idx, val in enumerate(values):
                    x = col_idx if col_idx < 3 else 3 + gap_frac
                    color = colors.get(val, "#CCCCCC")
                    if val == SPLIT:
                        color = colors.get("No majority", "#888888")
                    rect = plt.Rectangle((x, row_idx), 1, 1, facecolor=color, edgecolor="white", linewidth=0.3)
                    ax.add_patch(rect)
                    if cannot_label and val == cannot_label:
                        for offset in np.arange(0, 2, 0.25):
                            ax.plot([x + offset - 0.5, x + offset + 0.5], [row_idx + 0.5, row_idx + 1.5],
                                    color="white", linewidth=0.3, clip_on=True)

                ax.text(total_w + 0.1, row_idx + 0.5, rid, ha="left", va="center", fontsize=3)

            for col_idx, label in enumerate(["C01", "C02", "C03", "Majority"]):
                x = col_idx if col_idx < 3 else 3 + gap_frac
                ax.text(x + 0.5, -0.3, label, ha="center", va="bottom", fontsize=7, fontweight="bold")

            pop_label = f"(n={n})" if population == "baseline" else f"(n={n}) DIAGNOSTIC"
            ax.set_title(f"{title} {pop_label}", fontsize=8)
            ax.axis("off")

        fig.suptitle(f"Aligned record-level ratings — {'Baseline' if population == 'baseline' else 'Hard-case'}", fontsize=10)
        fig.tight_layout()
        fig.savefig(aligned_path, dpi=300, bbox_inches="tight")
        svg_aligned = aligned_path.with_suffix(".svg")
        fig.savefig(svg_aligned, format="svg", bbox_inches="tight")
        plt.close(fig)

    no_id_checks = verify_no_record_ids_in_paper(FIGURE_DIR, set(all_record_ids))
    all_checks.extend(no_id_checks)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(OUTPUT_DIR / "pattern_counts.csv", all_pattern_rows)
    _write_csv(OUTPUT_DIR / "block_summary.csv", all_block_rows)
    _write_csv(OUTPUT_DIR / "pairwise_crosstab.csv", all_crosstab_rows)
    _write_csv(OUTPUT_DIR / "direction_summary.csv", all_direction_rows)
    if all_cannot_rows:
        _write_csv(OUTPUT_DIR / "cannot_assess_summary.csv", all_cannot_rows)
    _write_csv(OUTPUT_DIR / "downgrade_overview.csv", all_downgrade_overview)
    _write_csv(OUTPUT_DIR / "downgrade_detail.csv", all_downgrade_detail)

    _write_csv(RESTRICTED_DIR / "record_level_ratings.csv", record_level_rows)

    results_md = _build_results_md(
        all_pattern_rows, all_block_rows, all_crosstab_rows,
        all_direction_rows, all_cannot_rows,
        all_downgrade_overview, all_downgrade_detail,
    )
    (OUTPUT_DIR / "results_record_level_ratings.md").write_text(results_md, encoding="utf-8")

    restricted_files = {}
    for path in RESTRICTED_DIR.iterdir():
        if path.is_file():
            restricted_files[str(path.relative_to(ROOT))] = _sha256(path)

    committed_files = {}
    for path in OUTPUT_DIR.rglob("*"):
        if path.is_file() and path.name != "run_metadata.json":
            committed_files[str(path.relative_to(ROOT))] = _sha256(path)

    metadata = {
        "run_timestamp": timestamp,
        "analysis": "record_level_ratings_exploratory",
        "addendum_commit": "ee31f65",
        "data_paths": {
            a.role: {"artifact_id": a.manifest_id, "path": a.path, "sha256": a.expected_sha256}
            for a in authorities
        },
        "populations": {"baseline": 150, "hard_case": 75},
        "sort_rule": "block (unanimous, two_agree, all_different); within block, majority category in scale order (Cannot assess and No majority last); within that, exact pattern; within that, record ID",
        "colors": {"register_entry_information": SUFFICIENCY_COLORS, "taxonomy_fit": TAXONOMY_COLORS},
        "software": {
            "python": platform.python_version(),
            "matplotlib": matplotlib.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "reconciliation_checks": all_checks,
        "restricted_outputs": restricted_files,
        "committed_outputs": committed_files,
    }
    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )

    failed_final = [c for c in all_checks if c.get("status") == "FAILED"]
    if failed_final:
        print(f"WARNING: {len(failed_final)} checks FAILED")
        for f in failed_final:
            print(f"  {f}")
    else:
        print(f"All {len(all_checks)} checks passed.")
    print(f"Committed outputs: {OUTPUT_DIR}")
    print(f"Restricted outputs: {RESTRICTED_DIR}")


def _build_results_md(
    pattern_rows, block_rows, crosstab_rows,
    direction_rows, cannot_rows,
    downgrade_overview, downgrade_detail,
) -> str:
    lines = ["# Record-level ratings: register-entry information and taxonomy fit", ""]
    table_num = 1

    for population in ("baseline", "hard_case"):
        pop_label = "Random baseline" if population == "baseline" else "Hard-case sample — DIAGNOSTIC — non-representative"
        pop_n = 150 if population == "baseline" else 75

        for q_title in ("Register-entry information", "Taxonomy fit"):
            lines.append(f"## RLR1T{table_num:03d} — Rating pattern counts — {pop_label} — {q_title}")
            lines.append("")
            rows = [r for r in pattern_rows if r["population"] == population and r["question"] == q_title]
            lines.append("| C01 | C02 | C03 | Count | % | Majority | Block |")
            lines.append("|---|---|---|---:|---:|---|---|")
            for r in rows:
                lines.append(f"| {r['C01']} | {r['C02']} | {r['C03']} | {r['count']} | {r['percentage']} | {r['majority_category']} | {r['block']} |")
            lines.append("")
            table_num += 1

            lines.append(f"## RLR1T{table_num:03d} — Block summary — {pop_label} — {q_title}")
            lines.append("")
            brows = [r for r in block_rows if r["population"] == population and r["question"] == q_title]
            lines.append("| Block | Count | % |")
            lines.append("|---|---:|---:|")
            for r in brows:
                lines.append(f"| {r['block']} | {r['count']} | {r['percentage']} |")
            lines.append("")
            table_num += 1

    for population in ("baseline", "hard_case"):
        pop_label = "Random baseline" if population == "baseline" else "Hard-case sample — DIAGNOSTIC — non-representative"
        for q_title in ("Register-entry information", "Taxonomy fit"):
            for pair_rows in [("C01", "C02"), ("C01", "C03"), ("C02", "C03")]:
                ca, cb = pair_rows
                lines.append(f"## RLR1T{table_num:03d} — Pairwise cross-tabulation — {pop_label} — {q_title} — {ca} vs {cb}")
                lines.append("")
                ct = [r for r in crosstab_rows if r["population"] == population and r["question"] == q_title and r["coder_row"] == ca and r["coder_col"] == cb]
                row_cats = []
                seen = set()
                for r in ct:
                    if r["row_category"] not in seen:
                        row_cats.append(r["row_category"])
                        seen.add(r["row_category"])
                col_cats = []
                seen = set()
                for r in ct:
                    if r["col_category"] not in seen:
                        col_cats.append(r["col_category"])
                        seen.add(r["col_category"])

                header = f"| {ca} \\ {cb} | " + " | ".join(col_cats) + " |"
                sep = "|---|" + "|".join(["---:" for _ in col_cats]) + "|"
                lines.append(header)
                lines.append(sep)
                for rc in row_cats:
                    vals = []
                    for cc in col_cats:
                        v = next((r["count"] for r in ct if r["row_category"] == rc and r["col_category"] == cc), 0)
                        vals.append(str(v))
                    lines.append(f"| {rc} | " + " | ".join(vals) + " |")
                lines.append("")
                table_num += 1

            lines.append(f"## RLR1T{table_num:03d} — Direction summary — {pop_label} — {q_title}")
            lines.append("")
            dr = [r for r in direction_rows if r["population"] == population and r["question"] == q_title]
            lines.append("| Pair | Row higher | Same | Row lower |")
            lines.append("|---|---:|---:|---:|")
            for r in dr:
                lines.append(f"| {r['coder_row']}–{r['coder_col']} | {r['row_higher']} | {r['same']} | {r['row_lower']} |")
            lines.append("")
            table_num += 1

            if q_title == "Taxonomy fit" and cannot_rows:
                lines.append(f"## RLR1T{table_num:03d} — Cannot assess usage — {pop_label} — {q_title}")
                lines.append("")
                cr = [r for r in cannot_rows if r["population"] == population and r["question"] == q_title]
                if cr:
                    lines.append("| Pair | Only row coder | Only col coder | Both | Neither |")
                    lines.append("|---|---:|---:|---:|---:|")
                    for r in cr:
                        lines.append(f"| {r['coder_row']}–{r['coder_col']} | {r.get('only_row_coder', 0)} | {r.get('only_col_coder', 0)} | {r['both_cannot_assess']} | {r['neither']} |")
                lines.append("")
                table_num += 1

    for population in ("baseline", "hard_case"):
        pop_label = "Random baseline" if population == "baseline" else "Hard-case sample — DIAGNOSTIC — non-representative"
        for q_title in ("Register-entry information", "Taxonomy fit"):
            lines.append(f"## RLR1T{table_num:03d} — Downgrade pattern overview — {pop_label} — {q_title}")
            lines.append("")
            ov = [r for r in downgrade_overview if r["population"] == population and r["question"] == q_title]
            lines.append("| Coder | Records (others agree, ordered) | Same | Higher | Lower | % Same | % Higher | % Lower |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
            for r in ov:
                lines.append(f"| {r['coder']} | {r['records_others_agree_ordered']} | {r['same']} | {r['higher']} | {r['lower']} | {r['pct_same']} | {r['pct_higher']} | {r['pct_lower']} |")
            lines.append("")
            table_num += 1

            lines.append(f"## RLR1T{table_num:03d} — Downgrade pattern by shared rating — {pop_label} — {q_title}")
            lines.append("")
            det = [r for r in downgrade_detail if r["population"] == population and r["question"] == q_title]
            lines.append("| Coder | Shared rating | Same | Higher | Lower |")
            lines.append("|---|---|---:|---:|---:|")
            for coder in CODERS:
                coder_det = [r for r in det if r["coder"] == coder]
                shared_labels = []
                seen = set()
                for r in coder_det:
                    if r["shared_rating"] not in seen:
                        shared_labels.append(r["shared_rating"])
                        seen.add(r["shared_rating"])
                for sl in shared_labels:
                    s = next((r["count"] for r in coder_det if r["shared_rating"] == sl and r["direction"] == "same"), 0)
                    h = next((r["count"] for r in coder_det if r["shared_rating"] == sl and r["direction"] == "higher"), 0)
                    lo = next((r["count"] for r in coder_det if r["shared_rating"] == sl and r["direction"] == "lower"), 0)
                    lines.append(f"| {coder} | {sl} | {s} | {h} | {lo} |")
            lines.append("")
            table_num += 1

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run()
