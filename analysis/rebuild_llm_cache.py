"""Rebuild the LLM classification cache from a layer_classifications.csv.

The classification cache (``llm_layer_cache.json``) is gitignored and may not
exist locally, but every published run keeps its full per-project outputs in
``layer_classifications.csv``. This tool reconstructs a schema-v6 cache from
that CSV — including content fingerprints computed from the Title and
"Datasets Used" text that produced each classification — so a register refresh
only pays API calls for new or changed projects instead of re-classifying the
whole register.

Usage:
    python -m analysis.rebuild_llm_cache \
        --classifications analysis/outputs_v4_8_rc2/layer_classifications.csv \
        --output analysis/outputs_v3/llm_layer_cache.json
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile

import pandas as pd

try:
    from analysis.llm_theme_analysis_v3 import (
        CACHE_SCHEMA_VERSION,
        MODEL,
        PROMPT_VERSION,
        RATIONALE_PLACEHOLDER,
        _classification_fingerprint,
        _sanitise_prompt_text,
        _summarise_datasets,
    )
except ModuleNotFoundError:
    from llm_theme_analysis_v3 import (  # type: ignore
        CACHE_SCHEMA_VERSION,
        MODEL,
        PROMPT_VERSION,
        RATIONALE_PLACEHOLDER,
        _classification_fingerprint,
        _sanitise_prompt_text,
        _summarise_datasets,
    )

ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLASSIFICATIONS = os.path.join(ANALYSIS_DIR, "outputs_v4_8_rc2", "layer_classifications.csv")
DEFAULT_OUTPUT = os.path.join(ANALYSIS_DIR, "outputs_v3", "llm_layer_cache.json")

REQUIRED_COLUMNS = [
    "Record ID",
    "Title",
    "Datasets Used",
    "substantive_domains",
    "analytical_purpose",
]


def _split_joined(value) -> list[str]:
    if pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def build_cache_entries(classifications: pd.DataFrame) -> dict:
    missing = [col for col in REQUIRED_COLUMNS if col not in classifications.columns]
    if missing:
        raise ValueError(f"Classifications CSV is missing columns: {', '.join(missing)}")

    duplicate_ids = classifications["Record ID"].astype(str).duplicated()
    if duplicate_ids.any():
        raise ValueError(
            f"Classifications CSV contains {int(duplicate_ids.sum())} duplicate Record IDs"
        )

    entries: dict[str, dict] = {}
    for _, row in classifications.iterrows():
        record_id = str(row["Record ID"])
        prompt_title = _sanitise_prompt_text(row["Title"])
        prompt_datasets = _summarise_datasets(row.get("Datasets Used", ""))
        rationale = row.get("rationale")
        entries[record_id] = {
            "substantive_domains": _split_joined(row["substantive_domains"]),
            "analytical_purpose": _split_joined(row["analytical_purpose"]),
            "cross_cutting_tags": _split_joined(row.get("cross_cutting_tags")),
            "rationale": (
                str(rationale)
                if rationale is not None and not pd.isna(rationale) and str(rationale).strip()
                else RATIONALE_PLACEHOLDER
            ),
            "fingerprint": _classification_fingerprint(prompt_title, prompt_datasets),
        }
    return entries


def write_cache(entries: dict, output_path: str, *, model: str, prompt_version: str) -> None:
    payload = {
        "__meta__": {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "prompt_version": prompt_version,
            "model": model,
        },
        "entries": entries,
    }
    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="llm_layer_cache_", suffix=".json", dir=output_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
    os.replace(tmp_path, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild llm_layer_cache.json from a layer_classifications.csv"
    )
    parser.add_argument("--classifications", default=DEFAULT_CLASSIFICATIONS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--model",
        default=MODEL,
        help="Model recorded in cache meta; must match the model the classifier will run with",
    )
    parser.add_argument(
        "--prompt-version",
        default=PROMPT_VERSION,
        help="Prompt version recorded in cache meta; must match the classifier's PROMPT_VERSION",
    )
    args = parser.parse_args()

    classifications = pd.read_csv(args.classifications, encoding="utf-8-sig")
    entries = build_cache_entries(classifications)
    write_cache(entries, args.output, model=args.model, prompt_version=args.prompt_version)
    print(
        f"Rebuilt cache with {len(entries):,} entries "
        f"(schema v{CACHE_SCHEMA_VERSION}, prompt {args.prompt_version}, model {args.model})"
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
