# Scratch-coder Stage A headline summary

Preliminary — frozen scratch-coder data. Stage A aggregate analysis complete. Label-specific diagnostics, disagreement adjudication and project-owner evidence are not yet incorporated.

## 1. Completion and QA

The frozen panel reconciles to 3 coders × 225 records (675 formal responses): 150 random-baseline and 75 hard-case records. Detailed response/project denominators are in [qa_summary.csv](qa_summary.csv).

## 2. Headline replacement analysis

| Dimension | N | Human α | Replace A α | Replace B α | Replace C α | ΔA | ΔB | ΔC | Δmin | 95% CI Δmin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Research Domains | 150 | 0.526 | 0.583 | 0.528 | 0.574 | 0.057 | 0.002 | 0.047 | 0.002 | [-0.035, 0.039] |
| Analytical Purposes | 150 | 0.292 | 0.276 | 0.249 | 0.358 | -0.016 | -0.043 | 0.065 | -0.043 | [-0.090, -0.002] |
| Demographic disparities / equity | 150 | 0.512 | 0.468 | 0.431 | 0.452 | -0.044 | -0.081 | -0.060 | -0.081 | [-0.202, -0.006] |
| COVID-19 & Pandemic | 150 | 0.940 | 0.940 | 0.941 | 0.971 | 0.000 | 0.001 | 0.032 | 0.000 | [0.000, 0.000] |

Mechanical review-trigger indicators:

- Research Domains: all three deltas below zero = NO; Δmin CI entirely below zero = NO.
- Analytical Purposes: all three deltas below zero = NO; Δmin CI entirely below zero = YES.
- Demographic disparities / equity: all three deltas below zero = YES; Δmin CI entirely below zero = YES.
- COVID-19 & Pandemic: all three deltas below zero = NO; Δmin CI entirely below zero = NO.

## 3. Register sufficiency

**Random baseline.** Sufficient: 92/150 (61.3%); Partially sufficient: 55/150 (36.7%); Insufficient: 2/150 (1.3%); No majority / split judgement: 1/150 (0.7%).
Broad/strict subsets: broad_register_usable: 148/150 (98.7%; 95% Wilson CI 95.3%–99.6%); strict_register_sufficient: 92/150 (61.3%; 95% Wilson CI 53.3%–68.8%).
**Hard case (diagnostic).** Sufficient: 42/75 (56.0%); Partially sufficient: 30/75 (40.0%); Insufficient: 0/75 (0.0%); No majority / split judgement: 3/75 (4.0%).
Broad/strict subsets: broad_register_usable: 75/75 (100.0%); strict_register_sufficient: 42/75 (56.0%).

## 4. Sufficiency-conditioned replacement

| Population | Dimension | N | Δmin | 95% CI |
|---|---|---:|---:|---:|
| baseline | Research Domains | 150 | 0.002 | [-0.035, 0.039] |
| baseline | Analytical Purposes | 150 | -0.043 | [-0.090, -0.002] |
| baseline | Demographic disparities / equity | 150 | -0.081 | [-0.202, -0.006] |
| baseline | COVID-19 & Pandemic | 150 | 0.000 | [0.000, 0.000] |
| baseline_broad_usable | Research Domains | 148 | 0.004 | [-0.033, 0.040] |
| baseline_broad_usable | Analytical Purposes | 148 | -0.041 | [-0.090, 0.001] |
| baseline_broad_usable | Demographic disparities / equity | 148 | -0.082 | [-0.199, -0.006] |
| baseline_broad_usable | COVID-19 & Pandemic | 148 | 0.000 | [0.000, 0.000] |
| baseline_strict_sufficient | Research Domains | 92 | 0.042 | [0.001, 0.076] |
| baseline_strict_sufficient | Analytical Purposes | 92 | 0.014 | [-0.035, 0.059] |
| baseline_strict_sufficient | Demographic disparities / equity | 92 | -0.065 | [-0.226, 0.021] |
| baseline_strict_sufficient | COVID-19 & Pandemic | 92 | 0.000 | [0.000, 0.000] |

## 5. Taxonomy fit

**Random baseline.** Fit: 119/150 (79.3%); Partial Fit: 12/150 (8.0%); No Fit: 0/150 (0.0%); Cannot assess from register entry: 6/150 (4.0%); No majority / split judgement: 13/150 (8.7%).
Applicable issue responses: Missing or inadequately represented category: 28/88 (31.8%); Ambiguous or overlapping category boundaries: 76/88 (86.4%); Other taxonomy problem: 11/88 (12.5%).
**Hard case (diagnostic).** Fit: 54/75 (72.0%); Partial Fit: 11/75 (14.7%); No Fit: 0/75 (0.0%); Cannot assess from register entry: 1/75 (1.3%); No majority / split judgement: 9/75 (12.0%).
Applicable issue responses: Missing or inadequately represented category: 18/56 (32.1%); Ambiguous or overlapping category boundaries: 45/56 (80.4%); Other taxonomy problem: 9/56 (16.1%).

Taxonomy-issue frequencies use only applicable Partial Fit/No Fit coder responses; percentages may sum to more than 100%. See [taxonomy_issue_summary.csv](taxonomy_issue_summary.csv).

## Timing

A6 not defensibly estimable from the frozen REDCap timestamp fields: the export contains no formal scratch_coder_timestamp values and no review-start timestamp for the same coding review.

> The random baseline is the preregistered population-level replacement analysis. The hard-case sample was deliberately disagreement-enriched and is diagnostic rather than representative.

> Replacement-panel differences estimate the change in three-member-panel reliability when the production model replaces one trained coder. They are not direct measures of classification accuracy.

> Stage A does not identify why individual disagreements occurred. Record-level disagreement adjudication remains deliberately source-masked and has not begun.

Full-precision values are in [replacement_panel_results.csv](replacement_panel_results.csv), [replacement_delta_results.csv](replacement_delta_results.csv), and [bootstrap_replicates.csv](bootstrap_replicates.csv).
