# Phase 5 completion report

## Conclusion

**Phase 5 candidate package complete and ready for live REDCap import and runtime QA.** The instrument remains a working candidate; no live import, pilot, assignment loading, or response collection occurred.

## Audit identity and objective

- Repository: `C:/Users/balin/Desktop/ADR_DEA_project`
- Branch: `main`
- Audited HEAD: `6da64a4eb003396856d85fe4fcf71cbe886be1bb`
- Starting worktree: clean
- Objective: construct and locally verify one importable REDCap candidate for scratch-coder and project-owner review without real assignments or outcomes.

## Blinding contradiction resolved

Protocol paragraphs 87–89 were applied as authoritative. In the coder handout, the heading `Fields you will see but not edit` became `Fields used in REDCap`. The stale assignment example `baseline_C02_2024_123` was replaced by opaque fictional `A7K3M9Q2`. The table now states that assignment ID, project title, and datasets used are visible (the latter two read-only), while reviewer/coder ID, source Record ID, official Project ID, sample/stratum fields, and model/comparison fields are hidden.

Coder handout SHA-256 changed from `5f0c4931306067100ab6e7ae1d1bd3ce2487ebb4ac5c7ed734c491d9f7dec0ea` to `cb0282696fe574a815937d181960a791b9aaf3c6cbff105d82491d69b34cde71`. The trainer handout (`ac80a5b5090aa7dbbb86116573bd1334af794c9ed5898ccd3a3fdfe84c9ecfd7`) and pilot/debrief reference (`9e541eb0b6fc2a874cdcb98c53f6d0ea0ceae3d18bb40066b26e3867219f551e`) contained no stale text and were unchanged. All DOCX ZIP CRCs and XML parts parse. Worked examples, answers, pilot IDs, taxonomy rules, protocol text, and exact 11 + 1 + 10 membership were unchanged.

## Project architecture

One non-longitudinal project has three instruments: hidden `assignment_admin`, reviewer-facing `scratch_coder`, and reviewer-facing `project_owner`. `assignment_id` is the unique record key. One reviewer-record assignment is one REDCap record and one export row. Separate assignments for the same source project retain unique opaque assignment IDs and share hidden project-level clustering identifiers.

Administrative fields cover reviewer/source/project linkage, frozen title and datasets, sample set, hard stratum, validation inclusion, active/reserve status, display order, batch, source/production/instrument versions, clustering, owner identifiers, and proposed-label flags. Every administrative field is marked hidden-survey and read-only; live user-rights verification remains mandatory.

## Scratch-coder instrument and rules

The coder sees only opaque assignment ID, title, datasets used, evidence/blinding declarations, domains, purposes, two tags, sufficiency, taxonomy fit/issue type, confidence, and conditional notes. The dictionary reproduces 11 substantive domains plus Unclear, seven purposes plus Unclear, and exactly two canonical tags from `dict-1.0-rc2`.

The local validator independently enforces Unclear exclusivity, one-to-two purposes, required core fields, exposure explanation, taxonomy issue type, and notes for exposure, Partial/Insufficient evidence, Partial/No Fit, or Low confidence. `@NONEOFTHEABOVE` and `@MAXCHOICE=2` are also recorded for live compatibility testing.

## Project-owner instrument and rules

For every canonical proposed label, an imported hidden flag controls a short label/definition display, a required Fits/Does not fit/Unsure response, and a required public-entry visibility response. Separate questions capture missing substantive domains, purposes, and tags, plus sufficiency, taxonomy fit/issues, and required explanation. The validator rejects missing displayed-label responses, unresolved branches, disagreement/uncertainty without explanation, and a proposed-and-fitting label simultaneously claimed as missing. Multiple owner rows remain assignment-level while sharing hidden project clustering.

## Taxonomy, protocol, and blinding alignment

No further substantive contradiction was found. Protocol and handouts agree on domain/purpose cardinality, Unclear use, tag coding, Sufficient/Partial/Insufficient, Fit/Partial Fit/No Fit, High/Medium/Low confidence, and required explanatory notes. Owner visibility categories are a documented candidate operationalisation requiring collaborator and pilot review.

Scratch displays contain no source ID, reviewer ID, sampling metadata, disagreement status, active/reserve data, model output/rationale, owner response, or other coder response. Owners see proposed labels because review is their task, but not rationales, model/comparison provenance, sampling data, or other responses.

## Candidate identity and supporting artefacts

The 29,178-byte `redcap_data_dictionary_candidate.csv` has 137 rows and SHA-256 `c905e60f5908da48451c1135e7def57e9f0d9dc855f2553f61993f5282b160ac`. Key supporting hashes are:

- field/response specification: `6626563a7c37de4de4633c47f1e74f1d17fe4258e1e442512c09ae5ab75aa996`;
- branching/validation specification: `83bfc93280fe8c02fdb349ff1ecd40acd7ed55df7aca3d2a21f89cd9727f589b`;
- assignment template: `61bc06ad478dda027e3cb844f6d66fcc3eff7acd3ecc59083e3b9fc61ae06318`;
- export schema: `d9b57700c661acca58c9ec97d6209cf1884aa42968ab50551deaa97b53f90c3f`;
- HTML preview: `cc2109d138f7775564823e158811c0e2118ee914173ebf16303a8b76cd9ff698`;
- validator: `2985ceb1323be603a8480cd5abc924266766fa3a301f37c4d29677968b725a1a`;
- validator tests: `65c746043e75691c6721303b4db061d9bc1366803955b6b3dc7ae9f2a2e87a33`;
- synthetic fixture: `a17e519724f7cce9c09323a31002c90385424ecdffcf8500425d969bd9637eab`.

The package also contains the codebook, taxonomy-variable mapping, project-setup checklist, instrument-QA checklist, version history, and blank live-runtime QA template. The deterministic builder can regenerate the dictionary and schemas from the frozen taxonomy.

## Synthetic QA and security

Twenty-three clearly fictional scenario records cover all 22 requested scratch and owner conditions, including two separate owners sharing one synthetic project. Nineteen are intended-valid and four intended-invalid; all behaved as expected. Thirty-two focused validator tests cover structure, names, branches, checkbox codes, taxonomy drift, response logic, blinding, synthetic-ID safety, schema alignment, clustering, and no-write check mode.

The public candidate contains no API token, password, email, live survey link, contact, real assignment row, real Record ID, response export, sample identity, or model-output leakage. `.env`, `.env.*`, token files, the restricted tree, and post-registration REDCap exports are ignored. Future response data are classified restricted.

## Manual steps remaining

Before the excluded pilot, a human must create a synthetic non-longitudinal UCL REDCap test project, import the candidate, record the REDCap version and warnings, configure surveys and rights, test action tags and branching on desktop/mobile, verify one-row-per-assignment export and multiple-owner behaviour, capture approved evidence, delete synthetic data, resolve defects, and record pilot readiness in the blank live-runtime QA template.

The dictionary, specifications, preview, checklists, and training handouts remain working candidates pending live QA, collaborator review, training, the excluded pilot, and resolution of findings. No unresolved local Phase 5 implementation issue remains; live-instance compatibility is the explicit outstanding risk.
