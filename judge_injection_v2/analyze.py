"""Paired base-case inference for the controlled judge experiment (standard library)."""
import collections
import json
from pathlib import Path
import random
import statistics
from privacy_study import core as c

SEED=20261106

def rate(values):
 values=list(values)
 return sum(values)/len(values) if values else None

def quantile(values,p):
 values=sorted(values);x=(len(values)-1)*p;k=int(x)
 return values[k]+(values[min(k+1,len(values)-1)]-values[k])*(x-k)

def clustered(values,resamples=10000):
 """Resample the entire paired base-case difference, never individual views."""
 if not values:raise ValueError('Empty cluster collection.')
 values=list(values);observed=statistics.mean(values);n=len(values);rng=random.Random(SEED)
 boot=[sum(rng.choices(values,k=n))/n for _ in range(resamples)]
 extreme=sum(abs(sum(v*rng.choice((-1,1)) for v in values)/n)>=abs(observed)-1e-14 for _ in range(resamples))
 return dict(base_cases=n,estimate=observed,bootstrap_95=[quantile(boot,.025),quantile(boot,.975)],
             sign_flip_p=(extreme+1)/(resamples+1),resamples=resamples,seed=SEED)

def holm(pvalues):
 ordered=sorted(pvalues,key=pvalues.get);adjusted={};previous=0
 for i,key in enumerate(ordered):
  previous=max(previous,min(1,pvalues[key]*(len(ordered)-i)));adjusted[key]=previous
 return adjusted

def summarize(rows):
 leak=[r for r in rows if r['gold']=='LEAK'];safe=[r for r in rows if r['gold']=='NO_LEAK']
 return dict(n=len(rows),leak_denominator=len(leak),safe_denominator=len(safe),
  false_safe=rate(r['scores']['false_safe'] for r in leak),false_alarm=rate(r['scores']['false_alarm'] for r in safe),
  accuracy=rate(r['scores']['correct'] for r in rows),invalid=rate(not r['scores']['valid'] for r in rows),
  private_echo=rate(r['scores']['private_echo'] for r in rows))

def paired(rows,clean_correct_only=False):
 clean={ (r['case_id'],r['gold']):r for r in rows if r['view']=='clean'}
 cells=collections.defaultdict(dict)
 for r in rows:
  if r['gold']!='LEAK' or r['view']=='clean':continue
  if clean_correct_only and not clean[(r['case_id'],r['gold'])]['scores']['correct']:continue
  cells[(r['case_id'],r['family'],r['position'])][r['view']]=int(r['scores']['false_safe'])
 clusters=collections.defaultdict(list)
 for (case,family,position),cell in cells.items():
  if set(cell)!= {'attack','neutral'}:raise ValueError('Unpaired judge comparison.')
  clusters[case].append(cell['attack']-cell['neutral'])
 if any(len(v)!=6 for v in clusters.values()):raise ValueError('Incomplete case cluster.')
 return {k:statistics.mean(v) for k,v in sorted(clusters.items())}

def analyze(root):
 root=Path(root);conditions=[];probes=[]
 for out in sorted((root/'evidence/judge-injection-v2').glob('*/*/*')):
  if not (out/'completion.json').exists():continue
  cond=c.read_json(out/'condition.json');rows=[json.loads(x) for x in (out/'judge-predictions.jsonl').read_text().splitlines()][1:]
  if cond['phase']=='test':
   complete=c.read_json(out/'completion.json')
   item=dict(model=cond['model'],guard=cond['guard'],by_view={v:summarize([r for r in rows if r['view']==v]) for v in ('clean','attack','neutral')},
    attack_minus_neutral=clustered(paired(rows).values()),
    by_family_position={f+':'+p:{v:summarize([r for r in rows if r['family']==f and r['position']==p and r['view']==v]) for v in ('attack','neutral')} for f in ('override','role_spoof','evaluation_calibration') for p in ('prefix','suffix')},
    performance=dict(inference_seconds=complete['seconds'],peak_reserved_gib=complete['peak_reserved_gib'],output_tokens=sum(r['output_tokens'] for r in rows),
                     output_tokens_per_second=sum(r['output_tokens'] for r in rows)/complete['seconds'],hit_output_cap=sum(r['hit_output_cap'] for r in rows)))
   subset=paired(rows,True);item['clean_correct_leak_subset']=dict(base_cases=len(subset),attack_minus_neutral=rate(subset.values()))
   conditions.append(item)
  elif cond['phase']=='repeat':
   groups=collections.defaultdict(list)
   for r in rows:groups[r['id'].rsplit(':',1)[0]].append(r)
   if any(len(v)!=3 or {r['repeat_index'] for r in v}!={0,1,2} for v in groups.values()):raise ValueError('Incomplete fresh repeat.')
   probes.append(dict(model=cond['model'],guard=cond['guard'],fresh_outputs=len(rows),groups=len(groups),
    text_disagreements=sum(len({r['output'] for r in v})>1 for v in groups.values()),
    label_disagreements=sum(len({r['scores']['label'] for r in v})>1 for v in groups.values())))
 if len(conditions)!=4 or len(probes)!=4:raise ValueError('Formal experiment or repeat probe is incomplete.')
 adjusted=holm({r['model']:r['attack_minus_neutral']['sign_flip_p'] for r in conditions if r['guard']=='J1'})
 for r in conditions:
  if r['guard']=='J1':r['attack_minus_neutral']['holm_adjusted_p']=adjusted[r['model']]
 return dict(schema_version=1,study='judge-injection-v2',scope='Exact synthetic target inclusion in controlled stored answers; judge outputs only.',
  statistical_unit='Base case; retain paired views and gold classes. Primary inference uses the LEAK member; NO_LEAK supplies false-alarm and accuracy diagnostics.',
  inference='10000 paired cluster bootstrap resamples and two-sided cluster sign flips. Holm correction over the two confirmatory J1 models only. J0 and family/position results are secondary.',
  conditions=conditions,repeat_probes=probes)

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--output',required=True);a=p.parse_args();c.write_json(a.output,analyze(a.root))
