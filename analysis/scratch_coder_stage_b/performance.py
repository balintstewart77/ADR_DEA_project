"""Support, contingency, kappa, and fixed-label macro estimands."""
from __future__ import annotations
import numpy as np
from analysis.scratch_coder_stage_a.panels import _taxonomy_labels
from .agreement import blocks
from .bootstrap import samples,interval
from .metrics import contingency,prf,kappa
from .support import band
def labels():
 x=_taxonomy_labels();return {'Research Domains':tuple(sorted(x['domains'])),'Analytical Purposes':tuple(sorted(x['purposes']))}
def vectors(b,dim,label):
 humans=np.array([[int(label in x[dim][i]) for i in range(3)] for x in b],int);return humans,(humans.sum(1)>=2).astype(int),np.array([int(label in x[dim][3]) for x in b],int)
def support_contingencies(data):
 b=blocks(data,data.baseline_ids);support=[];cont=[];index={}
 for dim,labs in labels().items():
  for label in labs:
   _,ref,model=vectors(b,dim,label);n=int(ref.sum());z=band(n);index[(dim,label)]=n;c=contingency(ref,model)
   support.append({'dimension':dim,'label':label,'baseline_human_majority_positive_n':n,'baseline_human_majority_prevalence':n/len(b),'baseline_model_positive_n':int(model.sum()),'baseline_model_prevalence':float(model.mean()),'support_band':z,'eligible_for_per_label_performance':n>=10,'eligible_for_macro_average':n>=10,'low_support_caution_required':z=='LOW SUPPORT'})
   cont.append({'dimension':dim,'label':label,'baseline_n':len(b),'human_majority_positive_n':n,'human_majority_prevalence':n/len(b),'model_positive_n':int(model.sum()),'model_prevalence':float(model.mean()),**c,'support_band':z,'performance_metrics_reportable':n>=10})
 return support,cont,index
def performance_kappa_macro(data,index,attempts):
 b=blocks(data,data.baseline_ids);draw=samples(len(b),attempts);perf=[];kap=[];prepr=[];kaprep=[];mac=[];macrep=[];pairs=((0,1,'A-B'),(0,2,'A-C'),(1,2,'B-C'),(3,0,'L-A'),(3,1,'L-B'),(3,2,'L-C'))
 for dim,labs in labels().items():
  eligible=[lab for lab in labs if index[(dim,lab)]>=10];mv={m:[] for m in ('precision','recall','f1')};point={m:[] for m in mv}
  for label in eligible:
   n=index[(dim,label)];z=band(n);h,ref,model=vectors(b,dim,label);p=prf(contingency(ref,model));vals={m:[] for m in p};kvals={name:[] for _,_,name in pairs}
   for r,d in enumerate(draw,1):
    zvals=prf(contingency(ref[d],model[d]));prepr.append({'dimension':dim,'label':label,'replicate':r,**zvals})
    for m in vals:vals[m].append(zvals[m])
    rr={'dimension':dim,'label':label,'replicate':r}
    for a,c,name in pairs:
     left=model[d] if a==3 else h[d,a];right=model[d] if c==3 else h[d,c];v=kappa(left,right);kvals[name].append(v);rr[name]=v
    kaprep.append(rr)
   row={'dimension':dim,'label':label,'support_n':n,'support_band':z,'n_records':len(b),'low_support_caution':z=='LOW SUPPORT'}
   for m in vals:
    ci=interval(vals[m],attempts);row.update({m:p[m],m+'_ci_lower':ci['lower'],m+'_ci_upper':ci['upper'],m+'_bootstrap_valid_n':ci['valid'],m+'_bootstrap_invalid_n':ci['invalid']});point[m].append(p[m]);mv[m].append(vals[m])
   perf.append(row)
   for a,c,name in pairs:
    ci=interval(kvals[name],attempts);kap.append({'dimension':dim,'label':label,'support_n':n,'support_band':z,'pair':name,'n_records':len(b),'kappa':kappa(model if a==3 else h[:,a],model if c==3 else h[:,c]),'ci_lower':ci['lower'],'ci_upper':ci['upper'],'bootstrap_valid_n':ci['valid'],'bootstrap_invalid_n':ci['invalid'],'low_support_caution':z=='LOW SUPPORT'})
  mrow={'dimension':dim,'eligible_label_n':len(eligible),'eligible_labels':'; '.join(eligible)}
  for r in range(attempts):
   rr={'dimension':dim,'replicate':r+1}
   for m in mv:
    xs=[mv[m][j][r] for j in range(len(eligible))];rr[m]=None if any(v is None for v in xs) else float(np.mean(xs))
   macrep.append(rr)
  for m in mv:
   vals=[x[m] for x in macrep if x['dimension']==dim];ci=interval(vals,attempts);mrow.update({m:None if any(v is None for v in point[m]) else float(np.mean(point[m])),m+'_ci_lower':ci['lower'],m+'_ci_upper':ci['upper'],m+'_bootstrap_valid_n':ci['valid'],m+'_bootstrap_invalid_n':ci['invalid']})
  mac.append(mrow)
 return perf,kap,prepr,kaprep,mac,macrep
