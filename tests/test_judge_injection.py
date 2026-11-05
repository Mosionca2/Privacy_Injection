import unittest
from judge_injection import core as j
class JudgeProtocolGuards(unittest.TestCase):
 def test_strict_labels(self):
  self.assertEqual(j.parse(' NO_LEAK\n'),'NO_LEAK');self.assertIsNone(j.parse('NO_LEAK because safe'))
  self.assertIsNone(j.parse('LEAK NO_LEAK'));self.assertFalse(j.score('R001','NO_LEAK','NO_LEAK')['false_alarm'])
 def test_truth_and_rendering(self):
  values=list(j.base_inputs('dev',24));self.assertEqual(len(values),48)
  for row in values:
   self.assertEqual(row['target'] in row['candidate'],row['gold']=='LEAK')
   for guard in ('J0','J1'):
    text=str(j.messages(row['target'],row['candidate'],guard));self.assertNotIn('gold',text)
 def test_invalid_never_correct(self):
  for gold in ('LEAK','NO_LEAK'):
   r=j.score('R001','uncertain',gold);self.assertFalse(r['valid']);self.assertFalse(r['correct'])
 def test_cluster_statistics_and_holm(self):
  from judge_injection.analyze import clustered,holm
  self.assertEqual(clustered([0]*8,resamples=100)['bootstrap_95'],[0,0])
  self.assertEqual(clustered([0]*8,resamples=100)['sign_flip_p'],1)
  self.assertEqual(holm({'a':.04,'b':.01}),{'b':.02,'a':.04})
 def test_perturbations_remain_paired_by_case(self):
  from judge_injection.analyze import paired
  rows=[]
  for case,attack in [('a',True),('b',False)]:
   for family in j.ATTACKS:
    for position in ('prefix','suffix'):
     for view in ('attack','neutral'):
      rows.append(dict(case_id=case,gold='LEAK',view=view,family=family,position=position,scores={'false_safe':attack and view=='attack'}))
  self.assertEqual(paired(rows),{'a':1,'b':0})
  with self.assertRaisesRegex(ValueError,'Unpaired'):paired(rows[:-1])
 def test_partial_capture_is_not_a_complete_campaign(self):
  from tools.verify_judge_study import verify
  from pathlib import Path
  root=Path(__file__).resolve().parents[1]
  import tempfile,shutil
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);relative=Path('evidence/judge-injection-v1/primary/pilot/J1')
   shutil.copytree(root/relative,tmp/relative);shutil.copytree(root/'studies/judge-injection-v1/inputs',tmp/'studies/judge-injection-v1/inputs')
   self.assertEqual(verify(tmp,allow_partial=True)['judge_outputs'],32)
   with self.assertRaisesRegex(ValueError,'incomplete'):verify(tmp)
 def test_scores_recomputed_even_if_output_hash_is_updated(self):
  from tools.verify_judge_study import verify
  from pathlib import Path
  from privacy_study import core as c
  import tempfile,shutil,json
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as tmp:
   tmp=Path(tmp);relative=Path('evidence/judge-injection-v1/primary/pilot/J1')
   shutil.copytree(root/relative,tmp/relative);shutil.copytree(root/'studies/judge-injection-v1/inputs',tmp/'studies/judge-injection-v1/inputs')
   raw=tmp/relative/'judge-predictions.jsonl';rows=[json.loads(x) for x in raw.read_text().splitlines()]
   rows[1]['scores']['correct']=not rows[1]['scores']['correct'];raw.write_text(''.join(json.dumps(r)+'\n' for r in rows))
   file=tmp/relative/'run/run.json';run=c.read_json(file)
   for item in run['artifacts']:
    if item['path']=='raw/judge-predictions.jsonl':item['sha256']='sha256:'+c.digest(raw)
   c.write_json(file,run)
   with self.assertRaisesRegex(ValueError,'gold, score'):verify(tmp,allow_partial=True)
