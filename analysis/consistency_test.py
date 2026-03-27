"""
Consistency Testing for Three-Layer LLM Classifications
========================================================
Measures classification stability by re-running a sample through the LLM
multiple times without caching, then computing agreement metrics.

Usage:
    set ANTHROPIC_API_KEY=sk-ant-...
    python analysis/consistency_test.py                # run 3 trials on 75 projects
    python analysis/consistency_test.py --trials 5     # run 5 trials
    python analysis/consistency_test.py --report-only  # just compute metrics from existing trials
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter

import numpy as np
import pandas as pd

import anthropic

# Import shared functions from the main classification script
from llm_theme_analysis_v3 import (
    classify_batch,
    load_data,
    _sanitise_prompt_text,
    _summarise_datasets,
    BATCH_SIZE,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ANALYSIS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(ANALYSIS_DIR, "outputs_v3")
QUALITY_DIR = os.path.join(OUTPUT_DIR, "quality")

# ---------------------------------------------------------------------------
# Sample selection
# ---------------------------------------------------------------------------

def select_test_sample(df: pd.DataFrame, n: int = 75, seed: int = 42) -> pd.DataFrame:
    """
    Stratified sample covering all Layer B categories and boundary cases.
    Returns a subset of the input DataFrame.
    """
    rng = np.random.default_rng(seed)

    # Read existing classifications to stratify by current labels
    csv_path = os.path.join(OUTPUT_DIR, "layer_classifications.csv")
    if os.path.exists(csv_path):
        df_cls = pd.read_csv(csv_path, encoding="utf-8-sig")
        # Merge linkage_mode onto df by Record ID
        if "linkage_mode" in df_cls.columns:
            mode_map = dict(zip(df_cls["Record ID"].astype(str), df_cls["linkage_mode"]))
            df = df.copy()
            df["_linkage_mode"] = df["Record ID"].astype(str).map(mode_map)
        else:
            df = df.copy()
            df["_linkage_mode"] = "unknown"
    else:
        df = df.copy()
        df["_linkage_mode"] = "unknown"

    sampled_ids = set()

    # Ensure each linkage mode is represented
    for mode in df["_linkage_mode"].dropna().unique():
        subset = df[df["_linkage_mode"] == mode]
        take = min(max(3, n // 10), len(subset))
        chosen = subset.sample(n=take, random_state=rng.integers(0, 2**31))
        sampled_ids.update(chosen["Record ID"])

    # Add short-title projects (boundary cases)
    short = df[(df["Title"].str.len() < 30) & (~df["Record ID"].isin(sampled_ids))]
    if len(short) > 0:
        take = min(5, len(short))
        chosen = short.sample(n=take, random_state=rng.integers(0, 2**31))
        sampled_ids.update(chosen["Record ID"])

    # Fill remaining quota randomly
    if len(sampled_ids) < n:
        remaining = df[~df["Record ID"].isin(sampled_ids)]
        extra = min(n - len(sampled_ids), len(remaining))
        if extra > 0:
            chosen = remaining.sample(n=extra, random_state=rng.integers(0, 2**31))
            sampled_ids.update(chosen["Record ID"])

    result = df[df["Record ID"].isin(sampled_ids)].drop(columns=["_linkage_mode"], errors="ignore")
    print(f"[sample] Selected {len(result)} projects for consistency testing")
    return result.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Trial execution
# ---------------------------------------------------------------------------

def run_trial(
    client: anthropic.Anthropic,
    sample_df: pd.DataFrame,
    trial_id: int,
    shuffle: bool = False,
    seed: int | None = None,
) -> dict:
    """
    Classify the sample once, bypassing the cache.
    Returns dict: record_id -> classification dict.
    """
    projects = [
        {
            "id": str(row["Record ID"]),
            "title": row["Title"],
            "prompt_title": _sanitise_prompt_text(row["Title"]),
            "prompt_datasets": _summarise_datasets(row.get("Datasets Used", "")),
        }
        for _, row in sample_df.iterrows()
    ]

    if shuffle and seed is not None:
        rng = np.random.default_rng(seed)
        rng.shuffle(projects)

    results = {}
    n_batches = (len(projects) - 1) // BATCH_SIZE + 1

    for i in range(0, len(projects), BATCH_SIZE):
        batch = projects[i: i + BATCH_SIZE]
        # Assign short prompt IDs
        batch = [
            {**p, "prompt_id": f"P{offset:02d}"}
            for offset, p in enumerate(batch, start=1)
        ]
        batch_num = i // BATCH_SIZE + 1
        print(f"  Trial {trial_id}, batch {batch_num}/{n_batches} ({len(batch)} projects)...")

        try:
            batch_results = classify_batch(client, batch)
            results.update(batch_results)
        except Exception as e:
            print(f"  [error] Batch {batch_num} failed: {e}")
            # Mark failed projects
            for p in batch:
                if p["id"] not in results:
                    results[p["id"]] = {
                        "substantive_domains": ["TRIAL_FAILED"],
                        "linkage_mode": "TRIAL_FAILED",
                        "analytical_purpose": ["TRIAL_FAILED"],
                    }

        time.sleep(0.5)

    return results


def save_trial(results: dict, trial_id: int) -> str:
    """Save trial results to JSON."""
    os.makedirs(QUALITY_DIR, exist_ok=True)
    path = os.path.join(QUALITY_DIR, f"consistency_trial_{trial_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return path


# ---------------------------------------------------------------------------
# Consistency metrics
# ---------------------------------------------------------------------------

def load_trials() -> list[dict]:
    """Load all consistency trial JSON files from the quality directory."""
    trials = []
    if not os.path.isdir(QUALITY_DIR):
        return trials
    for fname in sorted(os.listdir(QUALITY_DIR)):
        if fname.startswith("consistency_trial_") and fname.endswith(".json"):
            path = os.path.join(QUALITY_DIR, fname)
            with open(path, encoding="utf-8") as f:
                trials.append(json.load(f))
    return trials


def compute_consistency_metrics(trials: list[dict]) -> str:
    """Compute pairwise agreement across trials."""
    if len(trials) < 2:
        return "Need at least 2 trials to compute consistency. Run more trials."

    n_trials = len(trials)

    # Get IDs present in all trials
    all_ids = set(trials[0].keys())
    for t in trials[1:]:
        all_ids &= set(t.keys())
    all_ids = sorted(all_ids)

    if not all_ids:
        return "No common project IDs across trials."

    n_projects = len(all_ids)
    lines = [
        f"Consistency Report ({n_trials} trials, {n_projects} common projects)",
        "=" * 60,
        "",
    ]

    # Per-layer agreement
    for layer_key, layer_name in [
        ("linkage_mode", "Layer B — Linkage Mode"),
        ("substantive_domains", "Layer A — Substantive Domains"),
        ("analytical_purpose", "Layer C — Analytical Purpose"),
    ]:
        lines.append(f"{layer_name}")

        # Pairwise agreement
        pair_agreements = []
        for i in range(n_trials):
            for j in range(i + 1, n_trials):
                matches = 0
                for pid in all_ids:
                    v_i = trials[i].get(pid, {}).get(layer_key)
                    v_j = trials[j].get(pid, {}).get(layer_key)
                    if isinstance(v_i, list) and isinstance(v_j, list):
                        if set(v_i) == set(v_j):
                            matches += 1
                    elif v_i == v_j:
                        matches += 1
                pair_agreements.append(matches / n_projects)

        mean_agree = np.mean(pair_agreements)
        min_agree = np.min(pair_agreements)
        max_agree = np.max(pair_agreements)
        lines.append(f"  Pairwise agreement: {mean_agree:.1%} (range: {min_agree:.1%}–{max_agree:.1%})")

        # Per-project stability (unanimous across all trials)
        unanimous = 0
        unstable_examples = []
        for pid in all_ids:
            values = []
            for t in trials:
                v = t.get(pid, {}).get(layer_key)
                if isinstance(v, list):
                    values.append(tuple(sorted(v)))
                else:
                    values.append(v)
            if len(set(values)) == 1:
                unanimous += 1
            else:
                if len(unstable_examples) < 5:
                    unstable_examples.append((pid, values))

        lines.append(f"  Unanimous (same across all trials): {unanimous}/{n_projects} ({unanimous/n_projects:.1%})")

        if unstable_examples:
            lines.append(f"  Unstable examples:")
            for pid, vals in unstable_examples:
                val_strs = [str(v) for v in vals]
                lines.append(f"    {pid}: {' / '.join(val_strs)}")

        lines.append("")

    # Per-category stability for Layer B
    lines.append("Layer B stability by category:")
    category_stable = Counter()
    category_total = Counter()
    for pid in all_ids:
        values = [trials[t].get(pid, {}).get("linkage_mode") for t in range(n_trials)]
        most_common = Counter(values).most_common(1)[0][0]
        category_total[most_common] += 1
        if len(set(values)) == 1:
            category_stable[most_common] += 1

    for cat in sorted(category_total.keys()):
        stable = category_stable.get(cat, 0)
        total = category_total[cat]
        lines.append(f"  {cat}: {stable}/{total} stable ({stable/total:.0%})" if total else f"  {cat}: 0/0")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Consistency testing for LLM classifications")
    parser.add_argument("--trials", type=int, default=3, help="Number of trials to run")
    parser.add_argument("--sample-size", type=int, default=75, help="Number of projects per trial")
    parser.add_argument("--report-only", action="store_true", help="Only compute metrics from existing trials")
    args = parser.parse_args()

    if args.report_only:
        trials = load_trials()
        if not trials:
            print("No trial files found in", QUALITY_DIR)
            return
        report = compute_consistency_metrics(trials)
        print(report)
        report_path = os.path.join(QUALITY_DIR, "consistency_report.txt")
        os.makedirs(QUALITY_DIR, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\nSaved to {report_path}")
        return

    # Need API key for trials
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set. Set it to run consistency trials.")
        print("Use --report-only to compute metrics from existing trial files.")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # Load data and select sample
    print("Loading data...")
    df = load_data()
    sample = select_test_sample(df, n=args.sample_size)

    # Run trials
    for trial_id in range(1, args.trials + 1):
        shuffle = trial_id > 1  # first trial unshuffled, rest shuffled
        print(f"\n{'='*40}")
        print(f"Trial {trial_id}/{args.trials} {'(shuffled)' if shuffle else '(original order)'}")
        print(f"{'='*40}")

        results = run_trial(
            client, sample, trial_id,
            shuffle=shuffle,
            seed=trial_id * 1000 if shuffle else None,
        )
        path = save_trial(results, trial_id)
        print(f"  Saved to {path}")
        print(f"  Classified: {len(results)} projects")

        if trial_id < args.trials:
            print("  Waiting 2s before next trial...")
            time.sleep(2)

    # Compute metrics
    print(f"\n{'='*40}")
    print("Computing consistency metrics...")
    print(f"{'='*40}\n")

    trials = load_trials()
    report = compute_consistency_metrics(trials)
    print(report)

    report_path = os.path.join(QUALITY_DIR, "consistency_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved to {report_path}")
    print("\n[done]")


if __name__ == "__main__":
    main()
