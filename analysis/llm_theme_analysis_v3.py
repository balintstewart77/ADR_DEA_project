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

Outputs (written to analysis/outputs_v3/):
    - layer_classifications.csv     : One row per project, all three layers
    - layer_a_by_year.csv           : Domain frequency by year
    - layer_b_by_year.csv           : Linkage mode frequency by year
    - layer_c_by_year.csv           : Analytical purpose frequency by year
    - layer_summary.txt             : Narrative analysis
    - llm_layer_cache.json          : Cache of raw LLM outputs
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import textwrap
import time
from typing import Literal

import anthropic
import pandas as pd
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs_v3")

CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

SPECIAL_DROP_PROJECT_TITLE_PAIRS = {
    ("2023/113", "The Influence of Early Life Health and Nutritional Environment on Later Life Health and Morbidity"),
}

CACHE_FILE = os.path.join(OUTPUT_DIR, "llm_layer_cache.json")
CACHE_SCHEMA_VERSION = 2

MODEL      = "claude-opus-4-6"
BATCH_SIZE = 30          # conservative to stay within output token budget
MAX_TOKENS = 8192        # generous ceiling -- 30 projects x ~120 tokens/entry
MAX_RETRIES = 3          # retry transient API failures before giving up

# ---------------------------------------------------------------------------
# Layer A — Substantive Domains
# ---------------------------------------------------------------------------

DOMAINS = [
    "Labour Market & Employment",
    "Education & Skills",
    "Health & Social Care",
    "Crime & Justice",
    "Business & Productivity",
    "Poverty, Inequality & Living Standards",
    "Housing & Planning",
    "Migration & Demographics",
    "Environment & Agriculture",
    "Public Finance & Taxation",
    "Gender, Race & Ethnicity",
    "COVID-19 & Pandemic",
    "Data Infrastructure & Methodology",
    "Other",
]

DOMAIN_GUIDANCE = textwrap.dedent("""
  1.  Labour Market & Employment    — wages, jobs, unemployment, occupational mobility, gig economy
  2.  Education & Skills            — schools, colleges, universities, qualifications, apprenticeships, childcare
  3.  Health & Social Care          — NHS, hospitals, GP, mental health, social care, clinical outcomes, mortality
  4.  Crime & Justice               — policing, courts, prison, reoffending, victimisation, criminal records
  5.  Business & Productivity       — firms, innovation, trade, R&D, productivity, start-ups
  6.  Poverty, Inequality & Living Standards — income, benefits, deprivation, food security, debt
  7.  Housing & Planning            — housing tenure, homelessness, planning, neighbourhoods
  8.  Migration & Demographics      — migration flows, ethnicity, population, fertility, mortality
  9.  Environment & Agriculture     — pollution, land use, farming, energy, climate adaptation
  10. Public Finance & Taxation     — tax compliance, public spending, fiscal policy
  11. Gender, Race & Ethnicity      — gender gaps, racial disparities as primary focus (not incidental)
  12. COVID-19 & Pandemic           — COVID-19 transmission, vaccination, lockdown impacts
  13. Data Infrastructure & Methodology — record linkage methods, data quality, survey methodology
  14. Other                         — genuinely uncategorisable; use sparingly
""").strip()

# ---------------------------------------------------------------------------
# Layer B — Linkage Mode
# ---------------------------------------------------------------------------

LINKAGE_MODES = [
    "Single-Dataset",
    "Within-Domain Linkage",
    "Cross-Domain Linkage",
    "Multi-Domain Linkage",
    "Unclear from Title",
]

LINKAGE_GUIDANCE = textwrap.dedent("""
  Single-Dataset        — project uses only one administrative dataset; no record linkage implied
  Within-Domain Linkage — links 2+ datasets from the same domain (e.g. two education datasets,
                          or two health registries)
  Cross-Domain Linkage  — links datasets from exactly two distinct domains (e.g. education ↔ employment,
                          or health ↔ crime)
  Multi-Domain Linkage  — links datasets spanning three or more distinct domains
  Unclear from Title    — the title does not give enough information to judge linkage

  Classify what the project *does*, not what data *exist*.  If the title mentions only one
  outcome and one exposure from the same sector, choose Within-Domain Linkage.
  If the title clearly bridges two sectors (e.g. "school attainment and labour market outcomes"),
  choose Cross-Domain Linkage.
""").strip()

# ---------------------------------------------------------------------------
# Layer C — Analytical Purpose
# ---------------------------------------------------------------------------

