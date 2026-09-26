"""Synthetic-only helpers.  This module has no network or production fallback."""
from __future__ import annotations
import copy, csv, hashlib, json, random, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; FIXTURES=ROOT/"fixtures"
HEADER=["Variable / Field Name","Form Name","Section Header","Field Type","Field Label","Choices, Calculations, OR Slider Labels","Field Note","Text Validation Type OR Show Slider Number","Text Validation Min","Text Validation Max","Identifier?","Branching Logic (Show field only if...)","Required Field?","Custom Alignment","Question Number (surveys only)","Matrix Group Name","Matrix Ranking?","Field Annotation"]
DOMAINS=["Labour Market & Employment","Education & Skills","Health & Social Care","Crime & Justice","Business & Productivity","Poverty, Wealth & Living Standards","Housing & Planning","Migration & Demographics","Environment & Agriculture","Public Finance & Taxation","Data Infrastructure & Methodology","Unclear from Register Entry"]
PURPOSES=["Descriptive Monitoring","Outcome Tracking","Life-Course / Trajectory Analysis","Service Interaction / Systems Analysis","Policy Evaluation / Impact Analysis","Risk Prediction / Early Identification","Methodological / Infrastructure Research","Unclear from Register Entry"]
COMPONENTS=("dom","purp","covid","equity"); KEY={"dom":"domains","purp":"purposes","covid":"covid","equity":"equity"}

# Structured owner-screening allow-list.  Derived from the frozen owner data
# dictionary and asserted against it by the test suite.  Every other exported
# column -- notes, free-text bases, descriptive blocks -- is ignored here,
# because reading owner prose is deferred through the owner-analysis gate.
OWNER_FIT_FIELDS=("po_d01_fit","po_d02_fit","po_d03_fit","po_d04_fit","po_p01_fit","po_p02_fit")
OWNER_TAG_FIELDS=("po_t01_correct","po_t02_correct")
OWNER_VIS_FIELDS=("po_d01_vis","po_d02_vis","po_d03_vis","po_d04_vis","po_p01_vis","po_p02_vis","po_t01_vis","po_t02_vis")
# field -> (valid codes, qualifying codes, reason).  An empty reason means the
# field is read for validity and context only and can never qualify a record.
OWNER_RADIO_FIELDS={
    **{f:((1,2,3),(2,3),"fit_verdict") for f in OWNER_FIT_FIELDS},
    **{f:((0,1,2),(0,2),"tag_correctness") for f in OWNER_TAG_FIELDS},
    **{f:((0,1,2,3),(),"") for f in OWNER_VIS_FIELDS},
    "po_sufficiency":((1,2,3),(2,3),"public_sufficiency"),
    "po_taxonomy_fit":((1,2,3),(),""),
}
# checkbox field -> (exported option codes, reason).  REDCap exports one column
# per option, named field___code, holding "0" or "1".
OWNER_CHECKBOX_FIELDS={
    "po_miss_domains":(tuple(range(1,12)),"missing_label"),
    "po_miss_purposes":(tuple(range(1,8)),"missing_label"),
    "po_miss_tags":((1,2),"missing_label"),
    "po_tax_issue":((1,2,5),"taxonomy_issue"),
}
OWNER_REASON_ORDER=("fit_verdict","tag_correctness","missing_label","public_sufficiency","taxonomy_issue")

def load_json(name):
    p=FIXTURES/name
    if not p.exists(): raise FileNotFoundError(f"Synthetic fixture required: {p}; no production fallback exists.")
    return json.loads(p.read_text(encoding="utf-8"))
def stable_id(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:12]
def canonical(values,vocabulary): return sorted(values,key=lambda x:(0,vocabulary.index(x)) if x in vocabulary else (1,str(x)))
def qa_flags(c):
    flags=[]
    for k,vocab,empty,excess in (("domains",DOMAINS,"empty_domains",None),("purposes",PURPOSES,"empty_purposes","too_many_purposes")):
        values=c.get(k,[])
        if not values: flags.append(empty)
        if excess and len(values)>2: flags.append(excess)
        if any(x not in vocab for x in values): flags.append(f"unknown_{k}_label")
        if "Unclear from Register Entry" in values and len(values)>1: flags.append(f"unclear_combined_{k}")
    for tag in ("covid","equity"):
        if c.get(tag) not in {"Applied","Not applied"}: flags.append(f"invalid_{tag}_tag")
    return flags
def candidate_content(c): return {"domains":canonical(c.get("domains",[]),DOMAINS),"purposes":canonical(c.get("purposes",[]),PURPOSES),"covid":c.get("covid"),"equity":c.get("equity")}
def no_majority_components(case):
    """Components where no label reached two of three scratch coders.

    Section 9.1 compares the model against the labelwise two-of-three human
    reference.  Where that reference is empty the model differs from it by
    construction, not because anyone disagreed about a rule, so these records
    are adjudicated but analysed as their own stratum (ADJ-038).  What the
    reviewer sees is unaffected: the displayed options are the coders' own
    classifications, so the comparison on the form is well formed.

    A binary tag always has a majority among three coders, so only the label
    components can qualify, and with no coder panel the question does not
    arise.
    """
    coders=[c for c in case["classifications"] if c.get("source_type")=="scratch"]
    if len(coders)<3: return []
    return [comp for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES))
            if not any(sum(lab in (c.get(KEY[comp]) or []) for c in coders)>=2 for lab in vocab)]
def model_differing_components(case):
    """Components where the production model differs from the two-of-three reference.

    This is what route-1 eligibility rests on, and so what the stratum must be
    read against.  It is not the same as the components whose displayed options
    differ: coders can split on a component where the model matches the
    reference, which shows on the form but is not a model-human difference.
    """
    model=next((c for c in case["classifications"] if c.get("source_type")=="fable"),None)
    coders=[c for c in case["classifications"] if c.get("source_type")=="scratch"]
    if model is None or not coders: return []
    out=[]
    for comp in COMPONENTS:
        key=KEY[comp]
        if comp in ("dom","purp"):
            vocab=DOMAINS if comp=="dom" else PURPOSES
            majority={l for l in vocab if sum(l in (c.get(key) or []) for c in coders)*2>=len(coders)+1}
            if set(model.get(key) or [])!=majority: out.append(comp)
        else:
            applied=sum(c.get(comp)=="Applied" for c in coders)*2>=len(coders)+1
            if (model.get(comp)=="Applied")!=applied: out.append(comp)
    return out
def package_stratum(case,package):
    """1 standard, 2 mixed, 3 eligible only where the reference was empty.

    Stratum 3 is the record that is in adjudication only because the two-of-three
    reference was empty, so the model differs from it by construction (ADJ-038).
    It is read against the components the model differs on, not the components
    whose displayed options differ: an earlier version used the displayed ones
    and counted 11 records where the logged definition counts 22, because a
    record eligible only on empty references can still display a coder split
    elsewhere.

    It is analytic, not operational: nothing on the form reads it, and it is
    deliberately kept out of the REDCap record, because a hidden field saying
    the coders did not converge is source information sitting in the reviewer's
    own export.
    """
    differ=set(model_differing_components(case))
    if not differ: return 1
    empty=set(no_majority_components(case))
    return 3 if differ<=empty else (2 if differ&empty else 1)
def package_case(case,seed=20260921):
    kept=[x for x in case["classifications"] if x["source_type"] in {"fable","scratch"}]
    groups={}
    for c in kept:
        content=candidate_content(c); groups.setdefault("C_"+stable_id(content),content)
    ids=sorted(groups); random.Random(f"{seed}:{case['assignment_id']}").shuffle(ids)
    candidates=[{"candidate_id":i,**groups[i]} for i in ids]; interpretations={}
    for comp in COMPONENTS:
        keyed={}
        for c in candidates: keyed.setdefault(json.dumps(c[KEY[comp]],sort_keys=True),[]).append(c["candidate_id"])
        interpretations[comp]=[{"interpretation_id":f"{comp.upper()}_{n}","value":json.loads(v),"candidate_ids":cids} for n,(v,cids) in enumerate(keyed.items(),1)]
    identity={"assignment_id":case["assignment_id"],"record_id":case["record_id"],"candidates":candidates}
    return {"assignment_id":case["assignment_id"],"record_id":case["record_id"],"title":case.get("title",""),"datasets":case.get("datasets",""),"package_id":"PKG_"+stable_id(identity),"seed":seed,"candidates":candidates,"interpretations":interpretations,"qa_flags":sorted({f for c in kept for f in qa_flags(c)})}
def component_labels(package,comp):
    ids={x["interpretation_id"] for x in package["interpretations"][comp]}; labels={}
    for x in package["interpretations"][comp]:
        for label in x["value"]: labels.setdefault(label,set()).add(x["interpretation_id"])
    return ids,labels
def issue(value,choices,label): return [] if value in choices else [f"{label} required"]
# ---------------------------------------------------------------------------
# Lean Stage 1 (ADJ-036).  §9.2 asks five things of a comparative record: the
# labels that differ (generated), whether the public entry can distinguish the
# interpretations, whether a recognised or plausible boundary is involved,
# whether more than one interpretation stays defensible, and whether any set
# conflicts with an explicit rule.  ADJ-037 adds a blind best-supported choice
# for each component that actually differs; sufficiency is derived (ADJ-042).  The
# owner-only single-set path keeps the per-label checks §9.2 requires there.
# ---------------------------------------------------------------------------
COMPONENT_CODE={"dom":1,"purp":2,"covid":3,"equity":4}
# Option codes 1-4 are the stable internal slot codes, shown as Options A-D.
OPTION_LETTERS="ABCD"
BEST_CANNOT_DETERMINE=6; DEFENSIBLE_NONE=0; DEFENSIBLE_CANNOT_JUDGE=9
COMPARATIVE_RECORD_KEYS=("adj_rule_conflict","adj_rule_conflict_scope","adj_conflict_rule_cited","adj_conflict_rule_other","adj_rule_conflict_note",
                         "adj_boundary_same_rule","adj_conflict_second","adj_conflict_third","adj_conflict_fourth","adj_conflict_fifth","adj_conflict_sixth")+tuple(
                         k for n in (2,3,4,5,6) for k in (f"adj_conflict{n}_scope",f"adj_conflict_rule{n}_cited",f"adj_conflict_rule{n}_other",f"adj_rule_conflict_note{n}"))
COMPARATIVE_COMPONENT_KEYS=("evidence","best","defensible","conflict_slots")
# The frozen rules carry no identifiers.  The labels already ticked locate the
# rule; the rule type says which part of the taxonomy it is (ADJ-042).
# Every citable rule in the frozen taxonomy carries a permanent ID (ADJ-046),
# so a finding cites a specific text the second reviewer can read.
RULE_OTHER=999; RULE_CATALOGUE_VERSION="rulecat-0.1"
def rule_catalogue():
    path=ROOT/"instruments"/"rule_catalogue.csv"
    if not path.exists(): raise FileNotFoundError(f"rule catalogue required: {path}; run build_rule_catalogue.py")
    with path.open(encoding="utf-8",newline="") as file:
        return [{**r,"code":int(r["code"])} for r in csv.DictReader(file)]
def rule_codes(): return {r["code"] for r in rule_catalogue()}
# The visible label is the rule, not its ID: the ID is the stored key and the
# reference's audit handle, and reading it off a dropdown helped nobody
# (ADJ-049).  Names lead with Domains, Purposes, Tags or Principles, matching
# the mechanism vocabulary in Stage 2.
def rule_choices(): return " | ".join(f"{r['code']}, {r['name']}" for r in rule_catalogue())+f" | {RULE_OTHER}, Other rule or coding instruction"
def validate_rule_cited(value,other,label):
    out=issue(value,rule_codes()|{RULE_OTHER},f"{label} cited rule")
    if value==RULE_OTHER and not(other and str(other).strip()): out.append(f"{label} Other rule needs a description")
    return out
SINGLE_SET_KEYS=("label_assessments","tag_assessments")+tuple(f"adj_{c}_additional_label_{x}" for c in ("dom","purp") for x in ("state","ids","note"))
def comparative_components(p): return [c for c in COMPONENTS if len(p["interpretations"][c])>1]
def validate_label_assessment(a):
    """Single-set path: is this proposed label supported, and does it breach a rule?"""
    out=issue(a.get("support"),{1,2,3},"label support"); conflict=a.get("rule_conflict"); out+=issue(conflict,{0,1,2},"label rule-conflict state")
    if conflict==1:
        out+=validate_rule_cited(a.get("rule_cited"),a.get("rule_other"),"label conflict")
        if not a.get("rule_note"): out.append("rule conflict needs explanation")
    if conflict==2 and not a.get("rule_note"): out.append("cannot-assess conflict needs explanation")
    return out
