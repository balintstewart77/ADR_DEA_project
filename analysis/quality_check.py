"""
Quality Check for Three-Layer LLM Classifications
===================================================
Diagnostic metrics, suspicious-classification flagging, stratified sampling
for human review, and post-review agreement reporting.

No LLM calls are made — this script reads existing outputs only.

Usage:
    python analysis/quality_check.py                 # diagnostics + flags + review sample
    python analysis/quality_check.py --agreement review_completed.csv   # after human review
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
from collections import Counter

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ANALYSIS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(ANALYSIS_DIR, "outputs_v3")
QUALITY_DIR = os.path.join(OUTPUT_DIR, "quality")
CLASSIFICATIONS_CSV = os.path.join(OUTPUT_DIR, "layer_classifications.csv")
PROJECT_ROOT = os.path.dirname(ANALYSIS_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.dataset_normalisation import _clean_datasets_text  # noqa: E402

# ---------------------------------------------------------------------------
# Dataset-field helpers (lightweight — just counts providers/datasets)
# ---------------------------------------------------------------------------


def count_providers_and_datasets(raw: str) -> tuple[int, int, set[str]]:
    """Return (n_providers, n_datasets, provider_names) from a 'Datasets Used' string."""
    if not isinstance(raw, str) or not raw.strip():
        return 0, 0, set()
    cleaned = _clean_datasets_text(raw)
    providers: set[str] = set()
    n_datasets = 0
    for line in cleaned.split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            provider, rest = line.split(":", 1)
            provider = provider.strip()
            providers.add(provider)
            parts = [p.strip(" ,;") for p in re.split(r"\s*,\s*|\s+&\s+", rest) if p.strip(" ,;")]
            n_datasets += len(parts) if parts else 1
        else:
            parts = [p.strip(" ,;") for p in re.split(r"\s*,\s*|\s+&\s+", line) if p.strip(" ,;")]
            n_datasets += len(parts) if parts else 1
    return len(providers), n_datasets, providers


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_classifications() -> pd.DataFrame:
    """Load the main classification CSV and parse list columns."""
    df = pd.read_csv(CLASSIFICATIONS_CSV, encoding="utf-8-sig")

    # Parse semicolon-separated list columns back into lists
    for col in ("substantive_domains", "analytical_purpose", "cross_cutting_tags"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(
            lambda x: [s.strip() for s in str(x).split(";") if s.strip()] if pd.notna(x) else []
        )

    # Add dataset counts
    dataset_info = df["Datasets Used"].apply(count_providers_and_datasets)
    df["n_providers"] = dataset_info.apply(lambda x: x[0])
    df["n_datasets"] = dataset_info.apply(lambda x: x[1])
    df["provider_names"] = dataset_info.apply(lambda x: x[2])

    return df


# ---------------------------------------------------------------------------
# Diagnostic metrics
# ---------------------------------------------------------------------------

def compute_diagnostic_metrics(df: pd.DataFrame) -> str:
    """Compute and format diagnostic statistics as a readable report."""
    n = len(df)
    lines = [
        f"Classification Quality Diagnostics ({n:,} projects)",
        "=" * 60,
        "",
    ]

    # --- Layer A: domain distribution ---
    lines.append(f"LAYER A — SUBSTANTIVE DOMAINS")
    n_domains = df["substantive_domains"].apply(len)
    lines.append(f"  Domain count distribution:")
    for k in sorted(n_domains.unique()):
        cnt = (n_domains == k).sum()
        lines.append(f"    {k} domain(s): {cnt:,} projects ({cnt/n*100:.1f}%)")

    # "Unclear from Title" usage
    n_unclear = df["substantive_domains"].apply(lambda x: "Unclear from Title" in x).sum()
    lines.append(f"  Projects using 'Unclear from Title' domain: {n_unclear:,} ({n_unclear/n*100:.1f}%)")

    # --- Layer C: purpose distribution ---
    lines.append(f"\nLAYER C — ANALYTICAL PURPOSE")
    n_purposes = df["analytical_purpose"].apply(len)
    lines.append(f"  Purpose count distribution:")
    for k in sorted(n_purposes.unique()):
        cnt = (n_purposes == k).sum()
        lines.append(f"    {k} purpose(s): {cnt:,} projects ({cnt/n*100:.1f}%)")

    c_unclear = df["analytical_purpose"].apply(lambda x: "Unclear from Title" in x).sum()
    lines.append(f"  Projects with 'Unclear from Title' purpose: {c_unclear:,} ({c_unclear/n*100:.1f}%)")

    # --- Domain-purpose coupling ---
    lines.append(f"\nDOMAIN-PURPOSE COUPLING")
    lines.append(f"  Checking whether certain domains always get the same purpose:")
    for domain in df["primary_domain"].value_counts().head(8).index:
        subset = df[df["primary_domain"] == domain]
        purposes = subset["analytical_purpose"].explode()
        top_purpose = purposes.value_counts().index[0]
        top_pct = purposes.value_counts().iloc[0] / len(purposes) * 100
        flag = " ⚠ HIGH COUPLING" if top_pct > 50 else ""
        lines.append(f"  {domain}:")
        lines.append(f"    Most common purpose: {top_purpose} ({top_pct:.0f}%){flag}")

    # --- Title length stats ---
    lines.append(f"\nTITLE LENGTH")
    title_len = df["Title"].str.len()
    lines.append(f"  Median: {title_len.median():.0f} chars")
    lines.append(f"  Under 30 chars: {(title_len < 30).sum()} projects")
    lines.append(f"  Under 15 chars: {(title_len < 15).sum()} projects")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Suspicious classification flagging
# ---------------------------------------------------------------------------

FLAG_REASONS = {
    "short_title": "Title under 30 characters — may be an acronym or jargon",
    "domain_overreach": "4+ substantive domains assigned",
    "gender_inequality_tautology": "Gender/Race domain with Inequality purpose (potential tautological coupling)",
}


def flag_suspicious_classifications(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of flagged projects with reason codes."""
    flags = []

    for idx, row in df.iterrows():
        reasons = []

        # Short title
        if isinstance(row["Title"], str) and len(row["Title"]) < 30:
            reasons.append("short_title")

        # Domain overreach
        if isinstance(row["substantive_domains"], list) and len(row["substantive_domains"]) >= 4:
            reasons.append("domain_overreach")

        # Gender/Race → Inequality tautology
        if (row["primary_domain"] == "Gender, Race & Ethnicity"
                and isinstance(row["analytical_purpose"], list)
                and "Inequality / Disparities Analysis" in row["analytical_purpose"]):
            reasons.append("gender_inequality_tautology")

        if reasons:
            flags.append({
                "Project ID": row["Project ID"],
                "Record ID": row.get("Record ID", row["Project ID"]),
                "Title": row["Title"],
                "n_providers": row["n_providers"],
                "n_datasets": row["n_datasets"],
                "primary_domain": row["primary_domain"],
                "analytical_purpose": "; ".join(row["analytical_purpose"]) if isinstance(row["analytical_purpose"], list) else row["analytical_purpose"],
                "substantive_domains": "; ".join(row["substantive_domains"]) if isinstance(row["substantive_domains"], list) else row["substantive_domains"],
                "flag_reasons": "; ".join(reasons),
                "n_flags": len(reasons),
            })

    df_flags = pd.DataFrame(flags)
    if not df_flags.empty:
        df_flags = df_flags.sort_values("n_flags", ascending=False).reset_index(drop=True)
    return df_flags


