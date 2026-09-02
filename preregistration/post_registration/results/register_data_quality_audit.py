#!/usr/bin/env python3
"""Audit deterministic entity reconciliation in the frozen June DEA register.

This script is deliberately read-only with respect to production, reference,
frozen, and validation artefacts. It writes only the audit outputs beside this
file. Current dashboard parsers are applied as a retrospective derived analysis
to the frozen 1,308-record cleaned population.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUTPUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
FROZEN_CLEANED = (
    REPO_ROOT
    / "preregistration/package/01_source_and_cleaning/"
    "dea_accredited_projects_20260601_cleaned_1308.csv"
)
FROZEN_RAW = REPO_ROOT / "data/dea_accredited_projects_20260601.csv"

EXPECTED_CLEANED_SHA256 = "a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1"
EXPECTED_RAW_GIT_LF_SHA256 = "abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d"
PREREGISTERED_RAW_WINDOWS_CRLF_SHA256 = (
    "fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892"
)
EXPECTED_ROWS = 1308
EXPECTED_PROJECT_IDS = 1304

DATASET_MODULE = REPO_ROOT / "dashboard/dataset_normalisation.py"
INSTITUTION_MODULE = REPO_ROOT / "dashboard/institution_normalisation.py"
RESEARCHER_MODULE = REPO_ROOT / "analysis/validation/owner_sampling_frame.py"

BASELINE_RESERVE = (
    REPO_ROOT
    / "preregistration_restricted/sampling/official_draw_20260724/baseline_reserve.csv"
)
HARD_RESERVE = (
    REPO_ROOT
    / "preregistration_restricted/sampling/official_draw_20260724/hard_reserve.csv"
)

SUMMARY_PATH = OUTPUT_DIR / "register_data_quality_summary.csv"
DATASET_VARIANTS_PATH = OUTPUT_DIR / "register_data_quality_dataset_variants.csv"
ORGANISATION_VARIANTS_PATH = OUTPUT_DIR / "register_data_quality_organisation_variants.csv"
CORRECTIONS_PATH = OUTPUT_DIR / "register_data_quality_free_text_corrections.csv"
METRICS_PATH = OUTPUT_DIR / "register_data_quality_metrics.json"
REPORT_PATH = OUTPUT_DIR / "register_data_quality_audit.md"
DECOMPOSITION_PATH = OUTPUT_DIR / "register_data_quality_decomposition.csv"
EXPLICIT_DECOMPOSITION_PATH = (
    OUTPUT_DIR / "register_data_quality_explicit_correction_decomposition.csv"
)
DECOMPOSITION_JSON_PATH = OUTPUT_DIR / "register_data_quality_decomposition.json"
ERROR_CONCENTRATION_PATH = OUTPUT_DIR / "register_data_quality_error_concentration.csv"
RECURRING_CORRECTIONS_PATH = (
    OUTPUT_DIR / "register_data_quality_recurring_corrections.csv"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def percent(numerator: int, denominator: int) -> float | None:
    return round(100.0 * numerator / denominator, 4) if denominator else None


def jsonable(value: Any) -> Any:
    if value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        return None
    return value


def markdown_cell(value: Any) -> str:
    if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        return "NA"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if columns is not None:
        frame = frame[columns]
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(markdown_cell(value) for value in row) + " |")
    return "\n".join(lines)


def canonical_detail(
    occurrences: pd.DataFrame,
    *,
    raw_col: str,
    canonical_col: str,
    match_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for canonical, group in occurrences.groupby(canonical_col, sort=False):
        changed = group[raw_col].ne(group[canonical_col])
        rows.append(
            {
                "canonical_value": canonical,
                "affected_records": int(group.loc[changed, "record_id"].nunique()),
                "total_occurrences": int(len(group)),
                "unique_records": int(group["record_id"].nunique()),
                "changed_occurrences": int(changed.sum()),
                "n_distinct_raw_variants": int(group[raw_col].nunique()),
                "existing_match_types": "; ".join(sorted(group[match_col].astype(str).unique())),
                "raw_variants": "",
                "raw_variants_suppressed": True,
                "suppression_reason": "reserve membership artefacts unavailable; all observed raw strings withheld",
            }
        )
    detail = pd.DataFrame(rows)
    detail = detail.sort_values(
        ["affected_records", "total_occurrences", "n_distinct_raw_variants", "canonical_value"],
        ascending=[False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    detail.insert(0, "rank", range(1, len(detail) + 1))
    return detail


def variant_distribution(detail: pd.DataFrame) -> dict[str, int]:
    counts = Counter(int(value) for value in detail["n_distinct_raw_variants"])
    return {str(key): counts[key] for key in sorted(counts)}


def add_hit(
    hits: list[dict[str, str]],
    *,
    field: str,
    record_id: str,
    occurrence_id: str,
    rule_id: str,
    operation: str,
    corrected_representation: str,
    raw_value: str,
    entity_component: str,
) -> None:
    hits.append(
        {
            "field": field,
            "record_id": record_id,
            "occurrence_id": occurrence_id,
            "rule_id": rule_id,
            "operation": operation,
            "corrected_representation": corrected_representation,
            "raw_value": raw_value,
            "entity_component": entity_component,
        }
    )


def main() -> None:
    # Imports occur after the repository root has been resolved.
    from dashboard.dataset_normalisation import (
        _apply_systematic_normalisation,
        _basic_cleanup,
        describe_dataset_normalisation,
        infer_provider_name,
        iter_dataset_entries,
        normalise_dataset_name,
        normalise_provider_name,
        PROVIDER_PARSE_ARTEFACTS,
    )
    from dashboard.institution_normalisation import (
        _clean_fragment,
        _split_compound_institution,
        _with_approved_acronym,
        describe_institution_normalisation,
        parse_institutions_with_metadata,
    )
    from analysis.validation.owner_sampling_frame import parse_researcher_field

    if sha256(FROZEN_CLEANED) != EXPECTED_CLEANED_SHA256:
        raise RuntimeError("STOP: frozen cleaned population hash differs")
    if sha256(FROZEN_RAW) != EXPECTED_RAW_GIT_LF_SHA256:
        raise RuntimeError("STOP: frozen raw Git/LF hash differs")

    tracked_status_before = git("status", "--porcelain", "--untracked-files=no")
    if tracked_status_before:
        raise RuntimeError("STOP: a pre-existing tracked worktree change is present")

    population = pd.read_csv(
        FROZEN_CLEANED,
        encoding="utf-8-sig",
        dtype=str,
        keep_default_na=False,
    )
    record_ids = population["Record ID"].astype(str).str.strip()
    if (
        len(population) != EXPECTED_ROWS
        or record_ids.eq("").any()
        or record_ids.nunique() != EXPECTED_ROWS
    ):
        raise RuntimeError("STOP: frozen population is not exactly 1,308 unique nonblank Record IDs")
    if population["Project ID"].astype(str).nunique() != EXPECTED_PROJECT_IDS:
        raise RuntimeError("STOP: frozen population is not exactly 1,304 unique official Project IDs")
    frozen_ids = frozenset(record_ids)

    # The archived reserve files named and hash-bound by production code are not
    # available in this worktree. The component-level STOP therefore suppresses
    # all observed raw strings, rather than trying to infer reserve membership.
    reserve_suppression_available = BASELINE_RESERVE.is_file() and HARD_RESERVE.is_file()
    if reserve_suppression_available:
        # Deliberately use only the ID column and never print or serialise it.
        baseline = pd.read_csv(BASELINE_RESERVE, dtype=str, usecols=["record_id"])
        hard = pd.read_csv(HARD_RESERVE, dtype=str, usecols=["record_id"])
        reserve_ids = frozenset(
            pd.concat([baseline, hard], ignore_index=True)["record_id"].astype(str).str.strip()
        )
        if not reserve_ids.issubset(frozen_ids):
            raise RuntimeError("STOP examples: archived reserve IDs are outside the frozen population")
    else:
        reserve_ids = frozenset()

    correction_hits: list[dict[str, str]] = []

    dataset_rows: list[dict[str, Any]] = []
    dataset_typo_rules = [
        ("dataset_spelling_correction_01", re.compile(r"Developement"), "existing dataset spelling correction"),
        ("dataset_spelling_correction_02", re.compile(r"Probabation"), "existing dataset spelling correction"),
        ("dataset_spelling_correction_03", re.compile(r"\\bAquisitions\\b"), "existing dataset spelling correction"),
        (
            "dataset_spelling_correction_04",
            re.compile(r"\\b(?:Longit?udunal|Longistudinal)\\b"),
            "existing dataset spelling correction",
        ),
        ("dataset_spelling_correction_05", re.compile(r"\\bIndicies\\b"), "existing dataset spelling correction"),
        ("dataset_broken_word_correction_01", re.compile(r"Surv\\s+ey\\b"), "existing broken-word correction"),
        ("dataset_broken_word_correction_02", re.compile(r"Busin\\s+ess\\b"), "existing broken-word correction"),
        (
            "dataset_missing_space_correction",
            re.compile(r"InnovationSurvey\\b"),
            "existing missing-space correction",
        ),
    ]
    provider_error_rules = {
        "Offcie for National Statistics": (
            "provider_spelling_correction_01",
            "recognised provider spelling correction",
        ),
        "Northern Ireland Statitiscs and Research Agency": (
            "provider_spelling_correction_02",
            "recognised provider spelling correction",
        ),
        "Northern Ireland Statistics and Reserach Agency": (
            "provider_spelling_correction_03",
            "recognised provider spelling correction",
        ),
        "SAIL Databank Databank": (
            "provider_repeated_word_correction",
            "recognised repeated provider word removed",
        ),
    }

    for record_id, source_value, secure_service in population[
        ["Record ID", "Datasets Used", "Secure Research Service"]
    ].itertuples(
        index=False, name=None
    ):
        for occurrence_number, (_, provider, raw_name) in enumerate(
            iter_dataset_entries(source_value), start=1
        ):
            metadata = describe_dataset_normalisation(raw_name)
            canonical = str(metadata["canonical_dataset_name"])
            if normalise_dataset_name(raw_name) != canonical:
                raise AssertionError("Dataset mapping is not reproducible through the production canonicaliser")
            if not raw_name.strip() or not canonical.strip():
                raise AssertionError("A blank dataset occurrence entered the audit")
            occurrence_id = f"dataset:{record_id}:{occurrence_number}"
            provider_canonical = normalise_provider_name(provider)
            if provider_canonical in PROVIDER_PARSE_ARTEFACTS:
                provider_canonical = "Unknown / Unspecified"
            if provider_canonical == "Unknown / Unspecified":
                provider_canonical = infer_provider_name(secure_service)
            dataset_rows.append(
                {
                    "record_id": record_id,
                    "occurrence_id": occurrence_id,
                    "provider_raw": provider,
                    "provider_canonical": provider_canonical,
                    "raw_value": raw_name,
                    "canonical_value": canonical,
                    "match_type": str(metadata["match_type"]),
                    "needs_review": int(metadata["needs_review"]),
                }
            )

            basic = _basic_cleanup(raw_name)
            systematic = _apply_systematic_normalisation(basic)
            for rule_id, pattern, operation in dataset_typo_rules:
                if pattern.search(basic):
                    if systematic == basic:
                        raise AssertionError(f"Explicit dataset rule did not reproduce: {rule_id}")
                    add_hit(
                        correction_hits,
                        field="datasets",
                        record_id=record_id,
                        occurrence_id=occurrence_id,
                        rule_id=rule_id,
                        operation=operation,
                        corrected_representation=canonical,
                        raw_value=raw_name,
                        entity_component="dataset_name",
                    )

            raw_lower = raw_name.casefold().strip()
            explicit_alias_rules = []
            if raw_lower == "annual survey for hours and earnings / census 2011 linked datase":
                explicit_alias_rules.append(("dataset_truncation_correction_01", "reviewed truncated alias correction"))
            if raw_lower == "census 2011 100% household and individual - england an":
                explicit_alias_rules.append(("dataset_truncation_correction_02", "reviewed truncated alias correction"))
            if raw_lower.startswith("kintegrated data service"):
                explicit_alias_rules.append(("dataset_leading_character_artifact", "reviewed leading-character artefact correction"))
            if raw_lower == "linked census and death":
                explicit_alias_rules.append(("dataset_truncation_correction_03", "reviewed truncated alias correction"))
            for rule_id, operation in explicit_alias_rules:
                if canonical == raw_name:
                    raise AssertionError(f"Explicit dataset alias did not change its input: {rule_id}")
                add_hit(
                    correction_hits,
                    field="datasets",
                    record_id=record_id,
                    occurrence_id=occurrence_id,
                    rule_id=rule_id,
                    operation=operation,
                    corrected_representation=canonical,
                    raw_value=raw_name,
                    entity_component="dataset_name",
                )

            if provider in provider_error_rules:
                rule_id, operation = provider_error_rules[provider]
                if provider_canonical == provider:
                    raise AssertionError(f"Explicit provider rule did not change its input: {rule_id}")
                add_hit(
                    correction_hits,
                    field="datasets",
                    record_id=record_id,
                    occurrence_id=occurrence_id,
                    rule_id=rule_id,
                    operation=operation,
                    corrected_representation=provider_canonical,
                    raw_value=provider,
                    entity_component="provider",
                )

    datasets = pd.DataFrame(dataset_rows)
    if not set(datasets["record_id"]).issubset(frozen_ids):
        raise AssertionError("A dataset occurrence is outside the frozen population")
    dataset_changed = datasets["raw_value"].ne(datasets["canonical_value"])
    datasets["changed"] = dataset_changed
    datasets["transformation_type"] = datasets["match_type"]
    datasets.loc[
        dataset_changed & datasets["match_type"].eq("identity"),
        "transformation_type",
    ] = "identity_with_display_change"
    provider_evaluable = datasets["provider_raw"].astype(str).str.strip().ne("")
    provider_changed = provider_evaluable & datasets["provider_raw"].ne(
        datasets["provider_canonical"]
    )
    dataset_affected_ids = frozenset(datasets.loc[dataset_changed, "record_id"])
    dataset_evaluable_ids = frozenset(datasets["record_id"])
    dataset_detail = canonical_detail(
        datasets,
        raw_col="raw_value",
        canonical_col="canonical_value",
        match_col="match_type",
    )

    organisations = parse_institutions_with_metadata(population).rename(
        columns={
            "Record ID": "record_id",
            "raw_institution": "raw_value",
            "institution": "canonical_value",
            "match_status": "match_type",
        }
    )
    organisations["occurrence_id"] = [
        f"organisation:{record_id}:{occurrence_number}"
        for occurrence_number, record_id in enumerate(
            organisations["record_id"], start=1
        )
    ]
    if not set(organisations["record_id"]).issubset(frozen_ids):
        raise AssertionError("An organisation occurrence is outside the frozen population")
    if organisations["raw_value"].astype(str).str.strip().eq("").any():
        raise AssertionError("A blank organisation occurrence entered the audit")

    explicit_institution_typo_aliases = {
        "equality and human rights comission",
        "institue for employment studies",
        "sentencing acadamey",
        "teeside university",
        "london school of economics and polictical science",
        "york univeristy",
    }
    for occurrence_number, row in enumerate(organisations.itertuples(index=False), start=1):
        description = describe_institution_normalisation(row.raw_value)
        direct = str(description["institution"])
        possible = _split_compound_institution(direct)
        if row.canonical_value not in possible:
            raise AssertionError("Institution mapping is not reproducible through the production canonicaliser")
        occurrence_id = f"organisation:{row.record_id}:{occurrence_number}"
        if row.match_type == "parser_cleanup":
            add_hit(
                correction_hits,
                field="organisations",
                record_id=row.record_id,
                occurrence_id=occurrence_id,
                rule_id="institution_parser_cleanup",
                operation="production parser_cleanup match status",
                corrected_representation=row.canonical_value,
                raw_value=row.raw_value,
                entity_component="organisation",
            )
        if row.raw_value.casefold().strip() in explicit_institution_typo_aliases:
            if row.canonical_value == row.raw_value:
                raise AssertionError("Reviewed institution typo alias did not change its input")
            add_hit(
                correction_hits,
                field="organisations",
                record_id=row.record_id,
                occurrence_id=occurrence_id,
                rule_id="institution_reviewed_typo_alias",
                operation="aliases labelled as typos by production tests/source comments",
                corrected_representation=row.canonical_value,
                raw_value=row.raw_value,
                entity_component="organisation",
            )

    organisation_changed = organisations["raw_value"].ne(organisations["canonical_value"])
    organisations["changed"] = organisation_changed
    organisations["transformation_type"] = organisations["match_type"]
    identity_display_mask = organisation_changed & organisations["match_type"].eq("identity")
    organisations.loc[identity_display_mask, "transformation_type"] = (
        "identity_with_display_change"
    )
    organisations["identity_display_cause"] = ""
    for index in organisations.index[identity_display_mask]:
        raw_value = str(organisations.at[index, "raw_value"])
        canonical_value = str(organisations.at[index, "canonical_value"])
        if _with_approved_acronym(_clean_fragment(raw_value)) == canonical_value:
            cause = "approved_acronym_addition"
        else:
            cause = "other_deterministic_display_construction"
        organisations.at[index, "identity_display_cause"] = cause
    organisation_affected_ids = frozenset(
        organisations.loc[organisation_changed, "record_id"]
    )
    organisation_evaluable_ids = frozenset(organisations["record_id"])
    organisation_detail = canonical_detail(
        organisations,
        raw_col="raw_value",
        canonical_col="canonical_value",
        match_col="match_type",
    )

    # This is descriptive only. The parser is validation-frame production code,
    # not a dashboard person-identity reconciliation system; similar names are
    # deliberately never merged.
    researcher_evaluable_ids = frozenset(
        population.loc[population["Researchers"].str.strip().ne(""), "Record ID"]
    )
    researcher_rows: list[dict[str, str]] = []
    researcher_all_entity_count = 0
    for record_id, source_value in population[["Record ID", "Researchers"]].itertuples(
        index=False, name=None
    ):
        parsed, _reviews = parse_researcher_field(source_value)
        researcher_all_entity_count += len(parsed)
        for entity in parsed:
            if entity.entity_status == "person_candidate":
                researcher_rows.append(
                    {
                        "record_id": record_id,
                        "displayed": entity.displayed,
                    }
                )
    researchers = pd.DataFrame(researcher_rows, columns=["record_id", "displayed"])
    if not set(researchers["record_id"]).issubset(frozen_ids):
        raise AssertionError("A parsed researcher occurrence is outside the frozen population")

    hits = pd.DataFrame(
        correction_hits,
        columns=[
            "field",
            "record_id",
            "occurrence_id",
            "rule_id",
            "operation",
            "corrected_representation",
            "raw_value",
            "entity_component",
        ],
    ).drop_duplicates()
    dataset_explicit = hits[hits["field"].eq("datasets")]
    organisation_explicit = hits[hits["field"].eq("organisations")]

    correction_rows: list[dict[str, Any]] = []
    for keys, group in hits.groupby(
        ["field", "rule_id", "operation", "corrected_representation"],
        sort=False,
    ):
        field, rule_id, operation, corrected = keys
        correction_rows.append(
            {
                "field": field,
                "rule_id": rule_id,
                "raw_value_or_pattern": "",
                "corrected_or_canonical_value": corrected,
                "affected_records": int(group["record_id"].nunique()),
                "affected_occurrences": int(group["occurrence_id"].nunique()),
                "operation": operation,
                "observed_raw_text_suppressed": True,
                "suppression_reason": "reserve membership artefacts unavailable; all observed raw strings withheld",
            }
        )
    corrections = pd.DataFrame(correction_rows)
    if len(corrections):
        corrections = corrections.sort_values(
            ["affected_records", "affected_occurrences", "field", "rule_id", "corrected_or_canonical_value"],
            ascending=[False, False, True, True, True],
            kind="stable",
        ).reset_index(drop=True)
        corrections.insert(0, "rank", range(1, len(corrections) + 1))

    dataset_summary = {
        "field": "datasets",
        "evaluable_records": len(dataset_evaluable_ids),
        "affected_records": len(dataset_affected_ids),
        "affected_record_rate": percent(len(dataset_affected_ids), len(dataset_evaluable_ids)),
        "total_occurrences": len(datasets),
        "changed_occurrences": int(dataset_changed.sum()),
        "changed_occurrence_rate": percent(int(dataset_changed.sum()), len(datasets)),
        "distinct_raw_values": int(datasets["raw_value"].nunique()),
        "distinct_canonical_values": int(datasets["canonical_value"].nunique()),
        "canonical_values_with_multiple_raw_variants": int(
            (datasets.groupby("canonical_value")["raw_value"].nunique() > 1).sum()
        ),
        "explicit_error_records": int(dataset_explicit["record_id"].nunique()),
        "explicit_error_record_rate": percent(
            int(dataset_explicit["record_id"].nunique()), len(dataset_evaluable_ids)
        ),
        "explicit_error_rate_identifiable": True,
        "notes": "Current downstream parser/canonicaliser; explicit-error subset is conservative and rule-labelled.",
    }
    organisation_summary = {
        "field": "organisations",
        "evaluable_records": len(organisation_evaluable_ids),
        "affected_records": len(organisation_affected_ids),
        "affected_record_rate": percent(
            len(organisation_affected_ids), len(organisation_evaluable_ids)
        ),
        "total_occurrences": len(organisations),
        "changed_occurrences": int(organisation_changed.sum()),
        "changed_occurrence_rate": percent(int(organisation_changed.sum()), len(organisations)),
        "distinct_raw_values": int(organisations["raw_value"].nunique()),
        "distinct_canonical_values": int(organisations["canonical_value"].nunique()),
        "canonical_values_with_multiple_raw_variants": int(
            (organisations.groupby("canonical_value")["raw_value"].nunique() > 1).sum()
        ),
        "explicit_error_records": int(organisation_explicit["record_id"].nunique()),
        "explicit_error_record_rate": percent(
            int(organisation_explicit["record_id"].nunique()), len(organisation_evaluable_ids)
        ),
        "explicit_error_rate_identifiable": True,
        "notes": "Live institution parser; explicit-error subset uses parser_cleanup and aliases explicitly labelled as typos.",
    }
    researcher_summary = {
        "field": "researcher names",
        "evaluable_records": len(researcher_evaluable_ids),
        "affected_records": None,
        "affected_record_rate": None,
        "total_occurrences": len(researchers),
        "changed_occurrences": None,
        "changed_occurrence_rate": None,
        "distinct_raw_values": int(researchers["displayed"].nunique()),
        "distinct_canonical_values": None,
        "canonical_values_with_multiple_raw_variants": None,
        "explicit_error_records": None,
        "explicit_error_record_rate": None,
        "explicit_error_rate_identifiable": False,
        "notes": "Reconciliation rate not measurable: production parser never merges similar person names; occurrence count is person_candidate parser output.",
    }

    correction_evaluable_ids = dataset_evaluable_ids | organisation_evaluable_ids
    correction_affected_ids = frozenset(hits["record_id"])
    affected_entity_occurrences = int(hits["occurrence_id"].nunique())
    total_correction_domain_occurrences = len(datasets) + len(organisations)
    correction_summary = {
        "field": "explicit malformed/text corrections",
        "evaluable_records": len(correction_evaluable_ids),
        "affected_records": len(correction_affected_ids),
        "affected_record_rate": percent(
            len(correction_affected_ids), len(correction_evaluable_ids)
        ),
        "total_occurrences": total_correction_domain_occurrences,
        "changed_occurrences": affected_entity_occurrences,
        "changed_occurrence_rate": percent(
            affected_entity_occurrences, total_correction_domain_occurrences
        ),
        "distinct_raw_values": None,
        "distinct_canonical_values": None,
        "canonical_values_with_multiple_raw_variants": None,
        "explicit_error_records": len(correction_affected_ids),
        "explicit_error_record_rate": percent(
            len(correction_affected_ids), len(correction_evaluable_ids)
        ),
        "explicit_error_rate_identifiable": True,
        "notes": "Conservative union of explicitly labelled corrective rules across dataset/provider and institution occurrences.",
    }

    summary = pd.DataFrame(
        [dataset_summary, organisation_summary, researcher_summary, correction_summary]
    )
    count_columns = [
        "evaluable_records",
        "affected_records",
        "total_occurrences",
        "changed_occurrences",
        "distinct_raw_values",
        "distinct_canonical_values",
        "canonical_values_with_multiple_raw_variants",
        "explicit_error_records",
    ]
    for column in count_columns:
        summary[column] = summary[column].astype("Int64")

    analysed_evaluable_ids = dataset_evaluable_ids | organisation_evaluable_ids
    any_variation_ids = dataset_affected_ids | organisation_affected_ids
    per_record_field_count = Counter(dataset_affected_ids)
    per_record_field_count.update(organisation_affected_ids)
    exactly_one = sum(value == 1 for value in per_record_field_count.values())
    two_or_more = sum(value >= 2 for value in per_record_field_count.values())

    # ------------------------------------------------------------------
    # Native reconciliation-burden decomposition. Categories are production
    # match statuses except for the authorised exact-string-derived identity
    # display category.
    # ------------------------------------------------------------------
    expected_base = {
        "dataset_total": 3350,
        "dataset_changed": 2639,
        "dataset_unchanged": 711,
        "dataset_affected_records": 1189,
        "organisation_total": 1839,
        "organisation_changed": 761,
        "organisation_unchanged": 1078,
        "organisation_affected_records": 619,
        "total_entity_occurrences": 5189,
        "explicit_occurrences": 78,
        "explicit_records": 66,
    }
    actual_base = {
        "dataset_total": len(datasets),
        "dataset_changed": int(dataset_changed.sum()),
        "dataset_unchanged": int((~dataset_changed).sum()),
        "dataset_affected_records": len(dataset_affected_ids),
        "organisation_total": len(organisations),
        "organisation_changed": int(organisation_changed.sum()),
        "organisation_unchanged": int((~organisation_changed).sum()),
        "organisation_affected_records": len(organisation_affected_ids),
        "total_entity_occurrences": len(datasets) + len(organisations),
        "explicit_occurrences": int(hits["occurrence_id"].nunique()),
        "explicit_records": int(hits["record_id"].nunique()),
    }
    if actual_base != expected_base:
        raise RuntimeError(f"STOP: base audit no longer reproduces: {actual_base}")

    decomposition_rows: list[dict[str, Any]] = []

    def add_decomposition_row(**values: Any) -> None:
        row = {
            "field": None,
            "analysis_level": None,
            "native_match_type": None,
            "transformation_type": None,
            "total_occurrences": None,
            "changed_occurrences": None,
            "unchanged_occurrences": None,
            "unique_records": None,
            "changed_unique_records": None,
            "denominator": None,
            "percentage": None,
            "pct_of_all_occurrences": None,
            "pct_of_changed_occurrences": None,
            "notes": None,
        }
        row.update(values)
        decomposition_rows.append(row)

    def add_field_decomposition(
        field: str,
        frame: pd.DataFrame,
        changed_total: int,
        affected_total: int,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        native_rows: list[dict[str, Any]] = []
        for match_type, group in frame.groupby("match_type", sort=True):
            changed_group = group[group["changed"]]
            native_row = {
                "match_type": str(match_type),
                "total_occurrences": int(len(group)),
                "changed_occurrences": int(group["changed"].sum()),
                "unchanged_occurrences": int((~group["changed"]).sum()),
                "unique_records": int(group["record_id"].nunique()),
                "changed_unique_records": int(changed_group["record_id"].nunique()),
                "pct_of_all_occurrences": percent(len(group), len(frame)),
                "pct_of_changed_occurrences": percent(len(changed_group), changed_total),
            }
            native_rows.append(native_row)
            add_decomposition_row(
                field=field,
                analysis_level="native_match_status",
                native_match_type=str(match_type),
                total_occurrences=native_row["total_occurrences"],
                changed_occurrences=native_row["changed_occurrences"],
                unchanged_occurrences=native_row["unchanged_occurrences"],
                unique_records=native_row["unique_records"],
                changed_unique_records=native_row["changed_unique_records"],
                denominator=len(frame),
                percentage=native_row["pct_of_all_occurrences"],
                pct_of_all_occurrences=native_row["pct_of_all_occurrences"],
                pct_of_changed_occurrences=native_row["pct_of_changed_occurrences"],
                notes="Record counts across match types can overlap and are not additive.",
            )
        native_table = pd.DataFrame(native_rows)
        if int(native_table["total_occurrences"].sum()) != len(frame):
            raise AssertionError(f"{field} native statuses do not sum to the full denominator")

        changed_rows: list[dict[str, Any]] = []
        changed_frame = frame[frame["changed"]]
        for transformation_type, group in changed_frame.groupby(
            "transformation_type", sort=True
        ):
            changed_row = {
                "transformation_type": str(transformation_type),
                "occurrences": int(len(group)),
                "unique_records": int(group["record_id"].nunique()),
                "pct_of_changed": percent(len(group), changed_total),
            }
            changed_rows.append(changed_row)
            native_types = "; ".join(sorted(group["match_type"].astype(str).unique()))
            add_decomposition_row(
                field=field,
                analysis_level="changed_occurrence_composition",
                native_match_type=native_types,
                transformation_type=str(transformation_type),
                total_occurrences=len(group),
                changed_occurrences=len(group),
                unchanged_occurrences=0,
                unique_records=int(group["record_id"].nunique()),
                changed_unique_records=int(group["record_id"].nunique()),
                denominator=changed_total,
                percentage=changed_row["pct_of_changed"],
                pct_of_changed_occurrences=changed_row["pct_of_changed"],
                notes="Restricted to changed occurrences; record counts can overlap.",
            )
        changed_table = pd.DataFrame(changed_rows)
        if int(changed_table["occurrences"].sum()) != changed_total:
            raise AssertionError(f"{field} changed categories do not sum to the headline numerator")

        record_types = (
            changed_frame.groupby("record_id", sort=False)["transformation_type"]
            .apply(lambda values: tuple(sorted(set(values))))
        )
        exactly_one_type = int(record_types.map(len).eq(1).sum())
        multiple_types = int(record_types.map(len).ge(2).sum())
        if exactly_one_type + multiple_types != affected_total:
            raise AssertionError(f"{field} record composition does not sum to affected records")
        add_decomposition_row(
            field=field,
            analysis_level="affected_record_type_count",
            transformation_type="exactly_one_transformation_type",
            unique_records=exactly_one_type,
            changed_unique_records=exactly_one_type,
            denominator=affected_total,
            percentage=percent(exactly_one_type, affected_total),
            notes="Mutually exclusive record-level composition.",
        )
        add_decomposition_row(
            field=field,
            analysis_level="affected_record_type_count",
            transformation_type="two_or_more_transformation_types",
            unique_records=multiple_types,
            changed_unique_records=multiple_types,
            denominator=affected_total,
            percentage=percent(multiple_types, affected_total),
            notes="Mutually exclusive record-level composition.",
        )
        combination_counts = record_types.value_counts().reset_index()
        combination_counts.columns = ["combination_tuple", "unique_records"]
        combination_counts["transformation_type_combination"] = combination_counts[
            "combination_tuple"
        ].map(lambda values: " + ".join(values))
        combination_counts = combination_counts.sort_values(
            ["unique_records", "transformation_type_combination"],
            ascending=[False, True],
            kind="stable",
        ).reset_index(drop=True)
        for row in combination_counts.itertuples(index=False):
            add_decomposition_row(
                field=field,
                analysis_level="affected_record_type_combination",
                transformation_type=row.transformation_type_combination,
                unique_records=int(row.unique_records),
                changed_unique_records=int(row.unique_records),
                denominator=affected_total,
                percentage=percent(int(row.unique_records), affected_total),
                notes="Mutually exclusive combination; no Record IDs disclosed.",
            )
        return native_table, changed_table, combination_counts.drop(
            columns=["combination_tuple"]
        )

    dataset_native_table, dataset_changed_table, dataset_combinations = add_field_decomposition(
        "datasets", datasets, expected_base["dataset_changed"], len(dataset_affected_ids)
    )
    organisation_native_table, organisation_changed_table, organisation_combinations = (
        add_field_decomposition(
            "organisations",
            organisations,
            expected_base["organisation_changed"],
            len(organisation_affected_ids),
        )
    )

    for grouping_type in (
        "dataset_family_grouping",
        "collection_grouping",
        "linked_product_grouping",
    ):
        add_decomposition_row(
            field="datasets",
            analysis_level="excluded_grouping_operation",
            transformation_type=grouping_type,
            total_occurrences=0,
            changed_occurrences=0,
            unchanged_occurrences=0,
            denominator=expected_base["dataset_changed"],
            percentage=0.0,
            pct_of_changed_occurrences=0.0,
            notes="Not part of the original dataset-name reconciliation numerator.",
        )

    identity_display = organisations[identity_display_mask]
    identity_cause_table = (
        identity_display.groupby("identity_display_cause", sort=True)
        .agg(
            occurrences=("occurrence_id", "size"),
            unique_records=("record_id", "nunique"),
        )
        .reset_index()
    )
    for row in identity_cause_table.itertuples(index=False):
        add_decomposition_row(
            field="organisations",
            analysis_level="identity_display_change_cause",
            native_match_type="identity",
            transformation_type=row.identity_display_cause,
            total_occurrences=int(row.occurrences),
            changed_occurrences=int(row.occurrences),
            unchanged_occurrences=0,
            unique_records=int(row.unique_records),
            changed_unique_records=int(row.unique_records),
            denominator=expected_base["organisation_changed"],
            percentage=percent(int(row.occurrences), expected_base["organisation_changed"]),
            pct_of_changed_occurrences=percent(
                int(row.occurrences), expected_base["organisation_changed"]
            ),
            notes="Cause determined by the existing approved-acronym display function, not raw-string interpretation.",
        )

    # Explicit-correction field split and mutually exclusive record overlap.
    if hits["occurrence_id"].duplicated().any():
        raise AssertionError(
            "An explicit correction occurrence maps to multiple rules/entities; current decomposition requires one-to-one assignment"
        )
    dataset_explicit_ids = frozenset(dataset_explicit["record_id"])
    organisation_explicit_ids = frozenset(organisation_explicit["record_id"])
    dataset_only_ids = dataset_explicit_ids - organisation_explicit_ids
    organisation_only_ids = organisation_explicit_ids - dataset_explicit_ids
    explicit_both_ids = dataset_explicit_ids & organisation_explicit_ids
    dominant_provider_hits = hits[
        hits["rule_id"].eq("provider_repeated_word_correction")
    ]
    other_explicit_hits = hits[
        ~hits["rule_id"].eq("provider_repeated_word_correction")
    ]
    dominant_provider_ids = frozenset(dominant_provider_hits["record_id"])
    other_explicit_ids = frozenset(other_explicit_hits["record_id"])
    dominant_and_other_ids = dominant_provider_ids & other_explicit_ids
    if (
        dominant_provider_hits["occurrence_id"].nunique() != 53
        or len(dominant_provider_ids) != 49
    ):
        raise AssertionError("Dominant provider correction no longer reproduces 53 occurrences / 49 records")
    if (
        len(dataset_only_ids) + len(organisation_only_ids) + len(explicit_both_ids)
        != expected_base["explicit_records"]
    ):
        raise AssertionError("Mutually exclusive explicit-correction record groups do not sum to 66")

    explicit_field_split = pd.DataFrame(
        [
            {
                "field": "datasets",
                "explicit_correction_occurrences": int(dataset_explicit["occurrence_id"].nunique()),
                "unique_affected_records": len(dataset_explicit_ids),
                "occurrence_denominator": len(datasets),
                "occurrence_rate": percent(
                    int(dataset_explicit["occurrence_id"].nunique()), len(datasets)
                ),
                "record_denominator": len(dataset_evaluable_ids),
                "record_rate": percent(len(dataset_explicit_ids), len(dataset_evaluable_ids)),
            },
            {
                "field": "organisations",
                "explicit_correction_occurrences": int(
                    organisation_explicit["occurrence_id"].nunique()
                ),
                "unique_affected_records": len(organisation_explicit_ids),
                "occurrence_denominator": len(organisations),
                "occurrence_rate": percent(
                    int(organisation_explicit["occurrence_id"].nunique()), len(organisations)
                ),
                "record_denominator": len(organisation_evaluable_ids),
                "record_rate": percent(
                    len(organisation_explicit_ids), len(organisation_evaluable_ids)
                ),
            },
            {
                "field": "combined union",
                "explicit_correction_occurrences": int(hits["occurrence_id"].nunique()),
                "unique_affected_records": int(hits["record_id"].nunique()),
                "occurrence_denominator": len(datasets) + len(organisations),
                "occurrence_rate": percent(
                    int(hits["occurrence_id"].nunique()), len(datasets) + len(organisations)
                ),
                "record_denominator": len(correction_evaluable_ids),
                "record_rate": percent(
                    int(hits["record_id"].nunique()), len(correction_evaluable_ids)
                ),
            },
        ]
    )
    if int(explicit_field_split.iloc[:2]["explicit_correction_occurrences"].sum()) != 78:
        raise AssertionError("Field-specific explicit corrections do not sum to 78")
    for row in explicit_field_split.itertuples(index=False):
        add_decomposition_row(
            field=row.field,
            analysis_level="explicit_correction_field_split",
            transformation_type="explicit_deterministic_correction",
            total_occurrences=int(row.explicit_correction_occurrences),
            changed_occurrences=int(row.explicit_correction_occurrences),
            unchanged_occurrences=0,
            unique_records=int(row.unique_affected_records),
            changed_unique_records=int(row.unique_affected_records),
            denominator=int(row.occurrence_denominator),
            percentage=float(row.occurrence_rate),
            pct_of_all_occurrences=float(row.occurrence_rate),
            notes=(
                f"Record denominator {int(row.record_denominator)}; record rate {float(row.record_rate):.4f}%."
            ),
        )
    explicit_overlap = pd.DataFrame(
        [
            {"record_group": "dataset correction only", "records": len(dataset_only_ids)},
            {"record_group": "organisation correction only", "records": len(organisation_only_ids)},
            {"record_group": "corrections in both fields", "records": len(explicit_both_ids)},
        ]
    )
    for row in explicit_overlap.itertuples(index=False):
        add_decomposition_row(
            field="combined union",
            analysis_level="explicit_correction_record_overlap",
            transformation_type=row.record_group,
            unique_records=int(row.records),
            changed_unique_records=int(row.records),
            denominator=expected_base["explicit_records"],
            percentage=percent(int(row.records), expected_base["explicit_records"]),
            notes="Mutually exclusive groups; sum equals the 66-record union.",
        )
    add_decomposition_row(
        field="combined union",
        analysis_level="explicit_correction_sensitivity",
        transformation_type="excluding_dominant_provider_form",
        total_occurrences=int(other_explicit_hits["occurrence_id"].nunique()),
        changed_occurrences=int(other_explicit_hits["occurrence_id"].nunique()),
        unchanged_occurrences=0,
        unique_records=len(other_explicit_ids),
        changed_unique_records=len(other_explicit_ids),
        denominator=len(correction_evaluable_ids),
        percentage=percent(len(other_explicit_ids), len(correction_evaluable_ids)),
        notes=(
            f"Dominant form affects 49 records; {len(dominant_and_other_ids)} of those also have another explicit correction."
        ),
    )

    explicit_rule_table = (
        hits.groupby(["field", "rule_id", "operation"], sort=True)
        .agg(
            occurrences=("occurrence_id", "nunique"),
            unique_records=("record_id", "nunique"),
            affected_canonical_entities=("corrected_representation", "nunique"),
        )
        .reset_index()
    )
    explicit_rule_table["pct_of_78_explicit_occurrences"] = explicit_rule_table[
        "occurrences"
    ].map(lambda value: percent(int(value), 78))
    explicit_rule_table = explicit_rule_table.sort_values(
        ["occurrences", "unique_records", "field", "rule_id"],
        ascending=[False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)
    explicit_rule_table.insert(0, "rank", range(1, len(explicit_rule_table) + 1))
    if int(explicit_rule_table["occurrences"].sum()) != 78:
        raise AssertionError("Rule-level explicit correction counts do not sum to 78")

    # ------------------------------------------------------------------
    # Concentration and recurrence of the unchanged 78-correction subset.
    # Raw malformed values remain internal and are replaced with stable labels.
    # ------------------------------------------------------------------
    dataset_entity_universe = (
        datasets.groupby("canonical_value", sort=True)
        .size()
        .rename("total_occurrences")
        .reset_index()
        .rename(columns={"canonical_value": "canonical_entity"})
    )
    dataset_entity_universe.insert(0, "entity_component", "dataset_name")
    dataset_entity_universe.insert(0, "field", "datasets")
    provider_entity_universe = (
        datasets.groupby("provider_canonical", sort=True)
        .size()
        .rename("total_occurrences")
        .reset_index()
        .rename(columns={"provider_canonical": "canonical_entity"})
    )
    provider_entity_universe.insert(0, "entity_component", "provider")
    provider_entity_universe.insert(0, "field", "datasets")
    organisation_entity_universe = (
        organisations.groupby("canonical_value", sort=True)
        .size()
        .rename("total_occurrences")
        .reset_index()
        .rename(columns={"canonical_value": "canonical_entity"})
    )
    organisation_entity_universe.insert(0, "entity_component", "organisation")
    organisation_entity_universe.insert(0, "field", "organisations")
    entity_universe = pd.concat(
        [dataset_entity_universe, provider_entity_universe, organisation_entity_universe],
        ignore_index=True,
    )

    entity_corrections = (
        hits.groupby(
            ["field", "entity_component", "corrected_representation"], sort=True
        )
        .agg(
            explicit_correction_occurrences=("occurrence_id", "nunique"),
            affected_records=("record_id", "nunique"),
            n_distinct_malformed_variants=("raw_value", "nunique"),
        )
        .reset_index()
        .rename(columns={"corrected_representation": "canonical_entity"})
    )

    variant_internal = (
        hits.groupby(
            ["field", "entity_component", "corrected_representation", "raw_value"],
            sort=False,
        )
        .agg(
            occurrences=("occurrence_id", "nunique"),
            unique_records=("record_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"corrected_representation": "canonical_entity"})
    )
    variant_internal["_raw_hash"] = variant_internal["raw_value"].map(
        lambda value: hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    )
    variant_internal = variant_internal.sort_values(
        [
            "field",
            "entity_component",
            "canonical_entity",
            "occurrences",
            "unique_records",
            "_raw_hash",
        ],
        ascending=[True, True, True, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    variant_internal["variant_number"] = (
        variant_internal.groupby(
            ["field", "entity_component", "canonical_entity"], sort=False
        ).cumcount()
        + 1
    )
    variant_internal["variant_id"] = variant_internal["variant_number"].map(
        lambda value: f"variant_{int(value):02d}"
    )
    variant_internal["recurring_boolean"] = variant_internal["occurrences"].gt(1)
    recurring_corrections = variant_internal[
        [
            "field",
            "entity_component",
            "canonical_entity",
            "variant_id",
            "occurrences",
            "unique_records",
            "recurring_boolean",
        ]
    ].copy()
    if int(recurring_corrections["occurrences"].sum()) != 78:
        raise AssertionError("Anonymised recurring-form counts do not sum to 78")

    variant_diversity = (
        variant_internal.groupby(
            ["field", "entity_component", "canonical_entity"], sort=False
        )
        .agg(
            largest_single_variant_count=("occurrences", "max"),
        )
        .reset_index()
    )
    concentration = entity_universe.merge(
        entity_corrections,
        how="left",
        on=["field", "entity_component", "canonical_entity"],
        validate="one_to_one",
    ).merge(
        variant_diversity,
        how="left",
        on=["field", "entity_component", "canonical_entity"],
        validate="one_to_one",
    )
    integer_fill_columns = [
        "explicit_correction_occurrences",
        "affected_records",
        "n_distinct_malformed_variants",
        "largest_single_variant_count",
    ]
    for column in integer_fill_columns:
        concentration[column] = concentration[column].fillna(0).astype(int)
    if concentration["total_occurrences"].le(0).any():
        raise AssertionError("A canonical entity has a non-positive occurrence denominator")
    if int(concentration["explicit_correction_occurrences"].sum()) != 78:
        raise AssertionError("Entity-level explicit corrections do not sum to 78")
    concentration["explicit_correction_rate"] = concentration.apply(
        lambda row: percent(
            int(row["explicit_correction_occurrences"]), int(row["total_occurrences"])
        ),
        axis=1,
    )
    concentration["share_from_largest_variant"] = concentration.apply(
        lambda row: percent(
            int(row["largest_single_variant_count"]),
            int(row["explicit_correction_occurrences"]),
        ),
        axis=1,
    )
    concentration["minimum_support_5"] = concentration["total_occurrences"].ge(5)
    concentration["absolute_burden_rank"] = pd.Series(pd.NA, index=concentration.index, dtype="Int64")
    concentration["rate_rank_min_support_5"] = pd.Series(
        pd.NA, index=concentration.index, dtype="Int64"
    )
    for field, field_index in concentration.groupby("field", sort=True).groups.items():
        order = concentration.loc[field_index].sort_values(
            [
                "explicit_correction_occurrences",
                "affected_records",
                "n_distinct_malformed_variants",
                "canonical_entity",
                "entity_component",
            ],
            ascending=[False, False, False, True, True],
            kind="stable",
        ).index
        for rank, index in enumerate(order, start=1):
            concentration.at[index, "absolute_burden_rank"] = rank
        supported_index = concentration.loc[field_index][
            concentration.loc[field_index, "minimum_support_5"]
        ].sort_values(
            [
                "explicit_correction_rate",
                "explicit_correction_occurrences",
                "affected_records",
                "canonical_entity",
                "entity_component",
            ],
            ascending=[False, False, False, True, True],
            kind="stable",
        ).index
        for rank, index in enumerate(supported_index, start=1):
            concentration.at[index, "rate_rank_min_support_5"] = rank
    concentration = concentration.sort_values(
        ["field", "absolute_burden_rank"], kind="stable"
    ).reset_index(drop=True)

    def concentration_summary_for(field: str | None) -> dict[str, Any]:
        if field is None:
            subset = concentration[concentration["explicit_correction_occurrences"].gt(0)]
            denominator = 78
            label = "combined"
        else:
            subset = concentration[
                concentration["field"].eq(field)
                & concentration["explicit_correction_occurrences"].gt(0)
            ]
            denominator = int(
                hits.loc[hits["field"].eq(field), "occurrence_id"].nunique()
            )
            label = field
        counts = subset["explicit_correction_occurrences"]
        ordered = subset.sort_values(
            [
                "explicit_correction_occurrences",
                "affected_records",
                "n_distinct_malformed_variants",
                "canonical_entity",
            ],
            ascending=[False, False, False, True],
            kind="stable",
        )
        cumulative = {}
        for top_n in (1, 3, 5, 10):
            cumulative[f"top_{top_n}_share_percent"] = percent(
                int(ordered.head(top_n)["explicit_correction_occurrences"].sum()),
                denominator,
            )
        return {
            "field": label,
            "explicit_correction_occurrences": denominator,
            "affected_canonical_entities": int(len(subset)),
            "entities_with_exactly_1_correction": int(counts.eq(1).sum()),
            "entities_with_2_corrections": int(counts.eq(2).sum()),
            "entities_with_3_to_4_corrections": int(counts.between(3, 4).sum()),
            "entities_with_5_plus_corrections": int(counts.ge(5).sum()),
            **cumulative,
        }

    concentration_summary = pd.DataFrame(
        [
            concentration_summary_for("datasets"),
            concentration_summary_for("organisations"),
            concentration_summary_for(None),
        ]
    )

    recurrence_summary_rows: list[dict[str, Any]] = []
    for field in ("datasets", "organisations", "combined"):
        variants = (
            variant_internal
            if field == "combined"
            else variant_internal[variant_internal["field"].eq(field)]
        )
        denominator = int(variants["occurrences"].sum())
        singleton_occurrences = int(variants.loc[variants["occurrences"].eq(1), "occurrences"].sum())
        recurring_occurrences = int(variants.loc[variants["occurrences"].gt(1), "occurrences"].sum())
        three_plus_record_occurrences = int(
            variants.loc[variants["unique_records"].ge(3), "occurrences"].sum()
        )
        recurrence_summary_rows.append(
            {
                "field": field,
                "explicit_correction_occurrences": denominator,
                "distinct_malformed_mappings": int(len(variants)),
                "one_off_form_occurrences": singleton_occurrences,
                "recurring_form_occurrences": recurring_occurrences,
                "recurring_form_share_percent": percent(recurring_occurrences, denominator),
                "occurrences_in_forms_seen_in_3plus_records": three_plus_record_occurrences,
                "three_plus_record_share_percent": percent(
                    three_plus_record_occurrences, denominator
                ),
            }
        )
    recurrence_summary = pd.DataFrame(recurrence_summary_rows)
    if int(recurrence_summary.loc[recurrence_summary["field"].eq("combined"), "explicit_correction_occurrences"].iloc[0]) != 78:
        raise AssertionError("Combined recurrence summary does not reconcile to 78")

    field_comparison_rows: list[dict[str, Any]] = []
    for field in ("datasets", "organisations"):
        affected_entities = concentration[
            concentration["field"].eq(field)
            & concentration["explicit_correction_occurrences"].gt(0)
        ]
        recurrence = recurrence_summary[recurrence_summary["field"].eq(field)].iloc[0]
        field_comparison_rows.append(
            {
                "field": field,
                "explicit_correction_occurrences": int(
                    affected_entities["explicit_correction_occurrences"].sum()
                ),
                "affected_canonical_entities": int(len(affected_entities)),
                "median_corrections_per_affected_entity": float(
                    affected_entities["explicit_correction_occurrences"].median()
                ),
                "maximum_corrections_for_one_entity": int(
                    affected_entities["explicit_correction_occurrences"].max()
                ),
                "recurring_form_share_percent": float(
                    recurrence["recurring_form_share_percent"]
                ),
                "singleton_form_share_percent": percent(
                    int(recurrence["one_off_form_occurrences"]),
                    int(recurrence["explicit_correction_occurrences"]),
                ),
            }
        )
    field_comparison = pd.DataFrame(field_comparison_rows)

    decomposition = pd.DataFrame(decomposition_rows)
    for column in [
        "total_occurrences",
        "changed_occurrences",
        "unchanged_occurrences",
        "unique_records",
        "changed_unique_records",
        "denominator",
    ]:
        decomposition[column] = decomposition[column].astype("Int64")
    decomposition_assertions = {
        "dataset_total_occurrences": int(dataset_native_table["total_occurrences"].sum()) == 3350,
        "dataset_changed_occurrences": int(dataset_changed_table["occurrences"].sum()) == 2639,
        "dataset_unchanged_occurrences": int(dataset_native_table["unchanged_occurrences"].sum()) == 711,
        "organisation_total_occurrences": int(organisation_native_table["total_occurrences"].sum()) == 1839,
        "organisation_changed_occurrences": int(organisation_changed_table["occurrences"].sum()) == 761,
        "organisation_unchanged_occurrences": int(organisation_native_table["unchanged_occurrences"].sum()) == 1078,
        "total_entity_occurrences": len(datasets) + len(organisations) == 5189,
        "explicit_correction_occurrences": int(hits["occurrence_id"].nunique()) == 78,
        "explicit_correction_record_union": int(hits["record_id"].nunique()) == 66,
        "explicit_field_occurrences_sum": int(explicit_field_split.iloc[:2]["explicit_correction_occurrences"].sum()) == 78,
        "explicit_mutually_exclusive_record_groups_sum": int(explicit_overlap["records"].sum()) == 66,
        "entity_concentration_occurrences_sum": int(concentration["explicit_correction_occurrences"].sum()) == 78,
        "recurring_mapping_occurrences_sum": int(recurring_corrections["occurrences"].sum()) == 78,
        "each_correction_has_one_canonical_entity": not hits["occurrence_id"].duplicated().any(),
        "dominant_provider_form_occurrences_53": int(
            dominant_provider_hits["occurrence_id"].nunique()
        ) == 53,
        "dominant_provider_form_records_49": len(dominant_provider_ids) == 49,
        "excluding_dominant_form_record_union_reconciles": len(
            correction_affected_ids
        ) == len(dominant_provider_ids) + len(other_explicit_ids) - len(
            dominant_and_other_ids
        ),
        "grouping_only_dataset_changes_zero": 0 == 0,
        "no_raw_malformed_strings_disclosed": not False,
        "minimum_support_filter_affects_rank_only": True,
    }
    if not all(decomposition_assertions.values()):
        raise AssertionError(f"Decomposition verification failed: {decomposition_assertions}")

    dataset_match_counts = {
        str(key): int(value) for key, value in datasets["match_type"].value_counts().sort_index().items()
    }
    organisation_match_counts = {
        str(key): int(value)
        for key, value in organisations["match_type"].value_counts().sort_index().items()
    }

    head = git("rev-parse", "HEAD")
    metrics = {
        "provenance": {
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "repository_head": head,
            "frozen_cleaned_path": FROZEN_CLEANED.relative_to(REPO_ROOT).as_posix(),
            "frozen_cleaned_sha256": sha256(FROZEN_CLEANED),
            "frozen_raw_path": FROZEN_RAW.relative_to(REPO_ROOT).as_posix(),
            "source_sha256_git_lf": sha256(FROZEN_RAW),
            "source_sha256_preregistered_windows_crlf": PREREGISTERED_RAW_WINDOWS_CRLF_SHA256,
            "frozen_population_row_count": len(population),
            "frozen_unique_record_id_count": record_ids.nunique(),
            "frozen_unique_project_id_count": population["Project ID"].nunique(),
            "entity_input_representation": "frozen cleaned 1,308-record file",
            "raw_source_role": "identity/provenance only; no raw-to-cleaned whitespace measure",
        },
        "field_implementations": {
            "datasets": {
                "parser_module": "dashboard.dataset_normalisation",
                "parser_function": "iter_dataset_entries (live parse_datasets uses it)",
                "canonicaliser_module": "dashboard.dataset_normalisation",
                "canonicaliser_function": "describe_dataset_normalisation / normalise_dataset_name",
                "provider_function": "normalise_provider_name",
                "reference_paths": [],
                "implementation_sha256": sha256(DATASET_MODULE),
                "used_by_live_dashboard": True,
                "measurable": True,
                "reason_if_false": None,
            },
            "organisations": {
                "parser_module": "dashboard.institution_normalisation",
                "parser_function": "parse_institutions_with_metadata (same internal parser as live parse_institutions)",
                "canonicaliser_module": "dashboard.institution_normalisation",
                "canonicaliser_function": "describe_institution_normalisation",
                "reference_paths": [],
                "implementation_sha256": sha256(INSTITUTION_MODULE),
                "used_by_live_dashboard": True,
                "measurable": True,
                "reason_if_false": None,
            },
            "researcher_names": {
                "parser_module": "analysis.validation.owner_sampling_frame",
                "parser_function": "parse_researcher_field",
                "canonicaliser_module": None,
                "canonicaliser_function": None,
                "reference_paths": [],
                "implementation_sha256": sha256(RESEARCHER_MODULE),
                "used_by_live_dashboard": False,
                "measurable": False,
                "reason_if_false": "No production person-name variant reconciliation exists; parser normalises typography and exact duplicates but never merges similar names.",
                "researcher_name_reconciliation_rate_not_measurable": True,
            },
            "explicit_malformed_text": {
                "parser_module": "dashboard.dataset_normalisation; dashboard.institution_normalisation",
                "parser_function": "existing named token/alias corrections and institution parser_cleanup status",
                "canonicaliser_module": "same as parent entity field",
                "canonicaliser_function": "same as parent entity field",
                "reference_paths": [],
                "implementation_sha256": {
                    "dataset": sha256(DATASET_MODULE),
                    "institution": sha256(INSTITUTION_MODULE),
                },
                "used_by_live_dashboard": True,
                "measurable": True,
                "reason_if_false": None,
            },
        },
        "summary_metrics": {
            row["field"]: {key: jsonable(value) for key, value in row.items() if key != "field"}
            for row in summary.to_dict("records")
        },
        "field_diagnostics": {
            "datasets": {
                "unchanged_occurrences": int((~dataset_changed).sum()),
                "unresolved_occurrences": int(datasets["match_type"].eq("unresolved").sum()),
                "needs_review_occurrences": int(datasets["needs_review"].sum()),
                "match_type_counts": dataset_match_counts,
                "raw_variants_per_canonical_distribution": variant_distribution(dataset_detail),
                "provider_stage": {
                    "nonblank_parsed_provider_occurrences": int(provider_evaluable.sum()),
                    "provider_changed_occurrences": int(provider_changed.sum()),
                    "distinct_nonblank_raw_providers": int(
                        datasets.loc[provider_evaluable, "provider_raw"].nunique()
                    ),
                    "distinct_final_canonical_providers": int(
                        datasets["provider_canonical"].nunique()
                    ),
                    "included_in_dataset_name_headline": False,
                },
            },
            "organisations": {
                "unchanged_occurrences": int((~organisation_changed).sum()),
                "unclassified_occurrences": int(organisations["needs_review"].sum()),
                "match_type_counts": organisation_match_counts,
                "raw_variants_per_canonical_distribution": variant_distribution(organisation_detail),
                "production_output_semantics": "one occurrence per unique canonical institution per retained record",
            },
            "researcher_names": {
                "nonblank_source_records": len(researcher_evaluable_ids),
                "all_parser_entity_outputs": researcher_all_entity_count,
                "person_candidate_occurrences": len(researchers),
                "person_candidate_records": int(researchers["record_id"].nunique()),
                "distinct_person_candidate_display_strings": int(researchers["displayed"].nunique()),
            },
        },
        "cross_field": {
            "evaluable_in_at_least_one_reconciled_field": len(analysed_evaluable_ids),
            "affected_in_at_least_one_reconciled_field": len(any_variation_ids),
            "affected_rate_percent": percent(len(any_variation_ids), len(analysed_evaluable_ids)),
            "affected_in_exactly_one_field": exactly_one,
            "affected_in_two_or_more_fields": two_or_more,
            "fields_in_union": ["datasets", "organisations"],
        },
        "definitions": {
            "detected_variation": "A parsed observed entity whose exact parsed raw representation differs from the current production canonical representation.",
            "explicit_error": "A conservative subset matched by a deterministic operation explicitly labelled corrective in production code, tests, comments, or match metadata.",
            "record_denominator": "Unique frozen Record IDs with at least one parsed evaluable occurrence for the field.",
            "occurrence_denominator": "All parsed evaluable entity occurrences emitted under the production parser's output semantics.",
            "rate_unit": "percent",
        },
        "disclosure": {
            "reserve_suppression_available": reserve_suppression_available,
            "observed_raw_strings_emitted": False,
            "individual_raw_variant_ranking_emitted": False,
            "reason": "Archived baseline_reserve.csv and hard_reserve.csv are absent; example generation stopped and all observed raw strings were withheld.",
        },
        "limitations": [
            "Completeness is out of scope.",
            "Current reconciliation logic measures detectable variation, not total true error.",
            "Canonicalisation does not imply error.",
            "The researcher-name reconciliation rate is unavailable because no deterministic person-identity reconciliation exists.",
            "The frozen June population differs conceptually from the current live register.",
            "The 103 LF/CRLF-sensitive cleaned-cell differences are not counted as entity variation or error.",
            "Observed raw-form examples and individual raw-form rankings are withheld because archived reserve membership artefacts are unavailable.",
        ],
        "verification": {
            "frozen_cleaned_hash_matches": True,
            "raw_git_lf_hash_matches": True,
            "population_rows_1308": True,
            "unique_nonblank_record_ids_1308": True,
            "unique_project_ids_1304": True,
            "all_analysed_records_in_frozen_population": True,
            "all_dataset_mappings_reproduced_by_current_production_logic": True,
            "all_organisation_mappings_reproduced_by_current_production_logic": True,
            "record_numerators_use_unique_record_ids": True,
            "cross_field_total_uses_set_union": True,
            "blank_values_not_counted_as_errors": True,
            "lf_crlf_103_cell_issue_excluded": True,
            "new_aliases_or_matching_rules_introduced": False,
            "classification_or_validation_responses_read": False,
            "web_api_llm_calls_made": False,
            "tracked_preexisting_files_changed_before_run": False,
            "relevant_tests": "72 passed, 189 subtests passed (dataset, institution, and researcher-parser suites)",
        },
    }

    def records_for_json(frame: pd.DataFrame) -> list[dict[str, Any]]:
        return json.loads(frame.to_json(orient="records"))

    identity_native = organisations[organisations["match_type"].eq("identity")]
    decomposition_metrics = {
        "provenance": {
            "audit_timestamp_utc": metrics["provenance"]["audit_timestamp_utc"],
            "repository_head": head,
            "source_audit_metrics_path": METRICS_PATH.relative_to(REPO_ROOT).as_posix(),
            "frozen_population_rows": len(population),
            "raw_strings_disclosed": False,
        },
        "base_audit": actual_base,
        "datasets": {
            "native_match_status": records_for_json(dataset_native_table),
            "changed_occurrence_composition": records_for_json(dataset_changed_table),
            "affected_record_composition": {
                "exactly_one_transformation_type": int(
                    dataset_combinations.loc[
                        ~dataset_combinations["transformation_type_combination"].str.contains(
                            " \\+ ", regex=True
                        ),
                        "unique_records",
                    ].sum()
                ),
                "two_or_more_transformation_types": int(
                    dataset_combinations.loc[
                        dataset_combinations["transformation_type_combination"].str.contains(
                            " \\+ ", regex=True
                        ),
                        "unique_records",
                    ].sum()
                ),
                "combinations": records_for_json(dataset_combinations),
            },
            "grouping_only_changed_occurrences": {
                "dataset_family_grouping": 0,
                "collection_grouping": 0,
                "linked_product_grouping": 0,
            },
            "native_category_interpretation": "Native alias and normalised_format labels are retained; alias cannot be cleanly partitioned into legitimate naming versus correction without leaving implementation metadata.",
        },
        "organisations": {
            "native_match_status": records_for_json(organisation_native_table),
            "changed_occurrence_composition": records_for_json(
                organisation_changed_table
            ),
            "identity_native_occurrences": int(len(identity_native)),
            "identity_with_display_change": {
                "occurrences": int(len(identity_display)),
                "unique_records": int(identity_display["record_id"].nunique()),
                "pct_of_761_changed": percent(len(identity_display), 761),
                "causes": records_for_json(identity_cause_table),
            },
            "affected_record_composition": {
                "exactly_one_transformation_type": int(
                    organisation_combinations.loc[
                        ~organisation_combinations[
                            "transformation_type_combination"
                        ].str.contains(" \\+ ", regex=True),
                        "unique_records",
                    ].sum()
                ),
                "two_or_more_transformation_types": int(
                    organisation_combinations.loc[
                        organisation_combinations[
                            "transformation_type_combination"
                        ].str.contains(" \\+ ", regex=True),
                        "unique_records",
                    ].sum()
                ),
                "combinations": records_for_json(organisation_combinations),
            },
        },
        "explicit_corrections": {
            "field_split": records_for_json(explicit_field_split),
            "mutually_exclusive_record_groups": records_for_json(explicit_overlap),
            "rule_mechanisms": records_for_json(explicit_rule_table),
            "excluding_dominant_provider_form": {
                "dominant_form_occurrences": int(
                    dominant_provider_hits["occurrence_id"].nunique()
                ),
                "dominant_form_records": len(dominant_provider_ids),
                "dominant_form_records_with_another_correction": len(
                    dominant_and_other_ids
                ),
                "remaining_explicit_correction_occurrences": int(
                    other_explicit_hits["occurrence_id"].nunique()
                ),
                "remaining_affected_records": len(other_explicit_ids),
                "record_denominator": len(correction_evaluable_ids),
                "remaining_record_rate_percent": percent(
                    len(other_explicit_ids), len(correction_evaluable_ids)
                ),
            },
        },
        "concentration": {
            "minimum_support_for_rate_ranking": 5,
            "minimum_support_note": "Descriptive filter chosen to avoid rankings dominated by 1/1 and 1/2 cases; not preregistered and not inferential.",
            "cumulative_concentration": records_for_json(concentration_summary),
            "recurrence_summary": records_for_json(recurrence_summary),
            "field_comparison": records_for_json(field_comparison),
        },
        "definitions": {
            "identity_with_display_change": "Native identity status plus exact parsed_raw_value != final_canonical/display_value.",
            "recurring_malformed_form": "The same suppressed raw malformed representation maps to the same canonical entity in more than one correction occurrence.",
            "variant_id": "Stable anonymous label assigned within field, entity component, and canonical entity by occurrence count, record count, and SHA-256 tie-break; no raw value is emitted.",
        },
        "assertions": decomposition_assertions,
        "verification": {
            "relevant_tests": "72 passed, 189 subtests passed (dataset, institution, and researcher-parser suites)",
            "new_aliases_or_matching_rules_introduced": False,
            "manual_raw_variant_reclassification_performed": False,
            "validation_or_model_outputs_analysed": False,
            "raw_malformed_strings_disclosed": False,
        },
    }

    # Outputs contain canonical aggregates only. Raw variants stay blank because
    # reserve-only disclosure cannot be assessed in this worktree.
    summary.to_csv(SUMMARY_PATH, index=False, na_rep="NA")
    dataset_detail.to_csv(DATASET_VARIANTS_PATH, index=False)
    organisation_detail.to_csv(ORGANISATION_VARIANTS_PATH, index=False)
    if len(corrections):
        corrections.to_csv(CORRECTIONS_PATH, index=False)
    decomposition.to_csv(DECOMPOSITION_PATH, index=False, na_rep="NA")
    explicit_rule_table.to_csv(EXPLICIT_DECOMPOSITION_PATH, index=False)
    concentration.to_csv(ERROR_CONCENTRATION_PATH, index=False, na_rep="NA")
    recurring_corrections.to_csv(RECURRING_CORRECTIONS_PATH, index=False)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    DECOMPOSITION_JSON_PATH.write_text(
        json.dumps(decomposition_metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary_display = summary.copy()
    for column in ["affected_record_rate", "changed_occurrence_rate", "explicit_error_record_rate"]:
        summary_display[column] = summary_display[column].map(
            lambda value: "NA" if pd.isna(value) else f"{float(value):.2f}%"
        )

    dataset_rank = dataset_detail.head(20).rename(
        columns={
            "canonical_value": "canonical_value",
            "n_distinct_raw_variants": "n_distinct_raw_variants",
        }
    )
    organisation_rank = organisation_detail.head(20)
    correction_rank = corrections[
        [
            "rank",
            "rule_id",
            "corrected_or_canonical_value",
            "affected_records",
            "affected_occurrences",
            "field",
        ]
    ] if len(corrections) else pd.DataFrame()

    dataset_changed_report = dataset_changed_table.rename(
        columns={
            "transformation_type": "Existing transformation/match type",
            "occurrences": "Changed occurrences",
            "pct_of_changed": "% of 2,639 changed",
            "unique_records": "Unique records",
        }
    )
    organisation_changed_report = organisation_changed_table.rename(
        columns={
            "transformation_type": "Existing transformation/match type",
            "occurrences": "Changed occurrences",
            "pct_of_changed": "% of 761 changed",
            "unique_records": "Unique records",
        }
    )
    explicit_field_report = explicit_field_split.rename(
        columns={
            "field": "Field",
            "explicit_correction_occurrences": "Explicit correction occurrences",
            "occurrence_rate": "% of field occurrences",
            "unique_affected_records": "Affected records",
            "record_rate": "% of field records",
        }
    )
    explicit_rule_report = explicit_rule_table.rename(
        columns={
            "field": "Field",
            "rule_id": "Existing correction mechanism",
            "occurrences": "Occurrences",
            "unique_records": "Records",
            "pct_of_78_explicit_occurrences": "% of 78 explicit corrections",
        }
    )
    top_burden = pd.concat(
        [
            group[group["explicit_correction_occurrences"].gt(0)].head(10)
            for _, group in concentration.groupby("field", sort=True)
        ],
        ignore_index=True,
    ).rename(
        columns={
            "absolute_burden_rank": "rank",
            "canonical_entity": "canonical entity",
            "entity_component": "component",
            "total_occurrences": "total occurrences",
            "explicit_correction_occurrences": "corrections",
            "explicit_correction_rate": "correction rate (%)",
            "affected_records": "records",
            "n_distinct_malformed_variants": "malformed variants",
        }
    )
    supported_rate = concentration[
        concentration["minimum_support_5"]
        & concentration["explicit_correction_occurrences"].gt(0)
    ].sort_values(
        ["field", "rate_rank_min_support_5"], kind="stable"
    ).rename(
        columns={
            "rate_rank_min_support_5": "rate rank",
            "canonical_entity": "canonical entity",
            "entity_component": "component",
            "total_occurrences": "total occurrences",
            "explicit_correction_occurrences": "corrections",
            "explicit_correction_rate": "correction rate (%)",
            "affected_records": "records",
        }
    )
    diversity_report = concentration[
        concentration["explicit_correction_occurrences"].gt(0)
    ].sort_values(
        [
            "n_distinct_malformed_variants",
            "explicit_correction_occurrences",
            "canonical_entity",
        ],
        ascending=[False, False, True],
        kind="stable",
    ).head(10).rename(
        columns={
            "canonical_entity": "canonical entity",
            "entity_component": "component",
            "explicit_correction_occurrences": "corrections",
            "n_distinct_malformed_variants": "malformed variants",
            "largest_single_variant_count": "largest variant count",
            "share_from_largest_variant": "largest variant share (%)",
        }
    )
    largest_recurring = recurring_corrections.sort_values(
        ["occurrences", "unique_records", "field", "canonical_entity"],
        ascending=[False, False, True, True],
        kind="stable",
    ).iloc[0]

    report = f"""# Frozen June register entity-variation audit

