# Candidate 0.7 source-to-live dictionary comparison — 2026-07-22

**Decision: PASSED under the enumerated narrow REDCap round-trip equivalence contract.**

The generated candidate and live REDCap export are not textually identical. They are semantically equivalent under three enumerated, narrowly verified REDCap round-trip transformations. No difference affects field identity, order, type, choices, branching logic, validation, required status, annotations after the verified single-space transformation, or coder-facing content.

## Inputs and dimensions

- Generated source: `preregistration/package/06_redcap/redcap_data_dictionary_candidate.csv`
- Source SHA-256: `1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc`
- Final live export: `preregistration/package/06_redcap/live_snapshots/redcap_live_dictionary_candidate_0.7_final_2026-07-22.csv`
- Live SHA-256: `bb1de2b9ea811afc8b0f23fcb489c1e01eb94d6677d45a64c273140532c5293f`
- Source dimensions: 150 data rows × 18 columns
- Live dimensions: 150 data rows × 18 columns
- Fields by form in both files: assignment_admin=50; coder_declaration=4; scratch_coder=16; project_owner=80
- Ordered 18-column headers match: Yes
- Variable and form order match: Yes

## Level 1 — raw strict equality

The strict comparison parses both files as UTF-8 CSV with an optional BOM, compares every ordered cell, and normalizes only CRLF or CR inside cells to LF. It performs no trimming, entity decoding, case folding, Unicode normalization, whitespace collapsing, field reordering, or choice reordering.

- Raw mismatching cells: **65**
- Strict textual equality: **No**

