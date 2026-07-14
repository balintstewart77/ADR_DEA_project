# Fable 5 stability artefact recovery log

## Recovery result

The two source caches were recovered in place at their canonical repository
paths. No file was copied, moved, restored, rewritten, normalised, or deleted.
The paths labelled "original" and "canonical" below are therefore identical.

| Run | Original absolute path | Canonical repository path | Size (bytes) | Filesystem modified time (UTC) | SHA-256 before recovery | SHA-256 after verification | Copied |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| Run 1 | `C:\Users\balin\Desktop\ADR_DEA_project\analysis\outputs\model_comparison_fable_5_run1\llm_layer_cache.json` | `analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json` | 142209 | 2026-07-02T09:08:50.958880+00:00 | `e888422a3e46f8c3746c8560327e01fdb0e307491363e65a49c86ea78cb79156` | `e888422a3e46f8c3746c8560327e01fdb0e307491363e65a49c86ea78cb79156` | no |
| Run 2 | `C:\Users\balin\Desktop\ADR_DEA_project\analysis\outputs\model_comparison_fable_5_run2\llm_layer_cache.json` | `analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json` | 141219 | 2026-07-02T09:25:09.924958+00:00 | `77cd247f06b0d966334726e17de858d4b16c4f5bbe67e246b653e007fd676fff` | `77cd247f06b0d966334726e17de858d4b16c4f5bbe67e246b653e007fd676fff` | no |

At discovery, both files were ignored and untracked. `git check-ignore -v
--no-index` identified `.gitignore` line 116, `analysis/outputs/*`, as
the effective rule for both paths. The broader
`**/llm_layer_cache.json` protection also exists and remains applicable to
unrelated caches.

## Source-directory listings at recovery

The source directories were inspected with hidden and ignored content visible.
Only the cache and provenance metadata are source artefacts proposed for
tracking; the other files listed here are derived run sidecars and were not
copied into the evidence package.

### Run 1 directory

| Name | Type | Size (bytes) | Filesystem modified time (local BST) |
| --- | --- | ---: | --- |
| `quality/` | directory | - | 2026-07-02 09:54 |
| `all_projects_classified.csv` | CSV | 149882 | 2026-07-02 10:08 |
| `cross_domain_purpose.csv` | CSV | 731 | 2026-07-02 10:08 |
| `layer_a_by_year.csv` | CSV | 2621 | 2026-07-02 10:08 |
| `layer_a_totals.csv` | CSV | 362 | 2026-07-02 10:08 |
| `layer_c_by_year.csv` | CSV | 1916 | 2026-07-02 10:08 |
| `layer_c_totals.csv` | CSV | 274 | 2026-07-02 10:08 |
| `layer_classifications.csv` | CSV | 208258 | 2026-07-02 10:08 |
| `layer_summary.txt` | text | 0 | 2026-07-02 10:08 |
| `llm_layer_cache.json` | JSON | 142209 | 2026-07-02 10:08 |
| `run_metadata.json` | JSON | 7791 | 2026-07-02 10:08 |

### Run 2 directory

| Name | Type | Size (bytes) | Filesystem modified time (local BST) |
| --- | --- | ---: | --- |
| `quality/` | directory | - | 2026-07-02 10:11 |
| `all_projects_classified.csv` | CSV | 149024 | 2026-07-02 10:25 |
| `cross_domain_purpose.csv` | CSV | 783 | 2026-07-02 10:25 |
| `layer_a_by_year.csv` | CSV | 2577 | 2026-07-02 10:25 |
| `layer_a_totals.csv` | CSV | 362 | 2026-07-02 10:25 |
| `layer_c_by_year.csv` | CSV | 2014 | 2026-07-02 10:25 |
| `layer_c_totals.csv` | CSV | 305 | 2026-07-02 10:25 |
| `layer_classifications.csv` | CSV | 207298 | 2026-07-02 10:25 |
| `layer_summary.txt` | text | 0 | 2026-07-02 10:25 |
| `llm_layer_cache.json` | JSON | 141219 | 2026-07-02 10:25 |
| `run_metadata.json` | JSON | 7788 | 2026-07-02 10:25 |

## Search locations and methods

The search was read-only and returned paths or structural summaries rather
than complete project records.

- Exact expected Run 1 and Run 2 directories, including hidden, ignored and
  untracked content.
- Entire current repository, including hidden and ignored files, for all
  requested filename and content indicators.
