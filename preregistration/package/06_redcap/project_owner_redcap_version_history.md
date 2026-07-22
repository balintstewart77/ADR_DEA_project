# Standalone Project Owner REDCap version history

## owner-redcap-candidate-0.2 - 2026-07-22

- Current four-instrument development candidate: Owner Contact Admin (31),
  Project Owner Consent (12), Owner Assignment Admin (39), and Project Owner
  Review (85), totalling 167 fields.
- Supersedes candidate 0.1 before any live import or data collection.
- Obtains affirmative, electronic and versioned informed consent once on each
  researcher contact record before project-review links are released.
- Removes the per-assignment po_ack field; later reviews instead display a brief
  reminder that each review remains voluntary.
- Missing, declined, withdrawn or stale consent blocks assignment-link release.
  Substantial changes to research activities or intended use require re-consent.
- Preserves separate researcher-level acknowledgement and response-level
  quotation permission.
- This proportional implementation refinement changes no substantive review
  question or scientific design and is compatible with Protocol v0.15.
- Status: unfrozen development candidate; not imported; synthetic live QA,
  source/live comparison, evidence archive and explicit freeze remain pending.

## owner-redcap-candidate-0.1 - 2026-07-22

- Superseded historical development candidate; unfrozen and never imported.
- Candidate 0.1 collected participation acknowledgement per owner–project
  assignment and was superseded by candidate 0.2 before live QA.
- First standalone three-instrument development candidate under Validation
  Protocol v0.15: Owner Contact Admin (27), Owner Assignment Admin (39), and
  Project Owner Review (86), totalling 152 fields.
- Implements one contact record per researcher and one assignment record per
  owner-project pair, joined by pseudonymous `owner_id` and stable DEA Record ID.
- Separates expression of interest from later record-specific survey links and
  adds an explicit affirmative-interest link-release gate.
- Keeps researcher-level named acknowledgement separate from participation and
  response-level anonymised quotation permission.
- Reviews both Applied and Not applied states for both binary tags with
  correctness and public-register determinability questions.
- Retains fixed domain/purpose slots and the owner taxonomy Fit / Partial Fit /
  No Fit distinction; unused slots are hidden and never required.
- Adds deterministic offline generation, validation, synthetic fixtures,
  recruitment materials, export specification and a future live-QA plan.
- Intended future synthetic-QA target: Development PID 9149. No connection,
  import, live record, invitation or respondent test has occurred.
- Status: unfrozen development candidate. Synthetic live QA, source/live
  comparison, evidence archive and explicit freeze remain mandatory before
  registration or real owner review.

The inherited 80-field owner form in frozen scratch candidate 0.7 remains
historical source material. Candidate 0.7 and its frozen copy are unchanged;
their scratch-project freeze does not freeze or validate this standalone owner
candidate.
