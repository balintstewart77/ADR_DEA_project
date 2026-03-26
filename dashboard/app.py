"""
DEA Accredited Projects Dashboard
===================================
Interactive Dash app for exploring access requests under the Digital Economy Act,
focusing on ADR UK flagship datasets.

Run with:
    python dashboard/app.py

Then open http://127.0.0.1:8050 in your browser.
"""

import os
import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc

# ---------------------------------------------------------------------------
# 1. Data loading & processing
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]


def load_raw(data_dir=DATA_DIR):
    for fname in CANDIDATE_FILES:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(f"[data] Loaded {len(df)} rows from {fname}")
            return df, fname
    raise FileNotFoundError("No DEA projects CSV found in data/")


FLAGSHIP_COLLECTIONS = {
    "Data First": [
        "moj data first",
        "data first",
        "cross-justice",
        "cross justice",
        "crown court",
        "magistrates court",
        "magistrates' court",
        "prisoner dataset",
        "prisoner custodial journey",
        "probation dataset",
        "probation iteration",
        "family court",
        "civil court",
        "cafcass",
        "familyman",
        "offender assessment dataset",
    ],
    "LEO": [
        "longitudinal education outcomes",
        " leo ",
        ": leo",  # matches LEO after provider colon (e.g. "Department for Education: LEO")
        "leo via srs",
        "leo srs",
    ],
    "ECHILD": [
        "education and child health insights",
        "echild",
    ],
    "Growing up in England": [
        "growing up in england",
        "guie",
    ],
    "Wage and Employment Dynamics": [
        "annual survey of hours and earnings longitudinal",
        "annual survey of hours and earnings linked",
        "ashe longitudinal",
        "ashe linked",
        "wage and employment dynamics",
    ],
    "GRADE": [
        "grading and admissions data england",
        " grade ",
    ],
    "Agricultural Research Collection": [
        "agricultural research collection",
    ],
}

DATASET_LABELS = {
    "data first: crown court dataset": ("Data First", "Crown Court Dataset"),
    "data first: magistrates court dataset": ("Data First", "Magistrates Court Dataset"),
    "data first: cross-justice system linking dataset": ("Data First", "Cross-Justice System Linking Dataset"),
    "data first: prisoner dataset": ("Data First", "Prisoner Dataset"),
    "data first: prisoner custodial journey": ("Data First", "Prisoner Custodial Journey"),
    "data first: probation dataset": ("Data First", "Probation Dataset"),
    "data first: family court dataset": ("Data First", "Family Court Dataset"),
    "data first: family court linked to cafcass and census 2021": ("Data First", "Family Court Linked to CAFCASS"),
    "data first: civil court data": ("Data First", "Civil Court Data"),
    "data first: offender assessment dataset": ("Data First", "Offender Assessment Dataset"),
    "longitudinal education outcomes": ("LEO", "Longitudinal Education Outcomes"),
    "education and child health insights from linked data": ("ECHILD", "ECHILD"),
    "growing up in england": ("Growing up in England", "Growing up in England"),
    "annual survey of hours and earnings longitudinal": ("Wage and Employment Dynamics", "ASHE Longitudinal"),
    "annual survey of hours and earnings linked to census 2011": ("Wage and Employment Dynamics", "ASHE Linked to Census 2011"),
    "annual survey of hours and earnings linked to paye and self-assessment data": (
        "Wage and Employment Dynamics", "ASHE Linked to PAYE/SA"
    ),
    "grading and admissions data england": ("GRADE", "GRADE"),
    "agricultural research collection": ("Agricultural Research Collection", "Agricultural Research Collection"),
}

# -- Cohesive colour palette ------------------------------------------------

COLLECTION_COLOURS = {
    "Data First":                       "#3366cc",
    "LEO":                              "#dc3912",
    "ECHILD":                           "#109618",
    "Growing up in England":            "#ff9900",
    "Wage and Employment Dynamics":     "#6a3d9a",
    "GRADE":                            "#0099c6",
    "Agricultural Research Collection": "#e377c2",
}

PRIMARY_BAR = "#2a9d8f"
SECONDARY_BAR = "#e76f51"


def classify_collection(datasets_str: str) -> list[str]:
    """Return list of matching collection names for a datasets string."""
    if not isinstance(datasets_str, str):
        return []
    s = datasets_str.lower()
    matches = []
    for col, keywords in FLAGSHIP_COLLECTIONS.items():
        if any(kw in s for kw in keywords):
            matches.append(col)
    return matches