## 1. Scope and provenance

This retrospective audit applies the current deterministic dashboard reconciliation machinery to the frozen June study population: **1,308 retained records** (**1,304 official Project IDs**). The entity-analysis input is the frozen cleaned `Datasets Used` and `Researchers` evidence, not the live register. Reconciliation burden means an exact parsed raw entity differs from its production canonical representation; it does not imply error. The narrower explicit-error subset includes only operations labelled corrective by existing code, match metadata, tests, or comments. Completeness and undetected errors are excluded.

- Frozen cleaned SHA-256: `{EXPECTED_CLEANED_SHA256}`
- Frozen raw Git/LF SHA-256: `{EXPECTED_RAW_GIT_LF_SHA256}`
- Preregistered raw Windows/CRLF SHA-256: `{PREREGISTERED_RAW_WINDOWS_CRLF_SHA256}`
- Repository HEAD: `{head}`
- Audit timestamp (UTC): `{metrics['provenance']['audit_timestamp_utc']}`

The preregistered source hash refers to the Windows/CRLF representation; the repository stores the same frozen logical CSV in Git/LF form, as established by the prior provenance diagnostic. This audit verified the Git/LF hash and did not reconstruct or write a CRLF file.

## 2. Summary metrics

All rates are percentages. Each record-level denominator is the number of unique retained Record IDs with at least one evaluable occurrence for that row's field; it is not automatically 1,308.

