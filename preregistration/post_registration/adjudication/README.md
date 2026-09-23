# DEA adjudication build documentation

Status: proposed documentation and an offline synthetic prototype for review.
Neither is approved for formal adjudication, frozen, or authorised for a live
project. An earlier 209-field dictionary and its data-quality rules were
imported into the test project PID 9221 on 2026-09-22; the current 484-field
dictionary, its 36 data-quality rules and everything from ADJ-047 onwards have
not been imported or seen rendered, and `prototype/verification.md` records
exactly what each import covered. All prototype records, assignments, sources and
responses are synthetic; it contains no formal case content or source mapping.

## Purpose and navigation

The proposed workflow diagnoses the sources of selected classification
disagreements and informs, but does not replace, the preregistered release and
revision process. It does not alter the original independent-coder analyses,
make a gold standard, require consensus, or estimate register-wide error.

* [adjudication_build_spec.md](adjudication_build_spec.md) is the implementable
  REDCap and operating specification, including traceability, field proposals,
  masking, preservation, audit, and acceptance criteria.
* [adjudication_clarification_log.md](adjudication_clarification_log.md) logs
  agreed decisions, proposals, dependencies, and potential departures without
  treating a proposal as approval.
* [input_inventory.md](input_inventory.md) records the verified source paths,
  permitted inspection, version evidence, dictionary checks, and gaps.
* [prototype/README.md](prototype/README.md) describes the offline candidate
  dictionary, synthetic fixtures, local preview, validator and
  preservation/reveal simulation.

The documents use exactly these requirement classifications: **Preregistered
requirement**, **Agreed implementation decision**, **Proposed implementation
detail**, **Unresolved dependency**, and **Potential substantive departure**.
An agreed implementation decision does not amend the preregistration.

## Staged build sequence

1. Complete and review this documentation. It does not require reviewer
   appointments, a final owner export, or a live-system status conclusion.
2. Build and run the offline synthetic prototype in this directory. It checks
   canonical masked presentation, QA blocks, Stage 1 validation and append-only
   preservation/reveal using synthetic fixtures only; it does not establish
   REDCap behaviour, permissions, chronology, or human usability.
3. Test the reviewed prototype only in an explicitly authorised suitable
   non-production REDCap environment. This requires authorised test access,
   synthetic material, and capability checks for DAGs, locking, export/import
   logging and protected test storage; it does not require formal responses.
   Where the test project is intended to become the formal project, it remains
   in REDCap Development status throughout, and every synthetic record is
   erased and the erasure evidenced before any formal record is created.
4. Before formal coded-case primary adjudication, resolve its formal-use gates:
   build acceptance, appointed/conflict-declared roles, authorised eligibility
   inputs, and reconciled formal-response operational status.
5. Defer owner-derived eligibility and owner evidence until the coded-case
   gates and owner gates are met: verified communicated materials, collection
   and preparation completion, elapsed withdrawal deadline, and approved
   withdrawal/incomplete-response handling. Owner comments are substantive
   response analysis, not routine administration.
6. Fix the completed-primary universe, then perform the specified random and
   mandatory secondary-review selection. Secondary review follows only after
   the draw and without access to primary assessments. Release-gate work
   additionally requires the locked analysis inputs, evidence pack and senior
   sign-off process.

## Timing gates and immediate next action

The protocol requires owner materials to state a withdrawal deadline before
analysis begins (§6.5). The available v3.2 participant material states a
5 October 2026 survey closure and a 19 October 2026 withdrawal deadline. This
does not prove it was communicated to every relevant participant or establish
operational completion; those remain gates. The current documentation does not
read owner comments or select owner cases.

The next bounded task is review of the offline prototype, followed by testing
it in an explicitly authorised non-production REDCap project with synthetic
material only. It must not use formal cases, owner responses or live REDCap.
