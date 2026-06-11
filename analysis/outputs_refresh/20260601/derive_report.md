# rc2 temporal-structure correction report

## Scope

Reference version `0.4.6` was applied to 1,309 cleaned DEA register records. Output CSV: `analysis/outputs_deterministic_rc2/register_properties.csv`.

This run is deterministic and uses no LLM calls.

Reference 0.4.1 is a targeted correction: it tightens the temporal-structure rule to producer design/weighting/release and reclassifies aggregate indicators that are time series but not unit-following panels.

## Canonical keys

Datasets are parsed with `dashboard.dataset_normalisation.parse_datasets`, which applies `normalise_dataset_name` to each parsed dataset entry. Lookup first uses that exact canonical dataset string, then falls back to `dataset_family_for` where the normaliser defines a reviewed family key.

Researcher organisations are parsed with `dashboard.institution_normalisation.parse_institutions` and matched on the parser's canonical `institution` string.

## Record linkage

Record linkage is derived from linked-product component domains. A product with components from no recognised linked product is "No record linkage"; a product whose component-domain union contains one domain is within-domain; a product whose union contains two or more domains is cross-domain. linkage_span is derived from component_domains and is never stored in this reference.


A linked component contributes the "Migration & Demographics" domain only when the dataset's substantive origin is population or demography, such as Census as a population source, not when a dataset merely carries demographic fields. NPD ethnicity or free-school-meal attributes are attributes of education records, not a separate demographic component.


| Record linkage span | Count |
|---|---:|
| No record linkage | 904 |
| Within-domain record linkage | 124 |
| Cross-domain record linkage | 281 |

### Linkage edge checks

| Dataset | Products | Span | Expected | Pass |
|---|---|---|---|---|
| Longitudinal Education Outcomes (LEO) | Longitudinal Education Outcomes (LEO) | Cross-domain record linkage | Cross-domain record linkage | True |
| Education and Child Health Insights from Linked Data (ECHILD) | Education and Child Health Insights from Linked Data (ECHILD) | Cross-domain record linkage | Cross-domain record linkage | True |
| Linked Census, HES and Mortality Data | Linked Census, HES and Mortality Data | Cross-domain record linkage | Cross-domain record linkage | True |
| GRading and Admissions Data England (GRADE) | GRading and Admissions Data England (GRADE) | Within-domain record linkage | Within-domain record linkage | True |
| MoJ Data First Crown Court Defendant Case Level | MoJ Data First | Within-domain record linkage | Within-domain record linkage | True |
| Administrative Data \| Agricultural Research Collection (AD\|ARC) | Administrative Data \| Agricultural Research Collection (AD\|ARC) | Cross-domain record linkage | Cross-domain record linkage | True |
| Growing Up in England Wave 1 (GUIE) | Growing Up in England (GUIE) | Cross-domain record linkage | Cross-domain record linkage | True |
| Annual Survey of Hours and Earnings Longitudinal | Annual Survey of Hours and Earnings Longitudinal | Within-domain record linkage | Within-domain record linkage | True |
| Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment | Annual Survey of Hours and Earnings linked to PAYE and Self-Assessment | Within-domain record linkage | Within-domain record linkage | True |
| Annual Survey of Hours and Earnings linked to Census 2011 | Annual Survey of Hours and Earnings linked to Census 2011 | Cross-domain record linkage | Cross-domain record linkage | True |
| Annual Business Survey (ABS) |  | No record linkage | No record linkage | True |

## Dataset Collection Method

Collection method is a provenance fact, by design, single-label. Each dataset gets exactly one of survey or administrative. Survey means collected through a survey instrument or survey return, including employer survey forms. Administrative means derived from administrative, register, service, or operational records.


ASHE is survey by design even though sampled from PAYE administrative records, because it is collected through employer survey returns.


| Project collection-method set | Count |
|---|---:|
| survey | 674 |
| administrative | 325 |
| survey; administrative | 289 |
| (none matched) | 21 |

## Dataset Temporal Structure

Temporal structure is a time-structure fact, single-label, classified by the dataset producer's design, weighting, and release for use. Each dataset gets exactly one of cross-sectional or longitudinal. Longitudinal means the released dataset is designed and weighted to follow the same units (persons, households, firms, or equivalent records) over time. Cross-sectional means a point-in-time release or repeated fresh-extract release.


