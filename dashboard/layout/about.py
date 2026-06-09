"""About tab."""

from dash import dcc, html
import dash_bootstrap_components as dbc

from dashboard.config import FEEDBACK_EMAIL_URL, SOURCE_URL
from dashboard.data.registry import (
    PROCESSING_STATS, DATA_DATE, source_file,
    RETAINED_CONFLICTING_DUPLICATE_IDS_TEXT,
)


def build_about_tab():
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
| Rows with missing accreditation date or title removed | {PROCESSING_STATS['rows_after_required_fields']:,} | {PROCESSING_STATS['dropped_no_date_or_title']:,} |
| Filtered to DEA projects only (non-DEA/SRSA rows removed) | {PROCESSING_STATS['rows_after_dea_filter']:,} | {PROCESSING_STATS['dropped_non_dea']:,} |
| Tier 1 clerical duplicate rows removed | {PROCESSING_STATS['rows_after_dea_filter'] - PROCESSING_STATS['duplicate_tier1_rows_removed']:,} | {PROCESSING_STATS['duplicate_tier1_rows_removed']:,} |
| Tier 2 fragmented records merged | {PROCESSING_STATS['rows_after_duplicate_policy']:,} | {PROCESSING_STATS['duplicate_tier2_rows_removed']:,} |
| Tier 3 ambiguous duplicate rows flagged for review | {PROCESSING_STATS['rows_after_duplicate_policy']:,} | 0 |
| **Final dataset** | **{PROCESSING_STATS['final_rows']:,}** | |

Additional processing: column names are standardised, accreditation dates are
parsed, and year/quarter fields are derived for time-series analysis.

Duplicate policy:

- Same **Project ID** and **Title** rows with identical normalised datasets and researchers are collapsed as clerical duplicates.
- Same **Project ID**, **Title**, and accreditation date rows with fragmented datasets or researchers are merged by taking the union of parsed dataset entries and researcher entries.
- Ambiguous same-ID/same-title rows are retained and written to `{PROCESSING_STATS['duplicate_review_file']}` for manual review. Current flagged rows: {PROCESSING_STATS['duplicate_tier3_rows_flagged']:,}.
- Duplicate **Project ID** values with different titles are retained as separate projects for manual review.

Retained conflicting duplicate IDs:
`{RETAINED_CONFLICTING_DUPLICATE_IDS_TEXT}`

---

### Record Linkage Enrichment

Record-linkage and data-structure facets are read from the deterministic
register reference layer used by the Thematic Analysis tab. They are controlled
vocabulary lookups rather than LLM classifications.

Earlier dashboard versions included a keyword-matched "Cross-Domain Linked
Dataset Breakdown" based on the ADR UK flagship dataset list. That view is no
longer shown in Dataset Demand because it has been superseded by the
deterministic linkage layer. A future replacement should be recreated from the
current deterministic record-linkage and component-domain data.

---

### Individual Dataset Parsing (Dataset Demand Tab)

The "Datasets Used" free-text field is parsed into individual dataset entries:

1. **Split by newline** - each line typically represents one dataset source organisation
2. **Split by colon** - separates the dataset source organisation from the dataset list
3. **Split by comma and ampersand** - separates individual datasets within a dataset source organisation
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

- **Record linkage** - Deterministic classification of whether a project uses no
  record linkage, within-domain linkage, or cross-domain linkage, drawn from the
  register reference layer.

---

### Limitations and Caveats

- **Dataset parsing** splits on commas and ampersands, which can incorrectly
  break dataset source organisation names that contain these characters
  (e.g. "Department for Business, Energy & Industrial Strategy").
- **Duplicate handling** removes exact duplicates and same-ID/same-title
  duplicates, but retains duplicate IDs where the titles differ.
- **Dataset parsing** includes a cleanup pass for malformed provider breaks and
  drops obvious parser artefacts, but free-text source formatting can still
  produce imperfect splits.
- **Small processing environment categories** (under 3% of total projects) are grouped
  as "Other" in the pie chart for readability.
- **Project titles** alone may not fully describe the scope of a research project.

---

### LLM Thematic Analysis Methodology

**Note:** The Thematic Analysis tab is **experimental**. Classifications are
LLM-generated and have not yet been systematically validated against expert
review.

A separate analysis script (`llm_theme_analysis_v3.py`) classifies each project
from its title and datasets using substantive domains, analytical purpose, and
cross-cutting tags:

- **Layer A - Substantive Domain** (1 or more from the active domain set, e.g. "Education &
  Skills", "Health & Social Care", "Crime & Justice")
- **Layer C - Analytical Purpose** (1 or 2, e.g. "Policy Evaluation",
  "Descriptive Monitoring", "Life-Course Analysis")
- **Cross-cutting tags** - flags projects centred on COVID-19/pandemic framing,
  demographic disparities, or equity

Classification is performed by Claude (claude-opus-4-8) using structured output
via the Anthropic API. Labels follow the project taxonomy data dictionary, and
results are cached locally to avoid re-classification. Record-linkage properties
are no longer classified by the LLM; they are derived deterministically from the
register reference layer.

**Note:** Classification is based on both project titles and datasets used.
These fields may not fully convey the research methodology or the full scope of data linkage.
"""

    return dbc.Tab(label="About", tab_id="tab-about", children=[
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
