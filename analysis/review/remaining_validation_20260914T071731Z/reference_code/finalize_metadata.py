"""Record audit provenance and confirm that every immutable input is unchanged.

Usage (repository root, after run_all.py):
    .venv/bin/python -B analysis/review/remaining_validation_20260914T071731Z/reference_code/finalize_metadata.py

Writes audit_metadata.json inside the audit directory only.
"""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy  # noqa: E402
import pandas  # noqa: E402

import common as C  # noqa: E402

AUDIT_PREFIX = C.rel(C.AUDIT_DIR) + "/"


def main() -> int:
    before = json.loads((C.AUDIT_DIR / ".input_hashes_before.json").read_text())
    inputs, changed = {}, []
    for path, record in before.items():
        current = C.ROOT / path
        after = {"sha256": C.sha256(current), "bytes": current.stat().st_size} if current.exists() else None
        unchanged = after == record
        inputs[path] = {"sha256_before": record["sha256"], "sha256_after": after["sha256"] if after else None,
                        "bytes": record["bytes"], "unchanged": unchanged}
        if not unchanged:
            changed.append(path)
    status_before = [line for line in (C.AUDIT_DIR / ".git_status_before.txt").read_text().splitlines() if line]
    status_after = [line for line in C.git("status", "--porcelain=v1", "--untracked-files=all").splitlines() if line]
    outside_before = [line for line in status_before if AUDIT_PREFIX not in line]
    outside_after = [line for line in status_after if AUDIT_PREFIX not in line]
    summary = json.loads((C.AUDIT_DIR / "reference_results_summary.json").read_text())
    outputs = {name: C.sha256(C.AUDIT_DIR / name) for name in ("audit_report.md", "verification_ledger.csv", "reference_results_summary.json")
               if (C.AUDIT_DIR / name).exists()}
    metadata = {
        "audit": "Independent audit of post hoc hard-case strata, baseline Wilson supplement and canonical-report integration",
        "audit_directory": C.rel(C.AUDIT_DIR),
        "audit_started_utc": "2026-09-14T07:17:31Z",
        "metadata_written_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": C.git("rev-parse", "HEAD").strip(),
        "git_status_before_audit": status_before,
        "git_status_after_audit_outside_audit_directory": outside_after,
        "working_tree_unchanged_outside_audit_directory": outside_before == outside_after,
        "inputs_unchanged": not changed,
        "changed_inputs": changed,
        "input_count": len(inputs),
        "inputs": inputs,
        "selected_artifacts": {
            "canonical_report": ["analysis/scratch_coder_results/results.md", "analysis/scratch_coder_results/run_metadata.json"],
            "strata_outputs": "analysis/outputs_validation_scratch_hard_case_strata_20260825/",
            "strata_code": "analysis/scratch_coder_hard_case_strata/ (run at HEAD cc5cf7d while untracked; committed 298471a on 2026-08-26T09:17:23Z)",
            "wilson_supplement": "analysis/outputs_validation_wilson_baseline_20260907T142427225531Z/ (canonical metadata supplement.directory and housekeeping.retained_references)",
            "wilson_scope": "analysis/outputs_validation_consolidation_followup_20260907T132938546154Z/",
            "wilson_generator_commit": "dcf763bdec92a5f65d61cff4eeffaae6ded675fd",
            "superseded_not_used": "analysis/outputs_validation_wilson_baseline_20260907T142055636248Z (listed untracked in the supplement's pre-run git status; absent now; not referenced by canonical metadata)",
            "protocol": "preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx (PRO-018)",
            "taxonomy": "taxonomy_data_dictionary.yaml (MOD-001, rc2) with REDCap candidate 0.7 dictionary (RED-036) label sets",
            "prior_audits": ["analysis/outputs_validation_scratch_20260824/review/2026-08-24_claude_code_independent_audit.md",
                             "analysis/scratch_coder_stage_b/review/claude_independent_audit_b"],
        },
        "historical_code_evidence": {
            "strata_code_commit_vs_head_diff": C.git("diff", "--stat", "298471a", "HEAD", "--", "analysis/scratch_coder_hard_case_strata").strip(),
            "strata_dependencies_cc5cf7d_vs_head_diff": C.git("diff", "--stat", "cc5cf7dcede8134f24bd1ebb08b564f217da21f1", "HEAD", "--",
                                                              "analysis/scratch_coder_stage_a", "analysis/scratch_coder_stage_b", "analysis/validation",
                                                              "scripts/validate_redcap_candidate.py").strip(),
            "wilson_generator_dcf763b_vs_head_diff": C.git("diff", "--stat", "dcf763bdec92a5f65d61cff4eeffaae6ded675fd", "HEAD", "--",
                                                           "analysis/scratch_coder_consolidation_followup/wilson_supplement.py",
                                                           "analysis/scratch_coder_consolidated/supplement.py", "analysis/validation/intervals.py").strip(),
        },
        "reference_code": {path.name: C.sha256(path) for path in sorted((C.AUDIT_DIR / "reference_code").glob("*.py"))},
        "outputs": outputs,
        "ledger": summary["ledger"],
        "masking_scan": summary.get("masking"),
        "environment": {"python": sys.version, "platform": platform.platform(), "numpy": numpy.__version__, "pandas": pandas.__version__,
                        "decimal_precision_digits": 80, "git": C.git("--version").strip(), "production_modules_imported": False},
        "randomness": {"generator": "Python random.Random (Mersenne Twister)", "seed": C.SEED, "replicates": C.ATTEMPTS,
                       "draw": "randrange(25) x 25 per replicate, fresh generator per stratum x dimension x pair (set) and per stratum x dimension (replacement)",
                       "resampling_unit": "record; A/B/C/L ratings resampled together",
                       "record_order": "ascending Record ID string order: taken from the production convention (not documented in saved methods) and corroborated by exact reproduction of all 48,000 saved replicate rows"},
        "comparison_criteria": {"float_statistics_absolute": C.TOL_FLOAT, "wilson_bounds_absolute": C.TOL_WILSON, "z_constant_absolute": C.TOL_Z,
                                "integers_and_strings": "exact equality", "display_values": "exact equality with Python format(value, '.3f') of the independent value",
                                "stochastic": "exact regeneration of saved draws; no distributional tolerance was needed",
                                "fixed_before_comparison": True},
        "restricted_access": {
            "files_read": [C.rel(C.RAW), C.rel(C.BASE), C.rel(C.HARD), C.rel(C.CROSS)],
            "export_columns_read": C.RAW_COLS, "sample_columns_read": C.SAMPLE_COLS,
            "not_accessed": ["preregistration_restricted/contacts", "preregistration_restricted/reserve_samples", "preregistration_restricted/trainer_only",
                             "preregistration_restricted/blinded_assignments", "preregistration_restricted/pilot_private_review",
                             "export owner_*/po_*/prop_* fields, project titles, datasets, sc_note, sc_exposure_note"],
            "identifiers_written": "none (masking scan over audit directory)",
        },
        "reproduction_commands": [
            ".venv/bin/python -B analysis/review/remaining_validation_20260914T071731Z/reference_code/run_all.py",
            ".venv/bin/python -B analysis/review/remaining_validation_20260914T071731Z/reference_code/finalize_metadata.py",
        ],
    }
    (C.AUDIT_DIR / "audit_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: metadata[k] for k in ("git_head", "inputs_unchanged", "changed_inputs", "input_count",
                                                "working_tree_unchanged_outside_audit_directory", "git_status_after_audit_outside_audit_directory",
                                                "historical_code_evidence", "outputs")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
