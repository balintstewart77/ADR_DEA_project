# Publication linkage: feasibility pilot (20261103)

> **Absence of a findable output is not evidence of no output.** Government analysts' work is often
> internal, and many papers do not acknowledge the accreditation. Every rate below is a lower bound on
> public, findable, attributable outputs, not on research activity. Project-level files in this folder are
> working data; anything published is aggregated.

## Status

- Register snapshot 2026-10-21 (version 20261021), 1,385 cleaned records.
- Mature cohort: accredited on or before 2024-10-21 (two years before the snapshot).
- Sources that ran: core. Sources blocked by the session's network policy: openalex, europepmc, gtr, govuk, semanticscholar.
- Because sources were blocked, **this is a partial pilot**: rates, overlaps and source recommendations below cover only the sources that ran. Re-running the same command once access is open adds the missing sources (cached calls are reused).

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

Live run 2026-11-03T19:34:00+00:00 to 2026-11-03T19:47:00+00:00 (UTC); calls and errors from the call log. Tables were rebuilt from the cache on 20261103 without further calls.

| source | status | candidates | live_calls | http_errors | cost_usd | seconds |
|---|---|---|---|---|---|---|
| openalex | blocked | 0 | 0 | 0 | 0.0 | 0.0 |
| core | ok | 2740 | 183 | 5 | 0.0 | 711.0 |
| europepmc | blocked | 0 | 0 | 0 | 0.0 | 0.0 |
| gtr | blocked | 0 | 0 | 0 | 0.0 | 0.0 |
| govuk | blocked | 0 | 0 | 0 | 0.0 | 0.0 |
| semanticscholar | blocked | 0 | 0 | 0 | 0.0 | 0.0 |

- **openalex**: network policy refused host (proxy 403)
- **core**: fullText search unavailable at CORE (core 500: {"message":"Azure search failed with status code: 400. Error context: code=OperationNotAllowed, message=Illega); title-only phrase search used
- **core**: project-ID full-text search skipped: CORE fullText search unavailable
- **europepmc**: network policy refused host (proxy 403)
- **gtr**: network policy refused host (proxy 403)
- **govuk**: network policy refused host (proxy 403)
- **semanticscholar**: network policy refused host (proxy 403)

## Matches

| tier | project_output_pairs |
|---|---|
| Tier 1 | 0 |
| Tier 2 | 21 |
| Tier 3 | 22 |
| unresolved (pending adjudication / rejected) | 13 |

Tier 2 pairs by statement type (route = DEA / Research Accreditation Panel / accredited researcher / UKSA; environment = the project's own secure environment named):

| statement_type | tier2_pairs |
|---|---|
| environment | 14 |
| route+environment | 7 |

Per source and tier (pairs; unique = found by that source alone):

| source | tier | project_output_pairs | unique_pairs_this_source_only | projects | projects_this_source_only |
|---|---|---|---|---|---|
| core | tier_2 | 21 | 21 | 6 | 6 |
| core | tier_3 | 22 | 22 | 10 | 10 |
| core | unresolved | 13 | 13 | 6 | 6 |

Overlap between sources, Tier 1-2 outputs:

| sources | outputs |
|---|---|
| core | 13 |

## Share of pilot projects with a findable output

- Tier 1 or 2 (headline definition): 6/50 = 12% (95% Wilson CI 6% to 24%)
- Tier 1 (project ID quoted): 0/50 = 0% (95% Wilson CI 0% to 7%)
- Any tier including Tier 3 (probable): 11/50 = 22% (95% Wilson CI 13% to 35%); Tier 3 only: 5
- Median lag from accreditation to first Tier 1-2 output: 12 months (n=6)

Unweighted counts; the proportional design makes the sample roughly self-weighting by year x sector. Pilot intervals are wide by design and are not the headline estimate.

| accreditation_year | projects | with_t1_t2 | with_any_tier |
|---|---|---|---|
| 2019 | 2 | 0 | 1 |
| 2020 | 7 | 1 | 1 |
| 2021 | 9 | 2 | 4 |
| 2022 | 11 | 2 | 3 |
| 2023 | 11 | 0 | 1 |
| 2024 | 10 | 1 | 1 |

| sector_group | projects | with_t1_t2 | with_any_tier |
|---|---|---|---|
| academic | 32 | 3 | 8 |
| commercial | 6 | 0 | 0 |
| government | 7 | 2 | 2 |
| third-sector | 5 | 1 | 1 |

## Adjudication

Pairs the rules cannot settle (initial-only author, acronym-only dataset, another environment named, or a strong statement with no dataset string) are queued for helper-agent adjudication; each decision must quote the shown text verbatim, and the quote is checked by code.

| queued | decided | verified | unverified | confirmed | rejected | capped_to_tier3 |
|---|---|---|---|---|---|---|
| 13 | 13 | 13 | 0 | 0 | 13 | 0 |

## Full-run estimates

| source | pilot_calls | unit | units_full_register | est_calls_full_run | est_days_at_1000_tokens_per_day | est_cost_usd |
|---|---|---|---|---|---|---|
| core | 186 | unique researcher | 2548 | 3181 | 4 | 0.0 |
| openalex | 0 | unique researcher (+ phrase pages) | 2548 | 5161 |  | 2.87 |
| govuk | 0 | register dataset x 3 route terms (+ page fetches) | 353 | 1059 |  | 0.0 |

## Limitations

- Blocked sources mean recall here is lower than the full design would give.
- CORE's documented full-text and abstract search currently fails server-side, so CORE phrase searches fall back to titles and CORE contributes through author-centred retrieval with local full-text scanning.
- Author matching is by family name plus a compatible first given name; common names can produce false candidates (mitigated by the dataset, statement and date conditions).
- Environment statements for SAIL, UKDS SecureLab, NISRA and Scottish Safe Havens are weaker evidence of DEA use than DEA/RAP statements, because those environments host non-DEA work too; Tier 2 is split by statement type above for that reason.
- Outputs shared by two projects with the same team count for both.
