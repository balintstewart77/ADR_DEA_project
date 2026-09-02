# Frozen June register entity-variation audit

## 1. Scope and provenance

This retrospective audit applies the current deterministic dashboard reconciliation machinery to the frozen June study population: **1,308 retained records** (**1,304 official Project IDs**). The entity-analysis input is the frozen cleaned `Datasets Used` and `Researchers` evidence, not the live register. Reconciliation burden means an exact parsed raw entity differs from its production canonical representation; it does not imply error. The narrower explicit-error subset includes only operations labelled corrective by existing code, match metadata, tests, or comments. Completeness and undetected errors are excluded.

- Frozen cleaned SHA-256: `a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1`
- Frozen raw Git/LF SHA-256: `abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d`
- Preregistered raw Windows/CRLF SHA-256: `fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892`
- Repository HEAD: `7f500898db5e48b36cc76784e3774de28959f6d1`
- Audit timestamp (UTC): `2026-09-02T07:48:32.446438+00:00`

The preregistered source hash refers to the Windows/CRLF representation; the repository stores the same frozen logical CSV in Git/LF form, as established by the prior provenance diagnostic. This audit verified the Git/LF hash and did not reconstruct or write a CRLF file.

## 2. Summary metrics

All rates are percentages. Each record-level denominator is the number of unique retained Record IDs with at least one evaluable occurrence for that row's field; it is not automatically 1,308.

| field | evaluable_records | affected_records | affected_record_rate | total_occurrences | changed_occurrences | changed_occurrence_rate | distinct_raw_values | distinct_canonical_values | canonical_values_with_multiple_raw_variants | explicit_error_records | explicit_error_record_rate | explicit_error_rate_identifiable | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| datasets | 1307 | 1189 | 90.97% | 3350 | 2639 | 78.78% | 701 | 347 | 126 | 55 | 4.21% | True | Current downstream parser/canonicaliser; explicit-error subset is conservative and rule-labelled. |
| organisations | 1299 | 619 | 47.65% | 1839 | 761 | 41.38% | 409 | 281 | 75 | 12 | 0.92% | True | Live institution parser; explicit-error subset uses parser_cleanup and aliases explicitly labelled as typos. |
| researcher names | 1306 | NA | NA | 3997 | NA | NA | 2478 | NA | NA | NA | NA | False | Reconciliation rate not measurable: production parser never merges similar person names; occurrence count is person_candidate parser output. |
| explicit malformed/text corrections | 1308 | 66 | 5.05% | 5189 | 78 | 1.50% | NA | NA | NA | 66 | 5.05% | True | Conservative union of explicitly labelled corrective rules across dataset/provider and institution occurrences. |

## 3. Dataset variation

- Evaluable records: **1,307**.
- Records with at least one changed dataset occurrence: **1,189/1,307 (90.97%)**.
- Parsed occurrences: **3,350**; changed **2,639 (78.78%)**; unchanged **711**.
- Distinct parsed raw forms: **701**; distinct canonical forms: **347**; canonical forms receiving more than one raw form: **126**.
- Match types: `alias` 2,409, `compound_or_multi_dataset` 2, `identity` 513, `normalised_format` 426. Unresolved occurrences: **0**; review-flagged occurrences: **2**.
- Distribution of raw variants per canonical form (`variant_count: canonical_forms`): `1: 221`, `2: 45`, `3: 29`, `4: 17`, `5: 14`, `6: 9`, `7: 4`, `8: 1`, `9: 1`, `10: 4`, `11: 1`, `15: 1`.

Canonical forms with the largest observed variant burden (first 20 rows of the complete canonical-level CSV):

| rank | canonical_value | affected_records | total_occurrences | n_distinct_raw_variants | existing_match_types |
| --- | --- | --- | --- | --- | --- |
| 1 | Business Structure Database (BSD) | 281 | 283 | 7 | alias |
| 2 | Annual Business Survey (ABS) | 230 | 231 | 10 | alias; identity |
| 3 | Annual Survey of Hours and Earnings (ASHE) | 200 | 205 | 11 | alias |
| 4 | Annual Population Survey (APS) | 173 | 183 | 9 | alias; identity |
| 5 | Longitudinal Education Outcomes (LEO) | 116 | 119 | 15 | alias |
| 6 | Business Enterprise Research and Development (BERD) | 81 | 83 | 10 | alias; identity |
| 7 | UK Innovation Survey (UKIS) | 79 | 79 | 4 | alias |
| 8 | Business Register and Employment Survey (BRES) | 65 | 67 | 6 | alias |
| 9 | Labour Force Survey (LFS) | 61 | 81 | 4 | alias; identity |
| 10 | ONS Longitudinal Study (LS) | 54 | 57 | 7 | alias; identity |
| 11 | Labour Force Survey Person | 49 | 68 | 7 | identity; normalised_format |
| 12 | Annual Respondents Database X | 41 | 62 | 10 | alias |
| 13 | Business Insights and Conditions Survey (BICS) | 40 | 41 | 7 | alias; identity |
| 14 | Education and Child Health Insights from Linked Data (ECHILD) | 40 | 41 | 4 | alias; identity |
| 15 | Crime Survey for England and Wales (CSEW) | 39 | 41 | 3 | alias; identity |
| 16 | Living Costs and Food Survey (LCF) | 39 | 39 | 4 | alias |
| 17 | Labour Force Survey Household | 36 | 48 | 8 | identity; normalised_format |
| 18 | Annual Survey of Hours and Earnings Longitudinal | 36 | 42 | 10 | alias |
| 19 | Longitudinal Small Business Survey (LSBS) | 34 | 35 | 4 | alias; identity |
| 20 | Understanding Society | 32 | 58 | 4 | alias; identity; normalised_format |

Dataset-family grouping was not counted as name reconciliation. Provider canonicalisation is retained as a separate parser stage and contributes only where an existing provider rule is explicitly corrective.

For stage transparency, **3,343** parsed dataset occurrences had a nonblank provider representation and **3,092** of those differed from the final production provider representation. These provider-stage changes are not included in the dataset-name changed-occurrence numerator.

## 4. Organisation variation

- Evaluable records: **1,299**.
- Records with at least one changed institution occurrence: **619/1,299 (47.65%)**.
- Production-parser occurrences: **1,839**; changed **761 (41.38%)**; unchanged **1,078**.
- Distinct parsed raw forms: **409**; distinct canonical forms: **281**; canonical forms receiving more than one raw form: **75**.
- Match statuses: `alias` 624, `identity` 1,203, `parser_cleanup` 12. Unclassified-sector/review-flagged occurrences: **23**.
- Distribution of raw variants per canonical form (`variant_count: canonical_forms`): `1: 206`, `2: 49`, `3: 12`, `4: 9`, `5: 2`, `6: 1`, `9: 1`, `12: 1`.

Canonical organisations with the largest observed variant burden (first 20 rows of the complete canonical-level CSV):

