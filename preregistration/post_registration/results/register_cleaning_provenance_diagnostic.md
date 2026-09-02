# Frozen-register cleaning provenance diagnostic

Date of diagnostic: 2026-09-01  
Repository HEAD inspected: `7f500898db5e48b36cc76784e3774de28959f6d1`  
Scope: provenance and representation diagnostics only; no data-quality rates or new reconciliation rules.

## 1. Executive diagnostic result

The premise of post-freeze *code* drift is not supported. The current June-register cleaning route returns the same 1,308 Record IDs in the same order and differs from the frozen cleaned CSV in exactly 103 cells, all in `Datasets Used`. Every one of those 103 pairs is identical after whitespace collapse. No other cleaned column differs.

The cause is the byte representation supplied to an unchanged, line-ending-sensitive function:

1. The preregistered Windows file used CRLF bytes, SHA-256 `fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892`.
2. Git stores the same logical CSV with LF bytes, SHA-256 `abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d`.
3. `dashboard/dataset_normalisation.py::_clean_datasets_text()` changes `\r` to `\n` and then collapses runs of two or more whitespace characters before normalising remaining newline boundaries. An embedded CRLF therefore becomes `\n\n` and is usually collapsed to a space; an embedded LF remains a single newline.
4. The historical implementation at the commit that created the frozen CSV reproduces that CSV cell-for-cell and byte-for-byte when run on the reconstructed CRLF representation. The same historical implementation produces the 103-cell difference when run on the Git/LF representation.

This is classifier-input/source-text cleaning, not eligibility cleaning and not alias canonicalisation. The later dashboard parser/canonicaliser is a separate stage. The classifier prompt builder collapses whitespace again, so the two `Datasets Used` cell representations produce identical Fable/GPT prompt dataset text and identical classifier fingerprints for the frozen 1,308 records.

There are two archival limitations. First, two code hashes recorded in the Phase 3 production manifest do not identify a recoverable committed Git object. Second, the original GPT-5.5 1,309-row runtime cache and run metadata are absent. Consequently, the retained evidence-field provenance is established, but exact runtime-code identity for the original model calls is not fully recoverable. This is the report's required STOP for those narrower claims.

## 2. Immutable artefacts and hashes

| Artefact | Observed identity | Result |
|---|---|---|
| Frozen June raw CSV, Git/LF | `data/dea_accredited_projects_20260601.csv`; SHA-256 `abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d` | Present; 1,450 rows and seven columns |
| Reconstructed Windows/CRLF bytes | Constructed in memory from LF-normalised Git content; SHA-256 `fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892` | Matches preregistered Windows-byte hash; not written to the project |
| Frozen cleaned population | `preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv`; SHA-256 `a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1` | Present; 1,308 rows; 1,308 unique nonblank Record IDs; 1,304 Project IDs |
| Reviewed duplicate rulings | `analysis/register_duplicate_rulings.yaml`; SHA-256 `b074283b8995ccbeb09a2c15a48d2867994fe8c3d7146ccf07fba59fa3064f73` | Matches freeze and HEAD |

`preregistration/package/01_source_and_cleaning/source_register_provenance.json` records both raw hashes and states that the protected Windows working tree used CRLF. `register_cleaning_integrity_report.json` records 1,450 raw rows, 1,344 after the DEA filter, 23 tier-1 duplicate rows removed, 12 tier-2 rows removed, one reviewed duplicate/update row removed, and 1,308 final rows.

CSV logical content is representation-equivalent under universal-newline decoding: column names, 1,450 rows, and all logical field values compare equal. The important parser nuance is that pandas' byte/path CSV reader preserves embedded record line endings inside quoted fields. Comparing its LF and CRLF parses therefore shows 1,500 representation differences: `Project ID` 14, `Title` 44, `Researchers` 1,123, `Legal Basis` 4, and `Datasets Used` 315. Most field cleaners collapse those differences. The dataset cleaner deliberately preserves some newline structure, leaving the 103 final differences.

