# Exclusions and sampling

This folder contains the authoritative v8 list of 22 unique excluded Record
IDs and the Phase 4 sampling-system package. The sampling engine remains at
`scripts/draw_validation_samples.py`, with synthetic tests at
`tests/test_draw_validation_samples.py`; package rows reference those canonical
paths rather than creating competing copies.

`sampling_specification.yaml`, `sampling_output_schema.json` and
`official_sampling_runbook.md` are tested working candidates ready for Gate 1
freeze. The engine implements the v0.11 candidate 150/100 baseline draw, forced
accompanying-tag inclusion in the 25/25/25 active hard allocation, and the
seed-governed 17/17/16 reserve allocation with deterministic fallback.

The official seed is `SEED_DRAW = 20260713`. It is public preregistration
metadata, but was not used against the real frames in Phase 4. `--check` and
`--validate-real-inputs` create no RNG and write nothing. Official execution is
guarded by canonical protocol metadata authorising the draw, a real registration
receipt, Gate 2 confirmation, matching frozen commit and hashes, a clean
worktree, restricted storage, an empty output location and a typed confirmation
token. The current v0.11 metadata fails that guard by design.

Only scratch-coder reserves are defined: 100 baseline and 50 hard-case records.
There is no fixed project-owner reserve. Any later owner review follows the
separate post-revision recruitment rule in the protocol.

The code contains a synthetic-tested contactability-aware greedy resequencing
primitive, but no contactability search source hierarchy or maximum search
effort is invented here. Those operational details must be prespecified,
reviewed, and frozen after the remaining protocol gates; no real contact search
or cohort sequencing has occurred.

At registration, code, specification, seed, hashes, software environment,
schema and runbook may be public. No sampled IDs exist yet. After a future
authorised draw, all identities remain restricted; active identities may be
released only after initial independent coding and a blinding review, while
reserve identities, strata and ranks remain embargoed through reserve retesting
or formal retirement. Aggregate counts and strata may be public.

This folder must not contain active or reserve manifests, executed draw logs,
assignments or reserve identities. The superseded v7 exclusion file was not
located; v8 remains exactly machine-verified as 11 keyed worked examples, one
discussion case and ten pilot records.