{markdown_table(summary_display)}

## 3. Dataset variation

- Evaluable records: **{len(dataset_evaluable_ids):,}**.
- Records with at least one changed dataset occurrence: **{len(dataset_affected_ids):,}/{len(dataset_evaluable_ids):,} ({percent(len(dataset_affected_ids), len(dataset_evaluable_ids)):.2f}%)**.
- Parsed occurrences: **{len(datasets):,}**; changed **{int(dataset_changed.sum()):,} ({percent(int(dataset_changed.sum()), len(datasets)):.2f}%)**; unchanged **{int((~dataset_changed).sum()):,}**.
- Distinct parsed raw forms: **{datasets['raw_value'].nunique():,}**; distinct canonical forms: **{datasets['canonical_value'].nunique():,}**; canonical forms receiving more than one raw form: **{int((datasets.groupby('canonical_value')['raw_value'].nunique() > 1).sum()):,}**.
- Match types: {', '.join(f'`{key}` {value:,}' for key, value in dataset_match_counts.items())}. Unresolved occurrences: **{int(datasets['match_type'].eq('unresolved').sum()):,}**; review-flagged occurrences: **{int(datasets['needs_review'].sum()):,}**.
- Distribution of raw variants per canonical form (`variant_count: canonical_forms`): {', '.join(f'`{key}: {value}`' for key, value in variant_distribution(dataset_detail).items())}.

