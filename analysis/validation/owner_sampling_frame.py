"""Restricted researcher--project profiling for owner-sampling design.

Descriptive only: no cohort selection, model-label ranking, REDCap access,
external identity resolution, or contact details. Name-bearing outputs must be
written below ``preregistration_restricted/owner_sampling_exploration``.
"""

from __future__ import annotations

import argparse
import itertools
import re
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.register_cleaning import load_clean_register
from dashboard.institution_normalisation import (
    _ALIASES,
    _build_logical_lines,
    _clean_fragment,
    _clean_text,
    _starts_name,
    parse_institutions_with_metadata,
)

REPO_ROOT = PROJECT_ROOT
FROZEN_POPULATION = REPO_ROOT / "preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv"
EXCLUSIONS = REPO_ROOT / "preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv"
PROPERTIES = REPO_ROOT / "analysis/outputs_deterministic_rc2/register_properties.csv"
DEFAULT_OUTPUT = REPO_ROOT / "preregistration_restricted/owner_sampling_exploration"
EXPECTED_RECORDS = 1308
EXPECTED_PROJECT_IDS = 1304
MAJOR_COLLECTION_MIN_RECORDS = 10
UCL_INSTITUTIONS = frozenset({"University College London (UCL)", "UCL Institute of Education"})
THRESHOLDS = (25, 50, 75, 100, 125, 150, 200)
PREFIXES = (1, 5, 7, 10, 15, 20, 25, 30)
FORBIDDEN_CONTACT_TERMS = frozenset({"email", "e-mail", "phone", "telephone", "address", "contact"})

_ZERO_WIDTH = re.compile(r"[\u00ad\u200b\u200c\u200d\ufeff]")
_SPACE = re.compile(r"\s+")
_INSTITUTION_WORD = re.compile(
    r"\b(?:university|institute|college|school|department|centre|center|office|council|trust|service|bank|government|agency|databank)\b",
    re.I,
)
_ORGANISATION_SUFFIX = re.compile(
    r"\b(?:ltd|limited|llp|plc|inc|incorporated|corp|corporation|company|co|foundation|consortium|partnership|association|society|group|team)\.?$",
    re.I,
)
_DASHES = str.maketrans({c: "-" for c in "‐‑‒–—―−"})
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'"})


@dataclass(frozen=True)
class ParsedResearcher:
    displayed: str
    normalised: str
    identity_key: str
    entity_status: str
    entity_status_reason: str


def normalise_researcher_name(value: str) -> str:
    """Conservatively normalise typography, punctuation and whitespace."""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.translate(_DASHES).translate(_APOSTROPHES)
    text = _ZERO_WIDTH.sub("", text)
    return _SPACE.sub(" ", text).strip(" \t\r\n,;")


def researcher_identity_key(value: str) -> str:
    return normalise_researcher_name(value).casefold()


def reviewed_institution_names(
    aliases: Mapping[str, str] | None = None,
) -> tuple[frozenset[str], frozenset[str]]:
    source = _ALIASES if aliases is None else aliases
    alias_keys = frozenset(normalise_researcher_name(value).casefold() for value in source)
    canonical = frozenset(
        normalise_researcher_name(value).casefold() for value in source.values() if value
    )
    return alias_keys, canonical


