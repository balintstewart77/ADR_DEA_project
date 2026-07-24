#!/usr/bin/env python3
"""Generate deterministic formal-validation coder assignments from active samples only."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import random
import subprocess
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DRAW_COMMIT = "6500c92148d97043a7826b684f5885127fd22814"
BASELINE_ACTIVE = Path(
    "preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv"
)
HARD_ACTIVE = Path(
    "preregistration_restricted/sampling/official_draw_20260724/hard_active.csv"
)
POPULATION = Path(
    "preregistration/package/01_source_and_cleaning/"
    "dea_accredited_projects_20260601_cleaned_1308.csv"
)
IMPORT_TEMPLATE = Path(
    "preregistration/package/06_redcap/redcap_assignment_import_template.csv"
)
DATA_DICTIONARY = Path(
    "preregistration/package/06_redcap/redcap_data_dictionary_candidate.csv"
)
EXPECTED_ACTIVE = {
    BASELINE_ACTIVE.as_posix(): {
        "rows": 150,
        "bytes": 18022,
        "sha256": "0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11",
        "family": "baseline",
    },
    HARD_ACTIVE.as_posix(): {
        "rows": 75,
        "bytes": 9284,
        "sha256": "582f248d39d911275e4e4f11bc34660b51809a1ed7c330644f9e2036299cfb11",
        "family": "hard_case",
    },
}
CODER_SEEDS = {"C01": 101, "C02": 102, "C03": 103}
CODER_DAGS = {"C01": "c01", "C02": "c02", "C03": "c03"}
ASSIGNMENT_BATCH = "formal_validation_20260724"
INSTRUMENT_VERSION = "redcap-candidate-0.7"
OUTPUT_NAMES = (
    "formal_assignment_crosswalk.csv",
    "redcap_import_validation.csv",
    "formal_assignment_assertion_report.json",
    "formal_assignment_metadata.json",
)
IMPORT_COLUMNS = (
    "assignment_id",
    "redcap_data_access_group",
    "record_kind",
    "review_stream",
    "reviewer_id",
    "source_record_id",
    "official_project_id",
    "project_title",
    "datasets_used",
    "validation_included",
    "display_order",
    "assignment_batch",
    "instrument_ver",
    "cluster_id",
    "assignment_admin_complete",
    "scratch_coder_complete",
    "project_owner_complete",
)
CROSSWALK_COLUMNS = (
    "assignment_id",
    "reviewer_id",
    "source_record_id",
    "display_order",
    "source_active_input",
    "sample_family",
    "hard_case_stratum",
)
FORBIDDEN_IMPORT_COLUMNS = {
    "sample_set",
    "hard_stratum",
    "sample_status",
    "draw_stage",
    "draw_rank",
    "selection_probability",
    "model_release",
    "production_ver",
    "production_model_output",
    "comparison_model_output",
    "model_labels",
    "disagreement_type",
    "reserve_status",
}
REDCAP_SPECIAL_COLUMNS = {
    "redcap_data_access_group",
    "assignment_admin_complete",
    "scratch_coder_complete",
    "project_owner_complete",
}


class AssignmentError(RuntimeError):
    """Raised when formal assignment generation is unsafe or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise AssignmentError(f"CSV has no header: {path}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise AssignmentError(f"CSV row width differs from header: {path}")
    return rows


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def deterministic_token(namespace: str, *parts: str, length: int) -> str:
    payload = "\x1f".join((namespace, *parts)).encode("utf-8")
    encoded = base64.b32encode(hashlib.sha256(payload).digest()).decode("ascii").rstrip("=")
    return encoded[:length]


def validate_active_rows(
    baseline_rows: Sequence[Mapping[str, str]],
    hard_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    required = {
        "record_id",
        "official_project_id",
        "sample_family",
        "sample_status",
        "hard_case_stratum",
        "draw_stage",
        "draw_rank",
        "validation_included",
    }
    for name, rows, expected_family, expected_count in (
        ("baseline_active", baseline_rows, "baseline", 150),
        ("hard_active", hard_rows, "hard_case", 75),
    ):
        if len(rows) != expected_count:
            raise AssignmentError(f"{name} has {len(rows)} rows, expected {expected_count}")
        if rows and required - set(rows[0]):
            raise AssignmentError(f"{name} lacks columns: {sorted(required - set(rows[0]))}")
        if any(row["sample_family"] != expected_family for row in rows):
            raise AssignmentError(f"{name} contains the wrong sample family")
        if any(row["sample_status"] != "active" for row in rows):
            raise AssignmentError(f"{name} contains a non-active record")
        if any(row["validation_included"].lower() not in {"yes", "1", "true"} for row in rows):
            raise AssignmentError(f"{name} contains a validation-excluded record")
    combined = [dict(row, source_active_input=BASELINE_ACTIVE.as_posix()) for row in baseline_rows]
    combined.extend(dict(row, source_active_input=HARD_ACTIVE.as_posix()) for row in hard_rows)
    identifiers = [row["record_id"] for row in combined]
    if len(identifiers) != 225 or len(set(identifiers)) != 225:
        raise AssignmentError("Active inputs must contain exactly 225 unique Record IDs")
    if any(not identifier.strip() for identifier in identifiers):
        raise AssignmentError("Active input contains a blank Record ID")
    return sorted(combined, key=lambda row: row["record_id"])


def population_lookup(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    required = {"Record ID", "Project ID", "Title", "Datasets Used"}
    if rows and required - set(rows[0]):
        raise AssignmentError(f"Population lacks columns: {sorted(required - set(rows[0]))}")
    lookup: dict[str, dict[str, str]] = {}
    for row in rows:
        record_id = row["Record ID"]
        if record_id in lookup:
            raise AssignmentError("Population contains a duplicate Record ID")
        lookup[record_id] = {
            "official_project_id": row["Project ID"],
            "project_title": row["Title"],
            "datasets_used": row["Datasets Used"],
        }
    return lookup


def validate_import_schema(template_header: Sequence[str], dictionary_fields: set[str]) -> None:
    if FORBIDDEN_IMPORT_COLUMNS & set(IMPORT_COLUMNS):
        raise AssignmentError("Coder-facing import contains forbidden sampling/model columns")
    allowed = set(template_header) | dictionary_fields | REDCAP_SPECIAL_COLUMNS
    unknown = set(IMPORT_COLUMNS) - allowed
    if unknown:
        raise AssignmentError(f"Coder-facing import contains unknown columns: {sorted(unknown)}")


def build_rows(
    active_rows: Sequence[Mapping[str, str]],
    population: Mapping[str, Mapping[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    active_by_id = {row["record_id"]: row for row in active_rows}
    canonical_ids = sorted(active_by_id)
    missing = sorted(set(canonical_ids) - set(population))
    if missing:
        raise AssignmentError(f"Active records missing from frozen population: {len(missing)}")
    import_rows: list[dict[str, object]] = []
    crosswalk_rows: list[dict[str, object]] = []
    for coder, seed in CODER_SEEDS.items():
        ordered = canonical_ids.copy()
        random.Random(seed).shuffle(ordered)
        for position, record_id in enumerate(ordered, start=1):
            active = active_by_id[record_id]
            evidence = population[record_id]
            if active["official_project_id"] != evidence["official_project_id"]:
                raise AssignmentError("Active/population official Project ID mismatch")
            assignment_id = deterministic_token(
                "dea-formal-assignment-v1", coder, record_id, length=8
            )
            cluster_id = deterministic_token("dea-formal-cluster-v1", record_id, length=10)
            import_rows.append(
                {
                    "assignment_id": assignment_id,
                    "redcap_data_access_group": CODER_DAGS[coder],
                    "record_kind": 1,
                    "review_stream": 1,
                    "reviewer_id": coder,
                    "source_record_id": record_id,
                    "official_project_id": evidence["official_project_id"],
                    "project_title": evidence["project_title"],
                    "datasets_used": evidence["datasets_used"],
                    "validation_included": 1,
                    "display_order": position,
                    "assignment_batch": ASSIGNMENT_BATCH,
                    "instrument_ver": INSTRUMENT_VERSION,
                    "cluster_id": cluster_id,
                    "assignment_admin_complete": 2,
                    "scratch_coder_complete": 0,
                    "project_owner_complete": 0,
                }
            )
            crosswalk_rows.append(
                {
                    "assignment_id": assignment_id,
                    "reviewer_id": coder,
                    "source_record_id": record_id,
                    "display_order": position,
                    "source_active_input": active["source_active_input"],
                    "sample_family": active["sample_family"],
                    "hard_case_stratum": active["hard_case_stratum"],
                }
            )
    return import_rows, crosswalk_rows


def validate_generated(
    import_rows: Sequence[Mapping[str, object]],
    crosswalk_rows: Sequence[Mapping[str, object]],
    active_rows: Sequence[Mapping[str, str]],
) -> dict[str, bool]:
    active_ids = {row["record_id"] for row in active_rows}
    pairs = [(str(row["reviewer_id"]), str(row["source_record_id"])) for row in import_rows]
    assertions = {
        "total_rows_675": len(import_rows) == len(crosswalk_rows) == 675,
        "unique_assignment_ids": len({str(row["assignment_id"]) for row in import_rows}) == 675,
        "unique_coder_record_pairs": len(set(pairs)) == 675,
        "active_membership_only": {record_id for _, record_id in pairs} == active_ids,
        "every_active_record_once_per_coder": all(
            Counter(record_id for coder_id, record_id in pairs if coder_id == coder)
            == Counter({record_id: 1 for record_id in active_ids})
            for coder in CODER_SEEDS
        ),
        "exactly_225_rows_per_coder": Counter(coder for coder, _ in pairs)
        == Counter({coder: 225 for coder in CODER_SEEDS}),
        "positions_1_to_225_per_coder": all(
            sorted(int(row["display_order"]) for row in import_rows if row["reviewer_id"] == coder)
            == list(range(1, 226))
            for coder in CODER_SEEDS
        ),
        "independent_coder_orders": len(
            {
                tuple(
                    str(row["source_record_id"])
                    for row in import_rows
                    if row["reviewer_id"] == coder
                )
                for coder in CODER_SEEDS
            }
        ) == 3,
        "crosswalk_matches_import": {
            (str(row["assignment_id"]), str(row["reviewer_id"]), str(row["source_record_id"]), int(row["display_order"]))
            for row in crosswalk_rows
        }
        == {
            (str(row["assignment_id"]), str(row["reviewer_id"]), str(row["source_record_id"]), int(row["display_order"]))
            for row in import_rows
        },
        "no_forbidden_import_columns": not (FORBIDDEN_IMPORT_COLUMNS & set(IMPORT_COLUMNS)),
        "no_coding_responses_populated": not any(
            column.startswith(("sc_", "po_")) for column in IMPORT_COLUMNS
        ),
        "formal_import_not_performed": True,
    }
    failed = sorted(name for name, passed in assertions.items() if not passed)
    if failed:
        raise AssignmentError(f"Generated assignment assertions failed: {failed}")
    return assertions


def canonical_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return next(reader)
        except StopIteration as exc:
            raise AssignmentError(f"CSV has no header: {path}") from exc


def dictionary_fields(path: Path) -> set[str]:
    rows = read_csv(path)
    return {row["Variable / Field Name"] for row in rows}


def generate(output_directory: Path, timestamp_utc: str) -> dict[str, object]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    if head != SOURCE_DRAW_COMMIT:
        raise AssignmentError(f"Generation HEAD differs from completed draw commit: {head}")
    if output_directory.exists():
        raise AssignmentError(f"Output directory already exists: {output_directory}")
    for relative, expected in EXPECTED_ACTIVE.items():
        path = ROOT / relative
        if not path.is_file():
            raise AssignmentError(f"Active input is missing: {relative}")
        if path.stat().st_size != expected["bytes"] or sha256_file(path) != expected["sha256"]:
            raise AssignmentError(f"Active input bytes differ: {relative}")
    baseline = read_csv(ROOT / BASELINE_ACTIVE)
    hard = read_csv(ROOT / HARD_ACTIVE)
    active = validate_active_rows(baseline, hard)
    population_rows = read_csv(ROOT / POPULATION)
    population = population_lookup(population_rows)
    validate_import_schema(
        canonical_header(ROOT / IMPORT_TEMPLATE), dictionary_fields(ROOT / DATA_DICTIONARY)
    )
    import_rows, crosswalk_rows = build_rows(active, population)
    assertions = validate_generated(import_rows, crosswalk_rows, active)
    output_directory.mkdir(parents=True)
    import_path = output_directory / "redcap_import_validation.csv"
    crosswalk_path = output_directory / "formal_assignment_crosswalk.csv"
    assertion_path = output_directory / "formal_assignment_assertion_report.json"
    metadata_path = output_directory / "formal_assignment_metadata.json"
    write_csv(import_path, IMPORT_COLUMNS, import_rows)
    write_csv(crosswalk_path, CROSSWALK_COLUMNS, crosswalk_rows)
    assertion_path.write_text(
        json.dumps(assertions, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    output_hashes = {
        path.name: {"byte_size": path.stat().st_size, "sha256": sha256_file(path)}
        for path in (import_path, crosswalk_path, assertion_path)
    }
    metadata = {
        "schema_version": 1,
        "purpose": "formal_validation_assignment_generation",
        "generated_at_utc": timestamp_utc,
        "source_draw_completion_commit": SOURCE_DRAW_COMMIT,
        "builder": {
            "repository_path": "scripts/generate_formal_validation_assignments.py",
            "sha256": sha256_file(Path(__file__)),
        },
        "active_inputs": {
            relative: {
                "row_count": expected["rows"],
                "byte_size": expected["bytes"],
                "sha256": expected["sha256"],
            }
            for relative, expected in EXPECTED_ACTIVE.items()
        },
        "public_evidence_lookup": {
            "repository_path": POPULATION.as_posix(),
            "byte_size": (ROOT / POPULATION).stat().st_size,
            "sha256": sha256_file(ROOT / POPULATION),
        },
        "redcap_contract": {
            "template_path": IMPORT_TEMPLATE.as_posix(),
            "template_sha256": sha256_file(ROOT / IMPORT_TEMPLATE),
            "dictionary_path": DATA_DICTIONARY.as_posix(),
            "dictionary_sha256": sha256_file(ROOT / DATA_DICTIONARY),
            "instrument_version": INSTRUMENT_VERSION,
            "import_status": "not_performed",
        },
        "randomisation": {
            "method": "Independent random.Random(seed).shuffle over Record-ID-sorted active records for each coder.",
            "seeds": CODER_SEEDS,
        },
        "coder_dag_mapping": CODER_DAGS,
        "counts": {
            "unique_active_record_ids": 225,
            "rows_per_coder": {coder: 225 for coder in CODER_SEEDS},
            "total_assignment_rows": 675,
        },
        "output_directory": output_directory.relative_to(ROOT).as_posix(),
        "outputs": output_hashes,
        "assertions": assertions,
        "restrictions": {
            "reserve_inputs_read": False,
            "reserve_records_assigned": False,
            "redcap_connection_used": False,
            "redcap_import_performed": False,
            "formal_validation_coding_started": False,
            "external_service_used": False,
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--generate-official", action="store_true")
    result.add_argument("--output-directory", type=Path)
    result.add_argument("--timestamp-utc")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_import_schema(
        canonical_header(ROOT / IMPORT_TEMPLATE), dictionary_fields(ROOT / DATA_DICTIONARY)
    )
    if args.check:
        print("Formal assignment builder static checks passed; no assignment was generated.")
        return 0
    if args.output_directory is None or not args.timestamp_utc:
        raise AssignmentError("Official generation requires --output-directory and --timestamp-utc")
    output_directory = args.output_directory.resolve()
    restricted_root = (ROOT / "preregistration_restricted/assignments").resolve()
    try:
        output_directory.relative_to(restricted_root)
    except ValueError as exc:
        raise AssignmentError("Formal assignment outputs must use restricted assignment storage") from exc
    metadata = generate(output_directory, args.timestamp_utc)
    print(
        "Formal validation assignments generated: "
        f"rows={metadata['counts']['total_assignment_rows']}, coders={len(CODER_SEEDS)}; "
        "REDCap import not performed."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssignmentError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2) from exc
