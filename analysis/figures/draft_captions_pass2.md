# Draft captions — pass 2

## Figure 1

**Figure 1. Replacing a human coder with Fable 5: panel agreement and replacement differences.**

Legend content checklist:

- Baseline n=150 records in every panel; tag counts are equity 11 and COVID-19 12 records applied by the coder majority [S2T001/S2T002, denominator and label-count cells; displayed 11 and 12].
- ABC is C01/C02/C03; LBC, ALC and ABL replace C01, C02 and C03 respectively with Fable 5; each δ is the substituted-panel α minus ABC [S2T001, S2T002, S3T001, S3T002 row cells].
- For equity, δᵦ upper=0.004117088549351349 (display +0.004) crosses zero; δₘᵢₙ upper=-0.006490658978949588 (display −0.006) does not [S2T001 interval-upper cells].
- COVID-19 δₐ interval=[0.0, 0.0] and δₘᵢₙ interval=[0.0, 0.0] (each displayed [0.000, 0.000]); both have zero width [S2T002 interval cells].
- The δₘᵢₙ point estimate matches δᵦ for domains, purposes and equity, and δₐ for COVID-19; δₘᵢₙ is selected within each resample, so its interval can differ from that component’s interval [S3T001, S3T002, S2T001, S2T002 δ cells].

## Figure 2

**Figure 2. Agreement and replacement differences for all baseline records and for those whose register entry coders judged sufficient to classify.**

Legend content checklist:

- Baseline n=150 and strict register-sufficient n=92; the two populations are nested [S3T001/S3T002 and S3T011/S3T012 denominator cells; displayed 150 and 92].
- The δₘᵢₙ point estimate matches δᵦ in both dimensions and both populations; it is selected within each resample, so intervals can differ [S3T001, S3T002, S3T011, S3T012 δ cells].
- Baseline purposes δₘᵢₙ upper=-0.002141124278556386 (display −0.002) and strict domains δₘᵢₙ lower=0.0005992244570877603 (display +0.001); both intervals exclude zero [S3T002/S3T011 interval cells].
- The α axis is 0.15–0.75, rather than the 0–1 scale used in Figure 1 and Supplementary Figure S1 [S3T001, S3T002, S3T011, S3T012 interval cells].

## Figure 3

**Figure 3. Label application counts: Fable 5 against the human majority.**

Legend content checklist:

- Across all labels, Fable 5 made 199 domain and 160 purpose applications; the coder majority made 173 and 129 (display unchanged) [S5T001/S5T002, summed label-count cells; G.12 derivation 3].
- Counts across labels are label applications rather than records; each point is one label [S5T001/S5T002 label-count cells].
- Vertical lines at 10 and 30 records show the preregistered count thresholds; labels below 10 remain plotted as counts [S5T001/S5T002 exported band cells].
- The 45° line marks equal application counts; points above it were applied more often by Fable 5 and points below it more often by the coder majority [S5T001/S5T002 label-count cells].
- The outlined point is Unclear from Register Entry: domains (13, 1) and purposes (26, 1), displayed as integer counts [S5T001/S5T002 coder-majority-positive and model-positive cells].

## Figure 4

**Figure 4. Kinds of disagreement between pairs of human coders and between Fable 5 and each coder.**

Legend content checklist:

- Displayed shares are containment/overlap/disjoint: domains human pairs 48%/5%/47% (n=220), domains Fable 5 pairs 52%/8%/40% (n=199), purposes human pairs 14%/<1%/86% (n=272), purposes Fable 5 pairs 15%/1%/84% (n=270) [disagreement_type_distribution.csv full-precision proportion and count cells].
- Containment means one set is inside the other; overlap means a shared label plus labels unique to each; disjoint means no shared label [disagreement export relation cells].
- Each record contributes three human pairs and three Fable 5–coder pairs; only different, non-empty sets are counted, and pairs from one record are not independent [disagreement export, eligible_records and nonidentical_nonempty_pairs cells].
- Unclear from Register Entry counts as a label; the export does not separate decline-versus-classify pairs from other disjoint pairs [disagreement export relation definition].
- The display describes kinds of disagreement rather than disagreement frequency or seriousness [disagreement export conditioning cells].

## Table 1

**Table 1: Research Domains: agreement on each label between pairs of human coders and between Fable 5 and each coder.**

Legend content checklist:

