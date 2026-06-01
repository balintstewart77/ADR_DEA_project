"""
Three-Layer LLM Classification of DEA Project Titles
=====================================================
Implements a three-dimensional classification framework that avoids collapsing
all nuance into a single subject-area label:

    Layer A — Substantive Domain   (1 or more from 14 themes)
    Layer B — Linkage Mode         (exactly 1)
    Layer C — Analytical Purpose   (1 or 2)

Each layer is classified independently so that patterns across dimensions can
be analysed separately (e.g. all "Cross-Domain Linkage" projects, or all
"Policy Evaluation" projects regardless of domain).

Output format per project:
{
  "ProjectID": {
    "substantive_domains": ["Education & Skills", "Labour Market & Employment"],
    "linkage_mode": "Cross-Domain Linkage",
    "analytical_purpose": ["Life-Course / Trajectory Analysis"]
  }
}

Requirements:
    pip install anthropic pandas pydantic

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...   (Unix)
    set   ANTHROPIC_API_KEY=sk-ant-...   (Windows)

    python analysis/llm_theme_analysis_v3.py
    python analysis/llm_theme_analysis_v3.py --model claude-opus-4-6 --output-dir analysis/outputs_opus_4_6
    python analysis/llm_theme_analysis_v3.py --model claude-sonnet-4-6 --output-dir analysis/outputs_sonnet_4_6

Outputs (written to analysis/outputs_v3/):
    - layer_classifications.csv     : One row per project, all three layers
    - layer_a_by_year.csv           : Domain frequency by year
    - layer_b_by_year.csv           : Linkage mode frequency by year
    - layer_c_by_year.csv           : Analytical purpose frequency by year
    - layer_summary.txt             : Narrative analysis
    - llm_layer_cache.json          : Cache of raw LLM outputs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import textwrap
import time
from functools import lru_cache
from pathlib import Path

import anthropic
import pandas as pd
import yaml
from pydantic import BaseModel, Field, field_validator

try:
    from analysis.register_cleaning import CANDIDATE_FILES, DATA_DIR, clean_register_dataframe, load_raw_register
except ModuleNotFoundError:
    from register_cleaning import CANDIDATE_FILES, DATA_DIR, clean_register_dataframe, load_raw_register  # type: ignore


def _make_console_output_safe() -> None:
    """Prevent Unicode log output from crashing on legacy Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="backslashreplace")
            except (OSError, ValueError):
                pass


_make_console_output_safe()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs_v3")

CACHE_FILE = os.path.join(OUTPUT_DIR, "llm_layer_cache.json")
CACHE_SCHEMA_VERSION = 4
PROMPT_VERSION = "dict-1.0-rc1"

MODEL      = "claude-opus-4-8"
BATCH_SIZE = 10          # projects per LLM batch (reduced to improve Opus reliability)
MAX_TOKENS = 8192        # generous ceiling -- 20 projects x ~180 tokens/entry
MAX_RETRIES = 3          # retry transient API failures before giving up
RATIONALE_PLACEHOLDER = "(rationale not provided)"
LAST_PROMPT_CACHE_USAGE: dict[str, int | None] = {}
LAST_CLASSIFY_API_PATH = ""

# ---------------------------------------------------------------------------
# Taxonomy data dictionary
# ---------------------------------------------------------------------------

TAXONOMY_FILENAME = "taxonomy_data_dictionary.yaml"
LAYER_A_DOMAIN = "Layer A -- domain"
LAYER_B_LINKAGE = "Layer B -- linkage"
LAYER_C_PURPOSE = "Layer C -- purpose"
LAYER_CROSS_CUTTING_TAG = "Cross-cutting tag"
PROMPT_LAYERS = (LAYER_A_DOMAIN, LAYER_B_LINKAGE, LAYER_C_PURPOSE, LAYER_CROSS_CUTTING_TAG)


def _find_taxonomy_path() -> Path:
    """Locate the taxonomy dictionary by walking up from this file."""
    script_path = Path(__file__).resolve()
    for directory in script_path.parents:
        candidate = directory / TAXONOMY_FILENAME
        if candidate.is_file():
            return candidate
    expected = script_path.parent.parent / TAXONOMY_FILENAME
    raise FileNotFoundError(
        f"Taxonomy data dictionary not found. Expected {TAXONOMY_FILENAME} at {expected}"
    )


def _load_taxonomy_dictionary() -> dict:
    path = _find_taxonomy_path()
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise RuntimeError(f"Failed to parse taxonomy data dictionary at {path}") from e
    except OSError as e:
        raise RuntimeError(f"Failed to read taxonomy data dictionary at {path}") from e
    if not isinstance(data, dict):
        raise RuntimeError(f"Taxonomy data dictionary at {path} did not parse to a mapping")
    if not isinstance(data.get("categories"), list):
        raise RuntimeError(f"Taxonomy data dictionary at {path} is missing a categories list")
    if not isinstance(data.get("metadata"), dict):
        raise RuntimeError(f"Taxonomy data dictionary at {path} is missing a metadata block")
    return data


TAXONOMY_DATA = _load_taxonomy_dictionary()


def _flatten_dictionary_text(value: object) -> str:
    """Collapse YAML-folded whitespace without changing wording."""
    return " ".join(str(value or "").split()).strip()


