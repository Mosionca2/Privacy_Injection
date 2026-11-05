"""Verify judge-only recorded outputs separately from the original victim-answer ledger."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from privacy_study import core as c
from judge_injection import core as j
from tools.validate_source_recorder import check_input_capture
from tools.verify_evidence import require,local_file

def verify(root=ROOT,allow_partial=False):
 root=Path(root);captures=[];total=0
 for out in sorted((root/'evidence/judge-injection-v1').glob('*/*/*')):
  if not (out/'run/run.json').exists():continue
  cond=c.read_json(out/'condition.json');run=c.read_json(out/'run/run.json')
  require(run['status']=='completed' and run['exit_code']==0 and run['schema_version']==2,'Unsuccessful judge capture.')
  check_input_capture(run,[])
  for item in [run['manifest'],run['lock'],*run['files']]:
   require(item['sha256']=='sha256:'+c.digest(local_file(out/'run',item['snapshot'])),'Judge input snapshot hash mismatch.')
  manifest=c.read_json(out/'run'/run['manifest']['snapshot'])
  require(manifest['experiment']['profiles']==['judge_only'] and 'primary' not in manifest['models'] and 'judge' in manifest['models'],'Wrong judge-only model roles.')
  for field,value in [('evaluation.judge.params.max_tokens',16),('evaluation.judge.params.temperature',0),('evaluation.judge.repetitions',3 if cond['phase']=='repeat' else 1)]:
   require(bool(run['bindings_observed'][field]) and all(v['value']==value for v in run['bindings_observed'][field]),'Judge binding contradiction.')
  raw=(out/'judge-predictions.jsonl').read_bytes();docs=[json.loads(x) for x in raw.splitlines()];identity=docs[0]['identity'];rows=docs[1:]
  artifacts={v['path']:v['sha256'] for v in run['artifacts']}
  require(artifacts['raw/judge-predictions.jsonl']=='sha256:'+c.digest(out/'judge-predictions.jsonl') and artifacts['raw/completion.json']=='sha256:'+c.digest(out/'completion.json'),'Judge output artifact mismatch.')
  dataset=root/'studies/judge-injection-v1/inputs'/(cond['model']+'-'+('test' if cond['phase']=='test' else 'dev')+'.jsonl')
  inputs=[json.loads(x) for x in dataset.read_text().splitlines()]
  if cond['phase'] in ('pilot','repeat'):
   ids=sorted({r['case_id'] for r in inputs})[:8]
   inputs=[r for r in inputs if r['case_id'] in ids and (r['view']=='clean' or (r['view']=='attack' and r['family']=='override' and r['position']=='suffix'))]
  encoded=''.join(json.dumps(r,sort_keys=True)+'\n' for r in inputs)
  require(j.digest_text(encoded)==identity['input_sha256'],'Judge dataset identity mismatch.')
  reps=3 if cond['phase']=='repeat' else 1;expected={r['id']+':'+str(k):(r,k) for r in inputs for k in range(reps)}
  require(len(rows)==len(expected)==cond['expected'] and {r['id'] for r in rows}==set(expected),'Judge response coverage mismatch.')
  for row in rows:
   original,rep=expected[row['id']]
   require(row['scores']==j.score(original['target'],row['output'],original['gold']) and row['gold']==original['gold'] and row['reprollm_run_id']==run['run_id'],'Judge gold, score or run ownership mismatch.')
   require(all(row[k]==original[k] for k in ('case_id','task','view','family','position')),'Judge metadata mismatch.')
   require(0<row['input_tokens']<=1024 and 0<row['output_tokens']<=16,'Recorded token budget mismatch.')
   require(not row['hit_output_cap'] or not row['scores']['valid'],'Truncated output accepted as valid.')
  if cond['phase'] in ('dev','test'):
   pairs={}
   for r in rows:
    if r['view']!='clean':pairs.setdefault((r['case_id'],r['gold'],r['family'],r['position']),{})[r['view']]=r['input_tokens']
   require(all(set(v)=={'attack','neutral'} and v['attack']==v['neutral'] for v in pairs.values()),'Attack/neutral token lengths differ.')
  complete=c.read_json(out/'completion.json');require(complete['new_judge_outputs']==len(rows) and complete['reprollm_run_id']==run['run_id'],'Judge completion mismatch.')
  require(run['run_id'] in (out/'REPRODUCIBILITY.md').read_text(),'Selected judge export mismatch.')
  require(identity['guard']==cond['guard'] and identity['max_tokens']==16 and identity['repetitions']==reps,'Judge identity contradicts condition.')
  require(all(r['repeat_index']==expected[r['id']][1] for r in rows),'Repeat ownership mismatch.')
  require(run['reprollm_version']=='0.7.0','Unexpected source recorder version.')
  witness=c.read_json(out/'runtime-witness.json');document=c.read_json(out/'recorder-source.json')
  require(witness['module_version']==document['module_version']=='0.7.0' and witness['module_sha256']==next(v['sha256'] for v in document['files'] if v['name']=='reprollm/__init__.py'),'Wrong witnessed recorder source.')
  if cond['phase']=='test':
   for template in ('acl','neurips'):
    require(run['run_id'] in (out/('REPRODUCIBILITY-'+template+'.md')).read_text(),'Conference export selected wrong run.')
  captures.append(dict(model=cond['model'],phase=cond['phase'],guard=cond['guard'],run_id=run['run_id'],judge_outputs=len(rows)));total+=len(rows)
 if not allow_partial:
  require(total==12928 and len(captures)==14,'Judge campaign is incomplete.')
  require({(v['model'],v['phase'],v['guard']) for v in captures}=={(m,p,g) for m in ('primary','extension') for p in ('pilot','dev','test','repeat') for g in (('J1',) if p=='pilot' else ('J0','J1'))},'Missing or duplicate judge condition.')
  frozen=c.read_json(root/'studies/judge-injection-v1/protocol.freeze.json')
  for name,digest in frozen['files'].items():require(c.digest(local_file(root,name))==digest,'Formal judge study changed after freeze.')
 return dict(schema_version=1,all_passed=True,judge_outputs=total,gpu_captures=len(captures),records=captures,new_victim_generations=0)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--allow-partial',action='store_true');a=p.parse_args();print(json.dumps(verify(allow_partial=a.allow_partial),indent=2))
