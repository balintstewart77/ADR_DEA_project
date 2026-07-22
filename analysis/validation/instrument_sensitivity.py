"""Frozen-instrument validation and matched-panel sensitivity analysis.

The narrow adapter sends completed formal candidate-0.7 scratch responses to
the frozen REDCap validator without changing their source mappings. Scientific
recomputation uses the repository's existing replacement-panel functions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable, Mapping, Sequence

from scripts.validate_redcap_candidate import VERSION, validate_scratch

from .diagnostics import human_supported, support_band
from .metrics import masi_distance, nominal_distance
from .replacement import DimensionPanel, replacement_panel_analysis
from .schema import CoderRating, ModelRating, ProjectRatings


FORMAL_BATCH = "formal_validation"
EXPECTED_CODER_COUNT = 3


@dataclass(frozen=True)
class StructuralValidityResult:
    """Frozen-validator outcome for one completed formal coder-project response."""

    assignment_id: str
    record_id: str
    reviewer_id: str
    issues: tuple[str, ...] = ()

    @property
    def affected(self) -> bool:
        return bool(self.issues)


@dataclass(frozen=True)
class StructuralValidityBatch:
    results: tuple[StructuralValidityResult, ...]
    excluded_row_count: int


@dataclass(frozen=True)
class InstrumentSensitivityPopulation:
    primary_project_ids: tuple[str, ...]
    affected_response_count: int
    affected_project_ids: tuple[str, ...]
    retained_project_ids: tuple[str, ...]
    response_issues: Mapping[str, tuple[str, ...]]

    @property
    def affected_project_count(self) -> int:
        return len(self.affected_project_ids)

    @property
    def retained_project_count(self) -> int:
        return len(self.retained_project_ids)


@dataclass(frozen=True)
class EstimateComparison:
    family: str
    dimension: str
    metric: str
    label: str
    panel: str
    primary_estimate: float | None
    sensitivity_estimate: float | None
    difference: float | None
    difference_unit: str


@dataclass(frozen=True)
class InstrumentSensitivityReport:
    population: InstrumentSensitivityPopulation
    replacement_estimates: tuple[EstimateComparison, ...]
    per_label_estimates: tuple[EstimateComparison, ...]
    zero_affected_results_identical: bool


class InstrumentSensitivityError(ValueError):
    """Raised when a claimed formal matched panel is structurally ambiguous."""


def _strict_integer(value: object, field: str, issues: list[str]) -> int | None:
    """Decode a REDCap integer without trimming or permissive conversion."""

    if isinstance(value, bool):
        issues.append(f"malformed raw integer {field}: {value!r}")
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value and value.isascii() and value.isdecimal():
        return int(value)
    if value in (None, ""):
        return None
    issues.append(f"malformed raw integer {field}: {value!r}")
    return None


def _checkbox_codes(
    row: Mapping[str, object], prefix: str, codes: range, issues: list[str]
) -> list[int]:
    direct = row.get(prefix)
    if isinstance(direct, list):
        output: list[int] = []
        for index, value in enumerate(direct):
            parsed = _strict_integer(value, f"{prefix}[{index}]", issues)
            if parsed is not None:
                output.append(parsed)
        return output
    if direct not in (None, ""):
        issues.append(f"malformed raw checkbox collection {prefix}: {direct!r}")
    selected: list[int] = []
    for code in codes:
        field = f"{prefix}___{code}"
        parsed = _strict_integer(row.get(field, "0"), field, issues)
        if parsed not in (0, 1):
            issues.append(f"malformed raw checkbox value {field}: {row.get(field)!r}")
        elif parsed == 1:
            selected.append(code)
    unknown = sorted(
        key for key, value in row.items()
        if key.startswith(prefix + "___")
        and key[len(prefix) + 3 :].isdecimal()
        and int(key[len(prefix) + 3 :]) not in codes
        and value not in (0, "0", "", None)
    )
    if unknown:
        issues.append(f"unknown selected checkbox columns for {prefix}: {unknown}")
    return selected


def _formal_candidate_0_7_row(row: Mapping[str, object]) -> bool:
    """Identify only included formal scratch project assignments."""

    return (
        row.get("instrument_ver") == VERSION
        and str(row.get("record_kind", "")) == "1"
        and str(row.get("review_stream", "")) == "1"
        and str(row.get("validation_included", "")) == "1"
        and str(row.get("sample_status", "")) == "1"
        and row.get("assignment_batch") == FORMAL_BATCH
        and str(row.get("sample_set", "")) in {"1", "2"}
    )


def _validator_payload(
    row: Mapping[str, object], adapter_issues: list[str]
) -> dict[str, object]:
    """Build the frozen validator payload without modifying ``row``."""

    payload: dict[str, object] = {
        "assignment_id": row.get("assignment_id"),
        "instrument_ver": row.get("instrument_ver"),
        "sc_domains": _checkbox_codes(row, "sc_domains", range(1, 13), adapter_issues),
        "sc_purposes": _checkbox_codes(row, "sc_purposes", range(1, 9), adapter_issues),
        "sc_tax_issue": _checkbox_codes(row, "sc_tax_issue", range(1, 6), adapter_issues),
        "sc_exposure_note": row.get("sc_exposure_note"),
        "sc_note": row.get("sc_note"),
        "sc_blind_decl": row.get("sc_blind_decl"),
    }
    for field in (
        "record_kind", "sc_exposure", "sc_covid", "sc_equity",
        "sc_sufficiency", "sc_taxonomy_fit", "sc_confidence",
    ):
        payload[field] = _strict_integer(row.get(field), field, adapter_issues)
    return payload


def validate_formal_candidate_0_7_rows(
    rows: Iterable[Mapping[str, object]],
) -> StructuralValidityBatch:
    """Use the actual frozen validator for completed eligible responses.

    Declaration, owner, synthetic-QA, historical, excluded, and non-formal rows
    are counted and ignored. Incomplete forms are not reclassified as completed
    affected responses; their absence is caught by the matched-panel check.
    """

    results: list[StructuralValidityResult] = []
    excluded = 0
    for row in rows:
        if not _formal_candidate_0_7_row(row) or str(row.get("scratch_coder_complete", "")) != "2":
            excluded += 1
            continue
        adapter_issues: list[str] = []
        payload = _validator_payload(row, adapter_issues)
        validator_issues = validate_scratch(payload)
        assignment_id = str(row.get("assignment_id", ""))
        record_id = str(row.get("source_record_id", ""))
        reviewer_id = str(row.get("reviewer_id", ""))
        identity_issues = []
        if not record_id or record_id != record_id.strip():
            identity_issues.append("missing or whitespace-unclean source_record_id")
        if not reviewer_id or reviewer_id != reviewer_id.strip():
            identity_issues.append("missing or whitespace-unclean reviewer_id")
        results.append(StructuralValidityResult(
            assignment_id, record_id, reviewer_id,
            tuple(adapter_issues + validator_issues + identity_issues),
        ))
    return StructuralValidityBatch(tuple(results), excluded)


def matched_panel_sensitivity_population(
    project_ids: Sequence[str],
    response_results: Iterable[StructuralValidityResult],
    *,
    reviewer_ids_by_project: Mapping[str, frozenset[str]],
    model_record_ids: Iterable[str],
) -> InstrumentSensitivityPopulation:
    """Exclude affected projects after proving complete three-coder/model panels."""

    ordered_projects = tuple(project_ids)
    if any(not value or value != value.strip() for value in ordered_projects):
        raise InstrumentSensitivityError("Project IDs must be non-empty and whitespace-clean")
    if len(set(ordered_projects)) != len(ordered_projects):
        raise InstrumentSensitivityError("Project IDs must be unique")
    project_set = set(ordered_projects)
    if set(reviewer_ids_by_project) != project_set:
        raise InstrumentSensitivityError("Reviewer-panel projects do not match the primary population")
    if set(model_record_ids) != project_set:
        raise InstrumentSensitivityError("Model panels do not match the primary population")

    seen_assignments: set[str] = set()
    by_project: dict[str, list[StructuralValidityResult]] = defaultdict(list)
    affected_projects: set[str] = set()
    affected_responses = 0
    response_issues: dict[str, tuple[str, ...]] = {}
    for result in response_results:
        if result.assignment_id in seen_assignments:
            raise InstrumentSensitivityError(f"Duplicate assignment result: {result.assignment_id}")
        seen_assignments.add(result.assignment_id)
        if result.record_id not in project_set:
            raise InstrumentSensitivityError(
                f"Structural result references a project outside the analysis population: {result.record_id}"
            )
        by_project[result.record_id].append(result)
        if result.affected:
            affected_responses += 1
            affected_projects.add(result.record_id)
            response_issues[result.assignment_id] = tuple(result.issues)

    for record_id in ordered_projects:
        results = by_project.get(record_id, [])
        reviewers = [item.reviewer_id for item in results]
        expected = reviewer_ids_by_project[record_id]
        if len(results) != EXPECTED_CODER_COUNT or len(set(reviewers)) != EXPECTED_CODER_COUNT:
            raise InstrumentSensitivityError(
                f"Project {record_id} requires exactly three distinct completed scratch responses"
            )
        if set(reviewers) != set(expected) or len(expected) != EXPECTED_CODER_COUNT:
            raise InstrumentSensitivityError(
                f"Project {record_id} structural results do not match its three-coder panel"
            )

    affected = tuple(value for value in ordered_projects if value in affected_projects)
    retained = tuple(value for value in ordered_projects if value not in affected_projects)
    return InstrumentSensitivityPopulation(
        ordered_projects, affected_responses, affected, retained, response_issues
    )


def _dimension_panel(project: ProjectRatings, dimension: str) -> DimensionPanel[Hashable]:
    def value(rating: CoderRating | ModelRating | None) -> Hashable | None:
        return None if rating is None else getattr(rating, dimension)
    return DimensionPanel(
        project.record_id,
        value(project.coder_a), value(project.coder_b), value(project.coder_c), value(project.model),
    )


def _comparison(
    family: str, dimension: str, metric: str, label: str, panel: str,
    primary: float | None, sensitivity: float | None, unit: str,
) -> EstimateComparison:
    difference = None if primary is None or sensitivity is None else sensitivity-primary
    if difference is not None and unit == "percentage_points":
        difference *= 100.0
    return EstimateComparison(
        family, dimension, metric, label, panel, primary, sensitivity, difference, unit
    )


def _replacement_comparisons(
    projects: Sequence[ProjectRatings], retained_ids: frozenset[str]
) -> tuple[EstimateComparison, ...]:
    output: list[EstimateComparison] = []
    for dimension, distance in (
        ("domains", masi_distance), ("purposes", masi_distance),
        ("equity_tag", nominal_distance), ("covid_tag", nominal_distance),
    ):
        panels = tuple(_dimension_panel(project, dimension) for project in projects)
        primary = replacement_panel_analysis(panels, distance)
        sensitivity = replacement_panel_analysis(
            (panel for panel in panels if panel.record_id in retained_ids), distance
        )
        values = (
            ("alpha_ABC", primary.alpha_abc.alpha, sensitivity.alpha_abc.alpha),
            ("alpha_LBC", primary.alpha_lbc.alpha, sensitivity.alpha_lbc.alpha),
            ("alpha_ALC", primary.alpha_alc.alpha, sensitivity.alpha_alc.alpha),
            ("alpha_ABL", primary.alpha_abl.alpha, sensitivity.alpha_abl.alpha),
            ("delta_A", primary.delta_a, sensitivity.delta_a),
            ("delta_B", primary.delta_b, sensitivity.delta_b),
            ("delta_C", primary.delta_c, sensitivity.delta_c),
            ("delta_min", primary.delta_min, sensitivity.delta_min),
        )
        output.extend(
            _comparison("replacement_panel", dimension, metric, "", metric, left, right, "absolute")
            for metric, left, right in values
        )
    return tuple(output)


def _cohen_kappa(left: Sequence[int], right: Sequence[int]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    observed = sum(a == b for a, b in zip(left, right))/len(left)
    p_left, p_right = sum(left)/len(left), sum(right)/len(right)
    expected = p_left*p_right + (1-p_left)*(1-p_right)
    return None if abs(1-expected) <= 1e-15 else (observed-expected)/(1-expected)


def _binary_metrics(reference: Sequence[int], predicted: Sequence[int]) -> Mapping[str, float | None]:
    if len(reference) != len(predicted) or not reference:
        return {name: None for name in ("prevalence", "precision", "recall", "f1")}
    tp = sum(a == 1 and b == 1 for a, b in zip(reference, predicted))
    fp = sum(a == 0 and b == 1 for a, b in zip(reference, predicted))
    fn = sum(a == 1 and b == 0 for a, b in zip(reference, predicted))
    precision = tp/(tp+fp) if tp+fp else None
    recall = tp/(tp+fn) if tp+fn else None
    f1 = None if precision is None or recall is None or precision+recall == 0 else 2*precision*recall/(precision+recall)
    return {
        "prevalence": sum(reference)/len(reference), "precision": precision,
        "recall": recall, "f1": f1,
    }


def _per_label_comparisons(
    projects: Sequence[ProjectRatings], retained_ids: frozenset[str]
) -> tuple[EstimateComparison, ...]:
    output: list[EstimateComparison] = []
    for dimension in ("domains", "purposes"):
        labels = sorted({
            label for project in projects for rating in (*project.coders, project.model)
            if rating is not None and getattr(rating, dimension) is not None
            for label in getattr(rating, dimension)
        })
        for label in labels:
            rows: list[tuple[str, tuple[int, int, int], int, int]] = []
            for project in projects:
                coder_sets = tuple(getattr(coder, dimension) if coder else None for coder in project.coders)
                model_set = getattr(project.model, dimension) if project.model else None
                if any(value is None for value in (*coder_sets, model_set)):
                    continue
                coder_bits = tuple(int(label in value) for value in coder_sets)
                rows.append((
                    project.record_id,
                    coder_bits,
                    int(label in model_set),
                    int(human_supported(coder_sets, label)),
                ))
            sensitive_rows = [row for row in rows if row[0] in retained_ids]
            primary_support = sum(row[3] for row in rows)
            sensitivity_support = sum(row[3] for row in sensitive_rows)
            primary_metrics = _binary_metrics([r[3] for r in rows], [r[2] for r in rows])
            sensitivity_metrics = _binary_metrics([r[3] for r in sensitive_rows], [r[2] for r in sensitive_rows])
            primary_reportable = support_band(primary_support) != "fewer_than_10_descriptive_only"
            sensitivity_reportable = support_band(sensitivity_support) != "fewer_than_10_descriptive_only"
            for metric in ("prevalence", "precision", "recall", "f1"):
                left = primary_metrics[metric] if metric == "prevalence" or primary_reportable else None
                right = sensitivity_metrics[metric] if metric == "prevalence" or sensitivity_reportable else None
                output.append(_comparison(
                    "per_label", dimension, metric, label, "model_vs_majority_human",
                    left, right, "percentage_points",
                ))
            pair_specs = (
                ("C01_C02", 0, 1, False), ("C01_C03", 0, 2, False),
                ("C02_C03", 1, 2, False), ("model_C01", 0, 0, True),
                ("model_C02", 1, 0, True), ("model_C03", 2, 0, True),
            )
            for panel, left_index, right_index, model_left in pair_specs:
                def kappa_for(values):
                    if model_left:
                        return _cohen_kappa(
                            [row[2] for row in values],
                            [row[1][left_index] for row in values],
                        )
                    return _cohen_kappa(
                        [row[1][left_index] for row in values],
                        [row[1][right_index] for row in values],
                    )
                left = kappa_for(rows) if primary_reportable else None
                right = kappa_for(sensitive_rows) if sensitivity_reportable else None
                output.append(_comparison(
                    "per_label", dimension, "cohen_kappa", label, panel,
                    left, right, "absolute",
                ))
    return tuple(output)


def analyse_instrument_validity_sensitivity(
    projects: Sequence[ProjectRatings],
    response_results: Iterable[StructuralValidityResult],
) -> InstrumentSensitivityReport:
    """Recompute estimates after whole-project exclusion without mutating primary data."""

    primary = tuple(projects)
    project_ids = tuple(project.record_id for project in primary)
    reviewer_ids: dict[str, frozenset[str]] = {}
    model_ids: set[str] = set()
    for project in primary:
        if project.instrument_version != VERSION or not project.validation_included:
            raise InstrumentSensitivityError("Primary sensitivity projects must be included candidate-0.7 records")
        present = tuple(coder for coder in project.coders if coder is not None)
        ids = frozenset(coder.reviewer_id for coder in present)
        if len(present) != EXPECTED_CODER_COUNT or len(ids) != EXPECTED_CODER_COUNT:
            raise InstrumentSensitivityError(
                f"Project {project.record_id} does not contain exactly three distinct scratch coders"
            )
        reviewer_ids[project.record_id] = ids
        if project.model is None or not project.model.valid:
            raise InstrumentSensitivityError(f"Project {project.record_id} lacks a complete model panel")
        model_ids.add(project.record_id)

    population = matched_panel_sensitivity_population(
        project_ids, response_results,
        reviewer_ids_by_project=reviewer_ids, model_record_ids=model_ids,
    )
    retained = frozenset(population.retained_project_ids)
    for project in primary:
        if project.record_id not in retained:
            continue
        for rating in (*project.coders, project.model):
            if rating is None or any(
                getattr(rating, dimension) is None
                for dimension in ("domains", "purposes", "equity_tag", "covid_tag")
            ):
                raise InstrumentSensitivityError(
                    f"Retained project {project.record_id} lacks a complete matched human-model panel"
                )

    replacement = _replacement_comparisons(primary, retained)
    per_label = _per_label_comparisons(primary, retained)
    identical = population.affected_response_count == 0
    if identical and any(
        item.primary_estimate != item.sensitivity_estimate
        for item in (*replacement, *per_label)
    ):
        raise AssertionError("Zero-affected sensitivity estimates must equal primary estimates")
    return InstrumentSensitivityReport(population, replacement, per_label, identical)
