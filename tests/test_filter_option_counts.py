"""Regression coverage for dynamic Project Explorer and Enriched facet labels."""

import copy
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from dashboard.data.filtering import (
    _BROWSE_FACET_OPTIONS,
    _ENRICHED_FACET_OPTIONS,
    _ENRICHED_FACET_PREDICATES,
    _REGISTER_FACET_PREDICATES,
    _apply_enriched_register_filters,
    _apply_register_filters,
    _enriched_register_base,
    _facet_options_with_dynamic_counts,
    _get_browse_display_df,
    _get_browse_facet_options,
    _get_enriched_register_display_df,
    _get_enriched_register_facet_options,
)
from dashboard.data.registry import df_all
from dashboard.data.year_filter import filter_records_by_year, selected_record_ids, year_range


BASELINE = json.loads(
    (Path(__file__).parent / "fixtures" / "filter_option_count_baseline.json").read_text()
)
YEAR_RANGE = year_range(df_all)
COUNT_RE = re.compile(r"  \((\d+) projects?\)$")


def _label_count(option):
    match = COUNT_RE.search(option["label"])
    assert match, option
    return int(match.group(1))


def _counts(options):
    return {option["value"]: _label_count(option) for option in options if option["value"] != "ALL"}


def _all_enriched_state(**overrides):
    state = {
        "search": None,
        "dataset": "ALL",
        "provider": "ALL",
        "institution": "ALL",
        "tre": "ALL",
        "domain": "ALL",
        "domain_count": "ALL",
        "purpose": "ALL",
        "tag": "ALL",
        "record_linkage": "ALL",
        "collection_method": "ALL",
        "temporal_structure": "ALL",
        "unit": "ALL",
        "researcher_sector": "ALL",
    }
    state.update(overrides)
    return state


def _browse_options(**state):
    selected = {"search": None, "dataset": "ALL", "provider": "ALL", "institution": "ALL", "tre": "ALL"}
    selected.update(state)
    return _get_browse_facet_options(
        selected["search"],
        selected["dataset"],
        selected["provider"],
        selected["institution"],
        selected["tre"],
        YEAR_RANGE.value,
        YEAR_RANGE.minimum,
        YEAR_RANGE.maximum,
    )


def _enriched_options(state=None, *, portfolio_years=None, years=None):
    selected = _all_enriched_state(**(state or {}))
    portfolio_years = portfolio_years or YEAR_RANGE.value
    years = years or YEAR_RANGE.value
    eligible_ids = selected_record_ids(df_all, portfolio_years, YEAR_RANGE)
    return _get_enriched_register_facet_options(
        selected["search"], selected["dataset"], selected["provider"],
        selected["institution"], selected["tre"], selected["domain"],
        selected["domain_count"], selected["purpose"], selected["tag"],
        selected["record_linkage"], selected["collection_method"],
        selected["temporal_structure"], selected["unit"], selected["researcher_sector"],
        eligible_ids, years, YEAR_RANGE.minimum, YEAR_RANGE.maximum,
    )


def _record_ids(frame):
    return set(frame["Record ID"].astype(str))


def _sha256_csv(frame):
    return hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()


def test_reset_counts_match_independent_predicates_and_recorded_static_baseline():
    """The counter is not its own oracle at reset, including every old label."""
    explorer = _browse_options()
    enriched = _enriched_options()

    for facet, options in _BROWSE_FACET_OPTIONS.items():
        expected = {
            option["value"]: int(
                _REGISTER_FACET_PREDICATES[facet](df_all, option["value"])["Record ID"].nunique()
            )
            for option in options if option["value"] != "ALL"
        }
        assert _counts(explorer[facet]) == expected
        assert expected == {item["value"]: item["count"] for item in BASELINE["static_option_counts"][facet]}

    base = _enriched_register_base()
    for facet, options in _ENRICHED_FACET_OPTIONS.items():
        expected = {
            option["value"]: int(
                _ENRICHED_FACET_PREDICATES[facet](base, option["value"])["Record ID"].nunique()
            )
            for option in options if option["value"] != "ALL"
        }
        assert _counts(enriched[facet]) == expected
        static = {item["value"]: item["count"] for item in BASELINE["static_option_counts"][facet]}
        if facet == "domain_count":
            assert {key: value for key, value in expected.items() if key != 0} == {
                key: value for key, value in static.items() if key != 0
            }
            assert (static[0], expected[0]) == (2, 1343)
        else:
            assert expected == static


def test_other_filters_constrain_counts_but_a_facet_own_selection_does_not():
    selected_dataset = "Annual Business Survey (ABS)"
    initial = _browse_options()
    constrained = _browse_options(dataset=selected_dataset)

    # Dataset labels omit the dataset selection itself; provider labels retain it.
    assert _counts(constrained["dataset"]) == _counts(initial["dataset"])
    expected_provider = _apply_register_filters(
        df_all, None, selected_dataset, "ALL", "ALL", "ALL",
    )
    provider = "Bank of England"
    expected = _REGISTER_FACET_PREDICATES["provider"](expected_provider, provider)
    assert _counts(constrained["provider"])[provider] == expected["Record ID"].nunique()

    state = {"domain": "Business & Productivity", "purpose": "Outcome Tracking"}
    enriched = _enriched_options(state)
    without_domain = _apply_enriched_register_filters(
        _enriched_register_base(), _all_enriched_state(**state), {"domain"},
    )
    assert _counts(enriched["domain"])["Health & Social Care"] == _ENRICHED_FACET_PREDICATES["domain"](
        without_domain, "Health & Social Care",
    )["Record ID"].nunique()
    assert _counts(enriched["domain"]) == _counts(_enriched_options({"purpose": "Outcome Tracking"})["domain"])


