# REDCap instruments

This folder contains the Phase 5 working candidate for one non-longitudinal
REDCap project with assignment_admin, scratch_coder, and project_owner
instruments. One reviewer-record assignment is one REDCap record and export
row. The current post-training version is redcap-candidate-0.4.

The excluded pilot was launched under redcap-candidate-0.3. Existing pilot
assignment imports and instrument_ver values remain candidate 0.3; collected
pilot responses are not recoded or regenerated. The branching specification
retains the complete candidate-0.3 response mapping for decode-only historical
use.

Candidate 0.4 makes two diagnostic-instrument changes:

- sc_taxonomy_fit adds stored code 4, Cannot assess from register entry.
  This records an evidence limitation and is coherent only with Partial or
  Insufficient register sufficiency.
- sc_tax_issue and po_tax_issue retain stored codes 1, 2 and 5, with revised
  labels. Codes 3, 4 and 6 are retired without reuse.

The project-owner stream remains deliberately distinct: po_sufficiency assesses
the public entry, while po_taxonomy_fit assesses actual-project taxonomy fit
using owner knowledge and remains Fit / Partial Fit / No Fit.

Candidate 0.4 is for formal coding only after all candidate-0.3 pilot responses
are complete, exported and archived; repository validation passes; and fresh
live runtime QA passes. Live candidate-0.4 QA is pending. The dated 16 July
runtime record is historical and does not establish candidate-0.4 readiness.

The deterministic builder and validator remain in scripts; synthetic fixtures
remain under tests/fixtures and contain no real Record ID. This folder must
never contain completed responses, response exports, formal assignments, live
survey links or project identifiers, API tokens, personal information, or
contacts.
