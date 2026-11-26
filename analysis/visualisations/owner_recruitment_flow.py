"""Supplementary Figure S1: project-owner recruitment flow (protocol 8.6).

Stage 1 (extract) reads the hash-pinned final owner export, the frozen owner
dictionary and the restricted recruitment tables, recomputes every count, checks
each against the owner analysis record (``owner_results_provisional.json``) and
writes one figure-data CSV plus a manifest.  Stage 2 (render) reads that CSV
only.  All outputs go to gitignored paths: figure data and the figure itself to
``preregistration_restricted/owner_responses/analysis/recruitment_flow/``, and a
copy of the figure to ``DEA_paper/figures/``.  Counts are aggregate; nothing is
broken down by owner or institution.

Owner-derived material: keep it away from the secondary adjudicator until their
Stage 1 is complete (adjudication methods 9.2).

Run from the repository root:  python -m analysis.visualisations.owner_recruitment_flow
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402  (sets the shared rcParams)
import render_scratch_coder_pass4 as p4  # noqa: E402

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

from figure_style import COLOURS  # noqa: E402

from analysis.validation import run_owner_analysis as roa  # noqa: E402

SLUG = "supplementary_figure_s1_owner_recruitment_flow"
DELIVERABLE = "Supplementary Figure S1"
RESTRICTED = REPO / "preregistration_restricted"
OUT = RESTRICTED / "owner_responses/analysis/recruitment_flow"
PAPER_FIGURES = REPO / "DEA_paper/figures"
RESULTS = RESTRICTED / "owner_responses/analysis/owner_results_provisional.json"
COMPLETENESS = RESTRICTED / "owner_responses/analysis/owner_completeness_check.csv"
FRAME_8A = REPO / "preregistration/post_registration/owner_candidate_frame_8a/owner_candidate_incidence_deidentified.csv"
ASSIGNMENTS_8B = REPO / "preregistration/post_registration/owner_candidate_frame_8b/owner_assignment_frame_8b.csv"
SEQUENCE_LOG = RESTRICTED / "owner_candidate_frame_8a/owner_sequence_log_8b.csv"
FINAL_EXPORT_CHECK = RESTRICTED / "owner_responses/exports/final_export_check_2026-11-12.md"
WAVES = ("initial_invitation", "checkpoint_1_day14", "checkpoint_2_day21", "checkpoint_3_day28")
PROTOCOL_MINIMUM, PROTOCOL_TARGET = 25, 50  # unique records with an analytically complete sequence-based review (protocol 5.4)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_of(path: Path, encoding: str = "utf-8-sig") -> list[dict]:
    with path.open(encoding=encoding, newline="") as handle:
        return list(csv.DictReader(handle))


# --------------------------------------------------------------------------- Stage 1
def extract() -> tuple[Path, dict]:
    data = roa.EXPORT.read_bytes()
    if hashlib.sha256(data).hexdigest() != roa.EXPORT_SHA256:
        raise SystemExit("the owner export does not match its pinned SHA-256")
    rows = list(csv.DictReader(data.decode("utf-8-sig").splitlines(keepends=True)))
    dd = roa.dictionary()
    required = {f: compile(roa.to_py(m["branching"]) if m["branching"] else "True", f, "eval")
                for f, m in dd.items() if m["required"] and m["form"] == "project_review"}
    owners = {r["owner_id"]: r for r in rows if not r["redcap_repeat_instrument"]}
    consented = {o for o, r in owners.items() if r.get("owner_consent_complete") == "2" and r.get("owner_consent") == "1"}
    reviews = [r for r in rows if r["redcap_repeat_instrument"] == "project_review"]
    po_cols = [c for c in rows[0] if c.startswith("po_")]

    # Assignment states, exactly as run_owner_analysis derives them
    state_of = {}
    for r in reviews:
        touched = any((r.get(c) or "").strip() not in ("", "0") for c in po_cols)
        submitted = r["project_review_complete"] == "2"
        v = lambda name, r=r: r.get(name, "")
        missing = [f for f, code in required.items() if eval(code, {"v": v}) and not roa.answered(r, f, dd[f]["type"])]
        analytic = submitted and r["owner_id"] in consented and not missing
        state_of[r["assignment_id"]] = ("analytically complete" if analytic else
                                        "submitted, not analytically complete" if submitted else "partial" if touched else "untouched")
    recorded_states = {c["assignment_id"]: c["state"] for c in rows_of(COMPLETENESS, "utf-8")}
    if recorded_states != state_of:
        raise RuntimeError("assignment states differ from owner_completeness_check.csv")

    dispatch = [d for d in rows_of(roa.DISPATCH, "utf-8") if d["owner_id"]]
    followup = rows_of(roa.FOLLOWUP)
    withdrawn = {f["owner_id"] for f in followup if "WITHDRAWN" in (f.get("consent status", "") + f.get("action", "")).upper()}
    invited = {d["owner_id"] for d in dispatch}
    complete = [r for r in reviews if state_of[r["assignment_id"]] == "analytically complete"]
    completing = {r["owner_id"] for r in complete}
    per_owner = Counter(r["owner_id"] for r in reviews)

    # Structural checks behind the nesting the figure draws
    frame_assignments = rows_of(ASSIGNMENTS_8B)
    sequence = rows_of(SEQUENCE_LOG)
    frame = rows_of(FRAME_8A)
    checks = {
        "export owners equal the invited owners": set(owners) == invited,
        "every invitation dispatched": all(d["dispatch_status"] == "SENT" for d in dispatch),
        "every export assignment is in the 8b sequence frame (no supplementary assignment)":
            {r["assignment_id"] for r in reviews} == {a["assignment_id"] for a in frame_assignments},
        "no withdrawn owner consented": not (withdrawn & consented),
        "every completing owner consented": completing <= consented,
        "sequence admitted equals invited": sum(s["outcome"] == "ADMITTED" for s in sequence) == len(invited),
        "every sequence removal was NOT_FOUND": all(s["disposition"] == "NOT_FOUND" for s in sequence if s["outcome"] != "ADMITTED"),
        "one analytically complete review per record": len(complete) == len({r["source_record_id"] for r in complete}),
    }
    if not all(checks.values()):
        raise RuntimeError(f"structural check failed: {[k for k, v in checks.items() if not v]}")

    states = Counter(state_of.values())
    q = {
        "candidate_researchers": len({r["candidate_key"] for r in frame}),
        "eligible_records": len({r["eligible_record_id"] for r in frame}),
        "candidates_searched": len(sequence),
        "candidates_no_route": sum(s["outcome"] != "ADMITTED" for s in sequence),
        "researchers_invited": len(invited),
        **{f"invited_{w}": sum(d["recruitment_wave"] == w for d in dispatch) for w in WAVES},
        "assignments_offered": len(reviews),
        "records_offered": len({a["eligible_record_id"] for a in frame_assignments}),
        "researchers_not_consented": len(invited - consented),
        "researchers_withdrew_before_consent": len(withdrawn),
        "researchers_no_consent_recorded": len(invited - consented - withdrawn),
        "researchers_consented": len(consented),
        "assignments_to_consented": sum(per_owner[o] for o in consented),
        "researchers_consented_no_complete_review": len(consented - completing),
        "assignments_to_consented_no_complete_review": sum(per_owner[o] for o in consented - completing),
        "researchers_completing": len(completing),
        "assignments_to_completing": sum(per_owner[o] for o in completing),
        "assignments_to_completing_untouched": sum(per_owner[o] for o in completing) - len(complete),
        "reviews_analytically_complete": len(complete),
        "unique_records_analytically_complete": len({r["source_record_id"] for r in complete}),
        "assignments_untouched": states["untouched"], "assignments_partial": states["partial"],
        "assignments_submitted_not_complete": states["submitted, not analytically complete"],
        "supplementary_route_assignments": 0, "protocol_minimum": PROTOCOL_MINIMUM, "protocol_target": PROTOCOL_TARGET,
    }
    q["candidates_not_searched"] = q["candidate_researchers"] - q["candidates_searched"]
    if q["invited_initial_invitation"] + sum(q[f"invited_{w}"] for w in WAVES[1:]) != q["researchers_invited"]:
        raise RuntimeError("wave counts do not sum to invited researchers")
    if sum(states.values()) != q["assignments_offered"]:
        raise RuntimeError("assignment states do not sum to assignments offered")

    # Reconcile with the owner analysis record
    flow = json.loads(RESULTS.read_text(encoding="utf-8"))["recruitment_flow"]
    record = {"owners invited": q["researchers_invited"], "owners consented": q["researchers_consented"],
              "owners recorded as withdrawn before submitting": q["researchers_withdrew_before_consent"],
              "owners with at least one analytically complete review": q["researchers_completing"],
              "reviews offered": q["assignments_offered"],
              "unique records with an analytically complete review": q["unique_records_analytically_complete"]}
    mismatches = {k: (v, flow[k]) for k, v in record.items() if flow[k] != v}
    if dict(Counter({k: v for k, v in states.items() if v})) != flow["review states"]:
        mismatches["review states"] = (dict(states), flow["review states"])
    if {w: q[f"invited_{w}"] for w in WAVES} != flow["invitation waves"]:
        mismatches["invitation waves"] = flow["invitation waves"]
    if mismatches:
        raise RuntimeError(f"counts differ from the owner analysis record: {mismatches}")

    OUT.mkdir(parents=True, exist_ok=True)
    data_csv = OUT / f"{SLUG}_data.csv"
    with data_csv.open("w", newline="", encoding="utf-8") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["quantity", "value"])
        w.writerows(sorted(q.items()))
    manifest = {
        "deliverable": DELIVERABLE, "slug": SLUG, "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "exploratory presentation of the protocol 8.6 recruitment flow; aggregate counts only",
        "figure_data": {data_csv.name: sha256(data_csv)},
        "inputs": {str(p.relative_to(REPO)).replace("\\", "/"): sha256(p) for p in
                   (roa.EXPORT, roa.DICTIONARY, roa.DISPATCH, roa.FOLLOWUP, FRAME_8A, ASSIGNMENTS_8B, SEQUENCE_LOG, RESULTS, COMPLETENESS)},
        "export_confirmed_final_by": str(FINAL_EXPORT_CHECK.relative_to(REPO)).replace("\\", "/"),
        "structural_checks": checks, "reconciled_with": str(RESULTS.relative_to(REPO)).replace("\\", "/"),
        "withdrawals_source_note": "withdrawals as recorded in PO_followup_log.csv; owner consent from the final REDCap export",
    }
    (OUT / f"{SLUG}_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return data_csv, manifest


# --------------------------------------------------------------------------- Stage 2
FONT_PT = 8.5
EDGE = "#3D3D3D"
ARROW = "#6B6B6B"
FINAL_EDGE = EDGE  # every box outlined alike (17 November 2026; was the baseline blue)
WIDTH = p3.FIGURE_WIDTH
MAIN_X0, MAIN_X1 = 0.04, 3.86
SIDE_X0, SIDE_X1 = 4.16, WIDTH - 0.04
LINE_IN = FONT_PT * 1.32 / 72
PAD_IN = 0.08
GAP_IN = 0.10


def n(value: int) -> str:
    return f"{value:,}"


def boxes_from(q: dict[str, int]) -> list[tuple[list[str], list[str] | None]]:
    """(main box lines, side box lines) from top to bottom; a side box sits on the connector below its main box."""
    plural = lambda k, one, many: one if q[k] == 1 else many
    waves = ", ".join(n(q[f"invited_{w}"]) for w in WAVES)
    return [
        ([f"{n(q['candidate_researchers'])} candidate researchers named on",
          f"{n(q['eligible_records'])} eligible register records"],
         [f"{n(q['candidates_not_searched'])} not searched: the sequence",
          f"closed at {n(q['researchers_invited'])} contactable researchers"]),
        ([f"{n(q['candidates_searched'])} candidates searched for a professional",
          "contact route, in greedy coverage order"],
         [f"{n(q['candidates_no_route'])} with no contact route found,",
          "removed from the sequence"]),
        ([f"{n(q['researchers_invited'])} researchers invited in four waves ({waves})",
          f"{n(q['assignments_offered'])} assignments covering {n(q['records_offered'])} records"],
         [f"{n(q['researchers_not_consented'])} did not consent: {n(q['researchers_withdrew_before_consent'])} withdrew,",
          f"{n(q['researchers_no_consent_recorded'])} with no consent recorded"]),
        ([f"{n(q['researchers_consented'])} researchers consented",
          f"{n(q['assignments_to_consented'])} assignments"],
         [f"{n(q['researchers_consented_no_complete_review'])} completed no review",
          f"{n(q['assignments_to_consented_no_complete_review'])} assignments untouched"]),
        ([f"{n(q['researchers_completing'])} researchers completed at least one review",
          f"{n(q['assignments_to_completing'])} assignments"],
         [f"{n(q['assignments_to_completing_untouched'])} {plural('assignments_to_completing_untouched', 'assignment', 'assignments')} untouched"]),
        ([f"{n(q['reviews_analytically_complete'])} analytically complete reviews of "
          f"{n(q['unique_records_analytically_complete'])} unique records",
          f"Protocol minimum {n(q['protocol_minimum'])}, target {n(q['protocol_target'])} unique records"],
         [f"All {n(q['assignments_offered'])} assignments:",
          f"{n(q['reviews_analytically_complete'])} analytically complete",
          f"{n(q['assignments_submitted_not_complete'])} submitted, not analytically complete",
          f"{n(q['assignments_partial'])} partially answered",
          f"{n(q['assignments_untouched'])} untouched"]),
    ]


def height(lines: list[str]) -> float:
    return len(lines) * LINE_IN + 2 * PAD_IN


def render(data_csv: Path, base: Path) -> dict:
    q = {r["quantity"]: int(r["value"]) for r in rows_of(data_csv, "utf-8")}
    layout = boxes_from(q)
    # Vertical extent: main boxes, with each intermediate side box between them on the connector
    y, placed = 0.0, []
    for i, (main, side) in enumerate(layout):
        top = y; y += height(main); placed.append(("main", main, top, y, i == len(layout) - 1))
        if i < len(layout) - 1:
            y += GAP_IN; side_top = y; y += height(side); placed.append(("side", side, side_top, y, False)); y += GAP_IN
    final_side = layout[-1][1]
    total = y + 0.02
    final_main = placed[-1]
    total = max(total, final_main[2] + height(final_side) + 0.02)

    fig = plt.figure(figsize=(WIDTH, total))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, WIDTH); ax.set_ylim(total, 0); ax.axis("off")
    boxes, texts = [], []

    def box(x0, x1, top, bottom, lines, edge=EDGE, lw=0.8, align="center"):
        ax.add_patch(Rectangle((x0, top), x1 - x0, bottom - top, facecolor="white", edgecolor=edge, linewidth=lw, zorder=2))
        x = (x0 + x1) / 2 if align == "center" else x0 + PAD_IN
        t = ax.text(x, (top + bottom) / 2, "\n".join(lines), ha=align, va="center", fontsize=FONT_PT, linespacing=1.32, color="0.1", zorder=3)
        boxes.append((x0, x1, top, bottom)); texts.append(t)

    centre = (MAIN_X0 + MAIN_X1) / 2
    mains = [p for p in placed if p[0] == "main"]
    for kind, lines, top, bottom, last in placed:
        if kind == "main":
            box(MAIN_X0, MAIN_X1, top, bottom, lines, edge=FINAL_EDGE if last else EDGE, lw=0.8)
        else:
            box(SIDE_X0, SIDE_X1, top, bottom, lines, align="left")
            ax.add_patch(FancyArrowPatch((centre, (top + bottom) / 2), (SIDE_X0, (top + bottom) / 2), arrowstyle="-|>",
                                         mutation_scale=7, color=ARROW, linewidth=0.8, shrinkA=0, shrinkB=0, zorder=1))
    for upper, lower in zip(mains, mains[1:]):
        ax.add_patch(FancyArrowPatch((centre, upper[3]), (centre, lower[2]), arrowstyle="-|>", mutation_scale=7,
                                     color=ARROW, linewidth=0.8, shrinkA=0, shrinkB=0, zorder=1))
    fm = final_main
    box(SIDE_X0, SIDE_X1, fm[2], fm[2] + height(final_side), final_side, align="left")

    # Text must sit inside its own box
    fig.canvas.draw(); renderer = fig.canvas.get_renderer(); inv = ax.transData.inverted()
    fit_failures = []
    for t, (x0, x1, top, bottom) in zip(texts, boxes):
        e = t.get_window_extent(renderer); (a, b), (c, d) = inv.transform((e.x0, e.y0)), inv.transform((e.x1, e.y1))
        if min(a, c) < x0 + 0.03 or max(a, c) > x1 - 0.03 or min(b, d) < top + 0.02 or max(b, d) > bottom - 0.02:
            fit_failures.append(t.get_text())
    metrics = p4.save_figure(fig, base, DELIVERABLE)
    metrics["text_fit_failures"] = fit_failures
    metrics["banned_text"] = p3.banned_check_text(metrics["rendered_text"], DELIVERABLE)
    metrics["hyphen_before_digit"] = [t for t in metrics["rendered_text"] if p4.HYPHEN_BEFORE_DIGIT.search(t)]
    return metrics


CAPTION = (
    "Supplementary Figure S1. Project-owner recruitment flow. Researchers named on eligible register records were searched for a "
    "published professional contact route in greedy marginal-coverage order until 25 were contactable; all 25 were invited, in four "
    "waves from 24 August 2026, each with a fixed set of review assignments. Every assignment came from this sequence; none was "
    "created through the supplementary purposive route, so that route has no column. A review is analytically complete when consent "
    "is recorded, the review is submitted and every required field shown is answered (protocol §5.4). Withdrawals are as recorded in "
    "the follow-up log; consent and review states are from the final export after the 26 October 2026 withdrawal deadline. Counts "
    "are aggregate and are not broken down by researcher or institution; recruitment was not random, so no intervals are given."
)


def main() -> None:
    data_csv, manifest = extract()
    base = OUT / SLUG
    metrics = render(data_csv, base)
    with tempfile.TemporaryDirectory() as tmp:  # Stage 2 isolation: a copy of the figure data alone gives the same SVG
        copy = Path(tmp) / data_csv.name; shutil.copy2(data_csv, copy)
        render(copy, Path(tmp) / SLUG)
        isolated = sha256(Path(tmp) / f"{SLUG}.svg") == sha256(base.with_suffix(".svg"))
    failures = {k: metrics[k] for k in ("text_fit_failures", "banned_text", "hyphen_before_digit", "text_overlaps") if metrics.get(k)}
    if metrics["font_status"] != "PASS": failures["font"] = metrics["minimum_effective_pt"]
    if metrics["edge_status"] != "PASS": failures["edges"] = metrics["edge_failures"]
    if not isolated: failures["isolation"] = "SVG from the copied figure data differs"
    if failures:
        raise RuntimeError(f"{DELIVERABLE} checks failed: {failures}")
    (OUT / f"{SLUG}_caption.md").write_text(CAPTION + "\n", encoding="utf-8")
    report = {"deliverable": DELIVERABLE, "rendered_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "figure_data_sha256": sha256(data_csv), "manifest_generated_utc": manifest["generated_utc"],
              "checks": {"H.1 minimum pt": metrics["minimum_effective_pt"], "H.2 edges": metrics["edge_status"], "text overlaps": "PASS",
                         "text inside boxes": "PASS", "banned wording": "PASS", "minus sign": "PASS", "stage 2 isolation": "PASS"},
              "outputs": {}, "software": {"python": sys.version, "matplotlib": matplotlib.__version__}}
    PAPER_FIGURES.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".svg"):
        shutil.copy2(base.with_suffix(suffix), PAPER_FIGURES / f"{SLUG}{suffix}")
        report["outputs"][f"{SLUG}{suffix}"] = sha256(base.with_suffix(suffix))
    (OUT / f"{SLUG}_rendering_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{DELIVERABLE} written to {OUT.relative_to(REPO)} and copied to {PAPER_FIGURES.relative_to(REPO)}; all checks passed")


if __name__ == "__main__":
    main()
