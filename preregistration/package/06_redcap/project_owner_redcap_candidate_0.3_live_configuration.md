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

   > <strong>Project Owner Review</strong><br>Please begin by completing <strong>Participant Information and Consent</strong> below. If you agree to take part, your available project reviews will then appear in this list. You may complete all, some or none, in any order. To pause an unfinished review, use <strong>Save & Return Later</strong> before leaving. You can return using the same personalised link. Please do not forward this link.

13. Configure the Project Review survey settings as required, without treating repository documentation as proof of the live state:
   - **Save & Return Later: enabled**;
   - **respondents may return without a separate Return Code: enabled**;
   - **modification of completed responses: disabled**;
   - **Automatically continue to next survey: disabled**;
   - **redirect URL: blank**;
   - **participant “Repeat the Survey” option: disabled**.
14. Security implication: possession of the personalised link permits access to an unfinished review. Participants are instructed not to forward it, and direct contact identifiers are not held in the REDCap response project. Verify the live behaviour; do not describe it as confirmed from repository artefacts.
15. Configure the Project Review completion text exactly or equivalently as: “Thank you for reviewing this project. Your response has been recorded under the reference [assignment_id]. Please return to your personalised project list to review another project or to finish.” Return the participant to the visible Survey Queue and do not auto-start another review.
16. Confirm the near-submission `po_final_warning` reminder reads: “You may request withdrawal of this submitted review before the deadline stated in the Participant Information Sheet by contacting the study team and quoting the Review reference shown above.” Do not add the all-reviews procedure to the repeat.
17. Do not use a public survey URL for recruitment. Use only the participant/record-specific Survey Queue URL, which must reopen the same owner queue after Save & Return Later has been selected.
18. After approval, replace `project-owner-information-pending-approval-candidate-0.3` with the approved participant-information version in controlled import data and attach/link the final approved PDF at `participant_info_link`.
19. After coordinated participant-document alignment, format and attach/link the final taxonomy-reference PDF at `po_taxonomy_ref`; the repository Markdown is the author-approved wording source.
20. Load only `live_qa/project_owner_synthetic_import_candidate_0.3.csv`. It contains three owner rows and 19 pre-created Project Review repeat rows across 90 importable columns; the three stored classification summaries are populated on every assignment, descriptive fields and unexpanded checkbox base variables are excluded, and participant explanation fields are blank.
21. Confirm `assignment_id` is displayed as the survey-read-only **Review reference**, contains no personal identifier, states its specific-withdrawal purpose near submission, and remains stable when repeat instances are reordered.
22. Confirm the specific-review withdrawal wording uses `[assignment_id]`; confirm the all-reviews wording requires no visible owner identifier. Configure no production deadline outside the approved Participant Information Sheet.
23. Test desktop and mobile, then export and verify row structure before any real recruitment.

## Required live-QA assertions

