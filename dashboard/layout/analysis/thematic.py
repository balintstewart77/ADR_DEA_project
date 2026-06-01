"""Thematic Analysis sub-tab."""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from dashboard.charts.template import CHART_CONFIG
from dashboard.components.stat_card import stat_card
from dashboard.components.table_styles import ENRICHED_TABLE_STYLES
from dashboard import taxonomy
from dashboard.config import REGISTER_SOURCE_ICON, DERIVED_FIELD_ICON
from dashboard.data.registry import (
    _ALL_DATASET_OPTIONS, _ALL_PROVIDER_OPTIONS, _ALL_INSTITUTION_OPTIONS, _ALL_TRE_OPTIONS,
)
from dashboard.data.thematic import (
    THEMATIC_DATA_AVAILABLE, THEMATIC_NARRATIVE, THEMATIC_PROJECT_COUNT, THEMATIC_TAGGED_COUNT,
    THEMATIC_PROJECT_CROSS_RATE, THEMATIC_ASSIGNMENT_CROSS_RATE,
    _THEMATIC_DOMAIN_OPTIONS, _THEMATIC_DOMAIN_COUNT_OPTIONS,
    _THEMATIC_LINKAGE_OPTIONS, _THEMATIC_PURPOSE_OPTIONS, _THEMATIC_TAG_OPTIONS,
)

_MD_STYLE = {"fontSize": "0.85rem", "lineHeight": "1.6"}


def _md_table(layer: str) -> str:
    """Render a label/definition markdown table straight from the taxonomy dictionary."""
    lines = ["| Label | Definition |", "|---|---|"]
    for label, definition in taxonomy.category_rows(layer):
        safe = definition.replace("|", "\\|")
        lines.append(f"| {label} | {safe} |")
    return "\n".join(lines)


def _graph(graph_id: str) -> html.Div:
    """A chart wrapper whose graph resizes correctly when its accordion opens."""
    return html.Div(
        dcc.Graph(id=graph_id, config=CHART_CONFIG, responsive=True),
        className="chart-wrapper",
    )


_thematic_methodology_md = f"""
**Model:** Claude Opus 4.8 (`claude-opus-4-8`) via the Anthropic API with
structured JSON output.

**Taxonomy:** Labels follow the project taxonomy data dictionary
(`{taxonomy.DICTIONARY_VERSION}`, ontology {taxonomy.ONTOLOGY_VERSION}). The
dashboard reads its label set directly from that dictionary, so the displayed
categories cannot drift from the ones the classifier used.

**Input:** Each project's title and its listed datasets are sent together — the
title gives the research question, the datasets reveal the domains and linkage scope.

**Batch processing:** Projects are classified in batches of 10 with retry logic
for transient API failures, and results are cached so that re-runs only classify
new or changed projects.

**Reliability:** Classification is not fully deterministic — repeated runs can
differ on borderline cases. Stability was assessed by re-running the model over
the entire register a second time and comparing the two passes.
"""

_thematic_layers_md = f"""
#### Layer A — Substantive Domain (1 or more per project)

What the project is about. Assigned from the datasets and research question:

{_md_table(taxonomy.LAYER_A_DOMAIN)}

&nbsp;

#### Layer B — Linkage Mode (exactly 1 per project)

How the data are linked, judged by the number of policy domains the datasets span:

{_md_table(taxonomy.LAYER_B_LINKAGE)}

&nbsp;

#### Layer C — Analytical Purpose (1 or 2 per project)

What analytical purpose the project serves:

{_md_table(taxonomy.LAYER_C_PURPOSE)}

&nbsp;

#### Cross-Cutting Tag (zero or more, orthogonal to the three layers)

{_md_table(taxonomy.LAYER_CROSS_CUTTING_TAG)}
"""

_linkage_profile_desc = (
    "This chart compares the linkage profile of each substantive domain, showing "
    "the share of projects in that domain that are single-dataset, within-domain "
    "linkage, or cross-domain linkage. Domains are ordered by their cross-domain "
    "share. Because Layer A is multi-label, a project is counted once in each domain "
    "it touches; a cross-domain project may therefore contribute to several domain "
    "bars. The chart is assignment-weighted: it describes the distribution of linkage "
    "modes across domain assignments, not across unique projects. On that basis, "
    f"{THEMATIC_ASSIGNMENT_CROSS_RATE:g}% of domain assignments are cross-domain, "
    f"compared with {THEMATIC_PROJECT_CROSS_RATE:g}% of projects when each project is "
    "counted once. Use the chart to compare domains with each other, not as the "
    "headline portfolio-wide project-level rate."
)

_enriched_register_desc = (
    "The Enriched Register combines the canonical DEA register (the source of truth, "
    "also accessible via the Project Explorer) with classifications and analytical fields "
    f"derived from the project descriptions. Columns sourced directly from the public "
    f"register are marked with a {REGISTER_SOURCE_ICON} icon; classifications derived "
    f"by the dashboard's analytical layer are marked with a {DERIVED_FIELD_ICON} icon."
)


