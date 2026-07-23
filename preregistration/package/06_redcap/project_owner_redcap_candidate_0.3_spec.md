# Project Owner REDCap candidate 0.3 specification

Version: owner-redcap-candidate-0.3  
Status: unfrozen development candidate; controlled manual import and live QA pending.  
Live-development target: UCL REDCap PID 9149, “DEA Validation Study – Project Owner Review”. No repository process connected to REDCap.

## Architecture

Candidate 0.3 is a substantial pre-recruitment architecture change:

- one pseudonymous REDCap record per owner, keyed by `owner_id`, in a Classic/non-longitudinal project;
- non-repeating survey `owner_consent`;
- repeating survey `project_review`;
- one pre-created repeat instance for every owner–project assignment;
- one participant-specific Survey Queue link per owner;
- owner-level consent and acknowledgement preference collected once;
- each review independently completable and exported as one long-format row.

The dictionary contains exactly two instruments and 97 fields:

- `owner_consent`: 11 fields;
- `project_review`: 86 fields.

Candidate 0.2 remains unchanged and unfrozen. Candidate 0.3 is not frozen and does not authorise recruitment.

## Frozen production capacity check

The authoritative frozen file is `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` (6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299; 1,308 rows). Semicolon-delimited non-empty values were counted independently in the three output columns.

| Dimension | Frozen column | Observed maximum | Candidate slots | Rows at maximum |
|---|---|---:|---:|---:|
| Research Domains | `substantive_domains` | 4 | 4 | 1 |
| Analytical Purposes | `analytical_purpose` | 2 | 2 | 128 |
| Cross-cutting tags | `cross_cutting_tags` | 2 | 2 | 9 |

Generation fails if any observed maximum exceeds capacity.

## Taxonomy display source

`project_owner_taxonomy_display_v1.yaml` is the single owner-facing display source. It is parsed from `taxonomy_data_dictionary.yaml`, includes exactly 11 substantive domains, seven purposes and two tags in missing-label menus, plus the active proposed-only Domain and Purpose `Unclear from Register Entry` fallbacks. Every entry carries three separate values: the immutable `source_definition`, the author-approved compact `owner_microdefinition`, and the author-approved participant-reference `owner_reference_definition`. All 22 rows record `review_status: approved_by_author`, reviewer `Balint Stewart` and review date `2026-07-23`. Eighteen reference definitions remain verbatim frozen definitions after whitespace normalisation. Data Infrastructure & Methodology, Outcome Tracking and both cross-cutting tags combine the frozen definition with an imported inclusion/exclusion boundary clause. Their `reference_definition_provenance`, `imported_boundary_source_field`, `imported_boundary_source_path`, `imported_boundary_source_text` and `imported_boundary_note` values record the exact authoritative source and make clear that the combined reference wording is not verbatim. The microdefinitions are unchanged display-only condensations and do not alter taxonomy rules.

The unique display key is `(owner_layer, canonical_label)`, so the Domain and Purpose `Unclear from Register Entry` entries remain distinct and map to their different frozen definitions. Candidate 0.3 selects entries only when the authoritative `include_in_prompt=true`, the source layer is current and the source status is not removed. The legacy Layer B linkage `Unclear from Register Entry` has `include_in_prompt=false`, status `removed rc2`, and a non-owner layer; generation and validation therefore exclude it from every owner-facing output. Both active Unclear entries remain available only when pre-populated as model proposals and are absent from the 11/7/2 owner missing-label menus.

The same YAML generates inline definitions, menu option text, `project_owner_taxonomy_reference_v1.md` and the 22-row `project_owner_taxonomy_human_review_v1.csv`. Inline REDCap definitions and missing-label choice displays use `owner_microdefinition`; the reference Markdown uses `owner_reference_definition`. The Markdown is clean participant content with its own document version/date and no repository filenames, build/review status or audit footer; technical provenance remains in the YAML, human-review table, specification and manifest. Proposed instances pre-populate canonical label and microdefinition fields through the layer-qualified display index (including its proposed-only fallback section when needed); REDCap descriptive rows pipe those values inline. No `revision_required` or unapproved row may propagate.

## Consent and disposition

