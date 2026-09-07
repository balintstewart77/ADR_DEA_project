"""Inventory Wilson-scope candidates without calculating analytical quantities."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(__file__).resolve().parent
STAGE_A = "analysis/outputs_validation_scratch_20260824"
PROTOCOL = "preregistration/package/00_protocol/Validation_Protocol_PreReg_v1.1.docx"
METHODS = f"{STAGE_A}/methods_stage_a.md"
REFERENCE = "analysis/outputs_validation_consolidated_20260907T082625857355Z"
TASK_A = "analysis/outputs_validation_consolidated_20260907T085849219598Z"
TASK_B = "analysis/outputs_validation_consolidated_20260907T131344836676Z"
GOVERNANCE = ("preregistration/README.md", "preregistration/package/09_logs_and_templates/README.md")
FILES = {
    "qa_summary": ("population", "dimension", "measure"),
    "sufficiency_response_distribution": ("population", "coder", "category"),
    "sufficiency_record_distribution": ("population", "category"),
    "sufficiency_subset_summary": ("population", "subset"),
    "taxonomy_fit_response_distribution": ("population", "coder", "category"),
    "taxonomy_fit_record_distribution": ("population", "category"),
    "taxonomy_issue_summary": ("population", "issue"),
    "unclear_register_summary": ("population", "dimension", "section", "measure", "category"),
    "taxonomy_coherence_summary": ("population", "analysis", "category"),
}
ALLOWED_DECISIONS = {
    "candidate_for_later_authorised_wilson", "already_exported", "methodological_decision_required",
    "no_inferential_interval_proposed", "excluded_nonbaseline", "source_counts_unavailable",
    "zero_denominator", "invalid_source_counts",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return {"command": ["git", *args], "exit_code": p.returncode, "stdout": p.stdout.rstrip("\n"), "stderr": p.stderr.rstrip("\n")}


def cell(path, key, column, value):
    return {"source_path": path, "row_key": key, "column": column, "raw_value": value}


def read_csv(path, hashes):
    data=(ROOT/path).read_bytes(); hashes[path]={"sha256_before":sha(data),"bytes":len(data)}
    rows=list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    if not rows: raise ValueError(f"Empty required CSV: {path}")
    return rows


def classify(name, row):
    if name == "qa_summary":
        measure=row["measure"]
        if measure in ("records", "expected_responses", "rows_in_raw_export"):
            return "structural_ratio", "fixed design/accounting total", False, "qa_design_accounting"
        if measure.endswith("_responses"):
            return "pooled_coder_responses", "coder response nested within sampled project", True, "qa_response_status"
        return "record_binary", "sampled project/record", False, "qa_record_status"
    if name in ("sufficiency_response_distribution", "taxonomy_fit_response_distribution"):
        if row["coder"] == "all":
            return "pooled_coder_responses", "coder response nested within sampled project", True, "pooled_all_coder_distribution"
        return "individual_coder_binary", f"sampled project rated by {row['coder']}", False, "named_coder_distribution"
    if name in ("sufficiency_record_distribution", "taxonomy_fit_record_distribution", "sufficiency_subset_summary"):
        return "record_binary", "sampled project/record", False, "record_majority_or_subset"
    if name == "taxonomy_issue_summary":
        return "pooled_coder_responses", "conditional coder response (Partial Fit or No Fit) nested within sampled project", True, "conditional_taxonomy_issue_response"
    if name == "unclear_register_summary":
        if row["section"] == "frequency" and row["measure"].startswith("records_"):
            return "record_binary", "sampled project/record", False, "unclear_record_frequency"
        return "pooled_coder_responses", "coder response nested within sampled project, possibly conditional on another response", True, "unclear_response_frequency_or_crosstab"
    if name == "taxonomy_coherence_summary":
        return "pooled_coder_responses", "conditional Cannot-assess coder response nested within sampled project", True, "conditional_coherence_response"
    return "other_or_unclear", "unresolved", None, "other_or_unclear"


def decision(item):
    if item["count_validation"] == "invalid_source_counts":
        return "invalid_source_counts", "Exported count or denominator is invalid; no repair or interval is proposed."
    if item["count_validation"] == "zero_denominator":
        return "zero_denominator", "The exported denominator is zero; no numerical interval is proposed."
    if item["population"] != "baseline":
        return "excluded_nonbaseline", "The proposed supplement is baseline-only. The source population and any existing interval status are retained."
    if item["existing_interval"]["status"] == "reported" or item["equivalent_existing_interval"] is not None:
        return "already_exported", "A Wilson interval for the same source result is already exported directly or through a verified equivalent; no duplicate or overwrite is proposed."
    unit=item["observational_unit_class"]
    if unit == "structural_ratio":
        return "no_inferential_interval_proposed", "This is a design/accounting ratio rather than a project event-frequency estimand with a clear inferential basis."
    if unit == "pooled_coder_responses":
        return "methodological_decision_required", "The row pools repeated ratings from sampled projects. An ordinary binomial Wilson interval does not account for within-project dependence; §8.9 and the saved methods do not resolve how the pooled row should be treated."
    if unit in ("record_binary", "individual_coder_binary"):
        return "candidate_for_later_authorised_wilson", "The baseline row has an exported integer event count and a positive record-based denominator. Its observational unit matches a project or one named coder's one-rating-per-project series; §8.9 supplies the 95% Wilson basis, subject to a later authorised implementation."
    return "methodological_decision_required", "The observational unit or protocol scope is not sufficiently established for an ordinary Wilson interval."


def inventory(hashes):
    tables={name:read_csv(f"{STAGE_A}/{name}.csv",hashes) for name in FILES}
    indexes={}
    for name,rows in tables.items():
        idx={}
        for row in rows:
            key=tuple(row[k] for k in FILES[name])
            if key in idx: raise ValueError(f"Duplicate source row key: {name}: {key}")
            idx[key]=row
        indexes[name]=idx
    strict=indexes["sufficiency_subset_summary"].get(("baseline","strict_register_sufficient"))
    sufficient=indexes["sufficiency_record_distribution"].get(("baseline","Sufficient"))
    if strict is None or sufficient is None or any(strict[c]!=sufficient[c] for c in ("count","denominator","proportion")):
        raise ValueError("Strict-sufficiency/result-majority equivalence cannot be established from exact exported cells")
    manifest=[]
    for name in FILES:
        path=f"{STAGE_A}/{name}.csv"
        rows=tables[name]
        for row in rows:
            key={k:row[k] for k in FILES[name]}
            numerator_col="count" if "count" in row else None
            denominator_col="applicable_denominator" if "applicable_denominator" in row else "denominator" if "denominator" in row else None
            numerator=row.get(numerator_col,"") if numerator_col else ""
            denominator=row.get(denominator_col,"") if denominator_col else ""
            validation="valid_integer_counts"
            try:
                k,n=int(numerator),int(denominator)
                if k<0 or n<0 or k>n: validation="invalid_source_counts"
                elif n==0: validation="zero_denominator"
            except (ValueError,TypeError):
                validation="source_counts_unavailable"
            unit,sampling,pooled,family=classify(name,row)
            existing={"status":"not_exported","method":None,"lower":None,"upper":None,"lineage":[]}
            if "ci_lower" in row:
                existing={"status":"reported" if row["ci_lower"]!="" and row["ci_upper"]!="" else "source_status_without_endpoints",
                          "method":row["ci_method"],"lower":row["ci_lower"],"upper":row["ci_upper"],
                          "lineage":[cell(path,key,c,row[c]) for c in ("ci_method","ci_lower","ci_upper")]}
            equivalent=None
            if name=="sufficiency_record_distribution" and key=={"population":"baseline","category":"Sufficient"}:
                ekey={"population":"baseline","subset":"strict_register_sufficient"}
                equivalent={"source_path":f"{STAGE_A}/sufficiency_subset_summary.csv","row_key":ekey,
                            "identity_evidence":"Exact exported count, denominator and proportion strings match; saved methods define both as at least two Sufficient ratings.",
                            "method":strict["ci_method"],"lower":strict["ci_lower"],"upper":strict["ci_upper"],
                            "lineage":[cell(f"{STAGE_A}/sufficiency_subset_summary.csv",ekey,c,strict[c]) for c in ("count","denominator","proportion","ci_method","ci_lower","ci_upper")]}
            item={"candidate_id":f"WSA{len(manifest)+1:04d}","source_path":path,"source_sha256":hashes[path]["sha256_before"],
                  "row_key":key,"metric_name":"proportion","metric_family":family,"population":row["population"],
                  "source_numerator":numerator,"source_denominator":denominator,"source_proportion":row["proportion"],
                  "numerator_lineage":cell(path,key,numerator_col,numerator) if numerator_col else None,
                  "denominator_lineage":cell(path,key,denominator_col,denominator) if denominator_col else None,
                  "proportion_lineage":cell(path,key,"proportion",row["proportion"]),
                  "source_unit":row.get("unit"),"source_unit_lineage":cell(path,key,"unit",row["unit"]) if "unit" in row else None,
                  "count_validation":validation,"observational_unit_class":unit,"sampling_unit":sampling,
                  "pooled_repeated_within_project":pooled,
                  "weighting_or_dependence":"Equal-weighted source response rows are evidently clustered by project; independence is not demonstrated by the summary CSV." if pooled else "One source event indicator per stated project-level unit; independence is not empirically demonstrated by the summary CSV.",
                  "existing_interval":existing,"equivalent_existing_interval":equivalent,
                  "protocol_scope_evidence":{"section":"8.9","paragraph_index":167,"wording":"Baseline proportions will use 95% Wilson score intervals.","applicability_assessment":"Requires row-level observational-unit assessment; the clause alone does not establish an ordinary binomial model for pooled responses."}}
            if validation=="source_counts_unavailable":
                item["scope_decision"]="source_counts_unavailable"; item["scope_reason"]="Required integer source count or denominator is unavailable; none is inferred from the proportion."
            else:
                item["scope_decision"],item["scope_reason"]=decision(item)
            manifest.append(item)
    return manifest,tables


def protocol_evidence(hashes):
    data=(ROOT/PROTOCOL).read_bytes();hashes[PROTOCOL]={"sha256_before":sha(data),"bytes":len(data)}
    root=ET.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"));ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs=["".join(t.text or "" for t in p.iter(ns+"t")).strip() for p in root.iter(ns+"p")]
    required={52:"Random baseline is a simple random sample of 150 records and is the primary agreement/sufficiency population.",
              146:"Register sufficiency specifies individual coder-rating distributions, record-majority ratings, and broad/strict subsets.",
              147:"Taxonomy fit specifies individual and record-majority distributions and conditions taxonomy-issue frequencies on Partial Fit or No Fit responses.",
              148:"Record-majority diagnostic ratings require at least two coders to choose the same category; splits remain separate.",
              149:"Unclear reporting includes coder-specific use, majority use, and coherence with sufficiency/confidence.",
              166:"Section heading: 8.9 Uncertainty intervals.",
              167:"The protocol explicitly prescribes 95% Wilson score intervals for baseline proportions and record bootstrap percentile intervals for agreement families."}
    return [{"path":PROTOCOL,"sha256":hashes[PROTOCOL]["sha256_before"],"paragraph_index":i,"paraphrase":note,"recorded_text":paragraphs[i]} for i,note in required.items()]


def markdown(manifest,evidence,hashes):
    decisions=Counter(x["scope_decision"] for x in manifest); units=Counter(x["observational_unit_class"] for x in manifest)
    grouped=defaultdict(Counter)
    for x in manifest: grouped[(x["source_path"],x["metric_family"],x["observational_unit_class"])][x["scope_decision"]]+=1
    lines=["# Wilson scope assessment — no intervals calculated","",
           "This is a row-level eligibility assessment for a possible later supplement. It does not calculate Wilson endpoints, replace existing intervals, create an analytical source, or close a consolidation unresolved entry.","",
           "## Evidence and scope","",
           f"The frozen protocol (`{PROTOCOL}`, SHA-256 `{hashes[PROTOCOL]['sha256_before']}`) states in §8.9, paragraph index 167: “Baseline proportions will use 95% Wilson score intervals.” Adjacent §§5.2 and 8.5 identify the 150-record random baseline, individual-coder distributions, record-majority rules, sufficiency subsets, conditional taxonomy-issue response frequencies and Unclear-use summaries.","",
           f"The saved Stage A methods (`{METHODS}`, SHA-256 `{hashes[METHODS]['sha256_before']}`) also document 95% Wilson intervals for baseline proportions, the broad/strict definitions, two-of-three record-majority rule, and Partial Fit/No Fit taxonomy-issue denominator. The CSVs export integer counts, denominators and proportions for all inventoried rows; only baseline `sufficiency_subset_summary.csv` rows contain Wilson endpoints. Other interval semantics remain absent from those schemas.","",
           "The broad protocol wording does not by itself establish that 450 pooled coder responses are independent binomial trials. Those rows contain three ratings per sampled project and are marked `methodological_decision_required`. Named-coder rows contain one rating per project for the named coder. Record-majority and subset rows contain one binary event indicator per project. QA design totals are separated from observed events.","",
           "No empirical independence claim is made from the summaries. No count is reconstructed, no category is summed, and no source proportion is verified or recalculated from its count and denominator.","",
           "## Inventory totals","",
           f"Inventoried rows: {len(manifest)}. Scope decisions: "+", ".join(f"`{k}` {v}" for k,v in sorted(decisions.items()))+". Observational units: "+", ".join(f"`{k}` {v}" for k,v in sorted(units.items()))+".","",
           "| Source / metric family | Unit class | Candidate later | Already exported | Decision required | Nonbaseline excluded | No inferential interval | Other exclusions |","| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for (path,family,unit),c in sorted(grouped.items()):
        other=sum(v for k,v in c.items() if k not in ("candidate_for_later_authorised_wilson","already_exported","methodological_decision_required","excluded_nonbaseline","no_inferential_interval_proposed"))
        lines.append(f"| `{path}` / `{family}` | `{unit}` | {c['candidate_for_later_authorised_wilson']} | {c['already_exported']} | {c['methodological_decision_required']} | {c['excluded_nonbaseline']} | {c['no_inferential_interval_proposed']} | {other} |")
    lines += ["","## Existing interval and duplicate-result inventory","",
              "The two baseline broad/strict sufficiency-subset rows already export `Wilson score 95%` endpoints and are marked `already_exported`. The baseline record-majority `Sufficient` row has exactly matching exported count, denominator and proportion strings and the same saved-method definition as `strict_register_sufficient`; it links to that existing interval rather than proposing a duplicate. Hard-case subset rows retain the source `not applied (diagnostic sample)` status and remain excluded as nonbaseline. No other inventoried row exports interval columns.","",
              "## Decisions needed before any later computation","",
              "A later instruction must decide whether the protocol's broad phrase covers QA event frequencies and each named-coder and record-level distribution family as assessed here. It must explicitly decide how to handle pooled all-coder and conditional-response rows; ordinary Wilson treats trials as binomial observations and does not account for three ratings clustered within a project. This assessment neither extends the prescription to pooled rows nor substitutes a clustered or bootstrap method.","",
              "If later authorised for eligible rows, implementation checks must specify two-sided 95% Wilson score intervals without continuity correction where justified; record the implementation and version; enforce integer 0 ≤ k ≤ n with n > 0; compare the implementation's centre against k/n under a tolerance chosen only after inspecting that implementation; preserve source precision and provenance; and explicitly handle any floating-point boundary correction. No tolerance is selected here.","",
              "## Governance","",
              "The repository governance states that post-registration changes require a new version and that substantive changes also require an amendment under `preregistration/post_registration/amendments/`. It does not establish whether this proposed supplementary presentation is substantive or require a deviation-log entry for it. The documentation route and substantive-status decision therefore remain to be settled; no governance file is changed here.","",
              "The complete row-level source keys, raw cells, lineage, unit classifications, decisions, reasons, existing endpoints and equivalence link are in `wilson_scope_manifest.json`.",""]
    return "\n".join(lines)


def remedy_map(unresolved,manifest):
    by_source=defaultdict(list)
    for x in manifest: by_source[x["source_path"]].append(x)
    uid_sources={
        "U0020":("qa_summary","overall"),"U0023":("qa_summary","baseline"),"U0024":("qa_summary","hard_case"),
        "U0035":("sufficiency_response_distribution","baseline"),"U0036":("sufficiency_response_distribution","hard_case"),
        "U0037":("sufficiency_record_distribution","baseline"),"U0038":("sufficiency_record_distribution","hard_case"),
        "U0039":("taxonomy_fit_response_distribution","baseline"),"U0040":("taxonomy_fit_response_distribution","hard_case"),
        "U0041":("taxonomy_fit_record_distribution","baseline"),"U0042":("taxonomy_fit_record_distribution","hard_case"),
        "U0043":("taxonomy_issue_summary","baseline"),"U0044":("taxonomy_issue_summary","hard_case"),
        "U0045":("unclear_register_summary","baseline"),"U0046":("unclear_register_summary","hard_case"),
        "U0047":("taxonomy_coherence_summary","baseline"),"U0048":("taxonomy_coherence_summary","hard_case"),
    }
    original={x["id"]:x for x in unresolved}; result=[]
    for uid,(name,pop) in uid_sources.items():
        rows=[x for x in by_source[f"{STAGE_A}/{name}.csv"] if x["population"]==pop]
        result.append({"unresolved_id":uid,"canonical_entry":original[uid],"affected_candidate_ids":[x["candidate_id"] for x in rows],
                       "decision_counts":dict(Counter(x["scope_decision"] for x in rows)),
                       "later_supplement_could_address":"Missing interval presentation for rows marked candidate_for_later_authorised_wilson; an already-exported equivalent can be linked without recomputation." if pop=="baseline" else "No rows: the proposed supplement is baseline-only.",
                       "would_remain":"Original omission reason/source status remains unavailable; pooled/ambiguous, structural and nonbaseline rows remain outside calculation unless separately resolved. The item is not automatically closed."})
    u69rows=[x for x in manifest if x["source_path"]!=f"{STAGE_A}/qa_summary.csv" and x["population"]=="baseline"]
    result.append({"unresolved_id":"U0069","canonical_entry":original["U0069"],"affected_candidate_ids":[x["candidate_id"] for x in u69rows],
                   "decision_counts":dict(Counter(x["scope_decision"] for x in u69rows)),
                   "later_supplement_could_address":"Supply new, explicitly supplemental intervals for eligible rows after the methodological choices and a separate calculation authorisation; link the existing strict-sufficiency equivalent.",
                   "would_remain":"The undocumented historical reason the original distribution intervals were omitted would remain unavailable. Pooled-response decisions and any excluded rows are not remedied by eligible-row intervals, so no future unresolved count is predicted."})
    return result


def compare_runs():
    def load(directory):
        p=ROOT/directory
        return json.loads((p/"run_metadata.json").read_text()),(p/"consolidated_results.md").read_text()
    ref,rm=load(REFERENCE); a,am=load(TASK_A); b,bm=load(TASK_B)
    if ref["generator"]["git_head"]!="732bf6668d9e9d702f0eb798fee5d46a16eb8a1e" or len(ref["unresolved_items"])!=69:
        raise ValueError("Reference identity or canonical unresolved count mismatch")
    def normalise_pair(x,y,paths):
        x=json.loads(json.dumps(x));y=json.loads(json.dumps(y));ignored=[]
        for path in paths:
            u,v=x,y
            for k in path[:-1]:u=u[k];v=v[k]
            ignored.append({"key":"/".join(path),"old":u[path[-1]],"new":v[path[-1]]});u[path[-1]]=v[path[-1]]="<ALLOWED>"
        return x,y,ignored
    volatile=[("generation_timestamp_utc",),("output_directory",),("document_sha256",),("generator","git_head"),("generator","git_status_before"),("generator","git_status_after_validation")]
    x,y,aignored=normalise_pair(ref,a,volatile)
    if x!=y: raise ValueError("Task A metadata differs outside explicit allowlist")
    def line(meta):return f"Generation time (UTC): `{meta['generation_timestamp_utc']}`. Generator HEAD: `{meta['generator']['git_head']}`. Generator working-tree state: {'dirty' if meta['generator']['git_status_before'] else 'clean'}. These describe the generator, not the source runs."
    if rm.replace(line(ref),"<RUN>")!=am.replace(line(a),"<RUN>"):raise ValueError("Task A Markdown differs outside named run line")
    bpaths=volatile+[("generator","source_hashes","analysis/scratch_coder_consolidated/report.py"),("generator","source_hashes","analysis/scratch_coder_consolidated/test_collation.py")]
    x,y,bignored=normalise_pair(a,b,bpaths);roll=y.pop("unresolved_explanation_rollup")
    if x!=y:raise ValueError("Task B metadata differs outside explicit allowlist")
    if am[am.index("## Section 1 —"):]!=bm[bm.index("## Section 1 —"):]:raise ValueError("Task B changed Sections 1–11 or appendices")
    if a["unresolved_items"]!=b["unresolved_items"] or len(b["unresolved_items"])!=69:raise ValueError("Task B changed canonical unresolved entries")
    expected=defaultdict(list)
    for u in b["unresolved_items"]:expected[u["cannot_establish"]].append(u["id"])
    if {r["cannot_establish"]:r["member_ids"] for r in roll}!=dict(expected):raise ValueError("Task B rollup differs from canonical entries")
    return {"reference":{"path":REFERENCE,"reported_head":ref["generator"]["git_head"],"unresolved_count":len(ref["unresolved_items"])},
            "task_a":{"path":TASK_A,"commit":a["generator"]["git_head"],"result":"equivalent outside generator-run allowlist","ignored_fields":aignored,"lineage_identical":ref["cell_lineage"]==a["cell_lineage"],"source_files_identical":ref["source_files"]==a["source_files"]},
            "task_b":{"path":TASK_B,"commit":b["generator"]["git_head"],"result":"bounded change only","ignored_metadata_fields":bignored,"added_metadata_key":"unresolved_explanation_rollup","sections_1_11_and_appendices_identical":True,"canonical_unresolved_identical":True,"rollup":roll}}


def main():
    if not sys.dont_write_bytecode:
        raise SystemExit("Run with -B to keep caches disabled")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out=ROOT/"analysis"/f"outputs_validation_consolidation_followup_{stamp}"
    out.mkdir(exist_ok=False)
    hashes={}
    evidence=protocol_evidence(hashes)
    methods=(ROOT/METHODS).read_bytes();hashes[METHODS]={"sha256_before":sha(methods),"bytes":len(methods)}
    manifest,_=inventory(hashes)
    comparisons=compare_runs()
    refmeta=json.loads((ROOT/REFERENCE/"run_metadata.json").read_text())
    taskbmeta=json.loads((ROOT/TASK_B/"run_metadata.json").read_text())
    for path in (f"{REFERENCE}/consolidated_results.md",f"{REFERENCE}/run_metadata.json",f"{TASK_A}/consolidated_results.md",f"{TASK_A}/run_metadata.json",f"{TASK_B}/consolidated_results.md",f"{TASK_B}/run_metadata.json",*GOVERNANCE):
        data=(ROOT/path).read_bytes();hashes.setdefault(path,{"sha256_before":sha(data),"bytes":len(data)})
    overlap={}
    for path,recorded in refmeta["source_files"].items():
        current=sha((ROOT/path).read_bytes())
        overlap[path]={"task_a_reference_sha256":recorded["sha256"],"current_sha256":current,"matches":current==recorded["sha256"]}
    if not all(x["matches"] for x in overlap.values()):raise ValueError("An immutable source no longer matches the Task A/reference hash")
    remedies=remedy_map(refmeta["unresolved_items"],manifest)
    counts=Counter(x["scope_decision"] for x in manifest)
    if len(manifest)!=len({x["candidate_id"] for x in manifest}):raise ValueError("Duplicate inventory candidate ID")
    if any(x["scope_decision"] not in ALLOWED_DECISIONS for x in manifest):raise ValueError("Unknown scope decision")
    prohibited_units=("pooled_coder_responses","structural_ratio","other_or_unclear")
    if any(x["scope_decision"]=="candidate_for_later_authorised_wilson" and (x["population"]!="baseline" or x["observational_unit_class"] in prohibited_units or x["count_validation"]!="valid_integer_counts") for x in manifest):raise ValueError("Ineligible row marked candidate")
    if any(x["existing_interval"]["status"]=="reported" and x["scope_decision"]!="already_exported" for x in manifest):raise ValueError("Existing interval not preserved")
    if sum(counts.values())!=len(manifest):raise ValueError("Assessment decision totals do not match row manifest")
    for path,expected in taskbmeta["generator"]["source_hashes"].items():
        if sha((ROOT/path).read_bytes())!=expected:raise ValueError(f"Task B generator byte mismatch: {path}")
    scope={"schema_version":"1.0","assessment":"No intervals calculated","generated_at_utc":datetime.now(timezone.utc).isoformat(),
           "protocol_evidence":evidence,"saved_methods":{"path":METHODS,"sha256":hashes[METHODS]["sha256_before"],"documented":"Baseline proportions use the repository Wilson-score implementation at 95%; project-level broad/strict and majority definitions are stated."},
           "totals":{"inventoried":len(manifest),"decisions":dict(sorted(counts.items())),"observational_units":dict(sorted(Counter(x["observational_unit_class"] for x in manifest).items()))},
           "join_checks":[{"left_source":f"{STAGE_A}/sufficiency_record_distribution.csv","left_key":{"population":"baseline","category":"Sufficient"},
                           "right_source":f"{STAGE_A}/sufficiency_subset_summary.csv","right_key":{"population":"baseline","subset":"strict_register_sufficient"},
                           "cardinality":"one_to_one","matched_rows":1,"unmatched_rows":0,"comparison_columns":["count","denominator","proportion"],"exact_source_strings_equal":True,
                           "semantic_basis":"Saved methods define record-majority Sufficient and strict_register_sufficient as at least two Sufficient ratings."}],
           "later_implementation_checks":["two-sided 95% Wilson score without continuity correction where justified","documented implementation and version","0 <= k <= n with n > 0","numerical-tolerance checks against k/n after inspecting the implementation; no tolerance chosen here","source precision and provenance preserved","explicit floating-point boundary correction handling"],
           "rows":manifest}
    report=markdown(manifest,evidence,hashes)
    command_log=[
      {"command":"git status --porcelain=v1 --untracked-files=all; git diff --stat; git diff --cached --stat; git rev-parse --verify HEAD","cwd":str(ROOT),"exit_code":0,"result":"Initial index empty; only generator/reference paths untracked; HEAD 732bf6668d9e9d702f0eb798fee5d46a16eb8a1e."},
      {"command":"git add analysis/scratch_coder_consolidated/README.md analysis/scratch_coder_consolidated/__init__.py analysis/scratch_coder_consolidated/__main__.py analysis/scratch_coder_consolidated/generate.py analysis/scratch_coder_consolidated/preflight.py analysis/scratch_coder_consolidated/report.py analysis/scratch_coder_consolidated/schemas.json analysis/scratch_coder_consolidated/test_collation.py","cwd":str(ROOT),"exit_code":0,"result":"Exact Task A allowlist staged after sandbox approval."},
      {"command":"git commit -m \"Commit consolidation generator for reproducibility check\"","cwd":str(ROOT),"exit_code":0,"result":"Created 808e5993cd41893a57896b35b12d9c498c16931f; commit hooks passed."},
      {"command":".venv/bin/python -B -m analysis.scratch_coder_consolidated","cwd":str(ROOT),"exit_code":0,"result":TASK_A},
      {"command":".venv/bin/python -B -m unittest analysis.scratch_coder_consolidated.test_collation","cwd":str(ROOT),"exit_code":0,"result":"Task B precommit: 9 tests passed."},
      {"command":"git add analysis/scratch_coder_consolidated/report.py analysis/scratch_coder_consolidated/test_collation.py","cwd":str(ROOT),"exit_code":0,"result":"Exact Task B allowlist staged after sandbox approval."},
      {"command":"git commit -m \"Add unresolved-entry explanation rollup to consolidation provenance\"","cwd":str(ROOT),"exit_code":0,"result":"Created a69ac7289b662675d71c3afa95bab02217f7800c; commit hooks passed."},
      {"command":".venv/bin/python -B -m analysis.scratch_coder_consolidated","cwd":str(ROOT),"exit_code":0,"result":TASK_B},
      {"command":".venv/bin/python -B -m unittest analysis.scratch_coder_consolidation_followup.test_assessment analysis.scratch_coder_consolidated.test_collation","cwd":str(ROOT),"exit_code":0,"result":"12 tests passed before the assessment-helper commit."},
      {"command":"git add analysis/scratch_coder_consolidation_followup/__init__.py analysis/scratch_coder_consolidation_followup/__main__.py analysis/scratch_coder_consolidation_followup/assessment.py analysis/scratch_coder_consolidation_followup/test_assessment.py","cwd":str(ROOT),"exit_code":0,"result":"Exact Task C helper allowlist staged after sandbox approval."},
      {"command":"git commit -m \"Add Wilson scope assessment helper\"","cwd":str(ROOT),"exit_code":0,"result":"Assessment-helper commit is recorded in task_commits.assessment_helper; commit hooks passed."},
      {"command":".venv/bin/python -B -m analysis.scratch_coder_consolidation_followup","cwd":str(ROOT),"exit_code":0,"result":str(out.relative_to(ROOT))},
    ]
    (out/"wilson_scope_manifest.json").write_text(json.dumps(scope,indent=2,ensure_ascii=False)+"\n")
    (out/"wilson_scope_assessment.md").write_text(report)
    (out/"command_log.json").write_text(json.dumps(command_log,indent=2,ensure_ascii=False)+"\n")
    (out/"followup_metadata.json").write_text("{}\n")
    status_after=git("status","--porcelain=v1","--untracked-files=all")
    code_check=git("diff","--exit-code","HEAD","--","analysis/scratch_coder_consolidated","analysis/scratch_coder_consolidation_followup")
    head=git("rev-parse","HEAD")
    for path,entry in hashes.items():
        now=sha((ROOT/path).read_bytes());entry["sha256_after"]=now;entry["unchanged"]=now==entry["sha256_before"]
    if not all(x["unchanged"] for x in hashes.values()):raise ValueError("A read immutable input changed during assessment")
    deliverables={p.name:{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in out.iterdir() if p.name!="followup_metadata.json"}
    metadata={"status":"complete_scope_assessment_no_intervals_calculated","generated_at_utc":scope["generated_at_utc"],
              "task_commits":{"task_a":"808e5993cd41893a57896b35b12d9c498c16931f","task_b":"a69ac7289b662675d71c3afa95bab02217f7800c","assessment_helper":head["stdout"]},
              "invocation":[sys.executable,"-B","-m","analysis.scratch_coder_consolidation_followup"],
              "external_versions":{"python":sys.version,"task_a_generator_PyYAML":"6.0.3","assessment_helper":"standard library only"},
              "comparisons":comparisons,"reference_unresolved_count":69,"reference_unresolved_entries":refmeta["unresolved_items"],
              "unresolved_remedy_mapping":remedies,"assessment_totals":scope["totals"],"immutable_inputs_read":hashes,
              "task_a_overlapping_sources":overlap,"relevant_code":{"generator_task_b_recorded_hashes":taskbmeta["generator"]["source_hashes"],
                  "git_diff_against_head_exit_code":code_check["exit_code"],"helper_files":{p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(PACKAGE.glob("*.py"))}},
              "repository_state":{"actual_status_after_task_b_run":taskbmeta["generator"]["git_status_after_validation"],"actual_status_after_followup_artifacts_created":status_after["stdout"],"head_at_assessment":head["stdout"]},
              "output_artifacts":{"directory":out.relative_to(ROOT).as_posix(),"files":deliverables,"note":"Output paths are recorded separately from Git status, including when untracked/ignored."},
              "governance_assessment":{"evidence_paths":list(GOVERNANCE),"finding":"Post-registration changes require a new version; substantive changes also require an amendment. Whether this supplement is substantive and whether a deviation-log entry is appropriate are not established and remain documentation decisions."},
              "boundaries":{"wilson_endpoints_computed":False,"analytical_proportions_computed":False,"bootstrap_files_read":False,"restricted_paths_read":False,"unresolved_entries_closed":False}}
    (out/"followup_metadata.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n")
    # Parse/read back every completed artifact.
    json.loads((out/"wilson_scope_manifest.json").read_text());json.loads((out/"command_log.json").read_text());json.loads((out/"followup_metadata.json").read_text())
    if (out/"wilson_scope_assessment.md").read_text()!=report:raise ValueError("Assessment read-back mismatch")
    print(json.dumps({"output_directory":str(out),"inventoried":len(manifest),"decisions":dict(sorted(counts.items())),"commit":head["stdout"]},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
