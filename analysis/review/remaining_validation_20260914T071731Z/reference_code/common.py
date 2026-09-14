"""Shared helpers for the independent remaining-validation audit (2026-09-14).

Independence rule: nothing in this package imports ``analysis.*`` or
``scripts.*``. Statistics are re-derived from frozen inputs and saved/protocol
definitions with the standard library, pandas (CSV parsing) and numpy (integer
array indexing). No Record ID, Project ID, assignment ID, title, free-text note
or owner/contact field is written to any output.
"""
from __future__ import annotations

import csv
import hashlib
import math
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
AUDIT_DIR = Path(__file__).resolve().parents[1]

RAW = ROOT / "preregistration_restricted/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv"
BASE = ROOT / "preregistration_restricted/sampling/official_draw_20260724/baseline_active.csv"
HARD = ROOT / "preregistration_restricted/sampling/official_draw_20260724/hard_active.csv"
CROSS = ROOT / "preregistration_restricted/sampling/official_draw_20260724/formal_assignment_crosswalk.csv"
MODEL = ROOT / "analysis/outputs_classified_20260702_fable5/layer_classifications.csv"
DICTIONARY = ROOT / "preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv"
MANIFEST = ROOT / "preregistration/preregistration_artifact_manifest.csv"
STAGE_A = ROOT / "analysis/outputs_validation_scratch_20260824"
STAGE_B = ROOT / "analysis/outputs_validation_scratch_stage_b_20260825"
STRATA = ROOT / "analysis/outputs_validation_scratch_hard_case_strata_20260825"
WILSON = ROOT / "analysis/outputs_validation_wilson_baseline_20260907T142427225531Z"
FOLLOWUP = ROOT / "analysis/outputs_validation_consolidation_followup_20260907T132938546154Z"
CANON = ROOT / "analysis/scratch_coder_results"

CODERS = ("C01", "C02", "C03")  # A, B, C in saved Stage A/B methods and report Section 11
DIMENSIONS = ("Research Domains", "Analytical Purposes")
UNCLEAR = "Unclear from Register Entry"
SEED = 20260714
ATTEMPTS = 2000

# Comparison criteria fixed before any saved value was compared (see audit_report.md §3).
TOL_FLOAT = 1e-12   # absolute; double-precision statistics vs exact-rational / regenerated values
TOL_WILSON = 1e-12  # absolute; saved doubles vs 80-digit Decimal Wilson bounds
TOL_Z = 1e-15       # absolute; double-precision z constant vs high-precision inverse normal

# Analytical columns only: no titles, datasets, notes, exposure notes, owner or proposal fields.
RAW_COLS = [
    "assignment_id", "reviewer_id", "source_record_id", "validation_included",
    "scratch_coder_complete", "sample_set", "hard_stratum", "sc_sufficiency", "sc_taxonomy_fit",
    *[f"sc_domains___{i}" for i in range(1, 13)], *[f"sc_purposes___{i}" for i in range(1, 9)],
]
SAMPLE_COLS = [
    "record_id", "official_project_id", "sample_family", "sample_status", "hard_case_stratum",
    "accompanying_tag_disagreement", "forced_into_active_hard", "validation_included",
]


def rel(path) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    return result.stdout if binary else result.stdout.decode("utf-8", "replace")


def manifest_row(artifact_id: str) -> dict:
    with open(MANIFEST, encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["artifact_id"] == artifact_id]
    if len(rows) != 1:
        raise ValueError(f"{artifact_id} resolved {len(rows)} times")
    return rows[0]


def read_str_csv(path, usecols=None) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", usecols=usecols)


def redcap_choices(field: str) -> dict[int, str]:
    with open(DICTIONARY, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["Variable / Field Name"] == field:
                choices = {}
                for part in row["Choices, Calculations, OR Slider Labels"].split("|"):
                    if part.strip():
                        code, label = part.split(",", 1)
                        choices[int(code.strip())] = label.strip()
                return choices
    raise KeyError(field)


def split_labels(value: str) -> frozenset:
    return frozenset(part.strip() for part in value.split(";") if part.strip())


def type7(values, probability: float) -> float:
    """Hyndman-Fan Type 7: h=(N-1)p, linear interpolation between order statistics."""
    ordered = sorted(float(value) for value in values)
    h = (len(ordered) - 1) * probability
    low = math.floor(h)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (h - low) * (ordered[high] - ordered[low])


def _numeric(value) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return True
    try:
        float(str(value))
        return str(value).strip().lower() not in {"", "nan", "inf", "-inf", "true", "false"}
    except ValueError:
        return False


def _text(value) -> str:
    if isinstance(value, float):
        return repr(value)
    return "" if value is None else str(value)


class Ledger:
    FIELDS = ("check_id", "family", "artifact", "source_identifier", "check", "saved_value",
              "independent_value", "difference", "criterion", "status", "finding_ref", "note")
    STATUSES = {"VERIFIED", "DISCREPANT", "BLOCKED", "NOT_CHECKED"}

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, family, artifact, identifier, check, saved="", independent="", criterion="",
            status="VERIFIED", finding="", note="", difference=""):
        if status not in self.STATUSES:
            raise ValueError(status)
        if difference == "" and _numeric(saved) and _numeric(independent):
            difference = repr(abs(float(saved) - float(independent)))
        self.rows.append({
            "check_id": f"V{len(self.rows) + 1:05d}", "family": family, "artifact": artifact,
            "source_identifier": identifier, "check": check, "saved_value": _text(saved),
            "independent_value": _text(independent), "difference": difference, "criterion": criterion,
            "status": status, "finding_ref": finding, "note": note,
        })
        return status

    def num(self, family, artifact, identifier, check, saved, independent, tol, finding="", note=""):
        ok = saved not in (None, "") and independent is not None and abs(float(saved) - float(independent)) <= tol
        return self.add(family, artifact, identifier, check, saved, float(independent) if independent is not None else "",
                        f"absolute difference <= {tol:g}", "VERIFIED" if ok else "DISCREPANT", finding, note)

    def exact(self, family, artifact, identifier, check, saved, independent, finding="", note="",
              criterion="exact equality"):
        return self.add(family, artifact, identifier, check, saved, independent, criterion,
                        "VERIFIED" if saved == independent else "DISCREPANT", finding, note)

    def write(self, path):
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(self.rows)


