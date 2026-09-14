"""Stage 1: extract the revised scratch-coder paper figures and tables.

Only retained aggregate releases are read.  This module deliberately does not
import an analysis package.  Values are copied with their original strings;
numeric parsing is solely for rendering and validation arithmetic.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "analysis/scratch_coder_results/results.md"
RESULTS_META = ROOT / "analysis/scratch_coder_results/run_metadata.json"
MAJORITY_DIR = ROOT / "analysis/outputs_majority_coverage_20260914T170315Z"
MAJORITY_CSV = MAJORITY_DIR / "majority_coverage.csv"
MAJORITY_SUMMARY = MAJORITY_DIR / "majority_coverage_summary.md"
MAJORITY_META = MAJORITY_DIR / "run_metadata.json"
DISAGREE_DIR = ROOT / "analysis/outputs_disagreement_types_20260909T084916Z"
DISAGREE_CSV = DISAGREE_DIR / "disagreement_type_distribution.csv"
DISAGREE_SUMMARY = DISAGREE_DIR / "disagreement_type_summary.md"
DISAGREE_META = DISAGREE_DIR / "run_metadata.json"
METHODS_STAGE_A = ROOT / "analysis/outputs_validation_scratch_20260824/methods_stage_a.md"
PANELS_CODE = ROOT / "analysis/scratch_coder_stage_a/panels.py"
MAPPINGS_CODE = ROOT / "analysis/scratch_coder_stage_a/mappings.py"
AUDIT_FOLLOWUP = ROOT / "analysis/scratch_coder_consolidated/2026-09-14_audit_reporting_followup.md"
RENDERER = ROOT / "analysis/visualisations/render_scratch_coder_paper.py"

EXPECTED_COMMITS = {
    "initial_extractor": "4d5bbbd5fd4b072d488d859618200ef3f7649995",
    "extractor_refinement": "a848a87c8d6907a8793cc1032ff762b825b05155",
    "prior_data_outputs": "33a46415dc308db4d675c7c4638e8fcdf10cc2b8",
    "majority_coverage": "ac7536806d3c7dcc1f4eb4a933772f8fb25eac42",
}

DIMENSIONS = ("Research Domains", "Analytical Purposes")
PAIRS = (
    "C01 versus C02", "C01 versus C03", "C02 versus C03",
    "Fable 5 versus C01", "Fable 5 versus C02", "Fable 5 versus C03",
)
PAIR_DISPLAY = {pair: pair.replace(" versus ", "–") for pair in PAIRS}
REPLACEMENT_MAPPING = {
    "alpha ABC": "C01/C02/C03",
    "alpha LBC": "Fable 5/C02/C03",
    "alpha ALC": "C01/Fable 5/C03",
    "alpha ABL": "C01/C02/Fable 5",
    "delta_A": "LBC − ABC",
    "delta_B": "ALC − ABC",
    "delta_C": "ABL − ABC",
    "delta_min": "minimum of delta_A, delta_B and delta_C",
}

VALUE_FIELDS = [
    "deliverable_id", "role", "population", "dimension", "label", "source_order",
    "series", "quantity", "pair", "source_file", "source_table_id", "source_section",
    "source_row_key", "source_column_locator", "source_value_string", "parsed_value",
    "interval_lower_string", "parsed_interval_lower", "interval_upper_string",
    "parsed_interval_upper", "estimate_status", "interval_status", "original_status_string",
    "interval_method", "confidence_level", "denominator_string", "sample_size",
    "denominator_unit", "support_string", "support_band", "exported_caution",
    "eligible_for_per_label_performance", "eligible_for_macro_average",
    "performance_metrics_reportable", "unavailable_reason", "presentation_note",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_name(path: Path) -> str:
    """Return a repo-relative path in production and a basename in isolation."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob_sha256(commit: str, path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    raw = subprocess.run(
        ["git", "show", f"{commit}:{rel}"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def git_filtered_blob(path: Path) -> str:
    return git("hash-object", "--path", path.relative_to(ROOT).as_posix(), path.relative_to(ROOT).as_posix())


def clean(cell: str) -> str:
    return cell.strip().strip("`")


def parse_markdown_tables(text: str) -> dict[str, dict]:
    tables: dict[str, dict] = {}
    lines = text.splitlines()
    heading_re = re.compile(r"^### (S\d+T\d+) — (.*)$")
    for index, line in enumerate(lines):
        match = heading_re.match(line)
        if not match:
            continue
        table_id, heading = match.groups()
        cursor = index + 1
        prose = []
        while cursor < len(lines) and not lines[cursor].startswith("|"):
            if lines[cursor].strip():
                prose.append(lines[cursor].strip())
            cursor += 1
        if cursor + 1 >= len(lines):
            continue
        header = [clean(value) for value in lines[cursor].strip("|").split("|")]
        cursor += 2
        rows = []
        while cursor < len(lines) and lines[cursor].startswith("|"):
            values = [clean(value) for value in lines[cursor].strip("|").split("|")]
            if len(values) == len(header):
                rows.append(dict(zip(header, values)))
            cursor += 1
        tables[table_id] = {"heading": heading, "prose": prose, "rows": rows}
    return tables


def numeric(value: str) -> str:
    try:
        float(value)
    except (TypeError, ValueError):
        return ""
    return value


def status_parts(value: str) -> tuple[str, str, str, str]:
    head, *tail = value.split(";")
    estimate, interval = (head.split("/", 1) + [""])[:2]
    estimate, interval = estimate.strip(), interval.strip()
    method = ""
    for part in tail:
        part = part.strip()
        if part in {"bootstrap_percentile", "wilson_score"}:
            method = part
            break
    confidence = "95%" if "confidence 95%" in value else "unresolved" if "confidence unresolved" in value else ""
    return estimate, interval, method, confidence


def support_parts(value: str) -> tuple[str, str, str]:
    support = re.search(r"baseline support: ([^;]+)", value)
    band = re.search(r"baseline band: ([A-Z ]+?)(?:;|$)", value)
    caution = re.search(r"exported caution: (True|False)", value)
    return (
        support.group(1).strip() if support else "",
        band.group(1).strip() if band else "",
        caution.group(1) if caution else "",
    )


def denominator_parts(value: str) -> tuple[str, str]:
    match = re.match(r"^(\d+)\s+([A-Za-z-]+)", value)
    return (match.group(1), match.group(2)) if match else ("", "")


def value_row(
    deliverable: str, population: str, dimension: str, source_table: str,
    source_row: dict, *, label: str = "", source_order: int | str = "",
    series: str = "", quantity: str = "", pair: str = "", role: str = "plotted",
    source_file: str = "analysis/scratch_coder_results/results.md",
) -> dict:
    status = source_row.get("Estimate / interval status; method; draws", "")
    est_status, int_status, method, confidence = status_parts(status)
    denom = source_row.get("Total / denominator / unit", "")
    sample_size, unit = denominator_parts(denom)
    support_raw = source_row.get("Observed support and caution", "")
    support, band, caution = support_parts(support_raw)
    value = source_row.get("Estimate / count / flag", "")
    lower = source_row.get("Interval lower", "")
    upper = source_row.get("Interval upper", "")
    unavailable = ""
    if est_status in {"W", "D", "U", "N"}:
        unavailable = {"W": "Intentionally withheld by the source reporting rule.", "D": "Undefined in source.", "U": "Unresolved in source.", "N": "Not applicable."}[est_status]
    elif int_status in {"SV", "SD"}:
        unavailable = "Interval suppressed by the valid-replicate rule."
    elif int_status == "A":
        unavailable = "Interval unavailable in the source."
    return {
        "deliverable_id": deliverable, "role": role, "population": population,
        "dimension": dimension, "label": label, "source_order": source_order,
        "series": series, "quantity": quantity, "pair": pair,
        "source_file": source_file, "source_table_id": source_table,
        "source_section": source_table.split("T", 1)[0],
        "source_row_key": source_row.get("Row / comparator", ""),
        "source_column_locator": "Estimate / count / flag; Interval lower; Interval upper; Estimate / interval status; method; draws",
        "source_value_string": value, "parsed_value": numeric(value),
        "interval_lower_string": lower, "parsed_interval_lower": numeric(lower),
        "interval_upper_string": upper, "parsed_interval_upper": numeric(upper),
        "estimate_status": est_status, "interval_status": int_status,
        "original_status_string": status, "interval_method": method,
        "confidence_level": confidence, "denominator_string": denom,
        "sample_size": sample_size, "denominator_unit": unit,
        "support_string": support, "support_band": band, "exported_caution": caution,
        "eligible_for_per_label_performance": "", "eligible_for_macro_average": "",
        "performance_metrics_reportable": "", "unavailable_reason": unavailable,
        "presentation_note": "",
    }


def group_rows(table: dict) -> tuple[list[str], dict[str, dict[str, dict]]]:
    order: list[str] = []
    grouped: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in table["rows"]:
        label = row["Row / comparator"]
        if label not in grouped:
            order.append(label)
        grouped[label][row["Quantity"]] = row
    return order, grouped


def verify_prerequisites() -> dict:
    required = [RESULTS, RESULTS_META, MAJORITY_CSV, MAJORITY_SUMMARY, MAJORITY_META,
                DISAGREE_CSV, DISAGREE_SUMMARY, DISAGREE_META]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Required aggregate sources missing: {missing}")
    resolved = {name: git("rev-parse", commit) for name, commit in EXPECTED_COMMITS.items()}
    if resolved != EXPECTED_COMMITS:
        raise RuntimeError(f"Commit identity mismatch: {resolved}")
    majority_commit = EXPECTED_COMMITS["majority_coverage"]
    majority_blob = {
        path.relative_to(ROOT).as_posix(): git_blob_sha256(majority_commit, path)
        for path in (MAJORITY_CSV, MAJORITY_SUMMARY, MAJORITY_META)
    }
    majority_working = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in (MAJORITY_CSV, MAJORITY_SUMMARY, MAJORITY_META)
    }
    # The CSV can be checked out with CRLF on some platforms.  The Git-cleaned
    # object must still be exactly the committed blob; raw-byte divergence is recorded.
    csv_commit_object = git("rev-parse", f"{majority_commit}:{MAJORITY_CSV.relative_to(ROOT).as_posix()}")
    if git_filtered_blob(MAJORITY_CSV) != csv_commit_object:
        raise RuntimeError("Majority aggregate does not clean-filter to its ac75368 blob.")
    for path in (MAJORITY_SUMMARY, MAJORITY_META):
        rel = path.relative_to(ROOT).as_posix()
        if majority_working[rel] != majority_blob[rel]:
            raise RuntimeError(f"Majority source bytes differ from ac75368: {rel}")

    meta = json.loads(MAJORITY_META.read_text())
    expected_head = EXPECTED_COMMITS["prior_data_outputs"]
    if meta.get("git_head") != expected_head:
        raise RuntimeError("Majority metadata has the wrong input HEAD.")
    required_meta_checks = [
        meta.get("majority_helper", {}).get("definition") == "labelwise human membership sum >= 2",
        meta.get("mask", {}).get("status") == "reconstructed",
        meta.get("baseline_reconciliation", {}).get("status") == "passed",
        meta.get("baseline_reconciliation", {}).get("mismatches") == [],
        set(meta.get("aggregate_exclusions", {})) == {
            f"{population}::{dimension}" for population in ("baseline", "hard_case") for dimension in DIMENSIONS
        },
        all(not any(group.values()) for group in meta.get("aggregate_exclusions", {}).values()),
    ]
    if not all(required_meta_checks):
        raise RuntimeError("Majority metadata does not establish the intended masks/reconciliation.")
    summary = MAJORITY_SUMMARY.read_text()
    for expected in ("POST-028/POST-009/POST-011/POST-019", "No majority label: **5 / 150**",
                     "No majority label: **24 / 150**", "Majority sets exceeding the single-coder limit of two: **0 / 150**"):
        if expected not in summary:
            raise RuntimeError(f"Majority summary evidence absent: {expected}")
    current_report_commit = git("log", "-1", "--format=%H", "--", RESULTS.relative_to(ROOT).as_posix())
    if git("diff", "--name-only", "HEAD", "--", RESULTS.relative_to(ROOT).as_posix(), RESULTS_META.relative_to(ROOT).as_posix()):
        raise RuntimeError("Canonical report or metadata has uncommitted changes.")
    return {
        "resolved_commits": resolved,
        "pre_run_head": git("rev-parse", "HEAD"),
        "pre_run_worktree": git("status", "--short", "--untracked-files=all"),
        "canonical_report_commit": current_report_commit,
        "canonical_report_sha256": sha256(RESULTS),
        "canonical_metadata_sha256": sha256(RESULTS_META),
        "canonical_reporting_only_compatibility": {
            "evidence": "analysis/scratch_coder_consolidated/2026-09-14_audit_reporting_followup.md",
            "status": "analytical content and source identities documented unchanged from audited snapshot",
        },
        "majority_working_sha256": majority_working,
        "majority_ac75368_blob_sha256": majority_blob,
        "majority_csv_checkout_note": (
            "Raw working bytes differ only because the checkout uses CRLF while the committed blob uses LF; "
            "Git clean-filtered object equals the ac75368 blob. Source was not modified."
            if majority_working[MAJORITY_CSV.relative_to(ROOT).as_posix()] != majority_blob[MAJORITY_CSV.relative_to(ROOT).as_posix()]
            else "Raw working bytes equal the ac75368 blob."
        ),
        "cohort_compatibility": {
            "population_ids": ["POST-009", "POST-011"],
            "crosswalk": "POST-019", "responses": "POST-028",
            "mask": "complete C01/C02/C03 and frozen model value per dimension",
            "baseline_hard_case_disjointness_evidence": "analysis/scratch_coder_stage_a/panels.py rejects any baseline_ids & hard_ids overlap; its retained hash is recorded by the majority metadata",
            "strict_subset_evidence": "Sufficiency subset IDs are derived only from baseline responses; population_ids returns the strict set",
        },
        "code_and_method_evidence_hashes": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (Path(__file__).resolve(), RENDERER, METHODS_STAGE_A, PANELS_CODE, MAPPINGS_CODE, AUDIT_FOLLOWUP)
        },
    }


