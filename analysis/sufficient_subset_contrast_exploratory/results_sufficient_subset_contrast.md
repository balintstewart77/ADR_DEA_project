# Strict register-sufficient subset against the full random baseline (post hoc, exploratory)

**Post hoc and exploratory; not preregistered.** The specification (`SPEC_sufficient_subset_contrast_2026-11-13.md`) was written on 13 November 2026 after initial results from a since-deleted run had been seen. No hypothesis tests or p-values. Bootstrap intervals here are 95% percentile intervals (10,000 paired record resamples, seed 20261113). Distance: MASI. A = C01, B = C02, C = C03, L = Fable 5.

Populations: full random baseline (150 records); strict register-sufficient subset (92 records on which at least two coders rated the entry Sufficient); its complement (58 records). The exposure-flagged record is kept (it lies in the sufficient subset). All four raters have complete, valid sets in both dimensions on all 150 records.

## Caveats for interpretation (added after the first run)

These caveats were added after the first run, on review, before any commit. They change no method or number.

1. **The subset is not independent of the coders' abstention.** Sufficiency is rated by the same coders whose agreement is measured, and each coder's Unclear-only sets fall almost entirely on entries that coder did not rate Sufficient (SSC1T012; Unclear-only when own rating Sufficient against when not: Research Domains, C01: 0/107 against 7/43; Research Domains, C02: 2/96 against 12/54; Research Domains, C03: 0/59 against 39/91; Analytical Purposes, C01: 1/107 against 22/43; Analytical Purposes, C02: 1/96 against 14/54; Analytical Purposes, C03: 0/59 against 68/91). Fable 5 almost never abstains, so restricting to coder-rated Sufficient entries removes coder abstentions largely by construction, and that favours the panels that include Fable 5. For Analytical Purposes the abstention (U) term is 76% of the delta_min contrast (+0.0430 of +0.0563), so that contrast mostly reflects this selection, not better substantive classification on clear entries. For Research Domains the substantive (S) term is 89% (+0.0355 of +0.0401), so the domains contrast rests mainly on substantive agreement.
2. **The contrast compares a subset with the population that contains it.** The subset is 92 of the 150 records (61%), so strict minus full is diluted towards zero and is not a comparison of sufficient against not-sufficient entries. The complement estimates show the larger gap (human-only alpha: domains 0.57 sufficient, 0.45 complement; purposes 0.29 and 0.18).
3. **delta_B and delta_min are not separate findings.** delta_min equals delta_B at the point estimate in both populations and both dimensions, so both intervals excluding zero is one finding, not two. Sixteen intervals are reported without adjustment (10 exclude zero); reading only those that exclude zero overstates the evidence.
4. **Delta contrasts are differences of differences.** Each delta contrast is in substance a subset-by-panel interaction. They are reported as descriptive contrasts; no interaction is claimed, and an interval excluding zero is not evidence of one.
5. **The coders are held fixed.** Only records were resampled, so the intervals describe uncertainty over records for these three coders (C01, C02, C03) and this model output, not over other coders or other runs.

## SSC1T001–002 — Point estimates and strict-minus-full contrasts

| Quantity | Domains: full | strict | contrast [95% interval] | Purposes: full | strict | contrast [95% interval] |
|---|---|---|---|---|---|---|
| alpha_ABC (primary) | 0.5263 | 0.5663 | +0.0400 [−0.0093, +0.0871] | 0.2921 | 0.2885 | −0.0036 [−0.0553, +0.0467] |
| alpha_LBC | 0.5834 | 0.6547 | +0.0713 [+0.0194, +0.1260] | 0.2756 | 0.3299 | +0.0543 [+0.0047, +0.1036] |
| alpha_ALC | 0.5280 | 0.6080 | +0.0801 [+0.0321, +0.1288] | 0.2494 | 0.3021 | +0.0527 [+0.0057, +0.1005] |
| alpha_ABL | 0.5735 | 0.6396 | +0.0661 [+0.0178, +0.1133] | 0.3575 | 0.3965 | +0.0389 [−0.0163, +0.0935] |
| delta_A | 0.0570 | 0.0884 | +0.0313 [−0.0054, +0.0704] | −0.0165 | 0.0414 | +0.0579 [+0.0177, +0.1023] |
| delta_B | 0.0016 | 0.0417 | +0.0401 [+0.0087, +0.0735] | −0.0427 | 0.0136 | +0.0563 [+0.0173, +0.0980] |
| delta_C | 0.0472 | 0.0733 | +0.0261 [−0.0125, +0.0652] | 0.0654 | 0.1080 | +0.0425 [−0.0093, +0.0945] |
| delta_min | 0.0016 | 0.0417 | +0.0401 [+0.0067, +0.0701] | −0.0427 | 0.0136 | +0.0563 [+0.0159, +0.0950] |

