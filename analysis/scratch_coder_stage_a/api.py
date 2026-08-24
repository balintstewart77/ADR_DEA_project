"""Small public API for independent aggregate review notebooks."""

from __future__ import annotations

from analysis.validation.replacement import replacement_panel_analysis

from .agreement import bootstrap_replacement, encode_panels
from .load import load_frozen_export
from .panels import build_stage_a_data, dimension_panels, distance_for_dimension


def validate_export():
    """Validate authorities, formal joins, structure, labels, and return StageAData."""

    return build_stage_a_data()


def build_panels(data, record_ids, dimension):
    return dimension_panels(data, frozenset(record_ids), dimension)


def run_replacement_analysis(panels, dimension):
    return replacement_panel_analysis(panels, distance_for_dimension(dimension))


def bootstrap_replacement_analysis(panels, dimension, *, attempts=2000, seed=20260714):
    encoded = encode_panels(panels, distance_for_dimension(dimension))
    return bootstrap_replacement(encoded, attempts=attempts, seed=seed)
