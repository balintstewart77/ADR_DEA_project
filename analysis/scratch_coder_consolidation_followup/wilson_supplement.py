"""Create the authorised 37-row baseline Wilson interval supplement."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, getcontext
import hashlib
import inspect
import io
import json
from math import sqrt
import os
from pathlib import Path
import subprocess
import sys

from analysis.validation.intervals import Z_975, wilson_interval

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "analysis/outputs_validation_consolidation_followup_20260907T132938546154Z/wilson_scope_manifest.json"
PROTOCOL = ROOT / "preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx"
METHODS_A = ROOT / "analysis/outputs_validation_scratch_20260824/methods_stage_a.md"
IMPLEMENTATION = ROOT / "analysis/validation/intervals.py"
TASK_B = ROOT / "analysis/outputs_validation_consolidated_20260907T131344836676Z"
SELECTED_RANGES = ((53, 61), (75, 77), (90, 101), (118, 122), (135, 138), (146, 149))
SELECTED_IDS = tuple(f"WSA{i:04d}" for start, end in SELECTED_RANGES for i in range(start, end + 1))
REUSED_IDS = ("WSA0074", "WSA0082", "WSA0083")
TOLERANCE = 1e-12


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> dict:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return {"command": ["git", *args], "exit_code": p.returncode,
            "stdout": p.stdout.rstrip("\n"), "stderr": p.stderr.rstrip("\n")}


def independent_wilson(successes: int, n: int) -> tuple[float, float]:
    """Direct standard-form check, independent of the repository function."""
    p = successes / n
    z2 = Z_975 * Z_975
    denominator = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denominator
    half = Z_975 * sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denominator
    return centre - half, centre + half


def high_precision_wilson(successes: int, n: int) -> tuple[float, float]:
    """Decimal formula check to make floating-point agreement explicit."""
    getcontext().prec = 50
    k, total, z = Decimal(successes), Decimal(n), Decimal(str(Z_975))
    p = k / total
    z2 = z * z
    denominator = Decimal(1) + z2 / total
    centre = (p + z2 / (Decimal(2) * total)) / denominator
    half = z * (p * (Decimal(1) - p) / total + z2 / (Decimal(4) * total * total)).sqrt() / denominator
    return float(centre - half), float(centre + half)


def calculation(successes: int, n: int) -> dict:
    result = wilson_interval(successes, n)
    raw_lower, raw_upper = independent_wilson(successes, n)
    decimal_lower, decimal_upper = high_precision_wilson(successes, n)
    corrected_lower = 0.0 if successes == 0 else max(0.0, raw_lower)
    corrected_upper = 1.0 if successes == n else min(1.0, raw_upper)
    if max(abs(result.lower - corrected_lower), abs(result.upper - corrected_upper),
           abs(result.lower - (0.0 if successes == 0 else decimal_lower)),
           abs(result.upper - (1.0 if successes == n else decimal_upper))) > TOLERANCE:
        raise ValueError(f"Wilson implementation/formula mismatch for {successes}/{n}")
    corrections = []
    if result.lower != raw_lower:
        corrections.append({"endpoint": "lower", "raw": repr(raw_lower), "corrected": repr(result.lower),
                            "reason": "Repository implementation fixes the zero-success lower boundary at 0" if successes == 0 else "Clamp to [0,1]"})
    if result.upper != raw_upper:
        corrections.append({"endpoint": "upper", "raw": repr(raw_upper), "corrected": repr(result.upper),
                            "reason": "Repository implementation fixes the all-success upper boundary at 1" if successes == n else "Clamp to [0,1]"})
    return {"lower": result.lower, "upper": result.upper, "raw_lower": raw_lower, "raw_upper": raw_upper,
            "decimal_lower": decimal_lower, "decimal_upper": decimal_upper, "boundary_corrections": corrections}


def load_manifest(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    manifest = json.loads(data)
    rows = manifest.get("rows", [])
    if len(rows) != len({row["candidate_id"] for row in rows}):
        raise ValueError("Scope manifest candidate IDs are not unique")
    return manifest, data


def csv_row(source_path: str, key: dict) -> tuple[dict, str]:
    path = ROOT / source_path
    digest = sha(path.read_bytes())
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    matches = [row for row in rows if all(row.get(k) == v for k, v in key.items())]
    if len(matches) != 1:
        raise ValueError(f"Expected one source row for {source_path} {key}; found {len(matches)}")
    return matches[0], digest


def validate_selected(scope: dict) -> tuple[list[dict], dict[str, dict]]:
    by_id = {row["candidate_id"]: row for row in scope["rows"]}
    if set(SELECTED_IDS) - set(by_id):
        raise ValueError("An authorised candidate ID is absent from the scope manifest")
    selected = []
    hashes: dict[str, dict] = {}
    for candidate_id in SELECTED_IDS:
        item = by_id[candidate_id]
        if item["scope_decision"] != "candidate_for_later_authorised_wilson":
            raise ValueError(f"Selected item is not a scope candidate: {candidate_id}")
        if item["population"] != "baseline" or item["observational_unit_class"] not in ("record_binary", "individual_coder_binary"):
            raise ValueError(f"Selected item has an unapproved population/unit: {candidate_id}")
        row, digest = csv_row(item["source_path"], item["row_key"])
        if digest != item["source_sha256"]:
            raise ValueError(f"Source hash differs from scope manifest: {candidate_id}")
        hashes.setdefault(item["source_path"], {"sha256_before": digest, "bytes": (ROOT / item["source_path"]).stat().st_size})
        for manifest_field, column in (("source_numerator", "count"), ("source_denominator", "denominator"), ("source_proportion", "proportion")):
            if item[manifest_field] != row[column]:
                raise ValueError(f"Source cell differs from scope manifest: {candidate_id}/{column}")
        if item["metric_name"] != "proportion" or item["source_denominator"] != "150":
            raise ValueError(f"Selected metric/denominator is outside approved scope: {candidate_id}")
        try:
            k, n = int(item["source_numerator"]), int(item["source_denominator"])
        except ValueError as exc:
            raise ValueError(f"Non-integer count: {candidate_id}") from exc
        if not (0 <= k <= n and n > 0):
            raise ValueError(f"Invalid source count: {candidate_id}")
        selected.append(item)
    if len(selected) != 37 or len({(x["source_path"], json.dumps(x["row_key"], sort_keys=True), x["metric_name"]) for x in selected}) != 37:
        raise ValueError("Selected target identity is not exactly 37 unique source/key/metric combinations")
    return selected, hashes


def reused_payload(scope: dict, source_hashes: dict) -> dict:
    by_id = {row["candidate_id"]: row for row in scope["rows"]}
    entries = {}
    for candidate_id in REUSED_IDS:
        item = by_id[candidate_id]
        row, digest = csv_row(item["source_path"], item["row_key"])
        if digest != item["source_sha256"]:
            raise ValueError(f"Reuse target hash mismatch: {candidate_id}")
        source_hashes.setdefault(item["source_path"], {"sha256_before": digest, "bytes": (ROOT / item["source_path"]).stat().st_size})
        for field, column in (("source_numerator", "count"), ("source_denominator", "denominator"), ("source_proportion", "proportion")):
            if item[field] != row[column]:
                raise ValueError(f"Reuse target cell mismatch: {candidate_id}/{column}")
        entries[candidate_id] = item
    strict = entries["WSA0083"]
    sufficient = entries["WSA0074"]
    if any(strict[field] != sufficient[field] for field in ("source_numerator", "source_denominator", "source_proportion")):
        raise ValueError("WSA0074/WSA0083 equivalence cells differ")
    eq = sufficient["equivalent_existing_interval"]
    if eq is None or eq["source_path"] != strict["source_path"] or eq["row_key"] != strict["row_key"]:
        raise ValueError("WSA0074 equivalence target does not resolve to WSA0083")
    if strict["existing_interval"]["status"] != "reported" or entries["WSA0082"]["existing_interval"]["status"] != "reported":
        raise ValueError("Expected source interval is not reported")
    if (eq["lower"], eq["upper"], eq["method"]) != (strict["existing_interval"]["lower"], strict["existing_interval"]["upper"], strict["existing_interval"]["method"]):
        raise ValueError("Equivalent interval values differ")
    origins = {}
    for candidate_id in ("WSA0082", "WSA0083"):
        item = entries[candidate_id]
        origins[candidate_id] = {"candidate_id": candidate_id, "source_path": item["source_path"], "source_hash": item["source_sha256"],
            "source_key": item["row_key"], "metric": item["metric_name"], "numerator": item["source_numerator"],
            "denominator": item["source_denominator"], "proportion": item["source_proportion"],
            "method": item["existing_interval"]["method"], "confidence_level": "95%",
            "lower": item["existing_interval"]["lower"], "upper": item["existing_interval"]["upper"],
            "cell_lineage": item["numerator_lineage"], "denominator_lineage": item["denominator_lineage"],
            "proportion_lineage": item["proportion_lineage"], "interval_lineage": item["existing_interval"]["lineage"]}
    return {"originating_interval_count": 2, "report_entry_count": 3, "originating_intervals": origins,
        "report_entries": [
            {"candidate_id": "WSA0082", "origin": "WSA0082", "use": "retain_existing_source_interval", "target": origins["WSA0082"]},
            {"candidate_id": "WSA0083", "origin": "WSA0083", "use": "retain_existing_source_interval", "target": origins["WSA0083"]},
            {"candidate_id": "WSA0074", "origin": "WSA0083", "use": "reuse_verified_equivalent_result",
             "target": {"source_path": sufficient["source_path"], "source_hash": sufficient["source_sha256"],
                        "source_key": sufficient["row_key"], "metric": sufficient["metric_name"],
                        "numerator": sufficient["source_numerator"], "denominator": sufficient["source_denominator"],
                        "proportion": sufficient["source_proportion"]},
             "equivalence_evidence": eq["identity_evidence"], "join_cardinality": "one_to_one",
             "exact_cells_equal": ["count", "denominator", "proportion"],
             "lower": origins["WSA0083"]["lower"], "upper": origins["WSA0083"]["upper"],
             "method": origins["WSA0083"]["method"], "confidence_level": "95%",
             "interval_lineage": origins["WSA0083"]["interval_lineage"]}]}


def create_rows(selected: list[dict], calculation_time: str, implementation_hash: str) -> tuple[list[dict], list[dict]]:
    rows, corrections = [], []
    for item in selected:
        k, n = int(item["source_numerator"]), int(item["source_denominator"])
        result = calculation(k, n)
        source_point = float(item["source_proportion"])
        calculated_point = k / n
        difference = abs(calculated_point - source_point)
        if difference > TOLERANCE:
            raise ValueError(f"Exported proportion differs from k/n beyond tolerance: {item['candidate_id']}")
        if not (-TOLERANCE <= result["lower"] <= source_point <= result["upper"] <= 1.0 + TOLERANCE):
            raise ValueError(f"Point/bounds validation failure: {item['candidate_id']}")
        for correction in result["boundary_corrections"]:
            corrections.append({"candidate_id": item["candidate_id"], **correction})
        rows.append({"candidate_id": item["candidate_id"], "source_path": item["source_path"],
            "source_sha256": item["source_sha256"], "source_key_json": json.dumps(item["row_key"], ensure_ascii=False, sort_keys=True),
            "metric": item["metric_name"], "population": item["population"], "observational_unit": item["observational_unit_class"],
            "numerator_column": item["numerator_lineage"]["column"], "original_numerator": item["source_numerator"],
            "denominator_column": item["denominator_lineage"]["column"], "original_denominator": item["source_denominator"],
            "original_proportion": item["source_proportion"], "validation_k_over_n": repr(calculated_point),
            "point_validation_absolute_difference": repr(difference), "raw_formula_lower": repr(result["raw_lower"]),
            "raw_formula_upper": repr(result["raw_upper"]), "ci_lower": repr(result["lower"]), "ci_upper": repr(result["upper"]),
            "boundary_correction": json.dumps(result["boundary_corrections"], ensure_ascii=False),
            "method": "Wilson score", "confidence_level": "0.95", "alpha": "0.05", "two_sided": "True",
            "continuity_correction": "False", "calculation_timestamp_utc": calculation_time,
            "implementation_path": IMPLEMENTATION.relative_to(ROOT).as_posix(), "implementation_sha256": implementation_hash})
    return rows, corrections


def write_csv_text(rows: list[dict]) -> str:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return handle.getvalue()


def methods_text(timestamp: str, implementation_hash: str, checks: list[dict], corrections: list[dict], manifest_path: Path, manifest_hash: str) -> str:
    return f"""# Supplementary baseline Wilson intervals

