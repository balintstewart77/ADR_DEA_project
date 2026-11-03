"""Exploratory descriptive run: individual-rater label application, cardinality and abstention.

Specification: SPEC_label_application_cardinality_2026-11-03.md (written before this
code). Reads the shared Stage A data without modification. Random baseline only;
aggregate counts only; no intervals, no tests, no record-level output.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import platform
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.config import CODERS  # noqa: E402
from analysis.scratch_coder_stage_a.load import verify_authorities  # noqa: E402
from analysis.scratch_coder_stage_a.panels import _taxonomy_labels, build_stage_a_data, dimension_panels  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent
SPEC = OUTPUT_DIR / "SPEC_label_application_cardinality_2026-11-03.md"
RESULTS = ROOT / "analysis/scratch_coder_results/results.md"
UNCLEAR = "Unclear from Register Entry"
FABLE = "Fable 5"
RATERS = (*CODERS, FABLE)
DIMENSIONS = ("Research Domains", "Analytical Purposes")
TAXONOMY_KEY = {"Research Domains": "domains", "Analytical Purposes": "purposes"}
SOURCE_TABLES = {
    "Research Domains": {"labels": "S5T001", "unclear": "S10T001"},
    "Analytical Purposes": {"labels": "S5T002", "unclear": "S10T002"},
}
# Approved G.12 derivations 3 and 4 (pass-2 log): Fable 5 totals with and without Unclear.
G12_FABLE_TOTALS = {"Research Domains": (199, 198), "Analytical Purposes": (160, 159)}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def results_section(table_id: str) -> list[str]:
    lines = RESULTS.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"### {table_id} "))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("### ") or lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def exported_value(table_id: str, row_key: str, quantity: str) -> str:
    for line in results_section(table_id):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == row_key and cells[1] == f"`{quantity}`":
            return cells[2]
    raise KeyError(f"{table_id}: {row_key} / {quantity} not found")


def ratio(numerator: int, denominator: int) -> str:
    return repr(numerator / denominator) if denominator else ""


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    started = datetime.datetime.now(datetime.timezone.utc)
    checks: list[dict] = []

    def check(name: str, passed: bool, actual=None, expected=None) -> None:
        checks.append({"check": name, "status": "passed" if passed else "FAILED", "actual": actual, "expected": expected})
        if not passed:
            raise ValueError(f"Check failed: {name}: actual={actual!r} expected={expected!r}")

    for authority in verify_authorities():
        check(f"hash {authority.manifest_id}", authority.matched, authority.observed_sha256, authority.expected_sha256)
    data = build_stage_a_data()
    check("baseline record count", len(data.baseline_ids) == 150, len(data.baseline_ids), 150)
    taxonomy = _taxonomy_labels()

    label_rows: list[dict] = []
    cardinality_rows: list[dict] = []
    populations: dict[str, dict] = {}
    for dimension in DIMENSIONS:
        panels = dimension_panels(data, data.baseline_ids, dimension)
        check(f"{dimension}: one panel per baseline record", len(panels) == 150, len(panels), 150)
        valid, excluded = [], []
        for panel in panels:
            sets = dict(zip(RATERS, (panel.coder_a, panel.coder_b, panel.coder_c, panel.model)))
            missing = [rater for rater, value in sets.items() if value is None]
            invalid = data.responses[(data.responses["record_id"] == panel.record_id) & ~data.responses["structural_valid"]]
            if missing or len(invalid):
                excluded.append({"reason": "missing set" if missing else "structurally invalid coder response", "raters": missing})
            else:
                valid.append(sets)
        n = len(valid)
        populations[dimension] = {"population": "baseline", "records": 150, "valid_common_records": n,
                                  "excluded_records": len(excluded), "excluded_reasons": excluded}
        check(f"{dimension}: valid common records", n == 150, n, 150)

        labels = sorted(taxonomy[TAXONOMY_KEY[dimension]])
        check(f"{dimension}: Unclear in frozen label set", UNCLEAR in labels, UNCLEAR in labels, True)
        for rater in RATERS:
            empty = sum(1 for sets in valid if not sets[rater])
            mixed = sum(1 for sets in valid if UNCLEAR in sets[rater] and len(sets[rater]) > 1)
            unknown = set().union(*(sets[rater] for sets in valid)) - set(labels)
            check(f"{dimension}/{rater}: no empty sets", empty == 0, empty, 0)
            check(f"{dimension}/{rater}: Unclear exclusive", mixed == 0, mixed, 0)
            check(f"{dimension}/{rater}: labels within frozen taxonomy", not unknown, sorted(unknown), [])

        tables = SOURCE_TABLES[dimension]
        for label in labels:
            counts = {rater: sum(1 for sets in valid if label in sets[rater]) for rater in RATERS}
            majority = sum(1 for sets in valid if sum(label in sets[coder] for coder in CODERS) >= 2)
            exported_model = int(exported_value(tables["labels"], label, "baseline_model_positive_n"))
            exported_majority = int(exported_value(tables["labels"], label, "baseline_human_majority_positive_n"))
            check(f"{dimension}/{label}: Fable 5 count equals {tables['labels']}", counts[FABLE] == exported_model, counts[FABLE], exported_model)
            check(f"{dimension}/{label}: recomputed majority equals {tables['labels']}", majority == exported_majority, majority, exported_majority)
            coder_counts = [counts[coder] for coder in CODERS]
            low, high = min(coder_counts), max(coder_counts)
            position = "above_all_coders" if counts[FABLE] > high else "below_all_coders" if counts[FABLE] < low else "within_coder_range"
            label_rows.append({
                "table_id": "LAC1T001", "population": "baseline", "dimension": dimension, "label": label,
                "label_type": "unclear" if label == UNCLEAR else "substantive",
                "C01_count": counts["C01"], "C02_count": counts["C02"], "C03_count": counts["C03"], "fable5_count": counts[FABLE],
                "coder_min": low, "coder_max": high, "fable5_position": position, "denominator_records": n,
                "denominator_definition": "baseline records with a complete, structurally valid set from all three coders and Fable 5 in this dimension",
                "fable5_reconciled_with": f"{tables['labels']} baseline_model_positive_n = {exported_model}",
                "coder_majority_recomputed_check": f"{tables['labels']} baseline_human_majority_positive_n = {exported_majority}",
                "status": "exploratory descriptive; not preregistered",
            })

        unclear_uses = 0
        for rater in RATERS:
            sizes = [len(sets[rater] - {UNCLEAR}) for sets in valid]
            unclear = sum(1 for sets in valid if UNCLEAR in sets[rater])
            classified = sum(1 for size in sizes if size >= 1)
            total_all = sum(len(sets[rater]) for sets in valid)
            substantive = sum(sizes)
            if rater in CODERS:
                unclear_uses += unclear
            if rater == FABLE:
                check(f"{dimension}: Fable 5 totals equal G.12 derivations 3-4", (total_all, substantive) == G12_FABLE_TOTALS[dimension],
                      [total_all, substantive], list(G12_FABLE_TOTALS[dimension]))
            check(f"{dimension}/{rater}: classified plus Unclear equals N", classified + unclear == n, classified + unclear, n)
            cardinality_rows.append({
                "table_id": "LAC1T002", "population": "baseline", "dimension": dimension, "rater": rater,
                "records_N": n,
                "substantive_label_applications": substantive,
                "mean_substantive_labels_per_record": ratio(substantive, n),
                "unclear_records": unclear, "unclear_proportion": ratio(unclear, n),
                "substantively_classified_records": classified,
                "mean_substantive_labels_among_classified": ratio(substantive, classified),
                "all_label_applications_including_unclear": total_all,
                "empty_set_records": 0, "unclear_with_substantive_records": 0,
                "status": "exploratory descriptive; not preregistered; no intervals",
            })
        exported_uses = int(exported_value(tables["unclear"], "frequency; coder_response_uses; Unclear", "count"))
        check(f"{dimension}: coder Unclear uses equal {tables['unclear']}", unclear_uses == exported_uses, unclear_uses, exported_uses)

    write_csv(OUTPUT_DIR / "LAC1T001.csv", label_rows)
    write_csv(OUTPUT_DIR / "LAC1T002.csv", cardinality_rows)

    lines = [
        "# Individual-rater label application, cardinality and abstention (exploratory, descriptive)", "",
        "Not preregistered. Specification: `SPEC_label_application_cardinality_2026-11-03.md`. Random baseline only; "
        "valid common records per dimension; no intervals or tests. Marginal counts do not show whether raters labelled the same records.", "",
    ]
    for dimension in DIMENSIONS:
        lines += [f"## LAC1T001 — Label application counts — {dimension}", "",
                  "| Label | C01 | C02 | C03 | Fable 5 | Coder range | Fable 5 placement | Records |", "|---|---|---|---|---|---|---|---|"]
        for row in (r for r in label_rows if r["dimension"] == dimension):
            lines.append(f"| {row['label']} | {row['C01_count']} | {row['C02_count']} | {row['C03_count']} | {row['fable5_count']} | "
                         f"{row['coder_min']}–{row['coder_max']} | {row['fable5_position'].replace('_', ' ')} | {row['denominator_records']} |")
        lines.append("")
    lines += ["## LAC1T002 — Cardinality and abstention", "",
              "| Dimension | Rater | N | Mean substantive labels per record | Unclear n (proportion) | Classified records | Mean substantive labels among classified |",
              "|---|---|---|---|---|---|---|"]
    for row in cardinality_rows:
        lines.append(f"| {row['dimension']} | {row['rater']} | {row['records_N']} | {Decimal(row['mean_substantive_labels_per_record']):.4f} | "
                     f"{row['unclear_records']} ({Decimal(row['unclear_proportion']):.4f}) | {row['substantively_classified_records']} | "
                     f"{Decimal(row['mean_substantive_labels_among_classified']):.4f} |")
    (OUTPUT_DIR / "results_label_application_cardinality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--", "analysis/label_application_cardinality_exploratory"], cwd=ROOT, text=True).strip())
    metadata = {
        "status": "exploratory descriptive, not preregistered",
        "specification": {"path": str(SPEC.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256_file(SPEC),
                          "created": "2026-11-03", "committed_before_run": False,
                          "note": "Investigator instructed no commit in this session; specification hash recorded instead."},
        "run_started_utc": started.isoformat(), "run_completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository_head": head, "run_directory_uncommitted": dirty,
        "populations": populations, "raters": list(RATERS), "dimensions": list(DIMENSIONS),
        "reconciliation_sources": {"results_md": {"path": "analysis/scratch_coder_results/results.md", "sha256": sha256_file(RESULTS)},
                                   "tables": SOURCE_TABLES, "g12_fable_totals": {k: list(v) for k, v in G12_FABLE_TOTALS.items()}},
        "checks": checks,
        "outputs": {name: sha256_file(OUTPUT_DIR / name) for name in ("LAC1T001.csv", "LAC1T002.csv", "results_label_application_cardinality.md")},
        "restricted_outputs": [],
        "not_accessed": ["adjudication findings", "project-owner responses"],
        "software": {"python": sys.version, "platform": platform.platform()},
    }
    (OUTPUT_DIR / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(checks)} checks passed")


if __name__ == "__main__":
    main()
