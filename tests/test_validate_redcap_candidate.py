from __future__ import annotations
import csv, hashlib, json, shutil, tempfile, unittest
from pathlib import Path
import yaml
from scripts import validate_redcap_candidate as v

class CandidateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.package=self.root/'06_redcap'; shutil.copytree(v.PACKAGE,self.package); self.fixture=self.root/'fixtures.yaml'; shutil.copy2(v.FIXTURES,self.fixture)
 def tearDown(self): self.tmp.cleanup()
 def rows(self):
  with (self.package/'redcap_data_dictionary_candidate.csv').open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))
 def write_rows(self,rows,headers=v.HEADERS):
  clean=[{key:value for key,value in item.items() if key in headers} for item in rows]
  with (self.package/'redcap_data_dictionary_candidate.csv').open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=headers,lineterminator='\n'); w.writeheader(); w.writerows(clean)
 def check(self):
  rows,by=v.validate_dictionary(self.package/'redcap_data_dictionary_candidate.csv'); return v.validate_supporting(rows,by,self.package,self.fixture)
 def test_01_valid_candidate_passes(self): self.check()
 def test_02_duplicate_variable_fails(self):
  r=self.rows(); r[1]['Variable / Field Name']=r[0]['Variable / Field Name']; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'Duplicate variable'): self.check()
 def test_03_invalid_variable_name_fails(self):
  r=self.rows(); r[1]['Variable / Field Name']='Bad-Name'; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'Invalid REDCap'): self.check()
 def test_04_overlength_name_fails(self):
  r=self.rows(); r[1]['Variable / Field Name']='a'+'x'*26; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'Overlength'): self.check()
 def test_05_assignment_id_not_first_fails(self):
  r=self.rows(); r[0],r[1]=r[1],r[0]; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'First dictionary'): self.check()
 def test_06_missing_standard_column_fails(self):
  h=v.HEADERS[:-1]; self.write_rows(self.rows(),h)
  with self.assertRaisesRegex(v.CandidateError,'headers differ'): self.check()
 def test_07_unknown_branch_field_fails(self):
  r=self.rows(); r[-1]['Branching Logic (Show field only if...)']="[missing_field] = '1'"; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'Unknown branching'): self.check()
 def test_08_bad_checkbox_reference_fails(self):
  r=self.rows(); r[-1]['Branching Logic (Show field only if...)']="[sc_domains(99)] = '1'"; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'Invalid checkbox-code'): self.check()
 def test_09_duplicate_choice_code_fails(self):
  r=self.rows(); x=next(x for x in r if x['Variable / Field Name']=='sc_domains'); x['Choices, Calculations, OR Slider Labels']+=' | 1, Duplicate'; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'Duplicate choice'): self.check()
 def change_domain(self,fn):
  r=self.rows(); x=next(x for x in r if x['Variable / Field Name']=='sc_domains'); parts=x['Choices, Calculations, OR Slider Labels'].split(' | '); x['Choices, Calculations, OR Slider Labels']=' | '.join(fn(parts)); self.write_rows(r)
 def test_10_taxonomy_label_missing_fails(self):
  self.change_domain(lambda p:p[:-1])
  with self.assertRaisesRegex(v.CandidateError,'Taxonomy label mismatch'): self.check()
 def test_11_obsolete_label_fails(self):
  self.change_domain(lambda p:p+['13, Gender, Race & Ethnicity'])
  with self.assertRaisesRegex(v.CandidateError,'Obsolete taxonomy'): self.check()
 def test_12_unknown_taxonomy_label_fails(self):
  self.change_domain(lambda p:p+['13, Fictional Domain'])
  with self.assertRaisesRegex(v.CandidateError,'Taxonomy label mismatch'): self.check()
 def sc(self): return {'assignment_id':'A7K3M9Q2','record_kind':3,'instrument_ver':v.VERSION,'sc_exposure':0,'sc_domains':[1],'sc_purposes':[1],'sc_covid':0,'sc_equity':0,'sc_sufficiency':1,'sc_taxonomy_fit':1,'sc_confidence':1}
 def admin(self): return {'assignment_id':'B6J4K8M2','record_kind':1,'instrument_ver':v.VERSION,'review_stream':1,'sample_set':1,'validation_included':1}
 def po(self): return {'assignment_id':'Q4N8Z2L7','instrument_ver':v.VERSION,'cluster_id':'SYNTH-P','owner_resp_id':'SYNTH-O','prop_d01':1,'po_d01_fit':1,'po_d01_vis':1,'po_miss_domain':0,'po_miss_purpose':0,'po_miss_tag':0,'po_sufficiency':1,'po_taxonomy_fit':1}
 def mapping(self): return yaml.safe_load(v.BRANCH_SPEC.read_text(encoding='utf-8'))['owner']['label_mapping']
 def test_13_unclear_plus_domain_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_domains=[1,12])))
 def test_14_three_purposes_fail(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_purposes=[1,2,3])))
 def test_15_zero_purpose_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_purposes=[])))
 def test_16_partial_without_note_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_sufficiency=2)))
 def test_17_low_confidence_without_note_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_confidence=3)))
 def test_18_taxonomy_issue_without_type_note_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_taxonomy_fit=2)))
 def test_19_exposure_without_explanation_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),sc_exposure=1)))
 def test_19a_exposure_with_dedicated_description_needs_no_generic_note(self): self.assertFalse(v.validate_scratch(dict(self.sc(),sc_exposure=1,sc_exposure_note='Synthetic accidental exposure.')))
 def test_20_owner_proposed_response_missing_fails(self):
  d=self.po(); d.pop('po_d01_fit'); self.assertTrue(v.validate_owner(d,self.mapping()))
 def test_21_owner_disagreement_without_note_fails(self): self.assertTrue(v.validate_owner(dict(self.po(),po_d01_fit=2),self.mapping()))
 def test_22_owner_missing_branch_incomplete_fails(self): self.assertTrue(v.validate_owner(dict(self.po(),po_miss_domain=1),self.mapping()))
 def test_23_owner_contradiction_fails(self): self.assertTrue(v.validate_owner(dict(self.po(),po_miss_domain=1,po_miss_domains=[1],po_note='x'),self.mapping()))
 def test_24_neutral_assignment_id_passes(self): self.assertFalse(v.validate_scratch(self.sc()))
 def test_25_encoded_assignment_id_fails(self): self.assertTrue(v.validate_scratch(dict(self.sc(),assignment_id='HARD0001')))
 def test_26_visible_hidden_admin_fails(self):
  r=self.rows(); next(x for x in r if x['Variable / Field Name']=='source_record_id')['Field Annotation']=''; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'not hidden'): self.check()
 def test_27_visible_model_output_fails(self):
  r=self.rows(); next(x for x in r if x['Variable / Field Name']=='sc_intro')['Field Label']+=' model rationale'; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'leaks hidden'): self.check()
 def test_28_real_record_id_in_fixture_fails(self):
  self.fixture.write_text(self.fixture.read_text(encoding='utf-8')+'\n# 2025/999\n',encoding='utf-8'); rows,by=v.validate_dictionary(self.package/'redcap_data_dictionary_candidate.csv')
  with self.assertRaisesRegex(v.CandidateError,'Real Record ID'): v.validate_supporting(rows,by,self.package,self.fixture)
 def test_29_import_template_mismatch_fails(self):
  p=self.package/'redcap_assignment_import_template.csv'; h=p.read_text(encoding='utf-8').strip().split(','); p.write_text(','.join(h[:-1])+'\n',encoding='utf-8')
  with self.assertRaisesRegex(v.CandidateError,'Import-template'): self.check()
 def test_30_export_schema_omission_fails(self):
  p=self.package/'redcap_expected_export_schema.csv'
  with p.open(encoding='utf-8',newline='') as f: reader=csv.DictReader(f); rows=list(reader); h=reader.fieldnames
  rows=[x for x in rows if x['variable']!='scratch_coder_complete']
  with p.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=h,lineterminator='\n'); w.writeheader(); w.writerows(rows)
  with self.assertRaisesRegex(v.CandidateError,'Expected-export-schema omission'): self.check()
 def test_31_multiple_owners_share_project_but_not_assignment(self): self.assertEqual(v.validate_submissions(self.fixture)['cases'],50)
 def test_32_check_writes_no_files(self):
  before={p.relative_to(v.ROOT):p.stat().st_mtime_ns for p in v.PACKAGE.iterdir() if p.is_file()}; self.assertEqual(v.main(['--check']),0); after={p.relative_to(v.ROOT):p.stat().st_mtime_ns for p in v.PACKAGE.iterdir() if p.is_file()}; self.assertEqual(before,after)
 def test_33_legacy_maxchoice_action_tag_fails(self):
  r=self.rows(); next(x for x in r if x['Variable / Field Name']=='sc_purposes')['Field Annotation']="@MAXCHOICE=2 @NONEOFTHEABOVE='8'"; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'purpose action tags differ'): self.check()
 def test_34_generic_note_exposure_branch_fails(self):
  r=self.rows(); note=next(x for x in r if x['Variable / Field Name']=='sc_note'); note['Branching Logic (Show field only if...)']="[sc_exposure] = '1' or "+note['Branching Logic (Show field only if...)']; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'generic note branching differs'): self.check()
 def test_35_sample_set_mapping_is_exact_and_existing_codes_unchanged(self):
  row=next(x for x in self.rows() if x['Variable / Field Name']=='sample_set')
  self.assertEqual(v.choices(row['Choices, Calculations, OR Slider Labels']),{'1':'Baseline','2':'Hard case','3':'Owner review','4':'Pilot'})
  for code in (1,2,3): self.assertFalse(v.validate_admin(dict(self.admin(),sample_set=code)))
 def test_36_candidate_without_pilot_sample_set_fails(self):
  r=self.rows(); next(x for x in r if x['Variable / Field Name']=='sample_set')['Choices, Calculations, OR Slider Labels']='1, Baseline | 2, Hard case | 3, Owner review'; self.write_rows(r)
  with self.assertRaisesRegex(v.CandidateError,'sample_set choices differ'): self.check()
 def test_37_pilot_sample_set_is_valid_when_excluded(self): self.assertFalse(v.validate_admin(dict(self.admin(),sample_set=4,validation_included=0)))
 def test_38_unknown_sample_set_is_invalid(self): self.assertTrue(v.validate_admin(dict(self.admin(),sample_set=9)))
 def test_39_pilot_cannot_be_validation_included(self): self.assertTrue(v.validate_admin(dict(self.admin(),sample_set=4,validation_included=1)))
 def test_40_scratch_coder_form_signature_changes_for_diagnostics_only(self):
   rows=[r for r in self.rows() if r['Form Name']=='scratch_coder']; payload=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
   self.assertEqual(hashlib.sha256(payload).hexdigest(),'7b67ac98c4a1a661a8b5d8ca670c17e4b0af472b77900ab062eb838f1f8298c3')
   self.assertNotEqual(hashlib.sha256(payload).hexdigest(),'7c17aba55f089f78603ae7cf6b48253c50e518dadc05445632680b1e86ac816c')
   self.assertNotEqual(hashlib.sha256(payload).hexdigest(),'8f59881f91573106a2327fc6d056fd04b9bdb34816846daf0898e3b26196c00f')
 def test_41_candidate_version_is_0_7(self): self.assertEqual(yaml.safe_load((self.package/'redcap_branching_validation_specification.yaml').read_text(encoding='utf-8'))['version'],'redcap-candidate-0.7')
 def test_42_runtime_corrections_remain_intact(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  self.assertEqual(by['sc_purposes']['Field Annotation'],v.PURPOSE_ANNOTATION)
  self.assertEqual(by['sc_note']['Branching Logic (Show field only if...)'],v.SC_NOTE_BRANCH)
  self.assertNotIn('sc_exposure',v.SC_NOTE_CONDITION)
 def test_43_substantive_classification_core_signature_is_unchanged(self):
  rows=[r for r in self.rows() if r['Variable / Field Name'] in ('sc_domains','sc_purposes','sc_covid','sc_equity')]
  for row in rows: row['Branching Logic (Show field only if...)']=''
  payload=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
  self.assertEqual(hashlib.sha256(payload).hexdigest(),'73406c72fc8c86bdb362dcf1c02a42b3b420484a7edc2415583899cb5581230f')
 def test_44_exact_fit_issue_choices_and_branches(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  scratch_fit=by['sc_taxonomy_fit']
  self.assertEqual(v.choices(scratch_fit['Choices, Calculations, OR Slider Labels']),v.SC_TAXONOMY_FIT_CHOICES)
  self.assertEqual(scratch_fit['Field Note'],v.SC_TAXONOMY_FIT_HELP)
  self.assertEqual(scratch_fit['Field Type'],'radio')
  self.assertEqual(scratch_fit['Required Field?'],'y')
  self.assertEqual(scratch_fit['Branching Logic (Show field only if...)'],v.PROJECT_RECORD_GUARD)
  self.assertFalse(scratch_fit['Field Annotation'])
  self.assertEqual(v.choices(by['po_taxonomy_fit']['Choices, Calculations, OR Slider Labels']),v.PO_TAXONOMY_FIT_CHOICES)
  for field in ('sc_tax_issue','po_tax_issue'):
   self.assertEqual(v.choices(by[field]['Choices, Calculations, OR Slider Labels']),v.CURRENT_TAXONOMY_ISSUE_CHOICES)
   self.assertFalse(by[field]['Field Annotation'])
  self.assertEqual(by['sc_tax_issue']['Branching Logic (Show field only if...)'],v.SC_TAX_ISSUE_BRANCH)
  self.assertEqual(by['po_tax_issue']['Branching Logic (Show field only if...)'],"[po_taxonomy_fit] = '2' or [po_taxonomy_fit] = '3'")
 def test_45_cannot_assess_coherence(self):
  self.assertFalse(v.validate_scratch(dict(self.sc(),sc_sufficiency=3,sc_taxonomy_fit=4,sc_note='Thin public evidence.')))
  self.assertFalse(v.validate_scratch(dict(self.sc(),sc_sufficiency=2,sc_taxonomy_fit=4,sc_note='Partial public evidence.')))
  self.assertTrue(v.validate_scratch(dict(self.sc(),sc_sufficiency=1,sc_taxonomy_fit=4)))
  self.assertTrue(v.validate_scratch(dict(self.sc(),sc_sufficiency=3,sc_taxonomy_fit=4,sc_tax_issue=[1],sc_note='Incoherent.')))
 def test_46_current_and_historical_issue_code_rules(self):
  for code in (3,4,6):
   self.assertTrue(v.validate_scratch(dict(self.sc(),sc_taxonomy_fit=2,sc_tax_issue=[code],sc_note='Retired current code.')))
   self.assertFalse(v.validate_scratch(dict(self.sc(),record_kind='',instrument_ver=v.HISTORICAL_VERSION,sc_blind_decl=1,sc_taxonomy_fit=2,sc_tax_issue=[code],sc_note='Historical response.')))
 def test_47_hidden_or_missing_issue_rules(self):
  self.assertTrue(v.validate_scratch(dict(self.sc(),sc_taxonomy_fit=1,sc_tax_issue=[1])))
  self.assertTrue(v.validate_scratch(dict(self.sc(),sc_taxonomy_fit=2,sc_note='Missing issue type.')))
  self.assertTrue(v.validate_owner(dict(self.po(),po_taxonomy_fit=1,po_tax_issue=[1]),self.mapping()))
  self.assertTrue(v.validate_owner(dict(self.po(),po_taxonomy_fit=2,po_note='Missing issue type.'),self.mapping()))
 def test_48_other_problem_requires_note_and_owner_has_no_fit_code_4(self):
  self.assertTrue(v.validate_scratch(dict(self.sc(),sc_taxonomy_fit=2,sc_tax_issue=[5])))
  self.assertTrue(v.validate_owner(dict(self.po(),po_taxonomy_fit=2,po_tax_issue=[5]),self.mapping()))
  self.assertTrue(v.validate_owner(dict(self.po(),po_taxonomy_fit=4),self.mapping()))
 def test_49_dictionary_field_count_and_owner_actual_project_wording(self):
  rows=self.rows(); by={r['Variable / Field Name']:r for r in rows}
  self.assertEqual(len(rows),150)
  self.assertIn('actual-project fit',by['po_intro']['Field Label'])
  self.assertIn('actual project',by['po_d01_fit']['Field Label'])
  self.assertEqual(v.choices(by['owner_recruit_route']['Choices, Calculations, OR Slider Labels'])['2'],'Supplementary purposive')
 def test_50_taxonomy_fit_help_is_synchronised_to_derived_materials(self):
  with (self.package/'redcap_field_response_specification.csv').open(encoding='utf-8-sig',newline='') as f:
   spec=[r for r in csv.DictReader(f) if r['variable_name']=='sc_taxonomy_fit']
  self.assertEqual(len(spec),4)
  self.assertTrue(all(r['notes']==v.SC_TAXONOMY_FIT_HELP for r in spec))
  preview=(self.package/'redcap_candidate_instrument_preview.html').read_text(encoding='utf-8')
  self.assertIn(v.SC_TAXONOMY_FIT_HELP,preview)
  codebook=(self.package/'redcap_instrument_codebook.md').read_text(encoding='utf-8')
  self.assertIn(v.SC_TAXONOMY_FIT_HELP,' '.join(codebook.split()))
 def test_51_missing_taxonomy_fit_help_fails(self):
  rows=self.rows(); next(r for r in rows if r['Variable / Field Name']=='sc_taxonomy_fit')['Field Note']=''; self.write_rows(rows)
  with self.assertRaisesRegex(v.CandidateError,'taxonomy-fit help text differs'): self.check()
 def test_52_obsolete_pilot_issue_options_are_absent_but_historical_mapping_remains(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  current=set(v.choices(by['sc_tax_issue']['Choices, Calculations, OR Slider Labels']).values())
  self.assertTrue({'None','Too broad','Too narrow'}.isdisjoint(current))
  history=yaml.safe_load((self.package/'redcap_branching_validation_specification.yaml').read_text(encoding='utf-8'))['historical_versions']['redcap-candidate-0.3']
  self.assertEqual(history['scratch_taxonomy_fit_codes'],{1:'Fit',2:'Partial Fit',3:'No Fit'})
  self.assertEqual(history['taxonomy_issue_codes'],{1:'Missing category',2:'Ambiguous/overlapping categories',3:'Too broad',4:'Too narrow',5:'Other',6:'None'})
  self.assertTrue(history['decode_only'])
  self.assertTrue(history['no_destructive_recode'])

 def test_53_record_kind_and_coder_declaration_are_exact(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  record_kind=by['record_kind']
  self.assertEqual(record_kind['Form Name'],'assignment_admin')
  self.assertEqual(record_kind['Field Type'],'radio')
  self.assertEqual(v.choices(record_kind['Choices, Calculations, OR Slider Labels']),{'1':'Project assignment','2':'Coder declaration','3':'Synthetic QA'})
  self.assertEqual(record_kind['Field Annotation'],'@HIDDEN-SURVEY @READONLY')
  self.assertEqual(by['cd_intro']['Section Header'],'Formal coding declaration')
  self.assertEqual(by['cd_declaration']['Field Label'],v.CD_DECLARATION_LABEL)
  self.assertEqual(v.choices(by['cd_declaration']['Choices, Calculations, OR Slider Labels']),{'1':'Confirmed','0':'Cannot confirm'})
  self.assertEqual(by['cd_nonconfirm_note']['Branching Logic (Show field only if...)'],"[record_kind] = '2' and [cd_declaration] = '0'")
  self.assertEqual(by['cd_nonconfirm_note']['Required Field?'],'y')

 def test_54_declaration_nonconfirmation_requires_note(self):
  base={'assignment_id':'D7C4L8R2','record_kind':2,'reviewer_id':'QA01','instrument_ver':v.VERSION,'cd_declaration':1}
  self.assertFalse(v.validate_declaration(base))
  self.assertTrue(v.validate_declaration(dict(base,cd_declaration=0)))
  self.assertFalse(v.validate_declaration(dict(base,cd_declaration=0,cd_nonconfirm_note='Synthetic reason.')))

 def test_55_historical_declaration_is_preserved_and_hidden_current(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  blind=by['sc_blind_decl']
  self.assertEqual(blind['Branching Logic (Show field only if...)'],v.SC_BLIND_BRANCH)
  self.assertIn("[instrument_ver] = 'redcap-candidate-0.3'",blind['Branching Logic (Show field only if...)'])
  historical=dict(self.sc(),record_kind='',instrument_ver=v.HISTORICAL_VERSION,sc_blind_decl=1)
  self.assertFalse(v.validate_scratch(historical))
  self.assertTrue(v.validate_scratch(dict(self.sc(),sc_blind_decl=1)))

 def test_56_per_project_exposure_wording_codes_and_note_are_exact(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  exposure=by['sc_exposure']; note=by['sc_exposure_note']
  self.assertEqual(exposure['Field Label'],v.SC_EXPOSURE_LABEL)
  self.assertIn('prior involvement',exposure['Field Note'])
  self.assertIn('accidental exposure',exposure['Field Note'])
  self.assertIn('Still complete the classification',exposure['Field Note'])
  self.assertEqual(v.choices(exposure['Choices, Calculations, OR Slider Labels']),{'0':'No','1':'Yes'})
  self.assertEqual(exposure['Required Field?'],'y')
  self.assertEqual(note['Field Label'],v.SC_EXPOSURE_NOTE_LABEL)
  self.assertEqual(note['Field Note'],v.SC_EXPOSURE_NOTE_HELP)
  self.assertEqual(note['Branching Logic (Show field only if...)'],v.SC_EXPOSURE_BRANCH)
  self.assertEqual(note['Required Field?'],'y')

 def test_57_scratch_record_guard_covers_declaration_form_without_weakening_conditions(self):
  rows=[r for r in self.rows() if r['Form Name']=='scratch_coder']
  expected={r['Variable / Field Name']:v.PROJECT_RECORD_GUARD for r in rows}
  expected.update({'sc_blind_decl':v.SC_BLIND_BRANCH,'sc_exposure_note':v.SC_EXPOSURE_BRANCH,'sc_tax_issue':v.SC_TAX_ISSUE_BRANCH,'sc_note':v.SC_NOTE_BRANCH})
  self.assertEqual({r['Variable / Field Name']:r['Branching Logic (Show field only if...)'] for r in rows},expected)
  visible=lambda kind: kind!=2 or kind==''
  self.assertTrue(visible(1)); self.assertTrue(visible(3)); self.assertTrue(visible('')); self.assertFalse(visible(2))
  self.assertIn(v.SC_TAX_ISSUE_CONDITION,v.SC_TAX_ISSUE_BRANCH)
  self.assertIn(v.SC_NOTE_CONDITION,v.SC_NOTE_BRANCH)

 def test_58_candidate_0_6_scientific_fields_and_project_owner_form_are_unchanged(self):
  scientific={'sc_domains','sc_purposes','sc_covid','sc_equity','sc_sufficiency','sc_taxonomy_fit','sc_tax_issue','sc_confidence','sc_note'}
  rows=[dict(r) for r in self.rows() if r['Variable / Field Name'] in scientific]
  for row in rows:
   branch=row['Branching Logic (Show field only if...)']
   if branch==v.PROJECT_RECORD_GUARD: row['Branching Logic (Show field only if...)']=''
   elif branch.startswith(f'({v.PROJECT_RECORD_GUARD}) and (') and branch.endswith(')'): row['Branching Logic (Show field only if...)']=branch[len(v.PROJECT_RECORD_GUARD)+8:-1]
  payload=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
  self.assertEqual(hashlib.sha256(payload).hexdigest(),'f08c540e5b8490703fc7591b34088e193908c81de090869832b42b0a3617173c')
  owner=[r for r in self.rows() if r['Form Name']=='project_owner']
  payload=json.dumps(owner,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
  self.assertEqual(hashlib.sha256(payload).hexdigest(),'568940ceade8eac8a236d60c6b4d051123cc78140e54f003721dbab6b8ce07a1')

 def test_59_raw_pilot_and_candidate_0_3_mapping_are_unchanged(self):
  raw=v.ROOT/'preregistration/package/05_training_and_pilot/pilot_raw_DATA_2026-07-20_2153.csv'
  self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(),'ab338998123b806898cfb714814b6b51cde918deffd5e6345a98b7871db093f5')
  with raw.open(encoding='utf-8-sig',newline='') as handle:
   versions={r['instrument_ver'] for r in csv.DictReader(handle)}
  self.assertEqual(versions,{v.HISTORICAL_VERSION})

 def test_60_live_qa_fixtures_are_synthetic_excluded_and_not_formal(self):
  qa=self.package/'live_qa'
  current=[]
  for name in ('redcap_live_qa_coder_declaration_candidate_0.7.csv','redcap_live_qa_synthetic_project_assignment_candidate_0.7.csv'):
   with (qa/name).open(encoding='utf-8',newline='') as handle: current.extend(csv.DictReader(handle))
  self.assertEqual({r['record_kind'] for r in current},{'2','3'})
  self.assertTrue(all(r['instrument_ver']==v.VERSION and r['validation_included']=='0' and r['sample_status']=='3' for r in current))
  self.assertFalse(any(r['record_kind']=='1' for r in current))
  self.assertTrue((qa/'redcap_live_qa_synthetic_assignments_candidate_0.6.csv').is_file())

 def test_61_candidate_0_7_documentation_is_synchronised(self):
  docs={
   'README.md':['redcap-candidate-0.7','one-time coder-level governance control','Yes does not mean the project should be skipped'],
   'redcap_instrument_codebook.md':['redcap-candidate-0.7','One-time coder declaration and per-project exposure','Exposure-flagged coder–project responses remain in the primary analysis'],
   'redcap_project_setup_checklist.md':['candidate 0.7','four-form order and 150 fields'],
   'redcap_instrument_qa_checklist.md':['redcap-candidate-0.7','field count is 150'],
   'redcap_live_runtime_qa_template.md':['candidate-0.7','Four forms and 150 fields confirmed'],
   'redcap_version_history.md':['redcap-candidate-0.7','superseded before final runtime QA by candidate 0.7','frozen on 22 July 2026','zero residual mismatches'],
   'redcap_live_runtime_qa_20260722.md':['live-runtime QA and candidate-0.7 freeze','Restricted C02 QA — passed','pilot_and_qa_archi','Residual mismatches are zero','formal sampling and assignment import remain prohibited'],
  }
  for name,needles in docs.items():
   text=' '.join((self.package/name).read_text(encoding='utf-8').split())
   for needle in needles: self.assertIn(needle,text,name)
  with (v.ROOT/'preregistration/preregistration_artifact_manifest.csv').open(encoding='utf-8',newline='') as handle:
   manifest={r['artifact_id']:r for r in csv.DictReader(handle)}
  self.assertEqual(manifest['RED-001']['version'],v.VERSION)
  self.assertEqual(manifest['RED-001']['supersedes_or_superseded_by'],'redcap-candidate-0.6')
  self.assertEqual(manifest['RED-022']['version'],v.VERSION)
  self.assertEqual(manifest['RED-023']['version'],v.VERSION)
  self.assertEqual(manifest['RED-026']['sha256'],'bb1de2b9ea811afc8b0f23fcb489c1e01eb94d6677d45a64c273140532c5293f')
  self.assertEqual(manifest['RED-036']['frozen'],'true')
  self.assertEqual(manifest['RED-036']['registered'],'false')
  frozen=self.package/'redcap_data_dictionary_frozen_0.7_2026-07-22.csv'
  self.assertEqual(frozen.read_bytes(),(self.package/'redcap_data_dictionary_candidate.csv').read_bytes())

if __name__=='__main__': unittest.main()
