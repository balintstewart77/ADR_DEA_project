# Independent audit — hard-case strata, baseline Wilson supplement and canonical-report integration

Audit date: 2026-09-14 (started 07:17:31 UTC). Repository HEAD: `7585fed18ae5b7a4022d51d611d3148343b61afb`. Auditor: Claude Code (Opus 5).
Directory: `analysis/review/remaining_validation_20260914T071731Z/`. Ledger: `verification_ledger.csv` (3,496 checks; IDs `V00001`–`V03496`).

## 1. Verdicts

| Artefact | Verdict | Qualifications |
|---|---|---|
| **Post hoc hard-case strata** (`analysis/outputs_validation_scratch_hard_case_strata_20260825/`) | **Fully verified for computation and membership.** Every exported estimate, all 84 interval bounds and all 48,000 saved bootstrap replicate rows were reproduced from frozen inputs by independent code, with a maximum absolute difference of 6.2e-16. Membership is 25/25/25, disjoint, and equal to the 75-record hard-case sample. | The run-time code snapshot cannot be proven identical to the committed code (U0003, open). The official draw was not re-executed (V00027). Methodological cautions F-01, F-02 and F-03 apply to interpretation, not to the numbers. |
| **Baseline Wilson supplement** (`analysis/outputs_validation_wilson_baseline_20260907T142427225531Z/`) | **Fully verified for computation, counts and scope.** 37 new intervals, 2 retained original intervals and 1 equivalent-result reuse (WSA0074 ← WSA0083) are confirmed. Every count was rebuilt from the raw export, and every bound matches an 80-digit Wilson solution to within 1.4e-16. **Provenance is partly verified.** | Historical re-execution with current code is blocked (F-06). The approval instruction for the 37-row scope is not archived in the repository (F-07). The inferential notes in F-08 apply. |
| **Canonical-report integration** (`analysis/scratch_coder_results/results.md`) | **Fully verified for all in-scope cells.** All Section 11 cells, and every row of S8T001–S10T004, match their source strings exactly. Provenance labels, lineage metadata and all 69 unresolved entries are unchanged against the pre-supplement reference. | Two non-material reporting issues: the Section 8 prose does not mention the supplement (F-09), and the U0005 confidence annotation is more conservative than the saved evidence supports (F-04). |

**No material finding.** No computational error was found, and nothing found changes a reported value, population, denominator or method. These verdicts cover only the checks listed in §12. They are not a statement that the validation study, or all of its analyses, has passed.

## 2. Scope

**In scope.**
- The separately generated hard-case-stratum outputs (run 2026-08-25T16:18:24Z).
- The 2026-09-07 baseline Wilson supplement and its scope assessment.
- The integration of both into the canonical report.

**Prior audits used as evidence, not as proof of the new results.**
- `analysis/outputs_validation_scratch_20260824/review/2026-08-24_claude_code_independent_audit.md`. This covered the Stage A replacement panels (150 baseline, pooled 75 hard-case), the original WSA0082/WSA0083 Wilson intervals to 6 decimal places, and the subset counts 148/92.
- `analysis/scratch_coder_stage_b/review/claude_independent_audit_b` (a single file, not a directory). This covered the Stage B per-label, agreement and tag diagnostics, including the pooled hard-case exact-set and Jaccard point estimates.
- Neither audit examined per-stratum outputs or the supplement. Pooled quantities were revisited here only to reconcile against the strata and to validate this audit's own independent estimator (§7.4).

**Excluded; recorded as outside this audit (§14).** Project-owner responses and outcomes (collection ongoing), adjudication, secondary review, release decisions, senior sign-off, new stability analyses and model comparisons.

## 3. Evidence, provenance and access

### 3.1 Selected artefacts and how they relate

| Role | Artefact | Selection basis |
|---|---|---|
| Canonical report | `analysis/scratch_coder_results/results.md` (SHA-256 `5a7e4a3e…`), `run_metadata.json` | `document_sha256` and `housekeeping.selected_final_run.report_sha256` both equal the current file hash. The source was historical run `…consolidated_20260907T142435900989Z`, later deleted by housekeeping. |
| Strata outputs | 9 files in `analysis/outputs_validation_scratch_hard_case_strata_20260825/` | Listed in the canonical `source_files`. Committed in `298471a` and unchanged since. |
| Strata code | `analysis/scratch_coder_hard_case_strata/*.py` | Untracked when run at HEAD `cc5cf7d`. Committed the next day (`298471a`, 2026-08-26T09:17:23Z), byte-identical to HEAD. Stage A, Stage B, `analysis/validation` and validator code are unchanged from `cc5cf7d` to HEAD; the only change in those paths is the added audit document. |
| Wilson supplement | `wilson_intervals.csv`, `reused_intervals.json`, `methods_wilson_baseline.md`, `run_metadata.json` | Canonical `supplement.directory` and `housekeeping.retained_references`. The metadata hash `b1747a8c…` equals the canonical record. An earlier sibling (`…wilson_baseline_20260907T142055636248Z`) was untracked before the run, is now absent, and is referenced nowhere canonically; it was not used. |
| Wilson scope | `analysis/outputs_validation_consolidation_followup_20260907T132938546154Z/` (manifest, assessment, followup metadata, command log) | Recorded as supplement inputs with matching hashes. |
| Wilson generator | Commit `dcf763b` | The blobs of `wilson_supplement.py` (`bf275502…`) and `scratch_coder_consolidated/supplement.py` (`981d8268…`) equal the recorded `task_code` hashes. Both files changed at HEAD (commit `5559da3`). |
| Protocol and governance | Protocol v1.1 (PRO-018, `fd1fa40b…`); `protocol_deviation_log.csv` (DEV-001–DEV-004); `preregistration/post_registration/amendments/` (only `.gitkeep`); `sampling_specification.yaml` | No deviation or amendment entry concerns the strata analysis or the supplement. |
| Taxonomy | rc2 (`taxonomy_data_dictionary.yaml`, MOD-001). Label sets taken from the frozen REDCap candidate 0.7 dictionary (RED-036). | Used by both analyses. |
| Frozen inputs (restricted, read in memory only) | POST-028 raw export, POST-009, POST-011, POST-019 | Hashes equal the manifest identities (V00001–V00005). MOD-006 equals its recorded LF identity (V00006). |