| Row | Variable | Column | Source value | Live value |
|---:|---|---|---|---|
| 2 | `assignment_id` | `Section Header` | `"Hidden assignment administration"` | `""` |
| 2 | `assignment_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 3 | `record_kind` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 4 | `review_stream` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 5 | `reviewer_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 6 | `source_record_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 7 | `official_project_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 8 | `project_title` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 9 | `datasets_used` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 10 | `sample_set` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 11 | `hard_stratum` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 12 | `validation_included` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 13 | `sample_status` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 14 | `display_order` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 15 | `assignment_batch` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 16 | `source_pop_ver` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 17 | `production_ver` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 18 | `instrument_ver` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 19 | `cluster_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 20 | `owner_resp_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 21 | `owner_project_id` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 22 | `owner_recruit_route` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 23 | `owner_sequence_pos` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 24 | `owner_invite_batch` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 25 | `owner_invite_date` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 26 | `owner_reminder_date` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 27 | `owner_contact_disp` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 28 | `owner_supp_reason` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 29 | `owner_response_status` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 30 | `prop_d01` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 31 | `prop_d02` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 32 | `prop_d03` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 33 | `prop_d04` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 34 | `prop_d05` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 35 | `prop_d06` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 36 | `prop_d07` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 37 | `prop_d08` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 38 | `prop_d09` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 39 | `prop_d10` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 40 | `prop_d11` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 41 | `prop_d12` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 42 | `prop_p01` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 43 | `prop_p02` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 44 | `prop_p03` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 45 | `prop_p04` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 46 | `prop_p05` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 47 | `prop_p06` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 48 | `prop_p07` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 49 | `prop_p08` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 50 | `prop_t01` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 51 | `prop_t02` | `Field Annotation` | `"@HIDDEN-SURVEY @READONLY"` | `" @HIDDEN-SURVEY @READONLY"` |
| 63 | `sc_domains` | `Field Annotation` | `"@NONEOFTHEABOVE='12'"` | `" @NONEOFTHEABOVE='12'"` |
| 64 | `sc_purposes` | `Field Annotation` | `"@MAXCHECKED=2 @NONEOFTHEABOVE='8'"` | `" @MAXCHECKED=2 @NONEOFTHEABOVE='8'"` |
| 76 | `po_d01_label` | `Field Label` | `"<strong>Labour Market &amp; Employment</strong><br>Research concerning work, employment, labour-market participation, and workforce dynamics. Includes wages and earnings; employment, unemployment, inactivity and underemployment; job quality; working hours, contracts, gig or platform work, and working conditions; labour supply and demand; occupational, sectoral and geographic mobility; workforce recruitment and retention; skills demand and mismatch; and transitions into, through, or out of work."` | `"<strong>Labour Market & Employment</strong><br>Research concerning work, employment, labour-market participation, and workforce dynamics. Includes wages and earnings; employment, unemployment, inactivity and underemployment; job quality; working hours, contracts, gig or platform work, and working conditions; labour supply and demand; occupational, sectoral and geographic mobility; workforce recruitment and retention; skills demand and mismatch; and transitions into, through, or out of work."` |
| 79 | `po_d02_label` | `Field Label` | `"<strong>Education &amp; Skills</strong><br>Research concerning education, learning, training, skills formation, and transitions through education systems. Includes early years, schools, colleges,  universities, qualifications, apprenticeships, admissions, attainment, attendance, teacher workforce issues, childcare, and education-to-work pathways."` | `"<strong>Education & Skills</strong><br>Research concerning education, learning, training, skills formation, and transitions through education systems. Includes early years, schools, colleges,  universities, qualifications, apprenticeships, admissions, attainment, attendance, teacher workforce issues, childcare, and education-to-work pathways."` |
| 82 | `po_d03_label` | `Field Label` | `"<strong>Health &amp; Social Care</strong><br>Research concerning health, illness, mortality, wellbeing, clinical outcomes, health services, public health,  mental health, social care, and care-system use. Includes NHS services, hospitals, GP care, palliative care,  maternity, morbidity, mortality where health is the research object, and adult or children&#x27;s social care."` | `"<strong>Health & Social Care</strong><br>Research concerning health, illness, mortality, wellbeing, clinical outcomes, health services, public health,  mental health, social care, and care-system use. Includes NHS services, hospitals, GP care, palliative care,  maternity, morbidity, mortality where health is the research object, and adult or children's social care."` |
| 85 | `po_d04_label` | `Field Label` | `"<strong>Crime &amp; Justice</strong><br>Research concerning crime, victimisation, public safety, offending, policing, courts, prisons, probation, sentencing, family justice, civil justice, reoffending, and criminal records."` | `"<strong>Crime & Justice</strong><br>Research concerning crime, victimisation, public safety, offending, policing, courts, prisons, probation, sentencing, family justice, civil justice, reoffending, and criminal records."` |
| 88 | `po_d05_label` | `Field Label` | `"<strong>Business &amp; Productivity</strong><br>Research concerning firms, business activity, industrial structure, innovation, productivity, entrepreneurship,  trade, exports, foreign direct investment, research and development, business support, and firm-level performance."` | `"<strong>Business & Productivity</strong><br>Research concerning firms, business activity, industrial structure, innovation, productivity, entrepreneurship,  trade, exports, foreign direct investment, research and development, business support, and firm-level performance."` |
| 91 | `po_d06_label` | `Field Label` | `"<strong>Poverty, Wealth &amp; Living Standards</strong><br>Research concerning material resources, economic hardship, household living standards, poverty, wealth, debt,  savings, benefits, deprivation, food security, cost of living, household income, and distribution of resources."` | `"<strong>Poverty, Wealth & Living Standards</strong><br>Research concerning material resources, economic hardship, household living standards, poverty, wealth, debt,  savings, benefits, deprivation, food security, cost of living, household income, and distribution of resources."` |
| 94 | `po_d07_label` | `Field Label` | `"<strong>Housing &amp; Planning</strong><br>Research concerning housing, homelessness, residential conditions, tenure, home ownership, planning systems,  neighbourhoods, gentrification, residential mobility, and place-based housing or planning interventions."` | `"<strong>Housing & Planning</strong><br>Research concerning housing, homelessness, residential conditions, tenure, home ownership, planning systems,  neighbourhoods, gentrification, residential mobility, and place-based housing or planning interventions."` |
| 97 | `po_d08_label` | `Field Label` | `"<strong>Migration &amp; Demographics</strong><br>Research concerning population structure, population change, migration, immigration,  population mobility, fertility, ageing, mortality as a demographic outcome,  census-based population analysis, and demographic composition."` | `"<strong>Migration & Demographics</strong><br>Research concerning population structure, population change, migration, immigration,  population mobility, fertility, ageing, mortality as a demographic outcome,  census-based population analysis, and demographic composition."` |
| 100 | `po_d09_label` | `Field Label` | `"<strong>Environment &amp; Agriculture</strong><br>Research concerning the natural environment, climate, climate adaptation or resilience, energy, agriculture, farming, land use, pollution, decarbonisation, environmental policy, domestic or industrial energy use, and environmental impacts of economic or social activity."` | `"<strong>Environment & Agriculture</strong><br>Research concerning the natural environment, climate, climate adaptation or resilience, energy, agriculture, farming, land use, pollution, decarbonisation, environmental policy, domestic or industrial energy use, and environmental impacts of economic or social activity."` |
| 103 | `po_d10_label` | `Field Label` | `"<strong>Public Finance &amp; Taxation</strong><br>Research concerning government revenue, taxation, tax compliance, tax credits, public expenditure,  public spending, fiscal transfers, business rates, tax reliefs, and fiscal policy."` | `"<strong>Public Finance & Taxation</strong><br>Research concerning government revenue, taxation, tax compliance, tax credits, public expenditure,  public spending, fiscal transfers, business rates, tax reliefs, and fiscal policy."` |
| 106 | `po_d11_label` | `Field Label` | `"<strong>Data Infrastructure &amp; Methodology</strong><br>Research primarily focused on the methods, measures, tools, classifications, linkage processes, data quality, survey design, statistical infrastructure, or dataset development needed to produce, improve, validate, or use research data."` | `"<strong>Data Infrastructure & Methodology</strong><br>Research primarily focused on the methods, measures, tools, classifications, linkage processes, data quality, survey design, statistical infrastructure, or dataset development needed to produce, improve, validate, or use research data."` |
| 139 | `po_t02_label` | `Field Label` | `"<strong>COVID-19 &amp; Pandemic</strong><br>A cross-cutting tag for projects where COVID-19, the COVID-19 pandemic, pandemic conditions, infection surveillance, vaccination, lockdowns, social distancing, pandemic-related public support, or pandemic consequences are a central condition or lens for the research question."` | `"<strong>COVID-19 & Pandemic</strong><br>A cross-cutting tag for projects where COVID-19, the COVID-19 pandemic, pandemic conditions, infection surveillance, vaccination, lockdowns, social distancing, pandemic-related public support, or pandemic consequences are a central condition or lens for the research question."` |

