# REDCap instrument QA checklist — redcap-candidate-0.7

- [ ] Confirm every candidate-0.3 pilot response is complete, exported and
      archived before candidate 0.7 is imported.
- [ ] Candidate 0.6 remains documented as imported and partially inspected,
      then superseded before final runtime QA without collecting formal data.
- [ ] Dictionary imports without unresolved warnings; field count is 150 and
      form order is assignment_admin, coder_declaration, scratch_coder,
      project_owner.
- [ ] Administrative, source, sampling and model fields are absent from coder
      and owner displays.
- [ ] Existing sample-set codes 1–4 are unchanged and every Pilot row has
      validation_included = 0 and instrument_ver = redcap-candidate-0.3.
- [ ] record_kind shows exactly 1 Project assignment, 2 Coder declaration and
      3 Synthetic QA in administration and is hidden/read-only on surveys.
- [ ] The candidate-0.7 declaration fixture creates one new review-only
      declaration record and no sampled project.
- [ ] coder_declaration appears only for record_kind 2; cd_declaration wording
      and codes are exact; cd_nonconfirm_note is required only for code 0.
- [ ] REDCap audit trail and coder_declaration completion timestamp provide the
      declaration completion record; no manual declaration date is present.
- [ ] sc_blind_decl retains its candidate-0.3 wording/codes, is visible on a
      blank-record_kind candidate-0.3 pilot record, and is hidden on candidate
      0.7 project assignments.
- [ ] Every scratch field is hidden for record_kind 2 and remains visible for
      record_kind 1, record_kind 3 and blank historical records, subject to its
      preserved conditional logic.
- [ ] sc_taxonomy_fit shows exactly codes 1 Fit, 2 Partial Fit, 3 No Fit and
      4 Cannot assess from register entry.
- [ ] po_taxonomy_fit shows exactly codes 1 Fit, 2 Partial Fit and 3 No Fit.
- [ ] The exact approved point-of-use help text appears beneath
      sc_taxonomy_fit and nowhere on unrelated taxonomy fields.
- [ ] Both taxonomy-issue fields show only stored codes 1, 2 and 5 with the
      candidate-0.7 labels.
- [ ] sc_tax_issue appears and is required for fit 2 or 3 only; it remains
      hidden for fit 1 and 4.
- [ ] po_tax_issue appears and is required for fit 2 or 3 only; it remains
      hidden for fit 1.
- [ ] Multiple retained issue types can be selected.
- [ ] Other taxonomy problem requires the stream's explanatory note.
- [ ] Cannot Assess plus Sufficient is rejected or review-flagged, while
      Cannot Assess plus Partial or Insufficient with a note is accepted.
- [ ] sc_note is triggered by Partial/Insufficient sufficiency, Partial/No Fit,
      or Low confidence, and not by accidental exposure alone.
- [ ] sc_exposure is required per project and its wording covers prior project
      involvement/familiarity, professional or institutional knowledge, and
      accidental reviewer-information exposure.
- [ ] The exposure help tells a flagged coder to complete the classification
      using only permitted evidence; Yes does not skip or invalidate the record.
- [ ] sc_exposure_note remains required when exposure is Yes, asks only for the
      source, and warns against reproducing restricted content or another
      reviewer's classification.
- [ ] Domain and purpose Unclear exclusivity and MAXCHECKED=2 behave as
      intended; COVID and equity choices are unchanged.
- [ ] Export contains current issue checkbox columns 1, 2 and 5, not 3, 4 or 6.
- [ ] Desktop/mobile display, save-and-return and completion status work.
- [ ] Export matches redcap_expected_export_schema.csv with one row per
      assignment.
- [ ] Capture dated import log and screenshots or PDF evidence in approved
      restricted storage.
- [ ] Candidate-0.7 readiness is not marked passed until all tests above pass.
