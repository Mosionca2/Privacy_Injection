import importlib.util
from pathlib import Path
import tempfile
import unittest
from privacy_study import core as c
from privacy_study.record import manifest
from privacy_study.run import science_files

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('metadata_tools',ROOT/'tools/complete_recording_metadata.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class MetadataTests(unittest.TestCase):
    def test_annotations_describe_actual_interventions_and_are_idempotent(self):
        for defense in c.DEFENSES:
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder); c.write_json(root/'reprollm.yaml',manifest(defense,'dev',64,8))
                module.complete(root); first=(root/'reprollm.yaml').read_bytes()
                params=c.read_json(root/'reprollm.yaml')['privacy']['mechanism']['params']
                self.assertEqual(params['external_boundary'],defense in ('D1','D2','D3'))
                self.assertEqual(params['trusted_tail_reminder'],defense=='D2')
                self.assertEqual(params['per_line_origin_labels'],defense=='D3')
                module.complete(root);self.assertEqual(first,(root/'reprollm.yaml').read_bytes())
                self.assertIn('torch==',(root/'requirements.runtime.txt').read_text())

    def test_scientific_freeze_still_matches_current_inference_sources(self):
        self.assertEqual(c.read_json(ROOT/'protocol.freeze.json')['files'],science_files(ROOT))
