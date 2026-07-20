#!/usr/bin/env python3
"""Deterministically build the public Phase 5 REDCap candidate package offline."""
from __future__ import annotations
import csv, html, json
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'preregistration/package/06_redcap'
FIXTURES=ROOT/'tests/fixtures'
VERSION='redcap-candidate-0.5'
HISTORICAL_VERSION='redcap-candidate-0.3'
HEADERS=['Variable / Field Name','Form Name','Section Header','Field Type','Field Label','Choices, Calculations, OR Slider Labels','Field Note','Text Validation Type OR Show Slider Number','Text Validation Min','Text Validation Max','Identifier?','Branching Logic (Show field only if...)','Required Field?','Custom Alignment','Question Number (surveys only)','Matrix Group Name','Matrix Ranking?','Field Annotation']
SAMPLE_SET_CHOICES='1, Baseline | 2, Hard case | 3, Owner review | 4, Pilot'
PURPOSE_ANNOTATION="@MAXCHECKED=2 @NONEOFTHEABOVE='8'"
SC_NOTE_BRANCH="[sc_sufficiency] = '2' or [sc_sufficiency] = '3' or [sc_taxonomy_fit] = '2' or [sc_taxonomy_fit] = '3' or [sc_confidence] = '3'"
SC_NOTE_HELP='Required for partial or insufficient evidence, low confidence, or a taxonomy concern.'
SC_TAXONOMY_FIT_CHOICES='1, Fit | 2, Partial Fit | 3, No Fit | 4, Cannot assess from register entry'
PO_TAXONOMY_FIT_CHOICES='1, Fit | 2, Partial Fit | 3, No Fit'
TAXONOMY_ISSUE_CHOICES='1, Missing or inadequately represented category | 2, Ambiguous or overlapping category boundaries | 5, Other taxonomy problem'

def tax():
 d=yaml.safe_load((ROOT/'taxonomy_data_dictionary.yaml').read_text(encoding='utf-8'))['categories']
 d=[x for x in d if x.get('include_in_prompt')]
 groups=([x for x in d if x['layer']=='Layer A -- domain'],[x for x in d if x['layer']=='Layer C -- purpose'],[x for x in d if x['layer']=='Cross-cutting tag'])
 assert tuple(map(len,groups))==(12,8,2); return groups

def choice(labels): return ' | '.join(f'{i}, {v}' for i,v in enumerate(labels,1))
def field(name,form,typ,label,section='',choices='',note='',validation='',branch='',required=False,annotation=''):
 r={h:'' for h in HEADERS}; r.update({'Variable / Field Name':name,'Form Name':form,'Section Header':section,'Field Type':typ,'Field Label':label,'Choices, Calculations, OR Slider Labels':choices,'Field Note':note,'Text Validation Type OR Show Slider Number':validation,'Branching Logic (Show field only if...)':branch,'Required Field?':'y' if required else '','Field Annotation':annotation}); return r
def write_csv(path,headers,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=headers,lineterminator='\n'); w.writeheader(); w.writerows(rows)

