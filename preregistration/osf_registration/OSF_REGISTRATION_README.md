# OSF preregistration packet

## Registration identity

- **Study title:** Validation protocol for LLM-assisted classification of the DEA accredited research projects register
- **Protocol version:** v1.0
- **Protocol manifest ID:** PRO-017
- **Protocol byte size:** 413327 bytes
- **Protocol SHA-256:** `6d385f40443e96b0b8cc774610b5d0ff6947ae43dff42576aa1a84c90dc8906e`
- **Protocol-freeze Git commit:** `200021df2d57b3c50ef0cc4eab63aac98ef03b52`
- **Repository:** `balintstewart77/ADR_DEA_project`
- **Branch:** `main`
- **Preparation date:** 24 July 2026

This packet prepares the OSF upload. It does not state that the registration has
already been submitted, approved or assigned an OSF registration identifier.

## Packet contents and purpose

The scoped manifest lists 16 scientific, design and provenance artefacts:

- the frozen preregistration protocol, sampling specification and 22-record training/pilot exclusion list;
- the frozen taxonomy and exact production prompt;
- the frozen Fable 5 classifications under validation and their run metadata;
- source and population provenance plus reviewed duplicate rulings;
- the exact pre-existing GPT-5.5 comparison output;
- cross-model metrics and the canonical 380-record disagreement frame used for hard-case sampling;
- production-model repeat-run stability metrics;
- the frozen scratch-coder REDCap dictionary; and
- the post-pilot shared calibration note.

The 16 listed artefacts, this README and `osf_registration_manifest.csv` make
exactly 18 OSF files. The manifest does not list or hash itself or this README.

The scoped manifest records two forms of byte provenance. `byte_size` and
`sha256` identify the exact working-tree files prepared for OSF upload.
`git_blob_byte_size` and `git_blob_sha256` identify the canonical repository
blobs at the common packet-basis commit
`f81724a7a740a7511a7bd70e0929cea6b04d9677`. For text files checked out with
Windows line endings, the raw upload bytes may differ from the LF-normalised Git
blob; such cases are accepted only where Git clean-filter verification proves
that both represent the same committed content. No scientific file was
rewritten for this packet.

`production_release_manifest.yaml` is preserved unchanged as the historical
frozen Phase 3 release record. Later pilot, instrument-freeze and protocol
status is governed by protocol v1.0 and this registration README.

### Cross-model metrics provenance

The frozen Phase 3 production-release manifest records SHA-256
`c7ae2c262b0c6da67320c65881b5c973d979f7a22967461afc8eefbf2f4d0c7d`
for the cross-model metrics file. Those exact bytes occur at repository commit
`e0c322fd77ae93a574a0dfcee076757d294de0d2`, rather than at the manifest's
top-level repository commit
`e9d53023417348ad2784e629c855bf8d04f38df8`. The registration archives the
later provenance-refreshed version with SHA-256
`d84c3d497d3c556f7d59aaf1471738ff455d6edcf626d39f0f618b97bd136e7a`.
Direct JSON comparison confirmed that only the canonical GPT-5.5 source path
changed; all scientific metrics, counts and referenced model-output hashes are
unchanged. The frozen production-release manifest is preserved without
modification.

## Prospective boundary

At the time represented by this packet:

- shared training, the ten-record pilot and post-pilot calibration had occurred, and every associated record was permanently excluded from validation and reserve samples;
- no active validation sample or reserve sample had been drawn;
- no formal 675-row assignment import had occurred;
- no formal scratch-coder validation responses existed;
- official sampling and assignment import remained unauthorised pending registration and the subsequent authorization gate; and
- Project Owner recruitment and data collection had not begun, and owner activity remained conditional on ethics approval, live QA and instrument freeze.

## Deliberate exclusions

This scoped packet deliberately excludes:

- the raw UKSA register snapshot and cleaned 1,308-record register CSV;
- `crossmodel_comparison.csv` and Fable repeat-run caches;
- protocol v0.18 and earlier versions;
- the full repository artefact manifest;
- Project Owner instrument candidates; and
- sampled-record or assignment files.

Population identity remains fixed through the source-provenance record,
production-release manifest, reviewed duplicate rulings, hashes and repository
commit. The exact frozen production and comparison-model outputs are included.
The canonical 380-record disagreement frame and cross-model metrics are
included, so the full comparison table is not required.

### Training-material identity limitation

No definitive coder- or trainer-handout identity is asserted by this
registration. Historical and working handout versions remain preserved in the
repository, but this registration does not identify any one file as the
definitive byte-exact handout governing formal validation coding. The post-pilot
shared calibration note is archived separately because its identity and
simultaneous circulation to all three coders are established.

### Other protocol §11 materials

Other reproducibility materials named in protocol §11—including the comparison
and sampling scripts, analysis code, scratch-coder coding guide, pilot-debrief
materials, and the protocol-deviation, instrument-change and dated
pilot-feedback logs—remain preserved in repository
`balintstewart77/ADR_DEA_project`, branch `main`, at protocol-freeze commit
`200021df2d57b3c50ef0cc4eab63aac98ef03b52`, and are linked rather than
duplicated in this scoped OSF upload.

- **Comparison scripts:** `analysis/outputs/gpt55_crossmodel_stratum_run.py`; `analysis/crossmodel_comparison.py`; `analysis/regenerate_crossmodel_evidence.py`; `analysis/verify_fable_run_stability.py`
- **Sampling scripts:** `scripts/draw_validation_samples.py`
- **Analysis code:** `preregistration/package/07_analysis/run_validation_analysis.py`; `analysis/validation/alpha.py`; `analysis/validation/bootstrap.py`; `analysis/validation/diagnostics.py`; `analysis/validation/adjudication.py`; `analysis/validation/release.py`
- **Scratch-coder coding guide:** `preregistration/package/06_redcap/redcap_instrument_codebook.md`
- **Pilot-debrief materials:** `preregistration/package/05_training_and_pilot/DEA_pilot_projects_trainer_debrief_reference.docx`; `preregistration/package/05_training_and_pilot/DEA_pilot_projects_trainer_debrief_reference_v2.docx`
- **Protocol-deviation log:** `preregistration/package/09_logs_and_templates/protocol_deviation_log.csv`
- **Instrument-change log:** `preregistration/package/09_logs_and_templates/instrument_change_log.csv`
- **Dated pilot-feedback log:** `preregistration/package/05_training_and_pilot/pilot_feedback_log_20260717.md`

## Scope, reproducibility and rights

The 18-file OSF packet is a deliberately scoped archival packet rather than a
complete repository export. The items in the deliberate-exclusions section are
omitted by design. Separately, the handout omission reflects an unresolved
byte-identity limitation. The other protocol §11 materials are accounted for
through their concrete repository paths and the protocol-freeze commit rather
than duplicated in the OSF folder. The repository also contains additional
tests, logs, caches and historical materials. Hashes in
`osf_registration_manifest.csv` identify the exact files archived with the
registration.

Register-derived fields are adapted from data published by the UK Statistics
Authority and remain subject to the Open Government Licence v3.0. Any licence
selected for the OSF project or registration does not supersede third-party or
source-data rights.

The reproducibility reference is repository
`balintstewart77/ADR_DEA_project`, branch `main`, with protocol-freeze commit
`200021df2d57b3c50ef0cc4eab63aac98ef03b52`.
