import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from tools.validate_gpu_resume import (cleanup_owned, interrupt_after_progress, sample_rows,
                                      kill_after_progress, kill_scientific_child, scientific_child)


class RecoveryControllerTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'linux', 'requires Linux process descriptors')
    def test_child_sigkill_preserves_recorder_and_never_signals_wrong_command_or_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder).resolve()
            output = work/'results.jsonl'
            script = "import time; from pathlib import Path; Path('results.jsonl').write_text('{\"type\":\"sample\",\"id\":\"one\"}\\n'); time.sleep(20)"
            argv = [sys.executable, '-c', script]
            parent = "import subprocess,sys; p=subprocess.Popen(sys.argv[1:]); code=p.wait(); print(code,flush=True)"
            process = subprocess.Popen([sys.executable, '-c', parent, *argv], cwd=work,
                                       stdout=subprocess.PIPE, text=True, start_new_session=True)
            try:
                import time
                deadline = time.monotonic()+5
                while not output.exists():
                    if time.monotonic() > deadline:
                        self.fail('Child failed to report progress.')
                    time.sleep(.01)
                for directory, command in ((work.parent, argv), (work, [sys.executable, '-c', 'wrong'])):
                    with self.assertRaisesRegex(RuntimeError, 'ownership'):
                        kill_scientific_child(process, directory, command)
                self.assertIsNone(process.poll())
                self.assertGreater(scientific_child(process, work, argv), 1)
                self.assertEqual(kill_after_progress(process, output, 1, 4, work, argv, timeout=5), 1)
                stdout, _ = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0)
                self.assertEqual(stdout.strip(), '-9')
                self.assertEqual(len(sample_rows(output, final=True)), 1)
                with self.assertRaisesRegex(RuntimeError, 'live owned'):
                    scientific_child(process, work, argv)
            finally:
                cleanup_owned(process)
                process.stdout.close()

    def test_child_kill_refuses_complete_workload(self):
        class OwnedProcess:
            def poll(self): return None
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'results.jsonl'
            path.write_text('{"type":"sample","id":"one"}\n{"type":"sample","id":"two"}\n')
            with self.assertRaisesRegex(RuntimeError, 'finished'):
                kill_after_progress(OwnedProcess(), path, 1, 2, Path(folder), [], timeout=1)

    def test_inflight_tail_is_not_a_success_and_finalized_tail_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'results.jsonl'
            path.write_text(json.dumps({'type':'sample','id':'first'}) + '\n' + '{"type":"sample"')
            self.assertEqual(set(sample_rows(path)), {'first'})
            with self.assertRaisesRegex(ValueError, 'incomplete line'):
                sample_rows(path, final=True)
            path.write_text((json.dumps({'type':'sample','id':'first'})+'\n')*2)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                sample_rows(path, final=True)

    @unittest.skipUnless(os.name == 'posix', 'controlled SIGTERM validation requires POSIX')
    def test_only_the_owned_running_process_is_interrupted_after_observed_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'results.jsonl'
            script = "import json,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps({'type':'sample','id':'first'})+'\\n'); time.sleep(20)"
            process = subprocess.Popen([sys.executable, '-c', script, str(path)], start_new_session=True)
            try:
                observed = interrupt_after_progress(process, path, 1, 4, timeout=5, interval=.01)
                self.assertEqual(observed, 1)
                self.assertEqual(process.wait(timeout=5), -signal.SIGTERM)
                self.assertEqual(len(sample_rows(path, final=True)), 1)
            finally:
                cleanup_owned(process)

    def test_interruption_at_full_coverage_is_rejected_without_signalling(self):
        class OwnedProcess:
            def poll(self): return None
            def send_signal(self, number): raise AssertionError('Must not signal a completed workload')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'results.jsonl'
            path.write_text(''.join(json.dumps({'type':'sample','id':str(i)})+'\n' for i in range(4)))
            with self.assertRaisesRegex(RuntimeError, 'finished before interruption'):
                interrupt_after_progress(OwnedProcess(), path, 1, 4)
            with self.assertRaisesRegex(ValueError, 'inside'):
                interrupt_after_progress(OwnedProcess(), path, 4, 4)
