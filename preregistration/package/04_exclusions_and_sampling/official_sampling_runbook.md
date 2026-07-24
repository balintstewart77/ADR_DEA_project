# Official sampling execution runbook

This runbook records the controlled procedure used after excluded pilot completion and debrief, closure of the dated pilot-feedback log, final package QA, Gate 1 freeze, official preregistration verification, and Gate 2 authorisation. OSF registration `8sn2j` and the prospective Gate 2 authorisation were recorded before execution. The single authorised official draw was executed once on 24 July 2026 at clean authorisation commit `9fcabc3699ae2f047b7d33460c9867ab68457455`, whose direct parent was frozen implementation basis `abfdc3e83078fc0c510a30e699592074202c3525`. The public approval receipt at `preregistration/registration_records/osf_registration_8sn2j.yaml` was not used as the Gate 2 execution credential. The registered packet contains no sampled identities.

## Completed execution status

- Exit status: 0; official execution count: 1; redraw authorised: false.
- Aggregate output: 225 active and 150 reserve records, 375 unique records total.
- Active hard allocation: 25/25/25.
- The seeded reserve target 16/17/17 encountered six unavailable Domain-and-Purpose seats after baseline-first and active selection. The registered deterministic fallback produced 19/20/11 with no total shortfall.
- Restricted outputs remain at `preregistration_restricted/sampling/official_draw_20260724/`; hashes and aggregate checks are recorded in the canonical receipt and post-registration execution log.
- Deterministic assignments were generated later from the 225 active records only. REDCap import, formal coding, reserve activation and Project Owner recruitment remain unperformed; reserve records were not assigned.

## Before execution

- Confirm coder training and the excluded pilot are complete and all pilot-driven changes are resolved.
- Confirm Gate 1 passed and the final preregistration package is frozen.
- Confirm the recorded OSF registration identity and timestamp against the public approval receipt.
- Confirm the clean implementation-basis commit A. The later Gate 2 authorisation commit B must be its direct child, and official execution must occur at clean `HEAD=B` with `HEAD^=A`.
- Verify a clean worktree and activate the recorded Python environment (Python 3.13.2, NumPy 2.2.5, pandas 2.2.3 for this candidate).
- Verify the sampling specification and all three input hashes.
- Verify the force-tracked `preregistration_restricted/registration_receipt.json` in commit B contains the real registration identity and timestamp, `frozen_git_commit=A`, Gate 2 confirmation, `official_sample_draw_completed=false` and the expected hashes. Commit B deliberately does not record its own hash. Do not fabricate these values or reuse the public approval receipt as the execution credential.
- Restrict commit B to the tracked Gate 2 receipt, the canonical manifest and necessary current administrative status documentation. The guard rejects sampling code, frozen-input, protocol, output, assignment or unrelated changes.
- Do not add any later commit before the draw. Any descendant after B invalidates the authorisation and requires a new explicit Gate 2 authorisation commit directly above a newly verified basis.
- Confirm `preregistration_restricted/sampling/<official-output-directory>/` does not already contain an official draw.

## Execution

1. Run `python scripts/draw_validation_samples.py --validate-real-inputs`.
2. Review every displayed pre-draw count and hash. This command creates no RNG and writes nothing.
3. Record the full official command, using the canonical paths, the real receipt, a new restricted output directory, `--execute-official-draw`, and the typed token `EXECUTE_REGISTERED_DEA_DRAW`. Use placeholders while preparing the command; enter the token only after confirming the clean A-to-B handshake and every other guard condition.
4. Run official mode exactly once and preserve console output.
5. Inspect `sampling_assertion_report.json`; verify counts of 150 baseline active, 100 baseline reserve, 75 hard active and no more than 50 hard reserve, with any shortfall explained.
6. Verify all output hashes recorded in `sampling_metadata.json` and confirm no output existed before execution.

## After execution

- Archive the receipt, command, environment record, metadata and assertion report in restricted storage.
- Keep all active and reserve identities restricted. Release active identities only after initial independent coding is complete and release cannot compromise remaining blinded work.
- Keep reserve identities, strata and draw ranks embargoed until reserve retesting is complete or the reserve is formally retired unused.
- Import only authorised active assignments into REDCap; preserve reserve manifests untouched.
- Public metadata may report aggregate counts and strata without identities.
- Log any deviation immediately. Never redraw because selected records are inconvenient.

## Subsequent assignment generation

The active baseline and active hard-case files were combined only for
deterministic assignment generation. Each of C01, C02 and C03 received all 225
active records once, using registered shuffle seeds 101, 102 and 103. The
restricted assignment crosswalk and `redcap_import_validation.csv` are preserved
outside this public package. No reserve file was used as an assignment input,
and no REDCap import or formal coding action occurred.
