# Full-register Fable 5 replicate against production (exploratory, descriptive)

Post-registration; not preregistered. Specification: `SPEC_fable_production_replicate_2026-11-10.md`. Production labels (MOD-006) are unchanged. No intervals or tests. J = mean Jaccard.

## FPR1T001 — Replicate against production

| Population | Records | Research Domains exact (J) | Analytical Purposes exact (J) | COVID-19 & Pandemic | Demographic disparities / equity | Both tags | All four | Domains or purposes differ |
|---|---|---|---|---|---|---|---|---|
| full register | 1308 | 1215/1308 (0.929); J 0.965 | 1237/1308 (0.946); J 0.964 | 1305 | 1295 | 1292 | 1135 | 161 |
| random baseline | 150 | 139/150 (0.927); J 0.964 | 144/150 (0.960); J 0.977 | 150 | 148 | 148 | 132 | 17 |
| hard-case (diagnostic) | 75 | 59/75 (0.787); J 0.896 | 64/75 (0.853); J 0.900 | 75 | 74 | 74 | 48 | 26 |
| Stage R (run-1 sample) | 201 | 191/201 (0.950); J 0.978 | 189/201 (0.940); J 0.955 | 201 | 198 | 198 | 176 | 22 |
| Stage P (rest of register) | 1107 | 1024/1107 (0.925); J 0.963 | 1048/1107 (0.947); J 0.966 | 1104 | 1097 | 1094 | 959 | 139 |

## FPR1T002 — Three runs on the 201 run-1 sample records

| Comparison | Research Domains exact (J) | Analytical Purposes exact (J) | All four |
|---|---|---|---|
| run 1 (production) vs run 2 | 191/201 (0.950); J 0.974 | 185/201 (0.920); J 0.935 | 171 |
| replicate vs run 1 (production) | 191/201 (0.950); J 0.978 | 189/201 (0.940); J 0.955 | 176 |
| replicate vs run 2 | 191/201 (0.950); J 0.973 | 183/201 (0.910); J 0.930 | 170 |
| all three runs agree | 186/201 | 179/201 | 159 |

FPR1T003: 173 records differ on at least one component (register-wide; no sample membership recorded).
