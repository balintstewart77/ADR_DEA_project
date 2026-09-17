# Addendum — Exploratory pairwise Krippendorff's α: human panel structure and Fable 5 alignment (v1)

## Dates

- Specification: specified, and instruction issued, on or before 17 September 2026 (investigator-attested).
- Addendum creation date: 2026-09-17 (created 2026-09-17T14:18Z). Not backdated.
- This addendum is committed alone, before any analysis code for this run is written.

## Status

Exploratory and not preregistered. The protocol search (below) found no preregistered specification of pairwise Krippendorff's α, so no result from this run is labelled preregistered.

Stream: Scratch-coder analysis (Stream A). Separate from the figure pipeline. Changes no canonical artefact.

## Investigator statements

1. Hypothesis to examine (not tested formally): C02 agrees relatively well with both C01 and C03, so replacing C02 leaves little room for improvement, whereas replacing C01 or C03 does. Under this hypothesis, δ_min = δ_B partly reflects the human panel's structure rather than a specific weakness of Fable 5.
2. No pairwise α among these coders had been computed before this addendum.
3. Already seen before this addendum: canonical panel α and δ results (S2, S3 tables); per-label pairwise Cohen's κ (S5T005, S5T006); the δ_min matching components (pass-2 verification V2b).

## Coder mapping

Established from code, not data:

- `analysis/scratch_coder_stage_a/config.py:13` — `CODERS = ("C01", "C02", "C03")`.
- `analysis/scratch_coder_stage_a/panels.py:243–247` — `coder_a=values[0]` (C01), `coder_b=values[1]` (C02), `coder_c=values[2]` (C03), `model` = Fable 5 (MOD-006).
- `analysis/validation/replacement.py:71–84` — `lbc = (model, coder_b, coder_c)`, `alc = (coder_a, model, coder_c)`, `abl = (coder_a, coder_b, model)`; `delta_A = LBC − ABC`, `delta_B = ALC − ABC`, `delta_C = ABL − ABC`.
- Protocol v1.1 (PRO-018), Section 8.2: "alpha_LBC, alpha_ALC, and alpha_ABL: Krippendorff's alpha after replacing coder A, B, or C, respectively".

Therefore δ_A replaces C01, δ_B replaces C02, δ_C replaces C03. Below: A = C01, B = C02, C = C03, L = Fable 5.

## Search results

### Protocol search (Section 2.4)

Searched: `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` (PRO-018, SHA-256 `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77`), full text of `word/document.xml`. The instruction names `Validation_Protocol_PreReg_v1_1.docx`; no file of that exact name exists, and the manifest-registered v1.1 protocol above was searched. Terms: pairwise, pair-wise, each coder, each human, two-rater, Cohen, coder pair, pair of coders, between the model and, Krippendorff, alpha.

- Pairwise Krippendorff's α among coders: **not found** in the searched location.
- Pairwise Krippendorff's α between the model and each coder: **not found** in the searched location.
- Related pairwise analyses that are specified (Section 8.4), none of which is pairwise α: exact-set agreement between the production model and each scratch coder; record-level Jaccard similarity between the production model and each scratch coder (Research Domains, Analytical Purposes); per-label Cohen's κ for the three human–human pairs and three model–human pairs; per-tag Cohen's κ and Gwet's AC1.
- Section 4 (pre-existing model evidence, production-model stability) mentions "full pairwise metrics" for run-to-run production-pipeline stability; this concerns repeated model runs, not coders.

### Prior-result search (Section 2.5)

Searched: all tracked and untracked files in the repository excluding `venv/` and `.git/` (regular expression for pairwise Krippendorff/alpha/α, `alpha_AB|AC|BC|LA|LB|LC`, `alpha(A,B)`-style notation, "two-rater alpha"); git history of all refs (commit messages containing "pairwise"; pickaxe `-S pairwise_alpha`; `-G` for pairwise followed by alpha/Krippendorff).

- Pairwise Krippendorff's α results for C01, C02, C03 or Fable 5: **not found** in the searched locations.
- Other pairwise results found (not pairwise α): per-label pairwise Cohen's κ, `analysis/outputs_validation_scratch_stage_b_20260825/per_label_pairwise_kappa.csv` (and its consolidated tables S5T005/S5T006); pilot pairwise exact-set and Jaccard agreement, `preregistration/package/05_training_and_pilot/pilot_analysis/pilot_pairwise_agreement.csv` (training pilot, not the formal sample); commits `ad34cb6` and `6e067f4` (March 2026) mention pairwise agreement for LLM multi-trial consistency and method benchmarking, not coders.

## Data, metrics and estimator (reused, not modified)

