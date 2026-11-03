"""Declare one follow-up condition for actual ReproLLM execution."""
from privacy_study import core as c
from privacy_study import record
from tail_ablation import core as a


def manifest(model, split, defense):
    protocol=c.read_json(a.STUDY+'/protocol.json')
    batch=protocol['models'][model]['batch_size']
    value=record.manifest('D1',split,batch)
    value['experiment']['name']=f'tail-v1-{model}-{split}-{defense}'
    value['datasets']['eval'].update(id='neutral-tail-v1',files=[a.STUDY+'/data/'+split+'.jsonl'])
    value['datasets']['eval']['sampling'].update(seed=protocol['data_seed'],n=protocol['samples'][split])
    value['datasets']['eval']['preprocessing']['script']='tail_ablation/core.py'
    value['prompts']['system']['path']=a.STUDY+'/protocol.json'
    value['custom'].update(defense=defense,study_model=model)
    value['bindings']['custom.study_model']={'cli':'--study-model'}
    for field,key in [('generation.max_tokens','max_new_tokens'),('generation.seed','run_seed')]:
        value['bindings'][field]={'config':a.STUDY+'/protocol.json:'+key}
    value['privacy']['mechanism']=dict(name=defense,params=dict(external_boundary=True,
        trusted_tail_reminder=defense=='D2',neutral_tail=defense=='N',repeated_question=defense!='D1',
        shared_policy_source=a.STUDY+'/protocol.json:system',prompt_inventory=a.STUDY+'/prompts/'+model+'.jsonl'))
    value['execution']['command']=f'python -m tail_ablation.run --model assets/model --study-model {model} --defense {defense} --split {split} --batch-size {batch}'
    value['execution']['config_files']=sorted(set([*a.SCIENCE_FILES,
        *c.read_json(a.STUDY+'/protocol.freeze.json')['files'],a.STUDY+'/protocol.freeze.json',
        '.python-version','requirements.runtime.txt','recorder-source.json']))
    return value