Valid draws: Research Domains: 10,000/10,000 valid for every contrast; Analytical Purposes: 10,000/10,000 valid for every contrast. Full and strict point estimates equal S3T001, S3T002, S3T011 and S3T012 within 1e-12.

Complement point estimates (descriptive; no intervals): Research Domains: alpha_ABC 0.4465, delta_min −0.0522; Analytical Purposes: alpha_ABC 0.1775, delta_min −0.0960.

## SSC1T003 — Strict resample size

Across 10,000 draws the strict resample held 70–113 occurrences (median 92; central 95% 80–104); no draw had an empty subset; every draw contained duplicate records.

## SSC1T005 — Disagreement diagnostic, pooled by pair family

Pooled over three pairs (3N comparisons per family; not 3N independent observations).

### Research Domains

| Family | Population | Both Unclear-only | Exactly one Unclear-only | Different substantive (of both substantive) | Exact match | Mean Jaccard | Mean MASI distance | Mean MASI, both substantive |
|---|---|---|---|---|---|---|---|---|
| human-human | full | 19/450 (4%) | 82/450 (18%) | 138/349 (40%) | 230/450 (51%) | 0.633 | 0.410 | 0.294 |
| human-human | sufficient | 1/276 (<1%) | 30/276 (11%) | 96/245 (39%) | 150/276 (54%) | 0.678 | 0.370 | 0.294 |
| human-human | complement | 18/174 (10%) | 52/174 (30%) | 42/104 (40%) | 80/174 (46%) | 0.563 | 0.474 | 0.293 |
| model-human | full | 3/450 (1%) | 57/450 (13%) | 142/390 (36%) | 251/450 (56%) | 0.686 | 0.361 | 0.270 |
| model-human | sufficient | 0/276 (0%) | 16/276 (6%) | 83/260 (32%) | 177/276 (64%) | 0.763 | 0.280 | 0.235 |
| model-human | complement | 3/174 (2%) | 41/174 (24%) | 59/130 (45%) | 74/174 (43%) | 0.563 | 0.490 | 0.340 |

### Analytical Purposes

| Family | Population | Both Unclear-only | Exactly one Unclear-only | Different substantive (of both substantive) | Exact match | Mean Jaccard | Mean MASI distance | Mean MASI, both substantive |
|---|---|---|---|---|---|---|---|---|
| human-human | full | 44/450 (10%) | 124/450 (28%) | 148/282 (52%) | 178/450 (40%) | 0.439 | 0.576 | 0.480 |
| human-human | sufficient | 0/276 (0%) | 44/276 (16%) | 124/232 (53%) | 108/276 (39%) | 0.444 | 0.574 | 0.493 |
| human-human | complement | 44/174 (25%) | 80/174 (46%) | 24/50 (48%) | 70/174 (40%) | 0.430 | 0.580 | 0.418 |
| model-human | full | 3/450 (1%) | 103/450 (23%) | 167/344 (49%) | 180/450 (40%) | 0.447 | 0.569 | 0.445 |
| model-human | sufficient | 0/276 (0%) | 22/276 (8%) | 125/254 (49%) | 129/276 (47%) | 0.521 | 0.498 | 0.455 |
| model-human | complement | 3/174 (2%) | 81/174 (47%) | 42/90 (47%) | 51/174 (29%) | 0.330 | 0.682 | 0.419 |

Direction of model–human abstention mismatches (Fable 5 Unclear-only with the coder substantive / the coder Unclear-only with Fable 5 substantive): Research Domains, sufficient: 0 / 16; Research Domains, complement: 0 / 41; Analytical Purposes, sufficient: 0 / 22; Analytical Purposes, complement: 0 / 81. Per-pair rows are in `SSC1T004.csv`.

## SSC1T006 — Unclear-only frequency and substantive cardinality, by rater

