"""Exercise actual pinned-source project-rule lifecycle commands without inference."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from privacy_study import core as c
from tools.ci_verify import SOURCE_IDENTITY, check_consumer, directory_hashes
from tools.validate_source_recorder import check_input_capture, recorder_witness, runtime_env, verify_payload
from tools.verify_evidence import local_file, require

SCENARIOS=('roundtrip','conflict','tampered')


def call(work,env,label,args,expected=0):
    cli=Path(sys.executable).with_name('reprollm')
    result=subprocess.run([str(cli),*map(str,args)],cwd=work,env=env,capture_output=True,text=True,timeout=180)
    (work/'raw'/(label+'.stdout')).write_text(result.stdout)
    (work/'raw'/(label+'.stderr')).write_text(result.stderr)
    require(result.returncode==expected,f'{label}: expected exit {expected}, got {result.returncode}; inspect saved output.')
    return result.stdout


def prepare(work,scenario,source,document):
    work.mkdir(parents=True,exist_ok=False);(work/'raw').mkdir();(work/'inputs').mkdir()
    shutil.copyfile(ROOT/'tools/rule_lifecycle_fixture.py',work/'fixture.py')
    c.write_json(work/'configuration.json',dict(settings=dict(defense='D0')))
    for item in document['files']:
        target=work/'assets/recorder-source'/item['name'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/'src'/item['name'],target)
    c.write_json(work/'recorder-source.json',document);verify_payload(work,document)
    args=['python','fixture.py','--scenario',scenario,'--defense','D0']
    config_files=['fixture.py','configuration.json','recorder-source.json','.reprollm/project-rules.yaml']
    manifest=dict(schema_version=1,project=dict(name='project_rule_lifecycle_consumer'),
        experiment=dict(name=scenario,profiles=[]),custom=dict(scenario=scenario,defense='D0'),
        bindings={'custom.scenario':dict(cli='--scenario'),
                  'custom.defense':dict(cli='--defense',config='configuration.json:settings.defense',env='RULE_CHECK_DEFENSE')},
        execution=dict(command=' '.join(args),config_files=config_files),
        artifacts=dict(outputs=['raw/result.json','raw/snapshots/*','.reprollm/rule-archives/*.json']))
    c.write_json(work/'reprollm.yaml',manifest)
    (work/'.gitignore').write_text('raw/\nassets/\n.reprollm/runs/\n__pycache__/\n')
    subprocess.run(['git','init','-q'],cwd=work,check=True,capture_output=True)
    env=dict(runtime_env(True),RULE_CHECK_DEFENSE='D0',NO_COLOR='1',TERM='dumb')
    call(work,env,'add-scenario',['rules','add','--id','project.scenario','--field','custom.scenario',
         '--severity','CRITICAL','--reason','Bind the controlled scenario.','--cli=--scenario'])
    add=['rules','add','--id','project.defense','--field','custom.defense','--severity','CRITICAL',
         '--reason','Bind the declared defense to observed values.','--cli=--defense',
         '--config','configuration.json:settings.defense','--env','RULE_CHECK_DEFENSE']
    call(work,env,'add-defense',add)
    if scenario!='roundtrip':
        call(work,env,'prepare-archive',['rules','remove','project.defense','--reason','Retire the synthetic defense rule.'])
        archive=next((work/'.reprollm/rule-archives').glob('*.json'))
        shutil.copyfile(archive,work/'inputs/original-archive.json')
        config_files.extend(['inputs/original-archive.json',archive.relative_to(work).as_posix()])
        if scenario=='conflict':
            changed=add.copy();changed[changed.index('CRITICAL')]='WARNING'
            changed[changed.index('Bind the declared defense to observed values.')]='A different active declaration.'
            call(work,env,'prepare-conflict',changed)
        else:
            damaged=c.read_json(archive);damaged['reason']+=' Controlled copy alteration.';c.write_json(archive,damaged)
        c.write_json(work/'reprollm.yaml',manifest)
    call(work,env,'offline-lock',['lock','.','--offline']);call(work,env,'fresh-lock',['lock','.','--check'])
    subprocess.run(['git','add','.'],cwd=work,check=True,capture_output=True)
    subprocess.run(['git','-c','user.name=CPU consumer','-c','user.email=consumer@example.invalid','commit','-qm',
                    'test: freeze project-rule lifecycle '+scenario],cwd=work,check=True,capture_output=True)
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=work,text=True).strip(),'Fixture is not clean before recording.')
    return env,args


def exercise(work,scenario,source,document):
    env,args=prepare(work,scenario,source,document)
    witness=recorder_witness(work,document,True,env);c.write_json(work/'raw/runtime-witness.json',witness)
    paths=['reprollm.yaml','reprollm.lock',*c.read_json(work/'reprollm.yaml')['execution']['config_files']]
    before={name:c.digest(work/name) for name in paths}
    args[0]=sys.executable
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=work,text=True).strip(),'Fixture changed before launch.')
    call(work,env,'launcher',['run','--name',scenario,'--capture-output','--',*args])
    run_dir=next((work/'.reprollm/runs').iterdir());run=c.read_json(run_dir/'run.json')
    return assess(work,scenario,env,document,run_dir,before)


def assess(work,scenario,env,document,run_dir,before):
    """Assess an existing real record; never repeat a child to repair assessment logic."""
    run=c.read_json(run_dir/'run.json')
    require(run['status']=='completed' and run['exit_code']==0, 'Unexpected outer recording outcome.')
    require(run['schema_version']==2 and run['reprollm_version']==document['module_version'],'Wrong producer or schema.')
    for item in (run['manifest'],run['lock'],*run['files']):
        committed=subprocess.check_output(['git','show',run['code']['commit']+':'+item['path']],cwd=work)
        require(committed==local_file(run_dir,item['snapshot']).read_bytes(),'Captured initial inputs differ from their committed bytes.')
    changed=sorted(name for name,digest in before.items() if c.digest(work/name)!=digest)
    check_input_capture(run,changed);verify_payload(work,document)
    result=c.read_json(work/'raw/result.json')
    require(result['all_passed'] and result['scenario']==scenario and result['reprollm_run_id']==run['run_id'],'Driver result is not bound to its recording.')
    observed=run['bindings_observed']['custom.defense']
    require(all(v['value']=='D0' for v in observed)
            and {v['source']['type'] for v in observed}=={'cli','config','env'},
            'Missing actual CLI/config/environment observations.')
    for item in run['artifacts']:
        require(item['sha256']=='sha256:'+c.digest(work/item['path']),'Recorded output artifact differs from disk.')
    saved=directory_hashes(run_dir)
    if not (work/'raw/REPRODUCIBILITY.md').exists():
        call(work,env,'export',['export','.','--run',run['run_id'],'--output','raw/REPRODUCIBILITY.md'])
    require(run['run_id'] in (work/'raw/REPRODUCIBILITY.md').read_text(),'Selected export lost the actual run.')
    require(saved==directory_hashes(run_dir),'Export rewrote the historical run directory.')
    summary=dict(scenario=scenario,run_id=run['run_id'],status=run['status'],child_exit_code=run['exit_code'],
        recorder_version=run['reprollm_version'],run_schema_version=2,commands=len(result['commands']),
        expected_input_changes=changed,archive_id=result['archive_id'],all_passed=True,new_model_generations=0,
        pre_run_git_clean=True,committed_input_snapshots_verified=True,recorded_git_dirty=run['code']['dirty'])
    c.write_json(work/'raw/controller.json',summary)
    print(json.dumps(dict(event='rule_lifecycle_checked',**summary)),flush=True)
    return summary


def publish(work,out):
    out.mkdir(parents=True,exist_ok=False);summary=c.read_json(work/'raw/controller.json')
    source=work/'.reprollm/runs'/summary['run_id'];run=c.read_json(source/'run.json')
    shutil.copytree(source,out/'run')
    for item in (run['manifest'],run['lock'],*run['files']):
        target=local_file(out/'inputs',item['path']);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(local_file(source,item['snapshot']),target)
    for item in run['artifacts']:
        target=local_file(out/'outputs',item['path']);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(local_file(work,item['path']),target)
    for name in ('controller.json','runtime-witness.json','REPRODUCIBILITY.md'):
        shutil.copyfile(work/'raw'/name,out/name)
    require(directory_hashes(source)==directory_hashes(out/'run'),'Publication changed the original run directory.')


def validate(source,workspace,output,published=None):
    document=c.read_json(ROOT/SOURCE_IDENTITY);consumer=check_consumer(source,document)
    workspace.mkdir(parents=True,exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(exercise,workspace/scenario,scenario,source,document) for scenario in SCENARIOS]
        records=[f.result() for f in futures]
    cli=Path(sys.executable).with_name('reprollm');released=runtime_env(False)
    version=subprocess.run([str(cli),'--version'],env=released,capture_output=True,text=True,check=True).stdout.strip()
    help_text=subprocess.run([str(cli),'rules','--help'],env=dict(released,NO_COLOR='1',TERM='dumb'),capture_output=True,text=True,check=True).stdout
    capability=dict(version=version,remove_listed='remove' in help_text,restore_listed='restore' in help_text,
                    scope='Help-only released reference; lifecycle acceptance applies to pinned source.')
    result=dict(schema_version=1,all_passed=True,consumer=consumer,records=records,released_reference=capability,
                actual_cpu_recordings=3,new_model_generations=0,new_gpu_captures=0,
                source_payload_unchanged=True,installed_distribution_unchanged=True)
    if published:
        from tools.verify_rule_lifecycle import verify_published
        result['published_evidence']=verify_published(published)
    c.write_json(output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consumer-source',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--published',type=Path)
    args=parser.parse_args();validate(args.consumer_source.resolve(),args.workspace.resolve(),args.output.resolve(),args.published)
