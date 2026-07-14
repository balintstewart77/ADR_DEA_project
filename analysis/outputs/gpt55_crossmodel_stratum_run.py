from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis import llm_theme_analysis_v3 as clf
from analysis.crossmodel_comparison import build_comparison as _build_comparison_offline


MODEL = "gpt-5.5"
PROMPT_VERSION = clf.PROMPT_VERSION
TAXONOMY_VERSION = "dict-1.0-rc2"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "outputs"
CACHE_PATH = OUTPUT_DIR / f"gpt55_{MODEL}_{PROMPT_VERSION}_llm_layer_cache.json"
FABLE_RELEASE_CSV = PROJECT_ROOT / "analysis" / "outputs_classified_20260702_fable5" / "layer_classifications.csv"
FABLE_RELEASE_META = PROJECT_ROOT / "analysis" / "outputs_classified_20260702_fable5" / "run_metadata.json"
SAMPLE_PATH = OUTPUT_DIR / "model_comparison_sample.csv"
PRICING = {
    "input_per_mtok": 5.00,
    "output_per_mtok": 30.00,
}
MAX_RETRIES = 3


def _require_openai():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("The 'openai' package is required. Install it with: python -m pip install openai") from exc
    return OpenAI


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def _cache_meta(prompt_hash: str) -> dict[str, Any]:
    return {
        "cache_schema_version": "gpt55-stratum-1",
        "provider": "openai",
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "production_cache_schema_version": clf.CACHE_SCHEMA_VERSION,
        "prompt_hash_sha256": prompt_hash,
        "namespace": f"openai/{MODEL}/{PROMPT_VERSION}",
    }


def load_cache(prompt_hash: str) -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {"__meta__": _cache_meta(prompt_hash), "entries": {}, "usage_log": [], "failures": []}
    raw = _read_json(CACHE_PATH)
    expected = _cache_meta(prompt_hash)
    if raw.get("__meta__") != expected:
        raise SystemExit(f"Existing GPT cache meta mismatch at {CACHE_PATH}")
    raw.setdefault("entries", {})
    raw.setdefault("usage_log", [])
    raw.setdefault("failures", [])
    return raw


def save_cache(cache: dict[str, Any]) -> None:
    _write_json_atomic(CACHE_PATH, cache)


def _split_labels(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


def _join_labels(labels: object) -> str:
    if isinstance(labels, list):
        return "; ".join(str(item) for item in labels)
    if labels is None:
        return ""
    return str(labels)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def _fingerprint_for_row(row: pd.Series) -> str:
    prompt_title = clf._sanitise_prompt_text(row["Title"])
    prompt_datasets = clf._summarise_datasets(row.get("Datasets Used", ""))
    return clf._classification_fingerprint(prompt_title, prompt_datasets)


def _projects_to_classify(df: pd.DataFrame, cache: dict[str, Any]) -> list[dict[str, Any]]:
    entries = cache["entries"]
    projects: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record_id = str(row["Record ID"])
        prompt_title = clf._sanitise_prompt_text(row["Title"])
        prompt_datasets = clf._summarise_datasets(row.get("Datasets Used", ""))
        fingerprint = clf._classification_fingerprint(prompt_title, prompt_datasets)
        cached = entries.get(record_id)
        if isinstance(cached, dict) and cached.get("fingerprint") == fingerprint and cached.get("status") in {"ok", "gpt_invalid"}:
            continue
        projects.append({
            "id": record_id,
            "prompt_id": record_id,
            "title": row["Title"],
            "prompt_title": prompt_title,
            "prompt_datasets": prompt_datasets,
            "fingerprint": fingerprint,
        })
    return projects


def _usage_dict(response: Any, api_path: str, config_as_sent: dict[str, Any]) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)
    return {
        "api_path": api_path,
        "response_id": getattr(response, "id", None),
        "response_model": getattr(response, "model", None),
        "status": getattr(response, "status", None),
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "cached_input_tokens": getattr(input_details, "cached_tokens", None),
        "reasoning_output_tokens": getattr(output_details, "reasoning_tokens", None),
        "config_as_sent": config_as_sent,
    }


def _extract_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                parts.append(text)
    text = "\n".join(parts).strip()
    if text:
        return text
    raise RuntimeError("OpenAI response did not contain output_text")