| rank | canonical_value | affected_records | total_occurrences | n_distinct_raw_variants | existing_match_types |
| --- | --- | --- | --- | --- | --- |
| 1 | University College London (UCL) | 120 | 120 | 12 | alias; identity; parser_cleanup |
| 2 | London School of Economics and Political Science (LSE) | 97 | 97 | 9 | alias; parser_cleanup |
| 3 | Institute for Fiscal Studies (IFS) | 67 | 67 | 3 | alias; identity |
| 4 | Office for National Statistics (ONS) | 47 | 47 | 3 | alias |
| 5 | King's College London (KCL) | 32 | 32 | 5 | alias |
| 6 | University of Manchester | 25 | 43 | 4 | alias; identity |
| 7 | Ipsos | 22 | 27 | 5 | alias |
| 8 | University of Edinburgh | 18 | 31 | 2 | alias; identity |
| 9 | National Institute for Economic and Social Research (NIESR) | 15 | 15 | 2 | alias; identity |
| 10 | Public Health Wales (PHW) | 15 | 15 | 1 | identity |
| 11 | National Foundation for Education Research (NFER) | 14 | 14 | 2 | alias |
| 12 | London School of Hygiene and Tropical Medicine (LSHTM) | 13 | 13 | 1 | identity |
| 13 | Durham University | 11 | 19 | 2 | alias |
| 14 | Cardiff University | 9 | 37 | 3 | alias; identity |
| 15 | Queen Mary University of London | 9 | 16 | 6 | alias; identity |
| 16 | City, University of London | 9 | 11 | 4 | alias |
| 17 | Greater London Authority (GLA) | 9 | 9 | 1 | alias |
| 18 | Aston University | 8 | 14 | 4 | alias |
| 19 | University of the West of England | 8 | 10 | 3 | alias; identity |
| 20 | Competition and Markets Authority (CMA) | 8 | 8 | 1 | identity |

The live institution parser emits at most one occurrence of a given canonical institution per retained record. Counts therefore follow production output semantics rather than reconstructing duplicate mentions discarded by that parser.

The institution `identity` match status does not always mean exact string identity: approved display acronyms can be appended after status assignment. Changed-occurrence counts therefore use exact parsed-raw versus final-canonical inequality, as defined, rather than treating the match-status label as the change flag.

## 5. Researcher-name variation

`researcher_name_reconciliation_rate_not_measurable = true`. No live dashboard person-name canonicaliser was found. The production validation-frame parser (`analysis.validation.owner_sampling_frame.parse_researcher_field`) standardises typography, removes exact within-field duplicates, and explicitly never merges similar-looking names. It yielded **3,997** conservative `person_candidate` outputs across **1,302** records, with **2,478** distinct displayed strings, from **1,306** nonblank researcher fields. These are descriptive parser counts, not a reconciliation numerator or rate. No researcher variant CSV was created.

## 6. Explicit malformed/error corrections

The conservative explicitly corrective subset affects **66/1,308 (5.05%)** evaluable records and **78/5,189 (1.50%)** dataset/institution entity occurrences. A correction occurrence is counted once even if more than one named corrective rule applies.

| rank | rule_id | corrected_or_canonical_value | affected_records | affected_occurrences | field |
| --- | --- | --- | --- | --- | --- |
| 1 | provider_repeated_word_correction | SAIL Databank | 49 | 53 | datasets |
| 2 | institution_parser_cleanup | London School of Economics and Political Science (LSE) | 2 | 2 | organisations |
| 3 | institution_parser_cleanup | University College London (UCL) | 2 | 2 | organisations |
| 4 | provider_spelling_correction_01 | Office for National Statistics (ONS) | 1 | 2 | datasets |
| 5 | dataset_leading_character_artifact | Integrated Data Service | 1 | 1 | datasets |
| 6 | dataset_spelling_correction_01 | Business Enterprise Research and Development (BERD) | 1 | 1 | datasets |
| 7 | dataset_spelling_correction_02 | MoJ Data First Probation | 1 | 1 | datasets |
| 8 | dataset_truncation_correction_01 | Annual Survey of Hours and Earnings linked to Census 2011 | 1 | 1 | datasets |
| 9 | provider_spelling_correction_02 | Northern Ireland Statistics and Research Agency (NISRA) | 1 | 1 | datasets |
| 10 | institution_parser_cleanup | Academy of Medical Sciences | 1 | 1 | organisations |
| 11 | institution_parser_cleanup | Centre for Economic and Business Research (CEBR) | 1 | 1 | organisations |
| 12 | institution_parser_cleanup | Health Foundation | 1 | 1 | organisations |
| 13 | institution_parser_cleanup | Imperial College London | 1 | 1 | organisations |
| 14 | institution_parser_cleanup | Ministry of National Education, Republic of Türkiye | 1 | 1 | organisations |
| 15 | institution_parser_cleanup | University of Leeds | 1 | 1 | organisations |
| 16 | institution_parser_cleanup | University of Reading | 1 | 1 | organisations |
| 17 | institution_parser_cleanup | University of Warwick | 1 | 1 | organisations |
| 18 | institution_reviewed_typo_alias | Equality and Human Rights Commission (EHRC) | 1 | 1 | organisations |
| 19 | institution_reviewed_typo_alias | Institute for Employment Studies (IES) | 1 | 1 | organisations |
| 20 | institution_reviewed_typo_alias | London School of Economics and Political Science (LSE) | 1 | 1 | organisations |
| 21 | institution_reviewed_typo_alias | Sentencing Academy | 1 | 1 | organisations |
| 22 | institution_reviewed_typo_alias | Teesside University | 1 | 1 | organisations |
| 23 | institution_reviewed_typo_alias | University of York | 1 | 1 | organisations |

Routine line-ending, whitespace, BOM, line-wrap, generic case, and zero-width-character hygiene is excluded. The prior 103 LF/CRLF-sensitive dataset-cell differences are not counted.

## 7. Cross-field overlap

Across datasets and organisations, **1,236/1,308 (94.50%)** records evaluable in at least one reconciled field contain at least one detected variation. **664** are affected in exactly one field and **572** in both fields. These are set unions of Record IDs, not sums of field numerators.

## 8. Methods/provenance notes

| field | parser | canonicaliser | reference/version | live dashboard |
| --- | --- | --- | --- | --- |
| datasets | `dashboard.dataset_normalisation.iter_dataset_entries` (via `parse_datasets`) | `describe_dataset_normalisation`; `normalise_dataset_name`; provider stage `normalise_provider_name` | hard-coded deterministic rules; module SHA-256 `6e8e13a73e6f6cbe0ebb6256c4e32d5601bc6c198906952526f60f3fd793eff1` | Yes |
| organisations | `dashboard.institution_normalisation.parse_institutions_with_metadata` (same internal parser as `parse_institutions`) | `describe_institution_normalisation` | hard-coded aliases/sectors; module SHA-256 `c2ff06a5981f827b8695aab2198226b939da2f51dcdb3122b52626db02965662` | Yes |
| researcher names | `analysis.validation.owner_sampling_frame.parse_researcher_field` | none for person identity | module SHA-256 `06fe96265f1d613374788a2366c3f50bae8c9c33a8ba847f6e480571a255338b` | No |

`analysis/register_reference.yaml` is used by later register-property derivation, not by the dataset-name or institution-name canonicalisers measured here. Dataset family/collection assignment is outside the name-reconciliation counts.

Denominators: a record is evaluable only if the relevant production parser emits at least one entity occurrence. A changed occurrence requires exact inequality between the parser-preserved raw entity and canonical entity. Raw distinct forms are counted before canonicalisation, without audit-side pre-normalisation.

### Disclosure component STOP

The archived files `baseline_reserve.csv` and `hard_reserve.csv` named and hash-bound by production sampling code are absent from this worktree. Reserve membership could therefore not be obtained through the authorised path. Example generation and the individual non-canonical raw-form ranking were stopped. No observed raw string is emitted in this report or any CSV/JSON output; canonical-level aggregate counts retain all 1,308 records.