def build_dictionary():
 domains,purposes,tags=tax(); dl=[x['label'] for x in domains]; pl=[x['label'] for x in purposes]; tl=[x['label'] for x in tags]
 hidden='@HIDDEN-SURVEY @READONLY'; rows=[]
 admin=[
 ('assignment_id','Neutral opaque assignment identifier','text','', ''),('review_stream','Review stream','radio','1, Scratch coder | 2, Project owner',''),('reviewer_id','Administrative reviewer identifier','text','',''),('source_record_id','Stable source Record ID','text','',''),('official_project_id','Official Project ID','text','',''),('project_title','Frozen public-register project title','notes','',''),('datasets_used','Frozen public-register datasets-used entry','notes','',''),('sample_set','Sample set','radio',SAMPLE_SET_CHOICES,''),('hard_stratum','Hard-case stratum','radio','0, Not applicable | 1, Domain only | 2, Purpose only | 3, Both',''),('validation_included','Included in validation analysis','yesno','',''),('sample_status','Active or reserve status','radio','1, Active | 2, Reserve | 3, Review only',''),('display_order','Reviewer display order','text','','integer'),('assignment_batch','Assignment batch','text','',''),('source_pop_ver','Source-population version','text','',''),('production_ver','Production-output version','text','',''),('instrument_ver','Instrument version','text','',''),('cluster_id','Project-level clustering identifier','text','',''),('owner_resp_id','Owner respondent identifier','text','',''),('owner_project_id','Owner project identifier','text','',''),
 ('owner_recruit_route','Owner recruitment route','radio','0, Not applicable | 1, Sequence based | 2, Supplementary purposive | 3, Post-revision',''),
 ('owner_sequence_pos','Owner greedy-sequence position','text','','integer'),
 ('owner_invite_batch','Owner invitation batch or checkpoint','text','',''),
 ('owner_invite_date','Owner invitation date','text','','date_ymd'),
 ('owner_reminder_date','Owner reminder date','text','','date_ymd'),
 ('owner_contact_disp','Owner contact/recruitment disposition','radio','0, Not applicable | 1, Contactable | 2, Unreachable | 3, Failed delivery | 4, No response | 5, Response received',''),
 ('owner_supp_reason','Pre-contact reason for supplementary invitation','notes','',''),
 ('owner_response_status','Owner response status','radio','0, Not invited | 1, Invited | 2, Partial | 3, Complete | 4, Non-response | 5, Failed delivery','')]
 for i,x in enumerate(domains,1): admin.append((f'prop_d{i:02d}',f"Proposed domain flag: {x['label']}",'yesno','',''))
 for i,x in enumerate(purposes,1): admin.append((f'prop_p{i:02d}',f"Proposed purpose flag: {x['label']}",'yesno','',''))
 for i,x in enumerate(tags,1): admin.append((f'prop_t{i:02d}',f"Proposed tag flag: {x['label']}",'yesno','',''))
 for i,(n,l,t,c,v) in enumerate(admin): rows.append(field(n,'assignment_admin',t,l,'Hidden assignment administration' if i==0 else '',c,validation=v,required=n=='assignment_id',annotation=hidden))
 rows += [
 field('sc_intro','scratch_coder','descriptive','Classify using only the displayed title, datasets-used entry and approved training materials.','Scratch-coder review'),field('sc_assignment','scratch_coder','descriptive','Assignment: <strong>[assignment_id]</strong>'),field('sc_project_title','scratch_coder','descriptive','<strong>Project title</strong><br>[project_title]'),field('sc_datasets','scratch_coder','descriptive','<strong>Datasets used</strong><br>[datasets_used]'),
 field('sc_blind_decl','scratch_coder','radio','I confirm that I used only the permitted register evidence and training materials.',choices='1, Confirmed | 0, Cannot confirm',required=True),field('sc_exposure','scratch_coder','radio','Were you accidentally exposed to prohibited project or reviewer information?',choices='0, No | 1, Yes',required=True),field('sc_exposure_note','scratch_coder','notes','Describe the accidental exposure without copying restricted content.',branch="[sc_exposure] = '1'",required=True),
 field('sc_domains','scratch_coder','checkbox','Research Domain(s)','Classification',choice(dl),'Select every supported substantive domain, or Unclear alone.',required=True,annotation="@NONEOFTHEABOVE='12'"),field('sc_purposes','scratch_coder','checkbox','Analytical Purpose(s)',choices=choice(pl),note='Select one or at most two purposes, or Unclear alone.',required=True,annotation=PURPOSE_ANNOTATION),field('sc_covid','scratch_coder','radio','COVID-19 & Pandemic',choices='0, No | 1, Yes',required=True),field('sc_equity','scratch_coder','radio','Demographic disparities / equity tag',choices='0, No | 1, Yes',required=True),
 field('sc_sufficiency','scratch_coder','radio','Register-entry sufficiency','Evidence and confidence','1, Sufficient | 2, Partial | 3, Insufficient',required=True),field('sc_taxonomy_fit','scratch_coder','radio','Taxonomy fit',choices=SC_TAXONOMY_FIT_CHOICES,required=True),field('sc_tax_issue','scratch_coder','checkbox','Taxonomy issue type',choices=TAXONOMY_ISSUE_CHOICES,branch="[sc_taxonomy_fit] = '2' or [sc_taxonomy_fit] = '3'",required=True),field('sc_confidence','scratch_coder','radio','Classification confidence',choices='1, High | 2, Medium | 3, Low',required=True),field('sc_note','scratch_coder','notes','Explanatory note',note=SC_NOTE_HELP,branch=SC_NOTE_BRANCH,required=True)]
 rows += [field('po_intro','project_owner','descriptive','Review proposed labels separately for actual-project fit and visibility in the public register entry.','Project-owner review'),field('po_assignment','project_owner','descriptive','Assignment: <strong>[assignment_id]</strong>'),field('po_project_title','project_owner','descriptive','<strong>Project title</strong><br>[project_title]'),field('po_datasets','project_owner','descriptive','<strong>Datasets used</strong><br>[datasets_used]')]
 mapping=[]; triggers=[]
 for prefix,layer,items in [('d','domain',domains),('p','purpose',purposes),('t','tag',tags)]:
  for i,x in enumerate(items,1):
   stem=f'{prefix}{i:02d}'; flag=f'prop_{stem}'; fit=f'po_{stem}_fit'; vis=f'po_{stem}_vis'; branch=f"[{flag}] = '1'"
   rows += [field(f'po_{stem}_label','project_owner','descriptive',f"<strong>{html.escape(x['label'])}</strong><br>{html.escape(str(x['definition']))}",f'Proposed {layer} labels' if i==1 else '',branch=branch),field(fit,'project_owner','radio',f"Does {x['label']} describe the actual project?",choices='1, Fits | 2, Does not fit | 3, Unsure',branch=branch,required=True),field(vis,'project_owner','radio',f"Is the basis for {x['label']} visible in the public register entry?",choices='1, Clearly visible | 2, Partly visible | 3, Not visible | 4, Unsure',branch=branch,required=True)]
   triggers += [f"[{fit}] = '2'",f"[{fit}] = '3'",f"[{vis}] = '2'",f"[{vis}] = '3'",f"[{vis}] = '4'"]
   mapping.append({'variable':stem,'taxonomy_layer':layer,'canonical_label':x['label'],'choice_code':str(i),'proposed_label_flag':flag,'fit_field':fit,'evidence_visibility_field':vis,'missing_label_field':f'po_miss_{layer}s'})
 rows += [field('po_miss_domain','project_owner','radio','Is any Research Domain missing?','Missing labels and overall assessment','0, No | 1, Yes',required=True),field('po_miss_domains','project_owner','checkbox','Which Research Domain label(s) are missing?',choices=choice(dl[:-1]),branch="[po_miss_domain] = '1'",required=True),field('po_miss_purpose','project_owner','radio','Is any Analytical Purpose missing?',choices='0, No | 1, Yes',required=True),field('po_miss_purposes','project_owner','checkbox','Which Analytical Purpose label(s) are missing?',choices=choice(pl[:-1]),branch="[po_miss_purpose] = '1'",required=True),field('po_miss_tag','project_owner','radio','Is any cross-cutting tag missing?',choices='0, No | 1, Yes',required=True),field('po_miss_tags','project_owner','checkbox','Which cross-cutting tag(s) are missing?',choices=choice(tl),branch="[po_miss_tag] = '1'",required=True),field('po_sufficiency','project_owner','radio','Public register-entry sufficiency',choices='1, Sufficient | 2, Partial | 3, Insufficient',required=True),field('po_taxonomy_fit','project_owner','radio','Taxonomy fit',choices=PO_TAXONOMY_FIT_CHOICES,required=True),field('po_tax_issue','project_owner','checkbox','Taxonomy issue type',choices=TAXONOMY_ISSUE_CHOICES,branch="[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'",required=True)]
 note=' or '.join(triggers+["[po_miss_domain] = '1'","[po_miss_purpose] = '1'","[po_miss_tag] = '1'","[po_sufficiency] = '2'","[po_sufficiency] = '3'","[po_taxonomy_fit] = '2'","[po_taxonomy_fit] = '3'"])
 rows.append(field('po_note','project_owner','notes','Explanation',note='Required for disagreement, uncertainty, missing labels, limited public evidence, or taxonomy concern.',branch=note,required=True))
 return rows,{'domains':domains,'purposes':purposes,'tags':tags,'admin_fields':[x[0] for x in admin],'owner_mapping':mapping}

