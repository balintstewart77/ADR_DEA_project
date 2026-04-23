"""
DEA Accredited Projects Dashboard
===================================
Interactive Dash app for exploring access requests under the Digital Economy Act,
focusing on cross-domain linked datasets.

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

try:
    from dashboard.dataset_normalisation import iter_dataset_entries, parse_datasets
    from dashboard.institution_normalisation import parse_institutions
except ModuleNotFoundError:
    from dataset_normalisation import iter_dataset_entries, parse_datasets
    from institution_normalisation import parse_institutions

# ---------------------------------------------------------------------------
# 1. Data loading & processing
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

SPECIAL_DROP_PROJECT_TITLE_PAIRS = {
    ("2023/113", "The Influence of Early Life Health and Nutritional Environment on Later Life Health and Morbidity"),
}


def load_raw(data_dir=DATA_DIR):
    for fname in CANDIDATE_FILES:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(f"[data] Loaded {len(df)} rows from {fname}")
            return df, fname
    raise FileNotFoundError("No DEA projects CSV found in data/")


def apply_duplicate_policy(df: pd.DataFrame, stats: dict | None = None) -> pd.DataFrame:
    """Remove exact duplicates and same-ID/same-title duplicates, keep conflicting titles."""
    out = df.copy()

    n_before = len(out)
    out = out.drop_duplicates().reset_index(drop=True)
    exact_removed = n_before - len(out)

    special_removed = 0
    same_title_removed = 0
    if "Project ID" in out.columns and "Title" in out.columns:
        out["_title_key"] = out["Title"].fillna("").astype(str).str.strip()
        special_mask = out.apply(
            lambda row: (str(row["Project ID"]), row["_title_key"]) in SPECIAL_DROP_PROJECT_TITLE_PAIRS,
            axis=1,
        )
        n_before = len(out)
        out = out.loc[~special_mask].copy()
        special_removed = n_before - len(out)

        n_before = len(out)
        out = out.drop_duplicates(subset=["Project ID", "_title_key"], keep="first").reset_index(drop=True)
        same_title_removed = n_before - len(out)
        out = out.drop(columns="_title_key")

    if stats is not None:
        stats["dropped_exact_duplicates"] = exact_removed
        stats["dropped_special_duplicate_rows"] = special_removed
        stats["dropped_same_id_same_title"] = same_title_removed

    return out


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
        "annual survey for hours and earnings longitudinal",
        "annual survey for hours and earnings linked",
        "annual survey for hours and earnings / census 2011 linked",
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
    "annual survey of hours and earnings longitudinal": ("Wage and Employment Dynamics", "Annual Survey of Hours and Earnings Longitudinal"),
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

# -- Thematic analysis colour palettes -------------------------------------

DOMAIN_COLOURS = {
    "Labour Market & Employment":           "#2a9d8f",
    "Business & Productivity":              "#264653",
    "Education & Skills":                   "#e9c46a",
    "Health & Social Care":                 "#e76f51",
    "Poverty, Inequality & Living Standards": "#6a3d9a",
    "Gender, Race & Ethnicity":             "#d62728",
    "Migration & Demographics":             "#f4a261",
    "Crime & Justice":                      "#1f77b4",
    "COVID-19 & Pandemic":                  "#ff7f0e",
    "Housing & Planning":                   "#8c564b",
    "Environment & Agriculture":            "#2ca02c",
    "Public Finance & Taxation":            "#9467bd",
    "Data Infrastructure & Methodology":    "#7f7f7f",
    "Unclear from Title":                   "#bcbd22",
}

LINKAGE_COLOURS = {
    "Single-Dataset":           "#a8dadc",
    "Within-Domain Linkage":    "#457b9d",
    "Cross-Domain Linkage":     "#e76f51",
    "Unclear from Title":       "#bdc3c7",
}

PURPOSE_COLOURS = {
    "Descriptive Monitoring":                   "#3366cc",
    "Policy Evaluation / Impact Analysis":      "#dc3912",
    "Outcome Tracking":                         "#109618",
    "Inequality / Disparities Analysis":        "#ff9900",
    "Methodological / Infrastructure Research":  "#0099c6",
    "Life-Course / Trajectory Analysis":        "#6a3d9a",
    "Risk Prediction / Early Identification":   "#e377c2",
    "Service Interaction / Systems Analysis":   "#8c564b",
    "Unclear from Title":                       "#bdc3c7",
}

def classify_collection(datasets_str: str) -> list[str]:
    """Return list of matching collection names for a datasets string."""
    if not isinstance(datasets_str, str):
        return []
    s = " ".join(datasets_str.lower().split())
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
    entries = [
        " ".join(part.lower().split())
        for _, _, part in iter_dataset_entries(datasets_str)
        if part
    ]

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
        df_all      -- full cleaned dataset (one row per retained project record)
        df_flagship -- exploded dataset (one row per dataset request x collection)
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

    df = apply_duplicate_policy(df, stats)
    stats["after_filters"] = len(df)

    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")
    df["quarter_date"] = df["Quarter"].dt.to_timestamp()
    df["Project Row ID"] = [f"proj-{i:04d}" for i in range(len(df))]

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


# Load data once at startup
df_raw, source_file = load_raw()
df_all, df_flagship_requests, PROCESSING_STATS = process_data(df_raw)
PROCESSING_STATS["final_rows"] = len(df_all)
PROCESSING_STATS["retained_conflicting_duplicate_rows"] = int(
    df_all["Project ID"].duplicated(keep=False).sum()
)
df_flagship_projects = (
    df_flagship_requests
    .drop_duplicates(subset=["Project Row ID", "collection"], keep="first")
    .reset_index(drop=True)
)

# Parse individual dataset usage
df_datasets = parse_datasets(df_all)

# Parse institution affiliations
df_institutions = parse_institutions(df_all)

COLLECTIONS = (
    sorted(df_flagship_projects["collection"].unique())
    if len(df_flagship_projects)
    else list(FLAGSHIP_COLLECTIONS.keys())
)
_max_date = df_all["Accreditation Date"].max() if len(df_all) else None
DATA_DATE = _max_date.strftime("%d %B %Y") if _max_date is not None else "unknown"
# Detect whether the latest year is incomplete (data doesn't cover the full year)
PARTIAL_YEAR = int(_max_date.year) if (_max_date is not None and _max_date.month < 12) else None
PARTIAL_YEAR_LABEL = f"{PARTIAL_YEAR}*" if PARTIAL_YEAR else None
PARTIAL_YEAR_NOTE = (
    f"* {PARTIAL_YEAR} data covers Jan–{_max_date.strftime('%b')} only"
    if PARTIAL_YEAR else ""
)
TOTAL_PROJECTS = len(df_all)
TOTAL_DATASET_REQUESTS = len(df_datasets)
TOTAL_FLAGSHIP = df_flagship_projects["Project Row ID"].nunique() if len(df_flagship_projects) else 0
TOTAL_FLAGSHIP_REQUESTS = len(df_flagship_requests) if len(df_flagship_requests) else 0
YEAR_RANGE = f"{int(df_all['Year'].min())}–{int(df_all['Year'].max())}" if len(df_all) else ""
RETAINED_CONFLICTING_DUPLICATE_IDS = sorted(
    df_all.loc[df_all["Project ID"].duplicated(keep=False), "Project ID"].unique().tolist()
)
RETAINED_CONFLICTING_DUPLICATE_IDS_TEXT = (
    ", ".join(RETAINED_CONFLICTING_DUPLICATE_IDS) if RETAINED_CONFLICTING_DUPLICATE_IDS else "None"
)

# -- Thematic analysis data (LLM classification outputs) -------------------

_THEMATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "analysis", "outputs_v3")
THEMATIC_DATA_AVAILABLE = False

try:
    df_thematic_a = pd.read_csv(os.path.join(_THEMATIC_DIR, "layer_a_by_year.csv"), encoding="utf-8-sig")
    df_thematic_b = pd.read_csv(os.path.join(_THEMATIC_DIR, "layer_b_by_year.csv"), encoding="utf-8-sig")
    df_thematic_c = pd.read_csv(os.path.join(_THEMATIC_DIR, "layer_c_by_year.csv"), encoding="utf-8-sig")
    df_thematic_a_totals = pd.read_csv(os.path.join(_THEMATIC_DIR, "layer_a_totals.csv"), encoding="utf-8-sig")
    df_thematic_b_totals = pd.read_csv(os.path.join(_THEMATIC_DIR, "layer_b_totals.csv"), encoding="utf-8-sig")
    df_thematic_c_totals = pd.read_csv(os.path.join(_THEMATIC_DIR, "layer_c_totals.csv"), encoding="utf-8-sig")
    df_cross_mode_domain = pd.read_csv(os.path.join(_THEMATIC_DIR, "cross_mode_domain.csv"), encoding="utf-8-sig")
    df_cross_domain_purpose = pd.read_csv(os.path.join(_THEMATIC_DIR, "cross_domain_purpose.csv"), encoding="utf-8-sig")
    with open(os.path.join(_THEMATIC_DIR, "layer_summary.txt"), "r", encoding="utf-8") as _f:
        THEMATIC_NARRATIVE = _f.read()
    df_thematic_projects = pd.read_csv(
        os.path.join(_THEMATIC_DIR, "layer_classifications.csv"), encoding="utf-8-sig",
    )
    THEMATIC_PROJECT_COUNT = len(df_thematic_projects)

    # Remap legacy "Multi-Domain Linkage" → "Cross-Domain Linkage"
    _LINKAGE_REMAP = {"Multi-Domain Linkage": "Cross-Domain Linkage"}
    for _ldf in [df_thematic_b, df_thematic_b_totals]:
        if "linkage_mode" in _ldf.columns:
            _ldf["linkage_mode"] = _ldf["linkage_mode"].replace(_LINKAGE_REMAP)
    # Aggregate rows that now share the same key after remapping
    if "linkage_mode" in df_thematic_b.columns:
        df_thematic_b = df_thematic_b.groupby(["Year", "linkage_mode"], as_index=False).agg(
            {"count": "sum", "total": "first", "pct_of_projects": "sum"}
        )
    if "linkage_mode" in df_thematic_b_totals.columns:
        df_thematic_b_totals = df_thematic_b_totals.groupby("linkage_mode", as_index=False)["count"].sum()
        df_thematic_b_totals = df_thematic_b_totals.sort_values("count", ascending=False)
    df_thematic_projects["linkage_mode"] = df_thematic_projects["linkage_mode"].replace(_LINKAGE_REMAP)
    # Merge Multi-Domain column into Cross-Domain in cross-tab
    if "Multi-Domain Linkage" in df_cross_mode_domain.columns:
        if "Cross-Domain Linkage" not in df_cross_mode_domain.columns:
            df_cross_mode_domain = df_cross_mode_domain.rename(columns={"Multi-Domain Linkage": "Cross-Domain Linkage"})
        else:
            df_cross_mode_domain["Cross-Domain Linkage"] = (
                df_cross_mode_domain["Cross-Domain Linkage"] + df_cross_mode_domain["Multi-Domain Linkage"]
            )
            df_cross_mode_domain = df_cross_mode_domain.drop(columns=["Multi-Domain Linkage"])

    # Build filter options for the thematic browse table
    _all_domains = sorted({
        d.strip()
        for domains in df_thematic_projects["substantive_domains"].dropna()
        for d in domains.split(";")
        if d.strip()
    })
    _THEMATIC_DOMAIN_OPTIONS = (
        [{"label": "All domains", "value": "ALL"}]
        + [{"label": d, "value": d} for d in _all_domains]
    )
    _all_linkage = sorted(df_thematic_projects["linkage_mode"].dropna().unique())
    _THEMATIC_LINKAGE_OPTIONS = (
        [{"label": "All linkage modes", "value": "ALL"}]
        + [{"label": m, "value": m} for m in _all_linkage]
    )
    _all_purposes = sorted({
        p.strip()
        for purposes in df_thematic_projects["analytical_purpose"].dropna()
        for p in purposes.split(";")
        if p.strip()
    })
    _THEMATIC_PURPOSE_OPTIONS = (
        [{"label": "All purposes", "value": "ALL"}]
        + [{"label": p, "value": p} for p in _all_purposes]
    )

    THEMATIC_DATA_AVAILABLE = True
except (FileNotFoundError, KeyError):
    df_thematic_a = df_thematic_b = df_thematic_c = pd.DataFrame()
    df_thematic_a_totals = df_thematic_b_totals = df_thematic_c_totals = pd.DataFrame()
    df_cross_mode_domain = df_cross_domain_purpose = pd.DataFrame()
    df_thematic_projects = pd.DataFrame()
    THEMATIC_NARRATIVE = ""
    THEMATIC_PROJECT_COUNT = 0
    _THEMATIC_DOMAIN_OPTIONS = []
    _THEMATIC_LINKAGE_OPTIONS = []
    _THEMATIC_PURPOSE_OPTIONS = []


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


def _annotate_partial_year(fig: go.Figure, years=None) -> go.Figure:
    """Add a footnote and asterisked x-tick for the partial final year."""
    if not PARTIAL_YEAR:
        return fig
    if years is not None:
        tickvals = sorted(years)
        ticktext = [f"{yr}*" if yr == PARTIAL_YEAR else str(yr) for yr in tickvals]
        fig.update_xaxes(tickvals=tickvals, ticktext=ticktext)
    fig.add_annotation(
        text=PARTIAL_YEAR_NOTE,
        xref="paper", yref="paper",
        x=1, y=-0.12, showarrow=False,
        font=dict(size=10, color="#7f8c8d"),
        xanchor="right",
    )
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
    # Use a lighter colour for the partial final year
    colours = [
        SECONDARY_BAR if yr != PARTIAL_YEAR else "#f4a582"
        for yr in yearly["Year"]
    ]
    fig = go.Figure(go.Bar(
        x=yearly["Year"], y=yearly["Projects"],
        marker_color=colours,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>%{y} projects<extra></extra>",
    ))
    fig.update_layout(
        title="New DEA Projects by Year",
        xaxis_title="Year", yaxis_title="Projects",
        bargap=0.25, xaxis_dtick=1,
    )
    _annotate_partial_year(fig, years=yearly["Year"])
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
        texttemplate="%{label}<br>%{percent:.0%}",
        insidetextorientation="horizontal",
        hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent:.0%})<extra></extra>",
        textfont_size=12,
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=8, r=8, t=56, b=8),
    )
    return _apply_common(fig)


def _metric_labels(metric_mode: str) -> tuple[str, str]:
    if metric_mode == "requests":
        return "Dataset access requests", "requests"
    return "Distinct projects", "projects"


def make_collection_line_chart(df_flag: pd.DataFrame, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    counts = (
        df_flag.groupby(["quarter_date", "collection"])
        .size()
        .reset_index()
        .rename(columns={0: "Value"})
    )
    fig = px.line(
        counts, x="quarter_date", y="Value", color="collection",
        title=f"Cross-Domain Linked {metric_label} by Quarter",
        labels={"quarter_date": "Quarter", "Value": metric_label, "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
        markers=True,
    )
    fig.update_layout(xaxis_tickformat="%b %Y")
    fig.update_traces(
        line_width=2.5,
        marker_size=6,
        hovertemplate=f"<b>%{{fullData.name}}</b><br>%{{x|%b %Y}}<br>%{{y}} {title_noun}<extra></extra>",
    )
    return _apply_common(fig, height=CHART_HEIGHT + 20)


def make_collection_yearly_line_chart(df_flag: pd.DataFrame, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    counts = (
        df_flag.groupby(["Year", "collection"])
        .size()
        .reset_index()
        .rename(columns={0: "Value"})
    )
    fig = px.line(
        counts, x="Year", y="Value", color="collection",
        title=f"Cross-Domain Linked {metric_label} by Year",
        labels={"Year": "Year", "Value": metric_label, "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
        markers=True,
    )
    fig.update_layout(xaxis_dtick=1)
    fig.update_traces(
        line_width=2.5,
        marker_size=6,
        hovertemplate=f"<b>%{{fullData.name}}</b><br>%{{x}}<br>%{{y}} {title_noun}<extra></extra>",
    )
    _annotate_partial_year(fig, years=counts["Year"].unique())
    return _apply_common(fig, height=CHART_HEIGHT + 20)


def make_collection_totals_chart(df_flag: pd.DataFrame, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    totals = (
        df_flag.groupby("collection")
        .size()
        .reset_index()
        .rename(columns={0: "Value"})
        .sort_values("Value", ascending=True)
    )
    fig = px.bar(
        totals, x="Value", y="collection", orientation="h",
        title=f"Total Cross-Domain Linked {metric_label} per Collection",
        labels={"collection": "", "Value": metric_label},
        color="collection",
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(showlegend=False, yaxis_tickfont_size=12, margin=dict(l=220))
    fig.update_traces(
        marker_line_width=0,
        hovertemplate=f"<b>%{{y}}</b><br>%{{x}} {title_noun}<extra></extra>",
    )
    return _apply_common(fig)


def make_cumulative_chart(df_flag: pd.DataFrame, selected_collections: list, metric_mode: str) -> go.Figure:
    metric_label, title_noun = _metric_labels(metric_mode)
    sub = df_flag if not selected_collections else df_flag[df_flag["collection"].isin(selected_collections)]
    counts = (
        sub.groupby(["quarter_date", "collection"])
        .size()
        .reset_index()
        .rename(columns={0: "New"})
    )
    counts = counts.sort_values("quarter_date")
    counts["Cumulative"] = counts.groupby("collection")["New"].cumsum()
    fig = px.area(
        counts, x="quarter_date", y="Cumulative", color="collection",
        title=f"Cumulative Cross-Domain Linked {metric_label}",
        labels={"quarter_date": "Quarter", "Cumulative": f"Cumulative {title_noun}", "collection": "Collection"},
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
    fig.update_traces(
        line_width=2,
        hovertemplate=f"<b>%{{fullData.name}}</b><br>%{{x|%b %Y}}<br>%{{y}} cumulative {title_noun}<extra></extra>",
    )
    return _apply_common(fig)


def make_institution_bar(df_inst: pd.DataFrame, top_n: int = 20) -> go.Figure:
    """Horizontal bar chart of top institutions by project count."""
    counts = (
        df_inst.groupby("institution")["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
        .sort_values("Projects", ascending=True)
        .tail(top_n)
    )
    fig = px.bar(
        counts, x="Projects", y="institution", orientation="h",
        title=f"Top {top_n} Institutions by Number of DEA Projects",
        labels={"institution": "", "Projects": "Number of projects"},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{x} projects<extra></extra>",
    )
    fig.update_layout(
        margin=dict(l=280),
        height=max(400, top_n * 24),
        yaxis_tickfont=dict(size=11),
    )
    return _apply_common(fig, height=max(400, top_n * 24))


def make_institution_trend(df_inst: pd.DataFrame, top_n: int = 8) -> go.Figure:
    """Line chart of projects per year for the top institutions."""
    top_insts = (
        df_inst.groupby("institution")["Project ID"]
        .nunique()
        .nlargest(top_n)
        .index.tolist()
    )
    sub = df_inst[df_inst["institution"].isin(top_insts)]
    yearly = (
        sub.groupby(["Year", "institution"])["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig = px.line(
        yearly, x="Year", y="Projects", color="institution",
        title=f"Projects per Year — Top {top_n} Institutions",
        labels={"institution": "Institution", "Projects": "Projects"},
        markers=True,
    )
    fig.update_layout(
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=200),
    )
    fig.update_traces(line_width=2.5)
    _annotate_partial_year(fig, years=yearly["Year"].unique())
    return _apply_common(fig)


# -- Thematic analysis chart helpers ----------------------------------------

def make_thematic_trend(
    df_by_year: pd.DataFrame,
    category_col: str,
    colour_map: dict,
    metric_col: str,
    title: str,
    height: int = 480,
) -> go.Figure:
    """Multi-line trend chart for a thematic layer (domains or purposes)."""
    fig = go.Figure()
    for cat in df_by_year[category_col].unique():
        sub = df_by_year[df_by_year[category_col] == cat].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=sub["Year"], y=sub[metric_col],
            mode="lines+markers",
            name=cat,
            line=dict(color=colour_map.get(cat, "#999"), width=2.5),
            marker=dict(size=6),
            hovertemplate=(
                f"<b>{cat}</b><br>"
                "%{x}<br>"
                + ("%{y:.1f}%" if metric_col == "pct_of_projects" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))
    yaxis_title = "% of projects" if metric_col == "pct_of_projects" else "Projects"
    fig.update_layout(
        title=title,
        xaxis_title="Year", yaxis_title=yaxis_title,
        xaxis_dtick=1,
        legend=dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.02,
            font=dict(size=10),
        ),
        margin=dict(r=260),
    )
    _annotate_partial_year(fig, years=df_by_year["Year"].unique())
    return _apply_common(fig, height=height)


def make_linkage_area(
    df_by_year: pd.DataFrame,
    colour_map: dict,
    metric_col: str,
) -> go.Figure:
    """Stacked area chart for linkage modes (single-label, compositional)."""
    order = ["Single-Dataset", "Within-Domain Linkage", "Cross-Domain Linkage",
             "Unclear from Title"]
    present = [m for m in order if m in df_by_year["linkage_mode"].values]
    fig = go.Figure()
    for mode in present:
        sub = df_by_year[df_by_year["linkage_mode"] == mode].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=sub["Year"], y=sub[metric_col],
            mode="lines",
            name=mode,
            stackgroup="one",
            line=dict(color=colour_map.get(mode, "#999"), width=0.5),
            fillcolor=colour_map.get(mode, "#999"),
            hovertemplate=(
                f"<b>{mode}</b><br>"
                "%{x}<br>"
                + ("%{y:.1f}%" if metric_col == "pct_of_projects" else "%{y} projects")
                + "<extra></extra>"
            ),
        ))
    yaxis_title = "% of projects" if metric_col == "pct_of_projects" else "Projects"
    fig.update_layout(
        title="Data Linkage Complexity Over Time",
        xaxis_title="Year", yaxis_title=yaxis_title,
        xaxis_dtick=1,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.05,
            xanchor="left", x=0,
        ),
    )
    _annotate_partial_year(fig, years=df_by_year["Year"].unique())
    return _apply_common(fig)


def make_thematic_totals_bar(
    df_totals: pd.DataFrame,
    category_col: str,
    colour_map: dict,
    title: str,
    height: int = CHART_HEIGHT,
) -> go.Figure:
    """Horizontal bar chart of total counts for a layer."""
    df_sorted = df_totals.sort_values("count", ascending=True)
    colours = [colour_map.get(cat, "#999") for cat in df_sorted[category_col]]
    fig = go.Figure(go.Bar(
        y=df_sorted[category_col],
        x=df_sorted["count"],
        orientation="h",
        marker_color=colours,
        marker_line_width=0,
        hovertemplate="<b>%{y}</b><br>%{x} projects<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Projects",
        yaxis_title="",
        margin=dict(l=220),
    )
    return _apply_common(fig, height=height)


def make_cross_heatmap(
    df_cross: pd.DataFrame,
    row_col: str,
    title: str,
    colorscale: list | str = "Tealgrn",
) -> go.Figure:
    """Annotated heatmap from a cross-tabulation pivot table."""
    row_labels = df_cross[row_col].tolist()
    value_cols = [c for c in df_cross.columns if c != row_col]
    z = df_cross[value_cols].values

    annotations = []
    for i, row in enumerate(z):
        for j, val in enumerate(row):
            annotations.append(dict(
                x=value_cols[j], y=row_labels[i],
                text=str(int(val)),
                showarrow=False,
                font=dict(
                    size=11,
                    color="white" if val > z.max() * 0.55 else "#2c3e50",
                ),
            ))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=value_cols,
        y=row_labels,
        colorscale=colorscale,
        showscale=True,
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>%{z} projects<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        annotations=annotations,
        xaxis=dict(side="bottom", tickangle=-35, automargin=True),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=220, b=165),
    )
    return _apply_common(fig, height=380)


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
.navbar-badge {
    display: inline-flex;
    align-items: center;
    margin-left: 0.6rem;
    padding: 0.16rem 0.5rem;
    border-radius: 999px;
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.26);
    color: #ecf0f1;
    font-size: 0.67rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.nav-feedback-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-right: 0.75rem;
    padding: 0.32rem 0.82rem;
    border-radius: 6px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.22);
    color: #ecf0f1;
    font-size: 0.8rem;
    font-weight: 500;
    text-decoration: none;
    transition: background 0.2s ease;
}
.nav-feedback-link:hover {
    background: rgba(255,255,255,0.18);
    color: #ffffff;
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
    white-space: nowrap;
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

/* Hero search */
.hero-search {
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    text-align: center;
}
.hero-search h4 {
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 0.3rem;
}
.hero-search .hero-subtitle {
    font-size: 0.92rem;
    color: #7f8c8d;
    margin-bottom: 1.25rem;
}
.hero-search .hero-helper {
    font-size: 0.8rem;
    color: #95a5a6;
    margin-top: 0.75rem;
}

/* Overview lead */
.overview-lead {
    background: linear-gradient(135deg, #f7fbff 0%, #eef5fb 100%);
    border: 1px solid #d9e6f2;
    border-radius: 10px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
}
.overview-lead h4 {
    font-weight: 700;
    color: #1f3c5a;
    margin-bottom: 0.75rem;
}
.overview-lead p {
    font-size: 1rem;
    color: #5f7387;
    margin-bottom: 0.9rem;
    line-height: 1.8;
    max-width: 1100px;
}
.overview-lead p:last-child {
    margin-bottom: 0;
}
.prototype-note {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-top: 1rem;
    padding: 0.9rem 1rem;
    border: 1px solid #d9e3f0;
    border-radius: 10px;
    background: rgba(255,255,255,0.72);
}
.prototype-note p {
    margin: 0;
    color: #2c3e50;
    font-size: 0.9rem;
    line-height: 1.5;
}
.feedback-link {
    white-space: nowrap;
}

.analysis-shell {
    margin-top: 0.75rem;
}

.analysis-panel {
    background: #f7fafc;
    border: 1px solid #dde7f0;
    border-radius: 12px;
    padding: 1.25rem 1.35rem 1rem;
    margin-bottom: 1rem;
}

.analysis-tabs-label {
    font-size: 0.8rem;
    font-weight: 700;
    color: #607387;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.6rem;
}

.analysis-tabs {
    border-bottom: none;
    margin-bottom: 1.25rem;
}
.analysis-tabs .nav {
    gap: 0.5rem;
}
.analysis-tabs .nav-link {
    font-weight: 600;
    font-size: 0.9rem;
    color: #4f6274;
    background: #e8eef5;
    border: 1px solid transparent;
    border-radius: 999px;
    padding: 0.5rem 0.95rem;
    line-height: 1.2;
}
.analysis-tabs .nav-link:hover {
    color: #30475c;
    background: #dfe7f0;
}
.analysis-tabs .nav-link.active {
    color: #17324d !important;
    background: #d5e6f8 !important;
    border: 1px solid #b7d0ea !important;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
}

.about-content h3 {
    margin-top: 2rem;
    margin-bottom: 1rem;
}
.about-content h4 {
    margin-top: 1.75rem;
    margin-bottom: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #e3ebf3;
}
.about-content hr {
    margin: 2rem 0 1.5rem;
}

.page-title {
    margin-top: 0.5rem;
    margin-bottom: 0.35rem;
    font-size: 1.55rem;
    font-weight: 700;
    color: #2c3e50;
}

/* Mode cards */
.mode-card {
    border: 1px solid #ecf0f1;
    border-radius: 10px;
    padding: 1.5rem 1.75rem;
    background: white;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s, transform 0.2s;
    height: 100%;
}
.mode-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    transform: translateY(-2px);
}
.mode-card h5 {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 0.5rem;
}
.mode-card p {
    font-size: 0.88rem;
    color: #7f8c8d;
    margin-bottom: 1rem;
}

/* Navbar search button */
.nav-search-btn {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #ecf0f1 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.3rem 0.9rem !important;
    border-radius: 6px !important;
    transition: background 0.2s !important;
}
.nav-search-btn:hover {
    background: rgba(255,255,255,0.22) !important;
}

/* Project Explorer result bar */
.explorer-result-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 0;
    margin-bottom: 0.5rem;
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
server = app.server
FEEDBACK_EMAIL_URL = (
    "mailto:balintstewart@gmail.com"
    "?subject=Feedback%20on%20DEA%20Dashboard"
    "&body=Hello%20Balint%2C%0A%0AI%20have%20some%20feedback%20on%20the%20DEA%20dashboard%3A"
    "%0A%0AIssue%20%2F%20suggestion%3A"
    "%0APage%20%2F%20tab%3A"
    "%0AOptional%20screenshot%20or%20example%3A"
)
SOURCE_URL = "https://github.com/balintstewart77/ADR_DEA_project"

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
            html.Span("Beta", className="navbar-badge"),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div([
            html.A(
                "Provide feedback",
                href=FEEDBACK_EMAIL_URL,
                target="_blank",
                rel="noopener noreferrer",
                className="nav-feedback-link",
            ),
            html.A(
                "View source / report issue",
                href=SOURCE_URL,
                target="_blank",
                rel="noopener noreferrer",
                className="nav-feedback-link",
            ),
            html.Button(
                "\U0001F50D Search Projects",
                id="nav-search-btn",
                className="nav-search-btn btn btn-sm me-3",
            ),
            html.Span(
                f"Data to {DATA_DATE}  \u2022  {source_file}",
                className="nav-meta",
            ),
        ], className="d-flex align-items-center ms-auto"),
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
        className="col-auto",
    )


STAT_CARDS = dbc.Row([
    _stat_card(f"{TOTAL_PROJECTS:,}", "Total DEA Projects", "#3366cc"),
    _stat_card(f"{TOTAL_DATASET_REQUESTS:,}", "DEA Dataset Requests", "#6633cc"),
    _stat_card(f"{TOTAL_FLAGSHIP:,}", "Projects Using Cross-Domain Linked Datasets", "#109618"),
    _stat_card(f"{TOTAL_FLAGSHIP_REQUESTS:,}", "Cross-Domain Linked Dataset Requests", "#ff9900"),
    _stat_card(YEAR_RANGE, "Year Range", "#0099c6"),
], className="mb-4 g-3")

# -- Tab content ------------------------------------------------------------

OVERVIEW_TAB = dbc.Tab(label="Overview", tab_id="tab-overview", children=[
    html.Div([
        html.H4("Explore Digital Economy Act 2017 (DEA)-accredited research projects through a searchable public register and portfolio-level analysis."),
        html.P(
            "The DEA research powers allow accredited researchers to access de-identified data held by public authorities for public-good research "
            "in accredited secure environments. Built from the public register of DEA-accredited projects, this dashboard is primarily a public-facing "
            "tool to make those projects easier to see, search, and understand. It is intended to improve legibility around how public data is being "
            "used for accredited research, while also providing a clearer view of patterns "
            "in dataset use, institutional participation, and demand over time."
        ),
        html.Div([
            html.P("This dashboard is a public prototype. Feedback, corrections, and suggestions are welcome."),
            html.Div([
                html.A(
                    "Provide feedback",
                    href=FEEDBACK_EMAIL_URL,
                    target="_blank",
                    rel="noopener noreferrer",
                    className="btn btn-outline-secondary btn-sm feedback-link",
                ),
                html.A(
                    "View source / report issue",
                    href=SOURCE_URL,
                    target="_blank",
                    rel="noopener noreferrer",
                    className="btn btn-outline-secondary btn-sm feedback-link",
                ),
            ], style={"display": "flex", "gap": "0.6rem", "flexWrap": "wrap"}),
        ], className="prototype-note"),
    ], className="overview-lead"),

    # Mode selection cards
    dbc.Row([
        dbc.Col(
            html.Div([
                html.H5("\U0001F50D Project Explorer"),
                html.P(
                    "Search by title, researcher, dataset, provider, institution, or collection."
                ),
                html.Button(
                    "Open Project Explorer",
                    id="mode-explorer-btn",
                    className="btn btn-outline-primary btn-sm",
                ),
            ], className="mode-card"),
            md=6,
        ),
        dbc.Col(
            html.Div([
                html.H5("\U0001F4CA Portfolio Analysis"),
                html.P(
                    "Explore trends in project growth, dataset demand, linked dataset uptake, institutions, and themes."
                ),
                html.Button(
                    "View analysis",
                    id="mode-analysis-btn",
                    className="btn btn-outline-primary btn-sm",
                ),
            ], className="mode-card"),
            md=6,
        ),
    ], className="mb-4 g-3"),

    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="overview-teaser-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
])

OVERALL_TRENDS_TAB = dbc.Tab(label="Overall Trends", tab_id="tab-overall-trends", children=[
    html.P(
        "Track portfolio growth over time using yearly and quarterly views, alongside the spread of accredited researchers per project.",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="overall-yearly-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="overall-quarterly-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=6,
        ),
        dbc.Col(
            html.Div(dcc.Graph(id="overall-srs-chart", config=CHART_CONFIG), className="chart-wrapper"),
            md=6,
        ),
    ]),
])


_dataset_project_counts = (
    df_datasets.drop_duplicates(subset=["Project ID", "dataset"])
    .groupby("dataset")["Project ID"].nunique()
)
_flagship_collection_project_counts = (
    df_flagship_projects.drop_duplicates(subset=["Project Row ID", "collection"])
    .groupby("collection")["Project Row ID"].nunique()
    if len(df_flagship_projects)
    else pd.Series(dtype=int)
)
_ALL_DATASET_OPTIONS = (
    [{"label": "All datasets", "value": "ALL"}]
    + [
        {"label": f"{d}  ({n} {'project' if n == 1 else 'projects'})", "value": d}
        for d in sorted(df_datasets["dataset"].unique()) if d
        for n in [_dataset_project_counts.get(d, 0)]
    ]
    + [
        {
            "label": f"Cross-Domain Linked: {c}  ({n} {'project' if n == 1 else 'projects'})",
            "value": f"collection::{c}",
        }
        for c in COLLECTIONS
        for n in [_flagship_collection_project_counts.get(c, 0)]
    ]
)
_provider_project_counts = (
    df_datasets.drop_duplicates(subset=["Project ID", "provider"])
    .groupby("provider")["Project ID"].nunique()
)
_ALL_PROVIDER_OPTIONS = (
    [{"label": "All source organisations", "value": "ALL"}]
    + [
        {"label": f"{p}  ({n} {'project' if n == 1 else 'projects'})", "value": p}
        for p in sorted(df_datasets["provider"].unique()) if p
        for n in [_provider_project_counts.get(p, 0)]
    ]
)
_institution_project_counts = (
    df_institutions.drop_duplicates(subset=["Project ID", "institution"])
    .groupby("institution")["Project ID"].nunique()
)
_ALL_INSTITUTION_OPTIONS = (
    [{"label": "All institutions", "value": "ALL"}]
    + [
        {"label": f"{i}  ({n} {'project' if n == 1 else 'projects'})", "value": i}
        for i in sorted(df_institutions["institution"].unique()) if i
        for n in [_institution_project_counts.get(i, 0)]
    ]
)

BROWSE_TAB = dbc.Tab(label="\U0001F50D Project Explorer", tab_id="tab-browse", children=[
    html.H5(
        "Project Explorer",
        className="page-title",
    ),
    html.P(
        "Search and filter the full DEA-accredited project register.",
        className="section-desc",
    ),
    # Search row — prominent
    dbc.Row([
        dbc.Col([
            html.Label("Search", className="filter-label"),
            dbc.Input(
                id="browse-search",
                placeholder="Search by title or researcher\u2026",
                type="text",
            ),
        ],
            md=6,
        ),
        dbc.Col([
            html.Label("Dataset", className="filter-label"),
            dcc.Dropdown(
                id="browse-dataset-filter",
                options=_ALL_DATASET_OPTIONS,
                value="ALL",
                clearable=False,
                searchable=True,
                placeholder="All datasets",
            ),
        ], md=3),
        dbc.Col([
            html.Label("Source organisation", className="filter-label"),
            dcc.Dropdown(
                id="browse-provider-filter",
                options=_ALL_PROVIDER_OPTIONS,
                value="ALL",
                clearable=False,
                searchable=True,
                placeholder="All source organisations",
            ),
        ], md=3),
    ], className="mb-2 g-2"),
    # Secondary filters
    dbc.Row([
        dbc.Col([
            html.Label("Research Institution", className="filter-label"),
            dcc.Dropdown(
                id="browse-institution-filter",
                options=_ALL_INSTITUTION_OPTIONS,
                value="ALL",
                clearable=False,
                searchable=True,
                placeholder="All institutions",
            ),
        ], md=4),
        dbc.Col([
            html.Label("Per page", className="filter-label"),
            dcc.Dropdown(
                id="browse-page-size",
                options=[{"label": str(n), "value": n} for n in [10, 20, 50, 100]],
                value=20,
                clearable=False,
                searchable=False,
            ),
        ], md=2),
        dbc.Col([
            html.Div(id="browse-count", className="text-muted small",
                     style={"paddingTop": "1.8rem"}),
        ], md=6),
    ], className="mb-3 g-2"),
    html.Div(
        dash_table.DataTable(
            id="browse-table",
            columns=[
                {"name": "Project ID", "id": "Project ID"},
                {"name": "Title", "id": "Title"},
                {"name": "Researchers", "id": "Researchers"},
                {"name": "Datasets Used", "id": "Datasets Used"},
                {"name": "Accreditation Date", "id": "Accreditation Date"},
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

DATASETS_TAB = dbc.Tab(label="Dataset Demand", tab_id="tab-datasets", children=[
    html.P(
        "Explore which datasets are used most, how demand changes over time, and which source organisations are most represented.",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col([
            html.Label("Show top N datasets", className="filter-label"),
            html.Div([
                dcc.Dropdown(
                    id="datasets-topn-preset",
                    options=[
                        {"label": "5", "value": 5},
                        {"label": "10", "value": 10},
                        {"label": "25", "value": 25},
                        {"label": "50", "value": 50},
                        {"label": "Custom", "value": -1},
                    ],
                    value=10,
                    clearable=False,
                    searchable=False,
                    style={"width": "110px", "display": "inline-block", "verticalAlign": "middle"},
                ),
                dbc.Input(
                    id="datasets-topn-custom", type="number",
                    min=1, max=500, step=1, placeholder="N",
                    style={"width": "80px", "display": "none", "verticalAlign": "middle", "marginLeft": "8px"},
                ),
            ], style={"display": "flex", "alignItems": "center"}),
        ], md=3),
        dbc.Col([
            html.Label("Source organisation", className="filter-label"),
            dcc.Dropdown(
                id="datasets-provider-filter",
                options=_ALL_PROVIDER_OPTIONS,
                value="ALL",
                clearable=False,
            ),
        ], md=4),
        dbc.Col([
            html.Label("Exclude cross-domain linked datasets", className="filter-label"),
            dcc.Checklist(
                id="datasets-exclude-flagship",
                options=[{"label": " Exclude cross-domain linked", "value": "yes"}],
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
    html.Hr(className="my-4"),
    dbc.Accordion([
        dbc.AccordionItem(
            title="Cross-Domain Linked Dataset Breakdown",
            children=[
                html.P(
                    "Track use of cross-domain linked datasets using either distinct projects or total dataset requests.",
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
                    dbc.Col([
                        html.Label("Metric", className="filter-label"),
                        dcc.Dropdown(
                            id="flagship-metric-mode",
                            options=[
                                {"label": "Distinct projects", "value": "projects"},
                                {"label": "Dataset access requests", "value": "requests"},
                            ],
                            value="projects",
                            clearable=False,
                        ),
                    ], md=3),
                ], className="mb-2 g-2"),
                html.P(
                    "Distinct projects count each retained project once per collection. "
                    "Dataset access requests count every matched dataset request, so one project can contribute multiple requests within the same collection.",
                    className="section-desc",
                ),
                dbc.Row([
                    dbc.Col(
                        html.Div(dcc.Graph(id="flagship-pooled-yearly", config=CHART_CONFIG), className="chart-wrapper"),
                        width=12,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div(dcc.Graph(id="flagship-pooled-quarterly", config=CHART_CONFIG), className="chart-wrapper"),
                        width=12,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div(dcc.Graph(id="flagship-line-yearly-chart", config=CHART_CONFIG), className="chart-wrapper"),
                        width=12,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div(dcc.Graph(id="flagship-line-quarterly-chart", config=CHART_CONFIG), className="chart-wrapper"),
                        width=12,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div(dcc.Graph(id="flagship-totals-chart", config=CHART_CONFIG), className="chart-wrapper"),
                        width=12,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        html.Div(dcc.Graph(id="flagship-cumulative-chart", config=CHART_CONFIG), className="chart-wrapper"),
                        width=12,
                    ),
                ]),
            ],
        ),
    ], start_collapsed=True, className="mt-3"),
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

### What Data Access Does the DEA Enable?

The **Digital Economy Act 2017** research powers provide a legal gateway that
allows public authorities to share de-identified data with accredited
researchers for public-good research. Access is only permitted for accredited
researchers, accredited projects, and within accredited secure processing
environments. The framework can cover de-identified data held by public
authorities in connection with their functions, although data held for the
provision of health services or adult social care is excluded from this DEA
gateway. Some projects shown in the public register may also involve data
accessed under other legal gateways, including unpublished ONS data made
available under the Statistics and Registration Service Act, so the register is
not limited to administrative data alone.

---

### Data Processing

The raw data undergoes several cleaning steps before being displayed.
Row counts at each stage:

| Step | Rows | Dropped |
|------|-----:|--------:|
| Loaded from CSV | {PROCESSING_STATS['raw_loaded']:,} | - |
| Rows with missing accreditation date removed | {PROCESSING_STATS['raw_loaded'] - PROCESSING_STATS['dropped_no_date']:,} | {PROCESSING_STATS['dropped_no_date']:,} |
| Filtered to DEA projects only (non-DEA/SRSA rows removed) | {PROCESSING_STATS['after_filters'] + PROCESSING_STATS['dropped_exact_duplicates'] + PROCESSING_STATS['dropped_special_duplicate_rows'] + PROCESSING_STATS['dropped_same_id_same_title']:,} | {PROCESSING_STATS['dropped_non_dea']:,} |
| Exact duplicate rows removed | {PROCESSING_STATS['after_filters'] + PROCESSING_STATS['dropped_special_duplicate_rows'] + PROCESSING_STATS['dropped_same_id_same_title']:,} | {PROCESSING_STATS['dropped_exact_duplicates']:,} |
| Same Project ID + Title duplicates removed | {PROCESSING_STATS['after_filters'] + PROCESSING_STATS['dropped_special_duplicate_rows']:,} | {PROCESSING_STATS['dropped_same_id_same_title']:,} |
| Manual duplicate cleanup for 2023/113 | {PROCESSING_STATS['after_filters']:,} | {PROCESSING_STATS['dropped_special_duplicate_rows']:,} |
| **Final dataset** | **{PROCESSING_STATS['final_rows']:,}** | |

Additional processing: column names are standardised, accreditation dates are
parsed, and year/quarter fields are derived for time-series analysis.

Duplicate policy:

- Exact duplicate rows are removed.
- Duplicate rows sharing the same **Project ID** and **Title** are collapsed to one row.
- Duplicate **Project ID** values with different titles are retained as separate projects for manual review.
- Project `2023/113` is collapsed because both rows share the same project title.

Retained conflicting duplicate IDs:
`{RETAINED_CONFLICTING_DUPLICATE_IDS_TEXT}`

---

### Cross-Domain Linked Dataset Classification

Seven cross-domain linked data collections are identified by **case-insensitive
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

---

#### Counting methodology

The Cross-Domain Linked Dataset Breakdown section supports two views:

- **Distinct projects** - each retained project counts once per collection.
- **Dataset access requests** - every matched dataset request counts, so one
  project can contribute multiple requests to the same collection.

If a single project accesses three Data First datasets (e.g. Crown Court,
Magistrates Court, and Prisoner), that contributes **one** Data First project
in the first view and **three** Data First access requests in the second.

---

### Individual Dataset Parsing (Dataset Demand Tab)

The "Datasets Used" free-text field is parsed into individual dataset entries:

1. **Split by newline** - each line typically represents one source organisation
2. **Split by colon** - separates the source organisation from the dataset list
3. **Split by comma and ampersand** - separates individual datasets within a source organisation
4. **Geographic suffixes stripped** - e.g. "- UK", "- England and Wales" are removed for grouping
5. **Name aliases applied** - variant names are mapped to canonical labels
   (e.g. "LEO via SRS Iteration 1 Standard Extract" -> "Longitudinal Education Outcomes")

---

### Definitions

- **DEA (Digital Economy Act 2017)** - UK legislation that provides a legal
  framework for accredited researchers to access de-identified government
  administrative data for research purposes.

- **Trusted Research Environment (TRE)** - Accredited secure computing
  environments where researchers can access protected data without it leaving
  the secure setting. Examples include the ONS Secure Research Service (SRS)
  and the SAIL Databank.

- **Cross-Domain Linked Datasets** - Seven linked administrative data
  collections spanning justice, education, health, employment, and agriculture,
  identified by keyword matching against project dataset descriptions.

---

### Limitations and Caveats

- **Keyword matching** may miss dataset names not yet included in the keyword
  lists, or match false positives where keywords appear incidentally.
- **Dataset parsing** splits on commas and ampersands, which can incorrectly
  break source organisation names that contain these characters
  (e.g. "Department for Business, Energy & Industrial Strategy").
- **Duplicate handling** removes exact duplicates and same-ID/same-title
  duplicates, but retains duplicate IDs where the titles differ.
- **Dataset parsing** includes a cleanup pass for malformed provider breaks and
  drops obvious parser artefacts, but free-text source formatting can still
  produce imperfect splits.
- **Small TRE provider categories** (under 3% of total projects) are grouped
  as "Other" in the pie chart for readability.
- **Project titles** alone may not fully describe the scope of a research project.

---

### LLM Thematic Analysis Methodology

**Note:** The Thematic Analysis tab is **experimental**. Classifications are
LLM-generated and have not yet been systematically validated against expert
review.

A separate analysis script (`llm_theme_analysis_v3.py`) classifies project
titles using a three-layer framework:

- **Layer A - Substantive Domain** (1 or more from 14 themes, e.g. "Education &
  Skills", "Health & Social Care", "Crime & Justice")
- **Layer B - Linkage Mode** (exactly 1: Single-Dataset, Within-Domain,
  or Cross-Domain Linkage)
- **Layer C - Analytical Purpose** (1 or 2, e.g. "Policy Evaluation",
  "Descriptive Monitoring", "Life-Course Analysis")

Classification is performed by Claude (claude-opus-4-6) using structured output
via the Anthropic API. Results are cached locally to avoid re-classification.
A narrative summary is auto-generated from the aggregate statistics.

**Note:** Classification is based on both project titles and datasets used.
These fields may not fully convey the research methodology or the full scope of data linkage.
"""

