from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dash import no_update
from dash.development.base_component import Component
from dash._callback_context import context_value
from dash._utils import AttributeDict

from dashboard.callbacks import thematic as callbacks
from dashboard.callbacks.thematic import _enriched_table_records
from dashboard.data import thematic
from dashboard.data.registry import df_all
from dashboard.data.filtering import _apply_register_filters
from dashboard.layout.analysis import build_analysis_tab
from dashboard.layout.analysis.thematic import ENRICHED_PREVIEW_COLUMNS


FILTERS = (None, *(["ALL"] * 13))


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


def _table_callback():
    from dashboard.app import app

    matches = [
        spec for key, spec in app.callback_map.items()
        if "enriched-register-table.rowData" in key
    ]
    assert len(matches) == 1
    return matches[0]["callback"].__wrapped__, matches[0]


def _detail_callback():
    from dashboard.app import app

    key = next(
        key for key in app.callback_map
        if "enriched-record-detail-modal.is_open" in key
    )
    return app.callback_map[key]["callback"].__wrapped__, app.callback_map[key]


def _run_detail_callback(trigger, value, table_rows, selected_record_id=None):
    """Run the detail callback as Dash would for one triggering input."""
    callback, _ = _detail_callback()
    cell = value if trigger == "enriched-register-table.cellClicked" else None
    view = value if trigger == "enriched-register-view.data" else None
    token = context_value.set(AttributeDict(triggered_inputs=[{
        "prop_id": trigger,
        "value": value,
    }]))
    # The modal looks records up server-side; serve this test's rows instead.
    lookup = {row["id"]: row for row in table_rows}
    try:
        with patch.object(callbacks, "_enriched_records_by_id", return_value=lookup):
            return callback(cell, None, view, selected_record_id)
    finally:
        context_value.reset(token)


def _run_table(display):
    callback, _ = _table_callback()
    bounds = callbacks._YEAR_RANGE
    with patch.object(
        callbacks,
        "_get_enriched_register_display_df",
        return_value=(display.copy(), "old count"),
    ):
        result = callback(*FILTERS, [2023, 2024], bounds.value, 2023, 2024)
    return result[:2]


def _column_def(column_id):
    table = _component_by_id(build_analysis_tab(), "enriched-register-table")
    return next(column for column in table.columnDefs if column["colId"] == column_id)


def _fixture_rows():
    return pd.DataFrame([
        {
            "Record ID": 'record/alpha"<&',
            "Project ID": "repeated-project",
            "Title": 'Zulu title "<&',
            "Accreditation Date": "01 Dec 2023",
            "substantive_domain_count": 10,
            "rationale": (
                "Zulu rationale tied only to record alpha. "
                + "Further unchanged evidence. " * 8
                + "<script>not executable</script>"
            ),
        },
        {
            "Record ID": "record/beta",
            "Project ID": "repeated-project",
            "Title": "Alpha title",
            "Accreditation Date": "15 Feb 2023",
            "substantive_domain_count": 2,
            "rationale": "Alpha rationale.",
        },
        {
            "Record ID": "record/gamma",
            "Project ID": "missing-rationale",
            "Title": "Middle title",
            "Accreditation Date": "01 Jan 2024",
            "substantive_domain_count": None,
            "rationale": None,
        },
    ])


def test_nonempty_and_missing_rationales_are_presentational_only_and_escaped():
    source = _fixture_rows()
    records = _enriched_table_records(source)
    by_id = {row["id"]: row for row in records}

    long_row = by_id['record/alpha"<&']
    assert long_row["rationale"] == source.iloc[0]["rationale"]
    assert '<div class="rationale-cell"' in long_row["rationale_display"]
    assert 'data-record-id="record/alpha&quot;&lt;&amp;"' in long_row["rationale_display"]
    assert 'data-overflow="unknown"' in long_row["rationale_display"]
    assert "Read more" in long_row["rationale_display"]
    assert "Show less" in long_row["rationale_display"]
    assert (
        "Toggle full model-generated rationale for Zulu title &quot;&lt;&amp;"
        in long_row["rationale_display"]
    )
    assert "<script>" not in long_row["rationale_display"]
    assert "&lt;script&gt;not executable&lt;/script&gt;" in long_row["rationale_display"]

    # Fit is decided in the browser, so even short text remains accessible until measured.
    short_row = by_id["record/beta"]
    assert short_row["rationale"] == "Alpha rationale."
    assert '<details class="rationale-details"' in short_row["rationale_display"]
    assert 'data-overflow="unknown"' in short_row["rationale_display"]

    missing_row = by_id["record/gamma"]
    assert pd.isna(missing_row["rationale"])
    assert missing_row["rationale_display"] == '<span class="rationale-short">—</span>'


