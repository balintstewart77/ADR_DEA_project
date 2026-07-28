# Coder-declaration REDCap import validation — 28 July 2026

## Scope and result

This report validates the separate, three-row import file
`redcap_import_coder_declarations_20260728.csv`.  It is a local preparation
artefact only: no REDCap connection, import, export, or other external service
was used.

The file contains one new, one-time governance declaration record for each
scratch coder.  It is separate from, and makes no change to, the existing
675-row formal coder–project assignment import.

| Reviewer | New opaque `assignment_id` | `redcap_data_access_group` |
|---|---|---|
| C01 | `ANXINVEY` | `c01` |
| C02 | `STMHTPXQ` | `c02` |
| C03 | `SEZJRBVZ` | `c03` |

The identifiers were generated locally as the first all-alphabetic eight
character Base32 prefix of SHA-256 namespace
`dea-declaration-import-20260728-v1:{counter}:{coder}`: counters C01=1,
C02=1 and C03=18.  They are neutral opaque identifiers, not numeric record
IDs and not derived from a project or hidden identifier.

## Authoritative artefacts inspected

1. `preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv`
   — frozen candidate-0.7 field names, forms, response codes and branching.
2. `preregistration/package/06_redcap/live_snapshots/redcap_live_dictionary_candidate_0.7_final_2026-07-22.csv`
   — PID 9128 final live dictionary snapshot.  The relevant variables, field
   types and response codes agree with the frozen dictionary.  The only
   observed differences were one empty versus populated section header and a
   leading space in hidden/read-only annotations; neither changes a field name
   or code.
3. `preregistration/package/06_redcap/live_qa/redcap_live_qa_coder_declaration_C02_candidate_0.7.csv`
   and `preregistration/package/06_redcap/live_snapshots/redcap_live_data_candidate_0.7_post_archive_2026-07-22.csv`
   — the tested `DECL-C02-QA` declaration-record pattern.
4. `preregistration/package/06_redcap/redcap_branching_validation_specification.yaml`,
   `redcap_expected_export_schema.csv`, and `redcap_field_response_specification.csv`
   — declaration frequency/branching and generated form-status codes.
5. `preregistration_restricted/assignments/formal_validation_20260724/redcap_import_validation.csv`
   and `formal_assignment_metadata.json` — the 675-row formal import and its
   C01/C02/C03 DAG mapping.
6. `preregistration/post_registration/redcap_import_logs/formal_assignment_import_20260724.md`
   and `preregistration/registration_records/osf_registration_8sn2j.yaml` —
   import and registration provenance.

## Import columns and exact values

The CSV has exactly these 13 columns, in this order:

```text
assignment_id,redcap_data_access_group,record_kind,review_stream,reviewer_id,validation_included,sample_status,assignment_batch,instrument_ver,assignment_admin_complete,cd_declaration,cd_nonconfirm_note,coder_declaration_complete
```

| Field | Imported value | Authority / meaning |
|---|---|---|
| `assignment_id` | opaque IDs above | `assignment_id` is the dictionary's required neutral identifier; collision checks below passed. |
| `redcap_data_access_group` | `c01`, `c02`, `c03` | REDCap structural import field; copied exactly from the formal 675-row import and its receipt mapping. |
| `record_kind` | `2` | Frozen dictionary and branching specification: Coder declaration. |
| `review_stream` | `1` | Frozen dictionary: Scratch coder. |
| `reviewer_id` | `C01`, `C02`, `C03` | Formal import reviewer IDs. |
| `validation_included` | `0` | Frozen yes/no field: excluded from validation analysis. |
| `sample_status` | `3` | Frozen dictionary: Review only (not active or reserve). |
| `assignment_batch` | `post_import_coder_declarations_20260728` | A distinct operational batch label; text field, so no coded value was inferred. |
| `instrument_ver` | `redcap-candidate-0.7` | Frozen/current scratch-coder version and tested declaration fixture value. |
| `assignment_admin_complete` | `2` | REDCap generated form status: Complete. |
| `cd_declaration` | blank | Coder must supply the required declaration response. |
| `cd_nonconfirm_note` | blank | Coder must supply only if they select Cannot confirm. |
| `coder_declaration_complete` | `0` | REDCap generated form status: Incomplete. |

`redcap_data_access_group`, `assignment_admin_complete`, and
`coder_declaration_complete` are valid REDCap structural/export fields;
all remaining columns are fields in the frozen dictionary.  No checkbox base
variable or descriptive field is included.

No project-specific field is present: there is no Record ID, official Project
ID, title, datasets-used entry, sample set, hard-case stratum, display order,
cluster, source-population/production metadata, proposal/model output, or
scratch/project-owner response field.  The two declaration-response fields are
present and blank in every row.

## Programmatic validation performed

- Standard CSV parsing found exactly three rows and reproduced the exact file
  bytes when re-serialised with the declared header and newline convention.
- Reviewer IDs are exactly `{C01, C02, C03}`; IDs are unique, eight-character,
  upper-case alphabetic opaque values.
- The formal import was parsed as 675 rows and provided the exact mapping
  `C01 -> c01`, `C02 -> c02`, `C03 -> c03`; each new row matches it.
- Every import column was checked against the frozen dictionary or the allowed
  REDCap structural-field set.  Every coded value was checked against its
  frozen allowed set.
- Each row was confirmed as Coder declaration / Scratch coder /
  validation-excluded / Review only / candidate-0.7, with Assignment Admin
  complete and Coder Declaration incomplete.
- All project-specific, proposal/model, display-order, checkbox-base,
  descriptive, scratch-response and project-owner-response fields were
  confirmed absent.  `cd_declaration` and `cd_nonconfirm_note` were confirmed
  blank.
- Before creation, all three candidate identifiers were searched across the
  repository's formal assignment, pilot, QA, reserve and declaration artefacts;
  there were zero occurrences.  They were also checked against all 675 formal
  `assignment_id` values.  Thus this repository evidence supports an import
  result of **3 new records and 0 updates to existing records**.

## File integrity

- CSV byte size: `506`
- CSV SHA-256: `7e4acf4a61708dda2bc8c51c4b3508f05d3d32ad6a4bbcb5f7b7da4058ccc131`

The formal 675-row import, sampling membership, coding assignments, project
metadata, taxonomy, protocol, frozen dictionary and production
classifications were not modified.
