"""Aggregate output construction, human-readable reports, and masking scan."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import nbformat
import pandas as pd

from analysis.validation.replacement import replacement_panel_analysis

from .config import CODERS, DIMENSIONS, OUTPUT_DIR, ROOT
from .mappings import field_mapping_rows
from .panels import StageAData, dimension_panels, distance_for_dimension


def qa_rows(data: StageAData) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    populations = (
        ("overall", data.formal_ids),
        ("baseline", data.baseline_ids),
        ("hard_case", data.hard_case_ids),
    )
    for population, ids in populations:
        responses = data.responses[data.responses["record_id"].isin(ids)]
        expected = len(ids) * 3
        metrics = [
            ("records", len(ids), len(ids), "project"),
            ("expected_responses", expected, expected, "response"),
            ("submitted_responses", len(responses), expected, "response"),
            ("complete_responses", int(responses["complete"].sum()), expected, "response"),
            ("incomplete_responses", int((~responses["complete"]).sum()), expected, "response"),
            ("structural_invalid_responses", int((~responses["structural_valid"]).sum()), expected, "response"),
            ("structural_invalid_projects", len(set(responses.loc[~responses["structural_valid"], "record_id"])), len(ids), "project"),
            ("exposure_flagged_responses", int((responses["exposure"] == 1).sum()), expected, "response"),
            ("exposure_affected_projects", len(set(responses.loc[responses["exposure"] == 1, "record_id"])), len(ids), "project"),
            ("structural_sensitivity_retained_projects", len(ids - data.structural_invalid_ids), len(ids), "project"),
            ("exposure_sensitivity_retained_projects", len(ids - data.exposure_ids), len(ids), "project"),
        ]
        if population == "overall":
            metrics.insert(0, ("rows_in_raw_export", data.raw_rows, data.raw_rows, "export row"))
        if population == "hard_case":
            for stratum in ("domain_only", "purpose_only", "both"):
                metrics.append((f"hard_case_stratum_{stratum}_records", data.hard_stratum_counts.get(stratum, 0), 75, "project"))
        for metric, count, denominator, unit in metrics:
            rows.append({
                "population": population, "dimension": "all", "measure": metric,
                "count": count, "denominator": denominator,
                "proportion": count / denominator if denominator else None, "unit": unit,
            })
        for dimension in DIMENSIONS:
            result = replacement_panel_analysis(dimension_panels(data, ids, dimension), distance_for_dimension(dimension))
            rows.append({
                "population": population, "dimension": dimension,
                "measure": "complete_matched_three_coder_panels",
                "count": len(result.common_record_ids), "denominator": len(ids),
                "proportion": len(result.common_record_ids) / len(ids), "unit": "project",
            })
    return rows


def denominator_rows(
    qa: list[dict[str, object]], sufficiency: dict[str, list[dict[str, object]]],
    taxonomy: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []

    def add(analysis, population, measure, numerator, denominator, proportion, method="", low=None, high=None, notes=""):
        out.append({
            "analysis": analysis, "population": population, "measure": measure,
            "numerator": numerator, "denominator": denominator, "proportion": proportion,
            "interval_method": method, "ci_lower": low, "ci_upper": high, "notes": notes,
        })

    for row in qa:
        add("completion_and_qa", row["population"], f"{row['dimension']} | {row['measure']}",
            row["count"], row["denominator"], row["proportion"], notes=str(row["unit"]))
    for row in sufficiency["responses"]:
        add("sufficiency_response_distribution", row["population"], f"{row['coder']} | {row['category']}",
            row["count"], row["denominator"], row["proportion"])
    for row in sufficiency["records"]:
        add("sufficiency_record_distribution", row["population"], str(row["category"]),
            row["count"], row["denominator"], row["proportion"])
    for row in sufficiency["subsets"]:
        add("sufficiency_subset", row["population"], str(row["subset"]), row["count"],
            row["denominator"], row["proportion"], row["ci_method"], row["ci_lower"], row["ci_upper"])
    for key, analysis in (("responses", "taxonomy_fit_response_distribution"), ("records", "taxonomy_fit_record_distribution")):
        for row in taxonomy[key]:
            measure = f"{row.get('coder', 'record')} | {row['category']}"
            add(analysis, row["population"], measure, row["count"], row["denominator"], row["proportion"])
    for row in taxonomy["issues"]:
        add("taxonomy_issue", row["population"], str(row["issue"]), row["count"],
            row["applicable_denominator"], row["proportion"], notes=str(row["note"]))
    for key in ("unclear", "coherence"):
        for row in taxonomy[key]:
            measure = " | ".join(str(row.get(name, "")) for name in ("dimension", "section", "analysis", "measure", "category") if row.get(name, "") != "")
            add(f"taxonomy_{key}", row["population"], measure, row["count"], row["denominator"], row["proportion"])
    return out


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty required output: {path.name}")
    columns = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _lookup(rows, population, dimension, key, value):
    return next(row for row in rows if row["population"] == population and row["dimension"] == dimension and row[key] == value)


def headline_results(agreement, sufficiency, taxonomy, qa, timing) -> dict[str, object]:
    replacement = {}
    for population in ("baseline", "hard_case", "baseline_broad_usable", "baseline_strict_sufficient"):
        replacement[population] = {}
        for dimension in DIMENSIONS:
            panels = {p: _lookup(agreement["panels"], population, dimension, "panel", p)["point_estimate"] for p in ("ABC", "LBC", "ALC", "ABL")}
            deltas = {d: _lookup(agreement["deltas"], population, dimension, "delta", d)["point_estimate"] for d in ("delta_A", "delta_B", "delta_C", "delta_min")}
            delta_min = _lookup(agreement["deltas"], population, dimension, "delta", "delta_min")
            replacement[population][dimension] = {
                "n": delta_min["n_records"], **panels, **deltas,
                "delta_min_ci_lower": delta_min["ci_lower"], "delta_min_ci_upper": delta_min["ci_upper"],
            }
    return {
        "status": "preliminary_stage_a_aggregate_complete",
        "replacement": replacement,
        "triggers": agreement["triggers"],
        "qa": qa,
        "sufficiency_subsets": sufficiency["subsets"],
        "taxonomy_fit_records": taxonomy["records"],
        "timing": timing,
    }


def methods_text(raw_sha: str) -> str:
    return f"""# Scratch-coder Stage A methods

