# Specification — Exploratory: GPT-5.5, Fable 5 and three coders (GHA1)

## Dates and status

- Instruction received and specification written: 17 November 2026. Not backdated.
- Written after the analysis code was planned and before any new GHA1 quantity was calculated. Not committed before the run (investigator instruction: no commits); its SHA-256 is recorded in the run metadata.
- **Post hoc and exploratory, not preregistered.** The production-model (Fable 5) validation results, the pairwise-α results (PWA1), the consensus-state results (CST1), the enrichment calibration and the full-register Fable 5 replicate (FPR1) had all been inspected before this specification. Cross-model agreement on the full register (81% domains, 85% purposes) was also known. This is not a retrospective preregistration.
- The preregistered validation of the production model remains primary. Agreement is not accuracy; a human consensus is not an adjudicated reference.

## Questions

1. How does each model (Fable 5, the production model; GPT-5.5, the archived comparison model) agree with each of the three coders in the random baseline and in the enriched hard-case sample?
2. When the models disagree on a dimension, do the coders converge on one model's set, split between them, or give other sets?
3. Are these patterns associated with the dimension of model disagreement, the coders' record-majority sufficiency rating, or their record-majority taxonomy-fit rating?

## Sources and identities

| Source | Authority | Notes |
|---|---|---|
| Coders C01, C02, C03 | POST-028 frozen REDCap export, joined through POST-019, validated with the frozen validator as in Stage A | complete and structurally valid responses only |
| Fable 5 (production; `claude-fable-5`) | MOD-006 `layer_classifications.csv`; identity from MOD-011 production release manifest | labels as used in Stage A |
| GPT-5.5 (archived comparison) | EVD-005 `gpt55_classifications.csv`, hash checked against the manifest | valid only where `gpt_status` is `ok`, `validation_error` is empty and every label is an rc2 label of that layer |
| Samples | POST-009 (baseline, 150) and POST-011 (hard case, 75, with `hard_case_stratum`) | active rows only; reserves are never read |

GPT-5.5 received the production prompt without model-specific adaptation, so conclusions concern these frozen pipelines, not each model's best achievable performance. Tags are out of scope.

## Populations and data rules

- Baseline and hard-case samples are always analysed separately. No headline pools the 225 records.
- Hard-case strata (domain_only, purpose_only, both; 25 each) are taken from POST-011, never re-derived. Whether the two frozen outputs differ on each dimension is also computed from MOD-006 and EVD-005 and checked against the strata; any mismatch is logged, and the recorded strata are kept.
- Label sets are unordered; Unclear from Register Entry is an ordinary label. A missing or invalid classification is missing, never an empty set or Unclear.
- For each population and dimension, direct comparisons use the complete-case intersection of valid ratings from all five sources. If it differs from Stage A's population, Stage A results are also reproduced on their own population.

## Reproduction first

Before any new quantity: reproduce Stage A's α_ABC and the three Fable replacement α on the original populations (checkpoints from the instruction, compared to 1e-6), and the Stage A baseline intervals with Stage A's own resampling stream. Audit the hard-case stratum fields `mean_model_coder_exact_set` and `mean_model_coder_jaccard` against raw ratings. Discrepancies go to a discrepancy log; historical files are not changed.

## Quantities

