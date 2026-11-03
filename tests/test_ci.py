from pathlib import Path
import subprocess
import tempfile
import unittest

from privacy_study import core as c
from tools.ci_verify import check_consumer


class ConsumerSourceGuards(unittest.TestCase):
    def test_commit_and_version_cannot_hide_changed_or_added_package_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            module = root / 'src/reprollm/__init__.py'
            module.parent.mkdir(parents=True)
            original = '__version__ = "test"\n'
            module.write_text(original)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', 'add', 'src'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                            'commit', '-qm', 'fixture'], cwd=root, check=True)
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            document = dict(source_commit=commit, module_version='test',
                            files=[dict(name='reprollm/__init__.py', sha256=c.digest(module))])
            self.assertEqual(check_consumer(root, document, commit)['package_files_checked'], 1)
            module.write_text(original + 'unreviewed = True\n')
            with self.assertRaisesRegex(ValueError, 'package bytes'):
                check_consumer(root, document, commit)
            module.write_text(original)
            (module.parent / 'extra.py').write_text('unreviewed = True\n')
            with self.assertRaisesRegex(ValueError, 'package bytes'):
                check_consumer(root, document, commit)
            (module.parent / 'extra.py').unlink()
            with self.assertRaisesRegex(ValueError, 'source commit'):
                check_consumer(root, document, '0' * 40)
