# REDCap instruments

This folder contains the Phase 5 working candidate for one non-longitudinal
REDCap project with `assignment_admin`, `scratch_coder`, and `project_owner`
instruments. `assignment_id` is the record key: one reviewer-record assignment
is one REDCap record and one export row.

The candidate includes the importable combined dictionary, codebook,
field/response and branching specifications, headers-only assignment template,
expected export schema, taxonomy/variable mapping, setup and QA checklists,
version history, structural HTML preview, and blank live-runtime QA record.
The deterministic builder and offline validator remain at `scripts/`; synthetic
submission cases remain under `tests/fixtures/` and contain no real Record ID.

Scratch coders see only an opaque assignment code, title, datasets used, and
coding fields. Owners additionally see proposed labels and short definitions.
All source/reviewer IDs, sampling data, model provenance and rationales,
comparison status, reserve information, and other responses remain hidden.

No live REDCap project was accessed. Import, action-tag compatibility, user
rights, survey routing, mobile/desktop display, and export behaviour require
manual UCL REDCap QA before the excluded pilot. These artefacts are working
candidates, not frozen instruments. This folder must never contain completed
responses, formal assignments, live survey links, API tokens, or contacts.
