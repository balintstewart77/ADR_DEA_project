# Codebase hygiene audit — Phase 1 (report only, nothing committed)

Date: 2026-07-04 · Baseline: `main` @ `df4c034` (clean tree) · Auditor: Claude (Fable 5)

Canary baseline at audit time: **167 tests / 5.0s / 0 failures / 0 skipped**;
dashboard imports with **26 callbacks** and **1,309 projects**; committed
`register_properties.csv` byte-reproducibility test passes.

Categories: **A** mechanical/safe · **B** behaviour-risk · **C** decision-needed ·
**P** priority correctness. Every item: evidence → proposed action → risk note.
Hard-protected files (frozen releases, `register_reference.yaml` values,
`taxonomy_data_dictionary.yaml`, `release_pointers.json`, adjudicated tests) are
untouched by every proposal below.

---

## P. Priority correctness

### P1. Model-string default — VERIFIED RESOLVED, no action
- Evidence: `analysis/llm_theme_analysis_v3.py:105` → `MODEL = "claude-fable-5"`,
  changed in commit `173cae9` ("Align classifier default with Fable release",
  2026-07-02). Live release `analysis/outputs_classified_20260702_fable5/run_metadata.json`
  records `model`, `config_as_sent.model`, `cache_meta.model`, and every
  `usage_log[].response_model` as `claude-fable-5` — identical string.
- The known open item is closed: committed code regenerates the committed release.
- Action: none (recorded here for the audit trail).

### P2. Dashboard About page names the wrong model for the live release
- `dashboard/layout/about.py:151` — "Classification is performed by Claude
  (claude-opus-4-8)". The release pointer targets the **Fable 5** run.
  User-facing text mis-describes the committed outputs.
- Proposed action (minimal): update the string to Fable 5. Proper fix is **B1**
  (source it dynamically). Recommend applying the string fix now and deciding B1
  separately.
- Risk: none for the string fix (display text only); no test asserts it (verified
  by grep over `analysis/test_*.py`).

### P3. Thematic methodology text names the wrong model
- `dashboard/layout/analysis/thematic.py:194` — "**Model:** Claude Opus 4.8
  (`claude-opus-4-8`)". Same defect as P2. Note the adjacent taxonomy version on
  line 198 is already sourced dynamically from `dashboard/taxonomy.py` — only the
  model string is hard-coded.
- Proposed action: as P2 (string fix now; B1 for the dynamic fix).
- Risk: none for the string fix.

### P4. Duplicated-vocabulary scan (the DOMAIN_ORDER class) — no fifth instance found
- Checked: `dashboard/taxonomy.py` (labels derived from YAML, lines 79–81);
  `analysis/llm_theme_analysis_v3.py:193–199` (labels loaded from YAML at 155);
  `analysis/derive_register_properties.py` (`active_layer_a_domain_order()` reads
  taxonomy). Colour maps in `dashboard/config.py` are overrides keyed by label with
  a fallback palette — documented pattern, label *set* still single-sourced.
- One **latent** instance exists but is confined to dead code: see **C1**
  (`COLLECTION_COLOURS` — currently in sync with the reference labels, but a
  hard-coded list whose only consumer is an unreferenced module).

---

## A. Mechanical / safe

### A1. Unused imports in live code (5 files, ruff F401)
| Location | Unused |
|---|---|
| `analysis/derive_register_properties.py:6` | `os` |
| `analysis/quality_check.py:20` | `textwrap` |
| `dashboard/charts/core.py:7` | `CHART_HEIGHT` |
| `dashboard/data/loader.py:19–25` | `parse_datasets` (both try/except import branches; no call site in the file) |
| `dashboard/layout/overview.py:8` | `make_quarterly_chart`, `make_srs_chart` (both live in `trends.py`; only this import is dead) |
- Also 3 unused selenium-exception imports in `scrape/archive/scraper_html_table_legacy.py`
  — archive file, optional.
- Proposed action: remove the imports. Pure deletion of never-referenced names.
- Risk: none; full suite after.

