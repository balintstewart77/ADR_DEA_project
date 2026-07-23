# Standalone Project Owner REDCap version history

## owner-redcap-candidate-0.3 - 2026-07-23

- REDCAP-020 narrows each of the eight correctness-explanation branches to the
  explicit-disagreement code only, where the field remains required. The eight
  visibility explanations, three missing-label explanations, sufficiency
  explanation, project-knowledge note and taxonomy explanation are optional
  enrichment and do not determine analytical completion. Structured ratings,
  gateways, required missing-label selections and taxonomy issue types remain
  required. Questionnaire v3 and protocol candidate v0.17 document the same
  rule; v0.17 also closes DEV-001. The dictionary remains 108 fields and the
  pristine fixture remains 22 rows and 90 importable columns. PID 9149 requires
  controlled re-import and renewed live QA.

- REDCAP-019 removes the repeated sentence “Do not provide confidential or
  non-public information.” from 20 conditional per-question labels while
  retaining the central `po_privacy` and `po_final_warning` warnings. It also
  changes both tag visibility stems to “Is the basis for this tag status visible
  in the public project title and datasets listed above?” so the question matches
  the unchanged four-level scale. Field count, field order, choices, codes,
  branching, requiredness, fixture and analytical completion are unchanged.
  Those wording corrections are now carried into versioned Questionnaire v3
  and protocol candidate v0.17 under REDCAP-020; v2 and v0.16 remain archived.
- REDCAP-018 adds one participant-visible classification overview and three
  survey-hidden deterministic summary fields. The overview shows every proposed
  Domain and Purpose and both tag statuses without ranking, definitions or an
  overall correctness question. It also corrects Save & Return Later guidance,
  documents the required survey settings and security implication, isolates
  `po_suff_explain` to Partial/Insufficient public-entry sufficiency, places a
  concise withdrawal reminder near submission and aligns the Domain-cardinality
  sentence in the unfrozen taxonomy reference. The dictionary is now 108 fields
  and the import fixture 90 columns; PID 9149 must be re-imported and retested.
- Documentation alignment for ethics/DPO submission created Participant
  Information and Consent v2, Project Owner Review Questionnaire v2 and protocol
  candidate v0.16. These replace stale separate-link and record-per-assignment
  descriptions with one personalised Survey Queue link, consent once and
  pre-created repeating reviews. The invitation email is unchanged. This is a
  documentation correction only: participant population, substantive study
  purpose, owner sampling design, scratch sampling design and candidate-0.3
  REDCap fields are unchanged; controlled live QA remains incomplete.
- Current two-instrument development candidate: Owner Consent (11) and
  Project Review (97), totalling 108 dictionary fields.
- Substantially changes the record architecture before recruitment: one
  pseudonymous `owner_id` record per owner, one non-repeating consent survey,
  and one pre-created repeating Project Review instance per owner–project
  assignment.
- Uses one participant-specific Survey Queue link per owner. Project Review is
  the only repeating instrument, its custom label is
  `[assignment_id] — [project_title]`, Auto Start is disabled, and participants
  must not be allowed to create additional instances.
- Removes direct identifiers and all recruitment/contact administration from
  the research project. Those data remain in a separately restricted layer
  keyed by `owner_id`.
- Collects `ack_pref` once at owner level without collecting an
  acknowledgement name or affiliation; quotation permission remains
  review-instance-specific.
- Records one affirmative Yes/No consent decision after intended-recipient
  confirmation, branches wrong-recipient and consent-decline messages
  independently, and keeps optional acknowledgement outside consent and Survey
  Queue access.
- Preserves the four-level public-entry visibility scale (Clearly visible,
  Partly visible, Not visible, Unsure) for all four domain, two purpose and two
  tag reviews. Live-QA correction REDCAP-016 replaces each combined basis field
  with separate required correctness and public-visibility explanations.
- Presents both canonical cross-cutting tags on every assignment with an
  Applied/Not applied proposed status, correctness, visibility and separate
  conditional explanations; the missing-tag item is retained as a documented
  summary cross-check.
- Aligns the existing `po_nonpublic`/`po_nonpublic_note` pair to the explicit
  project-knowledge gateway and optional non-public-context warning.
- Documents offered, untouched, partial, analytically complete and submitted
  assignment-response states; submission status alone is not analytical
  completeness.
- Displays stable `assignment_id` as the neutral Review reference and uses it
  in completion and specific-response withdrawal instructions.
- Recalculates frozen production maxima as four domains, two purposes and two
  cross-cutting tags, and fails offline validation if display capacity is
  lower.
- Adds a single traced owner-facing taxonomy source with 11 substantive
  domains, seven purposes and two tags in missing-label menus, plus distinct
  proposed-only Domain and Purpose `Unclear from Register Entry` definitions.
  The layer-qualified display key prevents their duplicate label text from
  collapsing and excludes the removed linkage-layer entry.
- Expands the human-review table to 22 rows (12/8/2), leaves ordinary ambiguity
  fields blank and provides targeted review prompts for the data-infrastructure
  domain, Outcome Tracking/Policy Evaluation boundary and
  demographic-disparities tag.
- Records the final owner-facing taxonomy-display pass approved by Balint
  Stewart on 2026-07-23: 22 `approved_by_author`, zero pending and zero requiring
  revision. The display source now separates immutable `source_definition`,
  compact `owner_microdefinition` and participant-reference
  `owner_reference_definition`; inline REDCap uses the microdefinition and the
  Markdown reference uses the reference definition.
