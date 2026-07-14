# DEA validation preregistration inventory

## Inventory snapshot

- Inventory date: 2026-07-14
- Repository root: `/Users/balintstewart/Desktop/ADR_DEA_project`
- Branch: `main`
- Commit at pre-flight: `dfd6b2b080fcf6cd9453793a4ff0c80c42bec7b2`
- Python: 3.12.5
- Pre-flight Git status: clean
- Repository-level instruction files: none found

This was a read-only scientific-artefact inventory. Existing scientific files
were not edited, no model was called, and no official validation sampling
operation was run.

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

The manifest records 71 artefact rows. Thirty-one existing non-sensitive rows
have exact SHA-256 hashes, UTC modification times, and the inventory commit.
Forty missing, prospective, or restricted rows remain unhashed by design.

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
| Cleaned population | No standalone file | The Fable production CSV embeds 1,308 unique Record IDs and 1,304 Project IDs, but a distinct frozen cleaned-register export was not found. |
| Taxonomy | `taxonomy_data_dictionary.yaml` | File metadata and design facts agree on dictionary `1.0-rc2` / ontology `v3.4-rc2`. |
| Prompt implementation | `analysis/llm_theme_analysis_v3.py` | Declares Fable 5 and `dict-1.0-rc2`; the exact prompt is assembled dynamically. No standalone rendered prompt exists. |
| Production configuration | `analysis/outputs_classified_20260702_fable5/run_metadata.json` | Records Fable 5, prompt/taxonomy `dict-1.0-rc2`, 1,308 records, and a 201-entry seed-cache reference. |
| Production classifications | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | `data/release_pointers.json` targets this run; direct audit confirms 1,308 Record IDs, 1,304 Project IDs, and four doubled Project IDs. |

"Current candidate" does not mean "frozen". The protocol, cleaning bundle,
prompt rendering, and final package still require a cross-document audit.

## Duplicate and superseded versions

- `data/dea_accredited_projects_20260325.*` and the legacy
  `data/dea_accredited_projects.csv` are prior snapshots. The register manifest,
  not filename recency, establishes `20260601` as current.
- `taxonomy_data_dictionary.triage_backup.yaml` is an ignored 1.0/v3.4 backup.
  It is superseded by the rc2 taxonomy according to both the design facts and
  current dictionary metadata.
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
- standalone 1,308-row frozen cleaned register;
- `instruction_reviewed_duplicate_record_id_report.md`, which is referenced by
  `METHODS_LOG.md` but absent.

### Taxonomy, prompt, and pre-existing model evidence

- exact rendered `dict-1.0-rc2` production prompt;
- both Fable 5 repeatability runs and the exact shared 201-Record-ID manifest;
- production repeatability report;
- 1,308-record GPT-5.5 classification output;
- Fable 5/GPT-5.5 comparison script and verification report;
- full 380-record post-exclusion hard frame. The design facts specify 182
  domain-only, 143 purpose-only, 55 both-dimension, and 11 records with an
  accompanying tag disagreement, but the proving artefact is absent.

### Exclusions, instruments, and prospective tooling

- final 22-Record-ID v8 exclusion list;
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
2. Recover and identify the two Fable 5 repeatability runs, exact 201-record
   manifest, and report. Confirm sample composition or seed only from those
   artefacts or their proving generator.
3. Recover the GPT-5.5 output, comparison code/report, and exact 380-record hard
   frame; confirm that the documented 182/143/55 and 11-tag counts reproduce.
4. Locate the superseded v7 exclusion file and provide or approve the final v8
   22-Record-ID artefact. Decide whether v7 should be retained privately or as
   excluded historical provenance.
5. Decide how to materialise the standalone frozen cleaned register and exact
   rendered production prompt without rerunning a model.
6. Decide whether the dirty-worktree deterministic manifest is acceptable
   supporting provenance or must be replaced by a clean, portable manifest.
7. Decide whether the empty production layer summary should be omitted or
   replaced by a verified report derived without changing scientific outputs.
8. Approve the validation-specific sampling, REDCap, analysis, adjudication,
   log-template, and dependency-lock artefacts before registration and before
   any official sampling.
9. Confirm access and publication treatment for the trainer guide, Jo-review
   decision log, active identities, and any restricted hash commitments.

## Sampling confirmation

No active or reserve sample was drawn or generated. No sample manifest was
created. `SEED_DRAW = 20260713` is documented only as the future formal seed and
was not executed against the real frame. No reserve IDs were inspected or
written, no REDCap export was generated, and formal human coding has not begun.
