# Exploratory pairwise Krippendorff's α — results

Status: exploratory, not preregistered (addendum `a049c79`, `ADDENDUM_pairwise_alpha.md`). Dates: specified, and instruction issued, on or before 17 September 2026 (investigator-attested); addendum created 2026-09-17; run 2026-09-17T14:23:26.197909+00:00.

Coders: A = C01, B = C02, C = C03, L = Fable 5 (MOD-006). δ_A = α_LBC − α_ABC, δ_B = α_ALC − α_ABC, δ_C = α_ABL − α_ABC.

Confidence level: 95%. Intervals: joint record-level bootstrap per population × dimension (all four raters' labels kept together per record), 2000 requested replicates, seed 20260917, Type-7 percentile bounds; no interval is reported for a quantity with fewer than 1800 valid replicates; undefined replicates are excluded, not replaced.

D_X is a descriptive comparison, not a decomposition of δ_X. Orderings are ascending (smallest first); `=` marks an exact tie. Estimates are shown to 4 decimal places; each table's CSV holds full precision.

Hard-case tables are labelled **DIAGNOSTIC — non-representative**. Baseline and hard-case are never pooled.

## Check W — wiring

| Population | Dimension | Panel | Computed (repr) | Canonical exported (repr) | Exact | Role |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | Research Domains | ABC | 0.5263372741925532 | 0.5263372741925532 | yes | check_W |
| baseline | Research Domains | LBC | 0.5833854979981307 | 0.5833854979981307 | yes | supplementary_model_data_integrity |
| baseline | Research Domains | ALC | 0.5279824870301835 | 0.5279824870301835 | yes | supplementary_model_data_integrity |
| baseline | Research Domains | ABL | 0.5735239672738957 | 0.5735239672738957 | yes | supplementary_model_data_integrity |
| baseline | Analytical Purposes | ABC | 0.2921101465494055 | 0.2921101465494055 | yes | check_W |
| baseline | Analytical Purposes | LBC | 0.27561685370002553 | 0.27561685370002553 | yes | supplementary_model_data_integrity |
| baseline | Analytical Purposes | ALC | 0.24944189515977 | 0.24944189515977 | yes | supplementary_model_data_integrity |
| baseline | Analytical Purposes | ABL | 0.35754042811994313 | 0.35754042811994313 | yes | supplementary_model_data_integrity |
| baseline | Demographic disparities / equity | ABC | 0.5124552887072049 | 0.5124552887072049 | yes | check_W |
| baseline | Demographic disparities / equity | LBC | 0.46846749892380535 | 0.46846749892380535 | yes | supplementary_model_data_integrity |
| baseline | Demographic disparities / equity | ALC | 0.43107544480228077 | 0.43107544480228077 | yes | supplementary_model_data_integrity |
| baseline | Demographic disparities / equity | ABL | 0.45243902439024386 | 0.45243902439024386 | yes | supplementary_model_data_integrity |
| baseline | COVID-19 & Pandemic | ABC | 0.9397477187332259 | 0.9397477187332259 | yes | check_W |
| baseline | COVID-19 & Pandemic | LBC | 0.9397477187332259 | 0.9397477187332259 | yes | supplementary_model_data_integrity |
| baseline | COVID-19 & Pandemic | ALC | 0.9412342124206531 | 0.9412342124206531 | yes | supplementary_model_data_integrity |
| baseline | COVID-19 & Pandemic | ABL | 0.971320899335718 | 0.971320899335718 | yes | supplementary_model_data_integrity |
| hard_case | Research Domains | ABC | 0.46228781652079254 | 0.46228781652079254 | yes | check_W |
| hard_case | Research Domains | LBC | 0.4386641380008872 | 0.4386641380008872 | yes | supplementary_model_data_integrity |
| hard_case | Research Domains | ALC | 0.4429465414674122 | 0.4429465414674122 | yes | supplementary_model_data_integrity |
| hard_case | Research Domains | ABL | 0.4348981730590701 | 0.4348981730590701 | yes | supplementary_model_data_integrity |
| hard_case | Analytical Purposes | ABC | 0.29174237392340174 | 0.29174237392340174 | yes | check_W |
| hard_case | Analytical Purposes | LBC | 0.18259925261107035 | 0.18259925261107035 | yes | supplementary_model_data_integrity |
| hard_case | Analytical Purposes | ALC | 0.17791957263688996 | 0.17791957263688996 | yes | supplementary_model_data_integrity |
| hard_case | Analytical Purposes | ABL | 0.2556179923215066 | 0.2556179923215066 | yes | supplementary_model_data_integrity |
| hard_case | Demographic disparities / equity | ABC | 0.653652879783533 | 0.653652879783533 | yes | check_W |
| hard_case | Demographic disparities / equity | LBC | 0.5390946502057612 | 0.5390946502057612 | yes | supplementary_model_data_integrity |
| hard_case | Demographic disparities / equity | ALC | 0.5670660997294164 | 0.5670660997294164 | yes | supplementary_model_data_integrity |
| hard_case | Demographic disparities / equity | ABL | 0.5660783469651314 | 0.5660783469651314 | yes | supplementary_model_data_integrity |
| hard_case | COVID-19 & Pandemic | ABC | 0.8099547511312217 | 0.8099547511312217 | yes | check_W |
| hard_case | COVID-19 & Pandemic | LBC | 0.8660287081339713 | 0.8660287081339713 | yes | supplementary_model_data_integrity |
| hard_case | COVID-19 & Pandemic | ALC | 0.942769545222279 | 0.942769545222279 | yes | supplementary_model_data_integrity |
| hard_case | COVID-19 & Pandemic | ABL | 0.8099547511312217 | 0.8099547511312217 | yes | supplementary_model_data_integrity |

## PWA1T001 — baseline · Research Domains (MASI) · Analysis 1 — Pairwise α among humans

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.5209 | defined | 0.4435 | 0.5935 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.4385 | defined | 0.3597 | 0.5099 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.6181 | defined | 0.5276 | 0.6926 | reported | 2000 / 0 / 2000 |

## PWA1T002 — baseline · Research Domains (MASI) · Analysis 2 — Pairwise α between Fable 5 and each human

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.6063 | defined | 0.5309 | 0.6766 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.5934 | defined | 0.5185 | 0.6650 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.5350 | defined | 0.4516 | 0.6142 | reported | 2000 / 0 / 2000 |

## PWA1T003 — baseline · Research Domains (MASI) · Analysis 3 — Differences between human pairs

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | -0.0824 | defined | -0.1559 | -0.0140 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | -0.1797 | defined | -0.2590 | -0.0967 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | -0.0972 | defined | -0.1916 | 0.0067 | reported | 2000 / 0 / 2000 |

## PWA1T004 — baseline · Research Domains (MASI) · Analysis 4 — Replacement comparison per coder

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.4797 | defined | 0.4123 | 0.5440 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.5642 | defined | 0.4968 | 0.6338 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | 0.0845 | defined | 0.0192 | 0.1543 | reported | 2000 / 0 / 2000 | 0.0570 |
| H_B = mean(α(A,B), α(B,C)) | 0.5695 | defined | 0.5048 | 0.6276 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.5706 | defined | 0.5096 | 0.6297 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | 0.0011 | defined | -0.0538 | 0.0576 | reported | 2000 / 0 / 2000 | 0.0016 |
| H_C = mean(α(A,C), α(B,C)) | 0.5283 | defined | 0.4555 | 0.5924 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.5998 | defined | 0.5395 | 0.6575 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | 0.0715 | defined | 0.0048 | 0.1377 | reported | 2000 / 0 / 2000 | 0.0472 |

Ordering of D (ascending): B < C < A. Ordering of exported δ point estimates (ascending): B < C < A. Orderings agree: yes.

## PWA1T005 — baseline · Analytical Purposes (MASI) · Analysis 1 — Pairwise α among humans

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.3403 | defined | 0.2478 | 0.4246 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.3034 | defined | 0.2063 | 0.3986 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.2051 | defined | 0.1052 | 0.2944 | reported | 2000 / 0 / 2000 |

## PWA1T006 — baseline · Analytical Purposes (MASI) · Analysis 2 — Pairwise α between Fable 5 and each human

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.2757 | defined | 0.1873 | 0.3603 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.4546 | defined | 0.3611 | 0.5465 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.1343 | defined | 0.0407 | 0.2278 | reported | 2000 / 0 / 2000 |

## PWA1T007 — baseline · Analytical Purposes (MASI) · Analysis 3 — Differences between human pairs

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | -0.0369 | defined | -0.1488 | 0.0872 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | 0.0983 | defined | 0.0084 | 0.2037 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | 0.1352 | defined | 0.0371 | 0.2340 | reported | 2000 / 0 / 2000 |

## PWA1T008 — baseline · Analytical Purposes (MASI) · Analysis 4 — Replacement comparison per coder

Records: 150. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.3218 | defined | 0.2460 | 0.3896 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.2944 | defined | 0.2193 | 0.3647 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | -0.0274 | defined | -0.1042 | 0.0464 | reported | 2000 / 0 / 2000 | -0.0165 |
| H_B = mean(α(A,B), α(B,C)) | 0.2727 | defined | 0.1899 | 0.3444 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.2050 | defined | 0.1234 | 0.2771 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | -0.0677 | defined | -0.1415 | 0.0071 | reported | 2000 / 0 / 2000 | -0.0427 |
| H_C = mean(α(A,C), α(B,C)) | 0.2542 | defined | 0.1715 | 0.3314 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.3651 | defined | 0.2897 | 0.4343 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | 0.1109 | defined | 0.0155 | 0.2010 | reported | 2000 / 0 / 2000 | 0.0654 |

Ordering of D (ascending): B < A < C. Ordering of exported δ point estimates (ascending): B < A < C. Orderings agree: yes.

## PWA1T009 — baseline · Demographic disparities / equity (nominal) · Analysis 1 — Pairwise α among humans

Records: 150. Records the coder majority applied the tag to (canonical export): 11. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.4386 | defined | 0.1184 | 0.7047 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.6859 | defined | 0.4421 | 0.8678 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.3915 | defined | 0.0934 | 0.6091 | reported | 2000 / 0 / 2000 |

## PWA1T010 — baseline · Demographic disparities / equity (nominal) · Analysis 2 — Pairwise α between Fable 5 and each human

Records: 150. Records the coder majority applied the tag to (canonical export): 11. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.2617 | defined | 0.0144 | 0.4838 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.6576 | defined | 0.4049 | 0.8523 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.3708 | defined | 0.1296 | 0.5906 | reported | 2000 / 0 / 2000 |

## PWA1T011 — baseline · Demographic disparities / equity (nominal) · Analysis 3 — Differences between human pairs

Records: 150. Records the coder majority applied the tag to (canonical export): 11. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | 0.2473 | defined | -0.0456 | 0.5577 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | 0.2944 | defined | 0.0349 | 0.5713 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | 0.0471 | defined | -0.1453 | 0.2164 | reported | 2000 / 0 / 2000 |

## PWA1T012 — baseline · Demographic disparities / equity (nominal) · Analysis 4 — Replacement comparison per coder

Records: 150. Records the coder majority applied the tag to (canonical export): 11. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.5623 | defined | 0.3268 | 0.7330 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.5142 | defined | 0.3069 | 0.6773 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | -0.0481 | defined | -0.2431 | 0.1530 | reported | 2000 / 0 / 2000 | -0.0440 |
| H_B = mean(α(A,B), α(B,C)) | 0.4151 | defined | 0.1135 | 0.6438 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.3163 | defined | 0.0866 | 0.5184 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | -0.0988 | defined | -0.2223 | 0.0179 | reported | 2000 / 0 / 2000 | -0.0814 |
| H_C = mean(α(A,C), α(B,C)) | 0.5387 | defined | 0.3212 | 0.7099 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.4597 | defined | 0.2319 | 0.6397 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | -0.0791 | defined | -0.2494 | 0.0881 | reported | 2000 / 0 / 2000 | -0.0600 |

Ordering of D (ascending): B < C < A. Ordering of exported δ point estimates (ascending): B < C < A. Orderings agree: yes.

## PWA1T013 — baseline · COVID-19 & Pandemic (nominal) · Analysis 1 — Pairwise α among humans

Records: 150. Records the coder majority applied the tag to (canonical export): 12. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.9565 | defined | 0.8469 | 1.0000 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.9097 | defined | 0.7644 | 1.0000 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.9531 | defined | 0.8320 | 1.0000 | reported | 2000 / 0 / 2000 |

## PWA1T014 — baseline · COVID-19 & Pandemic (nominal) · Analysis 2 — Pairwise α between Fable 5 and each human

Records: 150. Records the coder majority applied the tag to (canonical export): 12. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 1.0000 | defined | 1.0000 | 1.0000 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.9565 | defined | 0.8469 | 1.0000 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.9097 | defined | 0.7644 | 1.0000 | reported | 2000 / 0 / 2000 |

## PWA1T015 — baseline · COVID-19 & Pandemic (nominal) · Analysis 3 — Differences between human pairs

Records: 150. Records the coder majority applied the tag to (canonical export): 12. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | -0.0468 | defined | -0.1680 | 0.0000 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | -0.0433 | defined | -0.1531 | 0.0000 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | 0.0034 | defined | -0.1316 | 0.1494 | reported | 2000 / 0 / 2000 |

## PWA1T016 — baseline · COVID-19 & Pandemic (nominal) · Analysis 4 — Replacement comparison per coder

Records: 150. Records the coder majority applied the tag to (canonical export): 12. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.9331 | defined | 0.8174 | 1.0000 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.9331 | defined | 0.8174 | 1.0000 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | 0.0000 | defined | 0.0000 | 0.0000 | reported | 2000 / 0 / 2000 | 0.0000 |
| H_B = mean(α(A,B), α(B,C)) | 0.9548 | defined | 0.8810 | 1.0000 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.9549 | defined | 0.8822 | 1.0000 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | 0.0001 | defined | 0.0000 | 0.0012 | reported | 2000 / 0 / 2000 | 0.0015 |
| H_C = mean(α(A,C), α(B,C)) | 0.9314 | defined | 0.8091 | 1.0000 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.9783 | defined | 0.9235 | 1.0000 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | 0.0469 | defined | 0.0000 | 0.1680 | reported | 2000 / 0 / 2000 | 0.0316 |

Ordering of D (ascending): A < B < C. Ordering of exported δ point estimates (ascending): A < B < C. Orderings agree: yes.

## PWA1T017 — hard_case · Research Domains (MASI) · Analysis 1 — Pairwise α among humans

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.4442 | defined | 0.3402 | 0.5390 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.4891 | defined | 0.3803 | 0.5905 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.4509 | defined | 0.3347 | 0.5543 | reported | 2000 / 0 / 2000 |

## PWA1T018 — hard_case · Research Domains (MASI) · Analysis 2 — Pairwise α between Fable 5 and each human

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.4172 | defined | 0.3187 | 0.5131 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.4435 | defined | 0.3399 | 0.5469 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.4181 | defined | 0.3123 | 0.5195 | reported | 2000 / 0 / 2000 |

## PWA1T019 — hard_case · Research Domains (MASI) · Analysis 3 — Differences between human pairs

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | 0.0449 | defined | -0.0655 | 0.1514 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | 0.0382 | defined | -0.0682 | 0.1527 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | -0.0067 | defined | -0.1120 | 0.1050 | reported | 2000 / 0 / 2000 |

## PWA1T020 — hard_case · Research Domains (MASI) · Analysis 4 — Replacement comparison per coder

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.4667 | defined | 0.3781 | 0.5487 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.4308 | defined | 0.3388 | 0.5188 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | -0.0359 | defined | -0.1243 | 0.0491 | reported | 2000 / 0 / 2000 | -0.0236 |
| H_B = mean(α(A,B), α(B,C)) | 0.4476 | defined | 0.3520 | 0.5326 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.4176 | defined | 0.3270 | 0.5046 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | -0.0300 | defined | -0.1168 | 0.0592 | reported | 2000 / 0 / 2000 | -0.0193 |
| H_C = mean(α(A,C), α(B,C)) | 0.4700 | defined | 0.3747 | 0.5571 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.4304 | defined | 0.3474 | 0.5151 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | -0.0397 | defined | -0.1299 | 0.0574 | reported | 2000 / 0 / 2000 | -0.0274 |

Ordering of D (ascending): C < A < B. Ordering of exported δ point estimates (ascending): C < A < B. Orderings agree: yes.

## PWA1T021 — hard_case · Analytical Purposes (MASI) · Analysis 1 — Pairwise α among humans

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.3715 | defined | 0.2384 | 0.4991 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.2770 | defined | 0.1353 | 0.4087 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.2059 | defined | 0.0499 | 0.3451 | reported | 2000 / 0 / 2000 |

## PWA1T022 — hard_case · Analytical Purposes (MASI) · Analysis 2 — Pairwise α between Fable 5 and each human

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.1521 | defined | 0.0382 | 0.2583 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.2329 | defined | 0.1154 | 0.3451 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.0667 | defined | -0.0563 | 0.1806 | reported | 2000 / 0 / 2000 |

## PWA1T023 — hard_case · Analytical Purposes (MASI) · Analysis 3 — Differences between human pairs

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | -0.0945 | defined | -0.2711 | 0.0793 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | 0.0711 | defined | -0.0899 | 0.2218 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | 0.1655 | defined | -0.0066 | 0.3373 | reported | 2000 / 0 / 2000 |

## PWA1T024 — hard_case · Analytical Purposes (MASI) · Analysis 4 — Replacement comparison per coder

**DIAGNOSTIC — non-representative**

Records: 75. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.3242 | defined | 0.2157 | 0.4146 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.1498 | defined | 0.0550 | 0.2365 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | -0.1744 | defined | -0.2873 | -0.0631 | reported | 2000 / 0 / 2000 | -0.1091 |
| H_B = mean(α(A,B), α(B,C)) | 0.2887 | defined | 0.1762 | 0.3909 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.1094 | defined | 0.0128 | 0.1921 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | -0.1793 | defined | -0.2895 | -0.0756 | reported | 2000 / 0 / 2000 | -0.1138 |
| H_C = mean(α(A,C), α(B,C)) | 0.2415 | defined | 0.1186 | 0.3470 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.1925 | defined | 0.0898 | 0.2851 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | -0.0490 | defined | -0.1817 | 0.0913 | reported | 2000 / 0 / 2000 | -0.0361 |

Ordering of D (ascending): B < A < C. Ordering of exported δ point estimates (ascending): B < A < C. Orderings agree: yes.

## PWA1T025 — hard_case · Demographic disparities / equity (nominal) · Analysis 1 — Pairwise α among humans

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 8. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.6321 | defined | 0.2557 | 0.8854 | reported | 2000 / 0 / 2000 |
| α(A,C) | 0.7492 | defined | 0.4440 | 0.9490 | reported | 2000 / 0 / 2000 |
| α(B,C) | 0.5810 | defined | 0.2471 | 0.8352 | reported | 2000 / 0 / 2000 |

## PWA1T026 — hard_case · Demographic disparities / equity (nominal) · Analysis 2 — Pairwise α between Fable 5 and each human

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 8. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.4849 | defined | 0.1002 | 0.7793 | reported | 2000 / 0 / 2000 |
| α(L,B) | 0.5830 | defined | 0.2174 | 0.8511 | reported | 2000 / 0 / 2000 |
| α(L,C) | 0.4612 | defined | 0.1230 | 0.7250 | reported | 2000 / 0 / 2000 |

## PWA1T027 — hard_case · Demographic disparities / equity (nominal) · Analysis 3 — Differences between human pairs

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 8. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | 0.1171 | defined | -0.2062 | 0.4826 | reported | 2000 / 0 / 2000 |
| α(A,C) − α(B,C) | 0.1682 | defined | -0.1320 | 0.4815 | reported | 2000 / 0 / 2000 |
| α(A,B) − α(B,C) | 0.0511 | defined | -0.2007 | 0.2813 | reported | 2000 / 0 / 2000 |

## PWA1T028 — hard_case · Demographic disparities / equity (nominal) · Analysis 4 — Replacement comparison per coder

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 8. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.6906 | defined | 0.4053 | 0.8716 | reported | 2000 / 0 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.5221 | defined | 0.1917 | 0.7588 | reported | 2000 / 0 / 2000 |  |
| D_A = M_A − H_A | -0.1685 | defined | -0.4810 | 0.1206 | reported | 2000 / 0 / 2000 | -0.1146 |
| H_B = mean(α(A,B), α(B,C)) | 0.6065 | defined | 0.2800 | 0.8426 | reported | 2000 / 0 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.4731 | defined | 0.1331 | 0.7339 | reported | 2000 / 0 / 2000 |  |
| D_B = M_B − H_B | -0.1334 | defined | -0.4155 | 0.0918 | reported | 2000 / 0 / 2000 | -0.0866 |
| H_C = mean(α(A,C), α(B,C)) | 0.6651 | defined | 0.4105 | 0.8610 | reported | 2000 / 0 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.5340 | defined | 0.1850 | 0.7832 | reported | 2000 / 0 / 2000 |  |
| D_C = M_C − H_C | -0.1311 | defined | -0.4402 | 0.1417 | reported | 2000 / 0 / 2000 | -0.0876 |

Ordering of D (ascending): A < B < C. Ordering of exported δ point estimates (ascending): A < C < B. Orderings agree: no.

## PWA1T029 — hard_case · COVID-19 & Pandemic (nominal) · Analysis 1 — Pairwise α among humans

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 6. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,B) | 0.7077 | defined | 0.2777 | 1.0000 | reported | 1997 / 3 / 2000 |
| α(A,C) | 0.9163 | defined | 0.6551 | 1.0000 | reported | 1997 / 3 / 2000 |
| α(B,C) | 0.7871 | defined | 0.3834 | 1.0000 | reported | 1995 / 5 / 2000 |