def build_specs(rows,meta):
 fh=['variable_name','conceptual_name','form_name','field_type','response_code','response_label','canonical_taxonomy_label','required_rule','branching_rule','visible_to_scratch_coder','visible_to_project_owner','exported_for_analysis','notes']; out=[]
 for r in rows:
  parts=r['Choices, Calculations, OR Slider Labels'].split(' | ') if r['Choices, Calculations, OR Slider Labels'] else ['']
  for part in parts:
   code,label=part.split(', ',1) if part else ('','')
   out.append({'variable_name':r['Variable / Field Name'],'conceptual_name':r['Field Label'],'form_name':r['Form Name'],'field_type':r['Field Type'],'response_code':code,'response_label':label,'canonical_taxonomy_label':label if r['Variable / Field Name'] in ('sc_domains','sc_purposes') else '','required_rule':'conditional' if r['Required Field?'] and r['Branching Logic (Show field only if...)'] else 'required' if r['Required Field?'] else 'optional/display','branching_rule':r['Branching Logic (Show field only if...)'],'visible_to_scratch_coder':'yes' if r['Form Name']=='scratch_coder' else 'no','visible_to_project_owner':'yes' if r['Form Name']=='project_owner' else 'no','exported_for_analysis':'no' if r['Field Type']=='descriptive' else 'yes','notes':r['Field Note'] or r['Field Annotation']})
 write_csv(PACKAGE/'redcap_field_response_specification.csv',fh,out)
 spec={
  'version':VERSION,
  'historical_versions':{
   HISTORICAL_VERSION:{
    'scratch_taxonomy_fit_codes':{1:'Fit',2:'Partial Fit',3:'No Fit'},
    'taxonomy_issue_codes':{1:'Missing category',2:'Ambiguous/overlapping categories',3:'Too broad',4:'Too narrow',5:'Other',6:'None'},
    'decode_only':True,
    'no_destructive_recode':True,
   }
  },
  'forms':['assignment_admin','scratch_coder','project_owner'],
  'scratch':{
   'domain_field':'sc_domains','domain_unclear_code':12,'domain_unclear_exclusive':True,
   'purpose_field':'sc_purposes','purpose_unclear_code':8,'purpose_min':1,'purpose_max':2,'purpose_unclear_exclusive':True,
   'taxonomy_fit_codes':{1:'Fit',2:'Partial Fit',3:'No Fit',4:'Cannot assess from register entry'},
   'taxonomy_issue_codes':{1:'Missing or inadequately represented category',2:'Ambiguous or overlapping category boundaries',5:'Other taxonomy problem'},
   'cannot_assess_requires_sufficiency':[2,3],
   'required_core':['sc_blind_decl','sc_exposure','sc_domains','sc_purposes','sc_covid','sc_equity','sc_sufficiency','sc_taxonomy_fit','sc_confidence'],
   'conditional_required':{
    'sc_exposure_note':'sc_exposure == 1',
    'sc_tax_issue':'sc_taxonomy_fit in [2,3]',
    'sc_note':'sc_sufficiency in [2,3] or sc_taxonomy_fit in [2,3] or sc_confidence == 3',
    'other_taxonomy_problem_note':'5 in sc_tax_issue',
   },
   'action_tags_for_live_confirmation':{'sc_domains':"@NONEOFTHEABOVE='12'",'sc_purposes':PURPOSE_ANNOTATION},
  },
  'owner':{
   'label_mapping':meta['owner_mapping'],
   'fit_codes':{1:'Fits',2:'Does not fit',3:'Unsure'},
   'taxonomy_fit_codes':{1:'Fit',2:'Partial Fit',3:'No Fit'},
   'taxonomy_issue_codes':{1:'Missing or inadequately represented category',2:'Ambiguous or overlapping category boundaries',5:'Other taxonomy problem'},
   'visibility_codes':{1:'Clearly visible',2:'Partly visible',3:'Not visible',4:'Unsure'},
   'missing_branches':{'po_miss_domains':'po_miss_domain == 1','po_miss_purposes':'po_miss_purpose == 1','po_miss_tags':'po_miss_tag == 1'},
   'conditional_note':'any proposed fit != 1 or visibility != 1; any missing-label report; sufficiency != 1; taxonomy_fit != 1; or Other taxonomy problem selected',
   'contradiction_rule':'Proposed-and-Fits plus missing for the same label is rejected.',
   'completion_rule':'Every proposed-label verdict and public-entry sufficiency are complete.',
  },
  'neutral_assignment_id':{'pattern':'^[A-Z0-9]{8}$','forbidden_tokens':['baseline','hard','reserve','active','coder','owner'],'must_not_derive_from_hidden_id':True},
  'completion':{'generated_fields':['assignment_admin_complete','scratch_coder_complete','project_owner_complete'],'invalid_if_trigger_unresolved':True},
 }
 spec['administration']={
  'sample_set_codes':{1:'Baseline',2:'Hard case',3:'Owner review',4:'Pilot'},
  'pilot_validation_included':0,
  'owner_recruitment_route_codes':{0:'Not applicable',1:'Sequence based',2:'Supplementary purposive',3:'Post-revision'},
  'owner_sequence_target_unique_records':50,
  'owner_sequence_minimum_viable_unique_records':25,
  'owner_supplementary_invitation_maximum':10,
  'owner_data_collection_close_day':42,
  'no_fixed_owner_reserve':True,
 }
 (PACKAGE/'redcap_branching_validation_specification.yaml').write_text(yaml.safe_dump(spec,sort_keys=False,allow_unicode=True),encoding='utf-8')
 write_csv(PACKAGE/'redcap_label_variable_mapping.csv',list(meta['owner_mapping'][0]),meta['owner_mapping'])

