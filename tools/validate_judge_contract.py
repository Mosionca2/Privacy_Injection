"""Actual CLI checks for the scoped judge-only exception and judge-parameter drift.

No inference is performed here; GPU runs and their judge outputs have their own ledger.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from privacy_study import core as c
from tools.ci_verify import SOURCE_IDENTITY,check_consumer,directory_hashes
from tools.validate_source_recorder import runtime_env,verify_payload,recorder_witness
from tools.verify_evidence import require


def validate(source,workspace,published):
 source=Path(source).resolve();workspace=Path(workspace).resolve();published=Path(published).resolve()
 document=c.read_json(ROOT/SOURCE_IDENTITY);check_consumer(source,document)
 require(not workspace.exists(),'Choose a fresh CPU validation workspace.')
 source_run=ROOT/'evidence/judge-injection-v1/primary/pilot/J1/run'
 record=c.read_json(source_run/'run.json');base=c.read_json(source_run/record['manifest']['snapshot'])
 results=[];calls=[]
 def call(work,label,args,expected=0):
  env=dict(runtime_env(True),NO_COLOR='1',TERM='dumb')
  result=subprocess.run([str(Path(sys.executable).with_name('reprollm')),*args],cwd=work,env=env,capture_output=True,text=True,timeout=180)
  (work/'raw'/(label+'.stdout')).write_text(result.stdout.rstrip()+'\n');(work/'raw'/(label+'.stderr')).write_text(result.stderr.rstrip()+'\n')
  require(result.returncode==expected,label+': unexpected CLI exit; inspect private logs.')
  calls.append(dict(scenario=work.name,label=label,exit_code=result.returncode,args=args))
  return result.stdout
 for scenario in ('judge_only','with_privacy','with_inference','user_override','missing_temperature','missing_judge_model','missing_judge_prompt'):
  work=workspace/scenario;work.mkdir(parents=True);(work/'raw').mkdir()
  for item in document['files']:
   path=work/'assets/recorder-source'/item['name'];path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/'src'/item['name'],path)
  verify_payload(work,document);c.write_json(work/'raw/runtime-witness.json',recorder_witness(work,document,True,runtime_env(True)))
  call(work,'init',['init','.','--profiles','judge_only'])
  manifest=copy.deepcopy(base)
  manifest['project']['name']='audit_only_synthetic_judge_contract'
  asset=work/'assets/audit-only-model';asset.mkdir();(asset/'config.json').write_text('{\"fixture\": true}\n')
  manifest['models']['judge']['id']='assets/audit-only-model'
  manifest['models']['judge']['tokenizer']['id']='assets/audit-only-model'
  # These are audit-only fixture declarations, never a replacement GPU run.
  if scenario=='with_privacy':manifest['experiment']['profiles'].append('privacy')
  if scenario=='with_inference':manifest['experiment']['profiles'].append('inference')
  if scenario=='user_override':
   target=work/'.reprollm/profiles/judge_only.yaml';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/'src/reprollm/profiles/judge_only.yaml',target)
  if scenario=='missing_temperature':del manifest['evaluation']['judge']['params']['temperature']
  if scenario=='missing_judge_model':manifest['models']['judge']={}
  if scenario=='missing_judge_prompt':manifest['prompts']['judge']={}
  # Materialize only portable research declarations, not machine configuration.
  for name in ('judge_injection/core.py','judge_injection/run.py','privacy_study/core.py','requirements.txt'):
   target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
  (work/'prompts').mkdir();(work/'prompts/judge.txt').write_text('Return exactly LEAK or NO_LEAK.\n')
  (work/'data').mkdir();shutil.copyfile(ROOT/'studies/judge-injection-v1/inputs/primary-dev.jsonl',work/'data/inputs.jsonl')
  manifest['execution']['config_files']=['requirements.txt','judge_injection/core.py','judge_injection/run.py','privacy_study/core.py']
  c.write_json(work/'reprollm.yaml',manifest)
  call(work,'lock',['lock','.','--offline']);call(work,'check-lock',['lock','.','--check'])
  audit=json.loads(call(work,'audit',['audit','.','--level','1','--format','json','--fail-on','never']))
  findings={v['rule_id']:v for v in audit['findings']}
  primary=findings['model.primary_declared'];skip=scenario not in ('with_inference','user_override')
  require(primary['status']==('skipped' if skip else 'fail'),'Primary-role exception scope changed.')
  if scenario=='missing_temperature':require(findings['judge.params_declared']['status']=='fail','Missing judge parameter was accepted.')
  if scenario=='missing_judge_model':require(findings['judge.model_declared']['status']=='fail','Missing judge model was accepted.')
  if scenario=='missing_judge_prompt':require(findings['judge.prompt_declared']['status']=='fail','Missing judge prompt was accepted.')
  if scenario in ('judge_only','with_privacy'):
   for rule in ('judge.model_declared','judge.prompt_declared','judge.params_declared','judge.repetitions_declared'):
    require(findings[rule]['status']=='pass','Valid judge declaration failed: '+rule)
  out=published/scenario;out.mkdir(parents=True,exist_ok=True)
  c.write_json(out/'audit.json',audit);c.write_json(out/'manifest.json',manifest);shutil.copyfile(work/'raw/runtime-witness.json',out/'runtime-witness.json')
  results.append(dict(scenario=scenario,primary_status=primary['status'],findings={key:findings[key]['status'] for key in ('judge.model_declared','judge.prompt_declared','judge.params_declared','judge.repetitions_declared')}))
 # Real completed J0/J1 GPU run diff; historical records remain untouched.
 diffwork=workspace/'judge_only'
 left=ROOT/'evidence/judge-injection-v1/primary/dev/J0/run/run.json';right=ROOT/'evidence/judge-injection-v1/primary/dev/J1/run/run.json'
 if left.exists() and right.exists():
  before={str(p):directory_hashes(p.parent) for p in (left,right)}
  # Relative inputs keep command evidence portable after copying.
  for label,path in [('left',left),('right',right)]:shutil.copytree(path.parent,diffwork/'history'/label)
  raw=json.loads(call(diffwork,'actual-guard-diff',['diff','history/left/run.json','history/right/run.json','--format','json']))
  c.write_json(published/'actual-guard-diff.json',raw)
  require(before=={str(p):directory_hashes(p.parent) for p in (left,right)},'Diff changed historical records.')
 # Controlled manifest/lock copies test parameter drift without fabricating a model run.
 baseline=c.read_json(diffwork/'reprollm.yaml');shutil.copyfile(diffwork/'reprollm.lock',diffwork/'before.lock')
 baseline['evaluation']['judge']['params']['max_tokens']=17;c.write_json(diffwork/'reprollm.yaml',baseline)
 call(diffwork,'changed-lock',['lock','.','--offline'])
 diff=json.loads(call(diffwork,'parameter-diff',['diff','before.lock','reprollm.lock','--format','json','--fail-on','HIGH'],expected=1))
 require(any(v['path']=='evaluation.judge.params.max_tokens' and v['severity']=='HIGH' for v in diff['changes']),'Judge parameter drift was not HIGH.')
 c.write_json(published/'parameter-diff.json',diff);c.write_json(published/'recorder-source.json',document)
 result=dict(schema_version=1,all_passed=True,source_commit=document['source_commit'],scenarios=results,commands=calls,cli_commands=len(calls),new_judge_outputs=0,new_victim_generations=0)
 c.write_json(published/'validation.json',result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--consumer-source',required=True);p.add_argument('--workspace',required=True);p.add_argument('--published',required=True);a=p.parse_args()
 print(json.dumps(validate(a.consumer_source,a.workspace,a.published),indent=2))
