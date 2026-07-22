# Standalone Project Owner REDCap instrument gap audit

Audit date: 2026-07-22  
Target blank REDCap project: PID 9149, `DEA Validation Study - Project Owner Review` (Development)  
Repository branch: `main`  
Repository HEAD: `6337c3e58d3e6d7e410682afa56ffc818e42d86f`  
Scope: offline design audit only; no REDCap connection, records, invitations, sample, protocol change, or dictionary construction.

## 1. Executive verdict

The proposed three-instrument architecture is technically and analytically coherent in one REDCap Classic project, provided it is implemented as two record classes rather than as a relational database: one restricted contact record per researcher and one separate assignment record per owner-project pairing. A pseudonymous `owner_id` links the classes outside REDCap; `owner_assignment_id` identifies an assignment; `source_record_id` is the stable DEA Record ID used to join the owner and scratch streams. REDCap supplies no foreign-key enforcement, so imports and offline validation must enforce uniqueness, referential integrity, and allowed record-type/form combinations.

The simplest robust respondent workflow is one record-specific survey link per assignment record. If one researcher reviews several projects, one invitation may list several links, but each link still opens a distinct assignment record. A Survey Queue does not join separate Classic records and therefore does not solve multi-project navigation. Repeating instruments and longitudinal events add no material advantage and would weaken the protocol's one owner-project assignment per record/export-row rule.

The existing 80-field `project_owner` form contains the core scientific questions, but it cannot be moved unchanged. Every field needs at least a standalone assignment-record guard; classification fields also need an acknowledgement guard. The two binary tags are currently displayed only when the production flag is positive, so negative tag proposals cannot be reviewed. The form also lacks participant information/acknowledgement, quotation permission, an explicit non-public-knowledge question, and a protected contact/recruitment record model. None of the 80 fields is scientifically obsolete, but zero are reusable as byte-for-byte dictionary rows; all 80 are reusable with wording or configuration changes. The proposed candidate-0.1 structure contains 152 user-defined fields: 27 in Owner Contact Admin, 39 in Owner Assignment Admin, and 86 in Project Owner Review. Thirty-seven proposed variable names are new relative to the combined candidate-0.7 dictionary; six of those extend the respondent-facing form.

Candidate-0.1 dictionary construction is blocked by three genuine decisions: approve the contact/survey-link delivery mechanism without copying email addresses into assignment records; approve the participant-information, withdrawal and quotation-permission policy text; and confirm that both positive and negative binary tag proposals are to receive explicit owner verdicts. Contact-source hierarchy and maximum search effort must also be frozen before real contactability work, but their final values need not block creation of a structurally extensible draft dictionary.

## 2. Authoritative-source inventory

| Source | State and relevance |
|---|---|
| `package/00_protocol/Validation_Protocol_PreReg_v0.15.docx` | Current unregistered review candidate; SHA-256 `5eff044b4f8d488e84a5b49720d35318add4f29ef53136cb6ce9c2b197409ee7`. Sections 5.4, 6.3, 6.5, 7, 7.2, 8.6, 8.10, 9.1-9.3, 10.2 and 11 govern this audit. |
| `package/06_redcap/redcap_data_dictionary_candidate.csv` | Frozen combined candidate-0.7 source; SHA-256 `1bb8d75675bd1723c398680dff3625955ac5760d4987b4c41bce44fe57d2bbcc`. It has 80 inherited owner fields and was frozen for the scratch project, not independently validated as the standalone owner workflow. |
| `scripts/build_redcap_candidate.py` and `scripts/validate_redcap_candidate.py` | Deterministic source and offline rules for the inherited owner form: proposed-label mappings, fit/visibility values, missing-label branches, taxonomy rules, conditional note and synthetic cases. |
| REDCap README, codebook, field/response specification, branching specification, label mapping, expected export, QA records and tests | Confirm the old combined four-form design, candidate-0.7 mappings, owner form invariance since candidate 0.6, and that owner live QA remained outstanding. These are historical inputs, not evidence that PID 9149 has been tested. |
| `analysis/validation/owner.py` and owner tests | Define completion, response denominators, route separation, unique record-label patterns, no owner majority, the 50-record target and 25-record minimum. |
| `analysis/validation/owner_sampling_frame.py`, sampling specification and sampling README | Define prospective owner eligibility and the contactability-aware sequence primitive. They explicitly say no owner cohort/contact list exists and that contact-source hierarchy and maximum effort remain to be specified. |
| `package/07_analysis/project_owner_results.csv`, traceability and output manifest | Blank output shell and tested analytical primitives; owner recruitment and empirical ingestion remain prospective. |
| Manifest RED-001 to RED-038, especially RED-002 and RED-018 | RED-002 still describes a separate owner dictionary as a superseded placeholder, which conflicts with v0.15's current architecture and must be corrected during implementation. RED-018 records that the inherited owner form did not complete live QA. |

No repository source claims that PID 9149 has been connected, populated, configured, or tested. The PID and blank-project facts in the task are treated as supplied operational context, not independently verified live evidence.

## 3. Existing 80-field inventory

The complete row-level inventory is in `project_owner_existing_field_inventory.csv`. It preserves source order, exact field names, types, labels, choices, validation, branching, required and identifier flags, notes and annotations. It also records respondent visibility, analytical role and standalone disposition for every row.

Summary:

