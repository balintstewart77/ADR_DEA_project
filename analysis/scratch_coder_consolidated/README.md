# Scratch-coder consolidated results

From the repository root, run:

```sh
.venv/bin/python -B -m analysis.scratch_coder_consolidated
```

This ordinary invocation regenerates the Wilson-enriched canonical pair at:

- `analysis/scratch_coder_results/results.md`
- `analysis/scratch_coder_results/run_metadata.json`

It uses the retained approved supplement at
`analysis/outputs_validation_wilson_baseline_20260907T142427225531Z/` by
default. An unsupplemented report cannot replace the canonical pair; it is available only
as an explicit temporary audit render:

```sh
.venv/bin/python -B -m analysis.scratch_coder_consolidated \
  --without-wilson-supplement --staging-output <new-directory-below-the-system-temp-directory>
```

Python 3.10+ and PyYAML are required; the existing project environment supplies them.
The generator imports no analysis modules and reads no replicate draws or owner inputs.
It reads the three fixed scratch-coder output directories plus explicitly named public
configuration, saved methods, frozen dictionary/protocol/instrument and release provenance.
Configuration is parsed with `ast.literal_eval`; the analysis code is read as text only.

`schemas.json` records the actual inspected CSV headers. `preflight.py` defines explicit
stage selection, source keys, aliases, independently specified coverage, support joins
and compatibility checks. `report.py` creates long-form metric/status items and renders
the requested sections, building and checking the tag section first. All source CSV values
remain strings. The adapter copies the already-calculated approved Wilson supplement; the
consolidation generator does not recalculate intervals, percentages, deltas or flags.
The support-band consistency check is a presentation-policy check against exported support.

Generation occurs in a temporary staging directory. Both files are parsed, hashed and
validated before the stable pair is replaced; a generation or validation failure leaves
the prior canonical pair intact. The metadata contains adapters, coverage, hashes, all
cell lineage, unresolved items, supplement provenance and validation results. The source
directory names are fixed deliberately; unsupported schemas and missing expected rows fail
rather than being guessed. The generator never removes analytical source directories.

Rare support withholds only domain/purpose per-label kappa, precision, recall and F1.
Tags retain their full exported diagnostic set. Baseline-defined support bands stay
explicitly baseline-scoped on hard-case rows, alongside the hard-case support count.
Unavailable sensitivity/subset tag support is disclosed. Tag stratum coverage is
explicitly recorded as intentional non-applicability. Missing historical code snapshots
and unexported interval annotations cause an INCOMPLETE report, not invented metadata.

Run the targeted structural/presentation checks without caches or test artifacts:

```sh
.venv/bin/python -B -m unittest analysis.scratch_coder_consolidated.test_collation
```

These checks operate on summaries and in-memory copies only. They do not run or validate
the statistical analyses. All task edits belong in this package; never edit source outputs
or any source stage's `report.py` to resolve a collation failure.

The historical Task A/Task B comparison helper is retained under
`analysis/scratch_coder_consolidation_followup/`. Its original timestamped inputs are no
longer live defaults: rerunning that one-off audit requires explicitly supplied restored
historical directories. Normal canonical regeneration does not depend on those deleted runs.
