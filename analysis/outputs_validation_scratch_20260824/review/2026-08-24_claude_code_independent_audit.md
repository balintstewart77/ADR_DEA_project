# Stage A Audit Report

## 1. Overall verdict

**Minor issues.** No computational, statistical, denominator or parsing error was found. Every headline figure I was asked to scrutinise reproduced *exactly* under an independently written implementation. Two reporting/protocol-conformance gaps affect how two headline rows should be interpreted.

## 2. Critical issues

None. No finding is capable of changing a computed headline result.

## 3. Minor issues / ambiguities

### a. COVID tag reported without the protocol's required low-prevalence caution

Protocol §8.8 (¶159) is explicit: the COVID tag's "binary-tag diagnostics, **including any tag-level alpha**, will therefore be reported descriptively with an explicit low-prevalence caution rather than interpreted as a stable performance estimate."

Observed two-of-three human-majority support is 12 baseline records. No caution appears in `headline_summary.md`, `methods_stage_a.md`, or any CSV (I grepped for it). The row currently reads as α = 0.940 with a 95% CI of [0.000, 0.000].

### b. The COVID `delta_min` CI of [0.000, 0.000] is a structural artefact, not precision

The production model's COVID tag is identical to coder C01's on **all 150** baseline records (0 discrepancies; C01 vs C02 differ on 1, C01 vs C03 on 2). The LBC panel is therefore numerically the same matrix as ABC, so `delta_A ≡ 0` in every replicate, pinning `delta_min ≤ 0` with an exactly-zero interval.

This is not an aliasing bug — the model differs from C01 on 1 hard-case COVID record, on 116/225 Research Domain records and 157/225 Purpose records — but presented bare, the interval invites reading as an extraordinarily precise null.

### c. The exposure sensitivity is omitted from the headline summary, and it is the one place a conclusion changes

Protocol §8.3 requires the exposure sensitivity to report "changes in headline estimates". The results exist in `replacement_delta_results.csv` and the counts in `qa_summary.csv`/`denominator_audit.csv`, but §4 of `headline_summary.md` lists only baseline, broad and strict.

Dropping the single exposure-flagged project moves Equity `delta_min` from −0.0814, CI [−0.2020, **−0.0065**] to −0.0683, CI [−0.1875, **+0.0031**] — i.e. the CI crosses zero and the §10.2 "stronger signal" trigger would not fire.

To be fair to the analysis: this is **not** something special about the exposure record. Leave-one-out shows it is tied 1st–5th of 150 for influence (Δ +0.0131), one of 7 baseline records where the model tags equity and no coder does. The honest reading is that the Equity result is marginal and n-fragile at 19 model-positives, not that the exposure case is driving it. Equity's own human-majority support is 11 records — also inside the protocol's 10–29 low-support band.

### d. Review notebook is unexecuted

All 12 code cells have `execution_count: null` and no stored outputs, so the notebook does not itself evidence the results; it must be run. Its internal cross-checks are sound when run (cell 12 independently re-derives the CIs via pandas `linear` quantiles and asserts against the reported values).

### e. Latent robustness, not triggered here

`taxonomy.py:68` would raise `TypeError` if a Partial/No Fit response ever had unparseable issue checkboxes (`taxonomy_issues=None`); `agreement.py:126` uses `int(0.9 * attempts)`, which floors and only coincides with the protocol's 90% rule because `attempts` is exactly 2000.

Neither affects this run.

### f. `baseline_structural_sensitivity` is vacuous

`baseline_structural_sensitivity` is vacuous (0 invalid responses), so it duplicates `baseline` exactly. Correct per §8.10 ¶168, just non-informative.

## 4. Independent checks performed

