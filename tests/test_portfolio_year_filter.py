import hashlib
import json
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from dash.development.base_component import Component
from plotly.utils import PlotlyJSONEncoder

from dashboard.callbacks.datasets import build_dataset_demand_figures
from dashboard.callbacks.explorer import _filter_accreditation_year_range
from dashboard.callbacks.portfolio import build_overall_figures, portfolio_filter_summary
from dashboard.charts.institutions import make_institution_bar, make_institution_trend
from dashboard.charts.uptake import make_exposure_rate_bar
from dashboard.data import registry, thematic
from dashboard.data.collection_view import COLLECTION_VIEW_INDIVIDUAL
from dashboard.data.filtering import _get_enriched_register_display_df
from dashboard.data.uptake import (
    FLAGSHIP_PRODUCTS,
    adoption_curve_table,
    product_summary_table,
)
from dashboard.data.year_filter import (
    DATE_FIELD,
    RECORD_KEY,
    date_coverage,
    filter_records_by_year,
    filter_related_by_record_ids,
    selected_record_ids,
    year_range,
)
from dashboard.layout.analysis import build_analysis_tab
from dashboard.layout.explorer import build_explorer_tab


ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads(
    (ROOT / "tests/fixtures/portfolio_analysis_prechange_baseline.json").read_text()
)


def _normalise(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if pd.isna(value) else float(value)
    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)
    if isinstance(value, np.ndarray):
        return [_normalise(item) for item in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalise(item) for key, item in value.items()}
    return value


def _sha256_payload(payload) -> str:
    serialised = json.dumps(
        _normalise(payload),
        sort_keys=True,
        separators=(",", ":"),
        cls=PlotlyJSONEncoder,
    )
    return hashlib.sha256(serialised.encode()).hexdigest()


def _figure_data(figure):
    return [
        {
            "type": trace.get("type"),
            "name": trace.get("name"),
            "x": trace.get("x"),
            "y": trace.get("y"),
            "z": trace.get("z"),
            "values": trace.get("values"),
            "labels": trace.get("labels"),
            "customdata": trace.get("customdata"),
        }
        for trace in figure.to_plotly_json().get("data", [])
    ]


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


def _all_component_ids(root):
    found = []
    if isinstance(root, Component):
        if getattr(root, "id", None):
            found.append(root.id)
        children = getattr(root, "children", None)
        if isinstance(children, (list, tuple)):
            for child in children:
                found.extend(_all_component_ids(child))
        elif children is not None:
            found.extend(_all_component_ids(children))
    return found


def test_shared_contract_preserves_record_units_and_invalid_date_policy():
    fixture = pd.DataFrame(
        {
            "Record ID": ["same/a", "same/b", "missing", "malformed", "boundary"],
            "Project ID": ["same", "same", "missing", "malformed", "boundary"],
            "Accreditation Date": [
                "15 Jan 2020", "20 Jun 2022", None, "not-a-date", "31 Dec 2023",
            ],
        }
    )
    bounds = year_range(fixture)

    assert filter_records_by_year(fixture, bounds.value, bounds)[RECORD_KEY].tolist() == fixture[RECORD_KEY].tolist()
    assert selected_record_ids(fixture, [2020, 2022], bounds) == ["same/a", "same/b"]
    assert selected_record_ids(fixture, [2023, 2023], bounds) == ["boundary"]
    assert date_coverage(fixture) == {
        "eligible_records": 5,
        "valid_year_records": 3,
        "missing_date_records": 1,
        "malformed_date_records": 1,
        "undated_or_invalid_records": 2,
    }

    related = pd.DataFrame(
        {
            "Record ID": ["same/a", "same/a", "same/b", "malformed"],
            "Project ID": ["same", "same", "same", "malformed"],
            "value": [1, 2, 3, 4],
        }
    )
    selected = filter_related_by_record_ids(related, ["same/a"])
    assert selected["value"].tolist() == [1, 2]
    assert "same/b" not in selected["Record ID"].tolist()

    explorer_display = fixture[["Project ID", DATE_FIELD]].copy()
    filtered, _ = _filter_accreditation_year_range(
        explorer_display, [2020, 2022], bounds.minimum, bounds.maximum,
    )
    assert filtered["Project ID"].tolist() == ["same", "same"]


