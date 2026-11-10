"""Full-register replicate of the Fable 5 production run (exploratory, post-registration).

Specification: SPEC_fable_production_replicate_2026-11-10.md (written before this code).

Runs the production code from commit fdc13fd, extracted to a temporary directory, on
the June 2026 register, in production's two stages: the 201 run-1 sample records
(21 batches), then the other 1,108 records (111 batches), with batch membership fixed
in advance. Check mode (the default) makes no API call. ``--execute`` sends requests,
and every batch's uncached input tokens must equal the value logged for the same batch
in run 1 or production, which shows the request text is identical.

    python analysis/fable_production_replicate_exploratory/run.py
    python analysis/fable_production_replicate_exploratory/run.py --execute --stage R --max-batches 1
    python analysis/fable_production_replicate_exploratory/run.py --execute --stage R --run-dir <dir>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SPEC = HERE / "SPEC_fable_production_replicate_2026-11-10.md"

PRODUCTION_COMMIT = "fdc13fdcafcacafbb86d7818fe1485be0b1ed912"
MODEL = "claude-fable-5"
PROMPT_VERSION = "dict-1.0-rc2"
MAX_TOKENS = 8192
BATCH_SIZE = 10
PARSE_KWARGS = {"model", "max_tokens", "messages", "output_format"}
EXPECTED_VERSIONS = {
    "python": "3.13.2", "anthropic": "0.86.0", "pydantic": "2.12.5",
    "httpx": "0.28.1", "pandas": "2.2.3", "PyYAML": "6.0.2",
}
EXPECTED_COUNTS = {"records": 1309, "stage_R_records": 201, "stage_R_batches": 21, "stage_P_records": 1108, "stage_P_batches": 111}

REGISTER = ROOT / "data/dea_accredited_projects_20260601.csv"
REGISTER_RELATIVE = "data/dea_accredited_projects_20260601.csv"
TAXONOMY_RELATIVE = "taxonomy_data_dictionary.yaml"
TAXONOMY = ROOT / TAXONOMY_RELATIVE
STABILITY_METRICS = ROOT / "preregistration/package/03_preexisting_model_evidence/fable_run_stability_metrics.json"
RUN1_CACHE = ROOT / "analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json"
RUN1_METADATA = ROOT / "analysis/outputs/model_comparison_fable_5_run1/run_metadata.json"
PRODUCTION_CACHE = ROOT / "analysis/outputs_classified_20260702_fable5/llm_layer_cache.json"
PRODUCTION_METADATA = ROOT / "analysis/outputs_classified_20260702_fable5/run_metadata.json"

# Record IDs changed after the production run (2020/097 and 2020/102 renamed; 2023/211/a and /b
# collapsed into 2023/211, whose production entry is /b by fingerprint). Used only to map
# replicate records onto production's canonical keys.
CANONICAL_ID = {"2020/097": "2020/097 CLOSED", "2020/102": "2020/102 CLOSED", "2023/211/b": "2023/211"}
NOT_IN_CANONICAL = {"2023/211/a"}

# Pricing used for the production run's cost estimate (5-minute prompt-cache rates).
PRICING = {"base_input_per_mtok": 10.00, "cache_write_5m_per_mtok": 12.50, "cache_read_per_mtok": 1.00, "output_per_mtok": 50.00}


class PreflightError(RuntimeError):
    pass


class RefusedFallback(RuntimeError):
    """Production code falls back to an unstructured call when parsing fails; the replicate does not."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def canonical(record_id: str) -> str:
    return CANONICAL_ID.get(record_id, record_id)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightError(message)


