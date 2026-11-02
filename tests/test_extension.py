import copy
import tempfile
from pathlib import Path
import unittest
from privacy_study import core as c
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