def _in_prompt_category(category: dict, layer: str) -> bool:
    status = _flatten_dictionary_text(category.get("status")).lower()
    return (
        category.get("layer") == layer
        and category.get("include_in_prompt") is True
        and not status.startswith("removed")
    )


def _categories_for_layer(layer: str) -> list[dict]:
    return [
        category
        for category in TAXONOMY_DATA["categories"]
        if isinstance(category, dict) and _in_prompt_category(category, layer)
    ]


LAYER_CATEGORIES = {layer: _categories_for_layer(layer) for layer in PROMPT_LAYERS}


def _labels_for_layer(layer: str) -> list[str]:
    labels = []
    for category in LAYER_CATEGORIES[layer]:
        label = category.get("label")
        if not isinstance(label, str) or not label.strip():
            raise RuntimeError(f"Taxonomy category in {layer} is missing a label")
        labels.append(label)
    return labels


DOMAINS = _labels_for_layer(LAYER_A_DOMAIN)
LINKAGE_MODES = _labels_for_layer(LAYER_B_LINKAGE)
PURPOSES = _labels_for_layer(LAYER_C_PURPOSE)
CROSS_CUTTING_TAGS = _labels_for_layer(LAYER_CROSS_CUTTING_TAG)

DOMAIN_LABELS = set(DOMAINS)
LINKAGE_MODE_LABELS = set(LINKAGE_MODES)
PURPOSE_LABELS = set(PURPOSES)
CROSS_CUTTING_TAG_LABELS = set(CROSS_CUTTING_TAGS)


