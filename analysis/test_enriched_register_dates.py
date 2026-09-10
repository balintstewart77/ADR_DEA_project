"""Enriched Register date sorting, year selection, and CSV regression checks."""

from io import StringIO
import re
from unittest.mock import ANY, patch

import pandas as pd
import pytest
from dash import Dash

from dashboard.callbacks import thematic as callbacks
from dashboard.layout.analysis import thematic as layout
from analysis.test_dashboard_date_provenance import _find_component, _text_values


FILTERS = (None, *(["ALL"] * 13))


@pytest.fixture
def registered():
    app = Dash(__name__)
    callbacks.register(app)
    table_specs = [v for k, v in app.callback_map.items() if "enriched-register-table.data" in k]
    assert len(table_specs) == 1
    return (
        table_specs[0]["callback"].__wrapped__,
        app.callback_map["enriched-download-csv.data"]["callback"].__wrapped__,
        table_specs[0],
        app.callback_map["enriched-download-csv.data"],
    )


@pytest.fixture
def display():
    return pd.DataFrame({
        "Record ID": [f"record-{index}" for index in range(6)],
        "Project ID": ["repeat", "repeat", "third", "missing", "bad", "null"],
        "Title": ["Unchanged title"] * 6,
        "Accreditation Date": ["01 Dec 2023", "15 Feb 2023", "01 Jan 2024", "", "not-a-date", None],
    })


def test_iso_sorting_blanks_and_other_columns(registered, display):
    with patch.object(callbacks, "_get_enriched_register_display_df", return_value=(display, "old count")):
        records, _, count = registered[0](
            *FILTERS, 20, [2023, 2024], callbacks._YEAR_RANGE.value, [], 2023, 2024,
        )
    dates = [r["Accreditation Date"] for r in records]
    assert dates[3:] == ["", "", ""]
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates[:3])
    assert sorted(dates[:3]) == ["2023-02-15", "2023-12-01", "2024-01-01"]
    assert sorted(dates[:3], reverse=True) == ["2024-01-01", "2023-12-01", "2023-02-15"]
    assert sorted(display["Accreditation Date"][:2]) != ["15 Feb 2023", "01 Dec 2023"]
    for column in ("Project ID", "Title"):
        assert [r[column] for r in records] == list(display[column])
    assert count == "Showing 6 accreditation records"
    assert display["Accreditation Date"].iloc[0] == "01 Dec 2023"


@pytest.mark.parametrize("reset", [[2023, 2024], [2024, 2023], None, [], [2023], [2023, 2024, 2025], ["bad", 2024]])
def test_inclusive_narrowing_widening_and_reset(registered, display, reset):
    with patch.object(callbacks, "_get_enriched_register_display_df", return_value=(display, "old count")):
        lower, _, count = registered[0](*FILTERS, 20, [2023, 2023], callbacks._YEAR_RANGE.value, [], 2023, 2024)
        upper, _, singular = registered[0](*FILTERS, 20, [2024, 2024], callbacks._YEAR_RANGE.value, [], 2023, 2024)
        restored, _, _ = registered[0](*FILTERS, 20, reset, callbacks._YEAR_RANGE.value, [], 2023, 2024)
        empty, _, empty_count = registered[0](*FILTERS, 20, [2022, 2022], callbacks._YEAR_RANGE.value, [], 2023, 2024)
    assert [r["Accreditation Date"] for r in lower] == ["2023-12-01", "2023-02-15"]
    assert [r["Accreditation Date"] for r in upper] == ["2024-01-01"]
    assert len(restored) == len(display)
    assert count == "Showing 2 accreditation records"
    assert singular == "Showing 1 accreditation record"
    assert empty == [] and empty_count == "Showing 0 accreditation records"


def test_global_bounds_and_complete_native_pages(registered, display):
    subset = pd.concat([display.iloc[[0]]] * 25 + [display.iloc[[3, 4]]], ignore_index=True)
    subset["Record ID"] = [f"bulk-{index}" for index in range(len(subset))]
    filters = ("search", "dataset", "provider", "institution", "tre", "domain", "2",
               "purpose", "tag", "linkage", "collection", "temporal", "unit", "sector")
    with patch.object(callbacks, "_get_enriched_register_display_df", return_value=(subset, "old count")) as getter:
        records, page, count = registered[0](
            *filters, 10, [2023, 2023], callbacks._YEAR_RANGE.value, [], 2019, 2026,
        )
        getter.assert_called_once_with(*filters, ANY, include_record_id=True)
        restored, _, _ = registered[0](
            *filters, 10, [2019, 2026], callbacks._YEAR_RANGE.value, [], 2019, 2026,
        )
    assert len(records) == 25 > page == 10
    assert count == "Showing 25 accreditation records"
    assert len(restored) == 27


