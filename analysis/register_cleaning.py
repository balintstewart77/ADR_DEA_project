"""Canonical DEA register loading and cleaning.

This module owns raw-register preparation shared by the dashboard and the LLM
classification pipeline. LLM-specific prompt/cache/model logic should stay in
``llm_theme_analysis_v3.py``; dashboard-specific collection tagging should stay
in dashboard modules.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs_v3")

CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

DUPLICATE_REVIEW_FILE = os.path.join(OUTPUT_DIR, "quality", "duplicate_review_flagged.csv")

COLUMN_MAP = {
    "Project Number": "Project ID",
    "Project Name": "Title",
    "Accredited Researchers": "Researchers",
    "Legal Gateway": "Legal Basis",
    "Protected Data Accessed": "Datasets Used",
    "Processing Environment": "Secure Research Service",
}

try:
    from dashboard.dataset_normalisation import (
        _clean_datasets_text,
        iter_dataset_entries,
        normalise_dataset_name,
        normalise_provider_name,
    )
except ModuleNotFoundError:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))
    from dataset_normalisation import (  # type: ignore
        _clean_datasets_text,
        iter_dataset_entries,
        normalise_dataset_name,
        normalise_provider_name,
    )


@dataclass
class DuplicatePolicyResult:
    dataframe: pd.DataFrame
    tier1_rows_removed: int = 0
    tier2_merge_groups: int = 0
    tier2_input_rows: int = 0
    tier3_rows_flagged: int = 0
    tier2_project_ids: list[str] = field(default_factory=list)
    review_file: str = DUPLICATE_REVIEW_FILE

    @property
    def tier2_rows_removed(self) -> int:
        return self.tier2_input_rows - self.tier2_merge_groups


def load_raw_register(
    data_dir: str = DATA_DIR,
    candidate_files: Iterable[str] = CANDIDATE_FILES,
) -> tuple[pd.DataFrame, str]:
    for fname in candidate_files:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(f"[data] Loaded {len(df):,} rows from {fname}")
            return df, fname
    raise FileNotFoundError("No DEA projects CSV found in data/")


def normalise_register_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=COLUMN_MAP).copy()


def filter_dea_projects(df: pd.DataFrame, stats: dict | None = None) -> pd.DataFrame:
    out = df.copy()
    out["Accreditation Date"] = pd.to_datetime(out["Accreditation Date"], errors="coerce")

    n_before = len(out)
    out = out.dropna(subset=["Accreditation Date", "Title"])
    if stats is not None:
        stats["dropped_no_date_or_title"] = n_before - len(out)
        stats["dropped_no_date"] = stats["dropped_no_date_or_title"]
        stats["rows_after_required_fields"] = len(out)

    if "Legal Basis" in out.columns:
        n_before = len(out)
        out = out[out["Legal Basis"].astype(str).str.contains("Digital Economy Act", na=False, case=False)]
        if stats is not None:
            stats["dropped_non_dea"] = n_before - len(out)
    elif stats is not None:
        stats["dropped_non_dea"] = 0

    if stats is not None:
        stats["rows_after_dea_filter"] = len(out)
    return out


def _normalise_duplicate_text(value) -> str:
    """Normalise text for duplicate comparison without changing retained values."""
    if pd.isna(value):
        return ""
    text = str(value)
    text = text.replace("_x000D_", " ").replace("\u00a0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _normalise_title_key(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalise_date_key(value) -> str:
    if pd.isna(value):
        return ""
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return _normalise_duplicate_text(value)
    return parsed.strftime("%Y-%m-%d")


def _dataset_entry_key(provider: str, part: str) -> tuple[str, str]:
    provider_name = normalise_provider_name(provider)
    dataset_name = normalise_dataset_name(part)
    return (
        _normalise_duplicate_text(provider_name),
        _normalise_duplicate_text(dataset_name),
    )


def _dataset_entry_display(provider: str, part: str) -> str:
    provider_name = normalise_provider_name(provider)
    dataset_name = normalise_dataset_name(part)
    return f"{provider_name}: {dataset_name}" if provider_name else dataset_name


def _dataset_entries_for_merge(raw: str) -> list[tuple[tuple[str, str], str]]:
    """Return parser-derived dataset entries plus nonempty parser-dropped lines."""
    parsed_entries = list(iter_dataset_entries(raw))
    parsed_line_keys = {
        _normalise_duplicate_text(line)
        for line, _, _ in parsed_entries
        if line
    }
    entries: list[tuple[tuple[str, str], str]] = []
    for line, provider, part in parsed_entries:
        entries.append((_dataset_entry_key(provider, part), _dataset_entry_display(provider, part)))

    cleaned = _clean_datasets_text(raw)
    for line in cleaned.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        if _normalise_duplicate_text(line) in parsed_line_keys:
            continue
        provider, rest = line.split(":", 1)
        rest = re.sub(r"\s+", " ", rest).strip(" ,;:")
        if not rest:
            continue
        provider = re.sub(r"\s+", " ", provider).strip()
        display = f"{provider}: {rest}" if provider else rest
        key = (_normalise_duplicate_text(provider), _normalise_duplicate_text(rest))
        entries.append((key, display))

    return entries


def _merge_dataset_values(values: pd.Series) -> str:
    """Union dataset entries using the shared dataset parser/normaliser."""
    merged: list[str] = []
    seen: set[tuple[str, str]] = set()
    raw_seen: set[str] = set()

    for value in values:
        raw = "" if pd.isna(value) else str(value)
        parsed_entries = _dataset_entries_for_merge(raw)
        if parsed_entries:
            for key, display in parsed_entries:
                if key in seen:
                    continue
                seen.add(key)
                merged.append(display)
            continue

        # Fallback only when the shared parser cannot emit an entry; keeps data
        # visible rather than silently dropping an unusual raw dataset string.
        raw_key = _normalise_duplicate_text(raw)
        if raw_key and raw_key not in raw_seen:
            raw_seen.add(raw_key)
            merged.append(" ".join(raw.split()))

    return "\n".join(merged)


def _split_researcher_entries(value) -> list[str]:
    if pd.isna(value):
        return []
    text = str(value)
    text = text.replace("_x000D_", "\n").replace("\r", "\n")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\u00a0", " ")
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.split("\n")
        if re.sub(r"\s+", " ", line).strip()
    ]


def _merge_researcher_values(values: pd.Series) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for value in values:
        for entry in _split_researcher_entries(value):
            key = _normalise_duplicate_text(entry)
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)
    return "\n".join(merged)


def _inconsistent_nonmerge_columns(group: pd.DataFrame) -> list[str]:
    allowed_to_differ = {
        "Project ID",
        "Title",
        "Accreditation Date",
        "Datasets Used",
        "Researchers",
        "_title_key",
    }
    inconsistent: list[str] = []
    for col in group.columns:
        if col in allowed_to_differ:
            continue
        values = group[col].map(_normalise_duplicate_text)
        if values.nunique(dropna=False) > 1:
            inconsistent.append(col)
    return inconsistent


def _append_duplicate_review_rows(
    flagged_rows: list[pd.DataFrame],
    group: pd.DataFrame,
    reason: str,
) -> None:
    review = group.drop(columns=["_title_key"], errors="ignore").copy()
    review.insert(0, "duplicate_flag_reason", reason)
    review.insert(1, "duplicate_group_size", len(group))
    flagged_rows.append(review)


def write_duplicate_review(
    flagged_rows: list[pd.DataFrame],
    columns: list[str],
    review_file: str = DUPLICATE_REVIEW_FILE,
) -> None:
    os.makedirs(os.path.dirname(review_file), exist_ok=True)
    if flagged_rows:
        review = pd.concat(flagged_rows, ignore_index=True)
    else:
        review = pd.DataFrame(columns=["duplicate_flag_reason", "duplicate_group_size", *columns])
    review.to_csv(review_file, index=False, encoding="utf-8-sig")


def apply_duplicate_policy(
    df: pd.DataFrame,
    *,
    review_file: str = DUPLICATE_REVIEW_FILE,
    stats: dict | None = None,
    verbose: bool = True,
) -> DuplicatePolicyResult:
    """Resolve same-ID/same-title duplicates without silently dropping content."""
    if "Project ID" not in df.columns or "Title" not in df.columns:
        out = df.copy().drop_duplicates().reset_index(drop=True)
        result = DuplicatePolicyResult(dataframe=out, review_file=review_file)
        if stats is not None:
            _update_duplicate_stats(stats, result)
        return result

    working = df.copy().reset_index(drop=True)
    original_columns = list(working.columns)
    working["_title_key"] = working["Title"].apply(_normalise_title_key)

    retained_rows: list[pd.Series] = []
    flagged_rows: list[pd.DataFrame] = []
    tier1_removed = 0
    tier2_groups = 0
    tier2_input_rows = 0
    tier2_project_ids: list[str] = []

    grouped = working.groupby(["Project ID", "_title_key"], sort=False, dropna=False)
    for (_, _), group in grouped:
        if len(group) == 1:
            retained_rows.append(group.iloc[0].drop(labels=["_title_key"]))
            continue

        date_keys = group["Accreditation Date"].map(_normalise_date_key)
        if date_keys.nunique(dropna=False) > 1:
            reason = "same Project ID + title, but different Accreditation Date values"
            _append_duplicate_review_rows(flagged_rows, group, reason)
            for _, row in group.iterrows():
                retained_rows.append(row.drop(labels=["_title_key"]))
            continue

        inconsistent_cols = _inconsistent_nonmerge_columns(group)
        if inconsistent_cols:
            reason = (
                "same Project ID + title + accreditation date, but non-merge "
                f"columns differ: {', '.join(inconsistent_cols)}"
            )
            if verbose:
                print(
                    f"[duplicates] WARNING: ambiguous duplicate group "
                    f"{group.iloc[0]['Project ID']} flagged ({reason})"
                )
            _append_duplicate_review_rows(flagged_rows, group, reason)
            for _, row in group.iterrows():
                retained_rows.append(row.drop(labels=["_title_key"]))
            continue

        dataset_keys = group["Datasets Used"].map(_normalise_duplicate_text)
        researcher_keys = group["Researchers"].map(_normalise_duplicate_text)
        if dataset_keys.nunique(dropna=False) == 1 and researcher_keys.nunique(dropna=False) == 1:
            retained_rows.append(group.iloc[0].drop(labels=["_title_key"]))
            tier1_removed += len(group) - 1
            continue

        merged = group.iloc[0].copy()
        merged["Datasets Used"] = _merge_dataset_values(group["Datasets Used"])
        merged["Researchers"] = _merge_researcher_values(group["Researchers"])
        retained_rows.append(merged.drop(labels=["_title_key"]))
        tier2_groups += 1
        tier2_input_rows += len(group)
        tier2_project_ids.append(str(merged["Project ID"]))
        if verbose:
            print(
                f"[duplicates] Tier 2 merge: {merged['Project ID']} "
                f"({len(group)} rows) - {str(merged['Title'])[:100]}"
            )

    out = pd.DataFrame(retained_rows, columns=original_columns).reset_index(drop=True)
    write_duplicate_review(flagged_rows, original_columns, review_file)

    result = DuplicatePolicyResult(
        dataframe=out,
        tier1_rows_removed=tier1_removed,
        tier2_merge_groups=tier2_groups,
        tier2_input_rows=tier2_input_rows,
        tier3_rows_flagged=sum(len(rows) for rows in flagged_rows),
        tier2_project_ids=tier2_project_ids,
        review_file=review_file,
    )
    if stats is not None:
        _update_duplicate_stats(stats, result)
    if verbose:
        print(
            "[duplicates] "
            f"input rows: {len(df):,}; output rows: {len(out):,}; "
            f"Tier 1 duplicate rows removed: {result.tier1_rows_removed:,}; "
            f"Tier 2 merge groups: {result.tier2_merge_groups:,} "
            f"({result.tier2_input_rows:,} input rows); "
            f"Tier 3 rows flagged: {result.tier3_rows_flagged:,}"
        )
        print(f"[duplicates] Tier 3 review file: {review_file}")
    return result


def _update_duplicate_stats(stats: dict, result: DuplicatePolicyResult) -> None:
    stats["duplicate_tier1_rows_removed"] = result.tier1_rows_removed
    stats["duplicate_tier2_merge_groups"] = result.tier2_merge_groups
    stats["duplicate_tier2_input_rows"] = result.tier2_input_rows
    stats["duplicate_tier2_rows_removed"] = result.tier2_rows_removed
    stats["duplicate_tier3_rows_flagged"] = result.tier3_rows_flagged
    stats["duplicate_review_file"] = result.review_file
    stats["rows_after_duplicate_policy"] = len(result.dataframe)

    # Backward-compatible aliases for any callers not yet updated.
    stats["dropped_exact_duplicates"] = result.tier1_rows_removed
    stats["dropped_same_id_same_title"] = result.tier1_rows_removed + result.tier2_rows_removed
    stats["dropped_special_duplicate_rows"] = 0
    stats["after_filters"] = len(result.dataframe)


def assign_record_ids(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Project ID"] = (
        out["Project ID"].astype(str)
        .str.strip()
        .str.replace(r"\s*CLOSED\s*$", "", regex=True)
        .str.strip()
    )

    duplicated_ids = out["Project ID"].duplicated(keep=False)
    out["Record ID"] = out["Project ID"]
    if duplicated_ids.any():
        for pid, grp in out.loc[duplicated_ids].groupby("Project ID", sort=False):
            for i, idx in enumerate(grp.index):
                out.loc[idx, "Record ID"] = f"{pid}/{chr(ord('a') + i)}"
    return out


def add_time_fields(df: pd.DataFrame, *, include_quarter_date: bool = False) -> pd.DataFrame:
    out = df.copy()
    out["Year"] = out["Accreditation Date"].dt.year
    out["Quarter"] = out["Accreditation Date"].dt.to_period("Q")
    out["Quarter Label"] = out["Quarter"].dt.strftime("Q%q %Y")
    if include_quarter_date:
        out["quarter_date"] = out["Quarter"].dt.to_timestamp()
    return out


def clean_register_dataframe(
    df_raw: pd.DataFrame,
    *,
    output_dir: str = OUTPUT_DIR,
    include_quarter_date: bool = False,
    include_project_row_id: bool = False,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict]:
    output_dir = os.path.abspath(os.path.normpath(output_dir))
    stats: dict = {"raw_loaded": len(df_raw)}
    df = normalise_register_columns(df_raw)
    df = filter_dea_projects(df, stats)
    review_file = os.path.join(output_dir, "quality", "duplicate_review_flagged.csv")
    duplicate_result = apply_duplicate_policy(df, review_file=review_file, stats=stats, verbose=verbose)
    df = assign_record_ids(duplicate_result.dataframe)
    df = add_time_fields(df, include_quarter_date=include_quarter_date)
    if include_project_row_id:
        df["Project Row ID"] = [f"proj-{i:04d}" for i in range(len(df))]
    stats["final_rows"] = len(df)
    return df.reset_index(drop=True), stats


def load_clean_register(
    data_dir: str = DATA_DIR,
    *,
    candidate_files: Iterable[str] = CANDIDATE_FILES,
    output_dir: str = OUTPUT_DIR,
    include_quarter_date: bool = False,
    include_project_row_id: bool = False,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict, str]:
    df_raw, source_file = load_raw_register(data_dir, candidate_files)
    df, stats = clean_register_dataframe(
        df_raw,
        output_dir=output_dir,
        include_quarter_date=include_quarter_date,
        include_project_row_id=include_project_row_id,
        verbose=verbose,
    )
    return df, stats, source_file