## Frozen inputs

The authoritative raw input is `preregistration/post_registration/redcap_exports/scratch_coder_export_frozen_2026-08-24.csv` (POST-028; SHA-256 `{raw_sha}`). The governing protocol is PRO-018. Candidate-0.7 is represented by RED-036, parsed under RED-005/006/007 and structurally checked using RED-013. Sample membership comes only from POST-009, POST-011 and POST-019. Formal scratch coding and production classifications use the MOD-001 rc2 taxonomy. Production model L is the protected MOD-006 Fable 5 output.

## Loading, validation and panels

Rows enter the formal panel only when `validation_included=1` and their assignment, coder and source-record keys match POST-019 exactly. Each formal record must have exactly one response from C01, C02 and C03. Complete-case membership is assessed separately by classification dimension, with the same records used for ABC and every replacement panel. No response is imputed or repaired. A zero in binary fields is retained as a substantive No. Checkbox groups are parsed explicitly; taxonomy-issue checkboxes are interpreted only where `sc_taxonomy_fit` is Partial Fit or No Fit.

Completed responses are passed unchanged through RED-013 `validate_scratch`. Structurally invalid responses remain in the primary analysis; the structural sensitivity excludes an entire record if any coder response fails. Exposure-flagged responses likewise remain primary; the exposure sensitivity excludes an entire record if any response is flagged. The primary population is the 150-record random baseline. The 75 hard cases are analysed separately as disagreement-enriched diagnostics.

## Classification and agreement

Research Domains and Analytical Purposes are unordered `frozenset` values. `Unclear from Register Entry` remains a valid category and its mutual-exclusivity rules are checked by the frozen validator. The equity and COVID tags are separate binary nominal dimensions. Model classifications are split only on their frozen semicolon delimiter and validated against MOD-001.

