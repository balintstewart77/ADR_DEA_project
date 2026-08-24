"""Auditable REDCap-to-analysis mappings."""

from __future__ import annotations

import csv
from pathlib import Path

from .config import ROOT


DICTIONARY = ROOT / "preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv"


def parse_choices(text: str) -> dict[int, str]:
    choices: dict[int, str] = {}
    for item in text.split("|"):
        if not item.strip():
            continue
        code, label = item.split(",", 1)
        choices[int(code.strip())] = label.strip()
    return choices


def dictionary_rows() -> list[dict[str, str]]:
    with DICTIONARY.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def choice_mappings() -> dict[str, dict[int, str]]:
    wanted = {
        "record_kind", "sample_set", "sample_status", "validation_included",
        "sc_exposure", "sc_domains", "sc_purposes", "sc_covid", "sc_equity",
        "sc_sufficiency", "sc_taxonomy_fit", "sc_tax_issue", "sc_confidence",
    }
    return {
        row["Variable / Field Name"]: parse_choices(row["Choices, Calculations, OR Slider Labels"])
        for row in dictionary_rows()
        if row["Variable / Field Name"] in wanted
    }


def field_mapping_rows() -> list[dict[str, str]]:
    """Return construct metadata only; never response values."""

    items = [
        ("coder pseudonym", "reviewer_id", "assignment_admin", "text", "C01/C02/C03", "formal assignment", "blank invalid", "Panel member"),
        ("assignment join key", "assignment_id", "assignment_admin", "opaque text", "direct", "formal assignment", "blank invalid", "Joined exactly to POST-019"),
        ("source-record join key", "source_record_id", "assignment_admin", "opaque text", "direct", "formal assignment", "blank invalid", "Never written to aggregate outputs"),
        ("formal inclusion", "validation_included", "assignment_admin", "0 No; 1 Yes", "1=formal", "all rows", "blank invalid", "Formal filter"),
        ("completion", "scratch_coder_complete", "scratch_coder", "0/1/2", "2=Complete", "project assignment", "blank/incomplete excluded dimension-wise", "REDCap form status"),
        ("Research Domains", "sc_domains___1..12", "scratch_coder", "checkbox 0/1", "unordered label set", "project assignment", "respect complete response and checkbox group", "Zero means unticked, not missing"),
        ("Analytical Purposes", "sc_purposes___1..8", "scratch_coder", "checkbox 0/1", "unordered label set", "project assignment", "respect complete response and checkbox group", "At most two; Unclear mutually exclusive"),
        ("equity tag", "sc_equity", "scratch_coder", "0 No; 1 Yes", "binary nominal", "project assignment", "blank missing; zero retained", "Analysed separately"),
        ("COVID tag", "sc_covid", "scratch_coder", "0 No; 1 Yes", "binary nominal", "project assignment", "blank missing; zero retained", "Analysed separately"),
        ("register sufficiency", "sc_sufficiency", "scratch_coder", "1 Sufficient; 2 Partial; 3 Insufficient", "categorical and majority", "project assignment", "blank missing", "Broad/strict subsets use original ratings"),
        ("taxonomy fit", "sc_taxonomy_fit", "scratch_coder", "1 Fit; 2 Partial Fit; 3 No Fit; 4 Cannot assess", "categorical and majority", "project assignment", "blank missing", "Cannot assess remains separate"),
        ("taxonomy issues", "sc_tax_issue___1/2/5", "scratch_coder", "checkbox 0/1", "multi-response issue indicators", "only fit codes 2/3", "ignore checkbox zeros when parent inapplicable", "Percentages may exceed 100%"),
        ("confidence", "sc_confidence", "scratch_coder", "1 High; 2 Medium; 3 Low", "categorical", "project assignment", "blank missing", "Used in aggregate coherence tables"),
        ("exposure", "sc_exposure", "scratch_coder", "0 No; 1 Yes", "binary flag", "project assignment", "blank missing; zero retained", "Flagged responses retained primary"),
        ("exposure explanation", "sc_exposure_note", "scratch_coder", "free text", "validation only", "sc_exposure=1", "blank invalid when applicable", "Text never exported to Stage A outputs"),
        ("conditional structural note", "sc_note", "scratch_coder", "free text", "validation only", "branching rule in RED-006", "blank invalid when applicable", "Text never exported to Stage A outputs"),
        ("structural validity", "all scratch fields", "scratch_coder", "frozen validator", "pass/fail", "complete project assignment", "no repair", "RED-013 validate_scratch"),
        ("submission timestamp", "scratch_coder_timestamp", "REDCap generated", "datetime", "completion timestamp only", "when present", "blank unavailable", "No review-start timestamp; duration not estimable"),
    ]
    columns = (
        "analysis_construct", "redcap_field", "instrument_section", "raw_coding",
        "derived_interpretation", "applicability_rule", "missingness_rule", "notes",
    )
    return [dict(zip(columns, item)) for item in items]