- Labels applied by the coder majority to at least 10 baseline records are shown; six labels below 10 are omitted here and retained as counts in Table 3: Migration & Demographics 9, Crime & Justice 4, Environment & Agriculture 4, Public Finance & Taxation 2, Data Infrastructure & Methodology 0, Housing & Planning 0 [S5T001 count and band cells].
- Cells are Cohen’s κ with 95% percentile-bootstrap intervals; pair columns share records and coders and are not independent [S5T005 status and interval cells].
- For Unclear from Register Entry, human-pair κ spans 0.150–0.322 and Fable 5–coder κ spans 0.037–0.241 (display 0.15–0.32 and 0.04–0.24); Fable 5 applied the label to 1 record [S5T005 and S5T001 cells].
- Unclear C01–C02 lower=−0.03775091928386179 (display −0.04); Fable 5–C03 lower=−3.142158243798238e-16 (display 0.00) [S5T005 interval-lower cells].

## Table 2

**Table 2: Analytical Purposes: agreement on each label between pairs of human coders and between Fable 5 and each coder.**

Legend content checklist:

- Labels applied by the coder majority to at least 10 baseline records are shown; four labels below 10 are omitted here and retained as counts in Table 4: Life-Course / Trajectory Analysis 9, Methodological / Infrastructure Research 7, Risk Prediction / Early Identification 1, Service Interaction / Systems Analysis 1 [S5T002 count and band cells].
- Cells are Cohen’s κ with 95% percentile-bootstrap intervals; pair columns share records and coders and are not independent [S5T006 status and interval cells].
- Outcome Tracking C01–C03 lower=−0.06775275757843611 (display −0.07) and C02–C03 lower=−0.0381591707542619 (display −0.04) [S5T006 interval-lower cells].
- All three Fable 5–coder lower bounds for Unclear are exactly 0 (display 0.00); the coder majority applied Unclear to 26 records and Fable 5 to 1 [S5T006/S5T002 cells].

## Table 3

**Table 3: Research Domains: agreement on each label between Fable 5 and the coder majority.**

Legend content checklist:

- Precision, recall and F1 are shown only for labels applied by the coder majority to at least 10 records; labels below 10 retain counts only [S5T001/S5T003/S5T007/S5T009 cells].
- Each label is assessed separately, using the coder majority as the reference rather than an adjudicated truth set [S5T003/S5T007 cells].
- For Unclear, Fable 5 applied the label to 1 of 13 coder-majority-positive records; precision and F1 are not estimable with an interval, while recall is 0.07692307692307693 [0.0, 0.25] (display 0.08 [0.00, 0.25]) [S5T003/S5T007/S5T009 cells].
- Total applications are Fable 5 199 and coder majority 173; substantive-only totals are 198 and 160 (display unchanged) [S5T001 summed cells; G.12 derivations 3–4].

## Table 4

**Table 4: Analytical Purposes: agreement on each label between Fable 5 and the coder majority.**

Legend content checklist:

- Precision, recall and F1 are shown only for labels applied by the coder majority to at least 10 records; labels below 10 retain counts only [S5T002/S5T004/S5T008/S5T010 cells].
- Each label is assessed separately, using the coder majority as the reference rather than an adjudicated truth set [S5T004/S5T008 cells].
- For Unclear, Fable 5 applied the label to 1 of 26 coder-majority-positive records; precision and F1 are not estimable with an interval, while recall is 0.038461538461538464 [0.0, 0.125] (display 0.04 [0.00, 0.13]) [S5T004/S5T008/S5T010 cells].
- Total applications are Fable 5 160 and coder majority 129; substantive-only totals are 159 and 103 (display unchanged) [S5T002 summed cells; G.12 derivations 3–4].

## Table 5

**Table 5: Kinds of disagreement between pairs of human coders and between Fable 5 and each coder: number and percentage of disagreeing pairs.**

Legend content checklist:

- Cells give n and whole percentages: domains human pairs 105/11/104 of 220 (48%/5%/47%); domains Fable 5 pairs 103/16/80 of 199 (52%/8%/40%); purposes human pairs 38/1/233 of 272 (14%/<1%/86%); purposes Fable 5 pairs 40/4/226 of 270 (15%/1%/84%) [disagreement_type_distribution.csv count and full-precision proportion cells].
- Each record contributes three human pairs and three Fable 5–coder pairs; only different, non-empty sets are counted, and pairs from one record are not independent [disagreement export, eligible_records and nonidentical_nonempty_pairs cells].
- No disagreeing domain or purpose pair involved an empty label set; Unclear from Register Entry counts as a label [disagreement export both-empty and exactly-one-empty cells, all 0].
- Unclear from Register Entry is counted as a label, and decline-versus-classify pairs are not separated from other disjoint pairs [disagreement export relation definition].

