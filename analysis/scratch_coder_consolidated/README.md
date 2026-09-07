# Scratch-coder consolidated results

From the repository root, run:

```sh
.venv/bin/python -B -m analysis.scratch_coder_consolidated
```

Python 3.10+ and PyYAML are required; the existing project environment supplies them.
The generator imports no analysis modules and reads no replicate draws or owner inputs.
It reads the three fixed scratch-coder output directories plus explicitly named public
configuration, saved methods, frozen dictionary/protocol/instrument and release provenance.
Configuration is parsed with `ast.literal_eval`; the analysis code is read as text only.

`schemas.json` records the actual inspected CSV headers. `preflight.py` defines explicit
stage selection, source keys, aliases, independently specified coverage, support joins
and compatibility checks. `report.py` creates long-form metric/status items and renders
the requested sections, building and checking the tag section first. All CSV values
remain strings. No analytical statistics, percentages, deltas or flags are recomputed.
The support-band consistency check is a presentation-policy check against exported support.

Each run exclusively creates `analysis/outputs_validation_consolidated_<UTC timestamp>/`.
A successful run contains only `consolidated_results.md` and `run_metadata.json`.
The latter contains adapters, coverage, hashes, all cell lineage, unresolved items and
validation results. The source directory names are fixed deliberately; unsupported
schemas and missing expected rows fail rather than being guessed. A fatal run writes
failed metadata without a results document. No output directory is reused.

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