### 3.2 Access restrictions

- **Read.** Only the four restricted scratch-coder files above. From the export, only analytical columns were loaded: assignment, coder pseudonym, source record, inclusion, completeness, sufficiency, fit, and domain/purpose checkboxes. The full list is in `audit_metadata.json`.
- **Not read.** Titles, datasets, free-text notes, exposure notes, owner/proposal fields, and the `contacts`, `reserve_samples`, `trainer_only`, `blinded_assignments` and `pilot_private_review` directories.
- **Outputs.** No Record ID, Project ID, assignment ID or title appears in any output. A masking scan of the audit directory covered 900 identifier tokens and 224 titles and found 0 hits.
- **Stale README.** `preregistration_restricted/README.md` still says the sampling and export children are empty. They are populated, and hash-verified against manifest rows POST-009/011/019/028.

### 3.3 Integrity and working-tree state

- **Git status before the audit:** clean. The only entry was this audit's own status file.
- **Input hashes:** 141 immutable input files (inputs, source outputs, canonical pair, supplement, scope files, code, protocol, logs, prior audits) were hashed before and after. **All unchanged.**
- **Git status after the audit:** unchanged outside the audit directory.
- **Commands:** no production generator was run, no production test was run (to avoid cache side effects), and no commit, push or remote action was taken.

## 4. Independent methods and pre-declared criteria

**Independence.** The reference code (`reference_code/*.py`) imports nothing from `analysis.*` or `scripts.*`. It uses Python 3.12.5, pandas 3.0.2 (CSV parsing only), numpy 2.4.4 (integer indexing) and the standard library (`fractions`, `decimal`, `random`, `statistics`).

**Comparison criteria, fixed before any comparison was made.** These tolerances were not adjusted afterwards.
- Integers and strings: exact equality.
- Double-precision statistics against exact rationals or regenerated values: absolute difference ≤ 1e-12.
- Wilson bounds against 80-digit Decimal values: absolute difference ≤ 1e-12.
- The z constant: absolute difference ≤ 1e-15.
- Displayed values: exact equality with `format(independent_value, ".3f")`.
- Stochastic quantities: exact regeneration of the saved draws. Because this succeeded, no distributional criterion was needed.

**Membership and joins.**
- Strata were rebuilt from POST-011 `hard_case_stratum` and cross-checked per assignment against POST-019.
- Responses came from the export (`validation_included=1`), joined one-to-one on assignment ID with reviewer and record agreement checked. Checkbox codes were mapped with this audit's own parser of the RED-036 choices.
- Model sets were read by splitting MOD-006 `substantive_domains` and `analytical_purpose` on `;`.
- None of this reuses Stage A parsing.

**Set metrics.**
- Exact-set agreement: equality of unordered sets.
- Jaccard: |A∩B|/|A∪B| in exact rationals (empty/empty = 1; no empty sets occur).
- Quartiles: Hyndman–Fan Type 7, written independently.

**Replacement α.**
- MASI distance is 1 − Jaccard × w, with w = 1 (equal), 2/3 (one set contains the other), 1/3 (partial overlap) or 0 (disjoint). This matches protocol §8.3 ¶128–¶130 and the saved Stage A methods.
- Point estimates use the literal ordered-pair Krippendorff definition in exact `Fraction` arithmetic.
- Replicates use a second, integer-scaled coincidence form. Distances are scaled by 83,160 (3 × lcm(1..12)) to keep the arithmetic exact. The two forms agree exactly on the full sample (6 checks).
- Deltas and Δmin follow the saved definitions: LBC/ALC/ABL minus ABC, then the minimum.

**Bootstrap.**
- Generator: `random.Random(20260714)`, drawing `randrange(25)` 25 times per replicate, for 2,000 replicates. The record is the resampling unit, with A/B/C/L ratings kept together.
- Generator lifetime: a fresh generator per stratum × dimension × pair for set metrics, and per stratum × dimension for replacement.
- Percentiles: Type 7 at p = 0.025 and 0.975.
- Record order was ascending Record ID. The saved methods do not document this; it is the production convention, and exact reproduction of every saved replicate row corroborates it.

