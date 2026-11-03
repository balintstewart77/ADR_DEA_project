"""Stage 1 for the pass-4 scratch-coder presentation run.

Reads the pass-3 figure data as its numeric baseline, the exploratory
label-application and cardinality outputs (LAC1T001-LAC1T002), and the verified
pre-existing model-evidence metrics.  It renumbers deliverables, adds the
supplementary repeatability and cardinality material, records lineage and
repeats carry-over and reconciliation assertions.  It does not read
record-level inputs or rerun any analysis.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "analysis/figure_data"
ARCHIVE_NAME = "pass4_preexisting_7e77c47"
LAC_DIR = ROOT / "analysis/label_application_cardinality_exploratory"
LAC_SPEC = LAC_DIR / "SPEC_label_application_cardinality_2026-11-03.md"
EVIDENCE_DIR = ROOT / "preregistration/package/03_preexisting_model_evidence"
STABILITY = EVIDENCE_DIR / "fable_run_stability_metrics.json"
STABILITY_MANIFEST = EVIDENCE_DIR / "fable_run_stability_201_record_manifest.csv"
CROSS_MODEL = EVIDENCE_DIR / "fable5_gpt55_metrics.json"
# Untracked recovered sample; its SHA-256 is pinned in fable_run_stability_metrics.json.
STABILITY_SAMPLE = ROOT / "analysis/outputs/model_comparison_sample.csv"
PASS3_CAPTIONS = ROOT / "analysis/figures/draft_captions_pass2.md"
PASS3_CAPTIONS_ARCHIVED = ROOT / "analysis/figures/archive" / ARCHIVE_NAME / "draft_captions_pass2.md"

FIELDNAMES = [
    "deliverable_id", "role", "population", "dimension", "label", "source_order",
    "series", "quantity", "pair", "source_file", "source_table_id", "source_section",
    "source_row_key", "source_column_locator", "source_value_string", "parsed_value",
    "interval_lower_string", "parsed_interval_lower", "interval_upper_string",
    "parsed_interval_upper", "estimate_status", "interval_status", "original_status_string",
    "interval_method", "confidence_level", "denominator_string", "sample_size",
    "denominator_unit", "support_string", "support_band", "exported_caution",
    "eligible_for_per_label_performance", "eligible_for_macro_average",
    "performance_metrics_reportable", "unavailable_reason", "presentation_note",
    "derivation_id", "derivation_operands", "row_group", "display_percent",
]
ORDER = (
    "Figure 1", "Figure 2", "Figure 3",
    "Supplementary Figure S1", "Supplementary Figure S2", "Supplementary Figure S3", "Supplementary Figure S4",
    "Figure 3 source table", "Supplementary Table S13", "Supplementary Table S14",
)
SLUGS = {
    "Figure 1": "figure_1_replacement_reliability_baseline_sufficient",
    "Figure 2": "figure_2_coder_ratings_baseline",
    "Figure 3": "figure_3_label_application_by_coder",
    "Supplementary Figure S1": "supplementary_figure_s1_baseline_vs_hardcase",
    "Supplementary Figure S2": "supplementary_figure_s2_hardcase_ratings_confidence",
    "Supplementary Figure S3": "supplementary_figure_s3_tag_replacement_baseline",
    "Supplementary Figure S4": "supplementary_figure_s4_repeatability_cross_model",
    "Figure 3 source table": "figure_3_label_application_by_coder_source",
    "Supplementary Table S13": "supplementary_table_s13_cardinality_abstention",
    "Supplementary Table S14": "supplementary_table_s14_repeatability_cross_model",
}
TITLES = {
    "Figure 1": "Replacement-panel reliability in the random baseline and the register-sufficient subset",
    "Figure 2": "Register-entry information and taxonomy fit: ratings by each coder and by the majority of coders",
    "Figure 3": "Label application by Fable 5 and the three independent coders",
    "Supplementary Figure S1": "Replacing a human coder with Fable 5 in a non-representative hard-case sample (diagnostic)",
    "Supplementary Figure S2": "Coder ratings in the hard-case sample, and coder confidence in both samples",
    "Supplementary Figure S3": "Binary-tag replacement agreement in the random baseline",
    "Supplementary Figure S4": "Same-model repeatability and cross-model agreement (pre-existing descriptive analyses)",
    "Figure 3 source table": "Label application counts by each coder and Fable 5, random baseline (source data for Figure 3)",
    "Supplementary Table S13": "Label-set cardinality and abstention by rater, random baseline",
    "Supplementary Table S14": "Same-model repeatability and cross-model agreement: all exported metrics",
}
# Pass-3 figure data carried forward, by pass-4 deliverable.
PASS3_SOURCES = {
    "Figure 1": "figure_3_sufficiency_sensitivity.csv",
    "Figure 2": "figure_2_coder_ratings_baseline.csv",
    "Supplementary Figure S1": "supplementary_figure_s1_baseline_vs_hardcase.csv",
    "Supplementary Figure S2": "supplementary_figure_s2_hardcase_ratings_confidence.csv",
    "Supplementary Figure S3": "figure_1_panel_agreement_replacement.csv",
}
PASS3_LABEL_COUNTS = "figure_4_label_application.csv"
# Pass-3 figure-data files that pass 4 supersedes or rewrites.  Table data stay in place.
PASS3_SUPERSEDED = (
    "figure_1_panel_agreement_replacement", "figure_2_coder_ratings_baseline", "figure_3_sufficiency_sensitivity",
    "figure_4_label_application", "supplementary_figure_s1_baseline_vs_hardcase",
    "supplementary_figure_s2_hardcase_ratings_confidence", "supplementary_figure_s3_disagreement_composition",
)
CARRIED_TABLES = {
    "Table 1": "table_1_agreement_domains", "Table 2": "table_2_agreement_purposes",
    "Table 3": "table_3_agreement_with_majority_domains", "Table 4": "table_4_agreement_with_majority_purposes",
    "Supplementary Table S1a": "supplementary_table_s1a_register_information",
    "Supplementary Table S1b": "supplementary_table_s1b_taxonomy_fit",
    "Supplementary Table S1c": "supplementary_table_s1c_agreed_labels",
}
WITHHELD_TABLE = ("Supplementary Table S2", "supplementary_table_s2_disagreement_composition")
DIMENSION_NAMES = ("Research Domains", "Analytical Purposes", "Demographic disparities / equity", "COVID-19 & Pandemic")
TAGS = DIMENSION_NAMES[2:]
RATERS = ("C01", "C02", "C03", "Fable 5")
UNCLEAR = "Unclear from Register Entry"
# Values stated in protocol v1.1 §§4.2–4.3; the verified metrics must agree with them.
PROTOCOL_STATED = {
    "repeatability": {"n": 201, "domain_exact": (191, "95.0"), "purpose_exact": (185, "92.0"),
                      "domain_jaccard": "0.974", "purpose_jaccard": "0.935"},
    "cross_model": {"n": 1308, "domain_exact_rate": "81.4", "purpose_exact_rate": "84.7",
                    "domain_jaccard": "0.904", "purpose_jaccard": "0.885"},
    "frame_pre": {"total_disagreement": 386, "domain_only": 186, "purpose_only": 143, "both": 57,
                  "tag_disagreement_alongside_domain_or_purpose": 12, "tag_only_outside_domain_purpose_frame": 37},
    "frame_post": {"total_disagreement": 380, "domain_only": 182, "purpose_only": 143, "both": 55,
                   "tag_disagreement_alongside_domain_or_purpose": 11},
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def rounded(value: Decimal, places: int) -> str:
    return str(value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def pass3_path(data_dir: Path, name: str) -> Path:
    """Prefer the archived pass-3 copy, so reruns read pass-3 values, not pass-4 rewrites."""
    archived = data_dir / "archive" / ARCHIVE_NAME / name
    return archived if archived.is_file() else data_dir / name


def archive_pass3(data_dir: Path) -> list[dict]:
    archive = data_dir / "archive" / ARCHIVE_NAME
    names = [f"{slug}{suffix}" for slug in PASS3_SUPERSEDED for suffix in (".csv", "_metadata.json")]
    names += ["pass3_deliverable_manifest.json", "pass3_run_metadata.json"]
    moved = []
    for name in names:
        source, target = data_dir / name, archive / name
        if not source.is_file() or target.is_file():
            continue  # already archived on an earlier pass-4 run; the active file is a pass-4 output
        archive.mkdir(parents=True, exist_ok=True)
        shutil.move(source, target)
        moved.append({"from": str(source.relative_to(ROOT)), "to": str(target.relative_to(ROOT))})
    return moved


def clone(rows: list[dict], deliverable: str) -> list[dict]:
    copied = deepcopy(rows)
    for row in copied:
        row["deliverable_id"] = deliverable
    return copied


def carryover_check(old: dict[str, list[dict]], new: dict[str, list[dict]]) -> dict:
    """Every carried-forward row is identical to its pass-3 row except for the deliverable ID."""
    failures = []; checked = 0
    for deliverable, rows in old.items():
        strip = lambda row: {k: v for k, v in row.items() if k != "deliverable_id"}  # noqa: E731
        before = [strip(row) for row in rows]; after = [strip(row) for row in new[deliverable]]
        checked += len(before)
        if before != after:
            failures.append(deliverable)
    if failures:
        raise RuntimeError(f"Pass-4 carried-over values changed: {failures}")
    return {"status": "PASS", "rows_checked": checked, "deliverables": sorted(old)}


def base_row(deliverable: str, *shared: dict, **values) -> dict:
    """A figure-data row: defaults, then shared field dicts, then explicit values (later wins)."""
    row = {name: "" for name in FIELDNAMES}
    row.update({"deliverable_id": deliverable, "role": "plotted", "estimate_status": "R", "interval_status": "N"})
    for layer in (*shared, values):
        row.update({k: str(v) for k, v in layer.items()})
    return row


def label_application_rows(lac_rows: list[dict], pass3_counts: list[dict]) -> tuple[list[dict], dict]:
    """Figure 3 rows: coder counts from LAC1T001, Fable 5 counts from S5T001/S5T002 (reconciled)."""
    exported = {(r["dimension"], r["label"]): r for r in pass3_counts}
    rows = []; placement = {}
    for lac in lac_rows:
        key = (lac["dimension"], lac["label"])
        s5 = exported[key]
        if int(lac["fable5_count"]) != int(s5["interval_lower_string"]):
            raise RuntimeError(f"Fable 5 count does not reconcile with {s5['source_table_id']}: {key}")
        order = s5["source_order"]
        common = {"population": "baseline", "dimension": lac["dimension"], "label": lac["label"], "source_order": order,
                  "series": "label application", "denominator_string": f"{lac['denominator_records']} baseline records (valid common records)",
                  "sample_size": lac["denominator_records"], "denominator_unit": "records",
                  "row_group": "unclear" if lac["label"] == UNCLEAR else "substantive",
                  "presentation_note": "row order: pass-3 label-application point number (descending coder-majority count, ties alphabetical); Unclear plotted last"}
        for coder in RATERS[:3]:
            rows.append(base_row("Figure 3", common, quantity="label_application_count", pair=coder,
                                 source_file="analysis/label_application_cardinality_exploratory/LAC1T001.csv", source_table_id="LAC1T001",
                                 source_section="exploratory descriptive (not preregistered)", source_row_key=lac["label"],
                                 source_column_locator=f"{coder}_count", source_value_string=lac[f"{coder}_count"],
                                 parsed_value=lac[f"{coder}_count"], original_status_string="exploratory descriptive count"))
        rows.append(base_row("Figure 3", common, quantity="label_application_count", pair="Fable 5",
                             source_file=s5["source_file"], source_table_id=s5["source_table_id"], source_section=s5["source_section"],
                             source_row_key=lac["label"], source_column_locator="baseline_model_positive_n",
                             source_value_string=s5["interval_lower_string"], parsed_value=s5["interval_lower_string"],
                             original_status_string="R/N", presentation_note=common["presentation_note"] + "; equals LAC1T001 fable5_count"))
        for quantity, column in (("coder_min", "coder_min"), ("coder_max", "coder_max")):
            rows.append(base_row("Figure 3", common, role="derived", quantity=quantity, pair="C01/C02/C03",
                                 source_file="analysis/label_application_cardinality_exploratory/LAC1T001.csv", source_table_id="LAC1T001",
                                 source_row_key=lac["label"], source_column_locator=column, source_value_string=lac[column],
                                 parsed_value=lac[column], derivation_id=f"P4.D1 {quantity.replace('coder_', '')} of three coder counts",
                                 derivation_operands=f"{lac['C01_count']};{lac['C02_count']};{lac['C03_count']}"))
            if int(lac[column]) != (min if quantity == "coder_min" else max)(int(lac[f"{c}_count"]) for c in RATERS[:3]):
                raise RuntimeError(f"LAC1T001 {column} inconsistent for {key}")
        placement.setdefault(lac["dimension"], {}).setdefault(lac["fable5_position"], []).append(lac["label"])
    return rows, placement


def cardinality_rows(lac2: list[dict]) -> list[dict]:
    rows = []
    for index, lac in enumerate(lac2, 1):
        common = {"population": "baseline", "dimension": lac["dimension"], "pair": lac["rater"], "source_order": index,
                  "series": "cardinality and abstention", "source_file": "analysis/label_application_cardinality_exploratory/LAC1T002.csv",
                  "source_table_id": "LAC1T002", "source_section": "exploratory descriptive (not preregistered)", "source_row_key": lac["rater"],
                  "sample_size": lac["records_N"], "denominator_unit": "records", "original_status_string": "exploratory descriptive; no intervals"}
        values = (
            ("mean_substantive_labels_per_record", "mean_substantive_labels_per_record", f"{lac['records_N']} valid common records"),
            ("substantive_label_applications", "substantive_label_applications", f"{lac['records_N']} valid common records"),
            ("unclear_records", "unclear_records", f"{lac['records_N']} valid common records"),
            ("unclear_proportion", "unclear_proportion", f"{lac['records_N']} valid common records"),
            ("substantively_classified_records", "substantively_classified_records", f"{lac['records_N']} valid common records"),
            ("mean_substantive_labels_among_classified", "mean_substantive_labels_among_classified",
             f"{lac['substantively_classified_records']} substantively classified records"),
        )
        for quantity, column, denominator in values:
            rows.append(base_row("Supplementary Table S13", common, quantity=quantity, source_column_locator=column,
                                 source_value_string=lac[column], parsed_value=lac[column], denominator_string=denominator))
    return rows


def evidence_rows(stability: dict, cross: dict, composition: dict) -> tuple[list[dict], list[dict]]:
    """Supplementary Figure S4 and Supplementary Table S14 rows from the verified metrics files."""
    stab_file = str(STABILITY.relative_to(ROOT)).replace("\\", "/")
    cross_file = str(CROSS_MODEL.relative_to(ROOT)).replace("\\", "/")
    s_metrics, c_metrics = stability["metrics"], cross["comparison"]
    panels = {
        "repeatability": {"population": "fixed_201_record_stability_sample", "pair": "Fable 5 run 1 versus Fable 5 run 2",
                          "file": stab_file, "table": "PME-STAB", "n": s_metrics["n"]},
        "cross_model": {"population": "frozen_register_1308", "pair": "Fable 5 versus GPT-5.5 (production prompt)",
                        "file": cross_file, "table": "PME-XMOD", "n": c_metrics["n"]},
    }
    figure, table = [], []

    def add(target: list[dict], deliverable: str, panel: str, dimension: str, quantity: str, value, locator: str,
            numerator: str = "", derivation: str = "", order: int = 0) -> None:
        spec = panels[panel]
        target.append(base_row(deliverable, population=spec["population"], dimension=dimension, pair=spec["pair"], series=panel,
                               quantity=quantity, source_file=spec["file"], source_table_id=spec["table"],
                               source_section="pre-existing model evidence (protocol §§4.2–4.3); not preregistered",
                               source_row_key=quantity, source_column_locator=locator, source_value_string=repr(value) if isinstance(value, float) else value,
                               parsed_value=repr(value) if isinstance(value, float) else value, sample_size=spec["n"],
                               denominator_string=f"{spec['n']} records", denominator_unit="records", derivation_id=derivation,
                               derivation_operands=numerator, source_order=order, original_status_string="verified pre-existing descriptive metric"))

    exact = {
        ("repeatability", "Research Domains"): (s_metrics["domain_exact"]["count"], s_metrics["domain_exact"]["denominator"], "metrics.domain_exact.count"),
        ("repeatability", "Analytical Purposes"): (s_metrics["purpose_exact"]["count"], s_metrics["purpose_exact"]["denominator"], "metrics.purpose_exact.count"),
        ("cross_model", "Research Domains"): (c_metrics["domain_exact_count"], c_metrics["n"], "comparison.domain_exact_count"),
        ("cross_model", "Analytical Purposes"): (c_metrics["purpose_exact_count"], c_metrics["n"], "comparison.purpose_exact_count"),
    }
    jaccard = {
        ("repeatability", "Research Domains"): (s_metrics["mean_domain_jaccard"], "metrics.mean_domain_jaccard"),
        ("repeatability", "Analytical Purposes"): (s_metrics["mean_purpose_jaccard"], "metrics.mean_purpose_jaccard"),
        ("cross_model", "Research Domains"): (c_metrics["domain_mean_jaccard"], "comparison.domain_mean_jaccard"),
        ("cross_model", "Analytical Purposes"): (c_metrics["purpose_mean_jaccard"], "comparison.purpose_mean_jaccard"),
    }
    for order, (panel, dimension) in enumerate(exact, 1):
        count, denominator, locator = exact[(panel, dimension)]
        if denominator != panels[panel]["n"]:
            raise RuntimeError(f"Exact-set denominator differs from panel n: {panel} {dimension}")
        proportion = Decimal(count) / Decimal(denominator)
        for target, deliverable in ((figure, "Supplementary Figure S4"), (table, "Supplementary Table S14")):
            add(target, deliverable, panel, dimension, "exact_set_count", str(count), locator, order=order)
            add(target, deliverable, panel, dimension, "exact_set_proportion", str(proportion), locator,
                numerator=f"{count}/{denominator}", derivation="P4.D2 exact-set count divided by records compared", order=order)
            value, jlocator = jaccard[(panel, dimension)]
            add(target, deliverable, panel, dimension, "mean_jaccard", float(value), jlocator, order=order)
    tags = (
        ("repeatability", "COVID-19 & Pandemic", s_metrics["covid_tag_agreement"]["count"], "metrics.covid_tag_agreement.count"),
        ("repeatability", "Demographic disparities / equity", s_metrics["equity_tag_agreement"]["count"], "metrics.equity_tag_agreement.count"),
        ("repeatability", "Both tags", s_metrics["joint_tag_agreement"]["count"], "metrics.joint_tag_agreement.count"),
        ("repeatability", "All four components", s_metrics["all_component_agreement"]["count"], "metrics.all_component_agreement.count"),
        ("cross_model", "COVID-19 & Pandemic", c_metrics["covid_tag_match_count"], "comparison.covid_tag_match_count"),
        ("cross_model", "Demographic disparities / equity", c_metrics["disparities_tag_match_count"], "comparison.disparities_tag_match_count"),
        ("cross_model", "Both tags", c_metrics["joint_tag_match_count"], "comparison.joint_tag_match_count"),
    )
    for order, (panel, dimension, count, locator) in enumerate(tags, 10):
        add(table, "Supplementary Table S14", panel, dimension, "agreement_count", str(count), locator, order=order)
    add(table, "Supplementary Table S14", "repeatability", "All components", "invalid_or_failed_classifications",
        str(s_metrics["invalid_or_failed_classifications"]), "metrics.invalid_or_failed_classifications", order=20)
    add(table, "Supplementary Table S14", "cross_model", "All components", "invalid_or_failed_classifications",
        str(c_metrics["gpt_invalid_count"]), "comparison.gpt_invalid_count", order=20)
    for stage, block in (("pre_exclusion", cross["pre_exclusion"]), ("post_exclusion", cross["post_exclusion"])):
        for order, (key, value) in enumerate(block.items(), 30 if stage == "pre_exclusion" else 40):
            add(table, "Supplementary Table S14", "cross_model", "Disagreement frame", f"{stage}:{key}", str(value), f"{stage}.{key}", order=order)
    add(table, "Supplementary Table S14", "cross_model", "Disagreement frame", "exclusions_applied", str(cross["exclusions"]["count"]),
        "exclusions.count", order=50)
    for stratum, count in composition["strata"].items():
        add(figure, "Supplementary Figure S4", "repeatability", "Sample composition", f"stratum:{stratum}", str(count),
            "model_comparison_sample.csv stratum column (SHA-256 pinned at comparison_sample.source_sha256)", order=60)
        add(table, "Supplementary Table S14", "repeatability", "Sample composition", f"stratum:{stratum}", str(count),
            "model_comparison_sample.csv stratum column (SHA-256 pinned at comparison_sample.source_sha256)", order=60)
    return figure, table


def evidence_assertions(stability: dict, cross: dict) -> dict:
    checks = []

    def same(name: str, observed, expected) -> None:
        checks.append({"check": name, "observed": observed, "expected": expected, "status": "PASS" if observed == expected else "FAIL"})

    same("stability verification_status", stability["verification_status"], "verified")
    same("cross-model verification_status", cross["verification_status"], "verified")
    same("stability no API calls", stability["no_api_or_llm_calls_made"], True)
    s, c, p = stability["metrics"], cross["comparison"], PROTOCOL_STATED
    same("repeatability n", s["n"], p["repeatability"]["n"])
    for key in ("domain_exact", "purpose_exact"):
        same(f"repeatability {key} count", s[key]["count"], p["repeatability"][key][0])
        same(f"repeatability {key} percentage (1 dp)", rounded(Decimal(str(s[key]["percentage"])), 1), p["repeatability"][key][1])
    same("repeatability domain Jaccard (3 dp)", rounded(Decimal(str(s["mean_domain_jaccard"])), 3), p["repeatability"]["domain_jaccard"])
    same("repeatability purpose Jaccard (3 dp)", rounded(Decimal(str(s["mean_purpose_jaccard"])), 3), p["repeatability"]["purpose_jaccard"])
    same("stability model", (stability["run1"]["model"], stability["run2"]["model"]), ("claude-fable-5", "claude-fable-5"))
    same("stability prompt", (stability["run1"]["prompt_version"], stability["run2"]["prompt_version"]), ("dict-1.0-rc2", "dict-1.0-rc2"))
    same("cross-model n", c["n"], p["cross_model"]["n"])
    same("cross-model domain exact rate (1 dp)", rounded(Decimal(str(c["domain_exact_rate"])) * 100, 1), p["cross_model"]["domain_exact_rate"])
    same("cross-model purpose exact rate (1 dp)", rounded(Decimal(str(c["purpose_exact_rate"])) * 100, 1), p["cross_model"]["purpose_exact_rate"])
    same("cross-model domain rate equals count/n", abs(c["domain_exact_count"] / c["n"] - c["domain_exact_rate"]) < 1e-12, True)
    same("cross-model purpose rate equals count/n", abs(c["purpose_exact_count"] / c["n"] - c["purpose_exact_rate"]) < 1e-12, True)
    same("cross-model domain Jaccard (3 dp)", rounded(Decimal(str(c["domain_mean_jaccard"])), 3), p["cross_model"]["domain_jaccard"])
    same("cross-model purpose Jaccard (3 dp)", rounded(Decimal(str(c["purpose_mean_jaccard"])), 3), p["cross_model"]["purpose_jaccard"])
    for key, expected in p["frame_pre"].items():
        same(f"frame pre {key}", cross["pre_exclusion"][key], expected)
    for key, expected in p["frame_post"].items():
        same(f"frame post {key}", cross["post_exclusion"][key], expected)
    same("frame pre components sum", cross["pre_exclusion"]["domain_only"] + cross["pre_exclusion"]["purpose_only"] + cross["pre_exclusion"]["both"],
         cross["pre_exclusion"]["total_disagreement"])
    same("frame post components sum", cross["post_exclusion"]["domain_only"] + cross["post_exclusion"]["purpose_only"] + cross["post_exclusion"]["both"],
         cross["post_exclusion"]["total_disagreement"])
    failures = [check for check in checks if check["status"] != "PASS"]
    if failures:
        raise RuntimeError(f"Pre-existing evidence assertions failed: {failures}")
    return {"status": "PASS", "checks": checks}


def stability_composition(stability: dict) -> dict:
    if not STABILITY_SAMPLE.is_file():
        raise FileNotFoundError(f"Untracked stability sample required for composition: {STABILITY_SAMPLE}")
    observed = sha256(STABILITY_SAMPLE)
    if observed != stability["comparison_sample"]["source_sha256"]:
        raise RuntimeError("Stability sample hash differs from fable_run_stability_metrics.json")
    rows = read_csv(STABILITY_SAMPLE)
    strata: dict[str, int] = {}
    for row in rows:
        strata[row["stratum"]] = strata.get(row["stratum"], 0) + 1
    manifest_ids = {row["run_record_id"] for row in read_csv(STABILITY_MANIFEST)}
    if {row["Record ID"] for row in rows} != manifest_ids or len(rows) != stability["metrics"]["n"]:
        raise RuntimeError("Stability sample does not match the 201-record manifest")
    if strata != {"adjudicated": 31, "random": 170}:
        raise RuntimeError(f"Unexpected stability sample strata: {strata}")
    return {"path": str(STABILITY_SAMPLE.relative_to(ROOT)).replace("\\", "/"), "tracked": False, "sha256": observed,
            "hash_pinned_by": "preregistration/package/03_preexisting_model_evidence/fable_run_stability_metrics.json comparison_sample.source_sha256",
            "strata": {"adjudicated": strata["adjudicated"], "random": strata["random"]},
            "random_draw": "seed 20260702 from the live register excluding the 31 purposively selected IDs (analysis/outputs/model_comparison_fable5_build_sample.py)",
            "purposive_sources": "earlier rc2 temporal-correction spot-checks, unclassified-dataset review cases, alias regression tests, and two cases flagged by an earlier re-classification stability check"}


def placement_text(placement: dict) -> str:
    parts = []
    for dimension in DIMENSION_NAMES[:2]:
        groups = placement[dimension]
        above, below, within = (groups.get(key, []) for key in ("above_all_coders", "below_all_coders", "within_coder_range"))
        parts.append(f"{dimension}: above every coder for {len(above)} labels ({'; '.join(above)}), below every coder for {len(below)} "
                     f"({'; '.join(below)}) and within the coder range for {len(within)}")
    return ". ".join(parts)


def old_bullets(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}; current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip(); result[current] = []
        elif current and line.startswith("- "):
            result[current].append(line[2:])
    return result


def captions(old: dict[str, list[str]], placement: dict, lac2: list[dict], composition: dict) -> dict[str, list[str]]:
    bullets: dict[str, list[str]] = {}
    bullets["Figure 1"] = [
        "Filled markers: the full random baseline (n=150), the primary preregistered replacement analysis. Hollow markers: the register-sufficient subset (n=92), the preregistered sensitivity analysis. The subset is nested within the baseline [S3T001/S3T002 and S3T011/S3T012 denominator cells; displayed 150 and 92].",
        "ABC is the all-human panel (C01, C02, C03); LBC, ALC and ABL are the panels in which Fable 5 replaces C01, C02 and C03 respectively. δₐ = LBC − ABC, δᵦ = ALC − ABC and δ꜀ = ABL − ABC; each δ sits level with the panel it measures. δₘᵢₙ is the least favourable of the three and sits level with ABC [S3T001/S3T002/S3T011/S3T012 row cells].",
        old["Figure 3"][1],
        "Baseline Analytical Purposes δₘᵢₙ upper=-0.002141124278556386 (display −0.002) and register-sufficient subset Research Domains δₘᵢₙ lower=0.0005992244570877603 (display +0.001); both intervals exclude zero [S3T002/S3T011 interval cells].",
        "Intervals are percentile bootstrap intervals from 2,000 record resamples; their confidence level was not recorded, so they are not labelled 95% [S3T001/S3T002/S3T011/S3T012 status cells, confidence unresolved].",
        "The register-sufficient subset comprises records that at least two of three coders rated Sufficient (n=92); Figure 2 shows the ratings that define it [S8T003/S8T005 count cells].",
        "Conditioning on the coders’ ratings changes which records are analysed and may change label prevalence. Differences between the two populations are descriptive: they do not show that sufficiency raised agreement or that the subset is free of classification errors.",
        "The α axis is 0.15–0.75, rather than the 0–1 scale used in Supplementary Figures S1 and S3 [S3T001, S3T002, S3T011, S3T012 interval cells].",
        "Research Domains and Analytical Purposes only; the two binary tags are shown in Supplementary Figure S3, and hard-case results in Supplementary Figure S1.",
    ]
    bullets["Figure 2"] = [
        old["Figure 2"][0],
        "A majority rating is the category chosen identically by at least two of three coders; when all three differ the result is No majority, which remains a separate category [S8T003/S9T003 category cells].",
        "Cannot assess from register entry is distinct from No Fit: coders were instructed to choose it when the entry was too limited to judge fit, and not to choose Partial Fit or No Fit solely because the entry lacked information [RED-036 field note for sc_taxonomy_fit].",
        "Coder bars show each coder’s own distribution; the Majority of coders bar is derived from them and is set apart by a gap [S8T001/S8T003/S9T001/S9T003 cells].",
        old["Figure 2"][2],
        "Figure 1’s register-sufficient subset is the 92 records with a Sufficient majority. The broad subset is 148 records and is not obtained by adding the Sufficient and Partially sufficient majority counts [S8T003/S8T005 count cells].",
        old["Figure 2"][4],
        old["Figure 2"][5],
    ]
    bullets["Figure 3"] = [
        "Each row is one label in the random baseline; every rater classified the same 150 valid common records in each dimension [LAC1T001 denominator cells].",
        "Small hollow markers show the number of records to which each coder applied the label (C01 circle, C02 square, C03 triangle); the large filled diamond shows Fable 5 [LAC1T001 coder count cells; Fable 5 counts from S5T001/S5T002 model-positive cells, reconciled with LAC1T001].",
        "The thin line spans the lowest to the highest of the three coder counts: the observed range across three coders, not a confidence interval.",
        "Markers with identical or adjacent counts are offset vertically within their row so that each stays visible; horizontal positions are the exact counts.",
        f"{placement_text(placement)} [LAC1T001 placement cells]. A count outside the coders’ range is not evidence of over-labelling, under-labelling or error, and a count inside it does not show record-level agreement.",
        "Marginal counts do not show whether raters labelled the same records. Majority-referenced contingencies (Tables 3–4) are a different estimand: a labelwise majority set can contain more or fewer labels than individual sets.",
        "Unclear from Register Entry (declined to classify) is plotted below the substantive labels in each panel. All labels are shown, including those with zero applications.",
        "Rows keep the order of the former label-application figure: descending number of records to which the coder majority applied the label, ties alphabetical; the majority itself is not plotted [S5T001/S5T002 coder-majority-positive cells].",
        "Coder counts are exploratory descriptive summaries, not preregistered (specification dated 3 November 2026); Supplementary Table S13 gives labels per record and Unclear use by rater.",
    ]
    bullets["Supplementary Figure S1"] = list(old["Supplementary Figure S1"])
    bullets["Supplementary Figure S2"] = list(old["Supplementary Figure S2"])
    bullets["Supplementary Figure S3"] = [
        "Random baseline, n=150 records in every panel. The coder majority applied Demographic disparities / equity to 11 records and COVID-19 & Pandemic to 12, displayed beside each tag. With so few positive records the estimates are unstable and interpretation is limited [S2T001/S2T002 denominator and label-count cells].",
        "Krippendorff’s α with nominal distance. ABC is the all-human panel (C01, C02, C03); LBC, ALC and ABL replace C01, C02 and C03 respectively with Fable 5. δₐ = LBC − ABC, δᵦ = ALC − ABC, δ꜀ = ABL − ABC; δₘᵢₙ, the least favourable of the three, sits level with ABC [S2T001/S2T002 row cells].",
        "The annotation beside δₘᵢₙ identifies the component whose point estimate equals δₘᵢₙ: δᵦ for Demographic disparities / equity and δₐ for COVID-19 & Pandemic. The δₘᵢₙ interval is estimated separately and can differ from that component’s interval [S2T001/S2T002 point-estimate and interval cells].",
        old["Figure 1"][2],
        "For Demographic disparities / equity, all three replacement-difference point estimates are below zero and the δₘᵢₙ interval lies entirely below zero, so both preregistered review indicators were met; every component interval crosses zero [S4T003; S2T001 estimate and interval cells].",
        old["Figure 1"][3],
        "Intervals are percentile bootstrap intervals from 2,000 record resamples; their confidence level was not recorded, so they are not labelled 95% [S2T001/S2T002 status cells, confidence unresolved].",
    ]
    stab = composition["strata"]
    bullets["Supplementary Figure S4"] = [
        f"A, same-model repeatability: two independent Fable 5 runs on one fixed sample of 201 records, holding model, prompt (dict-1.0-rc2), taxonomy and input fields constant. The sample combined {stab['adjudicated']} purposively selected records (earlier spot-check, regression-test and stability-flagged cases) with {stab['random']} records drawn at random from the rest of the register, so its pooled results describe that sample only [fable_run_stability_metrics.json metrics; stability sample stratum column, hash-matched].",
        "B, cross-model agreement: Fable 5 against one GPT-5.5 run on the frozen register (1,308 records). GPT-5.5 received the production prompt without model-specific adaptation, so agreement measures sensitivity to model choice under this prompt and may also reflect prompt fit [fable5_gpt55_metrics.json comparison; protocol §4.3].",
        "Exact-set agreement is the proportion of records with identical label sets (numerator/denominator shown); mean Jaccard is the mean over records of shared labels divided by all labels used. Both are on a 0–1 scale. No intervals were computed for either analysis.",
        "Both are pre-existing descriptive analyses completed before preregistration (protocol §§4.2–4.3); they are not preregistered validation outcomes.",
        "The two panels cover different populations and are not a controlled comparison of how much higher repeatability is than cross-model agreement. Repeatability does not establish correctness.",
        "Whether cross-model disagreement marks records with lower human agreement is assessed separately in the baseline enrichment-calibration analysis (exploratory), not from these percentages.",
        "Supplementary Table S14 gives the tag metrics, exact-match numerators and denominators, and disagreement-frame counts before and after exclusions.",
    ]
    bullets["Figure 3 source table"] = [
        "One row per label and dimension; counts are records in the random baseline to which each rater applied the label. Denominator: the 150 valid common records for which all three coders and Fable 5 gave a complete, structurally valid set [LAC1T001 denominator cells].",
        "Coder counts, minimum and maximum come from the exploratory descriptive run LAC1T001 (not preregistered); Fable 5 counts are the preregistered S5T001/S5T002 model-positive exports and equal the LAC1T001 recount.",
        "Placement compares Fable 5 with the three coders’ counts only; it is not a judgement of correctness, and marginal counts do not show record-level agreement.",
    ]
    by = {(r["dimension"], r["rater"]): r for r in lac2}
    bullets["Supplementary Table S13"] = [
        "Random baseline; N=150 valid common records in each dimension for every rater (all three coders and Fable 5 gave a complete, structurally valid set) [LAC1T002 records_N cells].",
        "Mean substantive labels per record counts Unclear from Register Entry as zero substantive labels, so it combines willingness to classify with set size [LAC1T002 mean_substantive_labels_per_record cells].",
        "Records assigned Unclear are records whose set was Unclear from Register Entry; Unclear is never counted as a substantive label, no rater combined it with a substantive label and no set was empty [LAC1T002 unclear and check cells].",
        "Mean substantive labels among classified records conditions on the rater having applied at least one substantive label; its denominator is shown and differs between raters, so the records averaged over differ [LAC1T002 conditional cells].",
        "Coder-majority set sizes are not shown and are not a substitute for individual raters’ set sizes.",
        "Exploratory descriptive summaries, not preregistered (specification dated 3 November 2026); no intervals or tests.",
        f"Production note: means to two decimals; percentages whole numbers (e.g. C03 Analytical Purposes Unclear {by[('Analytical Purposes', 'C03')]['unclear_records']} of 150).",
    ]
    bullets["Supplementary Table S14"] = [
        "Column A: two Fable 5 runs on the fixed 201-record sample. Column B: Fable 5 against GPT-5.5 on the frozen 1,308-record register. Different populations; not a controlled comparison [fable_run_stability_metrics.json; fable5_gpt55_metrics.json].",
        "Agreement cells give records with identical output over records compared; tags are compared as two independent binary facets [metrics files, count and denominator fields].",
        "The disagreement frame counts records where Fable 5 and GPT-5.5 differed on Research Domains or Analytical Purposes, before and after removing the 22 training and pilot records; tag-only disagreements lie outside the frame [fable5_gpt55_metrics.json pre_exclusion, post_exclusion and exclusions fields].",
        "Pre-existing descriptive analyses completed before preregistration (protocol §§4.2–4.3); no intervals.",
        "Percentages are whole numbers; values of at least 99.5% but below 100% display as >99%.",
    ]
    return bullets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--pass4-log", type=Path, required=True)
    parser.add_argument("--pass3-log", type=Path, required=True)
    parser.add_argument("--findings-log", type=Path, required=True)
    parser.add_argument("--archive-existing", action="store_true")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()

    old = {deliverable: read_csv(pass3_path(data_dir, name)) for deliverable, name in PASS3_SOURCES.items()}
    old["Supplementary Figure S3"] = [row for row in old["Supplementary Figure S3"] if row["dimension"] in TAGS]
    label_counts = read_csv(pass3_path(data_dir, PASS3_LABEL_COUNTS))
    caption_source = PASS3_CAPTIONS_ARCHIVED if PASS3_CAPTIONS_ARCHIVED.is_file() else PASS3_CAPTIONS
    old_captions = old_bullets(caption_source)

    lac_metadata = json.loads((LAC_DIR / "run_metadata.json").read_text(encoding="utf-8"))
    if any(check["status"] != "passed" for check in lac_metadata["checks"]):
        raise RuntimeError("LAC1 run has failed checks")
    if lac_metadata["specification"]["sha256"] != sha256(LAC_SPEC):
        raise RuntimeError("LAC1 specification changed after the run")
    for name, digest in lac_metadata["outputs"].items():
        if sha256(LAC_DIR / name) != digest:
            raise RuntimeError(f"LAC1 output changed after the run: {name}")
    lac1, lac2 = read_csv(LAC_DIR / "LAC1T001.csv"), read_csv(LAC_DIR / "LAC1T002.csv")
    stability = json.loads(STABILITY.read_text(encoding="utf-8"))
    cross = json.loads(CROSS_MODEL.read_text(encoding="utf-8"))
    evidence_checks = evidence_assertions(stability, cross)
    composition = stability_composition(stability)

    datasets = {deliverable: clone(rows, deliverable) for deliverable, rows in old.items()}
    datasets["Figure 3"], placement = label_application_rows(lac1, label_counts)
    datasets["Figure 3 source table"] = clone(datasets["Figure 3"], "Figure 3 source table")
    datasets["Supplementary Table S13"] = cardinality_rows(lac2)
    datasets["Supplementary Figure S4"], datasets["Supplementary Table S14"] = evidence_rows(stability, cross, composition)

    carryover = carryover_check(old, datasets)
    fable_totals = {}
    for dimension, expected in {"Research Domains": (199, 198), "Analytical Purposes": (160, 159)}.items():
        fable = [r for r in datasets["Figure 3"] if r["dimension"] == dimension and r["pair"] == "Fable 5"]
        total = sum(int(r["parsed_value"]) for r in fable)
        substantive = total - sum(int(r["parsed_value"]) for r in fable if r["label"] == UNCLEAR)
        fable_totals[dimension] = [total, substantive]
        if (total, substantive) != expected:
            raise RuntimeError(f"G.12 derivations 3-4 failed for {dimension}: {(total, substantive)}")
    untraced = [(d, r["quantity"]) for d, rows in datasets.items() for r in rows
                if r["source_value_string"] and (not r["source_table_id"] or not (r["source_column_locator"] or r["derivation_id"]))]
    if untraced:
        raise RuntimeError(f"Untraced pass-4 values: {untraced}")
    bullets = captions(old_captions, placement, lac2, composition)

    archived = archive_pass3(data_dir) if args.archive_existing else []
    generated = datetime.now(timezone.utc).isoformat()
    logs = {}
    for path in (args.pass4_log.resolve(), args.pass3_log.resolve(), args.findings_log.resolve()):
        stat = path.stat()
        logs[path.name] = {"path": str(path), "sha256": sha256(path), "size_bytes": stat.st_size,
                           "last_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
    entries = {}
    for deliverable in ORDER:
        slug = SLUGS[deliverable]
        data_name, metadata_name = f"{slug}.csv", f"{slug}_metadata.json"
        write_csv(data_dir / data_name, datasets[deliverable])
        metadata = {"deliverable": deliverable, "slug": slug, "generated_utc": generated, "rows": len(datasets[deliverable]),
                    "numeric_baseline": "pass-3 figure data at 7e77c47" if deliverable in old else "new pass-4 inputs (see manifest provenance)",
                    "dimension_names": list(DIMENSION_NAMES)}
        (data_dir / metadata_name).write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        outputs = [f"{slug}.png", f"{slug}.svg"] if "Figure" in deliverable and "table" not in deliverable else [f"{slug}.csv", f"{slug}.md"]
        entries[deliverable] = {"slug": slug, "title": TITLES[deliverable], "inputs": {"data": data_name, "metadata": metadata_name},
                                "outputs": outputs, "caption_bullets": bullets[deliverable]}
    carried = {}
    for deliverable, slug in CARRIED_TABLES.items():
        carried[deliverable] = {"slug": slug, "data": f"{slug}.csv", "data_sha256": sha256(data_dir / f"{slug}.csv"),
                                "outputs": {name: sha256(ROOT / "analysis/tables" / name) for name in (f"{slug}.csv", f"{slug}.md")},
                                "caption_bullets": old_captions[deliverable], "title": None}
    manifest = {
        "generated_utc": generated, "entries": entries, "order": list(ORDER), "dimension_names": list(DIMENSION_NAMES),
        "carried_forward_tables": {
            "note": "Rendered in pass 3 and unchanged here; file numbering follows pass-3 H.7 pending the author's table-numbering decision.",
            "entries": carried,
        },
        "withheld": {WITHHELD_TABLE[0]: {"slug": WITHHELD_TABLE[1], "reason": "Unclear from Register Entry counts as a label; no export separates pairs where exactly one rater used Unclear only. Outside the publication set pending that correction; file left unchanged."},
                     "Supplementary Figure S5": {"slug": None, "reason": "Disagreement-composition figure; conditional on the decline-versus-classify correction, which does not exist. Not rendered; manuscript placeholder only. Pass-3 output archived."}},
        "unnumbered_placeholders": ["Adjudication figures (flow, blind Stage 1 ratings, drift, families by consensus state)",
                                    "Project-owner figures (recruitment flow, selection-design coverage)"],
        "axis_ranges": {"alpha_figure_1": [0.15, 0.75], "alpha_s1_s3": [0.0, 1.0], "delta_all": [-0.45, 0.45],
                        "figure_3_counts": [-1.5, 70.0], "s4": [0.0, 1.0]},
        "figure_3_placement": placement,
        "provenance": {
            "logs": logs, "archived_figure_data": archived, "head_at_run_start": git("rev-parse", "HEAD"),
            "pass3_figure_data": {deliverable: str(pass3_path(data_dir, name).relative_to(ROOT)).replace("\\", "/") for deliverable, name in PASS3_SOURCES.items()},
            "label_application_cardinality": {"directory": str(LAC_DIR.relative_to(ROOT)).replace("\\", "/"), "specification_sha256": lac_metadata["specification"]["sha256"],
                                              "outputs": lac_metadata["outputs"], "status": lac_metadata["status"]},
            "preexisting_model_evidence": {"stability": {"path": str(STABILITY.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(STABILITY)},
                                           "cross_model": {"path": str(CROSS_MODEL.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(CROSS_MODEL)},
                                           "stability_sample_composition": composition},
        },
        "assertions": {"carried_over_values": carryover, "g12_derivations_3_4_fable": {"status": "PASS", "totals": fable_totals},
                       "preexisting_evidence": evidence_checks, "lac1_checks": {"status": "PASS", "count": len(lac_metadata["checks"])},
                       "new_values_traced": {"status": "PASS"}},
    }
    (data_dir / "pass4_deliverable_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run_metadata = {
        "run_timestamp_utc": generated, "head_at_run_start": git("rev-parse", "HEAD"),
        "working_tree_note": "Pass-4 code and inputs were uncommitted at run time (investigator instruction: do not commit).",
        "logs": logs, "software": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform()},
        "assertions": manifest["assertions"],
    }
    (data_dir / "pass4_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
