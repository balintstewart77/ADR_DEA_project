"""Create one exclusively named run; publish final filenames only after validation."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

from .preflight import Fatal, PACKAGE, ROOT, Sources, git, sha
from .report import DIAGNOSTIC, Report, esc


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def fresh_directory():
    while True:
        path = ROOT / "analysis" / ("outputs_validation_consolidated_" + timestamp())
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            continue


def outside_task_status(status, out):
    if status is None:
        return None
    allowed = (PACKAGE.relative_to(ROOT).as_posix() + "/", out.relative_to(ROOT).as_posix() + "/")
    return [line for line in status.splitlines() if not any(line[3:].startswith(p) for p in allowed)]


def main():
    # -B is the documented invocation; refuse a cache-producing invocation.
    if not sys.dont_write_bytecode:
        print("Use Python -B (or PYTHONDONTWRITEBYTECODE=1) to prevent caches.", file=sys.stderr)
        return 2
    out = fresh_directory()
    before = git("status", "--porcelain=v1", "--untracked-files=all")
    meta = dict(generator={"identity": "scratch_coder_consolidated v2", "invocation": [sys.executable, "-B", "-m", "analysis.scratch_coder_consolidated"],
                           "git_head": git("rev-parse", "HEAD"), "git_status_before": before,
                           "source_hashes": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(PACKAGE.iterdir()) if p.suffix in (".py", ".json", ".md")}},
                generation_timestamp_utc=datetime.now(timezone.utc).isoformat(), output_directory=out.relative_to(ROOT).as_posix(),
                write_scope="Only this exclusively created output directory; generator source code does not write elsewhere.",
                boundaries={"source_directories_read_only": True, "restricted_tree_accessed": False, "analysis_pipelines_executed": False, "owner_inputs_accessed": False, "git_mutations": False})
    sources = Sources(meta)
    published_document = False
    published_metadata = False
    try:
        sources.load()
        report = Report(sources)
        report.build()
        document = report.render()
        # Validate the actual rendered table fragments, not only internal flags.
        for t in report.tables:
            rendered = report.render_table(t)
            if rendered not in document:
                raise Fatal(f"Rendered table missing from document: {t['id']}")
            rows = [line for line in rendered.splitlines() if line.startswith("| ")][2:]
            if len(rows) != len(t["items"]):
                raise Fatal(f"Rendered table row count mismatch: {t['id']}")
            for line, item in zip(rows, t["items"], strict=True):
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
                if cells[2:5] != [esc(item[k] or "") for k in ("displayed_estimate", "displayed_lower", "displayed_upper")]:
                    raise Fatal(f"Rendered estimate/bounds differ from validated source copy: {item['result_id']}")
            if t["population"] in ("hard_case", "overall") and DIAGNOSTIC not in rendered.splitlines()[0]:
                raise Fatal(f"Hard-case diagnostic header absent: {t['id']}")
        for sec in range(12):
            if document.count(f"## Section {sec} —") != 1:
                raise Fatal(f"Section coverage/order failure: {sec}")
        if document.index("## Section 11 —") > document.index("## Appendix A"):
            raise Fatal("Appendix ordering failure")
        sources.unchanged()
        after = git("status", "--porcelain=v1", "--untracked-files=all")
        if outside_task_status(before, out) != outside_task_status(after, out):
            raise Fatal("Working-tree state outside task locations changed during run")
        meta["generator"]["git_status_after_validation"] = after
        meta["validation_results"].update(source_hashes_before_after="passed", outside_task_working_tree="unchanged", hard_case_table_headers="passed", rendered_table_presence="passed", rendered_estimates_and_bounds="passed", final_section_structure="passed")
        meta["document_sha256"] = sha(document.encode("utf-8"))
        # Serialize both in memory before creating either final filename.
        payload = json.dumps(meta, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        metadata_temp = out / ".run_metadata.json.tmp"
        document_temp = out / ".consolidated_results.md.tmp"
        with metadata_temp.open("x", encoding="utf-8") as handle:
            handle.write(payload)
        with document_temp.open("x", encoding="utf-8") as handle:
            handle.write(document)
        # Hard-link publication is atomic and fails if a destination exists.
        os.link(metadata_temp, out / "run_metadata.json")
        published_metadata = True
        os.link(document_temp, out / "consolidated_results.md")
        published_document = True
        metadata_temp.unlink()
        document_temp.unlink()
        if {p.name for p in out.iterdir()} != {"run_metadata.json", "consolidated_results.md"}:
            raise Fatal("Unexpected files in successful output directory")
        if sha((out / "consolidated_results.md").read_bytes()) != meta["document_sha256"] or (out / "run_metadata.json").read_text() != payload:
            raise Fatal("Deliverable read-back mismatch")
        print(json.dumps({"status": meta["status"], "unresolved_items": len(sources.unresolved), "output_directory": str(out),
                          "validation": meta["validation_results"]}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        if published_document:
            (out / "consolidated_results.md").unlink()
        meta["status"] = "failed"
        meta["fatal_diagnostics"] = [{"type": type(exc).__name__, "message": str(exc)}]
        try:
            sources.unchanged()
        except Exception as hash_error:
            meta["fatal_diagnostics"].append({"type": type(hash_error).__name__, "message": str(hash_error)})
        for name in (".run_metadata.json.tmp", ".consolidated_results.md.tmp"):
            temporary = out / name
            if temporary.exists():
                temporary.unlink()
        if published_metadata:
            failed_temp = out / ".failed_metadata.tmp"
            with failed_temp.open("x", encoding="utf-8") as handle:
                json.dump(meta, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(failed_temp, out / "run_metadata.json")
        elif not (out / "run_metadata.json").exists():
            with (out / "run_metadata.json").open("x", encoding="utf-8") as handle:
                json.dump(meta, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        print(json.dumps({"status": "failed", "output_directory": str(out), "diagnostics": meta["fatal_diagnostics"]}, ensure_ascii=False), file=sys.stderr)
        return 1
