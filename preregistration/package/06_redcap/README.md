# REDCap instruments

This folder contains the frozen redcap-candidate-0.7 scratch instrument source
and its historical combined owner form, plus the separate unfrozen standalone
Project Owner development candidates. Candidate 0.7 remains the frozen
scratch-coder version; its historical `project_owner` form was never
independently live-QA tested for the standalone owner workflow.

`owner-redcap-candidate-0.3` is the current separate 97-field, two-instrument
Classic project candidate. It uses one pseudonymous record per owner, a
non-repeating Owner Consent survey, and a repeating Project Review survey with
one administrator-created instance per owner–project assignment. One
participant-specific Survey Queue link gives each owner access to their
pre-created reviews. Direct identifiers and recruitment/contact administration
are absent from the research project. The canonical specification is
`project_owner_redcap_candidate_0.3_spec.md`, and the project-level manual setup
is `project_owner_redcap_candidate_0.3_live_configuration.md`.

Candidate 0.3 is intended for controlled synthetic-only live QA in Development
PID 9149. It has not been imported, live tested or frozen and does not authorise
real contacts, invitations, assignments or data collection. The instrument is
technically ready for that controlled synthetic import. All 22 owner-facing
taxonomy microdefinitions and participant-reference definitions were approved
by Balint Stewart on 2026-07-23. Taxonomy wording is approved for participant
use. The participant taxonomy-reference Markdown contains only participant
content plus its document version/date; definition provenance and approval
metadata remain in the display YAML, review CSV, specification and manifest.
The reference and Project Review introduction state that Research Domains may
be multi-label and are unranked, while Analytical Purposes may also be
multi-label but are limited to two main analytical aims. Four expanded
participant-reference definitions (Data Infrastructure & Methodology, Outcome
Tracking, and both cross-cutting tags) are explicitly recorded as frozen
definitions plus imported inclusion/exclusion boundary clauses with exact
taxonomy source fields and paths; the other 18 remain verbatim after whitespace
normalisation.
Live QA and coordinated Participant Information, Questionnaire,
invitation, protocol, ethics and governance alignment remain required before
recruitment.

`owner-redcap-candidate-0.2` remains byte-for-byte unchanged as an unfrozen,
never-imported historical candidate. Its four-instrument contact/assignment
architecture was superseded before recruitment by candidate 0.3.

`owner-redcap-candidate-0.1` remains unchanged as an unfrozen, never-imported
historical candidate. It used a per-assignment participation acknowledgement
and was superseded by candidate 0.2 before live QA.

The existing participant-facing Word files remain unchanged and are not yet
aligned to candidate 0.3. Participant-facing version identifiers are separate
from the REDCap candidate:
`project-owner-information-v1` identifies Project Owner Participant
Information and Consent — Version 1, while
`project-owner-review-questionnaire-v1` identifies Project Owner Review
Questionnaire — Version 1. The Word files are retained byte-for-byte under
`participant_materials/`; candidate 0.3 uses an explicit pending-approval
participant-information token until the later coordinated alignment task.

Candidate 0.7 passed repository validation and completed live REDCap QA on 22
July 2026. It is frozen for preregistration and subsequent formal scratch
coding, but it has not been populated with formal validation assignments and
does not authorise sampling or import before preregistration is final. The
authoritative completed QA record is `redcap_live_runtime_qa_20260722.md`; its
source-to-live audit records 65 textual round-trip differences and zero
residual semantic differences under three narrow, enumerated transformations.

The excluded pilot was launched under redcap-candidate-0.3. Existing pilot
assignment imports and instrument_ver values remain candidate 0.3; collected
pilot responses are not recoded or regenerated. The branching specification
retains the complete candidate-0.3 response mapping for decode-only historical
use. The historical `sc_blind_decl` field and its response codes are unchanged;
it is displayed only where `instrument_ver = redcap-candidate-0.3` and is hidden
for candidate-0.7 project assignments.

Candidate 0.4 made two diagnostic-instrument changes that candidate 0.7 retains:

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
Candidate 0.3 pilot responses remain unchanged.

Candidate 0.6 added point-of-use help to `sc_taxonomy_fit`, distinguishing an
evidence limitation from a genuine taxonomy-fit problem. It does not alter the
field's options, codes, type, position, required status, branching, validation,
or export mapping. `Cannot assess from register entry` records an inability to
judge taxonomy fit from insufficient visible evidence. It is distinct from
`Partial Fit` or `No Fit`, which indicate a genuine taxonomy limitation for a
sufficiently understood project. Candidate 0.5 remains the historical
predecessor. Candidate 0.6 was imported into the live scratch project and
partially inspected, then superseded before final runtime QA by candidate 0.7.
It collected no formal data and was never frozen or authorised for formal
coding. The retained live snapshot and synthetic candidate-0.6 fixture are
historical evidence of that intermediate test.

Candidate 0.7 makes the permitted-material declaration a one-time coder-level
governance control. `record_kind` distinguishes formal project assignments (1),
one declaration record per coder (2), and synthetic runtime-QA records (3); a
blank value is reserved for historical candidate-0.3 records. `record_kind`
does not change scientific sample membership. The declaration uses REDCap's
audit trail and form-completion timestamp rather than a manually entered date.

Every candidate-0.7 coder–project assignment asks whether the coder had
information beyond the permitted evidence. This includes prior project
involvement, professional or institutional familiarity, and accidental exposure
to reviewer or other prohibited information. A Yes response requires only the
source of exposure, not the substantive knowledge. The coder still completes
the classification using the visible permitted evidence. Flagged responses are
retained in the primary analysis and are not automatically missing or invalid.

The project-owner stream remains deliberately distinct: po_sufficiency assesses
the public entry, while po_taxonomy_fit assesses actual-project taxonomy fit
using owner knowledge and remains Fit / Partial Fit / No Fit.

Candidate 0.7 retains candidate 0.5's hidden owner recruitment-route, sequence-position,
invitation/checkpoint, disposition, supplementary-reason, and response-status
administration. It also records the 50-record target, 25-record minimum, 10
supplementary-invitation maximum, 42-day close, and absence of a fixed owner
reserve. Candidate 0.7 completed fresh live runtime QA and was frozen on 22
July 2026. This resolves the instrument gate only: Jo's final review,
preregistration completion, and all other preregistration gates remain. Formal
sampling and assignment import remain prohibited until preregistration is
final.

No coder-facing start pack currently exists in this repository. When created,
its instructions must explain that the declaration is completed once; the
exposure question is answered for every project; Yes does not mean the project
should be skipped; and the coder must still classify from the visible permitted
evidence. Screenshot-based taxonomy-fit guidance remains planned for that pack.

The deterministic builder and validator remain in scripts; synthetic fixtures
remain under tests/fixtures and contain no real Record ID. Candidate-0.7 import
fixtures under `live_qa/` are explicitly synthetic, review-only and excluded
from validation. The dated files under `live_snapshots/` and `live_qa/audit/`
are the deliberately retained read-only freeze evidence. No additional
completed response export, formal assignment, live survey link, project
credential, API token, personal information or contact file belongs here.