def count_collection_usages(datasets_str: str) -> list[str]:
    """Return one collection entry per individual dataset match.

    If a project uses Crown Court + Magistrates Court + Prisoner Dataset,
    this returns ["Data First", "Data First", "Data First"] — counting each
    dataset access request separately, consistent with the notebook methodology.
    """
    if not isinstance(datasets_str, str):
        return []
    # Split into individual dataset entries (same logic as parse_datasets)
    entries = []
    for line in datasets_str.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            _, rest = line.split(":", 1)
            parts = re.split(r"[,&]", rest)
        else:
            parts = [line]
        for p in parts:
            p = p.strip().lower()
            if p:
                entries.append(p)

    usages = []
    for entry in entries:
        for col, keywords in FLAGSHIP_COLLECTIONS.items():
            if any(kw in entry for kw in keywords):
                usages.append(col)
                break  # each entry maps to at most one collection
    return usages


def process_data(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Returns:
        df_all      -- full cleaned dataset (one row per project)
        df_flagship -- exploded dataset (one row per project x collection)
        stats       -- dict of row counts at each processing step
    """
    stats = {}
    df = df_raw.copy()

    col_map = {
        "Project Number": "Project ID",
        "Project Name": "Title",
        "Accredited Researchers": "Researchers",
        "Legal Gateway": "Legal Basis",
        "Protected Data Accessed": "Datasets Used",
        "Processing Environment": "Secure Research Service",
    }
    df = df.rename(columns=col_map)
    stats["raw_loaded"] = len(df)

    df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    n_before = len(df)
    df = df.dropna(subset=["Accreditation Date"])
    stats["dropped_no_date"] = n_before - len(df)

    if "Legal Basis" in df.columns:
        n_before = len(df)
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]
        stats["dropped_non_dea"] = n_before - len(df)
    else:
        stats["dropped_non_dea"] = 0

    stats["after_filters"] = len(df)

    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")
    df["quarter_date"] = df["Quarter"].dt.to_timestamp()

    df["collections"] = df["Datasets Used"].apply(classify_collection)
    df["is_flagship"] = df["collections"].apply(lambda x: len(x) > 0)

    # Explode by individual dataset usage (not just unique collection per project).
    # A project using 3 Data First datasets produces 3 rows, counting each access request.
    df["collection_usages"] = df["Datasets Used"].apply(count_collection_usages)
    flagship_rows = []
    for _, row in df[df["is_flagship"]].iterrows():
        for coll in row["collection_usages"]:
            flagship_rows.append({**row.to_dict(), "collection": coll})
    df_flagship = pd.DataFrame(flagship_rows)

    return df, df_flagship, stats


# Regex patterns mapping dataset name variants to a canonical name.
# Each entry: (compiled regex matched against the normalised name, canonical label).
DATASET_ALIASES = [
    (re.compile(r"(?i)^longitudinal education outcomes.*"), "Longitudinal Education Outcomes"),
    (re.compile(r"(?i)^leo\b.*"), "Longitudinal Education Outcomes"),
]


def _normalise_dataset_name(name: str) -> str:
    """Strip geographic suffixes, then apply alias rules."""
    # Strip trailing geographic qualifiers
    name = re.sub(
        r"\s*-\s*(UK|GB|Great Britain|England|England and Wales|Wales|Scotland|Northern Ireland)\s*$",
        "", name, flags=re.IGNORECASE,
    ).strip()
    # Apply alias patterns
    for pattern, canonical in DATASET_ALIASES:
        if pattern.match(name):
            return canonical
    return name


def parse_datasets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the 'Datasets Used' column into one row per project x dataset.
    Returns DataFrame with columns: Project ID, Year, quarter_date, provider, dataset, dataset_full.
    """
    rows = []
    for _, proj in df.iterrows():
        raw = proj.get("Datasets Used", "")
        if not isinstance(raw, str) or not raw.strip():
            continue
        pid = proj["Project ID"]
        year = proj["Year"]
        qd = proj["quarter_date"]
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                provider, rest = line.split(":", 1)
                provider = provider.strip()
                parts = re.split(r"[,&]", rest)
            else:
                provider = ""
                parts = [line]
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                name_norm = _normalise_dataset_name(p)
                rows.append({
                    "Project ID": pid,
                    "Year": year,
                    "quarter_date": qd,
                    "provider": provider,
                    "dataset": name_norm,
                    "dataset_full": f"{provider}: {p}" if provider else p,
                })
    return pd.DataFrame(rows)


# Load data once at startup
df_raw, source_file = load_raw()
df_all, df_flagship, PROCESSING_STATS = process_data(df_raw)

# Deduplicate by Project ID (raw data contains duplicates)
_n_before = len(df_all)
df_all = df_all.drop_duplicates(subset=["Project ID"], keep="first").reset_index(drop=True)
PROCESSING_STATS["dropped_duplicates"] = _n_before - len(df_all)
PROCESSING_STATS["final_rows"] = len(df_all)
if PROCESSING_STATS["dropped_duplicates"] > 0:
    print(f"[data] Dropped {PROCESSING_STATS['dropped_duplicates']} duplicate Project IDs "
          f"({_n_before} -> {len(df_all)})")
df_flagship = df_flagship.drop_duplicates(subset=["Project ID", "collection"], keep="first").reset_index(drop=True)

# Parse individual dataset usage
df_datasets = parse_datasets(df_all)

COLLECTIONS = sorted(df_flagship["collection"].unique()) if len(df_flagship) else list(FLAGSHIP_COLLECTIONS.keys())
DATA_DATE = df_all["Accreditation Date"].max().strftime("%d %B %Y") if len(df_all) else "unknown"
TOTAL_PROJECTS = len(df_all)
TOTAL_FLAGSHIP = df_flagship["Project ID"].nunique() if len(df_flagship) else 0
TOTAL_FLAGSHIP_REQUESTS = len(df_flagship) if len(df_flagship) else 0
YEAR_RANGE = f"{int(df_all['Year'].min())}--{int(df_all['Year'].max())}" if len(df_all) else ""


# ---------------------------------------------------------------------------
# 2. Plotly template & chart helpers
# ---------------------------------------------------------------------------

# Shared template for all charts -- consistent look with minimal clutter
_template = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            size=13,
            color="#2c3e50",
        ),
        title=dict(
            font=dict(size=15, color="#2c3e50"),
            x=0.01, xanchor="left",
            y=0.97, yanchor="top",
            yref="container",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=56, r=24, t=80, b=48),
        xaxis=dict(
            gridcolor="#ecf0f1",
            linecolor="#bdc3c7",
            linewidth=1,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#ecf0f1",
            linecolor="#bdc3c7",
            linewidth=1,
            showgrid=True,
            zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#ecf0f1",
            borderwidth=1,
            font=dict(size=11),
            orientation="h",
            yanchor="bottom", y=1.08,
            xanchor="left", x=0,
        ),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#bdc3c7",
            font_size=12,
        ),
    )
)
pio.templates["dea"] = _template
pio.templates.default = "dea"

