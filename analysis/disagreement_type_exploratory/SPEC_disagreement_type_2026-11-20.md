# Specification: type of pairwise set disagreement by dimension (post hoc, exploratory)

## Dates and status

- Specification written 20 November 2026. Not backdated.
- **Post hoc.** Prompted by a draft sentence attributing domain disagreement to projects spanning several plausible areas and purpose disagreement to thin register entries. Not planned before the data were seen.
- **Initial results were seen first.** An ad hoc scratchpad script on 20 November 2026 printed aggregate counts of the categories below; it wrote nothing and has been superseded by this folder's code. This specification fixes the method and adds intervals; the run here reconciles its counts against Supplementary Table S15b's source (SSC1T005) rather than against that script.
- **Not preregistered.** Descriptive only. No hypothesis tests, no p-values, no multiplicity adjustment. It must never be described as preregistered or confirmatory.
- Changes no protocol, taxonomy, production classification, preregistered analysis or canonical result.

## Question

When two raters give different sets for the same record, what kind of difference is it, and does that differ between Research Domains and Analytical Purposes, and between entries the coder majority rated Sufficient and the rest?

## Populations and raters

- Random baseline, 150 records (POST-009). Strict register-sufficient subset: the 92 records at least two coders rated Sufficient (`derive_sufficiency_subsets(...)["strict"]`); its complement: the other 58. No hard-case data.
- Raters C01, C02, C03 and Fable 5 (production output). Sets as in the Stage A panels (`dimension_panels`). All four raters must have a set on all 150 records in both dimensions; the run aborts otherwise.

## Comparisons

- **Coder pairs:** C01–C02, C01–C03, C02–C03 (three per record).
- **Fable 5–coder pairs:** Fable 5 against each coder (three per record).
- Pairs within a record are not independent; pooled counts are descriptive.

## Categories (mutually exclusive, in this order)

1. **Same set:** the two sets are equal (including both Unclear from Register Entry only).
2. **Unclear against a label:** the sets differ and either is Unclear from Register Entry. (Unclear is exclusive in the taxonomy, so such a set is Unclear alone.)
3. **One set contains the other:** both substantive, and one is a proper subset of the other.
4. **Partial overlap:** both substantive, sharing at least one label, neither containing the other.
5. **No label shared:** both substantive and disjoint.

Categories 3–5 are **substantive disagreements**. Reported: count and share of all pairs for each category, and the share of substantive disagreements in categories 3, 4 and 5. Also reported: of the pairs with no label shared, how many are one label against one label.

## Intervals

Record-level bootstrap within the population: 2,000 resamples of records with replacement (seed 20261120, `numpy.random.default_rng`), all of a record's pairs kept together; each share recomputed as a ratio of summed counts in each resample. 95% percentile intervals, Hyndman-Fan Type 7 (`analysis.validation.bootstrap.percentile`). A share whose denominator is zero in a resample is undefined for that resample; intervals use the defined resamples and report their number.

## Reconciliation (run aborts on failure)

For each dimension, population (full, sufficient, complement) and family, the counts equal SSC1T005: same set = `both_unclear_only + identical_substantive`; Unclear against a label = `exactly_one_unclear_only`; categories 3–5 summed = `different_substantive`; pairs = `comparisons`.

## Outputs

Aggregate only, outside the repository's tracked files: `preregistration_restricted/disagreement_type_exploratory/` (DTY1T001.csv, DTY1T001.md, run_metadata.json), and Supplementary Table S2 (the corrected disagreement-composition table, with Unclear separated from substantive disagreement) to `analysis/tables/` and `DEA_paper/tables/` (both gitignored). No record identifiers are written.