def test_multiline_long_and_boundary_text_all_reach_rendered_measurement():
    texts = [
        "one\ntwo\nthree\nfour",
        "A long single-line rationale " + ("with evidence " * 30),
        "Boundary text " * 6,
    ]
    source = pd.DataFrame([
        {
            "Record ID": f"measurement-{index}",
            "Project ID": f"measurement-{index}",
            "Title": f"Measurement {index}",
            "rationale": text,
        }
        for index, text in enumerate(texts)
    ])
    records = _enriched_table_records(source)

    assert len(texts[0]) < 120
    for record, source_text in zip(records, texts):
        assert record["rationale"] == source_text
        assert source_text in record["rationale_display"]
        assert '<details class="rationale-details" data-overflow="unknown">' in record["rationale_display"]


def test_rows_keep_full_source_values_beside_their_previews():
    records, count = _run_table(_fixture_rows())
    assert count == "Showing 3 accreditation records"
    assert [row["id"] for row in records] == ['record/alpha"<&', "record/beta", "record/gamma"]
    assert records[0]["rationale"].endswith("<script>not executable</script>")
    assert records[0]["Title"] == 'Zulu title "<&'
    assert pd.isna(records[2]["substantive_domain_count"])


def test_preview_and_rationale_columns_sort_on_the_full_source_value():
    # The grid sorts in the browser (tests/test_dashboard_tables_browser.py),
    # on each column's field. A preview column's field is its source value.
    for display_column, source_column in ENRICHED_PREVIEW_COLUMNS.items():
        column = _column_def(display_column)
        assert column["field"] == source_column
        assert column["cellRenderer"] == "ServerHtml"
    rationale = _column_def("rationale_display")
    assert (rationale["field"], rationale["cellRenderer"]) == ("rationale", "ServerHtml")
    assert _column_def("details_action")["sortable"] is False
    for plain in ("Project ID", "Accreditation Date", "record_linkage", "substantive_domain_count"):
        assert _column_def(plain)["field"] == plain
        assert "cellRenderer" not in _column_def(plain)


def test_search_scope_is_enriched_only_and_uses_raw_full_text():
    source = pd.DataFrame([
        {
            "Record ID": "record/deep",
            "Project ID": "project/deep",
            "Title": "Ordinary title",
            "Researchers": "Ordinary researcher",
            "rationale": "Opening words. " + ("filler " * 40) + "deep-only-needle",
        },
        {
            "Record ID": "record/other",
            "Project ID": "project/other",
            "Title": "Another title",
            "Researchers": "Another researcher",
            "rationale": "No matching content",
        },
    ])
    args = (source, "deep-only-needle", "ALL", "ALL", "ALL", "ALL")
    assert _apply_register_filters(*args).empty
    enriched = _apply_register_filters(*args, include_rationale_search=True)
    assert enriched["Record ID"].tolist() == ["record/deep"]
    assert _apply_register_filters(
        source, "Read more", "ALL", "ALL", "ALL", "ALL",
        include_rationale_search=True,
    ).empty


def test_grid_shows_server_html_and_registers_the_page_change_callback():
    from dashboard.app import app

    layout = build_analysis_tab()
    table = _component_by_id(layout, "enriched-register-table")
    assert table.getRowId == "params.data.id"
    assert table.defaultColDef["comparator"] == {"function": "nullsLast"}
    assert _component_by_id(layout, "enriched-register-view") is not None

    _, table_spec = _table_callback()
    assert not any(item["id"] == "enriched-register-table" for item in table_spec["inputs"])
    page_changed = next(
        item for item in app._callback_list
        if item["output"] == "enriched-register-view.data"
    )
    assert page_changed["clientside_function"] == {
        "namespace": "enrichedRegister",
        "function_name": "pageChanged",
    }
    assert [(item["id"], item["property"]) for item in page_changed["inputs"]] == [
        ("enriched-register-table", "virtualRowData"),
        ("enriched-register-table", "paginationInfo"),
    ]

    assets = Path(__file__).parents[1] / "dashboard/assets"
    rationale = (assets / "rationale_overflow.js").read_text()
    assert "ResizeObserver" in rationale and "MutationObserver" in rationale
    assert "setInterval" not in rationale and "addEventListener(\"resize\"" not in rationale
    grid_functions = (assets / "dash_ag_grid_functions.js").read_text()
    assert "functions.nullsLast" in grid_functions
    assert "components.ServerHtml" in grid_functions


