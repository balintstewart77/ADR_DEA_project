# REDCap project setup checklist — candidate 0.7

Candidate-0.7 completion is recorded in `redcap_live_runtime_qa_20260722.md`.
The boxes below remain the reusable setup-control template rather than a second
authoritative completion log.

- [ ] Complete, export and archive all candidate-0.3 pilot responses before
      changing the live project.
- [ ] Preserve pilot assignment IDs, survey links, DAG mappings and
      instrument_ver = redcap-candidate-0.3.
- [ ] Record the candidate-0.3 export hash and access-controlled archive path.
- [ ] Confirm candidate 0.6 is documented as an imported intermediate candidate
      superseded before final runtime QA and that it collected no formal data.
- [ ] Import candidate-0.7 only after repository validation and protocol gates pass.
- [ ] Record the actual REDCap version and candidate-0.7 dictionary hash.
- [ ] Record every import warning; confirm four-form order and 150 fields.
- [ ] Keep assignment_admin non-survey, hidden and read-only.
- [ ] Confirm `record_kind` is hidden/read-only and uses 1 Project assignment,
      2 Coder declaration and 3 Synthetic QA; blank remains historical only.
- [ ] Confirm reviewer rights deny exports, API, administration and other
      records as applicable.
- [ ] Use only the excluded declaration and project synthetic fixtures for
      candidate-0.7 runtime QA; do not create formal records.
- [ ] Execute every candidate-0.7 branch, response-code and field-note test in the QA
      checklist and blank runtime template.
- [ ] Confirm one declaration record per coder precedes formal coding, and use
      REDCap's audit trail/form-completion timestamp rather than a manual date.
- [ ] Confirm scratch content is hidden on declaration records and visible on
      formal, synthetic-QA and blank historical records.
- [ ] Confirm one assignment per export row and hidden project clustering.
- [ ] Move pilot and synthetic QA records to the no-user archive DAG after QA;
      do not treat them as formal records.
- [ ] Do not sample, import formal assignments or begin formal coding until
      preregistration is final. Candidate-0.7 runtime QA and instrument freeze
      are complete.
- [ ] Store no API token, live URL, project identifier or contact file in Git.
