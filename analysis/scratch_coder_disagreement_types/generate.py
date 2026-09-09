"""Generate descriptive distributions of scratch-coder/model set relations.

This module does not calculate agreement coefficients, distances, inferential
intervals, or any other analytical result outside the requested counts and
conditional proportions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

from scripts import validate_redcap_candidate as frozen_validator


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent

RAW_EXPORT = ROOT / "preregistration_restricted/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv"
BASELINE_AUTHORITY = ROOT / "preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv"
HARD_AUTHORITY = ROOT / "preregistration_restricted/sampling/official_draw_20260724/hard_active.csv"
CROSSWALK_AUTHORITY = ROOT / "preregistration_restricted/sampling/official_draw_20260724/formal_assignment_crosswalk.csv"
MODEL_OUTPUT = ROOT / "analysis/outputs_classified_20260702_fable5/layer_classifications.csv"
TAXONOMY = ROOT / "taxonomy_data_dictionary.yaml"
REDCAP_DICTIONARY = ROOT / "preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv"
MANIFEST = ROOT / "preregistration/preregistration_artifact_manifest.csv"
STAGE_A_METHODS = ROOT / "analysis/outputs_validation_scratch_20260824/methods_stage_a.md"
STAGE_A_METADATA = ROOT / "analysis/outputs_validation_scratch_20260824/run_metadata.json"
STAGE_A_DENOMINATORS = ROOT / "analysis/outputs_validation_scratch_20260824/denominator_audit.csv"
STAGE_A_REPLACEMENT = ROOT / "analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv"
STAGE_B_METADATA = ROOT / "analysis/outputs_validation_scratch_stage_b_20260825/run_metadata.json"
CANONICAL_REPORT = ROOT / "analysis/scratch_coder_results/results.md"
CANONICAL_METADATA = ROOT / "analysis/scratch_coder_results/run_metadata.json"
VALIDATOR = ROOT / "scripts/validate_redcap_candidate.py"

EXPECTED_HASHES = {
    RAW_EXPORT: "29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d",
    BASELINE_AUTHORITY: "0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11",
    HARD_AUTHORITY: "582f248d39d911275e4e4f11bc34660b51809a1ed7c330644f9e2036299cfb11",
    CROSSWALK_AUTHORITY: "96daddae15848331f7bef486a6c630e00de598ddb91f5ce317457e09a8bdd666",
    MODEL_OUTPUT: "9827fc9f01b9e1f3e9b58fe8f41b59eb5a569c77aacb77d5140628ec04f5eeab",
    TAXONOMY: "7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de",
    REDCAP_DICTIONARY: "1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc",
    STAGE_A_METHODS: "a78393b73ad39e3bde4dd949cce99575d257938b9cfd8c72d43dfa25df6f5f67",
    STAGE_A_METADATA: "a685d524fcb90195d7e4badf17a56aa8feb54e28b848d39df33ef1f8cf1debf4",
    STAGE_A_DENOMINATORS: "0b60e10e86ee996ba270c323b2cb00bb0d73d1403a419b20372dea069fa9dacc",
    STAGE_A_REPLACEMENT: "d9a3201b4965e678c29e375775c410c2b770d65c1421be85835f00bcd5fe1f82",
    VALIDATOR: "f28f45cdc45fd1dbc3f97d8bc0c8e4cfc2e1ce29ae4f95bcd3d423975f030190",
}

MANIFEST_IDENTITIES = {
    RAW_EXPORT: "POST-028",
    BASELINE_AUTHORITY: "POST-009",
    HARD_AUTHORITY: "POST-011",
    CROSSWALK_AUTHORITY: "POST-019",
    MODEL_OUTPUT: "MOD-006",
    TAXONOMY: "MOD-001",
    REDCAP_DICTIONARY: "RED-036",
    VALIDATOR: "RED-013",
}

CODERS = ("C01", "C02", "C03")
POPULATIONS = ("baseline", "hard_case")
DIMENSIONS = ("Research Domains", "Analytical Purposes", "Joint cross-cutting tag set")
PAIR_FAMILIES = ("human_human", "model_human")
RELATIONS = ("both_empty", "exactly_one_empty", "identical", "containment", "overlap", "disjoint")
TAG_NAMES = ("Demographic disparities / equity tag", "COVID-19 & Pandemic")
MODEL_ENDPOINT = "model:claude-fable-5"
CSV_COLUMNS = (
    "population", "dimension", "pair_family", "relation", "eligible_records", "count",
    "total_pairs_classified", "nonidentical_nonempty_pairs", "all_nonidentical_pairs",
    "empty_set_involved_pairs", "proportion_of_nonidentical_nonempty_pairs",
    "nonempty_proportion_status", "proportion_of_all_nonidentical_pairs", "all_proportion_status",
)


@dataclass(frozen=True)
class EndpointValue:
    value: frozenset[str] | None
    source_ref: str
    row_key: Mapping[str, str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or ())


def git_output(*args: str) -> str:
    result = subprocess.run(
        ("git", *args), cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return result.stdout.rstrip("\n")


def verify_hashes(paths: Iterable[Path]) -> dict[Path, str]:
    observed: dict[Path, str] = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Required input is absent: {relative(path)}")
        actual = sha256_file(path)
        expected = EXPECTED_HASHES.get(path)
        if expected is not None and actual != expected:
            raise ValueError(
                f"Input hash mismatch for {relative(path)}: expected {expected}, observed {actual}"
            )
        observed[path] = actual
    return observed


def manifest_index() -> dict[str, dict[str, str]]:
    rows, _ = read_csv(MANIFEST)
    index = {row["artifact_id"]: row for row in rows}
    for path, artifact_id in MANIFEST_IDENTITIES.items():
        row = index.get(artifact_id)
        if row is None:
            raise ValueError(f"Manifest identity missing: {artifact_id}")
        protected_expected = (
            "6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299"
            if path == MODEL_OUTPUT else EXPECTED_HASHES[path]
        )
        if row["sha256"] != protected_expected:
            raise ValueError(f"Manifest hash differs for {artifact_id}")
    return index


def parse_choices(text: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for item in text.split("|"):
        if not item.strip():
            continue
        code, label = item.split(",", 1)
        numeric = int(code.strip())
        if numeric in result:
            raise ValueError(f"Duplicate REDCap choice code {numeric}")
        result[numeric] = label.strip()
    return result


def load_label_universe() -> tuple[dict[int, str], dict[int, str], frozenset[str]]:
    dictionary, fields = read_csv(REDCAP_DICTIONARY)
    required = {"Variable / Field Name", "Choices, Calculations, OR Slider Labels", "Field Label"}
    if not required <= set(fields):
        raise ValueError("Frozen REDCap dictionary lacks required label-mapping columns")
    by_name = {row["Variable / Field Name"]: row for row in dictionary}
    domain_map = parse_choices(by_name["sc_domains"]["Choices, Calculations, OR Slider Labels"])
    purpose_map = parse_choices(by_name["sc_purposes"]["Choices, Calculations, OR Slider Labels"])
    taxonomy = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    active = [row for row in taxonomy["categories"] if row.get("include_in_prompt")]
    domains = frozenset(row["label"] for row in active if row["layer"] == "Layer A -- domain")
    purposes = frozenset(row["label"] for row in active if row["layer"] == "Layer C -- purpose")
    tags = frozenset(row["label"] for row in active if row["layer"] == "Cross-cutting tag")
    if frozenset(domain_map.values()) != domains or len(domains) != 12:
        raise ValueError("Frozen domain choices do not match the 12-label MOD-001 universe")
    if frozenset(purpose_map.values()) != purposes or len(purposes) != 8:
        raise ValueError("Frozen purpose choices do not match the 8-label MOD-001 universe")
    if tags != frozenset(TAG_NAMES) or len(tags) != 2:
        raise ValueError(f"Joint tag universe is not the expected two labels: {sorted(tags)}")
    if by_name["sc_equity"]["Field Label"] != TAG_NAMES[0] or by_name["sc_covid"]["Field Label"] != TAG_NAMES[1]:
        raise ValueError("Frozen tag fields do not match the MOD-001 tag universe")
    return domain_map, purpose_map, tags


def integer(value: str) -> int | None:
    return None if value == "" else int(value)


def checkbox_codes(row: Mapping[str, str], prefix: str, codes: Iterable[int]) -> frozenset[int] | None:
    values = {code: row[f"{prefix}___{code}"] for code in codes}
    if any(value not in {"0", "1"} for value in values.values()):
        return None
    return frozenset(code for code, value in values.items() if value == "1")


def validator_payload(row: Mapping[str, str]) -> dict[str, Any]:
    domains = checkbox_codes(row, "sc_domains", range(1, 13))
    purposes = checkbox_codes(row, "sc_purposes", range(1, 9))
    issues = checkbox_codes(row, "sc_tax_issue", (1, 2, 5))
    return {
        "assignment_id": row["assignment_id"],
        "instrument_ver": row["instrument_ver"],
        "record_kind": integer(row["record_kind"]),
        "sc_blind_decl": integer(row["sc_blind_decl"]),
        "sc_exposure": integer(row["sc_exposure"]),
        "sc_exposure_note": row["sc_exposure_note"],
        "sc_domains": sorted(domains) if domains is not None else None,
        "sc_purposes": sorted(purposes) if purposes is not None else None,
        "sc_covid": integer(row["sc_covid"]),
        "sc_equity": integer(row["sc_equity"]),
        "sc_sufficiency": integer(row["sc_sufficiency"]),
        "sc_taxonomy_fit": integer(row["sc_taxonomy_fit"]),
        "sc_tax_issue": sorted(issues) if issues is not None else None,
        "sc_confidence": integer(row["sc_confidence"]),
        "sc_note": row["sc_note"],
    }


def decode_human_row(
    row: Mapping[str, str], domain_map: Mapping[int, str], purpose_map: Mapping[int, str]
) -> tuple[dict[str, frozenset[str] | None], list[str]]:
    payload = validator_payload(row)
    errors = frozen_validator.validate_scratch(payload)
    complete = row["scratch_coder_complete"] == "2"
    domain_codes = payload["sc_domains"]
    purpose_codes = payload["sc_purposes"]
    equity = payload["sc_equity"]
    covid = payload["sc_covid"]
    domains = None if not complete or domain_codes is None else frozenset(domain_map[code] for code in domain_codes)
    purposes = None if not complete or purpose_codes is None else frozenset(purpose_map[code] for code in purpose_codes)
    if not complete or equity not in {0, 1} or covid not in {0, 1}:
        tags = None
    else:
        tags = frozenset(
            tag for tag, present in ((TAG_NAMES[0], equity), (TAG_NAMES[1], covid)) if present == 1
        )
    return {
        "Research Domains": domains,
        "Analytical Purposes": purposes,
        "Joint cross-cutting tag set": tags,
    }, errors


def semicolon_set_with_audit(value: str, *, record_id: str, field: str) -> tuple[frozenset[str], dict[str, str] | None]:
    if not value:
        return frozenset(), None
    tokens = [part.strip() for part in value.split(";") if part.strip()]
    duplicate = None
    if len(tokens) != len(set(tokens)):
        duplicate = {"record_key": record_id, "field": field}
    return frozenset(tokens), duplicate


def decode_model_rows(
    rows: Sequence[Mapping[str, str]], formal_ids: set[str], domain_universe: frozenset[str],
    purpose_universe: frozenset[str], tag_universe: frozenset[str],
) -> tuple[dict[str, dict[str, frozenset[str]]], list[dict[str, str]]]:
    identifiers = [row["Record ID"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Frozen model output contains duplicate Record IDs")
    by_id = {row["Record ID"]: row for row in rows if row["Record ID"] in formal_ids}
    if set(by_id) != formal_ids:
        raise ValueError("Formal sample does not join one-to-one to the frozen Fable 5 output")
    output: dict[str, dict[str, frozenset[str]]] = {}
    duplicates: list[dict[str, str]] = []
    for record_id, row in by_id.items():
        domains, duplicate = semicolon_set_with_audit(
            row["substantive_domains"], record_id=record_id, field="substantive_domains"
        )
        if duplicate:
            duplicates.append(duplicate)
        purposes, duplicate = semicolon_set_with_audit(
            row["analytical_purpose"], record_id=record_id, field="analytical_purpose"
        )
        if duplicate:
            duplicates.append(duplicate)
        tags, duplicate = semicolon_set_with_audit(
            row["cross_cutting_tags"], record_id=record_id, field="cross_cutting_tags"
        )
        if duplicate:
            duplicates.append(duplicate)
        unknown = (domains - domain_universe) | (purposes - purpose_universe) | (tags - tag_universe)
        if unknown:
            raise ValueError(f"Unknown model taxonomy label at Record ID {record_id}")
        output[record_id] = {
            "Research Domains": domains,
            "Analytical Purposes": purposes,
            "Joint cross-cutting tag set": tags,
        }
    return output, duplicates


def classify_relation(left: frozenset[str] | None, right: frozenset[str] | None) -> str:
    if left is None or right is None:
        raise ValueError("Missing observations cannot be assigned a set relation")
    if not left and not right:
        return "both_empty"
    if not left or not right:
        return "exactly_one_empty"
    if left == right:
        return "identical"
    if left < right or right < left:
        return "containment"
    if left & right:
        return "overlap"
    return "disjoint"


def relation_row(
    *, population: str, dimension: str, family: str, relation: str, eligible_records: int,
    counts: Mapping[str, int],
) -> dict[str, str | int]:
    total = sum(counts[item] for item in RELATIONS)
    nonempty = counts["containment"] + counts["overlap"] + counts["disjoint"]
    all_nonidentical = nonempty + counts["exactly_one_empty"]
    empty_involved = counts["both_empty"] + counts["exactly_one_empty"]
    nonempty_applicable = relation in {"containment", "overlap", "disjoint"}
    all_applicable = relation in {"containment", "overlap", "disjoint", "exactly_one_empty"}
    if nonempty_applicable and nonempty:
        p_nonempty, nonempty_status = format(counts[relation] / nonempty, ".17g"), "reported"
    elif nonempty_applicable:
        p_nonempty, nonempty_status = "", "zero_denominator"
    else:
        p_nonempty, nonempty_status = "", "not_applicable"
    if all_applicable and all_nonidentical:
        p_all, all_status = format(counts[relation] / all_nonidentical, ".17g"), "reported"
    elif all_applicable:
        p_all, all_status = "", "zero_denominator"
    else:
        p_all, all_status = "", "not_applicable"
    return {
        "population": population,
        "dimension": dimension,
        "pair_family": family,
        "relation": relation,
        "eligible_records": eligible_records,
        "count": counts[relation],
        "total_pairs_classified": total,
        "nonidentical_nonempty_pairs": nonempty,
        "all_nonidentical_pairs": all_nonidentical,
        "empty_set_involved_pairs": empty_involved,
        "proportion_of_nonidentical_nonempty_pairs": p_nonempty,
        "nonempty_proportion_status": nonempty_status,
        "proportion_of_all_nonidentical_pairs": p_all,
        "all_proportion_status": all_status,
    }


def source_refs() -> dict[str, dict[str, Any]]:
    human_fields = {
        "domains": [f"sc_domains___{code}" for code in range(1, 13)],
        "purposes": [f"sc_purposes___{code}" for code in range(1, 9)],
        "joint_tags": ["sc_equity", "sc_covid"],
    }
    return {
        "human:domains": {"path": relative(RAW_EXPORT), "row_key": ["source_record_id", "reviewer_id"], "fields": human_fields["domains"]},
        "human:purposes": {"path": relative(RAW_EXPORT), "row_key": ["source_record_id", "reviewer_id"], "fields": human_fields["purposes"]},
        "human:joint_tags": {"path": relative(RAW_EXPORT), "row_key": ["source_record_id", "reviewer_id"], "fields": human_fields["joint_tags"]},
        "model:domains": {"path": relative(MODEL_OUTPUT), "row_key": ["Record ID"], "fields": ["substantive_domains"]},
        "model:purposes": {"path": relative(MODEL_OUTPUT), "row_key": ["Record ID"], "fields": ["analytical_purpose"]},
        "model:joint_tags": {"path": relative(MODEL_OUTPUT), "row_key": ["Record ID"], "fields": ["cross_cutting_tags"]},
    }


def dimension_ref_suffix(dimension: str) -> str:
    return {
        "Research Domains": "domains",
        "Analytical Purposes": "purposes",
        "Joint cross-cutting tag set": "joint_tags",
    }[dimension]


def endpoint_ledger(identifier: str, record_id: str, dimension: str) -> dict[str, Any]:
    suffix = dimension_ref_suffix(dimension)
    if identifier == MODEL_ENDPOINT:
        return {
            "identifier": identifier,
            "source_ref": f"model:{suffix}",
            "row_key": {"Record ID": record_id},
        }
    return {
        "identifier": identifier,
        "source_ref": f"human:{suffix}",
        "row_key": {"source_record_id": record_id, "reviewer_id": identifier},
    }


def construct_data() -> dict[str, Any]:
    manifest = manifest_index()
    stage_a_metadata = json.loads(STAGE_A_METADATA.read_text(encoding="utf-8"))
    stage_b_metadata = json.loads(STAGE_B_METADATA.read_text(encoding="utf-8"))
    domain_map, purpose_map, tag_universe = load_label_universe()
    domain_universe = frozenset(domain_map.values())
    purpose_universe = frozenset(purpose_map.values())

    raw_rows, raw_fields = read_csv(RAW_EXPORT)
    formal = [row for row in raw_rows if row.get("validation_included") == "1"]
    if len(formal) != 675:
        raise ValueError(f"Expected 675 formal responses, observed {len(formal)}")
    required_raw = {
        "assignment_id", "source_record_id", "reviewer_id", "validation_included",
        "scratch_coder_complete", "sc_equity", "sc_covid",
    }
    if not required_raw <= set(raw_fields):
        raise ValueError(f"Frozen export lacks required columns: {sorted(required_raw - set(raw_fields))}")
    if len({row["assignment_id"] for row in formal}) != len(formal):
        raise ValueError("Formal frozen export contains duplicate assignment IDs")
    response_keys = [(row["source_record_id"], row["reviewer_id"]) for row in formal]
    if len(response_keys) != len(set(response_keys)):
        raise ValueError("Formal frozen export contains duplicate record/coder responses")
    if set(row["reviewer_id"] for row in formal) != set(CODERS):
        raise ValueError("Formal coder identities differ from C01/C02/C03")

    crosswalk, cross_fields = read_csv(CROSSWALK_AUTHORITY)
    required_cross = {"assignment_id", "reviewer_id", "source_record_id", "sample_family"}
    if not required_cross <= set(cross_fields) or len(crosswalk) != 675:
        raise ValueError("POST-019 schema or row count differs from the resolved formal crosswalk")
    cross_ids = [row["assignment_id"] for row in crosswalk]
    if len(cross_ids) != len(set(cross_ids)) or set(cross_ids) != {row["assignment_id"] for row in formal}:
        raise ValueError("POST-019 does not join one-to-one to the formal export")
    cross_by_assignment = {row["assignment_id"]: row for row in crosswalk}
    for row in formal:
        authority = cross_by_assignment[row["assignment_id"]]
        if row["reviewer_id"] != authority["reviewer_id"] or row["source_record_id"] != authority["source_record_id"]:
            raise ValueError("Formal export reviewer/source identity differs from POST-019")

    baseline, baseline_fields = read_csv(BASELINE_AUTHORITY)
    hard, hard_fields = read_csv(HARD_AUTHORITY)
    if "record_id" not in baseline_fields or "record_id" not in hard_fields:
        raise ValueError("Sample authority lacks record_id")
    population_ids = {
        "baseline": {row["record_id"] for row in baseline},
        "hard_case": {row["record_id"] for row in hard},
    }
    if len(population_ids["baseline"]) != 150 or len(population_ids["hard_case"]) != 75:
        raise ValueError("POST-009/POST-011 population sizes differ from 150/75")
    if population_ids["baseline"] & population_ids["hard_case"]:
        raise ValueError("POST-009 and POST-011 overlap")
    formal_ids = {row["source_record_id"] for row in formal}
    if population_ids["baseline"] | population_ids["hard_case"] != formal_ids:
        raise ValueError("POST-009/POST-011 do not exactly partition the formal records")
    for population, record_ids in population_ids.items():
        cross_ids_for_population = {
            row["source_record_id"] for row in crosswalk if row["sample_family"] == population
        }
        if cross_ids_for_population != record_ids:
            raise ValueError(f"POST-019 population membership differs for {population}")

    humans: dict[str, dict[str, dict[str, frozenset[str] | None]]] = defaultdict(dict)
    structural_invalid: list[dict[str, Any]] = []
    exposure_count = 0
    for row in formal:
        decoded, errors = decode_human_row(row, domain_map, purpose_map)
        record_id, coder = row["source_record_id"], row["reviewer_id"]
        humans[record_id][coder] = decoded
        if errors:
            structural_invalid.append({"record_key": record_id, "coder": coder, "errors": errors})
        if row["sc_exposure"] == "1":
            exposure_count += 1
    if structural_invalid:
        raise ValueError("Frozen formal responses no longer reproduce the zero-invalid Stage A audit")
    for record_id in formal_ids:
        if set(humans[record_id]) != set(CODERS):
            raise ValueError(f"Record {record_id} does not have the formal three-coder panel")

    model_rows, _ = read_csv(MODEL_OUTPUT)
    models, duplicate_tokens = decode_model_rows(
        model_rows, formal_ids, domain_universe, purpose_universe, tag_universe
    )
    if duplicate_tokens:
        raise ValueError("Frozen model output contains duplicate delimiter tokens; see parser audit")

    denominator_rows, _ = read_csv(STAGE_A_DENOMINATORS)
    expected_complete = {
        (row["population"], row["measure"].split(" | ", 1)[0]): int(row["numerator"])
        for row in denominator_rows
        if row["analysis"] == "completion_and_qa"
        and row["population"] in POPULATIONS
        and row["measure"].endswith("complete_matched_three_coder_panels")
    }
    replacement_rows, _ = read_csv(STAGE_A_REPLACEMENT)
    replacement_n = {
        (row["population"], row["dimension"]): int(row["n_records"])
        for row in replacement_rows
        if row["population"] in POPULATIONS and row["panel"] == "ABC"
    }

    eligible: dict[tuple[str, str], list[str]] = {}
    exclusions: list[dict[str, str]] = []
    for population in POPULATIONS:
        for dimension in DIMENSIONS:
            retained: list[str] = []
            for record_id in sorted(population_ids[population]):
                missing = [coder for coder in CODERS if humans[record_id][coder][dimension] is None]
                if models[record_id][dimension] is None:
                    missing.append(MODEL_ENDPOINT)
                if missing:
                    exclusions.append({
                        "record_key": record_id,
                        "population": population,
                        "dimension": dimension,
                        "reason": "existing dimension-specific complete-case mask: unavailable endpoint(s) " + ", ".join(missing),
                        "exclusion_type": "existing_cohort_mask",
                    })
                else:
                    retained.append(record_id)
            eligible[(population, dimension)] = retained
            if dimension != "Joint cross-cutting tag set":
                expected = expected_complete.get((population, dimension))
                if expected != len(retained) or replacement_n.get((population, dimension)) != len(retained):
                    raise ValueError(f"Eligible cohort differs from archived Stage A outputs for {population}/{dimension}")
            else:
                equity_expected = expected_complete.get((population, "Demographic disparities / equity"))
                covid_expected = expected_complete.get((population, "COVID-19 & Pandemic"))
                if equity_expected != len(retained) or covid_expected != len(retained):
                    raise ValueError(f"Joint tag intersection differs from separate tag masks for {population}")

    if exclusions:
        raise ValueError("An unexplained complete-case mismatch exists despite the archived all-complete audit")

    return {
        "manifest": manifest,
        "stage_a_metadata": stage_a_metadata,
        "stage_b_metadata": stage_b_metadata,
        "humans": humans,
        "models": models,
        "population_ids": population_ids,
        "eligible": eligible,
        "exclusions": exclusions,
        "duplicate_tokens": duplicate_tokens,
        "structural_invalid": structural_invalid,
        "exposure_response_count": exposure_count,
        "label_universe": {
            "Research Domains": sorted(domain_universe),
            "Analytical Purposes": sorted(purpose_universe),
            "Joint cross-cutting tag set": list(TAG_NAMES),
        },
    }


def enumerate_pairs(data: Mapping[str, Any]) -> tuple[list[dict[str, str | int]], list[dict[str, Any]]]:
    humans = data["humans"]
    models = data["models"]
    ledger: list[dict[str, Any]] = []
    counts_by_group: dict[tuple[str, str, str], Counter[str]] = {}
    for population in POPULATIONS:
        for dimension in DIMENSIONS:
            record_ids = data["eligible"][(population, dimension)]
            for family in PAIR_FAMILIES:
                counts: Counter[str] = Counter({relation: 0 for relation in RELATIONS})
                for record_id in record_ids:
                    if family == "human_human":
                        pairs = itertools.combinations(CODERS, 2)
                    else:
                        pairs = ((MODEL_ENDPOINT, coder) for coder in CODERS)
                    observed_pair_count = 0
                    for left_id, right_id in pairs:
                        left = models[record_id][dimension] if left_id == MODEL_ENDPOINT else humans[record_id][left_id][dimension]
                        right = humans[record_id][right_id][dimension]
                        relation = classify_relation(left, right)
                        counts[relation] += 1
                        observed_pair_count += 1
                        ledger.append({
                            "record_key": record_id,
                            "population": population,
                            "dimension": dimension,
                            "pair_family": family,
                            "endpoint_1": endpoint_ledger(left_id, record_id, dimension),
                            "endpoint_2": endpoint_ledger(right_id, record_id, dimension),
                            "relation": relation,
                        })
                    if observed_pair_count != 3:
                        raise ValueError(f"Expected three {family} pairs for {record_id}/{dimension}")
                counts_by_group[(population, dimension, family)] = counts

    rows: list[dict[str, str | int]] = []
    for population in POPULATIONS:
        for dimension in DIMENSIONS:
            for family in PAIR_FAMILIES:
                counts = counts_by_group[(population, dimension, family)]
                for relation in RELATIONS:
                    rows.append(relation_row(
                        population=population,
                        dimension=dimension,
                        family=family,
                        relation=relation,
                        eligible_records=len(data["eligible"][(population, dimension)]),
                        counts=counts,
                    ))
    return rows, ledger


def validate_results(rows: Sequence[Mapping[str, Any]], ledger: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(rows) != 72:
        raise ValueError(f"Expected 72 distribution rows, observed {len(rows)}")
    row_keys = [(row["population"], row["dimension"], row["pair_family"], row["relation"]) for row in rows]
    if len(row_keys) != len(set(row_keys)):
        raise ValueError("Distribution row keys are not unique")
    expected_keys = set(itertools.product(POPULATIONS, DIMENSIONS, PAIR_FAMILIES, RELATIONS))
    if set(row_keys) != expected_keys:
        raise ValueError("Distribution does not contain the full expected category grid")
    ledger_keys = [
        (
            item["record_key"], item["population"], item["dimension"], item["pair_family"],
            item["endpoint_1"]["identifier"], item["endpoint_2"]["identifier"],
        )
        for item in ledger
    ]
    if len(ledger_keys) != len(set(ledger_keys)):
        raise ValueError("Pair ledger keys are not unique")
    grouped_ledger: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    for item in ledger:
        if item["relation"] not in RELATIONS:
            raise ValueError("Pair ledger contains an unknown relation")
        grouped_ledger[(item["population"], item["dimension"], item["pair_family"])][item["relation"]] += 1
    tolerance = 1e-12
    for group in itertools.product(POPULATIONS, DIMENSIONS, PAIR_FAMILIES):
        group_rows = [row for row in rows if (row["population"], row["dimension"], row["pair_family"]) == group]
        if len(group_rows) != 6:
            raise ValueError(f"Group {group} does not have six relation rows")
        total = sum(int(row["count"]) for row in group_rows)
        if any(int(row["total_pairs_classified"]) != total for row in group_rows):
            raise ValueError(f"Group {group} has inconsistent total-pair denominators")
        eligible_records = int(group_rows[0]["eligible_records"])
        if total != eligible_records * 3:
            raise ValueError(f"Group {group} pair count differs from three per eligible record")
        for row in group_rows:
            if grouped_ledger[group][row["relation"]] != int(row["count"]):
                raise ValueError(f"Ledger does not reconcile for {group}/{row['relation']}")
        nonempty_values = [
            float(row["proportion_of_nonidentical_nonempty_pairs"])
            for row in group_rows if row["nonempty_proportion_status"] == "reported"
        ]
        nonempty_denominator = int(group_rows[0]["nonidentical_nonempty_pairs"])
        if nonempty_denominator and abs(sum(nonempty_values) - 1.0) > tolerance:
            raise ValueError(f"Nonempty conditional proportions do not sum to one for {group}")
        if not nonempty_denominator and any(row["proportion_of_nonidentical_nonempty_pairs"] for row in group_rows):
            raise ValueError(f"Zero nonempty denominator has numerical proportions for {group}")
        all_values = [
            float(row["proportion_of_all_nonidentical_pairs"])
            for row in group_rows if row["all_proportion_status"] == "reported"
        ]
        all_denominator = int(group_rows[0]["all_nonidentical_pairs"])
        if all_denominator and abs(sum(all_values) - 1.0) > tolerance:
            raise ValueError(f"All-disagreement conditional proportions do not sum to one for {group}")
        if not all_denominator and any(row["proportion_of_all_nonidentical_pairs"] for row in group_rows):
            raise ValueError(f"Zero all-disagreement denominator has numerical proportions for {group}")
    tag_overlap = [
        row for row in rows if row["dimension"] == "Joint cross-cutting tag set" and row["relation"] == "overlap"
    ]
    if any(int(row["count"]) != 0 for row in tag_overlap):
        raise ValueError("Two-label joint tag sets unexpectedly contain overlap without containment")
    return {
        "status": "passed",
        "distribution_rows": 72,
        "pair_ledger_entries": len(ledger),
        "unique_distribution_keys": True,
        "unique_pair_keys": True,
        "one_relation_per_pair": True,
        "three_pairs_per_family_per_retained_record": True,
        "families_share_eligible_records": True,
        "category_counts_reconcile": True,
        "conditional_denominators_reconcile": True,
        "conditional_proportions_sum_to_one_tolerance": tolerance,
        "zero_denominators_have_no_numeric_proportions": True,
        "joint_tag_overlap_structural_zero": True,
    }


def markdown_proportion(value: Any, status: str) -> str:
    if status == "reported":
        return f"{float(value):.4f}"
    return f"— ({status})"


def render_markdown(rows: Sequence[Mapping[str, Any]], data: Mapping[str, Any], timestamp: str) -> str:
    lines = [
        "# Descriptive distribution of scratch-coder/model disagreement types",
        "",
        f"Generated: `{timestamp}`",
        "",
        "This is a newly calculated descriptive supplement from frozen coded data. It reports set-relation counts and two specified pair-weighted conditional distributions only. It does not calculate an agreement coefficient, a distance score, an inferential interval, or the effect of an alternative distance on alpha.",
        "",
        "## Scope and frozen inputs",
        "",
        "The formal panel uses C01, C02 and C03, the 150-record random baseline (POST-009), the separate 75-record hard-case sample (POST-011), resolved assignments from POST-019, and the frozen Fable 5 production classifications (MOD-006). Research Domains and Analytical Purposes use the dimension-specific common complete-case rule from the saved Stage A replacement-panel methods. The joint cross-cutting tag set uses the intersection of the separate equity-tag and COVID-tag panel masks.",
        "",
        "| Role | Identity | Source |",
        "|---|---|---|",
        f"| Scratch-coder responses | POST-028 | `{relative(RAW_EXPORT)}` |",
        f"| Baseline membership | POST-009 | `{relative(BASELINE_AUTHORITY)}` |",
        f"| Hard-case membership | POST-011 | `{relative(HARD_AUTHORITY)}` |",
        f"| Resolved formal assignments | POST-019 | `{relative(CROSSWALK_AUTHORITY)}` |",
        f"| Production model classifications | MOD-006, Fable 5 | `{relative(MODEL_OUTPUT)}` |",
        f"| Frozen taxonomy | MOD-001, dict-1.0-rc2 | `{relative(TAXONOMY)}` |",
        f"| Frozen instrument dictionary | RED-036, candidate-0.7 | `{relative(REDCAP_DICTIONARY)}` |",
        "",
        "POST-028 was read under the 9 September 2026 named-file amendment. The original categorical restricted-path prohibition conflicted with the record-level data requirement; the amendment permits this one hash-verified input and the exact POST-009/011/019 authorities without relaxing access to other restricted content.",
        "",
        "## Parsing and cohort rules",
        "",
        "Domain and purpose responses are decoded from their explicit REDCap checkbox columns using the frozen RED-036 choice mapping. Checkbox `0` means known unselected, not missing. Tags use `sc_equity` and `sc_covid`, where `0` is known absent and `1` is present; two known-absent tags therefore form a valid empty joint set. The model fields use the saved semicolon-only codec: split on `;`, trim delimiter-adjacent whitespace, discard blank delimiter fragments, preserve spelling/case, and deduplicate only through set construction. No duplicate model tokens occurred. All decoded labels were checked against MOD-001; `Unclear from Register Entry` remains an ordinary dimension-specific label.",
        "",
        "An empty decoded set is distinct from a missing or invalid observation. Missing observations are not classified. Formal rows require `validation_included=1`; assignment, reviewer and source-record identities match POST-019 one-to-one; and each retained record has one complete response from each of C01/C02/C03 plus a model observation. The primary masks retain exposure flags and structurally invalid responses under the saved Stage A rule; the frozen data reproduce zero structurally invalid formal responses. One exposure-flagged response remains in the baseline primary cohort, as in Stage A.",
        "",
        "The canonical record unit is `source_record_id`; `assignment_id` resolves submissions through POST-019 but is not treated as the record unit. Human–human and model–human families use exactly the same eligible records within each population/dimension. Each retained record contributes three unordered human pairs and three model–human pairs. Pair records are descriptive units and are not treated as independent observations for inference.",
        "",
        "## Relation definitions",
        "",
        "The ordered checks are: both sets empty (`both_empty`); exactly one empty (`exactly_one_empty`); equal nonempty sets (`identical`); proper-subset relation (`containment`); nonempty intersection without containment (`overlap`); and disjoint nonempty sets (`disjoint`). These categories are mutually exclusive and exhaustive for two available sets. `both_empty` is identical assignment, not disagreement.",
        "",
        "The first proportion conditions on non-identical pairs with both sets nonempty (containment + overlap + disjoint). The second conditions on all non-identical pairs (those three categories + exactly one empty). `empty_set_involved_pairs` is the combined `both_empty` + `exactly_one_empty` count, not a seventh category. CSV proportions retain up to 17 significant digits; the tables below display four decimal places.",
        "",
        "The joint-tag view is supplementary to the existing separate binary-tag analyses and does not replace or reinterpret them. With exactly two possible tag labels, two nonempty sets cannot overlap without one containing the other unless they are equal; joint-tag `overlap` is therefore a structural zero and is retained as a row.",
        "",
        "## Distributions",
    ]
    for population in POPULATIONS:
        pop_title = "Random baseline" if population == "baseline" else "Hard-case sample — DIAGNOSTIC — non-representative"
        lines.extend(["", f"### {pop_title}"])
        if population == "hard_case":
            lines.extend(["", "All tables in this subsection are **DIAGNOSTIC — non-representative**."])
        for dimension in DIMENSIONS:
            for family in PAIR_FAMILIES:
                group_rows = [
                    row for row in rows
                    if row["population"] == population and row["dimension"] == dimension and row["pair_family"] == family
                ]
                title = f"{dimension} — {family}"
                if population == "hard_case":
                    title += " — DIAGNOSTIC — non-representative"
                first = group_rows[0]
                lines.extend([
                    "",
                    f"#### {title}",
                    "",
                    f"Eligible records: {first['eligible_records']}; classified pair units: {first['total_pairs_classified']}; non-identical/nonempty denominator: {first['nonidentical_nonempty_pairs']}; all-non-identical denominator: {first['all_nonidentical_pairs']}; empty-set-involved pairs: {first['empty_set_involved_pairs']}.",
                    "",
                    "| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |",
                    "|---|---:|---:|---:|",
                ])
                for row in group_rows:
                    lines.append(
                        f"| {row['relation']} | {row['count']} | "
                        f"{markdown_proportion(row['proportion_of_nonidentical_nonempty_pairs'], row['nonempty_proportion_status'])} | "
                        f"{markdown_proportion(row['proportion_of_all_nonidentical_pairs'], row['all_proportion_status'])} |"
                    )
    lines.extend(["", "## Exclusions", ""])
    if not data["exclusions"]:
        lines.append("No record was excluded: all 150 baseline and 75 hard-case records satisfied each relevant complete-case mask, including the joint-tag intersection. There were no new unresolved data problems.")
    else:
        lines.extend([
            "| Record key | Population | Dimension | Type | Reason |",
            "|---|---|---|---|---|",
        ])
        for item in data["exclusions"]:
            lines.append(
                f"| {item['record_key']} | {item['population']} | {item['dimension']} | "
                f"{item['exclusion_type']} | {item['reason']} |"
            )
    lines.extend([
        "",
        "## Reporting boundary",
        "",
        "These counts and proportions do not determine alpha, quantify distance sensitivity, assess whether MASI or Jaccard is preferable, or establish coder/model quality, accuracy or superiority. They do not validate, confirm or undermine the canonical report, and they imply no release, review-trigger or equity/purpose conclusion.",
        "",
    ])
    return "\n".join(lines)


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def metadata_source_entry(
    path: Path, before: Mapping[Path, str], after: Mapping[Path, str], *, restricted: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": relative(path),
        "sha256_before": before[path],
        "sha256_after": after[path],
        "unchanged": before[path] == after[path],
        "restricted_named_file_read": restricted,
        "tracked_by_git": bool(git_output("ls-files", "--", relative(path))),
    }
    if path in MANIFEST_IDENTITIES:
        result["manifest_id"] = MANIFEST_IDENTITIES[path]
    if path == MODEL_OUTPUT:
        result.update({
            "protected_raw_sha256": "6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299",
            "representation_note": "Observed file is the Git working-tree LF-normalised representation recorded by Stage B.",
        })
    return result


def build_metadata(
    *, timestamp: str, invocation: list[str], output_dir: Path, rows: Sequence[Mapping[str, Any]],
    ledger: Sequence[Mapping[str, Any]], data: Mapping[str, Any], input_before: Mapping[Path, str],
    input_after: Mapping[Path, str], validation: Mapping[str, Any], repository_status_start: str,
    repository_status_before_metadata: str, csv_path: Path, markdown_path: Path,
) -> dict[str, Any]:
    code_files = [PACKAGE / "__init__.py", PACKAGE / "__main__.py", PACKAGE / "generate.py", PACKAGE / "test_generate.py"]
    relevant_diff = git_output("status", "--porcelain=v1", "--untracked-files=all", "--", *(relative(path) for path in code_files))
    restricted = {RAW_EXPORT, BASELINE_AUTHORITY, HARD_AUTHORITY, CROSSWALK_AUTHORITY}
    source_entries = [
        metadata_source_entry(path, input_before, input_after, restricted=path in restricted)
        for path in input_before
    ]
    counts = Counter((row["population"], row["dimension"], row["pair_family"]) for row in rows)
    return {
        "status": "complete",
        "artifact_type": "newly calculated descriptive disagreement-type supplement",
        "generation_timestamp_utc": timestamp,
        "invocation": invocation,
        "output_directory": relative(output_dir),
        "generator": {
            "module": "analysis.scratch_coder_disagreement_types",
            "git_head": git_output("rev-parse", "--verify", "HEAD"),
            "relevant_code_matches_head": relevant_diff == "",
            "relevant_code_status": relevant_diff,
            "code_files": [{"path": relative(path), "sha256": sha256_file(path)} for path in code_files],
            "python_version": sys.version,
            "pyyaml_version": getattr(yaml, "__version__", "unavailable"),
        },
        "repository_state": {
            "status_porcelain_at_execution_start": repository_status_start.splitlines(),
            "status_porcelain_after_csv_markdown_before_metadata": repository_status_before_metadata.splitlines(),
            "note": "Repository status is distinct from whether the relevant committed generator code matches HEAD.",
        },
        "source_release_identifiers": {
            "scratch_export": "POST-028",
            "baseline_population": "POST-009",
            "hard_case_population": "POST-011",
            "formal_assignment_crosswalk": "POST-019",
            "taxonomy": {"manifest_id": "MOD-001", "version": "dict-1.0-rc2"},
            "instrument": {"manifest_id": "RED-036", "version": "redcap-candidate-0.7"},
            "validator": "RED-013",
            "production_model": {"manifest_id": "MOD-006", "name": "Fable 5"},
            "protocol": {"manifest_id": "PRO-018", "sha256": data["stage_a_metadata"]["protocol_sha256"]},
            "stage_a_run_datetime": data["stage_a_metadata"]["analysis_run_datetime"],
            "stage_a_code_identity": data["stage_a_metadata"]["analysis_code_commit_or_worktree_state"],
            "stage_b_run_datetime": data["stage_b_metadata"]["analysis_run_datetime"],
            "stage_b_git_head": data["stage_b_metadata"]["git_HEAD"],
        },
        "input_files": source_entries,
        "restricted_path_authorisation": {
            "amendment_date": "2026-09-09",
            "reason": "The original categorical restriction conflicted with the record-level data requirement; access was narrowed to named, hash-verified files.",
            "files_read": [
                {"manifest_id": MANIFEST_IDENTITIES[path], "path": relative(path), "verified_sha256": input_before[path]}
                for path in (RAW_EXPORT, BASELINE_AUTHORITY, HARD_AUTHORITY, CROSSWALK_AUTHORITY)
            ],
            "post_009_post_011_post_019_needed": {
                "POST-009": "read; defines baseline membership",
                "POST-011": "read; defines hard-case membership",
                "POST-019": "read; verifies resolved assignment/reviewer/source keys and population membership",
            },
            "content_handling": "No restricted input or extract was copied to a permitted path, output artifact, or Git. Outputs contain aggregates and a key-only pair ledger, without raw response text or full label sets.",
            "access_boundary": "No other preregistration_restricted path was listed, traversed, opened, or read.",
        },
        "path_resolution_observations": {
            "POST-028": {
                "manifest_current_path": data["manifest"]["POST-028"]["current_path"],
                "manifest_path_present": False,
                "manifest_directory_observation": "The public canonical directory contains only .gitkeep.",
                "gitignore_rule": ".gitignore:161 excludes /preregistration/post_registration/redcap_exports/*; line 162 re-includes .gitkeep.",
                "action": "No reconciliation attempted; manifest and .gitignore were unchanged.",
            },
            "POST-019": {
                "manifest_current_path": data["manifest"]["POST-019"]["current_path"],
                "manifest_path_present": False,
                "resolved_path": relative(CROSSWALK_AUTHORITY),
                "resolution_evidence": "Stage B run_metadata.json formal_assignment_crosswalk_path plus matching POST-019 SHA-256.",
            },
        },
        "parsing_decisions": [
            "Formal rows are those with validation_included=1.",
            "source_record_id is the record unit; assignment_id is the one-to-one submission-resolution key checked against POST-019.",
            "Domains use sc_domains___1..12 and purposes use sc_purposes___1..8; every checkbox must be exactly 0 or 1.",
            "Checkbox 0 is known unselected; an all-zero domain group is an explicit empty set if otherwise valid.",
            "Human tags use sc_equity/sc_covid with 0 known absent, 1 present, and blank/invalid unavailable.",
            "The joint tag set is available only when both tag states are known for every human and the model.",
            "Model sets split only on semicolon, trim delimiter-adjacent whitespace, discard blank fragments, and otherwise preserve exact labels.",
            "Duplicate tokens follow set decoding and are separately audited; no occurrences were observed.",
            "All labels are validated against release-specific MOD-001 dimension universes; no fuzzy matching or aliases are used.",
            "Unclear from Register Entry remains an ordinary label in each of its two dimensions.",
            "Explicit empty, missing, and invalid states remain distinct; missing/invalid states are never classified.",
            "Exposure and structural-validity flags follow the Stage A primary-mask policy; exposure does not trigger primary exclusion.",
        ],
        "cohort_evidence": {
            "formal_coders": list(CODERS),
            "formal_response_rows": 675,
            "records": 225,
            "one_response_per_record_coder": True,
            "POST-019_one_to_one_join": True,
            "population_membership": {population: len(data["population_ids"][population]) for population in POPULATIONS},
            "eligible_records": {
                population: {dimension: len(data["eligible"][(population, dimension)]) for dimension in DIMENSIONS}
                for population in POPULATIONS
            },
            "matched_complete_case_evidence": [relative(STAGE_A_METHODS), relative(STAGE_A_DENOMINATORS), relative(STAGE_A_REPLACEMENT)],
            "joint_tag_scope": "Intersection of the existing equity and COVID tag-panel eligibility masks within each population.",
            "human_human_and_model_human_same_records": True,
            "expected_human_pairs_per_record": 3,
            "expected_model_human_pairs_per_record": 3,
            "exposure_flagged_responses_retained_primary": data["exposure_response_count"],
            "structural_invalid_responses": len(data["structural_invalid"]),
        },
        "label_universe": data["label_universe"],
        "duplicate_token_occurrences": data["duplicate_tokens"],
        "exclusions": data["exclusions"],
        "unresolved_limitations": [
            "Stage A recorded its analysis package as untracked in a dirty working tree; the saved methods, metadata and current code identify the historical procedure, but the historical generator bytes were not hash-pinned in that run metadata.",
            "The POST-028 public manifest path is absent and gitignored; this run used only the amendment-authorised restricted copy with the same manifest hash.",
        ],
        "source_reference_legend": source_refs(),
        "pair_ledger": list(ledger),
        "distribution_grid": {
            "populations": list(POPULATIONS),
            "dimensions": list(DIMENSIONS),
            "pair_families": list(PAIR_FAMILIES),
            "relations": list(RELATIONS),
            "rows_per_group": {"/".join(group): count for group, count in sorted(counts.items())},
        },
        "calculation_scope": {
            "calculated": ["relation counts", "specified pair-weighted conditional proportions"],
            "not_calculated": [
                "alpha", "alternative-distance alpha", "kappa", "bootstrap quantities", "replacement deltas",
                "precision", "recall", "F1", "MASI", "Jaccard", "confidence intervals",
                "record-level any-disagreement rates",
            ],
        },
        "validation": dict(validation),
        "output_files": {
            "disagreement_type_distribution.csv": {"sha256": sha256_file(csv_path), "bytes": csv_path.stat().st_size},
            "disagreement_type_summary.md": {"sha256": sha256_file(markdown_path), "bytes": markdown_path.stat().st_size},
        },
        "canonical_results_unchanged": {
            "report_path": relative(CANONICAL_REPORT),
            "report_sha256": input_after[CANONICAL_REPORT],
            "metadata_path": relative(CANONICAL_METADATA),
            "metadata_sha256": input_after[CANONICAL_METADATA],
            "unchanged": input_before[CANONICAL_REPORT] == input_after[CANONICAL_REPORT]
            and input_before[CANONICAL_METADATA] == input_after[CANONICAL_METADATA],
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir.resolve()
    try:
        output_dir.relative_to(ROOT / "analysis")
    except ValueError:
        raise SystemExit("Output directory must be below the repository analysis directory")
    if not output_dir.name.startswith("outputs_disagreement_types_"):
        raise SystemExit("Output directory must use the outputs_disagreement_types_<UTC> convention")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    invocation = [sys.executable, "-m", "analysis.scratch_coder_disagreement_types", *sys.argv[1:]]
    repository_status_start = git_output("status", "--porcelain=v1", "--untracked-files=all")
    inputs = [
        RAW_EXPORT, BASELINE_AUTHORITY, HARD_AUTHORITY, CROSSWALK_AUTHORITY, MODEL_OUTPUT,
        TAXONOMY, REDCAP_DICTIONARY, MANIFEST, STAGE_A_METHODS, STAGE_A_METADATA,
        STAGE_A_DENOMINATORS, STAGE_A_REPLACEMENT, STAGE_B_METADATA, VALIDATOR,
        CANONICAL_REPORT, CANONICAL_METADATA,
    ]
    input_before = verify_hashes(inputs)
    output_dir.mkdir(parents=False, exist_ok=False)
    staging = output_dir / ".staging"
    staging.mkdir()
    csv_final = output_dir / "disagreement_type_distribution.csv"
    markdown_final = output_dir / "disagreement_type_summary.md"
    metadata_final = output_dir / "run_metadata.json"
    try:
        data = construct_data()
        rows, ledger = enumerate_pairs(data)
        validation = validate_results(rows, ledger)
        csv_staging = staging / csv_final.name
        markdown_staging = staging / markdown_final.name
        write_csv(csv_staging, rows)
        markdown_staging.write_text(render_markdown(rows, data, timestamp), encoding="utf-8")
        # Read-back checks ensure the final formats preserve the validated row grid.
        csv_readback, csv_fields = read_csv(csv_staging)
        if tuple(csv_fields) != CSV_COLUMNS or len(csv_readback) != 72:
            raise ValueError("CSV read-back validation failed")
        if markdown_staging.read_text(encoding="utf-8").count("| both_empty |") != 12:
            raise ValueError("Markdown read-back does not contain all twelve group tables")
        os.replace(csv_staging, csv_final)
        os.replace(markdown_staging, markdown_final)
        staging.rmdir()
        input_after = verify_hashes(inputs)
        if input_before != input_after:
            raise ValueError("An input hash changed during execution")
        repository_status_before_metadata = git_output("status", "--porcelain=v1", "--untracked-files=all")
        metadata = build_metadata(
            timestamp=timestamp,
            invocation=invocation,
            output_dir=output_dir,
            rows=rows,
            ledger=ledger,
            data=data,
            input_before=input_before,
            input_after=input_after,
            validation=validation,
            repository_status_start=repository_status_start,
            repository_status_before_metadata=repository_status_before_metadata,
            csv_path=csv_final,
            markdown_path=markdown_final,
        )
        metadata_tmp = output_dir / ".run_metadata.json.tmp"
        metadata_tmp.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        json.loads(metadata_tmp.read_text(encoding="utf-8"))
        os.replace(metadata_tmp, metadata_final)
        if sorted(path.name for path in output_dir.iterdir()) != sorted(
            [csv_final.name, markdown_final.name, metadata_final.name]
        ):
            raise ValueError("Successful output directory contains files beyond the three deliverables")
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        for path in (csv_final, markdown_final, metadata_final, output_dir / ".run_metadata.json.tmp"):
            if path.exists():
                path.unlink()
        if output_dir.exists() and not any(output_dir.iterdir()):
            output_dir.rmdir()
        raise
    print(json.dumps({
        "status": "complete",
        "output_directory": relative(output_dir),
        "rows": 72,
        "pair_ledger_entries": len(ledger),
    }, indent=2))
    return 0