def test_csv_export_keeps_full_rationale_and_existing_order():
    from dashboard.app import app

    long_rows = thematic.df_thematic_projects[
        thematic.df_thematic_projects["rationale"].astype("string").str.len().gt(180)
    ]
    target = long_rows.iloc[0]
    original = str(target["rationale"])
    matching, _ = callbacks._get_enriched_register_display_df(
        original, *(["ALL"] * 13),
    )
    assert original in matching["rationale"].tolist()
    callback = app.callback_map["enriched-download-csv.data"]["callback"].__wrapped__
    bounds = callbacks._YEAR_RANGE
    result = callback(
        1,
        original,
        *(["ALL"] * 13),
        bounds.value,
        bounds.minimum,
        bounds.maximum,
        bounds.value,
    )
    exported = pd.read_csv(StringIO(result["content"]))
    assert original in exported["rationale"].tolist()
    assert "rationale_display" not in exported.columns
    assert "Record ID" not in exported.columns
    assert "model-generated rationale" in _enriched_table_records(
        pd.DataFrame([{
            "Record ID": "annotation",
            "Project ID": "annotation",
            "Title": "Annotated project",
            "rationale": original,
        }])
    )[0]["rationale_display"]


def test_previews_reuse_existing_entry_parsers_and_keep_raw_values_for_sorting():
    dataset_value = "ONS: Alpha Dataset, Beta Dataset, Gamma Dataset, Delta Dataset"
    rows = pd.DataFrame([
        {
            "Record ID": "record/zulu",
            "Project ID": "duplicate-project",
            "Title": "Zulu " + ("title " * 24),
            "Researchers": "Zoe " + ("unstructured affiliation text " * 8),
            "Datasets Used": dataset_value,
            "researcher_sectors": "Academic; Government; Commercial",
            "rationale": "A rationale",
        },
        {
            "Record ID": "record/alpha",
            "Project ID": "duplicate-project",
            "Title": "Alpha " + ("title " * 24),
            "Researchers": "Ann " + ("unstructured affiliation text " * 8),
            "Datasets Used": "ONS: One Dataset",
            "researcher_sectors": "Academic",
            "rationale": "B rationale",
        },
    ])

    records = _enriched_table_records(rows)
    zulu = next(record for record in records if record["id"] == "record/zulu")
    assert zulu["Datasets Used"] == dataset_value
    assert "Alpha Dataset; Beta Dataset" in zulu["Datasets Used_display"]
    assert "+2 more entries" in zulu["Datasets Used_display"]
    assert "Academic; Government" in zulu["researcher_sectors_display"]
    assert "+1 more entries" in zulu["researcher_sectors_display"]
    assert "View full value" in zulu["Researchers_display"]
    assert "more researchers" not in zulu["Researchers_display"]
    assert "View full value" in zulu["Title_display"]
    assert 'data-record-id="record/zulu"' in zulu["details_action"]
    # The full values stay in the row for the grid to sort on.
    assert zulu["Title"] == rows.loc[0, "Title"]
    assert zulu["researcher_sectors"] == "Academic; Government; Commercial"


def test_preview_sort_uses_raw_value_when_the_truncated_previews_are_identical():
    shared_prefix = "A common preview prefix " * 6
    rows = pd.DataFrame([
        {
            "Record ID": "record/zulu",
            "Project ID": "project/zulu",
            "Title": shared_prefix + "Zulu full value",
        },
        {
            "Record ID": "record/alpha",
            "Project ID": "project/alpha",
            "Title": shared_prefix + "Alpha full value",
        },
    ])
    records = _enriched_table_records(rows)
    previews = [record["Title_display"] for record in records]
    assert previews[0].replace("record/zulu", "record") == previews[1].replace(
        "record/alpha", "record",
    )
    # The grid sorts the Title column on the full title, which differs.
    assert _column_def("Title_display")["field"] == "Title"
    assert sorted(record["Title"] for record in records)[0].endswith("Alpha full value")


def test_detail_callback_uses_record_id_not_duplicate_project_id_and_closes_out_of_view():
    records = _enriched_table_records(_fixture_rows())
    # Both rows share a Project ID; the grid reports the clicked row's Record ID.
    is_open, body, selected = _run_detail_callback(
        "enriched-register-table.cellClicked",
        {"colId": "details_action", "rowId": "record/beta", "rowIndex": 1},
        records,
    )
    assert is_open is True
    assert selected == "record/beta"
    text = " ".join(str(child) for child in body.children)
    assert "record/beta" in text
    assert "Alpha title" in text
    assert "Zulu rationale" not in text

    preview_click = _run_detail_callback(
        "enriched-register-table.cellClicked",
        {"colId": "Title_display", "rowId": 'record/alpha"<&', "rowIndex": 0},
        records,
    )
    assert preview_click[2] == 'record/alpha"<&'

    for cell in (
        {"colId": "Project ID", "rowId": "record/beta"},
        {"colId": "rationale_display", "rowId": "record/beta"},
        {"colId": "details_action", "rowId": "record/unknown"},
    ):
        assert _run_detail_callback(
            "enriched-register-table.cellClicked", cell, records,
        ) == (no_update, no_update, no_update)

    still_visible = _run_detail_callback(
        "enriched-register-view.data",
        {"recordIds": ["record/alpha", "record/beta"]},
        records,
        selected_record_id="record/beta",
    )
    assert still_visible == (no_update, no_update, no_update)
    left_page = _run_detail_callback(
        "enriched-register-view.data",
        {"recordIds": ["record/alpha"]},
        records,
        selected_record_id="record/beta",
    )
    assert left_page == (False, [], None)
    closed = _run_detail_callback(
        "enriched-record-detail-close.n_clicks", 1, records, selected_record_id="record/beta",
    )
    assert closed == (False, [], None)


