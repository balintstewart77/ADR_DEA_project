import csv
import json

import pytest

from analysis.visualisations.owner_sampling import (
    EXPECTED_GREEDY_CUMULATIVE,
    EXPECTED_TOTAL_CUMULATIVE,
    FIGURE_DATA_FIELDS,
    FIGURE_DATA_PATH,
    METADATA_PATH,
    PORTFOLIO_COMPARISON_PNG_PATH,
    PORTFOLIO_COMPARISON_SVG_PATH,
    PNG_PATH,
    PURE_SELECTION_TARGET,
    REPO_ROOT,
    STRATEGY_GREEDY,
    STRATEGY_TOTAL,
    SVG_PATH,
    figure_data_rows,
    greedy_marginal_coverage,
    load_authoritative_inputs,
    rank_by_total_projects,
    validate_expected_pure_curves,
    validate_figure_data,
    validate_selection_portfolio_counts,
)


def _synthetic():
    portfolios = {
        "a": {"p1", "p2", "p3", "p4"},
        "b": {"p1", "p2", "p3"},
        "c": {"p4", "p5"},
    }
    tie_breaks = {"a": "01", "b": "02", "c": "03"}
    return portfolios, tie_breaks


def test_total_count_ranking_is_sorted_once_not_dynamically_reranked():
    portfolios, tie_breaks = _synthetic()
    result = rank_by_total_projects(portfolios, tie_breaks)
    assert [row.candidate for row in result] == ["a", "b", "c"]
    assert [row.marginal_unique_projects for row in result] == [4, 0, 1]


def test_greedy_recomputes_marginal_and_removes_selected_candidate():
    portfolios, tie_breaks = _synthetic()
    result = greedy_marginal_coverage(portfolios, tie_breaks)
    assert [row.candidate for row in result] == ["a", "c", "b"]
    assert len({row.candidate for row in result}) == len(result)
    assert [row.marginal_unique_projects for row in result] == [4, 1, 0]


@pytest.mark.parametrize("strategy", [rank_by_total_projects, greedy_marginal_coverage])
def test_sequence_coverage_invariants_and_full_union(strategy):
    portfolios, tie_breaks = _synthetic()
    result = strategy(portfolios, tie_breaks)
    cumulative = [row.cumulative_unique_projects for row in result]
    assert cumulative == sorted(cumulative)
    assert all(row.marginal_unique_projects >= 0 for row in result)
    assert all(
        row.marginal_unique_projects <= row.owner_total_eligible_projects
        for row in result
    )
    selected_union = set()
    for row in result:
        selected_union.update(portfolios[row.candidate])
        assert row.cumulative_unique_projects == len(selected_union)
    assert result[-1].cumulative_unique_projects == len(set().union(*portfolios.values()))


def test_overlap_can_change_second_selection():
    portfolios, tie_breaks = _synthetic()
    total = rank_by_total_projects(portfolios, tie_breaks)
    greedy = greedy_marginal_coverage(portfolios, tie_breaks)
    assert total[1].candidate == "b"
    assert greedy[1].candidate == "c"


def test_total_count_ties_use_registered_identity_key():
    portfolios = {"a": {"p1", "p2"}, "b": {"p3", "p4"}}
    result = rank_by_total_projects(portfolios, {"a": "02", "b": "01"})
    assert [row.candidate for row in result] == ["b", "a"]
    assert result[0].tie_break_applied == "conservative_identity_key_asc"


def test_registered_tie_break_is_deterministic_at_both_levels():
    portfolios = {
        "first": {"p1", "p2", "p3", "p4"},
        "larger_total": {"p1", "p2", "p5"},
        "smaller_total": {"p3", "p5"},
        "identity_first": {"p1", "p6"},
        "identity_second": {"p2", "p7"},
    }
    tie_breaks = {
        "first": "00",
        "larger_total": "01",
        "smaller_total": "02",
        "identity_first": "03",
        "identity_second": "04",
    }
    result = greedy_marginal_coverage(portfolios, tie_breaks)
    assert result[0].candidate == "first"
    assert result[1].candidate == "larger_total"
    assert result[1].tie_break_applied == "total_eligible_record_count_desc"
    assert result[2].candidate == "identity_first"
    assert "conservative_identity_key_asc" in result[2].tie_break_applied


def test_pure_curves_reconcile_all_25_expected_values_without_contactability():
    inputs = load_authoritative_inputs()
    assert len(inputs.portfolios) == 2353
    greedy = greedy_marginal_coverage(
        inputs.portfolios,
        inputs.tie_break_keys,
        selection_limit=PURE_SELECTION_TARGET,
    )
    total = rank_by_total_projects(
        inputs.portfolios,
        inputs.tie_break_keys,
        selection_limit=PURE_SELECTION_TARGET,
    )
    denominator = len(set().union(*inputs.portfolios.values()))
    assert denominator == 1130
    validate_expected_pure_curves(total, greedy)
    validate_selection_portfolio_counts(total, inputs.portfolios)
    validate_selection_portfolio_counts(greedy, inputs.portfolios)
    assert tuple(row.cumulative_unique_projects for row in total) == (
        EXPECTED_TOTAL_CUMULATIVE
    )
    assert tuple(row.cumulative_unique_projects for row in greedy) == (
        EXPECTED_GREEDY_CUMULATIVE
    )
    assert total[-1].cumulative_unique_projects == 159
    assert greedy[-1].cumulative_unique_projects == 203