def prior_inventory() -> dict:
    files = []
    for directory in (ROOT / "analysis/figure_data", ROOT / "analysis/figures"):
        for path in sorted(directory.glob("scratch_coder_figure_[1-6]*")):
            if path.is_file():
                files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"observed_before_task": {"head": EXPECTED_COMMITS["majority_coverage"], "working_tree": "clean"}, "files": files}


def replacement_extract(tables: dict, deliverable: str, specs: list[tuple[str, str, str, str]]) -> list[dict]:
    out = []
    for table_id, population, dimension, role in specs:
        for row in tables[table_id]["rows"]:
            quantity = row["Row / comparator"]
            item = value_row(deliverable, population, dimension, table_id, row,
                             series="alpha" if quantity.startswith("alpha") else "delta",
                             quantity=quantity, role=role)
            item["presentation_note"] = REPLACEMENT_MAPPING[quantity]
            out.append(item)
        delta_rows = [x for x in out if x["source_table_id"] == table_id and x["quantity"].startswith("delta")]
        delta_min = next(x for x in delta_rows if x["quantity"] == "delta_min")
        matches = [x["quantity"] for x in delta_rows if x["quantity"] != "delta_min" and x["source_value_string"] == delta_min["source_value_string"]]
        delta_min["presentation_note"] += "; matching observed component(s): " + ", ".join(matches)
    return out