**Wilson.**
- z is Φ⁻¹(0.975), found by bisection on an 80-digit erf series (π by Gauss–Legendre).
- The bounds are the two roots of (k/n − p)² = z²p(1−p)/n. This is an algebraic form different from the production centre ± half-width.
- The score equation was checked at each bound (residual < 1e-60).
- Every numerator and denominator was rebuilt from the raw export. Named-coder rows use that coder's 150 ratings. Record majority means ≥2 identical of 3 ratings. Unclear measures count the coders using "Unclear from Register Entry".

## 5. Measurement inventory

| ID | Report location | Source artefact / key | Population · unit | Quantities | Interval (method) | Prior audit | This audit |
|---|---|---|---|---|---|---|---|
| H1 | S11T013–S11T018 | `hard_case_stratum_exact_set_jaccard.csv` (stratum, dimension, pair L-A/L-B/L-C); 18 rows | Hard-case stratum, n=25 · record | `exact_match_n`, `exact_match_proportion`, mean/median/Q1/Q3 Jaccard; pair-averaged `mean_model_coder_*` | Exact-set and mean-Jaccard 2.5/97.5 percentile, 2,000 record resamples, seed 20260714, Type 7; 72 bounds | None (Stage B covered pooled 75 only) | Full |
| H2 | S11T007–S11T012 | `hard_case_stratum_human_pair_agreement.csv` (pairs A-B/A-C/B-C); 18 rows | Same | Same point fields; `mean_model_coder_*` holds human-pair means (U0068) | None exported | None | Full |
| H3 | S11T001–S11T006 | `hard_case_stratum_replacement.csv`; 6 rows | Same · complete-case record | α_ABC, α_LBC, α_ALC, α_ABL (MASI), δA/δB/δC, Δmin | Δmin percentile; 12 bounds; valid/invalid 2000/0 | None | Full |
| H4 | — (not rendered; not loaded by the report generator) | `bootstrap_hard_case_stratum_*.csv`: 36,000 + 12,000 rows | Same | All replicate statistics | — | None | Full |
| H5 | — | `hard_case_stratum_summary.md` | Same | 39 displayed 3-dp lines: pair means, contrasts, full tables | — | None | Full |
| W1 | S8T001, S8T003, S9T001, S9T003, S10T001, S10T002 | `wilson_intervals.csv`: WSA0053–0061, 0075–0077, 0090–0101, 0118–0122, 0135–0138, 0146–0149 (37) | Baseline, n=150 · named-coder rating per project, or one record indicator | Proportion k/150 | New Wilson 95%, two-sided, no continuity correction | None | Full |
| W2 | S8T005 | `sufficiency_subset_summary.csv`: WSA0082 (148/150), WSA0083 (92/150) | Baseline · record | Subset proportion | Original Stage A Wilson 95% | Stage A audit (6 dp) | Recomputed at full precision; lineage |
| W3 | S8T003 "Sufficient" | `reused_intervals.json`: WSA0074 ← WSA0083 (92/150) | Baseline · record | Record-majority Sufficient | Reused bounds | None | Per-record equivalence and lineage |
| W4 | S8T001/S9T001 "all coders", S9T005, S10 response and crosstab rows, S10T005 | Manifest `methodological_decision_required` (37), `no_inferential_interval_proposed` (2), QA candidates (8), `excluded_nonbaseline` (106) | Baseline pooled responses, QA, structural, hard case | — | Excluded (no interval) | None | Exclusion verified in CSV and report |
| R1 | Section 0, Appendix A, `run_metadata.json` | `unresolved_items`, `result_items`, `cell_lineage`, `supplement` | — | Status, lineage, 69 entries | — | None | Full |

## 6. Protocol mapping

| Requirement / element | Status | Delivered |
|---|---|---|
| 75 hard cases, 25/25/25 by domain_only, purpose_only and both; accompanying-tag records forced within quota (§5.3 ¶53–¶57) | Preregistered (sampling) | Membership verified (§7.1). 5 forced records confirmed. |
| Hard-case sample analysed separately as diagnostic and non-representative (¶123) | Preregistered | Pooled 75 in Stage A/B. The strata diagnostic is labelled post hoc and diagnostic in its methods, summary and report §11 (results.md:1874). |
| Per-stratum set agreement and replacement α | **Not preregistered.** Documented post hoc addition (`methods_hard_case_strata.md`) | Correctly not described as confirmatory. No deviation-log or amendment entry exists; the repository does not settle whether one is required (outside scope). |
| Set agreement (¶139–¶140), MASI replacement α (¶128–¶130), record bootstrap 2,000, seed 20260714, Type 7, joint recalculation (¶167) | Preregistered methods, reused for strata | Implemented as specified (§7.3). |
| "Baseline proportions will use 95% Wilson score intervals" (¶167) | Preregistered | The original Stage A run exported subsets only (U0069). The 2026-09-07 dated supplement adds 37 selected rows. |
| Pooled coder-response proportions | Protocol wording is broad; no clustered method is specified | Excluded pending a methodological decision (manifest). Correctly not given ordinary Wilson intervals. |
| Governance of the supplement | Undetermined in the repository (scope assessment, "Governance") | No deviation or amendment entry. The approval instruction is not archived (F-07). |

