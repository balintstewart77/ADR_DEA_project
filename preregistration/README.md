# DEA validation preregistration workspace

## 1. Purpose

This directory contains the frozen preregistration materials and current
administrative state for the validation study of classifications applied to the
Digital Economy Act (DEA) accredited-project register. It separates the scoped
registered packet from restricted operational material and from outputs that
may exist only after registration.

## 2. Current study status

- `Validation_Protocol_PreReg_v1.1.docx` is the sole current preregistration
  protocol. It was frozen on 24 July 2026 after a typographical rendering
  correction to v1.0, which remains preserved as its superseded predecessor.
  OSF registration `8sn2j` was reported approved by the project lead at
  2026-07-24 14:45 Europe/London. The approval record does not by itself
  authorise formal sampling, assignment import or coding.
- REDCap candidate 0.7 passed completed administrator and restricted-user live
  QA and is the frozen 150-field formal instrument. No formal assignments are
  populated; candidates 0.3 and 0.6 remain historical pilot/QA references only.
- Phase 3 source, model, taxonomy, evidence and exclusion artefacts remain frozen.
- The single authorised official draw was executed once on 24 July 2026. It
  produced 225 active and 150 reserve records; all sampled identities remain
  restricted, and the reserve is not activated.
- Assignment generation, REDCap import, formal validation coding and Project
  Owner recruitment remain unauthorised or unstarted as applicable.
- The durable approval receipt is
  `registration_records/osf_registration_8sn2j.yaml`; its evidence basis is
  `project_lead_reported`, not an independently verified archival status check.

The current cleaned population is 1,308 retained register records representing
1,304 unique official Project IDs. Four Project IDs occur on two retained
records each. Sampling and exclusions must use stable synthetic `Record ID`,
not official Project ID.

## 3. Workspace map

- `package/00_protocol/`: reviewed protocol source and final registration PDF.
- `package/01_source_and_cleaning/`: source snapshot, cleaning/versioning
  evidence, duplicate rulings, Record-ID procedure, and frozen cleaned register.
- `package/02_taxonomy_prompt_and_model/`: frozen taxonomy, production prompt
  implementation/version, production configuration, classifications and the
  Phase 3 production release manifest.
- `package/03_preexisting_model_evidence/`: model repeatability and GPT-5.5
  comparison evidence that predates registration.
- `package/04_exclusions_and_sampling/`: final v8 exclusions and frozen sampling
  code, tests, and execution checklist; never operational reserve IDs.
- `package/05_training_and_pilot/`: current coder/trainer handouts, pilot/debrief
  reference, structured record manifest, and machine-checked teaching/pilot
  membership; no blinded assignments.
- `package/06_redcap/`: data dictionaries, codebook, and import templates; no
  formal exports or personal contact data.
- `package/07_analysis/`: prospective confirmatory analysis code and dependency
  lockfile; no results generated before registration.
- `package/08_adjudication_and_release/`: preregistered adjudication instrument,
  audit-selection code, and blank evidence/sign-off templates.
- `package/09_logs_and_templates/`: blank deviation, instrument-change, coding-
  clarification, and review-decision logs.
- `registration_records/`: durable public administrative receipts recorded
  after registration; never a substitute for restricted draw authorisation.
- `post_registration/`: outputs and amendments created only after registration.

The numbered package folders contain the current reviewed artefacts, historical
versions, operational templates and scope READMEs. Their status and proposed
registration treatment are recorded in `preregistration_artifact_manifest.csv`.

Phase 3 follows this reference-based convention. Exact current paths and hashes
are recorded in
`package/02_taxonomy_prompt_and_model/production_release_manifest.yaml`; no
parallel authoritative copies were created.

## 4. Public, restricted and post-registration materials

The scoped 18-file OSF packet references selected files from
`preregistration/package/` and the repository; the broader package directory is
not itself the scoped upload list. `preregistration_restricted/` is a separate,
Git-ignored local area for restricted operational material.
`preregistration/post_registration/` is for outputs produced only after
registration. Material must not be moved between these areas merely for
convenience: access and study timing determine location.

Reserve Record IDs, trainer-only answer keys, personal contact details, and
blinded assignment files belong only in `preregistration_restricted/`. Formal
REDCap exports remain restricted post-registration data.

## 5. Prospective versus pre-existing evidence

The production-model repeatability exercise and GPT-5.5 comparison are
pre-existing evidence. Their locally recovered/current artefacts have been
deterministically verified offline and documented in the model-evidence
package. Human coding, project-owner review, confirmatory analysis,
adjudication, and the release decision are prospective. The manifest labels every row as `pre_existing`,
`prospective`, `mixed`, or `not_applicable` so the timing distinction survives
packaging.