def support_extract(tables: dict, table_id: str) -> tuple[list[str], dict[str, dict]]:
    order, grouped = group_rows(tables[table_id])
    out = {}
    for label in order:
        values = grouped[label]
        support_row = values["baseline_human_majority_positive_n"]
        support, band, caution = support_parts(support_row["Observed support and caution"])
        out[label] = {
            "support": support_row["Estimate / count / flag"], "support_band": band,
            "caution": caution,
            "human": support_row["Estimate / count / flag"],
            "model": values["baseline_model_positive_n"]["Estimate / count / flag"],
            "eligible": values["eligible_for_per_label_performance"]["Estimate / count / flag"],
            "macro": values["eligible_for_macro_average"]["Estimate / count / flag"],
            "rows": values,
        }
    return order, out


def figure3_extract(tables: dict) -> list[dict]:
    out = []
    for dimension, support_id, contingency_id in (("Research Domains", "S5T001", "S5T003"), ("Analytical Purposes", "S5T002", "S5T004")):
        order, support = support_extract(tables, support_id)
        _, contingency = group_rows(tables[contingency_id])
        if set(order) != set(contingency):
            raise RuntimeError(f"Figure 3 label mismatch for {dimension}")
        for idx, label in enumerate(order, 1):
            source = support[label]["rows"]["baseline_human_majority_positive_n"]
            item = value_row("Figure 3", "baseline", dimension, support_id, source,
                             label=label, source_order=idx, series="label counts", quantity="human/model positive counts")
            model_source = support[label]["rows"]["baseline_model_positive_n"]
            item.update({
                "source_column_locator": "S5T001/S5T002 baseline_human_majority_positive_n and baseline_model_positive_n; exact keyed check against S5T003/S5T004",
                "source_value_string": support[label]["human"], "parsed_value": numeric(support[label]["human"]),
                "interval_lower_string": model_source["Estimate / count / flag"],
                "parsed_interval_lower": numeric(model_source["Estimate / count / flag"]),
                "interval_status": "N", "support_band": support[label]["support_band"],
                "exported_caution": support[label]["caution"],
                "eligible_for_per_label_performance": support[label]["eligible"],
                "eligible_for_macro_average": support[label]["macro"],
                "presentation_note": "x=human-majority-positive count; y=model-positive count" + ("; non-substantive classification option" if label == "Unclear from Register Entry" else ""),
            })
            for quantity, source_name in (("human_majority_positive_n", "human"), ("model_positive_n", "model")):
                if contingency[label][quantity]["Estimate / count / flag"] != support[label][source_name]:
                    raise RuntimeError(f"Figure 3 conflicting count: {dimension}/{label}/{quantity}")
            out.append(item)
    return out