| Existing field group | Count | Current behaviour | Standalone disposition |
|---|---:|---|---|
| Introduction and project display | 4 | Intro, opaque assignment, title, datasets | Reuse content, but update information/piping and guard by assignment record. |
| Domain proposal display/verdict/visibility | 36 | 12 fixed slots, each controlled by `prop_dNN` | Retain names, labels, definitions and codes; combine each existing branch with record/acknowledgement guards. |
| Purpose proposal display/verdict/visibility | 24 | 8 fixed slots, each controlled by `prop_pNN` | Same treatment as domains. |
| Binary-tag display/verdict/visibility | 6 | Two slots shown only for `prop_tNN = 1` | Modify so both Yes and No proposals are visible and reviewable. |
| Missing-label questions | 6 | Domain, purpose and tag yes/no plus conditional checkbox | Retain codes; add common guards. Substantive `Unclear` is correctly excluded from missing-domain/purpose lists. |
| Overall sufficiency/taxonomy | 3 | Sufficiency; Fit/Partial Fit/No Fit; conditional issue type | Retain codes; make labels self-explanatory; no owner `Cannot assess`. |
| Omnibus explanation | 1 | Required for any non-positive fit/visibility, missing label, limited entry or taxonomy issue | Retain one field for minimum burden, but make it identify every affected label/issue and prohibit confidential detail. |
| **Total** | **80** | All respondent-facing; no direct identifiers | **0 unchanged rows; 80 reusable with change; 0 obsolete.** |

The zero unchanged count is a configuration result, not scientific rejection: even content that is otherwise reusable must be guarded so it never appears on contact records. Sixty-nine fields retain their substantive wording/codes, while eleven need wording or proposal-presentation changes in addition to the guard.

## 4. Protocol-to-field traceability

| Protocol requirement | Existing support | Candidate-0.1 requirement | Finding class |
|---|---|---|---|
| Separate owner assignment and survey workflow; one assignment per row | Existing combined record has one owner response row, but no standalone record class | `record_type`, `owner_assignment_id`, `owner_id`, `source_record_id`; one non-repeating survey per assignment | Required for candidate-0.1 |
| Owners see public entry, proposals and short definitions | Title/datasets plus 22 fixed label descriptions | Retain fixed proposal slots and definitions; show proposal state explicitly for tags | Required for candidate-0.1 |
| Fits / Does not fit / Unsure for every proposed label | Implemented for positive proposal flags | Retain for domains/purposes; extend to negative binary-tag proposals if confirmed | Blocker before dictionary construction |
| Public-entry visibility for each proposal | Implemented as Clearly/Partly/Not visible/Unsure | Retain and pair with each displayed proposal | Required for candidate-0.1 |
| Explanation for Does not fit or Unsure | `po_note` is conditionally required; it also triggers for visibility concerns | Retain one conditional note, instructing respondent to name each affected label | Required for candidate-0.1 |
| Missing domains, purposes and tags | Implemented | Retain structured yes/no and checkbox fields | Required for candidate-0.1 |
| Public-entry sufficiency | Implemented with correct three codes | Replace terse label with a question; retain codes | Required for candidate-0.1 |
| Taxonomy fit: Fit / Partial Fit / No Fit only | Correct | Retain; continue to exclude `Cannot assess` | Acceptable/documented |
| Taxonomy-problem explanation | Issue type and omnibus note | Retain both; clarify that actual-project taxonomy fit is distinct from public evidence | Required for candidate-0.1 |
| Non-public project knowledge | Not directly asked | Add structured yes/no plus source/type note, with no request for confidential content | Required for candidate-0.1 |
| Voluntary participation and information | Absent | Add concise information, privacy/withdrawal text and required continue/decline acknowledgement | Blocker before dictionary construction |
| Owner evidence is not a gold standard | Intro does not say this | Add neutral wording that responses are project-informed evidence, not an authoritative answer | Required for candidate-0.1 |
| Contact/recruitment admin hidden from respondents | Partial hidden fields exist in combined Assignment Admin, but no contact record | Add protected contact form and guarded assignment form; enable only review as a survey | Required for candidate-0.1 |
| No scratch/sample/reserve/adjudication exposure | Hidden combined admin contains these fields | Do not include them at all in the standalone owner dictionary | Required for candidate-0.1 |
| Sequence and supplementary routes reported separately | Existing route, position, batch and reason fields | Split contact operations from assignment-level analytical provenance | Required for candidate-0.1 |
| Completion = every proposed verdict plus sufficiency | Validator implements this for positive flags | Implement against every displayed proposal, including tag No proposals if approved; require sufficiency | Required for candidate-0.1 |

## 5. Record-model assessment

### Recommended Classic-project model

Use one non-longitudinal Classic project with three instruments and two formal record types:

1. `owner_contact_admin`: common record key/type fields plus one restricted contact record per researcher.
2. `owner_assignment_admin`: one assignment record per owner-project pairing, with only pseudonymous and public/provenance fields.
3. `project_owner_review`: the sole survey-enabled instrument, on assignment records only.

Use `record_type = 1` for contact and `record_type = 2` for assignment. Use a separate hidden `synthetic_qa` flag rather than overloading record type, so synthetic contact and assignment records exercise the same branches as their formal counterparts. All contact-only fields use `[record_type] = '1'`; assignment-admin fields use `[record_type] = '2'`; survey context uses `[record_type] = '2'`; classification fields additionally require `[po_ack] = '1'`. Existing proposal branches are parenthesised and combined with those guards.

REDCap branching hides fields, not the existence of every instrument tab or status icon from authorised staff. Safety therefore requires all of: field guards, only `project_owner_review` enabled as a survey, survey invitation/queue eligibility restricted to assignment records, staff instrument permissions, filtered operational reports, and live QA. Respondents receiving a unique survey link see only that record's survey and do not need a REDCap account.

### Keys and joins

| Key | Level | Rule |
|---|---|---|
| `owner_record_id` | REDCap record | Neutral opaque unique project record identifier; the generator prevents contact/assignment collisions without embedding sampling or project facts. |
| `owner_id` | Researcher | Stable pseudonymous identifier present on the contact record and every assignment for that person. It is not a direct identifier, but it remains restricted because it links to the crosswalk. |
| `owner_assignment_id` | Owner-project assignment | Unique, immutable, one-to-one with an assignment record and respondent link. |
| `source_record_id` | DEA project record | Stable Record ID used for scratch/owner/production joins and unique-record deduplication. |
| `official_project_id` | Public project metadata | Retained for public display/provenance; not a substitute for stable Record ID. |