def build_templates(rows,meta):
 write_csv(PACKAGE/'redcap_assignment_import_template.csv',meta['admin_fields'],[])
 h=['variable','source_form','redcap_generated_or_user_defined','data_type','allowed_values','analysis_role','project_level_or_assignment_level','required_at_lock','restricted_public_status','notes']; out=[]
 for r in rows:
  if r['Field Type']=='descriptive': continue
  n=r['Variable / Field Name']; ch=r['Choices, Calculations, OR Slider Labels']
  if r['Field Type']=='checkbox':
   for part in ch.split(' | '):
    code,label=part.split(', ',1); out.append({'variable':f'{n}___{code}','source_form':r['Form Name'],'redcap_generated_or_user_defined':'REDCap checkbox export','data_type':'integer','allowed_values':'0,1','analysis_role':'classification/diagnostic','project_level_or_assignment_level':'assignment','required_at_lock':r['Required Field?'],'restricted_public_status':'restricted response data','notes':label})
  else: out.append({'variable':n,'source_form':r['Form Name'],'redcap_generated_or_user_defined':'user-defined','data_type':'string' if r['Field Type'] in ('text','notes') else 'integer','allowed_values':ch,'analysis_role':'identifier/provenance' if r['Form Name']=='assignment_admin' else 'classification/diagnostic','project_level_or_assignment_level':'project' if n in ('cluster_id','owner_project_id') else 'assignment','required_at_lock':r['Required Field?'],'restricted_public_status':'restricted response data','notes':'Hidden from reviewers' if r['Form Name']=='assignment_admin' else ''})
 for form in ('assignment_admin','scratch_coder','project_owner'): out.append({'variable':f'{form}_complete','source_form':form,'redcap_generated_or_user_defined':'REDCap-generated','data_type':'integer','allowed_values':'0, Incomplete | 1, Unverified | 2, Complete','analysis_role':'completion/lock','project_level_or_assignment_level':'assignment','required_at_lock':'y','restricted_public_status':'restricted response data','notes':'Standard REDCap form status; no redundant custom completion field.'})
 write_csv(PACKAGE/'redcap_expected_export_schema.csv',h,out)

