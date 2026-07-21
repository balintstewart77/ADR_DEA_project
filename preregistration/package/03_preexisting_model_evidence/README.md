# Pre-existing model evidence

This folder contains the verified reproducibility package for the two recovered
Fable 5 repeatability runs on the same fixed set of 201 records: the exact
Record-ID manifest, record-level diagnostics, machine-readable metrics,
verification report, and forensic recovery log. The original caches and run
metadata remain byte-for-byte at their canonical paths under
`analysis/outputs/model_comparison_fable_5_run1/` and
`analysis/outputs/model_comparison_fable_5_run2/`.

The GPT-5.5 classifications are frozen at
`../../../analysis/releases/gpt55_crossmodel_20260707/gpt55_classifications.csv`.
That tracked canonical release is byte-identical to the recovered original run
output at `../../../analysis/outputs/gpt55_classifications.csv`; formal
validation uses the release path. The Fable 5/GPT-5.5 comparison was verified
locally by deterministic, offline recomputation. The package includes
the 380-record post-exclusion disagreement frame, metrics, and a verification
report. These are pre-existing model-evidence outputs, not prospective
validation samples or results.

A 1,309-row restricted intermediate was temporarily used during excluded-pilot
review but was not retained as a formal study artefact. All formal provenance,
sampling and validation now use the recovered frozen 1,308-row canonical
GPT-5.5 release. No direct scientific comparison with that absent intermediate
is claimed.

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

The verified stability and cross-model artefacts are hash-linked into
`../02_taxonomy_prompt_and_model/production_release_manifest.yaml` and form the
frozen pre-existing-evidence component of the completed Phase 3 release.