Offline import validation must require one contact row per `owner_id`, exactly one `owner_id` and one `source_record_id` per assignment, unique `owner_assignment_id`, no contact fields on assignment records, no project/proposal fields on contact records, and a valid contact parent for every formal assignment. REDCap itself will not enforce these relationships.

### Links, multiple projects and lifecycle

- Generate a record-specific link only after an assignment record has passed offline validation. Never use a public survey link that creates an uncontrolled new record.
- If one researcher has several projects, send separate assignment links, potentially collected in one invitation. A Survey Queue is record-local and cannot queue surveys across separate Classic records.
- Keep Save & Return on each assignment. Test return-code behaviour, partial saves, browser closure, repeat access after completion and link disabling after withdrawal.
- Use standard form status and survey/audit timestamps as operational completion evidence. Do not add a manually typed completion date merely to duplicate the audit trail; derive the completion date in the restricted export process.
- A contact-level withdrawal/do-not-contact flag governs future messages for all assignments. An assignment-level withdrawal status records whether a specific response is withdrawn. The operational procedure must propagate contact-level withdrawal to all open assignments without deleting audit history.
- Do not use repeating instruments or longitudinal events. Both would complicate invitation routing and exports without improving the one-assignment/one-row design.

### Invitation-delivery constraint

Separating email from assignment records is analytically desirable, but REDCap cannot automatically look up an email stored on a different record through `owner_id`. The preferred design is a restricted, approved mail-merge process that joins contact email to record-specific assignment links outside the analytical export and writes only delivery metadata back to REDCap. Copying email into every assignment would make REDCap invitations easier but duplicate direct identifiers across analytical records. This choice must be approved before dictionary construction because it determines whether an assignment-email field is needed. No public survey link, external REDCap account, or respondent DAG is required. DAGs are staff-record segregation tools, not a participant privacy control.

## 6. Privacy and access assessment

The planned separation is adequate only if it is treated as a least-privilege workflow, not as automatic de-identification. In one Classic project, a sufficiently privileged full export can still contain contact records and assignment records and can join them through `owner_id`. `@HIDDEN-SURVEY` and branching protect the respondent interface; they do not prevent an administrator from exporting the fields.

| Data class | Storage and visibility | Analytical export treatment |
|---|---|---|
| Name, email, organisation/affiliation | Owner Contact Admin only; REDCap Identifier = `y`; contact-admin role only | Exclude entirely. Retain only in the restricted contact crosswalk/operational export. |
| `owner_id` | Common hidden pseudonym on contact and assignment records | Include in restricted response-level working data; omit or further pseudonymise from public release. |
| `owner_assignment_id` | Hidden assignment admin; may be displayed as a neutral reference | Include as response key in restricted analysis; not a direct identifier. |
| Stable `source_record_id` | Hidden assignment admin | Include; it is the protocol join key and unique-record unit. |
| Public title/datasets and official Project ID | Assignment admin, piped to survey | Include as public context where needed; public release follows the later disclosure plan. |
| Proposed labels, definitions and production provenance | Assignment admin and survey display | Include in analytical export. Do not expose scratch ratings, sample set, reserve, disagreement or adjudication metadata. |
| Owner verdicts and structured diagnostics | Survey | Include in restricted analytical export. |
| Free-text comments/non-public-knowledge source | Survey response; potentially sensitive even without direct identifiers | Restricted. Qualitatively code or redact only under the protocol; never publish raw/named comments without permission. |
| Recruitment route, batch, sequence position, response/completion status | Contact operational record and non-identifying assignment provenance | Include the minimum needed for route-specific flow; exclude contact-source URLs, emails and operational notes. |
| Invitation/reminder/delivery/contactability history | Contact admin | Use for restricted flow audit. Export only aggregated/nonidentifying derived status to analysis. |
| Withdrawal/do-not-contact | Contact admin and assignment status where applicable | Exclude from scientific outcome tables except aggregate flow; retain operationally to honour the instruction. |

Create named export/report specifications rather than relying on staff to deselect identifiers each time. One restricted contact report contains contact rows and no survey answers; one analytical report filters `record_type = 2`, excludes all `oc_*` fields and includes only approved keys, provenance, proposal and response fields. Full-data-export permission should be limited to the data manager. Instrument permissions hide both admin forms from any respondent-facing/recruitment role that does not require them.

## 7. Question, branching and participant-information audit

### Participant information and acknowledgement

The current form has no adequate information or acknowledgement layer. Candidate 0.1 should provide, before substantive questions:

- a concise survey introduction explaining why the person was invited, the professional-review purpose, approximate burden, voluntary participation and that the response is project-informed evidence rather than a gold standard;
- intended use: aggregate methodological reporting, adjudication triggers and possible taxonomy improvement;
- a warning not to paste restricted, confidential, personal or otherwise non-public substantive material;
- the withdrawal deadline and study contact route;
- privacy/retention/controller or equivalent information by link to a separately governed participant-information document if required;
- a required `Continue / I do not wish to participate` acknowledgement; selecting the latter reveals no scientific questions and is recorded only as a recruitment disposition;
- a separate quotation choice. The recommended default is no direct quotation; an owner may permit anonymous verbatim quotation. Any named quotation requires later case-specific permission outside this survey.

The invitation email should contain the invitation rationale, expected burden, number of project links, voluntary nature, one-reminder schedule, contact details and participant-information link. The separate participant-information document should carry fuller privacy, retention, withdrawal, complaint/contact and governance information if the institution requires it. The survey itself need not reproduce the whole protocol, collect demographic data, create a user account, or request a signature for this low-burden professional review. Whether a formal ethics-approved consent formulation is required is not evidenced by the repository and must not be invented here.

### Owner-review logic

The inherited form correctly avoids asking owners to classify the full taxonomy, uses Fits / Does not fit / Unsure, pairs each positive proposed label with public-entry visibility, retains missing-label fields, uses Fit / Partial Fit / No Fit for owner taxonomy fit, and has no owner `Cannot assess` option. It does not call owners a gold standard. It also does not expose scratch answers or adjudication in respondent-facing fields, although those unrelated hidden fields must be removed from the standalone dictionary rather than merely trusted to remain hidden.

