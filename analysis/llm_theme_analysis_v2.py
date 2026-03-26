"""
LLM-based Research Theme Analysis — v2
=======================================
Upgrades over v1:

1. Tighter taxonomy    — per-theme definitions with inclusion/exclusion notes
                         embedded directly in the prompt
2. Hierarchical themes — top-level theme + subtheme (from a closed list per theme)
3. Structured output   — Pydantic schema via client.messages.parse(), replacing
                         fragile JSON regex parsing
4. Ambiguity tracking  — every classification carries a ≤8-word reason and a
                         high / medium / low confidence flag
5. Adjudication pass   — projects flagged as uncertain (low confidence, "Other",
                         or 3+ themes) are re-classified with a stricter single-
                         theme prompt and adaptive thinking for deeper reasoning
6. Baseline benchmarks — keyword matching, TF-IDF zero-shot similarity, and
                         sentence-transformer embedding baseline for comparison;
                         pairwise agreement stats measure LLM vs cheap baselines

Usage
-----
  set ANTHROPIC_API_KEY=sk-ant-...          (Windows)
  export ANTHROPIC_API_KEY=sk-ant-...       (Unix)
  python analysis/llm_theme_analysis_v2.py

Outputs  (analysis/outputs_v2/)
--------------------------------
  theme_classifications_v2.csv   one row per project, all classification fields
  benchmark_comparison.csv       per-project comparison of all four methods
  theme_trends_by_year.csv       theme share by year (%)
  theme_trends_by_quarter.csv    theme counts by quarter
  theme_totals.csv               overall theme frequency table
  theme_summary.txt              Claude-generated policy briefing
  benchmark_summary.txt          pairwise agreement statistics
"""

import os
import re
import json
import time
import textwrap
import warnings
import pandas as pd
import numpy as np
from typing import Literal
from pydantic import BaseModel, field_validator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    warnings.warn(
        "sentence-transformers not installed — embedding baseline skipped. "
        "Install with: pip install sentence-transformers",
        ImportWarning,
        stacklevel=1,
    )

import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs_v2")

CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

CACHE_FILE = os.path.join(OUTPUT_DIR, "llm_theme_cache_v2.json")
ADJ_CACHE_FILE = os.path.join(OUTPUT_DIR, "llm_theme_cache_v2_adj.json")

MODEL = "claude-opus-4-6"

# Batch size — smaller than v1 because we return richer structured output
BATCH_SIZE = 25

# Adjudication triggers
ADJ_LOW_CONFIDENCE = {"low"}        # confidence values that trigger adjudication
ADJ_MAX_THEMES = 3                  # projects with this many or more themes → adjudicate


# ---------------------------------------------------------------------------
# Theme taxonomy
# ---------------------------------------------------------------------------