The preregistered source hash therefore refers to the Windows/CRLF byte representation; the repository stores the same frozen source content in canonical Git/LF representation. This diagnostic used the Git representation only after byte-level verification that CRLF conversion reproduces the preregistered hash.

## 3. Historical cleaning reproduction

### Producer and execution route

The frozen cleaned CSV first appears in commit `696c6643e1344dfa0683339499f8726a1d4334c2`, dated 2026-07-14, subject `Normalize Record IDs and verify pre-registration model evidence`.

Evidence:

- `analysis/migrate_record_id_whitespace.py` at that commit imports `analysis.register_cleaning.load_clean_register()`, runs it in a temporary output directory, and serialises the returned dataframe as UTF-8 with BOM and LF record terminators.
- `preregistration/package/01_source_and_cleaning/record_id_whitespace_migration_log.json` records execution at `2026-07-14T21:38:07.341059+00:00` in the Windows repository root, the CRLF source hash, 16 Record-ID whitespace corrections, zero classification calls, unchanged classification content, and no raw-source modification.
- `preregistration/package/01_source_and_cleaning/register_cleaning_integrity_report.json` records the cleaning counts and exact final population.
- `preregistration/package/01_source_and_cleaning/source_register_provenance.json` binds the raw source, cleaner, duplicate rulings, and cleaned output.

Relevant committed identities at `696c664`:

| Component | Git/LF SHA-256 |
|---|---|
| `analysis/register_cleaning.py` | `4670131c3c57cec8d101db14790915a3c5e6fc2a4a68dd973acf4408fca2725c` |
| `dashboard/dataset_normalisation.py` | `6e8e13a73e6f6cbe0ebb6256c4e32d5601bc6c198906952526f60f3fd793eff1` |
| `analysis/register_duplicate_rulings.yaml` | `b074283b8995ccbeb09a2c15a48d2867994fe8c3d7146ccf07fba59fa3064f73` |

All three identities are unchanged at the Phase 3 audit commit `e9d53023417348ad2784e629c855bf8d04f38df8` and at current HEAD.

### Isolated reproduction

A complete `git archive` snapshot of `696c664` was extracted under `/tmp`. Historical code imported only modules from that snapshot. No old module was run against current repository modules. The only external comparison artefact was the read-only frozen CSV. The temporary snapshot was removed after execution.

| Check | Historical code + reconstructed CRLF | Historical code + Git/LF |
|---|---:|---:|
| Rows | 1,308 | 1,308 |
| Unique Record IDs | 1,308 | 1,308 |
| Columns and order | Exact | Exact |
| Record-ID set and order | Exact | Exact |
| Differing cells | 0 | 103, all `Datasets Used` |
| Reproduced serialised SHA-256 | `a334bd7f...` (exact frozen file) | `e080e96f28c22f3d0667f5d07bfb31115365043c14868cec95891d24d3938602` |

Thus historical implementation `696c664` reproduces the frozen 1,308 cleaned population cell-for-cell and byte-for-byte from the Windows/CRLF representation.

## 4. Current versus frozen comparison

The current production route, `load_raw_register(...candidate_files=["dea_accredited_projects_20260601.csv"])` followed by `clean_register_dataframe()`, was run with all diagnostic outputs directed to a temporary directory.

| Field | Differing cells | Affected Record IDs |
|---|---:|---:|
| Project ID | 0 | 0 |
| Title | 0 | 0 |
| Researchers | 0 | 0 |
| Legal Basis | 0 | 0 |
| Datasets Used | 103 | 103 |
| Secure Research Service | 0 | 0 |
| Accreditation Date | 0 | 0 |
| Record ID | 0 | 0 |
| Year | 0 | 0 |
| Quarter | 0 | 0 |
| Quarter Label | 0 | 0 |

