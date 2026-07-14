# Pre-existing model evidence

This folder contains the verified reproducibility package for the two recovered
Fable 5 repeatability runs on the same fixed set of 201 records: the exact
Record-ID manifest, record-level diagnostics, machine-readable metrics,
verification report, and forensic recovery log. The original caches and run
metadata remain byte-for-byte at their canonical paths under
`analysis/outputs/model_comparison_fable_5_run1/` and
`analysis/outputs/model_comparison_fable_5_run2/`.

The current GPT-5.5 classifications and Fable 5/GPT-5.5 comparison were
verified locally by deterministic, offline recomputation. The package includes
the 380-record post-exclusion disagreement frame, metrics, and a verification
report. These are pre-existing model-evidence outputs, not prospective
validation samples or results.

The comparison treats the frozen `COVID-19 & Pandemic` and `Demographic
disparities / equity tag` labels as independent binary facets. The compatibility
field `any_tag_set_match` now has the documented two-facet-conjunction meaning
of `tag_set_match`; unknown tag labels fail verification. Aggregate Jaccards
are calculated directly from unrounded parsed label sets.

The recovered Fable run-cache keys were already clean. A pre-registration
upstream cleaning defect had introduced boundary whitespace into 16 later
canonical IDs; it was corrected offline in the cleaned register and current
derived outputs. No model call or classification rerun occurred, and neither
recovered run cache was modified.