`owner_id` is the first field and REDCap record ID. It is pseudonymous and hidden from surveys with `@HIDDEN-SURVEY`. PID 9149 contains no participant name, email, affiliation, organisation or recruitment/contact field. Those data and all invitation/withdrawal administration stay in a separately restricted layer keyed by `owner_id`.

`participant_info_ver` uses the explicit candidate token `project-owner-information-pending-approval-candidate-0.3`. It must be replaced with the approved participant-document version before production. The descriptive field is only a clearly marked attachment/link placeholder.

`intended_recipient` and `owner_consent` are required Yes/No gateways. Participant information precedes them. `owner_consent` appears only for the intended recipient; the two concise stop messages branch on their respective No values. The Project Review queue condition requires completed Owner Consent plus both affirmative values. REDCap Survey Stop Actions for each No response must be configured manually after import and verified live. No automatic deletion, retention-period, recruitment-system or reminder-suppression behaviour is claimed by the dictionary.

`ack_pref` is optional, appears once after affirmative intended-recipient confirmation and consent, and offers Yes / No / Decide later. It does not affect consent, Survey Queue access or analytical completion. PID 9149 does not collect a preferred acknowledgement name or affiliation.

## Repeating project review

Every repeat contains neutral assignment/source identifiers, frozen register text, production/taxonomy provenance and fixed proposed-label slots. `assignment_id` is a stable, survey-read-only participant-facing Review reference; it contains no participant name, email or direct identifier in the fixture or design contract. `owner_id` and internal source/provenance fields remain survey-hidden. Empty domain/purpose proposal slots are completely hidden through `[prop_*_label] <> ''`.

The Project Review introduction states: “A project may have several Research Domains. Each proposed Domain should be judged independently; the Domains are not ranked.” This is descriptive guidance only and adds no response field.

Each populated domain/purpose slot has an inline label/definition and a Fits / Does not fit / Unsure verdict. Domain and purpose slots ask, “Is the basis for this classification visible in the public project title and datasets listed above?”

Both canonical cross-cutting tags are reviewed on every assignment, including when their pre-populated status is Not applied. Each block shows its common-source definition, a survey-read-only Applied/Not applied proposed status, required Yes/No/Unsure correctness, the preserved question “Could the correct status for this tag reasonably be determined from the public project title and datasets listed above?”, and a conditional required basis. Neither block branches on proposed status.

Every visibility field uses `2, Clearly visible | 1, Partly visible | 0, Not visible | 3, Unsure`. A domain/purpose basis is shown and required for Does not fit/Unsure or Partly visible/Not visible/Unsure. A tag basis is shown and required for correctness No/Unsure or the same three non-clear visibility responses. Clearly visible alone never reveals a basis field.

All three missing-label gateways are required Yes/No/Unsure items. The complete 11/7/2 definition-bearing checkbox menus appear only after Yes and are required when displayed; Unsure does not force a label selection. One basis field per dimension is shown and required when at least one checkbox is selected. The missing-purpose construct displays the maximum-two guidance immediately before its checkbox and applies `@MAXCHECKED=2`. REDCap checkbox requiredness, at-least-one behaviour and the maximum-two action tag must be confirmed in live QA. The missing-tag gateway is retained as an explicit summary cross-check; the two per-tag correctness judgements are the primary status assessments. This deliberate redundancy requires later protocol and participant-document alignment but is not a contradictory coding rule.

Overall review fields retain public-entry sufficiency, taxonomy fit and issue type, conditional explanations, optional final comments and response-specific quotation permission. Existing `po_nonpublic`/`po_nonpublic_note` fields are aligned as the required project-knowledge gateway and optional conditional context note. Warnings prohibit confidential or non-public content. Named acknowledgement is not repeated.

## Long-format export and analysis preparation

An owner row has blank `redcap_repeat_instrument`/`redcap_repeat_instance` and holds `intended_recipient`, `owner_consent`, `ack_pref`, `owner_consent_timestamp` and `owner_consent_complete`.

A review row has `redcap_repeat_instrument = project_review`, numbered `redcap_repeat_instance`, assignment/project/proposal values, owner responses, `project_review_timestamp` and `project_review_complete`. Pre-created untouched instances must remain exported as incomplete review rows.

Assignment-response states are defined independently:

