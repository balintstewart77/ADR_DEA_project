# Methods Log — DEA Project Classification

This document records the methodological decisions behind the LLM classification pipeline for DEA-accredited research projects. It is organised by decision area (data preparation → ontology → pipeline → validation)  so that each can be read as a coherent narrative with its full rationale and change history. Commit hashes and dates are cited inline throughout.

---

## 1. The classification task

The unit of classification is a **DEA-accredited research project** as recorded in the UKSA accredited-projects register. Each project record includes a Project ID, title, accreditation date, researcher names, legal basis, datasets accessed, and processing environment. The register is published by the UK Statistics Authority and is the authoritative record of all projects accredited under the Digital Economy Act 2017. The register also includes projects accredited under the Statistics and Registration Service Act 2007 (SRSA), which we exclude in this analysis, because SRSA is limited to unpublished data held directly by the ONS, and is tailored for general statistical/deomsgraphic research.

The original motivation for an LLM-based classification was to provide a more semantically-aware classification than that done in the July 2025 analysis in DEA_projects_analysis, which used bag-of-words / TF-IDF to track changes in research themes over time (initial script introduced in `242ce2b`, 2026-03-25). The v1 script classified all project titles into 14 research themes using the Claude API, with batching, caching, trend tables by year/quarter, and a generated narrative policy summary. It was superseded by the three-layer v3 framework.

This 3-layer classification framework assigns each project three independent facets — substantive domain, linkage mode, and analytical purpose — using the project's title and datasets-used field as input. The classifier is Claude Opus 4.6, prompted with label definitions, decision rules, and worked examples, producing structured JSON output validated against a Pydantic schema.

---

## 2. Data preparation

## 2. Data preparation

The classification operates on the UK Statistics Authority's public register of DEA-accredited research projects. The register is published as a periodically updated spreadsheet and contains systematic data-quality defects in its free-text fields. The steps below define how the raw register is turned into the cleaned input consumed by the classifier.

A single shared loading pathway, `analysis/register_cleaning.py::clean_register_dataframe()`, serves both the classifier and the dashboard, so both operate on identically prepared data except where explicitly noted.

### Input data

The input is a snapshot of the register:

- File: `data/dea_accredited_projects_20260325.csv`
- Rows: 6,229
- Scraped: 2026-03-25
- Scraper: `scrape/scraper_20260325.py`
- Committed: 2026-04-07, commit `8dd315b`

The scraper handles the post-March-2026 spreadsheet download format.

### DEA-only legal-basis filter

The raw register includes projects accredited under multiple legal gateways. A filter retains only rows whose `Legal Basis` field contains `Digital Economy Act`, case-insensitively, scoping the analysis to DEA-accredited projects.

This was implemented inline initially in `6e067f4` and later moved into the shared loading pathway.

### Duplicate handling

Inspection of the register identified three categories of duplicate record:

1. **Same title, different Project IDs**  
   These are genuinely distinct projects, often re-accreditations of similar work by the same team in a later year. They are retained as separate records.

2. **Same Project ID, different titles**  
   These are distinct projects sharing an ID through register error. They are disambiguated by appending a `/a`, `/b` suffix to form a unique `Record ID`.

3. **Same Project ID and same title**  
   This subdivides into:
   - clerical double entries, where rows are substantively identical;
   - fragmented records, where rows share ID and title but differ materially in datasets accessed and/or researchers listed.

The current duplicate policy is content-aware: `apply_duplicate_policy()`, revised on 2026-05-21. Rows sharing Project ID and title are compared across their remaining fields. Substantively identical rows are deduplicated. Rows sharing Project ID, title and accreditation date but differing in datasets or researchers are treated as a single accreditation whose record was fragmented across rows, and are merged by taking the union of their dataset and researcher lists. Any remaining ambiguous cases are flagged to a review file rather than silently collapsed.

Running the analysis confirmed that no ambiguous cases remain: re-accredited projects with the same title but a different date are issued different Project IDs.

This policy replaced an earlier approach that keyed only on Project ID and title and retained the first occurrence. That earlier approach silently discarded differing dataset and researcher information in the problematic sub-type above. Because linkage classification depends on the dataset list, this had corrupted classification inputs for an unknown number of projects, making the content-aware policy necessary.

#### Known issue: project `2023/113`

The earlier duplicate policy could not disambiguate same-ID/same-title rows differing in other fields, so one such case, `2023/113`, was handled by a hardcoded special-drop.

This later became actively harmful. `2023/113` appeared in the raw register as two rows: one accredited under SRSA 2007 and one under the DEA. The DEA-only legal-basis filter already removed the SRSA row, so the special-drop then deleted the surviving legitimate DEA row. As a result, `2023/113` was wrongly absent from the dashboard.

The hardcode was removed on 2026-05-21. The case is now handled correctly by the general duplicate policy after the legal-basis filter is applied.

### Register text cleaning

The register's `Title` and `Datasets Used` fields contain character-encoding corruption, whitespace artefacts, HTML entities and inconsistent formatting.

Two canonical functions in `dashboard/dataset_normalisation.py` perform this cleaning:

- `_clean_title_text()`
- `_clean_datasets_text()`

Both the classifier and dashboard receive register text cleaned by these functions.

During this work, duplicate copies of dataset-cleaning logic were found in both `analysis/quality_check.py` and the classifier prompt-construction code. A separate finding established that the title field was not being cleaned before reaching the classifier. These paths were consolidated onto the canonical functions.

The cleaning removes spreadsheet carriage-return artefacts and HTML-like tags, decodes HTML entities, normalises whitespace, including non-breaking spaces and soft hyphens, strips embedded newlines, and repairs a defined set of known character-encoding corruptions, including corrupted dashes, quotation marks and apostrophes.

Encoding-corruption repair is deliberately confined to patterns whose intended character can be confidently inferred. Ambiguous corruption is left in place and recorded rather than guessed at.

Across the register, this cleaning changed the title or dataset text of **192 project records**.

### Provider parsing

Within the dataset field, distinct data providers are identified by a provider-header regex that inserts boundaries between providers' dataset lists. Provider identity feeds the Layer B linkage judgement.

The regex was found to exist in two divergent copies whose provider vocabularies differed. This meant the QA tooling and classifier had been recognising different sets of providers.

The logic was reconciled into a single canonical version and verified against the register:

- every recognised provider was confirmed to appear genuinely in the register;
- entries with no occurrences were excluded;
- a complete scan confirmed that remaining unrecognised colon-patterns are dataset-name fragments, not missed providers.

A related defect, in which the regex's interaction with whitespace normalisation introduced stray line-break artefacts, was also corrected.

### Dataset name normalisation

Dataset-name normalisation maps variant spellings of a dataset to a canonical form. It uses a deterministic regex-alias table:

- `DATASET_ALIASES`
- `normalise_dataset_name()`
- Location: `dashboard/dataset_normalisation.py`

This deterministic approach was chosen over fuzzy or probabilistic matching for auditability and reproducibility. A hand-maintained alias table is transparent and inspectable, whereas fuzzy matching introduces a tunable threshold and the risk of non-deterministic or difficult-to-audit merges.

The normalisation system also strips geographic and year-range suffixes, corrects known typographic variants, and groups datasets into families such as Census, ASHE, Labour Force Survey and COVID-19 datasets.

Iterative refinement reduced the raw register's variant dataset names to **321 canonical forms**. Supporting QA tooling and an audit script accompany the normalisation system.

#### Scope decision: classifier receives cleaned but non-canonicalised dataset text

Dataset-name canonicalisation is applied by the dashboard but is not applied to the classifier input.

The classifier receives cleaned but non-canonicalised dataset text. This is deliberate: canonicalisation tuned for dashboard grouping could mask distinctions the linkage classification depends on, for example by collapsing a pre-linked cross-domain dataset towards a generic form.

Whether dataset normalisation should precede classification is recorded as an open question for later evidence-based evaluation.

### Provider and institution name normalisation

Provider names are normalised on the same deterministic regex-alias principle, using:

- `normalise_provider_name()`
- `PROVIDER_ALIASES`

This standardises abbreviations and corrects typographic variants.

#### Known issue: ISER transposition

From its introduction in `e9be89b` on 2026-04-06 until correction in `6df8226` on 2026-05-19, a window of roughly 43 days, the provider **Institute for Social and Economic Research** was incorrectly mapped to the transposed form **Institute for Economic and Social Research**.

Both the mapping table and its test were corrected. Dashboard views or dataset analyses using provider names during that window would show the wrong canonical name.

### Institution parsing

Institution parsing, implemented in `dashboard/institution_normalisation.py`, is a dashboard-only normalisation path.

The dashboard builds a parsed institutions table once at startup. This table is used by the Institutions analysis tab and by institution filters shared across the Project Explorer and Enriched Register.

The classifier does not use institution parsing. Classifier prompts are built only from:

- `Record ID`
- cleaned title
- cleaned dataset text

The `Researchers` field is never presented to the model. Institution normalisation therefore does not need to be shared with the classifier. It remains part of the dashboard data-quality pipeline because institution labels drive dashboard filters and counts.

A wrapped-line parsing defect, in which institution labels absorbed researcher-name fragments, was fixed on 2026-05-26 and diff-tested across the full register. Six projects changed, each confirmed by manual inspection to be a genuine correction.

### Note on cleaning pathways

Three normalisation concerns are handled differently, for different reasons:

| Concern | Pathway | Rationale |
|---|---|---|
| Title and dataset text cleaning | Shared by classifier and dashboard | Both require cleaned title and dataset text |
| Institution normalisation | Dashboard only | The classifier does not consume the researcher field |
| Dataset/provider-name canonicalisation | Dashboard only | Withheld from classifier pending evidence on whether canonicalisation helps or harms linkage classification |

Every free-text parsing component inspected in the register pipeline contained a genuine defect: title cleaning, dataset cleaning, provider recognition and institution parsing. The register's free-text fields are therefore treated as an expected source of classification risk. This is one reason the validation study specifically attends to data-quality-driven misclassification.

---

## 3. The ontology

### External review and terminology decisions (not strictly about the ontology, more labelling focus in the dashboard)

