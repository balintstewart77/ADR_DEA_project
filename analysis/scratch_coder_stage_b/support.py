"""Frozen-authority checks and controlled reuse of audited Stage A parsing."""
from __future__ import annotations
import hashlib
from pathlib import Path
import pandas as pd
from analysis.scratch_coder_stage_a import load as a_load, panels as a_panels
from analysis.scratch_coder_stage_a.load import AuthorityCheck, resolve_manifest_row
from .config import ROOT,RAW,OVERRIDE,RAW_MOD,LF_MOD
def sha(path:Path):
 h=hashlib.sha256();
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def authorities():
 """Verify all Stage-B authorities; only MOD-006 has the explicit LF exception."""
 wanted={'raw_export','protocol','instrument','validator','formal_assignment_crosswalk','baseline_sample','hard_case_sample','taxonomy_rc2','production_model'}; out=[]
 for role,aid in a_load.AUTHORITY_IDS.items():
  if role not in wanted:continue
  row=resolve_manifest_row(aid); path=RAW if aid=='POST-028' else OVERRIDE.get(aid,ROOT/row['current_path']); observed=sha(path)
  if aid=='MOD-006':
   if row['sha256']!=RAW_MOD or observed not in {RAW_MOD,LF_MOD}:raise ValueError('MOD-006 identity failure outside specified raw/LF representation rule')
   matched=True
  else:
   matched=observed==row['sha256']
  if not matched:raise ValueError(f'Authority identity failure: {aid}')
  out.append(AuthorityCheck(role,aid,path.relative_to(ROOT).as_posix(),row['sha256'],observed,path.stat().st_size,matched))
 for role,expected in {'protocol':'fd1fa40b8047a4fb512cc6fc00f0ae686001b2fe9510ffe34e1c335a1df2fb77','taxonomy_rc2':'7ddbf1bb5ae4588c82c7c23f90bd96885684ff1ec71382f6403c36c4b89e31de'}.items():
  if next(x for x in out if x.role==role).expected_sha256!=expected:raise ValueError(f'Protected manifest identity failure: {role}')
 return tuple(out)
def build_stage_b_data():
 """Call, but never alter, Stage A's canonical parsing and panel construction."""
 old_load,old_read=a_panels.load_frozen_export,a_panels.read_manifest_csv
 def load_raw():return pd.read_csv(RAW,dtype=str,keep_default_na=False,encoding='utf-8-sig')
 def read(aid):return pd.read_csv(OVERRIDE.get(aid,ROOT/resolve_manifest_row(aid)['current_path']),dtype=str,keep_default_na=False,encoding='utf-8-sig')
 try:
  a_panels.load_frozen_export=load_raw;a_panels.read_manifest_csv=read;data=a_panels.build_stage_a_data()
 finally:a_panels.load_frozen_export=old_load;a_panels.read_manifest_csv=old_read
 assert (data.raw_rows,data.raw_columns,len(data.responses),len(data.formal_ids),len(data.baseline_ids),len(data.hard_case_ids),data.structural_invalid_response_count,data.exposure_response_count)==(713,164,675,225,150,75,0,1)
 assert data.hard_stratum_counts=={'domain_only':25,'purpose_only':25,'both':25}
 return data
def band(n):return 'RARE' if n<10 else 'LOW SUPPORT' if n<30 else 'STANDARD'
