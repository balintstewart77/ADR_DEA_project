"""Thematic Analysis sub-tab."""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from dashboard.charts.template import CHART_CONFIG, CHART_HEIGHT
from dashboard.components.chart_tips import chart_wrapper
from dashboard.components.stat_card import stat_card
from dashboard.components.table_styles import ENRICHED_TABLE_STYLES
from dashboard import taxonomy
from dashboard import reference_definitions
from dashboard.config import REGISTER_SOURCE_ICON, DERIVED_FIELD_ICON
from dashboard.data.registry import (
    _ALL_DATASET_OPTIONS, _ALL_PROVIDER_OPTIONS, _ALL_INSTITUTION_OPTIONS, _ALL_TRE_OPTIONS,
)
from dashboard.data.thematic import (
    THEMATIC_DATA_AVAILABLE, THEMATIC_PROJECT_COUNT, THEMATIC_TAGGED_COUNT,
    LATENT_NO_LINKAGE_COUNT,
    _THEMATIC_DOMAIN_OPTIONS, _THEMATIC_DOMAIN_COUNT_OPTIONS,
    _THEMATIC_PURPOSE_OPTIONS, _THEMATIC_TAG_OPTIONS,
    _DETERMINISTIC_RECORD_LINKAGE_OPTIONS,
    _DETERMINISTIC_COLLECTION_METHOD_OPTIONS,
    _DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS,
    _DETERMINISTIC_UNIT_OPTIONS,
    _DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS,
)

_MD_STYLE = {"fontSize": "0.88rem", "lineHeight": "1.6"}
DOMAIN_MATRIX_HEIGHT = 724
LATENT_DEMAND_HEIGHT = 724
DOMAIN_PURPOSE_HEIGHT = 560
DOMAIN_LINKAGE_HEIGHT = 560
TAG_DOMAIN_HEIGHT = 440
DOMAIN_TREND_HEIGHT = 480
RECORD_LINKAGE_TREND_HEIGHT = 360
COMPACT_DISTRIBUTION_HEIGHT = 280
RESEARCHER_SECTOR_MATRIX_HEIGHT = 500


def _md_table(layer: str) -> str:
    """Render a label/definition markdown table straight from the taxonomy dictionary."""
    lines = ["| Label | Definition |", "|---|---|"]
    for label, definition in taxonomy.category_rows(layer):
        safe = definition.replace("|", "\\|")
        lines.append(f"| {label} | {safe} |")
    return "\n".join(lines)


def _graph(graph_id: str, height: int = CHART_HEIGHT) -> html.Div:
    """A chart wrapper with a fixed graph height that survives re-render."""
    return chart_wrapper(
        dcc.Graph(
            id=graph_id,
            config=CHART_CONFIG,
            responsive=True,
            style={"height": f"{height}px"},
        ),
        graph_id,
        style={"minHeight": f"{height + 8}px"},
    )


def _metric_dropdown(dropdown_id: str) -> dbc.Row:
    return dbc.Row([
        dbc.Col([
            html.Label("Metric", className="filter-label"),
            dcc.Dropdown(
                id=dropdown_id,
                options=[
                    {"label": "% of projects", "value": "pct"},
                    {"label": "Project count", "value": "count"},
                ],
                value="pct",
                clearable=False,
                searchable=False,
            ),
        ], md=3),
    ], className="mb-2 g-2")


def _domain_share_dropdown(dropdown_id: str) -> dbc.Row:
    """Count vs %-of-domain metric control for the tag-by-domain bars."""
    return dbc.Row([
        dbc.Col([
            html.Label("Metric", className="filter-label"),
            dcc.Dropdown(
                id=dropdown_id,
                options=[
                    {"label": "Project count", "value": "count"},
                    {"label": "% of domain's projects", "value": "pct"},
                ],
                value="count",
                clearable=False,
                searchable=False,
            ),
        ], md=6),
    ], className="mb-2 g-2")


def _definition_detail(detail: dict) -> html.Div:
    content = detail["content"]
    if isinstance(content, list):
        body = html.Ul([html.Li(item) for item in content], className="mb-0")
    else:
        body = dcc.Markdown(content, style=_MD_STYLE)
    return html.Div([
        html.Strong(detail["title"]),
        body,
    ], className="mb-2")


