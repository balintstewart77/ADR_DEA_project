"""Visitor-facing dashboard date and provenance display checks."""

from collections.abc import Iterator
import json
import re
from unittest.mock import patch

import pandas as pd
from dash import Dash

from dashboard.data.registry import DATA_DATE, DATA_SOURCE_LABEL, PARTIAL_YEAR_INFO, df_all
from dashboard.layout.about import build_about_tab
from dashboard.layout.navbar import build_navbar


def _text_values(value) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _text_values(item)
    elif hasattr(value, "children"):
        yield from _text_values(value.children)


def test_public_coverage_date_is_computed_from_loaded_register_data():
    maximum = df_all["Accreditation Date"].max()
    assert DATA_DATE == maximum.strftime("%d %B %Y")
    assert PARTIAL_YEAR_INFO.note == (
        f"* {maximum.year} data covers Jan–{maximum.strftime('%b')} only"
    )


def test_public_provenance_uses_human_readable_source_not_internal_snapshot_path():
    navbar_text = " ".join(_text_values(build_navbar()))
    about_text = " ".join(_text_values(build_about_tab()))
    public_text = f"{navbar_text} {about_text}"

    assert DATA_SOURCE_LABEL in public_text
    assert DATA_DATE in public_text
    assert "register_snapshots/" not in public_text
    assert re.search(r"\b[0-9a-f]{64}\b", public_text, flags=re.IGNORECASE) is None
    assert "source file:" not in public_text.lower()
    assert "last updated" not in public_text.lower()


def test_footer_describes_data_coverage_using_the_loaded_data_date():
    from dashboard.app import app

    app_text = " ".join(_text_values(app.layout))
    assert f"Accreditation data through {DATA_DATE}" in app_text
    assert "last updated" not in app_text.lower()


def _find_component(component, component_id):
    if getattr(component, "id", None) == component_id:
        return component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            found = _find_component(child, component_id)
            if found is not None:
                return found
    elif children is not None:
        return _find_component(children, component_id)
    return None


def _browse_callback():
    from dashboard.callbacks import explorer as explorer_callbacks

    app = Dash(__name__)
    explorer_callbacks.register(app)
    spec = next(
        spec for callback_id, spec in app.callback_map.items()
        if "browse-table.data" in callback_id
    )
    return explorer_callbacks, spec["callback"]


def _download_callback():
    from dashboard.callbacks import explorer as explorer_callbacks

    app = Dash(__name__)
    explorer_callbacks.register(app)
    spec = next(
        spec for callback_id, spec in app.callback_map.items()
        if "browse-download-csv.data" in callback_id
    )
    return explorer_callbacks, spec["callback"]


def _run_browse_callback(
    display,
    accreditation_year_range,
    page_size=20,
    accreditation_year_min=2023,
    accreditation_year_max=2024,
    dataset_filter="ALL",
    provider_filter="ALL",
    institution_filter="ALL",
    tre_filter="ALL",
):
    explorer_callbacks, callback = _browse_callback()
    outputs = [
        {"id": "browse-table", "property": "data"},
        {"id": "browse-table", "property": "tooltip_data"},
        {"id": "browse-table", "property": "page_size"},
        {"id": "browse-count", "property": "children"},
    ]
    with patch.object(
        explorer_callbacks,
        "_get_browse_display_df",
        return_value=display,
    ) as display_getter:
        response = callback(
            dataset_filter, provider_filter, institution_filter, tre_filter, None,
            page_size, accreditation_year_range,
            accreditation_year_min, accreditation_year_max,
            outputs_list=outputs,
        )
    return json.loads(response)["response"], display_getter.call_args


def _browse_fixture():
    return pd.DataFrame([
        {"Project ID": "2023/001", "Accreditation Date": "01 Dec 2023"},
        {"Project ID": "2023/002", "Accreditation Date": "15 Feb 2023"},
        {"Project ID": "2024/001", "Accreditation Date": "01 Jan 2024"},
        {"Project ID": "2024/002", "Accreditation Date": ""},
        {"Project ID": "2024/003", "Accreditation Date": "not-a-date"},
    ])


