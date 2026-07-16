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
 def sc(self): return {'assignment_id':'A7K3M9Q2','sc_blind_decl':1,'sc_exposure':0,'sc_domains':[1],'sc_purposes':[1],'sc_covid':0,'sc_equity':0,'sc_sufficiency':1,'sc_taxonomy_fit':1,'sc_confidence':1}
 def admin(self): return {'assignment_id':'B6J4K8M2','review_stream':1,'sample_set':1,'validation_included':1}
 def po(self): return {'assignment_id':'Q4N8Z2L7','cluster_id':'SYNTH-P','owner_resp_id':'SYNTH-O','prop_d01':1,'po_d01_fit':1,'po_d01_vis':1,'po_miss_domain':0,'po_miss_purpose':0,'po_miss_tag':0,'po_sufficiency':1,'po_taxonomy_fit':1}
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
 def test_31_multiple_owners_share_project_but_not_assignment(self): self.assertEqual(v.validate_submissions(self.fixture)['cases'],27)
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
 def test_40_scratch_coder_form_signature_is_unchanged(self):
  rows=[r for r in self.rows() if r['Form Name']=='scratch_coder']; payload=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
  self.assertEqual(hashlib.sha256(payload).hexdigest(),'8f59881f91573106a2327fc6d056fd04b9bdb34816846daf0898e3b26196c00f')
 def test_41_candidate_version_is_0_3(self): self.assertEqual(yaml.safe_load((self.package/'redcap_branching_validation_specification.yaml').read_text(encoding='utf-8'))['version'],'redcap-candidate-0.3')
 def test_42_runtime_corrections_remain_intact(self):
  by={r['Variable / Field Name']:r for r in self.rows()}
  self.assertEqual(by['sc_purposes']['Field Annotation'],v.PURPOSE_ANNOTATION)
  self.assertEqual(by['sc_note']['Branching Logic (Show field only if...)'],v.SC_NOTE_BRANCH)
  self.assertNotIn('sc_exposure',by['sc_note']['Branching Logic (Show field only if...)'])

if __name__=='__main__': unittest.main()