THEME_TAXONOMY: dict[str, dict] = {
    "Labour Market & Employment": {
        "definition": (
            "wages, earnings, employment rates, job quality, unemployment, occupational "
            "outcomes, labour mobility, labour supply and demand, gig economy, trade unions, "
            "working conditions, non-standard work"
        ),
        "exclusions": (
            "educational attainment → Education & Skills; "
            "welfare transfer mechanisms → Public Finance & Taxation"
        ),
        "subthemes": [
            "wages & pay",
            "unemployment & inactivity",
            "labour mobility & transitions",
            "occupational outcomes",
            "gig economy & non-standard work",
            "skills & training outcomes",
        ],
    },
    "Education & Skills": {
        "definition": (
            "school attainment, higher education outcomes, vocational and further education, "
            "early years education, special educational needs (SEND), teacher workforce, "
            "educational inequality, student progression and destinations"
        ),
        "exclusions": (
            "workplace skills development → Labour Market & Employment "
            "unless formal education context"
        ),
        "subthemes": [
            "school attainment & outcomes",
            "higher education",
            "vocational & further education",
            "early years & child development",
            "educational inequality & SEND",
            "teacher & school workforce",
        ],
    },
    "Health & Social Care": {
        "definition": (
            "health outcomes, NHS services, hospital care, primary care, mental health, "
            "social care services, public health, patient populations, healthcare workforce, "
            "mortality, morbidity, long-term conditions, disability"
        ),
        "exclusions": "childcare / early-years care → Education & Skills",
        "subthemes": [
            "mental health",
            "hospital & acute care",
            "public health & prevention",
            "social care",
            "healthcare workforce",
            "long-term conditions & disability",
        ],
    },
    "Crime & Justice": {
        "definition": (
            "crime rates, criminal justice system, courts, prisons, probation, policing, "
            "reoffending, victimisation, sentencing outcomes, judicial processes, fraud"
        ),
        "exclusions": "",
        "subthemes": [
            "policing & crime",
            "courts & sentencing",
            "prisons & probation",
            "reoffending & rehabilitation",
            "victimisation",
            "crime & social inequality",
        ],
    },
    "Business & Productivity": {
        "definition": (
            "firm performance, productivity growth, innovation, entrepreneurship, investment, "
            "business survival and entry/exit, industrial strategy, trade and exports, "
            "supply chains, regional economic development"
        ),
        "exclusions": (
            "personal earnings → Labour Market & Employment; "
            "agricultural output → Environment & Agriculture"
        ),
        "subthemes": [
            "firm productivity & performance",
            "innovation & R&D",
            "entrepreneurship & start-ups",
            "trade & exports",
            "regional & industrial policy",
            "investment & capital",
        ],
    },
    "Poverty, Inequality & Living Standards": {
        "definition": (
            "income poverty, material deprivation, living standards, social mobility, "
            "consumption inequality, welfare take-up, financial hardship, child poverty; "
            "focus on distributional outcomes across the income spectrum"
        ),
        "exclusions": (
            "gender/ethnic pay gaps → Gender, Race & Ethnicity unless broader poverty context; "
            "tax-credits design/mechanism → Public Finance & Taxation"
        ),
        "subthemes": [
            "income poverty",
            "social mobility",
            "welfare & benefits take-up",
            "material deprivation",
            "living standards & consumption",
            "child poverty",
        ],
    },
    "Housing & Planning": {
        "definition": (
            "housing affordability, homelessness, rental markets, homeownership, "
            "planning policy, housing supply, neighbourhood deprivation, evictions, "
            "rough sleeping, housing quality"
        ),
        "exclusions": "",
        "subthemes": [
            "housing affordability & supply",
            "homelessness & rough sleeping",
            "rental markets",
            "neighbourhood & area effects",
            "housing & health",
            "planning & land use",
        ],
    },
    "Migration & Demographics": {
        "definition": (
            "immigration, emigration, migrant integration and outcomes, population structure, "
            "fertility, mortality trends, population ageing, internal migration; "
            "focus on population dynamics, not ethnic group outcomes per se"
        ),
        "exclusions": (
            "ethnic minority discrimination/inequalities → Gender, Race & Ethnicity; "
            "refugee integration outcomes may genuinely overlap — use both if warranted"
        ),
        "subthemes": [
            "immigration outcomes & integration",
            "emigration & return migration",
            "population ageing",
            "fertility & family formation",
            "internal migration & mobility",
            "demographic change & projection",
        ],
    },
    "Environment & Agriculture": {
        "definition": (
            "environmental outcomes, agricultural policy and productivity, rural economy, "
            "food systems, land use, forestry, climate adaptation, biodiversity; "
            "substantive environmental or agricultural research focus required"
        ),
        "exclusions": (
            "environmental health outcomes → Health & Social Care "
            "unless the environmental cause is the main research focus"
        ),
        "subthemes": [
            "agricultural productivity & policy",
            "rural economy",
            "environmental regulation & compliance",
            "food systems & security",
            "climate change & adaptation",
            "land use & biodiversity",
        ],
    },
    "Public Finance & Taxation": {
        "definition": (
            "tax compliance, tax revenues, public spending, fiscal policy, benefits design "
            "and take-up, welfare reform, pension policy; focus on the fiscal mechanism, "
            "not downstream poverty or inequality outcomes"
        ),
        "exclusions": "poverty outcomes of welfare → Poverty, Inequality & Living Standards",
        "subthemes": [
            "tax compliance & avoidance",
            "public spending & fiscal policy",
            "benefits & tax credits design",
            "pension policy",
            "welfare reform",
            "tax revenues & forecasting",
        ],
    },
    "Gender, Race & Ethnicity": {
        "definition": (
            "gender gaps, pay gaps, ethnic disparities, racial inequality, "
            "intersectionality, discrimination in labour/education/health/justice; "
            "use when inequality by gender, race, or ethnicity IS a primary research focus"
        ),
        "exclusions": "any-group poverty/deprivation without discrimination focus → Poverty, Inequality",
        "subthemes": [
            "gender pay & career gaps",
            "ethnic & racial inequality",
            "intersectionality & multiple disadvantage",
            "discrimination",
            "diversity in workforce or institutions",
            "gender-based violence",
        ],
    },
    "COVID-19 & Pandemic": {
        "definition": (
            "ONLY use when COVID-19 is a PRIMARY substantive focus: pandemic mortality, "
            "COVID-19 economic impacts, pandemic policy responses, vaccine uptake, long COVID. "
            "Do NOT use merely because data collection spans 2020–2022 or "
            "pandemic is background context."
        ),
        "exclusions": (
            "If pandemic is just a time-period framing or incidental mention, "
            "assign the substantive theme instead (e.g. Labour Market, Health)"
        ),
        "subthemes": [
            "pandemic mortality & health outcomes",
            "pandemic economic impacts",
            "pandemic & education",
            "pandemic & inequality",
            "pandemic policy & vaccine uptake",
            "long COVID",
        ],
    },
    "Data Infrastructure & Methodology": {
        "definition": (
            "data linkage methods, record linkage, statistical methodology, data quality, "
            "data governance, administrative data access infrastructure; use ONLY when "
            "the method or data infrastructure IS the research question, not just a tool"
        ),
        "exclusions": (
            "studies that USE linked data but investigate a substantive topic → "
            "assign the substantive topic instead"
        ),
        "subthemes": [
            "data linkage & integration methods",
            "statistical methods & evaluation",
            "data governance & access",
            "measurement & data quality",
            "synthetic data & privacy",
            "data infrastructure & pipelines",
        ],
    },
    "Other": {
        "definition": "Use ONLY when no other theme adequately describes the project.",
        "exclusions": "",
        "subthemes": [],
    },
}