Required corrections:

1. Every survey field must be assignment guarded. Existing conditional logic must be parenthesised and combined, never replaced.
2. Each displayed proposal must have both a verdict and visibility response. The current fixed slots avoid hidden non-proposed domain/purpose slots being required, because their response fields branch on `prop_* = 1`.
3. Both binary tags must show the actual production proposal (`Yes` or `No`) and accept a verdict. The current positive-only branch fails the required negative-tag QA case.
4. `po_note` may remain a single low-burden note, but its label must instruct the owner to identify every label or issue to which the explanation applies. It must not ask for the substantive non-public information.
5. Add `po_nonpublic` and conditional `po_nonpublic_note` asking whether answers used knowledge beyond the public entry and, if Yes, only the source/type of that knowledge.
6. Completion is valid only when every displayed proposed-label verdict and `po_sufficiency` are complete and all triggered required fields resolve. Visibility, missing-label and taxonomy questions are required for a valid completed export even though the protocol's shortest completion definition names verdicts and sufficiency.
7. Disagreement must not create greater navigational difficulty than agreement. Conditional notes should appear immediately after the relevant review block or as one clearly labelled summary note; they must not cause a second survey or contact requirement.

### Dynamic proposal presentation

| Option | Assessment |
|---|---|
| Fixed taxonomy-coded slots with branching | **Recommended.** Stable columns, deterministic proposal flags, straightforward validation, fixed definitions, no manual field generation per record. Supports all 12 domain codes, all 8 purpose codes and both tags. |
| Dynamically generated descriptive fields | REDCap does not generate dictionary fields at runtime. Piping can change displayed values, but it cannot create a variable number of response columns safely. |
| Matrix | Poor fit: definitions and conditional notes are awkward, mixed Fit and visibility scales require separate matrices, mobile usability is weaker, and branching at row level is limited. |
| Repeating instrument | Unnecessary long-form repeats, more complex invitations/completion and a mismatch with one assignment/export row. |

For domains, prepopulate `prop_d01`-`prop_d12` as 0/1 and show only proposed slots. For purposes, do the same for `prop_p01`-`prop_p08`; the production maximum of two is checked before import. For tags, store both binary proposal values and always show both tag blocks, piping `Yes` or `No` into the proposal statement. Each shown block has stable `_fit` and `_vis` columns. Unused domain/purpose slots remain blank and hidden, never required.

Store `production_ver`, `taxonomy_ver`, `proposal_output_sha256` and the full proposal flags on each assignment. The immutable import-generation audit should verify that flags exactly reproduce the frozen production output for `source_record_id`. Definitions remain dictionary-controlled and versioned by `instrument_ver`/`taxonomy_ver` rather than copied as editable record text.

## 8. Recruitment-workflow audit

| Protocol operation | Level | Recommended controlled metadata |
|---|---|---|
| Researcher identity/contact and public source | Contact | `owner_id`, name, email, organisation, source type/note, search date/operator |
| Contactability and maximum-effort outcome | Contact | contactability status/reason, sequence eligibility, source/version audit |
| Greedy sequence position | Contact master and copied to assignment provenance | sequence position and frozen sequence version |
| Sequence vs supplementary vs post-revision route | Contact decision and copied to assignments | route code; never inferred from response or model output |
| Initial 10 / day 14 / 21 / 28 / supplementary batch | Contact and copied to assignments | controlled invitation-batch code |
| Reason for supplementary invitation | Contact decision and copied verbatim or coded to assignments before contact | required only for supplementary route; must not mention model/coder disagreement |
| First invitation and one reminder about day 10 | Contact | actual dates; do not manufacture a reminder date when none is sent |
| Failed delivery | Contact; derived assignment response state | delivery status distinct from contactability and nonresponse |
| No response, partial, complete, declined | Contact summary plus assignment status/form status | assignment-level response state supports owner-record completion; contact summary supports invited/responding researchers |
| Completion date | Assignment/system | derive from survey completion timestamp/audit trail, not a manual respondent field |
| Withdrawal/do-not-contact | Contact master; assignment-specific withdrawal where necessary | contact-level suppression plus immutable response-withdrawal audit |
| Close 42 days after first invitation | Study/wave configuration | one controlled cohort close date in the recruitment runbook; do not duplicate an editable date on every record |

The current admin fields conflate contactability, failed delivery, nonresponse and response received in `owner_contact_disp`. Candidate 0.1 should split contactability, delivery and response status. Existing response codes also lack declined, withdrawn and closed states. The repository does not yet define a contact-source hierarchy or maximum search effort; those choices must be frozen before any real contact search or sequence is finalised.

## 9. Analysis-export audit

The proposed export supports Section 8.6 without interpreting free text if it contains:

- keys/provenance: `owner_id`, `owner_assignment_id`, `source_record_id`, route, sequence position, invitation batch, production/taxonomy/instrument versions and proposal flags;
- flow: invited/delivery/response status, form completion, survey completion timestamp and withdrawal exclusion state;
- all displayed proposal verdict and visibility fields;
- missing-domain, missing-purpose and missing-tag indicators and selections;
- public-entry sufficiency, taxonomy fit, taxonomy issue types, non-public-knowledge indicator and restricted notes.

Analysis rules:

- invited and responding researchers deduplicate `owner_id`; completed owner-record responses count assignment rows; unique reviewed records deduplicate `source_record_id`;
- sequence, supplementary and post-revision routes remain separate, with combined unique-record results deduplicated but every response retained;
- owner-label denominators include completed Fits / Does not fit / Unsure verdicts only;
- record-label patterns are one completed response, multiple concordant responses or mixed responses; no owner-majority classification is constructed;
- missing-label results are reported at response level and as any-owner at unique-record level;
- sufficiency and taxonomy fit use nonmissing completed owner-record responses;
- owner evidence can trigger adjudication but is not an authoritative gold standard;
- non-public project knowledge is flagged as project-informed evidence and does not penalise a register-only model.

