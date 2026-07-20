# Pilot structural and instrument QC

Detected instrument version: `redcap-candidate-0.3`

- Expected assignments: 30
- Observed assignments: 30
- Unique assignments: 30
- Unique records: 10
- Unique coders: 3
- C01 assignments: 10
- C02 assignments: 10
- C03 assignments: 10
- Missing coder-record combinations: 0
- Duplicate coder-record combinations: 0
- Ambiguous mappings: 0
- Invalid response codes: 0
- Required-field failures: 0
- Fatal QC status: PASS

The mapping uses the explicit hidden `reviewer_id` field. Row order, timestamps,
display order, and response order are not used to infer coder identity.

Static instrument documentation marks administrative sample/model fields hidden and
read-only. Export contents alone cannot prove the historical live UI rendering.

## Findings

| Severity | Code | Record | Coder | Detail |
| --- | --- | --- | --- | --- |
| warning_interpretable | candidate_0_3_none_taxonomy_issue | 2021/103 | C02 | Historical candidate-0.3 recorded the known incoherent None issue option |
