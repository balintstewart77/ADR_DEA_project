from __future__ import annotations
import numpy as np
from .agreement import blocks
from .bootstrap import samples,interval
from .config import TAGS
from .metrics import tagstats
from .support import band
def diagnostics(data,attempts):
 base=blocks(data,data.baseline_ids);support={t:sum(sum(x[t][:3])>=2 for x in base) for t in TAGS};srows=[];rows=[];rep=[]
 for tag in TAGS:
  a=np.array([x[tag] for x in base]);n=support[tag];srows.append({'dimension':'Cross-cutting tag','label':tag,'baseline_human_majority_positive_n':n,'baseline_human_majority_prevalence':n/150,'baseline_model_positive_n':int(a[:,3].sum()),'baseline_model_prevalence':float(a[:,3].mean()),'support_band':band(n),'eligible_for_per_label_performance':n>=10,'eligible_for_macro_average':False,'low_support_caution_required':band(n)=='LOW SUPPORT'})
 for pop,ids in [('baseline',data.baseline_ids),('hard_case',data.hard_case_ids)]:
  b=blocks(data,ids);d=samples(len(b),attempts)
  for tag in TAGS:
   a=np.array([x[tag] for x in b]);ref=(a[:,:3].sum(1)>=2).astype(int);model=a[:,3];point=tagstats(ref,model);metrics=('raw_agreement','positive_agreement','negative_agreement','cohen_kappa','gwet_ac1','precision','recall','f1');vals={m:[] for m in metrics}
   for r,x in enumerate(d,1):
    z=tagstats(ref[x],model[x]);rep.append({'population':pop,'tag':tag,'replicate':r,**{m:z[m] for m in metrics}})
    for m in metrics:vals[m].append(z[m])
   row={'population':pop,'tag':tag,'baseline_support_n':support[tag],'support_band':band(support[tag]),'n_records':len(b),**point,'low_support_caution':band(support[tag])=='LOW SUPPORT','analysis_note':'DIAGNOSTIC — disagreement-enriched and non-representative.' if pop=='hard_case' else ''}
   for m in metrics:
    z=interval(vals[m],attempts);row.update({m+'_ci_lower':z['lower'],m+'_ci_upper':z['upper'],m+'_bootstrap_valid_n':z['valid'],m+'_bootstrap_invalid_n':z['invalid']})
   rows.append(row)
 return rows,rep,srows