### A2. No `.gitattributes`; 42 tracked files have mixed line endings in the worktree
- Evidence: `git ls-files --eol` → 106 × `i/lf w/crlf` (expected under
  `core.autocrlf=true`), **42 × `i/lf w/mixed`**, 24 × `i/lf w/lf`. Mixed-EOL
  worktree files are the source of the recurring "LF will be replaced by CRLF"
  churn and can silently break byte-exact comparisons.
- Proposed action: add `.gitattributes` pinning `*.py *.csv *.yaml *.yml *.md
  *.json *.txt text eol=lf` (binary extensions marked `-text`), then a one-time
  `git add --renormalize .` **as its own commit**.
- Risk note: the renormalise commit touches many files (noise in blame);
  index content for the affected files is already LF so committed bytes should
  not change materially — but the byte-exact idempotency canary
  (`test_committed_register_properties_are_reproducible`) MUST be run
  immediately after, and the batch reverted if it fails.

### A3. README links use absolute local paths (username leak + broken on GitHub)
- `README.md` lines 24–29, 43, 59, 161–164: links of the form
  `/C:/Users/balin/Desktop/ADR_DEA_project/...` (10 occurrences). They leak the
  local username and do not resolve on GitHub.
- Proposed action: convert to repo-relative links (`dashboard/app.py`, etc.).
- Risk: none (docs only).

### A4. README stale fact: flagship classification method
- `README.md:156` — "Flagship classification is based on keyword matching against
  dataset text." Retired: collection membership is now derived from the
  linked-product reference (`dashboard/data/loader.py:36–62`; the retired keyword
  list is referenced as retired in `test_derive_register_properties.py:202–205`).
- Proposed action: reword to "derived from the curated linked-product reference
  (`analysis/register_reference.yaml`)".
- Risk: none (docs only).

### A5. `.gitignore` duplicate entries
- `venv/`+`.venv/`, `__pycache__/`+`*.pyc`, and `.claude/` each appear twice
  (early block and later blocks). Harmless but confusing.
- Proposed action: consolidate duplicates, no semantic change to what is ignored
  (verify with `git status --ignored` before/after produces identical sets).
- Risk: low; mis-editing could untrack/track something — the before/after
  ignored-set diff is the guard.

### A6. Other stale-fact sweep — clean
- `temperature` — zero occurrences anywhere in tracked code/docs.
- "13 domains" — only `METHODS_LOG.md:456`, which reads "Of the original 13
  substantive domains, twelve are…" — intentional historical narrative in the
  log; leave as is.
- No dead file-path references found in code comments pointing at nonexistent
  modules.

---

## B. Behaviour-risk (each needs explicit approval)

### B1. Source the displayed model string from the live release metadata
- Fix P2/P3 properly: read `model` from
  `<classification_dir>/run_metadata.json` (via the existing release-pointer
  resolution in `dashboard/config.py`) with a safe fallback string, so About and
  Thematic can never again drift from the run they describe. Mirrors the pattern
  already used for the taxonomy version (`thematic.py:198`).
- Risk: new file-read at import time; needs a fallback for missing/unreadable
  metadata (same degrade-to-blank discipline as `load_register_properties`).
  Small test to pin it.

### B2. Register-version-coupled test pins
- `analysis/test_collection_toggle.py:47–49` (Data First = 31 projects / 94
  requests) and `analysis/test_dashboard_registry_options.py:34` (31). These
  assert live-register values and will fail on the next register refresh even
  when the code is correct.
- Options: (a) keep as deliberate refresh canaries, updated as part of each
  refresh PR (status quo, zero work); (b) parameterise expected values from a
  small per-register-version fixtures file resolved via the register manifest.
- Proposed action: Balint chooses; (a) is defensible — these have caught real
  regressions. If (b), it is a test-only change but touches the refresh
  workflow's expectations, hence B not A.
- Note: `test_refresh_pipeline.py:196` mentioning `outputs_classified_20260601`
  is a temp-file fixture, **not** release-coupled — no action.

### B3. Dependency pinning
- All seven `requirements*.txt` files are fully unpinned. Installed runtime
  today: dash 4.1.0, plotly 6.6.0, pandas 2.2.3, numpy 2.2.5, PyYAML 6.0.2,
  gunicorn 25.3.0, Flask 3.1.3 / Werkzeug 3.1.7 (transitive), anthropic 0.86.0,
  pydantic 2.12.5, requests 2.32.3, selenium 4.32.0.
