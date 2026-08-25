from __future__ import annotations

import json
from math import ceil

import numpy as np
import pandas as pd

from analysis.scratch_coder_stage_b.agreement import exact_jaccard
from analysis.scratch_coder_stage_b.bootstrap import interval, samples
from analysis.scratch_coder_stage_b.config import LF_MOD, OUT, RAW_MOD, SEED
from analysis.scratch_coder_stage_b.metrics import ac1, contingency, jac, kappa, prf, tagstats
from analysis.scratch_coder_stage_b.performance import support_contingencies
from analysis.scratch_coder_stage_b.support import authorities, band, build_stage_b_data


def test_known_mod006_raw_vs_lf_representation_is_narrowly_accepted():
    model = next(x for x in authorities() if x.manifest_id == "MOD-006")
    assert model.expected_sha256 == RAW_MOD
    assert model.observed_sha256 == LF_MOD
    assert model.matched


def test_frozen_panel_reuses_stage_a_parsing_and_reconciles():
    data = build_stage_b_data()
    assert (len(data.responses), len(data.formal_ids), len(data.baseline_ids), len(data.hard_case_ids)) == (675, 225, 150, 75)
    assert data.hard_stratum_counts == {"domain_only": 25, "purpose_only": 25, "both": 25}
    assert data.structural_invalid_response_count == 0 and data.exposure_response_count == 1


def test_majority_support_bands_and_hard_cases_not_used():
    assert [band(x) for x in (0, 9, 10, 29, 30)] == ["RARE", "RARE", "LOW SUPPORT", "LOW SUPPORT", "STANDARD"]
    data = build_stage_b_data(); _, _, supports = support_contingencies(data)
    assert all(key[0] in {"Research Domains", "Analytical Purposes"} for key in supports)


def test_set_agreement_and_jaccard_edge_cases():
    assert jac(frozenset(), frozenset()) == 1.0
    assert jac(frozenset({"A"}), frozenset({"A", "B"})) == .5
    assert frozenset(("A", "B")) == frozenset(("B", "A"))


def test_binary_orientation_prf_and_kappa():
    c = contingency([1, 1, 0, 0], [1, 0, 1, 0])
    assert c == {"tp": 1, "fp": 1, "fn": 1, "tn": 1, "n": 4}
    assert prf(c) == {"precision": .5, "recall": .5, "f1": .5}
    assert kappa([0, 1, 0, 1], [0, 1, 0, 1]) == 1.0
    assert kappa([0, 0], [0, 0]) is None


def test_gwet_ac1_hand_fixtures_and_swap_symmetry():
    assert ac1([0, 1, 0, 1], [0, 1, 0, 1]) == 1.0
    assert ac1([0, 0, 0, 1], [0, 0, 1, 1]) == ac1([0, 0, 1, 1], [0, 0, 0, 1])
    stats = tagstats([1, 1, 0, 0], [1, 0, 1, 0])
    assert stats["raw_agreement"] == .5 and stats["positive_agreement"] == .5 and stats["negative_agreement"] == .5


def test_bootstrap_is_record_joint_deterministic_and_type7_threshold():
    assert np.array_equal(samples(3, 1, SEED)[0], samples(3, 1, SEED)[0])
    assert interval([None] * 1799 + [.5], 2000)["reported"] is False
    assert ceil(.9 * 2000) == 1800


def test_outputs_are_aggregate_masked_and_rare_labels_not_performance_rows():
    data = build_stage_b_data(); support = pd.read_csv(OUT / "label_support.csv"); perf = pd.read_csv(OUT / "per_label_model_performance.csv")
    rare = support[(support.dimension != "Cross-cutting tag") & (support.support_band == "RARE")].label
    assert not set(rare) & set(perf.label)
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUT.iterdir() if path.is_file())
    assert not any(record_id in text for record_id in data.formal_ids)
    assert not any((OUT / name).exists() for name in ("adjudication_population.csv", "disagreement_records.csv", "false_positive_records.csv", "false_negative_records.csv", "model_errors.csv"))


def test_notebook_root_discovery_and_saved_cross_checks():
    notebook = json.loads((OUT / "scratch_coder_stage_b_review.ipynb").read_text())
    source = "".join("".join(c["source"]) for c in notebook["cells"])
    assert "Path.cwd()" in source and "while ROOT" in source and ".head(" not in source
    assert "adjudication_population" not in source and "project_title" not in source