- All local and remote-tracking branches, tag `v1.0-rc1-frozen`, the empty
  stash list, all reflogs, reachable history, deleted paths, five unreachable
  commits, 94 unreachable blobs, and three unreachable tags.
- Git LFS across all refs; no LFS entries were present.
- Desktop, Documents, Downloads, OneDrive, the separate
  `DEA_Project_Local_Reports_&_overflow` directory, `.codex`, `.claude`,
  the user temporary directory, `C:\tmp`, and the Recycle Bin without
  restoring content.
- Mounted filesystem drives. Only `C:` and the user Temp mapping were
  present; no Google Drive or Dropbox mount or home-directory sync folder was
  present.
- Six other discovered Git working trees. Their remotes were Heart Disease,
  agent interview prep, Camelyon pathology, Magnimind assignments, a Codex
  plugin cache with no remote, and a recycled Pathovis clone. None was another
  ADR DEA clone.
- Archive and backup names under the scoped user locations. No relevant archive
  candidate was found.

Search statistics for the expanded user-location pass were:

| Location | Files inspected by name | Strong name hits | Content hits | Relevant conclusion |
| --- | ---: | ---: | ---: | --- |
| Desktop outside this repository | 77509 | 2 | 8 | no Fable stability source |
| Documents | 3 | 0 | 0 | no candidate |
| Downloads | 371 | 1 | 19 | preregistration/training prose only; no source cache |
| OneDrive | 14 | 0 | 0 | no candidate |
| `.codex` | 5682 | 12 | 3 in the extension-limited pass | session/log references only |
| `.claude` | 488 | 0 | 2 in the extension-limited pass | settings/changelog references only |
| user Temp | 523 | 0 | 6 | setup logs only |
| `C:\tmp` | 59 | 9 | 5 | prior local verification helpers; no original cache |
| Recycle Bin | 386 | 0 | 6 | unrelated notebooks/markdown and Pathovis clone |

A second targeted search included Codex and Claude JSONL/file-history content.
It located narrative references and the 2 July Codex session that created the
model-comparison work, but no second byte copy of either source cache.

## Plausible-candidate inventory

The following files were treated as plausible source, provenance, metric,
migration, or corroborating candidates. JSON keys and CSV columns were
inspected structurally; full rows and rationales were not printed.

