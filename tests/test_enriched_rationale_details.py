from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dash.development.base_component import Component
from dash._callback_context import context_value
from dash._utils import AttributeDict

from dashboard.callbacks import thematic as callbacks
from dashboard.callbacks.thematic import _enriched_table_records
from dashboard.data import thematic
from dashboard.data.registry import df_all
from dashboard.data.filtering import _apply_register_filters
from dashboard.layout.analysis import build_analysis_tab


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
        if "enriched-register-table.data" in key
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


def _run_detail_callback(
    active_cell,
    viewport_rows,
    table_rows,
    viewport_record_ids,
    selected_record_id=None,
    trigger="enriched-register-table.active_cell",
):
    callback, _ = _detail_callback()
    token = context_value.set(AttributeDict(triggered_inputs=[{
        "prop_id": trigger,
        "value": active_cell,
    }]))
    try:
        return callback(
            active_cell,
            None,
            viewport_rows,
            0,
            table_rows,
            viewport_record_ids,
            selected_record_id,
        )
    finally:
        context_value.reset(token)


def _run_table(display, sort_by=None, page_size=10):
    callback, _ = _table_callback()
    bounds = callbacks._YEAR_RANGE
    with patch.object(
        callbacks,
        "_get_enriched_register_display_df",
        return_value=(display.copy(), "old count"),
    ):
        return callback(
            *FILTERS,
            page_size,
            [2023, 2024],
            bounds.value,
            sort_by or [],
            2023,
            2024,
        )


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


def test_rationale_sort_uses_raw_full_text_in_both_directions_across_pages():
    rows = []
    for index in range(25):
        reverse_key = 24 - index
        rows.append({
            "Record ID": f"record/{index:02d}",
            "Project ID": "repeated-project" if index < 2 else f"project/{index:02d}",
            "Title": f"Title {reverse_key:02d}",
            "Accreditation Date": "01 Jan 2024",
            "substantive_domain_count": index,
            "rationale": f"{reverse_key:02d} raw rationale " + ("evidence " * 20),
        })
    display = pd.DataFrame(rows)

    ascending, page_size, _ = _run_table(
        display,
        [{"column_id": "rationale_display", "direction": "asc"}],
    )
    descending, _, _ = _run_table(
        display,
        [{"column_id": "rationale_display", "direction": "desc"}],
    )

    assert len(ascending) == len(descending) == 25 > page_size == 10
    assert [row["id"] for row in ascending] == [
        f"record/{index:02d}" for index in range(24, -1, -1)
    ]
    assert [row["id"] for row in descending] == [
        f"record/{index:02d}" for index in range(25)
    ]
    for row in ascending:
        assert f'data-record-id="{row["id"]}"' in row["rationale_display"]


def test_sort_preserves_nulls_ties_numeric_titles_dates_and_multi_column_order():
    display = pd.DataFrame([
        {"Record ID": "r3", "Project ID": "repeat", "Title": "Beta", "Accreditation Date": "01 Dec 2023", "substantive_domain_count": 10, "rationale": "Same"},
        {"Record ID": "r1", "Project ID": "repeat", "Title": "Alpha", "Accreditation Date": "15 Feb 2023", "substantive_domain_count": 2, "rationale": "Same"},
        {"Record ID": "r2", "Project ID": "other", "Title": "Gamma", "Accreditation Date": "01 Jan 2024", "substantive_domain_count": None, "rationale": None},
        {"Record ID": "r4", "Project ID": "other", "Title": "Delta", "Accreditation Date": "20 Mar 2023", "substantive_domain_count": 2, "rationale": "Alpha"},
    ])

    rationale_asc, _, _ = _run_table(
        display, [{"column_id": "rationale_display", "direction": "asc"}],
    )
    rationale_desc, _, _ = _run_table(
        display, [{"column_id": "rationale_display", "direction": "desc"}],
    )
    assert [row["id"] for row in rationale_asc] == ["r4", "r3", "r1", "r2"]
    assert [row["id"] for row in rationale_desc] == ["r3", "r1", "r4", "r2"]

    expected = {
        "Title": ["r1", "r3", "r4", "r2"],
        "substantive_domain_count": ["r1", "r4", "r3", "r2"],
        "Accreditation Date": ["r1", "r4", "r3", "r2"],
    }
    for column_id, record_ids in expected.items():
        records, _, _ = _run_table(
            display, [{"column_id": column_id, "direction": "asc"}],
        )
        assert [row["id"] for row in records] == record_ids

    multiple, _, _ = _run_table(display, [
        {"column_id": "rationale_display", "direction": "asc"},
        {"column_id": "Title", "direction": "asc"},
    ])
    assert [row["id"] for row in multiple] == ["r4", "r1", "r3", "r2"]


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