THEMES: list[str] = list(THEME_TAXONOMY.keys())
_VALID_THEMES: set[str] = set(THEMES)


# ---------------------------------------------------------------------------
# Keyword rules (for the keyword baseline)
# ---------------------------------------------------------------------------

KEYWORD_RULES: dict[str, list[str]] = {
    "Labour Market & Employment": [
        r"\blabou?r market\b", r"\bemploy", r"\bunemploy", r"\bwages?\b",
        r"\bearnings?\b", r"\bworkers?\b", r"\bworkplac", r"\bjobs?\b",
        r"\boccupat", r"\bworkforc", r"\bgig econom", r"\bself.?employ",
        r"\btrade union", r"\bpart.?time\b", r"\bpay gap\b",
    ],
    "Education & Skills": [
        r"\beducat", r"\bschool\b", r"\bpupil", r"\bstudents?\b",
        r"\battainment\b", r"\bqualif", r"\buniversit", r"\bgraduate",
        r"\bskills?\b", r"\bapprentice", r"\bteach", r"\bnursery\b",
        r"\bhigher education\b", r"\bsend\b", r"\bspecial educational",
    ],
    "Health & Social Care": [
        r"\bhealth\b", r"\bnhs\b", r"\bhospital", r"\bpatient",
        r"\bclinical\b", r"\bmortality\b", r"\bmorbidity\b",
        r"\bmental health\b", r"\bsocial care\b", r"\bnurse",
        r"\bdisability\b", r"\bcancer\b", r"\bdiabet", r"\bcardio",
    ],
    "Crime & Justice": [
        r"\bcrime\b", r"\bcriminal\b", r"\bjustice\b", r"\bpolice\b",
        r"\bprison", r"\boffend", r"\bvictim\b", r"\bsentenc",
        r"\bcourt\b", r"\bprobation\b", r"\breoffend", r"\bfraud\b",
    ],
    "Business & Productivity": [
        r"\bfirms?\b", r"\bbusiness", r"\bproductiv", r"\binnovation\b",
        r"\bentrepreneur", r"\binvestment\b", r"\bexports?\b", r"\bindustr",
        r"\bmanufact", r"\bsupply chain", r"\bcompan", r"\bsme\b",
    ],
    "Poverty, Inequality & Living Standards": [
        r"\bpoverty\b", r"\bdepriv", r"\binequality\b",
        r"\bliving standards?\b", r"\bwelfare\b", r"\bbenefits?\b",
        r"\bsocial mobil", r"\bhardship", r"\blow.?income", r"\bchild poverty\b",
    ],
    "Housing & Planning": [
        r"\bhousing\b", r"\bhomeless", r"\brents?\b", r"\baffordab",
        r"\bplanning\b", r"\bneighbou?r", r"\bdwelling", r"\btenure\b",
        r"\blandlord", r"\bevict",
    ],
    "Migration & Demographics": [
        r"\bimmigr", r"\bemigr", r"\bmigrant", r"\bpopulat",
        r"\bfertility\b", r"\bageing\b", r"\baging\b", r"\bdemograph",
        r"\brefugee", r"\basylum\b",
    ],
    "Environment & Agriculture": [
        r"\benviron", r"\bagricult", r"\bfarms?\b", r"\brural\b",
        r"\bclimate\b", r"\bfood security\b", r"\bland use\b",
        r"\brenewable", r"\bforest", r"\bbiodiversity\b",
    ],
    "Public Finance & Taxation": [
        r"\btax\b", r"\btaxation\b", r"\bfiscal\b", r"\bhmrc\b",
        r"\bpublic spending\b", r"\bpension", r"\bwelfare reform\b",
        r"\btax credits?\b", r"\bnational insurance\b",
    ],
    "Gender, Race & Ethnicity": [
        r"\bgender\b", r"\bwomen\b", r"\bfemale\b", r"\bethnic",
        r"\bracial\b", r"\bminority\b", r"\bdiscriminat",
        r"\bdiversit", r"\bintersection", r"\bgender pay\b",
    ],
    "COVID-19 & Pandemic": [
        r"\bcovid", r"\bpandemic\b", r"\bcoronavirus", r"\bsars.?cov",
        r"\blockdown\b", r"\blong covid\b",
    ],
    "Data Infrastructure & Methodology": [
        r"\blinkage\b", r"\blinked data\b", r"\brecord link",
        r"\bdata quality\b", r"\bstatistical method", r"\bdata governance\b",
        r"\bvalidat", r"\bsynthetic data\b", r"\bdata infrastructure\b",
    ],
}


