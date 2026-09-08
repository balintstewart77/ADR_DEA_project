# Wilson scope assessment — no intervals calculated

This is a row-level eligibility assessment for a possible later supplement. It does not calculate Wilson endpoints, replace existing intervals, create an analytical source, or close a consolidation unresolved entry.

## Evidence and scope

The frozen protocol (`preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx`, SHA-256 `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77`) states in §8.9, paragraph index 167: “Baseline proportions will use 95% Wilson score intervals.” Adjacent §§5.2 and 8.5 identify the 150-record random baseline, individual-coder distributions, record-majority rules, sufficiency subsets, conditional taxonomy-issue response frequencies and Unclear-use summaries.

The saved Stage A methods (`analysis/outputs_validation_scratch_20260824/methods_stage_a.md`, SHA-256 `a78393b73ad39e3bde4dd949cce99575d257938b9cfd8c72d43dfa25df6f5f67`) also document 95% Wilson intervals for baseline proportions, the broad/strict definitions, two-of-three record-majority rule, and Partial Fit/No Fit taxonomy-issue denominator. The CSVs export integer counts, denominators and proportions for all inventoried rows; only baseline `sufficiency_subset_summary.csv` rows contain Wilson endpoints. Other interval semantics remain absent from those schemas.

The broad protocol wording does not by itself establish that 450 pooled coder responses are independent binomial trials. Those rows contain three ratings per sampled project and are marked `methodological_decision_required`. Named-coder rows contain one rating per project for the named coder. Record-majority and subset rows contain one binary event indicator per project. QA design totals are separated from observed events.

No empirical independence claim is made from the summaries. No count is reconstructed, no category is summed, and no source proportion is verified or recalculated from its count and denominator.

## Inventory totals

Inventoried rows: 193. Scope decisions: `already_exported` 3, `candidate_for_later_authorised_wilson` 45, `excluded_nonbaseline` 106, `methodological_decision_required` 37, `no_inferential_interval_proposed` 2. Observational units: `individual_coder_binary` 42, `pooled_coder_responses` 79, `record_binary` 65, `structural_ratio` 7.

| Source / metric family | Unit class | Candidate later | Already exported | Decision required | Nonbaseline excluded | No inferential interval | Other exclusions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `analysis/outputs_validation_scratch_20260824/qa_summary.csv` / `qa_design_accounting` | `structural_ratio` | 0 | 0 | 0 | 5 | 2 | 0 |
| `analysis/outputs_validation_scratch_20260824/qa_summary.csv` / `qa_record_status` | `record_binary` | 8 | 0 | 0 | 19 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/qa_summary.csv` / `qa_response_status` | `pooled_coder_responses` | 0 | 0 | 5 | 10 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/sufficiency_record_distribution.csv` / `record_majority_or_subset` | `record_binary` | 3 | 1 | 0 | 4 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/sufficiency_response_distribution.csv` / `named_coder_distribution` | `individual_coder_binary` | 9 | 0 | 0 | 9 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/sufficiency_response_distribution.csv` / `pooled_all_coder_distribution` | `pooled_coder_responses` | 0 | 0 | 3 | 3 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/sufficiency_subset_summary.csv` / `record_majority_or_subset` | `record_binary` | 0 | 2 | 0 | 2 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/taxonomy_coherence_summary.csv` / `conditional_coherence_response` | `pooled_coder_responses` | 0 | 0 | 8 | 8 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/taxonomy_fit_record_distribution.csv` / `record_majority_or_subset` | `record_binary` | 5 | 0 | 0 | 5 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/taxonomy_fit_response_distribution.csv` / `named_coder_distribution` | `individual_coder_binary` | 12 | 0 | 0 | 12 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/taxonomy_fit_response_distribution.csv` / `pooled_all_coder_distribution` | `pooled_coder_responses` | 0 | 0 | 4 | 4 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/taxonomy_issue_summary.csv` / `conditional_taxonomy_issue_response` | `pooled_coder_responses` | 0 | 0 | 3 | 3 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/unclear_register_summary.csv` / `unclear_record_frequency` | `record_binary` | 8 | 0 | 0 | 8 | 0 | 0 |
| `analysis/outputs_validation_scratch_20260824/unclear_register_summary.csv` / `unclear_response_frequency_or_crosstab` | `pooled_coder_responses` | 0 | 0 | 14 | 14 | 0 | 0 |

## Existing interval and duplicate-result inventory

The two baseline broad/strict sufficiency-subset rows already export `Wilson score 95%` endpoints and are marked `already_exported`. The baseline record-majority `Sufficient` row has exactly matching exported count, denominator and proportion strings and the same saved-method definition as `strict_register_sufficient`; it links to that existing interval rather than proposing a duplicate. Hard-case subset rows retain the source `not applied (diagnostic sample)` status and remain excluded as nonbaseline. No other inventoried row exports interval columns.

## Decisions needed before any later computation

A later instruction must decide whether the protocol's broad phrase covers QA event frequencies and each named-coder and record-level distribution family as assessed here. It must explicitly decide how to handle pooled all-coder and conditional-response rows; ordinary Wilson treats trials as binomial observations and does not account for three ratings clustered within a project. This assessment neither extends the prescription to pooled rows nor substitutes a clustered or bootstrap method.

If later authorised for eligible rows, implementation checks must specify two-sided 95% Wilson score intervals without continuity correction where justified; record the implementation and version; enforce integer 0 ≤ k ≤ n with n > 0; compare the implementation's centre against k/n under a tolerance chosen only after inspecting that implementation; preserve source precision and provenance; and explicitly handle any floating-point boundary correction. No tolerance is selected here.

## Governance

The repository governance states that post-registration changes require a new version and that substantive changes also require an amendment under `preregistration/post_registration/amendments/`. It does not establish whether this proposed supplementary presentation is substantive or require a deviation-log entry for it. The documentation route and substantive-status decision therefore remain to be settled; no governance file is changed here.

The complete row-level source keys, raw cells, lineage, unit classifications, decisions, reasons, existing endpoints and equivalence link are in `wilson_scope_manifest.json`.