- Strengthens the participant-reference definitions for Data Infrastructure &
  Methodology, Outcome Tracking and both cross-cutting tags with imported
  inclusion/exclusion boundary clauses while leaving all approved inline
  microdefinitions unchanged. Their wording origin is recorded as frozen
  definition plus imported clause, with exact authoritative taxonomy source
  fields, paths and text; the other 18 reference definitions are verified
  verbatim after whitespace normalisation. The
  participant Markdown adds explanatory framing for the two Unclear entries
  and removes repository filenames, build/review status and audit footers;
  technical traceability remains outside participant-visible content.
- Clarifies in both the participant reference and Project Review introduction
  that multiple Research Domains may validly apply and are judged independently
  without ranking. The participant reference separately retains the maximum of
  two Analytical Purposes and states that more than one may describe the main
  analytical aims. Its usage guidance now prepares participants to judge both
  actual-project fit and public-entry visibility, and a framework-definition
  lead-in distinguishes the two traceable Unclear definitions from participant
  selection instructions. No response field was added.
- Corrects the first controlled-import compatibility issue reported by UCL
  REDCap: `public_register_url` remains a survey-read-only text field with its
  existing values and presentation, but its unsupported `url` Text Validation
  Type is now blank. Candidate validation now enforces the target instance's
  lower-case validation-type allow-list. No response code, field structure,
  participant-facing meaning or analytical rule changed.
- Corrects the subsequent PID 9149 synthetic Data Import Tool rejection caused
  by non-storage columns. At that correction the 80-column fixture excluded all
  descriptive fields and the four unexpanded checkbox base variables; it
  contained no expanded checkbox columns because the pristine QA fixture
  pre-populates no participant checkbox responses. Assignment metadata,
  proposed labels, version/provenance values, repeat instrument/instance
  values, three owners, 19 assignments and 22 rows were unchanged. The
  then-97-field REDCap dictionary was byte-identical to the pre-correction
  dictionary; REDCAP-016 later regenerated the importable schema to 87 columns
  alongside the permitted 104-field instrument correction.
- Removes the internal administrative `intended_recipient` field note exposed
  during synthetic live QA. The note is now blank; the field label, Yes/No
  choices, requiredness, instrument placement, wrong-recipient branch, manual
  Stop Action and Project Review Survey Queue condition are unchanged. The
  deliberate participant-information and taxonomy-reference attachment
  placeholders remain pending final document configuration.
- Corrects four linked participant-facing defects identified in continuing
  synthetic live QA. The Project Review opening now gives concise Domain,
  Purpose and tag guidance without repeating withdrawal arrangements; privacy
  and non-production reference placeholders remain separate semantic-HTML
  blocks. A 17-row formatting audit verifies balanced minimal HTML and no
  wholly bold descriptive block. The redundant `po_tax_other` textbox is
  removed, while `po_tax_explain` covers all Partial/No Fit issue types.
  Across all eight proposed-classification blocks, each former combined
  `*_basis` field is replaced by a correctness explanation immediately after
  the fit/correctness item and a visibility explanation immediately after the
  four-level visibility item. This changes Project Review from 86 to 93 fields
  and requires dictionary re-import before continued PID 9149 live QA.
- Adds participant guidance beside the missing-purpose menu and uses the
  repository-validated `@MAXCHECKED=2` action tag. Analysis derives the implied
  corrected-purpose count and treats counts above two as a cardinality/taxonomy
  issue rather than a directly comparable corrected classification.
- Adds a 22-row long-format synthetic fixture for three owners and 19
  pre-created assignments (1, 3 and 15 projects).
- Supersedes candidate 0.2 as the current development candidate. Candidate 0.2
  remains byte-for-byte unchanged and retains its provenance as an unfrozen,
  never-imported historical candidate.
- This is a substantial instrument architecture change made before recruitment
  and before final participant-document, protocol and ethics alignment.
- Status: unfrozen development candidate; no REDCap connection or import;
  technically ready for controlled synthetic import into Development PID 9149
  and taxonomy wording approved for participant use. Live QA and coordinated
  participant-document, invitation, protocol, ethics and governance alignment
  remain pending before recruitment.

## owner-redcap-candidate-0.2 - 2026-07-22

- Follow-up documentation correction after the initial candidate-0.2 commit:
  the participant-information identifier changes from owner-information-0.2 to
  project-owner-information-v1, and the readable questionnaire is identified
  separately as project-owner-review-questionnaire-v1. The REDCap instrument
  remains owner-redcap-candidate-0.2. No survey question, consent requirement,
  branching rule, response code or scientific design changed. The correction
  creates distinct, auditable instrument and participant-document namespaces.
- Current four-instrument development candidate: Owner Contact Admin (31),
  Project Owner Consent (12), Owner Assignment Admin (39), and Project Owner
  Review (85), totalling 167 fields.
- Supersedes candidate 0.1 before any live import or data collection.
- Obtains affirmative, electronic and versioned informed consent once on each
  researcher contact record before project-review links are released.
- Removes the per-assignment po_ack field; later reviews instead display a brief
  reminder that each review remains voluntary.
- Missing, declined, withdrawn or stale consent blocks assignment-link release.
  Substantial changes to research activities or intended use require re-consent.
- Preserves separate researcher-level acknowledgement and response-level
  quotation permission.
- This proportional implementation refinement changes no substantive review
  question or scientific design and is compatible with Protocol v0.15.
- Status: unfrozen development candidate; not imported; synthetic live QA,
  source/live comparison, evidence archive and explicit freeze remain pending.

## owner-redcap-candidate-0.1 - 2026-07-22

- Superseded historical development candidate; unfrozen and never imported.
- Candidate 0.1 collected participation acknowledgement per owner–project
  assignment and was superseded by candidate 0.2 before live QA.
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