PURPOSES = [
    "Descriptive Monitoring",
    "Outcome Linkage",
    "Life-Course / Trajectory Analysis",
    "Inequality / Disparities Analysis",
    "Service Interaction / Systems Analysis",
    "Policy Evaluation / Impact Analysis",
    "Risk Prediction / Early Identification",
    "Methodological / Infrastructure Research",
    "Unclear from Title",
]

PURPOSE_GUIDANCE = textwrap.dedent("""
  Descriptive Monitoring            — measuring prevalence, trends, or patterns without causal claim
  Outcome Linkage                   — linking an exposure/condition to a downstream outcome
  Life-Course / Trajectory Analysis — tracking individuals over time (childhood → adulthood arcs)
  Inequality / Disparities Analysis — comparing outcomes across social groups as the primary aim
  Service Interaction / Systems Analysis — how individuals interact with public services (NHS, DWP, courts)
  Policy Evaluation / Impact Analysis   — evaluating a specific policy, programme, or intervention
  Risk Prediction / Early Identification — building risk scores or identifying at-risk subgroups
  Methodological / Infrastructure Research — developing or validating data linkage methods / datasets
  Unclear from Title                — insufficient information in the title

  Assign 1 or 2 purposes.  Most projects have exactly 1; assign 2 only when both are clearly
  central and not redundant (e.g. "Inequality / Disparities Analysis" + "Policy Evaluation").
""").strip()

# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------

DOMAIN_LITERALS  = Literal[
    "Labour Market & Employment",
    "Education & Skills",
    "Health & Social Care",
    "Crime & Justice",
    "Business & Productivity",
    "Poverty, Inequality & Living Standards",
    "Housing & Planning",
    "Migration & Demographics",
    "Environment & Agriculture",
    "Public Finance & Taxation",
    "Gender, Race & Ethnicity",
    "COVID-19 & Pandemic",
    "Data Infrastructure & Methodology",
    "Other",
]

LINKAGE_LITERALS = Literal[
    "Single-Dataset",
    "Within-Domain Linkage",
    "Cross-Domain Linkage",
    "Multi-Domain Linkage",
    "Unclear from Title",
]

PURPOSE_LITERALS = Literal[
    "Descriptive Monitoring",
    "Outcome Linkage",
    "Life-Course / Trajectory Analysis",
    "Inequality / Disparities Analysis",
    "Service Interaction / Systems Analysis",
    "Policy Evaluation / Impact Analysis",
    "Risk Prediction / Early Identification",
    "Methodological / Infrastructure Research",
    "Unclear from Title",
]


class ProjectLayers(BaseModel):
    project_id: str
    substantive_domains: list[DOMAIN_LITERALS]
    linkage_mode: LINKAGE_LITERALS
    analytical_purpose: list[PURPOSE_LITERALS]

    @field_validator("substantive_domains")
    @classmethod
    def clean_domains(cls, v):
        if not v:
            return ["Other"]
        # Deduplicate while preserving order
        seen, deduped = set(), []
        for d in v:
            if d not in seen:
                seen.add(d)
                deduped.append(d)
        # Drop "Other" if a real domain is present
        if len(deduped) > 1:
            deduped = [d for d in deduped if d != "Other"] or ["Other"]
        return deduped

    @field_validator("analytical_purpose")
    @classmethod
    def clean_purposes(cls, v):
        if not v:
            return ["Unclear from Title"]
        # Deduplicate while preserving order, cap at 2
        seen, deduped = set(), []
        for p in v:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        deduped = deduped[:2]
        # Drop "Unclear from Title" if a real purpose is present
        if len(deduped) > 1:
            deduped = [p for p in deduped if p != "Unclear from Title"] or ["Unclear from Title"]
        return deduped


class BatchLayerResult(BaseModel):
    classifications: list[ProjectLayers]


