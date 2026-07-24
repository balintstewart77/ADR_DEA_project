# OSF preregistration packet

## Registration identity

- **Study title:** Validation protocol for LLM-assisted classification of the DEA accredited research projects register
- **Protocol version:** v1.0
- **Protocol manifest ID:** PRO-017
- **Protocol byte size:** 413327 bytes
- **Protocol SHA-256:** `6d385f40443e96b0b8cc774610b5d0ff6947ae43dff42576aa1a84c90dc8906e`
- **Protocol-freeze Git commit:** `200021df2d57b3c50ef0cc4eab63aac98ef03b52`
- **Packet preparation date:** 24 July 2026

The protocol identity above was verified directly from the current file bytes.
This packet prepares the OSF upload; it does not state that the registration has
already been submitted, approved or assigned an OSF registration identifier.

## Status represented by this packet

- The cleaned 1,308-record population and Fable 5 classification release were frozen.
- Scratch-coder REDCap candidate 0.7 had completed training/pilot QA and was frozen.
- Shared training, the ten-record pilot and post-pilot calibration had already occurred.
- Every training, discussion and pilot record was permanently excluded from validation and reserve samples.
- No active validation or reserve sample had been drawn.
- No formal 675-row assignment import had occurred, and official sampling and assignment import remained unauthorised until OSF registration and the subsequent authorization gate.
- No formal scratch-coder validation responses existed.
- Project Owner recruitment and data collection had not begun. Project Owner activity remained conditional on ethics approval, live QA and instrument freeze.

## Packet scope

`osf_registration_manifest.csv` lists the eight scientific artefacts intended
for separate upload and records hashes computed from their current repository
bytes. Together they identify the preregistered design, exclusions and frozen
classification system. The full repository contains additional provenance,
tests, scripts and pre-existing evidence.

The full repository artefact manifest is intentionally not included because it
is a broader internal inventory rather than the scoped OSF upload list. This
README and `osf_registration_manifest.csv` are administrative packet files and
will also accompany the upload, but neither is listed as a scientific artefact;
the packet manifest therefore does not hash itself or this README.

The coder handout is omitted. Repository metadata identifies the delivered v2
training handout as superseded and v3 as a working candidate/draft template
pending final approval and the coding authorization gate. The repository does
not demonstrate that v3 was both frozen and supplied to all coders, so no coder
handout identity is asserted here.

## Reproducibility reference

- **Repository:** `ADR_DEA_project`
- **Branch at packet preparation:** `main`
- **Freeze commit:** `200021df2d57b3c50ef0cc4eab63aac98ef03b52`
- **Public repository:** https://github.com/balintstewart77/ADR_DEA_project

Hashes in `osf_registration_manifest.csv` identify the exact scientific
artefacts intended for upload.
