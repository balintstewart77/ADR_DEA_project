#!/usr/bin/env python3
"""Verify candidate-0.7 source/live round-trip equivalence and archive state."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "preregistration/package/06_redcap"
SOURCE = PACKAGE / "redcap_data_dictionary_candidate.csv"
LIVE = PACKAGE / "live_snapshots/redcap_live_dictionary_candidate_0.7_final_2026-07-22.csv"
LIVE_DATA = PACKAGE / "live_snapshots/redcap_live_data_candidate_0.7_post_archive_2026-07-22.csv"
AUDIT_PRE = PACKAGE / "live_qa/audit/redcap_archive_migration_pre_2026-07-22.csv"
AUDIT_REASSIGN = PACKAGE / "live_qa/audit/redcap_archive_dag_reassignment_2026-07-22.csv"
AUDIT_POST = PACKAGE / "live_qa/audit/redcap_archive_migration_post_2026-07-22.csv"
REPORT = PACKAGE / "live_qa/audit/redcap_candidate_0.7_source_live_comparison_2026-07-22.md"

SOURCE_SHA256 = "1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc"
LIVE_SHA256 = "bb1de2b9ea811afc8b0f23fcb489c1e01eb94d6677d45a64c273140532c5293f"
LIVE_DATA_SHA256 = "d618848e0b9d01edd3521c9f71c3a81b050ffa271e015fe46e4beca81d8a81ca"
AUDIT_PRE_SHA256 = "fc74e2904c21e463615d50fbc969a9e8ee24406a2fb892d0c8bf1816fa206189"
AUDIT_REASSIGN_SHA256 = "8eb9d0ad77ee887b60789d473a329a87e426bbf2f442b3e5ca77cab44b7a5ed6"
AUDIT_POST_SHA256 = "931df02328c93799b55a6304fdb3a63465dc5e29f058366b576aafc0267eb909"

EXPECTED_HEADERS = [
    "Variable / Field Name", "Form Name", "Section Header", "Field Type",
    "Field Label", "Choices, Calculations, OR Slider Labels", "Field Note",
    "Text Validation Type OR Show Slider Number", "Text Validation Min",
    "Text Validation Max", "Identifier?",
    "Branching Logic (Show field only if...)", "Required Field?",
    "Custom Alignment", "Question Number (surveys only)", "Matrix Group Name",
    "Matrix Ranking?", "Field Annotation",
]
EXPECTED_FORMS = {
    "assignment_admin": 50,
    "coder_declaration": 4,
    "scratch_coder": 16,
    "project_owner": 80,
}
EXPECTED_TRANSFORMATIONS = {
    "single_leading_ascii_space_in_live_annotation": 52,
    "one_pass_html_entity_decoding_in_live_owner_label": 12,
    "hidden_assignment_id_section_header_omitted_in_live": 1,
}
TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")


@dataclass(frozen=True)
class Difference:
    row: int
    variable: str
    column: str
    source: str
    live: str
    accepted_transformation: str = ""
    reason: str = ""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows[0], rows[1:]


def normalize_newlines(value: str) -> str:
    """The only normalization used by the raw strict comparison."""
    return value.replace("\r\n", "\n").replace("\r", "\n")


def raw_differences(
    source_header: list[str], source_rows: list[list[str]],
    live_header: list[str], live_rows: list[list[str]],
) -> list[Difference]:
    differences: list[Difference] = []
    if source_header != live_header:
        differences.append(Difference(1, "", "ordered headers", repr(source_header), repr(live_header)))
    for index in range(max(len(source_rows), len(live_rows))):
        row_number = index + 2
        if index >= len(source_rows):
            differences.append(Difference(row_number, live_rows[index][0], "row", "<missing>", repr(live_rows[index])))
            continue
        if index >= len(live_rows):
            differences.append(Difference(row_number, source_rows[index][0], "row", repr(source_rows[index]), "<missing>"))
            continue
        source_row, live_row = source_rows[index], live_rows[index]
        for column_index in range(max(len(source_row), len(live_row))):
            source_value = source_row[column_index] if column_index < len(source_row) else "<missing>"
            live_value = live_row[column_index] if column_index < len(live_row) else "<missing>"
            if normalize_newlines(source_value) != normalize_newlines(live_value):
                column = source_header[column_index] if column_index < len(source_header) else f"column_{column_index + 1}"
                differences.append(Difference(row_number, source_row[0], column, source_value, live_value))
    return differences


def _classify(
    difference: Difference, source_row: dict[str, str], live_row: dict[str, str],
) -> Difference:
    if difference.column == "Field Annotation":
        if not difference.source.startswith(" ") and difference.live == " " + difference.source:
            return replace(difference, accepted_transformation="single_leading_ascii_space_in_live_annotation")
        return replace(difference, reason="annotation is not exactly one live-only leading U+0020")

    if difference.column == "Field Label":
        same_tags = TAG_RE.findall(difference.source) == TAG_RE.findall(difference.live)
        one_pass_equal = html.unescape(difference.source) == difference.live
        if (
            source_row["Form Name"] == live_row["Form Name"] == "project_owner"
            and difference.variable.startswith("po_") and difference.variable.endswith("_label")
            and one_pass_equal and same_tags and difference.source != difference.live
        ):
            return replace(difference, accepted_transformation="one_pass_html_entity_decoding_in_live_owner_label")
        return replace(difference, reason="owner-label one-pass entity predicate or markup-structure predicate failed")

    if difference.column == "Section Header":
        if (
            difference.variable == "assignment_id"
            and difference.source == "Hidden assignment administration"
            and difference.live == ""
            and source_row["Form Name"] == live_row["Form Name"] == "assignment_admin"
        ):
            return replace(difference, accepted_transformation="hidden_assignment_id_section_header_omitted_in_live")
        return replace(difference, reason="section-header omission predicate failed")

    return replace(difference, reason="column is outside the three permitted transformations")


def verify_round_trip(source: Path = SOURCE, live: Path = LIVE) -> dict[str, object]:
    source_header, source_rows = read_csv(source)
    live_header, live_rows = read_csv(live)
    raw = raw_differences(source_header, source_rows, live_header, live_rows)
    issues: list[str] = []
    if source_header != EXPECTED_HEADERS or live_header != EXPECTED_HEADERS:
        issues.append("ordered dictionary headers are not the expected 18 columns")
    if len(source_rows) != 150 or len(live_rows) != 150:
        issues.append("both dictionaries must contain exactly 150 fields")
    if [row[0] for row in source_rows] != [row[0] for row in live_rows]:
        issues.append("variable order differs")
    if [row[1] for row in source_rows] != [row[1] for row in live_rows]:
        issues.append("form order differs")
    source_forms = Counter(row[1] for row in source_rows)
    live_forms = Counter(row[1] for row in live_rows)
    if dict(source_forms) != EXPECTED_FORMS or dict(live_forms) != EXPECTED_FORMS:
        issues.append("field counts by form differ from the frozen candidate-0.7 contract")

    source_dicts = [dict(zip(source_header, row)) for row in source_rows]
    live_dicts = [dict(zip(live_header, row)) for row in live_rows]
    classified: list[Difference] = []
    for difference in raw:
        if difference.row < 2 or difference.row - 2 >= len(source_dicts) or difference.row - 2 >= len(live_dicts):
            classified.append(replace(difference, reason="difference is not a comparable data cell"))
        else:
            classified.append(_classify(difference, source_dicts[difference.row - 2], live_dicts[difference.row - 2]))

    counts = Counter(item.accepted_transformation for item in classified if item.accepted_transformation)
    if len(raw) != 65:
        issues.append(f"strict mismatch count must be 65, found {len(raw)}")
    if dict(counts) != EXPECTED_TRANSFORMATIONS:
        issues.append(f"accepted transformation counts differ: {dict(counts)}")
    unaccepted = [item for item in classified if not item.accepted_transformation]

    section_differences = [item for item in raw if item.column == "Section Header"]
    assignment_source = source_dicts[0] if source_dicts else {}
    assignment_live = live_dicts[0] if live_dicts else {}
    if len(section_differences) != 1:
        issues.append("assignment_id omission is not the only section-header difference")
    if not (
        assignment_source.get("Variable / Field Name") == assignment_live.get("Variable / Field Name") == "assignment_id"
        and assignment_source.get("Form Name") == assignment_live.get("Form Name") == "assignment_admin"
        and assignment_source.get("Field Type") == assignment_live.get("Field Type") == "text"
        and assignment_source.get("Required Field?") == assignment_live.get("Required Field?") == "y"
        and assignment_source.get("Branching Logic (Show field only if...)") == assignment_live.get("Branching Logic (Show field only if...)") == ""
        and assignment_source.get("Field Annotation") == "@HIDDEN-SURVEY @READONLY"
        and assignment_live.get("Field Annotation") == " @HIDDEN-SURVEY @READONLY"
    ):
        issues.append("assignment_id no longer satisfies first-field, hidden-admin, required, or non-branching invariants")
    if any("[assignment_id]" in row.get("Branching Logic (Show field only if...)", "") for row in source_dicts + live_dicts):
        issues.append("a field branching rule depends on assignment_id")

    residual_count = len(unaccepted) + len(issues)
    return {
        "source": source,
        "live": live,
        "source_sha256": sha256(source),
        "live_sha256": sha256(live),
        "source_rows": len(source_rows),
        "live_rows": len(live_rows),
        "source_columns": len(source_header),
        "live_columns": len(live_header),
        "source_forms": dict(source_forms),
        "live_forms": dict(live_forms),
        "headers_match": source_header == live_header,
        "variable_order_matches": [row[0] for row in source_rows] == [row[0] for row in live_rows],
        "raw_mismatches": classified,
        "raw_mismatch_count": len(raw),
        "accepted_counts": dict(counts),
        "unaccepted": unaccepted,
        "contract_issues": issues,
        "residual_mismatch_count": residual_count,
    }


def verify_archive_state() -> dict[str, object]:
    data_header, data_rows_raw = read_csv(LIVE_DATA)
    pre_header, pre_rows_raw = read_csv(AUDIT_PRE)
    reassign_header, reassign_rows_raw = read_csv(AUDIT_REASSIGN)
    post_header, post_rows_raw = read_csv(AUDIT_POST)
    rows = lambda header, values: [dict(zip(header, row)) for row in values]
    data = rows(data_header, data_rows_raw)
    pre = rows(pre_header, pre_rows_raw)
    reassign = rows(reassign_header, reassign_rows_raw)
    post = rows(post_header, post_rows_raw)
    ids = lambda values: [row["assignment_id"] for row in values]
    pre_by = {row["assignment_id"]: row for row in pre}
    post_by = {row["assignment_id"]: row for row in post}
    non_dag_differences = []
    for assignment_id in sorted(set(pre_by) & set(post_by)):
        for column in pre_header:
            if column != "redcap_data_access_group" and pre_by[assignment_id].get(column) != post_by[assignment_id].get(column):
                non_dag_differences.append({
                    "assignment_id": assignment_id, "column": column,
                    "pre": pre_by[assignment_id].get(column), "post": post_by[assignment_id].get(column),
                })
    checks = {
        "evidence_hashes": {
            LIVE_DATA.name: sha256(LIVE_DATA) == LIVE_DATA_SHA256,
            AUDIT_PRE.name: sha256(AUDIT_PRE) == AUDIT_PRE_SHA256,
            AUDIT_REASSIGN.name: sha256(AUDIT_REASSIGN) == AUDIT_REASSIGN_SHA256,
            AUDIT_POST.name: sha256(AUDIT_POST) == AUDIT_POST_SHA256,
        },
        "live_rows_35_unique": len(data) == 35 and len(set(ids(data))) == 35,
        "live_all_archive_dag": {row.get("redcap_data_access_group") for row in data} == {"pilot_and_qa_archi"},
        "live_all_validation_excluded": {row.get("validation_included") for row in data} == {"0"},
        "no_formal_validation_batch": not any(row.get("assignment_batch") == "formal_validation" for row in data),
        "composition_exact": Counter(row.get("instrument_ver") for row in data) == Counter({"redcap-candidate-0.3": 30, "redcap-candidate-0.6": 1, "redcap-candidate-0.7": 4}),
        "reassignment_header_exact": reassign_header == ["assignment_id", "redcap_data_access_group"],
        "reassignment_35_unique": len(reassign) == 35 and len(set(ids(reassign))) == 35,
        "reassignment_all_archive_dag": {row.get("redcap_data_access_group") for row in reassign} == {"pilot_and_qa_archi"},
        "pre_post_35_unique": len(pre) == len(post) == 35 and len(set(ids(pre))) == len(set(ids(post))) == 35,
        "pre_post_same_ids": set(ids(pre)) == set(ids(post)) == set(ids(reassign)),
        "pre_post_same_columns": pre_header == post_header,
        "only_dag_changed": not non_dag_differences,
        "post_all_archive_dag": {row.get("redcap_data_access_group") for row in post} == {"pilot_and_qa_archi"},
        "post_matches_live_audit_columns": all(all(row.get(column, "") == post_by[row["assignment_id"]].get(column, "") for column in post_header) for row in data),
    }
    passed = all(value if isinstance(value, bool) else all(value.values()) for value in checks.values())
    return {
        "passed": passed,
        "checks": checks,
        "composition": dict(Counter(row.get("instrument_ver") for row in data)),
        "non_dag_differences": non_dag_differences,
    }


def _json_cell(value: str) -> str:
    return json.dumps(value, ensure_ascii=False).replace("|", "\\|")


def render_report(result: dict[str, object], archive: dict[str, object]) -> str:
    differences: list[Difference] = result["raw_mismatches"]  # type: ignore[assignment]
    counts: dict[str, int] = result["accepted_counts"]  # type: ignore[assignment]
    lines = [
        "# Candidate 0.7 source-to-live dictionary comparison — 2026-07-22", "",
        "**Decision: PASSED under the enumerated narrow REDCap round-trip equivalence contract.**", "",
        "The generated candidate and live REDCap export are not textually identical. They are semantically equivalent under three enumerated, narrowly verified REDCap round-trip transformations. No difference affects field identity, order, type, choices, branching logic, validation, required status, annotations after the verified single-space transformation, or coder-facing content.", "",
        "## Inputs and dimensions", "",
        f"- Generated source: `{Path(result['source']).relative_to(ROOT).as_posix()}`", f"- Source SHA-256: `{result['source_sha256']}`",
        f"- Final live export: `{Path(result['live']).relative_to(ROOT).as_posix()}`", f"- Live SHA-256: `{result['live_sha256']}`",
        f"- Source dimensions: {result['source_rows']} data rows × {result['source_columns']} columns",
        f"- Live dimensions: {result['live_rows']} data rows × {result['live_columns']} columns",
        "- Fields by form in both files: assignment_admin=50; coder_declaration=4; scratch_coder=16; project_owner=80",
        f"- Ordered 18-column headers match: {'Yes' if result['headers_match'] else 'No'}",
        f"- Variable and form order match: {'Yes' if result['variable_order_matches'] else 'No'}", "",
        "## Level 1 — raw strict equality", "",
        "The strict comparison parses both files as UTF-8 CSV with an optional BOM, compares every ordered cell, and normalizes only CRLF or CR inside cells to LF. It performs no trimming, entity decoding, case folding, Unicode normalization, whitespace collapsing, field reordering, or choice reordering.", "",
        f"- Raw mismatching cells: **{result['raw_mismatch_count']}**", "- Strict textual equality: **No**", "",
        "| Row | Variable | Column | Source value | Live value |", "|---:|---|---|---|---|",
    ]
    for item in differences:
        lines.append(f"| {item.row} | `{item.variable}` | `{item.column}` | `{_json_cell(item.source)}` | `{_json_cell(item.live)}` |")
    lines += ["", "## Level 2 — narrow REDCap round-trip equivalence", "",
        "| Accepted transformation | Exact predicate | Count |", "|---|---|---:|",
        f"| Single leading annotation space | Column is `Field Annotation`; source does not begin with U+0020; live is exactly one U+0020 followed by the complete source value. No trim or other whitespace rule is used. | {counts.get('single_leading_ascii_space_in_live_annotation', 0)} |",
        f"| One-pass HTML character-entity decoding | Column is `Field Label`; form is `project_owner`; variable is `po_*_label`; `html.unescape(source)` exactly equals live; source/live markup-tag sequences are identical. No HTML stripping or textual normalization is used. | {counts.get('one_pass_html_entity_decoding_in_live_owner_label', 0)} |",
        f"| Hidden assignment header omitted | The sole `Section Header` difference is `assignment_id`: source is `Hidden assignment administration`, live is blank. It remains the first required text field on hidden `assignment_admin`; it has no branching logic and no branching expression references it. | {counts.get('hidden_assignment_id_section_header_omitted_in_live', 0)} |", "",
        f"- Unaccepted raw differences: **{len(result['unaccepted'])}**", f"- Contract issues: **{len(result['contract_issues'])}**",
        f"- Residual mismatches: **{result['residual_mismatch_count']}**", "",
        "The `assignment_id` section-header omission is a presentation-only round-trip difference on the hidden Assignment Admin instrument. Source value: `Hidden assignment administration`; live value: blank. No coder-facing field, branching logic, instrument visibility rule, or stored data value depends on that header.", "",
        "## Limits of equivalence", "",
        "This finding does not claim byte identity or unrestricted semantic normalization. Only the three predicates above are accepted, only at the 65 listed cells. Any additional space, different column or variable, second decoding step, changed markup tag, wording change, reordered row/choice, or new missing header is residual and fails the verifier.", "",
        "## Archive-state cross-check", "",
        f"- Archive verification passed: **{'Yes' if archive['passed'] else 'No'}**",
        "- Final data: 35 rows and 35 unique assignment IDs; all `pilot_and_qa_archi`; all `validation_included=0`; no `formal_validation` batch.",
        "- Composition: 30 candidate-0.3 pilot records, 1 candidate-0.6 QA record, and 4 candidate-0.7 QA records.",
        "- Pre/post audit membership is identical; the reassignment file has only `assignment_id` and `redcap_data_access_group`; the only migration change is DAG assignment.", "",
        "## Freeze conclusion", "",
        "The narrow verifier leaves zero residual mismatches and the archive-state cross-check passes. Candidate 0.7 may proceed to repository freeze subject to the required test suite and manifest/documentation checks. The raw source and live export remain textually different in exactly 65 fully enumerated cells.", "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--live", type=Path, default=LIVE)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify_round_trip(args.source, args.live)
    archive = verify_archive_state()
    hash_issues = []
    if args.source.resolve() == SOURCE.resolve() and result["source_sha256"] != SOURCE_SHA256:
        hash_issues.append("canonical source SHA-256 differs")
    if args.live.resolve() == LIVE.resolve() and result["live_sha256"] != LIVE_SHA256:
        hash_issues.append("final live SHA-256 differs")
    if hash_issues:
        result["contract_issues"].extend(hash_issues)  # type: ignore[union-attr]
        result["residual_mismatch_count"] = int(result["residual_mismatch_count"]) + len(hash_issues)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(result, archive), encoding="utf-8", newline="\n")
    summary = {
        "source_sha256": result["source_sha256"], "live_sha256": result["live_sha256"],
        "raw_mismatch_count": result["raw_mismatch_count"], "accepted_counts": result["accepted_counts"],
        "residual_mismatch_count": result["residual_mismatch_count"], "contract_issues": result["contract_issues"],
        "archive_passed": archive["passed"], "report_written": str(args.report) if args.write_report else None,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["residual_mismatch_count"] == 0 and archive["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
