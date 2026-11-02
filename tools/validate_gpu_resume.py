"""Capture a prepared GPU condition, optionally interrupting after real progress."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from privacy_study import core as c
from privacy_study import record


def sample_rows(path: Path, *, final: bool = False) -> dict[str, dict]:
    """Ignore a writer's in-flight tail only while monitoring; finalized data must be whole."""
    if not path.exists():
        return {}
    data = path.read_bytes()
    if final and data and not data.endswith(b'\n'):
        raise ValueError('Finalized output has an incomplete line; preserve and inspect it.')
    rows = {}
    for line in data.splitlines(keepends=True):
        if not line.endswith(b'\n'):
            break
        value = json.loads(line)
        if value['type'] == 'sample':
            if value['id'] in rows:
                raise ValueError('Duplicate successful sample.')
            rows[value['id']] = value
    return rows


def interrupt_after_progress(
    process: subprocess.Popen, results: Path, stop_after: int, expected: int,
    *, timeout: float = 900, interval: float = 0.05,
) -> int:
    """Signal only the supplied owned recorder, after observing an incomplete real workload."""
    if not 0 < stop_after < expected:
        raise ValueError('The interruption point must lie inside the workload.')
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        completed = len(sample_rows(results))
        if completed >= expected:
            raise RuntimeError('The workload finished before interruption; this is not a recovery test.')
        if completed >= stop_after:
            process.send_signal(signal.SIGTERM)
            return completed
        if time.monotonic() >= deadline:
            raise TimeoutError('No sufficient real progress before the interruption deadline.')
        time.sleep(interval)
    raise RuntimeError('The recorder exited before the requested interruption point.')


def cleanup_owned(process: subprocess.Popen) -> None:
    """The caller creates a new session; cleanup cannot target an unrelated process group."""
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.getpgid(process.pid) != process.pid:
            raise RuntimeError('Refusing cleanup of an unowned process group.')
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def capture(workspace: Path, gpu_index: int, name: str, expected: int,
            interrupt_after: int | None, timeout: int, min_free_mib: int) -> dict:
    workspace = workspace.resolve()
    if os.name != 'posix':
        raise ValueError('This controlled signal validation requires a POSIX host.')
    if not name or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for ch in name):
        raise ValueError('Use a simple capture label.')
    raw = workspace / 'raw'
    raw.mkdir(exist_ok=True)
    target = raw / (name + '.controller.json')
    if target.exists():
        raise ValueError('A capture with this label already exists; preserve its evidence.')
    output = raw / 'results.jsonl'
    initial = sample_rows(output, final=True)
    initial_bytes = output.read_bytes() if output.exists() else b''
    if len(initial) >= expected:
        raise ValueError('This workload is already complete; do not create an empty model recording.')
    if interrupt_after is not None and (initial or not 0 < interrupt_after < expected):
        raise ValueError('Interrupt only a fresh workload, at a point inside its coverage.')
    free = subprocess.check_output(['nvidia-smi', f'--id={gpu_index}', '--query-gpu=memory.free',
                                    '--format=csv,noheader,nounits'], text=True)
    if int(free.strip()) < min_free_mib:
        raise RuntimeError('Insufficient currently free GPU memory; reconsider scheduling.')
    cli = Path(sys.executable).with_name('reprollm')
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu_index), HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
               TOKENIZERS_PARALLELISM='false', PYTHONUNBUFFERED='1')
    env.pop('PYTHONPATH', None)
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
    record.command([cli, 'lock', '.', '--check'], workspace, env=env)
    if record.command(['git', 'status', '--porcelain'], workspace).stdout.strip():
        raise ValueError('Commit the actual recording inputs before execution.')
    declaration = c.read_json(workspace / 'reprollm.yaml')
    argv = shlex.split(declaration['execution']['command'])
    if not argv or argv[0] not in ('python', 'python3', sys.executable):
        raise ValueError('This validation expects the prepared Python study command.')
    argv[0] = sys.executable
    before = set((workspace / '.reprollm/runs').glob('*'))
    sent_at = None
    with (raw / (name + '.stdout')).open('w') as stdout, (raw / (name + '.stderr')).open('w') as stderr:
        process = subprocess.Popen([str(cli), 'run', '--name', name, '--capture-output', '--'] + argv,
            cwd=workspace, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            if interrupt_after is not None:
                sent_at = interrupt_after_progress(process, output, interrupt_after, expected, timeout=timeout)
            launcher_exit = process.wait(timeout=timeout)
        finally:
            cleanup_owned(process)
    created = [p for p in set((workspace / '.reprollm/runs').glob('*')) - before if p.is_dir()]
    if len(created) != 1:
        raise ValueError('Expected one genuine ReproLLM recording.')
    run = c.read_json(created[0] / 'run.json')
    rows = sample_rows(output, final=True)
    if not output.read_bytes().startswith(initial_bytes):
        raise ValueError('Resume changed existing result bytes.')
    if run['code']['dirty']:
        raise ValueError('The actual captured Git tree was not clean.')
    if interrupt_after is not None:
        if run['status'] != 'interrupted' or not run['exit_code'] or not launcher_exit or not 0 < len(rows) < expected:
            raise ValueError('No valid interrupted partial workload was observed.')
    elif run['status'] != 'completed' or run['exit_code'] != 0 or launcher_exit != 0 or len(rows) != expected:
        raise ValueError('The genuine GPU workload did not complete with full coverage.')
    result = dict(schema_version=1, run_id=run['run_id'], status=run['status'], child_exit_code=run['exit_code'],
        launcher_exit_code=launcher_exit, recorded_commit=run['code']['commit'], git_dirty=False,
        expected_samples=expected, completed_before=len(initial), completed_after=len(rows),
        new_completed_samples=len(rows)-len(initial), signalled_after_samples=sent_at,
        original_result_prefix_unchanged=True, gpu_index=gpu_index)
    c.write_json(target, result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--gpu-index', type=int, required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--expected-samples', type=int, required=True)
    p.add_argument('--interrupt-after', type=int)
    p.add_argument('--timeout', type=int, default=900)
    p.add_argument('--min-free-mib', type=int, default=24576)
    a = p.parse_args()
    print(json.dumps(capture(a.workspace, a.gpu_index, a.name, a.expected_samples,
                             a.interrupt_after, a.timeout, a.min_free_mib), sort_keys=True))
