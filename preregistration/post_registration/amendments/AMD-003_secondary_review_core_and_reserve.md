# AMD-003: secondary review in a blind core with reserve batches (§9.1)

| | |
|---|---|
| Date | 2026-11-13 |
| Protocol | v1.1 (frozen), §9.1 Adjudication population and process; as amended by AMD-002 |
| Type | Substantive change to the second-review procedure, made before the audit draw and before any formal secondary review |
| Made | After the primary pass (199 records) was completed and after N became final (no withdrawal by the 26 October 2026 deadline; DEV-006). Before the audit draw, before the secondary adjudicator has any access to formal records, and before any formal secondary review |
| Approval | Study lead (Balint Stewart), 2026-11-13. The protocol requires a substantive amendment to be versioned and documented before the affected step (§11); it requires no further approval |
| Implementation | `draw_secondary_audit.py`, generator `secondary-audit-3.0 (AMD-003)`, function `draw_batches`. The AMD-002 function `draw` is kept unchanged for the record |
| Deviation log | DEV-009 |

## Text

**Preregistered (§9.1):** a second adjudicator independently reviews a random 20% of completed adjudicated records, in addition to the mandatory items.

**As amended by AMD-002:** the random audit is ⌈0.20 × N⌉ records, seed 20260715, drawn first; mandatory items 1 to 4 are added.

**Amended:**

1. **The random audit is drawn exactly as preregistered.** It is ⌈0.20 × N⌉ = 40 records, sampled with seed 20260715 using the same call as AMD-002. The sampled order is kept.
2. **The core** is the first 20 records of the random audit in seeded order, together with the AMD-002 mandatory items 1 to 4. For item 4, a recurring mechanism counts as covered only if one of its records is among the core's random records or the mandatory records, which are the records the secondary actually reviews. Otherwise one of its records is drawn with seed 20261019, as in AMD-002.
3. **The core is reviewed as one masked batch.** Random and mandatory records are interleaved with seed 20260924 so that they cannot be told apart. Every Stage 1 is completed and preserved before any reveal, and Stage 2 follows the reveal.
4. **Two reserve batches** hold the remaining random records in seeded order:
   - **extension 1:** positions 21 to 30;
   - **extension 2:** positions 31 to 40.

   Any record that is already mandatory is reviewed in the core instead.
5. **Whether a reserve batch is reviewed depends only on the secondary adjudicator's available time.** That decision is made before any of the secondary's core answers are compared with the primary's. Each reserve batch is reviewed whole, Stage 1 for the whole batch before its reveal. Reserve batches are reviewed after the core's reveal, so they are post-reveal.

## Analysis

- **Agreement on the random audit** is estimated from the core's 20 random records, which were reviewed blind. This is the primary estimate.
- **Reserve-batch records**, if reviewed, are reported separately and pooled with the core as a sensitivity analysis, labelled post-reveal.
- **The number of random records reviewed** is reported against the preregistered 40.
- **Mandatory items and the confirmation of recurring mechanisms** are reported as under AMD-002, from the core.

## Reason

The secondary adjudicator's time is limited. Under AMD-002 the expected load is about 54 records, roughly 13 to 14 hours. The core is expected to be about 37 records, roughly 9 hours, and each reserve batch about 2 to 3 hours.

The size of the core was set by that capacity alone. It is the smallest random sample judged useful for an agreement estimate that keeps every mandatory review.

Taking the first records in seeded order keeps the core a simple random sample of completed records, as ADJ-076 relied on for the interim primary results.

## Effect and limitations

- **Agreement on the random audit rests on 20 blind records,** not 40. The estimate is less precise and is reported as such.
- **Reserve-batch records are not blind in the same sense,** because the secondary has seen the core's reveals. They are reported separately.
- **Some recurring mechanisms need one more mandatory record each** than under AMD-002, because records in the reserve batches no longer count as covering them. The mandatory set never shrinks.
- **The primary adjudicator knew the aggregate primary results when this amendment was made,** as with AMD-002. The rule refers to no finding, mechanism or record: it fixes a number and an order. The records come from the preregistered seeded draw.
- **The secondary adjudicator (the principal investigator) is told only the workload:** the core and the optional reserve batches.