def keyword_classify(title: str) -> str:
    """Return the theme with most keyword hits; ties broken by list order."""
    t = title.lower()
    scores: dict[str, int] = {}
    for theme, patterns in KEYWORD_RULES.items():
        hits = sum(1 for p in patterns if re.search(p, t))
        if hits:
            scores[theme] = hits
    return max(scores, key=scores.get) if scores else "Other"


# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------

class ProjectClassification(BaseModel):
    project_id: str
    themes: list[str]
    subtheme: str
    reason: str
    confidence: Literal["high", "medium", "low"]

    @field_validator("themes")
    @classmethod
    def validate_themes(cls, v: list) -> list:
        cleaned = [t for t in v if t in _VALID_THEMES]
        return cleaned[:3] if cleaned else ["Other"]

    @field_validator("reason")
    @classmethod
    def truncate_reason(cls, v: str) -> str:
        return " ".join(str(v).split()[:10])


class BatchResult(BaseModel):
    classifications: list[ProjectClassification]


class AdjudicatedClassification(BaseModel):
    project_id: str
    theme: str
    subtheme: str
    reason: str

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        return v if v in _VALID_THEMES else "Other"


class AdjudicationBatchResult(BaseModel):
    classifications: list[AdjudicatedClassification]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

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
        "Project Name": "Title",
        "Accredited Researchers": "Researchers",
        "Legal Gateway": "Legal Basis",
        "Protected Data Accessed": "Datasets Used",
        "Processing Environment": "Secure Research Service",
    })
    df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    df = df.dropna(subset=["Accreditation Date", "Title"])
    if "Legal Basis" in df.columns:
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]
    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# TF-IDF zero-shot baseline
# ---------------------------------------------------------------------------

def build_tfidf_baseline():
    """Return (vectorizer, theme_matrix, theme_names) fitted on theme definitions."""
    theme_names = [n for n in THEMES if n != "Other"]
    theme_docs = [
        f"{n}: {THEME_TAXONOMY[n]['definition']}"
        for n in theme_names
    ]
    vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    matrix = vec.fit_transform(theme_docs)
    return vec, matrix, theme_names


def tfidf_classify(title: str, vec, matrix, theme_names: list[str]) -> str:
    title_vec = vec.transform([title.lower()])
    sims = cosine_similarity(title_vec, matrix)[0]
    best = int(np.argmax(sims))
    return theme_names[best] if sims[best] > 0 else "Other"


# ---------------------------------------------------------------------------
# Sentence-transformer embedding baseline
# ---------------------------------------------------------------------------

