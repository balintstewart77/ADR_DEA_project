# DEA validation preregistration inventory

## Inventory snapshot

- Inventory date: 2026-07-14
- Repository root: `C:\Users\balin\Desktop\ADR_DEA_project`
- Branch: `main`
- Commit at recovery pre-flight: `e1ee9e3f55a9733468395bc90c548e12bde7707f`
- Python: 3.13.2 (`C:\Users\balin\Desktop\ADR_DEA_project\venv\Scripts\python.exe`)
- Pre-flight Git status: clean
- Repository-level instruction files: none found

The initial scientific-artefact inventory and forensic search were read-only.
After the Fable evidence gates passed, an authorised pre-registration
Record-ID cleaning correction was applied. It changed only the central cleaning
invariant and current derived Record-ID keys, then regenerated deterministic
evidence artefacts. The raw source and recovered run caches were not edited, no
model was called, and no official validation sampling operation was run.

## Files searched

The complete repository working tree was searched, excluding `.git/`, `.venv/`,
`.venv-test/`, `venv/`, and generated `__pycache__/` directories. The search
covered 317 regular working-tree files, 231 tracked files, and 270 unique paths
seen in Git history. Filename and content searches covered protocol,
preregistration, register, cleaning, duplicate, Record ID, taxonomy, prompt,
model, Fable, GPT, comparison, repeatability, consistency, exclusion, training,
pilot, REDCap, sampling, analysis, adjudication, evidence pack, sign-off,
release, decision, deviation, clarification, log, checklist, instrument,
dictionary, codebook, template, and lockfile terms. No DOCX or PDF file exists
in the current worktree.

High-signal locations inspected directly included:

- `data/` source snapshots, `register_manifest.json`, and release pointers;
- `analysis/register_cleaning.py`, duplicate rulings, Record-ID migrations, and
  their tests;
- `taxonomy_data_dictionary*.yaml` and `analysis/llm_theme_analysis_v3.py`;
- all `analysis/outputs_classified_*`, `outputs_v*`,
  `outputs_comparison_*`, `outputs_deterministic_rc2`, `outputs_refresh`, and
  tracked/ignored `analysis/outputs/` files;
- model comparison, experiment-sample, and consistency scripts and outputs;
- repository requirements files, dashboard adjudication tests, methods notes,
  QA reports, and all relevant paths in Git history.

The manifest is refreshed after the clean-ID migration. Existing non-sensitive
rows have exact SHA-256 hashes, UTC modification times, and the verification-time
repository HEAD; missing, prospective, or restricted rows remain skipped by
design.

## Proposed authoritative or current candidates

These assessments use explicit design facts and repository pointers, not
version-number or timestamp inference.

| Area | Candidate | Assessment and evidence |
| --- | --- | --- |
| Protocol | `Validation_Protocol_PreReg_v4.docx` | Named current review candidate, but missing. It is not frozen. |
| Source | `data/dea_accredited_projects_20260601.xlsx` and matching CSV | `data/register_manifest.json` explicitly points to version `20260601` as current. |
| Cleaning | `analysis/register_cleaning.py` | Current implementation produces 1,308 retained rows after reviewed rulings; candidate for final freeze pending cross-document audit. |
| Duplicate rulings | `analysis/register_duplicate_rulings.yaml` | Governing reviewed rulings for the current release. |
| Record ID | `assign_record_ids` and reviewed-ruling logic in `analysis/register_cleaning.py` | Current stable synthetic identifier implementation, supported by `analysis/test_record_id_stability.py`. |
| Cleaned population | `preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv` | Frozen deterministic export with 1,308 clean unique Record IDs and 1,304 Project IDs; integrity and whitespace-normalisation audits accompany it. |
| Taxonomy | `taxonomy_data_dictionary.yaml` | File metadata and design facts agree on dictionary `1.0-rc2` / ontology `v3.4-rc2`. |
| Prompt implementation | `analysis/llm_theme_analysis_v3.py` | Declares Fable 5 and `dict-1.0-rc2`; the exact prompt is assembled dynamically. No standalone rendered prompt exists. |
| Production configuration | `analysis/outputs_classified_20260702_fable5/run_metadata.json` | Records Fable 5, prompt/taxonomy `dict-1.0-rc2`, 1,308 records, and a 201-entry seed-cache reference. |
| Production classifications | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | `data/release_pointers.json` targets this run; direct audit confirms 1,308 Record IDs, 1,304 Project IDs, and four doubled Project IDs. |
| Fable 5 stability evidence | `analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json` and `analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json` | Recovered and verified as the two independent Fable 5 / `dict-1.0-rc2` runs on the same exact 201-record sample. Deterministic recomputation reproduces every reported target. |
| GPT-5.5 comparison evidence | `analysis/outputs/gpt55_classifications.csv` and current cross-model outputs | Deterministically regenerated offline after key migration; all reported aggregate agreement and disagreement counts are unchanged. |

