from pathlib import Path

import pytest

from analysis.validation.build_private_pilot_heatmap import (
    PrivateHeatmapError,
    build_expanded_rows,
    build_wide_rows,
    classify_coder_cells,
    display_value,
    validate_expanded_matrix,
    validate_private_output_path,
)


def synthetic_inputs():
    ready_rows = []
    record_rows = []
    summary_rows = []
    for index in range(1, 11):
        record_id = f"SYN-{index:03}"
        coder_values = {
            "C01": {
                "research_domains": "Education & Skills",
                "analytical_purposes": "Descriptive Monitoring",
                "register_sufficiency": "Sufficient",
                "taxonomy_fit": "Fit",
                "confidence": "High",
            },
            "C02": {
                "research_domains": "Education & Skills",
                "analytical_purposes": "Outcome Tracking",
                "register_sufficiency": "Sufficient",
                "taxonomy_fit": "Fit",
                "confidence": "Medium",
            },
            "C03": {
                "research_domains": "Health & Social Care",
                "analytical_purposes": "Risk Prediction / Early Identification",
                "register_sufficiency": "Sufficient",
                "taxonomy_fit": "No Fit",
                "confidence": "Low",
            },
        }
        for coder, values in coder_values.items():
            ready_rows.append({"record_id": record_id, "coder_id": coder, **values})
        record_rows.extend([
            {
                "record_id": record_id,
                "classification_dimension": "Research Domains",
                "complete_set_pattern": "two_vs_one",
                "C01_set": coder_values["C01"]["research_domains"],
                "C02_set": coder_values["C02"]["research_domains"],
                "C03_set": coder_values["C03"]["research_domains"],
            },
            {
                "record_id": record_id,
                "classification_dimension": "Analytical Purposes",
                "complete_set_pattern": "all_sets_distinct",
                "C01_set": coder_values["C01"]["analytical_purposes"],
                "C02_set": coder_values["C02"]["analytical_purposes"],
                "C03_set": coder_values["C03"]["analytical_purposes"],
            },
        ])
        summary_rows.extend([
            {"record_id": record_id, "dimension": "Research Domains", "agreement_pattern": "two_vs_one"},
            {"record_id": record_id, "dimension": "Analytical Purposes", "agreement_pattern": "all_sets_distinct"},
            {"record_id": record_id, "dimension": "Register sufficiency", "agreement_pattern": "all_agree"},
            {"record_id": record_id, "dimension": "Taxonomy fit", "agreement_pattern": "two_vs_one"},
            {"record_id": record_id, "dimension": "Confidence", "agreement_pattern": "split"},
        ])
    return record_rows, ready_rows, summary_rows


def test_cell_states_for_all_agree_two_vs_one_and_split():
    unanimous = classify_coder_cells({"C01": "A", "C02": "A", "C03": "A"}, "all_agree")
    assert set(unanimous.values()) == {("majority_match", "green")}
    two_one = classify_coder_cells({"C01": "A", "C02": "A", "C03": "B"}, "two_vs_one")
    assert two_one["C01"] == ("majority_match", "green")
    assert two_one["C03"] == ("lone_dissenter", "red")
    split = classify_coder_cells({"C01": "A", "C02": "B", "C03": "C"}, "split")
    assert set(split.values()) == {("split_all_different", "amber")}


def test_display_abbreviations_are_compact_and_deterministic():
    assert display_value("Domains", "Education & Skills | Labour Market & Employment") == "Edu|Lab"
    assert display_value(
        "Purposes", "Descriptive Monitoring | Life-Course / Trajectory Analysis"
    ) == "Desc|Traj"
    assert display_value("Sufficiency", "Partially sufficient") == "P"
    assert display_value("TaxonomyFit", "Cannot assess from register entry") == "CA"
    assert display_value("Confidence", "Low") == "L"


def test_expanded_matrix_is_exactly_ten_by_fifteen_with_150_classified_cells():
    rows = build_expanded_rows(*synthetic_inputs())
    record_ids, columns = validate_expanded_matrix(rows)
    assert len(record_ids) == 10
    assert len(columns) == 15
    assert len(rows) == 150
    assert {row["cell_color"] for row in rows} == {"green", "red", "amber"}
    assert all("Tag" not in row["dimension"] for row in rows)


def test_optional_wide_output_has_all_15_states_and_values():
    rows = build_expanded_rows(*synthetic_inputs())
    headers, wide = build_wide_rows(rows)
    assert len(wide) == 10
    assert len(headers) == 31
    assert sum(header.endswith("_state") for header in headers) == 15
    assert sum(header.endswith("_value") for header in headers) == 15


def test_private_path_enforcement(tmp_path):
    validate_private_output_path(tmp_path / "preregistration_restricted" / "pilot_private_review")
    with pytest.raises(PrivateHeatmapError, match="preregistration_restricted"):
        validate_private_output_path(tmp_path / "preregistration" / "pilot_analysis")