Classify by producer design, weighting, and release, not by the raw sampling frame or by what could be constructed from the data. A dataset whose sampling frame permits longitudinal linkage but which is produced and weighted cross-sectionally is cross-sectional; a longitudinal version exists as a distinct entry only when the longitudinal construction and weighting has actually been done.


Aggregate indicators and national or area-level time-series outputs such as CPI, GVA, PPI, and Capital Stock are not longitudinal under this facet because they follow no units. They are time series, but not unit panels, and are classified as cross-sectional point-in-time aggregate releases.


The former cohort category is retired because it conflated collection method with temporal structure and misnamed longitudinality. Business panels are longitudinal but are not cohort studies.


| Project temporal-structure set | Count |
|---|---:|
| cross-sectional | 704 |
| longitudinal | 345 |
| cross-sectional; longitudinal | 239 |
| (none matched) | 21 |

### Temporal distribution delta from 0.4.0

| Project temporal-structure set | 0.4.0 | 0.4.1 | Delta |
|---|---|---|---|
| cross-sectional | 485 | 704 | +219 |
| longitudinal | 387 | 345 | -42 |
| cross-sectional; longitudinal | 378 | 239 | -139 |
| (none matched) | 22 | 21 | -1 |

### Reclassified aggregate-indicator datasets

| Dataset | Register spellings | 0.4.0 temporal_structure | 0.4.1 temporal_structure | Current | Pass |
|---|---|---|---|---|---|
| UK Gross Value Added | UK Gross Value Added | longitudinal | cross-sectional | cross-sectional | True |
| Consumer Prices Index | Consumer Prices Index; Retail Price Index | longitudinal | cross-sectional | cross-sectional | True |
| Producer Price Index | Producer Price Index | longitudinal | cross-sectional | cross-sectional | True |
| Capital Stock Dataset | Capital Stock Dataset; Capital Stock 2014; Capital Stock; Capital Stocks | longitudinal | cross-sectional | cross-sectional | True |

### Time-series-not-unit-panel audit

No additional longitudinal dataset records with time-series/index/aggregate cues were found.

### Unchanged temporal edge checks

| Dataset | Current temporal_structure | Expected | Pass |
|---|---|---|---|
| ONS Longitudinal Study (LS) | longitudinal | longitudinal | True |
| Public Health Research Database | longitudinal | longitudinal | True |
| Longitudinal Education Outcomes (LEO) | longitudinal | longitudinal | True |
| Education and Child Health Insights from Linked Data (ECHILD) | longitudinal | longitudinal | True |
| Understanding Society | longitudinal | longitudinal | True |
| Annual Survey of Hours and Earnings Longitudinal | longitudinal | longitudinal | True |
| Decision Maker Panel | longitudinal | longitudinal | True |
| Labour Force Survey Longitudinal | longitudinal | longitudinal | True |
| Annual Survey of Hours and Earnings (ASHE) | cross-sectional | cross-sectional | True |

Full migration review table: `analysis/outputs_deterministic_rc2/quality/dataset_collection_split_review.csv`. It lists every dataset with `legacy_collection_type`, `collection_method`, `temporal_structure`, and `temporal_is_new_decision`, now refreshed under reference 0.4.1.

## Dataset unit of observation

The unit is the unit the dataset is structured or collected around, not the unit a project analyses, and the rule is applied symmetrically. Each dataset gets exactly one of individual, household, business, or area.


Aggregate indicators and national time-series outputs (CPI, GVA, PPI, and Capital Stock) do not fit the unit-based deterministic facets cleanly. They have no unit of observation in the four-value vocabulary, so they are mapped to the closest available value (area for CPI/GVA, business for PPI/Capital Stock) and classified as cross-sectional because they are not unit-following panels. This is a known boundary of the unit-based schema rather than a new aggregate/time-series facet value for a small number of cases.


Census appears in three facets as survey, individual, and Migration & Demographics as a linkage component. These rulings are mutually consistent: Census is a population survey enumerating individuals whose substantive object is demography.


| Project unit set | Count |
|---|---:|
| individual | 706 |
| business | 240 |
| individual; business | 165 |
| individual; household | 66 |
| household | 45 |
| individual; household; business | 33 |
| (none matched) | 21 |
| household; business | 12 |
| individual; household; business; area | 6 |
| area | 3 |
| individual; business; area | 3 |
| household; area | 3 |
| business; area | 2 |
| individual; area | 2 |
| household; business; area | 1 |
| individual; household; area | 1 |

