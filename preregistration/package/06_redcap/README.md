# REDCap instruments

This folder contains the frozen redcap-candidate-0.7 scratch instrument source
and its historical combined owner form, plus the separate unfrozen standalone
Project Owner development candidates. Candidate 0.7 remains the frozen
scratch-coder version; its historical `project_owner` form was never
independently live-QA tested for the standalone owner workflow.

`owner-redcap-candidate-0.4` is the current separate 119-field, two-instrument
Classic project candidate. It uses one pseudonymous record per owner, a
non-repeating Owner Consent survey, and a repeating Project Review survey with
one administrator-created instance per owner–project assignment. One
participant-specific Survey Queue link gives each owner access to their
pre-created reviews. Direct identifiers and recruitment/contact administration
are absent from the research project. The canonical specification is
`project_owner_redcap_candidate_0.4_spec.md`, and the project-level controlled
migration/live-QA guide is
`project_owner_redcap_candidate_0.4_live_configuration.md`.

Candidate 0.4 aligns Owner Consent to Participant Information and Consent v3:
ten separately auditable owner-level confirmations, a deterministic
`consent_items_complete` flag, the retained final consent decision and a
Survey Queue gate requiring all four consent-validity conditions. It removes
the obsolete per-project quotation-permission question because quotation
agreement is now sought by email at point of use with the exact proposed
wording and context. It also corrects the optional acknowledgement wording.
Candidate 0.3 remains unchanged as the historical predecessor.

Candidate 0.4 also enforces the operational two-tag invariant without changing
the frozen taxonomy or production prompt: `Demographic disparities / equity
tag` and `COVID-19 & Pandemic`. Operational inclusion is controlled by
`include_in_prompt=true`, the current Cross-cutting tag layer and a status that
does not begin `removed`; lifecycle/provenance values such as `new v3.4` and
`active` are not the inclusion criterion. Each Project Review displays the full
two-sentence authoritative definition for both tags immediately before its
Applied / Not applied status and independent correctness and visibility
questions. The scoped audit is
`project_owner_cross_cutting_tag_and_quotation_audit_candidate_0.4.md`.

Candidate 0.4 removes the inherited participant-visible `po_taxonomy_ref`
synthetic-QA placeholder without replacement. No separate taxonomy-reference
PDF, attachment, external link, Appendix A link or optional guide will be used.
Project Review now places the concise, questionnaire-matched “How the
classifications work” orientation after the displayed project information and
immediately before the unchanged read-only classification overview. Eleven
boundary-bearing Q6b missing-Domain microdefinitions were explicitly approved
by the project author on 2026-07-28 and are generated from the canonical-label
`OWNER_DOMAIN_DISPLAY` mapping into the questionnaire and REDCap artefacts.
`project_owner_missing_domain_microdefinitions_candidate_0.4_review.md` records
the approval and implementation decision;
`project_owner_domain_wording_concordance_candidate_0.4.md` records the human
full-definition/compressed-wording comparison. The frozen taxonomy remains the
substantive authority and was not changed. Migration and recruitment remain
blocked pending controlled PID 9149 migration and successful live semantic and
display QA for all 11 Domains.

The orientation now makes the governing substantive-focus threshold explicit
before the classification overview and strongly emphasises only the phrase
“only when it is a substantive focus of the project’s research question or
analytical aims”. Display-only reminders immediately before Q6b and Q7b
respectively emphasise a substantive subject and a substantive analytical aim.
These two reminder fields account for the increase from 117 to 119 fields;
they change no choices, codes, branching, requiredness, exports or analytical
constructs. Their rich-text presentation remains a mandatory desktop/mobile
live-QA gate.

Candidate 0.4 is intended for controlled synthetic-only migration/live QA in Development
PID 9149. It has not been imported or live tested and does not authorise
real contacts, invitations, assignments or data collection. The instrument is
unfrozen and non-authoritative. Historical candidate 0.3 retained the 22
owner-facing microdefinitions approved by Balint Stewart on 2026-07-23 and its
separate taxonomy-reference Markdown source as audit evidence. Candidate 0.4
does not use that reference artefact or require a formatted derivative.
Continuing candidate-0.3 synthetic live QA produced a coordinated participant-facing and
branching correction: the review opening is concise and semantically formatted,
the duplicate taxonomy-fit textbox is removed, and all eight proposed-label
blocks now separate actual-project correctness explanations from public-entry
visibility explanations. REDCAP-018 adds a contextual read-only classification
overview backed by three survey-hidden deterministic summary fields, accurate
Save & Return Later instructions and required live survey settings, and a short
withdrawal reminder near submission. The generated formatting audit records
all 18 participant-visible descriptive fields. The revised dictionary and
90-column synthetic fixture must be re-imported before live QA continues.
REDCAP-019 subsequently removes 20 repeated per-question privacy sentences and
aligns both tag visibility stems to the unchanged four-level scale. The central
privacy warnings survive unchanged; field count and structure remain 108.
The Participant Information and Consent v3 is the authoritative source for the
ten candidate-0.4 confirmation statements. The canonical consent and Project
Owner Review Questionnaire v3 DOCX files are aligned to candidate 0.4 and pinned
by SHA-256 and byte size. The consent document uses the complete approved
acknowledgement wording and response labels. The questionnaire reproduces the
REDCap participant-facing labels, response choices and inline checkbox
microdefinitions, records the full valid owner-consent join in Appendix B, and
contains no Q13 or per-project quotation-permission question. The former
untracked `- Copy` questionnaire is not required. The current
REDCAP-020 semantic-hardening clarification preserves raw hidden values while
masking them from final-applicable derived analysis, treats blank optional prose
as not provided and calibrates owner signals as adjudication evidence rather than
a definitive error source. Archived
Questionnaire v2 and protocol v0.16 remain byte-identical. The invitation email was reviewed and retained
byte-for-byte. Controlled REDCap migration/live QA and ethics/governance approval
remain required before recruitment.

`owner-redcap-candidate-0.2` remains byte-for-byte unchanged as an unfrozen,
never-imported historical candidate. Its four-instrument contact/assignment
architecture was superseded before recruitment by candidate 0.3.

`owner-redcap-candidate-0.1` remains unchanged as an unfrozen, never-imported
historical candidate. It used a per-assignment participation acknowledgement
and was superseded by candidate 0.2 before live QA.

Participant-facing document versions remain separate from the REDCap candidate.
`Project_Owner_Participant_Information_and_Consent_v3.docx` and
`Project_Owner_Review_Questionnaire_v3.docx` are the current ethics/DPO review
copies. Their v1 predecessors remain byte-for-byte under
`participant_materials/`. Candidate 0.3 continues to use its explicit
pre-production participant-information token until the controlled live project
is configured and the approved final document version is entered.

Candidate 0.7 passed repository validation and completed live REDCap QA on 22
July 2026. It is frozen for preregistration and subsequent formal scratch
coding. A deterministic 675-row formal import was generated from the 225 active
records for review, but candidate 0.7 has not been populated with those
assignments and no REDCap import was performed. The
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
July 2026. This resolved the instrument gate only. Preregistration was later
approved and the single official sample draw completed. Formal assignments have
now been generated for review, but assignment import and coding remain separate
later actions and have not occurred.

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
completed response export, restricted formal assignment or import file, live
survey link, project credential, API token, personal information or contact
file belongs in this public package. The restricted assignment artefacts are
identified by aggregate provenance in the canonical receipt and manifest.
