"""
Find near-duplicate dataset name clusters in the DEA dashboard data.

This script reimplements only the minimal data-loading and parsing logic from
dashboard/app.py (to avoid importing Dash/Plotly), then groups dataset names
that are likely near-duplicates.

Usage:
    python analysis/find_duplicates.py
"""

import os
import re
import pandas as pd
from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations
import sys

# ── Paths ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dataset_normalisation import parse_datasets  # noqa: E402
from register_cleaning import clean_register_dataframe, load_raw_register  # noqa: E402

# ── Data loading (minimal, no Dash) ──────────────────────────────────────

def load_raw(data_dir=DATA_DIR):
    return load_raw_register(data_dir)


def process_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    df, _stats = clean_register_dataframe(df_raw, include_quarter_date=True)
    return df


# ── Near-duplicate detection ─────────────────────────────────────────────

TRAILING_NOISE_WORDS = [
    "Data", "Dataset", "Statistics", "Survey", "Residents",
    "Register", "Records", "Service", "System", "Database",
    "Programme", "Project", "Collection", "Information",
]

_TRAILING_NOISE_PAT = re.compile(
    r"\s+(?:" + "|".join(w.lower() for w in TRAILING_NOISE_WORDS) + r")\s*$",
)


def _canon(name: str) -> str:
    """Lowercase, collapse whitespace, iteratively strip trailing noise words."""
    s = " ".join(name.lower().split())
    prev = None
    while prev != s:
        prev = s
        s = _TRAILING_NOISE_PAT.sub("", s).strip()
    return s


def find_clusters(names_counts: dict[str, int]) -> list[list[str]]:
    """Return groups of near-duplicate dataset names.

    Heuristics:
      a. One name is a prefix/substring of another
      b. Names that differ only by trailing noise words
      c. Fuzzy similarity (SequenceMatcher ratio > 0.85)
    """
    names = sorted(names_counts.keys())
    n = len(names)

    # Union-Find
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    lowered = [name.lower() for name in names]
    canon = [_canon(name) for name in names]

    for i, j in combinations(range(n), 2):
        if find(i) == find(j):
            continue

        li, lj = lowered[i], lowered[j]
        ci, cj = canon[i], canon[j]

        # a. Substring / prefix check
        if li in lj or lj in li:
            union(i, j)
            continue

        # b. Same after stripping trailing noise words
        if ci and cj and ci == cj:
            union(i, j)
            continue

        # c. Fuzzy match on the full lowered names
        ratio = SequenceMatcher(None, li, lj).ratio()
        if ratio > 0.85:
            union(i, j)
            continue

        # Also fuzzy-match on canon forms
        if ci and cj:
            ratio_canon = SequenceMatcher(None, ci, cj).ratio()
            if ratio_canon > 0.85:
                union(i, j)
                continue

    groups: dict[int, list[str]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(names[i])

    return [members for members in groups.values() if len(members) >= 2]


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    df_raw, source_file = load_raw()
    df_all = process_data(df_raw)
    df_datasets = parse_datasets(df_all)

    # Unique dataset names with project counts (de-duplicate within a project)
    ds_counts = (
        df_datasets
        .drop_duplicates(subset=["Project ID", "dataset"])
        .groupby("dataset")["Project ID"]
        .nunique()
        .to_dict()
    )

    print(f"Total unique dataset names (after normalisation): {len(ds_counts)}")
    print()

    clusters = find_clusters(ds_counts)

    # Sort clusters by total project count (descending)
    clusters.sort(key=lambda grp: sum(ds_counts[n] for n in grp), reverse=True)

    print(f"Near-duplicate clusters found: {len(clusters)}")
    print("=" * 80)

    for idx, cluster in enumerate(clusters, 1):
        cluster.sort(key=lambda n: ds_counts[n], reverse=True)
        total = sum(ds_counts[n] for n in cluster)
        print(f"\nCluster {idx}  (total projects: {total})")
        print("-" * 60)
        for name in cluster:
            print(f"  {ds_counts[name]:>4}  {name}")

    if not clusters:
        print("\nNo near-duplicate clusters detected.")


if __name__ == "__main__":
    main()
