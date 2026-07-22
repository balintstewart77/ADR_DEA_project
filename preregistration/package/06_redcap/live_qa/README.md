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

Candidate-0.7 live QA was completed on 22 July 2026. The synthetic and pilot
records were retained in the no-user `Pilot and QA archive` DAG rather than
treated as formal records. The authoritative result is
`../redcap_live_runtime_qa_20260722.md`; `audit/` contains the immutable archive
exports and the two-level source/live comparison. The comparison preserves 65
raw textual differences while verifying zero residual differences under its
three explicitly limited round-trip predicates.
