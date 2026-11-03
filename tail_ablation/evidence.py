"""Offline checks for the separately frozen follow-up's real model captures."""
import json
from pathlib import Path
import shlex

from privacy_study import core as c
from tail_ablation import core as a
from tools.validate_source_recorder import check_input_capture


def check_capture(root, directory):
    root, directory = Path(root), Path(directory)
    _, model, split, defense = directory.relative_to(root/'evidence').parts
    study=root/a.STUDY; protocol=c.read_json(study/'protocol.json')
    run=c.read_json(directory/'run/run.json')
    data=(directory/'results.jsonl').read_bytes()
    a.require(data.endswith(b'\n'), 'Incomplete follow-up result tail.')
    documents=[json.loads(line) for line in data.splitlines()]
    a.require(documents[0]['type']=='meta', 'Missing follow-up identity.')
    identity=documents[0]['identity'];rows={}
    for row in documents[1:]:
        a.require(row['type']=='sample' and row['id'] not in rows, 'Failure or duplicate follow-up response.')
        rows[row['id']]=row
    batch=protocol['models'][model]['batch_size']
    a.check_freeze(root,model,identity['versions'],batch)
    a.require(identity['study_id']=='tail-ablation-v1' and identity['study_model']==model
              and identity['split']==split and identity['defense']==defense and identity['batch_size']==batch,
              'Follow-up condition identity mismatch.')
    a.require(identity['protocol']==c.digest(study/'protocol.json')
              and identity['dataset']==c.digest(study/'data'/(split+'.jsonl'))
              and identity['prompt_index']==c.digest(study/'prompts'/(model+'.jsonl'))
              and identity['model']==c.read_json(root/protocol['models'][model]['identity']), 'Follow-up input identity mismatch.')
    a.require(identity['code']=={name:c.digest(root/name) for name in a.SCIENCE_FILES}, 'Follow-up source identity mismatch.')
    cases=c.load_cases(study,split);expected=c.expected_ids(cases)
    a.require(identity['cases']==[v['id'] for v in cases] and set(rows)==expected, 'Incomplete follow-up case clusters.')
    manifest=c.read_json(directory/'run'/run['manifest']['snapshot'])
    a.require(manifest['datasets']['eval']['files']==[a.STUDY+'/data/'+split+'.jsonl']
              and manifest['datasets']['eval']['sampling']['n']==len(cases), 'Follow-up declaration uses different cases.')
    argv=run['command']['argv'];declared=shlex.split(manifest['execution']['command'])
    a.require('tail_ablation.run' in argv, 'Unexpected follow-up entry point.')
    for key,value,flag in [('defense',defense,'--defense'),('dataset_split',split,'--split'),
                           ('batch_size',batch,'--batch-size'),('study_model',model,'--study-model')]:
        a.require(manifest['custom'][key]==value and argv[argv.index(flag)+1]==str(value)
                  and declared[declared.index(flag)+1]==str(value)
                  and [v['value'] for v in run['bindings_observed']['custom.'+key]]==[value],
                  'Follow-up declared/observed condition mismatch: '+key)
    snapshots=0
    for item in [run['manifest'],run['lock'],*run['files']]:
        a.require(not item.get('redacted',False), 'Unexpected redacted follow-up input.')
        if item['snapshot']:
            path=(directory/'run'/item['snapshot']).resolve()
            a.require(path.is_relative_to((directory/'run').resolve()), 'Snapshot escaped its run directory.')
            snapshots+=1
        else:
            path=(root/item['path']).resolve()
            a.require(path.is_relative_to(root.resolve()), 'Input escaped the research repository.')
        a.require('sha256:'+c.digest(path)==item['sha256'], 'Follow-up captured input hash mismatch.')
    source=c.read_json(directory/'recorder-source.json');witness=c.read_json(directory/'runtime-witness.json')
    canonical=c.read_json(root/'evidence/source-recovery-validation/primary-reference/recorder-source.json')
    a.require(source==canonical and source['source_commit']==protocol['upstream_source_commit']
              and run['schema_version']==2 and run['reprollm_version']==source['module_version']==witness['module_version']
              and identity['versions']['reprollm']==source['installed_distribution_version']==witness['installed_distribution_version']
              and witness['module_file']=='assets/recorder-source/reprollm/__init__.py'
              and witness['module_sha256']==next(v['sha256'] for v in source['files'] if v['name']=='reprollm/__init__.py'),
              'Follow-up pinned recorder witness mismatch.')
    check_input_capture(run,[])
    a.require(run['status']=='completed' and run['exit_code']==0 and not run['code']['dirty'], 'Follow-up capture did not finish cleanly.')
    packets=a.load_prompts(root,model,split,defense);by_case={v['id']:v for v in cases}
    for row in rows.values():
        packet=packets[row['id']]
        a.require(row['reprollm_run_id']==run['run_id'] and row['task']==by_case[row['case_id']]['task']
                  and row['id']==':'.join(row[k] for k in ('case_id','variant','family','position'))
                  and row['scores']==c.score(by_case[row['case_id']],row['variant'],row['output'])
                  and row['prompt_sha256']==packet['rendered_sha256'] and row['input_ids_sha256']==packet['input_ids_sha256']
                  and row['input_tokens']==packet['input_tokens'], 'Follow-up response/prompt/scoring mismatch.')
    for filename in ('results.jsonl','completion.json'):
        digest=next(v['sha256'] for v in run['artifacts'] if v['path']=='raw/'+filename)
        a.require(digest=='sha256:'+c.digest(directory/filename), 'Follow-up output artifact hash mismatch.')
    completion=c.read_json(directory/'completion.json')
    a.require(completion['expected']==completion['new_generations']==len(rows)
              and completion['reprollm_run_id']==run['run_id']
              and run['run_id'] in (directory/'REPRODUCIBILITY.md').read_text(), 'Follow-up completion/export mismatch.')
    return dict(evidence=directory.relative_to(root).as_posix(),run_id=run['run_id'],status=run['status'],
        child_exit_code=0,recorder_version=run['reprollm_version'],run_schema_version=2,split=split,defense=defense,
        model_label=identity['model']['model_label'],new_responses=len(rows),result_rows=len(rows),snapshot_hashes_checked=snapshots,
        results_sha256=c.digest(directory/'results.jsonl'),capture_warning_count=len(run['warnings']),historical_source_files=[],
        recorded_commit=run['code']['commit'],input_baseline_phase='pre_child',input_changes=[]),identity,rows