def test_explorer_uses_iso_dates_for_native_chronological_sorting():
    response, _ = _run_browse_callback(_browse_fixture(), [2023, 2024])
    records = response["browse-table"]["data"]
    dates = [record["Accreditation Date"] for record in records]
    valid_dates = [value for value in dates if value]

    assert dates[-2:] == ["", ""]
    assert sorted(valid_dates) == ["2023-02-15", "2023-12-01", "2024-01-01"]
    assert sorted(valid_dates, reverse=True) == ["2024-01-01", "2023-12-01", "2023-02-15"]
    assert sorted(["01 Dec 2023", "15 Feb 2023"]) != ["15 Feb 2023", "01 Dec 2023"]


def test_explorer_accreditation_year_filter_is_inclusive_and_returns_complete_data():
    fixture = _browse_fixture()
    full_range, _ = _run_browse_callback(fixture.copy(), [2023, 2024])
    cleared, _ = _run_browse_callback(fixture.copy(), None)
    selected_2023, _ = _run_browse_callback(fixture.copy(), [2023, 2023])
    records_2023 = selected_2023["browse-table"]["data"]

    assert len(full_range["browse-table"]["data"]) == len(fixture)
    assert len(cleared["browse-table"]["data"]) == len(fixture)
    assert full_range["browse-count"]["children"] == "Showing 5 accreditation records"
    assert [record["Project ID"] for record in records_2023] == ["2023/001", "2023/002"]
    assert selected_2023["browse-count"]["children"] == "Showing 2 accreditation records"

    single_record, _ = _run_browse_callback(fixture.copy(), [2024, 2024])
    assert single_record["browse-count"]["children"] == "Showing 1 accreditation record"

    paged_fixture = pd.concat([fixture.iloc[:1]] * 25, ignore_index=True)
    paged, _ = _run_browse_callback(paged_fixture, [2023, 2023], page_size=10)
    assert len(paged["browse-table"]["data"]) == 25
    assert paged["browse-table"]["page_size"] == 10
    assert paged["browse-count"]["children"] == "Showing 25 accreditation records"


def test_explorer_year_filter_intersects_existing_server_side_filters():
    server_filtered = pd.DataFrame([
        {"Project ID": "2023/050", "Accreditation Date": "15 Feb 2023"},
        {"Project ID": "2024/050", "Accreditation Date": "01 Jan 2024"},
    ])
    response, filter_call = _run_browse_callback(
        server_filtered,
        [2023, 2023],
        dataset_filter="Dataset A",
        provider_filter="Provider A",
        institution_filter="Institution A",
        tre_filter="TRE A",
    )

    assert filter_call.args == (None, "Dataset A", "Provider A", "Institution A", "TRE A")
    assert [row["Project ID"] for row in response["browse-table"]["data"]] == ["2023/050"]


def test_explorer_download_respects_accreditation_year_range():
    explorer_callbacks, callback = _download_callback()
    fixture = _browse_fixture()
    with (
        patch.object(
            explorer_callbacks,
            "_get_browse_display_df",
            return_value=fixture,
        ),
        patch.object(explorer_callbacks.dcc, "send_data_frame", return_value={"content": "csv"}) as send,
    ):
        callback(
            1, None, "Dataset A", "Provider A", "Institution A", "TRE A",
            [2023, 2023], 2023, 2024,
            outputs_list={"id": "browse-download-csv", "property": "data"},
        )

    downloaded = send.call_args.args[0].__self__
    assert [row for row in downloaded["Project ID"]] == ["2023/001", "2023/002"]


def test_explorer_layout_keeps_native_table_behavior_and_derived_year_range():
    from dashboard.layout.explorer import build_explorer_tab

    layout = build_explorer_tab()
    table = _find_component(layout, "browse-table")
    year_filter = _find_component(layout, "browse-accreditation-year-filter")
    props = table.to_plotly_json()["props"]
    parsed_dates = pd.to_datetime(df_all["Accreditation Date"], errors="coerce")

    assert props["sort_action"] == "native"
    assert props["filter_action"] == "none"
    assert "page_action" not in props
    assert props["page_size"] == 20
    assert year_filter.value == [parsed_dates.min().year, parsed_dates.max().year]
    assert year_filter.allowCross is False
