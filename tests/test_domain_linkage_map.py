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


PRODUCTS = [
    {"canonical": "Cross Product", "component_domains": ["Education & Skills",
                                                         "Labour Market & Employment"]},
    {"canonical": "Three Domain Product", "component_domains": ["A", "B", "C"]},
    {"canonical": "Crime Product", "component_domains": ["Crime & Justice"]},
    {"canonical": "Other Crime Product", "component_domains": ["Crime & Justice"]},
    {"canonical": "Housing Product", "component_domains": ["Housing & Planning"]},
]


@pytest.fixture
def pairs(monkeypatch):
    properties = pd.DataFrame({
        "Record ID": ["r1", "r2", "r3", "r4", "r5", "r6"],
        "matched_products": [
            "Cross Product",
            "Cross Product",
            "Crime Product",
            "Three Domain Product",
            # Two single-domain products in different domains. The linkage rule
            # says this is NOT cross-domain linkage, so no pair may appear.
            "Crime Product; Housing Product",
            # Two products in the same cell: one project, counted once.
            "Crime Product; Other Crime Product",
        ],
    })
    monkeypatch.setattr(
        "dashboard.data.thematic.load_register_properties",
        lambda columns=None, path=None: properties,
    )
    monkeypatch.setattr("dashboard.data.thematic.LINKED_PRODUCTS", PRODUCTS)
    monkeypatch.setattr(
        "dashboard.data.thematic.product_short_label", lambda name: name)
    frame = pd.DataFrame({"Record ID": ["r1", "r2", "r3", "r4", "r5", "r6"]})
    return _record_linkage_domain_pairs(frame)


def _cells(pairs):
    return {(row.domain_a, row.domain_b): row for row in pairs.itertuples()}


def test_pairs_are_unordered_counted_once_and_include_within_domain(pairs):
    cells = _cells(pairs)
    assert cells[("Education & Skills", "Labour Market & Employment")].count == 2
    assert cells[("Crime & Justice", "Crime & Justice")].within_domain is True
    # Three linked domains contribute each pair once, never the project three times.
    for pair in (("A", "B"), ("A", "C"), ("B", "C")):
        assert cells[pair].count == 1


def test_separate_single_domain_products_are_not_cross_domain(pairs):
    # r5 matched a Crime product and a Housing product. Under the linkage rule
    # the span is a property of each product, so the project appears on both
    # diagonals and in no Crime x Housing cell.
    cells = _cells(pairs)
    assert ("Crime & Justice", "Housing & Planning") not in cells
    assert ("Housing & Planning", "Crime & Justice") not in cells
    assert cells[("Housing & Planning", "Housing & Planning")].count == 1


def test_a_project_matching_two_products_in_one_cell_is_counted_once(pairs):
    # r3, r5 and r6 all matched Crime products; r6 matched two of them.
    assert _cells(pairs)[("Crime & Justice", "Crime & Justice")].count == 3


def test_products_label_names_the_drivers_biggest_first(pairs):
    cells = _cells(pairs)
    assert cells[("Education & Skills", "Labour Market & Employment")].products == (
        "Cross Product 2")
    crime = cells[("Crime & Justice", "Crime & Justice")].products
    assert crime.startswith("Crime Product 3"), crime
    assert "Other Crime Product 1" in crime
    # Per-product counts sum past the cell's project count, so say so.
    assert "projects overlap" in crime


def test_unknown_products_contribute_nothing(monkeypatch):
    properties = pd.DataFrame({
        "Record ID": ["r1"], "matched_products": ["Not In The Reference"]})
    monkeypatch.setattr(
        "dashboard.data.thematic.load_register_properties",
        lambda columns=None, path=None: properties)
    monkeypatch.setattr("dashboard.data.thematic.LINKED_PRODUCTS", PRODUCTS)
    result = _record_linkage_domain_pairs(pd.DataFrame({"Record ID": ["r1"]}))
    assert result.empty


def test_projects_without_linkage_contribute_nothing(pairs):
    assert not ((pairs["domain_a"] == "") | (pairs["domain_b"] == "")).any()


def test_map_hover_carries_the_products_behind_each_cell(pairs):
    fig = make_domain_linkage_map(pairs)
    trace = fig.data[0]
    assert "%{customdata}" in trace.hovertemplate
    labels = [cell for row in trace.customdata for cell in row if cell]
    assert len(labels) == len(pairs)
    assert any("Cross Product 2" in label for label in labels)


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
