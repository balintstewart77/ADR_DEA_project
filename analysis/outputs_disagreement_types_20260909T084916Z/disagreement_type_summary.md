# Descriptive distribution of scratch-coder/model disagreement types

Generated: `2026-09-09T08:49:22.249523+00:00`

This is a newly calculated descriptive supplement from frozen coded data. It reports set-relation counts and two specified pair-weighted conditional distributions only. It does not calculate an agreement coefficient, a distance score, an inferential interval, or the effect of an alternative distance on alpha.

## Scope and frozen inputs

The formal panel uses C01, C02 and C03, the 150-record random baseline (POST-009), the separate 75-record hard-case sample (POST-011), resolved assignments from POST-019, and the frozen Fable 5 production classifications (MOD-006). Research Domains and Analytical Purposes use the dimension-specific common complete-case rule from the saved Stage A replacement-panel methods. The joint cross-cutting tag set uses the intersection of the separate equity-tag and COVID-tag panel masks.

| Role | Identity | Source |
|---|---|---|
| Scratch-coder responses | POST-028 | `preregistration_restricted/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv` |
| Baseline membership | POST-009 | `preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv` |
| Hard-case membership | POST-011 | `preregistration_restricted/sampling/official_draw_20260724/hard_active.csv` |
| Resolved formal assignments | POST-019 | `preregistration_restricted/sampling/official_draw_20260724/formal_assignment_crosswalk.csv` |
| Production model classifications | MOD-006, Fable 5 | `analysis/outputs_classified_20260702_fable5/layer_classifications.csv` |
| Frozen taxonomy | MOD-001, dict-1.0-rc2 | `taxonomy_data_dictionary.yaml` |
| Frozen instrument dictionary | RED-036, candidate-0.7 | `preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv` |

POST-028 was read under the 9 September 2026 named-file amendment. The original categorical restricted-path prohibition conflicted with the record-level data requirement; the amendment permits this one hash-verified input and the exact POST-009/011/019 authorities without relaxing access to other restricted content.

## Parsing and cohort rules

Domain and purpose responses are decoded from their explicit REDCap checkbox columns using the frozen RED-036 choice mapping. Checkbox `0` means known unselected, not missing. Tags use `sc_equity` and `sc_covid`, where `0` is known absent and `1` is present; two known-absent tags therefore form a valid empty joint set. The model fields use the saved semicolon-only codec: split on `;`, trim delimiter-adjacent whitespace, discard blank delimiter fragments, preserve spelling/case, and deduplicate only through set construction. No duplicate model tokens occurred. All decoded labels were checked against MOD-001; `Unclear from Register Entry` remains an ordinary dimension-specific label.

An empty decoded set is distinct from a missing or invalid observation. Missing observations are not classified. Formal rows require `validation_included=1`; assignment, reviewer and source-record identities match POST-019 one-to-one; and each retained record has one complete response from each of C01/C02/C03 plus a model observation. The primary masks retain exposure flags and structurally invalid responses under the saved Stage A rule; the frozen data reproduce zero structurally invalid formal responses. One exposure-flagged response remains in the baseline primary cohort, as in Stage A.

The canonical record unit is `source_record_id`; `assignment_id` resolves submissions through POST-019 but is not treated as the record unit. Human–human and model–human families use exactly the same eligible records within each population/dimension. Each retained record contributes three unordered human pairs and three model–human pairs. Pair records are descriptive units and are not treated as independent observations for inference.

## Relation definitions

The ordered checks are: both sets empty (`both_empty`); exactly one empty (`exactly_one_empty`); equal nonempty sets (`identical`); proper-subset relation (`containment`); nonempty intersection without containment (`overlap`); and disjoint nonempty sets (`disjoint`). These categories are mutually exclusive and exhaustive for two available sets. `both_empty` is identical assignment, not disagreement.

The first proportion conditions on non-identical pairs with both sets nonempty (containment + overlap + disjoint). The second conditions on all non-identical pairs (those three categories + exactly one empty). `empty_set_involved_pairs` is the combined `both_empty` + `exactly_one_empty` count, not a seventh category. CSV proportions retain up to 17 significant digits; the tables below display four decimal places.

The joint-tag view is supplementary to the existing separate binary-tag analyses and does not replace or reinterpret them. With exactly two possible tag labels, two nonempty sets cannot overlap without one containing the other unless they are equal; joint-tag `overlap` is therefore a structural zero and is retained as a row.

## Distributions

### Random baseline

#### Research Domains — human_human

Eligible records: 150; classified pair units: 450; non-identical/nonempty denominator: 220; all-non-identical denominator: 220; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 230 | — (not_applicable) | — (not_applicable) |
| containment | 105 | 0.4773 | 0.4773 |
| overlap | 11 | 0.0500 | 0.0500 |
| disjoint | 104 | 0.4727 | 0.4727 |

#### Research Domains — model_human

Eligible records: 150; classified pair units: 450; non-identical/nonempty denominator: 199; all-non-identical denominator: 199; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 251 | — (not_applicable) | — (not_applicable) |
| containment | 103 | 0.5176 | 0.5176 |
| overlap | 16 | 0.0804 | 0.0804 |
| disjoint | 80 | 0.4020 | 0.4020 |

#### Analytical Purposes — human_human

