# Publication linkage: feasibility pilot (20261103)

> **Absence of a findable output is not evidence of no output.** Government analysts' work is often
> internal, and many papers do not acknowledge the accreditation. Every rate below is a lower bound on
> public, findable, attributable outputs, not on research activity. Project-level files in this folder are
> working data; anything published is aggregated.

## Status

- Register snapshot 2026-10-21 (version 20261021), 1,385 cleaned records.
- Mature cohort: accredited on or before 2024-10-21 (two years before the snapshot).
- Sources that ran: openalex, core, europepmc, gtr, govuk. Blocked by the network policy: none. Failed: semanticscholar (see source notes).
- OpenAlex spend by UTC day (ledger of reported meta.cost_usd; stop at $0.90 of the free $1): 2026-11-03: $0.2551 (server credits left 7,449 of 10,000).

## Sample

50 projects drawn with seed 20261103, proportional to accreditation year x sector group (largest-remainder allocation).

| accreditation_year | academic | commercial | government | third-sector |
|---|---|---|---|---|
| 2019 | 1 | 0 | 1 | 0 |
| 2020 | 4 | 1 | 1 | 1 |
| 2021 | 6 | 1 | 1 | 1 |
| 2022 | 7 | 2 | 1 | 1 |
| 2023 | 7 | 1 | 2 | 1 |
| 2024 | 7 | 1 | 1 | 1 |

## Source runs

Live run 2026-11-03T21:30:00+00:00 to 2026-11-03T23:15:00+00:00 (UTC); calls and errors from the call log. Tables were rebuilt from the cache on 20261103 without further calls.

| source | status | candidates | live_calls | http_errors | of_which_429 | cost_usd | seconds_in_responses |
|---|---|---|---|---|---|---|---|
| openalex | ok | 10898 | 478 | 113 | 113 | 0.2551 | 160.5 |
| core | ok | 5811 | 219 | 0 | 0 | 0.0 | 354.1 |
| europepmc | ok | 1824 | 1182 | 20 | 0 | 0.0 | 910.7 |
| gtr | ok | 142 | 534 | 0 | 0 | 0.0 | 101.2 |
| govuk | ok | 45 | 162 | 0 | 0 | 0.0 | 36.8 |
| semanticscholar | failed | 0 | 5 | 5 | 5 | 0.0 | 0.8 |

