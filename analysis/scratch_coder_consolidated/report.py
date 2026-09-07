"""Metric-level presentation and lineage; no statistical computation."""
from __future__ import annotations

from collections import defaultdict
import json

from .preflight import (CONFIG, DEVIATIONS, DICTIONARY, DIRS, Fatal, HUMAN_PAIRS, INSTRUMENT, KEYS,
                        METHODS, MODEL_PAIRS, PANELS, DELTAS, PROTOCOL, RELEASE,
                        SECTIONS, SETS, STRATA, TAGS)

DIAGNOSTIC = "DIAGNOSTIC — non-representative"
TITLES = ["Provenance and report status", "Populations and denominators", "Cross-cutting tags",
          "Replacement-panel analysis: domains and purposes", "Review-trigger indicators",
          "Per-label diagnostics", "Macro-averages", "Exact-set and Jaccard agreement",
          "Register sufficiency", "Taxonomy fit", "Unclear from Register Entry", "Hard-case strata"]
POP_NAMES = {
    "overall": "All formal scratch-coder records (baseline and hard-case)",
    "baseline": "Random baseline",
    "baseline_exposure_sensitivity": "Baseline exposure sensitivity: any exposure-flagged record excluded",
    "baseline_structural_sensitivity": "Baseline structural sensitivity: any structurally invalid record excluded",
    "hard_case": "Hard-case sample — " + DIAGNOSTIC,
    "baseline_broad_usable": "Baseline broad register-usable subset: at least two Sufficient/Partially sufficient ratings",
    "baseline_strict_sufficient": "Baseline strict register-sufficient subset: at least two Sufficient ratings",
}
PAIRS = {"A-B": "C01 versus C02", "A-C": "C01 versus C03", "B-C": "C02 versus C03",
         "L-A": "Fable 5 versus C01", "L-B": "Fable 5 versus C02", "L-C": "Fable 5 versus C03"}
METRICS = {
    "qa_summary": ("count", "proportion"),
    "replacement_panel_results": ("point_estimate",),
    "replacement_delta_results": ("point_estimate",),
    "replacement_trigger_summary": ("all_three_replacement_deltas_below_zero", "delta_min_ci_entirely_below_zero"),
    "label_support": ("baseline_human_majority_positive_n", "baseline_human_majority_prevalence", "baseline_model_positive_n", "baseline_model_prevalence", "eligible_for_per_label_performance", "eligible_for_macro_average"),
    "per_label_contingencies": ("baseline_n", "human_majority_positive_n", "human_majority_prevalence", "model_positive_n", "model_prevalence", "tp", "fp", "fn", "tn", "n", "performance_metrics_reportable"),
    "per_label_model_performance": ("precision", "recall", "f1"),
    "per_label_pairwise_kappa": ("kappa",),
    "macro_performance": ("eligible_label_n", "precision", "recall", "f1"),
    "tag_diagnostics": ("n_records", "tp", "fp", "fn", "tn", "n", "human_majority_positive_n", "human_majority_prevalence", "model_positive_n", "model_prevalence", "raw_agreement", "positive_agreement", "negative_agreement", "cohen_kappa", "gwet_ac1", "precision", "recall", "f1"),
    "exact_set_jaccard_summary": ("exact_match_n", "exact_match_proportion", "mean_jaccard", "median_jaccard", "q1_jaccard", "q3_jaccard"),
    "sufficiency_response_distribution": ("count", "proportion"),
    "sufficiency_record_distribution": ("count", "proportion"),
    "sufficiency_subset_summary": ("count", "proportion"),
    "taxonomy_fit_response_distribution": ("count", "proportion"),
    "taxonomy_fit_record_distribution": ("count", "proportion"),
    "taxonomy_issue_summary": ("count", "proportion"),
    "unclear_register_summary": ("count", "proportion"),
    "taxonomy_coherence_summary": ("count", "proportion"),
    "hard_case_stratum_replacement": ("human_alpha", "replace_a_alpha", "replace_b_alpha", "replace_c_alpha", "delta_a", "delta_b", "delta_c", "delta_min"),
    "hard_case_stratum_exact_set_jaccard": ("exact_match_n", "exact_match_proportion", "mean_jaccard", "median_jaccard", "q1_jaccard", "q3_jaccard", "mean_model_coder_exact_set", "mean_model_coder_jaccard"),
    "hard_case_stratum_human_pair_agreement": ("exact_match_n", "exact_match_proportion", "mean_jaccard", "median_jaccard", "q1_jaccard", "q3_jaccard", "mean_model_coder_exact_set", "mean_model_coder_jaccard"),
}
TAG_DIAGNOSTICS = ("raw_agreement", "positive_agreement", "negative_agreement", "human_majority_prevalence", "model_prevalence", "cohen_kappa", "gwet_ac1", "precision", "recall", "f1")
COUNT_COLS = {"count", "n", "n_records", "baseline_n", "applicable_denominator", "tp", "fp", "fn", "tn", "exact_match_n", "eligible_label_n", "human_majority_positive_n", "model_positive_n", "baseline_human_majority_positive_n", "baseline_model_positive_n"}
FLAG_COLS = {"eligible_for_per_label_performance", "eligible_for_macro_average", "performance_metrics_reportable", "all_three_replacement_deltas_below_zero", "delta_min_ci_entirely_below_zero"}
ESTIMATE_CODES = {"reported": "R", "withheld_support_rule": "W", "undefined": "D", "unavailable_in_source": "A", "unresolved": "U", "not_applicable": "N"}
INTERVAL_CODES = {"reported": "R", "suppressed_diagnostic_policy": "SD", "suppressed_valid_replicate_threshold": "SV", "withheld_support_rule": "W", "undefined": "D", "not_applicable": "N", "unavailable_in_source": "A", "unresolved": "U"}