| Check | Result |
|---|---|
| Frozen export SHA-256 | Matches `2980934…dee0a6` ✓ |
| Panel reconstruction | 675 formal responses (713 raw − 38 `validation_included=0`), 3 coders × 225, 150/75, one response per coder-record, one-to-one Fable 5 join ✓ |
| Alpha/deltas, all 4 dimensions | Recomputed with my **own** MASI + Krippendorff (exact `Fraction` arithmetic, brute-force ordered pairs). All 4 headline rows reproduce to 3 dp ✓ |
| Bootstrap, all 6 populations × 4 dimensions | Re-implemented independently (seed 20260714, 2000 draws, own Type-7 percentile). **All 24 `delta_min` point estimates and CIs reproduce** ✓ |
| Purpose Δmin | −0.0427, CI [−0.0903, −0.0021] ✓ |
| Equity Δmin | −0.0814, CI [−0.2020, −0.0065] ✓ |
| Strict-sufficient Purpose Δmin | +0.0136 ✓ |
| COVID Δmin CI | [0.000, 0.000] ✓ (mechanism explained in 3b) |
| Broad / strict subsets | 148/150 and 92/150 ✓; strict count reconciles with the 92 majority-Sufficient records |
| Taxonomy-issue denominator | 84 Partial + 4 No Fit = **88** baseline responses ✓ (hard case 54+2=56) |
| Checkbox gateway | Every `fit∈{2,3}` response has ≥1 issue ticked; **every** `fit∈{1,4}` response has all issue boxes `0` and is correctly excluded. Zero leakage of undisplayed zeros ✓ |
| Zero retention | `keep_default_na=False`, `dtype=str`; no blanks in any analysed field; `sc_covid=0`/`sc_equity=0` retained as substantive ✓ |
| Wilson intervals | Both reproduce to 6 dp ✓ |
| Encoded vs canonical alpha | Code asserts equality at 1e-12; I verified the coincidence-form algebra is correct ✓ |
| Joint resampling | All four alphas + three deltas + `delta_min` come from one `indices` draw; duplicates retained via fancy indexing. Seed reuse across dimensions is benign — panel ordering is identical, so it acts as common random numbers on the same records ✓ |
| Undefined replicates | Only hard-case COVID (1998/2000 valid); ≥1800 threshold correct, counts reported ✓ |
| Trigger logic | All 4 rows verified against §10.2 ✓ |
| Masking | Scanned every output file against the real 225-ID set — **no** source Record ID or title present ✓ |
| Test suite | `tests/test_scratch_coder_stage_a.py` — 16 passed ✓ |

Protocol concordance was checked line-by-line against §8.1–8.10 and §10.2. Complete-case rule (¶116), broad/strict definitions (¶132), split-judgement rule (¶143), Cannot-assess exclusion from issue denominators (¶142), Unclear-as-ordinary-label (¶121), nominal distance for tags (¶130), joint recalculation (¶161), and the 90%/valid-count rule (¶162) are all implemented exactly as written.

## 5. Results that should be manually rechecked

1. **COVID row** — confirm the intended presentation of a [0.000, 0.000] interval, and add the §8.8 low-prevalence caution. Worth stating in text that `Δ_A` is identically zero by construction.
2. **Equity trigger (§10.2 "stronger signal")** — the CI upper bound is −0.0065. Given 19 model-positives and the sensitivity result, consider whether this meets §10.2's bar or falls under ¶208's "inconclusive" framing.
3. **Exposure sensitivity rows** — should appear in the headline summary per §8.3.

Not examined, per your constraints: the record-level disagreement/adjudication population, and Stage B per-label metrics (§8.4/8.8). I also took POST-009/POST-011 sample membership as given from the hash-verified manifest rather than re-deriving the draw from `SEED_DRAW`.

## 6. Statement

**No material problems were found.** The Stage A implementation is a faithful and unusually careful implementation of the preregistered analysis — the hash-pinning of authorities, the canonical-vs-encoded alpha cross-assertion, the explicit checkbox gating, and the write-time masking scan are all above the standard I'd expect. Every reported headline figure is arithmetically correct and independently reproducible. The issues above concern presentation and protocol-required caveating, not computation.

No files were modified, created, deleted, staged or committed.