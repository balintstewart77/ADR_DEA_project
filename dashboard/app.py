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
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc

# ---------------------------------------------------------------------------
# 1. Data loading & processing
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Prefer the freshest scraped file; fall back to the original
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


# Mapping: collection name -> keywords to match in 'Datasets Used' (case-insensitive)
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
        "probation dataset",
        "family court",
    ],
    "LEO": [
        "longitudinal education outcomes",
        " leo ",
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

# Sub-dataset labels for drill-down
DATASET_LABELS = {
    "data first: crown court dataset": ("Data First", "Crown Court Dataset"),
    "data first: magistrates court dataset": ("Data First", "Magistrates Court Dataset"),
    "data first: cross-justice system linking dataset": ("Data First", "Cross-Justice System Linking Dataset"),
    "data first: prisoner dataset": ("Data First", "Prisoner Dataset"),
    "data first: probation dataset": ("Data First", "Probation Dataset"),
    "data first: family court dataset": ("Data First", "Family Court Dataset"),
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

COLLECTION_COLOURS = {
    "Data First":                       "#1f77b4",
    "LEO":                              "#ff7f0e",
    "ECHILD":                           "#2ca02c",
    "Growing up in England":            "#d62728",
    "Wage and Employment Dynamics":     "#9467bd",
    "GRADE":                            "#8c564b",
    "Agricultural Research Collection": "#e377c2",
}


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


def process_data(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        df_all   – full cleaned dataset (one row per project)
        df_flagship – exploded dataset (one row per project × collection)
    """
    df = df_raw.copy()

    # Standardise column names (handle both old and new xlsx schemas)
    col_map = {
        "Project Number": "Project ID",
        "Project Name": "Title",
        "Accredited Researchers": "Researchers",
        "Legal Gateway": "Legal Basis",
        "Protected Data Accessed": "Datasets Used",
        "Processing Environment": "Secure Research Service",
    }
    df = df.rename(columns=col_map)

    # Parse accreditation date
    df["Accreditation Date"] = pd.to_datetime(df["Accreditation Date"], errors="coerce")
    df = df.dropna(subset=["Accreditation Date"])

    # Filter to DEA only (exclude SRSA-only rows)
    if "Legal Basis" in df.columns:
        df = df[df["Legal Basis"].str.contains("Digital Economy Act", na=False, case=False)]

    df["Year"] = df["Accreditation Date"].dt.year
    df["Quarter"] = df["Accreditation Date"].dt.to_period("Q")
    df["Quarter Label"] = df["Quarter"].dt.strftime("Q%q %Y")
    df["quarter_date"] = df["Quarter"].dt.to_timestamp()

    # Classify collections
    df["collections"] = df["Datasets Used"].apply(classify_collection)
    df["is_flagship"] = df["collections"].apply(lambda x: len(x) > 0)

    # ---- Flagship exploded view ----
    flagship_rows = []
    for _, row in df[df["is_flagship"]].iterrows():
        for coll in row["collections"]:
            flagship_rows.append({**row.to_dict(), "collection": coll})
    df_flagship = pd.DataFrame(flagship_rows)

    return df, df_flagship


# Load data once at startup
df_raw, source_file = load_raw()
df_all, df_flagship = process_data(df_raw)

COLLECTIONS = sorted(df_flagship["collection"].unique()) if len(df_flagship) else list(FLAGSHIP_COLLECTIONS.keys())
DATA_DATE = df_all["Accreditation Date"].max().strftime("%d %B %Y") if len(df_all) else "unknown"
TOTAL_PROJECTS = len(df_all)
TOTAL_FLAGSHIP = df_flagship["Project ID"].nunique() if len(df_flagship) else 0


# ---------------------------------------------------------------------------
# 2. Helper chart builders
# ---------------------------------------------------------------------------

def make_quarterly_chart(df: pd.DataFrame, title: str = "New DEA Projects by Quarter") -> go.Figure:
    counts = (
        df.groupby("quarter_date")["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig = px.bar(
        counts, x="quarter_date", y="Projects",
        title=title,
        labels={"quarter_date": "Quarter", "Projects": "New Projects"},
        color_discrete_sequence=["#4C72B0"],
    )
    fig.update_layout(xaxis_tickformat="%b %Y", bargap=0.1)
    return fig


def make_collection_line_chart(df_flag: pd.DataFrame) -> go.Figure:
    counts = (
        df_flag.groupby(["quarter_date", "collection"])["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "Projects"})
    )
    fig = px.line(
        counts, x="quarter_date", y="Projects", color="collection",
        title="Flagship Dataset Requests by Quarter",
        labels={"quarter_date": "Quarter", "Projects": "New Projects", "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
        markers=True,
    )
    fig.update_layout(xaxis_tickformat="%b %Y", legend_title_text="Collection")
    return fig


def make_collection_totals_chart(df_flag: pd.DataFrame) -> go.Figure:
    totals = (
        df_flag.groupby("collection")["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "Total Projects"})
        .sort_values("Total Projects", ascending=True)
    )
    fig = px.bar(
        totals, x="Total Projects", y="collection", orientation="h",
        title="Total Approved Projects per Collection",
        labels={"collection": "Collection", "Total Projects": "Total Approved Projects"},
        color="collection",
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(showlegend=False)
    return fig


def make_cumulative_chart(df_flag: pd.DataFrame, selected_collections: list) -> go.Figure:
    sub = df_flag if not selected_collections else df_flag[df_flag["collection"].isin(selected_collections)]
    counts = (
        sub.groupby(["quarter_date", "collection"])["Project ID"]
        .count()
        .reset_index()
        .rename(columns={"Project ID": "New"})
    )
    counts = counts.sort_values("quarter_date")
    counts["Cumulative"] = counts.groupby("collection")["New"].cumsum()
    fig = px.area(
        counts, x="quarter_date", y="Cumulative", color="collection",
        title="Cumulative Approved Projects (Flagship Datasets)",
        labels={"quarter_date": "Quarter", "Cumulative": "Cumulative Projects", "collection": "Collection"},
        color_discrete_map=COLLECTION_COLOURS,
    )
    fig.update_layout(xaxis_tickformat="%b %Y", legend_title_text="Collection")
    return fig


# ---------------------------------------------------------------------------
# 3. App layout
# ---------------------------------------------------------------------------

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="DEA Projects Dashboard",
)

NAVBAR = dbc.Navbar(
    dbc.Container([
        html.Span("DEA Accredited Projects Dashboard", className="navbar-brand fw-bold fs-5"),
        html.Span(
            f"Data as of 24 March 2026  |  Source: {source_file}",
            className="text-muted small ms-auto",
        ),
    ], fluid=True),
    color="dark", dark=True, className="mb-3",
)

STAT_CARDS = dbc.Row([
    dbc.Col(dbc.Card([
        dbc.CardBody([html.H3(f"{TOTAL_PROJECTS:,}", className="card-title text-primary"),
                      html.P("Total DEA Projects", className="card-text text-muted")])
    ]), width=3),
    dbc.Col(dbc.Card([
        dbc.CardBody([html.H3(f"{TOTAL_FLAGSHIP:,}", className="card-title text-success"),
                      html.P("Flagship Dataset Projects", className="card-text text-muted")])
    ]), width=3),
    dbc.Col(dbc.Card([
        dbc.CardBody([html.H3(str(len(COLLECTIONS)), className="card-title text-warning"),
                      html.P("ADR Collections", className="card-text text-muted")])
    ]), width=3),
    dbc.Col(dbc.Card([
        dbc.CardBody([html.H3(DATA_DATE, className="card-title text-info fs-6 mt-1"),
                      html.P("Latest Project Date", className="card-text text-muted")])
    ]), width=3),
], className="mb-4 g-3")

COLLECTION_FILTER = dbc.Row([
    dbc.Col([
        html.Label("Filter by Collection:", className="fw-semibold"),
        dcc.Dropdown(
            id="collection-filter",
            options=[{"label": c, "value": c} for c in COLLECTIONS],
            multi=True,
            placeholder="All collections",
            clearable=True,
        ),
    ], width=6),
], className="mb-3")

OVERVIEW_TAB = dbc.Tab(label="Overview", tab_id="tab-overview", children=[
    dbc.Row([
        dbc.Col(dcc.Graph(id="overview-quarterly-chart"), width=12),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="overview-yearly-chart"), width=6),
        dbc.Col(dcc.Graph(id="overview-srs-chart"), width=6),
    ]),
])

FLAGSHIP_TAB = dbc.Tab(label="Flagship Datasets", tab_id="tab-flagship", children=[
    COLLECTION_FILTER,
    dbc.Row([
        dbc.Col(dcc.Graph(id="flagship-line-chart"), width=12),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="flagship-totals-chart"), width=6),
        dbc.Col(dcc.Graph(id="flagship-cumulative-chart"), width=6),
    ]),
])

BROWSE_TAB = dbc.Tab(label="Browse Projects", tab_id="tab-browse", children=[
    dbc.Row([
        dbc.Col([
            html.Label("Collection:", className="fw-semibold"),
            dcc.Dropdown(
                id="browse-collection-filter",
                options=[{"label": "All Collections", "value": "ALL"}]
                        + [{"label": c, "value": c} for c in COLLECTIONS],
                value="ALL",
                clearable=False,
            ),
        ], width=4),
        dbc.Col([
            html.Label("Search title / researcher:", className="fw-semibold"),
            dbc.Input(id="browse-search", placeholder="Type to filter...", type="text"),
        ], width=5),
        dbc.Col([
            html.Label("Show:", className="fw-semibold"),
            dcc.Dropdown(
                id="browse-scope",
                options=[
                    {"label": "All DEA Projects", "value": "all"},
                    {"label": "Flagship only", "value": "flagship"},
                ],
                value="flagship",
                clearable=False,
            ),
        ], width=3),
    ], className="mb-3 g-2"),
    html.Div(id="browse-count", className="text-muted small mb-2"),
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
            "padding": "6px 10px",
            "fontFamily": "sans-serif",
            "fontSize": "13px",
            "whiteSpace": "normal",
            "maxWidth": "400px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
        },
        style_header={
            "backgroundColor": "#343a40",
            "color": "white",
            "fontWeight": "bold",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"},
        ],
        tooltip_data=[],
        tooltip_delay=0,
        tooltip_duration=None,
    ),
])

app.layout = dbc.Container([
    NAVBAR,
    STAT_CARDS,
    dbc.Tabs([OVERVIEW_TAB, FLAGSHIP_TAB, BROWSE_TAB], id="main-tabs", active_tab="tab-overview"),
], fluid=True)


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
    # Quarterly
    fig_q = make_quarterly_chart(df_all)

    # Yearly
    yearly = df_all.groupby("Year")["Project ID"].count().reset_index()
    yearly.columns = ["Year", "Projects"]
    fig_y = px.bar(yearly, x="Year", y="Projects",
                   title="New DEA Projects by Year",
                   color_discrete_sequence=["#2ca02c"])
    fig_y.update_layout(bargap=0.2)

    # By Secure Research Service
    srs = (df_all["Secure Research Service"]
           .str.strip()
           .value_counts()
           .reset_index())
    srs.columns = ["SRS", "Count"]
    srs["SRS"] = srs["SRS"].str.replace(" Secure Research Service", "", regex=False)
    fig_srs = px.pie(srs, names="SRS", values="Count",
                     title="Projects by Secure Research Service",
                     hole=0.35)
    fig_srs.update_traces(textposition="inside", textinfo="percent+label")
    fig_srs.update_layout(showlegend=False)

    return fig_q, fig_y, fig_srs


@app.callback(
    Output("flagship-line-chart", "figure"),
    Output("flagship-totals-chart", "figure"),
    Output("flagship-cumulative-chart", "figure"),
    Input("collection-filter", "value"),
)
def update_flagship(selected_collections):
    if not len(df_flagship):
        empty = go.Figure().update_layout(title="No flagship data available")
        return empty, empty, empty

    sub = df_flagship
    if selected_collections:
        sub = df_flagship[df_flagship["collection"].isin(selected_collections)]

    return (
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
        # Use flagship frame (includes collection column), deduplicated per project
        base = df_flagship.drop_duplicates(subset=["Project ID", "collection"]).copy()
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

    # Tooltips for long cells
    tooltip_data = [
        {
            col: {"value": str(row.get(col, "")), "type": "markdown"}
            for col in display_cols
        }
        for row in table_data
    ]

    count_text = f"Showing {len(table_data):,} project{'s' if len(table_data) != 1 else ''}"
    return table_data, tooltip_data, count_text


# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