@pytest.mark.parametrize("years, expected", [([2023, 2023], 2), ([2024, 2024], 1), ([2023, 2024], 6), (None, 6)])
def test_download_range_filters_and_presentation(registered, display, years, expected):
    filters = ("search", "dataset", "provider", "institution", "tre", "domain", "2",
               "purpose", "tag", "linkage", "collection", "temporal", "unit", "sector")
    with (
        patch.object(callbacks, "_get_enriched_register_display_df", return_value=(display, "old count")) as getter,
        patch.object(callbacks, "_csv_date_stamp", return_value="2026-09-06"),
    ):
        result = registered[1](
            1, *filters, years, 2023, 2024, callbacks._YEAR_RANGE.value,
        )
        getter.assert_called_once_with(*filters, ANY)
    csv = pd.read_csv(StringIO(result["content"]), keep_default_na=False)
    assert len(csv) == expected
    assert list(csv.columns) == list(display.columns)
    assert result["filename"] == "dea-enriched-register-2026-09-06.csv"
    if years == [2023, 2023]:
        assert list(csv["Accreditation Date"]) == ["01 Dec 2023", "15 Feb 2023"]
    elif years == [2024, 2024]:
        assert list(csv["Accreditation Date"]) == ["01 Jan 2024"]
    else:
        assert list(csv["Accreditation Date"]) == list(display["Accreditation Date"].fillna(""))


def test_real_search_composes_with_year_and_download(registered):
    full, _ = callbacks._get_enriched_register_display_df(*FILTERS)
    dates = pd.to_datetime(full["Accreditation Date"], format="%d %b %Y")
    bounds = [int(dates.min().year), int(dates.max().year)]
    year = int(dates.iloc[0].year)
    filters = (full["Project ID"].iloc[0], *FILTERS[1:])
    searched, _ = callbacks._get_enriched_register_display_df(*filters)
    selected = searched.loc[pd.to_datetime(searched["Accreditation Date"], format="%d %b %Y").dt.year.eq(year)]
    assert 0 < len(selected) < len(full)
    records, _, count = registered[0](
        *filters, 10, [year, year], callbacks._YEAR_RANGE.value, [], *bounds,
    )
    expected = selected.copy()
    expected["Accreditation Date"] = pd.to_datetime(expected["Accreditation Date"], format="%d %b %Y").dt.strftime("%Y-%m-%d")
    assert [
        {column: row[column] for column in expected.columns}
        for row in records
    ] == expected.to_dict("records")
    assert count == f"Showing {len(selected):,} accreditation record{'s' if len(selected) != 1 else ''}"
    downloaded = registered[1](
        1, *filters, [year, year], *bounds, callbacks._YEAR_RANGE.value,
    )
    assert downloaded["content"] == selected.to_csv(index=False)
    restored, _, _ = registered[0](
        *FILTERS, 10, None, callbacks._YEAR_RANGE.value, [], *bounds,
    )
    assert len(restored) == len(full) > 10


def test_layout_settings_global_bounds_help_and_registration(registered):
    tab = layout.build_thematic_tab()
    dates = pd.to_datetime(
        callbacks.df_all["Accreditation Date"], format="%d %b %Y", errors="coerce",
    )
    slider = _find_component(tab, "enriched-accreditation-year-filter")
    assert slider.value == [int(dates.min().year), int(dates.max().year)]
    assert [slider.min, slider.max] == slider.value
    assert slider.step == 1 and slider.allowCross is False
    assert slider.marks == {year: str(year) for year in range(slider.min, slider.max + 1)}
    text = " ".join(_text_values(tab))
    assert "Accreditation year" in text
    assert "Records without a usable accreditation date" in text
    props = _find_component(tab, "enriched-register-table").to_plotly_json()["props"]
    assert props["sort_action"] == "custom" and props["filter_action"] == "none"
    assert props["page_size"] == 20
    assert all(prop not in props for prop in ("sort_mode", "page_action", "data"))
    year_id = "enriched-accreditation-year-filter"
    assert {"id": year_id, "property": "value"} in registered[2]["inputs"]
    assert {"id": "enriched-register-table", "property": "sort_by"} in registered[2]["inputs"]
    for prop in ("min", "max"):
        assert {"id": year_id, "property": prop} in registered[2]["state"]
    for prop in ("value", "min", "max"):
        assert {"id": year_id, "property": prop} in registered[3]["state"]
