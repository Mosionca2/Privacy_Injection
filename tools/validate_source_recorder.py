"""Validate a pinned source recorder on prepared local GPU conditions."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from privacy_study import record
from tools.validate_gpu_resume import cleanup_owned, sample_rows


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_input_capture(run, expected_changes):
    capture = run.get('input_capture')
    if run['schema_version'] == 1:
        require(capture is None and not expected_changes, 'Legacy input phases must remain unknown.')
        return None
    require(run['schema_version'] == 2 and capture
            and capture['baseline_phase'] == 'pre_child' and capture['check_phase'] == 'post_child'
            and capture['consumption'] == 'unverified', 'Unexpected input capture phases or consumption.')
    checks = capture['checks']
    require(len({v['path'] for v in checks}) == len(checks), 'Duplicate input checks.')
    refs = [run.get('manifest'), run.get('lock'), *run.get('files', [])]
    hashes = {v['path']: v['sha256'] for v in refs if v}
    changed = []
    for check in checks:
        before, after = check['before'], check['after']
        if check['path'] in hashes:
            require(before['sha256'] == hashes[check['path']], 'Input baseline no longer matches its saved reference.')
        for fingerprint in (before, after):
            if fingerprint['availability'] == 'present':
                require(fingerprint['sha256'] is not None and type(fingerprint['size_bytes']) is int,
                        'Present input fingerprints require a hash and size.')
            else:
                require(fingerprint['sha256'] is None and fingerprint['size_bytes'] is None,
                        'Absent input fingerprints must not invent content identity.')
        states = before['availability'], after['availability']
        require('unavailable' not in states, 'Unexpected unavailable input check in this bounded case.')
        if states == ('missing', 'present'):
            actual = 'created'
        elif states == ('present', 'missing'):
            actual = 'removed'
        else:
            require(states in (('present', 'present'), ('missing', 'missing')), 'Unexpected fingerprint availability.')
            actual = ('unchanged' if (before['sha256'], before['size_bytes']) ==
                      (after['sha256'], after['size_bytes']) else 'changed')
        require(check['change'] == actual, 'Input change disagrees with fingerprints.')
        if actual != 'unchanged':
            changed.append(check['path'])
    require(set(hashes) <= {v['path'] for v in checks}, 'Missing input baseline checks.')
    require(sorted(changed) == sorted(expected_changes), 'Unexpected input changes.')
    return sorted(changed)


def verify_payload(workspace, document):
    base = Path(workspace) / 'assets/recorder-source'
    for item in document['files']:
        path = (base / item['name']).resolve()
        require(path.is_relative_to(base.resolve()) and c.digest(path) == item['sha256'],
                'Source payload changed; preserve the original source identity.')


def runtime_env(source, gpu=None):
    env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false', PYTHONUNBUFFERED='1')
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
    if source:
        env['PYTHONPATH'] = 'assets/recorder-source'
    else:
        env.pop('PYTHONPATH', None)
    if gpu is not None:
        env['CUDA_VISIBLE_DEVICES'] = str(gpu)
    return env


def mutate_after_progress(process, results, marker, threshold, expected, *, timeout=900):
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        count = len(sample_rows(results))
        require(count < expected, 'Workload completed before diagnostic input change.')
        if count >= threshold:
            c.write_json(marker, dict(schema_version=1, stage='after-child-start',
                                     role='Declared diagnostic input; not read by the scientific runner.'))
            return count
        if time.monotonic() >= deadline:
            raise TimeoutError('No model progress before the diagnostic deadline.')
        time.sleep(.02)
    raise RuntimeError('Recorder exited before diagnostic input change.')


def capture(workspace, gpu, label, expected=64):
    work = Path(workspace).resolve()
    spec = c.read_json(work / 'reports/source-recorder-validation/protocol.json')['conditions'][label]
    source, changes = spec['source_recorder'], spec['expected_input_changes']
    raw = work / 'raw'; raw.mkdir(exist_ok=True)
    require(not (raw / 'controller.json').exists() and not (raw / 'results.jsonl').exists(),
            'Use a fresh prepared condition; preserve earlier attempts.')
    free = subprocess.check_output(['nvidia-smi', f'--id={gpu}', '--query-gpu=memory.free',
                                    '--format=csv,noheader,nounits'], text=True)
    require(int(free.strip()) >= 8192, 'Insufficient currently free GPU memory.')
    env, cli = runtime_env(source, gpu), Path(sys.executable).with_name('reprollm')
    document = c.read_json(work / 'recorder-source.json')
    if source:
        verify_payload(work, document)
    witness_code = (
        'import hashlib,json,reprollm; from pathlib import Path; from importlib import metadata; '
        'p=Path(reprollm.__file__).resolve(); root=Path.cwd().resolve(); '
        "print(json.dumps(dict(module_version=reprollm.__version__,installed_distribution_version=metadata.version('reprollm'),"
        "module_file=p.relative_to(root).as_posix() if p.is_relative_to(root) else 'installed-distribution',"
        "module_sha256=hashlib.sha256(p.read_bytes()).hexdigest())))")
    witness = json.loads(record.command([sys.executable, '-c', witness_code], work, env=env).stdout)
    require(witness['module_version'] == document['module_version']
            and witness['installed_distribution_version'] == document['installed_distribution_version'],
            'Actual module/distribution identity differs from the declaration.')
    if source:
        require(witness['module_file'] == 'assets/recorder-source/reprollm/__init__.py',
                'Source recorder did not load from the materialized pinned package.')
    c.write_json(raw / 'runtime-witness.json', witness)
    record.command([cli, 'lock', '.', '--check'], work, env=env)
    require(not record.command(['git', 'status', '--porcelain'], work).stdout.strip(),
            'Commit all declared inputs before recording.')
    before = set((work / '.reprollm/runs').glob('*'))
    declaration = c.read_json(work / 'reprollm.yaml')
    argv = shlex.split(declaration['execution']['command']); argv[0] = sys.executable
    progress = None
    with (raw / 'launcher.stdout').open('w') as stdout, (raw / 'launcher.stderr').open('w') as stderr:
        process = subprocess.Popen([str(cli), 'run', '--name', label, '--capture-output', '--', *argv],
            cwd=work, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            if changes:
                require(changes == ['probe/declared-input.json'], 'Unexpected diagnostic target.')
                progress = mutate_after_progress(process, raw / 'results.jsonl', work / changes[0], 8, expected)
                c.write_json(raw / 'input-change-event.json', dict(schema_version=1, observed_samples=progress))
            exit_code = process.wait(timeout=900)
        finally:
            cleanup_owned(process)
    created = [p for p in set((work / '.reprollm/runs').glob('*')) - before if p.is_dir()]
    require(len(created) == 1, 'Expected exactly one actual recorder capture.')
    run = c.read_json(created[0] / 'run.json')
    rows = sample_rows(raw / 'results.jsonl', final=True)
    require(exit_code == run['exit_code'] == 0 and run['status'] == 'completed'
            and len(rows) == expected and all(r['reprollm_run_id'] == run['run_id'] for r in rows.values()),
            'Incomplete genuine model execution.')
    require(run['reprollm_version'] == document['module_version']
            and run['schema_version'] == (2 if source else 1), 'Unexpected recorder version/schema.')
    observed_changes = check_input_capture(run, changes)
    if source:
        verify_payload(work, document)
    if not changes:
        require(not run['code']['dirty'], 'Unexpected dirty captured inputs.')
    else:
        require(run['code']['dirty'], 'Expected diagnostic Git change was not retained.')
    result = dict(schema_version=1, run_id=run['run_id'], status=run['status'], child_exit_code=run['exit_code'],
        launcher_exit_code=exit_code, expected_samples=expected, completed_before=0, completed_after=len(rows),
        new_completed_samples=len(rows), recorded_commit=run['code']['commit'],
        git_dirty=run['code']['dirty'], inputs_clean_before_launch=True,
        expected_input_changes=changes, observed_input_changes=observed_changes,
        changed_after_observed_samples=progress, source_payload_unchanged=source,
        missing_input_candidates=[v['path'] for v in (run.get('input_capture') or {}).get('checks', [])
                                  if v['before']['availability'] == 'missing'],
        recorder_module_version=run['reprollm_version'], run_schema_version=run['schema_version'])
    c.write_json(raw / 'controller.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--gpu-index', required=True, type=int)
    parser.add_argument('--condition', required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args.workspace, args.gpu_index, args.condition), sort_keys=True))