Invalid-replicate reasons: α(A,B): expected_disagreement_zero: 3 | α(A,C): expected_disagreement_zero: 3 | α(B,C): expected_disagreement_zero: 5.

## PWA1T030 — hard_case · COVID-19 & Pandemic (nominal) · Analysis 2 — Pairwise α between Fable 5 and each human

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 6. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(L,A) | 0.9163 | defined | 0.6551 | 1.0000 | reported | 1997 / 3 / 2000 |
| α(L,B) | 0.7871 | defined | 0.3834 | 1.0000 | reported | 1995 / 5 / 2000 |
| α(L,C) | 1.0000 | defined | 1.0000 | 1.0000 | reported | 1995 / 5 / 2000 |

Invalid-replicate reasons: α(L,A): expected_disagreement_zero: 3 | α(L,B): expected_disagreement_zero: 5 | α(L,C): expected_disagreement_zero: 5.

## PWA1T031 — hard_case · COVID-19 & Pandemic (nominal) · Analysis 3 — Differences between human pairs

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 6. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested |
| --- | --- | --- | --- | --- | --- | --- |
| α(A,C) − α(A,B) | 0.2087 | defined | 0.0000 | 0.6166 | reported | 1997 / 3 / 2000 |
| α(A,C) − α(B,C) | 0.1292 | defined | -0.2510 | 0.5884 | reported | 1995 / 5 / 2000 |
| α(A,B) − α(B,C) | -0.0795 | defined | -0.3191 | 0.0000 | reported | 1995 / 5 / 2000 |