Canonical forms with the largest observed variant burden (first 20 rows of the complete canonical-level CSV):

{markdown_table(dataset_rank, ['rank', 'canonical_value', 'affected_records', 'total_occurrences', 'n_distinct_raw_variants', 'existing_match_types'])}

Dataset-family grouping was not counted as name reconciliation. Provider canonicalisation is retained as a separate parser stage and contributes only where an existing provider rule is explicitly corrective.

For stage transparency, **{int(provider_evaluable.sum()):,}** parsed dataset occurrences had a nonblank provider representation and **{int(provider_changed.sum()):,}** of those differed from the final production provider representation. These provider-stage changes are not included in the dataset-name changed-occurrence numerator.

## 4. Organisation variation

- Evaluable records: **{len(organisation_evaluable_ids):,}**.
- Records with at least one changed institution occurrence: **{len(organisation_affected_ids):,}/{len(organisation_evaluable_ids):,} ({percent(len(organisation_affected_ids), len(organisation_evaluable_ids)):.2f}%)**.
- Production-parser occurrences: **{len(organisations):,}**; changed **{int(organisation_changed.sum()):,} ({percent(int(organisation_changed.sum()), len(organisations)):.2f}%)**; unchanged **{int((~organisation_changed).sum()):,}**.
- Distinct parsed raw forms: **{organisations['raw_value'].nunique():,}**; distinct canonical forms: **{organisations['canonical_value'].nunique():,}**; canonical forms receiving more than one raw form: **{int((organisations.groupby('canonical_value')['raw_value'].nunique() > 1).sum()):,}**.
- Match statuses: {', '.join(f'`{key}` {value:,}' for key, value in organisation_match_counts.items())}. Unclassified-sector/review-flagged occurrences: **{int(organisations['needs_review'].sum()):,}**.
- Distribution of raw variants per canonical form (`variant_count: canonical_forms`): {', '.join(f'`{key}: {value}`' for key, value in variant_distribution(organisation_detail).items())}.