## 9. Limitations

- The results quantify variation detected by current deterministic reconciliation, not total true error or register completeness.
- Canonicalisation includes legitimate aliases and formatting conventions; it is not generally an error indicator.
- Explicit-error figures are a conservative identifiable subset, not an estimate of all malformed register content.
- Researcher identity variation is not measurable without person-resolution logic that production does not provide.
- The frozen June population and current live register are conceptually distinct.
- Observed raw variants are withheld because reserve-only disclosure could not be assessed.

## 10. Verification

- Frozen cleaned hash matched; the file had exactly 1,308 rows, 1,308 unique nonblank Record IDs, and 1,304 unique official Project IDs.
- Frozen raw Git/LF hash matched; the preregistered CRLF hash was retained as provenance metadata.
- Every analysed occurrence belonged to a frozen Record ID.
- Every dataset and institution mapping was re-run and asserted through the current production canonicaliser; the audit introduced no alias or matching rule.
- Record numerators used unique Record-ID sets; cross-field counts used unions.
- Blank values were excluded from error counts; the 103 LF/CRLF issue was excluded.
- Relevant existing tests passed: **72 tests and 189 subtests** across dataset normalisation, institution normalisation, and the researcher parser.
- No classification output, coder response, owner response, adjudication output, or disagreement status was read.
- No web, API, or LLM call was made. No commit or push was performed.


## Reconciliation-burden decomposition

The decomposition below preserves the original audit's exact-string change definition and native production match statuses. Category-level record counts can overlap because one record can contain changed occurrences of more than one type; they must not be summed.

### Dataset decomposition

| Existing transformation/match type | Changed occurrences | % of 2,639 changed | Unique records |
| --- | ---: | ---: | ---: |
| alias | 2211 | 83.78 | 1108 |
| compound_or_multi_dataset | 2 | 0.08 | 2 |
| normalised_format | 426 | 16.14 | 252 |

The native-status table reconciles to **3,350 total**, **2,639 changed**, and **711 unchanged** dataset occurrences. Native `alias` comprises 2,409 occurrences (2,211 changed; 198 unchanged), `identity` 513 (all unchanged), `normalised_format` 426 (all changed), and `compound_or_multi_dataset` 2 (both changed). Dataset-family, collection, and linked-product grouping account for **zero** occurrences in this numerator: those later grouping operations were not included in the original audit. Native `alias` and `normalised_format` labels are retained because production metadata does not support a clean three-way split between legitimate naming, formatting, and explicit correction. `compound_or_multi_dataset` is retained as an implementation label without further semantic interpretation. The conservative correction subset is reported separately below.

Among the **1,189** affected dataset records, **1,017** contain exactly one changed-occurrence transformation type and **172** contain two or more.

### Organisation decomposition

| Existing transformation/match type | Changed occurrences | % of 761 changed | Unique records |
| --- | ---: | ---: | ---: |
| alias | 514 | 67.54 | 456 |
| identity_with_display_change | 235 | 30.88 | 219 |
| parser_cleanup | 12 | 1.58 | 7 |

The native-status table reconciles to **1,839 total**, **761 changed**, and **1,078 unchanged** organisation occurrences. Native `alias` comprises 624 occurrences (514 changed; 110 unchanged), `identity` 1,203 (235 changed; 968 unchanged), and `parser_cleanup` 12 (all changed). Of the native `identity` occurrences, **235**, across **219** records, are `identity_with_display_change`, representing **30.88%** of all 761 changed organisation occurrences. Existing deterministic function behaviour attributes **235** to approved acronym addition and **0** to other deterministic display construction. This is display standardisation, not an error classification.

Among the **619** affected organisation records, **556** contain exactly one transformation type and **63** contain two or more.

### Conservative explicit corrections

| Field | Explicit correction occurrences | % of field occurrences | Affected records | % of field records |
| --- | ---: | ---: | ---: | ---: |
| datasets | 60 | 1.79 | 55 | 4.21 |
| organisations | 18 | 0.98 | 12 | 0.92 |
| combined union | 78 | 1.50 | 66 | 5.05 |

The 66-record union comprises **54** records with dataset corrections only, **11** with organisation corrections only, and **1** with corrections in both fields. These mutually exclusive groups sum to 66.

Excluding the dominant recurring provider form leaves **18/1,308 (1.38%)** records with at least one explicit deterministic correction. The dominant form occurs in 49 records, of which **1** also contain another explicit correction; this overlap is why subtracting 49 from 66 would not give the remaining numerator. The remaining subset contains **25** correction occurrences.

| Field | Existing correction mechanism | Occurrences | Records | % of 78 explicit corrections |
| --- | --- | ---: | ---: | ---: |
| datasets | provider_repeated_word_correction | 53 | 49 | 67.95 |
| organisations | institution_parser_cleanup | 12 | 7 | 15.38 |
| organisations | institution_reviewed_typo_alias | 6 | 6 | 7.69 |
| datasets | provider_spelling_correction_01 | 2 | 1 | 2.56 |
| datasets | dataset_leading_character_artifact | 1 | 1 | 1.28 |
| datasets | dataset_spelling_correction_01 | 1 | 1 | 1.28 |
| datasets | dataset_spelling_correction_02 | 1 | 1 | 1.28 |
| datasets | dataset_truncation_correction_01 | 1 | 1 | 1.28 |
| datasets | provider_spelling_correction_02 | 1 | 1 | 1.28 |

The broad reconciliation-burden rates measure how frequently observed register forms require deterministic standardisation to reach the dashboard's canonical representation. They include legitimate aliases and display standardisation and should not be interpreted as error rates. The conservative explicit-correction subset identifies only transformations whose existing deterministic rules are clearly corrective or malformed; it is not a complete or externally validated error rate.

### Concentration and recurrence of explicit corrections

The original explicit subset contains dataset-name, dataset-provider, and organisation corrections. Provider targets remain labelled `provider` below rather than being presented as dataset-name entities.

Top affected canonical entities by absolute correction burden (up to ten per field):

| rank | field | component | canonical entity | total occurrences | corrections | correction rate (%) | records | malformed variants |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | datasets | provider | SAIL Databank | 68 | 53 | 77.94 | 49 | 1 |
| 2 | datasets | provider | Office for National Statistics (ONS) | 2619 | 2 | 0.08 | 1 | 1 |
| 3 | datasets | dataset_name | Annual Survey of Hours and Earnings linked to Census 2011 | 24 | 1 | 4.17 | 1 | 1 |
| 4 | datasets | dataset_name | Business Enterprise Research and Development (BERD) | 83 | 1 | 1.20 | 1 | 1 |
| 5 | datasets | dataset_name | Integrated Data Service | 1 | 1 | 100.00 | 1 | 1 |
| 6 | datasets | dataset_name | MoJ Data First Probation | 7 | 1 | 14.29 | 1 | 1 |
| 7 | datasets | provider | Northern Ireland Statistics and Research Agency (NISRA) | 39 | 1 | 2.56 | 1 | 1 |
| 1 | organisations | organisation | London School of Economics and Political Science (LSE) | 97 | 3 | 3.09 | 3 | 3 |
| 2 | organisations | organisation | University College London (UCL) | 120 | 2 | 1.67 | 2 | 2 |
| 3 | organisations | organisation | Academy of Medical Sciences | 1 | 1 | 100.00 | 1 | 1 |
| 4 | organisations | organisation | Centre for Economic and Business Research (CEBR) | 1 | 1 | 100.00 | 1 | 1 |
| 5 | organisations | organisation | Equality and Human Rights Commission (EHRC) | 2 | 1 | 50.00 | 1 | 1 |
| 6 | organisations | organisation | Health Foundation | 2 | 1 | 50.00 | 1 | 1 |
| 7 | organisations | organisation | Imperial College London | 17 | 1 | 5.88 | 1 | 1 |
| 8 | organisations | organisation | Institute for Employment Studies (IES) | 1 | 1 | 100.00 | 1 | 1 |
| 9 | organisations | organisation | Ministry of National Education, Republic of Türkiye | 1 | 1 | 100.00 | 1 | 1 |
| 10 | organisations | organisation | Sentencing Academy | 1 | 1 | 100.00 | 1 | 1 |

