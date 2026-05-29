# v4 rc1 Intra-vs-Inter Comparison Decomposition

This report compares two disagreement baselines for the same full DEA register and the same rc1 dictionary. The intra-4.8 comparison measures Opus 4.8 run against itself on identical inputs. The inter-model comparison measures Opus 4.8 against Opus 4.6 on the same inputs.

## 1. Headline Decomposition

| Comparison | Overall agreement | Domains | Linkage | Purpose | Tags |
| --- | --- | --- | --- | --- | --- |
| Intra-4.8 (run 1 vs run 2) | 77.0% | 91.3% | 93.1% | 91.7% | 98.3% |
| Inter-model (4.8 vs 4.6) | 55.6% | 79.0% | 86.3% | 83.5% | 96.1% |
| Difference (inter - intra disagreement) | +21.4 pp | +12.3 pp | +6.8 pp | +8.3 pp | +2.1 pp |

The difference row reports excess inter-model disagreement in percentage points, calculated as inter-model disagreement minus intra-4.8 disagreement.

## 2. Interpretation Framing

Intra-4.8 disagreement reflects stochastic variation in the model's output on identical inputs. Inter-model disagreement reflects stochastic variation plus differences in how Opus 4.8 and Opus 4.6 read the prompt and apply the dictionary. The difference between inter-model and intra-model disagreement is an approximate lower bound on the model-attributable portion. It is approximate because the two sources are not strictly additive; both involve sampling.

## 3. Per-Field Rates

| Comparison | Overall agreement | Domains | Linkage | Purpose | Tags |
| --- | --- | --- | --- | --- | --- |
| Intra-4.8 (run 1 vs run 2) | 76.9654 | 91.2736 | 93.0818 | 91.7453 | 98.2704 |
| Inter-model (4.8 vs 4.6) | 55.5818 | 79.0094 | 86.3208 | 83.4906 | 96.1478 |
| Excess inter-model disagreement, percentage points | 21.3836 | 12.2642 | 6.7610 | 8.2547 | 2.1226 |

The numeric rates table is also saved as `per_layer_rates.csv`.

## 4. Pattern Overlap

| Measure | Value |
| --- | --- |
| Projects unstable intra-4.8 | 293 |
| Projects disagreed inter-model | 565 |
| Overlap count | 206 |
| Union count | 652 |
| Jaccard index | 0.3160 |

The project-level overlap table is saved as `pattern_overlap.csv`.

## 5. Per-Field Examples

### Domains

| Bucket | Example titles |
| --- | --- |
| Disagreed inter-model but agreed intra-4.8 | The fall of the labour share and rise of the superstar region - Labour share and earning in UK regions; Improving Regional Economic Indicators Regional Consumer Prices; Research on homeless mortality among St Mungo's clients; Spatial sorting in housing and employment: impact of public investments, planning decisions, housing subsidies, and business rates; Subjective wellbeing impacts of debt and debt-related factors |
| Disagreed intra-4.8 but agreed inter-model | Economic environment and child development; Digital skills in medium and associate professional job roles: An analysis of institutional data from English apprenticeship standard; Health of Older People in Places : an asset for economic and social improvement for all; Economic scarring from the COVID-19 induced crisis: monitoring inequality in economic and education outcomes. Enhancing impact of UKRI social mobility research with TRE data to inform national response; Analysis of occupation and Covid-19 as part of PROTECT project using ONS Infection survey |
| Disagreed in both | UK coastal tourism: efficiency and revival; Identifying flare ups of the COVID-19 infection across the UK; Local wellbeing impacts of the Grosvenor Square Gardens Project; UK Local Employment Multipliers; Effect of 9/11 on Muslim Marriage Market |

### Linkage

| Bucket | Example titles |
| --- | --- |
| Disagreed inter-model but agreed intra-4.8 | Thriving Places index indicators of wellbeing at local authority level; Class in UK creative industries: Beyond participation; Diversity in the Creative Industries; Homeownership of the young; The impact of government expenditure on employment and wages: evidence from firm-level data for the UK |
| Disagreed intra-4.8 but agreed inter-model | Understanding the uptake and use of the Northern Ireland Concessionary Fares Scheme for the population aged 60 and over; Analysis of the clustering of UK digital sectors; The Resilience of British Cities; Mid Term Evaluation of the Wales Business Fund; Wellbeing in different occupations |
| Disagreed in both | The determinants of performance-pay utilisation by firms and its consequences for firm behaviour, performance, and employee outcomes; Controlling COVID-19 through enhanced population surveillance and intervention : a platform approach; Local Institutions, Productivity, Sustainability and Inclusivity Trade-offs; Director relationships and UK firm performance; Occupational segregation by ethnicity: the impact of regional job availability on occupational choice |

### Purpose

| Bucket | Example titles |
| --- | --- |
| Disagreed inter-model but agreed intra-4.8 | The contribution of digital economy in Wales, a measurement by an information and communications satellite account; Understanding saving behaviour in the UK; Homeownership of the young; The Right to Buy: Migration and Gentrification; Parental separation and educational inequality: any evidence for growing disadvantage or 'diverging destinies' across three recent cohorts? |
| Disagreed intra-4.8 but agreed inter-model | Wage and employment dynamics; Wellbeing in different occupations; How is COVID-19 impacting women and men's working lives in the UK?; Location decisions in response to school quality over the lifecycle; Identifying effective post-16 education pathways to Level 2 and Level 3 achievement, for learners with a 3 or below in Maths and/or English at KS4 |
| Disagreed in both | Modelling the regional implications of COVID-19 using the Enterprise Research Centre's longitudinal firm-level dataset based on the Business Structure Database; COVID-19 Infection Survey; IFS Deaton Review: Geographic Inequalities and spatial mobility; Impact of migration on Scotland versus the UK; UK Local Employment Multipliers |

### Tags

| Bucket | Example titles |
| --- | --- |
| Disagreed inter-model but agreed intra-4.8 | Understanding the uptake and use of the Northern Ireland Concessionary Fares Scheme for the population aged 60 and over; Migration Observatory analysis of EU and non-EU migration in the UK; Parental separation and educational inequality: any evidence for growing disadvantage or 'diverging destinies' across three recent cohorts?; Contextualised Admissions and University Choice; Health of Older People in Places : an asset for economic and social improvement for all |
| Disagreed intra-4.8 but agreed inter-model | Homeownership of the young; Inequalities in the 21st Century – Chapter on Labour Market Inequality; Forecasting future socioeconomic inequalities in longevity: the impact of lifestyle "epidemics"; Addressing inclusivity in the spatial and social impacts of COVID-19 on the self-employed in the UK; The link between characteristics of school pupils and labour market outcomes |
| Disagreed in both | Education and Identity; Inequalities in the 21st Century: Transfers, tax and tax credits; Classifying the older population: understanding the geography of opportunities and challenges in England; Exploring Fertility Differentials in the 2011 Census; The inequalities in the patterns of needs for carers and cared for people receiving support from local authorities across Wales |

