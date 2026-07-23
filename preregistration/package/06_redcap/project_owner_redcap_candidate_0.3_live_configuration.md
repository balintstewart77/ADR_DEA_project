# Project Owner REDCap candidate 0.3 — PID 9149 live configuration

Version: owner-redcap-candidate-0.3  
Candidate source commit: `69cf6665b845428fa2abd855c0445ae20589579f`
Status: manual controlled-import checklist; unfrozen; live QA pending.  
Target: UCL REDCap PID 9149, “DEA Validation Study – Project Owner Review”.

The REDCap CSV cannot encode project mode, repeating-instrument settings, Survey Queue behaviour, Survey Stop Actions, survey completion routing, uploaded files or participant-specific invitations. Treat every item below as a required admin action or live-QA assertion.

## Controlled setup

1. Verify PID 9149 is blank, in Development, and contains no real records.
2. Import `project_owner_redcap_data_dictionary_candidate_0.3.csv`.
3. Confirm Classic/non-longitudinal mode and `owner_id` as the first/record-ID field. Do not enable auto-numbering.
4. Confirm exactly two instruments in this order: Owner Consent (`owner_consent`) and Project Review (`project_review`).
5. Enable both instruments as surveys.
6. Configure Project Review as the **only** repeating instrument.
7. Set its repeating-instance custom label exactly to `[assignment_id] — [project_title]`.
8. Keep **Repeat the Survey disabled**. Participants must not be able to create blank instances; administrators pre-create every assignment instance.
9. Keep the Survey Queue visible and configure:
   - Owner Consent active;
   - condition `[owner_id] <> ''`;
   - Auto Start enabled;
   - Project Review active;
   - condition `[owner_consent_complete] = '2' and [owner_consent] = '1' and [intended_recipient] = '1'`;
   - Project Review Auto Start disabled.
10. Configure a Survey Stop Action for `intended_recipient = No`. Expected behaviour: show the wrong-recipient stop text, end the survey, show no consent/acknowledgement questions and no Project Review queue entries. Do not infer or claim automatic deletion, retention or reminder-suppression behaviour.
11. Configure a Survey Stop Action for `owner_consent = No`. Expected behaviour: show the decline text, end the survey, collect no `ack_pref` and show no Project Review queue entries. Do not infer or claim automatic deletion, retention or reminder-suppression behaviour.
12. Add this concise queue-top text:

   > You may review the listed projects in any order and may complete all, some or none. Progress is saved, and this personalised link returns you to the same queue. Short definitions appear inside each review and an optional taxonomy reference is available. Please do not forward this personalised link.

13. Configure the Project Review completion text exactly or equivalently as: “Thank you for reviewing this project. Your response has been recorded under the reference [assignment_id]. Please return to your personalised project list to review another project or to finish.” Return the participant to the visible Survey Queue and do not auto-start another review.
14. Do not use a public survey URL for recruitment. Use only the participant/record-specific Survey Queue URL, which must reopen the same owner queue and preserve progress.
15. After approval, replace `project-owner-information-pending-approval-candidate-0.3` with the approved participant-information version in controlled import data and attach/link the final approved PDF at `participant_info_link`.
16. After coordinated participant-document alignment, format and attach/link the final taxonomy-reference PDF at `po_taxonomy_ref`; the repository Markdown is the author-approved wording source.
17. Load only `live_qa/project_owner_synthetic_import_candidate_0.3.csv`. It contains three owner rows and 19 pre-created Project Review repeat rows across 80 importable columns; descriptive fields and unexpanded checkbox base variables are excluded.
18. Confirm `assignment_id` is displayed as the survey-read-only **Review reference**, contains no personal identifier, and remains stable when repeat instances are reordered.
19. Confirm the specific-review withdrawal wording uses `[assignment_id]`; confirm the all-reviews wording requires no visible owner identifier. Configure no production deadline outside the approved Participant Information Sheet.
20. Test desktop and mobile, then export and verify row structure before any real recruitment.

## Required live-QA assertions

- OWNER_TEST_001 shows consent once and one labelled project instance.
- OWNER_TEST_002 shows consent once and three separately labelled instances.
- OWNER_TEST_003 remains usable with 15 separately labelled instances.
- The custom labels show `[assignment_id] — [project_title]`.
- The same owner-specific queue link reopens the queue and preserves saved progress.
- One, some, all or none of the reviews can be completed independently.
- Completing one review returns to the visible queue and does not auto-start another.
- Participants cannot create an extra repeat instance and never see a Repeat the Survey control.
- Intended-recipient No and consent No each stop as specified and suppress Project Review.
- Owner-level `ack_pref` appears once only; no acknowledgement field appears inside Project Review.
- `ack_pref` is optional and has no effect on Survey Queue access, submission or analytical completeness.
- Empty proposed-label slots are absent, and populated definitions/conditional basis fields behave correctly.
- Both canonical tag blocks appear on every repeat, including Not applied statuses; each has required correctness and preserved four-level visibility, and neither branches on status.
- Missing menus contain 11 domains, seven purposes and two tags with definitions; no menu contains `Unclear from Register Entry`.
- Missing checkbox menus appear only for Yes, are required when shown, and enforce at least one selection; Unsure does not reveal a required menu. Treat at-least-one behaviour as a live-QA assertion.
- The missing-purpose guidance appears directly before its menu; `@MAXCHECKED=2` limits that menu to two selections. Confirm the action tag live, and verify analysis flags fitted-proposal-plus-missing selections above two as a cardinality/taxonomy issue.
- The missing-tag gateway functions as a summary cross-check after both primary per-tag correctness judgements and is not presented as a replacement assessment.
- The required project-knowledge gateway appears once; its optional note appears for Yes or Unsure and warns against confidential or non-public detail.
- Domain/purpose and tag basis fields retain the four-level visibility triggers: Partly visible, Not visible or Unsure; Clearly visible alone does not reveal them.
- `assignment_id` is visible as Review reference near project information, is included in completion and specific-withdrawal wording, and the REDCap repeat-instance number is not the sole participant reference.
- An untouched pre-created assignment exports as a row with `redcap_repeat_instrument = project_review`, its numbered instance and incomplete status.
- Each repeat exports separately; owner consent remains on the non-repeating owner row and is blank on repeated rows.
- The analysis test join by `owner_id` supplies consent to repeated reviews; no direct repeated-row consent filter is used.
- Export preparation distinguishes offered, untouched, partial, analytically complete and submitted; a submitted row is not accepted as analytically complete unless every condition in the specification is met.
- PID 9149 contains no participant name, email, affiliation, organisation/contact field, public recruitment URL, real record or real response.

## Evidence and exit gate

Archive the post-import live dictionary, configuration screenshots/notes, desktop/mobile results, synthetic export and a source/live comparison without credentials or live links. Candidate 0.3 remains unfrozen until every assertion passes and residual differences are resolved or explicitly approved. It is technically ready for controlled synthetic import and all 22 taxonomy definitions are author-approved. Recruitment remains blocked until live QA and later participant-document, invitation, protocol, ethics and governance alignment are complete.