def _fallback_label_for_layer(layer: str) -> str:
    matches = [
        label
        for label in _labels_for_layer(layer)
        if label.lower().startswith("unclear ")
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one unclear fallback label for {layer}, found {matches}")
    return matches[0]


UNCLEAR_DOMAIN_LABEL = _fallback_label_for_layer(LAYER_A_DOMAIN)
UNCLEAR_LINKAGE_LABEL = _fallback_label_for_layer(LAYER_B_LINKAGE)
UNCLEAR_PURPOSE_LABEL = _fallback_label_for_layer(LAYER_C_PURPOSE)


def _render_category_guidance(category: dict) -> str:
    label = _flatten_dictionary_text(category.get("label"))
    definition = _flatten_dictionary_text(category.get("definition"))
    include = _flatten_dictionary_text(category.get("inclusion_rules"))
    exclude = _flatten_dictionary_text(category.get("exclusion_rules"))
    return "\n".join([
        label,
        f"  Definition: {definition}",
        f"  Include: {include}",
        f"  Exclude: {exclude}",
    ])


def _render_layer_guidance(layer: str) -> str:
    return "\n\n".join(_render_category_guidance(category) for category in LAYER_CATEGORIES[layer])


METADATA_RULE_KEYS = (
    "layer_a_assignment_rule",
    "layer_b_assignment_rule",
    "layer_c_assignment_rule",
    "unclear_fallback_rule",
)

def _metadata_rule_value(key: str) -> str:
    metadata = TAXONOMY_DATA["metadata"]
    if key not in metadata:
        raise RuntimeError(f"Taxonomy metadata is missing {key}")
    return _flatten_dictionary_text(metadata[key])


def _cross_layer_principle_values() -> list[str]:
    principles = TAXONOMY_DATA["metadata"].get("cross_layer_assignment_principles")
    if not isinstance(principles, dict):
        raise RuntimeError("Taxonomy metadata is missing cross_layer_assignment_principles")
    return [_flatten_dictionary_text(value) for value in principles.values()]


def _render_assignment_rules() -> str:
    lines = [_metadata_rule_value(key) for key in METADATA_RULE_KEYS]
    lines.extend(_cross_layer_principle_values())
    lines.append(_metadata_rule_value("methodology_domain_purpose_distinction"))
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------

class ProjectLayers(BaseModel):
    project_id: str
    substantive_domains: list[str]
    linkage_mode: str
    analytical_purpose: list[str]
    cross_cutting_tags: list[str] = Field(default_factory=list)
    rationale: str

    @field_validator("substantive_domains")
    @classmethod
    def clean_domains(cls, v):
        if not v:
            return [UNCLEAR_DOMAIN_LABEL]
        invalid = [d for d in v if d not in DOMAIN_LABELS]
        if invalid:
            raise ValueError(f"Unknown Layer A domain label(s): {invalid}")
        # Deduplicate while preserving order
        seen, deduped = set(), []
        for d in v:
            if d not in seen:
                seen.add(d)
                deduped.append(d)
        # Drop the unclear fallback if a real domain is present
        if len(deduped) > 1:
            deduped = [d for d in deduped if d != UNCLEAR_DOMAIN_LABEL] or [UNCLEAR_DOMAIN_LABEL]
        return deduped

    @field_validator("linkage_mode")
    @classmethod
    def validate_linkage_mode(cls, v):
        if v not in LINKAGE_MODE_LABELS:
            raise ValueError(f"Unknown Layer B linkage label: {v}")
        return v

    @field_validator("analytical_purpose")
    @classmethod
    def clean_purposes(cls, v):
        if not v:
            return [UNCLEAR_PURPOSE_LABEL]
        invalid = [p for p in v if p not in PURPOSE_LABELS]
        if invalid:
            raise ValueError(f"Unknown Layer C purpose label(s): {invalid}")
        # Deduplicate while preserving order, cap at 2
        seen, deduped = set(), []
        for p in v:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        deduped = deduped[:2]
        # Drop the unclear fallback if a real purpose is present
        if len(deduped) > 1:
            deduped = [p for p in deduped if p != UNCLEAR_PURPOSE_LABEL] or [UNCLEAR_PURPOSE_LABEL]
        return deduped

    @field_validator("cross_cutting_tags")
    @classmethod
    def clean_cross_cutting_tags(cls, v):
        if not v:
            return []
        seen, deduped = set(), []
        for tag in v:
            if tag in CROSS_CUTTING_TAG_LABELS and tag not in seen:
                seen.add(tag)
                deduped.append(tag)
        return deduped

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("rationale must be a non-empty string")
        return v.strip()


class BatchLayerResult(BaseModel):
    classifications: list[ProjectLayers]


class BatchClassificationError(RuntimeError):
    """Raised when a batch response cannot be safely accepted."""


# ---------------------------------------------------------------------------
# Label normalisation (for raw JSON fallback)
# ---------------------------------------------------------------------------

# Build lookup tables: lowercase → canonical label
_DOMAIN_LOOKUP = {d.lower(): d for d in DOMAINS}
_LINKAGE_LOOKUP = {m.lower(): m for m in LINKAGE_MODES}
_PURPOSE_LOOKUP = {p.lower(): p for p in PURPOSES}
_TAG_LOOKUP = {tag.lower(): tag for tag in CROSS_CUTTING_TAGS}

# Legacy linkage mode remapping (Multi-Domain folded into Cross-Domain)
_LINKAGE_LOOKUP["multi-domain linkage"] = "Cross-Domain Linkage"


def _normalise_label(value: str, lookup: dict) -> str | None:
    """Try to match a label to a canonical form. Returns None if no match."""
    v = value.strip()
    # Exact match
    if v in lookup.values():
        return v
    # Case-insensitive match
    low = v.lower()
    if low in lookup:
        return lookup[low]
    # Strip trailing/leading whitespace variants and common punctuation
    cleaned = low.strip(" .,;")
    if cleaned in lookup:
        return lookup[cleaned]
    return None


def _normalise_classification_dict(raw_dict: dict) -> dict:
    """
    Normalise label strings in a raw classification dict before Pydantic validation.
    Fixes case mismatches, cross-layer label swaps, and minor spelling variants.
    """
    if "classifications" not in raw_dict:
        return raw_dict

    for entry in raw_dict["classifications"]:
        # Normalise domains
        if "substantive_domains" in entry and isinstance(entry["substantive_domains"], list):
            normalised = []
            for d in entry["substantive_domains"]:
                canon = _normalise_label(d, _DOMAIN_LOOKUP)
                if canon:
                    normalised.append(canon)
                # else: drop unrecognised labels rather than failing
            entry["substantive_domains"] = normalised if normalised else [UNCLEAR_DOMAIN_LABEL]

        # Normalise linkage mode
        if "linkage_mode" in entry and isinstance(entry["linkage_mode"], str):
            canon = _normalise_label(entry["linkage_mode"], _LINKAGE_LOOKUP)
            if canon:
                entry["linkage_mode"] = canon
            else:
                entry["linkage_mode"] = UNCLEAR_LINKAGE_LABEL

        # Normalise purposes
        if "analytical_purpose" in entry and isinstance(entry["analytical_purpose"], list):
            normalised = []
            for p in entry["analytical_purpose"]:
                canon = _normalise_label(p, _PURPOSE_LOOKUP)
                if canon:
                    normalised.append(canon)
            entry["analytical_purpose"] = normalised if normalised else [UNCLEAR_PURPOSE_LABEL]

        # Normalise cross-cutting tags
        if "cross_cutting_tags" in entry and isinstance(entry["cross_cutting_tags"], list):
            normalised = []
            for tag in entry["cross_cutting_tags"]:
                canon = _normalise_label(tag, _TAG_LOOKUP)
                if canon:
                    normalised.append(canon)
            entry["cross_cutting_tags"] = normalised
        else:
            entry["cross_cutting_tags"] = []

        rationale = entry.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            project_id = entry.get("project_id", "<unknown>")
            print(f"  [warning] Missing rationale for {project_id}; using placeholder")
            entry["rationale"] = RATIONALE_PLACEHOLDER
        else:
            entry["rationale"] = rationale.strip()

    return raw_dict


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_data(data_dir: str = DATA_DIR) -> pd.DataFrame:
    df_raw, _source_file = load_raw_register(data_dir, CANDIDATE_FILES)
    df, _stats = clean_register_dataframe(df_raw, output_dir=OUTPUT_DIR)
    return df


def filter_to_record_ids(df: pd.DataFrame, record_ids_path: str) -> pd.DataFrame:
    """Restrict the dataset to record IDs listed in a CSV file."""
    subset = pd.read_csv(record_ids_path, encoding="utf-8-sig")
    if "Record ID" not in subset.columns:
        raise ValueError(f"{record_ids_path} must contain a 'Record ID' column")

    wanted_ids = subset["Record ID"].astype(str).dropna().tolist()
    out = df[df["Record ID"].astype(str).isin(wanted_ids)].copy()
    missing = sorted(set(wanted_ids) - set(out["Record ID"].astype(str)))
    if missing:
        raise ValueError(f"{len(missing)} Record ID(s) from {record_ids_path} were not found in the DEA data")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def load_cache(cache_path: str) -> dict:
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[cache] Corrupt cache file ({e}) - starting fresh")
            return {}
        if not isinstance(raw, dict) or "entries" not in raw:
            print("[cache] Unrecognised cache format - invalidating cache")
            return {}
        meta = raw.get("__meta__", {})
        if meta.get("cache_schema_version") != CACHE_SCHEMA_VERSION:
            print("[cache] Schema version mismatch - invalidating cache")
            return {}
        if meta.get("prompt_version") != PROMPT_VERSION:
            print(f"[cache] Prompt version changed ({meta.get('prompt_version')} -> {PROMPT_VERSION}) "
                  f"- invalidating cache")
            return {}
        if meta.get("model") != MODEL:
            print(f"[cache] Model changed ({meta.get('model')} -> {MODEL}) "
                  f"- invalidating cache")
            return {}
        return raw.get("entries", {})
    return {}


def save_cache(cache: dict, cache_path: str):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    payload = {
        "__meta__": {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "prompt_version": PROMPT_VERSION,
            "model": MODEL,
        },
        "entries": cache,
    }
    cache_dir = os.path.dirname(cache_path)
    fd, tmp_path = tempfile.mkstemp(prefix="llm_layer_cache_", suffix=".json", dir=cache_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, cache_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

def _sanitise_prompt_text(value: str) -> str:
    """Normalise text before inserting it into the prompt."""
    text = " ".join(str(value).split())
    text = text.replace("```", "'''")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("[", "(").replace("]", ")")
    return text.strip()


def _summarise_datasets(raw: str, max_chars: int = 600) -> str:
    """Produce a concise, prompt-safe summary of the 'Datasets Used' field."""
    if not isinstance(raw, str) or not raw.strip():
        return "(no datasets listed)"
    # Register text cleaning is owned by clean_register_dataframe(); this only
    # flattens the cleaned dataset field for compact prompt display.
    text = " ".join(raw.split())
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    text = _sanitise_prompt_text(text)
    return text

def _build_projects_block(projects: list[dict]) -> str:
    numbered = "\n".join(
        f'{i + 1}. [{p["prompt_id"]}] Title: {p["prompt_title"]} | Datasets: {p["prompt_datasets"]}'
        for i, p in enumerate(projects)
    )
    return "\n".join([
        "══════════════════════════════════════════════════════════════",
        "PROJECTS TO CLASSIFY",
        "══════════════════════════════════════════════════════════════",
        numbered,
    ])


@lru_cache(maxsize=1)
def _build_static_prompt() -> str:
    prompt = textwrap.dedent("""
        You are a research classification expert specialising in UK administrative data research.
        Classify each project below using three independent layers plus cross-cutting tags.
        Each project shows a title and the datasets it accesses.

        ══════════════════════════════════════════════════════════════
        LAYER A — SUBSTANTIVE DOMAIN  (assign 1 or more)
        ══════════════════════════════════════════════════════════════
        __DOMAIN_GUIDANCE__

        ══════════════════════════════════════════════════════════════
        LAYER B — LINKAGE MODE  (assign exactly 1)
        ══════════════════════════════════════════════════════════════
        __LINKAGE_GUIDANCE__

        ══════════════════════════════════════════════════════════════
        LAYER C — ANALYTICAL PURPOSE  (assign 1 or 2)
        ══════════════════════════════════════════════════════════════
        __PURPOSE_GUIDANCE__

        ══════════════════════════════════════════════════════════════
        CROSS-CUTTING TAGS  (assign zero or more)
        ══════════════════════════════════════════════════════════════
        __TAG_GUIDANCE__

        ══════════════════════════════════════════════════════════════
        CLASSIFICATION RULES
        ══════════════════════════════════════════════════════════════
        __ASSIGNMENT_RULES__

        Respond with a JSON object matching this schema exactly:
        {
          "classifications": [
            {
              "project_id": "<Record ID shown in brackets, e.g. 2020/001>",
              "substantive_domains": ["<domain>", ...],
              "linkage_mode": "<exactly one linkage mode>",
              "analytical_purpose": ["<purpose>"],
              "cross_cutting_tags": ["<tag>", ...],
              "rationale": "Assigned <domains> because <evidence>; <linkage> because <evidence>; <purpose> because <evidence>; <tag or no tag> because <evidence>."
            },
            ...
          ]
        }

        The "project_id" field must repeat the exact Record ID shown in brackets
        for each project (e.g. "2020/001" or "2023/045").
        Use only the labels defined above, spelled exactly as shown.
        The "cross_cutting_tags" list may be empty ([]); assign tags independently
        of the other layers.
        For each project, also provide a "rationale" field: a single concise
        sentence explaining each layer's assignment in turn. Use the structure:
        "Assigned <domains> because <evidence>; <linkage> because <evidence>;
        <purpose> because <evidence>; <tag or no tag> because <evidence>."
        The rationale should cite specific evidence from the title and dataset
        field, not restate the category definition.
        Produce one entry per project in the same order as listed.
    """).strip()
    return (
        prompt
        .replace("__DOMAIN_GUIDANCE__", _render_layer_guidance(LAYER_A_DOMAIN))
        .replace("__LINKAGE_GUIDANCE__", _render_layer_guidance(LAYER_B_LINKAGE))
        .replace("__PURPOSE_GUIDANCE__", _render_layer_guidance(LAYER_C_PURPOSE))
        .replace("__TAG_GUIDANCE__", _render_layer_guidance(LAYER_CROSS_CUTTING_TAG))
        .replace("__ASSIGNMENT_RULES__", _render_assignment_rules())
    )


def _build_prompt(projects: list[dict]) -> str:
    return f"{_build_static_prompt()}\n\n{_build_projects_block(projects)}"


def _build_prompt_messages(projects: list[dict]) -> list[dict]:
    return [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": _build_static_prompt(),
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": _build_projects_block(projects),
            },
        ],
    }]


