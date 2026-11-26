# Specification: taxonomy fit, descriptive and triangulation (post hoc, exploratory)

## Dates and status

- Specification written 26 November 2026. Not backdated.
- **Post hoc.** Prompted by drafting the paper, after the coder taxonomy-fit counts (S9T001–S9T008, RLR1T003–RLR1T004) and the fit-majority × sufficiency overlap (88 of 92 Sufficient entries Fit-majority, seen in an ad hoc count on 26 November 2026) had been seen.
- **Not preregistered.** Descriptive only: counts, shares and 95% Wilson CIs. No hypothesis tests, no p-values, no replacement contrast on a fit subset (dropped because fit and sufficiency select nearly the same records).
- **Coder notes have not been read** by anyone in aggregate for this analysis. The codebook below is fixed before the coding sheet is built. Part 3 follows the free-text analysis plan (`preregistration/post_registration/adjudication/free_text_analysis_plan.md`, ADJ-080): the study lead codes; no language model is the primary coder; counts of comments are reported, never prevalence; no quotations.
- Changes no protocol, taxonomy, production classification, preregistered analysis or canonical result.

## Populations and sources

Random baseline only (150 records, POST-009). Hard-case records are excluded from every part.

| Source | What is used | Location |
|---|---|---|
| Coder ratings | `taxonomy_fit` (1 Fit, 2 Partial Fit, 3 No Fit, 4 Cannot assess from register entry), `taxonomy_issues`, domains and purposes, `sufficiency` | Stage A panels (`build_stage_a_data`) |
| Coder notes | `sc_note` on responses rated Partial Fit or No Fit | frozen export (`scratch_coder_export_frozen_2026-08-24.csv`) |
| Post-coding feedback | themes by coder, fixed below from `coder_feedback_synthesis.md` (30 September 2026) | restricted |
| Adjudication | non-retracted primary findings on baseline records: family and mechanism | `adjudication_formal/analysis/findings_long.csv` (restricted; pre-secondary review) |
| Taxonomy review notes | TR-001 to TR-005 | `adjudication_formal/taxonomy_review_notes.md` |
| Owners | `po_taxonomy_fit`, `po_tax_issue` on the 30 analytically complete reviews; `po_tax_explain` mapped to themes only, never quoted | owner export of 13 October 2026 |

## Part 1. Descriptive (TFX1)

- **T001** Fit by coder and all coders, responses: counts, shares, 95% Wilson CIs. Reconciles to S9T001.
- **T002** Fit by record majority (two identical ratings; otherwise split): counts, shares, Wilson CIs. Reconciles to S9T003.
- **T003** Fit majority × sufficiency majority (records).
- **T004** Issue types by coder among Partial Fit and No Fit responses (multiple ticks allowed). Totals reconcile to S9T005 (28, 76, 11 of 88).
- **T005** Owners: fit and issue types on the 30 reviews.

## Part 2. Where flags concentrate (TFX2)

A response is **flagged** if rated Partial Fit or No Fit. Denominators exclude Cannot assess (an evidence outcome, not a fit judgement).

- **T001** For each label (domains, purposes, Unclear excluded): responses assigning it, flagged responses, flagged share; all coders, and excluding C03 (who gave 57 of the 88 flagged responses). Labels assigned in fewer than 10 responses are shown but marked.
- **T002** For each pair of labels in the same dimension assigned together in one response: responses, flagged, flagged share. Pairs with fewer than 5 responses are omitted.

## Part 3. Coding the notes (TFX3)

The script writes a restricted coding sheet of baseline notes on flagged responses, in a seeded random order (seed 20261126), with the title, datasets-used field, the coder's labels, fit rating and issue ticks shown, **and the coder ID hidden** (kept in a separate key). The study lead assigns one or more codes per note.

**Codebook (fixed 26 November 2026):**

| Code | Theme | Basis |
|---|---|---|
| T01 | No category for transport, travel or mobility | Feedback (C01, C02); TR-004 |
| T02 | No home for wellbeing (between Health & Social Care and Poverty, Wealth & Living Standards) | Feedback (C01, C02) |
| T03 | No home for third-sector or civil-society research | TR-005 |
| T04 | Overlap among Business & Productivity, Labour Market & Employment and Poverty, Wealth & Living Standards | Feedback (C01, C02) |
| T05 | Descriptive Monitoring as a default, or its boundary with Outcome Tracking or Life-Course / Trajectory Analysis | Feedback (C02, C03) |
| T06 | Policy Evaluation / Impact Analysis boundary (named intervention; against Outcome Tracking) | Feedback (C01, C03); TR-002 |
| T07 | Scope of the Demographic disparities / equity tag | TR-001 |
| T08 | Whether a dataset alone can set a domain or purpose | TR-003 |
| T09 | Other missing or poorly represented domain (e.g. age group, family or household, mental health, region, foreign affairs) | Feedback (C01) |
| T10 | Other missing purpose (e.g. historical linking, description distinct from monitoring) | Feedback (C01) |
| T11 | Thin evidence rather than a taxonomy problem | Feedback (C02, C03); CAL-FORMAL-003 |
| T12 | Ambiguity of Migration & Demographics or Environment & Agriculture | Feedback (C03) |
| T99 | Other (inductive; give a short label) | — |
| T00 | Note gives no taxonomy reason | — |

Rules: a note may take several codes; T00 only alone. Inductive T99 labels are harmonised after coding, with counts before and after.

## Part 4. Triangulation (TFX4)

A matrix with one row per theme (T01–T12, plus "missing category, any": T01, T02, T03, T09, T10) and one column per source type:

1. **Coders:** notes (number of notes and distinct coders, from Part 3) and post-coding feedback (coders raising the theme, fixed above).
2. **Adjudication:** baseline findings by mapped mechanism, split by family, and the related TR note. Mapping, fixed here: T01 TR-004; T02 mechanism 38; T03 TR-005; T04 mechanisms 3, 9, 41; T05 mechanisms 11, 36, 42; T06 mechanisms 12, 16, 43 and TR-002; T07 mechanisms 28, 29 and TR-001; T08 mechanism 24 and TR-003; T11 family 3 (evidence problem); T12 mechanism 7; "missing category, any" mechanism 34 and family 4.
3. **Owners:** owner reviews whose `po_tax_explain` maps to the theme (mapped by the study lead; count only).

Part 2's flagged shares for the label sets of T04, T05, T06 and T12 are shown alongside as supporting evidence.

A theme is **convergent** if at least two of the three source types (coders, adjudication, owners) point to it. Coders' notes and feedback come from the same three people and count as one source type. Until Part 3 is coded, the notes column reads "pending" and convergence is computed from the other sources only, and labelled so.

## Outputs

Aggregate tables and run metadata to `preregistration_restricted/taxonomy_fit_exploratory/` (gitignored). The coding sheet and its key also go there and stay restricted, because notes can identify records. No record identifiers in any aggregate table. Code only in this folder.
