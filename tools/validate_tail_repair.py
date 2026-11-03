"""Record copy-only tail repair and refusal with actual released/source ReproLLM CLIs."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from privacy_study import core as c
from tools.ci_verify import SOURCE_IDENTITY, check_consumer, directory_hashes
from tools.repair_result_tail import digest
from tools.validate_source_recorder import recorder_witness, runtime_env, verify_payload
from tools.verify_evidence import require

ORIGINAL='evidence/tail-ablation-v1/primary/dev/N/results.jsonl'
SCENARIOS=('inspect','repair','refuse-complete-failure')


def command(work,env,label,args,expected=0):
    cli=Path(sys.executable).with_name('reprollm')
    result=subprocess.run([str(cli),*map(str,args)],cwd=work,env=env,capture_output=True,text=True,timeout=180)
    (work/'raw'/(label+'.stdout')).write_text(result.stdout)
    (work/'raw'/(label+'.stderr')).write_text(result.stderr)
    require(result.returncode==expected,f'{label} returned {result.returncode}; inspect its saved output.')
    return result.stdout


def prepare(work,engine,scenario,source,document):
    work.mkdir(parents=True,exist_ok=False);(work/'inputs').mkdir();(work/'raw').mkdir()
    shutil.copyfile(ROOT/'tools/repair_result_tail.py',work/'repair.py')
    original=(ROOT/ORIGINAL).read_bytes()
    expected=next(v['results_sha256'] for v in c.read_json(ROOT/'reports/delivery/evidence-verification.json')['runs']
                  if v['evidence']=='evidence/tail-ablation-v1/primary/dev/N')
    require(digest(original)==expected,'The selected real source artifact no longer matches its published receipt.')
    lines=original.splitlines(keepends=True);identity=json.loads(lines[0])['identity']
    genuine=b''.join(lines[:9])
    failure=b'{"type":"failure","sample_ids":["controlled"],"error_type":"SyntheticFailure"}\n'
    prefix=genuine+failure
    fragment=b'{"type":"sample","id":"controlled-tail","output":"unfinished'
    negative=failure.rstrip(b'\n')
    data=prefix+(negative if scenario=='refuse-complete-failure' else fragment)
    (work/'inputs/genuine-prefix.jsonl').write_bytes(genuine)
    (work/'inputs/checkpoint.jsonl').write_bytes(data)
    c.write_json(work/'inputs/identity.json',identity)
    c.write_json(work/'inputs/derivation.json',dict(schema_version=1,original=ORIGINAL,
        original_sha256=expected,genuine_prefix_sha256=digest(genuine),genuine_sample_rows=8,
        complete_synthetic_failure_rows=1,controlled_suffix=('complete JSON failure without newline'
        if scenario=='refuse-complete-failure' else 'synthetic unfinished sample string'),
        source_model_generations=0,scope='Controlled corruption of copies of existing public rows; no new model execution.'))
    (work/'.gitignore').write_text('raw/\nassets/\n.reprollm/runs/\n__pycache__/\n')
    env=runtime_env(engine=='source')
    if engine=='source':
        for item in document['files']:
            target=work/'assets/recorder-source'/item['name'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source/'src'/item['name'],target)
        c.write_json(work/'recorder-source.json',document);verify_payload(work,document)
        witness_doc=document
    else:
        witness_doc=dict(module_version='0.6.1',installed_distribution_version=document['installed_distribution_version'])
    witness=recorder_witness(work,witness_doc,engine=='source',env)
    c.write_json(work/'raw/runtime-witness.json',witness)
    mode='inspect' if scenario=='inspect' else 'repair'
    args=['python','repair.py','--input','inputs/checkpoint.jsonl','--identity','inputs/identity.json','--mode',mode]
    if mode=='repair':args+=['--sha256',digest(data),'--output-directory','raw/bundle']
    declaration=dict(schema_version=1,project=dict(name='result_tail_repair_fixture'),
        experiment=dict(name=engine+'-'+scenario,profiles=[]),custom=dict(mode=mode,input_file='inputs/checkpoint.jsonl'),
        bindings={'custom.mode':dict(cli='--mode'),'custom.input_file':dict(cli='--input')},
        execution=dict(command=' '.join(args),config_files=['repair.py','inputs/checkpoint.jsonl','inputs/identity.json','inputs/derivation.json']),
        artifacts=dict(outputs=['raw/bundle/*.json','raw/bundle/*.jsonl','raw/bundle/*.bin']))
    c.write_json(work/'reprollm.yaml',declaration)
    subprocess.run(['git','init','-q'],cwd=work,check=True,capture_output=True)
    for name,flag in [('mode','--mode'),('input_file','--input')]:
        command(work,env,'rule-'+name,['rules','add','--id','project.'+name,'--field','custom.'+name,
            '--severity','CRITICAL','--reason','The actual repair operation and checkpoint must match the declaration.','--cli='+flag])
    command(work,env,'offline-lock',['lock','.','--offline'])
    command(work,env,'lock-check',['lock','.','--check'])
    names=['.gitignore','repair.py','inputs','reprollm.yaml','reprollm.lock','.reprollm/project-rules.yaml']
    if engine=='source':names.append('recorder-source.json')
    subprocess.run(['git','add',*names],cwd=work,check=True,capture_output=True)
    subprocess.run(['git','-c','user.name=CPU fixture','-c','user.email=fixture@example.invalid','commit','-qm',
                    'test: freeze controlled result-tail repair inputs'],cwd=work,check=True,capture_output=True)
    require(not subprocess.check_output(['git','status','--porcelain'],cwd=work,text=True).strip(),'Fixture inputs are dirty.')
    return env,args,witness,data,prefix,identity


def exercise(work,engine,scenario,source,document):
    env,args,witness,data,prefix,identity=prepare(work,engine,scenario,source,document)
    before=set((work/'.reprollm/runs').glob('*'));inputs=directory_hashes(work/'inputs')
    args[0]=sys.executable
    expected=2 if scenario=='refuse-complete-failure' else 0
    command(work,env,'launcher',['run','--name',scenario,'--capture-output','--',*args],expected)
    created=set((work/'.reprollm/runs').glob('*'))-before;require(len(created)==1,'Expected one actual repair-tool recording.')
    run_dir=created.pop();run=c.read_json(run_dir/'run.json');run_id=run['run_id']
    require(run['status']=='completed' and run['exit_code']==expected and not run['code']['dirty'],
            'Unexpected CPU child outcome or dirty recording inputs.')
    require(run['schema_version']==(2 if engine=='source' else 1)
            and run['reprollm_version']==witness['module_version'],'Wrong recorder producer/schema.')
    for key,value in [('mode','inspect' if scenario=='inspect' else 'repair'),('input_file','inputs/checkpoint.jsonl')]:
        require([v['value'] for v in run['bindings_observed']['custom.'+key]]==[value],'CLI binding mismatch.')
    require(inputs==directory_hashes(work/'inputs'),'Repair operation changed the source or trusted inputs.')
    if scenario=='repair':
        bundle=work/'raw/bundle';receipt=c.read_json(bundle/'receipt.json')
        require((bundle/'damaged.jsonl').read_bytes()==data and (bundle/'repaired.jsonl').read_bytes()==prefix
                and receipt['tool_run_id']==run_id and receipt['complete_failure_rows']==1,'Copy/backup/receipt mismatch.')
        require(len(c.completed_rows(bundle/'repaired.jsonl',identity))==8,'Frozen scientific resume reader did not retain all eight original successes.')
        for item in run['artifacts']:
            require('sha256:'+c.digest(work/item['path'])==item['sha256'],'Recorder output artifact hash mismatch.')
    else:
        require(not (work/'raw/bundle').exists(),'Inspection or refusal created an unexpected output bundle.')
    if scenario=='refuse-complete-failure':
        require('complete JSON without a newline' in (run_dir/'stderr.log').read_text(),'Missing actual refusal diagnostic.')
    saved=directory_hashes(run_dir)
    shown=command(work,env,'show',['runs','show',run_id,'--json'])
    require(shown==(run_dir/'run.json').read_text(),'Run inspection changed the saved record.')
    command(work,env,'export',['export','.','--run',run_id,'--output','raw/REPRODUCIBILITY.md'])
    require(run_id in (work/'raw/REPRODUCIBILITY.md').read_text(),'Selected export chose a different run.')
    if engine=='source':
        filtered=json.loads(command(work,env,'outcome',['runs','list','--outcome','failure' if expected else 'success','--json']))
        require([v['run_id'] for v in filtered]==[run_id],'Source outcome filter lost the actual child outcome.')
        verify_payload(work,document)
    require(saved==directory_hashes(run_dir) and inputs==directory_hashes(work/'inputs'),'Post-run inspection rewrote history or inputs.')
    print(json.dumps(dict(event='tail_repair_checked',engine=engine,scenario=scenario,run_id=run_id,child_exit_code=expected)),flush=True)
    return dict(engine=engine,scenario=scenario,run_id=run_id,run_schema_version=run['schema_version'],
        recorder_version=run['reprollm_version'],child_exit_code=expected,record_status=run['status'],
        original_inputs_unchanged=True,run_directory_unchanged=True,
        retained_sample_rows=8,complete_failure_rows_preserved=1 if scenario=='repair' else None,
        backup_and_output_hashes_verified=scenario=='repair',scientific_reader_compatibility_checked=scenario=='repair')


def validate(source,workspace,output):
    tool_sha256=c.digest(ROOT/'tools/repair_result_tail.py')
    document=c.read_json(ROOT/SOURCE_IDENTITY);consumer=check_consumer(source,document)
    workspace.mkdir(parents=True,exist_ok=False)
    pairs=[(engine,scenario) for engine in ('released','source') for scenario in SCENARIOS]
    def run(pair):return exercise(workspace/pair[0]/pair[1],*pair,source,document)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:records=list(pool.map(run,pairs))
    diffs=[]
    for engine in ('released','source'):
        work=workspace/engine/'inspect';env=runtime_env(engine=='source')
        left=next((workspace/engine/'inspect/.reprollm/runs').glob('*/run.json'))
        right=next((workspace/engine/'repair/.reprollm/runs').glob('*/run.json'))
        value=json.loads(command(work,env,'mode-diff',['diff',left,right,'--format','json']))
        require(any(v['path']=='custom.mode' for v in value['changes']),'Actual inspection/repair mode drift was lost.')
        c.write_json(workspace/(engine+'-diff.json'),value)
        diffs.append(dict(engine=engine,custom_mode_change_detected=True))
    require(c.digest(ROOT/'tools/repair_result_tail.py')==tool_sha256,'Repair tool changed during validation.')
    result=dict(schema_version=1,all_passed=True,consumer=consumer,records=records,diffs=diffs,
        actual_cpu_recordings=6,new_model_generations=0,repair_tool_sha256=c.digest(ROOT/'tools/repair_result_tail.py'),
        scope='Controlled corruption/failure markers on copies of existing public model rows; actual repair-tool CLI capture, not GPU corruption/recovery or power-loss testing.')
    c.write_json(output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consumer-source',type=Path,required=True)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    validate(args.consumer_source.resolve(),args.workspace.resolve(),args.output.resolve())