class BatchClassificationError(RuntimeError):
    """Raised when a batch response cannot be safely accepted."""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def apply_duplicate_policy(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().drop_duplicates().reset_index(drop=True)
    out["_title_key"] = out["Title"].fillna("").astype(str).str.strip()
    special_mask = out.apply(
        lambda row: (str(row["Project ID"]), row["_title_key"]) in SPECIAL_DROP_PROJECT_TITLE_PAIRS,
        axis=1,
    )
    out = out.loc[~special_mask].copy()
    out = out.drop_duplicates(subset=["Project ID", "_title_key"], keep="first").reset_index(drop=True)
    return out.drop(columns="_title_key")

def load_data(data_dir: str = DATA_DIR) -> pd.DataFrame:
    for fname in CANDIDATE_FILES:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(f"[data] Loaded {len(df):,} rows from {fname}")
            break
    else:
        raise FileNotFoundError("No DEA projects CSV found in data/")

    df = df.rename(columns={
        "Project Number": "Project ID",
        "Project Name":   "Title",
        "Accredited Researchers": "Researchers",
        "Legal Gateway":  "Legal Basis",
        "Protected Data Accessed": "Datasets Used",
        "Processing Environment":  "Secure Research Service",
    })

    df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    df = df.dropna(subset=["Accreditation Date", "Title"])

    if "Legal Basis" in df.columns:
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]

    df = apply_duplicate_policy(df)
    title_key = df["Title"].fillna("").astype(str).str.strip()
    duplicated_ids = df["Project ID"].duplicated(keep=False)
    df["Record ID"] = df["Project ID"].astype(str)
    df.loc[duplicated_ids, "Record ID"] = (
        df.loc[duplicated_ids, "Project ID"].astype(str)
        + " :: "
        + title_key.loc[duplicated_ids]
    )
    df["Year"]         = df["Accreditation Date"].dt.year
    df["Quarter"]      = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Caching helpers
# ---------------------------------------------------------------------------

def load_cache(cache_path: str) -> dict:
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[cache] Corrupt cache file ({e}) — starting fresh")
            return {}
        if not isinstance(raw, dict) or "entries" not in raw:
            print("[cache] Unrecognised cache format — invalidating cache")
            return {}
        meta = raw.get("__meta__", {})
        if meta.get("cache_schema_version") != CACHE_SCHEMA_VERSION:
            print("[cache] Schema version mismatch — invalidating cache")
            return {}
        if meta.get("model") != MODEL:
            print(f"[cache] Model changed ({meta.get('model')} → {MODEL}) "
                  f"— invalidating cache")
            return {}
        return raw.get("entries", {})
    return {}


