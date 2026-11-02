"""Bounded CPU fixture checks for ReproLLM; these are not model experiments."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacy_study import core as c
from privacy_study.record import command


def verify(work,output):
    work=Path(work).resolve(); work.mkdir(parents=True,exist_ok=False)
    cli=Path(sys.executable).with_name('reprollm'); checks=[]
    c.write_json(work/'assets/model/config.json',{'model_type':'synthetic_tool_fixture','version':1})
    (work/'assets/model/fixture.bin').write_bytes(b'not-a-model; tool-lock-fixture')
    manifest=dict(schema_version=1,project={'name':'ReproLLM_fixture_validation'},
        experiment={'name':'cpu-contract-checks','profiles':['inference']},
        models={'primary':{'provider':'local','id':'assets/model','dtype':'float16'}},
        custom={'defense':'D0'},bindings={'custom.defense':{'cli':'--defense'}})
    c.write_json(work/'reprollm.yaml',manifest)
    command([cli,'rules','add','--id','project.defense','--field','custom.defense','--severity','CRITICAL',
             '--reason','A defense contradiction must be reported.','--cli=--defense'],work)
    command([cli,'lock','.','--offline'],work)
    lock_before=c.digest(work/'reprollm.lock')
    command([cli,'lock','.','--check'],work)
    checks.append({'check':'offline_lock_fresh','passed':True})
    config=work/'assets/model/config.json'; original=config.read_bytes()
    c.write_json(config,{'model_type':'synthetic_tool_fixture','version':2})
    changed=command([cli,'lock','.','--check'],work,allowed=(0,))
    assert c.digest(work/'reprollm.lock')==lock_before
    config.write_bytes(original)
    command([cli,'lock','.','--check'],work)
    checks.append({'check':'local_asset_rehash_outside_lock_check_contract','passed':True,'observed_exit_code':changed.returncode,
                   'limitation':'lock --check compares manifest and project rules only; it does not rehash referenced local model content.'})
    manifest['custom']['defense']='D1'; c.write_json(work/'reprollm.yaml',manifest)
    changed=command([cli,'lock','.','--check'],work,allowed=(1,))
    manifest['custom']['defense']='D0'; c.write_json(work/'reprollm.yaml',manifest)
    command([cli,'lock','.','--check'],work)
    checks.append({'check':'manifest_drift_detected_without_rewriting_lock','passed':True,'exit_code':changed.returncode})
    clean_env={key:os.environ[key] for key in ('PATH','LANG','LC_ALL') if key in os.environ}
    canary='hf_'+'A'*40
    clean_env['HF_TOKEN']=canary
    clean_env['EXPERIMENT_PASSWORD']='synthetic-secret-for-validation'
    def recorded(code,defense='D0',allowed=(0,)):
        before=set((work/'.reprollm/runs').glob('*'))
        result=command([cli,'run','--capture-output','--env-capture','all','--',sys.executable,'-c',code,'--defense',defense],
                       work,allowed=allowed,env=clean_env)
        new=set((work/'.reprollm/runs').glob('*'))-before
        run=next(p for p in new if p.is_dir())
        return result,run,c.read_json(run/'run.json')
    result,first,first_record=recorded('import os; print(os.environ["HF_TOKEN"])')
    saved='\n'.join(p.read_text() for p in first.rglob('*') if p.is_file())
    assert canary not in saved and 'synthetic-secret-for-validation' not in saved
    assert first_record['environment']['env']['HF_TOKEN']=={'present':True}
    checks.append({'check':'synthetic_credentials_absent_from_owned_persistence','passed':True,'run_id':first.name})
    _r,conflict,_record=recorded('print("intentional binding mismatch")','D3')
    audit=command([cli,'audit','.','--format','json','--fail-on','never'],work)
    findings=json.loads(audit.stdout)['findings']
    matched=[f for f in findings if f.get('rule_id')=='consistency.custom_fields' and f.get('status')=='fail' and any(e.get('field')=='custom.defense' for e in f.get('evidence',[]))]
    assert matched and any(f.get('severity')=='CRITICAL' for f in matched)
    checks.append({'check':'custom_defense_contradiction_is_critical','passed':True,'run_id':conflict.name})
    result,failed,record=recorded('raise SystemExit(7)',allowed=(7,))
    assert record['status']=='completed' and record['exit_code']==7
    checks.append({'check':'nonzero_child_exit_preserved','passed':True,'exit_code':result.returncode,'run_id':failed.name})
    before=set((work/'.reprollm/runs').glob('*'))
    result=command([cli,'run','--','reprollm-validation-command-does-not-exist'],work,allowed=(1,2,3,127))
    missing=next(p for p in set((work/'.reprollm/runs').glob('*'))-before if p.is_dir())
    assert c.read_json(missing/'run.json')['status']=='failed'
    checks.append({'check':'unstartable_command_records_failed_status','passed':True,'exit_code':result.returncode,'run_id':missing.name})
    manifest['custom']['defense']='D1'; c.write_json(work/'reprollm.yaml',manifest)
    command([cli,'export','.','--run',first.name,'--output','selected-history.md'],work)
    exported=(work/'selected-history.md').read_text()
    assert first.name in exported
    checks.append({'check':'explicit_historical_run_export_after_manifest_change','passed':True,'selected_run_id':first.name})
    command([cli,'diff',str(first/'run.json'),str(conflict/'run.json'),'--format','json'],
            work,output=work/'fixture-diff.json')
    checks.append({'check':'recorded_fixture_diff_executes','passed':True})
    report=dict(schema_version=1,scope='CPU-only synthetic contract checks, not scientific model generations.',
                reprollm_version='0.6.1',checks=checks,all_passed=True,
                limitations=['lock --check does not rehash local model files; referenced content needs separate verification.','Only the tested synthetic credential patterns were checked.','Scientific defense effects require the independent real GPU runs.'])
    c.write_json(output,report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args(); verify(args.workspace,args.output)
