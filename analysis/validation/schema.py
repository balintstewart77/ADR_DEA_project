"""Canonical immutable rating model and instrument-coherence validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


UNCLEAR = "Unclear from Register Entry"

DOMAIN_LABELS = frozenset(
    {
        "Labour Market & Employment",
        "Education & Skills",
        "Health & Social Care",
        "Crime & Justice",
        "Business & Productivity",
        "Poverty, Wealth & Living Standards",
        "Housing & Planning",
        "Migration & Demographics",
        "Environment & Agriculture",
        "Public Finance & Taxation",
        "Data Infrastructure & Methodology",
        UNCLEAR,
    }
)

PURPOSE_LABELS = frozenset(
    {
        "Descriptive Monitoring",
        "Outcome Tracking",
        "Life-Course / Trajectory Analysis",
        "Service Interaction / Systems Analysis",
        "Policy Evaluation / Impact Analysis",
        "Risk Prediction / Early Identification",
        "Methodological / Infrastructure Research",
        UNCLEAR,
    }
)

REGISTER_SUFFICIENCY_VALUES = frozenset(
    {"Sufficient", "Partially sufficient", "Insufficient"}
)
TAXONOMY_FIT_03 = frozenset({"Fit", "Partial Fit", "No Fit"})
TAXONOMY_FIT_04 = TAXONOMY_FIT_03 | {"Cannot assess from register entry"}
TAXONOMY_ISSUES_03 = frozenset(
    {
        "Missing category",
        "Ambiguous/overlapping categories",
        "Too broad",
        "Too narrow",
        "Other",
        "None",
    }
)
TAXONOMY_ISSUES_04 = frozenset(
    {
        "Missing or inadequately represented category",
        "Ambiguous or overlapping category boundaries",
        "Other taxonomy problem",
    }
)
INSTRUMENT_VERSIONS = frozenset({
    "redcap-candidate-0.3",
    "redcap-candidate-0.4",
    "redcap-candidate-0.5",
    "redcap-candidate-0.6",
    "redcap-candidate-0.7",
})
SAMPLE_SETS = frozenset({"random_baseline", "hard_case", "owner_review", "pilot"})


class IssueSeverity(str, Enum):
    RETAINED_INCONSISTENT = "retained_instrument_inconsistent"
    FATAL = "fatal_or_uninterpretable"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    dimension: str
    severity: IssueSeverity
    message: str


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues

    @property
    def retained_instrument_inconsistent(self) -> bool:
        return bool(self.issues) and not any(
            issue.severity is IssueSeverity.FATAL for issue in self.issues
        )

    @property
    def fatal_dimensions(self) -> frozenset[str]:
        return frozenset(
            issue.dimension
            for issue in self.issues
            if issue.severity is IssueSeverity.FATAL
        )

    @property
    def status(self) -> str:
        if self.valid:
            return "valid_response"
        if self.retained_instrument_inconsistent:
            return "retained_instrument_inconsistent"
        return "fatal_or_uninterpretable_dimension"


@dataclass(frozen=True)
class CoderRating:
    reviewer_id: str
    domains: frozenset[str] | None
    purposes: frozenset[str] | None
    equity_tag: int | None
    covid_tag: int | None
    register_sufficiency: str | None
    taxonomy_fit: str | None
    taxonomy_issues: frozenset[str] = frozenset()
    explanatory_note: str | None = None
    exposure_flag: bool | None = None
    exposure_source_note: str | None = None
    complete: bool = True
    response_valid: bool = True


@dataclass(frozen=True)
class ModelRating:
    domains: frozenset[str] | None
    purposes: frozenset[str] | None
    equity_tag: int | None
    covid_tag: int | None
    valid: bool = True


@dataclass(frozen=True)
class ProjectRatings:
    record_id: str
    sample_set: str
    coder_a: CoderRating | None
    coder_b: CoderRating | None
    coder_c: CoderRating | None
    model: ModelRating | None
    instrument_version: str
    validation_included: bool = True

    @property
    def coders(self) -> tuple[CoderRating | None, CoderRating | None, CoderRating | None]:
        return self.coder_a, self.coder_b, self.coder_c


def _label_issues(
    labels: frozenset[str] | None,
    *,
    allowed: frozenset[str],
    dimension: str,
    coder: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if labels is None:
        return [
            ValidationIssue(
                "missing_rating", dimension, IssueSeverity.FATAL, f"{coder} has no {dimension} rating"
            )
        ]
    if not labels:
        issues.append(
            ValidationIssue(
                "empty_response", dimension, IssueSeverity.FATAL, f"{coder} has an empty {dimension} response"
            )
        )
    unknown = labels - allowed
    if unknown:
        issues.append(
            ValidationIssue(
                "unknown_label",
                dimension,
                IssueSeverity.FATAL,
                f"{coder} has unknown {dimension} labels: {sorted(unknown)}",
            )
        )
    if UNCLEAR in labels and len(labels) > 1:
        issues.append(
            ValidationIssue(
                "unclear_with_substantive_label",
                dimension,
                IssueSeverity.RETAINED_INCONSISTENT,
                f"{coder} selected {UNCLEAR} with a substantive label",
            )
        )
    return issues


def validate_project(project: ProjectRatings) -> ValidationReport:
    """Classify fatal and retainable inconsistencies without adjudicating them.

    A fatal issue prevents interpretation of the named dimension.  A retained
    inconsistency is readable but violates the instrument rules and is kept in
    the unconditional analysis unless a prespecified sensitivity analysis later
    excludes it before analysis lock (protocol Section 8.8).
    """

    issues: list[ValidationIssue] = []
    if not project.record_id or project.record_id != project.record_id.strip():
        issues.append(
            ValidationIssue(
                "invalid_record_id", "record_id", IssueSeverity.FATAL, "Record ID is blank or has boundary whitespace"
            )
        )
    if project.sample_set not in SAMPLE_SETS:
        issues.append(
            ValidationIssue("unknown_sample_set", "sample_set", IssueSeverity.FATAL, project.sample_set)
        )
    if project.instrument_version not in INSTRUMENT_VERSIONS:
        issues.append(
            ValidationIssue(
                "unknown_instrument_version",
                "all",
                IssueSeverity.FATAL,
                project.instrument_version,
            )
        )

    present = [coder for coder in project.coders if coder is not None]
    reviewer_ids = [coder.reviewer_id for coder in present]
    if len(set(reviewer_ids)) != len(reviewer_ids):
        issues.append(
            ValidationIssue(
                "duplicate_reviewer_project_assignment",
                "all",
                IssueSeverity.FATAL,
                "A reviewer appears more than once for this project",
            )
        )

    for slot, coder in zip(("coder_a", "coder_b", "coder_c"), project.coders):
        if coder is None:
            issues.append(
                ValidationIssue("missing_coder", "all", IssueSeverity.FATAL, f"{slot} is missing")
            )
            continue
        if not coder.complete or not coder.response_valid:
            issues.append(
                ValidationIssue(
                    "incomplete_or_invalid_coder",
                    "all",
                    IssueSeverity.FATAL,
                    f"{slot} is incomplete or administratively invalid",
                )
            )
        issues.extend(
            _label_issues(coder.domains, allowed=DOMAIN_LABELS, dimension="domains", coder=slot)
        )
        issues.extend(
            _label_issues(coder.purposes, allowed=PURPOSE_LABELS, dimension="purposes", coder=slot)
        )
        if coder.purposes is not None and len(coder.purposes) > 2:
            issues.append(
                ValidationIssue(
                    "purpose_maximum_exceeded",
                    "purposes",
                    IssueSeverity.RETAINED_INCONSISTENT,
                    f"{slot} selected more than two purposes",
                )
            )
        for dimension, value in (("equity_tag", coder.equity_tag), ("covid_tag", coder.covid_tag)):
            if value not in (0, 1):
                issues.append(
                    ValidationIssue(
                        "malformed_binary", dimension, IssueSeverity.FATAL, f"{slot}: {value!r}"
                    )
                )
        if coder.register_sufficiency not in REGISTER_SUFFICIENCY_VALUES:
            issues.append(
                ValidationIssue(
                    "unknown_sufficiency",
                    "register_sufficiency",
                    IssueSeverity.FATAL,
                    f"{slot}: {coder.register_sufficiency!r}",
                )
            )
        fit_values = TAXONOMY_FIT_03 if project.instrument_version == "redcap-candidate-0.3" else TAXONOMY_FIT_04
        issue_values = TAXONOMY_ISSUES_03 if project.instrument_version == "redcap-candidate-0.3" else TAXONOMY_ISSUES_04
        if coder.taxonomy_fit not in fit_values:
            issues.append(
                ValidationIssue(
                    "unknown_taxonomy_fit",
                    "taxonomy_fit",
                    IssueSeverity.FATAL,
                    f"{slot}: {coder.taxonomy_fit!r}",
                )
            )
        unknown_issues = coder.taxonomy_issues - issue_values
        if unknown_issues:
            issues.append(
                ValidationIssue(
                    "unknown_taxonomy_issue",
                    "taxonomy_issue",
                    IssueSeverity.FATAL,
                    f"{slot}: {sorted(unknown_issues)}",
                )
            )
        if project.instrument_version in {
            "redcap-candidate-0.4",
            "redcap-candidate-0.5",
            "redcap-candidate-0.6",
            "redcap-candidate-0.7",
        }:
            if coder.taxonomy_fit == "Cannot assess from register entry" and coder.register_sufficiency == "Sufficient":
                issues.append(
                    ValidationIssue(
                        "cannot_assess_with_sufficient",
                        "taxonomy_fit",
                        IssueSeverity.RETAINED_INCONSISTENT,
                        f"{slot}: Cannot assess with Sufficient evidence",
                    )
                )
            if coder.taxonomy_fit in {"Fit", "Cannot assess from register entry"} and coder.taxonomy_issues:
                issues.append(
                    ValidationIssue(
                        "hidden_taxonomy_issue_selected",
                        "taxonomy_issue",
                        IssueSeverity.RETAINED_INCONSISTENT,
                        f"{slot}: taxonomy issue selected when field should be hidden",
                    )
                )
            if coder.taxonomy_fit in {"Partial Fit", "No Fit"} and not coder.taxonomy_issues:
                issues.append(
                    ValidationIssue(
                        "missing_required_taxonomy_issue",
                        "taxonomy_issue",
                        IssueSeverity.RETAINED_INCONSISTENT,
                        f"{slot}: fit requires at least one issue type",
                    )
                )
            if (
                "Other taxonomy problem" in coder.taxonomy_issues
                and not (coder.explanatory_note or "").strip()
            ):
                issues.append(
                    ValidationIssue(
                        "other_taxonomy_problem_without_note",
                        "taxonomy_issue",
                        IssueSeverity.RETAINED_INCONSISTENT,
                        f"{slot}: Other taxonomy problem requires an explanatory note",
                    )
                )

    if project.model is None or not project.model.valid:
        issues.append(
            ValidationIssue("missing_or_invalid_model", "all", IssueSeverity.FATAL, "Production model rating unavailable")
        )
    else:
        issues.extend(
            _label_issues(project.model.domains, allowed=DOMAIN_LABELS, dimension="domains", coder="model")
        )
        issues.extend(
            _label_issues(project.model.purposes, allowed=PURPOSE_LABELS, dimension="purposes", coder="model")
        )
        if project.model.purposes is not None and len(project.model.purposes) > 2:
            issues.append(
                ValidationIssue(
                    "purpose_maximum_exceeded",
                    "purposes",
                    IssueSeverity.FATAL,
                    "model selected more than two purposes",
                )
            )
        for dimension, value in (("equity_tag", project.model.equity_tag), ("covid_tag", project.model.covid_tag)):
            if value not in (0, 1):
                issues.append(
                    ValidationIssue("malformed_binary", dimension, IssueSeverity.FATAL, f"model: {value!r}")
                )
    return ValidationReport(tuple(issues))


def complete_case_projects(
    projects: Iterable[ProjectRatings], dimension: str
) -> tuple[ProjectRatings, ...]:
    """Return one common interpretable set for a dimension, retaining flagged cases."""

    if dimension not in {"domains", "purposes", "equity_tag", "covid_tag"}:
        raise ValueError(f"Unknown classification dimension: {dimension}")
    retained: list[ProjectRatings] = []
    for project in projects:
        report = validate_project(project)
        if "all" in report.fatal_dimensions or dimension in report.fatal_dimensions:
            continue
        retained.append(project)
    return tuple(retained)
