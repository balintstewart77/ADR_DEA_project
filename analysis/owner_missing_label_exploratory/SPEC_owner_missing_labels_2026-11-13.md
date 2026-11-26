# Specification: owner missing-label reports, project knowledge and rule adherence (exploratory)

Written 13 November 2026, before the analysis code and before any owner free text below is read in aggregate. Exploratory and post hoc; not preregistered. Protocol RQ6 (§8.6) asks how often owners identify missing labels; this analysis asks why.

## What is already known

The structured owner results (Supplementary Tables S12a–S12e) were viewed on 12–13 November 2026. Owners named a missing label (DEV-007 rule) on 15 of 30 records. Five reviews reported relying on non-public knowledge and one was unsure, so at least 9 of the 15 came from reviews reporting no such reliance. Tag explanations were read for the DEV-007 classification on 19 October 2026. No other owner free text has been read in aggregate for analysis. The study lead may have seen owner evidence record by record during route-2 adjudication. Route-2 adjudication findings are held until 20 November 2026 and are not used here.

## Questions

1. **Project knowledge.** Are records with a missing-label report the ones whose owners relied on knowledge outside the public entry, or rated the entry less than sufficient?
2. **Rule adherence.** Owners were not trained in the taxonomy, but the instrument stated the rules at the point of selection. A Research Domain was to be selected "only when it is a substantive subject of the project", not "solely because the project uses a related dataset or variable, examines a population with a related characteristic, or mentions it as context". An Analytical Purpose was to be selected only as "a substantive aim of the project", not "solely because it describes a method, analytical step or secondary feature", and with no more than two purposes in total. Do owners' stated reasons for missing labels meet these rules?
3. **Source of the basis.** Does each stated reason rest on something in the public entry, which is the title and datasets shown to the owner, or on knowledge of the project?

## Data

- Final owner export: SHA-256 `792afed9…`, confirmed final on 12 November 2026.
- Frozen owner dictionary.
- `owner_completeness_check.csv`: analytically complete reviews only, 30 reviews, one per record.
- DEV-007 rules as in `run_owner_analysis.py`. A label already proposed is not a missing label; such selections are counted separately and not coded.
- The public entry is the `project_title` and `datasets_used` fields in the export, which are what owners saw.

## Part A: cross-tabulations (structured fields only)

Unit: the review (equivalently, the record).

- **OMX1T001.** Any missing label (DEV-007; and raw) against `po_nonpublic` (No / Yes / Unsure), overall and by layer.
- **OMX1T002.** The same against `po_sufficiency` (Sufficient / Partial / Insufficient).
- **OMX1T003.** The same against `po_taxonomy_fit` (Fit / Partial Fit / No Fit).
- **OMX1T004.** Label level: each named missing label (DEV-007) against `po_nonpublic` for its review.
- **OMX1T005.** Mechanical rule checks:
  - reviews whose missing purposes would take the record above two purposes;
  - reviews selecting an already-proposed label (DEV-007);
  - missing-label selections with and without a basis explanation.

Counts only. No tests or intervals. Responses cluster within seven researchers. The number of researchers contributing to each non-empty cell is recorded in the restricted output only, and never published.

## Part B: missing-label explanations (free text)

Corpus: the `po_miss_domain_basis`, `po_miss_purpose_basis` and `po_miss_tag_basis` text of analytically complete reviews. Unit of coding: each missing label named under DEV-007, read with its layer's basis text. One text may cover several labels; each label is coded separately where the text distinguishes them, and otherwise jointly.

Two codes per label, defined here before reading.

**B1. Rule reading.**
- **S (substantive):** the explanation presents the label as a substantive subject (domain) or aim (purpose) of the project.
- **I (incidental):** the explanation ties the label only to something the instrument's rule excludes: a dataset, variable, population characteristic or contextual mention (domains), or a method, analytical step or secondary feature (purposes).
- **U (unclear):** too brief or ambiguous to decide.
- **N:** no explanation provided. Blank text means not provided; it is not evidence either way.

B1 judges the explanation against the rule. It does not judge whether the label is correct; adjudication decides that.

**B2. Source of the basis.**
- **E:** what the explanation cites is visible in the title or datasets shown.
- **K:** it rests on project information not in the title or datasets.
- **B:** both.
- **U:** cannot tell.

Tags have no substantive-subject reminder. For tags, B1 records whether the explanation states that demographic or equality-relevant group comparison is central (S), or only that groups appear (I), following the tag definition owners were shown.

Other owner free text is summarised descriptively by field, with the number of comments contributing and no prevalence:
- sufficiency explanations;
- non-public knowledge notes;
- visibility explanations;
- taxonomy explanations;
- other comments;
- the one not-fit explanation.

Tag-status explanations are not recoded: the 19 October DEV-007 classification stands.

**Coder.** The free-text plan (§6) says no language model is the primary coder, and prefers a model from a different family from the production model. Owner comments are outside that plan's scope, but its reasoning applies. Candidate codes are therefore drafted by Claude Opus 5.5, which is from the same family as Fable 5, with a written rationale for each. They become analysis codes only after the study lead verifies each one, line by line. A blank sheet with the codes hidden is provided so that the study lead can code blind first. If that is done, agreement is reported descriptively.

## Reporting

- Counts of labels, explanations and records, never prevalence.
- Owner comments are not quoted in any publication without permission (protocol §11). Paraphrases omit non-public project information.
- All outputs stay in `preregistration_restricted/owner_responses/analysis/missing_label_exploratory/`.
- The code sits in `analysis/owner_missing_label_exploratory/` and reads restricted inputs only.
- This specification's SHA-256 is recorded in the run metadata.
