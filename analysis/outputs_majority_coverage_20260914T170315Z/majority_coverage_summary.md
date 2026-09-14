# Per-record labelwise-majority coverage and composition

Descriptive bookkeeping over the existing labelwise majority rule. These aggregate counts do not make an accuracy, reliability, quality, coherence, or record-level-adjudication claim.

## Rule and cohort

The reused implementation is `analysis/scratch_coder_stage_b/performance.py`, function `vectors(b, dim, label)`. For each label it forms the three-human membership vector and returns `(humans.sum(1) >= 2)` as the labelwise majority reference. No majority rule was added or modified.

The mask was reconstructed, not recovered from a stored record-level artefact: `analysis.scratch_coder_stage_a.panels.dimension_panels()` rebuilt the formal C01/C02/C03 record panels from the hash-verified POST-028/POST-009/POST-011/POST-019 inputs. A record entered a dimension/population denominator only when all three complete human values and the frozen model value were present, matching the replacement-panel complete-case condition. Formal responses require `validation_included=1`.

Analytical Purposes has a single-coder constraint of at most two labels, documented in `analysis/scratch_coder_stage_a/mappings.py` (`sc_purposes___1..8`: ‘At most two; Unclear mutually exclusive’). The labelwise majority itself is not capped. No cardinality constraint is documented in that mapping for Research Domains, so no Domain violation count is reported.

## Baseline

### Research Domains

Majority-set size distribution:

| Size | Count | Denominator |
| --- | --- | --- |
| 0 | 5 | 150 |
| 1 | 120 | 150 |
| 2 | 22 | 150 |
| 3 | 3 | 150 |
| 4+ | 0 | 150 |

No majority label: **5 / 150**.

Unclear composition (descriptive only):

| Unclear | At least one substantive label | Count | Denominator |
| --- | --- | --- | --- |
| absent | absent | 5 | 150 |
| absent | present | 132 | 150 |
| present | absent | 13 | 150 |
| present | present | 0 | 150 |
### Analytical Purposes

Majority-set size distribution:

| Size | Count | Denominator |
| --- | --- | --- |
| 0 | 24 | 150 |
| 1 | 123 | 150 |
| 2 | 3 | 150 |
| 3 | 0 | 150 |
| 4+ | 0 | 150 |

No majority label: **24 / 150**.

Unclear composition (descriptive only):

| Unclear | At least one substantive label | Count | Denominator |
| --- | --- | --- | --- |
| absent | absent | 24 | 150 |
| absent | present | 100 | 150 |
| present | absent | 26 | 150 |
| present | present | 0 | 150 |

Majority sets exceeding the single-coder limit of two: **0 / 150**.

### Aggregate exclusions by reason

| Dimension | Reason | Count | Population membership |
| --- | --- | --- | --- |
| Research Domains | missing_formal_record_panel | 0 | 150 |
| Research Domains | incomplete_or_missing_dimension_response | 0 | 150 |
| Research Domains | missing_model_classification | 0 | 150 |
| Analytical Purposes | missing_formal_record_panel | 0 | 150 |
| Analytical Purposes | incomplete_or_missing_dimension_response | 0 | 150 |
| Analytical Purposes | missing_model_classification | 0 | 150 |

## Hard-case — DIAGNOSTIC — non-representative

### Research Domains

Majority-set size distribution:

| Size | Count | Denominator |
| --- | --- | --- |
| 0 | 6 | 75 |
| 1 | 48 | 75 |
| 2 | 18 | 75 |
| 3 | 3 | 75 |
| 4+ | 0 | 75 |

No majority label: **6 / 75**.

Unclear composition (descriptive only):

| Unclear | At least one substantive label | Count | Denominator |
| --- | --- | --- | --- |
| absent | absent | 6 | 75 |
| absent | present | 66 | 75 |
| present | absent | 3 | 75 |
| present | present | 0 | 75 |
### Analytical Purposes

Majority-set size distribution:

| Size | Count | Denominator |
| --- | --- | --- |
| 0 | 9 | 75 |
| 1 | 62 | 75 |
| 2 | 4 | 75 |
| 3 | 0 | 75 |
| 4+ | 0 | 75 |

No majority label: **9 / 75**.

Unclear composition (descriptive only):

| Unclear | At least one substantive label | Count | Denominator |
| --- | --- | --- | --- |
| absent | absent | 9 | 75 |
| absent | present | 46 | 75 |
| present | absent | 20 | 75 |
| present | present | 0 | 75 |

Majority sets exceeding the single-coder limit of two: **0 / 75**.

### Aggregate exclusions by reason

| Dimension | Reason | Count | Population membership |
| --- | --- | --- | --- |
| Research Domains | missing_formal_record_panel | 0 | 75 |
| Research Domains | incomplete_or_missing_dimension_response | 0 | 75 |
| Research Domains | missing_model_classification | 0 | 75 |
| Analytical Purposes | missing_formal_record_panel | 0 | 75 |
| Analytical Purposes | incomplete_or_missing_dimension_response | 0 | 75 |
| Analytical Purposes | missing_model_classification | 0 | 75 |

## Baseline per-label reconciliation

Each derived baseline label count matched the `baseline_human_majority_positive_n` source cell in `results.md` S5T001/S5T002.

| Dimension | Label | Derived | S5 exported | Result |
| --- | --- | --- | --- | --- |
| Research Domains | Business & Productivity | 41 | 41 | match |
| Research Domains | Crime & Justice | 4 | 4 | match |
| Research Domains | Data Infrastructure & Methodology | 0 | 0 | match |
| Research Domains | Education & Skills | 27 | 27 | match |
| Research Domains | Environment & Agriculture | 4 | 4 | match |
| Research Domains | Health & Social Care | 23 | 23 | match |
| Research Domains | Housing & Planning | 0 | 0 | match |
| Research Domains | Labour Market & Employment | 39 | 39 | match |
| Research Domains | Migration & Demographics | 9 | 9 | match |
| Research Domains | Poverty, Wealth & Living Standards | 11 | 11 | match |
| Research Domains | Public Finance & Taxation | 2 | 2 | match |
| Research Domains | Unclear from Register Entry | 13 | 13 | match |
| Analytical Purposes | Descriptive Monitoring | 36 | 36 | match |
| Analytical Purposes | Life-Course / Trajectory Analysis | 9 | 9 | match |
| Analytical Purposes | Methodological / Infrastructure Research | 7 | 7 | match |
| Analytical Purposes | Outcome Tracking | 19 | 19 | match |
| Analytical Purposes | Policy Evaluation / Impact Analysis | 30 | 30 | match |
| Analytical Purposes | Risk Prediction / Early Identification | 1 | 1 | match |
| Analytical Purposes | Service Interaction / Systems Analysis | 1 | 1 | match |
| Analytical Purposes | Unclear from Register Entry | 26 | 26 | match |

## Output boundary

No record identifiers, membership lists, individual responses, or per-record label sets are written in this directory. The frozen restricted files were read after hash verification and were not copied.
