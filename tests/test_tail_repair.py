import json
from pathlib import Path
import tempfile
import unittest

from tools.repair_result_tail import RepairError, digest, inspect_bytes, repair


class CopyRepairGuards(unittest.TestCase):
    def setUp(self):
        self.identity={'cases':['one'],'protocol':'frozen-fixture'}
        self.header=json.dumps(dict(type='meta',identity=self.identity)).encode()+b'\n'
        self.sample=b'{"type":"sample","id":"one:clean:none:none","output":"synthetic"}\n'
        self.failure=b'{"type":"failure","sample_ids":["two"],"error_type":"SyntheticFailure"}\n'
        self.prefix=self.header+self.sample+self.failure
        self.tail=b'{"type":"sample","output":"unfinished'

    def test_repair_copies_backups_and_preserves_complete_failure_and_sample_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'checkpoint.jsonl';data=self.prefix+self.tail;source.write_bytes(data)
            bundle=Path(folder)/'repair'
            result=repair(source,self.identity,mode='repair',expected_sha256=digest(data),output_directory=bundle)
            self.assertEqual(source.read_bytes(),data)
            self.assertEqual((bundle/'damaged.jsonl').read_bytes(),data)
            self.assertEqual((bundle/'repaired.jsonl').read_bytes(),self.prefix)
            self.assertEqual((bundle/'unfinished-tail.bin').read_bytes(),self.tail)
            self.assertEqual((result['complete_sample_rows'],result['complete_failure_rows']),(1,1))
            self.assertFalse(result['source_modified'])

    def test_inspection_has_no_filesystem_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'checkpoint.jsonl';source.write_bytes(self.prefix+self.tail)
            before=list(Path(folder).iterdir());result=repair(source,self.identity)
            self.assertTrue(result['repair_needed']);self.assertEqual(before,list(Path(folder).iterdir()))
            self.assertEqual(source.read_bytes(),self.prefix+self.tail)

    def test_complete_unterminated_sample_or_failure_is_never_discarded(self):
        for row in (self.sample,self.failure):
            with self.subTest(row=row),self.assertRaisesRegex(RepairError,'complete JSON without a newline'):
                inspect_bytes(self.header+row.rstrip(b'\n'),self.identity)

    def test_middle_corruption_and_non_prefix_tail_are_refused(self):
        for data in (self.header+b'{broken}\n'+self.tail,self.prefix+b'{"type":,,}',self.prefix+b'trash'):
            with self.subTest(data=data),self.assertRaises(RepairError):
                inspect_bytes(data,self.identity)

    def test_identity_duplicate_samples_and_ambiguous_json_are_refused(self):
        with self.assertRaisesRegex(RepairError,'identity differs'):
            inspect_bytes(self.prefix+self.tail,{'cases':['other']})
        typed_header=json.dumps(dict(type='meta',identity={'schema_version':1})).encode()+b'\n'
        with self.assertRaisesRegex(RepairError,'identity differs'):
            inspect_bytes(typed_header+self.sample+self.tail,{'schema_version':True})
        with self.assertRaisesRegex(RepairError,'duplicate successful'):
            inspect_bytes(self.header+self.sample+self.sample+self.tail,self.identity)
        with self.assertRaises(RepairError):
            inspect_bytes(self.prefix+b'{"type":"sample","type":"failure"}',self.identity)

    def test_changed_preimage_or_existing_bundle_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'checkpoint.jsonl';data=self.prefix+self.tail;source.write_bytes(data)
            inspected=repair(source,self.identity);source.write_bytes(data+b' changed')
            target=Path(folder)/'repair'
            with self.assertRaisesRegex(RepairError,'digest changed'):
                repair(source,self.identity,mode='repair',expected_sha256=inspected['source_sha256'],output_directory=target)
            self.assertFalse(target.exists())
            source.write_bytes(data);target.mkdir();(target/'keep').write_text('preserve')
            with self.assertRaisesRegex(RepairError,'directory exists'):
                repair(source,self.identity,mode='repair',expected_sha256=digest(data),output_directory=target)
            self.assertEqual((target/'keep').read_text(),'preserve')

    def test_clean_checkpoint_is_a_noop_and_needs_no_output_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'checkpoint.jsonl';source.write_bytes(self.prefix)
            result=repair(source,self.identity,mode='repair',output_directory=Path(folder)/'unused')
            self.assertFalse(result['repair_needed']);self.assertFalse((Path(folder)/'unused').exists())
            self.assertEqual(source.read_bytes(),self.prefix)