| Dimension | Rater | Unclear-only: sufficient | complement | Mean substantive labels among classified: sufficient | complement |
|---|---|---|---|---|---|
| Research Domains | C01 | 0/92 (0%) | 7/58 (12%) | 1.47 | 1.59 |
| Research Domains | C02 | 2/92 (2%) | 12/58 (21%) | 1.08 | 1.24 |
| Research Domains | C03 | 14/92 (15%) | 25/58 (43%) | 1.26 | 1.24 |
| Research Domains | Fable 5 | 0/92 (0%) | 1/58 (2%) | 1.29 | 1.39 |
| Analytical Purposes | C01 | 2/92 (2%) | 21/58 (36%) | 1.26 | 1.24 |
| Analytical Purposes | C02 | 0/92 (0%) | 15/58 (26%) | 1.00 | 1.02 |
| Analytical Purposes | C03 | 20/92 (22%) | 48/58 (83%) | 1.03 | 1.20 |
| Analytical Purposes | Fable 5 | 0/92 (0%) | 1/58 (2%) | 1.09 | 1.04 |

## SSC1T007 — Label counts by rater (sufficient / complement)

Counts out of 92 / 58 records; zero-count labels included.

### Research Domains

| Label | C01 | C02 | C03 | Fable 5 |
|---|---|---|---|---|
| Business & Productivity | 27 / 20 | 25 / 13 | 23 / 9 | 29 / 16 |
| Crime & Justice | 3 / 1 | 3 / 1 | 3 / 0 | 3 / 1 |
| Data Infrastructure & Methodology | 2 / 1 | 0 / 0 | 0 / 0 | 2 / 2 |
| Education & Skills | 22 / 9 | 18 / 9 | 16 / 6 | 23 / 12 |
| Environment & Agriculture | 5 / 4 | 1 / 2 | 2 / 2 | 5 / 5 |
| Health & Social Care | 17 / 8 | 15 / 4 | 21 / 3 | 18 / 7 |
| Housing & Planning | 1 / 2 | 0 / 0 | 0 / 0 | 1 / 0 |
| Labour Market & Employment | 33 / 17 | 25 / 15 | 22 / 10 | 31 / 25 |
| Migration & Demographics | 7 / 8 | 2 / 5 | 3 / 4 | 2 / 4 |
| Poverty, Wealth & Living Standards | 15 / 7 | 7 / 7 | 8 / 7 | 4 / 6 |
| Public Finance & Taxation | 3 / 4 | 1 / 1 | 0 / 0 | 1 / 1 |
| Unclear from Register Entry | 0 / 7 | 2 / 12 | 14 / 25 | 0 / 1 |

### Analytical Purposes

| Label | C01 | C02 | C03 | Fable 5 |
|---|---|---|---|---|
| Descriptive Monitoring | 34 / 14 | 28 / 22 | 29 / 4 | 25 / 27 |
| Life-Course / Trajectory Analysis | 14 / 9 | 15 / 7 | 2 / 2 | 6 / 5 |
| Methodological / Infrastructure Research | 15 / 6 | 3 / 2 | 4 / 0 | 6 / 4 |
| Outcome Tracking | 23 / 5 | 29 / 8 | 5 / 1 | 35 / 12 |
| Policy Evaluation / Impact Analysis | 24 / 9 | 15 / 5 | 32 / 5 | 23 / 10 |
| Risk Prediction / Early Identification | 1 / 2 | 2 / 0 | 1 / 0 | 1 / 1 |
| Service Interaction / Systems Analysis | 2 / 1 | 0 / 0 | 1 / 0 | 4 / 0 |
| Unclear from Register Entry | 2 / 21 | 0 / 15 | 20 / 48 | 0 / 1 |

## SSC1T008 — Secondary check: records where all four raters classify substantively

Not a controlled comparison: the records that remain differ in composition between populations.

| Dimension | Population | Records | Family | Different substantive sets | Mean MASI distance |
|---|---|---|---|---|---|
| Research Domains | sufficient | 77/92 | human-human | 87/231 (38%) | 0.279 |
| Research Domains | sufficient | 77/92 | model-human | 70/231 (30%) | 0.218 |
| Research Domains | complement | 29/58 | human-human | 35/87 (40%) | 0.289 |
| Research Domains | complement | 29/58 | model-human | 37/87 (43%) | 0.318 |
| Analytical Purposes | sufficient | 70/92 | human-human | 110/210 (52%) | 0.487 |
| Analytical Purposes | sufficient | 70/92 | model-human | 98/210 (47%) | 0.434 |
| Analytical Purposes | complement | 9/58 | human-human | 9/27 (33%) | 0.272 |
| Analytical Purposes | complement | 9/58 | model-human | 12/27 (44%) | 0.370 |