def test_search_year_and_portfolio_restrictions_are_included_without_cross_tab_state():
    explorer = _browse_options(search="mortality", dataset="ALL")
    direct = _apply_register_filters(df_all, "mortality", "ALL", "ALL", "ALL", "ALL")
    assert _counts(explorer["tre"])["ONS Secure Research Service (SRS)"] == _REGISTER_FACET_PREDICATES["tre"](
        direct, "ONS Secure Research Service (SRS)",
    )["Record ID"].nunique()

    years = [2024, 2024]
    enriched = _enriched_options({"search": "mortality"}, portfolio_years=years, years=years)
    eligible = selected_record_ids(df_all, years, YEAR_RANGE)
    base = _enriched_register_base(eligible)
    direct = filter_records_by_year(
        _apply_enriched_register_filters(base, _all_enriched_state(search="mortality"), {"tre"}),
        years, YEAR_RANGE,
    )
    assert _counts(enriched["tre"])["ONS Secure Research Service (SRS)"] == _ENRICHED_FACET_PREDICATES["tre"](
        direct, "ONS Secure Research Service (SRS)",
    )["Record ID"].nunique()
    # Explorer's state remains independent of Portfolio's upstream restriction.
    assert _counts(_browse_options(search="mortality")["tre"]) == _counts(explorer["tre"])


def test_zero_count_options_remain_present_enabled_and_filter_to_an_empty_result():
    state = {"dataset": "Annual Business Survey (ABS)"}
    options = _browse_options(**state)
    zero_provider = "Annual Population Survey"
    option = next(option for option in options["provider"] if option["value"] == zero_provider)
    assert _label_count(option) == 0
    assert "disabled" not in option

    result = _get_browse_display_df(
        None, state["dataset"], zero_provider, "ALL", "ALL",
    )
    assert result.empty
    # Restoring the selected dataset does not remove the zero-count provider.
    assert any(option["value"] == zero_provider for option in _browse_options(**state)["provider"])


def test_distinct_record_identity_and_multilabel_rows_are_not_inflated():
    base = pd.DataFrame([
        {"Record ID": "r1", "Project ID": "same", "labels": "alpha; beta"},
        {"Record ID": "r1", "Project ID": "same", "labels": "alpha; beta"},
        {"Record ID": "r2", "Project ID": "same", "labels": "alpha"},
    ])
    options = {"labels": [{"label": "All labels", "value": "ALL"}, {"label": "Alpha", "value": "alpha"}]}
    observed = _facet_options_with_dynamic_counts(
        base,
        {"labels": "alpha"},
        options,
        lambda frame, _state, _excluded: frame,
        {"labels": lambda frame, value: frame[frame["labels"].str.contains(value, regex=False)]},
    )
    assert _label_count(observed["labels"][1]) == 2


def test_option_definitions_order_table_results_and_exports_are_unchanged():
    before_browse = copy.deepcopy(_BROWSE_FACET_OPTIONS)
    before_enriched = copy.deepcopy(_ENRICHED_FACET_OPTIONS)
    _browse_options(search="mortality", dataset="Annual Business Survey (ABS)")
    _enriched_options({"domain": "Business & Productivity", "purpose": "Outcome Tracking"})
    assert _BROWSE_FACET_OPTIONS == before_browse
    assert _ENRICHED_FACET_OPTIONS == before_enriched

    explorer_fixture = BASELINE["representative_prechange_results"]["explorer"]
    explorer = _get_browse_display_df(None, explorer_fixture["filters"]["dataset"], "ALL", "ALL", "ALL")
    assert _sha256_csv(explorer) == explorer_fixture["export_sha256"]

    enriched_fixture = BASELINE["representative_prechange_results"]["enriched"]
    enriched, _ = _get_enriched_register_display_df(
        None, "ALL", "ALL", "ALL", "ALL", enriched_fixture["filters"]["domain"],
        "ALL", "ALL", "ALL",
    )
    assert _sha256_csv(enriched) == enriched_fixture["export_sha256"]


def test_callbacks_own_each_option_output_once_without_writing_values_or_year_marks():
    from dashboard.app import app

    for prefix, facets in (("browse", _BROWSE_FACET_OPTIONS), ("enriched", _ENRICHED_FACET_OPTIONS)):
        for facet in facets:
            target = f"{prefix}-{facet.replace('_', '-')}-filter.options"
            owners = [key for key in app.callback_map if target in key]
            assert len(owners) == 1
            metadata = app.callback_map[owners[0]]
            outputs = metadata["output"]
            assert {item.component_property for item in outputs if item.component_id.startswith(prefix)} >= {"options"}
            assert not any(item.component_property == "value" for item in outputs)
            assert not any(item.component_property == "marks" for item in outputs)