def _strict_schema_from_pydantic_model() -> dict[str, Any]:
    try:
        from openai.lib._pydantic import to_strict_json_schema

        return to_strict_json_schema(clf.BatchLayerResult)
    except Exception:
        pass

    schema = clf.BatchLayerResult.model_json_schema()

    def strictify(node: Any) -> Any:
        if isinstance(node, dict):
            out = {key: strictify(value) for key, value in node.items()}
            if out.get("type") == "object" and isinstance(out.get("properties"), dict):
                out["additionalProperties"] = False
                out["required"] = list(out["properties"].keys())
            return out
        if isinstance(node, list):
            return [strictify(item) for item in node]
        return node

    return strictify(schema)


def _response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "name": "BatchLayerResult",
        "schema": _strict_schema_from_pydantic_model(),
        "strict": True,
    }


def _input_for_batch(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "role": "user",
        "content": [
            {"type": "input_text", "text": clf._build_static_prompt()},
            {"type": "input_text", "text": clf._build_projects_block(projects)},
        ],
    }]


def _classify_batch(client: Any, projects: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    request_input = _input_for_batch(projects)
    config_as_sent = {
        "model": MODEL,
        "max_output_tokens": clf.MAX_TOKENS,
        "input": "single user message with two input_text blocks: static taxonomy prompt, then per-batch projects block",
        "text.format": "json_schema generated from analysis.llm_theme_analysis_v3.BatchLayerResult",
        "text.format.strict": True,
        "temperature": "omitted",
        "reasoning": "omitted",
    }
    response = client.responses.create(
        model=MODEL,
        input=request_input,
        max_output_tokens=clf.MAX_TOKENS,
        text={"format": _response_format()},
    )
    usage = _usage_dict(response, "responses.create", config_as_sent)
    raw_text = _extract_output_text(response)
    raw_dict = json.loads(raw_text)
    expected_ids = [project["id"] for project in projects]
    returned = raw_dict.get("classifications", [])
    if not isinstance(returned, list):
        raise RuntimeError("Structured response did not contain a classifications list")

    by_id: dict[str, Any] = {}
    duplicate_ids: list[str] = []
    unexpected_ids: list[str] = []
    for item in returned:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("project_id", ""))
        if rid not in expected_ids:
            unexpected_ids.append(rid)
            continue
        if rid in by_id:
            duplicate_ids.append(rid)
            continue
        by_id[rid] = item
    missing_ids = [rid for rid in expected_ids if rid not in by_id]
    if unexpected_ids or duplicate_ids or missing_ids:
        raise RuntimeError(
            "Batch integrity failure: "
            f"unexpected={unexpected_ids}; duplicate={duplicate_ids}; missing={missing_ids}"
        )

    results: dict[str, Any] = {}
    fingerprint_by_id = {project["id"]: project["fingerprint"] for project in projects}
    for rid in expected_ids:
        item = dict(by_id[rid])
        try:
            parsed = clf.ProjectLayers(**item)
            results[rid] = {
                "status": "ok",
                "substantive_domains": parsed.substantive_domains,
                "analytical_purpose": parsed.analytical_purpose,
                "cross_cutting_tags": parsed.cross_cutting_tags,
                "rationale": parsed.rationale,
                "fingerprint": fingerprint_by_id[rid],
            }
        except Exception as exc:
            results[rid] = {
                "status": "gpt_invalid",
                "raw_classification": item,
                "validation_error": str(exc),
                "substantive_domains": item.get("substantive_domains", []),
                "analytical_purpose": item.get("analytical_purpose", []),
                "cross_cutting_tags": item.get("cross_cutting_tags", []),
                "rationale": item.get("rationale", ""),
                "fingerprint": fingerprint_by_id[rid],
            }
    return results, usage


def run_gpt55(df: pd.DataFrame, cache: dict[str, Any]) -> None:
    OpenAI = _require_openai()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set")
    client = OpenAI()
    to_classify = _projects_to_classify(df, cache)
    print(f"[gpt55] {len(df) - len(to_classify):,} cached; {len(to_classify):,} to classify")
    if not to_classify:
        return
    n_batches = (len(to_classify) - 1) // clf.BATCH_SIZE + 1
    for start in range(0, len(to_classify), clf.BATCH_SIZE):
        batch = to_classify[start:start + clf.BATCH_SIZE]
        batch_num = start // clf.BATCH_SIZE + 1
        print(f"  Batch {batch_num}/{n_batches} ({len(batch)} projects)")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                results, usage = _classify_batch(client, batch)
                cache["entries"].update(results)
                cache["usage_log"].append(usage)
                save_cache(cache)
                break
            except Exception as exc:
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    print(f"  [retry] attempt {attempt}/{MAX_RETRIES} failed: {exc}; waiting {wait}s")
                    time.sleep(wait)
                    continue
                failure = {
                    "batch_num": batch_num,
                    "record_ids": [project["id"] for project in batch],
                    "error": str(exc),
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                }
                cache["failures"].append(failure)
                save_cache(cache)
                raise
        time.sleep(0.5)


