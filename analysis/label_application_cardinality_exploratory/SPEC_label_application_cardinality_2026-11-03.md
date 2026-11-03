# Specification — Exploratory: individual-rater label application, label-set cardinality and abstention

## Dates

- Specification and instruction date: 3 November 2026 (investigator instruction for the figure revision that makes label application by individual coders main Figure 3).
- Specification creation date: 2026-11-03. Not backdated.
- Written before any calculation code for this run. The investigator instructed that nothing be committed or pushed in this session, so this file is **not committed before the run**; its SHA-256 at the time of the run is recorded in `run_metadata.json` instead. Commit it together with, or before, the outputs.

## Status

Exploratory, descriptive, and **not preregistered**. The protocol search below found no preregistered per-coder label prevalence, per-rater label-set cardinality or per-rater abstention summary. Results must be labelled exploratory and descriptive wherever they appear, and must not be described as preregistered.

Stream: scratch-coder analysis (Stream A). Separate from the preregistered analyses, the figure pipeline and the other exploratory runs. Changes no existing result, classification, protocol or taxonomy artefact. No primary statistical analysis is rerun.

## Purpose

The former label-application figure compared Fable 5 with the labelwise coder majority. A labelwise majority set is a different estimand from any individual rater's set: aggregation can raise or lower set size, and the majority is not guaranteed to contain fewer labels than individual sets. This run produces the individual-rater counts needed to show, for each label, whether Fable 5 applied it more often than every coder, less often than every coder, or within the coders' observed range, and to describe willingness to classify and set size separately for each rater.

These are marginal counts. They do not show whether raters labelled the same records, and an outside-range count is not evidence of over-labelling, under-labelling or error.

## Population, raters and dimensions

- Population: random baseline only (n = 150; POST-009). The hard-case sample is not used.
- Raters: C01, C02, C03 and Fable 5 (production output MOD-006). The labelwise coder majority is used only for a reconciliation check (below); it is not a rater in any output.
- Dimensions: Research Domains and Analytical Purposes. The binary tags are excluded (their counts are already exported in S2T013–S2T016).

### Valid, common records

For each dimension, the analysis set is the baseline records on which **all four raters** have a complete, structurally valid, non-missing label set for that dimension (coder response complete and passing the frozen structural validator; model set present). The count of valid common records, and any record excluded with its reason category, is reported per dimension. No record is imputed. If the valid common set differs between dimensions, each dimension uses its own set and the difference is reported.

## Definitions

Let *U* = Unclear from Register Entry. For rater *r* and record *i*, let *S(r,i)* be the rater's label set in the dimension, and *S⁺(r,i) = S(r,i) \ {U}* its substantive part.

### LAC1T001 — Label application counts (per label, per rater)

For every label in the frozen rc2 taxonomy for the dimension, including *U* and including labels with zero applications:

- `count(r, label)` = number of valid common records with label ∈ *S(r,i)*.
- `coder_min`, `coder_max` = minimum and maximum of the three coder counts.
- `fable_position` = `above_all_coders` if Fable 5's count > `coder_max`; `below_all_coders` if < `coder_min`; otherwise `within_coder_range` (inclusive of the bounds). Descriptive placement only.
- Denominator: number of valid common records for the dimension.

### LAC1T002 — Cardinality and abstention (per rater, per dimension)

1. **Mean substantive labels per record** = Σᵢ |*S⁺(r,i)*| / N, over all N valid common records. A record assigned *U* contributes zero substantive labels. This measure combines willingness to classify with set size.
2. **Records assigned Unclear** = number of records with *U* ∈ *S(r,i)*; proportion = that count / N.
3. **Mean substantive labels among substantively classified records** = Σᵢ |*S⁺(r,i)*| / Nₛ(r), where Nₛ(r) = number of records with |*S⁺(r,i)*| ≥ 1. Nₛ(r) is reported beside the mean as the conditional denominator. This describes set size conditional on classifying; the record subset can differ between raters.

Also reported for reconciliation, not interpretation: total label applications including *U*, total substantive applications, records with an empty set, and records where *U* co-occurs with a substantive label.

*U* is never counted as a substantive label. Majority-set cardinality is never substituted for an individual rater's cardinality.

## Structural and reconciliation checks (run aborts on failure)

- Authority hashes verified as in the other exploratory runs (`verify_authorities`).
- Baseline n = 150; three coder responses per record.
- No empty sets and *U* exclusive within every rater set (expected from the frozen validator; any exception is reported, not silently corrected).
- Fable 5 per-label counts equal the exported `baseline_model_positive_n` in S5T001 (domains) and S5T002 (purposes).
- Labelwise coder-majority counts recomputed from the same record-level sets equal the exported `baseline_human_majority_positive_n` in S5T001/S5T002 (a check that the coder sets are read correctly).
- Fable 5 totals equal the approved G.12 derivations: all applications 199 (domains) and 160 (purposes); substantive-only 198 and 159.
- Per-coder *U* uses summed over coders equal the exported `coder_response_uses` count in S10T001/S10T002.

## Exclusions

- No hypothesis tests, no p-values, no new confidence intervals or bootstrap.
- No pooling with the hard-case sample.
- No claims of correctness, over-application, under-application or error.
- No record-level output; outputs are aggregate counts only, so no restricted output is written.
- No adjudication findings and no project-owner responses are read.

## Protocol search

Searched: `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` (PRO-018, SHA-256 `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77`), full text, for cardinality, number of labels, labels per record, prevalence, marginal, label count, each coder's, per coder.

- Tag prevalence and rare-label human-supported and production-model positive counts are preregistered (§8.4, §8.8). Per-coder label prevalence for domains and purposes, per-rater set cardinality and per-rater abstention: **not found**.

## Prior-result search

Searched: `analysis/` excluding `analysis/audits/` (cardinality, per_coder_label, coder_positive_n, labels_per_record, mean_set_size), and `DEA_paper/sources/results.md`.

- Per-coder per-label counts: **not found**. S5T001/S5T002 export coder-majority and Fable 5 counts only; S10T001/S10T002 export pooled coder uses of *U*.
- Cardinality: the consensus-state run (CST1T001–CST1T020) exports model-set and majority-set cardinality within consensus states only. Individual-coder cardinality: **not found**.

## Data and code (reused, not modified)

Shared Stage A loader `analysis.scratch_coder_stage_a.panels.build_stage_a_data`, with the same authorities as the consensus-state run: raw export POST-028, baseline sample POST-009, formal assignment crosswalk POST-019, production model output MOD-006, taxonomy MOD-001, label mapping RED-017, structural validator RED-013. Reconciliation authorities: `analysis/scratch_coder_results/results.md` S5T001, S5T002, S10T001, S10T002 (via the pass-3 figure data for S5).

## Outputs

`analysis/label_application_cardinality_exploratory/`: `LAC1T001.csv`, `LAC1T002.csv`, `results_label_application_cardinality.md`, `run_metadata.json`, `run.py`. No restricted outputs.
