# Confirmatory analysis

This folder contains version-controlled schemas, ten blank output shells, the
v0.15 read-only analysis-preflight scaffold and a direct-runtime dependency record. It
contains no formal data, sample identity, empirical result, completed adjudication,
or release decision.

The tested foundations in `analysis/validation/` cover raw-code parsing,
exact-set/Jaccard/MASI measures, Krippendorff alpha, replacement panels,
register-sufficiency subsets, labelwise support, owner denominators, source-masked
adjudication, Wilson intervals, 2,000-project-block bootstrap mechanics and blank
output validation. Percentile calculations use Hyndman–Fan Type 7, equivalent to
NumPy/Pandas linear interpolation.

`run_validation_analysis.py --check` validates the v0.15 protocol metadata,
candidate-0.7 150-field frozen dictionary, sampling gate, output schemas,
dependency lock, Type-7 bootstrap contract and matched-panel sensitivity contract.
Formal execution is not implemented in this preregistration scaffold; `--run`
fails explicitly without reading formal data. The final executable orchestration
will be completed and verified before analysis lock without changing the
preregistered rules. The scaffold has no network, API, LLM, REDCap, sampling,
RNG, or assignment-import behaviour and never substitutes synthetic data.

The instrument-validity sensitivity uses the frozen candidate-0.7 validator as
authoritative. The primary analysis retains affected responses
exactly as recorded; the sensitivity excludes every project containing an affected
human response so matched panels remain complete. Project-owner analysis is
separate. `protocol_analysis_traceability.csv` records the implemented foundation
and remaining prospective empirical reporting work. Classifying this file as a
supporting preflight scaffold resolves the earlier readiness-audit option without
pretending that a complete executable pipeline is frozen. Analysis begins only
after the registered protocol, later gates, and the separately verified executable
orchestration permit it.
