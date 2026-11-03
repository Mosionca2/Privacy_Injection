import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.verify_evidence import check_capture, reconcile

ROOT = Path(__file__).resolve().parents[1]


class PublishedEvidenceGuards(unittest.TestCase):
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
