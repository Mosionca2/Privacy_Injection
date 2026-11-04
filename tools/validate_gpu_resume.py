"""Capture a prepared GPU condition, optionally interrupting after real progress."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
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


def scientific_child(process: subprocess.Popen, workspace: Path, argv: list[str]) -> int:
    """Find exactly one live, immediate child with our command, directory and session."""
    if sys.platform != 'linux' or process.poll() is not None:
        raise RuntimeError('A live owned Linux recorder is required.')
    children = Path(f'/proc/{process.pid}/task/{process.pid}/children').read_text().split()
    matches = []
    for value in children:
        pid = int(value)
        proc = Path('/proc') / value
        try:
            command = [os.fsdecode(v) for v in (proc/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')]
            parent = next(line.split()[1] for line in (proc/'status').read_text().splitlines()
                          if line.startswith('PPid:'))
            if (command == argv and int(parent) == process.pid
                    and (proc/'cwd').resolve(strict=True) == workspace.resolve()
                    and os.getpgid(pid) == process.pid and os.getsid(pid) == process.pid):
                matches.append(pid)
        except (FileNotFoundError, ProcessLookupError):
            continue
    if len(matches) != 1 or process.poll() is not None:
        raise RuntimeError('Scientific child ownership is absent or ambiguous; refusing to signal.')
    return matches[0]


def kill_scientific_child(process: subprocess.Popen, workspace: Path, argv: list[str]) -> None:
    """Use a Linux process descriptor so a reused numeric PID cannot be signalled."""
    pid = scientific_child(process, workspace, argv)
    libc = ctypes.CDLL(None, use_errno=True)
    if hasattr(libc, 'pidfd_open') and hasattr(libc, 'pidfd_send_signal'):
        open_fd = lambda: libc.pidfd_open(pid, 0)
        send = lambda fd: libc.pidfd_send_signal(fd, signal.SIGKILL, None, 0)
    elif platform.machine() == 'x86_64':
        # Stable x86_64 Linux UAPI numbers, also checked against the execution host's headers.
        # Older libc/Python may lack wrappers even though the running kernel supports them.
        libc.syscall.restype = ctypes.c_long
        open_fd = lambda: libc.syscall(434, pid, 0)
        send = lambda fd: libc.syscall(424, fd, signal.SIGKILL, ctypes.c_void_p(), 0)
    else:
        raise RuntimeError('Linux process-descriptor support is required for child SIGKILL.')
    fd = open_fd()
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'Cannot open the owned child process descriptor.')
    try:
        if scientific_child(process, workspace, argv) != pid:
            raise RuntimeError('Child ownership changed before signalling.')
        if send(fd) != 0:
            raise OSError(ctypes.get_errno(), 'Cannot signal the owned child process descriptor.')
    finally:
        os.close(fd)


def kill_after_progress(process, results, stop_after, expected, workspace, argv,
                        *, timeout=900, interval=.01):
    if not 0 < stop_after < expected:
        raise ValueError('The interruption point must lie inside the workload.')
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        completed = len(sample_rows(results))
        if completed >= expected:
            raise RuntimeError('The workload finished before interruption.')
        if completed >= stop_after:
            kill_scientific_child(process, workspace, argv)
            return completed
        if time.monotonic() >= deadline:
            raise TimeoutError('No sufficient progress before child SIGKILL deadline.')
        time.sleep(interval)
    raise RuntimeError('The recorder exited before child SIGKILL.')


def capture(workspace: Path, gpu_index: int, name: str, expected: int,
            interrupt_after: int | None, timeout: int, min_free_mib: int,
            source_recorder: bool = False, child_sigkill: bool = False) -> dict:
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
    if child_sigkill and (interrupt_after is None or not source_recorder):
        raise ValueError('Child SIGKILL requires a fresh interrupted source-recorder workload.')
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
    if source_recorder:
        from tools.validate_source_recorder import (
            check_input_capture, recorder_witness, runtime_env, verify_payload,
        )
        document = c.read_json(workspace / 'recorder-source.json')
        verify_payload(workspace, document)
        env = runtime_env(True, gpu_index)
        witness = recorder_witness(workspace, document, True, env)
        c.write_json(raw / (name + '.runtime-witness.json'), witness)
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
                sent_at = (kill_after_progress(process, output, interrupt_after, expected, workspace, argv,
                                              timeout=timeout) if child_sigkill else
                           interrupt_after_progress(process, output, interrupt_after, expected, timeout=timeout))
                c.write_json(raw / (name + '.progress.json'), dict(schema_version=1, observed_samples=sent_at))
            launcher_exit = process.wait(timeout=timeout)
        finally:
            cleanup_owned(process)
    created = [p for p in set((workspace / '.reprollm/runs').glob('*')) - before if p.is_dir()]
    if len(created) != 1:
        raise ValueError('Expected one genuine ReproLLM recording.')
    run = c.read_json(created[0] / 'run.json')
    if source_recorder:
        if run['schema_version'] != 2 or run['reprollm_version'] != document['module_version']:
            raise ValueError('The recovery attempt did not use the pinned schema-2 recorder.')
        check_input_capture(run, [])
        verify_payload(workspace, document)
    rows = sample_rows(output, final=True)
    if not output.read_bytes().startswith(initial_bytes):
        raise ValueError('Resume changed existing result bytes.')
    if run['code']['dirty']:
        raise ValueError('The actual captured Git tree was not clean.')
    if interrupt_after is not None:
        if run['status'] != 'interrupted' or not run['exit_code'] or not launcher_exit or not 0 < len(rows) < expected:
            raise ValueError('No valid interrupted partial workload was observed.')
        if child_sigkill and (run['exit_code'] != -signal.SIGKILL or launcher_exit != 247):
            raise ValueError('Expected actual child SIGKILL and the corresponding CLI exit 247.')
    elif run['status'] != 'completed' or run['exit_code'] != 0 or launcher_exit != 0 or len(rows) != expected:
        raise ValueError('The genuine GPU workload did not complete with full coverage.')
    result = dict(schema_version=1, run_id=run['run_id'], status=run['status'], child_exit_code=run['exit_code'],
        launcher_exit_code=launcher_exit, recorded_commit=run['code']['commit'], git_dirty=False,
        expected_samples=expected, completed_before=len(initial), completed_after=len(rows),
        new_completed_samples=len(rows)-len(initial), signalled_after_samples=sent_at,
        original_result_prefix_unchanged=True, gpu_index=gpu_index)
    if source_recorder:
        result.update(source_module_version=run['reprollm_version'], run_schema_version=2,
                      source_commit=document['source_commit'], source_payload_unchanged=True,
                      input_baseline_phase=run['input_capture']['baseline_phase'])
    if child_sigkill:
        result.update(signal_target='owned_immediate_scientific_child', signal='SIGKILL',
                      process_descriptor_used=True)
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
    p.add_argument('--source-recorder', action='store_true')
    p.add_argument('--child-sigkill', action='store_true')
    a = p.parse_args()
    print(json.dumps(capture(a.workspace, a.gpu_index, a.name, a.expected_samples,
                             a.interrupt_after, a.timeout, a.min_free_mib, a.source_recorder,
                             a.child_sigkill), sort_keys=True))
