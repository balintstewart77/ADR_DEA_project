"""One-off migration to content-stable Record IDs.

``assign_record_ids`` previously lettered duplicate Project IDs (``/a``,
``/b`` ...) by row position in the source file; it now orders them by content
(date, title, datasets, researchers), so a register re-publication that
reorders rows cannot silently re-letter records. This script relabels the
artefacts that were generated under the positional scheme:

- ``layer_classifications.csv`` files: remapped by content — each suffixed row
  is matched to the register row with the same Project ID and Title, and takes
  that row's stable Record ID. Idempotent.
- ``register_properties.csv``: has no content columns, so each suffixed row is
  matched by comparing its facet values against a freshly derived properties
  table keyed by stable IDs. Pairs whose facets are identical need no change;
  pairs that cannot be matched consistently are reported and left untouched.
  Idempotent.

Run with no arguments for a dry run; pass --apply to write changes.
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

try:
    from analysis.register_cleaning import (
        _normalise_duplicate_text,
        load_clean_register,
    )
    from analysis.derive_register_properties import (
        REFERENCE_PATH,
        build_indexes,
        derive_properties,
        load_reference,
        parse_register_entities,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from analysis.register_cleaning import (  # type: ignore
        _normalise_duplicate_text,
        load_clean_register,
    )
    from analysis.derive_register_properties import (  # type: ignore
        REFERENCE_PATH,
        build_indexes,
        derive_properties,
        load_reference,
        parse_register_entities,
    )

ANALYSIS_DIR = Path(__file__).resolve().parent
FACET_COLUMNS = [
    "record_linkage",
    "matched_products",
    "record_linkage_component_domains",
    "dataset_collection_methods",
    "dataset_temporal_structures",
    "dataset_units",
    "researcher_sectors",
]


def _load_stable_register() -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        df, _stats, _source = load_clean_register(
            output_dir=tmp, include_quarter_date=True, verbose=False
        )
    return df


def _suffixed(record_id: str, project_id: str) -> bool:
    return str(record_id) != str(project_id)


def _content_key(project_id, title) -> tuple[str, str]:
    return (str(project_id).strip(), _normalise_duplicate_text(title))


def _stable_id_by_content(register: pd.DataFrame) -> dict[tuple[str, str], str]:
    """(Project ID, normalised Title) -> stable Record ID for duplicate groups."""
    mapping: dict[tuple[str, str], str] = {}
    dup_mask = register["Project ID"].duplicated(keep=False)
    for _, row in register.loc[dup_mask].iterrows():
        key = _content_key(row["Project ID"], row["Title"])
        if key in mapping:
            raise ValueError(
                f"Ambiguous duplicate group {key[0]}: two records share a title; "
                "content-based remapping cannot distinguish them"
            )
        mapping[key] = str(row["Record ID"])
    return mapping


def migrate_classifications_csv(
    path: str,
    content_map: dict[tuple[str, str], str],
    *,
    apply: bool,
) -> tuple[int, list[str]]:
    """Returns (rows changed, problems)."""
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if "Record ID" not in df.columns or "Project ID" not in df.columns or "Title" not in df.columns:
        return 0, [f"{path}: missing Record ID / Project ID / Title columns; skipped"]

    changed = 0
    problems: list[str] = []
    for idx, row in df.iterrows():
        if not _suffixed(row["Record ID"], row["Project ID"]):
            continue
        key = _content_key(row["Project ID"], row["Title"])
        stable_id = content_map.get(key)
        if stable_id is None:
            problems.append(
                f"{path}: no register row matches {row['Record ID']} "
                f"({str(row['Title'])[:60]!r}); left unchanged"
            )
            continue
        if stable_id != row["Record ID"]:
            df.loc[idx, "Record ID"] = stable_id
            changed += 1

    if changed and apply:
        df.to_csv(path, index=False, encoding="utf-8-sig")
    return changed, problems


def migrate_register_properties(
    path: str,
    register: pd.DataFrame,
    *,
    apply: bool,
) -> tuple[int, list[str]]:
    """Relabel suffixed rows by matching facets against a fresh derivation."""
    committed = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    if "Record ID" not in committed.columns:
        return 0, [f"{path}: missing Record ID column; skipped"]

    reference = load_reference(REFERENCE_PATH)
    indexes = build_indexes(reference)
    datasets, institutions = parse_register_entities(register)
    fresh = derive_properties(register, datasets, institutions, indexes)
    fresh_by_id = fresh.set_index("Record ID")

    dup_mask = register["Project ID"].duplicated(keep=False)
    groups: dict[str, list[str]] = {}
    for _, row in register.loc[dup_mask].iterrows():
        groups.setdefault(str(row["Project ID"]), []).append(str(row["Record ID"]))

    changed = 0
    problems: list[str] = []
    facet_cols = [col for col in FACET_COLUMNS if col in committed.columns and col in fresh.columns]

    for project_id, stable_ids in groups.items():
        member_mask = committed["Record ID"].astype(str).str.startswith(f"{project_id}/")
        member_idx = list(committed.index[member_mask])
        if len(member_idx) != len(stable_ids):
            problems.append(
                f"{path}: {project_id} has {len(member_idx)} rows but the register "
                f"has {len(stable_ids)}; left unchanged"
            )
            continue

        fresh_facets = {
            sid: tuple(str(fresh_by_id.loc[sid, col]) for col in facet_cols)
            for sid in stable_ids
        }
        if len(set(fresh_facets.values())) == 1:
            # All group members derive identical facets: any labelling is
            # equivalent, so the committed rows are already correct.
            continue

        assignment: dict[int, str] = {}
        used: set[str] = set()
        ok = True
        for idx in member_idx:
            row_facets = tuple(str(committed.loc[idx, col]) for col in facet_cols)
            matches = [
                sid for sid, facets in fresh_facets.items()
                if facets == row_facets and sid not in used
            ]
            if len(matches) != 1:
                ok = False
                break
            assignment[idx] = matches[0]
            used.add(matches[0])
        if not ok:
            problems.append(
                f"{path}: {project_id} facets do not match a fresh derivation "
                "(reference may have changed since this file was generated); "
                "left unchanged - regenerate with derive_register_properties"
            )
            continue

        for idx, stable_id in assignment.items():
            if str(committed.loc[idx, "Record ID"]) != stable_id:
                committed.loc[idx, "Record ID"] = stable_id
                changed += 1

    if changed and apply:
        committed.to_csv(path, index=False, encoding="utf-8-sig")
    return changed, problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate artefacts to content-stable Record IDs")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = parser.parse_args()

    register = _load_stable_register()
    content_map = _stable_id_by_content(register)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] register has {len(content_map)} records in duplicate-ID groups")

    all_problems: list[str] = []
    total_changed = 0

    for path in sorted(glob.glob(str(ANALYSIS_DIR / "outputs*" / "layer_classifications.csv"))):
        changed, problems = migrate_classifications_csv(path, content_map, apply=args.apply)
        total_changed += changed
        all_problems.extend(problems)
        print(f"  {os.path.relpath(path, ANALYSIS_DIR)}: {changed} Record IDs relabelled")

    properties_path = ANALYSIS_DIR / "outputs_deterministic_rc2" / "register_properties.csv"
    if properties_path.exists():
        changed, problems = migrate_register_properties(
            str(properties_path), register, apply=args.apply
        )
        total_changed += changed
        all_problems.extend(problems)
        print(f"  {os.path.relpath(properties_path, ANALYSIS_DIR)}: {changed} Record IDs relabelled")

    for problem in all_problems:
        print(f"  [problem] {problem}")
    print(
        f"[{mode}] {total_changed} Record IDs relabelled across artefacts; "
        f"{len(all_problems)} problems"
    )
    if not args.apply and total_changed:
        print("Re-run with --apply to write these changes.")


if __name__ == "__main__":
    main()
