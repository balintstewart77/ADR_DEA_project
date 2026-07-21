#!/usr/bin/env python3
"""Regenerate cross-model evidence from existing local classification outputs only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.crossmodel_comparison import ComparisonError, build_comparison, disagreement_counts


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_exclusions(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row.get("record_id", "") for row in rows]
    if len(ids) != 22 or len(ids) != len(set(ids)) or any(not item or item != item.strip() for item in ids):
        raise ComparisonError(f"Exclusion list is not 22 unique clean IDs: {path}")
    return set(ids)


def _metrics(comparison: pd.DataFrame, stratum: pd.DataFrame, exclusions: set[str]) -> dict[str, object]:
    pre = disagreement_counts(comparison, stratum)
    post_comparison = comparison.loc[~comparison["Record ID"].isin(exclusions)].copy()
    post = stratum.loc[~stratum["Record ID"].isin(exclusions)].copy()
    return {
        "comparison": {
            "n": int(len(comparison)),
            "unique_record_ids": int(comparison["Record ID"].nunique()),
            "domain_exact_count": int(comparison["domains_exact_match"].sum()),
            "domain_exact_rate": float(comparison["domains_exact_match"].mean()),
            "domain_mean_jaccard": float(comparison["domains_jaccard"].mean()),
            "purpose_exact_count": int(comparison["purposes_exact_match"].sum()),
            "purpose_exact_rate": float(comparison["purposes_exact_match"].mean()),
            "purpose_mean_jaccard": float(comparison["purposes_jaccard"].mean()),
            "covid_tag_match_count": int(comparison["covid_tag_match"].sum()),
            "disparities_tag_match_count": int(comparison["disparities_tag_match"].sum()),
            "joint_tag_match_count": int(comparison["tag_set_match"].sum()),
            "tag_mismatch_count": int((~comparison["tag_set_match"]).sum()),
            "gpt_invalid_count": int((comparison["gpt_status"] != "ok").sum()),
        },
        "pre_exclusion": pre,
        "post_exclusion": disagreement_counts(post_comparison, post),
        "post_frame": post,
    }


def _report(metrics: dict[str, object], frame_name: str) -> str:
    comp = metrics["comparison"]
    pre = metrics["pre_exclusion"]
    post = metrics["post_exclusion"]
    assert isinstance(comp, dict) and isinstance(pre, dict) and isinstance(post, dict)
    return f"""# Fable 5 / GPT-5.5 deterministic comparison verification

## Scope

This report was regenerated locally from the existing corrected Fable 5 and
GPT-5.5 classification outputs. No API or model call was made and no
classification was regenerated. Cross-cutting tags are compared as two frozen
taxonomy facets: `COVID-19 & Pandemic` and `Demographic disparities / equity tag`.
`tag_set_match` and the retained compatibility field `any_tag_set_match` both mean
that the two facets agree.

Jaccards are calculated directly from unrounded raw label sets; per-record CSV
values are stored at normal Python floating-point precision.

## Full 1,308-record population

- Domain exact agreement: {comp['domain_exact_count']}/{comp['n']} ({comp['domain_exact_rate'] * 100:.12f}%).
- Mean domain Jaccard: {comp['domain_mean_jaccard']:.15f}.
- Purpose exact agreement: {comp['purpose_exact_count']}/{comp['n']} ({comp['purpose_exact_rate'] * 100:.12f}%).
- Mean purpose Jaccard: {comp['purpose_mean_jaccard']:.15f}.
- COVID tag agreement: {comp['covid_tag_match_count']}/{comp['n']}.
- Demographic-disparities/equity tag agreement: {comp['disparities_tag_match_count']}/{comp['n']}.
- Joint two-tag agreement: {comp['joint_tag_match_count']}/{comp['n']}; {comp['tag_mismatch_count']} records differ on at least one tag.
- Invalid GPT-5.5 outputs: {comp['gpt_invalid_count']}.

## Domain/purpose disagreement frame

Before the final verified 22-record training/discussion/pilot exclusion set:

- {pre['total_disagreement']} total: {pre['domain_only']} domain-only, {pre['purpose_only']} purpose-only, and {pre['both']} both.
- {pre['tag_disagreement_alongside_domain_or_purpose']} include a tag disagreement; {pre['tag_only_outside_domain_purpose_frame']} tag-only disagreements sit outside the frame.

