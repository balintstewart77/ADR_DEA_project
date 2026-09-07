"""Read-only, summary-only source inventory and structural compatibility checks.

No source-analysis modules are imported. CSV values remain strings throughout.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
DIRS = {
    "a": "analysis/outputs_validation_scratch_20260824",
    "b": "analysis/outputs_validation_scratch_stage_b_20260825",
    "h": "analysis/outputs_validation_scratch_hard_case_strata_20260825",
}
METHODS = {"a": "methods_stage_a.md", "b": "methods_stage_b.md", "h": "methods_hard_case_strata.md"}
CONFIG = "analysis/scratch_coder_stage_a/config.py"
PROTOCOL = "preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx"
RELEASE = "preregistration/package/02_taxonomy_prompt_and_model/production_release_manifest.yaml"
DICTIONARY = "taxonomy_data_dictionary.yaml"
DEVIATIONS = "preregistration/package/09_logs_and_templates/protocol_deviation_log.csv"
INSTRUMENT = "preregistration/package/06_redcap/redcap_data_dictionary_frozen_0.7_2026-07-22.csv"
SETS = ("Research Domains", "Analytical Purposes")
TAGS = ("Demographic disparities / equity", "COVID-19 & Pandemic")
PANELS = ("ABC", "LBC", "ALC", "ABL")
DELTAS = ("delta_A", "delta_B", "delta_C", "delta_min")
MODEL_PAIRS = ("L-A", "L-B", "L-C")
HUMAN_PAIRS = ("A-B", "A-C", "B-C")
STRATA = ("domain_only", "purpose_only", "both")
SUFF = ("Sufficient", "Partially sufficient", "Insufficient")
FIT = ("Fit", "Partial Fit", "No Fit", "Cannot assess from register entry")
SPLIT = "No majority / split judgement"
KEYS = {
    "qa_summary": ("population", "dimension", "measure"),
    "replacement_panel_results": ("population", "dimension", "panel"),
    "replacement_delta_results": ("population", "dimension", "delta"),
    "replacement_trigger_summary": ("population", "dimension"),
    "sufficiency_response_distribution": ("population", "coder", "category"),
    "sufficiency_record_distribution": ("population", "category"),
    "sufficiency_subset_summary": ("population", "subset"),
    "taxonomy_fit_response_distribution": ("population", "coder", "category"),
    "taxonomy_fit_record_distribution": ("population", "category"),
    "taxonomy_issue_summary": ("population", "issue"),
    "unclear_register_summary": ("population", "dimension", "section", "measure", "category"),
    "taxonomy_coherence_summary": ("population", "analysis", "category"),
    "label_support": ("dimension", "label"),
    "per_label_contingencies": ("dimension", "label"),
    "per_label_model_performance": ("dimension", "label"),
    "per_label_pairwise_kappa": ("dimension", "label", "pair"),
    "macro_performance": ("dimension",),
    "tag_diagnostics": ("population", "tag"),
    "exact_set_jaccard_summary": ("population", "dimension", "pair"),
    "hard_case_stratum_replacement": ("stratum", "dimension"),
    "hard_case_stratum_human_pair_agreement": ("stratum", "dimension", "pair"),
    "hard_case_stratum_exact_set_jaccard": ("stratum", "dimension", "pair"),
}
SECTIONS = {
    "qa_summary": 1, "replacement_panel_results": [2, 3], "replacement_delta_results": [2, 3],
    "replacement_trigger_summary": 4, "label_support": [2, 5], "tag_diagnostics": 2,
    "per_label_contingencies": 5, "per_label_model_performance": 5, "per_label_pairwise_kappa": 5,
    "macro_performance": 6, "exact_set_jaccard_summary": 7,
    "sufficiency_response_distribution": 8, "sufficiency_record_distribution": 8, "sufficiency_subset_summary": 8,
    "taxonomy_fit_response_distribution": 9, "taxonomy_fit_record_distribution": 9, "taxonomy_issue_summary": 9,
    "unclear_register_summary": 10, "taxonomy_coherence_summary": 10,
    "hard_case_stratum_replacement": 11, "hard_case_stratum_human_pair_agreement": 11,
    "hard_case_stratum_exact_set_jaccard": 11,
}


class Fatal(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.stdout.rstrip("\n") if p.returncode == 0 else None


def literal_assignments(text):
    result = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    try:
                        result[target.id] = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        pass
    return result


class Sources:
    def __init__(self, metadata):
        self.meta = metadata
        self.files = metadata.setdefault("source_files", {})
        self.tables = {}
        self.index = {}
        self.stage = {}
        self.runs = metadata.setdefault("source_run_metadata", {})
        self.manifest = metadata.setdefault("expected_coverage_manifest", [])
        self.joins = metadata.setdefault("join_checks", [])
        self.unresolved = metadata.setdefault("unresolved_items", [])
        self._issue_keys = set()

    def issue(self, section, key, field, known, unknown, source):
        identity = (str(section), str(key), field)
        if identity in self._issue_keys:
            return next(x["id"] for x in self.unresolved if (str(x["section"]), str(x["result_key"]), x["field"]) == identity)
        self._issue_keys.add(identity)
        number = f"U{len(self.unresolved) + 1:04d}"
        self.unresolved.append(dict(id=number, section=section, result_key=key, field=field,
                                    known=known, cannot_establish=unknown, source_location=source))
        return number

    def read(self, relative):
        p = ROOT / relative
        resolved = p.resolve()
        if "preregistration_restricted" in p.parts or "preregistration_restricted" in resolved.parts:
            raise Fatal(f"Inaccessible under task instruction: {relative}")
        if not resolved.is_relative_to(ROOT) or p.is_symlink():
            raise Fatal(f"Unsupported source location: {relative}")
        if p.name.startswith("bootstrap_"):
            raise Fatal(f"Replicate files are disabled: {relative}")
        data = p.read_bytes()
        observed = sha(data)
        if relative in self.files and self.files[relative]["sha256"] != observed:
            raise Fatal(f"Source changed during reads: {relative}")
        self.files[relative] = {"sha256": observed, "bytes": len(data)}
        return data

    def text(self, relative):
        return self.read(relative).decode("utf-8-sig")

    def lookup(self, name, **key):
        if set(key) != set(KEYS[name]):
            raise Fatal(f"Incomplete lookup key for {name}: {key}")
        try:
            return self.index[name][tuple(key[k] for k in KEYS[name])]
        except KeyError as exc:
            raise Fatal(f"Unmatched required key: {name}: {key}") from exc

    def ref(self, name, row, column):
        return {"lineage_type": "summary_csv_cell", "source_path": self.path(name),
                "row_selection_key": {k: row[k] for k in KEYS[name]}, "column": column,
                "raw_value": row[column]}

    def path(self, name):
        return f"{DIRS[self.stage[name]]}/{name}.csv"

    def expect(self, name, expected, evidence):
        expected = list(expected)
        if len(expected) != len(set(expected)):
            raise Fatal(f"Duplicate expected manifest keys: {name}")
        actual = set(self.index[name])
        wanted = set(expected)
        entry = dict(section=SECTIONS[name], source=self.path(name), key_columns=KEYS[name],
                     expected_keys=expected, expected_row_count=len(expected), observed_row_count=len(actual),
                     missing_keys=sorted(wanted - actual), unexpected_keys=sorted(actual - wanted),
                     scope_evidence=evidence, status="passed" if actual == wanted else "failed")
        self.manifest.append(entry)
        if actual != wanted:
            raise Fatal(f"Coverage failure {self.path(name)}: missing={entry['missing_keys']}; unexpected={entry['unexpected_keys']}")

    def load(self):
        schemas = json.loads((PACKAGE / "schemas.json").read_text())
        adapters = self.meta.setdefault("schema_adapters", {})
        for stage, files in schemas.items():
            for name, expected in files.items():
                path = f"{DIRS[stage]}/{name}.csv"
                try:
                    reader = csv.DictReader(io.StringIO(self.text(path)))
                except FileNotFoundError as exc:
                    raise Fatal(f"Required CSV missing: {path}; semantic fields={expected}; actual columns=[]") from exc
                columns = reader.fieldnames
                if columns is None or len(columns) != len(set(columns)) or set(columns) != set(expected):
                    raise Fatal(f"Unsupported schema {path}; required semantic columns={expected}; actual columns={columns}")
                rows = list(reader)
                if any(None in r or any(v is None for v in r.values()) for r in rows):
                    raise Fatal(f"Malformed CSV record: {path}; actual columns={columns}")
                idx = {}
                for row in rows:
                    key = tuple(row[k] for k in KEYS[name])
                    if key in idx:
                        raise Fatal(f"Ambiguous duplicate row key {path}: {key}; actual columns={columns}")
                    idx[key] = row
                self.tables[name], self.index[name], self.stage[name] = rows, idx, stage
                adapters[name] = dict(source_path=path, columns=columns, source_row_key=KEYS[name],
                    section=SECTIONS[name], column_aliases={}, implicit_population=("baseline" if stage == "b" and "population" not in columns else "hard_case" if stage == "h" else None),
                    population_evidence=f"{DIRS[stage]}/{METHODS[stage]}", duplicate_keys=0)
        for stage in DIRS:
            self.runs[stage] = json.loads(self.text(f"{DIRS[stage]}/run_metadata.json"))
            methods = self.text(f"{DIRS[stage]}/{METHODS[stage]}")
            requested = re.search(r"([\d,]+) (?:attempted )?record-level", methods)
            seed = re.search(r"seed (\d+)", methods)
            if not requested or not seed or int(requested[1].replace(",", "")) != self.runs[stage].get("bootstrap_replicates") or int(seed[1]) != self.runs[stage].get("bootstrap_seed"):
                raise Fatal(f"Bootstrap metadata/methods identity mismatch or unsupported settings: {stage}")
        saved_a = self.text(f"{DIRS['a']}/{METHODS['a']}")
        saved_b = self.text(f"{DIRS['b']}/{METHODS['b']}")
        threshold_a = re.search(r"fewer than ([\d,]+) replicates are valid", saved_a)
        threshold_b = re.search(r"below ceil\(0.90\*attempts\)=([\d,]+) valid replicates", saved_b)
        if not threshold_a or not threshold_b or "2.5/97.5" not in saved_b:
            raise Fatal("Unsupported saved interval-policy evidence in Stage A/B methods")
        self.interval_policy = {"a": {"minimum_valid": int(threshold_a[1].replace(",", "")), "confidence_level": None},
                                "b": {"minimum_valid": int(threshold_b[1].replace(",", "")), "confidence_level": "95%"}}
        self.meta["interval_policy"] = self.interval_policy
        self.config = literal_assignments(self.text(CONFIG))
        self.populations = tuple(self.config["POPULATION_ORDER"])
        self.dimensions = tuple(self.config["DIMENSIONS"])
        if self.dimensions != SETS + TAGS:
            raise Fatal(f"Unsupported dimensions in {CONFIG}: {self.dimensions}")
        if self.populations != ("baseline", "baseline_exposure_sensitivity", "baseline_structural_sensitivity", "hard_case", "baseline_broad_usable", "baseline_strict_sufficient"):
            raise Fatal(f"Unsupported populations in {CONFIG}: {self.populations}")
        self.meta["identities"] = dict(population_order=self.populations, dimensions=self.dimensions,
            population_source=CONFIG, subset_populations_explicitly_configured=True,
            stratum_order=STRATA, stratum_parent="hard_case", aliases={
                "Cross-cutting tag + label": "dimension = label; label = label",
                "Demographic disparities / equity tag": TAGS[0],
                "sufficiency response code 2: Partial": "Partially sufficient (Stage A exported display label)",
                "A": "C01", "B": "C02", "C": "C03", "L": "production model MOD-006"})
        # Static reads only: this code is never imported or attributed to an old run.
        code_paths = ["analysis/scratch_coder_stage_a/" + n + ".py" for n in ("agreement", "panels", "sufficiency", "taxonomy", "report")]
        code_paths += ["analysis/scratch_coder_stage_b/" + n + ".py" for n in ("config", "performance", "tags", "support", "agreement", "bootstrap", "metrics")]
        code_paths += ["analysis/scratch_coder_hard_case_strata/analysis.py"]
        self.meta["current_code_evidence"] = {p: {"sha256": sha(self.read(p)), "historical_identity": "not established"} for p in code_paths}
        self.compatibility()
        self.coverage()
        self.support_joins()
        self.meta["preflight"] = "passed"

    def compatibility(self):
        authorities = {s: {x["role"]: x for x in r["verified_authorities"]} for s, r in self.runs.items()}
        findings = self.meta.setdefault("source_compatibility", [])
        for role in ("raw_export", "protocol", "taxonomy_rc2", "production_model", "baseline_sample", "hard_case_sample", "formal_assignment_crosswalk"):
            identities = {s: authorities[s][role]["expected_sha256"] for s in DIRS}
            if len(set(identities.values())) != 1:
                raise Fatal(f"Incompatible source release: {role}: {identities}")
            findings.append(dict(field=role, expected_relationship="same protected input identity, different stage scopes", recorded_identities=identities, status="recorded identities agree; underlying restricted inputs not opened"))
        if self.runs["b"]["stage_a_reference_directory"] != DIRS["a"]:
            raise Fatal("Stage B references another Stage A run")
        for name in self.tables:
            if self.stage[name] != "a":
                continue
            filename = name + ".csv"
            before = self.runs["b"]["stage_a_numerical_hashes_before"].get(filename)
            after = self.runs["b"]["stage_a_numerical_hashes_after"].get(filename)
            current = self.files[self.path(name)]["sha256"]
            if before != after or before != current:
                raise Fatal(f"Stage A summary identity differs from Stage B's recorded source: {filename}")
        findings.append(dict(field="Stage A required summaries", status="actual hashes match Stage B recorded before/after hashes", expected_relationship="same Stage A source outputs"))
        for stage in DIRS:
            for role, entry in authorities[stage].items():
                if entry.get("matched") is not True:
                    raise Fatal(f"Source authority marked unmatched: {stage}/{role}")
                if entry["observed_sha256"] != entry["expected_sha256"]:
                    model = self.runs["b"]["production_model"]
                    if role != "production_model" or entry["observed_sha256"] != model["working_tree_lf_sha256"] or entry["expected_sha256"] != model["protected_raw_sha256"]:
                        raise Fatal(f"Unexplained source representation mismatch: {stage}/{role}")
                    findings.append(dict(stage=stage, field=role, status="documented LF representation", evidence="Stage B run_metadata.json: production_model"))
        for path, role in ((DICTIONARY, "taxonomy_rc2"), (PROTOCOL, "protocol"), (INSTRUMENT, "instrument")):
            if sha(self.read(path)) != authorities["a"][role]["expected_sha256"]:
                raise Fatal(f"Historical release compatibility failure: {path}")
        instrument_rows = list(csv.DictReader(io.StringIO(self.text(INSTRUMENT))))
        self.meta["scratch_response_definitions"] = [{k: row[k] for k in ("Variable / Field Name", "Field Label", "Choices, Calculations, OR Slider Labels", "Field Note")} for row in instrument_rows if row["Variable / Field Name"] in ("sc_taxonomy_fit", "sc_sufficiency")]
        dictionary = yaml.safe_load(self.text(DICTIONARY))
        labels = []
        layer_dim = {"Layer A -- domain": SETS[0], "Layer C -- purpose": SETS[1]}
        for entry in dictionary["categories"]:
            if entry.get("include_in_prompt") is not True:
                continue
            label = entry["label"]
            if entry["layer"] == "Cross-cutting tag":
                label = TAGS[0] if label == "Demographic disparities / equity tag" else label
                dim = label
            elif entry["layer"] in layer_dim:
                dim = layer_dim[entry["layer"]]
            else:
                raise Fatal(f"Unexpected active dictionary entry: {entry['layer']}/{label}")
            labels.append((dim, label))
        if len(labels) != len(set(labels)) or tuple(sum(d == x for d, _ in labels) for x in self.dimensions) != (12, 8, 1, 1):
            raise Fatal(f"Frozen label universe mismatch: {labels}")
        self.labels = labels
        self.meta["identities"].update(dictionary_version=dictionary["metadata"]["dictionary_version"], frozen_label_universe=labels,
                                         dictionary_hash=sha(self.read(DICTIONARY)))
        self.release = yaml.safe_load(self.text(RELEASE))
        if self.release["production_model"]["output_sha256"] != authorities["a"]["production_model"]["expected_sha256"] or self.release["taxonomy"]["taxonomy_sha256"] != sha(self.read(DICTIONARY)):
            raise Fatal("Production release manifest does not identify the source release")
        self.meta["production_release"] = self.release
        # Read only protocol paragraphs needed for scratch-coder definitions/reporting.
        root = ET.fromstring(zipfile.ZipFile(io.BytesIO(self.read(PROTOCOL))).read("word/document.xml"))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = ["".join(t.text or "" for t in p.iter(ns + "t")) for p in root.iter(ns + "p")]
        self.meta["policy_evidence"] = [dict(path=PROTOCOL, paragraph_index=i, text=p) for i, p in enumerate(paragraphs)
            if any(t in p for t in ("A label's support", "Fewer than 10 positive", "10 to 29 positive", "For each tag:", "Its binary-tag diagnostics", "Baseline proportions will use", "For each binary tag", "Cannot assess will be reported"))]
        if not any("Fewer than 10 positive" in x["text"] for x in self.meta["policy_evidence"]):
            raise Fatal("Rare-support policy not found in hash-verified protocol")
        self.text(DEVIATIONS)
        for stage in DIRS:
            self.issue(0, stage, "historical_code_snapshot", "The source run records its HEAD and uncommitted code; saved methods describe the run.",
                       "An exact snapshot/hash of the uncommitted analysis code used by the run is unavailable. Current code is corroborating evidence only.",
                       f"{DIRS[stage]}/run_metadata.json; {DIRS[stage]}/{METHODS[stage]}")
        self.issue(0, "Stage A intervals", "confidence_level", "Saved methods identify percentile intervals, Type 7 and replicate policy; current code uses 0.025/0.975.",
                   "The saved Stage A metadata/methods do not state the bootstrap confidence level, and current code has no verified historical snapshot. Bounds are retained without a confidence-level claim.",
                   f"{DIRS['a']}/methods_stage_a.md; {DIRS['a']}/run_metadata.json")
        self.issue(11, "replacement intervals", "confidence_level", "Strata methods document reuse of Stage A bootstrap and Type 7.",
                   "The historical replacement bootstrap confidence level is not explicitly recorded in saved methods/metadata.", f"{DIRS['h']}/methods_hard_case_strata.md")

    def coverage(self):
        product = itertools.product
        a_method = f"{DIRS['a']}/{METHODS['a']}; {CONFIG}; current agreement.py corroboration"
        b_method = f"{DIRS['b']}/{METHODS['b']}; current Stage B generating loops corroboration"
        h_method = f"{DIRS['h']}/{METHODS['h']}; current strata generating loops corroboration"
        self.expect("replacement_panel_results", product(self.populations, self.dimensions, PANELS), a_method)
        self.expect("replacement_delta_results", product(self.populations, self.dimensions, DELTAS), a_method)
        for name in ("replacement_panel_results", "replacement_delta_results"):
            for row in self.tables[name]:
                if row["point_estimate"] == "":
                    raise Fatal(f"Missing replacement estimate without a point-specific source status: {self.path(name)}; key={tuple(row[k] for k in KEYS[name])}; actual columns={list(row)}")
        self.expect("replacement_trigger_summary", product(("baseline",), self.dimensions), a_method)
        self.manifest.append(dict(section=4, populations=[p for p in self.populations if p != "baseline"], status="intentional_non_applicability", reason="Source trigger summary is baseline-only; diagnostic indicators do not activate or override baseline triggers.", evidence=a_method))
        support_keys = [("Cross-cutting tag" if d in TAGS else d, l) for d, l in self.labels]
        self.expect("label_support", support_keys, f"Hash-verified {DICTIONARY}: include_in_prompt=true; explicit layer/tag aliases")
        self.expect("per_label_contingencies", [(d, l) for d, l in self.labels if d in SETS], b_method)
        eligible = []
        for row in self.tables["label_support"]:
            n = int(row["baseline_human_majority_positive_n"])
            expected_band = "RARE" if n < 10 else "LOW SUPPORT" if n < 30 else "STANDARD"
            if row["support_band"] != expected_band:
                raise Fatal(f"Exported support band conflicts with documented rule: {row}")
            if row["dimension"] in SETS and row["eligible_for_per_label_performance"] == "True":
                eligible.append((row["dimension"], row["label"]))
            if row["eligible_for_per_label_performance"] != str(n >= 10):
                raise Fatal(f"Support eligibility conflicts with policy: {row}")
            if row["low_support_caution_required"] != str(expected_band == "LOW SUPPORT"):
                raise Fatal(f"Exported caution conflicts with documented source rule: {row}")
        self.expect("per_label_model_performance", eligible, "Explicit label_support.csv eligible_for_per_label_performance flags; baseline only")
        self.expect("per_label_pairwise_kappa", [(d, l, p) for d, l in eligible for p in HUMAN_PAIRS + MODEL_PAIRS], b_method)
        self.manifest.append(dict(section=5, status="intentional_withholding", population="baseline",
            label_keys=[(r["dimension"], r["label"]) for r in self.tables["label_support"] if r["dimension"] in SETS and r["support_band"] == "RARE"],
            metrics=["kappa", "precision", "recall", "f1"], reason="Source eligibility excludes rare domain/purpose metric rows; counts remain and explicit W/W rows are presented.", evidence=b_method + "; user v2 §5.1"))
        self.expect("macro_performance", [(d,) for d in SETS], b_method)
        for row in self.tables["macro_performance"]:
            membership = row["eligible_labels"].split("; ")
            exported = {r["label"] for r in self.tables["label_support"] if r["dimension"] == row["dimension"] and r["eligible_for_macro_average"] == "True"}
            if len(membership) != len(set(membership)) or len(membership) != int(row["eligible_label_n"]) or set(membership) != exported:
                raise Fatal(f"Explicit macro membership/count inconsistency: {row['dimension']}")
        self.expect("tag_diagnostics", product(("baseline", "hard_case"), TAGS), b_method)
        self.expect("exact_set_jaccard_summary", product(("baseline", "hard_case"), SETS, MODEL_PAIRS), b_method)
        self.expect("hard_case_stratum_replacement", product(STRATA, SETS), h_method)
        for row in self.tables["hard_case_stratum_replacement"]:
            for column in ("human_alpha", "replace_a_alpha", "replace_b_alpha", "replace_c_alpha", "delta_a", "delta_b", "delta_c", "delta_min"):
                if row[column] == "":
                    raise Fatal(f"Missing stratum replacement estimate without an explicit source status: {self.path('hard_case_stratum_replacement')}; metric={column}; key={(row['stratum'], row['dimension'])}")
        self.expect("hard_case_stratum_exact_set_jaccard", product(STRATA, SETS, MODEL_PAIRS), h_method)
        self.expect("hard_case_stratum_human_pair_agreement", product(STRATA, SETS, HUMAN_PAIRS), h_method)
        self.manifest.append(dict(section=11, status="intentional_non_applicability", parent_population="hard_case", strata=STRATA,
            dimensions=TAGS, reason="Source methods explicitly state no tag stratum analyses are calculated; user v2 §3.3 pre-registers non-applicability.", evidence=h_method))
        for prefix, categories in (("sufficiency", SUFF), ("taxonomy_fit", FIT)):
            self.expect(prefix + "_response_distribution", product(("baseline", "hard_case"), ("all", "C01", "C02", "C03"), categories), a_method)
            self.expect(prefix + "_record_distribution", product(("baseline", "hard_case"), categories + (SPLIT,)), a_method)
        self.expect("sufficiency_subset_summary", product(("baseline", "hard_case"), ("broad_register_usable", "strict_register_sufficient")), a_method)
        tax_config = literal_assignments(self.text("analysis/scratch_coder_stage_a/taxonomy.py"))
        self.expect("taxonomy_issue_summary", product(("baseline", "hard_case"), tax_config["ISSUE_LABELS"].values()), a_method)
        unclear = []
        for p, d in product(("baseline", "hard_case"), SETS):
            unclear.extend((p, d, "frequency", m, "Unclear") for m in ("coder_response_uses", "records_with_1_of_3", "records_with_2_of_3", "records_with_3_of_3", "records_with_majority_use"))
            for construct, cats in (("sufficiency", SUFF), ("confidence", ("High", "Medium", "Low"))):
                unclear.extend((p, d, "response_crosstab_" + construct, "unclear_use", c) for c in cats)
        self.expect("unclear_register_summary", unclear, a_method)
        coherent = []
        for p in ("baseline", "hard_case"):
            for analysis, cats in (("cannot_assess_by_sufficiency", SUFF), ("cannot_assess_by_confidence", ("High", "Medium", "Low")), ("candidate_0.7_cannot_assess_coherence", ("validator_coherent", "validator_incoherent"))):
                coherent.extend((p, analysis, c) for c in cats)
        self.expect("taxonomy_coherence_summary", coherent, a_method)
        qa = []
        measures = ("records", "expected_responses", "submitted_responses", "complete_responses", "incomplete_responses", "structural_invalid_responses", "structural_invalid_projects", "exposure_flagged_responses", "exposure_affected_projects", "structural_sensitivity_retained_projects", "exposure_sensitivity_retained_projects")
        for p in ("overall", "baseline", "hard_case"):
            qa.extend((p, "all", m) for m in measures)
            qa.extend((p, d, "complete_matched_three_coder_panels") for d in self.dimensions)
        qa += [("overall", "all", "rows_in_raw_export")]
        qa += [("hard_case", "all", f"hard_case_stratum_{s}_records") for s in STRATA]
        self.expect("qa_summary", qa, "Current Stage A report.py:qa_rows read statically; saved Stage A methods and verified configuration")
        self.meta["observed_tag_support"] = [{"branch": "tag_always_report_with_caution", "support_population": "baseline",
            "identity": {"dimension": r["label"], "label": r["label"]},
            "cells": {c: self.ref("label_support", r, c) for c in r if c not in KEYS["label_support"]}}
            for r in self.tables["label_support"] if r["dimension"] == "Cross-cutting tag"]

    def support_joins(self):
        for name in ("per_label_contingencies", "per_label_model_performance", "per_label_pairwise_kappa", "tag_diagnostics"):
            for row in self.tables[name]:
                dim, label = ("Cross-cutting tag", row["tag"]) if name == "tag_diagnostics" else (row["dimension"], row["label"])
                support = self.lookup("label_support", dimension=dim, label=label)
                if row["support_band"] != support["support_band"]:
                    raise Fatal(f"Support join conflict {name}: {dim}/{label}")
                col = "baseline_support_n" if name == "tag_diagnostics" else "human_majority_positive_n" if name == "per_label_contingencies" else "support_n"
                if row[col] != support["baseline_human_majority_positive_n"]:
                    raise Fatal(f"Support count join conflict {name}: {dim}/{label}")
                if "low_support_caution" in row and row["low_support_caution"] != support["low_support_caution_required"]:
                    raise Fatal(f"Support caution join conflict {name}: {dim}/{label}")
                if name == "tag_diagnostics" and row["population"] == "baseline" and row["human_majority_positive_n"] != support["baseline_human_majority_positive_n"]:
                    raise Fatal(f"Baseline tag human reference count conflict: {label}")
            self.joins.append(dict(left=self.path(name), right=self.path("label_support"),
                left_keys=(["tag"] if name == "tag_diagnostics" else ["dimension", "label"]), right_keys=["dimension", "label"],
                alias_rule=("dimension=Cross-cutting tag, label=tag; baseline band remains explicitly baseline-scoped" if name == "tag_diagnostics" else "implicit population=baseline"),
                cardinality="many_to_one", left_rows=len(self.tables[name]), joined_rows=len(self.tables[name]), unmatched=0, right_duplicates=0, status="passed"))
        for p, d in itertools.product(self.populations, self.dimensions):
            denominators = {r["n_records"] for name in ("replacement_panel_results", "replacement_delta_results") for r in self.tables[name] if r["population"] == p and r["dimension"] == d}
            if len(denominators) != 1:
                raise Fatal(f"Replacement panel/delta denominator incompatibility {p}/{d}")
        self.joins.append(dict(left=self.path("replacement_panel_results"), right=self.path("replacement_delta_results"),
            keys=["population", "dimension"], cardinality="one group of four panels to one group of four deltas; no Cartesian row merge", status="passed", unmatched=0))

    def unchanged(self):
        changed = []
        for path, entry in self.files.items():
            current = sha((ROOT / path).read_bytes())
            entry["sha256_after"] = current
            entry["unchanged"] = current == entry["sha256"]
            if not entry["unchanged"]:
                changed.append(path)
        if changed:
            raise Fatal(f"Source hashes changed: {changed}")
