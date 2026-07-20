# Pilot agreement heatmap legend

The heatmap shows seven dimensions for each of the 10 pilot Record IDs:
Research Domains, Analytical Purposes, the demographic-disparities/equality tag,
the COVID-19/pandemic tag, register sufficiency, taxonomy fit, and confidence.

## Colours and classification rules

- **Green — all three agree.** For set dimensions, all three complete label sets
  are identical. For binary tags, all three responses are positive or all three
  are negative. For categorical diagnostics, all three selected the same category.
- **Yellow — two agree and one differs.** For set dimensions, exactly two complete
  sets are identical. For tags or categorical diagnostics, two responses match
  and the third differs.
- **Red — split.** For set dimensions, all three complete sets differ pairwise.
  For categorical diagnostics, all three categories differ and there is no
  majority. A three-way binary-tag split is impossible under the stored 0/1 coding.

The labels inside the cells abbreviate these states as `All agree`, `All +`,
`All −`, `2–1`, or `Split`. Set-level `all_sets_distinct` does not imply that no
individual label has two-of-three support.

This is a descriptive instrument-pilot visual intended to highlight difficult
records and dimensions. It is not a coder-performance ranking and does not
identify or evaluate a lone dissenter.
