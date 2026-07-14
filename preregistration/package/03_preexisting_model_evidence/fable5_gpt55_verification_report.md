# Fable 5 / GPT-5.5 deterministic comparison verification

## Scope

This report was regenerated locally from the existing corrected Fable 5 and
GPT-5.5 classification outputs. No API or model call was made and no
classification was regenerated. Cross-cutting tags are compared as two frozen
taxonomy facets: `COVID-19 & Pandemic` and `Demographic disparities / equity tag`.
`tag_set_match` and the retained compatibility field `any_tag_set_match` both mean
that the two facets agree.

Jaccards are calculated directly from unrounded raw label sets; per-record CSV
values are stored at normal Python floating-point precision.

## Full 1,308-record population

- Domain exact agreement: 1065/1308 (81.422018348624%).
- Mean domain Jaccard: 0.904243119266055.
- Purpose exact agreement: 1108/1308 (84.709480122324%).
- Mean purpose Jaccard: 0.884556574923547.
- COVID tag agreement: 1304/1308.
- Demographic-disparities/equity tag agreement: 1263/1308.
- Joint two-tag agreement: 1259/1308; 49 records differ on at least one tag.
- Invalid GPT-5.5 outputs: 0.

## Domain/purpose disagreement frame

Before the final verified 22-record training/discussion/pilot exclusion set:

- 386 total: 186 domain-only, 143 purpose-only, and 57 both.
- 12 include a tag disagreement; 37 tag-only disagreements sit outside the frame.

After exclusions, `gpt55_disagreement_frame_380.csv` has 380 records:

- 182 domain-only, 143 purpose-only, 55 both.
- 11 include a tag disagreement; 37 tag-only disagreements remain outside the frame.