The route returns 1,308 rows, 1,308 unique Record IDs, and the exact frozen Record-ID set and order. The current live dashboard pointer resolves a later observed revision of the nominal June register at `data/register_snapshots/33c8ba2abd2085a28b2e5ca5ba2913398c6edb96f59f31331e5c125c96661014/canonical.csv`, canonical CSV SHA-256 `918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd`. That current pointer also returns the same 1,308 IDs, zero title differences, and the same 103 dataset-cell differences relative to the frozen CSV.

## 5. Origin and mechanism of the 103 differences

### Actual transformation path

`analysis/register_cleaning.clean_register_dataframe()` performs:

`raw register` → column normalisation → DEA eligibility filter → duplicate policy → reviewed duplicate rulings → Record-ID assignment → title/researcher/dataset/source-text cleaning → time fields.

For `Datasets Used`, the general cleaned register receives only `_clean_datasets_text()`. General rows are not passed through `iter_dataset_entries()` or `normalise_dataset_name()` at this stage. Those parser/canonicaliser functions are used within duplicate-merge handling where required, and separately downstream by the dashboard.

The dashboard path in `dashboard/data/registry.py` is:

`clean_register_dataframe()` → retained `df_all["Datasets Used"]` → `parse_datasets(df_all)` → `iter_dataset_entries()` → `normalise_dataset_name()` / provider normalisation → separate exploded `df_datasets`.

Dataset-family/collection grouping is another derived stage in `dashboard/data/loader.py`; it does not rewrite the retained study field.

### Mechanical cause

The causal lines in `_clean_datasets_text()` are, in order:

1. `text = text.replace("\r", "\n")`
2. `text = re.sub(r"\s{2,}", " ", text)`
3. `text = re.sub(r"\s*\n\s*", "\n", text)`

For an embedded CRLF, step 1 creates two consecutive newline characters; step 2 collapses them to a space. For an embedded LF, step 1 does nothing and the single newline survives step 2. This function ordering was introduced before the study freeze and remains unchanged.

| Mechanism | Affected records | Affected cells |
|---|---:|---:|
| Line-ending-sensitive whitespace/source-text cleaning in `_clean_datasets_text()` | 103 | 103 |

All 103 pairs are whitespace-equivalent. In 76, replacing current LF newlines with spaces produces the frozen field exactly. Across the 103 cells, the Git/LF output contains 297 newline characters and the frozen output 65.

This is not alias canonicalisation, spelling correction, provider canonicalisation, or dataset-family mapping. No raw examples are needed to establish the mechanism, so none are quoted and no reserve-disclosure operation was required.

### Downstream consequence without conflating stages

Applying the existing downstream parser to the two already-cleaned representations yields the same parsed raw and canonical entry lists for 97 of the 103 records. Six records differ in parser segmentation; the affected subset yields 468 entries from the Git/LF representation and 470 from the frozen representation. This is a consequence in the separate dashboard representation, not the source of the 103 cleaned-field cells.

## 6. Relevant code-history timeline