"Current candidate" does not mean "frozen". The protocol, cleaning bundle,
prompt rendering, and final package still require a cross-document audit.

## Duplicate and superseded versions

- `data/dea_accredited_projects_20260325.*` and the legacy
  `data/dea_accredited_projects.csv` are prior snapshots. The register manifest,
  not filename recency, establishes `20260601` as current.
- `taxonomy_data_dictionary.triage_backup.yaml` was previously inventoried as
  an ignored 1.0/v3.4 backup but is not present in this checkout. Its manifest
  row now accurately records it as missing and superseded by the rc2 taxonomy.
- `analysis/outputs_classified_20260601/layer_classifications.csv` contains
  1,309 records and five doubled official Project IDs. It is superseded by the
  reviewed 1,308-row Fable output.
- `analysis/outputs_v4_8_rc1/layer_classifications.csv`, its full-register
  replicate, and the rc2 Opus output each contain 1,272 rows from an earlier
  register. They are historical model evidence, not current production output.
- The three tracked legacy consistency trials contain 75 records each and are
  reported by the old three-trial workflow. They are not the required two
  Fable 5 runs on the fixed 201-record sample.
- `analysis/outputs_v3/model_selection_v3.2/experiment_sample_150.csv` and
  `analysis/build_experiment_sample.py` belong to an older 150-record
  Opus/Sonnet comparison. They are not official validation sampling artefacts.
- `analysis/build_model_comparison.py` compares older Opus/Sonnet outputs and
  cannot be silently relabelled as the Fable 5/GPT-5.5 comparison script.
- The design states that `training_pilot_exclusion_list_v7` is superseded by
  v8. No v7 file was found in the worktree or any Git-history path, so its
  physical identity and location remain unverified.

## Missing expected artefacts

### Protocol and source freeze

- `Validation_Protocol_PreReg_v4.docx` and final protocol PDF;

### Taxonomy, prompt, and pre-existing model evidence

- exact rendered `dict-1.0-rc2` production prompt;

### Exclusions, instruments, and prospective tooling

- official sampling script, sampling tests, and execution checklist;
- coder handout, trainer guide, and separated pilot exclusion/assignment files;
- both REDCap dictionaries, codebook, and import template;
- validation analysis script and exact dependency lockfile;
- adjudication instrument, audit-selection script, evidence-pack template, and
  senior sign-off template;
- protocol-deviation, instrument-change, coding-clarification, and Jo-review
  decision log templates.

The official active sample manifest, reserve manifest, formal REDCap export,
final results, and adjudication outputs are intentionally not yet generated.
Their manifest rows are post-registration placeholders, not missing work to be
produced in this phase.

## Recovered and verified Fable 5 stability evidence

The pre-existing Fable stability package was recovered and independently
verified on this Windows checkout at
`C:\Users\balin\Desktop\ADR_DEA_project`, branch `main`, starting HEAD
`e1ee9e3f55a9733468395bc90c548e12bde7707f`. No LLM or API call was made.

Authoritative source files:

- Run 1 cache:
  `analysis/outputs/model_comparison_fable_5_run1/llm_layer_cache.json`,
  SHA-256
  `e888422a3e46f8c3746c8560327e01fdb0e307491363e65a49c86ea78cb79156`;
- Run 2 cache:
  `analysis/outputs/model_comparison_fable_5_run2/llm_layer_cache.json`,
  SHA-256
  `77cd247f06b0d966334726e17de858d4b16c4f5bbe67e246b653e007fd676fff`;
- Run 1 metadata:
  `analysis/outputs/model_comparison_fable_5_run1/run_metadata.json`,
  SHA-256
  `90553e77b8a262bb7ff73668dc3336ab721bbd39650780ed86ac4660d36ace50`;
- Run 2 metadata:
  `analysis/outputs/model_comparison_fable_5_run2/run_metadata.json`,
  SHA-256
  `e3f7cc0e9ffd38b882c80e52d359d19d50cc1236c20c284716f72acfc76c0426`.

Both cache key sets and the recovered
`analysis/outputs/model_comparison_sample.csv` contain the same 201 Record
IDs. Both caches identify model `claude-fable-5`, prompt
`dict-1.0-rc2`, and cache schema 6. Their run metadata records distinct
timestamps and 21 disjoint provider response IDs per run.

Exact reproduced metrics:

| Measure | Result |
| --- | ---: |
| Research Domain exact-set agreement | 191/201 (95.0%) |
| Mean Research Domain Jaccard | 0.974295190713 (0.974 displayed) |
| Analytical Purpose exact-set agreement | 185/201 (92.0%) |
| Mean Analytical Purpose Jaccard | 0.935323383085 (0.935 displayed) |
| COVID-19/pandemic tag agreement | 201/201 (100.0%) |
| Demographic-disparities/equity tag agreement | 197/201 (98.0%) |
| Joint two-tag agreement | 197/201 (98.0%) |
| All-component agreement | 171/201 (85.1%) |
| Invalid or failed classifications | 0 |

