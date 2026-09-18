# Enrichment calibration exploratory results

Generated: 2026-09-18T12:37:24Z

Population: baseline only (n = 150).

Exposure: dimension-matched cross-model disagreement (Fable 5 vs GPT-5.5).

## ECT001 — Baseline frame membership

| Stratum | n |
|---|---|
| domain_only | 20 |
| purpose_only | 20 |
| both | 11 |
| none | 99 |
| **Total disagreement** | **51** |
| **Total** | **150** |

## ECT002 — Alpha comparison — Research Domains

Dimension-matched exposure: domains disagreement (n exposed = 31, n unexposed = 119).

| Group | n | α ABC (MASI) | 95% CI |
|---|---|---|---|
| Full baseline | 150 | 0.5263 | [0.4635, 0.5827] |
| Exposed | 31 | 0.3680 | [0.2475, 0.4642] |
| Unexposed | 119 | 0.5641 | [0.4931, 0.6305] |
| **Δα (exposed − unexposed)** | — | **-0.1961** | **[-0.3369, -0.0799]** |

## ECT003 — Human-human pairwise Jaccard — Research Domains

Mean of per-record mean pairwise Jaccard: J(A,B), J(A,C), J(B,C).

| Group | n | Mean | 95% CI |
|---|---|---|---|
| Exposed | 31 | 0.5057 | [0.4120, 0.6030] |
| Unexposed | 119 | 0.6667 | [0.6091, 0.7236] |

## ECT004 — Human difficulty indicators — Research Domains

| Indicator | Group | n | Count | Rate | 95% CI |
|---|---|---|---|---|---|
| Unclear-only (S3) | Exposed | 31 | 6 | 0.1935 | [0.0645, 0.3448] |
| Unclear-only (S3) | Unexposed | 119 | 7 | 0.0588 | [0.0169, 0.1043] |
| No agreed label (S4) | Exposed | 31 | 1 | 0.0323 | [0.0000, 0.1071] |
| No agreed label (S4) | Unexposed | 119 | 4 | 0.0336 | [0.0081, 0.0690] |

## ECT005 — Consensus-state distribution — Research Domains

| State | Exposed n | Exposed prop | Exposed 95% CI | Unexposed n | Unexposed prop | Unexposed 95% CI |
|---|---|---|---|---|---|---|
| S1 | 2 | 0.0645 | [0.0000, 0.1667] | 48 | 0.4034 | [0.3140, 0.4917] |
| S2 | 22 | 0.7097 | [0.5405, 0.8636] | 60 | 0.5042 | [0.4107, 0.5948] |
| S3 | 6 | 0.1935 | [0.0645, 0.3448] | 7 | 0.0588 | [0.0169, 0.1043] |
| S4 | 1 | 0.0323 | [0.0000, 0.1071] | 4 | 0.0336 | [0.0081, 0.0690] |
| **Total** | **31** | — | — | **119** | — | — |

## ECT006 — Model-coder Jaccard (secondary) — Research Domains

Mean of per-record mean model-coder Jaccard: J(M,A), J(M,B), J(M,C). Secondary outcome.

| Group | n | Mean | 95% CI |
|---|---|---|---|
| Exposed | 31 | 0.4785 | [0.3754, 0.5800] |
| Unexposed | 119 | 0.7395 | [0.6887, 0.7861] |

## ECT007 — Alpha comparison — Analytical Purposes

Dimension-matched exposure: purposes disagreement (n exposed = 31, n unexposed = 119).

| Group | n | α ABC (MASI) | 95% CI |
|---|---|---|---|
| Full baseline | 150 | 0.2921 | [0.2266, 0.3570] |
| Exposed | 31 | 0.2624 | [0.1172, 0.3976] |
| Unexposed | 119 | 0.2945 | [0.2213, 0.3679] |
| **Δα (exposed − unexposed)** | — | **-0.0321** | **[-0.1983, 0.1195]** |

## ECT008 — Human-human pairwise Jaccard — Analytical Purposes

Mean of per-record mean pairwise Jaccard: J(A,B), J(A,C), J(B,C).

| Group | n | Mean | 95% CI |
|---|---|---|---|
| Exposed | 31 | 0.4337 | [0.3162, 0.5580] |
| Unexposed | 119 | 0.4398 | [0.3794, 0.5055] |

## ECT009 — Human difficulty indicators — Analytical Purposes

| Indicator | Group | n | Count | Rate | 95% CI |
|---|---|---|---|---|---|
| Unclear-only (S3) | Exposed | 31 | 8 | 0.2581 | [0.1111, 0.4194] |
| Unclear-only (S3) | Unexposed | 119 | 18 | 0.1513 | [0.0917, 0.2185] |
| No agreed label (S4) | Exposed | 31 | 6 | 0.1935 | [0.0666, 0.3333] |
| No agreed label (S4) | Unexposed | 119 | 18 | 0.1513 | [0.0893, 0.2131] |

## ECT010 — Consensus-state distribution — Analytical Purposes

| State | Exposed n | Exposed prop | Exposed 95% CI | Unexposed n | Unexposed prop | Unexposed 95% CI |
|---|---|---|---|---|---|---|
| S1 | 4 | 0.1290 | [0.0303, 0.2667] | 23 | 0.1933 | [0.1250, 0.2667] |
| S2 | 13 | 0.4194 | [0.2400, 0.5926] | 60 | 0.5042 | [0.4180, 0.5935] |
| S3 | 8 | 0.2581 | [0.1111, 0.4194] | 18 | 0.1513 | [0.0917, 0.2185] |
| S4 | 6 | 0.1935 | [0.0666, 0.3333] | 18 | 0.1513 | [0.0893, 0.2131] |
| **Total** | **31** | — | — | **119** | — | — |

## ECT011 — Model-coder Jaccard (secondary) — Analytical Purposes

Mean of per-record mean model-coder Jaccard: J(M,A), J(M,B), J(M,C). Secondary outcome.

| Group | n | Mean | 95% CI |
|---|---|---|---|
| Exposed | 31 | 0.2706 | [0.1667, 0.3832] |
| Unexposed | 119 | 0.4935 | [0.4365, 0.5497] |
