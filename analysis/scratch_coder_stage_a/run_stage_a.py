"""Authoritative command-line entry point for Stage A aggregate analysis."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone

import nbformat
import numpy as np
import pandas as pd
import pytest
import yaml

from .agreement import run_replacement_analyses
from .config import BOOTSTRAP_REPLICATES, OUTPUT_DIR, RAW_EXPORT, ROOT, SEED_BOOTSTRAP
from .load import read_manifest_csv, sha256_file, verify_authorities
from .panels import build_stage_a_data
from .report import qa_rows, write_outputs
from .sufficiency import derive_sufficiency_subsets, summarise_sufficiency
from .taxonomy import summarise_taxonomy_fit
from .timing import summarise_timing


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def main() -> int:
    if OUTPUT_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite existing analysis run: {OUTPUT_DIR}")
    raw_before = sha256_file(RAW_EXPORT)
    authorities = verify_authorities()
    data = build_stage_a_data()
    subsets = derive_sufficiency_subsets(data)
    sufficiency = summarise_sufficiency(data)
    taxonomy = summarise_taxonomy_fit(data)
    timing = summarise_timing(data)
    qa = qa_rows(data)
    agreement = run_replacement_analyses(data, subsets)
    model_rows = read_manifest_csv("MOD-006")
    formal_titles = set(
        model_rows.loc[model_rows["Record ID"].isin(data.formal_ids), "Title"].astype(str)
    ) - {""}
    status = _git("status", "--short", "--untracked-files=all")
    head = _git("rev-parse", "HEAD")
    metadata = {
        "analysis_run_datetime": datetime.now(timezone.utc).isoformat(),
        "analysis_code_commit_or_worktree_state": {
            "head_commit": head,
            "worktree_dirty": bool(status),
            "changed_paths_at_run": status.splitlines(),
        },
        "python_version": sys.version,
        "package_versions": {
            "numpy": np.__version__, "pandas": pd.__version__, "PyYAML": yaml.__version__,
            "nbformat": nbformat.__version__, "pytest": pytest.__version__,
            "krippendorff_alpha": "repository analysis.validation.alpha",
            "masi_distance": "repository analysis.validation.metrics",
        },
        "platform": platform.platform(),
        "raw_export_relative_path": RAW_EXPORT.relative_to(ROOT).as_posix(),
        "raw_export_sha256": raw_before,
        "raw_export_bytes": RAW_EXPORT.stat().st_size,
        "raw_export_rows": data.raw_rows,
        "raw_export_columns": data.raw_columns,
        "protocol_path": next(item.path for item in authorities if item.role == "protocol"),
        "protocol_sha256": next(item.expected_sha256 for item in authorities if item.role == "protocol"),
        "taxonomy_identity": {"manifest_id": "MOD-001", "version": "dict-1.0-rc2"},
        "instrument_identity": {"manifest_id": "RED-036", "version": "redcap-candidate-0.7"},
        "validator_identity": {"manifest_id": "RED-013"},
        "sample_identity": {"baseline": "POST-009", "hard_case": "POST-011", "crosswalk": "POST-019"},
        "production_model_path": next(item.path for item in authorities if item.role == "production_model"),
        "production_model_sha256": next(item.expected_sha256 for item in authorities if item.role == "production_model"),
        "bootstrap_seed": SEED_BOOTSTRAP,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "quantile_method": "Hyndman-Fan Type 7 / linear",
        "verified_authorities": [item.__dict__ for item in authorities],
        "panel_design": {"coders": 3, "formal_records": 225, "baseline": 150, "hard_case": 75, "responses": 675},
        "raw_export_hash_after_analysis": None,
    }
    results = write_outputs(
        output_dir=OUTPUT_DIR, metadata=metadata, qa=qa, agreement=agreement,
        sufficiency=sufficiency, taxonomy=taxonomy, timing=timing,
        prohibited_ids=set(data.formal_ids), raw_sha=raw_before,
        prohibited_titles=formal_titles,
    )
    raw_after = sha256_file(RAW_EXPORT)
    if raw_after != raw_before:
        raise RuntimeError("Frozen raw export changed during analysis")
    metadata["raw_export_hash_after_analysis"] = raw_after
    metadata["raw_export_unchanged"] = True
    (OUTPUT_DIR / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "raw_sha256": raw_before,
        "formal_responses": len(data.responses),
        "baseline_records": len(data.baseline_ids),
        "hard_case_records": len(data.hard_case_ids),
        "structural_invalid_responses": data.structural_invalid_response_count,
        "exposure_flagged_responses": data.exposure_response_count,
        "broad_subset": len(subsets["broad"]),
        "strict_subset": len(subsets["strict"]),
        "output_directory": OUTPUT_DIR.relative_to(ROOT).as_posix(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