| Date | Commit | Relevant change | Relative to freeze |
|---|---|---|---|
| 2026-04-02 | `d5c3697add2d01b6b5d57272e3059bd2ef92d1a0` — `Overhaul dashboard UX and dataset name normalisation` | Introduced the line-ending-sensitive `_clean_datasets_text()` ordering | Before source snapshot and freeze |
| 2026-05-25 | `e9553efdea2886fcb269696271a5b7a7cdab642a` — `Clean register title and dataset text via shared pipeline functions` | Wired shared title/dataset text cleaning into `analysis/register_cleaning.py`; removed separate classifier-side dataset cleanup | Before source snapshot and freeze |
| 2026-06-09 | `9572fb222143a5073f91bec212793200046b669c` — dashboard update | Added deterministic `_x000D_` cleanup | Before freeze |
| 2026-07-02 | `fdc13fdcafcacafbb86d7818fe1485be0b1ed912` — `add fable 5 run outputs` | First committed Fable production outputs; original run metadata reports 1,308 after later metadata migration, but the committed original cleaner reproduces 1,309 pre-ruling rows | Before 1,308 freeze |
| 2026-07-13 | `3174b71dc2d00149446051445fde543ec5ff59e2` — `fix duplicate project handling and stabilise record ids` | Added reviewed duplicate rulings; collapsed the 1,309 pre-ruling state to 1,308 and migrated model caches by exact prompt fingerprint without model calls | Before freeze |
| 2026-07-14 | `696c6643e1344dfa0683339499f8726a1d4334c2` — `Normalize Record IDs and verify pre-registration model evidence` | Normalised 16 Record IDs and first wrote the frozen 1,308 cleaned CSV | Freeze producer |
| 2026-07-15 | `e9d53023417348ad2784e629c855bf8d04f38df8` — Phase 3 provenance refresh | Audited/froze the coherent 1,308 release | Freeze audit |

No commit after `696c664` changes `analysis/register_cleaning.py`, `dashboard/dataset_normalisation.py`, or `analysis/register_duplicate_rulings.yaml`. The smallest causal code set is therefore the pre-freeze `_clean_datasets_text()` ordering plus the checkout's LF/CRLF representation—not a post-freeze commit.

## 7. Fable 5 input provenance

`analysis/outputs_classified_20260702_fable5/run_metadata.json` records a 2026-07-02 production run over the June CSV via the register manifest, model `claude-fable-5`, prompt/taxonomy `dict-1.0-rc2`, and model-visible evidence fields `Title` and `Datasets Used`.

The original API execution preceded the reviewed-duplicate decision. A complete snapshot of the parent of the output-adding commit (`93803df45e81345ba3207c435cf9f92f915bbc1b`) run with CRLF source bytes returns 1,309 rows. Its IDs and titles match the first-committed 1,309 Fable output; one dataset source cell is whitespace-different but yields the same prompt text. On 2026-07-13, `analysis/migrate_reviewed_duplicate_record_ids.py` built the formal 1,308 release by matching every retained row to the old cache using exact Project ID plus classifier fingerprint. One reviewed duplicate/update row was removed and retained duplicate IDs were rekeyed. The migration made no LLM calls.

The classifier constructs the model-visible values as:

- title: `_sanitise_prompt_text(Title)`, which collapses whitespace;
- dataset: `_summarise_datasets(Datasets Used)`, which collapses whitespace, truncates after 600 characters if needed, and sanitises prompt delimiters;
- fingerprint: SHA-256-derived identifier of the exact prompt title plus prompt dataset.

The current Git/LF cleaned values and frozen CSV produce zero prompt-title differences, zero prompt-dataset differences, and zero fingerprint differences over all 1,308 records. The stored formal Fable release contains the exact frozen `Title` and `Datasets Used` fields for all 1,308 rows. Therefore, for the retained formal population, the 103 cell-level newline differences do not alter the title/dataset evidence supplied to Fable.

Archival limitation: the Phase 3 manifest records classifier SHA-256 `51adce65...` and cleaning SHA-256 `1d803490...`; neither hash matches any committed LF, CRLF, or BOM variant found in repository history. The adjacent pre-run commit has classifier SHA-256 `aa1a3817...` and cleaner SHA-256 `b632d88a...`. Exact retained prompt fingerprints are documented, but an exact committed runtime-code object for the original API call is not recoverable.

## 8. GPT-5.5 input provenance

The canonical artefact is `analysis/releases/gpt55_crossmodel_20260707/gpt55_classifications.csv`, SHA-256 `5bb4379174e1c9b9cf7faf611712c53648bc57eea7ba1d28127ecedab16b5ded`. Its receipt records 1,308 rows, prompt/taxonomy `dict-1.0-rc2`, and exact population alignment. Its stored `Title` and `Datasets Used` fields match the frozen cleaned CSV in all 1,308 rows.