def build_preview(rows):
 forms=[]
 for form in ('scratch_coder','project_owner'):
  fs=[]
  for r in rows:
   if r['Form Name']!=form: continue
   c=r['Choices, Calculations, OR Slider Labels']; b=r['Branching Logic (Show field only if...)']
   fs.append(f"<section><h3>{html.escape(r['Field Label'])}{' *' if r['Required Field?'] else ''}</h3>{'<p>Choices: '+html.escape(c)+'</p>' if c else ''}{'<p class=branch>Shown when: '+html.escape(b)+'</p>' if b else ''}</section>")
  forms.append(f'<h2>{form}</h2>'+''.join(fs))
 admin=''.join(f"<li>{html.escape(r['Variable / Field Name'])}: {html.escape(r['Field Label'])}{': '+html.escape(r['Choices, Calculations, OR Slider Labels']) if r['Choices, Calculations, OR Slider Labels'] else ''}</li>" for r in rows if r['Form Name']=='assignment_admin')
 doc=f"<!doctype html><html lang=en><head><meta charset=utf-8><title>REDCap candidate preview</title><style>body{{font-family:Arial;max-width:960px;margin:2rem auto}}section{{border-top:1px solid #ccc}}.warning{{background:#fff3cd;padding:1rem}}</style></head><body><h1>REDCap candidate instrument preview</h1><p class=warning>Candidate {VERSION}; synthetic structural preview only, not a pixel-perfect REDCap rendering. Confirm appearance, branching and action tags in live runtime QA before formal coding.</p>{''.join(forms)}<h2>Administrative appendix (hidden from reviewers)</h2><ul>{admin}</ul></body></html>"
 (PACKAGE/'redcap_candidate_instrument_preview.html').write_text(doc,encoding='utf-8')