The existing `project_owner_results.csv` is a result-table shell, not a raw REDCap ingestion schema. Candidate implementation needs a new exact raw-export schema and version-aware parser. It should reject duplicate assignment IDs, missing parent `owner_id`, invalid proposal cardinality, response values on hidden slots and contact fields in the analytical export. Notes are qualitative evidence and must not be parsed to manufacture structured outcomes.

## 10. Minimum synthetic QA matrix

### Offline dictionary and validator QA

| Case | Required assertion |
|---|---|
| Contact record | Only common/contact fields applicable; no assignment or survey response can validate. |
| Assignment record | Valid parent `owner_id`, unique assignment/Record ID keys, proposal provenance and no contact details. |
| One contact with several assignments | One-to-many join validates; every assignment remains one row with a distinct link. |
| Single- and multiple-project owners | Correct keys, route and batch; no response overwrites another project. |
| Sequence and supplementary | Controlled route codes; supplementary reason required only for route 2. |
| Proposal cardinality | One and multiple domains; one and two purposes; reject more than two purposes and invalid/empty required proposal sets. |
| Binary tags | Both positive and negative proposals displayed and answered; stable columns. |
| Fits / Does not fit / Unsure | Exact codes; explanation required for Does not fit/Unsure; hidden slots stay blank. |
| Missing labels | Yes requires at least one allowed missing label; proposed-and-Fits plus missing contradiction rejected. |
| Sufficiency | Sufficient, Partial and Insufficient accepted; conditional explanation for limited evidence. |
| Taxonomy fit | Fit, Partial Fit and No Fit only; issue type/note branches enforced; reject Cannot assess. |
| Non-public knowledge | Yes requires source/type note; no substantive confidential content requested. |
| Completion | Every displayed proposal verdict plus sufficiency and all triggered fields; no hidden non-proposed slot required. |
| Export/privacy | Analytical schema contains assignment rows only and none of name, email, contact source/note, invitation address or do-not-contact detail. |
| Prohibited metadata | Dictionary/survey contains no sample set, reserve, scratch response, disagreement or adjudication field. |

### Live PID 9149 QA before freeze

Use synthetic records only and record browser/export evidence for: admin contact record; contact with several assignments; single- and multiple-project owners; sequence and supplementary routes; all proposal cardinalities; positive and negative tags; every verdict/visibility branch; missing-label branches; Partial/Insufficient public entry; Partial Fit/No Fit taxonomy branches; Continue and decline acknowledgement; non-public-knowledge and quote-permission branches; Save & Return; incomplete and complete save/reopen; assignment-specific and contact-wide withdrawal/do-not-contact; failed delivery and reminder statuses; restricted contact export; identifier-free analytical export; respondent inability to access other records; respondent inability to see either admin form; absence of scratch/sample/reserve metadata; link disabling after withdrawal; and mobile plus supported desktop-browser usability.

Offline checks cannot establish survey-link isolation, browser branching, erasure of hidden values, staff permissions, export permissions, timestamp behaviour, invitation-log behaviour or mobile usability. Those require documented live QA in PID 9149. No such test was performed in this audit.

## 11. Proposed candidate-0.1 field structure

This is a design specification, not a REDCap dictionary. It proposes 152 user-defined fields: 27 in Owner Contact Admin, 39 in Owner Assignment Admin and 86 in Project Owner Review. Standard REDCap form-status fields and survey/audit timestamps are additional system-generated export columns, not manually defined fields.

### Owner Contact Admin (27 fields)

Common keys are physically placed on this first administrative instrument but populated on both contact and assignment records. `C` below means `[record_type] = '1'`. Every field is hidden from surveys. Direct-identifier fields are excluded from analytical exports; operational fields appear only in restricted contact exports.