Feedback from ONS (Louise Corti) making recommendations on labelling were integrated in `2fe2414` (2026-04-14). While most changes affected dashboard terminology rather than the classification ontology directly, they shaped the public-facing framing of the analytical categories

| Feedback / recommendation                                                                                                                                                                                   |                      Decision | Action taken                                                                                                                                                                                                                                                        |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clarify whether the dashboard is privately published and avoid implying official ownership.                                                                                                                 |                   **Adopted** | Confirmed in correspondence that the dashboard is independently published and personally hosted. Prototype status retained in public wording.                                                                                                                       |
| Avoid the label **"ADR England linked datasets"** in headline stats, as the DEA legal gateway permits access through the Accredited Processor, in this case the ONS SRS, rather than "ADR England" as such. |                   **Adopted** | Removed / reduced ADR England-facing terminology and replaced it with more neutral wording focused on DEA projects, SRS access, and cross-domain linked datasets.                                                                                                   |
| Do not foreground the **ADR Flagship** subset, as it is insider-facing, not meaningful to most users, and changes over time.                                                                                | **Adopted / partly deferred** | Removed "ADR Flagship" as public-facing terminology. Retained the underlying analytical grouping for now, but reframed it as **cross-domain linked datasets**. Longer-term decision deferred on whether this subset should remain as a dashboard feature.           |
| Rename the dashboard URL, as it should not be named **ADR**.                                                                                                                                                |                  **Deferred** | Agreed in principle, but left unchanged temporarily because the live URL had already been shared and changing it cleanly risked breaking existing links. ADR emphasis was reduced elsewhere. Browser/page title uses the neutral **DEA Projects Dashboard**.        |
| Clarify that the Project Explorer covers the full DEA/SRS project register, not only ADR-linked datasets.                                                                                                   |                   **Adopted** | Front-page and explorer framing tightened to make clear that the explorer covers the full DEA-accredited project register. Linked-dataset analysis is presented as one analytical view, not the scope of the whole dashboard.                                       |
| Clarify the meaning of the date column.                                                                                                                                                                     |                   **Adopted** | The date field was explicitly labelled as **Accreditation Date**, reflecting the source register field rather than leaving the column ambiguous.                                                                                                                    |
| Rename **"Data provider"** using DEA terminology, with **"Data Processor"** suggested.                                                                                                                      |            **Partly adopted** | "Data provider" wording was changed, but not mechanically replaced with "Data Processor", because the chart groups organisations named in dataset text rather than making a formal legal-role claim. More precise wording such as **Source organisation** was used. |
| Remove one decimal place from pie-chart percentages.                                                                                                                                                        |                   **Adopted** | Pie-chart percentages rounded to whole percentages to reduce clutter.                                                                                                                                                                                               |

### Three-layer faceted design

The classification uses a three-layer faceted framework, introduced in `6e067f4` (2026-03-26) as v3, replacing the single-taxonomy v1 approach (from `242ce2b`, 2026-03-25). An intermediate v2 (`llm_theme_analysis_v2.py`) was also added in the same commit — implementing hierarchical classification with tighter taxonomy definitions, confidence flags, an adjudication pass, and three non-LLM baseline comparators (keyword regex, TF-IDF zero-shot, sentence-transformer embeddings). This machinery was all removed for v3, and both v1 and v2 scripts were deleted the same day (`778f767`, 2026-03-26) as "redundant." The v2 baseline comparators and pairwise agreement statistics do not appear in v3 or anywhere in the current codebase.

The three layers are:

- **Layer A — Substantive Domain:** what the project is about (1 or more labels)
- **Layer B — Linkage Mode:** how the data are linked (exactly 1 label)
- **Layer C — Analytical Purpose:** what analytical purpose the project serves (1–2 labels)

The three-layer decomposition separates "what the project is about" from "how the data are linked" from "what analytical purpose the project serves." That is analytically cleaner than a single theme label because a project can be about education, use cross-domain linkage, and be primarily a policy evaluation without forcing those dimensions into one bucket. The code explicitly says the three layers are classified independently so that patterns can be analysed separately. The 'linkage mode' uses the term 'linkage' loosely, referring not only to projects that use datasets that are linked at record-level, but also projects that use multiple datasets from the same substantive research domain ('within-domain linkage') as well as projects that use datasets from different substantive research domains ('cross-domain linkage'). In those instances, the datasets themselves are not linked, but the research undertaken using them crosses domains. This is a nuance worth disentangling more clearly in future classification (v3.4 run?)

### Layer A — Substantive Domain

**Initial label set** (14 labels, `6e067f4`, 2026-03-26): Health & Social Care, Education & Skills, Crime & Justice, Labour Market & Employment, Business & Productivity, Housing & Planning, Poverty, Inequality & Living Standards, Migration & Demographics, Environment & Agriculture, Public Finance & Taxation, Gender, Race & Ethnicity, COVID-19 & Pandemic, Data Infrastructure & Methodology, Other.

