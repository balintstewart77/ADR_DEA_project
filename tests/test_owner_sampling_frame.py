from __future__ import annotations

import pandas as pd
import pytest

from analysis.validation.owner_sampling_frame import (
    EXPECTED_RECORDS,
    assert_no_contact_columns,
    apply_scratch_reserve_exclusions,
    build_contactability_aware_sequence,
    build_prefix_concentration,
    build_researcher_summary,
    build_coverage_sequences,
    build_coverage_thresholds,
    build_overlap_summary,
    build_sequence_recruitment_batches,
    build_researcher_record_frame,
    classify_entity,
    load_exclusion_ids,
    normalise_researcher_name,
    parse_researcher_field,
    researcher_identity_key,
    researcher_portfolios,
    validate_population,
)


def test_multiple_researchers_duplicates_and_separator_normalisation():
    names, reviews = parse_researcher_field(
        "  Alex Alpha, Synthetic University ; Alex Alpha, Synthetic University\n"
        "Blair Beta, Test Institute  "
    )
    assert [name.normalised for name in names] == ["Alex Alpha", "Blair Beta"]
    assert {item["reason"] for item in reviews} >= {
        "ambiguous_separator", "exact_duplicate_name_removed"
    }


def test_unicode_and_whitespace_normalisation_is_conservative():
    assert normalise_researcher_name("  Jo  O’Neil–Smith  ") == "Jo O'Neil-Smith"


def test_similar_names_are_not_fuzzily_merged():
    names, _ = parse_researcher_field(
        "Alex Smith, Synthetic University\nA Smith, Synthetic University"
    )
    assert len(names) == 2
    assert researcher_identity_key(names[0].normalised) != researcher_identity_key(names[1].normalised)


def synthetic_inputs():
    population = pd.DataFrame([
        {
            "Record ID": "SYN-001", "Project ID": "SYN-P1", "Title": "Synthetic one",
            "Researchers": "Alex Alpha, Synthetic University\nBlair Beta, Test Institute",
            "Year": 2020, "Datasets Used": "Synthetic data",
        },
        {
            "Record ID": "SYN-002", "Project ID": "SYN-P2", "Title": "Synthetic two",
            "Researchers": "Alex Alpha, Synthetic University", "Year": 2021,
            "Datasets Used": "Synthetic data",
        },
        {
            "Record ID": "SYN-003", "Project ID": "SYN-P3", "Title": "Synthetic three",
            "Researchers": "Casey Gamma, Test Institute\nBlair Beta, Test Institute",
            "Year": 2022, "Datasets Used": "Synthetic data",
        },
    ])
    properties = pd.DataFrame([
        {
            "Record ID": record_id, "record_linkage": "No record linkage",
            "matched_products": "", "dataset_collection_methods": "",
            "dataset_temporal_structures": "", "dataset_units": "",
            "researcher_sectors": "",
        }
        for record_id in population["Record ID"]
    ])
    institutions = pd.DataFrame([
        {"Record ID": "SYN-001", "institution": "Synthetic University"},
        {"Record ID": "SYN-002", "institution": "Synthetic University"},
        {"Record ID": "SYN-003", "institution": "Test Institute"},
    ])
    return population, properties, institutions


def test_frame_handles_multi_record_people_overlap_and_exclusion():
    population, properties, institutions = synthetic_inputs()
    frame, _ = build_researcher_record_frame(
        population, frozenset({"SYN-003"}), properties, institutions
    )
    alex = frame.loc[frame["researcher_normalised"].eq("Alex Alpha")]
    assert set(alex["record_id"]) == {"SYN-001", "SYN-002"}
    assert frame.loc[
        frame["record_id"].eq("SYN-003"), "provisional_base_owner_eligible"
    ].eq(0).all()
    assert frame.loc[
        frame["record_id"].eq("SYN-001"), "in_training_pilot_exclusion_set"
    ].eq(0).all()