## 6. Artefact-state definitions

The manifest uses these columns and controlled values.

- `artifact_id`: stable unique manifest identifier.
- `artefact_group`: numbered package or operational group.
- `filename`: expected basename, whether or not the file currently exists.
- `current_path`: repository-relative current location; blank when absent or
  when recording only a sensitive category.
- `proposed_package_path`: proposed destination, not evidence that copying has
  occurred.
- `description`, `version`, `notes`: manually maintained explanatory fields.
- `sha256`, `size_bytes`, `created_or_modified_at`, `source_commit`: exact-
  content and inventory-refresh provenance for existing non-sensitive files.
- Protocol rows additionally use `size_bytes`, `git_blob_oid`,
  `protocol_source_commit`, `protocol_source_commit_date`,
  `protocol_source_commit_message`, and `implementation_last_checked_commit`.
  The protocol-source commit identifies where the DOCX was introduced; the
  implementation-check commit identifies the repository revision audited
  against it. Neither is a future final-package freeze commit.
- `protocol_status`, `current_implementation_basis`, `frozen`, `registered`,
  `official_sample_draw_authorised`, `supersedes`, `superseded_by`, and
  `pending_gates` record protocol state without overloading registration intent.

`current_state`:

- `existing`: present and inspectable.
- `working_candidate`: present but still under active review.
- `missing`: expected from prior work but not located.
- `placeholder`: category or planned template represented without study data.
- `superseded`: retained only for history and not current use.
- `historical_git_only`: superseded unregistered protocol draft retained through
  Git history and manifest metadata, with no physical working-tree path.
- `needs_verification`: present, but identity, completeness, or provenance is
  unresolved.
- `not_yet_generated`: prospective output or template that should not yet exist.

`status_at_registration`:

- `frozen`: intended to be immutable at registration.
- `draft_template`: blank structure registered before prospective use.
- `restricted_and_hash_committed`: restricted item represented only through an
  approved commitment, never through disclosed content.
- `post_registration_output`: generated only after registration.
- `not_yet_generated`: absent and not currently ready for registration.

`pre_existing_or_prospective`:

- `pre_existing`: evidence or source created before registration.
- `prospective`: created or populated after registration under the protocol.
- `mixed`: contains clearly separated pre-existing and prospective components.
- `not_applicable`: timing classification does not apply.

`access_class`:

- `public`: suitable for the public package after review.
- `restricted`: operational material not for public upload.
- `temporarily_embargoed`: withheld until the stated study stage is complete.
- `contains_personal_data`: handled under the applicable data controls and never
  hashed into the public manifest.
- `undecided`: access decision is still required.

`registration_inclusion`:

- `include`: proposed for the immutable package.
- `link_only`: referenced without copying the content into the public package.
- `exclude`: not part of the public registration package.
- `undecided`: inclusion requires an explicit decision.

`authoritative_status`:

- `authoritative`: supported by explicit repository or study-design evidence.
- `current_candidate`: apparent current review candidate, not frozen.
- `supporting`: relevant evidence but not the governing artefact.
- `superseded`: replaced and not valid for current use.
- `ambiguous`: authority or identity cannot be established from available
  evidence.
- `missing_expected_artefact`: required artefact was not found.
- `not_applicable`: authority classification does not apply.

## 7. Hash and provenance conventions

SHA-256 identifies exact file content. The repository commit is recorded in a
separate field because a content hash and a Git revision answer different
questions. A hash does not imply that a draft is frozen, scientifically valid,
or authoritative. File modification times are recorded in UTC and are useful
inventory metadata, not proof of authorship or authority.

Sensitive content, secrets, environment files, contact lists, reserve IDs,
trainer keys, and blinded assignments must not be hashed into this public
manifest. A repository-controlled restricted artefact may be represented by a
non-sensitive repository-relative path and classification, but its content hash
is omitted and the file is excluded from the public registration package unless
a separately approved commitment procedure is adopted.

The manifest does not hash itself because doing so would be recursive. Tracked
`.gitkeep` directory markers are repository structure rather than study
artefacts and are outside manifest coverage. Office lock files, `.Rhistory`,
caches and temporary exports are prohibited package detritus.

## 8. Authority and versioning

The manifest distinguishes authoritative, candidate, supporting, superseded,
ambiguous, and missing artefacts. A higher version number or later timestamp is
not, by itself, evidence of authority. Phase 3 source, cleaning, production and
pre-existing-evidence artefacts are frozen only after their completed offline
cross-document audit. Prospective materials are finally frozen only after their
applicable collaborator-review and pilot gates are complete; protocol v1.1 now
records completion of the protocol freeze. After registration, changes require a new version;
substantive changes also require a preregistration amendment recorded under
`post_registration/amendments/`.