def build_panel() -> dict:
    """Join export -> POST-019 -> POST-009/011 -> MOD-006 without using production parsing."""
    diag: dict[str, object] = {}
    base = read_str_csv(BASE, SAMPLE_COLS)
    hard = read_str_csv(HARD, SAMPLE_COLS)
    cross = read_str_csv(CROSS, ["assignment_id", "reviewer_id", "source_record_id", "sample_family", "hard_case_stratum"])
    raw = read_str_csv(RAW, RAW_COLS)
    formal = raw[raw["validation_included"] == "1"]
    diag["raw_rows"] = len(raw)
    diag["formal_rows"] = len(formal)
    diag["formal_assignment_duplicates"] = int(formal["assignment_id"].duplicated().sum())
    formal_record_ids = set(formal["source_record_id"])
    diag["nonformal_rows_on_formal_records"] = int(((raw["validation_included"] != "1") & raw["source_record_id"].isin(formal_record_ids)).sum())
    diag["export_sample_set_nonblank_formal"] = int((formal["sample_set"] != "").sum())
    diag["export_hard_stratum_nonblank_formal"] = int((formal["hard_stratum"] != "").sum())
    merged = formal.merge(cross, on="assignment_id", how="outer", suffixes=("_export", "_crosswalk"), indicator=True)
    diag["join_both"] = int((merged["_merge"] == "both").sum())
    diag["join_export_only"] = int((merged["_merge"] == "left_only").sum())
    diag["join_crosswalk_only"] = int((merged["_merge"] == "right_only").sum())
    both = merged[merged["_merge"] == "both"]
    diag["reviewer_mismatch"] = int((both["reviewer_id_export"] != both["reviewer_id_crosswalk"]).sum())
    diag["record_mismatch"] = int((both["source_record_id_export"] != both["source_record_id_crosswalk"]).sum())
    diag["incomplete_formal"] = int((both["scratch_coder_complete"] != "2").sum())

    domains, purposes = redcap_choices("sc_domains"), redcap_choices("sc_purposes")
    responses: dict[tuple[str, str], dict] = {}
    duplicates = invalid_boxes = empty_sets = unclear_combined = 0
    for row in both.to_dict("records"):
        key = (row["source_record_id_crosswalk"], row["reviewer_id_crosswalk"])
        duplicates += key in responses
        boxes_d = {code: row[f"sc_domains___{code}"] for code in domains}
        boxes_p = {code: row[f"sc_purposes___{code}"] for code in purposes}
        invalid_boxes += any(value not in ("0", "1") for value in (*boxes_d.values(), *boxes_p.values()))
        dom = frozenset(domains[c] for c, v in boxes_d.items() if v == "1")
        pur = frozenset(purposes[c] for c, v in boxes_p.items() if v == "1")
        empty_sets += (not dom) + (not pur)
        unclear_combined += (UNCLEAR in dom and len(dom) > 1) + (UNCLEAR in pur and len(pur) > 1)
        responses[key] = {
            "population": row["sample_family"], "stratum": row["hard_case_stratum"],
            "complete": row["scratch_coder_complete"] == "2",
            "Research Domains": dom, "Analytical Purposes": pur,
            "sufficiency": int(row["sc_sufficiency"]) if row["sc_sufficiency"] else None,
            "fit": int(row["sc_taxonomy_fit"]) if row["sc_taxonomy_fit"] else None,
        }
    diag.update(response_duplicates=duplicates, invalid_checkbox_responses=invalid_boxes,
                empty_coder_sets=empty_sets, coder_unclear_with_other_label=unclear_combined)

    model = read_str_csv(MODEL, ["Record ID", "substantive_domains", "analytical_purpose"])
    diag["model_duplicate_record_ids"] = int(model["Record ID"].duplicated().sum())
    formal_ids = set(cross["source_record_id"])
    subset = model[model["Record ID"].isin(formal_ids)]
    diag["model_join_rows"] = len(subset)
    diag["model_join_unique"] = int(subset["Record ID"].nunique())
    allowed = {"Research Domains": set(domains.values()), "Analytical Purposes": set(purposes.values())}
    records: dict[str, dict] = {}
    unknown = empty_model = unclear_model = 0
    for row in subset.to_dict("records"):
        labels = {"Research Domains": split_labels(row["substantive_domains"]),
                  "Analytical Purposes": split_labels(row["analytical_purpose"])}
        for dim, values in labels.items():
            unknown += len(values - allowed[dim])
            empty_model += not values
            unclear_model += UNCLEAR in values and len(values) > 1
        records[row["Record ID"]] = {"model": labels, "coders": {}}
    diag.update(model_unknown_labels=unknown, model_empty_sets=empty_model, model_unclear_with_other_label=unclear_model)
    for (record_id, coder), response in responses.items():
        records.setdefault(record_id, {"model": None, "coders": {}})["coders"][coder] = response
    return {"base": base, "hard": hard, "cross": cross, "records": records, "diag": diag}