def test_generated_algorithm_data_has_common_selection_semantics_and_denominator():
    inputs = load_authoritative_inputs()
    greedy = greedy_marginal_coverage(
        inputs.portfolios,
        inputs.tie_break_keys,
        selection_limit=PURE_SELECTION_TARGET,
    )
    total = rank_by_total_projects(
        inputs.portfolios,
        inputs.tie_break_keys,
        selection_limit=PURE_SELECTION_TARGET,
    )
    denominator = len(set().union(*inputs.portfolios.values()))
    rows = figure_data_rows(total, greedy, denominator)
    validate_figure_data(rows, denominator)
    assert len(rows) == 2 * (PURE_SELECTION_TARGET + 1)
    for strategy in (STRATEGY_TOTAL, STRATEGY_GREEDY):
        selected = [row for row in rows if row["strategy"] == strategy]
        assert [row["selection_step"] for row in selected] == list(range(26))
        assert selected[0]["selection_step"] == 0
        assert selected[0]["owner_total_eligible_projects"] == ""
        assert selected[0]["marginal_unique_projects"] == ""
    assert rows[PURE_SELECTION_TARGET]["cumulative_unique_projects"] == (
        total[-1].cumulative_unique_projects
    )
    assert rows[-1]["cumulative_unique_projects"] == greedy[-1].cumulative_unique_projects
    total_rows = [row for row in rows if row["strategy"] == STRATEGY_TOTAL][1:]
    greedy_rows = [row for row in rows if row["strategy"] == STRATEGY_GREEDY][1:]
    total_portfolios = [int(row["owner_total_eligible_projects"]) for row in total_rows]
    greedy_portfolios = [
        int(row["owner_total_eligible_projects"]) for row in greedy_rows
    ]
    assert total_portfolios == sorted(total_portfolios, reverse=True)
    assert greedy_portfolios == [
        len(inputs.portfolios[item.candidate]) for item in greedy
    ]
    assert greedy_portfolios != sorted(greedy_portfolios, reverse=True)
    assert any(
        later > earlier
        for earlier, later in zip(greedy_portfolios, greedy_portfolios[1:], strict=True)
    )
    assert all(
        int(row["marginal_unique_projects"])
        <= int(row["owner_total_eligible_projects"])
        for row in total_rows + greedy_rows
    )


def test_public_outputs_are_anonymous_and_structurally_restricted():
    assert FIGURE_DATA_PATH.is_file()
    assert METADATA_PATH.is_file()
    assert PNG_PATH.is_file()
    assert SVG_PATH.is_file()
    assert PORTFOLIO_COMPARISON_PNG_PATH.is_file()
    assert PORTFOLIO_COMPARISON_SVG_PATH.is_file()
    with FIGURE_DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == FIGURE_DATA_FIELDS
    assert {row["strategy"] for row in rows} == {STRATEGY_TOTAL, STRATEGY_GREEDY}
    public_text = FIGURE_DATA_PATH.read_text(encoding="utf-8")
    public_text += METADATA_PATH.read_text(encoding="utf-8")
    public_text += SVG_PATH.read_text(encoding="utf-8")
    public_text += PORTFOLIO_COMPARISON_SVG_PATH.read_text(encoding="utf-8")
    lowered = public_text.casefold()
    forbidden_column_terms = (
        "researcher_name",
        "institution_name",
        "email",
        "owner_id,",
        "candidate_key,",
        "source_record_id",
        "project_title",
    )
    assert sum(term in lowered for term in forbidden_column_terms) == 0

    inputs = load_authoritative_inputs()
    sensitive_tokens = set(inputs.portfolios)
    sensitive_tokens.update(set().union(*inputs.portfolios.values()))
    restricted_frame = REPO_ROOT / (
        "preregistration_restricted/owner_candidate_frame_8a/"
        "owner_candidate_frame_restricted.csv"
    )
    with restricted_frame.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["frame_row_type"] == "candidate":
                sensitive_tokens.add(row["canonical_person_name"])
                sensitive_tokens.add(row["candidate_institution_normalised"])
    recruitment_table = REPO_ROOT / (
        "preregistration_restricted/owner_candidate_frame_8a/"
        "owner_recruitment_table.csv"
    )
    with recruitment_table.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for field in ("owner_id", "name", "institution", "contact_route"):
                sensitive_tokens.add(row[field])
    eligible_records = set().union(*inputs.portfolios.values())
    cleaned_population = REPO_ROOT / (
        "preregistration/package/01_source_and_cleaning/"
        "dea_accredited_projects_20260601_cleaned_1308.csv"
    )
    with cleaned_population.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["Record ID"] in eligible_records:
                sensitive_tokens.add(row["Title"])
    sensitive_tokens.discard("")
    matches = sum(token in public_text for token in sensitive_tokens)
    assert matches == 0

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    assert metadata["candidate_count"] == len(inputs.portfolios)
    assert metadata["eligible_unique_project_count"] == len(
        set().union(*inputs.portfolios.values())
    )
    assert "Ignored for both strategies" in metadata["contactability_handling"]
    assert metadata["figure_sequence_endpoint"] == {
        "algorithmic_selections_per_strategy": 25,
        "rule": "first 25 algorithmic candidate selections",
    }
    assert metadata["figure_outputs"][
        "paired_portfolio_and_marginal_comparison"
    ] == [
        "analysis/figures/owner_sampling_portfolio_vs_marginal_comparison.png",
        "analysis/figures/owner_sampling_portfolio_vs_marginal_comparison.svg",
    ]
