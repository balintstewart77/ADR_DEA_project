"""Build the Instruction 8A owner candidate frame without contact searches.

This builder intentionally reads the frozen preregistration population, the
training/pilot exclusion sources, and only the Record-ID columns of the two
archived scratch-coder reserve files.  Reserve rows are anti-joined before the
Researchers field is parsed.  It emits one restricted identity-bearing frame
and one de-identified candidate--Record-ID incidence frame.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.validation.owner_sampling_frame import (  # noqa: E402
    _possible_variant,
    normalise_researcher_name,
    parse_researcher_field,
    resolve_frame_entity_statuses,
)
from scripts.verify_training_exclusion_membership import verify_membership  # noqa: E402


POPULATION = REPO_ROOT / "preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv"
EXCLUSIONS = REPO_ROOT / "preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv"
BASELINE_RESERVE = REPO_ROOT / "preregistration_restricted/sampling/official_draw_20260724/baseline_reserve.csv"
HARD_RESERVE = REPO_ROOT / "preregistration_restricted/sampling/official_draw_20260724/hard_reserve.csv"
SAMPLING_METADATA = REPO_ROOT / "preregistration_restricted/sampling/official_draw_20260724/sampling_metadata.json"
SAMPLING_ASSERTIONS = REPO_ROOT / "preregistration_restricted/sampling/official_draw_20260724/sampling_assertion_report.json"
PROTOCOL = REPO_ROOT / "preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx"
SAMPLING_SPECIFICATION = REPO_ROOT / "preregistration/package/04_exclusions_and_sampling/sampling_specification.yaml"
SAMPLING_RUNBOOK = REPO_ROOT / "preregistration/package/04_exclusions_and_sampling/official_sampling_runbook.md"
CONTACTABILITY_PROCEDURE = REPO_ROOT / "preregistration/post_registration/procedures/owner_contactability_procedure_v1.0.md"
TRAINER = REPO_ROOT / "preregistration/package/05_training_and_pilot/DEA_trainer_handout_v2.docx"
CODER = REPO_ROOT / "preregistration/package/05_training_and_pilot/DEA_coder_training_handout_v3.docx"
PILOT_REFERENCE = REPO_ROOT / "preregistration/package/05_training_and_pilot/DEA_pilot_projects_trainer_debrief_reference_v2.docx"
OWNER_FRAME_CODE = REPO_ROOT / "analysis/validation/owner_sampling_frame.py"
INSTITUTION_CODE = REPO_ROOT / "dashboard/institution_normalisation.py"
TRAINING_VERIFY_CODE = REPO_ROOT / "scripts/verify_training_exclusion_membership.py"

RESTRICTED_OUTPUT = REPO_ROOT / "preregistration_restricted/owner_candidate_frame_8a/owner_candidate_frame_restricted.csv"
INCIDENCE_OUTPUT = REPO_ROOT / "preregistration/post_registration/owner_candidate_frame_8a/owner_candidate_incidence_deidentified.csv"

EXPECTED_HASHES = {
    POPULATION: "a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1",
    EXCLUSIONS: "cf36e6d34375d0e68bac31df8169207fc0602bc7291a64e995b9cd86141413a6",
    BASELINE_RESERVE: "a30f9bc24ba8328b694a43fc7063b2a012dae2bcfe8dc65bfa60fd37b1f3171b",
    HARD_RESERVE: "8409f51c55cd572d6c6837ef59b666f3a712f2a67a7086489cec7f93bfd64c4b",
    SAMPLING_METADATA: "861e63b963b64037c1db74663ae32f3e24d9e5e283c2584b62ecc05dc86d8d3c",
    SAMPLING_ASSERTIONS: "a2d78e74d1d5fd91b37f86395863de8dbd41e1d3207641562f9c6930c084de4d",
    PROTOCOL: "fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77",
    SAMPLING_SPECIFICATION: "d926d4911f626a72ceab71f2ed37879dbe960f100bf2d5c075812617b63ef63b",
    SAMPLING_RUNBOOK: "9a06fd1dfb09b8ebea7381db14361fcd74318737af3df6a893ce2fd255e3728b",
    CONTACTABILITY_PROCEDURE: "2c57258812eeff84e09fef62539460dfb896503ef667208c340f487170a00793",
    TRAINER: "8b030a48c8b482d50fa4cede3a50e2c47b83d7866f836ca113e5ebeff30cf9d0",
    CODER: "7a351641de997f78374082538285a3d6dd589c6d8fb0928bb4c6725b49c173b5",
    PILOT_REFERENCE: "47707df5d3a52eed4b326aa50d2c4d21d005390162e5d9694d3626b913465cfa",
    OWNER_FRAME_CODE: "06fe96265f1d613374788a2366c3f50bae8c9c33a8ba847f6e480571a255338b",
    INSTITUTION_CODE: "583e3b6d35342693f2bb484b3f3d74dcaef07eea77cbc5d9e20654a44cdeef91",
    TRAINING_VERIFY_CODE: "1ce1bf1c49ddf8e3ce6f385e8999276601ec0925f6bef29aa4de3dc12067748d",
}

REGISTERED_TIE_BREAK = (
    "marginal eligible Record-ID gain descending; total eligible Record-ID "
    "count descending; conservative identity key ascending"
)
KEY_RULE = (
    "CAND_ + first 20 lowercase hexadecimal characters of SHA-256(" 
    "UTF-8 'owner_candidate_frame_v1\\0' + conservative identity key); "
    "independent of conditional-greedy position"
)
PLANNING_WARNING = (
    "COUNTERFACTUAL UNIVERSAL-CONTACTABILITY PLANNING ONLY. This is not a fixed "
    "or authorised search order. In Instruction 8B, after every disposition, "
    "the next candidate must be recomputed before any further search."
)
BURDEN_THRESHOLD = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_input_hashes() -> dict[str, str]:
    actual: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            raise ValueError(f"Required archived input is missing: {path.relative_to(REPO_ROOT)}")
        value = sha256(path)
        if value != expected:
            raise ValueError(f"Archived input hash differs: {path.relative_to(REPO_ROOT)}")
        actual[path.relative_to(REPO_ROOT).as_posix()] = value
    return actual


def candidate_key(identity_key: str) -> str:
    material = ("owner_candidate_frame_v1\0" + identity_key).encode("utf-8")
    return "CAND_" + hashlib.sha256(material).hexdigest()[:20]


def join_values(values: Iterable[object]) -> str:
    cleaned = {str(value).strip() for value in values if str(value).strip()}
    return "; ".join(sorted(cleaned, key=lambda value: (value.casefold(), value)))


def exact_membership_join(
    population: pd.DataFrame, ids: pd.DataFrame, marker: str
) -> pd.Series:
    right = ids.rename(columns={ids.columns[0]: "Record ID"}).copy()
    if right["Record ID"].isna().any() or right["Record ID"].str.strip().eq("").any():
        raise ValueError(f"{marker} join key contains a blank value")
    if right["Record ID"].duplicated().any():
        raise ValueError(f"{marker} join key is not unique")
    joined = population[["Record ID"]].merge(
        right.assign(**{marker: 1}), on="Record ID", how="left",
        validate="one_to_one", sort=False,
    )
    if len(joined) != len(population):
        raise ValueError(f"{marker} join changed population row count")
    matched = joined[marker].eq(1)
    if int(matched.sum()) != len(right):
        raise ValueError(f"{marker} join did not match every archived exclusion row")
    return matched


def build_parsed_frame(eligible: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    incidences: list[dict[str, object]] = []
    reviews: list[dict[str, object]] = []
    for record in eligible[["Record ID", "Project ID", "Title", "Researchers"]].to_dict("records"):
        parsed, record_reviews = parse_researcher_field(record.get("Researchers"))
        for person in parsed:
            incidences.append({
                "record_id": str(record["Record ID"]),
                "project_id": str(record["Project ID"]),
                "researcher_displayed": person.displayed,
                "researcher_normalised": person.normalised,
                "researcher_identity_key": person.identity_key,
                "entity_status": person.entity_status,
                "entity_status_reason": person.entity_status_reason,
                "eligible_as_index_researcher": int(person.entity_status == "person_candidate"),
            })
        for item in record_reviews:
            reviews.append({
                "record_id": str(record["Record ID"]),
                "project_id": str(record["Project ID"]),
                "review_reason": item["reason"],
                "review_details": item["details"],
                "automatic_action": "No fuzzy merge or external resolution; conservative parser result retained.",
            })
    frame = pd.DataFrame(incidences)
    if frame.empty:
        raise ValueError("No researcher incidences were parsed")
    frame = resolve_frame_entity_statuses(frame)
    frame = frame.drop_duplicates(["researcher_identity_key", "record_id"]).reset_index(drop=True)
    return frame, pd.DataFrame(reviews)


def portfolios_from(frame: pd.DataFrame) -> dict[str, frozenset[str]]:
    people = frame.loc[frame["entity_status"].eq("person_candidate")]
    return {
        key: frozenset(group["record_id"].astype(str))
        for key, group in people.groupby("researcher_identity_key", sort=True)
    }


def greedy_sequence(portfolios: Mapping[str, frozenset[str]]) -> pd.DataFrame:
    remaining = set(portfolios)
    covered: set[str] = set()
    rows: list[dict[str, object]] = []
    while remaining:
        marginal = {key: len(portfolios[key] - covered) for key in remaining}
        maximum = max(marginal.values())
        primary = {key for key in remaining if marginal[key] == maximum}
        maximum_total = max(len(portfolios[key]) for key in primary)
        secondary = {key for key in primary if len(portfolios[key]) == maximum_total}
        chosen = min(secondary)
        if len(primary) == 1:
            applied = "none"
        elif len(secondary) == 1:
            applied = "total_eligible_record_count_desc"
        else:
            applied = "total_eligible_record_count_desc_then_conservative_identity_key_asc"
        new_records = portfolios[chosen] - covered
        covered.update(portfolios[chosen])
        remaining.remove(chosen)
        remaining_maximum = max(
            (len(portfolios[key] - covered) for key in remaining), default=0
        )
        rows.append({
            "researcher_identity_key": chosen,
            "conditional_sequence_step": len(rows) + 1,
            "conditional_marginal_coverage": len(new_records),
            "conditional_cumulative_coverage": len(covered),
            "registered_tie_break_rule": REGISTERED_TIE_BREAK,
            "tie_break_applied": applied,
            "primary_tie_size": len(primary),
            "secondary_tie_size": len(secondary),
            "maximum_remaining_marginal_after_step": remaining_maximum,
        })
    return pd.DataFrame(rows)


def possible_variants(
    names: Mapping[str, str], portfolios: Mapping[str, frozenset[str]]
) -> dict[str, list[str]]:
    keys = sorted(names)
    variants: dict[str, list[str]] = defaultdict(list)
    for left_index, left in enumerate(keys):
        for right in keys[left_index + 1:]:
            if _possible_variant(names[left], names[right]):
                variants[left].append(right)
                variants[right].append(left)
    return variants


def assert_no_leading_variant_ambiguity(
    names: Mapping[str, str], portfolios: Mapping[str, frozenset[str]],
    sequence: pd.DataFrame, variants: Mapping[str, list[str]],
) -> None:
    leading = set(sequence.head(25)["researcher_identity_key"])
    leading_floor = int(sequence.head(25)["conditional_marginal_coverage"].min())
    checked_pairs: set[tuple[str, str]] = set()
    capable: list[tuple[str, str]] = []
    for left, others in variants.items():
        for right in others:
            pair = tuple(sorted((left, right)))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            if left in leading or right in leading:
                capable.append(pair)
                continue
            merged_records = portfolios[left] | portfolios[right]
            if len(merged_records) < leading_floor:
                # Marginal gain can never exceed total portfolio size, so this
                # pair cannot displace any member of the observed prefix.
                continue
            merged_key = min(pair) + "\0merged-variant-diagnostic"
            alternative = {
                key: records for key, records in portfolios.items() if key not in pair
            }
            alternative[merged_key] = merged_records
            remaining = set(alternative)
            covered: set[str] = set()
            merged_position: int | None = None
            for position in range(1, 26):
                chosen = min(
                    remaining,
                    key=lambda key: (
                        -len(alternative[key] - covered),
                        -len(alternative[key]),
                        key,
                    ),
                )
                if chosen == merged_key:
                    merged_position = position
                    break
                covered.update(alternative[chosen])
                remaining.remove(chosen)
            if merged_position is not None:
                capable.append(pair)
    if capable:
        labels = [f"{names[left]} / {names[right]}" for left, right in capable]
        raise ValueError(
            "Unresolved possible-name variants could affect the first 25 conditional "
            "greedy positions: " + "; ".join(labels)
        )


def candidate_rows(
    frame: pd.DataFrame, reviews: pd.DataFrame, portfolios: Mapping[str, frozenset[str]],
    sequence: pd.DataFrame, variants: Mapping[str, list[str]],
) -> pd.DataFrame:
    sequence_map = sequence.set_index("researcher_identity_key").to_dict("index")
    names = {
        key: sorted(
            set(group["researcher_normalised"]),
            key=lambda value: (str(value).casefold(), str(value)),
        )[0]
        for key, group in frame.loc[frame["entity_status"].eq("person_candidate")]
        .groupby("researcher_identity_key", sort=True)
    }
    rows: list[dict[str, object]] = []
    for identity_key in sorted(portfolios):
        group = frame.loc[frame["researcher_identity_key"].eq(identity_key)]
        sequence_values = sequence_map[identity_key]
        variant_names = [names[key] for key in variants.get(identity_key, [])]
        count = len(portfolios[identity_key])
        step = int(sequence_values["conditional_sequence_step"])
        rows.append({
            "frame_row_type": "candidate",
            "candidate_key": candidate_key(identity_key),
            "canonical_person_name": names[identity_key],
            "eligibility_status": "ELIGIBLE_NAMED_PERSON",
            "entity_status": "person_candidate",
            "parsing_and_identity_resolution_evidence": (
                "Exact conservative identity after Unicode typography, punctuation, separator, "
                "and whitespace normalisation; exact within-record duplicates removed; no fuzzy "
                "merge or external resolution. Observed forms: "
                + join_values(group["researcher_displayed"])
                + (". Possible variants kept separate: " + join_values(variant_names) if variant_names else ". No possible variant flagged.")
            ),
            "conservative_exclusion_reason": "",
            "associated_eligible_record_count": count,
            "associated_eligible_record_ids": join_values(portfolios[identity_key]),
            "potential_review_incidence_count": count,
            "burden_diagnostic": f"HIGH_COUNT_GE_{BURDEN_THRESHOLD}" if count >= BURDEN_THRESHOLD else "",
            "conditional_sequence_step": step,
            "conditional_marginal_coverage": sequence_values["conditional_marginal_coverage"],
            "conditional_cumulative_coverage": sequence_values["conditional_cumulative_coverage"],
            "maximum_remaining_marginal_after_step": sequence_values["maximum_remaining_marginal_after_step"],
            "registered_tie_break_rule": sequence_values["registered_tie_break_rule"],
            "tie_break_applied": sequence_values["tie_break_applied"],
            "primary_tie_size": sequence_values["primary_tie_size"],
            "secondary_tie_size": sequence_values["secondary_tie_size"],
            "candidate_key_generation_rule": KEY_RULE,
            "conditional_universal_contactability_planning_only": 1,
            "next_assessment_status": "KNOWN_NEXT_ONLY" if step == 1 else "CONDITIONAL_RECOMPUTE_IN_8B",
            "disposition": "",
            "source_reached_or_succeeded": "",
            "url": "",
            "search_date": "",
            "elapsed_minutes": "",
            "note": "",
            "planning_warning": PLANNING_WARNING,
        })

    excluded = frame.loc[~frame["entity_status"].eq("person_candidate")]
    for identity_key, group in excluded.groupby("researcher_identity_key", sort=True):
        statuses = join_values(group["entity_status"])
        reasons = join_values(group["entity_status_reason"])
        rows.append({
            "frame_row_type": "conservative_exclusion",
            "candidate_key": "",
            "canonical_person_name": sorted(set(group["researcher_normalised"]), key=str.casefold)[0],
            "eligibility_status": "EXCLUDED_BEFORE_SEQUENCING",
            "entity_status": statuses,
            "parsing_and_identity_resolution_evidence": "Conservative parser classification; no external resolution performed.",
            "conservative_exclusion_reason": reasons,
            "associated_eligible_record_count": group["record_id"].nunique(),
            "associated_eligible_record_ids": join_values(group["record_id"]),
            "planning_warning": PLANNING_WARNING,
        })

    exclusion_review_reasons = {
        "empty_or_malformed_researcher_field", "unparsed_logical_line", "no_person_name_parsed"
    }
    for item in reviews.loc[reviews["review_reason"].isin(exclusion_review_reasons)].to_dict("records"):
        rows.append({
            "frame_row_type": "conservative_exclusion",
            "candidate_key": "",
            "canonical_person_name": normalise_researcher_name(item["review_details"]),
            "eligibility_status": "EXCLUDED_BEFORE_SEQUENCING",
            "entity_status": "unresolved_or_unparsed_identity",
            "parsing_and_identity_resolution_evidence": item["automatic_action"],
            "conservative_exclusion_reason": f"{item['review_reason']}: {item['review_details']}",
            "associated_eligible_record_count": 1,
            "associated_eligible_record_ids": item["record_id"],
            "planning_warning": PLANNING_WARNING,
        })
    output = pd.DataFrame(rows)
    candidate_mask = output["frame_row_type"].eq("candidate")
    output.loc[candidate_mask] = output.loc[candidate_mask].sort_values(
        "conditional_sequence_step", kind="stable"
    ).values
    return output


def incidence_rows(
    frame: pd.DataFrame, portfolios: Mapping[str, frozenset[str]]
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for identity_key in sorted(portfolios):
        key = candidate_key(identity_key)
        count = len(portfolios[identity_key])
        for record_id in sorted(portfolios[identity_key]):
            rows.append({
                "candidate_key": key,
                "eligible_record_id": record_id,
                "incidence_type": "NAMED_PERSON_ON_ELIGIBLE_RECORD",
                "potential_review_status": "POTENTIAL_NOT_PRODUCTION_ASSIGNMENT",
                "candidate_eligible_record_count": count,
                "burden_diagnostic": f"HIGH_COUNT_GE_{BURDEN_THRESHOLD}" if count >= BURDEN_THRESHOLD else "",
            })
    return pd.DataFrame(rows).sort_values(
        ["candidate_key", "eligible_record_id"], kind="stable"
    ).reset_index(drop=True)


def assert_outputs(
    restricted: pd.DataFrame, incidence: pd.DataFrame,
    portfolios: Mapping[str, frozenset[str]], eligible_ids: set[str],
    sequence: pd.DataFrame,
) -> None:
    candidates = restricted.loc[restricted["frame_row_type"].eq("candidate")]
    if candidates["candidate_key"].duplicated().any() or candidates["candidate_key"].eq("").any():
        raise ValueError("candidate_key is blank or duplicated")
    if set(incidence["candidate_key"]) != set(candidates["candidate_key"]):
        raise ValueError("Restricted and incidence candidate keys do not reconcile")
    expected_incidences = sum(len(records) for records in portfolios.values())
    if len(incidence) != expected_incidences or incidence.duplicated(["candidate_key", "eligible_record_id"]).any():
        raise ValueError("Eligible person--record incidences do not reconcile")
    if not set(incidence["eligible_record_id"]) <= eligible_ids:
        raise ValueError("Incidence output contains an ineligible Record ID")
    forbidden_columns = re.compile(r"name|email|affiliation|institution|contact|phone|address", re.I)
    prohibited = [column for column in incidence if forbidden_columns.search(column)]
    if prohibited:
        raise ValueError(f"De-identified incidence has prohibited columns: {prohibited}")
    direct_names = set(candidates["canonical_person_name"].astype(str))
    incidence_values = set(incidence.astype(str).stack())
    if direct_names & incidence_values:
        raise ValueError("A canonical person name entered the de-identified incidence output")
    cumulative = sequence["conditional_cumulative_coverage"].astype(int)
    if not cumulative.is_monotonic_increasing:
        raise ValueError("Conditional coverage curve is not monotonic")
    if int(cumulative.iloc[-1]) != len(set(incidence["eligible_record_id"])):
        raise ValueError("Conditional coverage does not end at the coverable-record union")
    if restricted["disposition"].fillna("").ne("").any():
        raise ValueError("A contactability disposition was populated during 8A")
    if any("owner_id" in column or "assignment_id" in column for column in restricted.columns):
        raise ValueError("A production identifier column was generated")


def first_position(sequence: pd.DataFrame, target: int) -> int | None:
    reached = sequence.loc[sequence["conditional_cumulative_coverage"].ge(target)]
    return int(reached.iloc[0]["conditional_sequence_step"]) if len(reached) else None


def distribution(values: Iterable[int]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(Counter(values).items())}


def build() -> dict[str, object]:
    input_hashes = verify_input_hashes()
    training = verify_membership(TRAINER, CODER, PILOT_REFERENCE, EXCLUSIONS, POPULATION)
    if training["counts"] != {
        "keyed_worked_examples": 11, "unkeyed_discussion": 1,
        "pilot": 10, "total_unique": 22,
    }:
        raise ValueError("Training/pilot source verification counts differ")

    metadata = json.loads(SAMPLING_METADATA.read_text(encoding="utf-8"))
    assertions = json.loads(SAMPLING_ASSERTIONS.read_text(encoding="utf-8"))
    if not assertions or not all(assertions.values()):
        raise ValueError("An archived official-draw assertion is false")
    if metadata["output_hashes"]["baseline_reserve.csv"] != EXPECTED_HASHES[BASELINE_RESERVE]:
        raise ValueError("Baseline reserve is not bound by sampling metadata")
    if metadata["output_hashes"]["hard_reserve.csv"] != EXPECTED_HASHES[HARD_RESERVE]:
        raise ValueError("Hard reserve is not bound by sampling metadata")

    contactability_text = CONTACTABILITY_PROCEDURE.read_text(encoding="utf-8")
    for code in ("CONTACTABLE", "NOT_FOUND", "UNRESOLVED", "INELIGIBLE"):
        if f"`{code}`" not in contactability_text:
            raise ValueError(f"Contactability disposition is missing: {code}")
    if "Ten minutes per candidate" not in contactability_text:
        raise ValueError("Contactability effort ceiling differs")

    population = pd.read_csv(
        POPULATION, encoding="utf-8-sig", dtype=str,
        usecols=["Record ID", "Project ID", "Title", "Researchers"],
    ).fillna("")
    if len(population) != 1308 or population["Record ID"].nunique() != 1308:
        raise ValueError("Frozen population is not exactly 1,308 unique Record IDs")
    if population["Project ID"].nunique() != 1304:
        raise ValueError("Frozen population is not exactly 1,304 unique Project IDs")

    exclusions = pd.read_csv(EXCLUSIONS, encoding="utf-8-sig", dtype=str, usecols=["record_id"])
    baseline_reserve = pd.read_csv(
        BASELINE_RESERVE, encoding="utf-8-sig", dtype=str, usecols=["record_id"]
    )
    hard_reserve = pd.read_csv(
        HARD_RESERVE, encoding="utf-8-sig", dtype=str, usecols=["record_id"]
    )
    training_mask = exact_membership_join(population, exclusions, "in_training_pilot")
    reserve_ids = pd.concat([baseline_reserve, hard_reserve], ignore_index=True)
    if len(baseline_reserve) != 100 or len(hard_reserve) != 50 or reserve_ids["record_id"].duplicated().any():
        raise ValueError("Archived reserve row counts or cross-file uniqueness differ")
    reserve_mask = exact_membership_join(population, reserve_ids, "in_scratch_reserve")
    if (training_mask & reserve_mask).any():
        raise ValueError("Training/pilot and scratch-reserve exclusions overlap")
    eligible = population.loc[~training_mask & ~reserve_mask].copy()
    registered_after_training = int(metadata["eligible_population_count"])
    registered_after_reserve = registered_after_training - len(reserve_ids)
    discrepancy = len(eligible) - registered_after_reserve

    frame, reviews = build_parsed_frame(eligible)
    portfolios = portfolios_from(frame)
    sequence = greedy_sequence(portfolios)
    names = {
        key: sorted(set(group["researcher_normalised"]), key=str.casefold)[0]
        for key, group in frame.loc[frame["entity_status"].eq("person_candidate")]
        .groupby("researcher_identity_key", sort=True)
    }
    variants = possible_variants(names, portfolios)
    assert_no_leading_variant_ambiguity(names, portfolios, sequence, variants)

    restricted = candidate_rows(frame, reviews, portfolios, sequence, variants)
    incidence = incidence_rows(frame, portfolios)
    eligible_ids = set(eligible["Record ID"])
    assert_outputs(restricted, incidence, portfolios, eligible_ids, sequence)

    RESTRICTED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    INCIDENCE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    restricted.to_csv(RESTRICTED_OUTPUT, index=False, encoding="utf-8-sig", lineterminator="\n")
    incidence.to_csv(INCIDENCE_OUTPUT, index=False, encoding="utf-8-sig", lineterminator="\n")

    marginal = sequence["conditional_marginal_coverage"].astype(int)
    at_most_one = sequence.loc[sequence["maximum_remaining_marginal_after_step"].le(1)]
    candidates = restricted.loc[restricted["frame_row_type"].eq("candidate")]
    excluded = restricted.loc[restricted["frame_row_type"].eq("conservative_exclusion")]
    entity_counts = (
        excluded["entity_status"].value_counts().sort_index().astype(int).to_dict()
    )
    counts = [len(records) for records in portfolios.values()]
    summary = {
        "outputs": {
            RESTRICTED_OUTPUT.relative_to(REPO_ROOT).as_posix(): sha256(RESTRICTED_OUTPUT),
            INCIDENCE_OUTPUT.relative_to(REPO_ROOT).as_posix(): sha256(INCIDENCE_OUTPUT),
        },
        "inputs": input_hashes,
        "population": {
            "starting_record_ids": len(population),
            "starting_project_ids": population["Project ID"].nunique(),
            "training_pilot_exclusions": int(training_mask.sum()),
            "reserve_exclusions": int(reserve_mask.sum()),
            "eligible_record_ids": len(eligible),
            "registered_after_training": registered_after_training,
            "registered_after_reserve_arithmetic": registered_after_reserve,
            "registered_reconciliation_discrepancy": discrepancy,
        },
        "three_populations": {
            "eligible_record_ids": len(eligible_ids),
            "eligible_named_person_record_incidences": len(incidence),
            "eligible_named_people": len(candidates),
            "coverable_record_ids": incidence["eligible_record_id"].nunique(),
            "eligible_records_without_usable_candidate": len(eligible_ids) - incidence["eligible_record_id"].nunique(),
        },
        "conservative_exclusions": {
            "rows_in_restricted_audit": len(excluded),
            "entity_status_distribution": entity_counts,
            "parse_review_reason_distribution": reviews["review_reason"].value_counts().sort_index().astype(int).to_dict(),
        },
        "conditional_greedy_universal_contactability": {
            "candidate_positions": len(sequence),
            "marginal_coverage_distribution": distribution(marginal),
            "first_step_after_which_all_remaining_gain_at_most_one": int(at_most_one.iloc[0]["conditional_sequence_step"]),
            "coverage_feasibility_position_25": first_position(sequence, 25),
            "coverage_feasibility_position_50": first_position(sequence, 50),
            "final_coverable_records": int(sequence.iloc[-1]["conditional_cumulative_coverage"]),
            "tie_break_applied_distribution": sequence["tie_break_applied"].value_counts().sort_index().astype(int).to_dict(),
        },
        "potential_review_incidences": {
            "per_candidate_count_distribution": distribution(counts),
            "high_count_threshold": BURDEN_THRESHOLD,
            "high_count_candidates": sum(value >= BURDEN_THRESHOLD for value in counts),
            "maximum": max(counts),
        },
        "worklist": {
            "rows": len(candidates),
            "ceiling_minutes_all_conditional_rows": len(candidates) * 10,
            "ceiling_minutes_maximum_25_sequence_positions": min(25, len(candidates)) * 10,
            "only_position_1_is_next": True,
        },
        "assertions": {
            "training_membership_verified_from_archived_sources": True,
            "reserve_exact_join_before_researcher_parsing": True,
            "reserve_ids_not_printed_enumerated_sampled_or_logged": True,
            "no_post_preregistration_population_read": True,
            "no_prohibited_selection_attribute_read": True,
            "reproducible_deterministic_build": True,
            "coverage_curve_monotonic": True,
            "no_contactability_search": True,
            "no_production_identifier_generated": True,
            "incidence_has_no_direct_identity_or_contact_fields": True,
            "nothing_frozen_or_contacted": True,
        },
    }
    return summary


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
