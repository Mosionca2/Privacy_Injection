import json
from pathlib import Path
import shutil
import tempfile
import unittest

from privacy_study import core as c
from tools.verify_rule_lifecycle import verify_case, verify_published

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence/rule-lifecycle-validation'


class RuleLifecycleEvidenceGuards(unittest.TestCase):
    def copy(self,folder,scenario):
        target=Path(folder)/scenario;shutil.copytree(EVIDENCE/scenario,target);return target

    def rehash_artifact(self,case,relative):
        path=case/'outputs'/relative;run=c.read_json(case/'run/run.json')
        artifact=next(v for v in run['artifacts'] if v['path']==relative)
        artifact.update(sha256='sha256:'+c.digest(path),size_bytes=path.stat().st_size)
        c.write_json(case/'run/run.json',run)

    def test_completed_lifecycle_preserves_precommitted_inputs_and_truthful_post_run_dirty_state(self):
        result=verify_published(EVIDENCE)
        self.assertEqual(sum(v['commands_checked'] for v in result['records']),20)
        self.assertTrue(c.read_json(EVIDENCE/'roundtrip/run/run.json')['code']['dirty'])
        self.assertEqual(result['records'][0]['expected_input_changes'],['reprollm.lock'])

    def test_rehashed_false_success_does_not_hide_required_cli_refusal(self):
        with tempfile.TemporaryDirectory() as folder:
            case=self.copy(folder,'conflict');path=case/'outputs/raw/result.json';value=c.read_json(path)
            command=next(v for v in value['commands'] if v['label']=='restore-refused')
            command.update(actual_exit=0,expected_exit=0);c.write_json(path,value)
            self.rehash_artifact(case,'raw/result.json')
            with self.assertRaisesRegex(ValueError,'Unexpected CLI exit'):
                verify_case(case,'conflict')

    def test_rehashed_archive_with_lost_binding_still_fails_original_rule_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            case=self.copy(folder,'roundtrip');relative='raw/snapshots/archive-original.json'
            archive=c.read_json(case/'outputs'/relative);archive['rule']['bindings']['config']=None
            c.write_json(case/'outputs'/relative,archive);self.rehash_artifact(case,relative)
            archive_relative='.reprollm/rule-archives/'+archive['archive_id']+'.json'
            shutil.copyfile(case/'outputs'/relative,case/'outputs'/archive_relative)
            self.rehash_artifact(case,archive_relative)
            result=c.read_json(case/'outputs/raw/result.json')
            result['snapshots']['archive-original.json']['sha256']=c.digest(case/'outputs'/relative)
            c.write_json(case/'outputs/raw/result.json',result);self.rehash_artifact(case,'raw/result.json')
            with self.assertRaisesRegex(ValueError,'complete rule|content ID'):
                verify_case(case,'roundtrip')
