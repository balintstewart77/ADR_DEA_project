#!/usr/bin/env python3
"""Offline structural, taxonomy, blinding, and synthetic-response validation."""
from __future__ import annotations
import argparse, csv, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Mapping
import yaml

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'preregistration/package/06_redcap'
DICTIONARY=PACKAGE/'redcap_data_dictionary_candidate.csv'
FIELD_SPEC=PACKAGE/'redcap_field_response_specification.csv'
BRANCH_SPEC=PACKAGE/'redcap_branching_validation_specification.yaml'
IMPORT_TEMPLATE=PACKAGE/'redcap_assignment_import_template.csv'
EXPORT_SCHEMA=PACKAGE/'redcap_expected_export_schema.csv'
PREVIEW=PACKAGE/'redcap_candidate_instrument_preview.html'
FIXTURES=ROOT/'tests/fixtures/redcap_candidate_synthetic_submissions.yaml'
HEADERS=['Variable / Field Name','Form Name','Section Header','Field Type','Field Label','Choices, Calculations, OR Slider Labels','Field Note','Text Validation Type OR Show Slider Number','Text Validation Min','Text Validation Max','Identifier?','Branching Logic (Show field only if...)','Required Field?','Custom Alignment','Question Number (surveys only)','Matrix Group Name','Matrix Ranking?','Field Annotation']
FORMS={'assignment_admin','scratch_coder','project_owner'}
TYPES={'text','notes','radio','dropdown','checkbox','yesno','truefalse','descriptive','calc','slider','file','signature'}
VERSION='redcap-candidate-0.3'
SAMPLE_SET_CHOICES={'1':'Baseline','2':'Hard case','3':'Owner review','4':'Pilot'}
SAMPLE_SET_TEXT='1, Baseline | 2, Hard case | 3, Owner review | 4, Pilot'
PURPOSE_ANNOTATION="@MAXCHECKED=2 @NONEOFTHEABOVE='8'"
SC_EXPOSURE_BRANCH="[sc_exposure] = '1'"
SC_NOTE_BRANCH="[sc_sufficiency] = '2' or [sc_sufficiency] = '3' or [sc_taxonomy_fit] = '2' or [sc_taxonomy_fit] = '3' or [sc_confidence] = '3'"
SC_NOTE_HELP='Required for partial or insufficient evidence, low confidence, or a taxonomy concern.'
NAME_RE=re.compile(r'^[a-z][a-z0-9_]*$'); REAL_ID_RE=re.compile(r'(?<!\d)20\d{2}/\d{3}(?!\d)')
BRANCH_RE=re.compile(r'\[([a-z][a-z0-9_]*)(?:\((\d+)\))?\]')

class CandidateError(ValueError): pass
class PreviewParser(HTMLParser):
 def __init__(self): super().__init__(); self.html=False; self.h1=False
 def handle_starttag(self,tag,attrs): self.html|=tag=='html'; self.h1|=tag=='h1'

def read_csv(path):
 with path.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f); rows=list(reader); return rows,list(reader.fieldnames or [])
def choices(text):
 out={}
 if not text: return out
 for part in text.split(' | '):
  if ', ' not in part: raise CandidateError(f'Malformed choice: {part}')
  code,label=part.split(', ',1)
  if code in out: raise CandidateError(f'Duplicate choice code {code}')
  out[code]=label
 return out
def taxonomy_labels():
 cats=yaml.safe_load((ROOT/'taxonomy_data_dictionary.yaml').read_text(encoding='utf-8'))['categories']; cats=[x for x in cats if x.get('include_in_prompt')]
 return {'domain':[x['label'] for x in cats if x['layer']=='Layer A -- domain'],'purpose':[x['label'] for x in cats if x['layer']=='Layer C -- purpose'],'tag':[x['label'] for x in cats if x['layer']=='Cross-cutting tag']}

