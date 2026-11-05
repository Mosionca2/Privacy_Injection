"""Independently check published CPU lifecycle records and intermediate byte evidence."""
import hashlib
import json
from pathlib import Path

import yaml

from privacy_study import core as c
from tools.ci_verify import SOURCE_IDENTITY
from tools.validate_source_recorder import check_input_capture
from tools.verify_evidence import flag, local_file, require

ROOT=Path(__file__).resolve().parents[1]


def content_id(archive):
    body={k:v for k,v in archive.items() if k!='archive_id'}
    return 'ra-'+hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:16]


def rules(data):
    value=yaml.safe_load(data)
    return json.loads(json.dumps(value,default=lambda v:v.isoformat().replace('+00:00','Z')))['rules']


def verify_case(out,scenario):
    out=Path(out).resolve();run=c.read_json(out/'run/run.json');controller=c.read_json(out/'controller.json')
    require(run['schema_version']==2 and run['reprollm_version']=='0.7.0'
            and run['status']=='completed' and run['exit_code']==0, 'Unexpected lifecycle recorder outcome.')
    require(controller['run_id']==run['run_id'] and controller['scenario']==scenario and controller['all_passed'], 'Lifecycle controller mismatch.')
    require(controller['pre_run_git_clean'] and controller['committed_input_snapshots_verified']
            and controller['recorded_git_dirty']==run['code']['dirty'], 'Git input/capture phase mismatch.')
    if run['code']['patch_file'] is not None:
        require('sha256:'+c.digest(local_file(out/'run',run['code']['patch_file']))==run['code']['patch_sha256'], 'Recorded Git patch hash mismatch.')
    baseline={}
    for item in (run['manifest'],run['lock'],*run['files']):
        snapshot=local_file(out/'run',item['snapshot']);public=local_file(out/'inputs',item['path'])
        require(item['sha256']=='sha256:'+c.digest(snapshot) and snapshot.read_bytes()==public.read_bytes(), 'Lifecycle input snapshot differs from its public copy.')
        baseline[item['path']]=c.digest(snapshot)
    for item in run['artifacts']:
        require(item['sha256']=='sha256:'+c.digest(local_file(out/'outputs',item['path'])), 'Lifecycle output artifact hash mismatch.')
    source=c.read_json(out/'inputs/recorder-source.json');witness=c.read_json(out/'runtime-witness.json')
    require(source==c.read_json(ROOT/SOURCE_IDENTITY) and witness['module_version']==source['module_version']
            and witness['installed_distribution_version']==source['installed_distribution_version']
            and witness['module_file']=='assets/recorder-source/reprollm/__init__.py'
            and witness['module_sha256']==next(v['sha256'] for v in source['files'] if v['name']=='reprollm/__init__.py'), 'Lifecycle source identity/witness mismatch.')
    manifest=c.read_json(out/'inputs/reprollm.yaml')
    require(manifest['custom']==dict(scenario=scenario,defense='D0')
            and flag(run['command']['argv'],'--scenario')==scenario
            and flag(run['command']['argv'],'--defense')=='D0', 'Lifecycle actual command mismatch.')
    observations=run['bindings_observed']['custom.defense']
    require({v['source']['type'] for v in observations}=={'cli','config','env'}
            and all(v['value']=='D0' for v in observations),'CLI/config/environment observations are incomplete.')
    result=c.read_json(out/'outputs/raw/result.json')
    require(result['all_passed'] and result['scenario']==scenario and result['reprollm_run_id']==run['run_id']
            and result['new_model_generations']==0 and result['consumed_values']==dict(cli='D0',config='D0',env='D0'), 'Lifecycle driver result mismatch.')
    snapshots={}
    for name,item in result['snapshots'].items():
        path=local_file(out/'outputs',item['path']);require(c.digest(path)==item['sha256'],'Intermediate snapshot hash mismatch.')
        snapshots[name]=path.read_bytes()
    require(snapshots['before-rules.yaml']==(out/'inputs/.reprollm/project-rules.yaml').read_bytes()
            and snapshots['before-lock.json']==(out/'inputs/reprollm.lock').read_bytes(),'Intermediate baseline was replaced.')
    changed=[]
    final={'.reprollm/project-rules.yaml':hashlib.sha256(snapshots['final-rules.yaml']).hexdigest(),
           'reprollm.lock':hashlib.sha256(snapshots['final-lock.json']).hexdigest()}
    for name,digest in baseline.items():
        if name in final and final[name]!=digest:changed.append(name)
    require(sorted(changed)==controller['expected_input_changes'],'Independent input-change inventory mismatch.')
    check_input_capture(run,sorted(changed))
    for name,digest in result['immutable_input_hashes'].items():
        require(c.digest(local_file(out/'inputs',name))==digest,'Immutable experiment input changed.')
    commands={v['label']:v for v in result['commands']}
    require(len(commands)==len(result['commands'])==controller['commands']
            and all(v['actual_exit']==v['expected_exit'] for v in commands.values()), 'CLI command outcomes disagree.')
    def exit_code(label,value):
        require(commands[label]['actual_exit']==value and commands[label]['argv'][0]=='reprollm',f'Unexpected CLI exit: {label}')
    before=rules(snapshots['before-rules.yaml']);after=rules(snapshots['final-rules.yaml'])
    require(json.loads(commands['before-list']['stdout'])==before,'Actual rule inspection disagrees with captured baseline.')
    if scenario=='roundtrip':
        require(set(commands)=={'before-list','fresh-before','remove','removed-list','removed-show','stale-after-remove',
             'refresh-inactive','restore','restored-list','restored-show','stale-after-restore','duplicate-refused','refresh-restored','fresh-final'}, 'Incomplete roundtrip command coverage.')
        archive=json.loads(snapshots['archive-original.json'])
        original=next(v for v in before if v['id']=='project.defense')
        require(archive['archive_id']==content_id(archive)==result['archive_id'] and archive['rule']==original==result['original_rule'], 'Original complete rule or archive content ID changed.')
        require(before==after==rules(snapshots['restored-rules.yaml'])
                and not any(v['id']=='project.defense' for v in rules(snapshots['removed-rules.yaml'])), 'Removal/restoration lost original semantics.')
        require(json.loads(commands['removed-list']['stdout'])==rules(snapshots['removed-rules.yaml'])
                and json.loads(commands['restored-list']['stdout'])==before,'CLI inspection differs from intermediate snapshots.')
        require(json.loads(commands['removed-show']['stdout'])['state']=='inactive'
                and json.loads(commands['restored-show']['stdout'])['state']=='active-identical','Archive states are not derived from active rules.')
        for label,value in [('fresh-before',0),('remove',0),('restore',0),('stale-after-remove',1),('stale-after-restore',1),('duplicate-refused',2),('fresh-final',0)]:exit_code(label,value)
    else:
        original=c.read_json(out/'inputs/inputs/original-archive.json');archive=json.loads(snapshots['archive-input.json'])
        require(original['archive_id']==content_id(original)==result['archive_id'] and original['rule']==result['original_rule'], 'Original recovery backup identity mismatch.')
        require(snapshots['before-rules.yaml']==snapshots['final-rules.yaml']
                and snapshots['before-lock.json']==snapshots['final-lock.json'],'Expected refusal rewrote rules or lock.')
        exit_code('restore-refused',2)
        if scenario=='conflict':
            require(set(commands)=={'before-list','restore-refused','builtin-remove-refused','conflict-show'},'Incomplete conflict coverage.')
            require(archive==original and any(v['id']==original['rule']['id'] and v!=original['rule'] for v in before),'Fixture lacks an actual conflicting rule.')
            require(json.loads(commands['conflict-show']['stdout'])['state']=='conflict','Wrong conflict inspection state.')
            exit_code('builtin-remove-refused',2)
        else:
            require(set(commands)=={'before-list','restore-refused'} and content_id(archive)!=archive['archive_id']
                    and archive['rule']==original['rule'],'Fixture lacks the declared controlled archive change.')
            require('content does not match' in commands['restore-refused']['stderr'],'Missing actual archive-integrity refusal.')
    archive_output=out/'outputs/.reprollm/rule-archives'/(result['archive_id']+'.json')
    require(archive_output.read_bytes()==snapshots['archive-original.json' if scenario=='roundtrip' else 'archive-input.json'],'Recovery archive was rewritten.')
    require(run['run_id'] in (out/'REPRODUCIBILITY.md').read_text(),'Selected lifecycle export mismatch.')
    return dict(scenario=scenario,run_id=run['run_id'],all_passed=True,commands_checked=len(commands),
                expected_input_changes=sorted(changed),new_model_generations=0)


def verify_published(root):
    root=Path(root);require(root.is_dir(),'Published lifecycle evidence is missing.')
    records=[verify_case(root/scenario,scenario) for scenario in ('roundtrip','conflict','tampered')]
    return dict(all_passed=True,records=records,cpu_recordings=3,new_model_generations=0)