## SSC1T009 — Observed (Do) and expected (De) disagreement

Do = mean MASI distance over the three within-record pairs; DoU = abstention mismatches (one set Unclear-only, the other substantive); DoS = different substantive sets.

| Dimension | Panel | Population | Do | DoU | DoS | De | alpha |
|---|---|---|---|---|---|---|---|
| Research Domains | ABC | full | 0.4100 | 0.1822 | 0.2278 | 0.8655 | 0.5263 |
| Research Domains | ABC | sufficient | 0.3696 | 0.1087 | 0.2609 | 0.8522 | 0.5663 |
| Research Domains | ABC | complement | 0.4741 | 0.2989 | 0.1752 | 0.8565 | 0.4465 |
| Research Domains | LBC | full | 0.3563 | 0.1822 | 0.1741 | 0.8552 | 0.5834 |
| Research Domains | LBC | sufficient | 0.2899 | 0.1087 | 0.1812 | 0.8395 | 0.6547 |
| Research Domains | LBC | complement | 0.4617 | 0.2989 | 0.1628 | 0.8569 | 0.4612 |
| Research Domains | ALC | full | 0.4093 | 0.1778 | 0.2315 | 0.8672 | 0.5280 |
| Research Domains | ALC | sufficient | 0.3353 | 0.1014 | 0.2339 | 0.8556 | 0.6080 |
| Research Domains | ALC | complement | 0.5267 | 0.2989 | 0.2278 | 0.8695 | 0.3943 |
| Research Domains | ABL | full | 0.3662 | 0.0756 | 0.2907 | 0.8587 | 0.5735 |
| Research Domains | ABL | sufficient | 0.3039 | 0.0145 | 0.2895 | 0.8435 | 0.6396 |
| Research Domains | ABL | complement | 0.4650 | 0.1724 | 0.2926 | 0.8726 | 0.4672 |
| Analytical Purposes | ABC | full | 0.5760 | 0.2756 | 0.3005 | 0.8138 | 0.2921 |
| Analytical Purposes | ABC | sufficient | 0.5737 | 0.1594 | 0.4143 | 0.8063 | 0.2885 |
| Analytical Purposes | ABC | complement | 0.5798 | 0.4598 | 0.1201 | 0.7049 | 0.1775 |
| Analytical Purposes | LBC | full | 0.5812 | 0.2978 | 0.2835 | 0.8024 | 0.2756 |
| Analytical Purposes | LBC | sufficient | 0.5298 | 0.1449 | 0.3849 | 0.7907 | 0.3299 |
| Analytical Purposes | LBC | complement | 0.6628 | 0.5402 | 0.1226 | 0.7500 | 0.1162 |
| Analytical Purposes | ALC | full | 0.6131 | 0.3111 | 0.3020 | 0.8168 | 0.2494 |
| Analytical Purposes | ALC | sufficient | 0.5624 | 0.1594 | 0.4030 | 0.8058 | 0.3021 |
| Analytical Purposes | ALC | complement | 0.6935 | 0.5517 | 0.1418 | 0.7550 | 0.0815 |
| Analytical Purposes | ABL | full | 0.5205 | 0.1244 | 0.3960 | 0.8102 | 0.3575 |
| Analytical Purposes | ABL | sufficient | 0.4783 | 0.0145 | 0.4638 | 0.7925 | 0.3965 |
| Analytical Purposes | ABL | complement | 0.5875 | 0.2989 | 0.2886 | 0.7974 | 0.2633 |

## SSC1T010 — Arithmetic audit of each contrast

alpha_strict − alpha_full = (DoU_full − DoU_strict)/De_full + (DoS_full − DoS_strict)/De_full + Do_strict(1/De_full − 1/De_strict). Delta rows are the replacement panel's terms minus ABC's. Order-dependent arithmetic, not causal attribution.