def test_both_tabs_use_same_full_register_options_and_independent_state():
    explorer = build_explorer_tab()
    portfolio = build_analysis_tab()
    explorer_slider = _component_by_id(explorer, "browse-accreditation-year-filter")
    portfolio_slider = _component_by_id(portfolio, "portfolio-accreditation-year-filter")

    assert explorer_slider.id != portfolio_slider.id
    assert explorer_slider.min == portfolio_slider.min == 2019
    assert explorer_slider.max == portfolio_slider.max == 2026
    assert explorer_slider.value == portfolio_slider.value == [2019, 2026]
    assert explorer_slider.marks == portfolio_slider.marks
    assert getattr(explorer_slider, "persistence", None) is None
    assert getattr(portfolio_slider, "persistence", None) is None
    ids = _all_component_ids(portfolio)
    assert len(ids) == len(set(ids))


def test_current_date_coverage_and_derived_fields_reconcile_exactly():
    coverage = date_coverage(registry.df_all)
    assert coverage == {
        "eligible_records": 1343,
        "valid_year_records": 1343,
        "missing_date_records": 0,
        "malformed_date_records": 0,
        "undated_or_invalid_records": 0,
    }
    dates = pd.to_datetime(registry.df_all[DATE_FIELD], errors="coerce")
    assert dates.dt.year.astype("Int64").equals(registry.df_all["Year"].astype("Int64"))
    assert (dates.dt.to_period("Q") == registry.df_all["Quarter"]).all()
    yearly = dates.dt.year.value_counts().sort_index().to_dict()
    assert {str(year): int(count) for year, count in yearly.items()} == BASELINE["overall_yearly_counts"]
    assert sum(yearly.values()) + coverage["undated_or_invalid_records"] == len(registry.df_all)

    for frame, expected in [
        (registry.df_datasets, 1333),
        (registry.df_institutions, 1334),
        (thematic.df_thematic_projects, 1343),
    ]:
        record_units = frame.drop_duplicates(RECORD_KEY)
        assert record_units[RECORD_KEY].nunique() == expected
        assert record_units.groupby("Year").size().sum() == expected


def test_all_years_matches_prechange_numeric_baseline_exactly():
    source_path = ROOT / BASELINE["contract"]["source_path"]
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == BASELINE["contract"]["source_sha256"]
    bounds = year_range(registry.df_all)
    selected = filter_records_by_year(registry.df_all, bounds.value, bounds)
    assert selected[RECORD_KEY].tolist() == registry.df_all[RECORD_KEY].tolist()

    overall = build_overall_figures(bounds.value)
    datasets = build_dataset_demand_figures(
        10, None, "ALL", "count", COLLECTION_VIEW_INDIVIDUAL,
    )
    institutions = (
        make_institution_bar(registry.df_institutions, 10),
        make_institution_trend(registry.df_institutions, 8, registry.PARTIAL_YEAR_INFO),
    )
    curve = adoption_curve_table(
        "year", selected_products=FLAGSHIP_PRODUCTS, collection_view="grouped",
    )
    summary = product_summary_table(
        selected_products=FLAGSHIP_PRODUCTS, collection_view="grouped",
    )
    observed = {
        "overall_yearly": _sha256_payload(_figure_data(overall[0])),
        "overall_quarterly": _sha256_payload(_figure_data(overall[1])),
        "overall_srs": _sha256_payload(_figure_data(overall[2])),
        "datasets_top10": _sha256_payload(_figure_data(datasets[0])),
        "datasets_trend": _sha256_payload(_figure_data(datasets[1])),
        "datasets_provider": _sha256_payload(_figure_data(datasets[2])),
        "institutions_top10": _sha256_payload(_figure_data(institutions[0])),
        "institutions_trend_top8": _sha256_payload(_figure_data(institutions[1])),
        "uptake_curve": _sha256_payload(curve.to_dict("records")),
        "uptake_exposure_bar": _sha256_payload(_figure_data(make_exposure_rate_bar(summary))),
        "uptake_summary_table": _sha256_payload(summary.to_dict("records")),
    }
    assert observed == BASELINE["default_numeric_output_sha256"]

    aggregates = thematic.build_thematic_aggregates(thematic.df_thematic_projects)
    assert aggregates["THEMATIC_PROJECT_COUNT"] == BASELINE["headlines"]["classified_records"]
    assert aggregates["LATENT_NO_LINKAGE_COUNT"] == BASELINE["headlines"]["latent_no_linkage"]
    for name, expected_hash in BASELINE["thematic_numeric_table_sha256"].items():
        assert _sha256_payload(aggregates[name].to_dict("split")) == expected_hash