def _parse_raw_json(raw: str, projects: list[dict]) -> dict:
    """Extract JSON from response, with fallback extraction."""
    text = raw.strip()

    # Strip markdown fences if present
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if m:
            text = m.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]+\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    raise BatchClassificationError("Could not parse JSON from LLM response")


def _record_prompt_cache_usage(response) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    cache_creation = getattr(usage, "cache_creation_input_tokens", None)
    cache_read = getattr(usage, "cache_read_input_tokens", None)
    LAST_PROMPT_CACHE_USAGE.clear()
    LAST_PROMPT_CACHE_USAGE.update({
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
    })
    print(
        "  [prompt-cache] "
        f"cache_creation_input_tokens={cache_creation}; "
        f"cache_read_input_tokens={cache_read}"
    )
    return dict(LAST_PROMPT_CACHE_USAGE)


def _validate_batch_integrity(
    classifications: list[ProjectLayers],
    projects: list[dict],
) -> None:
    """Check that the LLM returned exactly the IDs we asked for.

    The prompt shows sanitised ``prompt_id`` values to the LLM, so the
    returned ``project_id`` fields are compared against those.
    """
    expected_ids = [p["prompt_id"] for p in projects]
    expected_set = set(expected_ids)
    seen = set()
    duplicate_ids = set()
    unexpected_ids = set()

    for cls in classifications:
        if cls.project_id not in expected_set:
            unexpected_ids.add(cls.project_id)
            continue
        if cls.project_id in seen:
            duplicate_ids.add(cls.project_id)
            continue
        seen.add(cls.project_id)

    missing_ids = [pid for pid in expected_ids if pid not in seen]
    problems = []
    if unexpected_ids:
        problems.append(f"unexpected IDs: {sorted(unexpected_ids)}")
    if duplicate_ids:
        problems.append(f"duplicate IDs: {sorted(duplicate_ids)}")
    if missing_ids:
        problems.append(f"missing IDs: {missing_ids}")
    if problems:
        raise BatchClassificationError("; ".join(problems))


