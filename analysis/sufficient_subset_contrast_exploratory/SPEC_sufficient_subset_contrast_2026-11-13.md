# Specification — Post hoc exploratory: strict register-sufficient subset against the full random baseline

## Dates and status

- Instruction and specification date: 13 November 2026. Specification created 2026-11-13. Not backdated.
- **Post hoc.** This analysis follows Figure 1 (replacement-panel alpha for the full random baseline, n = 150, and the strict register-sufficient subset, n = 92). It was not planned before the data were seen.
- **The initial results were seen first.** An earlier throwaway run on 13 November 2026 produced the figures listed under *Reconciliation targets*; that run and its code were deleted at the investigator's request. This specification was written after those results were seen, and before the code in this folder was written. It fixes the method so that the run here is an independent reimplementation, not a reproduction tuned to those numbers.
- **Not preregistered.** Exploratory and descriptive. It must never be described as preregistered or confirmatory. No hypothesis tests and no p-values.
- The investigator instructed that nothing be committed or pushed in this session. This file is therefore not committed before the run; its SHA-256 at run time is recorded in `run_metadata.json`.
- Stream: scratch-coder analysis (Stream A). Changes no protocol, taxonomy, production classification, preregistered analysis or canonical result. Outputs stay in this folder, separate from the canonical outputs (`analysis/outputs_validation_scratch_20260824/`, `analysis/scratch_coder_results/`).

## Question

In Figure 1, replacing a coder with Fable 5 looks more favourable on the strict register-sufficient subset than on the full baseline. This analysis asks, descriptively:

1. How large is each strict-minus-full contrast, with a paired bootstrap interval that respects the dependence between the subset and the population it is drawn from?
2. Where does the change come from: abstention mismatches (one rater Unclear from Register Entry, the other substantive), disagreement between substantive label sets, or the expected-disagreement denominator?

## Populations

- **Full baseline:** the 150 random-baseline records (POST-009).
- **Strict register-sufficient subset ("sufficient subset"):** the 92 baseline records on which at least two of the three coders rated the register entry Sufficient (`derive_sufficiency_subsets(...)["strict"]`; S8T003).
- **Complement:** the other 58 baseline records (at least two coders did not rate Sufficient: 55 Partially sufficient majorities, 2 Insufficient majorities, 1 no majority). It is called "the complement" and is **never** called "Insufficient".
- The exposure-flagged record is kept in every population, as in the primary analysis. Its population membership is reported in the run metadata.
- No hard-case data.

## Raters and dimensions

Raters C01, C02, C03 (always these codes) and Fable 5 (production output MOD-006). Dimensions: Research Domains and Analytical Purposes. All four raters must have a complete, structurally valid set in both dimensions on all 150 records; the run aborts otherwise.

Panel and delta notation follows the canonical code (`analysis/validation/replacement.py`): A = C01, B = C02, C = C03, L = Fable 5. alpha_ABC is the human-only panel; alpha_LBC, alpha_ALC and alpha_ABL replace C01, C02 and C03; delta_A = alpha_LBC − alpha_ABC, delta_B = alpha_ALC − alpha_ABC, delta_C = alpha_ABL − alpha_ABC; delta_min = min(delta_A, delta_B, delta_C). Distance: MASI (`analysis.validation.metrics.masi_distance`).

## 1. Point estimates

For each population and dimension, the eight statistics from `replacement_panel_analysis` (canonical Fraction-based MASI). Complement estimates are descriptive only.

**Reconciliation (run aborts on failure):** the full and strict values equal S3T001, S3T002, S3T011 and S3T012 in `analysis/scratch_coder_results/results.md`, all 32 within 1e-12. Full-baseline per-rater, per-label counts equal LAC1T001.

## 2. Paired bootstrap of strict-minus-full contrasts

