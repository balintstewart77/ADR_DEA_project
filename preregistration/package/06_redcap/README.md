# REDCap instruments

This folder contains the Phase 5 working candidate for one non-longitudinal
REDCap project with `assignment_admin`, `scratch_coder`, and `project_owner`
instruments. `assignment_id` is the record key: one reviewer-record assignment
is one REDCap record and one export row. The current version is
`redcap-candidate-0.3`.

The candidate includes the importable combined dictionary, codebook,
field/response and branching specifications, headers-only assignment template,
expected export schema, taxonomy/variable mapping, setup and QA checklists,
version history, structural HTML preview, runtime-QA template, and dated
2026-07-16 runtime-QA record.
The deterministic builder and offline validator remain at `scripts/`; synthetic
submission cases remain under `tests/fixtures/` and contain no real Record ID.

Scratch coders see only an opaque assignment code, title, datasets used, and
coding fields. Owners additionally see proposed labels and short definitions.
All source/reviewer IDs, sampling data, model provenance and rationales,
comparison status, reserve information, and other responses remain hidden.

Candidate 0.3 adds the hidden administrative `sample_set` code `4, Pilot` so
the already-specified excluded training pilot can be represented without
misusing Baseline, Hard case, or Owner review. Pilot administration must use
`validation_included = 0`. This correction does not change pilot membership,
the respondent-facing instruments, taxonomy, protocol, or sampling design. No
pilot assignment file was generated under candidate 0.2 or during this schema
revision.

Synthetic-only testing in a UCL REDCap test project identified and confirmed
corrections to the Analytical Purposes maximum-selection tag and the generic
Scratch Coder explanatory-note branch. Seven synthetic assignment records
confirmed one row per assignment, and essential Scratch Coder runtime QA
passed. Project Owner runtime QA remains outstanding. These artefacts are
working candidates, not frozen instruments; no pilot or real assignments have
been created. This folder must never contain completed responses, response
exports, formal assignments, live survey links or project identifiers, API
tokens, personal information, or contacts.