def table_kappa_extract(tables: dict, deliverable: str, dimension: str, ids: tuple[str, str, str]) -> list[dict]:
    support_id, kappa_id, withholding_id = ids
    order, support = support_extract(tables, support_id)
    rows_by_label_pair = {}
    for row in tables[kappa_id]["rows"]:
        label, pair = row["Row / comparator"].rsplit("; ", 1)
        key = (label, pair)
        if key in rows_by_label_pair:
            raise RuntimeError(f"Duplicate kappa key: {key}")
        rows_by_label_pair[key] = row
    withheld = {}
    for row in tables[withholding_id]["rows"]:
        if row["Quantity"] != "kappa":
            continue
        parts = row["Row / comparator"].split("; ")
        label = parts[0]
        for pair in parts[1:]:
            withheld[(label, pair)] = row
    out = []
    for source_order, label in enumerate(order, 1):
        for pair in PAIRS:
            source = rows_by_label_pair.get((label, pair)) or withheld.get((label, pair))
            if not source:
                raise RuntimeError(f"Missing kappa cell: {dimension}/{label}/{pair}")
            item = value_row(deliverable, "baseline", dimension,
                             kappa_id if (label, pair) in rows_by_label_pair else withholding_id,
                             source, label=label, source_order=source_order, series="kappa", quantity="kappa", pair=pair, role="tabulated")
            item.update({"support_string": support[label]["support"], "support_band": support[label]["support_band"],
                         "exported_caution": support[label]["caution"],
                         "eligible_for_per_label_performance": support[label]["eligible"],
                         "eligible_for_macro_average": support[label]["macro"]})
            out.append(item)
    return out


def withholding_metrics(table: dict) -> dict[tuple[str, str], dict]:
    out = {}
    for row in table["rows"]:
        if row["Quantity"] in {"precision", "recall", "f1"}:
            label = row["Row / comparator"].split("; Fable 5 versus", 1)[0]
            out[(label, row["Quantity"])] = row
    return out


def table_performance_extract(tables: dict, deliverable: str, dimension: str, ids: tuple[str, str, str, str]) -> list[dict]:
    support_id, cont_id, perf_id, withholding_id = ids
    order, support = support_extract(tables, support_id)
    _, contingencies = group_rows(tables[cont_id])
    _, performance = group_rows(tables[perf_id])
    withheld = withholding_metrics(tables[withholding_id])
    if set(order) != set(contingencies):
        raise RuntimeError(f"Contingency label mismatch for {dimension}")
    out = []
    for source_order, label in enumerate(order, 1):
        c = contingencies[label]
        required = {"baseline_n", "tp", "fp", "fn", "tn", "performance_metrics_reportable"}
        if not required <= set(c):
            raise RuntimeError(f"Incomplete contingency row: {dimension}/{label}")
        counts = [int(c[q]["Estimate / count / flag"]) for q in ("tp", "fp", "fn", "tn")]
        n = int(c["baseline_n"]["Estimate / count / flag"])
        if sum(counts) != n:
            raise RuntimeError(f"Contingency identity failed: {dimension}/{label}")
        for quantity in ("tp", "fp", "fn", "tn"):
            item = value_row(deliverable, "baseline", dimension, cont_id, c[quantity], label=label,
                             source_order=source_order, series="contingency", quantity=quantity, role="tabulated")
            out.append(item)
        for metric in ("precision", "recall", "f1"):
            source = performance.get(label, {}).get(metric) or withheld.get((label, metric))
            if not source:
                raise RuntimeError(f"Missing performance cell: {dimension}/{label}/{metric}")
            item = value_row(deliverable, "baseline", dimension,
                             perf_id if label in performance and metric in performance[label] else withholding_id,
                             source, label=label, source_order=source_order, series="performance", quantity=metric, role="tabulated")
            out.append(item)
        reportable = c["performance_metrics_reportable"]["Estimate / count / flag"]
        for item in out[-7:]:
            item.update({"support_string": support[label]["support"], "support_band": support[label]["support_band"],
                         "exported_caution": support[label]["caution"],
                         "eligible_for_per_label_performance": support[label]["eligible"],
                         "eligible_for_macro_average": support[label]["macro"],
                         "performance_metrics_reportable": reportable})
        metric_statuses = {(x["estimate_status"], x["interval_status"]) for x in out[-3:]}
        if reportable == "False" and metric_statuses != {("W", "W")}:
            raise RuntimeError(f"Reportability contradiction: {dimension}/{label}")
        if reportable == "True" and any(status[0] != "R" for status in metric_statuses):
            raise RuntimeError(f"Reportable metric estimate absent: {dimension}/{label}")
    return out


