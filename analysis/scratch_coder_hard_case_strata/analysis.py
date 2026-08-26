"""Stratum diagnostics reusing Stage A/B canonical data and estimators."""
from __future__ import annotations
import numpy as np
import pandas as pd
from analysis.scratch_coder_stage_a.panels import dimension_panels, distance_for_dimension
from analysis.scratch_coder_stage_a.agreement import encode_panels, bootstrap_replacement, encoded_replacement_statistics
from analysis.validation.replacement import replacement_panel_analysis
from analysis.scratch_coder_stage_b.agreement import blocks, q
from analysis.scratch_coder_stage_b.bootstrap import samples, interval
from analysis.scratch_coder_stage_b.metrics import jac
from analysis.scratch_coder_stage_b.support import build_stage_b_data
from analysis.scratch_coder_stage_b.config import CROSS, SETS, SEED, ATTEMPTS

MODEL_PAIRS=((3,0,'L-A'),(3,1,'L-B'),(3,2,'L-C'))
HUMAN_PAIRS=((0,1,'A-B'),(0,2,'A-C'),(1,2,'B-C'))

def build_strata(data=None):
 data=build_stage_b_data() if data is None else data
 cross=pd.read_csv(CROSS,dtype=str,keep_default_na=False)
 hard=cross[cross.sample_family.eq('hard_case')]
 grouped=hard.groupby('source_record_id')['hard_case_stratum'].agg(lambda x:set(x))
 if not all(len(x)==1 for x in grouped):raise ValueError('A hard-case record has zero or multiple strata')
 strata={name:frozenset(grouped[grouped.map(lambda x:next(iter(x))==name)].index) for name in ('domain_only','purpose_only','both')}
 if {x for ids in strata.values() for x in ids} != set(data.hard_case_ids) or sum(len(x) for x in strata.values())!=75 or {k:len(v) for k,v in strata.items()}!={'domain_only':25,'purpose_only':25,'both':25}:raise ValueError('Hard-case strata do not partition the frozen 75-record population 25/25/25')
 return data,strata

def _set_rows(stratum, records, dimension, pairs, attempts, bootstrap):
 rows=[];reps=[]
 for left,right,pair in pairs:
  exact=np.array([x[dimension][left]==x[dimension][right] for x in records],float);jacc=np.array([jac(x[dimension][left],x[dimension][right]) for x in records],float)
  row={'stratum':stratum,'dimension':dimension,'pair':pair,'n_records':len(records),'exact_match_n':int(exact.sum()),'exact_match_proportion':float(exact.mean()),'mean_jaccard':float(jacc.mean()),'median_jaccard':q(jacc,.5),'q1_jaccard':q(jacc,.25),'q3_jaccard':q(jacc,.75)}
  if bootstrap:
   ev=[];jv=[]
   for r,d in enumerate(samples(len(records),attempts),1):
    e=float(exact[d].mean());j=float(jacc[d].mean());ev.append(e);jv.append(j);reps.append({'stratum':stratum,'dimension':dimension,'pair':pair,'replicate':r,'exact_match_proportion':e,'mean_jaccard':j})
   ec,jc=interval(ev,attempts),interval(jv,attempts);row.update({'exact_match_ci_lower':ec['lower'],'exact_match_ci_upper':ec['upper'],'exact_match_bootstrap_valid_n':ec['valid'],'mean_jaccard_ci_lower':jc['lower'],'mean_jaccard_ci_upper':jc['upper'],'mean_jaccard_bootstrap_valid_n':jc['valid']})
  rows.append(row)
 mean_exact=float(np.mean([x['exact_match_proportion'] for x in rows]));mean_j=float(np.mean([x['mean_jaccard'] for x in rows]))
 for row in rows:row.update({'mean_model_coder_exact_set':mean_exact,'mean_model_coder_jaccard':mean_j})
 return rows,reps

