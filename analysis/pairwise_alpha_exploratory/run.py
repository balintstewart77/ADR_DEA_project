"""Exploratory pairwise alpha run (addendum a049c79); requires committed code.

Run from the repository root: python -m analysis.pairwise_alpha_exploratory.run
Order: preflight -> source/data checks -> check W -> Analyses 1-4 and joint
bootstraps -> output checks -> outputs. Nothing is written unless every check
passes; any failure raises.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from math import ceil, isfinite
from pathlib import Path

from analysis.scratch_coder_stage_a.config import CODERS, DIMENSIONS, MANIFEST, ROOT
from analysis.scratch_coder_stage_a.load import resolve_manifest_row, sha256_file
from analysis.scratch_coder_stage_a.panels import (
    _taxonomy_labels, build_stage_a_data, dimension_panels, distance_for_dimension, population_ids,
)
from analysis.validation.bootstrap import StatisticValue

from . import compute
from .compute import (
    DIFFERENCES, HUMAN_PAIRS, MODEL_PAIRS, PAIR_NAMES, REPLACEMENT_TERMS, STATISTIC_NAMES,
    canonical_distance, memoised, panel_alpha,
)

HERE = Path(__file__).resolve().parent
ADDENDUM_COMMIT = "a049c79ff0cab8706f6dcd8febfa560b4c60f6ae"
ADDENDUM_CREATED = "2026-09-17"
DATE_STATEMENT = "specified, and instruction issued, on or before 17 September 2026 (investigator-attested)"
SEED = 20260917
ATTEMPTS = 2000
MIN_VALID_FRACTION = 0.90
THRESHOLD = ceil(MIN_VALID_FRACTION * ATTEMPTS)
CONFIDENCE = 0.95
POPULATIONS = (("baseline", 150), ("hard_case", 75))
DIAGNOSTIC = "DIAGNOSTIC — non-representative"
METRIC_NAME = {"Research Domains": "MASI", "Analytical Purposes": "MASI",
               "Demographic disparities / equity": "nominal", "COVID-19 & Pandemic": "nominal"}
STAGE_A = ROOT / "analysis/outputs_validation_scratch_20260824"
STAGE_B = ROOT / "analysis/outputs_validation_scratch_stage_b_20260825"
DATA_AUTHORITIES = ("POST-028", "POST-009", "POST-011", "POST-019", "MOD-006", "MOD-001", "RED-036", "RED-017", "RED-013")
SHARED_CODE = ("analysis/validation/alpha.py", "analysis/validation/metrics.py", "analysis/validation/bootstrap.py",
               "analysis/validation/replacement.py", "analysis/scratch_coder_stage_a/panels.py",
               "analysis/scratch_coder_stage_a/load.py", "analysis/scratch_coder_stage_a/config.py",
               "analysis/scratch_coder_stage_a/mappings.py")
OUTPUT_NAMES = ("results_pairwise_alpha.md", "run_metadata.json")

ANALYSIS_TITLES = {
    1: "Analysis 1 — Pairwise α among humans",
    2: "Analysis 2 — Pairwise α between Fable 5 and each human",
    3: "Analysis 3 — Differences between human pairs",
    4: "Analysis 4 — Replacement comparison per coder",
}
DEFINITIONS = {
    "alpha_AB": "α(A,B)", "alpha_AC": "α(A,C)", "alpha_BC": "α(B,C)",
    "alpha_LA": "α(L,A)", "alpha_LB": "α(L,B)", "alpha_LC": "α(L,C)",
    "diff_AC_minus_AB": "α(A,C) − α(A,B)", "diff_AC_minus_BC": "α(A,C) − α(B,C)", "diff_AB_minus_BC": "α(A,B) − α(B,C)",
    "H_A": "H_A = mean(α(A,B), α(A,C))", "M_A": "M_A = mean(α(L,B), α(L,C))", "D_A": "D_A = M_A − H_A",
    "H_B": "H_B = mean(α(A,B), α(B,C))", "M_B": "M_B = mean(α(L,A), α(L,C))", "D_B": "D_B = M_B − H_B",
    "H_C": "H_C = mean(α(A,C), α(B,C))", "M_C": "M_C = mean(α(L,A), α(L,B))", "D_C": "D_C = M_C − H_C",
}
ANALYSIS_QUANTITIES = {
    1: tuple(f"alpha_{x}{y}" for x, y in HUMAN_PAIRS),
    2: tuple(f"alpha_{x}{y}" for x, y in MODEL_PAIRS),
    3: tuple(name for name, _, _ in DIFFERENCES),
    4: compute.REPLACEMENT_NAMES,
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def require(ledger: list, name: str, actual, expected, source: str) -> None:
    if actual != expected:
        raise RuntimeError(f"CHECK FAILED {name}: actual={actual!r} expected={expected!r} source={source}")
    ledger.append(dict(check=name, status="passed", actual=actual, expected=expected, source=source))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def crlf_row_terminator_sha256(raw: bytes) -> tuple[str, int]:
    """SHA-256 after turning newlines outside double-quoted CSV fields into CRLF."""

    out, quoted = bytearray(), False
    for byte in raw:
        if byte == 0x22:
            quoted = not quoted
        if byte == 0x0A and not quoted:
            out += b"\r\n"
        else:
            out.append(byte)
    return hashlib.sha256(bytes(out)).hexdigest(), len(out)


# ---------------------------------------------------------------- checks (step 4)

def preflight() -> dict:
    status = git("status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError("Working tree not clean; commit code before executing:\n" + status)
    existing = [p.name for p in HERE.glob("PWA1T*.csv")] + [n for n in OUTPUT_NAMES if (HERE / n).exists()]
    if existing:
        raise FileExistsError(f"Outputs from an earlier execution exist; discard them first: {existing}")
    return dict(head=git("rev-parse", "HEAD"), addendum_is_ancestor=subprocess.run(
        ["git", "merge-base", "--is-ancestor", ADDENDUM_COMMIT, "HEAD"], cwd=ROOT).returncode == 0)


def source_checks(ledger: list) -> list[dict]:
    sources = []
    for identifier in DATA_AUTHORITIES:
        row = resolve_manifest_row(identifier)
        path = ROOT / row["current_path"]
        raw = path.read_bytes()
        raw_sha = hashlib.sha256(raw).hexdigest()
        method = "raw_bytes"
        observed = raw_sha
        if raw_sha != row["sha256"] and path.suffix == ".csv":
            observed, size = crlf_row_terminator_sha256(raw)
            method = "csv_row_terminator_crlf_reconstruction"
        require(ledger, f"hash {identifier}", observed, row["sha256"], MANIFEST.relative_to(ROOT).as_posix() + f" ({method})")
        sources.append(dict(manifest_id=identifier, path=row["current_path"], manifest_sha256=row["sha256"],
                            on_disk_raw_sha256=raw_sha, on_disk_bytes=len(raw), match_method=method,
                            git_blob_commit=git("log", "-1", "--format=%H", "--", row["current_path"]) or None))
    return sources


def build_records(data) -> dict[tuple[str, str], dict]:
    out = {}
    for population, _ in POPULATIONS:
        ids = population_ids(data, population, {})
        for dimension in DIMENSIONS:
            panels = dimension_panels(data, ids, dimension)
            out[(population, dimension)] = dict(
                ids=tuple(p.record_id for p in panels),
                records=tuple((p.coder_a, p.coder_b, p.coder_c, p.model) for p in panels),
            )
    return out


def data_checks(ledger: list, data, built: dict) -> dict:
    responses = data.responses
    require(ledger, "coder pseudonyms", tuple(sorted(responses["coder"].unique())), CODERS, "shared loader")
    require(ledger, "duplicate coder-record responses", int(responses.duplicated(["record_id", "coder"]).sum()), 0, "shared loader")
    stage_a_panels = read_csv(STAGE_A / "replacement_panel_results.csv")
    labels = _taxonomy_labels()
    majority = {(r["population"], r["tag"]): int(r["human_majority_positive_n"]) for r in read_csv(STAGE_B / "tag_diagnostics.csv")}
    context = {}
    for population, n in POPULATIONS:
        authority = frozenset(r["record_id"] for r in read_csv(ROOT / resolve_manifest_row(
            "POST-009" if population == "baseline" else "POST-011")["current_path"]))
        require(ledger, f"{population} authority size", len(authority), n, "POST-009/POST-011")
        require(ledger, f"{population} shared membership equals authority", population_ids(data, population, {}) == authority, True, "POST-009/POST-011")
        per_record = responses[responses["record_id"].isin(authority)].groupby("record_id")["coder"].apply(lambda s: tuple(sorted(s)))
        require(ledger, f"{population} one response per coder per record", bool((per_record == CODERS).all()) and len(per_record) == n, True, "shared loader")
        for dimension in DIMENSIONS:
            item = built[(population, dimension)]
            key = f"{population} / {dimension}"
            require(ledger, f"{key} record-ID set equals canonical set", frozenset(item["ids"]) == authority, True, "canonical population set")
            require(ledger, f"{key} record-ID uniqueness", len(set(item["ids"])), len(item["ids"]), "panels")
            canonical_n = {int(r["n_records"]) for r in stage_a_panels if r["population"] == population and r["dimension"] == dimension}
            require(ledger, f"{key} n equals canonical export", sorted(canonical_n), [len(item["ids"])], "replacement_panel_results.csv")
            missing = sum(value is None for record in item["records"] for value in record)
            require(ledger, f"{key} one label set per rater per record (no missing)", missing, 0, "panels")
            if dimension in ("Research Domains", "Analytical Purposes"):
                allowed = labels["domains" if dimension == "Research Domains" else "purposes"]
                bad = sum(not isinstance(v, frozenset) or not v <= allowed for r in item["records"] for v in r)
                empty = sum(isinstance(v, frozenset) and not v for r in item["records"] for v in r)
            else:
                bad = sum(type(v) is not int or v not in (0, 1) for r in item["records"] for v in r)
                empty = None
            require(ledger, f"{key} permitted labels only", bad, 0, "MOD-001 taxonomy / RED-036 choices")
            context[(population, dimension)] = dict(
                n_records=len(item["ids"]),
                tag_majority_positive_n=majority.get((population, dimension)),
                empty_label_sets=empty,
            )
            if dimension not in ("Research Domains", "Analytical Purposes"):
                require(ledger, f"{key} canonical tag majority count present", context[(population, dimension)]["tag_majority_positive_n"] is not None, True, "tag_diagnostics.csv")
    for dimension in DIMENSIONS:
        require(ledger, f"metric {dimension}", canonical_distance(dimension).__name__, distance_for_dimension(dimension).__name__, "panels.py:252-253")
        require(ledger, f"metric {dimension} same function object", canonical_distance(dimension) is distance_for_dimension(dimension), True, "panels.py:252-253")
    return context


def check_w(ledger: list, built: dict) -> list[dict]:
    exported = {(r["population"], r["dimension"], r["panel"]): r["point_estimate"] for r in read_csv(STAGE_A / "replacement_panel_results.csv")}
    rows = []
    for (population, dimension), item in built.items():
        distance = memoised(canonical_distance(dimension))
        for panel, raters, role in (("ABC", "ABC", "check_W"), ("LBC", "LBC", "supplementary_model_data_integrity"),
                                    ("ALC", "ALC", "supplementary_model_data_integrity"), ("ABL", "ABL", "supplementary_model_data_integrity")):
            result = panel_alpha(item["records"], tuple(raters), distance)
            canonical = float(exported[(population, dimension, panel)])
            rows.append(dict(role=role, population=population, dimension=dimension, panel=panel,
                             computed=result.alpha, canonical_exported=canonical, exact_equal=result.alpha == canonical,
                             computed_repr=repr(result.alpha), canonical_repr=exported[(population, dimension, panel)]))
            require(ledger, f"{role} {population} / {dimension} alpha_{panel} exact", result.alpha == canonical, True,
                    "analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv")
    return rows


# ---------------------------------------------------------------- analyses (step 5)

def compute_all(built: dict, attempts: int = ATTEMPTS, workers: int | None = None) -> dict:
    points = {key: compute.statistics(item["records"], memoised(canonical_distance(key[1]))) for key, item in built.items()}
    workers = workers or min(len(built), os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {key: pool.submit(compute.bootstrap_job, item["records"], key[1], attempts, SEED, MIN_VALID_FRACTION)
                   for key, item in built.items()}
        boots = {key: future.result() for key, future in futures.items()}
    return dict(points=points, boots=boots)


def exported_deltas() -> dict:
    return {(r["population"], r["dimension"], r["delta"]): (None if r["point_estimate"] == "" else float(r["point_estimate"]))
            for r in read_csv(STAGE_A / "replacement_delta_results.csv")}


# ---------------------------------------------------------------- output checks (step 6)

def output_checks(ledger: list, results: dict, attempts: int = ATTEMPTS) -> None:
    for key, point in results["points"].items():
        label = " / ".join(key)
        for name in PAIR_NAMES:
            item = point[name]
            ok = (item.valid and item.value is not None and isfinite(item.value) and -1.0 <= item.value <= 1.0) or (
                not item.valid and item.reason is not None)
            require(ledger, f"{label} {name} in [-1, 1] or undefined with reason", ok, True, "estimator range")
        value = {n: point[n].value if point[n].valid else None for n in STATISTIC_NAMES}

        def arith(fn, *names):
            return None if any(value[n] is None for n in names) else fn(*[value[n] for n in names])

        for name, left, right in DIFFERENCES:
            require(ledger, f"{label} {name} arithmetic exact", value[name], arith(lambda a, b: a - b, left, right), "Analysis 1 points")
        for x, (human, model) in REPLACEMENT_TERMS.items():
            h = arith(lambda a, b: (a + b) / 2, *human)
            m = arith(lambda a, b: (a + b) / 2, *model)
            require(ledger, f"{label} H_{x} arithmetic exact", value[f"H_{x}"], h, "Analysis 1 points")
            require(ledger, f"{label} M_{x} arithmetic exact", value[f"M_{x}"], m, "Analysis 2 points")
            require(ledger, f"{label} D_{x} arithmetic exact", value[f"D_{x}"], None if h is None or m is None else m - h, "Analysis 1-2 points")
        boot = results["boots"][key]
        require(ledger, f"{label} bootstrap seed", boot["_seed"]["seed"], SEED, "instruction")
        for name in STATISTIC_NAMES:
            b = boot[name]
            require(ledger, f"{label} {name} valid+invalid = requested", (b["valid"] + b["invalid"], b["attempted"]), (attempts, attempts), "bootstrap")


# ---------------------------------------------------------------- tables and outputs (step 7)

def build_tables(results: dict, context: dict, deltas: dict, attempts: int = ATTEMPTS, threshold: int = THRESHOLD) -> list[dict]:
    tables, number = [], 0
    for population, _ in POPULATIONS:
        for dimension in DIMENSIONS:
            key = (population, dimension)
            point, boot, ctx = results["points"][key], results["boots"][key], context[key]
            note = DIAGNOSTIC if population == "hard_case" else ""
            d_values = {x: (point[f"D_{x}"].value if point[f"D_{x}"].valid else None) for x in "ABC"}
            delta_values = {x: deltas.get((population, dimension, f"delta_{x}")) for x in "ABC"}
            d_order, delta_order = compute.ordering(d_values), compute.ordering(delta_values)
            agree = "not determinable" if d_order is None or delta_order is None else ("yes" if d_order == delta_order else "no")
            for analysis in (1, 2, 3, 4):
                number += 1
                rows = []
                for name in ANALYSIS_QUANTITIES[analysis]:
                    p, b = point[name], boot[name]
                    row = dict(
                        table_id=f"PWA1T{number:03d}", population=population, population_note=note, dimension=dimension,
                        metric=METRIC_NAME[dimension], analysis=ANALYSIS_TITLES[analysis], quantity=name, definition=DEFINITIONS[name],
                        n_records=ctx["n_records"], tag_majority_positive_n=ctx["tag_majority_positive_n"],
                        estimate=p.value if p.valid else None, estimate_status="defined" if p.valid else "undefined",
                        estimate_undefined_reason=None if p.valid else p.reason, confidence_level=CONFIDENCE,
                        ci_lower=b["lower"], ci_upper=b["upper"],
                        interval_status="reported" if b["interval_reported"] else f"not_reported_valid_replicates_below_{threshold}",
                        bootstrap_requested=b["attempted"], bootstrap_valid=b["valid"], bootstrap_invalid=b["invalid"],
                        bootstrap_invalid_reasons="; ".join(f"{r}: {c}" for r, c in b["invalid_reasons"]) or None,
                        bootstrap_seed=SEED, interval_method="percentile (Hyndman-Fan Type 7), joint record-level bootstrap",
                    )
                    if analysis == 4:
                        x = name[-1]
                        row.update(exported_delta_name=f"delta_{x}", exported_delta_point=delta_values[x],
                                   d_ordering_ascending=d_order, delta_ordering_ascending=delta_order, orderings_agree=agree)
                    rows.append(row)
                tables.append(dict(table_id=f"PWA1T{number:03d}", population=population, dimension=dimension,
                                   analysis=analysis, note=note, context=ctx, rows=rows,
                                   ordering=dict(d=d_order, delta=delta_order, agree=agree) if analysis == 4 else None))
    return tables


def _fmt(value, digits: int = 4) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def render_markdown(tables: list[dict], metadata: dict) -> str:
    lines = [
        "# Exploratory pairwise Krippendorff's α — results",
        "",
        f"Status: exploratory, not preregistered (addendum `{ADDENDUM_COMMIT[:7]}`, `ADDENDUM_pairwise_alpha.md`). "
        f"Dates: {DATE_STATEMENT}; addendum created {ADDENDUM_CREATED}; run {metadata['run_started_utc']}.",
        "",
        "Coders: A = C01, B = C02, C = C03, L = Fable 5 (MOD-006). δ_A = α_LBC − α_ABC, δ_B = α_ALC − α_ABC, δ_C = α_ABL − α_ABC.",
        "",
        f"Confidence level: 95%. Intervals: joint record-level bootstrap per population × dimension (all four raters' labels kept "
        f"together per record), {ATTEMPTS} requested replicates, seed {SEED}, Type-7 percentile bounds; no interval is reported for "
        f"a quantity with fewer than {THRESHOLD} valid replicates; undefined replicates are excluded, not replaced.",
        "",
        "D_X is a descriptive comparison, not a decomposition of δ_X. Orderings are ascending (smallest first); `=` marks an exact tie. "
        "Estimates are shown to 4 decimal places; each table's CSV holds full precision.",
        "",
        "Hard-case tables are labelled **DIAGNOSTIC — non-representative**. Baseline and hard-case are never pooled.",
        "",
        "## Check W — wiring",
        "",
        "| Population | Dimension | Panel | Computed (repr) | Canonical exported (repr) | Exact | Role |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in metadata["check_w"]:
        lines.append(f"| {row['population']} | {row['dimension']} | {row['panel']} | {row['computed_repr']} | {row['canonical_repr']} | "
                     f"{'yes' if row['exact_equal'] else 'NO'} | {row['role']} |")
    for table in tables:
        head = table["rows"][0]
        title = f"{table['table_id']} — {table['population']} · {table['dimension']} ({head['metric']}) · {ANALYSIS_TITLES[table['analysis']]}"
        lines += ["", f"## {title}", ""]
        if table["note"]:
            lines += [f"**{table['note']}**", ""]
        ctx = table["context"]
        context = f"Records: {ctx['n_records']}."
        if ctx["tag_majority_positive_n"] is not None:
            context += f" Records the coder majority applied the tag to (canonical export): {ctx['tag_majority_positive_n']}."
        lines += [context + " Confidence level: 95%.", ""]
        extra = table["analysis"] == 4
        lines.append("| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |"
                     + (" Exported δ (same X) |" if extra else ""))
        lines.append("| --- | --- | --- | --- | --- | --- | --- |" + (" --- |" if extra else ""))
        for row in table["rows"]:
            status = row["estimate_status"] + (f" ({row['estimate_undefined_reason']})" if row["estimate_undefined_reason"] else "")
            line = (f"| {row['definition']} | {_fmt(row['estimate'])} | {status} | {_fmt(row['ci_lower'])} | {_fmt(row['ci_upper'])} | "
                    f"{row['interval_status']} | {row['bootstrap_valid']} / {row['bootstrap_invalid']} / {row['bootstrap_requested']} |")
            if extra:
                line += f" {_fmt(row['exported_delta_point']) if row['quantity'].startswith('D_') else ''} |"
            lines.append(line)
        if extra:
            o = table["ordering"]
            lines += ["", f"Ordering of D (ascending): {o['d'] or 'not determinable'}. "
                          f"Ordering of exported δ point estimates (ascending): {o['delta'] or 'not determinable'}. "
                          f"Orderings agree: {o['agree']}."]
        reasons = [f"{r['definition']}: {r['bootstrap_invalid_reasons']}" for r in table["rows"] if r["bootstrap_invalid_reasons"]]
        if reasons:
            lines += ["", "Invalid-replicate reasons: " + " | ".join(reasons) + "."]
    return "\n".join(lines) + "\n"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if v is None else repr(v) if isinstance(v, float) else v) for k, v in row.items()})


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    ledger: list[dict] = []
    pre = preflight()
    require(ledger, "addendum commit is ancestor of code", pre["addendum_is_ancestor"], True, "git")
    sources = source_checks(ledger)
    data = build_stage_a_data()  # sole response loader and membership implementation
    built = build_records(data)
    context = data_checks(ledger, data, built)
    check_w_rows = check_w(ledger, built)
    print("Pre-computation checks and check W passed.", flush=True)
    results = compute_all(built)
    output_checks(ledger, results)
    deltas = exported_deltas()
    tables = build_tables(results, context, deltas)
    completed = datetime.now(timezone.utc).isoformat()

    code_commits = git("log", "--format=%H %s", f"{ADDENDUM_COMMIT}..HEAD", "--", "analysis/pairwise_alpha_exploratory").splitlines()
    packages = {}
    for name in ("numpy", "pandas", "PyYAML"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    metadata = dict(
        specification_and_instruction_date=DATE_STATEMENT,
        addendum_creation_date=ADDENDUM_CREATED,
        run_started_utc=started,
        run_completed_utc=completed,
        status="exploratory, not preregistered",
        addendum_commit=ADDENDUM_COMMIT,
        execution_code_commit=pre["head"],
        analysis_code_commits_since_addendum=code_commits,
        coder_mapping=dict(A="C01", B="C02", C="C03", L="Fable 5 (MOD-006)",
                           delta_A="alpha_LBC - alpha_ABC (replaces C01)", delta_B="alpha_ALC - alpha_ABC (replaces C02)",
                           delta_C="alpha_ABL - alpha_ABC (replaces C03)",
                           code_references=["analysis/scratch_coder_stage_a/config.py:13", "analysis/scratch_coder_stage_a/panels.py:243-247",
                                            "analysis/validation/replacement.py:71-84"]),
        metrics={d: dict(metric=METRIC_NAME[d], function=canonical_distance(d).__name__) for d in DIMENSIONS},
        metric_code_references=["analysis/scratch_coder_stage_a/panels.py:252-253", "analysis/scratch_coder_stage_a/agreement.py:171",
                                "analysis/validation/metrics.py"],
        estimator="analysis/validation/alpha.py krippendorff_alpha (distance memoised per process with functools.lru_cache; identical returned objects)",
        bootstrap=dict(function="analysis/validation/bootstrap.py bootstrap_joint", seed=SEED, requested_replicates=ATTEMPTS,
                       minimum_valid_fraction=MIN_VALID_FRACTION, minimum_valid_replicates=THRESHOLD, confidence_level=CONFIDENCE,
                       percentile="Hyndman-Fan Type 7", resampling_unit="record (A, B, C, L labels kept together)",
                       undefined_rule="excluded per statistic; no top-up or replacement", parallelism="one process per population x dimension; each job seeded identically and independently"),
        populations=dict(baseline=150, hard_case=75, pooled=False, hard_case_label=DIAGNOSTIC),
        data_sources=sources,
        absent_manifest_authority_not_used=dict(
            manifest_id="POST-022", path=resolve_manifest_row("POST-022")["current_path"],
            note="formal assignment metadata (coder seeds); absent on this machine; hashed by verify_authorities but not read by build_stage_a_data or any alpha computation; not verified"),
        canonical_exports=[dict(path=(STAGE_A / n).relative_to(ROOT).as_posix(), sha256=sha256_file(STAGE_A / n),
                                commit=git("log", "-1", "--format=%H", "--", (STAGE_A / n).relative_to(ROOT).as_posix()))
                           for n in ("replacement_panel_results.csv", "replacement_delta_results.csv")]
                          + [dict(path=(STAGE_B / "tag_diagnostics.csv").relative_to(ROOT).as_posix(), sha256=sha256_file(STAGE_B / "tag_diagnostics.csv"),
                                  commit=git("log", "-1", "--format=%H", "--", (STAGE_B / "tag_diagnostics.csv").relative_to(ROOT).as_posix()))],
        shared_code=[dict(path=p, commit=git("log", "-1", "--format=%H", "--", p), sha256=sha256_file(ROOT / p)) for p in SHARED_CODE],
        protocol_search=dict(
            file="preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx (PRO-018)",
            file_sha256=resolve_manifest_row("PRO-018")["sha256"],
            pairwise_krippendorff_alpha_among_coders="not found", pairwise_krippendorff_alpha_model_vs_each_coder="not found",
            related_specified_analyses_not_pairwise_alpha=["Section 8.4 exact-set agreement model vs each coder",
                                                           "Section 8.4 Jaccard model vs each coder",
                                                           "Section 8.4 per-label Cohen's kappa, 3 human-human and 3 model-human pairs",
                                                           "Section 8.4 per-tag Cohen's kappa and Gwet's AC1"],
            labelled_preregistered=False),
        prior_result_search=dict(
            locations=["repository working tree excluding venv/ and .git/", "git history, all refs (messages, -S, -G)"],
            pairwise_krippendorff_alpha="not found",
            other_pairwise_results_found=["analysis/outputs_validation_scratch_stage_b_20260825/per_label_pairwise_kappa.csv (S5T005/S5T006)",
                                          "preregistration/package/05_training_and_pilot/pilot_analysis/pilot_pairwise_agreement.csv (pilot exact-set/Jaccard)",
                                          "commits ad34cb6, 6e067f4: LLM multi-trial / method-benchmark pairwise agreement"]),
        software=dict(python=sys.version, platform=platform.platform(), packages=packages),
        check_w=check_w_rows,
        checks=ledger,
        output_tables=[t["table_id"] for t in tables],
    )
    markdown = render_markdown(tables, metadata)
    serialised = markdown + json.dumps(metadata, ensure_ascii=False, default=str) + json.dumps([t["rows"] for t in tables], default=str)
    leaked = sum(record_id in serialised for record_id in data.formal_ids)
    require(ledger, "no formal record ID in any output", leaked, 0, "restricted-identifier guard")
    metadata["checks"] = ledger
    for table in tables:
        write_csv(HERE / f"{table['table_id']}.csv", table["rows"])
    (HERE / "results_pairwise_alpha.md").write_text(markdown, encoding="utf-8")
    metadata["output_file_sha256"] = {p.name: sha256_file(p) for p in sorted(HERE.glob("PWA1T*.csv")) + [HERE / "results_pairwise_alpha.md"]}
    (HERE / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {len(tables)} tables; {len(ledger)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