This dated post-registration supplement was calculated at `{timestamp}` under the explicit selected scope in the user instruction. It adds 37 newly calculated marginal two-sided 95% Wilson score intervals without continuity correction. It is not simultaneous coverage across categories and does not support inference to a population of coders.

The selection uses `{manifest_path.relative_to(ROOT)}` (SHA-256 `{manifest_hash}`) without regenerating its classifications. Included IDs are `{', '.join(SELECTED_IDS)}`: nine named-coder sufficiency, three record-majority sufficiency, twelve named-coder taxonomy fit, five record-majority taxonomy fit, and four record-level Unclear-use rows in each set-valued dimension. Each source denominator is 150.

The explicit scope interpretation covers these research-reporting outcomes. The eight QA candidates remain descriptive, pooled within-project responses receive no ordinary Wilson interval, structural ratios and all nonbaseline rows remain excluded. This does not claim that every baseline proportion has an interval or that a QA interval would necessarily be mathematically invalid.

Protocol evidence is §8.9 of `{PROTOCOL.relative_to(ROOT)}` (SHA-256 `{sha(PROTOCOL.read_bytes())}`), which states that baseline proportions use 95% Wilson score intervals. The original saved Stage A methods are `{METHODS_A.relative_to(ROOT)}` (SHA-256 `{sha(METHODS_A.read_bytes())}`). The original assessment remains unchanged.