def build_embedding_baseline(model_name: str = "all-MiniLM-L6-v2"):
    """Return (st_model, embeddings, theme_names). Returns (None, None, None) if unavailable."""
    if not _ST_AVAILABLE:
        return None, None, None
    print("[embed] Loading sentence-transformer model...")
    st_model = SentenceTransformer(model_name)
    theme_names = [n for n in THEMES if n != "Other"]
    docs = [f"{n}: {THEME_TAXONOMY[n]['definition']}" for n in theme_names]
    embeddings = st_model.encode(docs, normalize_embeddings=True)
    return st_model, embeddings, theme_names


def embedding_classify(title: str, st_model, embeddings, theme_names: list[str]) -> str:
    if st_model is None:
        return "N/A"
    emb = st_model.encode([title], normalize_embeddings=True)
    sims = (emb @ embeddings.T)[0]
    return theme_names[int(np.argmax(sims))]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_taxonomy_block() -> str:
    lines = []
    for name, meta in THEME_TAXONOMY.items():
        if name == "Other":
            lines.append(f"\n  Other: use only when nothing else fits.")
            continue
        subs = " | ".join(meta["subthemes"])
        lines.append(f"\n  {name}")
        lines.append(f"    Definition : {meta['definition']}")
        if meta["exclusions"]:
            lines.append(f"    NOT        : {meta['exclusions']}")
        lines.append(f"    Subthemes  : {subs}")
    return "\n".join(lines)


_TAXONOMY_BLOCK: str = _build_taxonomy_block()   # built once at import time


def _main_prompt(projects: list[dict]) -> str:
    numbered = "\n".join(
        f'  {i+1}. [{p["id"]}] {p["title"]}'
        for i, p in enumerate(projects)
    )
    return textwrap.dedent(f"""
        You are a research classification expert. Classify each DEA-accredited
        project title below by research theme, using the taxonomy provided.

        THEME TAXONOMY:
        {_TAXONOMY_BLOCK}

        CLASSIFICATION RULES:
        - Assign 1–2 themes per project; only add a second if genuinely co-equal.
        - Pick ONE subtheme from the subtheme list of the PRIMARY theme.
        - Write a SHORT reason (max 8 words) explaining your primary choice.
        - Set confidence: "high" = clear fit, "medium" = arguable, "low" = genuinely ambiguous.
        - COVID-19: ONLY if pandemic is the primary research focus, not just a time period.
        - Data Infrastructure: ONLY if method/linkage IS the research question itself.

        PROJECT TITLES ({len(projects)} to classify):
        {numbered}

        Return JSON matching this schema exactly:
        {{
          "classifications": [
            {{
              "project_id": "<id>",
              "themes": ["<Primary Theme>"],
              "subtheme": "<subtheme from that theme's list>",
              "reason": "<max 8-word reason>",
              "confidence": "high" | "medium" | "low"
            }},
            ...
          ]
        }}

        Include all {len(projects)} projects.
    """).strip()


def _adjudication_prompt(projects: list[dict]) -> str:
    numbered = "\n".join(
        f'  {i+1}. [{p["id"]}] {p["title"]}  [prior: {p.get("prior", "?")}]'
        for i, p in enumerate(projects)
    )
    return textwrap.dedent(f"""
        You are a research classification expert resolving ambiguous cases.
        These projects were flagged as uncertain in a prior classification pass.

        For each project, assign EXACTLY ONE theme. Be decisive — do not hedge.
        If a project spans two areas, pick the more substantively important one.

        THEME TAXONOMY:
        {_TAXONOMY_BLOCK}

        PROJECTS (prior uncertain classification shown):
        {numbered}

        Return JSON:
        {{
          "classifications": [
            {{
              "project_id": "<id>",
              "theme": "<exactly one Theme Name>",
              "subtheme": "<subtheme>",
              "reason": "<max 8-word reason>"
            }}
          ]
        }}
    """).strip()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def load_cache(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# LLM classification — main pass
# ---------------------------------------------------------------------------

def _classify_batch_structured(client: anthropic.Anthropic, projects: list[dict]) -> list[dict]:
    """Use client.messages.parse() for guaranteed structured output."""
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": _main_prompt(projects)}],
        output_format=BatchResult,
    )
    return [c.model_dump() for c in response.parsed_output.classifications]