After exclusions, `{frame_name}` has {post['total_disagreement']} records:

- {post['domain_only']} domain-only, {post['purpose_only']} purpose-only, {post['both']} both.
- {post['tag_disagreement_alongside_domain_or_purpose']} include a tag disagreement; {post['tag_only_outside_domain_purpose_frame']} tag-only disagreements remain outside the frame.
"""


def regenerate(
    fable_path: Path, gpt_path: Path, exclusion_path: Path, comparison_path: Path,
    stratum_path: Path, evidence_dir: Path, *, check: bool = False,
) -> dict[str, object]:
    fable = pd.read_csv(fable_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    gpt = pd.read_csv(gpt_path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    exclusions = read_exclusions(exclusion_path)
    comparison, stratum = build_comparison(fable, gpt)
    metrics = _metrics(comparison, stratum, exclusions)
    post = metrics.pop("post_frame")
    assert isinstance(post, pd.DataFrame)
    frame_name = f"gpt55_disagreement_frame_{len(post)}.csv"
    values: dict[str, object] = {
        "comparison": comparison,
        "stratum": stratum,
        "post": post,
        "metrics": metrics,
        "frame_name": frame_name,
    }
    if check:
        return values
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    stratum_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    stratum.to_csv(stratum_path, index=False, encoding="utf-8-sig")
    frame_path = evidence_dir / frame_name
    post.to_csv(frame_path, index=False, encoding="utf-8-sig")
    payload = {
        "verification_status": "verified",
        "no_api_or_llm_calls_made": True,
        "classification_content_changed": False,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "inputs": {str(path.relative_to(ROOT)).replace("\\", "/"): {"sha256": sha256(path)} for path in (fable_path, gpt_path, exclusion_path)},
        "comparison": metrics["comparison"],
        "pre_exclusion": metrics["pre_exclusion"],
        "post_exclusion": metrics["post_exclusion"],
        "post_exclusion_frame": {
            "path": str(frame_path.relative_to(ROOT)).replace("\\", "/"),
            "rows": int(len(post)),
            "unique_record_ids": int(post["Record ID"].nunique()),
            "sha256": sha256(frame_path),
        },
        "exclusions": {"count": len(exclusions), "path": str(exclusion_path.relative_to(ROOT)).replace("\\", "/")},
        "calculation_method": "Exact set equality and Jaccard from parsed raw semicolon-delimited label sets; no six-decimal intermediate rounding.",
    }
    (evidence_dir / "fable5_gpt55_metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (evidence_dir / "fable5_gpt55_verification_report.md").write_text(_report(metrics, frame_name), encoding="utf-8")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline deterministic Fable/GPT comparison regeneration (no API calls).")
    parser.add_argument("--fable", type=Path, default=ROOT / "analysis/outputs_classified_20260702_fable5/layer_classifications.csv")
    parser.add_argument(
        "--gpt",
        type=Path,
        default=ROOT / "analysis/releases/gpt55_crossmodel_20260707/gpt55_classifications.csv",
    )
    parser.add_argument("--exclusions", type=Path, default=ROOT / "preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv")
    parser.add_argument("--comparison", type=Path, default=ROOT / "analysis/outputs/crossmodel_comparison.csv")
    parser.add_argument("--stratum", type=Path, default=ROOT / "analysis/outputs/crossmodel_disagreement_stratum.csv")
    parser.add_argument("--evidence-dir", type=Path, default=ROOT / "preregistration/package/03_preexisting_model_evidence")
    parser.add_argument("--check", action="store_true", help="Recompute and validate only; write no files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        values = regenerate(args.fable, args.gpt, args.exclusions, args.comparison, args.stratum, args.evidence_dir, check=args.check)
    except (ComparisonError, OSError, ValueError, pd.errors.ParserError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    metrics = values["metrics"]
    assert isinstance(metrics, dict)
    print(json.dumps({"status": "passed", "comparison": metrics["comparison"], "pre_exclusion": metrics["pre_exclusion"], "post_exclusion": metrics["post_exclusion"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