Invalid-replicate reasons: α(A,C) − α(A,B): input_undefined(alpha_AC:expected_disagreement_zero;alpha_AB:expected_disagreement_zero): 3 | α(A,C) − α(B,C): input_undefined(alpha_AC:expected_disagreement_zero;alpha_BC:expected_disagreement_zero): 3; input_undefined(alpha_BC:expected_disagreement_zero): 2 | α(A,B) − α(B,C): input_undefined(alpha_AB:expected_disagreement_zero;alpha_BC:expected_disagreement_zero): 3; input_undefined(alpha_BC:expected_disagreement_zero): 2.

## PWA1T032 — hard_case · COVID-19 & Pandemic (nominal) · Analysis 4 — Replacement comparison per coder

**DIAGNOSTIC — non-representative**

Records: 75. Records the coder majority applied the tag to (canonical export): 6. Confidence level: 95%.

| Quantity | Estimate | Estimate status | 95% CI lower | 95% CI upper | Interval status | Valid / invalid / requested | Exported δ (same X) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H_A = mean(α(A,B), α(A,C)) | 0.8120 | defined | 0.5193 | 1.0000 | reported | 1997 / 3 / 2000 |  |
| M_A = mean(α(L,B), α(L,C)) | 0.8936 | defined | 0.6917 | 1.0000 | reported | 1995 / 5 / 2000 |  |
| D_A = M_A − H_A | 0.0816 | defined | 0.0000 | 0.3357 | reported | 1995 / 5 / 2000 | 0.0561 |
| H_B = mean(α(A,B), α(B,C)) | 0.7474 | defined | 0.3196 | 1.0000 | reported | 1995 / 5 / 2000 |  |
| M_B = mean(α(L,A), α(L,C)) | 0.9582 | defined | 0.8275 | 1.0000 | reported | 1995 / 5 / 2000 |  |
| D_B = M_B − H_B | 0.2108 | defined | 0.0000 | 0.6166 | reported | 1995 / 5 / 2000 | 0.1328 |
| H_C = mean(α(A,C), α(B,C)) | 0.8517 | defined | 0.6119 | 1.0000 | reported | 1995 / 5 / 2000 |  |
| M_C = mean(α(L,A), α(L,B)) | 0.8517 | defined | 0.6119 | 1.0000 | reported | 1995 / 5 / 2000 |  |
| D_C = M_C − H_C | 0.0000 | defined | 0.0000 | 0.0000 | reported | 1995 / 5 / 2000 | 0.0000 |

