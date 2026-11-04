"""Verify the byte chain from real child SIGKILL through recorded copy repair and resume."""
import json
import shlex

from privacy_study import core as c
from tools.repair_result_tail import canonical_identity, digest, inspect_bytes
from tools.validate_source_recorder import check_input_capture


def check_tail_recovery(root, completion, stages, protocol):
    from tools.verify_evidence import flag, local_file, require

    require(completion['protocol_sha256'] == c.digest(root/'reports/gpu-tail-recovery-validation/protocol.json'),
            'GPU tail recovery protocol changed after execution.')
    require(set(completion['cpu_repairs']) == set(protocol['models']), 'Repair model coverage mismatch.')
    require(completion['completed_responses_published'] == protocol['expected_new_completed_responses']
            and completion['real_gpu_runs'] == protocol['expected_captures'], 'Bounded recovery workload mismatch.')
    for model, repair in completion['cpu_repairs'].items():
        partial, resumed, reference = (stages[model+'-'+stage] for stage in ('interrupted','resumed','reference'))
        directory = local_file(root, partial[0]['evidence'])
        original = (directory/'results.jsonl').read_bytes()
        identity = partial[1]
        controller = c.read_json(directory/'controller.json')
        require(controller['child_exit_code'] == -9 and controller['launcher_exit_code'] == 247
                and controller['signal'] == 'SIGKILL' and controller['process_descriptor_used'] is True
                and controller['signal_target'] == 'owned_immediate_scientific_child'
                and protocol['interrupt_after_observed_samples'] <= controller['signalled_after_samples'] <= len(partial[2]),
                'GPU child SIGKILL evidence mismatch.')
        for capture in (partial, resumed, reference):
            path = local_file(root, capture[0]['evidence'])
            run = c.read_json(path/'run/run.json')
            output = [a for a in run['artifacts'] if a['path'] == 'raw/results.jsonl']
            require(len(output) == 1 and output[0]['sha256'] == 'sha256:'+c.digest(path/'results.jsonl'),
                    'GPU recorded output artifact differs from the published bytes.')
        require(repair['controlled_corruption'] is True and repair['original_interrupted_bytes_preserved'] is True
                and repair['new_model_generations'] == 0 and set(repair['records']) == {'inspect','repair'},
                'Controlled repair scope mismatch.')
        damaged = original + protocol['controlled_tail'].encode()
        plan, prefix, tail = inspect_bytes(damaged, identity)
        require(plan == repair['plan'] and prefix == original, 'Repair plan or original prefix mismatch.')
        source_doc = c.read_json(directory/'recorder-source.json')
        for mode, item in repair['records'].items():
            out = local_file(root, item['evidence'])
            require(out == root/'evidence/gpu-tail-recovery-validation'/(model+'-'+mode),
                    'CPU repair evidence path mismatch.')
            run = c.read_json(out/'run/run.json')
            require(run['run_id'] == item['run_id'] and run['schema_version'] == 2
                    and run['status'] == 'completed' and run['exit_code'] == 0 and not run['code']['dirty'],
                    'CPU repair capture outcome mismatch.')
            check_input_capture(run, [])
            require(c.read_json(out/'recorder-source.json') == source_doc
                    and run['reprollm_version'] == source_doc['module_version'], 'CPU repair recorder identity mismatch.')
            witness = c.read_json(out/'runtime-witness.json')
            require(witness['module_version'] == source_doc['module_version']
                    and witness['installed_distribution_version'] == source_doc['installed_distribution_version']
                    and witness['module_file'] == 'assets/recorder-source/reprollm/__init__.py'
                    and witness['module_sha256'] == next(v['sha256'] for v in source_doc['files']
                                                        if v['name'] == 'reprollm/__init__.py'),
                    'CPU repair runtime witness mismatch.')
            for snapshot in (run['manifest'], run['lock'], *run['files']):
                require(snapshot.get('snapshot') and not snapshot.get('redacted', False), 'Missing CPU input snapshot.')
                path = local_file(out/'run', snapshot['snapshot'])
                require(snapshot['sha256'] == 'sha256:'+c.digest(path), 'CPU repair input snapshot hash mismatch.')
                original_path = snapshot.get('path')
                if original_path:
                    public_input = local_file(out, original_path)
                    if public_input.is_file():
                        require(c.digest(public_input) == c.digest(path), 'CPU repair public input differs from snapshot.')
            manifest = c.read_json(out/'reprollm.yaml')
            declared, actual = shlex.split(manifest['execution']['command']), run['command']['argv']
            for field, option, value in (('mode','--mode',mode),('input_file','--input','inputs/checkpoint.jsonl')):
                require(manifest['custom'][field] == value and flag(declared, option) == flag(actual, option) == value
                        and [v['value'] for v in run['bindings_observed']['custom.'+field]] == [value],
                        'CPU repair actual command/binding mismatch.')
            require((out/'inputs/checkpoint.jsonl').read_bytes() == damaged
                    and canonical_identity(c.read_json(out/'inputs/identity.json')) == canonical_identity(identity),
                    'CPU repair damaged input or trusted identity mismatch.')
            require(c.digest(out/'repair.py') == c.digest(root/'tools/repair_result_tail.py'), 'Repair tool identity mismatch.')
            derivation = c.read_json(out/'inputs/derivation.json')
            require(derivation['interrupted_run_id'] == partial[0]['run_id']
                    and derivation['original_sha256'] == digest(original)
                    and derivation['damaged_sha256'] == digest(damaged)
                    and derivation['controlled_tail'] == protocol['controlled_tail'], 'CPU repair source linkage mismatch.')
            require(run['run_id'] in (out/'REPRODUCIBILITY.md').read_text(), 'CPU selected-run export mismatch.')
            if mode == 'inspect':
                require(not (out/'bundle').exists(), 'Inspection unexpectedly published repaired output.')
                inspection = json.loads((out/'run/stdout.log').read_text())
                require(all(inspection[key] == value for key, value in plan.items()), 'Recorded inspection plan mismatch.')
                continue
            bundle = out/'bundle'
            require((bundle/'damaged.jsonl').read_bytes() == damaged
                    and (bundle/'repaired.jsonl').read_bytes() == prefix
                    and (bundle/'unfinished-tail.bin').read_bytes() == tail,
                    'Repair backup/prefix/tail byte chain mismatch.')
            receipt = c.read_json(bundle/'receipt.json')
            require(all(receipt[key] == value for key, value in plan.items())
                    and receipt['tool_run_id'] == run['run_id'] and receipt['source_modified'] is False,
                    'Repair receipt differs from recomputed bytes.')
            require(flag(actual,'--sha256') == plan['source_sha256']
                    and flag(actual,'--output-directory') == 'raw/bundle', 'Repair invocation did not pin inspected bytes.')
            require({a['path'] for a in run['artifacts']} == {'raw/bundle/'+v for v in
                    ('damaged.jsonl','repaired.jsonl','unfinished-tail.bin','receipt.json')}, 'Missing recorded repair artifacts.')
            for artifact in run['artifacts']:
                require(artifact['sha256'] == 'sha256:'+c.digest(local_file(out, artifact['path'].removeprefix('raw/'))),
                        'Recorded repair output artifact hash mismatch.')
        final = local_file(root, resumed[0]['evidence'])/'results.jsonl'
        require(final.read_bytes().startswith(prefix), 'Installed repaired prefix changed during resume.')
