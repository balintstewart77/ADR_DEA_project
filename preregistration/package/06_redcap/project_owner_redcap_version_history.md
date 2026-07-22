# Standalone Project Owner REDCap version history

## owner-redcap-candidate-0.1 - 2026-07-22

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