**Derivation and alignment with ADR UK themes:** Domains were developed inductively from the accredited register because no single authoritative standard scheme exists. The closest thing we have is [ADR UK's seven ARI-aligned strategic themes](https://www.adruk.org/our-work/our-work/) (note: Older ADR UK and UKRI materials refer to eight themes, including “Growing old”, and "world of work → "Employment & the economy", so we refer to the current ADR UK website framing while noting that ADR UK’s theme structure has changed over time). Our scheme aligns substantially with ADR UK's strategic research themes, while providing finer granularity and additional coverage of economic, fiscal and demographic research present in the wider DEA portfolio but outside ADR UK's funded priorities (ONS SRS has a long history of supporting economics / fiscal research). ADR UK's eight strategic research themes were designed to align with departmental Areas of Research Interest (ARIs) and the stated priority research interests of the devolved governments. A couple of differences that could be potential weaknesses/need future modification: Gender, Race & Ethnicity (doesn't match ADR which instead has "Social mobility & inclusion", and causes cross-layer errors as we discovered a bit later); COVID-19 and Data Infrastructure (category-type outliers compared to the others, absent from ADR).

**Gender, Race & Ethnicity guidance tightened** (`ad34cb6`, 2026-03-27): definition narrowed to "as the *primary research question* (not when demographic variables appear as controls or covariates)." An anti-tautology rule was added: "Avoid treating domain and purpose as synonymous — a Gender, Race & Ethnicity project is NOT automatically Inequality / Disparities Analysis."

**Overlap rules added** (`33f8a8c`, 2026-04-07): mortality data assignment depends on research question target; poverty vs inequality vs gender/race boundaries clarified; COVID-19 overlap rules (assign both COVID-19 and substantive domain).

**"Other" renamed to "Unclear from Title"** (`33f8a8c`, 2026-04-07, as part of prompt v3.2): "Other" suggests the project didn't fit into any domain, but more accurately, this only reflected a project whose domain was ambiguous from the title and datasets it used. The rename makes the label semantically accurate.

**Current label set** (14 labels): Health & Social Care, Education & Skills, Crime & Justice, Labour Market & Employment, Business & Productivity, Housing & Planning, Poverty, Inequality & Living Standards, Migration & Demographics, Environment & Agriculture, Public Finance & Taxation, Gender, Race & Ethnicity, COVID-19 & Pandemic, Data Infrastructure & Methodology, Unclear from Title.

### Layer B — Linkage Mode

**Initial label set** (5 labels, `6e067f4`, 2026-03-26): Single-Dataset, Within-Domain Linkage, Cross-Domain Linkage, Multi-Domain Linkage, Unclear from Title. The initial guidance classified by title alone.

**Guidance rewrite — title to provider counting** (`ad34cb6`, 2026-03-27): Layer B guidance rewritten to instruct counting by provider/policy area rather than by title alone. Explicit decision tree introduced: 1 dataset → Single; 2+ same provider → Within-Domain; 2 distinct providers → Cross-Domain; 3+ → Multi-Domain. Dataset info was included in the prompt for the first time (each project now shows `Title: ... | Datasets: ...`), addressing a structural limitation: linkage mode is a property of the *datasets* a project draws on, not of its title, so title-only classification cannot determine it — including the parsed Datasets Used field is what makes Layer B classifiable at all.

**Guidance rewrite — provider counting to domain counting** (`33f8a8c`, 2026-04-07, as part of prompt v3.2): the linkage-guidance was rewritten from provider-based to policy-domain-based counting ("Count by *policy domain*, not just provider name — large agencies like ONS supply datasets across many domains"). This addresses a clear misclassification mode: datasets from a single large agency (e.g. ONS) that actually span different policy areas were being classified as Within-Domain because they shared a provider; domain-counting corrects this. Pre-linked product handling was also added: "ASHE linked to Census 2011" spans employment + demographics → Cross-Domain; CIS linked to NHS Test and Trace stays within health.

**Multi-Domain merged into Cross-Domain** (`0a6798d`, 2026-04-23, prompt v3.3): "Multi-Domain Linkage" removed from the ontology and merged into "Cross-Domain Linkage," now defined as "links datasets from two or more distinct policy domains" (previously "exactly two"). Legacy remapping added: `_LINKAGE_LOOKUP["multi-domain linkage"] = "Cross-Domain Linkage"`. Worked example #4 updated (3-domain project → Cross-Domain Linkage). `PROMPT_VERSION` bumped v3.2→v3.3.

The rationale for the merge of multi-domain into cross-domain: The five-category scheme made the Layer B classification depend on a *precise domain count* (exactly 2 vs 3+), which is structurally the same judgement as Layer A (substantive domains). The 2-vs-3 boundary therefore inherited any error in Layer A's domain classification — if Layer A over- or under-assigned domains, a project drifted between Cross-Domain and Multi-Domain through no linkage-specific error of its own. The four-category scheme ("2 or more domains → Cross-Domain") asks only the coarser, more robust question — does the project cross domain boundaries at all — which is far less sensitive to domain-count noise. The finer "3+ domains" signal, where analytically useful, is better recovered as a derived property (a count over Layer A's domain list) than as an independently-classified linkage category. The merge was a deliberate taxonomy simplification, not a relabelling: classification outputs were subsequently fully regenerated under the v3.3 prompt (`31af95a`, 2026-05-20), not remapped from v3.2 output. The legacy runtime remap in `dashboard/data/thematic.py` was removed once native v3.3 outputs were committed.

**Current label set** (4 labels): Single-Dataset, Within-Domain Linkage, Cross-Domain Linkage, Unclear from Title.

### Layer C — Analytical Purpose

**Initial label set** (9 labels, `6e067f4`, 2026-03-26): Descriptive Monitoring, Outcome Linkage, Life-Course / Trajectory Analysis, Inequality / Disparities Analysis, Service Interaction / Systems Analysis, Policy Evaluation / Impact Analysis, Risk Prediction / Early Identification, Methodological / Infrastructure Research, Unclear from Title. Each project receives 1–2 purpose labels.

**"Outcome Linkage" renamed to "Outcome Tracking"** (`33f8a8c`, 2026-04-07, as part of prompt v3.2): the word "linkage" was changed to "tracking" to make it clear that this was related to analytical purpose rather than data linkage.

**Purpose guidance expanded** (`33f8a8c`, 2026-04-07): a "Distinguishing similar purposes" section was added — Descriptive Monitoring vs Outcome Tracking (measuring "how much" vs linking exposure to outcome), Outcome Tracking vs Life-Course (specific exposure→outcome vs extended time-period tracking), Outcome Tracking vs Policy Evaluation (naturally occurring exposure vs named policy/programme), Service Interaction vs others (focus on *how people move through* services).

**Anti-tautology rule** (`ad34cb6`, 2026-03-27): "Avoid treating domain and purpose as synonymous — a Gender, Race & Ethnicity project is NOT automatically Inequality / Disparities Analysis; it could be Descriptive Monitoring, Outcome Tracking, or Policy Evaluation depending on the research design."

**Current label set** (9 labels): Descriptive Monitoring, Outcome Tracking, Life-Course / Trajectory Analysis, Inequality / Disparities Analysis, Service Interaction / Systems Analysis, Policy Evaluation / Impact Analysis, Risk Prediction / Early Identification, Methodological / Infrastructure Research, Unclear from Title.

---

## 4. The classification pipeline

### Model selection

Claude Opus 4.6 is the classification model. A boundary-aware 150-project comparison sample (`build_experiment_sample.py`) and an Opus-vs-Sonnet review harness (`build_model_comparison.py`) were built to support the model choice (added in `33f8a8c`, 2026-04-07). Opus 4.6 was selected over Sonnet on the basis of perceived accuracy on the comparison sample. The v3.3 regeneration deliberately retained Opus 4.6 rather than adopting a newer model: holding the model fixed across the v3.2→v3.3 prompt change keeps that change single-variable, so any difference in output is attributable to the prompt alone. Adopting a newer model would be a separate, controlled follow-up (a prompt-held-constant model comparison). The comparison sample and review CSV are retained at `analysis/outputs_v3/model_selection_v3.2/` (untracked — see actions).

### Prompt versioning

The classification prompt evolved through four major versions. Each version change invalidated the cache (prompt version tracked in cache metadata from v3.2 onwards).

**v1** (`242ce2b`, 2026-03-25): single-taxonomy, 14 research themes, title-only input. Co-authored with Claude Sonnet 4.6. Superseded the next day.

**v2** (`6e067f4`, 2026-03-26, abandoned): hierarchical classification with tighter taxonomy definitions, confidence flags (high/medium/low), an adjudication pass with adaptive thinking for uncertain cases, and three non-LLM baseline comparators (keyword regex, TF-IDF zero-shot, sentence-transformer embeddings) with pairwise agreement statistics. All removed for v3; scripts deleted same day (`778f767`). The baseline comparators do not appear in the current codebase.

**v3 → prompt improvements** (`6e067f4`, 2026-03-26, then `ad34cb6`, 2026-03-27): three-layer framework. Initial prompt used title-only input. Prompt improvements in `ad34cb6` added dataset info to the prompt, 6 worked examples, rewritten Layer B guidance (provider-counting decision tree), tightened Layer A guidance (Gender/Race narrowed), classification rules updated ("Be conservative" removed, replaced with "prefer a specific classification if the title gives reasonable evidence"), and the anti-tautology rule.

**v3.2** (`33f8a8c`, 2026-04-07): major prompt revision. Linkage guidance switched from provider-counting to domain-counting. Overlap rules added for domains. Pre-linked product handling added. Purpose guidance expanded with "Distinguishing similar purposes" section. 5 new worked examples (#7–#11) added plus corrections to examples #3–#5. Example #5 corrected: census + death registrations → Migration & Demographics (not Health & Social Care). `PROMPT_VERSION = "v3.2"` introduced and stored in cache metadata. Full reclassification performed and outputs committed (`fdf1a74`, 2026-04-07).

**v3.3** (`0a6798d`, 2026-04-23): Multi-Domain Linkage merged into Cross-Domain Linkage. Worked example #4 updated. `PROMPT_VERSION` bumped to v3.3. Full reclassification performed and outputs committed (`31af95a`, 2026-05-20).

### Structured output and post-processing

Classification uses `client.messages.parse()` with Pydantic structured output (`BatchLayerResult` containing a list of `ProjectLayers`). When structured parsing fails, a raw JSON fallback path extracts and parses the response text manually (`_parse_raw_json`). Introduced in `6e067f4` (2026-03-26).

**Label normalisation (`_LABEL_CORRECTIONS`):** A label normalisation system was added in `ad34cb6` (2026-03-27) to salvage case mismatches and cross-layer label swaps in the raw JSON fallback path without burning retries. `_normalise_classification_dict()` applied lookup tables (`_DOMAIN_LOOKUP`, `_LINKAGE_LOOKUP`, `_PURPOSE_LOOKUP`) plus a `_LABEL_CORRECTIONS` dict for known cross-layer mistakes (e.g. "Descriptive Monitoring" appearing in the domains slot). Modified in `33f8a8c` (2026-04-07) to add "Outcome Tracking" mapping and "Other"→"Unclear from Title". Removed entirely in `3341ef8` (2026-05-19): this dict operated only in the *fallback* classification path, normalising non-canonical labels the constrained schema would otherwise reject. Some of its entries were mechanical aliases (case/punctuation variants); at least one ("outcome linkage" → "Outcome Tracking") was an interpretive rewrite that silently merged conceptually distinct labels. The dict was removed as a deliberate move away from silent post-processing toward auditable classification output.
**Effect on final outputs**: Not part of the final classification method after 3341ef8.

**Pydantic validators:** `clean_domains` deduplicates while preserving order and drops "Other"/"Unclear from Title" if a real domain is present; `clean_purposes` deduplicates, caps at 2, and drops "Unclear from Title" if a real purpose is present (enhanced in `0fbf259`, 2026-03-27).

### Batching, reliability, and API parameters

**Batch size tuning:** Batch size was reduced iteratively over development — 40 (`6e067f4`) → 30 (`9502be0`, 2026-03-26) → 20 (`ad34cb6`, 2026-03-27) → 10 (`33f8a8c`, 2026-04-07). The reductions were driven primarily by two observed reliability problems with larger batches: field misalignment / cross-contamination in the structured output (labels drifting into the wrong project's record), and unreliable matching of returned classifications back to project IDs. Smaller batches reduced both failure modes. A code comment at the 20→10 reduction additionally notes it improved reliability with the Opus model; the final batch size of 10 was retained.

**Token budget:** `max_tokens` increased 4000→8192 in `9502be0` (2026-03-26) to prevent output truncation.

**Retry logic:** Exponential backoff (3 attempts, wait = 2^attempt seconds) for transient API failures, added in `9502be0` (2026-03-26).

**Temperature:** `temperature=0` added to all API calls (classification and narrative) in `33f8a8c` (2026-04-07). Classifications are still not entirely deterministic though! This is because of batch effects (which can route through different Mixtures of Experts depending on their composition), and floating point error means that classifications close to one another can change in different runs, this was tested explicitly for v3.2 and v3.3 runs (see 'consistency testing' in section 5).

**Hardening (`0fbf259`, 2026-03-27):** Substantial reliability improvements:
- `BatchClassificationError` introduced: replaces silent fallback-to-defaults behaviour. Parse failures and validation failures now raise rather than silently assigning "Other"/"Unclear."
- `_validate_batch_integrity()` added: checks that the LLM returned exactly the requested IDs — flags unexpected, duplicate, or missing IDs.
- `_sanitise_prompt_text()` added: normalises whitespace, replaces backticks/braces/brackets to prevent prompt injection via special characters in titles.
- Failed batch tracking: if any batch fails after all retries, raises `RuntimeError` listing which batches failed (previously silently continued).
- Removed all silent defaults: previously, parse failures or missing projects got "Other"/"Unclear from Title" defaults without error; now these raise exceptions.

**On removing silent defaults specifically:** silent fallback-to-defaults meant a parse failure, a missing project, or a malformed response was recorded as a real classification ("Other"/"Unclear from Title"), indistinguishable from a genuine model judgement. This silently corrupts both the classification dataset and any quality metric computed over it. Raising `BatchClassificationError` instead makes failures loud and diagnosable — a necessary property for a pipeline whose output is intended to be formally validated, where an undetected silent default would inflate apparent accuracy.

**Response deduplication (`33f8a8c`, 2026-04-07):** drops duplicate `project_id` entries from LLM response before validation.

### Caching

The cache (`llm_layer_cache.json`) stores classifications keyed by Record ID, avoiding re-classification of already-processed projects. 

- **Cache schema versioning:** introduced in `3d22251` (2026-03-26) with `CACHE_SCHEMA_VERSION = 2` and `__meta__` envelope storing schema version and model. Bumped to 3 in `ad34cb6`, to 4 in `33f8a8c`.
- **Prompt version tracking:** `PROMPT_VERSION` stored in cache metadata from `33f8a8c` (2026-04-07); cache invalidated on prompt version change.
- **Model tracking:** cache invalidated on model change (from `0fbf259`, 2026-03-27).
- **Atomic writes:** `tempfile.mkstemp()` + `os.replace()` to prevent corruption from interrupted writes (`0fbf259`).
- **Corrupt cache handling:** catches `JSONDecodeError`/`ValueError`, starts fresh (`0fbf259`).
- **Cache pruning:** entries not matching current valid Record IDs are dropped on load (`3d22251`).

### Output regenerations

Classification outputs were fully regenerated twice:
- **v3.2 outputs** committed in `fdf1a74` (2026-04-07) — first committed outputs under the v3.2 prompt with renamed labels, domain-counting linkage rules, and `temperature=0`.
- **v3.3 outputs** committed in `31af95a` (2026-05-20) — regenerated after the Multi-Domain→Cross-Domain merge, with native 4-category schema. The legacy runtime remap in `dashboard/data/thematic.py` was removed.

---

## 5. Quality and consistency testing

### Quality diagnostics

`analysis/quality_check.py` (508 lines, introduced in `ad34cb6`, 2026-03-27): diagnostic metrics (Layer B unclear rate by year, domain distribution, domain-count distribution), suspicious-flag detection (e.g. Single-Dataset with 3+ datasets from 2+ providers; Cross-Domain with only 1 dataset; 4+ domains assigned; short titles), stratified human-review sampling, and post-review agreement reporting. No LLM calls — reads existing outputs only.

The diagnostic metric tracking "Other" domain usage was updated to track "Unclear from Title" in `3341ef8` (2026-05-19), aligning with the label rename from `33f8a8c`.

#### Results 

Layer A: Most projects get 1–2 domains (93.3% combined). Only 0.2% (2 projects) are "Unclear from Title."

Layer B: Very low "Unclear" rate (0.1% — just 1 project). Single-Dataset is the largest category (42.3%), followed by Within-Domain (38.4%) and Cross-Domain (19.3%). Notably, Cross-Domain projects have a median of only 1 provider — same as Within-Domain — which is a signal that the domain-counting guidance (not provider-counting) is doing the work (this can also arise occasionally if the dataset is a single record-level linked dataset, like LEO).

Layer C: 93.6% get exactly 1 purpose. Only 0.2% are "Unclear."

**Suspicious flags:** 134 projects flagged across 4 reasons:

- 60 Cross-Domain but only 1 dataset listed — the biggest category, suggesting either the LLM is inferring cross-domain linkage from the title when the dataset field is sparse, or the dataset parser is undercounting. Review of these showed these are overwhelmingly pre-linked cross-domain products, not classification errors:

| Dataset type | Count |
|---|---:|
| ECHILD (NHS + DfE pre-linked) | 39 |
| ASHE linked to 2011 Census | 11 |
| Census linked to Benefits & Income | 3 |
| Other Census-linked (NMC-Census, Companies House-Census, ASHE-HMRC) | 5 |
| NI linked datasets (Death + Offending) | 1 |
| Parsing artefact (2020/038 — actually lists 2 datasets, separator missed) | 1 |

The LLM correctly classified these as Cross-Domain because the single listed "dataset" genuinely spans domains. ECHILD alone accounts for 65% of all flags. This is a data-representation issue (the register lists one product name for what is internally a multi-source linkage), not a classification error.

- 57 short titles (<30 chars) — acronyms/jargon where the classifier is working with limited evidence
- 18 Gender/Race domain + Inequality purpose, a known tautological-coupling stress point: Inequality / Disparities analysis isn't really an analytical purpose, it's a topic. Analytical purpose should refer more to the method/analytical lens than it should to what topic is being studied, which is captured in layer A.
- 3 projects with 4+ domains assigned



### Consistency testing

`analysis/consistency_test.py` (360 lines, introduced in `ad34cb6`, 2026-03-27): measures classification stability by re-running a stratified 75-project sample through the LLM multiple times without caching, then computing pairwise agreement metrics per layer. Trial order shuffling (first trial unshuffled, subsequent trials shuffled with different seeds) tests sensitivity to presentation order. `TRIAL_FAILED` sentinel handling was added in `3341ef8` (2026-05-19) — projects with trial failures are excluded from consistency metrics rather than distorting agreement rates.

Consistency testing was introduced as a pre-validation diagnostic — measuring how often the classifier reproduces its own output across repeated runs on a fixed sample, as a proxy for where the classification task is hardest (could be useful for highlighting projects to oversample of human validation testing). API inference is not fully deterministic even at temperature 0 (owing to floating-point and batching effects), and classifications flip run-to-run only where the model's label probabilities are genuinely close — so instability localises the model's areas of genuine uncertainty rather than being uniform noise.

#### Results

**v3.2 consistency** (first committed in `60b364c`, 2026-05-20; 3 trials, 75 common projects):
- Layer B (Linkage Mode): 93.8% mean pairwise agreement, 90.7% unanimous
- Layer A (Substantive Domains): 82.7% mean pairwise agreement, 74.7% unanimous
- Layer C (Analytical Purpose): 77.3% mean pairwise agreement, 64.0% unanimous

**v3.3 consistency** (updated in `31af95a`, 2026-05-20; 3 trials, 75 common projects):
- Layer B: 95.6% mean pairwise agreement, 92.0% unanimous (up from 93.8%/90.7%)
- Layer A: 85.8% mean pairwise agreement, 76.0% unanimous (up from 82.7%/74.7%)
- Layer C: 82.2% mean pairwise agreement, 68.0% unanimous (up from 77.3%/64.0%)

The consistency improvement may partly reflect the simpler 4-category linkage schema.

#### Interpretation

Headline pairwise agreement of ~82–96% across the three layers indicates moderate-to-good reproducibility, but is not itself an accuracy measure — a classifier can be consistent and consistently wrong. The diagnostically important result is the *per-category* breakdown of Layer B: Cross-Domain Linkage is markedly less stable (≈62% category stability) than Single-Dataset (≈90%) or Within-Domain Linkage (≈93%). This corroborates the structural concern behind the `0a6798d` merge — the cross-domain judgement is the genuinely hard, genuinely uncertain part of the linkage layer. Consistency testing is therefore used to *target* the human validation effort: Cross-Domain projects are oversampled in the validation sample because that is where reproducibility is weakest and human ground-truth is most valuable. (Note: the per-category figures rest on a small sample — e.g. Cross-Domain n≈16 in the consistency trials — and should be read as indicative, not precise.)

---

## 6. Validation

### Validation study design

A researcher-led external validation study is in design. Key decisions taken so far:

- **Approach:** project researchers validate the classifications of their own projects — either classifying from scratch against the ontology, or reviewing the existing LLM classification and flagging errors.
- **Design:** hybrid — classify-from-scratch on a smaller rigorous core sample (clean inter-rater agreement); review-only on a larger coverage sample.
- **Sampling:** stratified, oversampling difficult cases like Cross-Domain linkage projects (least stable in consistency testing) and inequality-related projects (error-prone per the fallback analysis) (although note, we aim to improve these with a v3.4 run with prompt changes), with a random baseline stratum retained so an unbiased portfolio-wide error rate can still be estimated.
- **Split-sample design** also an option, given human validation is one-shot and expensive. This would involve recruiting a full set of researcher-validators, but holding a portion in reserve. Validate v4 on the first portion. If it reveals something serious and fixable, fix it, and validate the fix on the held-back portion. If v4 looks fine, you just use the reserve portion as additional sample. This gets you a safety net against "we validated and then found a glaring fixable problem" without asking anyone twice.
- **Schema validation:** the study should also address whether the ontology itself holds up, not only the LLM's application of it. A comparison of our schema against the [Office for National Statistics Taxonomy Best Practice Evaluation Framework][1] was done, indicating that the main weaknesses in the taxonomy are around governance rather than taxonomy design: (Scoring: 0 = absent, 1 = emerging, 2 = adequate for internal/prototype use, 3 = strong enough for public-facing or cross-organisational use.)

- **Schema validation:** the study should also address whether the ontology itself holds up, not only the LLM's application of it. A comparison of the taxonomy against the Office for National Statistics Taxonomy Best Practice Evaluation Framework indicates that the v3.4 dictionary is now broadly adequate for prototype/public-facing analytical use, with the remaining weaknesses concentrated in external engagement, validation, and unresolved category-type exceptions. Scoring: 0 = absent, 1 = emerging, 2 = adequate for internal/prototype use, 3 = strong enough for public-facing or cross-organisational use.

| ONS principle | Score | Assessment |
|---|---:|---|
| Definition | 3 | Strong. The taxonomy clearly names and classifies DEA projects across separate dimensions: substantive domain, linkage mode, analytical purpose, and a cross-cutting demographic-disparities/equity tag. The dictionary now provides definitions, inclusion rules, exclusion rules, examples, counterexamples, and prompt-inclusion status for each category. |
| Purpose | 3 | Strong. The purpose is explicit: to make DEA-accredited project activity analysable by research domain, data-linkage complexity, analytical purpose, and demographic-disparities focus. The dictionary is also explicitly positioned as the source for v4 prompt generation, validator guidance, and methods documentation. |
| Complexity | 2 | Adequate but still needs careful explanation. The faceted design is justified because it separates unlike concepts: policy/research domain, linkage structure, analytical purpose, and cross-cutting demographic comparison. However, multi-label domains, 1–2 purposes, conditional co-labels, and cross-cutting tags make this too complex to score as fully mature until tested with validators. |
| Balance | 2 | Improved but not fully resolved. Removing **Gender, Race & Ethnicity** from Layer A and **Inequality / Disparities Analysis** from Layer C fixes the main category-type imbalance. The relabel to **Poverty, Wealth & Living Standards** also reduces cross-layer confusion. However, **COVID-19 & Pandemic** remains a documented category-type anomaly, and **Data Infrastructure & Methodology** is still a meta-domain rather than a conventional policy/sector domain. Category sizes also remain uneven, though this is now acknowledged explicitly. |
| Ownership and governance | 2 | Improved from weak to adequate. The dictionary now has a role-based taxonomy owner, governance block, review process, change-approval note, validation expectation, feedback route, and review triggers. This is enough for prototype governance. It would need a tested review cycle, named decision authority, and public change process to score 3. |
| Accessibility | 2 | Adequate. The taxonomy is now a standalone dictionary rather than being embedded only in code or prompt text. It is more readable and machine-usable. To score 3, it should be published/signposted as a downloadable taxonomy pack, ideally with rendered Markdown/CSV views and plain-English validator guidance. |
| Interoperability | 3 | Strong. The dictionary now includes an explicit ADR UK theme-alignment block, records the seven current ADR UK themes, distinguishes close, partial, and no-direct-equivalent mappings, and states that the comparison is for interoperability rather than adoption. This directly addresses the ONS expectation that overlap with existing taxonomies be documented where possible. |
| Supported | 3 | Strong. The dictionary now contains detailed scope notes, inclusion/exclusion rules, examples, counterexamples, conditional labels, co-labels separated by layer, and historical notes for removed categories. This is a major improvement over prompt-only guidance. |
| Well-defined terms | 2 | Much improved but not quite a 3. The biggest ambiguity cluster around inequality has been structurally repaired. **Unclear from Title** has been renamed **Unclear from Register Entry**, which better reflects the evidence used. However, some boundaries still require validation: Labour Market vs Poverty/Wealth, Migration/Demographics vs demographic tag, Data Infrastructure domain vs Methodological purpose, and Outcome Tracking vs Risk Prediction. |
| Revision and maintenance | 2 | Adequate. The dictionary now records version/date fields separately, includes v3.4 changes, preserves removed labels with `include_in_prompt: false`, and adds governance/review metadata. To score 3, the revision cycle needs to be exercised in practice and accompanied by published migration/change notes after v4 validation. |
| Metadata | 3 | Strong. The old thin source metadata has been replaced by derivation metadata, list-form `dictionary_compiled_from`, taxonomy owner, layer cardinality, category identity note, ADR UK alignment, balance note, COVID-19 anomaly note, and prompt-inclusion flags. This is now a proper metadata record rather than incidental implementation metadata. |
| Methodology | 3 | Strong. The taxonomy derivation is documented as inductive from the UKSA DEA register, compared against ADR UK themes, assessed against the ONS framework, and supported by open code, structured outputs, consistency testing, caching, retry logic, and validation planning. |
| Engagement strategy | 2 | Improved but still limited. A feedback route and review trigger are now recorded, which is enough for prototype governance. It does not yet amount to a full stakeholder engagement strategy with users, researchers, public representatives, or institutional owners. |
| Future proof | 2 | Adequate. The faceted design, `include_in_prompt` flags, historical labels, “Unclear from Register Entry” fallbacks, and explicit future-facing retention of small purposes make the ontology adaptable. However, unresolved questions around **COVID-19 & Pandemic**, future category additions, and post-validation migration rules mean this should remain 2 until the first v4 validation/revision cycle is complete. |                                                   |

[1]: https://www.ons.gov.uk/file?uri=%2Fmethodology%2Fclassificationsandstandards%2Ftaxonomybestpracticeframework%2F20240312taxonomybestpracticeevaluationframeworkupdated.pptx.pdf "20240312 Taxonomy Best Practice Evaluation Framework UPDATED.pptx"

- **Possible automated triage:** a cross-vendor LLM adjudication pass (a different vendor's model, run as a committed, version-pinned script with a fixed prompt and blind re-classification) may be used to flag likely-wrong classifications and target the human sample — as a triage layer feeding the human study, not a substitute for it.
- **Target:** validation runs against the frozen v3.3 / Opus 4.6 classification output.

---

## 7. Known issues and limitations

### Known classification errors

Manual review of the 6 structured-parse fallback cases from the v3.3 run identified 2 errors:

- **2024/042** ("Exploring factors affecting the disability pay gap") — Layer A wrongly includes "Gender, Race & Ethnicity"; should be "Poverty, Inequality & Living Standards" (disability is outside the scope of the Gender/Race/Ethnicity label). Layers B and C correct.
- **2025/260** ("Inequalities and Health: Cancer Outcomes and Preventive Pathways in Wales") — Layer B classified "Single-Dataset"; the project uses two Census waves (2011, 2021) and should be "Within-Domain Linkage." Layers A and C correct.

Both produced schema-valid output and would not be caught by any automated check. Both are left **uncorrected** in the v3.3 outputs and retained as known reference cases: correcting errors found by chance would contaminate the validation accuracy measurement, so the validation study runs against genuine, uncorrected classifier output. All 6 fallback cases involved the "Inequality / Disparities Analysis" label, and both substantive errors were inequality-adjacent — indicating the inequality concept is an ontology stress point, spanning a Layer A domain ("Poverty, Inequality & Living Standards") and a Layer C purpose ("Inequality / Disparities Analysis"). This is a candidate for a v3.4 prompt clarification and a stratification variable for the validation study.

### Inequality cross-layer stress point

The "Inequality / Disparities Analysis" concept spans Layer A (as the "Poverty, Inequality & Living Standards" domain) and Layer C (as the "Inequality / Disparities Analysis" purpose), creating a cross-layer interaction that the prompt's anti-tautology rule (`ad34cb6`) attempts to manage. The Gender, Race & Ethnicity domain compounds this: it can be confused with both the inequality purpose and the poverty domain. Both known classification errors (above) are inequality-adjacent, there are also 18 projects flagged by `analysis/quality_check.py` (see section 5). The consistency results also show Layer C (where the inequality purpose resides) as the least stable layer (68.0% unanimous at v3.3). 

Analysis of these projects has highlighted an ontological discrepancy in "Inequality / Disparities Analysis" purpose, because it reflects a topic more than it does an analytical method or lens, and Layer A is supposed to catch topic domains (and does so already as "Poverty, Inequality & Living Standards", which itself can be confused with "Gender, Race & Ethnicity" domain).

**Layer C revision: the "Inequality / Disparities Analysis" category**
Problem identified. Diagnostic review found that the Layer C purpose label "Inequality / Disparities Analysis" does not behave as an analytical-purpose category. It functions as a topic rather than a method: the classifier assigns it whenever a project's title is framed in inequality terms ("pay gap", "disparities", "ethnic inequalities"), regardless of the project's actual analytical approach. This produced 18 tautological classifications where primary domain "Gender, Race & Ethnicity" was almost automatically paired with purpose "Inequality / Disparities Analysis" — and is the same cross-layer confusion seen in the structured-output fallback errors and in known error 2024/042. The label spans a Layer A domain ("Poverty, Inequality & Living Standards") and a Layer C purpose, which is the root cause: a topic placed in the purpose layer.
Scope. 207 projects (~16% of 1,271) currently carry this purpose label — not only the 18 tautological cases.

Reclassification feasibility check. Each of the 207 was assessed (by Claude Code Opus 4.7, so NOT reproducible but useful as a quick check) for where its Layer C purpose would fall if the category were removed:

| Destination                                          | Count |   % |
| ---------------------------------------------------- | ----: | --: |
| Already has a valid second purpose (drop label only) |    56 | 27% |
| Descriptive Monitoring                               |    93 | 45% |
| Outcome Tracking                                     |    43 | 21% |
| Life-Course / Trajectory Analysis                    |    11 |  5% |
| Policy Evaluation / Impact Analysis                  |     3 |  1% |
| Genuinely ambiguous                                  |     1 | <1% |

The single ambiguous case (2026/026) is an "Unclear from Title" problem, not a missing-category problem. No project is left without a home; no remaining category becomes a disproportionate catch-all. Removal is therefore feasible.
**Residual cost**. Removal has a genuine cost: the remaining seven purposes cannot mark the specific analytical intent of comparing outcomes *across demographic groups* to quantify a disparity. The 93 projects absorbed into "Descriptive Monitoring" are technically correctly labelled (they document patterns) but the comparative-disparities lens is flattened. The demographic dimension is not lost from the classification overall — Layer A still captures it via the domain — but it ceases to be expressible in the purpose layer.

**Decision:** Delete the category. Simpler ontology; comparative-group analysis is no longer a distinct purpose; the inequality signal is instead carried by a cross-cutting 'demographic disparities / equity" tag, orthoganel to the three layers (see below).

## Layer A revision (v3.4): demographic characteristics are not policy domains

### Problem

Diagnostic review identified a structural fault in Layer A paralleling the one found in Layer C.

Of the original 13 substantive domains, twelve are policy or sector domains: spheres of social or economic life that government acts on and collects data about, such as Labour Market & Employment, Health & Social Care, Crime & Justice, and Housing & Planning.

One domain, **Gender, Race & Ethnicity**, is not a policy domain of that kind. It is a set of demographic characteristics: dimensions along which outcomes in any policy domain can be disaggregated.

A gender pay gap study is a labour-market study analysed by gender. Ethnic disparities in mortality is a health study analysed by ethnicity. The demographic dimension is an analytical cross-cut, not a subject area.

This miscategorisation was one corner of a three-way confusion. The concept of inequality or disparity appeared in three confusable places:

1. Layer C purpose: **Inequality / Disparities Analysis**
2. Layer A domain: **Poverty, Inequality & Living Standards**
3. Layer A domain: **Gender, Race & Ethnicity**

The demographic category was the place such research was most often conducted. The word **inequality** appeared in two of the three category names. The classifier moved between them, producing:

- 18 tautological **Gender, Race & Ethnicity** + **Inequality / Disparities Analysis** pairings
- Both known classification errors, `2024/042` and `2025/260`, being inequality-adjacent
- Layer C registering as the least stable layer in consistency testing, with **68.0% unanimous agreement at v3.3**

### Decision: three coordinated changes

The fault was a category being the wrong kind of thing for its layer, not a labelling slip. The fix is therefore structural.

1. **Remove “Inequality / Disparities Analysis” from Layer C**

   This was a topic occupying the analytical-purpose layer. Layer C reduces to seven purposes. Feasibility and reasoning are recorded in the Layer C section.

2. **Remove “Gender, Race & Ethnicity” from Layer A**

   This was a demographic cross-cut occupying the policy-domain layer. Layer A reduces to twelve domains, all genuine policy or sector domains.

3. **Relabel “Poverty, Inequality & Living Standards” to “Poverty, Wealth & Living Standards”**

   This removes the contested word **inequality** from the domain layer entirely, de-conflicting the domain from the now-removed purpose. The new label is also cleaner on its own terms: symmetric across the income/wealth distribution, and purely a description of material conditions, which is what a policy domain should be.

After these three changes, every Layer A entry is a policy domain, every Layer C entry is a genuine analytical purpose, and the **inequality** lexical hook appears in no category name in either layer. The confusion triangle is eliminated.

### Reclassification feasibility for “Gender, Race & Ethnicity”

| Situation | Count | Effect of removal |
|---|---:|---|
| GR&E assigned alongside at least one retained substantive domain | 106 | Straightforward: remove GR&E and retain the remaining substantive domain label(s). No project loses its subject classification. |
| GR&E assigned as the only Layer A domain | 3 | Requires reassignment to a substantive domain based on the project title and dataset context; see below. |

The three sole-domain cases reclassify without strain:

| Project ID | Title | Reclassified domain |
|---|---|---|
| `2021/109` | Is Britain Fairer? 2020–2021 | Poverty, Wealth & Living Standards |
| `2023/095` | Statutory Review of Equality and Human Rights 2023 | Poverty, Wealth & Living Standards |
| `2023/006` | Ethnic Minority British Election Study pilot | Migration & Demographics |

Across the 109 projects carrying GR&E, 106 already had at least one other substantive Layer A domain. Removing GR&E therefore does not remove their substantive subject classification. Only three records require reassignment, and each can be mapped to an existing substantive domain without creating a new category.

### The cost, and how it is addressed

Removing GR&E as a domain and removing **Inequality / Disparities Analysis** as a purpose together remove the demographic-disparities dimension from the classification entirely. It would survive in neither layer.

For a dashboard whose purpose is the legibility of the research-data-access ecosystem, this is a real loss. Questions such as the following are squarely the kind of question the classification should be able to answer:

- How much DEA research examines outcomes by ethnicity or gender?
- Is the portfolio’s attention to demographic disparities changing over time?
- Which policy domains attract demographic-disparities research?

After the two removals, the classification could not answer those questions.

The resolution is not to retain either miscategorised category, but to represent the dimension as what it actually is. A cross-cutting **demographic-disparities / equity tag** is added in v4: a facet orthogonal to the three layers, marking projects whose work centres on comparing outcomes across demographic groups.

The approximately 109 former GR&E projects and the former inequality-purpose projects are approximately the population this tag should capture.

This mirrors the treatment of multi-domain linkage, which was likewise removed as a layer category and recovered as a derived property. A genuinely cross-cutting attribute belongs neither as a peer of the layer categories, where it generates tautologies and category errors, nor discarded, where it loses real signal. It should be represented as a cross-cutting facet.

The tag requires its own definition:

> Project centres on comparing outcomes across demographic groups to characterise differences.

It also requires its own validation attention. It is in scope for v4 so that the validated ontology is complete rather than carrying a known gap.

### Net effect of the v3.4 ontology revision

| Component | Change |
|---|---|
| Layer A | Reduced from 13 to 12 policy domains |
| Layer C | Reduced from 8 to 7 analytical purposes |
| Layer A label | “Poverty, Inequality & Living Standards” relabelled to “Poverty, Wealth & Living Standards” |
| New facet | Cross-cutting demographic-disparities / equity tag added for v4 |
| Implementation | Full reclassification after ontology update; individual records are not hand-corrected |

All changes precede the v4 classification freeze and the validation sample draw. The changes are to the ontology and classifier, followed by full reclassification. Individual records are not hand-corrected.

### ISER provider canonicalisation bug window

The provider name "Institute for Social and Economic Research" was being incorrectly mapped to "Institute for Economic and Social Research" (words transposed) from its introduction in `e9be89b` (2026-04-06) until the fix in `6df8226` (2026-05-19) — a window of ~43 days. Both the mapping table and test suite were corrected. Any dataset analysis or dashboard views using provider names during this period would show the wrong canonical name.

### Duplicate handling gap

The original deduplication policy (keying only on Project ID + title) silently discarded differing dataset and researcher information for same-ID/same-title rows that differed materially. Because linkage classification depends on the dataset list, this corrupted classification inputs for an unknown number of projects. The content-aware policy (2026-05-21) addresses this, but all prior classification runs may have been affected.

# Methods log — Taxonomy Data Dictionary v1.0-rc1 (release candidate)

**Artefact:** `taxonomy_data_dictionary.yaml`
**Dictionary version:** 1.0-rc1 (release candidate, frozen at commit
`f006abb`)
**Ontology version documented:** v3.4
**Status:** frozen as a release candidate for collaborator review. The
dictionary will be declared v1.0 after review meetings on 1 June and
10 June 2026. Changes requested during those reviews are pre-release
refinements (rc1 → rc2 → ... → 1.0), not post-release changelog entries.
Post-release revisions begin only after v1.0 is declared.

This entry records the design decisions behind the rc1 candidate and the
reasoning for each. It is decision-oriented, not a development history;
supporting detail (the ONS-framework self-assessment, the register-cleaning
provenance) lives in its own sections of this log and in the committed code.

## What the dictionary is

The dictionary is the single source of truth for the v3.4 ontology: three
faceted layers (A — substantive domain, multi-label; B — linkage mode, exactly
one; C — analytical purpose, one or two) plus a cross-cutting
demographic-disparities/equity tag. Each active category carries a definition,
inclusion rules, exclusion rules, counterexamples, and a status. The
dictionary is hand-edited YAML; human-readable renderings and the classifier
prompt are *derived* from it rather than maintained separately. This keeps one
editable source and avoids divergence between what humans read and what the
classifier receives.

## Key design decisions and rationale

### 1. Dictionary and ontology are versioned independently
The dictionary carries `dictionary_version` (1.0-rc1) separately from
`documents_ontology_version` (v3.4). The two can change at different rates:
the ontology changes when categories are added, removed, or redefined; the
dictionary changes when its wording, structure, or examples change without
altering the ontology. Conflating them (as the earlier per-category
`version_added`/`version_changed` fields did) produced internal
contradictions, so those fields were removed. Category lineage is now carried
only by `status` (active / relabelled v3.4 / removed v3.4 / new v3.4);
post-release change history is carried by the `changelog`, which records
named releases (including release candidates) and any evidence-driven
revisions made after a release — not pre-release development, which is
documented here.

### 2. The dictionary is rule-driven, not example-driven
Category meaning is carried by definitions; assignment by inclusion/exclusion
rules and the metadata-level assignment principles; difficult boundaries are
illustrated by counterexamples. The `examples` field is empty for all but one
category.

This was a deliberate reversal of an earlier, more example-heavy draft. On
review, most "examples" were one of two things: restatements of the
definition (adding nothing), or assignment principles written in example form
(rules in disguise). Restatements were cut; the principles they carried were
lifted into the rules or — where they recurred across categories — into
single metadata-level principles. An example is retained only where it is a
concrete, recognisable instance doing work the rules cannot easily do in
prose. After this pass, exactly one example survives: the gender pay gap, on
the demographic-disparities tag, which shows the tag operating alongside a
substantive domain (Labour Market & Employment). The `examples` field is
retained but empty elsewhere, reserved for evidence-driven additions
post-validation.

### 3. Recurring assignment principles are stated once, in metadata
Several assignment rules apply across all categories in a layer, or across
layers. Stating them inside each category's rules would have produced
drift-prone duplication. They are therefore stated once as metadata
principles: `layer_a_assignment_rule` (domains are multi-label and
non-hierarchical; assign every domain with substantive evidence, no
primary/secondary ordering); `layer_b_assignment_rule` (linkage mode by
dataset configuration; Single/Within/Cross ladder; provider identity
insufficient); `layer_c_assignment_rule` (purpose follows the visible
analytical operation; one or two, both substantive); the
`cross_layer_assignment_principles` block (`layer_independence`,
`evidence_not_keyword_rule`, `register_field_evidence_rule`,
`domain_purpose_separation`, `setting_vs_purpose_rule`, `tag_lens_rule`);
`methodology_domain_purpose_distinction` (Layer A Data Infrastructure &
Methodology vs Layer C Methodological / Infrastructure Research); and
`unclear_fallback_rule` (the three-layer "Unclear from Register Entry"
describes insufficient evidence in the register entry's informative fields —
title and dataset field — not inherently unclassifiable research).
Per-category rules state only what is distinctive about that category and do
not repeat the metadata principles.

### 4. The "no primary/secondary domain" decision
Layer A is multi-label and non-hierarchical: a project receives every domain
it substantively analyses, with no ranking. Whether to introduce a
primary/secondary distinction was considered and deferred — it would require
defining "primary" and a register survey to test inter-assessor agreement,
and is recorded as an open question rather than built into the rc1 candidate.

### 5. Worked examples are excluded on circularity grounds
The dictionary contains no worked classifications of real register projects.
Worked classifications are an *output* of the validation process, not an
input to it; feeding the classifier's own prior outputs back into the prompt
would be circular. They are held in a separate validation-track artefact.
The dictionary's examples and counterexamples are authored illustrations,
true by construction, and are explicitly not validated classifications.
Concrete project-based illustration for human readers is kept in a separate
explanatory document (`taxonomy_explanatory_examples.md`), which is not a
classifier input.

### 6. Examples and counterexamples illustrate boundaries; they do not define them
Boundary-drawing is operative and belongs in the inclusion/exclusion rules
and metadata principles, which the classifier acts on. Examples and
counterexamples are illustrative, not operative: a counterexample shows a
similar-looking case that falls outside a category and may name an
alternative label, but the boundary it points to is defined in the rules.
This keeps the operative logic in one place.

## Known anomalies and open questions (documented, not actioned in rc1)

- **COVID-19 & Pandemic** is retained as a Layer A domain but is a
  category-type anomaly: it is a time-bounded cross-cutting event rather
  than a policy/sector area, and its inclusion rule directs that it be
  assigned alongside a substantive domain. Whether to convert it to a
  cross-cutting tag is an open question for after v4 validation.
- **Data Infrastructure & Methodology (Layer A) vs Methodological /
  Infrastructure Research (Layer C):** in the v3 classifications these
  co-occurred in every case where the Layer A domain was assigned (no Layer
  A without the matching Layer C; 25 Layer C without Layer A). This is
  consistent with the layer distinction (methods can be instrumental to
  another domain, giving C without A) but may also reflect a classifier
  coupling. Flagged as a v4 validation question.
- **Small Layer C categories** (Risk Prediction / Early Identification;
  Service Interaction / Systems Analysis) are retained on conceptual and
  future-proofing grounds; no trend claims are made about them at current
  sizes.
- **Hard-coded category-label references in metadata prose:** the
  multi-label example in `layer_a_assignment_rule` names two specific
  domains (Labour Market & Employment; Poverty, Wealth & Living Standards).
  This is the only place in the dictionary where the prose contains exact
  category-label references; if either is relabelled, this reference must
  be updated. No automated check catches it.

## Validation stance

The dictionary is quality-assured against the ONS Taxonomy Best Practice
Evaluation Framework (self-assessment recorded separately in this log). It
is not "validated" in the sense of proven correct — no inductive taxonomy
is. It is empirically stress-tested *indirectly* through the
project-classification validation study: the taxonomy is revised, via the
changelog, only where a *systematic pattern* of classification errors
indicates a taxonomy fault rather than a classifier fault. Isolated
misclassifications are diagnosed as classifier issues, not taxonomy issues.
The taxonomy is described as "researcher-validated" where appropriate, never
as a "gold standard"; the validator pool's composition is described honestly
where the validation is reported.

## Path to v1.0

v1.0-rc1 is frozen at commit `f006abb` as the provenance anchor for
collaborator review. The path to v1.0:

- **1 June 2026:** review meeting with Jo Lam (PI). Discuss the taxonomy and
  the approach. Surface any structural concerns.
- **10 June 2026:** presentation to the wider team. Discuss the v4
  classifications (produced by the dictionary-driven, rationale-equipped
  classifier described in this log).
- **Post-10 June:** apply any agreed pre-release changes (rc1 → rc2 → ...
  → 1.0). When no further changes are requested, the dictionary is declared
  v1.0.
- **After v1.0 is declared:** the changelog begins recording post-release
  evidence-driven revisions only. Pre-release refinements (rc1 → rc2 →
  ... → 1.0) are recorded as named releases in the changelog *and* discussed
  in the methods log; evidence-driven post-release changes appear in the
  changelog only, per `changelog_note`.

  # Methods log — v1.0-rc1 classifier, classification runs, and noise/model-difference decomposition

**Artefacts:**
- Classifier code: `analysis/llm_theme_analysis_v3.py`
- Comparison/decomposition scripts: `analysis/build_v4_comparison.py`,
  `analysis/build_v4_decomposition.py`
- Dictionary: `taxonomy_data_dictionary.yaml` (v1.0-rc1, frozen at commit
  `f006abb`)
- Classification outputs: `analysis/outputs_v4_8_rc1/`,
  `analysis/outputs_v4_6_rc1/`, `analysis/outputs_v4_8_rc1_replicate/`
- Comparison outputs: `analysis/outputs_comparison_v4_rc1/`,
  `analysis/outputs_comparison_v4_8_intra_rc1/`,
  `analysis/outputs_comparison_decomposition_rc1/`
- Repository freeze tag: `v1.0-rc1-frozen` (commit
  `16a7f41`)

**Status:** v1.0-rc1 baseline produced for collaborator review on 1 June and
10 June 2026. No artefact in this entry is treated as v1.0; the path to v1.0
is described in the dictionary's methods-log entry.

This entry records the design and operational choices behind the rc1
classifier and the three full-register classification runs. It is paired with
the separate methods-log entry on the dictionary itself and should be read
alongside it. Decisions are stated as decisions, with rationale; this is not a
development history.

## What the classifier is

`analysis/llm_theme_analysis_v3.py` is an LLM-as-classifier that assigns each
project on the UKSA public register of DEA-accredited projects to:
- one or more Layer A substantive domains,
- exactly one Layer B linkage mode,
- one or two Layer C analytical purposes,
- zero or more cross-cutting tags (the demographic-disparities / equity tag
  is currently the only tag in the ontology),

and produces a structured prose **rationale** for each classification.

The classifier reads the project title and the dataset field from the
register entry; it does not use any other register field, and it does not
have access to external documentation about the project.

## Key design decisions

### 1. The classifier is dictionary-derived

The category ontology — the labels, definitions, inclusion rules, exclusion
rules, and cross-layer assignment principles — is **not maintained in Python**.
It lives in `taxonomy_data_dictionary.yaml`. At import time the classifier
reads the dictionary and derives:
- the per-layer label sets used for output validation (Pydantic
  `field_validator` membership checks against derived sets, not static
  `Literal` types),
- the per-category guidance blocks in the prompt (the definition, inclusion
  rules, and exclusion rules of each in-prompt category, rendered as prose),
- the cross-layer rules section of the prompt (the metadata `*_rule` and
  `cross_layer_assignment_principles` keys, rendered as prose paragraphs).

Removed and not-in-prompt categories are excluded automatically by status and
`include_in_prompt` filters.

The motivation is structural: a single source of truth removes the
divergence-between-prompt-and-code class of bugs (which had been a real and
documented problem in earlier classifier versions, where Python-side label
lists and prompt-side category lists could drift). If the dictionary changes,
the prompt and the validator change together by construction.

A consequence is that the prompt's quality is bounded by the dictionary's
quality. The discipline that follows: when the prompt reads thinly, the fix is
in the dictionary, not in the builder. The builder does not "improve on" what
the dictionary says.

### 2. The prompt is rules-driven, not example-driven

The dictionary contains no worked examples of real register projects (see the
dictionary methods-log entry for the reasoning). The classifier prompt
therefore contains no worked examples either. The category guidance section
provides only definition + inclusion + exclusion for each in-prompt category;
the rules section provides only the metadata-level assignment principles as
prose paragraphs. The model is given the rules and the project, and is
expected to apply the former to the latter.

This is a deliberate architectural choice. Worked examples would have to come
either from the dictionary (which excludes them on circularity grounds) or
from a separate authored corpus (which would have its own validation problem).
The rules-driven prompt avoids both.

### 3. The classifier produces a structured rationale per project

Each classification carries a required, non-empty `rationale` field: a single
prose sentence structured as
"Assigned <domains> because <evidence>; <linkage> because <evidence>;
<purpose> because <evidence>; <tag or no tag> because <evidence>." The model
is instructed to cite specific evidence from the title and dataset field, not
to restate definitions.

The rationale field serves two purposes. First, it provides per-case
reasoning that supports validation by making the classifier's reasoning
inspectable; an isolated wrong label without reasoning is less diagnostic than
a wrong label whose reasoning shows which rule the model misapplied. Second,
the act of producing reasoning appears to constrain the model's own
classification on boundary cases — for example, the TAGTEST/002
ethnic-disparities-in-sentencing project moved from Outcome Tracking to
Descriptive Monitoring when the rationale was added, with reasoning that
articulated *why* descriptive was the better reading. This is consistent with
chain-of-thought benefits reported elsewhere for LLM classification tasks.

A required, non-empty rationale rejects empty strings at validation. Missing
rationales in old cached entries (from prior schema versions) default to a
`"(rationale not provided)"` placeholder rather than crashing, so old caches
remain readable.

### 4. The prompt is split into a cached static block and a per-batch dynamic block

The static portion of the prompt — role framing, all four layer guidance
blocks, all cross-layer rules, the JSON schema, the rationale instruction — is
identical across every batch in a run. It is marked
`cache_control: {"type": "ephemeral"}` on the API call. The per-batch list of
projects to classify is appended as a non-cached suffix.

On Opus 4.8, with a static block of ~10,000 tokens, the first batch in a run
pays full input price for cache creation; subsequent batches (within the
ephemeral cache's ~5-minute lifetime) read the static block from cache. In
practice, cache hit rates above 97% were observed across the full-register
runs, reducing input cost to roughly 10% of the un-cached price. This made
running the full register multiple times — once on each of two models, and
twice on one model — practically and financially trivial (~$19 across three
full runs).

### 5. Model: Opus 4.8 default with CLI override

The default model is `claude-opus-4-8`. The CLI `--model` argument can target
any Claude model identifier (used during this project to run a 4.6 comparison
baseline).

Migration from 4.6 to 4.8 (via the 4.7 breaking-change boundary) required
removing the `temperature` parameter from all API calls — non-default
sampling values return a 400 error on 4.7+. `temperature=0` was previously set
but did not in fact guarantee determinism on 4.6 either; its removal makes
the non-determinism explicit and documents it.

The choice of 4.8 over 4.6 is empirically motivated, not a default-to-newest
choice. See "Why 4.8" below.

### 6. The validator is dictionary-driven and tolerant of unknown labels

`ProjectLayers` validation accepts each output field's list of labels and
checks each value against the dictionary-derived label set for that field.
Unknown labels are dropped (consistent across the raw-JSON fallback and the
structured-parse path), rather than raising. Empty Layer A and Layer C lists
fall back to "Unclear from Register Entry"; empty cross_cutting_tags is
treated as valid (no tag is the common case, not a fallback). This means a
model that occasionally produces a label not in the dictionary degrades
gracefully rather than failing the batch.

## What the rc1 runs measured

Three full-register runs were performed against the rc1 prompt:

| Run | Model | Output directory |
| --- | --- | --- |
| Run 1 | Opus 4.8 | `outputs_v4_8_rc1/` |
| Run 2 | Opus 4.6 | `outputs_v4_6_rc1/` |
| Run 3 | Opus 4.8 (replicate) | `outputs_v4_8_rc1_replicate/` |

All three runs used the same prompt (`PROMPT_VERSION = "dict-1.0-rc1"`), the
same register (1,272 projects classified, after register cleaning), and the
same dictionary (v1.0-rc1).

Two pairwise comparisons were then built using the generalised
`build_v4_comparison.py` script:

| Comparison | Comparison directory |
| --- | --- |
| Inter-model (4.8 run 1 vs 4.6) | `outputs_comparison_v4_rc1/` |
| Intra-model (4.8 run 1 vs 4.8 run 3) | `outputs_comparison_v4_8_intra_rc1/` |

A third analysis decomposed the two comparisons against each other using
`build_v4_decomposition.py`:

| Output | Directory |
| --- | --- |
| Decomposition report | `outputs_comparison_decomposition_rc1/` |

## Why three runs, not two

A two-model comparison alone cannot decompose "the two models disagreed" into
"the two models genuinely read this case differently" versus "either model
would have disagreed with itself on this case." Without a within-model
baseline, every disagreement counts equally, when in fact some portion of
disagreement is intrinsic to the model's own stochasticity on identical
inputs (the Anthropic API is non-deterministic).

Running Opus 4.8 twice against the full register on identical inputs measures
this stochastic component. The difference between inter-model and intra-model
disagreement is then an approximate lower bound on the *model-attributable*
portion of the inter-model disagreement.

Within-vendor versus cross-vendor was a separate question; see "Open methods
questions" below.

## Headline findings

The decomposition produced the following rates:

| Field | Intra-4.8 agreement | Inter-model agreement | Excess inter-model disagreement |
| --- | --- | --- | --- |
| Substantive domains | 91.3% | 79.0% | 12.3 pp |
| Linkage mode | 93.1% | 86.3% | 6.8 pp |
| Analytical purpose | 91.7% | 83.5% | 8.3 pp |
| Cross-cutting tags | 98.3% | 96.1% | 2.1 pp |
| All four fields | 77.0% | 55.6% | 21.4 pp |

Of the 1,272 projects:
- 652 disagreed in at least one of the two comparisons (union),
- 206 disagreed in both intra-4.8 and inter-model (Jaccard 0.316),
- 87 disagreed intra-4.8 but agreed inter-model,
- 359 disagreed inter-model but agreed intra-4.8.

The decomposition has three substantive consequences for how the rc1 runs
should be read:

**(a) Tag discipline is genuinely a model property.** Inter-model
disagreement on tags exceeds intra-model disagreement by only 2.1 pp, meaning
almost all of the 4.6-vs-4.8 tag disagreement is real model behaviour rather
than noise. The asymmetry is one-directional: 4.6 assigned the
demographic-disparities tag to 44 projects that 4.8 did not, while 4.8 added
the tag to 5 projects that 4.6 did not. The 4.6 over-tags concentrate on
projects defined by age, migrant status, socioeconomic background, or other
characteristics that the dictionary's `tag_lens_rule` exclusion explicitly
covers as "controls, covariates, sample descriptors, or routine stratifiers".
4.8 reads this exclusion more literally. This is consistent with reported
4.7+ behaviour of more literal instruction-following.

**(b) The Layer C Outcome/Descriptive boundary is intrinsically noisy, not
model-specific.** Inter-model excess on purpose is 8.3 pp; intra-4.8 purpose
disagreement is itself 8.3 pp (291 projects ÷ 1,272). Roughly half of the
inter-model purpose disagreement would have arisen between two replicates of
the same model. The largest specific pattern — Outcome Tracking ↔ Descriptive
Monitoring — appears in both comparisons. This points at the dictionary's
distinction between these categories as operationally underspecified, not at
a model-choice problem.

**(c) The 206 "disagreed in both" projects are the primary dictionary
refinement candidates.** These are cases that the same model cannot decide
stably *and* that two models read differently. They concentrate on the
predictable boundaries (Outcome vs Descriptive; primary-vs-secondary domain
under multi-label Layer A; the equity tag on inequality-themed projects that
are not centrally demographic) and are the cases where the dictionary's rules
are most plausibly leaving the classification underdetermined. Validation
should oversample this set if it intends to evaluate the dictionary, not just
the classifier.

## Why 4.8

The decision to use Opus 4.8 as the rc1 default rests on three observations:

1. **The tag-discipline finding above is the primary empirical case.** With
   intra-4.8 noise on tags at only 1.7 pp, the 4.8-vs-4.6 tag asymmetry is
   robustly attributable to the models' interpretive difference rather than
   sampling noise. The dictionary's `tag_lens_rule` is one of the more
   precisely written rules in the dictionary, and 4.8 applies it more
   correctly.
2. **No field-level disadvantage was observed.** On the other three fields,
   4.8 and 4.6 differ in ways that include but are not dominated by noise;
   neither model's labels look systematically worse than the other's on
   inspection of disagreement cases.
3. **The migration cost was negligible.** Removing one parameter
   (`temperature`) was the only breaking-change adjustment. Prompt caching,
   the rationale instruction, and the dictionary-derived prompt structure all
   worked unchanged across both models.

Run 1 of 4.8 is treated as the rc1 baseline classification (the canonical
labels for each project). Run 3 (the replicate) is treated as a confidence
indicator: each project carries a per-case agreement count derived from how
many of the four fields match across the two 4.8 runs (0-4). Validation is
expected to stratify by this flag.

The choice of "run 1, not run 3" as the canonical baseline is principled but
arbitrary at the case level: run 1 was completed first, both runs are
representative samples from the same underlying distribution, and choosing
run 3 would produce identical methodological claims with different specific
labels. This is documented honestly rather than disguised.

## Operational anomalies

Both 4.8 runs encountered a reproducible failure mode at one specific batch
boundary (batch 76, project IDs including `2024/136`, `2024/014/a`,
`2024/142`, `2024/131`, `2024/121`, `2024/081`): the model returned
hallucinated project IDs (e.g. `2024/076b_placeholder`, `2024/076b`) instead
of the requested IDs. The retry mechanism reproduced the failure across three
attempts; the targeted cache-fill recovery (classifying the affected projects
individually) succeeded on the first attempt in both runs.

This is documented because:
- It is *reproducible*, not random — the same projects failed in both 4.8
  runs in the same way. This is a systematic 4.8 failure mode on this
  batch's content, not stochastic instability.
- The recovery is honest disclosure: the rc1 classifications for these
  specific projects came from the single-project recovery path, not from
  batch classification. Their rationale fields and labels are valid; their
  per-batch classification context is different.
- It is a methodological note for the methods paper: LLM-as-classifier
  pipelines should expect and design for such failures at batch boundaries.
  The retry-then-targeted-fill pattern is the right design choice and worked.

The 4.6 run did not encounter this failure mode on this batch.

## What rc1 does not claim

- rc1 is **not** v1.0. It is a release candidate frozen for collaborator
  review. The path from rc1 to v1.0 is described in the dictionary's
  methods-log entry.
- rc1's classifications are **not** ground truth. They are stochastic
  outputs of a non-deterministic LLM classifier, with known per-field
  noise (~7-9% intra-model on purpose and linkage; ~2% on tags) and known
  model dependence on the tag.
- The rc1 baseline is **not** "validated" in the sense of having been
  independently checked against external truth. It is a classifier baseline
  against which the planned validation study will be run.
- No accuracy claim is made by this entry. Per-field agreement rates measure
  *consistency* (between models or between replicates), not correctness.

## Open methods questions for collaborator review

The following are surfaced explicitly so the 1 June and 10 June meetings can
address them rather than discovering them later:

1. **Confidence flag derivation.** Should the per-case confidence flag be a
   boolean (all four fields agreed across the two 4.8 runs) or a count
   (0-4)? Boolean is simpler; count is more diagnostic for stratified
   validation analysis. Recommendation: count.
2. **Number of intra-model replicates.** Two replicates measure instability
   but cannot distinguish "stably right" from "stably wrong" — both register
   as high confidence. Additional replicates (3-5) would enable mode-based
   aggregation. Cost is ~$7 per replicate. Whether to do this depends on the
   rigour bar the PI sets.
3. **Cross-vendor comparison.** A third independent classifier (e.g. GPT-5)
   would break the within-vendor correlation in the Opus comparisons. It is
   most informative for the 359 "inter-model only" disagreements (Bucket A)
   — cases where the two Anthropic models stably disagree. It does not
   resolve the 206 "disagreed in both" cases (those are dictionary refinement
   candidates regardless of how many models classify them). Whether the
   cross-vendor signal is worth the operational cost (~$10-15 plus an SDK
   integration) is a PI-level methods decision.
4. **Validation sample design.** Two complementary samples — random
   (unbiased discovery instrument) and enriched (powered for pattern
   characterisation) — were proposed. The enriched sample should combine at
   least three strata: model-disagreement (intra and inter), structural
   heuristics derived from the dictionary's boundary points, and (optionally)
   cross-vendor disagreement. The random sample size should be set to detect
   unanticipated failure modes at a defined frequency. These design choices
   are a PI-level decision.
5. **Primary/secondary domain.** Layer A is multi-label and
   non-hierarchical in the dictionary. A substantial portion of inter-model
   domain disagreement (e.g. 20 projects where 4.8 assigns Education + Labour
   and 4.6 assigns only Education) reflects the unresolved question of
   whether multi-label assignment should be ranked. This is a dictionary
   question that the rc1 data forces back onto the agenda.

## Reproducibility

The repository state corresponding to this entry is tagged
`v1.0-rc1-frozen`. From this tag, the dictionary, the classifier code, the
three classification CSVs (`layer_classifications.csv` in each
`outputs_v4_*_rc1*` directory), and the comparison/decomposition artefacts
are all inspectable. The cache files (`llm_layer_cache.json`) are not
tracked, on the principle that the canonical artefact is the
`layer_classifications.csv`, not the cache it was extracted from. A fresh run
of the classifier against the same dictionary and register would produce
different specific labels (because the API is non-deterministic), but the
distributional behaviour — the per-field agreement rates, the pattern of
disagreements, the tag discipline finding — should reproduce.

---

## 8. Open questions and future work

- **Model comparison artifacts never generated:** `build_experiment_sample.py` and `build_model_comparison.py` were added in `33f8a8c` to support Opus vs Sonnet comparison, but no output artifacts (experiment_sample_150.csv, model_comparison_review.csv, any Sonnet classification CSVs) appear in git history or on disk. It is unclear whether the comparison was conducted, conducted but kept locally, or abandoned.

- Cross-lab LLM disagreement is a candidate method for selecting the hard-case validation stratum; to be designed properly. Note: disagreement is a triage signal for sample selection only — agreement does not constitute validation, as frontier models may share correlated bias
