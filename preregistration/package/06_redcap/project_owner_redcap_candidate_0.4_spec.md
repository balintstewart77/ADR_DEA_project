# Project Owner REDCap candidate 0.4 specification

Version: `owner-redcap-candidate-0.4`  
Status: unfrozen development candidate; pre-recruitment; controlled PID 9149 migration and live QA pending.  
Ethics trace: UCL Project ID 5004; corrected Participant Information v3.1 dated 18 August 2026 preserves the ethics-approved v3 source; Questionnaire v3 remains the approved reference and requires reconciliation with the live-QA changes recorded below.

## Architecture and field counts

Candidate 0.4 preserves candidate 0.3 as its unchanged historical predecessor. It retains one pseudonymous owner record, non-repeating `owner_consent`, repeating `project_review`, pre-created review instances and one participant-specific Survey Queue link. It contains exactly two instruments and 117 dictionary fields:

- `owner_consent`: 22 fields;
- `project_review`: 95 fields.

The Project Owner instrument remains unfrozen and non-authoritative. This candidate does not authorise recruitment or live migration. Both canonical participant DOCX files are pinned by SHA-256 and byte size; generation stops if either changes without an authorised metadata refresh. The missing-Domain wording is author-approved and repository-validated; controlled migration and live semantic/display QA remain mandatory before recruitment.

## Project Review orientation and point-of-need references

After the public project information, `po_llm_disclaimer` reproduces the Questionnaire v3 large-language-model disclaimer verbatim. `po_intro` then presents the six-paragraph Questionnaire Section 2 block beginning “How the classifications work”. The heading is closed before the normal-weight body begins; the terms “Research Domains” and “Analytical Purposes” are strongly emphasised without their definitions, and the governing substantive-focus phrase is strongly emphasised in its threshold paragraph. It is followed by the detailed Domain, Purpose and tag judgements; the former read-only classification overview and its three hidden summary inputs are absent. The intro contains no consent, confidentiality, withdrawal or Save & Return Later wording and introduces no training material.

The inherited participant-visible `po_taxonomy_ref` synthetic-QA placeholder remains absent. It is replaced functionally—not as a standalone field or attachment—by three complete always-open reference blocks immediately before the missing-Domain, missing-Purpose and missing-tag menus. These blocks are the participant delivery route for every nominable category definition at the point of need. Each block states that labels already proposed above remain listed for completeness and should be selected only when genuinely absent from the proposal.

Q6b contains exactly 11 label-only missing-Domain choices. `po_miss_domain_reference` displays every matching author-approved boundary definition generated from `OWNER_DOMAIN_DISPLAY`; `Unclear from Register Entry` is excluded. Q7b and Q8b likewise use label-only choices with complete adjacent reference blocks sourced from their questionnaire/rc3-identical wording. `project_owner_missing_domain_microdefinitions_candidate_0.4_review.md` records the author decision, and `project_owner_domain_wording_concordance_candidate_0.4.md` records the human semantic review. Live semantic, wrapping and PDF/export display QA remains pending.

The three missing-label menus are displayed unconditionally and are optional. The former Yes/No/Unsure identification radios are absent. Submitted checkbox state is the missing-label measure: because each complete menu is always displayed, an all-zero submitted set records that the owner selected no missing label. Domain and Purpose guidance remains visible before the relevant checkbox. This deliberate departure from the approved questionnaire branching must be notified to the REC. A separate structured Unsure response is no longer collected; because each optional basis field remains conditional on a checkbox selection, uncertainty can be recorded there only when the owner selects at least one candidate label.

## Operational cross-cutting-tag invariant

The operational set contains exactly two frozen machine values, in this order:

- `Demographic disparities / equity tag` (`prop_t01_status`);
- `COVID-19 & Pandemic` (`prop_t02_status`).

Operational inclusion is determined by `include_in_prompt is true; layer is Cross-cutting tag; source status does not begin 'removed'`. Lifecycle/provenance status is not the inclusion criterion: the first tag is `new v3.4`, while the second is `active`, and both are operational because they satisfy the explicit rule. The production classifier, production outputs, dashboard and Project Owner pipeline therefore retain both tags; no one-tag bug exists. Candidate 0.4 changes neither the frozen taxonomy nor the production prompt.

Each Project Review displays the canonical label and exact rc3 proposed-label short definition from `prop_t01_def` or `prop_t02_def` immediately before its Applied / Not applied proposed status. The longer Questionnaire and Appendix A definitions remain documentary reference wording and are not substituted into the proposed-label display. Both independent correctness and visibility blocks remain required for analytical completion.

## Ethics-to-REDCap consent traceability

The participant-visible sequence is: the pinned verbatim inline Participant Information v3.1 in `participant_info_link`; `intended_recipient`; ten separately stored confirmations; final `owner_consent`; and optional `ack_pref` only after valid affirmative consent. The downloadable participant-information PDF remains a separate manual survey attachment.

The canonical consent statements remain aligned with the ten confirmation fields, including restoration of the strict approved `consent_no_nonpublic` wording. Questionnaire v3 remains stale relative to the live-QA changes in form guidance, duration, visibility stems, missing-label guidance and disclaimer placement; it requires separate reconciliation and applicable ethics/change-control action before production. Its Appendix B records the complete owner-level consent-validity join. Q13, participant-facing per-project quotation permission and taxonomy-reference placeholders are absent. Controlled migration and live QA remain mandatory before recruitment.

