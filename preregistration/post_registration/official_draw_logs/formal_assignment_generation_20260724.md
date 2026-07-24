# Formal validation assignment generation — 24 July 2026

Formal coder assignments were generated deterministically from the completed official active sample. No reserve input was read or assigned, no REDCap connection or import occurred, and formal coding did not begin.

- Source draw completion commit: `6500c92148d97043a7826b684f5885127fd22814`
- Generation time: `2026-07-24T16:32:29+01:00` (`2026-07-24T15:32:29Z`)
- Builder: `scripts/generate_formal_validation_assignments.py`
- Builder SHA-256: `17404d9124ec135ceabfd4c27ab4a113c61de46bc724ccf82c1057dbab60d408`
- Method: independent `random.Random(seed).shuffle` over Record-ID-sorted active records
- Seeds: C01 `101`; C02 `102`; C03 `103`

## Aggregate result

- Active input records: 225 unique records
- C01 assignments: 225
- C02 assignments: 225
- C03 assignments: 225
- Total coder–record assignments: 675
- Assignment positions: exactly 1–225 once per coder
- Each active record: exactly once per coder
- Reserve assignments: 0

The restricted output directory is `preregistration_restricted/assignments/formal_validation_20260724/`. Exact paths, sizes and hashes are recorded in the canonical receipt and full artefact manifest. The coder-facing import omits sampling family, hard-case stratum, reserve status, model outputs, model labels, disagreement fields and coding-response fields.

`redcap_import_validation.csv` was generated for later controlled review. Its REDCap import status is `not_performed`; assignment import, formal validation coding, reserve activation and Project Owner recruitment remain unstarted.
