# Portfolio accreditation-year filter contract

## Pinned date contract

- Authoritative release: canonical UKSA register snapshot `20260813`, read from
  `data/register_snapshots/dc97c680115fc036b26ed486b163d5b6afeb242411e2f1a1020d71eacbc44a40/canonical.csv`
  (SHA-256 `381593a7c64b297b9ee289c84b02a6982824b74f85800b4082e5ff1f059583f4`).
- Record unit: retained accreditation record, uniquely keyed by `Record ID`.
  `Project ID` is not a join key because four official IDs each occur in two
  legitimate retained records in the current release.
- Authoritative field: `Accreditation Date`. Project Explorer first formats it
  as `%d %b %Y` and parses it with
  `pandas.to_datetime(..., format="%d %b %Y", errors="coerce")`; this is the
  shared selection parser. Year is `parsed_date.dt.year`; the stored `Year` and
  `Quarter` columns are derived aggregation fields, never selection fallbacks.
- Control: inclusive two-handle year range, with every integer from the full
  canonical register's minimum through maximum year available as a mark.
  The default/full range is 2019–2026 and means all years.
- Missing/invalid policy: all years includes undated or invalid records;
  restricted ranges exclude them. The selected-count text reports how many are
  included or omitted. Current retained data contain none.
- Options: constructed once from the full canonical register before any
  Explorer, Portfolio, or sub-view filter. They do not narrow with selections.
- Exposure observation window: the established register start `R0` is
  `2019-01-01`. The established cutoff `C` is the maximum authoritative
  `Accreditation Date` in the full cleaned register, currently `2026-08-12`;
  it is not inferred from selected records. As in the pre-filter calculation,
  duration is `(C - start).days / 365.25`: the interval is half-open at `C`
  and no extra day is added. All years preserves `[R0, C)`. An inclusive
  restricted selection `[L, U]` uses
  `[max(R0, L-01-01), min(C, (U+1)-01-01))`, so a completed calendar year runs
  to the following 1 January even if its last accreditation was earlier.
- Reset/session state: Portfolio's **All years** button restores the full range.
  Explorer and Portfolio use distinct component values; Dash retains each while
  switching tabs, with no new reload-persistence mechanism.

Current record-level reconciliation is 1,343 eligible = 1,343 valid-year + 0
missing + 0 malformed. Counts by year are 22, 120, 160, 202, 209, 236, 272 and
122 for 2019–2026 respectively, summing to 1,343. `Accreditation Date` disagrees
with stored `Year` for 0 records and with stored `Quarter` for 0 records. The
four repeated official Project IDs do not cross years; consequently there is no
cross-year distinct-ID overlap in this release, although 2024 contains 236
record units and 234 distinct official Project IDs.

## Portfolio output inventory

| View | Outputs | Record source and aggregation | Status |
|---|---|---|---|
| Overall Trends | yearly entries, quarterly entries, processing-environment pie | canonical register; record counts before aggregation | deterministic register values |
| Dataset Demand | top-N demand/rate, annual trend, provider breakdown | dataset rows expanded from canonical records; distinct selected `Record ID` per dataset/provider; historical availability is curated where present and otherwise proxied by first full-register appearance; exposure is its intersection with the explicit observation window | deterministic derived values |
| Linked Data Uptake | adoption curve, exposure-rate bar, adoption summary table | matched-product rows joined by `Record ID`; selected-period project/request definitions preserved; historical first accredited use comes from the full matched-product history and exposure is its intersection with the explicit observation window | deterministic derived values with existing DEA-route caveats |
| Institutions | top-N bar and annual trend | affiliation rows expanded from canonical records; distinct `Record ID` | deterministic derived values |
| Thematic Analysis | headline count; domain/purpose totals and trends; domain-purpose and domain co-occurrence; domain-breadth trend and coverage; tag trend and tag-domain bars | frozen classifications filtered by canonical `Record ID`, then expanded/aggregated | indicative LLM classifications; existing warning retained |
| Deterministic thematic facets | record-linkage distributions/trend/domain breakdown; researcher-sector distribution/co-occurrence; unit, collection-method and temporal-structure distributions/trends | frozen deterministic facets filtered at record level, then expanded/aggregated | deterministic derived values; mixed-layer latent-demand warning retained |
| Enriched Register | displayed count/table and CSV download | classified records joined and filtered by `Record ID`; global and local filters intersect | register fields plus clearly marked deterministic/indicative derived fields |