def validate_dictionary(path=DICTIONARY):
 rows,header=read_csv(path); errors=[]
 if header!=HEADERS: errors.append(f'Standard dictionary headers differ: {header}')
 if not rows: errors.append('Dictionary is empty'); raise CandidateError('\n'.join(errors))
 names=[r.get('Variable / Field Name','') for r in rows]
 if names[0]!='assignment_id': errors.append('First dictionary field must be assignment_id')
 if len(names)!=len(set(names)): errors.append('Duplicate variable name')
 for n in names:
  if not NAME_RE.fullmatch(n): errors.append(f'Invalid REDCap variable name: {n}')
  if len(n)>26: errors.append(f'Overlength REDCap variable name: {n}')
 by={r.get('Variable / Field Name',''):r for r in rows}
 for r in rows:
  if r.get('Form Name') not in FORMS: errors.append(f"Invalid form name for {r.get('Variable / Field Name')}: {r.get('Form Name')}")
  if r.get('Field Type') not in TYPES: errors.append(f"Invalid field type: {r.get('Field Type')}")
  try: choices(r.get('Choices, Calculations, OR Slider Labels',''))
  except CandidateError as e: errors.append(f"{r.get('Variable / Field Name')}: {e}")
  for ref,code in BRANCH_RE.findall(r.get('Branching Logic (Show field only if...)','')):
   if ref not in by: errors.append(f"Unknown branching-logic field {ref}")
   elif code and code not in choices(by[ref].get('Choices, Calculations, OR Slider Labels','')): errors.append(f"Invalid checkbox-code reference {ref}({code})")
 labels=taxonomy_labels()
 for variable,layer in [('sc_domains','domain'),('sc_purposes','purpose')]:
  actual=list(choices(by.get(variable,{}).get('Choices, Calculations, OR Slider Labels','')).values())
  if actual!=labels[layer]: errors.append(f'Taxonomy label mismatch for {variable}: expected={labels[layer]}, actual={actual}')
 if by.get('sc_equity',{}).get('Field Label')!=labels['tag'][0] or by.get('sc_covid',{}).get('Field Label')!=labels['tag'][1]: errors.append('Scratch tag labels differ from the two canonical taxonomy tags')
 obsolete={'Gender, Race & Ethnicity','Inequality / Disparities Analysis','Single-Dataset','Within-Domain Linkage','Cross-Domain Linkage'}
 all_choice_labels={v for r in rows for v in choices(r.get('Choices, Calculations, OR Slider Labels','')).values()}
 if all_choice_labels & obsolete: errors.append(f'Obsolete taxonomy label present: {sorted(all_choice_labels & obsolete)}')
 admin=[r for r in rows if r.get('Form Name')=='assignment_admin']
 for r in admin:
  if '@HIDDEN-SURVEY' not in r.get('Field Annotation','') or '@READONLY' not in r.get('Field Annotation',''): errors.append(f"Administrative field not hidden/read-only: {r.get('Variable / Field Name')}")
 scratch_text=' '.join(r.get('Field Label','')+' '+r.get('Branching Logic (Show field only if...)','') for r in rows if r.get('Form Name')=='scratch_coder').lower()
 for forbidden in ('source_record_id','official_project_id','sample_set','hard_stratum','sample_status','draw_rank','model rationale','cross-model','owner response','reviewer_id'):
  if forbidden in scratch_text: errors.append(f'Scratch form leaks hidden field/content: {forbidden}')
 if '[assignment_id]' not in scratch_text or '[project_title]' not in scratch_text or '[datasets_used]' not in scratch_text: errors.append('Scratch form lacks permitted neutral/evidence piping')
 if by.get('sc_purposes',{}).get('Field Annotation')!=PURPOSE_ANNOTATION: errors.append('Scratch purpose action tags differ')
 if by.get('sc_domains',{}).get('Field Annotation')!="@NONEOFTHEABOVE='12'": errors.append('Scratch domain action tag differs')
 if choices(by.get('sample_set',{}).get('Choices, Calculations, OR Slider Labels',''))!=SAMPLE_SET_CHOICES: errors.append('Administrative sample_set choices differ')
 exposure_note=by.get('sc_exposure_note',{})
 if exposure_note.get('Branching Logic (Show field only if...)')!=SC_EXPOSURE_BRANCH or exposure_note.get('Required Field?')!='y': errors.append('Dedicated exposure description must remain required when sc_exposure = 1')
 sc_note=by.get('sc_note',{})
 if sc_note.get('Branching Logic (Show field only if...)')!=SC_NOTE_BRANCH: errors.append('Scratch generic note branching differs')
 if sc_note.get('Field Note')!=SC_NOTE_HELP: errors.append('Scratch generic note help text differs')
 if errors: raise CandidateError('\n'.join(errors))
 return rows,by