### Dataset edge checks

| Dataset | Method | Temporal | Unit | Expected | Pass |
|---|---|---|---|---|---|
| Census | survey | cross-sectional | individual | survey / cross-sectional / individual | True |
| Understanding Society | survey | longitudinal | household | survey / longitudinal / household | True |
| Millennium Cohort Study | survey | longitudinal | individual | survey / longitudinal / individual | True |
| ONS Longitudinal Study (LS) | survey | longitudinal | individual | administrative / longitudinal / individual | False |
| Annual Survey of Hours and Earnings (ASHE) | survey | cross-sectional | individual | survey / cross-sectional / individual | True |
| Annual Survey of Hours and Earnings Longitudinal | survey | longitudinal | individual | survey / longitudinal / individual | True |
| Longitudinal Education Outcomes (LEO) | administrative | longitudinal | individual | administrative / longitudinal / individual | True |
| Education and Child Health Insights from Linked Data (ECHILD) | administrative | longitudinal | individual | administrative / longitudinal / individual | True |
| Linked Census, HES and Mortality Data | survey | longitudinal | individual | administrative / longitudinal / individual | False |
| Public Health Research Database | administrative | longitudinal | individual | administrative / longitudinal / individual | True |
| Death Registrations | administrative | cross-sectional | individual | administrative / cross-sectional / individual | True |
| Birth Registrations in England and Wales | administrative | cross-sectional | individual | administrative / cross-sectional / individual | True |
| Annual Business Survey (ABS) | survey | cross-sectional | business | survey / cross-sectional / business | True |
| Annual Population Survey (APS) | survey | cross-sectional | individual | survey / cross-sectional / individual | True |
| Labour Force Survey | survey | cross-sectional | individual | survey / cross-sectional / individual | True |
| Labour Force Survey Longitudinal | survey | longitudinal | individual | survey / longitudinal / individual | True |
| Decision Maker Panel | survey | longitudinal | business | survey / longitudinal / business | True |
| Longitudinal Small Business Survey (LSBS) | survey | longitudinal | business | survey / longitudinal / business | True |
| UK Gross Value Added | administrative | cross-sectional | area | administrative / cross-sectional / area | True |
| Consumer Prices Index | survey | cross-sectional | area | administrative / cross-sectional / area | False |
| Producer Price Index | survey | cross-sectional | business | survey / cross-sectional / business | True |
| Capital Stock Dataset | administrative | cross-sectional | business | administrative / cross-sectional / business | True |
| Capital Stock 2014 | administrative | cross-sectional | business | administrative / cross-sectional / business | True |

## Researcher sector

Researcher sector is structural/legal status, not behaviour. Classify each organisation, then derive a project's researcher_sectors as the union of its researchers' organisation sectors.


| Project researcher-sector set | Count |
|---|---:|
| academic | 809 |
| commercial | 115 |
| third-sector | 104 |
| government | 98 |
| academic; government | 64 |
| academic; third-sector | 52 |
| unclassified | 16 |
| academic; commercial | 14 |
| government; commercial | 10 |
| academic; government; third-sector | 7 |
| academic; government; commercial | 5 |
| government; third-sector | 4 |
| third-sector; commercial | 3 |
| government; third-sector; commercial | 2 |
| academic; government; third-sector; commercial | 1 |
| academic; government; unclassified | 1 |
| commercial; unclassified | 1 |
| academic; third-sector; commercial | 1 |
| academic; third-sector; unclassified | 1 |
| academic; unclassified | 1 |

### Sector edge checks

| Organisation | Sectors | Expected | Pass |
|---|---|---|---|
| Nesta | third-sector | third-sector | True |
| Institute for Fiscal Studies | third-sector | third-sector | True |
| Bank of England | government | government | True |
| Office for National Statistics | government | government | True |
| Frontier Economics Ltd | commercial | commercial | True |
| University College London | academic | academic | True |
| AQA Education | third-sector | third-sector | True |
| Tech City UK | government | government | True |
| Office of the Victims' Commissioner for England and Wales | government | government | True |
| Chartered Institute of Personnel and Development | third-sector | third-sector | True |
| Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR) | unclassified | unclassified | True |
| Equality and Human Rights Commission (EHRC) | government | government | True |

## Coverage and unmatched tail

