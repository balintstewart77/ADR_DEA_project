#!/usr/bin/env python3
"""Deterministically select the preregistered secondary-adjudication audit.

This module performs no network access and contains no study records.  The
official audit universe is supplied only after primary adjudication is complete.
The command-line ``--check`` mode validates the frozen specification without
creating an RNG or selecting any project.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


SEED_ADJUDICATION_AUDIT = 20260715
AUDIT_FRACTION = 0.20
BIT_GENERATOR = "numpy.random.PCG64"


@dataclass(frozen=True)
class AuditSelection:
    ordered_universe: tuple[str, ...]
    random_audit_size: int
    random_draw_order: tuple[str, ...]
    random_selected_set: tuple[str, ...]
    mandatory_selected_set: tuple[str, ...]
    overlap: tuple[str, ...]
    unique_second_reviewed_set: tuple[str, ...]
    seed: int

    @property
    def mandatory_review_count(self) -> int:
        return len(self.mandatory_selected_set)

    @property
    def overlap_count(self) -> int:
        return len(self.overlap)

    @property
    def unique_second_reviewed_count(self) -> int:
        return len(self.unique_second_reviewed_set)


def _stable_order(record_ids: Iterable[str]) -> tuple[str, ...]:
    values = tuple(record_ids)
    if any(not value or value != value.strip() for value in values):
        raise ValueError("Record IDs must be non-empty and free of boundary whitespace")
    if len(set(values)) != len(values):
        raise ValueError("The completed primary-adjudication universe contains duplicate Record IDs")
    # Record ID is the unique project-level key.  Python's stable string order
    # is the deterministic secondary rule if textual keys otherwise compare equal.
    return tuple(sorted(values))


def random_audit_size(completed_primary_adjudications: int) -> int:
    if completed_primary_adjudications < 0:
        raise ValueError("completed_primary_adjudications cannot be negative")
    if completed_primary_adjudications == 0:
        return 0
    return ceil(AUDIT_FRACTION * completed_primary_adjudications)


def select_adjudication_audit(
    completed_record_ids: Sequence[str],
    *,
    mandatory_record_ids: Sequence[str] = (),
    seed: int = SEED_ADJUDICATION_AUDIT,
) -> AuditSelection:
    """Select without replacement after the completed universe is fixed.

    Mandatory or triggered second reviews are additional to the random audit.
    Overlap is retained and reported and never reduces the random draw size.
    """

    universe = _stable_order(completed_record_ids)
    mandatory = _stable_order(mandatory_record_ids)
    unknown_mandatory = set(mandatory) - set(universe)
    if unknown_mandatory:
        raise ValueError(
            "Mandatory second reviews are outside the completed universe: "
            f"{sorted(unknown_mandatory)}"
        )
    size = random_audit_size(len(universe))
    if size:
        generator = np.random.Generator(np.random.PCG64(seed))
        indices = generator.choice(len(universe), size=size, replace=False)
        draw_order = tuple(universe[int(index)] for index in indices)
    else:
        draw_order = ()
    selected = tuple(sorted(draw_order))
    overlap = tuple(sorted(set(selected) & set(mandatory)))
    unique = tuple(sorted(set(selected) | set(mandatory)))
    return AuditSelection(
        ordered_universe=universe,
        random_audit_size=size,
        random_draw_order=draw_order,
        random_selected_set=selected,
        mandatory_selected_set=mandatory,
        overlap=overlap,
        unique_second_reviewed_set=unique,
        seed=seed,
    )


def select_official_adjudication_audit(
    completed_record_ids: Sequence[str],
    *,
    mandatory_record_ids: Sequence[str] = (),
) -> AuditSelection:
    """Official wrapper whose frozen seed cannot be overridden by a caller."""

    return select_adjudication_audit(
        completed_record_ids,
        mandatory_record_ids=mandatory_record_ids,
        seed=SEED_ADJUDICATION_AUDIT,
    )


def audit_evidence_document(selection: AuditSelection) -> dict[str, object]:
    """Return the deterministic, reviewable evidence schema for one selection."""

    return {
        "schema_version": "adjudication-audit-evidence-1.0",
        "seed": selection.seed,
        "bit_generator": BIT_GENERATOR,
        "audit_fraction": AUDIT_FRACTION,
        "ordered_universe": list(selection.ordered_universe),
        "random_audit_size": selection.random_audit_size,
        "selected_draw_order": list(selection.random_draw_order),
        "final_random_selected_set": list(selection.random_selected_set),
        "mandatory_review_set": list(selection.mandatory_selected_set),
        "overlap": list(selection.overlap),
        "unique_second_reviewed_set": list(selection.unique_second_reviewed_set),
        "counts": {
            "random_audit": selection.random_audit_size,
            "mandatory_review": selection.mandatory_review_count,
            "overlap": selection.overlap_count,
            "unique_second_reviewed": selection.unique_second_reviewed_count,
        },
    }


def write_audit_evidence(selection: AuditSelection, output_path: Path) -> None:
    """Write evidence only when an authorised future caller supplies a path."""

    output_path.write_text(
        json.dumps(audit_evidence_document(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def static_check() -> None:
    assert AUDIT_FRACTION == 0.20
    assert SEED_ADJUDICATION_AUDIT == 20260715
    assert BIT_GENERATOR == "numpy.random.PCG64"
    assert random_audit_size(0) == 0
    assert random_audit_size(1) == 1
    assert random_audit_size(6) == 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate constants and ceiling rules; create no RNG or selection.",
    )
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("Only the read-only --check mode is available from the command line")
    static_check()
    print("Adjudication audit specification passed static checks; no RNG was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
