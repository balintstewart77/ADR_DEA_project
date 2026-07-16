# REDCap candidate version history

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
