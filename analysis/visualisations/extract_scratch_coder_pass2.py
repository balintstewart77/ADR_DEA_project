"""Stage 1 for the pass-2 scratch-coder presentation run.

This program reads retained aggregate exports only.  It copies source strings
into slugged figure-data files, performs the four authorised G.12 derivations,
and writes a manifest consumed by the isolated Stage 2 renderer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import platform
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.visualisations import extract_scratch_coder_paper as legacy


RESULTS = ROOT / "analysis/scratch_coder_results/results.md"
RESULTS_META = ROOT / "analysis/scratch_coder_results/run_metadata.json"
CONFIDENCE = ROOT / "analysis/confidence_exploratory/results_confidence.md"
VERIFICATION = ROOT / "analysis/verification_pass2/verification_report.md"
INVENTORY = ROOT / "analysis/verification_pass2/v9_inventory/claims_inventory.csv"
MAJORITY = legacy.MAJORITY_CSV
DISAGREEMENT = legacy.DISAGREE_CSV
LEGACY_COMMIT = "6cbf154"
REQUIRED_ANCESTORS = ("960c38d", "6cbf154", "f36d738", "1287716")

DEFAULT_LOG_DIR = Path(r"C:\Users\balin\Desktop\DEA_working_logs")
DEFAULT_REVISION_LOG = DEFAULT_LOG_DIR / "scratch_coder_figure_revisions_log_pass2.md"
DEFAULT_FINDINGS_LOG = DEFAULT_LOG_DIR / "scratch_coder_interpretive_findings.md"

EXTRA_FIELDS = ("derivation_id", "derivation_operands", "row_group", "display_percent")
FIELDS = legacy.VALUE_FIELDS + list(EXTRA_FIELDS)

SLUGS = {
    "Figure 1": "figure_1_panel_agreement_replacement",
    "Figure 2": "figure_2_sufficiency_sensitivity",
    "Figure 3": "figure_3_label_application",
    "Figure 4": "figure_4_disagreement_composition",
    "Supplementary Figure S1": "supplementary_figure_s1_baseline_vs_hardcase",
    "Supplementary Figure S2": "supplementary_figure_s2_coder_ratings",
    "Table 1": "table_1_agreement_domains",
    "Table 2": "table_2_agreement_purposes",
    "Table 3": "table_3_agreement_with_majority_domains",
    "Table 4": "table_4_agreement_with_majority_purposes",
    "Table 5": "table_5_disagreement_composition",
    "Supplementary Table S1a": "supplementary_table_s1a_register_information",
    "Supplementary Table S1b": "supplementary_table_s1b_taxonomy_fit",
    "Supplementary Table S1c": "supplementary_table_s1c_agreed_labels",
}

TITLES = {
    "Figure 1": "Replacing a human coder with Fable 5: panel agreement and replacement differences",
    "Figure 2": "Agreement and replacement differences for all baseline records and for those whose register entry coders judged sufficient to classify",
    "Figure 3": "Label application counts: Fable 5 against the human majority",
    "Figure 4": "Kinds of disagreement between pairs of human coders and between Fable 5 and each coder",
    "Supplementary Figure S1": "Replacing a human coder with Fable 5 in a non-representative hard-case sample (diagnostic)",
    "Supplementary Figure S2": "How each coder, and the majority of coders, rated register-entry information and taxonomy fit",
    "Table 1": "Research Domains: agreement on each label between pairs of human coders and between Fable 5 and each coder",
    "Table 2": "Analytical Purposes: agreement on each label between pairs of human coders and between Fable 5 and each coder",
    "Table 3": "Research Domains: agreement on each label between Fable 5 and the coder majority",
    "Table 4": "Analytical Purposes: agreement on each label between Fable 5 and the coder majority",
    "Table 5": "Kinds of disagreement between pairs of human coders and between Fable 5 and each coder: number and percentage of disagreeing pairs",
    "Supplementary Table S1a": "Majority ratings of whether the register entry gave enough information to classify the project",
    "Supplementary Table S1b": "Majority ratings of how well the taxonomy fitted the project",
    "Supplementary Table S1c": "Number of labels agreed by at least two of three coders per record",
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def last_commit(path: Path) -> str:
    return git("log", "-1", "--format=%H", "--", path.relative_to(ROOT).as_posix())


def table_map(text: str, prefix: str) -> dict[str, dict]:
    """Parse the simple Markdown tables used by the retained reports."""
    result: dict[str, dict] = {}
    lines = text.splitlines()
    heading = re.compile(rf"^##+ ({re.escape(prefix)}\d+) — (.*)$")
    for index, line in enumerate(lines):
        match = heading.match(line)
        if not match:
            continue
        table_id, title = match.groups()
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].startswith("|"):
            cursor += 1
        if cursor + 1 >= len(lines):
            continue
        headers = [cell.strip().strip("`") for cell in lines[cursor].strip("|").split("|")]
        cursor += 2
        rows = []
        while cursor < len(lines) and lines[cursor].startswith("|"):
            cells = [cell.strip().strip("`") for cell in lines[cursor].strip("|").split("|")]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
            cursor += 1
        result[table_id] = {"heading": title, "rows": rows}
    return result


def decimal(value: str) -> Decimal:
    return Decimal(str(value))


def whole_percent(value: str) -> str:
    return str(int((decimal(value) * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def blank_row() -> dict:
    return {field: "" for field in FIELDS}


def normalise_rows(rows: list[dict], deliverable: str) -> list[dict]:
    output = []
    for original in rows:
        row = blank_row()
        row.update(original)
        row["deliverable_id"] = deliverable
        output.append(row)
    return output


def grouped(table: dict) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in table["rows"]:
        out[row["Row / comparator"]][row["Quantity"]] = row
    return out


def archive_existing(data_dir: Path) -> list[dict]:
    """Move pre-pass-2 scratch-coder data aside once, without overwriting."""
    archive = data_dir / "archive" / "pass2_preexisting_6cbf154"
    candidates = [p for p in data_dir.glob("scratch_coder_*") if p.is_file()]
    if not candidates:
        return []
    archive.mkdir(parents=True, exist_ok=True)
    moved = []
    for source in sorted(candidates):
        name = source.name
        name = name.replace("scratch_coder_figure_4_baseline_hard_case", "supplementary_figure_s1_baseline_vs_hardcase_superseded")
        name = name.replace("scratch_coder_figure_1_panel_agreement", "figure_1_panel_agreement_replacement_superseded")
        name = name.replace("scratch_coder_figure_2_sufficiency_sensitivity", "figure_2_sufficiency_sensitivity_superseded")
        name = name.replace("scratch_coder_figure_3_label_application_patterns", "figure_3_label_application_superseded")
        name = name.replace("scratch_coder_table_1_pairwise_kappa_domains", "table_1_agreement_domains_superseded")
        name = name.replace("scratch_coder_table_2_pairwise_kappa_purposes", "table_2_agreement_purposes_superseded")
        name = name.replace("scratch_coder_table_3_contingencies_performance_domains", "table_3_agreement_with_majority_domains_superseded")
        name = name.replace("scratch_coder_table_4_contingencies_performance_purposes", "table_4_agreement_with_majority_purposes_superseded")
        name = name.replace("scratch_coder_table_5_disagreeing_pair_relations", "table_5_disagreement_composition_superseded")
        name = name.replace("scratch_coder_supplementary_table_s1_majority_coverage", "supplementary_table_s1_combined_superseded")
        name = name.replace("scratch_coder_", "legacy_")
        target = archive / name
        if target.exists():
            raise RuntimeError(f"Archive target already exists: {target}")
        shutil.move(source, target)
        moved.append({"from": source.relative_to(ROOT).as_posix(), "to": target.relative_to(ROOT).as_posix()})
    return moved


def prerequisites(revision_log: Path, findings_log: Path) -> dict:
    required_files = (RESULTS, RESULTS_META, CONFIDENCE, VERIFICATION, MAJORITY, DISAGREEMENT, revision_log, findings_log)
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise RuntimeError(f"Required input missing: {missing}")
    for commit in REQUIRED_ANCESTORS:
        git("cat-file", "-e", f"{commit}^{{commit}}")
        if subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT).returncode:
            raise RuntimeError(f"Required commit is not an ancestor of HEAD: {commit}")
    retained = legacy.verify_prerequisites()
    log_info = {}
    for path in (revision_log, findings_log):
        stat = path.stat()
        log_info[path.name] = {
            "path": str(path.resolve()), "sha256": sha256(path), "size_bytes": stat.st_size,
            "last_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        }
    return {
        "run_start_head": git("rev-parse", "HEAD"),
        "required_ancestors": {commit: True for commit in REQUIRED_ANCESTORS},
        "source_commits": {
            "pipeline_code": git("rev-parse", "960c38d"),
            "canonical_data_outputs": git("rev-parse", "6cbf154"),
            "exploratory_confidence_outputs": git("rev-parse", "f36d738"),
            "verification_report": git("rev-parse", "1287716"),
            "results_last_commit": last_commit(RESULTS),
            "confidence_last_commit": last_commit(CONFIDENCE),
        },
        "sources": {
            RESULTS.relative_to(ROOT).as_posix(): {"sha256": sha256(RESULTS), "last_commit": last_commit(RESULTS)},
            RESULTS_META.relative_to(ROOT).as_posix(): {"sha256": sha256(RESULTS_META), "last_commit": last_commit(RESULTS_META)},
            CONFIDENCE.relative_to(ROOT).as_posix(): {"sha256": sha256(CONFIDENCE), "last_commit": last_commit(CONFIDENCE)},
            VERIFICATION.relative_to(ROOT).as_posix(): {"sha256": sha256(VERIFICATION), "last_commit": last_commit(VERIFICATION)},
            MAJORITY.relative_to(ROOT).as_posix(): {"sha256": sha256(MAJORITY), "last_commit": last_commit(MAJORITY)},
            DISAGREEMENT.relative_to(ROOT).as_posix(): {"sha256": sha256(DISAGREEMENT), "last_commit": last_commit(DISAGREEMENT)},
        },
        "logs": log_info,
        "retained_pipeline_prerequisites": retained,
    }


def replacement_rows(tables: dict, deliverable: str, specs: list[tuple[str, str, str, str]]) -> list[dict]:
    return normalise_rows(legacy.replacement_extract(tables, deliverable, specs), deliverable)


def table_rows(tables: dict) -> dict[str, list[dict]]:
    return {
        "Table 1": normalise_rows(legacy.table_kappa_extract(tables, "Table 1", "Research Domains", ("S5T001", "S5T005", "S5T009")), "Table 1"),
        "Table 2": normalise_rows(legacy.table_kappa_extract(tables, "Table 2", "Analytical Purposes", ("S5T002", "S5T006", "S5T010")), "Table 2"),
        "Table 3": normalise_rows(legacy.table_performance_extract(tables, "Table 3", "Research Domains", ("S5T001", "S5T003", "S5T007", "S5T009")), "Table 3"),
        "Table 4": normalise_rows(legacy.table_performance_extract(tables, "Table 4", "Analytical Purposes", ("S5T002", "S5T004", "S5T008", "S5T010")), "Table 4"),
    }


def set_row_groups(datasets: dict[str, list[dict]]) -> dict:
    mapping = {
        "STANDARD": "Applied by coder majority to 30 or more records",
        "LOW SUPPORT": "Applied by coder majority to 10–29 records: fewer records, so wider intervals; interpret with caution",
        "RARE": "Applied by coder majority to fewer than 10 records: counts only",
    }
    assignments = {}
    for deliverable in ("Table 1", "Table 2", "Table 3", "Table 4"):
        for row in datasets[deliverable]:
            if row["label"] == "Unclear from Register Entry":
                group = "Unclear from Register Entry — fewer records, so wider intervals; interpret with caution"
            else:
                group = mapping[row["support_band"]]
            row["row_group"] = group
            assignments[(deliverable, row["label"])] = {"band": row["support_band"], "group": group, "n": row["support_string"]}
    expected = {
        ("Table 2", "Policy Evaluation / Impact Analysis"): "STANDARD",
        ("Table 2", "Descriptive Monitoring"): "STANDARD",
        ("Table 2", "Outcome Tracking"): "LOW SUPPORT",
        ("Table 1", "Unclear from Register Entry"): "LOW SUPPORT",
        ("Table 2", "Unclear from Register Entry"): "LOW SUPPORT",
    }
    failures = []
    for key, band in expected.items():
        if assignments[key]["band"] != band:
            failures.append({"key": key, "expected": band, "observed": assignments[key]["band"]})
    if failures:
        raise RuntimeError(f"Exported row-group assertion failed: {failures}")
    return {"status": "PASS", "assignments": {"|".join(key): value for key, value in assignments.items()}}


def s2_rows(tables: dict, confidence_tables: dict) -> tuple[list[dict], list[dict]]:
    output: list[dict] = []
    total_checks = []
    specs = (
        ("Register-entry information", "baseline", "S8T001", "S8T003", ("Sufficient", "Partially sufficient", "Insufficient", "No majority / split judgement")),
        ("Register-entry information", "hard_case", "S8T002", "S8T004", ("Sufficient", "Partially sufficient", "Insufficient", "No majority / split judgement")),
        ("Taxonomy fit", "baseline", "S9T001", "S9T003", ("Fit", "Partial Fit", "No Fit", "Cannot assess from register entry", "No majority / split judgement")),
        ("Taxonomy fit", "hard_case", "S9T002", "S9T004", ("Fit", "Partial Fit", "No Fit", "Cannot assess from register entry", "No majority / split judgement")),
    )
    for construct, population, coder_id, majority_id, categories in specs:
        coder_group = grouped(tables[coder_id])
        majority_group = grouped(tables[majority_id])
        for actor in ("C01", "C02", "C03", "Majority of coders"):
            counts = []
            for order, category in enumerate(categories, 1):
                key = f"{actor}; {category}" if actor != "Majority of coders" else category
                source = coder_group.get(key) if actor != "Majority of coders" else majority_group.get(key)
                if not source:
                    continue
                count_row, prop_row = source["count"], source["proportion"]
                item = normalise_rows([legacy.value_row("Supplementary Figure S2", population, construct,
                    coder_id if actor != "Majority of coders" else majority_id, count_row,
                    label=category, source_order=order, series=construct, quantity="category count",
                    pair=actor, role="plotted")], "Supplementary Figure S2")[0]
                item.update({
                    "source_column_locator": "Estimate / count / flag (count and proportion rows)",
                    "interval_lower_string": prop_row["Estimate / count / flag"],
                    "parsed_interval_lower": prop_row["Estimate / count / flag"],
                    "interval_status": "N", "denominator_string": prop_row["Total / denominator / unit"],
                })
                output.append(item)
                counts.append(int(count_row["Estimate / count / flag"]))
            expected_n = 150 if population == "baseline" else 75
            total_checks.append({"panel": construct, "population": population, "bar": actor,
                                 "observed_sum": sum(counts), "denominator": expected_n,
                                 "status": "PASS" if sum(counts) == expected_n else "FAIL"})

    for population, coder_id, majority_id, alpha_id, unanimous_id in (
        ("baseline", "SCF1T001", "SCF1T002", "SCF1T003", "SCF1T004"),
        ("hard_case", "SCF1T006", "SCF1T007", "SCF1T008", "SCF1T009"),
    ):
        for actor in ("C01", "C02", "C03", "Majority of coders"):
            source_id = coder_id if actor != "Majority of coders" else majority_id
            rows = [r for r in confidence_tables[source_id]["rows"] if actor == "Majority of coders" or r.get("coder") == actor]
            counts = []
            for order, source in enumerate(rows, 1):
                item = blank_row()
                item.update({
                    "deliverable_id": "Supplementary Figure S2", "role": "plotted", "population": population,
                    "dimension": "Coder confidence", "label": source["category"], "source_order": order,
                    "series": "Coder confidence", "quantity": "category count", "pair": actor,
                    "source_file": CONFIDENCE.relative_to(ROOT).as_posix(), "source_table_id": source_id,
                    "source_section": source_id, "source_row_key": f"{actor}|{source['category']}",
                    "source_column_locator": "count; proportion; denominator", "source_value_string": source["count"],
                    "parsed_value": source["count"], "interval_lower_string": source["proportion"],
                    "parsed_interval_lower": source["proportion"], "estimate_status": "R", "interval_status": "N",
                    "original_status_string": f"{source['estimate_status']}/{source['interval_status']}",
                    "denominator_string": source["denominator"], "sample_size": source["denominator"],
                    "denominator_unit": "records",
                })
                output.append(item)
                counts.append(int(source["count"]))
            expected_n = 150 if population == "baseline" else 75
            total_checks.append({"panel": "Coder confidence", "population": population, "bar": actor,
                                 "observed_sum": sum(counts), "denominator": expected_n,
                                 "status": "PASS" if sum(counts) == expected_n else "FAIL"})
        alpha = confidence_tables[alpha_id]["rows"][0]
        alpha_row = blank_row()
        alpha_row.update({
            "deliverable_id": "Supplementary Figure S2", "role": "caption", "population": population,
            "dimension": "Coder confidence", "series": "Ordinal Krippendorff’s α", "quantity": "alpha",
            "source_file": CONFIDENCE.relative_to(ROOT).as_posix(), "source_table_id": alpha_id,
            "source_section": alpha_id, "source_row_key": "alpha", "source_column_locator": "alpha; ci_lower; ci_upper; replicate fields",
            "source_value_string": alpha["alpha"], "parsed_value": alpha["alpha"],
            "interval_lower_string": alpha["ci_lower"], "parsed_interval_lower": alpha["ci_lower"],
            "interval_upper_string": alpha["ci_upper"], "parsed_interval_upper": alpha["ci_upper"],
            "estimate_status": "R", "interval_status": "R", "confidence_level": alpha["confidence_level"],
            "denominator_string": alpha["denominator"], "sample_size": alpha["denominator"], "denominator_unit": "records",
            "presentation_note": json.dumps({key: alpha[key] for key in ("requested_replicates", "valid_replicates", "invalid_replicates")}),
        })
        output.append(alpha_row)
        unanimous = confidence_tables[unanimous_id]["rows"][0]
        unanimity_row = blank_row()
        unanimity_row.update({
            "deliverable_id": "Supplementary Figure S2", "role": "caption", "population": population,
            "dimension": "Coder confidence", "series": "Unanimity", "quantity": "count",
            "source_file": CONFIDENCE.relative_to(ROOT).as_posix(), "source_table_id": unanimous_id,
            "source_section": unanimous_id, "source_row_key": "unanimous confidence count", "source_column_locator": "count; denominator",
            "source_value_string": unanimous["count"], "parsed_value": unanimous["count"],
            "estimate_status": "R", "interval_status": "N", "denominator_string": unanimous["denominator"],
            "sample_size": unanimous["denominator"], "denominator_unit": "records",
        })
        output.append(unanimity_row)
    if any(check["status"] != "PASS" for check in total_checks):
        raise RuntimeError(f"Supplementary Figure S2 category total failed: {total_checks}")
    return output, total_checks


def supplementary_tables(tables: dict) -> tuple[dict[str, list[dict]], list[dict]]:
    source_rows = normalise_rows(legacy.supplementary_extract(tables), "Supplementary Table S1")
    a = [r for r in source_rows if r["series"] == "Part A" and r["dimension"] == "Sufficiency"]
    b = [r for r in source_rows if r["series"] == "Part A" and r["dimension"] == "Taxonomy fit"]
    for row in a:
        row["deliverable_id"] = "Supplementary Table S1a"
    for row in b:
        row["deliverable_id"] = "Supplementary Table S1b"
    totals = []
    for deliverable, rows in (("Supplementary Table S1a", a), ("Supplementary Table S1b", b)):
        counts: dict[str, list[int]] = defaultdict(list)
        denominators: dict[str, int] = {}
        for row in rows:
            if row["quantity"] == "count":
                counts[row["population"]].append(int(row["source_value_string"]))
                denominators[row["population"]] = int(row["sample_size"])
        for population in counts:
            observed = sum(counts[population])
            expected = denominators[population]
            totals.append({"deliverable": deliverable, "population": population, "observed_sum": observed,
                           "denominator": expected, "status": "PASS" if observed == expected else "FAIL"})
    if any(row["status"] != "PASS" for row in totals):
        raise RuntimeError(f"Supplementary table category total failed: {totals}")
    return {"Supplementary Table S1a": a, "Supplementary Table S1b": b}, totals


def g12_derivations(tables: dict) -> tuple[list[dict], dict]:
    with MAJORITY.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    key = {(r["population"], r["dimension"], r["quantity"], r["category"]): r for r in rows}
    report = {"status": "PASS", "derivation_1_and_2": [], "derivation_3": [], "derivation_4": []}
    output = []
    expected_rows = {
        ("baseline", "Analytical Purposes"): ([24, 26, 97, 3, 0], [16, 17, 65, 2, 0]),
        ("baseline", "Research Domains"): ([5, 13, 107, 22, 3], [3, 9, 71, 15, 2]),
        ("hard_case", "Analytical Purposes"): ([9, 20, 42, 4, 0], [12, 27, 56, 5, 0]),
        ("hard_case", "Research Domains"): ([6, 3, 45, 18, 3], [8, 4, 60, 24, 4]),
    }
    categories = ("No agreed label", "Agreed only on Unclear", "1 agreed label", "2 agreed labels", "3 agreed labels")
    for (population, dimension), (expected_counts, expected_percents) in expected_rows.items():
        denominator = 150 if population == "baseline" else 75
        size1 = int(key[(population, dimension, "majority_set_size", "size_1")]["count"])
        unclear_only = int(key[(population, dimension, "unclear_composition", "unclear_present__substantive_absent")]["count"])
        mixed = int(key[(population, dimension, "unclear_composition", "unclear_present__substantive_present")]["count"])
        if mixed != 0:
            raise RuntimeError(f"G.12 derivation 1 operand assertion failed: {population}/{dimension}/mixed={mixed}")
        derived_one = size1 - unclear_only
        raw_specs = (
            ("majority_set_size", "size_0"),
            ("unclear_composition", "unclear_present__substantive_absent"),
            ("derived", "one"),
            ("majority_set_size", "size_2"),
            ("majority_set_size", "size_3"),
        )
        counts = []
        for spec in raw_specs:
            counts.append(derived_one if spec[0] == "derived" else int(key[(population, dimension, spec[0], spec[1])]["count"]))
        percentages = [int((Decimal(count) * Decimal(100) / Decimal(denominator)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) for count in counts]
        if counts != expected_counts or percentages != expected_percents or sum(counts) != denominator or sum(percentages) != 100:
            raise RuntimeError(f"G.12 derivation 1/2 assertion failed: {population}/{dimension}: {counts}/{percentages}")
        report["derivation_1_and_2"].append({
            "population": population, "dimension": dimension, "size_1": size1, "unclear_only": unclear_only,
            "unclear_and_substantive": mixed, "one_agreed_label": derived_one, "counts": counts,
            "percentages": percentages, "count_sum": sum(counts), "percentage_sum": sum(percentages), "status": "PASS",
        })
        for order, (category, count, percent, spec) in enumerate(zip(categories, counts, percentages, raw_specs), 1):
            row = blank_row()
            if spec[0] == "derived":
                source_table = "G.12 derivation 1"
                source_key = f"size_1 {size1} minus Unclear-only {unclear_only}"
                derivation = "G12.1; G12.2"
                operands = {"size_1": size1, "unclear_only": unclear_only, "unclear_and_substantive": mixed,
                            "percentage_count": count, "records": denominator}
            else:
                source = key[(population, dimension, spec[0], spec[1])]
                source_table = "majority_coverage.csv"
                source_key = f"{population}|{dimension}|{spec[0]}|{spec[1]}"
                derivation = "G12.2"
                operands = {"source_count": int(source["count"]), "records": denominator}
            row.update({
                "deliverable_id": "Supplementary Table S1c", "role": "tabulated", "population": population,
                "dimension": dimension, "label": category, "source_order": order, "series": "agreed labels",
                "quantity": "count and whole percentage", "source_file": MAJORITY.relative_to(ROOT).as_posix(),
                "source_table_id": source_table, "source_section": "G.12", "source_row_key": source_key,
                "source_column_locator": "count; denominator; approved derivation", "source_value_string": str(count),
                "parsed_value": str(count), "interval_lower_string": str(percent), "parsed_interval_lower": str(percent),
                "estimate_status": "R", "interval_status": "N", "denominator_string": str(denominator),
                "sample_size": str(denominator), "denominator_unit": "records", "derivation_id": derivation,
                "derivation_operands": json.dumps(operands, sort_keys=True), "display_percent": str(percent),
            })
            output.append(row)

    for dimension, support_id, contingency_id, expected_model, expected_human, unclear_model, unclear_human, expected_sub_model, expected_sub_human in (
        ("Research Domains", "S5T001", "S5T003", 199, 173, 1, 13, 198, 160),
        ("Analytical Purposes", "S5T002", "S5T004", 160, 129, 1, 26, 159, 103),
    ):
        support = grouped(tables[support_id])
        contingency = grouped(tables[contingency_id])
        model_total = human_total = 0
        for label, values in support.items():
            model = int(values["baseline_model_positive_n"]["Estimate / count / flag"])
            human = int(values["baseline_human_majority_positive_n"]["Estimate / count / flag"])
            tp = int(contingency[label]["tp"]["Estimate / count / flag"])
            fp = int(contingency[label]["fp"]["Estimate / count / flag"])
            fn = int(contingency[label]["fn"]["Estimate / count / flag"])
            if model != tp + fp or human != tp + fn:
                raise RuntimeError(f"G.12 derivation 3 label identity failed: {dimension}/{label}")
            model_total += model
            human_total += human
        unclear = support["Unclear from Register Entry"]
        observed_unclear_model = int(unclear["baseline_model_positive_n"]["Estimate / count / flag"])
        observed_unclear_human = int(unclear["baseline_human_majority_positive_n"]["Estimate / count / flag"])
        substantive_model = model_total - observed_unclear_model
        substantive_human = human_total - observed_unclear_human
        if (model_total, human_total) != (expected_model, expected_human):
            raise RuntimeError(f"G.12 derivation 3 total assertion failed: {dimension}")
        if (observed_unclear_model, observed_unclear_human, substantive_model, substantive_human) != (unclear_model, unclear_human, expected_sub_model, expected_sub_human):
            raise RuntimeError(f"G.12 derivation 4 assertion failed: {dimension}")
        report["derivation_3"].append({"dimension": dimension, "model_total": model_total, "coder_majority_total": human_total, "status": "PASS"})
        report["derivation_4"].append({"dimension": dimension, "model_total": model_total, "coder_majority_total": human_total,
            "unclear_model": observed_unclear_model, "unclear_coder_majority": observed_unclear_human,
            "substantive_model": substantive_model, "substantive_coder_majority": substantive_human, "status": "PASS"})
    return output, report


def disagreement_rows() -> tuple[list[dict], dict]:
    rows = normalise_rows(legacy.table5_extract(), "Table 5")
    selected = [r for r in rows if r["dimension"] in {"Research Domains", "Analytical Purposes"}]
    relevant = [r for r in selected if r["quantity"] in {"containment", "overlap", "disjoint", "both_empty", "exactly_one_empty"}]
    grouped_rows: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in relevant:
        grouped_rows[(row["dimension"], row["series"])][row["quantity"]] = row
    checks = []
    for (dimension, family), relations in grouped_rows.items():
        percentages = []
        for relation in ("containment", "overlap", "disjoint"):
            row = relations[relation]
            pct = whole_percent(row["interval_lower_string"])
            row["display_percent"] = pct
            percentages.append(int(pct))
        empty = int(relations["both_empty"]["source_value_string"]) + int(relations["exactly_one_empty"]["source_value_string"])
        check = {"dimension": dimension, "pair_family": family, "displayed_percentages": percentages,
                 "displayed_sum": sum(percentages), "empty_set_involved": empty,
                 "status": "PASS" if sum(percentages) == 100 and empty == 0 else "FAIL"}
        checks.append(check)
    if any(check["status"] != "PASS" for check in checks):
        raise RuntimeError(f"Disagreement display assertion failed: {checks}")
    plotted = []
    tabulated = []
    for row in relevant:
        figure_row = row.copy(); figure_row["deliverable_id"] = "Figure 4"; figure_row["role"] = "plotted"; plotted.append(figure_row)
        table_row = row.copy(); table_row["deliverable_id"] = "Table 5"; table_row["role"] = "tabulated"; tabulated.append(table_row)
    return plotted + tabulated, {"status": "PASS", "rows": checks}


def numeric_inventory(rows: list[dict]) -> dict[tuple[str, ...], set[str]]:
    inventory: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for row in rows:
        base_key = (row.get("source_table_id", ""), row.get("population", ""), row.get("dimension", ""),
                    row.get("label", ""), row.get("pair", ""), row.get("quantity", ""), row.get("source_row_key", ""))
        for field in ("source_value_string", "interval_lower_string", "interval_upper_string", "denominator_string", "sample_size", "support_string"):
            value = row.get(field, "")
            match = re.match(r"^[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?$", str(value).strip())
            if match:
                inventory[base_key + (field,)].add(str(value).strip())
    return inventory


def legacy_rows() -> list[dict]:
    paths = git("ls-tree", "-r", "--name-only", LEGACY_COMMIT, "--", "analysis/figure_data").splitlines()
    paths = [p for p in paths if p.endswith(".csv") and Path(p).name.startswith("scratch_coder_")]
    output = []
    for path in paths:
        raw = subprocess.run(["git", "show", f"{LEGACY_COMMIT}:{path}"], cwd=ROOT, check=True, text=True, capture_output=True).stdout
        try:
            output.extend(csv.DictReader(io.StringIO(raw)))
        except csv.Error:
            continue
    return output


def carryover_check(new_rows: list[dict]) -> dict:
    old = numeric_inventory(legacy_rows())
    new = numeric_inventory(new_rows)
    matched = sorted(set(old) & set(new))
    changes = []
    identical = 0
    for key in matched:
        old_values, new_values = old[key], new[key]
        if len(old_values) != 1 or len(new_values) != 1:
            if old_values != new_values:
                changes.append({"key": key, "old": sorted(old_values), "new": sorted(new_values), "reason": "non-unique semantic key"})
            else:
                identical += 1
            continue
        old_value, new_value = next(iter(old_values)), next(iter(new_values))
        if decimal(old_value) == decimal(new_value):
            identical += 1
        else:
            changes.append({"key": key, "old": old_value, "new": new_value})
    if changes:
        raise RuntimeError(f"Carried-over values changed: {changes[:10]}")
    return {
        "status": "PASS", "matched": len(matched), "identical": identical,
        "approved_corrections": 0, "changes": changes,
        "unmatched_legacy": len(set(old) - set(new)), "new_without_legacy_counterpart": len(set(new) - set(old)),
        "unmatched_legacy_keys": [list(key) for key in sorted(set(old) - set(new))],
        "new_keys": [list(key) for key in sorted(set(new) - set(old))],
    }


def trace_check(rows: list[dict]) -> dict:
    failures = []
    for index, row in enumerate(rows, 1):
        numeric_fields = [row.get(field, "") for field in ("source_value_string", "interval_lower_string", "interval_upper_string")]
        if not any(re.match(r"^[-+]?\d", str(value)) for value in numeric_fields if value != ""):
            continue
        source_ok = bool(row.get("source_file") and row.get("source_table_id") and row.get("source_row_key") and row.get("source_column_locator"))
        derivation_ok = bool(row.get("derivation_id") and row.get("derivation_operands"))
        if not source_ok and not derivation_ok:
            failures.append({"row": index, "deliverable": row.get("deliverable_id"), "quantity": row.get("quantity")})
    if failures:
        raise RuntimeError(f"Untraced numeric values: {failures[:10]}")
    return {"status": "PASS", "numeric_rows_checked": len(rows), "failures": []}


def caption_bullets(datasets: dict[str, list[dict]], derivations: dict) -> dict[str, list[str]]:
    def find(deliverable: str, table: str, quantity: str, population: str = "") -> dict:
        return next(r for r in datasets[deliverable] if r["source_table_id"] == table and r["quantity"] == quantity and (not population or r["population"] == population))
    f1_equity_b = find("Figure 1", "S2T001", "delta_B")
    f1_equity_min = find("Figure 1", "S2T001", "delta_min")
    f1_covid_a = find("Figure 1", "S2T002", "delta_A")
    f1_covid_min = find("Figure 1", "S2T002", "delta_min")
    f2_purpose_min = find("Figure 2", "S3T002", "delta_min", "baseline")
    f2_domain_min = find("Figure 2", "S3T011", "delta_min", "baseline_strict_sufficient")
    s1_equity = find("Supplementary Figure S1", "S2T007", "delta_min", "hard_case")
    s1_covid_c = find("Supplementary Figure S1", "S2T008", "delta_C", "hard_case")
    s1_covid_min = find("Supplementary Figure S1", "S2T008", "delta_min", "hard_case")
    s2_alpha = {r["population"]: r for r in datasets["Supplementary Figure S2"] if r["quantity"] == "alpha"}
    s2_unanimous = {r["population"]: r for r in datasets["Supplementary Figure S2"] if r["series"] == "Unanimity"}
    totals = {r["dimension"]: r for r in derivations["derivation_3"]}
    substantive = {r["dimension"]: r for r in derivations["derivation_4"]}
    common_pair = "Each record contributes three human pairs and three Fable 5–coder pairs; only different, non-empty sets are counted, and pairs from one record are not independent [disagreement export, eligible_records and nonidentical_nonempty_pairs cells]."
    return {
        "Figure 1": [
            "Baseline n=150 records in every panel; tag counts are equity 11 and COVID-19 12 records applied by the coder majority [S2T001/S2T002, denominator and label-count cells; displayed 11 and 12].",
            "ABC is C01/C02/C03; LBC, ALC and ABL replace C01, C02 and C03 respectively with Fable 5; each δ is the substituted-panel α minus ABC [S2T001, S2T002, S3T001, S3T002 row cells].",
            f"For equity, δᵦ upper={f1_equity_b['interval_upper_string']} (display +0.004) crosses zero; δₘᵢₙ upper={f1_equity_min['interval_upper_string']} (display −0.006) does not [S2T001 interval-upper cells].",
            f"COVID-19 δₐ interval=[{f1_covid_a['interval_lower_string']}, {f1_covid_a['interval_upper_string']}] and δₘᵢₙ interval=[{f1_covid_min['interval_lower_string']}, {f1_covid_min['interval_upper_string']}] (each displayed [0.000, 0.000]); both have zero width [S2T002 interval cells].",
            "The δₘᵢₙ point estimate matches δᵦ for domains, purposes and equity, and δₐ for COVID-19; δₘᵢₙ is selected within each resample, so its interval can differ from that component’s interval [S3T001, S3T002, S2T001, S2T002 δ cells].",
        ],
        "Figure 2": [
            "Baseline n=150 and strict register-sufficient n=92; the two populations are nested [S3T001/S3T002 and S3T011/S3T012 denominator cells; displayed 150 and 92].",
            "The δₘᵢₙ point estimate matches δᵦ in both dimensions and both populations; it is selected within each resample, so intervals can differ [S3T001, S3T002, S3T011, S3T012 δ cells].",
            f"Baseline purposes δₘᵢₙ upper={f2_purpose_min['interval_upper_string']} (display −0.002) and strict domains δₘᵢₙ lower={f2_domain_min['interval_lower_string']} (display +0.001); both intervals exclude zero [S3T002/S3T011 interval cells].",
            "The α axis is 0.15–0.75, rather than the 0–1 scale used in Figure 1 and Supplementary Figure S1 [S3T001, S3T002, S3T011, S3T012 interval cells].",
        ],
        "Figure 3": [
            f"Across all labels, Fable 5 made {totals['Research Domains']['model_total']} domain and {totals['Analytical Purposes']['model_total']} purpose applications; the coder majority made {totals['Research Domains']['coder_majority_total']} and {totals['Analytical Purposes']['coder_majority_total']} (display unchanged) [S5T001/S5T002, summed label-count cells; G.12 derivation 3].",
            "Counts across labels are label applications rather than records; each point is one label [S5T001/S5T002 label-count cells].",
            "Vertical lines at 10 and 30 records show the preregistered count thresholds; labels below 10 remain plotted as counts [S5T001/S5T002 exported band cells].",
            "The outlined point is Unclear from Register Entry: domains (13, 1) and purposes (26, 1), displayed as integer counts [S5T001/S5T002 coder-majority-positive and model-positive cells].",
        ],
        "Figure 4": [
            "Displayed shares are containment/overlap/disjoint: domains human pairs 48%/5%/47% (n=220), domains Fable 5 pairs 52%/8%/40% (n=199), purposes human pairs 14%/<1%/86% (n=272), purposes Fable 5 pairs 15%/1%/84% (n=270) [disagreement_type_distribution.csv full-precision proportion and count cells].",
            "Containment means one set is inside the other; overlap means a shared label plus labels unique to each; disjoint means no shared label [disagreement export relation cells].",
            common_pair,
            "Unclear from Register Entry counts as a label; the export does not separate decline-versus-classify pairs from other disjoint pairs [disagreement export relation definition].",
            "The display describes kinds of disagreement rather than disagreement frequency or seriousness [disagreement export conditioning cells].",
        ],
        "Supplementary Figure S1": [
            "Baseline n=150 and hard-case n=75; hard-case is diagnostic and non-representative [S2T001/S2T002/S3T001/S3T002 and S2T007/S2T008/S3T007/S3T008 denominator cells].",
            "Applied by coder majority: baseline equity 11 and COVID-19 12; hard-case equity 8 and COVID-19 6 (display unchanged) [S2T001/S2T002 context and S2T017/S2T018 count cells].",
            "δₘᵢₙ matches baseline→hard-case components as follows: domains δᵦ→δ꜀; purposes δᵦ→δᵦ; equity δᵦ→δₐ; COVID-19 δₐ→δ꜀ [replacement tables’ point-estimate cells].",
            f"Hard-case equity δₘᵢₙ={s1_equity['source_value_string']} [{s1_equity['interval_lower_string']}, {s1_equity['interval_upper_string']}] (display −0.115 [−0.330, 0.000]); the interval reaches zero [S2T007 δₘᵢₙ cells].",
            f"Hard-case COVID-19 δ꜀ interval=[{s1_covid_c['interval_lower_string']}, {s1_covid_c['interval_upper_string']}] and δₘᵢₙ interval=[{s1_covid_min['interval_lower_string']}, {s1_covid_min['interval_upper_string']}] (each displayed [0.000, 0.000]); both have zero width [S2T008 interval cells].",
        ],
        "Supplementary Figure S2": [
            "Baseline n=150 and hard-case n=75; hard-case panels are diagnostic and non-representative [S8T001–S8T004, S9T001–S9T004 and SCF1T001–SCF1T009 denominator cells].",
            "The confidence row is exploratory and not preregistered [SCF1T001 onwards].",
            f"Ordinal Krippendorff’s α for confidence is baseline {s2_alpha['baseline']['source_value_string']} [{s2_alpha['baseline']['interval_lower_string']}, {s2_alpha['baseline']['interval_upper_string']}] and hard-case {s2_alpha['hard_case']['source_value_string']} [{s2_alpha['hard_case']['interval_lower_string']}, {s2_alpha['hard_case']['interval_upper_string']}] (display 0.18 [0.08, 0.28] and 0.11 [−0.05, 0.25]); valid/invalid/requested resamples are 2000/0/2000 for each [SCF1T003/SCF1T008].",
            f"Unanimous confidence ratings: baseline {s2_unanimous['baseline']['source_value_string']}/{s2_unanimous['baseline']['denominator_string']} and hard-case {s2_unanimous['hard_case']['source_value_string']}/{s2_unanimous['hard_case']['denominator_string']} (display unchanged) [SCF1T004/SCF1T009].",
            "Supplementary Tables S1a–S1b give the exact register-information and taxonomy-fit values [S8T001–S8T004 and S9T001–S9T004].",
        ],
        "Table 1": [
            "Labels applied by the coder majority to at least 10 baseline records are shown; six labels below 10 are omitted here and retained as counts in Table 3: Migration & Demographics 9, Crime & Justice 4, Environment & Agriculture 4, Public Finance & Taxation 2, Data Infrastructure & Methodology 0, Housing & Planning 0 [S5T001 count and band cells].",
            "Cells are Cohen’s κ with 95% percentile-bootstrap intervals; pair columns share records and coders and are not independent [S5T005 status and interval cells].",
            "For Unclear from Register Entry, human-pair κ spans 0.150–0.322 and Fable 5–coder κ spans 0.037–0.241 (display 0.15–0.32 and 0.04–0.24); Fable 5 applied the label to 1 record [S5T005 and S5T001 cells].",
            "Unclear C01–C02 lower=−0.03775091928386179 (display −0.04); Fable 5–C03 lower=−3.142158243798238e-16 (display 0.00) [S5T005 interval-lower cells].",
        ],
        "Table 2": [
            "Labels applied by the coder majority to at least 10 baseline records are shown; four labels below 10 are omitted here and retained as counts in Table 4: Life-Course / Trajectory Analysis 9, Methodological / Infrastructure Research 7, Risk Prediction / Early Identification 1, Service Interaction / Systems Analysis 1 [S5T002 count and band cells].",
            "Cells are Cohen’s κ with 95% percentile-bootstrap intervals; pair columns share records and coders and are not independent [S5T006 status and interval cells].",
            "Outcome Tracking C01–C03 lower=−0.06775275757843611 (display −0.07) and C02–C03 lower=−0.0381591707542619 (display −0.04) [S5T006 interval-lower cells].",
            "All three Fable 5–coder lower bounds for Unclear are exactly 0 (display 0.00); the coder majority applied Unclear to 26 records and Fable 5 to 1 [S5T006/S5T002 cells].",
        ],
        "Table 3": [
            "Precision, recall and F1 are shown only for labels applied by the coder majority to at least 10 records; labels below 10 retain counts only [S5T001/S5T003/S5T007/S5T009 cells].",
            "Each label is assessed separately, using the coder majority as the reference rather than an adjudicated truth set [S5T003/S5T007 cells].",
            "For Unclear, Fable 5 applied the label to 1 of 13 coder-majority-positive records; precision and F1 are not estimable with an interval, while recall is 0.07692307692307693 [0.0, 0.25] (display 0.08 [0.00, 0.25]) [S5T003/S5T007/S5T009 cells].",
            f"Total applications are Fable 5 {totals['Research Domains']['model_total']} and coder majority {totals['Research Domains']['coder_majority_total']}; substantive-only totals are {substantive['Research Domains']['substantive_model']} and {substantive['Research Domains']['substantive_coder_majority']} (display unchanged) [S5T001 summed cells; G.12 derivations 3–4].",
        ],
        "Table 4": [
            "Precision, recall and F1 are shown only for labels applied by the coder majority to at least 10 records; labels below 10 retain counts only [S5T002/S5T004/S5T008/S5T010 cells].",
            "Each label is assessed separately, using the coder majority as the reference rather than an adjudicated truth set [S5T004/S5T008 cells].",
            "For Unclear, Fable 5 applied the label to 1 of 26 coder-majority-positive records; precision and F1 are not estimable with an interval, while recall is 0.038461538461538464 [0.0, 0.125] (display 0.04 [0.00, 0.13]) [S5T004/S5T008/S5T010 cells].",
            f"Total applications are Fable 5 {totals['Analytical Purposes']['model_total']} and coder majority {totals['Analytical Purposes']['coder_majority_total']}; substantive-only totals are {substantive['Analytical Purposes']['substantive_model']} and {substantive['Analytical Purposes']['substantive_coder_majority']} (display unchanged) [S5T002 summed cells; G.12 derivations 3–4].",
        ],
        "Table 5": [
            "Cells give n and whole percentages: domains human pairs 105/11/104 of 220 (48%/5%/47%); domains Fable 5 pairs 103/16/80 of 199 (52%/8%/40%); purposes human pairs 38/1/233 of 272 (14%/<1%/86%); purposes Fable 5 pairs 40/4/226 of 270 (15%/1%/84%) [disagreement_type_distribution.csv count and full-precision proportion cells].",
            common_pair,
            "No disagreeing domain or purpose pair involved an empty label set; Unclear from Register Entry counts as a label [disagreement export both-empty and exactly-one-empty cells, all 0].",
            "Unclear from Register Entry is counted as a label, and decline-versus-classify pairs are not separated from other disjoint pairs [disagreement export relation definition].",
        ],
        "Supplementary Table S1a": [
            "A majority rating is the category chosen by at least two of three coders; if all three differ, the result is No majority [S8T003/S8T004 category cells].",
            "Hard-case percentages have no intervals because the sample is non-random [S8T004 interval-status cells].",
            "Strict n=92 equals the Sufficient majority count; broad n=148 pools Sufficient and Partially sufficient before counting coders and therefore differs from 92+55=147 [S8T003/S8T005 cells].",
            "Exact coder distributions are shown in Supplementary Figure S2 [S8T001–S8T004 cells].",
        ],
        "Supplementary Table S1b": [
            "A majority rating is the category chosen by at least two of three coders; if all three differ, the result is No majority [S9T003/S9T004 category cells].",
            "Hard-case percentages have no intervals because the sample is non-random [S9T004 interval-status cells].",
            "Exact coder distributions are shown in Supplementary Figure S2 [S9T001–S9T004 cells].",
        ],
        "Supplementary Table S1c": [
            "Each label is assessed separately and is agreed when at least two coders applied it, so a record can have none, one or several agreed labels [majority_coverage.csv count cells].",
            "‘1 agreed label’ excludes records agreed only on Unclear; counts and whole percentages are approved derivations from exported operands [majority_coverage.csv and G.12 derivations 1–2].",
            "No record combined agreed Unclear with a substantive label; no record had more than three agreed labels; no record had more than two agreed purposes (baseline 0/150, hard-case 0/75) [majority_coverage.csv zero and constraint cells].",
            "Hard-case percentages have no intervals because the sample is non-random [majority_coverage.csv population cells].",
        ],
    }


def write_dataset(data_dir: Path, deliverable: str, rows: list[dict], provenance: dict) -> dict:
    stem = SLUGS[deliverable]
    csv_path = data_dir / f"{stem}.csv"
    metadata_path = data_dir / f"{stem}_metadata.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(rows)
    metadata = {
        "deliverable_id": deliverable, "slug": stem, "data_file": csv_path.name,
        "source_files": sorted({row["source_file"] for row in rows if row["source_file"]}),
        "source_table_ids": sorted({row["source_table_id"] for row in rows if row["source_table_id"]}),
        "source_hashes": provenance["sources"], "row_count": len(rows),
        "all_numeric_values_traced": True,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"data": csv_path.name, "metadata": metadata_path.name}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "analysis/figure_data")
    parser.add_argument("--revision-log", type=Path, default=DEFAULT_REVISION_LOG)
    parser.add_argument("--findings-log", type=Path, default=DEFAULT_FINDINGS_LOG)
    parser.add_argument("--archive-existing", action="store_true")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve(); data_dir.mkdir(parents=True, exist_ok=True)
    provenance = prerequisites(args.revision_log, args.findings_log)
    archived = archive_existing(data_dir) if args.archive_existing else []

    source_hashes_before = {path: sha256(path) for path in (RESULTS, RESULTS_META, CONFIDENCE, VERIFICATION, MAJORITY, DISAGREEMENT, args.revision_log, args.findings_log)}
    tables = legacy.parse_markdown_tables(RESULTS.read_text(encoding="utf-8"))
    confidence_tables = table_map(CONFIDENCE.read_text(encoding="utf-8"), "SCF1T")

    datasets: dict[str, list[dict]] = {}
    datasets["Figure 1"] = replacement_rows(tables, "Figure 1", [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S2T001", "baseline", "Demographic disparities / equity", "plotted"), ("S2T002", "baseline", "COVID-19 & Pandemic", "plotted")])
    datasets["Figure 2"] = replacement_rows(tables, "Figure 2", [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S3T011", "baseline_strict_sufficient", "Research Domains", "plotted"), ("S3T012", "baseline_strict_sufficient", "Analytical Purposes", "plotted")])
    datasets["Figure 3"] = normalise_rows(legacy.figure3_extract(tables), "Figure 3")
    datasets["Supplementary Figure S1"] = replacement_rows(tables, "Supplementary Figure S1", [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S2T001", "baseline", "Demographic disparities / equity", "plotted"), ("S2T002", "baseline", "COVID-19 & Pandemic", "plotted"),
        ("S3T007", "hard_case", "Research Domains", "plotted"), ("S3T008", "hard_case", "Analytical Purposes", "plotted"),
        ("S2T007", "hard_case", "Demographic disparities / equity", "plotted"), ("S2T008", "hard_case", "COVID-19 & Pandemic", "plotted")])
    datasets.update(table_rows(tables))
    row_groups = set_row_groups(datasets)
    s2, s2_totals = s2_rows(tables, confidence_tables); datasets["Supplementary Figure S2"] = s2
    supplementary, supplementary_totals = supplementary_tables(tables); datasets.update(supplementary)
    s1c, derivations = g12_derivations(tables); datasets["Supplementary Table S1c"] = s1c
    disagreement, disagreement_checks = disagreement_rows()
    datasets["Figure 4"] = [r for r in disagreement if r["deliverable_id"] == "Figure 4"]
    datasets["Table 5"] = [r for r in disagreement if r["deliverable_id"] == "Table 5"]

    all_rows = [row for rows in datasets.values() for row in rows]
    tracing = trace_check(all_rows)
    carryover = carryover_check(all_rows)
    bullets = caption_bullets(datasets, derivations)
    if set(datasets) != set(SLUGS) or set(bullets) != set(SLUGS):
        raise RuntimeError(f"Deliverable coverage mismatch: data={set(SLUGS)-set(datasets)}, captions={set(SLUGS)-set(bullets)}")

    entries = {}
    for deliverable in SLUGS:
        inputs = write_dataset(data_dir, deliverable, datasets[deliverable], provenance)
        is_figure = "Figure" in deliverable
        outputs = ([f"analysis/figures/{SLUGS[deliverable]}.svg", f"analysis/figures/{SLUGS[deliverable]}.png"] if is_figure else
                   [f"analysis/tables/{SLUGS[deliverable]}.csv", f"analysis/tables/{SLUGS[deliverable]}.md"])
        entries[deliverable] = {"slug": SLUGS[deliverable], "title": TITLES[deliverable],
                                "inputs": inputs, "outputs": outputs, "caption_bullets": bullets[deliverable]}

    inventory_nonpass = []
    if INVENTORY.exists():
        with INVENTORY.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                if row.get("status") not in {"PASS", "PASS (APPROXIMATE)"}:
                    inventory_nonpass.append({"claim_id": row.get("claim_id"), "section": row.get("section_number"),
                                              "status": row.get("status"), "quantity": row.get("quantity_label")})
    manifest = {
        "manifest_version": 2, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "workflow": {"stage_1": "aggregate-source extraction and four authorised derivations",
                     "stage_2": "isolated rendering from this manifest and listed figure-data files only"},
        "provenance": provenance, "archived_figure_data": archived,
        "assertions": {
            "carried_over_values": carryover, "new_values_traced": tracing, "g12_derivations": derivations,
            "category_totals": {"supplementary_figure_s2": s2_totals, "supplementary_tables": supplementary_totals},
            "disagreement_percentages": disagreement_checks, "row_groups": row_groups,
            "approved_numeric_corrections": [], "log_quote_source_differences": [],
            "inventory_nonpass_outside_specification": inventory_nonpass,
        },
        "axis_ranges": {"alpha_figure_1_and_s1": [0.0, 1.0], "delta_all": [-0.45, 0.45], "alpha_figure_2": [0.15, 0.75], "figure_3": [0, 60]},
        "entries": entries,
    }
    (data_dir / "pass2_deliverable_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run_metadata = {
        "run_timestamp_utc": manifest["generated_utc"], "head_at_run_start": provenance["run_start_head"],
        "code_commits": {"extractor": last_commit(Path(__file__)), "renderer": last_commit(ROOT / "analysis/visualisations/render_scratch_coder_pass2.py"),
                         "runner": last_commit(ROOT / "analysis/visualisations/run_scratch_coder_pass2.py")},
        "source_commits": provenance["source_commits"], "logs": provenance["logs"],
        "software": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform()},
        "assertions": manifest["assertions"],
    }
    (data_dir / "pass2_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    source_hashes_after = {path: sha256(path) for path in source_hashes_before}
    if source_hashes_before != source_hashes_after:
        raise RuntimeError("A read-only source changed during Stage 1.")


if __name__ == "__main__":
    main()