- Records sorted by Record ID (the order `dimension_panels` returns, checked).
- One draw: `numpy.random.default_rng(20261113).integers(0, 150, size=(10000, 150), dtype=np.int32)`. The same index matrix is used for both dimensions and both populations.
- Each drawn index carries the whole record: the three coder sets, the model set and the three sufficiency ratings (hence strict-subset membership) in both dimensions.
- Full-baseline resample: all 150 drawn occurrences. Strict resample: the drawn occurrences whose record is in the strict subset, with duplicates kept, so its size varies by draw. The two populations are never resampled independently; coders are never resampled; duplicates are never removed.
- Per draw, the eight statistics are computed for each population with the encoded coincidence-form alpha of `analysis.scratch_coder_stage_a.agreement` (`encode_panels` built once on the 150 records, `encoded_replacement_statistics` on the drawn rows); delta_min is recomputed within each resample from that resample's three deltas. The encoded alpha is checked against the canonical `replacement_panel_analysis` on the observed data (1e-12), and on the explicit duplicated record sequences of a sample of draws (1e-12).
- Contrast per draw = strict value − full value. Primary: alpha_ABC. Secondary: alpha_LBC, alpha_ALC, alpha_ABL, delta_A, delta_B, delta_C, delta_min.
- A draw is valid for a contrast when both its strict and full values are defined. Undefined draws are counted and reported, never replaced with zero. An interval is given only if at least 90% of the 10,000 attempted draws are valid.
- Interval: 95% percentile interval, NumPy `quantile(..., method="linear")` (Hyndman–Fan Type 7) at 0.025 and 0.975. These are explicitly 95% intervals. (The canonical alpha and delta intervals in results.md have an unrecorded confidence level and are never described as 95%.)
- Also reported: the distribution of the strict resample size across draws.

## 3. Disagreement diagnostic

Populations: full baseline, sufficient subset, complement. Per dimension.

Pairs: human–human C01–C02, C01–C03, C02–C03; model–human Fable 5–C01, Fable 5–C02, Fable 5–C03.

A set is *Unclear-only* when it equals {Unclear from Register Entry}; otherwise it is *substantive* (Unclear is exclusive and no set is empty; checked). Each record and pair falls into exactly one category:

1. both Unclear-only;
2. exactly one Unclear-only (for model–human pairs, split by direction: Fable 5 Unclear-only with the coder substantive, or the coder Unclear-only with Fable 5 substantive);
3. both substantive, identical sets;
4. both substantive, different sets.

Quantities, per pair and pooled by pair family (3N comparisons; these are **not** 3N independent observations, because each record contributes three dependent comparisons): category counts with denominators; exact match rate, mean Jaccard similarity and mean MASI distance, overall (denominator N or 3N) and among comparisons where both raters classify substantively (denominator reported).

Per-rater exports for each population: Unclear-only frequency and proportion; mean substantive labels per record and among substantively classified records; per-label counts and proportions for every label in the frozen rc2 taxonomy, including zero-count labels and Unclear.

Secondary check: the pair-family diagnostic restricted to records on which all four raters classify substantively, by population. These records differ in composition between populations, so this is **not** a controlled comparison.

## 4. Observed and expected disagreement audit

For each panel (ABC, LBC, ALC, ABL), population and dimension: observed disagreement Do = mean over records of the mean MASI distance over the three within-record pairs (identical to `AlphaResult.observed_disagreement` for complete three-rater units; checked); expected disagreement De from `AlphaResult.expected_disagreement`. Do is split into DoU (pairs with exactly one Unclear-only set, each at MASI distance 1) and DoS (pairs with two different substantive sets); both-Unclear and identical pairs contribute zero. Do = DoU + DoS (checked).

Optional arithmetic identity, per panel:

alpha_strict − alpha_full = (DoU_full − DoU_strict)/De_full + (DoS_full − DoS_strict)/De_full + Do_strict × (1/De_full − 1/De_strict).

A delta contrast's terms are the replacement panel's terms minus ABC's. This is an order-dependent arithmetic audit (a different order of substitution would split the change differently), **not** a causal attribution.

**Reconciliation (run aborts on failure):** 92 + 58 = 150 records and category counts add across populations; record-weighted Do sums add (150·Do_full = 92·Do_strict + 58·Do_complement, and likewise for DoU and DoS); pair-family pooled mean MASI distances equal the panel Do values; each identity sums to the observed contrast within 1e-12.

## Reconciliation targets from the deleted run (reported, not enforced)

The run compares its results with the figures below and reports every discrepancy. The code is not adjusted to reproduce them.

Strict minus full [95% interval]:

| Quantity | Research Domains | Analytical Purposes |
|---|---|---|
| alpha_ABC | +0.0400 [−0.0093, +0.0871] | −0.0036 [−0.0553, +0.0467] |
| alpha_LBC | +0.0713 [+0.0194, +0.1260] | +0.0543 [+0.0047, +0.1036] |
| alpha_ALC | +0.0801 [+0.0321, +0.1288] | +0.0527 [+0.0057, +0.1005] |
| alpha_ABL | +0.0661 [+0.0178, +0.1133] | +0.0389 [−0.0163, +0.0935] |
| delta_A | +0.0313 [−0.0054, +0.0704] | +0.0579 [+0.0177, +0.1023] |
| delta_B | +0.0401 [+0.0087, +0.0735] | +0.0563 [+0.0173, +0.0980] |
| delta_C | +0.0261 [−0.0125, +0.0652] | +0.0425 [−0.0093, +0.0945] |
| delta_min | +0.0401 [+0.0067, +0.0701] | +0.0563 [+0.0159, +0.0950] |