Rate ranking with the authorised descriptive minimum-support filter of **at least 5 total occurrences**:

| rate rank | field | component | canonical entity | total occurrences | corrections | correction rate (%) | records |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | datasets | provider | SAIL Databank | 68 | 53 | 77.94 | 49 |
| 2 | datasets | dataset_name | MoJ Data First Probation | 7 | 1 | 14.29 | 1 |
| 3 | datasets | dataset_name | Annual Survey of Hours and Earnings linked to Census 2011 | 24 | 1 | 4.17 | 1 |
| 4 | datasets | provider | Northern Ireland Statistics and Research Agency (NISRA) | 39 | 1 | 2.56 | 1 |
| 5 | datasets | dataset_name | Business Enterprise Research and Development (BERD) | 83 | 1 | 1.20 | 1 |
| 6 | datasets | provider | Office for National Statistics (ONS) | 2619 | 2 | 0.08 | 1 |
| 1 | organisations | organisation | University of Leeds | 12 | 1 | 8.33 | 1 |
| 2 | organisations | organisation | University of Reading | 13 | 1 | 7.69 | 1 |
| 3 | organisations | organisation | University of York | 13 | 1 | 7.69 | 1 |
| 4 | organisations | organisation | Imperial College London | 17 | 1 | 5.88 | 1 |
| 5 | organisations | organisation | London School of Economics and Political Science (LSE) | 97 | 3 | 3.09 | 3 |
| 6 | organisations | organisation | University of Warwick | 34 | 1 | 2.94 | 1 |
| 7 | organisations | organisation | University College London (UCL) | 120 | 2 | 1.67 | 2 |

The minimum-support filter is descriptive, was chosen only to avoid a rate ranking dominated by 1/1 and 1/2 cases, and does not change any underlying count.

Cumulative concentration and affected-entity distribution:

| field | explicit_correction_occurrences | affected_canonical_entities | entities_with_exactly_1_correction | entities_with_2_corrections | entities_with_3_to_4_corrections | entities_with_5_plus_corrections | top_1_share_percent | top_3_share_percent | top_5_share_percent | top_10_share_percent |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| datasets | 60 | 7 | 5 | 1 | 0 | 1 | 88.33 | 93.33 | 96.67 | 100.00 |
| organisations | 18 | 15 | 13 | 1 | 1 | 0 | 16.67 | 33.33 | 44.44 | 72.22 |
| combined | 78 | 22 | 18 | 2 | 1 | 1 | 67.95 | 74.36 | 78.21 | 84.62 |

Singleton versus recurring suppressed malformed mappings:

| field | explicit_correction_occurrences | distinct_malformed_mappings | one_off_form_occurrences | recurring_form_occurrences | recurring_form_share_percent | occurrences_in_forms_seen_in_3plus_records | three_plus_record_share_percent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| datasets | 60 | 7 | 5 | 55 | 91.67 | 53 | 88.33 |
| organisations | 18 | 18 | 18 | 0 | 0.00 | 0 | 0.00 |
| combined | 78 | 25 | 23 | 55 | 70.51 | 53 | 67.95 |

The largest recurring mapping is the suppressed `variant_01` for **SAIL Databank** (provider): the same malformed representation occurs **53** times across **49** records. This is consistent with a repeated or propagated entry form, although the audit cannot establish how it arose.

Field comparison:

| field | explicit_correction_occurrences | affected_canonical_entities | median_corrections_per_affected_entity | maximum_corrections_for_one_entity | recurring_form_share_percent | singleton_form_share_percent |
| --- | --- | --- | --- | --- | --- | --- |
| datasets | 60 | 7 | 1.00 | 53 | 91.67 | 8.33 |
| organisations | 18 | 15 | 1.00 | 3 | 0.00 | 100.00 |

Entities with the largest malformed-variant diversity:

| field | component | canonical entity | corrections | malformed variants | largest variant count | largest variant share (%) |
| --- | --- | --- | --- | --- | --- | --- |
| organisations | organisation | London School of Economics and Political Science (LSE) | 3 | 3 | 1 | 33.33 |
| organisations | organisation | University College London (UCL) | 2 | 2 | 1 | 50.00 |
| datasets | provider | SAIL Databank | 53 | 1 | 53 | 100.00 |
| datasets | provider | Office for National Statistics (ONS) | 2 | 1 | 2 | 100.00 |
| organisations | organisation | Academy of Medical Sciences | 1 | 1 | 1 | 100.00 |
| datasets | dataset_name | Annual Survey of Hours and Earnings linked to Census 2011 | 1 | 1 | 1 | 100.00 |
| datasets | dataset_name | Business Enterprise Research and Development (BERD) | 1 | 1 | 1 | 100.00 |
| organisations | organisation | Centre for Economic and Business Research (CEBR) | 1 | 1 | 1 | 100.00 |
| organisations | organisation | Equality and Human Rights Commission (EHRC) | 1 | 1 | 1 | 100.00 |
| organisations | organisation | Health Foundation | 1 | 1 | 1 | 100.00 |

Raw malformed strings remain suppressed. `variant_01`, `variant_02`, and subsequent labels in the recurring-corrections CSV are stable anonymous identifiers within each canonical entity. Repeated labels establish only that the same malformed representation recurred; they do not establish how or why it propagated.

### Decomposition verification

- Native dataset and organisation status totals reconcile exactly to 3,350/2,639/711 and 1,839/761/1,078 respectively.
- Changed-occurrence transformation totals reconcile exactly to the original numerators.
- Field-specific explicit corrections sum to 78 occurrences; mutually exclusive record groups sum to the 66-record union.
- Entity concentration and anonymised recurring-form occurrence counts each sum to 78.
- No raw malformed string, Record ID, project title, or researcher name is disclosed.
- No transformation was manually reclassified from raw content; no new alias, matching rule, or error definition was introduced.

### Illustrative explicit corrections

The 25 mappings below concern strings published in the frozen public register. This subsequent disclosure clarification supersedes the earlier reserve-based suppression statements for these illustrative mappings: reserve-based suppression is not applied to public dataset, provider, and organisation forms. The mapping-level CSV therefore reports the observed form for every mapping. Two parser-emitted organisation forms contain an embedded researcher name; only those name tokens remain redacted, in accordance with the continuing prohibition on disclosing researcher names. Counts, mappings, and correction definitions are unchanged.

#### Complete dataset/provider correction ranking

