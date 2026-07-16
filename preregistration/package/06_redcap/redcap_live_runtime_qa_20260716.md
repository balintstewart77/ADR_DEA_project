# UCL REDCap live-runtime QA — 2026-07-16

## Scope and data handling

Testing used synthetic data only in a UCL REDCap test project. Seven synthetic
assignment records were tested. The fresh export contained seven unique
assignment identifiers and seven rows, confirming one row per assignment.

No survey link, live project identifier, personal information, or response
export is recorded here or should be stored in Git.

## Initial defects and exact corrections

1. The Analytical Purposes field used `@MAXCHOICE=2`, which did not limit
   respondent selections in the UCL instance. It was replaced with
   `@MAXCHECKED=2`. The existing `@NONEOFTHEABOVE='8'` annotation and all other
   field settings were preserved.
2. The generic Scratch Coder explanatory note branched on
   `[sc_exposure] = '1'` as well as the evidence, confidence, and taxonomy
   triggers. The exposure condition was removed. The dedicated exposure
   description remains required when `[sc_exposure] = '1'`. The generic field
   note now reads: “Required for partial or insufficient evidence, low
   confidence, or a taxonomy concern.”

## Fresh-record export evidence

- On a fresh synthetic record, attempting a third Analytical Purpose did not
  persist; the export showed exactly two selected purpose checkbox fields.
- On a fresh synthetic exposure record, the dedicated exposure description was
  populated, the generic explanatory note remained blank, and the Scratch
  Coder survey completed successfully.
- Across the fresh seven-record export, seven unique assignment identifiers and
  seven rows confirmed one row per assignment.

The corrected candidate dictionary is `redcap-candidate-0.2`, SHA-256
`294c090dee0b5f7f0776415c64c6b9e0df723d3020c78fba5c1b69c69d174bb5`.

## QA status

Essential Scratch Coder runtime QA passed. Project Owner runtime QA remains
outstanding. No pilot or real assignments were created.