def unresolved_explanation_rollup(items):
    """Group canonical Appendix A entries by their complete recorded explanation."""
    identifiers = [item["id"] for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise Fatal("Duplicate canonical unresolved identifier")
    groups = defaultdict(list)
    for item in items:
        groups[item["cannot_establish"]].append(item["id"])
    rows = [
        {"cannot_establish": explanation, "count": len(member_ids), "member_ids": member_ids}
        for explanation, member_ids in groups.items()
    ]
    rows.sort(key=lambda row: (-row["count"], row["cannot_establish"]))
    grouped_ids = [identifier for row in rows for identifier in row["member_ids"]]
    if len(grouped_ids) != len(identifiers) or set(grouped_ids) != set(identifiers):
        raise Fatal("Canonical unresolved identifiers are missing from or duplicated across rollup groups")
    return rows


def esc(value):
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def table(headers, rows):
    return "\n".join(["| " + " | ".join(map(esc, headers)) + " |", "| " + " | ".join("---" for _ in headers) + " |"] + ["| " + " | ".join(map(esc, row)) + " |" for row in rows])


class Report:
    def __init__(self, sources, supplement=None):
        self.s = sources
        self.supplement = supplement
        self.meta = sources.meta
        self.tables = []
        self.items = self.meta.setdefault("result_items", [])
        self.lineage = self.meta.setdefault("cell_lineage", [])
        self.bysection = defaultdict(list)
        self.notes = defaultdict(list)
        self.meta["replicate_validity_count_exceptions"] = []

    def cell(self, item, name, row, col, role, displayed=None):
        ref = self.s.ref(name, row, col)
        self.lineage.append(dict(ref, table_id=item["table_id"], result_id=item["result_id"], metric=item["metric"],
            document_cell_role=role, displayed_value=row[col] if displayed is None else displayed,
            formatting="exact source string" if displayed is None else "presentation withholding" if displayed == "" and row[col] else "documented formatting",
            displayed_status=item["estimate_status"] if role == "estimate" else item["interval_status"] if role.startswith("interval_") else "reported",
            retained_raw_status=item["source_status"]))
        return row[col] if displayed is None else displayed

    def context(self, name, row):
        pop = row.get("population", "hard_case" if self.s.stage[name] == "h" else "baseline")
        dim = row.get("tag", row.get("dimension", "all"))
        if dim == "Cross-cutting tag":
            dim = row["label"]
        return pop, dim, row.get("stratum", "")

    def support(self, item, name, row):
        pop, dim, _ = self.context(name, row)
        if dim not in TAGS and "label" not in row:
            return ""
        tag = dim in TAGS
        label = dim if tag else row["label"]
        support = self.s.lookup("label_support", dimension="Cross-cutting tag" if tag else dim, label=label)
        cells = {c: self.cell(item, "label_support", support, c, "support." + c) for c in
                 ("baseline_human_majority_positive_n", "support_band", "low_support_caution_required")}
        own = "unavailable in source"
        if pop == "baseline":
            own = cells["baseline_human_majority_positive_n"]
        elif tag and pop == "hard_case":
            diagnostic = self.s.lookup("tag_diagnostics", population=pop, tag=dim)
            own = self.cell(item, "tag_diagnostics", diagnostic, "human_majority_positive_n", "population_support")
        elif tag:
            self.s.issue(2, f"{pop}/{dim}", "population_specific_support", "Replacement quantities and complete-case record totals are exported; the support band is defined on baseline.",
                         "Human-majority positive support for this sensitivity/subset population is not exported. Baseline support is explicitly labelled and is not substituted for it.", self.s.path("replacement_panel_results") + "; " + self.s.path("label_support"))
        item["support"] = dict(population=pop, population_positive_support=own, baseline_positive_support=cells["baseline_human_majority_positive_n"],
                               exported_band=cells["support_band"], exported_caution=cells["low_support_caution_required"], band_population="baseline",
                               branch="tag_always_report_with_caution" if tag else "domain_purpose_support_withholding")
        return f"This population support: {own}; baseline support: {cells['baseline_human_majority_positive_n']}; baseline band: {cells['support_band']}; exported caution: {cells['low_support_caution_required']}"

    def denominator(self, item, name, row, col):
        def value(c):
            return self.cell(item, name, row, c, "denominator." + c)
        if col == "eligible_label_n":
            return "total eligible labels (explicit membership below)"
        if name == "macro_performance":
            return "eligible labels: " + value("eligible_label_n") + "; fixed membership below"
        if col in FLAG_COLS:
            return "structural flag / exported condition; interval not applicable"
        if col in ("n", "n_records", "baseline_n"):
            return "total records"
        if col in ("precision", "recall", "f1", "positive_agreement", "negative_agreement"):
            r, family = row, name
            if name == "per_label_model_performance":
                r = self.s.lookup("per_label_contingencies", dimension=row["dimension"], label=row["label"])
                family = "per_label_contingencies"
            if "tp" in r:
                if col in ("precision", "recall"):
                    denominator_col = "model_positive_n" if col == "precision" else "human_majority_positive_n"
                    n = self.cell(item, family, r, denominator_col, "denominator." + denominator_col)
                    return n + (" model-positive records (precision denominator)" if col == "precision" else " human-majority-positive records (recall denominator)")
                operands = ("tn", "fp", "fn") if col == "negative_agreement" else ("tp", "fp", "fn")
                values = [c.upper() + "=" + self.cell(item, family, r, c, "denominator_operand." + c) for c in operands]
                definition = "2TP+FP+FN" if col == "positive_agreement" else "2TN+FP+FN" if col == "negative_agreement" else "precision+recall (source harmonic-mean definition)"
                return "; ".join(values) + "; denominator: " + definition + "; resulting denominator not separately exported"
        if name == "label_support":
            nrow = self.s.lookup("qa_summary", population="baseline", dimension="all", measure="records")
            return self.cell(item, "qa_summary", nrow, "count", "denominator.baseline_records") + " baseline records"
        for c in ("denominator", "applicable_denominator", "n_records", "n"):
            if c in row:
                n = value(c)
                unit = "records"
                if name == "qa_summary":
                    unit = self.cell(item, name, row, "unit", "unit")
                elif "response_distribution" in name or name in ("taxonomy_issue_summary", "taxonomy_coherence_summary"):
                    unit = "coder responses"
                elif name == "unclear_register_summary":
                    unit = "records" if row["measure"].startswith("records_") else "coder responses"
                return n + " " + unit + ("; total scope" if row.get("measure") in ("records", "expected_responses", "rows_in_raw_export") else "")
        if name == "replacement_trigger_summary":
            return "baseline-only exported condition"
        self.s.issue(SECTIONS[name], name, "denominator", "No compatible exported denominator column.", "Applicable denominator unavailable; none calculated.", self.s.path(name))
        return "unavailable in source"

    def bounds(self, name, row, col):
        if col in COUNT_COLS or col in FLAG_COLS:
            return None, None, None, None
        if name in ("replacement_panel_results", "replacement_delta_results", "per_label_pairwise_kappa"):
            return "ci_lower", "ci_upper", "bootstrap_valid_n", "bootstrap_invalid_n"
        if name == "sufficiency_subset_summary" and col == "proportion":
            return "ci_lower", "ci_upper", None, None
        stem = "exact_match" if col == "exact_match_proportion" else col
        lower = stem + "_ci_lower"
        if lower in row:
            valid = "bootstrap_valid_n" if name == "hard_case_stratum_replacement" else stem + "_bootstrap_valid_n"
            invalid = "bootstrap_invalid_n" if name == "hard_case_stratum_replacement" else stem + "_bootstrap_invalid_n"
            return lower, stem + "_ci_upper", valid if valid in row else None, invalid if invalid in row else None
        return None, None, None, None

    def add(self, t, name, row, col, force_withheld=False):
        pop, dim, stratum = self.context(name, row)
        key = {k: row[k] for k in KEYS[name]}
        ident = f"{t['id']}.r{len(t['items']) + 1}"
        source_status = {c: row[c] for c in ("analysis_note", "ci_reported", "ci_method", "note") if c in row}
        item = dict(table_id=t["id"], result_id=ident, source_name=name, source_path=self.s.path(name), source_key=key,
                    source_column=col if not force_withheld else None, metric=col, population=pop, dimension=dim, stratum=stratum,
                    estimate_status="reported", interval_method="none", interval_status="not_applicable", source_status=source_status or {"absence": "No source status/reason column"},
                    status_reason=[], policy_source=[], confidence_level=None, bootstrap_unit=None, bootstrap_method=None,
                    requested_replicate_count=None, valid_replicate_count=None, invalid_replicate_count=None, validity_threshold=None, seed=None)
        raw = row[col] if not force_withheld else None
        lo, hi, valid, invalid = self.bounds(name, row, col) if not force_withheld else (None, None, None, None)
        item.update(raw_estimate=raw, raw_interval_lower=row[lo] if lo else None, raw_interval_upper=row[hi] if hi else None,
                    raw_interval_method="none", interval_columns=[lo, hi])
        if raw == "":
            # Missingness does not imply zero or a specific undefined denominator.
            item["estimate_status"] = "unresolved"
            item["status_reason"].append("Blank source estimate; exact undefined condition not exported")
            self.s.issue(t["section"], key, col + ".estimate_status", "Source estimate is blank.", "Exact undefined condition not recorded for this result.", self.s.path(name))
        if col not in COUNT_COLS and col not in FLAG_COLS and not force_withheld:
            method_source = f"{DIRS[self.s.stage[name]]}/{METHODS[self.s.stage[name]]}"
            item["policy_source"].append(method_source)
            if lo:
                if name == "sufficiency_subset_summary":
                    item["interval_method"] = "wilson_score" if row["ci_method"] == "Wilson score 95%" else "none"
                    item["confidence_level"] = "95%" if row["ci_method"] == "Wilson score 95%" else None
                    item["policy_source"].append(self.s.ref(name, row, "ci_method"))
                else:
                    item["interval_method"] = "bootstrap_percentile"
                    run = self.s.runs[self.s.stage[name]]
                    item.update(bootstrap_unit="record; linked A/B/C/L retained", bootstrap_method=run.get("quantile_method"),
                                requested_replicate_count=run.get("bootstrap_replicates"), seed=run.get("bootstrap_seed"),
                                validity_threshold=(str(self.s.interval_policy[self.s.stage[name]]["minimum_valid"]) + " valid replicates (saved methods)" if self.s.stage[name] in self.s.interval_policy else None),
                                confidence_level="95%" if self.s.stage[name] == "b" or (self.s.stage[name] == "h" and name != "hard_case_stratum_replacement") else None)
                    item["policy_source"].append(f"{DIRS['b']}/methods_stage_b.md: 2.5/97.5 percentiles; valid-replicate threshold" if self.s.stage[name] != "a" else f"{DIRS['a']}/methods_stage_a.md: Bootstrap and intervals")
                if row[lo] and row[hi]:
                    item["interval_status"] = "reported"
                elif bool(row[lo]) != bool(row[hi]):
                    raise Fatal(f"Only one interval endpoint present: {name}/{key}/{col}")
                elif name == "sufficiency_subset_summary" and row["ci_method"] == "not applied (diagnostic sample)":
                    item["interval_status"] = "suppressed_diagnostic_policy"
                    item["status_reason"].append("Explicit source ci_method: not applied (diagnostic sample)")
                elif valid and row[valid] != "" and self.s.stage[name] in self.s.interval_policy and int(row[valid]) < self.s.interval_policy[self.s.stage[name]]["minimum_valid"]:
                    # Apply only the verified saved-method rule; never inspect draws.
                    item["interval_status"] = "suppressed_valid_replicate_threshold"
                    item["status_reason"].append("Saved methods suppress intervals below " + str(self.s.interval_policy[self.s.stage[name]]["minimum_valid"]) + " valid replicates; observed counts retained")
                else:
                    item["interval_status"] = "unresolved"
                    item["status_reason"].append("Interval absent without an established applicable reason")
                    self.s.issue(t["section"], key, col + ".interval_status", "Bounds are blank.", "Specific suppression/undefined reason not established.", self.s.path(name))
            else:
                item["interval_status"] = "unavailable_in_source"
                item["status_reason"].append("Interval columns not exported for this quantity")
                self.s.issue(t["section"], name + "/" + pop, col + ".interval", "The existing summary exports this quantity without interval columns.",
                             "Interval and any applicable absence reason unavailable; not computed here.", self.s.path(name))
        if valid:
            item["valid_replicate_count"] = row[valid] or None
        if invalid:
            item["invalid_replicate_count"] = row[invalid] or None
        item["raw_interval_method"] = item["interval_method"]
        if pop == "hard_case":
            item["status_reason"].append(DIAGNOSTIC + "; existing intervals retained")
        if force_withheld or (dim in SETS and "label" in row and col in ("kappa", "precision", "recall", "f1") and self.s.lookup("label_support", dimension=dim, label=row["label"])["support_band"] == "RARE"):
            item["estimate_status"] = "withheld_support_rule"
            item["interval_status"] = "withheld_support_rule"
            item["status_reason"].append("Domain/purpose rare-support presentation rule; metric row not exported for ineligible label" if force_withheld else "Domain/purpose rare-support presentation rule")
            item["policy_source"].append(PROTOCOL + " §8.8; user v2 §5.1 domain/purpose branch")
        item["displayed_estimate"] = "" if item["estimate_status"] == "withheld_support_rule" else raw
        item["displayed_lower"] = "" if item["interval_status"] == "withheld_support_rule" else row[lo] if lo else ""
        item["displayed_upper"] = "" if item["interval_status"] == "withheld_support_rule" else row[hi] if hi else ""
        item["denominator_display"] = self.denominator(item, name, row, col)
        item["support_display"] = self.support(item, name, row)
        if not force_withheld:
            self.cell(item, name, row, col, "estimate", item["displayed_estimate"])
        else:
            self.lineage.append(dict(lineage_type="policy_withholding", table_id=t["id"], result_id=ident, metric=col,
                document_cell_role="estimate", source_path=self.s.path(name), row_selection_key=key, column=None,
                raw_value=None, displayed_value="", displayed_status="withheld_support_rule", retained_raw_status=item["source_status"],
                policy_source=item["policy_source"], reason="No metric row exported; blank required by user §5.1; no estimate manufactured"))
        for c, role in ((lo, "interval_lower"), (hi, "interval_upper"), (valid, "valid_replicate_count"), (invalid, "invalid_replicate_count")):
            if c:
                shown = item["displayed_lower"] if role == "interval_lower" else item["displayed_upper"] if role == "interval_upper" else row[c]
                self.cell(item, name, row, c, role, shown)
        for c in KEYS[name]:
            self.cell(item, name, row, c, "row_identifier." + c)
        for c in ("baseline_support_n", "support_n", "support_band", "low_support_caution", "low_support_caution_required", "distance", "ci_method", "ci_reported", "analysis_note", "note"):
            if c in row:
                self.cell(item, name, row, c, "source_annotation." + c)
        if item["requested_replicate_count"] is not None:
            stage = self.s.stage[name]
            for field, source_field in (("requested_replicate_count", "bootstrap_replicates"), ("seed", "bootstrap_seed"), ("bootstrap_method", "quantile_method")):
                self.lineage.append(dict(lineage_type="source_run_metadata", table_id=t["id"], result_id=ident, metric=col,
                    document_cell_role=field, source_path=f"{DIRS[stage]}/run_metadata.json", field=source_field,
                    raw_value=self.s.runs[stage].get(source_field), displayed_value=item[field]))
        if name == "macro_performance":
            self.cell(item, name, row, "eligible_labels", "macro_membership")
        self.items.append(item)
        t["items"].append(item)
        return item

    def new_table(self, section, title, population, dimension="all", stratum=""):
        t = dict(id=f"S{section}T{len(self.bysection[section]) + 1:03d}", section=section, title=title,
                 population=population, dimension=dimension, stratum=stratum, items=[])
        self.tables.append(t)
        self.bysection[section].append(t)
        return t

    def replacement(self, section, dimensions):
        for p in self.s.populations:
            for d in dimensions:
                t = self.new_table(section, "Replacement components and deltas", p, d)
                for panel in PANELS:
                    self.add(t, "replacement_panel_results", self.s.lookup("replacement_panel_results", population=p, dimension=d, panel=panel), "point_estimate")
                for delta in DELTAS:
                    self.add(t, "replacement_delta_results", self.s.lookup("replacement_delta_results", population=p, dimension=d, delta=delta), "point_estimate")

    def family(self, name, section=None, predicate=None):
        section = section if section is not None else SECTIONS[name]
        groups = defaultdict(list)
        for row in self.s.tables[name]:
            if predicate is None or predicate(row):
                groups[self.context(name, row)].append(row)
        order = {p: i for i, p in enumerate(("overall",) + self.s.populations)}
        dims = {d: i for i, d in enumerate(("all",) + self.s.dimensions)}
        for (p, d, st), rows in sorted(groups.items(), key=lambda kv: (order[kv[0][0]], STRATA.index(kv[0][2]) if kv[0][2] else -1, dims[kv[0][1]])):
            t = self.new_table(section, name.replace("_", " "), p, d, st)
            for row in rows:
                for col in METRICS[name]:
                    self.add(t, name, row, col)

    def build(self):
        # User requires Section 2 built and validated before assembling the rest.
        self.replacement(2, TAGS)
        self.family("label_support", 2, lambda r: r["dimension"] == "Cross-cutting tag")
        self.family("tag_diagnostics")
        self.validate_tags()
        self.meta["section_2_built_and_validated_first"] = True
        self.family("qa_summary")
        # Dimension-wise complete-case denominators across configured populations.
        for p in self.s.populations:
            t = self.new_table(1, "Dimension-specific common complete-case records", p)
            for d in self.s.dimensions:
                self.add(t, "replacement_panel_results", self.s.lookup("replacement_panel_results", population=p, dimension=d, panel="ABC"), "n_records")
        self.replacement(3, SETS)
        self.family("replacement_trigger_summary")
        self.family("label_support", 5, lambda r: r["dimension"] in SETS)
        for name in ("per_label_contingencies", "per_label_pairwise_kappa", "per_label_model_performance"):
            self.family(name)
        for d in SETS:
            t = self.new_table(5, "Rare-label intentional blanks", "baseline", d)
            for r in self.s.tables["per_label_contingencies"]:
                if r["dimension"] == d and r["support_band"] == "RARE":
                    for metric in ("kappa", "precision", "recall", "f1"):
                        item = self.add(t, "per_label_contingencies", r, metric, force_withheld=True)
                        item["comparison_override"] = "; ".join(PAIRS[p] for p in HUMAN_PAIRS + MODEL_PAIRS) if metric == "kappa" else "Fable 5 versus labelwise human majority"
        for name in ("macro_performance", "exact_set_jaccard_summary", "sufficiency_response_distribution", "sufficiency_record_distribution", "sufficiency_subset_summary", "taxonomy_fit_response_distribution", "taxonomy_fit_record_distribution", "taxonomy_issue_summary", "unclear_register_summary", "taxonomy_coherence_summary", "hard_case_stratum_replacement", "hard_case_stratum_human_pair_agreement", "hard_case_stratum_exact_set_jaccard"):
            self.family(name)
        self.taxonomy_denominators()
        self.s.issue(11, "human-pair summaries", "mean_model_coder_* column naming", "The human-pair CSV exports mean_model_coder_exact_set and mean_model_coder_jaccard. Current code assigns averages of the selected human pairs to these column names.",
                     "The historical uncommitted code snapshot is unavailable; the misleading exported names are retained and are not described as model-versus-human results in that table.", self.s.path("hard_case_stratum_human_pair_agreement") + "; analysis/scratch_coder_hard_case_strata/analysis.py:_set_rows")
        # Protocol intended Wilson intervals more broadly than the summary schemas supply.
        self.s.issue(8, "baseline proportions", "protocol/output interval scope", "Protocol §8.9 and saved methods specify Wilson intervals for baseline proportions. Only subset proportions export Wilson endpoints among these Stage A distribution tables.",
                     "The reason distribution proportion intervals were not exported is not documented; all source values are retained with unavailable interval status.", PROTOCOL + " §8.9; Stage A distribution CSV schemas")
        self.meta["schema_adapters"].update({n: dict(self.meta["schema_adapters"][n], metric_columns=list(cols),
            interval_aliases={c: list(self.bounds(n, self.s.tables[n][0], c)) for c in cols},
            support_aliases={"human_reference_support": "baseline_human_majority_positive_n" if n == "label_support" else "support_n / baseline_support_n / human_majority_positive_n as explicitly keyed", "tag_dimension": "tag"}) for n, cols in METRICS.items()})
        if self.supplement:
            self.supplement.apply(self)
        self.validate()

    def taxonomy_denominators(self):
        for p in ("baseline", "hard_case"):
            t = self.new_table(9, "Taxonomy-issue denominator construction — exported operands and result", p)
            for category in ("Partial Fit", "No Fit", "Cannot assess from register entry"):
                r = self.s.lookup("taxonomy_fit_response_distribution", population=p, coder="all", category=category)
                self.add(t, "taxonomy_fit_response_distribution", r, "count")
            r = self.s.lookup("taxonomy_issue_summary", population=p, issue="Missing or inadequately represented category")
            item = self.add(t, "taxonomy_issue_summary", r, "applicable_denominator")
            item["interval_status"] = "not_applicable"
            item["interval_method"] = "none"
            item["denominator_display"] = "total applicable coder responses; Partial Fit + No Fit; addition not recomputed"

    def validate_tags(self):
        if not set(TAG_DIAGNOSTICS) <= set(METRICS["tag_diagnostics"]):
            raise Fatal("A mandated tag diagnostic is absent from the presentation adapter")
        for row in self.s.tables["tag_diagnostics"]:
            for col in METRICS["tag_diagnostics"]:
                matches = [i for i in self.items if i["source_name"] == "tag_diagnostics" and i["source_key"] == {k: row[k] for k in KEYS["tag_diagnostics"]} and i["metric"] == col]
                if len(matches) != 1 or matches[0]["displayed_estimate"] != row[col] or matches[0]["estimate_status"] == "withheld_support_rule":
                    raise Fatal(f"Tag diagnostic completeness/copy failure: {row['population']}/{row['tag']}/{col}")
                if not matches[0].get("support") or matches[0]["support"]["population_positive_support"] != row["human_majority_positive_n"]:
                    raise Fatal(f"Tag own-population support not displayed: {row['population']}/{row['tag']}")
        for t in self.bysection[2]:
            if t["title"] == "Replacement components and deltas" and len(t["items"]) != 8:
                raise Fatal(f"Incomplete tag replacement components: {t['id']}")
        if any(i["dimension"] in TAGS and i["estimate_status"] == "withheld_support_rule" for i in self.items):
            raise Fatal("A tag metric was withheld")

    def validate(self):
        self.validate_tags()
        for t in self.tables:
            if not t["items"]:
                raise Fatal(f"Empty results table: {t['id']}")
            if t["title"] == "Replacement components and deltas" and len(t["items"]) != 8:
                raise Fatal(f"Incomplete replacement table: {t['id']}")
            for i in t["items"]:
                if i["estimate_status"] not in ESTIMATE_CODES or i["interval_status"] not in INTERVAL_CODES:
                    raise Fatal(f"Unsupported metric-level status: {i['result_id']}")
                if i["dimension"] in SETS and "label" in i["source_key"] and i["metric"] in ("kappa", "precision", "recall", "f1"):
                    r = self.s.lookup("label_support", dimension=i["dimension"], label=i["source_key"]["label"])
                    if r["support_band"] == "RARE" and any(i[k] for k in ("displayed_estimate", "displayed_lower", "displayed_upper")):
                        raise Fatal(f"Rare domain/purpose metric exposure: {i['result_id']}")
                if i["source_name"] == "macro_performance" and (i["dimension"] not in SETS or i["metric"] == "kappa"):
                    raise Fatal("Forbidden macro quantity")
        coverage = defaultdict(set)
        for c in self.lineage:
            if c["lineage_type"] == "summary_csv_cell":
                name = c["source_path"].rsplit("/", 1)[1][:-4]
                row = self.s.lookup(name, **c["row_selection_key"])
                if c["raw_value"] != row[c["column"]]:
                    raise Fatal(f"Raw lineage copy mismatch: {c}")
                if c["displayed_status"] not in ("withheld_support_rule",) and c["displayed_value"] != row[c["column"]]:
                    raise Fatal(f"Displayed lineage copy mismatch: {c}")
                coverage[c["result_id"]].add(c["document_cell_role"])
            elif c["lineage_type"] == "policy_withholding":
                coverage[c["result_id"]].add("estimate")
            elif c["lineage_type"] in ("supplement_interval_cell", "reused_interval_cell"):
                if c["displayed_value"] != c["raw_value"]:
                    raise Fatal(f"Supplement/reuse lineage display mismatch: {c}")
                coverage[c["result_id"]].add(c["document_cell_role"])
        for i in self.items:
            if "estimate" not in coverage[i["result_id"]]:
                raise Fatal(f"Missing estimate lineage: {i['result_id']}")
            if i["interval_status"] == "reported" and not {"interval_lower", "interval_upper"} <= coverage[i["result_id"]]:
                raise Fatal(f"Missing interval lineage: {i['result_id']}")
        self.meta["source_map"] = []
        for t in self.tables:
            refs = [x for x in self.lineage if x["table_id"] == t["id"] and x["lineage_type"] in
                    ("summary_csv_cell", "supplement_interval_cell", "reused_interval_cell")]
            grouped = defaultdict(lambda: {"columns": set(), "keys": {}})
            for r in refs:
                g = grouped[r["source_path"]]
                g["columns"].add(r["column"])
                g["keys"][json.dumps(r["row_selection_key"], sort_keys=True)] = r["row_selection_key"]
            self.meta["source_map"].append(dict(table_id=t["id"], section=t["section"], title=t["title"],
                sources=[dict(path=p, columns=sorted(g["columns"]), row_selection_keys=list(g["keys"].values())) for p, g in grouped.items()]))
        self.meta["validation_results"] = dict(required_schemas="passed", source_identity_checks="recorded identities agree; historical code limitations disclosed",
            frozen_label_coverage="passed", expected_coverage="passed", tag_strata_non_applicability="passed",
            eight_replacement_quantities="passed", tag_diagnostic_completeness="passed", tag_no_withholding="passed",
            domain_purpose_rare_withholding="passed", metric_status_attribution="passed", macro_scope_and_explicit_membership="passed",
            exact_source_cell_copy="passed", join_cardinality="passed", result_lineage="passed", table_source_maps="passed",
            result_items=len(self.items), result_tables=len(self.tables), source_csv_cells=len([c for c in self.lineage if c["lineage_type"] == "summary_csv_cell"]),
            statistical_validation=("37 supplementary Wilson intervals calculated in the dated supplement; no other statistical validation performed"
                                    if self.supplement else "not performed; collation only"), replicate_files_loaded=0)
        if self.supplement:
            self.meta["validation_results"].update(supplement_interval_rows=37, supplement_join_coverage="37 new plus one equivalent-result reuse",
                                                   original_unresolved_entries="69 retained unchanged")

    def row_label(self, item):
        key = item["source_key"]
        name = item["source_name"]
        parts = []
        if name == "replacement_panel_results":
            parts.append("alpha " + key["panel"])
            if item["metric"] == "n_records":
                parts.insert(0, key["dimension"])
        elif name == "replacement_delta_results":
            parts.append(key["delta"])
        else:
            for k, v in key.items():
                if k not in ("population", "dimension", "stratum", "tag"):
                    parts.append(PAIRS.get(v, v) if k == "pair" else "all coders" if k == "coder" and v == "all" else v)
        if item.get("comparison_override"):
            parts.append(item["comparison_override"])
        if not parts:
            parts.append("Fable 5 versus labelwise human majority" if name in ("tag_diagnostics", "macro_performance") else item["dimension"])
        return "; ".join(parts)

    def render_table(self, t):
        population = POP_NAMES[t["population"]]
        if t["population"] == "overall":
            population += " — includes hard-case records; " + DIAGNOSTIC
        heading = f"### {t['id']} — {t['title']} — {population} (`{t['population']}`)"
        if t["dimension"] != "all":
            heading += " — " + t["dimension"]
        if t["stratum"]:
            heading += " — stratum `" + t["stratum"] + "`"
        if t["population"] == "hard_case" and DIAGNOSTIC not in heading:
            raise Fatal("Hard-case table lacks diagnostic header")
        notes = []
        if t["section"] in (2, 5, 6):
            notes.append("Support bands and exported caution flags refer to random-baseline human-majority support. This-population support is stated separately. "
                         "Tag bands never cause withholding. Model performance and tag diagnostics compare Fable 5 with the independent two-of-three labelwise human reference; pairwise kappa uses the named coder pair.")
        if any(i["source_name"] == "macro_performance" for i in t["items"]):
            r = self.s.lookup("macro_performance", dimension=t["dimension"])
            notes.append("Explicit exported eligible membership: " + esc(r["eligible_labels"]) + ".")
        if t["section"] == 11 and "human pair" in t["title"]:
            notes.append("The exported `mean_model_coder_*` names are retained verbatim; current code assigns human-pair averages in this file. See Appendix A for the historical-code limitation.")
        if t["title"].startswith("Taxonomy-issue denominator"):
            notes.append("Applicable response denominator = Partial Fit responses + No Fit responses. The component counts and exported result are copied below; their sum is not computed. Cannot assess is shown as an excluded operand. Record-majority counts are not operands.")
        rows = []
        has_support = any(i["support_display"] for i in t["items"])
        for i in t["items"]:
            status = ESTIMATE_CODES[i["estimate_status"]] + "/" + INTERVAL_CODES[i["interval_status"]]
            if i["interval_status"] == "reported":
                status += "; " + i["interval_method"] + "; confidence " + (i["confidence_level"] or "unresolved")
                if i.get("supplement_interval"):
                    supplement = i["supplement_interval"]
                    if supplement["origin"] == "newly_calculated_supplementary_wilson":
                        status += "; supplementary Wilson 95%; calculated " + supplement["calculation_timestamp_utc"] + "; source " + supplement["source_path"]
                    else:
                        status += "; reused from strict-sufficiency result; source " + supplement["source_path"]
            if i["valid_replicate_count"] is not None:
                status += "; valid/invalid/requested draws " + str(i["valid_replicate_count"]) + "/" + str(i["invalid_replicate_count"] if i["invalid_replicate_count"] is not None else "unavailable") + "/" + str(i["requested_replicate_count"] if i["requested_replicate_count"] is not None else "unavailable")
            if i["interval_status"] in ("suppressed_valid_replicate_threshold", "suppressed_diagnostic_policy"):
                status += "; " + "; ".join(i["status_reason"])
            result = [self.row_label(i), "`" + i["metric"] + "`", i["displayed_estimate"] or "", i["displayed_lower"], i["displayed_upper"], status, i["denominator_display"]]
            if has_support:
                result.append(i["support_display"])
            rows.append(result)
        headers = ["Row / comparator", "Quantity", "Estimate / count / flag", "Interval lower", "Interval upper", "Estimate / interval status; method; draws", "Total / denominator / unit"]
        if has_support:
            headers.append("Observed support and caution")
        return heading + "\n\n" + "\n\n".join(notes + [table(headers, rows)])

    def methodological_notes(self):
        evidence = f"Evidence: `{PROTOCOL}` §§8.2–8.9; saved methods in the three source directories (Appendix B)."
        common = ("Krippendorff’s alpha is reported for ABC (C01/C02/C03), LBC (Fable 5/C02/C03), ALC (C01/Fable 5/C03), and ABL (C01/C02/Fable 5). "
                  "The exported deltas are replacement alpha minus ABC: delta_A = LBC − ABC, delta_B = ALC − ABC, delta_C = ABL − ABC. delta_min is the source-exported minimum of those three deltas. "
                  "Set dimensions use Measuring Agreement on Set-valued Items (MASI) distance; each binary tag uses nominal distance. No deltas are calculated here.")
        return {
            1: "The configuration explicitly lists all six core population identifiers, including the two baseline sufficiency subsets. The broad/strict subset identifiers in Section 8 remain separate source fields. "
               "Complete cases use the same records across the four panels, separately by dimension. Structural-invalid and exposure-flagged responses remain in primary populations; their respective sensitivities exclude an entire affected record. No sample-flow exclusions are inferred. " + evidence,
            2: common + "\n\nCross-cutting tag diagnostics are reported in full for both samples. Where a tag's support is low, the accompanying caution indicates that its values are descriptive and are not stable performance estimates.\n\n"
               "Human-majority positive support requires at least two of C01/C02/C03 to assign the individual label. This reference is not an adjudicated record-level truth set. "
               "The exported support band is baseline-scoped even on hard-case tag rows; the hard-case human-positive count is copied separately. No hard-case support band is inferred. "
               "Raw agreement is the fraction with the same binary classification; positive and negative agreement use their respective class-specific denominators. "
               "Human-majority and model prevalence are distinct. Cohen’s kappa and Gwet’s first-order agreement coefficient (AC1) retain the source comparator. "
               "Precision, recall and F1 (harmonic mean of precision and recall) retain the exported values. True positives (TP), false positives (FP), false negatives (FN) and true negatives (TN) use reference=human majority, prediction=Fable 5. "
               "For positive agreement, the source denominator is 2TP+FP+FN; for negative agreement, 2TN+FP+FN. The operands are displayed, and their denominators are not calculated. " + evidence,
            3: common + "\n\nAnalytical Purpose results describe agreement on classifications assigned from the available register fields. They do not establish the projects' actual analytical purposes or validate register-wide purpose prevalence.\n\n" + evidence,
            4: "Both indicators are copied from the baseline-only trigger summary. YES and NO retain the source meaning; a blank is not NO. Hard-case indicators do not activate or override baseline triggers. Nonbaseline trigger rows are not exported by the source module and are recorded as not applicable to this baseline trigger table. " + evidence,
            5: "All frozen domain/purpose labels appear in the support/contingency tables. The two tags appear in Section 2 and are not duplicated here. "
               "Support is the number of random-baseline records positive under the independent two-of-three human-majority rule. RARE means fewer than 10; LOW SUPPORT means 10–29; STANDARD means at least 30. "
               "For rare domain/purpose labels, kappa, precision, recall, F1 and bounds are intentionally empty (W/W). Source metric rows are absent by the documented eligibility rule; counts and contingencies remain. "
               "LOW SUPPORT metrics retain source intervals where available and the exported caution. Eligibility and caution flags are copied, not inferred as results. "
               "A blank metric for an undefined denominator is not substituted with zero. Purpose majority labels are labelwise and need not form a taxonomy-valid record-level set. " + evidence,
            6: "Macro precision, recall and F1 are the source-exported unweighted fixed-membership averages for baseline, Fable 5 versus the labelwise human-majority reference. "
               "Eligible-label counts and membership lists are copied explicitly. Cross-cutting tags are excluded. Kappa is not macro-averaged in this consolidated report. "
               "Saved Stage B methods suppress a bootstrap interval below " + str(self.s.interval_policy["b"]["minimum_valid"]) + " valid draws out of " + str(self.s.runs["b"]["bootstrap_replicates"]) + " requested draws; the observed metric-specific counts are shown. "
               "An undefined component makes the source fixed-membership macro replicate undefined. No macro-average is computed here. " + evidence,
            7: "Exact-set agreement is equality of the complete unordered sets. Jaccard is intersection divided by union, with empty/empty=1 in the source definition. "
               "The model is compared separately with each coder. No majority exact-set combination is constructed. Median and first/third quartile Jaccard quantities retain their exported names and are not confidence intervals. " + evidence,
            8: "Coder-response and record-majority distributions are separate. A record-majority category requires two identical ratings; No majority / split judgement remains its own category. "
               "Broad register-usable means at least two coders chose Sufficient or Partially sufficient; strict register-sufficient means at least two chose Sufficient. "
               "The subsets use original pre-adjudication ratings. Counts have no confidence interval. Baseline subset proportions carry exported 95% Wilson-score intervals; hard-case subset intervals have an explicit diagnostic nonapplication source field. " + evidence,
            9: "The four response categories retain their source labels: Fit, Partial Fit, No Fit, and Cannot assess from register entry. "
               "They concern whether the taxonomy can adequately represent the project. The frozen instrument says to select Cannot assess when the entry is too limited to determine taxonomy fit, and not to select Partial Fit or No Fit solely because the entry lacks information. "
               "Cannot assess is an evidence-sufficiency outcome, separate from No Fit and from taxonomy defects. Only Partial Fit and No Fit coder responses enter taxonomy-issue denominators; multiple issues can be selected. "
               "Record majorities require two identical categories; split judgements remain separate. The exported operands and resulting issue denominator are displayed below without addition. " + evidence + " Instrument evidence: `" + INSTRUMENT + "`, sc_taxonomy_fit Field Note and response choices.",
            10: "Unclear from Register Entry is a valid taxonomy label separately in Research Domains and Analytical Purposes. It is not a missing response or a sufficiency/taxonomy-fit response category. "
                "Frequency rows distinguish coder-response uses and record-level use by one, two, three or a majority of coders. Response cross-tabs use the exported category-specific response denominators. "
                "Coherence rows use Cannot assess responses as their denominator: the source validator marks Cannot assess with Sufficient as incoherent, and other sufficiency responses as coherent. " + evidence,
            11: "The saved methods explicitly state that this module covers Research Domains and Analytical Purposes and calculates no tag stratum analyses. The cross-cutting tags are absent from all stratum outputs; this is intentional non-applicability in the coverage manifest under user §3.3. "
                "This is a post hoc exploratory diagnostic; no claim is made that the source scope decision was preregistered. "
                "The parent population is hard_case. Source order is domain_only (cross-model Research Domain disagreement only), purpose_only (Analytical Purpose disagreement only), both (both dimensions); these refer to the production/comparison-model sampling disagreement strata, not scratch-coder disagreements. "
                "Each table retains its exported denominator and separate comparisons. Existing bootstrap intervals remain visible. No strata are pooled. " + common + " " + evidence,
        }

    def render(self):
        status = "INCOMPLETE — unresolved metadata or reporting semantics" if self.s.unresolved else "COMPLETE"
        self.meta["status"] = status
        self.meta["unresolved_item_count"] = len(self.s.unresolved)
        rollup = unresolved_explanation_rollup(self.s.unresolved)
        if sum(row["count"] for row in rollup) != len(self.s.unresolved):
            raise Fatal("Unresolved explanation rollup total differs from canonical Appendix A total")
        self.meta["unresolved_explanation_rollup"] = rollup
        notes = self.methodological_notes()
        out = ["# Consolidated scratch-coder results", "## Section 0 — Provenance and report status",
               f"{status}. Unresolved-item count: {len(self.s.unresolved)}; see [Appendix A](#appendix-a--unresolved-or-unavailable-items).",
               "### Unresolved entries grouped by recorded explanation",
               table(["Cannot be established", "Appendix entry count"], [[row["cannot_establish"], row["count"]] for row in rollup]),
               "Entries can concern overlapping limitations. Grouping by exact recorded explanation does not change any entry's status.",
               ("Original point estimates and other source quantities are unchanged. Thirty-seven supplementary Wilson intervals were newly calculated; three interval entries use existing source bounds, comprising two retained original sufficiency-subset intervals and one verified equivalent-result lookup."
                if self.supplement else "Analytical results are collated from existing outputs; no analytical statistics have been recomputed."),
               "No replicate files were loaded; no replicate-validity count exception was used. Validation covers structure, identifiers, copying and presentation, not independent statistical validation.",
               "Generation time (UTC): `" + self.meta["generation_timestamp_utc"] + "`. Generator HEAD: `" + str(self.meta["generator"]["git_head"]) + "`. Generator working-tree state: " + ("dirty" if self.meta["generator"]["git_status_before"] else "clean") + ". These describe the generator, not the source runs.",
               "Source directories and run timestamps:"]
        for stage in DIRS:
            r = self.s.runs[stage]
            head = r.get("git_HEAD", r.get("git_head", r.get("analysis_code_commit_or_worktree_state", {}).get("head_commit")))
            out.append(f"- `{DIRS[stage]}/`: `{r.get('analysis_run_datetime', 'unavailable')}`; source HEAD `{head}`; source code was uncommitted at run time (Appendix A).")
        production = self.s.release["production_model"]
        out.append("Production release: `" + self.s.release["release"]["release_id"] + "`; model `" + production["model_identifier"] + "`; prompt identifier `" + production["prompt_version"] + "`; dictionary `" + self.s.release["taxonomy"]["taxonomy_version"] + "`. "
                   "These identifiers are joined through the release manifest’s protected model-output and dictionary hashes. Source protocol: PRO-018, `" + PROTOCOL + "`, SHA-256 `" + self.s.runs["a"]["protocol_sha256"] + "`. "
                   "Recorded shared input identities agree across stages. Stage B documents the model output’s LF-normalised representation. Restricted source inputs were not opened. Exact current and recorded hashes are in metadata.")
        out.append("The deviation log was consulted for reporting context. Its open hidden-child-value item concerns owner responses and does not supply a scratch-coder reporting amendment. "
                   "The saved analysis methods and hash-verified protocol are distinguished from current generating code, whose exact historical version is unavailable.")
        out.append("Status legend used in every table: before the slash = estimate; after the slash = interval. R reported; W withheld by the domain/purpose support rule; D undefined; A unavailable in source; U unresolved; N not applicable; SD interval suppressed by explicit diagnostic policy; SV interval suppressed by valid-replicate policy. Full definitions and source maps are in Appendix B. All values preserve source precision and scale.")
        if self.supplement:
            supplement = self.meta["supplement"]
            out += ["### Supplement coverage",
                    "The dated post-registration supplement at `" + supplement["directory"] + "` supplies 37 newly calculated marginal two-sided 95% Wilson score intervals without continuity correction. WSA0082 and WSA0083 retain their original Stage A intervals; WSA0074 reuses WSA0083 after the verified one-to-one equivalent-result lookup. Newly supplied cells are marked in their table status. Original source absence/status remains in metadata lineage.",
                    "The selected scope covers the specified named-coder and record-level research-reporting outcomes. QA frequencies remain descriptive; ordinary Wilson intervals are not applied to pooled within-project ratings. This is an explicit interpretation of the protocol’s broad baseline-proportions clause, not a claim that every baseline proportion has received an interval or that QA intervals would necessarily be mathematically invalid.",
                    "All 69 original-source unresolved reporting/provenance entries remain open and retain their identifiers and descriptions. U0069's undocumented historical omission reason remains unresolved; the supplement supplies intervals for only the selected cells and is a partial presentational remedy, not recovery of that reason."]
        for sec in range(1, 12):
            out += [f"## Section {sec} — {TITLES[sec]}", notes[sec]]
            out.extend(self.render_table(t) for t in self.bysection[sec])
        out += ["## Appendix A — Unresolved or unavailable items"]
        if not self.s.unresolved:
            out.append("There are no unresolved items.")
        else:
            out.append(("These are the 69 original-source limitations from the Task B consolidation, retained without renumbering or closure. Historical wording such as ‘not computed here’ describes the original consolidation. Source-defined suppression and intentional rare-domain/purpose blanks are not unresolved errors. Entries below identify unavailable provenance or reporting semantics."
                        if self.supplement else "Source-defined suppression and intentional rare-domain/purpose blanks are not unresolved errors. Entries below identify unavailable provenance or reporting semantics."))
            out.append(table(["ID", "Section / result key", "Affected field", "Known", "Cannot be established", "Source"],
                [[x["id"], str(x["section"]) + " / " + str(x["result_key"]) + (" / " + DIAGNOSTIC if str(x["section"]) == "11" or "hard_case" in str(x["result_key"]) else ""), x["field"], x["known"], x["cannot_establish"], x["source_location"]] for x in self.s.unresolved]))
            if self.supplement:
                out.append("Supplement coverage does not alter these original-source records. U0069 remains open because newly supplied intervals do not establish why the historical distribution intervals were omitted, and its scope also includes excluded rows.")
        out += ["## Appendix B — Source map and status definitions",
                "Detailed cell lineage, original strings/statuses, metric statuses, schema adapters, coverage keys and non-applicability entries are in `run_metadata.json`. "
                "A missing source field remains unavailable. Zero, NO and False are substantive values. Empty domain/purpose rare-metric cells are intentional W/W; tags are always reported with their exported caution. "
                "An exported interval remains reported even if its confidence level cannot be established. Missing bounds alone do not establish suppression.",
                table(["Field", "Values / meaning"], [["estimate_status", "; ".join(k + "=" + v for k, v in ESTIMATE_CODES.items())], ["interval_status", "; ".join(k + "=" + v for k, v in INTERVAL_CODES.items())], ["interval_method", "wilson_score; bootstrap_percentile; other_documented; none; unresolved"], ["source_status", "Original source status/reason fields unchanged, or explicit absence"], ["status_reason / policy_source", "Independent applicable reasons and exact source evidence retained per metric"]]),
                "Methodological evidence: `" + CONFIG + "` (population/dimension order); hash-verified `" + DICTIONARY + "` (frozen label identities); `" + RELEASE + "` (production model/prompt identity); `" + PROTOCOL + "` §§8.2–8.9 (reporting policy); `" + DEVIATIONS + "` (documented deviations). "
                "Saved Stage A methods: loading, panel definitions, MASI/nominal distance, majority/subset definitions, percentile/Wilson methods and suppression threshold. Saved Stage B methods: majority reference, baseline support bands, macro eligibility, binary comparison orientation, exact-set/Jaccard definitions, percentile levels and valid-replicate rule. Saved strata methods: strata scope/order, reuse of methods and diagnostic status. Exact file hashes and current-code locations appear in metadata.",
                "Source-run bootstrap settings (provenance, not analytical results): " + "; ".join(f"{s}: requested={r.get('bootstrap_replicates', 'unavailable')}, seed={r.get('bootstrap_seed', 'unavailable')}, quantile method={r.get('quantile_method', 'unavailable')}" for s, r in self.s.runs.items()) + ". Saved methods identify record resampling with linked ratings. Stage B saved methods specify 2.5/97.5 percentiles. Unavailable historical confidence-level annotations are listed in Appendix A."]
        for mapping in self.meta["source_map"]:
            out.append("### Source map " + mapping["table_id"])
            for src in mapping["sources"]:
                out.append("`" + src["path"] + "`; columns: " + ", ".join("`" + c + "`" for c in src["columns"]) + ". Row selections: " + esc(json.dumps(src["row_selection_keys"], ensure_ascii=False)) + ".")
        return "\n\n".join(out) + "\n"
