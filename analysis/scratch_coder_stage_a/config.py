"""Frozen paths and analytical constants for Stage A."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "analysis/outputs_validation_scratch_20260824"
RAW_EXPORT = ROOT / "preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv"
MANIFEST = ROOT / "preregistration/preregistration_artifact_manifest.csv"

CODERS = ("C01", "C02", "C03")
SEED_BOOTSTRAP = 20260714
BOOTSTRAP_REPLICATES = 2000
MINIMUM_VALID_REPLICATES = 1800

AUTHORITY_IDS = {
    "raw_export": "POST-028",
    "protocol": "PRO-018",
    "instrument": "RED-036",
    "validator": "RED-013",
    "field_specification": "RED-005",
    "branching_specification": "RED-006",
    "export_specification": "RED-007",
    "codebook": "RED-003",
    "label_mapping": "RED-017",
    "formal_assignment_crosswalk": "POST-019",
    "formal_assignment_metadata": "POST-022",
    "baseline_sample": "POST-009",
    "hard_case_sample": "POST-011",
    "taxonomy_rc2": "MOD-001",
    "production_model": "MOD-006",
}

DIMENSIONS = (
    "Research Domains",
    "Analytical Purposes",
    "Demographic disparities / equity",
    "COVID-19 & Pandemic",
)

POPULATION_ORDER = (
    "baseline",
    "baseline_exposure_sensitivity",
    "baseline_structural_sensitivity",
    "hard_case",
    "baseline_broad_usable",
    "baseline_strict_sufficient",
)