# ---------------------------------------------------------------------------- production code and inputs
def materialise_production_code(target: Path) -> str:
    """Extract the fdc13fd tree into ``target`` and return its tree hash.

    Production read the working-copy taxonomy and register on 2 July, so those exact bytes replace
    the extracted copies, after checking that their content equals fdc13fd's apart from line endings.
    """
    archive = git("-c", "core.autocrlf=false", "archive", "--format=tar", PRODUCTION_COMMIT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")
    for relative, path in ((TAXONOMY_RELATIVE, TAXONOMY), (REGISTER_RELATIVE, REGISTER)):
        committed, working = (target / relative).read_bytes(), path.read_bytes()
        require(committed.replace(b"\r\n", b"\n") == working.replace(b"\r\n", b"\n"), f"{relative} content differs from fdc13fd")
        (target / relative).write_bytes(working)
    return git("rev-parse", f"{PRODUCTION_COMMIT}^{{tree}}").decode().strip()


def import_production_classifier(tree: Path, scratch: Path):
    if any(name == "analysis" or name.startswith(("analysis.", "dashboard")) for name in sys.modules):
        raise PreflightError("analysis or dashboard modules were imported before the production tree")
    sys.path.insert(0, str(tree))
    from analysis import llm_theme_analysis_v3 as clf  # noqa: PLC0415  (imported from the extracted tree)
    from analysis import register_cleaning  # noqa: PLC0415
    for module in (clf, register_cleaning):
        require(Path(module.__file__).resolve().is_relative_to(tree.resolve()), f"{module.__name__} imported from outside the production tree")
    # As the production release script did: set the model, redirect outputs, rebuild the static prompt.
    clf.MODEL = MODEL
    clf.OUTPUT_DIR = str(scratch)
    clf.CACHE_FILE = str(scratch / "llm_layer_cache.json")
    clf._build_static_prompt.cache_clear()
    require((clf.PROMPT_VERSION, clf.BATCH_SIZE, clf.MAX_TOKENS, clf.CACHE_SCHEMA_VERSION) == (PROMPT_VERSION, BATCH_SIZE, MAX_TOKENS, 6),
            "production classifier constants differ from the specification")
    return clf


def environment_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for package in ("anthropic", "pydantic", "httpx", "pandas", "PyYAML"):
        versions[package] = importlib_metadata.version(package)
    return versions


def build_plan(clf, df) -> dict[str, Any]:
    """Records in production's order and the two stages' fixed batch lists (as ``classify_all`` builds them)."""
    records = []
    for _, row in df.iterrows():
        prompt_title = clf._sanitise_prompt_text(row["Title"])
        prompt_datasets = clf._summarise_datasets(row.get("Datasets Used", ""))
        record_id = str(row["Record ID"])
        records.append({"id": record_id, "title": row["Title"], "prompt_title": prompt_title, "prompt_datasets": prompt_datasets,
                        "fingerprint": clf._classification_fingerprint(prompt_title, prompt_datasets), "prompt_id": record_id})
    seed_ids = set(json.loads(RUN1_CACHE.read_text(encoding="utf-8"))["entries"])
    stages = {"R": [r for r in records if r["id"] in seed_ids], "P": [r for r in records if r["id"] not in seed_ids]}
    batches = {stage: [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)] for stage, items in stages.items()}
    return {"records": records, "seed_ids": seed_ids, "stages": stages, "batches": batches}