Dataset reference coverage: 3,229/3,337 project-dataset mentions (96.8%), 239/339 unique canonical datasets.

Organisation reference coverage: 1,831/1,842 project-organisation mentions (99.4%), 275/286 unique canonical organisations.

Largest unmatched datasets:

| Dataset | Mentions |
|---|---:|
| Research and Development Expenditures and Subsidies | 3 |
| Firm Productivity | 3 |
| Employment Creation and Survival | 3 |
| Foreign Direct Investment Index | 2 |
| Northern Ireland Annual Business Inquiry (NIABI) | 2 |
| Financial Assets and Liabilities Survey | 1 |
| Investment in Intangible Assets | 1 |
| Small Business Survey Longitudinal | 1 |
| Designs and Trade Marks Office for National Statistics / | 1 |
| Valuation data of Scottish properties | 1 |
| Linked Inter-Departmental Business Register and Valuation Office Agency | 1 |
| Quarterly Survey of Financial Assets and Liabilities | 1 |
| Linked Director's mortality | 1 |
| Linked Census and death occurrences Office for National Statistics / | 1 |
| Wealth and Assets Survey Great Britain | 1 |
| Trade in Services | 1 |
| State-funded schools inspections and outcomes | 1 |
| General Lifestyle Survey to 2010 | 1 |
| Department for Business | 1 |
| Energy and Industrial Strategy: Community Innovation Survey | 1 |
| Provisional Monthly Extracts England and Wales | 1 |
| Annual Acquisition and Disposals of Capital Assets Survey | 1 |
| Workplace Employee Relations Survey | 1 |
| Secure Census 2011 Scotland | 1 |
| Northern Ireland School Leavers Survey | 1 |

Largest unmatched organisations:

| Organisation | Mentions |
|---|---:|
| Independent Researcher | 1 |
| OREC | 1 |
| Reading University Ministry of National Education, Republic of Turkiye | 1 |
| York Univeristy | 1 |
| York University | 1 |
| Calver Pang | 1 |
| Oxford Brookes University | 1 |
| Manchester University | 1 |
| Alison Sizer, University College London | 1 |
| Sheffield University | 1 |
| Anna Freud Centre | 1 |

### Deliberate non-mappings and manual-review dataset names

| Raw entry | Action | Rationale |
|---|---|---|
| Research and Development Expenditures and Subsidies | review_manually | Likely incomplete or derived. It could relate to BERD plus subsidy/admin data, but should not be auto-mapped without source context. |
| Firm Productivity | review_manually | Looks like an analytical output or derived measure rather than a dataset title. Do not auto-map to ABS/ABI/IDBR without source context. |
| Employment Creation and Survival | review_manually | Looks like a derived business-demography measure rather than a dataset title. Do not auto-map to BSD/LBD/IDBR without source context. |
| Foreign Direct Investment Index | review_manually | Index wording suggests an output/indicator rather than the source FDI survey. Do not auto-map unless project text confirms it means the Annual Foreign Direct Investment Survey. |
| Racial Disparity Audit | do_not_map_as_dataset | Not a single dataset; closer to a government audit/dashboard/publication drawing on multiple sources. Needs the underlying dataset title. |
| Bespoke National Council for Voluntary Organisations | do_not_map_as_dataset | Incomplete title naming an organisation/source rather than a dataset. Needs the actual NCVO dataset name. |

## Spot-check sample