def build_fixtures():
 adm={'assignment_id':'B6J4K8M2','review_stream':1,'sample_set':1,'validation_included':1,'instrument_ver':VERSION}
 sc={'assignment_id':'A7K3M9Q2','instrument_ver':VERSION,'sc_blind_decl':1,'sc_exposure':0,'sc_domains':[1],'sc_purposes':[1],'sc_covid':0,'sc_equity':0,'sc_sufficiency':1,'sc_taxonomy_fit':1,'sc_confidence':1}
 po={'assignment_id':'Q4N8Z2L7','instrument_ver':VERSION,'cluster_id':'SYNTH-PROJECT-A','owner_resp_id':'SYNTH-OWNER-A','prop_d01':1,'po_d01_fit':1,'po_d01_vis':1,'po_miss_domain':0,'po_miss_purpose':0,'po_miss_tag':0,'po_sufficiency':1,'po_taxonomy_fit':1}
 cases=[]
 def add(cid,stream,valid,base,**kw):
  d=dict(base); d.update(kw); cases.append({'case_id':cid,'stream':stream,'expected_valid':valid,'data':d})
 add('admin_01_baseline','admin',True,adm)
 add('admin_02_pilot_excluded','admin',True,adm,sample_set=4,validation_included=0,instrument_ver=HISTORICAL_VERSION)
 add('admin_03_unknown_sample_set','admin',False,adm,sample_set=9)
 add('admin_04_pilot_included','admin',False,adm,sample_set=4,validation_included=1,instrument_ver=HISTORICAL_VERSION)
 add('sc_01_ordinary','scratch',True,sc)
 add('sc_02_multi_domain','scratch',True,sc,sc_domains=[1,2])
 add('sc_03_two_purpose','scratch',True,sc,sc_purposes=[1,2])
 add('sc_04_unclear_domain','scratch',True,sc,sc_domains=[12])
 add('sc_05_unclear_conflict','scratch',False,sc,sc_domains=[1,12])
 add('sc_06_three_purpose','scratch',False,sc,sc_purposes=[1,2,3])
 add('sc_07_partial_note','scratch',True,sc,sc_sufficiency=2,sc_note='Public entry gives only partial evidence.')
 add('sc_08_insufficient_note','scratch',True,sc,sc_sufficiency=3,sc_note='The analytical operation is not visible.')
 add('sc_09_low_confidence','scratch',True,sc,sc_confidence=3,sc_note='A rule boundary remains uncertain.')
 add('sc_10_partial_missing_issue','scratch',True,sc,sc_taxonomy_fit=2,sc_tax_issue=[1],sc_note='An important category is inadequately represented.')
 add('sc_11_no_fit_boundary_issue','scratch',True,sc,sc_taxonomy_fit=3,sc_tax_issue=[2],sc_note='Category boundaries cannot express the understood project.')
 add('sc_12_partial_other_issue','scratch',True,sc,sc_taxonomy_fit=2,sc_tax_issue=[5],sc_note='A different taxonomy problem is present.')
 add('sc_13_cannot_assess_insufficient','scratch',True,sc,sc_sufficiency=3,sc_taxonomy_fit=4,sc_note='The register entry is too thin to assess taxonomy fit.')
 add('sc_14_cannot_assess_partial','scratch',True,sc,sc_sufficiency=2,sc_taxonomy_fit=4,sc_note='The register entry supports only a partial understanding.')
 add('sc_15_cannot_assess_sufficient','scratch',False,sc,sc_sufficiency=1,sc_taxonomy_fit=4)
 add('sc_16_cannot_assess_with_issue','scratch',False,sc,sc_sufficiency=3,sc_taxonomy_fit=4,sc_tax_issue=[1],sc_note='Incoherent issue selection.')
 add('sc_17_fit_with_issue','scratch',False,sc,sc_taxonomy_fit=1,sc_tax_issue=[1])
 add('sc_18_partial_without_issue','scratch',False,sc,sc_taxonomy_fit=2,sc_note='Issue type omitted.')
 add('sc_19_retired_issue_3','scratch',False,sc,sc_taxonomy_fit=2,sc_tax_issue=[3],sc_note='Retired code.')
 add('sc_20_retired_issue_4','scratch',False,sc,sc_taxonomy_fit=2,sc_tax_issue=[4],sc_note='Retired code.')
 add('sc_21_retired_issue_6','scratch',False,sc,sc_taxonomy_fit=2,sc_tax_issue=[6],sc_note='Retired code.')
 add('sc_22_other_without_note','scratch',False,sc,sc_taxonomy_fit=2,sc_tax_issue=[5])
 add('sc_23_exposure','scratch',True,sc,sc_exposure=1,sc_exposure_note='Unexpected non-permitted context was visible.')
 incomplete=dict(sc); incomplete.pop('sc_purposes')
 add('sc_24_incomplete_core','scratch',False,incomplete)
 add('sc_25_historical_issue_3','scratch',True,sc,instrument_ver=HISTORICAL_VERSION,sc_taxonomy_fit=2,sc_tax_issue=[3],sc_note='Historical response retained exactly.')
 add('sc_26_historical_issue_4','scratch',True,sc,instrument_ver=HISTORICAL_VERSION,sc_taxonomy_fit=2,sc_tax_issue=[4],sc_note='Historical response retained exactly.')
 add('sc_27_historical_issue_6','scratch',True,sc,instrument_ver=HISTORICAL_VERSION,sc_taxonomy_fit=2,sc_tax_issue=[6],sc_note='Historical response retained exactly.')
 add('po_28_all_fit','owner',True,po)
 add('po_29_not_fit','owner',True,po,po_d01_fit=2,po_note='The proposed domain does not fit.')
 add('po_30_unsure','owner',True,po,po_d01_fit=3,po_note='I am unsure.')
 add('po_31_basis_not_visible','owner',True,po,po_d01_vis=3,po_note='The basis is not public.')
 add('po_32_missing_domain','owner',True,po,po_miss_domain=1,po_miss_domains=[2],po_note='Education is missing.')
 add('po_33_missing_purpose','owner',True,po,po_miss_purpose=1,po_miss_purposes=[2],po_note='Outcome tracking is missing.')
 add('po_34_missing_tag','owner',True,po,po_miss_tag=1,po_miss_tags=[1],po_note='The equity tag is missing.')
 add('po_35_taxonomy_concern','owner',True,po,po_taxonomy_fit=2,po_tax_issue=[1],po_note='A category is inadequately represented.')
 add('po_36_no_fit_boundary','owner',True,po,po_taxonomy_fit=3,po_tax_issue=[2],po_note='The boundaries cannot express the project.')
 add('po_37_other_taxonomy_problem','owner',True,po,po_taxonomy_fit=2,po_tax_issue=[5],po_note='A different taxonomy problem is present.')
 add('po_38_fit_code_4','owner',False,po,po_taxonomy_fit=4)
 add('po_39_partial_without_issue','owner',False,po,po_taxonomy_fit=2,po_note='Issue omitted.')
 add('po_40_other_without_note','owner',False,po,po_taxonomy_fit=2,po_tax_issue=[5])
 add('po_41_owner_a','owner',True,po)
 add('po_41_owner_b','owner',True,dict(po,assignment_id='R5T9X3C8',owner_resp_id='SYNTH-OWNER-B'))
 add('po_42_contradiction','owner',False,po,po_miss_domain=1,po_miss_domains=[1],po_note='Contradictory synthetic case.')
 FIXTURES.mkdir(parents=True,exist_ok=True)
 (FIXTURES/'redcap_candidate_synthetic_submissions.yaml').write_text(yaml.safe_dump({'fixture_status':'synthetic_only','contains_real_record_ids':False,'cases':cases},sort_keys=False),encoding='utf-8')

def main():
 PACKAGE.mkdir(parents=True,exist_ok=True); rows,meta=build_dictionary(); write_csv(PACKAGE/'redcap_data_dictionary_candidate.csv',HEADERS,rows); build_specs(rows,meta); build_templates(rows,meta); build_preview(rows); build_fixtures(); print(json.dumps({'status':'built','dictionary_rows':len(rows)}))
if __name__=='__main__': main()