The global summary cards above the main tabs intentionally remain app-wide.
Portfolio therefore shows its own selected-record count next to the year control.
Dataset-demand eligibility is 1,333 record units, institution eligibility 1,334,
linked-product eligibility 385, and thematic eligibility 1,343; each population
has zero invalid-year units and its disjoint year counts reconcile to its total.

The compact pre-change regression baseline is
`tests/fixtures/portfolio_analysis_prechange_baseline.json`. It records the
input identity, headline values, chart-eligibility totals, yearly series, and
canonical hashes of the numeric figure/table payloads at the original defaults.
Provider and product filters affect selected numerators, never the calendar
window or historical anchors. Adoption curves enumerate every year or quarter
intersecting the explicit window, retain eligible zero-use periods after
historical first use, report percentages as unavailable when a period has no
selected register records, and never extend beyond `C`.

Domain breadth uses the active taxonomy's substantive-domain labels on each
selected, dated `Record ID`. It counts distinct recognised labels after
excluding the taxonomy's `Unclear` fallback; a set with an unrecognised token
is excluded as invalid rather than partially counted. The three plotted buckets
are 1, 2 and 3+ domains, with each period's percentage denominator restricted
to records in one of those buckets. The coverage table separately reconciles
unmatched, missing, invalid and zero-substantive classifications; undated
records remain a selection-level exclusion. This is an indicative description
of assigned domains, not evidence of interdisciplinary methods or
collaboration.

## Domain-breadth count diagnostic

The active release pointer, `data/release_pointers.json`, selects
`analysis/outputs_classified_20260813-dc97c680115f/layer_classifications.csv`.
That production CSV has no `substantive_domain_count` column. The dashboard
creates the displayed field while loading it in
`dashboard/data/thematic.py:_count_substantive_domains`, by counting every
non-empty semicolon-delimited token. It is therefore a dashboard-derived
display count, not a historical count loaded from the release file.

The chart resolves its label universe from the active Layer A labels in
`taxonomy_data_dictionary.yaml`, whose `dictionary_version` is `1.0-rc2`: 12
recognised labels, including `Unclear from Register Entry`, of which 11 are
substantive for this chart. The active release metadata identifies its taxonomy
as `dict-1.0-rc2`. Explicitly comparing the trimmed labels used in the release
CSV with the current 12-label universe found no extra or missing label. The
release does not separately preserve a frozen label list, but its version
identifier and observed values agree with the active universe. The displayed
count itself has no taxonomy label universe: it counts tokens indiscriminately.
Consequently, the discrepancy is a counting-rule difference, not evidence of a
taxonomy-version mismatch.

There are two discrepancies (below the 20-record documentation limit), both
with the same fallback-only pattern:

| Record ID | Original domain-label value | Stored count (dashboard-derived) | Chart-derived count | Chart status | Evidence-based explanation |
|---|---|---:|---:|---|---|
| 2024/019 | `Unclear from Register Entry` | 1 | 0 | zero substantive domains; excluded | The loader counts the fallback token. The chart recognises it but excludes it from substantive breadth. |
| 2025/200 | `Unclear from Register Entry` | 1 | 0 | zero substantive domains; excluded | The loader counts the fallback token. The chart recognises it but excludes it from substantive breadth. |

No classifications, source counts, or taxonomy labels were changed by this
diagnostic.
