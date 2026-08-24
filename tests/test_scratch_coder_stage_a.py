from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from random import Random

import nbformat
import numpy as np
import pandas as pd
import pytest

from analysis.scratch_coder_stage_a.agreement import (
    alpha_encoded,
    bootstrap_replacement,
    encode_panels,
    encoded_replacement_statistics,
)
from analysis.scratch_coder_stage_a.config import OUTPUT_DIR, RAW_EXPORT, ROOT
from analysis.scratch_coder_stage_a.load import resolve_manifest_row
from analysis.scratch_coder_stage_a.panels import build_stage_a_data, dimension_panels
from analysis.scratch_coder_stage_a.sufficiency import (
    SPLIT,
    SUFFICIENCY_LABELS,
    derive_sufficiency_subsets,
    majority_category,
)
from analysis.scratch_coder_stage_a.taxonomy import summarise_taxonomy_fit
from analysis.validation.alpha import krippendorff_alpha
from analysis.validation.bootstrap import percentile
from analysis.validation.intervals import wilson_interval
from analysis.validation.metrics import masi_distance, nominal_distance
from analysis.validation.replacement import DimensionPanel, replacement_panel_analysis
from scripts.validate_redcap_candidate import validate_scratch


RAW_SHA = "29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d"


@pytest.fixture(scope="module")
def stage_data():
    return build_stage_a_data()


def test_frozen_raw_export_is_hash_pinned_unchanged_and_ignored():
    assert hashlib.sha256(RAW_EXPORT.read_bytes()).hexdigest() == RAW_SHA
    row = resolve_manifest_row("POST-028")
    assert row["sha256"] == RAW_SHA
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(RAW_EXPORT.relative_to(ROOT))],
        cwd=ROOT,
    )
    assert result.returncode == 0


def test_formal_panel_and_strata_reconcile(stage_data):
    assert len(stage_data.responses) == 675
    assert len(stage_data.formal_ids) == 225
    assert len(stage_data.baseline_ids) == 150
    assert len(stage_data.hard_case_ids) == 75
    counts = stage_data.responses.groupby(["record_id", "coder"]).size()
    assert len(counts) == 675 and (counts == 1).all()


def test_candidate_07_structural_validation_passes_without_repair(stage_data):
    assert stage_data.structural_invalid_response_count == 0
    assert stage_data.structural_invalid_ids == frozenset()


def test_zero_is_substantive_and_checkbox_applicability_uses_parent(stage_data):
    assert set(stage_data.responses["exposure"]) == {0, 1}
    assert set(stage_data.responses["equity"]) <= {0, 1}
    assert set(stage_data.responses["covid"]) <= {0, 1}
    summaries = summarise_taxonomy_fit(stage_data)
    for population in ("baseline", "hard_case"):
        expected = int(stage_data.responses.query("population == @population")["taxonomy_fit"].isin([2, 3]).sum())
        assert {row["applicable_denominator"] for row in summaries["issues"] if row["population"] == population} == {expected}


def test_classification_sets_are_unordered_and_unclear_rules_are_enforced():
    assert frozenset(("A", "B")) == frozenset(("B", "A"))
    base = {
        "assignment_id": "A7K3M9Q2", "instrument_ver": "redcap-candidate-0.7",
        "record_kind": 3, "sc_exposure": 0, "sc_domains": [12],
        "sc_purposes": [8], "sc_covid": 0, "sc_equity": 0,
        "sc_sufficiency": 2, "sc_taxonomy_fit": 4, "sc_confidence": 2,
        "sc_tax_issue": [], "sc_note": "Synthetic limited evidence.",
    }
    assert validate_scratch(base) == []
    assert "Unclear domain plus substantive domain" in validate_scratch({**base, "sc_domains": [1, 12]})
    assert "purposes must contain one or two responses" in validate_scratch({**base, "sc_purposes": [1, 2, 3]})


def test_masi_ordering_perfect_alpha_and_tag_zero():
    identical = float(masi_distance(frozenset({"A"}), frozenset({"A"})))
    partial = float(masi_distance(frozenset({"A"}), frozenset({"A", "B"})))
    disjoint = float(masi_distance(frozenset({"A"}), frozenset({"B"})))
    assert identical < partial < disjoint
    perfect = krippendorff_alpha(((0, 0, 0), (1, 1, 1)), nominal_distance)
    assert perfect.alpha == pytest.approx(1.0)
    assert krippendorff_alpha(((0, 0, 0), (0, 1, 1)), nominal_distance).valid


def _synthetic_panels():
    return (
        DimensionPanel("r1", frozenset({"A"}), frozenset({"A"}), frozenset({"A"}), frozenset({"A"})),
        DimensionPanel("r2", frozenset({"B"}), frozenset({"B"}), frozenset({"A", "B"}), frozenset({"B"})),
        DimensionPanel("r3", frozenset({"A", "B"}), frozenset({"A"}), frozenset({"B"}), frozenset({"A", "B"})),
    )