| Field | Purpose | Type / choices or validation | Required | Branch | Identifier | Respondent visibility | Analytical export | Source |
|---|---|---|---|---|---|---|---|---|
| `owner_record_id` | REDCap record identifier | text; unique neutral ID | Yes | none | No | Hidden/admin | Assignment rows only as operational key | New |
| `record_type` | Distinguish contact and assignment records | radio: 1 Contact; 2 Assignment | Yes | none | No | Hidden/admin | Include | New, replacing combined `record_kind` semantics |
| `synthetic_qa` | Exclude synthetic runtime-QA records | yesno: 0 Formal/prospective; 1 Synthetic QA | Yes | none | No | Hidden/admin | Include/exclusion flag | New |
| `owner_id` | Pseudonymous researcher join | text; controlled unique pseudonym | Yes | none | No, but restricted link key | Hidden/admin | Include on assignment rows | Renamed from `owner_resp_id` |
| `oc_name` | Researcher name | text | Yes on contact | C | Yes | Hidden/admin | Exclude | New |
| `oc_email` | Approved invitation address | text; email validation | Conditional when contactable | C | Yes | Hidden/admin | Exclude | New |
| `oc_organisation` | Professional affiliation used for contact verification | text | No | C | Yes | Hidden/admin | Exclude | New |
| `oc_contact_source` | Public/approved source category | dropdown controlled after governance decision | Yes once searched | C | No | Hidden/admin | Exclude | New |
| `oc_contact_source_note` | Restricted source reference, not substantive project information | notes | Conditional for Other/ambiguity | C | Yes/potential identifier | Hidden/admin | Exclude | New |
| `oc_contact_search_date` | Date contactability checked | text; date_ymd | Yes once searched | C | No | Hidden/admin | Exclude or aggregate | New |
| `oc_contact_searcher_id` | Staff audit identifier | text; controlled code | Yes once searched | C | No | Hidden/admin | Exclude | New |
| `oc_contactability` | Contactability result | radio: 0 Unresolved; 1 Contactable; 2 Unreachable; 3 Identity ambiguous; 4 Do not contact | Yes | C | No | Hidden/admin | Aggregate only | Split from `owner_contact_disp` |
| `oc_contactability_note` | Reason for unresolved/unreachable/ambiguous outcome | notes; no project content | Conditional when code 2-4 | C and outcome 2-4 | Yes/potential identifier | Hidden/admin | Exclude | New |
| `oc_sequence_eligible` | Eligibility after contactability/person checks | yesno | Yes after resolution | C | No | Hidden/admin | Aggregate only | New |
| `oc_sequence_pos` | Frozen greedy-sequence position | text; integer >=1 | Conditional for sequence route | C and route 1 | No | Hidden/admin | Copied value included on assignment | Modified from `owner_sequence_pos` |
| `oc_sequence_ver` | Frozen sequence/frame provenance | text | Conditional for sequence route | C and route 1 | No | Hidden/admin | Copied value included on assignment if needed | New |
| `oc_recruit_route` | Researcher recruitment route | radio: 1 Sequence based; 2 Supplementary purposive; 3 Post-revision | Yes before contact | C | No | Hidden/admin | Copied value included on assignment | Modified from `owner_recruit_route` |
| `oc_invite_batch` | Initial/checkpoint invitation batch | radio: initial 10; day 14; day 21; day 28; supplementary; post-revision | Conditional when invited | C | No | Hidden/admin | Copied value included on assignment | Modified from `owner_invite_batch` |
| `oc_supp_reason` | Pre-contact supplementary rationale | notes; no model/coder/disagreement content | Conditional | C and route 2 | No | Hidden/admin | Restricted qualitative audit; approved code/text copied as needed | Modified from `owner_supp_reason` |
| `oc_first_invite_date` | Actual first invitation date | text; date_ymd | Conditional when invited | C | No | Hidden/admin | Aggregate flow only | Renamed from `owner_invite_date` |
| `oc_reminder_date` | Actual single reminder date | text; date_ymd | No; at most one | C | No | Hidden/admin | Aggregate flow only | Renamed from `owner_reminder_date` |
| `oc_delivery_status` | Separate delivery from contactability/response | radio: 0 Not sent; 1 Delivered/no failure; 2 Failed delivery; 3 Unknown | Yes once sent | C | No | Hidden/admin | Aggregate flow only | New, split from `owner_contact_disp` |
| `oc_response_status` | Researcher-level recruitment status | radio: 0 Not invited; 1 Invited; 2 Any partial; 3 Any complete; 4 No response; 5 Declined; 6 Withdrawn; 7 Closed | Yes | C | No | Hidden/admin | Aggregate/deduplicated flow | Modified from `owner_response_status` |
| `oc_withdrawal_status` | Scope of withdrawal | radio: 0 None; 1 Open assignments only; 2 Submitted responses and open assignments; 3 Contact withdrawn pending clarification | Conditional | C and response 6 | No | Hidden/admin | Exclude; apply governed derivation | New |
| `oc_withdrawal_date` | Date withdrawal received | text; date_ymd | Conditional | C and response 6 | No | Hidden/admin | Exclude | New |
| `oc_do_not_contact` | Suppress all further contact | yesno | Yes | C | No | Hidden/admin | Exclude | New |
| `oc_admin_note` | Restricted exceptional operational note | notes; never substantive project content | No | C | Yes/potential identifier | Hidden/admin | Exclude | New |

### Owner Assignment Admin (39 fields)

All fields use `[record_type] = '2'`, are hidden from the survey and are read-only after validated import except controlled status fields. `owner_id` is the common field defined above and is therefore not duplicated as a second dictionary field.

| Field(s) | Count | Purpose | Type / choices or validation | Required | Identifier | Analytical export | Source |
|---|---:|---|---|---|---|---|---|
| `owner_assignment_id` | 1 | Immutable owner-project assignment key; displayed as neutral reference | text; unique | Yes | No | Include | New |
| `source_record_id` | 1 | Stable DEA Record ID and cross-stream join | text; controlled format | Yes | No | Include | Existing Assignment Admin field |
| `official_project_id` | 1 | Public official Project ID | text | Yes | No | Include as public provenance | Existing |
| `project_title` | 1 | Frozen public title piped to survey | notes | Yes | No | Include | Existing |
| `datasets_used` | 1 | Frozen public datasets-used entry | notes | Yes | No | Include | Existing |
| `owner_recruit_route` | 1 | Assignment-level route provenance | radio: 1 Sequence based; 2 Supplementary purposive; 3 Post-revision | Yes | No | Include | Existing, remove 0 Not applicable |
| `owner_sequence_pos` | 1 | Copied sequence position | integer | Conditional for route 1 | No | Include | Existing |
| `owner_invite_batch` | 1 | Copied controlled invitation batch/checkpoint | radio as contact batch | Yes when invited | No | Include | Existing text field, changed to controlled radio |
| `owner_invite_date` | 1 | Date this assignment link was first sent | date_ymd | Conditional when invited | No | Include for flow | Existing |
| `owner_supp_reason` | 1 | Frozen pre-contact supplementary rationale | notes or controlled code plus text | Conditional for route 2 | No | Restricted analytical/audit use | Existing |
| `owner_response_status` | 1 | Assignment response state | radio: 0 Prepared; 1 Invited; 2 Partial; 3 Complete; 4 No response; 5 Failed delivery; 6 Declined; 7 Withdrawn; 8 Closed | Yes | No | Include | Existing, expanded codes |
| `owner_assignment_order` | 1 | Stable order of project links for one owner | integer >=1 | Yes | No | Optional analysis/provenance | New |
| `source_pop_ver` | 1 | Source-population provenance | text | Yes | No | Include | Existing |
| `production_ver` | 1 | Production-label output version | text | Yes | No | Include | Existing |
| `instrument_ver` | 1 | Standalone owner instrument version | text; fixed `owner-candidate-0.1` | Yes | No | Include | Existing name, new version namespace |
| `taxonomy_ver` | 1 | Taxonomy/definition provenance | text | Yes | No | Include | New |
| `proposal_output_sha256` | 1 | Byte-level proposal-source provenance | text; 64 lowercase hex | Yes | No | Include | New |
| `prop_d01` ... `prop_d12` | 12 | Proposed domain flags | yesno 0/1 | Yes | No | Include | Existing flags |
| `prop_p01` ... `prop_p08` | 8 | Proposed purpose flags | yesno 0/1; pre-import max two | Yes | No | Include | Existing flags |
| `prop_t01`, `prop_t02` | 2 | Binary tag proposal values, including No | yesno 0/1 | Yes | No | Include | Existing flags, changed presentation use |
| **Total** | **39** |  |  |  |  |  |  |

