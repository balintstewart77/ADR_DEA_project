# REDCap candidate version history

## redcap-candidate-0.6 — 2026-07-21

- Created from intermediate formal candidate 0.5 in response to final coder
  usability feedback on the revised scratch-coder taxonomy-fit question. The
  feedback request was circulated with the shared calibration note to all three
  scratch coders on 21 July 2026. All three responded. No additional substantive
  taxonomy or instrument concerns were raised; one coder requested clearer
  operational guidance for using `Cannot assess from register entry`.
- Added point-of-use help text to `sc_taxonomy_fit`: "Taxonomy fit asks whether
  the taxonomy can adequately represent the project, not whether the public
  register entry contains enough information to judge this. Select “Cannot
  assess from register entry” when the entry is too limited to determine
  taxonomy fit. Do not select “Partial Fit” or “No Fit” solely because the entry
  lacks information."
- This is an operational clarification of the revised diagnostic instrument.
  It does not change the taxonomy, Research Domain or Analytical Purpose rules,
  field name, radio type, answer codes or labels, field order, required status,
  branching, validation, export mappings, or candidate-0.3 pilot data.
- `Cannot assess from register entry` records an inability to judge taxonomy fit
  from insufficient visible evidence. It is distinct from `Partial Fit` or `No
  Fit`, which indicate a genuine taxonomy limitation for a sufficiently
  understood project.
- Regenerated the dictionary, machine-readable field specification, structural
  preview, candidate specification, and synthetic fixtures from the
  deterministic local builder. The preview now renders dictionary field notes
  so the point-of-use guidance is visible in the human-readable derivative.
- The coder-feedback window is closed because all three coders responded before
  the stated close-of-play deadline on Wednesday 22 July 2026. Their responses
  are not treated as formal approval or endorsement. Screenshot-based guidance
  remains planned for the coder start pack.
- Candidate 0.6 is the current working formal-instrument review candidate. It
  has passed offline repository validation, but it has not been imported into
  REDCap, has not passed fresh live runtime QA, and is not frozen or authorised
  for formal coding.

## redcap-candidate-0.5 — 2026-07-18

- Provisional repository candidate aligned to protocol v0.11. It has not been
  imported into or connected to REDCap and is not authorised for formal use.
- Added hidden, read-only owner recruitment-route, greedy-sequence position,
  invitation/checkpoint, reminder, contact disposition, supplementary-reason,
  and response-status fields. These preserve sequence-based, supplementary
  purposive, and post-revision routes in exports without exposing them to
  reviewers.
- Recorded the 50-unique-record sequence target, 25-record minimum viable
  threshold, maximum 10 supplementary invitations, 42-day close, and absence of
  a fixed project-owner reserve in the machine-readable candidate specification.
- Preserved all respondent-facing candidate-0.4 fields and codes. Candidate 0.3
  and 0.4 remain historical decode-compatible versions; no pilot data were
  recoded or regenerated.
- Status at this version: intermediate working review candidate pending pilot closure, Jo's review,
  propagation of resulting changes, repository QA, and fresh live runtime QA.
- Post-pilot shared calibration did not introduce another instrument or
  taxonomy change. The already-implemented distinction remains: `Cannot assess
  from register entry` records inability to judge taxonomy fit from thin public
  evidence; `Partial Fit` and `No Fit` record genuine taxonomy limitations for
  a sufficiently understood project. Candidate-0.3 pilot responses remain
  unchanged, and candidate 0.5 applies only to formal coding after repository
  validation and fresh live REDCap runtime QA.
- The shared-calibration decision is cross-referenced in
  `../05_training_and_pilot/pilot_feedback_log_20260717.md` and
  `../09_logs_and_templates/coding_clarification_log.csv`. At the candidate 0.5
  stage, the coder circulation and remaining-feedback request were prepared but
  not yet recorded as sent. Candidate 0.6 records the subsequent circulation,
  feedback resolution, and continuing live-QA gate.

## redcap-candidate-0.4 — 2026-07-17

- Created after the 17 July shared scratch-coder training feedback and pilot
  launch, before formal validation coding and before preregistration
  submission. Candidate 0.3, not candidate 0.4, was used for the pilot.
- Added scratch-coder stored choice 4, Cannot assess from register entry. The
  complete new sc_taxonomy_fit set is 1 Fit; 2 Partial Fit; 3 No Fit; 4 Cannot
  assess from register entry. Project-owner po_taxonomy_fit remains 1 Fit;
  2 Partial Fit; 3 No Fit because owners assess actual-project fit separately
  from public-entry sufficiency.
