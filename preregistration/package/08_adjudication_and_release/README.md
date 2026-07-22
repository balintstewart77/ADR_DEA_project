# Adjudication and release

This folder contains the blank v0.14 adjudication instrument, deterministic
secondary-audit selector, and blank evidence-pack and senior sign-off templates.
They contain no study record, completed adjudication, reviewer contact detail, or
release decision.

The adjudication population and eight issue families follow protocol v0.14.
Stage 1 presents duplicate label sets once and masks their sources; Stage 2 reveals
sources only after the provisional diagnosis. Owner-only Stage 1 does not invent an
artificial comparator, and recurring-trigger independence remains explicit.

The random secondary-review audit is drawn only after the universe of completed
primary-adjudication projects is fixed. Its size is zero for N=0 and otherwise
`ceil(0.20 × N)`. The universe is stable-sorted by source Record ID and sampled
without replacement with NumPy PCG64 and `SEED_ADJUDICATION_AUDIT = 20260715`.
The general selector remains available for synthetic testing; the official
wrapper exposes no seed parameter. The deterministic evidence schema records
the ordered universe, draw order, final random set, mandatory set, overlap and
unique second-reviewed set. `--check` creates no RNG and writes no evidence.
The ordered universe, draw order and selected set are recorded. Mandatory reviews
are additional; overlap is allowed and reported and never reduces the random draw.
No real audit universe or audit sample exists in this package.
