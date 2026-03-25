"""
LLM-based Research Theme Analysis of DEA Project Titles
=========================================================
Uses the Claude API to systematically classify DEA project titles into
research themes, enabling analysis of how research priorities have shifted
over time.

Requirements:
    pip install anthropic

Usage:
    # Set your API key first:
    export ANTHROPIC_API_KEY=sk-ant-...   (Unix)
    set ANTHROPIC_API_KEY=sk-ant-...      (Windows)

    python analysis/llm_theme_analysis.py

Outputs (written to analysis/outputs/):
    - theme_classifications.csv   : One row per project with assigned theme(s)
    - theme_trends_by_year.csv    : Theme frequencies by year
    - theme_trends_by_quarter.csv : Theme frequencies by quarter
    - theme_summary.txt           : Human-readable summary from Claude

The script batches titles to minimise API calls and caches results so
re-running only processes newly added projects.
"""

import os
import json
import time
import textwrap
import pandas as pd
import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")

# Prefer freshest data file
CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

# Cache file — stores previously classified projects to avoid re-classifying
CACHE_FILE = os.path.join(OUTPUT_DIR, "llm_theme_cache.json")

# Claude model to use
MODEL = "claude-opus-4-6"

# Batch size: number of project titles per API call
BATCH_SIZE = 50

# Predefined themes — Claude will assign one or more of these to each project.
# Keeping the list stable across runs allows proper trend analysis.
THEMES = [
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

THEMES_STR = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(THEMES))


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

    # Standardise column names
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

    # DEA only
    if "Legal Basis" in df.columns:
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]

    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