### Project Owner Review (86 fields)

The 80 inherited fields remain individually specified in `project_owner_existing_field_inventory.csv`. The table below is the candidate-0.1 overlay and supplies every field's proposed branch, visibility and export treatment. Let `A` mean `[record_type] = '2'` and `R` mean `([record_type] = '2') and ([po_ack] = '1')`. All classification branches combine `R` with the stated existing condition.

| Field(s) | Count | Purpose | Type / choices | Required and branching | Identifier | Respondent visibility | Analytical export | Source |
|---|---:|---|---|---|---|---|---|---|
| `po_intro` | 1 | Concise purpose, voluntariness, use and non-gold-standard framing | descriptive | A | No | Visible before acknowledgement | Exclude | Modified existing |
| `po_privacy` | 1 | Non-public-information warning, withdrawal deadline/contact and participant-information link | descriptive | A | No | Visible before acknowledgement | Exclude | New |
| `po_ack` | 1 | Choice to begin or decline | radio: 1 Continue; 0 I do not wish to participate | Required; A | No | Visible | Include in restricted flow only | New |
| `po_assignment` | 1 | Neutral assignment reference | descriptive piping `[owner_assignment_id]` | R | No | Visible after continue | Exclude | Modified existing |
| `po_project_title`, `po_datasets` | 2 | Public project context | descriptive piping frozen admin fields | R | No | Visible | Exclude as response fields; context retained from admin | Existing, guarded |
| `po_d01_label` ... `po_d12_label` | 12 | Proposed domain name and frozen short definition | descriptive | `R and [prop_dNN] = '1'` | No | Proposed slots only | Exclude descriptive fields | Existing, guarded |
| `po_d01_fit` ... `po_d12_fit` | 12 | Actual-project verdict for each proposed domain | radio: 1 Fits; 2 Does not fit; 3 Unsure | Required on same domain branch | No | Proposed slots only | Include | Existing, guarded |
| `po_d01_vis` ... `po_d12_vis` | 12 | Public-entry visibility for each proposed domain | radio: 1 Clearly; 2 Partly; 3 Not visible; 4 Unsure | Required on same domain branch | No | Proposed slots only | Include | Existing, guarded |
| `po_p01_label` ... `po_p08_label` | 8 | Proposed purpose name and frozen short definition | descriptive | `R and [prop_pNN] = '1'` | No | Proposed slots only | Exclude descriptive fields | Existing, guarded |
| `po_p01_fit` ... `po_p08_fit` | 8 | Actual-project verdict for each proposed purpose | radio: 1 Fits; 2 Does not fit; 3 Unsure | Required on same purpose branch | No | Proposed slots only | Include | Existing, guarded |
| `po_p01_vis` ... `po_p08_vis` | 8 | Public-entry visibility for each proposed purpose | radio: 1 Clearly; 2 Partly; 3 Not visible; 4 Unsure | Required on same purpose branch | No | Proposed slots only | Include | Existing, guarded |
| `po_t01_label`, `po_t02_label` | 2 | Tag definition plus explicit piped production proposal Yes/No | descriptive | R (always show both tags) | No | Visible | Exclude descriptive fields | Modified existing |
| `po_t01_fit`, `po_t02_fit` | 2 | Verdict on each proposed Yes/No tag assignment | radio: 1 Fits; 2 Does not fit; 3 Unsure | Required; R | No | Visible | Include | Modified existing |
| `po_t01_vis`, `po_t02_vis` | 2 | Whether public entry supports judging each tag proposal | radio: 1 Clearly; 2 Partly; 3 Not visible; 4 Unsure | Required; R | No | Visible | Include | Modified existing |
| `po_miss_domain`, `po_miss_purpose`, `po_miss_tag` | 3 | Structured missing-label indicators | radio: 0 No; 1 Yes | Required; R | No | Visible | Include | Existing, guarded |
| `po_miss_domains` | 1 | Missing substantive domain labels | checkbox: existing 11 substantive domains | Required; `R and [po_miss_domain] = '1'` | No | Conditional | Include | Existing, guarded |
| `po_miss_purposes` | 1 | Missing substantive purposes | checkbox: existing 7 substantive purposes | Required; `R and [po_miss_purpose] = '1'` | No | Conditional | Include | Existing, guarded |
| `po_miss_tags` | 1 | Missing positive cross-cutting tags | checkbox: existing two tags | Required; `R and [po_miss_tag] = '1'` | No | Conditional | Include | Existing, guarded; retain for explicit missing-label reporting |
| `po_sufficiency` | 1 | Overall public-entry sufficiency | radio: 1 Sufficient; 2 Partial; 3 Insufficient | Required; R | No | Visible | Include | Existing codes, modified wording/guard |
| `po_taxonomy_fit` | 1 | Actual-project taxonomy fit | radio: 1 Fit; 2 Partial Fit; 3 No Fit | Required; R | No | Visible | Include | Existing codes, modified wording/guard |
| `po_tax_issue` | 1 | Structured taxonomy problem type | checkbox: codes 1, 2 and 5 unchanged | Required; `R and (taxonomy fit 2 or 3)` | No | Conditional | Include | Existing, guarded |
| `po_note` | 1 | Required explanation naming every disagreement, uncertainty, visibility problem, missing label, limited entry or taxonomy issue | notes; do not disclose restricted content | Required; `R` plus parenthesised existing trigger set | Yes/potential identifying free text | Conditional | Include restricted qualitative field | Modified existing |
| `po_nonpublic` | 1 | Whether answers drew on knowledge beyond the public entry | radio: 0 No; 1 Yes | Required; R | No | Visible | Include | New |
| `po_nonpublic_note` | 1 | Source/type of non-public knowledge, not its substance | notes | Required; `R and [po_nonpublic] = '1'` | Yes/potential identifying free text | Conditional | Include restricted qualitative field | New |
| `po_quote_permission` | 1 | Direct-quotation permission | radio: 0 No direct quote; 1 Anonymous direct quote permitted | Required; R | No | Visible | Restricted governance field; not a scientific outcome | New |
| `po_other_comment` | 1 | Optional additional methodological comment | notes; warning against confidential/personal detail | Optional; R | Yes/potential identifying free text | Visible | Restricted qualitative field | New |
| **Total** | **86** |  |  |  |  |  |  |  |

