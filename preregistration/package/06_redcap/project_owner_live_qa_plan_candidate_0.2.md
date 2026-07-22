# Live-QA plan — owner-redcap-candidate-0.2

Status: unfrozen development candidate. PID 9149 is documented only as the
intended blank Development target. No connection, import or live test occurred.

Candidate 0.2 cannot be frozen until all applicable live tests pass, evidence is
archived, and all synthetic records are removed or moved to an approved no-user
archive.

## A. Offline validation already performed

- Deterministic 167-field generation and exact 31 / 12 / 39 / 85 counts.
- Unique names, valid types and choices, balanced branching.
- Contact-only consent and assignment-only review guards.
- Candidate-0.1 and frozen scratch-candidate hashes.
- Identifier confinement to Owner Contact Admin.
- No scratch, sample, reserve, disagreement-status or adjudication leakage.
- One consent per synthetic owner_id.
- Current-consent and project-link release derivations.
- Missing, declined, stale, withdrawn and current synthetic consent cases.
- Substantive review and analytical-completion regression.

Offline validation does not establish REDCap runtime behaviour.

## B. Later admin-user live QA in Development PID 9149

1. Import into a verified blank Classic, non-longitudinal project.
2. Confirm form order and counts: Owner Contact Admin; Project Owner Consent;
   Owner Assignment Admin; Project Owner Review.
3. Enable only Project Owner Consent and Project Owner Review as surveys.
4. Confirm both administrative instruments remain admin-only.
5. Create synthetic contact and assignment records only.
6. Confirm consent appears only for contact records and review only for assignments.
7. Confirm direct identifiers/contact administration never appear in consent.
8. Confirm participant-information version displays read-only.
9. Submit Yes and verify native timestamp, form status, version and decision.
10. Submit No and verify survey end and blocked assignment links.
11. Confirm interest alone does not make links eligible.
12. Confirm missing, declined, withdrawn or re-consent-required consent blocks links.
13. Confirm current consent makes links eligible but does not send them.
14. Confirm one consent supports several separate assignment links.
15. Confirm only record-specific links; no shared public link.
16. Test re-consent and withdrawal administration without deleting data.
17. Verify full restricted export and de-identified analytical export.
18. Confirm analytical export joins owner_id, stable Record ID, consent
    version/status and review data without direct identifiers.

## C. Later external/respondent-view live QA

- Consent desktop/mobile display, save-and-return, incomplete, Yes and No.
- Respondent cannot see admin instruments, other contacts or assignments.
- Review link opens only its own assignment.
- Later reviews show the voluntary reminder and no repeated consent checkbox.
- One owner can access several assignments after one consent.
- Review save-and-return, partial and completed responses.
- All label-slot, tag-status, conditional-note, missing-label, sufficiency and
  taxonomy branches.
- Quotation remains response-specific; acknowledgement remains researcher-level.
- Withdrawal and contact placeholders render after approved configuration.

## D. Freeze criteria

- Placeholders approved and configured.
- Admin and respondent QA pass with archived evidence.
- Consent timestamp/version, re-consent and withdrawal work as specified.
- Source/live comparison has no unexplained residual difference.
- Analytical export excludes direct identifiers.
- No scratch or sampling metadata is exposed.
- All synthetic records are deleted or archived outside active access.
- A frozen dictionary is generated only after explicit freeze.

Until then candidate 0.2 is not frozen and does not authorise recruitment, data
collection, or any connection to PID 9149.
