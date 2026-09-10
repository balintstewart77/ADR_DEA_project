"""Domain-breadth aggregation, rendering, and Portfolio callback regressions."""

import pandas as pd
import pytest
from dash.development.base_component import Component
from unittest.mock import patch

from dashboard import taxonomy
from dashboard.charts.thematic import make_domain_breadth_trend
from dashboard.config import PartialYearInfo
from dashboard.data import thematic
from dashboard.data.registry import df_all
from dashboard.data.thematic import domain_breadth_aggregates
from dashboard.data.year_filter import YearRange, year_range


DOMAIN_A = "Labour Market & Employment"
DOMAIN_B = "Education & Skills"
DOMAIN_C = "Health & Social Care"
DOMAIN_D = "Crime & Justice"
UNCLEAR = "Unclear from Register Entry"


def _fixture_register():
    rows = [
        ("r1", "repeat", "01 Jan 2024"),
        ("r2", "repeat", "02 Jan 2024"),
        ("r3", "three", "03 Jan 2024"),
        ("r4", "four", "04 Jan 2024"),
        ("r5", "five", "05 Jan 2024"),
        ("r6", "unclear", "06 Jan 2024"),
        ("r7", "missing", "07 Jan 2024"),
        ("r8", "invalid", "08 Jan 2024"),
        ("r9", "unmatched", "09 Jan 2024"),
        ("r10", "plus-unclear", "01 Aug 2024"),
        ("r11", "quarter-four", "01 Nov 2024"),
        ("r12", "next-year", "01 Feb 2025"),
    ]
    return pd.DataFrame(rows, columns=["Record ID", "Project ID", "Accreditation Date"])


def _fixture_classifications():
    rows = [
        ("r1", DOMAIN_A, 1),
        ("r2", f"{DOMAIN_A}; {DOMAIN_B}", 2),
        ("r3", f"{DOMAIN_A}; {DOMAIN_B}; {DOMAIN_C}", 3),
        ("r4", f"{DOMAIN_A}; {DOMAIN_B}; {DOMAIN_C}; {DOMAIN_D}", 4),
        ("r5", f"{DOMAIN_A}; {DOMAIN_A}", 1),
        ("r6", UNCLEAR, 1),
        ("r7", None, None),
        ("r8", f"{DOMAIN_A}; invented domain", 2),
        ("r10", f"{DOMAIN_A}; {UNCLEAR}", 2),
        ("r11", f"{DOMAIN_A}; {DOMAIN_B}", 2),
        ("r12", f"{DOMAIN_A}; {DOMAIN_B}; {DOMAIN_C}", 3),
    ]
    return pd.DataFrame(
        rows,
        columns=["Record ID", "substantive_domains", "substantive_domain_count"],
    )


@pytest.fixture
def breadth_data():
    return domain_breadth_aggregates(
        _fixture_register(), _fixture_classifications(), [2024, 2025], YearRange(2024, 2025),
    )


def _period(frame, label):
    return frame.loc[frame["period_label"].eq(label)].set_index("domain_breadth")


def test_domain_breadth_uses_distinct_taxonomy_domains_and_reconciles_coverage(breadth_data):
    quarter = _period(breadth_data["df_domain_breadth_by_quarter"], "2024 Q1")
    assert quarter["count"].to_dict() == {
        "1 domain": 2,
        "2 domains": 1,
        "3+ domains": 2,
    }
    assert quarter["eligible_denominator"].nunique() == 1
    assert quarter["eligible_denominator"].iloc[0] == 5
    assert quarter["pct_of_eligible"].to_dict() == {
        "1 domain": 40.0,
        "2 domains": 20.0,
        "3+ domains": 40.0,
    }
    assert quarter["count"].sum() == quarter["eligible_denominator"].iloc[0]

    coverage = breadth_data["df_domain_breadth_coverage_by_quarter"].set_index("period_label")
    assert coverage.loc["2024 Q1", [
        "dated_selected_records", "included_records", "unmatched_classification",
        "missing_classification", "invalid_classification", "zero_substantive_domains",
        "excluded_records",
    ]].to_dict() == {
        "dated_selected_records": 9,
        "included_records": 5,
        "unmatched_classification": 1,
        "missing_classification": 1,
        "invalid_classification": 1,
        "zero_substantive_domains": 1,
        "excluded_records": 4,
    }
    assert coverage.loc["2024 Q1", "dated_selected_records"] == (
        coverage.loc["2024 Q1", "included_records"]
        + coverage.loc["2024 Q1", "excluded_records"]
    )
    # The Unclear-only stored count is deliberately not reused by this chart.
    assert breadth_data["domain_breadth_selection_coverage"]["stored_domain_count_discrepancies"] == 2