The standard `project_owner_review_complete` export field and survey completion timestamp are required operational columns. They must not be replaced by a custom respondent-entered completion date.

### Exact new-field count

Relative to all 150 fields in the existing combined candidate-0.7 dictionary, candidate 0.1 proposes 37 new variable names: all 27 Owner Contact Admin names; four Owner Assignment Admin names (`owner_assignment_id`, `owner_assignment_order`, `taxonomy_ver`, `proposal_output_sha256`); and six survey names (`po_privacy`, `po_ack`, `po_nonpublic`, `po_nonpublic_note`, `po_quote_permission`, `po_other_comment`). Other proposed admin fields reuse or rename existing combined-administration concepts. Relative to the existing 80-field owner form alone, 66 administrative/common fields would sit outside that form, including reused combined-admin concepts.

## 12. Findings, blockers and decisions for Balint

### Blockers before dictionary construction

1. **Contact storage and link-delivery mechanism.** Approve the recommended same-PID restricted contact records plus external restricted mail merge of record-specific links, or require a separate contact store/project. If native REDCap invitations are mandatory, decide whether duplicating email on assignment records is acceptable. The audit recommends no duplication.
2. **Participant-information governance text.** Confirm the applicable privacy/contact information, withdrawal deadline, whether an external participant-information document is required, and the anonymous quotation options. The repository does not establish institutional ethics wording.
3. **Binary-tag proposal semantics.** Confirm that both production Yes and No values are “proposed tags” requiring Fits / Does not fit / Unsure and visibility judgements. This is the recommended interpretation and is necessary for the requested negative-tag QA case, but the inherited instrument asked only about positive tags.

### Required for candidate-0.1

- implement the two-record-type, three-instrument Classic model with common guards and `synthetic_qa` exclusion;
- use `owner_id`, `owner_assignment_id` and stable `source_record_id` with offline referential-integrity checks;
- remove scratch/sample/reserve/disagreement/adjudication fields from the standalone dictionary;
- add contactability, delivery, response, withdrawal and do-not-contact states without conflation;
- add participant information/acknowledgement, non-public-knowledge and quotation fields;
- retain all scientific codes, including owner taxonomy Fit / Partial Fit / No Fit only;
- store instrument, taxonomy, production and proposal-output provenance;
- create exact import, raw-export and analytical-export schemas plus version-aware validators;
- create synthetic contact/assignment fixtures and complete the offline and live-QA matrix before freeze;
- configure least-privilege staff roles, custom reports and assignment-only survey eligibility.

### Recommended improvements

- Send one invitation email containing multiple clearly labelled assignment links when an owner has several projects; do not redesign records to reduce the number of links.
- Use controlled codes for contact source, batch and statuses, with a restricted note only for exceptions.
- Place the conditional explanation close to the proposal blocks and use wording that makes disagreement as easy to record as agreement.
- Export contact and analytical data through named, tested reports and verify that an analytical export cannot contain any `oc_*` field.
- Use a custom operational dashboard filtered by record type and status; do not depend on the default dashboard's blank form icons.

### Optional / not recommended by default

- External REDCap user accounts, respondent DAGs, Survey Queue, repeating instruments and longitudinal events are unnecessary for the recommended model.
- A separate contact REDCap project is a stronger technical privacy boundary but adds cross-project operations; use it only if governance rejects same-project restricted records.
- A named-quotation option may be omitted entirely if the study will never publish named quotations.

### Documentation-only corrections during implementation

- Manifest row RED-002 and the current REDCap package README still describe the separate owner dictionary as superseded and the frozen candidate as one combined formal project. Preserve that history, but add a new standalone owner-candidate series and mark RED-002/current status consistently with v0.15.
- Do not rewrite candidate-0.7 history: the 80-field owner form was inherited unchanged, and the scratch candidate's live QA/freeze does not constitute owner-project QA.
- Add a distinct owner dictionary version history, QA record, setup checklist, import/export schemas and freeze evidence for PID 9149.

### Decision required before recruitment, but not before a draft dictionary

Freeze the public contact-source hierarchy, maximum search effort, treatment of identity ambiguity, permitted contact channels and responsibility for contact verification before any real contactability search or sequence is finalised. The current sampling README deliberately leaves these unresolved. Candidate 0.1 can define controlled fields and provisional enumerations, but it must not claim that the operational policy is frozen.

## 13. Recommended next implementation task

After the three blocker decisions are recorded, build a deterministic standalone `owner-candidate-0.1` source dictionary and validator from the frozen taxonomy and v0.15 protocol. Generate only blank templates and clearly synthetic fixtures. Validate record types, one-to-many joins, proposal provenance/cardinality, every survey branch, completion, export separation and absence of prohibited metadata. Then import only synthetic QA records into PID 9149, complete documented administrator and respondent live QA, compare source to live export narrowly, and freeze the owner instrument before registration. No owner cohort, contact file, invitation, assignment or scientific response should be created by that implementation task.
