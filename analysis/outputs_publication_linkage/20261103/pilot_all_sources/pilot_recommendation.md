# All-sources feasibility pilot: interpretation and recommendation (2026-11-04)

Hand-written reading of `pilot_report.md` in this folder (every number there is
produced by code). Same 50 projects and seed as the CORE-only pilot in
`../pilot/`. All five discovery sources ran; Semantic Scholar (enrichment only)
failed on rate limits.

## Results

- **Headline (Tier 1 or 2): 12 of 50 projects, 24% (95% Wilson CI 14% to
  37%)**, up from 6 of 50 with CORE alone.
- **Sensitivity, accreditation-route statements only: 9 of 50, 18% (10% to
  31%).** The gap is the SAIL pattern: 39 of the 58 Tier 2 pairs rest on the
  project's environment being named, with no route statement.
- Any tier including Tier 3: 20 of 50 (40%). Tier 1: none. Median lag to the
  first Tier 1-2 output: 21 months (n=12).
- Adjudication: 51 pairs, 47 newly decided by four helper agents in parallel
  plus 4 reused from round 1 (text unchanged); all 51 quotes verified. Your two
  decisions are applied as final, and both overrode the round-2 agent:
  it rejected `2021/044` / `jech-2022-218786` (now Tier 3) and gave Tier 3 to
  `2022/111` / `ijpds.v10i4.3193` (now rejected).

## Per-source yield, overlap and cost

| Source | Live calls | Cost | Tier 1-2 outputs it found (of 39) | Unique Tier 2 pairs | Statement text supplied for Tier 2 pairs (of 58), only source |
|---|---|---|---|---|---|
| OpenAlex | 478 (113 of them HTTP 429, retried, not charged) | $0.2551 | 38 | 3 (1 project) | 34, 3 |
| Europe PMC | 1,182 | free | 31 | 0 | 49, 16 |
| CORE | 219 this round (plus 183 cached from the first pilot) | free | 20 | 0 | 27, 5 |
| GtR | 534 | free | 3 | 0 | 0, 0 |
| GOV.UK | 162 | free | 0 | 0 | 0, 0 |
| Semantic Scholar | 5, all HTTP 429 | free | n/a | n/a | n/a |

OpenAlex finds almost every output; Europe PMC and CORE are what make Tier 2
checkable, because OpenAlex returns no full text: without Europe PMC full text
16 Tier 2 pairs would lose their quotable statement, without CORE 5. At Tier 3,
OpenAlex adds 30 unique pairs (6 projects) and CORE 9 (1 project).

OpenAlex spend today was $0.2551 of the free $1 (ledger and server credit
counter agree after removing the 113 rate-limited calls, which the server did
not charge); server credits left: 7,449 of 10,000.

## Full-run estimates (from every request the pilot needed, cached or live)

| Source | Calls | Cost | Limit |
|---|---|---|---|
| CORE | about 6,500 | free | about 7 days at 1,000 tokens/day (binding) |
| OpenAlex | about 6,000 | about $4.14 | about 5 days at the $0.90/day stop |
| Europe PMC | about 18,800 (mostly full-text fetches) | free | hours, not days |
| GtR | about 9,600 | free | hours |
| GOV.UK | about 1,200 | free | under an hour |

## Recommendation

1. **Keep OpenAlex, Europe PMC and CORE.** OpenAlex for discovery; Europe PMC
   and CORE for the text that lets the rules quote statements. Space OpenAlex
   author searches (`/authors?search`) about a second apart to avoid the 429s.
2. **Drop GtR.** 534 calls produced 3 Tier 2 pairs, all found elsewhere, and
   no statement text; about 9,600 calls for the full register.
3. **Drop GOV.UK** (or keep as a cheap optional pass). 162 calls, 45
   candidates, no linked pair; the 2 government-sector projects with outputs
   were found through OpenAlex and Europe PMC. GOV.UK pages rarely name authors,
   so they can only reach Tier 2 when a register name is in the body.
4. **Drop Semantic Scholar**, or request a free API key if DOI resolution for
   author-less records becomes necessary; OpenAlex already supplies abstracts.
5. **Keep the project-ID searches in OpenAlex and Europe PMC; drop CORE's.**
   No Tier 1 appeared in this sample, and the ID hits that reached the rules
   were funder and university project numbers ("Research Project no:
   2020/080"), now filtered unless a DEA-specific term is beside the ID. The
   route is still the only way to find Tier 1, and the known "DEA project number
   2022/139" paper shows it works in OpenAlex; $0.001 a project. CORE's ID
   search reaches titles and abstracts only and would cost about 1,400 tokens,
   so dropping it shortens the CORE-bound timeline by about 1.4 days.
6. **Decision for you: near-miss adjudication.** The rule that queues "strong
   statement + author + date, no dataset string" pairs sent 47 pairs to
   adjudication; the agents confirmed none, and the only one that survived is
   the `2021/044` pair you classified as Tier 3. At full scale that would be
   roughly 1,300 decisions. I suggest adjudicating a 10% random sample of near misses
   in the full run (to monitor what the dataset rule misses) and leaving the
   rest unresolved, rather than adjudicating them all.

With 2, 3, 4 and the CORE half of 5, the full run is about 6 days, bounded by
CORE tokens, with OpenAlex spend spread over the same days inside the free
tier.