def validate_tag_assessment(a):
    out=issue(a.get("support"),{1,2,3},"tag support"); conflict=a.get("rule_conflict"); out+=issue(conflict,{0,1,2},"tag conflict")
    if conflict==1:
        out+=validate_rule_cited(a.get("rule_cited"),a.get("rule_other"),"tag conflict")
        if not a.get("rule_note"): out.append("tag conflict needs explanation")
    if conflict==2 and not a.get("rule_note"): out.append("tag cannot-assess conflict needs explanation")
    state=a.get("supported_status"); out+=issue(state,{0,1,2},"tag alternative-status assessment")
    if state in {1,2} and not a.get("supported_status_note"): out.append("tag alternative-status needs explanation")
    return out
CONFLICT_BLOCKS=(1,2,3,4,5,6); EXTRA_CONFLICTS=CONFLICT_BLOCKS[1:]
CONFLICT_ASK={2:"adj_conflict_second",3:"adj_conflict_third",4:"adj_conflict_fourth",5:"adj_conflict_fifth",6:"adj_conflict_sixth"}
CONFLICT_ORDINAL={1:"first",2:"second",3:"third",4:"fourth",5:"fifth",6:"sixth"}
def conflict_block(n):
    """Field names for the nth rule conflict.

    One conflict is one rule (ADJ-054).  Options breaching the same rule are
    ticked together within a block; an option breaching two rules occupies two.
    Six blocks are declared and each opens only once the one before it is
    filled, so the reviewer is never asked about a conflict that does not exist
    and never runs out of room (ADJ-055).  The first is named differently and
    also carries Cannot judge.
    """
    if n==1:
        return {"ask":"adj_rule_conflict","scope":"adj_rule_conflict_scope","cited":"adj_conflict_rule_cited",
                "other":"adj_conflict_rule_other","note":"adj_rule_conflict_note",
                "slots":lambda c:f"adj_{c}_conflict_slots","labels":lambda c:f"adj_{c}_conflict_labels"}
    return {"ask":CONFLICT_ASK[n],"scope":f"adj_conflict{n}_scope","cited":f"adj_conflict_rule{n}_cited",
            "other":f"adj_conflict_rule{n}_other","note":f"adj_rule_conflict_note{n}",
            "slots":lambda c:f"adj_{c}_conflict{n}_slots","labels":lambda c:f"adj_{c}_conflict{n}_labels"}
_RULE_INDEX=None
def rule_index():
    global _RULE_INDEX
    if _RULE_INDEX is None: _RULE_INDEX={r["code"]:r for r in rule_catalogue()}
    return _RULE_INDEX
def rule_component(code):
    """The component a cited rule belongs to, or None where it names no label.

    A category rule already names its label: `Domains: Poverty, Wealth &
    Living Standards - definition` says both the component and the label. Only
    the assignment principles, which apply to any layer, and Other leave the
    label open (ADJ-055).
    """
    r=rule_index().get(code)
    if not r or r["scope"]!="category": return None
    if r["kind"]=="Research Domain": return "dom"
    if r["kind"]=="Analytical Purpose": return "purp"
    return "covid" if r["category"].startswith("COVID") else "equity"
def rule_label(code):
    r=rule_index().get(code)
    return r["category"] if r and r["scope"]=="category" else None
def label_free_rules():
    """Cited rules that do not name a label, so the labels question is asked."""
    return sorted({c for c,r in rule_index().items() if r["scope"]=="principle"}|{RULE_OTHER})
def conflict_keys(n):
    b=conflict_block(n)
    return [b["ask"],b["scope"],b["cited"],b["other"],b["note"]]+[b["slots"](c) for c in COMPONENTS]+[b["labels"](c) for c in ("dom","purp")]
def validate_extra_conflicts(r):
    """Conflicts after the first, each naming one rule not already cited.

    A record can show several options failing on different grounds, and a
    single option can breach two rules at once, so a citation that is not tied
    to its own options cannot be attributed later.  Each block is asked only
    once the one before it is recorded, so a record with one conflict is
    unaffected.
    """
    out=[]; cited=[r.get("adj_conflict_rule_cited")]; askable=r.get("adj_rule_conflict")==1
    for n in EXTRA_CONFLICTS:
        b=conflict_block(n)
        if not askable:
            if any(k in r for k in conflict_keys(n)): out.append(f"conflict {n} is only recorded once conflict {n-1} is")
            continue
        ask=r.get(b["ask"]); out+=issue(ask,{0,1},f"conflict {n} question")
        if ask!=1:
            if any(k in r for k in conflict_keys(n)[1:]): out.append(f"conflict {n} details are only recorded where conflict {n} is reported")
            askable=False; continue
        out+=validate_rule_cited(r.get(b["cited"]),r.get(b["other"]),f"conflict {n}")
        if r.get(b["cited"]) in cited and r.get(b["cited"])!=RULE_OTHER:
            out.append(f"conflict {n} must name a rule not already cited")
        cited.append(r.get(b["cited"]))
        scope=set(r.get(b["scope"],[]))
        if not scope or not scope<=set(COMPONENT_CODE.values()): out.append(f"conflict {n} needs its component scope")
        out+=validate_cited_component(r.get(b["cited"]),scope,f"conflict {n}")
        if not r.get(b["note"]): out.append(f"conflict {n} needs explanation")
    return out
def validate_cited_component(code,scope,tag):
    """A category rule can only be breached in its own component.

    Requiring the rule's component merely to be present let a Purposes rule be
    scoped to Purposes and the equity tag at once, so an equity option was
    recorded as breaching a Purposes rule and no error was raised.  One
    conflict is one rule, so the scope is exactly that rule's component; only a
    principle, which applies to any layer, and Other span components.
    """
    comp=rule_component(code)
    if comp is not None and scope!={COMPONENT_CODE[comp]}:
        return [f"{tag} cites a {COMPONENT_LABEL[comp]} rule, so its scope is {COMPONENT_LABEL[comp]} alone"]
    return []
def validate_boundary(r):
    """Record-level boundary judgement, asked for every record.

    Where the reviewer has already recorded a rule conflict and ticks a
    documented boundary, one question asks whether it is the same rule; a Yes
    skips re-entering the rule type and explanation (ADJ-042).
    """
    states=set(r.get("adj_boundary",[])); scope=set(r.get("adj_boundary_scope",[])); out=[]
    if not states or not states<={0,1,2,9}: out.append("boundary state required")
    if (0 in states or 9 in states) and len(states)!=1: out.append("no/cannot boundary state is exclusive")
    if states&{1,2}:
        if not scope or not scope<=set(COMPONENT_CODE.values()): out.append("recognised/plausible boundary needs its component scope")
    elif scope: out.append("boundary scope is only recorded for a recognised or plausible boundary")
    shortcut=r.get("adj_rule_conflict")==1 and 1 in states; same=r.get("adj_boundary_same_rule")
    if shortcut: out+=issue(same,{0,1},"same-rule-as-conflict answer")
    elif "adj_boundary_same_rule" in r: out.append("same-rule question is only asked for a documented boundary alongside a rule conflict")
    cites=1 in states and not(shortcut and same==1)
    if cites: out+=validate_rule_cited(r.get("adj_boundary_rule_cited"),r.get("adj_boundary_rule_other"),"recognised boundary")
    elif "adj_boundary_rule_cited" in r: out.append("boundary rule is only recorded for a documented boundary that is not the conflict rule")
    if (cites or 2 in states) and not r.get("adj_boundary_note"): out.append("recognised/plausible boundary needs explanation")
    return out
def yes_no_with_note(r,field,note,label):
    value=r.get(field); out=issue(value,{0,1},label)
    if value==1 and not r.get(note): out.append(f"{label} needs explanation")
    return out
def validate_submission(r,p):
    out=[]
    if r.get("assignment_id")!=p["assignment_id"]: out.append("assignment mismatch")
    if r.get("package_id")!=p["package_id"]: out.append("package mismatch")
    if r.get("adj_diff_check") not in {1,2}: out.append("generated-difference check required")
    if r.get("adj_diff_check")==2: out.append("generation error blocks Stage 1 completion")
    out+=validate_boundary(r)
    masking=r.get("adj_masking_failure"); out+=issue(masking,{0,1,2},"masking failure")
    if masking in {1,2} and not r.get("adj_masking_note"): out.append("masking failure needs explanation")
    out+=yes_no_with_note(r,"adj_other_concern","adj_other_concern_note","other concern")
    out+=yes_no_with_note(r,"adj_stage1_unresolved","adj_stage1_unresolved_note","unresolved at Stage 1")
    if any(k.endswith(("_best_skipped","_best_outcome","_multiple_defensible","_insufficient_support")) for k in r): out.append("derived indicators cannot be supplied")
    if any(k.endswith("_adequacy") for k in r): out.append("sufficient support is derived, not asked (ADJ-042)")
    comps=comparative_components(p)
    if comps:
        if any(k in r for k in SINGLE_SET_KEYS): out.append("single-set questions do not apply when displayed sets compete")
        for c in COMPONENTS:
            pre=f"adj_{c}_"
            if c not in comps:
                if any(pre+x in r for x in COMPARATIVE_COMPONENT_KEYS if x!="conflict_slots"): out.append(f"{c}: comparative questions do not apply to a component that does not differ")
                continue
            options=set(range(1,len(p["interpretations"][c])+1))
            # Evidence: how much the entry supports assessing these options.
            evidence=r.get(pre+"evidence"); out+=issue(evidence,{1,2,3,4},f"{c}: evidence")
            # Relative support: tick every option tied for best, or cannot determine.
            best=set(r.get(pre+"best",[]))
            if evidence==3:
                if best: out.append(f"{c}: best-supported is not asked when there is too little information")
            elif not best: out.append(f"{c}: best-supported answer required")
            elif BEST_CANNOT_DETERMINE in best:
                if len(best)!=1: out.append(f"{c}: cannot determine is exclusive")
            elif not best<=options: out.append(f"{c}: best-supported names an option that is not displayed")
            # Defensibility: every option reasonable under the rules.
            defensible=set(r.get(pre+"defensible",[]))
            if not defensible: out.append(f"{c}: defensibility answer required")
            elif defensible&{DEFENSIBLE_NONE,DEFENSIBLE_CANNOT_JUDGE}:
                if len(defensible)!=1: out.append(f"{c}: none and cannot judge are exclusive")
            elif not defensible<=options: out.append(f"{c}: defensible names an option that is not displayed")
        conflict=r.get("adj_rule_conflict"); rscope=set(r.get("adj_rule_conflict_scope",[])); out+=issue(conflict,{0,1,2},"rule-conflict judgement")
        if conflict==1:
            if not rscope or not rscope<=set(COMPONENT_CODE.values()): out.append("rule conflict needs its component scope")
            out+=validate_rule_cited(r.get("adj_conflict_rule_cited"),r.get("adj_conflict_rule_other"),"rule conflict")
            out+=validate_cited_component(r.get("adj_conflict_rule_cited"),rscope,"rule conflict")
            if not r.get("adj_rule_conflict_note"): out.append("rule conflict needs explanation")
            out+=validate_extra_conflicts(r)
        elif rscope: out.append("rule-conflict scope is only recorded for a conflict")
        if conflict!=1: out+=validate_extra_conflicts(r)
        if conflict==2 and not r.get("adj_rule_conflict_note"): out.append("cannot-judge rule conflict needs explanation")
        for c in COMPONENTS:
            options=set(range(1,len(p["interpretations"][c])+1))
            # A label the cited rule already names is not asked for again, so
            # the two can never disagree (ADJ-055).  Where the rule names no
            # label the question stands, and the answer comes from the whole
            # vocabulary rather than the displayed labels, because a rule can
            # be breached by omitting a label that is not on screen.
            vocab=set(DOMAINS) if c=="dom" else set(PURPOSES) if c=="purp" else set()
            for n in CONFLICT_BLOCKS:
                b=conflict_block(n)
                active=(conflict==1) if n==1 else r.get(b["ask"])==1
                in_scope_n=active and COMPONENT_CODE[c] in set(r.get(b["scope"],[]))
                slots_n=set(r.get(b["slots"](c),[]))
                if in_scope_n:
                    if not slots_n or not slots_n<=options: out.append(f"{c}: conflict {n} needs the conflicting option(s)")
                elif slots_n: out.append(f"{c}: conflict {n} options are only recorded for that conflict in a scoped component")
                if c in ("dom","purp"):
                    labels_n=set(r.get(b["labels"](c),[])); named=rule_component(r.get(b["cited"])) is not None
                    if in_scope_n and not named:
                        if not labels_n or not labels_n<=vocab: out.append(f"{c}: conflict {n} needs the label(s) concerned")
                    elif labels_n: out.append(f"{c}: conflict {n} labels are only recorded where the cited rule names none")
    else:
        if any(k in r for k in COMPARATIVE_RECORD_KEYS) or any(f"adj_{c}_{x}" in r for c in COMPONENTS for x in COMPARATIVE_COMPONENT_KEYS+("conflict_labels",)):
            out.append("comparative questions do not apply to a single displayed set")
        assessments=r.get("label_assessments",{})
        for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
            ids,labels=component_labels(p,comp)
            for label in labels:
                a=assessments.get(comp,{}).get(label)
                if a is None: out.append(f"{comp}: displayed label {label!r} requires assessment")
                else: out+=[f"{comp}: {x}" for x in validate_label_assessment(a)]
            state=r.get(f"adj_{comp}_additional_label_state"); selected=set(r.get(f"adj_{comp}_additional_label_ids",[])); absent=set(vocab)-set(labels)
            out+=issue(state,{0,1,2},f"{comp}: additional-label state")
            if state==1 and(not selected or not selected<=absent or not r.get(f"adj_{comp}_additional_label_note")): out.append(f"{comp}: additional labels need permitted IDs and note")
            if state in {0,2} and selected: out.append(f"{comp}: additional None/Cannot determine has no IDs")
            if state==2 and not r.get(f"adj_{comp}_additional_label_note"): out.append(f"{comp}: additional Cannot determine needs note")
            for label in selected:
                a=assessments.get(comp,{}).get(label)
                if a is None: out.append(f"{comp}: selected additional label {label!r} needs assessment")
                else: out+=[f"{comp}: {x}" for x in validate_label_assessment(a)]
        for comp in ("covid","equity"):
            a=r.get("tag_assessments",{}).get(comp)
            if a is None: out.append(f"{comp}: tag assessment required")
            else: out+=[f"{comp}: {x}" for x in validate_tag_assessment(a)]
    if r.get("adj_stage1_affirmed")!=1: out.append("Stage 1 completion not affirmed")
    return out
