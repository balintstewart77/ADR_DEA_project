# Phase 4 completion report

## Conclusion

**Phase 4 complete.** The official sampling system is implemented, tested and
documented as a working candidate ready for Gate 1 freeze. The official draw
was not executed.

## Audit identity and objective

- Repository: `C:/Users/balin/Desktop/ADR_DEA_project`
- Branch: `main`
- Audited HEAD: `c34f963ed404c29ac299ac2b0f82f0bb5bf2bc05`
- Python: 3.13.2; NumPy: 2.2.5; pandas: 2.2.3
- Starting worktree: clean

The objective was to implement and verify the future official draw while
preserving the prospective boundary: no sample, rank, assignment or validation
coding is produced before registration and Gate 2.

## Authoritative inputs validated without drawing

| Input | Rows | SHA-256 |
| --- | ---: | --- |
| `preregistration/package/01_source_and_cleaning/dea_accredited_projects_20260601_cleaned_1308.csv` | 1,308 | `a334bd7f06e23db4cc8497274b36c0c483f6f0db7b079013e18729cd189ff9c1` |
| `preregistration/package/04_exclusions_and_sampling/training_pilot_exclusion_list_v8.csv` | 22 | `cf36e6d34375d0e68bac31df8169207fc0602bc7291a64e995b9cd86141413a6` |
| `preregistration/package/03_preexisting_model_evidence/gpt55_disagreement_frame_380.csv` | 380 | `e21c113913beb5f70bb45080808c7d4d78df95798f32db16aecf718b10cb93af` |

The exclusion and disagreement-frame digests are raw SHA-256 values of their
canonical UTF-8-with-BOM, LF serializations enforced by `.gitattributes`;
platform-specific CRLF working copies are not valid replacement provenance
values.

The cleaned population has 1,308 unique clean canonical Record IDs. The
exclusion set is exactly 11 keyed worked examples, one unkeyed discussion case
and ten pilots. All exclusions exist in the population and none is in the
post-exclusion hard frame. The hard frame has 182 domain-only, 143 purpose-only
and 55 both-dimension disagreements; 11 also have an accompanying tag
disagreement.

## Implemented draw design

`scripts/draw_validation_samples.py` stable-sorts clean Record IDs before every
random operation and uses `numpy.random.Generator` with `numpy.random.PCG64`.
The registered master seed is 20260713, but Phase 4 never supplied it to the
real frames.

The future generator-consumption order is: baseline active (150), baseline
reserve (100), random fills for active hard domain-only, purpose-only and both
after sorted forced cases, selection of the 16-seat reserve stratum, one
seed-governed reserve-reallocation tie order, then reserve draws in the fixed
domain-only, purpose-only and both order. Every operation is without
replacement and all four outputs are mutually disjoint.

After baseline depletion, every remaining accompanying-tag case is forced into
the active hard sample inside its existing stratum and counts toward that
stratum's quota. More than 25 forced cases or fewer than 25 available cases in
any stratum is fatal. Active hard is exactly 25/25/25.

Hard reserve begins 17/17/16, with the 16-seat stratum selected by PCG64. Each
quota is capped at post-active availability. A shortfall is reallocated one
seat at a time across strata with spare capacity, following one recorded
seed-governed tie order. If total capacity is below 50, the largest valid
reserve is returned and the unfilled shortfall is recorded; active quotas are
never reallocated.

## Safety guard and prospective boundary

`--check` parses static configuration and creates no RNG. The
`--validate-real-inputs` path validates hashes, schemas, IDs, counts, strata and
pre-baseline feasibility without calling the RNG factory and without writing.
Synthetic mode requires explicit toy paths, an output directory and a
non-official seed; it rejects the official seed and the canonical real-path
triple.

Future `--execute-official-draw` additionally requires the canonical inputs,
restricted ignored output storage, a local registration receipt with a real OSF
identity and timestamp, Gate 2 confirmation, the frozen commit and all four
expected hashes, exact HEAD agreement, a clean worktree, 22 exclusions, the
typed token `EXECUTE_REGISTERED_DEA_DRAW`, and an output location containing no
prior official draw. No receipt was created in Phase 4.

## Tests and output contract

Thirty-two synthetic and safety tests cover ordinary and deterministic draws,
row-order invariance, different seeds, exclusions and disjointness, both forms
of baseline hard-frame depletion, forced inclusion and overflow, deterministic
17/17/16 allocation, one- and two-stratum fallback, total shortfall, active
infeasibility, exact exhaustion, dirty/duplicate/missing IDs, unknown strata,
inconsistent flags, no-write/no-RNG check modes, official guard failures, and
output metadata/hash integrity. All tests pass.

`sampling_output_schema.json` defines the four future restricted CSVs, combined
manifest, metadata and assertion report without containing identities. Metadata
records input and output hashes, versions, counts, pre/post strata, forced
counts, initial/final allocations, fallback actions and assertions.

## Embargo and disclosure

At registration, code, specification, official seed, input paths and hashes,
environment, schema and runbook may be public. No sampled IDs are archived
because none exists. After a future draw, all identity manifests remain
restricted. Active identities may be released only after initial independent
coding and a blinding review. Reserve identities, strata and ranks remain
embargoed until reserve retesting is complete or the reserve is formally
retired. Aggregate counts and strata may be public.

## Artefacts and unresolved items

Created: sampling engine, its tests, sampling specification, output schema,
official runbook and this report. Updated: package 04 README, preregistration
README, inventory and artefact manifest. The protocol, REDCap instrument,
coder/trainer/pilot materials and scientific inputs were not modified.

The sampling artefacts remain working candidates pending collaborator/pilot
resolution and Gate 1 freeze. Registration receipt, official outputs, coder
assignments and formal validation data are correctly absent and prospective.
There is no unresolved Phase 4 implementation or verification issue.

No official draw was executed; no real Record ID was randomly ranked or
selected; no active or reserve manifest or coder assignment exists; no API or
LLM call occurred; and no scientific source, taxonomy, classification or
evidence package changed.
