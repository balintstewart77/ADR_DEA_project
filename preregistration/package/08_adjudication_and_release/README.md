# Adjudication and release

This folder is for the candidate adjudication instrument, audit-selection code,
and blank evidence-pack and senior sign-off templates. It must not contain
completed adjudications, reviewer contact details, or final release decisions
before registration. Candidate code now defines the v0.11 adjudication
population, exact eight issue families, source-masked presentation with duplicate
label sets shown once, owner-only Stage 1 without an artificial competitor, and
the recurring-trigger independence rule. It is tested only with synthetic
fixtures in `analysis/validation/adjudication.py`; it is not frozen, and no
adjudication has begun. The six release-category labels and distinct scratch
reserve versus post-revision owner routes are represented without automating a
release decision. Audit selection and completed instruments remain gated; the
protocol does not yet fix the 20% rounding and generator details, so the code
does not guess them.
