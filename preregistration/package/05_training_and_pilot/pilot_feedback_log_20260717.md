# Pilot feedback log — 17 July 2026

Status: open pending completion of the excluded pilot, debrief, and formal log
closure. The recorded diagnostic decisions were implemented in candidate 0.4
and are retained in the v0.11-aligned candidate 0.5; live runtime QA remains
pending. The pilot was launched under redcap-candidate-0.3.

## PILOT-001 — Taxonomy fit cannot be assessed under insufficient evidence

| Item | Record |
| --- | --- |
| Issue ID | PILOT-001 |
| Date observed | 2026-07-17 |
| Study stage | Shared training and pilot launch |
| Issue observed | The register entry is insufficient to identify the project domain or purpose. The existing Fit / Partial Fit / No Fit choices force a coder either to claim that the taxonomy fits or to misclassify an evidence problem as a taxonomy failure. |
| Example exposing it | AMPHoRA, Record ID 2021/103 |
| Coder feedback or group discussion | No Fit is inappropriate because the underlying project is not sufficiently understood. The form needs a way to state that taxonomy fit cannot be assessed from the public entry. |
| Proposed resolution | Add a distinct scratch-coder response for an evidence limitation, without treating it as a taxonomy defect. |
| Final decision | Add stored choice 4, Cannot assess from register entry to sc_taxonomy_fit. Do not add it to po_taxonomy_fit: repository inspection confirms that the owner stream separately assesses public-entry sufficiency and actual-project taxonomy fit using owner knowledge. |
| Affected fields/files | sc_taxonomy_fit; its branching, validation, export and reporting specifications; active protocol candidate; post-pilot coder/trainer/debrief materials |
| Classification-rule change or diagnostic-instrument change | Diagnostic-instrument clarification only |
| Implementation version | redcap-candidate-0.4 |
| Status | Implemented in repository candidate; live runtime QA pending |
| Impact on pilot data | Candidate-0.3 pilot responses remain unchanged and are interpreted under the candidate-0.3 schema. |
| Impact on formal coding | Candidate 0.4 applies only after all pilot responses are complete, candidate-0.3 pilot data are exported and archived, repository validation passes, and candidate-0.4 live runtime QA passes. |

Not changed: Research Domain, Analytical Purpose or tag taxonomy; LLM outputs;
sample design.

## PILOT-002 — Redundant and incoherent taxonomy-issue options

| Item | Record |
| --- | --- |
| Issue ID | PILOT-002 |
| Date observed | 2026-07-17 |
| Study stage | Shared training and pilot launch |
| Issue observed | Too broad and Too narrow duplicate broader diagnostic concepts, while None is incoherent in a field conditional on Partial Fit or No Fit. |
| Example exposing it | Shared scratch-coder review of taxonomy-issue branching and response choices |
| Coder feedback or group discussion | Too narrow is subsumed by a missing or inadequately represented category. Too broad is subsumed by ambiguous or overlapping category boundaries. Other remains necessary for uncaptured taxonomy problems. |
| Proposed resolution | Consolidate both issue fields while retaining their established stored-code identities. |
| Final decision | Retain 1, Missing or inadequately represented category; 2, Ambiguous or overlapping category boundaries; and 5, Other taxonomy problem. Retire codes 3, 4 and 6 without reuse or renumbering. |
| Affected fields/files | sc_tax_issue, po_tax_issue; their branching, validation, export and reporting specifications; active protocol candidate; post-pilot coder/trainer/debrief materials |
| Classification-rule change or diagnostic-instrument change | Diagnostic-instrument simplification only |
| Implementation version | redcap-candidate-0.4 |
| Status | Implemented in repository candidate; live runtime QA pending |
| Impact on pilot data | Archived candidate-0.3 responses may contain retired codes and remain decodable using the historical version mapping. No old response is mapped or destructively recoded. |
| Impact on formal coding | Candidate-0.4 formal responses accept only stored codes 1, 2 and 5; the issue field is required only for Partial Fit or No Fit, and Other taxonomy problem requires an explanatory note. |

## Before-edit provenance

These hashes record the artefacts inspected before any post-training version was
created:

| Artefact | SHA-256 |
| --- | --- |
| Candidate-0.3 REDCap dictionary | d690ec4a882ff8a7eddc9c227952e09db0af51992948e5e1f8731dc5d2e891c7 |
| Active protocol candidate Validation_Protocol_PreReg_v0.9.docx | 1ff1add4fdcddaa6b55d19370cd16b88cbc128b2688466d897ee579390e5285a |
| As-delivered coder handout DEA_coder_training_handout_v2.docx | ca41f969bbc633e33a52f6bd16b6020381df56cd917c50d7cd57f14f245bce26 |
| As-delivered trainer guide DEA_trainer_handout_v1.docx | dd8956c75e6f2165377e2dea6eef4cbb4ba71220aeaaf3084840ae8e78dcbb74 |
| As-delivered trainer pilot-debrief reference | 9e541eb0b6fc2a874cdcb98c53f6d0ea0ceae3d18bb40066b26e3867219f551e |
