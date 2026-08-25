"""Aggregate exact-set/Jaccard calculations; record identities stay in memory."""
from __future__ import annotations
import numpy as np
from .bootstrap import samples,interval
from .metrics import jac
from .config import SETS
def blocks(data,ids):
 rows=data.responses[data.responses.record_id.isin(ids)];g={i:x for i,x in rows.groupby('record_id')};out=[]
 for rid in sorted(ids):
  c={r['coder']:r for r in g[rid].to_dict('records')};assert all(c[x]['complete'] for x in ('C01','C02','C03'))
  out.append({'Research Domains':(c['C01']['domains'],c['C02']['domains'],c['C03']['domains'],data.model[rid]['Research Domains']),'Analytical Purposes':(c['C01']['purposes'],c['C02']['purposes'],c['C03']['purposes'],data.model[rid]['Analytical Purposes']),'Demographic disparities / equity':(int(c['C01']['equity']),int(c['C02']['equity']),int(c['C03']['equity']),int(data.model[rid]['Demographic disparities / equity'])),'COVID-19 & Pandemic':(int(c['C01']['covid']),int(c['C02']['covid']),int(c['C03']['covid']),int(data.model[rid]['COVID-19 & Pandemic']))})
 return out
def q(vals,p):
 s=sorted(vals);r=(len(s)-1)*p;lo=int(r);hi=min(lo+1,len(s)-1);return s[lo]+(s[hi]-s[lo])*(r-lo)
def exact_jaccard(data,attempts):
 summary=[];rep=[]
 for pop,ids in [('baseline',data.baseline_ids),('hard_case',data.hard_case_ids)]:
  b=blocks(data,ids);draw=samples(len(b),attempts);note='DIAGNOSTIC — disagreement-enriched and non-representative.' if pop=='hard_case' else ''
  for dim in SETS:
   for i,pair in enumerate(('L-A','L-B','L-C')):
    ex=np.array([x[dim][3]==x[dim][i] for x in b],float);ja=np.array([jac(x[dim][3],x[dim][i]) for x in b],float);ev=[];jv=[]
    for k,d in enumerate(draw,1):
     e=float(ex[d].mean());j=float(ja[d].mean());ev.append(e);jv.append(j);rep.append({'population':pop,'dimension':dim,'pair':pair,'replicate':k,'exact_match_proportion':e,'mean_jaccard':j})
    ec,jc=interval(ev,attempts),interval(jv,attempts);summary.append({'population':pop,'dimension':dim,'pair':pair,'n_records':len(b),'exact_match_n':int(ex.sum()),'exact_match_proportion':float(ex.mean()),'exact_match_ci_lower':ec['lower'],'exact_match_ci_upper':ec['upper'],'exact_match_bootstrap_valid_n':ec['valid'],'exact_match_bootstrap_invalid_n':ec['invalid'],'mean_jaccard':float(ja.mean()),'mean_jaccard_ci_lower':jc['lower'],'mean_jaccard_ci_upper':jc['upper'],'mean_jaccard_bootstrap_valid_n':jc['valid'],'mean_jaccard_bootstrap_invalid_n':jc['invalid'],'median_jaccard':q(ja,.5),'q1_jaccard':q(ja,.25),'q3_jaccard':q(ja,.75),'analysis_note':note})
 return summary,rep