def preflight(tree: Path, tree_hash: str, clf, df, plan: dict) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, observed: Any = None, expected: Any = None) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "observed": observed, "expected": expected})
        if not passed:
            raise PreflightError(f"{name}: observed {observed!r}, expected {expected!r}")

    versions = environment_versions()
    check("environment versions", versions == EXPECTED_VERSIONS, versions, EXPECTED_VERSIONS)
    stability = json.loads(STABILITY_METRICS.read_text(encoding="utf-8"))
    check("taxonomy hash equals the production input hash", sha256_file(TAXONOMY) == stability["input_hashes"]["taxonomy_data_dictionary.yaml"],
          sha256_file(TAXONOMY), stability["input_hashes"]["taxonomy_data_dictionary.yaml"])
    check("run-1 cache hash pinned in stability metrics", sha256_file(RUN1_CACHE) == stability["run1"]["cache_sha256"])
    check("run-1 metadata hash pinned in stability metrics", sha256_file(RUN1_METADATA) == stability["run1"]["metadata_sha256"])
    register_bytes = REGISTER.read_bytes()
    check("June register unchanged since before the production run",
          datetime.fromtimestamp(REGISTER.stat().st_mtime, timezone.utc) < datetime(2026, 7, 2, tzinfo=timezone.utc),
          datetime.fromtimestamp(REGISTER.stat().st_mtime, timezone.utc).isoformat(), "before 2026-07-02")
    manifest = json.loads((tree / "data/register_manifest.json").read_text(encoding="utf-8"))
    june = next(v for v in manifest["versions"] if v["version"] == "20260601")
    check("fdc13fd register manifest selects 20260601", manifest["current"] == "20260601", manifest["current"], "20260601")
    check("June register equals its manifest hash apart from line endings",
          sha256_bytes(register_bytes.replace(b"\r\n", b"\n")) == june["sha256_csv"], sha256_bytes(register_bytes.replace(b"\r\n", b"\n")), june["sha256_csv"])

    counts = {"records": len(plan["records"]), "stage_R_records": len(plan["stages"]["R"]), "stage_R_batches": len(plan["batches"]["R"]),
              "stage_P_records": len(plan["stages"]["P"]), "stage_P_batches": len(plan["batches"]["P"])}
    check("record and batch counts", counts == EXPECTED_COUNTS, counts, EXPECTED_COUNTS)
    check("all run-1 sample records present", plan["seed_ids"] <= {r["id"] for r in plan["records"]})
    run1_order = list(json.loads(RUN1_CACHE.read_text(encoding="utf-8"))["entries"])
    check("Stage R order equals run 1's cache order", [r["id"] for r in plan["stages"]["R"]] == run1_order)
    production_cache = json.loads(PRODUCTION_CACHE.read_text(encoding="utf-8"))["entries"]
    stage_p_canonical: list[str] = []
    for record in plan["stages"]["P"]:
        if record["id"] not in NOT_IN_CANONICAL and canonical(record["id"]) not in stage_p_canonical:
            stage_p_canonical.append(canonical(record["id"]))
    production_fresh_order = [key for key in production_cache if key not in plan["seed_ids"]]
    check("Stage P order equals production's cache order for non-seed records", stage_p_canonical == production_fresh_order)
    mismatched = [r["id"] for r in plan["records"] if r["id"] not in NOT_IN_CANONICAL
                  and production_cache.get(canonical(r["id"]), {}).get("fingerprint") != r["fingerprint"]]
    check("prompt fingerprints equal production's for every canonical record", not mismatched, mismatched[:10], [])
    check("collapsed record 2023/211 matches 2023/211/b",
          production_cache["2023/211"]["fingerprint"] == next(r["fingerprint"] for r in plan["records"] if r["id"] == "2023/211/b"))
    references = {"R": json.loads(RUN1_METADATA.read_text(encoding="utf-8"))["usage_log"],
                  "P": json.loads(PRODUCTION_METADATA.read_text(encoding="utf-8"))["usage_log"]}
    for stage, log in references.items():
        check(f"Stage {stage}: reference usage log has one parsed request per batch",
              len(log) == len(plan["batches"][stage]) and all(e["api_path"] == "messages.parse" and e["stop_reason"] == "end_turn" for e in log),
              len(log), len(plan["batches"][stage]))

    static_prompt = clf._build_static_prompt()
    batch_hashes = {stage: [sha256_bytes(clf._build_projects_block(batch).encode("utf-8")) for batch in batches]
                    for stage, batches in plan["batches"].items()}
    return {
        "status": "PASS", "checked_utc": datetime.now(timezone.utc).isoformat(), "specification_sha256": sha256_file(SPEC),
        "production_commit": PRODUCTION_COMMIT, "production_tree": tree_hash, "environment": versions,
        "inputs": {"register": {"path": REGISTER_RELATIVE, "sha256_on_disk": sha256_bytes(register_bytes), "manifest_sha256": june["sha256_csv"]},
                   "taxonomy_sha256": sha256_file(TAXONOMY), "run1_cache_sha256": sha256_file(RUN1_CACHE),
                   "production_cache_sha256": sha256_file(PRODUCTION_CACHE), "production_metadata_sha256": sha256_file(PRODUCTION_METADATA)},
        "request": {"api": "client.messages.parse", "model": MODEL, "max_tokens": MAX_TOKENS, "output_format": "BatchLayerResult",
                    "static_prompt_cache_control": "ephemeral", "not_sent": ["temperature", "effort", "thinking"],
                    "static_prompt_sha256": sha256_bytes(static_prompt.encode("utf-8"))},
        "counts": counts,
        "batches": {stage: [{"batch": n, "record_ids": [r["id"] for r in batch], "projects_block_sha256": batch_hashes[stage][n - 1],
                             "reference_input_tokens": references[stage][n - 1]["input_tokens"]}
                            for n, batch in enumerate(plan["batches"][stage], 1)] for stage in ("R", "P")},
        "checks": checks,
        "expected_cost_usd_at_reference_usage": {stage: round(cost(totals(log)), 4) for stage, log in references.items()},
    }


