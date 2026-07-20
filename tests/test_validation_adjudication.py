from analysis.validation.adjudication import (
    ADJUDICATION_ISSUE_FAMILIES, AdjudicationCase, MechanismReport,
    adjudication_reasons, build_source_masked_stage1, recurring_mechanism,
)


def test_adjudication_population_reasons_are_protocol_scoped():
    case = AdjudicationCase(
        "SYN-001", "random_baseline", {"domains": frozenset({"A"})},
        {"domains": frozenset({"B"})}, owner_problem_reported=True,
    )
    assert adjudication_reasons(case) == {
        "production_majority_disagreement", "owner_reported_problem"
    }


def test_stage1_masks_sources_deduplicates_sets_and_withholds_owner_evidence():
    masked = build_source_masked_stage1({
        "production": frozenset({"A"}),
        "coder_a": frozenset({"A"}),
        "coder_b": frozenset({"B"}),
    }, seed=17)
    assert len(masked) == 2
    assert all(not hasattr(item, "source") for item in masked)
    assert {item.labels for item in masked} == {frozenset({"A"}), frozenset({"B"})}


def test_owner_only_stage1_does_not_construct_an_artificial_competitor():
    masked = build_source_masked_stage1({"production": frozenset({"A"})}, seed=18)
    assert len(masked) == 1


def test_recurring_rule_requires_distinct_records_or_independent_pre_reveal_streams():
    confirmation = (
        MechanismReport("SYN-001", "owner"),
        MechanismReport("SYN-001", "adjudicator", source_revealed_confirmation=True),
    )
    assert not recurring_mechanism(confirmation)
    assert recurring_mechanism((
        MechanismReport("SYN-001", "owner"),
        MechanismReport("SYN-002", "owner"),
    ))
    assert recurring_mechanism((
        MechanismReport("SYN-001", "owner"),
        MechanismReport("SYN-001", "scratch_coder"),
    ))


def test_issue_family_vocabulary_matches_v0_11():
    assert len(ADJUDICATION_ISSUE_FAMILIES) == 8
    assert "Taxonomy problem" in ADJUDICATION_ISSUE_FAMILIES
