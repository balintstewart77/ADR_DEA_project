"""Synthetic-only helpers.  This module has no network or production fallback."""
from __future__ import annotations
import copy, csv, hashlib, json, random
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
    return {"assignment_id":case["assignment_id"],"record_id":case["record_id"],"package_id":"PKG_"+stable_id(identity),"seed":seed,"candidates":candidates,"interpretations":interpretations,"qa_flags":sorted({f for c in kept for f in qa_flags(c)})}
def component_labels(package,comp):
    ids={x["interpretation_id"] for x in package["interpretations"][comp]}; labels={}
    for x in package["interpretations"][comp]:
        for label in x["value"]: labels.setdefault(label,set()).add(x["interpretation_id"])
    return ids,labels
def issue(value,choices,label): return [] if value in choices else [f"{label} required"]
def validate_label_assessment(a,omitting,require_omission):
    out=issue(a.get("support"),{1,2,3},"label support"); conflict=a.get("rule_conflict"); out+=issue(conflict,{0,1,2},"label rule-conflict state")
    if conflict==1 and not(a.get("rule_ref") and a.get("rule_note")): out.append("rule conflict needs citation and explanation")
    if conflict==2 and not a.get("rule_note"): out.append("cannot-assess conflict needs explanation")
    selected=set(a.get("omission_ids",[])); state=a.get("omission")
    if require_omission:
        out+=issue(state,{0,1,2},"omission state")
        if state==1 and(not selected or not selected<=set(omitting) or not a.get("omission_note")): out.append("supported omission needs only omitting IDs and explanation")
        if state in {0,2} and selected: out.append("no/cannot-determine omission has no IDs")
        if state==2 and not a.get("omission_note"): out.append("cannot-determine omission needs explanation")
    elif selected: out.append("cannot select omission IDs when no displayed interpretation omits label")
    return out
def validate_tag_assessment(a):
    out=issue(a.get("support"),{1,2,3},"tag support"); conflict=a.get("rule_conflict"); out+=issue(conflict,{0,1,2},"tag conflict")
    if conflict==1 and not(a.get("rule_ref") and a.get("rule_note")): out.append("tag conflict needs citation and explanation")
    if conflict==2 and not a.get("rule_note"): out.append("tag cannot-assess conflict needs explanation")
    state=a.get("supported_status"); out+=issue(state,{0,1,2},"tag alternative-status assessment")
    if state in {1,2} and not a.get("supported_status_note"): out.append("tag alternative-status needs explanation")
    return out
def validate_boundary(a):
    states=set(a.get("states",[])); out=[]
    if not states or not states<={0,1,2,9}: out.append("boundary state required")
    if (0 in states or 9 in states) and len(states)!=1: out.append("no/cannot boundary state is exclusive")
    if states&{1,2} and not a.get("scope"): out.append("recognised/plausible boundary needs scope")
    if 1 in states and not(a.get("rule_ref") and a.get("recognised_note")): out.append("recognised boundary needs citation and explanation")
    if 2 in states and not a.get("plausible_note"): out.append("plausible boundary needs explanation")
    return out