# ---------------------------------------------------------------------------- execution
def usage_entry(response: Any, api_path: str) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    entry = {"api_path": api_path, "response_id": getattr(response, "id", None), "response_model": getattr(response, "model", None),
             "stop_reason": getattr(response, "stop_reason", None)}
    for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        entry[key] = getattr(usage, key, None)
    return entry


def totals(log: list[dict[str, Any]]) -> dict[str, int]:
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return {key: int(sum(entry.get(key) or 0 for entry in log)) for key in keys}


def cost(sums: dict[str, int]) -> float:
    """Approximate USD cost. ``input_tokens`` already excludes cache reads and writes; the production
    release script subtracted them again, which understated its reported cost."""
    mtok = 1_000_000
    return (sums["input_tokens"] / mtok * PRICING["base_input_per_mtok"]
            + sums["cache_creation_input_tokens"] / mtok * PRICING["cache_write_5m_per_mtok"]
            + sums["cache_read_input_tokens"] / mtok * PRICING["cache_read_per_mtok"]
            + sums["output_tokens"] / mtok * PRICING["output_per_mtok"])


class GuardedMessages:
    """Passes only production's ``messages.parse`` request through; refuses the unstructured fallback."""

    def __init__(self, real: Any, schema: type, log: list[dict[str, Any]]):
        self._real, self._schema, self._log = real, schema, log
        # Production's classify_batch catches every exception from parse, so a violation is
        # recorded here as well as raised, and the caller stops on it.
        self.violation: str | None = None

    def parse(self, **kwargs: Any) -> Any:
        if set(kwargs) != PARSE_KWARGS or kwargs["model"] != MODEL or kwargs["max_tokens"] != MAX_TOKENS or kwargs["output_format"] is not self._schema:
            self.violation = f"request differs from production: {sorted(kwargs)}"
            raise PreflightError(self.violation)
        try:
            response = self._real.parse(**kwargs)
        except Exception as exc:
            self._log.append({"api_path": "messages.parse (error)", "error": f"{type(exc).__name__}: {exc}"})
            raise
        self._log.append(usage_entry(response, "messages.parse"))
        return response

    def create(self, **kwargs: Any) -> Any:
        self._log.append({"api_path": "messages.create (refused)"})
        raise RefusedFallback("structured-output fallback refused; the batch is retried with messages.parse")


class GuardedClient:
    def __init__(self, messages: Any):
        self.messages = messages


class NoCallClient:
    """Used when assembling outputs from a complete cache: any API call is an error."""

    class _Messages:
        def parse(self, **kwargs: Any) -> Any:
            raise RuntimeError("unexpected API call while assembling outputs")

        create = parse

    messages = _Messages()


