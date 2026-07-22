"""Synthetic-tested foundations for the preregistered validation analysis.

This package contains no live REDCap client, official sampling execution,
completed adjudication, automated release decision, or empirical-result code.
Sections 8-10 of protocol v0.14 are the current review-candidate specification.
"""

from .alpha import AlphaResult, krippendorff_alpha
from .bootstrap import BootstrapResult, BootstrapStatistic, StatisticValue, bootstrap_joint
from .intervals import Interval, wilson_interval
from .instrument_sensitivity import (
    EstimateComparison,
    InstrumentSensitivityError,
    InstrumentSensitivityPopulation,
    InstrumentSensitivityReport,
    StructuralValidityBatch,
    StructuralValidityResult,
    analyse_instrument_validity_sensitivity,
    matched_panel_sensitivity_population,
    validate_formal_candidate_0_7_rows,
)
from .metrics import exact_set_equality, jaccard_similarity, masi_distance, masi_similarity, nominal_distance
from .replacement import DimensionPanel, ReplacementPanelResult, replacement_panel_analysis
from .schema import CoderRating, ModelRating, ProjectRatings, ValidationReport, validate_project

__all__ = [
    "AlphaResult",
    "BootstrapResult",
    "BootstrapStatistic",
    "CoderRating",
    "DimensionPanel",
    "EstimateComparison",
    "Interval",
    "InstrumentSensitivityError",
    "InstrumentSensitivityPopulation",
    "InstrumentSensitivityReport",
    "ModelRating",
    "ProjectRatings",
    "ReplacementPanelResult",
    "StatisticValue",
    "StructuralValidityBatch",
    "StructuralValidityResult",
    "ValidationReport",
    "analyse_instrument_validity_sensitivity",
    "bootstrap_joint",
    "exact_set_equality",
    "jaccard_similarity",
    "krippendorff_alpha",
    "masi_distance",
    "masi_similarity",
    "matched_panel_sensitivity_population",
    "nominal_distance",
    "replacement_panel_analysis",
    "validate_project",
    "validate_formal_candidate_0_7_rows",
    "wilson_interval",
]
