# Synthetic live-QA import fixtures

This directory contains import-only synthetic records for live REDCap runtime
QA. It contains no formal coder declaration, sampled project assignment, real
Record ID, response export, live URL, project identifier, or credential.

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
