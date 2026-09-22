"""Source line breaks stay visible in the Explorer and Enriched Register (#9).

The register separates researchers (and dataset lines) with line breaks. HTML
and markdown collapse those into spaces unless the display keeps them.
"""

from dash.development.base_component import Component

from dashboard.callbacks.thematic import _generic_preview_display
from dashboard.data.registry import df_all
from dashboard.data.year_filter import year_range
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


def test_enriched_preview_turns_line_breaks_into_br_and_still_escapes():
    value = "Genevieve Cezard, University of Cambridge\nAshley Akbari, Swansea <University>"
    assert _generic_preview_display(value, "r1") == (
        "Genevieve Cezard, University of Cambridge<br>Ashley Akbari, Swansea &lt;University&gt;"
    )


def test_truncated_enriched_preview_keeps_line_breaks():
    value = "\n".join(f"Researcher {i}, University of Somewhere" for i in range(10))
    display = _generic_preview_display(value, "r1")
    assert "Researcher 0, University of Somewhere<br>Researcher 1" in display
    assert "View full value" in display


def test_explorer_researcher_and_dataset_cells_preserve_line_breaks():
    table = _component_by_id(build_explorer_tab(), "browse-table")
    pre_line = {
        rule["if"]["column_id"]
        for rule in table.style_cell_conditional
        if rule.get("whiteSpace") == "pre-line"
    }
    assert pre_line == {"Researchers", "Datasets Used"}


def test_explorer_tooltips_use_markdown_hard_breaks():
    from dashboard.app import app

    callback = next(
        spec["callback"].__wrapped__
        for key, spec in app.callback_map.items()
        if "browse-table.tooltip_data" in key
    )
    bounds = year_range(df_all)
    data, tooltips, *_ = callback(
        None, None, None, None, "2026/122", 20, bounds.value, bounds.minimum, bounds.maximum,
    )
    row = next(i for i, record in enumerate(data) if record["Project ID"] == "2026/122")
    researchers = tooltips[row]["Researchers"]["value"]
    assert "Genevieve Cezard, University of Cambridge  \nAshley Akbari, Swansea University" in researchers