| Dimension | Contrast | U term | S term | De term | Total |
|---|---|---|---|---|---|
| Research Domains | alpha_ABC | +0.0849 | −0.0383 | −0.0067 | +0.0400 |
| Research Domains | alpha_LBC | +0.0860 | −0.0083 | −0.0064 | +0.0713 |
| Research Domains | alpha_ALC | +0.0880 | −0.0027 | −0.0053 | +0.0801 |
| Research Domains | alpha_ABL | +0.0711 | +0.0014 | −0.0064 | +0.0661 |
| Research Domains | delta_A | +0.0010 | +0.0300 | +0.0003 | +0.0313 |
| Research Domains | delta_B | +0.0031 | +0.0355 | +0.0014 | +0.0401 |
| Research Domains | delta_C | −0.0138 | +0.0397 | +0.0003 | +0.0261 |
| Research Domains | delta_min | +0.0031 | +0.0355 | +0.0014 | +0.0401 |
| Analytical Purposes | alpha_ABC | +0.1427 | −0.1398 | −0.0065 | −0.0036 |
| Analytical Purposes | alpha_LBC | +0.1905 | −0.1264 | −0.0098 | +0.0543 |
| Analytical Purposes | alpha_ALC | +0.1857 | −0.1237 | −0.0094 | +0.0527 |
| Analytical Purposes | alpha_ABL | +0.1357 | −0.0836 | −0.0132 | +0.0389 |
| Analytical Purposes | delta_A | +0.0478 | +0.0134 | −0.0033 | +0.0579 |
| Analytical Purposes | delta_B | +0.0430 | +0.0161 | −0.0029 | +0.0563 |
| Analytical Purposes | delta_C | −0.0070 | +0.0562 | −0.0067 | +0.0425 |
| Analytical Purposes | delta_min | +0.0430 | +0.0161 | −0.0029 | +0.0563 |

## SSC1T011 — Comparison with the deleted 13 November run

48 of 48 target items reproduce exactly (bootstrap at four decimal places, alpha at six, counts exactly).

## SSC1T012 — Coder abstention by the coder's own sufficiency rating (caveat 1)

| Dimension | Coder | Unclear-only when own rating Sufficient | Unclear-only when own rating not Sufficient |
|---|---|---|---|
| Research Domains | C01 | 0/107 (0%) | 7/43 (16%) |
| Research Domains | C02 | 2/96 (2%) | 12/54 (22%) |
| Research Domains | C03 | 0/59 (0%) | 39/91 (43%) |
| Analytical Purposes | C01 | 1/107 (1%) | 22/43 (51%) |
| Analytical Purposes | C02 | 1/96 (1%) | 14/54 (26%) |
| Analytical Purposes | C03 | 0/59 (0%) | 68/91 (75%) |

## Suggested manuscript tables (not applied)

### Compact bootstrap table

Strict register-sufficient subset (n = 92) minus full random baseline (n = 150); paired record bootstrap, 10,000 resamples; 95% percentile intervals. Post hoc. delta_min equals delta_B at the point estimate. The subset is defined by the coders' own sufficiency ratings, which track their own abstention, and the coders are held fixed; see the caveats above.

| Quantity | Research Domains | Analytical Purposes |
|---|---|---|
| Human-only alpha (C01, C02, C03) | +0.040 [−0.009, +0.087] | −0.004 [−0.055, +0.047] |
| delta_A (Fable 5 replaces C01) | +0.031 [−0.005, +0.070] | +0.058 [+0.018, +0.102] |
| delta_B (Fable 5 replaces C02) | +0.040 [+0.009, +0.074] | +0.056 [+0.017, +0.098] |
| delta_C (Fable 5 replaces C03) | +0.026 [−0.013, +0.065] | +0.043 [−0.009, +0.094] |
| delta_min | +0.040 [+0.007, +0.070] | +0.056 [+0.016, +0.095] |

### Small diagnostic table

Pair comparisons pooled over three pairs per family (3N; not independent). Sufficient subset (92 records) / complement (58 records).

| Dimension | Pairs | One rater Unclear-only, other substantive | Different substantive sets, of comparisons where both classify |
|---|---|---|---|
| Research Domains | human-human | 11% / 30% | 96/245 (39%) / 42/104 (40%) |
| Research Domains | model-human | 6% / 24% | 83/260 (32%) / 59/130 (45%) |
| Analytical Purposes | human-human | 16% / 46% | 124/232 (53%) / 24/50 (48%) |
| Analytical Purposes | model-human | 8% / 47% | 125/254 (49%) / 42/90 (47%) |

