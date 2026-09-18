# Addendum — Exploratory record-level ratings: register-entry information and taxonomy fit (v1)

## Dates

- Specification: specified, and instruction issued, on or before 17 September 2026 (investigator-attested).
- Addendum creation date: 2026-09-18 (created 2026-09-18). Not backdated.
- This addendum is committed alone, before any analysis code for this run is written.

## Status

Exploratory and not preregistered. The protocol search (below) found no preregistered specification of record-level rating patterns or coder-by-coder cross-tabulations of register-entry information or taxonomy fit, so no result from this run is labelled preregistered.

Stream: Scratch-coder analysis (Stream A). Separate from the pairwise α run and the figure pipeline. Changes no canonical artefact.

## Investigator hypothesis

C03 may apply the register-entry information and taxonomy fit categories more strictly rather than being less certain (interpretive findings F.4, F.20). This run does not test that hypothesis formally; it produces descriptive, exploratory record-level views bearing on the question.

## Prior state of knowledge

Record-level rating patterns had not previously been examined for the formal panel. The following had already been seen before this addendum:

- Coder-level and majority totals for register-entry information (S8T001–S8T004) and taxonomy fit (S9T001–S9T004).
- The confidence exploratory results (SCF1T001–SCF1T010).
- The pairwise α exploratory results.

## Search results

### Protocol search

Searched: `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` (PRO-018, SHA-256 `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77`), full text of `word/document.xml`. Terms: record-level, record level, cross-tabulation, coder-by-coder, pairwise rating, rating pattern, heatmap, per record, sufficiency record, taxonomy record.

- Record-level coder rating patterns (tuples of C01/C02/C03 ratings) for register-entry information or taxonomy fit: **not found** in the searched location.
- Coder-by-coder cross-tabulation of sufficiency or taxonomy fit: **not found** in the searched location.
- Related record-level analyses that are specified: record-level Jaccard similarity between the production model and each scratch coder (Section 8.4); record-level instability diagnostics for production model stability (Section 4). Neither is a coder-by-coder rating cross-tabulation.

### Prior-result search

Searched: all tracked and untracked files in the repository excluding `venv/` and `.git/` (grep for record-level, record level, cross-tabulation, coder-by-coder, pairwise rating, rating pattern); git history (commit messages; pickaxe for record_level_rating); `analysis/outputs_validation_scratch_20260824/` (all CSV outputs); `analysis/scratch_coder_results/results.md` (all S8/S9 table IDs); `preregistration_restricted/pilot_private_review/` (pilot data).

- Record-level coder rating patterns or coder cross-tabulations for register-entry information or taxonomy fit in the formal panel: **not found** in the searched locations.
- Pilot private review: `preregistration_restricted/pilot_private_review/` contains pilot-phase coder divergence summaries and case-review files. These use pilot data (not the formal 225-record panel) and do not contain the analyses specified here.

## Restricted-output location

The project stores restricted analysis outputs under `preregistration_restricted/`. Restricted outputs for this run will be placed in `preregistration_restricted/record_level_ratings_exploratory/`. Their paths and SHA-256 hashes will be recorded in `analysis/record_level_ratings_exploratory/run_metadata.json`, following the convention used by exploratory analysis runs that do not have dedicated manifest artifact IDs.

## Data, population authorities and code (reused, not modified)