- Replaced each candidate-0.3 taxonomy-issue choice set — 1 Missing category;
  2 Ambiguous/overlapping categories; 3 Too broad; 4 Too narrow; 5 Other;
  6 None — with 1 Missing or inadequately represented category; 2 Ambiguous or
  overlapping category boundaries; 5 Other taxonomy problem.
- Retained stored codes 1, 2 and 5. Retired codes 3, 4 and 6 without reuse or
  renumbering. Historical candidate-0.3 mappings remain decode-only and no
  pilot response is silently consolidated or destructively recoded.
- Limited each issue field to Partial Fit or No Fit, retained multi-select
  behaviour, and required an explanatory note for Other taxonomy problem.
  Cannot assess is not No Fit, is not a taxonomy defect, and does not trigger
  the issue field.
- Added offline incoherence detection for scratch Cannot Assess with Sufficient
  register evidence. Partial or Insufficient evidence does not force Cannot
  Assess.
- Preserved all domain labels and cardinality, the purpose labels and maximum
  two rule, both Unclear exclusivity rules, the COVID tag, and the
  demographic-disparities/equity tag. This is not a substantive taxonomy
  change.
- The pilot exclusion set, sampling artefacts, assignments, taxonomy, prompts,
  production outputs and cross-model frame were not changed. No formal
  validation coding had begun.
- Status: repository-validated working candidate for post-pilot formal coding.
  Candidate-0.4 live runtime QA remains pending until manually tested.

## redcap-candidate-0.3 — 2026-07-16

- This was the instrument version used for the 17 July excluded pilot. Its
  pilot assignment imports and instrument_ver values remain unchanged.
- Candidate dictionary SHA-256:
  `d690ec4a882ff8a7eddc9c227952e09db0af51992948e5e1f8731dc5d2e891c7`.
- Its exact taxonomy-fit choices for both streams were 1 Fit; 2 Partial Fit;
  3 No Fit. Its exact taxonomy-issue choices for both streams were 1 Missing
  category; 2 Ambiguous / overlapping categories; 3 Too broad; 4 Too narrow;
  5 Other; 6 None. These values remain the historical decoding schema.

- Corrected a hidden administrative-schema defect discovered while preparing
  to generate the frozen scratch-coder training-pilot import: candidate 0.2
  could not represent the already-specified Pilot sample without an incorrect
  substitute.
- Added `4, Pilot` to `sample_set` while preserving `1, Baseline`, `2, Hard
  case`, and `3, Owner review` exactly.
- Required Pilot administration to use `validation_included = 0` (No) and
  added synthetic and regression coverage for the exact mapping, unknown
  codes, and pilot exclusion.
- Preserved the protocol-authoritative ten pilot Record IDs, the complete
  22-record exclusion set, taxonomy, respondent-facing Scratch Coder form and
  branching, sampling design, `@MAXCHECKED=2`, and the corrected generic-note
  exposure behavior.
- No invalid substitute code was used and no pilot assignment file was
  generated under the invalid schema or during this revision. No validation or
  reserve sample was drawn.

## redcap-candidate-0.2 — 2026-07-16

- Applied two confirmed UCL REDCap runtime corrections after synthetic-only
  testing: `@MAXCHOICE=2` became `@MAXCHECKED=2`, and `sc_exposure` was removed
  from the generic `sc_note` branch.
- Preserved Unclear exclusivity, response codes, taxonomy labels, and all other
  instrument content. The dedicated `sc_exposure_note` remains required when
  `sc_exposure = 1`.
- Regenerated the candidate dictionary, field/response specification,
  branching/validation specification, structural preview, and synthetic
  fixtures; added regression tests for both initial defects.
- Seven synthetic assignment records confirmed one row per assignment. Fresh
  records confirmed both fixes. Essential Scratch Coder runtime QA passed;
  Project Owner runtime QA remains outstanding.
- Status: corrected working candidate; not piloted or frozen. No pilot or real
  assignments were created.

## redcap-candidate-0.1 — 2026-07-15

- Audited repository commit: `6da64a4eb003396856d85fe4fcf71cbe886be1bb`.
- Status: working candidate; not imported, live-tested, piloted, or frozen.
- Created one-project, three-instrument dictionary, schemas, validation rules, synthetic fixtures, preview, and handoff records.
- Applied protocol-authoritative opaque assignment IDs and hidden reviewer, source, sampling, and model fields.
- Candidate owner visibility categories and all action tags require live-instance confirmation.
- Final freeze occurs only after collaborator review, training, the excluded pilot, and resolution of findings.