def validate_component(comp,r,p):
    out=[]; pre=f"adj_{comp}_"; ids={x["interpretation_id"] for x in p["interpretations"][comp]}; comparative=len(ids)>1
    fields=("comparative_outcome","best_interpretations","public_evidence","adequacy","defensible_state","defensible_interpretations","defensible_note","weaker","weaker_interpretations","weaker_note","support_note")
    if not comparative:
        for x in fields:
            if pre+x in r: out.append(f"{comp}: comparative {x} is not applicable to one interpretation")
        return out
    outcome=r.get(pre+"comparative_outcome"); best=set(r.get(pre+"best_interpretations",[])); weaker=r.get(pre+"weaker"); weakids=set(r.get(pre+"weaker_interpretations",[])); defensive=r.get(pre+"defensible_state"); defids=set(r.get(pre+"defensible_interpretations",[]))
    out+=issue(r.get(pre+"public_evidence"),{1,2,3,4},f"{comp}: public evidence"); out+=issue(outcome,{1,2,3,4},f"{comp}: comparative outcome"); out+=issue(r.get(pre+"adequacy"),{1,2,3},f"{comp}: absolute adequacy"); out+=issue(defensive,{0,1,2},f"{comp}: defensibility state"); out+=issue(weaker,{0,1,2},f"{comp}: weaker-support state")
    if not(best<=ids and weakids<=ids and defids<=ids): out.append(f"{comp}: unknown interpretation ID")
    if outcome==1 and len(best)!=1: out.append(f"{comp}: unique best requires exactly one ID")
    if outcome==2 and(len(ids)<3 or not 2<=len(best)<len(ids)): out.append(f"{comp}: tied subset requires 3+ interpretations and a proper subset")
    if outcome==3 and(best!=ids or weaker!=0): out.append(f"{comp}: all equal selects all IDs and weaker=No")
    if outcome==4 and best: out.append(f"{comp}: unable to distinguish has no best IDs")
    if best&weakids: out.append(f"{comp}: best interpretation cannot be materially weaker")
    if defensive==1 and not defids: out.append(f"{comp}: identified defensibility needs IDs")
    if defensive in {0,2} and defids: out.append(f"{comp}: None/Cannot judge must not select defensible IDs")
    if defensive==2 and not r.get(pre+"defensible_note"): out.append(f"{comp}: cannot-judge defensibility needs note")
    if weaker==1 and(not weakids or not r.get(pre+"weaker_note")): out.append(f"{comp}: weaker support needs IDs and note")
    if weaker==2 and not r.get(pre+"weaker_note"): out.append(f"{comp}: cannot-judge weaker support needs note")
    if(outcome==4 or r.get(pre+"adequacy") in {2,3} or defensive in {1,2} or weaker in {1,2} or r.get(pre+"public_evidence") in {2,3,4}) and not r.get(pre+"support_note"): out.append(f"{comp}: support note required")
    if pre+"multiple_defensible" in r: out.append(f"{comp}: multiple-defensible is derived and cannot be supplied")
    return out
