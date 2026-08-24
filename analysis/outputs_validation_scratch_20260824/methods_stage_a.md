# Scratch-coder Stage A methods

## Frozen inputs

The authoritative raw input is `preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv` (POST-028; SHA-256 `29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d`). The governing protocol is PRO-018. Candidate-0.7 is represented by RED-036, parsed under RED-005/006/007 and structurally checked using RED-013. Sample membership comes only from POST-009, POST-011 and POST-019. Formal scratch coding and production classifications use the MOD-001 rc2 taxonomy. Production model L is the protected MOD-006 Fable 5 output.

## Loading, validation and panels

Rows enter the formal panel only when `validation_included=1` and their assignment, coder and source-record keys match POST-019 exactly. Each formal record must have exactly one response from C01, C02 and C03. Complete-case membership is assessed separately by classification dimension, with the same records used for ABC and every replacement panel. No response is imputed or repaired. A zero in binary fields is retained as a substantive No. Checkbox groups are parsed explicitly; taxonomy-issue checkboxes are interpreted only where `sc_taxonomy_fit` is Partial Fit or No Fit.

Completed responses are passed unchanged through RED-013 `validate_scratch`. Structurally invalid responses remain in the primary analysis; the structural sensitivity excludes an entire record if any coder response fails. Exposure-flagged responses likewise remain primary; the exposure sensitivity excludes an entire record if any response is flagged. The primary population is the 150-record random baseline. The 75 hard cases are analysed separately as disagreement-enriched diagnostics.

## Classification and agreement

Research Domains and Analytical Purposes are unordered `frozenset` values. `Unclear from Register Entry` remains a valid category and its mutual-exclusivity rules are checked by the frozen validator. The equity and COVID tags are separate binary nominal dimensions. Model classifications are split only on their frozen semicolon delimiter and validated against MOD-001.

For each dimension the code calculates Krippendorff's alpha for ABC, LBC, ALC and ABL. Domains and Purposes use the repository's MASI distance (`analysis.validation.metrics.masi_distance`); tags use nominal distance. Deltas are replacement alpha minus ABC, and `delta_min` is the minimum of the three jointly calculated deltas. Point estimates use `analysis.validation.replacement.replacement_panel_analysis` and `analysis.validation.alpha.krippendorff_alpha`. Bootstrap evaluation uses an algebraically equivalent encoded coincidence calculation and asserts equality with the canonical point estimates to 1e-12.

## Bootstrap and intervals

Each analysis uses 2,000 attempted record-level bootstrap replicates with Python's `random.Random`, seed 20260714. A draw carries the complete A/B/C/L record block; duplicate draws remain duplicated rows. All four alphas, all three deltas and `delta_min` are recalculated from the same draw. Percentile endpoints use Hyndman-Fan Type 7 linear interpolation through `analysis.validation.bootstrap.percentile`. Undefined statistics stay blank and their counts are retained. An interval is suppressed if fewer than 1,800 replicates are valid.

Baseline proportions use the repository Wilson-score implementation at 95%. Broad register-usable means at least two coders selected Sufficient or Partial; strict register-sufficient means at least two selected Sufficient. These subsets use original pre-adjudication ratings. Record-level sufficiency and taxonomy-fit majorities require two identical categories; otherwise the result is `No majority / split judgement`. `Cannot assess from register entry` is not collapsed into No Fit. Taxonomy-issue percentages use only applicable Partial Fit/No Fit responses and may sum above 100%.

## Timing and masking

The export has neither a formal review-start timestamp nor formal `scratch_coder_timestamp` values, so A6 is not defensibly estimable. Time gaps between submissions are not used. All saved outputs are aggregate. The run scans them against the real source-ID set and does not create record-level disagreement, majority-versus-model, adjudication, or per-label performance artefacts.

## Importable review API

```python
from analysis.scratch_coder_stage_a import (
    load_frozen_export, validate_export, build_panels,
    run_replacement_analysis, bootstrap_replacement_analysis,
    derive_sufficiency_subsets, summarise_taxonomy_fit,
)

raw = load_frozen_export()  # inspect shape/columns only; do not display response rows
data = validate_export()
subsets = derive_sufficiency_subsets(data)
panels = build_panels(data, data.baseline_ids, "Research Domains")
point = run_replacement_analysis(panels, "Research Domains")
bootstrap = bootstrap_replacement_analysis(panels, "Research Domains")
taxonomy = summarise_taxonomy_fit(data)
```

The command-line run is authoritative; notebook code imports these functions rather than duplicating the implementation.