The implementation is `analysis.validation.intervals.wilson_interval` in `{IMPLEMENTATION.relative_to(ROOT)}`, SHA-256 `{implementation_hash}`, signature `{inspect.signature(wilson_interval)}`. It uses `Z_975={Z_975!r}`, the standard two-sided 95% Wilson formula, no continuity correction and no finite-population adjustment. Python `{sys.version.split()[0]}` was used.

The previous assessment's proposed centre check is corrected here: the Wilson interval midpoint generally differs from `k/n`. Validation instead requires `lower <= k/n <= upper`, bounds within `[0,1]`, exact integer `0 <= k <= n` with `n > 0`, and agreement within absolute tolerance `{TOLERANCE}` against direct double-precision and independent high-precision Decimal evaluations. The exported proportion remains the point estimate; calculated `k/n` is validation only.

Focused checks covered {', '.join(f"{x['case']} (k={x['k']}, n={x['n']})" for x in checks)}. All passed. Boundary corrections recorded: {len(corrections)}. Any correction is recorded per row with raw and corrected endpoints and its reason.

`WSA0082` and `WSA0083` retain their two original Stage A Wilson intervals. `WSA0074` reuses the `WSA0083` strict-sufficiency interval after a one-to-one lookup and exact equality of exported count, denominator and proportion; it is not recomputed.