- **Pairwise (descriptive):** for all ten pairs of the five sources, denominator, exact-set count and proportion, and mean Jaccard; 5×5 matrices with one source order and one colour scale. Per hard-case stratum: point estimates only. Model–model disagreement in the hard cases is guaranteed by selection and is not a finding.
- **Replacement:** α_ABC; for each model, α with the model replacing C01, C02 and C03 in turn; δ = replacement α − α_ABC; each model's δ_min with all components shown.
- **Direct contrasts:** for each replaced coder, α(GPT-5.5 panel) − α(Fable 5 panel), with the same two retained coders. A positive contrast means higher agreement for that GPT-5.5 panel on these records, not higher accuracy. The two models' δ_min are not contrasted, because they need not arise from the same substitution. No equivalence margin, winner threshold or release criterion is introduced.
- **Context:** label frequencies and mean set sizes by source.
- **Record level** (restricted): one row per record and dimension with the five sets, stratum, model agreement, coder unanimity, and each coder's exact match and Jaccard with each model. Where the models differ on the dimension, exactly one of seven patterns: coders unanimous and matching Fable 5; unanimous and matching GPT-5.5; unanimous on a third set; not unanimous with an exact match to each model; Fable 5 only; GPT-5.5 only; no exact match to either. Patterns are agreement patterns, not correctness verdicts.
- **Cross-tabulations:** patterns by population, dimension and stratum, and against the record-majority sufficiency and taxonomy-fit ratings (two identical ratings, otherwise split; Cannot assess kept apart from No Fit). Counts and denominators; no tests; no inference about causes.

## Uncertainty

- 2,000 paired record-level bootstrap draws, seed 20260714, percentile endpoints at 2.5 and 97.5 with Hyndman–Fan Type 7 interpolation, for α, δ, δ_min and the direct contrasts. All five ratings of a record stay together, and every compared panel and both models use the same drawn records.
- Baseline: records resampled with Stage A's generator (Python `Random(20260714)`, records in Record-ID order), so Fable intervals on an unchanged population reproduce Stage A's.
- Hard cases: resampled within each recorded stratum at its observed size (25), strata drawn in the order domain_only, purpose_only, both, from one `Random(20260714)` stream. These are exploratory conditional intervals for the selected case mix, not design-based intervals for the disagreement frame or the register, and they ignore the forced inclusion of accompanying-tag disagreements.
- A statistic is undefined in a draw if α is undefined; a contrast uses draws where both components are defined. Valid and invalid counts are reported, and an interval is suppressed below 90% valid draws (1,800). No multiplicity adjustment; intervals are descriptive.
- Stratum-level (n = 25) results and pattern tables are point estimates only.
- Intervals condition on these three coders and these frozen outputs; they do not cover other coders, prompts, reruns or model versions.

## Departures from the instruction (agreed review, 17 November 2026)

1. **Record-level outputs are restricted.** The record-level diagnostic file (Record IDs, hard-case strata, coder label sets) is written under `preregistration_restricted/` (gitignored), because the sample allocations and the coder export are restricted and secondary adjudication is in progress: source-attributed labels by record must not reach the secondary adjudicator before their Stage 1 is complete. Revised the same day at the investigator's instruction: no results are kept in the repository, so aggregate outputs, figures and the report are also written to the gitignored `preregistration_restricted/exploratory_gpt55_human_agreement_<UTC>/`, with the record-level file in its `record_level/` subfolder; the repository holds code and this plan only.
2. **Naming.** Analysis ID GHA1; tables GHA1T001 onwards, following the repository's exploratory convention; this file is the dated plan.
3. **Baseline resampling stream** is Stage A's, as above, so the reproduction extends to intervals.
4. **Model divergence** is computed from the frozen outputs and checked against the recorded strata rather than assumed.
5. **GPT-5.5 validity** is defined as above; the purpose cardinality rule (one or two purposes, or Unclear alone) is checked and violations are counted as invalid.

## Checks (hard stops unless stated)

Authority and EVD-005 hashes; 150/75 and 25/25/25 counts; unique Record IDs and one-to-one joins; title and dataset text identical between MOD-006 and EVD-005 for every active record; Stage A point estimates reproduced to 1e-6; pairwise results symmetric and invariant to label order; identical model outputs give zero contrasts; every divergent record-dimension assigned exactly one pattern; `git diff --check` clean for the new module.

## Exclusions

No model API calls; no reruns; no change to prompts, taxonomy, labels, protocol, release pointers, frozen outputs, samples, exports or adjudication material; no reserve data; no full-register enumeration beyond the active joins; no adjudication or owner material read; no five-rater α as a headline.