def test_detail_layout_is_accessible_keyed_and_keeps_rationale_lifecycle():
    layout = build_analysis_tab()
    project_id = _column_def("Project ID")
    assert (project_id["pinned"], project_id["width"]) == ("left", 90)
    assert _column_def("details_action")["cellRenderer"] == "ServerHtml"
    assert _component_by_id(layout, "enriched-record-detail-modal") is not None
    assert _component_by_id(layout, "enriched-record-detail-close") is not None

    _, detail_spec = _detail_callback()
    assert [(item["id"], item["property"]) for item in detail_spec["inputs"]] == [
        ("enriched-register-table", "cellClicked"),
        ("enriched-record-detail-close", "n_clicks"),
        ("enriched-register-view", "data"),
    ]
    # The full table is never uploaded: only the clicked cell, the visible
    # Record IDs and the selected-record store travel with the detail callback.
    assert [(item["id"], item["property"]) for item in detail_spec["state"]] == [
        ("enriched-record-detail-record-id", "data"),
    ]

    asset = (Path(__file__).parents[1] / "dashboard/assets/enriched_record_detail.js").read_text()
    assert "Escape" in asset and "Enter" in asset
    assert "enriched-record-detail-close" in asset
    assert "focus" in asset


def test_detail_lookup_matches_the_table_row_for_a_real_record():
    callback, _ = _table_callback()
    bounds = callbacks._YEAR_RANGE
    records = callback(*FILTERS, bounds.value, bounds.value, *bounds.value)[0]
    lookup = callbacks._enriched_records_by_id()
    assert len(lookup) == len(records)
    for row in records[:5]:
        assert lookup[row["id"]] == row


def test_search_inputs_are_debounced():
    from dashboard.layout.explorer import build_explorer_tab

    assert _component_by_id(build_analysis_tab(), "enriched-search").debounce == 400
    assert _component_by_id(build_explorer_tab(), "browse-search").debounce == 400


def test_csv_export_keeps_full_dataset_value_when_table_uses_a_preview():
    from dashboard.app import app

    full_dataset_value = str(df_all.loc[
        df_all["Record ID"].astype(str).eq("2019/014"), "Datasets Used",
    ].iloc[0])
    assert len(full_dataset_value) > 96
    table_row = _enriched_table_records(pd.DataFrame([{
        "Record ID": "2019/014",
        "Project ID": "2019/014",
        "Datasets Used": full_dataset_value,
    }]))[0]
    assert "+7 more entries" in table_row["Datasets Used_display"]

    callback = app.callback_map["enriched-download-csv.data"]["callback"].__wrapped__
    bounds = callbacks._YEAR_RANGE
    result = callback(
        1,
        "2019/014",
        *( ["ALL"] * 13 ),
        bounds.value,
        bounds.minimum,
        bounds.maximum,
        bounds.value,
    )
    exported = pd.read_csv(StringIO(result["content"]))
    assert full_dataset_value in exported["Datasets Used"].tolist()
    assert not any(column.endswith("_display") for column in exported.columns)


def test_csv_export_keeps_full_researchers_value_when_its_preview_is_truncated():
    from dashboard.app import app

    full_researchers_value = str(df_all.loc[
        df_all["Record ID"].astype(str).eq("2019/015"), "Researchers",
    ].iloc[0])
    assert len(full_researchers_value) > 96
    table_row = _enriched_table_records(pd.DataFrame([{
        "Record ID": "2019/015",
        "Project ID": "2019/015",
        "Researchers": full_researchers_value,
    }]))[0]
    assert "View full value" in table_row["Researchers_display"]

    callback = app.callback_map["enriched-download-csv.data"]["callback"].__wrapped__
    bounds = callbacks._YEAR_RANGE
    result = callback(
        1,
        "2019/015",
        *( ["ALL"] * 13 ),
        bounds.value,
        bounds.minimum,
        bounds.maximum,
        bounds.value,
    )
    exported = pd.read_csv(StringIO(result["content"]))
    assert full_researchers_value in exported["Researchers"].tolist()
    assert not any(column.endswith("_display") for column in exported.columns)
