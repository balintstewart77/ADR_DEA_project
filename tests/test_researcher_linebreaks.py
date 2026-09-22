"""Source line breaks stay visible in the Explorer and Enriched Register (#9).

The register separates researchers (and dataset lines) with line breaks. HTML
and markdown collapse those into spaces unless the display keeps them.
"""

import re

import pandas as pd
from dash.development.base_component import Component

from dashboard.callbacks.thematic import _generic_preview_display
from dashboard.display_text import datasets_display_text, researcher_display_text
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


def test_researcher_name_wrapped_before_its_organisation_is_rejoined():
    value = "Daniele Cox,\nOffice for National Statistics\nMary Cleaton,\nOffice for National Statistics"
    assert researcher_display_text(value) == (
        "Daniele Cox, Office for National Statistics\nMary Cleaton, Office for National Statistics"
    )


def test_ambiguous_researcher_lines_are_left_as_written():
    # Lone names without organisations (2021/178) must not be merged, and an
    # organisation containing a comma (2020/116) is not guessed at.
    names = "Mark Bryan, University of Sheffield\nJennifer Roberts,\nCristina Sechel,\nAndrew Bryce,"
    assert researcher_display_text(names) == names
    city = "Giulia Faggio,\nCity, University of London"
    assert researcher_display_text(city) == city


def test_wrapped_organisation_names_continue_the_previous_line():
    value = (
        "Antonio Gasparrini, London School of Hygiene\nand Tropical Medicine\n"
        "Stephen Machin, London School of\nEconomics"
    )
    assert researcher_display_text(value) == (
        "Antonio Gasparrini, London School of Hygiene and Tropical Medicine\n"
        "Stephen Machin, London School of Economics"
    )


def test_researcher_tidying_never_changes_words_across_the_register():
    def squash(text):
        return re.sub(r"\s+", " ", text).strip()

    for value in df_all["Researchers"].dropna().astype(str):
        assert squash(researcher_display_text(value)) == squash(value)


def test_datasets_are_listed_under_their_organisation():
    value = (
        "Office for National Statistics: Wealth and Assets Survey & Annual Survey of Hours "
        "and Earnings, Annual Survey of Hours and Earnings\n"
        "Department for Business, Energy & Industrial Strategy: Community Innovation Survey "
        "“ United Kingdom Innovation Survey Data given for all available years unless otherwise stated."
    )
    assert datasets_display_text(value) == (
        "Office for National Statistics (ONS)\n"
        "• Wealth and Assets Survey (WAS)\n"
        "• Annual Survey of Hours and Earnings (ASHE)\n"
        "Department for Business, Energy and Industrial Strategy (BEIS)\n"
        "• UK Innovation Survey (UKIS)"
    )


def test_display_helpers_leave_empty_values_blank():
    for helper in (researcher_display_text, datasets_display_text):
        assert helper(None) == ""
        assert helper(float("nan")) == ""
        assert helper(pd.NA) == ""


def test_explorer_cells_show_tidied_text_and_tooltips_keep_the_register_text():
    from dashboard.app import app

    callback = next(
        spec["callback"].__wrapped__
        for key, spec in app.callback_map.items()
        if "browse-table.tooltip_data" in key
    )
    bounds = year_range(df_all)
    data, tooltips, *_ = callback(
        None, None, None, None, "2019/005", 20, bounds.value, bounds.minimum, bounds.maximum,
    )
    row = next(i for i, record in enumerate(data) if record["Project ID"] == "2019/005")
    assert data[row]["Researchers"].splitlines()[0] == "Daniele Cox, Office for National Statistics"
    assert data[row]["Datasets Used"].splitlines()[1].startswith("• ")
    assert "Daniele Cox,  \nOffice for National Statistics" in tooltips[row]["Researchers"]["value"]
