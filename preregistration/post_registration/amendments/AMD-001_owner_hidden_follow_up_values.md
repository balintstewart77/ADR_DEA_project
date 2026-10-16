# AMD-001: values in hidden project-owner follow-up questions (§8.6)

| | |
|---|---|
| Date | 2026-10-16 |
| Protocol | v1.1 (frozen), §8.6 Project-owner review analysis; the same sentence appears in v1.0 |
| Resolves | DEV-004 (identified 2026-08-17) |
| Type | Correction of a statement about how the REDCap instrument behaves. Non-substantive: no outcome, derived variable, analysis population or analysis changes. |
| Made | After owner recruitment and data collection, before any substantive analysis of owner responses (DEV-006) |

## Text

**Original (§8.6):** "Raw retained values from fields hidden by a changed
parent response are preserved but excluded from derived completion and
analysis variables under the final branching state."

**Amended:** "When a changed parent response hides a field, REDCap deletes that
field's value, so no value from a hidden field is retained. Derived completion
and analysis variables are evaluated under the final branching state."

The rest of §8.6 is unchanged.

## Reason

Controlled live testing of the owner instrument in REDCap (PID 9149) on
17 August 2026 showed that REDCap deletes a child field's value, without
warning, when the parent response changes so that the child is hidden (DEV-004).
The protocol had assumed the value would be retained.

## Effect

None on any derived variable or result. Values in hidden fields were to be
excluded from derived variables in any case, and derived variables were always
to be evaluated under the final branching state. What is lost is the record of
answers an owner abandoned by changing a parent response; no preregistered or
planned analysis used them.

The owner analysis implementation (`analysis/validation/owner.py`) reads final
values only and uses no hidden-field values, so it needs no change.

## Verification

The closing owner export of 13 October 2026 (SHA-256
792afed9d6e6b6c0d45be03aa690526a534d43f15bc18cb6b7b6e930617ad169) was checked
against the frozen owner data dictionary of 24 August 2026 before any
substantive owner analysis. Of 319 populated values across the 47 branched
fields (calculated and descriptive fields excluded), none lies in a field that
is hidden under the final branching state. Only populated-field status and the
branching conditions were evaluated; the check reports counts only.