## 7. Hard-case strata — results

### 7.1 Membership and joins (V00001–V00050)

- **POST-011:** 75 rows, 75 unique Record IDs, 75 unique official Project IDs (none repeated, so no Project-ID collapse issue arises). Stratum counts are 25/25/25, matching `run_metadata.json`. No value falls outside the three strata, no record has more than one stratum, and every row is `hard_case`/`active`/`yes`.
- **Mutually exclusive and exhaustive.** The strata union is the 75-record sample, with zero pairwise overlap (V00050).
- **Baseline disjointness.** POST-011 and POST-009 share 0 Record IDs and 0 Project IDs.
- **POST-019:**
  - 225 hard-case assignment rows, and every hard-case record has exactly one C01, one C02 and one C03 assignment.
  - The stratum is consistent within each record and equals POST-011 for all 225 rows.
  - The hard-case and baseline Record ID sets equal POST-011 and POST-009.
- **Stratum labels outside the sample (V00024).** 51 baseline records also carry frame labels (domain_only 20, purpose_only 20, both 11). The production code filters on `sample_family=='hard_case'` (`analysis/scratch_coder_hard_case_strata/analysis.py:20`), so none enters the strata. This is confirmed by n=25 per stratum and the union identity.
- **Forced records (V00025).** 5 records were forced into the active strata by the accompanying-tag rule: domain_only 4, purpose_only 1, both 0. The `accompanying_tag_disagreement` and `forced_into_active_hard` flags agree on all rows.
- **Export:**
  - 675 formal rows, joined one-to-one to POST-019 with no reviewer or record mismatch.
  - All responses complete; no duplicate (record, coder) pairs, no non-0/1 checkbox values, no empty coder sets.
  - None of the 38 non-formal rows attaches to a formal record.
  - The hidden `sample_set`/`hard_stratum` fields are blank for all 675 formal rows, so the export cannot serve as a third membership source (V00043, NOT_CHECKED).
- **Model:** joined one-to-one for 225 records, with no duplicate Record IDs, no labels outside the frozen label sets and no empty sets. "Unclear" never co-occurs with another label, for either coders or model.
- **Complete cases:** 25 records per stratum, for both dimensions.
- **Not re-derived.** The stratified draw itself (SEED_DRAW 20260713 from the 380-record frame) was not re-executed, because doing so would materialise embargoed reserve identities (V00027).

### 7.2 Point estimates (V00054–V00741, `strata_point`)

All exported point quantities were recomputed: 18 model–coder rows × 9 fields, 18 human-pair rows × 9 fields, and 6 replacement rows × 9 fields. Counts match exactly; continuous values match to a maximum absolute difference of 2.8e-16.

The pair-averaged columns equal the mean over the three pairs in their own file. In the human-pair CSV, `mean_model_coder_exact_set` and `mean_model_coder_jaccard` are human-pair means for all 18 rows (36 checks, U0068).

### 7.3 Intervals and replicates (`strata_bootstrap`, V00051–V00755)

- **Settings.** Seed 20260714 and 2,000 replicates, as recorded. Replicate numbering runs 1..2000 in all 24 groups, and `sample_n` is 25 throughout.
- **Replicates.** All 84 replicate groups (18 × 2 set statistics and 6 × 8 replacement statistics) reproduce 2000/2000 from regenerated draws, with a maximum absolute difference of 6.2e-16. There are 0 undefined replicates, so the saved valid/invalid counts of 2000/0 are correct.
- **Bounds.** All 72 set-metric bounds and all 12 Δmin bounds equal Type 7 p=0.025/0.975 quantiles, whether computed from the saved replicates or from the independently regenerated ones.
- **Example.** The upper bound 0.44099999999999456 (domain_only, Analytical Purposes, L-A) is a genuine Type 7 interpolation (0.44 + 0.025 × 0.04 plus floating residue), and 0.441 is displayed correctly.
- **Confidence level.** For exact-set and Jaccard, 95% is documented through the reused Stage B methods ("2.5/97.5"). For Δmin, the saved strata methods give no level, but the saved `hard_case_stratum_summary.md` column is headed "Δmin [95% CI]" and the bounds are numerically the 2.5/97.5 percentiles (see F-04).
- **Shared draws.** Re-seeding means the same 2,000 index draws are used for every pair and every stratum (common random numbers). This is descriptive and not an error, but the intervals for different pairs and strata are not independent.
- **Summary display.** All 39 numeric lines in the summary match the independent values at 3 dp (V00810–V00849).

### 7.4 Reconciliation with the pooled hard-case outputs (V00756–V00809)

