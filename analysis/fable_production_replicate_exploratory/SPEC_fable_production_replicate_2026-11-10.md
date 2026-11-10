# Specification — Exploratory: full-register replicate of the Fable 5 production run

## Dates

- Specification and instruction date: 10 November 2026 (investigator instruction: a second Fable 5 run over the full register under exactly the production conditions).
- Specification creation date: 2026-11-10. Not backdated.
- Written before the runner code and before any API call. Commit this file alone before the first API call.

## Status

Post-registration, exploratory and descriptive. Not preregistered: protocol v1.1 §4.2 reports one pre-existing run pair on a fixed 201-record sample and specifies no further replicate. The production labels (MOD-006) are unchanged and remain the labels under validation. No preregistered or exploratory analysis is rerun with the replicate labels; any such use needs its own dated specification.

Results are reported separately from the pre-existing 201-record stability evidence and never pooled with it.

## Purpose

To describe run-to-run repeatability of the frozen production pipeline over the whole frozen register, and within the random baseline and hard-case samples, rather than only on the mixed 201-record sample. Repeatability does not establish correctness.

## What "the production conditions" were

Established from the production artefacts before this specification was written (2026-11-10, offline):

- **Production procedure (`analysis/outputs/fable5_full_release_run.py`, 2 July 2026).** The run copied run 1's 201-entry cache in as a seed, then called `classify_all` on the full classifier data frame. The seeded records were therefore classified in run 1, and only the other 1,108 records were sent to the API in that run (111 requests; `fresh_api_classifications` 1,108).
- **Run 1 (`analysis/outputs/model_comparison_fable5_run_sample.py`).** The same data frame filtered to the 201 sample records, in register order, 10 per request (21 requests).
- **Code.** Commit `fdc13fd` (2 July 2026; adds only outputs, so its code is the code that ran). Since then the classifier changed only in its docstring and a default the run overrode; `analysis/register_cleaning.py` and `dashboard/dataset_normalisation.py` changed substantially (Record IDs, duplicate handling, dataset text), so current code does not reproduce the production input.
- **Input.** `data/dea_accredited_projects_20260601.csv`, selected by the `fdc13fd` register manifest (`current` = 20260601); the current manifest points to a later register and must not be used.
- **Request.** `client.messages.parse(model="claude-fable-5", max_tokens=8192, messages=…, output_format=BatchLayerResult)`; the static taxonomy prompt carries `cache_control: ephemeral` and the per-batch projects block follows it; no `temperature`, no `effort` (API default `high` on Fable 5), no `thinking` parameter, synchronous Messages API (not the Batch API). All 111 production requests and all 21 run-1 requests used `messages.parse` and ended `end_turn`.
- **Environment.** Python 3.13.2; `anthropic` 0.86.0 and `pydantic` 2.12.5 (installed 25 March 2026), `httpx` 0.28.1, `pandas` 2.2.3, `PyYAML` 6.0.2; unchanged since before the production run.

## Conditions for the replicate

| Condition | Value |
|---|---|
| Code | `git archive fdc13fd`, extracted to a temporary directory and imported from there; tree hash recorded |
| Input register | the on-disk June file, unchanged since 26 June 2026 (SHA-256 recorded; its committed blob matches the manifest hash `abd65ff9…`) |
| Taxonomy | `taxonomy_data_dictionary.yaml`, SHA-256 `7ddbf1bb5ae4588c…` (identical at `fdc13fd`) |
| Model, prompt | `claude-fable-5`; `dict-1.0-rc2` |
| Request parameters | exactly as production (table above); runner asserts none is added |
| SDK and runtime | the versions above; runner aborts if any differ |
| Records | the 1,309 rows of the July classifier data frame |
| Stage R (run-1 conditions) | the 201 run-1 sample records in register order, 21 batches of up to 10 |
| Stage P (production conditions) | the remaining 1,108 records in register order, 111 batches (110 of 10, one of 8) |
| Order of stages | R then P, matching production's seeding |
| Retries | as production: up to 3 attempts per batch, waits of 2 and 4 seconds, 0.5 seconds between batches |
| Structured-output fallback | **not accepted.** Production code falls back to an unstructured `messages.create` call if parsing fails; production never used it. A fallback is treated as a failed attempt and the batch is retried with `messages.parse` |

Batch composition is fixed in advance and does not change if the run is interrupted: resumption skips whole completed batches only.

## Pre-run checks (offline, no API call)

The runner's check mode must pass before any request:

1. Code snapshot imports from the temporary tree, not the working copy.
2. Input and taxonomy hashes; environment versions.
3. 1,309 records; the 201 run-1 sample IDs all present; Stage R and Stage P batch lists as above.
4. Stage R batch membership equals run 1's cache order; Stage P batch membership equals the production cache order for the non-seed records (after the post-run ID changes below).
5. For every record, the prompt fingerprint (title and dataset text) equals the production cache entry's fingerprint.
6. Static prompt SHA-256 and every batch's projects block recorded.

Post-run ID changes, applied only for comparison and mapping: `2020/097` → `2020/097 CLOSED`; `2020/102` → `2020/102 CLOSED`; `2023/211/a` and `2023/211/b` were collapsed into `2023/211`, whose production entry is `2023/211/b` by fingerprint.

## Smoke check (first paid requests)

Run the first batch of Stage R and the first batch of Stage P. For each, the response's uncached `input_tokens` must equal the value logged for the same batch in run 1's and production's usage logs, and the response model must be `claude-fable-5`. Equal input tokens show the request text is identical. If either differs, stop and investigate before any further request. The runner applies the same check to every later batch and stops at the first difference.

## Outputs

Under `analysis/fable_production_replicate_exploratory/run_<UTC timestamp>/`: the replicate cache (1,309 entries), a batch ledger (stage, batch number, record IDs in order, attempts, response ID, response model, stop reason, API path, token usage), and run metadata (conditions, hashes, versions, cost). Labels mapped to the 1,308 canonical records with the ID changes above.

## Comparisons (defined before the run)

Replicate against production labels (MOD-006), using the classifier's parsed sets:

- Research Domains and Analytical Purposes: exact-set agreement (count, denominator, proportion) and mean Jaccard.
- Each tag (COVID-19 & Pandemic; Demographic disparities / equity), both tags jointly, and all four components jointly.
- Populations, never pooled: the full register (1,308); the random baseline (150); the hard-case sample (75, diagnostic); Stage R records (201) and Stage P records (1,107 canonical).
- For the 201 Stage R records, also against run 2, giving three runs (run 1 = production, run 2, replicate).
- Record-level diagnostics: which records and components differ.

Descriptive only: no intervals and no tests, matching the pre-existing stability report.

## Exclusions

- Production labels are not replaced, merged or averaged with replicate labels.
- No change to the protocol, taxonomy, prompt, model or code under validation.
- No Batch API, no parameter added for cost or speed.
- No adjudication findings or project-owner responses are read.

## Spend

The expected cost is computed in the pre-run check from the token usage logged by run 1 and production, at Fable 5's first-party rates (USD 10 per million input tokens, 12.50 cache write, 1 cache read, 50 output). The production release script reported USD 21.06 for its 1,108 records and the run-1 script USD 4.02, but both subtracted cached tokens from input tokens twice, so they understate the cost slightly. Actual cost varies with output length. The investigator approves the spend before the smoke check.
