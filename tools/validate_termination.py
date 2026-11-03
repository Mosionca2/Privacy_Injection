"""Exercise real ReproLLM forced-termination boundaries with owned Linux CPU fixtures."""
import argparse
from contextlib import contextmanager
import ctypes
from importlib import metadata
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from tools.ci_verify import SOURCE_IDENTITY, check_consumer, directory_hashes
from tools.verify_evidence import require

CHILD = '''import argparse, json, os, time
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--case', required=True)
a = p.parse_args()
raw = Path('raw'); raw.mkdir(exist_ok=True)
value = dict(run_id=os.environ['REPROLLM_RUN_ID'], case=a.case,
             work_units=1, checksum=sum(range(1000)))
(raw/'artifact.json').write_text(json.dumps(value)+'\\n')
marker = dict(value, pid=os.getpid(), parent=os.getppid(),
              nonce=os.environ['BOUNDARY_NONCE'])
(raw/'ready.tmp').write_text(json.dumps(marker))
(raw/'ready.tmp').replace(raw/'ready.json')
print(json.dumps(value), flush=True)
if a.case != 'success':
    time.sleep(180)
(raw/'completion.json').write_text(json.dumps(value)+'\\n')
'''


@contextmanager
def adopt_orphans():
    """Reap our fixture after killing its recorder; do not leave an orphan behind."""
    require(sys.platform == 'linux', 'This validation requires Linux process ownership checks.')
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    require(libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0,
            'Cannot query Linux child-subreaper state.')
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'Cannot adopt the owned recorder child.')
    try:
        yield
    finally:
        if libc.prctl(36, previous.value, 0, 0, 0) != 0:
            raise RuntimeError('Cannot restore child-subreaper state.')


def owned_child(process, marker, nonce):
    """Reject untrusted/stale markers before any signal is sent."""
    require(process.poll() is None and marker['nonce'] == nonce,
            'Recorder exited or child ownership nonce differs.')
    pid = marker['pid']
    require(type(pid) is int and pid > 1 and marker['parent'] == process.pid,
            'Marker does not identify the owned recorder child.')
    status = (Path('/proc') / str(pid) / 'status').read_text()
    parent = next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:'))
    require(int(parent) == process.pid and os.getpgid(pid) == process.pid
            and os.getsid(pid) == process.pid, 'Child process ownership no longer matches.')
    return pid


