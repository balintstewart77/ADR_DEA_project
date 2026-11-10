"""Exploratory: model disagreement and instability as proxies for register insufficiency.

Specification: SPEC_sufficiency_proxy_2026-11-10.md (committed in 6d304d1 before this code and
before any replicate label was read). Random baseline only; aggregate counts with 95% Wilson
intervals; no tests; no record-level output.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.config import CODERS  # noqa: E402
from analysis.scratch_coder_stage_a.load import read_manifest_csv, resolve_manifest_row, semicolon_set, verify_authorities  # noqa: E402
from analysis.scratch_coder_stage_a.panels import build_stage_a_data  # noqa: E402
from analysis.scratch_coder_stage_a.sufficiency import SUFFICIENCY_LABELS, _record_codes, majority_category  # noqa: E402
from analysis.validation.intervals import wilson_interval  # noqa: E402

HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_sufficiency_proxy_2026-11-10.md"
SPEC_COMMIT = "6d304d1"
FRAME = ROOT / "preregistration/package/03_preexisting_model_evidence/gpt55_disagreement_frame_380.csv"
EXCLUSIONS = ROOT / "preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv"
REPLICATE_DIR = ROOT / "analysis/fable_production_replicate_exploratory/run_20261110"
UNCLEAR = "Unclear from Register Entry"
DIMENSIONS = {"Research Domains": ("domains", "domain_only"), "Analytical Purposes": ("purposes", "purpose_only")}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def label_sets(path: Path) -> dict[str, dict[str, frozenset[str]]]:
    return {row["Record ID"]: {"domains": semicolon_set(row["substantive_domains"]), "purposes": semicolon_set(row["analytical_purpose"])}
            for row in read_rows(path)}


def proportion(k: int, n: int) -> dict:
    interval = wilson_interval(k, n)
    return {"n": n, "k": k, "proportion": k / n, "wilson_lower": interval.lower, "wilson_upper": interval.upper}


def reading(row: dict, rate: float) -> str:
    """The specification's reading rule: position of the flagged-record interval relative to the baseline rate."""
    if row["wilson_lower"] > rate:
        return "above the baseline rate"
    if row["wilson_upper"] < rate:
        return "below the baseline rate"
    return "overlaps the baseline rate"


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    checks: list[dict] = []

    def check(name: str, passed: bool, observed=None, expected=None) -> None:
        checks.append({"check": name, "status": "passed" if passed else "FAILED", "observed": observed, "expected": expected})
        if not passed:
            raise SystemExit(f"Check failed: {name}: observed {observed!r}, expected {expected!r}")

    for authority in verify_authorities():
        check(f"hash {authority.manifest_id}", authority.matched)
    data = build_stage_a_data()
    baseline = sorted(data.baseline_ids)
    check("150 baseline records", len(baseline) == 150, len(baseline), 150)

    # Signal X: frozen cross-model stratum from the baseline sampling file.
    strata = {row["record_id"]: (row["hard_case_stratum"] or "none") for _, row in read_manifest_csv("POST-009").iterrows()}
    check("strata as ECT001", Counter(strata[r] for r in baseline) == Counter({"none": 99, "domain_only": 20, "purpose_only": 20, "both": 11}),
          dict(Counter(strata[r] for r in baseline)))
    frame = {row["Record ID"] for row in read_rows(FRAME)}
    check("frame membership equals non-none stratum", all((strata[r] != "none") == (r in frame) for r in baseline))

    # Signal U: replicate against production (MOD-006); for the run-1 records production is run 1.
    replicate_metadata = json.loads((REPLICATE_DIR / "run_metadata.json").read_text(encoding="utf-8"))
    check("replicate complete and matched its reference requests",
          replicate_metadata["requests"] == 132 and replicate_metadata["all_input_tokens_match_reference"] and replicate_metadata["refused_fallbacks"] == 0)
    replicate_path = REPLICATE_DIR / "replicate_labels_canonical.csv"
    check("replicate labels unchanged since the run", sha256(replicate_path) == replicate_metadata["outputs"]["replicate_labels_canonical.csv"])
    production = label_sets(ROOT / resolve_manifest_row("MOD-006")["current_path"])
    replicate = label_sets(replicate_path)
    check("replicate covers every baseline record", set(baseline) <= set(replicate) and set(baseline) <= set(production))

    def unstable(record_id: str, field: str | None = None) -> bool:
        fields = (field,) if field else ("domains", "purposes")
        return any(production[record_id][f] != replicate[record_id][f] for f in fields)

    signals = {
        "X: cross-model disagreement": {r for r in baseline if strata[r] != "none"},
        "U: model instability": {r for r in baseline if unstable(r)},
    }
    signals["E: either signal"] = signals["X: cross-model disagreement"] | signals["U: model instability"]
    check("X flags 51 records", len(signals["X: cross-model disagreement"]) == 51, len(signals["X: cross-model disagreement"]), 51)

    # Outcomes from coder ratings.
    codes = _record_codes(data, "baseline")
    check("all baseline records have three sufficiency ratings", set(codes) == set(baseline))
    majority = {r: majority_category(codes[r], SUFFICIENCY_LABELS) for r in baseline}
    counts = Counter(majority.values())
    check("majority sufficiency equals S8T003", [counts["Sufficient"], counts["Partially sufficient"], counts["Insufficient"], 150 - sum(
        counts[k] for k in SUFFICIENCY_LABELS.values())] == [92, 55, 2, 1], dict(counts))
    not_sufficient = {r for r in baseline if majority[r] != "Sufficient"}
    sufficient_votes = {r: sum(code == 1 for code in codes[r]) for r in baseline}
    base_rate = len(not_sufficient) / len(baseline)

    responses = data.responses[data.responses["record_id"].isin(baseline)]
    coder_sets = {(row["record_id"], row["coder"]): row for row in responses.to_dict("records")}

    def unclear_only(record_id: str, field: str) -> bool:
        votes = Counter(label for coder in CODERS for label in coder_sets[(record_id, coder)][field])
        return {label for label, n in votes.items() if n >= 2} == {UNCLEAR}

    # SPX1T001: primary outcome.
    table1 = []
    for name, flagged in signals.items():
        unflagged = set(baseline) - flagged
        flagged_row = proportion(len(flagged & not_sufficient), len(flagged))
        table1.append({
            "table_id": "SPX1T001", "signal": name, "flagged_records": len(flagged),
            "flagged_not_sufficient": len(flagged & not_sufficient), "flagged_sufficient": len(flagged - not_sufficient),
            "unflagged_not_sufficient": len(unflagged & not_sufficient), "unflagged_sufficient": len(unflagged - not_sufficient),
            "not_sufficient_among_flagged": flagged_row["proportion"], "not_sufficient_among_flagged_lower": flagged_row["wilson_lower"],
            "not_sufficient_among_flagged_upper": flagged_row["wilson_upper"],
            **{f"not_sufficient_among_unflagged{suffix}": proportion(len(unflagged & not_sufficient), len(unflagged))[key]
               for suffix, key in (("", "proportion"), ("_lower", "wilson_lower"), ("_upper", "wilson_upper"))},
            **{f"flagged_among_not_sufficient{suffix}": proportion(len(flagged & not_sufficient), len(not_sufficient))[key]
               for suffix, key in (("", "proportion"), ("_lower", "wilson_lower"), ("_upper", "wilson_upper"))},
            "baseline_rate_not_sufficient": base_rate, "reading": reading(flagged_row, base_rate),
            "interval": "95% Wilson score", "status": "exploratory, not preregistered",
        })

    # SPX1T002: number of coders rating Sufficient, by flag status.
    table2 = []
    for name, flagged in signals.items():
        for status, group in (("flagged", flagged), ("not flagged", set(baseline) - flagged)):
            votes = Counter(sufficient_votes[r] for r in group)
            table2.append({"table_id": "SPX1T002", "signal": name, "flag_status": status, "records": len(group),
                           **{f"sufficient_ratings_{k}": votes.get(k, 0) for k in range(4)}})

    # SPX1T003: dimension-matched signals against majority Unclear-only.
    table3 = []
    for dimension, (field, only_stratum) in DIMENSIONS.items():
        s3 = {r for r in baseline if unclear_only(r, field)}
        dimension_signals = {f"X: cross-model disagreement ({dimension})": {r for r in baseline if strata[r] in (only_stratum, "both")},
                             f"U: model instability ({dimension})": {r for r in baseline if unstable(r, field)}}
        for name, flagged in dimension_signals.items():
            unflagged = set(baseline) - flagged
            row = {"table_id": "SPX1T003", "dimension": dimension, "signal": name, "flagged_records": len(flagged)}
            for status, group in (("flagged", flagged), ("unflagged", unflagged)):
                values = proportion(len(group & s3), len(group))
                row.update({f"{status}_unclear_only_n": values["k"], f"{status}_unclear_only": values["proportion"],
                            f"{status}_lower": values["wilson_lower"], f"{status}_upper": values["wilson_upper"]})
            table3.append(row)
        x_row = next(r for r in table3 if r["dimension"] == dimension and r["signal"].startswith("X"))
        expected = {"Research Domains": (6, 31, 7, 119), "Analytical Purposes": (8, 31, 18, 119)}[dimension]
        observed = (x_row["flagged_unclear_only_n"], x_row["flagged_records"], x_row["unflagged_unclear_only_n"], 150 - x_row["flagged_records"])
        check(f"{dimension}: Unclear-only counts by X equal the enrichment calibration", observed == expected, observed, expected)

    # SPX1T004: register-level flag rates over the records eligible for validation sampling.
    excluded = {row["record_id"] for row in read_rows(EXCLUSIONS)}
    eligible = set(production) - excluded
    check("1,286 eligible register records", len(eligible) == 1286 and len(excluded) == 22, len(eligible), 1286)
    check("frame lies within the eligible records", frame <= eligible, len(frame - eligible), 0)
    register_u = {r for r in eligible if unstable(r)}
    table4 = [{"table_id": "SPX1T004", "signal": name, "eligible_records": len(eligible), "flagged_records": len(flagged),
               "flagged_proportion": len(flagged) / len(eligible)}
              for name, flagged in (("X: cross-model disagreement", frame), ("U: model instability", register_u), ("E: either signal", frame | register_u))]

    for name, rows in (("SPX1T001.csv", table1), ("SPX1T002.csv", table2), ("SPX1T003.csv", table3), ("SPX1T004.csv", table4)):
        write_csv(HERE / name, rows)

    def pct(value: float) -> str:
        return f"{value * 100:.0f}%"

    lines = ["# Model signals as proxies for register insufficiency (exploratory, descriptive)", "",
             f"Not preregistered. Specification `SPEC_sufficiency_proxy_2026-11-10.md`, committed in {SPEC_COMMIT} before this code. "
             "Random baseline (n = 150). Not Sufficient = coder majority Partially sufficient, Insufficient or no majority. "
             "Intervals are 95% Wilson; no tests.", "",
             f"Baseline rate not Sufficient: {len(not_sufficient)}/150 ({pct(base_rate)}).", "",
             "## SPX1T001 — Signals against the coder majority sufficiency rating", "",
             "| Signal | Flagged | Not Sufficient among flagged | Not Sufficient among unflagged | Not-Sufficient records flagged | Reading |",
             "|---|---|---|---|---|---|"]
    for row in table1:
        lines.append(f"| {row['signal']} | {row['flagged_records']} | {row['flagged_not_sufficient']}/{row['flagged_records']} "
                     f"({pct(row['not_sufficient_among_flagged'])} [{pct(row['not_sufficient_among_flagged_lower'])}, {pct(row['not_sufficient_among_flagged_upper'])}]) | "
                     f"{row['unflagged_not_sufficient']}/{150 - row['flagged_records']} ({pct(row['not_sufficient_among_unflagged'])} "
                     f"[{pct(row['not_sufficient_among_unflagged_lower'])}, {pct(row['not_sufficient_among_unflagged_upper'])}]) | "
                     f"{row['flagged_not_sufficient']}/{len(not_sufficient)} ({pct(row['flagged_among_not_sufficient'])}) | {row['reading']} |")
    lines += ["", "## SPX1T002 — Number of coders rating Sufficient (0/1/2/3)", "", "| Signal | Flag status | Records | 0 | 1 | 2 | 3 |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['signal']} | {r['flag_status']} | {r['records']} | " + " | ".join(str(r[f'sufficient_ratings_{k}']) for k in range(4)) + " |" for r in table2]
    lines += ["", "## SPX1T003 — Dimension-matched signals against majority Unclear-only", "",
              "| Signal | Flagged | Unclear-only among flagged | Unclear-only among unflagged |", "|---|---|---|---|"]
    for r in table3:
        lines.append(f"| {r['signal']} | {r['flagged_records']} | {r['flagged_unclear_only_n']}/{r['flagged_records']} ({pct(r['flagged_unclear_only'])} "
                     f"[{pct(r['flagged_lower'])}, {pct(r['flagged_upper'])}]) | {r['unflagged_unclear_only_n']}/{150 - r['flagged_records']} "
                     f"({pct(r['unflagged_unclear_only'])} [{pct(r['unflagged_lower'])}, {pct(r['unflagged_upper'])}]) |")
    lines += ["", "## SPX1T004 — Share of the register each signal would flag", "", "| Signal | Flagged of 1,286 eligible records |", "|---|---|"]
    lines += [f"| {r['signal']} | {r['flagged_records']} ({pct(r['flagged_proportion'])}) |" for r in table4]
    (HERE / "results_sufficiency_proxy.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    metadata = {"status": "exploratory, not preregistered, descriptive", "specification": {"path": SPEC.name, "sha256": sha256(SPEC), "commit": SPEC_COMMIT},
                "completed_utc": datetime.now(timezone.utc).isoformat(),
                "inputs": {"frame": sha256(FRAME), "exclusions": sha256(EXCLUSIONS), "replicate_labels": sha256(replicate_path),
                           "replicate_run_metadata": sha256(REPLICATE_DIR / "run_metadata.json")},
                "checks": checks, "restricted_outputs": [],
                "outputs": {name: sha256(HERE / name) for name in ("SPX1T001.csv", "SPX1T002.csv", "SPX1T003.csv", "SPX1T004.csv", "results_sufficiency_proxy.md")}}
    (HERE / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
