# Formal validation assignment import — 24 July 2026

The frozen formal-validation coder assignments were imported into REDCap using the manual REDCap Data Import Tool. This is an administrative record of a completed import and administrator-side verification. No REDCap connection or export was made from this repository, and formal validation coding has not begun.

## Import details

- REDCap project PID: `9128`
- Import method: manual REDCap Data Import Tool
- Importing username: `sejkbst` (Balint Stewart)
- Import completed locally: `2026-07-24T17:03:00+01:00`
- Timezone: Europe/London
- Corresponding UTC timestamp: `2026-07-24T16:03:00Z`
- Source file: `preregistration_restricted/assignments/formal_validation_20260724/redcap_import_validation.csv`
- Source SHA-256: `ed5a1c66e4dfa1037dfae2eb166a20fcca12ae18e77ca2b298bd5152252f5ae5`
- Generation commit for the source file: `d732b83f56b4f2b3b00f54f7f97266c3f4513d14`

## Import result

- Source rows: 675
- Imported as new records: 675
- Existing records updated or overwritten: 0
- Assignments imported: C01 225, C02 225, C03 225
- Existing pilot/QA records retained: 35
- Total REDCap records after import: 710

Row arithmetic: 225 + 225 + 225 = 675 imported; 675 + 35 = 710 total.

## Administrator-side verification performed

- The import file matched the frozen SHA-256 above.
- All 675 rows were accepted as new records; none updated or overwrote an existing record.
- Each coder Data Access Group (DAG) contains 225 formal records: `c01` 225, `c02` 225, `c03` 225.
- The existing pilot/QA DAG retained 35 records.
- Each coder account was assigned to its corresponding DAG.
- Coder user rights were checked and remained restricted.
- The administrator account had no DAG assignment and retained project-wide access.
- The Formal Coding dashboard initially showed no records because its filter required the unpopulated field `[sample_status] = '1'`.
- The dashboard filter was corrected by removing that condition.
- The corrected dashboard displays the formal validation batch.
- Records also remain visible in REDCap's Default dashboard, which is normal and does not indicate duplication.
- Access separation is provided by the DAGs, not by dashboard membership.

The effective Formal Coding dashboard filter is based on `[assignment_batch] = 'formal_validation_20260724'`. It may also contain valid conditions on populated fields such as `record_kind`, `review_stream` and `validation_included`; the exact full filter is not asserted here.

## Restricted-user QA status

- Full login testing through each actual restricted coder account was **not** performed.
- Administrator-side rights, DAG and record-count checks **were** performed.
- First-login confirmation from each coder is **required** before they begin coding.
- Coders will be instructed not to start if anything appears missing, unexpected, or visible when it should not be.

Restricted-user live QA is therefore explicitly recorded as not completed and not passed.

## Operational state after import

- `formal_assignments_generated = true`
- `formal_assignment_import_completed = true`
- `formal_validation_coding_started = false`
- `reserve_activated = false`
- `project_owner_recruitment_started = false`

Records being present in REDCap does not mean coding has started. No screenshots or confidential REDCap exports are included in Git.
