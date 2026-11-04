# Publication linkage

Links projects on the UKSA register of DEA-accredited research projects to the
public outputs they produced, using free sources only. Method decisions are in
`METHODS_LOG.md` ("Publication linkage" entries).

## Layout

| Module | Role |
|---|---|
| `register_records.py` | Cleaned register (`load_raw` + `process_data`) joined to `register_properties.csv`; researchers as name/institution pairs; dataset match terms from the reference layer. |
| `matching.py` | Accreditation phrases, project-ID detection, dataset terms, author names, statement snippets. Pure functions. |
| `outputs.py` | Candidate outputs, output-type classification, de-duplication (DOI, then title + year). |
| `tiers.py` | Evidence per project-output pair and tier rules (1 explicit, 2 strong, 3 probable). |
| `http_client.py` | Cached, rate-limited, retrying HTTP client; blocked-host detection; OpenAlex daily spend ledger. |
| `sources/` | OpenAlex, CORE, Europe PMC, Gateway to Research, GOV.UK; Semantic Scholar enrichment. |
| `adjudication.py` | Queue of pairs the rules cannot settle; verification of helper-agent quotes. |
| `pipeline.py` | Runs sources, links outputs, builds the output tables. |
| `pilot.py` | Feasibility pilot (50 stratified mature-cohort projects) and its report. |

## Running

```bash
python -m analysis.publication_linkage.pilot --run-date 20261103
python -m analysis.publication_linkage.pilot --run-date 20261103 --offline
```

The first command calls every source; blocked or failing sources are logged
and skipped. The second rebuilds every table from the cache with no network
calls (use it after adjudication decisions are added). `--name` picks the
output folder under the run date (the all-sources pilot is
`--name pilot_all_sources`); `--report-only` rewrites the report and estimates
from a finished run's saved tables.

Adjudication runs in rounds (`adjudication/round_NNN/`): batches for helper
agents, their `.decisions.jsonl`, and a tracked `manifest.json` of the text
hash each item was shown, so a decision is reused only on identical text.
`adjudication/reviewer_decisions.jsonl` holds human decisions, applied last.

Credentials come from the environment only: `OPENALEX_API_KEY` (query
parameter `api_key`) and, optionally, `CORE_API_KEY` (Bearer). Without
`CORE_API_KEY` CORE is called without an Authorization header, so a network
secret configured on the cloud environment is attached by the proxy.

Raw responses are cached in `data/publication_linkage_cache/` (ignored by git),
with a call log (`call_log.jsonl`) and the OpenAlex spend ledger
(`openalex/usage_ledger.json`). Outputs go to
`analysis/outputs_publication_linkage/<YYYYMMDD>/`.

## Reporting rule

Absence of a findable output is not evidence of no output. Project-level files
are working data; anything published (blog, dashboard, paper) is aggregated,
and no list or chart of named projects or researchers with "no output found"
is published.