## Level 2 — narrow REDCap round-trip equivalence

| Accepted transformation | Exact predicate | Count |
|---|---|---:|
| Single leading annotation space | Column is `Field Annotation`; source does not begin with U+0020; live is exactly one U+0020 followed by the complete source value. No trim or other whitespace rule is used. | 52 |
| One-pass HTML character-entity decoding | Column is `Field Label`; form is `project_owner`; variable is `po_*_label`; `html.unescape(source)` exactly equals live; source/live markup-tag sequences are identical. No HTML stripping or textual normalization is used. | 12 |
| Hidden assignment header omitted | The sole `Section Header` difference is `assignment_id`: source is `Hidden assignment administration`, live is blank. It remains the first required text field on hidden `assignment_admin`; it has no branching logic and no branching expression references it. | 1 |

- Unaccepted raw differences: **0**
- Contract issues: **0**
- Residual mismatches: **0**

The `assignment_id` section-header omission is a presentation-only round-trip difference on the hidden Assignment Admin instrument. Source value: `Hidden assignment administration`; live value: blank. No coder-facing field, branching logic, instrument visibility rule, or stored data value depends on that header.

## Limits of equivalence

This finding does not claim byte identity or unrestricted semantic normalization. Only the three predicates above are accepted, only at the 65 listed cells. Any additional space, different column or variable, second decoding step, changed markup tag, wording change, reordered row/choice, or new missing header is residual and fails the verifier.

## Archive-state cross-check

- Archive verification passed: **Yes**
- Final data: 35 rows and 35 unique assignment IDs; all `pilot_and_qa_archi`; all `validation_included=0`; no `formal_validation` batch.
- Composition: 30 candidate-0.3 pilot records, 1 candidate-0.6 QA record, and 4 candidate-0.7 QA records.
- Pre/post audit membership is identical; the reassignment file has only `assignment_id` and `redcap_data_access_group`; the only migration change is DAG assignment.

## Freeze conclusion

The narrow verifier leaves zero residual mismatches and the archive-state cross-check passes. Candidate 0.7 may proceed to repository freeze subject to the required test suite and manifest/documentation checks. The raw source and live export remain textually different in exactly 65 fully enumerated cells.
