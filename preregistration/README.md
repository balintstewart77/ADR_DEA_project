# DEA validation preregistration workspace

## 1. Purpose

This directory prepares the proposed immutable preregistration package for the
validation study of classifications applied to the Digital Economy Act (DEA)
accredited-project register. It separates materials intended for registration
from restricted operational material and from outputs that may exist only after
registration. Creating this workspace does not itself freeze or register an
artefact.

## 2. Current study status

- `Validation_Protocol_PreReg_v0.11.docx` is the current implementation and
  collaborator-review candidate. It is present but is not finally frozen or
  registered, and it does not authorise an official sample draw.
- Phase 3 is complete: the source, cleaned population, taxonomy/production
  classification release, pre-existing model evidence and exact exclusions are
  frozen and tied together by a machine-readable release manifest.
- Protocol, training, REDCap and other prospective validation artefacts remain
  absent or working candidates pending collaborator review and the pilot.
- No official active or reserve sample has been drawn.
- Formal human coding has not begun.
- Nothing in this workspace has been uploaded to OSF.

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
- `post_registration/`: outputs and amendments created only after registration.

The numbered package folders currently contain scope READMEs, not frozen copies
of the proposed artefacts. Proposed destinations are recorded in
`preregistration_artifact_manifest.csv`; copying is deferred until authority and
completeness decisions are resolved.

Phase 3 follows this reference-based convention. Exact current paths and hashes
are recorded in
`package/02_taxonomy_prompt_and_model/production_release_manifest.yaml`; no
parallel authoritative copies were created.

## 4. Public, restricted and post-registration materials

`preregistration/package/` is the proposed immutable public registration
package. `preregistration_restricted/` is a separate, Git-ignored local area for
restricted operational material. `preregistration/post_registration/` is for
outputs produced only after registration. Material must not be moved between
these areas merely for convenience: access and study timing determine location.

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
- `sha256`, `created_or_modified_at`, `source_commit`: legacy exact-content and
  inventory-refresh provenance for existing non-sensitive files.
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
manifest. Restricted categories are represented without paths or hashes unless
a separately approved commitment procedure is adopted.

## 8. Authority and versioning

The manifest distinguishes authoritative, candidate, supporting, superseded,
ambiguous, and missing artefacts. A higher version number or later timestamp is
not, by itself, evidence of authority. Phase 3 source, cleaning, production and
pre-existing-evidence artefacts are frozen only after their completed offline
cross-document audit. Protocol, teaching, REDCap and other prospective
materials are not finally frozen until their collaborator-review and pilot
gates are complete. After registration, changes require a new version;
substantive changes also require a preregistration amendment recorded under
`post_registration/amendments/`.

The v7 training/pilot exclusion file is superseded by design and must never be
labelled as the final exclusion set. The current v8 list contains 22 unique
stable Record IDs and is verified for exact equality with the canonical coder,
trainer, discussion, and pilot/debrief materials. No physical v7 file has been
located.

## 9. Blinding and embargo

Active sample identities are withheld from coders through blinded assignments.
Reserve Record IDs remain embargoed and unexamined until reserve retesting is
complete or the reserve is formally retired. Trainer answer keys and personal
contact data remain restricted. Empty restricted folders are not invitations to
populate them before the protocol permits the corresponding operation.

## 10. OSF mapping

The intended mapping, to be performed only after explicit approval, is:

- `preregistration/package/` -> immutable registration package;
- `preregistration_restricted/` -> private/restricted storage, not the public
  registration;
- `preregistration/post_registration/` -> associated working-project outputs.

This phase performs no OSF operation and uploads nothing.

## 11. Phase 3 completion and unresolved artefacts

The detailed inventory and `phase_3_completion_report.md` record the completed
offline Phase 3 audit. The frozen cleaned register, production classification,
Fable 5 run-to-run package, current Fable 5/GPT-5.5 comparison package and exact
22-record exclusions reproduce and are hash-linked in the production release
manifest. A 16-ID boundary-whitespace defect in the previous cleaned population
was corrected before registration without changing the raw source or any
classification content.

The exact production prompt is dynamically assembled by the hashed classifier
code from the hashed taxonomy; no separate rendered prompt file exists. This is
an explicit packaging limitation, not an unresolved production identity.
Remaining work concerns the future protocol, pilot and training freeze,
REDCap, Gate 1/Gate 2 execution, prospective analysis, adjudication and
log-template artefacts. No official active or reserve validation sample
manifests exist, as expected at this stage.

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
schema and runbook may be archived publicly. Actual sampled identities do not
exist yet. Future active and reserve identities remain restricted under the
embargo in the specification and runbook. See `phase_4_completion_report.md`.

## 13. Phase 5 REDCap candidate

Phase 5 resolved a stale coder-handout blinding table in favour of the protocol:
visible assignment IDs are opaque, while reviewer/source IDs and all sampling,
model, comparison, reserve, and other-response metadata are hidden. No teaching
answer or exclusion ID changed.

Package 06 now contains a locally validated candidate for one REDCap project
with hidden administration, scratch-coder, and project-owner instruments. The
dictionary is generated from the frozen taxonomy, and its branching,
assignment-import, export, blinding, and synthetic-response rules are checked
offline. No formal assignment or response exists. Live import, user-rights,
action-tag, rendering, routing, and export QA remain mandatory before the
excluded pilot; the candidate is not frozen.

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
