import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from privacy_study import core as c
from tools.validate_source_recorder import check_input_capture, mutate_after_progress, verify_payload
from tools.validate_gpu_resume import cleanup_owned


class SourceRecorderGuards(unittest.TestCase):
    def record(self):
        before = dict(availability='present', sha256='sha256:'+'a'*64, size_bytes=3)
        return dict(schema_version=2, manifest=dict(path='reprollm.yaml', sha256=before['sha256']),
                    lock=None, files=[], input_capture=dict(baseline_phase='pre_child',
                    check_phase='post_child', consumption='unverified', checks=[dict(
                    path='reprollm.yaml', origin='manifest', before=before,
                    after=copy.deepcopy(before), change='unchanged')]))

    def test_versioned_phases_keep_legacy_unknown_and_source_consumption_unverified(self):
        self.assertEqual(check_input_capture(self.record(), []), [])
        self.assertIsNone(check_input_capture({'schema_version': 1}, []))
        value = self.record(); value['input_capture']['consumption'] = 'verified'
        with self.assertRaisesRegex(ValueError, 'capture phases'):
            check_input_capture(value, [])

    def test_replaced_baseline_hash_is_rejected(self):
        value = self.record()
        value['input_capture']['checks'][0]['before']['sha256'] = 'sha256:'+'b'*64
        with self.assertRaisesRegex(ValueError, 'baseline'):
            check_input_capture(value, ['reprollm.yaml'])

    def test_unexpected_or_inconsistent_input_change_is_rejected(self):
        value = self.record(); check = value['input_capture']['checks'][0]
        check['after']['sha256'] = 'sha256:'+'b'*64
        check['change'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'Unexpected input changes'):
            check_input_capture(value, [])
        self.assertEqual(check_input_capture(value, ['reprollm.yaml']), ['reprollm.yaml'])
        check['change'] = 'unchanged'
        with self.assertRaisesRegex(ValueError, 'fingerprints'):
            check_input_capture(value, [])

    def test_source_payload_changes_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder); target = work / 'assets/recorder-source/reprollm/__init__.py'
            target.parent.mkdir(parents=True); target.write_text('__version__="test"\n')
            document = {'files': [{'name': 'reprollm/__init__.py', 'sha256': c.digest(target)}]}
            verify_payload(work, document)
            target.write_text('changed source\n')
            with self.assertRaisesRegex(ValueError, 'Source payload changed'):
                verify_payload(work, document)

    def test_missing_optional_candidates_remain_visible_without_replacing_real_baselines(self):
        value = self.record()
        missing = dict(availability='missing', sha256=None, size_bytes=None)
        value['input_capture']['checks'].append(dict(path='An inline definition.', origin='declared',
            before=copy.deepcopy(missing), after=copy.deepcopy(missing), change='unchanged'))
        self.assertEqual(check_input_capture(value, []), [])
        value['input_capture']['checks'][0]['before'] = copy.deepcopy(missing)
        value['input_capture']['checks'][0]['after'] = copy.deepcopy(missing)
        with self.assertRaisesRegex(ValueError, 'baseline'):
            check_input_capture(value, [])

    def test_probe_mutates_only_after_owned_child_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder); results = work/'results.jsonl'; marker = work/'marker.json'
            script = "import json,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps({'type':'sample','id':'one'})+'\\n'); time.sleep(1)"
            child = subprocess.Popen([sys.executable, '-c', script, str(results)], start_new_session=True)
            try:
                count = mutate_after_progress(child, results, marker, 1, 4, timeout=5)
                self.assertEqual(count, 1)
                self.assertEqual(json.loads(marker.read_text())['stage'], 'after-child-start')
                self.assertEqual(child.wait(timeout=5), 0)
            finally:
                cleanup_owned(child)