def validate_submission(r,p):
    out=[]
    if r.get("assignment_id")!=p["assignment_id"]: out.append("assignment mismatch")
    if r.get("package_id")!=p["package_id"]: out.append("package mismatch")
    if r.get("adj_diff_check") not in {1,2}: out.append("generated-difference check required")
    if r.get("adj_diff_check")==2: out.append("generation error blocks Stage 1 completion")
    concerns=set(r.get("adj_concern_scope",[]))
    if not concerns or not concerns<={0,1,2,3,4,5}: out.append("concern scope required")
    if 0 in concerns and len(concerns)!=1: out.append("no-concern scope is exclusive")
    if 5 in concerns and not r.get("adj_concern_other_note"): out.append("other concern needs note")
    exposure=r.get("adj_prior_exposure"); out+=issue(exposure,{0,1,2},"prior exposure")
    if exposure==2 and not(r.get("adj_prior_exposure_source") and r.get("adj_prior_exposure_timing")): out.append("known prior exposure needs source and timing")
    masking=r.get("adj_masking_failure"); out+=issue(masking,{0,1},"masking failure")
    if masking==1 and not r.get("adj_masking_note"): out.append("masking failure needs note")
    status=set(r.get("adj_stage1_case_status",[]))
    if not status or not status<={0,1,2,3}: out.append("Stage 1 case status required")
    if 0 in status and len(status)!=1: out.append("Stage 1 none status is exclusive")
    if status&{1,2,3} and not r.get("adj_stage1_case_status_note"): out.append("Stage 1 case status needs note")
    for comp in COMPONENTS:
        out+=validate_component(comp,r,p); boundary=r.get("boundary",{}).get(comp)
        if boundary is None: out.append(f"{comp}: boundary response required")
        else: out += [f"{comp}: {x}" for x in validate_boundary(boundary)]
    assessments=r.get("label_assessments",{})
    for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
        ids,labels=component_labels(p,comp); comparative=len(ids)>1
        for label,present in labels.items():
            if len(present)<len(ids) or not comparative:
                a=assessments.get(comp,{}).get(label)
                if a is None: out.append(f"{comp}: displayed/differing label {label!r} requires assessment")
                else: out += [f"{comp}: {x}" for x in validate_label_assessment(a,sorted(ids-present),bool(ids-present))]
        shared_state=r.get(f"adj_{comp}_shared_label_state"); shared_ids=set(r.get(f"adj_{comp}_shared_label_ids",[])); shared={x for x,present in labels.items() if present==ids}
        if comparative:
            out+=issue(shared_state,{0,1,2},f"{comp}: shared-label state")
            if shared_state==1 and(not shared_ids or not shared_ids<=shared or not r.get(f"adj_{comp}_shared_label_note")): out.append(f"{comp}: shared labels need permitted IDs and note")
            if shared_state in {0,2} and shared_ids: out.append(f"{comp}: shared None/Cannot judge has no IDs")
            if shared_state==2 and not r.get(f"adj_{comp}_shared_label_note"): out.append(f"{comp}: shared Cannot judge needs note")
        elif any(x in r for x in (f"adj_{comp}_shared_label_state",f"adj_{comp}_shared_label_ids")): out.append(f"{comp}: shared-label controls are comparative only")
        state=r.get(f"adj_{comp}_additional_label_state"); selected=set(r.get(f"adj_{comp}_additional_label_ids",[])); absent=set(vocab)-set(labels); out+=issue(state,{0,1,2},f"{comp}: additional-label state")
        if state==1 and(not selected or not selected<=absent or not r.get(f"adj_{comp}_additional_label_note")): out.append(f"{comp}: additional labels need permitted IDs and note")
        if state in {0,2} and selected: out.append(f"{comp}: additional None/Cannot determine has no IDs")
        if state==2 and not r.get(f"adj_{comp}_additional_label_note"): out.append(f"{comp}: additional Cannot determine needs note")
        for label in shared_ids|selected:
            a=assessments.get(comp,{}).get(label)
            if a is None: out.append(f"{comp}: selected shared/additional label {label!r} needs assessment")
            else: out += [f"{comp}: {x}" for x in validate_label_assessment(a,[],False)]
    for comp in ("covid","equity"):
        a=r.get("tag_assessments",{}).get(comp)
        if a is None: out.append(f"{comp}: tag assessment required")
        else: out += [f"{comp}: {x}" for x in validate_tag_assessment(a)]
    if r.get("adj_stage1_affirmed")!=1: out.append("Stage 1 completion not affirmed")
    return out
