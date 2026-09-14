"""Run every independent check and write the verification ledger.

Usage (repository root):
    .venv/bin/python -B analysis/review/remaining_validation_20260914T071731Z/reference_code/run_all.py

Writes only inside the audit directory: verification_ledger.csv and reference_results_summary.json.
Reads restricted scratch-coder inputs in memory (analytical columns only) and prints aggregates.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common as C  # noqa: E402
import integration_check  # noqa: E402
import strata_check  # noqa: E402
import wilson_check  # noqa: E402


def masking_scan(panel: dict) -> dict:
    """Confirm no record identifier, Project ID, assignment ID or formal title is written to the audit directory."""
    tokens = set(panel["cross"]["source_record_id"]) | set(panel["cross"]["assignment_id"])
    tokens |= set(panel["base"]["official_project_id"]) | set(panel["hard"]["official_project_id"])
    model = C.read_str_csv(C.MODEL, ["Record ID", "Title"])
    titles = {t for t in model.loc[model["Record ID"].isin(set(panel["cross"]["source_record_id"])), "Title"] if len(t) > 10}
    hits: Counter = Counter()
    for path in C.AUDIT_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in {".csv", ".json", ".md", ".py", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in tokens:
            if token and re.search(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", text):
                hits[path.name] += 1
        for title in titles:
            if title in text:
                hits[path.name] += 1
    return {"tokens_scanned": len(tokens), "titles_scanned": len(titles), "files_with_hits": dict(hits)}


def main() -> int:
    started = time.time()
    ledger = C.Ledger()
    panel = C.build_panel()
    summary = {"strata": strata_check.run(ledger, panel)}
    summary["wilson"] = wilson_check.run(ledger, panel)
    summary["integration"] = integration_check.run(ledger)
    ledger.write(C.AUDIT_DIR / "verification_ledger.csv")
    status = Counter(row["status"] for row in ledger.rows)
    by_family = Counter((row["family"], row["status"]) for row in ledger.rows)
    summary["ledger"] = {"rows": len(ledger.rows), "status": dict(status),
                         "by_family": {f"{k[0]}|{k[1]}": v for k, v in sorted(by_family.items())}}
    summary["discrepant_or_blocked"] = [{k: row[k] for k in ("check_id", "family", "source_identifier", "check", "saved_value", "independent_value", "status", "finding_ref", "note")}
                                        for row in ledger.rows if row["status"] in ("DISCREPANT", "BLOCKED", "NOT_CHECKED")]
    summary["runtime_seconds"] = round(time.time() - started, 1)
    (C.AUDIT_DIR / "reference_results_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n")
    summary["masking"] = masking_scan(panel)
    (C.AUDIT_DIR / "reference_results_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in ("ledger", "runtime_seconds", "masking")}, indent=2))
    for row in summary["discrepant_or_blocked"]:
        print(row["check_id"], row["status"], row["family"], row["source_identifier"][:80], "|", row["check"][:90], "|", row["saved_value"][:60], "|", row["independent_value"][:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
