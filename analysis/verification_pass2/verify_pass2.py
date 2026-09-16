"""Read-only aggregate verification. --self-test reads no repository data.

Only this script's three report files are written. No analysis modules are imported.
Decimal arithmetic is limited to the operations authorised in instruction v2.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import platform
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
START_HEAD = 'f36d738560bb7a2e1c5be68777851778c85b04d5'
RESULTS = 'analysis/scratch_coder_results/results.md'
META = 'analysis/scratch_coder_results/run_metadata.json'
S1 = 'analysis/tables/scratch_coder_supplementary_table_s1_majority_coverage.md'
COVERAGE = 'analysis/outputs_majority_coverage_20260914T170315Z/majority_coverage.csv'
RELATIONS = 'analysis/outputs_disagreement_types_20260909T084916Z/disagreement_type_distribution.csv'
UNCLEAR = 'Unclear from Register Entry'
DOM, PUR = 'Research Domains', 'Analytical Purposes'
GOOD = {'PASS', 'ASSUMPTION HOLDS', 'EQUAL', 'WITHIN RANGE'}


def git(*args):
    p = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    return p.stdout.strip(), p.returncode, p.stderr.strip()


def rnd(x, places=0):
    return D(str(x)).quantize(D(1).scaleb(-places), rounding=ROUND_HALF_UP)


def equal(a, b, places=None):
    try:
        return (rnd(a, places) if places is not None else D(str(a))) == D(str(b))
    except Exception:
        return str(a) == str(b)


def parse_md(text):
    tables, tid = {}, None
    for line in text.splitlines():
        m = re.match(r'^### (S\d+T\d+) ', line)
        if m:
            tid = m[1]
            tables[tid] = []
        elif line.startswith('##'):
            tid = None
        elif tid and line.startswith('|'):
            cells = [s.strip().strip('`') for s in line.strip('|').split('|')]
            if cells[0] != 'Row / comparator' and not cells[0].startswith('---'):
                tables[tid].append(cells)
    return tables


class Missing(Exception):
    pass


class Audit:
    def __init__(self):
        self.checks, self.claims, self.cache, self.used, self.evidence = [], [], {}, set(), []
        self.meta = json.loads((ROOT / META).read_text(encoding='utf-8'))
        self.items = self.meta['result_items']
        self.tables = parse_md((ROOT / RESULTS).read_text(encoding='utf-8'))
        self.figures = []
        for path in sorted((ROOT / 'analysis/figure_data').glob('scratch_coder*.csv')):
            rel = path.relative_to(ROOT).as_posix()
            for n, row in enumerate(self.csv(rel), 2):
                self.figures.append((rel, n, row))
        self.allowed = {p for p in self.meta['source_files'] if '/outputs_validation_' in p and p.endswith('.csv')}
        self.allowed |= {COVERAGE, RELATIONS}

    def csv(self, path):
        if path not in self.cache:
            p = ROOT / path
            if not p.exists():
                raise Missing(path)
            self.cache[path] = list(csv.DictReader(io.StringIO(p.read_text(encoding='utf-8-sig'))))
        return self.cache[path]

    def source(self, path, key, column):
        if path not in self.allowed:
            raise Missing('Path not in aggregate allowlist: ' + path)
        rows = [(n, r) for n, r in enumerate(self.csv(path), 2) if all(r.get(k) == str(v) for k, v in key.items())]
        if len(rows) != 1 or column not in rows[0][1]:
            raise Missing(f'{path}: nonunique/missing {key} {column}')
        n, row = rows[0]
        return {'path': path, 'cell': f'CSV row {n}, {column}', 'key': key,
                'precision': 'integer exact or unrounded binary64 round-trip decimal (generator evidence in metadata)', 'value': row[column]}

    def item(self, tid, metric=None, **key):
        self.used.add(tid)
        a = [i for i in self.items if i['table_id'] == tid and (metric is None or i['metric'] == metric)
             and all(i['source_key'].get(k) == v for k, v in key.items())]
        if len(a) != 1:
            raise Missing(f'{tid} {metric} {key}: {len(a)} mapped items')
        return a[0]

    def value(self, item, part=0):
        """Read actual export, actual Markdown cell, all corresponding figure CSVs."""
        tid = item['table_id']
        self.used.add(tid)
        role = ['estimate', 'interval_lower', 'interval_upper'][part]
        lines = [x for x in self.meta['cell_lineage'] if x.get('result_id') == item['result_id']
                 and x.get('document_cell_role') == role and x.get('lineage_type') == 'summary_csv_cell']
        sources = []
        for x in lines:
            sources.append(self.source(x['source_path'], x['row_selection_key'], x['column']))
        if not sources:
            col = item['source_column'] if part == 0 else item['interval_columns'][part-1]
            if not col:
                raise Missing(item['result_id'] + ' missing source column')
            sources.append(self.source(item['source_path'], item['source_key'], col))
        ix = int(item['result_id'].split('.r')[1])-1
        rows = self.tables.get(tid, [])
        if ix >= len(rows):
            raise Missing(item['result_id'] + ' results.md row missing')
        md = rows[ix]
        sources.append({'path': RESULTS, 'cell': f'{item["result_id"]} {role}', 'precision': 'source string preserved', 'value': md[2+part]})
        fcol = ['source_value_string', 'interval_lower_string', 'interval_upper_string'][part]
        for path, n, row in self.figures:
            if row.get('source_table_id') != tid or row.get('source_row_key') != md[0]:
                continue
            # Support count rows use a combined quantity and require separate handling.
            if row.get('quantity') not in (md[1], md[0]):
                continue
            if row.get(fcol, '') != '':
                sources.append({'path': path, 'cell': f'CSV row {n}, {fcol}', 'precision': 'source string preserved', 'value': row[fcol]})
        observed = [s['value'] for s in sources]
        mismatch = any(not equal(observed[0], x) for x in observed[1:])
        record = {'table_id': tid, 'result_id': item['result_id'], 'part': role, 'sources': sources, 'discrepancy': mismatch}
        self.evidence.append(record)
        if observed[0] == '':
            raise Missing(f'{tid} {item["source_key"]} {role} is blank')
        return D(observed[0])

    def v(self, tid, metric=None, part=0, **key):
        return self.value(self.item(tid, metric, **key), part)

    def triple(self, tid, metric=None, **key):
        item = self.item(tid, metric, **key)
        return [self.value(item, part) for part in range(3)]

    def check(self, cid, fn, expected=None, note='', log='', success='PASS', deps=()):
        start = len(self.evidence)
        blocked = next((d for d in deps if not any(c['id'] == d and c['status'] in GOOD for c in self.checks)), None)
        status, observed = 'PASS', None
        try:
            if blocked:
                status = 'BLOCKED BY ' + blocked
            else:
                ans = fn()
                if isinstance(ans, tuple) and len(ans) == 2 and isinstance(ans[0], bool):
                    ok, observed = ans
                    status = success if ok else ('DISCREPANCY' if cid.startswith('V9') else 'FAIL')
                else:
                    observed = ans
                    status = success
                if any(e['discrepancy'] for e in self.evidence[start:]):
                    status = 'DISCREPANCY'
        except Missing as e:
            status, observed = 'SOURCE MISSING', str(e)
        except Exception as e:
            # A programming defect is recorded, and must be fixed/committed before final publication.
            status, observed = 'NOT ESTABLISHED FROM EXPORTS', f'EXECUTION ERROR: {type(e).__name__}: {e}'
        c = {'id': cid, 'status': status, 'dependency': blocked, 'sources_consulted': self.evidence[start:],
             'expected': expected, 'observed': observed, 'notes': note, 'log_items': log}
        self.checks.append(c)
        return c

    def quote(self, log, tid, metric, expected, key=None, part=None, places=None):
        cid = f'V9.Q{len(self.claims)+1:03}'
        def run():
            observed = self.triple(tid, metric, **(key or {})) if isinstance(expected, list) else self.v(tid, metric, part=part or 0, **(key or {}))
            vals = observed if isinstance(observed, list) else [observed]
            exp = expected if isinstance(expected, list) else [expected]
            return all(equal(a,b,places) for a,b in zip(vals,exp)), observed
        c = self.check(cid, run, expected, f'{tid} {metric} {key or {}}', log)
        self.claims.append({'claim_id': cid, 'origin': 'v2 supplied checklist (governing log unavailable)', 'log_item': log,
                            'claim': f'{tid} {metric} {key or {}} part={part}: {expected}', 'mapped_check': cid,
                            'status': c['status'], 'reason': c['notes']})


def main_checks(a):
    # V1: scan every allowed canonical aggregate CSV, never replicate or record-level files.
    def covid_search():
        candidates, searched = [], []
        for path in sorted(a.allowed):
            searched.append(path)
            for n,row in enumerate(a.csv(path),2):
                if not any('COVID' in str(v) for v in row.values()):
                    continue
                if any(k in row for k in ('pair','tp','exact_match_n','agreement','discordant_n')):
                    tids = sorted({i['table_id'] for i in a.items if i['source_path']==path and all(row.get(k)==str(v) for k,v in i['source_key'].items())})
                    candidates.append({'path':path,'row':n,'table_ids':tids,'values':row})
        return {'searched':searched,'candidates':candidates,'conclusion':'No candidate supplies the required named-coder COVID identity comparison; majority diagnostics are not named-coder identity.'}
    a.check('V1.identity',covid_search,note='No inference from alpha equality.',log='1.6; S1.6',success='NOT ESTABLISHED FROM EXPORTS')
    for tid,components in [('S2T002',{'ABC':['0.9397477187332259','0.8355110514104286','1.0'],'LBC':['0.9397477187332259','0.8355110514104286','1.0'],'delta_A':['0','0','0'],'delta_min':['0','0','0']}),('S2T008',{'ABC':['0.8099547511312217'],'ABL':['0.8099547511312217'],'delta_C':['0','0','0'],'delta_min':['0','0','0']})]:
        for comp,expected in components.items():
            key = {'delta' if comp.startswith('delta') else 'panel':comp}
            def run(t=tid,k=key,e=expected):
                vals=[a.v(t,part=p,**k) for p in range(len(e))]
                return vals==list(map(D,e)),vals
            a.check(f'V1.context.{tid}.{comp}',run,expected,log='1.6; S1.6; G.6')
    for metric,e in [('tp',6),('fp',0),('fn',0),('human_majority_positive_n',6),('model_positive_n',6)]:
        a.check('V1.context.S2T018.'+metric,lambda m=metric,e=e:(a.v('S2T018',m)==e,a.v('S2T018',m)),e,log='S1.6')

    tids=['S3T001','S3T002','S2T001','S2T002','S3T011','S3T012','S3T007','S3T008','S2T007','S2T008']
    minima={}
    for tid in tids:
        def numerical(t=tid):
            vals={d:a.v(t,delta=d) for d in ['delta_A','delta_B','delta_C','delta_min']}
            low=min(vals[d] for d in ['delta_A','delta_B','delta_C'])
            matching=[d for d in ['delta_A','delta_B','delta_C'] if vals[d]==low]
            minima[t]=matching
            return vals['delta_min']==low,{'components':vals,'matching':matching}
        a.check('V2a.'+tid,numerical,'delta_min = minimum components',log='1.3; 2.3; S1.4')
        c=a.check('V2b.'+tid,lambda t=tid:(len(minima[t])==1,{'matching':minima[t]}),'unique minimum',log='1.3; 2.3; S1.4',success='ASSUMPTION HOLDS',deps=['V2a.'+tid])
        if c['status']=='FAIL':c['status']='ASSUMPTION DOES NOT HOLD'
        def intervals(t=tid):
            v={d:[a.v(t,part=p,delta=d) for p in (1,2)] for d in ['delta_min']+minima[t]}
            return all(v[d]==v['delta_min'] for d in minima[t]),v
        c=a.check('V2c.'+tid,intervals,'matching intervals',log='1.3; 2.3; S1.4',success='EQUAL',deps=['V2a.'+tid])
        if c['status']=='FAIL':c['status']='DIFFERENT'
    for left,right in [('S3T001','S3T011'),('S3T002','S3T012'),('S3T001','S3T007'),('S3T002','S3T008'),('S2T001','S2T007'),('S2T002','S2T008')]:
        c=a.check(f'V2b.paired.{left}.{right}',lambda l=left,r=right:(len(minima[l])==len(minima[r])==1 and minima[l]==minima[r],{l:minima[l],r:minima[r]}),'same unique minimum',log='2.3; S1.4',success='ASSUMPTION HOLDS',deps=['V2a.'+left,'V2a.'+right])
        if c['status']=='FAIL':c['status']='ASSUMPTION DOES NOT HOLD'
    for tid,comp in [('S3T001','delta_B'),('S3T002','delta_B'),('S3T011','delta_B'),('S3T012','delta_B'),('S2T001','delta_B'),('S2T002','delta_A')]:
        c=a.check('V2b.expected.'+tid,lambda t=tid,c=comp:(minima[t]==[c],minima[t]),comp,log='1.3; 2.3',success='ASSUMPTION HOLDS',deps=['V2a.'+tid])
        if c['status']=='FAIL':c['status']='ASSUMPTION DOES NOT HOLD'
    # Figure 2 only exports strict domain/purpose panels; report explicit scope gap for tags.
    for tag in ['equity','COVID']:
        a.check('V2.strict.'+tag,lambda:'No strict tag replacement table in source map or Figure 2 plotted rows.',note='No strict tag values substituted from baseline.',log='2.3',success='NOT ESTABLISHED FROM EXPORTS')

    labels={}
    for tid in ['S5T003','S5T004']:
        labels[tid]=list(dict.fromkeys(i['source_key']['label'] for i in a.items if i['table_id']==tid))
        for n,label in enumerate(labels[tid],1):
            def run(t=tid,l=label):
                vals={k:a.v(t,k,label=l) for k in ['human_majority_positive_n','model_positive_n','tp','fp','fn','tn']}
                ok=vals['tp']+vals['fn']==vals['human_majority_positive_n'] and vals['tp']+vals['fp']==vals['model_positive_n'] and sum(vals[k] for k in ['tp','fp','fn','tn'])==150
                return ok,{'label':l,**vals}
            a.check(f'V3.{tid}.{n}',run,'all six fields; count identities; total 150',label,'K.2; C.3')
    required={DOM:['Migration & Demographics','Crime & Justice','Environment & Agriculture','Public Finance & Taxation','Data Infrastructure & Methodology','Housing & Planning'],PUR:['Life-Course / Trajectory Analysis','Methodological / Infrastructure Research','Risk Prediction / Early Identification','Service Interaction / Systems Analysis']}
    for dim,tid in [(DOM,'S5T003'),(PUR,'S5T004')]:
        a.check('V3.sparse.'+tid,lambda d=dim,t=tid:(all(l in labels[t] and a.v(t,'human_majority_positive_n',label=l)<10 for l in required[d]),required[d]),required[dim],log='K.2; C.3')

    def precision():
        code=(ROOT/'analysis/scratch_coder_disagreement_types/generate.py').read_text(encoding='utf-8')
        return 'format(counts[relation] / nonempty, ".17g")' in code,{'path':'analysis/scratch_coder_disagreement_types/generate.py','lines':'326-327; 776-781','format':'.17g; binary64 round-trip precision, not exact rational precision'}
    a.check('V4.1',precision,'unrounded computed proportions',log='E.4; T5.2')
    for dim,fam,counts,den,pct in [(DOM,'human_human',[105,11,104],220,[48,5,47]),(DOM,'model_human',[103,16,80],199,[52,8,40]),(PUR,'human_human',[38,1,233],272,[14,0,86]),(PUR,'model_human',[40,4,226],270,[15,1,84])]:
        suffix=('domains' if dim==DOM else 'purposes')+'.'+fam
        def rel(col,relation,dim=dim,fam=fam):
            src=a.source(RELATIONS,{'population':'baseline','dimension':dim,'pair_family':fam,'relation':relation},col)
            sources=[src]
            for path,n,row in a.figures:
                if row.get('source_table_id')!='disagreement_type_distribution.csv' or row.get('dimension')!=dim or row.get('population')!='baseline':continue
                if row.get('source_row_key') not in (f'baseline|{dim}|{fam}|{relation}',f'{fam}:{relation}'):continue
                fc='source_value_string' if col=='count' else ('interval_lower_string' if col=='proportion_of_nonidentical_nonempty_pairs' and row.get('deliverable_id')=='Table 5' else None)
                if fc and row.get(fc):sources.append({'path':path,'cell':f'CSV row {n}, {fc}','precision':'source string','value':row[fc]})
            a.evidence.append({'sources':sources,'discrepancy':any(not equal(src['value'],s['value']) for s in sources[1:])})
            return D(src['value'])
        def counts_run(r=rel,e=counts,d=den):
            vals=[r('count',x) for x in ['containment','overlap','disjoint']]
            dens=[r('nonidentical_nonempty_pairs',x) for x in ['containment','overlap','disjoint']]
            return vals==e and dens==[d]*3,{'counts':vals,'denominators':dens}
        a.check('V4.2.'+suffix,counts_run,{'counts':counts,'denominator':den},log='E.4; T5.2')
        def percents(r=rel,e=pct):
            vals=[rnd(r('proportion_of_nonidentical_nonempty_pairs',x)*100) for x in ['containment','overlap','disjoint']]
            return vals==e and sum(vals)==100,{'percentages':vals,'sum':sum(vals)}
        a.check('V4.3.'+suffix,percents,pct,log='E.4; T5.2',deps=['V4.1'])
        def empties(r=rel):
            vals=[r('count','both_empty'),r('count','exactly_one_empty'),r('empty_set_involved_pairs','containment')]
            return vals==[0,0,0],vals
        a.check('V4.4.'+suffix,empties,[0,0,0],log='E.4; T5.2')
    def tags():
        rows=[r for r in a.csv(RELATIONS) if r['dimension'] not in (DOM,PUR) and r['population']=='baseline' and r['relation']=='exactly_one_empty']
        return len(rows)==2 and sorted((r['pair_family'],int(r['count']),int(r['nonidentical_nonempty_pairs'])) for r in rows)==[('human_human',30,7),('model_human',45,6)],{'path':RELATIONS,'rows':rows}
    a.check('V4.5',tags,{'human_human':[30,7],'model_human':[45,6]},log='findings log')

    for pop,dim,size,unc,no,two,three,sub,result,pct in [('baseline',PUR,123,26,24,3,0,100,97,[16,17,65,2,0]),('baseline',DOM,120,13,5,22,3,132,107,[3,9,71,15,2]),('hard_case',PUR,62,20,9,4,0,46,42,[12,27,56,5,0]),('hard_case',DOM,48,3,6,18,3,66,45,[8,4,60,24,4])]:
        suffix=pop+'.'+('domains' if dim==DOM else 'purposes')
        def cov(category,quantity,p=pop,d=dim):
            src=a.source(COVERAGE,{'population':p,'dimension':d,'quantity':quantity,'category':category},'count')
            a.evidence.append({'sources':[src],'discrepancy':False})
            return D(src['value'])
        a.check('V5.1.prerequisite.'+suffix,lambda c=cov:(c('unclear_present__substantive_present','unclear_composition')==0,c('unclear_present__substantive_present','unclear_composition')),0,log='G.12')
        def deriv(c=cov,s=size,u=unc,r=result):
            vals=[c('size_1','majority_set_size'),c('unclear_present__substantive_absent','unclear_composition')]
            return vals==[s,u] and vals[0]-vals[1]==r,{'operands':vals,'result':vals[0]-vals[1]}
        a.check('V5.1.'+suffix,deriv,result,log='G.12',deps=['V5.1.prerequisite.'+suffix])
        def full(c=cov,e=[no,two,three,0,sub]):
            vals=[c(k,'majority_set_size') for k in ['size_0','size_2','size_3','size_4_plus']]+[c('unclear_absent__substantive_present','unclear_composition')]
            return vals==e,vals
        a.check('V5.1.full.'+suffix,full,[no,two,three,0,sub],log='G.12')
        def percentages(c=cov,e=pct,p=pop,d=dim):
            src=a.source(COVERAGE,{'population':p,'dimension':d,'quantity':'majority_set_size','category':'size_1'},'denominator')
            a.evidence.append({'sources':[src],'discrepancy':False})
            n=D(src['value'])
            if n not in [D(150) if p=='baseline' else D(75)]:raise Missing('Unexpected denominator')
            u=c('unclear_present__substantive_absent','unclear_composition')
            counts=[c('size_0','majority_set_size'),u,c('size_1','majority_set_size')-u,c('size_2','majority_set_size'),c('size_3','majority_set_size')+c('size_4_plus','majority_set_size')]
            vals=[rnd(x/n*100) for x in counts]
            return vals==e and sum(vals)==100,{'counts':counts,'denominator':n,'percentages':vals,'sum':sum(vals)}
        a.check('V5.2.'+suffix,percentages,pct,log='G.12',deps=['V5.1.'+suffix,'V5.1.full.'+suffix])
    totals={}
    for tid,ct,dim,expected,unc,sub in [('S5T001','S5T003',DOM,[199,173],[1,13],[198,160]),('S5T002','S5T004',PUR,[160,129],[1,26],[159,103])]:
        def total(t=tid,c=ct,e=expected):
            vals=[sum(a.v(t,k,label=l) for l in labels[c]) for k in ['baseline_model_positive_n','baseline_human_majority_positive_n']]
            cross=[]
            for l in labels[c]:
                cross.append([l,a.v(t,'baseline_model_positive_n',label=l),a.v(c,'tp',label=l)+a.v(c,'fp',label=l),a.v(t,'baseline_human_majority_positive_n',label=l),a.v(c,'tp',label=l)+a.v(c,'fn',label=l)])
            totals[t]=vals
            return vals==e and all(x[1]==x[2] and x[3]==x[4] for x in cross),{'totals':vals,'all_label_crosschecks':cross}
        a.check('V5.3.'+tid,total,expected,log='G.12',deps=[f'V3.{ct}.{i}' for i in range(1,len(labels[ct])+1)])
        def substantive(t=tid,e=sub,u=unc):
            operands=[a.v(t,k,label=UNCLEAR) for k in ['baseline_model_positive_n','baseline_human_majority_positive_n']]
            vals=[v-w for v,w in zip(totals[t],operands)]
            return operands==u and vals==e,{'totals':totals[t],'unclear':operands,'results':vals}
        a.check('V5.4.'+tid,substantive,sub,log='G.12',deps=['V5.3.'+tid])

    for cid,ts,kind,lo,hi in [('V6.1',[t for t in tids if t not in ['S3T011','S3T012']],'panel','0','1'),('V6.2',tids,'delta','-0.45','0.45'),('V6.3',['S3T001','S3T002','S3T011','S3T012'],'panel','0','1')]:
        def bounds(ts=ts,k=kind,l=lo,h=hi):
            vals=[(a.value(i,1),a.value(i,2),i['result_id'],i['source_key']) for i in a.items if i['table_id'] in ts and k in i['source_key']]
            if not vals:raise Missing('No plotted interval rows')
            low=min(v[0] for v in vals); high=max(v[1] for v in vals)
            return low>=D(l) and high<=D(h),{'minimum_lower':low,'minimum_cells':[v for v in vals if v[0]==low],'maximum_upper':high,'maximum_cells':[v for v in vals if v[1]==high],'interval_count':len(vals)}
        c=a.check(cid,bounds,[lo,hi],note='V6.3 reports Figure 2 alpha extrema against [0,1]; no narrower range specified.' if cid=='V6.3' else '',log='G.1; G.6; 2.8',success='WITHIN RANGE')
        if c['status']=='FAIL':c['status']='OUTSIDE RANGE'

    for tid,ct in [('S5T001','S5T003'),('S5T002','S5T004')]:
        for n,label in enumerate(labels[ct],1):
            def band(t=tid,l=label):
                i=a.item(t,'baseline_human_majority_positive_n',label=l)
                count=a.value(i)
                src=a.source(i['source_path'],i['source_key'],'support_band')
                a.evidence.append({'sources':[src],'discrepancy':False})
                expected='STANDARD' if count>=30 else 'LOW SUPPORT' if count>=10 else 'RARE'
                return src['value']==expected,{'label':l,'count':count,'exported_band':src['value'],'expected_band':expected}
            a.check(f'V7.{tid}.{n}',band,'>=30 STANDARD; 10-29 LOW SUPPORT; <10 RARE',label,'P.2; C.2; D.1')
    for pair in ['A-B','L-C']:
        def signed(p=pair):
            val=a.v('S5T005','kappa',part=1,label=UNCLEAR,pair=p)
            typ='negative zero' if val.is_zero() and val.is_signed() else 'zero' if val.is_zero() else 'small negative number' if val<0 and rnd(val,3)==0 else 'negative number' if val<0 else 'positive number'
            return rnd(val,3)==D('-0.000'),{'value':val,'classification':typ,'three_decimal_display':str(rnd(val,3))}
        a.check('V8.1.'+pair,signed,'-0.000',log='G.14; P.3; P.4')
    for pair,expected in [('A-C','-0.07'),('B-C','-0.04')]:
        a.check('V8.2.Outcome.'+pair,lambda p=pair,e=expected:(rnd(a.v('S5T006','kappa',part=1,label='Outcome Tracking',pair=p),2)==D(e),a.v('S5T006','kappa',part=1,label='Outcome Tracking',pair=p)),expected,log='P.3; P.4')
    for pair in ['L-A','L-B','L-C']:
        a.check('V8.2.Unclear.'+pair,lambda p=pair:(a.v('S5T006','kappa',part=1,label=UNCLEAR,pair=p)==0,a.v('S5T006','kappa',part=1,label=UNCLEAR,pair=p)),0,log='P.3; P.4')
    for tid,valid,invalid,recall in [('S5T007','1284','716',['0.077','0.000','0.250']),('S5T008','1233','767',['0.038','0.000','0.125'])]:
        for metric in ['precision','f1']:
            def suppression(t=tid,m=metric,v=valid,iv=invalid):
                i=a.item(t,m,label=UNCLEAR)
                # Counts are read directly from aggregate export as well as interpreted metadata.
                row=next(r for r in a.csv(i['source_path']) if all(r.get(k)==str(x) for k,x in i['source_key'].items()))
                fields={k:row[k] for k in row if k.startswith(m+'_')}
                return i['interval_status']=='suppressed_valid_replicate_threshold' and str(i['valid_replicate_count'])==v and str(i['invalid_replicate_count'])==iv and i['requested_replicate_count']==2000 and '1800' in i['validity_threshold'] and row.get(m+'_ci_lower')==row.get(m+'_ci_upper')=='' and row.get(m+'_bootstrap_valid_n')==v and row.get(m+'_bootstrap_invalid_n')==iv,{'path':i['source_path'],'key':i['source_key'],'export_fields':fields,'metadata':{k:i[k] for k in ['interval_status','valid_replicate_count','invalid_replicate_count','requested_replicate_count','validity_threshold','policy_source']}}
            a.check(f'V8.3.{tid}.{metric}',suppression,[valid,invalid,2000,1800],log='C.4; D.2')
        a.check('V8.3.'+tid+'.recall',lambda t=tid,e=recall:(all(equal(x,y,3) for x,y in zip(a.triple(t,'recall',label=UNCLEAR),e)),a.triple(t,'recall',label=UNCLEAR)),recall,log='C.4; D.2')
    for tid in ['S5T005','S5T006','S5T007','S5T008']:
        a.check('V8.4.'+tid,lambda t=tid:(all(i['confidence_level']=='95%' for i in a.items if i['table_id']==t),[{'result_id':i['result_id'],'confidence_level':i['confidence_level'],'policy_source':i['policy_source']} for i in a.items if i['table_id']==t]),'95%',log='C.4; D.2; P.3; P.4')


def quoted_checks(a):
    a.check('V9.inventory',lambda:'Governing log not found in repository; no separate supplied copy in this conversation. Its complete quantitative inventory and hash cannot be established.',note='Checklist below is explicitly not exhaustive of the missing log.',success='SOURCE MISSING')
    specs=[('1.4','S2T001','delta_B',2,'0.004117088549351349',None),('1.4','S2T001','delta_min',2,'-0.006490658978949588',None),
      ('2.4','S3T002','delta_min',None,['-0.04266825138963548','-0.09028046253808193','-0.002141124278556386'],None),('2.4','S3T011','delta_min',None,['0.04169778425221149','0.0005992244570877603','0.07637533196699833'],None),
      ('S1.5','S2T007','delta_min',None,['-0.11455822957777184','-0.33012555322232656','0.0'],None),
      ('F.9','S3T002','ABC',None,['0.292','0.224','0.355'],3),('F.9','S3T012','ABC',None,['0.289','0.207','0.366'],3),
      ('S1.8','S3T001','ABC',0,'0.526',3),('S1.8','S3T007','ABC',0,'0.462',3),('S1.8','S3T008','ABC',0,'0.292',3),
      ('S1.8','S3T007','delta_min',None,['-0.027','-0.096','0.010'],3),('S1.8','S2T001','ABC',None,['0.512','0.300','0.691'],3),('S1.8','S2T007','ABC',None,['0.654','0.386','0.843'],3)]
    for log,tid,comps,values in [('F.7','S2T001',['delta_A','delta_B','delta_C','delta_min'],['-.044 -.181 .104','-.081 -.174 .004','-.060 -.189 .070','-.081 -.202 -.006']),('2.2','S3T011',['delta_A','delta_B','delta_C'],['.088 .039 .144','.042 .001 .083','.073 .023 .124']),('2.2','S3T012',['delta_A','delta_B','delta_C'],['.041 -.010 .096','.014 -.035 .068','.108 .051 .171']),('S1.8','S3T008',['delta_A','delta_B','delta_min'],['-.109 -.183 -.034','-.114 -.182 -.046','-.114 -.191 -.059'])]:
        specs.extend((log,tid,c,None,v.split(),3) for c,v in zip(comps,values))
    for log,tid,comp,part,expected,places in specs:
        a.quote(log,tid,None,expected,{'delta' if comp.startswith('delta') else 'panel':comp},part,places)
    c=a.check('V9.crosses_zero',lambda:(a.v('S3T008',part=1,delta='delta_C')<0<a.v('S3T008',part=2,delta='delta_C'),a.triple('S3T008',delta='delta_C')), 'lower < 0 < upper',log='S1.8')
    a.claims.append({'claim_id':c['id'],'origin':'v2 supplied checklist','log_item':'S1.8','claim':'S3T008 delta_C crosses zero','mapped_check':c['id'],'status':c['status'],'reason':''})
    for tid,log,values in [('S2T001','1.1',{'support':11}),('S2T002','1.1',{'support':12}),('S2T017','S1.3; O.1',{'human_majority_positive_n':8,'model_positive_n':8,'fp':3,'fn':3}),('S2T018','S1.3',{'human_majority_positive_n':6})]:
        for metric,e in values.items():
            if metric=='support':
                tag='Demographic disparities / equity' if tid=='S2T001' else 'COVID-19 & Pandemic'
                # Direct tag diagnostic table identifies the baseline majority count.
                match=next(i for i in a.items if i['source_name']=='tag_diagnostics' and i['population']=='baseline' and i['source_key'].get('tag')==tag)
                a.quote(log,match['table_id'],'human_majority_positive_n',str(e))
            else:a.quote(log,tid,metric,str(e))
    tag=next(i for i in a.items if i['source_name']=='tag_diagnostics' and i['population']=='baseline' and i['source_key'].get('tag')=='Demographic disparities / equity')
    for metric,e in [('model_positive_n',19),('human_majority_positive_n',11),('fp',13),('fn',5)]:a.quote('F.1',tag['table_id'],metric,str(e))
    for tid,ranges in [('S5T005',[['.150','.322'],['.037','.241']]),('S5T006',[['.236','.401'],['.016','.114']])]:
        for pairs,expected in zip([['A-B','A-C','B-C'],['L-A','L-B','L-C']],ranges):
            cid=f'V9.range.{tid}.{pairs[0]}'
            def run(t=tid,p=pairs,e=expected):
                vals=[a.v(t,'kappa',label=UNCLEAR,pair=x) for x in p]
                return [rnd(min(vals),3),rnd(max(vals),3)]==list(map(D,e)),{'pairs':p,'values':vals,'min':min(vals),'max':max(vals)}
            c=a.check(cid,run,expected,log='K.4; F.2')
            a.claims.append({'claim_id':cid,'origin':'v2 supplied checklist','log_item':'K.4; F.2','claim':f'{tid} Unclear {pairs} range {expected}','mapped_check':cid,'status':c['status'],'reason':''})
    for pair,vals in [('A-B','.355 .181 .520'),('A-C','.055 -.068 .207'),('B-C','.076 -.038 .211'),('L-C','.127 .017 .246')]:a.quote('F.5','S5T006','kappa',vals.split(),{'label':'Outcome Tracking','pair':pair},places=3)
    for label,e in [('Descriptive Monitoring','.554'),('Policy Evaluation / Impact Analysis','.615'),('Outcome Tracking','.474')]:a.quote('F.6','S5T006','kappa',e,{'label':label,'pair':'L-B'},places=3)
    for prefix,vals in [('Labour Market',{'tp':35,'fp':21,'fn':4}),('Environment & Agriculture',{'fp':6,'tp':4}),('Data Infrastructure',{'fp':4,'tp':0}),('Housing & Planning',{'fp':1,'tp':0}),('Poverty',{'fp':4,'fn':5}),('Migration & Demographics',{'fp':2,'fn':5})]:
        label=next(i['source_key']['label'] for i in a.items if i['table_id']=='S5T003' and i['source_key']['label'].startswith(prefix))
        for metric,e in vals.items():a.quote('F.14' if prefix.startswith('Migration') else 'F.13','S5T003',metric,str(e),{'label':label})
    for prefix,metric,expected in [('Labour Market','precision',['.625','.492','.750']),('Poverty','recall',['.545','.231','.857'])]:
        label=next(i['source_key']['label'] for i in a.items if i['table_id']=='S5T003' and i['source_key']['label'].startswith(prefix))
        # S5T003 is contingencies; performance intervals are S5T007.
        a.quote('F.13','S5T007',metric,expected,{'label':label},places=3)
    for prefix,fp,fn in [('Outcome Tracking',34,6),('Descriptive Monitoring',26,10),('Policy Evaluation',12,9),('Life-Course',8,6),('Methodological',5,2),('Service Interaction',3,0),('Risk Prediction',1,0)]:
        label=next(i['source_key']['label'] for i in a.items if i['table_id']=='S5T004' and i['source_key']['label'].startswith(prefix))
        for metric,e in [('fp',fp),('fn',fn)]:a.quote('F.14','S5T004',metric,str(e),{'label':label})
    a.quote('F.15','S5T004','model_positive_n','47',{'label':'Outcome Tracking'})
    a.quote('F.15','S5T008','precision',['.277','.152','.417'],{'label':'Outcome Tracking'},places=3)
    for tid,cats,counts in [('S8T001',['Sufficient','Partially sufficient','Insufficient'],[[107,39,4],[96,48,6],[59,89,2]]),('S9T001',['Fit','Partial Fit','No Fit','Cannot assess from register entry'],[[103,20,3,24],[133,7,1,9],[92,57,0,1]])]:
        for coder,values in zip(['C01','C02','C03'],counts):
            for cat,e in zip(cats,values):a.quote('T.6; F.4',tid,'count',str(e),{'coder':coder,'category':cat})
    a.quote('O.4','S8T003','count','92',{'category':'Sufficient'})
    a.quote('O.4','S8T003','proportion',['.613','.533','.688'],{'category':'Sufficient'},places=3)
    for subset,e in [('broad_register_usable',148),('strict_register_sufficient',92)]:a.quote('T.5','S8T005','count',str(e),{'subset':subset})
    # Current S1 Part A is the instructed expected source, not a regenerated table.
    rows=[]
    for line in (ROOT/S1).read_text(encoding='utf-8').split('## Part B')[0].splitlines():
        if line.startswith('| Sufficiency |') or line.startswith('| Taxonomy fit |'):
            rows.append([x.strip() for x in line.strip('|').split('|')])
    for response,pop,cat,count,*_ in rows:
        tid=('S8T' if response=='Sufficiency' else 'S9T')+('003' if pop=='Baseline' else '004')
        a.quote('T.2',tid,'count',count,{'category':cat})
    # Map all quantitative assertions checked in V1-V8 as supplied-instruction claims.
    for c in a.checks:
        if c['id'].startswith('V9') or c['expected'] is None:continue
        a.claims.append({'claim_id':'I.'+c['id'],'origin':'v2 sections V1-V8','log_item':c['log_items'],
                         'claim':f'{c["id"]}: {c["expected"]}', 'mapped_check':c['id'],'status':c['status'],'reason':c['notes']})
    a.claims.append({'claim_id':'REMAINDER','origin':'missing governing log','log_item':'all other log items',
                     'claim':'Additional quantitative claims cannot be enumerated without the governing log.',
                     'mapped_check':'','status':'NOT CHECKED','reason':'Log absent; no attached copy. Not counted as an enumerated quantitative claim.'})
    a.check('V9.remainder',lambda:'Unknown additional claims in missing log; cannot enumerate or map.',success='NOT CHECKED')


def provenance(path):
    p=ROOT/path
    return {'path':path,'exists':p.exists(),'last_commit':git('log','-1','--format=%H','--',path)[0],
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None}


def publish(a):
    tracked=git('ls-files')[0].splitlines()
    logs=[p for p in tracked if p.endswith('scratch_coder_figure_revisions_log_pass2.md')]
    metadata={'run_start_head':START_HEAD,'initial_git_status_porcelain':'','initial_git_warnings':['Git global ignore and .pytest_cache access denied; no porcelain entries'],
      'script_commit':git('log','-1','--format=%H','--','analysis/verification_pass2/verify_pass2.py')[0],
      'script_commit_history':git('log','--format=%H %s','--','analysis/verification_pass2/verify_pass2.py')[0].splitlines(),
      'run_timestamp_utc':datetime.now(timezone.utc).isoformat(),'software':{'python':sys.version,'platform':platform.platform(),'git':git('--version')[0]},
      'provenance':[provenance(p) for p in [RESULTS,META,S1,'analysis/tables/scratch_coder_supplementary_table_s1_majority_coverage.csv']],
      'governing_log':[provenance(p) for p in logs] or {'status':'SOURCE MISSING','repository_search':'git ls-files and rg --files --hidden filename search','supplied_copy':'none attached; cannot hash'},
      'figure_data_commit':git('log','-1','--format=%H','--','analysis/figure_data')[0],
      'ancestors':{h:{'exists':git('cat-file','-t',h)[1]==0,'ancestor_of_start':git('merge-base','--is-ancestor',h,START_HEAD)[1]==0} for h in ['960c38d','6cbf154']},
      'source_precision':{'canonical_stage_a':'csv.DictWriter without rounding: analysis/scratch_coder_stage_a/report.py:104-111; Python float string round-trip precision, integers exact',
         'canonical_stage_b':'DataFrame.to_csv without float_format: analysis/scratch_coder_stage_b/report.py:9; unrounded binary64 serialization, integers exact',
         'results.md':'Source precision preserved per results.md status legend; actual cells compared to canonical source using Decimal',
         'figure_data':'source_value_string and interval_*_string copied unchanged; extract_scratch_coder_paper.py:179-221,648-670; parsed float columns are not treated as primary source strings',
         'Table5':'generate.py:326-327 .17g; 17 significant digits preserve binary64 round-trip precision',
         'current_S1':'Counts exact; displayed proportions and intervals three decimal places'},
      'judgement_calls':['No governing log or separate supplied copy found; inventory explicitly limited to claims in v2, with unknown remainder NOT CHECKED.',
         'Use metadata result_items and cell_lineage only as locators, read actual aggregate CSVs and actual results.md cells; do not import analysis code.',
         'Compare all matching scratch_coder figure-data generations separately by table ID, row key and quantity.',
         'Full precision means unrounded exported binary64 round-trip precision, not exact rational arithmetic.',
         'Map Figure S1 to existing baseline/hard-case exports despite their historical Figure 4/6 filenames.',
         'Figure 2 only supplies strict domain/purpose rows; strict equity/COVID scope gaps receive non-pass statuses.',
         'V6.3 reports alpha extrema and uses [0,1] for range status because no narrower numerical range is specified.',
         'F.13 precision/recall intervals map to S5T007; the instructed S5T003 supplies contingencies only.',
         'An interval or tuple is one inventory claim; repeated V1-V8 assertions remain separately traceable. Unknown remainder is not counted as a claim.',
         'Every non-PASS status is listed for review, including neutral EQUAL, WITHIN RANGE and ASSUMPTION HOLDS classifications.'],
      'source_mapping':[{'table_id':t,'canonical':[s for x in a.meta['source_map'] if x['table_id']==t for s in x['sources']],
          'figure_data':sorted({p for p,n,r in a.figures if r.get('source_table_id')==t}),
          'gap':not any(r.get('source_table_id')==t for p,n,r in a.figures)} for t in sorted(a.used)],
      'aggregate_files_read':sorted(a.cache)}
    real=[c for c in a.claims if c['claim_id']!='REMAINDER']
    metadata['inventory_counts']={'enumerated_supplied_instruction_claims':len(real),'mapped':sum(bool(c['mapped_check']) for c in real),
      'passed':sum(c['status'] in GOOD for c in real),'not_passed':sum(c['status'] not in GOOD and c['status']!='NOT CHECKED' for c in real),
      'not_checked_enumerated':sum(c['status']=='NOT CHECKED' for c in real),'unquantifiable_remainder_rows':1,'complete_governing_log_count':'unknown'}
    data={'metadata':metadata,'checks':a.checks}
    (OUT/'verification_checks.json').write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    with (OUT/'claims_inventory.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['claim_id','origin','log_item','claim','mapped_check','status','reason']);writer.writeheader();writer.writerows(a.claims)
    lines=['# Pass-2 read-only verification report','','This report and its companion JSON/CSV come from one complete execution of the committed script. No statistical metrics or intervals were recomputed. The governing log is missing; its exhaustive claim inventory is not established.','','## Step A, provenance, precision and judgement calls','','```json',json.dumps(metadata,indent=2,ensure_ascii=False,default=str),'```','','## All checks and sub-checks','','| Check | Status | Log items | Note / observed summary |','| --- | --- | --- | --- |']
    for c in a.checks:
        summary=json.dumps(c['observed'],ensure_ascii=False,default=str)
        lines.append('| '+ ' | '.join([c['id'],c['status'],c['log_items'],(c['notes']+' '+summary[:600]).replace('|','\\|').replace('\n',' ')])+' |')
    lines+=['','## Decisions needed / non-PASS register','','Neutral statuses are retained here because the instruction requests every non-PASS status. No figure or table remedy is selected.']
    for c in a.checks:
        if c['status']=='PASS':continue
        lines+=['',f'### {c["id"]} — {c["status"]}',f'Log: {c["log_items"] or "not specified"}. {c["notes"]}', '', '```json',json.dumps({'expected':c['expected'],'observed':c['observed'],'dependency':c['dependency']},indent=2,ensure_ascii=False,default=str),'```']
    lines+=['','## Complete cell evidence','','Every check below records all consulted cell strings, paths and precision. Source gaps are not filled with invented values.']
    for c in a.checks:
        lines+=['',f'### {c["id"]}','','```json',json.dumps(c,indent=2,ensure_ascii=False,default=str),'```']
    (OUT/'verification_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status_counts':dict(Counter(c['status'] for c in a.checks)),'inventory':metadata['inventory_counts'],
                      'execution_errors':[c['id'] for c in a.checks if 'EXECUTION ERROR' in str(c['observed'])]},indent=2))


def self_test():
    assert equal('0.10000000000000001','0.1') is False
    assert rnd('0.125',2)==D('.13') and rnd('-.125',2)==D('-.13')
    assert equal('0.8099547511312217','.810',3)
    assert str(rnd('-0.0000000000000003',3))=='-0.000'
    assert D('-0').is_zero() and D('-0').is_signed()
    assert [k for k,v in {'A':D(0),'B':D(0),'C':D(1)}.items() if v==0]==['A','B']
    assert rnd((D(123)-D(26))/D(150)*100)==65
    tables=parse_md('### S2T001 — synthetic\n\n| Row / comparator | Quantity | Estimate / count / flag | Interval lower | Interval upper |\n| --- | --- | --- | --- | --- |\n| alpha ABC | `point_estimate` | 0.123 | -0.0 | 1.0 |')
    assert tables['S2T001'][0][2:] == ['0.123','-0.0','1.0']
    # Dependency propagation uses synthetic in-memory checks only.
    a=Audit.__new__(Audit);a.evidence=[];a.checks=[]
    a.check('A',lambda:(_ for _ in ()).throw(Missing('synthetic')))
    a.check('B',lambda:True,deps=['A'])
    assert a.checks[-1]['status']=='BLOCKED BY A'
    print('Synthetic-only tests passed (rounding, exactness, signed zeros, ties, derivation, parsing, dependency propagation).')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:self_test()
    else:
        if not (ROOT/RESULTS).exists():raise SystemExit('Hard stop: results.md missing')
        dirty=git('status','--porcelain')[0].splitlines()
        if any('analysis/verification_pass2/' not in line for line in dirty):raise SystemExit('Hard stop: unrelated working-tree changes')
        if git('diff','HEAD','--','analysis/verification_pass2/verify_pass2.py')[0]:raise SystemExit('Commit script fixes before running')
        audit=Audit();main_checks(audit);quoted_checks(audit);publish(audit)
