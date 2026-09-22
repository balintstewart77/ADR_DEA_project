import copy, csv, json, re, sys, unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"scripts"))
from prototype_lib import (COMPONENTS,DOMAINS,HEADER,data_quality_rules,comparative_components,component_labels,generated_evidence,IMPORT_FORBIDDEN,import_rows,slot_map,OWNER_CHECKBOX_FIELDS,OWNER_RADIO_FIELDS,OWNER_VIS_FIELDS,PURPOSES,ROOT,aggregate_independence,default_valid_submission,derive_stage1,derive_sufficiency,field_rows,load_json,owner_trigger,package_case,preserve,record_correction,record_reflection,reveal,validate_submission,verify_snapshot)

FROZEN_OWNER=ROOT.parents[3]/"preregistration"/"package"/"06_redcap"/"DEAValidationStudyProjectOwner_DataDictionary_frozen_2026-08-24.csv"

def frozen_owner_rows():
    with FROZEN_OWNER.open(encoding="utf-8-sig",newline="") as f: return {x["Variable / Field Name"]:x for x in csv.DictReader(f)}
def choice_codes(row): return {int(entry.split(",",1)[0].strip()) for entry in row["Choices, Calculations, OR Slider Labels"].split(" | ")}

def redcap_shows(branch,context):
    """Evaluate the REDCap branching subset used in the candidate dictionary.

    Supports [field] and [field(code)] references, = and <>, and/or, and
    parentheses.  Unanswered fields read as blank; unticked options as '0'.
    """
    if not branch.strip(): return True
    def value(match):
        name,code=match.group(1),match.group(2)
        if code is not None: return repr("1" if int(code) in context.get(name,[]) else "0")
        return repr(str(context.get(name,"")))
    expression=re.sub(r"\[([a-z0-9_]+)(?:\((\d+)\))?\]",value,branch).replace("<>","!=").replace(" = "," == ")
    return bool(eval(expression,{"__builtins__":{}},{}))
def hidden_choices(annotation,context):
    """Resolve nested @IF(...) to the @HIDECHOICE codes it applies, if any."""
    text=annotation[annotation.index("@IF("):].strip() if "@IF(" in annotation else ""
    while text.startswith("@IF("):
        depth=0; quote=None; parts=[]; start=4
        for i in range(4,len(text)):
            ch=text[i]
            if quote:
                if ch==quote: quote=None
                continue
            if ch in "'\"": quote=ch
            elif ch=="(": depth+=1
            elif ch==")":
                if depth==0: parts.append(text[start:i]); break
                depth-=1
            elif ch=="," and depth==0: parts.append(text[start:i]); start=i+1
        condition,when_true,when_false=[x.strip() for x in parts]
        text=when_true if redcap_shows(condition,context) else when_false
    if text.startswith("@HIDECHOICE="): return {int(x) for x in text.split("=",1)[1].strip("'").split(",")}
    return set()