These are newly calculated supplementary intervals, not intervals present in the original Stage A analysis. Creating this artifact does not resolve the undocumented historical omission reason in U0069, close any original unresolved entry, amend the protocol or historical deviation log, or itself establish that governance requirements have been satisfied.
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope-manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    manifest_path = args.scope_manifest.resolve()
    if not manifest_path.is_relative_to(ROOT) or "preregistration_restricted" in manifest_path.parts:
        raise SystemExit("Scope manifest must be an unrestricted repository file")
    before_status = git("status", "--porcelain=v1", "--untracked-files=all")
    head = git("rev-parse", "HEAD")
    code_check = git("diff", "--exit-code", "HEAD", "--", "analysis/scratch_coder_consolidation_followup", "analysis/scratch_coder_consolidated", "analysis/validation/intervals.py")
    if head["exit_code"] or code_check["exit_code"]:
        raise SystemExit("Relevant calculation/adapter code does not match HEAD")
    scope, manifest_bytes = load_manifest(manifest_path)
    selected, source_hashes = validate_selected(scope)
    reused = reused_payload(scope, source_hashes)
    implementation_hash = sha(IMPLEMENTATION.read_bytes())
    calculation_time = datetime.now(timezone.utc).isoformat()
    checks=[]
    for label,k,n in (("zero-success",0,150),("all-success",150,150),("interior",75,150),("interior-source-scale",92,150)):
        result=calculation(k,n); checks.append({"case":label,"k":k,"n":n,"lower":repr(result["lower"]),"upper":repr(result["upper"]),"status":"passed"})
    rows, corrections = create_rows(selected, calculation_time, implementation_hash)
    if len(rows) != 37:
        raise ValueError("Supplement must contain exactly 37 rows")
    # Recheck every immutable input after calculation and before publication.
    for path, record in source_hashes.items():
        after = sha((ROOT / path).read_bytes()); record["sha256_after"] = after; record["unchanged"] = after == record["sha256_before"]
    input_records = {
        manifest_path.relative_to(ROOT).as_posix(): {"sha256_before": sha(manifest_bytes), "sha256_after": sha(manifest_path.read_bytes())},
        IMPLEMENTATION.relative_to(ROOT).as_posix(): {"sha256_before": implementation_hash, "sha256_after": sha(IMPLEMENTATION.read_bytes())},
        PROTOCOL.relative_to(ROOT).as_posix(): {"sha256_before": sha(PROTOCOL.read_bytes()), "sha256_after": sha(PROTOCOL.read_bytes())},
        METHODS_A.relative_to(ROOT).as_posix(): {"sha256_before": sha(METHODS_A.read_bytes()), "sha256_after": sha(METHODS_A.read_bytes())},
        f"{TASK_B.relative_to(ROOT)}/run_metadata.json": {"sha256_before": sha((TASK_B/"run_metadata.json").read_bytes()), "sha256_after": sha((TASK_B/"run_metadata.json").read_bytes())},
    }
    if not all(x["unchanged"] for x in source_hashes.values()) or not all(x["sha256_before"] == x["sha256_after"] for x in input_records.values()):
        raise ValueError("An immutable input changed during supplement generation")
    output = ROOT / "analysis" / ("outputs_validation_wilson_baseline_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output.mkdir(exist_ok=False)
    csv_text = write_csv_text(rows)
    methods = methods_text(calculation_time, implementation_hash, checks, corrections, manifest_path, sha(manifest_bytes))
    reused_text = json.dumps(reused, indent=2, ensure_ascii=False) + "\n"
    (output/"wilson_intervals.csv").write_text(csv_text)
    (output/"reused_intervals.json").write_text(reused_text)
    (output/"methods_wilson_baseline.md").write_text(methods)
    (output/"run_metadata.json").write_text("{}\n")
    after_status = git("status", "--porcelain=v1", "--untracked-files=all")
    metadata = {"status":"complete","artifact_type":"new_dated_post_registration_supplement",
        "calculation_timestamp_utc":calculation_time,"output_directory":output.relative_to(ROOT).as_posix(),
        "invocation":[sys.executable,"-B","-m","analysis.scratch_coder_consolidation_followup.wilson_supplement","--scope-manifest",manifest_path.relative_to(ROOT).as_posix()],
        "git_head":head["stdout"],"relevant_code_matches_head":True,
        "repository_status_before":before_status["stdout"],"repository_status_after_artifacts_created":after_status["stdout"],
        "implementation":{"callable":"analysis.validation.intervals.wilson_interval","path":IMPLEMENTATION.relative_to(ROOT).as_posix(),
            "sha256":implementation_hash,"git_blob":git("hash-object",IMPLEMENTATION.relative_to(ROOT).as_posix())["stdout"],
            "signature":str(inspect.signature(wilson_interval)),"z":repr(Z_975),"python_version":sys.version,
            "statsmodels":"not installed; repository implementation used"},
        "method":{"name":"Wilson score","confidence_level":0.95,"alpha":0.05,"two_sided":True,"continuity_correction":False,
                  "finite_population_adjustment":False,"validation_absolute_tolerance":TOLERANCE,"coverage":"marginal, not simultaneous"},
        "selection_list":list(SELECTED_IDS),"selection_count":len(rows),"reused_report_entries":list(REUSED_IDS),
        "scope_decision":{"included":"Specified research-reporting outcomes only","excluded":{"qa_candidates":8,"pooled_response_rows":37,"structural_ratios":2,"nonbaseline_rows":106},
                          "interpretation":"QA frequencies remain descriptive; ordinary Wilson intervals are not applied to pooled within-project ratings."},
        "source_files":source_hashes,"inputs":input_records,"focused_numerical_checks":checks,"boundary_corrections":corrections,
        "validation":{"manifest_identities_checked":True,"source_hashes_match_manifest":True,"complete_source_key_joins":"one_to_one",
            "selected_population":"baseline","selected_units":["individual_coder_binary","record_binary"],"all_denominators":"150",
            "integer_and_range_checks":"passed","source_count_and_proportion_strings_match_manifest":True,
            "point_within_bounds":"passed","bounds_within_unit_interval":"passed","formula_cross_check":"passed",
            "new_interval_rows":37,"originating_existing_intervals":2,"report_interval_entries_from_existing_bounds":3,
            "archived_inputs_unchanged":True,"bootstrap_files_read":0,"other_statistics_calculated":0},
        "files": {"wilson_intervals.csv":{"bytes":len(csv_text.encode()),"sha256":sha(csv_text.encode())},
                  "reused_intervals.json":{"bytes":len(reused_text.encode()),"sha256":sha(reused_text.encode())},
                  "methods_wilson_baseline.md":{"bytes":len(methods.encode()),"sha256":sha(methods.encode())}}}
    metadata_text=json.dumps(metadata,indent=2,ensure_ascii=False)+"\n"
    temporary=output/".run_metadata.tmp";temporary.write_text(metadata_text);os.replace(temporary,output/"run_metadata.json")
    # Read back and validate final files.
    final_rows=list(csv.DictReader((output/"wilson_intervals.csv").open()));json.loads((output/"reused_intervals.json").read_text());json.loads((output/"run_metadata.json").read_text())
    if len(final_rows)!=37 or {r["candidate_id"] for r in final_rows}!=set(SELECTED_IDS) or (output/"methods_wilson_baseline.md").read_text()!=methods:
        raise ValueError("Published supplement read-back failed")
    print(json.dumps({"output_directory":str(output),"new_interval_rows":37,"existing_interval_origins":2,"equivalent_reuse":1,"git_head":head["stdout"]},indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