CHART_HEIGHT = 400
CHART_CONFIG = {"displayModeBar": False}


def _apply_common(fig: go.Figure, height: int = CHART_HEIGHT) -> go.Figure:
    """Apply shared styling to any figure."""
    fig.update_layout(height=height)
    return fig


def make_quarterly_chart(df: pd.DataFrame) -> go.Figure:
    counts = (
        df.groupby("quarter_date")["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig = px.bar(
        counts, x="quarter_date", y="Projects",
        title="New DEA-Accredited Projects by Quarter",
        labels={"quarter_date": "Quarter", "Projects": "New projects"},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig.update_layout(xaxis_tickformat="%b %Y", bargap=0.15)
    fig.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y} projects<extra></extra>",
    )
    return _apply_common(fig)


def make_yearly_chart(df: pd.DataFrame) -> go.Figure:
    yearly = df.groupby("Year")["Project ID"].count().reset_index()
    yearly.columns = ["Year", "Projects"]
    fig = px.bar(
        yearly, x="Year", y="Projects",
        title="New DEA Projects by Year",
        color_discrete_sequence=[SECONDARY_BAR],
    )
    fig.update_layout(bargap=0.25, xaxis_dtick=1)
    fig.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>%{y} projects<extra></extra>",
    )
    return _apply_common(fig)


def make_srs_chart(df: pd.DataFrame) -> go.Figure:
    srs = (
        df["Secure Research Service"]
        .str.strip()
        .value_counts()
        .reset_index()
    )
    srs.columns = ["SRS", "Count"]
    srs["SRS"] = srs["SRS"].str.replace(" Secure Research Service", "", regex=False)

    # Collapse small slices into "Other"
    threshold = srs["Count"].sum() * 0.03
    small = srs[srs["Count"] < threshold]
    if len(small) > 0:
        srs = srs[srs["Count"] >= threshold].copy()
        srs = pd.concat([srs, pd.DataFrame([{"SRS": "Other", "Count": small["Count"].sum()}])],
                        ignore_index=True)

    fig = px.pie(
        srs, names="SRS", values="Count",
        title="Projects by Trusted Research Environment Provider",
        color_discrete_sequence=["#2a9d8f", "#264653", "#e9c46a", "#e76f51", "#f4a261",
                                 "#606c38", "#457b9d", "#bc6c25", "#8d99ae"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        insidetextorientation="horizontal",
        hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent})<extra></extra>",
        textfont_size=12,
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=8, r=8, t=56, b=8),
    )
    return _apply_common(fig)


