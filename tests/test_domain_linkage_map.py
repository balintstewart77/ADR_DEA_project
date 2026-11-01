"""Domain linkage map, and the redrawn record-linkage trend.

The map reads the deterministic component domains recorded for each linkage,
so a project's inferred substantive domains never reach it.
"""

import pandas as pd
import pytest
from dash.development.base_component import Component

from dashboard.charts.thematic import make_domain_linkage_map, make_record_linkage_trend
from dashboard.data.thematic import _record_linkage_domain_pairs
from dashboard.layout.analysis import build_analysis_tab


class _PartialYear:
    year = 2026
    label = "2026*"
    note = "* 2026 data covers Jan-Aug only"


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


@pytest.fixture
def pairs(monkeypatch):
    properties = pd.DataFrame({
        "Record ID": ["r1", "r2", "r3", "r4", "r5"],
        "record_linkage_component_domains": [
            "Education & Skills; Labour Market & Employment",
            "Labour Market & Employment; Education & Skills",  # order must not matter
            "Crime & Justice",                                  # within-domain
            "A; B; C",                                          # three domains -> three pairs
            "",                                                 # no linkage
        ],
    })
    monkeypatch.setattr(
        "dashboard.data.thematic.load_register_properties",
        lambda columns=None, path=None: properties,
    )
    frame = pd.DataFrame({"Record ID": ["r1", "r2", "r3", "r4", "r5"]})
    return _record_linkage_domain_pairs(frame)


def test_pairs_are_unordered_counted_once_and_include_within_domain(pairs):
    rows = {(row.domain_a, row.domain_b): (row.count, row.within_domain) for row in pairs.itertuples()}
    assert rows[("Education & Skills", "Labour Market & Employment")] == (2, False)
    assert rows[("Crime & Justice", "Crime & Justice")] == (1, True)
    # Three linked domains contribute each pair once, never the project three times.
    assert rows[("A", "B")] == (1, False)
    assert rows[("A", "C")] == (1, False)
    assert rows[("B", "C")] == (1, False)
    assert len(pairs) == 5


def test_projects_without_linkage_contribute_nothing(pairs):
    assert not ((pairs["domain_a"] == "") | (pairs["domain_b"] == "")).any()


def test_map_draws_one_triangle_and_marks_within_domain_cells(pairs):
    fig = make_domain_linkage_map(pairs)
    z = fig.data[0].z
    size = len(z)
    assert all(z[i][j] is None for i in range(size) for j in range(size) if j > i), (
        "the matrix is symmetric, so the upper triangle must stay empty"
    )
    assert sum(1 for row in z for value in row if value is not None) == len(pairs)
    # One dotted outline per within-domain cell.
    assert len(fig.layout.shapes) == int(pairs["within_domain"].sum())


def test_map_handles_missing_data_without_a_figure():
    assert len(make_domain_linkage_map(pd.DataFrame()).data) == 0
    assert len(_record_linkage_domain_pairs(pd.DataFrame())) == 0


def _trend_frame():
    return pd.DataFrame([
        {"Year": year, "record_linkage": linkage, "count": count, "total": 100,
         "pct_of_projects": count}
        for year, linkage, count in [
            (2024, "Cross-domain", 40), (2024, "Within-domain", 9), (2024, "No record linkage", 51),
            (2025, "Cross-domain", 41), (2025, "Within-domain", 10), (2025, "No record linkage", 49),
            (2026, "Cross-domain", 25), (2026, "Within-domain", 11), (2026, "No record linkage", 64),
        ]
    ])


def test_trend_plots_linkage_spans_only_and_dots_the_partial_year():
    fig = make_record_linkage_trend(_trend_frame(), metric="pct", partial_year_info=_PartialYear())
    names = {trace.name for trace in fig.data}
    assert names == {"Cross-domain linkage", "Within-domain linkage"}, (
        "'No record linkage' is the remainder and is not plotted"
    )
    dotted = [trace for trace in fig.data if trace.line.dash == "dot"]
    assert len(dotted) == 2
    assert all(list(trace.x) == [2025, 2026] for trace in dotted)
    # One legend entry per series; the dotted part-year tail must not add more.
    assert sum(1 for trace in fig.data if trace.showlegend is not False) == 2


def test_trend_direct_labels_carry_the_series_name_and_value():
    fig = make_record_linkage_trend(_trend_frame(), metric="pct", partial_year_info=_PartialYear())
    labels = [a.text for a in fig.layout.annotations if "<b>" in (a.text or "")]
    assert any("Cross-domain" in text and "25%" in text for text in labels)
    assert any("Within-domain" in text and "11%" in text for text in labels)


def test_trend_partial_year_note_clears_the_axis():
    note = _PartialYear.note
    fig = make_record_linkage_trend(_trend_frame(), metric="pct", partial_year_info=_PartialYear())
    placed = next(a for a in fig.layout.annotations if a.text == note)
    assert placed.y > 1, "the note sits above the plot, not over the final tick"


def test_map_is_registered_in_the_record_linkage_section():
    from dashboard.app import app

    assert _component_by_id(build_analysis_tab(), "deterministic-domain-linkage-map") is not None
    callback = next(
        spec for key, spec in app.callback_map.items()
        if "deterministic-domain-linkage-map.figure" in key
    )
    assert [item["id"] for item in callback["inputs"]] == ["portfolio-accreditation-year-filter"]