def default_valid_submission(p):
    """A minimal valid response: the shortest path a reviewer can take."""
    r={"assignment_id":p["assignment_id"],"package_id":p["package_id"],"adj_diff_check":1,"adj_boundary":[0],"adj_masking_failure":0,"adj_other_concern":0,"adj_stage1_unresolved":0,"adj_stage1_note":"Synthetic reviewer note.","adj_stage1_affirmed":1}
    comps=comparative_components(p)
    if comps:
        r["adj_rule_conflict"]=0
        for c in comps: r.update({f"adj_{c}_evidence":1,f"adj_{c}_best":[1],f"adj_{c}_defensible":[1]})
    else:
        r["label_assessments"]={comp:{label:{"support":1,"rule_conflict":0} for label in component_labels(p,comp)[1]} for comp in ("dom","purp")}
        r["tag_assessments"]={comp:{"support":1,"rule_conflict":0,"supported_status":0} for comp in ("covid","equity")}
        for comp in ("dom","purp"): r[f"adj_{comp}_additional_label_state"]=0; r[f"adj_{comp}_additional_label_ids"]=[]
    return r
def derive_sufficiency(ratings):
    if ratings is None:return {"broad":9,"strict":9}
    if len(ratings)!=3 or any(x not in {"Sufficient","Partially sufficient","Insufficient"} for x in ratings):return {"broad":8,"strict":8}
    return {"broad":int(sum(x in {"Sufficient","Partially sufficient"} for x in ratings)>=2),"strict":int(sum(x=="Sufficient" for x in ratings)>=2)}
def owner_code(field,value):
    """Normalise one exported cell.  Blank or absent means no response, not zero."""
    if value is None: return None
    text=str(value).strip()
    if text=="": return None
    try: return int(text)
    except ValueError: raise ValueError(f"owner screening: non-numeric code {value!r} for {field}") from None
def owner_trigger(row):
    """Screen one export-shaped owner response row against the structured allow-list.

    Only allow-listed structured fields are read.  Unknown or invalid codes
    raise; they are never silently treated as absent.  Every key that is not on
    the allow-list is returned in "ignored_fields" so the gate stays auditable.
    """
    found=set(); ignored=[]; visibility=False; taxonomy_fit=None; taxonomy_issue_selected=False
    for key in row:
        base,sep,option=key.partition("___")
        if sep:
            if base in OWNER_RADIO_FIELDS:
                raise ValueError(f"owner screening: {base} is a single-answer field and has no checkbox export column {key}")
            if base not in OWNER_CHECKBOX_FIELDS:
                ignored.append(key); continue
            codes,reason=OWNER_CHECKBOX_FIELDS[base]
            try: opt=int(option.strip())
            except ValueError: raise ValueError(f"owner screening: non-numeric checkbox option in {key}") from None
            if opt not in codes: raise ValueError(f"owner screening: {opt} is not a choice code of {base}")
            value=owner_code(key,row[key])
            if value is None: continue
            if value not in (0,1): raise ValueError(f"owner screening: checkbox column {key} exports 0 or 1, not {row[key]!r}")
            if value==1:
                found.add(reason)
                if base=="po_tax_issue": taxonomy_issue_selected=True
            continue
        if key in OWNER_CHECKBOX_FIELDS:
            raise ValueError(f"owner screening: {key} is a checkbox and exports as {key}___<option> columns")
        if key not in OWNER_RADIO_FIELDS:
            ignored.append(key); continue
        valid,qualifying,reason=OWNER_RADIO_FIELDS[key]
        value=owner_code(key,row[key])
        if value is None: continue
        if value not in valid: raise ValueError(f"owner screening: {row[key]!r} is not a choice code of {key}")
        if key in OWNER_VIS_FIELDS: visibility=True; continue
        if key=="po_taxonomy_fit": taxonomy_fit=value; continue
        if value in qualifying: found.add(reason)
    reasons=[x for x in OWNER_REASON_ORDER if x in found]
    status="unresolved" if taxonomy_fit in (2,3) and not taxonomy_issue_selected else "not_applicable"
    return {"qualifies":bool(reasons),"reasons":reasons,"taxonomy_fit_only_status":status,"visibility_diagnostic_only":visibility and not reasons,"ignored_fields":sorted(ignored)}
def aggregate_independence(findings,mapping):
    for r in findings:
        if type(r["pre_reveal"]) is not int or r["pre_reveal"] not in {0,1,2}:raise ValueError("pre_reveal must be 0 No, 1 Yes, or 2 Unknown")
    def summaries(mapping):
        groups={}
        for r in findings:
            mech=mapping.get(r["mechanism_versioned"],r["mechanism_versioned"])
            code=r.get("mechanism_code") or (r.get("mechanism") or {}).get("code")
            if code is None: raise ValueError("mechanism code required to distinguish general from pair-specific recurrence")
            code=int(code)
            if code in GENERAL_MECHANISM_CODES:
                dom=tuple(finding_label_names(r.get("dom_labels",[]),DOMAINS))
                purp=tuple(finding_label_names(r.get("purp_labels",[]),PURPOSES))
                if not(dom or purp): raise ValueError("general mechanism needs its affected labels before aggregation")
                mech=f"{mech} | dom:{'; '.join(dom)} | purp:{'; '.join(purp)}"
            groups.setdefault(mech,[]).append(r)
        result={}
        for mech,rows in groups.items():
            records={r["record_id"] for r in rows}; streams={r["stream"] for r in rows if r["pre_reveal"]==1}; pairs={(r["stream"],r["signal_ref"]) for r in rows if r["pre_reveal"]==1}; inclusive=len(records)>=2 or len(streams)>=2; adjudicator_only=len(records)==1 and streams and streams<={"primary","secondary"} and len(streams)>=2
            result[mech]={"distinct_record_count":len(records),"pre_reveal_stream_signal_count":len(pairs),"independent_conservative":inclusive and not adjudicator_only,"independent_inclusive":inclusive}
        return result
    return {"pre_harmonisation":summaries({}),"post_harmonisation":summaries(mapping)}
CORRECTION_KEYS=("field","original_value","corrected_value","reason","author","date")
REFLECTION_KEYS=("scope","reflection","author","date")

def derive_stage1(response,package):
    """Derived, read-only Stage 1 indicators.  Never reviewer-entered.

    For each component that differs:
    * best_skipped: 1 where best-supported was not asked because the reviewer
      judged there was too little information; separates a skip from a gap.
    * best_outcome: 1 unique best, 2 tie among a proper subset, 3 all options
      equally supported, 4 cannot determine, 9 not asked.  Read off the ticks,
      so the tied options themselves stay in the response.
    * multiple_defensible: 1 when two or more options are ticked defensible.
    * insufficient_support: 1 where no option is sufficiently supported, read
      as too little information or no defensible option; 9 where either answer
      is cannot judge; otherwise 0.  Replaces the asked question (ADJ-042).
    """
    derived={}
    for c in comparative_components(package):
        n=len(package["interpretations"][c]); pre=f"adj_{c}_"
        best=set(response.get(pre+"best",[])); defensible=set(response.get(pre+"defensible",[]))-{DEFENSIBLE_NONE,DEFENSIBLE_CANNOT_JUDGE}
        skipped=response.get(pre+"evidence")==3
        if skipped: outcome=9
        elif best=={BEST_CANNOT_DETERMINE}: outcome=4
        elif len(best)==1: outcome=1
        elif len(best)==n: outcome=3
        else: outcome=2
        ticked=set(response.get(pre+"defensible",[])); evidence=response.get(pre+"evidence")
        if evidence==4 or ticked=={DEFENSIBLE_CANNOT_JUDGE}: insufficient=9
        elif evidence==3 or ticked=={DEFENSIBLE_NONE}: insufficient=1
        else: insufficient=0
        derived.update({pre+"best_skipped":int(skipped),pre+"best_outcome":outcome,pre+"multiple_defensible":int(len(defensible)>=2),pre+"insufficient_support":insufficient})
    return derived
def canonical_bytes(value): return json.dumps(value,sort_keys=True,separators=(",",":")).encode("utf-8")
def verify_snapshot(store):
    """Recompute the preserved-snapshot hash and raise if it does not match."""
    if "snapshot" not in store: raise PermissionError("no preserved snapshot to verify")
    blob=canonical_bytes(store["snapshot"])
    if store.get("snapshot_bytes")!=blob or hashlib.sha256(blob).hexdigest()!=store.get("snapshot_hash"):
        raise PermissionError("preserved snapshot failed its integrity check")
    return store["snapshot_hash"]
def preserve(r,p,store):
    if "snapshot" in store:
        store.setdefault("events",[]).append({"event":"preserve_rejected_existing_snapshot","at":datetime.now(timezone.utc).isoformat()});raise RuntimeError("append-only preservation rejects a second snapshot")
    if p["qa_flags"]:raise ValueError("QA flags block preservation: "+", ".join(p["qa_flags"]))
    problems=validate_submission(r,p)
    if problems:raise ValueError("; ".join(problems))
    snapshot={"assignment_id":p["assignment_id"],"package_id":p["package_id"],"presented":copy.deepcopy(p),"response":copy.deepcopy(r),"derived":derive_stage1(r,p)}
    blob=canonical_bytes(snapshot); token=hashlib.sha256(blob).hexdigest()
    # Store the hashed bytes and a copy detached from the caller, so later
    # mutation of the submitted response cannot reach the preserved snapshot.
    store["snapshot"]=json.loads(blob.decode("utf-8")); store["snapshot_bytes"]=blob; store["snapshot_hash"]=token
    store.setdefault("events",[]).append({"event":"preserved","hash":token,"at":datetime.now(timezone.utc).isoformat()})
    return token
def require_entry_keys(kind,entry,keys):
    if not isinstance(entry,dict): raise ValueError(f"{kind} entry must be a mapping")
    missing=[k for k in keys if k not in entry]
    if missing: raise ValueError(f"{kind} requires {', '.join(missing)}")
    unknown=sorted(set(entry)-set(keys))
    if unknown: raise ValueError(f"{kind} rejects unknown keys: {', '.join(unknown)}")
def require_text(kind,entry,key):
    if not isinstance(entry[key],str) or not entry[key].strip(): raise ValueError(f"{kind} requires non-empty {key}")
def require_iso_date(kind,entry,key="date"):
    require_text(kind,entry,key)
    try: datetime.fromisoformat(entry[key].strip().replace("Z","+00:00"))
    except ValueError: raise ValueError(f"{kind} {key} is not ISO 8601: {entry[key]!r}") from None
