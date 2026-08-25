# Scratch-coder Stage B summary

Preliminary Stage B aggregate diagnostics from the frozen scratch-coder validation dataset. Record-level disagreement adjudication and project-owner evidence are not incorporated.

## Support distribution

Support is determined only from two-of-three majority-human positives in the 150-record random baseline.

### <10
- Analytical Purposes: Life-Course / Trajectory Analysis (N=9)
- Analytical Purposes: Methodological / Infrastructure Research (N=7)
- Analytical Purposes: Risk Prediction / Early Identification (N=1)
- Analytical Purposes: Service Interaction / Systems Analysis (N=1)
- Research Domains: Crime & Justice (N=4)
- Research Domains: Data Infrastructure & Methodology (N=0)
- Research Domains: Environment & Agriculture (N=4)
- Research Domains: Housing & Planning (N=0)
- Research Domains: Migration & Demographics (N=9)
- Research Domains: Public Finance & Taxation (N=2)

### 10–29
- Analytical Purposes: Outcome Tracking (N=19)
- Analytical Purposes: Unclear from Register Entry (N=26)
- Cross-cutting tag: COVID-19 & Pandemic (N=12)
- Cross-cutting tag: Demographic disparities / equity (N=11)
- Research Domains: Education & Skills (N=27)
- Research Domains: Health & Social Care (N=23)
- Research Domains: Poverty, Wealth & Living Standards (N=11)
- Research Domains: Unclear from Register Entry (N=13)

### >=30
- Analytical Purposes: Descriptive Monitoring (N=36)
- Analytical Purposes: Policy Evaluation / Impact Analysis (N=30)
- Research Domains: Business & Productivity (N=41)
- Research Domains: Labour Market & Employment (N=39)

## Exact-set / Jaccard

### baseline

| Dimension | Pair | Exact-set [95% CI] | Mean Jaccard [95% CI] |
|---|---|---:|---:|
| Research Domains | L-A | 0.560 [0.487, 0.640] | 0.719 [0.663, 0.774] |
| Research Domains | L-B | 0.573 [0.493, 0.653] | 0.701 [0.639, 0.760] |
| Research Domains | L-C | 0.540 [0.460, 0.620] | 0.637 [0.569, 0.702] |
| Analytical Purposes | L-A | 0.347 [0.273, 0.427] | 0.440 [0.371, 0.509] |
| Analytical Purposes | L-B | 0.560 [0.480, 0.640] | 0.583 [0.503, 0.660] |
| Analytical Purposes | L-C | 0.293 [0.220, 0.367] | 0.319 [0.247, 0.389] |

### hard_case — DIAGNOSTIC — disagreement-enriched and non-representative.

| Dimension | Pair | Exact-set [95% CI] | Mean Jaccard [95% CI] |
|---|---|---:|---:|
| Research Domains | L-A | 0.333 [0.227, 0.440] | 0.583 [0.506, 0.658] |
| Research Domains | L-B | 0.400 [0.293, 0.507] | 0.577 [0.489, 0.667] |
| Research Domains | L-C | 0.373 [0.267, 0.493] | 0.548 [0.458, 0.644] |
| Analytical Purposes | L-A | 0.213 [0.120, 0.307] | 0.324 [0.236, 0.424] |
| Analytical Purposes | L-B | 0.293 [0.200, 0.400] | 0.400 [0.300, 0.500] |
| Analytical Purposes | L-C | 0.173 [0.093, 0.267] | 0.253 [0.167, 0.347] |

## Per-label Domain diagnostics

| Label | Human N | Model N | Band | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] |
|---|---:|---:|---|---:|---:|---:|
| Business & Productivity | 41 | 45 | STANDARD | 0.889 [0.787, 0.975] | 0.976 [0.917, 1.000] | 0.930 [0.864, 0.978] |
| Crime & Justice | 4 | 4 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Data Infrastructure & Methodology | 0 | 4 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Education & Skills | 27 | 35 | LOW SUPPORT | 0.743 [0.590, 0.885] | 0.963 [0.880, 1.000] | 0.839 [0.723, 0.923] |
| Environment & Agriculture | 4 | 10 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Health & Social Care | 23 | 25 | LOW SUPPORT | 0.880 [0.731, 1.000] | 0.957 [0.852, 1.000] | 0.917 [0.818, 0.982] |
| Housing & Planning | 0 | 1 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Labour Market & Employment | 39 | 56 | STANDARD | 0.625 [0.492, 0.750] | 0.897 [0.791, 0.976] | 0.737 [0.627, 0.830] |
| Migration & Demographics | 9 | 6 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Poverty, Wealth & Living Standards | 11 | 10 | LOW SUPPORT | 0.600 [0.250, 0.900] | 0.545 [0.231, 0.857] | 0.571 [0.272, 0.800] |
| Public Finance & Taxation | 2 | 2 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Unclear from Register Entry | 13 | 1 | LOW SUPPORT | 1.000 [CI NOT ESTIMABLE, CI NOT ESTIMABLE] | 0.077 [0.000, 0.250] | 0.143 [CI NOT ESTIMABLE, CI NOT ESTIMABLE] |
Pairwise A-B/A-C/B-C/L-A/L-B/L-C kappa is provided in `per_label_pairwise_kappa.csv`. Record examples and adjudicated issue notes for rare labels are deferred until adjudication in order to preserve record-level masking.

## Per-label Purpose diagnostics

