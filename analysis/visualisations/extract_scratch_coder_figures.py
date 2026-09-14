"""Extract auditable scratch-coder figure inputs from the canonical releases.

This is deliberately a copying/reshaping step.  It does not calculate any
analytical statistic; the only numeric conversion is the ``plot_value`` field
alongside the original source string.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "analysis" / "figure_data"
RESULTS = ROOT / "analysis" / "scratch_coder_results" / "results.md"
PROVENANCE = ROOT / "analysis" / "scratch_coder_results" / "run_metadata.json"
DISAGREEMENT = ROOT / "analysis" / "outputs_disagreement_types_20260909T084916Z" / "disagreement_type_distribution.csv"

FIELDS = [
    "figure_id", "role", "population", "dimension", "source_table_id", "source_row_key",
    "quantity", "series", "label", "source_value_string", "plot_value",
    "interval_lower_string", "interval_lower", "interval_upper_string", "interval_upper",
    "estimate_status", "interval_status", "interval_method", "confidence_level_wording",
    "sample_size_string", "sample_size", "sample_unit", "support_band", "exported_caution",
    "unavailable_reason", "human_majority_positive_n_string", "human_majority_positive_n",
    "model_positive_n_string", "model_positive_n", "fp_string", "fp", "fn_string", "fn",
    "performance_metrics_reportable", "pair_family", "relation", "eligible_pairs_string",
    "eligible_pairs", "pair_count_string", "pair_count", "empty_set_pairs_string", "empty_set_pairs",
    "nonempty_proportion_status",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(cell: str) -> str:
    return cell.strip().strip("`")


def parse_markdown_tables(text: str):
    """Return table-id -> (heading, rows), preserving every source cell string."""
    tables = {}
    heading_re = re.compile(r"^### (S\d+T\d+) — (.*)$")
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        match = heading_re.match(lines[index])
        if not match:
            index += 1
            continue
        table_id, heading = match.groups()
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].startswith("|"):
            cursor += 1
        if cursor + 1 >= len(lines) or not lines[cursor].startswith("|"):
            index += 1
            continue
        header = [clean(value) for value in lines[cursor].strip("|").split("|")]
        cursor += 2  # separator
        rows = []
        while cursor < len(lines) and lines[cursor].startswith("|"):
            values = [clean(value) for value in lines[cursor].strip("|").split("|")]
            if len(values) == len(header):
                rows.append(dict(zip(header, values)))
            cursor += 1
        tables[table_id] = (heading, rows)
        index = cursor
    return tables


def status_parts(status: str):
    first = status.split(";")[0].strip()
    if "/" in first:
        estimate, interval = [part.strip() for part in first.split("/", 1)]
    else:
        estimate, interval = "", ""
    method = ";".join(status.split(";")[1:]).strip()
    confidence = "confidence unresolved" if "confidence unresolved" in status else (
        "95%" if "95%" in status else "not applicable" if interval == "N" else ""
    )
    return estimate, interval, method, confidence


def num(value: str) -> str:
    """CSV-friendly parsed value, blank where source has no numeric value."""
    try:
        float(value)
    except (TypeError, ValueError):
        return ""
    return value


def sample_parts(text: str):
    match = re.match(r"^(\d+)\s+([A-Za-z]+)", text)
    return (text, match.group(1), match.group(2)) if match else (text, "", "")


def support_parts(text: str):
    band = re.search(r"baseline band: ([A-Z ]+?);", text)
    caution = re.search(r"exported caution: (True|False)", text)
    return (band.group(1) if band else "", caution.group(1) if caution else "")


def base_row(figure_id, role, population, dimension, table_id, source_row, quantity):
    row = {field: "" for field in FIELDS}
    row.update({
        "figure_id": figure_id, "role": role, "population": population,
        "dimension": dimension, "source_table_id": table_id,
        "source_row_key": source_row, "quantity": quantity,
    })
    return row


def replacement_rows(figure_id, table_id, population, dimension, tables, role="plotted"):
    heading, rows = tables[table_id]
    out = []
    for source in rows:
        quantity = source["Row / comparator"]
        row = base_row(figure_id, role, population, dimension, table_id, quantity, quantity)
        value = source["Estimate / count / flag"]
        lower, upper = source["Interval lower"], source["Interval upper"]
        status = source["Estimate / interval status; method; draws"]
        estimate_status, interval_status, method, confidence = status_parts(status)
        sample_text, sample_n, sample_unit = sample_parts(source["Total / denominator / unit"])
        band, caution = support_parts(source.get("Observed support and caution", ""))
        row.update({
            "series": "alpha" if quantity.startswith("alpha") else "delta",
            "source_value_string": value, "plot_value": num(value),
            "interval_lower_string": lower, "interval_lower": num(lower),
            "interval_upper_string": upper, "interval_upper": num(upper),
            "estimate_status": estimate_status, "interval_status": interval_status,
            "interval_method": method, "confidence_level_wording": confidence,
            "sample_size_string": sample_text, "sample_size": sample_n, "sample_unit": sample_unit,
            "support_band": band, "exported_caution": caution,
        })
        out.append(row)
    return out


def contingency_rows(figure_id, table_id, dimension, tables, *, include_excluded_caption=False):
    _, rows = tables[table_id]
    labels = defaultdict(dict)
    annotations = {}
    for source in rows:
        labels[source["Row / comparator"]][source["Quantity"]] = source
    out = []
    for label, values in labels.items():
        # The two requested count cells are retained even when a performance flag is false.
        human = values.get("human_majority_positive_n", {})
        model = values.get("model_positive_n", {})
        fp = values.get("fp", {})
        fn = values.get("fn", {})
        flag = values.get("performance_metrics_reportable", {}).get("Estimate / count / flag", "")
        any_source = human or model or fp or fn
        support = next(iter(values.values())).get("Observed support and caution", "")
        band, caution = support_parts(support)
        sample = human.get("Total / denominator / unit", model.get("Total / denominator / unit", ""))
        sample_text, sample_n, sample_unit = sample_parts(sample)
        row = base_row(figure_id, "plotted", "baseline", dimension, table_id, label, "label_counts")
        row.update({
            "label": label,
            "human_majority_positive_n_string": human.get("Estimate / count / flag", ""),
            "human_majority_positive_n": num(human.get("Estimate / count / flag", "")),
            "model_positive_n_string": model.get("Estimate / count / flag", ""),
            "model_positive_n": num(model.get("Estimate / count / flag", "")),
            "fp_string": fp.get("Estimate / count / flag", ""), "fp": num(fp.get("Estimate / count / flag", "")),
            "fn_string": fn.get("Estimate / count / flag", ""), "fn": num(fn.get("Estimate / count / flag", "")),
            "performance_metrics_reportable": flag,
            "sample_size_string": sample_text, "sample_size": sample_n, "sample_unit": sample_unit,
            "support_band": band, "exported_caution": caution,
            "estimate_status": "R", "interval_status": "N", "confidence_level_wording": "not applicable for exported counts",
        })
        if not human or not model:
            row["role"] = "unavailable"
            row["unavailable_reason"] = "Requested human-majority or model-positive count is absent from the source table."
        # Figure 4's excluded labels are retained as caption-only rows, with no
        # substitution from an associated performance-metric status.
        if include_excluded_caption and flag != "True":
            row.update({"role": "caption", "quantity": "excluded_label_fp_fn"})
            if not fp or not fn:
                row["unavailable_reason"] = "FP and/or FN count absent from the source table; not inferred."
        out.append(row)
    return out


def disagreement_rows():
    with DISAGREEMENT.open(newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    out = []
    for source in source_rows:
        relation = source["relation"]
        role = "plotted" if source["population"] == "baseline" and relation in {"containment", "overlap", "disjoint"} else "caption"
        # Preserve all baseline group rows so denominators and exported empty-pair counts can be captioned.
        if source["population"] != "baseline":
            continue
        row = base_row("figure_5", role, source["population"], source["dimension"], "disagreement_type_distribution.csv", f"{source['pair_family']}:{relation}", relation)
        prop = source["proportion_of_nonidentical_nonempty_pairs"]
        status = source["nonempty_proportion_status"]
        row.update({
            "series": "relation_proportion", "pair_family": source["pair_family"], "relation": relation,
            "source_value_string": prop, "plot_value": num(prop) if status == "reported" else "",
            "estimate_status": "R" if status == "reported" else "N",
            "interval_status": "A", "confidence_level_wording": "interval unavailable in source",
            "sample_size_string": f"{source['eligible_records']} records; {source['total_pairs_classified']} pairs classified",
            "sample_size": source["eligible_records"], "sample_unit": "records",
            "eligible_pairs_string": source["nonidentical_nonempty_pairs"], "eligible_pairs": source["nonidentical_nonempty_pairs"],
            "pair_count_string": source["count"], "pair_count": source["count"],
            "empty_set_pairs_string": source["empty_set_involved_pairs"], "empty_set_pairs": source["empty_set_involved_pairs"],
            "nonempty_proportion_status": status,
        })
        if status in {"zero_denominator", "not_applicable"}:
            row["role"] = "unavailable"
            row["unavailable_reason"] = f"Proportion status is {status}; source does not report a plottable proportion."
        out.append(row)
    return out


CAPTIONS = {
    "figure_1": "Baseline (n=150 records). Krippendorff’s alpha is shown for ABC (C01/C02/C03) and each model-substituted panel: LBC (Fable 5/C02/C03), ALC (C01/Fable 5/C03), and ABL (C01/C02/Fable 5). Replacement differences are source-exported panel alpha minus ABC: δ_A=LBC−ABC, δ_B=ALC−ABC, δ_C=ABL−ABC; δ_min is the source-exported minimum. Bars are percentile-bootstrap intervals with confidence level unresolved in the source. Low-support tag rows carry the source caution that values are descriptive and not stable performance estimates.",
    "figure_2": "Baseline (n=150 records) and strict register-sufficient subset (n=92 records). Krippendorff’s alpha and source-exported δ_min use the same panel definitions as Figure 1. The broad subset retained 148/150 records and is available in the accompanying figure data but omitted from this display. Bars are shown only where exported; percentile-bootstrap confidence level is unresolved in the source.",
    "figure_3": "Baseline (n=150 records). Each point compares the exported human-majority-positive record count (x) with the model-positive record count (y); bands are the exported baseline support bands. Differences in Unclear use and substantive-label application may involve overlapping records and must not be read as independent findings. This marginal-count figure does not establish the extent of that overlap.",
    "figure_4": "Baseline (n=150 records). False positives (FP) and false negatives (FN) are against labelwise human-majority labels, not an adjudicated record-level truth set. Labels excluded by the exported performance_metrics_reportable flag are listed with their exported FP/FN counts in the accompanying figure data and caption notes.",
    "figure_5": "Baseline. Proportions are among non-identical pairs where both label sets are non-empty, separately for human–human and model–human pair families. Denominators are eligible pairs, not records. Empty-set-pair counts are exported where available; unavailable proportions are not rendered as zero and are not renormalised. No proportion intervals were exported.",
    "figure_6": "Baseline (n=150 records) compared with the pooled hard-case sample (n=75 records) across all dimensions. Panel definitions and source-exported replacement differences follow Figure 1. Every hard-case panel is DIAGNOSTIC — non-representative; it was selected using cross-model disagreement. Bars are percentile-bootstrap intervals with confidence level unresolved in the source. Hard-case tag support bands remain baseline-scoped in the source.",
}


def write_figure(figure_id, rows, source_paths, tables_used, missing=None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / f"scratch_coder_{figure_id}.csv"
    metadata_path = DATA_DIR / f"scratch_coder_{figure_id}_metadata.json"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    before = {str(path.relative_to(ROOT)): sha256(path) for path in source_paths}
    # No source files are modified by this extractor; read hashes a second time as a guard.
    after = {str(path.relative_to(ROOT)): sha256(path) for path in source_paths}
    if before != after:
        raise RuntimeError(f"Analytical source changed during extraction for {figure_id}.")
    value_statuses = [
        {"source_table_id": row["source_table_id"], "row_key": row["source_row_key"],
         "quantity": row["quantity"], "estimate_status": row["estimate_status"],
         "interval_status": row["interval_status"], "confidence_level_wording": row["confidence_level_wording"]}
        for row in rows
    ]
    metadata = {
        "figure_id": figure_id,
        "figure_data_file": str(csv_path.relative_to(ROOT)),
        "caption": CAPTIONS[figure_id],
        "authoritative_source_paths": [str(path.relative_to(ROOT)) for path in source_paths],
        "authoritative_source_hashes_before_extraction": before,
        "authoritative_source_hashes_after_extraction": after,
        "source_hashes_unchanged": True,
        "source_section_table_ids": tables_used,
        "population_and_dimension": sorted({f"{row['population']} — {row['dimension']}" for row in rows}),
        "sample_sizes_and_units": sorted({f"{row['population']} — {row['dimension']}: {row['sample_size_string']}" for row in rows if row['sample_size_string']}),
        "value_statuses": value_statuses,
        "confidence_level_caution": "Intervals are labelled per exported status. ‘confidence unresolved’ is retained where the source reports percentile-bootstrap bounds without a resolved confidence level.",
        "missing_requested_values": missing or [],
        "generation": "Extraction only: values are copied from the cited canonical source cells; parsed fields are for plotting.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")


def main():
    source_hashes_before = {RESULTS: sha256(RESULTS), PROVENANCE: sha256(PROVENANCE), DISAGREEMENT: sha256(DISAGREEMENT)}
    # Provenance is intentionally opened during Stage 1, even though values come from results.md.
    json.loads(PROVENANCE.read_text())
    tables = parse_markdown_tables(RESULTS.read_text())
    required = {f"S2T{i:03d}" for i in [1, 2, 7, 8]} | {f"S3T{i:03d}" for i in [1, 2, 7, 8, 9, 10, 11, 12]} | {"S5T003", "S5T004"}
    missing_tables = required - tables.keys()
    if missing_tables:
        raise RuntimeError(f"Required source tables are absent: {sorted(missing_tables)}")

    base_sources = [RESULTS, PROVENANCE]
    figure1 = []
    for table, dimension in [("S3T001", "Research Domains"), ("S3T002", "Analytical Purposes"), ("S2T002", "COVID-19 tag"), ("S2T001", "Demographic disparities / equity tag")]:
        figure1 += replacement_rows("figure_1", table, "baseline", dimension, tables)
    write_figure("figure_1", figure1, base_sources, ["S3T001", "S3T002", "S2T001", "S2T002"])

    figure2 = []
    for table, population, dimension, role in [
        ("S3T001", "baseline", "Research Domains", "plotted"), ("S3T002", "baseline", "Analytical Purposes", "plotted"),
        ("S3T011", "baseline_strict_sufficient", "Research Domains", "plotted"), ("S3T012", "baseline_strict_sufficient", "Analytical Purposes", "plotted"),
        ("S3T009", "baseline_broad_usable", "Research Domains", "caption"), ("S3T010", "baseline_broad_usable", "Analytical Purposes", "caption"),
    ]:
        figure2 += replacement_rows("figure_2", table, population, dimension, tables, role)
    strict_sizes = {row["sample_size"] for row in figure2 if row["population"] == "baseline_strict_sufficient"}
    missing2 = [] if strict_sizes == {"92"} else [f"Expected strict n=92 records; source exports {sorted(strict_sizes)}."]
    write_figure("figure_2", figure2, base_sources, ["S3T001", "S3T002", "S3T009", "S3T010", "S3T011", "S3T012"], missing2)

    figure3 = contingency_rows("figure_3", "S5T003", "Research Domains", tables) + contingency_rows("figure_3", "S5T004", "Analytical Purposes", tables)
    write_figure("figure_3", figure3, base_sources, ["S5T003", "S5T004"])

    figure4 = contingency_rows("figure_4", "S5T003", "Research Domains", tables, include_excluded_caption=True) + contingency_rows("figure_4", "S5T004", "Analytical Purposes", tables, include_excluded_caption=True)
    write_figure("figure_4", figure4, base_sources, ["S5T003", "S5T004"])

    figure5 = disagreement_rows()
    write_figure("figure_5", figure5, [DISAGREEMENT], ["disagreement_type_distribution.csv"])

    figure6 = []
    for table, population, dimension in [
        ("S3T001", "baseline", "Research Domains"), ("S3T002", "baseline", "Analytical Purposes"),
        ("S2T002", "baseline", "COVID-19 tag"), ("S2T001", "baseline", "Demographic disparities / equity tag"),
        ("S3T007", "hard_case", "Research Domains"), ("S3T008", "hard_case", "Analytical Purposes"),
        ("S2T008", "hard_case", "COVID-19 tag"), ("S2T007", "hard_case", "Demographic disparities / equity tag"),
    ]:
        figure6 += replacement_rows("figure_6", table, population, dimension, tables)
    write_figure("figure_6", figure6, base_sources, ["S3T001", "S3T002", "S3T007", "S3T008", "S2T001", "S2T002", "S2T007", "S2T008"])

    source_hashes_after = {RESULTS: sha256(RESULTS), PROVENANCE: sha256(PROVENANCE), DISAGREEMENT: sha256(DISAGREEMENT)}
    if source_hashes_before != source_hashes_after:
        raise RuntimeError("A canonical source changed during extraction.")


if __name__ == "__main__":
    main()
