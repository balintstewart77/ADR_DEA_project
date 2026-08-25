from __future__ import annotations
def div(a,b):return None if b==0 else a/b
def contingency(ref,pred):
 tp=fp=fn=tn=0
 for a,b in zip(ref,pred,strict=True):
  if a and b:tp+=1
  elif b:fp+=1
  elif a:fn+=1
  else:tn+=1
 return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'n':tp+fp+fn+tn}
def prf(c):
 p=div(c['tp'],c['tp']+c['fp']);r=div(c['tp'],c['tp']+c['fn']);return {'precision':p,'recall':r,'f1':None if p is None or r is None or p+r==0 else 2*p*r/(p+r)}
def kappa(a,b):
 x=list(zip(a,b,strict=True));n=len(x)
 if not n:return None
 po=sum(u==v for u,v in x)/n;pa=sum(u for u,_ in x)/n;pb=sum(v for _,v in x)/n;pe=pa*pb+(1-pa)*(1-pb);return None if 1-pe==0 else (po-pe)/(1-pe)
def ac1(a,b):
 x=list(zip(a,b,strict=True));n=len(x)
 if not n:return None
 po=sum(u==v for u,v in x)/n;p=(sum(u for u,_ in x)+sum(v for _,v in x))/(2*n);pe=2*p*(1-p);return None if 1-pe==0 else (po-pe)/(1-pe)
def tagstats(ref,pred):
 c=contingency(ref,pred);tp,fp,fn,tn,n=(c[k] for k in ('tp','fp','fn','tn','n'));return {**c,'human_majority_positive_n':tp+fn,'human_majority_prevalence':div(tp+fn,n),'model_positive_n':tp+fp,'model_prevalence':div(tp+fp,n),'raw_agreement':div(tp+tn,n),'positive_agreement':div(2*tp,2*tp+fp+fn),'negative_agreement':div(2*tn,2*tn+fp+fn),'cohen_kappa':kappa(ref,pred),'gwet_ac1':ac1(ref,pred),**prf(c)}
def jac(a,b):return 1.0 if not(a|b) else len(a&b)/len(a|b)
