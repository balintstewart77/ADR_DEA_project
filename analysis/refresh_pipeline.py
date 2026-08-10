"""One-command register refresh pipeline.

Chains the full data-refresh flow with validation gates and written reports:

1. **Fetch** the latest register (scrape/fetch_register.py). An already-recorded
   observation identity exits successfully without repository changes.
2. **Compare** the new snapshot both with the preceding ingested content hash
   and, separately, with the preceding nominal release.
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
from analysis.register_manifest import (  # noqa: E402
    CURRENT_POINTER,
    DATA_DIR,
    load_manifest,
    previous_ingested_snapshot,
    previous_nominal_release_snapshot,
    resolve_snapshot_csv,
    snapshot_record,
)
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
RAW_DIFF_CONTENT_COLUMNS = [
    "Title", "Researchers", "Legal Basis", "Datasets Used",
    "Secure Research Service", "Accreditation Date",
]


def _emit_workflow_outcome(outcome: str) -> None:
    """Expose an outcome without creating a Git-tracked status file."""
    print(f"REFRESH_OUTCOME={outcome}")
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"outcome={outcome}\n")


# ---------------------------------------------------------------------------
# Register loading and diffing
# ---------------------------------------------------------------------------

def load_cleaned_version(version: str) -> pd.DataFrame:
    raw, _source = load_raw_register(version=version)
    with tempfile.TemporaryDirectory() as tmp:
        df, _stats = clean_register_dataframe(raw, output_dir=tmp, verbose=False)
    return df


def load_raw_snapshot(snapshot_ref: str, *, data_dir: str = DATA_DIR) -> pd.DataFrame:
    path, _snapshot = resolve_snapshot_csv(data_dir, snapshot_ref)
    return pd.read_csv(path, encoding="utf-8-sig")


def load_cleaned_snapshot(snapshot_ref: str, *, data_dir: str = DATA_DIR) -> pd.DataFrame:
    raw = load_raw_snapshot(snapshot_ref, data_dir=data_dir)
    with tempfile.TemporaryDirectory() as tmp:
        cleaned, _stats = clean_register_dataframe(raw, output_dir=tmp, verbose=False)
    return cleaned


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


def build_raw_register_diff(old_df: pd.DataFrame, new_df: pd.DataFrame) -> dict:
    """Compare raw projects by Project ID while tolerating published duplicates."""
    old = old_df.assign(_project_id=old_df["Project ID"].astype(str))
    new = new_df.assign(_project_id=new_df["Project ID"].astype(str))
    old_ids, new_ids = set(old["_project_id"]), set(new["_project_id"])
    added = [{"project_id": value} for value in sorted(new_ids - old_ids)]
    removed = [{"project_id": value} for value in sorted(old_ids - new_ids)]
    changed = []
    for project_id in sorted(old_ids & new_ids):
        old_group = old.loc[old["_project_id"] == project_id]
        new_group = new.loc[new["_project_id"] == project_id]
        fields = []
        for column in RAW_DIFF_CONTENT_COLUMNS:
            if column not in old_group or column not in new_group:
                continue
            left = sorted(_normalise_duplicate_text(value) for value in old_group[column])
            right = sorted(_normalise_duplicate_text(value) for value in new_group[column])
            if left != right:
                fields.append(column)
        if fields:
            changed.append({"project_id": project_id, "fields": fields})
    return {
        "old_rows": len(old_df),
        "new_rows": len(new_df),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _snapshot_metadata(snapshot: dict) -> dict:
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "nominal_source_date": snapshot["nominal_source_date"],
        "raw_xlsx_sha256": snapshot.get("raw_xlsx_sha256"),
        "canonical_csv_sha256": snapshot["canonical_csv_sha256"],
        "source_url": snapshot.get("source_url"),
    }


def build_snapshot_comparison(
    baseline: dict,
    target: dict,
    *,
    kind: str,
    meaning: str,
    data_dir: str = DATA_DIR,
) -> dict:
    old_raw = load_raw_snapshot(baseline["snapshot_id"], data_dir=data_dir)
    new_raw = load_raw_snapshot(target["snapshot_id"], data_dir=data_dir)
    old_clean = load_cleaned_snapshot(baseline["snapshot_id"], data_dir=data_dir)
    new_clean = load_cleaned_snapshot(target["snapshot_id"], data_dir=data_dir)
    raw_diff = build_raw_register_diff(old_raw, new_raw)
    cleaned_diff = build_register_diff(old_clean, new_clean)
    analytical_impact = "none" if not any(
        cleaned_diff[key] for key in ("added", "removed", "changed")
    ) else "changed"
    return {
        "kind": kind,
        "meaning": meaning,
        "baseline": _snapshot_metadata(baseline),
        "target": _snapshot_metadata(target),
        "raw_diff": raw_diff,
        "cleaned_diff": cleaned_diff,
        "analytical_impact": analytical_impact,
    }


def build_ingest_revision_comparison(
    manifest: dict,
    target_ref: str = CURRENT_POINTER,
    *,
    data_dir: str = DATA_DIR,
    unchanged_observation: bool = False,
) -> dict | None:
    target = snapshot_record(manifest, target_ref)
    baseline = target if unchanged_observation else previous_ingested_snapshot(manifest, target_ref)
    if baseline is None:
        return None
    meaning = (
        "Repeated observation of already-ingested content; no new snapshot."
        if unchanged_observation else
        "Newly observed content snapshot versus the immediately preceding distinct ingested snapshot, regardless of nominal source date."
    )
    return build_snapshot_comparison(
        baseline, target, kind="ingest_revision", meaning=meaning, data_dir=data_dir
    )


def build_nominal_release_comparison(
    manifest: dict,
    target_ref: str = CURRENT_POINTER,
    *,
    data_dir: str = DATA_DIR,
) -> dict | None:
    target = snapshot_record(manifest, target_ref)
    baseline = previous_nominal_release_snapshot(manifest, target_ref)
    if baseline is None:
        return None
    return build_snapshot_comparison(
        baseline,
        target,
        kind="nominal_release",
        meaning=(
            "Latest revision for the current nominal source date versus the latest "
            "revision for the preceding nominal source date; this is release history, "
            "not the change detected at the latest observation."
        ),
        data_dir=data_dir,
    )


def comparison_markdown(comparison: dict, title: str) -> str:
    raw, cleaned = comparison["raw_diff"], comparison["cleaned_diff"]
    baseline, target = comparison["baseline"], comparison["target"]
    lines = [
        f"# {title}", "", comparison["meaning"], "",
        f"- Baseline snapshot: `{baseline['snapshot_id']}`",
        f"- Baseline nominal source date: {baseline['nominal_source_date']}",
        f"- Baseline canonical CSV SHA-256: `{baseline['canonical_csv_sha256']}`",
        f"- Target snapshot: `{target['snapshot_id']}`",
        f"- Target nominal source date: {target['nominal_source_date']}",
        f"- Target canonical CSV SHA-256: `{target['canonical_csv_sha256']}`",
        f"- Raw projects added / removed / changed: {len(raw['added'])} / {len(raw['removed'])} / {len(raw['changed'])}",
        f"- Cleaned projects added / removed / changed: {len(cleaned['added'])} / {len(cleaned['removed'])} / {len(cleaned['changed'])}",
        f"- Analytical impact: {comparison['analytical_impact']}", "",
    ]
    if raw["changed"]:
        lines += ["## Raw content changes", ""] + [
            f"- `{item['project_id']}` ({', '.join(item['fields'])})"
            for item in raw["changed"]
        ] + [""]
    if cleaned["changed"]:
        lines += ["## Cleaned content changes", ""] + [
            f"- `{item['record_id']}` ({', '.join(item['fields'])})"
            for item in cleaned["changed"]
        ] + [""]
    return "\n".join(lines)


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
                        help="Re-run downstream steps with --skip-fetch; exact fetch retries remain no-ops")
    parser.add_argument("--classify", action="store_true",
                        help="Run incremental LLM classification (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--model", default=None, help="Model for the classification step")
    parser.add_argument("--baseline-version", default=None,
                        help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.baseline_version:
        parser.error(
            "--baseline-version encoded ambiguous nominal-date semantics and has been "
            "retired; inspect the separately generated ingest-revision and nominal-release reports"
        )

    manifest = load_manifest()
    if manifest is None:
        print("No data manifest found; run scrape/fetch_register.py first")
        return 2
    pre_snapshot = snapshot_record(manifest, CURRENT_POINTER)

    if args.skip_fetch:
        target_snapshot_id = pre_snapshot["snapshot_id"]
        fetch_status = "skipped"
        unchanged_observation = True
    else:
        from fetch_register import run_fetch
        result = run_fetch()
        fetch_status = result["status"]
        if fetch_status == "invalid":
            _emit_workflow_outcome("invalid")
            return 2
        fetch_outcome = result["outcome"]
        if fetch_outcome == "unchanged_noop":
            print(
                "Observed identity is already recorded; successful no-op. No manifest, "
                "snapshot, pointer or analytical report was changed."
            )
            _emit_workflow_outcome(fetch_outcome)
            return 0
        target_snapshot_id = result["snapshot_id"]
        unchanged_observation = fetch_outcome == "new_provenance_observation"

    manifest = load_manifest()
    assert manifest is not None
    target_snapshot = snapshot_record(manifest, target_snapshot_id)
    nominal_version = target_snapshot["nominal_source_date"].replace("-", "")
    report_key = f"{nominal_version}-{target_snapshot['raw_xlsx_sha256'][:12]}"
    report_dir = REFRESH_DIR / report_key
    report_dir.mkdir(parents=True, exist_ok=True)

    ingest_comparison = build_ingest_revision_comparison(
        manifest,
        target_snapshot_id,
        unchanged_observation=unchanged_observation,
    )
    nominal_comparison = build_nominal_release_comparison(manifest, target_snapshot_id)
    if ingest_comparison:
        (report_dir / "ingest_revision_diff.md").write_text(
            comparison_markdown(ingest_comparison, "Ingest/revision comparison"),
            encoding="utf-8",
        )
    if nominal_comparison:
        (report_dir / "nominal_release_diff.md").write_text(
            comparison_markdown(nominal_comparison, "Nominal-release comparison"),
            encoding="utf-8",
        )

    summary: list[str] = [
        f"# Register refresh: snapshot {target_snapshot['raw_xlsx_sha256'][:12]}",
        "",
        f"- Run at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Fetch status: {fetch_status}",
        f"- Nominal source date: {target_snapshot['nominal_source_date']}",
        f"- Raw XLSX SHA-256: `{target_snapshot['raw_xlsx_sha256']}`",
        f"- Canonical CSV SHA-256: `{target_snapshot['canonical_csv_sha256']}`",
        "",
    ]

    new_register = load_cleaned_snapshot(target_snapshot_id)
    summary.append(f"- Cleaned register rows: {len(new_register):,}")
    if ingest_comparison:
        raw_diff = ingest_comparison["raw_diff"]
        cleaned_diff = ingest_comparison["cleaned_diff"]
        summary += [
            "",
            "## Ingest/revision comparison",
            "",
            ingest_comparison["meaning"],
            f"- Raw added / removed / changed: {len(raw_diff['added'])} / {len(raw_diff['removed'])} / {len(raw_diff['changed'])}",
            f"- Cleaned added / removed / changed: {len(cleaned_diff['added'])} / {len(cleaned_diff['removed'])} / {len(cleaned_diff['changed'])}",
            f"- Analytical impact: {ingest_comparison['analytical_impact']}",
            "- Report: ingest_revision_diff.md",
        ]
    if nominal_comparison:
        raw_diff = nominal_comparison["raw_diff"]
        cleaned_diff = nominal_comparison["cleaned_diff"]
        summary += [
            "",
            "## Nominal-release comparison",
            "",
            nominal_comparison["meaning"],
            f"- Raw added / removed / changed: {len(raw_diff['added'])} / {len(raw_diff['removed'])} / {len(raw_diff['changed'])}",
            f"- Cleaned added / removed / changed: {len(cleaned_diff['added'])} / {len(cleaned_diff['removed'])} / {len(cleaned_diff['changed'])}",
            "- Report: nominal_release_diff.md",
        ]

    analytical_changed = bool(
        ingest_comparison and ingest_comparison["analytical_impact"] != "none"
    )
    if analytical_changed or args.force:
        print("[derive] regenerating deterministic facets...")
        _properties, coverage = derive_run(
            report_path=(report_dir / "derive_report.md").resolve()
        )
        (report_dir / "review_required.md").write_text(
            review_required_markdown(coverage, known_unclassifiable_organisations()),
            encoding="utf-8",
        )
        summary += [
            f"- Dataset coverage: {coverage['dataset_mentions_matched']:,}/{coverage['dataset_mentions_total']:,}",
            f"- Organisation coverage: {coverage['organisation_mentions_matched']:,}/{coverage['organisation_mentions_total']:,}",
            "- Curation queue: review_required.md",
        ]
    else:
        summary.append(
            "- Deterministic facets: unchanged cleaned state; existing output retained"
        )

    classifications_csv = None
    if args.classify and analytical_changed:
        classification_dir = classify_step(report_key, model=args.model)
        classifications_csv = classification_dir / "layer_classifications.csv"
        summary.append(f"- Classification run: {classification_dir.name}")
    elif args.classify:
        summary.append("- Classification: not run because the cleaned analytical state is unchanged")
    else:
        summary.append("- Classification: skipped; classification pointer unchanged")

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
        _emit_workflow_outcome("gate_failure")
        return 2

    if args.classify and classifications_csv is not None and analytical_changed:
        update_classification_pointer(classifications_csv.parent)
        summary.append("- Dashboard pointer updated to the new classification run")

    summary += ["", "All validation gates passed."]
    summary_text = "\n".join(summary) + "\n"
    (report_dir / "refresh_summary.md").write_text(summary_text, encoding="utf-8")
    (report_dir / "manifest.json").write_text(
        json.dumps({
            "schema_version": 2,
            "snapshot": _snapshot_metadata(target_snapshot),
            "ingest_revision_comparison": ingest_comparison,
            "nominal_release_comparison": nominal_comparison,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    REFRESH_DIR.mkdir(parents=True, exist_ok=True)
    (REFRESH_DIR / "latest_summary.md").write_text(summary_text, encoding="utf-8")
    print(summary_text)
    print(f"Reports written to {report_dir}")
    _emit_workflow_outcome(
        "reprocessed" if args.skip_fetch else fetch_outcome
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