def test_replacement_construction_and_encoded_equivalence():
    panels = _synthetic_panels()
    canonical = replacement_panel_analysis(panels, masi_distance)
    encoded = encoded_replacement_statistics(encode_panels(panels, masi_distance))
    assert encoded["alpha_ABC"] == pytest.approx(canonical.alpha_abc.alpha)
    assert encoded["alpha_LBC"] == pytest.approx(canonical.alpha_lbc.alpha)
    changed = list(panels)
    changed[0] = DimensionPanel("r1", panels[0].coder_a, panels[0].coder_b, panels[0].coder_c, frozenset({"B"}))
    assert replacement_panel_analysis(changed, masi_distance).alpha_abc == canonical.alpha_abc


def test_record_bootstrap_retains_duplicate_draws_is_joint_and_deterministic():
    encoded = encode_panels(_synthetic_panels(), masi_distance)
    first = bootstrap_replacement(encoded, attempts=10, seed=20260714)
    second = bootstrap_replacement(encoded, attempts=10, seed=20260714)
    assert first == second
    generator = Random(20260714)
    indices = np.array([generator.randrange(3) for _ in range(3)])
    assert len(set(indices.tolist())) < 3  # first draw deliberately contains a duplicate
    expected = encoded_replacement_statistics(encoded, indices)
    assert all(first[0][name] == pytest.approx(value) for name, value in expected.items() if value is not None)
    assert first[0]["sample_n"] == 3


def test_type7_percentile_and_undefined_alpha_are_explicit():
    assert percentile([0.0, 10.0], 0.25) == pytest.approx(2.5)
    undefined = krippendorff_alpha(((0, 0, 0), (0, 0, 0)), nominal_distance)
    assert not undefined.valid
    assert undefined.alpha is None
    assert undefined.undefined_reason == "expected_disagreement_zero"


def test_sufficiency_majority_subsets_and_wilson(stage_data):
    assert majority_category((1, 1, 2), SUFFICIENCY_LABELS) == "Sufficient"
    assert majority_category((1, 2, 3), SUFFICIENCY_LABELS) == SPLIT
    subsets = derive_sufficiency_subsets(stage_data)
    assert subsets["strict"] <= subsets["broad"] <= stage_data.baseline_ids
    interval = wilson_interval(75, 150)
    assert interval.lower < 0.5 < interval.upper


def test_cannot_assess_and_multilabel_issue_denominators_remain_separate(stage_data):
    taxonomy = summarise_taxonomy_fit(stage_data)
    assert any(row["category"] == "Cannot assess from register entry" for row in taxonomy["responses"])
    assert any(row["category"] == "No majority / split judgement" for row in taxonomy["records"])
    assert all(row["note"] == "Percentages may sum to more than 100%." for row in taxonomy["issues"])


def test_all_four_dimensions_have_complete_baseline_panels(stage_data):
    for dimension in ("Research Domains", "Analytical Purposes", "Demographic disparities / equity", "COVID-19 & Pandemic"):
        panels = dimension_panels(stage_data, stage_data.baseline_ids, dimension)
        result = replacement_panel_analysis(panels, masi_distance if "Domains" in dimension or "Purposes" in dimension else nominal_distance)
        assert len(result.common_record_ids) == 150


def test_trackable_outputs_are_aggregate_masked_and_not_stage_b(stage_data):
    assert OUTPUT_DIR.is_dir()
    prohibited_names = {"disagreement_records.csv", "adjudication_population.csv", "model_errors.csv", "majority_vs_model.csv"}
    assert not prohibited_names & {path.name for path in OUTPUT_DIR.iterdir()}
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUTPUT_DIR.iterdir() if path.is_file())
    assert not any(record_id in text for record_id in stage_data.formal_ids)
    assert "per-label precision" not in text.lower()


def test_review_notebook_has_no_raw_row_display_or_disagreement_logic():
    notebook = nbformat.read(OUTPUT_DIR / "scratch_coder_stage_a_review.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells)
    assert ".head(" not in source
    assert "disagreement_records" not in source
    assert "project_title" not in source
    assert "datasets_used" not in source
    assert all(not cell.get("outputs") for cell in notebook.cells if cell.cell_type == "code")


def test_saved_bootstrap_has_2000_rows_per_population_dimension():
    rows = pd.read_csv(OUTPUT_DIR / "bootstrap_replicates.csv")
    counts = rows.groupby(["population", "dimension"]).size()
    assert len(counts) == 24
    assert (counts == 2000).all()
    assert set(rows["sample_n"]) <= {75, 92, 148, 149, 150}


def test_run_metadata_and_raw_final_hash():
    metadata = json.loads((OUTPUT_DIR / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["raw_export_sha256"] == metadata["raw_export_hash_after_analysis"] == RAW_SHA
    assert metadata["bootstrap_seed"] == 20260714
    assert metadata["bootstrap_replicates"] == 2000
    assert metadata["masking"] == {
        "real_source_ids_detected": 0,
        "real_project_titles_detected": 0,
        "record_level_disagreement_outputs": 0,
        "stage_b_outputs": 0,
    }