| Rank | Component | Canonical entity | Corrections | Records | Malformed forms | Total entity occurrences | Within-entity correction rate |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | provider | SAIL Databank | 53 | 49 | 1 | 68 | 77.94% |
| 2 | provider | Office for National Statistics (ONS) | 2 | 1 | 1 | 2,619 | 0.08% |
| 3 | dataset name | Annual Survey of Hours and Earnings linked to Census 2011 | 1 | 1 | 1 | 24 | 4.17% |
| 4 | dataset name | Business Enterprise Research and Development (BERD) | 1 | 1 | 1 | 83 | 1.20% |
| 5 | dataset name | Integrated Data Service | 1 | 1 | 1 | 1 | 100.00% |
| 6 | dataset name | MoJ Data First Probation | 1 | 1 | 1 | 7 | 14.29% |
| 7 | provider | Northern Ireland Statistics and Research Agency (NISRA) | 1 | 1 | 1 | 39 | 2.56% |

#### Complete organisation correction ranking

| Rank | Canonical organisation | Corrections | Records | Malformed forms | Total entity occurrences | Within-entity correction rate |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | London School of Economics and Political Science (LSE) | 3 | 3 | 3 | 97 | 3.09% |
| 2 | University College London (UCL) | 2 | 2 | 2 | 120 | 1.67% |
| 3 | Academy of Medical Sciences | 1 | 1 | 1 | 1 | 100.00% |
| 4 | Centre for Economic and Business Research (CEBR) | 1 | 1 | 1 | 1 | 100.00% |
| 5 | Equality and Human Rights Commission (EHRC) | 1 | 1 | 1 | 2 | 50.00% |
| 6 | Health Foundation | 1 | 1 | 1 | 2 | 50.00% |
| 7 | Imperial College London | 1 | 1 | 1 | 17 | 5.88% |
| 8 | Institute for Employment Studies (IES) | 1 | 1 | 1 | 1 | 100.00% |
| 9 | Ministry of National Education, Republic of Türkiye | 1 | 1 | 1 | 1 | 100.00% |
| 10 | Sentencing Academy | 1 | 1 | 1 | 1 | 100.00% |
| 11 | Teesside University | 1 | 1 | 1 | 2 | 50.00% |
| 12 | University of Leeds | 1 | 1 | 1 | 12 | 8.33% |
| 13 | University of Reading | 1 | 1 | 1 | 13 | 7.69% |
| 14 | University of Warwick | 1 | 1 | 1 | 34 | 2.94% |
| 15 | University of York | 1 | 1 | 1 | 13 | 7.69% |

#### Compact presentation table

Up to five mapping rows are shown for mechanisms with multiple forms, prioritised by occurrence count, affected-record count, and then lexical observed form. The mapping-level CSV contains all 25 mappings.

| Field | Mechanism | Observed register form | Corrected/canonical form | Occurrences | Records |
| --- | --- | --- | --- | ---: | ---: |
| datasets | dataset_leading_character_artifact | KIntegrated Data Service Environment Health Cohort Spine | Integrated Data Service | 1 | 1 |
| datasets | dataset_spelling_correction_01 | Business Enterprise Research and Developement | Business Enterprise Research and Development (BERD) | 1 | 1 |
| datasets | dataset_spelling_correction_02 | MOJ Data First Probabation | MoJ Data First Probation | 1 | 1 |
| datasets | dataset_truncation_correction_01 | Annual Survey for Hours and Earnings / Census 2011 Linked Datase | Annual Survey of Hours and Earnings linked to Census 2011 | 1 | 1 |
| organisations | institution_parser_cleanup | [researcher name redacted], University College London | University College London (UCL) | 1 | 1 |
| organisations | institution_parser_cleanup | Centre for Economic and Business Research Ltd (CEBR) | Centre for Economic and Business Research (CEBR) | 1 | 1 |
| organisations | institution_parser_cleanup | Health Foundation/ Academy of Medical Sciences | Academy of Medical Sciences | 1 | 1 |
| organisations | institution_parser_cleanup | Health Foundation/ Academy of Medical Sciences | Health Foundation | 1 | 1 |
| organisations | institution_parser_cleanup | Imperial College Business, School/London School of Economics | Imperial College London | 1 | 1 |
| organisations | institution_reviewed_typo_alias | Equality and Human Rights Comission | Equality and Human Rights Commission (EHRC) | 1 | 1 |
| organisations | institution_reviewed_typo_alias | Institue for Employment Studies | Institute for Employment Studies (IES) | 1 | 1 |
| organisations | institution_reviewed_typo_alias | London School of Economics and Polictical Science | London School of Economics and Political Science (LSE) | 1 | 1 |
| organisations | institution_reviewed_typo_alias | Sentencing Acadamey | Sentencing Academy | 1 | 1 |
| organisations | institution_reviewed_typo_alias | Teeside University | Teesside University | 1 | 1 |
| datasets | provider_repeated_word_correction | SAIL Databank Databank | SAIL Databank | 53 | 49 |
| datasets | provider_spelling_correction_01 | Offcie for National Statistics | Office for National Statistics (ONS) | 2 | 1 |
| datasets | provider_spelling_correction_02 | Northern Ireland Statitiscs and Research Agency | Northern Ireland Statistics and Research Agency (NISRA) | 1 | 1 |

Verification: the 25 mapping-level rows still sum to 78 explicit corrections (60 dataset/provider and 18 organisation) across the unchanged 66-record union. Every displayed form was reproduced from an actual frozen-register occurrence and matched to the original explicit-correction mechanism and anonymous recurrence row. No additional correction, alias, or interpretation was introduced. No Record ID, Project ID, project title, reserve membership, validation output, or researcher name is disclosed.

### Illustrative benign normalisation

> The broad reconciliation-burden rate counts any change between the parsed register form and the canonical representation used for aggregation. Most such changes are benign standardisation rather than corrections.

Dataset changes comprise 2,211/2,639 aliases (83.78%), 426/2,639 normalised-format changes (16.14%), and 2/2,639 compound/multi-dataset changes (0.08%). Organisation changes comprise 514/761 aliases (67.54%), 235/761 identity-with-display changes (30.88%), and 12/761 parser-cleanup changes (1.58%). `parser_cleanup` is not included in the benign examples.

| Field | Transformation class | Changed occurrences | Distinct non-corrective mappings | Top-five share of class |
| --- | --- | ---: | ---: | ---: |
| datasets | alias | 2,211 | 325 | 29.90% |
| datasets | normalised_format | 426 | 162 | 29.11% |
| organisations | alias | 514 | 169 | 32.10% |
| organisations | identity_with_display_change | 235 | 13 | 86.81% |

The class totals retain the authoritative native-status denominators; the example candidates exclude mappings already present in the explicit-correction subset.

| Type | Observed register form | Canonical form | Occurrences | What the transformation does |
| --- | --- | --- | ---: | --- |
| Dataset alias | Business Structure Database | Business Structure Database (BSD) | 176 | collapses equivalent dataset naming |
| Dataset alias | Annual Business Survey | Annual Business Survey (ABS) | 143 | collapses equivalent dataset naming |
| Dataset alias | Annual Population Survey | Annual Population Survey (APS) | 131 | collapses equivalent dataset naming |
| Dataset alias | Annual Survey of Hours and Earnings | Annual Survey of Hours and Earnings (ASHE) | 123 | collapses equivalent dataset naming |
| Dataset alias | Business Structure Database - UK | Business Structure Database (BSD) | 88 | collapses equivalent dataset naming |
| Dataset normalised format | Labour Force Survey Person - UK | Labour Force Survey Person | 39 | standardises formatting |
| Organisation alias | London School of Economics | London School of Economics and Political Science (LSE) | 55 | collapses equivalent organisation naming |
| Organisation identity with display change | University College London | University College London (UCL) | 99 | adds approved canonical display acronym |