- **Offered:** a pre-created repeat exists.
- **Untouched:** the repeat exists with no participant response.
- **Partial:** at least one response exists but the analytical-completion rule fails.
- **Analytically complete:** joined intended-recipient and consent are affirmative; every populated domain/purpose has verdict and visibility; both tags have correctness and visibility; all three missing-label gateways, sufficiency, project-knowledge gateway and taxonomy fit are answered; and every triggered menu, basis, issue type or explanation is present.
- **Submitted:** `project_review_complete = 2`.

A submitted review should normally be analytically complete because requiredness and branching operate in REDCap, but analysis derives and verifies analytical completeness rather than relying on form status alone. Optional `ack_pref`, project-knowledge note, final comments and quotation permission do not determine it.

Analysis preparation must:

1. split owner rows where `redcap_repeat_instrument` is blank from review rows where it equals `project_review`;
2. join owner consent to reviews by `owner_id`;
3. derive offered, untouched, partial, analytically complete and submitted indicators using the rule above;
4. retain offered, untouched and partial rows for recruitment and response-rate reporting;
5. restrict substantive complete-review summaries to analytically complete rows after the owner join.

For Analytical Purposes, derive the implied corrected-purpose count as the number of populated proposed purposes judged `Fits` plus the number of selected missing-purpose labels. If that count exceeds two, flag the response as a purpose-cardinality/taxonomy issue rather than treating it as a directly comparable corrected classification. A response containing an `Unsure` proposed-purpose verdict is not a definitive corrected-purpose set even when analytically complete.

Do **not** filter repeated rows directly with `owner_consent = 1`: non-repeating values are blank on repeated rows.

## Withdrawal reference

`assignment_id` is displayed as Review reference near the project information, remains stable independently of repeat-instance ordering, and is repeated in the manually configured completion text. Specific-review withdrawal instructions use this reference. A participant withdrawing all submitted reviews may contact the study team from the professional email address used for the invitation and state that request without knowing or quoting `owner_id`. The production withdrawal deadline remains a Participant Information Sheet configuration item and is not invented here.

## Candidate 0.2 → 0.3 architecture change

| Component | Candidate 0.2 | Candidate 0.3 |
|---|---|---|
| Record unit | Owner–project assignment (plus contact records) | One pseudonymous owner |
| Assignment representation | One separate record | One pre-created repeating Project Review instance |
| Participant link | One link per assignment | One participant-specific Survey Queue link per owner |
| Consent | Linked contact workflow | One non-repeating consent gateway |
| Acknowledgement | Restricted contact-admin location | `ack_pref` once at owner level; presentation handled separately |
| Project reviews | Separate records | Independent long-format repeat rows |
| Direct identifiers | Present in restricted admin instrument inside the project | Absent from PID 9149; contact layer separated |
| Taxonomy delivery | Inline full definitions/full admin flags | Inline definitions, conditional complete menus, optional reference |
| Export | Wide assignment/contact records | Owner row plus long-format repeating rows |

This substantial instrument architecture change is made before recruitment and before final participant-document, protocol and ethics alignment.

## Field-level traceability