def _analyses_accordion():
    return dbc.Accordion(
        [
            dbc.AccordionItem(
                [
                    html.P(
                        "Projects may belong to multiple domains, so percentages sum to more "
                        "than 100% per year. Click a legend entry to show/hide individual domains.",
                        className="section-desc",
                    ),
                    _graph("thematic-domain-trend"),
                    html.P(
                        "Each project has exactly one linkage mode, so these shares are compositional.",
                        className="section-desc mt-3",
                    ),
                    _graph("thematic-linkage-trend"),
                    html.P(
                        "Projects may have up to two purposes, so percentages can sum to slightly "
                        "more than 100%.",
                        className="section-desc mt-3",
                    ),
                    _graph("thematic-purpose-trend"),
                ],
                title="Layer Trends Over Time",
            ),
            dbc.AccordionItem(
                dbc.Row([
                    dbc.Col(_graph("thematic-domain-totals"), md=5),
                    dbc.Col(_graph("thematic-linkage-totals"), md=3),
                    dbc.Col(_graph("thematic-purpose-totals"), md=4),
                ], className="g-3"),
                title="Overall Distribution",
            ),
            dbc.AccordionItem(
                [
                    html.P(_linkage_profile_desc, className="section-desc"),
                    _graph("thematic-linkage-complexity"),
                ],
                title="Linkage Profile by Domain (relative complexity)",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        "Substantive domains are multi-label, so each project is counted once per "
                        "domain it is assigned — column totals can therefore exceed the project count. "
                        "All domains are shown. The metric toggle above switches the cells between "
                        "counts and each domain's row-wise percentage; the hover always shows both.",
                        className="section-desc",
                    ),
                    dbc.Row([
                        dbc.Col(_graph("thematic-cross-mode-domain"), md=6),
                        dbc.Col(_graph("thematic-cross-domain-purpose"), md=6),
                    ], className="g-3"),
                ],
                title="Cross-Layer Patterns",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        "Substantive domains are multi-label, so a project can carry several. "
                        "This matrix counts how often each pair of domains appears together in "
                        "the same project — which research areas are studied jointly. The "
                        "diagonal (a domain with itself) is omitted and the \"Unclear\" fallback "
                        "is excluded. In count mode the matrix is symmetric (projects carrying "
                        "both domains); the metric toggle switches it to a row-wise share — of "
                        "the row domain's projects, the percentage that also touch the column "
                        "domain — which is directional, so the matrix is no longer symmetric. "
                        "The hover shows both.",
                        className="section-desc",
                    ),
                    _graph("thematic-domain-cooccurrence"),
                ],
                title="Domain Co-occurrence",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        f"A cross-cutting tag, orthogonal to the three layers, marks projects whose "
                        f"analysis centres on demographic disparities or equity. It applies to "
                        f"{THEMATIC_TAGGED_COUNT:,} of {THEMATIC_PROJECT_COUNT:,} classified projects. "
                        "The trend follows the metric toggle above; the bar shows which domains the "
                        "tagged projects fall in.",
                        className="section-desc",
                    ),
                    dbc.Row([
                        dbc.Col(_graph("thematic-tag-trend"), md=6),
                        dbc.Col(_graph("thematic-tag-domain"), md=6),
                    ], className="g-3"),
                ],
                title="Demographic-Disparities / Equity Lens",
            ),
            dbc.AccordionItem(
                [
                    html.P(_enriched_register_desc, className="section-desc"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Search", className="filter-label"),
                            dbc.Input(
                                id="enriched-search",
                                placeholder="Search by project ID, title, or researcher…",
                                type="text",
                            ),
                        ], md=5),
                        dbc.Col([
                            html.Label("Dataset", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-dataset-filter",
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
                                id="enriched-provider-filter",
                                options=_ALL_PROVIDER_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                                placeholder="All source organisations",
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Domain count", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-domain-count-filter",
                                options=_THEMATIC_DOMAIN_COUNT_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=False,
                            ),
                        ], md=2),
                    ], className="mb-2 g-2"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Research institution", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-institution-filter",
                                options=_ALL_INSTITUTION_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                                placeholder="All institutions",
                            ),
                        ], md=3),
                        dbc.Col([
                            html.Label("Processing environment", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-tre-filter",
                                options=_ALL_TRE_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                                placeholder="All processing environments",
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Domain", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-domain-filter",
                                options=_THEMATIC_DOMAIN_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Linkage mode", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-linkage-filter",
                                options=_THEMATIC_LINKAGE_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=False,
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Analytical purpose", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-purpose-filter",
                                options=_THEMATIC_PURPOSE_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Demographic / equity tag", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-tag-filter",
                                options=_THEMATIC_TAG_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=False,
                            ),
                        ], md=3),
                        dbc.Col([
                            html.Label("Per page", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-page-size",
                                options=[{"label": str(n), "value": n} for n in [10, 20, 50, 100]],
                                value=20,
                                clearable=False,
                                searchable=False,
                            ),
                        ], md=1),
                    ], className="mb-2 g-2"),
                    dbc.Row([
                        dbc.Col([
                            html.Div(
                                id="enriched-browse-count",
                                className="text-muted small",
                                style={"paddingTop": "0.35rem", "textAlign": "center"},
                            ),
                        ], md=9),
                        dbc.Col([
                            html.Button(
                                "Download CSV",
                                id="enriched-download-btn",
                                className="btn btn-outline-primary btn-sm w-100",
                            ),
                            dbc.Tooltip(
                                "Downloads all projects matching the current filters.",
                                target="enriched-download-btn",
                                placement="top",
                            ),
                        ], md=3),
                    ], className="mb-3 g-2"),
                    html.Div(
                        dash_table.DataTable(
                            id="enriched-register-table",
                            columns=[
                                {"name": f"{REGISTER_SOURCE_ICON} Project ID", "id": "Project ID"},
                                {"name": f"{REGISTER_SOURCE_ICON} Title", "id": "Title"},
                                {"name": f"{REGISTER_SOURCE_ICON} Researchers", "id": "Researchers"},
                                {"name": f"{REGISTER_SOURCE_ICON} Datasets Used", "id": "Datasets Used"},
                                {"name": f"{REGISTER_SOURCE_ICON} Processing environment", "id": "Secure Research Service"},
                                {"name": f"{REGISTER_SOURCE_ICON} Accreditation Date", "id": "Accreditation Date"},
                                {"name": f"{DERIVED_FIELD_ICON} Domains", "id": "substantive_domains"},
                                {"name": f"{DERIVED_FIELD_ICON} Layer A domain count", "id": "substantive_domain_count"},
                                {"name": f"{DERIVED_FIELD_ICON} Linkage mode", "id": "linkage_mode"},
                                {"name": f"{DERIVED_FIELD_ICON} Purpose", "id": "analytical_purpose"},
                                {"name": f"{DERIVED_FIELD_ICON} Demographic / equity tag", "id": "cross_cutting_tags"},
                                {"name": f"{DERIVED_FIELD_ICON} Rationale", "id": "rationale"},
                            ],
                            page_size=20,
                            sort_action="native",
                            filter_action="none",
                            **ENRICHED_TABLE_STYLES,
                        ),
                        className="dea-table mb-2",
                    ),
                ],
                title="Enriched Register",
            ),
        ],
        start_collapsed=True,
        always_open=True,
        className="mb-4",
    )