def classify_batch(client: anthropic.Anthropic, projects: list[dict]) -> dict:
    """
    Returns dict: project_id -> classification fields.
    """
    global LAST_CLASSIFY_API_PATH

    messages = _build_prompt_messages(projects)

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
            output_format=BatchLayerResult,
        )
        _record_prompt_cache_usage(response)
        LAST_CLASSIFY_API_PATH = "messages.parse"
        result_obj: BatchLayerResult = response.parsed_output
        classifications = result_obj.classifications
    except Exception as e:
        print(f"  [warning] Structured parse failed ({e}); falling back to raw JSON")
        raw_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=messages,
        )
        _record_prompt_cache_usage(raw_response)
        LAST_CLASSIFY_API_PATH = "messages.create fallback"
        if not raw_response.content or not hasattr(raw_response.content[0], "text"):
            raise RuntimeError("API returned empty or non-text response content")
        raw_text = raw_response.content[0].text
        raw_dict = _parse_raw_json(raw_text, projects)
        raw_dict = _normalise_classification_dict(raw_dict)

        try:
            result_obj = BatchLayerResult(**raw_dict)
            classifications = result_obj.classifications
        except Exception as e2:
            raise BatchClassificationError(f"Pydantic validation failed: {e2}") from e2

    # Deduplicate: keep first occurrence of each project_id
    seen_ids: set[str] = set()
    deduped: list[ProjectLayers] = []
    for cls in classifications:
        if cls.project_id not in seen_ids:
            seen_ids.add(cls.project_id)
            deduped.append(cls)
    if len(deduped) < len(classifications):
        n_dropped = len(classifications) - len(deduped)
        print(f"  [info] Dropped {n_dropped} duplicate classification(s) from LLM response")
    classifications = deduped

    _validate_batch_integrity(classifications, projects)
    prompt_to_actual = {p["prompt_id"]: p["id"] for p in projects}

    # Build output dict
    out = {}
    for cls in classifications:
        actual_id = prompt_to_actual[cls.project_id]
        out[actual_id] = {
            "substantive_domains": cls.substantive_domains,
            "linkage_mode":        cls.linkage_mode,
            "analytical_purpose":  cls.analytical_purpose,
            "cross_cutting_tags":  cls.cross_cutting_tags,
            "rationale":           cls.rationale,
        }

    return out


