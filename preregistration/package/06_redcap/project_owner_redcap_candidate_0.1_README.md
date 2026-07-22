# Standalone Project Owner REDCap candidate

Version: `owner-redcap-candidate-0.1`  
Date: 2026-07-22  
Status: development review candidate; unfrozen; not imported; synthetic live QA pending.

## Source and scope

This candidate implements the field-level design in
`project_owner_instrument_gap_audit.md`, the complete inherited-field inventory,
Validation Protocol v0.15 and the subsequently locked two-stage recruitment,
permission, withdrawal and binary-tag decisions. It does not change the
taxonomy, sampling, analysis estimands, exclusions, model outputs or frozen
scratch instrument.

The canonical generated dictionary is
`project_owner_redcap_data_dictionary_candidate_0.1.csv`:

- SHA-256: `e3b59478ff9e37a52964790340dc1a65daccb5381293a42883ed7eaf398c3114`
- size: 39,310 bytes
- Owner Contact Admin: 27 fields
- Owner Assignment Admin: 39 fields
- Project Owner Review: 86 fields
- total: 152 fields

The intended future synthetic-QA target is blank Development PID 9149,
`DEA Validation Study – Project Owner Review`. No connection or import has
occurred. PID 9149 is not a credential and is recorded only in setup/QA
documentation.

## Architecture

The dictionary is for one non-longitudinal Classic project. `record_type` is 1
Contact or 2 Assignment. One restricted contact record stores direct identifiers
and researcher-level recruitment/acknowledgement permission. Every owner-project
pair is a separate assignment record linked by pseudonymous `owner_id` and stable
DEA `source_record_id`. Project Owner Review is the only survey. It uses one
record-specific link per assignment after an explicit link-release gate confirms
affirmative expression of interest.

No repeating instruments, longitudinal events, respondent accounts, respondent
DAGs, shared public survey link or direct identifiers on assignment records are
used. REDCap has no foreign-key constraint across records; the offline validator
enforces the contact-to-assignment relationship.

## Locked implementation decisions

- Initial contact is expression of interest only and contains no survey link.
- Named acknowledgement is optional, researcher-level and stored once on the
  contact record with preferred name/affiliation plus permission date/source.
- Participation and response-level anonymised quotation permission are separate.
- Both Applied and Not applied model statuses are reviewed for both binary tags.
- Withdrawal date, study email, dashboard URL and estimated time remain explicit
  double-braced configuration placeholders pending approved live setup.
- Owner answers are project-informed validation evidence, not a gold standard.

## Generated and supporting artefacts

- `scripts/build_project_owner_redcap_candidate.py`: deterministic offline builder.
- `scripts/validate_project_owner_redcap_candidate.py`: offline structure,
  privacy, linkage, fixture and analytical-completion validator.
- `project_owner_redcap_field_specification_candidate_0.1.csv`: row-level field,
  visibility, export and provenance map.
- `project_owner_redcap_branching_specification_candidate_0.1.yaml`: machine-readable
  record guards, label mapping, permissions and completion rules.
- `project_owner_redcap_expected_export_candidate_0.1.csv`: contact exclusion and
  analytical-export specification, including generated status/timestamp fields.
- `live_qa/project_owner_synthetic_import_candidate_0.1.csv`: synthetic import fixture;
  SHA-256 `bbf7dfbea83362c395bcc4525bf7d3d6d0d559938ba8bd32044444f76537856b`.
- `tests/fixtures/project_owner_candidate_0_1_synthetic_submissions.yaml`: synthetic
  contact, assignment and response cases; SHA-256
  `9eeb8915dabce74a2f894f361fdb7106e5763d4e0debc54385f550bd6a8e584e`.
- `project_owner_recruitment_materials_candidate_0.1.md`: two-stage recruitment,
  survey and permission wording templates.
- `project_owner_live_qa_plan_candidate_0.1.md`: future admin/respondent live-QA
  matrix and freeze gate.

The synthetic fixtures use fictional people, `.invalid` email addresses,
synthetic titles and non-DEA Record IDs. They are not a sample, recruitment
cohort, formal assignment or collected response.

## Completion and export

`owner_analytical_complete` is a documented deterministic export derivation:
affirmative `po_ack`; every populated proposed-domain and proposed-purpose
verdict; both tag-correctness responses; and public-entry sufficiency. REDCap's
generated form status and survey/audit timestamp supply administrative
completion evidence. Quote permission, optional comments and hidden unused
slots do not determine analytical completion.

The ordinary analytical export filters assignment records and excludes every
contact-only field. A separate restricted contact export contains the direct
identifier crosswalk. Free-text response fields remain restricted qualitative
evidence.

## Remaining gates

Before registration, candidate 0.1 must be imported into blank Development PID
9149 using synthetic records only, pass the complete live-QA plan, undergo a
narrow source/live comparison, have synthetic records archived or deleted, and
be explicitly frozen with archived evidence. No real contact, invitation,
assignment or formal data collection is authorised.
