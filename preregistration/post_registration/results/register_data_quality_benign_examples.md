# Benign normalisation examples

> The broad reconciliation-burden rate counts any change between the parsed register form and the canonical representation used for aggregation. Most such changes are benign standardisation rather than corrections.

## Quantitative context

- Datasets: aliases account for 2,211/2,639 changed occurrences (83.78%), normalised format for 426/2,639 (16.14%), and compound/multi-dataset handling for 2/2,639 (0.08%).
- Organisations: aliases account for 514/761 changed occurrences (67.54%), identity-with-display-change for 235/761 (30.88%), and parser cleanup for 12/761 (1.58%).
- `parser_cleanup` is excluded from the benign examples. The two compound/multi-dataset occurrences are retained in the quantitative context but are not needed in the shortlist.

The class denominators above are the unchanged authoritative native-status totals. The candidate mapping counts and ranked examples below exclude mappings already classified in the audit's explicit-correction subset. The top-five share uses the full native class occurrence denominator.

| Field | Transformation class | Changed occurrences | Distinct non-corrective mappings | Share accounted for by top five mappings |
| --- | --- | ---: | ---: | ---: |
| datasets | alias | 2,211 | 325 | 29.90% |
| datasets | normalised_format | 426 | 162 | 29.11% |
| organisations | alias | 514 | 169 | 32.10% |
| organisations | identity_with_display_change | 235 | 13 | 86.81% |

## Top mappings by class

### Dataset alias

| Rank | Field | Transformation class | Observed register form | Canonical form | Occurrences | Records |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1 | datasets | alias | Business Structure Database | Business Structure Database (BSD) | 176 | 176 |
| 2 | datasets | alias | Annual Business Survey | Annual Business Survey (ABS) | 143 | 143 |
| 3 | datasets | alias | Annual Population Survey | Annual Population Survey (APS) | 131 | 126 |
| 4 | datasets | alias | Annual Survey of Hours and Earnings | Annual Survey of Hours and Earnings (ASHE) | 123 | 123 |
| 5 | datasets | alias | Business Structure Database - UK | Business Structure Database (BSD) | 88 | 88 |
| 6 | datasets | alias | UK Innovation Survey | UK Innovation Survey (UKIS) | 75 | 75 |
| 7 | datasets | alias | Labour Force Survey | Labour Force Survey (LFS) | 70 | 54 |
| 8 | datasets | alias | Longitudinal Education Outcomes SRS Iteration 2 Standard Extract - England | Longitudinal Education Outcomes (LEO) | 55 | 55 |
| 9 | datasets | alias | Annual Business Survey - GB | Annual Business Survey (ABS) | 44 | 44 |
| 10 | datasets | alias | Annual Survey of Hours and Earnings - UK | Annual Survey of Hours and Earnings (ASHE) | 41 | 41 |

### Dataset normalised format

| Rank | Field | Transformation class | Observed register form | Canonical form | Occurrences | Records |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1 | datasets | normalised_format | Labour Force Survey Person - UK | Labour Force Survey Person | 39 | 39 |
| 2 | datasets | normalised_format | Understanding Society - UK | Understanding Society | 28 | 28 |
| 3 | datasets | normalised_format | Labour Force Survey Longitudinal - UK | Labour Force Survey Longitudinal | 22 | 22 |
| 4 | datasets | normalised_format | Labour Force Survey Household - UK | Labour Force Survey Household | 21 | 21 |
| 5 | datasets | normalised_format | Employer Skills Survey and Investment in Training - UK | Employer Skills Survey and Investment in Training | 14 | 14 |
| 6 | datasets | normalised_format | Annual Foreign Direct Investment Survey - UK | Annual Foreign Direct Investment Survey | 8 | 8 |
| 7 | datasets | normalised_format | Annual Purchases Survey - UK | Annual Purchases Survey | 8 | 8 |
| 8 | datasets | normalised_format | Decision Maker Panel - UK | Decision Maker Panel | 8 | 8 |
| 9 | datasets | normalised_format | MoJ Data First Crown court defendant case level dataset | MoJ Data First Crown Court Defendant Case Level | 8 | 7 |
| 10 | datasets | normalised_format | Labour Force Survey Five-Quarter Longitudinal Dataset | Labour Force Survey Five-Quarter Longitudinal | 7 | 7 |