def build_thematic_tab():
    if THEMATIC_DATA_AVAILABLE:
        children = [
            # Caveat banner
            dbc.Alert([
                html.Strong("Experimental Analysis"),
                " — Classifications below were generated by a large language model (Claude Opus). "
                "They are based on project titles and dataset names only, and should be treated as "
                "indicative rather than definitive. Ambiguous or terse titles may be misclassified.",
            ], color="warning", className="mb-3 mt-2"),

            # Summary stats
            dbc.Row([
                stat_card(f"{THEMATIC_PROJECT_COUNT:,}", "Projects Classified", "#2a9d8f"),
                stat_card(f"{len(taxonomy.DOMAIN_LABELS)}", "Substantive Domains", "#264653"),
                stat_card(f"{len(_THEMATIC_LINKAGE_OPTIONS) - 1:,}", "Linkage Modes", "#457b9d"),
                stat_card(f"{len(taxonomy.PURPOSE_LABELS)}", "Analytical Purposes", "#e76f51"),
            ], className="mb-3 g-3"),

            html.P(
                "Each project is independently classified across three layers: "
                "the substantive research domain(s), the data linkage complexity, "
                "and the analytical purpose. Projects may belong to multiple domains "
                "and may have up to two analytical purposes.",
                className="section-desc",
            ),

            # Collapsible methods
            dbc.Accordion([
                dbc.AccordionItem(
                    dcc.Markdown(_thematic_methodology_md, style=_MD_STYLE),
                    title="Classification Methodology",
                ),
                dbc.AccordionItem(
                    dcc.Markdown(_thematic_layers_md, style=_MD_STYLE, className="taxonomy-defs"),
                    title="Layer Definitions",
                ),
                dbc.AccordionItem(
                    dcc.Markdown(THEMATIC_NARRATIVE, style=_MD_STYLE),
                    title="Analytical Narrative (LLM-Generated)",
                ),
            ], start_collapsed=True, className="mb-4"),

            # Metric toggle (drives the chart sections below)
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

            html.P(
                "Expand a section to view it — several can be open at once.",
                className="section-desc text-muted",
            ),

            # Collapsible analyses
            _analyses_accordion(),
        ]
    else:
        children = [
            dbc.Alert(
                "Thematic analysis data not available. Run analysis/llm_theme_analysis_v3.py to generate.",
                color="info", className="mt-3",
            ),
        ]

    return dbc.Tab(
        label="Thematic Analysis (Experimental)", tab_id="tab-thematic", children=children,
    )