def test_table_registers_custom_full_result_sort_and_lifecycle_callback():
    from dashboard.app import app

    layout = build_analysis_tab()
    table = _component_by_id(layout, "enriched-register-table")
    rationale_column = next(
        column for column in table.columns if column["id"] == "rationale_display"
    )
    assert rationale_column["presentation"] == "markdown"
    assert table.markdown_options == {"html": True}
    assert table.sort_action == "custom"
    assert table.page_current == 0
    assert _component_by_id(layout, "enriched-rationale-view-reset") is not None

    _, table_spec = _table_callback()
    assert {"id": "enriched-register-table", "property": "sort_by"} in table_spec["inputs"]
    reset = next(
        item for item in app._callback_list
        if item["output"] == "enriched-rationale-view-reset.data"
    )
    assert reset["clientside_function"] == {
        "namespace": "enrichedRationale",
        "function_name": "update",
    }
    assert {item["property"] for item in reset["inputs"]} == {
        "derived_viewport_data", "page_current", "sort_by",
    }

    asset = (
        Path(__file__).parents[1] / "dashboard/assets/rationale_overflow.js"
    ).read_text()
    assert "ResizeObserver" in asset and "MutationObserver" in asset
    assert "setInterval" not in asset and "addEventListener(\"resize\"" not in asset


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

    sorted_records = callbacks._sort_enriched_table_records(
        records, [{"column_id": "Title_display", "direction": "asc"}],
    )
    assert [record["id"] for record in sorted_records] == [
        "record/alpha", "record/zulu",
    ]


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
    assert [record["id"] for record in callbacks._sort_enriched_table_records(
        records, [{"column_id": "Title_display", "direction": "asc"}],
    )] == ["record/alpha", "record/zulu"]


def test_detail_callback_uses_record_id_not_duplicate_project_id_and_closes_out_of_view():
    display = _fixture_rows()
    records = _enriched_table_records(display)
    open_result = _run_detail_callback(
        {"row": 0, "column_id": "details_action"},
        [records[1]],
        records,
        ["record/beta"],
    )
    is_open, body, selected = open_result
    assert is_open is True
    assert selected == "record/beta"
    text = " ".join(str(child) for child in body.children)
    assert "record/beta" in text
    assert "Alpha title" in text
    assert "Zulu rationale" not in text

    close_result = _run_detail_callback(
        None,
        [records[0]],
        records,
        ["record/alpha"],
        selected_record_id="record/beta",
        trigger="enriched-register-table.derived_viewport_data",
    )
    assert close_result == (False, [], None)


def test_detail_layout_is_accessible_keyed_and_keeps_rationale_lifecycle():
    from dashboard.app import app

    layout = build_analysis_tab()
    table = _component_by_id(layout, "enriched-register-table")
    assert table.fixed_columns == {"headers": True, "data": 1}
    project_id_style = next(
        style for style in table.style_cell_conditional
        if style["if"]["column_id"] == "Project ID"
    )
    assert project_id_style["width"] == "90px"
    details_column = next(column for column in table.columns if column["id"] == "details_action")
    assert details_column["presentation"] == "markdown"
    assert _component_by_id(layout, "enriched-record-detail-modal") is not None
    assert _component_by_id(layout, "enriched-record-detail-close") is not None

    _, detail_spec = _detail_callback()
    assert {item["property"] for item in detail_spec["inputs"]} == {
        "active_cell", "n_clicks", "derived_viewport_data", "page_current",
    }
    assert [item["property"] for item in detail_spec["state"]] == [
        "data", "derived_viewport_row_ids", "data",
    ]

    asset = (Path(__file__).parents[1] / "dashboard/assets/enriched_record_detail.js").read_text()
    assert "Escape" in asset
    assert "enriched-record-detail-close" in asset
    assert "focus" in asset

    rationale_asset = (Path(__file__).parents[1] / "dashboard/assets/rationale_overflow.js").read_text()
    assert "ResizeObserver" in rationale_asset and "MutationObserver" in rationale_asset


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
