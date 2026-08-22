"""Replay the contactability-aware owner sequence for Instruction 8B.

The builder consumes only the frozen 8A candidate/incidence outputs and the
two restricted manual-control tables.  It never performs contactability
searches, reads response/model/adjudication data, or opens reserve artefacts.

Each successful incomplete pass writes an append-only, numbered 8B state
snapshot plus deterministic sequence and offered-coverage diagnostics.  No
production identifier is generated until the registered frame-completion
condition has been reached.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from owner_sampling_frame import assign_production_identifiers


REPO_ROOT = Path(__file__).resolve().parents[2]

INCIDENCE_PATH = REPO_ROOT / (
    "preregistration/post_registration/owner_candidate_frame_8a/"
    "owner_candidate_incidence_deidentified.csv"
)
RESTRICTED_FRAME_PATH = REPO_ROOT / (
    "preregistration_restricted/owner_candidate_frame_8a/"
    "owner_candidate_frame_restricted.csv"
)
DISPOSITIONS_PATH = REPO_ROOT / (
    "preregistration_restricted/owner_candidate_frame_8a/"
    "owner_contactability_dispositions.csv"
)
RECRUITMENT_PATH = REPO_ROOT / (
    "preregistration_restricted/owner_candidate_frame_8a/"
    "owner_recruitment_table.csv"
)
STATE_DIRECTORY = REPO_ROOT / "preregistration_restricted/owner_candidate_frame_8a"
SEQUENCE_LOG_PATH = STATE_DIRECTORY / "owner_sequence_log_8b.csv"
COVERAGE_PATH = STATE_DIRECTORY / "owner_offered_coverage_8b.csv"
IDENTIFIER_METADATA_PATH = STATE_DIRECTORY / "owner_identifier_metadata.json"
ASSIGNMENT_FRAME_PATH = REPO_ROOT / (
    "preregistration/post_registration/owner_candidate_frame_8b/"
    "owner_assignment_frame_8b.csv"
)

SAMPLING_SPECIFICATION = REPO_ROOT / (
    "preregistration/package/04_exclusions_and_sampling/sampling_specification.yaml"
)
SAMPLING_RUNBOOK = REPO_ROOT / (
    "preregistration/package/04_exclusions_and_sampling/official_sampling_runbook.md"
)
CONTACTABILITY_PROCEDURE = REPO_ROOT / (
    "preregistration/post_registration/procedures/"
    "owner_contactability_procedure_v1.1.md"
)
IDENTIFIER_SPECIFICATION = REPO_ROOT / (
    "preregistration/package/04_exclusions_and_sampling/"
    "owner_identifier_specification.yaml"
)

EXPECTED_HASHES = {
    INCIDENCE_PATH: "5c275edb4637a2f702f732064a6a7d0cbfec586beca75a22f5e61f0fe80820e1",
    RESTRICTED_FRAME_PATH: "33538966dbc3bb44d3f76affe3be339368507b969e0ee1268fe97f3dc2ec6a26",
    SAMPLING_SPECIFICATION: "d926d4911f626a72ceab71f2ed37879dbe960f100bf2d5c075812617b63ef63b",
    SAMPLING_RUNBOOK: "9a06fd1dfb09b8ebea7381db14361fcd74318737af3df6a893ce2fd255e3728b",
    CONTACTABILITY_PROCEDURE: "7ebaf22d33bdc509fb34297fcc96761cce8a6a26893093647a8ffe3ba2d036e4",
    IDENTIFIER_SPECIFICATION: "9207e1cef09632e9657519cf966f03fdb39cb570bb27e1a2a88d0bbce3e539bc",
}

DISPOSITION_HEADERS = [
    "candidate_key",
    "sequence_step",
    "disposition",
    "source_reached",
    "url",
    "search_date",
    "elapsed_minutes",
    "note",
]
RECRUITMENT_HEADERS = [
    "candidate_key",
    "name",
    "institution",
    "contact_route",
    "route_source",
    "route_url",
    "date_established",
    "owner_id",
]
SEQUENCE_LOG_HEADERS = [
    "search_step",
    "candidate_key",
    "marginal_coverage",
    "total_eligible_record_count",
    "registered_tie_break_rule",
    "tie_break_applied",
    "primary_tie_size",
    "secondary_tie_size",
    "disposition",
    "outcome",
    "admitted_sequence_position",
    "contactability_adjusted_cumulative_offered_coverage",
]
COVERAGE_HEADERS = [
    "admitted_sequence_position",
    "search_step",
    "candidate_key",
    "marginal_coverage",
    "contactability_adjusted_cumulative_offered_coverage",
    "8a_conditional_offered_coverage_at_same_position",
    "coverage_divergence_8b_minus_8a",
    "coverage_quantity_label",
]
ASSIGNMENT_FRAME_HEADERS = [
    "owner_id",
    "assignment_id",
    "eligible_record_id",
    "owner_sequence_position",
    "recruitment_stage",
    "owner_eligible_record_count",
    "burden_diagnostic",
    "review_instance_status",
]

PERMITTED_DISPOSITIONS = {
    "CONTACTABLE",
    "NOT_FOUND",
    "UNRESOLVED",
    "INELIGIBLE",
}
REGISTERED_TIE_BREAK = (
    "marginal eligible Record-ID gain descending; total eligible Record-ID "
    "count descending; conservative identity key ascending"
)
COMPLETION_CONTACTABLE = 25
SEARCH_CAP = 50
EFFORT_CEILING_MINUTES = 10
BURDEN_THRESHOLD = 10
OWNER_ID_PERMUTATION_SEED = 3409862802234783309
ASSIGNMENT_ID_SEED = 8377163197361553429
PRODUCTION_SEEDS_FIXED_DATE = "2026-08-21"
FIRST_EXPECTED_CANDIDATE = "CAND_83ca90913b53f68a0cdf"
STATE_PATTERN = re.compile(r"owner_sequence_8b_state_pass_(\d{3,})\.json$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def csv_bytes(
    headers: list[str], rows: Iterable[Mapping[str, object]]
) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header, "") for header in headers})
    return buffer.getvalue().encode("utf-8")


def read_csv_exact(path: Path, expected_headers: list[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Required file is missing: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_headers:
            raise ValueError(
                f"Headers differ for {path.relative_to(REPO_ROOT)}: {reader.fieldnames}"
            )
        rows = []
        for row in reader:
            if None in row:
                raise ValueError(f"Malformed CSV row in {path.relative_to(REPO_ROOT)}")
            rows.append({key: str(value or "") for key, value in row.items()})
    return rows


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise ValueError(f"Required file is missing: {path.relative_to(REPO_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path.relative_to(REPO_ROOT)}")
        rows = [{key: str(value or "") for key, value in row.items()} for row in reader]
        return list(reader.fieldnames), rows


def write_csv(path: Path, headers: list[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def verify_frozen_hashes() -> dict[str, str]:
    values: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            raise ValueError(f"Frozen input is missing: {path.relative_to(REPO_ROOT)}")
        actual = sha256(path)
        if actual != expected:
            raise ValueError(
                f"Frozen input hash changed: {path.relative_to(REPO_ROOT)}; "
                f"expected {expected}, found {actual}"
            )
        values[path.relative_to(REPO_ROOT).as_posix()] = actual
    return values


def normalise_name(value: str) -> str:
    # The frozen 8A output already contains typographically normalised names.
    # This second pass only reproduces its whitespace/punctuation identity key.
    return re.sub(r"\s+", " ", value).strip(" \t\r\n,;").casefold()


def candidate_key(identity_key: str) -> str:
    material = ("owner_candidate_frame_v1\0" + identity_key).encode("utf-8")
    return "CAND_" + hashlib.sha256(material).hexdigest()[:20]


def reconstruct_identity_keys(
    candidates: Mapping[str, Mapping[str, str]],
    merge_rows: Iterable[Mapping[str, str]],
    portfolios: Mapping[str, frozenset[str]],
) -> dict[str, str]:
    """Reconstruct the registered conservative key and verify its candidate hash."""

    merge_names: dict[str, set[str]] = defaultdict(set)
    for row in merge_rows:
        key = row["candidate_key"]
        for column in ("source_name_string_a", "source_name_string_b"):
            if row.get(column, "").strip():
                merge_names[key].add(normalise_name(row[column]))

    identity_keys: dict[str, str] = {}
    for key, row in candidates.items():
        canonical = row["canonical_person_name"]
        institution = row["candidate_institution_normalised"]
        names = merge_names.get(key) or {normalise_name(canonical)}
        if institution:
            nodes = sorted(
                json.dumps(
                    [name, institution], ensure_ascii=False, separators=(",", ":")
                )
                for name in names
            )
        else:
            records = portfolios[key]
            if len(records) != 1 or len(names) != 1:
                raise ValueError(
                    "Missing-institution candidate cannot be reconstructed "
                    f"conservatively: {key}"
                )
            nodes = [
                json.dumps(
                    [next(iter(names)), "MISSING", next(iter(records))],
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            ]
        signature = json.dumps(nodes, ensure_ascii=False, separators=(",", ":"))
        identity_key = (
            f"{canonical.casefold()}|||{institution.casefold()}|||"
            f"{hashlib.sha256(signature.encode('utf-8')).hexdigest()[:16]}"
        )
        if candidate_key(identity_key) != key:
            raise ValueError(
                "Conservative identity-key reconstruction failed for candidate "
                f"{key}; the registered tie-break cannot be replayed"
            )
        identity_keys[key] = identity_key
    if len(set(identity_keys.values())) != len(identity_keys):
        raise ValueError("Conservative identity keys are not unique")
    return identity_keys


def load_8a() -> tuple[
    dict[str, frozenset[str]],
    dict[str, dict[str, str]],
    dict[str, str],
    dict[int, int],
]:
    incidence_headers, incidence = read_csv(INCIDENCE_PATH)
    forbidden = re.compile(r"name|email|affiliation|institution|contact|phone|address", re.I)
    bad_columns = [column for column in incidence_headers if forbidden.search(column)]
    if bad_columns:
        raise ValueError(f"De-identified incidence has prohibited columns: {bad_columns}")
    required_incidence = {
        "candidate_key",
        "eligible_record_id",
        "incidence_type",
        "potential_review_status",
        "candidate_eligible_record_count",
        "burden_diagnostic",
    }
    if set(incidence_headers) != required_incidence:
        raise ValueError("8A incidence columns differ")

    portfolio_sets: dict[str, set[str]] = defaultdict(set)
    pairs: set[tuple[str, str]] = set()
    for row in incidence:
        key, record = row["candidate_key"], row["eligible_record_id"]
        if not key or not record or (key, record) in pairs:
            raise ValueError("8A incidence contains a blank or duplicate key pair")
        pairs.add((key, record))
        if row["incidence_type"] != "NAMED_PERSON_ON_ELIGIBLE_RECORD":
            raise ValueError("8A incidence type differs")
        if row["potential_review_status"] != "POTENTIAL_NOT_PRODUCTION_ASSIGNMENT":
            raise ValueError("8A potential-review status differs")
        portfolio_sets[key].add(record)
    portfolios = {key: frozenset(values) for key, values in portfolio_sets.items()}
    for row in incidence:
        if int(row["candidate_eligible_record_count"]) != len(
            portfolios[row["candidate_key"]]
        ):
            raise ValueError("8A incidence count metadata does not reconcile")

    frame_headers, frame = read_csv(RESTRICTED_FRAME_PATH)
    required_frame = {
        "frame_row_type",
        "candidate_key",
        "canonical_person_name",
        "candidate_institution_normalised",
        "conditional_sequence_step",
        "conditional_cumulative_coverage",
        "source_name_string_a",
        "source_name_string_b",
    }
    if not required_frame <= set(frame_headers):
        raise ValueError("Restricted 8A frame is missing required replay fields")
    candidate_rows = [row for row in frame if row["frame_row_type"] == "candidate"]
    candidates = {row["candidate_key"]: row for row in candidate_rows}
    if len(candidates) != len(candidate_rows) or set(candidates) != set(portfolios):
        raise ValueError("Restricted candidates and de-identified incidence do not reconcile")
    direct_names = {row["canonical_person_name"] for row in candidate_rows}
    if any(value in direct_names for row in incidence for value in row.values()):
        raise ValueError("A direct name entered the de-identified incidence artefact")

    merge_rows = [
        row for row in frame if row["frame_row_type"] == "identity_merge_evidence"
    ]
    identity_keys = reconstruct_identity_keys(candidates, merge_rows, portfolios)
    conditional_curve: dict[int, int] = {}
    for row in candidate_rows:
        position = int(row["conditional_sequence_step"])
        cumulative = int(row["conditional_cumulative_coverage"])
        if position in conditional_curve:
            raise ValueError("8A conditional sequence position is duplicated")
        conditional_curve[position] = cumulative
    if set(conditional_curve) != set(range(1, len(candidates) + 1)):
        raise ValueError("8A conditional sequence positions are not contiguous")
    if list(conditional_curve.values()) != sorted(conditional_curve.values()):
        raise ValueError("8A conditional offered-coverage curve is not monotonic")
    return portfolios, candidates, identity_keys, conditional_curve


def validate_dispositions(rows: list[dict[str, str]], candidates: set[str]) -> None:
    seen_candidates: set[str] = set()
    for expected_step, row in enumerate(rows, 1):
        key = row["candidate_key"]
        if key not in candidates:
            raise ValueError(f"Disposition references an unknown candidate: {key}")
        if key in seen_candidates:
            raise ValueError(f"Candidate has more than one disposition row: {key}")
        seen_candidates.add(key)
        try:
            step = int(row["sequence_step"])
        except ValueError as exc:
            raise ValueError(f"Disposition sequence_step is not an integer: {key}") from exc
        if step != expected_step:
            raise ValueError(
                f"Disposition rows are not append-only contiguous steps at {key}: "
                f"expected {expected_step}, found {step}"
            )
        if row["disposition"] not in PERMITTED_DISPOSITIONS:
            raise ValueError(
                f"Disposition category is not exhaustive-procedure code: "
                f"{row['disposition']}"
            )
        for field in ("source_reached", "url", "search_date", "elapsed_minutes"):
            if not row[field].strip():
                raise ValueError(f"Disposition evidence field {field} is blank: {key}")
        try:
            date.fromisoformat(row["search_date"])
        except ValueError as exc:
            raise ValueError(f"Disposition search_date is not ISO YYYY-MM-DD: {key}") from exc
        try:
            elapsed = float(row["elapsed_minutes"])
        except ValueError as exc:
            raise ValueError(f"Disposition elapsed_minutes is not numeric: {key}") from exc
        if not math.isfinite(elapsed) or elapsed < 0 or elapsed > EFFORT_CEILING_MINUTES:
            raise ValueError(f"Disposition exceeds the ten-minute effort ceiling: {key}")
        if not elapsed.is_integer():
            raise ValueError(f"Elapsed time is not recorded to the nearest whole minute: {key}")


def validate_recruitment(
    rows: list[dict[str, str]],
    dispositions: list[dict[str, str]],
    candidates: Mapping[str, Mapping[str, str]],
    *,
    identifiers_due: bool,
) -> None:
    if len({row["candidate_key"] for row in rows}) != len(rows):
        raise ValueError("Restricted recruitment table contains a duplicate candidate")
    contactable = {
        row["candidate_key"]: row
        for row in dispositions
        if row["disposition"] == "CONTACTABLE"
    }
    if set(row["candidate_key"] for row in rows) != set(contactable):
        raise ValueError(
            "Restricted recruitment rows do not exactly match CONTACTABLE dispositions"
        )
    for row in rows:
        key = row["candidate_key"]
        disposition = contactable[key]
        candidate = candidates[key]
        required = (
            "name",
            "institution",
            "contact_route",
            "route_source",
            "route_url",
            "date_established",
        )
        if any(not row[field].strip() for field in required):
            raise ValueError(f"Restricted recruitment evidence is incomplete: {key}")
        if row["name"] != candidate["canonical_person_name"]:
            raise ValueError(f"Restricted recruitment name differs from 8A frame: {key}")
        if row["institution"] != candidate["candidate_institution_normalised"]:
            raise ValueError(f"Restricted recruitment institution differs from 8A frame: {key}")
        if (
            row["route_source"] != disposition["source_reached"]
            or row["route_url"] != disposition["url"]
            or row["date_established"] != disposition["search_date"]
        ):
            raise ValueError(f"Recruitment result does not reconcile to search evidence: {key}")
        if not identifiers_due and row["owner_id"].strip():
            raise ValueError(f"owner_id exists before sequence completion: {key}")


def choose_next(
    remaining: set[str],
    portfolios: Mapping[str, frozenset[str]],
    identity_keys: Mapping[str, str],
    covered: set[str],
) -> dict[str, object]:
    if not remaining:
        raise ValueError("Cannot choose from an exhausted candidate pool")
    marginal = {key: len(portfolios[key] - covered) for key in remaining}
    maximum = max(marginal.values())
    primary = {key for key in remaining if marginal[key] == maximum}
    maximum_total = max(len(portfolios[key]) for key in primary)
    secondary = {key for key in primary if len(portfolios[key]) == maximum_total}
    chosen = min(secondary, key=lambda key: identity_keys[key])
    if len(primary) == 1:
        applied = "none"
    elif len(secondary) == 1:
        applied = "total_eligible_record_count_desc"
    else:
        applied = "total_eligible_record_count_desc_then_conservative_identity_key_asc"
    return {
        "candidate_key": chosen,
        "marginal_coverage": marginal[chosen],
        "total_eligible_record_count": len(portfolios[chosen]),
        "registered_tie_break_rule": REGISTERED_TIE_BREAK,
        "tie_break_applied": applied,
        "primary_tie_size": len(primary),
        "secondary_tie_size": len(secondary),
    }


def replay(
    portfolios: Mapping[str, frozenset[str]],
    identity_keys: Mapping[str, str],
    dispositions: list[dict[str, str]],
) -> dict[str, object]:
    remaining = set(portfolios)
    covered: set[str] = set()
    admitted: list[str] = []
    removed: list[str] = []
    log: list[dict[str, object]] = []

    for disposition in dispositions:
        if len(admitted) >= COMPLETION_CONTACTABLE or len(log) >= SEARCH_CAP:
            raise ValueError("Disposition exists after the registered frame stopping condition")
        selected = choose_next(remaining, portfolios, identity_keys, covered)
        expected_key = str(selected["candidate_key"])
        if disposition["candidate_key"] != expected_key:
            raise ValueError(
                "Disposition was recorded for a candidate who was not computed next at "
                f"step {len(log) + 1}: recorded {disposition['candidate_key']}, "
                f"computed {expected_key}"
            )
        remaining.remove(expected_key)
        outcome = "ADMITTED" if disposition["disposition"] == "CONTACTABLE" else "REMOVED"
        admitted_position: int | str = ""
        if outcome == "ADMITTED":
            admitted.append(expected_key)
            admitted_position = len(admitted)
            covered.update(portfolios[expected_key])
        else:
            removed.append(expected_key)
        log.append(
            {
                "search_step": len(log) + 1,
                **selected,
                "disposition": disposition["disposition"],
                "outcome": outcome,
                "admitted_sequence_position": admitted_position,
                "contactability_adjusted_cumulative_offered_coverage": len(covered),
            }
        )

    completion_reason = ""
    if len(admitted) >= COMPLETION_CONTACTABLE:
        completion_reason = "25_CONTACTABLE"
    elif len(log) >= SEARCH_CAP:
        completion_reason = "50_SEARCH_CAP"
    elif not remaining:
        completion_reason = "CANDIDATE_POOL_EXHAUSTED"

    next_candidate = None
    if not completion_reason:
        next_candidate = {
            "search_step": len(log) + 1,
            **choose_next(remaining, portfolios, identity_keys, covered),
        }
    return {
        "sequence_log": log,
        "admitted_candidate_keys": admitted,
        "removed_candidate_keys": removed,
        "covered_record_count": len(covered),
        "covered_record_ids_sha256": canonical_hash(sorted(covered)),
        "remaining_candidate_count": len(remaining),
        "next_required_candidate": next_candidate,
        "frame_complete": bool(completion_reason),
        "completion_reason": completion_reason,
    }


def previous_states() -> list[tuple[int, Path, dict[str, object]]]:
    found: list[tuple[int, Path, dict[str, object]]] = []
    for path in STATE_DIRECTORY.glob("owner_sequence_8b_state_pass_*.json"):
        match = STATE_PATTERN.fullmatch(path.name)
        if not match:
            continue
        number = int(match.group(1))
        data = json.loads(path.read_text(encoding="utf-8"))
        found.append((number, path, data))
    found.sort(key=lambda item: item[0])
    if found and [number for number, _, _ in found] != list(range(1, len(found) + 1)):
        raise ValueError("8B state-pass numbering is not contiguous")
    return found


def validate_append_only(
    states: list[tuple[int, Path, dict[str, object]]],
    dispositions: list[dict[str, str]],
    frozen_hashes: Mapping[str, str],
) -> None:
    if not states:
        return
    previous = states[-1][2]
    previous_rows = previous.get("dispositions_incorporated")
    if not isinstance(previous_rows, list):
        raise ValueError("Previous 8B state lacks its disposition snapshot")
    if len(dispositions) < len(previous_rows):
        raise ValueError("Previously accepted disposition rows were deleted")
    for index, old in enumerate(previous_rows):
        if dispositions[index] != old:
            raise ValueError(
                "Previously accepted disposition or evidence changed at "
                f"sequence step {index + 1}"
            )
    if previous.get("frozen_input_hashes") != dict(frozen_hashes):
        raise ValueError("Frozen 8A/specification hashes differ from the preceding pass")


def coverage_rows(
    sequence_log: list[dict[str, object]], conditional_curve: Mapping[int, int]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in sequence_log:
        if item["outcome"] != "ADMITTED":
            continue
        position = int(item["admitted_sequence_position"])
        actual = int(item["contactability_adjusted_cumulative_offered_coverage"])
        conditional = int(conditional_curve[position])
        rows.append(
            {
                "admitted_sequence_position": position,
                "search_step": item["search_step"],
                "candidate_key": item["candidate_key"],
                "marginal_coverage": item["marginal_coverage"],
                "contactability_adjusted_cumulative_offered_coverage": actual,
                "8a_conditional_offered_coverage_at_same_position": conditional,
                "coverage_divergence_8b_minus_8a": actual - conditional,
                "coverage_quantity_label": (
                    "8B contactability-adjusted offered coverage; diagnostic only; "
                    "not completed-review coverage"
                ),
            }
        )
    cumulative = [
        int(row["contactability_adjusted_cumulative_offered_coverage"])
        for row in rows
    ]
    if cumulative != sorted(cumulative):
        raise ValueError("8B contactability-adjusted offered coverage is not monotonic")
    return rows


def recruitment_stage(sequence_position: int) -> str:
    if sequence_position <= 10:
        return "INITIAL_10"
    if sequence_position <= 15:
        return "BATCH_1"
    if sequence_position <= 20:
        return "BATCH_2"
    if sequence_position <= 25:
        return "BATCH_3"
    raise ValueError("Owner sequence position exceeds the registered 25 positions")


def identifier_mapping_hashes(
    recruitment: Iterable[Mapping[str, object]],
    assignments: Iterable[Mapping[str, object]],
) -> tuple[str, str]:
    owner_mapping = sorted(
        (str(row["candidate_key"]), str(row["owner_id"])) for row in recruitment
    )
    assignment_mapping = sorted(
        (
            str(row["owner_id"]),
            str(row["eligible_record_id"]),
            str(row["assignment_id"]),
        )
        for row in assignments
    )
    return canonical_hash(owner_mapping), canonical_hash(assignment_mapping)


def assignment_burden_summary(
    assignments: list[dict[str, object]],
) -> dict[str, object]:
    counts = Counter(str(row["owner_id"]) for row in assignments)
    values = sorted(counts.values())
    if not values:
        raise ValueError("Production assignment frame is empty")
    distribution = Counter(values)
    high_burden = [
        {"owner_id": owner_id, "assignment_count": count}
        for owner_id, count in sorted(counts.items())
        if count >= BURDEN_THRESHOLD
    ]
    middle = len(values) // 2
    if len(values) % 2:
        median = float(values[middle])
    else:
        median = (values[middle - 1] + values[middle]) / 2
    return {
        "owner_count": len(counts),
        "assignment_count": len(assignments),
        "minimum_assignments_per_owner": min(values),
        "median_assignments_per_owner": median,
        "maximum_assignments_per_owner": max(values),
        "assignment_count_distribution": {
            str(count): owners for count, owners in sorted(distribution.items())
        },
        "high_burden_threshold": BURDEN_THRESHOLD,
        "high_burden_diagnostic": f"HIGH_COUNT_GE_{BURDEN_THRESHOLD}",
        "high_burden_owners": high_burden,
    }


def validate_assignment_frame(
    assignments: list[dict[str, str]], admitted_owner_ids: set[str]
) -> None:
    forbidden_columns = re.compile(
        r"candidate|researcher|name|email|affiliation|institution|contact|route|"
        r"proposed|model|classification|disagreement|active|sample|coder",
        re.I,
    )
    bad_columns = [
        column for column in ASSIGNMENT_FRAME_HEADERS if forbidden_columns.search(column)
    ]
    if bad_columns:
        raise ValueError(
            f"Pseudonymous assignment frame has prohibited columns: {bad_columns}"
        )
    if not assignments:
        raise ValueError("Production assignment frame is empty")
    if any(any(not str(row[column]).strip() for column in ASSIGNMENT_FRAME_HEADERS) for row in assignments):
        # burden_diagnostic is the sole intentionally blank field for ordinary burdens.
        for row in assignments:
            for column in ASSIGNMENT_FRAME_HEADERS:
                if column != "burden_diagnostic" and not str(row[column]).strip():
                    raise ValueError(f"Production assignment field is blank: {column}")
    owner_pattern = re.compile(r"^OWNER_[0-9]{3,}$")
    assignment_pattern = re.compile(
        r"^REV-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}-"
        r"[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{4}$"
    )
    if any(not owner_pattern.fullmatch(row["owner_id"]) for row in assignments):
        raise ValueError("Assignment frame contains an invalid owner_id")
    if any(
        not assignment_pattern.fullmatch(row["assignment_id"])
        for row in assignments
    ):
        raise ValueError("Assignment frame contains an invalid assignment_id")
    assignment_ids = [row["assignment_id"] for row in assignments]
    if len(set(assignment_ids)) != len(assignment_ids):
        raise ValueError("Assignment IDs are not study-wide unique")
    pairs = [(row["owner_id"], row["eligible_record_id"]) for row in assignments]
    if len(set(pairs)) != len(pairs):
        raise ValueError("Assignment frame contains a duplicate owner-record incidence")
    if set(row["owner_id"] for row in assignments) != admitted_owner_ids:
        raise ValueError("Assignment frame owner set differs from the admitted frame")
    if any(row["review_instance_status"] != "PRECREATED_UNPOPULATED" for row in assignments):
        raise ValueError("Assignment frame contains an unexpected review-instance status")


def produce_or_verify_identifiers(
    *,
    first: Mapping[str, object],
    portfolios: Mapping[str, frozenset[str]],
    identity_keys: Mapping[str, str],
    recruitment: list[dict[str, str]],
    frozen_hashes: Mapping[str, str],
) -> dict[str, object]:
    admitted_keys = [str(value) for value in first["admitted_candidate_keys"]]
    if not first["frame_complete"] or not admitted_keys:
        raise ValueError(
            "Production identifiers are due only after sequence completion"
        )

    if IDENTIFIER_METADATA_PATH.is_file():
        metadata = json.loads(IDENTIFIER_METADATA_PATH.read_text(encoding="utf-8"))
        if (
            metadata.get("owner_id_permutation_seed") != OWNER_ID_PERMUTATION_SEED
            or metadata.get("assignment_id_seed") != ASSIGNMENT_ID_SEED
        ):
            raise ValueError(
                "Existing owner_identifier_metadata.json carries production seeds "
                "different from Instruction 8B Task 3"
            )
        if not ASSIGNMENT_FRAME_PATH.is_file():
            raise ValueError(
                "Identifier metadata exists but the production assignment frame is missing"
            )
        assignments = read_csv_exact(ASSIGNMENT_FRAME_PATH, ASSIGNMENT_FRAME_HEADERS)
        admitted_owner_ids = {row["owner_id"] for row in recruitment}
        if any(not value.strip() for value in admitted_owner_ids):
            raise ValueError(
                "Identifier metadata exists but the restricted owner mapping is incomplete"
            )
        validate_assignment_frame(assignments, admitted_owner_ids)
        if sha256(RECRUITMENT_PATH) != metadata.get("recruitment_table_sha256"):
            raise ValueError("Issued restricted owner mapping changed after generation")
        if sha256(ASSIGNMENT_FRAME_PATH) != metadata.get("assignment_frame_sha256"):
            raise ValueError("Issued assignment frame changed after generation")
        owner_hash, assignment_hash = identifier_mapping_hashes(
            recruitment, assignments
        )
        if owner_hash != metadata.get("owner_mapping_sha256"):
            raise ValueError("Issued candidate-to-owner mapping changed after generation")
        if assignment_hash != metadata.get("assignment_mapping_sha256"):
            raise ValueError("Issued assignment mapping changed after generation")
        correlation = float(
            metadata["owner_id_sequence_position_spearman_correlation"]
        )
        if abs(correlation) > 0.25:
            raise ValueError(
                "Existing owner-ID mapping exceeds the Spearman correlation guard"
            )
        return {
            "generated_now": False,
            "recruitment": recruitment,
            "assignments": assignments,
            "metadata": metadata,
            "metadata_sha256": sha256(IDENTIFIER_METADATA_PATH),
            "recruitment_sha256": sha256(RECRUITMENT_PATH),
            "assignment_sha256": sha256(ASSIGNMENT_FRAME_PATH),
            "burden": assignment_burden_summary(assignments),
        }

    if any(row["owner_id"].strip() for row in recruitment):
        raise ValueError(
            "Restricted owner IDs exist without owner_identifier_metadata.json; "
            "generation history cannot be verified"
        )

    sequence_input = pd.DataFrame(
        [
            {
                "sequence_position": position,
                "researcher_identity_key": identity_keys[key],
                "candidate_key": key,
            }
            for position, key in enumerate(admitted_keys, 1)
        ]
    )
    assignment_input = pd.DataFrame(
        [
            {
                "researcher_identity_key": identity_keys[key],
                "source_record_id": record_id,
                "candidate_key": key,
                "owner_sequence_position": position,
            }
            for position, key in enumerate(admitted_keys, 1)
            for record_id in sorted(portfolios[key])
        ]
    )
    result = assign_production_identifiers(
        sequence_input,
        assignment_input,
        owner_id_permutation_seed=OWNER_ID_PERMUTATION_SEED,
        assignment_id_seed=ASSIGNMENT_ID_SEED,
        specification_path=IDENTIFIER_SPECIFICATION,
    )
    correlation = float(
        result.metadata["owner_id_sequence_position_spearman_correlation"]
    )
    if abs(correlation) > 0.25:
        raise ValueError(
            "Spearman correlation between sequence_position and owner_id suffix "
            f"exceeds 0.25: {correlation:.12f}"
        )

    owner_by_candidate = {
        str(row["candidate_key"]): str(row["owner_id"])
        for row in result.owners.to_dict("records")
    }
    if set(owner_by_candidate) != set(admitted_keys):
        raise ValueError("Generated owner mapping differs from the admitted candidate set")
    updated_recruitment = [
        {**row, "owner_id": owner_by_candidate[row["candidate_key"]]}
        for row in recruitment
    ]
    assignment_rows: list[dict[str, object]] = []
    for row in result.assignments.to_dict("records"):
        position = int(row["owner_sequence_position"])
        key = str(row["candidate_key"])
        count = len(portfolios[key])
        assignment_rows.append(
            {
                "owner_id": str(row["owner_id"]),
                "assignment_id": str(row["assignment_id"]),
                "eligible_record_id": str(row["source_record_id"]),
                "owner_sequence_position": position,
                "recruitment_stage": recruitment_stage(position),
                "owner_eligible_record_count": count,
                "burden_diagnostic": (
                    f"HIGH_COUNT_GE_{BURDEN_THRESHOLD}"
                    if count >= BURDEN_THRESHOLD
                    else ""
                ),
                "review_instance_status": "PRECREATED_UNPOPULATED",
            }
        )
    assignment_rows.sort(
        key=lambda row: (
            int(row["owner_sequence_position"]), str(row["eligible_record_id"])
        )
    )
    admitted_owner_ids = set(owner_by_candidate.values())
    validate_assignment_frame(
        [{key: str(value) for key, value in row.items()} for row in assignment_rows],
        admitted_owner_ids,
    )
    expected_pairs = {
        (owner_by_candidate[key], record_id)
        for key in admitted_keys
        for record_id in portfolios[key]
    }
    actual_pairs = {
        (str(row["owner_id"]), str(row["eligible_record_id"]))
        for row in assignment_rows
    }
    if actual_pairs != expected_pairs:
        raise ValueError("Production assignments differ from the admitted 8A incidences")

    recruitment_payload = csv_bytes(RECRUITMENT_HEADERS, updated_recruitment)
    assignment_payload = csv_bytes(ASSIGNMENT_FRAME_HEADERS, assignment_rows)
    owner_hash, assignment_hash = identifier_mapping_hashes(
        updated_recruitment, assignment_rows
    )
    burden = assignment_burden_summary(assignment_rows)
    metadata = {
        **result.metadata,
        "production_seeds_fixed_date": PRODUCTION_SEEDS_FIXED_DATE,
        "identifier_generation_timing": "END_ONLY_AFTER_25_CONTACTABLE",
        "identifier_generation_event": "GENERATED_EXACTLY_ONCE_AT_FRAME_COMPLETION",
        "identifiers_issued_or_imported": False,
        "frame_completion_reason": first["completion_reason"],
        "frame_completion_sequence_state_hash": canonical_hash(
            {
                "sequence_log": first["sequence_log"],
                "admitted_candidate_keys": admitted_keys,
                "removed_candidate_keys": first["removed_candidate_keys"],
                "covered_record_count": first["covered_record_count"],
                "covered_record_ids_sha256": first["covered_record_ids_sha256"],
                "next_required_candidate": first["next_required_candidate"],
                "frame_complete": first["frame_complete"],
                "completion_reason": first["completion_reason"],
            }
        ),
        "frozen_input_hashes": dict(frozen_hashes),
        "disposition_file_sha256": sha256(DISPOSITIONS_PATH),
        "recruitment_table": RECRUITMENT_PATH.relative_to(REPO_ROOT).as_posix(),
        "recruitment_table_sha256": bytes_sha256(recruitment_payload),
        "assignment_frame": ASSIGNMENT_FRAME_PATH.relative_to(REPO_ROOT).as_posix(),
        "assignment_frame_sha256": bytes_sha256(assignment_payload),
        "owner_mapping_sha256": owner_hash,
        "assignment_mapping_sha256": assignment_hash,
        "burden_diagnostics": burden,
        "verification": {
            "owner_ids_unique_and_complete_permutation": True,
            "owner_position_absolute_spearman_at_most_0_25": True,
            "assignment_ids_unique_study_wide": True,
            "assignment_tokens_use_only_registered_safe_alphabet": True,
            "assignment_pairs_exactly_equal_admitted_8a_incidences": True,
            "assignment_frame_has_no_direct_identity_or_contact_columns": True,
            "assignment_frame_has_no_outcome_or_model_columns": True,
            "no_identifier_is_time_derived": True,
        },
    }
    metadata_payload = (
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    # The frozen specification requires metadata to exist before owner records
    # are created or imported. All payloads have been fully computed and
    # verified above; publish the metadata first, then the two mappings.
    IDENTIFIER_METADATA_PATH.write_bytes(metadata_payload)
    RECRUITMENT_PATH.write_bytes(recruitment_payload)
    ASSIGNMENT_FRAME_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASSIGNMENT_FRAME_PATH.write_bytes(assignment_payload)
    return {
        "generated_now": True,
        "recruitment": updated_recruitment,
        "assignments": assignment_rows,
        "metadata": metadata,
        "metadata_sha256": bytes_sha256(metadata_payload),
        "recruitment_sha256": bytes_sha256(recruitment_payload),
        "assignment_sha256": bytes_sha256(assignment_payload),
        "burden": burden,
    }


def build() -> dict[str, object]:
    frozen_hashes = verify_frozen_hashes()
    dispositions = read_csv_exact(DISPOSITIONS_PATH, DISPOSITION_HEADERS)
    recruitment = read_csv_exact(RECRUITMENT_PATH, RECRUITMENT_HEADERS)
    portfolios, candidates, identity_keys, conditional_curve = load_8a()
    validate_dispositions(dispositions, set(candidates))

    states = previous_states()
    validate_append_only(states, dispositions, frozen_hashes)

    first = replay(portfolios, identity_keys, dispositions)
    second = replay(portfolios, identity_keys, dispositions)
    if canonical_hash(first) != canonical_hash(second):
        raise ValueError("Sequence replay is not reproducible")

    if not dispositions:
        next_key = first["next_required_candidate"]["candidate_key"]
        if next_key != FIRST_EXPECTED_CANDIDATE:
            raise ValueError(
                f"First computed candidate differs: expected {FIRST_EXPECTED_CANDIDATE}, "
                f"found {next_key}"
            )

    identifiers_due = bool(first["frame_complete"])
    validate_recruitment(
        recruitment, dispositions, candidates, identifiers_due=identifiers_due
    )
    identifier_result = None
    if identifiers_due:
        identifier_result = produce_or_verify_identifiers(
            first=first,
            portfolios=portfolios,
            identity_keys=identity_keys,
            recruitment=recruitment,
            frozen_hashes=frozen_hashes,
        )
        recruitment = identifier_result["recruitment"]
        validate_recruitment(
            recruitment, dispositions, candidates, identifiers_due=True
        )

    coverage = coverage_rows(first["sequence_log"], conditional_curve)
    next_required_report = None
    if first["next_required_candidate"] is not None:
        next_key = str(first["next_required_candidate"]["candidate_key"])
        next_required_report = {
            "candidate_key": next_key,
            "name": candidates[next_key]["canonical_person_name"],
            "institution": candidates[next_key]["candidate_institution_normalised"],
        }
    sequence_state_payload = {
        "sequence_log": first["sequence_log"],
        "admitted_candidate_keys": first["admitted_candidate_keys"],
        "removed_candidate_keys": first["removed_candidate_keys"],
        "covered_record_count": first["covered_record_count"],
        "covered_record_ids_sha256": first["covered_record_ids_sha256"],
        "next_required_candidate": first["next_required_candidate"],
        "frame_complete": first["frame_complete"],
        "completion_reason": first["completion_reason"],
    }
    sequence_state_hash = canonical_hash(sequence_state_payload)
    contactable_count = len(first["admitted_candidate_keys"])
    searches = len(dispositions)
    contactable_remaining = max(COMPLETION_CONTACTABLE - contactable_count, 0)
    searches_remaining = max(SEARCH_CAP - searches, 0)
    if contactable_remaining < searches_remaining:
        nearer = "25_CONTACTABLE_THRESHOLD"
    elif searches_remaining < contactable_remaining:
        nearer = "50_SEARCH_CAP"
    else:
        nearer = "EQUALLY_NEAR"

    pass_number = len(states) + 1
    verification = {
        "8a_artifacts_match_frozen_hashes": True,
        "append_only_history_matches_preceding_pass": True,
        "every_disposition_matches_computed_next_candidate": True,
        "marginal_coverage_recomputed_after_every_disposition": True,
        "removals_logged_as_fully_as_admissions": True,
        "deterministic_tie_break_recorded": True,
        "replay_twice_identical": True,
        "incidence_contains_no_direct_identity_or_contact_columns": True,
        "coverage_monotonic_and_diagnostic_only": True,
        "no_contactability_search_performed": True,
        "nothing_frozen_invited_or_contacted": True,
        "no_reserve_artifact_read_by_8b_builder": True,
    }
    if identifier_result is None:
        verification["no_production_identifier_generated_before_completion"] = True
    else:
        verification.update(
            {
                "production_seeds_fixed_and_recorded": True,
                "production_identifiers_generated_or_loaded_only_at_completion": True,
                "owner_id_position_correlation_guard_passed": True,
                "owner_ids_unique_and_non_monotonic": True,
                "assignment_ids_unique_and_neutral": True,
                "assignments_exactly_match_admitted_8a_incidences": True,
                "no_assignment_references_record_outside_frozen_8a_eligible_incidence": True,
                "assignment_frame_contains_no_direct_identity_contact_model_or_outcome_columns": True,
            }
        )

    state = {
        "instruction": "8B_contactability_aware_sequence",
        "state_schema_version": "1.0",
        "pass_number": pass_number,
        "frozen_input_hashes": frozen_hashes,
        "disposition_file": DISPOSITIONS_PATH.relative_to(REPO_ROOT).as_posix(),
        "disposition_file_sha256": sha256(DISPOSITIONS_PATH),
        "recruitment_table": RECRUITMENT_PATH.relative_to(REPO_ROOT).as_posix(),
        "recruitment_table_sha256": sha256(RECRUITMENT_PATH),
        "dispositions_incorporated": dispositions,
        "searches_conducted": searches,
        "search_cap": SEARCH_CAP,
        "contactable_admitted": contactable_count,
        "contactable_target": COMPLETION_CONTACTABLE,
        "removed": len(first["removed_candidate_keys"]),
        "which_threshold_is_nearer": nearer,
        "contactability_adjusted_cumulative_offered_coverage": first[
            "covered_record_count"
        ],
        "next_required_candidate": next_required_report,
        "sequence_state_hash": sequence_state_hash,
        "sequence_log": first["sequence_log"],
        "frame_complete": first["frame_complete"],
        "completion_reason": first["completion_reason"],
        "search_cap_bound_before_25_contactable": False,
        "production_identifiers_generated": identifier_result is not None,
        "assignment_frame_generated": identifier_result is not None,
        "effort": {
            "recorded_elapsed_minutes": sum(
                int(float(row["elapsed_minutes"])) for row in dispositions
            ),
            "ceiling_minutes_for_searches_conducted": searches
            * EFFORT_CEILING_MINUTES,
            "per_candidate_ceiling_minutes": EFFORT_CEILING_MINUTES,
        },
        "coverage_quantities": {
            "8a": "conditional offered coverage assuming universal contactability",
            "8b": "contactability-adjusted offered coverage; diagnostic only",
            "completed_review": "not known until collection closes",
        },
        "verification": verification,
    }
    if identifier_result is not None:
        metadata = identifier_result["metadata"]
        state["production_identifiers"] = {
            "generation_action_this_pass": (
                "GENERATED_NOW"
                if identifier_result["generated_now"]
                else "LOADED_AND_VERIFIED_EXISTING"
            ),
            "owner_id_permutation_seed": OWNER_ID_PERMUTATION_SEED,
            "assignment_id_seed": ASSIGNMENT_ID_SEED,
            "metadata_path": IDENTIFIER_METADATA_PATH.relative_to(REPO_ROOT).as_posix(),
            "metadata_sha256": identifier_result["metadata_sha256"],
            "assignment_frame_path": ASSIGNMENT_FRAME_PATH.relative_to(REPO_ROOT).as_posix(),
            "assignment_frame_sha256": identifier_result["assignment_sha256"],
            "owner_count": metadata["owner_count"],
            "assignment_count": metadata["assignment_count"],
            "owner_id_sequence_position_spearman_correlation": metadata[
                "owner_id_sequence_position_spearman_correlation"
            ],
            "maximum_absolute_owner_position_correlation": metadata[
                "maximum_absolute_owner_position_correlation"
            ],
            "assignment_id_collision_count": metadata[
                "assignment_id_collision_count"
            ],
            "burden_diagnostics": identifier_result["burden"],
        }

    write_csv(SEQUENCE_LOG_PATH, SEQUENCE_LOG_HEADERS, first["sequence_log"])
    write_csv(COVERAGE_PATH, COVERAGE_HEADERS, coverage)
    state_path = STATE_DIRECTORY / f"owner_sequence_8b_state_pass_{pass_number:03d}.json"
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output = {
        "state_path": state_path.relative_to(REPO_ROOT).as_posix(),
        "state_sha256": sha256(state_path),
        "sequence_log_path": SEQUENCE_LOG_PATH.relative_to(REPO_ROOT).as_posix(),
        "sequence_log_sha256": sha256(SEQUENCE_LOG_PATH),
        "coverage_path": COVERAGE_PATH.relative_to(REPO_ROOT).as_posix(),
        "coverage_sha256": sha256(COVERAGE_PATH),
        "state": state,
    }
    if identifier_result is not None:
        output.update(
            {
                "identifier_metadata_path": IDENTIFIER_METADATA_PATH.relative_to(
                    REPO_ROOT
                ).as_posix(),
                "identifier_metadata_sha256": identifier_result["metadata_sha256"],
                "assignment_frame_path": ASSIGNMENT_FRAME_PATH.relative_to(
                    REPO_ROOT
                ).as_posix(),
                "assignment_frame_sha256": identifier_result["assignment_sha256"],
            }
        )
    return output


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True))
