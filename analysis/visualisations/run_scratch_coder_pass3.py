"""Run committed pass-3 extraction, rendering, and Stage 2 isolation."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = ROOT / "analysis/visualisations/extract_scratch_coder_pass3.py"
RENDERER = ROOT / "analysis/visualisations/render_scratch_coder_pass3.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "analysis/figure_data")
    parser.add_argument("--figure-dir", type=Path, default=ROOT / "analysis/figures")
    parser.add_argument("--table-dir", type=Path, default=ROOT / "analysis/tables")
    parser.add_argument("--pass3-log", type=Path, required=True)
    parser.add_argument("--pass2-log", type=Path, required=True)
    parser.add_argument("--findings-log", type=Path, required=True)
    args = parser.parse_args()
    data_dir, figure_dir, table_dir = args.data_dir.resolve(), args.figure_dir.resolve(), args.table_dir.resolve()

    run([sys.executable, "-B", str(EXTRACTOR), "--data-dir", str(data_dir),
         "--pass3-log", str(args.pass3_log.resolve()), "--pass2-log", str(args.pass2_log.resolve()),
         "--findings-log", str(args.findings_log.resolve()), "--archive-existing"], ROOT)
    run([sys.executable, "-B", str(RENDERER), "--data-dir", str(data_dir),
         "--figure-dir", str(figure_dir), "--table-dir", str(table_dir), "--archive-existing"], ROOT)

    manifest = json.loads((data_dir / "pass3_deliverable_manifest.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="scratch_coder_pass3_isolation_") as temporary:
        isolated = Path(temporary)
        isolated_data = isolated / "figure_data"; isolated_figures = isolated / "figures"; isolated_tables = isolated / "tables"
        isolated_data.mkdir()
        copied = {"pass3_deliverable_manifest.json", "pass3_run_metadata.json"}
        for entry in manifest["entries"].values():
            copied.update(entry["inputs"].values())
        for name in sorted(copied):
            shutil.copy2(data_dir / name, isolated_data / name)
        isolated_renderer = isolated / RENDERER.name
        shutil.copy2(RENDERER, isolated_renderer)
        renderer_text = isolated_renderer.read_text(encoding="utf-8")
        forbidden_literals = ["scratch_coder_results", "confidence_exploratory", "results.md", "outputs_disagreement", "outputs_majority"]
        found_literals = [value for value in forbidden_literals if value in renderer_text]
        if found_literals:
            raise RuntimeError(f"Stage 2 code contains analytical-source path literals: {found_literals}")
        run([sys.executable, "-B", str(isolated_renderer), "--data-dir", str(isolated_data),
             "--figure-dir", str(isolated_figures), "--table-dir", str(isolated_tables)], isolated)
        expected = [Path(path).name for entry in manifest["entries"].values() for path in entry["outputs"]]
        missing = [name for name in expected if not ((isolated_figures / name).is_file() or (isolated_tables / name).is_file())]
        if missing:
            raise RuntimeError(f"Stage 2 isolation output missing: {missing}")
        matches = {}
        for name in expected:
            production = figure_dir / name if (figure_dir / name).is_file() else table_dir / name
            isolated_output = isolated_figures / name if (isolated_figures / name).is_file() else isolated_tables / name
            matches[name] = sha256(production) == sha256(isolated_output)
        isolation = {
            "status": "PASS" if not missing and all(matches.values()) else "FAIL",
            "completed_utc": datetime.now(timezone.utc).isoformat(), "renderer_copy": str(isolated_renderer),
            "working_directory": str(isolated), "analytical_inputs_present": [], "copied_inputs": sorted(copied),
            "forbidden_source_path_literals_in_renderer": found_literals, "expected_outputs": len(expected),
            "outputs_created": len(expected) - len(missing), "missing_outputs": missing,
            "byte_identical_to_production": matches, "all_byte_identical": all(matches.values()),
        }
        if isolation["status"] != "PASS":
            raise RuntimeError(f"Stage 2 isolation failed: {isolation}")

    report_path = figure_dir / "pass3_rendering_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")); report["isolation_test"] = isolation
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for metadata_path in (data_dir / "pass3_run_metadata.json", figure_dir / "pass3_run_metadata.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")); metadata["isolation_test"] = isolation
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
