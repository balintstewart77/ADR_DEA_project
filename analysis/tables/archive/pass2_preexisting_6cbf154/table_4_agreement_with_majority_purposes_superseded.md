# Per-label contingencies and model performance — Analytical Purposes (baseline n=150 records).

| Label | Support n | TP | FP | FN | TN | Precision | Recall | F1 | Band |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Descriptive Monitoring | 36 | 26 | 26 | 10 | 88 | 0.500 [0.367, 0.639] 95% | 0.722 [0.568, 0.861] 95% | 0.591 [0.463, 0.699] 95% | STANDARD |
| Policy Evaluation / Impact Analysis | 30 | 21 | 12 | 9 | 108 | 0.636 [0.459, 0.808] 95% | 0.700 [0.531, 0.857] 95% | 0.667 [0.507, 0.793] 95% | STANDARD |
| Unclear from Register Entry | 26 | 1 | 0 | 25 | 124 | 1.000 SV | 0.038 [0.000, 0.125] 95% | 0.074 SV | LOW SUPPORT |
| Outcome Tracking | 19 | 13 | 34 | 6 | 97 | 0.277 [0.152, 0.417] 95% | 0.684 [0.458, 0.889] 95% | 0.394 [0.229, 0.540] 95% | LOW SUPPORT |
| Life-Course / Trajectory Analysis | 9 | 3 | 8 | 6 | 133 | Withheld | Withheld | Withheld | RARE |
| Methodological / Infrastructure Research | 7 | 5 | 5 | 2 | 138 | Withheld | Withheld | Withheld | RARE |
| Risk Prediction / Early Identification | 1 | 1 | 1 | 0 | 148 | Withheld | Withheld | Withheld | RARE |
| Service Interaction / Systems Analysis | 1 | 1 | 3 | 0 | 146 | Withheld | Withheld | Withheld | RARE |

**Notes.** Reference is the labelwise human majority, not an adjudicated record-level truth set. Each label is evaluated separately; this is not exact-set accuracy against an adjudicated label combination. TP: model and reference positive; FP: model positive/reference negative; FN: model negative/reference positive; TN: both negative. Precision denominator is model-positive records; recall denominator is human-majority-positive records. Standard ≥30, Low support 10–29, Rare <10 baseline human-majority-positive records; all exported cautions and the three eligibility/reportability flags remain in the CSV. Macro eligibility does not govern this table. Withheld is distinct from undefined/unavailable; SV means interval suppressed by the valid-replicate rule while the estimate is retained. In Analytical Purposes, Unclear has model-positive n=1, TP=1, FP=0 and FN=25; precision 1.0 therefore reflects one model-positive record, not broad agreement. Its precision and F1 intervals are marked SV because only 1233/767/2000 replicates were valid/invalid/requested, below the recorded 1,800-valid threshold. Unclear is a non-substantive classification option; FP/FN describe disagreement about applying it, not a proven right/wrong classification. Full-width/landscape typesetting is recommended.