def test_greedy_coverage_and_tie_breaking_are_deterministic():
    portfolios = {
        "alex": frozenset({"SYN-001", "SYN-002"}),
        "blair": frozenset({"SYN-001", "SYN-003"}),
        "casey": frozenset({"SYN-004"}),
    }
    summary = pd.DataFrame([
        {
            "researcher_identity_key": key, "researcher": key.title(),
            "ucl_linked_status_from_reviewed_record_institutions": "Unknown",
            "reviewed_institutions_on_associated_records": "",
        }
        for key in portfolios
    ])
    first = build_coverage_sequences(summary, portfolios, 4)
    second = build_coverage_sequences(summary, portfolios, 4)
    pd.testing.assert_frame_equal(first, second)
    greedy = first.loc[first["planning_method"].eq("greedy_marginal_coverage")]
    assert list(greedy["researcher_identity_key"]) == ["alex", "blair", "casey"]
    assert list(greedy["newly_covered_records"]) == [2, 1, 1]


def test_thresholds_report_actual_coverage_without_official_selection():
    portfolios = {
        "a": frozenset({f"SYN-{i:03d}" for i in range(1, 31)}),
        "b": frozenset({f"SYN-{i:03d}" for i in range(31, 61)}),
    }
    summary = pd.DataFrame([
        {
            "researcher_identity_key": key, "researcher": key,
            "ucl_linked_status_from_reviewed_record_institutions": "Unknown",
            "reviewed_institutions_on_associated_records": "",
        }
        for key in portfolios
    ])
    thresholds = build_coverage_thresholds(
        build_coverage_sequences(summary, portfolios, 100)
    )
    row = thresholds.loc[
        thresholds["planning_method"].eq("raw_project_count")
        & thresholds["target_unique_eligible_records"].eq(50)
    ].iloc[0]
    assert row["index_researchers_required"] == 2
    assert row["actual_unique_records_covered"] == 60


def test_population_size_and_project_count_are_strict():
    with pytest.raises(ValueError, match="missing columns"):
        validate_population(pd.DataFrame([{"Record ID": "SYN-001"}]))
    frame = pd.DataFrame({
        "Record ID": [f"SYN-{i:04d}" for i in range(EXPECTED_RECORDS)],
        "Project ID": [f"SYN-P{i:04d}" for i in range(EXPECTED_RECORDS)],
        "Title": "Synthetic", "Researchers": "Alex Alpha", "Year": 2020,
        "Datasets Used": "Synthetic",
    })
    with pytest.raises(ValueError, match="1304"):
        validate_population(frame)


def test_no_contact_columns_are_emitted():
    population, properties, institutions = synthetic_inputs()
    frame, reviews = build_researcher_record_frame(
        population, frozenset(), properties, institutions
    )
    assert_no_contact_columns((frame, reviews))
    assert not any("email" in column.casefold() for column in frame.columns)


def test_overlap_distribution_retains_eligible_records_with_no_parsed_name():
    population, properties, institutions = synthetic_inputs()
    frame, _ = build_researcher_record_frame(
        population, frozenset(), properties, institutions
    )
    summary = pd.DataFrame([
        {
            "researcher_identity_key": key,
            "researcher": key,
            "ucl_linked_status_from_reviewed_record_institutions": "Unknown",
            "reviewed_institutions_on_associated_records": "",
        }
        for key in frame["researcher_identity_key"].unique()
    ])
    portfolios = {
        key: frozenset(group["record_id"])
        for key, group in frame.groupby("researcher_identity_key")
    }
    sequence = build_coverage_sequences(summary, portfolios, 4)
    overlap = build_overlap_summary(
        frame, sequence,
        {"SYN-001": "SYN-P1", "SYN-002": "SYN-P2", "SYN-003": "SYN-P3", "SYN-004": "SYN-P4"},
    )
    zero = overlap.loc[
        overlap["row_type"].eq("record_researcher_count_distribution")
        & overlap["named_researcher_count"].eq(0)
    ]
    assert int(zero.iloc[0]["eligible_unit_count"]) == 1


def test_synthetic_fixture_contains_no_real_record_ids():
    population, _, _ = synthetic_inputs()
    assert population["Record ID"].str.fullmatch(r"SYN-\d{3}").all()


def test_reviewed_synthetic_institution_alias_precedes_person_shape():
    status, reason = classify_entity(
        "Example Labs", reviewed_aliases={"example labs": "Example Laboratories"}
    )
    assert status == "organisation_exact_match"
    assert "alias" in reason


