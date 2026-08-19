"""Regression tests for the observed DEA-register uptake measure."""

from pathlib import Path

import pandas as pd
import yaml

from dashboard.charts.uptake import make_adoption_curves, make_exposure_rate_bar
from dashboard.data import uptake
from dashboard.layout.analysis.uptake import build_adoption_summary_table


def test_product_exposure_starts_at_first_accredited_use_not_reference_availability():
    summary = uptake.product_summary_table(collection_view="individual").set_index("product")
    earlier_reference_dates = []

    for product in uptake.LINKED_PRODUCTS:
        canonical = product["canonical"]
        first_use = uptake._first_seen_by_product.get(canonical, pd.NaT)
        if pd.isna(first_use):
            continue
        row = summary.loc[canonical]
        first_use = pd.Timestamp(first_use)
        exposure = uptake._exposure_years(first_use)

        assert row["exposure_start"] == first_use
        assert row["first_use"] == uptake._quarter_label(first_use)
        assert row["exposure_years"] == round(exposure, 1)
        assert row["projects_per_exposure_year"] == round(
            row["total_projects"] / exposure, 1
        )
        if product["curated_date"] is not None and product["curated_date"] < first_use:
            earlier_reference_dates.append(canonical)
            assert row["exposure_start"] != product["curated_date"]

    # The test covers real products with earlier externally curated dates, not
    # merely the no-metadata path.
    assert earlier_reference_dates


def test_grouped_collection_exposure_uses_earliest_member_first_use():
    individual = uptake.product_summary_table(collection_view="individual")
    grouped = uptake.product_summary_table(collection_view="grouped")

    for collection in ("Data First", "Wage and Employment Dynamics"):
        members = individual[individual["collection_label"] == collection]
        assert len(members) > 1
        expected_start = members["exposure_start"].dropna().min()
        actual = grouped.loc[grouped["product"] == collection, "exposure_start"].iloc[0]
        assert actual == expected_start


def test_adoption_curves_have_no_period_before_first_accredited_use():
    selected = [
        "MoJ Data First Crown Court Defendant",
        "MoJ Data First Magistrates' Court Defendant",
        "Annual Survey of Hours and Earnings linked to Census 2011",
        "Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment",
    ]
    for granularity in ("year", "quarter"):
        for collection_view in ("individual", "grouped"):
            curve = uptake.adoption_curve_table(
                granularity,
                selected_products=selected,
                collection_view=collection_view,
            )
            assert not curve.empty
            for line_id, line in curve.groupby("line_id", sort=False):
                products = list(line["product"].iloc[0].split("; "))
                expected_start = uptake._line_start_for_products(products, granularity)
                assert line["period_date"].min() >= expected_start, line_id

            figure = make_adoption_curves(
                curve,
                granularity=granularity,
                collection_view=collection_view,
            ).to_plotly_json()
            annotation_text = " ".join(
                str(annotation.get("text", ""))
                for annotation in figure["layout"].get("annotations", [])
            )
            assert "availability" not in annotation_text.lower()
            assert "first accredited use" in annotation_text.lower()


def test_adoption_summary_hides_availability_and_lag_presentation():
    table = build_adoption_summary_table(
        uptake.product_summary_table(collection_view="grouped")
    )
    column_names = [str(column["name"]) for column in table.columns]
    rendered = " ".join(column_names).lower()

    for obsolete in (
        "availability",
        "adoption lag",
        "announcement -> first dea-route use",
        "delivery/governance lag",
        "bounded; announced",
        "n/a (bounded)",
    ):
        assert obsolete not in rendered
    assert "First accredited use" in column_names
    assert "Exposure (years)" in column_names
    assert "Projects / exposure-year" in column_names


def test_reference_availability_and_announcement_metadata_are_preserved():
    reference_path = Path("analysis/register_reference.yaml")
    reference = yaml.safe_load(reference_path.read_text(encoding="utf-8"))
    products = reference["linked_products"]

    assert any("availability_date" in product for product in products)
    assert any("availability_basis" in product for product in products)
    assert any("availability_source" in product for product in products)
    assert any("availability_announced" in product for product in products)
    assert any("availability_announced_source" in product for product in products)
    assert any("availability_note" in product for product in products)


def test_exposure_rate_chart_wraps_long_collection_labels_without_changing_hover_data():
    summary = uptake.product_summary_table(collection_view="grouped")
    figure = make_exposure_rate_bar(summary).to_plotly_json()
    trace = figure["data"][0]
    labels = list(trace["y"])
    tick_text = dict(zip(figure["layout"]["yaxis"]["tickvals"], figure["layout"]["yaxis"]["ticktext"]))

    assert "Wage and Employment Dynamics" in labels
    assert "Agricultural Research Collection" in labels
    assert tick_text["Wage and Employment Dynamics"] == "Wage and Employment<br>Dynamics"
    assert tick_text["Agricultural Research Collection"] == "Agricultural Research<br>Collection"
    assert figure["layout"]["yaxis"]["automargin"] is True
    assert any(
        row[0] == "Wage and Employment Dynamics" for row in trace["customdata"]
    )
    assert any(
        row[0] == "Agricultural Research Collection" for row in trace["customdata"]
    )
