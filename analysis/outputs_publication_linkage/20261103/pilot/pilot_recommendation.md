# Feasibility pilot: interpretation and recommendation (2026-11-03)

Hand-written reading of `pilot_report.md` (all numbers there are produced by
code). This is a **partial pilot**: only CORE could be reached. OpenAlex,
Europe PMC, Gateway to Research, GOV.UK and Semantic Scholar were refused by
the cloud environment's network policy (proxy 403 on CONNECT), so their
documentation hosts were unreachable too and their clients have been tested
only offline against fixtures.

## What the pilot shows

- **CORE author-centred retrieval works.** 183 live calls for 149 unique
  researchers (about 1.2 per researcher) in 12 minutes, no cost. CORE's
  documented full-text and abstract search fails server-side ("fullText is not
  a searchable field"), so its phrase searches fall back to titles; the useful
  route is pulling each researcher's works and scanning CORE's inline full text
  locally.
- **Yield from CORE alone:** Tier 1 or 2 for 6 of 50 projects (12%, 95% Wilson
  CI 6% to 24%); any tier for 11 of 50 (22%). No Tier 1 in the sample. Tier 1
  wording does occur in the wild: during development, outside the sample, a
  paper stated "Digital Economy Act project number 2022/139".
- **Tier 2 evidence is concentrated.** 14 of the 21 Tier 2 pairs rest on an
  environment statement alone, all of them SAIL team papers linked to the two
  SAIL Census Wales 2011 projects in the sample (2 of the 6 projects with a
  Tier 1-2 output). The other 7 pairs also carry a route statement (DEA,
  Research Accreditation Panel); 5 of those are for the 4 SRS projects.
- **Boilerplate was the main precision risk, and is now handled.** Two
  wordings produced false route statements in development: "made available to
  accredited researchers only" (CVD-COVID-UK / NHS England SDE papers) and
  SAIL's "UK Statistics Authority (UKSA) Digital Economy Act (DEA) accredited
  Trusted Research Environment". Route phrases inside such sentences are now
  recorded as boilerplate and do not count. Generic dataset terms ("COVID-19",
  "Longitudinal Study", "Family Court") were removed for the same reason.
- **Adjudication:** 13 pairs queued, 13 decided by a helper agent, all 13
  quotes verified verbatim, all 13 rejected. The agent flagged two close calls
  for a human look: `2021/044` with `doi:10.1136/jech-2022-218786` (same team
  and topic, no Infection Survey named) and `2022/111` with
  `doi:10.23889/ijpds.v10i4.3193` (uses the register's Data First family court
  data, but via SAIL rather than the register's SRS).

## Recommendation

1. **Open network access and re-run the pilot before the full run.** Add
   `api.openalex.org`, `www.ebi.ac.uk`, `gtr.ukri.org`, `www.gov.uk` and
   `api.semanticscholar.org` (and, for checking parameters, `docs.openalex.org`
   / `developers.openalex.org`) under the cloud environment's Network access
   settings. The same command re-runs every source and reuses the CORE cache:
   `python -m analysis.publication_linkage.pilot --run-date <date>`.
   Without that, the pilot cannot compare sources, which is its main purpose.
2. **Keep CORE.** It produced every match so far, and its inline full text is
   what makes Tier 2 statements quotable. Full register: about 3,200 calls,
   about 4 days at the personal tier's 1,000 tokens a day (the responses
   reported a 150-token limit that never fell during the run, so the key may
   be on a larger tier; the client paces at 25 a minute regardless).
3. **Keep OpenAlex and Europe PMC (provisionally).** OpenAlex is the expected
   breadth source; its full-text phrase hits cannot be quoted, so CORE and
   Europe PMC full text are needed to confirm them. Europe PMC should matter
   for SAIL/health projects. Estimated OpenAlex cost for the full register is
   about $2.90, so about 4 days inside the free $1/day with the $0.90 stop.
4. **Decide GtR and GOV.UK after the re-run.** Government-sector projects are
   7 of 50 in the sample; GOV.UK is the only source aimed at them, but its pages
   rarely name authors, so it can reach Tier 2 only when a register researcher
   is named in the body. GtR adds candidates only through grant-to-project
   matching; keep it if the re-run shows unique Tier 1-2 outputs.
5. **A decision for you:** should environment-only Tier 2 (the SAIL pattern)
   count in the headline? The brief's rules say yes; I suggest keeping that
   definition and also reporting the headline with route statements only as a
   sensitivity, and sampling the precision check by statement type.