def expected_exports(rows):
 out=set()
 for r in rows:
  if r['Field Type']=='descriptive': continue
  n=r['Variable / Field Name']
  if r['Field Type']=='checkbox': out|={f'{n}___{c}' for c in choices(r['Choices, Calculations, OR Slider Labels'])}
  else: out.add(n)
 out|={'assignment_admin_complete','scratch_coder_complete','project_owner_complete'}; return out

def validate_supporting(rows,by,package=PACKAGE,fixture_path=FIXTURES):
 errors=[]
 fs,fh=read_csv(package/'redcap_field_response_specification.csv')
 keys=[(r.get('variable_name'),r.get('response_code')) for r in fs]
 if len(keys)!=len(set(keys)): errors.append('Duplicate conceptual/response mapping')
 sample_set_mapping={r.get('response_code'):r.get('response_label') for r in fs if r.get('variable_name')=='sample_set'}
 if sample_set_mapping!=SAMPLE_SET_CHOICES: errors.append('Field specification sample_set mapping differs')
 spec=yaml.safe_load((package/'redcap_branching_validation_specification.yaml').read_text(encoding='utf-8'))
 if spec.get('version')!=VERSION: errors.append('Branch specification candidate version differs')
 if spec.get('forms')!=['assignment_admin','scratch_coder','project_owner']: errors.append('Branch specification form order differs')
 admin_spec=spec.get('administration',{})
 if admin_spec.get('sample_set_codes')!={1:'Baseline',2:'Hard case',3:'Owner review',4:'Pilot'}: errors.append('Branch specification sample_set codes differ')
 if admin_spec.get('pilot_validation_included')!=0: errors.append('Branch specification pilot exclusion rule differs')
 scratch_spec=spec.get('scratch',{})
 if scratch_spec.get('conditional_required',{}).get('sc_exposure_note')!='sc_exposure == 1': errors.append('Branch specification exposure-note rule differs')
 if scratch_spec.get('conditional_required',{}).get('sc_note')!='sc_sufficiency in [2,3] or sc_taxonomy_fit in [2,3] or sc_confidence == 3': errors.append('Branch specification generic-note rule differs')
 if scratch_spec.get('action_tags_for_live_confirmation',{}).get('sc_purposes')!=PURPOSE_ANNOTATION: errors.append('Branch specification purpose action tags differ')
 mapping=spec.get('owner',{}).get('label_mapping',[]); labels=taxonomy_labels()
 for layer in ('domain','purpose','tag'):
  actual=[x.get('canonical_label') for x in mapping if x.get('taxonomy_layer')==layer]
  if actual!=labels[layer]: errors.append(f'Owner taxonomy mapping mismatch: {layer}')
 imp,ih=read_csv(package/'redcap_assignment_import_template.csv'); admin=[r['Variable / Field Name'] for r in rows if r['Form Name']=='assignment_admin']
 if ih!=admin: errors.append('Import-template/dictionary mismatch')
 if imp: errors.append('Assignment import template contains rows')
 exp,eh=read_csv(package/'redcap_expected_export_schema.csv'); actual={r.get('variable') for r in exp}; missing=expected_exports(rows)-actual
 if missing: errors.append(f'Expected-export-schema omission: {sorted(missing)}')
 sample_export=next((r for r in exp if r.get('variable')=='sample_set'),{})
 if sample_export.get('allowed_values')!=SAMPLE_SET_TEXT: errors.append('Expected-export-schema sample_set choices differ')
 preview=(package/'redcap_candidate_instrument_preview.html').read_text(encoding='utf-8'); parser=PreviewParser(); parser.feed(preview)
 if not (parser.html and parser.h1): errors.append('Static preview is not parseable HTML')
 if html.escape(SC_NOTE_BRANCH) not in preview: errors.append('Static preview lacks corrected generic-note branch')
 fixture=fixture_path.read_text(encoding='utf-8')
 if REAL_ID_RE.search(fixture): errors.append('Real Record ID in synthetic fixture')
 if re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',fixture): errors.append('Email address in synthetic fixture')
 for path in package.iterdir():
  if path.is_file() and path.suffix.lower() in {'.csv','.yaml','.md','.html','.json'}:
   text=path.read_text(encoding='utf-8-sig')
   if re.search(r'(?i)(?:api[_ -]?token|password)\s*[:=]\s*[A-Za-z0-9_-]{12,}',text): errors.append(f'Credential-like value in {path.name}')
   if re.search(r'https?://[^\s<]+/(?:surveys|redcap_v\d+)',text,re.I): errors.append(f'Live survey/project link in {path.name}')
 if errors: raise CandidateError('\n'.join(errors))
 return spec