Eligible records: 150; classified pair units: 450; non-identical/nonempty denominator: 272; all-non-identical denominator: 272; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 178 | — (not_applicable) | — (not_applicable) |
| containment | 38 | 0.1397 | 0.1397 |
| overlap | 1 | 0.0037 | 0.0037 |
| disjoint | 233 | 0.8566 | 0.8566 |

#### Analytical Purposes — model_human

Eligible records: 150; classified pair units: 450; non-identical/nonempty denominator: 270; all-non-identical denominator: 270; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 180 | — (not_applicable) | — (not_applicable) |
| containment | 40 | 0.1481 | 0.1481 |
| overlap | 4 | 0.0148 | 0.0148 |
| disjoint | 226 | 0.8370 | 0.8370 |

#### Joint cross-cutting tag set — human_human

Eligible records: 150; classified pair units: 450; non-identical/nonempty denominator: 7; all-non-identical denominator: 37; empty-set-involved pairs: 395.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 365 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 30 | — (not_applicable) | 0.8108 |
| identical | 48 | — (not_applicable) | — (not_applicable) |
| containment | 6 | 0.8571 | 0.1622 |
| overlap | 0 | 0.0000 | 0.0000 |
| disjoint | 1 | 0.1429 | 0.0270 |

#### Joint cross-cutting tag set — model_human

Eligible records: 150; classified pair units: 450; non-identical/nonempty denominator: 6; all-non-identical denominator: 51; empty-set-involved pairs: 391.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 346 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 45 | — (not_applicable) | 0.8824 |
| identical | 53 | — (not_applicable) | — (not_applicable) |
| containment | 5 | 0.8333 | 0.0980 |
| overlap | 0 | 0.0000 | 0.0000 |
| disjoint | 1 | 0.1667 | 0.0196 |

### Hard-case sample — DIAGNOSTIC — non-representative

All tables in this subsection are **DIAGNOSTIC — non-representative**.

#### Research Domains — human_human — DIAGNOSTIC — non-representative

Eligible records: 75; classified pair units: 225; non-identical/nonempty denominator: 131; all-non-identical denominator: 131; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 94 | — (not_applicable) | — (not_applicable) |
| containment | 67 | 0.5115 | 0.5115 |
| overlap | 9 | 0.0687 | 0.0687 |
| disjoint | 55 | 0.4198 | 0.4198 |

#### Research Domains — model_human — DIAGNOSTIC — non-representative

Eligible records: 75; classified pair units: 225; non-identical/nonempty denominator: 142; all-non-identical denominator: 142; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 83 | — (not_applicable) | — (not_applicable) |
| containment | 77 | 0.5423 | 0.5423 |
| overlap | 20 | 0.1408 | 0.1408 |
| disjoint | 45 | 0.3169 | 0.3169 |

#### Analytical Purposes — human_human — DIAGNOSTIC — non-representative

Eligible records: 75; classified pair units: 225; non-identical/nonempty denominator: 132; all-non-identical denominator: 132; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 93 | — (not_applicable) | — (not_applicable) |
| containment | 12 | 0.0909 | 0.0909 |
| overlap | 0 | 0.0000 | 0.0000 |
| disjoint | 120 | 0.9091 | 0.9091 |

#### Analytical Purposes — model_human — DIAGNOSTIC — non-representative

Eligible records: 75; classified pair units: 225; non-identical/nonempty denominator: 174; all-non-identical denominator: 174; empty-set-involved pairs: 0.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 0 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 0 | — (not_applicable) | 0.0000 |
| identical | 51 | — (not_applicable) | — (not_applicable) |
| containment | 44 | 0.2529 | 0.2529 |
| overlap | 1 | 0.0057 | 0.0057 |
| disjoint | 129 | 0.7414 | 0.7414 |

#### Joint cross-cutting tag set — human_human — DIAGNOSTIC — non-representative

Eligible records: 75; classified pair units: 225; non-identical/nonempty denominator: 2; all-non-identical denominator: 22; empty-set-involved pairs: 193.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 173 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 20 | — (not_applicable) | 0.9091 |
| identical | 30 | — (not_applicable) | — (not_applicable) |
| containment | 2 | 1.0000 | 0.0909 |
| overlap | 0 | 0.0000 | 0.0000 |
| disjoint | 0 | 0.0000 | 0.0000 |

#### Joint cross-cutting tag set — model_human — DIAGNOSTIC — non-representative

Eligible records: 75; classified pair units: 225; non-identical/nonempty denominator: 1; all-non-identical denominator: 25; empty-set-involved pairs: 195.

| Relation | Count | Proportion among non-identical pairs with both sets nonempty | Proportion among all non-identical pairs |
|---|---:|---:|---:|
| both_empty | 171 | — (not_applicable) | — (not_applicable) |
| exactly_one_empty | 24 | — (not_applicable) | 0.9600 |
| identical | 29 | — (not_applicable) | — (not_applicable) |
| containment | 1 | 1.0000 | 0.0400 |
| overlap | 0 | 0.0000 | 0.0000 |
| disjoint | 0 | 0.0000 | 0.0000 |

## Exclusions

No record was excluded: all 150 baseline and 75 hard-case records satisfied each relevant complete-case mask, including the joint-tag intersection. There were no new unresolved data problems.

## Reporting boundary

These counts and proportions do not determine alpha, quantify distance sensitivity, assess whether MASI or Jaccard is preferable, or establish coder/model quality, accuracy or superiority. They do not validate, confirm or undermine the canonical report, and they imply no release, review-trigger or equity/purpose conclusion.