def save_cache(cache: dict, cache_path: str):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    payload = {
        "__meta__": {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
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


def _build_prompt(projects: list[dict]) -> str:
    numbered = "\n".join(
        f'{i + 1}. [{p["prompt_id"]}] {p["prompt_title"]}'
        for i, p in enumerate(projects)
    )
    return textwrap.dedent(f"""
        You are a research classification expert specialising in UK administrative data research.
        Classify each project title below using three independent layers.

        ══════════════════════════════════════════════════════════════
        LAYER A — SUBSTANTIVE DOMAIN  (assign 1 or more)
        ══════════════════════════════════════════════════════════════
        {DOMAIN_GUIDANCE}

        ══════════════════════════════════════════════════════════════
        LAYER B — LINKAGE MODE  (assign exactly 1)
        ══════════════════════════════════════════════════════════════
        {LINKAGE_GUIDANCE}

        ══════════════════════════════════════════════════════════════
        LAYER C — ANALYTICAL PURPOSE  (assign 1 or 2)
        ══════════════════════════════════════════════════════════════
        {PURPOSE_GUIDANCE}

        ══════════════════════════════════════════════════════════════
        CLASSIFICATION RULES
        ══════════════════════════════════════════════════════════════
        • Be conservative — prefer "Unclear from Title" over guessing.
        • Keep the three layers independent; do not let your domain choice
          bias your linkage or purpose choice.
        • Most projects: 1 domain + "Unclear from Title" linkage + 1 purpose.
        • Only expand domain list if genuinely multi-topic.
        • When assigning multiple domains, list the most relevant domain first.
        • Never assign more than 2 purposes.

        ══════════════════════════════════════════════════════════════
        PROJECT TITLES TO CLASSIFY
        ══════════════════════════════════════════════════════════════
        {numbered}

        Respond with a JSON object matching this schema exactly:
        {{
          "classifications": [
            {{
              "project_id": "<Project ID string>",
              "substantive_domains": ["<domain>", ...],
              "linkage_mode": "<exactly one linkage mode>",
              "analytical_purpose": ["<purpose>"]
            }},
            ...
          ]
        }}

        Use only the labels defined above, spelled exactly as shown.
        Produce one entry per project in the same order as listed.
    """).strip()


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


def _validate_batch_integrity(classifications: list[ProjectLayers], projects: list[dict]) -> None:
    requested_ids = [p["id"] for p in projects]
    requested_set = set(requested_ids)
    seen = set()
    duplicate_ids = set()
    unexpected_ids = set()

    for cls in classifications:
        if cls.project_id not in requested_set:
            unexpected_ids.add(cls.project_id)
            continue
        if cls.project_id in seen:
            duplicate_ids.add(cls.project_id)
            continue
        seen.add(cls.project_id)

    missing_ids = [project_id for project_id in requested_ids if project_id not in seen]
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
    Returns dict: project_id -> {substantive_domains, linkage_mode, analytical_purpose}
    """
    prompt = _build_prompt(projects)

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            output_format=BatchLayerResult,
        )
        result_obj: BatchLayerResult = response.parsed_output
        classifications = result_obj.classifications
    except Exception as e:
        print(f"  [warning] Structured parse failed ({e}); falling back to raw JSON")
        raw_response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        if not raw_response.content or not hasattr(raw_response.content[0], "text"):
            raise RuntimeError("API returned empty or non-text response content")
        raw_text = raw_response.content[0].text
        raw_dict = _parse_raw_json(raw_text, projects)

        try:
            result_obj = BatchLayerResult(**raw_dict)
            classifications = result_obj.classifications
        except Exception as e2:
            raise BatchClassificationError(f"Pydantic validation failed: {e2}") from e2

    _validate_batch_integrity(classifications, projects)

    # Build output dict
    out = {}
    for cls in classifications:
        out[cls.project_id] = {
            "substantive_domains": cls.substantive_domains,
            "linkage_mode":        cls.linkage_mode,
            "analytical_purpose":  cls.analytical_purpose,
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
            "prompt_id": _sanitise_prompt_text(str(row["Record ID"])),
            "prompt_title": _sanitise_prompt_text(row["Title"]),
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
        lambda record_id: _get(record_id, "substantive_domains", ["Other"])
    )
    df["linkage_mode"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "linkage_mode", "Unclear from Title")
    )
    df["analytical_purpose"] = df["Record ID"].apply(
        lambda record_id: _get(record_id, "analytical_purpose", ["Unclear from Title"])
    )
    # First-listed domain is the most relevant (prompt instructs this ordering)
    df["primary_domain"] = df["substantive_domains"].apply(
        lambda x: x[0] if x else "Other"
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

    # ---- Cross-tabulations ----
    top_domains = totals_a.head(6)["domain"].tolist()
    df_cross = df[df["primary_domain"].isin(top_domains)]

    # Linkage mode × primary domain
    cross_mode_domain = pd.crosstab(df_cross["primary_domain"], df_cross["linkage_mode"])

    # Primary domain × analytical purpose (exploded)
    df_dp = df_cross.explode("analytical_purpose").rename(
        columns={"analytical_purpose": "purpose"}
    )
    cross_domain_purpose = pd.crosstab(df_dp["primary_domain"], df_dp["purpose"])

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

    print("\n=== Cross-tab: Linkage Mode × Primary Domain ===")
    print(trends["cross_mode_domain"].to_string())

    print("\n=== Cross-tab: Primary Domain × Analytical Purpose ===")
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

        LINKAGE MODE × PRIMARY DOMAIN CROSS-TAB:
        {cross_mode_str}

        PRIMARY DOMAIN × ANALYTICAL PURPOSE CROSS-TAB:
        {cross_purpose_str}

        Write a concise analytical summary (5–7 paragraphs) covering:
        1. The dominant substantive domains and how the research landscape has evolved
        2. Trends in data linkage complexity — are projects becoming more cross-domain over time?
        3. The main analytical purposes and which are growing or declining
        4. Interesting combinations revealed by the cross-tabs (e.g. which domains favour
           policy evaluation, or which domains rely most on cross-domain linkage?)
        5. What this tells us about how UK researchers are exploiting administrative data
        6. Gaps or emerging areas to watch

        Write in a professional policy-briefing style, suitable for a senior civil servant audience.
        Be specific: cite numbers and trends rather than vague generalisations.
        Only comment on patterns that are directly supported by the data provided above.
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
    df_out.to_csv(
        os.path.join(output_dir, "layer_classifications.csv"),
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
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable not set.\n"
            "Set it with:  set ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Load data
    df = load_data()
    print(f"[data] {len(df):,} DEA projects, {df['Year'].min()}-{df['Year'].max()}")

    # Classify
    df_classified = classify_all(df, client)

    # Analyse
    print("\n[analysis] Computing layer frequency tables...")
    trends = analyse_layers(df_classified)
    print_quick_stats(trends)

    # Narrative
    print("\n[llm] Generating narrative summary...")
    narrative = generate_narrative(client, trends, n_projects=len(df_classified))
    print("\n--- NARRATIVE SUMMARY ---")
    print(narrative)

    # Save
    save_outputs(df_classified, trends, narrative, OUTPUT_DIR)
    print("\n[done]")
