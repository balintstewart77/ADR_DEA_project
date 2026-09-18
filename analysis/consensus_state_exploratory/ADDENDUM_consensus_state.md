# Addendum — Exploratory: model agreement by human consensus state (v2)

## Dates

- Specification: specified, and instruction issued, on or before 18 September 2026 (investigator-attested).
- Addendum creation date: 2026-09-18 (created 2026-09-18). Not backdated.
- This addendum is committed alone, before any analysis code for this run is written.

## Status

Exploratory and not preregistered. The protocol search (below) found no preregistered specification of model-versus-majority-set agreement conditioned on human consensus state, so all results from this run are labelled exploratory. This analysis does not replace, amend or operationalise the preregistered release rule.

Stream: Scratch-coder analysis (Stream A). Separate from the pairwise alpha run, the record-level ratings run, and the figure pipeline. Changes no canonical artefact.

## Purpose

The protocol's release framework allows release with caveats where disagreement is concentrated in low-confidence human cases. Exploratory work has shown that this category is nearly empty: Low confidence was used in 15 of 450 baseline responses and no baseline record has a Low-confidence majority (results_confidence.md).

Human consensus state is observable on every record and is defined without reference to the model. This exploratory run asks whether the model's relationship to trained-human classifications varies according to the degree and form of human agreement on the same record.

This is a complementary exploratory diagnostic. It does not replace, amend or operationalise the preregistered release rule, and consensus is not a proxy for correctness. Agreement may track task difficulty, register sufficiency, taxonomy boundaries or other mechanisms that cannot be resolved without adjudication.

Consensus states are defined from human ratings only. The model plays no role in assigning a record to a state.

## Definitions

Consensus states and outcome measures were defined before any outcome was computed.

### Consensus state (defined from human ratings only)

For each record and dimension, using the existing labelwise majority rule (a label is in the majority set if at least two of three coders applied it):

| State | Definition |
|---|---|
| **S1 Unanimous** | All three coders gave identical label sets, and that set is substantive (does not contain Unclear from Register Entry). |
| **S2 Majority with dissent** | The majority set is substantive and non-empty, but the three coders' sets are not identical. |
| **S3 Majority Unclear** | The majority set consists of Unclear from Register Entry only. |
| **S4 No agreed label** | No label reached two of three coders; the majority set is empty. |

States are mutually exclusive and exhaustive.

### Outcomes by state

**S1 and S2 (substantive majority set exists):**
- Exact match: model set identical to the labelwise majority set (count and within-state proportion).
- Mean Jaccard similarity between model set and majority set.
- Set relationship (five mutually exclusive categories): Exact; strict superset; strict subset; partial overlap; disjoint.
- Mean model-set cardinality and mean majority-set cardinality.
- Analytical Purposes only: count and within-state proportion of records whose labelwise majority set contains more than two labels (expected zero).

**S3 (majority Unclear only):**
- Count and within-state proportion where the model applied Unclear from Register Entry.
- Count and within-state proportion where the model applied one or more substantive labels.
- Among records where the model applied at least one substantive label, the mean number applied (with denominator stated explicitly).

**S4 (no agreed label):**
- Model-set cardinality distribution (0, 1, 2, 3+).
- Count and within-state proportion where the model applied Unclear from Register Entry.
- No Jaccard or exact match: the human-majority reference set is empty and these are undefined.

**Human support for the model's labels (within each state, never pooled):**
For each consensus state, population and dimension: distribution of model-label assignments by the number of scratch coders who applied that same label (0, 1, 2 or 3).

### Bootstrap intervals

Record-level bootstrap within each population and dimension, 2,000 replicates, seed 20260918, 95% percentile bounds. The existing valid-replicate threshold (1,800/2,000) and suppression rule apply. No rescue of undefined replicates. State membership is a deterministic property of each resampled record's frozen human ratings. Intervals apply to proportions, means and other estimands, not to raw observed counts. Interval overlap or non-overlap between states is not a significance test.