- `consent_read_info` — I have read and understood the participant information above.
- `consent_understand_invitation` — I understand why I have been invited and what taking part involves.
- `consent_voluntary` — I understand that participation is voluntary and that I may review all, some or none of the projects offered.
- `consent_no_nonpublic` — I understand that I should not disclose confidential, sensitive or otherwise non-public information.
- `consent_confidentiality_limits` — I understand that my information will be handled confidentially and that direct identifiers will not appear in research outputs, but complete anonymity cannot be guaranteed because the participant group is small and responses concern publicly identifiable projects.
- `consent_withdrawal_deadline` — I understand that I may withdraw a submitted review by emailing the study team by Friday 2 October 2026, and that after this date responses can no longer be removed.
- `consent_quote_process` — I understand that if the study wishes to quote my comments, I will be sent the exact proposed wording in advance and it will only be used if I agree.
- `consent_retention_reanalysis` — I agree that my pseudonymised research data may be retained for 10 years and used by the research team for verification and further analyses directly related to this validation study and the improvement of the classification framework and dashboard.
- `consent_complaints` — I am aware of who I should contact if I wish to lodge a complaint.
- `consent_acknowledgement` — I understand that choosing to be acknowledged by name is optional, is separate to my decision to take part, and would make my participation in this study permanently and publicly identifiable.

Every confirmation is a separate required owner-level radio field with stored codes `1, Confirmed | 0, Not confirmed`, starts blank, is never pre-populated, and branches only on `[intended_recipient] = '1'`. Requiredness prevents an incomplete consent-form submission; the calculation separately requires every stored value to equal `1`, so a required `0` does not establish valid consent. None appears in `project_review` or counts as a Project Review analytical outcome.

`consent_form_ver` remains a hidden/read-only text field populated by the owner-frame import. Its `@DEFAULT='owner-consent-v3'` annotation also supplies the displayed consent version when a record reaches the survey without that imported value, including a decline submission; controlled live QA must confirm the default is stored on the target REDCap runtime.

`consent_items_complete` is a survey-hidden calculated field with this exact expression:

```text
if([consent_read_info] = '1' and [consent_understand_invitation] = '1' and [consent_voluntary] = '1' and [consent_no_nonpublic] = '1' and [consent_confidentiality_limits] = '1' and [consent_withdrawal_deadline] = '1' and [consent_quote_process] = '1' and [consent_retention_reanalysis] = '1' and [consent_complaints] = '1' and [consent_acknowledgement] = '1', 1, 0)
```

Valid affirmative consent is the composite condition:

```text
[intended_recipient] = '1' and [consent_items_complete] = '1' and [owner_consent] = '1' and [owner_consent_complete] = '2'
```

`owner_consent` retains the ethics-approved final decision wording and `1, Yes, I agree to take part | 0, No, I do not wish to take part`. It is shown whenever the intended-recipient response is Yes, so a participant can actively decline even when one or more confirmations are blank or Not confirmed. The existing No Stop Action ends the consent survey, hides acknowledgement and reveals no reviews. An attempted raw Yes with `consent_items_complete != 1` is not valid consent, grants no Survey Queue access and must be tested explicitly during controlled live QA. No unverified action tag or runtime claim is encoded.

The Project Review Survey Queue condition is exactly:

```text
[owner_consent_complete] = '2' and [owner_consent] = '1' and [intended_recipient] = '1' and [consent_items_complete] = '1'
```

Clearing a confirmation recalculates `consent_items_complete` to 0 and therefore invalidates queue eligibility.

## Acknowledgement and quotation policy

`ack_pref` remains optional, owner-level, and excluded from consent validity and analytical completion. It appears only after intended-recipient Yes, all ten confirmations and final consent Yes. Its participant-facing wording and the full Yes / No / Decide later response labels match the canonical consent document exactly. It states that declining means the study team will not name or acknowledge the participant in resulting outputs; it does not make an absolute non-disclosure claim.

Candidate 0.4 removes `po_quote_permission` from the generator, dictionary, Project Review count, branching specification, field and export specifications, fixture and analytical-completion documentation. It is not replaced. Quotation permission is not collected in REDCap. If the study team wishes to use a participant’s words, the participant will be contacted by email with the exact proposed quotation and the context in which it would appear. The quotation will be used only following written agreement.

`po_final_warning` now follows `po_other_comment` immediately before submission and has no quotation-permission dependency.

All participant-visible read-only stimulus fields and all survey-hidden administrative fields are optional, so an empty prefilled value cannot block submission. `public_register_url` is retained for downstream compatibility but survey-hidden; `po_register_provenance` supplies the static register provenance line as at 1 June 2026. `owner_intro` retains the review-duration and Save & Return guidance, while `po_privacy` uses the live-QA form-guidance wording and the stricter approved consent statement remains unchanged. Descriptive-field bodies render at normal weight while intended headings and proposed category labels remain emphasised.

## Fixture and long-format analysis

The synthetic fixture remains three owners, 19 pre-created Project Review instances and 22 long-format rows. Owner consent responses, all ten confirmations, `consent_items_complete`, final consent and acknowledgement are blank on import. Owner consent values occur only on the non-repeating owner row; Project Review repeat rows keep them blank. No synthetic participant is imported as consented.

Analysis must join the non-repeating owner row to reviews by `owner_id` and require intended-recipient Yes, all-confirmed 1, final consent Yes and Owner Consent complete. Review-row values alone must never establish consent.

## Scope exclusions and change record

Reason: repair participant-facing requiredness, density, inline information delivery, duration, guidance, visibility wording, missing-label task order, provenance and descriptive formatting defects while preserving category wording authorities. Nature: candidate 0.4 remains unfrozen, pre-recruitment and non-authoritative. The missing-label gate removal and other documented live-QA text departures require questionnaire reconciliation and applicable REC/change-control action before migration. No frozen taxonomy, protocol, production prompt, candidate 0.3 artefact, assignment, sample or participant record changed.
