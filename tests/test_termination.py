import os
import subprocess
import sys
import unittest

from tools.validate_termination import cleanup, owned_child


@unittest.skipUnless(sys.platform == 'linux', 'Linux process ownership is required')
class SignalOwnershipGuards(unittest.TestCase):
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
