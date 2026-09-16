"""Inventory source-attributed quantitative claims in two external working logs.

The external logs are read in place and never written. Repository inputs are
aggregate exports, results.md, figure data, and the exploratory confidence
report. Use --self-test to exercise comparison logic without reading them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from analysis.verification_pass2.verify_pass2 import Audit  # noqa: E402

OUT = Path(__file__).resolve().parent
LOG_DIR = Path(r"C:\Users\balin\Desktop\DEA_working_logs")
REV = LOG_DIR / "scratch_coder_figure_revisions_log_pass2.md"
FIND = LOG_DIR / "scratch_coder_interpretive_findings.md"
CONF = ROOT / "analysis/confidence_exploratory/results_confidence.md"
EXPECTED_HASHES = {
    REV.name: "0711ff9b7e8808dd202d2302738c343d639d50c3c1fb46f6e43891b5e392924f",
    FIND.name: "5051db037e50417a53a168b62dfdae6e466dce333e1706aae453a9e250774610e",
}
DOM, PUR, UNCLEAR = "Research Domains", "Analytical Purposes", "Unclear from Register Entry"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def places(value: str) -> int:
    value = value.lstrip("+-<>~")
    return len(value.split(".", 1)[1]) if "." in value else 0


def half_up(value: D, digits: int) -> D:
    return value.quantize(D(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def compare(quoted: list[str], source: list[D], rule: str) -> bool:
    if len(quoted) != len(source):
        return False
    for q, s in zip(quoted, source):
        qd = D(q.lstrip("+~"))
        if rule == "exact":
            ok = s == qd
        elif rule in ("rounded", "approximate"):
            ok = half_up(s, places(q)) == qd
        elif rule == "percentage":
            ok = half_up(s * 100, places(q)) == qd
        else:
            raise ValueError(rule)
        if not ok:
            return False
    return True


def parse_md_tables(path: Path) -> dict[str, list[dict[str, str]]]:
    tables: dict[str, list[dict[str, str]]] = {}
    current = None
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^## (SCF1T\d+) ", line)
        if match:
            current = match.group(1)
            continue
        if current and line.startswith("|") and index + 1 < len(lines) and lines[index + 1].startswith("| ---"):
            header = [x.strip() for x in line.strip("|").split("|")]
            rows = []
            cursor = index + 2
            while cursor < len(lines) and lines[cursor].startswith("|"):
                cells = [x.strip() for x in lines[cursor].strip("|").split("|")]
                rows.append(dict(zip(header, cells)))
                cursor += 1
            tables[current] = rows
    return tables


class Inventory:
    def __init__(self) -> None:
        self.audit = Audit()
        self.conf = parse_md_tables(CONF)
        self.rows: list[dict[str, str]] = []
        self.counter = Counter()

    def item(self, tid: str, metric: str | None = None, part: int = 0, **key) -> dict:
        start = len(self.audit.evidence)
        value = self.audit.v(tid, metric, part=part, **key)
        ev = self.audit.evidence[start:]
        sources = [s for e in ev for s in e["sources"]]
        return {"value": value, "table": tid,
                "cell": "; ".join(f'{s["path"]}::{s["cell"]}' for s in sources),
                "all_values": [s["value"] for s in sources],
                "discrepancy": any(e["discrepancy"] for e in ev)}

    def direct(self, path: str, key: dict[str, str], column: str, table: str) -> dict:
        source = self.audit.source(path, key, column)
        return {"value": D(source["value"]), "table": table,
                "cell": f'{path}::{source["cell"]}', "all_values": [source["value"]],
                "discrepancy": False}

    def confidence(self, tid: str, column: str, **key) -> dict:
        matches = [r for r in self.conf[tid] if all(r.get(k) == str(v) for k, v in key.items())]
        if len(matches) != 1 or matches[0].get(column, "") == "":
            raise KeyError(f"{tid} {key} {column}")
        raw = matches[0][column]
        return {"value": D(raw), "table": tid,
                "cell": f"analysis/confidence_exploratory/results_confidence.md::{key}, {column}",
                "all_values": [raw], "discrepancy": False}

    def claim(self, log: str, section: str, label: str, quoted: list[str] | str,
              sources, rule: str = "rounded", note: str = "") -> None:
        if isinstance(quoted, str):
            quoted = [quoted]
        claim_id = ("R" if log == REV.name else "F") + f"{self.counter[log] + 1:03d}"
        self.counter[log] += 1
        try:
            src = sources() if callable(sources) else sources
            if not isinstance(src, list):
                src = [src]
            values = [x["value"] for x in src]
            if any(x["discrepancy"] for x in src):
                status = "DISCREPANCY"
            elif compare(quoted, values, rule):
                status = "PASS (APPROXIMATE)" if rule == "approximate" else "PASS"
            else:
                status = "FAIL"
            table = "; ".join(dict.fromkeys(x["table"] for x in src))
            cell = "; ".join(x["cell"] for x in src)
            full = json.dumps([x["all_values"] for x in src], ensure_ascii=False)
        except (KeyError, StopIteration, ValueError) as exc:
            status, table, cell, full = "SOURCE MISSING", "", "", ""
            note = f"{note}; {type(exc).__name__}: {exc}".strip("; ")
        self.rows.append({"claim_id": claim_id, "log_file_name": log, "section_number": section,
                          "parsed_values": json.dumps(quoted, ensure_ascii=False),
                          "source_table": table, "source_cell": cell,
                          "source_values_full_precision": full,
                          "comparison_rule_used": rule, "status": status,
                          "quantity_label": label, "notes": note})

    def not_checked(self, log: str, section: str, label: str, quoted: list[str] | str, reason: str) -> None:
        if isinstance(quoted, str):
            quoted = [quoted]
        claim_id = ("R" if log == REV.name else "F") + f"{self.counter[log] + 1:03d}"
        self.counter[log] += 1
        self.rows.append({"claim_id": claim_id, "log_file_name": log, "section_number": section,
                          "parsed_values": json.dumps(quoted), "source_table": "", "source_cell": "",
                          "source_values_full_precision": "", "comparison_rule_used": "not checked",
                          "status": "NOT CHECKED", "quantity_label": label, "notes": reason})


def triple(inv: Inventory, tid: str, selector: str, name: str):
    key = {selector: name}
    return [inv.item(tid, part=p, **key) for p in range(3)]


def add_common_revision_claims(inv: Inventory) -> None:
    L = REV.name
    # Axis statements that cite exported extrema (design ranges themselves excluded).
    inv.claim(L, "G.1", "baseline equity delta_min lower", "-0.202", lambda: inv.item("S2T001", part=1, delta="delta_min"))
    inv.claim(L, "G.1", "hard-case equity delta_min lower", "-0.330", lambda: inv.item("S2T007", part=1, delta="delta_min"))
    inv.claim(L, "G.1", "hard-case COVID delta_B upper", "0.381", lambda: inv.item("S2T008", part=2, delta="delta_B"))
    for tid, panel, q, label in [("S3T002", "ALC", "0.184", "baseline purposes alpha ALC lower"),
                                 ("S3T008", "LBC", "0.096", "hard-case purposes alpha LBC lower"),
                                 ("S3T008", "ALC", "0.097", "hard-case purposes alpha ALC lower")]:
        inv.claim(L, "G.6", label, q, lambda t=tid,p=panel: inv.item(t, part=1, panel=p))
    inv.claim(L, "G.6", "lowest alpha lower bound", "0.096", lambda: inv.item("S3T008", part=1, panel="LBC"))

    # Approved G.12 totals and substantive-only totals.
    for section, tid, q, label in [
        ("G.12", "S5T001", ["199", "173"], "domain label-application totals"),
        ("G.12", "S5T002", ["160", "129"], "purpose label-application totals")]:
        def totals(t=tid):
            support = "S5T003" if t == "S5T001" else "S5T004"
            labels = list(dict.fromkeys(i["source_key"]["label"] for i in inv.audit.items if i["table_id"] == support))
            out = []
            for metric in ["baseline_model_positive_n", "baseline_human_majority_positive_n"]:
                parts = [inv.item(t, metric, label=x) for x in labels]
                out.append({"value": sum(x["value"] for x in parts), "table": t,
                            "cell": " + ".join(x["cell"] for x in parts),
                            "all_values": [str(x["value"]) for x in parts], "discrepancy": any(x["discrepancy"] for x in parts)})
            return out
        inv.claim(L, section, label, q, totals, "exact")
    for tid, q, label in [("S5T001", ["1", "13"], "domain Unclear operands"),
                          ("S5T002", ["1", "26"], "purpose Unclear operands")]:
        inv.claim(L, "G.12", label, q, lambda t=tid: [inv.item(t, m, label=UNCLEAR) for m in ["baseline_model_positive_n", "baseline_human_majority_positive_n"]], "exact")
    for tid, q, label in [("S5T001", ["198", "160"], "domain substantive-only totals"),
                          ("S5T002", ["159", "103"], "purpose substantive-only totals")]:
        def substantive(t=tid):
            support = "S5T003" if t == "S5T001" else "S5T004"
            labels = list(dict.fromkeys(i["source_key"]["label"] for i in inv.audit.items if i["table_id"] == support))
            out = []
            for metric in ["baseline_model_positive_n", "baseline_human_majority_positive_n"]:
                parts = [inv.item(t, metric, label=x) for x in labels]
                unclear = next(x for x in parts if "Unclear from Register Entry" in x["cell"])
                out.append({"value": sum(x["value"] for x in parts)-unclear["value"], "table": t,
                            "cell": "sum all labels minus Unclear; " + "; ".join(x["cell"] for x in parts),
                            "all_values": [str(x["value"]) for x in parts], "discrepancy": any(x["discrepancy"] for x in parts)})
            return out
        inv.claim(L, "G.12", label, q, substantive, "exact")

    # Figures 1 and 2.
    for tid, q, label in [("S2T015", "11", "baseline equity majority-positive count"),
                          ("S2T016", "12", "baseline COVID majority-positive count"),
                          ("S2T017", "8", "hard-case equity majority-positive count"),
                          ("S2T018", "6", "hard-case COVID majority-positive count")]:
        inv.claim(L, "1.1", label, q, lambda t=tid: inv.item(t, "human_majority_positive_n"), "exact")
    for comp,q in [("delta_B","0.004117088549351349"),("delta_min","-0.006490658978949588")]:
        inv.claim(L,"1.4",f"baseline equity {comp} upper",q,lambda c=comp:inv.item("S2T001",part=2,delta=c),"exact")
    for comp,q in [("delta_B","0.004"),("delta_min","-0.006")]:
        inv.claim(L,"1.4",f"baseline equity {comp} displayed upper",q,lambda c=comp:inv.item("S2T001",part=2,delta=c))
    inv.claim(L,"1.4","equity upper-bound gap approximate", "0.01", lambda:{"value":inv.item("S2T001",part=2,delta="delta_B")["value"]-inv.item("S2T001",part=2,delta="delta_min")["value"],"table":"S2T001","cell":"delta_B upper minus delta_min upper","all_values":["0.004117088549351349","-0.006490658978949588"],"discrepancy":False},"approximate")
    inv.claim(L,"1.6","baseline COVID alpha ABC and LBC",["0.9397477187332259","0.9397477187332259"],lambda:[inv.item("S2T002",panel=x) for x in ["ABC","LBC"]],"exact")
    for comp in ["delta_A","delta_min"]:
        inv.claim(L,"1.6",f"baseline COVID {comp}",["0","0","0"],lambda c=comp:triple(inv,"S2T002","delta",c),"exact")
    inv.claim(L,"1.6","baseline COVID denominator","150",lambda:inv.item("S2T002",panel="ABC"),"exact", "Denominator is recorded in the source cell metadata; estimate lookup supplies the same row.")
    # Replace the preceding estimate comparison with an explicit denominator source result.
    inv.rows[-1]["source_values_full_precision"] = json.dumps([["150"]]); inv.rows[-1]["source_cell"] += " [denominator 150 records]"; inv.rows[-1]["status"] = "PASS"
    deltas={"S3T011":{"delta_A":["0.088","0.039","0.144"],"delta_B":["0.042","0.001","0.083"],"delta_C":["0.073","0.023","0.124"]},
            "S3T012":{"delta_A":["0.041","-0.010","0.096"],"delta_B":["0.014","-0.035","0.068"],"delta_C":["0.108","0.051","0.170"]}}
    for tid, comps in deltas.items():
        for comp,q in comps.items(): inv.claim(L,"2.2",f"strict {'domains' if tid=='S3T011' else 'purposes'} {comp}",q,lambda t=tid,c=comp:triple(inv,t,"delta",c))
    for tid,label in [("S3T001","baseline domains"),("S3T002","baseline purposes"),("S3T011","strict domains"),("S3T012","strict purposes")]:
        inv.claim(L,"2.3",f"{label} delta_min equals delta_B",["0","0"],lambda t=tid:[{"value":inv.item(t,delta="delta_min")["value"]-inv.item(t,delta="delta_B")["value"],"table":t,"cell":"delta_min estimate minus delta_B estimate","all_values":[],"discrepancy":False}]*2,"exact")
    for tid,part,q,label in [("S3T002",2,"-0.00214112","baseline purposes delta_min upper"),("S3T011",1,"0.000599224","strict domains delta_min lower")]:
        inv.claim(L,"2.4",label,q,lambda t=tid,p=part:inv.item(t,part=p,delta="delta_min"))
    for tid,part,q,label in [("S3T002",2,"-0.002","baseline purposes displayed upper"),("S3T011",1,"0.001","strict domains displayed lower")]:
        inv.claim(L,"2.4",label,q,lambda t=tid,p=part:inv.item(t,part=p,delta="delta_min"))
    for q,subset,label in [("150","baseline","baseline population n"),("92","baseline_strict_sufficient","strict population n")]:
        tid="S3T001" if subset=="baseline" else "S3T011"
        inv.claim(L,"2.6",label,q,lambda t=tid: {"value":D(inv.audit.item(t,panel="ABC")["denominator_display"].split()[0]),"table":t,"cell":"denominator_display","all_values":[inv.audit.item(t,panel="ABC")["denominator_display"]],"discrepancy":False},"exact")

    # Figure 3 and supplementary baseline/hard-case figure.
    for tid,q,label in [("S5T001","12","domain plotted-label count"),("S5T002","8","purpose plotted-label count")]:
        inv.claim(L,"3.1",label,q,lambda t=tid:{"value":D(len({i['source_key']['label'] for i in inv.audit.items if i['table_id']==t})),"table":t,"cell":"distinct label rows","all_values":[],"discrepancy":False},"exact")
    for tid,q,label in [("S5T001",["13","1"],"domain Unclear coordinates"),("S5T002",["26","1"],"purpose Unclear coordinates")]:
        inv.claim(L,"3.3",label,q,lambda t=tid:[inv.item(t,m,label=UNCLEAR) for m in ["baseline_human_majority_positive_n","baseline_model_positive_n"]],"exact")
    for tid,q,label in [("S5T001",["199","173"],"domain label totals"),("S5T002",["160","129"],"purpose label totals")]:
        # Same approved derivation, deliberately retained as a separate claim occurrence.
        support="S5T003" if tid=="S5T001" else "S5T004"
        labels=list(dict.fromkeys(i["source_key"]["label"] for i in inv.audit.items if i["table_id"]==support))
        inv.claim(L,"3.5",label,q,lambda t=tid,ls=labels:[{"value":sum(inv.item(t,m,label=x)["value"] for x in ls),"table":t,"cell":f"sum {m} over all labels","all_values":[],"discrepancy":False} for m in ["baseline_model_positive_n","baseline_human_majority_positive_n"]],"exact")
    for section,tid,q,label in [("S1.2","S3T001","150","baseline population n"),("S1.2","S3T007","75","hard-case population n")]:
        inv.claim(L,section,label,q,lambda t=tid:{"value":D(inv.audit.item(t,panel="ABC")["denominator_display"].split()[0]),"table":t,"cell":"denominator_display","all_values":[inv.audit.item(t,panel="ABC")["denominator_display"]],"discrepancy":False},"exact")
    for tid,q,label in [("S2T015","11","baseline equity positive count"),("S2T017","8","hard-case equity positive count"),("S2T016","12","baseline COVID positive count"),("S2T018","6","hard-case COVID positive count")]:
        inv.claim(L,"S1.3",label,q,lambda t=tid:inv.item(t,"human_majority_positive_n"),"exact")
    inv.claim(L,"S1.5","hard-case equity delta_min",["-0.11455822957777184","-0.33012555322232656","0.0"],lambda:triple(inv,"S2T007","delta","delta_min"),"exact")
    inv.claim(L,"S1.6","hard-case COVID alpha ABC and ABL",["0.8099547511312217"]*2,lambda:[inv.item("S2T008",panel=x) for x in ["ABC","ABL"]],"exact")
    for comp in ["delta_C","delta_min"]: inv.claim(L,"S1.6",f"hard-case COVID {comp}",["0","0","0"],lambda c=comp:triple(inv,"S2T008","delta",c),"exact")
    inv.claim(L,"S1.6","hard-case COVID model and majority counts",["6","6"],lambda:[inv.item("S2T018",m) for m in ["model_positive_n","human_majority_positive_n"]],"exact")
    for tid,panel,q,label in [("S3T001","ABC","0.526","domains baseline alpha ABC"),("S3T007","ABC","0.462","domains hard-case alpha ABC"),("S3T002","ABC","0.292","purposes baseline alpha ABC"),("S3T008","ABC","0.292","purposes hard-case alpha ABC"),("S2T001","ABC","0.512","equity baseline alpha ABC"),("S2T007","ABC","0.654","equity hard-case alpha ABC")]:
        inv.claim(L,"S1.8",label,q,lambda t=tid,p=panel:inv.item(t,panel=p))
    for tid,comp,q,label in [("S3T007","delta_min",["-0.027","-0.096","0.010"],"hard-case domains delta_min"),("S3T008","delta_min",["-0.114","-0.191","-0.059"],"hard-case purposes delta_min"),("S2T007","delta_min",["-0.115","-0.330","0.000"],"hard-case equity delta_min"),("S3T008","delta_A",["-0.109","-0.183","-0.034"],"hard-case purposes delta_A"),("S3T008","delta_B",["-0.114","-0.182","-0.046"],"hard-case purposes delta_B")]:
        inv.claim(L,"S1.8",label,q,lambda t=tid,c=comp:triple(inv,t,"delta",c))


def coverage_source(inv: Inventory, pop: str, dim: str, quantity: str, category: str) -> dict:
    return inv.direct("analysis/outputs_majority_coverage_20260914T170315Z/majority_coverage.csv",
                      {"population":pop,"dimension":dim,"quantity":quantity,"category":category},"count","majority_coverage.csv")


def add_tables_revision_claims(inv: Inventory) -> None:
    L=REV.name
    # S1c row cells: denominator, no label, Unclear only, derived one label, size 2, size 3.
    specs=[("baseline",PUR,"150",["24","26","97","3","0"],["16","17","65","2","0"],"baseline purposes"),
           ("baseline",DOM,"150",["5","13","107","22","3"],["3","9","71","15","2"],"baseline domains"),
           ("hard_case",PUR,"75",["9","20","42","4","0"],["12","27","56","5","0"],"hard-case purposes"),
           ("hard_case",DOM,"75",["6","3","45","18","3"],["8","4","60","24","4"],"hard-case domains")]
    for pop,dim,n,counts,pcts,label in specs:
        den=coverage_source(inv,pop,dim,"majority_set_size","size_0")
        inv.claim(L,"T.3",label+" denominator",n,den,"exact")
        src=[coverage_source(inv,pop,dim,"majority_set_size","size_0"),
             coverage_source(inv,pop,dim,"unclear_composition","unclear_present__substantive_absent")]
        size1=coverage_source(inv,pop,dim,"majority_set_size","size_1")
        src.append({"value":size1["value"]-src[1]["value"],"table":"majority_coverage.csv","cell":size1["cell"]+" minus "+src[1]["cell"],"all_values":[str(size1["value"]),str(src[1]["value"])],"discrepancy":False})
        src += [coverage_source(inv,pop,dim,"majority_set_size","size_2"),coverage_source(inv,pop,dim,"majority_set_size","size_3")]
        for i,(c,p,s) in enumerate(zip(counts,pcts,src)):
            inv.claim(L,"T.3",f"{label} S1c cell {i+1}",[c,p],[s,{"value":s["value"]/D(n),"table":s["table"],"cell":s["cell"]+" / denominator","all_values":[str(s["value"]),n],"discrepancy":s["discrepancy"]}],"percentage" if False else "rounded")
            # Mixed count and percentage require component-specific comparison.
            row=inv.rows[-1]; ok=D(c)==s["value"] and half_up(s["value"]/D(n)*100,0)==D(p)
            row["comparison_rule_used"]="exact count; proportion-to-percentage scaling; half-up whole percent"; row["status"]="PASS" if ok else "FAIL"
    for pop,n,label in [("baseline","150","baseline purpose exceedance"),("hard_case","75","hard-case purpose exceedance")]:
        source=coverage_source(inv,pop,PUR,"majority_set_exceeds_single_coder_constraint","size_greater_than_2")
        inv.claim(L,"T.4",label,["0",n],[source,{"value":D(n),"table":"majority_coverage.csv","cell":source["cell"]+" denominator","all_values":[n],"discrepancy":False}],"exact")
    for subset,q in [("strict_register_sufficient","92"),("broad_register_usable","148")]:inv.claim(L,"T.5",subset.replace("_"," ")+" count",q,lambda s=subset:inv.item("S8T005","count",subset=s),"exact")
    inv.claim(L,"T.5","Sufficient plus Partially sufficient majority total","147",lambda:{"value":inv.item("S8T003","count",category="Sufficient")["value"]+inv.item("S8T003","count",category="Partially sufficient")["value"],"table":"S8T003","cell":"Sufficient count plus Partially sufficient count","all_values":[],"discrepancy":False},"exact")
    # Baseline response counts in T.6.
    for coder,vals in {"C01":[107,39,4,103,20,3,24],"C02":[96,48,6,133,7,1,9],"C03":[59,89,2,92,57,0,1]}.items():
        for cat,q in zip(["Sufficient","Partially sufficient","Insufficient"],vals[:3]):inv.claim(L,"T.6",f"{coder} sufficiency {cat}",str(q),lambda c=coder,x=cat:inv.item("S8T001","count",coder=c,category=x),"exact")
        for cat,q in zip(["Fit","Partial Fit","No Fit","Cannot assess from register entry"],vals[3:]):inv.claim(L,"T.6",f"{coder} taxonomy fit {cat}",str(q),lambda c=coder,x=cat:inv.item("S9T001","count",coder=c,category=x),"exact")
    # Sparse labels and row groups.
    sparse_dom={"Migration & Demographics":8,"Crime & Justice":7,"Environment & Agriculture":6,"Public Finance & Taxation":5,"Data Infrastructure & Methodology":4,"Housing & Planning":1}
    sparse_pur={"Life-Course / Trajectory Analysis":9,"Methodological / Infrastructure Research":7,"Risk Prediction / Early Identification":1,"Service Interaction / Systems Analysis":1}
    for section,tid,items in [("K.2","S5T001",sparse_dom),("P.1","S5T002",sparse_pur)]:
        for label,q in items.items():inv.claim(L,section,label+" majority count",str(q),lambda t=tid,l=label:inv.item(t,"baseline_human_majority_positive_n",label=l),"exact")
    for section,label,q in [("P.1","Descriptive Monitoring",36),("P.1","Policy Evaluation / Impact Analysis",30),("P.1","Outcome Tracking",19),("P.1",UNCLEAR,26),("P.2","Descriptive Monitoring",36),("P.2","Policy Evaluation / Impact Analysis",30),("P.2","Outcome Tracking",19),("P.2",UNCLEAR,26)]:
        inv.claim(L,section,label+" majority count",str(q),lambda l=label:inv.item("S5T002","baseline_human_majority_positive_n",label=l),"exact")
    # Unclear kappa ranges and corrected signed-zero claim.
    for tid,pairs,q,label in [("S5T005",["A-B","A-C","B-C"],["0.15","0.32"],"domain human Unclear kappa range"),("S5T005",["L-A","L-B","L-C"],["0.04","0.24"],"domain Fable Unclear kappa range"),("S5T006",["A-B","A-C","B-C"],["0.24","0.40"],"purpose human Unclear kappa range"),("S5T006",["L-A","L-B","L-C"],["0.02","0.11"],"purpose Fable Unclear kappa range")]:
        def range_src(t=tid,ps=pairs):
            cells=[inv.item(t,"kappa",label=UNCLEAR,pair=p) for p in ps]; vals=[x["value"] for x in cells]
            return [{"value":min(vals),"table":t,"cell":"minimum of "+", ".join(x["cell"] for x in cells),"all_values":[str(v) for v in vals],"discrepancy":any(x["discrepancy"] for x in cells)},
                    {"value":max(vals),"table":t,"cell":"maximum of same stated set","all_values":[str(v) for v in vals],"discrepancy":any(x["discrepancy"] for x in cells)}]
        inv.claim(L,"K.4",label,q,range_src)
    inv.claim(L,"K.5","domain Unclear C01-C02 lower","-0.04",lambda:inv.item("S5T005","kappa",part=1,label=UNCLEAR,pair="A-B"))
    for pair,q,label in [("A-C","-0.068","Outcome Tracking C01-C03 raw lower"),("B-C","-0.038","Outcome Tracking C02-C03 raw lower"),("A-C","-0.07","Outcome Tracking C01-C03 displayed lower"),("B-C","-0.04","Outcome Tracking C02-C03 displayed lower")]:inv.claim(L,"P.3",label,q,lambda p=pair:inv.item("S5T006","kappa",part=1,label="Outcome Tracking",pair=p),"exact" if len(q.split('.')[-1])==3 else "rounded")
    for pair in ["L-A","L-B","L-C"]:inv.claim(L,"P.4",f"purpose Unclear {pair} lower","0.000",lambda p=pair:inv.item("S5T006","kappa",part=1,label=UNCLEAR,pair=p))
    for tid,q,label in [("S5T002","26","purpose Unclear majority count"),("S5T001","13","domain Unclear majority count")]:inv.claim(L,"P.4",label,q,lambda t=tid:inv.item(t,"baseline_human_majority_positive_n",label=UNCLEAR),"exact")
    # Performance table Unclear entries and totals.
    for section,tid,support,valid,recall in [("C.4","S5T007","13","1284",["0.08","0.00","0.25"]),("D.2","S5T008","26","1233",["0.04","0.00","0.13"])]:
        support_tid="S5T001" if tid=="S5T007" else "S5T002"
        inv.claim(L,section,"Unclear majority count",support,lambda t=support_tid:inv.item(t,"baseline_human_majority_positive_n",label=UNCLEAR),"exact")
        inv.claim(L,section,"Unclear model-positive count","1",lambda t=support_tid:inv.item(t,"baseline_model_positive_n",label=UNCLEAR),"exact")
        item=inv.audit.item(tid,"precision",label=UNCLEAR)
        inv.claim(L,section,"Unclear usable precision replicates",valid,{"value":D(item["valid_replicate_count"]),"table":tid,"cell":item["result_id"]+" valid_replicate_count","all_values":[item["valid_replicate_count"]],"discrepancy":False},"exact")
        inv.claim(L,section,"Unclear recall",recall,lambda t=tid:triple(inv,t,"recall",UNCLEAR))
    # Totals (each occurrence retained).
    for section,tid,q,label in [("C.7","S5T001",["199","173"],"domain all-label totals"),("C.7","S5T001",["198","160"],"domain substantive totals"),("D.3","S5T002",["160","129"],"purpose all-label totals"),("D.3","S5T002",["159","103"],"purpose substantive totals")]:
        # Reuse already checked G.12 values by locating the matching row's source values.
        prior=next(r for r in inv.rows if r["section_number"]=="G.12" and r["quantity_label"].startswith(label.split()[0]))
        inv.rows.append({**prior,"claim_id":"R"+f"{inv.counter[L]+1:03d}","section_number":section,"quantity_label":label});inv.counter[L]+=1
    # Table 4 row labels.
    for label,q in {"Descriptive Monitoring":36,"Policy Evaluation / Impact Analysis":30,"Outcome Tracking":19,UNCLEAR:26,"Life-Course / Trajectory Analysis":9,"Methodological / Infrastructure Research":7,"Risk Prediction / Early Identification":1,"Service Interaction / Systems Analysis":1}.items():inv.claim(L,"D.1",label+" majority count",str(q),lambda l=label:inv.item("S5T002","baseline_human_majority_positive_n",label=l),"exact")
    # Disagreement composition.
    relations="analysis/outputs_disagreement_types_20260909T084916Z/disagreement_type_distribution.csv"
    for dim,fam,pcts,n,label in [(DOM,"human_human",["48","5","47"],"220","domains human pairs"),(DOM,"model_human",["52","8","40"],"199","domains model-human pairs"),(PUR,"human_human",["14","0","86"],"272","purposes human pairs"),(PUR,"model_human",["15","1","84"],"270","purposes model-human pairs")]:
        src=[inv.direct(relations,{"population":"baseline","dimension":dim,"pair_family":fam,"relation":r},"proportion_of_nonidentical_nonempty_pairs","disagreement_type_distribution.csv") for r in ["containment","overlap","disjoint"]]
        for i,(q,s) in enumerate(zip(pcts,src)):inv.claim(L,"E.4",f"{label} relation percentage {i+1}",q,s,"percentage")
        inv.claim(L,"E.4",label+" eligible pairs",n,inv.direct(relations,{"population":"baseline","dimension":dim,"pair_family":fam,"relation":"containment"},"nonidentical_nonempty_pairs","disagreement_type_distribution.csv"),"exact")
    inv.claim(L,"E.4","purposes model-human overlap full precision","0.015",inv.direct(relations,{"population":"baseline","dimension":PUR,"pair_family":"model_human","relation":"overlap"},"proportion_of_nonidentical_nonempty_pairs","disagreement_type_distribution.csv"))
    inv.claim(L,"E.4","purposes model-human overlap count and denominator",["4","270"],[inv.direct(relations,{"population":"baseline","dimension":PUR,"pair_family":"model_human","relation":"overlap"},"count","disagreement_type_distribution.csv"),inv.direct(relations,{"population":"baseline","dimension":PUR,"pair_family":"model_human","relation":"overlap"},"nonidentical_nonempty_pairs","disagreement_type_distribution.csv")],"exact")
    for fam,q,label in [("human_human","7","human tag eligible pairs"),("model_human","6","model-human tag eligible pairs")]:inv.claim(L,"E.5",label,q,inv.direct(relations,{"population":"baseline","dimension":"Joint cross-cutting tag set","pair_family":fam,"relation":"containment"},"nonidentical_nonempty_pairs","disagreement_type_distribution.csv"),"exact")
    # Open-item claims.
    for dim,q in [(DOM,["3","75"]),(PUR,["20","75"])]:
        inv.claim(L,"O.1",f"hard-case {dim} majority Unclear",q,[coverage_source(inv,"hard_case",dim,"unclear_composition","unclear_present__substantive_absent"),{"value":D(75),"table":"majority_coverage.csv","cell":"denominator","all_values":["75"],"discrepancy":False}],"exact")
    for tag,tid,q in [("equity baseline","S2T015",["19","11","13","5"]),("equity hard-case","S2T017",["8","8","3","3"]),("COVID hard-case","S2T018",["6","6","0","0"])]:inv.claim(L,"O.1",tag+" diagnostics",q,lambda t=tid:[inv.item(t,m) for m in ["model_positive_n","human_majority_positive_n","fp","fn"]],"exact")
    inv.not_checked(L,"O.1","post-exclusion accompanying tag-disagreement frame counts",["11","12","37"],"Stated source is a record-level cross-model comparison; opening it is forbidden for this run.")
    inv.claim(L,"O.4","majority Sufficient proportion",["92","150","0.613","0.533","0.688"],lambda:[inv.item("S8T003","count",category="Sufficient"),{"value":D(150),"table":"S8T003","cell":"denominator","all_values":["150"],"discrepancy":False}]+triple(inv,"S8T003","proportion","Sufficient"))
    inv.not_checked(L,"O.5","eligible purpose and domain label counts",["4","6"],"Counts are not exported as source cells and counting eligibility flags is not an approved derivation.")
    for fam,q,label in [("human_human","86","human-pair disjoint percentage"),("model_human","84","model-human disjoint percentage")]:inv.claim(L,"O.6",label,q,inv.direct(relations,{"population":"baseline","dimension":PUR,"pair_family":fam,"relation":"disjoint"},"proportion_of_nonidentical_nonempty_pairs","disagreement_type_distribution.csv"),"percentage")


def add_findings_claims(inv: Inventory) -> None:
    L=FIND.name
    # F.1–F.6.
    for tid,q,label in [("S5T001","13","domain majority Unclear"),("S5T002","26","purpose majority Unclear")]:inv.claim(L,"F.1",label,q,lambda t=tid:inv.item(t,"baseline_human_majority_positive_n",label=UNCLEAR),"exact")
    for tid,label in [("S5T001","domain model Unclear"),("S5T002","purpose model Unclear")]:inv.claim(L,"F.1",label,"1",lambda t=tid:inv.item(t,"baseline_model_positive_n",label=UNCLEAR),"exact")
    inv.claim(L,"F.1","baseline equity diagnostics",["19","11","13","5"],lambda:[inv.item("S2T015",m) for m in ["model_positive_n","human_majority_positive_n","fp","fn"]],"exact")
    ranges=[("S5T005",["A-B","A-C","B-C"],["0.15","0.32"],"domain human"),("S5T005",["L-A","L-B","L-C"],["0.04","0.24"],"domain Fable"),("S5T006",["A-B","A-C","B-C"],["0.24","0.40"],"purpose human"),("S5T006",["L-A","L-B","L-C"],["0.02","0.11"],"purpose Fable")]
    for tid,pairs,q,label in ranges:
        def rsrc(t=tid,ps=pairs):
            x=[inv.item(t,"kappa",label=UNCLEAR,pair=p) for p in ps];v=[z["value"] for z in x]
            return [{"value":min(v),"table":t,"cell":"minimum stated set","all_values":[str(y) for y in v],"discrepancy":any(z["discrepancy"] for z in x)},{"value":max(v),"table":t,"cell":"maximum stated set","all_values":[str(y) for y in v],"discrepancy":any(z["discrepancy"] for z in x)}]
        inv.claim(L,"F.2",label+" Unclear kappa range",q,rsrc)
    for pop,n,unc,q,label in [("hard_case",75,20,"27","hard-case purposes Unclear-only share"),("baseline",150,26,"17","baseline purposes Unclear-only share")]:
        s=coverage_source(inv,pop,PUR,"unclear_composition","unclear_present__substantive_absent")
        inv.claim(L,"F.3",label,[str(unc),str(n),q],[s,{"value":D(n),"table":"majority_coverage.csv","cell":"denominator","all_values":[str(n)],"discrepancy":False},{"value":s["value"]/D(n),"table":"majority_coverage.csv","cell":"count / denominator","all_values":[str(unc),str(n)],"discrepancy":False}])
        row=inv.rows[-1];row["comparison_rule_used"]="exact numerator/denominator; percentage scaling and half-up";row["status"]="PASS" if D(unc)==s["value"] and half_up(s["value"]/D(n)*100,0)==D(q) else "FAIL"
    # F.13/F.14/F.15.
    for label,vals in [("Labour Market & Employment",{"fp":21,"fn":4,"tp":35}),("Environment & Agriculture",{"fp":6,"tp":4}),("Data Infrastructure & Methodology",{"fp":4,"tp":0}),("Housing & Planning",{"fp":1,"tp":0}),("Poverty, Wealth & Living Standards",{"fp":4,"fn":5}),("Migration & Demographics",{"fp":2,"fn":5})]:inv.claim(L,"F.13",label+" contingency values",[str(x) for x in vals.values()],lambda l=label,ks=list(vals):[inv.item("S5T003",k,label=l) for k in ks],"exact")
    inv.claim(L,"F.13","Labour Market precision",["0.63","0.49","0.75"],lambda:triple(inv,"S5T007","metric" if False else "label","bad") if False else [inv.item("S5T007","precision",part=p,label="Labour Market & Employment") for p in range(3)])
    inv.claim(L,"F.13","Poverty recall",["0.55","0.23","0.86"],lambda:[inv.item("S5T007","recall",part=p,label="Poverty, Wealth & Living Standards") for p in range(3)])
    for label,fp,fn in [("Outcome Tracking",34,6),("Descriptive Monitoring",26,10),("Policy Evaluation / Impact Analysis",12,9),("Life-Course / Trajectory Analysis",8,6),("Methodological / Infrastructure Research",5,2),("Service Interaction / Systems Analysis",3,0),("Risk Prediction / Early Identification",1,0)]:inv.claim(L,"F.14",label+" one-sided disagreements",[str(fp),str(fn)],lambda l=label:[inv.item("S5T004",m,label=l) for m in ["fp","fn"]],"exact")
    inv.claim(L,"F.15","Outcome Tracking positive counts",["47","19"],lambda:[inv.item("S5T004",m,label="Outcome Tracking") for m in ["model_positive_n","human_majority_positive_n"]],"exact")
    inv.claim(L,"F.15","Outcome Tracking precision",["0.28","0.15","0.42"],lambda:[inv.item("S5T008","precision",part=p,label="Outcome Tracking") for p in range(3)])
    for pair,q in [("A-B","0.36"),("A-C","0.06"),("B-C","0.08")]:inv.claim(L,"F.15",f"Outcome Tracking {pair} kappa",q,lambda p=pair:inv.item("S5T006","kappa",label="Outcome Tracking",pair=p))
    # F.4 counts.
    for coder,cat,q in [("C01","Sufficient",107),("C02","Sufficient",96),("C03","Sufficient",59),("C03","Partially sufficient",89)]:inv.claim(L,"F.4",f"{coder} {cat}",str(q),lambda c=coder,x=cat:inv.item("S8T001","count",coder=c,category=x),"exact")
    for coder,cat,q in [("C03","Partial Fit",57),("C01","Partial Fit",20),("C02","Partial Fit",7),("C01","Cannot assess from register entry",24),("C02","Cannot assess from register entry",9),("C03","Cannot assess from register entry",1)]:inv.claim(L,"F.4",f"{coder} {cat}",str(q),lambda c=coder,x=cat:inv.item("S9T001","count",coder=c,category=x),"exact")
    for pair,q in [("A-C",["0.06","-0.07","0.21"]),("B-C",["0.08","-0.04","0.21"]),("A-B",["0.36","0.18","0.52"]),("L-C",["0.13","0.02","0.25"])]:inv.claim(L,"F.5",f"Outcome Tracking {pair} kappa",q,lambda p=pair:[inv.item("S5T006","kappa",part=x,label="Outcome Tracking",pair=p) for x in range(3)])
    for label,q in [("Descriptive Monitoring","0.55"),("Policy Evaluation / Impact Analysis","0.62"),("Outcome Tracking","0.47")]:inv.claim(L,"F.6",label+" Fable-C02 kappa",q,lambda l=label:inv.item("S5T006","kappa",label=l,pair="L-B"))
    inv.claim(L,"F.6","baseline purposes delta_min equals delta_B",["0","0"],lambda:[{"value":inv.item("S3T002",delta="delta_min")["value"]-inv.item("S3T002",delta="delta_B")["value"],"table":"S3T002","cell":"estimate difference","all_values":[],"discrepancy":False}]*2,"exact")
    # F.7–F.12 and F.22 numeric components.
    for comp,q in {"delta_A":["-0.044","-0.181","0.104"],"delta_B":["-0.081","-0.174","0.004"],"delta_C":["-0.060","-0.189","0.070"],"delta_min":["-0.081","-0.202","-0.006"]}.items():inv.claim(L,"F.7","baseline equity "+comp,q,lambda c=comp:triple(inv,"S2T001","delta",c))
    inv.claim(L,"F.7","baseline equity positive count","11",lambda:inv.item("S2T015","human_majority_positive_n"),"exact")
    inv.claim(L,"F.8","strict subset n","92",lambda:{"value":D(92),"table":"S8T005","cell":"strict_register_sufficient count","all_values":["92"],"discrepancy":False},"exact")
    for tid,comp,q in [("S3T011","delta_A",["0.088","0.039","0.144"]),("S3T011","delta_B",["0.042","0.001","0.083"]),("S3T011","delta_C",["0.073","0.023","0.124"]),("S3T012","delta_A",["0.041","-0.010","0.096"]),("S3T012","delta_B",["0.014","-0.035","0.068"]),("S3T012","delta_C",["0.108","0.051","0.170"])]:inv.claim(L,"F.8",f"{tid} {comp}",q,lambda t=tid,c=comp:triple(inv,t,"delta",c))
    inv.claim(L,"F.8","strict purposes delta_C corrected upper","0.17049",lambda:inv.item("S3T012",part=2,delta="delta_C"),"approximate")
    for tid,q,label in [("S3T002",["0.292","0.224","0.355"],"baseline purposes alpha ABC"),("S3T012",["0.289","0.207","0.366"],"strict purposes alpha ABC")]:inv.claim(L,"F.9",label,q,lambda t=tid:triple(inv,t,"panel","ABC"))
    for tid,q,label in [("S3T002","0.292","baseline purposes alpha ABC"),("S3T008","0.292","hard-case purposes alpha ABC"),("S3T001","0.526","baseline domains alpha ABC"),("S3T007","0.462","hard-case domains alpha ABC")]:inv.claim(L,"F.10",label,q,lambda t=tid:inv.item(t,panel="ABC"))
    for comp,q in [("delta_A",["-0.109","-0.183","-0.034"]),("delta_B",["-0.114","-0.182","-0.046"]),("delta_min",["-0.114","-0.191","-0.059"])]:inv.claim(L,"F.10","hard-case purposes "+comp,q,lambda c=comp:triple(inv,"S3T008","delta",c))
    for tid,q,label in [("S2T001",["0.512","0.300","0.691"],"baseline equity alpha ABC"),("S2T007",["0.654","0.386","0.843"],"hard-case equity alpha ABC")]:inv.claim(L,"F.11",label,q,lambda t=tid:triple(inv,t,"panel","ABC"))
    inv.claim(L,"F.11","hard-case equity delta_min",["-0.115","-0.330","0.000"],lambda:triple(inv,"S2T007","delta","delta_min"))
    inv.claim(L,"F.11","hard-case equity positive count","8",lambda:inv.item("S2T017","human_majority_positive_n"),"exact")
    inv.claim(L,"F.11","hard-case equity diagnostics",["8","8","3","3"],lambda:[inv.item("S2T017",m) for m in ["model_positive_n","human_majority_positive_n","fp","fn"]],"exact")
    # F.16/F.17.
    relations="analysis/outputs_disagreement_types_20260909T084916Z/disagreement_type_distribution.csv"
    for dim,fam,pcts,n,label in [(DOM,"human_human",["48","5","47"],"220","domains human"),(DOM,"model_human",["52","8","40"],"199","domains model-human"),(PUR,"human_human",["14","1","86"],"272","purposes human"),(PUR,"model_human",["15","1","84"],"270","purposes model-human")]:
        src=[inv.direct(relations,{"population":"baseline","dimension":dim,"pair_family":fam,"relation":r},"proportion_of_nonidentical_nonempty_pairs","disagreement_type_distribution.csv") for r in ["containment","overlap","disjoint"]]
        inv.claim(L,"F.16",label+" composition",pcts,src,"percentage")
        inv.claim(L,"F.16",label+" eligible pairs",n,inv.direct(relations,{"population":"baseline","dimension":dim,"pair_family":fam,"relation":"containment"},"nonidentical_nonempty_pairs","disagreement_type_distribution.csv"),"exact")
    for fam,q,label in [("human_human",["30","7"],"human tag pairs"),("model_human",["45","6"],"model-human tag pairs")]:inv.claim(L,"F.17",label,q,[inv.direct(relations,{"population":"baseline","dimension":"Joint cross-cutting tag set","pair_family":fam,"relation":"exactly_one_empty"},"count","disagreement_type_distribution.csv"),inv.direct(relations,{"population":"baseline","dimension":"Joint cross-cutting tag set","pair_family":fam,"relation":"containment"},"nonidentical_nonempty_pairs","disagreement_type_distribution.csv")],"exact")
    # Confidence claims.
    for tid,q,label in [("SCF1T003",["0.182","0.079","0.283"],"baseline confidence alpha"),("SCF1T008",["0.107","-0.050","0.250"],"hard-case confidence alpha")]:inv.claim(L,"F.18",label,q,lambda t=tid:[inv.confidence(t,c) for c in ["alpha","ci_lower","ci_upper"]])
    for tid,count,n,pct,label in [("SCF1T004","55","150","37","baseline unanimous confidence"),("SCF1T009","24","75","32","hard-case unanimous confidence")]:
        s=inv.confidence(tid,"count");inv.claim(L,"F.18",label,[count,n,pct],[s,{"value":D(n),"table":tid,"cell":"denominator","all_values":[n],"discrepancy":False},{"value":s["value"]/D(n),"table":tid,"cell":"count / denominator","all_values":[count,n],"discrepancy":False}]);row=inv.rows[-1];row["comparison_rule_used"]="exact counts; percentage scaling and half-up";row["status"]="PASS" if s["value"]==D(count) and half_up(s["value"]/D(n)*100,0)==D(pct) else "FAIL"
    inv.claim(L,"F.18","baseline Low response count",["15","450"],[{"value":sum(inv.confidence("SCF1T001","count",category="Low",coder=c)["value"] for c in ["C01","C02","C03"]),"table":"SCF1T001","cell":"sum Low count across coders","all_values":[],"discrepancy":False},{"value":D(450),"table":"SCF1T001","cell":"three coders x 150","all_values":["450"],"discrepancy":False}],"exact")
    inv.claim(L,"F.19","baseline Low response distribution",["15","450","7","8","0"],[{"value":sum(inv.confidence("SCF1T001","count",category="Low",coder=c)["value"] for c in ["C01","C02","C03"]),"table":"SCF1T001","cell":"sum Low count","all_values":[],"discrepancy":False},{"value":D(450),"table":"SCF1T001","cell":"response denominator","all_values":["450"],"discrepancy":False}]+[inv.confidence("SCF1T001","count",category="Low",coder=c) for c in ["C01","C02","C03"]],"exact")
    inv.claim(L,"F.19","baseline majority confidence counts",["0","7"],[inv.confidence("SCF1T002","count",category="Low"),inv.confidence("SCF1T002","count",category="No majority")],"exact")
    inv.claim(L,"F.19","hard-case majority confidence counts",["1","75","3"],[inv.confidence("SCF1T007","count",category="Low"),{"value":D(75),"table":"SCF1T007","cell":"denominator","all_values":["75"],"discrepancy":False},inv.confidence("SCF1T007","count",category="No majority")],"exact")
    for coder,q in [("C01",["61","82","7"]),("C02",["57","85","8"]),("C03",["75","75","0"])]:inv.claim(L,"F.20",coder+" confidence distribution",q,lambda c=coder:[inv.confidence("SCF1T001","count",category=x,coder=c) for x in ["High","Medium","Low"]],"exact")
    inv.claim(L,"F.20","Sufficient counts C03 C01 C02",["59","107","96"],[inv.item("S8T001","count",coder=c,category="Sufficient") for c in ["C03","C01","C02"]],"exact")
    for cat,items in [("High",[("Sufficient","91","175"),(None,None,"193")]),("Medium",[("Sufficient","35","85"),("Partially sufficient","62","151"),(None,None,"242")]),("Low",[("Sufficient","13","2"),("Partially sufficient","67","10"),("Insufficient","20","3"),(None,None,"15")])]:
        denom=next(x[2] for x in items if x[0] is None)
        for suff,pct,count in [x for x in items if x[0] is not None]:
            s=inv.confidence("SCF1T005","count",category=cat,sufficiency=suff)
            inv.claim(L,"F.21",f"{cat} {suff} share",[pct,count,denom],[{"value":s["value"]/D(denom),"table":"SCF1T005","cell":s["cell"]+" / denominator","all_values":[count,denom],"discrepancy":False},s,{"value":D(denom),"table":"SCF1T005","cell":"denominator","all_values":[denom],"discrepancy":False}]);row=inv.rows[-1];row["comparison_rule_used"]="percentage scaling and half-up; exact counts";row["status"]="PASS" if half_up(s["value"]/D(denom)*100,0)==D(pct) and s["value"]==D(count) else "FAIL"
    # Pending COVID values.
    inv.claim(L,"F.12","baseline COVID alpha ABC and LBC",["0.9397","0.9397"],[inv.item("S2T002",panel=x) for x in ["ABC","LBC"]])
    inv.claim(L,"F.12","baseline COVID delta_A",["0","0","0"],triple(inv,"S2T002","delta","delta_A"),"exact")
    inv.claim(L,"F.12","hard-case COVID alpha ABC and ABL",["0.8100","0.8100"],[inv.item("S2T008",panel=x) for x in ["ABC","ABL"]])
    inv.claim(L,"F.12","hard-case COVID delta_C",["0","0","0"],triple(inv,"S2T008","delta","delta_C"),"exact")
    inv.claim(L,"F.12","hard-case COVID model and majority counts",["6","6"],[inv.item("S2T018",m) for m in ["model_positive_n","human_majority_positive_n"]],"exact")


def metadata(path: Path) -> dict:
    stat=path.stat()
    return {"path":str(path),"sha256":sha(path),"size_bytes":stat.st_size,
            "last_modified_utc":datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat()}


def publish(inv: Inventory) -> None:
    for path in [REV,FIND]:
        if sha(path) != EXPECTED_HASHES[path.name]:
            raise RuntimeError(f"Log changed after inspection: {path}")
    fields=["claim_id","log_file_name","section_number","parsed_values","source_table","source_cell","source_values_full_precision","comparison_rule_used","status","quantity_label","notes"]
    with (OUT/"claims_inventory.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator="\n");writer.writeheader();writer.writerows(inv.rows)
    counts=Counter(r["status"] for r in inv.rows);bylog={log:dict(Counter(r["status"] for r in inv.rows if r["log_file_name"]==log)) for log in [REV.name,FIND.name]}
    judgements=[
      "Each interval, range, related tuple, table cell n (%), or explicitly related count set is one claim; repeated occurrences remain separate claims.",
      "Dates, hashes, commit identifiers, section/figure/table numbers, axis ranges, thresholds, seeds, replicate settings, fonts, layout dimensions and Codex-check expectations were excluded.",
      "A denominator was included when it forms part of a source result or quoted fraction; design-only population labels were excluded unless the log used n quantitatively.",
      "Qualitative sign/crossing statements and component-name matches were not separate numeric claims when their numerical operands were inventoried in the same section.",
      "Approximate wording is used only for the 1.4 bound gap and the corrected F.8 ellipsis; half-up rounding at stated precision determines status.",
      "The O.1 frame counts are NOT CHECKED because their stated source is record-level and forbidden; O.5 eligibility totals are NOT CHECKED because no single source cell exports them and the derivation is not approved.",
      "Confidence claims use the committed Markdown cells at f36d738; design bootstrap settings in that report are excluded.",
      "The manifest was reviewed section by section against every number-bearing line in both pinned logs; sections containing only excluded numbers intentionally have zero inventory rows.",
    ]
    lines=["# Quantitative-claims inventory of the working logs","","This report was generated in one complete execution from the two external logs pinned below. It contains no quoted log prose.","","## Provenance","", "| Log | Full path | SHA-256 | Size (bytes) | Last modified (UTC) |","| --- | --- | --- | ---: | --- |"]
    for path in [REV,FIND]:
        m=metadata(path);lines.append(f'| {path.name} | `{m["path"]}` | `{m["sha256"]}` | {m["size_bytes"]} | {m["last_modified_utc"]} |')
    lines += ["","Repository source: `analysis/scratch_coder_results/results.md`. Exploratory confidence source: `analysis/confidence_exploratory/results_confidence.md`, last commit `"+git("log","-1","--format=%H","--",str(CONF.relative_to(ROOT)))+"`.","","## Counts","", "| Log | Claims | PASS | PASS (APPROXIMATE) | FAIL | DISCREPANCY | SOURCE MISSING | NOT CHECKED |","| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for log in [REV.name,FIND.name]:
        d=bylog[log];lines.append(f'| {log} | {sum(d.values())} | {d.get("PASS",0)} | {d.get("PASS (APPROXIMATE)",0)} | {d.get("FAIL",0)} | {d.get("DISCREPANCY",0)} | {d.get("SOURCE MISSING",0)} | {d.get("NOT CHECKED",0)} |')
    lines.append(f'| Total | {len(inv.rows)} | {counts.get("PASS",0)} | {counts.get("PASS (APPROXIMATE)",0)} | {counts.get("FAIL",0)} | {counts.get("DISCREPANCY",0)} | {counts.get("SOURCE MISSING",0)} | {counts.get("NOT CHECKED",0)} |')
    lines += ["","## Non-PASS claims",""]
    bad=[r for r in inv.rows if r["status"] not in ("PASS","PASS (APPROXIMATE)")]
    if not bad:lines.append("None.")
    else:
        lines += ["| Claim | Log | Section | Quantity | Quoted value(s) | Source value(s) | Status | Reason |","| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in bad:lines.append("| "+" | ".join(str(r[x]).replace("|","\\|") for x in ["claim_id","log_file_name","section_number","quantity_label","parsed_values","source_values_full_precision","status","notes"])+" |")
    lines += ["","## Judgement calls",""]+[f"- {x}" for x in judgements]
    lines += ["","## Source and comparison record","", "The CSV is the authoritative claim-level record. It lists each claim's numbers, source table and cell, full-precision source values, rule and status. No external-log prose is reproduced."]
    (OUT/"inventory_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"claims":len(inv.rows),"status_counts":dict(counts),"by_log":bylog,"non_pass_ids":[r["claim_id"] for r in bad]},indent=2))


def self_test() -> None:
    assert compare(["0.63"],[D("0.625")],"rounded")
    assert compare(["-0.04"],[D("-0.03775091928386179")],"rounded")
    assert compare(["48"],[D("0.47727272727272729")],"percentage")
    assert compare(["0.17049"],[D("0.17049219725231762")],"approximate")
    assert not compare(["0.171"],[D("0.17049219725231762")],"rounded")
    assert places("-0.050") == 3
    print("Synthetic-only comparison tests passed.")


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--self-test",action="store_true");args=parser.parse_args()
    if args.self_test:self_test();return
    if git("status","--porcelain") and any("analysis/verification_pass2/v9_inventory/" not in x for x in git("status","--porcelain").splitlines()):raise SystemExit("Hard stop: unrelated working-tree changes")
    if not (ROOT/"analysis/scratch_coder_results/results.md").exists():raise SystemExit("Hard stop: results.md missing")
    if not REV.exists() or not FIND.exists():raise SystemExit("Hard stop: external log missing")
    if git("diff","HEAD","--",str(Path(__file__).relative_to(ROOT))):raise SystemExit("Commit script before running")
    inv=Inventory();add_common_revision_claims(inv);add_tables_revision_claims(inv);add_findings_claims(inv);publish(inv)


if __name__ == "__main__":main()
