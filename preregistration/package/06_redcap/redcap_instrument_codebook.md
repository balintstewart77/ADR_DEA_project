# REDCap instrument codebook

Status: live-QA-complete frozen formal instrument redcap-candidate-0.7. The
pilot used redcap-candidate-0.3. Candidate 0.6 was imported and partially
inspected, then superseded before final runtime QA. Candidate 0.7 is frozen for
preregistration and subsequent formal scratch coding but has no formal
assignments populated. Preregistration completion is the next permitted step;
sampling and assignment import remain prohibited until preregistration is
final.

## Architecture and visibility

One non-longitudinal REDCap project contains assignment_admin,
coder_declaration, scratch_coder, and project_owner. assignment_id is the record
key. Multiple coders or owners reviewing one project have distinct opaque
assignment IDs and share hidden project clustering identifiers. A declaration
is a separate record rather than a project assignment.

Scratch coders see only a neutral assignment code, title, datasets used, and
scratch questions. Owners additionally see proposed labels and definitions.
The owner stream separates actual-project fit from whether the public register
entry visibly supports the label. Administrative fields remain hidden and
read-only. `record_kind` uses 1 Project assignment, 2 Coder declaration and 3
Synthetic QA. Blank is permitted only for historical candidate-0.3 records and
is treated as a project-assignment record for display. The field is
administrative and does not alter scientific sample membership.

## One-time coder declaration and per-project exposure

Before formal coding, each scratch coder completes one `coder_declaration`
record. `cd_declaration` confirms that classifications will use only the
permitted public-register title, datasets-used entry and approved training
materials, and that additional prior, professional or accidentally acquired
information will be flagged per project. `cd_nonconfirm_note` is required only
for Cannot confirm. REDCap's audit trail and form-completion timestamp provide
the operational completion record; there is no manually entered declaration
date.

Every coder–project assignment requires `sc_exposure` (0 No, 1 Yes). Yes covers
prior involvement or familiarity with the project, professional or
institutional knowledge, and accidental exposure to another reviewer's
information. `sc_exposure_note` then records the source of additional knowledge
without reproducing restricted content, another reviewer's classification, or
the substantive knowledge itself. The coder still completes the project using
only the visible permitted evidence.

## Current response codes

- Domains and purposes reproduce dict-1.0-rc2. Purposes permit one or two;
  Unclear is exclusive in both layers.
- Tags: 0 No; 1 Yes.
- Sample set: 1 Baseline; 2 Hard case; 3 Owner review; 4 Pilot. Pilot rows use
  validation_included = 0.
- Sufficiency: 1 Sufficient; 2 Partial; 3 Insufficient.
- Scratch taxonomy fit: 1 Fit; 2 Partial Fit; 3 No Fit; 4 Cannot assess from
  register entry.
- Project-owner taxonomy fit: 1 Fit; 2 Partial Fit; 3 No Fit.
- Taxonomy issue, both streams: 1 Missing or inadequately represented
  category; 2 Ambiguous or overlapping category boundaries; 5 Other taxonomy
  problem.
- Confidence: 1 High; 2 Medium; 3 Low.
- Proposed-label owner fit: 1 Fits; 2 Does not fit; 3 Unsure.
- Owner public-entry visibility: 1 Clearly visible; 2 Partly visible; 3 Not
  visible; 4 Unsure.

Cannot assess from register entry means that the visible title and dataset field
are too thin to judge taxonomy fit. It is not No Fit, is not a taxonomy defect,
does not display sc_tax_issue, and is coherent only when sc_sufficiency is
Partial or Insufficient. Partial or Insufficient evidence does not force this
response: a coder may still be able to judge taxonomy fit.

Point-of-use guidance for `sc_taxonomy_fit`: Taxonomy fit asks whether the
taxonomy can adequately represent the project, not whether the public register
entry contains enough information to judge this. Select “Cannot assess from
register entry” when the entry is too limited to determine taxonomy fit. Do not
select “Partial Fit” or “No Fit” solely because the entry lacks information.

The issue field is shown and required only for Partial Fit or No Fit. One or
more retained issue types may be selected. Other taxonomy problem requires an
explanatory note. The field remains hidden for Fit and, in the scratch stream,
Cannot assess from register entry.

## Historical candidate-0.3 decoding

Candidate 0.3 scratch taxonomy fit used only 1 Fit, 2 Partial Fit and 3 No Fit.
Both candidate-0.3 issue fields used:

1. Missing category
2. Ambiguous/overlapping categories
3. Too broad
4. Too narrow
5. Other
6. None

Archived pilot exports must be decoded by instrument_ver. Codes 3, 4 and 6 are
preserved exactly for candidate-0.3 data and are not silently mapped to the
candidate-0.7 categories. `sc_blind_decl` retains its original label, codes and
historical values and is shown only for candidate-0.3 records. The current
expected export schema lists only candidate-0.7 checkbox columns 1, 2 and 5.

## Reporting

Scratch taxonomy-fit reporting includes Fit, Partial Fit, No Fit and Cannot
assess from register entry. Where useful, an assessable-fit distribution is
reported using only Fit, Partial Fit and No Fit. Cannot assess is reported with
register-sufficiency diagnostics; it is not counted as No Fit, a taxonomy
defect, or in the taxonomy-issue denominator. Taxonomy-issue frequencies use
only cases with Partial Fit or No Fit.

Exposure-flagged coder–project responses remain in the primary analysis. Their
frequency is reported, with qualitative source summaries where appropriate. A
sensitivity analysis excluding flagged responses is presented where their
number and pattern make that informative; a flag is not automatically missing
or invalid.

REDCap generates the four standard form-completion fields. The local validator
blocks unresolved conditional requirements and applies instrument-version-aware
response validation.
