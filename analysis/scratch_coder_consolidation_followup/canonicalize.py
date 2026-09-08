"""Install a verified consolidation as the stable result pair and record cleanup."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "analysis/scratch_coder_results"
RESULT_NAMES = {"consolidated_results.md", "run_metadata.json"}


def digest(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def repository_path(value: Path, *, directory: bool = True) -> Path:
    path = value.resolve()
    if not path.is_relative_to(ROOT) or "preregistration_restricted" in path.parts or path.is_symlink():
        raise ValueError(f"Unsupported housekeeping path: {value}")
    if directory and not path.is_dir():
        raise ValueError(f"Expected directory: {value}")
    return path


def inventory(directory: Path) -> dict:
    if directory.is_symlink():
        raise ValueError(f"Deletion target may not be a symlink: {directory}")
    entries = sorted(directory.iterdir())
    if {path.name for path in entries} != RESULT_NAMES or any(not path.is_file() or path.is_symlink() for path in entries):
        raise ValueError(f"Unexpected consolidation content: {directory}: {[path.name for path in entries]}")
    metadata = json.loads((directory / "run_metadata.json").read_text())
    return {
        "historical_directory": directory.relative_to(ROOT).as_posix(),
        "files": {path.name: digest(path) for path in entries},
        "recorded_status": metadata.get("status"),
        "recorded_generator_head": metadata.get("generator", {}).get("git_head"),
        "recorded_unresolved_count": metadata.get("unresolved_item_count"),
        "recorded_supplement": metadata.get("supplement", {}).get("directory"),
        "deletion_verified": False,
    }


def compact_comparison_evidence(followup: dict, evidence_path: str) -> dict:
    comparisons = followup["comparisons"]
    task_a = comparisons["task_a"]
    task_b = comparisons["task_b"]
    return {
        "evidence_path": evidence_path,
        "evidence_sha256": digest(ROOT / evidence_path)["sha256"],
        "reference": comparisons["reference"],
        "task_a": {
            "historical_run_path": task_a["path"], "commit": task_a["commit"], "recorded_result": task_a["result"],
            "lineage_identical": task_a["lineage_identical"], "source_files_identical": task_a["source_files_identical"],
            "generator_run_allowlist_entry_count": len(task_a["ignored_fields"]),
        },
        "task_b": {
            "historical_run_path": task_b["path"], "commit": task_b["commit"], "recorded_result": task_b["result"],
            "sections_1_11_and_appendices_identical": task_b["sections_1_11_and_appendices_identical"],
            "canonical_unresolved_identical": task_b["canonical_unresolved_identical"],
            "added_metadata_key": task_b["added_metadata_key"],
            "generator_run_allowlist_entry_count": len(task_b["ignored_metadata_fields"]),
            "rollup_counts": [{"cannot_establish": row["cannot_establish"], "count": row["count"]} for row in task_b["rollup"]],
        },
    }


def install(args):
    selected = repository_path(args.selected_run)
    followup_path = repository_path(args.followup_evidence, directory=False)
    supplement = repository_path(args.wilson_supplement)
    deletions = [repository_path(path) for path in args.delete_dir]
    if len(deletions) != len(set(deletions)) or selected not in deletions:
        raise ValueError("Deletion inventory must contain unique targets and include the selected historical run")
    if CANONICAL.exists():
        raise ValueError("Canonical directory already exists; inspect it before any replacement")
    selected_files = sorted(selected.iterdir())
    if {path.name for path in selected_files} != RESULT_NAMES:
        raise ValueError("Selected final run does not contain exactly the expected report pair")
    report_path = selected / "consolidated_results.md"
    metadata_path = selected / "run_metadata.json"
    selected_report = report_path.read_bytes()
    selected_metadata_bytes = metadata_path.read_bytes()
    selected_metadata = json.loads(selected_metadata_bytes)
    if selected_metadata.get("status") != "INCOMPLETE — unresolved metadata or reporting semantics":
        raise ValueError("Selected final run status is not the verified incomplete-with-disclosures status")
    if selected_metadata.get("unresolved_item_count") != 69 or len(selected_metadata.get("unresolved_items", [])) != 69:
        raise ValueError("Selected final run does not retain 69 historical unresolved entries")
    validation = selected_metadata.get("validation_results", {})
    supplement_record = selected_metadata.get("supplement", {})
    if (validation.get("supplement_interval_rows"), supplement_record.get("new_interval_rows"),
            supplement_record.get("originating_existing_intervals_retained"), supplement_record.get("equivalent_result_reuse")) != (
            37, 37, ["WSA0082", "WSA0083"], "WSA0074 from WSA0083"):
        raise ValueError("Selected run lacks the verified Wilson supplement coverage")
    if supplement_record.get("directory") != supplement.relative_to(ROOT).as_posix():
        raise ValueError("Selected run does not identify the retained approved Wilson supplement")
    if selected_metadata.get("document_sha256") != hashlib.sha256(selected_report).hexdigest():
        raise ValueError("Selected report hash does not match selected metadata")
    inventories = [inventory(path) for path in deletions]
    followup = json.loads(followup_path.read_text())
    if followup.get("status") != "complete_scope_assessment_no_intervals_calculated":
        raise ValueError("Follow-up comparison evidence is not complete")
    timestamp = datetime.now(timezone.utc).isoformat()
    selected_relative = selected.relative_to(ROOT).as_posix()
    followup_relative = followup_path.relative_to(ROOT).as_posix()
    metadata = json.loads(selected_metadata_bytes)
    metadata["output_directory"] = CANONICAL.relative_to(ROOT).as_posix()
    metadata["housekeeping"] = {
        "status": "canonical_pair_installed; deletions pending verification",
        "installed_at_utc": timestamp,
        "selected_final_run": {
            "historical_original_path": selected_relative,
            "report_sha256": digest(report_path)["sha256"],
            "metadata_sha256": digest(metadata_path)["sha256"],
            "selection_basis": "Successful Wilson-enriched consolidation: 37 supplementary rows, WSA0082/WSA0083 retained, WSA0074 reused, 69 original unresolved entries retained, structural validations passed.",
        },
        "canonical": {
            "report_path": "analysis/scratch_coder_results/results.md",
            "metadata_path": "analysis/scratch_coder_results/run_metadata.json",
            "report_sha256": hashlib.sha256(selected_report).hexdigest(),
        },
        "copy_comparison_allowlist": {
            "report": [],
            "metadata": ["output_directory", "housekeeping"],
            "result": "Report bytes identical; metadata identical outside the two named keys.",
        },
        "deletion_inventory": inventories,
        "task_a_task_b_evidence": compact_comparison_evidence(followup, followup_relative),
        "retained_references": {
            "analytical_source_archives": [
                "analysis/outputs_validation_scratch_20260824",
                "analysis/outputs_validation_scratch_stage_b_20260825",
                "analysis/outputs_validation_scratch_hard_case_strata_20260825",
            ],
            "wilson_supplement": supplement.relative_to(ROOT).as_posix(),
            "scope_manifest": "analysis/outputs_validation_consolidation_followup_20260907T132938546154Z/wilson_scope_manifest.json",
            "scope_assessment": "analysis/outputs_validation_consolidation_followup_20260907T132938546154Z/wilson_scope_assessment.md",
            "followup_evidence": followup_relative,
        },
        "normal_regeneration": {
            "invocation": ".venv/bin/python -B -m analysis.scratch_coder_consolidated",
            "canonical_destination": "analysis/scratch_coder_results",
            "default_wilson_supplement": supplement.relative_to(ROOT).as_posix(),
            "staging_before_replacement": True,
            "unsupplemented_canonical_replacement_guarded": True,
        },
        "historical_facts_preserved": ["generation_timestamp_utc", "generator.git_head", "generator.git_status_before", "generator.git_status_after_validation"],
        "active_documentation": ["analysis/scratch_coder_consolidated/README.md"],
    }
    comparison = json.loads(json.dumps(metadata))
    del comparison["housekeeping"]
    comparison["output_directory"] = selected_metadata["output_directory"]
    if comparison != selected_metadata:
        raise ValueError("Canonical metadata differs outside the documented housekeeping/path allowlist")
    CANONICAL.mkdir(exist_ok=False)
    (CANONICAL / "results.md").write_bytes(selected_report)
    (CANONICAL / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    parsed = json.loads((CANONICAL / "run_metadata.json").read_text())
    if (CANONICAL / "results.md").read_bytes() != selected_report or parsed != metadata:
        raise ValueError("Canonical pair read-back failed")
    print(json.dumps({"status": metadata["housekeeping"]["status"], "canonical": str(CANONICAL),
                      "report_sha256": metadata["document_sha256"], "deletion_targets": len(inventories)}, indent=2))


def finalize():
    if CANONICAL.is_symlink() or not CANONICAL.is_dir():
        raise ValueError("Canonical directory is unavailable")
    metadata_path = CANONICAL / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    housekeeping = metadata["housekeeping"]
    for item in housekeeping["deletion_inventory"]:
        path = ROOT / item["historical_directory"]
        if path.exists() or path.is_symlink():
            raise ValueError(f"Deletion target still exists: {path}")
        item["deletion_verified"] = True
    housekeeping["status"] = "complete"
    housekeeping["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    housekeeping["deleted_directories"] = [item["historical_directory"] for item in housekeeping["deletion_inventory"]]
    report_hash = digest(CANONICAL / "results.md")["sha256"]
    if report_hash != metadata["document_sha256"] or report_hash != housekeeping["canonical"]["report_sha256"]:
        raise ValueError("Canonical report changed before deletion finalisation")
    temporary = CANONICAL / ".run_metadata.json.tmp"
    temporary.write_text(json.dumps(metadata, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(metadata_path)
    if json.loads(metadata_path.read_text()) != metadata:
        raise ValueError("Final canonical metadata read-back failed")
    print(json.dumps({"status": "complete", "canonical": str(CANONICAL),
                      "deleted_directories": housekeeping["deleted_directories"]}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("--selected-run", type=Path, required=True)
    install_parser.add_argument("--followup-evidence", type=Path, required=True)
    install_parser.add_argument("--wilson-supplement", type=Path, required=True)
    install_parser.add_argument("--delete-dir", type=Path, action="append", required=True)
    subparsers.add_parser("finalize-deletions")
    args = parser.parse_args(argv)
    if args.command == "install":
        install(args)
    else:
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
