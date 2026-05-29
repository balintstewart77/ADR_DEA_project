# Opus 4.8 vs Opus 4.6 rc1 Comparison Summary

This report compares the full-register v4 rc1 classifications side by side. It reports label agreement and disagreement patterns only; it does not rank the models.

## Run Counts

| Run | Projects classified |
| --- | --- |
| Opus 4.8 | 1272 |
| Opus 4.6 | 1272 |

Project ID sets match: yes

## Agreement Rates

Overall agreement: 55.6% (707 of 1,272 projects agreed on all four label fields).

| Field | Agreement rate | Agreed projects | Compared projects |
| --- | --- | --- | --- |
| substantive_domains | 79.0% | 1005 | 1272 |
| linkage_mode | 86.3% | 1098 | 1272 |
| analytical_purpose | 83.5% | 1062 | 1272 |
| cross_cutting_tags | 96.1% | 1223 | 1272 |

## Disagreement Patterns by Category

### substantive_domains

| 4.8 label set | 4.6 label set | Projects |
| --- | --- | --- |
| Education & Skills; Labour Market & Employment | Education & Skills | 20 |
| Labour Market & Employment | Business & Productivity; Labour Market & Employment | 11 |
| Business & Productivity; Labour Market & Employment | Business & Productivity | 9 |
| Labour Market & Employment | Education & Skills; Labour Market & Employment | 9 |
| Business & Productivity | Business & Productivity; Data Infrastructure & Methodology | 7 |
| Labour Market & Employment | Labour Market & Employment; Poverty, Wealth & Living Standards | 5 |
| Business & Productivity; Environment & Agriculture | Business & Productivity | 4 |
| Labour Market & Employment | Health & Social Care; Labour Market & Employment | 4 |
| Labour Market & Employment | Data Infrastructure & Methodology; Labour Market & Employment | 4 |
| Education & Skills | Education & Skills; Labour Market & Employment | 4 |
| COVID-19 & Pandemic; Health & Social Care | COVID-19 & Pandemic; Data Infrastructure & Methodology; Health & Social Care | 3 |
| Migration & Demographics | Data Infrastructure & Methodology; Migration & Demographics | 3 |
| Migration & Demographics | Health & Social Care | 3 |
| Health & Social Care | Data Infrastructure & Methodology; Health & Social Care | 3 |
| Labour Market & Employment; Poverty, Wealth & Living Standards | Poverty, Wealth & Living Standards | 3 |
| Labour Market & Employment; Migration & Demographics | Migration & Demographics | 3 |
| Business & Productivity | Business & Productivity; Public Finance & Taxation | 3 |
| Health & Social Care | Health & Social Care; Migration & Demographics | 3 |
| Labour Market & Employment; Poverty, Wealth & Living Standards | Labour Market & Employment | 3 |
| Labour Market & Employment | Labour Market & Employment; Migration & Demographics | 3 |
| Health & Social Care | Education & Skills; Health & Social Care | 3 |

### linkage_mode

| 4.8 label set | 4.6 label set | Projects |
| --- | --- | --- |
| Cross-Domain Linkage | Within-Domain Linkage | 62 |
| Within-Domain Linkage | Cross-Domain Linkage | 43 |
| Cross-Domain Linkage | Single-Dataset | 43 |
| Within-Domain Linkage | Single-Dataset | 13 |
| Single-Dataset | Cross-Domain Linkage | 10 |
| Single-Dataset | Within-Domain Linkage | 3 |

### analytical_purpose

| 4.8 label set | 4.6 label set | Projects |
| --- | --- | --- |
| Outcome Tracking | Descriptive Monitoring | 39 |
| Descriptive Monitoring | Outcome Tracking | 26 |
| Descriptive Monitoring | Methodological / Infrastructure Research | 14 |
| Outcome Tracking | Policy Evaluation / Impact Analysis | 13 |
| Descriptive Monitoring | Descriptive Monitoring; Methodological / Infrastructure Research | 8 |
| Life-Course / Trajectory Analysis | Outcome Tracking | 7 |
| Policy Evaluation / Impact Analysis | Outcome Tracking | 6 |
| Descriptive Monitoring; Methodological / Infrastructure Research | Methodological / Infrastructure Research | 5 |
| Outcome Tracking | Life-Course / Trajectory Analysis | 5 |
| Policy Evaluation / Impact Analysis | Descriptive Monitoring | 4 |
| Descriptive Monitoring | Life-Course / Trajectory Analysis | 4 |
| Life-Course / Trajectory Analysis | Life-Course / Trajectory Analysis; Outcome Tracking | 4 |
| Risk Prediction / Early Identification | Outcome Tracking | 4 |
| Life-Course / Trajectory Analysis; Outcome Tracking | Outcome Tracking | 4 |
| Descriptive Monitoring; Methodological / Infrastructure Research | Descriptive Monitoring | 3 |
| Risk Prediction / Early Identification | Methodological / Infrastructure Research; Risk Prediction / Early Identification | 3 |
| Life-Course / Trajectory Analysis; Service Interaction / Systems Analysis | Life-Course / Trajectory Analysis | 3 |
| Methodological / Infrastructure Research | Descriptive Monitoring | 3 |
| Policy Evaluation / Impact Analysis | Methodological / Infrastructure Research | 3 |
| Descriptive Monitoring | Unclear from Register Entry | 3 |
| Service Interaction / Systems Analysis | Life-Course / Trajectory Analysis; Service Interaction / Systems Analysis | 3 |
| Outcome Tracking | Descriptive Monitoring; Outcome Tracking | 3 |

### cross_cutting_tags

| 4.8 label set | 4.6 label set | Projects |
| --- | --- | --- |
| (none) | Demographic disparities / equity tag | 44 |
| Demographic disparities / equity tag | (none) | 5 |

## Tag-Specific Differences

| Tag | 4.8 only count | 4.8 only example titles | 4.6 only count | 4.6 only example titles |
| --- | --- | --- | --- | --- |
| Demographic disparities / equity tag | 5 | Classifying the older population: understanding the geography of opportunities and challenges in England; Analysis and modelling of age, period and cohort effects on smoking status and cigarette consumption for the population of Great Britain (1972-2014); Demographic and Economic Features of Households’ Division of Labour in the United Kingdom, 2004-2024; Analysis of Stratification in Scottish Higher Education using UCAS Data; Sampling frame for sex orientation identified based on Census 2021 small area geographies | 44 | Understanding the uptake and use of the Northern Ireland Concessionary Fares Scheme for the population aged 60 and over; Migration Observatory analysis of EU and non-EU migration in the UK; Parental separation and educational inequality: any evidence for growing disadvantage or 'diverging destinies' across three recent cohorts?; Contextualised Admissions and University Choice; Education and Identity; Inequalities in the 21st Century: Transfers, tax and tax credits; Health of Older People in Places : an asset for economic and social improvement for all; Accounting for Unmet Need in Equitable Healthcare Resource Allocation |

## Cache Telemetry and Cost

| Run | Cache read tokens | Cache creation tokens | Approx cache hit rate | Approx cost |
| --- | --- | --- | --- | --- |
| Opus 4.8 | 1472256 | 27553 | 98.2% | $7.50 |
| Opus 4.6 | 844812 | 25701 | 97.0% | $4.35 |

Cost note: Opus 4.8: output tokens not present in run.log telemetry. Opus 4.6: output tokens not present in run.log telemetry.