def _deterministic_facet_definition(facet: dict) -> html.Div:
    return html.Div([
        html.H5(facet["name"], className="mb-1"),
        html.P([
            html.Strong("Values: "),
            ", ".join(facet["values"]),
        ], className="text-muted small mb-2"),
        dcc.Markdown(f"**Rule:** {facet['rule']}", style=_MD_STYLE),
        html.Details([
            html.Summary("Worked edge cases and secondary rules"),
            html.Div(
                [_definition_detail(detail) for detail in facet["details"]],
                className="mt-2",
            ),
        ], className="mb-3"),
    ], className="mb-3")


def _deterministic_definitions_section() -> html.Div:
    return html.Div([
        html.P(
            "These facets are derived deterministically from the register via fixed rules — "
            "exact, reproducible, auditable. The rules below are read from "
            "analysis/register_reference.yaml.",
            className="section-desc",
        ),
        dcc.Markdown(reference_definitions.meta_principle(), style=_MD_STYLE),
        html.Hr(),
        *[
            _deterministic_facet_definition(facet)
            for facet in reference_definitions.deterministic_facets()
        ],
    ], className="deterministic-defs")


_glossary_md = """
| Acronym | Full term |
|---|---|
| ADR | Administrative Data Research |
| ADR UK | Administrative Data Research UK |
| AD\\|ARC | Administrative Data \\| Agricultural Research Collection |
| ALB | Arm's-length body |
| API | Application programming interface |
| ASHE | Annual Survey of Hours and Earnings |
| BSD | Business Structure Database |
| CPI | Consumer Prices Index |
| DEA | Digital Economy Act |
| DfE | Department for Education |
| DWP | Department for Work and Pensions |
| ECHILD | Education and Child Health Insights from Linked Data |
| EES | Earnings and Employees Study |
| EOL | Education Outcomes Linkage |
| GRADE | Grading and Admissions Data for England |
| GVA | Gross Value Added |
| GUIE | Growing Up in England |
| HES | Hospital Episode Statistics |
| HEI | Higher education institution |
| HMRC | HM Revenue and Customs |
| IDBR | Inter-Departmental Business Register |
| ILR | Individualised Learner Record |
| LEO | Longitudinal Education Outcomes |
| LLM | Large language model |
| LS | Longitudinal Study |
| MoJ | Ministry of Justice |
| NDPB | Non-departmental public body |
| NHS | National Health Service |
| NINo | National Insurance number |
| NISRA | Northern Ireland Statistics and Research Agency |
| NMC | Nursing and Midwifery Council |
| NPD | National Pupil Database |
| ONS | Office for National Statistics |
| PAYE | Pay As You Earn |
| PHDA | Public Health Data Asset |
| PPI | Producer Price Index |
| SRS | Secure Research Service |
| UCAS | Universities and Colleges Admissions Service |
| VOA | Valuation Office Agency |
| WED | Wage and Employment Dynamics programme; its datasets are named individually, e.g. ASHE linked to Census or PAYE/Self-Assessment. |
"""


_thematic_methodology_md = f"""
**Model:** Claude Fable 5 (`claude-fable-5`) via the Anthropic API with
structured JSON output.

**Taxonomy:** Labels follow the project taxonomy data dictionary
(`{taxonomy.DICTIONARY_VERSION}`, ontology {taxonomy.ONTOLOGY_VERSION}). The
dashboard reads its label set directly from that dictionary, so the displayed
categories cannot drift from the ones the classifier used.

**Input:** Each project's title and its listed datasets are sent together — the
title gives the research question, and the datasets provide additional
classification evidence.

**Batch processing:** Projects are classified in batches of 10 with retry logic
for transient API failures, and results are cached so that re-runs only classify
new or changed projects.

**Reliability:** Classification is not fully deterministic — repeated runs can
differ on borderline cases. Stability was assessed by re-running the model over
the entire register a second time and comparing the two passes.
"""

_thematic_layers_md = f"""
These classifications are LLM-inferred from project titles and dataset names.
They are indicative rather than definitive, pending validation.

#### Substantive Domain (1 or more per project)

What the project is about. Assigned from the datasets and research question:

{_md_table(taxonomy.LAYER_A_DOMAIN)}

#### Analytical Purpose (1 or 2 per project)

What analytical purpose the project serves:

{_md_table(taxonomy.LAYER_C_PURPOSE)}

#### Cross-Cutting Tag (zero or more, orthogonal to the classifications)

{_md_table(taxonomy.LAYER_CROSS_CUTTING_TAG)}
"""