def classify_entity(
    value: str,
    *,
    reviewed_aliases: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Classify conservatively; reviewed institution matches take precedence."""
    normalised = normalise_researcher_name(value)
    key = normalised.casefold()
    aliases, canonical = reviewed_institution_names(reviewed_aliases)
    if key in aliases:
        return "organisation_exact_match", "Exact reviewed institution alias match."
    if key in canonical:
        return "organisation_exact_match", "Exact reviewed canonical institution match."
    if _ORGANISATION_SUFFIX.search(normalised):
        return "organisation_pattern_match", "Unambiguous organisation suffix or collective construction."
    if _INSTITUTION_WORD.search(normalised):
        return "organisation_pattern_match", "Unambiguous institutional construction."
    if any(character.isdigit() for character in normalised):
        return "ambiguous_entity", "Contains digits and cannot be conservatively treated as a person."
    letters = [character for character in normalised if character.isalpha()]
    if letters and all(character.isupper() for character in letters):
        return "ambiguous_entity", "All-uppercase person-shaped string without a reviewed entity match."
    if len(normalised.split()) < 2:
        return "ambiguous_entity", "Single-token identity cannot be conservatively classified as a person."
    return "person_candidate", "Accepted by reviewed person-name syntax with no organisation evidence."


def parse_researcher_field(value: object) -> tuple[tuple[ParsedResearcher, ...], tuple[dict[str, str], ...]]:
    """Use reviewed logical-line/name rules; never merge similar names."""
    reviews: list[dict[str, str]] = []
    if not isinstance(value, str) or not value.strip():
        return (), ({"reason": "empty_or_malformed_researcher_field", "details": "No non-empty text."},)
    raw = value
    if ";" in raw:
        reviews.append({"reason": "ambiguous_separator", "details": "Semicolon treated as a record separator."})
    if re.search(r"\s+(?:and|&)\s+", raw, re.I) and "," not in raw and "\n" not in raw:
        reviews.append({"reason": "ambiguous_separator", "details": "Unsplit conjunction may join people or organisations."})
    text = _clean_text(raw.replace(";", "\n"))
    parsed: list[ParsedResearcher] = []
    seen: set[str] = set()
    duplicate_count = 0
    for line in _build_logical_lines(text):
        tokens = [_clean_fragment(part) for part in line.split(",") if _clean_fragment(part)]
        found_on_line = False
        index = 0
        while index < len(tokens):
            consumed = _starts_name(tokens, index)
            if not consumed:
                index += 1
                continue
            found_on_line = True
            displayed = normalise_researcher_name(" ".join(tokens[index : index + consumed]))
            key = researcher_identity_key(displayed)
            if key in seen:
                duplicate_count += 1
            else:
                seen.add(key)
                status, status_reason = classify_entity(displayed)
                parsed.append(ParsedResearcher(displayed, displayed, key, status, status_reason))
                words = displayed.split()
                if len(displayed) < 4 or len(displayed) > 80 or len(words) < 2 or len(words) > 5:
                    reviews.append({"reason": "unusual_parsed_element_length", "details": displayed})
                if _INSTITUTION_WORD.search(displayed):
                    reviews.append({"reason": "suspected_organisation_text_in_name", "details": displayed})
            index += consumed
            while index < len(tokens) and not _starts_name(tokens, index):
                index += 1
        if tokens and not found_on_line:
            reviews.append({"reason": "unparsed_logical_line", "details": line})
            if len(tokens) == 1:
                displayed = normalise_researcher_name(tokens[0])
                status, status_reason = classify_entity(displayed)
                if status in {"organisation_exact_match", "organisation_pattern_match", "ambiguous_entity"}:
                    key = researcher_identity_key(displayed)
                    if key not in seen:
                        seen.add(key)
                        parsed.append(ParsedResearcher(displayed, displayed, key, status, status_reason))
    if duplicate_count:
        reviews.append({"reason": "exact_duplicate_name_removed", "details": f"Removed {duplicate_count} repeated occurrence(s)."})
    if len(parsed) > 25:
        reviews.append({
            "reason": "unusually_many_parsed_researchers",
            "details": f"Parsed {len(parsed)} distinct names; manual structure review required.",
        })
    if not any(identity.entity_status == "person_candidate" for identity in parsed):
        reviews.append({"reason": "no_person_name_parsed", "details": "Reviewed name rules found no person."})
    return tuple(parsed), tuple(reviews)


def validate_population(population: pd.DataFrame) -> None:
    required = {"Record ID", "Project ID", "Title", "Researchers", "Year", "Datasets Used"}
    missing = required - set(population.columns)
    if missing:
        raise ValueError(f"Cleaned population is missing columns: {sorted(missing)}")
    if len(population) != EXPECTED_RECORDS:
        raise ValueError(f"Expected exactly {EXPECTED_RECORDS} records; found {len(population)}")
    if population["Record ID"].isna().any() or population["Record ID"].astype(str).str.strip().eq("").any():
        raise ValueError("Record ID is missing or blank")
    if population["Record ID"].astype(str).nunique() != EXPECTED_RECORDS:
        raise ValueError("Record IDs are not unique across the 1,308-record population")
    if population["Project ID"].astype(str).nunique() != EXPECTED_PROJECT_IDS:
        raise ValueError(f"Expected {EXPECTED_PROJECT_IDS} unique Project IDs")


def reconstruct_canonical_population() -> pd.DataFrame:
    """Rebuild in a temporary directory and require exact frozen agreement."""
    with tempfile.TemporaryDirectory(prefix="owner-frame-clean-") as output_dir:
        rebuilt, _, source = load_clean_register(
            str(REPO_ROOT / "data"), candidate_files=["dea_accredited_projects_20260601.csv"],
            output_dir=output_dir, verbose=False,
        )
    if source != "dea_accredited_projects_20260601.csv":
        raise ValueError(f"Unexpected source register: {source}")
    frozen = pd.read_csv(FROZEN_POPULATION, encoding="utf-8-sig", dtype={"Record ID": "string", "Project ID": "string"})
    validate_population(rebuilt)
    validate_population(frozen)
    columns = ["Record ID", "Project ID", "Title", "Researchers", "Datasets Used"]
    left = rebuilt[columns].fillna("").astype(str).sort_values("Record ID").reset_index(drop=True)
    right = frozen[columns].fillna("").astype(str).sort_values("Record ID").reset_index(drop=True)
    if not left.equals(right):
        raise ValueError("Rebuilt population does not exactly match the frozen 1,308-record frame")
    return rebuilt


def load_exclusion_ids(path: Path = EXCLUSIONS) -> frozenset[str]:
    frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    values = frozenset(frame["record_id"].str.strip())
    if len(values) != 22:
        raise ValueError(f"Expected exactly 22 training/pilot exclusions; found {len(values)}")
    return values


def _join(values: Iterable[str]) -> str:
    cleaned = {str(value).strip() for value in values if str(value).strip()}
    return "; ".join(sorted(cleaned, key=lambda value: (value.casefold(), value)))


def _collection_values(value: object) -> frozenset[str]:
    if not isinstance(value, str) or not value.strip():
        return frozenset()
    return frozenset(part.strip() for part in value.split(";") if part.strip())


def build_researcher_record_frame(
    population: pd.DataFrame,
    exclusion_ids: frozenset[str],
    properties: pd.DataFrame,
    institutions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the name-bearing relationship frame and initial review queue."""
    property_map = properties.set_index("Record ID").to_dict("index")
    institution_map = (
        institutions.groupby("Record ID", sort=False)["institution"]
        .apply(lambda values: tuple(sorted(set(values), key=str.casefold))).to_dict()
        if len(institutions) else {}
    )
    rows: list[dict[str, object]] = []
    review_rows: list[dict[str, object]] = []
    for record in population.to_dict("records"):
        record_id = str(record["Record ID"])
        names, reviews = parse_researcher_field(record.get("Researchers"))
        institutions_on_record = tuple(institution_map.get(record_id, ()))
        if any(value in UCL_INSTITUTIONS for value in institutions_on_record):
            ucl_status = "Yes"
        elif institutions_on_record:
            ucl_status = "No"
        else:
            ucl_status = "Unknown"
        props = property_map.get(record_id, {})
        for name in names:
            rows.append({
                "record_id": record_id,
                "project_id": str(record["Project ID"]),
                "project_title": str(record["Title"]),
                "researchers_original": "" if pd.isna(record.get("Researchers")) else str(record.get("Researchers")),
                "researcher_displayed": name.displayed,
                "researcher_normalised": name.normalised,
                "researcher_identity_key": name.identity_key,
                "entity_status": name.entity_status,
                "entity_status_reason": name.entity_status_reason,
                "eligible_as_index_researcher": int(name.entity_status == "person_candidate"),
                "reviewed_institutions_on_record": _join(institutions_on_record),
                "reviewed_institution_count_on_record": len(institutions_on_record),
                "ucl_linked_on_record": ucl_status,
                "record_year": int(record["Year"]) if not pd.isna(record["Year"]) else "",
                "record_linkage": props.get("record_linkage", ""),
                "matched_linked_collections": props.get("matched_products", ""),
                "dataset_collection_methods": props.get("dataset_collection_methods", ""),
                "dataset_temporal_structures": props.get("dataset_temporal_structures", ""),
                "dataset_units": props.get("dataset_units", ""),
                "researcher_sectors_on_record": props.get("researcher_sectors", ""),
                "in_full_cleaned_population": 1,
                "in_training_pilot_exclusion_set": int(record_id in exclusion_ids),
                "provisional_base_owner_eligible": int(record_id not in exclusion_ids),
                "owner_review_record_eligibility": int(record_id not in exclusion_ids),
                "future_reserve_removal_pending": 1,
            })
        for review in reviews:
            review_rows.append({
                "record_id": record_id,
                "project_id": str(record["Project ID"]),
                "project_title": str(record["Title"]),
                "researchers_original": "" if pd.isna(record.get("Researchers")) else str(record.get("Researchers")),
                "researcher_displayed": "",
                "researcher_normalised": "",
                "review_reason": review["reason"],
                "review_details": review["details"],
                "automatic_action": "Flag only; no fuzzy merge or external resolution.",
            })
    return pd.DataFrame(rows), pd.DataFrame(review_rows)


def resolve_frame_entity_statuses(frame: pd.DataFrame) -> pd.DataFrame:
    """Make exact conservative identity keys internally status-consistent."""
    precedence = {
        "organisation_exact_match": 0,
        "organisation_pattern_match": 1,
        "person_candidate": 2,
        "ambiguous_entity": 3,
    }
    out = frame.copy()
    for _, index in out.groupby("researcher_identity_key", sort=False).groups.items():
        statuses = set(out.loc[index, "entity_status"])
        chosen = min(statuses, key=lambda value: precedence[value])
        reasons = sorted(
            set(out.loc[index, "entity_status_reason"]), key=lambda value: (value.casefold(), value)
        )
        if chosen == "person_candidate" and "ambiguous_entity" in statuses:
            reason = "Ordinary person-form occurrence resolves a casing-only ambiguous occurrence for the same exact conservative key."
        else:
            reason = next(
                value for value in reasons
                if classify_entity(str(out.loc[index, "researcher_normalised"].iloc[0]))[0] == chosen
            ) if len(reasons) == 1 else "; ".join(reasons)
        out.loc[index, "entity_status"] = chosen
        out.loc[index, "entity_status_reason"] = reason
        out.loc[index, "eligible_as_index_researcher"] = int(chosen == "person_candidate")
    return out


def _variant_tokens(value: str) -> tuple[str, ...]:
    return tuple(
        re.sub(r"[^\w'-]", "", token, flags=re.UNICODE).casefold()
        for token in value.split() if token
    )


def _possible_variant(left: str, right: str) -> bool:
    a, b = _variant_tokens(left), _variant_tokens(right)
    if len(a) < 2 or len(b) < 2 or a[-1] != b[-1] or a == b:
        return False
    same_first = a[0] == b[0]
    initial_match = a[0][:1] == b[0][:1] and (len(a[0]) == 1 or len(b[0]) == 1)
    return same_first or initial_match


def add_variant_reviews(frame: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    representatives = frame.drop_duplicates("researcher_identity_key")
    by_signature: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in representatives.to_dict("records"):
        tokens = _variant_tokens(str(row["researcher_normalised"]))
        if len(tokens) >= 2:
            by_signature[(tokens[-1], tokens[0][:1])].append(row)
    additions: list[dict[str, object]] = []
    for candidates in by_signature.values():
        for left, right in itertools.combinations(candidates, 2):
            if not _possible_variant(str(left["researcher_normalised"]), str(right["researcher_normalised"])):
                continue
            for current, other in ((left, right), (right, left)):
                additions.append({
                    "record_id": current["record_id"],
                    "project_id": current["project_id"],
                    "project_title": current["project_title"],
                    "researchers_original": current["researchers_original"],
                    "researcher_displayed": current["researcher_displayed"],
                    "researcher_normalised": current["researcher_normalised"],
                    "review_reason": "possible_name_variant_not_merged",
                    "review_details": f"Kept separate from: {other['researcher_normalised']}",
                    "automatic_action": "Flag only; no fuzzy merge or external resolution.",
                })
    if additions:
        reviews = pd.concat([reviews, pd.DataFrame(additions)], ignore_index=True)
    columns = ["record_id", "project_id", "project_title", "researchers_original", "researcher_displayed", "researcher_normalised", "review_reason", "review_details", "automatic_action"]
    return (
        reviews.reindex(columns=columns).drop_duplicates()
        .sort_values(["review_reason", "record_id", "researcher_normalised"], kind="stable")
        .reset_index(drop=True)
    )


def build_researcher_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, tuple[str, ...]]:
    eligible = frame.loc[frame["provisional_base_owner_eligible"].eq(1)].drop_duplicates(["researcher_identity_key", "record_id"])
    record_people = eligible.groupby("record_id")["researcher_identity_key"].apply(set).to_dict()
    record_collections = (
        eligible.drop_duplicates("record_id").set_index("record_id")["matched_linked_collections"]
        .map(_collection_values).to_dict()
    )
    global_counts = Counter(collection for values in record_collections.values() for collection in values)
    major = tuple(sorted((name for name, count in global_counts.items() if count >= MAJOR_COLLECTION_MIN_RECORDS), key=str.casefold))
    researcher_counts = eligible.groupby("researcher_identity_key")["record_id"].nunique().to_dict()
    prolific = {key for key, count in researcher_counts.items() if count >= 2}
    rows: list[dict[str, object]] = []
    for key, group in frame.groupby("researcher_identity_key", sort=True):
        group_eligible = group.loc[group["provisional_base_owner_eligible"].eq(1)].drop_duplicates("record_id")
        record_ids = set(group_eligible["record_id"])
        coauthors = set().union(*(record_people.get(record_id, set()) for record_id in record_ids)) - {key}
        institutions: set[str] = set()
        collection_counts: Counter[str] = Counter()
        for row in group_eligible.to_dict("records"):
            institutions.update(part.strip() for part in str(row["reviewed_institutions_on_record"]).split(";") if part.strip())
            collection_counts.update(_collection_values(row["matched_linked_collections"]))
        shared = sum(bool((record_people.get(record_id, set()) - {key}) & prolific) for record_id in record_ids)
        ucl_values = set(group_eligible["ucl_linked_on_record"])
        ucl_status = "Yes" if "Yes" in ucl_values else ("No" if "No" in ucl_values else "Unknown")
        display = sorted(set(group["researcher_normalised"]), key=lambda value: (str(value).casefold(), str(value)))[0]
        statuses = set(group["entity_status"])
        reasons = set(group["entity_status_reason"])
        if len(statuses) != 1 or len(reasons) != 1:
            raise ValueError(f"Inconsistent entity classification for conservative identity key: {key}")
        entity_status = next(iter(statuses))
        rows.append({
            "researcher": display,
            "researcher_identity_key": key,
            "entity_status": entity_status,
            "entity_status_reason": next(iter(reasons)),
            "eligible_as_index_researcher": int(entity_status == "person_candidate"),
            "unique_eligible_record_ids": len(record_ids),
            "unique_eligible_official_project_ids": group_eligible["project_id"].nunique(),
            "earliest_project_year": group_eligible["record_year"].min() if len(group_eligible) else "",
            "latest_project_year": group_eligible["record_year"].max() if len(group_eligible) else "",
            "distinct_co_researchers": len(coauthors),
            "distinct_reviewed_institutions_on_associated_records": len(institutions),
            "reviewed_institutions_on_associated_records": _join(institutions),
            "ucl_linked_status_from_reviewed_record_institutions": ucl_status,
            "linked_collection_record_counts": _join(f"{name}={count}" for name, count in collection_counts.items()),
            "major_linked_collection_record_counts": _join(f"{name}={collection_counts.get(name, 0)}" for name in major),
            "records_shared_with_another_multi_project_researcher": shared,
            "raw_name_variants_observed": _join(group["researcher_displayed"]),
            "future_reserve_removal_pending": 1,
        })
    summary = pd.DataFrame(rows).sort_values(
        ["unique_eligible_record_ids", "researcher_identity_key"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    return summary, major


def researcher_portfolios(
    frame: pd.DataFrame, *, person_candidates_only: bool = True
) -> dict[str, frozenset[str]]:
    eligible = frame.loc[frame["provisional_base_owner_eligible"].eq(1)]
    if person_candidates_only:
        eligible = eligible.loc[eligible["entity_status"].eq("person_candidate")]
    return {
        key: frozenset(group["record_id"])
        for key, group in eligible.groupby("researcher_identity_key") if len(group)
    }


def build_coverage_sequences(
    summary: pd.DataFrame,
    portfolios: Mapping[str, frozenset[str]],
    eligible_population_count: int,
) -> pd.DataFrame:
    metadata = summary.set_index("researcher_identity_key").to_dict("index")
    keys = tuple(portfolios)
    orders: dict[str, list[str]] = {
        "raw_project_count": sorted(keys, key=lambda key: (-len(portfolios[key]), key)),
    }
    remaining = set(keys)
    covered: set[str] = set()
    greedy: list[str] = []
    while remaining:
        chosen = min(
            remaining,
            key=lambda key: (-len(portfolios[key] - covered), -len(portfolios[key]), key),
        )
        greedy.append(chosen)
        covered.update(portfolios[chosen])
        remaining.remove(chosen)
    orders["greedy_marginal_coverage"] = greedy
    rows: list[dict[str, object]] = []
    for method, order in orders.items():
        covered = set()
        for position, key in enumerate(order, 1):
            records = portfolios[key]
            new = records - covered
            already = records & covered
            covered.update(records)
            meta = metadata[key]
            rows.append({
                "planning_method": method,
                "sequence_position": position,
                "researcher": meta["researcher"],
                "researcher_identity_key": key,
                "entity_status": meta.get("entity_status", "person_candidate"),
                "total_eligible_records": len(records),
                "newly_covered_records": len(new),
                "cumulative_unique_records_covered": len(covered),
                "cumulative_proportion_of_eligible_population": len(covered) / eligible_population_count,
                "already_covered_records_contributed": len(already),
                "ucl_linked_status": meta["ucl_linked_status_from_reviewed_record_institutions"],
                "reviewed_institutions_on_associated_records": meta["reviewed_institutions_on_associated_records"],
                "tie_break_rule": (
                    "new coverage descending; total eligible records descending; conservative identity key ascending"
                    if method.startswith("greedy") else
                    "total eligible records descending; conservative identity key ascending"
                ),
                "planning_only_not_an_official_selection": 1,
            })
    return pd.DataFrame(rows)


def build_coverage_thresholds(sequences: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, group in sequences.groupby("planning_method", sort=True):
        group = group.sort_values("sequence_position")
        for threshold in THRESHOLDS:
            reached = group.loc[group["cumulative_unique_records_covered"].ge(threshold)]
            chosen = reached.iloc[0] if len(reached) else group.iloc[-1]
            rows.append({
                "planning_method": method,
                "target_unique_eligible_records": threshold,
                "index_researchers_required": int(chosen["sequence_position"]) if len(reached) else "",
                "actual_unique_records_covered": int(chosen["cumulative_unique_records_covered"]),
                "threshold_reached": int(bool(len(reached))),
                "planning_only_not_an_official_selection": 1,
            })
    return pd.DataFrame(rows)


def build_entity_exclusion_audit(
    summary: pd.DataFrame,
    unfiltered_sequences: pd.DataFrame,
    reviews: pd.DataFrame,
) -> pd.DataFrame:
    positions = {
        (row["planning_method"], row["researcher_identity_key"]): int(row["sequence_position"])
        for row in unfiltered_sequences.to_dict("records")
    }
    rows: list[dict[str, object]] = []
    for row in summary.loc[~summary["entity_status"].eq("person_candidate")].to_dict("records"):
        key = row["researcher_identity_key"]
        rows.append({
            "displayed_identity": row["researcher"],
            "researcher_identity_key": key,
            "entity_status": row["entity_status"],
            "entity_status_reason": row["entity_status_reason"],
            "eligible_record_count": row["unique_eligible_record_ids"],
            "raw_count_position_before_filtering": positions.get(("raw_project_count", key), ""),
            "greedy_position_before_filtering": positions.get(("greedy_marginal_coverage", key), ""),
            "exclusion_reason": "Not a person_candidate; retained for restricted audit only.",
        })
    unparsed = reviews.loc[reviews["review_reason"].isin({"empty_or_malformed_researcher_field", "no_person_name_parsed"})]
    represented = set(summary.loc[~summary["entity_status"].eq("person_candidate"), "researcher_identity_key"])
    for row in unparsed.to_dict("records"):
        if row.get("researcher_normalised") and researcher_identity_key(row["researcher_normalised"]) in represented:
            continue
        rows.append({
            "displayed_identity": row.get("researcher_normalised", ""),
            "researcher_identity_key": researcher_identity_key(row["researcher_normalised"]) if row.get("researcher_normalised") else "",
            "entity_status": "unparsed",
            "entity_status_reason": row["review_reason"],
            "eligible_record_count": 1,
            "raw_count_position_before_filtering": "",
            "greedy_position_before_filtering": "",
            "exclusion_reason": "No conservative person identity available for sequencing.",
        })
    return pd.DataFrame(rows).drop_duplicates().sort_values(
        ["entity_status", "eligible_record_count", "researcher_identity_key"],
        ascending=[True, False, True], kind="stable",
    ).reset_index(drop=True)


def build_leading_identity_review(
    summary: pd.DataFrame,
    frame: pd.DataFrame,
    corrected_sequences: pd.DataFrame,
    unfiltered_sequences: pd.DataFrame,
) -> pd.DataFrame:
    corrected = corrected_sequences.loc[corrected_sequences["sequence_position"].le(30)]
    raw_position = corrected.loc[corrected["planning_method"].eq("raw_project_count")].set_index("researcher_identity_key")["sequence_position"].to_dict()
    greedy_rows = corrected.loc[corrected["planning_method"].eq("greedy_marginal_coverage")]
    greedy_position = greedy_rows.set_index("researcher_identity_key")["sequence_position"].to_dict()
    greedy_marginal = greedy_rows.set_index("researcher_identity_key")["newly_covered_records"].to_dict()
    old_leading = unfiltered_sequences.loc[unfiltered_sequences["sequence_position"].le(30)]
    old_keys = set(old_leading["researcher_identity_key"])
    status = summary.set_index("researcher_identity_key")["entity_status"].to_dict()
    flagged = set(raw_position) | set(greedy_position) | {key for key in old_keys if status.get(key) != "person_candidate"}
    portfolios = researcher_portfolios(frame, person_candidates_only=False)
    displays = summary.set_index("researcher_identity_key")["researcher"].to_dict()
    variants: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    people = list(summary.loc[summary["entity_status"].eq("person_candidate"), "researcher_identity_key"])
    raw30 = corrected_sequences.loc[
        corrected_sequences["planning_method"].eq("raw_project_count")
        & corrected_sequences["sequence_position"].eq(30), "total_eligible_records"
    ]
    raw30_cut = int(raw30.iloc[0]) if len(raw30) else 0
    for left, right in itertools.combinations(people, 2):
        if not _possible_variant(displays[left], displays[right]):
            continue
        shared = len(portfolios.get(left, frozenset()) & portfolios.get(right, frozenset()))
        merged = len(portfolios.get(left, frozenset()) | portfolios.get(right, frozenset()))
        variants[left].append((right, shared, merged))
        variants[right].append((left, shared, merged))
        if left in flagged or right in flagged or merged >= raw30_cut:
            flagged.update({left, right})
    cut_counts = {}
    raw = corrected_sequences.loc[corrected_sequences["planning_method"].eq("raw_project_count")]
    for cutoff in (10, 20, 30):
        row = raw.loc[raw["sequence_position"].eq(cutoff)]
        cut_counts[cutoff] = int(row.iloc[0]["total_eligible_records"]) if len(row) else 0
    meta = summary.set_index("researcher_identity_key").to_dict("index")
    rows = []
    for key in sorted(flagged):
        item = meta[key]
        variant_items = sorted(variants.get(key, []), key=lambda value: displays[value[0]].casefold())
        max_merged = max((value[2] for value in variant_items), default=int(item["unique_eligible_record_ids"]))
        affects = {cutoff: bool(variant_items and max_merged >= threshold) for cutoff, threshold in cut_counts.items()}
        rows.append({
            "displayed_identity": item["researcher"],
            "conservative_identity_key": key,
            "entity_status": item["entity_status"],
            "status_reason": item["entity_status_reason"],
            "raw_count_position": raw_position.get(key, ""),
            "greedy_position": greedy_position.get(key, ""),
            "eligible_record_id_count": item["unique_eligible_record_ids"],
            "marginal_record_contribution": greedy_marginal.get(key, ""),
            "observed_raw_name_variants": item["raw_name_variants_observed"],
            "possible_unmerged_variants": _join(displays[other] for other, _, _ in variant_items),
            "shared_records_with_flagged_variants": _join(f"{displays[other]}={shared}" for other, shared, _ in variant_items),
            "could_alter_first_10": int(affects[10]),
            "could_alter_first_20": int(affects[20]),
            "could_alter_first_30": int(affects[30]),
            "review_status": "pending_manual_review" if variant_items or item["entity_status"] != "person_candidate" else "leading_identity_check_pending",
            "review_note": "No automatic merge; organisation/ambiguous entities are excluded from corrected sequences.",
        })
    result = pd.DataFrame(rows)
    result["_raw_sort"] = pd.to_numeric(result["raw_count_position"], errors="coerce").fillna(10**9)
    result["_greedy_sort"] = pd.to_numeric(result["greedy_position"], errors="coerce").fillna(10**9)
    return result.sort_values(
        ["_raw_sort", "_greedy_sort", "conservative_identity_key"], kind="stable",
    ).drop(columns=["_raw_sort", "_greedy_sort"]).reset_index(drop=True)


def build_prefix_concentration(
    sequences: pd.DataFrame,
    portfolios: Mapping[str, frozenset[str]],
    eligible_record_ids: frozenset[str],
    institutions: pd.DataFrame,
    properties: pd.DataFrame,
) -> pd.DataFrame:
    """Profile unique covered records; marker percentages may overlap."""
    institution_by_record = (
        institutions.loc[institutions["Record ID"].astype(str).isin(eligible_record_ids)]
        .groupby("Record ID")["institution"].apply(set).to_dict()
    )
    for record_id in eligible_record_ids:
        institution_by_record.setdefault(record_id, set())
    products_by_record = {
        str(row["Record ID"]): _collection_values(row.get("matched_products", ""))
        for row in properties.to_dict("records") if str(row["Record ID"]) in eligible_record_ids
    }
    product_counts = Counter(product for values in products_by_record.values() for product in values)
    major_products = tuple(sorted(
        (product for product, count in product_counts.items() if count >= MAJOR_COLLECTION_MIN_RECORDS),
        key=lambda value: (value.casefold(), value),
    ))
    product_markers: dict[str, set[str]] = {}
    for record_id in eligible_record_ids:
        products = products_by_record.get(record_id, frozenset())
        markers = {product for product in major_products if product in products}
        if any("data first" in product.casefold() for product in products):
            markers.add("Data First")
        if not markers:
            markers.add("No major linked-product marker")
        product_markers[record_id] = markers
    institution_markers = sorted(
        {marker for values in institution_by_record.values() for marker in values},
        key=lambda value: (value.casefold(), value),
    )
    linked_markers = sorted(
        {marker for values in product_markers.values() for marker in values},
        key=lambda value: (value.casefold(), value),
    )
    population_n = len(eligible_record_ids)
    population_counts = {
        "institution_marker": {
            marker: sum(marker in institution_by_record[record_id] for record_id in eligible_record_ids)
            for marker in institution_markers
        },
        "linked_product_marker": {
            marker: sum(marker in product_markers[record_id] for record_id in eligible_record_ids)
            for marker in linked_markers
        },
        "ucl_record_marker": {
            "Reviewed UCL record marker": sum(
                bool(institution_by_record[record_id] & UCL_INSTITUTIONS)
                for record_id in eligible_record_ids
            )
        },
    }
    rows: list[dict[str, object]] = []
    for method, sequence in sequences.groupby("planning_method", sort=True):
        sequence = sequence.sort_values("sequence_position")
        for prefix in PREFIXES:
            selected = tuple(sequence.head(prefix)["researcher_identity_key"])
            covered = set().union(*(portfolios[key] for key in selected)) if selected else set()
            covered_n = len(covered)
            dimension_values = {
                "institution_marker": institution_by_record,
                "linked_product_marker": product_markers,
                "ucl_record_marker": {
                    record_id: ({"Reviewed UCL record marker"} if institution_by_record[record_id] & UCL_INSTITUTIONS else set())
                    for record_id in eligible_record_ids
                },
            }
            for dimension, values_by_record in dimension_values.items():
                markers = population_counts[dimension]
                for marker, population_count in markers.items():
                    covered_count = sum(marker in values_by_record[record_id] for record_id in covered)
                    covered_proportion = covered_count / covered_n if covered_n else 0.0
                    population_proportion = population_count / population_n
                    rows.append({
                        "row_type": "marker_prevalence",
                        "planning_method": method,
                        "prefix_size": prefix,
                        "dimension": dimension,
                        "marker": marker,
                        "unique_covered_records": covered_n,
                        "covered_record_count": covered_count,
                        "covered_record_proportion": covered_proportion,
                        "eligible_population_record_count": population_count,
                        "eligible_population_proportion": population_proportion,
                        "prefix_to_population_prevalence_ratio": covered_proportion / population_proportion if population_proportion else "",
                        "metric": "",
                        "metric_value": "",
                        "notes": "Markers are record-level and multi-valued; proportions may sum above 100%." if dimension != "ucl_record_marker" else "Reviewed record-level UCL marker; not a verified personal affiliation.",
                    })
            institution_shares = sorted(
                (sum(marker in institution_by_record[record_id] for record_id in covered) / covered_n for marker in institution_markers),
                reverse=True,
            ) if covered_n else []
            product_shares = sorted(
                (sum(marker in product_markers[record_id] for record_id in covered) / covered_n for marker in linked_markers if marker != "No major linked-product marker"),
                reverse=True,
            ) if covered_n else []
            selected_set = set(selected)
            multiple = sum(
                sum(record_id in portfolios[key] for key in selected_set) > 1
                for record_id in covered
            )
            metrics = {
                "largest_single_institution_marker_share": max(institution_shares, default=0.0),
                "five_largest_institution_marker_shares_sum": sum(institution_shares[:5]),
                "largest_linked_product_share": max(product_shares, default=0.0),
                "five_largest_linked_product_shares_sum": sum(product_shares[:5]),
                "distinct_institution_markers": sum(any(marker in institution_by_record[record_id] for record_id in covered) for marker in institution_markers),
                "distinct_major_linked_products": sum(any(marker in product_markers[record_id] for record_id in covered) for marker in linked_markers if marker != "No major linked-product marker"),
                "records_receiving_multiple_reviews": multiple,
                "proportion_receiving_multiple_reviews": multiple / covered_n if covered_n else 0.0,
            }
            for metric, value in metrics.items():
                rows.append({
                    "row_type": "summary_indicator", "planning_method": method,
                    "prefix_size": prefix, "dimension": "summary", "marker": "",
                    "unique_covered_records": covered_n, "covered_record_count": "",
                    "covered_record_proportion": "", "eligible_population_record_count": population_n,
                    "eligible_population_proportion": "", "prefix_to_population_prevalence_ratio": "",
                    "metric": metric, "metric_value": value,
                    "notes": "Coverage uses unique Record IDs; no diversity-adjusted ranking is applied.",
                })
    return pd.DataFrame(rows)


def build_overlap_summary(
    frame: pd.DataFrame,
    sequences: pd.DataFrame,
    eligible_record_to_project: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    eligible = frame.loc[
        frame["provisional_base_owner_eligible"].eq(1)
        & frame["entity_status"].eq("person_candidate")
    ].drop_duplicates(
        ["researcher_identity_key", "record_id"]
    )
    record_people = eligible.groupby("record_id")["researcher_identity_key"].apply(set).to_dict()
    project_people = eligible.groupby("project_id")["researcher_identity_key"].apply(set).to_dict()
    if eligible_record_to_project is not None:
        for record_id, project_id in eligible_record_to_project.items():
            record_people.setdefault(record_id, set())
            project_people.setdefault(project_id, set())
    rows: list[dict[str, object]] = []
    for unit, groups in (("record", record_people), ("official_project_id", project_people)):
        distribution = Counter(len(values) for values in groups.values())
        for count, units in sorted(distribution.items()):
            rows.append({
                "row_type": f"{unit}_researcher_count_distribution",
                "named_researcher_count": count,
                "eligible_unit_count": units,
            })
        rows.append({
            "row_type": f"{unit}_one_named_researcher",
            "eligible_unit_count": sum(len(values) == 1 for values in groups.values()),
        })
        rows.append({
            "row_type": f"{unit}_multiple_named_researchers",
            "eligible_unit_count": sum(len(values) > 1 for values in groups.values()),
        })
    pair_counts: Counter[tuple[str, str]] = Counter()
    for people in record_people.values():
        pair_counts.update(itertools.combinations(sorted(people), 2))
    names = (
        eligible.drop_duplicates("researcher_identity_key")
        .set_index("researcher_identity_key")["researcher_normalised"].to_dict()
    )
    for (left, right), count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0])):
        rows.append({
            "row_type": "researcher_pair_shared_eligible_records",
            "researcher_a": names[left],
            "researcher_b": names[right],
            "shared_eligible_record_count": count,
        })
    for method, sequence in sequences.groupby("planning_method", sort=True):
        sequence = sequence.sort_values("sequence_position")
        for cutoff in PREFIXES:
            selected = set(sequence.head(cutoff)["researcher_identity_key"])
            multiple = sum(len(people & selected) > 1 for people in record_people.values())
            rows.append({
                "row_type": "prefix_records_receiving_multiple_reviews",
                "planning_method": method,
                "position_cutoff": cutoff,
                "eligible_record_count": multiple,
            })
    columns = [
        "row_type", "planning_method", "position_cutoff", "researcher_a", "researcher_b",
        "named_researcher_count", "eligible_unit_count", "shared_eligible_record_count",
        "eligible_record_count", "notes",
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def _profile_markdown(
    population: pd.DataFrame,
    frame: pd.DataFrame,
    summary: pd.DataFrame,
    reviews: pd.DataFrame,
    sequences: pd.DataFrame,
    thresholds: pd.DataFrame,
    institutions: pd.DataFrame,
    major_collections: Sequence[str],
    exclusion_count: int,
) -> str:
    eligible_records = len(population) - exclusion_count
    eligible_frame = frame.loc[frame["provisional_base_owner_eligible"].eq(1)]
    parsed_records = eligible_frame["record_id"].nunique()
    counts = summary["unique_eligible_record_ids"]
    lines = [
        "# Project-owner sampling exploration profile",
        "",
        "Planning evidence only. No official recruitment cohort or reserve has been selected.",
        "",
        "## Source frame and eligibility",
        "",
        f"- The canonical June 2026 pipeline reproduced {len(population):,} unique Record IDs and {population['Project ID'].nunique():,} unique official Project IDs exactly.",
        f"- The 22 training/pilot Record IDs are marked ineligible, leaving {eligible_records:,} provisionally base-eligible records.",
        "- Scratch-coder reserve records have not been removed because no official draw exists. Final owner eligibility requires reserve removal after that draw.",
        f"- At least one researcher was conservatively parsed for {parsed_records:,} of the {eligible_records:,} provisionally eligible records.",
        "",
        "## Parsing and identity",
        "",
        "Names use the repository's reviewed logical-line and person-name recognition rules. Normalisation is limited to Unicode typography, punctuation, line/separator and whitespace consistency. Exact within-record duplicates are removed. No fuzzy merge, web resolution, or contact lookup is performed.",
        f"The frame contains {len(frame):,} unique researcher-record relationships, {len(summary):,} conservative researcher identities, and {len(reviews):,} manual-review rows.",
        "Institution and UCL fields are reviewed record-level associations; they must not be interpreted as verified current personal affiliations.",
        "",
        "Unresolved manual-review reasons: "
        + "; ".join(
            f"{reason}={count}"
            for reason, count in reviews["review_reason"].value_counts().sort_index().items()
        )
        + ".",
        "",
        "## Eligible portfolio distribution",
        "",
        f"Median eligible records per researcher: {counts.median():.0f}; mean: {counts.mean():.2f}; maximum: {counts.max():.0f}.",
    ]
    for threshold in (2, 3, 5, 10, 15):
        lines.append(f"- Researchers with at least {threshold} eligible records: {int(counts.ge(threshold).sum()):,}.")
    lines += ["", "## Coverage planning sequences", ""]
    for method, group in sequences.groupby("planning_method", sort=True):
        group = group.sort_values("sequence_position")
        values = []
        for prefix in PREFIXES:
            row = group.iloc[min(prefix, len(group)) - 1]
            values.append(
                f"top {prefix}: {int(row['cumulative_unique_records_covered'])} "
                f"({row['cumulative_proportion_of_eligible_population']:.1%})"
            )
        target = thresholds.loc[
            thresholds["planning_method"].eq(method)
            & thresholds["target_unique_eligible_records"].eq(100)
        ].iloc[0]
        lines.append(
            f"- {method}: " + "; ".join(values)
            + f". Researchers required to reach 100 records: {target['index_researchers_required']}."
        )
    ucl_records = eligible_frame.loc[eligible_frame["ucl_linked_on_record"].eq("Yes"), "record_id"].nunique()
    ucl_researchers = summary["ucl_linked_status_from_reviewed_record_institutions"].eq("Yes").sum()
    eligible_ids = set(eligible_frame["record_id"])
    institution_record_counts = (
        institutions.loc[institutions["Record ID"].astype(str).isin(eligible_ids)]
        .groupby("institution")["Record ID"].nunique().sort_values(ascending=False)
    )
    lines += [
        "", "## Institution and linked-collection concentration", "",
        f"- {ucl_records:,} eligible records contain a reviewed UCL institution marker; {ucl_researchers:,} conservative researcher portfolios touch at least one such record.",
    ]
    if len(institution_record_counts):
        lines.append(
            f"- The largest reviewed institution occurs on {int(institution_record_counts.iloc[0]):,} eligible records; "
            f"the five largest together account for {int(institution_record_counts.head(5).sum()):,} institution-record mentions."
        )
    lines.append(
        f"- {len(major_collections)} deterministic linked-data products occur on at least "
        f"{MAJOR_COLLECTION_MIN_RECORDS} eligible records; product-specific counts are in the restricted summary."
    )
    collection_counts: Counter[str] = Counter()
    for value in eligible_frame.drop_duplicates("record_id")["matched_linked_collections"]:
        collection_counts.update(_collection_values(value))
    if collection_counts:
        lines.append(
            "- Most frequent deterministic linked products: "
            + "; ".join(f"{name} ({count} records)" for name, count in collection_counts.most_common(5))
            + "."
        )
    prolific = set(summary.loc[summary["unique_eligible_record_ids"].ge(2), "researcher_identity_key"])
    record_people = eligible_frame.groupby("record_id")["researcher_identity_key"].apply(set)
    overlap_records = sum(len(values & prolific) > 1 for values in record_people)
    one_named = sum(len(values) == 1 for values in record_people)
    multiple_named = sum(len(values) > 1 for values in record_people)
    zero_named = eligible_records - len(record_people)
    pair_counts: Counter[tuple[str, str]] = Counter()
    for people in record_people:
        pair_counts.update(itertools.combinations(sorted(people), 2))
    lines += [
        "", "## Overlap and limitations", "",
        f"- Eligible Record-ID multiplicity: {zero_named:,} with no parsed name, {one_named:,} with one, and {multiple_named:,} with multiple.",
        f"- {overlap_records:,} eligible records are shared by at least two researchers who each have multiple eligible projects.",
        f"- The largest conservatively identified researcher pair shares {max(pair_counts.values(), default=0):,} eligible records; {sum(count >= 2 for count in pair_counts.values()):,} pairs share at least two.",
        "- Raw project counts favour concentrated portfolios; greedy marginal coverage favours breadth but can still concentrate institutions or data collections.",
        "- Neither ordering represents willingness, reachability, independence of responses, current project ownership, or a defensible recruitment probability.",
        "- Manual name review, reserve removal after the official draw, contact-governance decisions, and a preregistered recruitment/sampling rule remain necessary.",
        "", "No official project-owner cohort, reserve, recruitment list, or contact file has been selected or created.", "",
    ]
    for method, sequence in sequences.groupby("planning_method", sort=True):
        sequence = sequence.sort_values("sequence_position")
        values = []
        for cutoff in PREFIXES:
            selected = set(sequence.head(cutoff)["researcher_identity_key"])
            values.append(f"top {cutoff}={sum(len(people & selected) > 1 for people in record_people)}")
        lines.insert(-2, f"- Records that would receive multiple reviews under {method}: " + "; ".join(values) + ".")
    return "\n".join(lines)


def assert_no_contact_columns(frames: Iterable[pd.DataFrame]) -> None:
    for frame in frames:
        prohibited = [
            column for column in frame.columns
            if any(term in column.casefold() for term in FORBIDDEN_CONTACT_TERMS)
        ]
        if prohibited:
            raise ValueError(f"Contact-like columns are prohibited: {prohibited}")


def corrected_profile_markdown(
    population: pd.DataFrame,
    frame: pd.DataFrame,
    summary: pd.DataFrame,
    reviews: pd.DataFrame,
    sequences: pd.DataFrame,
    thresholds: pd.DataFrame,
    concentration: pd.DataFrame,
    entity_audit: pd.DataFrame,
    leading_review: pd.DataFrame,
    exclusion_count: int,
) -> str:
    people = summary.loc[summary["entity_status"].eq("person_candidate")]
    status_counts = summary["entity_status"].value_counts().to_dict()
    status_counts["unparsed"] = int(entity_audit["entity_status"].eq("unparsed").sum())
    eligible_n = len(population) - exclusion_count
    lines = [
        "# Corrected project-owner sampling exploration profile", "",
        "Planning evidence only. No recruitment cohort, reserve, or contact list has been selected.", "",
        "## Population and entity eligibility", "",
        f"- Canonical population: {len(population):,} unique Record IDs and {population['Project ID'].nunique():,} unique official Project IDs.",
        f"- Training/pilot exclusions: {exclusion_count}; provisional pre-reserve owner-review population: {eligible_n:,} records.",
        "- Reviewed institution aliases and canonical names take precedence over person-shaped syntax. Strong organisation constructions are excluded; all-uppercase, numeric, or otherwise unresolved entities are withheld as ambiguous.",
        "- Only person_candidate identities enter raw-count or greedy sequences. Excluded entities remain in the restricted frame and audits.",
    ]
    for status in ("person_candidate", "organisation_exact_match", "organisation_pattern_match", "ambiguous_entity", "unparsed"):
        lines.append(f"- {status}: {int(status_counts.get(status, 0)):,} identities/audit entries.")
    organisations = entity_audit["entity_status"].isin({"organisation_exact_match", "organisation_pattern_match"})
    ambiguous = entity_audit["entity_status"].eq("ambiguous_entity")
    lines += [
        f"- Organisation identities withheld: {int(organisations.sum()):,}, associated with {int(entity_audit.loc[organisations, 'eligible_record_count'].sum()):,} identity-record counts before deduplication.",
        f"- Ambiguous identities withheld: {int(ambiguous.sum()):,}.", "",
        "## Identity review", "",
        f"- Manual parse/variant review rows: {len(reviews):,}.",
        f"- Leading-identity audit rows: {len(leading_review):,}.",
        f"- Rows potentially able to alter first 10 / 20 / 30 positions: {int(leading_review['could_alter_first_10'].sum())} / {int(leading_review['could_alter_first_20'].sum())} / {int(leading_review['could_alter_first_30'].sum())}.",
        "- Possible variants remain separate; no fuzzy merge is applied.", "",
        "## Corrected person-candidate portfolios", "",
        f"- Identities: {len(people):,}; median eligible records: {people['unique_eligible_record_ids'].median():.0f}; mean: {people['unique_eligible_record_ids'].mean():.2f}; maximum: {people['unique_eligible_record_ids'].max():.0f}.",
    ]
    for cutoff in (2, 3, 5, 10, 15):
        lines.append(f"- At least {cutoff} eligible records: {int(people['unique_eligible_record_ids'].ge(cutoff).sum()):,} people.")
    lines += ["", "## Corrected coverage", ""]
    for method, group in thresholds.groupby("planning_method", sort=True):
        details = "; ".join(
            f"{int(row.target_unique_eligible_records)} records -> {row.index_researchers_required} people ({int(row.actual_unique_records_covered)} reached)"
            for row in group.itertuples()
        )
        lines.append(f"- {method}: {details}.")
    lines += ["", "## Prefix concentration", ""]
    for method in sorted(sequences["planning_method"].unique()):
        for prefix in (5, 10, 15, 20):
            block = concentration.loc[
                concentration["planning_method"].eq(method)
                & concentration["prefix_size"].eq(prefix)
            ]
            marker_rows = block.loc[block["row_type"].eq("marker_prevalence")]
            inst = marker_rows.loc[marker_rows["dimension"].eq("institution_marker")].sort_values("covered_record_proportion", ascending=False)
            products = marker_rows.loc[
                marker_rows["dimension"].eq("linked_product_marker")
                & ~marker_rows["marker"].eq("No major linked-product marker")
            ].sort_values("covered_record_proportion", ascending=False)
            ucl = marker_rows.loc[marker_rows["dimension"].eq("ucl_record_marker")].iloc[0]
            metrics = block.loc[block["row_type"].eq("summary_indicator")].set_index("metric")["metric_value"].to_dict()
            covered = int(block["unique_covered_records"].iloc[0])
            top_inst = "none" if not len(inst) else f"{inst.iloc[0]['marker']} {float(inst.iloc[0]['covered_record_proportion']):.1%}"
            top_product = "none" if not len(products) else f"{products.iloc[0]['marker']} {float(products.iloc[0]['covered_record_proportion']):.1%}"
            lines.append(
                f"- {method} top {prefix}: {covered} unique records; largest institution marker {top_inst}; "
                f"UCL record marker {float(ucl['covered_record_proportion']):.1%} versus {float(ucl['eligible_population_proportion']):.1%} population; "
                f"largest major product {top_product}; multiple-review records {int(float(metrics['records_receiving_multiple_reviews']))}."
            )
    lines += [
        "", "## Interpretation limits", "",
        "- Institution markers are record-level reviewed markers, not verified current affiliations of index researchers.",
        "- Institution and product markers are multi-valued; their percentages can sum above 100%.",
        "- Greedy coverage is recomputed from the corrected person-only frame and is not a splice of the prior sequence.",
        "- The sequences do not encode willingness, contactability, independence, current ownership, recruitment probability, or a diversity adjustment.",
        "- Manual leading-identity review and removal of the future scratch reserve remain necessary before preregistration.", "",
        "No official project-owner recruitment cohort or reserve has been selected.", "",
    ]
    return "\n".join(lines)


def generate_outputs(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, object]:
    output_dir = output_dir.resolve()
    restricted_root = (REPO_ROOT / "preregistration_restricted").resolve()
    if output_dir != restricted_root and restricted_root not in output_dir.parents:
        raise ValueError("Name-bearing outputs must remain below preregistration_restricted")
    population = reconstruct_canonical_population()
    exclusions = load_exclusion_ids()
    population_ids = set(population["Record ID"].astype(str))
    if not exclusions <= population_ids:
        raise ValueError("The 22-record exclusion set is not a subset of the cleaned population")
    properties = pd.read_csv(PROPERTIES, encoding="utf-8-sig", dtype=str).fillna("")
    if set(properties["Record ID"]) != population_ids or len(properties) != EXPECTED_RECORDS:
        raise ValueError("Deterministic property frame does not match the 1,308 Record IDs")
    institutions = parse_institutions_with_metadata(population)
    frame, reviews = build_researcher_record_frame(population, exclusions, properties, institutions)
    frame = resolve_frame_entity_statuses(frame)
    reviews = add_variant_reviews(frame, reviews)
    summary, major_collections = build_researcher_summary(frame)
    portfolios = researcher_portfolios(frame)
    unfiltered_portfolios = researcher_portfolios(frame, person_candidates_only=False)
    eligible_population_count = EXPECTED_RECORDS - len(exclusions)
    sequences = build_coverage_sequences(summary, portfolios, eligible_population_count)
    unfiltered_sequences = build_coverage_sequences(summary, unfiltered_portfolios, eligible_population_count)
    thresholds = build_coverage_thresholds(sequences)
    eligible_record_to_project = {
        str(row["Record ID"]): str(row["Project ID"])
        for row in population.to_dict("records")
        if str(row["Record ID"]) not in exclusions
    }
    overlap = build_overlap_summary(frame, sequences, eligible_record_to_project)
    entity_audit = build_entity_exclusion_audit(summary, unfiltered_sequences, reviews)
    leading_review = build_leading_identity_review(
        summary, frame, sequences, unfiltered_sequences
    )
    eligible_ids = frozenset(eligible_record_to_project)
    concentration = build_prefix_concentration(
        sequences, portfolios, eligible_ids, institutions, properties
    )
    assert_no_contact_columns((
        frame, summary, reviews, sequences, thresholds, overlap,
        entity_audit, leading_review, concentration,
    ))
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "researcher_record_frame.csv": frame,
        "researcher_summary.csv": summary,
        "researcher_name_parse_review.csv": reviews,
        "researcher_coverage_sequence.csv": sequences,
        "coverage_thresholds.csv": thresholds,
        "researcher_overlap_summary.csv": overlap,
        "leading_identity_review.csv": leading_review,
        "entity_exclusion_audit.csv": entity_audit,
        "planning_prefix_concentration.csv": concentration,
    }
    for filename, data in outputs.items():
        data.to_csv(output_dir / filename, index=False, encoding="utf-8-sig")
    profile = corrected_profile_markdown(
        population, frame, summary, reviews, sequences, thresholds,
        concentration, entity_audit, leading_review, len(exclusions),
    )
    (output_dir / "owner_sampling_profile.md").write_text(profile, encoding="utf-8")
    return {
        "population_records": len(population),
        "unique_project_ids": population["Project ID"].nunique(),
        "exclusions": len(exclusions),
        "provisional_eligible_records": eligible_population_count,
        "researcher_record_relationships": len(frame),
        "conservative_researcher_identities": len(summary),
        "review_rows": len(reviews),
        "major_linked_collections": len(major_collections),
        "entity_status_counts": summary["entity_status"].value_counts().to_dict(),
        "entity_exclusion_rows": len(entity_audit),
        "leading_identity_review_rows": len(leading_review),
        "output_dir": str(output_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    print(generate_outputs(parse_args().output_dir))
