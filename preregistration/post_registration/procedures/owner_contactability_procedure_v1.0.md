# Owner contactability procedure

Version 1.0 | 18 August 2026

Frozen before any contact search or sequence position was determined. Post-registration procedural specification.

Fills the gap §5.4 identifies but does not populate: the prespecified source hierarchy and fixed effort ceiling for establishing whether a candidate owner is contactable.

---

## Scope

Applies to sequence-based recruitment only. Supplementary recruitment is governed separately under §5.4 and its reviews do not count toward the 25 or 50 thresholds.

A candidate is a conservatively identified named person from the Accredited Researchers field of an eligible register record. Organisations, ambiguous entities and unresolved identities are excluded at the parsing stage, before this procedure applies.

**Scratch coders require no exclusion.** They are not named in the register and therefore cannot be candidates.

## What counts as contactable

A **professional** contact route: an email address published by an institution, publisher, professional body or the person themselves in a professional capacity.

Not acceptable: personal addresses, addresses obtained from private correspondence, addresses inferred from an institutional pattern without a published instance, social media direct messaging, and any route obtained from data held by this study.

The route must be current on its face — a staff page marked as former staff does not qualify.

## Source hierarchy

Searched in order. **Stop at first success.** Record which source succeeded.

1. **Institutional staff or departmental page** for the institution named alongside the researcher in the register.
2. **Institutional directory search** for the same institution, where no staff page is found.
3. **Corresponding-author address** on a publication by that person, where the publication is retrievable and the address is published in it.
4. **ORCID record**, or an equivalent professional research profile, where it carries a published contact address.
Sources not in this list are not searched. **A candidate who has left the institution named in the register is `NOT_FOUND`** — the search does not follow them to a new institution. This keeps the search bounded and the procedure uniform; the cost is a small number of otherwise-reachable people, accepted deliberately. If a route surfaces incidentally from a source outside the hierarchy, it is not used.

## Effort ceiling

**Ten minutes per candidate**, measured from opening the first source.

Rationale: sources 1 and 2 resolve most academic researchers in under two minutes. Ten minutes allows progression through the hierarchy for a harder case without the search becoming open-ended, and is short enough to apply honestly across twenty-five candidates.

The ceiling is a stopping rule, not a target. A candidate resolved in thirty seconds is resolved.

Where the ceiling is reached without a route, the disposition is **not contactable within ceiling**. This records the outcome of a bounded search; it does not assert the person is unreachable in principle.

## Disposition categories

Exhaustive. Every candidate assessed receives exactly one.

| Code | Disposition | Meaning |
|---|---|---|
| `CONTACTABLE` | Contactable | A qualifying professional route was found within the ceiling. |
| `NOT_FOUND` | Not contactable within ceiling | The hierarchy was exhausted, or the ceiling reached, without a qualifying route. |
| `UNRESOLVED` | Identity unresolvable | The register name could not be resolved to a specific person with confidence — common name, no institution, or multiple plausible matches. |
| `INELIGIBLE` | Ineligible | Deceased, retired with no professional route, or otherwise not appropriately approached. Record the reason as free text. |

Under §5.4 every disposition other than `CONTACTABLE` removes the candidate **without covering their records**, and marginal coverage is recomputed before the next position.

## Evidence recorded per candidate

- `candidate_key`
- Sequence step at which the search was conducted
- Disposition code
- Source that succeeded, or the last source reached
- URL of the page carrying the route, or of the last source consulted
- Date of search
- Elapsed time, to the nearest minute
- Free-text note, only where the disposition needs explanation

The contact route itself is recorded in the restricted recruitment table, never in the pseudonymous frame.

## Procedural rules

**One candidate at a time.** A search may only be conducted for the candidate the algorithm has computed as next. Searching ahead is not permitted: an earlier non-contactable disposition changes who comes next, so a search conducted early may be for someone who never reaches the front.

**Incidental prior knowledge is not a disposition.** Knowing a researcher's address before they reach the front of the queue is not a protocol departure; recording it as a sequence disposition before that point is. When they reach the front, the search is conducted and recorded as normal, and an already-known published route may be verified rather than rediscovered — record the source and URL as usual.

**Dispositions are append-only.** A recorded disposition is not revised silently. A correction is recorded as a correction, with its reason, and treated as a protocol deviation if it changes the sequence.

**No contact is made during this procedure.** Establishing that a route exists is not contacting the person. Invitations issue separately, after the frame is frozen.

---

## Status

Frozen 18 August 2026, before the first candidate frame was built and before any contact search.

This is a **post-registration procedural specification**, not a preregistered artefact. §5.4 requires that a source hierarchy and effort ceiling be prespecified; it does not fix their content. This document supplies that content and is fixed before use, which is what the requirement asks for.

Not added to the preregistration manifest. Held in the post-registration record.

The ten-minute ceiling is a judgement rather than a derivation. Sources 1 and 2 resolve most UK academics in under two minutes; ten allows progression to ORCID for a harder case without the search drifting, and caps twenty-five candidates at roughly four hours.
