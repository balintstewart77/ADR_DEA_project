# rc2 deterministic reference report

## Scope

Reference version `0.1.0` was applied to 1,272 cleaned DEA register records. Output CSV: `analysis/outputs_deterministic_rc2/register_properties.csv`.

This run is deterministic and uses no LLM calls.

## Canonical keys

Datasets are parsed with `dashboard.dataset_normalisation.parse_datasets`, which applies `normalise_dataset_name` to each parsed dataset entry. Lookup first uses that exact canonical dataset string, then falls back to `dataset_family_for` where the normaliser defines a reviewed family key.

Researcher organisations are parsed with `dashboard.institution_normalisation.parse_institutions` and matched on the parser's canonical `institution` string.

## Record linkage

Record linkage is derived from linked-product component domains. A product with components from no recognised linked product is "No record linkage"; a product whose component-domain union contains one domain is within-domain; a product whose union contains two or more domains is cross-domain. linkage_span is derived from component_domains and is never stored in this reference.


A linked component contributes the "Migration & Demographics" domain only when the dataset's substantive origin is population or demography, such as Census as a population source, not when a dataset merely carries demographic fields. NPD ethnicity or free-school-meal attributes are attributes of education records, not a separate demographic component.


| Record linkage span | Count |
|---|---:|
| No record linkage | 980 |
| Within-domain record linkage | 88 |
| Cross-domain record linkage | 204 |

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

## Dataset collection type

Primary type by design, single-label. Each dataset gets exactly one of survey, cohort, or administrative. Cohort means any longitudinal study following the same units over time, including household and business panels. Administrative includes vital-events and registry data such as births and deaths.


Single-label classification suppresses dual-nature data. Census is filed as survey by design though administratively used; a longitudinal survey is filed under cohort, losing its survey aspect.


| Project collection-type set | Count |
|---|---:|
| survey | 512 |
| administrative | 319 |
| survey; administrative | 236 |
| cohort | 74 |
| survey; cohort | 56 |
| survey; cohort; administrative | 45 |
| (none matched) | 24 |
| cohort; administrative | 6 |

## Dataset unit of observation

The unit is the unit the dataset is structured or collected around, not the unit a project analyses, and the rule is applied symmetrically. Each dataset gets exactly one of individual, household, business, or area.


Census appears in three facets as survey, individual, and Migration & Demographics as a linkage component. These rulings are mutually consistent: Census is a population survey enumerating individuals whose substantive object is demography.


| Project unit set | Count |
|---|---:|
| individual | 681 |
| business | 232 |
| individual; business | 161 |
| individual; household | 63 |
| household | 45 |
| individual; household; business | 33 |
| (none matched) | 24 |
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

| Dataset | Collection | Unit | Expected | Pass |
|---|---|---|---|---|
| Census | survey | individual | survey / individual | True |
| Understanding Society | cohort | household | cohort / household | True |
| Annual Survey of Hours and Earnings (ASHE) | survey | individual | survey / individual | True |
| Longitudinal Education Outcomes (LEO) | administrative | individual | administrative / individual | True |
| Education and Child Health Insights from Linked Data (ECHILD) | administrative | individual | administrative / individual | True |
| Linked Census, HES and Mortality Data | administrative | individual | administrative / individual | True |
| Death Registrations | administrative | individual | administrative / individual | True |
| Birth Registrations in England and Wales | administrative | individual | administrative / individual | True |
| Decision Maker Panel | cohort | business | cohort / business | True |
| Longitudinal Small Business Survey (LSBS) | cohort | business | cohort / business | True |

## Researcher sector

Researcher sector is structural/legal status, not behaviour. Classify each organisation, then derive a project's researcher_sectors as the union of its researchers' organisation sectors.


| Project researcher-sector set | Count |
|---|---:|
| academic | 741 |
| commercial | 98 |
| government | 81 |
| unclassified | 80 |
| third-sector | 79 |
| academic; government | 52 |
| academic; third-sector | 45 |
| academic; unclassified | 35 |
| academic; commercial | 11 |
| commercial; unclassified | 8 |
| government; commercial | 7 |
| government; unclassified | 6 |
| academic; government; unclassified | 6 |
| academic; government; third-sector | 5 |
| government; third-sector | 3 |
| academic; government; commercial | 3 |
| academic; commercial; unclassified | 2 |
| academic; government; third-sector; unclassified | 2 |
| government; third-sector; commercial | 2 |
| academic; government; third-sector; commercial; unclassified | 1 |
| academic; government; commercial; unclassified | 1 |
| government; commercial; unclassified | 1 |
| third-sector; unclassified | 1 |
| third-sector; commercial; unclassified | 1 |
| third-sector; commercial | 1 |

### Sector edge checks

| Organisation | Sectors | Expected | Pass |
|---|---|---|---|
| Nesta | third-sector | third-sector | True |
| Institute for Fiscal Studies | third-sector | third-sector | True |
| Bank of England | government | government | True |
| Office for National Statistics | government | government | True |
| Frontier Economics Ltd | commercial | commercial | True |
| University College London | academic | academic | True |
| Tech City UK | government | government | True |
| Office of the Victims' Commissioner for England and Wales | government | government | True |
| Chartered Institute of Personnel and Development | third-sector | third-sector | True |
| Centre for Healthcare Evaluation, Device Assessment, and Research (CEDAR) | unclassified | unclassified | True |
| Equality and Human Rights Commission (EHRC) | government | government | True |

## Coverage and unmatched tail

Dataset reference coverage: 3,137/3,250 project-dataset mentions (96.5%), 229/327 unique canonical datasets.

Organisation reference coverage: 1,658/1,805 project-organisation mentions (91.9%), 173/320 unique canonical organisations.

