# Pilot feedback log — 17 July 2026

Status: coder feedback closed and resolved; formal-instrument freeze and fresh
live REDCap runtime QA remain pending. The recorded diagnostic decisions were
implemented in candidate 0.4 and are retained in formal review candidate 0.6.
Candidate 0.6 has passed offline repository validation. The pilot was launched
under redcap-candidate-0.3.

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

## PILOT-003 — Shared post-pilot calibration before formal coding

| Item | Record |
| --- | --- |
| Issue ID | PILOT-003 |
| Date prepared | 2026-07-21 |
| Study stage | Pre-formal pilot calibration |
| Issue observed | The excluded pilot showed recurring differences in assigning a Domain from a dataset rather than the substantive research object; the threshold for additional Domains or Purposes; adding Descriptive Monitoring alongside a more specific operation; using Unclear from Register Entry independently by dimension; distinguishing residential mobility from general transport mobility; and recognising justified multi-domain cases without treating fewer labels as inherently preferable. |
| Evidence | Shared calibration examples use permanently excluded Record IDs 2019/015, 2021/038, 2021/056 and 2024/248. |
| Decision | Circulate one shared calibration note simultaneously to all three scratch coders. Do not require retrospective pilot recoding. Do not treat the note as an accuracy score or gold-standard answer key. Do not send coder-specific performance comparisons. Preserve independent judgement and legitimate disagreement during formal coding. |
| Classification of change | Clarification of existing coding rules and pre-formal calibration. No taxonomy structural change. No production-model change. No change to original pilot data. |
| Protocol implication | Describe the shared clarification process and qualitative model-direction check briefly in the active protocol candidate. All ten pilot records remain permanently excluded. |
| Model-direction check | The four shared readings were compared with archived Fable 5 and GPT-5.5 outputs. The direction was mixed: one matched both models, one matched Fable only, one matched GPT-5.5 only, and one was narrower than either model. See post_pilot_calibration_model_direction_audit.csv and the coding-clarification governance log. |
| Calibration document | DEA_post_pilot_shared_calibration_note.docx; SHA-256 ae2bae5169260f4e7e3bf10af5e158068d91be6e0a4860fc36b6612538d3c946; 198448 bytes. The DOCX is an unchanged project-lead input. |
| Document QA limitation | The calibration DOCX contains the four intended cases and no coder/model information, but does not itself explicitly state that the pilot was unscored, original responses must not be revised, disagreement remains expected, or formal coding remains independent. Those governance conditions are recorded here and in the protocol; any change to the DOCX requires manual project-lead action and a new hash. |
| Circulation evidence | Circulated simultaneously to all three scratch coders on 2026-07-21. The covering email explained that the pilot was not scored, pilot responses did not need revision, disagreement remained expected and informative, and formal coding should remain independent. |
| Feedback request | Remaining feedback was requested on wording, branching, required notes, conditional fields and technical usability by close of play on Wednesday 22 July 2026. All three coders responded before closure; their responses are not treated as formal approval or endorsement. |
| Feedback outcome | All three coders responded. No additional substantive taxonomy or instrument concerns were raised. One coder requested explicit guidance for projects where taxonomy fit cannot be judged because the public register entry lacks information, rather than because a taxonomy category is missing or inadequate. |
| Resolution | Candidate 0.6 adds point-of-use guidance to the formal taxonomy-fit field distinguishing Cannot assess from register entry from Partial Fit, No Fit and a missing-category diagnosis. The same distinction will be illustrated in the coder start pack. Candidate-0.3 pilot responses remain unchanged. |
| Remaining action | Add screenshot-based guidance to the coder start pack; complete fresh live REDCap runtime QA; freeze the formal instrument only after all remaining gates pass. |
| Resolver | Project lead, with repository verification of model-direction and provenance claims. |
| Affected artefacts | Active protocol candidate; REDCap version history; coding-clarification log; teaching-material and preregistration artefact manifests. |
| Status | Coder feedback resolved; formal-instrument freeze and live REDCap QA pending. |

The original 22 July deadline is retained as historical metadata. Feedback was
closed because all three coders responded, not because silence was treated as
approval.

## PILOT-004 — Point-of-use taxonomy-fit guidance

| Item | Record |
| --- | --- |
| Issue ID | PILOT-004 |
| Date recorded | 2026-07-21 |
| Study stage | Final pre-formal instrument feedback |
| Feedback | Coders reported no further substantive taxonomy or instrument concerns. One coder requested explicit confirmation of how to complete the revised taxonomy-fit field where a project cannot be classified easily because the public register entry lacks information, rather than because the taxonomy is missing or inadequately represents a category. |
| Resolution | Candidate 0.6 adds point-of-use help text to the formal scratch-coder `sc_taxonomy_fit` field distinguishing `Cannot assess from register entry` from Partial Fit, No Fit and a missing-category diagnosis. The same distinction will be illustrated with screenshot-based guidance in the coder start pack. |
| Classification of change | Operational clarification of the revised diagnostic instrument. No taxonomy change and no Domain or Analytical Purpose classification-rule change. |
| Historical treatment | Candidate-0.3 pilot responses remain unchanged. The clarification applies only to formal instrument candidate 0.6. |
| Invariants | Field name, radio type, answer codes and labels, field order, required status, branching, validation and export mappings remain unchanged. |
| Status | Implemented in repository candidate 0.6; offline validation passed; coder feedback resolved; coder-pack illustration, formal-instrument freeze and fresh live REDCap QA pending. |

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
