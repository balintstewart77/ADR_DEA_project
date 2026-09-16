"""Ordered D-G execution; requires committed code and pre-analysis validation.

Run from the repository root: python -m analysis.confidence_exploratory.run
No real-data statistic is calculated until source_checks returns successfully.
No output file is written until output_checks returns successfully.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

from analysis.scratch_coder_stage_a.config import CODERS, ROOT, MANIFEST
from analysis.scratch_coder_stage_a.load import resolve_manifest_row, sha256_file, read_manifest_csv
from analysis.scratch_coder_stage_a.panels import build_stage_a_data, population_ids
from analysis.scratch_coder_stage_a.sufficiency import majority_category, SPLIT, SUFFICIENCY_LABELS
from analysis.scratch_coder_stage_a.taxonomy import CONFIDENCE_LABELS
from analysis.validation.bootstrap import bootstrap_joint
from analysis.validation.intervals import wilson_interval
from .ordinal_distance import estimate, bootstrap_evaluator

HERE = Path(__file__).resolve().parent
ADDENDUM = "660f7d8624f03629cb39dd2cbe8911e0497d7895"
SEED = 20260915
ATTEMPTS = 2000
THRESHOLD = 1800
DATE_STATEMENT = "specified, and instruction v5 issued, on or before 16 September 2026 (investigator-attested)"
DIAGNOSTIC = "DIAGNOSTIC — non-representative"
CONF = ("High", "Medium", "Low")
SUFF = tuple(SUFFICIENCY_LABELS.values())
RANK = {"Low": 1, "Medium": 2, "High": 3}
RANK_LABELS = {v: k for k, v in RANK.items()}
EXPECTED_CONF = {"baseline": (193, 242, 15), "hard_case": (78, 139, 8)}
EXPECTED_BASE_SUFF = {"all": (262, 176, 12), "C01": (107, 39, 4), "C02": (96, 48, 6), "C03": (59, 89, 2)}
STAGE = ROOT / "analysis/outputs_validation_scratch_20260824"
CANONICAL = ROOT / "analysis/scratch_coder_results/run_metadata.json"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def check(ledger, name, actual, expected, source):
    if actual != expected:
        raise RuntimeError(f"{name} failed: actual={actual!r}; expected={expected!r}; source={source}")
    ledger.append(dict(check=name, status="passed", actual=actual, expected=expected, source=source))


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def source_checks():
    ledger, sources = [], []
    historical = json.loads((STAGE / "run_metadata.json").read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
    # D.0: exact file bytes, with no newline normalisation for restricted data.
    for identifier in ("POST-028", "POST-009", "POST-011", "POST-019"):
        row = resolve_manifest_row(identifier)
        path = ROOT / row["current_path"]
        actual = sha256_file(path)
        check(ledger, "1.0 " + identifier, actual, row["sha256"], str(MANIFEST.relative_to(ROOT)))
        registered = git("log", "--reverse", "--format=%H", "-S", identifier + ",", "--", MANIFEST.relative_to(ROOT).as_posix()).splitlines()[0]
        sources.append(dict(manifest_id=identifier, path=row["current_path"], sha256=actual,
                            manifest_path=MANIFEST.relative_to(ROOT).as_posix(), registering_commit=registered))
        for label, old in (("Stage A", historical), ("canonical", canonical["source_run_metadata"]["a"])):
            previous = next(x for x in old["verified_authorities"] if x["manifest_id"] == identifier)
            check(ledger, "1.2 authority identity " + label + " " + identifier,
                  (row["current_path"], actual), (previous["path"], previous["expected_sha256"]), "S8–S10 recorded input authorities")

    data = build_stage_a_data()  # Sole response loader and membership implementation.
    responses = data.responses
    check(ledger, "1.1 duplicate coder-record keys", int(responses.duplicated(["population", "record_id", "coder"]).sum()), 0, "shared loader response frame")
    check(ledger, "1.3 populations", sorted(responses.population.unique()), ["baseline", "hard_case"], "instruction")
    suff_export = read_csv(STAGE / "sufficiency_response_distribution.csv")
    unclear_export = read_csv(STAGE / "unclear_register_summary.csv")
    # Check source exports against canonical file identities and every selected cell.
    for filename in ("sufficiency_response_distribution.csv", "unclear_register_summary.csv"):
        path = STAGE / filename
        recorded = canonical["source_files"][path.relative_to(ROOT).as_posix()]["sha256"]
        raw = path.read_bytes()
        represented = hashlib.sha256(raw).hexdigest()
        if represented != recorded:
            represented = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        check(ledger, "canonical export identity " + filename, represented, recorded, "canonical source_files")
    for item in canonical["result_items"]:
        if item["table_id"] not in ("S8T001", "S8T002", "S10T001", "S10T002", "S10T003", "S10T004"):
            continue
        source = suff_export if item["source_name"] == "sufficiency_response_distribution" else unclear_export
        matches = [r for r in source if all(r[k] == v for k, v in item["source_key"].items())]
        if len(matches) != 1:
            raise RuntimeError("Canonical source-key lookup is not unique")
        source_row = matches[0]
        check(ledger, "canonical cell " + item["result_id"], source_row[item["source_column"]], item["raw_estimate"], "canonical result_items and CSV")
        expected_denom = str(source_row["denominator"]) + (" records" if item["source_key"].get("measure", "").startswith("records_") else " coder responses")
        # S8 named-coder distributions are records, although source data are response rows.
        if item["table_id"].startswith("S8") and item["source_key"]["coder"] != "all":
            expected_denom = str(source_row["denominator"]) + " coder responses"
        if int(item["denominator_display"].split()[0]) != int(source_row["denominator"]):
            raise RuntimeError("Canonical denominator differs from CSV")

    summary = {}
    for population, n, authority in (("baseline", 150, "POST-009"), ("hard_case", 75, "POST-011")):
        rows = responses[responses.population == population]
        ids = population_ids(data, population, {})
        historical_ids = frozenset(read_manifest_csv(authority)["record_id"])
        # Compare the ID sets directly; export only cardinalities and equality, never IDs.
        same = frozenset(rows.record_id) == ids == historical_ids
        check(ledger, "1.2 ID-set equality " + population, same, True, "hash-identical sample authority recorded for S8–S10; shared population_ids")
        check(ledger, "1.2 record count " + population, len(ids), n, "instruction")
        check(ledger, "1.3 coder set " + population, sorted(rows.coder.unique()), list(CODERS), "instruction")
        for coder in CODERS:
            selected = rows[rows.coder == coder]
            check(ledger, "1.3 responses " + population + " " + coder, len(selected), n, "instruction")
            check(ledger, "1.3 confidence permitted " + population + " " + coder, bool(selected.confidence.isin(CONFIDENCE_LABELS).all()), True, "shared source confidence labels")
            check(ledger, "1.3 sufficiency permitted " + population + " " + coder, bool(selected.sufficiency.isin(SUFFICIENCY_LABELS).all()), True, "shared source sufficiency labels")
        conf_counts = tuple(int((rows.confidence == code).sum()) for code in CONFIDENCE_LABELS)
        check(ledger, "1.4 instruction confidence " + population, conf_counts, EXPECTED_CONF[population], "instruction High/Medium/Low")
        for dimension in ("Research Domains", "Analytical Purposes"):
            exported = tuple(int(next(r for r in unclear_export if r["population"] == population and r["dimension"] == dimension and r["section"] == "response_crosstab_confidence" and r["category"] == category)["denominator"]) for category in CONF)
            check(ledger, "1.4 canonical confidence " + population + " " + dimension, conf_counts, exported, "S10T001–S10T004 and unclear_register_summary.csv")
        per_coder = {}
        for coder in ("all", *CODERS):
            selected = rows if coder == "all" else rows[rows.coder == coder]
            counts = tuple(int((selected.sufficiency == code).sum()) for code in SUFFICIENCY_LABELS)
            exported = tuple(int(next(r for r in suff_export if r["population"] == population and r["coder"] == coder and r["category"] == category)["count"]) for category in SUFF)
            number = "1.5" if coder == "all" else "1.6"
            check(ledger, number + " canonical sufficiency " + population + " " + coder, counts, exported, "S8T001/S8T002 and sufficiency_response_distribution.csv")
            if population == "baseline":
                check(ledger, number + " instruction sufficiency " + coder, counts, EXPECTED_BASE_SUFF[coder], "instruction Sufficient/Partially sufficient/Insufficient")
            per_coder[coder] = counts
        summary[population] = dict(records=n, responses=len(rows), confidence_counts=conf_counts, sufficiency_counts=per_coder)
    return data, ledger, sources, summary


def proportion_row(population, category, count, denominator, coder=None, sufficiency=None, intervals=False):
    row = dict(population=population, analysis_note=DIAGNOSTIC if population == "hard_case" else "",
               category=category, count=count, denominator=denominator, proportion=count / denominator if denominator else None,
               count_status="reported", estimate_status="reported" if denominator else "undefined",
               interval_status="not_applicable", interval_method="none", confidence_level=None, ci_lower=None, ci_upper=None)
    if coder is not None:
        row["coder"] = coder
    if sufficiency is not None:
        row["sufficiency"] = sufficiency
    if intervals:
        if population == "baseline":
            ci = wilson_interval(count, denominator)
            row.update(interval_status="reported", interval_method="wilson_score", confidence_level=.95, ci_lower=ci.lower, ci_upper=ci.upper)
        else:
            row.update(interval_status="not_applied_diagnostic_sample")
    return row


def compute(data):
    tables = []
    for population in ("baseline", "hard_case"):
        responses = data.responses[data.responses.population == population]
        n = len(population_ids(data, population, {}))
        # Labels decode source codes; ranks are a separate analytical mapping.
        units = []
        for _, group in responses.groupby("record_id", sort=True):
            by_coder = {r["coder"]: RANK[CONFIDENCE_LABELS[r["confidence"]]] for r in group.to_dict("records")}
            units.append(tuple(by_coder[c] for c in CODERS))
        dist = []
        for coder in CODERS:
            counts = Counter(CONFIDENCE_LABELS[v] for v in responses.loc[responses.coder == coder, "confidence"])
            dist.extend(proportion_row(population, c, counts[c], n, coder=coder, intervals=True) for c in CONF)
        majorities = Counter(majority_category(u, RANK_LABELS) for u in units)
        majority = [proportion_row(population, c, majorities[SPLIT if c == "No majority" else c], n, intervals=True) for c in (*CONF, "No majority")]
        print("Step E: ordinal alpha bootstrap " + population, flush=True)
        point = estimate(units)
        boot = bootstrap_joint(units, bootstrap_evaluator, statistic_names=("alpha",), attempted_replicates=ATTEMPTS, seed=SEED)
        result = boot.statistics["alpha"]
        alpha = [dict(population=population, analysis_note=DIAGNOSTIC if population == "hard_case" else "", alpha=point.alpha,
                      estimate_status="reported" if point.valid else "undefined", undefined_reason=point.undefined_reason,
                      ci_lower=result.lower, ci_upper=result.upper, confidence_level=.95, seed=SEED,
                      requested_replicates=result.attempted, valid_replicates=result.valid, invalid_replicates=result.invalid,
                      valid_replicate_threshold=THRESHOLD, minimum_valid_fraction=.90,
                      interval_status="reported" if result.interval_reported else "suppressed_valid_replicate_policy",
                      interval_method="bootstrap_percentile_type7", observed_disagreement=point.observed_disagreement,
                      expected_disagreement=point.expected_disagreement, denominator=n, rating_count=point.number_of_ratings,
                      invalid_reasons=json.dumps(dict(result.invalid_reasons), sort_keys=True))]
        unanimity = [dict(population=population, analysis_note=DIAGNOSTIC if population == "hard_case" else "",
                          count=sum(len(set(u)) == 1 for u in units), denominator=n, estimate_status="reported", interval_status="not_applicable")]
        cross = []
        for confidence in CONF:
            selected = responses[responses.confidence.map(CONFIDENCE_LABELS) == confidence]
            counts = Counter(SUFFICIENCY_LABELS[v] for v in selected.sufficiency)
            cross.extend(proportion_row(population, confidence, counts[s], len(selected), sufficiency=s) for s in SUFF)
        for title, rows in (("Confidence per coder", dist), ("Majority confidence", majority), ("Ordinal confidence alpha", alpha),
                            ("Unanimous confidence count", unanimity), ("Confidence × register-entry sufficiency", cross)):
            tables.append(dict(table_id=f"SCF1T{len(tables)+1:03d}", population=population, title=title, rows=rows))
    return tables


def output_checks(tables, summary):
    ledger = []
    for population in ("baseline", "hard_case"):
        dist, majority, alpha, unanimity, cross = [t["rows"] for t in tables if t["population"] == population]
        n = summary[population]["records"]
        for coder in CODERS:
            selected = [r for r in dist if r["coder"] == coder]
            check(ledger, "2.1 coder sum " + population + " " + coder, sum(r["count"] for r in selected), n, "Group 1 record count")
            check(ledger, "2.1 categories " + population + " " + coder, [r["category"] for r in selected], list(CONF), "instruction")
        check(ledger, "2.1 majority sum " + population, sum(r["count"] for r in majority), n, "Group 1 record count")
        check(ledger, "2.1 majority categories " + population, [r["category"] for r in majority], [*CONF, "No majority"], "instruction")
        check(ledger, "2.2 nine cells " + population, len(cross), 9, "instruction")
        check(ledger, "2.2 grand total " + population, sum(r["count"] for r in cross), 3*n, "Group 1 response count")
        for confidence, expected in zip(CONF, summary[population]["confidence_counts"]):
            check(ledger, "2.2 confidence margin " + population + " " + confidence, sum(r["count"] for r in cross if r["category"] == confidence), expected, "Group 1 check 1.4")
        for sufficiency, expected in zip(SUFF, summary[population]["sufficiency_counts"]["all"]):
            check(ledger, "2.2 sufficiency margin " + population + " " + sufficiency, sum(r["count"] for r in cross if r["sufficiency"] == sufficiency), expected, "Group 1 check 1.5")
        for index, row in enumerate(dist + majority + cross):
            denominator = summary[population]["confidence_counts"][CONF.index(row["category"])] if "sufficiency" in row else n
            check(ledger, f"2.3 denominator {population} {index}", row["denominator"], denominator, "Group 1 count")
            check(ledger, f"2.3 proportion {population} {index}", row["proportion"], row["count"]/denominator if denominator else None, "count / denominator")
            check(ledger, f"2.3 estimate status {population} {index}", row["estimate_status"], "reported" if denominator else "undefined", "zero-denominator rule")
            if "sufficiency" in row or population == "hard_case":
                check(ledger, f"interval scope {population} {index}", (row["ci_lower"], row["ci_upper"]), (None, None), "instruction")
        a = alpha[0]
        check(ledger, "2.4 attempts " + population, a["valid_replicates"] + a["invalid_replicates"], ATTEMPTS, "existing bootstrap")
        check(ledger, "2.4 requested " + population, a["requested_replicates"], ATTEMPTS, "instruction")
        report = a["valid_replicates"] >= THRESHOLD
        check(ledger, "2.4 status " + population, a["interval_status"], "reported" if report else "suppressed_valid_replicate_policy", "existing 90% rule")
        check(ledger, "2.4 bounds availability " + population, a["ci_lower"] is not None and a["ci_upper"] is not None, report, "existing 90% rule")
    return ledger


JUDGEMENTS = [
    "Continued from Step C under v5.1; only the two expected untracked files were present. Step A was not repeated.",
    "Used the existing project venv for krippendorff==0.8.2; dependency files unchanged. The prior metadata-access problem is not a numerical validation failure under v5.1.",
    "Used both external validation routes and 24 deterministic synthetic datasets spanning balanced, absent-category and skewed-frequency cases.",
    "Exact Fraction arithmetic constructs squared ordinal distances; precomputed float entries feed the unchanged alpha implementation. The distance is rebuilt for each call.",
    "Decoded source confidence 1=High, 2=Medium, 3=Low using shared labels, then mapped labels to required analytical ranks Low=1, Medium=2, High=3; no response was imputed or changed.",
    "Displayed shared majority split status as No majority, retaining the shared majority decision itself.",
    "Used ten tables: per-coder, majority, alpha, unanimous count and crosstab for baseline, then the same five for hard-case. Unanimity has a separate count-only table.",
    "Used explicit separate estimate and interval status columns consistent with canonical semantics; hard-case proportion status says not_applied_diagnostic_sample.",
    "Compared record-ID sets to hash-identical population authorities recorded in Stage A and canonical metadata because aggregate S8–S10 exports do not contain record IDs. No restricted IDs are exported.",
    "Canonical CSV identities permit their recorded LF representation; restricted input integrity always compares exact bytes.",
    "Retained Fraction-to-float distances without rescaling so observed and expected disagreements refer to the instructed raw squared metric.",
    "Used the same specified seed independently for each population and sorted record IDs for deterministic record ordering.",
    "Stored validation evidence with code, and all Group 1/2 checks in output metadata; no real-data result was written before Group 2 passed.",
    "Recorded actual file creation and execution dates separately from the exact investigator-attested date statement; repository history timestamps are provenance, not inferred specification dates.",
    "Preserved the prior-result search findings in the addendum, including pilot agreement-pattern results and formal Cannot assess × confidence summaries, without asserting what the investigator inspected.",
    "Interpreted the Section 3A nominal wiring test as synthetic validation only; no nominal confidence statistic is computed on real data.",
]


def write_outputs(tables, metadata):
    texts = ["# Exploratory coder-confidence results", "", DATE_STATEMENT + ".", "",
             "Exploratory; not preregistered. Populations are analysed separately. These results do not partition coder and record effects or define low-confidence human cases.", "",
             "Estimate and interval statuses are recorded separately. Count statuses are reported; zero-denominator proportions are undefined. Baseline distribution intervals are 95% Wilson score. Ordinal α intervals are 95% Type-7 percentile bootstrap intervals with 2,000 attempted record draws, seed 20260915 and a minimum of 1,800 valid estimates. Undefined draws are not replaced.", ""]
    for table in tables:
        rows = table["rows"]
        title = table["table_id"] + " — " + ("Baseline" if table["population"] == "baseline" else "Hard-case — " + DIAGNOSTIC) + " — " + table["title"]
        texts.extend(["## " + title, ""])
        if "sufficiency" in rows[0]:
            texts.extend(["Response-level counts; proportions use the total within each confidence category as denominator. No intervals, tests or association measures.", ""])
        else:
            texts.extend([f"Denominator: {rows[0]['denominator']} records.", ""])
        columns = [k for k in rows[0] if k not in ("population", "analysis_note")]
        texts.extend(["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"])
        for row in rows:
            texts.append("| " + " | ".join("" if row[k] is None else str(row[k]).replace("|", "\\|") for k in columns) + " |")
        texts.append("")
    # G begins here, after all results and checks exist in memory.
    for table in tables:
        with (HERE / (table["table_id"] + ".csv")).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["table_id", *table["rows"][0]])
            writer.writeheader()
            writer.writerows(dict(table_id=table["table_id"], **row) for row in table["rows"])
    (HERE / "results_confidence.md").write_text("\n".join(texts), encoding="utf-8")
    metadata["tables"] = [{k: v for k, v in t.items() if k != "rows"} for t in tables]
    metadata["output_file_sha256"] = {p.name: sha256_file(p) for p in [HERE / "results_confidence.md", *[HERE / (t["table_id"] + ".csv") for t in tables]]}
    (HERE / "run_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if git("status", "--porcelain"):
        raise RuntimeError("Commit code before starting D")
    if (HERE / "run_metadata.json").exists() or list(HERE.glob("SCF1T*.csv")):
        raise RuntimeError("Outputs already exist; this command creates a new execution only")
    code = git("rev-parse", "HEAD")
    subprocess.run(["git", "merge-base", "--is-ancestor", ADDENDUM, code], check=True)
    validation = json.loads((HERE / "validation_record.json").read_text(encoding="utf-8"))
    if any(validation[str(i)]["status"] != "passed" for i in (3, 4, 5)) or not any(validation[str(i)]["status"] == "passed" for i in (1, 2)):
        raise RuntimeError("Validation prerequisites not met")
    started = datetime.now(timezone.utc).isoformat()
    print("Step D: source and canonical checks", flush=True)
    data, group1, sources, summary = source_checks()
    print("Step D passed: " + json.dumps(summary), flush=True)
    tables = compute(data)
    print("Step F: output consistency", flush=True)
    group2 = output_checks(tables, summary)
    code_commits = git("log", "--reverse", "--format=%H", ADDENDUM + "..HEAD", "--", "analysis/confidence_exploratory/*.py", "analysis/confidence_exploratory/validation_record.json").splitlines()
    erratum = git("log", "-1", "--format=%H", "--", "analysis/confidence_exploratory/ADDENDUM_ERRATUM.md")
    shared = ["analysis/scratch_coder_stage_a/" + p + ".py" for p in ("load", "panels", "sufficiency", "taxonomy", "agreement")]
    shared += ["analysis/validation/" + p + ".py" for p in ("alpha", "metrics", "intervals", "bootstrap")]
    metadata = dict(specification_date=DATE_STATEMENT, instruction_issue_date=DATE_STATEMENT, continuation="v5.1",
                    addendum_creation_date="2026-09-16", run_started_utc=started, run_completed_utc=datetime.now(timezone.utc).isoformat(),
                    addendum_commit=ADDENDUM, erratum_commit=erratum, analysis_code_commits=code_commits, execution_code_commit=code,
                    data_sources=sources, source_checks=group1, output_checks=group2, checked_totals=summary, validation=validation,
                    shared_code=[dict(path=p, commit=git("log", "-1", "--format=%H", "--", p), sha256=sha256_file(ROOT/p)) for p in shared],
                    input_export_sha256={str(p.relative_to(ROOT)): sha256_file(p) for p in (CANONICAL, STAGE/"run_metadata.json", STAGE/"sufficiency_response_distribution.csv", STAGE/"unclear_register_summary.csv")},
                    seed=SEED, requested_replicates_per_population=ATTEMPTS, valid_replicate_threshold=THRESHOLD, minimum_valid_fraction=.9,
                    confidence_level=.95, percentile_method="Type-7, 2.5th and 97.5th percentiles of valid replicates",
                    undefined_replicate_treatment="Count invalid; no replacement, redraw or top-up; withhold bounds below threshold",
                    bootstrap_results={t["population"]: t["rows"][0] for t in tables if t["title"] == "Ordinal confidence alpha"},
                    ordinal_category_mapping=RANK, source_category_mapping=CONFIDENCE_LABELS,
                    distance_contract=dict(path="analysis/validation/alpha.py", pairable_lines="38–41", within_unit_weight_lines="49–54", direct_float_conversion_lines=[50,58], expected_disagreement_lines="57–63", receives="category values", squares_returned_distance=False, arithmetic="Fraction distance construction then existing float estimator", recomputation="bootstrap evaluator constructs metric from each sampled block"),
                    software_versions={name: importlib.metadata.version(name) for name in ("numpy", "pandas", "PyYAML", "krippendorff")},
                    python=sys.version, platform=platform.platform(), judgements=JUDGEMENTS,
                    prior_result_search="See committed addendum: pilot confidence agreement flags and exact counts, pilot confidence frequencies/majorities, and formal Cannot assess × confidence summaries found. No formal confidence alpha or confidence × sufficiency table found in searched text/history.",
                    execution_scope="One complete D–G execution from final committed code; real-data calculations limited to three specified analyses.")
    print("Step F passed; Step G writing outputs", flush=True)
    write_outputs(tables, metadata)
    print(json.dumps({"code_commit": code, "tables": len(tables), "checks_passed": len(group1)+len(group2)}, indent=2), flush=True)


if __name__ == "__main__":
    main()
