# Hard-case sampling-strata diagnostic

> Post hoc diagnostic analysis of the preregistered 75-record hard-case sample. The three 25-record strata were selected using prior cross-model disagreement and are deliberately non-representative. Results below assess whether that sampling signal corresponded to lower subsequent Fable/scratch-coder agreement in the intended dimension.

## Pair-averaged model–coder comparison

| Stratum | Domain exact-set | Domain Jaccard | Purpose exact-set | Purpose Jaccard |
|---|---:|---:|---:|---:|
| domain_only | 0.213 | 0.458 | 0.320 | 0.413 |
| purpose_only | 0.640 | 0.760 | 0.147 | 0.284 |
| both | 0.253 | 0.490 | 0.213 | 0.280 |

Positive Domain-minus-Purpose contrasts indicate higher Domain agreement; negative contrasts indicate lower Domain agreement.
- domain_only: exact-set -0.107; Jaccard 0.044.
- purpose_only: exact-set 0.493; Jaccard 0.476.
- both: exact-set 0.040; Jaccard 0.210.

Across-stratum descriptive contrasts (first minus second; no hypothesis tests):
- Domain domain_only minus purpose_only: exact-set -0.427; Jaccard -0.302.
- Domain domain_only minus both: exact-set -0.040; Jaccard -0.032.
- Domain purpose_only minus both: exact-set 0.387; Jaccard 0.270.
- Purpose domain_only minus purpose_only: exact-set 0.173; Jaccard 0.129.
- Purpose domain_only minus both: exact-set 0.107; Jaccard 0.133.
- Purpose purpose_only minus both: exact-set -0.067; Jaccard 0.004.

## Human–human context

| Stratum | Domain exact-set | Domain Jaccard | Purpose exact-set | Purpose Jaccard |
|---|---:|---:|---:|---:|
| domain_only | 0.253 | 0.463 | 0.440 | 0.453 |
| purpose_only | 0.493 | 0.663 | 0.400 | 0.427 |
| both | 0.507 | 0.613 | 0.400 | 0.440 |

## Full model–coder results

| Stratum | Dimension | Pair | Exact-set [95% CI] | Mean Jaccard [95% CI] |
|---|---|---|---:|---:|
| domain_only | Research Domains | L-A | 0.160 [0.040, 0.320] | 0.473 [0.357, 0.593] |
| domain_only | Research Domains | L-B | 0.280 [0.120, 0.480] | 0.497 [0.353, 0.643] |
| domain_only | Research Domains | L-C | 0.200 [0.040, 0.360] | 0.403 [0.263, 0.550] |
| domain_only | Analytical Purposes | L-A | 0.280 [0.120, 0.441] | 0.400 [0.240, 0.560] |
| domain_only | Analytical Purposes | L-B | 0.440 [0.240, 0.640] | 0.540 [0.380, 0.720] |
| domain_only | Analytical Purposes | L-C | 0.240 [0.080, 0.400] | 0.300 [0.140, 0.480] |
| purpose_only | Research Domains | L-A | 0.600 [0.400, 0.800] | 0.760 [0.627, 0.873] |
| purpose_only | Research Domains | L-B | 0.640 [0.440, 0.800] | 0.733 [0.580, 0.873] |
| purpose_only | Research Domains | L-C | 0.680 [0.480, 0.840] | 0.787 [0.647, 0.907] |
| purpose_only | Analytical Purposes | L-A | 0.080 [0.000, 0.200] | 0.213 [0.100, 0.340] |
| purpose_only | Analytical Purposes | L-B | 0.120 [0.000, 0.240] | 0.280 [0.140, 0.420] |
| purpose_only | Analytical Purposes | L-C | 0.240 [0.080, 0.400] | 0.360 [0.200, 0.520] |
| both | Research Domains | L-A | 0.240 [0.080, 0.400] | 0.517 [0.390, 0.643] |
| both | Research Domains | L-B | 0.280 [0.120, 0.440] | 0.500 [0.360, 0.640] |
| both | Research Domains | L-C | 0.240 [0.080, 0.400] | 0.453 [0.300, 0.600] |
| both | Analytical Purposes | L-A | 0.280 [0.120, 0.480] | 0.360 [0.200, 0.520] |
| both | Analytical Purposes | L-B | 0.320 [0.160, 0.520] | 0.380 [0.220, 0.560] |
| both | Analytical Purposes | L-C | 0.040 [0.000, 0.120] | 0.100 [0.020, 0.200] |

## Replacement-panel diagnostic

POST HOC / DIAGNOSTIC / N=25 PER STRATUM. No baseline mechanical review triggers are applied.

| Stratum | Dimension | Human α | Replace A | Replace B | Replace C | Δmin [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| domain_only | Research Domains | 0.316 | 0.287 | 0.284 | 0.306 | -0.031 [-0.133, 0.014] |
| domain_only | Analytical Purposes | 0.316 | 0.272 | 0.212 | 0.366 | -0.105 [-0.210, -0.016] |
| purpose_only | Research Domains | 0.533 | 0.627 | 0.627 | 0.600 | 0.067 [-0.026, 0.114] |
| purpose_only | Analytical Purposes | 0.298 | 0.164 | 0.200 | 0.130 | -0.168 [-0.293, -0.078] |
| both | Research Domains | 0.520 | 0.388 | 0.406 | 0.383 | -0.137 [-0.251, -0.057] |
| both | Analytical Purposes | 0.230 | 0.076 | 0.099 | 0.263 | -0.154 [-0.269, -0.063] |

## Interpretation

The results are descriptive only. The stratum labels describe the prior cross-model disagreement selection mechanism, not true errors or a gold standard. No classifier release decision, population-performance inference, per-label analysis, or adjudication follows from this diagnostic.
