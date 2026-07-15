# Official sampling execution runbook

Use this runbook only after collaborator review, excluded pilot completion, Gate 1 freeze, OSF registration and Gate 2 authorisation. The Phase 4 package does not contain a registration receipt or sampled identities.

## Before execution

- Confirm coder training and the excluded pilot are complete and all pilot-driven changes are resolved.
- Confirm Gate 1 passed and the final preregistration package is frozen.
- Confirm OSF registration completed; record its real identifier and timestamp.
- Confirm Gate 2 passed, record the frozen Git commit, and verify that HEAD equals it.
- Verify a clean worktree and activate the recorded Python environment (Python 3.13.2, NumPy 2.2.5, pandas 2.2.3 for this candidate).
- Verify the sampling specification and all three input hashes.
- Create `preregistration_restricted/registration_receipt.json` with the real registration identity, timestamp, frozen commit, Gate 2 confirmation and the expected hashes. Do not fabricate these values.
- Confirm `preregistration_restricted/sampling/<official-output-directory>/` does not already contain an official draw.

## Execution

1. Run `python scripts/draw_validation_samples.py --validate-real-inputs`.
2. Review every displayed pre-draw count and hash. This command creates no RNG and writes nothing.
3. Record the full official command, using the canonical paths, the real receipt, a new restricted output directory, `--execute-official-draw`, and the typed token `EXECUTE_REGISTERED_DEA_DRAW`. Use placeholders while preparing the command; do not enter the token until Gate 2.
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
