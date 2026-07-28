# Project Owner candidate 0.4 authorised-administrator migration and live-QA checklist

Status: instructions only. Do not execute without separate authorisation. Candidate 0.4 is unfrozen, pre-recruitment and non-authoritative. Recruitment remains blocked until every item passes.

## Before migration

Document baseline: verify the canonical consent and questionnaire DOCX files match the SHA-256 and byte-size metadata embedded in the generator and branching specification. Confirm the consent wording, questionnaire labels/options and Appendix B against the generated dictionary before any live action. The former untracked `- Copy` questionnaire is not required.

1. Confirm PID 9149 is the Development project and contains no real participant, contact, consent or response records.
2. Confirm only disposable synthetic candidate-0.3 data exist.
3. Archive/export the candidate-0.3 live dictionary, synthetic data export, Survey Queue/repeating settings and QA evidence without credentials or live links.
4. Delete only the verified disposable synthetic records through the authorised REDCap administrator workflow.

## Controlled dictionary migration

5. Import `project_owner_redcap_data_dictionary_candidate_0.4.csv` through the controlled REDCap dictionary process and resolve every reported change before applying it.
6. Confirm exactly two instruments: non-repeating Owner Consent (`owner_consent`) and repeating Project Review (`project_review`).
7. Confirm `project_review` is the only repeating instrument, custom label `[assignment_id] — [project_title]`, participant-created repeats disabled and auto-start disabled.
8. Display or attach the full approved `Project_Owner_Participant_Information_and_Consent_v3` information sheet before `intended_recipient`.
9. Confirm all ten confirmation fields are owner-level, blank by default, not import-populated and hidden after intended-recipient No.
10. Confirm `consent_items_complete` uses exactly `if([consent_read_info] = '1' and [consent_understand_invitation] = '1' and [consent_voluntary] = '1' and [consent_no_nonpublic] = '1' and [consent_confidentiality_limits] = '1' and [consent_withdrawal_deadline] = '1' and [consent_quote_process] = '1' and [consent_retention_reanalysis] = '1' and [consent_complaints] = '1' and [consent_acknowledgement] = '1', 1, 0)` and is hidden/read-only to participants.
11. Configure the Project Review Survey Queue condition exactly as `[owner_consent_complete] = '2' and [owner_consent] = '1' and [intended_recipient] = '1' and [consent_items_complete] = '1'`. Do not include `ack_pref`.
12. Re-establish the existing Stop Action for `intended_recipient = No`: end the consent survey and reveal no consent items, acknowledgement or Project Reviews.
13. Re-establish the existing Stop Action for `owner_consent = No`: end the consent survey, collect no acknowledgement and reveal no Project Reviews.
14. Do not add an unverified action tag. Verify in the Online Designer that an attempted affirmative response with any confirmation blank or Not confirmed is not treated as valid participation and cannot reveal Project Reviews. If the target REDCap runtime cannot enforce this beyond the deterministic gate, stop migration approval and document the unresolved limitation before recruitment.

## Synthetic import and consent-path tests

15. Import `live_qa/project_owner_synthetic_import_candidate_0.4.csv`; verify three owner rows, 19 pre-created reviews and 22 total rows.
16. Verify no owner is imported with any consent confirmation, final consent, acknowledgement or all-confirmed value populated.
17. Test affirmative consent with all ten confirmations: calculated flag 1, final Yes, Owner Consent complete and Project Reviews visible.
18. Repeat the attempted affirmative test ten times, omitting or clearing one different confirmation each time: flag 0 and no Project Review visible.
19. Test active final No without all ten confirmations; verify the consent-decline Stop Action and no acknowledgement/reviews.
20. Test intended-recipient No; verify immediate termination and no downstream fields/reviews.
21. Verify `ack_pref` appears only after intended-recipient Yes, all-confirmed 1 and final consent Yes; verify it remains optional and does not affect queue eligibility or analytical completion.
22. Clear a previously confirmed item before final submission; verify the flag returns to 0 and Project Review eligibility is removed.

## Review, export and evidence tests

23. Verify `po_quote_permission` and any replacement quotation-permission question are absent.
24. Verify `po_final_warning` follows final comments immediately before submission and does not refer to quotation permission.
25. Verify existing Project Review wording and branching are unchanged apart from quotation-field removal and placement text.
26. Verify consent values export only on the non-repeating owner row and are blank on every Project Review repeat row.
27. Verify valid consent is joined onto review rows using all four conditions: intended recipient, all-confirmed, final Yes and Owner Consent complete.
28. Verify Save & Return Later, return-to-queue, completed-response modification disabled, no automatic next survey, no redirect and no participant-created repeat.
29. Verify desktop and mobile rendering of the full information sheet, ten statements, final decision, acknowledgement and repeated reviews.
30. Archive post-migration screenshots, dictionary, configuration evidence, synthetic export and source/live comparison in the approved restricted evidence location.

Recruitment is prohibited until all tests pass, residual differences are resolved or approved, and candidate 0.4 receives the required ethics/governance and repository approval.