- `pip-audit` is not installed; no offline vulnerability check was possible.
  None of the versions above is end-of-life old; Balint may wish to run
  `pip-audit` online.
- Proposed action: add a `constraints.txt` (or pin `requirements-dashboard.txt`
  only) capturing today's known-good runtime set. Deploy-behaviour change →
  needs a deliberate decision.
- Risk: pins can conflict with the deployment platform's build; keep optional
  sets unpinned if in doubt.

### B4. Bare `except:` (E722) — none in live code
- All 6 hits are inside the archived 2025 notebooks. No action proposed; recorded
  so nobody "fixes" the notebooks (they are frozen artefacts).

---

## C. Decision-needed

### C1. Dead module: `dashboard/charts/collections.py` (+ `COLLECTION_COLOURS`)
- Evidence: all four functions (`make_collection_line_chart`,
  `make_collection_yearly_line_chart`, `make_collection_totals_chart`,
  `make_cumulative_chart`) have **zero call sites** outside the module (grep over
  dashboard/analysis/scrape). `dashboard/charts/__init__.py` is empty; no layout
  or callback imports the module. Its sole dependency uniquely consumed is
  `COLLECTION_COLOURS` (`dashboard/config.py:14–22`) — a hard-coded collection
  list of the DOMAIN_ORDER drift class (currently in sync with the reference's
  seven `collection_label`s, verified programmatically, but nothing enforces it).
- Proposed action: delete `charts/collections.py` and `COLLECTION_COLOURS`
  together. This removes the latent fifth drift instance rather than defending it.
- Risk: low (no references), but it is a deletion → Balint approval required.

### C2. Top-level taxonomy backup/diff files (untracked, ignored)
- `taxonomy_data_dictionary.CONFLICT_BACKUP.yaml`, `.principles_backup.yaml`,
  `.rule_wording_backup.yaml`, `.current_diff.patch` (May 27–28 era, superseded
  by the committed dictionary at 0.5.x/dict-1.0-rc2 line).
- Proposed action: Balint decides — delete, or move to a local archive folder
  outside the repo. No repo impact either way (ignored).

### C3. Accidental `%USERPROFILE%/` directory at repo root
- Contains only `.claude/settings.json`; created by an unexpanded Windows env
  var. Untracked/ignored.
- Proposed action: inspect content once, then delete the directory.

### C4. Large tracked legacy artefacts (~10 MB, inflating clones)
- `analysis/DEA_projects_analysis.ipynb` (2.6 MB),
  `DEA_projects_analysis_figures_only_20250704.{html,ipynb}` (2.2 + 2.0 MB),
  `DEA_projects_analysis_web_20250704/20250708.ipynb` (2.0 MB each), plus
  duplicated PNG sets `docs/DEA_projects_analysis_web_20250704_files/` vs
  `_20250708_files/` and `analysis/DEA_projects_analysis_files_July25/`
  (12 files). `.git` is 116 MB.
- These are the July-2025 published-analysis record. Options: keep (provenance;
  simplest), or relocate the superseded 20250704 set (the 20250708 set appears
  to be the published one via `docs/index.md`). **No history rewrite proposed.**
- Proposed action: Balint decides retention; default keep.

### C5. Stale ignored workspace directories
- `analysis/outputs_register_properties_tmp/` (964 KB, name says tmp),
  `analysis/outputs_v3/dashboard_*std{out,err}.log` (refactor-era logs),
  `analysis/outputs_examples_rc2/`, `analysis/opus_v_sonnet_comparison_analysis/`.
  All ignored, workspace-only.
- Proposed action: Balint marks keep/delete per directory; `_tmp` and the
  `dashboard_*.log` files look safely deletable.