The first tracked GPT runner, `analysis/outputs/gpt55_crossmodel_stratum_run.py` at commit `063e53726234060ecb17f75083e57ba876cbf221`, calls `analysis.llm_theme_analysis_v3.load_data()` and reuses the Fable `_sanitise_prompt_text()`, `_summarise_datasets()`, fingerprint, static prompt, and project-block builders. Repository migration evidence records that the pre-ruling GPT state was also migrated to the 1,308 population by exact prompt fingerprint without a model call.

However, the runner was first committed after the named 2026-07-07 run, and the original `analysis/outputs/gpt55_run_metadata.json`, cache, and source output are absent from this checkout. The release receipt explicitly says the historical 1,309-row intermediate was not retained or reconstructed. Accordingly:

- the formal 1,308 GPT release's title and dataset source fields are proven cell-identical to the frozen CSV;
- the tracked runner would give the same prompt title/dataset as Fable and is insensitive to the 103 whitespace-only differences;
- exact runtime-code and byte-exact original API-input provenance cannot be independently established from surviving repository objects. No inference from today's runner is treated as proof.

This is a diagnostic STOP for the stronger claim that the exact original GPT request can be reconstructed.

## 9. Scratch-coder input provenance

`scripts/generate_formal_validation_assignments.py` directly reads the frozen cleaned CSV and copies `Title` to `project_title` and `Datasets Used` to `datasets_used`. The public generation record identifies commit `6500c92148d97043a7826b684f5885127fd22814`, generation time `2026-07-24T15:32:29Z`, and 675 assignments covering 225 records three times. The restricted import's recorded SHA-256 is `ed5a1c66e4dfa1037dfae2eb166a20fcca12ae18e77ca2b298bd5152252f5ae5`.

Only public evidence and administrative inclusion fields were selected from the frozen REDCap export; no coder response field was read.

| Check | Result |
|---|---:|
| Formal assignment rows checked | 675 |
| Unique formal records checked | 225 |
| Title mismatches versus frozen CSV | 0 rows |
| Dataset mismatches versus frozen CSV | 108 assignment rows / 36 unique records |
| Dataset mismatches after whitespace collapse | 0 |

The generator/import source was the frozen CSV, so later general cleaning did not enter this stream. The export differences are a REDCap import/storage/export whitespace round trip: all 108 are whitespace-equivalent, and the same public field is displayed through `[datasets_used]`. They are not the current cleaner's 103-cell output; only five of the 36 affected scratch records are among those 103 Record IDs.

Pilot/training and declaration rows were excluded by the formal batch/record flags and were not compared.

## 10. Project-owner input provenance

The tracked production import is `preregistration/post_registration/owner_record_import/project_owner_production_import_20260824.csv`, added in commit `ac183152ba192b2bc74e0e41e16ce4d699cc321c` on 2026-08-24, SHA-256 `ab1b91daaed282d8451e25383c7e1dceec97969c5ebee9f417041b5b322337d9`. Its 215 `project_review` rows cover 201 unique frozen Record IDs and declare source population `20260601-cleaned-1308`.

| Check | Result |
|---|---:|
| Project-review rows checked | 215 |
| Unique records checked | 201 |
| Title mismatches versus frozen CSV | 0 |
| Dataset mismatches versus frozen CSV | 0 |

The candidate-0.4 dictionary uses read-only `project_title` and `datasets_used` fields. The tracked 8B assignment frame was produced by `analysis/validation/build_owner_sequence_8b.py` and commit `5739fa2a7b1aedaac60fb0814141d61b5093e29e`; the owner-frame code binds the frozen population. No tracked script that materialises the real 2026-08-24 production import from the assignment frame, frozen population, and Fable release was found. `scripts/build_project_owner_redcap_candidate_0_4.py` builds the instrument and synthetic fixtures, not this real import. The exact input artefact proves the public evidence values, but its final materialisation command is unresolved.

