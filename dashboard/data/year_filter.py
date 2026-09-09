"""Shared accreditation-year contract for dashboard record filtering.

The canonical cleaned register's ``Accreditation Date`` is authoritative.
``Year`` and ``Quarter`` are derived display/aggregation fields and are never
used as a fallback when selecting records.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


DATE_FIELD = "Accreditation Date"
RECORD_KEY = "Record ID"
DISPLAY_DATE_FORMAT = "%d %b %Y"


@dataclass(frozen=True)
class YearRange:
    minimum: int
    maximum: int

    @property
    def value(self) -> list[int]:
        return [self.minimum, self.maximum]

    @property
    def marks(self) -> dict[int, str]:
        return {year: str(year) for year in range(self.minimum, self.maximum + 1)}


def parse_accreditation_dates(df: pd.DataFrame) -> pd.Series:
    """Parse the authoritative field using Explorer's established display contract."""
    if DATE_FIELD not in df.columns:
        raise KeyError(f"Missing authoritative date field: {DATE_FIELD}")
    return pd.to_datetime(
        df[DATE_FIELD], format=DISPLAY_DATE_FORMAT, errors="coerce",
    )


def accreditation_years(df: pd.DataFrame) -> pd.Series:
    """Return nullable years derived only from the authoritative date field."""
    return parse_accreditation_dates(df).dt.year.astype("Int64")


def year_range(df: pd.DataFrame) -> YearRange:
    years = accreditation_years(df).dropna()
    if years.empty:
        raise ValueError("The authoritative register contains no valid accreditation years")
    return YearRange(int(years.min()), int(years.max()))


def year_slider_kwargs(df: pd.DataFrame) -> dict:
    bounds = year_range(df)
    return {
        "min": bounds.minimum,
        "max": bounds.maximum,
        "step": 1,
        "value": bounds.value,
        "marks": bounds.marks,
        "allowCross": False,
    }


def _selected_bounds(selection, bounds: YearRange) -> tuple[int, int] | None:
    try:
        selected = sorted(int(year) for year in selection)
    except (TypeError, ValueError):
        return None
    if len(selected) != 2:
        return None
    return selected[0], selected[1]


def is_all_years(selection, bounds: YearRange) -> bool:
    selected = _selected_bounds(selection, bounds)
    return selected is None or (
        selected[0] <= bounds.minimum and selected[1] >= bounds.maximum
    )


def valid_year_mask(df: pd.DataFrame) -> pd.Series:
    return parse_accreditation_dates(df).notna()


def year_selection_mask(
    df: pd.DataFrame,
    selection,
    bounds: YearRange,
) -> pd.Series:
    """Inclusive record mask; full range includes invalid/undated records."""
    if is_all_years(selection, bounds):
        return pd.Series(True, index=df.index, dtype=bool)
    lower, upper = _selected_bounds(selection, bounds)
    years = accreditation_years(df)
    return years.between(lower, upper).fillna(False)


def filter_records_by_year(
    df: pd.DataFrame,
    selection,
    bounds: YearRange,
) -> pd.DataFrame:
    return df.loc[year_selection_mask(df, selection, bounds)].copy()


def selected_record_ids(
    register_df: pd.DataFrame,
    selection,
    bounds: YearRange,
) -> list[str]:
    """Return selected record-unit keys, rejecting ambiguous key mappings."""
    if RECORD_KEY not in register_df.columns:
        raise KeyError(f"Missing record-unit key: {RECORD_KEY}")
    keys = register_df[RECORD_KEY].astype("string").str.strip()
    if keys.isna().any() or keys.eq("").any() or keys.duplicated().any():
        raise ValueError(f"{RECORD_KEY} must be unique and non-blank")
    mask = year_selection_mask(register_df, selection, bounds)
    return keys.loc[mask].astype(str).tolist()


def filter_related_by_record_ids(
    related_df: pd.DataFrame,
    record_ids,
) -> pd.DataFrame:
    """Filter an expanded/secondary table without Project-ID leakage."""
    if RECORD_KEY not in related_df.columns:
        raise KeyError(f"Related table is missing record-unit key: {RECORD_KEY}")
    wanted = {str(value).strip() for value in record_ids}
    keys = related_df[RECORD_KEY].astype("string").str.strip()
    return related_df.loc[keys.isin(wanted)].copy()


def selection_label(selection, bounds: YearRange) -> str:
    if is_all_years(selection, bounds):
        return f"All years ({bounds.minimum}–{bounds.maximum})"
    lower, upper = _selected_bounds(selection, bounds)
    return str(lower) if lower == upper else f"{lower}–{upper}"


def date_coverage(df: pd.DataFrame) -> dict[str, int]:
    raw = df[DATE_FIELD]
    dates = parse_accreditation_dates(df)
    missing = raw.isna() | raw.astype("string").str.strip().eq("")
    malformed = ~missing & dates.isna()
    return {
        "eligible_records": int(len(df)),
        "valid_year_records": int(dates.notna().sum()),
        "missing_date_records": int(missing.sum()),
        "malformed_date_records": int(malformed.sum()),
        "undated_or_invalid_records": int(dates.isna().sum()),
    }