def set_diagnostics(data,strata,attempts):
 model=[];human=[];reps=[]
 for name,ids in strata.items():
  rec=blocks(data,ids)
  for dim in SETS:
   x,b=_set_rows(name,rec,dim,MODEL_PAIRS,attempts,True);model.extend(x);reps.extend(b)
   y,_=_set_rows(name,rec,dim,HUMAN_PAIRS,attempts,False);human.extend(y)
 return model,human,reps

def replacement_diagnostics(data,strata,attempts):
 rows=[];reps=[]
 for name,ids in strata.items():
  for dim in SETS:
   panels=dimension_panels(data,ids,dim);point=replacement_panel_analysis(panels,distance_for_dimension(dim));encoded=encode_panels(panels,distance_for_dimension(dim));boot=bootstrap_replacement(encoded,attempts=attempts,seed=SEED)
   vals=[x['delta_min'] for x in boot];ci=interval(vals,attempts)
   rows.append({'stratum':name,'dimension':dim,'n_records':len(panels),'human_alpha':point.alpha_abc.alpha,'replace_a_alpha':point.alpha_lbc.alpha,'replace_b_alpha':point.alpha_alc.alpha,'replace_c_alpha':point.alpha_abl.alpha,'delta_a':point.delta_a,'delta_b':point.delta_b,'delta_c':point.delta_c,'delta_min':point.delta_min,'delta_min_ci_lower':ci['lower'],'delta_min_ci_upper':ci['upper'],'bootstrap_valid_n':ci['valid'],'bootstrap_invalid_n':ci['invalid']})
   reps.extend({'stratum':name,'dimension':dim,**x} for x in boot)
 return rows,reps

def verify_overall(data,strata):
 ids=frozenset().union(*strata.values());assert ids==data.hard_case_ids
 from pathlib import Path
 root=Path(__file__).resolve().parents[2]
 saved_b=pd.read_csv(root/'analysis/outputs_validation_scratch_stage_b_20260825/exact_set_jaccard_summary.csv')
 rec=blocks(data,ids)
 for dim in SETS:
  for left,right,pair in MODEL_PAIRS:
   old=saved_b[(saved_b.population=='hard_case')&(saved_b.dimension==dim)&(saved_b.pair==pair)].iloc[0]
   assert int(sum(x[dim][left]==x[dim][right] for x in rec))==int(old.exact_match_n)
   assert np.isclose(np.mean([jac(x[dim][left],x[dim][right]) for x in rec]),old.mean_jaccard)
 saved_a=pd.read_csv(root/'analysis/outputs_validation_scratch_20260824/replacement_panel_results.csv');saved_d=pd.read_csv(root/'analysis/outputs_validation_scratch_20260824/replacement_delta_results.csv')
 for dim in SETS:
  result=replacement_panel_analysis(dimension_panels(data,ids,dim),distance_for_dimension(dim));old=saved_a[(saved_a.population=='hard_case')&(saved_a.dimension==dim)].set_index('panel');delta=saved_d[(saved_d.population=='hard_case')&(saved_d.dimension==dim)&(saved_d.delta=='delta_min')].iloc[0]
  assert all(np.isclose(a,b) for a,b in ((result.alpha_abc.alpha,old.loc['ABC','point_estimate']),(result.alpha_lbc.alpha,old.loc['LBC','point_estimate']),(result.alpha_alc.alpha,old.loc['ALC','point_estimate']),(result.alpha_abl.alpha,old.loc['ABL','point_estimate']),(result.delta_min,delta.point_estimate)))
 return True

def run_analysis(attempts=ATTEMPTS):
 data,strata=build_strata();model,human,set_boot=set_diagnostics(data,strata,attempts);replacement,rep_boot=replacement_diagnostics(data,strata,attempts);verify_overall(data,strata)
 return {'data':data,'strata':strata,'model':model,'human':human,'set_boot':set_boot,'replacement':replacement,'rep_boot':rep_boot}
