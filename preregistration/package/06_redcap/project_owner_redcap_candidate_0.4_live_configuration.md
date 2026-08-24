# Project Owner candidate 0.4 authorised-administrator migration and live-QA checklist

Status: instructions only. Do not execute without separate authorisation. Candidate 0.4 is unfrozen, pre-recruitment and non-authoritative. The missing-Domain wording is author-approved and implemented; PID 9149 migration and recruitment remain blocked until controlled migration is authorised and every live-QA item passes.

## Before migration

Document baseline: verify the canonical consent and questionnaire DOCX files match the SHA-256 and byte-size metadata embedded in the generator and branching specification. Confirm the consent wording, questionnaire labels/options and Appendix B against the generated dictionary before any live action. The former untracked `- Copy` questionnaire is not required.

Use the generated dictionary as the migration source. `project_owner_missing_domain_microdefinitions_candidate_0.4_review.md` records the author approval, and `project_owner_domain_wording_concordance_candidate_0.4.md` supplies the 11-row semantic-concordance record whose live-QA result must be completed.

1. Confirm PID 9149 is the Development project and contains no real participant, contact, consent or response records.
2. Confirm only disposable synthetic candidate-0.3 data exist.
3. Archive/export the candidate-0.3 live dictionary, synthetic data export, Survey Queue/repeating settings and QA evidence without credentials or live links.
4. Delete only the verified disposable synthetic records through the authorised REDCap administrator workflow.

## Controlled dictionary migration

5. Import `project_owner_redcap_data_dictionary_candidate_0.4.csv` through the controlled REDCap dictionary process and resolve every reported change before applying it.
6. Confirm exactly two instruments: non-repeating Owner Consent (`owner_consent`) and repeating Project Review (`project_review`).
7. Confirm `project_review` is the only repeating instrument, custom label `[assignment_id] — [project_title]`, participant-created repeats disabled and auto-start disabled.
8. Confirm `participant_info_link` displays the pinned v3.2 inline participant information byte-for-byte before `intended_recipient`, and configure the participant-information PDF download separately.
9. Confirm all ten confirmation fields are owner-level, required, blank by default, not import-populated and hidden after intended-recipient No.
9a. Confirm `consent_form_ver` is imported as `owner-consent-v3` on normal owner records and that `@DEFAULT='owner-consent-v3'` stores the same value when the field was initially blank and the owner submits either Yes or No.
10. Confirm `consent_items_complete` uses exactly `if([consent_read_info] = '1' and [consent_understand_invitation] = '1' and [consent_voluntary] = '1' and [consent_no_nonpublic] = '1' and [consent_confidentiality_limits] = '1' and [consent_withdrawal_deadline] = '1' and [consent_quote_process] = '1' and [consent_retention_reanalysis] = '1' and [consent_complaints] = '1' and [consent_acknowledgement] = '1', 1, 0)` and is hidden/read-only to participants.
11. Configure the Project Review Survey Queue condition exactly as `[owner_consent_complete] = '2' and [owner_consent] = '1' and [intended_recipient] = '1' and [consent_items_complete] = '1'`. Do not include `ack_pref`.
12. Re-establish the existing Stop Action for `intended_recipient = No`: end the consent survey and reveal no consent items, acknowledgement or Project Reviews.
13. Re-establish the existing Stop Action for `owner_consent = No`: end the consent survey, collect no acknowledgement and reveal no Project Reviews.
14. In the Online Designer for the Owner Consent survey, open each of the ten confirmation radio fields listed below, select **Survey Stop Action**, set the triggering response to **Not confirmed** (stored code `0`), and save the action. Configure the prompt behaviour used by the existing negative-response confirmation dialogue; do not configure an immediate terminal action. Repeat for: `consent_read_info`, `consent_understand_invitation`, `consent_voluntary`, `consent_no_nonpublic`, `consent_confidentiality_limits`, `consent_withdrawal_deadline`, `consent_quote_process`, `consent_retention_reanalysis`, `consent_complaints`, `consent_acknowledgement`.
14a. Live-test each of the ten actions separately. Select Not confirmed and verify that REDCap shows the confirmation dialogue before submission. Choose **Return and Edit Response** and verify that REDCap returns to the survey and clears the triggering answer. This is the intended mis-click recovery path. Also verify that continuing with the negative answer cannot establish `consent_items_complete = 1` or reveal Project Reviews.
14b. These ten Survey Stop Actions are manual project configuration. No Field Annotation or other data-dictionary action tag encodes them; archive screenshots or configuration evidence for all ten after migration.

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