def make_collection_line_chart(df_flag: pd.DataFrame) -> go.Figure:
    counts = (
        df_flag.groupby(["quarter_date", "collection"])["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig = px.line(
        counts, x="quarter_date", y="Projects", color="collection",
        title="ADR England Flagship Dataset Requests by Quarter",
        labels={"quarter_date": "Quarter", "Projects": "New projects", "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
        markers=True,
    )
    fig.update_layout(xaxis_tickformat="%b %Y")
    fig.update_traces(line_width=2.5, marker_size=6)
    return _apply_common(fig, height=CHART_HEIGHT + 20)


def make_collection_totals_chart(df_flag: pd.DataFrame) -> go.Figure:
    totals = (
        df_flag.groupby("collection")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Total Projects"})
        .sort_values("Total Projects", ascending=True)
    )
    fig = px.bar(
        totals, x="Total Projects", y="collection", orientation="h",
        title="Total Dataset Access Requests per Collection",
        labels={"collection": "", "Total Projects": "Access requests"},
        color="collection",
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(showlegend=False, yaxis_tickfont_size=12, margin=dict(l=220))
    fig.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>%{x} projects<extra></extra>",
    )
    return _apply_common(fig)


def make_cumulative_chart(df_flag: pd.DataFrame, selected_collections: list) -> go.Figure:
    sub = df_flag if not selected_collections else df_flag[df_flag["collection"].isin(selected_collections)]
    counts = (
        sub.groupby(["quarter_date", "collection"])["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "New"})
    )
    counts = counts.sort_values("quarter_date")
    counts["Cumulative"] = counts.groupby("collection")["New"].cumsum()
    fig = px.area(
        counts, x="quarter_date", y="Cumulative", color="collection",
        title="Cumulative Access Requests (ADR England Flagship Datasets)",
        labels={"quarter_date": "Quarter", "Cumulative": "Cumulative requests", "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(
        xaxis_tickformat="%b %Y",
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=160),
    )
    fig.update_traces(line_width=2)
    return _apply_common(fig)


# ---------------------------------------------------------------------------
# 3. App layout
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
/* Navbar */
.dea-navbar {
    background: linear-gradient(135deg, #1a252f 0%, #2c3e50 100%) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12);
    padding: 0.65rem 0;
}
.dea-navbar .navbar-brand {
    font-size: 1.15rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: #ecf0f1 !important;
}
.dea-navbar .nav-meta {
    font-size: 0.78rem;
    color: #95a5a6;
    letter-spacing: 0.01em;
}

/* Stat cards */
.stat-card {
    border: none;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s, transform 0.2s;
    overflow: hidden;
}
.stat-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    transform: translateY(-2px);
}
.stat-card .card-body {
    padding: 1.1rem 1.25rem;
    border-left: 4px solid var(--accent-color, #3366cc);
}
.stat-number {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 0.15rem;
    color: var(--accent-color, #2c3e50);
}
.stat-label {
    font-size: 0.82rem;
    color: #7f8c8d;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0;
}

/* Tabs */
.dea-tabs .nav-link {
    font-weight: 500;
    font-size: 0.92rem;
    color: #7f8c8d;
    border: none;
    padding: 0.6rem 1.2rem;
}
.dea-tabs .nav-link.active {
    color: #2c3e50 !important;
    border-bottom: 2.5px solid #3366cc !important;
    background: transparent !important;
}
.dea-tabs {
    border-bottom: 1px solid #ecf0f1;
    margin-bottom: 1.25rem;
}

/* Section description text */
.section-desc {
    font-size: 0.88rem;
    color: #7f8c8d;
    margin-bottom: 1rem;
    line-height: 1.5;
}

/* Chart containers */
.chart-wrapper {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    padding: 4px;
    margin-bottom: 1rem;
}

/* Table */
.dea-table .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: #2c3e50 !important;
    color: white !important;
    font-weight: 600;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 10px 12px !important;
    border: none !important;
}
.dea-table .dash-spreadsheet-container .dash-spreadsheet-inner td {
    border-color: #f0f0f0 !important;
    font-size: 0.85rem;
}

/* Footer */
.dea-footer {
    text-align: center;
    padding: 1.5rem 0 1rem;
    font-size: 0.78rem;
    color: #95a5a6;
    border-top: 1px solid #ecf0f1;
    margin-top: 2rem;
}

/* Filter controls */
.filter-label {
    font-size: 0.82rem;
    font-weight: 600;
    color: #2c3e50;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 0.3rem;
}

/* Page background */
body {
    background-color: #f8f9fb !important;
}
"""

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="DEA Projects Dashboard",
)

# Inject custom CSS via index_string (compatible with all Dash versions)
app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>""" + CUSTOM_CSS + """</style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# -- Navbar -----------------------------------------------------------------

NAVBAR = html.Nav(
    dbc.Container([
        html.Div([
            html.Span("DEA Accredited Projects", className="navbar-brand"),
            html.Span(" Dashboard", className="navbar-brand", style={"fontWeight": "400"}),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Span(
            f"Data to {DATA_DATE}  \u2022  {source_file}",
            className="nav-meta ms-auto",
        ),
    ], fluid=True, className="d-flex align-items-center"),
    className="dea-navbar navbar",
)

# -- Stat cards -------------------------------------------------------------


def _stat_card(value, label, accent):
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.Div(str(value), className="stat-number"),
                html.P(label, className="stat-label"),
            ]),
            className="stat-card",
            style={"--accent-color": accent},
        ),
        xs=6, md=3,
    )


STAT_CARDS = dbc.Row([
    _stat_card(f"{TOTAL_PROJECTS:,}", "Total DEA Projects", "#3366cc"),
    _stat_card(f"{TOTAL_FLAGSHIP:,}", "Projects Using ADR England Flagship Linked Datasets", "#109618"),
    _stat_card(str(len(COLLECTIONS)), "ADR Collections", "#ff9900"),
    _stat_card(YEAR_RANGE, "Year Range", "#0099c6"),
], className="mb-4 g-3")

# -- Tab content ------------------------------------------------------------

OVERVIEW_TAB = dbc.Tab(label="Overview", tab_id="tab-overview", children=[
    html.P(
        "High-level summary of all DEA-accredited research projects, "
        "including quarterly and yearly trends and processing environment breakdown.",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="overview-quarterly-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="overview-yearly-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=6,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="overview-srs-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=6,
        ),
    ]),
])

FLAGSHIP_TAB = dbc.Tab(label="ADR England Flagship Datasets", tab_id="tab-flagship", children=[
    html.P(
        "Trends for the seven ADR England flagship data collections. "
        "Use the filter below to focus on specific collections.",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col([
            html.Label("Filter by collection", className="filter-label"),
            dcc.Dropdown(
                id="collection-filter",
                options=[{"label": c, "value": c} for c in COLLECTIONS],
                multi=True,
                placeholder="All collections",
                clearable=True,
            ),
        ], md=6),
    ], className="mb-3"),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="flagship-pooled-quarterly", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="flagship-line-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="flagship-totals-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=6,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="flagship-cumulative-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=6,
        ),
    ]),
])

BROWSE_TAB = dbc.Tab(label="Browse Projects", tab_id="tab-browse", children=[
    html.P(
        "Search and filter individual projects. Hover over truncated cells to see full text.",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col([
            html.Label("Collection", className="filter-label"),
            dcc.Dropdown(
                id="browse-collection-filter",
                options=[{"label": "All collections", "value": "ALL"}]
                        + [{"label": c, "value": c} for c in COLLECTIONS],
                value="ALL",
                clearable=False,
            ),
        ], md=3),
        dbc.Col([
            html.Label("Search title / researcher", className="filter-label"),
            dbc.Input(id="browse-search", placeholder="Type to filter\u2026", type="text"),
        ], md=5),
        dbc.Col([
            html.Label("Scope", className="filter-label"),
            dcc.Dropdown(
                id="browse-scope",
                options=[
                    {"label": "All DEA projects", "value": "all"},
                    {"label": "ADR England Flagship only", "value": "flagship"},
                ],
                value="flagship",
                clearable=False,
            ),
        ], md=2),
        dbc.Col([
            html.Label("\u00a0", className="filter-label"),  # spacer for alignment
            html.Div(id="browse-count", className="text-muted small pt-2"),
        ], md=2),
    ], className="mb-3 g-2"),
    html.Div(
        dash_table.DataTable(
            id="browse-table",
            columns=[
                {"name": "Project ID", "id": "Project ID"},
                {"name": "Title", "id": "Title"},
                {"name": "Researchers", "id": "Researchers"},
                {"name": "Datasets Used", "id": "Datasets Used"},
                {"name": "Date", "id": "Accreditation Date"},
                {"name": "Collection", "id": "collection"},
            ],
            page_size=20,
            sort_action="native",
            filter_action="none",
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "8px 12px",
                "fontFamily": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                "fontSize": "13px",
                "whiteSpace": "normal",
                "maxWidth": "350px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "borderBottom": "1px solid #f0f0f0",
            },
            style_header={
                "backgroundColor": "#2c3e50",
                "color": "white",
                "fontWeight": "600",
                "fontSize": "12px",
                "textTransform": "uppercase",
                "letterSpacing": "0.03em",
                "padding": "10px 12px",
                "borderBottom": "none",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#fafbfc"},
            ],
            tooltip_data=[],
            tooltip_delay=0,
            tooltip_duration=None,
        ),
        className="dea-table",
    ),
])

DATASETS_TAB = dbc.Tab(label="All Datasets", tab_id="tab-datasets", children=[
    html.P(
        "Usage patterns across all individual datasets referenced in DEA projects. "
        "Datasets are normalised by stripping geographic suffixes (UK, GB, England, etc.).",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col([
            html.Label("Show top N datasets", className="filter-label"),
            dcc.Dropdown(
                id="datasets-topn",
                options=[{"label": str(n), "value": n} for n in [10, 20, 30, 50]],
                value=20,
                clearable=False,
            ),
        ], md=2),
        dbc.Col([
            html.Label("Provider filter", className="filter-label"),
            dcc.Dropdown(
                id="datasets-provider-filter",
                options=(
                    [{"label": "All providers", "value": "ALL"}]
                    + [{"label": p, "value": p}
                       for p in sorted(df_datasets["provider"].unique()) if p]
                ),
                value="ALL",
                clearable=False,
            ),
        ], md=4),
        dbc.Col([
            html.Label("Exclude flagship datasets", className="filter-label"),
            dcc.Checklist(
                id="datasets-exclude-flagship",
                options=[{"label": " Exclude ADR England flagship", "value": "yes"}],
                value=[],
                className="pt-1",
            ),
        ], md=3),
    ], className="mb-3 g-2"),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="datasets-topn-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="datasets-trend-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=7,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="datasets-provider-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=5,
        ),
    ]),
])

# -- About tab (static content) --------------------------------------------

_about_md = f"""
### Data Source

This dashboard presents data on research projects accredited under the
**Digital Economy Act (DEA) 2017**. The source data is published by the
[UK Statistics Authority (UKSA)](https://uksa.statisticsauthority.gov.uk/digitaleconomyact-research-statistics/better-useofdata-for-research-information-for-researchers/list-of-accredited-researchers-and-research-projects-under-the-research-strand-of-the-digital-economy-act/)
as a public register of accredited researchers and research projects.

The data is downloaded as an Excel file from the UKSA website and converted
to CSV for processing. The dashboard was last refreshed using data up to
**{DATA_DATE}** (source file: `{source_file}`).

---

### Data Processing

The raw data undergoes several cleaning steps before being displayed.
Row counts at each stage:

| Step | Rows | Dropped |
|------|-----:|--------:|
| Loaded from CSV | {PROCESSING_STATS['raw_loaded']:,} | — |
| Rows with missing accreditation date removed | {PROCESSING_STATS['raw_loaded'] - PROCESSING_STATS['dropped_no_date']:,} | {PROCESSING_STATS['dropped_no_date']:,} |
| Filtered to DEA projects only (non-DEA/SRSA rows removed) | {PROCESSING_STATS['after_filters']:,} | {PROCESSING_STATS['dropped_non_dea']:,} |
| Duplicate Project IDs removed (keep first occurrence) | {PROCESSING_STATS['final_rows']:,} | {PROCESSING_STATS['dropped_duplicates']:,} |
| **Final dataset** | **{PROCESSING_STATS['final_rows']:,}** | |

Additional processing: column names are standardised, accreditation dates are
parsed, and year/quarter fields are derived for time-series analysis.

---

### ADR England Flagship Dataset Classification

Seven ADR England flagship data collections are identified by **case-insensitive
keyword matching** against each project's "Datasets Used" field. A project can
match multiple collections if it uses datasets from more than one.

| Collection | Example keywords |
|------------|-----------------|
| Data First | "data first", "crown court", "magistrates court", "prisoner dataset", "civil court", "cafcass", "familyman" |
| LEO | "longitudinal education outcomes", "LEO via SRS" |
| ECHILD | "education and child health insights", "echild" |
| Growing up in England | "growing up in england", "guie" |
| Wage and Employment Dynamics | "annual survey of hours and earnings longitudinal", "ashe linked" |
| GRADE | "grading and admissions data england" |
| Agricultural Research Collection | "agricultural research collection" |

#### Counting methodology

The ADR England Flagship Datasets tab counts **individual dataset access
requests**, not unique projects. If a single project accesses three Data First
datasets (e.g. Crown Court, Magistrates Court, and Prisoner), this counts as
**three** Data First access requests. This approach reflects the demand placed
on each dataset and is consistent with the methodology used in the accompanying
analysis notebook.

The stat card ("Projects Using ADR England Flagship Linked Datasets") counts
**unique projects** — i.e. how many distinct projects use at least one flagship
dataset. These two numbers will always differ because a single project often
requests multiple datasets from the same collection.

---

### Individual Dataset Parsing (All Datasets Tab)

The "Datasets Used" free-text field is parsed into individual dataset entries:

1. **Split by newline** — each line typically represents one data provider
2. **Split by colon** — separates the provider name from the dataset list
3. **Split by comma and ampersand** — separates individual datasets within a provider
4. **Geographic suffixes stripped** — e.g. "- UK", "- England and Wales" are removed for grouping
5. **Name aliases applied** — variant names are mapped to canonical labels
   (e.g. "LEO via SRS Iteration 1 Standard Extract" → "Longitudinal Education Outcomes")

---

### Definitions

- **DEA (Digital Economy Act 2017)** — UK legislation that provides a legal
  framework for accredited researchers to access de-identified government
  administrative data for research purposes.

- **Trusted Research Environment (TRE)** — Accredited secure computing
  environments where researchers can access protected data without it leaving
  the secure setting. Examples include the ONS Secure Research Service (SRS)
  and the SAIL Databank.

- **ADR England Flagship Datasets** — Seven linked administrative data
  collections curated by ADR England for cross-domain research, spanning
  justice, education, health, employment, and agriculture.

---

### Limitations and Caveats

- **Keyword matching** may miss dataset names not yet included in the keyword
  lists, or match false positives where keywords appear incidentally.
- **Dataset parsing** splits on commas and ampersands, which can incorrectly
  break provider names that contain these characters
  (e.g. "Department for Business, Energy & Industrial Strategy").
- **Duplicate handling** uses Project ID only; genuine re-accreditations
  sharing the same ID are collapsed to a single entry.
- **Small TRE provider categories** (under 3% of total projects) are grouped
  as "Other" in the pie chart for readability.
- **Project titles** alone may not fully describe the scope of a research project.

---

### LLM Theme Classification Methodology

A separate analysis script (`llm_theme_analysis_v3.py`) classifies project
titles using a three-layer framework:

- **Layer A — Substantive Domain** (1 or more from 14 themes, e.g. "Education &
  Skills", "Health & Social Care", "Crime & Justice")
- **Layer B — Linkage Mode** (exactly 1: Single-Dataset, Within-Domain,
  Cross-Domain, or Multi-Domain Linkage)
- **Layer C — Analytical Purpose** (1 or 2, e.g. "Policy Evaluation",
  "Descriptive Monitoring", "Life-Course Analysis")

Classification is performed by Claude (claude-opus-4-6) using structured output
via the Anthropic API. Results are cached locally to avoid re-classification.
A narrative summary is auto-generated from the aggregate statistics.

**Note:** Classification is based on project titles only, which limits accuracy —
titles may not fully convey the research methodology or all datasets used.
"""

ABOUT_TAB = dbc.Tab(label="About", tab_id="tab-about", children=[
    dbc.Row([
        dbc.Col([
            dcc.Markdown(
                _about_md,
                style={
                    "fontSize": "0.88rem",
                    "lineHeight": "1.65",
                    "color": "#2c3e50",
                },
            ),
        ], md=10, lg=8),
    ], justify="center", className="py-3"),
])

# -- Full layout ------------------------------------------------------------

app.layout = html.Div([
    NAVBAR,
    dbc.Container([
        html.Div(style={"height": "1.25rem"}),  # spacer below navbar
        STAT_CARDS,
        dbc.Tabs(
            [OVERVIEW_TAB, DATASETS_TAB, FLAGSHIP_TAB, BROWSE_TAB, ABOUT_TAB],
            id="main-tabs",
            active_tab="tab-overview",
            className="dea-tabs",
        ),
        html.Footer(
            f"DEA Accredited Projects Dashboard  \u2022  Data sourced from UKSA  \u2022  "
            f"Last updated {DATA_DATE}",
            className="dea-footer",
        ),
    ], fluid=True),
])


# ---------------------------------------------------------------------------
# 4. Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    Output("overview-quarterly-chart", "figure"),
    Output("overview-yearly-chart", "figure"),
    Output("overview-srs-chart", "figure"),
    Input("main-tabs", "active_tab"),
)
def update_overview(_tab):
    return (
        make_quarterly_chart(df_all),
        make_yearly_chart(df_all),
        make_srs_chart(df_all),
    )


@app.callback(
    Output("flagship-pooled-quarterly", "figure"),
    Output("flagship-line-chart", "figure"),
    Output("flagship-totals-chart", "figure"),
    Output("flagship-cumulative-chart", "figure"),
    Input("collection-filter", "value"),
)
def update_flagship(selected_collections):
    if not len(df_flagship):
        empty = go.Figure().update_layout(title="No ADR England flagship data available")
        return empty, empty, empty, empty

    sub = df_flagship
    if selected_collections:
        sub = df_flagship[df_flagship["collection"].isin(selected_collections)]

    # Pooled quarterly: count unique projects per quarter across all (filtered) collections
    pooled = (
        sub.groupby("quarter_date")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig_pooled = px.bar(
        pooled, x="quarter_date", y="Projects",
        title="All ADR England Flagship Requests by Quarter (Pooled)",
        labels={"quarter_date": "Quarter", "Projects": "Distinct projects"},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig_pooled.update_layout(xaxis_tickformat="%b %Y", bargap=0.15)
    fig_pooled.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{x|%b %Y}</b><br>%{y} projects<extra></extra>",
    )
    _apply_common(fig_pooled)

    return (
        fig_pooled,
        make_collection_line_chart(sub),
        make_collection_totals_chart(sub),
        make_cumulative_chart(df_flagship, selected_collections or []),
    )


@app.callback(
    Output("browse-table", "data"),
    Output("browse-table", "tooltip_data"),
    Output("browse-count", "children"),
    Input("browse-collection-filter", "value"),
    Input("browse-search", "value"),
    Input("browse-scope", "value"),
)
def update_browse_table(collection, search, scope):
    if scope == "flagship" and len(df_flagship):
        # One row per unique project; join collection names for multi-collection projects
        coll_labels = (
            df_flagship.groupby("Project ID")["collection"]
            .apply(lambda x: ", ".join(sorted(x.unique())))
            .rename("collection")
        )
        base = df_all[df_all["is_flagship"]].drop_duplicates(subset=["Project ID"]).copy()
        base["collection"] = base["Project ID"].map(coll_labels)
    else:
        base = df_all.copy()
        base["collection"] = base["collections"].apply(
            lambda x: ", ".join(x) if x else ""
        )

    if collection and collection != "ALL":
        base = base[base["collection"] == collection]

    if search:
        mask = (
            base["Title"].str.contains(search, case=False, na=False)
            | base["Researchers"].str.contains(search, case=False, na=False)
        )
        base = base[mask]

    base["Accreditation Date"] = pd.to_datetime(base["Accreditation Date"]).dt.strftime("%d %b %Y")

    display_cols = ["Project ID", "Title", "Researchers", "Datasets Used", "Accreditation Date", "collection"]
    table_data = base[display_cols].to_dict("records")

    tooltip_data = [
        {
            col: {"value": str(row.get(col, "")), "type": "markdown"}
            for col in display_cols
        }
        for row in table_data
    ]

    count_text = f"Showing {len(table_data):,} project{'s' if len(table_data) != 1 else ''}"
    return table_data, tooltip_data, count_text


# Build a set of flagship dataset names (normalised) for optional exclusion
_FLAGSHIP_KW_LOWER = []
for kws in FLAGSHIP_COLLECTIONS.values():
    _FLAGSHIP_KW_LOWER.extend(kw.lower() for kw in kws)


def _is_flagship_dataset(name: str) -> bool:
    s = name.lower()
    return any(kw in s for kw in _FLAGSHIP_KW_LOWER)


@app.callback(
    Output("datasets-topn-chart", "figure"),
    Output("datasets-trend-chart", "figure"),
    Output("datasets-provider-chart", "figure"),
    Input("datasets-topn", "value"),
    Input("datasets-provider-filter", "value"),
    Input("datasets-exclude-flagship", "value"),
)
def update_datasets_tab(top_n, provider, exclude_flagship):
    sub = df_datasets.copy()

    if exclude_flagship and "yes" in exclude_flagship:
        sub = sub[~sub["dataset"].apply(_is_flagship_dataset)]

    if provider and provider != "ALL":
        sub = sub[sub["provider"] == provider]

    # -- Top N datasets bar chart --
    dataset_counts = (
        sub.groupby("dataset")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
        .sort_values("Projects", ascending=True)
        .tail(top_n)
    )
    fig_top = px.bar(
        dataset_counts, x="Projects", y="dataset", orientation="h",
        title=f"Top {top_n} Most-Requested Datasets",
        labels={"dataset": "", "Projects": "Distinct projects"},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig_top.update_layout(
        showlegend=False,
        margin=dict(l=320),
        yaxis_tickfont_size=11,
    )
    fig_top.update_traces(
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>%{x} projects<extra></extra>",
    )
    _apply_common(fig_top, height=max(400, top_n * 22))

    # -- Trend: top 5 datasets over time --
    top5 = (
        sub.groupby("dataset")["Project ID"]
        .nunique()
        .nlargest(5)
        .index.tolist()
    )
    trend_data = (
        sub[sub["dataset"].isin(top5)]
        .groupby(["Year", "dataset"])["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig_trend = px.line(
        trend_data, x="Year", y="Projects", color="dataset",
        title="Top 5 Datasets — Usage by Year",
        labels={"dataset": "Dataset"},
        markers=True,
    )
    fig_trend.update_layout(
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=9),
        ),
        margin=dict(r=200),
    )
    fig_trend.update_traces(line_width=2.5, marker_size=6)
    _apply_common(fig_trend)

    # -- Provider breakdown pie --
    prov_counts = (
        sub[sub["provider"] != ""]
        .groupby("provider")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
        .sort_values("Projects", ascending=False)
    )
    # Collapse small providers
    threshold = prov_counts["Projects"].sum() * 0.02
    small = prov_counts[prov_counts["Projects"] < threshold]
    if len(small) > 0:
        prov_counts = prov_counts[prov_counts["Projects"] >= threshold].copy()
        prov_counts = pd.concat(
            [prov_counts, pd.DataFrame([{"provider": "Other", "Projects": small["Projects"].sum()}])],
            ignore_index=True,
        )
    fig_prov = px.pie(
        prov_counts, names="provider", values="Projects",
        title="Projects by Data Provider",
    )
    fig_prov.update_traces(
        textposition="inside",
        textinfo="percent+label",
        insidetextorientation="horizontal",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent})<extra></extra>",
    )
    fig_prov.update_layout(
        showlegend=False,
        margin=dict(l=8, r=8, t=56, b=8),
    )
    _apply_common(fig_prov)

    return fig_top, fig_trend, fig_prov


# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
