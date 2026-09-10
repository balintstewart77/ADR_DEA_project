from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dash.development.base_component import Component

from dashboard.callbacks import thematic as callbacks
from dashboard.callbacks.thematic import _enriched_table_records
from dashboard.data import thematic
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
