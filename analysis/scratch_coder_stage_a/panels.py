"""Formal-panel reconstruction and candidate-0.7 structural validation."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Hashable, Iterable

import pandas as pd
import yaml

from analysis.validation.metrics import masi_distance, nominal_distance
from analysis.validation.replacement import DimensionPanel
from scripts import validate_redcap_candidate as frozen_validator

from .config import CODERS, ROOT
from .load import load_frozen_export, read_manifest_csv, semicolon_set
from .mappings import choice_mappings


@dataclass(frozen=True)
class StageAData:
    raw_rows: int
    raw_columns: int
    responses: pd.DataFrame
    model: dict[str, dict[str, Hashable]]
    baseline_ids: frozenset[str]
    hard_case_ids: frozenset[str]
    structural_invalid_response_count: int
    structural_invalid_ids: frozenset[str]
    exposure_response_count: int
    exposure_ids: frozenset[str]
    structural_error_counts: dict[str, int]
    hard_stratum_counts: dict[str, int]

    @property
    def formal_ids(self) -> frozenset[str]:
        return self.baseline_ids | self.hard_case_ids


def _integer(value: str) -> int | None:
    return None if value == "" else int(value)


def _checkbox(row: pd.Series, prefix: str, codes: Iterable[int]) -> frozenset[int] | None:
    values = {code: row[f"{prefix}___{code}"] for code in codes}
    if any(value not in {"0", "1"} for value in values.values()):
        return None
    return frozenset(code for code, value in values.items() if value == "1")


def _validator_payload(row: pd.Series) -> dict[str, Any]:
    domains = _checkbox(row, "sc_domains", range(1, 13))
    purposes = _checkbox(row, "sc_purposes", range(1, 9))
    issues = _checkbox(row, "sc_tax_issue", (1, 2, 5))
    return {
        "assignment_id": row["assignment_id"],
        "instrument_ver": row["instrument_ver"],
        "record_kind": _integer(row["record_kind"]),
        "sc_blind_decl": _integer(row["sc_blind_decl"]),
        "sc_exposure": _integer(row["sc_exposure"]),
        "sc_exposure_note": row["sc_exposure_note"],
        "sc_domains": sorted(domains) if domains is not None else None,
        "sc_purposes": sorted(purposes) if purposes is not None else None,
        "sc_covid": _integer(row["sc_covid"]),
        "sc_equity": _integer(row["sc_equity"]),
        "sc_sufficiency": _integer(row["sc_sufficiency"]),
        "sc_taxonomy_fit": _integer(row["sc_taxonomy_fit"]),
        "sc_tax_issue": sorted(issues) if issues is not None else None,
        "sc_confidence": _integer(row["sc_confidence"]),
        "sc_note": row["sc_note"],
    }


def _taxonomy_labels() -> dict[str, frozenset[str]]:
    taxonomy = yaml.safe_load((ROOT / "taxonomy_data_dictionary.yaml").read_text(encoding="utf-8"))
    active = [item for item in taxonomy["categories"] if item.get("include_in_prompt")]
    return {
        "domains": frozenset(item["label"] for item in active if item["layer"] == "Layer A -- domain"),
        "purposes": frozenset(item["label"] for item in active if item["layer"] == "Layer C -- purpose"),
        "tags": frozenset(item["label"] for item in active if item["layer"] == "Cross-cutting tag"),
    }


def _load_model(formal_ids: frozenset[str]) -> dict[str, dict[str, Hashable]]:
    rows = read_manifest_csv("MOD-006")
    if rows["Record ID"].duplicated().any():
        raise ValueError("Fable 5 contains duplicate Record IDs")
    subset = rows[rows["Record ID"].isin(formal_ids)].copy()
    if len(subset) != len(formal_ids) or set(subset["Record ID"]) != set(formal_ids):
        raise ValueError("Formal sample does not join one-to-one to Fable 5")
    allowed = _taxonomy_labels()
    output: dict[str, dict[str, Hashable]] = {}
    for row in subset.to_dict("records"):
        domains = semicolon_set(row["substantive_domains"])
        purposes = semicolon_set(row["analytical_purpose"])
        tags = semicolon_set(row["cross_cutting_tags"])
        unknown = (domains - allowed["domains"]) | (purposes - allowed["purposes"]) | (tags - allowed["tags"])
        if unknown:
            raise ValueError("Unknown production taxonomy label in the formal sample")
        output[row["Record ID"]] = {
            "Research Domains": domains,
            "Analytical Purposes": purposes,
            "Demographic disparities / equity": int("Demographic disparities / equity tag" in tags),
            "COVID-19 & Pandemic": int("COVID-19 & Pandemic" in tags),
        }
    return output


def build_stage_a_data() -> StageAData:
    raw = load_frozen_export()
    formal = raw[raw["validation_included"] == "1"].copy()
    if len(formal) != 675:
        raise ValueError(f"Expected 675 formal responses, observed {len(formal)}")
    if set(formal["reviewer_id"]) != set(CODERS):
        raise ValueError("Formal coder pseudonyms differ from C01/C02/C03")
    if formal["assignment_id"].duplicated().any():
        raise ValueError("Duplicate formal assignment response")

    crosswalk = read_manifest_csv("POST-019")
    if len(crosswalk) != 675 or crosswalk["assignment_id"].duplicated().any():
        raise ValueError("Formal assignment authority is not a unique 675-row crosswalk")
    if set(formal["assignment_id"]) != set(crosswalk["assignment_id"]):
        raise ValueError("Export assignment set differs from POST-019")
    merged = formal.merge(
        crosswalk[["assignment_id", "reviewer_id", "source_record_id", "sample_family"]],
        on="assignment_id", how="inner", validate="one_to_one", suffixes=("", "_authority"),
    )
    if (merged["reviewer_id"] != merged["reviewer_id_authority"]).any() or (
        merged["source_record_id"] != merged["source_record_id_authority"]
    ).any():
        raise ValueError("Export reviewer/source mapping differs from POST-019")
    merged.drop(columns=["reviewer_id_authority", "source_record_id_authority"], inplace=True)

    baseline = read_manifest_csv("POST-009")
    hard = read_manifest_csv("POST-011")
    baseline_ids = frozenset(baseline["record_id"])
    hard_ids = frozenset(hard["record_id"])
    if len(baseline_ids) != 150 or len(hard_ids) != 75 or baseline_ids & hard_ids:
        raise ValueError("Frozen 150/75 sample authority does not reconcile")
    cross_baseline = frozenset(merged.loc[merged["sample_family"] == "baseline", "source_record_id"])
    cross_hard = frozenset(merged.loc[merged["sample_family"] == "hard_case", "source_record_id"])
    if cross_baseline != baseline_ids or cross_hard != hard_ids:
        raise ValueError("Crosswalk stratum mapping differs from active sample authorities")
    counts = merged.groupby(["source_record_id", "reviewer_id"]).size()
    if len(counts) != 675 or not (counts == 1).all():
        raise ValueError("Formal panel is not one response per coder and record")
    per_record = merged.groupby("source_record_id")["reviewer_id"].nunique()
    if len(per_record) != 225 or not (per_record == 3).all():
        raise ValueError("Formal panel is not three independent responses per record")

    choices = choice_mappings()
    domain_labels = choices["sc_domains"]
    purpose_labels = choices["sc_purposes"]
    allowed_taxonomy = _taxonomy_labels()
    if frozenset(domain_labels.values()) != allowed_taxonomy["domains"]:
        raise ValueError("Candidate-0.7 Domain choices differ from rc2")
    if frozenset(purpose_labels.values()) != allowed_taxonomy["purposes"]:
        raise ValueError("Candidate-0.7 Purpose choices differ from rc2")
    derived: list[dict[str, Any]] = []
    error_counter: Counter[str] = Counter()
    invalid_ids: set[str] = set()
    invalid_responses = 0
    for _, row in merged.iterrows():
        payload = _validator_payload(row)
        errors = frozen_validator.validate_scratch(payload)
        if errors:
            invalid_responses += 1
            invalid_ids.add(row["source_record_id"])
            error_counter.update(errors)
        domain_codes = payload["sc_domains"]
        purpose_codes = payload["sc_purposes"]
        fit = payload["sc_taxonomy_fit"]
        issue_codes = payload["sc_tax_issue"] if fit in (2, 3) else []
        derived.append({
            "assignment_id": row["assignment_id"],
            "record_id": row["source_record_id"],
            "coder": row["reviewer_id"],
            "population": row["sample_family"],
            "complete": row["scratch_coder_complete"] == "2",
            "domains": None if domain_codes is None else frozenset(domain_labels[code] for code in domain_codes),
            "purposes": None if purpose_codes is None else frozenset(purpose_labels[code] for code in purpose_codes),
            "equity": payload["sc_equity"],
            "covid": payload["sc_covid"],
            "sufficiency": payload["sc_sufficiency"],
            "taxonomy_fit": fit,
            "taxonomy_issues": None if issue_codes is None else frozenset(issue_codes),
            "confidence": payload["sc_confidence"],
            "exposure": payload["sc_exposure"],
            "structural_valid": not errors,
        })
    responses = pd.DataFrame(derived)
    exposure_ids = frozenset(responses.loc[responses["exposure"] == 1, "record_id"])
    model = _load_model(baseline_ids | hard_ids)
    return StageAData(
        raw_rows=len(raw), raw_columns=len(raw.columns), responses=responses, model=model,
        baseline_ids=baseline_ids, hard_case_ids=hard_ids,
        structural_invalid_response_count=invalid_responses,
        structural_invalid_ids=frozenset(invalid_ids),
        exposure_response_count=int((responses["exposure"] == 1).sum()),
        exposure_ids=exposure_ids, structural_error_counts=dict(error_counter),
        hard_stratum_counts={str(key): int(value) for key, value in hard["hard_case_stratum"].value_counts().items()},
    )


def population_ids(data: StageAData, population: str, subset_ids: dict[str, frozenset[str]]) -> frozenset[str]:
    if population == "baseline":
        return data.baseline_ids
    if population == "hard_case":
        return data.hard_case_ids
    if population == "baseline_exposure_sensitivity":
        return data.baseline_ids - data.exposure_ids
    if population == "baseline_structural_sensitivity":
        return data.baseline_ids - data.structural_invalid_ids
    if population == "baseline_broad_usable":
        return subset_ids["broad"]
    if population == "baseline_strict_sufficient":
        return subset_ids["strict"]
    raise KeyError(population)


def dimension_panels(
    data: StageAData,
    record_ids: frozenset[str],
    dimension: str,
) -> tuple[DimensionPanel[Hashable], ...]:
    field = {
        "Research Domains": "domains",
        "Analytical Purposes": "purposes",
        "Demographic disparities / equity": "equity",
        "COVID-19 & Pandemic": "covid",
    }[dimension]
    rows = data.responses[data.responses["record_id"].isin(record_ids)]
    grouped = {rid: group for rid, group in rows.groupby("record_id")}
    panels: list[DimensionPanel[Hashable]] = []
    for record_id in sorted(record_ids):
        group = grouped.get(record_id)
        if group is None:
            continue
        by_coder = {row["coder"]: row for row in group.to_dict("records")}
        values = [by_coder[coder][field] if by_coder[coder]["complete"] else None for coder in CODERS]
        panels.append(DimensionPanel(
            record_id=record_id,
            coder_a=values[0], coder_b=values[1], coder_c=values[2],
            model=data.model[record_id][dimension],
        ))
    return tuple(panels)


def distance_for_dimension(dimension: str):
    return masi_distance if dimension in {"Research Domains", "Analytical Purposes"} else nominal_distance
