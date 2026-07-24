# Exclusions and sampling

This folder contains the authoritative v8 list of 22 unique excluded Record
IDs and the Phase 4 sampling-system package. The sampling engine remains at
`scripts/draw_validation_samples.py`, with synthetic tests at
`tests/test_draw_validation_samples.py`; package rows reference those canonical
paths rather than creating competing copies.

`sampling_specification.yaml` is the frozen specification archived with OSF
registration `8sn2j` under protocol v1.1. Its `registered: false` field records
the pre-approval state of the byte-exact archived packet and is intentionally
unchanged. Current registration status is recorded in the canonical artefact
manifest and `../../registration_records/osf_registration_8sn2j.yaml`. The
engine implements the unchanged 150/100 baseline draw, forced accompanying-tag
inclusion in the 25/25/25 active hard allocation, and the seed-governed 17/17/16
reserve allocation with deterministic fallback.

The official seed is `SEED_DRAW = 20260713`. It is public preregistration
metadata and was used exactly once for the official draw on 24 July 2026; it
was not used against the real frames during pre-registration Phase 4. `--check`
and `--validate-real-inputs` create no RNG and write nothing. Official execution is
guarded by canonical protocol metadata authorising the draw, a real registration
receipt, Gate 2 confirmation, matching frozen commit and hashes, a clean
worktree, restricted storage, an empty output location and a typed confirmation
token. Registration and Gate 2 are satisfied, and the one authorised draw is
complete. The restricted outputs contain 225 active and 150 reserve records;
no assignment or REDCap import output was created.

Gate 2 uses a two-commit handshake: clean verified implementation basis A,
followed by direct-child authorisation commit B. The tracked JSON receipt and
the manifest record `frozen_git_commit=A`, while execution requires clean
`HEAD=B` and `HEAD^=A`. B is not self-recorded. Its diff is restricted to the
receipt, manifest and enumerated administrative status files; any later commit,
sampling-code change, frozen-input change or unrelated file invalidates the
authorisation.

Only scratch-coder reserves are defined: 100 baseline and 50 hard-case records.
There is no fixed project-owner reserve. Any later owner review follows the
separate post-revision recruitment rule in the protocol.

The code contains a synthetic-tested contactability-aware greedy resequencing
primitive, but no contactability search source hierarchy or maximum search
effort is invented here. Those operational details must be prespecified,
reviewed, and frozen after the remaining protocol gates; no real contact search
or cohort sequencing has occurred.

At registration, code, specification, seed, hashes, software environment,
schema and runbook were public without sampled identities. After the later
authorised draw, all identities remain restricted; active identities may be
released only after initial independent coding and a blinding review, while
reserve identities, strata and ranks remain embargoed through reserve retesting
or formal retirement. Aggregate counts and strata may be public.

The seeded hard-reserve target was Domain-only 16, Purpose-only 17 and
Domain-and-Purpose 17. Baseline-first selection and the active 25/25/25 quotas
left 11 Domain-and-Purpose reserve cases. The registered deterministic fallback
reallocated six unavailable seats evenly to the other strata, producing a final
19/20/11 reserve allocation with no total shortfall. This is compliant with the
frozen rule, is not a protocol deviation and did not trigger a redraw.

## Exclusion membership and provenance

Final exclusion membership is defined by actual coder exposure in the final
training and pilot materials. Record `2025/039` was used as keyed worked
example P4 and `2021/113` as keyed worked example T1, so both remain excluded.
Records `2019/010` and `2024/259` occurred in a superseded planning list but
were not used in the final coder-facing training materials and are not
excluded. Record `2021/090` was a referenced contrast rather than a retained
training or pilot case and is also not excluded. This audit confirmed the
existing membership; it did not change any exclusion.

The canonical v8 CSV is UTF-8 with a byte-order mark and LF line endings. The
repository-wide `*.csv text eol=lf` rule in `.gitattributes` governs both the
Git object and working-tree serialization. Its recorded SHA-256 is the raw-file
hash of that canonical LF serialization:
`cf36e6d34375d0e68bac31df8169207fc0602bc7291a64e995b9cd86141413a6`.
CRLF serialization may parse to the same rows, but it is not the canonical
packaged byte representation and must not be used to update provenance hashes.

This folder must not contain active or reserve manifests, executed draw logs,
assignments or reserve identities. The superseded v7 exclusion file was not
located; v8 remains exactly machine-verified as 11 keyed worked examples, one
discussion case and ten pilot records.
