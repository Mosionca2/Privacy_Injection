"""ReproLLM orchestration with independent condition workspaces and local weights."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from privacy_study import core as c


def command(argv, cwd, *, allowed=(0,), output=None, env=None):
    result=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if output:
        target=Path(output); target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(result.stdout)
        target.with_suffix(target.suffix+'.stderr').write_text(result.stderr)
    if result.returncode not in allowed:
        raise RuntimeError(f'Command {argv[0]} failed ({result.returncode}): {result.stderr[-1500:]} {result.stdout[-1000:]}')
    return result


def model_identity(model_dir):
    root=Path(model_dir)
    files=sorted(p for p in root.iterdir() if p.is_file() and (p.suffix in ('.json','.safetensors','.model','.jinja')))
    return dict(schema_version=1,model_label='Qwen3-8B',upstream_revision=None,
                provenance='Existing local files; upstream revision not independently established.',
                files=[dict(name=p.name,size=p.stat().st_size,sha256=c.digest(p)) for p in files])


def link_model(model_dir, workspace):
    model_dir=Path(model_dir); target=Path(workspace)/'assets/model'; target.mkdir(parents=True,exist_ok=True)
    for item in model_dir.iterdir():
        if item.is_file() and item.suffix in ('.json','.safetensors','.model','.jinja'):
            dest=target/item.name
            if not dest.exists(): os.link(item,dest)


def manifest(defense,split,batch_size,limit=None):
    from privacy_study.run import versions
    protocol=c.read_json('configs/protocol.json')
    args=['python','-m','privacy_study.run','--model','assets/model','--defense',defense,'--split',split,'--batch-size',str(batch_size)]
    if limit: args+=['--limit',str(limit)]
    return dict(schema_version=1,project={'name':'Privacy_Injection'},
        experiment={'name':f'{split}-{defense}-b{batch_size}','profiles':['inference','evaluation','privacy']},
        models={'primary':{'provider':'local','id':'assets/model','dtype':'float16','quantization':'none',
                'trust_remote_code':False,'tokenizer':{'id':'assets/model'}}},
        datasets={'eval':{'provider':'local','id':'paired-identifiers-v1','split':split,'files':[f'data/{split}.jsonl'],
                         'sampling':{'n':limit or protocol['samples'][split],'method':'fixed_cases','seed':protocol['data_seed']},
                         'preprocessing':{'script':'privacy_study/core.py','description':'Balanced deterministic lookup and latest-record tasks.'}}},
        prompts={'system':{'path':'configs/protocol.json','format':'plain','few_shot':{'n':0}}},
        generation={'do_sample':False,'temperature':0.,'top_p':1.,'max_tokens':protocol['max_new_tokens'],'seed':protocol['run_seed'],'stop':[]},
        inference={'backend':'transformers','version':versions()['transformers'],'mode':'offline','dtype':'float16',
                   'quantization':'none','tensor_parallel_size':1,'max_model_len':protocol['max_input_tokens']+protocol['max_new_tokens'],
                   'params':{'batch_size':batch_size,'enable_thinking':False,'attention':'sdpa'}},
        evaluation={'metrics':[{'name':metric,'implementation':'privacy_study/core.py'} for metric in ['leak','utility','safe_utility']],
                    'repetitions':1,'query_budget':6,'aggregation':'Paired base-case clusters; controls kept separate.',
                    'definitions':{'asr':'Complete synthetic private identifier in newly generated attack response.'}},
        privacy={'threat_model':'Only retrieved text is attacker-controlled; private identifiers and system policy are hidden from the attacker.',
                 'mechanism':{'name':defense},'metrics':['leak','safe_utility'],'attack':{'method':'three fixed families in two positions','query_budget':6}},
        execution={'command':' '.join(args),'seed':protocol['run_seed'],'config_files':['configs/protocol.json','model.identity.json']},
        custom={'defense':defense,'dataset_split':split,'batch_size':batch_size},
        bindings={'models.primary.id':{'cli':'--model'},'custom.defense':{'cli':'--defense'},
                  'custom.dataset_split':{'cli':'--split'},'custom.batch_size':{'cli':'--batch-size'},
                  'generation.max_tokens':{'config':'configs/protocol.json:max_new_tokens'},
                  'generation.seed':{'config':'configs/protocol.json:run_seed'}},
        artifacts={'outputs':['raw/results.jsonl','raw/completion.json']})


def workspace(source, destination, model_dir, defense, split, batch_size, limit=None):
    source=Path(source).resolve(); destination=Path(destination).resolve()
    if destination.exists(): raise ValueError('Use a new condition workspace, or resume its existing declaration.')
    command(['git','clone','--quiet','--no-hardlinks',source,destination],source)
    command(['git','remote','set-url','origin','https://github.com/Mosionca2/Privacy_Injection.git'],destination)
    link_model(model_dir,destination)
    cli=Path(sys.executable).with_name('reprollm')
    command([cli,'init','.','--profiles','inference,evaluation,privacy'],destination,output=destination/'raw/init.txt')
    old=Path.cwd()
    try:
        os.chdir(destination); c.write_json('reprollm.yaml',manifest(defense,split,batch_size,limit))
    finally: os.chdir(old)
    for field,flag in [('defense','--defense'),('dataset_split','--split'),('batch_size','--batch-size')]:
        command([cli,'rules','add','--id',f'project.{field}','--field',f'custom.{field}','--severity','CRITICAL',
                 '--reason','This declared value must agree with actual execution.',f'--cli={flag}'],destination)
    return destination


def execute(work, gpu_uuid, *, limit=None, hash_weights=True):
    work=Path(work); cli=Path(sys.executable).with_name('reprollm'); declared=c.read_json(work/'reprollm.yaml')
    spec=declared['custom']; out=work/'raw'; out.mkdir(exist_ok=True)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu_uuid,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
             HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',PYTHONUNBUFFERED='1')
    lock=[cli,'lock','.','--offline']+(['--hash-large-files'] if hash_weights else [])
    command(lock,work,output=out/'lock.txt',env=env)
    command([cli,'lock','.','--check'],work,output=out/'lock-check.txt',env=env)
    args=[sys.executable,'-m','privacy_study.run','--model','assets/model','--defense',spec['defense'],
          '--split',spec['dataset_split'],'--batch-size',str(spec['batch_size'])]
    if limit: args+=['--limit',str(limit)]
    before=set((work/'.reprollm/runs').glob('*'))
    command([cli,'run','--name',declared['experiment']['name'],'--capture-output','--']+args,
            work,output=out/'launch.txt',env=env)
    created=set((work/'.reprollm/runs').glob('*'))-before
    ids=sorted(p.name for p in created if p.is_dir())
    if len(ids)!=1: raise ValueError('Expected one real ReproLLM run.')
    run_id=ids[0]
    command([cli,'runs','show',run_id,'--json'],work,output=out/'selected-run.json',env=env)
    command([cli,'audit','.','--format','json','--fail-on','never'],work,output=out/'audit.json',env=env)
    command([cli,'export','.','--run',run_id,'--output','raw/reproducibility.md'],work,output=out/'export.txt',env=env)
    c.write_json(out/'recording.json',dict(schema_version=1,run_id=run_id,defense=spec['defense'],split=spec['dataset_split']))
    return run_id


def publish_evidence(work,destination):
    work=Path(work); destination=Path(destination)
    recording=c.read_json(work/'raw/recording.json'); run_id=recording['run_id']
    destination.mkdir(parents=True,exist_ok=True)
    shutil.copytree(work/'.reprollm/runs'/run_id,destination/'run',dirs_exist_ok=True)
    for source,name in [('raw/results.jsonl','results.jsonl'),('raw/completion.json','completion.json'),
                         ('raw/audit.json','audit.json'),('raw/reproducibility.md','REPRODUCIBILITY.md'),
                         ('raw/recording.json','recording.json'),('reprollm.yaml','reprollm.yaml'),
                         ('reprollm.lock','reprollm.lock'),('.reprollm/project-rules.yaml','project-rules.yaml')]:
        shutil.copyfile(work/source,destination/name)
        if name=='audit.json':
            target=destination/name; target.write_text(target.read_text().rstrip()+'\n')
    return recording