def read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def execute(clf, plan: dict, report: dict, stage: str, run_dir: Path, max_batches: int | None) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Production authenticated with an API key; an OAuth profile would add a beta header to every request.
        raise SystemExit("ANTHROPIC_API_KEY is not set")
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger_path, cache_path = run_dir / "batch_ledger.jsonl", run_dir / "llm_layer_cache.json"
    preflight_path = run_dir / "preflight.json"
    if preflight_path.is_file():
        earlier = json.loads(preflight_path.read_text(encoding="utf-8"))
        if earlier["batches"] != report["batches"] or earlier["request"] != report["request"]:
            raise PreflightError("batch plan or request differs from the plan this run directory started with")
    else:
        preflight_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ledger = read_ledger(ledger_path)
    done = {(e["stage"], e["batch"]) for e in ledger if e["status"] == "completed"}
    if stage == "P" and any(("R", n) not in done for n in range(1, len(plan["batches"]["R"]) + 1)):
        raise SystemExit("Stage R must be complete before Stage P, as in production")
    clf.CACHE_FILE = str(cache_path)
    cache = clf.load_cache(str(cache_path))

    log: list[dict[str, Any]] = []
    guarded = GuardedMessages(clf._require_anthropic().Anthropic(api_key=api_key).messages, clf.BatchLayerResult, log)
    client = GuardedClient(guarded)
    reference = {entry["batch"]: entry["reference_input_tokens"] for entry in report["batches"][stage]}
    sent = 0
    for number, batch in enumerate(plan["batches"][stage], 1):
        if (stage, number) in done:
            continue
        if max_batches is not None and sent >= max_batches:
            break
        sent += 1
        start = len(log)
        print(f"[replicate] Stage {stage} batch {number}/{len(plan['batches'][stage])} ({len(batch)} records)")
        status, error, attempts = "failed", None, 0
        for attempt in range(1, clf.MAX_RETRIES + 1):  # production retry policy
            attempts = attempt
            try:
                results = clf.classify_batch(client, batch)
                missing = [r["id"] for r in batch if r["id"] not in results]
                if missing:
                    raise RuntimeError(f"records missing from response: {missing}")
                for record in batch:
                    results[record["id"]]["fingerprint"] = record["fingerprint"]
                cache.update(results)
                clf.save_cache(cache, str(cache_path))
                status = "completed"
                break
            except PreflightError:
                raise
            except Exception as exc:  # noqa: BLE001  (mirrors classify_all's retry loop)
                if guarded.violation:
                    raise PreflightError(guarded.violation) from exc
                error = f"{type(exc).__name__}: {exc}"
                if attempt < clf.MAX_RETRIES:
                    print(f"  [retry] attempt {attempt}/{clf.MAX_RETRIES} failed ({error}); retrying in {2 ** attempt}s")
                    time.sleep(2 ** attempt)
        responses = log[start:]
        parsed = [r for r in responses if r["api_path"] == "messages.parse"]
        final = parsed[-1] if parsed else {}
        token_match = final.get("input_tokens") == reference[number]
        entry = {"stage": stage, "batch": number, "status": status, "record_ids": [r["id"] for r in batch], "attempts": attempts,
                 "responses": responses, "reference_input_tokens": reference[number], "input_tokens_match_reference": token_match,
                 "error": error, "logged_utc": datetime.now(timezone.utc).isoformat()}
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if status != "completed":
            raise SystemExit(f"Stage {stage} batch {number} failed after {clf.MAX_RETRIES} attempts: {error}")
        if not token_match or final.get("response_model") != MODEL or final.get("stop_reason") != "end_turn":
            raise SystemExit(f"Stage {stage} batch {number} differs from the reference request: input_tokens {final.get('input_tokens')} "
                             f"vs {reference[number]}, model {final.get('response_model')}, stop {final.get('stop_reason')}. Stopping.")
        time.sleep(0.5)  # production's pause between batches
    print(f"[replicate] Stage {stage}: {sent} batch(es) sent this invocation; usage {totals(log)}; approx USD {cost(totals(log)):.4f}")


