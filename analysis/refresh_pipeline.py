"""One-command register refresh pipeline.

Chains the full data-refresh flow with validation gates and written reports:

1. **Fetch** the latest register (scrape/fetch_register.py). Exits cleanly
   when the published register has not changed (override with --force).
2. **Diff** the cleaned new register against the previous version: new,
   removed, and content-changed projects.
3. **Derive** the deterministic facets (register_properties.csv) and write a
   review-required report listing unmatched datasets/organisations that need
   register_reference.yaml or alias curation.
4. **Classify** (only with --classify and ANTHROPIC_API_KEY set): seeds a
   fingerprinted cache from the currently published classification run, runs
   the incremental LLM classifier into analysis/outputs_classified_<version>/,
   and on success points data/release_pointers.json at the new run.
5. **Gate**: every cleaned Record ID must have a deterministic-properties row
   (and a classification row when --classify ran) before the pipeline reports
   success.

Reports land in analysis/outputs_refresh/<version>/ (tracked in git so the
scheduled CI run can include them in its pull request), plus a stable copy at
analysis/outputs_refresh/latest_summary.md.

Usage:
    python -m analysis.refresh_pipeline                 # fetch, diff, derive, gate
    python -m analysis.refresh_pipeline --classify      # + LLM classification
    python -m analysis.refresh_pipeline --skip-fetch --force   # re-run on current data
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
_SCRAPE_DIR = PROJECT_ROOT / "scrape"
if str(_SCRAPE_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRAPE_DIR))

from analysis.register_cleaning import (  # noqa: E402
    _normalise_duplicate_text,
    clean_register_dataframe,
    load_raw_register,
)
from analysis.register_manifest import load_manifest  # noqa: E402
from analysis.derive_register_properties import (  # noqa: E402
    REFERENCE_PATH,
    load_reference,
    run as derive_run,
)
from analysis.rebuild_llm_cache import build_cache_entries, write_cache  # noqa: E402

ANALYSIS_DIR = PROJECT_ROOT / "analysis"
REFRESH_DIR = ANALYSIS_DIR / "outputs_refresh"
RELEASE_POINTERS_PATH = PROJECT_ROOT / "data" / "release_pointers.json"

DIFF_CONTENT_COLUMNS = ["Title", "Datasets Used", "Researchers", "Secure Research Service"]


# ---------------------------------------------------------------------------
# Register loading and diffing
# ---------------------------------------------------------------------------

def load_cleaned_version(version: str) -> pd.DataFrame:
    raw, _source = load_raw_register(version=version)
    with tempfile.TemporaryDirectory() as tmp:
        df, _stats = clean_register_dataframe(raw, output_dir=tmp, verbose=False)
    return df


def build_register_diff(old_df: pd.DataFrame, new_df: pd.DataFrame) -> dict:
    """Compare two cleaned registers by Record ID."""
    old = old_df.set_index(old_df["Record ID"].astype(str))
    new = new_df.set_index(new_df["Record ID"].astype(str))
    old_ids, new_ids = set(old.index), set(new.index)

    added = [
        {"record_id": rid, "title": str(new.loc[rid, "Title"])}
        for rid in sorted(new_ids - old_ids)
    ]
    removed = [
        {"record_id": rid, "title": str(old.loc[rid, "Title"])}
        for rid in sorted(old_ids - new_ids)
    ]
    changed = []
    for rid in sorted(old_ids & new_ids):
        fields = [
            col for col in DIFF_CONTENT_COLUMNS
            if col in old.columns and col in new.columns
            and _normalise_duplicate_text(old.loc[rid, col])
            != _normalise_duplicate_text(new.loc[rid, col])
        ]
        if fields:
            changed.append({
                "record_id": rid,
                "title": str(new.loc[rid, "Title"]),
                "fields": fields,
            })
    return {
        "old_rows": len(old_df),
        "new_rows": len(new_df),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def diff_markdown(diff: dict, old_version: str, new_version: str) -> str:
    lines = [
        f"# Register diff: {old_version} -> {new_version}",
        "",
        f"- Cleaned rows: {diff['old_rows']:,} -> {diff['new_rows']:,}",
        f"- New projects: {len(diff['added'])}",
        f"- Removed projects: {len(diff['removed'])}",
        f"- Content-changed projects: {len(diff['changed'])}",
        "",
    ]
    if diff["added"]:
        lines += ["## New projects", ""]
        lines += [f"- `{e['record_id']}` {e['title']}" for e in diff["added"]] + [""]
    if diff["removed"]:
        lines += ["## Removed projects", ""]
        lines += [f"- `{e['record_id']}` {e['title']}" for e in diff["removed"]] + [""]
    if diff["changed"]:
        lines += ["## Content-changed projects", ""]
        lines += [
            f"- `{e['record_id']}` ({', '.join(e['fields'])}) {e['title']}"
            for e in diff["changed"]
        ] + [""]
    return "\n".join(lines)


def known_unclassifiable_organisations() -> set[str]:
    """Adjudicated honest residuals from the reference (see the YAML comment)."""
    reference = load_reference(REFERENCE_PATH)
    return set(reference.get("known_unclassifiable_organisations") or [])


def review_required_markdown(coverage: dict, known_unclassifiable: set[str] | None = None) -> str:
    """Curation queue: unmatched datasets/organisations from the derive run.

    Strings in known_unclassifiable (adjudicated honest residuals, e.g. person
    names with no institution) are excluded from the action list and reported
    as a count, so the queue only surfaces genuinely-new unknowns.
    """
    known_unclassifiable = known_unclassifiable or set()
    lines = ["# Review required: reference-layer coverage gaps", ""]
    dataset_unmatched = coverage.get("dataset_unmatched_counts") or {}
    org_unmatched = coverage.get("organisation_unmatched_counts") or {}
    known_residuals = {
        name: count for name, count in org_unmatched.items()
        if name in known_unclassifiable
    }
    org_unmatched = {
        name: count for name, count in org_unmatched.items()
        if name not in known_unclassifiable
    }
    lines += [
        f"- Dataset mentions matched: {coverage['dataset_mentions_matched']:,}"
        f"/{coverage['dataset_mentions_total']:,}",
        f"- Organisation mentions matched: {coverage['organisation_mentions_matched']:,}"
        f"/{coverage['organisation_mentions_total']:,}",
        f"- Known residuals (adjudicated unclassifiable, no action): {len(known_residuals)}",
        "",
        "## Unmatched organisations (add to register_reference.yaml or alias maps)",
        "",
    ]
    if org_unmatched:
        for name, count in sorted(org_unmatched.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {name} ({count} mention{'s' if count != 1 else ''})")
    else:
        lines.append("- (none)")
    lines += ["", "## Unmatched datasets (top 30 by mentions)", ""]
    if dataset_unmatched:
        top = sorted(dataset_unmatched.items(), key=lambda kv: -kv[1])[:30]
        for name, count in top:
            lines.append(f"- {name} ({count} mention{'s' if count != 1 else ''})")
        if len(dataset_unmatched) > 30:
            lines.append(f"- ... and {len(dataset_unmatched) - 30} more")
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation gates
# ---------------------------------------------------------------------------

def run_gates(
    register_df: pd.DataFrame,
    properties_csv: Path,
    classifications_csv: Path | None = None,
) -> list[str]:
    problems: list[str] = []
    register_ids = set(register_df["Record ID"].astype(str))

    properties = pd.read_csv(properties_csv, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    property_ids = set(properties["Record ID"].astype(str))
    if property_ids != register_ids:
        missing = sorted(register_ids - property_ids)[:5]
        extra = sorted(property_ids - register_ids)[:5]
        problems.append(
            f"register_properties Record IDs do not match the register "
            f"(missing e.g. {missing}, extra e.g. {extra})"
        )

    if classifications_csv is not None:
        classifications = pd.read_csv(
            classifications_csv, encoding="utf-8-sig", dtype=str, keep_default_na=False
        )
        classified_ids = set(classifications["Record ID"].astype(str))
        if classified_ids != register_ids:
            missing = sorted(register_ids - classified_ids)[:5]
            problems.append(
                f"layer_classifications is missing {len(register_ids - classified_ids)} "
                f"register Record IDs (e.g. {missing})"
            )
    return problems


# ---------------------------------------------------------------------------
# Classification step
# ---------------------------------------------------------------------------

def _current_classification_dir() -> Path:
    with open(RELEASE_POINTERS_PATH, "r", encoding="utf-8") as f:
        pointers = json.load(f)
    return PROJECT_ROOT / Path(*pointers["classification_dir"].split("/"))


def classify_step(version: str, *, model: str | None) -> Path:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("--classify requires ANTHROPIC_API_KEY to be set")

    output_dir = ANALYSIS_DIR / f"outputs_classified_{version}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Seed the fingerprinted cache from the currently published run so only
    # new/changed projects are sent to the API.
    seed_csv = _current_classification_dir() / "layer_classifications.csv"
    seed_kwargs = {}
    if model:
        seed_kwargs["model"] = model
    if seed_csv.exists():
        from analysis.llm_theme_analysis_v3 import MODEL, PROMPT_VERSION
        entries = build_cache_entries(pd.read_csv(seed_csv, encoding="utf-8-sig"))
        write_cache(
            entries,
            str(output_dir / "llm_layer_cache.json"),
            model=model or MODEL,
            prompt_version=PROMPT_VERSION,
        )
        print(f"[classify] seeded cache with {len(entries):,} entries from {seed_csv}")
    else:
        print(f"[classify] no previous classifications at {seed_csv}; full run")

    command = [
        sys.executable,
        str(ANALYSIS_DIR / "llm_theme_analysis_v3.py"),
        "--output-dir", str(output_dir),
        "--skip-narrative",
    ]
    if model:
        command += ["--model", model]
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)
    return output_dir


def update_classification_pointer(classification_dir: Path) -> None:
    with open(RELEASE_POINTERS_PATH, "r", encoding="utf-8") as f:
        pointers = json.load(f)
    pointers["classification_dir"] = classification_dir.relative_to(PROJECT_ROOT).as_posix()
    with open(RELEASE_POINTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(pointers, f, indent=2)
        f.write("\n")
    print(f"[pointers] dashboard classification_dir -> {pointers['classification_dir']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Run the register refresh pipeline")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Use the manifest's current version without fetching")
    parser.add_argument("--force", action="store_true",
                        help="Run the remaining steps even when the register is unchanged")
    parser.add_argument("--classify", action="store_true",
                        help="Run incremental LLM classification (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--model", default=None, help="Model for the classification step")
    parser.add_argument("--baseline-version", default=None,
                        help="Diff against this version (default: previous current)")
    args = parser.parse_args()

    manifest = load_manifest()
    if manifest is None:
        print("No data manifest found; run scrape/fetch_register.py first")
        return 2
    pre_version = manifest["current"]

    if args.skip_fetch:
        new_version = pre_version
        fetch_status = "skipped"
    else:
        from fetch_register import run_fetch
        result = run_fetch()
        fetch_status = result["status"]
        if fetch_status == "invalid":
            return 2
        if fetch_status == "no-change" and not args.force:
            print("Register unchanged; nothing to do (use --force to re-run steps).")
            return 0
        new_version = result["version"] or pre_version

    baseline = args.baseline_version
    if baseline is None and pre_version != new_version:
        baseline = pre_version
    if baseline is None:
        numbered = sorted(
            r["version"] for r in manifest["versions"]
            if r["version"] != new_version and r["version"].isdigit()
        )
        baseline = numbered[-1] if numbered else None

    report_dir = REFRESH_DIR / new_version
    report_dir.mkdir(parents=True, exist_ok=True)
    summary: list[str] = [
        f"# Register refresh: version {new_version}",
        "",
        f"- Run at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Fetch status: {fetch_status}",
        f"- Baseline version: {baseline or '(none)'}",
        "",
    ]

    new_register = load_cleaned_version(new_version)
    summary.append(f"- Cleaned register rows: {len(new_register):,}")

    if baseline:
        old_register = load_cleaned_version(baseline)
        diff = build_register_diff(old_register, new_register)
        (report_dir / "register_diff.md").write_text(
            diff_markdown(diff, baseline, new_version), encoding="utf-8"
        )
        summary += [
            f"- New projects: {len(diff['added'])}",
            f"- Removed projects: {len(diff['removed'])}",
            f"- Content-changed projects: {len(diff['changed'])}",
            "- Diff report: register_diff.md",
        ]

    print("[derive] regenerating deterministic facets...")
    _properties, coverage = derive_run(
        report_path=(report_dir / "derive_report.md").resolve()
    )
    (report_dir / "review_required.md").write_text(
        review_required_markdown(coverage, known_unclassifiable_organisations()),
        encoding="utf-8",
    )
    summary += [
        f"- Dataset coverage: {coverage['dataset_mentions_matched']:,}"
        f"/{coverage['dataset_mentions_total']:,}",
        f"- Organisation coverage: {coverage['organisation_mentions_matched']:,}"
        f"/{coverage['organisation_mentions_total']:,}",
        "- Curation queue: review_required.md",
    ]

    classifications_csv = None
    if args.classify:
        classification_dir = classify_step(new_version, model=args.model)
        classifications_csv = classification_dir / "layer_classifications.csv"
        summary.append(f"- Classification run: {classification_dir.name}")
    else:
        summary.append(
            "- Classification: skipped (run with --classify to update the "
            "enriched/thematic views for new projects)"
        )

    properties_csv = (
        PROJECT_ROOT / "analysis" / "outputs_deterministic_rc2" / "register_properties.csv"
    )
    problems = run_gates(new_register, properties_csv, classifications_csv)
    if problems:
        summary += ["", "## GATE FAILURES", ""] + [f"- {p}" for p in problems]
        (report_dir / "refresh_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
        for problem in problems:
            print(f"[gate] {problem}")
        print(f"Reports written to {report_dir} - NOT publishing.")
        return 2

    if args.classify and classifications_csv is not None:
        update_classification_pointer(classifications_csv.parent)
        summary.append("- Dashboard pointer updated to the new classification run")

    summary += ["", "All validation gates passed."]
    summary_text = "\n".join(summary) + "\n"
    (report_dir / "refresh_summary.md").write_text(summary_text, encoding="utf-8")
    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    (REFRESH_DIR / "latest_summary.md").write_text(summary_text, encoding="utf-8")
    print(summary_text)
    print(f"Reports written to {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
