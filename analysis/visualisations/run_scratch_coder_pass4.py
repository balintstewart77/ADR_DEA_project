"""Run pass-4 extraction, rendering, and Stage 2 isolation."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_scratch_coder_pass3 import comparable_sha256, run  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR = ROOT / "analysis/visualisations/extract_scratch_coder_pass4.py"
RENDERER = ROOT / "analysis/visualisations/render_scratch_coder_pass4.py"
# The pass-4 renderer draws carried-forward figures with the pass-3 functions, so the isolated
# copy needs the pass-3 renderer and the shared style modules too.
RENDER_MODULES = ("render_scratch_coder_pass3.py", "figure_style.py", "rating_bars.py")
FORBIDDEN_LITERALS = ("scratch_coder_results", "confidence_exploratory", "results.md", "outputs_disagreement", "outputs_majority",
                      "label_application_cardinality_exploratory", "03_preexisting_model_evidence", "model_comparison_sample")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "analysis/figure_data")
    parser.add_argument("--figure-dir", type=Path, default=ROOT / "analysis/figures")
    parser.add_argument("--table-dir", type=Path, default=ROOT / "analysis/tables")
    parser.add_argument("--pass4-log", type=Path, required=True)
    parser.add_argument("--pass3-log", type=Path, required=True)
    parser.add_argument("--findings-log", type=Path, required=True)
    args = parser.parse_args()
    data_dir, figure_dir, table_dir = args.data_dir.resolve(), args.figure_dir.resolve(), args.table_dir.resolve()

    run([sys.executable, "-B", str(EXTRACTOR), "--data-dir", str(data_dir), "--pass4-log", str(args.pass4_log.resolve()),
         "--pass3-log", str(args.pass3_log.resolve()), "--findings-log", str(args.findings_log.resolve()), "--archive-existing"], ROOT)
    run([sys.executable, "-B", str(RENDERER), "--data-dir", str(data_dir), "--figure-dir", str(figure_dir),
         "--table-dir", str(table_dir), "--archive-existing"], ROOT)

    manifest = json.loads((data_dir / "pass4_deliverable_manifest.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="scratch_coder_pass4_isolation_") as temporary:
        isolated = Path(temporary)
        isolated_data, isolated_figures, isolated_tables = isolated / "figure_data", isolated / "figures", isolated / "tables"
        isolated_data.mkdir()
        copied = {"pass4_deliverable_manifest.json", "pass4_run_metadata.json"}
        for entry in manifest["entries"].values():
            copied.update(entry["inputs"].values())
        for name in sorted(copied):
            shutil.copy2(data_dir / name, isolated_data / name)
        isolated_renderer = isolated / RENDERER.name
        shutil.copy2(RENDERER, isolated_renderer)
        for module in RENDER_MODULES:
            shutil.copy2(RENDERER.parent / module, isolated / module)
        found = sorted({literal for path in [isolated_renderer, *(isolated / m for m in RENDER_MODULES)]
                        for literal in FORBIDDEN_LITERALS if literal in path.read_text(encoding="utf-8")})
        if found:
            raise RuntimeError(f"Stage 2 code contains analytical-source path literals: {found}")
        run([sys.executable, "-B", str(isolated_renderer), "--data-dir", str(isolated_data),
             "--figure-dir", str(isolated_figures), "--table-dir", str(isolated_tables)], isolated)
        expected = [name for entry in manifest["entries"].values() for name in entry["outputs"]]
        missing = [name for name in expected if not ((isolated_figures / name).is_file() or (isolated_tables / name).is_file())]
        matches = {}
        for name in expected:
            if name in missing:
                continue
            production = figure_dir / name if (figure_dir / name).is_file() else table_dir / name
            isolated_output = isolated_figures / name if (isolated_figures / name).is_file() else isolated_tables / name
            matches[name] = comparable_sha256(production) == comparable_sha256(isolated_output)
        isolation = {
            "status": "PASS" if not missing and all(matches.values()) else "FAIL",
            "completed_utc": datetime.now(timezone.utc).isoformat(), "copied_inputs": sorted(copied),
            "copied_code": [RENDERER.name, *RENDER_MODULES], "forbidden_source_path_literals_in_code": found,
            "expected_outputs": len(expected), "missing_outputs": missing, "content_identical_to_production": matches,
            "comparison_rule": "Exact bytes for PNG/CSV/Markdown; SVG after canonicalizing opaque generated id attributes and references by occurrence.",
        }
        if isolation["status"] != "PASS":
            raise RuntimeError(f"Stage 2 isolation failed: {isolation}")

    report_path = figure_dir / "pass4_rendering_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")); report["isolation_test"] = isolation
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for metadata_path in (data_dir / "pass4_run_metadata.json", figure_dir / "pass4_run_metadata.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")); metadata["isolation_test"] = isolation
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