def _classify_batch_fallback(client: anthropic.Anthropic, projects: list[dict]) -> list[dict]:
    """Plain messages.create() + JSON extraction — used if parse() fails."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": _main_prompt(projects)}],
    )
    raw = next((b.text for b in resp.content if b.type == "text"), "{}")
    m = re.search(r"\{[\s\S]+\}", raw)
    if not m:
        return [
            {"project_id": p["id"], "themes": ["Other"], "subtheme": "N/A",
             "reason": "parse error", "confidence": "low"}
            for p in projects
        ]
    data = json.loads(m.group(0))
    return data.get("classifications", [])


def classify_batch(client: anthropic.Anthropic, projects: list[dict]) -> list[dict]:
    try:
        return _classify_batch_structured(client, projects)
    except Exception as e:
        print(f"  [warning] parse() failed ({type(e).__name__}: {e}); using fallback")
        return _classify_batch_fallback(client, projects)


def classify_all(df: pd.DataFrame, client: anthropic.Anthropic) -> pd.DataFrame:
    cache = load_cache(CACHE_FILE)
    to_classify = [
        {"id": str(row["Project ID"]), "title": str(row["Title"])}
        for _, row in df.iterrows()
        if str(row["Project ID"]) not in cache
    ]
    n_batches = (len(to_classify) + BATCH_SIZE - 1) // BATCH_SIZE if to_classify else 0
    print(f"[llm] {len(cache)} cached; {len(to_classify)} to classify in {n_batches} batches")

    for i in range(0, len(to_classify), BATCH_SIZE):
        batch = to_classify[i: i + BATCH_SIZE]
        print(f"  Batch {i // BATCH_SIZE + 1}/{n_batches} ({len(batch)} projects)...")
        try:
            results = classify_batch(client, batch)
            for r in results:
                pid = str(r.get("project_id", ""))
                if pid:
                    cache[pid] = r
            save_cache(cache, CACHE_FILE)
        except Exception as e:
            print(f"  [error] {e}")
            time.sleep(2)
        time.sleep(0.3)

    df = df.copy()
    def _get(pid: str, field: str, default):
        entry = cache.get(str(pid))
        return entry.get(field, default) if isinstance(entry, dict) else default

    df["themes"]        = df["Project ID"].apply(lambda p: _get(p, "themes", ["Other"]))
    df["subtheme"]      = df["Project ID"].apply(lambda p: _get(p, "subtheme", "N/A"))
    df["reason"]        = df["Project ID"].apply(lambda p: _get(p, "reason", ""))
    df["confidence"]    = df["Project ID"].apply(lambda p: _get(p, "confidence", "low"))
    df["primary_theme"] = df["themes"].apply(lambda x: x[0] if x else "Other")
    return df


# ---------------------------------------------------------------------------
# Adjudication pass
# ---------------------------------------------------------------------------

def _is_uncertain(row: pd.Series) -> bool:
    themes = row["themes"] if isinstance(row["themes"], list) else ["Other"]
    return (
        row["confidence"] in ADJ_LOW_CONFIDENCE
        or "Other" in themes
        or len(themes) >= ADJ_MAX_THEMES
    )


def adjudicate(df: pd.DataFrame, client: anthropic.Anthropic) -> pd.DataFrame:
    uncertain_mask = df.apply(_is_uncertain, axis=1)
    uncertain = df[uncertain_mask]
    print(f"[adj] {len(uncertain)} uncertain projects flagged for adjudication pass")
    if len(uncertain) == 0:
        return df

    adj_cache = load_cache(ADJ_CACHE_FILE)
    to_adj = [
        {
            "id": str(row["Project ID"]),
            "title": str(row["Title"]),
            "prior": ", ".join(row["themes"]) if isinstance(row["themes"], list) else "?",
        }
        for _, row in uncertain.iterrows()
        if str(row["Project ID"]) not in adj_cache
    ]
    n_batches = (len(to_adj) + BATCH_SIZE - 1) // BATCH_SIZE if to_adj else 0
    print(f"[adj] {len(adj_cache)} cached; {len(to_adj)} to adjudicate in {n_batches} batches")

    for i in range(0, len(to_adj), BATCH_SIZE):
        batch = to_adj[i: i + BATCH_SIZE]
        print(f"  Adjudication batch {i // BATCH_SIZE + 1}/{n_batches} ({len(batch)} projects)...")
        try:
            # Use adaptive thinking for harder reasoning on ambiguous cases
            response = client.messages.parse(
                model=MODEL,
                max_tokens=4000,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": _adjudication_prompt(batch)}],
                output_format=AdjudicationBatchResult,
            )
            for r in response.parsed_output.classifications:
                adj_cache[r.project_id] = r.model_dump()
            save_cache(adj_cache, ADJ_CACHE_FILE)
        except Exception as e:
            print(f"  [error] adjudication failed: {e}; skipping batch")
            time.sleep(2)
        time.sleep(0.3)

    # Apply adjudications back onto df
    df = df.copy()
    for pid, adj in adj_cache.items():
        mask = df["Project ID"].astype(str) == pid
        if not mask.any():
            continue
        theme = adj.get("theme", "Other")
        df.loc[mask, "primary_theme"] = theme
        df.loc[mask, "subtheme"]      = adj.get("subtheme", "N/A")
        df.loc[mask, "reason"]        = adj.get("reason", "")
        df.loc[mask, "confidence"]    = "adjudicated"
        df.loc[mask, "themes"]        = df.loc[mask, "themes"].apply(lambda _: [theme])

    print(f"[adj] Applied {len(adj_cache)} adjudications")
    return df


# ---------------------------------------------------------------------------
# Baseline benchmarks
# ---------------------------------------------------------------------------

def run_benchmarks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    print("\n[benchmark] Keyword baseline...")
    df["kw_theme"] = df["Title"].apply(keyword_classify)

    print("[benchmark] TF-IDF zero-shot baseline...")
    vec, matrix, theme_names = build_tfidf_baseline()
    df["tfidf_theme"] = df["Title"].apply(
        lambda t: tfidf_classify(t, vec, matrix, theme_names)
    )

    if _ST_AVAILABLE:
        print("[benchmark] Sentence-transformer embedding baseline...")
        st_model, embeddings, st_names = build_embedding_baseline()
        df["embed_theme"] = df["Title"].apply(
            lambda t: embedding_classify(t, st_model, embeddings, st_names)
        )
    else:
        df["embed_theme"] = "N/A"

    return df


def benchmark_summary(df: pd.DataFrame) -> str:
    llm = df["primary_theme"]
    kw  = df["kw_theme"]
    tf  = df["tfidf_theme"]
    em  = df["embed_theme"]

    def pct_agree(a: pd.Series, b: pd.Series) -> float:
        valid = b != "N/A"
        return (a[valid] == b[valid]).mean() * 100 if valid.any() else float("nan")

    lines = [
        "=== Pairwise Agreement Rates ===",
        f"  LLM  vs Keyword   : {pct_agree(llm, kw):.1f}%",
        f"  LLM  vs TF-IDF    : {pct_agree(llm, tf):.1f}%",
    ]
    if _ST_AVAILABLE:
        lines += [
            f"  LLM  vs Embedding : {pct_agree(llm, em):.1f}%",
            f"  KW   vs TF-IDF    : {pct_agree(kw, tf):.1f}%",
            f"  KW   vs Embedding : {pct_agree(kw, em):.1f}%",
        ]
        all_agree = ((llm == kw) & (llm == tf) & (llm == em)).mean() * 100
        lines.append(f"\n  All three agree   : {all_agree:.1f}% of projects")

    lines += [
        "\n=== LLM confidence distribution ===",
        df["confidence"].value_counts().to_string(),
        "\n=== Per-theme keyword agreement (where LLM assigned that theme) ===",
    ]
    for theme in THEMES:
        if theme == "Other":
            continue
        llm_mask = llm == theme
        if llm_mask.sum() == 0:
            continue
        match = (kw[llm_mask] == theme).mean() * 100
        lines.append(
            f"  {theme:<44} {match:5.1f}%  ({llm_mask.sum()} projects)"
        )

    lines += [
        "\n=== Notes on interpretation ===",
        "  Low LLM-vs-keyword agreement on a theme suggests the theme relies on",
        "  contextual/semantic cues that keywords miss — a genuine LLM advantage.",
        "  High agreement suggests the LLM is largely replicating keyword logic.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trend analysis
# ---------------------------------------------------------------------------

def analyse_trends(df: pd.DataFrame) -> dict:
    df_exp = df.explode("themes").rename(columns={"themes": "theme"})

    by_year = (
        df_exp.groupby(["Year", "theme"])["Project ID"]
        .count().reset_index().rename(columns={"Project ID": "count"})
    )
    totals_year = df.groupby("Year")["Project ID"].count().rename("total")
    by_year = by_year.merge(totals_year, on="Year")
    by_year["pct"] = (by_year["count"] / by_year["total"] * 100).round(1)

    by_quarter = (
        df_exp.groupby(["Quarter Label", "theme"])["Project ID"]
        .count().reset_index().rename(columns={"Project ID": "count"})
    )
    totals = (
        df_exp.groupby("theme")["Project ID"]
        .count().reset_index().rename(columns={"Project ID": "count"})
        .sort_values("count", ascending=False)
    )
    return {"by_year": by_year, "by_quarter": by_quarter, "totals": totals}


def generate_narrative(client: anthropic.Anthropic, df: pd.DataFrame, trends: dict) -> str:
    year_pivot = (
        trends["by_year"]
        .pivot(index="Year", columns="theme", values="pct")
        .fillna(0).round(1)
    )
    prompt = textwrap.dedent(f"""
        You are a research policy analyst. DEA-accredited research projects have
        been classified into themes using a hierarchical LLM taxonomy (Opus 4.6)
        with confidence scoring and adjudication of uncertain cases.

        Overall theme totals (number of projects):
        {trends["totals"].to_string(index=False)}

        Theme share by year (% of that year's projects):
        {year_pivot.to_string()}

        Write a concise policy briefing (4–6 paragraphs) covering:
        1. Dominant research themes and their relative scale
        2. Notable trends — growing, declining, or stable themes
        3. Any theme that spiked in a particular year and likely reason
        4. What this reveals about evolving use of UK administrative data
        5. Emerging areas likely to grow in the next 2–3 years

        Style: professional but accessible, suitable for a policy audience.
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_outputs(
    df: pd.DataFrame,
    trends: dict,
    narrative: str,
    bench: str,
    output_dir: str = OUTPUT_DIR,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    df_out = df.copy()
    df_out["themes"] = df_out["themes"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )
    df_out.to_csv(
        os.path.join(output_dir, "theme_classifications_v2.csv"),
        index=False, encoding="utf-8-sig",
    )

    bench_cols = [
        c for c in [
            "Project ID", "Title", "primary_theme", "subtheme",
            "confidence", "reason", "kw_theme", "tfidf_theme", "embed_theme",
        ] if c in df_out.columns
    ]
    df_out[bench_cols].to_csv(
        os.path.join(output_dir, "benchmark_comparison.csv"),
        index=False, encoding="utf-8-sig",
    )

    trends["by_year"].to_csv(
        os.path.join(output_dir, "theme_trends_by_year.csv"), index=False, encoding="utf-8-sig"
    )
    trends["by_quarter"].to_csv(
        os.path.join(output_dir, "theme_trends_by_quarter.csv"), index=False, encoding="utf-8-sig"
    )
    trends["totals"].to_csv(
        os.path.join(output_dir, "theme_totals.csv"), index=False, encoding="utf-8-sig"
    )

    with open(os.path.join(output_dir, "theme_summary.txt"), "w", encoding="utf-8") as f:
        f.write(narrative)
    with open(os.path.join(output_dir, "benchmark_summary.txt"), "w", encoding="utf-8") as f:
        f.write(bench)

    print(f"\n[output] Saved to {output_dir}/")
    for fname in [
        "theme_classifications_v2.csv", "benchmark_comparison.csv",
        "theme_trends_by_year.csv", "theme_trends_by_quarter.csv",
        "theme_totals.csv", "theme_summary.txt", "benchmark_summary.txt",
    ]:
        print(f"  - {fname}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set.\n"
            "  Windows: set ANTHROPIC_API_KEY=sk-ant-...\n"
            "  Unix:    export ANTHROPIC_API_KEY=sk-ant-..."
        )

    client = anthropic.Anthropic(api_key=api_key)

    df = load_data()
    print(f"[data] {len(df):,} DEA projects, {df['Year'].min()}–{df['Year'].max()}")

    # 1. Main LLM classification (structured output via Pydantic)
    df = classify_all(df, client)

    # 2. Adjudication — re-run uncertain cases with adaptive thinking
    df = adjudicate(df, client)

    # 3. Baseline benchmarks
    df = run_benchmarks(df)
    bench = benchmark_summary(df)
    print("\n" + bench)

    # 4. Trend analysis
    print("\n[analysis] Computing trends...")
    trends = analyse_trends(df)
    print("\n=== Theme Totals ===")
    print(trends["totals"].to_string(index=False))

    # 5. Narrative policy summary
    print("\n[llm] Generating narrative...")
    narrative = generate_narrative(client, df, trends)
    print("\n--- NARRATIVE ---")
    print(narrative)

    # 6. Save all outputs
    save_outputs(df, trends, narrative, bench)
    print("\n[done]")