def record_correction(store,h,entry):
    """Append a clerical/transcription correction.  The snapshot is never altered."""
    if store.get("snapshot_hash")!=h:raise PermissionError("correction snapshot mismatch")
    verify_snapshot(store)
    require_entry_keys("correction",entry,CORRECTION_KEYS)
    for key in ("field","reason","author"): require_text("correction",entry,key)
    require_iso_date("correction",entry)
    response=store["snapshot"]["response"]
    if entry["field"] not in response: raise ValueError(f"correction field {entry['field']!r} is not in the preserved response")
    if response[entry["field"]]!=entry["original_value"]: raise ValueError(f"correction original_value does not match the preserved value of {entry['field']!r}")
    store.setdefault("adj_correction",[]).append(copy.deepcopy({"snapshot_hash":h,**entry}))
    store.setdefault("events",[]).append({"event":"correction_recorded","field":entry["field"],"at":datetime.now(timezone.utc).isoformat()})
def record_reflection(store,h,entry):
    """Append a changed-judgement reflection.  It never overwrites Stage 1."""
    if store.get("snapshot_hash")!=h:raise PermissionError("reflection snapshot mismatch")
    verify_snapshot(store)
    require_entry_keys("reflection",entry,REFLECTION_KEYS)
    for key in ("scope","reflection","author"): require_text("reflection",entry,key)
    require_iso_date("reflection",entry)
    if entry["scope"] not in COMPONENTS and entry["scope"] not in store["snapshot"]["response"]:
        raise ValueError(f"reflection scope {entry['scope']!r} is neither a component nor a preserved field")
    store.setdefault("adj_reflection",[]).append(copy.deepcopy({"snapshot_hash":h,**entry}))
    store.setdefault("events",[]).append({"event":"reflection_recorded","scope":entry["scope"],"at":datetime.now(timezone.utc).isoformat()})
def reveal(a,p,h,payload,store,case,simulate_partial=False):
    if "snapshot" not in store:raise PermissionError("premature reveal rejected: no preserved snapshot")
    verify_snapshot(store)
    if(a,p,h)!=(store["snapshot"]["assignment_id"],store["snapshot"]["package_id"],store["snapshot_hash"]):raise PermissionError("assignment, package, or snapshot mismatch")
    package=store["snapshot"]["presented"]
    verified_source_slots(case,package)
    if payload.get(a)!=reveal_fields(case,package): raise PermissionError("reveal payload does not match the original source classifications")
    if simulate_partial:
        store.setdefault("exposure_history",[]).append({"assignment_id":a,"source_information":"synthetic source-reveal mapping potentially accessible","accessibility":"potential","viewing":"unknown","extent":"unknown","at":datetime.now(timezone.utc).isoformat()});store.setdefault("events",[]).append({"event":"reveal_failed_partial","at":datetime.now(timezone.utc).isoformat()});raise RuntimeError("simulated partial reveal failure")
    store.setdefault("events",[]).append({"event":"reveal_recovered" if store.get("exposure_history") else "reveal_complete","at":datetime.now(timezone.utc).isoformat()});return {"assignment_id":a,"package_id":p,"sources":payload[a]}

# ---------------------------------------------------------------------------
# Lean Stage 2 (ADJ-043).  After reveal, §9.3 assigns one or more of eight
# families; a source-specific finding needs a clear basis in the frozen rules
# and the evidence available to that source.  The release triggers need the
# mechanism, the labels and the release implication of each finding.  Up to
# six findings per record; affected sources, mandatory second review and the
# families per record are derived rather than asked.
# ---------------------------------------------------------------------------
FAMILIES="1, Apparent model rule-application problem | 2, Apparent scratch-coder rule-application problem | 3, Evidence problem | 4, Taxonomy problem | 5, Project-knowledge gap | 6, Legitimate boundary case | 7, Data or instrument problem | 8, Unresolved"
# Six, matching the six Stage 1 conflicts: an independent audit found Stage 1
# could cite six rules while Stage 2 stopped at three findings, so a record with
# four distinct families or mechanisms could not be recorded, against 9.3.  A
# slot opens only when the one before it asks for another.
FINDING_SLOTS=6
BASIS="1, Conflicts with an explicit rule | 2, Materially weaker support than a displayed alternative | 3, Omits a materially better-supported label | 4, Applies the instructions inconsistently"
BASIS_BY_FAMILY={1:{1,2,3},2:{1,4}}
RELEASE="0, None | 1, Caveat only | 2, Evidence for prompt revision | 3, Evidence for taxonomy revision | 4, Data or instrument repair | 5, Evidence for non-release | 6, Escalate: may alter a headline dashboard output | 9, Pending"
# The three release implications that send a record to mandatory second review
# (§9.1).  The field note names these, so both read from one list.
RELEASE_MANDATORY=(2,3,5)
# Release implications that propose something, and so have something to explain.
# None and Pending propose nothing.
RELEASE_PROPOSES=(1,2,3,4,5,6)
RELEASE_CODES={0,1,2,3,4,5,6,9}
# Mechanisms come from the versioned vocabulary (ADJ-044): boundary and rule
# mechanisms for families 1, 2, 4 and 6; data and instrument mechanisms for 7.
MECHANISM_FAMILIES={1,2,4,6,7}; RULE_MECH_FAMILIES={1,2,4,6}; DATA_MECH_FAMILIES={7}
MECH_NEW=999; MECH_VOCABULARY="mechvocab-0.2"
GENERAL_MECHANISM_CODES={24,25,26,27,34,35,39}  # 39 added in mechvocab-0.3 (ADJ-086)
def mechanism_vocabulary():
    path=ROOT/"instruments"/"mechanism_vocabulary.csv"
    if not path.exists(): raise FileNotFoundError(f"mechanism vocabulary required: {path}; run build_mechanism_vocabulary.py")
    with path.open(encoding="utf-8",newline="") as file:
        return [{**r,"code":int(r["code"])} for r in csv.DictReader(file)]
def mechanism_codes(group): return {r["code"] for r in mechanism_vocabulary() if r["group"]==group}
def finding_label_names(values,vocab):
    return sorted({vocab[v-1] if type(v) is int and 1<=v<=len(vocab) else v
                   for v in values})
CODERS={1:"C01",2:"C02",3:"C03"}
NO_CONFLICT_BASIS=0; BASIS_RULE_CONFLICT=1
def recorded_conflicts(stage1):
    """The conflict numbers Stage 1 actually recorded."""
    if not stage1: return []
    out=[]
    for n in CONFLICT_BLOCKS:
        ask=stage1.get(conflict_block(n)["ask"])
        if ask!=1: break
        out.append(n)
    return out
def inherited_from_conflicts(stage1,cited):
    """Components, labels and basis a finding takes from its conflicts (ADJ-056).

    Stage 1 already recorded, blind, which components and options a rule was
    breached in and which rule it was.  Asking again after the reveal adds no
    information and lets the two accounts disagree about one finding, which is
    exactly what the blind stage exists to prevent.
    """
    components=set(); labels={"dom":set(),"purp":set()}
    for n in cited:
        b=conflict_block(n)
        components|=set(stage1.get(b["scope"],[]))
        named=rule_label(stage1.get(b["cited"]))
        for comp in ("dom","purp"):
            if COMPONENT_CODE[comp] not in set(stage1.get(b["scope"],[])): continue
            labels[comp]|={named} if named and rule_component(stage1.get(b["cited"]))==comp else set(stage1.get(b["labels"](comp),[]))
    return {"components":sorted(components),"dom_labels":sorted(labels["dom"]),"purp_labels":sorted(labels["purp"]),
            "basis":BASIS_RULE_CONFLICT,"explanations":[stage1.get(conflict_block(n)["note"]) for n in cited]}
def validate_stage2(r,stage1=None,case=None,package=None):
    """Validate a Stage 2 response against the lean instrument.

    With the Stage 1 response it also checks what a finding inherits from the
    conflicts it rests on, which REDCap cannot express as branching alone.
    """
    out=[]; closure=r.get("adj_stage2_closure"); out+=issue(closure,{1,2,3,4},"Stage 2 closure")
    source_slots=verified_source_slots(case,package) if case is not None and package is not None else None
    if closure==2 and not r.get("adj_no_issue_rationale"): out.append("no assignable issue needs a short positive rationale")
    shown=closure==1
    for k in range(1,FINDING_SLOTS+1):
        pre=f"adj_f{k}_"; present=[x for x in r if x.startswith(pre)]
        if not shown:
            if present: out.append(f"finding {k} is only recorded when an earlier finding asks for another")
            continue
        family=r.get(pre+"family"); out+=issue(family,set(range(1,9)),f"finding {k} family")
        available=recorded_conflicts(stage1)
        cited=set(r.get(pre+"conflicts",[]))
        if cited and stage1 is None: out.append(f"finding {k}: preserved Stage 1 response required for conflict attribution")
        if stage1 is not None:
            if available:
                if not cited or not cited<={NO_CONFLICT_BASIS}|set(available):
                    out.append(f"finding {k} needs the recorded conflicts it rests on, or None")
                elif NO_CONFLICT_BASIS in cited and len(cited)!=1:
                    out.append(f"finding {k}: None is exclusive")
            elif cited: out.append(f"finding {k}: conflicts are only cited where Stage 1 recorded one")
        rests_on=sorted(cited-{NO_CONFLICT_BASIS})
        inherited=inherited_from_conflicts(stage1,rests_on) if rests_on else None
        if inherited and family in (1,2):
            if source_slots is None: out.append(f"finding {k}: original source mapping required to verify attribution")
            else:
                affected={"production model"} if family==1 else {"coder "+CODERS[c] for c in r.get(pre+"coders",[]) if c in CODERS}
                attributed=set()
                for n in rests_on:
                    b=conflict_block(n)
                    cited_sources={source for comp in COMPONENTS if COMPONENT_CODE[comp] in stage1.get(b["scope"],[])
                                   for slot in stage1.get(b["slots"](comp),[])
                                   for source in source_slots[comp].get(slot,set())}
                    attributed|=cited_sources
                    if not affected&cited_sources:
                        out.append(f"finding {k}: affected source is absent from conflict {n} option(s)")
                if not affected<=attributed: out.append(f"finding {k}: an affected source is absent from cited conflict options")
        components=set(r.get(pre+"components",[]))
        if not inherited and r.get(pre+"mech") in GENERAL_MECHANISM_CODES and not components&{1,2}:
            out.append(f"finding {k}: general mechanism needs a Domain or Purpose component")
        if inherited:
            # Inherited, not asked: a second account of one finding can disagree.
            for field in ("components","dom_labels","purp_labels","basis","note"):
                if pre+field in r: out.append(f"finding {k}: {field} is inherited from the conflicts it rests on, not entered")
            if family not in (1,2): out.append(f"finding {k}: only a source-specific finding rests on a rule conflict")
        else:
            if not components or not components<={1,2,3,4}: out.append(f"finding {k} needs its components")
            if family in (1,2) or r.get(pre+"mech") in GENERAL_MECHANISM_CODES:
                for code,comp in ((1,"dom"),(2,"purp")):
                    if code in components and not r.get(pre+f"{comp}_labels"): out.append(f"finding {k} needs the {comp} labels concerned")
            if family in (1,2):
                basis=r.get(pre+"basis")
                if basis not in BASIS_BY_FAMILY[family]: out.append(f"finding {k} needs a clear basis valid for its family")
                if not r.get(pre+"note"): out.append(f"finding {k} needs its basis explained")
            elif pre+"basis" in r: out.append(f"finding {k}: a basis is only recorded for a source-specific finding")
        coders=set(r.get(pre+"coders",[]))
        for code,comp,vocab in ((1,"dom",DOMAINS),(2,"purp",PURPOSES)):
            selected=set(finding_label_names(r.get(pre+f"{comp}_labels",[]),vocab))
            if not inherited and selected and (code not in components or not selected<=set(vocab)):
                out.append(f"finding {k}: {comp} labels must be valid and in scope")
        if family==2:
            if not coders or not coders<=set(CODERS): out.append(f"finding {k} needs the coder or coders concerned")
        elif coders: out.append(f"finding {k}: coders are only recorded for a scratch-coder finding")
        for field,families,group in (("mech",RULE_MECH_FAMILIES,"rule"),("mech_data",DATA_MECH_FAMILIES,"data")):
            value=r.get(pre+field)
            if family in families:
                if value not in mechanism_codes(group)|{MECH_NEW}: out.append(f"finding {k} needs a mechanism from the list, or New mechanism")
            elif value is not None: out.append(f"finding {k}: {field} does not apply to this family")
        # REDCap cannot make a field required for some answers only, so the
        # validator carries it, with a data-quality rule as the backstop.
        if r.get(pre+"release") in RELEASE_MANDATORY and not str(r.get(pre+"release_note") or "").strip():
            out.append(f"finding {k} proposes a revision or non-release, so it needs the proposal explained")
        if r.get(pre+"release") not in RELEASE_PROPOSES and str(r.get(pre+"release_note") or "").strip():
            out.append(f"finding {k}: a proposal is only explained where one is made")
        if MECH_NEW in (r.get(pre+"mech"),r.get(pre+"mech_data")):
            if not(r.get(pre+"mech_new") and str(r.get(pre+"mech_new")).strip()): out.append(f"finding {k} needs the new mechanism described")
        elif pre+"mech_new" in r: out.append(f"finding {k}: a new-mechanism description is only recorded for New mechanism")
        out+=issue(r.get(pre+"release"),RELEASE_CODES,f"finding {k} release implication")
        if k<FINDING_SLOTS:
            another=r.get(pre+"another"); out+=issue(another,{0,1},f"finding {k} another-finding answer")
            shown=another==1
    if closure in (1,2) and r.get("adj_stage2_affirmed")!=1: out.append("Stage 2 completion not affirmed")
    if any(x.startswith("adj_stage2_derived") or x.endswith("_mandatory_review") for x in r): out.append("derived Stage 2 indicators cannot be supplied")
    return out
