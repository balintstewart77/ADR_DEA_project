"""Aggregate bookkeeping for labelwise human-majority set coverage.

This driver deliberately retains record identifiers and individual coder values
only in memory.  Its outputs are aggregate counts and label-level comparison
counts; it never writes identifiers, responses, or record-level label sets.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Drivers stored in timestamped output directories need the repository root on
# sys.path when invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis.scratch_coder_stage_a.panels import dimension_panels
from analysis.scratch_coder_stage_b.performance import labels, vectors
from analysis.scratch_coder_stage_b.support import build_stage_b_data


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESULTS = ROOT / "analysis" / "scratch_coder_results" / "results.md"
INPUTS = {
    "POST-028": (ROOT / "preregistration_restricted/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv", "29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d"),
    "POST-009": (ROOT / "preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv", "0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11"),
    "POST-011": (ROOT / "preregistration_restricted/sampling/official_draw_20260724/hard_active.csv", "582f248d39d911275e4e4f11bc34660b51809a1ed7c330644f9e2036299cfb11"),
    "POST-019": (ROOT / "preregistration_restricted/sampling/official_draw_20260724/formal_assignment_crosswalk.csv", "96daddae15848331f7bef486a6c630e00de598ddb91f5ce317457e09a8bdd666"),
}
DIMENSIONS = ("Research Domains", "Analytical Purposes")
UNL = "Unclear from Register Entry"
CSV_FIELDS = ("population", "dimension", "quantity", "category", "count", "denominator", "note")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs() -> dict[str, dict[str, str | bool]]:
    checks = {}
    for artifact, (path, expected) in INPUTS.items():
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError(f"STOP: {artifact} hash mismatch ({observed}, expected {expected})")
        checks[artifact] = {"path": path.relative_to(ROOT).as_posix(), "expected_sha256": expected, "observed_sha256": observed, "matched": True}
    return checks


def markdown_table(table_id: str) -> list[dict[str, str]]:
    lines = RESULTS.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"### {table_id} —"))
    cursor = start + 1
    while not lines[cursor].startswith("|"):
        cursor += 1
    headers = [cell.strip().strip("`") for cell in lines[cursor].strip("|").split("|")]
    cursor += 2
    rows = []
    while cursor < len(lines) and lines[cursor].startswith("|"):
        values = [cell.strip().strip("`") for cell in lines[cursor].strip("|").split("|")]
        rows.append(dict(zip(headers, values, strict=True)))
        cursor += 1
    return rows


def exported_baseline_support() -> dict[tuple[str, str], int]:
    values = {}
    for table_id, dimension in (("S5T001", "Research Domains"), ("S5T002", "Analytical Purposes")):
        for row in markdown_table(table_id):
            if row["Quantity"] == "baseline_human_majority_positive_n":
                values[(dimension, row["Row / comparator"])] = int(row["Estimate / count / flag"])
    if not values:
        raise RuntimeError("STOP: no S5T001/S5T002 baseline support values found")
    return values


def aggregate_population(data, population: str, record_ids, output_rows: list[dict[str, object]]):
    """Recover the replacement complete-case mask then use vectors() for majority."""
    exclusion_summary = {}
    reconciliation = {}
    for dimension in DIMENSIONS:
        panels = dimension_panels(data, record_ids, dimension)
        missing_panel = len(record_ids) - len(panels)
        incomplete_human = sum(any(value is None for value in (panel.coder_a, panel.coder_b, panel.coder_c)) for panel in panels)
        missing_model = sum(
            not any(value is None for value in (panel.coder_a, panel.coder_b, panel.coder_c)) and panel.model is None
            for panel in panels
        )
        complete = [panel for panel in panels if None not in (panel.coder_a, panel.coder_b, panel.coder_c, panel.model)]
        denominator = len(complete)
        if denominator + missing_panel + incomplete_human + missing_model != len(record_ids):
            raise RuntimeError("Exclusion accounting is not mutually exclusive")
        exclusions = {
            "missing_formal_record_panel": missing_panel,
            "incomplete_or_missing_dimension_response": incomplete_human,
            "missing_model_classification": missing_model,
        }
        exclusion_summary[(population, dimension)] = exclusions
        for category, count in exclusions.items():
            output_rows.append({"population": population, "dimension": dimension, "quantity": "exclusion", "category": category, "count": count, "denominator": len(record_ids), "note": "Replacement-panel complete-case mask reconstruction."})

        # Existing Stage B vectors() receives its usual 3-human-plus-model tuple.
        blocks = [{dimension: (panel.coder_a, panel.coder_b, panel.coder_c, panel.model)} for panel in complete]
        majority_sets = [set() for _ in blocks]
        per_label = {}
        for label in labels()[dimension]:
            _, majority, _ = vectors(blocks, dimension, label)
            per_label[label] = int(majority.sum())
            for index in np.flatnonzero(majority):
                majority_sets[int(index)].add(label)
        sizes = Counter(len(label_set) for label_set in majority_sets)
        categories = {"size_0": 0, "size_1": 0, "size_2": 0, "size_3": 0, "size_4_plus": 0}
        for size, count in sizes.items():
            categories["size_4_plus" if size >= 4 else f"size_{size}"] += count
        if sum(categories.values()) != denominator:
            raise RuntimeError("Majority size distribution does not reconcile")
        for category, count in categories.items():
            output_rows.append({"population": population, "dimension": dimension, "quantity": "majority_set_size", "category": category, "count": count, "denominator": denominator, "note": "Labelwise majority set size."})
        output_rows.append({"population": population, "dimension": dimension, "quantity": "no_majority_label", "category": "size_0", "count": categories["size_0"], "denominator": denominator, "note": "No label reached the existing two-of-three rule."})

        composition = Counter()
        for label_set in majority_sets:
            unclear = UNL in label_set
            substantive = bool(label_set - {UNL})
            composition[(unclear, substantive)] += 1
        composition_categories = {
            "unclear_absent__substantive_absent": composition[(False, False)],
            "unclear_absent__substantive_present": composition[(False, True)],
            "unclear_present__substantive_absent": composition[(True, False)],
            "unclear_present__substantive_present": composition[(True, True)],
        }
        if sum(composition_categories.values()) != denominator:
            raise RuntimeError("Unclear composition cross-tab does not reconcile")
        for category, count in composition_categories.items():
            output_rows.append({"population": population, "dimension": dimension, "quantity": "unclear_composition", "category": category, "count": count, "denominator": denominator, "note": "Descriptive set-membership cross-tab; no interpretation is inferred."})

        violations = None
        if dimension == "Analytical Purposes":
            violations = sum(size > 2 for size in sizes for _ in range(sizes[size]))
            output_rows.append({"population": population, "dimension": dimension, "quantity": "majority_set_exceeds_single_coder_constraint", "category": "size_greater_than_2", "count": violations, "denominator": denominator, "note": "Single-coder constraint: at most two Analytical Purposes."})
        reconciliation[(population, dimension)] = {"per_label": per_label, "denominator": denominator, "size": categories, "composition": composition_categories, "violations": violations}
    return reconciliation, exclusion_summary


def write_csv(rows):
    with (OUT / "majority_coverage.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def table(lines, headers, rows):
    lines.extend(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)


def write_summary(reconciliation, exclusions, exported):
    lines = [
        "# Per-record labelwise-majority coverage and composition",
        "",
        "Descriptive bookkeeping over the existing labelwise majority rule. These aggregate counts do not make an accuracy, reliability, quality, coherence, or record-level-adjudication claim.",
        "",
        "## Rule and cohort",
        "",
        "The reused implementation is `analysis/scratch_coder_stage_b/performance.py`, function `vectors(b, dim, label)`. For each label it forms the three-human membership vector and returns `(humans.sum(1) >= 2)` as the labelwise majority reference. No majority rule was added or modified.",
        "",
        "The mask was reconstructed, not recovered from a stored record-level artefact: `analysis.scratch_coder_stage_a.panels.dimension_panels()` rebuilt the formal C01/C02/C03 record panels from the hash-verified POST-028/POST-009/POST-011/POST-019 inputs. A record entered a dimension/population denominator only when all three complete human values and the frozen model value were present, matching the replacement-panel complete-case condition. Formal responses require `validation_included=1`.",
        "",
        "Analytical Purposes has a single-coder constraint of at most two labels, documented in `analysis/scratch_coder_stage_a/mappings.py` (`sc_purposes___1..8`: ‘At most two; Unclear mutually exclusive’). The labelwise majority itself is not capped. No cardinality constraint is documented in that mapping for Research Domains, so no Domain violation count is reported.",
    ]
    for population in ("baseline", "hard_case"):
        label = "Baseline" if population == "baseline" else "Hard-case — DIAGNOSTIC — non-representative"
        lines.extend(["", f"## {label}", ""])
        for dimension in DIMENSIONS:
            result = reconciliation[(population, dimension)]
            lines.extend([f"### {dimension}", "", "Majority-set size distribution:", ""])
            table(lines, ["Size", "Count", "Denominator"], [(key.replace("size_", "").replace("_plus", "+"), value, result["denominator"]) for key, value in result["size"].items()])
            lines.extend(["", f"No majority label: **{result['size']['size_0']} / {result['denominator']}**.", "", "Unclear composition (descriptive only):", ""])
            table(lines, ["Unclear", "At least one substantive label", "Count", "Denominator"], [
                ("absent", "absent", result["composition"]["unclear_absent__substantive_absent"], result["denominator"]),
                ("absent", "present", result["composition"]["unclear_absent__substantive_present"], result["denominator"]),
                ("present", "absent", result["composition"]["unclear_present__substantive_absent"], result["denominator"]),
                ("present", "present", result["composition"]["unclear_present__substantive_present"], result["denominator"]),
            ])
            if dimension == "Analytical Purposes":
                lines.extend(["", f"Majority sets exceeding the single-coder limit of two: **{result['violations']} / {result['denominator']}**."])
        lines.extend(["", "### Aggregate exclusions by reason", ""])
        table(lines, ["Dimension", "Reason", "Count", "Population membership"], [(dimension, reason, count, 150 if population == "baseline" else 75) for dimension in DIMENSIONS for reason, count in exclusions[(population, dimension)].items()])
    lines.extend(["", "## Baseline per-label reconciliation", "", "Each derived baseline label count matched the `baseline_human_majority_positive_n` source cell in `results.md` S5T001/S5T002.", ""])
    table(lines, ["Dimension", "Label", "Derived", "S5 exported", "Result"], [(dimension, label, reconciliation[("baseline", dimension)]["per_label"][label], exported[(dimension, label)], "match") for dimension in DIMENSIONS for label in sorted(reconciliation[("baseline", dimension)]["per_label"])])
    lines.extend(["", "## Output boundary", "", "No record identifiers, membership lists, individual responses, or per-record label sets are written in this directory. The frozen restricted files were read after hash verification and were not copied."])
    (OUT / "majority_coverage_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def scan_output(record_ids):
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUT.iterdir() if path.is_file() and path.name != Path(__file__).name)
    return {"record_identifier_strings_detected_in_outputs": sum(record_id in text for record_id in record_ids)}


def main():
    if any(path.name != Path(__file__).name for path in OUT.iterdir()):
        raise RuntimeError("Refusing to overwrite a non-empty coverage output directory")
    before = verify_inputs()
    data = build_stage_b_data()
    rows = []
    all_reconciliation, all_exclusions = {}, {}
    for population, record_ids in (("baseline", data.baseline_ids), ("hard_case", data.hard_case_ids)):
        reconciliation, exclusions = aggregate_population(data, population, record_ids, rows)
        all_reconciliation.update(reconciliation)
        all_exclusions.update(exclusions)
    exported = exported_baseline_support()
    mismatches = []
    for dimension in DIMENSIONS:
        for label, derived in all_reconciliation[("baseline", dimension)]["per_label"].items():
            expected = exported.get((dimension, label))
            if expected != derived:
                mismatches.append({"dimension": dimension, "label": label, "derived": derived, "exported": expected})
    if mismatches:
        raise RuntimeError(f"STOP: baseline per-label reconciliation mismatch: {mismatches}")
    write_csv(rows)
    write_summary(all_reconciliation, all_exclusions, exported)
    after = verify_inputs()
    if before != after:
        raise RuntimeError("STOP: a restricted input changed during the run")
    helper_paths = [
        ROOT / "analysis/scratch_coder_stage_b/performance.py",
        ROOT / "analysis/scratch_coder_stage_b/support.py",
        ROOT / "analysis/scratch_coder_stage_a/panels.py",
        ROOT / "analysis/scratch_coder_stage_a/mappings.py",
    ]
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    working_tree = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    metadata = {
        "generation_time_utc": datetime.now(timezone.utc).isoformat(), "git_head": git_head,
        "working_tree_dirty": bool(working_tree), "working_tree_entry_state": working_tree,
        "restricted_inputs_before": before, "restricted_inputs_after": after, "restricted_hashes_unchanged": True,
        "majority_helper": {"path": "analysis/scratch_coder_stage_b/performance.py", "function": "vectors", "definition": "labelwise human membership sum >= 2"},
        "helper_code_hashes": {path.relative_to(ROOT).as_posix(): sha256(path) for path in helper_paths},
        "mask": {"status": "reconstructed", "implementation": "analysis.scratch_coder_stage_a.panels.dimension_panels", "condition": "all C01/C02/C03 dimension values and frozen model value present"},
        "cardinality_constraints": {"Research Domains": {"status": "not documented", "violation_count_reported": False}, "Analytical Purposes": {"maximum_single_coder_labels": 2, "source": "analysis/scratch_coder_stage_a/mappings.py"}},
        "aggregate_exclusions": {f"{population}::{dimension}": values for (population, dimension), values in all_exclusions.items()},
        "baseline_reconciliation": {"status": "passed", "source_tables": ["S5T001", "S5T002"], "mismatches": []},
        "output_content_scan": scan_output(data.formal_ids),
    }
    (OUT / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "baseline": 150, "hard_case": 75, "reconciliation": "passed"}, indent=2))


if __name__ == "__main__":
    main()
