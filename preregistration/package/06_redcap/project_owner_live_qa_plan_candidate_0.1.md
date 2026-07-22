# Project Owner live-QA plan - owner-redcap-candidate-0.1

Intended Development project: PID 9149, `DEA Validation Study – Project Owner
Review`. PID 9149 is recorded here only as the future controlled QA target. No
connection, import, record creation or live test occurred during candidate
construction.

Candidate status: **development candidate; unfrozen; not authorised for real
contact, invitations, formal assignments or data collection**.

## A. Offline validation performed

The deterministic local builder and validator establish before any import:

- exactly 152 fields and ordered form counts 27 / 39 / 86;
- exactly `owner_contact_admin`, `owner_assignment_admin` and
  `project_owner_review`;
- one Classic, non-longitudinal architecture with no repeating instrument;
- neutral record key and stable record-type codes;
- contact and assignment guards on every applicable field;
- participant acknowledgement guard on all substantive survey content;
- direct identifiers only in Owner Contact Admin;
- no direct identifiers or scratch/sample/reserve/disagreement/adjudication
  administration in assignment or survey fields;
- fixed domain/purpose slots, unused-slot hiding and proposal cardinality;
- Applied and Not applied states for both tags with Yes / No / Unsure review;
- owner taxonomy Fit / Partial Fit / No Fit only;
- optional response-level quotation permission and contact-level named
  acknowledgement permission;
- deterministic analytical-completion derivation;
- affirmative expression of interest before link-release approval;
- synthetic-only fixtures, including one contact linked to multiple assignments;
- byte stability of the frozen scratch candidate-0.7 dictionary.

Offline validation cannot establish REDCap runtime branching, erasure of hidden
values, survey-link isolation, staff permissions, email/invitation behaviour,
browser rendering, export permissions or audit timestamps.

## B. Later admin-user live QA in PID 9149

Use only the versioned synthetic import fixture. Record the imported dictionary
export, fixture hash, tester, date, REDCap version where visible, result and any
corrective candidate version. Do not use real researchers or projects.

| Test | Required result |
|---|---|
| Blank-project import | Candidate imports into a blank Classic project without warnings that change meaning. |
| Project mode | Project remains Development, non-longitudinal and non-repeating. |
| Form order | Owner Contact Admin, Owner Assignment Admin, Project Owner Review. |
| Survey setup | Only Project Owner Review is enabled as a survey; contact and assignment instruments are not surveys. |
| Contact routing | Contact record exposes contact-admin fields only; assignment/review response fields remain hidden and non-actionable. |
| Assignment routing | Assignment record exposes assignment administration; no contact name/email/permission fields appear. |
| Record-specific links | Each assignment receives a distinct record-specific link; no shared public survey link is enabled. |
| Release gate | A link cannot be marked approved/released until the linked contact has affirmative expression of interest. |
| Multi-assignment owner | One synthetic owner_id links one contact record to several distinct assignment records and links. |
| Identifier permissions | Contact identifiers are visible only to the approved contact-admin role. |
| Full admin export | Contains expected contact and assignment rows, stable keys, form statuses and timestamps. |
| Restricted contact export | Contains contact crosswalk only and no review answers. |
| Analytical export | Filters assignment records; includes owner_id, stable DEA Record ID, proposals and responses; excludes all `oc_*` fields. |
| Prohibited leakage | No scratch identity/response, sample set, hard-case, reserve, disagreement or adjudication status exists. |
| Withdrawal | Researcher-level suppression and assignment-level withdrawal retain an audit trail and disable further operational use. |
| Hidden-value erasure | Changing a controlling answer clears values hidden by the new branch where REDCap erase-value configuration is applicable. |

## C. Later external/respondent-view live QA

Use a tester who has no REDCap account or project rights and only a synthetic
record-specific link. Do not email a real researcher.

- Confirm the respondent cannot see either administrative instrument or any
  other record.
- Confirm a Contact record cannot yield a usable Project Owner Review link.
- Confirm the introduction shows the dashboard, time, withdrawal and study
  contact placeholders only after they have been configured and approved.
- Confirm No at participation acknowledgement ends the review and hides every
  classification question.
- Test Save & Return, close/reopen, incomplete response and completed response.
- Test one owner with several links; completing one must not alter another.
- Test one and multiple proposed domains and one and two proposed purposes.
- Confirm every unused domain/purpose slot is hidden and not required.
- Test Applied and Not applied for each tag; confirm wording is status-based,
  not Fits/Does not fit for absent tags.
- Exercise tag correctness Yes, No and Unsure and determinability Yes, Partly,
  No and Unsure; No/Unsure must reveal the explanation.
- Exercise domain/purpose Fits, Does not fit and Unsure plus all visibility
  values and explanation branches.
- Exercise missing domain, purpose and tag branches.
- Exercise Sufficient, Partial and Insufficient public-entry branches.
- Exercise taxonomy Fit, Partial Fit and No Fit; verify no Cannot assess option.
- Exercise non-public-knowledge No/Yes and its source-only note.
- Confirm quotation permission is optional and offers Yes, No and Contact me.
- Confirm no named-acknowledgement permission is asked on the assignment survey.
- Confirm completion/thank-you and withdrawal wording.
- Inspect supported desktop browsers and a mobile-width display for readability,
  link safety and conditional-field placement.

## D. Freeze criteria

Candidate 0.1 remains unfrozen until all of the following are true:

1. The generated source dictionary has been imported into blank Development
   PID 9149 using the controlled procedure.
2. Every admin and respondent test above has passed with archived evidence.
3. A final live dictionary export has been compared with the generated source
   under explicit, narrow round-trip rules; all residual differences are zero.
4. Identifier, instrument and export permissions have passed restricted-user QA.
5. All synthetic QA records, links and invitation-log entries have been deleted
   or moved to an approved no-user archive before freeze, with an audit record.
6. The final source dictionary, live export, QA evidence and candidate history
   are hash-recorded and repository tests pass.
7. The owner candidate is explicitly frozen before the preregistration is made
   final. Freeze alone does not authorise real recruitment or data collection.

Until those criteria are met, do not describe this candidate as live-QA
approved, final, frozen or ready for formal use.