def default_valid_submission(p):
    r={"assignment_id":p["assignment_id"],"package_id":p["package_id"],"adj_diff_check":1,"adj_concern_scope":[0],"adj_prior_exposure":0,"adj_masking_failure":0,"adj_stage1_case_status":[0],"boundary":{c:{"states":[0]} for c in COMPONENTS},"label_assessments":{"dom":{},"purp":{}},"tag_assessments":{},"adj_stage1_affirmed":1}
    for comp in COMPONENTS:
        ids=[x["interpretation_id"] for x in p["interpretations"][comp]]
        if len(ids)>1: r.update({f"adj_{comp}_public_evidence":1,f"adj_{comp}_comparative_outcome":1,f"adj_{comp}_best_interpretations":[ids[0]],f"adj_{comp}_adequacy":1,f"adj_{comp}_defensible_state":1,f"adj_{comp}_defensible_interpretations":[ids[0]],f"adj_{comp}_weaker":0,f"adj_{comp}_weaker_interpretations":[],f"adj_{comp}_support_note":"Synthetic comparative basis."})
    for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
        ids,labels=component_labels(p,comp)
        for label,present in labels.items():
            if len(present)<len(ids) or len(ids)==1:r["label_assessments"][comp][label]={"support":1,"rule_conflict":0,"omission":0,"omission_ids":[]}
        if len(ids)>1:r[f"adj_{comp}_shared_label_state"]=0;r[f"adj_{comp}_shared_label_ids"]=[]
        r[f"adj_{comp}_additional_label_state"]=0;r[f"adj_{comp}_additional_label_ids"]=[]
    for comp in ("covid","equity"):r["tag_assessments"][comp]={"support":1,"rule_conflict":0,"supported_status":0}
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
        for r in findings:groups.setdefault(mapping.get(r["mechanism_versioned"],r["mechanism_versioned"]),[]).append(r)
        result={}
        for mech,rows in groups.items():
            records={r["record_id"] for r in rows}; streams={r["stream"] for r in rows if r["pre_reveal"]==1}; pairs={(r["stream"],r["signal_ref"]) for r in rows if r["pre_reveal"]==1}; inclusive=len(records)>=2 or len(streams)>=2; adjudicator_only=len(records)==1 and streams and streams<={"primary","secondary"} and len(streams)>=2
            result[mech]={"distinct_record_count":len(records),"pre_reveal_stream_signal_count":len(pairs),"independent_conservative":inclusive and not adjudicator_only,"independent_inclusive":inclusive}
        return result
    return {"pre_harmonisation":summaries({}),"post_harmonisation":summaries(mapping)}
MULTIPLE_DEFENSIBLE_CALC="if(([{p}defensible_interpretations(1)] + [{p}defensible_interpretations(2)] + [{p}defensible_interpretations(3)] + [{p}defensible_interpretations(4)]) >= 2, 1, 0)"
CORRECTION_KEYS=("field","original_value","corrected_value","reason","author","date")
REFLECTION_KEYS=("scope","reflection","author","date")

def derive_stage1(response,package):
    """Derived, read-only Stage 1 indicators.  Never reviewer-entered.

    adj_[component]_multiple_defensible is 1 when two or more distinct
    interpretation IDs are selected as defensible and 0 otherwise.  It is
    omitted for a single-interpretation component, where the comparative
    defensibility fields are not applicable.
    """
    derived={}
    for comp in COMPONENTS:
        ids={x["interpretation_id"] for x in package["interpretations"][comp]}
        if len(ids)<2: continue
        pre=f"adj_{comp}_"
        selected=set(response.get(pre+"defensible_interpretations",[]))&ids if response.get(pre+"defensible_state")==1 else set()
        derived[pre+"multiple_defensible"]=int(len(selected)>=2)
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
def reveal(a,p,h,payload,store,simulate_partial=False):
    if "snapshot" not in store:raise PermissionError("premature reveal rejected: no preserved snapshot")
    verify_snapshot(store)
    if(a,p,h)!=(store["snapshot"]["assignment_id"],store["snapshot"]["package_id"],store["snapshot_hash"]):raise PermissionError("assignment, package, or snapshot mismatch")
    if simulate_partial:
        store.setdefault("exposure_history",[]).append({"assignment_id":a,"source_information":"synthetic source-reveal mapping potentially accessible","accessibility":"potential","viewing":"unknown","extent":"unknown","at":datetime.now(timezone.utc).isoformat()});store.setdefault("events",[]).append({"event":"reveal_failed_partial","at":datetime.now(timezone.utc).isoformat()});raise RuntimeError("simulated partial reveal failure")
    store.setdefault("events",[]).append({"event":"reveal_recovered" if store.get("exposure_history") else "reveal_complete","at":datetime.now(timezone.utc).isoformat()});return {"assignment_id":a,"package_id":p,"sources":payload[a]}

