from io import StringIO

import pandas as pd
from dash.development.base_component import Component

from dashboard.callbacks.thematic import (
    RATIONALE_PREVIEW_CHARACTER_LIMIT,
    _enriched_table_records,
)
from dashboard.data import registry, thematic
from dashboard.data.filtering import _apply_register_filters
from dashboard.layout.analysis import build_analysis_tab


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


def _fixture_rows():
    long_text = (
        "A long rationale tied only to record alpha. "
        + "Further unchanged evidence. " * 8
        + "<script>not executable</script>"
    )
    return pd.DataFrame([
        {
            "Record ID": "record/alpha",
            "Project ID": "repeated-project",
            "Title": "Zulu title",
            "rationale": long_text,
        },
        {
            "Record ID": "record/beta",
            "Project ID": "repeated-project",
            "Title": "Alpha title",
            "rationale": "Short rationale.",
        },
        {
            "Record ID": "record/gamma",
            "Project ID": "missing-rationale",
            "Title": "Middle title",
            "rationale": None,
        },
    ])


def test_long_short_and_missing_rationales_are_presentational_only():
    source = _fixture_rows()
    records = _enriched_table_records(source)
    by_id = {row["id"]: row for row in records}

    long_row = by_id["record/alpha"]
    assert long_row["rationale"] == source.iloc[0]["rationale"]
    assert len(long_row["rationale"]) > RATIONALE_PREVIEW_CHARACTER_LIMIT
    assert '<details class="rationale-details"' in long_row["rationale_display"]
    assert 'data-record-id="record/alpha"' in long_row["rationale_display"]
    assert "Read more" in long_row["rationale_display"]
    assert "Show less" in long_row["rationale_display"]
    assert "Toggle full model-generated rationale for Zulu title" in long_row["rationale_display"]
    assert "<script>" not in long_row["rationale_display"]
    assert "&lt;script&gt;not executable&lt;/script&gt;" in long_row["rationale_display"]

    short_row = by_id["record/beta"]
    assert short_row["rationale"] == "Short rationale."
    assert "rationale-short" in short_row["rationale_display"]
    assert "<details" not in short_row["rationale_display"]
    assert "Read more" not in short_row["rationale_display"]

    missing_row = by_id["record/gamma"]
    assert pd.isna(missing_row["rationale"])
    assert missing_row["rationale_display"] == '<span class="rationale-short">—</span>'


def test_record_association_survives_sorting_and_paging_with_repeated_project_ids():
    records = _enriched_table_records(_fixture_rows())
    sorted_records = sorted(records, key=lambda row: row["Title"])
    pages = [sorted_records[index:index + 1] for index in range(len(sorted_records))]

    assert [page[0]["id"] for page in pages] == [
        "record/beta", "record/gamma", "record/alpha",
    ]
    for page in pages:
        row = page[0]
        if row["id"] == "record/alpha":
            assert 'data-record-id="record/alpha"' in row["rationale_display"]
            assert "record beta" not in row["rationale_display"]
        else:
            assert 'data-record-id="record/alpha"' not in row["rationale_display"]


def test_search_uses_full_rationale_beyond_the_preview():
    source = _fixture_rows()
    result = _apply_register_filters(
        source,
        "not executable",
        "ALL",
        "ALL",
        "ALL",
        "ALL",
    )
    assert result["Record ID"].tolist() == ["record/alpha"]


def test_table_uses_keyed_accessible_inline_details_and_resets_on_view_change():
    from dashboard.app import app

    layout = build_analysis_tab()
    table = _component_by_id(layout, "enriched-register-table")
    rationale_column = next(
        column for column in table.columns if column["id"] == "rationale_display"
    )
    assert rationale_column["presentation"] == "markdown"
    assert table.markdown_options == {"html": True}
    assert table.sort_action == "native"
    assert table.page_current == 0
    assert _component_by_id(layout, "enriched-rationale-view-reset") is not None

    reset_callback = app.callback_map["enriched-rationale-view-reset.data"]
    assert {item["property"] for item in reset_callback["inputs"]} == {
        "derived_viewport_data", "page_current", "sort_by",
    }


def test_csv_export_keeps_the_full_unchanged_rationale():
    from dashboard.app import app

    target = thematic.df_thematic_projects.iloc[0]
    original = str(target["rationale"])
    callback = app.callback_map["enriched-download-csv.data"]["callback"].__wrapped__
    result = callback(
        1,
        original,
        *(["ALL"] * 13),
        [2019, 2026],
        2019,
        2026,
        [2019, 2026],
    )
    exported = pd.read_csv(StringIO(result["content"]))
    assert original in exported["rationale"].tolist()
    assert "rationale_display" not in exported.columns
    assert "Record ID" not in exported.columns
    assert len(registry.df_all) == 1343
