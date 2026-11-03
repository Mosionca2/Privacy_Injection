from pathlib import Path
import json
import shutil
import tempfile
import unittest

from privacy_study import core as c
from tail_ablation import core as a
from tail_ablation.evidence import check_capture

ROOT=Path(__file__).resolve().parents[1]


class TailAblationGuards(unittest.TestCase):
    def test_published_capture_rejects_a_forged_actual_token_trace(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            frozen=c.read_json(ROOT/a.STUDY/'protocol.freeze.json')
            for name in [*frozen['files'],a.STUDY+'/protocol.freeze.json',
                         'evidence/source-recovery-validation/primary-reference/recorder-source.json']:
                destination=root/name;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,destination)
            name='evidence/tail-ablation-v1/primary/dev/N'
            shutil.copytree(ROOT/name,root/name)
            self.assertEqual(check_capture(root,root/name)[0]['new_responses'],192)
            target=root/name/'results.jsonl'
            values=[json.loads(line) for line in target.read_text().splitlines()]
            values[1]['input_ids_sha256']='0'*64
            target.write_text(''.join(json.dumps(v)+'\n' for v in values))
            with self.assertRaisesRegex(ValueError,'response/prompt/scoring mismatch'):
                check_capture(root,root/name)

    def test_neutral_control_preserves_policy_and_repeated_question(self):
        protocol=dict(c.read_json(ROOT/'configs/protocol.json'),neutral_tail=a.NEUTRAL)
        case=a.fresh_cases('dev',24,20261103)[0]
        for variant in c.VARIANTS:
            prompts={d:a.messages(case,d,variant,protocol,'dev') for d in a.CONDITIONS}
            self.assertEqual(prompts['D1'][0],prompts['N'][0])
            self.assertEqual(prompts['N'][0],prompts['D2'][0])
            self.assertEqual(prompts['D1'][1]['content'].count('Question:'),1)
            for defense in ('N','D2'):
                self.assertEqual(prompts[defense][1]['content'].count('Question:'),2)
                self.assertNotIn(case['private'],prompts[defense][1]['content'])
            self.assertIn(a.NEUTRAL,prompts['N'][1]['content'])
            self.assertNotIn(protocol['reminder'],prompts['N'][1]['content'])
            self.assertIn(protocol['reminder'],prompts['D2'][1]['content'])

    def test_equal_length_cannot_hide_different_actual_tokens_or_text(self):
        packet=dict(input_tokens=2,rendered_sha256=a.text_hash('text'),input_ids_sha256=a.token_hash([1,2]))
        a.check_encoded(packet,'text',[1,2])
        with self.assertRaisesRegex(ValueError,'frozen prompt inventory'):
            a.check_encoded(packet,'text',[1,3])
        with self.assertRaisesRegex(ValueError,'frozen prompt inventory'):
            a.check_encoded(packet,'other',[1,2])

    def test_followup_cases_do_not_reuse_original_identifiers_or_entity_names(self):
        for split in ('dev','test'):
            old=c.cases(split,24,20261102);new=a.fresh_cases(split,24,20261103)
            self.assertFalse({v[k] for v in old for k in ('private','public')}&{v[k] for v in new for k in ('private','public')})
            self.assertTrue(all(v['id'].startswith('tail-v1-') and 'tail-v1-' in v['question'] for v in new))
            self.assertEqual(sum(v['task']=='lookup' for v in new),12)

    def test_frozen_source_and_batch_cannot_drift_before_loading_a_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'source.py';target.write_text('before\n')
            versions={'reprollm':'fixture'}
            c.write_json(root/a.STUDY/'protocol.freeze.json',dict(versions=versions,batch_sizes={'primary':64},files={'source.py':c.digest(target)}))
            a.check_freeze(root,'primary',versions,64)
            with self.assertRaisesRegex(ValueError,'dependency/batch drift'):
                a.check_freeze(root,'primary',versions,32)
            target.write_text('changed\n')
            with self.assertRaisesRegex(ValueError,'frozen input changed'):
                a.check_freeze(root,'primary',versions,64)