Ordering of D (ascending): C < A < B. Ordering of exported δ point estimates (ascending): C < A < B. Orderings agree: yes.

Invalid-replicate reasons: H_A = mean(α(A,B), α(A,C)): input_undefined(alpha_AB:expected_disagreement_zero;alpha_AC:expected_disagreement_zero): 3 | M_A = mean(α(L,B), α(L,C)): input_undefined(alpha_LB:expected_disagreement_zero;alpha_LC:expected_disagreement_zero): 5 | D_A = M_A − H_A: input_undefined(M_A:input_undefined(alpha_LB:expected_disagreement_zero;alpha_LC:expected_disagreement_zero)): 2; input_undefined(M_A:input_undefined(alpha_LB:expected_disagreement_zero;alpha_LC:expected_disagreement_zero);H_A:input_undefined(alpha_AB:expected_disagreement_zero;alpha_AC:expected_disagreement_zero)): 3 | H_B = mean(α(A,B), α(B,C)): input_undefined(alpha_AB:expected_disagreement_zero;alpha_BC:expected_disagreement_zero): 3; input_undefined(alpha_BC:expected_disagreement_zero): 2 | M_B = mean(α(L,A), α(L,C)): input_undefined(alpha_LA:expected_disagreement_zero;alpha_LC:expected_disagreement_zero): 3; input_undefined(alpha_LC:expected_disagreement_zero): 2 | D_B = M_B − H_B: input_undefined(M_B:input_undefined(alpha_LA:expected_disagreement_zero;alpha_LC:expected_disagreement_zero);H_B:input_undefined(alpha_AB:expected_disagreement_zero;alpha_BC:expected_disagreement_zero)): 3; input_undefined(M_B:input_undefined(alpha_LC:expected_disagreement_zero);H_B:input_undefined(alpha_BC:expected_disagreement_zero)): 2 | H_C = mean(α(A,C), α(B,C)): input_undefined(alpha_AC:expected_disagreement_zero;alpha_BC:expected_disagreement_zero): 3; input_undefined(alpha_BC:expected_disagreement_zero): 2 | M_C = mean(α(L,A), α(L,B)): input_undefined(alpha_LA:expected_disagreement_zero;alpha_LB:expected_disagreement_zero): 3; input_undefined(alpha_LB:expected_disagreement_zero): 2 | D_C = M_C − H_C: input_undefined(M_C:input_undefined(alpha_LA:expected_disagreement_zero;alpha_LB:expected_disagreement_zero);H_C:input_undefined(alpha_AC:expected_disagreement_zero;alpha_BC:expected_disagreement_zero)): 3; input_undefined(M_C:input_undefined(alpha_LB:expected_disagreement_zero);H_C:input_undefined(alpha_BC:expected_disagreement_zero)): 2.