| Role | Artifact ID | Path | SHA-256 |
|---|---|---|---|
| Raw export | POST-028 | `preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv` | `29809349496bae050b66c158a595f235431b7457982990b8c4c29cf2abd0ee1d` |
| Baseline sample | POST-009 | `preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv` | `0ea3ccab580d1037bf4e35695f2554a69ef79628b53692b2664a2f251f6a4a11` |
| Hard-case sample | POST-011 | `preregistration_restricted/sampling/official_draw_20260724/hard_active.csv` | `582f248d39d911275e4e4f11bc34660b51809a1ed7c330644f9e2036299cfb11` |
| Assignment crosswalk | POST-019 | `preregistration_restricted/assignments/formal_validation_20260724/formal_assignment_crosswalk.csv` | `96daddae15848331f7bef486a6c630e00de598ddb91f5ce317457e09a8bdd666` |
| Protocol | PRO-018 | `preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx` | `fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77` |
| Taxonomy | MOD-001 | `taxonomy_data_dictionary.yaml` | `7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de` |
| Production model | MOD-006 | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` | `6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299` |

Code reused without modification:

- `analysis/scratch_coder_stage_a/load.py` — data loading and authority verification.
- `analysis/scratch_coder_stage_a/panels.py` — `build_stage_a_data` (formal panel reconstruction).
- `analysis/scratch_coder_stage_a/config.py` — `CODERS = ("C01", "C02", "C03")`.
- `analysis/scratch_coder_stage_a/sufficiency.py` — `SUFFICIENCY_LABELS`, `majority_category`, `SPLIT`.
- `analysis/scratch_coder_stage_a/taxonomy.py` — `FIT_LABELS`.
- `analysis/visualisations/figure_style.py` — shared matplotlib style (Arial, `svg.fonttype="none"`).

Canonical per-coder and majority exports used for reconciliation:

- `analysis/outputs_validation_scratch_20260824/sufficiency_response_distribution.csv` (S8T001/S8T002)
- `analysis/outputs_validation_scratch_20260824/sufficiency_record_distribution.csv` (S8T003/S8T004)
- `analysis/outputs_validation_scratch_20260824/taxonomy_fit_response_distribution.csv` (S9T001/S9T002)
- `analysis/outputs_validation_scratch_20260824/taxonomy_fit_record_distribution.csv` (S9T003/S9T004)

## Analyses

Populations: baseline (150 records) and hard-case (75 records), analysed separately, never pooled. Hard-case outputs are labelled **DIAGNOSTIC — non-representative**.

### Questions and categories

- **Register-entry information:** Sufficient > Partially sufficient > Insufficient. All ordered.
- **Taxonomy fit:** Fit > Partial Fit > No Fit (ordered), plus **Cannot assess from register entry** (not on the ordered scale).

Majority: the category chosen by at least two of three coders; otherwise No majority (reusing `analysis/scratch_coder_stage_a/sufficiency.py:majority_category`).

### Analysis 1 — Rating patterns

For each population and question: each record's pattern (C01, C02, C03); a pattern count table (every observed pattern, count, percentage, majority category, block); block summary (unanimous, two agree, all different).

### Analysis 2 — Pairwise cross-tabulations

For each population, question and coder pair (C01–C02, C01–C03, C02–C03): full cross-tabulation; direction summary on the ordered scale (higher, same, lower); for taxonomy fit, records where either coder chose Cannot assess, by which coder(s).

### Analysis 3 — Downgrade pattern for each coder

For each population, question and coder X, among records where the other two coders agree on an ordered category: counts of X rating same, higher or lower; broken down by the shared rating.

### Analysis 4 — Record-level heatmaps

Shared style module (Arial, `svg.fonttype="none"`). Category colours follow the pass-3 Figure 2 palette: register-entry information greens (Sufficient #246B45, Partially sufficient #78AF82, Insufficient #D6E8D8); taxonomy fit purples (Fit #5A4A86, Partial Fit #9B8CC0, No Fit #DED8EC, Cannot assess from register entry #5F5F5F hatched); No majority #888888 (register-entry information) or #AEAEAE (taxonomy fit).

Paper versions (no record IDs): `analysis/record_level_ratings_exploratory/figures/`. Internal versions (with record IDs): `preregistration_restricted/record_level_ratings_exploratory/`.

## Excluded

Tests, p-values, intervals or association measures. Statements about coder quality, competence or reliability; describing a coder as wrong. Treating Cannot assess or No majority as points on the ordered scale. Pooling baseline and hard-case. Modifying or reimplementing shared code; changing category names or the majority rule. Editing canonical results, the figure pipeline or any log. Further analyses require a new dated addendum.