def derive_stage2(r,stage1=None,case=None,package=None):
    """Families per record, affected sources, and whether second review is mandatory (§9.1).

    With the Stage 1 response, a finding also carries the components, labels
    and basis of the conflicts it rests on, so the preserved finding is whole
    whether or not they were entered twice (ADJ-056).
    """
    if any(set(r.get(f"adj_f{k}_conflicts",[]))-{NO_CONFLICT_BASIS} for k in range(1,FINDING_SLOTS+1)):
        problems=validate_stage2(r,stage1,case,package)
        if problems: raise ValueError("; ".join(problems))
    findings=[]
    if r.get("adj_stage2_closure")==1:
        for k in range(1,FINDING_SLOTS+1):
            family=r.get(f"adj_f{k}_family")
            if family is None: break
            sources=["production model"] if family==1 else [CODERS[c] for c in sorted(r.get(f"adj_f{k}_coders",[]))] if family==2 else []
            code=r.get(f"adj_f{k}_mech") if family in RULE_MECH_FAMILIES else r.get(f"adj_f{k}_mech_data") if family in DATA_MECH_FAMILIES else None
            # A code carries the version it was introduced in, so its versioned
            # key never shifts when later versions add entries (ADJ-082).
            vocab={x["code"]:x for x in mechanism_vocabulary()}
            mechanism=None if code is None else {"code":code,"name":("NEW: "+str(r.get(f"adj_f{k}_mech_new"))) if code==MECH_NEW else vocab[code]["name"],
                                                 "vocabulary":MECH_VOCABULARY if code==MECH_NEW else vocab[code]["introduced_in"]}
            rests_on=sorted(set(r.get(f"adj_f{k}_conflicts",[]))-{NO_CONFLICT_BASIS})
            inherited=inherited_from_conflicts(stage1,rests_on) if rests_on and stage1 else None
            findings.append({"finding":k,"family":family,"affected_sources":sources,"mechanism":mechanism,"release":r.get(f"adj_f{k}_release"),
                             "rests_on_conflicts":rests_on,
                             "components":inherited["components"] if inherited else sorted(r.get(f"adj_f{k}_components",[])),
                             "dom_labels":inherited["dom_labels"] if inherited else finding_label_names(r.get(f"adj_f{k}_dom_labels",[]),DOMAINS),
                             "purp_labels":inherited["purp_labels"] if inherited else finding_label_names(r.get(f"adj_f{k}_purp_labels",[]),PURPOSES),
                             "basis":inherited["basis"] if inherited else r.get(f"adj_f{k}_basis"),
                             "basis_explained":inherited["explanations"] if inherited else [r.get(f"adj_f{k}_note")]})
            if r.get(f"adj_f{k}_another")!=1: break
    families=sorted({f["family"] for f in findings})
    reasons=[]
    if 1 in families: reasons.append("apparent production-model rule-application problem")
    if 8 in families: reasons.append("unresolved")
    if any(f["release"] in RELEASE_MANDATORY for f in findings): reasons.append("proposed as evidence for prompt revision, taxonomy revision or non-release")
    return {"findings":findings,"families":families,"family_count":len(families),"mandatory_second_review":int(bool(reasons)),"mandatory_reasons":reasons}
def source_name(c):
    if c["source_type"]=="fable": return "production model"
    sid=c.get("source_id","?"); return "coder "+{"SC_A":"C01","SC_B":"C02","SC_C":"C03"}.get(sid,sid)
def verified_source_slots(case,package):
    """Resolve option sources from original classifications after Stage 1 preservation."""
    if package_case({**case,"assignment_id":package["assignment_id"]},seed=package["seed"])["package_id"]!=package["package_id"]:
        raise PermissionError("original classifications do not match the preserved package")
    candidates={}
    for c in case["classifications"]:
        if c["source_type"] in {"fable","scratch"}:
            candidates.setdefault("C_"+stable_id(candidate_content(c)),set()).add(source_name(c))
    return {comp:{slot_map(package,comp)[item["interpretation_id"]]:
                  {source for cid in item["candidate_ids"] for source in candidates[cid]}
                  for item in package["interpretations"][comp]} for comp in COMPONENTS}
def reveal_columns():
    """Reveal import columns: the source of each option slot, per component.

    The option values are Stage 1 fields, which Stage 2 pipes, so the reveal
    adds only what was withheld: who gave each option (ADJ-048).
    """
    return [f"adj_reveal_{comp}_{letter.lower()}_src" for comp in COMPONENTS for letter in OPTION_LETTERS]
def reveal_fields(case,package):
    """Reveal text per option: which source gave it, and what it says.

    A row per option, rather than one box per component, so the source sits on
    the option's own heading line instead of wrapping inside shared text
    (ADJ-047).  Only the source is revealed: the option text is a Stage 1 field
    Stage 2 pipes, so the blind and revealed views cannot disagree about what
    was shown (ADJ-048). A single displayed option still names its source;
    a slot the record does not have carries no value. Imported only after
    Stage 1 is preserved.
    """
    by_candidate={}
    for c in case["classifications"]:
        if c["source_type"] not in {"fable","scratch"}: continue
        by_candidate.setdefault("C_"+stable_id(candidate_content(c)),[]).append(source_name(c))
    order=lambda n:(n!="production model",n)
    out={c:"" for c in reveal_columns()}
    for comp in COMPONENTS:
        interpretations=package["interpretations"][comp]
        slots=slot_map(package,comp)
        for x in interpretations:
            low=OPTION_LETTERS[slots[x["interpretation_id"]]-1].lower()
            out[f"adj_reveal_{comp}_{low}_src"]=", ".join(sorted({n for cid in x["candidate_ids"] for n in by_candidate[cid]},key=order))
    return out
def write_reveal_import(path,pairs):
    """Reveal rows for (case, package) pairs.  Deliberately source-revealing."""
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["adj_assignment_id","adj_reveal_state"]+reveal_columns()); w.writeheader()
        for case,package in pairs: w.writerow({"adj_assignment_id":package["assignment_id"],"adj_reveal_state":1,**reveal_fields(case,package)})
REVIEWER_ROLES=((1,"primary",""),(2,"secondary","_SEC"))
IMPORTED_DEFAULTS={"adj_other_concern":0,"adj_stage1_unresolved":0}
BOLD_RESET="<span style='font-weight:normal;white-space:pre-line'>"
def dataset_lines(text):
    """The frozen datasets-used entry, one dataset per line.

    The register keeps the entry as a single string, so a narrow box ran the
    datasets together and the reviewer could not see how many there were
    (ADJ-048).  Splitting inserts line breaks and changes nothing else: the
    characters either side of a break are the frozen ones, and a string that
    does not split is shown exactly as the register holds it.

    A comma separates datasets in the register, but it also ends a clause such
    as a trailing year range, so a comma splits only when every resulting piece
    still looks like a dataset name.  Where it does not, the entry is left
    whole rather than broken in the wrong place.
    """
    text=str(text or "")
    parts=[p.strip() for p in text.split(" & ") if p.strip()]
    commas=[q.strip() for p in parts for q in p.split(", ") if q.strip()]
    if len(commas)>len(parts) and all(len(q)>=12 and any(c.isalpha() for c in q) for q in commas): parts=commas
    return "\n".join(parts) if len(parts)>1 else text
def plain(text):
    """Body text for a descriptive field.

    REDCap renders descriptive text bold, so a recap written as plain HTML came
    out entirely bold and nothing stood out (ADJ-047).  An inline weight beats
    the browser default for the element it wraps, so headings stay bold and
    everything under them reads normally.
    """
    return BOLD_RESET+text+"</span>"
def block(heading,body): return f"<b>{heading}</b><br>"+plain(body)
SAME_RULE_NOTE="Tick only the options that breach this conflict's rule."
def slot_hiding(comp):
    """@IF/@HIDECHOICE annotation hiding slots beyond this record's count.

    Evaluated when the form loads.  It hides nothing when the count is missing
    or invalid, and never hides an answer already saved; the validator and the
    data-quality rules are the backstop for both.
    """
    count=f"[adj_{comp}_slot_count]"
    return (f"@IF({count} = '1', @HIDECHOICE='2,3,4', "
            f"@IF({count} = '2', @HIDECHOICE='3,4', "
            f"@IF({count} = '3', @HIDECHOICE='4', '')))")
def data_quality_rules():
    """Form-level backstops for impossible, missing and contradictory answers."""
    rules=[("Generation error affirmed as complete Stage 1",
            "[adj_diff_check] = '2' and [adj_stage1_affirmed] = '1'","y")]
    for comp in COMPONENTS:
        count=f"[adj_{comp}_slot_count]"
        below=lambda s:"("+" or ".join(f"{count} = '{k}'" for k in [""]+[str(x) for x in range(1,s)])+")"
        for field,name in (("best","best-supported"),("defensible","defensible"),("conflict_slots","conflicting"))+tuple((f"conflict{n}_slots",f"{CONFLICT_ORDINAL[n]}-rule conflicting") for n in EXTRA_CONFLICTS):
            rules.append((f"Impossible {name} option: {COMPONENT_LABEL[comp]}",
                          " or ".join(f"([adj_{comp}_{field}({s})] = '1' and {below(s)})" for s in range(2,5)),"y"))
        rules.append((f"Missing or invalid slot count: {COMPONENT_LABEL[comp]}",
                      f"[adj_{comp}_comparative] = '1' and {count} <> '2' and {count} <> '3' and {count} <> '4'","y"))
        for n in CONFLICT_BLOCKS:
            b=conflict_block(n); slots=b["slots"](comp)
            rules.append((f"Missing {CONFLICT_ORDINAL[n]}-rule conflicting option: {COMPONENT_LABEL[comp]}",
                          f"[{b['ask']}] = '1' and [{b['scope']}({COMPONENT_CODE[comp]})] = '1' and " +
                          " and ".join(f"[{slots}({s})] <> '1'" for s in range(1,5)),"y"))
    for k in range(1,FINDING_SLOTS+1):
        pre=f"adj_f{k}_"
        rules.append((f"Unexplained proposal: finding {k}",
                      "("+" or ".join(f"[{pre}release] = '{c}'" for c in RELEASE_MANDATORY)+f") and [{pre}release_note] = ''","y"))
    return rules
def write_data_quality_rules(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["rule_name","rule_logic","real_time_execution"]); w.writerows(data_quality_rules())
COMPONENT_LABEL={"dom":"Research Domains","purp":"Analytical Purposes","covid":"COVID-19/pandemic tag","equity":"Demographic disparities/equity tag"}
SINGLE_SET_NOTE="No competing candidate differences; a single displayed candidate set is not a finding of no concern"
# Tokens that would betray a source if they ever reached a masked import row.
IMPORT_FORBIDDEN=("fable","scratch","gpt","coder","source_type","source_id","rationale","reveal")

def slot_map(package,comp):
    """Map this package's interpretation IDs onto the four neutral slots."""
    interpretations=package["interpretations"][comp]
    if len(interpretations)>4: raise ValueError(f"{comp}: {len(interpretations)} interpretations exceed the four neutral slots; overflow is a QA failure, not truncation")
    return {x["interpretation_id"]:n for n,x in enumerate(interpretations,1)}
