# Official sampling execution runbook

Use this runbook only after excluded pilot completion and debrief, closure of the dated pilot-feedback log, final package QA, Gate 1 freeze, official preregistration verification, and Gate 2 authorisation. OSF registration `8sn2j` and the prospective Gate 2 authorisation are recorded; the official draw remains unexecuted. Execution is permitted only while the Gate 2 authorisation commit is the clean current HEAD and its direct parent is the receipt's frozen implementation basis. The public approval receipt at `preregistration/registration_records/osf_registration_8sn2j.yaml` is not the Gate 2 execution credential. The registered packet contains no sampled identities.

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