def classify_all(df: pd.DataFrame, client: anthropic.Anthropic) -> pd.DataFrame:
    """Classify all projects, using cache to skip already-classified ones."""
    cache = load_cache(CACHE_FILE)
    valid_ids = set(df["Record ID"].astype(str))
    cache = {k: v for k, v in cache.items() if k in valid_ids}

    to_classify = [
        {
            "id": str(row["Record ID"]),
            "title": row["Title"],
            "prompt_title": _sanitise_prompt_text(row["Title"]),
            "prompt_datasets": _summarise_datasets(row.get("Datasets Used", "")),
        }
        for _, row in df.iterrows()
        if str(row["Record ID"]) not in cache
    ]

    print(f"[llm] {len(cache):,} projects cached; {len(to_classify):,} to classify")

    if to_classify:
        failed_batches = []
        n_batches = (len(to_classify) - 1) // BATCH_SIZE + 1
        for i in range(0, len(to_classify), BATCH_SIZE):
            batch = to_classify[i: i + BATCH_SIZE]
            batch = [
                {
                    **project,
                    "prompt_id": project["id"],
                }
                for project in batch
            ]
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{n_batches} ({len(batch)} projects)...")

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    results = classify_batch(client, batch)
                    cache.update(results)
                    save_cache(cache, CACHE_FILE)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        wait = 2 ** attempt
                        print(f"  [retry] Attempt {attempt}/{MAX_RETRIES} failed ({e}); "
                              f"retrying in {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"  [error] Batch {batch_num} failed after {MAX_RETRIES} "
                              f"attempts: {e}")
                        failed_batches.append(batch_num)

            time.sleep(0.5)

        if failed_batches:
            n_failed = len(failed_batches)
            raise RuntimeError(
                f"{n_failed} batch(es) failed after {MAX_RETRIES} retries each "
                f"(batches: {failed_batches}). Successfully classified batches "
                f"have been cached — re-run to retry only the failed ones."
            )

    # Attach to DataFrame
    df = df.copy()

    def _get(record_id, key, default):
        entry = cache.get(str(record_id))
        if isinstance(entry, dict):
            return entry.get(key, default)
        return default

    df["substantive_domains"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "substantive_domains", [UNCLEAR_DOMAIN_LABEL])
    )
    df["linkage_mode"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "linkage_mode", UNCLEAR_LINKAGE_LABEL)
    )
    df["analytical_purpose"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "analytical_purpose", [UNCLEAR_PURPOSE_LABEL])
    )
    df["cross_cutting_tags"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "cross_cutting_tags", [])
    )
    df["rationale"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "rationale", RATIONALE_PLACEHOLDER)
    )
    # Preserve the existing primary-domain summary convention.
    df["primary_domain"] = df["substantive_domains"].apply(
        lambda x: x[0] if x else UNCLEAR_DOMAIN_LABEL
    )

    return df


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse_layers(df: pd.DataFrame) -> dict:
    """Compute frequency tables for all three layers."""
    # Use Record ID as the unique identifier (handles duplicate Project IDs
    # that were disambiguated by title in load_data).
    rid = "Record ID"

    # ---- Layer A: domains (exploded, multiple per project) ----
    df_a = df.explode("substantive_domains").rename(columns={"substantive_domains": "domain"})
    by_year_a = (
        df_a.groupby(["Year", "domain"])[rid].count()
        .reset_index().rename(columns={rid: "count"})
    )
    total_a = df.groupby("Year")[rid].count().rename("total")
    by_year_a = by_year_a.merge(total_a, on="Year")
    # NB: multi-label — percentages can sum above 100% across domains in a year
    by_year_a["pct_of_projects"] = (by_year_a["count"] / by_year_a["total"] * 100).round(1)

    totals_a = (
        df_a.groupby("domain")[rid].count()
        .reset_index().rename(columns={rid: "count"})
        .sort_values("count", ascending=False)
    )

    # ---- Layer B: linkage mode (one per project) ----
    by_year_b = (
        df.groupby(["Year", "linkage_mode"])[rid].count()
        .reset_index().rename(columns={rid: "count"})
    )
    by_year_b = by_year_b.merge(total_a, on="Year")
    by_year_b["pct_of_projects"] = (by_year_b["count"] / by_year_b["total"] * 100).round(1)

    totals_b = (
        df.groupby("linkage_mode")[rid].count()
        .reset_index().rename(columns={rid: "count"})
        .sort_values("count", ascending=False)
    )

    # ---- Layer C: purpose (exploded, 1-2 per project) ----
    df_c = df.explode("analytical_purpose").rename(columns={"analytical_purpose": "purpose"})
    by_year_c = (
        df_c.groupby(["Year", "purpose"])[rid].count()
        .reset_index().rename(columns={rid: "count"})
    )
    by_year_c = by_year_c.merge(total_a, on="Year")
    # NB: multi-label — percentages can sum above 100% across purposes in a year
    by_year_c["pct_of_projects"] = (by_year_c["count"] / by_year_c["total"] * 100).round(1)

    totals_c = (
        df_c.groupby("purpose")[rid].count()
        .reset_index().rename(columns={rid: "count"})
        .sort_values("count", ascending=False)
    )

    # ---- Cross-tabulations (multi-label: one count per assigned domain, all
    # domains shown — Layer A is non-hierarchical, so there is no "primary"
    # domain to key on) ----
    # reset_index after explode: duplicate index labels make pd.crosstab raise on newer pandas
    df_dom = df.explode("substantive_domains").rename(columns={"substantive_domains": "domain"})
    df_dom = df_dom[df_dom["domain"].notna()].reset_index(drop=True)

    # Domain × linkage mode
    cross_mode_domain = pd.crosstab(df_dom["domain"], df_dom["linkage_mode"])

    # Domain × analytical purpose (both multi-label, exploded)
    df_dp = df_dom.explode("analytical_purpose").rename(
        columns={"analytical_purpose": "purpose"}
    ).reset_index(drop=True)
    cross_domain_purpose = pd.crosstab(df_dp["domain"], df_dp["purpose"])

    return {
        "by_year_a":            by_year_a,
        "totals_a":             totals_a,
        "by_year_b":            by_year_b,
        "totals_b":             totals_b,
        "by_year_c":            by_year_c,
        "totals_c":             totals_c,
        "cross_mode_domain":    cross_mode_domain,
        "cross_domain_purpose": cross_domain_purpose,
    }


