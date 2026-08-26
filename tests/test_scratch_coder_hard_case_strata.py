from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from analysis.scratch_coder_hard_case_strata.analysis import build_strata, verify_overall
from analysis.scratch_coder_hard_case_strata.run import OUT

def test_frozen_crosswalk_partitions_hard_case_exactly():
 data,strata=build_strata()
 assert {k:len(v) for k,v in strata.items()}=={'domain_only':25,'purpose_only':25,'both':25}
 assert frozenset().union(*strata.values())==data.hard_case_ids
 assert sum(len(v) for v in strata.values())==75

def test_aggregate_outputs_have_required_pairs_and_no_record_outputs():
 model=pd.read_csv(OUT/'hard_case_stratum_exact_set_jaccard.csv');human=pd.read_csv(OUT/'hard_case_stratum_human_pair_agreement.csv');rep=pd.read_csv(OUT/'hard_case_stratum_replacement.csv')
 assert len(model)==18 and set(model.pair)=={'L-A','L-B','L-C'} and set(model.n_records)=={25}
 assert len(human)==18 and set(human.pair)=={'A-B','A-C','B-C'} and set(human.n_records)=={25}
 assert len(rep)==6 and set(rep.dimension)=={'Research Domains','Analytical Purposes'} and set(rep.n_records)=={25}
 assert not any('adjudication' in x.name or 'disagreement_records' in x.name for x in OUT.iterdir())

def test_union_reproduces_frozen_stage_a_and_b_hard_case_results():
 data,strata=build_strata();assert verify_overall(data,strata)
 meta=json.loads((OUT/'run_metadata.json').read_text());assert meta['overall_hard_case_reconciliation']=='YES'

def test_outputs_are_source_masked():
 data,_=build_strata();text='\n'.join(x.read_text(encoding='utf-8',errors='ignore') for x in OUT.iterdir() if x.is_file())
 assert not any(x in text for x in data.formal_ids)