def test_quarterly_zero_periods_and_yearly_reconciliation_are_record_level(breadth_data):
    quarterly = breadth_data["df_domain_breadth_by_quarter"]
    q2 = _period(quarterly, "2024 Q2")
    assert q2["count"].tolist() == [0, 0, 0]
    assert q2["eligible_denominator"].tolist() == [0, 0, 0]
    assert q2["pct_of_eligible"].isna().tolist() == [True, True, True]

    yearly = _period(breadth_data["df_domain_breadth_by_year"], "2024")
    assert yearly["count"].to_dict() == {
        "1 domain": 3,
        "2 domains": 2,
        "3+ domains": 2,
    }
    assert yearly["eligible_denominator"].iloc[0] == 7
    assert yearly["pct_of_eligible"].to_dict() == {
        "1 domain": 42.9,
        "2 domains": 28.6,
        "3+ domains": 28.6,
    }
    assert yearly["count"].sum() == yearly["eligible_denominator"].iloc[0]


def test_restricted_selection_reset_and_empty_or_excluded_populations():
    register = _fixture_register()
    classifications = _fixture_classifications()
    bounds = YearRange(2024, 2025)
    restricted = domain_breadth_aggregates(register, classifications, [2024, 2024], bounds)
    assert restricted["df_domain_breadth_by_quarter"]["period_label"].drop_duplicates().tolist() == [
        "2024 Q1", "2024 Q2", "2024 Q3", "2024 Q4",
    ]
    assert restricted["domain_breadth_selection_coverage"]["included_records"] == 7
    reset = domain_breadth_aggregates(register, classifications, bounds.value, bounds)
    assert reset["domain_breadth_selection_coverage"]["included_records"] == 8

    excluded = domain_breadth_aggregates(
        register.loc[register["Record ID"].isin(["r6", "r7", "r8", "r9"])],
        classifications.loc[classifications["Record ID"].isin(["r6", "r7", "r8"])],
        [2024, 2024],
        bounds,
    )
    assert excluded["domain_breadth_selection_coverage"]["included_records"] == 0
    assert excluded["df_domain_breadth_by_year"]["pct_of_eligible"].isna().all()

    empty = domain_breadth_aggregates(register, classifications, [2023, 2023], bounds)
    assert empty["df_domain_breadth_by_year"].empty
    assert empty["df_domain_breadth_coverage_by_year"].empty


def test_chart_has_stable_series_unavailable_gaps_and_complete_hover_data(breadth_data):
    fig = make_domain_breadth_trend(
        breadth_data["df_domain_breadth_by_quarter"],
        metric="pct",
        granularity="quarter",
        partial_year_info=PartialYearInfo(2025, "2025*", "* 2025 data covers Jan–Feb only"),
    )
    assert [trace.name for trace in fig.data] == ["1 domain", "2 domains", "3+ domains"]
    assert [trace.marker.symbol for trace in fig.data] == ["circle", "square", "diamond"]
    assert fig.layout.yaxis.title.text == "Percentage of records with ≥1 substantive domain"
    assert "Eligible denominator" in fig.data[0].hovertemplate
    q2_index = list(fig.data[0].x).index("2024 Q2")
    assert fig.data[0].y[q2_index] is None
    assert any("2025 data covers" in annotation.text for annotation in fig.layout.annotations)


def _component_by_id(root, component_id):
    if isinstance(root, Component):
        if getattr(root, "id", None) == component_id:
            return root
        children = getattr(root, "children", None)
        if isinstance(children, (list, tuple)):
            for child in children:
                found = _component_by_id(child, component_id)
                if found is not None:
                    return found
        elif children is not None:
            return _component_by_id(children, component_id)
    return None


