# Opus 4.8 run 1 vs Opus 4.8 run 2 rc1 Comparison Summary

This report compares two full-register v4 rc1 classification runs side by side. It reports label agreement and disagreement patterns only; it does not rank the runs.

## Run Counts

| Run | Projects classified |
| --- | --- |
| Opus 4.8 run 1 | 1272 |
| Opus 4.8 run 2 | 1272 |

Project ID sets match: yes

## Agreement Rates

Overall agreement: 77.0% (979 of 1,272 projects agreed on all four label fields).

| Field | Agreement rate | Agreed projects | Compared projects |
| --- | --- | --- | --- |
| substantive_domains | 91.3% | 1161 | 1272 |
| linkage_mode | 93.1% | 1184 | 1272 |
| analytical_purpose | 91.7% | 1167 | 1272 |
| cross_cutting_tags | 98.3% | 1250 | 1272 |

## Disagreement Patterns by Category

### substantive_domains

| 4.8 run 1 label set | 4.8 run 2 label set | Projects |
| --- | --- | --- |
| Education & Skills | Education & Skills; Labour Market & Employment | 6 |
| Education & Skills; Labour Market & Employment | Education & Skills | 4 |
| Business & Productivity | Business & Productivity; Labour Market & Employment | 4 |
| Business & Productivity; Public Finance & Taxation | Business & Productivity | 4 |
| Labour Market & Employment | Education & Skills; Labour Market & Employment | 4 |
| Health & Social Care; Migration & Demographics | Health & Social Care | 3 |

### linkage_mode

| 4.8 run 1 label set | 4.8 run 2 label set | Projects |
| --- | --- | --- |
| Within-Domain Linkage | Cross-Domain Linkage | 34 |
| Cross-Domain Linkage | Within-Domain Linkage | 30 |
| Cross-Domain Linkage | Single-Dataset | 9 |
| Single-Dataset | Cross-Domain Linkage | 6 |
| Within-Domain Linkage | Single-Dataset | 6 |
| Single-Dataset | Within-Domain Linkage | 3 |

### analytical_purpose

| 4.8 run 1 label set | 4.8 run 2 label set | Projects |
| --- | --- | --- |
| Descriptive Monitoring | Outcome Tracking | 29 |
| Outcome Tracking | Descriptive Monitoring | 13 |
| Outcome Tracking | Policy Evaluation / Impact Analysis | 7 |
| Policy Evaluation / Impact Analysis | Outcome Tracking | 6 |
| Descriptive Monitoring | Methodological / Infrastructure Research | 4 |
| Outcome Tracking | Life-Course / Trajectory Analysis | 3 |
| Life-Course / Trajectory Analysis | Outcome Tracking | 3 |

### cross_cutting_tags

| 4.8 run 1 label set | 4.8 run 2 label set | Projects |
| --- | --- | --- |
| Demographic disparities / equity tag | (none) | 11 |
| (none) | Demographic disparities / equity tag | 11 |

## Tag-Specific Differences

| Tag | 4.8 run 1 only count | 4.8 run 1 only example titles | 4.8 run 2 only count | 4.8 run 2 only example titles |
| --- | --- | --- | --- | --- |
| Demographic disparities / equity tag | 11 | Homeownership of the young; Inequalities in the 21st Century – Chapter on Labour Market Inequality; Classifying the older population: understanding the geography of opportunities and challenges in England; Forecasting future socioeconomic inequalities in longevity: the impact of lifestyle "epidemics"; Addressing inclusivity in the spatial and social impacts of COVID-19 on the self-employed in the UK; Investigating HE application patterns by socioeconomic background across different institutions and courses; Tackling child health inequality. An interventional epidemiology platform to inform policy; Diagnostic profiles of bilingual and monolingual children in Wales | 11 | Education and Identity; Inequalities in the 21st Century: Transfers, tax and tax credits; Exploring Fertility Differentials in the 2011 Census; The link between characteristics of school pupils and labour market outcomes; The inequalities in the patterns of needs for carers and cared for people receiving support from local authorities across Wales; The effect of parental education and occupation on the disadvantage attainment gap - GUIE project; Social inequalities in education outcomes in NI; Youth Employment Analysis |

## Cache Telemetry and Cost

| Run | Cache read tokens | Cache creation tokens | Approx cache hit rate | Approx cost |
| --- | --- | --- | --- | --- |
| Opus 4.8 run 1 | 1472256 | 27553 | 98.2% | $7.50 |
| Opus 4.8 run 2 | 1441584 | 13968 | 99.0% | $7.28 |

Cost note: Opus 4.8 run 1: output tokens not present in run.log telemetry. Opus 4.8 run 2: output tokens not present in run.log telemetry.
