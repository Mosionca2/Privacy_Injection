import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from privacy_study import core as c
from tools.validate_termination import cleanup, owned_child, successful_pair_ids


@unittest.skipUnless(sys.platform == 'linux', 'Linux process ownership is required')
class SignalOwnershipGuards(unittest.TestCase):
    def test_successes_starting_in_the_same_second_use_saved_id_order(self):
        with tempfile.TemporaryDirectory() as folder:
            captures = []
            # Launch order alone cannot determine the product's saved-record order.
            for suffix in ('ffffff', 'aaaaaa'):
                run_id = '20261103T061700Z-' + suffix
                directory = Path(folder) / run_id
                c.write_json(directory / 'run.json', dict(started_at='2026-11-03T06:17:00Z'))
                captures.append((dict(run_id=run_id), directory))
            self.assertEqual(successful_pair_ids(captures),
                             ['20261103T061700Z-aaaaaa', '20261103T061700Z-ffffff'])

    def test_marker_cannot_redirect_a_signal_to_an_unrelated_live_process(self):
        recorder = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
        try:
            marker = dict(pid=unrelated.pid, parent=recorder.pid, nonce='owned-token')
            with self.assertRaisesRegex(ValueError, 'ownership no longer matches'):
                owned_child(recorder, marker, 'owned-token')
            marker['pid'] = os.getpid()
            with self.assertRaisesRegex(ValueError, 'nonce'):
                owned_child(recorder, marker, 'wrong-token')
            # Cleanup's waitpid guard must not signal an unrelated PID either.
            cleanup(recorder, unrelated.pid)
            self.assertIsNone(unrelated.poll())
        finally:
            cleanup(recorder, None)
            unrelated.terminate()
            unrelated.wait(timeout=5)