def generated_evidence(package):
    """Read-only generator output for one assignment.

    Slot numbers, membership and observed differences are derived only from the
    displayed candidates.  No source identity, route, count or reveal material
    is included.
    """
    out={"adj_case_title":package["title"],"adj_case_datasets":dataset_lines(package["datasets"])}; diff_dimensions=[]; diff_labels=[]; diff_tags=[]
    for comp in COMPONENTS:
        # Hidden per-record flags drive REDCap branching: the reviewer is only
        # asked the questions this package actually raises.
        out[f"adj_{comp}_comparative"]=int(len(package["interpretations"][comp])>1)
    # 1 when displayed sets compete anywhere; 0 routes the record to the
    # owner-only single-set questions instead of the comparative judgements.
    out["adj_pkg_comparative"]=int(len(package["candidates"])>1)
    # Distinct displayed interpretations per component.  Loaded before the
    # form opens, so @IF can hide slot choices this record does not have.
    for comp in COMPONENTS: out[f"adj_{comp}_slot_count"]=len(package["interpretations"][comp])
    for comp in COMPONENTS:
        interpretations=package["interpretations"][comp]; slots=slot_map(package,comp)
        # What the reviewer reads: one field per displayed option, labels
        # separated by semicolons because some canonical labels contain commas.
        # Stage 2 pipes these same fields, so the blind and revealed views
        # cannot disagree about what was shown (ADJ-048).
        for letter in OPTION_LETTERS: out[f"adj_{comp}_opt_{letter.lower()}"]=""
        for x in interpretations:
            low=OPTION_LETTERS[slots[x["interpretation_id"]]-1].lower()
            out[f"adj_{comp}_opt_{low}"]="; ".join(x["value"]) if isinstance(x["value"],list) else x["value"]
        # What the joins need: interpretation and candidate content IDs per slot,
        # kept in a hidden field so they never clutter the form.
        out[f"adj_{comp}_candidate_map"]="; ".join(f"Option {OPTION_LETTERS[slots[x['interpretation_id']]-1]} (code {slots[x['interpretation_id']]}) = {x['interpretation_id']}: {', '.join(x['candidate_ids'])}" for x in interpretations)
        if len(interpretations)>1: diff_dimensions.append(COMPONENT_LABEL[comp])
    for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
        ids,labels=component_labels(package,comp); slots=slot_map(package,comp)
        for n,label in enumerate(vocab,1):
            containing=sorted(slots[x] for x in labels.get(label,set())); omitting=sorted(slots[x] for x in ids-labels.get(label,set()))
            if not containing: text="Not displayed in any interpretation"
            elif not omitting: text="Contained by slots "+", ".join(map(str,containing))+"; omitted by no displayed interpretation"
            else:
                text="Contained by slots "+", ".join(map(str,containing))+"; omitted by slots "+", ".join(map(str,omitting))
                diff_labels.append(f"{COMPONENT_LABEL[comp]}: {label}")
            # Per-label rows serve the owner-only single-set path, where §9.2
            # asks whether each proposed label is supported.  Comparative
            # records answer the record-level judgements instead (ADJ-036).
            applicable=int(bool(containing) and len(package["candidates"])==1)
            out[f"adj_{comp}_l{n:02d}_applicable"]=applicable
            # A value in a field that branching hides makes REDCap prompt the
            # reviewer to erase it, and "Keep All" then displays it.  Write the
            # membership only where the row is shown.
            out[f"adj_{comp}_l{n:02d}_membership"]=text if applicable else ""
    for tag in ("covid","equity"):
        slots=slot_map(package,tag); parts=[]
        for status in ("Applied","Not applied"):
            carrying=sorted(slots[x["interpretation_id"]] for x in package["interpretations"][tag] if x["value"]==status)
            parts.append(f"{status}: "+(", ".join(f"slot {n}" for n in carrying) if carrying else "no displayed interpretation"))
        out[f"adj_{tag}_status_membership"]="; ".join(parts) if len(package["candidates"])==1 else ""
        if len(package["interpretations"][tag])>1: diff_tags.append(COMPONENT_LABEL[tag])
    comparative=len(package["candidates"])>1
    out["adj_diff_dimensions"]="; ".join(diff_dimensions) or (SINGLE_SET_NOTE if not comparative else "None")
    out["adj_diff_labels"]="; ".join(diff_labels) or (SINGLE_SET_NOTE if not comparative else "None")
    out["adj_diff_tag_statuses"]="; ".join(diff_tags) or (SINGLE_SET_NOTE if not comparative else "None")
    return out
def assignment_packages(case):
    """One masked package per reviewer role, each independently ordered."""
    out=[]
    for role,group,suffix in REVIEWER_ROLES:
        package=package_case({**case,"assignment_id":case["assignment_id"]+suffix})
        if package["qa_flags"]: raise ValueError(f"{package['assignment_id']}: QA flags block import generation: "+", ".join(package["qa_flags"]))
        out.append((role,group,package))
    return out
def import_rows(cases):
    rows=[]
    for case in cases:
        for role,group,package in assignment_packages(case):
            row={"adj_assignment_id":package["assignment_id"],"redcap_data_access_group":group,"adj_source_record_id":case["record_id"],"adj_reviewer_role":role,"adj_stage1_package_id":package["package_id"],**generated_evidence(package),
                 # REDCap applies @DEFAULT only to a form never saved, and this
                 # import writes to Stage 1, so the defaults are written here.
                 **IMPORTED_DEFAULTS}
            for key,value in row.items():
                lowered=str(value).lower()
                for token in IMPORT_FORBIDDEN:
                    if token in lowered: raise ValueError(f"masked import row {row['adj_assignment_id']} leaks {token!r} in {key}")
            rows.append(row)
    return rows
def write_record_import(path,cases):
    """Write the synthetic record-import file for an already-imported dictionary."""
    rows=import_rows(cases); names=[x[0] for x in field_rows()]
    unknown=[k for k in rows[0] if k!="redcap_data_access_group" and k not in names]
    if unknown: raise ValueError("import columns absent from the candidate dictionary: "+", ".join(unknown))
    columns=["adj_assignment_id","redcap_data_access_group"]+[n for n in names if n in rows[0] and n!="adj_assignment_id"]
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=columns); writer.writeheader(); writer.writerows(rows)
    return rows
