# Register refresh: snapshot 33c8ba2abd20

- Observation date: 2026-08-10
- Fetch status: new content snapshot under an existing nominal source date
- Nominal source date: 2026-06-01
- Raw XLSX SHA-256: `33c8ba2abd2085a28b2e5ca5ba2913398c6edb96f59f31331e5c125c96661014`
- Canonical CSV SHA-256: `918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd`
- Cleaned register rows: 1,308

## Ingest/revision comparison

This comparison uses the immediately preceding ingested content hash, even
though both snapshots have the same nominal 2026-06-01 source date.

- Raw added / removed / changed: 0 / 0 / 1
- Cleaned added / removed / changed: 0 / 0 / 0
- Analytical impact: none
- Report: `ingest_revision_diff.md`

## Nominal-release comparison

This separately retained historical comparison uses the latest March revision
and latest June revision. It is not labelled as a change detected in August.

- Raw added / removed / changed: 38 / 1 / 2
- Cleaned added / removed / changed: 38 / 1 / 1
- Report: `nominal_release_diff.md`

- Deterministic facets: byte-identical; existing output retained
- Classification: not run; classification pointer unchanged
- Dashboard analytical population: unchanged
- Frozen validation source and cleaned-population pointers: unchanged
- Outcome: `provenance-only; no analytical impact; not a deviation`
