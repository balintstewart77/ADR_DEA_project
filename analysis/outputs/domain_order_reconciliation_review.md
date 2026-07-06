# DOMAIN_ORDER reconciliation review

Phase 1 diagnosis only. No classifier, reference YAML, deterministic output CSV,
or tests have been changed.

Date: 2026-06-29

## Scope

`DOMAIN_ORDER` in `analysis/derive_register_properties.py` is the deterministic
register layer's component-domain allowed set and output ordering. The
authoritative taxonomy source for Layer A labels is
`taxonomy_data_dictionary.yaml` (`dictionary_version: 1.0-rc2`,
`documents_ontology_version: v3.4-rc2`). The LLM classifier already builds its
offered `substantive_domains` label set from this YAML via `_labels_for_layer`;
this review covers only the deterministic linked-product `component_domains`
vocabulary.

Current deterministic `DOMAIN_ORDER` has 15 labels. Current active taxonomy
Layer A has 12 labels:

- Labour Market & Employment
- Education & Skills
- Health & Social Care
- Crime & Justice
- Business & Productivity
- Poverty, Wealth & Living Standards
- Housing & Planning
- Migration & Demographics
- Environment & Agriculture
- Public Finance & Taxation
- Data Infrastructure & Methodology
- Unclear from Register Entry

## Complete mismatch scan

Labels present in `DOMAIN_ORDER` but not in active taxonomy Layer A:

- COVID-19 & Pandemic
- Income, Poverty & Inequality
- Other / Cross-sector
- Transport & Mobility

Labels present in active taxonomy Layer A but not in `DOMAIN_ORDER`:

- Poverty, Wealth & Living Standards

No other label-set mismatches were found.

## Live component-domain value set

The complete set of values currently used by linked-product
`component_domains` in `analysis/register_reference.yaml` is:

| component_domains value | linked-product count |
|---|---:|
| Business & Productivity | 1 |
| Crime & Justice | 1 |
| Education & Skills | 5 |
| Environment & Agriculture | 1 |
| Health & Social Care | 9 |
| Housing & Planning | 2 |
| Labour Market & Employment | 5 |
| Migration & Demographics | 8 |

No old, removed, or taxonomy-only drift labels are used as component-domain
values in the reference.

## Per-label diagnosis

| Label | In `component_domains` reference? | In live `register_properties.csv` domain field? | In active taxonomy Layer A? | Classification | Directional Phase 2 fix |
|---|---:|---:|---:|---|---|
| Other / Cross-sector | No, exact 0 and normalised/alias spelling 0 | No, `record_linkage_component_domains` 0/1309 | No | Vestige | Remove from deterministic domain vocabulary. No data fix. |
| COVID-19 & Pandemic | No, exact 0 and normalised/alias spelling 0 | No, `record_linkage_component_domains` 0/1309 | No as Layer A; yes as active cross-cutting tag | Vestige in deterministic layer | Remove from deterministic domain vocabulary. No product data correction is needed because no linked product uses COVID as a component domain. |
| Income, Poverty & Inequality | No, exact 0 and normalised/alias spelling 0 | No, `record_linkage_component_domains` 0/1309 | No | Vestige / stale pre-rename label | Replace via taxonomy single-source with `Poverty, Wealth & Living Standards`. No data fix because the old label is not live. |
| Poverty, Wealth & Living Standards | No, exact 0 and normalised/alias spelling 0 | No, `record_linkage_component_domains` 0/1309 | Yes | Taxonomy-only replacement label | Include through the taxonomy-derived deterministic vocabulary. No current output cells gain this label because no component product uses the poverty/wealth domain. |
| Transport & Mobility | No, exact 0 and normalised/alias spelling 0 | No, `record_linkage_component_domains` 0/1309 | No | Additional vestige found by full mismatch scan | Remove from deterministic domain vocabulary. No data fix. |

The specific COVID check is therefore: `COVID-19 & Pandemic` is not live in
`component_domains` or deterministic output. It is a deterministic-layer vestige,
not a current layer-confusion data error.

The specific poverty-label direction is therefore: the reference uses neither
old nor new poverty label. The deterministic constant is stale, and the
authoritative vocabulary should expose the new taxonomy label
`Poverty, Wealth & Living Standards`.

## Expected deterministic-output impact

The label removals/addition above have no direct label-value impact because none
of the drift labels are used in `analysis/register_reference.yaml` or
`analysis/outputs_deterministic_rc2/register_properties.csv`.

However, if Phase 2 uses the taxonomy YAML order directly for
`record_linkage_component_domains` ordering, 119 existing CSV cells are expected
to change by ordering only:

