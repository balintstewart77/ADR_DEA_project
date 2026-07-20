"""Machine-readable schemas for blank preregistered output shells."""

from __future__ import annotations

import csv
from pathlib import Path


COMMON_COLUMNS = (
    "table_version",
    "population",
    "subset",
    "sample_set",
    "classification_dimension",
    "metric",
    "label",
    "panel",
    "replacement_position",
    "respondent_or_project_level",
    "recruitment_route",
    "response_unit",
    "record_label_response_pattern",
    "unique_record_count",
    "completion_definition",
    "issue_code",
    "point_estimate",
    "lower_interval",
    "upper_interval",
    "interval_type",
    "attempted_bootstrap_replicates",
    "valid_bootstrap_replicates",
    "invalid_bootstrap_replicates",
    "support_count",
    "support_band",
    "reporting_caution_or_status",
    "numerator",
    "denominator",
    "denominator_definition",
    "notes",
)

OUTPUT_SHELLS = (
    "sample_flow_and_completion.csv",
    "replacement_panel_alphas.csv",
    "replacement_differences.csv",
    "sufficiency_sensitivity.csv",
    "per_label_diagnostics.csv",
    "tag_diagnostics.csv",
    "evidence_and_taxonomy_diagnostics.csv",
    "project_owner_results.csv",
    "adjudication_issue_frequencies.csv",
    "release_trigger_summary.csv",
)


def verify_header_only_shells(root: Path) -> None:
    """Fail if a prespecified shell is absent, populated, or has a stale header."""

    for filename in OUTPUT_SHELLS:
        path = root / filename
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        if rows != [list(COMMON_COLUMNS)]:
            raise ValueError(f"Output shell is missing, populated, or malformed: {path}")
