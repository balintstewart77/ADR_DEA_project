# Candidate 0.4 cross-cutting-tag and quotation-permission audit

Status: completed offline pre-migration audit; candidate 0.4 remains unfrozen, pre-recruitment and non-authoritative.

## Operational inclusion and data flow

The authoritative taxonomy is `taxonomy_data_dictionary.yaml`. The operational inclusion rule is: **include_in_prompt is true; layer is Cross-cutting tag; source status does not begin 'removed'**. It is implemented consistently in:

- `analysis/llm_theme_analysis_v3.py` (`_in_prompt_category`, `CROSS_CUTTING_TAGS`) for production prompt construction and output schema;
- `dashboard/taxonomy.py` (`_is_active`, `TAG_LABELS`) for dashboard values;
- `scripts/build_project_owner_redcap_candidate_0_3.py` (`taxonomy_groups`) inherited by candidate 0.4 for owner display and assignment generation;
- `scripts/build_project_owner_redcap_candidate_0_4.py` (`operational_tag_audit`) for the candidate guard, definitions and fixture;
- candidate field/export/branching specifications, synthetic fixture, validator and regression tests for analysis and QA.

The final operational set is exactly:

1. `Demographic disparities / equity tag` → `prop_t01_status`;
2. `COVID-19 & Pandemic` → `prop_t02_status`.

Lifecycle/provenance metadata deliberately differ:

- `Demographic disparities / equity tag`: `status=new v3.4`, `include_in_prompt=true`.
- `COVID-19 & Pandemic`: `status=active`, `include_in_prompt=true`.

Consequently, `status == active` is not and must not become the sole operational-inclusion test. No one-tag bug existed. Both tags are present in production instructions, outputs, dashboard data, owner records and both permanent REDCap review blocks. Every synthetic Project Review row carries both proposed statuses, and analytical completion requires both independent correctness and visibility judgements.

The frozen taxonomy and production prompt were inspected and deliberately left unchanged. No taxonomy category, label, output value, classification decision, assignment, sample or participant data was modified.

## Participant-facing definitions

The canonical Questionnaire main sections 5.1 and 5.2, Appendix A, and the REDCap values imported into `prop_t01_def` and `prop_t02_def` use the same full two-sentence definitions after whitespace normalisation. The descriptive displays `po_t01_display` and `po_t02_display` pipe the canonical label and definition immediately before the relevant proposed status and questions.

## Quotation-permission audit

`po_quote_permission` and any participant-facing equivalent are absent from the current candidate-0.4 dictionary, field specification, branching specification, expected export, synthetic fixture, analytical-completion rule, formatting audit, live-configuration guide and operational tests. The generator mentions the legacy variable only to remove it from the candidate-0.3 source rows; validators and tests mention it only as negative regression assertions. Historical candidate 0.1–0.3 artefacts, version history and audit logs remain unchanged or explicitly historical.

Quotation permission is not collected in REDCap. If the study team wishes to use a participant’s words, the participant will be contacted by email with the exact proposed quotation and the context in which it would appear. The quotation will be used only following written agreement.

The live-QA checklist requires an authorised administrator to confirm that the migrated PID 9149 Project Review contains no quotation-permission field. Migration and live QA were not executed, and recruitment remains blocked.