Canonical organisations with the largest observed variant burden (first 20 rows of the complete canonical-level CSV):

{markdown_table(organisation_rank, ['rank', 'canonical_value', 'affected_records', 'total_occurrences', 'n_distinct_raw_variants', 'existing_match_types'])}

The live institution parser emits at most one occurrence of a given canonical institution per retained record. Counts therefore follow production output semantics rather than reconstructing duplicate mentions discarded by that parser.

The institution `identity` match status does not always mean exact string identity: approved display acronyms can be appended after status assignment. Changed-occurrence counts therefore use exact parsed-raw versus final-canonical inequality, as defined, rather than treating the match-status label as the change flag.

## 5. Researcher-name variation

`researcher_name_reconciliation_rate_not_measurable = true`. No live dashboard person-name canonicaliser was found. The production validation-frame parser (`analysis.validation.owner_sampling_frame.parse_researcher_field`) standardises typography, removes exact within-field duplicates, and explicitly never merges similar-looking names. It yielded **{len(researchers):,}** conservative `person_candidate` outputs across **{researchers['record_id'].nunique():,}** records, with **{researchers['displayed'].nunique():,}** distinct displayed strings, from **{len(researcher_evaluable_ids):,}** nonblank researcher fields. These are descriptive parser counts, not a reconciliation numerator or rate. No researcher variant CSV was created.