def test_2024_selection_filters_before_expansion_and_combines_with_other_filters():
    bounds = year_range(registry.df_all)
    ids = selected_record_ids(registry.df_all, [2024, 2024], bounds)
    assert len(ids) == 236
    assert registry.df_all.loc[registry.df_all[RECORD_KEY].isin(ids), "Project ID"].nunique() == 234

    selected_datasets = filter_related_by_record_ids(registry.df_datasets, ids)
    selected_institutions = filter_related_by_record_ids(registry.df_institutions, ids)
    selected_thematic = filter_related_by_record_ids(thematic.df_thematic_projects, ids)
    assert selected_datasets[RECORD_KEY].nunique() == 236
    assert selected_institutions[RECORD_KEY].nunique() == 233
    assert selected_thematic[RECORD_KEY].nunique() == 236

    aggregates = thematic.build_thematic_aggregates(selected_thematic)
    assert aggregates["df_thematic_a_totals"]["count"].sum() == 319
    assert aggregates["df_thematic_c_totals"]["count"].sum() == 261
    assert aggregates["THEMATIC_TAGGED_COUNT"] == 42
    assert aggregates["LATENT_NO_LINKAGE_COUNT"] == 140

    provider = "Office for National Statistics (ONS)"
    display, _ = _get_enriched_register_display_df(
        None, "ALL", provider, "ALL", "ALL", "ALL", "ALL", "ALL", "ALL",
        "ALL", "ALL", "ALL", "ALL", "ALL", ids,
    )
    provider_ids = set(
        registry.df_datasets.loc[
            registry.df_datasets["provider"].eq(provider), RECORD_KEY
        ]
    )
    assert len(display) == len(set(ids) & provider_ids)
    assert len(display) < len(ids)
    assert "236 selected projects" in portfolio_filter_summary([2024, 2024])

    from dashboard.app import app

    download = app.callback_map["enriched-download-csv.data"]["callback"].__wrapped__(
        1,
        None,
        *(["ALL"] * 13),
        [2019, 2026],
        2019,
        2026,
        [2024, 2024],
    )
    exported = pd.read_csv(StringIO(download["content"]))
    exported_years = pd.to_datetime(
        exported[DATE_FIELD], errors="raise",
    ).dt.year.unique().tolist()
    assert len(exported) == 236
    assert exported_years == [2024]


def test_zero_match_is_explicit_and_reset_value_restores_full_population():
    figures = build_overall_figures([2030, 2030])
    for figure in figures:
        assert any(
            "No projects match" in str(annotation.text)
            for annotation in figure.layout.annotations or []
        )
    assert "No selected projects" in portfolio_filter_summary([2030, 2030])
    bounds = year_range(registry.df_all)
    assert len(filter_records_by_year(registry.df_all, bounds.value, bounds)) == 1343


def test_every_portfolio_output_callback_depends_on_the_global_year_selection():
    from dashboard.app import app

    expected_outputs = {
        "overall-yearly-chart", "overall-quarterly-chart", "overall-srs-chart",
        "datasets-topn-chart", "datasets-trend-chart", "datasets-provider-chart",
        "institutions-bar-chart", "institutions-trend-chart",
        "uptake-adoption-curves", "uptake-exposure-rate-bar", "uptake-adoption-summary-table",
        "thematic-domain-totals", "thematic-purpose-totals", "thematic-domain-trend",
        "thematic-purpose-trend", "thematic-cross-domain-purpose",
        "thematic-domain-cooccurrence", "thematic-tag-trend",
        "thematic-covid-tag-domain", "thematic-demographic-tag-domain",
        "thematic-latent-demand", "deterministic-record-linkage-distribution",
        "deterministic-record-linkage-trend", "deterministic-domain-linkage-breakdown",
        "deterministic-researcher-sector-distribution",
        "deterministic-researcher-sector-cooccurrence", "deterministic-unit-distribution",
        "deterministic-unit-trend", "deterministic-collection-method-distribution",
        "deterministic-collection-method-trend",
        "deterministic-temporal-structure-distribution",
        "deterministic-temporal-structure-trend", "thematic-project-count",
        "thematic-tagged-summary", "thematic-latent-demand-summary",
        "enriched-register-table", "enriched-browse-count", "enriched-download-csv",
    }
    covered = set()
    for callback_key, metadata in app.callback_map.items():
        dependencies = [*metadata.get("inputs", []), *metadata.get("state", [])]
        if not any(item.get("id") == "portfolio-accreditation-year-filter" for item in dependencies):
            continue
        covered.update(
            output_id for output_id in expected_outputs
            if output_id in callback_key
        )
    assert covered == expected_outputs

    layout_text = str(build_analysis_tab().to_plotly_json())
    assert "indicative rather than definitive" in layout_text
    assert "Indicative — mixed analytical layers." in layout_text