def test_layout_and_callback_depend_only_on_breadth_controls_and_portfolio_filter():
    from dashboard.app import app
    from dashboard.layout.analysis.thematic import build_thematic_tab

    layout = build_thematic_tab()
    assert _component_by_id(layout, "thematic-domain-breadth-metric").value == "pct"
    assert _component_by_id(layout, "thematic-domain-breadth-granularity").value == "year"
    assert _component_by_id(layout, "thematic-domain-breadth-coverage-table") is not None
    callback = next(
        spec for key, spec in app.callback_map.items()
        if "thematic-domain-breadth-trend.figure" in key
    )
    assert {
        f"{item['id']}.{item['property']}" for item in callback["inputs"]
    } == {
        "thematic-domain-breadth-metric.value",
        "thematic-domain-breadth-granularity.value",
        "portfolio-accreditation-year-filter.value",
    }
    assert callback["state"] == []


def test_actual_callback_handles_empty_and_all_excluded_populations(breadth_data):
    from dashboard.app import app
    from dashboard.callbacks import thematic as callbacks

    callback = next(
        spec["callback"].__wrapped__
        for key, spec in app.callback_map.items()
        if "thematic-domain-breadth-trend.figure" in key
    )
    empty_figure, empty_coverage, empty_note = callback("pct", "year", [2030, 2030])
    assert len(empty_figure.data) == 3
    assert empty_coverage == []
    assert "0 have a usable" in empty_note
    assert any("No usable substantive-domain" in item.text for item in empty_figure.layout.annotations)

    excluded_data = dict(breadth_data)
    excluded_data["df_domain_breadth_by_year"] = pd.DataFrame([
        {
            "Year": 2024, "Quarter": None, "period_date": pd.Timestamp("2024-01-01"),
            "period_label": "2024", "domain_breadth": category, "count": 0,
            "eligible_denominator": 0, "pct_of_eligible": None,
        }
        for category in ["1 domain", "2 domains", "3+ domains"]
    ])
    excluded_data["df_domain_breadth_coverage_by_year"] = pd.DataFrame([{
        "period_label": "2024", "dated_selected_records": 4, "included_records": 0,
        "unmatched_classification": 1, "missing_classification": 1,
        "invalid_classification": 1, "zero_substantive_domains": 1, "excluded_records": 4,
    }])
    excluded_data["domain_breadth_selection_coverage"] = {
        "selected_records": 4, "dated_selected_records": 4, "undated_selected_records": 0,
        "undated_omitted_records": 0, "included_records": 0,
        "unmatched_classification": 1, "missing_classification": 1,
        "invalid_classification": 1, "zero_substantive_domains": 1,
        "stored_domain_count_discrepancies": 0,
    }
    with patch.object(callbacks, "_aggregates", return_value=excluded_data):
        figure, coverage, note = callback("pct", "year", [2024, 2024])
    assert coverage[0]["excluded_records"] == 4
    assert "Zero substantive domains (1)" in note
    assert any("No usable substantive-domain" in item.text for item in figure.layout.annotations)


def test_current_release_reconciles_against_an_independent_record_level_count():
    bounds = year_range(df_all)
    result = domain_breadth_aggregates(df_all, thematic.df_thematic_projects, bounds.value, bounds)
    known = set(taxonomy.DOMAIN_LABELS)
    unclear = {label for label in known if label.lower().startswith("unclear")}
    expected = {"1 domain": 0, "2 domains": 0, "3+ domains": 0}
    for value in thematic.df_thematic_projects["substantive_domains"]:
        tokens = {part.strip() for part in str(value).split(";") if part.strip()}
        if not tokens or tokens - known:
            continue
        breadth = len(tokens - unclear)
        if breadth == 1:
            expected["1 domain"] += 1
        elif breadth == 2:
            expected["2 domains"] += 1
        elif breadth >= 3:
            expected["3+ domains"] += 1
    current = (
        result["df_domain_breadth_by_year"]
        .groupby("domain_breadth")["count"].sum().to_dict()
    )
    assert current == expected
    assert result["domain_breadth_selection_coverage"] == {
        "selected_records": 1343,
        "dated_selected_records": 1343,
        "undated_selected_records": 0,
        "undated_omitted_records": 0,
        "included_records": 1341,
        "unmatched_classification": 0,
        "missing_classification": 0,
        "invalid_classification": 0,
        "zero_substantive_domains": 2,
        "stored_domain_count_discrepancies": 2,
    }
