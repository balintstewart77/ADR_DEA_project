# MSS1: macro averages over substantive labels only (post hoc sensitivity)

Dated 17 November 2026. Written before any substantive-only macro quantity was calculated. Post hoc and exploratory:
it was specified after the preregistered per-label and macro results (Stage B; results.md S5T003, S5T004, S6T001,
S6T002) had been seen. It implements the sensitivity proposed in pass-3 decision M.3. It does not replace the
preregistered macro averages, which remain primary and are reported alongside it.

## Why

Protocol v1.1 §8.1 treats Unclear from Register Entry as an ordinary taxonomy label "because it is a valid outcome of
the register-only task", and §8.8 includes it in the macro averages wherever at least 10 baseline records are
majority-positive. In the baseline the coder majority applied Unclear to 13 domain and 26 purpose records, so it is
eligible in both dimensions, but Fable 5 applied it to one record in each. Its precision is therefore 1.00 on a single
model-positive record; that value enters the unweighted macro precision as a full label, and the same label's
undefined resamples (no Fable 5 Unclear drawn) leave macro precision and F1 without an interval. A macro average over
the substantive labels answers the question most readers ask (agreement on substantive labels) and can carry
intervals.

## Population and labels

Random baseline only (n = 150). Eligible substantive labels are the preregistered eligible labels (S6T001, S6T002)
minus Unclear from Register Entry:

- Research Domains (5): Business & Productivity; Education & Skills; Health & Social Care; Labour Market & Employment;
  Poverty, Wealth & Living Standards.
- Analytical Purposes (3): Descriptive Monitoring; Outcome Tracking; Policy Evaluation / Impact Analysis.

No label is added and the support rule is unchanged. The reference remains the labelwise coder majority, which is not a
truth set.

## Quantities

For each dimension: macro precision, recall and F1, each the unweighted mean of the per-label values over the
substantive labels (as protocol §8.8 defines the macro average, with Unclear removed). Per-label F1 is averaged, as in
the preregistered analysis; F1 is not recomputed from the macro precision and recall.

## Inputs (no new resampling)

The committed Stage B outputs in `analysis/outputs_validation_scratch_stage_b_20260825/`:
`per_label_model_performance.csv` (point estimates), `bootstrap_per_label_performance.csv` (per-label values in each of
the 2,000 record-level resamples, seed 20260714), `macro_performance.csv` and `bootstrap_macro_performance.csv`. Each
must match its committed version at HEAD (allowing for line endings); SHA-256 hashes are recorded. Stage B drew one set
of resamples per run and applied it to every label, so replicate r is the same resample for every label in a
dimension. Reusing the saved replicates gives the substantive-only macro exactly the resamples of the preregistered
macro.

## Interval

Per replicate, the macro value is the mean over the substantive labels, and is undefined if any of them is undefined in
that replicate (the Stage B rule). The interval is the Stage B `interval` function: 2.5th and 97.5th percentiles,
Hyndman–Fan Type 7, reported only if at least 90% of the 2,000 replicates (1,800) are valid. These are 95% percentile
intervals.

## Reproduction gate

Before any substantive-only value is written, the analysis recomputes the preregistered all-eligible macro (Unclear
included) from the same saved per-label replicates and must reproduce, to within 1e-12, every replicate value in
`bootstrap_macro_performance.csv` and the point estimates, interval bounds and valid/invalid counts in
`macro_performance.csv`. If any check fails, the run stops and writes nothing.

## Outputs

Results go to a gitignored folder under `preregistration_restricted/`; the repository holds code only. Table MSS1T001:
for each dimension, the preregistered macro (all eligible labels) and the substantive-only macro, each with point
estimate, 95% interval where reportable and valid/invalid replicate counts, and the number of labels averaged. A
results markdown file and run metadata (inputs, hashes, git HEAD, software versions) accompany it.

## Reporting

Label it a post hoc sensitivity analysis, specified after results had been seen. Report it beside the preregistered
macro averages, never instead of them, and state which is preregistered. Make no claim of correctness.
