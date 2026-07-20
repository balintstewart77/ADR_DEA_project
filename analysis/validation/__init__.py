"""Synthetic-tested foundations for the preregistered validation analysis.

This package contains no live REDCap client, official sampling execution,
completed adjudication, automated release decision, or empirical-result code.
Sections 8-10 of protocol v0.11 are the scientific specification.
"""

from .alpha import AlphaResult, krippendorff_alpha
from .bootstrap import BootstrapResult, BootstrapStatistic, StatisticValue, bootstrap_joint
from .intervals import Interval, wilson_interval
from .metrics import exact_set_equality, jaccard_similarity, masi_distance, masi_similarity, nominal_distance
from .replacement import DimensionPanel, ReplacementPanelResult, replacement_panel_analysis
from .schema import CoderRating, ModelRating, ProjectRatings, ValidationReport, validate_project

__all__ = [
    "AlphaResult",
    "BootstrapResult",
    "BootstrapStatistic",
    "CoderRating",
    "DimensionPanel",
    "Interval",
    "ModelRating",
    "ProjectRatings",
    "ReplacementPanelResult",
    "StatisticValue",
    "ValidationReport",
    "bootstrap_joint",
    "exact_set_equality",
    "jaccard_similarity",
    "krippendorff_alpha",
    "masi_distance",
    "masi_similarity",
    "nominal_distance",
    "replacement_panel_analysis",
    "validate_project",
    "wilson_interval",
]
