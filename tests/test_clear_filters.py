"""Clearable filter dropdowns and the "Clear filters" buttons.

Covers the Project Explorer and the Enriched Register: every filter dropdown
starts empty, can be cleared with its own control, and shows its "All …" label
as the placeholder; each panel's "Clear filters" button resets every filter the
table reads; and an empty filter value filters exactly like "ALL".
"""

import pandas as pd
import pytest
from dash.development.base_component import Component

from dashboard.callbacks.explorer import BROWSE_FILTER_DROPDOWN_IDS
from dashboard.callbacks.thematic import ENRICHED_FILTER_DROPDOWN_IDS
from dashboard.data.filtering import (
    _get_browse_display_df,
    _get_enriched_register_display_df,
)
from dashboard.layout.analysis import build_analysis_tab
from dashboard.layout.explorer import build_explorer_tab


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


def _callback(output_key):
    from dashboard.app import app

    return next(
        spec for key, spec in app.callback_map.items() if output_key in key
    )


PANELS = [
    pytest.param(
        build_explorer_tab, BROWSE_FILTER_DROPDOWN_IDS,
        "browse-clear-filters-btn.n_clicks", "browse-table.data",
        "browse-search", "browse-accreditation-year-filter", "browse-table",
        id="explorer",
    ),
    pytest.param(
        build_analysis_tab, ENRICHED_FILTER_DROPDOWN_IDS,
        "enriched-clear-filters-btn.n_clicks", "enriched-register-table.data",
        "enriched-search", "enriched-accreditation-year-filter", "enriched-register-table",
        id="enriched",
    ),
]


PANEL_NAMES = "build, dropdown_ids, button_input, table_output, search_id, year_id, table_id"


@pytest.mark.parametrize(PANEL_NAMES, PANELS)
def test_filter_dropdowns_start_empty_clearable_with_all_placeholder(
    build, dropdown_ids, button_input, table_output, search_id, year_id, table_id
):
    layout = build()
    for dropdown_id in dropdown_ids:
        dropdown = _component_by_id(layout, dropdown_id)
        all_label = next(o["label"] for o in dropdown.options if o["value"] == "ALL")
        assert dropdown.value is None, dropdown_id
        assert dropdown.clearable is True, dropdown_id
        assert dropdown.placeholder == all_label, dropdown_id


@pytest.mark.parametrize(PANEL_NAMES, PANELS)
def test_clear_button_resets_every_filter_the_table_reads(
    build, dropdown_ids, button_input, table_output, search_id, year_id, table_id
):
    table_spec = _callback(table_output)
    # The panel's own filters. The Enriched Register also reads the tab-wide
    # portfolio year filter, which drives the charts too and is not reset here.
    panel_prefix = search_id.split("-")[0] + "-"
    filter_inputs = {
        item["id"] for item in table_spec["inputs"]
        if item["id"].startswith(panel_prefix)
        and (item["id"].endswith("-filter") or item["id"] == search_id)
    }

    clear_spec = _clear_callback(button_input)
    outputs = [str(output).split("@")[0].split(".")[0] for output in clear_spec["output"]]
    # A filter added to the table later must be added to the reset too.
    assert filter_inputs <= set(outputs)

    result = clear_spec["callback"].__wrapped__(3, 2019, 2026)
    values = dict(zip(outputs, result))
    assert values[search_id] == ""
    assert all(values[dropdown_id] is None for dropdown_id in dropdown_ids)
    assert values[year_id] == [2019, 2026]
    assert values[table_id] == 0


def _clear_callback(button_input):
    from dashboard.app import app

    return next(
        spec for spec in app.callback_map.values()
        if button_input in {f"{i['id']}.{i['property']}" for i in spec["inputs"]}
    )


def test_empty_filter_values_filter_like_all():
    browse_all = _get_browse_display_df(None, "ALL", "ALL", "ALL", "ALL")
    browse_empty = _get_browse_display_df(None, None, None, None, None)
    pd.testing.assert_frame_equal(browse_all, browse_empty)

    enriched_all, all_note = _get_enriched_register_display_df(None, *["ALL"] * 13)
    enriched_empty, empty_note = _get_enriched_register_display_df(None, *[None] * 13)
    pd.testing.assert_frame_equal(enriched_all, enriched_empty)
    assert all_note == empty_note