No owner response file or field was read. This section establishes what the production import/instrument supplied, not whether a particular participant opened it.

## 11. Provenance matrix

| Consumer / artefact | Raw source snapshot | Cleaning implementation | Title representation | Dataset representation | Matches frozen 1308? | Evidence |
|---|---|---|---|---|---|---|
| Frozen cleaned population | Original June CRLF, `fc911d...` | `696c664`; cleaner `467013...`; rulings `b07428...` | `_clean_title_text()` field | `_clean_datasets_text()` on CRLF field | Reference | Exact historical reproduction; migration and integrity logs |
| Fable 5 production | Original June CRLF; original API state 1,309 then ruled/migrated to 1,308 | Adjacent original state `93803df`; formal migration `3174b71`; exact runtime hash unresolved | Whitespace-sanitised title in prompt | Whitespace-flattened/truncated/sanitised dataset in prompt | Yes for all retained prompt evidence and stored fields | Run metadata; first output commit; exact-fingerprint migration; 1,308 stored-field comparison |
| GPT-5.5 comparison | June source through fresh runtime cleaner; original 1,309 intermediate not retained | First tracked runner `063e537`; exact runtime commit/cache unresolved | Same tracked prompt transformation as Fable | Same tracked prompt transformation as Fable | Stored 1,308 fields: yes; exact original API request: unresolved | Release receipt; release CSV; runner; migration report |
| Scratch-coder formal records | Not re-cleaned; frozen cleaned CSV is direct source | `generate_formal_validation_assignments.py` at draw commit `6500c921` | Exact frozen field in generator/import and export | Exact frozen field in generator/import; frozen export has whitespace-only round-trip differences for 36 records | Generator/import yes; export cell identity no for 36 records | Generator, public generation/import logs, selected public/admin export columns |
| Project-owner production import | Not re-cleaned; declares frozen cleaned population | Final real-import generator unresolved; 8B frame and frozen-bound validation code tracked | Exact frozen field | Exact frozen field | Yes for all 215 review rows | Production import at `ac183152`; direct field comparison |
| Current dashboard | Current manifest pointer to later-observed nominal-June LF CSV `918117...` | Current cleaner `467013...`, then separate parser/canonicaliser `6e8e13...` | Same as frozen | Retained field differs in 103 whitespace-only cells; derived parser output additionally differs for six | IDs/title yes; dataset cells no | v2 manifest, `dashboard/data/loader.py`, `dashboard/data/registry.py`, aggregate rerun |

## 12. Answers to architectural questions A–F

### A. Was there cleaning between the raw UKSA June register and the frozen 1,308 study file?

Yes. The pipeline normalised columns, applied the DEA legal-basis/eligibility filter, resolved exact and mergeable duplicates, applied reviewed duplicate rulings, assigned/stabilised Record IDs, cleaned title/researcher/dataset and selected free-text fields, and derived time fields. `Datasets Used` received source/text cleaning through `_clean_datasets_text()`; the general field was not globally alias-canonicalised.

### B. Is there additional dataset normalisation downstream of that frozen representation?

Yes. Dashboard code separately parses provider/dataset occurrences, canonicalises dataset and provider names, filters fragments, and derives collection/family membership. It creates exploded derived representations rather than intentionally rewriting the frozen study field.

### C. Have any downstream transformations migrated into the current general cleaning path since freeze?

No. The general cleaner used `_clean_datasets_text()` before freeze and still does. General alias parsing/canonicalisation has not migrated into `clean_register_dataframe()`. The parser is used in duplicate-merge helpers and downstream dashboard derivations, as it was at freeze.

### D. Do the 103 changed cells represent post-freeze evolution of code rather than a changed June source?

