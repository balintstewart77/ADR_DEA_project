"""Derive the pure algorithmic owner-coverage visualisations.

Both strategies ignore contactability. Public outputs contain anonymous coverage
statistics only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Hashable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[2]
FIGURE_DATA_PATH = (
    REPO_ROOT / "analysis/figure_data/owner_sampling_coverage_comparison.csv"
)
METADATA_PATH = REPO_ROOT / (
    "analysis/figure_data/owner_sampling_coverage_comparison_metadata.json"
)
PNG_PATH = REPO_ROOT / "analysis/figures/owner_sampling_coverage_comparison.png"
SVG_PATH = REPO_ROOT / "analysis/figures/owner_sampling_coverage_comparison.svg"
PDF_PATH = REPO_ROOT / "analysis/figures/owner_sampling_coverage_comparison.pdf"
PORTFOLIO_COMPARISON_PNG_PATH = REPO_ROOT / (
    "analysis/figures/owner_sampling_portfolio_vs_marginal_comparison.png"
)
PORTFOLIO_COMPARISON_SVG_PATH = REPO_ROOT / (
    "analysis/figures/owner_sampling_portfolio_vs_marginal_comparison.svg"
)
PORTFOLIO_COMPARISON_PDF_PATH = REPO_ROOT / (
    "analysis/figures/owner_sampling_portfolio_vs_marginal_comparison.pdf"
)
STRATEGY_TOTAL = "total_project_count"
STRATEGY_GREEDY = "greedy_marginal_coverage"
FIGURE_DATA_FIELDS = [
    "strategy",
    "selection_step",
    "owner_total_eligible_projects",
    "marginal_unique_projects",
    "cumulative_unique_projects",
    "cumulative_coverage_pct",
]
PURE_SELECTION_TARGET = 25
EXPECTED_TOTAL_CUMULATIVE = (
    20, 37, 49, 51, 58, 70, 70, 80, 83, 92, 101, 102, 110,
    110, 110, 114, 120, 127, 134, 134, 140, 147, 147, 152, 159,
)
EXPECTED_GREEDY_CUMULATIVE = (
    20, 37, 49, 61, 71, 80, 89, 97, 104, 111, 118, 125, 132,
    139, 146, 152, 158, 164, 170, 176, 182, 188, 193, 198, 203,
)


@dataclass(frozen=True)
class SelectionStep:
    """One candidate selected by an algorithmic coverage sequence."""

    candidate: Hashable
    selection_step: int
    owner_total_eligible_projects: int
    marginal_unique_projects: int
    cumulative_unique_projects: int
    tie_break_applied: str
    primary_tie_size: int
    secondary_tie_size: int


@dataclass(frozen=True)
class AuthoritativeInputs:
    portfolios: dict[str, frozenset[str]]
    tie_break_keys: dict[str, str]
    authoritative_source_hashes: dict[str, str]


def _validate_inputs(
    portfolios: Mapping[Hashable, set[str] | frozenset[str]],
    tie_break_keys: Mapping[Hashable, str],
) -> dict[Hashable, frozenset[str]]:
    if not portfolios:
        raise ValueError("Candidate/project mapping is empty")
    canonical = {candidate: frozenset(projects) for candidate, projects in portfolios.items()}
    if any(not projects for projects in canonical.values()):
        raise ValueError("Every candidate must have at least one eligible project")
    if set(tie_break_keys) != set(canonical):
        raise ValueError("Tie-break keys do not exactly cover the candidate universe")
    if len(set(tie_break_keys.values())) != len(tie_break_keys):
        raise ValueError("Tie-break keys are not unique")
    return canonical


def rank_by_total_projects(
    portfolios: Mapping[Hashable, set[str] | frozenset[str]],
    tie_break_keys: Mapping[Hashable, str],
    *,
    selection_limit: int | None = None,
) -> list[SelectionStep]:
    """Rank once by total projects, then calculate coverage without re-ranking."""

    canonical = _validate_inputs(portfolios, tie_break_keys)
    order = sorted(
        canonical,
        key=lambda candidate: (-len(canonical[candidate]), tie_break_keys[candidate]),
    )
    if selection_limit is not None:
        if selection_limit < 0:
            raise ValueError("selection_limit cannot be negative")
        order = order[:selection_limit]

    covered: set[str] = set()
    sequence: list[SelectionStep] = []
    for step, candidate in enumerate(order, 1):
        marginal = len(canonical[candidate] - covered)
        covered.update(canonical[candidate])
        total_tie_size = sum(
            len(projects) == len(canonical[candidate])
            for projects in canonical.values()
        )
        sequence.append(
            SelectionStep(
                candidate=candidate,
                selection_step=step,
                owner_total_eligible_projects=len(canonical[candidate]),
                marginal_unique_projects=marginal,
                cumulative_unique_projects=len(covered),
                tie_break_applied=(
                    "none"
                    if total_tie_size == 1
                    else "conservative_identity_key_asc"
                ),
                primary_tie_size=total_tie_size,
                secondary_tie_size=total_tie_size,
            )
        )
    return sequence


def _choose_greedy(
    remaining: set[Hashable],
    portfolios: Mapping[Hashable, frozenset[str]],
    tie_break_keys: Mapping[Hashable, str],
    covered: set[str],
) -> tuple[Hashable, int, int, str, int, int]:
    marginal = {
        candidate: len(portfolios[candidate] - covered) for candidate in remaining
    }
    maximum_marginal = max(marginal.values())
    primary = {
        candidate
        for candidate in remaining
        if marginal[candidate] == maximum_marginal
    }
    maximum_total = max(len(portfolios[candidate]) for candidate in primary)
    secondary = {
        candidate
        for candidate in primary
        if len(portfolios[candidate]) == maximum_total
    }
    chosen = min(secondary, key=lambda candidate: tie_break_keys[candidate])
    if len(primary) == 1:
        applied = "none"
    elif len(secondary) == 1:
        applied = "total_eligible_record_count_desc"
    else:
        applied = (
            "total_eligible_record_count_desc_then_conservative_identity_key_asc"
        )
    return (
        chosen,
        marginal[chosen],
        len(portfolios[chosen]),
        applied,
        len(primary),
        len(secondary),
    )


def greedy_marginal_coverage(
    portfolios: Mapping[Hashable, set[str] | frozenset[str]],
    tie_break_keys: Mapping[Hashable, str],
    *,
    selection_limit: int | None = None,
) -> list[SelectionStep]:
    """Recompute marginal coverage at every step using the registered tie-break."""

    canonical = _validate_inputs(portfolios, tie_break_keys)
    if selection_limit is not None and selection_limit < 0:
        raise ValueError("selection_limit cannot be negative")

    remaining = set(canonical)
    covered: set[str] = set()
    sequence: list[SelectionStep] = []
    while remaining and (selection_limit is None or len(sequence) < selection_limit):
        (
            chosen,
            marginal,
            total,
            tie_applied,
            primary_size,
            secondary_size,
        ) = _choose_greedy(remaining, canonical, tie_break_keys, covered)
        remaining.remove(chosen)
        covered.update(canonical[chosen])
        sequence.append(
            SelectionStep(
                candidate=chosen,
                selection_step=len(sequence) + 1,
                owner_total_eligible_projects=total,
                marginal_unique_projects=marginal,
                cumulative_unique_projects=len(covered),
                tie_break_applied=tie_applied,
                primary_tie_size=primary_size,
                secondary_tie_size=secondary_size,
            )
        )
    return sequence


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_authoritative_inputs() -> AuthoritativeInputs:
    """Load through the tracked 8B builder so its frozen guards remain authoritative."""

    validation_dir = REPO_ROOT / "analysis/validation"
    if str(validation_dir) not in sys.path:
        sys.path.insert(0, str(validation_dir))
    import build_owner_sequence_8b as builder  # type: ignore[import-not-found]

    builder.verify_frozen_hashes()
    portfolios, _, tie_break_keys, _ = builder.load_8a()

    authority_paths = [
        builder.INCIDENCE_PATH,
        builder.RESTRICTED_FRAME_PATH,
        builder.DISPOSITIONS_PATH,
        builder.SEQUENCE_LOG_PATH,
        builder.IDENTIFIER_METADATA_PATH,
        builder.CONTACTABILITY_PROCEDURE,
        Path(builder.__file__).resolve(),
    ]
    hashes = {
        path.relative_to(REPO_ROOT).as_posix(): _sha256(path)
        for path in authority_paths
    }
    return AuthoritativeInputs(
        portfolios=dict(portfolios),
        tie_break_keys=dict(tie_break_keys),
        authoritative_source_hashes=hashes,
    )


def validate_expected_pure_curves(
    total_sequence: list[SelectionStep],
    greedy_sequence: list[SelectionStep],
) -> None:
    """Require exact agreement with the independently checked 25-step curves."""

    total_cumulative = tuple(
        item.cumulative_unique_projects for item in total_sequence
    )
    greedy_cumulative = tuple(
        item.cumulative_unique_projects for item in greedy_sequence
    )
    mismatch_count = sum(
        actual != expected
        for actual, expected in zip(
            total_cumulative, EXPECTED_TOTAL_CUMULATIVE, strict=False
        )
    ) + abs(len(total_cumulative) - len(EXPECTED_TOTAL_CUMULATIVE))
    mismatch_count += sum(
        actual != expected
        for actual, expected in zip(
            greedy_cumulative, EXPECTED_GREEDY_CUMULATIVE, strict=False
        )
    ) + abs(len(greedy_cumulative) - len(EXPECTED_GREEDY_CUMULATIVE))
    if mismatch_count:
        raise ValueError(
            "Pure algorithmic coverage reconciliation failed; "
            f"mismatching values={mismatch_count}"
        )


def validate_selection_portfolio_counts(
    sequence: list[SelectionStep],
    portfolios: Mapping[Hashable, set[str] | frozenset[str]],
) -> None:
    """Verify selected portfolio totals directly against the frozen incidence sets."""

    mismatch_count = sum(
        item.owner_total_eligible_projects != len(portfolios[item.candidate])
        for item in sequence
    )
    if mismatch_count:
        raise ValueError(
            "Selected portfolio totals do not reconcile to frozen incidence; "
            f"mismatching selections={mismatch_count}"
        )


def figure_data_rows(
    total_sequence: list[SelectionStep],
    greedy_sequence: list[SelectionStep],
    denominator: int,
) -> list[dict[str, object]]:
    if denominator <= 0:
        raise ValueError("Coverage denominator must be positive")
    rows: list[dict[str, object]] = []
    for strategy, sequence in (
        (STRATEGY_TOTAL, total_sequence),
        (STRATEGY_GREEDY, greedy_sequence),
    ):
        rows.append(
            {
                "strategy": strategy,
                "selection_step": 0,
                "owner_total_eligible_projects": "",
                "marginal_unique_projects": "",
                "cumulative_unique_projects": 0,
                "cumulative_coverage_pct": 0.0,
            }
        )
        for item in sequence:
            rows.append(
                {
                    "strategy": strategy,
                    "selection_step": item.selection_step,
                    "owner_total_eligible_projects": (
                        item.owner_total_eligible_projects
                    ),
                    "marginal_unique_projects": item.marginal_unique_projects,
                    "cumulative_unique_projects": item.cumulative_unique_projects,
                    "cumulative_coverage_pct": round(
                        100.0 * item.cumulative_unique_projects / denominator, 6
                    ),
                }
            )
    return rows


def validate_figure_data(rows: list[dict[str, object]], denominator: int) -> None:
    for strategy in (STRATEGY_TOTAL, STRATEGY_GREEDY):
        selected = [row for row in rows if row["strategy"] == strategy]
        if [int(row["selection_step"]) for row in selected] != list(range(len(selected))):
            raise ValueError("Figure-data selection steps are not contiguous")
        if selected[0]["cumulative_unique_projects"] != 0:
            raise ValueError("Figure-data cumulative coverage does not start at zero")
        previous = 0
        for row in selected[1:]:
            cumulative = int(row["cumulative_unique_projects"])
            marginal = int(row["marginal_unique_projects"])
            owner_total = int(row["owner_total_eligible_projects"])
            if marginal > owner_total:
                raise ValueError("Marginal contribution exceeds selected portfolio size")
            if marginal < 0 or cumulative != previous + marginal:
                raise ValueError("Figure-data cumulative and marginal counts differ")
            expected_pct = 100.0 * cumulative / denominator
            if abs(float(row["cumulative_coverage_pct"]) - expected_pct) > 0.000001:
                raise ValueError("Figure-data percentage denominator differs")
            previous = cumulative
        if strategy == STRATEGY_TOTAL:
            owner_totals = [
                int(row["owner_total_eligible_projects"]) for row in selected[1:]
            ]
            if owner_totals != sorted(owner_totals, reverse=True):
                raise ValueError("Fixed total-project ranking is not non-increasing")


def _git_value(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _base_metadata(
    figure_data_path: Path, inputs: AuthoritativeInputs
) -> dict[str, object]:
    return {
        "figure_data_file": figure_data_path.relative_to(REPO_ROOT).as_posix(),
        "generation_datetime": datetime.now(timezone.utc).isoformat(),
        "code_path": Path(__file__).relative_to(REPO_ROOT).as_posix(),
        "git_HEAD": _git_value("rev-parse", "HEAD"),
        "working_tree_dirty": bool(_git_value("status", "--short")),
        "authoritative_source_paths": list(inputs.authoritative_source_hashes),
        "authoritative_source_hashes": inputs.authoritative_source_hashes,
    }


def _write_algorithm_outputs(
    rows: list[dict[str, object]],
    inputs: AuthoritativeInputs,
) -> None:
    FIGURE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FIGURE_DATA_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FIGURE_DATA_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    project_count = len(set().union(*inputs.portfolios.values()))
    metadata = {
        **_base_metadata(FIGURE_DATA_PATH, inputs),
        "tie_break_rule_authority": [
            "analysis/validation/build_owner_sequence_8b.py",
            "preregistration_restricted/owner_candidate_frame_8a/"
            "owner_candidate_frame_restricted.csv",
            "preregistration/post_registration/procedures/"
            "owner_contactability_procedure_v1.1.md",
        ],
        "candidate_count": len(inputs.portfolios),
        "eligible_unique_project_count": project_count,
        "figure_sequence_endpoint": {
            "rule": "first 25 algorithmic candidate selections",
            "algorithmic_selections_per_strategy": PURE_SELECTION_TARGET,
        },
        "figure_outputs": {
            "coverage_comparison": [
                PNG_PATH.relative_to(REPO_ROOT).as_posix(),
                SVG_PATH.relative_to(REPO_ROOT).as_posix(),
            ],
            "paired_portfolio_and_marginal_comparison": [
                PORTFOLIO_COMPARISON_PNG_PATH.relative_to(REPO_ROOT).as_posix(),
                PORTFOLIO_COMPARISON_SVG_PATH.relative_to(REPO_ROOT).as_posix(),
            ],
        },
        "selection_step_definition": (
            "Algorithmic candidate selection position for both strategies."
        ),
        "contactability_handling": (
            "Ignored for both strategies; no disposition alters either sequence."
        ),
        "quantity_definitions": {
            "cumulative_unique_projects": (
                "Unique eligible projects covered by all algorithmic selections so far."
            ),
            "marginal_unique_projects": (
                "Projects in the selected researcher's portfolio not represented by "
                "any earlier selected researcher."
            ),
            "owner_total_eligible_projects": (
                "The selected researcher's full eligible portfolio, including projects "
                "already represented by earlier selected researchers."
            ),
        },
        "comparison_interpretation": (
            "Both strategies use the full 2,353-candidate incidence universe and "
            "the same 1,130-project denominator, isolating selection-algorithm "
            "behaviour under an all-candidates-reachable assumption."
        ),
        "strategy_definitions": {
            STRATEGY_TOTAL: (
                "Sort the full frozen candidate universe once by total eligible "
                "project count descending, then conservative identity key ascending; "
                "do not re-rank after selection."
            ),
            STRATEGY_GREEDY: (
                "At every algorithmic selection, choose maximum uncovered eligible-"
                "project gain, then total eligible-project count descending, then "
                "conservative identity key ascending; recompute after every selection."
            ),
        },
        "coverage_denominator": project_count,
        "expected_curve_reconciliation": {
            "steps_compared_per_strategy": PURE_SELECTION_TARGET,
            "mismatching_values": 0,
        },
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_outputs(*, include_pdf: bool = False) -> dict[str, object]:
    inputs = load_authoritative_inputs()
    project_count = len(set().union(*inputs.portfolios.values()))

    total = rank_by_total_projects(
        inputs.portfolios,
        inputs.tie_break_keys,
        selection_limit=PURE_SELECTION_TARGET,
    )
    pure_greedy = greedy_marginal_coverage(
        inputs.portfolios,
        inputs.tie_break_keys,
        selection_limit=PURE_SELECTION_TARGET,
    )
    if len(total) != len(pure_greedy):
        raise ValueError("Strategy endpoints differ")
    validate_expected_pure_curves(total, pure_greedy)
    validate_selection_portfolio_counts(total, inputs.portfolios)
    validate_selection_portfolio_counts(pure_greedy, inputs.portfolios)
    algorithm_rows = figure_data_rows(total, pure_greedy, project_count)
    validate_figure_data(algorithm_rows, project_count)
    _write_algorithm_outputs(algorithm_rows, inputs)

    from analysis.visualisations.plotting import (
        plot_owner_sampling_coverage,
        plot_owner_sampling_portfolio_vs_marginal,
    )

    plot_owner_sampling_coverage(
        FIGURE_DATA_PATH,
        png_path=PNG_PATH,
        svg_path=SVG_PATH,
        pdf_path=PDF_PATH if include_pdf else None,
    )
    plot_owner_sampling_portfolio_vs_marginal(
        FIGURE_DATA_PATH,
        png_path=PORTFOLIO_COMPARISON_PNG_PATH,
        svg_path=PORTFOLIO_COMPARISON_SVG_PATH,
        pdf_path=PORTFOLIO_COMPARISON_PDF_PATH if include_pdf else None,
    )
    return {
        "candidate_count": len(inputs.portfolios),
        "eligible_unique_project_count": project_count,
        "algorithm_figure_data_rows": len(algorithm_rows),
        "pure_algorithm_endpoints": {
            STRATEGY_TOTAL: total[-1].cumulative_unique_projects,
            STRATEGY_GREEDY: pure_greedy[-1].cumulative_unique_projects,
        },
        "outputs": [
            FIGURE_DATA_PATH.relative_to(REPO_ROOT).as_posix(),
            METADATA_PATH.relative_to(REPO_ROOT).as_posix(),
            PNG_PATH.relative_to(REPO_ROOT).as_posix(),
            SVG_PATH.relative_to(REPO_ROOT).as_posix(),
            PORTFOLIO_COMPARISON_PNG_PATH.relative_to(REPO_ROOT).as_posix(),
            PORTFOLIO_COMPARISON_SVG_PATH.relative_to(REPO_ROOT).as_posix(),
            *(
                [
                    PDF_PATH.relative_to(REPO_ROOT).as_posix(),
                    PORTFOLIO_COMPARISON_PDF_PATH.relative_to(REPO_ROOT).as_posix(),
                ]
                if include_pdf
                else []
            ),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also create a PDF (PNG and SVG are always generated).",
    )
    args = parser.parse_args()
    print(json.dumps(build_outputs(include_pdf=args.pdf), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
