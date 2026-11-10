"""Compare the full-register Fable 5 replicate with the production labels (exploratory, descriptive).

Specification: SPEC_fable_production_replicate_2026-11-10.md, "Comparisons". Reads the completed
replicate run, the production labels (MOD-006), the hash-pinned run-1 and run-2 caches and the
frozen sample authorities. Aggregate tables plus a register-wide record-level diagnostic file that
carries no sample membership. No intervals and no tests.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.scratch_coder_stage_a.load import read_manifest_csv, resolve_manifest_row, semicolon_set, verify_authorities  # noqa: E402

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run_20261110"
SPEC = HERE / "SPEC_fable_production_replicate_2026-11-10.md"
PRODUCTION = ROOT / "analysis/outputs_classified_20260702_fable5/layer_classifications.csv"
STABILITY_METRICS = ROOT / "preregistration/package/03_preexisting_model_evidence/fable_run_stability_metrics.json"
RUN_CACHES = {"run 1": ROOT / "analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json",
              "run 2": ROOT / "analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json"}
COVID, EQUITY = "COVID-19 & Pandemic", "Demographic disparities / equity tag"
COMPONENTS = ("domains", "purposes", "covid", "equity")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    """As analysis/verify_fable_run_stability.py: an empty-empty pair is an error, not 1."""
    union = left | right
    if not union:
        raise ValueError("empty-empty label sets")
    return len(left & right) / len(union)


def labels(domains: frozenset[str], purposes: frozenset[str], tags: frozenset[str]) -> dict:
    return {"domains": domains, "purposes": purposes, "covid": COVID in tags, "equity": EQUITY in tags, "tags": tags}


def from_csv(path: Path, id_column: str = "Record ID") -> dict[str, dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row[id_column]: labels(semicolon_set(row["substantive_domains"]), semicolon_set(row["analytical_purpose"]),
                                       semicolon_set(row["cross_cutting_tags"])) for row in csv.DictReader(handle)}


def from_cache(path: Path) -> dict[str, dict]:
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    return {key: labels(frozenset(e["substantive_domains"]), frozenset(e["analytical_purpose"]), frozenset(e["cross_cutting_tags"]))
            for key, e in entries.items()}


def agreement(left: dict[str, dict], right: dict[str, dict], ids: list[str]) -> dict:
    n = len(ids)
    row: dict = {"records": n}
    for dimension in ("domains", "purposes"):
        exact = sum(left[i][dimension] == right[i][dimension] for i in ids)
        row[f"{dimension}_exact_n"] = exact
        row[f"{dimension}_exact_proportion"] = exact / n
        row[f"{dimension}_mean_jaccard"] = sum(jaccard(left[i][dimension], right[i][dimension]) for i in ids) / n
    for tag in ("covid", "equity"):
        row[f"{tag}_agree_n"] = sum(left[i][tag] == right[i][tag] for i in ids)
    row["both_tags_agree_n"] = sum(left[i]["covid"] == right[i]["covid"] and left[i]["equity"] == right[i]["equity"] for i in ids)
    row["all_four_agree_n"] = sum(all(left[i][c] == right[i][c] for c in COMPONENTS) for i in ids)
    row["domains_or_purposes_differ_n"] = sum(left[i]["domains"] != right[i]["domains"] or left[i]["purposes"] != right[i]["purposes"] for i in ids)
    return row


def main() -> None:
    checks: list[dict] = []

    def check(name: str, passed: bool, observed=None, expected=None) -> None:
        checks.append({"check": name, "status": "passed" if passed else "FAILED", "observed": observed, "expected": expected})
        if not passed:
            raise SystemExit(f"Check failed: {name}: observed {observed!r}, expected {expected!r}")

    for authority in verify_authorities():
        check(f"hash {authority.manifest_id}", authority.matched)
    run_metadata = json.loads((RUN_DIR / "run_metadata.json").read_text(encoding="utf-8"))
    check("replicate complete with every batch matching its reference input tokens",
          run_metadata["requests"] == 132 and run_metadata["all_input_tokens_match_reference"] and run_metadata["refused_fallbacks"] == 0,
          {k: run_metadata[k] for k in ("requests", "all_input_tokens_match_reference", "refused_fallbacks")})
    replicate_path = RUN_DIR / "replicate_labels_canonical.csv"
    check("replicate labels unchanged since the run", sha256(replicate_path.read_bytes()) == run_metadata["outputs"]["replicate_labels_canonical.csv"])
    # verify_authorities() above already checked MOD-006's hash under the project's line-ending rule.
    check("production labels are the MOD-006 authority", PRODUCTION.resolve() == (ROOT / resolve_manifest_row("MOD-006")["current_path"]).resolve())
    stability = json.loads(STABILITY_METRICS.read_text(encoding="utf-8"))
    for name, path in RUN_CACHES.items():
        key = "run1" if name == "run 1" else "run2"
        check(f"{name} cache hash pinned in stability metrics", sha256(path.read_bytes()) == stability[key]["cache_sha256"])

    production, replicate = from_csv(PRODUCTION), from_csv(replicate_path)
    run1, run2 = from_cache(RUN_CACHES["run 1"]), from_cache(RUN_CACHES["run 2"])
    check("1,308 canonical records on both sides", set(production) == set(replicate) and len(production) == 1308, len(replicate), len(production))
    seed = list(run1)
    check("production labels for the 201 seed records equal run 1's", all(production[i] == run1[i] for i in seed))
    pre = agreement(run1, run2, seed)
    reference = stability["metrics"]
    check("run 1 vs run 2 reproduces the stability metrics",
          (pre["domains_exact_n"], pre["purposes_exact_n"], pre["covid_agree_n"], pre["equity_agree_n"], pre["all_four_agree_n"]) ==
          (reference["domain_exact"]["count"], reference["purpose_exact"]["count"], reference["covid_tag_agreement"]["count"],
           reference["equity_tag_agreement"]["count"], reference["all_component_agreement"]["count"]))

    baseline = sorted(read_manifest_csv("POST-009")["record_id"])
    hard_case = sorted(read_manifest_csv("POST-011")["record_id"])
    check("sample records present in production labels", set(baseline) | set(hard_case) <= set(production), len(baseline), 150)
    seed_set = set(seed)
    populations = {
        "full register": sorted(production), "random baseline": baseline, "hard-case (diagnostic)": hard_case,
        "Stage R (run-1 sample)": seed, "Stage P (rest of register)": sorted(set(production) - seed_set),
    }
    check("population sizes", [len(v) for v in populations.values()] == [1308, 150, 75, 201, 1107], [len(v) for v in populations.values()])

    table1 = [{"table_id": "FPR1T001", "comparison": "replicate vs production", "population": name, **agreement(replicate, production, ids)}
              for name, ids in populations.items()]
    table2 = [{"table_id": "FPR1T002", "comparison": name, "population": "Stage R (run-1 sample)", **agreement(a, b, seed)}
              for name, a, b in (("run 1 (production) vs run 2", run1, run2), ("replicate vs run 1 (production)", replicate, run1),
                                 ("replicate vs run 2", replicate, run2))]
    all_three = {"table_id": "FPR1T002", "comparison": "all three runs agree", "population": "Stage R (run-1 sample)", "records": len(seed)}
    for dimension in ("domains", "purposes"):
        all_three[f"{dimension}_exact_n"] = sum(run1[i][dimension] == run2[i][dimension] == replicate[i][dimension] for i in seed)
    all_three["all_four_agree_n"] = sum(all(run1[i][c] == run2[i][c] == replicate[i][c] for c in COMPONENTS) for i in seed)
    table2.append(all_three)

    diagnostics = []
    for record_id in sorted(production):
        p, r = production[record_id], replicate[record_id]
        differing = [c for c in COMPONENTS if p[c] != r[c]]
        if differing:
            diagnostics.append({"table_id": "FPR1T003", "Record ID": record_id, "stage": "R" if record_id in seed_set else "P",
                                "differing_components": "; ".join(differing),
                                "production_domains": "; ".join(sorted(p["domains"])), "replicate_domains": "; ".join(sorted(r["domains"])),
                                "production_purposes": "; ".join(sorted(p["purposes"])), "replicate_purposes": "; ".join(sorted(r["purposes"])),
                                "production_tags": "; ".join(sorted(p["tags"])), "replicate_tags": "; ".join(sorted(r["tags"]))})

    for name, rows in (("FPR1T001.csv", table1), ("FPR1T002.csv", table2), ("FPR1T003_record_diagnostics.csv", diagnostics)):
        fields = list(dict.fromkeys(key for row in rows for key in row))
        with (HERE / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def fmt(row: dict, dimension: str) -> str:
        return f"{row[f'{dimension}_exact_n']}/{row['records']} ({row[f'{dimension}_exact_proportion']:.3f}); J {row[f'{dimension}_mean_jaccard']:.3f}"

    lines = ["# Full-register Fable 5 replicate against production (exploratory, descriptive)", "",
             "Post-registration; not preregistered. Specification: `SPEC_fable_production_replicate_2026-11-10.md`. "
             "Production labels (MOD-006) are unchanged. No intervals or tests. J = mean Jaccard.", "",
             "## FPR1T001 — Replicate against production", "",
             "| Population | Records | Research Domains exact (J) | Analytical Purposes exact (J) | COVID-19 & Pandemic | Demographic disparities / equity | Both tags | All four | Domains or purposes differ |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in table1:
        lines.append(f"| {row['population']} | {row['records']} | {fmt(row, 'domains')} | {fmt(row, 'purposes')} | {row['covid_agree_n']} | {row['equity_agree_n']} | "
                     f"{row['both_tags_agree_n']} | {row['all_four_agree_n']} | {row['domains_or_purposes_differ_n']} |")
    lines += ["", "## FPR1T002 — Three runs on the 201 run-1 sample records", "",
              "| Comparison | Research Domains exact (J) | Analytical Purposes exact (J) | All four |", "|---|---|---|---|"]
    for row in table2:
        if "domains_mean_jaccard" in row:
            lines.append(f"| {row['comparison']} | {fmt(row, 'domains')} | {fmt(row, 'purposes')} | {row['all_four_agree_n']} |")
        else:
            lines.append(f"| {row['comparison']} | {row['domains_exact_n']}/{row['records']} | {row['purposes_exact_n']}/{row['records']} | {row['all_four_agree_n']} |")
    lines += ["", f"FPR1T003: {len(diagnostics)} records differ on at least one component (register-wide; no sample membership recorded).", ""]
    (HERE / "results_fable_production_replicate.md").write_text("\n".join(lines), encoding="utf-8")
    metadata = {"status": "exploratory, post-registration, descriptive", "specification_sha256": sha256(SPEC.read_bytes()),
                "run_metadata_sha256": sha256((RUN_DIR / "run_metadata.json").read_bytes()), "completed_utc": datetime.now(timezone.utc).isoformat(),
                "checks": checks, "outputs": {name: sha256((HERE / name).read_bytes()) for name in
                                              ("FPR1T001.csv", "FPR1T002.csv", "FPR1T003_record_diagnostics.csv", "results_fable_production_replicate.md")}}
    (HERE / "compare_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