- **Additive counts.** For every dimension × pair, the pooled Stage B `exact_match_n` equals the sum of the three stratum counts (for example, 4+15+6 = 25 for Research Domains L-A). Pooled `n_records` is 75.
- **Mean Jaccard.** The pooled mean equals the n-weighted mean of the stratum means (equal n).
- **Pooled quartiles.** Q1, median and Q3 cannot be reconstructed from strata. They were recomputed on the 75-record union and match.
- **Pooled α.** Pooled α_ABC/LBC/ALC/ABL and Δmin were recomputed directly on the union and match Stage A. They were never averaged from strata. The unweighted mean of the stratum α_ABC differs from the pooled value by 0.0060 (Domains) and 0.0100 (Purposes), which confirms that averaging would have been wrong. It was not done.

### 7.5 Interpretation (V00850–V00859)

The summary and report §11 keep the diagnostic framing ("post hoc", "deliberately non-representative", "no hypothesis tests", "descriptive only", "not true errors or a gold standard", no release, population, per-label or adjudication inference). No statement about adjudication needs or disagreement causes appears, and none follows from these quantities.

The descriptive pattern is mixed. Pair-averaged exact-set agreement (model–coder / human–human):

| Stratum | Domain | Purpose |
|---|---|---|
| domain_only | 0.213 / 0.253 | 0.320 / 0.440 |
| purpose_only | 0.640 / 0.493 | 0.147 / 0.400 |
| both | 0.253 / 0.507 | 0.213 / 0.400 |

- **purpose_only:** Purpose agreement is lower on both exact-set and Jaccard, and model–coder is far below human–human.
- **domain_only:** Domain is lower on exact-set, but Domain Jaccard is higher than Purpose (+0.044). Human–human Domain agreement is also lowest in this stratum (0.253), so the lower model–coder agreement cannot be attributed to the model (F-03).
- **Δmin:** 4 of 6 intervals lie wholly below zero (domain_only Purposes, purpose_only Purposes, both Domains, both Purposes). Correctly, no trigger is applied (F-02).

## 8. Wilson supplement — results

### 8.1 Scope (V00860–V00880)

- **The 37 IDs are identical** across the CSV, methods text, metadata `selection_list` and canonical `supplement.new_interval_candidate_ids`.
- **Family counts** match the methods: 9 named-coder sufficiency, 3 record sufficiency, 12 named-coder fit, 5 record fit, and 4 + 4 Unclear record rows.
- **Manifest decisions** recomputed from rows: 3 already exported, 45 candidates, 106 non-baseline, 37 methodological, 2 no inferential interval.
  - All 37 selected rows are candidates.
  - The 8 unselected candidates (WSA0023, WSA0025–WSA0031) are all QA record-status rows.
  - WSA0074, WSA0082 and WSA0083 are classified `already_exported`.
  - None of the 37 pooled rows is in the supplement, and all carry `pooled_repeated_within_project=true`.
  - The 2 structural and 106 non-baseline rows are excluded.
- **Units** (V00870–V00880).
  - Each named coder has exactly 150 baseline ratings, one per distinct project.
  - Record rows carry one indicator per project.
  - The excluded pooled rows have three ratings per project.

### 8.2 Counts and bounds (37 rows; `wilson_counts`, `wilson_numeric`)

- **Counts and strings.** For every row, the count, denominator and proportion strings are identical across the supplement CSV, the source CSV and the manifest.
  - Every count is an integer with 0 ≤ k ≤ 150, and no zero denominator exists.
  - Every proportion string equals `repr(k/150)`, so it comes from exact counts, not rounded percentages.
- **Reconstruction.** All 37 numerators and denominators were rebuilt from the raw export and match exactly. Source and manifest hashes equal the current files.
- **z.** The independent value is 1.95996398454005423552…; the repository's 1.959963984540054 is within 1e-15.
- **Bounds.** All 148 bound comparisons (`ci_*` and `raw_formula_*`) are within 1.4e-16. Bounds satisfy the score equation, and 0 ≤ lower ≤ k/n ≤ upper ≤ 1 holds for every row.
- **Method fields.** Every row records Wilson score, 0.95, α = 0.05, two-sided, no continuity correction, the implementation hash `7e2e383c…` and the timestamp 2026-09-07T14:24:27.146711Z.
- **Zero successes.** These occur only in WSA0100 (C03, No Fit) and WSA0120 (record majority, No Fit).
  - The exact lower root is 0.
  - The saved raw value 1.734723475976807e-18 equals 2⁻⁵⁹, a floating-point cancellation artefact.
  - The stored `ci_lower` is `0.0`, recorded per row and in `boundary_corrections`. The metadata lists exactly these two corrections.
  - The upper bound 0.0249702443680766 equals z²/(150 + z²).
- **All successes.** No row has k = n.
- **Other rows.** No correction is recorded, and the stored bounds equal the raw-formula strings.
- **Source intervals.** Neither correction touched pre-existing intervals. The Stage A subset CSV hash is unchanged, and the implementation (`analysis/validation/intervals.py:32-33`) is unchanged from the Stage A run HEAD `ac18315` (clean at that run) through `dcf763b` to HEAD.

### 8.3 Retained and reused intervals (V01592–V01609)

- **WSA0082 (148/150) and WSA0083 (92/150).**
  - The source CSV, `reused_intervals.json` and the manifest `existing_interval` hold identical strings.
  - Counts were rebuilt from the raw export.
  - Independent roots match the original bounds within 1.1e-16.