class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=load_json("cases.json"); cls.packages=[package_case(x) for x in cls.cases]; cls.submissions=load_json("submissions.json")
    def test_all_three_generated_valid_fixtures_pass(self):
        self.assertEqual(len(self.submissions),3)
        for package,response in zip(self.packages,self.submissions): self.assertEqual(validate_submission(response,package),[])
    def test_canonical_order_duplicate_collapse_and_gpt_exclusion(self):
        c={"record_id":"SYN_ADJ_CANON","assignment_id":"SYN_ASSIGN_CANON","classifications":[{"source_type":"fable","domains":[DOMAINS[5],DOMAINS[2]],"purposes":[PURPOSES[1]],"covid":"Applied","equity":"Not applied"},{"source_type":"scratch","domains":[DOMAINS[2],DOMAINS[5]],"purposes":[PURPOSES[1]],"covid":"Applied","equity":"Not applied"},{"source_type":"gpt55","rationale":"excluded","domains":[DOMAINS[0]],"purposes":[PURPOSES[0]],"covid":"Applied","equity":"Applied"}]}
        p=package_case(c); self.assertEqual(len(p["candidates"]),1); self.assertEqual(len(p["interpretations"]["dom"]),1); self.assertEqual(p["candidates"][0]["domains"],[DOMAINS[2],DOMAINS[5]]); self.assertNotIn("gpt55",json.dumps(p).lower())
    def test_per_reviewer_order_and_package_identity(self):
        classifications=[{"source_type":"fable" if i==0 else "scratch","domains":[DOMAINS[i]],"purposes":[PURPOSES[i]],"covid":"Applied" if i%2 else "Not applied","equity":"Applied" if i>1 else "Not applied"} for i in range(4)]
        orders=[]; contents=[]
        for n in range(6):
            p=package_case({"record_id":"SYN_ADJ_ORDER","assignment_id":f"SYN_ASSIGN_ORDER_{n}","classifications":classifications}); orders.append([x["candidate_id"] for x in p["candidates"]]); contents.append(sorted(x["candidate_id"] for x in p["candidates"]))
        self.assertTrue(all(x==contents[0] for x in contents)); self.assertGreater(len({tuple(x) for x in orders}),1)
    def test_qa_flags_preserve_values_and_block_preservation(self):
        cases=[("empty_domains",[],[PURPOSES[0]],"Applied","Applied"),("empty_purposes",[DOMAINS[0]],[],"Applied","Applied"),("too_many_purposes",[DOMAINS[0]],PURPOSES[:3],"Applied","Applied"),("unknown_domains_label",["Synthetic unknown"],[PURPOSES[0]],"Applied","Applied"),("unknown_purposes_label",[DOMAINS[0]],["Synthetic unknown"],"Applied","Applied"),("unclear_combined_domains",[DOMAINS[-1],DOMAINS[0]],[PURPOSES[0]],"Applied","Applied"),("unclear_combined_purposes",[DOMAINS[0]],[PURPOSES[-1],PURPOSES[0]],"Applied","Applied"),("invalid_covid_tag",[DOMAINS[0]],[PURPOSES[0]],"Neither","Applied"),("invalid_equity_tag",[DOMAINS[0]],[PURPOSES[0]],"Applied","Neither")]
        for flag,domains,purposes,covid,equity in cases:
            raw={"source_type":"fable","domains":domains,"purposes":purposes,"covid":covid,"equity":equity}; c={"record_id":"SYN_ADJ_QA","assignment_id":"SYN_ASSIGN_QA_"+flag,"classifications":[raw]}; p=package_case(c)
            self.assertIn(flag,p["qa_flags"]); self.assertEqual(raw["domains"],domains); self.assertEqual(raw["purposes"],purposes)
            with self.assertRaises(ValueError): preserve(default_valid_submission(p),p,{})
    def test_required_status_and_single_set_failures(self):
        p=self.packages[2]; empty={"assignment_id":p["assignment_id"],"package_id":p["package_id"]}; issues=validate_submission(empty,p)
        self.assertTrue(any("generated-difference" in x for x in issues)); self.assertTrue(any("displayed label" in x for x in issues)); self.assertTrue(any("tag assessment" in x for x in issues))
        self.assertIn("boundary state required",issues); self.assertTrue(any("masking failure required" in x for x in issues))
        bad=copy.deepcopy(self.submissions[2]); del bad["adj_boundary"]; self.assertIn("boundary state required",validate_submission(bad,p))
    def test_lean_comparative_judgements_are_enforced(self):
        # Per differing component: evidence, relative support (ties named),
        # sufficient support and defensible options (ADJ-040).
        p=self.packages[0]; base=copy.deepcopy(self.submissions[0]); self.assertEqual(validate_submission(base,p),[])
        self.assertEqual(comparative_components(p),["dom"])
        for key in ("adj_dom_evidence","adj_dom_best","adj_dom_adequacy","adj_dom_defensible","adj_rule_conflict"):
            bad=copy.deepcopy(base); del bad[key]; self.assertTrue(validate_submission(bad,p),key)
        for best in ([1],[2],[1,2],[6]):
            ok=copy.deepcopy(base); ok["adj_dom_best"]=best; self.assertEqual(validate_submission(ok,p),[],best)
        for best,phrase in (([3],"not displayed"),([1,6],"exclusive"),([],"required")):
            bad=copy.deepcopy(base); bad["adj_dom_best"]=best; self.assertTrue(any(phrase in x for x in validate_submission(bad,p)),best)
        for defensible in ([1],[1,2],[0],[9]):
            ok=copy.deepcopy(base); ok["adj_dom_defensible"]=defensible; self.assertEqual(validate_submission(ok,p),[],defensible)
        for defensible,phrase in (([3],"not displayed"),([0,1],"exclusive"),([0,9],"exclusive"),([],"required")):
            bad=copy.deepcopy(base); bad["adj_dom_defensible"]=defensible; self.assertTrue(any(phrase in x for x in validate_submission(bad,p)),defensible)
        bad=copy.deepcopy(base); bad["adj_rule_conflict"]=1; issues=validate_submission(bad,p)
        self.assertTrue(any("rule conflict needs its component scope" in x for x in issues)); self.assertTrue(any("citation and explanation" in x for x in issues))
        bad.update({"adj_rule_conflict_scope":[1],"adj_rule_conflict_ref":"SYN-RULE-1","adj_rule_conflict_note":"Synthetic"})
        issues=validate_submission(bad,p)
        self.assertTrue(any("conflicting option" in x for x in issues)); self.assertTrue(any("label(s) concerned" in x for x in issues))
        bad["adj_dom_conflict_slots"]=[2]; bad["adj_dom_conflict_labels"]=[DOMAINS[0]]
        self.assertTrue(any("label(s) concerned" in x for x in validate_submission(bad,p)),"label not in any displayed option")
        bad["adj_dom_conflict_labels"]=[DOMAINS[2]]; self.assertEqual(validate_submission(bad,p),[])
        bad["adj_dom_conflict_slots"]=[3]; self.assertTrue(any("conflicting option" in x for x in validate_submission(bad,p)))
        shared=copy.deepcopy(base); shared.update({"adj_rule_conflict":1,"adj_rule_conflict_scope":[2],"adj_rule_conflict_ref":"SYN-RULE-3","adj_rule_conflict_note":"Synthetic","adj_purp_conflict_labels":[PURPOSES[1]]})
        self.assertEqual(validate_submission(shared,p),[],"a shared Purpose can conflict; no option choice is asked where it does not differ")
        bad=copy.deepcopy(base); bad["adj_rule_conflict"]=2; self.assertTrue(any("cannot-judge rule conflict" in x for x in validate_submission(bad,p)))
        bad=copy.deepcopy(base); bad["adj_purp_best"]=[1]; self.assertTrue(any("does not differ" in x for x in validate_submission(bad,p)))
    def test_single_set_and_comparative_paths_do_not_mix(self):
        # Comparative records get the record-level judgements; the owner-only
        # single set gets §9.2's per-label checks and additional-label question.
        comparative=self.packages[0]; single=self.packages[2]
        base=copy.deepcopy(self.submissions[0]); single_response=copy.deepcopy(self.submissions[2])
        for field in ("label_assessments","tag_assessments","adj_dom_additional_label_state"): self.assertNotIn(field,base)
        for field in ("adj_dom_additional_label_state","adj_dom_additional_label_ids"):
            bad=copy.deepcopy(base); bad[field]=0 if field.endswith("state") else []
            self.assertTrue(any("single-set questions do not apply" in x for x in validate_submission(bad,comparative)),field)
        self.assertIn("adj_dom_additional_label_state",single_response); self.assertEqual(validate_submission(single_response,single),[])
        missing=copy.deepcopy(single_response); del missing["adj_dom_additional_label_state"]
        self.assertTrue(any("additional-label state required" in x for x in validate_submission(missing,single)))
        for field,value in (("adj_dom_evidence",1),("adj_dom_best",[1]),("adj_rule_conflict",0),("adj_dom_conflict_labels",[DOMAINS[6]])):
            bad=copy.deepcopy(single_response); bad[field]=value
            self.assertTrue(any("comparative questions do not apply" in x for x in validate_submission(bad,single)),field)
        opened=copy.deepcopy(single_response); opened.update({"adj_dom_additional_label_state":1,"adj_dom_additional_label_ids":[DOMAINS[0]],"adj_dom_additional_label_note":"Synthetic"})
        self.assertTrue(any("selected additional label" in x for x in validate_submission(opened,single)))
        opened["label_assessments"]["dom"][DOMAINS[0]]={"support":1,"rule_conflict":0}; self.assertEqual(validate_submission(opened,single),[])
    def test_diff_and_record_status_controls(self):
        p=self.packages[0]; base=self.submissions[0]
        bad=copy.deepcopy(base); bad["adj_diff_check"]=2; self.assertIn("generation error blocks Stage 1 completion",validate_submission(bad,p))
        for field,label in (("adj_masking_failure","masking failure"),("adj_other_concern","other concern"),("adj_stage1_unresolved","unresolved at Stage 1")):
            bad=copy.deepcopy(base); bad[field]=1; self.assertIn(f"{label} needs explanation",validate_submission(bad,p),field)
            bad=copy.deepcopy(base); del bad[field]; self.assertIn(f"{label} required",validate_submission(bad,p),field)
        unsure=copy.deepcopy(base); unsure["adj_masking_failure"]=2; self.assertIn("masking failure needs explanation",validate_submission(unsure,p))
        unsure["adj_masking_note"]="Synthetic: the phrasing felt familiar."; self.assertEqual(validate_submission(unsure,p),[])
        bad=copy.deepcopy(base); bad["adj_boundary"]=[0,1]; self.assertIn("no/cannot boundary state is exclusive",validate_submission(bad,p))
        bad=copy.deepcopy(base); bad["adj_boundary"]=[1]; issues=validate_submission(bad,p)
        for phrase in ("component scope","needs explanation","frozen rule citation"): self.assertTrue(any(phrase in x for x in issues),phrase)
        bad.update({"adj_boundary_scope":[2],"adj_boundary_rule_ref":"SYN-RULE-2","adj_boundary_note":"Synthetic"}); self.assertEqual(validate_submission(bad,p),[])
        bad=copy.deepcopy(base); bad["adj_boundary"]=[2]; bad["adj_boundary_scope"]=[1]; bad["adj_boundary_note"]="Synthetic"; self.assertEqual(validate_submission(bad,p),[])
        bad=copy.deepcopy(base); bad["adj_boundary_scope"]=[1]; self.assertTrue(any("boundary scope is only recorded" in x for x in validate_submission(bad,p)))
    def test_append_only_preservation_and_partial_reveal_recovery(self):
        p=self.packages[0]; response=self.submissions[0]; store={}; h=preserve(response,p,store); original=store["snapshot_hash"]
        with self.assertRaises(RuntimeError): preserve(response,p,store)
        self.assertEqual(original,store["snapshot_hash"]); self.assertEqual(store["events"][-1]["event"],"preserve_rejected_existing_snapshot")
        with self.assertRaises(RuntimeError): reveal(p["assignment_id"],p["package_id"],h,load_json("reveal_payloads.json"),store,True)
        self.assertEqual(store["snapshot_hash"],h); self.assertEqual(store["exposure_history"][0]["extent"],"unknown")
        reveal(p["assignment_id"],p["package_id"],h,load_json("reveal_payloads.json"),store); self.assertTrue(store["exposure_history"])
    def test_sufficiency_and_independence_timing(self):
        self.assertEqual(derive_sufficiency(["Sufficient","Sufficient","Insufficient"]),{"broad":1,"strict":1}); self.assertEqual(derive_sufficiency(["Sufficient"]),{"broad":8,"strict":8})
        f=[{"record_id":"SYN_A","mechanism_versioned":"M1","stream":"scratch","signal_ref":"S1","pre_reveal":1},{"record_id":"SYN_A","mechanism_versioned":"M1","stream":"primary","signal_ref":"P1","pre_reveal":0},{"record_id":"SYN_B","mechanism_versioned":"M2","stream":"primary","signal_ref":"P2","pre_reveal":1},{"record_id":"SYN_B","mechanism_versioned":"M2","stream":"secondary","signal_ref":"S2","pre_reveal":1},{"record_id":"SYN_C","mechanism_versioned":"M3","stream":"scratch","signal_ref":"U","pre_reveal":2},{"record_id":"SYN_C","mechanism_versioned":"M3","stream":"scratch","signal_ref":"U","pre_reveal":2}]
        r=aggregate_independence(f,{"M1":"H1","M2":"H2","M3":"H3"}); pre=r["pre_harmonisation"]
        self.assertFalse(pre["M1"]["independent_conservative"]); self.assertFalse(pre["M2"]["independent_conservative"]); self.assertTrue(pre["M2"]["independent_inclusive"]); self.assertEqual(pre["M3"]["pre_reveal_stream_signal_count"],0); self.assertIn("H2",r["post_harmonisation"])
        with self.assertRaises(ValueError): aggregate_independence([{**f[0],"pre_reveal":True}],{})
    def test_owner_trigger_qualifying_conditions_on_export_shaped_rows(self):
        # Every row below is export-shaped: string codes, one column per checkbox option.
        for row in ({"po_d01_fit":"2"},{"po_d04_fit":"3"},{"po_p02_fit":"2"}):
            self.assertEqual(owner_trigger(row)["reasons"],["fit_verdict"],row)
        for row in ({"po_t01_correct":"0"},{"po_t02_correct":"2"}):
            self.assertEqual(owner_trigger(row)["reasons"],["tag_correctness"],row)
        for row in ({"po_miss_domains___3":"1"},{"po_miss_purposes___7":"1"},{"po_miss_tags___2":"1"}):
            self.assertEqual(owner_trigger(row)["reasons"],["missing_label"],row)
        for row in ({"po_sufficiency":"2"},{"po_sufficiency":"3"}):
            self.assertEqual(owner_trigger(row)["reasons"],["public_sufficiency"],row)
        self.assertEqual(owner_trigger({"po_tax_issue___1":"1"})["reasons"],["taxonomy_issue"])
        self.assertEqual(owner_trigger({"po_tax_issue___5":"1"})["reasons"],["taxonomy_issue"])
        self.assertFalse(owner_trigger({"po_d01_fit":"1","po_t01_correct":"1","po_sufficiency":"1"})["qualifies"])
        combined=owner_trigger({"po_d01_fit":"2","po_t01_correct":"0","po_miss_tags___1":"1","po_sufficiency":"3","po_tax_issue___2":"1"})
        self.assertEqual(combined["reasons"],["fit_verdict","tag_correctness","missing_label","public_sufficiency","taxonomy_issue"])
    def test_owner_trigger_ignores_free_text_and_unselected_options(self):
        unselected=owner_trigger({"po_miss_domains___3":"0","po_tax_issue___1":"0"})
        self.assertFalse(unselected["qualifies"]); self.assertEqual(unselected["reasons"],[])
        blank=owner_trigger({"po_d01_fit":"","po_sufficiency":"   ","po_miss_tags___1":None})
        self.assertFalse(blank["qualifies"])
        basis=owner_trigger({"po_miss_domain_basis":"Synthetic free-text basis."})
        self.assertFalse(basis["qualifies"]); self.assertEqual(basis["ignored_fields"],["po_miss_domain_basis"])
        noise=owner_trigger({"po_miss_purpose_basis":"x","po_miss_tag_basis":"x","po_suff_explain":"x","po_tax_explain":"x","po_other_comment":"x","po_intro":"x","po_d01_display":"x","po_miss_domain_reminder":"x","record_id":"SYN_OWNER_1"})
        self.assertFalse(noise["qualifies"])
        self.assertEqual(noise["ignored_fields"],["po_d01_display","po_intro","po_miss_domain_reminder","po_miss_purpose_basis","po_miss_tag_basis","po_other_comment","po_suff_explain","po_tax_explain","record_id"])
    def test_owner_trigger_visibility_and_taxonomy_fit_states(self):
        for field in OWNER_VIS_FIELDS:
            result=owner_trigger({field:"0"})
            self.assertEqual(result,{"qualifies":False,"reasons":[],"taxonomy_fit_only_status":"not_applicable","visibility_diagnostic_only":True,"ignored_fields":[]},field)
        self.assertFalse(owner_trigger({"po_d01_vis":"2","po_p01_vis":"3","po_t01_vis":"1"})["qualifies"])
        self.assertTrue(owner_trigger({"po_d01_vis":"0","po_sufficiency":"3"})["qualifies"])
        self.assertFalse(owner_trigger({"po_d01_vis":"0","po_sufficiency":"3"})["visibility_diagnostic_only"])
        for code in ("2","3"):
            self.assertEqual(owner_trigger({"po_taxonomy_fit":code})["taxonomy_fit_only_status"],"unresolved")
        self.assertFalse(owner_trigger({"po_taxonomy_fit":"2"})["qualifies"])
        self.assertEqual(owner_trigger({"po_taxonomy_fit":"1"})["taxonomy_fit_only_status"],"not_applicable")
        self.assertEqual(owner_trigger({"po_taxonomy_fit":"3","po_tax_issue___2":"1"})["taxonomy_fit_only_status"],"not_applicable")
    def test_owner_trigger_rejects_unknown_and_invalid_codes(self):
        for row in ({"po_d01_fit":"7"},{"po_t01_correct":"9"},{"po_sufficiency":"0"},{"po_taxonomy_fit":"4"},{"po_d01_vis":"5"},
                    {"po_d01_fit":"Does not fit"},{"po_miss_domains___3":"2"},{"po_miss_domains___99":"1"},{"po_tax_issue___3":"1"},
                    {"po_tax_issue":"1"},{"po_miss_domains":"3"},{"po_d01_fit___2":"1"},{"po_miss_domains___x":"1"}):
            with self.assertRaises(ValueError,msg=row): owner_trigger(row)
    def test_owner_allow_list_matches_frozen_dictionary(self):
        rows=frozen_owner_rows()
        self.assertTrue(set(OWNER_RADIO_FIELDS)|set(OWNER_CHECKBOX_FIELDS)<=set(rows))
        for field,(valid,qualifying,reason) in OWNER_RADIO_FIELDS.items():
            self.assertEqual(rows[field]["Field Type"],"radio",field)
            self.assertEqual(choice_codes(rows[field]),set(valid),field)
            self.assertTrue(set(qualifying)<=set(valid),field)
            self.assertEqual(bool(qualifying),bool(reason),field)
        for field,(options,reason) in OWNER_CHECKBOX_FIELDS.items():
            self.assertEqual(rows[field]["Field Type"],"checkbox",field)
            self.assertEqual(choice_codes(rows[field]),set(options),field)
            self.assertTrue(reason)
        for field in set(OWNER_RADIO_FIELDS)|set(OWNER_CHECKBOX_FIELDS):
            self.assertNotIn(rows[field]["Field Type"],{"notes","text","descriptive"},field)
        # Free-text and descriptive owner fields must never reach the allow-list.
        for field,row in rows.items():
            if row["Field Type"] in {"notes","text","descriptive"}:
                self.assertNotIn(field,OWNER_RADIO_FIELDS,field); self.assertNotIn(field,OWNER_CHECKBOX_FIELDS,field)
    def test_preserved_snapshot_is_copied_and_integrity_checked(self):
        package=self.packages[0]; response=copy.deepcopy(self.submissions[0]); store={}
        h=preserve(response,package,store); self.assertEqual(verify_snapshot(store),h)
        response["adj_dom_adequacy"]=3; response["adj_boundary"].append(9); package["qa_flags"].append("synthetic_late_flag")
        self.assertEqual(store["snapshot"]["response"]["adj_dom_adequacy"],1)
        self.assertEqual(store["snapshot"]["response"]["adj_boundary"],self.submissions[0]["adj_boundary"])
        self.assertEqual(store["snapshot"]["presented"]["qa_flags"],[])
        self.assertEqual(store["snapshot_hash"],h); self.assertEqual(verify_snapshot(store),h)
        package["qa_flags"].pop()
        tampered=copy.deepcopy(store); tampered["snapshot"]["response"]["adj_dom_adequacy"]=3
        with self.assertRaises(PermissionError): verify_snapshot(tampered)
        with self.assertRaises(PermissionError): reveal(package["assignment_id"],package["package_id"],h,load_json("reveal_payloads.json"),tampered)
        with self.assertRaises(PermissionError): verify_snapshot({})
    def test_derived_best_skipped_indicator(self):
        # Derived at preservation, never reviewer-entered: why best-supported
        # was not asked, the outcome read off the ticks, and multiple-defensible.
        package=self.packages[0]; base=copy.deepcopy(self.submissions[0])
        self.assertEqual(derive_stage1(base,package),{"adj_dom_best_skipped":0,"adj_dom_best_outcome":1,"adj_dom_multiple_defensible":0})
        for best,outcome in (([1,2],3),([6],4)):
            r=copy.deepcopy(base); r["adj_dom_best"]=best; self.assertEqual(derive_stage1(r,package)["adj_dom_best_outcome"],outcome,best)
        three=self.packages[1]; r3=copy.deepcopy(self.submissions[1]); r3["adj_purp_best"]=[1,3]
        self.assertEqual(validate_submission(r3,three),[]); self.assertEqual(derive_stage1(r3,three)["adj_purp_best_outcome"],2,"a proper subset ties")
        r=copy.deepcopy(base); r["adj_dom_defensible"]=[1,2]; self.assertEqual(derive_stage1(r,package)["adj_dom_multiple_defensible"],1)
        r["adj_dom_defensible"]=[9]; self.assertEqual(derive_stage1(r,package)["adj_dom_multiple_defensible"],0)
        skipped=copy.deepcopy(base); skipped["adj_dom_evidence"]=3; del skipped["adj_dom_best"]
        self.assertEqual(validate_submission(skipped,package),[])
        self.assertEqual(derive_stage1(skipped,package),{"adj_dom_best_skipped":1,"adj_dom_best_outcome":9,"adj_dom_multiple_defensible":0})
        asked_anyway=copy.deepcopy(skipped); asked_anyway["adj_dom_best"]=[1]
        self.assertTrue(any("too little information" in x for x in validate_submission(asked_anyway,package)))
        self.assertEqual(derive_stage1(self.submissions[2],self.packages[2]),{})
        store={}; preserve(skipped,package,store)
        self.assertEqual(store["snapshot"]["derived"]["adj_dom_best_skipped"],1); self.assertNotIn("adj_dom_best_skipped",store["snapshot"]["response"])
        for key in ("adj_dom_best_skipped","adj_dom_best_outcome","adj_dom_multiple_defensible"):
            supplied=copy.deepcopy(base); supplied[key]=0
            self.assertTrue(any("derived indicators cannot be supplied" in x for x in validate_submission(supplied,package)),key)
    def test_corrections_and_reflections_require_complete_entries(self):
        package=self.packages[0]; store={}; h=preserve(copy.deepcopy(self.submissions[0]),package,store)
        preserved=store["snapshot"]["response"]["adj_stage1_note"]
        valid={"field":"adj_stage1_note","original_value":preserved,"corrected_value":preserved.replace(".", " (transcription corrected)."),"reason":"Transcription slip.","author":"SYN_ADJ_R1","date":"2026-09-21"}
        for key in valid:
            partial={k:v for k,v in valid.items() if k!=key}
            with self.assertRaises(ValueError,msg=key): record_correction(store,h,partial)
        with self.assertRaises(ValueError): record_correction(store,h,{})
        with self.assertRaises(ValueError): record_correction(store,h,{**valid,"unexpected":"x"})
        with self.assertRaises(ValueError): record_correction(store,h,{**valid,"original_value":"Not the preserved value."})
        with self.assertRaises(ValueError): record_correction(store,h,{**valid,"field":"adj_not_a_field"})
        with self.assertRaises(ValueError): record_correction(store,h,{**valid,"date":"21/09/2026"})
        with self.assertRaises(ValueError): record_correction(store,h,{**valid,"author":"  "})
        with self.assertRaises(PermissionError): record_correction(store,"0"*64,valid)
        self.assertNotIn("adj_correction",store)
        before=dict(store["snapshot"]); record_correction(store,h,valid)
        self.assertEqual(store["snapshot_hash"],h); self.assertEqual(verify_snapshot(store),h); self.assertEqual(store["snapshot"],before)
        self.assertEqual(len(store["adj_correction"]),1); self.assertEqual(store["adj_correction"][0]["snapshot_hash"],h)
        entry=dict(valid); record_correction(store,h,entry); entry["reason"]="Mutated after the fact."
        self.assertEqual(len(store["adj_correction"]),2); self.assertEqual(store["adj_correction"][1]["reason"],"Transcription slip.")
        reflection={"scope":"dom","reflection":"On reflection the comparative reading is weaker.","author":"SYN_ADJ_R1","date":"2026-09-21T10:00:00+00:00"}
        for key in reflection:
            partial={k:v for k,v in reflection.items() if k!=key}
            with self.assertRaises(ValueError,msg=key): record_reflection(store,h,partial)
        with self.assertRaises(ValueError): record_reflection(store,h,{"anything":1})
        with self.assertRaises(ValueError): record_reflection(store,h,{**reflection,"scope":"not_a_scope"})
        with self.assertRaises(PermissionError): record_reflection(store,"0"*64,reflection)
        record_reflection(store,h,reflection); record_reflection(store,h,{**reflection,"scope":"adj_stage1_note"})
        self.assertEqual(len(store["adj_reflection"]),2); self.assertEqual(store["snapshot_hash"],h); self.assertEqual(store["snapshot"],before)
        self.assertEqual(verify_snapshot(store),h)
    def test_noneoftheabove_annotations_are_quoted_and_valid(self):
        rows=field_rows(); annotated=[x for x in rows if "@NONEOFTHEABOVE" in x[17]]
        self.assertTrue(annotated)
        for row in annotated:
            self.assertEqual(row[3],"checkbox",row[0])
            value=row[17].split("@NONEOFTHEABOVE=",1)[1].split(" ")[0]
            self.assertRegex(value,r"^'\d+(,\d+)*'$",row[0])
            choices={entry.split(",",1)[0].strip() for entry in row[5].split(" | ")}
            for code in value.strip("'").split(","): self.assertIn(code,choices,row[0])
    def test_long_variable_names_match_verification_record(self):
        actual=[x[0] for x in field_rows() if len(x[0])>26]
        text=(ROOT/"verification.md").read_text(encoding="utf-8")
        block=text.split("## REDCap import-length check",1)[1].split("```text",1)[1].split("```",1)[0]
        recorded=[x.strip() for x in " ".join(block.split()).split(";") if x.strip()]
        self.assertEqual(recorded,actual)
        self.assertIn(f"{len(actual)} candidate variables exceed 26 characters",text)
    def test_dictionary_structure_choices_and_forms(self):
        rows=field_rows(); names=[x[0] for x in rows]; self.assertEqual(len(names),len(set(names))); self.assertEqual(HEADER.__len__(),18)
        form_order={"adj_admin":0,"adj_stage1":1,"adj_stage2":2}; by={x[0]:x for x in rows}
        for row in rows:
            self.assertNotEqual(row[3],"calc",row[0])
            if row[3]!="yesno" and row[5]:
                codes=[]
                for entry in row[5].split(" | "):
                    self.assertRegex(entry,r"^[^,]+, .+"); codes.append(entry.split(",",1)[0])
                if row[3] in ("checkbox","radio"): self.assertEqual(len(codes),len(set(codes)),row[0])
            for token in row[11].split("[")[1:]:
                ref=token.split("]")[0].split("(")[0]; self.assertIn(ref,by); self.assertLessEqual(form_order[by[ref][1]],form_order[row[1]])
        record={"adj_diff_check","adj_diff_error_note","adj_diff_dimensions","adj_diff_labels","adj_diff_tag_statuses","adj_case_title","adj_case_datasets",
                "adj_rule_conflict","adj_rule_conflict_scope","adj_rule_conflict_ref","adj_rule_conflict_note","adj_dom_conflict_labels","adj_purp_conflict_labels",
                "adj_boundary","adj_boundary_scope","adj_boundary_rule_ref","adj_boundary_note","adj_masking_failure","adj_masking_note","adj_other_concern","adj_other_concern_note",
                "adj_stage1_unresolved","adj_stage1_unresolved_note","adj_stage1_note","adj_stage1_affirmed","adj_source_record_id","adj_reviewer_role","adj_pkg_comparative"}
        for comp in COMPONENTS: record|={f"adj_{comp}_{x}" for x in ("comparative","slot_count","interpretation_map","candidate_map","evidence","best","adequacy","defensible","conflict_slots")}
        for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
            record|={f"adj_{comp}_{x}" for x in ("additional_label_state","additional_label_ids","additional_label_note")}
            for n in range(1,len(vocab)+1): record|={f"adj_{comp}_l{n:02d}_{x}" for x in ("applicable","membership","support","rule_conflict","rule_ref","rule_note")}
        for tag in ("covid","equity"): record|={f"adj_{tag}_{x}" for x in ("status_membership","status_support","rule_conflict","rule_ref","rule_note","supported_status","supported_status_note")}
        self.assertEqual(set(names)-{"adj_assignment_id","adj_stage1_package_id","adj_reveal_state","adj_stage2_closure","adj_no_issue_rationale"},record)
        retired=("comparative_outcome","best_interpretations","public_evidence","defensible_state","weaker","multiple_defensible","omission","shared_label","support_note","concern_scope","prior_exposure","case_status")
        for name in names: self.assertFalse(any(x in name for x in retired),name)
        self.assertTrue(all(x[1]!="adj_stage1" for x in rows if x[0] in {"adj_reveal_state","adj_stage2_closure","adj_no_issue_rationale"}))
        for name in ("adj_other_concern","adj_stage1_unresolved"): self.assertIn("@DEFAULT='0'",by[name][17])
    def test_generated_outputs_are_masked_and_reproducible(self):
        preview=(ROOT/"preview"/"index.html").read_text(encoding="utf-8").lower()
        for forbidden in ("source_id","gpt55","rationale","eligibility","reveal_payload","source_map"): self.assertNotIn(forbidden,preview)
        with (ROOT/"instruments"/"adjudication_stage1_candidate.csv").open(encoding="utf-8",newline="") as f:self.assertEqual(next(csv.reader(f)),HEADER)
    def test_generated_flags_gate_the_form_and_cut_what_is_asked(self):
        rows=field_rows(); by={x[0]:x for x in rows}
        flag=lambda ref: ref.endswith("_applicable") or ref.endswith("_comparative")
        refs=lambda b: [t.split("]")[0].split("(")[0] for t in b.split("[")[1:]]
        for name in ("adj_pkg_comparative",)+tuple(f"adj_{c}_comparative" for c in COMPONENTS): self.assertIn("@HIDDEN",by[name][17],name)
        self.assertIn("[adj_pkg_comparative] = '1'",by["adj_rule_conflict"][11])
        for comp in COMPONENTS:
            for name in ("evidence","best","adequacy","defensible"): self.assertIn(f"[adj_{comp}_comparative] = '1'",by[f"adj_{comp}_{name}"][11],name)
            self.assertIn(f"[adj_{comp}_evidence] <> '3'",by[f"adj_{comp}_best"][11],"best is skipped when there is too little information")
            for name in ("evidence","best","adequacy","defensible"): self.assertTrue(by[f"adj_{comp}_{name}"][6],f"{name} needs help text")
        for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
            for n in range(1,len(vocab)+1):
                self.assertIn("@HIDDEN",by[f"adj_{comp}_l{n:02d}_applicable"][17]); self.assertIn(f"[adj_{comp}_l{n:02d}_applicable] = '1'",by[f"adj_{comp}_l{n:02d}_support"][11])
            self.assertEqual(by[f"adj_{comp}_additional_label_state"][11],"[adj_pkg_comparative] = '0'")
        self.assertFalse(by["adj_boundary"][11],"boundary is asked for every record")
        answerable={"radio","checkbox","yesno","text","notes"}
        for case,package in zip(self.cases,self.packages):
            evidence=generated_evidence(package)
            self.assertEqual(evidence["adj_pkg_comparative"],int(len(package["candidates"])>1))
            for comp in COMPONENTS: self.assertEqual(evidence[f"adj_{comp}_comparative"],int(len(package["interpretations"][comp])>1))
            for comp,vocab in (("dom",DOMAINS),("purp",PURPOSES)):
                for n,label in enumerate(vocab,1):
                    shown=label in component_labels(package,comp)[1] and len(package["candidates"])==1
                    self.assertEqual(evidence[f"adj_{comp}_l{n:02d}_applicable"],int(shown))
            # Count what a reviewer is asked when the form opens, before any
            # answer: generated flags set, every reviewer field still blank.
            asked=[row[0] for row in rows if row[1]=="adj_stage1" and row[3] in answerable and row[0]!="adj_stage1_note"
                   and not any(a in row[17] for a in ("@HIDDEN","@READONLY","@DEFAULT")) and redcap_shows(row[11],evidence)]
            if len(package["candidates"])>1:
                # Differences, rule conflict, boundary, masking and affirmation,
                # plus evidence, best-supported, sufficient support and
                # defensible options for each component that differs.
                self.assertEqual(len(asked),5+4*len(comparative_components(package)),(case["record_id"],asked))
                self.assertFalse([x for x in asked if "_l0" in x or "_l1" in x or "additional_label" in x or "status_" in x],case["record_id"])
            else:
                labels=sum(len(component_labels(package,c)[1]) for c in ("dom","purp"))
                # Differences, boundary, masking and affirmation, then §9.2's
                # single-set checks: support and rule conflict per displayed
                # label, the additional-label question per component, and
                # support, conflict and alternative status per tag.
                self.assertEqual(len(asked),4+2*labels+2+3*2,(case["record_id"],asked))
                self.assertFalse([x for x in asked if x=="adj_rule_conflict" or x.endswith(("_evidence","_best","_defensible"))],case["record_id"])
    def test_frozen_public_entry_is_presented(self):
        by={x[0]:x for x in field_rows()}
        for name in ("adj_case_title","adj_case_datasets"):
            self.assertEqual(by[name][1],"adj_stage1"); self.assertIn("@READONLY",by[name][17])
        for package,case in zip(self.packages,self.cases):
            evidence=generated_evidence(package)
            self.assertEqual(evidence["adj_case_title"],case["title"]); self.assertEqual(evidence["adj_case_datasets"],case["datasets"])
            self.assertTrue(evidence["adj_case_datasets"].strip())
    def test_no_field_clashes_with_a_redcap_form_completion_name(self):
        rows=field_rows(); names={x[0] for x in rows}; forms={x[1] for x in rows}
        # REDCap generates [form_name]_complete itself and rejects a dictionary
        # that declares one. Rejected on real import as adj_stage1_complete.
        clashes=sorted(n for n in names if n in {f"{form}_complete" for form in forms})
        self.assertEqual(clashes,[])
        self.assertIn("adj_stage1_affirmed",names)
    def test_record_key_is_the_opaque_assignment_id(self):
        rows=field_rows(); self.assertEqual(rows[0][0],"adj_assignment_id")
        # REDCap takes the first field as the record identifier, which appears in
        # record lists, URLs, logs and exports; the source Record ID must not be it.
        self.assertNotEqual(rows[0][0],"adj_source_record_id")
        by={x[0]:x for x in rows}; self.assertEqual(by["adj_source_record_id"][17].strip(),"@HIDDEN")
        with (ROOT/"instruments"/"adjudication_stage1_candidate.csv").open(encoding="utf-8",newline="") as f:
            reader=csv.reader(f); next(reader); self.assertEqual(next(reader)[0],"adj_assignment_id")
    def test_synthetic_record_import_file_is_masked_and_complete(self):
        with (ROOT/"instruments"/"adjudication_record_import_synthetic.csv").open(encoding="utf-8",newline="") as f:
            rows=list(csv.DictReader(f)); columns=list(rows[0])
        self.assertEqual(columns[0],"adj_assignment_id"); self.assertEqual(len(rows),2*len(self.cases))
        names=set(x[0] for x in field_rows())
        self.assertTrue(set(columns)-{"redcap_data_access_group"}<=names)
        self.assertEqual(sorted(x["redcap_data_access_group"] for x in rows),["primary"]*3+["secondary"]*3)
        for row in rows:
            self.assertEqual(row["adj_reviewer_role"],"1" if row["redcap_data_access_group"]=="primary" else "2")
            single=row["adj_pkg_comparative"]=="0"
            for key,value in row.items():
                if key.endswith("_membership"):
                    # Written only where shown: a value in a hidden field makes
                    # REDCap offer to erase it, and Keep All then displays it.
                    shown=single if key.endswith("status_membership") else row[key.replace("_membership","_applicable")]=="1"
                    self.assertEqual(bool(str(value).strip()),shown,f"{row['adj_assignment_id']}:{key}")
                else: self.assertTrue(str(value).strip(),f"{row['adj_assignment_id']}:{key} is empty")
                for token in IMPORT_FORBIDDEN: self.assertNotIn(token,str(value).lower())
            # @DEFAULT does not apply to a form the import has written to.
            self.assertEqual((row["adj_other_concern"],row["adj_stage1_unresolved"]),("0","0"))
            self.assertNotIn("C_",row["adj_dom_interpretation_map"]); self.assertIn("C_",row["adj_dom_candidate_map"])
            self.assertTrue(row["adj_dom_interpretation_map"].startswith("Option A:")); self.assertNotIn("Slot",row["adj_dom_interpretation_map"])
            for letter in re.findall(r"Option ([A-Z])",row["adj_dom_interpretation_map"]): self.assertIn(letter,"ABCD")
        for case in self.cases:
            pair=[x for x in rows if x["adj_source_record_id"]==case["record_id"]]
            self.assertEqual(len({x["adj_stage1_package_id"] for x in pair}),2)
            self.assertEqual(len({x["adj_assignment_id"] for x in pair}),2)
        single=[x for x in rows if x["adj_source_record_id"]=="SYN_ADJ_003"]
        for row in single: self.assertIn("single displayed candidate set",row["adj_diff_dimensions"])
    def test_import_generation_refuses_qa_flags_and_slot_overflow(self):
        flagged={"record_id":"SYN_ADJ_QA_IMPORT","assignment_id":"SYN_ASSIGN_QA_IMPORT","classifications":[{"source_type":"fable","domains":[],"purposes":[PURPOSES[0]],"covid":"Applied","equity":"Applied"}]}
        with self.assertRaises(ValueError): import_rows([flagged])
        overflow={"record_id":"SYN_ADJ_OVERFLOW","assignment_id":"SYN_ASSIGN_OVERFLOW","classifications":[{"source_type":"fable" if n==0 else "scratch","domains":[DOMAINS[n]],"purposes":[PURPOSES[0]],"covid":"Applied","equity":"Applied"} for n in range(5)]}
        package=package_case(overflow); self.assertEqual(len(package["interpretations"]["dom"]),5)
        with self.assertRaises(ValueError): slot_map(package,"dom")
        with self.assertRaises(ValueError): import_rows([overflow])
    def test_slot_choices_hidden_by_count_with_backstops(self):
        by={x[0]:x for x in field_rows()}
        expected={1:{2,3,4},2:{3,4},3:{4},4:set()}
        for comp in COMPONENTS:
            self.assertIn("@HIDDEN",by[f"adj_{comp}_slot_count"][17])
            for field in (f"adj_{comp}_best",f"adj_{comp}_defensible",f"adj_{comp}_conflict_slots"):
                annotation=by[field][17]
                for count,hide in expected.items():
                    self.assertEqual(hidden_choices(annotation,{f"adj_{comp}_slot_count":str(count)}),hide,(field,count))
                # A missing or invalid count hides nothing: the backstops catch it.
                for count in ("","0","5","x"):
                    self.assertEqual(hidden_choices(annotation,{f"adj_{comp}_slot_count":count}),set(),(field,count))
                self.assertTrue({0,6,9}.isdisjoint(hidden_choices(annotation,{f"adj_{comp}_slot_count":"1"})),field)
        for package in self.packages:
            evidence=generated_evidence(package)
            for comp in COMPONENTS: self.assertEqual(evidence[f"adj_{comp}_slot_count"],len(package["interpretations"][comp]))
        # @HIDECHOICE never removes an answer already saved, so an impossible
        # slot must still be caught by the data-quality rules and the validator.
        rules={name:logic for name,logic,_ in data_quality_rules()}
        count=rules["Missing or invalid slot count: Research Domains"]
        for name,field in (("best-supported","adj_dom_best"),("defensible","adj_dom_defensible"),("conflicting","adj_dom_conflict_slots")):
            rule=rules[f"Impossible {name} option: Research Domains"]
            for slots,ticked,flagged in ((2,[1,2],False),(2,[3],True),(2,[4],True),(3,[3],False),(3,[4],True),(4,[4],False),("",[2],True),(2,[6],False),(2,[0],False),(2,[9],False)):
                self.assertEqual(redcap_shows(rule,{field:ticked,"adj_dom_slot_count":str(slots)}),flagged,(name,slots,ticked))
        for slots,flagged in (("2",False),("4",False),("",True),("1",True),("5",True)):
            self.assertEqual(redcap_shows(count,{"adj_dom_comparative":"1","adj_dom_slot_count":slots}),flagged,slots)
        self.assertFalse(redcap_shows(count,{"adj_dom_comparative":"0","adj_dom_slot_count":"1"}))
        names={x[0] for x in field_rows()}
        for _,logic,realtime in data_quality_rules():
            self.assertEqual(realtime,"y")
            for token in logic.split("[")[1:]: self.assertIn(token.split("]")[0].split("(")[0],names)
        package=self.packages[0]
        for field in ("adj_dom_best","adj_dom_defensible"):
            saved=copy.deepcopy(self.submissions[0]); saved[field]=[3]
            self.assertTrue(any("option that is not displayed" in x for x in validate_submission(saved,package)),field)
        with (ROOT/"instruments"/"adjudication_data_quality_rules.csv").open(encoding="utf-8",newline="") as f:
            self.assertEqual([r["rule_name"] for r in csv.DictReader(f)],[x[0] for x in data_quality_rules()])
if __name__=="__main__": unittest.main()
