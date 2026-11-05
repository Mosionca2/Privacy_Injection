"""Standalone CPU consumer copied into isolated rule-lifecycle workspaces."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive_id(document):
    body = {k:v for k,v in document.items() if k != 'archive_id'}
    return 'ra-'+sha(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())[:16]


def exercise(scenario, defense):
    root=Path.cwd();raw=root/'raw';(raw/'snapshots').mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH=str(root/'assets/recorder-source'))
    cli=str(Path(sys.executable).with_name('reprollm'))
    commands=[];snapshots={}
    def keep(name,path):
        data=path.read_bytes();target=raw/'snapshots'/name;target.write_bytes(data)
        snapshots[name]=dict(path=target.relative_to(root).as_posix(),sha256=sha(data))
        return data
    def call(label,args,expected=0):
        start=time.perf_counter()
        result=subprocess.run([cli,*args],cwd=root,env=env,capture_output=True,text=True,timeout=120)
        (raw/(label+'.stdout')).write_text(result.stdout);(raw/(label+'.stderr')).write_text(result.stderr)
        commands.append(dict(label=label,argv=['reprollm',*args],expected_exit=expected,actual_exit=result.returncode,
            duration_seconds=round(time.perf_counter()-start,6),stdout=result.stdout.replace(str(root),'<workspace>'),
            stderr=result.stderr.replace(str(root),'<workspace>'),stdout_sha256=sha(result.stdout.encode()),
            stderr_sha256=sha(result.stderr.encode())))
        if result.returncode != expected:
            raise RuntimeError(f'{label}: expected exit {expected}, got {result.returncode}; inspect saved output.')
        return result.stdout
    rules=root/'.reprollm/project-rules.yaml';lock=root/'reprollm.lock'
    immutable={name:sha((root/name).read_bytes()) for name in ('fixture.py','configuration.json','reprollm.yaml','recorder-source.json')}
    before_rules=keep('before-rules.yaml',rules);before_lock=keep('before-lock.json',lock)
    before_list=json.loads(call('before-list',['rules','list','--json']))
    if scenario == 'roundtrip':
        original=next(r for r in before_list if r['id']=='project.defense')
        call('fresh-before',['lock','.','--check'])
        prior=set((root/'.reprollm/rule-archives').glob('*.json'))
        call('remove',['rules','remove','project.defense','--reason','Retire the synthetic defense rule.'])
        created=set((root/'.reprollm/rule-archives').glob('*.json'))-prior
        if len(created)!=1:raise ValueError('Expected one new recovery archive.')
        archive_path=created.pop();archive=json.loads(archive_path.read_text());identifier=archive_path.stem
        if archive['archive_id']!=identifier or archive_id(archive)!=identifier or archive['rule']!=original:
            raise ValueError('Archive lost the original rule or its content identity.')
        archive_bytes=keep('archive-original.json',archive_path)
        keep('removed-rules.yaml',rules)
        if any(r['id']=='project.defense' for r in json.loads(call('removed-list',['rules','list','--json']))):
            raise ValueError('The rule remains active after successful removal.')
        if json.loads(call('removed-show',['rules','show',identifier]))['state']!='inactive':
            raise ValueError('Inspection did not derive inactive archive state.')
        call('stale-after-remove',['lock','.','--check'],1)
        if lock.read_bytes()!=before_lock:raise ValueError('Freshness check rewrote the lock.')
        call('refresh-inactive',['lock','.','--offline']);keep('inactive-lock.json',lock)
        call('restore',['rules','restore',identifier]);keep('restored-rules.yaml',rules)
        restored=json.loads(call('restored-list',['rules','list','--json']))
        if restored!=before_list:raise ValueError('Restore changed complete rule semantics or ordering.')
        if archive_path.read_bytes()!=archive_bytes:raise ValueError('Restore rewrote the recovery copy.')
        if json.loads(call('restored-show',['rules','show',identifier]))['state']!='active-identical':
            raise ValueError('Inspection did not derive active-identical archive state.')
        unchanged_lock=lock.read_bytes();call('stale-after-restore',['lock','.','--check'],1)
        if lock.read_bytes()!=unchanged_lock:raise ValueError('Freshness check rewrote the inactive-rule lock.')
        duplicate_before=(rules.read_bytes(),archive_path.read_bytes(),lock.read_bytes())
        call('duplicate-refused',['rules','restore',identifier],2)
        if duplicate_before!=(rules.read_bytes(),archive_path.read_bytes(),lock.read_bytes()):
            raise ValueError('Duplicate restoration changed state.')
        call('refresh-restored',['lock','.','--offline']);call('fresh-final',['lock','.','--check'])
        original_rule=original
    else:
        archive_path=next((root/'.reprollm/rule-archives').glob('*.json'));identifier=archive_path.stem
        archive_bytes=keep('archive-input.json',archive_path)
        original_rule=json.loads((root/'inputs/original-archive.json').read_text())['rule']
        unchanged=(rules.read_bytes(),archive_path.read_bytes(),lock.read_bytes())
        call('restore-refused',['rules','restore',identifier],2)
        if scenario=='conflict':
            call('builtin-remove-refused',['rules','remove','model.revision_pinned','--reason','Synthetic refusal check.'],2)
            if json.loads(call('conflict-show',['rules','show',identifier]))['state']!='conflict':
                raise ValueError('Inspection did not derive conflicting active state.')
        if unchanged!=(rules.read_bytes(),archive_path.read_bytes(),lock.read_bytes()):
            raise ValueError('Expected refusal changed active rules, archive or lock.')
        if rules.read_bytes()!=before_rules or archive_path.read_bytes()!=archive_bytes:
            raise ValueError('Refusal did not preserve the input bytes.')
    keep('final-rules.yaml',rules);keep('final-lock.json',lock)
    if immutable!={name:sha((root/name).read_bytes()) for name in immutable}:
        raise ValueError('Lifecycle commands changed experiment code, manifest, configuration or source identity.')
    config=json.loads((root/'configuration.json').read_text())['settings']['defense']
    observed=dict(cli=defense,config=config,env=os.environ['RULE_CHECK_DEFENSE'])
    if set(observed.values())!={'D0'}:raise ValueError('The fixture did not consume the expected three bound values.')
    result=dict(schema_version=1,all_passed=True,scenario=scenario,reprollm_run_id=os.environ['REPROLLM_RUN_ID'],
        commands=commands,snapshots=snapshots,archive_id=identifier,original_rule=original_rule,
        consumed_values=observed,immutable_input_hashes=immutable,new_model_generations=0,
        output_normalization='Workspace root replaced with <workspace>; original output digests and private command outputs retained.')
    (raw/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(scenario=scenario,all_passed=True,commands=len(commands))),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario',choices=['roundtrip','conflict','tampered'],required=True)
    parser.add_argument('--defense',required=True)
    args=parser.parse_args();exercise(args.scenario,args.defense)