- OWNER_TEST_001 shows consent once and one labelled project instance.
- OWNER_TEST_002 shows consent once and three separately labelled instances.
- OWNER_TEST_003 remains usable with 15 separately labelled instances.
- The custom labels show `[assignment_id] — [project_title]`.
- Save & Return Later is enabled; an unfinished review is recoverable through the same owner-specific queue link only after the participant selects Save & Return Later before leaving.
- Return without a separate Return Code is enabled; completed-response modification and Automatically continue to next survey are disabled; redirect URL is blank.
- One, some, all or none of the reviews can be completed independently.
- Completing one review returns to the visible queue and does not auto-start another.
- Participants cannot create an extra repeat instance and never see a Repeat the Survey control.
- Intended-recipient No and consent No each stop as specified and suppress Project Review.
- Owner-level `ack_pref` appears once only; no acknowledgement field appears inside Project Review.
- `ack_pref` is optional and has no effect on Survey Queue access, submission or analytical completeness.
- Empty proposed-label slots are absent, and populated definitions plus separately triggered correctness/visibility explanations behave correctly.
- The classification overview follows the Review reference/public project information and precedes detailed judgements; it shows every populated Domain and Purpose once, without ranking, and both tags in fixed order with Applied/Not applied status. The three stored summaries remain survey-hidden and participant-read-only through the overview.
- Both canonical tag blocks appear on every repeat, including Not applied statuses; each has required correctness, preserved four-level visibility, a required explanation only for No and an optional explanation for non-clear visibility, and neither branches on status.
- Both tag visibility questions use “Is the basis for this tag status visible in the public project title and datasets listed above?” with the unchanged four-level response scale.
- Missing menus contain 11 domains, seven purposes and two tags with definitions; no menu contains `Unclear from Register Entry`.
- Missing checkbox menus appear only for Yes, are required when shown, and enforce at least one selection; Unsure does not reveal a required menu. Treat at-least-one behaviour as a live-QA assertion.
- The missing-purpose guidance appears directly before its menu; `@MAXCHECKED=2` limits that menu to two selections. Confirm the action tag live, and verify analysis flags fitted-proposal-plus-missing selections above two as a cardinality/taxonomy issue.
- The missing-tag gateway functions as a summary cross-check after both primary per-tag correctness judgements and is not presented as a replacement assessment.
- The required project-knowledge gateway appears once; its optional note appears for Yes or Unsure and asks only for general-level context.
- In every domain, purpose and tag block, explicit disagreement reveals its required correctness explanation; Unsure reveals no correctness explanation; Partly visible/Not visible/Unsure reveals an optional visibility explanation; Fits/Yes plus Clearly visible reveals neither.
- The repeated sentence “Do not provide confidential or non-public information.” is absent from participant-visible field labels and notes; the central warnings in `po_privacy` and `po_final_warning` remain visible.
- `po_suff_explain` appears only as optional enrichment for Partial or Insufficient `po_sufficiency` and is not controlled by any proposed-classification fit, correctness or visibility response.
- Changing a parent response hides its former child field without necessarily deleting the stored value. Live QA must verify the display transition; analysis preserves the raw value but ignores it under the final inapplicable state.
- Does not fit/No cannot be submitted without the corresponding correctness explanation; Unsure shows no correctness-explanation textbox.
- Non-clear visibility can be submitted with its optional explanation blank.
- Missing-label Yes requires at least one selected label but not prose.
- Partial/Insufficient sufficiency can be submitted with `po_suff_explain` blank.
- Project-knowledge Yes/Unsure can be submitted with `po_nonpublic_note` blank.
- Partial Fit/No Fit requires at least one `po_tax_issue` selection but not `po_tax_explain`.
- Exercise final-state transitions: Does not fit→Unsure, missing-label Yes→No/Unsure, Partial/No Fit→Fit, non-clear→Clearly visible and project-knowledge Yes/Unsure→No. Confirm hidden values do not enter completion or derived analysis variables.
- Confirm blank optional prose is treated as not provided, never as a structured negative response.
- Live REDCap Required Field behaviour and the offline analytical-completion derivation agree; repository metadata is not proof that these runtime checks passed.
- `assignment_id` is visible as Review reference near project information, is included in completion and specific-withdrawal wording, and the REDCap repeat-instance number is not the sole participant reference.
- The short specific-review withdrawal reminder appears in `po_final_warning` after quotation permission and before submission, is absent from `po_intro`, and refers to the Participant Information Sheet and the Review reference.
- An untouched pre-created assignment exports as a row with `redcap_repeat_instrument = project_review`, its numbered instance and incomplete status.
- Each repeat exports separately; owner consent remains on the non-repeating owner row and is blank on repeated rows.
- The analysis test join by `owner_id` supplies consent to repeated reviews; no direct repeated-row consent filter is used.
- Export preparation distinguishes offered, untouched, partial, analytically complete and submitted; a submitted row is not accepted as analytically complete unless every condition in the specification is met.
- PID 9149 contains no participant name, email, affiliation, organisation/contact field, public recruitment URL, real record or real response.

## Required live migration after repository validation

Do not perform these actions from the repository task. In PID 9149 an authorised administrator must:

1. delete the disposable synthetic records;
2. re-import the regenerated candidate-0.3 dictionary;
3. confirm that `project_review` remains the repeating instrument;
4. confirm the custom repeat-instance label `[assignment_id] — [project_title]`;
5. verify Survey Queue conditions and both Stop Actions;
6. enable and verify Save & Return Later;
7. enable return without a separate Return Code;
8. confirm completed-response modification remains disabled;
9. import the regenerated synthetic fixture;
10. rerun the affected desktop/mobile, queue, overview, branching, final-state transition and return-flow live-QA tests;
11. export and verify all 19 offered assignment rows, their stored summaries and the separation of raw retained values from final-applicable analysis values.

## Evidence and exit gate

Archive the post-import live dictionary, configuration screenshots/notes, desktop/mobile results, synthetic export and a source/live comparison without credentials or live links. Candidate 0.3 remains unfrozen until every assertion passes and residual differences are resolved or explicitly approved. It is technically ready for controlled synthetic import and all 22 taxonomy definitions are author-approved. Recruitment remains blocked until live QA and later participant-document, invitation, protocol, ethics and governance alignment are complete.
