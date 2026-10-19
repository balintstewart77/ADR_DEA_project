# AMD-002: scope of mandatory second review (§9.1)

| | |
|---|---|
| Date | 2026-10-19 |
| Protocol | v1.1 (frozen), §9.1 Adjudication population and process |
| Type | Substantive change to the second-review procedure, made before any second review |
| Made | After the primary pass (199 records) was completed and before the audit draw, before the secondary adjudicator has any access to formal records, and before any secondary review |
| Approval | Study lead (Balint Stewart), 2026-10-19. The protocol requires a substantive amendment to be versioned and documented before the affected step (§11); it requires no further approval |
| Implementation | `draw_secondary_audit.py`, generator `secondary-audit-2.0 (AMD-002)`; draw manifest from `run_adjudication_diagnostics.py` |
| Deviation log | DEV-008 |

## Text

**Original (§9.1):** "All apparent production-model rule-application
problems, unresolved cases, and cases proposed as evidence for prompt
revision, taxonomy revision, or non-release receive mandatory second review in
addition to [the random audit]."

**Amended:** Mandatory second review comprises, in addition to the random
audit:

1. every completed record with a finding proposed as evidence for prompt
   revision, taxonomy revision or non-release;
2. every completed record with an Unresolved finding (family 8);
3. every record whose apparent model rule-application finding was retracted
   by a recorded reflection;
4. for each **recurring model-attributable mechanism**, at least one of the
   records carrying it. A mechanism is recurring when a family 1 finding with
   that mechanism appears on two or more distinct completed records, after
   harmonisation and the recode of mechanism 24, with retracted findings
   excluded. General mechanisms are counted separately for each label they
   concern. A mechanism is covered if any record already selected under the
   random audit or items 1 to 3 carries it. Otherwise one of its records is
   drawn at random.

The random audit is unchanged: ⌈0.20 × N⌉ records, seed 20260715, drawn
first. Apparent model rule-application findings on records not selected by
either route are second-reviewed only if they fall in the random audit.

## Selection procedure

After N is final (after the 26 October 2026 withdrawal deadline, DEV-006):

1. draw the random audit, as preregistered;
2. add items 1 to 3;
3. take the recurring model-attributable mechanisms in ascending order of
   record count, then mechanism code, then label. For each mechanism not yet
   covered, draw one of its records with `random.Random(20261019)` from its
   record IDs sorted ascending, and add it;
4. interleave and mask the queue so that random and mandatory selections
   cannot be told apart, as the protocol already requires.

The seed (20261019) and the order are fixed in this amendment, before any
draw.

## Reason

Under the original rule, every apparent model rule-application finding
receives mandatory second review. For the completed primary pass that brings
the expected second-review load, with the random audit, well beyond the
secondary adjudicator's capacity. The expected load under the original rule,
and the number and kinds of findings, are withheld here until the secondary
review ends (ADJ-073), and are reported with it.

The release framework (§10.2) turns on recurring model-attributable problems
and on cases proposed as evidence for revision or non-release, not on each
individual finding. The amended rule keeps an independent second review of
every revision or non-release proposal, every unresolved case, every retracted
model finding, and at least one instance of every recurring model-attributable
mechanism, while bringing the expected load to about 55 records.

## Effect and limitations

* Expected second-review load: about 55 records.
* Model findings that do not recur are second-reviewed only through the
  random audit. Agreement on model findings is estimated from the random
  audit and reported as such.
* Each recurring mechanism is independently confirmed on at least one record,
  so the recurrence itself rests on the primary's records. Where the
  secondary disagrees on the reviewed instance, the mechanism's recurrence is
  reported as unconfirmed.
* The primary adjudicator knew the aggregate count of model findings when
  this amendment was made. The records reviewed for each mechanism are chosen
  by a seeded draw, not by the primary.
* The amendment was made by the study lead, who is also the primary
  adjudicator. The secondary adjudicator (the principal investigator) is told
  only the revised workload, not the expected load under the original rule or
  the number or kinds of findings.