The complete top-10 tables for each class are in `register_data_quality_benign_examples.md` and `register_data_quality_benign_examples.csv`. All displayed forms occurred in the frozen register; no explicit-correction mapping is included.

### Analytical normalisation versus display-only standardisation

Display-only acronym standardisation changes how an already-resolved entity is presented but is not required to identify or aggregate that entity. Analytically necessary normalisation resolves alternative register representations that would otherwise fragment deterministic entity counts.

The classification is mechanical. For datasets, the canonical label must be an existing target of the production dataset-alias rules and removing its terminal acronym must reproduce the parsed raw dataset name exactly. For organisations, the raw value must be an exact key in the production approved-acronym map, the production display function must reproduce the canonical label, and removing the terminal acronym must reproduce the cleaned parsed value exactly. All other changed occurrences remain analytically necessary.

#### Occurrence-level decomposition

| Field | Transformation class | Occurrences | % of all evaluable occurrences | % of all changed occurrences |
| --- | --- | ---: | ---: | ---: |
| datasets | unchanged | 711 | 21.22% | NA |
| datasets | display_only_acronym | 965 | 28.81% | 36.57% |
| datasets | analytically_necessary_normalisation | 1,674 | 49.97% | 63.43% |
| organisations | unchanged | 1,078 | 58.62% | NA |
| organisations | display_only_acronym | 306 | 16.64% | 40.21% |
| organisations | analytically_necessary_normalisation | 455 | 24.74% | 59.79% |
| combined | unchanged | 1,789 | 34.48% | NA |
| combined | display_only_acronym | 1,271 | 24.49% | 37.38% |
| combined | analytically_necessary_normalisation | 2,129 | 41.03% | 62.62% |

The dataset rows reconcile to 3,350 occurrences and 2,639 changes; the organisation rows reconcile to 1,839 occurrences and 761 changes. Combined, 1,789 unchanged plus 1,271 display-only plus 2,129 analytically necessary occurrences equals 5,189, and the two changed classes sum to the original 3,400 changed occurrences.

#### Mutually exclusive record-level decomposition

| Record category | Records | % of 1,308 |
| --- | ---: | ---: |
| no changed entity | 72 | 5.50% |
| display-only changes only | 263 | 20.11% |
| analytically necessary changes only | 542 | 41.44% |
| both display-only and analytically necessary changes | 431 | 32.95% |

**973 / 1,308 (74.39%) records required analytically necessary entity normalisation.** This is the union of the 542 necessary-only records and 431 records containing both classes, not a subtraction from the broad 94.50% rate.

**263 / 1,308 (20.11%) records changed only because of display-only acronym standardisation.** In total, 694 records received at least one display-only acronym and 431 received both classes.

#### Existing native classes crossed with the new distinction

| Field | Native class | Display-only acronym | Analytically necessary | Total changed |
| --- | --- | ---: | ---: | ---: |
| datasets | alias | 965 | 1,246 | 2,211 |
| datasets | normalised_format | 0 | 426 | 426 |
| datasets | compound_or_multi_dataset | 0 | 2 | 2 |
| organisations | alias | 71 | 443 | 514 |
| organisations | identity_with_display_change | 235 | 0 | 235 |
| organisations | parser_cleanup | 0 | 12 | 12 |

All 235 organisation `identity_with_display_change` occurrences satisfy the exact approved-acronym-only test. Native `alias` is mixed: it contains 965 dataset and 71 organisation display-only changes, alongside 1,246 dataset and 443 organisation changes that alter more than the terminal acronym.

#### Most common display-only mappings

| Field | Observed form | Display form | Occurrences | Records |
| --- | --- | --- | ---: | ---: |
| datasets | Business Structure Database | Business Structure Database (BSD) | 176 | 176 |
| datasets | Annual Business Survey | Annual Business Survey (ABS) | 143 | 143 |
| datasets | Annual Population Survey | Annual Population Survey (APS) | 131 | 126 |
| datasets | Annual Survey of Hours and Earnings | Annual Survey of Hours and Earnings (ASHE) | 123 | 123 |
| organisations | University College London | University College London (UCL) | 99 | 99 |
| datasets | UK Innovation Survey | UK Innovation Survey (UKIS) | 75 | 75 |
| datasets | Labour Force Survey | Labour Force Survey (LFS) | 70 | 54 |
| organisations | Institute for Fiscal Studies | Institute for Fiscal Studies (IFS) | 64 | 64 |
| organisations | Office for National Statistics | Office for National Statistics (ONS) | 40 | 40 |
| datasets | Crime Survey for England and Wales | Crime Survey for England and Wales (CSEW) | 39 | 38 |

#### Most common analytically necessary mappings

| Field | Observed form | Canonical form | Occurrences | Records |
| --- | --- | --- | ---: | ---: |
| datasets | Business Structure Database - UK | Business Structure Database (BSD) | 88 | 88 |
| organisations | London School of Economics | London School of Economics and Political Science (LSE) | 55 | 55 |
| datasets | Longitudinal Education Outcomes SRS Iteration 2 Standard Extract - England | Longitudinal Education Outcomes (LEO) | 55 | 55 |
| datasets | Annual Business Survey - GB | Annual Business Survey (ABS) | 44 | 44 |
| datasets | Annual Survey of Hours and Earnings - UK | Annual Survey of Hours and Earnings (ASHE) | 41 | 41 |
| datasets | Annual Population Survey - UK | Annual Population Survey (APS) | 40 | 39 |
| datasets | Labour Force Survey Person - UK | Labour Force Survey Person | 39 | 39 |
| datasets | Annual Business Survey - UK | Annual Business Survey (ABS) | 31 | 31 |
| datasets | Business Enterprise Research and Development - Great Britain | Business Enterprise Research and Development (BERD) | 30 | 30 |
| datasets | Understanding Society - UK | Understanding Society | 28 | 28 |

#### Relationship to explicit corrections

The fixed broad dataset numerator compares parsed dataset names with canonical dataset names; it does not treat provider-label changes as dataset-name changes. The explicit-correction subset, however, includes provider corrections. Consequently, **53/78** explicit correction occurrences coincide with an analytically necessary changed entity-name occurrence, while **25/78** are provider corrections attached to an occurrence whose dataset name is unchanged. All 25 are accounted for, but they cannot be placed inside the fixed 2,639 changed dataset-name numerator without changing that authoritative numerator.

Within the fixed entity-name decomposition, 2,129 occurrences are analytically necessary; 53 carry an explicit correction and 2,076 are non-error canonicalisation occurrences. As a supplemental component-aware union, adding the 25 non-overlapping provider corrections gives 2,154 analytically necessary occurrence units, comprising 78 explicit corrections and 2,076 non-explicit canonicalisations. This supplemental figure is not substituted for the fixed 2,129/3,400 result.

The same unit distinction affects records: the fixed entity-name headline is 973 records. The 25 outside-provider corrections affect 25 records, six already in that set; including this one known provider-correction component would produce a 992-record union. That is reported only as a diagnostic sensitivity because the original broad numerator did not enumerate all provider-label normalisation, and it is therefore not a like-for-like decomposition of the 94.50% result.

