# Quantitative-claims inventory of the working logs

This report was generated in one complete execution from the two external logs pinned below. It contains no quoted log prose.

## Provenance

| Log | Full path | SHA-256 | Size (bytes) | Last modified (UTC) |
| --- | --- | --- | ---: | --- |
| scratch_coder_figure_revisions_log_pass2.md | `C:\Users\balin\Desktop\DEA_working_logs\scratch_coder_figure_revisions_log_pass2.md` | `0711ff9b7e8808dd202d2302738c343d639d50c3c1fb46f6e43891b5e392924f` | 66449 | 2026-09-16T11:42:25.255393+00:00 |
| scratch_coder_interpretive_findings.md | `C:\Users\balin\Desktop\DEA_working_logs\scratch_coder_interpretive_findings.md` | `5051db037e50417a53a168b62dfda6e466dce333e1706aae453a9e250774610e` | 16322 | 2026-09-16T11:45:18.974435+00:00 |

Repository source: `analysis/scratch_coder_results/results.md`. Exploratory confidence source: `analysis/confidence_exploratory/results_confidence.md`, last commit `f36d738560bb7a2e1c5be68777851778c85b04d5`.

## Counts

| Log | Claims | PASS | PASS (APPROXIMATE) | FAIL | DISCREPANCY | SOURCE MISSING | NOT CHECKED |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| scratch_coder_figure_revisions_log_pass2.md | 224 | 221 | 1 | 0 | 0 | 0 | 2 |
| scratch_coder_interpretive_findings.md | 117 | 116 | 1 | 0 | 0 | 0 | 0 |
| Total | 341 | 337 | 2 | 0 | 0 | 0 | 2 |

## Non-PASS claims

| Claim | Log | Section | Quantity | Quoted value(s) | Source value(s) | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R220 | scratch_coder_figure_revisions_log_pass2.md | O.1 | post-exclusion accompanying tag-disagreement frame counts | ["11", "12", "37"] |  | NOT CHECKED | Stated source is a record-level cross-model comparison; opening it is forbidden for this run. |
| R222 | scratch_coder_figure_revisions_log_pass2.md | O.5 | eligible purpose and domain label counts | ["4", "6"] |  | NOT CHECKED | Counts are not exported as source cells and counting eligibility flags is not an approved derivation. |

## Judgement calls

- Each interval, range, related tuple, table cell n (%), or explicitly related count set is one claim; repeated occurrences remain separate claims.
- Dates, hashes, commit identifiers, section/figure/table numbers, axis ranges, thresholds, seeds, replicate settings, fonts, layout dimensions and Codex-check expectations were excluded.
- A denominator was included when it forms part of a source result or quoted fraction; design-only population labels were excluded unless the log used n quantitatively.
- Qualitative sign/crossing statements and component-name matches were not separate numeric claims when their numerical operands were inventoried in the same section.
- Approximate wording is used only for the 1.4 bound gap and the corrected F.8 ellipsis; half-up rounding at stated precision determines status.
- The O.1 frame counts are NOT CHECKED because their stated source is record-level and forbidden; O.5 eligibility totals are NOT CHECKED because no single source cell exports them and the derivation is not approved.
- Confidence claims use the committed Markdown cells at f36d738; design bootstrap settings in that report are excluded.
- The manifest was reviewed section by section against every number-bearing line in both pinned logs; sections containing only excluded numbers intentionally have zero inventory rows.

## Source and comparison record

The CSV is the authoritative claim-level record. It lists each claim's numbers, source table and cell, full-precision source values, rule and status. No external-log prose is reproduced.
