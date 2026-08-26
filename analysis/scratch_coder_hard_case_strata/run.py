from __future__ import annotations
import hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from analysis.scratch_coder_stage_b.config import ROOT,ATTEMPTS,SEED
from analysis.scratch_coder_stage_b.support import authorities,sha
from .analysis import run_analysis
from .report import write_csv,summary,methods,notebook
OUT=ROOT/'analysis/outputs_validation_scratch_hard_case_strata_20260825'
def hashes(d):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file() and p.suffix in {'.csv','.json'}}
def main():
 if OUT.exists():raise FileExistsError(OUT)
 before_a=hashes(ROOT/'analysis/outputs_validation_scratch_20260824');before_b=hashes(ROOT/'analysis/outputs_validation_scratch_stage_b_20260825');initial=subprocess.run(['git','status','--short','--untracked-files=all'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.splitlines();checks=authorities();r=run_analysis(ATTEMPTS);OUT.mkdir()
 for name,key in [('hard_case_stratum_exact_set_jaccard.csv','model'),('hard_case_stratum_human_pair_agreement.csv','human'),('hard_case_stratum_replacement.csv','replacement'),('bootstrap_hard_case_stratum_exact_set_jaccard.csv','set_boot'),('bootstrap_hard_case_stratum_replacement.csv','rep_boot')]:write_csv(OUT/name,r[key])
 (OUT/'hard_case_stratum_summary.md').write_text(summary(r));(OUT/'methods_hard_case_strata.md').write_text(methods());notebook(OUT)
 text='\n'.join(x.read_text(encoding='utf-8',errors='ignore') for x in OUT.iterdir() if x.is_file());model=pd.read_csv(ROOT/'analysis/outputs_classified_20260702_fable5/layer_classifications.csv');titles=set(model.loc[model['Record ID'].isin(r['data'].formal_ids),'Title'].astype(str))-{''};mask={'source_ids_exposed':sum(x in text for x in r['data'].formal_ids),'project_titles_exposed':sum(x in text for x in titles),'record_level_disagreement_outputs':sum((OUT/x).exists() for x in ('adjudication_population.csv','disagreement_records.csv','model_errors.csv'))}
 if any(mask.values()):raise RuntimeError('mask failure')
 after_a=hashes(ROOT/'analysis/outputs_validation_scratch_20260824');after_b=hashes(ROOT/'analysis/outputs_validation_scratch_stage_b_20260825');assert before_a==after_a and before_b==after_b
 meta={'analysis_run_datetime':datetime.now(timezone.utc).isoformat(),'git_head':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip(),'working_tree_entry_state':initial,'verified_authorities':[x.__dict__ for x in checks],'bootstrap_seed':SEED,'bootstrap_replicates':ATTEMPTS,'quantile_method':'Hyndman–Fan Type 7 / linear','stratum_counts':{k:len(v) for k,v in r['strata'].items()},'overall_hard_case_reconciliation':'YES','masking':mask,'stage_a_numerical_output_changes':0,'stage_b_numerical_output_changes':0}
 (OUT/'run_metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta['stratum_counts']))
if __name__=='__main__':main()
