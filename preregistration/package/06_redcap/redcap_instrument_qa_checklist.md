# REDCap instrument QA checklist — redcap-candidate-0.6

- [ ] Confirm every candidate-0.3 pilot response is complete, exported and
      archived before candidate 0.6 is imported.
- [ ] Dictionary imports without unresolved warnings; field count is 145.
- [ ] Administrative, source, sampling and model fields are absent from coder
      and owner displays.
- [ ] Existing sample-set codes 1–4 are unchanged and every Pilot row has
      validation_included = 0 and instrument_ver = redcap-candidate-0.3.
- [ ] sc_taxonomy_fit shows exactly codes 1 Fit, 2 Partial Fit, 3 No Fit and
      4 Cannot assess from register entry.
- [ ] po_taxonomy_fit shows exactly codes 1 Fit, 2 Partial Fit and 3 No Fit.
- [ ] The exact approved point-of-use help text appears beneath
      sc_taxonomy_fit and nowhere on unrelated taxonomy fields.
- [ ] Both taxonomy-issue fields show only stored codes 1, 2 and 5 with the
      candidate-0.6 labels.
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
- [ ] sc_exposure_note remains required when accidental exposure is Yes.
- [ ] Domain and purpose Unclear exclusivity and MAXCHECKED=2 behave as
      intended; COVID and equity choices are unchanged.
- [ ] Export contains current issue checkbox columns 1, 2 and 5, not 3, 4 or 6.
- [ ] Desktop/mobile display, save-and-return and completion status work.
- [ ] Export matches redcap_expected_export_schema.csv with one row per
      assignment.
- [ ] Capture dated import log and screenshots or PDF evidence in approved
      restricted storage.
- [ ] Candidate-0.6 readiness is not marked passed until all tests above pass.