def cleanup(process, child_pid):
    """Stop only our recorder group or a child adopted and owned by this process."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            require(os.getpgid(process.pid) == process.pid, 'Refuse to signal a foreign process group.')
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
    if child_pid is None:
        return
    try:
        if os.getpgid(child_pid) != process.pid:
            return
    except ProcessLookupError:
        return
    # waitpid is an ownership check: a reaped or unrelated PID is never signalled.
    try:
        reaped, _ = os.waitpid(child_pid, os.WNOHANG)
    except ChildProcessError:
        return
    if reaped:
        return
    os.kill(child_pid, signal.SIGTERM)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if os.waitpid(child_pid, os.WNOHANG)[0]:
            return
        time.sleep(.02)
    os.kill(child_pid, signal.SIGKILL)
    os.waitpid(child_pid, 0)


def call(work, env, label, args, expected=0):
    cli = Path(sys.executable).with_name('reprollm')
    result = subprocess.run([str(cli), *args], cwd=work, env=env,
                            capture_output=True, text=True, timeout=120)
    (work / 'raw' / (label + '.stdout')).write_text(result.stdout)
    (work / 'raw' / (label + '.stderr')).write_text(result.stderr)
    require(result.returncode == expected, f'{label} exited {result.returncode}; inspect saved output.')
    return result.stdout


def prepare(work, case, source, identity):
    work.mkdir(parents=True, exist_ok=False)
    (work / 'raw').mkdir()
    (work / 'fixture.py').write_text(CHILD)
    (work / '.gitignore').write_text('raw/\nassets/\n.reprollm/runs/\n__pycache__/\n')
    c.write_json(work / 'reprollm.yaml', dict(schema_version=1,
        project=dict(name='forced_termination_fixture'),
        experiment=dict(name=case, profiles=[]),
        custom=dict(probe=case), bindings={'custom.probe': dict(cli='--case')},
        execution=dict(command=f'python fixture.py --case {case}', config_files=['fixture.py']),
        artifacts=dict(outputs=['raw/artifact.json', 'raw/completion.json'])))
    # Keep installed 0.6.1 and process-selected source 0.7.0 separate.
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL') if k in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    if source is not None:
        for item in identity['files']:
            target = work / 'assets/recorder-source' / item['name']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / 'src' / item['name'], target)
            require(c.digest(target) == item['sha256'], 'Materialized recorder source changed.')
        env['PYTHONPATH'] = 'assets/recorder-source'
    call(work, env, 'rules', ['rules', 'add', '--id', 'project.probe', '--field', 'custom.probe',
                            '--severity', 'CRITICAL', '--reason', 'The CPU scenario must match its command.',
                            '--cli=--case'])
    call(work, env, 'lock', ['lock', '.', '--offline'])
    call(work, env, 'lock-check', ['lock', '.', '--check'])
    for args in (['git', 'init', '-q'], ['git', 'add', '.gitignore', 'fixture.py', 'reprollm.yaml',
                  'reprollm.lock', '.reprollm/project-rules.yaml'],
                 ['git', '-c', 'user.name=CPU fixture', '-c', 'user.email=fixture@example.invalid',
                  'commit', '-qm', 'test: prepare owned CPU termination fixture']):
        subprocess.run(args, cwd=work, check=True, capture_output=True)
    return env


def capture(work, env, case, label):
    nonce = secrets.token_hex(16)
    env = dict(env, BOUNDARY_NONCE=nonce)
    ready = work / 'raw/ready.json'
    ready.unlink(missing_ok=True)
    cli = Path(sys.executable).with_name('reprollm')
    before = set((work / '.reprollm/runs').glob('*'))
    child_pid = None
    with (work / 'raw' / (label+'.stdout')).open('w') as out, (work / 'raw' / (label+'.stderr')).open('w') as err:
        process = subprocess.Popen([str(cli), 'run', '--name', label, '--capture-output', '--',
                                    sys.executable, 'fixture.py', '--case', case],
                                   cwd=work, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            deadline = time.monotonic() + 60
            while not ready.exists():
                require(process.poll() is None, 'Recorder exited before CPU child readiness.')
                require(time.monotonic() < deadline, 'No owned child progress before deadline.')
                time.sleep(.02)
            marker = c.read_json(ready)
            if case != 'success':
                child_pid = owned_child(process, marker, nonce)
                run_path = work / '.reprollm/runs' / marker['run_id'] / 'run.json'
                require(c.read_json(run_path)['status'] == 'running', 'Signal must follow a real running capture.')
                if case == 'child-kill':
                    os.kill(child_pid, signal.SIGKILL)
                else:
                    process.kill()
            launcher_exit = process.wait(timeout=120)
        finally:
            cleanup(process, child_pid)
    created = set((work / '.reprollm/runs').glob('*')) - before
    require(len(created) == 1, 'Expected exactly one genuine CPU recording.')
    directory = created.pop()
    run = c.read_json(directory / 'run.json')
    require(marker['nonce'] == nonce and marker['case'] == case
            and marker['run_id'] == run['run_id'] and marker['work_units'] == 1
            and marker['checksum'] == 499500, 'Missing actual child progress.')
    expected_status, expected_exit = {'success': ('completed', 0), 'child-kill': ('interrupted', -9),
                                      'recorder-kill': ('running', None)}[case]
    require(run['status'] == expected_status and run['exit_code'] == expected_exit,
            'Recorded termination status/exit differs from the contract.')
    require(launcher_exit == (0 if case == 'success' else 247 if case == 'child-kill' else -9),
            'Unexpected actual CLI process exit.')
    require((work / 'raw/completion.json').exists() == (case == 'success'), 'Incorrect completion evidence.')
    if case == 'success':
        require(c.read_json(work / 'raw/completion.json')['run_id'] == run['run_id'],
                'Completion belongs to an earlier attempt.')
    if case == 'recorder-kill' and run['schema_version'] == 2:
        checks = run['input_capture']['checks']
        require(run['manifest'] is not None and run['lock'] is not None and bool(checks)
                and all(v['change'] == 'unknown' and v['after']['availability'] == 'unavailable'
                        for v in checks), 'Unfinished input checks must preserve unknown final state.')
    return dict(run_id=run['run_id'], status=run['status'], child_exit_code=run['exit_code'],
                launcher_exit_code=launcher_exit, schema_version=run['schema_version'],
                recorder_version=run['reprollm_version'], recorded_commit=run['code']['commit'],
                input_baseline_saved=run['manifest'] is not None, child_work_units=1,
                owned_child_cleanup_complete=True,
                recorder_metadata_finalized=run['environment'] is not None), directory


def successful_pair_ids(captures):
    """Use the documented saved start-time/run-ID order, including same-second ties."""
    return [record['run_id'] for record, directory in sorted(captures, key=lambda item: (
        c.read_json(item[1] / 'run.json')['started_at'], item[0]['run_id']))]


def inspect(work, env, captures, source):
    before = directory_hashes(work / '.reprollm/runs')
    rows = json.loads(call(work, env, 'list', ['runs', 'list', '--json']))
    require({row['run_id'] for row in rows} == {r['run_id'] for r, _ in captures}, 'List lost a valid record.')
    for record, directory in captures:
        shown = call(work, env, record['run_id']+'-show', ['runs', 'show', record['run_id'], '--json'])
        require(shown == (directory / 'run.json').read_text(), 'Show rewrote saved evidence.')
        call(work, env, record['run_id']+'-export', ['export', '.', '--run', record['run_id'],
                                                  '--output', 'raw/'+record['run_id']+'.md'])
        require(record['run_id'] in (work / 'raw' / (record['run_id']+'.md')).read_text(), 'Wrong selected export.')
        if source:
            for outcome in ('success', 'failure'):
                matches = json.loads(call(work, env, record['run_id']+'-'+outcome,
                                          ['runs', 'list', '--outcome', outcome, '--json']))
                expected = record['status'] == ('completed' if outcome == 'success' else 'interrupted')
                require((record['run_id'] in {r['run_id'] for r in matches}) == expected,
                        'Running or interrupted record was incorrectly classified by outcome.')
    if len(captures) == 2:
        args = ['diff', str(captures[0][1]/'run.json'), str(captures[1][1]/'run.json'), '--format', 'json']
    else:
        args = ['diff', str(captures[0][1]/'run.json'), str(captures[0][1]/'run.json'), '--format', 'json']
    diff = json.loads(call(work, env, 'diff', args))
    if len(captures) == 1:
        require(diff['changes'] == [], 'Self-diff should preserve archived state.')
    if source and len(captures) == 2:
        selected = json.loads(call(work, env, 'latest-successful', ['diff', '--latest-successful', '--format', 'json']))
        require([selected[k]['ref'] for k in ('a', 'b')] == successful_pair_ids(captures),
                'Latest-successful diff chose the wrong attempts.')
    require(before == directory_hashes(work / '.reprollm/runs'), 'Inspection changed historical run bytes.')


def validate(source, workspace, output):
    validator_hash = c.digest(Path(__file__))
    identity = c.read_json(ROOT / SOURCE_IDENTITY)
    consumer = check_consumer(source, identity)
    workspace.mkdir(parents=True, exist_ok=False)
    engines = []
    with adopt_orphans():
        for engine in ('released', 'source'):
            records = []
            for case in ('child-kill', 'recorder-kill', 'success'):
                work = workspace / engine / case
                env = prepare(work, case, source if engine == 'source' else None, identity)
                captured = [capture(work, env, case, case+'-'+str(i)) for i in range(2 if case == 'success' else 1)]
                inspect(work, env, captured, engine == 'source')
                for record, _ in captured:
                    require(record['schema_version'] == (2 if engine == 'source' else 1)
                            and record['recorder_version'] == ('0.7.0' if engine == 'source' else '0.6.1'),
                            'The actual recorder version/schema differs from the pinned engine.')
                    records.append(dict(case=case, **record))
                print(json.dumps(dict(event='cpu_boundary_checked', engine=engine, case=case)), flush=True)
            engines.append(dict(engine=engine, records=records, inspection_preserved_all_run_bytes=True,
                                outcome_filters_checked=engine == 'source'))
    require(c.digest(Path(__file__)) == validator_hash, 'Validation controller changed during execution.')
    result = dict(schema_version=1, all_passed=True, consumer=consumer, engines=engines,
                  validator_sha256=validator_hash, fixture_sha256=c.digest(work / 'fixture.py'),
                  python_version=sys.version.split()[0], installed_distribution_version=metadata.version('reprollm'),
                  actual_cpu_recordings=8, new_model_generations=0,
                  scope='Linux owned CPU fixtures: child SIGKILL, recorder SIGKILL and two successful controls per engine; no GPU/model execution or power-loss simulation.')
    c.write_json(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consumer-source', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    validate(args.consumer_source.resolve(), args.workspace.resolve(), args.output.resolve())
