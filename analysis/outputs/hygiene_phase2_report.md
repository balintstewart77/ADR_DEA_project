# Hygiene Phase 2 — application report

Date: 2026-07-04 · Base: `main` @ `2cf1d81` (post requests-metric commit; the
instruction's df4c034 baseline plus two intervening feature commits Balint made)
· End: `main` @ `3022dbd` · **NOT pushed.**

Sequencing note: Batch A-2 (human-gated) was moved to the END of the run so its
gate could not block the other approved batches. The gate then resolved via the
instruction's zero-diff exception (see A-2 below), so no wait was needed.

After every batch the full gate ran: complete suite green, dashboard imports
(26 callbacks / 1,309 projects), byte-exact reproducibility canary, taxonomy-
equivalence and adjudication tests (all inside the discovered suite), and
`git status` clean. Every gate passed on the first run; nothing was reverted.

## Commit stack (in order)

| Commit | Batch | Suite after |
|---|---|---|
| `8375a93` | P — displayed model corrected to Fable 5 (P2 P3) | 167 OK |
| `8bbf754` | A-1 — unused imports, README links/fact, gitignore dedupe | 167 OK |
| `194fd1b` | B-1 — model string sourced from release metadata + tests | 171 OK |
| `7d010ff` | C-1 — dead collections module + COLLECTION_COLOURS deleted | 171 OK |
| `533544a` | C7 — requirements-ml annotated notebook-era | 171 OK |
| `5314e1b` | C8a+b — incident/QA reports + rc2 manifest tracked | 171 OK |
| `3022dbd` | A-2 — .gitattributes (zero-renormalise) | 171 OK + immediate byte-exact canary OK |

Suite grew 167 → 171 (four new tests in `analysis/test_release_model_string.py`).

## Batch P (urgent) — `8375a93`
`dashboard/layout/about.py:151` and `dashboard/layout/analysis/thematic.py:194`
now say `claude-fable-5` (was `claude-opus-4-8`). Reported to Balint immediately
after commit for optional early push. Superseded by B-1 below (as planned — P
was the stopgap).

## Batch A-1 — `8bbf754`
- **A1**: removed never-referenced imports in 5 live files
  (`derive_register_properties.py` `os`; `quality_check.py` `textwrap`;
  `charts/core.py` `CHART_HEIGHT`; `data/loader.py` `parse_datasets` both
  try/except branches; `layout/overview.py` `make_quarterly_chart`,
  `make_srs_chart`). Each verified referenced only at its import site before
  removal. Archived scraper untouched, as instructed.
- **A3**: all 10 absolute `/C:/Users/balin/...` README links converted to
  repo-relative; every target verified to exist; zero `C:/Users` strings remain.
- **A4**: README limitation line updated from retired keyword matching to the
  curated linked-product reference.
- **A5 guard**: `git status --ignored` captured before and after the dedupe —
  **ignored set IDENTICAL, 91 entries both sides** (diff empty). Removed
  duplicates: second `.claude/`, `**/__pycache__/`+`*.pyc` block, `venv/`+
  `.venv/` block. None interacted with any `!` negation.

## Batch B-1 — `194fd1b`
`dashboard/config.py` gains `RELEASE_MODEL` = the `model` field of
`<classification_dir>/run_metadata.json`, resolved via the existing
release-pointer mechanism, degrading to the visible placeholder
`"see release metadata"` on missing/unreadable file or empty field (same
discipline as `load_register_properties`). About and Thematic interpolate it.
New `analysis/test_release_model_string.py` pins: metadata equality, both
layouts render the value (and no `claude-opus-4-8` anywhere in them), missing-
file fallback, empty-field fallback. Current resolved value: `claude-fable-5`.

## Batch C-1 — `7d010ff`
Deleted `dashboard/charts/collections.py` (4 functions) and
`COLLECTION_COLOURS` (config.py). Grep guard before AND after deletion:
zero references to the module, its functions, or the constant anywhere in
dashboard/analysis/scrape ("NONE remaining"). This also removes the latent
fifth duplicated-vocabulary instance. 125 lines deleted; callbacks unchanged
at 26 (the module registered none).

## C7 — `533544a`
Header comment added to `requirements-ml.txt` (notebook-era, not for
deployment). Comment only.

## C8a + C8b — `5314e1b`
- Converted `analysis/outputs/` ignore from directory form to
  `analysis/outputs/*` — required because git cannot re-include files under an
  ignored *directory*; negations only work under a `*` ignore.
- Now tracked: `analysis/outputs/codebase_hygiene_audit.md`,
  `analysis/outputs/domain_order_reconciliation_review.md`,
  `analysis/outputs_deterministic_rc2/manifest.json` (C8b — run provenance for
  the frozen deterministic release).
- Spot-check guard: `git check-ignore` confirms other outputs files (e.g.
  `model_comparison_sample.csv`, `instruction_layer_figures_report.md`) and
  `outputs_deterministic_rc2/quality/` remain ignored. The redundant explicit
  `instruction_layer_figures_report.md` ignore line was folded into
  `analysis/outputs/*`.
- **FLAG for Balint**: METHODS_LOG references
  `analysis/outputs/linked_product_availability_review.csv` (the only
  availability-review CSV it names) but the file **does not exist on disk** —
  it was presumably cleaned away while the directory was wholesale-ignored.
  Not recreated; decide whether to regenerate it or amend the METHODS_LOG
  reference. (The other METHODS_LOG reference,
  `instruction_stable_record_id_regen_report.md`, also no longer exists and
  was not in the approved tracking list.)

## Workspace actions (no commits)
- **C3**: `%USERPROFILE%/.claude/settings.json` content (one line): a local
  Claude permissions allowlist for read-only Bash commands (python/cd/cat/ls/
  find/grep/head/tail/echo/pwd/which) — nothing sensitive. Directory deleted.
- **C5**: deleted `analysis/outputs_register_properties_tmp/` (964 KB) and the
  four `analysis/outputs_v3/dashboard_*std{out,err}.log` refactor logs.
  `opus_v_sonnet_comparison_analysis/` untouched.
- **C5 — `outputs_examples_rc2/` listing (NOT deleted; Balint decides):**
  `all_projects_classified.csv`, `cross_domain_purpose.csv`,
  `curated_record_ids.csv`, `example_cards.md`, `example_classifications.csv`,
  `instruction_rc2_examples_report.md`, `layer_a_by_year.csv`,
  `layer_a_totals.csv`, `layer_classifications.csv`, `layer_c_by_year.csv`,
  `layer_c_totals.csv`, `layer_summary.txt`, `llm_layer_cache.json`,
  `manifest.json`, `quality/duplicate_review_flagged.csv`,
  `quality/quality/duplicate_review_flagged.csv` (note the doubled nesting —
  looks accidental), `_verification_summary.json`.

## Batch A-2 — `3022dbd` (gate resolved by the zero-diff exception)
- `.gitattributes` added: `*.py *.csv *.yaml *.yml *.md *.json *.txt *.ipynb
  text eol=lf`; `*.png *.xlsx *.ods *.pdf -text`.
- **Gate evidence — staged stat after `git add --renormalize .`:**
  `.gitattributes | 16 ++++++++++++++++` — **one file, the new .gitattributes
  itself; ZERO tracked files renormalised.** All tracked content was already
  LF in the index (consistent with the Phase 1 `git ls-files --eol` survey —
  the CRLF/mixed issue was working-copy only). Frozen-release check: no
  `outputs_deterministic_rc2/` or `outputs_classified_*` paths staged — CLEAN.
- Per the instruction's exception clause the commit proceeded without waiting.
  Byte-exact canary run immediately after the commit: **OK**.
- Effect going forward: working copies check out LF for the pinned types, so
  the recurring "LF will be replaced by CRLF" warnings and mixed-EOL churn end
  as files are next touched.

## Not touched (as instructed)
B2 register-version test pins, B3 dependency pinning, B4, A6, C2 taxonomy
backups (still at repo root for Balint), C4 legacy artefacts, C6 LLM caches
(all retained), `outputs_examples_rc2/`, `opus_v_sonnet_comparison_analysis/`.
No reference-value, taxonomy, release-pointer, or adjudicated-test changes.

## End state
- `git log --oneline` (new commits, oldest first): `8375a93`, `8bbf754`,
  `194fd1b`, `7d010ff`, `533544a`, `5314e1b`, `3022dbd`.
- Full suite: **171 tests, OK**. Dashboard: **26 callbacks, 1,309 projects**.
  Byte-exact reproducibility, taxonomy-equivalence, adjudication tests: pass.
- `git status`: clean. (This report was initially untracked in the ignored
  `analysis/outputs/`; Balint spotted the irony and it is now tracked via its
  own `!` exception, follow-up commit after `3022dbd`.)
- **Nothing pushed** — the stack awaits Balint's review.
