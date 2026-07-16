# REDCap instrument codebook

Status: working candidate `redcap-candidate-0.3`; final freeze follows collaborator review and the excluded pilot.

## Architecture

One non-longitudinal REDCap project contains `assignment_admin`, `scratch_coder`, and `project_owner`. `assignment_id` is the record key. One reviewer-record assignment is one REDCap record and one export row. Multiple coders or owners reviewing the same project have distinct opaque assignment IDs and share hidden `cluster_id` or `owner_project_id` values.

## Blinding and visibility

Scratch coders see only a neutral assignment code, title, datasets used, and scratch questions. Owners additionally see proposed labels and short definitions because reviewing them is their task. The administrative form and imported flags are hidden from surveys and read-only; user rights must also deny reviewer access.

Source IDs, reviewer IDs, sampling information, model provenance and rationales, disagreement data, reserve data, other responses, and owner comments are never piped to scratch forms. Proposed-label flags reveal only the labels under owner review, not model rationale or comparison status. No names, emails, or recruitment contacts occur in the public dictionary.

## Response codes

- Domains and purposes reproduce `dict-1.0-rc2`. Purposes permit one or two; Unclear is exclusive in both layers.
- Tags: `0 No`, `1 Yes`.
- Administrative sample set: `1 Baseline`, `2 Hard case`, `3 Owner review`,
  `4 Pilot`. Pilot administration must use `validation_included = 0` (No).
- Sufficiency: `1 Sufficient`, `2 Partial`, `3 Insufficient`.
- Taxonomy fit: `1 Fit`, `2 Partial Fit`, `3 No Fit`.
- Confidence: `1 High`, `2 Medium`, `3 Low`.
- Owner fit: `1 Fits`, `2 Does not fit`, `3 Unsure`.
- Owner public-entry visibility: `1 Clearly visible`, `2 Partly visible`, `3 Not visible`, `4 Unsure`.
- Taxonomy issue: Missing category; Ambiguous/overlapping categories; Too broad; Too narrow; Other; None. The local validator rejects `None` when a concern triggers the field.

The assignment import template is the authoritative ordered administrative list. It includes neutral assignment and stream identifiers, hidden reviewer/source/project IDs, frozen evidence fields, sampling and provenance fields, clustering fields, owner identifiers, and one proposed-label flag per canonical label. Candidate 0.3 adds only the hidden administrative `sample_set = 4` Pilot representation; it does not change any respondent-facing field.

REDCap generates `assignment_admin_complete`, `scratch_coder_complete`, and `project_owner_complete`; there is no redundant custom completion field. The local validator blocks unresolved conditional requirements.

## Candidate limitations

`@MAXCHECKED=2` and `@NONEOFTHEABOVE` were confirmed for the Scratch Coder fields in the tested UCL REDCap version. Survey piping, hidden/read-only tags, user rights, save/return, rendering, and the Project Owner instrument still require completion of their applicable runtime QA. The owner visibility categories are an implementation-level candidate operationalisation of the protocol distinction and require collaborator/pilot review. The HTML preview is structural, not pixel-perfect.
