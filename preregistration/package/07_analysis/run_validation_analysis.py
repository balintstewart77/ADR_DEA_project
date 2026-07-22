#!/usr/bin/env python3
"""Read-only preregistration analysis-preflight scaffold.

The scaffold validates frozen rules, schemas, dependencies, and closed gates.
It is not the final executable formal-analysis pipeline and has no network,
API, LLM, sampling, assignment-import, or REDCap client behaviour.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import yaml


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from analysis.validation.bootstrap import DEFAULT_ATTEMPTS, percentile
from analysis.validation.instrument_sensitivity import validate_formal_candidate_0_7_rows
from analysis.validation.output_schemas import verify_header_only_shells


PROTOCOL_VERSION = "v0.14"
INSTRUMENT_VERSION = "redcap-candidate-0.7"
TYPE_7_METHOD = "Hyndman-Fan Type 7 (NumPy/Pandas linear interpolation)"
MANIFEST = ROOT / "preregistration/preregistration_artifact_manifest.csv"
SAMPLING_SPEC = ROOT / "preregistration/package/04_exclusions_and_sampling/sampling_specification.yaml"
FROZEN_DICTIONARY = ROOT / "preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv"
ANALYSIS_ROOT = ROOT / "preregistration/package/07_analysis"
LOCKFILE = ANALYSIS_ROOT / "validation_requirements.lock"
REQUIRED_LOCK_LINES = (
    "numpy==2.2.5",
    "pandas==2.2.3",
    "PyYAML==6.0.2",
)


class AnalysisReadinessError(RuntimeError):
    pass


@dataclass(frozen=True)
class GateState:
    protocol_status: str
    frozen: bool
    registered: bool
    official_sample_draw_authorised: bool


def _bool(row: dict[str, str], key: str) -> bool:
    value = row.get(key, "").strip().lower()
    if value not in {"true", "false"}:
        raise AnalysisReadinessError(f"Manifest {key} is not an explicit boolean")
    return value == "true"


def _protocol_row() -> dict[str, str]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        rows = [
            row for row in csv.DictReader(handle)
            if row.get("artefact_group") == "00_protocol"
            and row.get("version") == PROTOCOL_VERSION
        ]
    if len(rows) != 1:
        raise AnalysisReadinessError(
            f"Expected one manifest protocol row for {PROTOCOL_VERSION}; found {len(rows)}"
        )
    return rows[0]


def gate_state() -> GateState:
    row = _protocol_row()
    return GateState(
        protocol_status=row.get("protocol_status", "").strip(),
        frozen=_bool(row, "frozen"),
        registered=_bool(row, "registered"),
        official_sample_draw_authorised=_bool(row, "official_sample_draw_authorised"),
    )


def static_check() -> dict[str, object]:
    row = _protocol_row()
    protocol_path = ROOT / row["current_path"]
    if not protocol_path.is_file():
        raise AnalysisReadinessError("Current protocol file is absent")
    protocol_bytes = protocol_path.read_bytes()
    if hashlib.sha256(protocol_bytes).hexdigest() != row.get("sha256"):
        raise AnalysisReadinessError("Current protocol hash differs from its manifest row")
    if row.get("protocol_status") != "review_candidate":
        raise AnalysisReadinessError("v0.14 must remain a review_candidate in this release")
    state = gate_state()
    if state.frozen or state.registered or state.official_sample_draw_authorised:
        raise AnalysisReadinessError("Review candidate has a prematurely open execution gate")

    specification = yaml.safe_load(SAMPLING_SPEC.read_text(encoding="utf-8"))
    basis = specification["protocol_basis"]
    boundary = specification["prospective_boundary"]
    if basis["version"] != PROTOCOL_VERSION:
        raise AnalysisReadinessError("Sampling specification is not bound to protocol v0.14")
    if boundary["official_draw_executed"] or boundary["official_sample_exists"]:
        raise AnalysisReadinessError("Sampling specification claims an official sample exists")

    with FROZEN_DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
        dictionary_rows = list(csv.DictReader(handle))
    forms = {row["Form Name"] for row in dictionary_rows}
    if len(dictionary_rows) != 150 or forms != {
        "assignment_admin", "coder_declaration", "scratch_coder", "project_owner"
    }:
        raise AnalysisReadinessError("Frozen candidate-0.7 dictionary structure is unexpected")

    verify_header_only_shells(ANALYSIS_ROOT)
    lock_lines = tuple(
        line.strip() for line in LOCKFILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if lock_lines != REQUIRED_LOCK_LINES:
        raise AnalysisReadinessError("Validation dependency lock is not the reviewed direct-runtime set")
    if DEFAULT_ATTEMPTS != 2000 or percentile((0.0, 10.0), 0.025) != 0.25:
        raise AnalysisReadinessError("Type-7 / 2,000-replicate bootstrap contract failed")
    if validate_formal_candidate_0_7_rows(()).results:
        raise AnalysisReadinessError("Instrument-validity sensitivity contract failed")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "instrument_version": INSTRUMENT_VERSION,
        "dictionary_fields": len(dictionary_rows),
        "output_shells": 10,
        "bootstrap_replicates": DEFAULT_ATTEMPTS,
        "percentile_method": TYPE_7_METHOD,
        "gate_open": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.run:
        print(
            "FAILED: formal analysis is not implemented in this preregistration "
            "preflight scaffold",
            file=sys.stderr,
        )
        return 2
    try:
        contract = static_check()
    except (AnalysisReadinessError, OSError, csv.Error, yaml.YAMLError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(yaml.safe_dump(contract, sort_keys=True).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