### Organisation alias

| Rank | Field | Transformation class | Observed register form | Canonical form | Occurrences | Records |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1 | organisations | alias | London School of Economics | London School of Economics and Political Science (LSE) | 55 | 55 |
| 2 | organisations | alias | Office for National Statistics | Office for National Statistics (ONS) | 40 | 40 |
| 3 | organisations | alias | King's College London | King's College London (KCL) | 24 | 24 |
| 4 | organisations | alias | London School of Economics and Political Science | London School of Economics and Political Science (LSE) | 23 | 23 |
| 5 | organisations | alias | The University of Manchester | University of Manchester | 23 | 23 |
| 6 | organisations | alias | IPSOS MORI | Ipsos | 18 | 18 |
| 7 | organisations | alias | The University of Edinburgh | University of Edinburgh | 18 | 18 |
| 8 | organisations | alias | National Foundation for Educational Research | National Foundation for Education Research (NFER) | 13 | 13 |
| 9 | organisations | alias | The London School of Economics and Political Science | London School of Economics and Political Science (LSE) | 12 | 12 |
| 10 | organisations | alias | University of Durham | Durham University | 11 | 11 |

### Organisation identity with display change

| Rank | Field | Transformation class | Observed register form | Canonical form | Occurrences | Records |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 1 | organisations | identity_with_display_change | University College London | University College London (UCL) | 99 | 99 |
| 2 | organisations | identity_with_display_change | Institute for Fiscal Studies | Institute for Fiscal Studies (IFS) | 64 | 64 |
| 3 | organisations | identity_with_display_change | Public Health Wales | Public Health Wales (PHW) | 15 | 15 |
| 4 | organisations | identity_with_display_change | London School of Hygiene and Tropical Medicine | London School of Hygiene and Tropical Medicine (LSHTM) | 13 | 13 |
| 5 | organisations | identity_with_display_change | National Institute for Economic and Social Research | National Institute for Economic and Social Research (NIESR) | 13 | 13 |
| 6 | organisations | identity_with_display_change | Competition and Markets Authority | Competition and Markets Authority (CMA) | 8 | 8 |
| 7 | organisations | identity_with_display_change | Massachusetts Institute of Technology | Massachusetts Institute of Technology (MIT) | 5 | 5 |
| 8 | organisations | identity_with_display_change | Department for Business, Energy and Industrial Strategy | Department for Business, Energy and Industrial Strategy (BEIS) | 4 | 4 |
| 9 | organisations | identity_with_display_change | Low Pay Commission | Low Pay Commission (LPC) | 4 | 4 |
| 10 | organisations | identity_with_display_change | Public Health England | Public Health England (PHE) | 4 | 4 |

## ADR-facing shortlist

The shortlist is mechanical: it first takes the minimum class leaders needed for coverage (the two highest-frequency dataset aliases and the leader of each other required class), then fills to eight rows using the highest-frequency remaining mappings.

| Type | Observed register form | Canonical form | Occurrences | What the transformation does |
| --- | --- | --- | ---: | --- |
| Dataset alias | Business Structure Database | Business Structure Database (BSD) | 176 | collapses equivalent dataset naming |
| Dataset alias | Annual Business Survey | Annual Business Survey (ABS) | 143 | collapses equivalent dataset naming |
| Dataset alias | Annual Population Survey | Annual Population Survey (APS) | 131 | collapses equivalent dataset naming |
| Dataset alias | Annual Survey of Hours and Earnings | Annual Survey of Hours and Earnings (ASHE) | 123 | collapses equivalent dataset naming |
| Dataset alias | Business Structure Database - UK | Business Structure Database (BSD) | 88 | collapses equivalent dataset naming |
| Dataset normalised format | Labour Force Survey Person - UK | Labour Force Survey Person | 39 | standardises formatting |
| Organisation alias | London School of Economics | London School of Economics and Political Science (LSE) | 55 | collapses equivalent organisation naming |
| Organisation identity with display change | University College London | University College London (UCL) | 99 | adds approved canonical display acronym |

No mapping in these tables belongs to the audit's explicit-correction subset. All displayed raw forms occurred verbatim in the frozen register; no Record ID, Project ID, title, researcher name, or validation/sample information is included.