INSTITUTIONS_TAB = dbc.Tab(label="Institutions", tab_id="tab-institutions", children=[
    html.P(
        "See which research organisations are most represented through researcher affiliations, and how that changes over time.",
        className="section-desc",
    ),
    dbc.Row([
        dbc.Col([
            html.Label("Show top N institutions", className="filter-label"),
            html.Div([
                dcc.Dropdown(
                    id="institutions-topn-preset",
                    options=[
                        {"label": "5", "value": 5},
                        {"label": "10", "value": 10},
                        {"label": "25", "value": 25},
                        {"label": "50", "value": 50},
                        {"label": "Custom", "value": -1},
                    ],
                    value=10,
                    clearable=False,
                    searchable=False,
                    style={"width": "110px", "display": "inline-block", "verticalAlign": "middle"},
                ),
                dbc.Input(
                    id="institutions-topn-custom", type="number",
                    min=1, max=500, step=1, placeholder="N",
                    style={"width": "80px", "display": "none", "verticalAlign": "middle", "marginLeft": "8px"},
                ),
            ], style={"display": "flex", "alignItems": "center"}),
        ], md=3),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="institutions-bar-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
    dbc.Row([
        dbc.Col(
            html.Div(dcc.Graph(id="institutions-trend-chart", config=CHART_CONFIG), className="chart-wrapper"),
            width=12,
        ),
    ]),
])

# -- Thematic Analysis tab --------------------------------------------------

_thematic_methodology_md = """
**Model:** Claude Opus 4.6 (`claude-opus-4-6`) via the Anthropic API with structured
JSON output and `temperature=0` for deterministic classification.

**Input:** Each project's title and its listed datasets are provided to the model
together. Both fields inform all three classification layers — titles provide the
research question while datasets reveal the data domains and linkage scope.

**Batch processing:** Projects are classified in batches of 10-20, with automatic
retry logic for transient API failures. Results are cached locally so that
re-runs only classify new or changed projects.

**Validation:** A controlled experiment compared Opus 4.6 and Sonnet 4.6 on a
150-project stratified sample. Opus was selected as the preferred model after
manual review of disagreements.
"""

_thematic_layers_md = """
#### Layer A — Substantive Domain (1 or more per project)

Projects are assigned to one or more of 14 thematic domains based on the
research question and datasets used:

| Domain | Description |
|--------|-------------|
| Labour Market & Employment | Wages, jobs, skills demand, unemployment, gig economy |
| Business & Productivity | Firm performance, innovation, trade, enterprise zones |
| Education & Skills | Schools, universities, qualifications, pupil outcomes |
| Health & Social Care | NHS, mortality, mental health, social care interactions |
| Poverty, Inequality & Living Standards | Income distribution, deprivation, benefits, cost of living |
| Gender, Race & Ethnicity | Disparities by sex, ethnicity, or gender identity |
| Migration & Demographics | Population flows, fertility, ageing, migrant outcomes |
| Crime & Justice | Offending, victimisation, courts, policing |
| COVID-19 & Pandemic | Pandemic-specific research and data |
| Housing & Planning | Housing markets, homelessness, planning, energy in homes |
| Environment & Agriculture | Land use, farming, pollution, climate, food |
| Public Finance & Taxation | Tax policy, revenue, government expenditure |
| Data Infrastructure & Methodology | Linkage methods, data quality, statistical methodology |
| Unclear from Title | Insufficient information to classify |

&nbsp;

#### Layer B — Linkage Mode (exactly 1 per project)

Each project is assigned to one linkage mode based on the number of policy
domains its datasets span:

| Mode | Description |
|------|-------------|
| Single-Dataset | Uses only one dataset |
| Within-Domain Linkage | Links multiple datasets from the same policy domain |
| Cross-Domain Linkage | Links datasets across two or more distinct policy domains |

&nbsp;

#### Layer C — Analytical Purpose (1 or 2 per project)

Projects are classified by their primary research purpose:

| Purpose | Description |
|---------|-------------|
| Descriptive Monitoring | Measuring prevalence, trends, or patterns |
| Policy Evaluation / Impact Analysis | Evaluating a specific policy, programme, or intervention |
| Outcome Tracking | Linking an exposure or condition to a downstream outcome |
| Inequality / Disparities Analysis | Comparing outcomes across social groups |
| Life-Course / Trajectory Analysis | Tracking individuals over extended time periods |
| Methodological / Infrastructure Research | Developing or validating data linkage methods |
| Risk Prediction / Early Identification | Building risk scores or identifying at-risk subgroups |
| Service Interaction / Systems Analysis | How individuals move through public services |
"""

if THEMATIC_DATA_AVAILABLE:
    _thematic_children = [
        # Section 1: Caveat banner
        dbc.Alert([
            html.Strong("Experimental Analysis"),
            " — Classifications below were generated by a large language model (Claude Opus). "
            "They are based on project titles and dataset names only, and should be treated as "
            "indicative rather than definitive. Ambiguous or terse titles may be misclassified.",
        ], color="warning", className="mb-3 mt-2"),

        # Summary stats
        dbc.Row([
            _stat_card(f"{THEMATIC_PROJECT_COUNT:,}", "Projects Classified", "#2a9d8f"),
            _stat_card("14", "Substantive Domains", "#264653"),
            _stat_card("5", "Linkage Modes", "#457b9d"),
            _stat_card("9", "Analytical Purposes", "#e76f51"),
        ], className="mb-3 g-3"),

        html.P(
            "Each project is independently classified across three layers: "
            "the substantive research domain(s), the data linkage complexity, "
            "and the analytical purpose. Projects may belong to multiple domains "
            "and may have up to two analytical purposes.",
            className="section-desc",
        ),

        # Section 2: Collapsible methods
        dbc.Accordion([
            dbc.AccordionItem(
                dcc.Markdown(_thematic_methodology_md, style={"fontSize": "0.85rem", "lineHeight": "1.6"}),
                title="Classification Methodology",
            ),
            dbc.AccordionItem(
                dcc.Markdown(_thematic_layers_md, style={"fontSize": "0.85rem", "lineHeight": "1.6"}),
                title="Layer Definitions",
            ),
            dbc.AccordionItem(
                dcc.Markdown(THEMATIC_NARRATIVE, style={"fontSize": "0.85rem", "lineHeight": "1.6"}),
                title="Analytical Narrative (LLM-Generated)",
            ),
        ], start_collapsed=True, className="mb-4"),

        # Section 3: Metric toggle
        dbc.Row([
            dbc.Col([
                html.Label("Metric", className="filter-label"),
                dcc.Dropdown(
                    id="thematic-metric-toggle",
                    options=[
                        {"label": "% of projects in year", "value": "pct"},
                        {"label": "Absolute project count", "value": "count"},
                    ],
                    value="pct",
                    clearable=False,
                ),
            ], md=3),
        ], className="mb-3 g-2"),

        # Section 3: Domain trends
        html.H5(
            "Substantive Domains Over Time",
            className="mt-3 mb-2",
            style={"color": "#2c3e50", "fontWeight": "600"},
        ),
        html.P(
            "Projects may belong to multiple domains, so percentages sum to more than 100% per year. "
            "Click a legend entry to show/hide individual domains.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-domain-trend", config=CHART_CONFIG),
                className="chart-wrapper",
            ), width=12),
        ]),

        # Section 4: Linkage mode trends
        html.H5(
            "Data Linkage Complexity Over Time",
            className="mt-4 mb-2",
            style={"color": "#2c3e50", "fontWeight": "600"},
        ),
        html.P(
            "Each project has exactly one linkage mode, so these shares are compositional.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-linkage-trend", config=CHART_CONFIG),
                className="chart-wrapper",
            ), width=12),
        ]),

        # Section 5: Purpose trends
        html.H5(
            "Analytical Purpose Over Time",
            className="mt-4 mb-2",
            style={"color": "#2c3e50", "fontWeight": "600"},
        ),
        html.P(
            "Projects may have up to two purposes, so percentages can sum to slightly more than 100%.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-purpose-trend", config=CHART_CONFIG),
                className="chart-wrapper",
            ), width=12),
        ]),

        # Section 6: Totals
        html.H5(
            "Overall Distribution",
            className="mt-4 mb-2",
            style={"color": "#2c3e50", "fontWeight": "600"},
        ),
        dbc.Row([
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-domain-totals", config=CHART_CONFIG),
                className="chart-wrapper",
            ), md=5),
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-linkage-totals", config=CHART_CONFIG),
                className="chart-wrapper",
            ), md=3),
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-purpose-totals", config=CHART_CONFIG),
                className="chart-wrapper",
            ), md=4),
        ], className="g-3"),

        # Section 7: Cross-layer heatmaps
        html.H5(
            "Cross-Layer Patterns",
            className="mt-4 mb-2",
            style={"color": "#2c3e50", "fontWeight": "600"},
        ),
        html.P(
            "Cross-tabulations use the primary (first-listed) domain for each project. "
            "Only the six most common primary domains are shown.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-cross-mode-domain", config=CHART_CONFIG),
                className="chart-wrapper",
            ), md=6),
            dbc.Col(html.Div(
                dcc.Graph(id="thematic-cross-domain-purpose", config=CHART_CONFIG),
                className="chart-wrapper",
            ), md=6),
        ], className="g-3 mb-4"),

        # Section 8: Browse classified projects
        html.H5(
            "Browse Classified Projects",
            className="mt-4 mb-2",
            style={"color": "#2c3e50", "fontWeight": "600"},
        ),
        html.P(
            "Filter by domain, linkage mode, or analytical purpose to explore individual project classifications.",
            className="section-desc",
        ),
        dbc.Row([
            dbc.Col([
                html.Label("Domain", className="filter-label"),
                dcc.Dropdown(
                    id="thematic-domain-filter",
                    options=_THEMATIC_DOMAIN_OPTIONS,
                    value="ALL",
                    clearable=False,
                    searchable=True,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Linkage mode", className="filter-label"),
                dcc.Dropdown(
                    id="thematic-linkage-filter",
                    options=_THEMATIC_LINKAGE_OPTIONS,
                    value="ALL",
                    clearable=False,
                    searchable=False,
                ),
            ], md=2),
            dbc.Col([
                html.Label("Analytical purpose", className="filter-label"),
                dcc.Dropdown(
                    id="thematic-purpose-filter",
                    options=_THEMATIC_PURPOSE_OPTIONS,
                    value="ALL",
                    clearable=False,
                    searchable=True,
                ),
            ], md=3),
            dbc.Col([
                html.Label("Search title", className="filter-label"),
                dbc.Input(id="thematic-search", placeholder="Type to filter\u2026", type="text"),
            ], md=2),
            dbc.Col([
                html.Label("\u00a0", className="filter-label"),
                html.Div(id="thematic-browse-count", className="text-muted small pt-2"),
            ], md=2),
        ], className="mb-3 g-2"),
        html.Div(
            dash_table.DataTable(
                id="thematic-browse-table",
                columns=[
                    {"name": "Project ID", "id": "Project ID"},
                    {"name": "Title", "id": "Title"},
                    {"name": "Datasets Used", "id": "Datasets Used"},
                    {"name": "Domains", "id": "substantive_domains"},
                    {"name": "Linkage Mode", "id": "linkage_mode"},
                    {"name": "Purpose", "id": "analytical_purpose"},
                    {"name": "Accreditation Date", "id": "Accreditation Date"},
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
            ),
            className="dea-table mb-4",
        ),
    ]
else:
    _thematic_children = [
        dbc.Alert(
            "Thematic analysis data not available. Run analysis/llm_theme_analysis_v3.py to generate.",
            color="info", className="mt-3",
        ),
    ]

THEMATIC_TAB = dbc.Tab(
    label="Thematic Analysis (Experimental)", tab_id="tab-thematic", children=_thematic_children,
)

PORTFOLIO_ANALYSIS_TAB = dbc.Tab(label="Portfolio Analysis", tab_id="tab-analysis", children=[
    html.Div([
        html.H5(
            "Portfolio Analysis",
            className="page-title",
        ),
        html.P(
            "Explore portfolio-level patterns through trends, dataset demand, cross-domain linked dataset uptake, institutions, and thematic analysis.",
            className="section-desc",
        ),
        html.Div("Choose an analysis view", className="analysis-tabs-label"),
        dbc.Tabs(
            [OVERALL_TRENDS_TAB, DATASETS_TAB, INSTITUTIONS_TAB, THEMATIC_TAB],
            id="analysis-tabs",
            active_tab="tab-overall-trends",
            className="analysis-tabs analysis-shell",
        ),
    ], className="analysis-panel"),
])

ABOUT_TAB = dbc.Tab(label="About", tab_id="tab-about", children=[
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("This dashboard is a public prototype. Feedback, corrections, and suggestions are welcome."),
                html.Div([
                    html.A(
                        "Provide feedback",
                        href=FEEDBACK_EMAIL_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="btn btn-outline-secondary btn-sm feedback-link",
                    ),
                    html.A(
                        "View source / report issue",
                        href=SOURCE_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="btn btn-outline-secondary btn-sm feedback-link",
                    ),
                ], style={"display": "flex", "gap": "0.6rem", "flexWrap": "wrap"}),
            ], className="prototype-note mb-4"),
            dcc.Markdown(
                _about_md,
                className="about-content",
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
            [OVERVIEW_TAB, BROWSE_TAB, PORTFOLIO_ANALYSIS_TAB, ABOUT_TAB],
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
    Output("main-tabs", "active_tab"),
    Output("analysis-tabs", "active_tab"),
    Output("browse-search", "value"),
    Input("nav-search-btn", "n_clicks"),
    Input("mode-explorer-btn", "n_clicks"),
    Input("mode-analysis-btn", "n_clicks"),
    prevent_initial_call=True,
)
def navigate_tabs(nav_click, mode_explore, mode_analysis):
    from dash import ctx
    trigger = ctx.triggered_id
    if trigger == "mode-analysis-btn":
        return "tab-analysis", "tab-overall-trends", ""
    return "tab-browse", "tab-overall-trends", ""


@app.callback(
    Output("overview-teaser-chart", "figure"),
    Output("overall-quarterly-chart", "figure"),
    Output("overall-yearly-chart", "figure"),
    Output("overall-srs-chart", "figure"),
    Input("main-tabs", "active_tab"),
    Input("analysis-tabs", "active_tab"),
)
def update_overview(_tab, _analysis_tab):
    return (
        make_yearly_chart(df_all),
        make_quarterly_chart(df_all),
        make_yearly_chart(df_all),
        make_srs_chart(df_all),
    )


@app.callback(
    Output("flagship-pooled-yearly", "figure"),
    Output("flagship-pooled-quarterly", "figure"),
    Output("flagship-line-yearly-chart", "figure"),
    Output("flagship-line-quarterly-chart", "figure"),
    Output("flagship-totals-chart", "figure"),
    Output("flagship-cumulative-chart", "figure"),
    Input("collection-filter", "value"),
    Input("flagship-metric-mode", "value"),
)
def update_flagship(selected_collections, metric_mode):
    df_flagship = df_flagship_projects if metric_mode == "projects" else df_flagship_requests
    metric_label, title_noun = _metric_labels(metric_mode)

    if not len(df_flagship):
        empty = go.Figure().update_layout(title="No cross-domain linked data available")
        return empty, empty, empty, empty, empty, empty

    sub = df_flagship
    if selected_collections:
        sub = df_flagship[df_flagship["collection"].isin(selected_collections)]

    # Pooled yearly across all filtered collections
    if metric_mode == "projects":
        pooled_yearly = (
            sub.groupby("Year")["Project Row ID"]
            .nunique()
            .reset_index()
            .rename(columns={"Project Row ID": "Value"})
        )
    else:
        pooled_yearly = (
            sub.groupby("Year")
            .size()
            .reset_index()
            .rename(columns={0: "Value"})
        )
    year_colours = [
        SECONDARY_BAR if yr != PARTIAL_YEAR else "#f4a582"
        for yr in pooled_yearly["Year"]
    ]
    fig_pooled_yearly = go.Figure(go.Bar(
        x=pooled_yearly["Year"], y=pooled_yearly["Value"],
        marker_color=year_colours,
        marker_line_width=0,
        hovertemplate=f"<b>%{{x}}</b><br>%{{y}} {title_noun}<extra></extra>",
    ))
    fig_pooled_yearly.update_layout(
        title=f"All Cross-Domain Linked {metric_label} by Year",
        xaxis_title="Year",
        yaxis_title=metric_label,
        bargap=0.25,
        xaxis_dtick=1,
    )
    _annotate_partial_year(fig_pooled_yearly, years=pooled_yearly["Year"])
    _apply_common(fig_pooled_yearly)

    # Pooled quarterly across all filtered collections
    if metric_mode == "projects":
        pooled = (
            sub.groupby("quarter_date")["Project Row ID"]
            .nunique()
            .reset_index()
            .rename(columns={"Project Row ID": "Value"})
        )
    else:
        pooled = (
            sub.groupby("quarter_date")
            .size()
            .reset_index()
            .rename(columns={0: "Value"})
        )
    fig_pooled = px.bar(
        pooled, x="quarter_date", y="Value",
        title=f"All Cross-Domain Linked {metric_label} by Quarter (Pooled)",
        labels={"quarter_date": "Quarter", "Value": metric_label},
        color_discrete_sequence=[PRIMARY_BAR],
    )
    fig_pooled.update_layout(xaxis_tickformat="%b %Y", bargap=0.15)
    fig_pooled.update_traces(
        marker_line_width=0,
        hovertemplate=f"<b>%{{x|%b %Y}}</b><br>%{{y}} {title_noun}<extra></extra>",
    )
    _apply_common(fig_pooled)

    return (
        fig_pooled_yearly,
        fig_pooled,
        make_collection_yearly_line_chart(sub, metric_mode),
        make_collection_line_chart(sub, metric_mode),
        make_collection_totals_chart(sub, metric_mode),
        make_cumulative_chart(df_flagship, selected_collections or [], metric_mode),
    )


@app.callback(
    Output("browse-table", "data"),
    Output("browse-table", "tooltip_data"),
    Output("browse-table", "page_size"),
    Output("browse-count", "children"),
    Input("browse-dataset-filter", "value"),
    Input("browse-provider-filter", "value"),
    Input("browse-institution-filter", "value"),
    Input("browse-search", "value"),
    Input("browse-page-size", "value"),
)
def update_browse_table(dataset_filter, provider_filter, institution_filter, search, page_size):
    base = df_all.copy()

    if dataset_filter and dataset_filter != "ALL":
        if isinstance(dataset_filter, str) and dataset_filter.startswith("collection::"):
            selected_collection = dataset_filter.split("::", 1)[1]
            base = base[base["collections"].apply(lambda x: selected_collection in x)]
        else:
            matching_pids = set(
                df_datasets.loc[df_datasets["dataset"] == dataset_filter, "Project ID"]
            )
            base = base[base["Project ID"].isin(matching_pids)]

    if provider_filter and provider_filter != "ALL":
        matching_pids = set(
            df_datasets.loc[df_datasets["provider"] == provider_filter, "Project ID"]
        )
        base = base[base["Project ID"].isin(matching_pids)]

    if institution_filter and institution_filter != "ALL":
        matching_pids = set(
            df_institutions.loc[df_institutions["institution"] == institution_filter, "Project ID"]
        )
        base = base[base["Project ID"].isin(matching_pids)]

    if search:
        mask = (
            base["Title"].str.contains(search, case=False, na=False)
            | base["Researchers"].str.contains(search, case=False, na=False)
        )
        base = base[mask]

    base["Accreditation Date"] = pd.to_datetime(base["Accreditation Date"]).dt.strftime("%d %b %Y")

    display_cols = ["Project ID", "Title", "Researchers", "Datasets Used", "Accreditation Date"]
    table_data = base[display_cols].to_dict("records")

    tooltip_data = [
        {
            col: {"value": str(row.get(col, "")), "type": "markdown"}
            for col in display_cols
        }
        for row in table_data
    ]

    count_text = f"Showing {len(table_data):,} project{'s' if len(table_data) != 1 else ''}"
    return table_data, tooltip_data, page_size or 20, count_text


# Build a set of flagship dataset names (normalised) for optional exclusion
_FLAGSHIP_KW_LOWER = []
for kws in FLAGSHIP_COLLECTIONS.values():
    _FLAGSHIP_KW_LOWER.extend(kw.lower() for kw in kws)


def _is_flagship_dataset(name: str) -> bool:
    s = name.lower()
    return any(kw in s for kw in _FLAGSHIP_KW_LOWER)


@app.callback(
    Output("datasets-topn-custom", "style"),
    Input("datasets-topn-preset", "value"),
)
def toggle_datasets_custom(preset):
    base = {"width": "80px", "verticalAlign": "middle", "marginLeft": "8px"}
    if preset == -1:
        return {**base, "display": "inline-block"}
    return {**base, "display": "none"}


@app.callback(
    Output("datasets-topn-chart", "figure"),
    Output("datasets-trend-chart", "figure"),
    Output("datasets-provider-chart", "figure"),
    Input("datasets-topn-preset", "value"),
    Input("datasets-topn-custom", "value"),
    Input("datasets-provider-filter", "value"),
    Input("datasets-exclude-flagship", "value"),
)
def update_datasets_tab(preset, custom, provider, exclude_flagship):
    top_n = int(custom) if preset == -1 and custom else (preset if preset != -1 else 10)
    top_n = max(1, int(top_n))
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

    # -- Trend: top N datasets over time --
    trend_n = min(top_n, 15)  # cap legend at 15 for readability
    top_trend = (
        sub.groupby("dataset")["Project ID"]
        .nunique()
        .nlargest(trend_n)
        .index.tolist()
    )
    trend_data = (
        sub[sub["dataset"].isin(top_trend)]
        .groupby(["Year", "dataset"])["Project ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig_trend = px.line(
        trend_data, x="Year", y="Projects", color="dataset",
        title=f"Top {trend_n} Datasets — Usage by Year",
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
    _annotate_partial_year(fig_trend, years=trend_data["Year"].unique())
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
        title="Projects by Source Organisation",
    )
    fig_prov.update_traces(
        textposition="inside",
        texttemplate="%{label}<br>%{percent:.0%}",
        insidetextorientation="horizontal",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>%{value} projects (%{percent:.0%})<extra></extra>",
    )
    fig_prov.update_layout(
        showlegend=False,
        margin=dict(l=8, r=8, t=56, b=8),
    )
    _apply_common(fig_prov)

    return fig_top, fig_trend, fig_prov


@app.callback(
    Output("institutions-topn-custom", "style"),
    Input("institutions-topn-preset", "value"),
)
def toggle_institutions_custom(preset):
    base = {"width": "80px", "verticalAlign": "middle", "marginLeft": "8px"}
    if preset == -1:
        return {**base, "display": "inline-block"}
    return {**base, "display": "none"}


@app.callback(
    Output("institutions-bar-chart", "figure"),
    Output("institutions-trend-chart", "figure"),
    Input("institutions-topn-preset", "value"),
    Input("institutions-topn-custom", "value"),
)
def update_institutions_tab(preset, custom):
    top_n = int(custom) if preset == -1 and custom else (preset if preset != -1 else 10)
    top_n = max(1, int(top_n))
    return (
        make_institution_bar(df_institutions, top_n=top_n),
        make_institution_trend(df_institutions, top_n=8),
    )


# -- Thematic Analysis tab callback ----------------------------------------

if THEMATIC_DATA_AVAILABLE:
    @app.callback(
        Output("thematic-domain-trend", "figure"),
        Output("thematic-linkage-trend", "figure"),
        Output("thematic-purpose-trend", "figure"),
        Output("thematic-domain-totals", "figure"),
        Output("thematic-linkage-totals", "figure"),
        Output("thematic-purpose-totals", "figure"),
        Output("thematic-cross-mode-domain", "figure"),
        Output("thematic-cross-domain-purpose", "figure"),
        Input("thematic-metric-toggle", "value"),
    )
    def update_thematic_tab(metric_mode):
        metric_col = "pct_of_projects" if metric_mode == "pct" else "count"

        domain_trend = make_thematic_trend(
            df_thematic_a, "domain", DOMAIN_COLOURS, metric_col,
            "Substantive Domains Over Time",
        )
        linkage_trend = make_linkage_area(
            df_thematic_b, LINKAGE_COLOURS, metric_col,
        )
        purpose_trend = make_thematic_trend(
            df_thematic_c, "purpose", PURPOSE_COLOURS, metric_col,
            "Analytical Purpose Over Time",
            height=CHART_HEIGHT,
        )

        domain_totals = make_thematic_totals_bar(
            df_thematic_a_totals, "domain", DOMAIN_COLOURS,
            "Projects by Domain", height=440,
        )
        linkage_totals = make_thematic_totals_bar(
            df_thematic_b_totals, "linkage_mode", LINKAGE_COLOURS,
            "Projects by Linkage Mode", height=280,
        )
        purpose_totals = make_thematic_totals_bar(
            df_thematic_c_totals, "purpose", PURPOSE_COLOURS,
            "Projects by Purpose", height=380,
        )

        cross_mode = make_cross_heatmap(
            df_cross_mode_domain, "primary_domain",
            "Primary Domain × Linkage Mode",
            colorscale="Tealgrn",
        )
        cross_purpose = make_cross_heatmap(
            df_cross_domain_purpose, "primary_domain",
            "Primary Domain × Analytical Purpose",
            colorscale=[[0, "#fef0ec"], [0.5, "#f4a582"], [1, "#d73027"]],
        )

        return (
            domain_trend, linkage_trend, purpose_trend,
            domain_totals, linkage_totals, purpose_totals,
            cross_mode, cross_purpose,
        )

    @app.callback(
        Output("thematic-browse-table", "data"),
        Output("thematic-browse-count", "children"),
        Input("thematic-domain-filter", "value"),
        Input("thematic-linkage-filter", "value"),
        Input("thematic-purpose-filter", "value"),
        Input("thematic-search", "value"),
    )
    def update_thematic_browse(domain_filter, linkage_filter, purpose_filter, search):
        base = df_thematic_projects.copy()
        if domain_filter and domain_filter != "ALL":
            base = base[base["substantive_domains"].str.contains(domain_filter, na=False)]
        if linkage_filter and linkage_filter != "ALL":
            base = base[base["linkage_mode"] == linkage_filter]
        if purpose_filter and purpose_filter != "ALL":
            base = base[base["analytical_purpose"].str.contains(purpose_filter, na=False)]
        if search:
            base = base[base["Title"].str.contains(search, case=False, na=False)]

        display_cols = [
            "Project ID", "Title", "Datasets Used", "substantive_domains",
            "linkage_mode", "analytical_purpose", "Accreditation Date",
        ]
        count_text = f"{len(base):,} of {len(df_thematic_projects):,} projects"
        return base[display_cols].to_dict("records"), count_text


# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(
        debug=debug_mode,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8050)),
    )