def summarise_flags(df_flags: pd.DataFrame) -> str:
    """Produce a readable summary of flagged classifications."""
    if df_flags.empty:
        return "No suspicious classifications found."

    lines = [
        f"Suspicious Classifications: {len(df_flags):,} projects flagged",
        "=" * 60,
        "",
    ]

    # Count by reason
    all_reasons = []
    for reasons_str in df_flags["flag_reasons"]:
        all_reasons.extend(reasons_str.split("; "))
    reason_counts = Counter(all_reasons)

    lines.append("Flag counts by reason:")
    for reason, count in reason_counts.most_common():
        desc = FLAG_REASONS.get(reason, reason)
        lines.append(f"  {count:>4}  {desc}")

    lines.append(f"\nProjects with multiple flags: {(df_flags['n_flags'] > 1).sum()}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stratified sampling for human review
# ---------------------------------------------------------------------------

def sample_for_human_review(
    df: pd.DataFrame,
    df_flags: pd.DataFrame,
    n: int = 60,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Stratified random sample for human review.
    Prioritises flagged projects, then fills from each primary-domain cell.
    """
    rng = np.random.default_rng(seed)

    # Start with flagged projects (up to half the sample)
    max_flagged = n // 2
    if not df_flags.empty:
        flagged_ids = set(df_flags["Record ID"].head(max_flagged))
    else:
        flagged_ids = set()

    # Stratify the rest across primary-domain cells.
    remaining_n = n - len(flagged_ids)
    cells = df.groupby("primary_domain")
    cell_sizes = cells.size()
    n_cells = len(cell_sizes)

    # Allocate proportionally, minimum 1 per cell
    per_cell = max(1, remaining_n // n_cells)
    sampled_ids = set(flagged_ids)

    for domain, group in cells:
        available = group[~group["Record ID"].isin(sampled_ids)]
        if available.empty:
            continue
        take = min(per_cell, len(available))
        chosen = available.sample(n=take, random_state=rng.integers(0, 2**31))
        sampled_ids.update(chosen["Record ID"])

    # If still under target, fill randomly
    if len(sampled_ids) < n:
        remaining = df[~df["Record ID"].isin(sampled_ids)]
        extra = min(n - len(sampled_ids), len(remaining))
        if extra > 0:
            chosen = remaining.sample(n=extra, random_state=rng.integers(0, 2**31))
            sampled_ids.update(chosen["Record ID"])

    # Build the review DataFrame
    sample_df = df[df["Record ID"].isin(sampled_ids)].copy()

    # Mark which are flagged
    sample_df["is_flagged"] = sample_df["Record ID"].isin(flagged_ids)

    # Format for review
    review = sample_df[[
        "Project ID", "Record ID", "Title", "Datasets Used",
        "substantive_domains", "analytical_purpose", "cross_cutting_tags",
        "primary_domain", "n_providers", "n_datasets", "is_flagged",
    ]].copy()

    # Serialise list columns
    for col in ("substantive_domains", "analytical_purpose", "cross_cutting_tags"):
        review[col] = review[col].apply(
            lambda x: "; ".join(x) if isinstance(x, list) else str(x)
        )

    # Add blank columns for human review
    review["human_domain"] = ""
    review["human_purpose"] = ""
    review["human_tags"] = ""
    review["notes"] = ""

    # Sort: flagged first, then by primary_domain
    review = review.sort_values(
        ["is_flagged", "primary_domain"],
        ascending=[False, True],
    ).reset_index(drop=True)

    return review


# ---------------------------------------------------------------------------
# Agreement reporting (post human review)
# ---------------------------------------------------------------------------

def compute_agreement_report(review_csv_path: str) -> str:
    """
    Compare human labels against LLM labels in a completed review CSV.
    Expects columns: substantive_domains, analytical_purpose, cross_cutting_tags,
                     human_domain, human_purpose, human_tags
    """
    df = pd.read_csv(review_csv_path, encoding="utf-8-sig")
    for col in ("cross_cutting_tags", "human_domain", "human_purpose", "human_tags"):
        if col not in df.columns:
            df[col] = ""

    human_cols = ["human_domain", "human_purpose", "human_tags"]
    reviewed_mask = pd.Series(False, index=df.index)
    for col in human_cols:
        reviewed_mask |= df[col].fillna("").astype(str).str.strip() != ""
    df_reviewed = df[reviewed_mask].copy()

    if df_reviewed.empty:
        return "No human-reviewed rows found. Fill in the human_* columns and re-run."

    n = len(df_reviewed)
    lines = [
        f"Agreement Report ({n} projects reviewed)",
        "=" * 60,
        "",
    ]

    def _label_set(value: object) -> set[str]:
        return {s.strip() for s in str(value).split(";") if s.strip()}

    def _append_set_agreement(title: str, llm_col: str, human_col: str) -> None:
        section = df_reviewed[df_reviewed[human_col].fillna("").astype(str).str.strip() != ""]
        lines.append(f"\n{title}")
        if section.empty:
            lines.append("  No reviewed labels supplied.")
            return
        section_n = len(section)
        exact = 0
        overlaps = 0
        for _, row in section.iterrows():
            llm_set = _label_set(row[llm_col])
            human_set = _label_set(row[human_col])
            if llm_set == human_set:
                exact += 1
                overlaps += 1
            elif llm_set & human_set:
                overlaps += 1
        lines.append(f"  Exact set match: {exact}/{section_n} ({exact/section_n*100:.1f}%)")
        lines.append(f"  Any overlap: {overlaps}/{section_n} ({overlaps/section_n*100:.1f}%)")

    # --- Layer A: any-overlap match ---
    _append_set_agreement("LAYER A — SUBSTANTIVE DOMAINS", "substantive_domains", "human_domain")

    # --- Layer C: any-overlap match ---
    _append_set_agreement("LAYER C — ANALYTICAL PURPOSE", "analytical_purpose", "human_purpose")

    # --- Tags: set match ---
    _append_set_agreement("CROSS-CUTTING TAGS", "cross_cutting_tags", "human_tags")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Quality check for LLM classifications")
    parser.add_argument(
        "--agreement", type=str, default=None,
        help="Path to a completed human review CSV to compute agreement report",
    )
    args = parser.parse_args()

    if args.agreement:
        report = compute_agreement_report(args.agreement)
        print(report)
        out_path = os.path.join(QUALITY_DIR, "agreement_report.txt")
        os.makedirs(QUALITY_DIR, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nSaved to {out_path}")
        return

    # --- Full diagnostics run ---
    print("Loading classifications...")
    df = load_classifications()
    print(f"Loaded {len(df):,} projects\n")

    os.makedirs(QUALITY_DIR, exist_ok=True)

    # 1. Diagnostic metrics
    print("Computing diagnostic metrics...")
    diagnostics = compute_diagnostic_metrics(df)
    print(diagnostics)
    diag_path = os.path.join(QUALITY_DIR, "diagnostic_report.txt")
    with open(diag_path, "w", encoding="utf-8") as f:
        f.write(diagnostics)
    print(f"\nSaved to {diag_path}\n")

    # 2. Suspicious flags
    print("Flagging suspicious classifications...")
    df_flags = flag_suspicious_classifications(df)
    flag_summary = summarise_flags(df_flags)
    print(flag_summary)
    if not df_flags.empty:
        flags_path = os.path.join(QUALITY_DIR, "suspicious_flags.csv")
        df_flags.to_csv(flags_path, index=False, encoding="utf-8-sig")
        print(f"\nSaved {len(df_flags)} flags to {flags_path}")

    flag_report_path = os.path.join(QUALITY_DIR, "flag_summary.txt")
    with open(flag_report_path, "w", encoding="utf-8") as f:
        f.write(flag_summary)
    print(f"Saved to {flag_report_path}\n")

    # 3. Human review sample
    print("Generating stratified review sample...")
    review = sample_for_human_review(df, df_flags, n=60)
    review_path = os.path.join(QUALITY_DIR, "human_review_sample.csv")
    review.to_csv(review_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(review)} projects to {review_path}")
    print(f"  Flagged: {review['is_flagged'].sum()}")
    print(f"  Domains covered: {review['primary_domain'].nunique()}")

    print("\n[done]")


if __name__ == "__main__":
    main()