### C6. LLM cache retention (reproducibility record — listed, no deletion proposed)
| Cache | Size | Era |
|---|---|---|
| `outputs_classified_20260702_fable5/llm_layer_cache.json` | 904 KB | **live Fable 5 run — keep** |
| `outputs_v4_6_rc1/` | 1.0 MB | Opus-era |
| `outputs_v4_8_rc1/` · `_replicate/` | 884 + 888 KB | Opus-era |
| `outputs_v4_8_rc2/` | 744 KB | Opus-era (previous release) |
| `outputs_v3/llm_layer_cache.json` + `.v3.2.json` | 320 + 320 KB | v3-era |
| `outputs/model_comparison_fable_5_run{1,2}/` | 140 + 140 KB | comparison |
| `outputs/model_comparison_opus_4_8_run2/` | 128 KB | comparison |
| `opus_v_sonnet_comparison_analysis/outputs_{opus,sonnet}/` | 40 + 40 KB | early comparison |
- Total ≈ 5.5 MB, all gitignored. They are the reproducibility record of prior
  runs; retention is Balint's call. No default deletion.

### C7. `requirements-ml.txt` (torch/transformers/sentence-transformers…)
- No tracked `.py` imports any of these; `nltk`/`scikit-learn`/`scipy`/
  `statsmodels`/`seaborn`/`wordcloud` are used only by the archived 2025
  notebooks. The ML set looks entirely notebook/experiment-era.
- Proposed action: decide whether to retire `requirements-ml.txt` (and slim the
  analysis/dev extras) or keep them annotated as notebook-era. Doc-level change
  but alters what a future contributor installs → decision.

### C8. `.gitignore` policy items to confirm (list, not decide)
- Ignored but arguably track-worthy: `analysis/outputs/` currently holds
  incident/QA reports (`domain_order_reconciliation_review.md`, availability
  review CSVs, this audit) — the METHODS_LOG references some of them. If any are
  part of the permanent record, they need explicit `!` exceptions.
- `analysis/outputs_deterministic_rc2/manifest.json` is ignored while its CSV is
  tracked — the manifest carries run provenance (git commit, row counts);
  consider tracking it for the frozen release.
- `data/*.xlsx` tracked (291 KB) — intentional? (source extract; fine if yes.)

---

## Test suite health (recorded)

- **167 tests, 5.0 s, 0 failures, 0 errors, 0 skipped/xfail.** Slowest:
  `test_committed_register_properties_are_reproducible` 1.65 s, next 0.99 s —
  nothing pathological.
- Critical paths covered: derivation + byte-exact reproducibility
  (`test_derive_register_properties`), canonicalisation
  (`test_dataset_normalisation`, `test_institution_normalisation`),
  release-pointer resolution (`test_refresh_pipeline`), cache keying / record-ID
  stability (`test_record_id_stability`), adjudicated decisions
  (`test_adjudicated_decisions`), collection views (`test_collection_toggle`).
  No orphaned test files or duplicated test utilities found (13 test modules,
  each targeting a live module).
- Release-coupling: only the two pins in **B2**.

## Secrets & safety (recorded)

- No API keys/tokens/private keys in tracked files: the `sk-ant-` hits are
  docstring placeholders; both scripts read `ANTHROPIC_API_KEY` from the
  environment (`llm_theme_analysis_v3.py:1178`, `consistency_test.py:323`).
- `balintstewart@gmail.com` appears deliberately (feedback link,
  `dashboard/config.py:76`).
- Username-leaking absolute paths: `README.md` (fix = A3) and inside the two
  archived 2025 notebooks (in git history regardless; **flagged for human
  decision, no history rewrite proposed** — exposure is a local Windows
  username, low sensitivity).

---

## Proposed Phase 2 batching (pending item-by-item approval)

1. **Batch P** (if approved): P2 + P3 string fixes — one commit.
2. **Batch A-1**: A1 unused imports + A3 README links + A4 README fact + A5
   gitignore dedupe — one commit.
3. **Batch A-2**: A2 `.gitattributes` + renormalise — **its own commit**,
   canaries immediately after.
4. **Batch B-x**: only approved B items, smallest coherent batches.
5. **C items**: only those explicitly approved, one commit each, decision noted
   in the message.

After every batch: full suite green (167), dashboard imports (26 callbacks,
1,309 projects), idempotency/equivalence/adjudication canaries pass, `git
status` clean. Any failure → revert batch, stop, report. **No push at any point.**
