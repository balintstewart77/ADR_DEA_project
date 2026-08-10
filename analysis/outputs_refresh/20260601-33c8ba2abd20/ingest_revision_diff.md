# Ingest/revision comparison

Newly observed content snapshot versus the immediately preceding distinct
ingested snapshot, regardless of nominal source date.

- Baseline nominal source date: 2026-06-01
- Baseline XLSX SHA-256: `4f3851544846059c15b4df4dadc63b33079ca47a07e4eae41e98d5ddb3e452a3`
- Baseline canonical CSV SHA-256: `abd65ff9d8a5a521a83b5a8cd62eac2808fc330eda9f3f012751ad364f5c9d5d`
- Target nominal source date: 2026-06-01
- Target XLSX SHA-256: `33c8ba2abd2085a28b2e5ca5ba2913398c6edb96f59f31331e5c125c96661014`
- Target canonical CSV SHA-256: `918117144c4b01908dfdefc411c2baef81431cf3f0dd42d0c20a1b7d9e942acd`
- Raw rows: 1,450 → 1,450
- Raw projects added / removed / changed: 0 / 0 / 1
- Cleaned rows: 1,308 → 1,308
- Cleaned projects added / removed / changed: 0 / 0 / 0
- Analytical impact: none

## Raw content change

- `2023/126` (`Researchers`)

The changed row is SRSA-only and is excluded at the prespecified DEA
legal-basis filter before duplicate handling and all analytical use.