def field_rows():
    rows=[]
    def add(n,f,t,l,c="",b="",req="",a="",note="",val="",section=""):
        rows.append([n,f,section,t,l,c,note,val,"","","",b,req,"","","","",a])
    scope_choices="1, Research Domains | 2, Analytical Purposes | 3, COVID-19/pandemic tag | 4, Demographic disparities/equity tag"
    slot_choices=" | ".join(f"{n}, Option {OPTION_LETTERS[n-1]}" for n in range(1,5))
    NOUN={"dom":"Research Domain","purp":"Analytical Purpose","covid":"COVID-19/pandemic tag","equity":"demographic disparities/equity tag"}
    # REDCap takes the FIRST field as the record identifier, and that identifier
    # appears in record lists, URLs, logs and every export.  The opaque
    # assignment ID is therefore first; the stable source Record ID stays a
    # hidden field for restricted joins and must never become the record key.
    add("adj_assignment_id","adj_admin","text","Synthetic assignment ID (record key)",req="y");add("adj_source_record_id","adj_admin","text","Stable source Record ID (administrative join)",a="@HIDDEN");add("adj_reviewer_role","adj_admin","radio","Reviewer role","1, Primary | 2, Secondary","","y","@HIDDEN");add("adj_stage1_package_id","adj_admin","text","Masked package ID",a="@READONLY")
    # Generator-written hidden flags.  They decide which questions a record
    # raises, so the reviewer never filters the form by hand.
    add("adj_pkg_comparative","adj_stage1","text","Generated flag: displayed sets compete",a="@HIDDEN @READONLY")
    for comp in COMPONENTS: add(f"adj_{comp}_comparative","adj_stage1","text",f"Generated flag: {COMPONENT_LABEL[comp]} differ",a="@HIDDEN @READONLY")
    for comp in COMPONENTS: add(f"adj_{comp}_slot_count","adj_stage1","text",f"Generated count: {COMPONENT_LABEL[comp]} displayed interpretations",a="@HIDDEN @READONLY")
    comparative_pkg="[adj_pkg_comparative] = '1'"; single_pkg="[adj_pkg_comparative] = '0'"
    # The frozen public entry and the displayed interpretations (§9.2).
    add("adj_case_title","adj_stage1","notes","Frozen public register title",a="@HIDDEN @READONLY")
    add("adj_case_datasets","adj_stage1","notes","Frozen datasets-used entry",a="@HIDDEN @READONLY")
    add("adj_s1_entry","adj_stage1","descriptive",block("Frozen public register title","[adj_case_title]")+"<br>"+block("Datasets used","[adj_case_datasets]"),
        section="The public register entry")
    # A row per displayed option, so an option that names several labels wraps
    # under its own heading rather than into the next option (ADJ-048).  Option
    # A always shows, so the component's section header cannot vanish.
    for comp in COMPONENTS:
        for letter in OPTION_LETTERS:
            add(f"adj_{comp}_opt_{letter.lower()}","adj_stage1","notes",f"Displayed option: {COMPONENT_LABEL[comp]} Option {letter}",a="@HIDDEN @READONLY")
        for n,letter in enumerate(OPTION_LETTERS,1):
            add(f"adj_s1_opt_{comp}_{letter.lower()}","adj_stage1","descriptive",block(f"Option {letter}",f"[adj_{comp}_opt_{letter.lower()}]"),"",
                "("+" or ".join(f"[adj_{comp}_slot_count] = '{k}'" for k in range(n,5))+")",
                section=f"{NOUN[comp][0].upper()+NOUN[comp][1:]} classification options" if n==1 else "")
    for comp in COMPONENTS: add(f"adj_{comp}_candidate_map","adj_stage1","notes",f"{COMPONENT_LABEL[comp]}: option to candidate content IDs (join key)",a="@HIDDEN @READONLY")
    for n,l in (("adj_diff_dimensions","Components that differ"),("adj_diff_labels","Labels that differ"),("adj_diff_tag_statuses","Tag statuses that differ")):add(n,"adj_stage1","notes",l,a="@READONLY")
    # Judgement 1: the generated differences are accurate.
    add("adj_diff_check","adj_stage1","radio","Does the summary correctly identify the differences between the displayed options?","1, Yes | 2, No, there is an error","","y");add("adj_diff_error_note","adj_stage1","notes","Describe the error","","[adj_diff_check] = '2'","y")
    # Per differing component: evidence, relative support, sufficient support
    # and defensibility (ADJ-040).  Each has a short help text, because the
    # three support questions are easy to confuse and must stay distinct.
    for comp in COMPONENTS:
        noun=NOUN[comp]; differs=f"[adj_{comp}_comparative] = '1'"
        add(f"adj_{comp}_evidence","adj_stage1","radio",f"How much information do the title and listed datasets provide for assessing these {noun} options?",
            "1, Enough for a clear assessment | 2, Some useful information, but important uncertainty remains | 3, Too little information for a meaningful assessment | 4, Cannot judge",differs,"y",
            note="A clear assessment may still conclude that several options are defensible.")
        add(f"adj_{comp}_best","adj_stage1","checkbox",f"Which {noun} option or options are best supported by the title and listed datasets?",
            slot_choices+f" | {BEST_CANNOT_DETERMINE}, Cannot determine which is better supported",f"{differs} and [adj_{comp}_evidence] <> '3'","y",
            f"@NONEOFTHEABOVE='{BEST_CANNOT_DETERMINE}' "+slot_hiding(comp),
            note="Relative support: which option has stronger evidence. If options tie for best, tick each of them.")
        add(f"adj_{comp}_defensible","adj_stage1","checkbox",f"Which {noun} options, if any, could reasonably be assigned under the coding rules using only the title and listed datasets?",
            slot_choices+f" | {DEFENSIBLE_NONE}, None | {DEFENSIBLE_CANNOT_JUDGE}, Cannot judge",differs,"y",
            f"@NONEOFTHEABOVE='{DEFENSIBLE_NONE},{DEFENSIBLE_CANNOT_JUDGE}' "+slot_hiding(comp),
            note="Defensibility: which options are reasonable under the rules. Tick all that apply.")
    # Explicit rule conflict, record level, with the blind option and label
    # identification that later supports a clear-basis attribution at Stage 2.
    # Rule conflicts (ADJ-051, ADJ-054, ADJ-055).  One conflict is one rule.
    # Six blocks are declared and each opens only once the one before it is
    # filled, so a record with a single conflict is asked one question more and
    # a record with six never runs out of room.  The rule is cited before the
    # options it concerns, because the rule decides whether a label is asked
    # for at all: a category rule already names its label.
    label_free=lambda cited:"("+" or ".join(f"[{cited}] = '{code}'" for code in label_free_rules())+")"
    for n in CONFLICT_BLOCKS:
        b=conflict_block(n); word=CONFLICT_ORDINAL[n]
        block_pkg=f"{comparative_pkg} and [{b['ask']}] = '1'"
        if n==1:
            add(b["ask"],"adj_stage1","radio","Does any displayed option conflict with an explicit rule in the frozen taxonomy or coding instructions?",
                "1, Yes | 0, No | 2, Cannot judge",comparative_pkg,"y",
                note="A conflict means an option breaches an explicit rule. An option that is merely less well supported by the entry is not a "
                     "conflict; that is the best-supported question above. Record one rule per conflict: tick together the options breaching the "
                     "same rule, and record an option breaching two rules as two conflicts.")
        else:
            add(b["ask"],"adj_stage1","radio","Does another displayed option conflict with a rule not yet cited?","1, Yes | 0, No",
                f"{comparative_pkg} and [{conflict_block(n-1)['ask']}] = '1'","y",
                note="Answer Yes only for a rule not already cited. Several options breaching one rule are ticked together within its own conflict.")
        # Scope, then the options, then the rule they breach: the conflict is
        # narrowed before it is named.  The labels follow the rule, because the
        # rule decides whether they are asked for at all, so nothing appears
        # above the field just answered.
        add(b["scope"],"adj_stage1","checkbox",f"Which parts of the classification does the {word} conflict concern?" if n>1
            else "Which parts of the classification does the conflict concern?",scope_choices,block_pkg,"y")
        for comp in COMPONENTS:
            in_scope=f"{block_pkg} and [{b['scope']}({COMPONENT_CODE[comp]})] = '1'"
            add(b["slots"](comp),"adj_stage1","checkbox",f"Which {NOUN[comp]} option or options conflict with the {word} rule?" if n>1
                else f"Which {NOUN[comp]} option or options conflict?",slot_choices,
                in_scope,"y",slot_hiding(comp),note=SAME_RULE_NOTE)
        add(b["cited"],"adj_stage1","dropdown",f"Which rule does the {word} conflict involve?" if n>1 else "Which rule does it conflict with?",
            rule_choices(),block_pkg,"y",
            note="Type to search by category or rule ID. The same IDs head the rules in the adjudication rule reference.",val="autocomplete")
        add(b["other"],"adj_stage1","text","Describe the rule or coding instruction","",f"{block_pkg} and [{b['cited']}] = '{RULE_OTHER}'","y")
        for comp in ("dom","purp"):
            vocab=DOMAINS if comp=="dom" else PURPOSES
            # Asked only where the cited rule names no label of its own.
            add(b["labels"](comp),"adj_stage1","checkbox",f"Which {NOUN[comp]} label or labels are involved?",
                " | ".join(f"{i}, {x}" for i,x in enumerate(vocab,1)),
                f"{block_pkg} and [{b['scope']}({COMPONENT_CODE[comp]})] = '1' and {label_free(b['cited'])}","y",
                note="The rule you cited names no label of its own, so name the labels it was breached over.")
        add(b["note"],"adj_stage1","notes","Explain the conflict, or why it cannot be judged" if n==1 else f"Explain the {word} conflict","",
            f"{comparative_pkg} and ([{b['ask']}] = '1' or [{b['ask']}] = '2')" if n==1 else block_pkg,"y")
    # Owner-only single-set path: §9.2 asks whether each proposed label is
    # supported, whether a rule is breached, and whether an alternative or
    # additional label is supported.
    for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
        p=f"adj_{comp}_"
        for i,label in enumerate(vocab,1):
            c=f"l{i:02d}";applicable=f"[{p}{c}_applicable] = '1'"
            add(p+c+"_applicable","adj_stage1","text",f"Generated flag: {label} displayed in a single set",a="@HIDDEN @READONLY")
            add(p+c+"_membership","adj_stage1","notes",f"Proposed label: {label}","",applicable,a="@READONLY");add(p+c+"_support","adj_stage1","radio",f"{label}: supported by the visible public entry?","1, Supported | 2, Not supported | 3, Cannot determine",applicable,"y");add(p+c+"_rule_conflict","adj_stage1","radio",f"{label}: conflicts with an explicit taxonomy rule?","0, No | 1, Yes | 2, Cannot assess",applicable,"y");add(p+c+"_rule_cited","adj_stage1","dropdown",f"{label}: which rule?",rule_choices(),f"{applicable} and [{p}{c}_rule_conflict] = '1'","y",val="autocomplete");add(p+c+"_rule_other","adj_stage1","text",f"{label}: describe the rule","",f"{applicable} and [{p}{c}_rule_conflict] = '1' and [{p}{c}_rule_cited] = '{RULE_OTHER}'","y");add(p+c+"_rule_note","adj_stage1","notes",f"{label}: explanation","",f"{applicable} and ([{p}{c}_rule_conflict] = '1' or [{p}{c}_rule_conflict] = '2')","y")
        choices=" | ".join(f"{i}, {x}" for i,x in enumerate(vocab,1))
        add(p+"additional_label_state","adj_stage1","radio",f"{COMPONENT_LABEL[comp]}: is an additional or alternative label supported?","0, None identified | 1, Identified | 2, Cannot determine",single_pkg,"y");add(p+"additional_label_ids","adj_stage1","checkbox",f"{COMPONENT_LABEL[comp]}: supported additional labels",choices,f"{single_pkg} and [{p}additional_label_state] = '1'","y");add(p+"additional_label_note","adj_stage1","notes",f"{COMPONENT_LABEL[comp]}: explanation","",f"{single_pkg} and ([{p}additional_label_state] = '1' or [{p}additional_label_state] = '2')","y")
    for tag in ("covid","equity"):
        p=f"adj_{tag}_";add(p+"status_membership","adj_stage1","notes",f"{COMPONENT_LABEL[tag]}: proposed status","",single_pkg,a="@READONLY");add(p+"status_support","adj_stage1","radio",f"{COMPONENT_LABEL[tag]}: status supported by the visible public entry?","1, Supported | 2, Not supported | 3, Cannot determine",single_pkg,"y");add(p+"rule_conflict","adj_stage1","radio",f"{COMPONENT_LABEL[tag]}: conflicts with an explicit taxonomy rule?","0, No | 1, Yes | 2, Cannot assess",single_pkg,"y");add(p+"rule_cited","adj_stage1","dropdown",f"{COMPONENT_LABEL[tag]}: which rule?",rule_choices(),f"{single_pkg} and [{p}rule_conflict] = '1'","y",val="autocomplete");add(p+"rule_other","adj_stage1","text",f"{COMPONENT_LABEL[tag]}: describe the rule","",f"{single_pkg} and [{p}rule_conflict] = '1' and [{p}rule_cited] = '{RULE_OTHER}'","y");add(p+"rule_note","adj_stage1","notes",f"{COMPONENT_LABEL[tag]}: explanation","",f"{single_pkg} and ([{p}rule_conflict] = '1' or [{p}rule_conflict] = '2')","y");add(p+"supported_status","adj_stage1","radio",f"{COMPONENT_LABEL[tag]}: is the opposite status supported?","0, No | 1, Yes | 2, Cannot determine",single_pkg,"y");add(p+"supported_status_note","adj_stage1","notes",f"{COMPONENT_LABEL[tag]}: explanation","",f"{single_pkg} and ([{p}supported_status] = '1' or [{p}supported_status] = '2')","y")
    # Judgement 3: boundary, asked for every record.
    add("adj_boundary","adj_stage1","checkbox","Does a boundary between taxonomy categories help explain the classifications shown?","1, A boundary documented in the frozen rules or examples | 2, A plausible boundary identified in this review | 0, No | 9, Cannot judge","","y","@NONEOFTHEABOVE='0,9'",
        note="Both kinds may apply where distinct boundaries are involved. Sparse register evidence is not a taxonomy boundary.")
    add("adj_boundary_scope","adj_stage1","checkbox","Which components?",scope_choices,"[adj_boundary(1)] = '1' or [adj_boundary(2)] = '1'","y");add("adj_boundary_same_rule","adj_stage1","radio","Is the documented boundary the same rule you cited for the conflict?","1, Yes, the same rule | 0, No, a different rule","[adj_rule_conflict] = '1' and [adj_boundary(1)] = '1'","y",
        note="If Yes, the rule and explanation you gave for the conflict are used for the boundary too.")
    add("adj_boundary_rule_cited","adj_stage1","dropdown","Which rule documents the boundary?",rule_choices(),"[adj_boundary(1)] = '1' and [adj_boundary_same_rule] <> '1'","y",val="autocomplete")
    add("adj_boundary_rule_other","adj_stage1","text","Describe the rule or coding instruction","","[adj_boundary(1)] = '1' and [adj_boundary_same_rule] <> '1' and [adj_boundary_rule_cited] = '999'","y")
    add("adj_boundary_note","adj_stage1","notes","Explain the boundary","","([adj_boundary(1)] = '1' and [adj_boundary_same_rule] <> '1') or [adj_boundary(2)] = '1'","y")
    # Masking failures must be logged (§9.3).
    add("adj_masking_failure","adj_stage1","radio","Before the source reveal, did you recognise or become aware of which source produced any displayed option?","1, Yes | 0, No | 2, Unsure","","y",
        note="General prior exposure is recorded once in the adjudicator declaration, not here.");add("adj_masking_note","adj_stage1","notes","What prompted this, and when?","","[adj_masking_failure] = '1' or [adj_masking_failure] = '2'","y")
    # Defaults to No: explicit value stored, no click needed.
    add("adj_other_concern","adj_stage1","radio","Any other concern, such as a supported label that no option proposed?","0, No | 1, Yes","","y","@DEFAULT='0'");add("adj_other_concern_note","adj_stage1","notes","Describe the concern","","[adj_other_concern] = '1'","y")
    add("adj_stage1_unresolved","adj_stage1","radio","Unresolved at Stage 1?","0, No | 1, Yes","","y","@DEFAULT='0'");add("adj_stage1_unresolved_note","adj_stage1","notes","Why is the case unresolved?","","[adj_stage1_unresolved] = '1'","y")
    add("adj_stage1_note","adj_stage1","notes","Optional note")
    add("adj_stage1_affirmed","adj_stage1","yesno","Complete preserved Stage 1 assessment?","","[adj_diff_check] = '1'","y")
    # ---- Stage 2 (ADJ-043): imported reveal, then findings -------------------------------
    add("adj_reveal_state","adj_stage2","radio","Stage 2 reveal state","0, Not revealed | 1, Revealed | 2, Partial-failure exposure",a="@READONLY",section="Stage 2: after the source reveal")
    # REDCap shows only the open form's fields, so Stage 2 carries the entry,
    # the reveal and a recap of the reviewer's own Stage 1 answers.  Sections
    # and one box per component keep it readable.
    add("adj_s2_entry","adj_stage2","descriptive",block("Title","[adj_case_title]")+"<br>"+block("Datasets used","[adj_case_datasets]"),
        section="The public register entry")
    # A row per option, headed by the option and the source that gave it, so a
    # long classification wraps under its own heading rather than into the next
    # option (ADJ-047).  Exactly one of the option rows and the agreed row shows
    # per component, so both carry the component's section header.
    for comp in COMPONENTS:
        head=f"{COMPONENT_LABEL[comp]}: what each source gave"
        for letter in OPTION_LETTERS:
            add(f"adj_reveal_{comp}_{letter.lower()}_src","adj_stage2","text",f"Revealed source: {COMPONENT_LABEL[comp]} Option {letter}",a="@HIDDEN @READONLY")
        for n,letter in enumerate(OPTION_LETTERS,1):
            low=letter.lower()
            add(f"adj_s2_opt_{comp}_{low}","adj_stage2","descriptive",
                block(f"Option {letter} &mdash; [adj_reveal_{comp}_{low}_src]",f"[adj_{comp}_opt_{low}]"),"",
                f"[adj_{comp}_comparative] = '1' and ("+" or ".join(f"[adj_{comp}_slot_count] = '{k}'" for k in range(n,5))+")",
                section=head if n==1 else "")
        add(f"adj_s2_agreed_{comp}","adj_stage2","descriptive",block(f"Option A &mdash; [adj_reveal_{comp}_a_src]",f"[adj_{comp}_opt_a]"),"",
            f"[adj_{comp}_comparative] <> '1'",section=head)
    # The recap intro is unconditional, so its section header cannot disappear
    # with a component that did not differ.
    add("adj_s2_recap_intro","adj_stage2","descriptive",plain("These are the answers you gave before the sources were revealed."),
        section="Your Stage 1 assessment")
    for comp in COMPONENTS:
        add(f"adj_s2_recap_{comp}","adj_stage2","descriptive",
            block(COMPONENT_LABEL[comp],f"Information in the entry: [adj_{comp}_evidence]<br>"
                  f"Best supported: [adj_{comp}_best:checked]<br>Defensible: [adj_{comp}_defensible:checked]"),"",
            f"[adj_{comp}_comparative] = '1'")
    add("adj_s2_conflict_no","adj_stage2","descriptive",block("Explicit rule conflict","[adj_rule_conflict]"),"",
        "[adj_pkg_comparative] = '1' and [adj_rule_conflict] <> '1'")
    add("adj_s2_conflict_yes","adj_stage2","descriptive",block("Explicit rule conflict","yes, in [adj_rule_conflict_scope:checked]"),"",
        "[adj_pkg_comparative] = '1' and [adj_rule_conflict] = '1'")
    # One recap group per conflict: the rule, the options it concerns, and the
    # labels only where the rule named none, so no line shows blank.
    for n in CONFLICT_BLOCKS:
        b=conflict_block(n)
        add(f"adj_s2_conflict{n}_rule","adj_stage2","descriptive",
            block(f"Conflict {n}",f"Rule: [{b['cited']}]<br>Explanation: [{b['note']}]"),"",
            f"[adj_pkg_comparative] = '1' and [{b['ask']}] = '1'")
        for comp in COMPONENTS:
            in_scope=f"[{b['ask']}] = '1' and [{b['scope']}({COMPONENT_CODE[comp]})] = '1'"
            add(f"adj_s2_conflict{n}_{comp}","adj_stage2","descriptive",
                plain(f"{COMPONENT_LABEL[comp]}: options [{b['slots'](comp)}:checked]"),"",in_scope)
            if comp in ("dom","purp"):
                add(f"adj_s2_conflab{n}_{comp}","adj_stage2","descriptive",
                    plain(f"{COMPONENT_LABEL[comp]}: labels [{b['labels'](comp)}:checked]"),"",
                    f"{in_scope} and "+"("+" or ".join(f"[{b['cited']}] = '{code}'" for code in label_free_rules())+")")
    add("adj_s2_boundary","adj_stage2","descriptive",block("Boundary","[adj_boundary:checked]"))
    # A boundary that is the conflict rule was never re-entered at Stage 1, so
    # the recap points back rather than showing an empty rule and explanation.
    add("adj_s2_boundary_same","adj_stage2","descriptive",plain("The documented boundary is the rule cited above."),"",
        "[adj_boundary(1)] = '1' and [adj_boundary_same_rule] = '1'")
    add("adj_s2_boundary_rule","adj_stage2","descriptive",block("Rule documenting the boundary","[adj_boundary_rule_cited]"),"",
        "[adj_boundary(1)] = '1' and [adj_boundary_same_rule] <> '1'")
    add("adj_s2_boundary_note","adj_stage2","descriptive",block("Explanation","[adj_boundary_note]"),"",
        "([adj_boundary(1)] = '1' and [adj_boundary_same_rule] <> '1') or [adj_boundary(2)] = '1'")
    add("adj_s2_concern","adj_stage2","descriptive",block("Other concern","[adj_other_concern_note]"),"","[adj_other_concern] = '1'")
    add("adj_s2_unresolved","adj_stage2","descriptive",block("Unresolved at Stage 1","[adj_stage1_unresolved_note]"),"","[adj_stage1_unresolved] = '1'")
    add("adj_stage2_closure","adj_stage2","radio","Now that sources are revealed, does any diagnostic family apply?","1, Yes, record findings | 2, No, completed with no assignable issue | 3, Incomplete | 4, Administrative closure","","y",section="Findings",
        note="If the evidence cannot support a confident diagnosis, record a finding of family 8, Unresolved, rather than no issue.")
    add("adj_no_issue_rationale","adj_stage2","notes","Why does no family apply?","","[adj_stage2_closure] = '2'","y")
    for k in range(1,FINDING_SLOTS+1):
        p=f"adj_f{k}_"
        shown="[adj_stage2_closure] = '1'"+"".join(f" and [adj_f{j}_another] = '1'" for j in range(1,k))
        family=f"[{p}family]"
        add(p+"family","adj_stage2","radio",f"Finding {k}: which diagnostic family?",FAMILIES,shown,"y",
            note="One family per finding. Record another finding for a second family or mechanism.")
        # A finding rests on the Stage 1 conflicts it follows from, and takes
        # their components, labels, basis and explanation rather than asking
        # again after the reveal (ADJ-056).  Only the conflicts Stage 1
        # recorded are offered.
        hide=f"@IF([{conflict_block(6)['ask']}] = '1', '', "+"".join(
            f"@IF([{conflict_block(n)['ask']}] = '1', @HIDECHOICE='{','.join(str(x) for x in range(n+1,7))}', " for n in (5,4,3,2))+            "@HIDECHOICE='2,3,4,5,6'"+")"*5
        add(p+"conflicts","adj_stage2","checkbox",f"Finding {k}: which recorded conflicts does it rest on?",
            " | ".join(f"{n}, Conflict {n}" for n in CONFLICT_BLOCKS)+f" | {NO_CONFLICT_BASIS}, Not based on a recorded conflict",
            f"{shown} and [adj_rule_conflict] = '1'","y",f"@NONEOFTHEABOVE='{NO_CONFLICT_BASIS}' "+hide,
            note="Conflict numbers are the ones listed under Your Stage 1 assessment above, each headed by the rule you cited. "
                 "The components, labels, basis and explanation you recorded for a conflict carry over; they are not asked again.")
        # Asked only where the finding rests on no conflict.
        own=f"([adj_rule_conflict] <> '1' or [{p}conflicts({NO_CONFLICT_BASIS})] = '1')"
        add(p+"components","adj_stage2","checkbox",f"Finding {k}: which parts of the classification?","1, Research Domains | 2, Analytical Purposes | 3, COVID-19/pandemic tag | 4, Demographic disparities/equity tag",f"{shown} and {own}","y")
        source_specific=f"({family} = '1' or {family} = '2')"
        general_mechanism="("+" or ".join(f"[{p}mech] = '{code}'" for code in sorted(GENERAL_MECHANISM_CODES))+")"
        # A substitution reads either way round, so the note fixes which labels
        # are ticked; without it the second reviewer's counts mix the two
        # directions and mean nothing (ADJ-052).
        label_note=("Tick the labels your chosen basis concerns: the label wrongly assigned, or, for an omission, the label left out. "
                    "Where one label was assigned instead of another, the pair goes in the mechanism, not here.")
        add(p+"dom_labels","adj_stage2","checkbox",f"Finding {k}: which Research Domain labels?"," | ".join(f"{i}, {x}" for i,x in enumerate(DOMAINS,1)),f"{shown} and ({source_specific} or {general_mechanism}) and {own} and [{p}components(1)] = '1'","y",note=label_note)
        add(p+"purp_labels","adj_stage2","checkbox",f"Finding {k}: which Analytical Purpose labels?"," | ".join(f"{i}, {x}" for i,x in enumerate(PURPOSES,1)),f"{shown} and ({source_specific} or {general_mechanism}) and {own} and [{p}components(2)] = '1'","y",note=label_note)
        add(p+"coders","adj_stage2","checkbox",f"Finding {k}: which coder or coders?"," | ".join(f"{n}, {c}" for n,c in CODERS.items()),f"{shown} and {family} = '2'","y")
        add(p+"basis","adj_stage2","radio",f"Finding {k}: what is the clear basis?",BASIS,f"{shown} and {source_specific} and {own}","y",
            f"@IF({family} = '1', @HIDECHOICE='4', @IF({family} = '2', @HIDECHOICE='2,3', ''))",
            note="A source-specific finding needs a clear basis in the frozen rules and the evidence available to that source; disagreement alone is not enough.")
        vocab=mechanism_vocabulary()
        mech_choices=" | ".join(f"{m['code']}, {m['name']}" for m in vocab if m["group"]=="rule")+f" | {MECH_NEW}, New mechanism (describe below)"
        data_choices=" | ".join(f"{m['code']}, {m['name']}" for m in vocab if m["group"]=="data")+f" | {MECH_NEW}, New mechanism (describe below)"
        add(p+"mech","adj_stage2","dropdown",f"Finding {k}: which mechanism?",mech_choices,f"{shown} and ({family} = '1' or {family} = '2' or {family} = '4' or {family} = '6')","y",
            note="Not the cited rule again: the rule says what was breached, this says the pattern, and where one label was used "
                 "instead of another it names the pair. Pick the same entry whenever the same mechanism recurs; a count across "
                 "records is what shows a problem is more than one case.",val="autocomplete")
        add(p+"mech_data","adj_stage2","dropdown",f"Finding {k}: which data or instrument mechanism?",data_choices,f"{shown} and {family} = '7'","y",val="autocomplete")
        add(p+"mech_new","adj_stage2","text",f"Finding {k}: name the new mechanism in a few words","",f"{shown} and ([{p}mech] = '{MECH_NEW}' or [{p}mech_data] = '{MECH_NEW}')","y",
            note="It is added to the list, with a new code, between sessions.")
        add(p+"note","adj_stage2","notes",f"Finding {k}: explain the basis","",f"{shown} and {source_specific} and {own}","y")
        # Every other finding had no free text at all unless its release choice
        # opened the proposal box, so a taxonomy, evidence, boundary or
        # unresolved finding could not say what it saw (ADJ-078).  Optional,
        # and shown only where the required basis note is not, so a finding
        # never offers two boxes.
        add(p+"comment","adj_stage2","notes",f"Finding {k}: notes (optional)","",
            f"{shown} and {family} <> '' and (({family} <> '1' and {family} <> '2') or "
            f"([adj_rule_conflict] = '1' and [{p}conflicts({NO_CONFLICT_BASIS})] <> '1'))",
            note="Anything a later reader needs to understand this finding: what the entry or the rules left open, "
                 "or why this family rather than another.")
        # What is released is the model's classifications and the outputs built
        # from them, which is why a coder finding rarely bears on release, and
        # three of the codes carry a second-review cost the reviewer cannot see
        # from the choice list (ADJ-050).
        add(p+"release","adj_stage2","radio",f"Finding {k}: is this case evidence for a later release decision?",RELEASE,shown,"y",
            note="You are nominating the case, not deciding anything: the release decision is made later, on the accumulated evidence. "
                 "Release covers the model's classifications, not the coder benchmark, so record a coder finding as None; a model "
                 "finding is usually Caveat only (ADJ-084). Prompt revision, taxonomy revision and non-release each trigger a "
                 "mandatory second review. If an unclear rule caused the error, add a separate taxonomy finding.")
        proposes="("+" or ".join(f"[{p}release] = '{c}'" for c in RELEASE_PROPOSES)+")"
        add(p+"release_note","adj_stage2","notes",f"Finding {k}: what revision or caveat is proposed?","",f"{shown} and {proposes}","",
            note="Say what should change, and enough of why that someone deciding later, without this case in front of them, can act on it. "
                 "Required for prompt revision, taxonomy revision and non-release, which each commit a second reviewer.")
        if k<FINDING_SLOTS: add(p+"another","adj_stage2","radio",f"Record another finding?","1, Yes | 0, No",shown,"y")
    add("adj_stage2_affirmed","adj_stage2","yesno","Complete Stage 2 assessment?","","[adj_stage2_closure] = '1' or [adj_stage2_closure] = '2'","y")
    # Stage 2 opens only once Stage 1 is affirmed (ADJ-060).  The two forms sit
    # one click apart on the record home page, so nothing but the reviewer's
    # discipline kept the stages in order.  The gate makes the sequence
    # structural: it cannot expose a reveal by accident, and it does not replace
    # holding the reveal import back, which is what evidences the order.
    STAGE2_GATE="[adj_stage1_affirmed] = '1' and [adj_diff_check] = '1'"
    for row in rows:
        if row[1]!="adj_stage2": continue
        row[11]=STAGE2_GATE if not row[11] else f"{STAGE2_GATE} and ({row[11]})"
    return rows
def write_dictionary(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(HEADER);w.writerows(field_rows())