| Label | Human N | Model N | Band | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] |
|---|---:|---:|---|---:|---:|---:|
| Descriptive Monitoring | 36 | 52 | STANDARD | 0.500 [0.367, 0.639] | 0.722 [0.568, 0.861] | 0.591 [0.463, 0.699] |
| Life-Course / Trajectory Analysis | 9 | 11 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Methodological / Infrastructure Research | 7 | 10 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Outcome Tracking | 19 | 47 | LOW SUPPORT | 0.277 [0.152, 0.417] | 0.684 [0.458, 0.889] | 0.394 [0.229, 0.540] |
| Policy Evaluation / Impact Analysis | 30 | 33 | STANDARD | 0.636 [0.459, 0.808] | 0.700 [0.531, 0.857] | 0.667 [0.507, 0.793] |
| Risk Prediction / Early Identification | 1 | 2 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Service Interaction / Systems Analysis | 1 | 4 | RARE | DESCRIPTIVE ONLY — performance estimates withheld under preregistered rare-label rule. | DESCRIPTIVE ONLY | DESCRIPTIVE ONLY |
| Unclear from Register Entry | 26 | 1 | LOW SUPPORT | 1.000 [CI NOT ESTIMABLE, CI NOT ESTIMABLE] | 0.038 [0.000, 0.125] | 0.074 [CI NOT ESTIMABLE, CI NOT ESTIMABLE] |
Pairwise A-B/A-C/B-C/L-A/L-B/L-C kappa is provided in `per_label_pairwise_kappa.csv`. Record examples and adjudicated issue notes for rare labels are deferred until adjudication in order to preserve record-level masking.

## Macro performance
- Research Domains: eligible labels: Business & Productivity; Education & Skills; Health & Social Care; Labour Market & Employment; Poverty, Wealth & Living Standards; Unclear from Register Entry; precision 0.789 [CI NOT ESTIMABLE, CI NOT ESTIMABLE], recall 0.736 [0.678, 0.799], F1 0.689 [CI NOT ESTIMABLE, CI NOT ESTIMABLE].
- Analytical Purposes: eligible labels: Descriptive Monitoring; Outcome Tracking; Policy Evaluation / Impact Analysis; Unclear from Register Entry; precision 0.603 [CI NOT ESTIMABLE, CI NOT ESTIMABLE], recall 0.536 [0.453, 0.607], F1 0.431 [CI NOT ESTIMABLE, CI NOT ESTIMABLE].

## Tag diagnostics

### Demographic disparities / equity — baseline **LOW SUPPORT — estimates are unstable and should not be interpreted from point estimates alone.**
Support 11 (LOW SUPPORT); human prevalence 0.073; model prevalence 0.127.
Raw 0.880 [0.827, 0.927]; positive 0.400 [0.162, 0.606]; negative 0.933 [0.900, 0.961]; kappa 0.339 [0.099, 0.559]; AC1 0.854 [0.773, 0.918]; precision 0.316 [0.118, 0.538]; recall 0.545 [0.250, 0.857]; F1 0.400 [0.166, 0.606].

### COVID-19 & Pandemic — baseline **LOW SUPPORT — estimates are unstable and should not be interpreted from point estimates alone.**
Support 12 (LOW SUPPORT); human prevalence 0.080; model prevalence 0.087.
Raw 0.993 [0.980, 1.000]; positive 0.960 [0.857, 1.000]; negative 0.996 [0.989, 1.000]; kappa 0.956 [0.847, 1.000]; AC1 0.992 [0.975, 1.000]; precision 0.923 [0.750, 1.000]; recall 1.000 [1.000, 1.000]; F1 0.960 [0.857, 1.000].

### Demographic disparities / equity — hard_case — DIAGNOSTIC — disagreement-enriched and non-representative. **LOW SUPPORT — estimates are unstable and should not be interpreted from point estimates alone.**
Support 11 (LOW SUPPORT); human prevalence 0.107; model prevalence 0.107.
Raw 0.920 [0.853, 0.973]; positive 0.625 [0.286, 0.857]; negative 0.955 [0.917, 0.986]; kappa 0.580 [0.214, 0.834]; AC1 0.901 [0.812, 0.970]; precision 0.625 [0.250, 1.000]; recall 0.625 [0.250, 1.000]; F1 0.625 [0.286, 0.857].

### COVID-19 & Pandemic — hard_case — DIAGNOSTIC — disagreement-enriched and non-representative. **LOW SUPPORT — estimates are unstable and should not be interpreted from point estimates alone.**
Support 12 (LOW SUPPORT); human prevalence 0.080; model prevalence 0.080.
Raw 1.000 [1.000, 1.000]; positive 1.000 [1.000, 1.000]; negative 1.000 [1.000, 1.000]; kappa 1.000 [1.000, 1.000]; AC1 1.000 [1.000, 1.000]; precision 1.000 [1.000, 1.000]; recall 1.000 [1.000, 1.000]; F1 1.000 [1.000, 1.000].

## Interpretation boundary

The majority-human reference is a preregistered analytical device for per-label metrics and later adjudication eligibility. It is not an adjudicated gold standard.

Hard-case records are disagreement-enriched and are not used for population-level per-label performance estimation or support thresholds.

Labels with fewer than 10 majority-human-positive baseline records are reported descriptively only.

Stage B reveals aggregate label-specific performance patterns but does not identify the records producing those patterns.

Record examples and adjudicated issue notes are deferred until adjudication.
