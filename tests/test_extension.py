import copy
import os
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import yaml
from privacy_study import core as c
from tools import prepare_extension as extension
from tools.prepare_extension import ROOT, validate_study, prepare


class ExtensionGuards(unittest.TestCase):
    def fixture(self, directory):
        study = Path(directory)
        protocol = copy.deepcopy(c.read_json(ROOT / 'configs/protocol.json'))
        protocol.update(protocol_id='extension-test', model_label='Local test snapshot')
        c.write_json(study / 'protocol.json', protocol)
        c.write_json(study / 'model.identity.json', {'model_label': protocol['model_label']})
        c.write_json(study / 'study.json', {'shared_files': {
            'data/test.jsonl': c.digest(ROOT / 'data/test.jsonl')}})
        return study

    def test_prompt_edits_are_rejected_for_model_only_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            study = self.fixture(directory)
            validate_study(study)
            value = c.read_json(study / 'protocol.json')
            value['reminder'] += ' Changed.'
            c.write_json(study / 'protocol.json', value)
            with self.assertRaisesRegex(ValueError, 'changes prompts'):
                validate_study(study)

    def test_shared_data_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            study = self.fixture(directory)
            c.write_json(study / 'study.json', {'shared_files': {'data/test.jsonl': 'wrong'}})
            with self.assertRaisesRegex(ValueError, 'input drift'):
                validate_study(study)

    def test_unfrozen_formal_extension_is_rejected_before_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            study = self.fixture(directory)
            destination = study / 'not-created'
            with self.assertRaisesRegex(ValueError, 'own freeze'):
                prepare(study, destination, '/unused-model', 'D0', 'test', 64)
            self.assertFalse(destination.exists())


class ExtensionWorkspaceRegression(unittest.TestCase):
    def fixture(self, folder, *, initialized=True, rules=None):
        base = Path(folder)
        source, study, model = (base / name for name in ('source', 'study', 'model'))
        for path in (source, study, model):
            path.mkdir()
        protocol = c.read_json(ROOT / 'configs/protocol.json')
        (source / 'configs').mkdir()
        (source / 'configs/protocol.json').write_bytes((ROOT / 'configs/protocol.json').read_bytes())
        extended = dict(protocol, protocol_id='setup-regression', model_label='Synthetic fixture')
        c.write_json(study / 'protocol.json', extended)
        (model / 'config.json').write_text('{"model_type":"qwen3"}\n')
        identity = {'model_label': extended['model_label'], 'files': [{
            'name': 'config.json', 'size': (model / 'config.json').stat().st_size,
            'sha256': c.digest(model / 'config.json')}]}
        c.write_json(study / 'model.identity.json', identity)
        c.write_json(study / 'study.json', {'shared_files': {
            'configs/protocol.json': c.digest(source / 'configs/protocol.json')}})
        (source / '.gitignore').write_text('assets/\nraw/\n__pycache__/\n')
        if initialized:
            c.write_json(source / 'reprollm.yaml', c.read_json(ROOT / 'reprollm.yaml'))
            (source / 'reprollm.lock').write_text('inherited-condition-lock\n')
        if rules is not None:
            c.write_json(source / '.reprollm/project-rules.yaml', rules)
        for argv in (['git', 'init', '-q'], ['git', 'add', '.'],
                     ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '-qm', 'fixture']):
            subprocess.run(argv, cwd=source, check=True, capture_output=True)
        return source, study, model

    def rules(self):
        return yaml.safe_load((ROOT / '.reprollm/project-rules.yaml').read_text())

    def run_prepare(self, source, study, model, destination):
        with patch.object(extension, 'ROOT', source):
            return prepare(study, destination, model, 'D1', 'dev', 16, 1)

    def test_existing_manifest_reuses_matching_rules_without_touching_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source, study, model = self.fixture(folder, rules=self.rules())
            names = ['reprollm.yaml', 'reprollm.lock', '.reprollm/project-rules.yaml']
            before = {name: (source / name).read_bytes() for name in names}
            old_cwd = Path.cwd()
            work = self.run_prepare(source, study, model, Path(folder) / 'new-condition')
            self.assertEqual(Path.cwd(), old_cwd)
            self.assertEqual({name: (source / name).read_bytes() for name in names}, before)
            self.assertEqual((work / '.reprollm/project-rules.yaml').read_bytes(),
                             before['.reprollm/project-rules.yaml'])
            self.assertFalse((work / 'reprollm.lock').exists())
            self.assertFalse((work / 'raw/init.txt').exists())
            declared = c.read_json(work / 'reprollm.yaml')
            self.assertEqual(declared['custom'], {'defense': 'D1', 'dataset_split': 'dev', 'batch_size': 16})
            self.assertEqual(declared['datasets']['eval']['sampling']['n'], 1)
            self.assertEqual(c.read_json(work / 'configs/protocol.json')['protocol_id'], 'setup-regression')
            self.assertEqual(os.stat(model / 'config.json').st_ino,
                             os.stat(work / 'assets/model/config.json').st_ino)

    def test_fresh_checkout_still_initializes_all_bindings(self):
        with tempfile.TemporaryDirectory() as folder:
            source, study, model = self.fixture(folder, initialized=False)
            work = self.run_prepare(source, study, model, Path(folder) / 'new-condition')
            self.assertTrue((work / 'raw/init.txt').exists())
            rules = yaml.safe_load((work / '.reprollm/project-rules.yaml').read_text())['rules']
            self.assertEqual({r['id'] for r in rules},
                             {'project.defense', 'project.dataset_split', 'project.batch_size'})
            self.assertTrue(all(r['severity'] == 'CRITICAL' for r in rules))

    def test_missing_rules_are_added_and_unrelated_rules_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            document = self.rules()
            retained = document['rules'][0]
            unrelated = dict(retained, id='project.extra', field='custom.extra', reason='Keep this rule.')
            document['rules'] = [retained, unrelated]
            source, study, model = self.fixture(folder, rules=document)
            work = self.run_prepare(source, study, model, Path(folder) / 'new-condition')
            rules = yaml.safe_load((work / '.reprollm/project-rules.yaml').read_text())['rules']
            actual = {r['id']: r for r in rules}
            self.assertEqual(len(rules), 4)
            self.assertEqual(actual['project.defense'], retained)
            self.assertEqual(actual['project.extra'], unrelated)
            self.assertIn('project.dataset_split', actual)
            self.assertIn('project.batch_size', actual)

    def test_conflicting_existing_rule_is_rejected_without_overwriting_it(self):
        for change in ({'field': 'custom.wrong'}, {'severity': 'WARNING'},
                       {'bindings': {'cli': '--wrong'}}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                document = self.rules()
                document['rules'][0].update(change)
                source, study, model = self.fixture(folder, rules=document)
                destination = Path(folder) / 'new-condition'
                original = (source / '.reprollm/project-rules.yaml').read_bytes()
                with self.assertRaisesRegex(ValueError, 'Conflicting project rule project.defense'):
                    self.run_prepare(source, study, model, destination)
                self.assertEqual((destination / '.reprollm/project-rules.yaml').read_bytes(), original)
                self.assertEqual((source / '.reprollm/project-rules.yaml').read_bytes(), original)

    def test_existing_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            source, study, model = self.fixture(folder, rules=self.rules())
            destination = Path(folder) / 'existing-condition'
            destination.mkdir()
            marker = destination / 'resume-me.txt'
            marker.write_text('existing run evidence\n')
            with self.assertRaisesRegex(ValueError, 'new condition workspace'):
                self.run_prepare(source, study, model, destination)
            self.assertEqual(marker.read_text(), 'existing run evidence\n')