| Path | Size | Modified UTC | SHA-256 | State at discovery | Structure / count / provenance | Disposition |
| --- | ---: | --- | --- | --- | --- | --- |
| `analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json` | 142209 | 2026-07-02T09:08:50.958880+00:00 | `e888422a3e46f8c3746c8560327e01fdb0e307491363e65a49c86ea78cb79156` | ignored | JSON `__meta__` + `entries`; 201; `claude-fable-5`; `dict-1.0-rc2` | authoritative Run 1 source |
| `analysis/outputs/model_comparison_fable_5_run1/run_metadata.json` | 7791 | 2026-07-02T09:08:51.493059+00:00 | `90553e77b8a262bb7ff73668dc3336ab721bbd39650780ed86ac4660d36ace50` | ignored | run metadata; 201; 21 response IDs; Fable 5 / rc2 | authoritative provenance |
| `analysis/outputs/model_comparison_fable_5_run1/layer_classifications.csv` | 208258 | 2026-07-02T09:08:51.483045+00:00 | `9257005a921594b095cc11f601d6519fb9b9d46cf71481a585f570a42d514a0b` | ignored | 201 rows, 201 Record IDs, 16 columns | derived corroboration; not unignored |
| `analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json` | 141219 | 2026-07-02T09:25:09.924958+00:00 | `77cd247f06b0d966334726e17de858d4b16c4f5bbe67e246b653e007fd676fff` | ignored | JSON `__meta__` + `entries`; 201; `claude-fable-5`; `dict-1.0-rc2` | authoritative Run 2 source |
| `analysis/outputs/model_comparison_fable_5_run2/run_metadata.json` | 7788 | 2026-07-02T09:25:10.454519+00:00 | `e3f7cc0e9ffd38b882c80e52d359d19d50cc1236c20c284716f72acfc76c0426` | ignored | run metadata; 201; 21 response IDs; Fable 5 / rc2 | authoritative provenance |
| `analysis/outputs/model_comparison_fable_5_run2/layer_classifications.csv` | 207298 | 2026-07-02T09:25:10.444995+00:00 | `72cc4ce83fc5d0f594f3b43776fadaa1af4eebe6b1185e54e48681d34b7bf8f6` | ignored | 201 rows, 201 Record IDs, 16 columns | derived corroboration; not unignored |
| `analysis/outputs/model_comparison_sample.csv` | 35200 | 2026-07-02T08:29:56.592894+00:00 | `0e6c33456c1aaf1695bc089adb29d96e2dcb4b26a43feb8cb04262d6e8c46271` | ignored | 201 rows, 201 Record IDs; seven columns | exact recovered sample source; packaged through minimal derived manifest |
| `analysis/outputs/model_comparison_agreement_metrics.csv` | 3535 | 2026-07-02T09:29:13.114783+00:00 | `c4e1ffc43d9b8e5f4db0c8d126c38bbff0206a568cb8a0bebf4e4b59a77aabc6` | ignored | 27 stored aggregate rows | corroborating only; metrics independently recomputed |
| `analysis/outputs/model_comparison_fable5_build_sample.py` | 8513 | 2026-07-02T08:29:49.880586+00:00 | `aeeb1c5e6ae35bb9bb219ec9a3841d24b87faa64c0628f80bd66ce5c43d823f4` | ignored | Python sample builder | corroborating only; not executed |
| `analysis/outputs/model_comparison_fable5_run_sample.py` | 6168 | 2026-07-02T08:43:05.128283+00:00 | `a9de6dd43b9145c6041c9308114ed747e8d33dcbda338a0acc8a2671dafa7598` | ignored | Python LLM runner | provenance only; not executed |
| `analysis/outputs/model_comparison_fable5_score.py` | 22970 | 2026-07-02T09:29:07.309189+00:00 | `5af8c034f04bd95f958784dd25ef1af6db4fbff2a7694dc1be83997c3b95a903` | ignored | Python scorer | corroborating only; not trusted as verifier |
| `analysis/outputs/instruction_model_comparison_fable5_report.md` | 14566 | 2026-07-02T09:29:13.128844+00:00 | `fee18f5c3989085305414201b3f09456f196c3515b6ea095801ff4457f452d4f` | ignored | stored report with Fable self-agreement rows | corroborating only |
| `analysis/outputs/production_run_stability_check_20260714.json` | 35364 | 2026-07-14T06:58:48.256545+00:00 | `04a9ffe74facc1aea5bc4014880cce8908781585a05b5b5edc8f38da4ae239f7` | ignored | prior local check JSON | corroborating only; independently reverified |
| `analysis/outputs/production_run_stability_check_20260714.md` | 25282 | 2026-07-14T06:58:48.257045+00:00 | `e0d11bfcd530529006a08320a29e00261044ddbfa676a4835a0954c95a699cc8` | ignored | prior local check report | corroborating only; independently reverified |
| `analysis/outputs/reviewed_duplicate_record_id_migration_audit.csv` | 343181 | correction executed 2026-07-14 | `3790fbe30797257571db11c5466099e7d2f6e3e4adb1f3086710b3222d1c437a` | ignored | 2616 audit rows; 16 dirty `new_record_id` values per source corrected offline | authoritative migration history after canonical-ID correction |
| `analysis/outputs/instruction_reviewed_duplicate_record_id_report.md` | 3594 | 2026-07-13T17:59:32.012716+00:00 | `b4da43b22f05c2811a48ace5b6ae223e7d47715d2b3e7fed9994e3ba3ea801bc` | ignored | migration report | supporting mapping evidence |
| `analysis/migrate_reviewed_duplicate_record_ids.py` | 8125 | 2026-07-13T17:55:53.320447+00:00 | `f82d5cfcac2e781b7f6ebf5f149bfd44489627426b7dc4d5d9c8aa5bc499fb73` | tracked | offline exact-fingerprint migration implementation | supporting mapping evidence |
| `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | 1252471 | correction executed 2026-07-14 | `6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299` | tracked | 1308 clean unique Record IDs; classification fields semantically unchanged | authoritative corrected production output |
| `analysis/outputs_classified_20260702_fable5/run_metadata.json` | 37210 | correction executed 2026-07-14 | `0fd030520130542b70c3de719c136d9df6c66147c1bbfaa30108abb16e8671e4` | tracked | Fable 5 / rc2; 201 seed, 1108 fresh; explicit offline correction provenance | authoritative corrected production metadata |
| `C:\tmp\production_stability_verified_data_20260714.json` | 25337 | 2026-07-14T06:57:02.612720+00:00 | `b85ae9d7b4cac13cfc5bd9fb778622171affa8c46c2bcf90c0dec9d6040f8290` | external | prior local verification data | corroborating only |
| `C:\tmp\production_stability_verify_20260714.py` | 29877 | 2026-07-14T06:49:48.357882+00:00 | `16f406b65d0e8a85aac72bafb94ada0e824cf3e6d3af913704b2f851136253d8` | external | prior local verification helper | not executed or copied |
| `C:\tmp\production_stability_write_reports_20260714.py` | 31803 | 2026-07-14T06:54:50.422850+00:00 | `1fe1d099279ef9ee83d52a839eaddd5182452084e745ff2e90f251af06da2e02` | external | prior report writer | not executed or copied |

Five unreachable Git blobs matched broad search terms. Structural inspection
showed two historical methods logs, one curated-example metadata JSON, one
curated-example report, and one example-run metadata JSON. None was a Fable 5
stability cache or fixed-201 sample artefact.

## Provenance and pre-registration existence

- Run 1 metadata records creation at
  `2026-07-02T09:08:51.492750+00:00`, run key `fable_5_run1`, model
  `claude-fable-5`, prompt `dict-1.0-rc2`, 201 projects, and the recovered
  sample path.
- Run 2 metadata records creation at
  `2026-07-02T09:25:10.454036+00:00`, run key `fable_5_run2`, the same
  model/prompt/sample, and 201 projects.
- Each run metadata file contains 21 unique provider response IDs, and the two
  ID sets are disjoint. The IDs themselves are not reproduced in this public
  log.
- Commit `fdc13fdcafcacafbb86d7818fe1485be0b1ed912`, dated
  2026-07-02T12:29:29+01:00, first tracked the production output and metadata.
  That tracked metadata names the exact Run 1 cache path, records 201 seed
  entries and 1108 fresh classifications, and records the self-agreement
  basis.
- The source caches were ignored and therefore have no direct Git blob
  timestamp. Their filesystem timestamps and the tracked production reference
  are distinct forms of evidence; neither is misreported as the other.

## Security and content check

The two caches, both run metadata files, and both 201-row run CSVs were scanned
for the requested secret indicators. No occurrence was found for
`sk-`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `api_key`,
`Authorization:`, `Bearer`, `access_token`, `refresh_token`,
`client_secret`, or `private_key`.

Cache entries contain a public Record ID key, the three classification facets,
a model rationale, and a prompt fingerprint. Cache top-level metadata contains
only schema version, prompt version, and model. Run metadata adds non-secret
timestamps, usage counts, response identifiers, configuration notes, and local
paths. No restricted material or non-public personal information was found.

## Record-ID reconciliation

The Run 1 sample does not contain project `2023/211`. The current production
migration independently records that project's reviewed duplicate/update
collapse to one retained unsuffixed ID.

The recovered Run 1 and Run 2 keys were already clean. A pre-registration
audit found that an upstream cleaning-order defect had copied 16 unstripped
raw Project IDs into the later canonical `Record ID` column before `Project ID`
itself was stripped. This affected `2020/062`, `2021/140`, and `2022/159`
within the 201-record evidence sample, plus 13 records outside that sample.

The central `assign_record_ids()` function now strips existing Record IDs
before missing, uniqueness, and duplicate checks and rejects boundary
whitespace, CR, LF, tab, NBSP, and prohibited ASCII controls. The raw June
register remains byte-identical at
`fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892`.
Current deterministic, Fable, GPT-5.5, migration-audit, and cross-model outputs
were rekeyed or regenerated offline. Classification arrays, rationales,
fingerprints, and all other non-ID fields were verified unchanged.

All 201 Run 1 IDs now match corrected production IDs directly. No Fable
stability mapping is required. The complete 16-row escaped mapping and
per-file old/new hashes are recorded in
`preregistration/package/01_source_and_cleaning/record_id_whitespace_normalisation_audit.csv`
and `record_id_whitespace_migration_log.json`.

## Remaining caveats

- The caches themselves were ignored and untracked before recovery, so the
  direct byte provenance is filesystem-based. The tracked 2 July production
  metadata is the Git provenance anchor linking Run 1 to production.
- No second external byte copy of either cache was located. Because the
  originals were already canonical and hash-stable, no preservation copy was
  needed.
- Previously recorded production hashes identify the pre-correction dirty-ID
  files. Corrected current outputs necessarily have new hashes; the migration
  log proves their non-ID semantic digests are unchanged.
- The evidence describes one independent run pair on one fixed sample. It is
  pre-existing descriptive stability evidence, not a prospective validation
  result.

No LLM/API call occurred during recovery or verification. No classification
was regenerated, no official validation sample was drawn, and nothing was
uploaded.