- **WSA0074 ← WSA0083.** Equivalence rests on more than matching counts.
  - The per-record indicators for majority "Sufficient" and "≥2 Sufficient ratings" agree for 150 of 150 baseline records.
  - The denominator is the same: all three ratings are valid for every baseline record.
  - With three ratings, a category reaching ≥2 is necessarily the unique majority.
  - The reused bounds equal the WSA0083 strings and an independent 92/150 recomputation.

### 8.4 Lineage (V00883–V01633, `wilson_lineage`)

- **Hashes.** Supplement output hashes and sizes equal the recorded values, and the metadata hash equals the canonical record. The six source files match before, after and now.
- **Recorded generator code.** It exists at `dcf763b` (hashes match).
- **Current generator code differs** (V01627, V01629). The recorded invocation is not accepted by current code, which adds a required `--task-b-metadata` argument (V01631).
- **Deleted input.** The recorded input `analysis/outputs_validation_consolidated_20260907T131344836676Z/run_metadata.json` was deleted by housekeeping (V01625). Its SHA-256 `826b22e1…` matches the canonical deletion inventory. At `dcf763b` this file was used for provenance and for the unresolved-entry equality check, not for any interval calculation (F-06).

## 9. Canonical-report integration — results

- **Section 11** (1,071 checks).
  - All 18 tables have titles naming the family, `hard_case` parent, dimension and stratum.
  - Every exported estimate cell is rendered exactly once across the three strata CSVs (0 missing, 0 extra) with identical strings and "25 records" denominators.
  - Pair labels map correctly: C01=A, C02=B, C03=C, Fable 5=L.
  - Model–coder CIs are identical and marked `bootstrap_percentile; confidence 95%; …/2000`.
  - Δmin bounds are identical and marked "confidence unresolved" (results.md:1887, :1900, :1913, :1926, :1939, :1952; F-04).
  - Human-pair and component-α rows show no bounds, with status A.
  - The human-pair tables carry the `mean_model_coder_*` naming note (results.md:1956).
  - No values from another stratum or population were substituted.
- **Sections 8–10** (775 checks, 14 tables).
  - Every row resolves to one source row, with identical value strings and denominators.
  - **37 new intervals:** bounds identical, marked `supplementary Wilson 95%; calculated 2026-09-07T14:24:27.146711+00:00; source …/wilson_intervals.csv` (for example results.md:1475, :1603, :1653).
  - **WSA0074:** marked "reused from strict-sufficiency result" (results.md:1527).
  - **WSA0082/WSA0083:** original bounds retained, and not relabelled as supplementary (results.md:1553, :1555).
  - **Pooled and crosstab baseline rows:** no bounds, status R/A.
  - **Hard-case rows:** unchanged (A, or SD for subsets).
  - **Rendered totals:** 37 new, 1 reused, 2 retained.
- **Metadata.** 38 `result_items` carry supplement provenance, with correct displayed bounds, origin and original status "unavailable_in_source". There are 74 `supplement_interval_cell` and 2 `reused_interval_cell` lineage entries, with no value mismatch.
- **Missing versus zero.** No row with a non-reported interval status shows bounds. Zero lower bounds render as `0.0` with status R, distinct from blank unavailable cells.
- **Paths and disclosures.**
  - All cited repository paths resolve.
  - Section 0 discloses the supplement as a later dated calculation, not a historical export (results.md:21, :41–47).
  - The report status is INCOMPLETE with 69 unresolved entries (results.md:5). The filename does not imply that the study is complete.
- **Unresolved entries.** Appendix A has 69 contiguous entries identical to `run_metadata.unresolved_items`, which in turn are field-for-field identical to the pre-supplement Task B reference in `followup_metadata.json`. The Section 0 rollup matches the metadata.

## 10. Unresolved entries — implications (statuses not changed)

| Entry | Current state | Evidence from this audit | Recommendation |
|---|---|---|---|
| U0003 (strata code snapshot) | Open (results.md:2322) | The code committed ~17 h after the run (`298471a`) equals HEAD, and the strata dependencies are unchanged from run HEAD `cc5cf7d`. Independent exact reproduction of every output, including 48,000 replicates. | Keep open: run-time identity is still not provable. Consider annotating the numerical corroboration. |
| U0005 (strata replacement CI level) | Open (results.md:2324) | The saved `hard_case_stratum_summary.md` heads the column "Δmin [95% CI]", and all 12 bounds equal the 0.025/0.975 Type 7 quantiles of the saved replicates (V00632–V00755). | Owner to review whether this saved-output evidence resolves the entry. It would also make the S11T001–006 annotation consistent with S11T013–018. |
| U0035, U0037, U0039, U0041, U0045 (baseline distribution intervals) | Open | Named-coder and record rows now carry 37 supplementary intervals plus 1 reuse. The pooled "all coders", Unclear response-level and crosstab rows in the same sources still have none, and the historical omission reason is not recovered. | Keep open. Consider annotating the partial presentational remedy. |
| U0043, U0047 (taxonomy issue and coherence, baseline) | Open | Pooled conditional responses; a methodological decision is pending. | No change. |
| U0036, U0038, U0040, U0042, U0044, U0046, U0048 (hard-case distributions) | Open | Out of supplement scope. | No change. |
| U0049–U0067 (strata intervals not exported) | Open | The strata code computes intervals only for model–coder set metrics and Δmin; no saved reason exists. No interval was computed here. | No change. |
| U0068 (`mean_model_coder_*` naming) | Open (results.md:2387) | Values verified numerically as human-pair means for all 18 rows (independent of code). The name remains misleading. | Consider annotating that the value semantics are now established from data. The historical-code clause stands. |
| U0069 (omission reason) | Open (results.md:2388) | The supplement is a partial presentational remedy only. The reason is undocumented, and the scope still includes pooled and excluded rows. | Keep open, consistent with results.md:2390. |

