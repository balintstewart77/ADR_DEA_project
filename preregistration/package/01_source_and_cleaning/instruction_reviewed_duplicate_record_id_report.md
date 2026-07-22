# Reviewed duplicate-Project-ID migration report

## Rulings applied

Reviewed rulings are versioned in `analysis/register_duplicate_rulings.yaml`.

| Project ID | Ruling type | Result |
|---|---|---|
| `2020/030` | `project_number_collision` | Retained as `2020/030/a` and `2020/030/b`. |
| `2022/036` | `project_number_collision` | Retained as `2022/036/a` and `2022/036/b`. |
| `2023/211` | `duplicate_update` | Collapsed to one canonical `2023/211` record. |
| `2024/014` | `related_distinct_entries_same_project_id` | Retained as `2024/014/a` and `2024/014/b`; not asserted to be separate projects. |
| `2024/095` | `project_number_collision` | Retained as `2024/095/a` and `2024/095/b`. |

## Counts

| Measure | Before | After |
|---|---:|---:|
| Current cleaned register rows / retained classification units | 1,309 | 1,308 |
| Unique official Project IDs | 1,304 | 1,304 |
| Active Fable classification rows | 1,309 | 1,308 |
| Deterministic register-property rows | 1,309 | 1,308 |
| GPT-5.5 classification rows | 1,309 | 1,308 |
| Cross-model comparison rows | 1,309 | 1,308 |
| Domain/purpose disagreement stratum | 387 | 386 |

Regenerated pre-exclusion disagreement counts:

| Stratum | Count |
|---|---:|
| Research Domain-only | 186 |
| Analytical Purpose-only | 143 |
| Both dimensions | 57 |
| Tag-only supplement | 37 |

The 22-record training/pilot exclusion list was not present in this checkout under the searched names (`trainer`, `training`, `pilot`, `prereg`, `protocol`, `redcap`, `assignment`, `sample`), so post-exclusion counts were not recomputed here.

## Record ID migration

`2023/211/b` was migrated to unsuffixed `2023/211` because it matched the canonical title and exact prompt fingerprint. `2023/211/a` was removed as the malformed duplicate/update row. Retained duplicate Project IDs kept their explicit ruling-file mappings:

| Title | Record ID |
|---|---|
| Examining the relationship between engaging in design and exporting | `2020/030/a` |
| Occupational mobility: evidence from England and Wales | `2020/030/b` |
| Assessing and evaluating the real extent of hidden crimes in the UK | `2022/036/a` |
| Understanding Job Creation in Northern Ireland Firms | `2022/036/b` |
| Public services and youth crime (previously 'Gangs and social housing') | `2024/014/a` |
| The impact of youth centres on crime | `2024/014/b` |
| Diversity and the performance of UK firms and cities | `2024/095/a` |
| Understanding pathways for support amongst children and young people in Wales experiencing mental health problems | `2024/095/b` |

Full migration audit: `analysis/outputs/reviewed_duplicate_record_id_migration_audit.csv`.

## Outputs regenerated or migrated

- Cleaning implementation and duplicate-ruling audit.
- Active Fable release cache and CSV outputs in `analysis/outputs_classified_20260702_fable5/`.
- GPT-5.5 cache and regenerated `gpt55_classifications.csv`.
- Cross-model comparison and disagreement stratum.
- Deterministic register properties in `analysis/outputs_deterministic_rc2/register_properties.csv`.
- Dashboard count-unit handling for dataset and institution views.
- About/README/methods text for the corrected unit of analysis.

No LLM calls were made. Cached classifications were reused by exact prompt fingerprint.

## Verification

- `python -m unittest discover analysis` -> 178 tests, OK.
- `python -m py_compile ...` over edited Python modules -> OK.
- Active artifact check: no `2023/211/a` or `2023/211/b` remains in the active Fable release, deterministic properties, GPT-5.5 outputs, cross-model outputs, or GPT cache.