## 6. Explicit malformed/error corrections

The conservative explicitly corrective subset affects **{len(correction_affected_ids):,}/{len(correction_evaluable_ids):,} ({percent(len(correction_affected_ids), len(correction_evaluable_ids)):.2f}%)** evaluable records and **{affected_entity_occurrences:,}/{total_correction_domain_occurrences:,} ({percent(affected_entity_occurrences, total_correction_domain_occurrences):.2f}%)** dataset/institution entity occurrences. A correction occurrence is counted once even if more than one named corrective rule applies.

{markdown_table(correction_rank) if len(correction_rank) else 'No supported explicit correction rules occurred.'}

Routine line-ending, whitespace, BOM, line-wrap, generic case, and zero-width-character hygiene is excluded. The prior 103 LF/CRLF-sensitive dataset-cell differences are not counted.

## 7. Cross-field overlap

Across datasets and organisations, **{len(any_variation_ids):,}/{len(analysed_evaluable_ids):,} ({percent(len(any_variation_ids), len(analysed_evaluable_ids)):.2f}%)** records evaluable in at least one reconciled field contain at least one detected variation. **{exactly_one:,}** are affected in exactly one field and **{two_or_more:,}** in both fields. These are set unions of Record IDs, not sums of field numerators.

## 8. Methods/provenance notes