def load_cache(cache_path: str) -> dict:
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, cache_path: str):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def classify_batch(client: anthropic.Anthropic, projects: list[dict]) -> dict:
    """
    projects: list of {"id": ..., "title": ...}
    Returns: dict mapping project_id -> list of theme strings
    """
    numbered = "\n".join(
        f'{i+1}. [{p["id"]}] {p["title"]}' for i, p in enumerate(projects)
    )

    prompt = textwrap.dedent(f"""
        You are a research classification assistant. Below is a list of research project
        titles from the UK Digital Economy Act accredited projects register. Each title
        is numbered and preceded by its Project ID in square brackets.

        Your task: for each project, assign one or more of the following research themes
        that best describe the project. You may assign multiple themes if genuinely relevant,
        but prefer specificity — most projects should have 1–2 themes.

        Themes:
        {THEMES_STR}

        Project titles to classify:
        {numbered}

        Respond ONLY with a JSON object mapping each Project ID to an array of theme names.
        Use exactly the theme names listed above. Example format:
        {{
          "2019/003": ["Labour Market & Employment"],
          "2019/004": ["Business & Productivity", "Labour Market & Employment"]
        }}

        JSON response:
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    # Extract JSON from response (handle any surrounding text)
    json_match = raw
    if "```" in raw:
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
        if m:
            json_match = m.group(1).strip()

    try:
        result = json.loads(json_match)
    except json.JSONDecodeError:
        # Fallback: try to find the first { ... } block
        import re
        m = re.search(r"\{[\s\S]+\}", json_match)
        if m:
            result = json.loads(m.group(0))
        else:
            print(f"  [warning] Could not parse JSON from response; assigning 'Other'")
            result = {p["id"]: ["Other"] for p in projects}

    # Validate theme names
    valid_themes = set(THEMES)
    for pid, themes in result.items():
        result[pid] = [t for t in themes if t in valid_themes] or ["Other"]

    return result


def classify_all(df: pd.DataFrame, client: anthropic.Anthropic) -> pd.DataFrame:
    """Classify all projects, using cache to skip already-classified ones."""
    cache = load_cache(CACHE_FILE)

    to_classify = [
        {"id": row["Project ID"], "title": row["Title"]}
        for _, row in df.iterrows()
        if str(row["Project ID"]) not in cache
    ]

    print(f"[llm] {len(cache)} projects already cached; {len(to_classify)} to classify")

    if to_classify:
        for i in range(0, len(to_classify), BATCH_SIZE):
            batch = to_classify[i: i + BATCH_SIZE]
            print(f"  Classifying batch {i//BATCH_SIZE + 1} / {(len(to_classify) - 1)//BATCH_SIZE + 1} "
                  f"({len(batch)} projects)...")
            try:
                results = classify_batch(client, batch)
                cache.update({str(k): v for k, v in results.items()})
                save_cache(cache, CACHE_FILE)
            except Exception as e:
                print(f"  [error] Batch failed: {e}")
                # Brief pause before continuing
                time.sleep(2)
            time.sleep(0.5)  # Rate limiting courtesy pause

    # Attach themes to DataFrame
    df = df.copy()
    df["themes"] = df["Project ID"].astype(str).map(cache).apply(
        lambda x: x if isinstance(x, list) else ["Other"]
    )
    df["primary_theme"] = df["themes"].apply(lambda x: x[0] if x else "Other")
    return df


# ---------------------------------------------------------------------------
# Analysis & output
# ---------------------------------------------------------------------------

def analyse_trends(df_classified: pd.DataFrame) -> dict:
    """Compute theme frequency tables and return dict of DataFrames."""

    # Explode themes (one row per project × theme)
    df_exp = df_classified.explode("themes").rename(columns={"themes": "theme"})

    # By year
    by_year = (
        df_exp.groupby(["Year", "theme"])["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "count"})
    )
    total_by_year = df_classified.groupby("Year")["Project ID"].count().rename("total")
    by_year = by_year.merge(total_by_year, on="Year")
    by_year["pct"] = (by_year["count"] / by_year["total"] * 100).round(1)

    # By quarter
    by_quarter = (
        df_exp.groupby(["Quarter Label", "theme"])["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "count"})
    )

    # Overall theme totals
    totals = (
        df_exp.groupby("theme")["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "count"})
        .sort_values("count", ascending=False)
    )

    return {"by_year": by_year, "by_quarter": by_quarter, "totals": totals}


def generate_narrative_summary(
    client: anthropic.Anthropic,
    df_classified: pd.DataFrame,
    trends: dict,
) -> str:
    """Ask Claude to write a brief narrative summary of the theme trends."""
    year_pivot = (
        trends["by_year"]
        .pivot(index="Year", columns="theme", values="pct")
        .fillna(0)
        .round(1)
    )
    totals_str = trends["totals"].to_string(index=False)
    year_str = year_pivot.to_string()

    prompt = textwrap.dedent(f"""
        You are a research policy analyst. Below are statistics about DEA-accredited
        research projects in the UK, classified by research theme (percentage of projects
        per year assigned to each theme).

        Overall theme totals (number of projects):
        {totals_str}

        Theme share by year (% of projects that year):
        {year_str}

        Please write a concise analytical summary (4–6 paragraphs) covering:
        1. The dominant research themes overall
        2. Notable trends — which themes are growing, declining, or stable
        3. Any theme that spiked in a particular year and why (e.g. COVID-19 in 2020)
        4. What this tells us about the evolving use of administrative data in UK research
        5. Any gaps or emerging areas that might grow in future

        Write in a professional but accessible style, suitable for a policy briefing.
    """).strip()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def save_outputs(df_classified: pd.DataFrame, trends: dict, narrative: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # Flatten themes list to semicolon-separated string for CSV
    df_out = df_classified.copy()
    df_out["themes"] = df_out["themes"].apply(
        lambda x: "; ".join(x) if isinstance(x, list) else str(x)
    )
    df_out.to_csv(os.path.join(output_dir, "theme_classifications.csv"), index=False, encoding="utf-8-sig")

    trends["by_year"].to_csv(os.path.join(output_dir, "theme_trends_by_year.csv"), index=False, encoding="utf-8-sig")
    trends["by_quarter"].to_csv(os.path.join(output_dir, "theme_trends_by_quarter.csv"), index=False, encoding="utf-8-sig")
    trends["totals"].to_csv(os.path.join(output_dir, "theme_totals.csv"), index=False, encoding="utf-8-sig")

    with open(os.path.join(output_dir, "theme_summary.txt"), "w", encoding="utf-8") as f:
        f.write(narrative)

    print(f"\n[output] Files saved to {output_dir}/")
    print("  - theme_classifications.csv")
    print("  - theme_trends_by_year.csv")
    print("  - theme_trends_by_quarter.csv")
    print("  - theme_totals.csv")
    print("  - theme_summary.txt")


def print_quick_stats(trends: dict):
    print("\n=== Theme Totals ===")
    print(trends["totals"].to_string(index=False))

    print("\n=== Theme Share by Year (top themes) ===")
    top_themes = trends["totals"]["theme"].head(8).tolist()
    pivot = (
        trends["by_year"][trends["by_year"]["theme"].isin(top_themes)]
        .pivot(index="Year", columns="theme", values="pct")
        .fillna(0)
        .round(1)
    )
    print(pivot.to_string())


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
    print(f"[data] {len(df):,} DEA projects loaded, years {df['Year'].min()}–{df['Year'].max()}")

    # Classify themes
    df_classified = classify_all(df, client)

    # Compute trends
    print("\n[analysis] Computing theme trends...")
    trends = analyse_trends(df_classified)
    print_quick_stats(trends)

    # Generate narrative
    print("\n[llm] Generating narrative summary...")
    narrative = generate_narrative_summary(client, df_classified, trends)
    print("\n--- NARRATIVE SUMMARY ---")
    print(narrative)

    # Save outputs
    save_outputs(df_classified, trends, narrative, OUTPUT_DIR)
    print("\n[done]")