@pytest.mark.parametrize(
    "value",
    ["Example Research Ltd", "Northshire University", "Synthetic Policy Institute"],
)
def test_organisation_patterns_are_not_people(value):
    assert classify_entity(value, reviewed_aliases={})[0] == "organisation_pattern_match"


def test_ambiguous_and_valid_people_are_distinguished():
    assert classify_entity("EXAMPLE PERSON", reviewed_aliases={})[0] == "ambiguous_entity"
    assert classify_entity("Alex Alpha", reviewed_aliases={})[0] == "person_candidate"


def test_record_survives_when_organisation_and_person_are_both_present():
    population = pd.DataFrame([{
        "Record ID": "SYN-010", "Project ID": "SYN-P10", "Title": "Synthetic",
        "Researchers": "Example Research Ltd\nAlex Alpha, Northshire University",
        "Year": 2024, "Datasets Used": "Synthetic",
    }])
    properties = pd.DataFrame([{
        "Record ID": "SYN-010", "record_linkage": "No record linkage",
        "matched_products": "", "dataset_collection_methods": "",
        "dataset_temporal_structures": "", "dataset_units": "", "researcher_sectors": "",
    }])
    institutions = pd.DataFrame([{"Record ID": "SYN-010", "institution": "Northshire University"}])
    frame, _ = build_researcher_record_frame(population, frozenset(), properties, institutions)
    assert set(frame["entity_status"]) == {"organisation_pattern_match", "person_candidate"}
    person_portfolios = researcher_portfolios(frame)
    assert set(person_portfolios) == {"alex alpha"}
    assert person_portfolios["alex alpha"] == frozenset({"SYN-010"})


def test_person_only_sequences_recompute_greedy_from_start():
    rows = []
    for identity, status, records in (
        ("Example Research Ltd", "organisation_pattern_match", {"SYN-001", "SYN-002", "SYN-003"}),
        ("Alex Alpha", "person_candidate", {"SYN-001", "SYN-004"}),
        ("Blair Beta", "person_candidate", {"SYN-002", "SYN-003"}),
        ("EXAMPLE PERSON", "ambiguous_entity", {"SYN-004"}),
    ):
        for record_id in records:
            rows.append({
                "researcher_identity_key": identity.casefold(), "researcher_normalised": identity,
                "record_id": record_id, "provisional_base_owner_eligible": 1,
                "entity_status": status,
            })
    frame = pd.DataFrame(rows)
    summary = pd.DataFrame([
        {
            "researcher_identity_key": identity.casefold(), "researcher": identity,
            "entity_status": status,
            "ucl_linked_status_from_reviewed_record_institutions": "Unknown",
            "reviewed_institutions_on_associated_records": "",
        }
        for identity, status in (
            ("Example Research Ltd", "organisation_pattern_match"),
            ("Alex Alpha", "person_candidate"), ("Blair Beta", "person_candidate"),
            ("EXAMPLE PERSON", "ambiguous_entity"),
        )
    ])
    unfiltered = build_coverage_sequences(summary, researcher_portfolios(frame, person_candidates_only=False), 4)
    corrected = build_coverage_sequences(summary, researcher_portfolios(frame), 4)
    assert unfiltered.loc[unfiltered.planning_method.eq("greedy_marginal_coverage")].iloc[0].entity_status == "organisation_pattern_match"
    assert corrected.groupby("planning_method")["entity_status"].apply(set).eq({"person_candidate"}).all()
    assert "example person" not in set(corrected["researcher_identity_key"])
    assert corrected.loc[corrected.planning_method.eq("greedy_marginal_coverage")].iloc[0].newly_covered_records == 2


