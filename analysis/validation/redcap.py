"""Raw-code parser for synthetic rows shaped like a wide REDCap export.

The parser does not connect to REDCap and does not infer coder, stratum,
difficulty, or model information from assignment or Record IDs.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .schema import CoderRating, ModelRating, ProjectRatings


DOMAIN_CODES = {
    1: "Labour Market & Employment",
    2: "Education & Skills",
    3: "Health & Social Care",
    4: "Crime & Justice",
    5: "Business & Productivity",
    6: "Poverty, Wealth & Living Standards",
    7: "Housing & Planning",
    8: "Migration & Demographics",
    9: "Environment & Agriculture",
    10: "Public Finance & Taxation",
    11: "Data Infrastructure & Methodology",
    12: "Unclear from Register Entry",
}
PURPOSE_CODES = {
    1: "Descriptive Monitoring",
    2: "Outcome Tracking",
    3: "Life-Course / Trajectory Analysis",
    4: "Service Interaction / Systems Analysis",
    5: "Policy Evaluation / Impact Analysis",
    6: "Risk Prediction / Early Identification",
    7: "Methodological / Infrastructure Research",
    8: "Unclear from Register Entry",
}
SUFFICIENCY_CODES = {1: "Sufficient", 2: "Partially sufficient", 3: "Insufficient"}
FIT_CODES = {
    "redcap-candidate-0.3": {1: "Fit", 2: "Partial Fit", 3: "No Fit"},
    "redcap-candidate-0.4": {
        1: "Fit",
        2: "Partial Fit",
        3: "No Fit",
        4: "Cannot assess from register entry",
    },
}
ISSUE_CODES = {
    "redcap-candidate-0.3": {
        1: "Missing category",
        2: "Ambiguous/overlapping categories",
        3: "Too broad",
        4: "Too narrow",
        5: "Other",
        6: "None",
    },
    "redcap-candidate-0.4": {
        1: "Missing or inadequately represented category",
        2: "Ambiguous or overlapping category boundaries",
        5: "Other taxonomy problem",
    },
}
SAMPLE_SET_CODES = {1: "random_baseline", 2: "hard_case", 3: "owner_review", 4: "pilot"}


class ExportParseError(ValueError):
    pass


@dataclass(frozen=True)
class DecodedScratchAssignment:
    assignment_id: str
    reviewer_id: str
    record_id: str
    sample_set: str
    validation_included: bool
    instrument_version: str
    rating: CoderRating


@dataclass(frozen=True)
class ParsedScratchExport:
    projects: tuple[ProjectRatings, ...]
    excluded_assignment_count: int
    decoded_assignment_count: int


def load_wide_export(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _integer(value: object, field: str, *, allow_blank: bool = False) -> int | None:
    if value is None or str(value).strip() == "":
        if allow_blank:
            return None
        raise ExportParseError(f"Missing required raw-code field: {field}")
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise ExportParseError(f"Malformed integer in {field}: {value!r}") from exc
    return parsed


def _binary(value: object, field: str, *, allow_blank: bool = False) -> int | None:
    parsed = _integer(value, field, allow_blank=allow_blank)
    if parsed is None:
        return None
    if parsed not in (0, 1):
        raise ExportParseError(f"Malformed binary in {field}: {value!r}")
    return parsed


def _checkbox_set(
    row: Mapping[str, object], prefix: str, code_map: Mapping[int, str], *, required: bool
) -> frozenset[str] | None:
    unknown_selected = [
        key
        for key, value in row.items()
        if key.startswith(prefix + "___")
        and key[len(prefix) + 3 :].isdigit()
        and int(key[len(prefix) + 3 :]) not in code_map
        and str(value).strip() == "1"
    ]
    if unknown_selected:
        raise ExportParseError(f"Unknown selected checkbox columns for {prefix}: {unknown_selected}")
    raw_values = [row.get(f"{prefix}___{code}", "") for code in code_map]
    if all(value is None or str(value).strip() == "" for value in raw_values):
        return None if required else frozenset()
    selected = {
        label
        for code, label in code_map.items()
        if _binary(row.get(f"{prefix}___{code}", 0), f"{prefix}___{code}") == 1
    }
    return frozenset(selected)


def decode_scratch_row(row: Mapping[str, object]) -> DecodedScratchAssignment:
    """Decode one raw-code row, including decode-only candidate-0.3 choices."""

    version = str(row.get("instrument_ver", "")).strip()
    if version not in FIT_CODES:
        raise ExportParseError(f"Unknown instrument version: {version!r}")
    assignment_id = str(row.get("assignment_id", "")).strip()
    reviewer_id = str(row.get("reviewer_id", "")).strip()
    record_id = str(row.get("source_record_id", ""))
    if not assignment_id or not reviewer_id or not record_id or record_id != record_id.strip():
        raise ExportParseError("assignment_id, reviewer_id and a whitespace-clean source_record_id are required")
    review_stream = _integer(row.get("review_stream"), "review_stream")
    if review_stream != 1:
        raise ExportParseError(f"Not a scratch-coder row: review_stream={review_stream}")
    sample_code = _integer(row.get("sample_set"), "sample_set")
    if sample_code not in SAMPLE_SET_CODES:
        raise ExportParseError(f"Unknown sample_set raw code: {sample_code}")
    included = _binary(row.get("validation_included"), "validation_included") == 1
    fit_code = _integer(row.get("sc_taxonomy_fit"), "sc_taxonomy_fit", allow_blank=True)
    if fit_code is not None and fit_code not in FIT_CODES[version]:
        raise ExportParseError(f"Unknown sc_taxonomy_fit code {fit_code} for {version}")
    sufficiency_code = _integer(row.get("sc_sufficiency"), "sc_sufficiency", allow_blank=True)
    if sufficiency_code is not None and sufficiency_code not in SUFFICIENCY_CODES:
        raise ExportParseError(f"Unknown sc_sufficiency code: {sufficiency_code}")
    issues = _checkbox_set(row, "sc_tax_issue", ISSUE_CODES[version], required=False)
    rating = CoderRating(
        reviewer_id=reviewer_id,
        domains=_checkbox_set(row, "sc_domains", DOMAIN_CODES, required=True),
        purposes=_checkbox_set(row, "sc_purposes", PURPOSE_CODES, required=True),
        equity_tag=_binary(row.get("sc_equity"), "sc_equity", allow_blank=True),
        covid_tag=_binary(row.get("sc_covid"), "sc_covid", allow_blank=True),
        register_sufficiency=SUFFICIENCY_CODES.get(sufficiency_code),
        taxonomy_fit=FIT_CODES[version].get(fit_code),
        taxonomy_issues=issues or frozenset(),
        explanatory_note=(str(row.get("sc_note", "")).strip() or None),
        complete=_integer(row.get("scratch_coder_complete"), "scratch_coder_complete", allow_blank=True) == 2,
        response_valid=True,
    )
    return DecodedScratchAssignment(
        assignment_id=assignment_id,
        reviewer_id=reviewer_id,
        record_id=record_id,
        sample_set=SAMPLE_SET_CODES[sample_code],
        validation_included=included,
        instrument_version=version,
        rating=rating,
    )


def parse_scratch_export_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    model_by_record: Mapping[str, ModelRating],
    coder_slot_by_reviewer: Mapping[str, str],
) -> ParsedScratchExport:
    """Build project panels from raw rows using an explicit reviewer-to-slot map.

    Pilot, owner-review, and administratively excluded rows are decoded for
    schema compatibility but never enter returned validation panels.
    """

    decoded: list[DecodedScratchAssignment] = []
    excluded = 0
    assignment_records: dict[str, str] = {}
    reviewer_records: set[tuple[str, str]] = set()
    for row in rows:
        if str(row.get("review_stream", "")).strip() != "1":
            continue
        item = decode_scratch_row(row)
        prior_record = assignment_records.setdefault(item.assignment_id, item.record_id)
        if prior_record != item.record_id:
            raise ExportParseError(
                f"Assignment {item.assignment_id} has inconsistent Record IDs: {prior_record}, {item.record_id}"
            )
        reviewer_record = (item.reviewer_id, item.record_id)
        if reviewer_record in reviewer_records:
            raise ExportParseError(f"Duplicate reviewer-project assignment: {reviewer_record}")
        reviewer_records.add(reviewer_record)
        decoded.append(item)
        if not item.validation_included or item.sample_set not in {"random_baseline", "hard_case"}:
            excluded += 1

    grouped: dict[str, list[DecodedScratchAssignment]] = {}
    for item in decoded:
        if not item.validation_included or item.sample_set not in {"random_baseline", "hard_case"}:
            continue
        grouped.setdefault(item.record_id, []).append(item)

    projects: list[ProjectRatings] = []
    for record_id in sorted(grouped):
        items = grouped[record_id]
        sample_sets = {item.sample_set for item in items}
        versions = {item.instrument_version for item in items}
        if len(sample_sets) != 1 or len(versions) != 1:
            raise ExportParseError(f"Inconsistent project metadata for {record_id}")
        slots: dict[str, CoderRating] = {}
        for item in items:
            try:
                slot = coder_slot_by_reviewer[item.reviewer_id]
            except KeyError as exc:
                raise ExportParseError(
                    f"Reviewer {item.reviewer_id!r} has no explicit coder-slot mapping"
                ) from exc
            if slot not in {"A", "B", "C"}:
                raise ExportParseError(f"Invalid coder slot for {item.reviewer_id!r}: {slot!r}")
            if slot in slots:
                raise ExportParseError(f"Multiple reviewers mapped to coder slot {slot} for {record_id}")
            slots[slot] = item.rating
        projects.append(
            ProjectRatings(
                record_id=record_id,
                sample_set=next(iter(sample_sets)),
                coder_a=slots.get("A"),
                coder_b=slots.get("B"),
                coder_c=slots.get("C"),
                model=model_by_record.get(record_id),
                instrument_version=next(iter(versions)),
                validation_included=True,
            )
        )
    return ParsedScratchExport(tuple(projects), excluded, len(decoded))