REVIEWER_ROLES=((1,"primary",""),(2,"secondary","_SEC"))
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
    out={}; diff_dimensions=[]; diff_labels=[]; diff_tags=[]
    for comp in COMPONENTS:
        interpretations=package["interpretations"][comp]; slots=slot_map(package,comp)
        out[f"adj_{comp}_interpretation_map"]="; ".join(f"Slot {slots[x['interpretation_id']]} = {x['interpretation_id']}: {', '.join(x['value']) if isinstance(x['value'],list) else x['value']} [displayed candidates {', '.join(x['candidate_ids'])}]" for x in interpretations)
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
            out[f"adj_{comp}_l{n:02d}_membership"]=text
    for tag in ("covid","equity"):
        slots=slot_map(package,tag); parts=[]
        for status in ("Applied","Not applied"):
            carrying=sorted(slots[x["interpretation_id"]] for x in package["interpretations"][tag] if x["value"]==status)
            parts.append(f"{status}: "+(", ".join(f"slot {n}" for n in carrying) if carrying else "no displayed interpretation"))
        out[f"adj_{tag}_status_membership"]="; ".join(parts)
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
            row={"adj_assignment_id":package["assignment_id"],"redcap_data_access_group":group,"adj_source_record_id":case["record_id"],"adj_reviewer_role":role,"adj_stage1_package_id":package["package_id"],**generated_evidence(package)}
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
    def add(n,f,t,l,c="",b="",req="",a=""):
        rows.append([n,f,"",t,l,c,"Candidate offline dictionary; not REDCap-import-tested.","","","","",b,req,"","","","",a])
    # REDCap takes the FIRST field as the record identifier, and that identifier
    # appears in record lists, URLs, logs and every export.  The opaque
    # assignment ID is therefore first; the stable source Record ID stays a
    # hidden field for restricted joins and must never become the record key.
    add("adj_assignment_id","adj_admin","text","Synthetic assignment ID (record key)",req="y");add("adj_source_record_id","adj_admin","text","Stable source Record ID (administrative join)",a="@HIDDEN");add("adj_reviewer_role","adj_admin","radio","Reviewer role","1, Primary | 2, Secondary","","y","@HIDDEN");add("adj_stage1_package_id","adj_admin","text","Masked package ID",a="@READONLY")
    for n,l in (("adj_diff_dimensions","Read-only generated affected dimensions"),("adj_diff_labels","Read-only generated differing labels"),("adj_diff_tag_statuses","Read-only generated differing tag statuses")):add(n,"adj_stage1","notes",l,a="@READONLY")
    add("adj_diff_check","adj_stage1","radio","Are generated displayed differences accurate?","1, Accurate | 2, Generation error","","y");add("adj_diff_error_note","adj_stage1","notes","Describe generated-difference error","","[adj_diff_check] = '2'")
    add("adj_concern_scope","adj_stage1","checkbox","Reviewer-identified concern beyond generated differences","1, Research Domains | 2, Analytical Purposes | 3, COVID-19/pandemic | 4, Equity | 5, Other | 0, No concern beyond generated differences","","y","@NONEOFTHEABOVE='0'");add("adj_concern_other_note","adj_stage1","notes","Describe other concern","","[adj_concern_scope(5)] = '1'")
    add("adj_prior_exposure","adj_stage1","radio","Prior exposure to source-specific classification","0, None | 1, Possible | 2, Known","","y");add("adj_prior_exposure_source","adj_stage1","text","Known prior-exposure source","","[adj_prior_exposure] = '2'");add("adj_prior_exposure_timing","adj_stage1","text","Known prior-exposure timing","","[adj_prior_exposure] = '2'")
    add("adj_masking_failure","adj_stage1","radio","Masking failure or accidental disclosure?","0, No | 1, Yes","","y");add("adj_masking_note","adj_stage1","notes","Describe masking failure","","[adj_masking_failure] = '1'")
    add("adj_stage1_case_status","adj_stage1","checkbox","Stage 1 record-level status","1, Insufficiently evidenced | 2, Multiply defensible | 3, Unresolved at Stage 1 | 0, None of these","","y","@NONEOFTHEABOVE='0'");add("adj_stage1_case_status_note","adj_stage1","notes","Explain Stage 1 status","","[adj_stage1_case_status(1)] = '1' or [adj_stage1_case_status(2)] = '1' or [adj_stage1_case_status(3)] = '1'")
    slots="1, Interpretation slot 1 | 2, Interpretation slot 2 | 3, Interpretation slot 3 | 4, Interpretation slot 4"
    for comp in COMPONENTS:
        label={"dom":"Research Domains","purp":"Analytical Purposes","covid":"COVID-19/pandemic tag","equity":"Demographic disparities/equity tag"}[comp];p=f"adj_{comp}_"
        add(p+"interpretation_map","adj_stage1","notes",f"Read-only generated {label} interpretation map",a="@READONLY");add(p+"public_evidence","adj_stage1","radio",f"{label}: public-entry sufficiency","1, Sufficient to distinguish | 2, Partly sufficient or ambiguous | 3, Insufficient to distinguish | 4, Cannot assess sufficiency")
        add(p+"comparative_outcome","adj_stage1","radio",f"{label}: relative support","1, Unique relatively best | 2, Tied proper subset | 3, All equally supported | 4, Unable to distinguish");add(p+"best_interpretations","adj_stage1","checkbox",f"{label}: best interpretation slots",slots,f"[{p}comparative_outcome] = '1' or [{p}comparative_outcome] = '2' or [{p}comparative_outcome] = '3'")
        add(p+"adequacy","adj_stage1","radio",f"{label}: absolute adequacy","1, At least one adequate | 2, None adequate | 3, Cannot judge");add(p+"defensible_state","adj_stage1","radio",f"{label}: displayed defensibility","0, None | 1, Identified interpretations | 2, Cannot judge");add(p+"defensible_interpretations","adj_stage1","checkbox",f"{label}: defensible interpretation slots",slots,f"[{p}defensible_state] = '1'");add(p+"defensible_note","adj_stage1","notes",f"{label}: defensibility note","",f"[{p}defensible_state] = '2'");add(p+"multiple_defensible","adj_stage1","calc",f"{label}: derived multiple-defensible",MULTIPLE_DEFENSIBLE_CALC.format(p=p))
        add(p+"weaker","adj_stage1","radio",f"{label}: materially weaker support","0, No | 1, Yes | 2, Cannot judge");add(p+"weaker_interpretations","adj_stage1","checkbox",f"{label}: materially weaker slots",slots,f"[{p}weaker] = '1'");add(p+"weaker_note","adj_stage1","notes",f"{label}: weaker-support note","",f"[{p}weaker] = '1' or [{p}weaker] = '2'");add(p+"support_note","adj_stage1","notes",f"{label}: comparative support note")
        add(p+"boundary_state","adj_stage1","checkbox",f"{label}: boundary assessment","1, Recognised boundary | 2, Plausible boundary | 0, No boundary | 9, Cannot judge","","y","@NONEOFTHEABOVE='0,9'");add(p+"boundary_scope","adj_stage1","notes",f"{label}: boundary scope","",f"[{p}boundary_state(1)] = '1' or [{p}boundary_state(2)] = '1'");add(p+"recognised_boundary_rule_ref","adj_stage1","text",f"{label}: frozen rule citation","",f"[{p}boundary_state(1)] = '1'");add(p+"recognised_boundary_note","adj_stage1","notes",f"{label}: recognised-boundary explanation","",f"[{p}boundary_state(1)] = '1'");add(p+"plausible_boundary_note","adj_stage1","notes",f"{label}: plausible-boundary explanation","",f"[{p}boundary_state(2)] = '1'")
    for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
        p=f"adj_{comp}_"
        for i,label in enumerate(vocab,1):
            c=f"l{i:02d}";add(p+c+"_membership","adj_stage1","notes",f"Read-only generated membership: {label}",a="@READONLY");add(p+c+"_support","adj_stage1","radio",f"{label}: visible-public-entry support","1, Supported | 2, Not supported | 3, Cannot determine");add(p+c+"_rule_conflict","adj_stage1","radio",f"{label}: explicit taxonomy-rule conflict","0, No | 1, Possible/confirmed | 2, Cannot assess");add(p+c+"_rule_ref","adj_stage1","text",f"{label}: rule/counterexample citation","",f"[{p}{c}_rule_conflict] = '1'");add(p+c+"_rule_note","adj_stage1","notes",f"{label}: rule-conflict explanation","",f"[{p}{c}_rule_conflict] = '1' or [{p}{c}_rule_conflict] = '2'");add(p+c+"_omission","adj_stage1","radio",f"{label}: supported omission","0, No supported omission | 1, Omission overlooks supported label | 2, Cannot determine");add(p+c+"_omission_interpretations","adj_stage1","checkbox",f"{label}: omitting interpretation slots",slots,f"[{p}{c}_omission] = '1'");add(p+c+"_omission_note","adj_stage1","notes",f"{label}: omission explanation","",f"[{p}{c}_omission] = '1' or [{p}{c}_omission] = '2'")
        choices=" | ".join(f"{i}, {x}" for i,x in enumerate(vocab,1));add(p+"shared_label_state","adj_stage1","radio",f"{comp}: problematic shared labels","0, None identified | 1, Identified | 2, Cannot judge");add(p+"shared_label_ids","adj_stage1","checkbox",f"{comp}: shared-label IDs",choices,f"[{p}shared_label_state] = '1'");add(p+"shared_label_note","adj_stage1","notes",f"{comp}: shared-label explanation","",f"[{p}shared_label_state] = '1' or [{p}shared_label_state] = '2'");add(p+"additional_label_state","adj_stage1","radio",f"{comp}: supported labels absent from every candidate","0, None identified | 1, Identified | 2, Cannot determine");add(p+"additional_label_ids","adj_stage1","checkbox",f"{comp}: absent-label IDs",choices,f"[{p}additional_label_state] = '1'");add(p+"additional_label_note","adj_stage1","notes",f"{comp}: additional-label explanation","",f"[{p}additional_label_state] = '1' or [{p}additional_label_state] = '2'")
    for tag in ("covid","equity"):
        p=f"adj_{tag}_";add(p+"status_membership","adj_stage1","notes",f"Read-only generated membership for {tag}",a="@READONLY");add(p+"status_support","adj_stage1","radio",f"{tag}: displayed tag-status support","1, Supported | 2, Not supported | 3, Cannot determine");add(p+"rule_conflict","adj_stage1","radio",f"{tag}: explicit taxonomy-rule conflict","0, No | 1, Possible/confirmed | 2, Cannot assess");add(p+"rule_ref","adj_stage1","text",f"{tag}: rule citation","",f"[{p}rule_conflict] = '1'");add(p+"rule_note","adj_stage1","notes",f"{tag}: rule-conflict explanation","",f"[{p}rule_conflict] = '1' or [{p}rule_conflict] = '2'");add(p+"supported_status","adj_stage1","radio",f"{tag}: support for opposite status","0, No alternative supported | 1, Opposite status supported | 2, Cannot determine");add(p+"supported_status_note","adj_stage1","notes",f"{tag}: opposite-status explanation","",f"[{p}supported_status] = '1' or [{p}supported_status] = '2'")
    add("adj_stage1_affirmed","adj_stage1","yesno","Complete preserved Stage 1 assessment?","","","y");add("adj_reveal_state","adj_stage2","radio","Stage 2 reveal state","0, Not revealed | 1, Revealed | 2, Partial-failure exposure");add("adj_stage2_closure","adj_stage2","radio","Stage 2 closure","1, Completed with findings | 2, Completed no assignable issue | 3, Incomplete | 4, Administrative closure");add("adj_no_issue_rationale","adj_stage2","notes","Short rationale for no assignable issue","","[adj_stage2_closure] = '2'")
    return rows
def write_dictionary(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(HEADER);w.writerows(field_rows())
