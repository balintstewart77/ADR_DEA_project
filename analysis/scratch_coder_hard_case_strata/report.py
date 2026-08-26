from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from analysis.scratch_coder_stage_b.support import sha

def write_csv(path,rows):pd.DataFrame(rows).to_csv(path,index=False,lineterminator='\n')
def summary(results):
 m=pd.DataFrame(results['model']);h=pd.DataFrame(results['human']);r=pd.DataFrame(results['replacement']);lines=['# Hard-case sampling-strata diagnostic','','> Post hoc diagnostic analysis of the preregistered 75-record hard-case sample. The three 25-record strata were selected using prior cross-model disagreement and are deliberately non-representative. Results below assess whether that sampling signal corresponded to lower subsequent Fable/scratch-coder agreement in the intended dimension.','','## Pair-averaged model–coder comparison','','| Stratum | Domain exact-set | Domain Jaccard | Purpose exact-set | Purpose Jaccard |','|---|---:|---:|---:|---:|']
 compact={}
 for s in ('domain_only','purpose_only','both'):
  d=m[(m.stratum==s)&(m.dimension=='Research Domains')].iloc[0];p=m[(m.stratum==s)&(m.dimension=='Analytical Purposes')].iloc[0];compact[s]=(d.mean_model_coder_exact_set,d.mean_model_coder_jaccard,p.mean_model_coder_exact_set,p.mean_model_coder_jaccard);lines.append(f'| {s} | {d.mean_model_coder_exact_set:.3f} | {d.mean_model_coder_jaccard:.3f} | {p.mean_model_coder_exact_set:.3f} | {p.mean_model_coder_jaccard:.3f} |')
 lines+=['','Positive Domain-minus-Purpose contrasts indicate higher Domain agreement; negative contrasts indicate lower Domain agreement.']
 for s,v in compact.items():lines.append(f'- {s}: exact-set {v[0]-v[2]:.3f}; Jaccard {v[1]-v[3]:.3f}.')
 lines+=['','Across-stratum descriptive contrasts (first minus second; no hypothesis tests):']
 for dim,index_exact,index_jaccard in [('Domain',0,1),('Purpose',2,3)]:
  for left,right in [('domain_only','purpose_only'),('domain_only','both'),('purpose_only','both')]:lines.append(f'- {dim} {left} minus {right}: exact-set {compact[left][index_exact]-compact[right][index_exact]:.3f}; Jaccard {compact[left][index_jaccard]-compact[right][index_jaccard]:.3f}.')
 lines+=['','## Human–human context','','| Stratum | Domain exact-set | Domain Jaccard | Purpose exact-set | Purpose Jaccard |','|---|---:|---:|---:|---:|']
 for s in ('domain_only','purpose_only','both'):
  d=h[(h.stratum==s)&(h.dimension=='Research Domains')];p=h[(h.stratum==s)&(h.dimension=='Analytical Purposes')];lines.append(f'| {s} | {d.exact_match_proportion.mean():.3f} | {d.mean_jaccard.mean():.3f} | {p.exact_match_proportion.mean():.3f} | {p.mean_jaccard.mean():.3f} |')
 lines+=['','## Full model–coder results','','| Stratum | Dimension | Pair | Exact-set [95% CI] | Mean Jaccard [95% CI] |','|---|---|---|---:|---:|']
 for x in m.itertuples():lines.append(f'| {x.stratum} | {x.dimension} | {x.pair} | {x.exact_match_proportion:.3f} [{x.exact_match_ci_lower:.3f}, {x.exact_match_ci_upper:.3f}] | {x.mean_jaccard:.3f} [{x.mean_jaccard_ci_lower:.3f}, {x.mean_jaccard_ci_upper:.3f}] |')
 lines+=['','## Replacement-panel diagnostic','','POST HOC / DIAGNOSTIC / N=25 PER STRATUM. No baseline mechanical review triggers are applied.','','| Stratum | Dimension | Human α | Replace A | Replace B | Replace C | Δmin [95% CI] |','|---|---|---:|---:|---:|---:|---:|']
 for x in r.itertuples():lines.append(f'| {x.stratum} | {x.dimension} | {x.human_alpha:.3f} | {x.replace_a_alpha:.3f} | {x.replace_b_alpha:.3f} | {x.replace_c_alpha:.3f} | {x.delta_min:.3f} [{x.delta_min_ci_lower:.3f}, {x.delta_min_ci_upper:.3f}] |')
 lines+=['','## Interpretation','','The results are descriptive only. The stratum labels describe the prior cross-model disagreement selection mechanism, not true errors or a gold standard. No classifier release decision, population-performance inference, per-label analysis, or adjudication follows from this diagnostic.']
 return '\n'.join(lines)+'\n'
def methods():return '''# Hard-case strata methods

This is a post hoc exploratory diagnostic of the frozen hard-case sample. The POST-019 hard-case-stratum field assigns every record to exactly one pre-existing 25-record `domain_only`, `purpose_only`, or `both` cross-model-disagreement stratum. The strata are deliberately non-representative.

Stage B's canonical A/B/C/L record blocks, unordered set representation, exact-set equality, Jaccard definition (empty/empty=1), and record bootstrap are reused. Model-coder pairs are L-A/L-B/L-C and human context pairs are A-B/A-C/B-C. Pair-averaged model-coder values are descriptive display summaries, not independent estimates.

Replacement alpha reuses Stage A's MASI distances, complete-case conventions, αABC/LBC/ALC/ABL implementation, deltas, and 2,000 record-level resamples (seed 20260714; Type-7 linear percentiles). No tag stratum analyses, per-label metrics, support bands, release triggers, or adjudication counts are calculated. All outputs are aggregate-only and scanned for source IDs/titles.
'''
def notebook(out):
 cells=[{'cell_type':'markdown','metadata':{},'source':['# Hard-case strata aggregate review\n']},{'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':["from pathlib import Path\nimport sys\nROOT=Path.cwd().resolve()\nwhile ROOT != ROOT.parent and not (ROOT/'.git').exists(): ROOT=ROOT.parent\nsys.path.insert(0,str(ROOT))\nimport pandas as pd\nfrom analysis.scratch_coder_hard_case_strata.analysis import run_analysis\nOUT=ROOT/'analysis/outputs_validation_scratch_hard_case_strata_20260825'\n"]},{'cell_type':'markdown','metadata':{},'source':['## Aggregate stratum comparisons\n']},{'cell_type':'code','metadata':{},'execution_count':None,'outputs':[], 'source':["model=pd.read_csv(OUT/'hard_case_stratum_exact_set_jaccard.csv'); human=pd.read_csv(OUT/'hard_case_stratum_human_pair_agreement.csv'); replacement=pd.read_csv(OUT/'hard_case_stratum_replacement.csv'); (model,human,replacement)\n"]}]
 (out/'scratch_coder_hard_case_strata_review.ipynb').write_text(json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5},indent=1)+'\n')