# ---------------------------------------------------------------------------
# Quick print
# ---------------------------------------------------------------------------

def print_quick_stats(trends: dict):
    print("\n=== Layer A — Substantive Domain Totals ===")
    print(trends["totals_a"].to_string(index=False))

    print("\n=== Layer B — Linkage Mode Totals ===")
    print(trends["totals_b"].to_string(index=False))

    print("\n=== Layer C — Analytical Purpose Totals ===")
    print(trends["totals_c"].to_string(index=False))

    print("\n=== Cross-tab: Linkage Mode × Substantive Domain ===")
    print(trends["cross_mode_domain"].to_string())

    print("\n=== Cross-tab: Substantive Domain × Analytical Purpose ===")
    print(trends["cross_domain_purpose"].to_string())


# ---------------------------------------------------------------------------
# Narrative summary
# ---------------------------------------------------------------------------

def generate_narrative(
    client: anthropic.Anthropic,
    trends: dict,
    n_projects: int,
) -> str:
    a_str = trends["totals_a"].to_string(index=False)
    b_str = trends["totals_b"].to_string(index=False)
    c_str = trends["totals_c"].to_string(index=False)
    cross_mode_str = trends["cross_mode_domain"].to_string()
    cross_purpose_str = trends["cross_domain_purpose"].to_string()

    year_a_pivot = (
        trends["by_year_a"]
        .pivot(index="Year", columns="domain", values="pct_of_projects")
        .fillna(0).round(1)
    ).to_string()

    year_b_pivot = (
        trends["by_year_b"]
        .pivot(index="Year", columns="linkage_mode", values="pct_of_projects")
        .fillna(0).round(1)
    ).to_string()

    year_c_pivot = (
        trends["by_year_c"]
        .pivot(index="Year", columns="purpose", values="pct_of_projects")
        .fillna(0).round(1)
    ).to_string()

    prompt = textwrap.dedent(f"""
        You are a research policy analyst. Below are statistics from a three-layer
        classification of {n_projects:,} DEA-accredited research projects in the UK.

        LAYER A — SUBSTANTIVE DOMAIN TOTALS:
        {a_str}

        LAYER A — DOMAIN % BY YEAR (% of projects mentioning each domain; multi-domain
        projects are counted once per domain, so columns may sum above 100%):
        {year_a_pivot}

        LAYER B — LINKAGE MODE TOTALS:
        {b_str}

        LAYER B — LINKAGE MODE % BY YEAR (mutually exclusive; columns sum to 100%):
        {year_b_pivot}

        LAYER C — ANALYTICAL PURPOSE TOTALS:
        {c_str}

        LAYER C — PURPOSE % BY YEAR (projects may have 1–2 purposes, so columns
        may sum above 100%):
        {year_c_pivot}

        LINKAGE MODE × SUBSTANTIVE DOMAIN CROSS-TAB (multi-label; a project is
        counted once per assigned domain, so columns can exceed project totals):
        {cross_mode_str}

        SUBSTANTIVE DOMAIN × ANALYTICAL PURPOSE CROSS-TAB (multi-label):
        {cross_purpose_str}

        Write a concise analytical summary (5–7 paragraphs) covering:
        1. The dominant substantive domains and how the research landscape has evolved
        2. Trends in data linkage complexity — are projects becoming more cross-domain over time?
        3. The main analytical purposes and which are growing or declining
        4. Interesting combinations revealed by the cross-tabs (e.g. which domains favour
           policy evaluation, or which domains rely most on cross-domain linkage?)
        5. Domains or purposes with notably low or declining share — flag these as
           under-represented areas visible in the data (do not speculate about why)

        Write in a professional policy-briefing style, suitable for a senior civil servant audience.
        STRICT RULES:
        • Cite exact numbers and percentages from the tables above — do not round, smooth,
          or invent ranges.
        • Only describe patterns that are directly visible in the tables. Do not speculate
          about causes, motivations, or external factors (e.g. "reflecting the post-pandemic
          equity agenda").
        • Do not editorialize or make recommendations. The summary should be a factual
          description of what the data shows, not an interpretation of what it means.
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    if not response.content or not hasattr(response.content[0], "text"):
        raise RuntimeError("Narrative generation failed: API returned empty or non-text response")
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------

def _build_inspection_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Build a spreadsheet-friendly CSV with one boolean column per domain/purpose/tag."""
    out = df[["Project ID", "Record ID", "Title", "Datasets Used",
              "Accreditation Date", "Year"]].copy()

    # Layer A — one boolean column per domain
    for domain in DOMAINS:
        col = f"domain: {domain}"
        out[col] = df["substantive_domains"].apply(
            lambda x: 1 if isinstance(x, list) and domain in x else 0
        )
    out["primary_domain"] = df["primary_domain"]

    # Layer B — single column
    out["linkage_mode"] = df["linkage_mode"]

    # Layer C — one boolean column per purpose
    for purpose in PURPOSES:
        col = f"purpose: {purpose}"
        out[col] = df["analytical_purpose"].apply(
            lambda x: 1 if isinstance(x, list) and purpose in x else 0
        )

    # Cross-cutting tags — one boolean column per tag
    tag_values = df["cross_cutting_tags"] if "cross_cutting_tags" in df else pd.Series([[]] * len(df), index=df.index)
    for tag in CROSS_CUTTING_TAGS:
        col = f"tag: {tag}"
        out[col] = tag_values.apply(
            lambda x: 1 if isinstance(x, list) and tag in x else 0
        )

    out["rationale"] = df["rationale"] if "rationale" in df else RATIONALE_PLACEHOLDER

    return out


def save_outputs(df: pd.DataFrame, trends: dict, narrative: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # Flat CSV — lists as semicolon-separated strings
    df_out = df.copy()
    df_out["substantive_domains"] = df_out["substantive_domains"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )
    df_out["analytical_purpose"] = df_out["analytical_purpose"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )
    if "cross_cutting_tags" not in df_out:
        df_out["cross_cutting_tags"] = [[] for _ in range(len(df_out))]
    df_out["cross_cutting_tags"] = df_out["cross_cutting_tags"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )
    if "rationale" not in df_out:
        df_out["rationale"] = RATIONALE_PLACEHOLDER
    df_out.to_csv(
        os.path.join(output_dir, "layer_classifications.csv"),
        index=False, encoding="utf-8-sig",
    )

    # Inspection-friendly CSV with boolean columns
    df_inspect = _build_inspection_csv(df)
    df_inspect.to_csv(
        os.path.join(output_dir, "all_projects_classified.csv"),
        index=False, encoding="utf-8-sig",
    )

    trends["by_year_a"].to_csv(
        os.path.join(output_dir, "layer_a_by_year.csv"), index=False, encoding="utf-8-sig"
    )
    trends["by_year_b"].to_csv(
        os.path.join(output_dir, "layer_b_by_year.csv"), index=False, encoding="utf-8-sig"
    )
    trends["by_year_c"].to_csv(
        os.path.join(output_dir, "layer_c_by_year.csv"), index=False, encoding="utf-8-sig"
    )
    trends["totals_a"].to_csv(
        os.path.join(output_dir, "layer_a_totals.csv"), index=False, encoding="utf-8-sig"
    )
    trends["totals_b"].to_csv(
        os.path.join(output_dir, "layer_b_totals.csv"), index=False, encoding="utf-8-sig"
    )
    trends["totals_c"].to_csv(
        os.path.join(output_dir, "layer_c_totals.csv"), index=False, encoding="utf-8-sig"
    )
    trends["cross_mode_domain"].to_csv(
        os.path.join(output_dir, "cross_mode_domain.csv"), encoding="utf-8-sig"
    )
    trends["cross_domain_purpose"].to_csv(
        os.path.join(output_dir, "cross_domain_purpose.csv"), encoding="utf-8-sig"
    )

    with open(os.path.join(output_dir, "layer_summary.txt"), "w", encoding="utf-8") as f:
        f.write(narrative)

    print(f"\n[output] Files saved to {output_dir}/")
    for name in [
        "all_projects_classified.csv",
        "layer_classifications.csv",
        "layer_a_by_year.csv", "layer_b_by_year.csv", "layer_c_by_year.csv",
        "layer_a_totals.csv", "layer_b_totals.csv", "layer_c_totals.csv",
        "cross_mode_domain.csv", "cross_domain_purpose.csv", "layer_summary.txt",
    ]:
        print(f"  - {name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Three-layer DEA thematic analysis")
    parser.add_argument(
        "--model",
        default=MODEL,
        help="Anthropic model ID to use for classification and narrative generation",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Directory to write outputs and cache into",
    )
    parser.add_argument(
        "--record-ids-csv",
        default=None,
        help="Optional CSV containing a 'Record ID' column to restrict the run to a fixed subset",
    )
    parser.add_argument(
        "--skip-narrative",
        action="store_true",
        help="Skip the narrative summary call and save an empty layer_summary.txt",
    )
    args = parser.parse_args()

    MODEL = args.model
    OUTPUT_DIR = args.output_dir
    CACHE_FILE = os.path.join(OUTPUT_DIR, "llm_layer_cache.json")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Set it with:  set ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Load data
    df = load_data()
    if args.record_ids_csv:
        df = filter_to_record_ids(df, args.record_ids_csv)
    print(f"[data] {len(df):,} DEA projects, {df['Year'].min()}-{df['Year'].max()}")

    # Classify
    df_classified = classify_all(df, client)

    # Analyse
    print("\n[analysis] Computing layer frequency tables...")
    trends = analyse_layers(df_classified)
    print_quick_stats(trends)

    # Narrative
    if args.skip_narrative:
        narrative = ""
        print("\n[llm] Skipping narrative summary (--skip-narrative)")
    else:
        print("\n[llm] Generating narrative summary...")
        narrative = generate_narrative(client, trends, n_projects=len(df_classified))
        print("\n--- NARRATIVE SUMMARY ---")
        print(narrative)

    # Save
    save_outputs(df_classified, trends, narrative, OUTPUT_DIR)
    print("\n[done]")