| Count | Current value | Proposed taxonomy-order value |
|---:|---|---|
| 118 | Education & Skills; Labour Market & Employment | Labour Market & Employment; Education & Skills |
| 1 | Education & Skills; Health & Social Care; Labour Market & Employment; Migration & Demographics | Labour Market & Employment; Education & Skills; Health & Social Care; Migration & Demographics |

Affected record IDs for the 118-row order-only change:

`2021/074; 2021/075; 2021/076; 2021/182; 2021/186; 2022/015; 2022/017; 2022/028; 2022/029; 2022/042; 2022/048; 2022/086; 2022/100; 2022/121; 2023/005; 2023/011; 2023/017; 2023/018; 2023/019; 2023/034; 2023/035; 2023/049; 2023/067; 2023/173; 2023/174; 2023/175; 2023/212; 2023/232; 2023/303; 2023/310; 2024/024; 2024/028; 2024/038; 2024/041; 2024/043; 2024/056; 2024/068; 2024/071; 2024/073; 2024/080; 2024/084; 2024/085; 2024/094; 2024/107; 2024/117; 2024/121; 2024/122; 2024/123; 2024/136; 2024/137; 2024/143; 2024/147; 2024/148; 2024/149; 2024/152; 2024/154; 2024/155; 2024/157; 2024/165; 2024/176; 2024/178; 2024/185; 2024/196; 2024/198; 2024/200; 2024/204; 2024/212; 2024/220; 2024/259; 2025/008; 2025/013; 2025/016; 2025/026; 2025/030; 2025/036; 2025/037; 2025/041; 2025/046; 2025/049; 2025/057; 2025/064; 2025/070; 2025/099; 2025/108; 2025/119; 2025/120; 2025/122; 2025/127; 2025/132; 2025/133; 2025/134; 2025/135; 2025/156; 2025/161; 2025/167; 2025/169; 2025/174; 2025/176; 2025/190; 2025/197; 2025/198; 2025/208; 2025/214; 2025/231; 2025/235; 2025/243; 2025/249; 2025/250; 2025/259; 2026/015; 2026/021; 2026/025; 2026/026; 2026/028; 2026/034; 2026/035; 2026/074; 2026/087`

Affected record ID for the one 4-domain order-only change:

`2025/225`

Expected non-changes:

- `record_linkage`: no expected changes.
- `matched_products`: no expected changes.
- `dataset_collection_methods`, `dataset_temporal_structures`, `dataset_units`,
  `researcher_sectors`: no expected changes.
- `reference_version`: no expected bump unless Phase 2 chooses to edit
  `analysis/register_reference.yaml`; this diagnosis found no required live data
  edits.
- Frozen LLM/classification outputs: no expected changes and should not be
  touched.

Current deterministic linkage counts are:

- Cross-domain record linkage: 279
- Within-domain record linkage: 91
- No record linkage: 939

These counts are expected to remain unchanged. The requested dashboard headline
`279/91/28.3%` should therefore remain unchanged as well.

## Phase 2 proposal

Preferred structural fix: dynamically derive the deterministic component-domain
allowed set and ordering from `taxonomy_data_dictionary.yaml`, using the same
active Layer A filter as the LLM classifier and dashboard taxonomy reader:

- `layer == "Layer A -- domain"`
- `include_in_prompt is True`
- `status` does not start with `removed`

This removes the second hard-coded vocabulary copy and prevents recurrence of
this drift class. It will make the deterministic layer validate against the
same offered domain set as the classifier.

Because dynamic taxonomy order changes 119 output cells by ordering only, Phase 2
must treat exactly those `record_linkage_component_domains` cells as the
predicted idempotency exception and stop if any other deterministic cell moves.

If zero deterministic CSV diff is preferred instead, the fallback would be to
keep an explicit deterministic order list and add an equivalence test against
the taxonomy Layer A set. That is weaker because ordering can still be a second
policy choice. The preferred dynamic approach is feasible and should be used
unless Balint rejects the 119 order-only output changes.

## Phase 2 test additions

Add a test asserting that the deterministic component-domain vocabulary equals
the active taxonomy Layer A label set. The test comment should name this incident:
`Other / Cross-sector`, `COVID-19 & Pandemic`, and
`Income, Poverty & Inequality` drifted from `dict-1.0-rc2`.

No COVID or poverty live-data pin is required from this review because neither
label is currently live in `component_domains` or deterministic output. The
general vocabulary-equivalence test should catch future reintroduction.