_enriched_register_desc = (
    "The Enriched Register combines the canonical DEA register (the source of truth, "
    "also accessible via the Project Explorer) with classifications and analytical fields "
    f"derived from the project descriptions. Columns sourced directly from the public "
    f"register are marked with a {REGISTER_SOURCE_ICON} icon; classifications derived "
    f"by the dashboard's analytical layer are marked with a {DERIVED_FIELD_ICON} icon."
)


def _latent_demand_accordion_item() -> dbc.AccordionItem:
    return dbc.AccordionItem(
        [
            dbc.Alert([
                html.Strong("Indicative — mixed analytical layers."),
                " This is the dashboard's first deliberately mixed-layer figure: substantive "
                "domains are LLM-inferred (unvalidated, pending validation), while the "
                "no-record-linkage filter is deterministic. Treat the cell values as "
                "indicative rather than definitive.",
            ], color="warning", className="mb-3"),
            html.P(
                f"Domain co-occurrence computed ONLY over the {LATENT_NO_LINKAGE_COUNT:,} "
                "classified projects with no record linkage — researchers combining domains "
                "without using any linked product. Dot-marked cells indicate domain pairs already "
                "served by an existing linked product (the pair is contained in some product's "
                "component domains). Reading: a heavy unserved cell suggests latent demand for "
                "a new cross-domain asset; a heavy served cell suggests an awareness gap or "
                "deliberate non-use of the existing product.",
                className="section-desc",
            ),
            _metric_dropdown("thematic-latent-demand-metric"),
            _graph("thematic-latent-demand", height=LATENT_DEMAND_HEIGHT),
        ],
        title="Latent cross-domain demand (indicative)",
    )


def _deterministic_intro() -> html.P:
    return html.P(
        "These deterministic facets are exact, reproducible lookups derived "
        "from the register and analysis/register_reference.yaml.",
        className="section-desc",
    )


