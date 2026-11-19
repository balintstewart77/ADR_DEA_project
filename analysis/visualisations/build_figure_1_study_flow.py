"""Figure 1: study design and flow of records (pass-4 log P4.34).

Redraws the Methods flow diagram with the investigator's revisions of 16 November 2026: adjudication is its own
layer, fed by route 1 (Fable 5 differs from the coder majority) and route 2 (owner-flagged); route 3 (flagged during
coding or cleaning) contributed no records and is named in the caption only (P4.35). All boxes are outlined alike (P4.35).
The owner column carries its recruitment numbers and an owner-findings box. P4.92: the release-decision layer is
removed (the figure shows the flow of records; the release rule is in the Methods and Supplementary Table S19), and
the adjudication box gives the route-1 counts by sample, read from the route-1 component and the official sampling
draw (aggregate counts only), and the route-2 count and final N from the route-2 receipt (ADJ-106). The draft is not
shown to the secondary adjudicator until the secondary review is complete.

Register, exclusion and sample numbers are carried from the earlier diagram (protocol §5; manuscript §2.4). Owner
numbers are read from the Supplementary Figure S6 figure data (restricted, aggregate counts only) and checked.

Writes ``analysis/figures/figure_1_study_flow.{svg,png}``, a metadata file in ``analysis/figure_data/``, a Figure 1
section at the top of ``analysis/figures/draft_captions_pass4.md``, and copies of the images in ``DEA_paper/figures/``.

Run from the repository root:  python -m analysis.visualisations.build_figure_1_study_flow
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_scratch_coder_pass3 as p3  # noqa: E402  (sets the shared rcParams)

import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


SLUG = "figure_1_study_flow"
FIGURES = REPO / "analysis/figures"
FIGURE_DATA = REPO / "analysis/figure_data"
PAPER = REPO / "DEA_paper/figures"
CAPTIONS = FIGURES / "draft_captions_pass4.md"
OWNER_DATA = (REPO / "preregistration_restricted/owner_responses/analysis/recruitment_flow"
              / "supplementary_figure_s6_owner_recruitment_flow_data.csv")
ROUTE1 = REPO / "preregistration_restricted/adjudication_route1_component.csv"
DRAW = REPO / "preregistration_restricted/sampling/official_draw_20260724"
ROUTE2 = REPO / "preregistration_restricted/adjudication_formal/route2/route2_receipt.json"
TITLE = "Study design and flow of records"

# Carried from the earlier diagram (protocol §5; manuscript §2.4).
REGISTER, PROJECT_IDS, TRAINING, PILOT = 1308, 1304, 12, 10
BASELINE, BASELINE_RESERVE, HARD_POOL, HARD, HARD_RESERVE, STRATUM = 150, 100, 380, 75, 50, 25
CODERS = 3

BODY_PT, TITLE_PT, LAYER_PT = 8.5, 8.5, 9.0
LINE = "#333333"
SEPARATOR = "#DDDDDD"

W = p3.FIGURE_WIDTH
X0, X1, GAP = 1.15, W - 0.07, 0.12
COL_W = (X1 - X0 - 2 * GAP) / 3
COLS = [(X0 + i * (COL_W + GAP), X0 + i * (COL_W + GAP) + COL_W) for i in range(3)]
SPAN12 = (COLS[0][0], COLS[1][1])
SPAN123 = (COLS[0][0], COLS[2][1])


def owner_numbers() -> dict[str, int]:
    rows = {r["quantity"]: int(r["value"]) for r in csv.DictReader(OWNER_DATA.open(encoding="utf-8"))}
    waves = sum(1 for k in rows if k.startswith("invited_"))
    numbers = {"invited": rows["researchers_invited"], "waves": waves, "records_offered": rows["records_offered"],
               "consented": rows["researchers_consented"], "completing": rows["researchers_completing"],
               "records_complete": rows["unique_records_analytically_complete"],
               "minimum": rows["protocol_minimum"], "target": rows["protocol_target"]}
    invited_by_wave = sum(v for k, v in rows.items() if k.startswith("invited_"))
    if invited_by_wave != numbers["invited"]:
        raise SystemExit(f"Owner waves sum to {invited_by_wave}, not {numbers['invited']}")
    if not numbers["completing"] <= numbers["consented"] <= numbers["invited"]:
        raise SystemExit("Owner counts are not nested")
    if rows["reviews_analytically_complete"] != numbers["records_complete"]:
        raise SystemExit("Complete reviews and unique complete records differ")
    return numbers


def route1_numbers() -> dict[str, int]:
    """Route-1 eligibility by sample: aggregate counts from the route-1 component and the official draw."""
    family = {}
    for name, label in (("baseline_active.csv", "baseline"), ("hard_active.csv", "hard")):
        for row in csv.DictReader((DRAW / name).open(encoding="utf-8")):
            family[row["record_id"]] = label
    lines = [ln for ln in ROUTE1.open(encoding="utf-8") if not ln.startswith("#")]
    rows = list(csv.DictReader(lines))
    if len(rows) != BASELINE + HARD or any(r["source_record_id"] not in family for r in rows):
        raise SystemExit("Route-1 component does not match the coded samples")
    if any(r["qa_flagged"] != "0" for r in rows if r["route1_eligible"] == "1"):
        raise SystemExit("A QA-flagged record is marked route-1 eligible")
    eligible = [r for r in rows if r["route1_eligible"] == "1"]
    samples = [family[r["source_record_id"]] for r in eligible]
    numbers = {"baseline": samples.count("baseline"), "hard": samples.count("hard"), "total": len(eligible),
               "empty_reference": sum(1 for r in eligible if r["stratum"] == "3")}
    if (numbers["baseline"], numbers["hard"], numbers["total"], numbers["empty_reference"]) != (114, 72, 186, 22):
        raise SystemExit(f"Route-1 counts differ from the adjudication record (ADJ-038, ADJ-067): {numbers}")
    return numbers


def route2_numbers(route1_total: int, owner_reviewed: int) -> dict[str, int]:
    """Route-2 counts from the route-2 receipt (ADJ-106), with the final N."""
    receipt = json.loads(ROUTE2.read_text(encoding="utf-8"))
    numbers = {"qualifying": receipt["qualifying_records"], "overlap": receipt["overlap_with_route1"],
               "added": receipt["records"], "owner_reviewed": owner_reviewed}
    if numbers["added"] != numbers["qualifying"] - numbers["overlap"] or numbers["qualifying"] > owner_reviewed:
        raise SystemExit(f"Route-2 receipt is inconsistent: {numbers}")
    numbers["total"] = route1_total + numbers["added"]
    if (numbers["qualifying"], numbers["overlap"], numbers["added"], numbers["total"]) != (17, 4, 13, 199):
        raise SystemExit(f"Route-2 counts differ from the adjudication record (ADJ-106, ADJ-119): {numbers}")
    return numbers


WORDS = {2: "two", 3: "three", 4: "four", 5: "five"}


def boxes(owner: dict[str, int], route1: dict[str, int], route2: dict[str, int]) -> list[dict]:
    """Every box: x span, y top, height, title and body lines."""
    eligible = REGISTER - TRAINING - PILOT
    sampled = BASELINE + HARD
    return [
        {"id": "register", "x": SPAN12, "y": 0.15, "h": 0.50, "title": "Cleaned DEA register snapshot",
         "body": [f"{REGISTER:,} records ({PROJECT_IDS:,} official project IDs)"]},
        {"id": "frozen", "x": COLS[2], "y": 0.12, "h": 0.66, "title": "Frozen before sampling",
         "body": ["Fable 5 output, prompt,", "taxonomy, GPT-5.5 run"]},
        {"id": "excluded", "x": COLS[2], "y": 0.88, "h": 0.50, "title": f"Excluded: {TRAINING + PILOT}",
         "body": [f"{TRAINING} training, {PILOT} pilot"]},
        {"id": "eligible", "x": SPAN12, "y": 1.30, "h": 0.46, "title": "Eligible records", "body": [f"n = {eligible:,}"]},
        {"id": "baseline", "x": COLS[0], "y": 2.22, "h": 0.96, "title": "Random baseline",
         "body": ["Simple random sample", f"n = {BASELINE} analysed", f"n = {BASELINE_RESERVE} reserve, held back"]},
        {"id": "hardcase", "x": COLS[1], "y": 2.22, "h": 0.96, "title": "Hard-case sample",
         "body": [f"From {HARD_POOL} Fable 5 vs GPT-5.5", f"disagreements; {STRATUM}/{STRATUM}/{STRATUM} strata",
                  f"n = {HARD} analysed", f"n = {HARD_RESERVE} reserve, held back"]},
        {"id": "owners", "x": COLS[2], "y": 2.22, "h": 0.96, "title": "Project owners",
         "body": ["Greedy-coverage sequence", "of named researchers;",
                  f"{owner['invited']} invited in {WORDS.get(owner['waves'], owner['waves'])} waves,",
                  f"{owner['records_offered']} records offered"]},
        {"id": "coding", "x": SPAN12, "y": 3.52, "h": 1.10, "title": f"Blinded scratch coding of the same {sampled} records",
         "body": [f"{WORDS[CODERS].capitalize()} trained coders, title and datasets used only,",
                  "blind to model output, other coders and sample stratum;",
                  f"{CODERS * sampled} coder classifications, none excluded;",
                  "Fable 5 classifications taken from the frozen output"]},
        {"id": "ownerreview", "x": COLS[2], "y": 3.52, "h": 1.10, "title": "Owner review",
         "body": ["Owners judge Fable 5’s", "proposed labels;", f"{owner['consented']} consented, {owner['completing']} completed;",
                  f"{owner['records_complete']} records reviewed", f"(minimum {owner['minimum']}, target {owner['target']})"]},
        {"id": "primary", "x": COLS[0], "y": 4.94, "h": 1.30, "title": f"Primary: baseline, n = {BASELINE}",
         "body": ["Replacement-panel", "Krippendorff’s α (MASI)", "Sensitivity: register-", "sufficient subsets",
                  "Secondary: per-label κ,", "precision, recall, F1; tags"]},
        {"id": "diagnostic", "x": COLS[1], "y": 4.94, "h": 1.30, "title": "Diagnostic: hard cases",
         "body": [f"n = {HARD}", "Same metrics; not used", "for register-wide estimates"]},
        {"id": "ownerfindings", "x": COLS[2], "y": 4.94, "h": 1.30, "title": "Project-owner findings",
         "body": ["Descriptive and", "project-informed;", "reported separately,", "not treated as truth"]},
        {"id": "adjudication", "x": SPAN123, "y": 6.80, "h": 1.12, "title": f"Adjudication of {route2['total']} records",
         "body": ["Route 1: Fable 5 differs from the labelwise coder majority on any component;",
                  f"{route1['baseline']} of {BASELINE} baseline and {route1['hard']} of {HARD} hard-case records ({route1['total']})",
                  f"Route 2: flagged by an owner; {route2['qualifying']} of {route2['owner_reviewed']} reviewed records, {route2['added']} not in route 1",
                  "Stage 1 source-masked, then Stage 2 source-revealed diagnosis of each disagreement;",
                  "secondary review of a random core plus mandatory records"]},
    ]


LAYERS = [("Freeze and\nexclude", 0.0, 1.92), ("Sampling", 1.92, 3.36), ("Classification\nand review", 3.36, 4.78),
          ("Analysis", 4.78, 6.40), ("Adjudication", 6.40, 8.06)]
HEIGHT = LAYERS[-1][2]


def mid(span: tuple[float, float]) -> float:
    return (span[0] + span[1]) / 2


def arrow(ax, x: float, y0: float, y1: float) -> None:
    ax.annotate("", xy=(x, y1), xytext=(x, y0),
                arrowprops={"arrowstyle": "-|>", "color": LINE, "lw": 0.9, "shrinkA": 0, "shrinkB": 0, "mutation_scale": 8})


def line(ax, xs, ys) -> None:
    ax.plot(xs, ys, color=LINE, lw=0.9, solid_capstyle="butt")


def draw(owner: dict[str, int], route1: dict[str, int], route2: dict[str, int]) -> tuple[dict, list[dict]]:
    fig = plt.figure(figsize=(W, HEIGHT))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, W); ax.set_ylim(HEIGHT, 0); ax.axis("off")
    for label, top, bottom in LAYERS:
        ax.text(0.07, (top + bottom) / 2, label, ha="left", va="center", fontsize=LAYER_PT, fontweight="bold", color="0.15")
        if top > 0:
            line_artist = ax.plot([0.07, W - 0.07], [top, top], color=SEPARATOR, lw=0.7)
            line_artist[0].set_zorder(0)
    spec = {b["id"]: b for b in boxes(owner, route1, route2)}
    texts = []
    for b in spec.values():
        (x0, x1), y, h = b["x"], b["y"], b["h"]
        ax.add_patch(Rectangle((x0, y), x1 - x0, h, facecolor="white", edgecolor=LINE, lw=0.9, zorder=2))
        title = ax.text(mid(b["x"]), y + 0.08, b["title"], ha="center", va="top", fontsize=TITLE_PT, fontweight="bold", zorder=3)
        body = ax.text(mid(b["x"]), y + 0.08 + 0.19, "\n".join(b["body"]), ha="center", va="top", fontsize=BODY_PT,
                       linespacing=1.3, zorder=3)
        texts.append({"box": b, "artists": [title, body]})

    def bottom(i): return spec[i]["y"] + spec[i]["h"]
    # Freeze and exclude
    cx = mid(SPAN12)
    arrow(ax, cx, bottom("register"), spec["eligible"]["y"])
    branch_y = spec["excluded"]["y"] + spec["excluded"]["h"] / 2
    ax.annotate("", xy=(COLS[2][0], branch_y), xytext=(cx, branch_y),
                arrowprops={"arrowstyle": "-|>", "color": LINE, "lw": 0.9, "shrinkA": 0, "shrinkB": 0, "mutation_scale": 8})
    # Eligible to the three sampling streams
    bar_y = bottom("eligible") + 0.22
    line(ax, [cx, cx], [bottom("eligible"), bar_y])
    line(ax, [mid(COLS[0]), mid(COLS[2])], [bar_y, bar_y])
    for col in COLS:
        arrow(ax, mid(col), bar_y, spec["baseline"]["y"])
    # Sampling to classification
    arrow(ax, mid(COLS[0]), bottom("baseline"), spec["coding"]["y"])
    arrow(ax, mid(COLS[1]), bottom("hardcase"), spec["coding"]["y"])
    arrow(ax, mid(COLS[2]), bottom("owners"), spec["ownerreview"]["y"])
    # Classification to analysis
    arrow(ax, mid(COLS[0]), bottom("coding"), spec["primary"]["y"])
    arrow(ax, mid(COLS[1]), bottom("coding"), spec["diagnostic"]["y"])
    arrow(ax, mid(COLS[2]), bottom("ownerreview"), spec["ownerfindings"]["y"])
    # Analysis to adjudication, labelled by route
    for col, box_id, route in ((COLS[0], "primary", "Route 1"), (COLS[1], "diagnostic", "Route 1"), (COLS[2], "ownerfindings", "Route 2")):
        arrow(ax, mid(col), bottom(box_id), spec["adjudication"]["y"])
        texts.append({"box": None, "artists": [ax.text(mid(col) + 0.07, (bottom(box_id) + spec["adjudication"]["y"]) / 2, route,
                                                       ha="left", va="center", fontsize=BODY_PT, color="0.25")]})

    # Hard stop: every box's text sits inside its box, with 3 pt to spare
    fig.canvas.draw(); renderer = fig.canvas.get_renderer()
    failures = []
    for item in texts:
        b = item["box"]
        if b is None:
            continue
        (x0, x1), y, h = b["x"], b["y"], b["h"]
        corners = ax.transData.transform([(x0, y + h), (x1, y)])
        box_px = (corners[0][0], corners[0][1], corners[1][0], corners[1][1])
        pad = 3 * fig.dpi / 72
        for artist in item["artists"]:
            e = artist.get_window_extent(renderer)
            if e.x0 < box_px[0] + pad or e.x1 > box_px[2] - pad or e.y0 < box_px[1] + pad or e.y1 > box_px[3] - pad:
                failures.append({"box": b["id"], "text": artist.get_text()[:40]})
    if failures:
        raise SystemExit(f"Figure 1 text outside its box: {failures}")
    return p3.save_figure(fig, FIGURES / SLUG, "Figure 1", tight=False), list(spec.values())


def caption_bullets(owner: dict[str, int], route1: dict[str, int], route2: dict[str, int]) -> list[str]:
    return [
        f"Register snapshot, exclusions, the random baseline ({BASELINE} analysed, {BASELINE_RESERVE} held back) and the hard-case "
        f"sample ({HARD} analysed from {HARD_POOL} Fable 5 vs GPT-5.5 disagreements in three strata of {STRATUM}; {HARD_RESERVE} held "
        "back) are as fixed before sampling [protocol §5; manuscript §2.4].",
        f"Project owners: researchers named on eligible register records, searched for a published contact route in greedy "
        f"marginal-coverage order; {owner['invited']} were invited in {WORDS.get(owner['waves'], owner['waves'])} waves and offered "
        f"{owner['records_offered']} records; {owner['consented']} consented and {owner['completing']} completed at least one review; "
        f"{owner['records_complete']} records have an analytically complete review, against a protocol minimum of "
        f"{owner['minimum']} and target of {owner['target']}. Supplementary Figure S6 gives the full recruitment flow "
        "[S6 figure data].",
        "Adjudication takes records on which Fable 5 differed from the labelwise coder majority on any component (route 1: "
        f"{route1['baseline']} of {BASELINE} baseline and {route1['hard']} of {HARD} hard-case records, {route1['total']} in all, "
        f"{route1['empty_reference']} of them only because no coder majority formed on the differing component) and records an "
        f"owner flagged (route 2: {route2['qualifying']} of the {route2['owner_reviewed']} owner-reviewed records, {route2['overlap']} "
        f"of them already in route 1), {route2['total']} records in all. Records on which only the coders disagreed are not "
        "eligible. The third preregistered route, records flagged during coding or cleaning, contributed no records [protocol "
        "§9; ADJ-038, ADJ-063, ADJ-067, ADJ-106; route-1 component; route-2 receipt].",
        "The primary analysis is the random baseline; the hard-case sample is diagnostic and never pooled with it. "
        "Owner review is project-informed and reported separately, and is not treated as the correct answer.",
        "Any revision to model, prompt or taxonomy is retested on the held-back reserves.",
    ]


def update_captions(bullets: list[str]) -> None:
    text = CAPTIONS.read_text(encoding="utf-8")
    section = "\n".join(["## Figure 1", "", f"**Figure 1. {TITLE}.**", "", "Legend content checklist:", "",
                         *(f"- {b}" for b in bullets), "", ""])
    text = re.sub(r"## Figure 1\n.*?(?=\n## )\n", "", text, flags=re.S)
    marker = "## Figure 2\n"
    if text.count(marker) != 1:
        raise SystemExit("draft_captions_pass4.md: expected exactly one Figure 2 section")
    CAPTIONS.write_text(text.replace(marker, section + marker), encoding="utf-8")


def main() -> None:
    owner, route1 = owner_numbers(), route1_numbers()
    route2 = route2_numbers(route1["total"], owner["records_complete"])
    metrics, drawn = draw(owner, route1, route2)
    bullets = caption_bullets(owner, route1, route2)
    rendered = metrics["rendered_text"]
    banned = p3.banned_check_text(rendered + bullets + [TITLE], "Figure 1")
    ascii_minus = [t for t in rendered + bullets if re.search(r"(?<![A-Za-z0-9])-(?=\d)", t)]
    if banned or ascii_minus or metrics["font_status"] != "PASS" or metrics["edge_status"] != "PASS":
        raise SystemExit(f"Figure 1 checks failed: banned={banned} minus={ascii_minus} font={metrics['font_status']} "
                         f"edges={metrics['edge_failures']}")
    FIGURE_DATA.mkdir(parents=True, exist_ok=True)
    (FIGURE_DATA / f"{SLUG}_metadata.json").write_text(json.dumps({
        "deliverable": "Figure 1", "decision_log": "pass-4 P4.34 (16 November 2026)",
        "owner_input": {"path": str(OWNER_DATA.relative_to(REPO)).replace("\\", "/"),
                        "sha256": hashlib.sha256(OWNER_DATA.read_bytes()).hexdigest(), "values": owner},
        "route1_input": {"path": str(ROUTE1.relative_to(REPO)).replace("\\", "/"),
                         "sha256": hashlib.sha256(ROUTE1.read_bytes()).hexdigest(), "values": route1},
        "route2_input": {"path": str(ROUTE2.relative_to(REPO)).replace("\\", "/"),
                         "sha256": hashlib.sha256(ROUTE2.read_bytes()).hexdigest(), "values": route2},
        "carried_numbers": {"register": REGISTER, "project_ids": PROJECT_IDS, "excluded_training": TRAINING,
                            "excluded_pilot": PILOT, "baseline": BASELINE, "baseline_reserve": BASELINE_RESERVE,
                            "hard_case_pool": HARD_POOL, "hard_case": HARD, "hard_case_reserve": HARD_RESERVE,
                            "stratum": STRATUM, "coders": CODERS, "source": "earlier diagram; protocol §5; manuscript §2.4"},
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "matplotlib_version": matplotlib.__version__,
        "checks": {"font_status": metrics["font_status"], "minimum_effective_pt": metrics["minimum_effective_pt"],
                   "edge_status": metrics["edge_status"], "text_inside_boxes": "PASS", "banned_text": "PASS", "minus_sign": "PASS"},
        "boxes": [{"id": b["id"], "title": b["title"], "body": b["body"]} for b in drawn],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    update_captions(bullets)
    PAPER.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".svg"):
        shutil.copy2(FIGURES / f"{SLUG}{suffix}", PAPER / f"{SLUG}{suffix}")
    print(f"Figure 1 written to {FIGURES.relative_to(REPO)} and copied to {PAPER.relative_to(REPO)}; "
          f"minimum {metrics['minimum_effective_pt']:.2f} pt; checks passed")


if __name__ == "__main__":
    main()