Run 1 is the 201-entry seed cache named by the current production metadata.
All 201 Run 1 classifications now match the corrected 1,308-row production
output directly. The recovered Run 1 and Run 2 keys were already clean. The
previous three apparent mappings (`2020/062`, `2021/140`, and `2022/159`) were
caused solely by boundary whitespace in later canonical IDs. The central
cleaning correction strips boundary whitespace before Record-ID validation;
the 16-ID migration is documented in
`record_id_whitespace_normalisation_audit.csv` and the migration log. Project
`2023/211` was not in the 201-record comparison sample; its separate reviewed
duplicate/update collapse remains documented in production provenance.

The raw June source remains byte-identical. The current production hashes differ
from earlier reference values because the correction changed only 16 Record-ID
keys; semantic non-ID content digests and all agreement results were verified
unchanged. Current hashes are recorded in the migration log and manifest.

The complete record manifest, diagnostics, metrics, verification report and
forensic recovery log are under
`preregistration/package/03_preexisting_model_evidence/`. The raw caches were
already in their canonical paths, so no copy was made. Direct cache provenance
is limited by their formerly ignored/untracked status; tracked production
metadata committed on 2 July 2026 is the Git provenance anchor.

## Potentially stale artefacts

No protocol or trainer guide was available to scan for the prohibited 1,309 /
1,305 / five-duplicate / 23-exclusion / 387-frame facts. The following existing
files contain superseded population counts and must not be treated as current:

- `analysis/outputs_classified_20260601/layer_classifications.csv`: 1,309 rows
  and five doubled Project IDs;
- `analysis/outputs_refresh/20260601/derive_report.md`: says 1,309 cleaned
  records while its named deterministic output now contains 1,308 rows;
- `analysis/outputs_refresh/20260601/register_diff.md`: reports the earlier
  1,309-row cleaning result;
- `analysis/outputs/hygiene_phase2_report.md` and
  `analysis/outputs/codebase_hygiene_audit.md`: report 1,309 dashboard projects
  and predate the reviewed duplicate ruling;
- `analysis/outputs/domain_order_reconciliation_review.md`: uses 1,309 as its
  denominator and is historical rather than current population evidence.

`METHODS_LOG.md` contains older 1,309-row sections as historical entries, but
its leading 2026-07-13 correction explicitly supersedes them with 1,308 retained
records and 1,304 Project IDs. Preserve that historical context; do not quote
the old sections as the current design.

Two other quality concerns are not count staleness:

- `analysis/outputs_deterministic_rc2/manifest.json` records a dirty generating
  worktree and machine-local Windows paths. Its row count is correct, but its
  portability and provenance need a decision.
- Both current and older Fable `layer_summary.txt` files are empty. The current
  classification CSV and run metadata exist, but an empty narrative should not
  be represented as a substantive verification report.

## Artefacts requiring restricted handling

- reserve Record IDs and reserve manifests;
- trainer-only answer keys and restricted trainer material;
- personal contact lists;
- blinded coder assignments and operational pilot assignments;
- formal REDCap exports and any row-level personal data;
- active sample identities while coding remains blinded.

No path or hash for secret, personal, reserve, trainer-key, or blinded content
has been placed in the public manifest. The local
`preregistration_restricted/` tree is Git-ignored and contains only its warning
README plus empty directories.

## Decisions required from Balint

1. Supply or identify the actual `Validation_Protocol_PreReg_v4.docx`, then
   approve the final PDF only after collaborator review and cross-document audit.
2. Locate the superseded v7 exclusion file and provide or approve the final v8
   22-Record-ID artefact. Decide whether v7 should be retained privately or as
   excluded historical provenance.
3. Decide how to materialise the exact rendered production prompt without
   rerunning a model.
4. Decide whether the dirty-worktree deterministic manifest is acceptable
   supporting provenance or must be replaced by a clean, portable manifest.
5. Decide whether the empty production layer summary should be omitted or
   replaced by a verified report derived without changing scientific outputs.
6. Approve the validation-specific sampling, REDCap, analysis, adjudication,
   log-template, and dependency-lock artefacts before registration and before
   any official sampling.
7. Confirm access and publication treatment for the trainer guide, Jo-review
   decision log, active identities, and any restricted hash commitments.

## Sampling confirmation

No active or reserve validation sample was drawn or generated, and no official
validation sample manifest was created. The recovered 201-record file is a
pre-existing model-comparison evidence manifest, not an active or reserve
validation sample. `SEED_DRAW = 20260713` is documented only as the future
formal seed and was not executed against the real frame. No reserve IDs were
inspected or written, no REDCap export was generated, and formal human coding
has not begun.
