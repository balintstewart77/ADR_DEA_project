# REDCap candidate version history

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
- Status: working review candidate pending pilot closure, Jo's review,
  propagation of resulting changes, repository QA, and fresh live runtime QA.

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