def _analyses_accordion():
    return dbc.Accordion(
        [
            dbc.AccordionItem(
                dbc.Row([
                    dbc.Col(_graph("thematic-domain-totals", height=TAG_DOMAIN_HEIGHT), md=6),
                    dbc.Col(_graph("thematic-purpose-totals", height=380), md=6),
                ], className="g-3"),
                title="Overall Distribution",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        "Projects may belong to multiple domains, so percentages sum to more "
                        "than 100% per year. Click a legend entry to show/hide individual domains.",
                        className="section-desc",
                    ),
                    _metric_dropdown("thematic-domain-trend-metric"),
                    _graph("thematic-domain-trend", height=DOMAIN_TREND_HEIGHT),
                    html.P(
                        "Projects may have up to two purposes, so percentages can sum to slightly "
                        "more than 100%.",
                        className="section-desc mt-3",
                    ),
                    _metric_dropdown("thematic-purpose-trend-metric"),
                    _graph("thematic-purpose-trend", height=CHART_HEIGHT),
                ],
                title="Substantive domain and Analytical purpose trends over time",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        "Substantive domains are multi-label, so each project is counted once per "
                        "domain it is assigned — column totals can therefore exceed the project count. "
                        "All domains are shown. The metric control below switches the cells between "
                        "counts and each domain's row-wise percentage; the hover always shows both.",
                        className="section-desc",
                    ),
                    _metric_dropdown("thematic-cross-domain-purpose-metric"),
                    _graph("thematic-cross-domain-purpose", height=DOMAIN_PURPOSE_HEIGHT),
                ],
                title="Domain × Purpose breakdown",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        "Substantive domains are multi-label, so a project can carry several. "
                        "This matrix counts how often each pair of domains appears together in "
                        "the same project — which research areas are studied jointly. Diagonal "
                        "cells count projects whose domain set is exactly that one domain. The "
                        "\"Unclear\" fallback is excluded. In count mode the off-diagonal matrix "
                        "is symmetric; the metric control below switches it to a row-wise share "
                        "of the row domain's projects, which is directional. The hover shows both.",
                        className="section-desc",
                    ),
                    _metric_dropdown("thematic-domain-cooccurrence-metric"),
                    _graph("thematic-domain-cooccurrence", height=DOMAIN_MATRIX_HEIGHT),
                ],
                title="Domain Co-occurrence",
            ),
            dbc.AccordionItem(
                [
                    html.P(
                        f"Cross-cutting tags, orthogonal to the layers, mark projects whose "
                        f"analysis centres on a tag-defined lens or condition. At least one tag applies to "
                        f"{THEMATIC_TAGGED_COUNT:,} of {THEMATIC_PROJECT_COUNT:,} classified projects. "
                        "The trend has its own metric control; the domain bars below split the two "
                        "active tags into separate charts.",
                        className="section-desc",
                    ),
                    _metric_dropdown("thematic-tag-trend-metric"),
                    _graph("thematic-tag-trend", height=CHART_HEIGHT),
                    dbc.Row([
                        dbc.Col([
                            _domain_share_dropdown("thematic-covid-tag-domain-metric"),
                            _graph("thematic-covid-tag-domain", height=TAG_DOMAIN_HEIGHT),
                        ], md=6),
                        dbc.Col([
                            _domain_share_dropdown("thematic-demographic-tag-domain-metric"),
                            _graph("thematic-demographic-tag-domain", height=TAG_DOMAIN_HEIGHT),
                        ], md=6),
                    ], className="g-3"),
                    html.P(
                        "\"% of domain's projects\" divides each bar by the number of classified "
                        "projects carrying that domain, so large domains stop dominating purely "
                        "through size. Each chart's metric control is independent.",
                        className="section-desc text-muted small mt-2",
                    ),
                ],
                title="Cross-Cutting Tags",
            ),
            dbc.AccordionItem(
                [
                    _deterministic_intro(),
                    dbc.Row([
                        dbc.Col(
                            _graph(
                                "deterministic-record-linkage-distribution",
                                height=COMPACT_DISTRIBUTION_HEIGHT,
                            ),
                            lg=4,
                            md=6,
                        ),
                    ], className="g-3"),
                    _metric_dropdown("deterministic-record-linkage-trend-metric"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Granularity", className="filter-label"),
                            dcc.Dropdown(
                                id="deterministic-record-linkage-trend-granularity",
                                options=[
                                    {"label": "Year", "value": "year"},
                                    {"label": "Quarter", "value": "quarter"},
                                ],
                                value="year",
                                clearable=False,
                                searchable=False,
                            ),
                        ], md=3),
                    ], className="mb-2 g-2"),
                    _graph(
                        "deterministic-record-linkage-trend",
                        height=RECORD_LINKAGE_TREND_HEIGHT,
                    ),
                    _metric_dropdown("deterministic-domain-linkage-metric"),
                    _graph(
                        "deterministic-domain-linkage-breakdown",
                        height=DOMAIN_LINKAGE_HEIGHT,
                    ),
                ],
                title="Record linkage",
            ),
            dbc.AccordionItem(
                [
                    _deterministic_intro(),
                    dbc.Row([
                        dbc.Col(
                            _graph(
                                "deterministic-researcher-sector-distribution",
                                height=COMPACT_DISTRIBUTION_HEIGHT,
                            ),
                            lg=4,
                            md=6,
                        ),
                    ], className="g-3"),
                    _graph(
                        "deterministic-researcher-sector-cooccurrence",
                        height=RESEARCHER_SECTOR_MATRIX_HEIGHT,
                    ),
                ],
                title="Researcher sector",
            ),
            dbc.AccordionItem(
                [
                    _deterministic_intro(),
                    dbc.Row([
                        dbc.Col(
                            _graph(
                                "deterministic-unit-distribution",
                                height=COMPACT_DISTRIBUTION_HEIGHT,
                            ),
                            lg=4,
                            md=6,
                        ),
                    ], className="g-3"),
                    _metric_dropdown("deterministic-unit-trend-metric"),
                    _graph("deterministic-unit-trend", height=CHART_HEIGHT),
                ],
                title="Unit of observation",
            ),
            dbc.AccordionItem(
                [
                    _deterministic_intro(),
                    dbc.Row([
                        dbc.Col(
                            _graph(
                                "deterministic-collection-method-distribution",
                                height=COMPACT_DISTRIBUTION_HEIGHT,
                            ),
                            lg=4,
                            md=6,
                        ),
                        dbc.Col(
                            _graph(
                                "deterministic-temporal-structure-distribution",
                                height=COMPACT_DISTRIBUTION_HEIGHT,
                            ),
                            lg=4,
                            md=6,
                        ),
                    ], className="g-3"),
                    html.P(
                        "These trends recompute each year's share from the per-project facets. "
                        "Multi-count: a project using both survey and administrative data "
                        "counts in both lines (likewise for temporal structure), so shares "
                        "can sum past 100%.",
                        className="section-desc mt-3",
                    ),
                    _metric_dropdown("deterministic-collection-method-trend-metric"),
                    _graph("deterministic-collection-method-trend", height=CHART_HEIGHT),
                    _metric_dropdown("deterministic-temporal-structure-trend-metric"),
                    _graph("deterministic-temporal-structure-trend", height=CHART_HEIGHT),
                ],
                title="Collection method & temporal structure",
            ),
            _latent_demand_accordion_item(),
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
                            html.Label("Dataset source organisation", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-provider-filter",
                                options=_ALL_PROVIDER_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                                placeholder="All dataset source organisations",
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
                            html.Label("Cross-cutting tag", className="filter-label"),
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
                            html.Label("Record Linkage", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-record-linkage-filter",
                                options=_DETERMINISTIC_RECORD_LINKAGE_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=False,
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Collection method", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-collection-method-filter",
                                options=_DETERMINISTIC_COLLECTION_METHOD_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                            ),
                        ], md=3),
                        dbc.Col([
                            html.Label("Temporal structure", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-temporal-structure-filter",
                                options=_DETERMINISTIC_TEMPORAL_STRUCTURE_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Unit of observation", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-unit-filter",
                                options=_DETERMINISTIC_UNIT_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                            ),
                        ], md=2),
                        dbc.Col([
                            html.Label("Researcher sector", className="filter-label"),
                            dcc.Dropdown(
                                id="enriched-researcher-sector-filter",
                                options=_DETERMINISTIC_RESEARCHER_SECTOR_OPTIONS,
                                value="ALL",
                                clearable=False,
                                searchable=True,
                            ),
                        ], md=3),
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
                                {"name": f"{DERIVED_FIELD_ICON} Record Linkage", "id": "record_linkage"},
                                {"name": f"{DERIVED_FIELD_ICON} Collection method", "id": "dataset_collection_methods"},
                                {"name": f"{DERIVED_FIELD_ICON} Temporal structure", "id": "dataset_temporal_structures"},
                                {"name": f"{DERIVED_FIELD_ICON} Unit of observation", "id": "dataset_units"},
                                {"name": f"{DERIVED_FIELD_ICON} Researcher sector", "id": "researcher_sectors"},
                                {"name": f"{DERIVED_FIELD_ICON} Domains", "id": "substantive_domains"},
                                {"name": f"{DERIVED_FIELD_ICON} Substantive domain count", "id": "substantive_domain_count"},
                                {"name": f"{DERIVED_FIELD_ICON} Purpose", "id": "analytical_purpose"},
                                {"name": f"{DERIVED_FIELD_ICON} Cross-cutting tags", "id": "cross_cutting_tags"},
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
                html.Strong("Enrichment scope"),
                " — This section combines deterministic facets and LLM classifications. ",
                html.Strong("Deterministic facets"),
                " (record linkage, collection method, temporal structure, unit, and researcher sector) "
                "are controlled-vocabulary lookups: exact and reproducible. ",
                html.Strong("LLM classifications"),
                " (substantive domain, analytical purpose, and cross-cutting tags) are inferred by "
                "Claude Opus from project titles and dataset names only. They are indicative rather "
                "than definitive, pending validation, and ambiguous or terse titles may be misclassified.",
            ], color="warning", className="mb-3 mt-2"),

            # Summary stats
            dbc.Row([
                stat_card(f"{THEMATIC_PROJECT_COUNT:,}", "Projects Classified", "#2a9d8f"),
                stat_card(f"{len(taxonomy.DOMAIN_LABELS)}", "Substantive Domains", "#264653"),
                stat_card(f"{len(taxonomy.PURPOSE_LABELS)}", "Analytical Purposes", "#e76f51"),
                stat_card(f"{len(taxonomy.TAG_LABELS)}", "Cross-Cutting Tags", "#457b9d"),
            ], className="mb-3 g-3"),

            html.P(
                "Each project is independently classified by substantive research domain(s), "
                "analytical purpose, and cross-cutting tags. Projects may belong to multiple "
                "domains, may have up to two analytical purposes, and may carry multiple tags.",
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
                    title="Classification definitions",
                ),
                dbc.AccordionItem(
                    _deterministic_definitions_section(),
                    title="Deterministic facet definitions",
                ),
                dbc.AccordionItem(
                    dcc.Markdown(_glossary_md, style=_MD_STYLE, className="taxonomy-defs"),
                    title="Acronyms and abbreviations glossary",
                ),
            ], start_collapsed=True, className="mb-4"),

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
