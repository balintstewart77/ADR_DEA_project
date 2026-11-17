"""GHA1 results report (numbers generated from the output tables; interpretation is written separately)."""
from __future__ import annotations

from pathlib import Path

SOURCES = ("C01", "C02", "C03", "Fable 5", "GPT-5.5")
DIMS = ("Research Domains", "Analytical Purposes")
POPS = ("baseline", "hard_case")
CODERS = ("C01", "C02", "C03")


def f3(value) -> str:
    if value is None or value == "":
        return "–"
    text = f"{float(value):+.3f}" if float(value) < 0 else f"{float(value):.3f}"
    return text.replace("-", "−")


def signed(value) -> str:
    return "–" if value is None or value == "" else f"{float(value):+.3f}".replace("-", "−")


def iv(row: dict, sign: bool = False) -> str:
    fmt = signed if sign else f3
    if not row["interval_reported"]:
        return f"{fmt(row['point_estimate'])} (interval suppressed: {row['draws_valid']} valid draws)"
    return f"{fmt(row['point_estimate'])} ({fmt(row['interval_lower_95'])} to {fmt(row['interval_upper_95'])})"


def write(out_dir: Path, tables: dict, populations: dict, stage_a: dict, gpt_invalid, divergence: list, summary_md: str) -> Path:
    rep = {(r["population"], r["dimension"], r["statistic"]): r for r in tables["GHA1T004_replacement_and_contrasts.csv"]}
    pw = tables["GHA1T003_pairwise_agreement.csv"]
    lines = ["# GHA1 — GPT-5.5, Fable 5 and three coders (exploratory)", "",
             "**Post hoc and exploratory; not preregistered.** Specified on 17 November 2026 after the production-model results had been "
             "inspected (`SPEC_gpt55_human_agreement_2026-11-17.md`). The preregistered Fable 5 validation remains primary. Agreement is not "
             "accuracy, and a human consensus is not an adjudicated reference. GPT-5.5 received the production prompt without adaptation.", "",
             "## Populations", ""]
    for (pop, dim), n in populations.items():
        lines.append(f"- {pop}, {dim}: {n} records with valid ratings from all five sources (Stage A population {stage_a[(pop, dim)]}).")
    lines += [f"- GPT-5.5 invalid classifications among the 225 active records: {dict(gpt_invalid) or 'none'}.",
              "- Model divergence on each dimension (computed from the frozen outputs): " +
              "; ".join(f"{d['population']} {d['dimension']} {d['models_differ']} of {d['records']}" +
                        (f" (recorded strata imply {d['expected_from_strata']}; mismatched {d['mismatched_records']})" if 'expected_from_strata' in d else "")
                        for d in divergence) + ".", "",
              "## Pairwise agreement (exact-set proportion; mean Jaccard)", ""]
    for pop in POPS:
        for dim in DIMS:
            lines += [f"**{pop}, {dim}**", "", "| Pair | Family | Records | Exact set | Mean Jaccard |", "|---|---|---|---|---|"]
            for r in pw:
                if r["population"] == pop and r["dimension"] == dim and r["stratum"] == "all":
                    lines.append(f"| {r['source_a']}–{r['source_b']} | {r['family']} | {r['records']} | {r['exact_set_n']} ({r['exact_set_proportion']:.2f}) | {r['mean_jaccard']:.2f} |")
            lines.append("")
    lines += ["Hard-case model–model disagreement is guaranteed by selection on the dimensions of each stratum and is not a finding.", "",
              "## Replacement panels and paired contrasts (95% percentile bootstrap intervals)", "",
              "| Population | Dimension | All-human α | Replaced coder | Fable 5 panel α | GPT-5.5 panel α | GPT-5.5 minus Fable 5 |", "|---|---|---|---|---|---|---|"]
    for pop in POPS:
        for dim in DIMS:
            for coder in CODERS:
                lines.append(f"| {pop} | {dim} | {iv(rep[(pop, dim, 'alpha_ABC')])} | {coder} | {iv(rep[(pop, dim, f'F_alpha_replacing_{coder}')])} | "
                             f"{iv(rep[(pop, dim, f'G_alpha_replacing_{coder}')])} | {iv(rep[(pop, dim, f'contrast_G_minus_F_replacing_{coder}')], sign=True)} |")
    lines += ["", "| Population | Dimension | Fable 5 δ_min | GPT-5.5 δ_min |", "|---|---|---|---|"]
    for pop in POPS:
        for dim in DIMS:
            lines.append(f"| {pop} | {dim} | {iv(rep[(pop, dim, 'F_delta_min')], True)} | {iv(rep[(pop, dim, 'G_delta_min')], True)} |")
    lines += ["", "The two δ_min need not arise from the same substitution and are not contrasted. Baseline intervals resample records; hard-case "
              "intervals resample within each recorded stratum and are exploratory conditional intervals for the selected case mix. "
              "No multiplicity adjustment.", "", "## Record-level patterns where the models differ", "",
              "| Population | Dimension | Pattern | Records | Of |", "|---|---|---|---|---|"]
    for r in tables["GHA1T007_record_patterns.csv"]:
        if r["stratum"] == "all" and r["case"] == "models differ" and r["denominator"]:
            lines.append(f"| {r['population']} | {r['dimension']} | {r['pattern']} | {r['records']} | {r['denominator']} |")
    lines += ["", "Patterns describe agreement, not correctness. By-stratum counts, the model-agreement comparison cases and the sufficiency "
              "and taxonomy-fit cross-tabulations are in GHA1T007–GHA1T008.", "", "## Reproduction and audit", ""]
    failed = [r for r in tables["GHA1T002_reproduction.csv"] if r["status"] != "passed"]
    lines.append(f"- Stage A reproduction: {len(tables['GHA1T002_reproduction.csv'])} comparisons, {len(failed)} failed.")
    grouped: dict[tuple, list[str]] = {}
    for d in tables["discrepancy_log.csv"]:
        grouped.setdefault((d["file"], d["finding"]), []).append(f"{d['row']} ({d['field']})")
    for (file, finding), where in grouped.items():
        lines.append(f"- `{file}`: {finding} — {len(where)} field values" + ("" if len(where) > 3 else f": {'; '.join(where)}") +
                     ". Details in `discrepancy_log.csv`.")
    lines += ["", "## Limitations", "",
              "- Exploratory and post hoc; production-model results were seen first.",
              "- Intervals condition on these three coders and these frozen outputs; they do not cover other coders, prompts, reruns or versions.",
              "- The hard-case sample is enriched for model disagreement and selected symmetrically on it; it supports no register-wide ranking, "
              "error rate or claim about portfolio validity. Hard-case intervals ignore the forced inclusion of accompanying-tag disagreements.",
              "- Stratum-level results rest on 25 records and are sensitive to label prevalence.",
              "- GPT-5.5 used the production prompt without adaptation, so the comparison is of frozen pipelines, not of model capability."]
    path = out_dir / "results_gha1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