No. They are reproduced by the historical freeze implementation when its input bytes are LF and disappear when the same logical source is supplied as CRLF. No relevant post-freeze code commit exists. The current live pointer is a later observed byte snapshot, but running it yields the same 103 result; that does not explain the historical frozen/current difference.

### E. Did post-freeze cleaning evolution affect any formal validation input?

- **Fable 5:** No. There is no relevant post-freeze cleaner evolution. The formal 1,308 cache was migrated before freeze by exact prompt fingerprint; the 103 whitespace-only cell differences produce identical prompt evidence.
- **GPT-5.5:** No evidence that it did. The canonical source fields equal the frozen CSV and the tracked prompt route is whitespace-insensitive, but exact original runtime-code provenance is unresolved because the original cache/metadata are absent.
- **Scratch coders:** No. Their generator directly used the frozen CSV. The frozen export has a separate whitespace-only REDCap round-trip difference for 36 records.
- **Project owners:** No. The production import's 215 review rows are cell-identical to the frozen title/dataset fields. The final real-import generator is not archived.

### F. What representation should a future data-quality audit use for each possible question?

These are empirically different quantities:

1. **Transformations actually applied to study input:** compare raw June CRLF values with the historical study-input cleaning stages, while keeping source/text cleaning distinct from prompt whitespace sanitisation and from the reviewed 1,309-to-1,308 migration.
2. **Variation detectable by the later/current reconciliation system:** apply the current parser/canonicaliser as a separate derived analysis to the frozen raw population. This measures later reconciliation capability, not necessarily what the classifiers or validators saw.
3. **Variation in the register as currently published/served:** use the manifest's current content snapshot and current pipeline. This is a different source identity from the frozen validation snapshot even though both carry the nominal June date.

The 103-cell result itself demonstrates the distinction: unflattened cleaned field cells differ, classifier prompt evidence does not, and six downstream parsed representations do.

## 13. Unresolved questions and STOPs

1. The manifest's `cleaning_code_sha256: 1d803490...` and `classification_code_sha256: 51adce65...` do not match any committed LF, CRLF, BOM+LF, or BOM+CRLF version found in Git history. The exact historical frozen CSV is nevertheless reproduced by committed code at `696c664`.
2. The original GPT-5.5 1,309-row cache, run metadata, and source output are absent. The canonical 1,308 release is preserved, but byte-exact original API-input and runtime-code provenance cannot be reconstructed. This activates the requested STOP for that stronger claim.
3. No tracked generator for the real project-owner production import was found. The import file itself proves its title/dataset values, but the final join/materialisation command is unarchived.
4. A broad repository provenance search incidentally emitted historical model-output columns before searches were narrowed. No classification value was extracted, compared, summarised, or used in this diagnostic. No coder or owner response value was read.

No approximation or new matching rule was used to fill these gaps.

## 14. Verification

- Both raw-source byte identities and the frozen cleaned hash were reverified.
- The frozen CSV has exactly 1,308 unique nonblank Record IDs.
- Historical reproduction used a complete same-commit `/tmp` snapshot and did not mix historical project modules with current project modules.
- Reconstructed CRLF and all reproduced outputs existed only in temporary storage; temporary directories were removed.
- Current reruns wrote only cleaning audit intermediates under temporary directories.
- Every current/frozen comparison was keyed to the frozen population; no excluded population analysis was performed.
- No data-quality rates, aliases, matching rules, normalisation logic, or classifier calls were created.
- No coder responses, owner responses, adjudication outcomes, disagreement labels, or reserve classifications were analysed. Selected REDCap reads were restricted to public evidence and administrative inclusion fields.
- No reserve membership was disclosed.
- No web, API, or LLM call occurred.
- Relevant tests: 33 passed, seven subtests passed; one pandas deprecation warning.
- No production, reference, frozen input, or preregistration-package file was modified.
- No commit or push occurred.
- Before this report was added, `git status --short` was empty.

Final worktree status is reported in the task handoff after the report-only change.
