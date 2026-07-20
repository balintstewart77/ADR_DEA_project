"""Run the source-masked, descriptive three-coder pilot analysis.

The runner deliberately ignores every production-model field in the REDCap
export.  It cannot run formal validation, replacement-panel, inference,
sampling, adjudication-selection, or release workflows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping, Sequence

import yaml

from .diagnostics import majority_diagnostic_rating
from .redcap import (
    ExportParseError,
    FIT_CODES,
    ISSUE_CODES,
    DecodedScratchAssignment,
    decode_scratch_row,
    load_wide_export,
)
from .schema import UNCLEAR
from .scratch_agreement import (
    DEFAULT_CODERS,
    DEFAULT_PAIRS,
    ScratchAgreementError,
    ScratchSetRating,
    analyse_set_record,
    complete_case_three_coder_matrix,
    summarise_pairwise,
    three_rater_masi_alpha,
    three_rater_nominal_alpha,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXCLUSION_LIST = Path(
    "preregistration/package/04_exclusions_and_sampling/"
    "training_pilot_exclusion_list_v8.csv"
)
EXPECTED_RECORDS = 10
EXPECTED_ASSIGNMENTS = 30
EXPECTED_CODERS = DEFAULT_CODERS
FORMAL_VALIDATION_METRICS = False
MODEL_OUTPUTS_INITIALLY_HIDDEN = True
CONFIDENCE_CODES = {1: "High", 2: "Medium", 3: "Low"}
SEVERITIES = ("pass", "warning_interpretable", "query_required", "fatal")

ASSIGNMENT_QC_COLUMNS = (
    "assignment_id", "record_id", "coder_id", "mapping_source",
    "mapping_status", "duplicate_flag", "pilot_inclusion",
)
READY_COLUMNS = (
    "record_id", "coder_id", "instrument_version", "research_domains",
    "analytical_purposes", "covid_tag", "equity_tag",
    "register_sufficiency", "taxonomy_fit", "taxonomy_issues", "confidence",
    "response_complete", "note_triggered", "note_present", "qc_status",
)
RECORD_AGREEMENT_COLUMNS = (
    "record_id", "classification_dimension", "C01_set", "C02_set", "C03_set",
    "complete_set_pattern", "C01_C02_exact", "C01_C03_exact", "C02_C03_exact",
    "C01_C02_jaccard", "C01_C03_jaccard", "C02_C03_jaccard",
    "majority_supported_labels", "C01_difference", "C01_extra_labels",
    "C01_missing_labels", "C02_difference", "C02_extra_labels",
    "C02_missing_labels", "C03_difference", "C03_extra_labels",
    "C03_missing_labels", "majority_supported_count",
    "purpose_majority_exceeds_two", "all_sets_distinct_with_nonempty_majority",
)
PAIRWISE_COLUMNS = (
    "classification_dimension", "coder_pair", "denominator", "exact_count",
    "exact_proportion", "mean_jaccard", "median_jaccard", "minimum_jaccard",
    "maximum_jaccard",
)
METRIC_COLUMNS = (
    "metric", "classification_dimension", "category", "point_estimate", "valid",
    "undefined_reason", "numerator", "denominator",
    "descriptive_pilot_statistic", "notes",
)
DIAGNOSTIC_COLUMNS = (
    "item", "scope", "category", "coder_id", "record_id", "count",
    "denominator", "proportion", "majority_or_pattern", "details",
)
ISSUE_COLUMNS = (
    "record_id", "issue_source", "issue_category", "observed_pattern",
    "relevant_coder_ids", "brief_evidence", "status",
)


class PilotAnalysisError(RuntimeError):
    """Raised when pilot safety or structural constraints fail."""


@dataclass(frozen=True)
class QCFinding:
    severity: str
    code: str
    detail: str
    record_id: str = ""
    coder_id: str = ""
    assignment_id: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"Unknown QC severity: {self.severity}")


@dataclass(frozen=True)
class AssignmentMappingResult:
    rows: tuple[dict[str, object], ...]
    findings: tuple[QCFinding, ...]
    observed_assignments: int
    unique_assignments: int
    unique_records: int
    coder_counts: Mapping[str, int]
    missing_combinations: tuple[str, ...]
    duplicate_combinations: tuple[str, ...]

    @property
    def fatal(self) -> bool:
        return any(item.severity == "fatal" for item in self.findings)


@dataclass(frozen=True)
class PilotDecodedAssignment:
    decoded: DecodedScratchAssignment
    confidence: str | None
    note_triggered: bool
    note_present: bool
    raw: Mapping[str, str]


def validate_pilot_safety_configuration(
    *, formal_validation_metrics: bool, model_outputs_initially_hidden: bool
) -> None:
    if formal_validation_metrics:
        raise PilotAnalysisError("Formal validation metrics are disabled for the pilot")
    if not model_outputs_initially_hidden:
        raise PilotAnalysisError("Initial pilot analysis must keep model outputs hidden")


def _value(row: Mapping[str, object], field: str) -> str:
    return str(row.get(field, "") or "").strip()


def _integer(row: Mapping[str, object], field: str) -> int | None:
    value = _value(row, field)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _label_text(labels: Iterable[str]) -> str:
    return " | ".join(sorted(labels))


def _float(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def _git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def validate_output_row_schema(
    columns: Sequence[str], rows: Iterable[Mapping[str, object]]
) -> None:
    expected = set(columns)
    for position, row in enumerate(rows, 1):
        if set(row) != expected:
            raise PilotAnalysisError(
                f"Output row {position} has unexpected schema: "
                f"missing={sorted(expected - set(row))}, extra={sorted(set(row) - expected)}"
            )


def detect_instrument_version(
    rows: Sequence[Mapping[str, object]], *, explicit_version: str | None = None
) -> str:
    versions = {_value(row, "instrument_ver") for row in rows}
    versions.discard("")
    if len(versions) != 1:
        raise PilotAnalysisError(
            f"Expected exactly one non-empty instrument version; found {sorted(versions)}"
        )
    detected = next(iter(versions))
    if detected not in FIT_CODES:
        raise PilotAnalysisError(f"Unsupported instrument version: {detected}")
    if explicit_version is not None and explicit_version != detected:
        raise PilotAnalysisError(
            f"Explicit instrument version {explicit_version!r} conflicts with export {detected!r}"
        )
    return detected


def build_assignment_mapping(
    rows: Sequence[Mapping[str, object]],
    *,
    expected_records: int = EXPECTED_RECORDS,
    expected_assignments: int = EXPECTED_ASSIGNMENTS,
    expected_coders: tuple[str, str, str] = EXPECTED_CODERS,
) -> AssignmentMappingResult:
    """Use only explicit hidden reviewer IDs; never infer identity from order."""

    assignment_targets: defaultdict[str, set[tuple[str, str]]] = defaultdict(set)
    pair_counts: Counter[tuple[str, str]] = Counter()
    assignment_counts: Counter[str] = Counter()
    prepared: list[dict[str, object]] = []
    findings: list[QCFinding] = []

    for row in rows:
        assignment_id = _value(row, "assignment_id")
        record_id = _value(row, "source_record_id")
        raw_coder = _value(row, "reviewer_id")
        coder_id = raw_coder.upper()
        mapped = bool(assignment_id and record_id and coder_id in expected_coders)
        mapping_status = "mapped" if mapped else "unmapped"
        pilot_inclusion = (
            _value(row, "review_stream") == "1"
            and _value(row, "sample_set") == "4"
            and _value(row, "validation_included") == "0"
        )
        if mapped:
            assignment_targets[assignment_id].add((record_id, coder_id))
            pair_counts[(record_id, coder_id)] += 1
            assignment_counts[assignment_id] += 1
        else:
            findings.append(QCFinding(
                "fatal", "unmapped_assignment",
                "Explicit assignment, record, or recognised hidden reviewer ID is missing",
                record_id, coder_id, assignment_id,
            ))
        if not pilot_inclusion:
            findings.append(QCFinding(
                "fatal", "nonpilot_row",
                "Row is not an excluded scratch-coder pilot response",
                record_id, coder_id, assignment_id,
            ))
        prepared.append({
            "assignment_id": assignment_id,
            "record_id": record_id,
            "coder_id": coder_id,
            "mapping_source": "explicit_hidden_reviewer_id" if raw_coder else "",
            "mapping_status": mapping_status,
            "duplicate_flag": 0,
            "pilot_inclusion": int(pilot_inclusion),
        })

    ambiguous_assignments = {
        assignment_id for assignment_id, targets in assignment_targets.items()
        if len(targets) != 1
    }
    duplicate_pairs = {pair for pair, count in pair_counts.items() if count > 1}
    duplicate_assignments = {
        assignment_id for assignment_id, count in assignment_counts.items() if count > 1
    }
    for item in prepared:
        pair = (str(item["record_id"]), str(item["coder_id"]))
        assignment_id = str(item["assignment_id"])
        if assignment_id in ambiguous_assignments:
            item["mapping_status"] = "ambiguous"
        if pair in duplicate_pairs or assignment_id in duplicate_assignments:
            item["duplicate_flag"] = 1

    for assignment_id in sorted(ambiguous_assignments):
        findings.append(QCFinding(
            "fatal", "ambiguous_assignment_mapping",
            "One assignment ID maps to multiple record/coder targets",
            assignment_id=assignment_id,
        ))
    for record_id, coder_id in sorted(duplicate_pairs):
        findings.append(QCFinding(
            "fatal", "duplicate_coder_record",
            "Coder-record combination appears more than once", record_id, coder_id,
        ))
    for assignment_id in sorted(duplicate_assignments - ambiguous_assignments):
        findings.append(QCFinding(
            "fatal", "duplicate_assignment_id",
            "Assignment ID appears more than once", assignment_id=assignment_id,
        ))

    mapped_pairs = set(pair_counts)
    record_ids = {record_id for record_id, _ in mapped_pairs}
    observed_coders = {coder_id for _, coder_id in mapped_pairs}
    missing = tuple(sorted(
        f"{record_id}/{coder_id}"
        for record_id in record_ids
        for coder_id in expected_coders
        if (record_id, coder_id) not in mapped_pairs
    ))
    if len(rows) != expected_assignments:
        findings.append(QCFinding(
            "fatal", "unexpected_row_count",
            f"Expected {expected_assignments} rows; observed {len(rows)}",
        ))
    if len(assignment_counts) != expected_assignments:
        findings.append(QCFinding(
            "fatal", "unexpected_unique_assignment_count",
            f"Expected {expected_assignments} unique assignments; observed {len(assignment_counts)}",
        ))
    if len(record_ids) != expected_records:
        findings.append(QCFinding(
            "fatal", "unexpected_record_count",
            f"Expected {expected_records} records; observed {len(record_ids)}",
        ))
    if observed_coders != set(expected_coders):
        findings.append(QCFinding(
            "fatal", "unexpected_coder_set",
            f"Expected {sorted(expected_coders)}; observed {sorted(observed_coders)}",
        ))
    coder_counts = Counter(coder_id for _, coder_id in mapped_pairs)
    for coder_id in expected_coders:
        if coder_counts[coder_id] != expected_records:
            findings.append(QCFinding(
                "fatal", "unexpected_coder_assignment_count",
                f"{coder_id} has {coder_counts[coder_id]} assignments; expected {expected_records}",
                coder_id=coder_id,
            ))
    if missing:
        findings.append(QCFinding(
            "fatal", "missing_coder_record_combinations",
            f"Missing {len(missing)} required coder-record combinations",
        ))

    return AssignmentMappingResult(
        rows=tuple(prepared),
        findings=tuple(findings),
        observed_assignments=len(rows),
        unique_assignments=len(assignment_counts),
        unique_records=len(record_ids),
        coder_counts=dict(coder_counts),
        missing_combinations=missing,
        duplicate_combinations=tuple(
            f"{record_id}/{coder_id}" for record_id, coder_id in sorted(duplicate_pairs)
        ),
    )


def load_frozen_pilot_ids(path: Path) -> frozenset[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return frozenset(
            _value(row, "record_id") for row in rows
            if _value(row, "exclusion_group") == "pilot"
        )


def decode_pilot_assignments(
    rows: Sequence[Mapping[str, str]], instrument_version: str
) -> tuple[tuple[PilotDecodedAssignment, ...], tuple[QCFinding, ...]]:
    decoded: list[PilotDecodedAssignment] = []
    findings: list[QCFinding] = []
    for row in rows:
        assignment_id = _value(row, "assignment_id")
        record_id = _value(row, "source_record_id")
        coder_id = _value(row, "reviewer_id").upper()
        try:
            item = decode_scratch_row(row)
        except ExportParseError as exc:
            findings.append(QCFinding(
                "fatal", "decode_failure", str(exc), record_id, coder_id, assignment_id,
            ))
            continue
        confidence_code = _integer(row, "sc_confidence")
        confidence = CONFIDENCE_CODES.get(confidence_code)
        fit_code = _integer(row, "sc_taxonomy_fit")
        sufficiency_code = _integer(row, "sc_sufficiency")
        note_triggered = (
            sufficiency_code in {2, 3} or fit_code in {2, 3} or confidence_code == 3
        )
        decoded.append(PilotDecodedAssignment(
            decoded=item,
            confidence=confidence,
            note_triggered=note_triggered,
            note_present=bool(_value(row, "sc_note")),
            raw=row,
        ))
    if decoded and {item.decoded.instrument_version for item in decoded} != {instrument_version}:
        findings.append(QCFinding(
            "fatal", "decoded_version_mismatch",
            "Decoded rows do not all match the detected instrument version",
        ))
    return tuple(decoded), tuple(findings)


def instrument_qc(
    assignments: Sequence[PilotDecodedAssignment],
    *,
    frozen_pilot_ids: frozenset[str],
    instrument_version: str,
) -> tuple[QCFinding, ...]:
    findings: list[QCFinding] = []
    observed_ids = {item.decoded.record_id for item in assignments}
    if observed_ids != set(frozen_pilot_ids):
        findings.append(QCFinding(
            "fatal", "pilot_exclusion_mismatch",
            "Observed pilot Record IDs do not exactly match the frozen pilot exclusion set",
        ))

    for item in assignments:
        decoded, raw = item.decoded, item.raw
        rating = decoded.rating
        context = {
            "record_id": decoded.record_id,
            "coder_id": decoded.reviewer_id.upper(),
            "assignment_id": decoded.assignment_id,
        }

        if not rating.complete:
            findings.append(QCFinding(
                "fatal", "incomplete_response", "Scratch form is not marked complete", **context,
            ))
        if rating.domains is None or not rating.domains:
            findings.append(QCFinding(
                "fatal", "missing_domains", "Research Domains are missing", **context,
            ))
        if rating.purposes is None or not rating.purposes:
            findings.append(QCFinding(
                "fatal", "missing_purposes", "Analytical Purposes are missing", **context,
            ))
        if rating.purposes is not None and len(rating.purposes) > 2:
            findings.append(QCFinding(
                "query_required", "purpose_maximum_exceeded",
                "More than two Analytical Purposes were selected", **context,
            ))
        for dimension, labels in (("domains", rating.domains), ("purposes", rating.purposes)):
            if labels and UNCLEAR in labels and len(labels) > 1:
                findings.append(QCFinding(
                    "query_required", "unclear_with_substantive_label",
                    f"{dimension} combines Unclear with substantive labels", **context,
                ))
        if rating.covid_tag not in {0, 1} or rating.equity_tag not in {0, 1}:
            findings.append(QCFinding(
                "fatal", "invalid_binary_tag", "A cross-cutting tag is missing or invalid", **context,
            ))
        if rating.register_sufficiency is None or rating.taxonomy_fit is None:
            findings.append(QCFinding(
                "fatal", "missing_diagnostic", "Sufficiency or taxonomy fit is missing", **context,
            ))
        if item.confidence is None:
            findings.append(QCFinding(
                "fatal", "invalid_confidence", "Confidence is missing or unrecognised", **context,
            ))
        if _integer(raw, "sc_blind_decl") != 1:
            findings.append(QCFinding(
                "query_required", "blind_declaration_not_confirmed",
                "Permitted-evidence declaration was not confirmed", **context,
            ))
        exposure = _integer(raw, "sc_exposure")
        if exposure not in {0, 1}:
            findings.append(QCFinding(
                "fatal", "invalid_exposure_response", "Exposure response is missing or invalid", **context,
            ))
        elif exposure == 1:
            findings.append(QCFinding(
                "warning_interpretable", "reported_prohibited_exposure",
                "Coder reported accidental exposure; review the restricted note during debrief",
                **context,
            ))
            if not _value(raw, "sc_exposure_note"):
                findings.append(QCFinding(
                    "query_required", "missing_exposure_note",
                    "Exposure was reported but its required note is missing", **context,
                ))

        issues = rating.taxonomy_issues
        if rating.taxonomy_fit in {"Partial Fit", "No Fit"} and not issues:
            findings.append(QCFinding(
                "query_required", "missing_required_taxonomy_issue",
                "Partial Fit or No Fit has no taxonomy-issue response", **context,
            ))
        if rating.taxonomy_fit == "Fit" and issues:
            findings.append(QCFinding(
                "query_required", "hidden_taxonomy_issue_selected",
                "Taxonomy issue is selected when fit should hide the field", **context,
            ))
        if "None" in issues:
            severity = "warning_interpretable" if issues == {"None"} else "query_required"
            findings.append(QCFinding(
                severity, "candidate_0_3_none_taxonomy_issue",
                "Historical candidate-0.3 recorded the known incoherent None issue option",
                **context,
            ))
        if "Other" in issues and not item.note_present:
            findings.append(QCFinding(
                "query_required", "other_taxonomy_issue_without_note",
                "Historical Other taxonomy issue has no explanatory note", **context,
            ))
        if item.note_triggered and not item.note_present:
            findings.append(QCFinding(
                "query_required", "missing_triggered_note",
                "A conditional explanatory note trigger is present but the note is blank",
                **context,
            ))
        if instrument_version == "redcap-candidate-0.3" and (
            _integer(raw, "sc_taxonomy_fit") not in FIT_CODES[instrument_version]
            or any(
                _value(raw, f"sc_tax_issue___{code}") == "1"
                for code in range(1, 7) if code not in ISSUE_CODES[instrument_version]
            )
        ):
            findings.append(QCFinding(
                "fatal", "historical_code_mismatch",
                "Response does not conform to the candidate-0.3 code map", **context,
            ))
    return tuple(findings)


def _qc_status_for_assignment(
    assignment: PilotDecodedAssignment, findings: Sequence[QCFinding]
) -> str:
    relevant = [
        finding for finding in findings
        if finding.assignment_id == assignment.decoded.assignment_id
    ]
    for severity in reversed(SEVERITIES):
        if any(item.severity == severity for item in relevant):
            return severity
    return "pass"


def _metadata(
    source_path: Path,
    source_bytes: bytes,
    rows: Sequence[Mapping[str, str]],
    *,
    instrument_version: str,
    head: str,
    command: str,
    root: Path,
) -> dict[str, object]:
    match = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4})", source_path.name)
    export_timestamp = ""
    if match:
        export_timestamp = (
            f"{match.group(1)} {match.group(2)[:2]}:{match.group(2)[2:]} "
            "(filename; Europe/London local time)"
        )
    headers = list(rows[0]) if rows else []
    email_pattern = re.compile(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}")
    email_like = sum(
        bool(email_pattern.search(str(value))) for row in rows for value in row.values()
    )
    note_count = sum(bool(_value(row, "sc_note")) for row in rows)
    return {
        "source": {
            "repository_relative_path": _repo_relative(source_path, root),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
            "byte_size": len(source_bytes),
            "filename_export_timestamp": export_timestamp,
            "encoding": "utf-8-sig" if source_bytes.startswith(b"\xef\xbb\xbf") else "utf-8",
            "csv_rows": len(rows),
            "csv_columns": len(headers),
            "headers": headers,
            "detected_instrument_version": instrument_version,
        },
        "analysis": {
            "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "repository_head": head,
            "analysis_command": command,
            "code_path": "analysis/validation/run_pilot_analysis.py",
            "formal_validation_metrics": False,
            "model_outputs_initially_hidden": True,
        },
        "sensitivity": {
            "personal_name_or_email_headers_detected": False,
            "email_like_cells_detected": email_like,
            "free_text_note_field_present": "sc_note" in headers,
            "nonempty_free_text_notes": note_count,
            "hidden_administrative_identifiers_present": True,
            "raw_export_commit_recommendation": (
                "restricted/local only pending explicit disclosure review; source is currently tracked"
            ),
        },
        "generated_artifact_commit_recommendations": {
            "pilot_export_metadata.yaml": "safe to commit after sensitivity review",
            "pilot_assignment_qc.csv": "safe only after review of hidden pseudonymous identifiers",
            "pilot_qc_report.md": "safe to commit after sensitivity review",
            "pilot_analysis_ready.csv": "generated and reproducible; safe after disclosure review",
            "pilot_record_agreement.csv": "generated and reproducible; safe after disclosure review",
            "pilot_pairwise_agreement.csv": "generated and reproducible; safe to commit",
            "pilot_metric_summary.csv": "generated and reproducible; safe to commit",
            "pilot_diagnostic_item_summary.csv": "generated and reproducible; safe after disclosure review",
            "pilot_issue_candidates.csv": "safe only after debrief and disclosure review",
            "pilot_agreement_report.md": "safe to commit after debrief and disclosure review",
        },
    }


def _render_qc_report(
    mapping: AssignmentMappingResult,
    findings: Sequence[QCFinding],
    *, instrument_version: str,
) -> str:
    invalid_codes = sum(item.code in {"decode_failure", "historical_code_mismatch"} for item in findings)
    required_failures = sum(
        item.code.startswith("missing_") or item.code in {
            "incomplete_response", "invalid_binary_tag", "invalid_confidence",
        }
        for item in findings
    )
    ambiguous = sum(row["mapping_status"] == "ambiguous" for row in mapping.rows)
    fatal = any(item.severity == "fatal" for item in findings)
    lines = [
        "# Pilot structural and instrument QC",
        "",
        f"Detected instrument version: `{instrument_version}`",
        "",
        f"- Expected assignments: {EXPECTED_ASSIGNMENTS}",
        f"- Observed assignments: {mapping.observed_assignments}",
        f"- Unique assignments: {mapping.unique_assignments}",
        f"- Unique records: {mapping.unique_records}",
        f"- Unique coders: {sum(count > 0 for count in mapping.coder_counts.values())}",
        f"- C01 assignments: {mapping.coder_counts.get('C01', 0)}",
        f"- C02 assignments: {mapping.coder_counts.get('C02', 0)}",
        f"- C03 assignments: {mapping.coder_counts.get('C03', 0)}",
        f"- Missing coder-record combinations: {len(mapping.missing_combinations)}",
        f"- Duplicate coder-record combinations: {len(mapping.duplicate_combinations)}",
        f"- Ambiguous mappings: {ambiguous}",
        f"- Invalid response codes: {invalid_codes}",
        f"- Required-field failures: {required_failures}",
        f"- Fatal QC status: {'FAIL' if fatal else 'PASS'}",
        "",
        "The mapping uses the explicit hidden `reviewer_id` field. Row order, timestamps,",
        "display order, and response order are not used to infer coder identity.",
        "",
        "Static instrument documentation marks administrative sample/model fields hidden and",
        "read-only. Export contents alone cannot prove the historical live UI rendering.",
    ]
    nonpass = [item for item in findings if item.severity != "pass"]
    lines.extend(["", "## Findings", ""])
    if not nonpass:
        lines.append("No structural, mapping, decoding, or instrument-coherence findings.")
    else:
        lines.extend([
            "| Severity | Code | Record | Coder | Detail |",
            "| --- | --- | --- | --- | --- |",
        ])
        for item in nonpass:
            detail = item.detail.replace("|", "/")
            lines.append(
                f"| {item.severity} | {item.code} | {item.record_id} | "
                f"{item.coder_id} | {detail} |"
            )
    return "\n".join(lines) + "\n"


def _ready_rows(
    assignments: Sequence[PilotDecodedAssignment], findings: Sequence[QCFinding]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in sorted(
        assignments, key=lambda value: (value.decoded.record_id, value.decoded.reviewer_id)
    ):
        rating = item.decoded.rating
        rows.append({
            "record_id": item.decoded.record_id,
            "coder_id": item.decoded.reviewer_id.upper(),
            "instrument_version": item.decoded.instrument_version,
            "research_domains": _label_text(rating.domains or ()),
            "analytical_purposes": _label_text(rating.purposes or ()),
            "covid_tag": rating.covid_tag,
            "equity_tag": rating.equity_tag,
            "register_sufficiency": rating.register_sufficiency,
            "taxonomy_fit": rating.taxonomy_fit,
            "taxonomy_issues": _label_text(rating.taxonomy_issues),
            "confidence": item.confidence,
            "response_complete": int(rating.complete),
            "note_triggered": int(item.note_triggered),
            "note_present": int(item.note_present),
            "qc_status": _qc_status_for_assignment(item, findings),
        })
    return rows


def _set_outputs(
    assignments: Sequence[PilotDecodedAssignment], dimension: str
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], object]:
    attribute = "domains" if dimension == "Research Domains" else "purposes"
    ratings = [
        ScratchSetRating(
            item.decoded.record_id,
            item.decoded.reviewer_id.upper(),
            frozenset(getattr(item.decoded.rating, attribute) or ()),
        )
        for item in assignments
    ]
    matrix = complete_case_three_coder_matrix(ratings)
    record_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    patterns: Counter[str] = Counter()
    for record in matrix:
        agreement = analyse_set_record(record)
        patterns[agreement.pattern] += 1
        pair = {(item.left_coder, item.right_coder): item for item in agreement.pairwise}
        differences = agreement.majority_differences
        record_rows.append({
            "record_id": record.record_id,
            "classification_dimension": dimension,
            "C01_set": _label_text(record.coder_sets["C01"]),
            "C02_set": _label_text(record.coder_sets["C02"]),
            "C03_set": _label_text(record.coder_sets["C03"]),
            "complete_set_pattern": agreement.pattern,
            "C01_C02_exact": int(pair[("C01", "C02")].exact),
            "C01_C03_exact": int(pair[("C01", "C03")].exact),
            "C02_C03_exact": int(pair[("C02", "C03")].exact),
            "C01_C02_jaccard": _float(float(pair[("C01", "C02")].jaccard)),
            "C01_C03_jaccard": _float(float(pair[("C01", "C03")].jaccard)),
            "C02_C03_jaccard": _float(float(pair[("C02", "C03")].jaccard)),
            "majority_supported_labels": _label_text(agreement.majority_supported),
            "C01_difference": differences["C01"].classification,
            "C01_extra_labels": _label_text(differences["C01"].extra_labels),
            "C01_missing_labels": _label_text(differences["C01"].missing_labels),
            "C02_difference": differences["C02"].classification,
            "C02_extra_labels": _label_text(differences["C02"].extra_labels),
            "C02_missing_labels": _label_text(differences["C02"].missing_labels),
            "C03_difference": differences["C03"].classification,
            "C03_extra_labels": _label_text(differences["C03"].extra_labels),
            "C03_missing_labels": _label_text(differences["C03"].missing_labels),
            "majority_supported_count": len(agreement.majority_supported),
            "purpose_majority_exceeds_two": int(
                dimension == "Analytical Purposes" and len(agreement.majority_supported) > 2
            ),
            "all_sets_distinct_with_nonempty_majority": int(
                agreement.pattern == "all_sets_distinct" and bool(agreement.majority_supported)
            ),
        })
    pairwise_rows = [
        {
            "classification_dimension": dimension,
            "coder_pair": f"{item.left_coder}-{item.right_coder}",
            "denominator": item.denominator,
            "exact_count": item.exact_count,
            "exact_proportion": _float(item.exact_proportion),
            "mean_jaccard": _float(item.mean_jaccard),
            "median_jaccard": _float(item.median_jaccard),
            "minimum_jaccard": _float(item.minimum_jaccard),
            "maximum_jaccard": _float(item.maximum_jaccard),
        }
        for item in summarise_pairwise(matrix)
    ]
    alpha = three_rater_masi_alpha(matrix)
    metric_rows.append({
        "metric": "three_rater_krippendorff_alpha_masi",
        "classification_dimension": dimension,
        "category": "",
        "point_estimate": _float(alpha.alpha),
        "valid": int(alpha.valid),
        "undefined_reason": alpha.undefined_reason or "",
        "numerator": "",
        "denominator": alpha.number_of_units,
        "descriptive_pilot_statistic": 1,
        "notes": "No bootstrap; descriptive three-coder pilot statistic",
    })
    for pattern in ("unanimous", "two_vs_one", "all_sets_distinct"):
        metric_rows.append({
            "metric": "complete_set_pattern_count",
            "classification_dimension": dimension,
            "category": pattern,
            "point_estimate": patterns[pattern],
            "valid": 1,
            "undefined_reason": "",
            "numerator": patterns[pattern],
            "denominator": len(matrix),
            "descriptive_pilot_statistic": 1,
            "notes": "Complete-set equality pattern; not labelwise majority",
        })
    return record_rows, pairwise_rows, metric_rows, matrix


def _group_assignments(
    assignments: Sequence[PilotDecodedAssignment],
) -> dict[str, dict[str, PilotDecodedAssignment]]:
    grouped: dict[str, dict[str, PilotDecodedAssignment]] = defaultdict(dict)
    for item in assignments:
        grouped[item.decoded.record_id][item.decoded.reviewer_id.upper()] = item
    return dict(grouped)


def _diagnostic_outputs(
    assignments: Sequence[PilotDecodedAssignment],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    grouped = _group_assignments(assignments)
    diagnostic_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []

    categorical = {
        "register_sufficiency": lambda item: item.decoded.rating.register_sufficiency,
        "taxonomy_fit": lambda item: item.decoded.rating.taxonomy_fit,
        "confidence": lambda item: item.confidence,
    }
    for item_name, accessor in categorical.items():
        for coder in EXPECTED_CODERS:
            counts = Counter(accessor(record[coder]) for record in grouped.values())
            for category, count in sorted(counts.items(), key=lambda value: str(value[0])):
                diagnostic_rows.append({
                    "item": item_name,
                    "scope": "coder_frequency",
                    "category": category or "missing",
                    "coder_id": coder,
                    "record_id": "",
                    "count": count,
                    "denominator": len(grouped),
                    "proportion": _float(count / len(grouped)),
                    "majority_or_pattern": "",
                    "details": "",
                })
        for record_id, record in sorted(grouped.items()):
            values = tuple(str(accessor(record[coder]) or "") for coder in EXPECTED_CODERS)
            if any(not value for value in values):
                majority = "missing"
            else:
                majority = majority_diagnostic_rating(values)
            diagnostic_rows.append({
                "item": item_name,
                "scope": "record_majority",
                "category": "",
                "coder_id": "",
                "record_id": record_id,
                "count": "",
                "denominator": 3,
                "proportion": "",
                "majority_or_pattern": majority,
                "details": " | ".join(f"{coder}:{values[i]}" for i, coder in enumerate(EXPECTED_CODERS)),
            })
            if majority == "No majority / split judgement":
                issue_rows.append({
                    "record_id": record_id,
                    "issue_source": "diagnostic_item",
                    "issue_category": f"{item_name}_three_way_split",
                    "observed_pattern": majority,
                    "relevant_coder_ids": "C01 | C02 | C03",
                    "brief_evidence": f"All three {item_name} categories differ",
                    "status": "pending_debrief",
                })

    issue_counts: Counter[tuple[str, str]] = Counter()
    for assignment in assignments:
        coder = assignment.decoded.reviewer_id.upper()
        for issue in assignment.decoded.rating.taxonomy_issues:
            issue_counts[(coder, issue)] += 1
    for (coder, issue), count in sorted(issue_counts.items()):
        diagnostic_rows.append({
            "item": "taxonomy_issue_type",
            "scope": "coder_frequency",
            "category": issue,
            "coder_id": coder,
            "record_id": "",
            "count": count,
            "denominator": len(grouped),
            "proportion": _float(count / len(grouped)),
            "majority_or_pattern": "",
            "details": "Historical candidate-0.3 categories retained without recoding",
        })

    cannot_assess = sum(
        item.decoded.rating.taxonomy_fit == "Cannot assess from register entry"
        for item in assignments
    )
    low_confidence = [item for item in assignments if item.confidence == "Low"]
    triggered = [item for item in assignments if item.note_triggered]
    completed_notes = sum(item.note_present for item in triggered)
    for item_name, count, denominator in (
        ("cannot_assess_from_register_entry", cannot_assess, len(assignments)),
        ("low_confidence_response", len(low_confidence), len(assignments)),
        ("triggered_note_completed", completed_notes, len(triggered)),
    ):
        diagnostic_rows.append({
            "item": item_name,
            "scope": "overall_frequency",
            "category": "",
            "coder_id": "",
            "record_id": "",
            "count": count,
            "denominator": denominator,
            "proportion": _float(count / denominator) if denominator else "",
            "majority_or_pattern": "",
            "details": "",
        })
    for item in low_confidence:
        issue_rows.append({
            "record_id": item.decoded.record_id,
            "issue_source": "confidence",
            "issue_category": "low_confidence_response",
            "observed_pattern": "Low confidence",
            "relevant_coder_ids": item.decoded.reviewer_id.upper(),
            "brief_evidence": "At least one coder recorded low confidence",
            "status": "pending_debrief",
        })

    for tag_name, accessor in (
        ("COVID-19 & Pandemic", lambda item: item.decoded.rating.covid_tag),
        ("Demographic disparities / equity", lambda item: item.decoded.rating.equity_tag),
    ):
        nominal_records: list[dict[str, int | None]] = []
        pair_equal: Counter[tuple[str, str]] = Counter()
        pattern_counts: Counter[str] = Counter()
        for record_id, record in sorted(grouped.items()):
            values = {coder: accessor(record[coder]) for coder in EXPECTED_CODERS}
            nominal_records.append(values)
            positives = sum(value == 1 for value in values.values())
            pattern = (
                "unanimous_positive" if positives == 3 else
                "unanimous_negative" if positives == 0 else
                "two_versus_one_disagreement"
            )
            pattern_counts[pattern] += 1
            diagnostic_rows.append({
                "item": tag_name,
                "scope": "record_pattern",
                "category": "",
                "coder_id": "",
                "record_id": record_id,
                "count": positives,
                "denominator": 3,
                "proportion": _float(positives / 3),
                "majority_or_pattern": pattern,
                "details": " | ".join(f"{coder}:{values[coder]}" for coder in EXPECTED_CODERS),
            })
            for pair in DEFAULT_PAIRS:
                pair_equal[pair] += values[pair[0]] == values[pair[1]]
            if pattern == "two_versus_one_disagreement":
                issue_rows.append({
                    "record_id": record_id,
                    "issue_source": "binary_tag",
                    "issue_category": "tag_disagreement",
                    "observed_pattern": f"{tag_name}: {pattern}",
                    "relevant_coder_ids": "C01 | C02 | C03",
                    "brief_evidence": "Binary tag responses show a two-versus-one split",
                    "status": "pending_debrief",
                })
        for coder in EXPECTED_CODERS:
            count = sum(accessor(record[coder]) == 1 for record in grouped.values())
            diagnostic_rows.append({
                "item": tag_name,
                "scope": "positive_count_by_coder",
                "category": "positive",
                "coder_id": coder,
                "record_id": "",
                "count": count,
                "denominator": len(grouped),
                "proportion": _float(count / len(grouped)),
                "majority_or_pattern": "",
                "details": "",
            })
        for pattern, count in sorted(pattern_counts.items()):
            metric_rows.append({
                "metric": "binary_tag_record_pattern_count",
                "classification_dimension": "Cross-cutting tag",
                "category": f"{tag_name}: {pattern}",
                "point_estimate": count,
                "valid": 1,
                "undefined_reason": "",
                "numerator": count,
                "denominator": len(grouped),
                "descriptive_pilot_statistic": 1,
                "notes": "",
            })
        for left, right in DEFAULT_PAIRS:
            count = pair_equal[(left, right)]
            metric_rows.append({
                "metric": "binary_tag_pairwise_raw_agreement",
                "classification_dimension": "Cross-cutting tag",
                "category": f"{tag_name}: {left}-{right}",
                "point_estimate": _float(count / len(grouped)),
                "valid": 1,
                "undefined_reason": "",
                "numerator": count,
                "denominator": len(grouped),
                "descriptive_pilot_statistic": 1,
                "notes": "",
            })
        alpha = three_rater_nominal_alpha(nominal_records)
        metric_rows.append({
            "metric": "three_rater_krippendorff_alpha_nominal",
            "classification_dimension": "Cross-cutting tag",
            "category": tag_name,
            "point_estimate": _float(alpha.alpha),
            "valid": int(alpha.valid),
            "undefined_reason": alpha.undefined_reason or "",
            "numerator": "",
            "denominator": alpha.number_of_units,
            "descriptive_pilot_statistic": 1,
            "notes": "Undefined values remain undefined; no forced numeric result",
        })
    return diagnostic_rows, metric_rows, issue_rows


def _agreement_issue_candidates(
    record_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    for row in record_rows:
        pattern = str(row["complete_set_pattern"])
        if pattern == "unanimous":
            continue
        classifications = [str(row[f"{coder}_difference"]) for coder in EXPECTED_CODERS]
        relevant = [
            coder for coder, classification in zip(EXPECTED_CODERS, classifications)
            if classification != "matches_majority_supported_set"
        ]
        majority_count = int(row["majority_supported_count"])
        detail = (
            f"Complete sets: {pattern}; labelwise majority-supported count: {majority_count}"
        )
        issues.append({
            "record_id": row["record_id"],
            "issue_source": "set_agreement",
            "issue_category": f"{row['classification_dimension']}_disagreement",
            "observed_pattern": pattern,
            "relevant_coder_ids": " | ".join(relevant or EXPECTED_CODERS),
            "brief_evidence": detail,
            "status": "pending_debrief",
        })
        if int(row["purpose_majority_exceeds_two"]):
            issues.append({
                "record_id": row["record_id"],
                "issue_source": "labelwise_majority",
                "issue_category": "purpose_majority_exceeds_two",
                "observed_pattern": "More than two majority-supported purposes",
                "relevant_coder_ids": "C01 | C02 | C03",
                "brief_evidence": "Diagnostic majority set exceeds the respondent-level maximum",
                "status": "pending_debrief",
            })
    return issues


def _qc_issue_candidates(findings: Sequence[QCFinding]) -> list[dict[str, object]]:
    return [
        {
            "record_id": item.record_id,
            "issue_source": "instrument_qc",
            "issue_category": item.code,
            "observed_pattern": item.severity,
            "relevant_coder_ids": item.coder_id,
            "brief_evidence": item.detail,
            "status": "pending_debrief",
        }
        for item in findings if item.severity in {"warning_interpretable", "query_required"}
    ]


def _report(
    *,
    source_relative: str,
    mapping: AssignmentMappingResult,
    findings: Sequence[QCFinding],
    pairwise_rows: Sequence[Mapping[str, object]],
    metric_rows: Sequence[Mapping[str, object]],
    diagnostic_rows: Sequence[Mapping[str, object]],
    issue_rows: Sequence[Mapping[str, object]],
) -> str:
    def alpha_for(dimension: str) -> Mapping[str, object]:
        return next(
            row for row in metric_rows
            if row["metric"] == "three_rater_krippendorff_alpha_masi"
            and row["classification_dimension"] == dimension
        )

    def majority_counts(item: str) -> Counter[str]:
        return Counter(
            str(row["majority_or_pattern"])
            for row in diagnostic_rows
            if row["item"] == item and row["scope"] == "record_majority"
        )

    debrief_records = sorted({
        str(row["record_id"]) for row in issue_rows if row["record_id"]
    })

    lines = [
        "# Three-coder pilot agreement report",
        "",
        "## Source and QC",
        "",
        f"Source: `{source_relative}`",
        f"Mapping: {mapping.unique_assignments} unique assignments, "
        f"{mapping.unique_records} records, three explicit hidden reviewer IDs.",
        "The complete 10 × 3 Cartesian mapping passed. No coder identity was inferred",
        "from row order, timestamps, display order, or response order.",
        "",
        f"QC findings: {sum(item.severity == 'warning_interpretable' for item in findings)} "
        "interpretable warnings and "
        f"{sum(item.severity == 'query_required' for item in findings)} debrief queries; "
        "no fatal findings.",
        "",
        "## Research Domains and Analytical Purposes",
        "",
    ]
    for dimension in ("Research Domains", "Analytical Purposes"):
        lines.append(f"### {dimension}")
        lines.append("")
        alpha = alpha_for(dimension)
        if int(alpha["valid"]):
            lines.append(f"Descriptive three-rater MASI alpha: {alpha['point_estimate']}.")
        else:
            lines.append(f"Descriptive three-rater MASI alpha: undefined ({alpha['undefined_reason']}).")
        patterns = {
            str(row["category"]): int(row["numerator"])
            for row in metric_rows
            if row["metric"] == "complete_set_pattern_count"
            and row["classification_dimension"] == dimension
        }
        lines.append(
            "Complete-set patterns: "
            f"{patterns.get('unanimous', 0)} unanimous, "
            f"{patterns.get('two_vs_one', 0)} two-versus-one, and "
            f"{patterns.get('all_sets_distinct', 0)} all sets distinct."
        )
        lines.append("")
        lines.extend([
            "| Coder pair | Exact agreement | Mean Jaccard | Median | Range |",
            "| --- | ---: | ---: | ---: | ---: |",
        ])
        for row in pairwise_rows:
            if row["classification_dimension"] != dimension:
                continue
            lines.append(
                f"| {row['coder_pair']} | {row['exact_count']}/{row['denominator']} "
                f"({row['exact_proportion']}) | {row['mean_jaccard']} | "
                f"{row['median_jaccard']} | {row['minimum_jaccard']}–{row['maximum_jaccard']} |"
            )
        lines.append("")

    lines.extend(["## Cross-cutting tags", ""])
    for row in metric_rows:
        if row["metric"] == "three_rater_krippendorff_alpha_nominal":
            value = row["point_estimate"] if int(row["valid"]) else f"undefined ({row['undefined_reason']})"
            lines.append(f"- {row['category']}: descriptive nominal alpha {value}.")

    for tag_name in ("COVID-19 & Pandemic", "Demographic disparities / equity"):
        patterns = {
            str(row["category"]).split(": ", 1)[1]: int(row["numerator"])
            for row in metric_rows
            if row["metric"] == "binary_tag_record_pattern_count"
            and str(row["category"]).startswith(tag_name + ": ")
        }
        lines.append(
            f"- {tag_name}: {patterns.get('unanimous_positive', 0)} unanimous positive, "
            f"{patterns.get('unanimous_negative', 0)} unanimous negative, and "
            f"{patterns.get('two_versus_one_disagreement', 0)} two-versus-one disagreements."
        )

    low = next(
        (row for row in diagnostic_rows if row["item"] == "low_confidence_response"), None
    )
    notes = next(
        (row for row in diagnostic_rows if row["item"] == "triggered_note_completed"), None
    )
    sufficiency = majority_counts("register_sufficiency")
    taxonomy_fit = majority_counts("taxonomy_fit")
    confidence = majority_counts("confidence")
    finding_codes = Counter(
        item.code for item in findings
        if item.severity in {"warning_interpretable", "query_required"}
    )
    lines.extend([
        "",
        "## Diagnostic and debrief signals",
        "",
        f"- Low-confidence coder responses: {low['count']}/{low['denominator']}." if low else "",
        f"- Triggered explanatory notes completed: {notes['count']}/{notes['denominator']}." if notes else "",
        "- Record-majority sufficiency: " + ", ".join(
            f"{category}={count}" for category, count in sorted(sufficiency.items())
        ) + ".",
        "- Record-majority taxonomy fit: " + ", ".join(
            f"{category}={count}" for category, count in sorted(taxonomy_fit.items())
        ) + ".",
        "- Record-majority confidence: " + ", ".join(
            f"{category}={count}" for category, count in sorted(confidence.items())
        ) + ".",
        f"- Candidate debrief rows: {len(issue_rows)} across "
        f"{len(debrief_records)} records.",
        "- Records recommended for debrief: " + ", ".join(debrief_records) + ".",
        "- Instrument/workflow findings: " + (
            ", ".join(f"{code}={count}" for code, count in sorted(finding_codes.items()))
            if finding_codes else "none"
        ) + ".",
        "- Candidate issues are prompts for debrief, not automated diagnoses or coder errors.",
        "",
        "## Interpretation limits",
        "",
        "This is a descriptive instrument/workflow pilot with only 10 records. Labelwise",
        "two-of-three support is diagnostic aggregation, not a gold standard. The report",
        "contains no production-model or GPT-5.5 labels, agreement strata, instructor keys,",
        "replacement panels, performance estimates, bootstrap intervals, significance tests,",
        "formal adjudication selection, release triggers, or register-wide inference.",
    ])
    return "\n".join(line for line in lines if line is not None) + "\n"


def run_pilot_analysis(
    input_path: Path,
    output_dir: Path,
    *,
    exclusion_list: Path,
    explicit_instrument_version: str | None = None,
    command: str = "",
    repository_root: Path = REPOSITORY_ROOT,
) -> int:
    validate_pilot_safety_configuration(
        formal_validation_metrics=FORMAL_VALIDATION_METRICS,
        model_outputs_initially_hidden=MODEL_OUTPUTS_INITIALLY_HIDDEN,
    )
    input_path = input_path.resolve()
    exclusion_list = exclusion_list.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_bytes = input_path.read_bytes()
    try:
        source_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PilotAnalysisError("Pilot export is not valid UTF-8/UTF-8-SIG") from exc
    rows = load_wide_export(input_path)
    instrument_version = detect_instrument_version(
        rows, explicit_version=explicit_instrument_version
    )
    head = _git_head(repository_root)
    metadata = _metadata(
        input_path, source_bytes, rows, instrument_version=instrument_version,
        head=head, command=command, root=repository_root,
    )
    (output_dir / "pilot_export_metadata.yaml").write_text(
        yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    mapping = build_assignment_mapping(rows)
    assignment_rows = list(mapping.rows)
    validate_output_row_schema(ASSIGNMENT_QC_COLUMNS, assignment_rows)
    _write_csv(output_dir / "pilot_assignment_qc.csv", ASSIGNMENT_QC_COLUMNS, assignment_rows)

    decoded, decode_findings = decode_pilot_assignments(rows, instrument_version)
    frozen_pilot_ids = load_frozen_pilot_ids(exclusion_list)
    findings = [*mapping.findings, *decode_findings]
    if len(decoded) == len(rows):
        findings.extend(instrument_qc(
            decoded,
            frozen_pilot_ids=frozen_pilot_ids,
            instrument_version=instrument_version,
        ))
    else:
        findings.append(QCFinding(
            "fatal", "incomplete_decode",
            f"Only {len(decoded)} of {len(rows)} assignments decoded",
        ))

    qc_text = _render_qc_report(mapping, findings, instrument_version=instrument_version)
    (output_dir / "pilot_qc_report.md").write_text(qc_text, encoding="utf-8")
    if any(item.severity == "fatal" for item in findings):
        return 2

    ready_rows = _ready_rows(decoded, findings)
    validate_output_row_schema(READY_COLUMNS, ready_rows)
    _write_csv(output_dir / "pilot_analysis_ready.csv", READY_COLUMNS, ready_rows)

    record_rows: list[dict[str, object]] = []
    pairwise_rows: list[dict[str, object]] = []
    metric_rows: list[dict[str, object]] = [{
        "metric": "valid_coder_record_responses",
        "classification_dimension": "All scratch responses",
        "category": "",
        "point_estimate": len(decoded),
        "valid": 1,
        "undefined_reason": "",
        "numerator": len(decoded),
        "denominator": EXPECTED_ASSIGNMENTS,
        "descriptive_pilot_statistic": 1,
        "notes": "Completed, mapped, decodable pilot responses",
    }]
    for dimension in ("Research Domains", "Analytical Purposes"):
        dimension_records, dimension_pairs, dimension_metrics, _ = _set_outputs(
            decoded, dimension
        )
        record_rows.extend(dimension_records)
        pairwise_rows.extend(dimension_pairs)
        metric_rows.extend(dimension_metrics)

    diagnostic_rows, tag_metrics, diagnostic_issues = _diagnostic_outputs(decoded)
    metric_rows.extend(tag_metrics)
    issue_rows = [
        *_agreement_issue_candidates(record_rows),
        *diagnostic_issues,
        *_qc_issue_candidates(findings),
    ]
    issue_rows.sort(key=lambda row: (
        str(row["record_id"]), str(row["issue_source"]), str(row["issue_category"]),
        str(row["relevant_coder_ids"]),
    ))

    for columns, output_rows, filename in (
        (RECORD_AGREEMENT_COLUMNS, record_rows, "pilot_record_agreement.csv"),
        (PAIRWISE_COLUMNS, pairwise_rows, "pilot_pairwise_agreement.csv"),
        (METRIC_COLUMNS, metric_rows, "pilot_metric_summary.csv"),
        (DIAGNOSTIC_COLUMNS, diagnostic_rows, "pilot_diagnostic_item_summary.csv"),
        (ISSUE_COLUMNS, issue_rows, "pilot_issue_candidates.csv"),
    ):
        validate_output_row_schema(columns, output_rows)
        _write_csv(output_dir / filename, columns, output_rows)

    report = _report(
        source_relative=_repo_relative(input_path, repository_root),
        mapping=mapping,
        findings=findings,
        pairwise_rows=pairwise_rows,
        metric_rows=metric_rows,
        diagnostic_rows=diagnostic_rows,
        issue_rows=issue_rows,
    )
    (output_dir / "pilot_agreement_report.md").write_text(report, encoding="utf-8")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exclusion-list", type=Path, default=DEFAULT_EXCLUSION_LIST)
    parser.add_argument("--instrument-version")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = args.input if args.input.is_absolute() else REPOSITORY_ROOT / args.input
    output_dir = args.output_dir if args.output_dir.is_absolute() else REPOSITORY_ROOT / args.output_dir
    exclusion_list = (
        args.exclusion_list if args.exclusion_list.is_absolute()
        else REPOSITORY_ROOT / args.exclusion_list
    )
    command = " ".join([
        sys.executable, "-m", "analysis.validation.run_pilot_analysis",
        *(argv or sys.argv[1:]),
    ])
    try:
        result = run_pilot_analysis(
            input_path,
            output_dir,
            exclusion_list=exclusion_list,
            explicit_instrument_version=args.instrument_version,
            command=command,
        )
    except (OSError, PilotAnalysisError, ScratchAgreementError, subprocess.CalledProcessError) as exc:
        print(f"pilot analysis error: {exc}", file=sys.stderr)
        return 2
    if result:
        print("Pilot structural QC failed; metadata, mapping, and QC report were written.", file=sys.stderr)
    else:
        print(f"Pilot analysis written to {output_dir}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