## Supplementary Figure S1

**Supplementary Figure S1. Replacing a human coder with Fable 5 in a non-representative hard-case sample (diagnostic).**

Legend content checklist:

- Baseline n=150 and hard-case n=75; hard-case is diagnostic and non-representative [S2T001/S2T002/S3T001/S3T002 and S2T007/S2T008/S3T007/S3T008 denominator cells].
- Applied by coder majority: baseline equity 11 and COVID-19 12; hard-case equity 8 and COVID-19 6 (display unchanged) [S2T001/S2T002 context and S2T017/S2T018 count cells].
- δₘᵢₙ matches baseline→hard-case components as follows: domains δᵦ→δ꜀; purposes δᵦ→δᵦ; equity δᵦ→δₐ; COVID-19 δₐ→δ꜀ [replacement tables’ point-estimate cells].
- Hard-case equity δₘᵢₙ=-0.11455822957777184 [-0.33012555322232656, 0.0] (display −0.115 [−0.330, 0.000]); the interval reaches zero [S2T007 δₘᵢₙ cells].
- Hard-case COVID-19 δ꜀ interval=[0.0, 0.0] and δₘᵢₙ interval=[0.0, 0.0] (each displayed [0.000, 0.000]); both have zero width [S2T008 interval cells].

## Supplementary Figure S2

**Supplementary Figure S2. How each coder, and the majority of coders, rated register-entry information and taxonomy fit.**

**Title to revisit: confidence panel added.**

Legend content checklist:

- Baseline n=150 and hard-case n=75; hard-case panels are diagnostic and non-representative [S8T001–S8T004, S9T001–S9T004 and SCF1T001–SCF1T009 denominator cells].
- The confidence row is exploratory and not preregistered [SCF1T001 onwards].
- Ordinal Krippendorff’s α for confidence is baseline 0.18209041188026154 [0.07872545505759505, 0.283043590671762] and hard-case 0.10720791308938349 [-0.049591586591360405, 0.2497475826406676] (display 0.18 [0.08, 0.28] and 0.11 [−0.05, 0.25]); valid/invalid/requested resamples are 2000/0/2000 for each [SCF1T003/SCF1T008].
- Unanimous confidence ratings: baseline 55/150 and hard-case 24/75 (display unchanged) [SCF1T004/SCF1T009].
- Supplementary Tables S1a–S1b give the exact register-information and taxonomy-fit values [S8T001–S8T004 and S9T001–S9T004].

## Supplementary Table S1a

**Supplementary Table S1a: Majority ratings of whether the register entry gave enough information to classify the project.**

Legend content checklist:

- A majority rating is the category chosen by at least two of three coders; if all three differ, the result is No majority [S8T003/S8T004 category cells].
- Hard-case percentages have no intervals because the sample is non-random [S8T004 interval-status cells].
- Strict n=92 equals the Sufficient majority count; broad n=148 pools Sufficient and Partially sufficient before counting coders and therefore differs from 92+55=147 [S8T003/S8T005 cells].
- Exact coder distributions are shown in Supplementary Figure S2 [S8T001–S8T004 cells].

## Supplementary Table S1b

**Supplementary Table S1b: Majority ratings of how well the taxonomy fitted the project.**

Legend content checklist:

- A majority rating is the category chosen by at least two of three coders; if all three differ, the result is No majority [S9T003/S9T004 category cells].
- Hard-case percentages have no intervals because the sample is non-random [S9T004 interval-status cells].
- Exact coder distributions are shown in Supplementary Figure S2 [S9T001–S9T004 cells].

## Supplementary Table S1c

**Supplementary Table S1c: Number of labels agreed by at least two of three coders per record.**

Legend content checklist:

- Each label is assessed separately and is agreed when at least two coders applied it, so a record can have none, one or several agreed labels [majority_coverage.csv count cells].
- ‘1 agreed label’ excludes records agreed only on Unclear; counts and whole percentages are approved derivations from exported operands [majority_coverage.csv and G.12 derivations 1–2].
- No record combined agreed Unclear with a substantive label; no record had more than three agreed labels; no record had more than two agreed purposes (baseline 0/150, hard-case 0/75) [majority_coverage.csv zero and constraint cells].
- Hard-case percentages have no intervals because the sample is non-random [majority_coverage.csv population cells].
