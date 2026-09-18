# Addendum — Exploratory: enrichment calibration — does cross-model disagreement enrich for human disagreement? (v2)

## Dates

- Specification: specified, and instruction issued, on or before 18 September 2026 (investigator-attested).
- Addendum creation date: 2026-09-18 (created 2026-09-18). Not backdated.
- This addendum is committed alone, before any analysis code for this run is written.

## Status

Exploratory and not preregistered. The protocol search (below) found no preregistered specification of human-agreement outcomes conditioned on cross-model disagreement status, so all results from this run are labelled exploratory. This analysis does not replace, amend or operationalise the preregistered release rule.

Stream: Scratch-coder analysis (Stream A). Separate from the pairwise alpha run, the record-level ratings run, the consensus-state run, and the figure pipeline. Changes no canonical artefact.

## Purpose

The hard-case sample was drawn from records where Fable 5 and GPT-5.5 disagreed on domain or purpose labels. This run asks whether that cross-model disagreement — the exposure that defined the hard-case sampling frame — is associated with greater human disagreement within the random baseline sample.

Because the baseline was drawn without reference to model disagreement, any association is observational: it indicates whether the exposure enriches for human difficulty within a random sample, not whether the hard-case sample is representative or whether model disagreement causes human difficulty.

Cross-model disagreement is dimension-matched: domain disagreement is the exposure for Research Domains outcomes, and purpose disagreement is the exposure for Analytical Purposes outcomes.

## Definitions

All exposure classifications and outcome measures were defined before any outcome was computed.

### Exposure: dimension-matched cross-model disagreement

Each baseline record's cross-model disagreement stratum is taken from the frozen sampling artefact (`baseline_active.csv`, POST-009). The stratum was computed deterministically during sampling from the Fable 5 / GPT-5.5 comparison.

| Stratum | Definition |
|---|---|
| **domain_only** | Fable 5 and GPT-5.5 disagreed on Research Domains only (not Analytical Purposes). |
| **purpose_only** | Fable 5 and GPT-5.5 disagreed on Analytical Purposes only (not Research Domains). |
| **both** | Fable 5 and GPT-5.5 disagreed on both dimensions. |
| **none** | Fable 5 and GPT-5.5 agreed on both Research Domains and Analytical Purposes. |

Dimension-matched exposure assignment:

- **Research Domains:** exposed = domain_only ∪ both (n = 31); unexposed = purpose_only ∪ none (n = 119).
- **Analytical Purposes:** exposed = purpose_only ∪ both (n = 31); unexposed = domain_only ∪ none (n = 119).

Accompanying tag disagreement does not confer frame membership and plays no role in the exposure definition.

### Primary outcomes (human-only)

All primary outcomes are computed from human ratings only. The model plays no role.

1. **Krippendorff's α (MASI distance), panel ABC** — inter-coder agreement among the three scratch coders. Computed for the full baseline (reconciliation), the exposed subgroup, and the unexposed subgroup.

2. **Δα_enrichment = α_exposed − α_unexposed** — the difference in human inter-coder agreement between exposed and unexposed records. Computed within each bootstrap replicate, not from point estimates.

3. **Mean pairwise Jaccard (human-human)** — for each record, the mean of the three pairwise Jaccard similarities between coder label sets: J(A,B), J(A,C), J(B,C). Reported as the mean across records within each exposure group.

4. **Unclear-only rate** — proportion of records whose labelwise majority set consists of Unclear from Register Entry only (consensus state S3).

5. **No-agreed-label rate** — proportion of records whose labelwise majority set is empty (consensus state S4).

6. **Consensus-state distribution** — counts and within-exposure-group proportions for S1 (Unanimous), S2 (Majority with dissent), S3 (Majority Unclear), S4 (No agreed label). Definitions reused without modification from the consensus-state exploratory run.

### Secondary outcome

7. **Mean model-coder Jaccard** — for each record, the mean of the three Jaccard similarities between the production model (Fable 5) and each coder's label set: J(M,A), J(M,B), J(M,C). Reported as the mean across records within each exposure group. Labelled secondary because it involves the model.

### Jaccard convention

J(A, B) = |A ∩ B| / |A ∪ B|. When both sets are empty, the pairwise Jaccard for that pair is defined as 1.0 (identical empty classifications). When one set is empty and the other is not, J = 0.0.

### Bootstrap intervals