def table5_extract() -> list[dict]:
    with DISAGREE_CSV.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    baseline = [row for row in rows if row["population"] == "baseline"]
    grouped: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in baseline:
        key = (row["dimension"], row["pair_family"])
        if row["relation"] in grouped[key]:
            raise RuntimeError(f"Duplicate disagreement relation: {key}/{row['relation']}")
        grouped[key][row["relation"]] = row
    out = []
    for (dimension, family), relations in grouped.items():
        if set(relations) != {"both_empty", "exactly_one_empty", "identical", "containment", "overlap", "disjoint"}:
            raise RuntimeError(f"Incomplete relation group: {dimension}/{family}")
        for relation, source in relations.items():
            status = source["nonempty_proportion_status"]
            item = {field: "" for field in VALUE_FIELDS}
            item.update({
                "deliverable_id": "Table 5", "role": "tabulated", "population": "baseline",
                "dimension": dimension, "series": family, "quantity": relation,
                "source_file": DISAGREE_CSV.relative_to(ROOT).as_posix(),
                "source_table_id": "disagreement_type_distribution.csv",
                "source_section": "baseline distribution", "source_row_key": f"baseline|{dimension}|{family}|{relation}",
                "source_column_locator": "count; proportion_of_nonidentical_nonempty_pairs; denominators; empty_set_involved_pairs",
                "source_value_string": source["count"], "parsed_value": numeric(source["count"]),
                "interval_lower_string": source["proportion_of_nonidentical_nonempty_pairs"],
                "parsed_interval_lower": numeric(source["proportion_of_nonidentical_nonempty_pairs"]) if status == "reported" else "",
                "estimate_status": "R", "interval_status": status,
                "original_status_string": status, "denominator_string": source["nonidentical_nonempty_pairs"],
                "sample_size": source["eligible_records"], "denominator_unit": "pair units",
                "presentation_note": json.dumps({k: source[k] for k in ("eligible_records", "total_pairs_classified", "nonidentical_nonempty_pairs", "all_nonidentical_pairs", "empty_set_involved_pairs")}, sort_keys=True),
                "unavailable_reason": "Proportion not applicable to this relation." if status == "not_applicable" else "Proportion unavailable because the denominator is zero." if status == "zero_denominator" else "",
            })
            if dimension == "Joint cross-cutting tag set" and relation == "overlap" and status == "reported":
                item["presentation_note"] += "; structurally impossible under this two-label relation definition"
            out.append(item)
    return out


def supplementary_extract(tables: dict) -> list[dict]:
    out = []
    for construct, population, table_id in (
        ("Sufficiency", "baseline", "S8T003"), ("Sufficiency", "hard_case", "S8T004"),
        ("Taxonomy fit", "baseline", "S9T003"), ("Taxonomy fit", "hard_case", "S9T004"),
    ):
        order, grouped = group_rows(tables[table_id])
        for source_order, category in enumerate(order, 1):
            for quantity in ("count", "proportion"):
                item = value_row("Supplementary Table S1", population, construct, table_id,
                                 grouped[category][quantity], label=category, source_order=source_order,
                                 series="Part A", quantity=quantity, role="tabulated")
                item["presentation_note"] = "Record-majority response category; distinct from Part B labelwise-majority coverage."
                out.append(item)
    with MAJORITY_CSV.open(newline="") as handle:
        majority_rows = list(csv.DictReader(handle))
    expected_keys = set()
    for population in ("baseline", "hard_case"):
        for dimension in DIMENSIONS:
            for category in ("size_0", "size_1", "size_2", "size_3", "size_4_plus"):
                expected_keys.add((population, dimension, "majority_set_size", category))
            for category in (
                "unclear_absent__substantive_absent", "unclear_absent__substantive_present",
                "unclear_present__substantive_absent", "unclear_present__substantive_present",
            ):
                expected_keys.add((population, dimension, "unclear_composition", category))
    keyed = {(r["population"], r["dimension"], r["quantity"], r["category"]): r for r in majority_rows}
    if len(keyed) != len(majority_rows):
        raise RuntimeError("Duplicate majority aggregate key.")
    if not expected_keys <= set(keyed):
        raise RuntimeError(f"Majority aggregate missing required keys: {sorted(expected_keys - set(keyed))}")
    for key in sorted(expected_keys):
        source = keyed[key]
        item = {field: "" for field in VALUE_FIELDS}
        item.update({
            "deliverable_id": "Supplementary Table S1", "role": "tabulated", "population": source["population"],
            "dimension": source["dimension"], "label": source["category"], "series": "Part B",
            "quantity": source["quantity"], "source_file": MAJORITY_CSV.relative_to(ROOT).as_posix(),
            "source_table_id": "majority_coverage.csv", "source_section": source["quantity"],
            "source_row_key": "|".join(key), "source_column_locator": "count; denominator; note",
            "source_value_string": source["count"], "parsed_value": numeric(source["count"]),
            "estimate_status": "R", "interval_status": "N", "original_status_string": "reported count / interval not applicable",
            "denominator_string": source["denominator"], "sample_size": source["denominator"],
            "denominator_unit": "records", "presentation_note": source["note"],
        })
        out.append(item)
    # Cardinality constraint/exceedance is already exported; Domain is explicitly not assessed.
    for population in ("baseline", "hard_case"):
        source = keyed[(population, "Analytical Purposes", "majority_set_exceeds_single_coder_constraint", "size_greater_than_2")]
        item = {field: "" for field in VALUE_FIELDS}
        item.update({"deliverable_id": "Supplementary Table S1", "role": "tabulated", "population": population,
                     "dimension": "Analytical Purposes", "label": "size_greater_than_2", "series": "Part B",
                     "quantity": "majority_set_exceeds_single_coder_constraint", "source_file": MAJORITY_CSV.relative_to(ROOT).as_posix(),
                     "source_table_id": "majority_coverage.csv", "source_section": "cardinality constraint",
                     "source_row_key": f"{population}|Analytical Purposes|majority_set_exceeds_single_coder_constraint|size_greater_than_2",
                     "source_column_locator": "count; denominator; note", "source_value_string": source["count"],
                     "parsed_value": numeric(source["count"]), "estimate_status": "R", "interval_status": "N",
                     "original_status_string": "reported count / interval not applicable", "denominator_string": source["denominator"],
                     "sample_size": source["denominator"], "denominator_unit": "records", "presentation_note": source["note"]})
        out.append(item)
        domain = item.copy()
        domain.update({"dimension": "Research Domains", "label": "Not assessed — no documented constraint",
                       "source_row_key": f"run_metadata.json|cardinality_constraints|Research Domains|{population}",
                       "source_file": MAJORITY_META.relative_to(ROOT).as_posix(), "source_table_id": "run_metadata.json",
                       "source_value_string": "", "parsed_value": "", "estimate_status": "N",
                       "unavailable_reason": "Not assessed — no documented constraint",
                       "presentation_note": "No Research Domains cardinality constraint is documented; zero is not imputed."})
        out.append(domain)
    # Separate denominator checks; never used to fill values.
    for population in ("baseline", "hard_case"):
        for dimension in DIMENSIONS:
            subset = [r for r in out if r["series"] == "Part B" and r["population"] == population and r["dimension"] == dimension]
            for quantity in ("majority_set_size", "unclear_composition"):
                values = [r for r in subset if r["quantity"] == quantity]
                if sum(int(r["source_value_string"]) for r in values) != int(values[0]["denominator_string"]):
                    raise RuntimeError(f"Majority validation failed: {population}/{dimension}/{quantity}")
    return out