For each dimension the code calculates Krippendorff's alpha for ABC, LBC, ALC and ABL. Domains and Purposes use the repository's MASI distance (`analysis.validation.metrics.masi_distance`); tags use nominal distance. Deltas are replacement alpha minus ABC, and `delta_min` is the minimum of the three jointly calculated deltas. Point estimates use `analysis.validation.replacement.replacement_panel_analysis` and `analysis.validation.alpha.krippendorff_alpha`. Bootstrap evaluation uses an algebraically equivalent encoded coincidence calculation and asserts equality with the canonical point estimates to 1e-12.

## Bootstrap and intervals

Each analysis uses 2,000 attempted record-level bootstrap replicates with Python's `random.Random`, seed 20260714. A draw carries the complete A/B/C/L record block; duplicate draws remain duplicated rows. All four alphas, all three deltas and `delta_min` are recalculated from the same draw. Percentile endpoints use Hyndman-Fan Type 7 linear interpolation through `analysis.validation.bootstrap.percentile`. Undefined statistics stay blank and their counts are retained. An interval is suppressed if fewer than 1,800 replicates are valid.

Baseline proportions use the repository Wilson-score implementation at 95%. Broad register-usable means at least two coders selected Sufficient or Partial; strict register-sufficient means at least two selected Sufficient. These subsets use original pre-adjudication ratings. Record-level sufficiency and taxonomy-fit majorities require two identical categories; otherwise the result is `No majority / split judgement`. `Cannot assess from register entry` is not collapsed into No Fit. Taxonomy-issue percentages use only applicable Partial Fit/No Fit responses and may sum above 100%.

## Timing and masking

The export has neither a formal review-start timestamp nor formal `scratch_coder_timestamp` values, so A6 is not defensibly estimable. Time gaps between submissions are not used. All saved outputs are aggregate. The run scans them against the real source-ID set and does not create record-level disagreement, majority-versus-model, adjudication, or per-label performance artefacts.

## Importable review API

```python
from analysis.scratch_coder_stage_a import (
    load_frozen_export, validate_export, build_panels,
    run_replacement_analysis, bootstrap_replacement_analysis,
    derive_sufficiency_subsets, summarise_taxonomy_fit,
)

raw = load_frozen_export()  # inspect shape/columns only; do not display response rows
data = validate_export()
subsets = derive_sufficiency_subsets(data)
panels = build_panels(data, data.baseline_ids, "Research Domains")
point = run_replacement_analysis(panels, "Research Domains")
bootstrap = bootstrap_replacement_analysis(panels, "Research Domains")
taxonomy = summarise_taxonomy_fit(data)
```

