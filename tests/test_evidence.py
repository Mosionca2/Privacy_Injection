import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.verify_evidence import check_capture, compare_recovery_records, reconcile
from tools.verify_gpu_tail_recovery import check_tail_recovery

ROOT = Path(__file__).resolve().parents[1]


class PublishedEvidenceGuards(unittest.TestCase):
    def tail_recovery_fixture(self, folder):
        root = Path(folder)
        campaign = 'gpu-tail-recovery-validation'
        shutil.copytree(ROOT/'evidence'/campaign, root/'evidence'/campaign)
        shutil.copytree(ROOT/'reports'/campaign, root/'reports'/campaign)
        (root/'tools').mkdir()
        shutil.copyfile(ROOT/'tools/repair_result_tail.py',root/'tools/repair_result_tail.py')
        protocol = json.loads((root/'reports'/campaign/'protocol.json').read_text())
        completion = json.loads((root/'reports'/campaign/'comparison.json').read_text())
        stages = {name:check_capture(ROOT,ROOT/'evidence'/campaign/name) for name in protocol['conditions']}
        return root, completion, stages, protocol

    def test_gpu_tail_recovery_binds_real_interruption_to_backup_repair_and_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(check_tail_recovery(*self.tail_recovery_fixture(folder)))

    def test_gpu_tail_recovery_rejects_changed_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.tail_recovery_fixture(folder)
            backup = args[0]/'evidence/gpu-tail-recovery-validation/primary-repair/bundle/damaged.jsonl'
            backup.write_bytes(backup.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError,'byte chain'):
                check_tail_recovery(*args)

    def test_gpu_tail_recovery_rejects_changed_public_input_or_false_kill_target(self):
        with tempfile.TemporaryDirectory() as folder:
            args = self.tail_recovery_fixture(folder)
            path = args[0]/'evidence/gpu-tail-recovery-validation/primary-inspect/inputs/checkpoint.jsonl'
            data = path.read_bytes();path.write_bytes(data+b'changed')
            with self.assertRaisesRegex(ValueError,'differs from snapshot'):
                check_tail_recovery(*args)
            path.write_bytes(data)
            path = args[0]/'evidence/gpu-tail-recovery-validation/primary-interrupted/controller.json'
            value = json.loads(path.read_text());value['signal_target']='recorder'
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'SIGKILL evidence'):
                check_tail_recovery(*args)

    def fixture(self, folder):
        root = Path(folder)
        for name in ('configs', 'data', 'privacy_study'):
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(ROOT / 'model.identity.json', root / 'model.identity.json')
        directory = root / 'evidence/metadata-validation/D0'
        shutil.copytree(ROOT / 'evidence/metadata-validation/D0', directory)
        return root, directory

    def test_valid_published_capture_has_complete_scored_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            root, directory = self.fixture(folder)
            summary, _, rows = check_capture(root, directory)
            self.assertEqual(summary['new_responses'], 64)
            self.assertEqual(summary['status'], 'completed')
            self.assertEqual(len(rows), 64)

    def test_duplicate_success_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root, directory = self.fixture(folder)
            path = directory / 'results.jsonl'
            lines = path.read_text().splitlines()
            path.write_text('\n'.join(lines + [lines[1]]) + '\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate sample'):
                check_capture(root, directory)

    def test_missing_success_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root, directory = self.fixture(folder)
            path = directory / 'results.jsonl'
            path.write_text('\n'.join(path.read_text().splitlines()[:-1]) + '\n')
            with self.assertRaisesRegex(ValueError, 'Incomplete sample coverage'):
                check_capture(root, directory)

    def test_cached_score_disagreeing_with_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root, directory = self.fixture(folder)
            path = directory / 'results.jsonl'
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            rows[1]['scores']['leak'] = not rows[1]['scores']['leak']
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            with self.assertRaisesRegex(ValueError, 'Score mismatch'):
                check_capture(root, directory)

    def test_changed_input_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root, directory = self.fixture(folder)
            (directory / 'run/manifest.yaml').write_text('changed snapshot\n')
            with self.assertRaisesRegex(ValueError, 'Snapshot hash mismatch'):
                check_capture(root, directory)

    def test_resume_counts_retained_rows_once_and_rejects_changed_copy(self):
        identity = {'same': 'condition'}
        first = {'id': 'one', 'reprollm_run_id': 'interrupted', 'output': 'original'}
        second = {'id': 'two', 'reprollm_run_id': 'resumed', 'output': 'new'}
        captures = [({'run_id': 'interrupted'}, identity, {'one': first}),
                    ({'run_id': 'resumed'}, identity, {'one': copy.deepcopy(first), 'two': second})]
        self.assertEqual(reconcile(captures), 2)
        captures[1][2]['one']['output'] = 'changed retained response'
        with self.assertRaisesRegex(ValueError, 'Retained response changed'):
            reconcile(captures)

    def test_recovery_comparison_rejects_mixed_identities_and_changed_old_success(self):
        identity={'defense':'D0'}
        old={'id':'one','reprollm_run_id':'first','output':'A','scores':{'exact':True}}
        new={'id':'two','reprollm_run_id':'resume','output':'B','scores':{'exact':True}}
        partial=({'run_id':'first'},identity,{'one':old})
        resumed=({'run_id':'resume'},identity,{'one':copy.deepcopy(old),'two':new})
        reference=({'run_id':'fresh'},identity,{k:dict(v,reprollm_run_id='fresh') for k,v in resumed[2].items()})
        self.assertEqual(compare_recovery_records(partial,resumed,reference)['completed_responses'],4)
        with self.assertRaisesRegex(ValueError,'scientific identity'):
            compare_recovery_records(partial,resumed,(reference[0],{'defense':'D1'},reference[2]))
        resumed[2]['one']['reprollm_run_id']='resume'
        with self.assertRaisesRegex(ValueError,'retained response'):
            compare_recovery_records(partial,resumed,reference)