| Record ID | Title | Record linkage | Products | Methods | Temporal | Units | Sectors |
|---|---|---|---|---|---|---|---|
| 2019/024 | The Right to Buy: Migration and Gentrification | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/006 | Parental separation and educational inequality: any evidence for growing disadvantage or 'diverging  | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/027 | COVID-19 Infection Survey | Cross-domain record linkage | COVID-19 Infection Survey linked to Mortality - England and Wales ONS; Covid-19 Infection Survey linked with VOA and EPC | survey; administrative | cross-sectional; longitudinal | individual | academic; government; commercial |
| 2020/030/b | Occupational mobility: evidence from England and Wales | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/046 | Wage and employment dynamics | Cross-domain record linkage | Annual Survey of Hours and Earnings linked to Census 2011 | survey; administrative | cross-sectional; longitudinal | individual; business | academic; government |
| 2020/050 | Inequalities in the 21st Century | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | third-sector |
| 2020/074 | Health of Older People in Places : an asset for economic and social improvement for all | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/077 | Understanding the social determinants of place of death in older adults | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/078 | Addressing Health: Health and mortality of postal workers in England and Wales | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/083 | Religion and Labour Market Outcomes in England and Wales: 1991-2011 | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/092 | Understanding Recent Fertility in the UK and Improving Methodologies for Fertility Forecasting | Cross-domain record linkage | ONS Longitudinal Study | survey | longitudinal | individual | academic |
| 2020/095 | The effect of policy uncertainty on firm productivity and trade | Within-domain record linkage | Linked Trade-in-Goods/IDBR | survey; administrative | cross-sectional; longitudinal | individual; business | academic |
| 2020/104 | Analysis of the COVID-19 School Infection Survey to support government decision making during the pa | Within-domain record linkage | Covid-19 Schools Infection Survey linked with Test and Trace | survey | longitudinal | individual | academic; government |
| 2020/120 | COVID-19 Local Area Profiles | Cross-domain record linkage | Linked Census, HES and Mortality Data | survey; administrative | cross-sectional; longitudinal | individual; business | academic |
| 2021/012 | Investigating epidemiological insights for the COVID19 infection across the UK | Cross-domain record linkage | Linked Census, HES and Mortality Data | survey; administrative | cross-sectional; longitudinal | individual; business | academic; government |

## Judgement calls

- Base `ASHE` is cross-sectional because ONS weights and releases it cross-sectionally despite the recurring NINo sampling frame. `Annual Survey of Hours and Earnings Longitudinal` is longitudinal because the longitudinal construction and weighting have actually been applied.
- `AD|ARC` is labelled administrative/business for dataset facets. The product links individual and farm-level data, but the farm or agricultural holding is treated as the closest available structural unit.
- `Data First` is labelled administrative/individual for dataset facets. The extracts include case and journey structures, but the deterministic single-label unit is person-defendant/offender oriented.
- `Consumer Prices Index` is labelled administrative/area because the allowed unit vocabulary has no product or price-observation unit. Its temporal structure is cross-sectional because an aggregate index is a time series, not a unit panel.

### Temporal calls flagged for human review

| Dataset | Review note |
|---|---|
| ONS Longitudinal Study (LS) | Mixed Census/vital-event lineage; treated as administrative plus longitudinal because the released product follows linked persons over time. |
| Data First | Family spans case extracts and journey/linkage products; treated as longitudinal because the public-register family includes person/case journeys. |
| AD\|ARC | Agricultural collection spans linked administrative phases; temporal call should be reviewed against detailed product documentation. |
| Annual Respondents Database | Repeated annual business survey microdata may support linked firms, but treated as cross-sectional unless a panel design is explicit. |
| Business Insights and Conditions Survey (BICS) | Repeated-wave business survey; treated as cross-sectional unless a panel design is explicit. |
| Annual Gas and Electricity Consumption at Meter Level | Same meters/properties may recur, but treated as cross-sectional annual administrative extracts. |
| UK Gross Value Added | Aggregate indicator/time-series output; classified cross-sectional because it follows no units over time. |
| Workplace Employment Relations Survey | Repeated survey with some panel history; treated as cross-sectional at the reference-record level. |
| COVID-19 | CIS-linked products are longitudinal; cross-sectional COVID social surveys have explicit separate records. |
| Public Health Research Database | Health administrative records can be episode-based; treated as longitudinal because the product supports linked person histories. |
| Consumer Prices Index | Price-index time series has no perfect unit vocabulary fit; classified cross-sectional because it follows no units over time. |
| Producer Price Index | Price-index survey time series has no perfect unit vocabulary fit; classified cross-sectional because it follows no units over time. |
| Capital Stock Dataset | Economic stock time-series output; classified cross-sectional because it follows no units over time. |

## Verification summary

- Cross-table validation passed during reference load: every linked product resolves to a dataset facet record.
- `PROMPT_VERSION` is not read or changed by this deterministic derivation; no LLM classification is run.
- The rc1 output prefixes are checked below from git status.
- Reference version is `0.4.6`.

## Manifests and rc1

Deterministic output manifest: `analysis/outputs_deterministic_rc2/manifest.json`.

Quality output manifest: `analysis/outputs_deterministic_rc2/quality/manifest.json`.

Report output manifest: `analysis/outputs_refresh/20260601/manifest.json`.

No git status entries under rc1 output prefixes were present after this run.
