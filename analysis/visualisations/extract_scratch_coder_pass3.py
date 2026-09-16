"""Stage 1 for the pass-3 scratch-coder presentation run.

This stage reads the committed pass-2 figure data as its numeric baseline.  It
renumbers and splits deliverables, records presentation metadata, and repeats
the approved G.12 assertions.  It does not read record-level inputs or rerun an
analysis.
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
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PASS2_DATA = ROOT / "analysis/figure_data"
PASS2_CAPTIONS = ROOT / "analysis/figures/draft_captions_pass2.md"
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
    "Figure 1", "Figure 2", "Figure 3", "Figure 4",
    "Table 1", "Table 2", "Table 3", "Table 4",
    "Supplementary Figure S1", "Supplementary Figure S2", "Supplementary Figure S3",
    "Supplementary Table S1a", "Supplementary Table S1b", "Supplementary Table S1c",
    "Supplementary Table S2",
)
SLUGS = {
    "Figure 1": "figure_1_panel_agreement_replacement",
    "Figure 2": "figure_2_coder_ratings_baseline",
    "Figure 3": "figure_3_sufficiency_sensitivity",
    "Figure 4": "figure_4_label_application",
    "Table 1": "table_1_agreement_domains",
    "Table 2": "table_2_agreement_purposes",
    "Table 3": "table_3_agreement_with_majority_domains",
    "Table 4": "table_4_agreement_with_majority_purposes",
    "Supplementary Figure S1": "supplementary_figure_s1_baseline_vs_hardcase",
    "Supplementary Figure S2": "supplementary_figure_s2_hardcase_ratings_confidence",
    "Supplementary Figure S3": "supplementary_figure_s3_disagreement_composition",
    "Supplementary Table S1a": "supplementary_table_s1a_register_information",
    "Supplementary Table S1b": "supplementary_table_s1b_taxonomy_fit",
    "Supplementary Table S1c": "supplementary_table_s1c_agreed_labels",
    "Supplementary Table S2": "supplementary_table_s2_disagreement_composition",
}
TITLES = {
    "Figure 1": "Replacing a human coder with Fable 5: panel agreement and replacement differences",
    "Figure 2": "Register-entry information and taxonomy fit: ratings by each coder and by the majority of coders",
    "Figure 3": "Agreement and replacement differences for all baseline records and for those whose register entry coders judged sufficient to classify",
    "Figure 4": "Label application counts: Fable 5 against the coder majority",
    "Table 1": "Research Domains: agreement on each label between pairs of human coders and between Fable 5 and each coder",
    "Table 2": "Analytical Purposes: agreement on each label between pairs of human coders and between Fable 5 and each coder",
    "Table 3": "Research Domains: agreement on each label between Fable 5 and the coder majority",
    "Table 4": "Analytical Purposes: agreement on each label between Fable 5 and the coder majority",
    "Supplementary Figure S1": "Replacing a human coder with Fable 5 in a non-representative hard-case sample (diagnostic)",
    "Supplementary Figure S2": "Coder ratings in the hard-case sample, and coder confidence in both samples",
    "Supplementary Figure S3": "Kinds of disagreement between pairs of human coders and between Fable 5 and each coder",
    "Supplementary Table S1a": "Majority ratings of whether the register entry gave enough information to classify the project",
    "Supplementary Table S1b": "Majority ratings of how well the taxonomy fitted the project",
    "Supplementary Table S1c": "Number of labels agreed by at least two of three coders per record",
    "Supplementary Table S2": "Kinds of disagreement between pairs of human coders and between Fable 5 and each coder: number and percentage of disagreeing pairs",
}
DIMENSION_NAMES = (
    "Research Domains", "Analytical Purposes", "Demographic disparities / equity", "COVID-19 & Pandemic"
)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clone_rows(rows: list[dict], deliverable: str) -> list[dict]:
    copied = deepcopy(rows)
    for row in copied:
        row["deliverable_id"] = deliverable
    return copied


def archive_pass2_data(data_dir: Path, names: set[str]) -> list[dict]:
    archive = data_dir / "archive" / "pass3_preexisting_64679cf"
    existing = [data_dir / name for name in sorted(names) if (data_dir / name).is_file()]
    if existing:
        archive.mkdir(parents=True, exist_ok=True)
    moved = []
    for source in existing:
        target = archive / source.name
        if target.exists():
            raise RuntimeError(f"Archive target already exists: {target}")
        shutil.move(source, target)
        moved.append({"from": str(source), "to": str(target)})
    return moved


def whole_percent(value: str) -> int:
    return int((Decimal(value) * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def update_groups(datasets: dict[str, list[dict]]) -> None:
    for deliverable in ("Table 1", "Table 2", "Table 3", "Table 4"):
        for row in datasets[deliverable]:
            if row["label"] == "Unclear from Register Entry":
                row["row_group"] = "Declined to classify (10–29 records; interpret with caution)"
            elif row["support_band"] == "STANDARD":
                row["row_group"] = "30 or more records"
            elif row["support_band"] == "LOW SUPPORT":
                row["row_group"] = "10–29 records (interpret with caution)"
            else:
                row["row_group"] = "Fewer than 10 records (counts only)"


def number_figure4(rows: list[dict]) -> dict[str, list[dict]]:
    orders = {}
    for dimension in DIMENSION_NAMES[:2]:
        selected = [row for row in rows if row["dimension"] == dimension]
        selected.sort(key=lambda row: (-int(row["parsed_value"]), row["label"]))
        orders[dimension] = []
        for number, row in enumerate(selected, 1):
            row["source_order"] = str(number)
            row["presentation_note"] = (row["presentation_note"] + "; " if row["presentation_note"] else "") + "pass-3 point number: descending coder-majority count, ties alphabetical"
            orders[dimension].append({"number": number, "label": row["label"], "coder_majority_count": int(row["parsed_value"])})
    return orders


def numeric_inventory(datasets: dict[str, list[dict]]) -> dict[tuple[str, ...], set[str]]:
    fields = (
        "source_value_string", "parsed_value", "interval_lower_string", "parsed_interval_lower",
        "interval_upper_string", "parsed_interval_upper", "sample_size", "support_string", "display_percent",
    )
    inventory: dict[tuple[str, ...], set[str]] = defaultdict(set)
    for rows in datasets.values():
        for row in rows:
            base = (
                row["source_table_id"], row["source_row_key"], row["population"], row["dimension"],
                row["label"], row["pair"], row["series"], row["quantity"], row["derivation_id"],
            )
            for field in fields:
                if row.get(field, "") != "":
                    inventory[base + (field,)].add(row[field])
    return inventory


def carryover_check(old: dict[str, list[dict]], new: dict[str, list[dict]]) -> dict:
    before, after = numeric_inventory(old), numeric_inventory(new)
    common = sorted(set(before) & set(after))
    changes = [{"key": key, "old": sorted(before[key]), "new": sorted(after[key])} for key in common if before[key] != after[key]]
    unmatched = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    result = {
        "status": "PASS" if not changes and not unmatched and not added else "FAIL",
        "matched": len(common), "identical": len(common) - len(changes), "changes": changes,
        "unmatched_legacy": len(unmatched), "new_without_legacy_counterpart": len(added),
        "unmatched_legacy_keys": unmatched, "new_keys": added,
    }
    if result["status"] != "PASS":
        raise RuntimeError(f"Pass-3 carried-over numeric values failed: {result}")
    return result


def g12_assertions(datasets: dict[str, list[dict]], pass2_metadata: dict) -> dict:
    previous = pass2_metadata["assertions"]["g12_derivations"]
    if previous["status"] != "PASS":
        raise RuntimeError("Pass-2 G.12 prerequisite did not pass")
    s1c = datasets["Supplementary Table S1c"]
    expected_rows = {
        ("baseline", "Analytical Purposes"): ([24, 26, 97, 3, 0], [16, 17, 65, 2, 0]),
        ("baseline", "Research Domains"): ([5, 13, 107, 22, 3], [3, 9, 71, 15, 2]),
        ("hard_case", "Analytical Purposes"): ([9, 20, 42, 4, 0], [12, 27, 56, 5, 0]),
        ("hard_case", "Research Domains"): ([6, 3, 45, 18, 3], [8, 4, 60, 24, 4]),
    }
    checked = []
    for key, (counts_expected, pct_expected) in expected_rows.items():
        selected = sorted([r for r in s1c if (r["population"], r["dimension"]) == key], key=lambda r: int(r["source_order"]))
        counts = [int(r["source_value_string"]) for r in selected]
        percentages = [int(r["display_percent"]) for r in selected]
        status = "PASS" if counts == counts_expected and percentages == pct_expected and sum(percentages) == 100 else "FAIL"
        checked.append({"population": key[0], "dimension": key[1], "counts": counts, "percentages": percentages, "status": status})
    label_rows = datasets["Figure 4"]
    totals = {}
    substantive = {}
    for dimension in DIMENSION_NAMES[:2]:
        rows = [r for r in label_rows if r["dimension"] == dimension]
        model = sum(int(r["parsed_interval_lower"]) for r in rows)
        majority = sum(int(r["parsed_value"]) for r in rows)
        unclear = next(r for r in rows if r["label"] == "Unclear from Register Entry")
        totals[dimension] = [model, majority]
        substantive[dimension] = [model - int(unclear["parsed_interval_lower"]), majority - int(unclear["parsed_value"])]
    expected_totals = {"Research Domains": [199, 173], "Analytical Purposes": [160, 129]}
    expected_substantive = {"Research Domains": [198, 160], "Analytical Purposes": [159, 103]}
    status = "PASS" if all(r["status"] == "PASS" for r in checked) and totals == expected_totals and substantive == expected_substantive else "FAIL"
    result = {"status": status, "derivations_1_and_2": checked, "derivation_3": totals, "derivation_4": substantive}
    if status != "PASS":
        raise RuntimeError(f"G.12 assertion failed: {result}")
    return result


def totals_assertion(datasets: dict[str, list[dict]]) -> dict:
    checks = []
    for deliverable in ("Figure 2", "Supplementary Figure S2"):
        grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        for row in datasets[deliverable]:
            if row["role"] == "plotted":
                grouped[(row["dimension"], row["population"], row["pair"])].append(row)
        for key, rows in sorted(grouped.items()):
            observed = sum(int(r["parsed_value"]) for r in rows)
            denominator = int(rows[0]["sample_size"])
            checks.append({"deliverable": deliverable, "construct": key[0], "population": key[1], "bar": key[2],
                           "observed_sum": observed, "denominator": denominator, "status": "PASS" if observed == denominator else "FAIL"})
    if any(check["status"] != "PASS" for check in checks):
        raise RuntimeError(f"Category total assertion failed: {checks}")
    return {"status": "PASS", "checks": checks}


def trace_assertion(datasets: dict[str, list[dict]]) -> dict:
    failures = []
    checked = 0
    for deliverable, rows in datasets.items():
        for row in rows:
            numeric = any(row.get(field) for field in ("source_value_string", "interval_lower_string", "interval_upper_string"))
            if not numeric:
                continue
            checked += 1
            if not row["source_table_id"] or (not row["source_column_locator"] and not row["derivation_id"]):
                failures.append({"deliverable": deliverable, "row": row["source_row_key"], "quantity": row["quantity"]})
    if failures:
        raise RuntimeError(f"Untraced pass-3 values: {failures}")
    return {"status": "PASS", "numeric_rows_checked": checked, "failures": []}


def caption_sections(old_text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current = None
    for line in old_text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip(); result[current] = []
        elif current and line.startswith("- "):
            result[current].append(line[2:])
    return result


def captions(old_text: str, datasets: dict[str, list[dict]]) -> dict[str, list[str]]:
    old = caption_sections(old_text)
    bullets: dict[str, list[str]] = {}
    bullets["Figure 1"] = [
        "Baseline n=150 records in every panel; Demographic disparities / equity and COVID-19 & Pandemic were applied by the coder majority to 11 and 12 records respectively [S2T001/S2T002 denominator and label-count cells; displayed 11 and 12].",
        old["Figure 1"][1],
        old["Figure 1"][2].replace("For equity", "For Demographic disparities / equity"),
        "For COVID-19 & Pandemic, the exported δₐ and δₘᵢₙ point estimates and percentile interval bounds are exactly 0.0 (display 0.000 [0.000, 0.000]) [S2T002 estimate and interval cells].",
        "The annotation beside δₘᵢₙ identifies the component whose point estimate equals δₘᵢₙ: δᵦ for Research Domains, Analytical Purposes and Demographic disparities / equity, and δₐ for COVID-19 & Pandemic. The δₘᵢₙ interval is estimated separately and can differ from that component’s interval [S3T001/S3T002/S2T001/S2T002 point-estimate and interval cells].",
        "The two tag dimensions have 10–29 coder-majority-positive baseline records and are shown for description; their estimates are not stable [S2T001/S2T002 label-count and band cells].",
    ]
    s1a = datasets["Supplementary Table S1a"]
    sufficient = {(r["population"], r["quantity"]): r for r in s1a if r["label"] == "Sufficient"}
    prop = sufficient[("baseline", "proportion")]
    count = sufficient[("baseline", "count")]["source_value_string"]
    bullets["Figure 2"] = [
        "Baseline n=150; bars show C01, C02, C03 and the majority of coders for register-entry information and taxonomy fit [S8T001/S8T003/S9T001/S9T003 denominator cells].",
        "A majority rating is the category chosen by at least two of three coders; otherwise the result is No majority [S8T003/S9T003 category cells].",
        f"The Sufficient majority count is {count}; proportion={prop['source_value_string']} with 95% Wilson interval [{prop['interval_lower_string']}, {prop['interval_upper_string']}] (display 61% [53%, 69%]) [S8T003 count, proportion and interval cells].",
        "Figure 3’s strict subset is the 92 records with a Sufficient majority. The broad subset is 148 records and is not obtained by adding the Sufficient and Partially sufficient majority counts [S8T003/S8T005 count cells].",
        "Percentages are rounded half up to whole numbers, so some displayed bar labels sum to 99% or 101% [S8T001/S8T003/S9T001/S9T003 full-precision proportion cells].",
        "Supplementary Tables S1a–S1b give exact majority values; Supplementary Figure S2 gives hard-case ratings and confidence [S8T001–S8T004/S9T001–S9T004 and SCF1T001 onwards].",
    ]
    bullets["Figure 3"] = [
        old["Figure 2"][0].replace("strict register-sufficient", "register entry judged sufficient"),
        "The annotation beside the pair of δₘᵢₙ stars identifies δᵦ as the component whose point estimate equals δₘᵢₙ in both dimensions and populations. Each δₘᵢₙ interval is estimated separately and can differ from δᵦ’s interval [S3T001/S3T002/S3T011/S3T012 point-estimate and interval cells].",
        old["Figure 2"][2].replace("strict domains", "register-entry-sufficient Research Domains"),
        old["Figure 2"][3].replace("Figure 1", "Figure 1").replace("Supplementary Figure S1", "Supplementary Figure S1"),
        "The register-entry-sufficient subset contains records for which at least two of three coders rated the register entry Sufficient (n=92) [S8T003/S8T005 count cells].",
    ]
    bullets["Figure 4"] = [
        old["Figure 3"][0].replace("domain", "Research Domains").replace("purpose", "Analytical Purposes"),
        old["Figure 3"][1], old["Figure 3"][2], old["Figure 3"][3], old["Figure 3"][4],
        "Point numbers run in descending coder-majority count within each panel, with alphabetical tie-breaking; full label names are listed below each panel [S5T001/S5T002 coder-majority-positive cells].",
    ]
    for table in ("Table 1", "Table 2", "Table 3", "Table 4"):
        bullets[table] = list(old[table])
        extra = "Groups are defined by the number of records to which the coder majority applied the label; labels in the 10–29 group have fewer records and may have wider intervals"
        if table in {"Table 3", "Table 4"}:
            extra += "; labels below 10 show counts only"
        bullets[table].append(extra + " [S5T001/S5T002 exported band and count cells].")
    bullets["Table 3"].append("Production note: set this nine-column table in landscape or at a reduced manuscript font size.")
    bullets["Table 4"].append("Production note: set this nine-column table in landscape or at a reduced manuscript font size.")
    bullets["Supplementary Figure S1"] = [
        old["Supplementary Figure S1"][0],
        "Demographic disparities / equity was applied by the coder majority to 11 baseline and 8 hard-case records; COVID-19 & Pandemic to 12 and 6. The 10–29 caution band refers to baseline counts [S2T001/S2T002/S2T017/S2T018 count and band cells].",
        old["Supplementary Figure S1"][2].replace("domains", "Research Domains").replace("purposes", "Analytical Purposes").replace("equity", "Demographic disparities / equity").replace("COVID-19", "COVID-19 & Pandemic"),
        old["Supplementary Figure S1"][3].replace("Hard-case equity", "Hard-case Demographic disparities / equity"),
        "For baseline COVID-19 & Pandemic δₐ and δₘᵢₙ, and hard-case COVID-19 & Pandemic δ꜀ and δₘᵢₙ, the exported point estimates and percentile interval bounds are exactly 0.0 (display 0.000 [0.000, 0.000]) [S2T002/S2T008 estimate and interval cells].",
        "The hard-case Demographic disparities / equity δₘᵢₙ interval upper bound is exactly 0.0 (display 0.000), so the interval reaches zero [S2T007 interval-upper cell].",
    ]
    bullets["Supplementary Figure S2"] = [
        "Hard-case register-entry information and taxonomy-fit panels use n=75 and are diagnostic and non-representative; confidence panels use baseline n=150 and hard-case n=75 [S8T002/S8T004/S9T002/S9T004 and SCF1T001–SCF1T009 denominator cells].",
        old["Supplementary Figure S2"][1] + " The addendum documents this status.",
        old["Supplementary Figure S2"][2], old["Supplementary Figure S2"][3],
        "A majority rating is the category chosen by at least two of three coders; otherwise the result is No majority [S8T004/S9T004 and confidence majority cells].",
        "Supplementary Tables S1a–S1b give the exact register-entry information and taxonomy-fit majority values; Figure 2 gives the corresponding baseline coder and majority ratings [S8T001–S8T004/S9T001–S9T004 cells].",
    ]
    bullets["Supplementary Figure S3"] = list(old["Figure 4"])
    bullets["Supplementary Figure S3"].append("Supplementary Table S2 gives the corresponding counts and percentages [disagreement_type_distribution.csv count and proportion cells].")
    bullets["Supplementary Table S1a"] = [b.replace("Supplementary Figure S2", "Figure 2 and Supplementary Figure S2") for b in old["Supplementary Table S1a"]]
    bullets["Supplementary Table S1b"] = [b.replace("Supplementary Figure S2", "Figure 2 and Supplementary Figure S2") for b in old["Supplementary Table S1b"]]
    bullets["Supplementary Table S1c"] = list(old["Supplementary Table S1c"])
    bullets["Supplementary Table S2"] = [b.replace("Table 5", "Supplementary Table S2") for b in old["Table 5"]]
    bullets["Supplementary Table S2"].append("Supplementary Figure S3 displays the same composition proportions [disagreement_type_distribution.csv count and proportion cells].")
    return bullets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=PASS2_DATA)
    parser.add_argument("--pass3-log", type=Path, required=True)
    parser.add_argument("--pass2-log", type=Path, required=True)
    parser.add_argument("--findings-log", type=Path, required=True)
    parser.add_argument("--archive-existing", action="store_true")
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    manifest_path = data_dir / "pass2_deliverable_manifest.json"
    metadata_path = data_dir / "pass2_run_metadata.json"
    pass2_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pass2_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    old_captions = PASS2_CAPTIONS.read_text(encoding="utf-8")
    old: dict[str, list[dict]] = {}
    pass2_names = {manifest_path.name, metadata_path.name}
    for deliverable, entry in pass2_manifest["entries"].items():
        name = entry["inputs"]["data"]
        old[deliverable] = read_csv(data_dir / name)
        pass2_names.update(entry["inputs"].values())

    datasets: dict[str, list[dict]] = {
        "Figure 1": clone_rows(old["Figure 1"], "Figure 1"),
        "Figure 3": clone_rows(old["Figure 2"], "Figure 3"),
        "Figure 4": clone_rows(old["Figure 3"], "Figure 4"),
        "Supplementary Figure S1": clone_rows(old["Supplementary Figure S1"], "Supplementary Figure S1"),
        "Supplementary Figure S3": clone_rows(old["Figure 4"], "Supplementary Figure S3"),
        "Table 1": clone_rows(old["Table 1"], "Table 1"),
        "Table 2": clone_rows(old["Table 2"], "Table 2"),
        "Table 3": clone_rows(old["Table 3"], "Table 3"),
        "Table 4": clone_rows(old["Table 4"], "Table 4"),
        "Supplementary Table S1a": clone_rows(old["Supplementary Table S1a"], "Supplementary Table S1a"),
        "Supplementary Table S1b": clone_rows(old["Supplementary Table S1b"], "Supplementary Table S1b"),
        "Supplementary Table S1c": clone_rows(old["Supplementary Table S1c"], "Supplementary Table S1c"),
        "Supplementary Table S2": clone_rows(old["Table 5"], "Supplementary Table S2"),
    }
    ratings = old["Supplementary Figure S2"]
    datasets["Figure 2"] = clone_rows([
        row for row in ratings if row["population"] == "baseline" and row["dimension"] in {"Register-entry information", "Taxonomy fit"}
    ], "Figure 2")
    datasets["Supplementary Figure S2"] = clone_rows([
        row for row in ratings if (row["population"] == "hard_case" and row["dimension"] in {"Register-entry information", "Taxonomy fit"}) or row["dimension"] == "Coder confidence"
    ], "Supplementary Figure S2")
    update_groups(datasets)
    point_order = number_figure4(datasets["Figure 4"])

    carryover = carryover_check(old, datasets)
    g12 = g12_assertions(datasets, pass2_metadata)
    totals = totals_assertion(datasets)
    tracing = trace_assertion(datasets)
    caption_bullets = captions(old_captions, datasets)

    archived = archive_pass2_data(data_dir, pass2_names) if args.archive_existing else []
    generated = datetime.now(timezone.utc).isoformat()
    logs = {}
    for path in (args.pass3_log.resolve(), args.pass2_log.resolve(), args.findings_log.resolve()):
        stat = path.stat()
        logs[path.name] = {"path": str(path), "sha256": sha256(path), "size_bytes": stat.st_size,
                           "last_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()}
    source_commits = {
        "pass2_baseline": git("rev-parse", "64679cf"),
        "canonical_data_outputs": git("rev-parse", "6cbf154"),
        "exploratory_confidence_outputs": git("rev-parse", "f36d738"),
        "verification_report": git("rev-parse", "1287716"),
    }
    entries = {}
    for deliverable in ORDER:
        slug = SLUGS[deliverable]
        data_name = f"{slug}.csv"
        metadata_name = f"{slug}_metadata.json"
        write_csv(data_dir / data_name, datasets[deliverable])
        row_metadata = {
            "deliverable": deliverable, "slug": slug, "generated_utc": generated,
            "numeric_baseline": "pass-2 figure data at 64679cf", "rows": len(datasets[deliverable]),
            "dimension_names": list(DIMENSION_NAMES),
        }
        (data_dir / metadata_name).write_text(json.dumps(row_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        outputs = [f"{slug}.png", f"{slug}.svg"] if "Figure" in deliverable else [f"{slug}.csv", f"{slug}.md"]
        entries[deliverable] = {
            "slug": slug, "title": TITLES[deliverable], "inputs": {"data": data_name, "metadata": metadata_name},
            "outputs": outputs, "caption_bullets": caption_bullets[deliverable],
        }
    manifest = {
        "generated_utc": generated, "entries": entries, "order": list(ORDER),
        "dimension_names": list(DIMENSION_NAMES),
        "axis_ranges": {"alpha_figure_1_and_s1": [0.0, 1.0], "alpha_figure_3": [0.15, 0.75], "delta_all": [-0.45, 0.45], "figure_4": [-1.5, 60.0]},
        "point_order": point_order,
        "provenance": {"logs": logs, "source_commits": source_commits, "archived_figure_data": archived},
        "assertions": {
            "carried_over_values": carryover, "new_values_traced": tracing, "g12_derivations": g12,
            "category_totals": totals, "dimension_names": {"status": "PASS", "names": list(DIMENSION_NAMES)},
            "approved_numeric_corrections": [], "log_quote_source_differences": [],
        },
    }
    (data_dir / "pass3_deliverable_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    code_commits = {
        "extractor": git("log", "-1", "--format=%H", "--", str(Path(__file__).relative_to(ROOT))),
        "renderer": git("log", "-1", "--format=%H", "--", "analysis/visualisations/render_scratch_coder_pass3.py"),
        "runner": git("log", "-1", "--format=%H", "--", "analysis/visualisations/run_scratch_coder_pass3.py"),
    }
    run_metadata = {
        "run_timestamp_utc": generated, "head_at_run_start": git("rev-parse", "HEAD"),
        "code_commits": code_commits, "source_commits": source_commits, "logs": logs,
        "software": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform()},
        "assertions": manifest["assertions"],
    }
    (data_dir / "pass3_run_metadata.json").write_text(json.dumps(run_metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