The current v8 training/pilot exclusion list contains 22 unique stable Record
IDs and is verified for exact equality with the canonical coder, trainer,
discussion, and pilot/debrief materials. No physical v7 file has been located
in the worktree or Git history, so the manifest does not invent a historical
file row for it. The same rule applies to previously inventoried but unlocated
taxonomy-backup, trainer-guide and pilot-assignment filenames.

## 9. Blinding and embargo

Active sample identities are withheld from coders through blinded assignments.
Reserve Record IDs remain embargoed and unexamined until reserve retesting is
complete or the reserve is formally retired. Trainer answer keys and personal
contact data remain restricted. Empty restricted folders are not invitations to
populate them before the protocol permits the corresponding operation.

## 10. OSF registration record

The scoped 18-file packet for protocol v1.1 is recorded as approved on OSF under
registration ID `8sn2j`. The machine-readable public receipt is
`registration_records/osf_registration_8sn2j.yaml`. The project lead supplied
the approval time and status; the repository does not claim an independently
verified archival timestamp. Restricted operational material was not part of
the public registration. Recording this approval does not authorise the sample
draw or create a Gate 2 execution receipt.

## 11. Phase 3 completion and unresolved artefacts

The detailed inventory and `phase_3_completion_report.md` record the completed
offline Phase 3 audit. The frozen cleaned register, production classification,
Fable 5 run-to-run package, current Fable 5/GPT-5.5 comparison package and exact
22-record exclusions reproduce and are hash-linked in the production release
manifest. A 16-ID boundary-whitespace defect in the previous cleaned population
was corrected before registration without changing the raw source or any
classification content.

The exact static production prompt has been rendered offline from the unchanged
hashed classifier code and hashed taxonomy and is now hash-bound as MOD-003.
Record-specific project blocks remain separately fingerprinted; no model or API
was called to create the static rendering. Protocol freeze, registration and the
separate prospective Gate 2 draw authorisation are complete. The official draw
was executed exactly once at authorisation commit
`9fcabc3699ae2f047b7d33460c9867ab68457455`; restricted outputs and aggregate
provenance are recorded by POST-008 and the post-registration execution log.

## 12. Phase 4 sampling-system completion

Phase 4 produced a deterministic, test-covered sampling engine without drawing
the official sample. Its machine-readable specification fixes the PCG64 RNG,
stable Record-ID sorting, exact generator-consumption order, 150/100 baseline
allocation, 25/25/25 active hard allocation, forced accompanying-tag rule and
17/17/16 hard-reserve fallback. The official seed is recorded but tests use
only non-official seeds.

The engine has separate `--check` and `--validate-real-inputs` paths that do not
instantiate an RNG or write files. The latter verified the frozen 1,308-row
population, exact 22 exclusions and 380-row disagreement frame (182
domain-only, 143 purpose-only, 55 both; 11 accompanying-tag cases). Official
mode requires registration and Gate 2 receipt evidence, hash and commit
agreement, a clean worktree, restricted empty output storage and a typed token.

At registration, the code, specification, seed, hashes, environment, output
schema and runbook were archived without sampled identities. The later official
draw created active and reserve identities, which remain restricted under the
embargo in the specification and runbook. See `phase_4_completion_report.md`.

## 13. Phase 5 REDCap candidate

Phase 5 resolved a stale coder-handout blinding table in favour of the protocol:
visible assignment IDs are opaque, while reviewer/source IDs and all sampling,
model, comparison, reserve, and other-response metadata are hidden. No teaching
answer or exclusion ID changed.

Package 06 contains frozen candidate 0.7: one combined 150-field dictionary
covering Assignment Admin, Coder Declaration, Scratch Coder and Project Owner.
Completed administrator and restricted-user live QA, source/live equivalence,
archive controls and dashboard permissions are documented. No formal validation
assignment is populated. Candidate 0.3 pilot and candidate 0.6 intermediate-QA
materials are explicitly historical. Gate 2 authorised only the now-completed
official draw; assignment generation and REDCap import remain prohibited until
separately authorised after the draw.

## 14. How to update the manifest

From the repository root, check hashes and provenance without writing:

```bash
python scripts/update_preregistration_manifest.py --check
```

Refresh only computed hash, modification-time, and commit fields:

```bash
python scripts/update_preregistration_manifest.py
```

The utility preserves manually entered descriptions and classifications. It
does not alter scientific files and skips missing, prospective, and restricted
rows. Do not use its restricted opt-in for this public manifest without a
separately reviewed hash-commitment procedure.
