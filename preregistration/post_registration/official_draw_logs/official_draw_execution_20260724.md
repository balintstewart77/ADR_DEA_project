# Official validation sample draw execution — 24 July 2026

The official validation sample draw was executed exactly once under OSF registration `8sn2j`, protocol `PRO-018` / v1.1.

- Execution start: `2026-07-24T15:56:18+01:00` (`2026-07-24T14:56:18Z`)
- Execution-time authorisation commit: `9fcabc3699ae2f047b7d33460c9867ab68457455`
- Frozen implementation basis: `abfdc3e83078fc0c510a30e699592074202c3525`
- Python: `3.13.2`
- Draw seed: `20260713`
- Script SHA-256: `5a655299b79e5a4af08c1b599212f68f5ff2f8ff7220f992cc12bd147c0f0df1`
- Process exit status: `0`
- Official execution count: `1`
- Redraw authorised: `false`

Exact command, restricted output paths, byte sizes and SHA-256 values are recorded in `preregistration_restricted/registration_receipt.json`. The sample CSVs remain ignored in `preregistration_restricted/sampling/official_draw_20260724/`; this public log contains no sampled identity.

## Aggregate validation

- Active baseline: 150
- Active hard cases: 75 (25 Domain-only, 25 Purpose-only, 25 Domain-and-Purpose)
- Total active: 225
- Baseline reserve: 100
- Hard-case reserve: 50
- Total reserve: 150
- Complete draw: 375 unique Record IDs
- All selected records belong to the frozen population; exclusions are absent; active and reserve sets are disjoint.

## Reserve fallback

The official draw executed successfully once with exit status 0. The seeded hard-case reserve target was 16/17/17. Following baseline-first and active 25/25/25 selection, only 11 Domain-and-Purpose reserve records remained. The frozen implementation applied the registered deterministic shortfall fallback, reallocating six seats evenly to the other strata and producing 19/20/11. Total hard-case reserve remained 50. This is compliant with the registered sampling rule and is not a protocol deviation. A post-execution orchestration instruction had incorrectly treated 17/17/16 as an unconditional final invariant; no redraw was performed.

Assignment generation, REDCap import, formal validation coding, reserve activation and Project Owner recruitment remain unauthorised or unstarted as applicable.
