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
