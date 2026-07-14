# Fable 5 / GPT-5.5 cross-model verification

## Conclusion

The corrected current Fable 5 and pre-existing GPT-5.5 classifications were compared locally using only the deterministic `build_comparison()` portion of `analysis/outputs/gpt55_crossmodel_stratum_run.py`. The classification/API execution path was not invoked. No model output was regenerated. An in-memory comparison against the pre-correction comparison and disagreement CSVs established that every non-ID field was unchanged after canonicalising the 16 old Record IDs.

## Agreement

- Population: 1,308 clean unique Record IDs.
- Research Domain exact agreement: 1065/1308 (81.422018348624%); mean Jaccard 0.904243124618.
- Analytical Purpose exact agreement: 1108/1308 (84.709480122324%); mean Jaccard 0.884556574159.
- Invalid GPT-5.5 records: 0.

## Disagreement frames

| Frame | Total | Domain-only | Purpose-only | Both | Tag disagreement alongside | Tag-only outside |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pre-exclusion | 386 | 186 | 143 | 57 | 12 | 37 |
| After 22 training/pilot exclusions | 380 | 182 | 143 | 55 | 11 | 37 |

`gpt55_disagreement_frame_380.csv` is a deterministic pre-existing model-evidence frame. It is not an official validation sample, active sample, reserve sample, or sample manifest.

## Hashes

- `analysis/outputs_classified_20260702_fable5/layer_classifications.csv`: `6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299`
- `analysis/outputs/gpt55_classifications.csv`: `5bb4379174e1c9b9cf7faf611712c53648bc57eea7ba1d28127ecedab16b5ded`
- `analysis/outputs/crossmodel_comparison.csv`: `d0ef698bb4f723a468f74771c6717653ef0eb83b22de3057e6badc1400bf7924`
- `analysis/outputs/crossmodel_disagreement_stratum.csv`: `574566a5c72067c483b7cccfc7571c01a1c0d1e97df7f9bb93f356c429669ca5`
- `preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv`: `cf36e6d34375d0e68bac31df8169207fc0602bc7291a64e995b9cd86141413a6`
- `analysis/outputs/gpt55_crossmodel_stratum_run.py`: `ab91280f12f730e002c57f09b0a5768fbab1fbe258caa8586f97603105f2f9ae`
- `preregistration/package/03_preexisting_model_evidence/gpt55_disagreement_frame_380.csv`: `37099bb4ddf3ba8bb66f336e29d903d46e608881c7412df404d0d13c22d4b200`

No LLM/API call occurred, no classification was regenerated, and no sample was drawn.