The command-line run is authoritative; notebook code imports these functions rather than duplicating the implementation.
"""


def headline_markdown(results: dict[str, object], agreement, sufficiency, taxonomy, timing) -> str:
    lines = [
        "# Scratch-coder Stage A headline summary",
        "",
        "Preliminary — frozen scratch-coder data. Stage A aggregate analysis complete. Label-specific diagnostics, disagreement adjudication and project-owner evidence are not yet incorporated.",
        "",
        "## 1. Completion and QA",
        "",
        "The frozen panel reconciles to 3 coders × 225 records (675 formal responses): 150 random-baseline and 75 hard-case records. Detailed response/project denominators are in [qa_summary.csv](qa_summary.csv).",
        "",
        "## 2. Headline replacement analysis",
        "",
        "| Dimension | N | Human α | Replace A α | Replace B α | Replace C α | ΔA | ΔB | ΔC | Δmin | 95% CI Δmin |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    baseline = results["replacement"]["baseline"]
    for dimension in DIMENSIONS:
        r = baseline[dimension]
        fmt = lambda x: "NA" if x is None else f"{x:.3f}"
        ci = f"[{fmt(r['delta_min_ci_lower'])}, {fmt(r['delta_min_ci_upper'])}]"
        lines.append(f"| {dimension} | {r['n']} | {fmt(r['ABC'])} | {fmt(r['LBC'])} | {fmt(r['ALC'])} | {fmt(r['ABL'])} | {fmt(r['delta_A'])} | {fmt(r['delta_B'])} | {fmt(r['delta_C'])} | {fmt(r['delta_min'])} | {ci} |")
    lines.extend(["", "Mechanical review-trigger indicators:", ""])
    for row in agreement["triggers"]:
        lines.append(f"- {row['dimension']}: all three deltas below zero = {row['all_three_replacement_deltas_below_zero']}; Δmin CI entirely below zero = {row['delta_min_ci_entirely_below_zero']}.")
    lines.extend(["", "## 3. Register sufficiency", ""])
    for population in ("baseline", "hard_case"):
        label = "Random baseline" if population == "baseline" else "Hard case (diagnostic)"
        record_rows = [r for r in sufficiency["records"] if r["population"] == population]
        subset_rows = [r for r in sufficiency["subsets"] if r["population"] == population]
        lines.append(f"**{label}.** " + "; ".join(f"{r['category']}: {r['count']}/{r['denominator']} ({100*r['proportion']:.1f}%)" for r in record_rows) + ".")
        subset_bits = []
        for r in subset_rows:
            ci = "" if pd.isna(r["ci_lower"]) else f"; 95% Wilson CI {100*r['ci_lower']:.1f}%–{100*r['ci_upper']:.1f}%"
            subset_bits.append(f"{r['subset']}: {r['count']}/{r['denominator']} ({100*r['proportion']:.1f}%{ci})")
        lines.append("Broad/strict subsets: " + "; ".join(subset_bits) + ".")
    lines.extend(["", "## 4. Sufficiency-conditioned replacement", "", "| Population | Dimension | N | Δmin | 95% CI |", "|---|---|---:|---:|---:|"])
    for population in ("baseline", "baseline_broad_usable", "baseline_strict_sufficient"):
        for dimension in DIMENSIONS:
            r = results["replacement"][population][dimension]
            fmt = lambda x: "NA" if x is None else f"{x:.3f}"
            lines.append(f"| {population} | {dimension} | {r['n']} | {fmt(r['delta_min'])} | [{fmt(r['delta_min_ci_lower'])}, {fmt(r['delta_min_ci_upper'])}] |")
    lines.extend(["", "## 5. Taxonomy fit", ""])
    for population in ("baseline", "hard_case"):
        label = "Random baseline" if population == "baseline" else "Hard case (diagnostic)"
        fit_rows = [r for r in taxonomy["records"] if r["population"] == population]
        lines.append(f"**{label}.** " + "; ".join(f"{r['category']}: {r['count']}/{r['denominator']} ({100*r['proportion']:.1f}%)" for r in fit_rows) + ".")
        issue_rows = [r for r in taxonomy["issues"] if r["population"] == population]
        lines.append("Applicable issue responses: " + "; ".join(f"{r['issue']}: {r['count']}/{r['applicable_denominator']} ({100*r['proportion']:.1f}%)" for r in issue_rows) + ".")
    lines.extend([
        "", "Taxonomy-issue frequencies use only applicable Partial Fit/No Fit coder responses; percentages may sum to more than 100%. See [taxonomy_issue_summary.csv](taxonomy_issue_summary.csv).",
        "", "## Timing", "", str(timing[0]["reason"]),
        "", "> The random baseline is the preregistered population-level replacement analysis. The hard-case sample was deliberately disagreement-enriched and is diagnostic rather than representative.",
        "", "> Replacement-panel differences estimate the change in three-member-panel reliability when the production model replaces one trained coder. They are not direct measures of classification accuracy.",
        "", "> Stage A does not identify why individual disagreements occurred. Record-level disagreement adjudication remains deliberately source-masked and has not begun.",
        "", "Full-precision values are in [replacement_panel_results.csv](replacement_panel_results.csv), [replacement_delta_results.csv](replacement_delta_results.csv), and [bootstrap_replicates.csv](bootstrap_replicates.csv).",
    ])
    return "\n".join(lines) + "\n"


def create_review_notebook(path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["cells"] = [
        nbformat.v4.new_markdown_cell("# Scratch-coder Stage A aggregate review\n\nThis notebook never displays raw response rows, source IDs, projects, or disagreement cases."),
        nbformat.v4.new_markdown_cell("## 1. Frozen input"),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd, numpy as np\nfrom analysis.scratch_coder_stage_a import validate_export, derive_sufficiency_subsets, summarise_taxonomy_fit\nfrom analysis.scratch_coder_stage_a.api import build_panels, run_replacement_analysis\nROOT = Path.cwd()\nOUT = ROOT / 'analysis/outputs_validation_scratch_20260824'\nmetadata = json.loads((OUT/'run_metadata.json').read_text())\n{key: metadata[key] for key in ['raw_export_relative_path','raw_export_sha256','raw_export_rows','raw_export_columns','verified_authorities']}"),
        nbformat.v4.new_markdown_cell("## 2. Panel QA"),
        nbformat.v4.new_code_cell("qa = pd.read_csv(OUT/'qa_summary.csv')\nqa"),
        nbformat.v4.new_markdown_cell("## 3. Field mapping"),
        nbformat.v4.new_code_cell("pd.read_csv(OUT/'field_mapping.csv')"),
        nbformat.v4.new_markdown_cell("## 4. Agreement implementation"),
        nbformat.v4.new_code_cell("from analysis.validation.metrics import masi_distance\nfrom analysis.validation.alpha import krippendorff_alpha\nexamples = {'identical': float(masi_distance(frozenset({'A'}), frozenset({'A'}))), 'partial': float(masi_distance(frozenset({'A'}), frozenset({'A','B'}))), 'disjoint': float(masi_distance(frozenset({'A'}), frozenset({'B'})))}\nassert examples['identical'] < examples['partial'] < examples['disjoint']\nexamples"),
        nbformat.v4.new_markdown_cell("## 5. Baseline point estimates"),
        nbformat.v4.new_code_cell("data = validate_export()\nsubsets = derive_sufficiency_subsets(data)\npoint_rows=[]\nfor dimension in ['Research Domains','Analytical Purposes','Demographic disparities / equity','COVID-19 & Pandemic']:\n    result=run_replacement_analysis(build_panels(data,data.baseline_ids,dimension),dimension)\n    point_rows.append({'dimension':dimension,'N':len(result.common_record_ids),'ABC':result.alpha_abc.alpha,'LBC':result.alpha_lbc.alpha,'ALC':result.alpha_alc.alpha,'ABL':result.alpha_abl.alpha,'delta_min':result.delta_min})\npd.DataFrame(point_rows)"),
        nbformat.v4.new_markdown_cell("## 6. Bootstrap"),
        nbformat.v4.new_code_cell("reps=pd.read_csv(OUT/'bootstrap_replicates.csv')\ndeltas=pd.read_csv(OUT/'replacement_delta_results.csv')\nmanual=(reps[reps.population.eq('baseline')].groupby('dimension')['delta_min'].quantile([.025,.975],interpolation='linear').unstack())\nreported=deltas[(deltas.population.eq('baseline')) & (deltas.delta.eq('delta_min'))].set_index('dimension')[['ci_lower','ci_upper']]\nassert np.allclose(manual.sort_index().to_numpy(),reported.sort_index().to_numpy(),equal_nan=True)\nmanual"),
        nbformat.v4.new_markdown_cell("## 7. Sufficiency"),
        nbformat.v4.new_code_cell("from analysis.scratch_coder_stage_a.sufficiency import summarise_sufficiency\nsuff=summarise_sufficiency(data)\npd.DataFrame(suff['records'])"),
        nbformat.v4.new_markdown_cell("## 8. Broad/strict subsets"),
        nbformat.v4.new_code_cell("{'broad_register_usable':len(subsets['broad']),'strict_register_sufficient':len(subsets['strict'])}"),
        nbformat.v4.new_markdown_cell("## 9. Conditioned replacement"),
        nbformat.v4.new_code_cell("pd.read_csv(OUT/'replacement_delta_results.csv').query(\"population in ['baseline_broad_usable','baseline_strict_sufficient'] and delta == 'delta_min'\")"),
        nbformat.v4.new_markdown_cell("## 10. Taxonomy fit"),
        nbformat.v4.new_code_cell("tax=summarise_taxonomy_fit(data)\npd.DataFrame(tax['records'])"),
        nbformat.v4.new_markdown_cell("## 11. Timing"),
        nbformat.v4.new_code_cell("pd.read_csv(OUT/'timing_summary.csv')"),
        nbformat.v4.new_markdown_cell("## 12. Cross-checks"),
        nbformat.v4.new_code_cell("saved=pd.read_csv(OUT/'replacement_panel_results.csv')\ncalc=pd.DataFrame(point_rows).set_index('dimension')\nbase=saved[saved.population.eq('baseline')].pivot(index='dimension',columns='panel',values='point_estimate')\nassert np.allclose(calc.loc[base.index,['ABC','LBC','ALC','ABL']],base[['ABC','LBC','ALC','ABL']])\nassert len(data.baseline_ids)==150 and len(data.hard_case_ids)==75 and len(data.responses)==675\n'All aggregate cross-checks passed.'"),
    ]
    nbformat.write(nb, path)


def scan_masking(output_dir: Path, prohibited_ids: set[str], prohibited_titles: set[str]) -> dict[str, int]:
    prohibited_names = {"disagreement_records.csv", "adjudication_population.csv", "model_errors.csv", "majority_vs_model.csv"}
    if any((output_dir / name).exists() for name in prohibited_names):
        raise ValueError("A prohibited record-level disagreement artefact exists")
    matches = 0
    title_matches = 0
    for path in output_dir.iterdir():
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            matches += sum(identifier in text for identifier in prohibited_ids)
            title_matches += sum(title in text for title in prohibited_titles)
            if re.search(r"(?i)(per[-_ ]label (precision|recall|f1|kappa)|false[-_ ]positive|false[-_ ]negative)", text):
                raise ValueError(f"Stage B diagnostic language found in {path.name}")
    if matches or title_matches:
        raise ValueError(f"masking scan failed: {matches + title_matches} prohibited identifiers detected")
    return {"real_source_ids_detected": 0, "real_project_titles_detected": 0, "record_level_disagreement_outputs": 0, "stage_b_outputs": 0}


def write_outputs(
    *, output_dir: Path, metadata: dict[str, object], qa: list[dict[str, object]],
    agreement: dict[str, list[dict[str, object]]], sufficiency, taxonomy, timing,
    prohibited_ids: set[str], prohibited_titles: set[str], raw_sha: str,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_csv(output_dir / "field_mapping.csv", field_mapping_rows())
    _write_csv(output_dir / "qa_summary.csv", qa)
    _write_csv(output_dir / "denominator_audit.csv", denominator_rows(qa, sufficiency, taxonomy))
    _write_csv(output_dir / "replacement_panel_results.csv", agreement["panels"])
    _write_csv(output_dir / "replacement_delta_results.csv", agreement["deltas"])
    _write_csv(output_dir / "bootstrap_replicates.csv", agreement["replicates"])
    _write_csv(output_dir / "replacement_trigger_summary.csv", agreement["triggers"])
    _write_csv(output_dir / "sufficiency_response_distribution.csv", sufficiency["responses"])
    _write_csv(output_dir / "sufficiency_record_distribution.csv", sufficiency["records"])
    _write_csv(output_dir / "sufficiency_subset_summary.csv", sufficiency["subsets"])
    _write_csv(output_dir / "taxonomy_fit_response_distribution.csv", taxonomy["responses"])
    _write_csv(output_dir / "taxonomy_fit_record_distribution.csv", taxonomy["records"])
    _write_csv(output_dir / "taxonomy_issue_summary.csv", taxonomy["issues"])
    _write_csv(output_dir / "unclear_register_summary.csv", taxonomy["unclear"])
    _write_csv(output_dir / "taxonomy_coherence_summary.csv", taxonomy["coherence"])
    _write_csv(output_dir / "timing_summary.csv", timing)
    results = headline_results(agreement, sufficiency, taxonomy, qa, timing)
    (output_dir / "headline_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "headline_summary.md").write_text(headline_markdown(results, agreement, sufficiency, taxonomy, timing), encoding="utf-8")
    (output_dir / "methods_stage_a.md").write_text(methods_text(raw_sha), encoding="utf-8")
    create_review_notebook(output_dir / "scratch_coder_stage_a_review.ipynb")
    metadata["masking"] = scan_masking(output_dir, prohibited_ids, prohibited_titles)
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Re-scan with metadata included.
    metadata["masking"] = scan_masking(output_dir, prohibited_ids, prohibited_titles)
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return results