def neutral(value):
 return isinstance(value,str) and re.fullmatch(r'[A-Z0-9]{8}',value) is not None and not any(x in value.lower() for x in ('baseline','hard','reserve','active','coder','owner'))
def required(data,names,errors):
 for n in names:
  if n not in data or data[n] in ('',None,[]): errors.append(f'missing required {n}')
def validate_admin(data):
 e=[]
 if not neutral(data.get('assignment_id')): e.append('assignment_id is not neutral opaque')
 required(data,['review_stream','sample_set','validation_included'],e)
 if data.get('review_stream') not in (1,2): e.append('invalid review_stream code')
 if data.get('sample_set') not in (1,2,3,4): e.append('invalid sample_set code')
 if data.get('validation_included') not in (0,1): e.append('invalid validation_included code')
 if data.get('sample_set')==4 and data.get('validation_included')!=0: e.append('pilot assignments must be excluded from validation')
 return e
def validate_scratch(data):
 e=[]
 if not neutral(data.get('assignment_id')): e.append('assignment_id is not neutral opaque')
 required(data,['sc_blind_decl','sc_exposure','sc_domains','sc_purposes','sc_covid','sc_equity','sc_sufficiency','sc_taxonomy_fit','sc_confidence'],e)
 if data.get('sc_blind_decl')!=1: e.append('blinding declaration not confirmed')
 domains=data.get('sc_domains',[]); purposes=data.get('sc_purposes',[])
 if any(x not in range(1,13) for x in domains): e.append('invalid domain response code')
 if 12 in domains and len(domains)>1: e.append('Unclear domain plus substantive domain')
 if not 1<=len(purposes)<=2: e.append('purposes must contain one or two responses')
 if any(x not in range(1,9) for x in purposes): e.append('invalid purpose response code')
 if 8 in purposes and len(purposes)>1: e.append('Unclear purpose plus substantive purpose')
 if data.get('sc_exposure')==1 and not data.get('sc_exposure_note'): e.append('accidental exposure requires explanation')
 if data.get('sc_taxonomy_fit') in (2,3):
  if not data.get('sc_tax_issue') or 6 in data.get('sc_tax_issue',[]): e.append('taxonomy issue requires issue type')
 triggers=data.get('sc_sufficiency') in (2,3) or data.get('sc_taxonomy_fit') in (2,3) or data.get('sc_confidence')==3
 if triggers and not data.get('sc_note'): e.append('conditional explanatory note required')
 return e
