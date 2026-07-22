# UCL REDCap live-runtime QA and candidate-0.7 freeze — 2026-07-22

## Scope and evidence boundary

Candidate `redcap-candidate-0.7` completed live QA on 22 July 2026 using only
pilot-history and synthetic QA records. No formal validation sample or formal
assignment was created or imported. Tester names, the live project identifier,
URLs, screenshots, credentials and the C02 email are not stored in Git.

The C02 email result below is a manually recorded QA result, not a claim that
the email or an attachment is present in the repository. The tracked evidence
is limited to the final dictionary/data snapshots, synthetic import fixtures,
archive-migration audits and deterministic source/live comparison.

- Generated source dictionary SHA-256:
  `1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc`
- Frozen source dictionary SHA-256:
  `1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc`
- Final live dictionary SHA-256:
  `bb1de2b9ea811afc8b0f23fcb489c1e01eb94d6677d45a64c273140532c5293f`
- Final post-archive live-data SHA-256:
  `d618848e0b9d01edd3521c9f71c3a81b050ffa271e015fe46e4beca81d8a81ca`

## Admin live QA — passed

- The one-time coder declaration displayed only on declaration records.
- Confirmed / Cannot confirm branching worked; Cannot confirm required the
  non-confirmation note; erase-value behaviour passed when the branch closed.
- Historical candidate-0.3 `sc_blind_decl` remained available only on pilot
  records and candidate-0.3 pilot compatibility passed.
- The revised project-level exposure wording and help displayed correctly.
  Exposure Yes required a source note; the Yes-to-No erase behaviour passed.
- Research Domain Unclear exclusivity passed.
- Analytical Purpose enforced a maximum of two and Unclear exclusivity passed.
- Taxonomy Cannot assess hid taxonomy issue; Partial Fit revealed the required
  issue type.
- Explanatory-note branching passed for partial/insufficient evidence,
  Partial/No Fit and low confidence.
- Incomplete save/reopen and complete save/reopen both passed.

## Restricted C02 QA — passed

- C02 could see only records in their own DAG; no other coder's records were
  visible.
- Only Coder Declaration and Scratch Coder were available. Assignment Admin
  and Project Owner were hidden.
- Save/reopen worked.
- No setup, user-rights, reports, import, export, API, DAG-management or other
  administrative access remained.
- A temporary export-permission error was corrected and retested; Data Exports
  was no longer visible.

## Archive and dashboard QA — passed

- A no-user DAG titled `Pilot and QA archive` was created with unique name
  `pilot_and_qa_archi` and numeric DAG ID `15815`.
- All 35 pilot/QA records were moved to that DAG. The archive DAG has zero
  users, and C01, C02 and C03 no longer see historical pilot/QA records.
- A custom dashboard titled `Formal Coding` was created. It shows only Coder
  Declaration and Scratch Coder and sorts by `display_order` ascending.
- Its exact filter is:

  ```text
  [assignment_batch] = 'formal_validation'
  and
  (
    ([record_kind] = '1' and [validation_included] = '1' and [sample_status] = '1')
    or
    ([record_kind] = '2' and [sample_status] = '1')
  )
  ```

- Before formal import the dashboard correctly showed zero records.
- C02 confirmed by email on 22 July 2026 that neither the Formal Coding
  dashboard nor the Default Dashboard showed any records. This is recorded as
  a manual QA result; the email is not tracked.
- This completed restricted-user REDCap QA.

## Archive-state verification

The final data snapshot contains 35 rows and 35 unique `assignment_id` values.
All use DAG `pilot_and_qa_archi`, all have `validation_included = 0`, and none
has `assignment_batch = formal_validation`. Composition is 30 candidate-0.3
pilot assignments, one candidate-0.6 QA record and four candidate-0.7 QA
records. The reassignment file contains only `assignment_id` and
`redcap_data_access_group`; every target is `pilot_and_qa_archi`. Pre/post
audits contain the same 35 records and differ only in DAG assignment.

- Pre-migration audit SHA-256:
  `fc74e2904c21e463615d50fbc969a9e8ee24406a2fb892d0c8bf1816fa206189`
- DAG reassignment audit SHA-256:
  `8eb9d0ad77ee887b60789d473a329a87e426bbf2f442b3e5ca77cab44b7a5ed6`
- Post-migration audit SHA-256:
  `931df02328c93799b55a6304fdb3a63465dc5e29f058366b576aafc0267eb909`

## Source-to-live round trip

The generated and live dictionaries both contain 150 fields in the same order:
50 Assignment Admin, four Coder Declaration, 16 Scratch Coder and 80 Project
Owner. They are not textually or byte identical. Strict comparison found 65
raw cells: 52 live-only single leading ASCII spaces in Field Annotation, 12
one-pass HTML entity decodings in Project Owner descriptive labels with
unchanged markup structure, and one omitted `assignment_id` section header on
the hidden Assignment Admin instrument.

The deterministic verifier accepts only those exact transformations; it uses no
trim, whitespace collapse, case folding, HTML stripping, Unicode normalization
or field/choice reordering. Residual mismatches are zero. The authoritative
two-level report is
`live_qa/audit/redcap_candidate_0.7_source_live_comparison_2026-07-22.md`.
Its SHA-256 is
`2a4fbe7047f2790811e0a88b36270c65119e1fe2e62e234cd760ea85411fa603`.

## Freeze decision

Candidate 0.7 is live-QA complete and frozen for preregistration and subsequent
formal scratch coding. It is not populated with formal assignments. This
instrument freeze does not authorise sampling or import: preregistration
completion is the next permitted step, and formal sampling and assignment
import remain prohibited until preregistration is final.