### Observed naming fragmentation versus optional canonical standardisation

This refinement treats fragmentation as an empirical property of the frozen register's observed source forms, not as a difference between a source string and the production display label. A production-added acronym is therefore not a second source form unless that acronym-bearing form actually occurs in the register.

#### Headline hierarchy

| Quantity | Records | % of 1,308 | Interpretation |
| --- | ---: | ---: | --- |
| Any production string change | 1,236 | 94.50% | Existing broad reconciliation-burden measure |
| Non-display canonicalisation | 973 | 74.39% | Existing result; this should not be called necessarily required for observed aggregation |
| Exposed to observed source-name fragmentation | 1,289 | 98.55% | Contains an entity represented elsewhere under at least two observed source forms |
| Contains at least one non-modal source variant | 766 | 58.56% | Stricter modal-form minimum relabelling burden |
| Explicit corrective transformation | 66 | 5.05% | Existing conservative detected-error subset |
| Explicit correction excluding dominant provider form | 18 | 1.38% | Existing sensitivity result |

**1,289 / 1,308 records (98.55%) contained at least one dataset or organisation whose naming varied elsewhere in the frozen register, requiring entity reconciliation for consistent aggregation.** This exposure measure includes modal and non-modal occurrences of each fragmented entity.

**766 / 1,308 records (58.56%) contained at least one non-modal source representation.** This is the stricter record-level minimum burden and is calculated by Record-ID union, not subtraction.

#### Fragmentation and minimum relabelling burden

| Field | Single-form canonical entities | Fragmented canonical entities | Occurrences in fragmented entities | Records exposed | Minimum required relabels | % of evaluable occurrences |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| datasets | 221 | 126 | 2,969 | 1,224 | 1,186 | 35.40% |
| organisations | 206 | 75 | 1,251 | 981 | 276 | 15.01% |
| combined | 427 | 201 | 4,220 | 1,289 | 1,462 | 28.18% |

For each fragmented canonical entity, the modal observed raw form is retained hypothetically; minimum relabels equal total occurrences minus modal-form occurrences. Lexical order breaks modal ties without affecting the count.

#### Canonical standardisation without observed fragmentation

Production canonicalisation changed **277 occurrences across 226 records** even though the relevant canonical entity had only one observed source form in the frozen population: 159 dataset occurrences across 130 records and 118 organisation occurrences across 107 records.

| Field | Existing native class | Occurrences |
| --- | --- | ---: |
| datasets | alias | 57 |
| datasets | normalised_format | 100 |
| datasets | compound_or_multi_dataset | 2 |
| organisations | alias | 60 |
| organisations | identity_with_display_change | 55 |
| organisations | parser_cleanup | 3 |

#### Previous analytical/display classification crossed with source fragmentation

| Field | Previous class | Source entity single-form | Source entity fragmented | Total |
| --- | --- | ---: | ---: | ---: |
| datasets | display_only_acronym | 12 | 953 | 965 |
| datasets | analytically_necessary_normalisation | 147 | 1,527 | 1,674 |
| organisations | display_only_acronym | 62 | 244 | 306 |
| organisations | analytically_necessary_normalisation | 56 | 399 | 455 |

The earlier 74.39% figure is therefore best interpreted as **records receiving non-display canonicalisation**, not records necessarily requiring reconciliation to prevent fragmentation observed in this frozen population.

#### Ranked fragmented dataset entities

| Rank | Canonical entity | Distinct observed forms | Total occurrences | Modal-form occurrences | Minimum relabels | Records |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Business Structure Database (BSD) | 7 | 283 | 176 | 107 | 283 |
| 2 | Annual Business Survey (ABS) | 10 | 231 | 143 | 88 | 231 |
| 3 | Annual Survey of Hours and Earnings (ASHE) | 11 | 205 | 123 | 82 | 204 |
| 4 | Longitudinal Education Outcomes (LEO) | 15 | 119 | 55 | 64 | 118 |
| 5 | Annual Population Survey (APS) | 9 | 183 | 131 | 52 | 176 |
| 6 | Business Enterprise Research and Development (BERD) | 10 | 83 | 33 | 50 | 82 |
| 7 | Business Register and Employment Survey (BRES) | 6 | 67 | 25 | 42 | 66 |
| 8 | Annual Respondents Database X | 10 | 62 | 23 | 39 | 62 |
| 9 | ONS Longitudinal Study (LS) | 7 | 57 | 21 | 36 | 56 |
| 10 | Understanding Society | 4 | 58 | 28 | 30 | 58 |

| Canonical entity | Observed source forms and counts |
| --- | --- |
| Business Structure Database (BSD) | `Business Structure Database` — 176; `Business Structure Database - UK` — 88; `Business Structure Database UK` — 14; `Business Structure Database (BSD)` — 2; `Business Structure Database (1997-2023)` — 1; `Business structure Database - UK` — 1; `Business structure database` — 1 |
| Annual Business Survey (ABS) | `Annual Business Survey` — 143; `Annual Business Survey - GB` — 44; `Annual Business Survey - UK` — 31; `Annual Business Survey GB` — 4; `Annual Business Survey UK` — 4; `Annual Business Survey (ABS)` — 1; `Annual Business Survey 1973 onwards)` — 1; `Annual Business Survey 2005-2022` — 1; `Annual Business Survey Household Datasets` — 1; `Annual Business Survey in Great Britain` — 1 |
| Annual Survey of Hours and Earnings (ASHE) | `Annual Survey of Hours and Earnings` — 123; `Annual Survey of Hours and Earnings - UK` — 41; `Annual Survey of Hours and Earnings - GB` — 24; `Annual Survey of Hours and Earnings UK` — 7; `Annual Survey of Hours and Earnings (ASHE)` — 4; `ASHE` — 1; `Annual Survey for Hours and Earnings` — 1; `Annual Survey of Hours and Earnings (1997-2024)` — 1; `Annual Survey of Hours and Earnings 1997-2023` — 1; `Annual Survey of Hours and Earnings 1997-2024` — 1; `Annual Survey of Hours and Earnings GB` — 1 |
| Longitudinal Education Outcomes (LEO) | `Longitudinal Education Outcomes SRS Iteration 2 Standard Extract - England` — 55; `Longitudinal Education Outcomes SRS Iteration 1 Standard Extract - England` — 27; `LEO via SRS Iteration 1 Standard Extract` — 18; `Longitudinal Education` — 4; `LEO via SRS Iteration 2 Standard Extract` — 2; `Longitudinal Education Outcomes (LEO)` — 2; `Longitudinal Education Outcomes SRS Iteration 2` — 2; `Longitudinal Education Outcomes SRS Iteration 2 standard extract - England` — 2; `LEO` — 1; `LEO Scotland` — 1; `Longitudinal Education Outcomes` — 1; `Longitudinal Education Outcomes - England` — 1; `Longitudinal Education Outcomes Iteration 2` — 1; `Longitudinal Education Outcomes SRS Iteration 1 standard extract - England` — 1; `Longitudinal Education Outcomes SRS Iteration 2 - England` — 1 |
| Annual Population Survey (APS) | `Annual Population Survey` — 131; `Annual Population Survey - UK` — 40; `Annual Population Survey UK` — 4; `Annual Population Survey (APS)` — 3; `Annual Population Survey (2004-2022 secure access)` — 1; `Annual Population Survey (2004-2023 secure access)` — 1; `Annual Population Survey 2004-2022` — 1; `Annual Population Surveys - Wales` — 1; `Annual population survey - UK` — 1 |
| Business Enterprise Research and Development (BERD) | `Business Enterprise Research and Development` — 33; `Business Enterprise Research and Development - Great Britain` — 30; `Business Enterprise Research and Development - GB` — 7; `Business Enterprise Research and Development England` — 5; `Business Enterprise Research and Development - England` — 2; `Business Enterprise Research and Development - Northern Ireland` — 2; `Business Enterprise Research Development - GB` — 1; `Business Enterprise Research and Developement` — 1; `Business Enterprise Research and Development (BERD)` — 1; `Business enterprise research and development` — 1 |
| Business Register and Employment Survey (BRES) | `Business Register Employment Survey - UK` — 25; `Business Register and Employment Survey` — 20; `Business Register Employment Survey` — 19; `Business Register Employment Survey (BRES)` — 1; `Business Register Employment survey - UK` — 1; `Business Register and Employment Survey (BRES)` — 1 |
| Annual Respondents Database X | `Annual Respondents Database x - UK` — 23; `Annual Respondents Database X` — 21; `Annual Respondents Database x` — 6; `Annual Respondents Database x UK` — 5; `Annual Respondents Database X - UK` — 2; `Annual Respondent Database X` — 1; `Annual Respondents Database ARDx UK` — 1; `Annual Respondents Database X (ARDX)` — 1; `Annual Respondents Database X- UK` — 1; `Annual Respondents DatabaseX` — 1 |
| ONS Longitudinal Study (LS) | `Longitudinal Study of England and Wales` — 21; `ONS Longitudinal Study - England and Wales` — 19; `Longitudinal Study` — 8; `ONS Longitudinal Study` — 5; `ONS Longitudinal Study (LS)` — 2; `Longitudinal Study - England and Wales` — 1; `ONS Longitudinal Study of England and Wales` — 1 |
| Understanding Society | `Understanding Society - UK` — 28; `Understanding Society` — 26; `British Household Panel Survey` — 3; `Understanding Society UK` — 1 |

