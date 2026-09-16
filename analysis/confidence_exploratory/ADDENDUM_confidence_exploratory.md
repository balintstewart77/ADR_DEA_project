# Exploratory coder-confidence analysis addendum

Dates: specified, and instruction v5 issued, on or before 16 September 2026 (investigator-attested).

Actual addendum creation date: 16 September 2026. The execution timestamp will be recorded separately in run_metadata.json. Neither this file nor its commit is backdated.

These analyses are exploratory and were not preregistered. They were specified after the preregistered analyses were completed and reviewed.

## Investigator statements and repository findings

The investigator states that before specification no confidence agreement statistic and no confidence × sufficiency cross-tabulation had been computed. The investigator states that previously inspected confidence information was limited to exported Unclear × confidence cross-tabulations S10T001–S10T004, baseline response totals High 193, Medium 242, Low 15, and hard-case response totals High 78, Medium 139, Low 8; no other confidence summaries were inspected. These are attributed statements, not facts independently established by Codex, and must be read alongside the findings below.

Read-only searches found existing pilot confidence agreement-pattern results in preregistration/package/05_training_and_pilot/pilot_analysis/pilot_record_dimension_summary.csv (Confidence rows include all_agree_flag, two_vs_one_flag, split_flag and pairwise_exact_count). pilot_diagnostic_item_summary.csv in the same directory contains confidence frequencies and record majorities; pilot_agreement_report.md reports majority-category totals. These files entered history in commit 8b3ca1fca659e4e3dd2962ed96c25822348cdf42, whose recorded author timestamp is 2026-07-20T23:09:20+01:00. This is repository provenance, not an inferred specification date. Thus a blanket absence statement about earlier confidence results would be incorrect. These are pilot results, not a newly calculated formal-panel result.

The formal-panel taxonomy_coherence_summary.csv in analysis/outputs_validation_scratch_20260824 also contains Cannot assess × confidence summaries (S10T005–S10T006), alongside the known Unclear × confidence tables. File existence does not establish what the investigator inspected. No formal-panel confidence α result or confidence × sufficiency cross-tabulation was found in the searched text.

Search locations and method: working-tree analysis/, tests/ and preregistration/ text sources and outputs, including the canonical results.md and run_metadata.json; rg searches for confidence near alpha, agreement, sufficiency or crosstab, plus ordinal and confidence-specific identifiers; git log --all -G searches across tracked Python, Markdown, CSV and JSON history and commit-message searches for confidence. Pilot matches and their producing code were inspected. An initial all-file history search encountered unavailable PDF text conversion; it was repeated with text conversion disabled on the named text formats. This search does not establish absence outside these searched locations or inside unsearched binary documents. Under v5, these findings are recorded and do not halt the run.

## Analysis definitions

Baseline (150 records) and hard-case (75 records) are analysed separately, never pooled. Every hard-case output carries DIAGNOSTIC — non-representative. Confidence is ordered Low < Medium < High, mapped Low = 1, Medium = 2, High = 3. Source codes are decoded using the existing source labels before applying these analytical ranks.

### Analysis 1 — Coder confidence distributions

For each population and each coder C01, C02 and C03, export the count and proportion of records rated High, Medium and Low; denominators are 150 or 75 records. A record's majority confidence is the category chosen by at least two of three coders, otherwise No majority. With complete ratings, No majority means one Low, one Medium and one High. Reuse the majority rule used for S8T003 and S9T003. Majority proportions include all records in their denominator, including No majority. Export all four categories even when zero.

Baseline proportions receive 95% Wilson score intervals using the existing implementation. Hard-case proportions receive no intervals; interval status is not applied, matching S8/S9.

### Analysis 2 — Agreement on confidence

For each population compute only Krippendorff's ordinal α among the three human coders; Fable 5 gave no confidence ratings. Reuse the existing α estimator and record bootstrap. Each sampled record carries all three ratings, and repeated sampled records remain separate units. Attempt 2,000 replicates, with seed 20260915 and a 95% percentile interval. The existing rule requires 1,800 valid replicates (90%); bounds are the Type-7 2.5th and 97.5th percentiles of valid estimates. Undefined or non-finite replicates remain invalid, without rescue, redraw, replacement or top-up. Withhold bounds below the threshold and export the interval status and counts in either case.

The bootstrap must be attempted for both populations. The hard-case interval and status carry DIAGNOSTIC — non-representative and do not establish representativeness. Analysis 1's no-interval rule applies only to its hard-case proportions.

Export α, interval bounds, confidence level, seed, valid/invalid/requested replicate counts, valid-replicate threshold, interval status, and observed and expected disagreement. Also export the number of records with three identical confidence ratings, as a count only, without an interval. No nominal α, weighted κ, pairwise statistics or alternative agreement measures are computed on real data.

The sole authorised new estimator logic is a local ordinal distance function. For ordered ranks c < k, squared disagreement is (sum of n_g from c through k minus (n_c+n_k)/2) squared, with zero diagonal and symmetry. n_g counts values from units containing at least two nonmissing ratings in the data passed to that call. The bootstrap evaluator rebuilds this distance from each replicate's own frequencies, including zeros for absent categories, before calling the unchanged estimator. analysis/validation/alpha.py lines 38–42 identify pairable values, lines 49–54 weight ordered within-unit pairs by 1/(m_u−1), and lines 58–64 form expected disagreement from pooled ordered pairs. Lines 50 and 59 consume the supplied squared disagreement directly as float, without another square. Distances receive the original category values (analytical integer ranks here), not marginal counts. Exact arithmetic is used to construct distance values, then the existing estimator's float arithmetic is retained.

Before real-data use, validation must pass invariants, nominal-distance wiring and per-replicate recomputation, plus at least one external route: a published worked example or an independent implementation on at least 20 synthetic three-rater datasets. Both external routes will be attempted where feasible. An executed validation failure halts the run.

### Analysis 3 — Confidence against register-entry sufficiency

For each population, at coder–record response level, export all nine cells of confidence (High, Medium, Low) × sufficiency (Sufficient, Partially sufficient, Insufficient), including zeros. Export counts and row proportions within confidence. A zero-total confidence row retains zero counts and undefined row proportions with explicit status. No intervals, test statistic or association measure. Missing or unexpected values must fail the source checks, never be silently dropped, imputed or recoded.

## Sequence, history and scope

Bootstrap seed: 20260915, as specified in instruction v5.

Ordinal α was specified from v1. The v2 attempt stopped at precondition 3 before an addendum or analysis because shared code had no ordinal distance; nothing was changed, committed or computed. v3 introduced authorisation for a new ordinal distance function to be validated before use, rather than an implemented or executed function. v4 revised validation and interface requirements; its attempt stopped at unfilled date placeholders before any step. v5 filled the dates. The metric choice did not change.

This addendum is committed alone before analysis code. Code and published/synthetic validation precede a code commit; real-data checks and analyses follow that commit. A code defect at D–F requires applicable validation tests, a new fix commit, discarding the prior execution and restarting at D. Final files derive from one complete execution using final committed code. Group 2 failure after one rerun is a hard stop. Source-integrity and Group 1 failures are hard stops. No canonical artefact or figure-pipeline file is edited.

These analyses describe differences in confidence distributions between coders and agreement on confidence for the same records. They do not partition coder and record effects and do not establish a record-level definition of low-confidence human cases for the release decision rule. No claims about the quality or reliability of any named coder are made.

Excluded: any agreement or replacement analysis stratified by confidence. Such an analysis requires a separate dated addendum committed before it is run.