- **core**: fullText not searchable at CORE (core 500: {"message":"Azure search failed with status code: 400. Error context: code=OperationNotAllowed, mess)
- **core**: phrase and project-ID searches cover titles and abstracts only (CORE fullText not searchable)
- **europepmc**: full text unavailable (failed in the live run, so not cached): PMC8366514
- **europepmc**: full text unavailable (failed in the live run, so not cached): PMC9494386
- **europepmc**: full text unavailable (failed in the live run, so not cached): PMC9676077
- **semanticscholar**: 5 of 5 live calls failed (5 rate-limited, HTTP 429)

## Matches

| tier | project_output_pairs |
|---|---|
| Tier 1 | 0 |
| Tier 2 | 58 |
| Tier 3 | 53 |
| unresolved (pending adjudication / rejected) | 50 |

Tier 2 pairs by statement type (route = DEA / Research Accreditation Panel / accredited researcher / UKSA; environment = the project's own secure environment named):

| statement_type | tier2_pairs |
|---|---|
| environment | 39 |
| route | 4 |
| route+environment | 15 |

Per source and tier. Pairs and projects count discovery (unique = found by that source alone); statement_text_supplied counts pairs where that source's own abstract or full text carries the qualifying statement (the text that makes Tier 2 checkable), and _only_ where no other source did:

| source | tier | project_output_pairs | unique_pairs_this_source_only | projects | projects_this_source_only | statement_text_supplied | statement_text_only_from_this_source |
|---|---|---|---|---|---|---|---|
| core | tier_2 | 29 | 0 | 9 | 0 | 27 | 5 |
| europepmc | tier_2 | 49 | 0 | 8 | 0 | 49 | 16 |
| gtr | tier_2 | 3 | 0 | 1 | 0 | 0 | 0 |
| openalex | tier_2 | 57 | 3 | 11 | 1 | 34 | 3 |
| core | tier_3 | 23 | 9 | 11 | 1 | 1 | 1 |
| europepmc | tier_3 | 1 | 0 | 1 | 0 | 0 | 0 |
| gtr | tier_3 | 1 | 0 | 1 | 0 | 0 | 0 |
| openalex | tier_3 | 44 | 30 | 16 | 6 | 0 | 0 |
| core | unresolved | 26 | 4 | 9 | 1 | 17 | 8 |
| europepmc | unresolved | 36 | 1 | 8 | 0 | 35 | 15 |
| gtr | unresolved | 1 | 0 | 1 | 0 | 0 | 0 |
| openalex | unresolved | 44 | 4 | 11 | 1 | 21 | 4 |

Overlap between sources, Tier 1-2 outputs (each output counted once, by the set of sources that found it):

| sources | outputs |
|---|---|
| europepmc; openalex | 14 |
| core; europepmc; openalex | 13 |
| core; openalex | 5 |
| openalex | 3 |
| europepmc; gtr; openalex | 2 |
| core; europepmc; gtr; openalex | 1 |
| core; europepmc | 1 |

Overlap between sources, Tier 1-3 outputs:

| sources | outputs |
|---|---|
| openalex | 29 |
| core; openalex | 15 |
| europepmc; openalex | 14 |
| core; europepmc; openalex | 14 |
| core | 7 |
| europepmc; gtr; openalex | 2 |
| core; europepmc; gtr; openalex | 1 |
| core; europepmc | 1 |
| core; gtr; openalex | 1 |

Full-text completion for index-reported evidence: 79 DOIs wanted; text found via CORE 20, Europe PMC 6; not found 53.

## Share of pilot projects with a findable output

- Tier 1 or 2 (headline definition): 12/50 = 24% (95% Wilson CI 14% to 37%)
- Sensitivity, explicit accreditation-route statements only (Tier 1, or Tier 2 naming the DEA route, Research Accreditation Panel, accredited researcher or UKSA; environment-only Tier 2 excluded): 9/50 = 18% (95% Wilson CI 10% to 31%)
- Tier 1 (project ID quoted): 0/50 = 0% (95% Wilson CI 0% to 7%)
- Any tier including Tier 3 (probable): 20/50 = 40% (95% Wilson CI 28% to 54%); Tier 3 only: 8
- Projects with an index-reported Project ID that no available full text confirms: 0
- Median lag from accreditation to first Tier 1-2 output: 21 months (n=12)

Unweighted counts; the proportional design makes the sample roughly self-weighting by year x sector. Pilot intervals are wide by design and are not the headline estimate.

| accreditation_year | projects | with_t1_t2 | with_route_only | with_any_tier |
|---|---|---|---|---|
| 2019 | 2 | 1 | 1 | 1 |
| 2020 | 7 | 1 | 1 | 1 |
| 2021 | 9 | 5 | 3 | 6 |
| 2022 | 11 | 2 | 2 | 3 |
| 2023 | 11 | 1 | 1 | 5 |
| 2024 | 10 | 2 | 1 | 4 |

| sector_group | projects | with_t1_t2 | with_route_only | with_any_tier |
|---|---|---|---|---|
| academic | 32 | 9 | 6 | 16 |
| commercial | 6 | 0 | 0 | 0 |
| government | 7 | 2 | 2 | 2 |
| third-sector | 5 | 1 | 1 | 2 |

## Adjudication

Pairs the rules cannot settle (initial-only author, acronym-only dataset, another environment named, or a strong statement with no dataset string) are queued for helper-agent adjudication; each decision must quote the shown text verbatim, and the quote is checked by code.

| queued | decided | reused_from_earlier_round | verified | unverified | confirmed | rejected | capped_to_tier3 | pending | reviewer_decisions | reviewer_decisions_not_linked | reviewer_overrode_agent | round_written |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 51 | 51 | 4 | 51 | 0 | 1 | 50 | 0 | 0 | 2 | 0 | 2 |  |

## Full-run estimates

| source | pilot_calls_needed | of_which_register_wide | est_calls_full_run | est_cost_usd | est_days | limit_basis |
|---|---|---|---|---|---|---|
| core | 322 | 20 | 6533 | 0.0 | 7 | 1,000 tokens/day (personal tier) |
| europepmc | 1043 | 13 | 18775 | 0.0 |  | rate limit only |
| govuk | 162 | 0 | 1243 | 0.0 |  | rate limit only |
| gtr | 559 | 0 | 9563 | 0.0 |  | rate limit only |
| openalex | 355 | 37 | 5970 | 4.14 | 5 | $0.90/day stop within the free $1 |

## Limitations

- Failed this run: semanticscholar; Semantic Scholar is enrichment only, so abstracts came from OpenAlex, Europe PMC and CORE.
- CORE's index rejects every documented full-text lookup (including the docs' own examples), so CORE phrase and project-ID searches reach titles and abstracts only; CORE full text is scanned locally on author-centred results.
- OpenAlex matches phrases and project IDs in full text it does not return; such hits count only once CORE or Europe PMC text lets the rules quote them.
- Author matching is by family name plus a compatible first given name; common names can produce false candidates (mitigated by the dataset, statement and date conditions).
- Environment statements for SAIL, UKDS SecureLab, NISRA and Scottish Safe Havens are weaker evidence of DEA use than DEA/RAP statements, because those environments host non-DEA work too; Tier 2 is split by statement type above for that reason.
- Outputs shared by two projects with the same team count for both.