#### Ranked fragmented organisation entities

| Rank | Canonical entity | Distinct observed forms | Total occurrences | Modal-form occurrences | Minimum relabels | Records |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | London School of Economics and Political Science (LSE) | 9 | 97 | 55 | 42 | 97 |
| 2 | University College London (UCL) | 12 | 120 | 99 | 21 | 120 |
| 3 | University of Manchester | 4 | 43 | 23 | 20 | 43 |
| 4 | University of Edinburgh | 2 | 31 | 18 | 13 | 31 |
| 5 | Cardiff University | 3 | 37 | 28 | 9 | 37 |
| 6 | Ipsos | 5 | 27 | 18 | 9 | 27 |
| 7 | Queen Mary University of London | 6 | 16 | 7 | 9 | 16 |
| 8 | King's College London (KCL) | 5 | 32 | 24 | 8 | 32 |
| 9 | Durham University | 2 | 19 | 11 | 8 | 19 |
| 10 | Aston University | 4 | 14 | 6 | 8 | 14 |

| Canonical entity | Observed source forms and counts |
| --- | --- |
| London School of Economics and Political Science (LSE) | `London School of Economics` — 55; `London School of Economics and Political Science` — 23; `The London School of Economics and Political Science` — 12; `The London School of Economics` — 2; `LSE` — 1; `London School of Economics and Polictical Science` — 1; `London School of Economics and Political Science, University of London` — 1; `London School of Economics; and University College London` — 1; `University of Warwick/London School of Economics` — 1 |
| University College London (UCL) | `University College London` — 99; `University of London - University College` — 11; `[source form 03 withheld: contains researcher name]` — 1; `CASA University College London` — 1; `London School of Economics; and University College London` — 1; `UCL` — 1; `UCL Centre for Longitudinal Studies` — 1; `UCL Institute of Epidemiology and Health` — 1; `Univeristy College London` — 1; `University of London / University College` — 1; `University of London University College` — 1; `University of London-University College` — 1 |
| University of Manchester | `The University of Manchester` — 23; `University of Manchester` — 18; `Manchester University` — 1; `The Productivity Institute, University of Manchester` — 1 |
| University of Edinburgh | `The University of Edinburgh` — 18; `University of Edinburgh` — 13 |
| Cardiff University | `Cardiff University` — 28; `Cardiff Business School` — 6; `University of Cardiff` — 3 |
| Ipsos | `IPSOS MORI` — 18; `Ipsos` — 5; `Ipsos UK` — 2; `IPSOS UK` — 1; `Ipsos MORI` — 1 |
| Queen Mary University of London | `[source form 01 withheld: contains researcher name]` — 7; `[source form 02 withheld: contains researcher name]` — 5; `[source form 03 withheld: contains researcher name]` — 1; `[source form 04 withheld: contains researcher name]` — 1; `[source form 05 withheld: contains researcher name]` — 1; `[source form 06 withheld: contains researcher name]` — 1 |
| King's College London (KCL) | `King's College London` — 24; `University of London - Kings College` — 4; `Kings College London` — 2; `The Policy Institute, King's College London` — 1; `University of London Kings College` — 1 |
| Durham University | `University of Durham` — 11; `Durham University` — 8 |
| Aston University | `Aston University` — 6; `University of Aston` — 6; `Aston Business School` — 1; `The university of Aston` — 1 |

#### Top optional canonical/display standardisation mappings

| Rank | Field | Observed source form | Production canonical/display form | Occurrences | Records | Existing transformation class |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | organisations | Public Health Wales | Public Health Wales (PHW) | 15 | 15 | identity_with_display_change |
| 2 | organisations | London School of Hygiene and Tropical Medicine | London School of Hygiene and Tropical Medicine (LSHTM) | 13 | 13 | identity_with_display_change |
| 3 | datasets | Growing Up in England Wave 1 | Growing Up in England Wave 1 (GUIE) | 12 | 12 | alias |
| 4 | organisations | Greater London Authority | Greater London Authority (GLA) | 9 | 9 | alias |
| 5 | organisations | Competition and Markets Authority | Competition and Markets Authority (CMA) | 8 | 8 | identity_with_display_change |
| 6 | datasets | Labour Force Survey Five-Quarter Longitudinal Dataset | Labour Force Survey Five-Quarter Longitudinal | 7 | 7 | normalised_format |
| 7 | datasets | New Earnings Survey Panel Dataset | New Earnings Survey Panel | 7 | 7 | normalised_format |
| 8 | datasets | Absences and English School Census | English School Census Absences | 6 | 6 | alias |
| 9 | organisations | Department for Business and Trade | Department for Business and Trade (DBT) | 5 | 5 | alias |
| 10 | datasets | Labour Force Survey Two-Quarter Longitudinal Dataset | Labour Force Survey Two-Quarter Longitudinal | 5 | 5 | normalised_format |

#### Explicit corrections and provider boundary

The 78 explicit corrections remain a separate detected-error measure: 72 belong to canonical entities with fragmented observed forms and six to single-form canonical entities. By component, dataset-name corrections split 3 fragmented/1 single-form, organisation corrections split 13 fragmented/5 single-form, and all 56 provider corrections belong to fragmented provider entities.

Provider components remain outside the 3,350 dataset-name occurrence numerator. In particular, the previously identified 25 provider corrections attached to dataset-name-unchanged occurrences are not inserted into the fragmentation or minimum-relabel dataset-name totals.

