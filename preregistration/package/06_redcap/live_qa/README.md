# Synthetic live-QA import fixtures

This directory contains import-only synthetic records for live REDCap runtime
QA. It contains no formal coder declaration, sampled project assignment, real
Record ID, response export, live URL, project identifier, or credential.

- `project_owner_synthetic_import_candidate_0.3.csv` is the unfrozen Project
  Owner candidate-0.3 long-format fixture for future controlled manual import
  into Development PID 9149. It contains one non-repeating row per synthetic
  owner and 1, 3 or 15 pre-created `project_review` repeat rows (three owners,
  19 assignments, 22 rows total). Participant responses are blank, repeat
  instances are numbered 1...N, both canonical tag statuses are pre-populated on
  every repeat, and no name, email or real Record ID is present. Its inline
  definitions use the 22 author-approved owner microdefinitions recorded on
  2026-07-23. Following the first PID 9149 import rejection, the canonical
  fixture was corrected to 87 importable columns: descriptive fields and all
  unexpanded checkbox base variables are excluded, while no participant
  checkbox or explanation responses are pre-populated. Continuing live QA also
  led to the REDCAP-016 Project Review wording/formatting and explanation-field
  correction. REDCAP-018 adds three importable, deterministic classification-
  summary fields and one non-importable descriptive overview, bringing the
  current fixture to 90 columns and dictionary to 108 fields. All 19 repeat rows
  contain summaries matching their proposal slots and both tag statuses; owner
  rows remain structurally valid. The regenerated dictionary and fixture must
  be re-imported before testing resumes. Controlled live QA remains required
  before freeze or recruitment.

For that controlled retry, delete disposable synthetic records, re-import the
dictionary, reconfirm `project_review` as the only repeating instrument and its
custom label, verify Survey Queue conditions and Stop Actions, enable Save &
Return Later and return without a separate Return Code, keep completed-response
modification and participant-created repeats disabled, import the regenerated
fixture, rerun affected desktop/mobile checks, and export all 19 offered
assignment rows. These are required live steps; this repository record does not
claim they are already configured in PID 9149.

After the REDCAP-020 dictionary re-import, live QA must also verify that Does not
fit/No requires its correctness explanation; Unsure displays no correctness
explanation and can submit without one; non-clear visibility permits blank
optional prose; missing-label Yes requires a valid selection but not prose;
Partial/Insufficient sufficiency permits a blank explanation; project-knowledge
Yes/Unsure permits a blank note; and Partial Fit/No Fit requires an issue type
but not a taxonomy explanation. Confirm that live REDCap requiredness and the
repository analytical-completion derivation agree. None of these checks is
recorded as passed until directly retested in PID 9149.
- `redcap_live_qa_synthetic_assignments_candidate_0.6.csv` is retained unchanged
  as historical evidence of the intermediate candidate-0.6 live test. Candidate
  0.6 was imported and partially inspected, then superseded before final runtime
  QA by candidate 0.7. It collected no formal data.
- `redcap_live_qa_coder_declaration_candidate_0.7.csv` creates one new synthetic
  declaration record with `record_kind = 2`, `validation_included = 0`, and
  `sample_status = 3`.
- `redcap_live_qa_synthetic_project_assignment_candidate_0.7.csv` creates one
  synthetic project QA record with `record_kind = 3`,
  `validation_included = 0`, and `sample_status = 3`.

The candidate-0.7 records are review-only and must be deleted from the live
project after QA. They do not alter sample membership and must not be reused as
formal declarations or formal assignments.

Candidate-0.7 live QA was completed on 22 July 2026. The synthetic and pilot
records were retained in the no-user `Pilot and QA archive` DAG rather than
treated as formal records. The authoritative result is
`../redcap_live_runtime_qa_20260722.md`; `audit/` contains the immutable archive
exports and the two-level source/live comparison. The comparison preserves 65
raw textual differences while verifying zero residual differences under its
three explicitly limited round-trip predicates.
