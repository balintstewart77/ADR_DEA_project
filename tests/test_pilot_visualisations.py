from pathlib import Path

import pytest

from analysis.validation.build_pilot_visualisations import (
    HEATMAP_COLORS,
    PilotVisualisationError,
    build_private_coder_summary,
    build_record_dimension_summary,
    classify_binary_tag,
    classify_three_values,
    validate_output_separation,
)


def test_heatmap_colors_distinguish_majority_from_three_way_split():
    assert HEATMAP_COLORS == {
        "all_agree": "#5AAE61",
        "two_vs_one": "#F6C85F",
        "split": "#D6604D",
    }


def test_categorical_agreement_states():
    unanimous = classify_three_values({"C01": "A", "C02": "A", "C03": "A"})
    assert unanimous.agreement_pattern == "all_agree"
    assert unanimous.pairwise_exact_count == 3
    two_one = classify_three_values({"C01": "A", "C02": "A", "C03": "B"})
    assert two_one.agreement_pattern == "two_vs_one"
    assert two_one.majority_category == "A"
    split = classify_three_values({"C01": "A", "C02": "B", "C03": "C"})
    assert split.agreement_pattern == "split"
    assert split.majority_category == "No majority / split judgement"


def test_binary_tag_agreement_states_have_no_split_state():
    assert classify_binary_tag({"C01": "1", "C02": "1", "C03": "1"}).agreement_pattern == (
        "all_agree_positive"
    )
    assert classify_binary_tag({"C01": "0", "C02": "0", "C03": "0"}).agreement_pattern == (
        "all_agree_negative"
    )
    assert classify_binary_tag({"C01": "1", "C02": "0", "C03": "0"}).agreement_pattern == (
        "two_vs_one"
    )


def ready_rows(record_ids=("SYN-001",)):
    rows = []
    for record_id in record_ids:
        for coder, domain, purpose, sufficiency, fit, confidence in (
            ("C01", "A", "P1", "Sufficient", "Fit", "High"),
            ("C02", "A", "P1", "Sufficient", "Fit", "High"),
            ("C03", "B", "P2", "Insufficient", "No Fit", "Low"),
        ):
            rows.append({
                "record_id": record_id,
                "coder_id": coder,
                "research_domains": domain,
                "analytical_purposes": purpose,
                "covid_tag": "0",
                "equity_tag": "1",
                "register_sufficiency": sufficiency,
                "taxonomy_fit": fit,
                "confidence": confidence,
                "note_present": "1" if coder == "C03" else "0",
            })
    return rows


def record_rows(record_ids=("SYN-001",)):
    rows = []
    for record_id in record_ids:
        for dimension, sets in (
            ("Research Domains", ("A", "A", "B")),
            ("Analytical Purposes", ("P1", "P1", "P2")),
        ):
            rows.append({
                "record_id": record_id,
                "classification_dimension": dimension,
                "complete_set_pattern": "two_vs_one",
                "C01_set": sets[0],
                "C02_set": sets[1],
                "C03_set": sets[2],
                "C01_C02_exact": "1",
                "C01_C03_exact": "0",
                "C02_C03_exact": "0",
                "C01_C02_jaccard": "1.0",
                "C01_C03_jaccard": "0.0",
                "C02_C03_jaccard": "0.0",
            })
    return rows


def test_record_dimension_summary_contains_seven_neutral_rows_per_record():
    rows = build_record_dimension_summary(record_rows(), ready_rows())
    assert len(rows) == 7
    assert {row["dimension_type"] for row in rows} == {"set", "binary_tag", "categorical"}
    assert all("coder_id" not in row for row in rows)
    assert all("outlier" not in str(row).lower() for row in rows)


def test_private_summary_identifies_lone_dissenter_without_loaded_labels():
    rows, _ = build_private_coder_summary(record_rows(), ready_rows())
    by_coder = {row["coder_id"]: row for row in rows}
    assert by_coder["C03"]["domain_lone_dissenter_count"] == 1
    assert by_coder["C03"]["purpose_lone_dissenter_count"] == 1
    assert by_coder["C03"]["sufficiency_lone_dissenter_count"] == 1
    assert by_coder["C03"]["low_confidence_count"] == 1


def test_private_output_must_be_separate_and_restricted(tmp_path):
    shared = tmp_path / "preregistration" / "pilot_analysis"
    restricted = tmp_path / "preregistration_restricted" / "pilot_private_review"
    validate_output_separation(shared, restricted)
    with pytest.raises(PilotVisualisationError, match="must be separate"):
        validate_output_separation(shared, shared)
    with pytest.raises(PilotVisualisationError, match="preregistration_restricted"):
        validate_output_separation(shared, tmp_path / "private")