def validate_owner(data,mapping):
 e=[]
 if not neutral(data.get('assignment_id')): e.append('assignment_id is not neutral opaque')
 required(data,['cluster_id','owner_resp_id','po_miss_domain','po_miss_purpose','po_miss_tag','po_sufficiency','po_taxonomy_fit'],e)
 note=False
 for m in mapping:
  if data.get(m['proposed_label_flag'])==1:
   fit=data.get(m['fit_field']); vis=data.get(m['evidence_visibility_field'])
   if fit not in (1,2,3): e.append(f"owner proposed-label response missing: {m['fit_field']}")
   if vis not in (1,2,3,4): e.append(f"owner visibility response missing: {m['evidence_visibility_field']}")
   note |= fit in (2,3) or vis in (2,3,4)
   miss=data.get(m['missing_label_field'],[])
   if fit==1 and int(m['choice_code']) in miss: e.append(f"contradictory proposed/missing label: {m['canonical_label']}")
 for flag,target in [('po_miss_domain','po_miss_domains'),('po_miss_purpose','po_miss_purposes'),('po_miss_tag','po_miss_tags')]:
  if data.get(flag)==1:
   note=True
   if not data.get(target): e.append(f'owner missing-label branch incomplete: {target}')
 if data.get('po_taxonomy_fit') in (2,3):
  note=True
  if not data.get('po_tax_issue') or 6 in data.get('po_tax_issue',[]): e.append('owner taxonomy issue incomplete')
 note |= data.get('po_sufficiency') in (2,3)
 if note and not data.get('po_note'): e.append('owner disagreement/uncertainty explanation required')
 return e
def validate_submissions(path=FIXTURES,spec_path=BRANCH_SPEC):
 payload=yaml.safe_load(path.read_text(encoding='utf-8')); spec=yaml.safe_load(spec_path.read_text(encoding='utf-8')); errors=[]; owner_pair=[]
 for case in payload.get('cases',[]):
  cid=case.get('case_id'); data=case.get('data',{}); aid=data.get('assignment_id')
  stream=case.get('stream')
  if stream=='admin': actual=validate_admin(data)
  elif stream=='scratch': actual=validate_scratch(data)
  elif stream=='owner': actual=validate_owner(data,spec['owner']['label_mapping'])
  else: actual=[f'unknown synthetic stream: {stream}']
  expected=case.get('expected_valid')
  if expected and actual: errors.append(f'{cid}: expected valid but failed: {actual}')
  if not expected and not actual: errors.append(f'{cid}: expected invalid but passed')
  if str(cid).startswith('po_21_owner_'): owner_pair.append((data.get('cluster_id'),aid))
 raw=path.read_text(encoding='utf-8')
 if REAL_ID_RE.search(raw): errors.append('real Record ID in synthetic fixture')
 if len(owner_pair)!=2 or len({x[0] for x in owner_pair})!=1 or len({x[1] for x in owner_pair})!=2: errors.append('multiple owner rows do not remain separate assignments within a shared project')
 if errors: raise CandidateError('\n'.join(errors))
 return {'cases':len(payload.get('cases',[])),'valid_cases':sum(bool(x.get('expected_valid')) for x in payload.get('cases',[])),'invalid_cases':sum(not bool(x.get('expected_valid')) for x in payload.get('cases',[]))}

def check(package=PACKAGE,fixture_path=FIXTURES):
 rows,by=validate_dictionary(package/'redcap_data_dictionary_candidate.csv'); validate_supporting(rows,by,package,fixture_path); return {'dictionary_rows':len(rows),'forms':sorted(FORMS)}
def parse_args(argv=None):
 p=argparse.ArgumentParser(description=__doc__); mode=p.add_mutually_exclusive_group(required=True); mode.add_argument('--check',action='store_true'); mode.add_argument('--validate-submissions',type=Path); return p.parse_args(argv)
def main(argv=None):
 args=parse_args(argv)
 try:
  result=check()
  if args.validate_submissions: result.update(validate_submissions(args.validate_submissions))
 except (CandidateError,OSError,csv.Error,yaml.YAMLError) as exc:
  print(f'FAILED: {exc}',file=sys.stderr); return 1
 print(json.dumps({'status':'passed',**result},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