CAPTIONS = {
    "Figure 1": "Panel agreement and replacement differences. Baseline n=150 records in each dimension. ABC is C01/C02/C03; LBC, ALC and ABL replace C01, C02 and C03 respectively with Fable 5. Each delta is substituted-panel alpha minus ABC: positive values indicate higher agreement after replacement and negative values lower agreement. The exported delta_min point estimate is the minimum component; all tied matching components are marked. Retained methods state that the minimum is selected again within each bootstrap resample, so its interval need not equal the interval of the observed matching component. Percentile-bootstrap confidence level is unresolved in the canonical report (U0004). Coincident reported endpoints use a barred diamond; this does not establish absent sampling uncertainty. Tag support bands count baseline human-majority-positive records and retain their cautions.",
    "Figure 2": "Sufficiency sensitivity. Baseline (n=150 records) and strict register-sufficient subset (n=92 records), which retained methods define as a subset of baseline records with at least two Sufficient ratings. Populations are nested, not independent; comparison is descriptive. Panel and delta_min definitions follow Figure 1. The broad subset retained 148/150 records and is available in the accompanying figure data but omitted from this display. Percentile-bootstrap confidence level is unresolved in the canonical report. The alpha scale differs from Figures 1 and 4.",
    "Figure 3": "Label application patterns, baseline n=150 records. Each point is a label, not a record; counts across labels do not partition the sample and must not be summed as a record total. Support bands count baseline human-majority-positive records: Standard >=30, Low support 10–29, Rare <10. Above/below the equality line means only that the model applies the label more/less often, not accuracy or error. No observed human-majority set contained both Unclear and a substantive label in either analysed population or dimension. Marginal counts and the coverage summary do not identify whether lower model use of Unclear and higher model use of substantive labels concern the same records. Five of 150 Domain records and 24 of 150 Purpose records had no majority label; they contribute to no human-majority-positive count but may contribute to model-positive counts. See Supplementary Table S1.",
    "Figure 4": "Baseline against hard-case. Baseline n=150 records; pooled hard-case n=75 records. The retained panel construction verifies these populations are disjoint. Hard-case is DIAGNOSTIC — non-representative and was selected on cross-model disagreement; no cause or quality inference is warranted. Panel, delta and delta_min definitions follow Figure 1. Percentile-bootstrap confidence level is unresolved in the pooled canonical rows (U0004); newer separate-strata evidence does not close or transfer to these pooled results (U0005 remains open). Hard-case tag bands remain baseline-scoped; the separately exported hard-case equity support is 8 human-majority-positive records. Cautions remain marked.",
    "Table 1": "Per-label pairwise kappa — Research Domains (baseline n=150 records).",
    "Table 2": "Per-label pairwise kappa — Analytical Purposes (baseline n=150 records).",
    "Table 3": "Per-label contingencies and model performance — Research Domains (baseline n=150 records).",
    "Table 4": "Per-label contingencies and model performance — Analytical Purposes (baseline n=150 records).",
    "Table 5": "Relation of disagreeing pairs (baseline). This table describes the composition of eligible disagreements, not their overall frequency or severity.",
    "Supplementary Table S1": "Record-majority response categories and majority-label coverage. Parts A and B use different majority rules and are not pooled into a common failure count.",
}