Largest unmatched datasets:

| Dataset | Mentions |
|---|---:|
| Research and Development Expenditures and Subsidies | 3 |
| Firm Productivity | 3 |
| Employment Creation and Survival | 3 |
| Foreign Direct Investment Index | 2 |
| EOL | 2 |
| Childcare and Early Years Survey of Parents | 2 |
| Expenditure and Food Survey | 2 |
| International Passenger Survey | 2 |
| Innovation Panel | 2 |
| The Second Longitudinal Study of Young People in England | 2 |
| Telephone-Operated Crime Survey for England and Wales | 2 |
| Children of the 2020s Longitudinal Study | 2 |
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
| Capital Stock 2014 | 1 |
| Trade in Services | 1 |
| State-funded schools inspections and outcomes | 1 |

Largest unmatched organisations:

| Organisation | Mentions |
|---|---:|
| University of Bournemouth | 1 |
| Knowledge Transfer Network | 1 |
| Methods Analytics | 1 |
| Nuffield Department of Medicine | 1 |
| Queen's University Belfast Management, School | 1 |
| Cancer Research UK | 1 |
| Be the Business | 1 |
| National Institute of Social and Economic Research | 1 |
| Joint Biosecurity, Centre | 1 |
| Birkbeck, University of London | 1 |
| British Psychological Society | 1 |
| Nuffield Foundation | 1 |
| Institue for Employment Studies | 1 |
| Saga City Research | 1 |
| Free University of Bozen-Bolzano | 1 |
| Hackney Council | 1 |
| Cranfield School of Management | 1 |
| Warwick Economics and Development | 1 |
| What Works for Children's Social Care | 1 |
| University of Middlesex | 1 |
| London Borough of Redbridge | 1 |
| UCL Institute of Epidemiology and Health | 1 |
| UCL Institute for Global Health | 1 |
| UCL Institute of Health Informatics | 1 |
| WPI Economics | 1 |

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

| Record ID | Title | Record linkage | Products | Dataset types | Units | Sectors |
|---|---|---|---|---|---|---|
| 2020/046 | Wage and employment dynamics | Cross-domain record linkage | Annual Survey of Hours and Earnings linked to Census 2011 | survey; administrative | individual; business | academic; government |
| 2021/035 | Shaping, testing and demonstrating the value of the Growing up in England wave 1 dataset: Roma, Gyps | Cross-domain record linkage | Growing Up in England (GUIE) | administrative | individual | academic |
| 2021/037 | Ethnicity and COVID-19: investigating the determinants of excess risk | Cross-domain record linkage | Linked Census, HES and Mortality Data | survey; administrative | individual | academic; government |
| 2021/038 | Using linked Magistrates and Crown Court data to explore defendant appearance over time: specialisat | Within-domain record linkage | MoJ Data First | administrative | individual | academic |
| 2021/039 | A ticking social timebomb. An investigation into racial bias in court case outcomes in England and W | Within-domain record linkage | MoJ Data First | administrative | individual | academic |
| 2021/040 | Understanding the nature, extent and outcomes of serious and organised crime cases heard before the  | Within-domain record linkage | MoJ Data First | administrative | individual | academic |
| 2021/041 | Ethnic inequalities in the Criminal Justice System | Within-domain record linkage | MoJ Data First | administrative | individual | academic |
| 2021/047 | Exploring Child Sexual Exploitation Networks In The UK | Within-domain record linkage | MoJ Data First | administrative | individual | academic |
| 2021/074 | Identifying effective post-16 education pathways to Level 2 and Level 3 achievement, for learners wi | Cross-domain record linkage | Longitudinal Education Outcomes (LEO) | administrative | individual | academic; commercial |
| 2021/075 | Journey through education: How does the quality of schooling affect long-term labour market outcomes | Cross-domain record linkage | Longitudinal Education Outcomes (LEO) | administrative | individual | government |
| 2021/080 | Parenting Style, Parental Investment, and the Socioeconomic Environment | Within-domain record linkage | Annual Survey of Hours and Earnings Longitudinal | survey | individual | unclassified |
| 2021/107 | Assessing Equality Pay Gaps in Northern Ireland | Cross-domain record linkage | Earnings and Employees Study (EES) 2011 - Northern Ireland | survey | individual | academic; government |
| 2021/076 | Education & Social Mobility: Understanding Earnings Outcomes for Free School Meals Students | Cross-domain record linkage | Longitudinal Education Outcomes (LEO) | administrative | individual | government |
| 2021/094 | The impact of COVID-19 on unemployment and earnings inequality | Within-domain record linkage | Annual Survey of Hours and Earnings Longitudinal | survey | individual | academic |
| 2021/147 | Intergenerational Inequalities: sources across jobs and labour markets | Cross-domain record linkage | Annual Survey of Hours and Earnings Longitudinal; Annual Survey of Hours and Earnings linked to Census 2011 | survey; administrative | individual; business | academic; third-sector |

## Judgement calls

- `AD|ARC` is labelled administrative/business for dataset facets. The product links individual and farm-level data, but the farm or agricultural holding is treated as the closest available structural unit.
- `Data First` is labelled administrative/individual for dataset facets. The extracts include case and journey structures, but the deterministic single-label unit is person-defendant/offender oriented.
- `Consumer Prices Index` is labelled administrative/area because the allowed unit vocabulary has no product or price-observation unit.

## Manifests and rc1

Deterministic output manifest: `analysis/outputs_deterministic_rc2/manifest.json`.

Quality output manifest: `analysis/outputs_deterministic_rc2/quality/manifest.json`.

Report output manifest: `analysis/outputs/manifest.json`.

No git status entries under rc1 output prefixes were present after this run.