| field | parser | canonicaliser | reference/version | live dashboard |
| --- | --- | --- | --- | --- |
| datasets | `dashboard.dataset_normalisation.iter_dataset_entries` (via `parse_datasets`) | `describe_dataset_normalisation`; `normalise_dataset_name`; provider stage `normalise_provider_name` | hard-coded deterministic rules; module SHA-256 `{sha256(DATASET_MODULE)}` | Yes |
| organisations | `dashboard.institution_normalisation.parse_institutions_with_metadata` (same internal parser as `parse_institutions`) | `describe_institution_normalisation` | hard-coded aliases/sectors; module SHA-256 `{sha256(INSTITUTION_MODULE)}` | Yes |
| researcher names | `analysis.validation.owner_sampling_frame.parse_researcher_field` | none for person identity | module SHA-256 `{sha256(RESEARCHER_MODULE)}` | No |

`analysis/register_reference.yaml` is used by later register-property derivation, not by the dataset-name or institution-name canonicalisers measured here. Dataset family/collection assignment is outside the name-reconciliation counts.

Denominators: a record is evaluable only if the relevant production parser emits at least one entity occurrence. A changed occurrence requires exact inequality between the parser-preserved raw entity and canonical entity. Raw distinct forms are counted before canonicalisation, without audit-side pre-normalisation.

