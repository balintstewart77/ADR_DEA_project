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
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs_v3")

# Legacy fallback used only when data/register_manifest.json is absent.
# The manifest is the single source of truth for which extract to load;
# add new register versions with: python -m analysis.register_manifest add ...
CANDIDATE_FILES = [
    "dea_accredited_projects_20260325.csv",
    "dea_accredited_projects.csv",
]

DUPLICATE_REVIEW_FILE = os.path.join(OUTPUT_DIR, "quality", "duplicate_review_flagged.csv")
REGISTER_DUPLICATE_RULINGS_FILE = os.path.join(PROJECT_ROOT, "analysis", "register_duplicate_rulings.yaml")
DUPLICATE_RULINGS_AUDIT_FILE = os.path.join(OUTPUT_DIR, "quality", "duplicate_rulings_audit.csv")

RETAINED_DUPLICATE_RULING_TYPES = {
    "project_number_collision",
    "related_distinct_entries_same_project_id",
}
ALL_DUPLICATE_RULING_TYPES = {
    "duplicate_update",
    *RETAINED_DUPLICATE_RULING_TYPES,
}

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
        _clean_title_text,
        iter_dataset_entries,
        normalise_dataset_name,
        normalise_provider_name,
    )
except ModuleNotFoundError:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))
    from dataset_normalisation import (  # type: ignore
        _clean_datasets_text,
        _clean_title_text,
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


@dataclass
class DuplicateRulingsResult:
    dataframe: pd.DataFrame
    audit: pd.DataFrame
    audit_file: str = DUPLICATE_RULINGS_AUDIT_FILE
    merged_source_rows: int = 0
    retained_project_ids: list[str] = field(default_factory=list)


def load_raw_register(
    data_dir: str = DATA_DIR,
    candidate_files: Iterable[str] | None = None,
    *,
    version: str = "current",
) -> tuple[pd.DataFrame, str]:
    """Load a raw register extract.

    Resolution order:
    1. ``candidate_files``, when passed explicitly (back-compat / tests).
    2. ``data/register_manifest.json`` — the ``version`` argument selects a
       manifest version ("current" by default).
    3. The legacy ``CANDIDATE_FILES`` list, when no manifest exists.
    """
    if candidate_files is None:
        try:
            from analysis.register_manifest import resolve_register_csv
        except ModuleNotFoundError:
            from register_manifest import resolve_register_csv  # type: ignore
        try:
            path, record = resolve_register_csv(data_dir, version)
        except FileNotFoundError:
            if version != "current":
                raise  # an explicit version request must not fall back silently
            candidate_files = CANDIDATE_FILES
        else:
            df = pd.read_csv(path, encoding="utf-8-sig")
            print(
                f"[data] Loaded {len(df):,} rows from {record['csv']} "
                f"(register version {record['version']})"
            )
            return df, record["csv"]

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
    text = re.sub(r"\s*_x000D_\s*", " ", text, flags=re.IGNORECASE)
    text = text.replace("\r", " ").replace("\n", " ").replace("\u00a0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _clean_single_line_register_text(value):
    if pd.isna(value):
        return value
    text = str(value)
    text = re.sub(r"\s*_x000D_\s*", " ", text, flags=re.IGNORECASE)
    text = text.replace("\r", " ").replace("\n", " ").replace("\u00a0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    text = re.sub(r"\s*_x000D_\s*(?=,)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*_x000D_\s*", "\n", text, flags=re.IGNORECASE)
    text = text.replace("\r", "\n")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\u00a0", " ")
    return [
        re.sub(r"\s+", " ", line).strip()
        for line in text.split("\n")
        if re.sub(r"\s+", " ", line).strip()
    ]


def _clean_researcher_text(value):
    if pd.isna(value):
        return value
    text = str(value)
    text = re.sub(r"\s*_x000D_\s*(?=,)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*_x000D_\s*", "\n", text, flags=re.IGNORECASE)
    text = text.replace("\r", "\n")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t\f\v]*\n[ \t\f\v]*", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return "\n".join(line.strip() for line in text.split("\n") if line.strip())


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


def load_duplicate_rulings(path: str = REGISTER_DUPLICATE_RULINGS_FILE) -> dict[str, dict]:
    """Load reviewed rulings keyed by Project ID."""
    with open(path, "r", encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}
    rulings = payload.get("rulings")
    if not isinstance(rulings, list):
        raise ValueError(f"{path} must contain a 'rulings' list")

    by_project_id: dict[str, dict] = {}
    for ruling in rulings:
        if not isinstance(ruling, dict):
            raise ValueError(f"{path} contains a non-object ruling")
        project_id = str(ruling.get("project_id") or "").strip()
        ruling_type = str(ruling.get("ruling_type") or "").strip()
        if not project_id:
            raise ValueError(f"{path} contains a ruling without project_id")
        if ruling_type not in ALL_DUPLICATE_RULING_TYPES:
            raise ValueError(
                f"{path} ruling for {project_id} has invalid ruling_type {ruling_type!r}"
            )
        if project_id in by_project_id:
            raise ValueError(f"{path} contains duplicate rulings for {project_id}")
        by_project_id[project_id] = ruling
    return by_project_id


def _normalised_match_value(col: str, value) -> str:
    if col == "Accreditation Date":
        return _normalise_date_key(value)
    if col == "Title":
        return _clean_title_text(value) if not pd.isna(value) else ""
    if col == "Datasets Used":
        return _normalise_duplicate_text(_clean_datasets_text(value))
    if col in {"Researchers", "Legal Basis", "Secure Research Service"}:
        return _normalise_duplicate_text(value)
    return _normalise_duplicate_text(value)


def _match_column_name(key: str) -> str:
    return {
        "project_id": "Project ID",
        "title": "Title",
        "researchers": "Researchers",
        "legal_basis": "Legal Basis",
        "datasets_used": "Datasets Used",
        "secure_research_service": "Secure Research Service",
        "accreditation_date": "Accreditation Date",
    }.get(key, key)


def _match_rows_for_criteria(group: pd.DataFrame, criteria: dict, *, project_id: str) -> list[int]:
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError(f"Duplicate ruling for {project_id} has an empty source match")

    mask = pd.Series(True, index=group.index)
    for raw_col, expected in criteria.items():
        col = _match_column_name(str(raw_col))
        if col not in group.columns:
            raise ValueError(
                f"Duplicate ruling for {project_id} references missing match column {col!r}"
            )
        expected_key = _normalised_match_value(col, expected)
        values = group[col].map(lambda value: _normalised_match_value(col, value))
        mask &= values.eq(expected_key)
    return group.index[mask].tolist()


def _require_unique_matches(
    group: pd.DataFrame,
    matches: list[dict],
    *,
    project_id: str,
) -> list[int]:
    matched_indexes: list[int] = []
    for criteria in matches:
        indexes = _match_rows_for_criteria(group, criteria, project_id=project_id)
        if not indexes:
            raise ValueError(f"Duplicate ruling for {project_id} matched zero rows: {criteria}")
        if len(indexes) > 1:
            raise ValueError(
                f"Duplicate ruling for {project_id} matched multiple rows: {criteria}"
            )
        matched_indexes.append(indexes[0])
    if len(set(matched_indexes)) != len(matched_indexes):
        raise ValueError(f"Duplicate ruling for {project_id} matches the same row more than once")
    if set(matched_indexes) != set(group.index):
        missing = sorted(set(group.index) - set(matched_indexes))
        extra = sorted(set(matched_indexes) - set(group.index))
        raise ValueError(
            f"Duplicate ruling for {project_id} does not cover the residual duplicate group "
            f"(missing={missing}, extra={extra})"
        )
    return matched_indexes


def _required_equal_key(col: str, value) -> str:
    if col == "Datasets Used":
        return _normalise_duplicate_text(_clean_datasets_text(value))
    if col == "Accreditation Date":
        return _normalise_date_key(value)
    return _normalise_duplicate_text(value)


def _single_consistent_value(group: pd.DataFrame, col: str, *, project_id: str):
    values = group[col]
    keys = values.map(lambda value: _required_equal_key(col, value))
    nonempty_keys = {key for key in keys if key}
    if len(nonempty_keys) > 1:
        raise ValueError(
            f"Duplicate update ruling for {project_id} has conflicting values in {col!r}"
        )
    for value in values:
        if not pd.isna(value) and str(value).strip():
            return value
    return values.iloc[0]


def _merge_duplicate_update_group(group: pd.DataFrame, ruling: dict) -> pd.Series:
    project_id = str(ruling["project_id"])
    merge_policy = ruling.get("merge_policy") or {}
    require_equal = list(merge_policy.get("require_equal") or [])
    for col in require_equal:
        if col not in group.columns:
            raise ValueError(
                f"Duplicate update ruling for {project_id} requires missing column {col!r}"
            )

    merged = group.iloc[0].copy()
    for col in group.columns:
        if col == "Title":
            merged[col] = ruling.get("canonical_title") or group.iloc[0][col]
        elif col == "Researchers":
            merged[col] = _merge_researcher_values(group[col])
        elif col == "Record ID":
            merged[col] = ruling.get("canonical_record_id") or project_id
        elif col in require_equal:
            merged[col] = _single_consistent_value(group, col, project_id=project_id)
        else:
            keys = group[col].map(_normalise_duplicate_text)
            nonempty = [value for value in group[col] if not pd.isna(value) and str(value).strip()]
            if keys.nunique(dropna=False) <= 1:
                merged[col] = group.iloc[0][col]
            elif len(nonempty) == 1:
                merged[col] = nonempty[0]
            else:
                raise ValueError(
                    f"Duplicate update ruling for {project_id} has no merge rule for "
                    f"conflicting column {col!r}"
                )
    merged["Record ID"] = ruling.get("canonical_record_id") or project_id
    return merged


def _audit_row(
    group: pd.DataFrame,
    ruling: dict,
    *,
    action: str,
    record_ids: list[str],
    canonical_title: str = "",
) -> dict:
    return {
        "Project ID": str(ruling["project_id"]),
        "ruling_type": str(ruling["ruling_type"]),
        "action": action,
        "source_row_indexes": "; ".join(str(idx) for idx in group.index.tolist()),
        "source_titles": " | ".join(_clean_title_text(value) for value in group["Title"].tolist()),
        "resulting_record_ids": "; ".join(record_ids),
        "canonical_title": canonical_title,
        "source_row_count": len(group),
        "note": str(ruling.get("note") or "").strip(),
    }


def write_duplicate_rulings_audit(audit: pd.DataFrame, audit_file: str) -> None:
    os.makedirs(os.path.dirname(audit_file), exist_ok=True)
    audit.to_csv(audit_file, index=False, encoding="utf-8-sig")


def apply_reviewed_duplicate_rulings(
    df: pd.DataFrame,
    *,
    rulings_path: str = REGISTER_DUPLICATE_RULINGS_FILE,
    audit_file: str = DUPLICATE_RULINGS_AUDIT_FILE,
    stats: dict | None = None,
) -> DuplicateRulingsResult:
    """Apply reviewed rulings to residual duplicate Project IDs."""
    if "Project ID" not in df.columns or "Title" not in df.columns:
        out = df.copy()
        audit = pd.DataFrame()
        write_duplicate_rulings_audit(audit, audit_file)
        return DuplicateRulingsResult(dataframe=out, audit=audit, audit_file=audit_file)

    rulings = load_duplicate_rulings(rulings_path)
    working = df.copy().reset_index(drop=True)
    if "Record ID" not in working.columns:
        working["Record ID"] = pd.NA

    duplicate_ids = set(
        working.loc[working["Project ID"].astype(str).duplicated(keep=False), "Project ID"]
        .astype(str)
        .unique()
    )
    absent_rulings = sorted(set(rulings) - duplicate_ids)
    if absent_rulings:
        raise ValueError(
            "Duplicate rulings reference Project IDs not present as residual duplicates: "
            + ", ".join(absent_rulings)
        )
    missing_rulings = sorted(duplicate_ids - set(rulings))
    if missing_rulings:
        raise ValueError(
            "Residual duplicate Project IDs lack reviewed rulings: "
            + ", ".join(missing_rulings)
        )

    retained_rows: list[pd.Series] = []
    audit_rows: list[dict] = []
    merged_source_rows = 0
    retained_project_ids: list[str] = []

    for project_id, group in working.groupby("Project ID", sort=False, dropna=False):
        project_id = str(project_id)
        if project_id not in duplicate_ids:
            row = group.iloc[0].copy()
            row["Record ID"] = project_id
            retained_rows.append(row)
            continue

        ruling = rulings[project_id]
        ruling_type = str(ruling["ruling_type"])
        if ruling_type == "duplicate_update":
            matches = ruling.get("source_matches") or []
            if len(matches) != len(group):
                raise ValueError(
                    f"Duplicate update ruling for {project_id} expected {len(matches)} "
                    f"source matches but residual group has {len(group)} rows"
                )
            matched_indexes = _require_unique_matches(group, matches, project_id=project_id)
            matched_group = group.loc[matched_indexes]
            merged = _merge_duplicate_update_group(matched_group, ruling)
            retained_rows.append(merged)
            merged_source_rows += len(group)
            audit_rows.append(_audit_row(
                group,
                ruling,
                action="merged",
                record_ids=[str(merged["Record ID"])],
                canonical_title=str(merged["Title"]),
            ))
            continue

        entries = ruling.get("entries") or []
        if ruling_type not in RETAINED_DUPLICATE_RULING_TYPES:
            raise ValueError(f"Unsupported retained duplicate ruling type for {project_id}: {ruling_type}")
        if len(entries) != len(group):
            raise ValueError(
                f"Retained duplicate ruling for {project_id} has {len(entries)} entries "
                f"but residual group has {len(group)} rows"
            )
        match_criteria = [
            {key: value for key, value in entry.items() if key != "record_id"}
            for entry in entries
        ]
        matched_indexes = _require_unique_matches(group, match_criteria, project_id=project_id)
        assigned_ids: list[str] = []
        for entry, idx in zip(entries, matched_indexes):
            record_id = str(entry.get("record_id") or "").strip()
            if not record_id:
                raise ValueError(f"Retained duplicate ruling for {project_id} has an entry without record_id")
            row = group.loc[idx].copy()
            row["Record ID"] = record_id
            retained_rows.append(row)
            assigned_ids.append(record_id)
        retained_project_ids.append(project_id)
        audit_rows.append(_audit_row(
            group,
            ruling,
            action="retained",
            record_ids=assigned_ids,
            canonical_title="",
        ))

    out = pd.DataFrame(retained_rows, columns=working.columns).reset_index(drop=True)
    if out["Record ID"].isna().any() or (out["Record ID"].astype(str).str.strip() == "").any():
        raise ValueError("Some cleaned rows have no Record ID after duplicate rulings")
    duplicate_record_ids = out.loc[out["Record ID"].astype(str).duplicated(), "Record ID"].astype(str)
    if not duplicate_record_ids.empty:
        raise ValueError(
            "Duplicate Record IDs after duplicate rulings: "
            + ", ".join(sorted(duplicate_record_ids.unique()))
        )

    audit = pd.DataFrame(
        audit_rows,
        columns=[
            "Project ID",
            "ruling_type",
            "action",
            "source_row_indexes",
            "source_titles",
            "resulting_record_ids",
            "canonical_title",
            "source_row_count",
            "note",
        ],
    )
    write_duplicate_rulings_audit(audit, audit_file)

    if stats is not None:
        stats["duplicate_rulings_file"] = rulings_path
        stats["duplicate_rulings_audit_file"] = audit_file
        stats["duplicate_ruling_groups_applied"] = len(audit)
        stats["duplicate_ruling_merged_source_rows"] = merged_source_rows
        stats["duplicate_ruling_rows_removed"] = merged_source_rows - sum(
            1 for row in audit_rows if row["action"] == "merged"
        )
        stats["duplicate_ruling_retained_project_ids"] = retained_project_ids
        stats["rows_after_duplicate_rulings"] = len(out)

    return DuplicateRulingsResult(
        dataframe=out,
        audit=audit,
        audit_file=audit_file,
        merged_source_rows=merged_source_rows,
        retained_project_ids=retained_project_ids,
    )


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


_RECORD_ID_PRIMARY_KEY_COLUMNS = ("Accreditation Date", "Title", "Datasets Used", "Researchers")


def _record_suffix(rank: int) -> str:
    """0 -> a, 1 -> b, ... 25 -> z, 26 -> aa."""
    rank += 1
    letters = ""
    while rank:
        rank, rem = divmod(rank - 1, 26)
        letters = chr(ord("a") + rem) + letters
    return letters


def _record_id_sort_key(row: pd.Series) -> tuple:
    """Content-derived ordering key for duplicate-ID suffix assignment.

    Suffixes must not depend on row position in the source file: a register
    re-publication that reorders rows would otherwise silently re-letter
    Record IDs and mis-join every artefact keyed on them (deterministic
    facets, LLM classifications). Date/title/datasets/researchers decide the
    order; remaining columns are a deterministic tiebreak.
    """
    primary = tuple(
        _normalise_date_key(row.get(col))
        if col == "Accreditation Date"
        else _normalise_duplicate_text(row.get(col))
        for col in _RECORD_ID_PRIMARY_KEY_COLUMNS
    )
    tiebreak = tuple(
        _normalise_duplicate_text(value)
        for col, value in sorted(row.items(), key=lambda item: str(item[0]))
        if col not in _RECORD_ID_PRIMARY_KEY_COLUMNS
    )
    return primary + tiebreak


def assign_record_ids(df: pd.DataFrame, *, allow_auto_suffix: bool = True) -> pd.DataFrame:
    out = df.copy()
    out["Project ID"] = (
        out["Project ID"].astype(str)
        .str.strip()
        .str.replace(r"\s*CLOSED\s*$", "", regex=True)
        .str.strip()
    )

    duplicated_ids = out["Project ID"].duplicated(keep=False)
    if "Record ID" not in out.columns:
        out["Record ID"] = pd.NA
    # Reviewed duplicate handling can copy a raw Project ID into Record ID
    # before Project ID itself is normalised. Normalise every pre-existing
    # Record ID centrally so downstream joins never inherit boundary
    # whitespace or source-CSV line breaks.
    out["Record ID"] = out["Record ID"].astype("string").str.strip()
    missing_record_id = out["Record ID"].isna() | out["Record ID"].str.strip().eq("")
    out.loc[missing_record_id & ~duplicated_ids, "Record ID"] = out.loc[
        missing_record_id & ~duplicated_ids, "Project ID"
    ]
    if duplicated_ids.any():
        for pid, grp in out.loc[duplicated_ids].groupby("Project ID", sort=False):
            missing = grp["Record ID"].isna() | grp["Record ID"].str.strip().eq("")
            if not missing.any():
                continue
            if not allow_auto_suffix:
                raise ValueError(
                    f"Duplicate Project ID {pid} has no explicit reviewed Record ID mapping"
                )
            ranked = sorted(grp.index, key=lambda idx: _record_id_sort_key(out.loc[idx]))
            for rank, idx in enumerate(ranked):
                if pd.isna(out.loc[idx, "Record ID"]) or not str(out.loc[idx, "Record ID"]).strip():
                    out.loc[idx, "Record ID"] = f"{pid}/{_record_suffix(rank)}"

    record_ids = out["Record ID"].astype("string")
    missing_or_blank = record_ids.isna() | record_ids.str.strip().eq("")
    if missing_or_blank.any():
        raise ValueError("Some cleaned rows have a missing or blank Record ID after assignment")

    boundary_whitespace = record_ids.ne(record_ids.str.strip())
    if boundary_whitespace.any():
        sample = ", ".join(repr(value) for value in record_ids[boundary_whitespace].head(10))
        raise ValueError(f"Record ID values retain leading or trailing whitespace: {sample}")

    prohibited_controls = record_ids.str.contains(
        r"[\x00-\x1f\x7f\u00a0]", regex=True, na=False
    )
    if prohibited_controls.any():
        sample = ", ".join(repr(value) for value in record_ids[prohibited_controls].head(10))
        raise ValueError(f"Record ID values contain prohibited control characters: {sample}")

    if not all(isinstance(value, str) for value in record_ids):
        raise ValueError("Every Record ID must be string-valued after assignment")

    duplicate_record_ids = out.loc[record_ids.duplicated(), "Record ID"]
    if len(duplicate_record_ids):
        sample = ", ".join(sorted(duplicate_record_ids.astype(str).unique())[:10])
        raise ValueError(
            f"Duplicate Record ID values after whitespace normalisation: {sample}"
        )
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
    rulings_audit_file = os.path.join(output_dir, "quality", "duplicate_rulings_audit.csv")
    rulings_result = apply_reviewed_duplicate_rulings(
        duplicate_result.dataframe,
        audit_file=rulings_audit_file,
        stats=stats,
    )
    df = assign_record_ids(rulings_result.dataframe, allow_auto_suffix=False)
    df["Title"] = df["Title"].apply(_clean_title_text)
    df["Researchers"] = df["Researchers"].apply(_clean_researcher_text)
    df["Datasets Used"] = df["Datasets Used"].apply(
        lambda value: _clean_datasets_text(value) if isinstance(value, str) and value.strip() else value
    )
    for col in ("Legal Basis", "Secure Research Service"):
        if col in df.columns:
            df[col] = df[col].apply(_clean_single_line_register_text)
    df = add_time_fields(df, include_quarter_date=include_quarter_date)
    if include_project_row_id:
        df["Project Row ID"] = [f"proj-{i:04d}" for i in range(len(df))]
    stats["final_rows"] = len(df)
    return df.reset_index(drop=True), stats


def load_clean_register(
    data_dir: str = DATA_DIR,
    *,
    candidate_files: Iterable[str] | None = None,
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
