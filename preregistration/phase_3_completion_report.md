# Phase 3 completion audit

## Conclusion

**Phase 3 complete.** The frozen source, deterministic cleaned population,
production classification and pre-existing model-evidence artefacts form one
coherent release tied together by exact paths, hashes, versions and offline
verification. No official validation sample has been drawn and formal
validation coding has not begun.

## Audit identity and objective

- Repository branch: `main`
- Repository commit audited: `e9d53023417348ad2784e629c855bf8d04f38df8`
- Audit date: 2026-07-15
- Objective: close Phase 3 by verifying source and cleaning provenance,
  production-model release identity, pre-existing evidence, and exact
  training/pilot exclusions without generating new classifications or
  prospective validation data.

The starting worktree was clean. The project virtual environment used Python
3.13.2. No repository-level `AGENTS.md` or separate Phase 3 plan was present.

## Source-register provenance

`data/register_manifest.json` identifies version `20260601` as current. The
default `load_raw_register()` call resolved
`data/dea_accredited_projects_20260601.csv`, containing 1,450 rows and the seven
expected source columns. The protected Windows working-tree SHA-256 is
`fc911d3c2e5cb0ec42ef04b1bfa2822bd3b358558ba8afbfd75b1048dcfe9892`.

The source manifest records LF Git-blob SHA-256
`abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d`.
The difference is line endings only: the working tree has 6,374 CRLF line
endings, the Git blob has 6,374 LF line endings, and in-memory CRLF-to-LF
normalisation makes the byte streams identical. The raw source was not edited.
Publisher, URL, snapshot and retrieval dates are recorded in
`package/01_source_and_cleaning/source_register_provenance.json`; an explicit
source licence is not recorded in the repository.

## Cleaning and population integrity

A deterministic in-memory rerun of `analysis/register_cleaning.py` with the
reviewed rulings in `analysis/register_duplicate_rulings.yaml` reproduced the
frozen cleaned CSV exactly:

- 1,450 raw rows;
- 1,344 after the DEA filter;
- 23 tier-1 and 12 tier-2 duplicate rows removed;
- one reviewed duplicate/update row removed;
- 1,308 retained records;
- 1,304 unique official Project IDs;
- 1,308 unique canonical Record IDs.

The four doubled official IDs are `2020/030`, `2022/036`, `2024/014`, and
`2024/095`, with two retained records each. `2023/211` is retained once as
unsuffixed Record ID `2023/211`. No Record ID has boundary whitespace, CR, LF,
tab, NBSP or prohibited controls; no duplicate arises after stripping. The
cleaned-register SHA-256 is
`a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1`.

## Production classification release

The release pointer selects
`analysis/outputs_classified_20260702_fable5/`. Its authoritative
`layer_classifications.csv` has SHA-256
`6f4ff530a3620167c37dc0ddee927ac592ca4ea2410c663535674503f811e299`,
1,308 rows and 1,308 unique clean Record IDs. Its ID set and all eleven source
and deterministic fields match the cleaned register exactly. There are no
missing, extra or duplicated IDs, no invalid classifications, no blank domain,
purpose or rationale fields, and every primary-domain linkage is valid.

All observed classification labels belong to the frozen taxonomy: 12 active
domain labels, eight active purpose labels and two cross-cutting tags. No
classification or coding decision was changed during this audit.

## Model, prompt, taxonomy and code provenance

- Provider/model: Anthropic `claude-fable-5`.
- Prompt and taxonomy version: `dict-1.0-rc2`.
- Taxonomy identity: dictionary `1.0-rc2`, ontology `v3.4-rc2`.
- Cache schema: 6.
- Model-visible evidence: `Title` and `Datasets Used`.
- Classifier/prompt implementation: `analysis/llm_theme_analysis_v3.py`,
  SHA-256 `51adce65e808290dc7750a15f334fdcb7794f6d426d4aa7dc3edd9e98f460eac`.
