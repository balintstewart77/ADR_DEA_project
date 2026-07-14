# Fable 5 run-to-run stability verification

## Conclusion

The exact underlying Fable 5 caches were recovered in their original canonical directories and verified. The classifications pre-existed registration. Both run metadata files date the independent runs to 2 July 2026, and the tracked production metadata first entered Git at `fdc13fdcafcacafbb86d7818fe1485be0b1ed912` (2026-07-02T12:29:29+01:00) while naming Run 1 as its seed cache.

The recovered source caches were already at the canonical repository paths. They were not copied, rewritten, reformatted, normalised, or otherwise modified.

## Provenance and population

- Model: `claude-fable-5` (Fable 5).
- Prompt/taxonomy: `dict-1.0-rc2`.
- Comparison population: 201 exact Record IDs; both cache key sets and the recovered sample CSV agree.
- Run metadata contains disjoint provider response IDs, corroborating two independent executions.
- Run 1 was the 201-entry seed cache for the current production output.
- Corrected cleaned register: `preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv` (1308 rows); its canonical Record-ID set matches production exactly.

## Reproduced metrics

- Research Domain exact-set agreement: 191/201 (95.0%).
- Mean Research Domain Jaccard: 0.974295190713 (displayed as 0.974).
- Analytical Purpose exact-set agreement: 185/201 (92.0%).
- Mean Analytical Purpose Jaccard: 0.935323383085 (displayed as 0.935).
- COVID-19/pandemic tag agreement: 201/201 (100.0%).
- Demographic-disparities/equity tag agreement: 197/201 (98.0%).
- Joint two-tag agreement: 197/201 (98.0%).
- All-component agreement: 171/201 (85.1%).
- Invalid or failed classifications: 0.

## Production linkage and Record-ID migration

All 201 Run 1 classifications match the corrected 1308-row production output. The recovered run keys were already clean; the direct canonical linkage now requires:

- No Record-ID mapping was required.

Before registration, an upstream cleaning-order defect was found: 16 later canonical Record IDs inherited boundary spaces or CR/LF from the raw public register even though Project ID was subsequently stripped. The central Record-ID assignment function now normalises boundary whitespace and enforces control-character, nonblank, and uniqueness invariants. Current Fable/GPT and deterministic outputs were rekeyed offline. No classification array, rationale, fingerprint, or other model output was regenerated.

Project `2023/211` was not in the 201-record comparison sample. The production metadata and reviewed duplicate-ruling report separately record its collapse to one retained unsuffixed Record ID; no mapping for it was invented or applied here.

The previously recorded production hashes identify the pre-correction dirty-ID files. The corrected production output and metadata therefore have new hashes. Deterministic semantic checks prove that classification content is unchanged apart from Record-ID keys and the explicit metadata provenance annotation.

## Determinism and security

No model or API call was made. Verification used local JSON/CSV/YAML parsing, exact labels, unordered sets, ordinary set Jaccard, exact audit mappings, and local hashing. The recovered caches contain public register identifiers, classifications, rationales, prompt fingerprints, and non-sensitive run metadata. A targeted credential scan found no secret indicator.

## Limitations

This is one pre-existing run pair on one fixed 201-record sample. Filesystem timestamps are recovery metadata rather than proof of authorship; the tracked 2 July production metadata provides the stronger Git provenance link. The raw June register retains its source whitespace as an unchanged snapshot; only cleaned/current derived identifiers were corrected.

## Source hashes

- `analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json`: `e888422a3e46f8c3746c8560327e01fdb0e307491363e65a49c86ea78cb79156`
- `analysis/outputs/model_comparison_fable_5_run1/run_metadata.json`: `90553e77b8a262bb7ff73668dc3336ab721bbd39650780ed86ac4660d36ace50`
- `analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json`: `77cd247f06b0d966334726e17de858d4b16c4f5bbe67e246b653e007fd676fff`
- `analysis/outputs/model_comparison_fable_5_run2/run_metadata.json`: `e3f7cc0e9ffd38b882c80e52d359d19d50cc1236c20c284716f72acfc76c0426`
- `analysis/outputs/model_comparison_sample.csv`: `0e6c33456c1aaf1695bc089adb29d96e2dcb4b26a43feb8cb04262d6e8c46271`
- `analysis/outputs_classified_20260702_fable5/layer_classifications.csv`: `6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299`
- `analysis/outputs_classified_20260702_fable5/run_metadata.json`: `0fd030520130542b70c3de719c136d9df6c66147c1bbfaa30108abb16e8671e4`
- `preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv`: `a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1`
- `taxonomy_data_dictionary.yaml`: `7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de`

Verification script: `analysis/verify_fable_run_stability.py` at `940b8cc6243ae6aa636a9dc779390c2f792e1bfaca07a2e09998edb9f3ee88a1`.
