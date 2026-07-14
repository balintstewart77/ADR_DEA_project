# Record-ID normalisation verification

Status: **PASSED**. The current authoritative and preregistration-candidate
Record-ID fields and JSON mapping keys listed below contain no leading or
trailing whitespace, CR, LF, tab, NBSP, DEL, or other prohibited ASCII control
character. Stripping introduces no new duplicate group.

This audit was performed locally after the deterministic 16-ID migration. No
classification or model call was made. The unchanged raw source snapshot is
deliberately excluded from the clean-output requirement.

| Artefact | Path | Rows / entries | ID values | Unique IDs | Whitespace / control violations | Duplicate groups introduced by stripping | Result |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Frozen cleaned register | `preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| Deterministic register properties | `analysis/outputs_deterministic_rc2/register_properties.csv` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| Organisation review example-ID lists | `analysis/outputs_deterministic_rc2/quality/organisation_names_for_review.csv` | 281 | 1,015 | 787 | 0 | 0 | PASS |
| Fable all-project output | `analysis/outputs_classified_20260702_fable5/all_projects_classified.csv` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| Fable layer classifications | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| Fable production cache keys | `analysis/outputs_classified_20260702_fable5/llm_layer_cache.json` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| GPT-5.5 classifications | `analysis/outputs/gpt55_classifications.csv` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| GPT-5.5 cache keys | `analysis/outputs/gpt55_gpt-5.5_dict-1.0-rc2_llm_layer_cache.json` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| Cross-model comparison | `analysis/outputs/crossmodel_comparison.csv` | 1,308 | 1,308 | 1,308 | 0 | 0 | PASS |
| Cross-model disagreement frame | `analysis/outputs/crossmodel_disagreement_stratum.csv` | 386 | 386 | 386 | 0 | 0 | PASS |
| Packaged post-exclusion disagreement frame | `preregistration/package/03_preexisting_model_evidence/gpt55_disagreement_frame_380.csv` | 380 | 380 | 380 | 0 | 0 | PASS |
| Reviewed migration audit (`new_record_id`) | `analysis/outputs/reviewed_duplicate_record_id_migration_audit.csv` | 2,616 | 2,616 | 1,308 | 0 | 0 | PASS; paired Fable/GPT rows explain expected raw duplicates |
| Fable exact sample source | `analysis/outputs/model_comparison_sample.csv` | 201 | 201 | 201 | 0 | 0 | PASS |
| Recovered Fable Run 1 cache keys | `analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json` | 201 | 201 | 201 | 0 | 0 | PASS |
| Recovered Fable Run 2 cache keys | `analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json` | 201 | 201 | 201 | 0 | 0 | PASS |
| Fable evidence manifest | `preregistration/package/03_preexisting_model_evidence/fable_run_stability_201_record_manifest.csv` | 201 | 201 | 201 | 0 | 0 | PASS |
| Fable record diagnostics | `preregistration/package/03_preexisting_model_evidence/fable_run_stability_record_diagnostics.csv` | 201 | 201 | 201 | 0 | 0 | PASS |
| Normalisation audit corrected IDs | `preregistration/package/01_source_and_cleaning/record_id_whitespace_normalisation_audit.csv` | 16 | 16 | 16 | 0 | 0 | PASS |
| Training/pilot exclusion candidate | `preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv` | 22 | 22 | 22 | 0 | 0 | PASS; no sample manifest generated |

The raw file `data/dea_accredited_projects_20260601.csv` retains 17
whitespace-bearing source `Project ID` values by design and remains byte-exact
at SHA-256
`fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892`.
It is a raw source snapshot, not a canonical cleaned output.

Older `analysis/outputs_v3/`, `analysis/outputs_v4_*`, model-selection,
Opus/Sonnet, and other archived experiment directories were not rewritten.
They remain historical and are not designated current by this report.