def test_prefix_concentration_uses_unique_records_and_population_denominator():
    record_ids = frozenset(f"SYN-{number:03d}" for number in range(1, 11))
    portfolios = {
        "alex": frozenset({"SYN-001", "SYN-002"}),
        "blair": frozenset({"SYN-002", "SYN-003"}),
    }
    summary = pd.DataFrame([
        {"researcher_identity_key": key, "researcher": key, "entity_status": "person_candidate", "ucl_linked_status_from_reviewed_record_institutions": "Unknown", "reviewed_institutions_on_associated_records": ""}
        for key in portfolios
    ])
    sequences = build_coverage_sequences(summary, portfolios, 10)
    institutions = pd.DataFrame([
        {"Record ID": "SYN-001", "institution": "Northshire University"},
        {"Record ID": "SYN-001", "institution": "Northshire University"},
        {"Record ID": "SYN-002", "institution": "Northshire University"},
        {"Record ID": "SYN-002", "institution": "Synthetic Policy Institute"},
    ])
    properties = pd.DataFrame([
        {"Record ID": record_id, "matched_products": "Synthetic Major Product"}
        for record_id in record_ids
    ])
    concentration = build_prefix_concentration(
        sequences, portfolios, record_ids, institutions, properties
    )
    row = concentration.loc[
        concentration.planning_method.eq("raw_project_count")
        & concentration.prefix_size.eq(1)
        & concentration.dimension.eq("institution_marker")
        & concentration.marker.eq("Northshire University")
    ].iloc[0]
    assert row.covered_record_count == 2
    assert row.unique_covered_records == 2
    assert row.eligible_population_record_count == 2
    assert row.eligible_population_proportion == pytest.approx(0.2)
    assert row.prefix_to_population_prevalence_ratio == pytest.approx(5.0)
    product = concentration.loc[
        concentration.planning_method.eq("raw_project_count")
        & concentration.prefix_size.eq(1)
        & concentration.dimension.eq("linked_product_marker")
        & concentration.marker.eq("Synthetic Major Product")
    ].iloc[0]
    assert product.covered_record_count == 2


def test_exact_22_exclusion_enforcement(tmp_path):
    path = tmp_path / "synthetic_exclusions.csv"
    pd.DataFrame({"record_id": [f"SYN-{number:03d}" for number in range(21)]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="exactly 22"):
        load_exclusion_ids(path)


def test_reserve_exclusion_is_an_exact_join_without_identity_output():
    frame = pd.DataFrame({
        "record_id": ["SYN-001", "SYN-002", "SYN-003"],
        "provisional_base_owner_eligible": [1, 1, 0],
        "future_reserve_removal_pending": [1, 1, 1],
    })
    result = apply_scratch_reserve_exclusions(frame, {"SYN-002"})
    assert list(result["owner_review_record_eligibility"]) == [1, 0, 0]
    assert result["future_reserve_removal_pending"].eq(0).all()


def test_contactability_aware_greedy_recalculates_after_unreachable_candidate():
    portfolios = {
        "alex": frozenset({"SYN-001", "SYN-002", "SYN-003"}),
        "blair": frozenset({"SYN-001", "SYN-002"}),
        "casey": frozenset({"SYN-003", "SYN-004"}),
        "scratch": frozenset({"SYN-005"}),
    }
    summary = pd.DataFrame([
        {"researcher_identity_key": key, "entity_status": "person_candidate"}
        for key in portfolios
    ])
    result = build_contactability_aware_sequence(
        summary, portfolios, 5,
        {"alex": "unreachable", "blair": "contactable", "casey": "contactable"},
        scratch_coder_keys={"scratch"},
    )
    assert list(result.sequence["researcher_identity_key"]) == ["blair", "casey"]
    assert list(result.sequence["newly_covered_records"]) == [2, 2]
    assert result.disposition_audit.iloc[0]["contactability_disposition"] == "unreachable"


def test_unresolved_leading_contactability_stops_sequence():
    summary = pd.DataFrame([{
        "researcher_identity_key": "alex", "entity_status": "person_candidate"
    }])
    with pytest.raises(ValueError, match="must be resolved"):
        build_contactability_aware_sequence(
            summary, {"alex": frozenset({"SYN-001"})}, 1, {}
        )


def test_sequence_batches_follow_target_checkpoints_without_owner_reserve():
    batches = build_sequence_recruitment_batches(
        30, {14: 20, 21: 35, 28: 50}
    )
    assert list(batches["planned_people"]) == [10, 5, 5]
    assert list(batches["checkpoint_day"]) == [0, 14, 21]
    assert batches["minimum_viable_unique_complete_records"].eq(25).all()