For the hard-case sample, all bounds are labelled: descriptive resampling intervals for a selected diagnostic sample, not population-generalising intervals.

## Exclusions

- No tests, no significance language, no claim that consensus is truth.
- Tags (binary) excluded; they have their own diagnostics.
- Populations are never pooled.
- No Jaccard or exact match against an empty or Unclear-only reference set.
- No bootstrap intervals around raw counts.
- No pooling of model-label support distributions across states.

## Search results

### Protocol search

Searched: `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` (PRO-018, SHA-256 `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77`), full text.

- Section 8.4 preregisters record-level exact-set and Jaccard comparisons between the production model and each scratch coder. The two-of-three labelwise majority reference is specified for per-label metrics and adjudication eligibility.
- The protocol warns that the labelwise majority is not necessarily a taxonomy-valid record-level set and, for Analytical Purposes, may contain more than two supported labels.
- Conditioning model-versus-majority-set agreement on human consensus state: **not found** in the protocol.

This is post-registration exploratory analysis.

### Prior-result search

Searched: all tracked and untracked files in the repository excluding `venv/` and `.git/` (grep for consensus state, consensus-state, human consensus, human agreement state, agreement conditioned, conditioned on agreement); git history, all refs (commit messages, pickaxe for consensus_state and human_consensus).

- Agreement conditioned on human consensus state: **not found** in the searched locations.
- Related prior results already committed: record-level exact-set and Jaccard summary (S7T001–S7T004); pairwise alpha exploratory (PWA1T001–PWA1T032); record-level ratings exploratory; confidence exploratory; majority-coverage summary and Supplementary Table S1c.

## Data, population authorities and code (reused, not modified)

| Role | Artifact ID | Path | SHA-256 |
|---|---|---|---|
| Raw export | POST-028 | `preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv` | `29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d` |
| Baseline sample | POST-009 | `preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv` | `0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11` |
| Hard-case sample | POST-011 | `preregistration_restricted/sampling/official_draw_20260724/hard_active.csv` | `582f248d39d911275e4e4f11bc34660b51809a1ed7c330644f9e2036299cfb11` |
| Formal assignment crosswalk | POST-019 | `preregistration_restricted/assignments/formal_validation_20260724/formal_assignment_crosswalk.csv` | `96daddae15848331f7bef486a6c630e00de598ddb91f5ce317457e09a8bdd666` |
| Production model output | MOD-006 | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | `6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299` |
| Taxonomy | MOD-001 | `taxonomy_data_dictionary.yaml` | `7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de` |
| Data dictionary | RED-036 | `preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv` | `1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc` |
| Label mapping | RED-017 | `preregistration/package/06_redcap/redcap_label_variable_mapping.csv` | `fab68791df9a8bbb15dd93d2d06a6be15a0e6fd3ebb7d59b6ea75fef4aa7dfe8` |
| Structural validator | RED-013 | `scripts/validate_redcap_candidate.py` | `f28f45cdc45fd1dbc3f97d8bc0c8e4cfc2e1ce29ae4f95bcd3d423975f030190` |
| Protocol | PRO-018 | `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` | `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77` |

MOD-006 line-ending equivalence: the on-disk file (SHA-256 `9827fc9f01b9e1f3e9b58fe8f41b59eb5a569c77aacb77d5140628ec04f5eeab`) contains CRLF line terminators; the manifest SHA-256 (`6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299`) matches after CRLF-to-LF normalisation (csv_row_terminator_crlf_reconstruction), as recorded in the pairwise alpha run metadata.

### Reconciliation authority

Majority-coverage summary: `analysis/outputs_majority_coverage_20260914T170315Z/majority_coverage.csv` (committed, manifest not applicable — analysis output).

## Restricted-output location

Restricted outputs for this run (if any) will be placed in `preregistration_restricted/consensus_state_exploratory/`. Their paths and SHA-256 hashes will be recorded in `analysis/consensus_state_exploratory/run_metadata.json`.

## Seed

Bootstrap seed: 20260918 (from instruction date).
