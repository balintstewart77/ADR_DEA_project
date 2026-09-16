# Per-label contingencies and model performance — Research Domains (baseline n=150 records).

| Label | Support n | TP | FP | FN | TN | Precision | Recall | F1 | Band |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Business & Productivity | 41 | 40 | 5 | 1 | 104 | 0.889 [0.787, 0.975] 95% | 0.976 [0.917, 1.000] 95% | 0.930 [0.864, 0.978] 95% | STANDARD |
| Labour Market & Employment | 39 | 35 | 21 | 4 | 90 | 0.625 [0.492, 0.750] 95% | 0.897 [0.791, 0.976] 95% | 0.737 [0.627, 0.830] 95% | STANDARD |
| Education & Skills | 27 | 26 | 9 | 1 | 114 | 0.743 [0.590, 0.885] 95% | 0.963 [0.880, 1.000] 95% | 0.839 [0.723, 0.923] 95% | LOW SUPPORT |
| Health & Social Care | 23 | 22 | 3 | 1 | 124 | 0.880 [0.731, 1.000] 95% | 0.957 [0.852, 1.000] 95% | 0.917 [0.818, 0.982] 95% | LOW SUPPORT |
| Unclear from Register Entry | 13 | 1 | 0 | 12 | 137 | 1.000 SV | 0.077 [0.000, 0.250] 95% | 0.143 SV | LOW SUPPORT |
| Poverty, Wealth & Living Standards | 11 | 6 | 4 | 5 | 135 | 0.600 [0.250, 0.900] 95% | 0.545 [0.231, 0.857] 95% | 0.571 [0.272, 0.800] 95% | LOW SUPPORT |
| Migration & Demographics | 9 | 4 | 2 | 5 | 139 | Withheld | Withheld | Withheld | RARE |
| Crime & Justice | 4 | 4 | 0 | 0 | 146 | Withheld | Withheld | Withheld | RARE |
| Environment & Agriculture | 4 | 4 | 6 | 0 | 140 | Withheld | Withheld | Withheld | RARE |
| Public Finance & Taxation | 2 | 2 | 0 | 0 | 148 | Withheld | Withheld | Withheld | RARE |
| Data Infrastructure & Methodology | 0 | 0 | 4 | 0 | 146 | Withheld | Withheld | Withheld | RARE |
| Housing & Planning | 0 | 0 | 1 | 0 | 149 | Withheld | Withheld | Withheld | RARE |

**Notes.** Reference is the labelwise human majority, not an adjudicated record-level truth set. Each label is evaluated separately; this is not exact-set accuracy against an adjudicated label combination. TP: model and reference positive; FP: model positive/reference negative; FN: model negative/reference positive; TN: both negative. Precision denominator is model-positive records; recall denominator is human-majority-positive records. Standard ≥30, Low support 10–29, Rare <10 baseline human-majority-positive records; all exported cautions and the three eligibility/reportability flags remain in the CSV. Macro eligibility does not govern this table. Withheld is distinct from undefined/unavailable; SV means interval suppressed by the valid-replicate rule while the estimate is retained. In Research Domains, Unclear has model-positive n=1, TP=1, FP=0 and FN=12; precision 1.0 therefore reflects one model-positive record, not broad agreement. Its precision and F1 intervals are marked SV because only 1284/716/2000 replicates were valid/invalid/requested, below the recorded 1,800-valid threshold. Unclear is a non-substantive classification option; FP/FN describe disagreement about applying it, not a proven right/wrong classification. Full-width/landscape typesetting is recommended.
