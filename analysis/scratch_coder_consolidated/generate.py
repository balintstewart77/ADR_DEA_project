"""Generate the stable scratch-coder report through a validated staging directory."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import sys

from .preflight import Fatal, PACKAGE, ROOT, Sources, git, sha
from .report import DIAGNOSTIC, Report, esc
from .supplement import WilsonSupplement

CANONICAL = ROOT / "analysis/scratch_coder_results"
DEFAULT_SUPPLEMENT = ROOT / "analysis/outputs_validation_wilson_baseline_20260907T142427225531Z"
OUTPUT_NAMES = {"results.md", "run_metadata.json"}


def output_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def outside_task_status(status, staging):
    if status is None:
        return None
    prefixes = [PACKAGE.relative_to(ROOT).as_posix() + "/"]
    try:
        prefixes.append(staging.relative_to(ROOT).as_posix() + "/")
    except ValueError:
        pass
    return [line for line in status.splitlines() if not any(line[3:].startswith(prefix) for prefix in prefixes)]


def existing_housekeeping():
    if not CANONICAL.exists():
        return None
    if CANONICAL.is_symlink() or not CANONICAL.is_dir():
        raise Fatal("Canonical results path is not a regular directory")
    actual = {path.name for path in CANONICAL.iterdir() if path.is_file()}
    if actual != OUTPUT_NAMES or any(path.is_dir() for path in CANONICAL.iterdir()):
        raise Fatal(f"Canonical directory contains unexpected content: {sorted(path.name for path in CANONICAL.iterdir())}")
    metadata = json.loads((CANONICAL / "run_metadata.json").read_text())
    if metadata.get("generator", {}).get("identity") != "scratch_coder_consolidated v2" or "housekeeping" not in metadata:
        raise Fatal("Canonical directory is not an established scratch-coder result pair")
    if sha((CANONICAL / "results.md").read_bytes()) != metadata.get("document_sha256"):
        raise Fatal("Existing canonical report does not match its metadata hash")
    return copy.deepcopy(metadata["housekeeping"])


def staging_directory(requested: Path | None) -> tuple[Path, bool]:
    if requested is not None:
        path = requested.resolve()
        temporary_root = Path(tempfile.gettempdir()).resolve()
        if not path.is_relative_to(temporary_root) or path.is_symlink():
            raise Fatal(f"--staging-output must be a new directory below {temporary_root}")
        path.mkdir(exist_ok=False)
        return path, True
    CANONICAL.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=".scratch_coder_results_staging_", dir=CANONICAL.parent)), False


def clean_staging(path: Path):
    """Remove only known generator staging files and their now-empty directory."""
    for name in ("results.md", "run_metadata.json", ".run_metadata.json.tmp", ".results.md.tmp"):
        candidate = path / name
        if candidate.exists() and candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()
    if path.exists() and not any(path.iterdir()):
        path.rmdir()


def publish_canonical(staging: Path):
    """Swap a validated pair into place and restore the old pair on failure."""
    if {path.name for path in staging.iterdir()} != OUTPUT_NAMES:
        raise Fatal("Staging directory does not contain exactly the canonical result pair")
    previous = CANONICAL.parent / ".scratch_coder_results_previous"
    if previous.exists() or previous.is_symlink():
        raise Fatal("Unexpected prior canonical-swap directory exists")
    had_previous = CANONICAL.exists()
    if had_previous:
        os.rename(CANONICAL, previous)
    try:
        os.rename(staging, CANONICAL)
    except Exception:
        if had_previous and previous.exists() and not CANONICAL.exists():
            os.rename(previous, CANONICAL)
        raise
    if had_previous:
        for name in OUTPUT_NAMES:
            candidate = previous / name
            if not candidate.is_file() or candidate.is_symlink():
                raise Fatal("Unexpected file in previous canonical pair after successful swap")
            candidate.unlink()
        previous.rmdir()


def main(argv=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--wilson-supplement", type=Path, default=DEFAULT_SUPPLEMENT,
                       help="Validated Wilson supplement (defaults to the approved retained artifact)")
    group.add_argument("--without-wilson-supplement", action="store_const", const=None,
                       dest="wilson_supplement", help="Audit-only unsupplemented render; requires --staging-output")
    parser.add_argument("--staging-output", type=Path,
                        help="Validation-only output below the system temporary directory; never replaces canonical results")
    args = parser.parse_args(argv)
    if not sys.dont_write_bytecode:
        print("Use Python -B (or PYTHONDONTWRITEBYTECODE=1) to prevent caches.", file=sys.stderr)
        return 2
    if args.wilson_supplement is None and args.staging_output is None:
        print("Refusing to replace canonical results with an unsupplemented report; use --staging-output for that audit path.", file=sys.stderr)
        return 2

    housekeeping = existing_housekeeping()
    staging, caller_owned_staging = staging_directory(args.staging_output)
    before = git("status", "--porcelain=v1", "--untracked-files=all")
    actual_args = list(sys.argv[1:] if argv is None else argv)
    invocation = [sys.executable, "-B", "-m", "analysis.scratch_coder_consolidated", *actual_args]
    meta = dict(
        generator={
            "identity": "scratch_coder_consolidated v2",
            "invocation": invocation,
            "configuration": {
                "canonical_output_directory": CANONICAL.relative_to(ROOT).as_posix(),
                "wilson_supplement": output_label(args.wilson_supplement.resolve()) if args.wilson_supplement else None,
                "validation_only_staging": caller_owned_staging,
            },
            "git_head": git("rev-parse", "HEAD"),
            "git_status_before": before,
            "source_hashes": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(PACKAGE.iterdir()) if p.suffix in (".py", ".json", ".md")},
        },
        generation_timestamp_utc=datetime.now(timezone.utc).isoformat(),
        output_directory=CANONICAL.relative_to(ROOT).as_posix(),
        validation_staging_directory=output_label(staging),
        write_scope="Both deliverables are validated in a temporary staging directory before the canonical pair is replaced.",
        boundaries={"source_directories_read_only": True, "restricted_tree_accessed": False, "analysis_pipelines_executed": False,
                    "owner_inputs_accessed": False, "git_mutations": False, "source_directories_deleted": False},
    )
    if housekeeping is not None:
        meta["housekeeping"] = housekeeping
    sources = Sources(meta)
    try:
        sources.load()
        supplement = WilsonSupplement(args.wilson_supplement, sources) if args.wilson_supplement else None
        report = Report(sources, supplement=supplement)
        report.build()
        document = report.render()
        for report_table in report.tables:
            rendered = report.render_table(report_table)
            if rendered not in document:
                raise Fatal(f"Rendered table missing from document: {report_table['id']}")
            rows = [line for line in rendered.splitlines() if line.startswith("| ")][2:]
            if len(rows) != len(report_table["items"]):
                raise Fatal(f"Rendered table row count mismatch: {report_table['id']}")
            for line, item in zip(rows, report_table["items"], strict=True):
                cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line)[1:-1]]
                if cells[2:5] != [esc(item[key] or "") for key in ("displayed_estimate", "displayed_lower", "displayed_upper")]:
                    raise Fatal(f"Rendered estimate/bounds differ from validated source copy: {item['result_id']}")
            if report_table["population"] in ("hard_case", "overall") and DIAGNOSTIC not in rendered.splitlines()[0]:
                raise Fatal(f"Hard-case diagnostic header absent: {report_table['id']}")
        for section in range(12):
            if document.count(f"## Section {section} —") != 1:
                raise Fatal(f"Section coverage/order failure: {section}")
        if document.index("## Section 11 —") > document.index("## Appendix A"):
            raise Fatal("Appendix ordering failure")
        sources.unchanged()
        after_validation = git("status", "--porcelain=v1", "--untracked-files=all")
        if outside_task_status(before, staging) != outside_task_status(after_validation, staging):
            raise Fatal("Working-tree state outside task locations changed during generation")
        meta["generator"]["git_status_after_validation_before_publication"] = after_validation
        meta["validation_results"].update(
            source_hashes_before_after="passed", outside_task_working_tree="unchanged",
            hard_case_table_headers="passed", rendered_table_presence="passed",
            rendered_estimates_and_bounds="passed", final_section_structure="passed",
            canonical_output_guard="supplement required for canonical replacement",
        )
        meta["document_sha256"] = sha(document.encode("utf-8"))
        if housekeeping is not None:
            meta["housekeeping"]["canonical"]["report_sha256"] = meta["document_sha256"]
            meta["housekeeping"]["last_regeneration"] = {
                "timestamp_utc": meta["generation_timestamp_utc"],
                "generator_head": meta["generator"]["git_head"],
                "wilson_supplement": meta["generator"]["configuration"]["wilson_supplement"],
                "validation_only": caller_owned_staging,
            }
        payload = json.dumps(meta, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        metadata_temp = staging / ".run_metadata.json.tmp"
        document_temp = staging / ".results.md.tmp"
        with metadata_temp.open("x", encoding="utf-8") as handle:
            handle.write(payload)
        with document_temp.open("x", encoding="utf-8") as handle:
            handle.write(document)
        os.link(metadata_temp, staging / "run_metadata.json")
        os.link(document_temp, staging / "results.md")
        metadata_temp.unlink()
        document_temp.unlink()
        if {path.name for path in staging.iterdir()} != OUTPUT_NAMES:
            raise Fatal("Unexpected files in successful staging directory")
        if sha((staging / "results.md").read_bytes()) != meta["document_sha256"] or (staging / "run_metadata.json").read_text() != payload:
            raise Fatal("Staged deliverable read-back mismatch")
        physical_output = staging
        if not caller_owned_staging:
            publish_canonical(staging)
            physical_output = CANONICAL
        print(json.dumps({"status": meta["status"], "unresolved_items": len(sources.unresolved),
                          "output_directory": str(physical_output), "canonical_destination": str(CANONICAL),
                          "validation_only": caller_owned_staging, "validation": meta["validation_results"]},
                         ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        clean_staging(staging)
        print(json.dumps({"status": "failed", "canonical_preserved": CANONICAL.exists(),
                          "diagnostics": [{"type": type(exc).__name__, "message": str(exc)}]}, ensure_ascii=False), file=sys.stderr)
        return 1
