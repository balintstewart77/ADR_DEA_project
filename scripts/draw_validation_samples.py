#!/usr/bin/env python3
"""Deterministic DEA validation sampling engine with guarded official execution.

Phase 4 may run ``--check`` and ``--validate-real-inputs`` only. Random
selection from the real study frames is refused unless every registration and
Gate 2 safety condition passes in ``--execute-official-draw`` mode.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION_PATH = Path(
    "preregistration/package/04_exclusions_and_sampling/sampling_specification.yaml"
)
OFFICIAL_SEED = 20260713
CONFIRMATION_TOKEN = "EXECUTE_REGISTERED_DEA_DRAW"
STRATA = ("domain_only", "purpose_only", "both")
REAL_CLEANED_PATH = Path(
    "preregistration/package/01_source_and_cleaning/"
    "dea_accredited_projects_20260601_cleaned_1308.csv"
)
REAL_EXCLUSION_PATH = Path(
    "preregistration/package/04_exclusions_and_sampling/"
    "training_pilot_exclusion_list_v8.csv"
)
REAL_HARD_PATH = Path(
    "preregistration/package/03_preexisting_model_evidence/"
    "gpt55_disagreement_frame_380.csv"
)
RESTRICTED_SAMPLING_ROOT = Path("preregistration_restricted/sampling")
PROTOCOL_MANIFEST_PATH = Path("preregistration/preregistration_artifact_manifest.csv")
GATE_2_RECEIPT_PATH = Path("preregistration_restricted/registration_receipt.json")
DRAW_SCRIPT_PATH = Path("scripts/draw_validation_samples.py")
GATE_2_AUTHORISATION_ALLOWED_PATHS = frozenset(
    {
        GATE_2_RECEIPT_PATH.as_posix(),
        PROTOCOL_MANIFEST_PATH.as_posix(),
        "preregistration/README.md",
        "preregistration/package/00_protocol/README.md",
        "preregistration/package/04_exclusions_and_sampling/README.md",
        "preregistration/package/04_exclusions_and_sampling/official_sampling_runbook.md",
    }
)
GATE_2_AUTHORISATION_REQUIRED_PATHS = frozenset(
    {GATE_2_RECEIPT_PATH.as_posix(), PROTOCOL_MANIFEST_PATH.as_posix()}
)
OFFICIAL_OUTPUT_NAMES = (
    "baseline_active.csv",
    "baseline_reserve.csv",
    "hard_active.csv",
    "hard_reserve.csv",
    "combined_sampling_manifest.csv",
    "sampling_metadata.json",
    "sampling_assertion_report.json",
)
OUTPUT_COLUMNS = (
    "record_id",
    "official_project_id",
    "sample_family",
    "sample_status",
    "hard_case_stratum",
    "accompanying_tag_disagreement",
    "forced_into_active_hard",
    "draw_stage",
    "draw_rank",
    "validation_included",
    "source_population_version",
    "sampling_specification_version",
)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f\u00a0]")
# Canonical IDs include deterministic duplicate suffixes and two reviewed
# historical CLOSED identifiers retained by the frozen cleaning pipeline.
RECORD_ID_RE = re.compile(r"\d{4}/\d{3}(?:(?:/[a-z]+)|(?: CLOSED))?\Z")


class SamplingError(RuntimeError):
    """Raised when the registered design or safety boundary is violated."""


@dataclass(frozen=True)
class SamplingPlan:
    baseline_active_n: int = 150
    baseline_reserve_n: int = 100
    hard_active_quotas: Mapping[str, int] = field(
        default_factory=lambda: {
            "domain_only": 25,
            "purpose_only": 25,
            "both": 25,
        }
    )
    hard_reserve_target_n: int = 50


@dataclass(frozen=True)
class ValidatedInputs:
    cleaned: pd.DataFrame
    exclusions: frozenset[str]
    hard: pd.DataFrame
    input_hashes: Mapping[str, str]
    source_paths: Mapping[str, str]


@dataclass(frozen=True)
class SamplingResult:
    outputs: Mapping[str, pd.DataFrame]
    metadata: Mapping[str, object]
    assertions: Mapping[str, object]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _rooted(path: Path, root: Path = ROOT) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _relative(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    except (OSError, pd.errors.ParserError) as exc:
        raise SamplingError(f"Cannot read CSV {path}: {exc}") from exc


def _column(frame: pd.DataFrame, *names: str) -> str:
    for name in names:
        if name in frame.columns:
            return name
    raise SamplingError(f"Missing required column; expected one of {names}")


def _parse_bool(value: object, source: str) -> bool:
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise SamplingError(f"Invalid boolean {value!r} in {source}")


def _validate_ids(values: Iterable[object], source: str) -> list[str]:
    ids = [str(value) for value in values]
    if any(not value for value in ids):
        raise SamplingError(f"Blank Record ID in {source}")
    dirty = [value for value in ids if value != value.strip() or CONTROL_RE.search(value)]
    if dirty:
        raise SamplingError(f"Whitespace/control-character Record ID in {source}: {dirty[:3]!r}")
    malformed = [value for value in ids if RECORD_ID_RE.fullmatch(value) is None]
    if malformed:
        raise SamplingError(f"Malformed Record ID in {source}: {malformed[:3]!r}")
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise SamplingError(f"Duplicate Record IDs in {source}: {duplicates[:10]}")
    return ids


def load_sampling_specification(
    path: Path = SPECIFICATION_PATH,
    *,
    root: Path = ROOT,
    validate_hashes: bool = True,
) -> dict[str, object]:
    resolved = _rooted(path, root)
    try:
        specification = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SamplingError(f"Cannot parse sampling specification {resolved}: {exc}") from exc
    if not isinstance(specification, dict):
        raise SamplingError("Sampling specification must be a YAML mapping")
    required = {
        "release",
        "inputs",
        "randomisation",
        "baseline",
        "hard_active",
        "hard_reserve",
        "project_owner_review",
        "protocol_basis",
        "assertions",
        "prospective_boundary",
        "embargo",
    }
    if set(specification) != required:
        raise SamplingError(
            f"Sampling specification sections differ: missing={sorted(required - set(specification))}, "
            f"extra={sorted(set(specification) - required)}"
        )
    prospective = specification["prospective_boundary"]
    if not isinstance(prospective, dict) or prospective != {
        "official_draw_executed": False,
        "official_sample_exists": False,
        "draw_requires_registration": True,
        "draw_requires_gate_2": True,
        "real_seed_forbidden_in_tests": True,
        "canonical_protocol_authorisation_required": True,
    }:
        raise SamplingError("Prospective boundary is incomplete or unsafe")
    protocol_basis = specification["protocol_basis"]
    expected_protocol_basis = {
        "version": "v1.1",
        "path": "preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx",
        "status": "frozen",
        "current_implementation_basis": True,
        "frozen": True,
        "registered": False,
        "official_sample_draw_authorised": False,
    }
    if not isinstance(protocol_basis, dict) or protocol_basis != expected_protocol_basis:
        raise SamplingError(
            "Sampling specification protocol basis must be frozen, unregistered v1.1"
        )
    owner_review = specification["project_owner_review"]
    if not isinstance(owner_review, dict) or owner_review.get("fixed_reserve_exists") is not False:
        raise SamplingError("Sampling specification must not define a fixed owner reserve")
    randomisation = specification["randomisation"]
    if not isinstance(randomisation, dict):
        raise SamplingError("randomisation must be a mapping")
    if randomisation.get("master_seed") != OFFICIAL_SEED:
        raise SamplingError("Official seed differs from the protocol candidate constant")
    if randomisation.get("bit_generator") != "numpy.random.PCG64":
        raise SamplingError("Protocol bit generator must be numpy.random.PCG64")
    baseline = specification["baseline"]
    hard_active = specification["hard_active"]
    hard_reserve = specification["hard_reserve"]
    if not isinstance(baseline, dict) or (baseline.get("active_n"), baseline.get("reserve_n")) != (150, 100):
        raise SamplingError("Baseline design must be 150 active plus 100 reserve")
    if not isinstance(hard_active, dict) or (
        hard_active.get("domain_only_n"),
        hard_active.get("purpose_only_n"),
        hard_active.get("both_n"),
    ) != (25, 25, 25):
        raise SamplingError("Hard active design must be 25/25/25")
    if not isinstance(hard_reserve, dict) or hard_reserve.get("target_n") != 50:
        raise SamplingError("Hard reserve target must be 50")
    inputs = specification["inputs"]
    if not isinstance(inputs, dict):
        raise SamplingError("inputs must be a mapping")
    for prefix in ("cleaned_population", "exclusion", "disagreement_frame"):
        value = str(inputs.get(f"{prefix}_sha256", ""))
        if re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise SamplingError(f"Invalid {prefix} SHA-256")
        candidate = Path(str(inputs.get(f"{prefix}_path", "")))
        if candidate.is_absolute() or not str(candidate):
            raise SamplingError(f"{prefix} path must be repository-relative")
        if validate_hashes:
            actual = _rooted(candidate, root)
            if not actual.is_file() or sha256_file(actual) != value:
                raise SamplingError(f"{prefix} file/hash mismatch: {candidate}")
    return specification


def _normalise_hard_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rid_col = _column(frame, "Record ID", "record_id")
    pid_col = _column(frame, "Project ID", "official_project_id")
    stratum_col = _column(frame, "disagreement_layer", "hard_case_stratum")
    ids = _validate_ids(frame[rid_col], "disagreement frame")
    strata = frame[stratum_col].map(
        {"domain": "domain_only", "purpose": "purpose_only", "both": "both",
         "domain_only": "domain_only", "purpose_only": "purpose_only",
         "domains-only": "domain_only", "purposes-only": "purpose_only"}
    )
    if strata.isna().any():
        unknown = sorted(set(frame.loc[strata.isna(), stratum_col]))
        raise SamplingError(f"Unknown hard-case stratum values: {unknown}")
    accompanying: list[bool] = []
    has_raw_flags = {"domains_exact_match", "purposes_exact_match", "covid_tag_match", "disparities_tag_match", "tag_set_match"}.issubset(frame.columns)
    for index, row in frame.iterrows():
        stratum = strata.loc[index]
        if has_raw_flags:
            domain_match = _parse_bool(row["domains_exact_match"], f"hard row {index}")
            purpose_match = _parse_bool(row["purposes_exact_match"], f"hard row {index}")
            expected = {
                "domain_only": (False, True),
                "purpose_only": (True, False),
                "both": (False, False),
            }[stratum]
            if (domain_match, purpose_match) != expected:
                raise SamplingError(f"Hard stratum/label-match inconsistency at row {index}")
            covid_match = _parse_bool(row["covid_tag_match"], f"hard row {index}")
            equity_match = _parse_bool(row["disparities_tag_match"], f"hard row {index}")
            joint_match = _parse_bool(row["tag_set_match"], f"hard row {index}")
            if joint_match != (covid_match and equity_match):
                raise SamplingError(f"Inconsistent tag-disagreement flags at row {index}")
            if "any_tag_set_match" in frame and _parse_bool(row["any_tag_set_match"], f"hard row {index}") != joint_match:
                raise SamplingError(f"Inconsistent compatibility tag flag at row {index}")
            if "tag_only_disagreement" in frame and _parse_bool(row["tag_only_disagreement"], f"hard row {index}"):
                raise SamplingError(f"Tag-only record incorrectly present in hard frame at row {index}")
            if "DISAGREE" in frame and not _parse_bool(row["DISAGREE"], f"hard row {index}"):
                raise SamplingError(f"Non-disagreement record present in hard frame at row {index}")
            accompanying.append(not joint_match)
        elif "accompanying_tag_disagreement" in frame:
            accompanying.append(_parse_bool(row["accompanying_tag_disagreement"], f"hard row {index}"))
        else:
            raise SamplingError("Hard frame lacks validated tag-disagreement fields")
    return pd.DataFrame(
        {
            "record_id": ids,
            "official_project_id": frame[pid_col].astype(str).tolist(),
            "hard_case_stratum": strata.tolist(),
            "accompanying_tag_disagreement": accompanying,
        }
    )


def validate_inputs(
    cleaned_path: Path,
    exclusion_path: Path,
    disagreement_path: Path,
    *,
    specification: Mapping[str, object] | None = None,
    expect_real: bool = False,
    root: Path = ROOT,
) -> ValidatedInputs:
    paths = {
        "cleaned_population": _rooted(cleaned_path, root),
        "exclusion": _rooted(exclusion_path, root),
        "disagreement_frame": _rooted(disagreement_path, root),
    }
    cleaned_raw = _read_csv(paths["cleaned_population"])
    rid_col = _column(cleaned_raw, "Record ID", "record_id")
    pid_col = _column(cleaned_raw, "Project ID", "official_project_id")
    cleaned_ids = _validate_ids(cleaned_raw[rid_col], "cleaned population")
    cleaned = pd.DataFrame(
        {
            "record_id": cleaned_ids,
            "official_project_id": cleaned_raw[pid_col].astype(str).tolist(),
        }
    ).sort_values("record_id", kind="stable").reset_index(drop=True)
    exclusion_raw = _read_csv(paths["exclusion"])
    exclusion_col = _column(exclusion_raw, "record_id", "Record ID")
    exclusion_ids = _validate_ids(exclusion_raw[exclusion_col], "exclusion CSV")
    missing_exclusions = sorted(set(exclusion_ids) - set(cleaned_ids))
    if missing_exclusions:
        raise SamplingError(f"Excluded IDs absent from cleaned population: {missing_exclusions}")
    hard = _normalise_hard_frame(_read_csv(paths["disagreement_frame"]))
    missing_hard = sorted(set(hard["record_id"]) - set(cleaned_ids))
    if missing_hard:
        raise SamplingError(f"Hard-frame IDs absent from cleaned population: {missing_hard[:10]}")
    excluded_hard = sorted(set(hard["record_id"]) & set(exclusion_ids))
    if excluded_hard:
        raise SamplingError(f"Excluded IDs remain in disagreement frame: {excluded_hard}")
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    if specification is not None:
        spec_inputs = specification.get("inputs")
        if not isinstance(spec_inputs, Mapping):
            raise SamplingError("Specification inputs are missing")
        for name in paths:
            if hashes[name] != spec_inputs.get(f"{name}_sha256"):
                raise SamplingError(f"{name} hash differs from specification")
    if expect_real:
        counts = hard["hard_case_stratum"].value_counts().to_dict()
        if len(cleaned) != 1308 or len(exclusion_ids) != 22 or len(hard) != 380:
            raise SamplingError(
                f"Real input counts differ: cleaned={len(cleaned)}, exclusions={len(exclusion_ids)}, hard={len(hard)}"
            )
        if counts != {"domain_only": 182, "purpose_only": 143, "both": 55}:
            raise SamplingError(f"Real hard-stratum counts differ: {counts}")
        if int(hard["accompanying_tag_disagreement"].sum()) != 11:
            raise SamplingError("Real accompanying-tag count differs from 11")
    return ValidatedInputs(
        cleaned=cleaned,
        exclusions=frozenset(exclusion_ids),
        hard=hard.sort_values("record_id", kind="stable").reset_index(drop=True),
        input_hashes=hashes,
        source_paths={name: _relative(path, root) for name, path in paths.items()},
    )


def create_rng(seed: int) -> np.random.Generator:
    """Construct the registered generator. Real-input validation never calls this."""
    return np.random.Generator(np.random.PCG64(seed))


def _choice_ids(
    candidates: Iterable[str], n: int, rng: np.random.Generator
) -> list[str]:
    ordered = sorted(candidates)
    if n < 0 or n > len(ordered):
        raise SamplingError(f"Cannot draw {n} records from {len(ordered)} candidates")
    if n == 0:
        return []
    positions = rng.choice(len(ordered), size=n, replace=False)
    return [ordered[int(position)] for position in positions]


def _seed_order(rng: np.random.Generator) -> list[str]:
    positions = rng.permutation(len(STRATA))
    return [STRATA[int(position)] for position in positions]


def allocate_hard_reserve(
    availability: Mapping[str, int],
    rng: np.random.Generator,
    *,
    target: int = 50,
) -> tuple[dict[str, int], dict[str, int], list[str], list[dict[str, object]], int]:
    """Allocate the 17/17/16 reserve with deterministic even fallback."""
    sixteen_stratum = STRATA[int(rng.integers(0, len(STRATA)))]
    initial = {stratum: 17 for stratum in STRATA}
    initial[sixteen_stratum] = 16
    tie_order = _seed_order(rng)
    final = {stratum: min(initial[stratum], int(availability[stratum])) for stratum in STRATA}
    actions: list[dict[str, object]] = []
    for stratum in STRATA:
        shortfall = initial[stratum] - final[stratum]
        if shortfall:
            actions.append({"action": "initial_shortfall", "stratum": stratum, "seats": shortfall})
    seats_needed = target - sum(final.values())
    while seats_needed > 0:
        spare = {stratum: int(availability[stratum]) - final[stratum] for stratum in STRATA}
        eligible = [stratum for stratum in tie_order if spare[stratum] > 0]
        if not eligible:
            break
        for stratum in eligible:
            if seats_needed == 0:
                break
            final[stratum] += 1
            seats_needed -= 1
            actions.append({"action": "reallocate_one", "stratum": stratum, "seat": final[stratum]})
    return initial, final, tie_order, actions, seats_needed


def _record_rows(
    ids: Sequence[str],
    *,
    family: str,
    status: str,
    stage: str,
    cleaned_by_id: pd.DataFrame,
    hard_by_id: pd.DataFrame,
    forced_ids: frozenset[str] = frozenset(),
    population_version: str,
    specification_version: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for rank, record_id in enumerate(ids, start=1):
        cleaned = cleaned_by_id.loc[record_id]
        hard = hard_by_id.loc[record_id] if record_id in hard_by_id.index else None
        rows.append({
            "record_id": record_id,
            "official_project_id": str(cleaned["official_project_id"]),
            "sample_family": family,
            "sample_status": status,
            "hard_case_stratum": "" if hard is None else hard["hard_case_stratum"],
            "accompanying_tag_disagreement": False if hard is None else bool(hard["accompanying_tag_disagreement"]),
            "forced_into_active_hard": record_id in forced_ids,
            "draw_stage": stage,
            "draw_rank": rank,
            "validation_included": "yes",
            "source_population_version": population_version,
            "sampling_specification_version": specification_version,
        })
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _assert_sample(
    outputs: Mapping[str, pd.DataFrame],
    inputs: ValidatedInputs,
    plan: SamplingPlan,
    forced_eligible: frozenset[str],
    reserve_shortfall: int,
) -> dict[str, bool]:
    all_ids: list[str] = []
    for name, frame in outputs.items():
        missing_columns = [column for column in OUTPUT_COLUMNS if column not in frame]
        if missing_columns:
            raise SamplingError(f"{name} lacks output columns: {missing_columns}")
        ids = _validate_ids(frame["record_id"], name)
        all_ids.extend(ids)
    if len(all_ids) != len(set(all_ids)):
        raise SamplingError("A Record ID occurs in more than one sampling output")
    if set(all_ids) & inputs.exclusions:
        raise SamplingError("An excluded Record ID was selected")
    expected = {
        "baseline_active": plan.baseline_active_n,
        "baseline_reserve": plan.baseline_reserve_n,
        "hard_active": sum(plan.hard_active_quotas.values()),
    }
    for name, count in expected.items():
        if len(outputs[name]) != count:
            raise SamplingError(f"{name} has {len(outputs[name])} rows, expected {count}")
    if len(outputs["hard_reserve"]) > plan.hard_reserve_target_n:
        raise SamplingError("Hard reserve exceeds its target")
    if len(outputs["hard_reserve"]) + reserve_shortfall != plan.hard_reserve_target_n:
        raise SamplingError("Hard-reserve shortfall is not explained by availability")
    hard_active = outputs["hard_active"]
    active_counts = hard_active["hard_case_stratum"].value_counts().to_dict()
    if active_counts != dict(plan.hard_active_quotas):
        raise SamplingError(f"Active hard allocation differs: {active_counts}")
    if not forced_eligible.issubset(set(hard_active["record_id"])):
        raise SamplingError("An eligible accompanying-tag record was not forced into active hard")
    hard_source = inputs.hard.set_index("record_id")
    for frame in (hard_active, outputs["hard_reserve"]):
        for row in frame.itertuples(index=False):
            if hard_source.loc[row.record_id, "hard_case_stratum"] != row.hard_case_stratum:
                raise SamplingError(f"Hard stratum changed for {row.record_id}")
    return {
        "excluded_ids_absent": True, "no_replacement": True, "unique_ids": True,
        "active_reserve_disjoint": True, "hard_stratum_validity": True,
        "forced_tag_inclusion": True, "expected_columns": True,
        "clean_record_ids": True, "output_counts_valid": True,
        "reserve_shortfall_explained": True,
    }


def draw_samples(
    inputs: ValidatedInputs,
    seed: int,
    *,
    plan: SamplingPlan = SamplingPlan(),
    rng_factory: Callable[[int], np.random.Generator] | None = None,
    specification_version: str = "sampling-1.0-rc1",
    population_version: str = "dea-cleaned-20260601-1308",
) -> SamplingResult:
    """Execute the registered design on already validated inputs."""
    rng = (rng_factory or create_rng)(seed)
    eligible = sorted(set(inputs.cleaned["record_id"]) - inputs.exclusions)
    baseline_active_ids = _choice_ids(eligible, plan.baseline_active_n, rng)
    remaining = set(eligible) - set(baseline_active_ids)
    baseline_reserve_ids = _choice_ids(remaining, plan.baseline_reserve_n, rng)
    baseline_ids = set(baseline_active_ids) | set(baseline_reserve_ids)

    hard_pre_counts = {stratum: int((inputs.hard["hard_case_stratum"] == stratum).sum()) for stratum in STRATA}
    hard_remaining = inputs.hard[~inputs.hard["record_id"].isin(baseline_ids)].copy()
    hard_post_counts = {stratum: int((hard_remaining["hard_case_stratum"] == stratum).sum()) for stratum in STRATA}
    forced_counts: dict[str, int] = {}
    hard_active_ids: list[str] = []
    forced_ids: set[str] = set()
    for stratum in STRATA:
        stratum_frame = hard_remaining[hard_remaining["hard_case_stratum"] == stratum]
        quota = int(plan.hard_active_quotas[stratum])
        if len(stratum_frame) < quota:
            raise SamplingError(f"Active hard stratum {stratum} has {len(stratum_frame)} records, below quota {quota}")
        forced = sorted(stratum_frame.loc[stratum_frame["accompanying_tag_disagreement"], "record_id"].tolist())
        forced_counts[stratum] = len(forced)
        if len(forced) > quota:
            raise SamplingError(f"Forced accompanying-tag records in {stratum} ({len(forced)}) exceed quota {quota}")
        forced_ids.update(forced)
        chosen = _choice_ids(set(stratum_frame["record_id"]) - set(forced), quota - len(forced), rng)
        hard_active_ids.extend(forced + chosen)

    remaining_after_active = hard_remaining[~hard_remaining["record_id"].isin(hard_active_ids)]
    reserve_availability = {stratum: int((remaining_after_active["hard_case_stratum"] == stratum).sum()) for stratum in STRATA}
    initial_allocation, final_allocation, tie_order, fallback_actions, shortfall = allocate_hard_reserve(
        reserve_availability, rng, target=plan.hard_reserve_target_n
    )
    hard_reserve_ids: list[str] = []
    for stratum in STRATA:
        candidates = remaining_after_active.loc[remaining_after_active["hard_case_stratum"] == stratum, "record_id"]
        hard_reserve_ids.extend(_choice_ids(candidates, final_allocation[stratum], rng))

    common = {
        "cleaned_by_id": inputs.cleaned.set_index("record_id"),
        "hard_by_id": inputs.hard.set_index("record_id"),
        "population_version": population_version,
        "specification_version": specification_version,
    }
    outputs = {
        "baseline_active": _record_rows(baseline_active_ids, family="baseline", status="active", stage="1_baseline_active", **common),
        "baseline_reserve": _record_rows(baseline_reserve_ids, family="baseline", status="reserve", stage="2_baseline_reserve", **common),
        "hard_active": _record_rows(hard_active_ids, family="hard_case", status="active", stage="3_hard_active", forced_ids=frozenset(forced_ids), **common),
        "hard_reserve": _record_rows(hard_reserve_ids, family="hard_case", status="reserve", stage="4_hard_reserve", **common),
    }
    assertions = _assert_sample(outputs, inputs, plan, frozenset(forced_ids), shortfall)
    metadata = {
        "master_seed": seed,
        "rng": "numpy.random.Generator",
        "bit_generator": "numpy.random.PCG64",
        "rng_consumption_order": [
            "baseline_active", "baseline_reserve", "hard_active_domain_only_fill",
            "hard_active_purpose_only_fill", "hard_active_both_fill",
            "reserve_sixteen_seat_stratum", "reserve_reallocation_tie_order",
            "hard_reserve_domain_only", "hard_reserve_purpose_only", "hard_reserve_both",
        ],
        "eligible_population_count": len(eligible),
        "exclusion_count": len(inputs.exclusions),
        "pre_baseline_hard_stratum_counts": hard_pre_counts,
        "post_baseline_hard_stratum_counts": hard_post_counts,
        "forced_accompanying_tag_counts": forced_counts,
        "initial_hard_reserve_allocation": initial_allocation,
        "hard_reserve_sixteen_seat_stratum": next(stratum for stratum, seats in initial_allocation.items() if seats == 16),
        "hard_reserve_reallocation_tie_order": tie_order,
        "hard_reserve_availability": reserve_availability,
        "hard_reserve_fallback_actions": fallback_actions,
        "final_hard_reserve_allocation": final_allocation,
        "hard_reserve_unfilled_shortfall": shortfall,
    }
    return SamplingResult(outputs=outputs, metadata=metadata, assertions=assertions)


def write_sampling_outputs(
    result: SamplingResult,
    output_directory: Path,
    *,
    repository_commit: str,
    specification_path: str,
    specification_hash: str,
    input_hashes: Mapping[str, str],
    input_paths: Mapping[str, str],
    timestamp: str | None = None,
) -> Mapping[str, str]:
    output_directory.mkdir(parents=True, exist_ok=True)
    file_map = {
        "baseline_active.csv": result.outputs["baseline_active"],
        "baseline_reserve.csv": result.outputs["baseline_reserve"],
        "hard_active.csv": result.outputs["hard_active"],
        "hard_reserve.csv": result.outputs["hard_reserve"],
    }
    file_map["combined_sampling_manifest.csv"] = pd.concat(file_map.values(), ignore_index=True)
    for filename, frame in file_map.items():
        frame.to_csv(output_directory / filename, index=False, lineterminator="\n")
    assertion_path = output_directory / "sampling_assertion_report.json"
    assertion_path.write_text(json.dumps(result.assertions, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {filename: sha256_file(output_directory / filename) for filename in (*file_map.keys(), "sampling_assertion_report.json")}
    metadata = dict(result.metadata)
    metadata.update({
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "repository_commit": repository_commit,
        "input_paths": dict(input_paths), "input_hashes": dict(input_hashes),
        "specification_path": specification_path, "specification_hash": specification_hash,
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "output_row_counts": {name: len(frame) for name, frame in result.outputs.items()},
        "output_hashes": output_hashes, "assertions": dict(result.assertions),
    })
    metadata_path = output_directory / "sampling_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**output_hashes, "sampling_metadata.json": sha256_file(metadata_path)}


def _git_head(root: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def _git_clean(root: Path) -> bool:
    return not subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def _git_text(root: Path, *arguments: str) -> str:
    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        command = " ".join(arguments[:2])
        raise SamplingError(
            f"Cannot verify Gate 2 Git provenance with git {command}"
        ) from exc


def validate_gate_2_authorisation_commit(
    *, root: Path, head_commit: str, basis_commit: str, receipt_path: Path
) -> None:
    """Validate the direct-child Gate 2 authorisation commit without self-reference."""

    try:
        receipt_relative = receipt_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SamplingError("Gate 2 receipt is outside the repository") from exc
    if receipt_relative != GATE_2_RECEIPT_PATH.as_posix():
        raise SamplingError(
            f"Gate 2 receipt must use {GATE_2_RECEIPT_PATH.as_posix()}"
        )

    parent_commit = _git_text(root, "rev-parse", f"{head_commit}^")
    if parent_commit != basis_commit:
        raise SamplingError(
            "Execution HEAD must be the direct Gate 2 authorisation child of "
            "the frozen implementation basis"
        )

    changed: dict[str, str] = {}
    output = _git_text(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-status",
        "-r",
        "--no-renames",
        basis_commit,
        head_commit,
    )
    for line in output.splitlines():
        status, separator, path = line.partition("\t")
        if not separator or not path:
            raise SamplingError("Cannot parse Gate 2 authorisation commit diff")
        changed[path] = status

    unexpected = sorted(set(changed) - GATE_2_AUTHORISATION_ALLOWED_PATHS)
    if unexpected:
        raise SamplingError(
            "Gate 2 authorisation commit changes paths that are not permitted: "
            + ", ".join(unexpected)
        )
    invalid_status = sorted(
        path for path, status in changed.items() if status not in {"A", "M"}
    )
    if invalid_status:
        raise SamplingError(
            "Gate 2 authorisation commit may only add or modify allowed paths: "
            + ", ".join(invalid_status)
        )
    missing = sorted(GATE_2_AUTHORISATION_REQUIRED_PATHS - set(changed))
    if missing:
        raise SamplingError(
            "Gate 2 authorisation commit lacks required tracked changes: "
            + ", ".join(missing)
        )

    try:
        receipt_blob = _git_text(root, "rev-parse", f"{head_commit}:{receipt_relative}")
        worktree_receipt_blob = _git_text(
            root, "hash-object", f"--path={receipt_relative}", receipt_relative
        )
    except SamplingError as exc:
        raise SamplingError(
            "Gate 2 receipt must be tracked in the authorisation commit"
        ) from exc
    if receipt_blob != worktree_receipt_blob:
        raise SamplingError(
            "Working-tree Gate 2 receipt differs from the authorisation commit"
        )

    basis_script_blob = _git_text(
        root, "rev-parse", f"{basis_commit}:{DRAW_SCRIPT_PATH.as_posix()}"
    )
    head_script_blob = _git_text(
        root, "rev-parse", f"{head_commit}:{DRAW_SCRIPT_PATH.as_posix()}"
    )
    if basis_script_blob != head_script_blob:
        raise SamplingError(
            "Draw script differs between the implementation basis and authorisation commit"
        )


def validate_protocol_draw_authorisation(
    manifest_path: Path, receipt: Mapping[str, object]
) -> Mapping[str, str]:
    """Require the canonical manifest to authorise the registered frozen basis."""

    if not manifest_path.is_file():
        raise SamplingError("Canonical protocol manifest does not exist")
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        candidates = [
            row for row in csv.DictReader(handle)
            if row.get("artefact_group") == "00_protocol"
            and (row.get("current_implementation_basis") or "").lower() == "true"
        ]
    if len(candidates) != 1:
        raise SamplingError("Manifest must declare exactly one current protocol implementation basis")
    row = candidates[0]
    if (row.get("frozen") or "").lower() != "true":
        raise SamplingError("Current protocol implementation basis is not finally frozen")
    if (row.get("registered") or "").lower() != "true":
        raise SamplingError("Current protocol implementation basis is not registered")
    if (row.get("official_sample_draw_authorised") or "").lower() != "true":
        raise SamplingError("Canonical protocol metadata does not authorise an official sample draw")
    if not row.get("registration_identifier") or not row.get("registration_timestamp"):
        raise SamplingError("Registered protocol metadata lacks registration identity or timestamp")
    if row["registration_identifier"] != str(receipt.get("osf_registration_identifier_or_url", "")):
        raise SamplingError("Protocol metadata and receipt registration identities differ")
    if row["registration_timestamp"] != str(receipt.get("registration_timestamp", "")):
        raise SamplingError("Protocol metadata and receipt registration timestamps differ")
    if row.get("implementation_last_checked_commit") != str(receipt.get("frozen_git_commit", "")):
        raise SamplingError("Protocol implementation-check commit differs from the frozen receipt commit")
    return row


def validate_official_guard(
    *, receipt_path: Path, output_directory: Path, confirmation_token: str,
    specification_path: Path, inputs: ValidatedInputs, root: Path = ROOT,
    head_commit: str | None = None, worktree_clean: bool | None = None,
    protocol_manifest_path: Path | None = None,
) -> Mapping[str, object]:
    if confirmation_token != CONFIRMATION_TOKEN:
        raise SamplingError("Official confirmation token is absent or incorrect")
    restricted_root = (root / RESTRICTED_SAMPLING_ROOT).resolve()
    resolved_output = output_directory.resolve()
    try:
        resolved_output.relative_to(restricted_root)
    except ValueError as exc:
        raise SamplingError("Official output directory is outside restricted sampling storage") from exc
    if resolved_output.exists() and any((resolved_output / name).exists() for name in OFFICIAL_OUTPUT_NAMES):
        raise SamplingError("Official output directory already contains an official draw")
    try:
        receipt_relative = receipt_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise SamplingError("Gate 2 receipt is outside the repository") from exc
    if receipt_relative != GATE_2_RECEIPT_PATH.as_posix():
        raise SamplingError(
            f"Gate 2 receipt must use {GATE_2_RECEIPT_PATH.as_posix()}"
        )
    if not receipt_path.is_file():
        raise SamplingError("Registration receipt does not exist")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SamplingError("Gate 2 receipt is not valid JSON") from exc
    if not isinstance(receipt, Mapping):
        raise SamplingError("Gate 2 receipt must be a JSON object")
    required = {
        "osf_registration_identifier_or_url",
        "registration_timestamp",
        "frozen_git_commit",
        "gate_2_passed",
        "official_sample_draw_completed",
        "expected_hashes",
    }
    missing = sorted(required - set(receipt))
    if missing:
        raise SamplingError(f"Registration receipt lacks fields: {missing}")
    if not receipt["osf_registration_identifier_or_url"] or not receipt["registration_timestamp"]:
        raise SamplingError("Registration receipt has a blank registration identity or timestamp")
    if receipt["gate_2_passed"] is not True:
        raise SamplingError("Registration receipt does not confirm Gate 2")
    if receipt["official_sample_draw_completed"] is not False:
        raise SamplingError("Registration receipt says the official draw is already completed")
    validate_protocol_draw_authorisation(
        protocol_manifest_path or root / PROTOCOL_MANIFEST_PATH, receipt
    )
    actual_head = head_commit if head_commit is not None else _git_head(root)
    clean = worktree_clean if worktree_clean is not None else _git_clean(root)
    if not clean:
        raise SamplingError("Official draw requires a clean Git worktree")
    validate_gate_2_authorisation_commit(
        root=root,
        head_commit=actual_head,
        basis_commit=str(receipt["frozen_git_commit"]),
        receipt_path=receipt_path,
    )
    expected_hashes = receipt["expected_hashes"]
    if not isinstance(expected_hashes, Mapping):
        raise SamplingError("Registration receipt expected_hashes is invalid")
    actual_hashes = {"sampling_specification": sha256_file(specification_path), **inputs.input_hashes}
    if dict(expected_hashes) != actual_hashes:
        raise SamplingError(f"Receipt hash mismatch: expected={expected_hashes}, actual={actual_hashes}")
    if len(inputs.exclusions) != 22:
        raise SamplingError("Official exclusion count is not 22")
    return receipt


def _same_real_paths(args: argparse.Namespace, root: Path) -> bool:
    actual = {Path(args.cleaned).resolve(), Path(args.exclusions).resolve(), Path(args.disagreement).resolve()}
    expected = {(root / REAL_CLEANED_PATH).resolve(), (root / REAL_EXCLUSION_PATH).resolve(), (root / REAL_HARD_PATH).resolve()}
    return actual == expected


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--validate-real-inputs", action="store_true")
    modes.add_argument("--execute-synthetic", action="store_true")
    modes.add_argument("--execute-official-draw", action="store_true")
    parser.add_argument("--specification", type=Path, default=ROOT / SPECIFICATION_PATH)
    parser.add_argument("--cleaned", type=Path)
    parser.add_argument("--exclusions", type=Path)
    parser.add_argument("--disagreement", type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--registration-receipt", type=Path)
    parser.add_argument("--confirmation-token")
    return parser


def _require_explicit_paths(args: argparse.Namespace) -> None:
    missing = [name for name in ("cleaned", "exclusions", "disagreement", "output_directory") if getattr(args, name) is None]
    if missing:
        raise SamplingError(f"Execution mode requires explicit paths: {missing}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    specification = load_sampling_specification(args.specification)
    if args.check:
        print("Sampling specification and static engine checks passed; no RNG was created.")
        return 0
    if args.validate_real_inputs:
        inputs = validate_inputs(ROOT / REAL_CLEANED_PATH, ROOT / REAL_EXCLUSION_PATH, ROOT / REAL_HARD_PATH, specification=specification, expect_real=True)
        counts = inputs.hard["hard_case_stratum"].value_counts().to_dict()
        forced = int(inputs.hard["accompanying_tag_disagreement"].sum())
        print(f"Real inputs validated without RNG creation or selection: cleaned={len(inputs.cleaned)}, exclusions={len(inputs.exclusions)}, hard={len(inputs.hard)}, strata={counts}, accompanying_tag={forced}.")
        return 0
    _require_explicit_paths(args)
    assert args.cleaned is not None and args.exclusions is not None
    assert args.disagreement is not None and args.output_directory is not None
    if args.execute_synthetic:
        if args.seed is None:
            raise SamplingError("Synthetic execution requires --seed")
        if args.seed == OFFICIAL_SEED:
            raise SamplingError("The official seed is forbidden in synthetic execution")
        if _same_real_paths(args, ROOT):
            raise SamplingError("Synthetic execution refuses the three real input paths")
        inputs = validate_inputs(args.cleaned, args.exclusions, args.disagreement)
        result = draw_samples(inputs, args.seed)
        write_sampling_outputs(result, args.output_directory, repository_commit=_git_head(ROOT), specification_path=_relative(args.specification.resolve(), ROOT), specification_hash=sha256_file(args.specification), input_hashes=inputs.input_hashes, input_paths=inputs.source_paths)
        print(f"Synthetic outputs written to {args.output_directory}")
        return 0
    if not _same_real_paths(args, ROOT):
        raise SamplingError("Official mode requires the canonical real input paths")
    if args.seed not in (None, OFFICIAL_SEED):
        raise SamplingError("Official mode may use only the registered official seed")
    if args.registration_receipt is None:
        raise SamplingError("Official mode requires --registration-receipt")
    inputs = validate_inputs(args.cleaned, args.exclusions, args.disagreement, specification=specification, expect_real=True)
    receipt = validate_official_guard(receipt_path=args.registration_receipt, output_directory=args.output_directory, confirmation_token=args.confirmation_token or "", specification_path=args.specification, inputs=inputs)
    result = draw_samples(inputs, OFFICIAL_SEED)
    write_sampling_outputs(result, args.output_directory, repository_commit=str(receipt["frozen_git_commit"]), specification_path=_relative(args.specification.resolve(), ROOT), specification_hash=sha256_file(args.specification), input_hashes=inputs.input_hashes, input_paths=inputs.source_paths)
    print("Registered DEA official draw completed exactly once.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SamplingError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