## 11. Findings

Severity scale:
- **Material:** alters a reported value, population, denominator or method. None found.
- **Low:** could mislead interpretation or limits reproducibility, with no numerical change.
- **Info:** accuracy or presentation note.

### Material findings

None.

### Non-material findings

**F-01 · Methodological concern · Low — forced accompanying-tag records inside the strata are undisclosed** (`M-STRATA-FORCED`, V00025)
- **What.** 5 of the 75 stratum records were forced into the sample by the accompanying-tag rule (protocol ¶57): 4 of 25 in domain_only (16%), 1 of 25 in purpose_only, 0 in both. They were not randomly selected within their stratum.
- **Where it should be disclosed.** Neither `methods_hard_case_strata.md`, `hard_case_stratum_summary.md` nor report §11 (results.md:1874) mentions this.
- **Effect.** The record bootstrap treats each stratum as a simple random sample. The percentile intervals therefore describe resampling variability of these 25 records only; their sampling interpretation is weaker for domain_only. No reported value changes.

**F-02 · Methodological concern · Low — small-n percentile bootstrap intervals** (`M-STRATA-SMALLN`, V00859)
- **Lattice and zero bounds.** With n=25, exact-set replicates lie on a 1/25 lattice. Intervals for 1–3 matches reach 0.000:
  - both, Purposes, L-C: [0.000, 0.120]
  - purpose_only, Purposes, L-A: [0.000, 0.200]
  - purpose_only, Purposes, L-B: [0.000, 0.240]
- **Coverage.** Percentile-bootstrap coverage is unreliable at this size and near the boundaries.
- **Δmin and multiplicity.** Four of six Δmin intervals exclude zero, with no multiplicity control and shared draws across pairs and strata.
- **Framing.** The outputs correctly apply no triggers and call the results descriptive. Readers should not treat the intervals that exclude zero as evidence of population-level replacement effects.

**F-03 · Interpretation · Info — shared human difficulty limits attribution** (`N-STRATA-INTERP`, V00856–V00858)
- **Claim versus pattern.** The summary preface says the results "assess whether that sampling signal corresponded to lower subsequent Fable/scratch-coder agreement in the intended dimension". The pattern is mixed in domain_only: exact-set is lower for Domain, but Jaccard is higher (+0.044).
- **Human agreement.** Human–human Domain agreement is also lowest in domain_only (0.253), so the lower model–coder agreement may reflect intrinsic ambiguity rather than model error.
- **Overclaiming.** The summary does not overclaim. A sentence pointing readers to the human–human context would help.

**F-04 · Reporting (annotation) · Low — U0005 evidence exists in the saved outputs** (V00632–V00755; V01659, V01685, V01711, V01737, V01763, V01789)
- **Inconsistency.** Report §11 labels the strata Δmin intervals "confidence unresolved" (results.md:1887 and the corresponding lines), yet labels the exact-set and Jaccard intervals from the same run "confidence 95%".
- **Saved evidence.** The strata summary heads the Δmin column "[95% CI]", and the bounds are the 2.5/97.5 percentiles.
- **Recommendation.** Owner review of U0005 (§10). This audit does not change the entry.

**F-05 · Reporting (wording) · Info — stratum-label scope** (`N-STRATA-LABEL-SCOPE`, V00024)
- **Wording.** `methods_hard_case_strata.md` says "The POST-019 hard-case-stratum field assigns every record to exactly one pre-existing 25-record … stratum". That field also labels 51 of 150 baseline records (20/20/11) and is blank for 99.
- **Effect.** None. The code restricts to `sample_family=='hard_case'`, so "every hard-case record" is what is meant and implemented.

**F-06 · Historical provenance limitation · Low — supplement cannot be re-executed as recorded** (`N-WILSON-HIST-REPRO`, V01625, V01627, V01629, V01631)
- **Code changed after the run.** Commit `5559da3` (2026-09-08) changed `wilson_supplement.py` and `scratch_coder_consolidated/supplement.py`. The recorded invocation lacks the argument that current code now requires. The historical code is recoverable at `dcf763b`.
- **Input deleted.** The recorded Task B metadata input was deleted by the documented housekeeping. Its hash survives in the canonical deletion inventory, but the bytes do not.
- **Effect.** Historical re-execution is blocked. The numerical results are unaffected, and were verified independently here.

