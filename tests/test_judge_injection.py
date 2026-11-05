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