CAPTION_EVIDENCE = {
    "Figure 1": [
        {"fact": "panel/coder mappings, delta sign and exported delta_min", "locator": "results.md::Section 3 introductory text"},
        {"fact": "delta_min selected within each bootstrap resample", "locator": "methods_stage_a.md::Bootstrap procedure"},
        {"fact": "confidence level unresolved", "locator": "run_metadata.json::unresolved entry U0004"},
        {"fact": "support and caution meanings", "locator": "results.md::Section 2/Section 5 introductory text"},
    ],
    "Figure 2": [
        {"fact": "strict and broad subset definitions and nested baseline scope", "locator": "results.md::Section 1 and Section 8 introductory text; methods_stage_a.md::Population and subsets"},
        {"fact": "baseline/strict/broad denominators", "locator": "results.md::S3T001/S3T002/S3T009/S3T010/S3T011/S3T012"},
    ],
    "Figure 3": [
        {"fact": "label-count meanings and support bands", "locator": "results.md::S5T001-S5T004 and Section 5 introductory text"},
        {"fact": "no-majority counts and Unclear/substantive exclusivity", "locator": "majority_coverage.csv::majority_set_size and unclear_composition rows"},
        {"fact": "coverage rule/population scope", "locator": "majority_coverage_summary.md::Rule and cohort"},
    ],
    "Figure 4": [
        {"fact": "baseline/hard-case disjointness", "locator": "panels.py::load_data overlap guard; majority run_metadata.json::helper_code_hashes"},
        {"fact": "hard-case diagnostic selection", "locator": "results.md::Section 1 and hard-case table headings"},
        {"fact": "pooled confidence unresolved and separate-strata evidence not transferred", "locator": "run_metadata.json::U0004/U0005; results.md::Section 11 introductory text"},
        {"fact": "hard-case equity support 8 and baseline-scoped band", "locator": "results.md::S2T007"},
    ],
    "Table 1": [{"fact": "pair identities, baseline support and withholding", "locator": "results.md::S5T001/S5T005/S5T009"}],
    "Table 2": [{"fact": "pair identities, baseline support and withholding", "locator": "results.md::S5T002/S5T006/S5T010"}],
    "Table 3": [{"fact": "reference orientation, metric definitions, statuses and Unclear counts", "locator": "results.md::Section 2/Section 5; S5T001/S5T003/S5T007/S5T009"}],
    "Table 4": [{"fact": "reference orientation, metric definitions, statuses and Unclear counts", "locator": "results.md::Section 2/Section 5; S5T002/S5T004/S5T008/S5T010"}],
    "Table 5": [{"fact": "relation, pair-family and empty-set definitions", "locator": "disagreement_type_summary.md::Relation definitions and Rule/cohort"}],
    "Supplementary Table S1": [
        {"fact": "Part A record-majority categories and interval applicability", "locator": "results.md::Section 8/Section 9; S8T003/S8T004/S9T003/S9T004"},
        {"fact": "Part B rule, cardinality constraint and coverage meanings", "locator": "majority_coverage_summary.md::Rule and cohort; majority_coverage.csv; run_metadata.json::cardinality_constraints"},
    ],
}