| Candidate 0.2 field(s) | Candidate 0.3 disposition |
|---|---|
| `owner_record_id` | Replaced by `owner_id` as the REDCap record ID because one record now represents one owner. |
| `record_type` | Removed; row type is represented by REDCap repeating metadata. |
| `owner_id` | Retained and moved to the first field/record ID on non-repeating `owner_consent`. |
| `oc_name`, `oc_email`, `oc_affiliation`, `oc_contact_source`, `oc_contactability`, `oc_contact_issue_note` | Removed from the research project; held only in the separate restricted recruitment/contact layer keyed by `owner_id`. |
| `oc_eligible_projects`, `oc_projects_offered`, `oc_minutes_per_project`, `oc_est_total_minutes`, `oc_eoi_invite_date`, `oc_eoi_status`, `oc_eoi_response_date`, `oc_projects_accepted`, `oc_followup_date`, `oc_contact_suppression`, `oc_recruit_route`, `oc_sequence_pos`, `oc_supp_reason`, `oc_reconsent_required`, `oc_consent_withdrawal`, `oc_consent_withdraw_date`, `oc_link_eligible` | Removed from PID 9149 and moved to the restricted recruitment/contact workflow. Queue access now uses owner-row consent fields and manual restricted disposition. |
| `oc_ack_permission` | Moved and renamed to owner-level `ack_pref`; choices become Yes / No / Decide later. |
| `oc_ack_name`, `oc_ack_affiliation`, `oc_ack_permission_date`, `oc_ack_permission_source` | Removed from PID 9149. Exact presentation and its operational record remain in the separate restricted contact process. |
| `pc_intro`, `pc_reason`, `pc_burden`, `pc_scope`, `pc_voluntary`, `pc_data`, `pc_withdrawal`, `pc_contact`, `pc_reference` | Consolidated into `owner_intro`, the participant-information placeholder, and consent stop messages. |
| `pc_info_version` | Renamed `participant_info_ver`; hidden candidate token must be replaced by the approved document version before production. |
| `pc_decision` | Replaced by the two-stage `intended_recipient` and `owner_consent` gateway. |
| `pc_decline_end` | Replaced by `wrong_recipient_stop` and `consent_decline_stop`; live Stop Actions remain manual configuration. |
| `owner_assignment_id` | Renamed `assignment_id` and moved onto each repeating `project_review` instance. |
| `source_record_id`, `official_project_id`, `project_title`, `datasets_used`, `public_register_url`, `production_ver`, `taxonomy_ver`, `proposal_output_sha256` | Retained per assignment on repeating `project_review`; administrative provenance is survey-hidden, while public register text is survey-read-only. |
| `owner_recruit_route`, `owner_sequence_pos`, `owner_invite_batch`, `owner_link_release`, `owner_invite_date`, `owner_reminder_date`, `owner_withdrawal_status` | Removed from PID 9149 and moved to restricted recruitment/response administration. |
| `instrument_ver` | Split into `owner_instr_ver` and `review_instr_ver`; `consent_form_ver` and `taxonomy_display_ver` add document/display provenance. |
| `prop_d01`–`prop_d12`, `po_d01_label`–`po_d12_vis` | Replaced by four pre-populated domain value/definition slots (`prop_d01_*`–`prop_d04_*`) and paired display/verdict/visibility/basis fields. The capacity equals the frozen maximum. |
| `prop_p01`–`prop_p08`, `po_p01_label`–`po_p08_vis` | Replaced by two pre-populated purpose slots (`prop_p01_*`–`prop_p02_*`) with the same paired response structure. |
| `prop_t01`, `prop_t02`, `po_t01_label`–`po_t02_det` | Retained in substance as two always-present tag blocks: canonical label/definition, pre-populated Applied/Not applied status, required correctness, four-level visibility and conditional basis. |
| `po_intro`, `po_privacy`, `po_assignment`, `po_project_title`, `po_datasets` | Retained in substance; consolidated/renamed as `po_intro`, `po_privacy`, taxonomy-reference placeholder and read-only assignment fields. |
| `po_miss_domain`, `po_miss_purpose`, `po_miss_tag` | Retained as required gateways and expanded to Yes / No / Unsure. |
| `po_miss_domains`, `po_miss_purposes`, `po_miss_tags` | Retained with definitions added to every option and with `Unclear from Register Entry` excluded. |
| `po_note` | Split into one conditional basis field per proposed slot, one basis per missing-label dimension, `po_suff_explain`, `po_tax_explain`, and `po_tax_other`. |
| `po_sufficiency`, `po_taxonomy_fit`, `po_tax_issue` | Retained with the requested codes and explicit conditional explanations. |
| `po_nonpublic`, `po_nonpublic_note` | Retained; `po_nonpublic` adds Unsure and the note remains optional to reduce disclosure pressure. |
| `po_quote_permission`, `po_other_comment` | Retained at repeating review-instance level; quotation permission remains response-specific. |
| REDCap completion/timestamp fields | Generated per non-repeating consent row and per repeating review row; they are specified in the export schema, not dictionary rows. |

## Files and status

The dictionary, field/branch/export specifications, display/reference/review sources and synthetic fixture are deterministic repository artefacts. Project-level Survey Queue, repeating-instrument, Stop Action, checkbox requiredness, survey completion and attachment settings cannot be guaranteed by the CSV and are mandatory live-QA assertions. Candidate 0.3 is technically ready for controlled synthetic import and its taxonomy wording is approved for participant use. It remains unfrozen and is not ready for recruitment until live QA and coordinated participant-document, invitation, protocol, ethics and governance alignment are complete.