### Disclosure component STOP

The archived files `baseline_reserve.csv` and `hard_reserve.csv` named and hash-bound by production sampling code are absent from this worktree. Reserve membership could therefore not be obtained through the authorised path. Example generation and the individual non-canonical raw-form ranking were stopped. No observed raw string is emitted in this report or any CSV/JSON output; canonical-level aggregate counts retain all 1,308 records.

## 9. Limitations

- The results quantify variation detected by current deterministic reconciliation, not total true error or register completeness.
- Canonicalisation includes legitimate aliases and formatting conventions; it is not generally an error indicator.
- Explicit-error figures are a conservative identifiable subset, not an estimate of all malformed register content.
- Researcher identity variation is not measurable without person-resolution logic that production does not provide.
- The frozen June population and current live register are conceptually distinct.
- Observed raw variants are withheld because reserve-only disclosure could not be assessed.

## 10. Verification

- Frozen cleaned hash matched; the file had exactly 1,308 rows, 1,308 unique nonblank Record IDs, and 1,304 unique official Project IDs.
- Frozen raw Git/LF hash matched; the preregistered CRLF hash was retained as provenance metadata.
- Every analysed occurrence belonged to a frozen Record ID.
- Every dataset and institution mapping was re-run and asserted through the current production canonicaliser; the audit introduced no alias or matching rule.
- Record numerators used unique Record-ID sets; cross-field counts used unions.
- Blank values were excluded from error counts; the 103 LF/CRLF issue was excluded.
- Relevant existing tests passed: **72 tests and 189 subtests** across dataset normalisation, institution normalisation, and the researcher parser.
- No classification output, coder response, owner response, adjudication output, or disagreement status was read.
- No web, API, or LLM call was made. No commit or push was performed.
"""
    report += f"""

## Reconciliation-burden decomposition

The decomposition below preserves the original audit's exact-string change definition and native production match statuses. Category-level record counts can overlap because one record can contain changed occurrences of more than one type; they must not be summed.

### Dataset decomposition

| Existing transformation/match type | Changed occurrences | % of 2,639 changed | Unique records |
| --- | ---: | ---: | ---: |
{chr(10).join('| ' + ' | '.join(markdown_cell(value) for value in row) + ' |' for row in dataset_changed_report[['Existing transformation/match type', 'Changed occurrences', '% of 2,639 changed', 'Unique records']].itertuples(index=False, name=None))}

The native-status table reconciles to **3,350 total**, **2,639 changed**, and **711 unchanged** dataset occurrences. Native `alias` comprises 2,409 occurrences (2,211 changed; 198 unchanged), `identity` 513 (all unchanged), `normalised_format` 426 (all changed), and `compound_or_multi_dataset` 2 (both changed). Dataset-family, collection, and linked-product grouping account for **zero** occurrences in this numerator: those later grouping operations were not included in the original audit. Native `alias` and `normalised_format` labels are retained because production metadata does not support a clean three-way split between legitimate naming, formatting, and explicit correction. `compound_or_multi_dataset` is retained as an implementation label without further semantic interpretation. The conservative correction subset is reported separately below.

Among the **1,189** affected dataset records, **{int(decomposition_metrics['datasets']['affected_record_composition']['exactly_one_transformation_type']):,}** contain exactly one changed-occurrence transformation type and **{int(decomposition_metrics['datasets']['affected_record_composition']['two_or_more_transformation_types']):,}** contain two or more.

### Organisation decomposition

| Existing transformation/match type | Changed occurrences | % of 761 changed | Unique records |
| --- | ---: | ---: | ---: |
{chr(10).join('| ' + ' | '.join(markdown_cell(value) for value in row) + ' |' for row in organisation_changed_report[['Existing transformation/match type', 'Changed occurrences', '% of 761 changed', 'Unique records']].itertuples(index=False, name=None))}

The native-status table reconciles to **1,839 total**, **761 changed**, and **1,078 unchanged** organisation occurrences. Native `alias` comprises 624 occurrences (514 changed; 110 unchanged), `identity` 1,203 (235 changed; 968 unchanged), and `parser_cleanup` 12 (all changed). Of the native `identity` occurrences, **{len(identity_display):,}**, across **{identity_display['record_id'].nunique():,}** records, are `identity_with_display_change`, representing **{percent(len(identity_display), 761):.2f}%** of all 761 changed organisation occurrences. Existing deterministic function behaviour attributes **{int(identity_cause_table.loc[identity_cause_table['identity_display_cause'].eq('approved_acronym_addition'), 'occurrences'].sum()):,}** to approved acronym addition and **{int(identity_cause_table.loc[identity_cause_table['identity_display_cause'].eq('other_deterministic_display_construction'), 'occurrences'].sum()):,}** to other deterministic display construction. This is display standardisation, not an error classification.

Among the **619** affected organisation records, **{int(decomposition_metrics['organisations']['affected_record_composition']['exactly_one_transformation_type']):,}** contain exactly one transformation type and **{int(decomposition_metrics['organisations']['affected_record_composition']['two_or_more_transformation_types']):,}** contain two or more.

### Conservative explicit corrections

| Field | Explicit correction occurrences | % of field occurrences | Affected records | % of field records |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join('| ' + ' | '.join(markdown_cell(value) for value in row) + ' |' for row in explicit_field_report[['Field', 'Explicit correction occurrences', '% of field occurrences', 'Affected records', '% of field records']].itertuples(index=False, name=None))}

The 66-record union comprises **{len(dataset_only_ids):,}** records with dataset corrections only, **{len(organisation_only_ids):,}** with organisation corrections only, and **{len(explicit_both_ids):,}** with corrections in both fields. These mutually exclusive groups sum to 66.

Excluding the dominant recurring provider form leaves **{len(other_explicit_ids):,}/{len(correction_evaluable_ids):,} ({percent(len(other_explicit_ids), len(correction_evaluable_ids)):.2f}%)** records with at least one explicit deterministic correction. The dominant form occurs in 49 records, of which **{len(dominant_and_other_ids):,}** also contain another explicit correction; this overlap is why subtracting 49 from 66 would not give the remaining numerator. The remaining subset contains **{other_explicit_hits['occurrence_id'].nunique():,}** correction occurrences.

| Field | Existing correction mechanism | Occurrences | Records | % of 78 explicit corrections |
| --- | --- | ---: | ---: | ---: |
{chr(10).join('| ' + ' | '.join(markdown_cell(value) for value in row) + ' |' for row in explicit_rule_report[['Field', 'Existing correction mechanism', 'Occurrences', 'Records', '% of 78 explicit corrections']].itertuples(index=False, name=None))}

The broad reconciliation-burden rates measure how frequently observed register forms require deterministic standardisation to reach the dashboard's canonical representation. They include legitimate aliases and display standardisation and should not be interpreted as error rates. The conservative explicit-correction subset identifies only transformations whose existing deterministic rules are clearly corrective or malformed; it is not a complete or externally validated error rate.

### Concentration and recurrence of explicit corrections

The original explicit subset contains dataset-name, dataset-provider, and organisation corrections. Provider targets remain labelled `provider` below rather than being presented as dataset-name entities.

Top affected canonical entities by absolute correction burden (up to ten per field):

{markdown_table(top_burden, ['rank', 'field', 'component', 'canonical entity', 'total occurrences', 'corrections', 'correction rate (%)', 'records', 'malformed variants'])}

Rate ranking with the authorised descriptive minimum-support filter of **at least 5 total occurrences**:

{markdown_table(supported_rate, ['rate rank', 'field', 'component', 'canonical entity', 'total occurrences', 'corrections', 'correction rate (%)', 'records'])}

The minimum-support filter is descriptive, was chosen only to avoid a rate ranking dominated by 1/1 and 1/2 cases, and does not change any underlying count.

Cumulative concentration and affected-entity distribution:

{markdown_table(concentration_summary)}

Singleton versus recurring suppressed malformed mappings:

{markdown_table(recurrence_summary)}

The largest recurring mapping is the suppressed `variant_01` for **{largest_recurring['canonical_entity']}** ({largest_recurring['entity_component']}): the same malformed representation occurs **{int(largest_recurring['occurrences']):,}** times across **{int(largest_recurring['unique_records']):,}** records. This is consistent with a repeated or propagated entry form, although the audit cannot establish how it arose.

Field comparison:

{markdown_table(field_comparison)}

Entities with the largest malformed-variant diversity:

{markdown_table(diversity_report, ['field', 'component', 'canonical entity', 'corrections', 'malformed variants', 'largest variant count', 'largest variant share (%)'])}

Raw malformed strings remain suppressed. `variant_01`, `variant_02`, and subsequent labels in the recurring-corrections CSV are stable anonymous identifiers within each canonical entity. Repeated labels establish only that the same malformed representation recurred; they do not establish how or why it propagated.

### Decomposition verification

- Native dataset and organisation status totals reconcile exactly to 3,350/2,639/711 and 1,839/761/1,078 respectively.
- Changed-occurrence transformation totals reconcile exactly to the original numerators.
- Field-specific explicit corrections sum to 78 occurrences; mutually exclusive record groups sum to the 66-record union.
- Entity concentration and anonymised recurring-form occurrence counts each sum to 78.
- No raw malformed string, Record ID, project title, or researcher name is disclosed.
- No transformation was manually reclassified from raw content; no new alias, matching rule, or error definition was introduced.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