- Loader and population membership: `analysis/scratch_coder_stage_a/panels.py` (`build_stage_a_data`, `population_ids`, `dimension_panels`).
- Estimator: `analysis/validation/alpha.py` `krippendorff_alpha` (the estimator that produced the canonical point estimates via `analysis/validation/replacement.py`).
- Metrics: `analysis/scratch_coder_stage_a/panels.py:252–253` — `masi_distance` for Research Domains and Analytical Purposes; `nominal_distance` for Demographic disparities / equity and COVID-19 & Pandemic (`analysis/validation/metrics.py`). Confirmed by protocol v1.1 Section 8.2 and `analysis/scratch_coder_stage_a/agreement.py:171`.
- Bootstrap: `analysis/validation/bootstrap.py` `bootstrap_joint` — record-level resampling with replacement (`Random(seed).randrange(n)`, n draws per replicate), one evaluator call per replicate computing all linked statistics on the same sample, Type-7 percentile bounds at 0.025/0.975, valid-replicate threshold `ceil(0.90 × 2000) = 1800` (equal to `MINIMUM_VALID_REPLICATES = 1800`, `analysis/scratch_coder_stage_a/config.py:16`, and protocol v1.1 Section 8.9), invalid replicates excluded per statistic with no top-up or replacement.

## Analyses (as specified in the instruction, Section 4)

Populations: baseline (150 records) and hard-case (75 records), analysed separately, never pooled. Hard-case outputs are labelled **DIAGNOSTIC — non-representative**.

Dimensions and metrics: Research Domains (MASI), Analytical Purposes (MASI), Demographic disparities / equity (nominal), COVID-19 & Pandemic (nominal).

Record set per population and dimension: the canonical common complete-case sequence from `dimension_panels` (records with all of A, B, C and L present), in its canonical sorted record order. The same records are used for every quantity.

### Check W — wiring (hard stop)

Using the same code path as the pairwise computations (calls into `krippendorff_alpha` with units built from the same per-record label tuples), generalised to three-rater units (A, B, C), reproduce α_ABC for every population and dimension. It must equal the canonical exported value (`analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv`, column `point_estimate`, panel `ABC`) exactly at full precision (float equality after parsing the exported repr).

### Analysis 1 — Pairwise α among humans

For each population and dimension: α(A,B), α(A,C), α(B,C), each a two-rater Krippendorff's α with the canonical metric.

### Analysis 2 — Pairwise α between Fable 5 and each human

For each population and dimension: α(L,A), α(L,B), α(L,C).

### Analysis 3 — Differences between human pairs

- α(A,C) − α(A,B)
- α(A,C) − α(B,C)
- α(A,B) − α(B,C)

### Analysis 4 — Replacement comparison per coder

For each coder X in {A, B, C}, with Y and Z the other two humans:

- H_X = mean of α(X,Y) and α(X,Z).
- M_X = mean of α(L,Y) and α(L,Z).
- D_X = M_X − H_X.

Explicitly: H_A = (α(A,B) + α(A,C)) / 2; H_B = (α(A,B) + α(B,C)) / 2; H_C = (α(A,C) + α(B,C)) / 2; M_A = (α(L,B) + α(L,C)) / 2; M_B = (α(L,A) + α(L,C)) / 2; M_C = (α(L,A) + α(L,B)) / 2.

Report H_X, M_X and D_X for each X, and the ordering of D_A, D_B, D_C alongside the ordering of the exported δ_A, δ_B, δ_C point estimates (`analysis/outputs_validation_scratch_20260824/replacement_delta_results.csv`) for the same population and dimension, and whether the orderings agree.

D_X is a descriptive comparison. Panel α is not the mean of pairwise αs, so D_X is not expected to equal δ_X, and D_X is not a decomposition of δ.

### Operational definitions fixed here (before analysis)

- Ordering: ascending by point estimate (smallest first, matching the sense of δ_min). Ties are exact float equality only and are shown as `=`. Orderings "agree" only if the ranked sequences of component letters, including ties, are identical. If any D_X or δ_X point estimate is undefined, the ordering comparison is recorded as not determinable.
- Undefined propagation: a pairwise α is undefined when the shared estimator returns `valid = False` (e.g. zero expected disagreement). Any Analysis 3 or 4 quantity with an undefined input is undefined, in the point estimate and in each bootstrap replicate, with the reason recorded.
- Two-rater α is symmetric in rater order; α(L,X) is computed with units ordered (L, X) and human pairs with units ordered alphabetically (A before B before C).

### Intervals

- One joint bootstrap per population and dimension: resample records with replacement, keeping all four raters' labels (A, B, C, L) for each record together; compute every quantity in Analyses 1–4 within the same replicate.
- 2,000 replicates, seed **20260917**, 95% percentile bounds (Type 7), valid-replicate threshold 1,800 (90%), undefined replicates excluded for that statistic and not rescued or replaced. No interval is reported for a quantity with fewer than 1,800 valid replicates.
- For every quantity: valid, invalid and requested replicate counts, and interval status.
- Context: exact whole-number record count per population; for tags, the number of records the coder majority applied the tag to, taken from the canonical export `analysis/outputs_validation_scratch_stage_b_20260825/tag_diagnostics.csv` (`human_majority_positive_n`).

## Excluded

Significance testing; p-values; describing any difference as significant; judging differences by overlap of separate intervals; statements about coder quality, reliability or competence; statements about Fable 5 "embodying" or "reasoning like" a coder; describing D_X as a decomposition of δ or claiming the hypothesis is confirmed; pooling baseline and hard-case; any analysis not listed above. Further analyses require a new dated addendum.
