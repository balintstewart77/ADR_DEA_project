# REDCap instruments

This folder contains the Phase 5 working candidate for one non-longitudinal
REDCap project with assignment_admin, scratch_coder, and project_owner
instruments. One reviewer-record assignment is one REDCap record and export
row. The current formal-instrument repository version is redcap-candidate-0.6.

The excluded pilot was launched under redcap-candidate-0.3. Existing pilot
assignment imports and instrument_ver values remain candidate 0.3; collected
pilot responses are not recoded or regenerated. The branching specification
retains the complete candidate-0.3 response mapping for decode-only historical
use.

Candidate 0.4 made two diagnostic-instrument changes that candidate 0.6 retains:

- sc_taxonomy_fit adds stored code 4, Cannot assess from register entry.
  This records an evidence limitation and is coherent only with Partial or
  Insufficient register sufficiency.
- sc_tax_issue and po_tax_issue retain stored codes 1, 2 and 5, with revised
  labels. Codes 3, 4 and 6 are retired without reuse.

Post-pilot shared calibration did not alter these fields or the substantive
classification rules. The calibration note and request for any remaining
comments on wording, branching, required notes, conditional fields and
technical usability were circulated simultaneously to all three scratch coders
on 21 July 2026, ahead of the stated 22 July deadline. All three responded. No
additional substantive taxonomy or instrument concerns were raised; one coder
requested clearer operational guidance for `Cannot assess from register entry`.
Candidate 0.3 pilot responses remain unchanged. Candidate 0.6 has passed offline
repository validation but is not frozen and has not passed fresh live runtime
QA.

Candidate 0.6 adds point-of-use help to `sc_taxonomy_fit`, distinguishing an
evidence limitation from a genuine taxonomy-fit problem. It does not alter the
field's options, codes, type, position, required status, branching, validation,
or export mapping. `Cannot assess from register entry` records an inability to
judge taxonomy fit from insufficient visible evidence. It is distinct from
`Partial Fit` or `No Fit`, which indicate a genuine taxonomy limitation for a
sufficiently understood project. Candidate 0.5 remains the historical
predecessor. Screenshot-based guidance remains planned for the coder start pack.

The project-owner stream remains deliberately distinct: po_sufficiency assesses
the public entry, while po_taxonomy_fit assesses actual-project taxonomy fit
using owner knowledge and remains Fit / Partial Fit / No Fit.

Candidate 0.6 retains candidate 0.5's hidden owner recruitment-route, sequence-position,
invitation/checkpoint, disposition, supplementary-reason, and response-status
administration. It also records the 50-record target, 25-record minimum, 10
supplementary-invitation maximum, 42-day close, and absence of a fixed owner
reserve. It remains provisional pending Jo's review, formal-instrument freeze,
and fresh live runtime QA. The dated 16 July runtime record is historical and
does not establish candidate-0.6 readiness.

The deterministic builder and validator remain in scripts; synthetic fixtures
remain under tests/fixtures and contain no real Record ID. This folder must
never contain completed responses, response exports, formal assignments, live
survey links or project identifiers, API tokens, personal information, or
contacts.