def build_gpt_classifications(df: pd.DataFrame, cache: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    entries = cache["entries"]
    for _, row in df.iterrows():
        rid = str(row["Record ID"])
        entry = entries.get(rid, {})
        rows.append({
            "Project ID": row.get("Project ID", ""),
            "Record ID": rid,
            "Title": row.get("Title", ""),
            "Datasets Used": row.get("Datasets Used", ""),
            "Accreditation Date": row.get("Accreditation Date", ""),
            "Year": row.get("Year", ""),
            "gpt_status": entry.get("status", "missing"),
            "substantive_domains": _join_labels(entry.get("substantive_domains", [])),
            "analytical_purpose": _join_labels(entry.get("analytical_purpose", [])),
            "cross_cutting_tags": _join_labels(entry.get("cross_cutting_tags", [])),
            "rationale": entry.get("rationale", ""),
            "validation_error": entry.get("validation_error", ""),
            "raw_classification": json.dumps(entry.get("raw_classification", {}), ensure_ascii=False) if entry.get("raw_classification") else "",
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUTPUT_DIR / "gpt55_classifications.csv", index=False, encoding="utf-8-sig")
    return out


def build_comparison(gpt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fable = pd.read_csv(FABLE_RELEASE_CSV, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    comparison, stratum_df = _build_comparison_offline(fable, gpt)
    comparison.to_csv(OUTPUT_DIR / "crossmodel_comparison.csv", index=False, encoding="utf-8-sig")
    stratum_df.to_csv(OUTPUT_DIR / "crossmodel_disagreement_stratum.csv", index=False, encoding="utf-8-sig")
    return comparison, stratum_df


def _label_flip_counts(comparison: pd.DataFrame, layer: str) -> list[dict[str, Any]]:
    f_col = f"fable_{layer}"
    g_col = f"gpt_{layer}"
    exact_col = "domains_exact_match" if layer == "domains" else "purposes_exact_match"
    counter: Counter[str] = Counter()
    for _, row in comparison[~comparison[exact_col]].iterrows():
        f_labels = set(_split_labels(row[f_col]))
        g_labels = set(_split_labels(row[g_col]))
        for label in f_labels ^ g_labels:
            direction = "GPT-only" if label in g_labels else "Fable-only"
            counter[f"{label} [{direction}]"] += 1
    return [{"label": label, "count": count} for label, count in counter.most_common(10)]


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "(none)"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        values = [str(row.get(col, "")).replace("|", "\\|") for col in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _usage_totals(cache: dict[str, Any]) -> dict[str, int]:
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cached_input_tokens": 0,
        "reasoning_output_tokens": 0,
    }
    for item in cache.get("usage_log", []):
        for key in totals:
            totals[key] += int(item.get(key) or 0)
    return totals


def _cost(totals: dict[str, int]) -> float:
    return (
        totals["input_tokens"] / 1_000_000 * PRICING["input_per_mtok"]
        + totals["output_tokens"] / 1_000_000 * PRICING["output_per_mtok"]
    )


def write_metadata_and_report(
    df: pd.DataFrame,
    cache: dict[str, Any],
    comparison: pd.DataFrame,
    stratum_df: pd.DataFrame,
    docs_sources: dict[str, str],
) -> None:
    usage_totals = _usage_totals(cache)
    invalid = comparison[comparison["gpt_status"] == "gpt_invalid"].copy()
    tag_only_count = int(comparison["tag_only_disagreement"].sum())
    stratum_plus_tags = int(len(stratum_df) + tag_only_count)
    layer_breakdown = stratum_df["disagreement_layer"].value_counts().to_dict() if len(stratum_df) else {}
    adjudicated_ids: set[str] = set()
    if SAMPLE_PATH.exists():
        sample = pd.read_csv(SAMPLE_PATH, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        adjudicated_ids = set(sample.loc[sample["stratum"] == "adjudicated", "Record ID"].astype(str))
    stratum_ids = set(stratum_df["Record ID"].astype(str)) if len(stratum_df) else set()
    adjudicated_overlap = sorted(stratum_ids & adjudicated_ids)
    divergence_list = [
        "Provider/API changed from Anthropic Messages API to OpenAI Responses API.",
        "OpenAI invocation used input_text content blocks; Anthropic invocation used text content blocks with cache_control on the static prompt block.",
        "OpenAI structured output enforcement used text.format json_schema generated from the production BatchLayerResult Pydantic model; Fable used Anthropic messages.parse output_format=BatchLayerResult.",
        "OpenAI run omitted temperature, matching the Fable release omission; no reasoning parameter was sent.",
        "OpenAI prompt caching was not explicitly controlled; any provider-side caching is automatic and only visible through usage details if returned.",
    ]
    config_as_sent = {
        "model": MODEL,
        "max_output_tokens": clf.MAX_TOKENS,
        "batch_size": clf.BATCH_SIZE,
        "input": "single user message with two input_text blocks: exact static taxonomy prompt and per-batch projects block",
        "text_format": "json_schema generated from analysis.llm_theme_analysis_v3.BatchLayerResult",
        "text_format_strict": True,
        "temperature": "omitted",
        "reasoning": "omitted",
    }
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_type": "cross_model_hard_case_disagreement_stratum_not_release",
        "model": MODEL,
        "model_verification": docs_sources,
        "prompt_version": PROMPT_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "production_cache_schema_version": clf.CACHE_SCHEMA_VERSION,
        "n_projects": int(len(df)),
        "source_register": "same cleaned live register loaded by analysis.llm_theme_analysis_v3.load_data()",
        "fable_release_source": str(FABLE_RELEASE_CSV.relative_to(PROJECT_ROOT)),
        "cache_path": str(CACHE_PATH.relative_to(PROJECT_ROOT)),
        "cache_namespace": cache["__meta__"]["namespace"],
        "config_as_sent": config_as_sent,
        "divergences_from_fable_invocation": divergence_list,
        "usage_totals": usage_totals,
        "pricing": PRICING,
        "approx_cost_usd": round(_cost(usage_totals), 4),
        "gpt_invalid_count": int(len(invalid)),
        "gpt_invalid_record_ids": invalid["Record ID"].astype(str).tolist(),
        "outputs": [
            "analysis/outputs/gpt55_run_metadata.json",
            "analysis/outputs/gpt55_classifications.csv",
            "analysis/outputs/crossmodel_comparison.csv",
            "analysis/outputs/crossmodel_disagreement_stratum.csv",
            "analysis/outputs/instruction_gpt55_stratum_report.md",
        ],
        "confirmation": {
            "frozen_release_files_touched": False,
            "register_reference_touched": False,
            "taxonomy_yaml_touched": False,
            "release_pointers_touched": False,
            "git_push": False,
        },
        "usage_log": cache.get("usage_log", []),
    }
    _write_json_atomic(OUTPUT_DIR / "gpt55_run_metadata.json", metadata)

    all_n = len(comparison)
    domains_exact_rate = float(comparison["domains_exact_match"].mean())
    purposes_exact_rate = float(comparison["purposes_exact_match"].mean())
    covid_rate = float(comparison["covid_tag_match"].mean())
    disparities_rate = float(comparison["disparities_tag_match"].mean())
    report = f"""# GPT-5.5 cross-model disagreement stratum

## Scope

- Purpose: stratification apparatus for hard-case sampling; not validation and not a release.
- Population: `{all_n}` cleaned live projects.
- Fable source: `analysis/outputs_classified_20260702_fable5/layer_classifications.csv`.
- GPT model string: `{MODEL}`.
- Prompt/taxonomy: `{PROMPT_VERSION}` using the production taxonomy labels from `_labels_for_layer`.
- OpenAI docs verification: model page confirms model ID/pricing/context; structured-output docs confirm Pydantic structured outputs for `gpt-5.5`.

## Agreement rates

| Layer | Exact match rate | Mean Jaccard / match rate |
| --- | ---: | ---: |
| domains | {_pct(domains_exact_rate)} | {comparison["domains_jaccard"].mean():.3f} |
| purposes | {_pct(purposes_exact_rate)} | {comparison["purposes_jaccard"].mean():.3f} |
| COVID tag | {_pct(covid_rate)} | n/a |
| disparities tag | {_pct(disparities_rate)} | n/a |

## Stratum size

- DISAGREE stratum size: `{len(stratum_df)}`.
- Size if tag-only disagreements were also included: `{stratum_plus_tags}`.
- Tag-only disagreements excluded by default: `{tag_only_count}`.

## Disagreement breakdown

- Domains-only: `{layer_breakdown.get("domains-only", 0)}`.
- Purposes-only: `{layer_breakdown.get("purposes-only", 0)}`.
- Both domains and purposes: `{layer_breakdown.get("both", 0)}`.

## Top disagreed labels

### Domains

{_markdown_table(_label_flip_counts(comparison, "domains"), ["label", "count"])}

### Purposes

{_markdown_table(_label_flip_counts(comparison, "purposes"), ["label", "count"])}

## Adjudicated-set overlap

- Adjudicated/defended records in comparison sample: `{len(adjudicated_ids)}`.
- Adjudicated/defended records in DISAGREE stratum: `{len(adjudicated_overlap)}`.
- Overlap IDs: `{'; '.join(adjudicated_overlap) if adjudicated_overlap else '(none)'}`.

## GPT invalid

- GPT invalid records: `{len(invalid)}`.

{_markdown_table(invalid[["Record ID", "gpt_validation_error"]].to_dict("records"), ["Record ID", "gpt_validation_error"])}

## Cost and invocation

- Usage totals: `{usage_totals}`.
- Approximate cost: `${round(_cost(usage_totals), 4)}` using public GPT-5.5 input/output rates from the OpenAI models page.
- Config as sent: `{json.dumps(config_as_sent, ensure_ascii=False)}`.

Invocation divergences to carry into methods caveats:

{chr(10).join(f"- {item}" for item in divergence_list)}

## Guardrails

- Frozen release directory untouched.
- `register_reference.yaml`, `taxonomy_data_dictionary.yaml`, and `data/release_pointers.json` untouched.
- No dashboard, release, or user-facing artefacts changed.
- No git push.
"""
    (OUTPUT_DIR / "instruction_gpt55_stratum_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-run", action="store_true", help="Use existing GPT cache and rebuild CSV/report outputs only")
    args = parser.parse_args()

    clf.OUTPUT_DIR = str(OUTPUT_DIR / "gpt55_cleaning_aux")
    clf.CACHE_FILE = str(OUTPUT_DIR / "gpt55_unused_classifier_cache.json")
    clf._build_static_prompt.cache_clear()
    prompt_hash = hashlib.sha256(clf._build_static_prompt().encode("utf-8")).hexdigest()
    cache = load_cache(prompt_hash)

    df = clf.load_data()
    df["Record ID"] = df["Record ID"].astype(str)
    if len(df) != 1308:
        raise SystemExit(f"Expected 1,308 cleaned live register entries, got {len(df)}")
    fable_meta = _read_json(FABLE_RELEASE_META)
    if fable_meta.get("n_projects") != 1308 or fable_meta.get("prompt_version") != PROMPT_VERSION:
        raise SystemExit("Fable release metadata does not match expected population/prompt")

    if not args.skip_run:
        run_gpt55(df, cache)
        cache = load_cache(prompt_hash)

    missing = sorted(set(df["Record ID"]) - set(cache["entries"]))
    if missing:
        raise SystemExit(f"GPT cache incomplete; missing {len(missing)} records, e.g. {missing[:10]}")

    gpt = build_gpt_classifications(df, cache)
    comparison, stratum_df = build_comparison(gpt)
    write_metadata_and_report(
        df,
        cache,
        comparison,
        stratum_df,
        docs_sources={
            "models": "https://developers.openai.com/api/docs/models",
            "structured_outputs": "https://developers.openai.com/api/docs/guides/structured-outputs",
        },
    )
    print(f"[done] GPT classifications: {OUTPUT_DIR / 'gpt55_classifications.csv'}")
    print(f"[done] comparison: {OUTPUT_DIR / 'crossmodel_comparison.csv'}")
    print(f"[done] stratum: {OUTPUT_DIR / 'crossmodel_disagreement_stratum.csv'}")
    print(f"[done] report: {OUTPUT_DIR / 'instruction_gpt55_stratum_report.md'}")


if __name__ == "__main__":
    main()