23. Verify `po_quote_permission` and any participant-facing replacement quotation-permission question are absent everywhere in Project Review. Quotation remains a later point-of-use email process using the exact proposed wording and context and requiring written agreement.
24. Verify `po_final_warning` follows final comments immediately before submission and does not refer to quotation permission.
25. Verify both permanent tag blocks appear in every Project Review, each with its exact rc3 proposed-label short definition immediately before the Applied / Not applied proposed status.
26. Verify consent values export only on the non-repeating owner row and are blank on every Project Review repeat row.
27. Verify valid consent is joined onto review rows using all four conditions: intended recipient, all-confirmed, final Yes and Owner Consent complete.
28. Verify Save & Return Later, return-to-queue, completed-response modification disabled, no automatic next survey, no redirect and no participant-created repeat.
29. Verify desktop and mobile rendering of the full inline v3.2 participant information, ten statements, final decision, acknowledgement and repeated reviews.
30. Archive post-migration screenshots, dictionary, configuration evidence, synthetic export and source/live comparison in the approved restricted evidence location.
31. Verify `prop_t01_status` maps to `Demographic disparities / equity tag` and `prop_t02_status` maps to `COVID-19 & Pandemic` in every review and export.
32. Verify each tag's correctness and visibility questions operate independently and each visibility explanation retains its existing Partly visible / Not visible / Unsure branch.
33. Omit each tag correctness or visibility judgement in turn and confirm analytical completion remains false.
34. Verify all proposed-label displays use rc3 short definitions and that the separate missing-label reference blocks use Q6b/Q7b/Q8b wording.
35. Verify `po_taxonomy_ref` is absent and the three point-of-need reference blocks are the only complete participant-facing framework reference.
36. Verify `po_llm_disclaimer` appears verbatim after project information and immediately before the exact six-paragraph `po_intro` block; confirm both precede the detailed classification judgements and that `po_classification_overview` and all three hidden summary inputs are absent.
37. Verify `po_intro` contains no duplicate Save & Return Later, consent, confidentiality or withdrawal guidance.
38. Verify Q6b displays all 11 label-only choices in `DOMAIN_ORDER`, with no `Unclear from Register Entry` choice, and that `po_miss_domain_reference` contains all 11 exact approved boundary definitions.
39. Verify all three missing-label multi-select checkboxes display unconditionally and remain optional; confirm the former Yes/No/Unsure identification radios are absent and submitted checkbox state is the identification measure.
40. Verify every always-open reference block displays on desktop/mobile without truncation, literal markup or ambiguous line wrapping and survives PDF export.
41. Research Domain wording concordance: For every Research Domain, compare the rc3 definition displayed when the Domain is proposed with the Q6b boundary wording displayed in `po_miss_domain_reference`. Confirm that both identify the same substantive research object and apply compatible inclusion and exclusion boundaries.
42. Record an individual pass/fail live-QA result for all 11 Domains in `project_owner_domain_wording_concordance_candidate_0.4.md` or an associated completed QA record. Migration approval fails if any Domain points in materially different directions.
43. Confirm no separate taxonomy-reference document, link or placeholder appears and no participant-facing text promises one.
44. Verify the substantive-focus rule is visible before participants see or judge proposed classifications; confirm the `po_intro` heading, “Research Domains”, “Analytical Purposes” and `only when it is a substantive part of the project's research question or analytical aims` are clearly bold on desktop and mobile, while each definition and all surrounding prose remain normal weight.
45. Confirm the bold is not lost, malformed or displayed as literal HTML, and remains visible and readable after line wrapping.
46. Verify `po_miss_domain_reminder` appears after the Domain reference and before Q6b and clearly bolds only `a substantive subject of the project` on desktop and mobile.
47. Verify the Purpose reference, maximum-two guidance and `po_miss_purpose_reminder` all appear before Q7b, with only `a substantive aim of the project` strongly emphasised in the reminder.
48. Confirm participants are not instructed to assign a Domain merely because a dataset, variable, population characteristic or contextual factor is present.
49. Confirm participants are not instructed to assign a Purpose merely because a method, analytical step or secondary feature is present.
50. Confirm both reminders and the purpose guidance are unconditional; checkbox codes and order remain unchanged while checkbox requiredness is removed.
51. Compare the plain wording and visual emphasis of all three substantive-focus displays with the canonical questionnaire.
52. Fail migration approval if the governing rule is absent, appears after the detailed classification judgements or is not visibly emphasised.

Migration and recruitment are prohibited until controlled migration is authorised, all live tests pass, every Domain has a recorded semantic-concordance pass, residual differences are resolved or approved, and candidate 0.4 receives the required ethics/governance and repository approval.
