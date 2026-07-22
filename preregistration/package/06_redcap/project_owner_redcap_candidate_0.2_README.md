# Standalone Project Owner REDCap candidate 0.2

Version: owner-redcap-candidate-0.2  
Date: 2026-07-22  
Status: development review candidate; unfrozen; not imported; live QA pending.

## Change from candidate 0.1

Candidate 0.1 collected a participation acknowledgement on every owner–project
review. Candidate 0.2 replaces that repeated acknowledgement with one informed,
affirmative, electronically recorded and versioned consent on each researcher's
contact record. This is proportionate for researchers reviewing several
projects.

One consent covers the separate reviews described in the participant
information. Every later review remains voluntary. A substantial change to
research activities or intended use sets a re-consent block before more links
can be released.

This implementation refinement is consistent with Protocol v0.15. It changes no
scientific design or substantive owner-review question and requires no protocol
amendment.

## Canonical dictionary

project_owner_redcap_data_dictionary_candidate_0.2.csv

- SHA-256: 8225aec9afaae533151fa66e484b7361d8292777e9398b5a722fdc58b1fd52ec
- size: 41,753 bytes
- Owner Contact Admin: 31
- Project Owner Consent: 12
- Owner Assignment Admin: 39
- Project Owner Review: 85
- total: 167

Candidate-0.1 SHA-256 remains
e3b59478ff9e37a52964790340dc1a65daccb5381293a42883ed7eaf398c3114.

## Record and consent model

The project remains Classic, non-longitudinal and non-repeating. Each researcher
has one restricted contact record; each owner–project pair has one assignment
record. Records join through pseudonymous owner_id.

Project Owner Consent is contact-only and Project Owner Review assignment-only.
They are the only surveys. Direct identifiers remain in Owner Contact Admin and
are absent from consent fields, assignment records and analytical exports.

pc_decision, pc_info_version, the REDCap-native consent timestamp,
oc_reconsent_required, oc_consent_withdrawal and oc_contact_suppression establish
current consent. oc_link_eligible deterministically requires affirmative
interest and current affirmative consent. Eligibility never sends a link.

Acknowledgement remains researcher-level; quotation permission remains
project-response-level.

## Separate version namespaces

- REDCap schema and workflow: owner-redcap-candidate-0.2
- Participant information and consent: project-owner-information-v1
- Readable review questionnaire: project-owner-review-questionnaire-v1

The instrument version remains stored in instrument_ver. The contact-record
pc_info_version stores the participant-information identifier and controls
current-consent eligibility. Questionnaire version is documented as export and
configuration provenance without adding a new response field.

## Exact field-level difference

- 65 fields retained byte-for-byte;
- 86 modified only for one-time consent;
- 16 added: 4 contact consent-admin and 12 consent-survey fields;
- po_ack removed;
- zero renamed.

The net change is 152 to 167 fields. All substantive review questions preserve
candidate-0.1 names, types, codes and required rules.

## Analytical completion

Completion requires current linked contact consent, all populated
domain/purpose verdicts, both tag-correctness items and public-entry
sufficiency. No repeated consent checkbox is used. Optional comments and
quotation permission do not affect completion.

## Status

The synthetic import fixture SHA-256 is
1a0c61835fca6866196905f274908dc2f333be699d25066dbf4e19cb1e7d5346.
The response fixture SHA-256 is
7afe706a04d8f9ad40a167a303e507f67276543d545bcd4e663ad17a4c339733.

PID 9149 is the intended future synthetic live-QA target only. No connection or
import occurred. No frozen owner dictionary exists.