def assemble(clf, df, plan: dict, run_dir: Path) -> None:
    """Write production-format outputs and canonical labels once all 132 batches are complete."""
    ledger = read_ledger(run_dir / "batch_ledger.jsonl")
    done = {(e["stage"], e["batch"]) for e in ledger if e["status"] == "completed"}
    if len(done) != EXPECTED_COUNTS["stage_R_batches"] + EXPECTED_COUNTS["stage_P_batches"]:
        return
    clf.CACHE_FILE = str(run_dir / "llm_layer_cache.json")
    cache = clf.load_cache(clf.CACHE_FILE)
    missing = [r["id"] for r in plan["records"] if cache.get(r["id"], {}).get("fingerprint") != r["fingerprint"]]
    if missing:
        raise SystemExit(f"replicate cache incomplete or stale for {len(missing)} records: {missing[:10]}")
    df_classified = clf.classify_all(df, NoCallClient())
    clf.save_outputs(df_classified, clf.analyse_layers(df_classified), "", str(run_dir / "outputs"))
    with (run_dir / "replicate_labels_canonical.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Record ID", "run_record_id", "stage", "substantive_domains", "analytical_purpose", "cross_cutting_tags"])
        stage_of = {r["id"]: stage for stage, items in plan["stages"].items() for r in items}
        for _, row in df_classified.iterrows():
            record_id = str(row["Record ID"])
            if record_id in NOT_IN_CANONICAL:
                continue
            writer.writerow([canonical(record_id), record_id, stage_of[record_id], "; ".join(row["substantive_domains"]),
                             "; ".join(row["analytical_purpose"]), "; ".join(row["cross_cutting_tags"])])
    responses = [r for e in ledger for r in e["responses"]]
    sums = totals([r for r in responses if r["api_path"] == "messages.parse"])
    metadata = {
        "status": "exploratory, post-registration; production labels unchanged", "specification_sha256": sha256_file(SPEC),
        "completed_utc": datetime.now(timezone.utc).isoformat(), "preflight": "preflight.json", "batch_ledger": "batch_ledger.jsonl",
        "records_classified": len(plan["records"]), "canonical_records": len(plan["records"]) - len(NOT_IN_CANONICAL),
        "requests": sum(r["api_path"].startswith("messages.parse") for r in responses),
        "failed_parse_calls": sum(r["api_path"] == "messages.parse (error)" for r in responses),
        "refused_fallbacks": sum(r["api_path"] == "messages.create (refused)" for r in responses),
        "all_input_tokens_match_reference": all(e["input_tokens_match_reference"] for e in ledger if e["status"] == "completed"),
        "usage_totals": sums, "approx_cost_usd": round(cost(sums), 4), "pricing": PRICING,
        "outputs": {name: sha256_file(run_dir / name) for name in ("llm_layer_cache.json", "replicate_labels_canonical.csv")},
    }
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[replicate] complete: outputs in {run_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--execute", action="store_true", help="send requests (default: offline checks only)")
    parser.add_argument("--stage", choices=("R", "P"), help="stage to run with --execute")
    parser.add_argument("--max-batches", type=int, help="send at most this many batches in this invocation")
    parser.add_argument("--run-dir", type=Path, help="run directory to create or resume (default: new timestamped directory)")
    args = parser.parse_args()
    if args.execute and not args.stage:
        parser.error("--execute needs --stage R or --stage P")

    with tempfile.TemporaryDirectory(prefix="fable_replicate_fdc13fd_") as temporary:
        tree, scratch = Path(temporary) / "tree", Path(temporary) / "scratch"
        tree.mkdir()
        scratch.mkdir()
        tree_hash = materialise_production_code(tree)
        clf = import_production_classifier(tree, scratch)
        df = clf.load_data()
        plan = build_plan(clf, df)
        report = preflight(tree, tree_hash, clf, df, plan)
        if not args.execute:
            (HERE / "preflight.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"[preflight] PASS: {len(report['checks'])} checks; {report['counts']}; "
                  f"expected cost at reference usage {report['expected_cost_usd_at_reference_usage']}")
            return
        run_dir = (args.run_dir or HERE / f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}").resolve()
        execute(clf, plan, report, args.stage, run_dir, args.max_batches)
        assemble(clf, df, plan, run_dir)


if __name__ == "__main__":
    main()