**F-07 · Governance record · Info — approval text for the 37-row scope not archived** (`N-WILSON-APPROVAL-RECORD`, V00864, BLOCKED)
- **What is missing.** The methods cite "the explicit selected scope in the user instruction". No repository record of that instruction was found, and no deviation-log or amendment entry covers the supplement or the strata diagnostic. The scope assessment itself left the governance route unsettled.
- **What was verified instead.** The consistency of the scope list across five artefacts.
- **Owner decision.** Whether a record is required is a governance matter outside this audit.

**F-08 · Methodological note · Info — inferential reading of the new intervals** (`M-WILSON-INFERENCE`, V00880)
- **Unit.** Each included row has one indicator per sampled project, consistent with simple random sampling of records (¶52). Ordinary Wilson intervals are defensible.
- **What the intervals describe.** Named-coder intervals describe a fixed coder's rating proportion over register records. Record-majority and Unclear rows are conditional on the fixed three-coder panel. None generalises to other coders (the methods say so for coders).
- **Finite population.** No finite-population correction is applied. With about 150 of 1,286 eligible records (derived from the protocol: 1,308 cleaned records minus 22 exclusions), the intervals are slightly conservative.
- **Simultaneous coverage.** Intervals within a distribution are marginal, not simultaneous, as stated. `records_with_majority_use` overlaps `records_with_2_of_3` and `records_with_3_of_3`.
- **Pooled rows.** They correctly did not receive ordinary intervals.

**F-09 · Reporting (prose) · Low — Section 8 introduction does not mention the supplement** (`N-REPORT-S8-PROSE`, V03496)
- **What it says.** results.md:1462 reads "Counts have no confidence interval. Baseline subset proportions carry exported 95% Wilson-score intervals…". It does not mention that the distribution rows in the same section now show supplementary intervals.
- **Where it is disclosed.** Cell annotations and Section 0 disclose the supplement, so the prose is incomplete rather than wrong.

**No computational errors were found.**

## 12. Coverage

**Independently recomputed from frozen inputs.**
- Strata membership and all joins.
- Every exported stratum point estimate (378 numeric and count checks).
- All 84 interval bounds, from both the saved replicates and regenerated draws.
- All 48,000 saved replicate rows.
- Valid and invalid counts.
- All 39 summary display lines.
- Pooled reconciliation: 6 Stage B rows, 8 Stage A α values and 2 Δmin values.
- All 37 new Wilson rows: counts from the raw export, bounds, boundaries and metadata.
- 2 retained and 1 reused interval.
- Every in-scope report cell in S8T001–S10T004 and S11T001–S11T018, plus metadata lineage and all 69 unresolved entries.

**Relied on prior audit evidence only.**
- Stage A exposure and structural sensitivities, and the COVID and Equity replacement results.
- Stage B per-label, kappa, macro and tag metrics.
- These are dependencies of neither artefact, except the pooled hard-case quantities, which were re-derived anyway.

**Not checked.**
- Re-execution of the official stratified draw (V00027; embargo).
- The export's hidden stratum fields as a membership source (V00043; blank).
- The archived approval instruction (V00864; not located).
- Historical re-execution of the supplement generator (V01625, V01631).
- Report sections and appendices outside the scope in §2 (Sections 1–7, S9T005–S9T008, S10T005–S10T006 values, Appendix B source maps beyond the in-scope tables).

## 13. Limitations

- **Independence.** The reference code is new and imports no production module. It was written by the same assistant family that wrote the prior audits, and it reuses documented conventions, some of which could only be discovered from production code: sorted Record ID order, generator re-seeding per group, and complete-case handling. Each such convention was confirmed by exact reproduction rather than assumed.
- **Taxonomy labels.** Label identity was checked against the frozen REDCap dictionary (RED-036), not independently against `taxonomy_data_dictionary.yaml`.
- **Test suites.** Production tests were not run, to avoid writing caches.
- **Judgement.** The interpretation assessments (§7.5, F-01–F-03, F-08) are statistical judgements. They are separate from the numerical verification.

## 14. Outside this audit

The following were excluded by instruction and are not failures of the completed scratch-coder analyses:
- Project-owner response collection and outcomes (ongoing).
- Adjudication results and the adjudication population.
- Secondary review, release decisions and senior sign-off.
- Any new stability analysis or model comparison.
- Governance decisions on whether the post hoc strata or the supplement need deviation or amendment records (F-07).

## 15. Reproduction and integrity

From the repository root:

```sh
.venv/bin/python -B analysis/review/remaining_validation_20260914T071731Z/reference_code/run_all.py
.venv/bin/python -B analysis/review/remaining_validation_20260914T071731Z/reference_code/finalize_metadata.py
```

- **Runtime:** about 40 s.
- **Outputs:** `run_all.py` rewrites `verification_ledger.csv` and `reference_results_summary.json`. `finalize_metadata.py` re-hashes the 141 inputs listed in `.input_hashes_before.json` and writes `audit_metadata.json`, which holds hashes, versions, seed, criteria and git state.
- **Integrity result:** all 141 inputs unchanged. Working tree unchanged outside this directory. Masking scan: 0 identifier or title hits.
