# Specification — Exploratory: model disagreement and instability as proxies for register insufficiency

## Dates

- Specification and instruction date: 10 November 2026 (investigator instruction).
- Specification creation date: 2026-11-10. Not backdated.
- Committed alone **before the Fable 5 replicate run has finished** and before any replicate label has been compared with production or with coder ratings. At commit time the replicate (`analysis/fable_production_replicate_exploratory/run_20261110/`) had completed Stage R and 54 of 111 Stage P batches, and had written no outputs; only batch progress, not labels, was read.
- No calculation code exists yet. It is written after this commit and run once, after the replicate completes.

## Status

Post-registration, exploratory and descriptive. Not preregistered. No hypothesis tests. Reported as a short paragraph and a supplementary table, not a headline result.

## Question

Human sufficiency ratings exist only for the 150 baseline records. In deployment no record has them. This analysis asks whether two signals that exist, or will exist, for every register record line up with the coders' judgement that a register entry is not sufficient to classify:

- **Cross-model disagreement:** Fable 5 and GPT-5.5 gave different label sets.
- **Model instability:** two Fable 5 runs under identical conditions gave different label sets.

If they line up, flagged records could be marked as low-evidence across the register without human ratings. If they do not, that is reported as a finding.

## Population

The random baseline only (n = 150; POST-009), a simple random sample of the 1,286 register records eligible for validation sampling. The hard-case sample is excluded: it was selected on cross-model disagreement, so it cannot show whether disagreement predicts anything.

## Signals (fixed before any instability label is seen)

All signals are per record and use Research Domains and Analytical Purposes only; tags play no part, as in the cross-model sampling frame.

| Signal | Definition | Source |
|---|---|---|
| **X — cross-model disagreement** | the record's frozen sampling stratum is `domain_only`, `purpose_only` or `both` | stratum in POST-009 (`baseline_active.csv`), computed at sampling from the frozen Fable 5 / GPT-5.5 comparison; expected 51 of 150 (ECT001) |
| **U — model instability** | the replicate's label set differs from the production label set (MOD-006) on Research Domains or on Analytical Purposes (exact-set inequality) | replicate `replicate_labels_canonical.csv` against MOD-006, joined on canonical Record ID |
| **E — either** | X or U | — |

Dimension-matched versions, for the secondary dimension outcomes only: X_D (stratum `domain_only` or `both`), X_P (`purpose_only` or `both`), U_D (domain sets differ), U_P (purpose sets differ).

For the 201 run-1 sample records, the production label is run 1's label, so U compares the replicate with run 1 for those records. This follows from how production was built and is not changed.

## Outcomes

From the coders' record-level sufficiency ratings (Stage A loader, unchanged), using the existing majority rule (at least two identical ratings):

- **Primary:** coder majority **not Sufficient**: a Partially sufficient majority, an Insufficient majority, or no majority. Expected 58 of 150 (S8T003: 92 Sufficient, 55 Partially sufficient, 2 Insufficient, 1 no majority). This is the complement of the register-sufficient subset used in Figure 1.
- **Secondary 1:** number of coders rating the entry Sufficient (0, 1, 2, 3), because sufficiency ratings are strongly coder-dependent (C01 rated 71% Sufficient, C03 39%).
- **Secondary 2:** coder majority set is Unclear from Register Entry only (consensus state S3), separately for Research Domains against X_D and U_D, and for Analytical Purposes against X_P and U_P.

## Quantities reported, for each of X, U and E

- The 2×2 table of signal (flagged / not flagged) against the primary outcome (not Sufficient / Sufficient), as counts.
- Proportion not Sufficient among flagged records, and among unflagged records, each with a 95% Wilson interval, shown beside the baseline rate (58 of 150).
- Proportion of not-Sufficient records that are flagged, with a 95% Wilson interval.
- Secondary 1: distribution of the number of Sufficient ratings by flag status (counts).
- Secondary 2: for each dimension, the dimension-matched 2×2 table against majority Unclear-only, as counts with Wilson intervals on the two row proportions.
- Register-level flag rates, to show what deployment would flag: the share of the 1,286 eligible register records flagged by X (frozen post-exclusion frame, 380 records), by U (replicate against production) and by E.

## Reading rule (stated in advance)

The write-up says, for each signal, whether the proportion not Sufficient among flagged records lies above, overlaps or lies below the baseline rate of 58/150, judged by whether its Wilson interval excludes that rate. It does not describe a signal as a usable proxy on any other basis, and it does not call any result significant.

## Expected limits (stated in advance)

- **U will be sparse.** The pre-existing run pair agreed on 95% of domain sets and 92% of purpose sets on its 201-record sample, so U is expected to flag roughly 10–15 of the 150 baseline records. Its 2×2 table will have single-digit cells and is likely to be uninformative on its own. That is an expected result, not a failure.
- **The reference is noisy.** Coders disagree on sufficiency, so a weak association may reflect the reference as much as the signal.
- **X is partly prompt fit.** GPT-5.5 received the production prompt without model-specific adaptation, so some disagreement reflects the prompt rather than a thin entry.
- **Signals are not correctness.** A flag marks entries where model output is less settled; it says nothing about which label is right.

## Reconciliation checks (the run stops on failure)

- 150 baseline records; X flags 51 (strata 20/20/11/99, ECT001).
- Every baseline record with a non-`none` stratum is in the frozen 380-record frame, and no `none` record is.
- Coder-majority sufficiency counts equal S8T003 (92/55/2/1).
- Majority Unclear-only counts by X_D and X_P equal the enrichment-calibration results (Research Domains 6 of 31 exposed, 7 of 119 unexposed; Analytical Purposes 8 of 31, 18 of 119).
- The replicate run is complete (all 132 batches; `run_metadata.json` present), every batch matched its reference input tokens, and its canonical labels cover all 150 baseline records.

## Data

- Coder ratings and baseline membership: Stage A loader (`analysis.scratch_coder_stage_a.panels.build_stage_a_data`), authorities as in the other exploratory runs (POST-028, POST-009, POST-019, MOD-006).
- Cross-model frame: `preregistration/package/03_preexisting_model_evidence/gpt55_disagreement_frame_380.csv`.
- Replicate: `analysis/fable_production_replicate_exploratory/run_20261110/replicate_labels_canonical.csv` and its `run_metadata.json`.
- Training and pilot exclusions for the register-level rates: `preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv`.

## Outputs

`analysis/sufficiency_proxy_exploratory/`: run script, aggregate result tables (SPX1T001 onwards), a results file and run metadata. Aggregate counts only; no record-level output outside the restricted folder.

## Exclusions

No hard-case data; no hypothesis tests; no claims about model correctness; no change to any preregistered analysis, the protocol, the taxonomy or the production labels; no adjudication findings or project-owner responses.
