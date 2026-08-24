"""Timing support audit."""

from __future__ import annotations

from .panels import StageAData


def summarise_timing(data: StageAData) -> list[dict[str, object]]:
    """The frozen export has no review-start timestamp and no formal completion timestamps."""

    return [{
        "population": "formal_panel",
        "estimable": False,
        "valid_n": 0,
        "missing_n": len(data.responses),
        "measure": "active_review_duration",
        "reason": (
            "A6 not defensibly estimable from the frozen REDCap timestamp fields: "
            "the export contains no formal scratch_coder_timestamp values and no "
            "review-start timestamp for the same coding review."
        ),
        "median": None, "q1": None, "q3": None, "iqr": None,
        "p10": None, "p90": None, "p95": None, "maximum": None,
    }]
