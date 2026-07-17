# REDCap instrument codebook

Status: working post-training candidate redcap-candidate-0.4. The pilot used
redcap-candidate-0.3; candidate 0.4 live runtime QA remains pending.

## Architecture and visibility

One non-longitudinal REDCap project contains assignment_admin, scratch_coder,
and project_owner. assignment_id is the record key. Multiple coders or owners
reviewing one project have distinct opaque assignment IDs and share hidden
project clustering identifiers.

Scratch coders see only a neutral assignment code, title, datasets used, and
scratch questions. Owners additionally see proposed labels and definitions.
The owner stream separates actual-project fit from whether the public register
entry visibly supports the label. Administrative fields remain hidden and
read-only.

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
candidate-0.4 categories. The current expected export schema lists only
candidate-0.4 checkbox columns 1, 2 and 5.

## Reporting

Scratch taxonomy-fit reporting includes Fit, Partial Fit, No Fit and Cannot
assess from register entry. Where useful, an assessable-fit distribution is
reported using only Fit, Partial Fit and No Fit. Cannot assess is reported with
register-sufficiency diagnostics; it is not counted as No Fit, a taxonomy
defect, or in the taxonomy-issue denominator. Taxonomy-issue frequencies use
only cases with Partial Fit or No Fit.

REDCap generates the three standard form-completion fields. The local validator
blocks unresolved conditional requirements and applies instrument-version-aware
response validation.