Human-only alpha: domains 0.526337 (full) to 0.566337 (strict); purposes 0.292110 to 0.288509. All 10,000 draws valid.

Diagnostic (sufficient / complement): exactly one Unclear-only; then different substantive sets among both-substantive comparisons:

- Domains, human–human: 30/276, 52/174; 96/245, 42/104.
- Domains, model–human: 16/276, 41/174; 83/260, 59/130.
- Purposes, human–human: 44/276, 80/174; 124/232, 24/50.
- Purposes, model–human: 22/276, 81/174; 125/254, 42/90.
- Purposes, human–human, both Unclear-only: 0/276 sufficient, 44/174 complement.
- Fable 5 Descriptive Monitoring 25/92 against 27/58; C03 Policy Evaluation / Impact Analysis 32/92 against 5/58.
- All four raters substantive: domains 77 sufficient, 29 complement; purposes 70 and 9.

Audit for delta_min (= delta_B), U term, S term, De term, total: domains +0.0031, +0.0355, +0.0014, +0.0401; purposes +0.0430, +0.0161, −0.0029, +0.0563.

Bootstrap targets are compared at four decimal places; counts exactly.

## Reading rules (stated before the code)

- A contrast is described as having an interval that excludes zero, or not; it is never called significant.
- No causal claim (sufficiency does not "cause" agreement), no claim that Fable 5 is formally equivalent to the coders, and no claim of an interaction between subset and panel.
- Percentages in reader-facing text are whole numbers.

## Data and code (reused, not modified)

`analysis.scratch_coder_stage_a.load` (including `verify_authorities`), `.panels` (`build_stage_a_data`, `dimension_panels`, `_taxonomy_labels`), `.sufficiency` (`derive_sufficiency_subsets`, `_record_codes`), `.agreement` (`encode_panels`, `encoded_replacement_statistics`); `analysis.validation.metrics` (MASI, Jaccard) and `analysis.validation.replacement`. Reconciliation sources: `analysis/scratch_coder_results/results.md` (S3T001, S3T002, S3T011, S3T012) and `analysis/label_application_cardinality_exploratory/LAC1T001.csv`.

## Outputs

`analysis/sufficient_subset_contrast_exploratory/`: `run.py`, aggregate tables `SSC1T001.csv` onwards, `results_sufficient_subset_contrast.md` and `run_metadata.json` (hashes of sources, specification and code; software versions; seed; attempted and valid draws; analysis status). Aggregate counts only; no record-level output. Adjudication findings and project-owner responses are not read.

## Addendum — interpretation caveats (added after the first run, 13 November 2026)

Added after the first run, on review and before any commit. It changes no population, estimator, bootstrap setting, check or target; it adds one aggregate caveat table (SSC1T012) and the caveats below. The SHA-256 of this specification as it stood before this addendum (`b40b5c35a581670dd21150a9a62bf5cccc0bc7ace843b62f019a25b0e6befa50`) is kept in `run_metadata.json`.

1. **Selection is not independent of coder abstention.** The subset is defined by the same coders' sufficiency ratings, and each coder's Unclear-only sets fall almost entirely on entries that coder did not rate Sufficient (SSC1T012). Fable 5 almost never abstains, so the subset removes coder abstentions largely by construction, which favours the panels that include Fable 5. Where the arithmetic audit attributes a delta contrast mainly to the abstention (U) term, as for Analytical Purposes, the contrast is read as mostly selection, not as better substantive classification.
2. **Subset against the population that contains it.** Strict minus full is diluted towards zero (92 of 150 records) and is not a comparison of sufficient against not-sufficient entries; complement estimates are shown alongside, descriptively.
3. **delta_B and delta_min are one finding** where they coincide at the point estimate. The sixteen contrast intervals are unadjusted, and reading only those that exclude zero overstates the evidence.
4. **Delta contrasts are differences of differences.** They are described as descriptive contrasts; no subset-by-panel interaction is claimed.
5. **Coders held fixed.** Records only are resampled; intervals do not cover other coders or other model runs.