Record-level bootstrap of the full baseline (n = 150), 2,000 replicates, seed 20260918, 95% percentile bounds (Hyndman-Fan Type 7). The existing valid-replicate threshold (1,800/2,000) and suppression rule apply. No rescue of undefined replicates. Not stratified by exposure: each replicate resamples 150 records with replacement from the full baseline; exposure status is a deterministic property of each resampled record's frozen stratum.

Intervals are descriptive resampling intervals for a random sample. Interval overlap or non-overlap between groups is not a significance test.

## Exclusions

- No significance tests, no p-values, no interval overlap used as a test.
- No claim that cross-model disagreement is a proxy for correctness or truth.
- No claim that this analysis makes the hard-case sample representative.
- No conclusion from a null result that cross-model disagreement is merely model idiosyncrasy.
- No use of model-human agreement as evidence about human difficulty.
- Tags (binary) excluded; they have their own diagnostics.
- Hard-case quantities are not computed in this run.
- Populations are never pooled.
- The defective `disparities_tag_match` column in `crossmodel_comparison.csv` is never used.

## Search results

### Protocol search

Searched: `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` (PRO-018, SHA-256 `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77`), full text.

- Section 8.4 preregisters replacement-panel alpha (Krippendorff's α, MASI distance) for the production model versus each scratch coder. The hard-case sample is defined as records where two models disagreed on domain or purpose.
- Conditioning human-agreement outcomes on cross-model disagreement status within the baseline sample: **not found** in the protocol.

This is post-registration exploratory analysis.

### Prior-result search

Searched: all tracked and untracked files in the repository excluding `venv/` and `.git/` (grep for enrichment calibration, cross-model disagreement enriches, alpha exposed, alpha unexposed, delta enrichment); git history, all refs (commit messages, pickaxe for enrichment_calibr, alpha_exposed, alpha_unexposed, delta_enrichment).

- Human-agreement outcomes conditioned on cross-model disagreement status: **not found** in the searched locations.
- Related prior results already committed: full-baseline replacement alpha (replacement_panel_results.csv); cross-model comparison and disagreement stratum (crossmodel_comparison.csv, crossmodel_disagreement_stratum.csv); consensus-state exploratory (results_consensus_state.md).

## Data, population authorities and code (reused, not modified)

| Role | Artifact ID | Path | SHA-256 |
|---|---|---|---|
| Raw export | POST-028 | `preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv` | `29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d` |
| Baseline sample | POST-009 | `preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv` | `0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11` |
| Formal assignment crosswalk | POST-019 | `preregistration_restricted/assignments/formal_validation_20260724/formal_assignment_crosswalk.csv` | `96daddae15848331f7bef486a6c630e00de598ddb91f5ce317457e09a8bdd666` |
| Production model output | MOD-006 | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | `6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299` |
| Taxonomy | MOD-001 | `taxonomy_data_dictionary.yaml` | `7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de` |
| Data dictionary | RED-036 | `preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv` | `1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc` |
| Label mapping | RED-017 | `preregistration/package/06_redcap/redcap_label_variable_mapping.csv` | `fab68791df9a8bbb15dd93d2d06a6be15a0e6fd3ebb7d59b6ea75fef4aa7dfe8` |
| Protocol | PRO-018 | `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` | `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77` |
| Cross-model comparison | — | `analysis/outputs/crossmodel_comparison.csv` | — |
| Disagreement stratum | — | `analysis/outputs/crossmodel_disagreement_stratum.csv` | — |

MOD-006 line-ending equivalence: the on-disk file (SHA-256 `9827fc9f01b9e1f3e9b58fe8f41b59eb5a569c77aacb77d5140628ec04f5eeab`) contains CRLF line terminators; the manifest SHA-256 (`6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299`) matches after CRLF-to-LF normalisation (csv_row_terminator_crlf_reconstruction), as recorded in the pairwise alpha run metadata.

### Reconciliation authorities

- Full-baseline α ABC: `analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv` (Research Domains: 0.5263372741925532; Analytical Purposes: 0.2921101465494055).
- Consensus-state counts: `analysis/consensus_state_exploratory/run_metadata.json` (baseline Research Domains: S1=50, S2=82, S3=13, S4=5; baseline Analytical Purposes: S1=27, S2=73, S3=26, S4=24).

## Restricted-output location

Restricted outputs for this run (if any) will be placed in `preregistration_restricted/enrichment_calibration_exploratory/`. Their paths and SHA-256 hashes will be recorded in `analysis/enrichment_calibration_exploratory/run_metadata.json`.

## Seed

Bootstrap seed: 20260918 (from instruction date).
