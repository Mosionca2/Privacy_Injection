"""Annotate actual prompt mechanisms; record against an already committed lock."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from privacy_study import core as c
from privacy_study import record
from privacy_study.run import versions


def complete(workspace):
    root=Path(workspace); value=c.read_json(root/'reprollm.yaml'); defense=value['custom']['defense']
    value['privacy']['mechanism']['params']={
        'external_boundary':defense!='D0', 'trusted_tail_reminder':defense=='D2',
        'per_line_origin_labels':defense=='D3','shared_policy_source':'configs/protocol.json:system'}
    value['execution']['config_files']=sorted(set(value['execution']['config_files']+['.python-version','requirements.runtime.txt']))
    from reprollm.schemas.manifest import Manifest
    Manifest.model_validate(value)
    c.write_json(root/'reprollm.yaml',value)
    (root/'.python-version').write_text(sys.version.split()[0]+'\n')
    (root/'requirements.runtime.txt').write_text(''.join(f'{name}=={version}\n' for name,version in sorted(versions().items())))


def record_committed(workspace,gpu_id):
    root=Path(workspace); cli=Path(sys.executable).with_name('reprollm'); raw=root/'raw'
    value=c.read_json(root/'reprollm.yaml'); spec=value['custom']
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=gpu_id,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
             HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false',PYTHONUNBUFFERED='1')
    record.command([cli,'lock','.','--check'],root,env=env)
    before=set((root/'.reprollm/runs').glob('*'))
    argv=[sys.executable,'-m','privacy_study.run','--model','assets/model','--defense',spec['defense'],
          '--split',spec['dataset_split'],'--batch-size',str(spec['batch_size']),'--limit','8']
    record.command([cli,'run','--name','metadata-'+spec['defense'],'--capture-output','--']+argv,
                   root,output=raw/'launch.txt',env=env)
    created=[p for p in set((root/'.reprollm/runs').glob('*'))-before if p.is_dir()]
    if len(created)!=1: raise ValueError('Expected one actual run.')
    run_id=created[0].name
    record.command([cli,'runs','show',run_id,'--json'],root,output=raw/'selected-run.json',env=env)
    record.command([cli,'audit','.','--format','json','--fail-on','never'],root,output=raw/'audit.json',env=env)
    record.command([cli,'export','.','--run',run_id,'--output','raw/reproducibility.md'],root,output=raw/'export.txt',env=env)
    c.write_json(raw/'recording.json',dict(schema_version=1,run_id=run_id,defense=spec['defense'],split=spec['dataset_split']))
    return run_id

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True)
    p.add_argument('--record',action='store_true');p.add_argument('--gpu-id')
    a=p.parse_args()
    if a.record:
        if not a.gpu_id: p.error('Record mode requires a GPU identifier.')
        print(record_committed(a.workspace,a.gpu_id))
    else: complete(a.workspace)