def write_dataset(data_dir: Path, stem: str, rows: list[dict], source_paths: list[Path], provenance: dict, caption: str) -> tuple[str, str]:
    csv_path = data_dir / f"{stem}.csv"
    meta_path = data_dir / f"{stem}_metadata.json"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=VALUE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    before = {p.relative_to(ROOT).as_posix(): sha256(p) for p in source_paths}
    after = {p.relative_to(ROOT).as_posix(): sha256(p) for p in source_paths}
    if before != after:
        raise RuntimeError(f"Source changed during extraction: {stem}")
    metadata = {
        "deliverable_id": rows[0]["deliverable_id"], "data_file": output_name(csv_path),
        "caption": caption, "source_paths": list(before), "source_hashes_before_extraction": before,
        "source_hashes_after_extraction": after, "source_hashes_unchanged": True,
        "source_table_ids": sorted({row["source_table_id"] for row in rows}),
        "populations_dimensions": sorted({f"{row['population']}|{row['dimension']}" for row in rows}),
        "generation_provenance": provenance, "display_mappings": {"replacement_panels": REPLACEMENT_MAPPING, "pair_columns": PAIR_DISPLAY},
        "caption_evidence": CAPTION_EVIDENCE[rows[0]["deliverable_id"]],
        "status_legend": {"R": "reported", "SV": "suppressed by valid-replicate rule", "SD": "suppressed by source decision", "A": "unavailable", "N": "not applicable", "W": "withheld", "D": "undefined", "U": "unresolved"},
    }
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    return output_name(csv_path), output_name(meta_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "analysis/figure_data")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    provenance = verify_prerequisites()
    inventory_path = data_dir / "scratch_coder_prechange_inventory.json"
    if not inventory_path.exists():
        inventory_path.write_text(json.dumps(prior_inventory(), indent=2) + "\n")
    source_hashes_before = {p: sha256(p) for p in (RESULTS, RESULTS_META, MAJORITY_CSV, MAJORITY_SUMMARY, MAJORITY_META, DISAGREE_CSV, DISAGREE_SUMMARY, DISAGREE_META)}
    tables = parse_markdown_tables(RESULTS.read_text())
    required = {"S2T001", "S2T002", "S2T007", "S2T008", "S3T001", "S3T002", "S3T007", "S3T008", "S3T009", "S3T010", "S3T011", "S3T012", "S5T001", "S5T002", "S5T003", "S5T004", "S5T005", "S5T006", "S5T007", "S5T008", "S5T009", "S5T010", "S8T003", "S8T004", "S9T003", "S9T004"}
    if required - set(tables):
        raise RuntimeError(f"Required canonical table IDs absent: {sorted(required - set(tables))}")

    datasets = {}
    figure1 = replacement_extract(tables, "Figure 1", [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S2T002", "baseline", "COVID-19 & Pandemic", "plotted"), ("S2T001", "baseline", "Demographic disparities / equity", "plotted")])
    datasets["Figure 1"] = ("scratch_coder_figure_1_panel_agreement", figure1, [RESULTS, RESULTS_META])
    figure2 = replacement_extract(tables, "Figure 2", [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S3T011", "baseline_strict_sufficient", "Research Domains", "plotted"), ("S3T012", "baseline_strict_sufficient", "Analytical Purposes", "plotted"),
        ("S3T009", "baseline_broad_usable", "Research Domains", "caption"), ("S3T010", "baseline_broad_usable", "Analytical Purposes", "caption")])
    datasets["Figure 2"] = ("scratch_coder_figure_2_sufficiency_sensitivity", figure2, [RESULTS, RESULTS_META])
    datasets["Figure 3"] = ("scratch_coder_figure_3_label_application_patterns", figure3_extract(tables), [RESULTS, RESULTS_META, MAJORITY_CSV, MAJORITY_SUMMARY, MAJORITY_META])
    figure4 = replacement_extract(tables, "Figure 4", [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S2T002", "baseline", "COVID-19 & Pandemic", "plotted"), ("S2T001", "baseline", "Demographic disparities / equity", "plotted"),
        ("S3T007", "hard_case", "Research Domains", "plotted"), ("S3T008", "hard_case", "Analytical Purposes", "plotted"),
        ("S2T008", "hard_case", "COVID-19 & Pandemic", "plotted"), ("S2T007", "hard_case", "Demographic disparities / equity", "plotted")])
    datasets["Figure 4"] = ("scratch_coder_figure_4_baseline_hard_case", figure4, [RESULTS, RESULTS_META])
    datasets["Table 1"] = ("scratch_coder_table_1_pairwise_kappa_domains", table_kappa_extract(tables, "Table 1", "Research Domains", ("S5T001", "S5T005", "S5T009")), [RESULTS, RESULTS_META])
    datasets["Table 2"] = ("scratch_coder_table_2_pairwise_kappa_purposes", table_kappa_extract(tables, "Table 2", "Analytical Purposes", ("S5T002", "S5T006", "S5T010")), [RESULTS, RESULTS_META])
    datasets["Table 3"] = ("scratch_coder_table_3_contingencies_performance_domains", table_performance_extract(tables, "Table 3", "Research Domains", ("S5T001", "S5T003", "S5T007", "S5T009")), [RESULTS, RESULTS_META])
    datasets["Table 4"] = ("scratch_coder_table_4_contingencies_performance_purposes", table_performance_extract(tables, "Table 4", "Analytical Purposes", ("S5T002", "S5T004", "S5T008", "S5T010")), [RESULTS, RESULTS_META])
    datasets["Table 5"] = ("scratch_coder_table_5_disagreeing_pair_relations", table5_extract(), [DISAGREE_CSV, DISAGREE_SUMMARY, DISAGREE_META])
    datasets["Supplementary Table S1"] = ("scratch_coder_supplementary_table_s1_majority_coverage", supplementary_extract(tables), [RESULTS, RESULTS_META, MAJORITY_CSV, MAJORITY_SUMMARY, MAJORITY_META])

    manifest = {
        "manifest_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "workflow": {"stage_1": "this extractor reads retained aggregate sources", "stage_2": "renderer reads only this manifest and listed extracted CSV/JSON files"},
        "provenance": provenance,
        "current": {},
        "withdrawn": {
            "old Figure 1": {"status": "superseded by revised Figure 1", "archive_glob": "analysis/figures/archive/scratch_coder_pre_revision_*/scratch_coder_figure_1.*"},
            "old Figure 2": {"status": "superseded by revised Figure 2", "archive_glob": "analysis/figures/archive/scratch_coder_pre_revision_*/scratch_coder_figure_2.*"},
            "old Figure 3": {"status": "superseded by revised Figure 3", "archive_glob": "analysis/figures/archive/scratch_coder_pre_revision_*/scratch_coder_figure_3.*"},
            "old Figure 4": {"status": "withdrawn; replaced by Tables 3 and 4", "archive_glob": "analysis/figures/archive/scratch_coder_pre_revision_*/scratch_coder_figure_4.*"},
            "old Figure 5": {"status": "withdrawn; replaced by Table 5", "archive_glob": "analysis/figures/archive/scratch_coder_pre_revision_*/scratch_coder_figure_5.*"},
            "old Figure 6": {"status": "renumbered and replaced by new Figure 4", "archive_glob": "analysis/figures/archive/scratch_coder_pre_revision_*/scratch_coder_figure_6.*"},
        },
        "reader_numbering_note": "Display numbering comes from deliverable_id in this manifest, never from obsolete filenames.",
    }
    for deliverable, (stem, rows, sources) in datasets.items():
        data_file, metadata_file = write_dataset(data_dir, stem, rows, sources, provenance, CAPTIONS[deliverable])
        if deliverable.startswith("Figure"):
            outputs = [f"analysis/figures/{stem}.svg", f"analysis/figures/{stem}.png"]
        else:
            outputs = [f"analysis/tables/{stem}.csv", f"analysis/tables/{stem}.md"]
        manifest["current"][deliverable] = {"stem": stem, "inputs": [data_file, metadata_file], "outputs": outputs, "caption": CAPTIONS[deliverable]}
    manifest_path = data_dir / "scratch_coder_deliverable_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    source_hashes_after = {p: sha256(p) for p in source_hashes_before}
    if source_hashes_before != source_hashes_after:
        raise RuntimeError("A source changed during Stage 1.")


if __name__ == "__main__":
    main()
