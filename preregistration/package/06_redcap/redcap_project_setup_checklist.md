# REDCap project setup checklist — candidate 0.4

- [ ] Complete, export and archive all candidate-0.3 pilot responses before
      changing the live project.
- [ ] Preserve pilot assignment IDs, survey links, DAG mappings and
      instrument_ver = redcap-candidate-0.3.
- [ ] Record the candidate-0.3 export hash and access-controlled archive path.
- [ ] Import candidate-0.5 only after repository validation and protocol gates pass.
- [ ] Record the actual REDCap version and candidate-0.5 dictionary hash.
- [ ] Record every import warning; confirm form order and 137 fields.
- [ ] Keep assignment_admin non-survey, hidden and read-only.
- [ ] Confirm reviewer rights deny exports, API, administration and other
      records as applicable.
- [ ] Use only synthetic new records for candidate-0.5 runtime QA.
- [ ] Execute every candidate-0.5 branch and response-code test in the QA
      checklist and blank runtime template.
- [ ] Confirm one assignment per export row and hidden project clustering.
- [ ] Delete candidate-0.5 synthetic records after QA.
- [ ] Do not begin formal coding until candidate-0.5 runtime QA is signed off.
- [ ] Store no API token, live URL, project identifier or contact file in Git.
