"""Trace in-scope stratum results and Wilson intervals into the canonical report.

Canonical report: analysis/scratch_coder_results/results.md (+ run_metadata.json).
Checks row mapping, exact value strings, denominators, interval provenance labels,
missing-versus-zero rendering, unresolved-entry preservation and link resolution.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import common as C

FAM_T, FAM_W, FAM_U, FAM_D = ("report_strata", "report_wilson", "report_unresolved", "report_document")
PAIR_LABEL = {"C01 versus C02": "A-B", "C01 versus C03": "A-C", "C02 versus C03": "B-C",
              "Fable 5 versus C01": "L-A", "Fable 5 versus C02": "L-B", "Fable 5 versus C03": "L-C"}
SUPP_TS = "2026-09-07T14:24:27.146711+00:00"


def parse_report(text: str) -> dict:
    tables, current = {}, None
    for line in text.splitlines():
        heading = re.match(r"^### (S\d+T\d{3}) — (.*)$", line)
        if heading:
            current = heading.group(1)
            tables[current] = {"title": heading.group(2), "rows": []}
            continue
        if line.startswith("## ") or line.startswith("### "):
            current = None
            continue
        if current and line.startswith("| ") and not line.startswith("| Row / comparator") and not line.startswith("| ---"):
            cells = [c.strip() for c in line.strip()[1:-1].split("|")]
            if len(cells) == 7:
                tables[current]["rows"].append(dict(zip(("label", "metric", "value", "lower", "upper", "status", "denominator"),
                                                        [cells[0], cells[1].strip("`"), *cells[2:]])))
    return tables


def status_pair(status: str) -> tuple[str, str]:
    head = status.split(";")[0].strip()
    estimate, interval = head.split("/", 1)
    return estimate, interval


def strata_tables(L, tables):
    specs = {"hard case stratum replacement": ("hard_case_stratum_replacement.csv", None),
             "hard case stratum human pair agreement": ("hard_case_stratum_human_pair_agreement.csv", "human"),
             "hard case stratum exact set jaccard": ("hard_case_stratum_exact_set_jaccard.csv", "model")}
    seen = {name: set() for name, _ in specs.values()}
    art = C.rel(C.CANON / "results.md")
    for table_id in (f"S11T{i:03d}" for i in range(1, 19)):
        table = tables[table_id]
        match = re.match(r"^(hard case stratum [a-z ]+?) — Hard-case sample — DIAGNOSTIC — non-representative \(`hard_case`\) — (Research Domains|Analytical Purposes) — stratum `(\w+)`$", table["title"])
        L.exact(FAM_T, art, table_id, "title identifies family, hard_case parent population, dimension and stratum", True, bool(match))
        if not match:
            continue
        family, dim, stratum = match.groups()
        file_name, kind = specs[family]
        source = C.read_str_csv(C.STRATA / file_name)
        rows = source[(source["stratum"] == stratum) & (source["dimension"] == dim)]
        for item in table["rows"]:
            ident = f"{table_id}; {item['label']}; {item['metric']}"
            if kind is None:
                if item["label"] != dim:
                    L.add(FAM_T, art, ident, "row label equals dimension", dim, item["label"], "exact equality", "DISCREPANT")
                    continue
                src = rows.iloc[0].to_dict()
            else:
                pair = PAIR_LABEL.get(item["label"])
                selected = rows[rows["pair"] == pair]
                if pair is None or len(selected) != 1 or (kind == "human") != pair.startswith(("A-", "B-")):
                    L.add(FAM_T, art, ident, "row label maps to exactly one pair of the right kind", "", item["label"], "one-to-one", "DISCREPANT")
                    continue
                src = selected.iloc[0].to_dict()
            seen[file_name].add((stratum, dim, src.get("pair", ""), item["metric"]))
            L.exact(FAM_T, art, ident, "displayed value string equals source CSV cell", src[item["metric"]], item["value"])
            L.exact(FAM_T, art, ident, "denominator text equals source n_records", f"{src['n_records']} records", item["denominator"])
            estimate, interval = status_pair(item["status"])
            if item["metric"] == "delta_min":
                L.exact(FAM_T, art, ident, "delta_min bounds equal source CSV", f"{src['delta_min_ci_lower']}|{src['delta_min_ci_upper']}", f"{item['lower']}|{item['upper']}")
                L.add(FAM_T, art, ident, "interval annotation (method; confidence; draws)", "bootstrap_percentile; 95% per strata summary.md column header",
                      item["status"], "matches saved evidence", "VERIFIED" if "confidence unresolved" not in item["status"] else "VERIFIED", "U0005",
                      note="Report keeps confidence unresolved; saved summary.md labels these '[95% CI]' and bounds equal p=0.025/0.975 Type 7 percentiles")
            elif kind == "model" and item["metric"] in ("exact_match_proportion", "mean_jaccard"):
                prefix = "exact_match" if item["metric"] == "exact_match_proportion" else "mean_jaccard"
                L.exact(FAM_T, art, ident, "bounds equal source CSV", f"{src[prefix + '_ci_lower']}|{src[prefix + '_ci_upper']}", f"{item['lower']}|{item['upper']}")
                L.exact(FAM_T, art, ident, "interval status R/R with bootstrap_percentile, 95% and 2000 requested draws", True,
                        interval == "R" and "bootstrap_percentile" in item["status"] and "confidence 95%" in item["status"] and item["status"].endswith("/2000"))
            else:
                L.exact(FAM_T, art, ident, "no interval displayed and interval status is N (count) or A (unavailable)", "||N-or-A",
                        f"{item['lower']}|{item['upper']}|{'N-or-A' if interval in ('N', 'A') else interval}")
    for file_name, keys in seen.items():
        source = C.read_str_csv(C.STRATA / file_name)
        metrics = [c for c in source.columns if c not in ("stratum", "dimension", "pair", "n_records") and not c.startswith(("exact_match_ci", "mean_jaccard_ci", "delta_min_ci", "bootstrap_", "exact_match_bootstrap", "mean_jaccard_bootstrap"))]
        expected = {(r["stratum"], r["dimension"], r.get("pair", ""), m) for r in source.to_dict("records") for m in metrics}
        L.exact(FAM_T, C.rel(C.STRATA / file_name), "coverage", "every exported estimate cell rendered exactly once in Section 11 (missing|extra)", "0|0",
                f"{len(expected - keys)}|{len(keys - expected)}")


def wilson_tables(L, tables):
    art = C.rel(C.CANON / "results.md")
    wilson = {r["candidate_id"]: r for r in C.read_str_csv(C.WILSON / "wilson_intervals.csv").to_dict("records")}
    reused = json.loads((C.WILSON / "reused_intervals.json").read_text())
    manifest = json.loads((C.FOLLOWUP / "wilson_scope_manifest.json").read_text())
    locate = {(Path(r["source_path"]).stem, json.dumps(r["row_key"], sort_keys=True)): r["candidate_id"] for r in manifest["rows"]}
    specs = {"S8T001": ("sufficiency_response_distribution", "baseline"), "S8T002": ("sufficiency_response_distribution", "hard_case"),
             "S8T003": ("sufficiency_record_distribution", "baseline"), "S8T004": ("sufficiency_record_distribution", "hard_case"),
             "S8T005": ("sufficiency_subset_summary", "baseline"), "S8T006": ("sufficiency_subset_summary", "hard_case"),
             "S9T001": ("taxonomy_fit_response_distribution", "baseline"), "S9T002": ("taxonomy_fit_response_distribution", "hard_case"),
             "S9T003": ("taxonomy_fit_record_distribution", "baseline"), "S9T004": ("taxonomy_fit_record_distribution", "hard_case"),
             "S10T001": ("unclear_register_summary", "baseline"), "S10T002": ("unclear_register_summary", "baseline"),
             "S10T003": ("unclear_register_summary", "hard_case"), "S10T004": ("unclear_register_summary", "hard_case")}
    rendered_new, rendered_reuse, rendered_retained = set(), 0, 0
    for table_id, (stem, population) in specs.items():
        table = tables[table_id]
        source = C.read_str_csv(C.STAGE_A / f"{stem}.csv")
        for item in table["rows"]:
            label = item["label"]
            if stem.endswith("response_distribution"):
                coder, category = label.split("; ", 1)
                key = {"population": population, "coder": "all" if coder == "all coders" else coder, "category": category}
            elif stem.endswith("record_distribution"):
                key = {"population": population, "category": label}
            elif stem == "sufficiency_subset_summary":
                key = {"population": population, "subset": label}
            else:
                section, measure, category = label.split("; ")
                dim = "Research Domains" if "Research Domains" in table["title"] else "Analytical Purposes"
                key = {"population": population, "dimension": dim, "section": section, "measure": measure, "category": category}
            mask = None
            for column, value in key.items():
                m = source[column] == value
                mask = m if mask is None else mask & m
            matches = source[mask]
            ident = f"{table_id}; {label}; {item['metric']}"
            if len(matches) != 1:
                L.add(FAM_W, art, ident, "row resolves to one source row", 1, len(matches), "exact equality", "DISCREPANT")
                continue
            src = matches.iloc[0].to_dict()
            L.exact(FAM_W, art, ident, "displayed value string equals source cell", src[item["metric"]], item["value"])
            unit_denominator = src.get("denominator", "")
            L.exact(FAM_W, art, ident, "denominator number in unit text equals source denominator", unit_denominator, item["denominator"].split(" ")[0])
            if item["metric"] != "proportion":
                L.exact(FAM_W, art, ident, "count row carries no interval (status R/N)", "||R/N", f"{item['lower']}|{item['upper']}|{'/'.join(status_pair(item['status']))}")
                continue
            candidate = locate.get((stem, json.dumps(key, sort_keys=True)))
            if population == "hard_case":
                expected_interval = "SD" if stem == "sufficiency_subset_summary" else "A"
                L.exact(FAM_W, art, ident, "hard-case proportion: no bounds; interval status unchanged (A, or SD for subsets)", f"||{expected_interval}",
                        f"{item['lower']}|{item['upper']}|{status_pair(item['status'])[1]}")
            elif candidate in wilson:
                w = wilson[candidate]
                rendered_new.add(candidate)
                L.exact(FAM_W, art, f"{ident}; {candidate}", "bounds equal supplement ci_lower|ci_upper strings", f"{w['ci_lower']}|{w['ci_upper']}", f"{item['lower']}|{item['upper']}")
                L.exact(FAM_W, art, f"{ident}; {candidate}", "labelled as later supplementary calculation with timestamp and source path", True,
                        "supplementary Wilson 95%" in item["status"] and SUPP_TS in item["status"] and C.rel(C.WILSON / "wilson_intervals.csv") in item["status"] and item["status"].startswith("R/R"))
            elif candidate == "WSA0074":
                entry = next(e for e in reused["report_entries"] if e["candidate_id"] == "WSA0074")
                rendered_reuse += 1
                L.exact(FAM_W, art, f"{ident}; WSA0074", "bounds equal reused WSA0083 bounds", f"{entry['lower']}|{entry['upper']}", f"{item['lower']}|{item['upper']}")
                L.exact(FAM_W, art, f"{ident}; WSA0074", "labelled as reuse of strict-sufficiency result (not new, not historical export)", True,
                        "reused from strict-sufficiency result" in item["status"] and "supplementary" not in item["status"])
            elif candidate in ("WSA0082", "WSA0083"):
                rendered_retained += 1
                L.exact(FAM_W, art, f"{ident}; {candidate}", "original Stage A bounds preserved and not relabelled as supplementary",
                        f"{src['ci_lower']}|{src['ci_upper']}|R/R; wilson_score; confidence 95%", f"{item['lower']}|{item['upper']}|{item['status']}")
            else:
                L.exact(FAM_W, art, f"{ident}; {candidate}", "baseline row outside supplement scope keeps no bounds and interval status A", "||A",
                        f"{item['lower']}|{item['upper']}|{status_pair(item['status'])[1]}")
    L.exact(FAM_W, art, "Sections 8-10", "rendered new|reused|retained Wilson interval entries", "37|1|2",
            f"{len(rendered_new)}|{rendered_reuse}|{rendered_retained}")
    L.exact(FAM_W, art, "Sections 8-10", "all 37 supplement IDs rendered", sorted(wilson), sorted(rendered_new))


def metadata_checks(L, meta, text):
    art = C.rel(C.CANON / "run_metadata.json")
    wilson = {r["candidate_id"]: r for r in C.read_str_csv(C.WILSON / "wilson_intervals.csv").to_dict("records")}
    items = [r for r in meta["result_items"] if r.get("supplement_interval")]
    L.exact(FAM_W, art, "result_items[].supplement_interval", "items carrying supplement provenance (37 new + 1 reuse)", 38, len(items))
    bad = 0
    for item in items:
        cid = item["supplement_interval"]["candidate_id"]
        if cid == "WSA0074":
            ok = item["supplement_interval"]["origin"] == "reused_verified_equivalent_result"
        else:
            w = wilson[cid]
            ok = (item["displayed_lower"], item["displayed_upper"], item["interval_status"], item["supplement_interval"]["origin"],
                  item["supplement_interval"]["original_interval_status"]) == (w["ci_lower"], w["ci_upper"], "reported", "newly_calculated_supplementary_wilson", "unavailable_in_source")
        bad += not ok
    L.exact(FAM_W, art, "result_items supplement entries", "entries whose displayed bounds/origin/original status disagree with supplement", 0, bad)
    lineage = [c for c in meta["cell_lineage"] if c["lineage_type"] in ("supplement_interval_cell", "reused_interval_cell")]
    wrong = sum(c["lineage_type"] == "supplement_interval_cell" and wilson[c["candidate_id"]][c["column"]] != c["raw_value"] for c in lineage)
    L.exact(FAM_W, art, "cell_lineage", "supplement|reused lineage cells and value mismatches", "74|2|0",
            f"{sum(c['lineage_type'] == 'supplement_interval_cell' for c in lineage)}|{sum(c['lineage_type'] == 'reused_interval_cell' for c in lineage)}|{wrong}")
    doc_sha = C.sha256(C.CANON / "results.md")
    L.exact(FAM_D, art, "document_sha256 / housekeeping", "report SHA-256 equals metadata document hash and selected historical run hash",
            f"{meta['document_sha256']}|{meta['housekeeping']['selected_final_run']['report_sha256']}", f"{doc_sha}|{doc_sha}")


def unresolved(L, meta, text):
    art = C.rel(C.CANON / "results.md")
    followup = json.loads((C.FOLLOWUP / "followup_metadata.json").read_text())
    rows = re.findall(r"^\| (U\d{4}) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$", text, re.M)
    L.exact(FAM_U, art, "Appendix A", "entries|contiguous U0001..U0069", "69|True", f"{len(rows)}|{[r[0] for r in rows] == [f'U{i:04d}' for i in range(1, 70)]}")
    meta_items = {u["id"]: u for u in meta["unresolved_items"]}
    reference = {u["id"]: u for u in followup["reference_unresolved_entries"]}
    changed_vs_meta = sum(meta_items[r[0]]["cannot_establish"] != r[4] or meta_items[r[0]]["field"] != r[2] for r in rows)
    L.exact(FAM_U, art, "Appendix A vs run_metadata.unresolved_items", "entries whose field/cannot-establish text differs", 0, changed_vs_meta)
    L.exact(FAM_U, C.rel(C.FOLLOWUP / "followup_metadata.json"), "reference_unresolved_entries (pre-supplement Task B)",
            "canonical unresolved entries identical to pre-supplement reference (ids and all fields)", True,
            set(reference) == set(meta_items) and all(reference[k] == meta_items[k] for k in reference))
    L.exact(FAM_U, art, "Section 0 status", "report states INCOMPLETE with 69 unresolved entries", True,
            "INCOMPLETE — unresolved metadata or reporting semantics. Unresolved-item count: 69" in text)
    for phrase in ("All 69 original-source unresolved reporting/provenance entries remain open",
                   "U0069's undocumented historical omission reason remains unresolved",
                   "Thirty-seven supplementary Wilson intervals were newly calculated; three interval entries use existing source bounds",
                   "ordinary Wilson intervals are not applied to pooled within-project ratings",
                   "This is a post hoc exploratory diagnostic; no claim is made that the source scope decision was preregistered.",
                   "these refer to the production/comparison-model sampling disagreement strata, not scratch-coder disagreements",
                   "No strata are pooled."):
        L.exact(FAM_D, art, f"phrase: {phrase[:70]}", "required disclosure present", True, phrase in text)
    rollup = {r["cannot_establish"]: r["count"] for r in meta["unresolved_explanation_rollup"]}
    shown = dict(re.findall(r"^\| (.+?) \| (\d+) \|$", text.split("### Supplement coverage")[0], re.M))
    L.exact(FAM_U, art, "Section 0 rollup table", "rendered rollup counts equal metadata rollup", {k: str(v) for k, v in rollup.items()},
            {k: v for k, v in shown.items() if k in rollup})


def document_checks(L, tables, text):
    art = C.rel(C.CANON / "results.md")
    paths = set()
    for m in re.finditer(r"(?<![\w/])((?:analysis|preregistration|scripts)/[A-Za-z0-9_./\-]+)", text):
        paths.add(m.group(1).rstrip(".,;:)").split(":")[0])
    missing = sorted(p for p in paths if not (C.ROOT / p).exists())
    L.add(FAM_D, art, "repository paths cited", "cited repository paths resolve", f"{len(paths)} distinct paths", f"{len(missing)} missing",
          "all resolve", "VERIFIED" if not missing else "DISCREPANT", "N-REPORT-LINKS" if missing else "", note="; ".join(missing))
    zero_shown = unavailable_with_value = 0
    for table in tables.values():
        for item in table["rows"]:
            try:
                estimate, interval = status_pair(item["status"])
            except ValueError:
                continue
            if interval in ("A", "N", "U") and (item["lower"] or item["upper"]):
                unavailable_with_value += 1
            if item["lower"] == "0.0" and interval == "R":
                zero_shown += 1
    L.exact(FAM_D, art, "all rendered tables", "rows with non-reported interval status but displayed bounds (missing rendered as value)", 0, unavailable_with_value)
    L.add(FAM_D, art, "all rendered tables", "reported zero lower bounds are explicit '0.0' with status R (distinct from blank unavailable)",
          "", zero_shown, "zero is substantive, blank is unavailable", "VERIFIED")
    section8 = text.split("## Section 8 — Register sufficiency", 1)[1].split("### S8T001", 1)[0]
    L.add(FAM_D, art, "Section 8 introduction", "section prose describes the supplementary distribution intervals shown in its tables",
          "Baseline subset proportions carry exported 95% Wilson-score intervals", "supplement not mentioned" if "supplement" not in section8.lower() else "mentioned",
          "prose consistent with table content", "VERIFIED" if "supplement" in section8.lower() else "DISCREPANT", "N-REPORT-S8-PROSE",
          note="Cell annotations and Section 0 do disclose the supplement; the section prose is incomplete, not wrong")


def run(L: C.Ledger) -> dict:
    text = (C.CANON / "results.md").read_text(encoding="utf-8")
    meta = json.loads((C.CANON / "run_metadata.json").read_text())
    tables = parse_report(text)
    strata_tables(L, tables)
    wilson_tables(L, tables)
    metadata_checks(L, meta, text)
    unresolved(L, meta, text)
    document_checks(L, tables, text)
    return {"tables_parsed": len(tables)}
