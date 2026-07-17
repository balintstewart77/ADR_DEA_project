# Confirmatory analysis

This folder contains the version-controlled schemas and blank output shells for
the prospective validation analysis. It must not contain generated results,
exploratory output, real REDCap exports, pilot responses, active or reserve
sample identities, or changes to the existing dashboard analysis.

Batch 1 foundations are implemented in `analysis/validation/` and tested only
with `SYN-*` fixtures. They cover the immutable project-rating model, raw-code
wide-export parsing, exact-set/Jaccard/MASI primitives, transparent
Krippendorff alpha, replacement panels, register-sufficiency subsets,
labelwise majority support, project-level bootstrap mechanics, Wilson
intervals, and output-shell validation. They do not implement empirical
analysis, adjudication, release decisions, owner recruitment, or official
sampling.

`protocol_analysis_traceability.csv` maps every requirement in protocol
Sections 8.1-8.8 to the current foundation, test, output shell, explicit
deferral, or unresolved ambiguity. The ten result CSVs are header-only and
`figure_output_manifest.csv` describes intended figures without generating
empty plots.

These foundations are not the final frozen analysis program or dependency
lock. Full per-label/tag reporting, owner summaries, adjudication and release
logic remain deferred. Code and dependencies are frozen only at registration;
results are post-registration and analysis begins only after Gate 3.