- Taxonomy SHA-256:
  `7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de`.
- Run metadata SHA-256:
  `0fd030520130542b70c3de719c136d9df6c66147c1bbfaa30108abb16e8671e4`.

The production prompt was assembled dynamically from the hashed classifier
code and hashed taxonomy. No standalone exact rendered prompt was recovered;
this is a packaging limitation, not a gap in the model/version/code/taxonomy
identity of the completed release.

## Fable run-to-run stability

The offline checker verified the two protected 201-record source caches without
writing output. Run 1 SHA-256 is
`e888422a3e46f8c3746c8560327e01fdb0e307491363e65a49c86ea78cb79156`;
Run 2 SHA-256 is
`77cd247f06b0d966334726e17de858d4b16c4f5bbe67e246b653e007fd676fff`.

- Domain exact: 191/201; mean Jaccard 0.974295190713.
- Purpose exact: 185/201; mean Jaccard 0.935323383085.
- COVID agreement: 201/201.
- Demographic-disparities/equity agreement: 197/201.
- Joint tag agreement: 197/201.
- All-component agreement: 171/201.
- Invalid or failed classifications: 0.

## Fable 5 versus GPT-5.5 evidence

Independent offline recomputation from raw label sets reproduced:

- 1,308 records;
- domain exact 1,065/1,308, mean Jaccard 0.904243119266055;
- purpose exact 1,108/1,308, mean Jaccard 0.8845565749235474;
- COVID matches 1,304; demographic-disparities/equity matches 1,263;
- joint tag matches 1,259; 49 records differ on at least one tag;
- four COVID mismatches and 45 demographic-disparities/equity mismatches;
- zero invalid GPT-5.5 classifications.

The pre-exclusion disagreement frame is 386 records: 186 domain-only, 143
purpose-only and 57 both, including 12 accompanying tag disagreements; 37
tag-only disagreements sit outside the frame. The post-exclusion frame is 380:
182 domain-only, 143 purpose-only and 55 both, including 11 accompanying tag
disagreements; the 37 tag-only cases remain outside.

## Exact exclusions and prospective boundary

The structural DOCX checker verified exact equality among the coder/trainer
cards, trainer pilot section, separate pilot reference and v8 exclusion CSV:
11 keyed worked examples, one unkeyed discussion case and 10 pilots, for 22
unique clean exclusions. All 22 exist in the cleaned register and are marked
`validation_included = no` in the structured training-material record manifest.

- Official validation sample drawn: no.
- Active or reserve assignments created: no.
- Formal validation coding started: no.
- Pre-registration pilot: pending; the pilot records are already excluded from
  later validation analysis.

## Frozen authoritative artefacts

Phase 3 freezes the authoritative June source snapshot, cleaning code and
reviewed rulings, 1,308-record cleaned population, taxonomy, production
classifier/version metadata, production classification output, Fable stability
evidence, cross-model evidence, and v8 exclusion membership. Their exact
release identity is recorded in
`package/02_taxonomy_prompt_and_model/production_release_manifest.yaml`.

## Working candidates outside the Phase 3 freeze

The validation protocol and final PDF, coder/trainer/pilot materials, REDCap
dictionary and codebook, sampling execution materials, and other prospective
validation instruments remain absent or working candidates. They must not be
marked finally frozen until collaborator review and the pre-registration pilot
are resolved. The structured training-material record manifest is likewise a
verified working candidate pending post-pilot freeze.

## Unresolved issues

No issue blocks Phase 3. The absence of a standalone rendered production prompt
is explicitly documented; the exact dynamic prompt implementation, taxonomy,
version and run configuration are hash-tied. All remaining items are post-Phase
3 pilot, collaborator-review or prospective-validation work.

## Scope assurance

This audit made no API or LLM call, regenerated no classification, changed no
raw source or recovered cache, drew no sample, created no assignment, began no
formal coding, exposed no restricted material, and performed no staging,
commit, push or upload operation.
