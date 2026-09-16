# Exploratory confidence analysis

The original addendum and separate erratum precede code and outputs in history. Shared response loading, membership, majority rules, α, bootstrap and Wilson code are reused without changes. Only the ordinal-distance calculation is new estimator logic.

Validation uses published and synthetic data only:

```powershell
python -m analysis.confidence_exploratory.validate --output analysis/confidence_exploratory/validation_record.json
python -m unittest analysis.confidence_exploratory.test_run
```

The optional independent route uses krippendorff==0.8.2, installed with `python -m pip install --no-deps krippendorff==0.8.2` into the existing project venv. No project dependency file is changed. Published data and expected α are cited in validate.py. Environmental problems are classified as not run under instruction v5.1; numerical mismatches remain failures.

After committing code and validation evidence, execute once from a clean tree:

```powershell
python -m analysis.confidence_exploratory.run
```

The runner completes Group 1 before exploratory calculations, then Group 2 before writing any result file. It refuses existing outputs. A code defect at D–F requires a new code commit after applicable validation and a complete restart at D, retaining no results from the prior execution. The output commit hash is reported externally, never embedded in that commit.

SCF1T001–SCF1T005 are baseline per-coder distributions, majority distributions, ordinal α, unanimous count, and confidence × sufficiency. SCF1T006–SCF1T010 repeat those dimensions for hard-case, each carrying DIAGNOSTIC — non-representative. CSVs retain full float precision; no restricted record IDs are written.
